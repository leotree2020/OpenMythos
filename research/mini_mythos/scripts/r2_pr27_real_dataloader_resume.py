#!/usr/bin/env python3
"""R2 Gate H: REAL two-process PyTorch DataLoader prefetch/resume CPU proof.

This experiment creates TWO actual OS worker subprocesses with
DataLoader(num_workers=2, prefetch_factor=2, in_order=True).
It uses an immutable, pre-indexed LOCAL synthetic source, not HF FineWeb.
The only durable cursor is the optimizer-COMMITTED global task index.
Prefetched-but-unused records are reread on a new DataLoader after restart.

Unlike Gate G, workers really fetch samples in different processes and
write to a shared fetch-count array. Their PIDs are observed and asserted.
Worker PIDs / worker IDs are diagnostics, NOT part of bitwise training trace:
different worker assignment after resume is allowed if payloads are identical.

Interruption is a controlled termination of iterator after checkpoint, not
SIGKILL/power loss. No production IterableDataset, CUDA or 118M model.
"""
import argparse
import gc
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, get_worker_info

from common import atomic_json, get_repo
from r2_pr27_guarded_checkpoint import (
    read_frozen_contract, require_real_tokenizer_identity,
    safe_load_bound_checkpoint, save_bound_checkpoint,
)
from r2_pr27_tokenizer_contract import load_tokenizer
from r2_pr27_prefetch_commit import immutable_indexed_tasks
from r2_pr27_stream_resume import (
    CHUNK_LEN, LOOP_CHOICES, digest, exact_optimizer_state_equal,
    local_documents, new_training, restore_bundle, split_documents,
    training_bundle,
)


PROTOCOL = "R2_PR27_REAL_TWO_PROCESS_DATALOADER_V1"
WORKERS = 2
PREFETCH_FACTOR = 2
TOTAL_STEPS = 12
INTERRUPT_AFTER = 5
EXTRA_INDEXED_TASKS = 20


class PreindexedWorkerDataset(Dataset):
    """Map-style immutable local indexed chunks; access recorded in SHARED array."""

    def __init__(self, tasks, read_counts):
        if not tasks or len(read_counts) < len(tasks):
            raise ValueError("Tasks or shared read counters unavailable")
        self.tasks = tasks
        self.read_counts = read_counts

    def __len__(self):
        return len(self.tasks)

    def __getitem__(self, index):
        index = int(index)
        if not 0 <= index < len(self.tasks):
            raise IndexError(index)
        item = self.tasks[index]
        if item["task_id"] != index:
            raise ValueError("Dataset index/task-ID mismatch")
        with self.read_counts.get_lock():
            self.read_counts[index] += 1
        info = get_worker_info()
        return {
            "task_id": index,
            "x": item["x"].clone(),
            "y": item["y"].clone(),
            "chunk_sha256": item["chunk_sha256"],
            "worker_id": -1 if info is None else info.id,
            "worker_pid": os.getpid(),
        }


