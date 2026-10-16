#!/usr/bin/env python3
"""R2 Gate J: REAL frozen FineWeb-Edu TEXT through real two-worker CPU replay.

OFFLINE ONLY. Requires the exact previously frozen Gate I 32-document
JSONL + manifest from HF sample-10BT/train and the Gate D pinned GPT2
tokenizer already present in Codespaces. Does not fetch HF data/model
weights. Validates external fixed source SHA/revision *before* using text.

Converts the ordered 32 real source records to deterministic document IDs
without leaking text into results. Reuses Gate H's independently verified
PyTorch DataLoader(num_workers=2, prefetch_factor=2) CPU test: compare
uninterrupted 12 AdamW steps to committed-step-5 + 7-step checkpoint resume,
including actual subprocess worker PIDs, fetched/uncommitted task evidence,
model/optimizer/RNG/cursor and per-step digest equality.

A fixed ID-hash partition is ONLY for protocol isolation; it is NOT an
official FineWeb heldout set and no model-quality NLL/PPL is reported.
The real upstream HF IterableDataset/shard cursor is NOT exercised;
this is indexed replay of a local verified SOURCE SNAPSHOT.
"""
import argparse
from pathlib import Path

from common import atomic_json, commit_id, get_repo
from r2_fineweb_source_snapshot import (
    DATASET_CONFIG, DATASET_ID, DATASET_SPLIT, SELECTED_DOCS,
    read_verified_snapshot,
)
from r2_pr27_guarded_checkpoint import read_frozen_contract
from r2_pr27_real_dataloader_resume import compare_actual_multiprocess_resume
from r2_pr27_stream_resume import digest, split_documents
from r2_pr27_tokenizer_contract import load_tokenizer

SOURCE_REVISION = "87f09149ef4734204d70ed1d046ddc9ca3f2b8f9"
SOURCE_SNAPSHOT_SHA256 = "dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1"
TEXT_BYTES = 111361
SNAPSHOT_BYTES = 119588
TOKENIZER_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
TOKENIZER_CONTRACT_SHA256 = "d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9"
PROTOCOL = "R2_GATE_J_REAL_SOURCE_LOCAL_INDEXED_CPU_REPLAY_V1"


def verified_real_records(
    snapshot_dir, *, expected_revision=SOURCE_REVISION,
    expected_sha=SOURCE_SNAPSHOT_SHA256,
    expected_text_bytes=TEXT_BYTES,
    expected_snapshot_bytes=SNAPSHOT_BYTES,
):
    """Load full verified Gate I snapshot, then require external pinned IDs.

    Injection of expected provenance is ONLY for isolated synthetic tests.
    The CLI always uses constants above from the actual Gate I evidence.
    """
    manifest, rows = read_verified_snapshot(snapshot_dir)
    if (manifest["source"] != DATASET_ID or
            manifest["config"] != DATASET_CONFIG or
            manifest["split"] != DATASET_SPLIT):
        raise ValueError("Gate J FineWeb source/config/split mismatch")
    if manifest["resolved_revision"] != expected_revision:
        raise ValueError("Gate J source revision differs from Gate I frozen SHA")
    if manifest["snapshot_sha256"] != expected_sha:
        raise ValueError("Gate J source snapshot SHA differs from Gate I evidence")
    if (manifest["snapshot_bytes"] != expected_snapshot_bytes or
            manifest["capture_stats"]["selected_text_bytes"] != expected_text_bytes):
        raise ValueError("Gate J frozen text or snapshot byte count drift")
    if (len(rows) != SELECTED_DOCS or
            manifest["capture_stats"]["rows_scanned"] != SELECTED_DOCS or
            [r["source_row_index"] for r in rows] != list(range(SELECTED_DOCS))):
        raise ValueError("Gate J selected row sequence differs from 32-document Gate I")
    if manifest.get("source_license_metadata") != "odc-by":
        raise ValueError("Gate J FineWeb dataset license metadata differs from Gate I")
    records = [
        {
            "id": (
                "fineweb-gate-j:" + expected_revision + ":" +
                str(row["source_row_index"]) + ":" + row["text_sha256"]
            ),
            "text": row["text"],
        }
        for row in rows
    ]
    if len({r["id"] for r in records}) != SELECTED_DOCS:
        raise ValueError("Gate J duplicate source document IDs")
    return {
        "dataset": DATASET_ID, "config": DATASET_CONFIG,
        "split": DATASET_SPLIT, "revision": expected_revision,
        "snapshot_sha256": expected_sha,
        "snapshot_bytes": expected_snapshot_bytes,
        "text_bytes": expected_text_bytes,
        "license_metadata": manifest["source_license_metadata"],
        "source_document_count": len(records),
        "ordered_record_ids_sha256": digest([r["id"] for r in records]),
        "duplicate_text_digests": manifest["capture_stats"]["duplicates_by_text_sha"],
    }, records


