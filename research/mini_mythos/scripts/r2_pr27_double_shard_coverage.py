#!/usr/bin/env python3
"""R2 Gate L: real dual-worker test of PR27-like double-shard data loss.

OFFLINE: verify already-pinned real FineWeb snapshot, then pass ONLY
hashed document identities to 8 local HF Arrow shards. Compare PyTorch
DataLoader(num_workers=2) with native HF auto-shard against explicit
shard(2,worker_id) followed by HF auto-shard inside each OS subprocess.

No real text leaves source validation, no new Hub requests, no model
training, no GPU. This is NOT a measured production FineWeb loss rate.
"""
import argparse
import gc
import multiprocessing as mp
import os
from pathlib import Path
import sys

from torch.utils.data import DataLoader, IterableDataset, get_worker_info

from common import atomic_json, commit_id, get_repo
from r2_fineweb_local_replay import verified_real_records
from r2_pr27_stream_resume import digest, split_documents


PROTOCOL = "R2_GATE_L_PR27_DOUBLE_SHARD_COVERAGE_V1"
WORKERS = 2
SHARDS = 8
PREFETCH = 2
MODES = ("native_once", "explicit_twice")


def make_digest_source(records):
    """8 local Arrow shards with stable source hashes, NEVER source text."""
    from datasets import Dataset
    if len(records) < SHARDS:
        raise ValueError("Insufficient source records for eight shards")
    hashes = [digest(r["id"]) for r in records]
    if len(set(hashes)) != len(hashes):
        raise ValueError("Duplicate source record identities")
    source = Dataset.from_dict({"source_digest": hashes}).to_iterable_dataset(
        num_shards=SHARDS
    )
    if source.num_shards != SHARDS:
        raise ValueError("Unexpected HF IterableDataset source shard count")
    return source, hashes


class CoverageProbe(IterableDataset):
    """Each true PyTorch worker may explicitly shard before HF auto-shards."""

    def __init__(self, source, mode):
        super().__init__()
        if mode not in MODES or source.num_shards != SHARDS:
            raise ValueError("Invalid source or partition policy")
        self.source = source
        self.mode = mode

    def __iter__(self):
        info = get_worker_info()
        if info is None or info.num_workers != WORKERS:
            raise RuntimeError("Gate L requires two REAL subprocess workers")
        view = self.source
        if self.mode == "explicit_twice":
            view = view.shard(num_shards=WORKERS, index=info.id)
        # Now HF IterableDataset.__iter__ triggers its own _iter_pytorch
        # worker-aware auto-sharding when iterated in this subprocess.
        for row in view:
            yield {
                "source_digest": row["source_digest"],
                "worker_id": info.id,
                "worker_pid": os.getpid(),
                "visible_shards_before_auto": view.num_shards,
            }


def collect_worker_coverage(source, mode):
    if sys.platform != "linux":
        raise RuntimeError("Gate L Linux Codespaces-only")
    if mode not in MODES:
        raise ValueError("Invalid partition mode")
    ctx = mp.get_context("spawn")
    loader = DataLoader(
        CoverageProbe(source, mode),
        batch_size=None, num_workers=WORKERS, prefetch_factor=PREFETCH,
        in_order=True, persistent_workers=False,
        multiprocessing_context=ctx, timeout=30
    )
    iterator = iter(loader)
    records, worker_pids = [], {}
    try:
        for row in iterator:
            worker_id = int(row["worker_id"])
            pid = int(row["worker_pid"])
            ident = row["source_digest"]
            if worker_id not in (0, 1) or pid == os.getpid():
                raise RuntimeError("Missing actual subprocess identity")
            if worker_id in worker_pids and worker_pids[worker_id] != pid:
                raise RuntimeError("Worker PID unexpectedly changed")
            if not isinstance(ident, str) or len(ident) != 64:
                raise ValueError("Unexpected document SHA")
            worker_pids[worker_id] = pid
            records.append({
                "doc": ident, "worker": worker_id,
                "before_auto": int(row["visible_shards_before_auto"])
            })
    finally:
        del iterator
        del loader
        gc.collect()
    if set(worker_pids) != {0, 1} or len(set(worker_pids.values())) != 2:
        raise RuntimeError("Both real OS Worker PIDs required")
    return records, {str(i): worker_pids[i] for i in sorted(worker_pids)}


def summarize(expected, records, pids):
    if len(set(expected)) != len(expected):
        raise ValueError("Expected document IDs are not unique")
    got = [x["doc"] for x in records]
    if len(got) != len(set(got)):
        raise ValueError("Same document emitted multiple times")
    known = set(expected)
    if not set(got).issubset(known):
        raise ValueError("Worker emitted unknown source document")
    missing = known - set(got)
    per_worker = {
        str(i): sum(x["worker"] == i for x in records)
        for i in range(WORKERS)
    }
    if not all(per_worker.values()):
        raise RuntimeError("A worker produced no source documents")
    return {
        "expected_docs": len(expected),
        "observed_docs": len(got),
        "missing_docs": len(missing),
        "missing_source_order_indices": [
            i for i, h in enumerate(expected) if h in missing
        ],
        "duplicate_docs": len(got) - len(set(got)),
        "unknown_docs": len(set(got) - known),
        "per_worker_document_counts": per_worker,
        "actual_worker_pids": pids,
        "source_shards_before_hf_auto": sorted(set(
            x["before_auto"] for x in records
        )),
        "all_docs_covered_once": not missing and len(got) == len(expected),
        "covered_doc_digest_set_sha256": digest(sorted(set(got))),
    }