class DurableOptimizerCursor:
    """Optimizer update-ACK index; NO speculative Worker offsets in checkpoint."""

    def __init__(self, tasks, source_sha, contract_sha):
        if not tasks or [i["task_id"] for i in tasks] != list(range(len(tasks))):
            raise ValueError("Need consecutive immutable global task indices")
        if not isinstance(source_sha, str) or len(source_sha) != 64:
            raise ValueError("Invalid indexed source SHA")
        if not isinstance(contract_sha, str) or len(contract_sha) != 64:
            raise ValueError("Invalid tokenizer contract SHA")
        self.tasks = tasks
        self.source_sha = source_sha
        self.contract_sha = contract_sha
        self.seq_len = int(tasks[0]["x"].numel())
        self.committed = 0
        for i in tasks:
            if (i["x"].numel() != self.seq_len or
                    i["y"].numel() != self.seq_len or
                    digest({"x": i["x"].tolist(), "y": i["y"].tolist()})
                    != i["chunk_sha256"]):
                raise ValueError("Indexed training task corrupted")

    @property
    def emitted(self):
        return self.committed

    def ack_after_optimizer(self, task_id, actual_sha):
        if task_id != self.committed:
            raise ValueError("Only the next globally committed task can be acknowledged")
        if actual_sha != self.tasks[task_id]["chunk_sha256"]:
            raise ValueError("Optimizer task payload SHA differs from immutable source")
        self.committed += 1

    def state_dict(self):
        core = {
            "protocol": PROTOCOL,
            "source_sha": self.source_sha,
            "tokenizer_contract_sha256": self.contract_sha,
            "workers": WORKERS,
            "prefetch_factor": PREFETCH_FACTOR,
            "in_order": True,
            "seq_len": self.seq_len,
            "indexed_task_count": len(self.tasks),
            "emitted_chunks": self.committed,
            "next_committed_task_id": self.committed,
            "last_committed_chunk_sha256": (
                None if self.committed == 0 else
                self.tasks[self.committed - 1]["chunk_sha256"]
            ),
        }
        return dict(core, state_sha256=digest(core))

    def load_state_dict(self, state, *, strict_replay=True):
        if not isinstance(state, dict):
            raise ValueError("Checkpoint cursor missing")
        core = dict(state)
        saved_hash = core.pop("state_sha256", None)
        if saved_hash != digest(core):
            raise ValueError("Checkpoint cursor checksum mismatch")
        ours = self.state_dict()
        for field in ("protocol", "source_sha", "tokenizer_contract_sha256",
                      "workers", "prefetch_factor", "in_order",
                      "seq_len", "indexed_task_count"):
            if core.get(field) != ours[field]:
                raise ValueError("Checkpoint cursor source/worker policy mismatch: " + field)
        n = core.get("next_committed_task_id")
        if (not isinstance(n, int) or not 0 <= n <= len(self.tasks) or
                core.get("emitted_chunks") != n):
            raise ValueError("Checkpoint committed cursor invalid")
        last = None if n == 0 else self.tasks[n-1]["chunk_sha256"]
        if core.get("last_committed_chunk_sha256") != last:
            raise ValueError("Checkpoint last committed payload checksum mismatch")
        if strict_replay:
            for i in range(n):
                item = self.tasks[i]
                if (item["task_id"] != i or
                        digest({"x": item["x"].tolist(), "y": item["y"].tolist()})
                        != item["chunk_sha256"]):
                    raise ValueError("Checkpoint indexed source replay differs")
        self.committed = n


def shared_read_snapshot(counters):
    with counters.get_lock():
        return list(counters[:])


def observed_unused_fetches(reads, consumed_index):
    return [
        i for i, count in enumerate(reads)
        if i >= consumed_index and count > 0
    ]


def make_loader(tasks, *, start, counts, context):
    """Real PyTorch two-process ordered DataLoader; do not expose privates."""
    if not isinstance(start, int) or not 0 <= start < len(tasks):
        raise ValueError("Requested committed cursor outside indexed task range")
    dataset = PreindexedWorkerDataset(tasks, counts)
    # Starting at saved commit frontier makes already fetched but
    # uncommitted tasks available again; no queue snapshot is required.
    indices = list(range(start, len(tasks)))
    from torch.utils.data import Subset
    subset = Subset(dataset, indices)
    return DataLoader(
        subset, batch_size=None, shuffle=False, num_workers=WORKERS,
        prefetch_factor=PREFETCH_FACTOR, persistent_workers=False,
        multiprocessing_context=context, timeout=30, in_order=True,
    )


