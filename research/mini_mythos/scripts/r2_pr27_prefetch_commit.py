#!/usr/bin/env python3
"""R2 Gate G: simulated TWO-WORKER ordered-commit prefetch/resume control.

This is a deterministic CPU SIMULATOR, not torch DataLoader(num_workers=2),
not real Hugging Face FineWeb-Edu, and not an upstream PR27 trainer change.

Safety principle: save the global sample index that was COMMITTED by the
optimizer in the same checkpoint as model/optimizer/RNG. Prefetched and
completed-but-not-consumed batches are speculative and MUST be discarded
after a crash. Replay them from an immutable indexed source, with stable
worker assignment (task_id % worker_count).

The simulator deliberately completes tasks out of order, keeps prefetch
pending at checkpoint, and shows why restarting at DISPATCH frontier skips
samples. It verifies full model/optimizer/RNG/trace bitwise equality across
an interruption with real tiny AdamW and frozen GPT2 token IDs.

Limits: no actual processes, multiprocessing queues, HF data revision or
sharded loader, pinned FineWeb shard file, CUDA, or 118M weights.
"""
import argparse
from pathlib import Path
import random

import torch
import torch.nn.functional as F

from common import atomic_json, get_repo
from r2_pr27_guarded_checkpoint import (
    read_frozen_contract, require_real_tokenizer_identity,
    safe_load_bound_checkpoint, save_bound_checkpoint,
)
from r2_pr27_tokenizer_contract import load_tokenizer
from r2_pr27_stream_resume import (
    CHUNK_LEN, LOOP_CHOICES, PackedCursor, SEED,
    digest, exact_optimizer_state_equal, local_documents, new_training,
    restore_bundle, split_documents, training_bundle,
)


PROTOCOL = "R2_SIMULATED_ORDERED_COMMIT_PREFETCH_V1"
WORKERS = 2
PREFETCH_CAPACITY = 4
TOTAL_STEPS = 12
CHECKPOINT_STEP = 5


def immutable_indexed_tasks(train, tokenizer, contract, *, n_tasks=32):
    """Preindex PR27-shaped packed (x,y) chunks from an immutable local fixture.

    Preindexing is deliberate: it provides random access by global task id
    that upstream HF streaming does NOT currently provide. It is a protocol
    design input, not a claim that PR27 already supports this.
    """
    if not isinstance(n_tasks, int) or n_tasks <= 0:
        raise ValueError("n_tasks must be positive")
    original = PackedCursor(
        train, tokenizer, seq_len=CHUNK_LEN,
        contract_sha=contract["fingerprint_sha256"],
        eos_id=int(contract["fingerprint"]["special_tokens"]["eos_token_id"])
    )
    items = []
    try:
        for i in range(n_tasks):
            x, y = original.next_chunk()
            items.append({
                "task_id": i,
                "x": x,
                "y": y,
                "chunk_sha256": digest({"x": x.tolist(), "y": y.tolist()}),
            })
    except StopIteration as exc:
        raise ValueError("Not enough immutable source tokens to index tasks") from exc
    origin = {
        "records_sha256": digest(train),
        "tokenizer_contract_sha256": contract["fingerprint_sha256"],
        "seq_len": CHUNK_LEN,
        "tasks": [item["chunk_sha256"] for item in items],
    }
    return items, digest(origin)