def assemble_provenance_report(
    source, records, loader_report, *,
    tokenizer_contract_sha256=TOKENIZER_CONTRACT_SHA256,
):
    """No source text, original ID, model weights or token payload in output."""
    if not isinstance(loader_report, dict) or not loader_report.get("actual_worker_processes"):
        raise ValueError("Gate J requires actual subprocess worker evidence")
    if not all(loader_report.get(k) is True for k in (
        "trace_bitwise_equal", "model_parameters_bitwise_equal",
        "adamw_state_bitwise_equal", "committed_cursor_bitwise_equal",
        "python_torch_rng_bitwise_equal",
    )):
        raise ValueError("Gate J training and checkpoint recovery divergence")
    if (loader_report.get("max_abs_loss_difference") != 0.0 or
            loader_report.get("first_resumed_task_id") != 5 or
            loader_report.get("tokenizer_contract_sha256") !=
                tokenizer_contract_sha256 or
            loader_report.get("total_steps") != 12):
        raise ValueError("Gate J frozen restoration protocol mismatch")
    if loader_report.get("fineweb_data_consumed") is not False:
        raise ValueError("Gate H source marker unexpectedly changed")
    # Gate H's label 'synthetic' describes *its default input*; here we
    # explicitly passed real verified rows, after conversion to indexed tasks.
    train, excluded = split_documents(records)
    if (loader_report["train_documents"] != len(train) or
            loader_report["heldout_documents"] != len(excluded)):
        raise ValueError("Gate J source partition differs from actual trainer")
    if set(d["id"] for d in train) & set(d["id"] for d in excluded):
        raise AssertionError("Development partition leaked overlapping document IDs")
    # Gate H always labels its default source as synthetic. Gate J's CLI
    # requires the external, frozen REAL Gate I source, while offline tests
    # intentionally inject synthetic fixtures with different pinned SHA.
    # Distinguish those two cases in machine-readable output as well.
    verified_real_source = bool(
        source.get("snapshot_sha256") == SOURCE_SNAPSHOT_SHA256 and
        source.get("revision") == SOURCE_REVISION and
        source.get("source_document_count") == SELECTED_DOCS
    )
    loader_report = dict(loader_report)
    loader_report["data"] = (
        "REAL pinned FineWeb-Edu text from Gate I LOCAL 32-doc snapshot; "
        "already indexed before DataLoader creation"
        if verified_real_source else "SYNTHETIC OFFLINE UNIT-TEST FIXTURE"
    )
    loader_report["fineweb_data_consumed"] = verified_real_source
    loader_report["live_hf_streaming_consumed"] = False
    return {
        "protocol": PROTOCOL,
        "gate_i_real_source": source,
        "gate_d_tokenizer_contract_sha256": tokenizer_contract_sha256,
        "internal_protocol_development_records": len(train),
        "excluded_from_this_exercise": len(excluded),
        "official_heldout_or_test_set_created": False,
        "model_quality_evaluation_performed": False,
        "tiny_cpu_adamw_training_performed": True,
        "data_source": loader_report["data"],
        "original_upstream_hf_iterableloader_modified": False,
        "new_online_hf_requests": False,
        "gpu_training": "NOT_PERFORMED",
        "real_multiprocess_replay": loader_report,
        "limitations": "Exact local snapshot + deterministic indexing and a tiny "
                       "CPU model, NOT PR27 original HF Streaming IterableDataset, "
                       "shard offsets, SIGKILL recovery, or a 118M GPU run.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--source", default=
                   "research/mini_mythos/results/r2/fineweb_gate_i_32")
    p.add_argument("--contract", default=
                   "research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    p.add_argument("--checkpoint", default=
                   "research/mini_mythos/results/r2/pr27_gate_j_realtext_cpu.pt")
    p.add_argument("--manifest", default=
                   "research/mini_mythos/results/r2/pr27_gate_j_realtext_cpu.manifest.json")
    p.add_argument("--out", default=
                   "research/mini_mythos/results/r2/pr27_gate_j_realtext_replay.json")
    a = p.parse_args()
    repo = get_repo(a.repo)
    base = (repo / "research/mini_mythos/results").resolve()
    paths = [Path(z).resolve() for z in (
        a.source, a.contract, a.checkpoint, a.manifest, a.out
    )]
    if any(not x.is_relative_to(base) for x in paths):
        p.error("All read/write paths must stay inside ignored research results")
    if any(z.exists() for z in paths[2:]):
        p.error("Gate J checkpoint, sidecar or report exists; do not overwrite")
    source, records = verified_real_records(paths[0])
    contract = read_frozen_contract(paths[1], strict_gate=True)
    if (contract["fingerprint_sha256"] != TOKENIZER_CONTRACT_SHA256 or
            contract["fingerprint"]["pinned_revision"] != TOKENIZER_REVISION):
        raise ValueError("Unexpected Gate D tokenizer contract")
    token = load_tokenizer("gpt2", TOKENIZER_REVISION, offline=True)
    # Gate H validates loaded token-ID/backend against frozen contract.
    actual = compare_actual_multiprocess_resume(
        token, contract, checkpoint_path=paths[2], manifest_path=paths[3],
        records=records
    )
    report = assemble_provenance_report(
        source, records, actual,
        tokenizer_contract_sha256=TOKENIZER_CONTRACT_SHA256
    )
    report["research_branch_git_revision"] = commit_id(repo)
    atomic_json(paths[4], report)
    print("Source: REAL pinned FineWeb-Edu 32-doc LOCAL snapshot")
    print("Pinned HF revision:", source["revision"])
    print("Snapshot SHA256:", source["snapshot_sha256"])
    print("Frozen GPT2 contract SHA256:", TOKENIZER_CONTRACT_SHA256)
    print("Internal train/excluded document counts:",
          report["internal_protocol_development_records"],
          report["excluded_from_this_exercise"])
    print("Tiny CPU AdamW steps on real text: 12 (training pipeline smoke)")
    print("Model-quality evaluation:", "NOT_PERFORMED")
    print("Worker PIDs by continuous/interrupted/resumed run:")
    for phase, pids in actual["actual_os_worker_processes_observed_per_run"].items():
        print(" ", phase, pids)
    print("Fetched not committed:", actual["actual_worker_fetched_but_uncommitted"])
    print("First resumed Task ID:", actual["first_resumed_task_id"])
    print("Trace bitwise identical:", actual["trace_bitwise_equal"])
    print("Maximum absolute Loss difference:", actual["max_abs_loss_difference"])
    print("Model params identical:", actual["model_parameters_bitwise_equal"])
    print("AdamW identical:", actual["adamw_state_bitwise_equal"])
    print("Cursor identical:", actual["committed_cursor_bitwise_equal"])
    print("Python/Torch RNG identical:", actual["python_torch_rng_bitwise_equal"])
    print("Original HF IterableDataset resumed:", False)
    print("No HF network requests, no actual GPU training")
    print("Saved:", paths[4])


if __name__ == "__main__":
    main()
