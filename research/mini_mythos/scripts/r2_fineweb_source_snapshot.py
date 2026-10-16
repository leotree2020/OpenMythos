#!/usr/bin/env python3
"""R2 Gate I: bounded, revision-pinned, REAL FineWeb-Edu source snapshot.

This does NOT train or make original PR27 streaming checkpointable.
Resolve official HF dataset revision to immutable SHA before streaming,
select 32 bounded source documents, freeze their text and provenance in
GIT-IGNORED local results. No heldout or model evaluation occurs.
Online requests happen only for freeze; verify runs strictly offline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from common import atomic_json, commit_id, get_repo

DATASET_ID = "HuggingFaceFW/fineweb-edu"
DATASET_CONFIG = "sample-10BT"
DATASET_SPLIT = "train"
PROTOCOL = "R2_GATE_I_REAL_FINEWEB_PINNED_SNAPSHOT_V1"
SELECTED_DOCS = 32
MAX_SCANNED_DOCS = 128
MAX_SINGLE_DOC_BYTES = 262144
MAX_TOTAL_TEXT_BYTES = 4194304
SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
SHA64 = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_line(record):
    return (
        json.dumps(
            record, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False
        ) + "\n"
    ).encode("utf-8")


def validate_revision(revision):
    if not isinstance(revision, str) or SHA40.fullmatch(revision) is None:
        raise ValueError("Dataset revision must be immutable 40-char commit SHA")
    return revision.lower()


def capture_bounded_documents(records, *, limit=SELECTED_DOCS,
                              max_scan=MAX_SCANNED_DOCS,
                              max_doc_bytes=MAX_SINGLE_DOC_BYTES,
                              max_total_bytes=MAX_TOTAL_TEXT_BYTES):
    """First N eligible stream-order docs; do not select by test score."""
    if not 1 <= limit <= max_scan or max_doc_bytes <= 0 or max_total_bytes <= 0:
        raise ValueError("Invalid capture bounds")
    out, scanned, empty, too_large, total = [], 0, 0, 0, 0
    for item in records:
        if scanned >= max_scan or len(out) >= limit:
            break
        index = scanned
        scanned += 1
        if not isinstance(item, dict):
            raise ValueError("Streaming document must be a mapping")
        text = item.get("text")
        if not isinstance(text, str):
            raise ValueError("Streaming record has no string text")
        if not text.strip():
            empty += 1
            continue
        raw = text.encode("utf-8")
        if len(raw) > max_doc_bytes:
            too_large += 1
            continue
        if total + len(raw) > max_total_bytes:
            raise ValueError("Fixed text budget exhausted; do not retune selection")
        source_id = item.get("id")
        if source_id is not None and not isinstance(source_id, (str, int)):
            raise ValueError("Unexpected source document ID type")
        out.append({
            "selected_index": len(out),
            "source_row_index": index,
            "source_id_sha256": (
                None if source_id is None else
                sha256_bytes(str(source_id).encode("utf-8"))
            ),
            "text_sha256": sha256_bytes(raw),
            "text_bytes": len(raw),
            "text": text,
        })
        total += len(raw)
        if len(out) == limit:
            break
    if len(out) != limit:
        raise ValueError(
            f"Only {len(out)}/{limit} eligible documents after scanning "
            f"{scanned} rows; do not change frozen selection policy"
        )
    return out, {
        "rows_scanned": scanned,
        "empty_rows_skipped": empty,
        "oversized_rows_skipped": too_large,
        "selected_documents": len(out),
        "selected_text_bytes": total,
        "duplicates_by_text_sha": len(out) - len({
            row["text_sha256"] for row in out
        }),
    }


def snapshot_blob(rows):
    return b"".join(canonical_line(row) for row in rows)


def make_manifest(rows, stats, *, resolved_revision, requested_revision,
                  working_commit, license_label=None):
    revision = validate_revision(resolved_revision)
    if len(rows) != SELECTED_DOCS:
        raise ValueError("Wrong source document count")
    blob = snapshot_blob(rows)
    return {
        "protocol": PROTOCOL,
        "source": DATASET_ID, "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "requested_revision": requested_revision,
        "resolved_revision": revision,
        "selection_policy": {
            "selected_documents": SELECTED_DOCS,
            "max_scanned_rows": MAX_SCANNED_DOCS,
            "nonempty_text_only": True,
            "max_single_document_bytes": MAX_SINGLE_DOC_BYTES,
            "max_total_text_bytes": MAX_TOTAL_TEXT_BYTES,
            "source_order_kept": True,
            "truncate_text": False,
        },
        "capture_stats": stats,
        "source_license_metadata": license_label,
        "source_snapshot_file": "snapshot.jsonl",
        "snapshot_sha256": sha256_bytes(blob),
        "snapshot_bytes": len(blob),
        "source_document_summaries": [
            {k: row[k] for k in (
                "selected_index", "source_row_index", "source_id_sha256",
                "text_sha256", "text_bytes"
            )}
            for row in rows
        ],
        "github_source_revision": working_commit,
        "scope": "BOUNDED SOURCE SNAPSHOT; not training or heldout eval",
        "trust_note": "SHA proves local file consistency, not trusted origin "
                      "if snapshot and manifest can both be rewritten.",
    }


def check_manifest_and_snapshot(manifest, raw_snapshot):
    if not isinstance(manifest, dict) or manifest.get("protocol") != PROTOCOL:
        raise ValueError("Unknown FineWeb snapshot protocol")
    if (manifest.get("source") != DATASET_ID or
            manifest.get("config") != DATASET_CONFIG or
            manifest.get("split") != DATASET_SPLIT):
        raise ValueError("Wrong source/config/split for PR27 dataset")
    validate_revision(manifest.get("resolved_revision"))
    policy = {
        "selected_documents": SELECTED_DOCS,
        "max_scanned_rows": MAX_SCANNED_DOCS,
        "nonempty_text_only": True,
        "max_single_document_bytes": MAX_SINGLE_DOC_BYTES,
        "max_total_text_bytes": MAX_TOTAL_TEXT_BYTES,
        "source_order_kept": True,
        "truncate_text": False,
    }
    if manifest.get("selection_policy") != policy:
        raise ValueError("Snapshot selection policy drift")
    if manifest.get("source_snapshot_file") != "snapshot.jsonl":
        raise ValueError("Snapshot filename altered")
    if (manifest.get("snapshot_sha256") != sha256_bytes(raw_snapshot) or
            manifest.get("snapshot_bytes") != len(raw_snapshot)):
        raise ValueError("Snapshot SHA256 or size mismatch")
    lines = raw_snapshot.splitlines(keepends=True)
    if len(lines) != SELECTED_DOCS or any(
        not line.endswith(b"\n") for line in lines
    ):
        raise ValueError("Snapshot line framing or document count invalid")
    summaries = manifest.get("source_document_summaries")
    if not isinstance(summaries, list) or len(summaries) != SELECTED_DOCS:
        raise ValueError("Manifest document summaries missing")
    rows, last_idx, text_total = [], -1, 0
    for i, line in enumerate(lines):
        row = json.loads(line)
        if not isinstance(row, dict) or set(row) != {
            "selected_index", "source_row_index", "source_id_sha256",
            "text_sha256", "text_bytes", "text"
        }:
            raise ValueError("Malformed snapshot row")
        index = row["source_row_index"]
        text = row["text"]
        doc_id_hash = row["source_id_sha256"]
        if (row["selected_index"] != i or not isinstance(index, int)
                or index <= last_idx or index >= MAX_SCANNED_DOCS
                or not isinstance(text, str) or not text.strip()):
            raise ValueError("Snapshot source document order invalid")
        if doc_id_hash is not None and (
            not isinstance(doc_id_hash, str) or
            SHA64.fullmatch(doc_id_hash) is None
        ):
            raise ValueError("Source doc ID digest malformed")
        raw_text = text.encode("utf-8")
        if (not isinstance(row["text_sha256"], str) or
                SHA64.fullmatch(row["text_sha256"]) is None or
                sha256_bytes(raw_text) != row["text_sha256"] or
                row["text_bytes"] != len(raw_text) or
                len(raw_text) > MAX_SINGLE_DOC_BYTES):
            raise ValueError("Document content checksum or length mismatch")
        expected_summary = {k: row[k] for k in (
            "selected_index", "source_row_index", "source_id_sha256",
            "text_sha256", "text_bytes"
        )}
        if summaries[i] != expected_summary:
            raise ValueError("Document provenance differs from snapshot")
        if line != canonical_line(row):
            raise ValueError("Snapshot must remain canonical JSONL")
        last_idx, text_total = index, text_total + len(raw_text)
        rows.append(row)
    stats = manifest.get("capture_stats")
    if (text_total > MAX_TOTAL_TEXT_BYTES or
            not isinstance(stats, dict) or
            stats.get("selected_documents") != SELECTED_DOCS or
            stats.get("selected_text_bytes") != text_total or
            not isinstance(stats.get("rows_scanned"), int) or
            not last_idx < stats["rows_scanned"] <= MAX_SCANNED_DOCS):
        raise ValueError("Snapshot count, scan or byte budget inconsistent")
    return rows


def read_verified_snapshot(folder):
    folder = Path(folder)
    manifest = json.loads(
        (folder / "manifest.json").read_text(encoding="utf-8")
    )
    rows = check_manifest_and_snapshot(
        manifest, (folder / "snapshot.jsonl").read_bytes()
    )
    return manifest, rows


def freeze(folder, *, repo, requested_revision, api, dataset_loader):
    """Dependency injection allows all fetch behavior to be tested offline."""
    target = Path(folder)
    if target.exists():
        raise FileExistsError("Snapshot output exists; refusing overwrite")
    info = api.dataset_info(repo_id=DATASET_ID, revision=requested_revision)
    revision = validate_revision(info.sha)
    card = getattr(info, "cardData", None)
    license_value = (
        card.get("license") if isinstance(card, dict)
        else getattr(card, "license", None)
    )
    stream = dataset_loader(
        DATASET_ID, name=DATASET_CONFIG, split=DATASET_SPLIT,
        streaming=True, revision=revision
    )
    rows, stats = capture_bounded_documents(stream)
    manifest = make_manifest(
        rows, stats, resolved_revision=revision,
        requested_revision=requested_revision,
        working_commit=commit_id(repo), license_label=license_value
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="gate_i_stage_", dir=str(target.parent)
    ) as tmp:
        stage = Path(tmp)
        (stage / "snapshot.jsonl").write_bytes(snapshot_blob(rows))
        atomic_json(stage / "manifest.json", manifest)
        read_verified_snapshot(stage)
        if target.exists():
            raise FileExistsError("Snapshot target appeared concurrently")
        os.rename(stage, target)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("freeze", "verify"))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--revision", default="main")
    ap.add_argument("--out-dir", default=
                    "research/mini_mythos/results/r2/fineweb_gate_i_32")
    args = ap.parse_args()
    repo = get_repo(args.repo)
    target = Path(args.out_dir).resolve()
    base = (repo / "research/mini_mythos/results").resolve()
    if not target.is_relative_to(base):
        ap.error("Snapshot must stay under Git-ignored research results")
    if args.action == "freeze":
        try:
            from datasets import load_dataset
            from huggingface_hub import HfApi
        except ImportError as exc:
            raise RuntimeError("HF datasets and Hub clients are required") from exc
        info = freeze(
            target, repo=repo, requested_revision=args.revision,
            api=HfApi(), dataset_loader=load_dataset
        )
        print("Source:", DATASET_ID, DATASET_CONFIG, DATASET_SPLIT)
        print("Pinned HF dataset revision:", info["resolved_revision"])
        print("Dataset license metadata:", info["source_license_metadata"])
        print("Frozen source documents:", info["capture_stats"]["selected_documents"])
        print("Source rows scanned:", info["capture_stats"]["rows_scanned"])
        print("Text payload bytes:", info["capture_stats"]["selected_text_bytes"])
        print("Snapshot bytes:", info["snapshot_bytes"])
        print("Snapshot SHA256:", info["snapshot_sha256"])
        print("Saved:", target)
    else:
        manifest, rows = read_verified_snapshot(target)
        print("Offline source snapshot: VERIFIED")
        print("Source:", manifest["source"], manifest["config"], manifest["split"])
        print("Pinned HF dataset revision:", manifest["resolved_revision"])
        print("Document count:", len(rows))
        print("Snapshot SHA256:", manifest["snapshot_sha256"])
        print("Real text not printed; do not commit snapshot JSONL to Git")
        print("PR27 original Streaming loader modified: False")
        print("Model training: NOT_PERFORMED")


if __name__ == "__main__":
    main()