class OrderedCommitPrefetch:
    """Simulation of two workers returning precomputed tasks out of order.

    Its durable state NEVER includes speculative dispatched/completed IDs:
    those are only an in-process cache. After restart the same indexed task
    IDs are reissued from commit frontier, so prefetch cannot skip tokens.
    """

    def __init__(self, items, source_sha, contract_sha, *,
                 workers=WORKERS, capacity=PREFETCH_CAPACITY):
        if not items or workers != WORKERS or capacity < 2:
            raise ValueError("Gate G freezes two logical workers and bounded prefetch")
        if len(set(item["task_id"] for item in items)) != len(items):
            raise ValueError("Duplicate global task IDs")
        if [item["task_id"] for item in items] != list(range(len(items))):
            raise ValueError("Indexed tasks must be globally consecutive from zero")
        for item in items:
            if digest({"x": item["x"].tolist(),
                       "y": item["y"].tolist()}) != item["chunk_sha256"]:
                raise ValueError("Indexed task payload checksum mismatch")
        if not isinstance(source_sha, str) or len(source_sha) != 64:
            raise ValueError("Source SHA malformed")
        if not isinstance(contract_sha, str) or len(contract_sha) != 64:
            raise ValueError("Tokenizer contract SHA malformed")
        self.items = items
        self.source_sha = source_sha
        self.contract_sha = contract_sha
        self.workers = workers
        self.capacity = capacity
        self.seq_len = int(items[0]["x"].numel())
        if any(item["x"].numel() != self.seq_len or
               item["y"].numel() != self.seq_len for item in items):
            raise ValueError("Task sequence lengths do not match")
        self.committed = 0
        self.issued = 0
        self.outstanding = {}
        self.finished = set()
        self.completion_history = []

    @property
    def emitted(self):
        """Committed optimizer steps, not prefetched or completed requests."""
        return self.committed

    def worker_for(self, task_id):
        if not isinstance(task_id, int) or not 0 <= task_id < len(self.items):
            raise ValueError("Invalid global task index")
        return task_id % self.workers

    def dispatch(self):
        """Assign up to capacity speculative tasks with stable worker IDs."""
        while len(self.outstanding) < self.capacity and self.issued < len(self.items):
            i = self.issued
            self.outstanding[i] = self.worker_for(i)
            self.issued += 1
        return list(self.outstanding)

    def complete_out_of_order(self):
        """Reverse order completion intentionally models asynchronous workers."""
        self.dispatch()
        for task_id in sorted(self.outstanding, reverse=True):
            if task_id not in self.finished:
                self.finished.add(task_id)
                self.completion_history.append(task_id)

    def ready_next(self):
        """Only return global next COMMITTED index regardless of arrival order."""
        self.complete_out_of_order()
        idx = self.committed
        if idx >= len(self.items):
            raise StopIteration("Indexed training task stream exhausted")
        if idx not in self.finished:
            raise RuntimeError("Next ordered task has not completed")
        item = self.items[idx]
        return item["task_id"], item["x"], item["y"]

    def commit_after_optimizer(self, task_id):
        """Call ONLY after optimizer.step() returns successfully."""
        if task_id != self.committed or task_id not in self.finished:
            raise ValueError("Optimizer may commit only next ready task in order")
        self.outstanding.pop(task_id)
        self.finished.remove(task_id)
        self.committed += 1
        self.dispatch()

    def speculative_status(self):
        return {
            "committed_next_id": self.committed,
            "dispatched_next_id": self.issued,
            "outstanding_ids": sorted(self.outstanding),
            "completed_uncommitted_ids": sorted(self.finished),
            "worker_ids": {str(idx): self.worker_for(idx)
                           for idx in sorted(self.outstanding)},
        }

    def state_dict(self):
        """Durable commit frontier: never resume from dispatched/preloaded ID."""
        core = {
            "protocol": PROTOCOL,
            "source_sha": self.source_sha,
            "tokenizer_contract_sha256": self.contract_sha,
            "workers": self.workers,
            "capacity": self.capacity,
            "seq_len": self.seq_len,
            "task_count": len(self.items),
            "partition": "global_task_id modulo num_workers",
            "next_committed_task_id": self.committed,
            "emitted_chunks": self.committed,
            "last_committed_chunk_sha256":
                None if self.committed == 0
                else self.items[self.committed - 1]["chunk_sha256"],
        }
        return dict(core, state_sha256=digest(core))

    def load_state_dict(self, state, *, strict_replay=True):
        if not isinstance(state, dict):
            raise ValueError("Invalid global commit cursor")
        data = dict(state)
        got = data.pop("state_sha256", None)
        if got != digest(data):
            raise ValueError("Committed frontier checksum mismatch")
        ref = self.state_dict()
        for k in ("protocol", "source_sha", "tokenizer_contract_sha256",
                  "workers", "capacity", "seq_len", "task_count", "partition"):
            if data.get(k) != ref[k]:
                raise ValueError("Commit cursor source or worker policy mismatch: " + k)
        n = data.get("next_committed_task_id")
        if (not isinstance(n, int) or not 0 <= n <= len(self.items)
                or data.get("emitted_chunks") != n):
            raise ValueError("Commit cursor frontier invalid")
        previous = None if n == 0 else self.items[n - 1]["chunk_sha256"]
        if data.get("last_committed_chunk_sha256") != previous:
            raise ValueError("Last committed task digest mismatch")
        if strict_replay:
            for idx in range(n):
                item = self.items[idx]
                if (item["task_id"] != idx or
                        digest({"x": item["x"].tolist(),
                                "y": item["y"].tolist()})
                        != item["chunk_sha256"]):
                    raise ValueError("Indexed task source replay mismatch")
        self.committed = n
        # Drop ALL work issued/returned but not yet applied to optimizer.
        self.issued = n
        self.outstanding = {}
        self.finished = set()
        self.completion_history = []
        self.dispatch()