def consume_one(model, optimizer, cursor, py_rng, generator, batch):
    """Only acknowledge the global task AFTER optimizer.step succeeds."""
    idx = int(batch["task_id"])
    if idx != cursor.committed:
        raise ValueError("Loader returned nonconsecutive or duplicated task ID")
    x, y = batch["x"], batch["y"]
    observed = digest({"x": x.tolist(), "y": y.tolist()})
    if observed != batch["chunk_sha256"]:
        raise ValueError("DataLoader payload digest mismatch")
    loops = py_rng.choice(LOOP_CHOICES)
    noise = torch.rand(x.numel(), model.embedding.embedding_dim, generator=generator)
    optimizer.zero_grad(set_to_none=True)
    logits = model(x, loops=loops, noise=noise)
    loss = F.cross_entropy(logits, y)
    if not torch.isfinite(loss.detach()):
        raise RuntimeError("Invalid CPU micro-LM optimizer loss")
    loss.backward()
    optimizer.step()
    cursor.ack_after_optimizer(idx, observed)
    return {
        "task_id": idx,
        "chunk_sha256": observed,
        "loop_count": loops,
        "noise_mask_sha256": digest((noise > 0.15).to(torch.uint8).tolist()),
        "loss": float(loss.detach()),
    }


def run_actual_workers(
    model, optimizer, cursor, py_rng, generator, *,
    tasks, start, count, context, require_prefetch=False
):
    """Return training trace, worker PID evidence and speculative read IDs.

    Uses public DataLoader mechanics and re-creates loader after restart.
    No internal _send_idx/_rcvd_idx, worker queues or private loader methods.
    """
    if count < 1 or start != cursor.committed or start + count > len(tasks):
        raise ValueError("Run would exceed tasks or start from wrong cursor")
    shared = context.Array("i", len(tasks), lock=True)
    loader = make_loader(tasks, start=start, counts=shared, context=context)
    iterator = iter(loader)
    traces, worker_pids, worker_ids = [], set(), set()
    fetched_but_unused = []
    try:
        for _ in range(count):
            batch = next(iterator)
            if int(batch["worker_pid"]) == os.getpid():
                raise RuntimeError("Expected subprocess, got main-process dataset execution")
            worker_pids.add(int(batch["worker_pid"]))
            worker_ids.add(int(batch["worker_id"]))
            traces.append(
                consume_one(model, optimizer, cursor, py_rng, generator, batch)
            )
        if require_prefetch:
            # Worker prefetch proceeds asynchronously. Observe real
            # __getitem__() reads AFTER committed step, without consuming
            # additional main-process batches. Fixed bound is a test timeout,
            # not a synchronization contract for production checkpoints.
            deadline = time.monotonic() + 5.0
            while True:
                snapshot = shared_read_snapshot(shared)
                fetched_but_unused = observed_unused_fetches(
                    snapshot, cursor.committed
                )
                if fetched_but_unused or time.monotonic() >= deadline:
                    break
                time.sleep(0.03)
            if not fetched_but_unused:
                raise RuntimeError(
                    "No real worker prefetch observed beyond optimizer commit; "
                    "cannot claim Gate H verified speculative work"
                )
    finally:
        # Closing iterator owns worker lifecycle. Deleting the short-lived
        # iterator/loader (persistent_workers=False) shuts down processes
        # through PyTorch's public object lifetime contract, not checkpoint.
        del iterator
        del loader
        gc.collect()
    if len(worker_pids) < WORKERS or worker_ids != {0, 1}:
        raise RuntimeError(
            "Did not observe two distinct OS worker processes and IDs"
        )
    return {
        "trace": traces,
        "worker_pids": sorted(worker_pids),
        "worker_ids": sorted(worker_ids),
        "prefetched_but_uncommitted_task_ids": fetched_but_unused,
        "reads_by_task": shared_read_snapshot(shared),
    }