def compare_modes(
    records, *, source_sha, revision,
    expected_train=28, expected_excluded=4,
):
    """Both true worker experiments use exactly the SAME frozen identities.

    The CLI freezes 28/4 from real Gate I. Optional expected counts exist
    solely for tests with synthetic, never-sourced-from-HF fixture IDs.
    """
    if not isinstance(source_sha, str) or len(source_sha) != 64:
        raise ValueError("Frozen source digest missing")
    if not isinstance(revision, str) or len(revision) != 40:
        raise ValueError("Frozen source version missing")
    train, excluded = split_documents(records)
    if len(train) != expected_train or len(excluded) != expected_excluded:
        raise ValueError("Gate L source partition count differs from frozen protocol")
    source, expected = make_digest_source(train)
    native_rows, native_pids = collect_worker_coverage(source, "native_once")
    double_rows, double_pids = collect_worker_coverage(
        source, "explicit_twice"
    )
    native = summarize(expected, native_rows, native_pids)
    twice = summarize(expected, double_rows, double_pids)
    if not native["all_docs_covered_once"]:
        raise AssertionError("HF native one-time sharding lost a source document")
    if twice["missing_docs"] == 0 or twice["observed_docs"] >= len(expected):
        raise AssertionError("Double-shard silent-loss control did not fire")
    if twice["source_shards_before_hf_auto"] != [SHARDS // WORKERS]:
        raise AssertionError("Manual shard step did not reduce shard count")
    return {
        "protocol": PROTOCOL,
        "source_kind": "OFFLINE immutable Gate I REAL FineWeb text; HASHES only in workers",
        "dataset_revision": revision,
        "snapshot_sha256": source_sha,
        "source_document_count": len(records),
        "internal_training_docs": len(train),
        "excluded_docs_not_scored": len(excluded),
        "local_arrow_shards": SHARDS,
        "real_os_workers_per_arm": WORKERS,
        "native_hf_auto_once": native,
        "upstream_style_explicit_plus_hf_auto": twice,
        "counterexample_demonstrated": True,
        "true_remote_parquet_coverage_measured": False,
        "original_pr27_modified": False,
        "no_model_training": True,
        "gpu_training": False,
        "limitations": "8 local Arrow shards of real source ID hashes; NOT "
                       "a measurement of the missing fraction in original "
                       "FineWeb-Edu streamed Parquet files.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--source", default=
                   "research/mini_mythos/results/r2/fineweb_gate_i_32")
    p.add_argument("--out", default=
                   "research/mini_mythos/results/r2/pr27_gate_l_double_shard_coverage.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    base = (root / "research/mini_mythos/results").resolve()
    src, out = Path(a.source).resolve(), Path(a.out).resolve()
    if not src.is_relative_to(base) or not out.is_relative_to(base):
        p.error("All paths must be inside Git-ignored research results")
    if out.exists():
        p.error("Gate L result already exists; refusing overwrite")
    # validate external immutable source SHA and every JSONL entry first
    provenance, records = verified_real_records(src)
    report = compare_modes(
        records, source_sha=provenance["snapshot_sha256"],
        revision=provenance["revision"]
    )
    report["github_revision"] = commit_id(root)
    atomic_json(out, report)
    print("Source: verified REAL FineWeb local snapshot; workers get only ID hashes")
    print("Local Arrow shards:", report["local_arrow_shards"])
    print("Native Worker PIDs:", report["native_hf_auto_once"]["actual_worker_pids"])
    print("Double-shard Worker PIDs:",
          report["upstream_style_explicit_plus_hf_auto"]["actual_worker_pids"])
    print("Native source document coverage:",
          report["native_hf_auto_once"]["observed_docs"], "of",
          report["native_hf_auto_once"]["expected_docs"])
    print("Native covered once:", report["native_hf_auto_once"]["all_docs_covered_once"])
    print("Explicit + HF auto coverage:",
          report["upstream_style_explicit_plus_hf_auto"]["observed_docs"],
          "of", report["upstream_style_explicit_plus_hf_auto"]["expected_docs"])
    print("SILENT missing source documents:",
          report["upstream_style_explicit_plus_hf_auto"]["missing_docs"])
    print("Missing internal-train-order indices:",
          report["upstream_style_explicit_plus_hf_auto"]["missing_source_order_indices"])
    print("Both real worker PIDs seen in each path: True")
    print("No online HF requests, no source text sent, no training, no GPU")
    print("Upstream PR27 modified: False")
    print("Saved:", out)


if __name__ == "__main__":
    main()