def step_training_prefetched(model, optimizer, scheduler, py_rng, gen):
    task_id, x, y = scheduler.ready_next()
    loops = py_rng.choice(LOOP_CHOICES)
    noise = torch.rand(x.numel(), model.embedding.embedding_dim, generator=gen)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    logits = model(x, loops=loops, noise=noise)
    loss = F.cross_entropy(logits, y)
    if not torch.isfinite(loss.detach()):
        raise RuntimeError("Nonfinite tiny optimizer loss")
    loss.backward()
    optimizer.step()
    # Commit is AFTER the complete model update, not at task dispatch time.
    scheduler.commit_after_optimizer(task_id)
    return {
        "task_id": task_id,
        "worker_id": scheduler.worker_for(task_id),
        "chunk_sha256": digest({"x": x.tolist(), "y": y.tolist()}),
        "loops": loops,
        "noise_mask_sha256": digest((noise > 0.15).to(torch.uint8).tolist()),
        "loss": float(loss.detach()),
    }


def run_steps(model, optimizer, scheduler, py_rng, gen, steps):
    return [
        step_training_prefetched(model, optimizer, scheduler, py_rng, gen)
        for _ in range(steps)
    ]


def compare_with_prefetch_interruption(
    tokenizer, contract, *, checkpoint_path, manifest_path,
    total_steps=TOTAL_STEPS, cutoff=CHECKPOINT_STEP,
    documents=None
):
    if not 0 < cutoff < total_steps:
        raise ValueError("Invalid Gate G interruption point")
    records = documents if documents is not None else local_documents()
    train, heldout = split_documents(records)
    fingerprint = require_real_tokenizer_identity(tokenizer, contract)
    task_items, task_source_sha = immutable_indexed_tasks(
        train, tokenizer, contract, n_tasks=max(32, total_steps + 5)
    )
    vocab = contract["fingerprint"]["len_tokenizer"]
    torch.set_num_threads(min(4, torch.get_num_threads()))

    def make_scheduler():
        return OrderedCommitPrefetch(
            task_items, task_source_sha, contract["fingerprint_sha256"]
        )

    continuous_model, continuous_opt, continuous_py, continuous_gen = new_training(vocab)
    continuous_scheduler = make_scheduler()
    expected = run_steps(
        continuous_model, continuous_opt, continuous_scheduler,
        continuous_py, continuous_gen, total_steps
    )

    interrupted_model, interrupted_opt, interrupted_py, interrupted_gen = new_training(vocab)
    interrupted_scheduler = make_scheduler()
    prefix = run_steps(
        interrupted_model, interrupted_opt, interrupted_scheduler,
        interrupted_py, interrupted_gen, cutoff
    )

    # Prefetch has now dispatched tasks beyond cutoff and completed them,
    # but the optimizer has NOT used those tasks.
    interrupted_scheduler.complete_out_of_order()
    speculative = interrupted_scheduler.speculative_status()
    if (speculative["dispatched_next_id"] <= cutoff or
            not speculative["completed_uncommitted_ids"]):
        raise AssertionError("Gate G failed to create outstanding prefetch at interruption")
    durable = interrupted_scheduler.state_dict()
    if durable["next_committed_task_id"] != cutoff:
        raise AssertionError("Durable checkpoint was not taken at committed frontier")

    payload = training_bundle(
        contract, interrupted_model, interrupted_opt,
        interrupted_scheduler, interrupted_py, interrupted_gen
    )
    save_bound_checkpoint(
        checkpoint_path, manifest_path, payload, contract, fingerprint
    )

    resumed_model, resumed_opt, resumed_py, resumed_gen = new_training(vocab)
    resumed_scheduler = make_scheduler()
    bundle = safe_load_bound_checkpoint(
        checkpoint_path, manifest_path, contract, fingerprint
    )
    restore_bundle(
        bundle, resumed_model, resumed_opt, resumed_scheduler,
        resumed_py, resumed_gen
    )
    first_resumed = resumed_scheduler.ready_next()[0]
    if first_resumed != cutoff:
        raise AssertionError("Resume skipped speculative but unused tasks")
    suffix = run_steps(
        resumed_model, resumed_opt, resumed_scheduler, resumed_py,
        resumed_gen, total_steps - cutoff
    )
    observed = prefix + suffix

    trace_eq = expected == observed
    model_eq = exact_optimizer_state_equal(
        continuous_model.state_dict(), resumed_model.state_dict()
    )
    opt_eq = exact_optimizer_state_equal(
        continuous_opt.state_dict(), resumed_opt.state_dict()
    )
    stream_eq = continuous_scheduler.state_dict() == resumed_scheduler.state_dict()
    rng_eq = (
        continuous_py.getstate() == resumed_py.getstate()
        and torch.equal(continuous_gen.get_state(), resumed_gen.get_state())
    )
    if not all((trace_eq, model_eq, opt_eq, stream_eq, rng_eq)):
        raise AssertionError("Interrupted prefetched training diverged from continuous")
    naive_skipped = list(range(
        cutoff, speculative["dispatched_next_id"]
    ))
    if not naive_skipped:
        raise AssertionError("Naive dispatch cursor did not demonstrate skipped samples")

    return {
        "experiment": "R2 Gate G two-LOGICAL-worker prefetch+ordered commit CPU simulation",
        "source": "immutable indexed local synthetic PR27-shaped documents; NOT HF FineWeb",
        "tokenizer_contract_sha256": contract["fingerprint_sha256"],
        "source_documents": len(records),
        "training_documents": len(train),
        "heldout_documents": len(heldout),
        "heldout_consumed_for_training": False,
        "workers_simulated": WORKERS,
        "real_worker_processes_started": 0,
        "prefetch_capacity": PREFETCH_CAPACITY,
        "indexed_task_count": len(task_items),
        "immutable_source_sha256": task_source_sha,
        "total_optimizer_steps": total_steps,
        "interrupt_at_committed_step": cutoff,
        "speculative_state_before_crash": speculative,
        "durable_frontier_before_crash": durable,
        "first_replayed_after_crash_task_id": first_resumed,
        "naive_dispatch_frontier_would_skip_task_ids": naive_skipped,
        "trajectories_bitwise_equal": trace_eq,
        "max_abs_loss_difference": max(
            abs(a["loss"] - b["loss"]) for a, b in zip(expected, observed)
        ),
        "model_params_bitwise_equal": model_eq,
        "optimizer_state_bitwise_equal": opt_eq,
        "committed_cursor_bitwise_equal": stream_eq,
        "python_torch_rng_bitwise_equal": rng_eq,
        "no_fineweb_data": True,
        "production_dataloader_resume_implemented": False,
        "checkpoint": str(checkpoint_path),
        "manifest": str(manifest_path),
        "limitations": "This uses TWO LOGICAL workers in one CPU process, not "
                       "torch DataLoader(num_workers=2) or real HF Streaming. "
                       "There are no OS worker queues, file-shard source offsets "
                       "or distributed worker RNG states. Production multiworker "
                       "cannot be declared restorable from this simulation.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--contract", default=
                    "research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    ap.add_argument("--checkpoint", default=
                    "research/mini_mythos/results/r2/pr27_gate_g_prefetch_cpu.pt")
    ap.add_argument("--manifest", default=
                    "research/mini_mythos/results/r2/pr27_gate_g_prefetch_cpu.manifest.json")
    ap.add_argument("--out", default=
                    "research/mini_mythos/results/r2/pr27_gate_g_prefetch_comparison.json")
    args = ap.parse_args()
    root = get_repo(args.repo)
    result_root = (root / "research/mini_mythos/results").resolve()
    paths = [Path(x).resolve() for x in (
        args.contract, args.checkpoint, args.manifest, args.out
    )]
    if any(not p.is_relative_to(result_root) for p in paths):
        ap.error("All data must be kept under research/mini_mythos/results")
    if any(p.exists() for p in paths[1:]):
        ap.error("Gate G evidence exists; refusing overwrite")
    contract = read_frozen_contract(paths[0], strict_gate=True)
    fp = contract["fingerprint"]
    tokenizer = load_tokenizer(
        fp["identifier"], fp["pinned_revision"], offline=True
    )
    result = compare_with_prefetch_interruption(
        tokenizer, contract, checkpoint_path=paths[1], manifest_path=paths[2]
    )
    atomic_json(paths[3], result)
    print("Workers simulated:", result["workers_simulated"],
          "OS worker processes:", result["real_worker_processes_started"])
    print("Pending prefetch at crash:", 
          result["speculative_state_before_crash"]["completed_uncommitted_ids"])
    print("Committed cursor:", result["interrupt_at_committed_step"])
    print("Dispatched frontier:",
          result["speculative_state_before_crash"]["dispatched_next_id"])
    print("Naive dispatched-frontier resume would SKIP:",
          result["naive_dispatch_frontier_would_skip_task_ids"])
    print("First resumed task:", result["first_replayed_after_crash_task_id"])
    print("Trace identical:", result["trajectories_bitwise_equal"])
    print("Maximum abs loss difference:", result["max_abs_loss_difference"])
    print("Model params identical:", result["model_params_bitwise_equal"])
    print("AdamW optimizer identical:", result["optimizer_state_bitwise_equal"])
    print("Committed cursor identical:", result["committed_cursor_bitwise_equal"])
    print("Python/Torch RNG identical:", result["python_torch_rng_bitwise_equal"])
    print("Real HF FineWeb-Edu:", "NOT_CONSUMED")
    print("Actual multi-process PR27 loader:", "NOT_TESTED")
    print("GPU training:", "NOT_PERFORMED")
    print("Saved:", paths[3])


if __name__ == "__main__":
    main()