def compare_actual_multiprocess_resume(
    tokenizer, contract, *, checkpoint_path, manifest_path,
    total=TOTAL_STEPS, cutoff=INTERRUPT_AFTER,
    records=None
):
    if not 0 < cutoff < total:
        raise ValueError("Invalid interruption point")
    if sys.platform != "linux":
        raise RuntimeError("Gate H is currently Linux Codespaces only")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    source_docs = records if records is not None else local_documents()
    train, heldout = split_documents(source_docs)
    fingerprint = require_real_tokenizer_identity(tokenizer, contract)
    tasks, source_sha = immutable_indexed_tasks(
        train, tokenizer, contract, n_tasks=max(
            total + EXTRA_INDEXED_TASKS, 32
        )
    )
    vocab = contract["fingerprint"]["len_tokenizer"]
    context = mp.get_context("spawn")

    def cursor():
        return DurableOptimizerCursor(
            tasks, source_sha, contract["fingerprint_sha256"]
        )

    full_model, full_opt, full_py, full_gen = new_training(vocab)
    continuous_cursor = cursor()
    continuous = run_actual_workers(
        full_model, full_opt, continuous_cursor, full_py, full_gen,
        tasks=tasks, start=0, count=total, context=context
    )

    interrupted_model, interrupted_opt, interrupted_py, interrupted_gen = (
        new_training(vocab)
    )
    interrupted_cursor = cursor()
    prefix = run_actual_workers(
        interrupted_model, interrupted_opt, interrupted_cursor,
        interrupted_py, interrupted_gen,
        tasks=tasks, start=0, count=cutoff, context=context,
        require_prefetch=True
    )
    uncommitted = prefix["prefetched_but_uncommitted_task_ids"]
    assert uncommitted and min(uncommitted) >= cutoff
    durable = interrupted_cursor.state_dict()
    if durable["next_committed_task_id"] != cutoff:
        raise AssertionError("Durable cursor drift before checkpoint")
    if "prefetched_task_ids" in durable or "last_dispatched_id" in durable:
        raise AssertionError("Do not persist speculative worker frontier")

    payload = training_bundle(
        contract, interrupted_model, interrupted_opt, interrupted_cursor,
        interrupted_py, interrupted_gen
    )
    save_bound_checkpoint(
        checkpoint_path, manifest_path, payload, contract, fingerprint
    )
    restored_model, restored_opt, restored_py, restored_gen = new_training(vocab)
    restored_cursor = cursor()
    persisted = safe_load_bound_checkpoint(
        checkpoint_path, manifest_path, contract, fingerprint
    )
    restore_bundle(
        persisted, restored_model, restored_opt, restored_cursor,
        restored_py, restored_gen
    )
    if restored_cursor.committed != cutoff:
        raise AssertionError("Commit cursor was not restored")
    suffix = run_actual_workers(
        restored_model, restored_opt, restored_cursor,
        restored_py, restored_gen,
        tasks=tasks, start=cutoff, count=total-cutoff, context=context
    )

    resumed = prefix["trace"] + suffix["trace"]
    trace_eq = continuous["trace"] == resumed
    model_eq = exact_optimizer_state_equal(
        full_model.state_dict(), restored_model.state_dict()
    )
    optim_eq = exact_optimizer_state_equal(
        full_opt.state_dict(), restored_opt.state_dict()
    )
    cursor_eq = continuous_cursor.state_dict() == restored_cursor.state_dict()
    rng_eq = (full_py.getstate() == restored_py.getstate()
              and torch.equal(full_gen.get_state(), restored_gen.get_state()))
    if not all((trace_eq, model_eq, optim_eq, cursor_eq, rng_eq)):
        raise AssertionError(
            "Real two-process DataLoader 12-step vs resumed 5+7 trajectories diverged"
        )
    # Worker assignment/PID after creating fresh DataLoader may change.
    # Never require same worker PID/ID for a given task on restart.
    return {
        "experiment": "R2 Gate H actual PyTorch DataLoader 2-process CPU resume",
        "data": "frozen indexed local synthetic PR27-shaped tokens; NOT HF FineWeb-Edu",
        "train_documents": len(train),
        "heldout_documents": len(heldout),
        "tokenizer_contract_sha256": contract["fingerprint_sha256"],
        "indexed_source_sha256": source_sha,
        "workers_requested": WORKERS,
        "actual_os_worker_processes_observed_per_run": {
            "continuous": continuous["worker_pids"],
            "interrupted": prefix["worker_pids"],
            "resumed": suffix["worker_pids"],
        },
        "worker_ids_seen_in_each_run": {
            "continuous": continuous["worker_ids"],
            "interrupted": prefix["worker_ids"],
            "resumed": suffix["worker_ids"],
        },
        "prefetch_factor": PREFETCH_FACTOR,
        "committed_steps_at_interruption": cutoff,
        "actual_worker_fetched_but_uncommitted": uncommitted,
        "wrong_resume_from_last_fetched_would_skip": uncommitted,
        "durable_cursor_at_interruption": durable,
        "first_resumed_task_id": suffix["trace"][0]["task_id"],
        "total_steps": total,
        "trace_bitwise_equal": trace_eq,
        "max_abs_loss_difference": max(
            abs(a["loss"]-b["loss"])
            for a, b in zip(continuous["trace"], resumed)
        ),
        "model_parameters_bitwise_equal": model_eq,
        "adamw_state_bitwise_equal": optim_eq,
        "committed_cursor_bitwise_equal": cursor_eq,
        "python_torch_rng_bitwise_equal": rng_eq,
        "actual_worker_processes": True,
        "crash_type": "controlled iterator interruption/recreation; no SIGKILL",
        "fineweb_data_consumed": False,
        "pr27_original_loader_modified": False,
        "gpu_training": "NOT_PERFORMED",
        "limitations": "Map-style pre-indexed synthetic dataset in two actual OS "
                       "workers with PyTorch's ordered DataLoader. It does NOT "
                       "prove real Hugging Face IterableDataset streaming, "
                       "prefetch queue checkpointing, shard resume, unordered "
                       "loading, or abrupt process crash atomicity.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--contract", default=
                   "research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    p.add_argument("--checkpoint", default=
                   "research/mini_mythos/results/r2/pr27_gate_h_real_loader_cpu.pt")
    p.add_argument("--manifest", default=
                   "research/mini_mythos/results/r2/pr27_gate_h_real_loader_cpu.manifest.json")
    p.add_argument("--out", default=
                   "research/mini_mythos/results/r2/pr27_gate_h_real_loader_comparison.json")
    args = p.parse_args()
    repo = get_repo(args.repo)
    results_dir = (repo / "research/mini_mythos/results").resolve()
    paths = [Path(s).resolve() for s in (
        args.contract, args.checkpoint, args.manifest, args.out
    )]
    if any(not path.is_relative_to(results_dir) for path in paths):
        p.error("All paths must reside inside research/mini_mythos/results")
    if any(path.exists() for path in paths[1:]):
        p.error("Gate H outputs already exist; refusing overwrite")
    contract = read_frozen_contract(paths[0], strict_gate=True)
    fp = contract["fingerprint"]
    tok = load_tokenizer(fp["identifier"], fp["pinned_revision"], offline=True)
    result = compare_actual_multiprocess_resume(
        tok, contract, checkpoint_path=paths[1], manifest_path=paths[2]
    )
    atomic_json(paths[3], result)
    print("Actual OS worker processes: 2 per real DataLoader run")
    for run, pids in result["actual_os_worker_processes_observed_per_run"].items():
        print(run, "worker PIDs:", pids)
    print("Committed frontier at checkpoint:", result["committed_steps_at_interruption"])
    print("Actually fetched but uncommitted:",
          result["actual_worker_fetched_but_uncommitted"])
    print("Naive last-fetched cursor would SKIP:",
          result["wrong_resume_from_last_fetched_would_skip"])
    print("First replayed task after resume:", result["first_resumed_task_id"])
    print("Trace bitwise identical:", result["trace_bitwise_equal"])
    print("Max abs loss difference:", result["max_abs_loss_difference"])
    print("Model params bitwise equal:", result["model_parameters_bitwise_equal"])
    print("AdamW state bitwise equal:", result["adamw_state_bitwise_equal"])
    print("Committed cursor bitwise equal:", result["committed_cursor_bitwise_equal"])
    print("Python/Torch RNG bitwise equal:", result["python_torch_rng_bitwise_equal"])
    print("Data source: LOCAL INDEXED SYNTHETIC, NOT FINEWEB")
    print("Actual PR27 streaming loader patched:", False)
    print("GPU training:", "NOT_PERFORMED")
    print("Saved:", paths[3])


if __name__ == "__main__":
    main()
