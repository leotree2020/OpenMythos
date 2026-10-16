#!/usr/bin/env python3
"""R2 Gate K: actual HF IterableDataset worker SHARD-THEN-PACK resume.

Unlike Gate J, this offline study puts a *locally constructed* Hugging Face
IterableDataset inside TWO actual PyTorch DataLoader OS workers. HF's own
worker-aware __iter__ automatically shards data exactly once; each worker
THEN independently tokenizes,
appends EOS, and packs seq_len+1 chunks (as PR27 experiments/data.py does).

Data are the EXACT frozen 32-document Gate I REAL FineWeb source, but are
materialized locally before loading: NO live HF Parquet streaming, shard file
offsets or external requests. The HF source contains only two local Arrow
shards, not original 2410 remote files; task/document order can differ from
production. No original PR27 source is modified.

A safe research-only checkpoint commits a GLOBAL BATCH count + actual
consumed chunk SHA list with model/AdamW/RNG. Restart rebuilds workers from
the beginning and verifies all N already committed chunk SHA values as it
skips them. This is O(N) replay, appropriate only for the tiny snapshot.
Prefetched-but-uncommitted chunks are intentionally discarded.

Compares 12 uninterrupted CPU toy AdamW steps against 5 + resumed 7;
observes actual worker PIDs, worker prefetch and checks bitwise equality.
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
from torch.utils.data import DataLoader, IterableDataset, get_worker_info

from common import atomic_json, commit_id, get_repo
from r2_fineweb_local_replay import (
    TOKENIZER_CONTRACT_SHA256, TOKENIZER_REVISION, verified_real_records,
)
from r2_pr27_guarded_checkpoint import (
    read_frozen_contract, require_real_tokenizer_identity,
    safe_load_bound_checkpoint, save_bound_checkpoint,
)
from r2_pr27_prefetch_commit import immutable_indexed_tasks
from r2_pr27_stream_resume import (
    CHUNK_LEN, LOOP_CHOICES, digest, exact_optimizer_state_equal,
    new_training, restore_bundle, split_documents, training_bundle,
)
from r2_pr27_tokenizer_contract import load_tokenizer


PROTOCOL = "R2_GATE_K_LOCAL_HF_ITERABLE_WORKER_SHARD_PACK_V1"
WORKERS = 2
PREFETCH_FACTOR = 2
TOTAL_STEPS = 12
CUTOFF = 5


class HFWorkerShardPacker(IterableDataset):
    """HF-native worker auto-sharding followed by PR27-style worker-local packing.

    The HF IterableDataset is built in the main process with two Arrow shards.
    Its __iter__ calls _iter_pytorch() under DataLoader workers and distributes
    one shard to each worker. Explicitly calling .shard(2, worker_id) here
    reduces to 1 shard and HF would AUTO-SHARD that AGAIN for 2 workers,
    stopping one process. Do not double shard; no child accesses HF network.
    """

    def __init__(self, local_hf_source, tokenizer, seq_len, read_counts):
        super().__init__()
        if not isinstance(seq_len, int) or seq_len < 2:
            raise ValueError("Invalid local sequence length")
        if len(read_counts) != WORKERS:
            raise ValueError("Read counters must identify two real workers")
        self.source = local_hf_source
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.counts = read_counts
        self.eos_id = int(tokenizer.eos_token_id)

    def __iter__(self):
        worker = get_worker_info()
        if worker is None or worker.num_workers != WORKERS:
            raise RuntimeError("Gate K requires two real PyTorch worker processes")
        worker_id = worker.id
        # HF's native IterableDataset.__iter__ detects PyTorch worker_info
        # and calls _iter_pytorch(), which partitions the two Arrow shards
        # BEFORE yielding documents. An explicit .shard() here causes DOUBLE
        # SHARDING and prematurely stops one of the two workers.
        if self.source.num_shards != WORKERS:
            raise RuntimeError(
                "Gate K requires exactly two source shards for HF native "
                "DataLoader worker partition"
            )
        buffer = []
        need = self.seq_len + 1
        local_chunk_index = 0
        for document in self.source:
            text = document.get("text", "")
            if not text:
                continue
            ids = self.tokenizer.encode(text, add_special_tokens=False)
            ids.append(self.eos_id)
            buffer.extend(ids)
            while len(buffer) >= need:
                chunk = buffer[:need]
                buffer = buffer[need - 1:]
                x = torch.tensor(chunk[:-1], dtype=torch.long)
                y = torch.tensor(chunk[1:], dtype=torch.long)
                checksum = digest({"x": chunk[:-1], "y": chunk[1:]})
                with self.counts.get_lock():
                    self.counts[worker_id] += 1
                yield {
                    "x": x, "y": y,
                    "chunk_sha256": checksum,
                    "worker_id": worker_id,
                    "worker_local_chunk_index": local_chunk_index,
                    "worker_pid": os.getpid(),
                }
                local_chunk_index += 1


class CommittedHFStream:
    """Global committed optimizer batch frontier + verified replay digests."""

    def __init__(self, *, source_sha, contract_sha, seq_len):
        for name, sha in (("source", source_sha), ("tokenizer", contract_sha)):
            if not isinstance(sha, str) or len(sha) != 64:
                raise ValueError("Invalid " + name + " sha")
        self.source_sha = source_sha
        self.contract_sha = contract_sha
        self.seq_len = seq_len
        self.committed = []

    @property
    def emitted(self):
        return len(self.committed)

    def state_dict(self):
        body = {
            "protocol": PROTOCOL,
            "source_sha256": self.source_sha,
            "tokenizer_contract_sha256": self.contract_sha,
            "num_workers": WORKERS,
            "prefetch_factor": PREFETCH_FACTOR,
            "in_order": True,
            "seq_len": self.seq_len,
            "next_committed_global_batch": self.emitted,
            "emitted_chunks": self.emitted,
            "committed_chunk_sha256": list(self.committed),
        }
        return dict(body, state_sha256=digest(body))

    def load_state_dict(self, state, *, strict_replay=True):
        if not isinstance(state, dict):
            raise ValueError("Committed HF data cursor missing")
        body = dict(state)
        signature = body.pop("state_sha256", None)
        if signature != digest(body):
            raise ValueError("Committed HF data cursor checksum mismatch")
        current = self.state_dict()
        for key in (
            "protocol", "source_sha256", "tokenizer_contract_sha256",
            "num_workers", "prefetch_factor", "in_order", "seq_len"
        ):
            if body.get(key) != current[key]:
                raise ValueError("Data/tokenizer/worker policy mismatch: " + key)
        n = body.get("next_committed_global_batch")
        chunks = body.get("committed_chunk_sha256")
        if (
            not isinstance(n, int) or n < 0 or
            body.get("emitted_chunks") != n or
            not isinstance(chunks, list) or len(chunks) != n or
            any(not isinstance(v, str) or len(v) != 64 for v in chunks)
        ):
            raise ValueError("Committed HF cursor chunks invalid")
        # Each consumed chunk is checked AGAINST THE NEW real worker output
        # on resume; this prevents accepting changed byte/token order.
        self.committed = list(chunks)

    def ack(self, global_batch_id, checksum):
        if global_batch_id != self.emitted:
            raise ValueError("Optimizer can commit only next sequential batch")
        if not isinstance(checksum, str) or len(checksum) != 64:
            raise ValueError("Invalid committed chunk SHA")
        self.committed.append(checksum)


def build_local_hf_source(records):
    """HF datasets *locally* constructed, exactly two iterable Arrow shards."""
    from datasets import Dataset
    if not records or len({r["id"] for r in records}) != len(records):
        raise ValueError("Local source has no records or duplicate IDs")
    # Only a stable hash is used for audit, never output any actual text/ID.
    source = Dataset.from_dict({
        "text": [r["text"] for r in records],
        "source_doc_hash": [digest(r["id"]) for r in records],
    }).to_iterable_dataset(num_shards=WORKERS)
    if source.num_shards != WORKERS:
        raise RuntimeError("HF did not create exactly 2 iterable Arrow shards")
    return source


def audit_local_hf_worker_partition(source, expected_ids):
    """Check no duplicate/missing source rows under HF's native shard policy.

    The worker-aware HF IterableDataset iterator uses contiguous=False
    when distributing dataset Arrow shards to PyTorch workers.
    We audit precisely those shards outside workers, WITHOUT storing text.
    """
    if source.num_shards != WORKERS:
        raise ValueError("Source must expose exactly two native HF shards")
    expected = [digest(v) for v in expected_ids]
    if len(set(expected)) != len(expected):
        raise ValueError("Duplicate expected source ID")
    shard_hashes = []
    for worker_id in range(WORKERS):
        part = source.shard(
            num_shards=WORKERS, index=worker_id, contiguous=False
        )
        # Note: this .shard() is for MAIN-PROCESS AUDIT ONLY. The actual
        # DataLoader workers must iterate unmodified self.source.
        if part.num_shards != 1:
            raise RuntimeError("Unexpected HF shard count in partition audit")
        ids = [row["source_doc_hash"] for row in part]
        if not ids:
            raise ValueError("HF worker assigned an empty source partition")
        shard_hashes.append(ids)
    flattened = [v for part in shard_hashes for v in part]
    if len(flattened) != len(expected) or set(flattened) != set(expected):
        raise ValueError("HF native worker partitions omit or duplicate documents")
    if set(shard_hashes[0]) & set(shard_hashes[1]):
        raise ValueError("HF native worker partitions overlap")
    return {
        "partition_policy": "HF_ITERABLE_DATASET_NATIVE_AUTOSHARD_ON_TORCH_WORKERS",
        "dataset_source_shards": WORKERS,
        "per_worker_document_counts": [len(x) for x in shard_hashes],
        "all_source_doc_ids_covered_once": True,
        "source_doc_id_hashes_sha256": digest(sorted(flattened)),
    }


def run_real_hf_workers(
    model, optimizer, cursor, py_rng, gen,
    *, source, tokenizer, steps, replay_committed=0,
    require_prefetch=False
):
    if steps < 1 or replay_committed < 0:
        raise ValueError("Invalid Gate K worker run length")
    ctx = mp.get_context("spawn")
    counts = ctx.Array("i", WORKERS, lock=True)
    loader = DataLoader(
        HFWorkerShardPacker(source, tokenizer, cursor.seq_len, counts),
        batch_size=None, num_workers=WORKERS,
        prefetch_factor=PREFETCH_FACTOR,
        in_order=True, persistent_workers=False,
        multiprocessing_context=ctx, timeout=30
    )
    iterator = iter(loader)
    committed_before = list(cursor.committed)
    if replay_committed != len(committed_before):
        raise ValueError("Resume must replay ALL previously committed batches")
    trace, used_pids, used_workers = [], set(), set()
    fetched_uncommitted_count = 0
    try:
        # A restarted worker reads from the beginning; only the main process
        # uses checkpoint committed checksum list for deterministic replay.
        for i in range(replay_committed):
            row = next(iterator)
            if row["chunk_sha256"] != committed_before[i]:
                raise ValueError(
                    f"Resumed HF worker-shard token order drift at batch {i}"
                )
            used_pids.add(int(row["worker_pid"]))
            used_workers.add(int(row["worker_id"]))
        for _ in range(steps):
            row = next(iterator)
            worker_pid = int(row["worker_pid"])
            if worker_pid == os.getpid():
                raise RuntimeError("Expected genuine worker subprocess")
            used_pids.add(worker_pid)
            used_workers.add(int(row["worker_id"]))
            x, y = row["x"], row["y"]
            chunk_sha = digest({"x": x.tolist(), "y": y.tolist()})
            if chunk_sha != row["chunk_sha256"]:
                raise ValueError("Worker token payload checksum mismatch")
            idx = cursor.emitted
            loops = py_rng.choice(LOOP_CHOICES)
            noise = torch.rand(x.numel(), model.embedding.embedding_dim,
                               generator=gen)
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(model(x, loops=loops, noise=noise), y)
            if not torch.isfinite(loss.detach()):
                raise RuntimeError("Nonfinite Gate K tiny CPU loss")
            loss.backward()
            optimizer.step()
            cursor.ack(idx, chunk_sha)
            trace.append({
                "global_batch_id": idx,
                "chunk_sha256": chunk_sha,
                "loop_count": loops,
                "noise_sha256": digest(
                    (noise > 0.15).to(torch.uint8).tolist()
                ),
                "loss": float(loss.detach()),
            })
        if require_prefetch:
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                with counts.get_lock():
                    fetched = sum(counts[:])
                if fetched > cursor.emitted:
                    break
                time.sleep(0.03)
            with counts.get_lock():
                fetched_uncommitted_count = sum(counts[:]) - cursor.emitted
            if fetched_uncommitted_count < 1:
                raise RuntimeError(
                    "No genuine HF IterableDataset worker prefetch observed"
                )
    finally:
        del iterator
        del loader
        gc.collect()
    if len(used_pids) != WORKERS or used_workers != {0, 1}:
        raise RuntimeError("Missing one of two actual DataLoader worker PIDs")
    return {
        "trace": trace,
        "worker_pids": sorted(used_pids),
        "worker_ids": sorted(used_workers),
        "worker_fetched_uncommitted_count": fetched_uncommitted_count,
    }


def compare_worker_shard_resume(
    tokenizer, contract, records, *, checkpoint_path, manifest_path,
    snapshot_sha, steps=TOTAL_STEPS, cutoff=CUTOFF
):
    if sys.platform != "linux":
        raise RuntimeError("Gate K runs only in Linux Codespaces")
    if not 0 < cutoff < steps:
        raise ValueError("Invalid checkpoint step")
    if not isinstance(snapshot_sha, str) or len(snapshot_sha) != 64:
        raise ValueError("Invalid frozen source SHA")
    fingerprint = require_real_tokenizer_identity(tokenizer, contract)
    train, excluded = split_documents(records)
    source = build_local_hf_source(train)
    source_audit = audit_local_hf_worker_partition(
        source, [r["id"] for r in train]
    )
    vocab = contract["fingerprint"]["len_tokenizer"]
    torch.set_num_threads(min(4, torch.get_num_threads()))

    def cursor():
        return CommittedHFStream(
            source_sha=snapshot_sha,
            contract_sha=contract["fingerprint_sha256"], seq_len=CHUNK_LEN
        )

    full_model, full_opt, full_py, full_gen = new_training(vocab)
    full_cur = cursor()
    continuous = run_real_hf_workers(
        full_model, full_opt, full_cur, full_py, full_gen,
        source=source, tokenizer=tokenizer, steps=steps
    )

    prefix_model, prefix_opt, prefix_py, prefix_gen = new_training(vocab)
    prefix_cur = cursor()
    prefix = run_real_hf_workers(
        prefix_model, prefix_opt, prefix_cur, prefix_py, prefix_gen,
        source=source, tokenizer=tokenizer, steps=cutoff,
        require_prefetch=True
    )
    prefetch_count = prefix["worker_fetched_uncommitted_count"]
    payload = training_bundle(
        contract, prefix_model, prefix_opt, prefix_cur, prefix_py, prefix_gen
    )
    save_bound_checkpoint(
        checkpoint_path, manifest_path, payload, contract, fingerprint
    )

    resumed_model, resumed_opt, resumed_py, resumed_gen = new_training(vocab)
    resumed_cur = cursor()
    saved = safe_load_bound_checkpoint(
        checkpoint_path, manifest_path, contract, fingerprint
    )
    restore_bundle(
        saved, resumed_model, resumed_opt, resumed_cur,
        resumed_py, resumed_gen
    )
    suffix = run_real_hf_workers(
        resumed_model, resumed_opt, resumed_cur,
        resumed_py, resumed_gen,
        source=source, tokenizer=tokenizer,
        steps=steps-cutoff, replay_committed=cutoff
    )
    expected = continuous["trace"]
    observed = prefix["trace"] + suffix["trace"]
    trace_equal = expected == observed
    model_equal = exact_optimizer_state_equal(
        full_model.state_dict(), resumed_model.state_dict()
    )
    optimizer_equal = exact_optimizer_state_equal(
        full_opt.state_dict(), resumed_opt.state_dict()
    )
    cursor_equal = full_cur.state_dict() == resumed_cur.state_dict()
    rng_equal = (
        full_py.getstate() == resumed_py.getstate() and
        torch.equal(full_gen.get_state(), resumed_gen.get_state())
    )
    if not all((trace_equal, model_equal, optimizer_equal,
                cursor_equal, rng_equal)):
        raise AssertionError("HF shard-then-pack worker resume diverged")
    # Contrast with Gate J's pack-before-shard topology on exact same docs.
    global_tasks, global_source_sha = immutable_indexed_tasks(
        train, tokenizer, contract, n_tasks=steps
    )
    mismatched = sum(
        a["chunk_sha256"] != b["chunk_sha256"]
        for a, b in zip(global_tasks, expected)
    )
    if mismatched == 0:
        raise AssertionError(
            "Global pack and worker-local pack unexpectedly share identical "
            "all-step trace; topology control did not discriminate"
        )
    return {
        "experiment": "R2 Gate K true worker-local HF IterableDataset sharding on frozen local real text",
        "hf_dataset_kind": "LOCAL Arrow-generated HF IterableDataset, NOT remote streaming Parquet",
        "source_snapshot_sha256": snapshot_sha,
        "source_license_metadata": "from fixed Gate I local snapshot",
        "tokenizer_contract_sha256": contract["fingerprint_sha256"],
        "source_documents": len(records),
        "development_training_documents": len(train),
        "excluded_documents_not_evaluated": len(excluded),
        "actual_os_workers": WORKERS,
        "worker_pids": {
            "continuous": continuous["worker_pids"],
            "interrupted": prefix["worker_pids"],
            "resumed": suffix["worker_pids"],
        },
        "local_hf_source_shards": WORKERS,
        "hf_native_auto_shard_audit": source_audit,
        "upstream_explicit_shard_double_partition_risk": True,
        "checkpoint_optimizer_committed_batches": cutoff,
        "worker_local_prefetched_but_uncommitted_count": prefetch_count,
        "first_resumed_global_batch": suffix["trace"][0]["global_batch_id"],
        "continuous_vs_resumed_trace_bitwise_equal": trace_equal,
        "maximum_absolute_loss_difference": max(
            abs(a["loss"] - b["loss"])
            for a, b in zip(expected, observed)
        ),
        "model_params_bitwise_equal": model_equal,
        "adamw_state_bitwise_equal": optimizer_equal,
        "committed_cursor_bitwise_equal": cursor_equal,
        "python_torch_rng_bitwise_equal": rng_equal,
        "global_pack_vs_worker_shard_pack_mismatched_first_n_chunks": mismatched,
        "global_pack_source_sha256": global_source_sha,
        "exact_PR27_source_unchanged": True,
        "hf_live_streaming_used": False,
        "official_quality_evaluation": False,
        "tiny_cpu_adamw_steps": steps,
        "gpu_training": False,
        "limitations": "Replay starts source from beginning and skips committed "
                       "batches with chunk-SHA checks; O(N), not scalable "
                       "stateful shard seek. Local 2 Arrow shards do not "
                       "represent upstream 2410 files, no SIGKILL, no CUDA.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--source", default=
                   "research/mini_mythos/results/r2/fineweb_gate_i_32")
    p.add_argument("--contract", default=
                   "research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    p.add_argument("--checkpoint", default=
                   "research/mini_mythos/results/r2/pr27_gate_k_worker_pack_cpu.pt")
    p.add_argument("--manifest", default=
                   "research/mini_mythos/results/r2/pr27_gate_k_worker_pack_cpu.manifest.json")
    p.add_argument("--out", default=
                   "research/mini_mythos/results/r2/pr27_gate_k_worker_pack_report.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    result_root = (root / "research/mini_mythos/results").resolve()
    paths = [Path(z).resolve() for z in (
        a.source, a.contract, a.checkpoint, a.manifest, a.out
    )]
    if any(not z.is_relative_to(result_root) for z in paths):
        p.error("All paths must remain in Git-ignored research results directory")
    if any(z.exists() for z in paths[2:]):
        p.error("Gate K evidence already exists; refusing overwrite")
    source, records = verified_real_records(paths[0])
    contract = read_frozen_contract(paths[1], strict_gate=True)
    if (contract["fingerprint_sha256"] != TOKENIZER_CONTRACT_SHA256 or
            contract["fingerprint"]["pinned_revision"] != TOKENIZER_REVISION):
        raise ValueError("Unexpected frozen GPT2 contract")
    tok = load_tokenizer("gpt2", TOKENIZER_REVISION, offline=True)
    report = compare_worker_shard_resume(
        tok, contract, records,
        checkpoint_path=paths[2], manifest_path=paths[3],
        snapshot_sha=source["snapshot_sha256"]
    )
    report["git_commit"] = commit_id(root)
    atomic_json(paths[4], report)
    print("Source: REAL FineWeb-Edu 32-document frozen LOCAL snapshot")
    print("Source SHA:", report["source_snapshot_sha256"])
    print("HF IterableDataset: LOCAL two Arrow shards, NOT live Parquet")
    print("Partition policy:", report["hf_native_auto_shard_audit"]["partition_policy"])
    print("Source docs covered once:", report["hf_native_auto_shard_audit"]["all_source_doc_ids_covered_once"])
    print("Worker source document counts:", report["hf_native_auto_shard_audit"]["per_worker_document_counts"])
    for name, pids in report["worker_pids"].items():
        print(name, "real Worker PIDs:", pids)
    print("Optimizer committed frontier:", report["checkpoint_optimizer_committed_batches"])
    print("Real worker-prefetched but uncommitted count:",
          report["worker_local_prefetched_but_uncommitted_count"])
    print("First resumed global batch:", report["first_resumed_global_batch"])
    print("Global-pack vs shard-then-pack differing chunks:",
          report["global_pack_vs_worker_shard_pack_mismatched_first_n_chunks"])
    print("Bitwise equal trace:", report["continuous_vs_resumed_trace_bitwise_equal"])
    print("Max abs loss difference:", report["maximum_absolute_loss_difference"])
    print("Model parameters equal:", report["model_params_bitwise_equal"])
    print("AdamW equal:", report["adamw_state_bitwise_equal"])
    print("Commit cursor equal:", report["committed_cursor_bitwise_equal"])
    print("Python/Torch RNG equal:", report["python_torch_rng_bitwise_equal"])
    print("Original HF remote streaming resumed:", False)
    print("Model-quality evaluation:", "NOT_PERFORMED")
    print("GPU training:", "NOT_PERFORMED")
    print("Saved:", paths[4])


if __name__ == "__main__":
    main()
