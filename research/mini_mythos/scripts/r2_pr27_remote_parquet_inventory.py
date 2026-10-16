#!/usr/bin/env python3
"""R2 Gate M: pin TRUE FineWeb-Edu sample/10BT Parquet FILE INVENTORY.

Uses HF Hub TREE METADATA only (not parquet file downloads) at the SAME
immutable revision as Gate I. No remote dataset iteration, no model, GPU,
source text transfer, or original PR27 modifications.

Project upstream-style shard assignment at the file-ID level:
  HF-native = one non-contiguous worker split, source[worker::workers];
  manual+HF = contiguous manual split then non-contiguous auto worker
              split WITHIN that reduced source.

This is ONLY a file-ID projection using verified HF datasets split rules.
It does not observe remote HF DataLoader, nor assume one file equals one
IterableDataset shard without further verification. It says nothing
quantitative about the *document or token* omission rate in production.

Actions:
  freeze = validate local Gate I snapshot; query HF pinned TREE METADATA;
           save immutable file names/sizes and projected assignments.
  verify = read saved metadata JSON strictly OFFLINE, no Hub use.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from common import atomic_json, commit_id, get_repo
from r2_fineweb_local_replay import SOURCE_REVISION, verified_real_records
from r2_fineweb_source_snapshot import DATASET_ID, DATASET_CONFIG, DATASET_SPLIT


PROTOCOL = "R2_GATE_M_PINNED_SAMPLE10BT_PARQUET_FILE_INVENTORY_V1"
FILE_PREFIX = "sample/10BT"
WORKERS = 2
MAX_PARQUET_FILES = 256


def canonical_digest(value):
    raw = json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_files(files):
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_PARQUET_FILES:
        raise ValueError("Missing or excessive sample/10BT parquet file count")
    filenames = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "size"}:
            raise ValueError("Invalid dataset file metadata schema")
        path, size = item["path"], item["size"]
        if (not isinstance(path, str)
                or PurePosixPath(path).parent.as_posix() != FILE_PREFIX
                or not path.endswith(".parquet") or ".." in path.split("/")
                or not isinstance(size, int) or isinstance(size, bool)
                or size <= 0):
            raise ValueError("Out-of-scope/invalid parquet source file entry")
        filenames.append(path)
    if filenames != sorted(filenames) or len(filenames) != len(set(filenames)):
        raise ValueError("Dataset file list must be sorted, unique, immutable")
    return filenames


def contiguous_indices(count, wid, workers=WORKERS):
    # HF IterableDataset.shard(..., contiguous=True) is the PR27 default.
    div, mod = divmod(count, workers)
    start = div * wid + min(wid, mod)
    stop = start + div + int(wid < mod)
    return list(range(start, stop))


def project_two_worker_file_assignments(files):
    """Project actual FILE IDs, not document/shard-iterable objects."""
    names = validate_files(files)
    native, double = {}, {}
    for worker in range(WORKERS):
        native[str(worker)] = list(range(worker, len(names), WORKERS))
        manual = contiguous_indices(len(names), worker)
        double[str(worker)] = manual[worker::WORKERS]

    def audit(source_indices):
        flat = source_indices["0"] + source_indices["1"]
        missing = [i for i in range(len(names)) if i not in set(flat)]
        duplicate = len(flat) - len(set(flat))
        return {
            "per_worker_file_counts": {
                str(w): len(source_indices[str(w)]) for w in range(WORKERS)
            },
            "worker_file_indices": source_indices,
            "files_seen": len(flat),
            "files_missing": len(missing),
            "missing_file_indices": missing,
            "missing_file_paths": [names[i] for i in missing],
            "duplicate_files": duplicate,
            "covers_all_files_once": not missing and duplicate == 0,
        }

    return {
        "source_file_count": len(names),
        "native_auto_once": audit(native),
        "pr27_style_manual_contiguous_plus_hf_native_auto": audit(double),
        "projection_note": "FILE-ID assignment under documented HF rules; "
                           "NOT measured live dataset shards/docs/token loss",
    }


def build_inventory(files, *, repo_revision, code_revision="unknown"):
    if repo_revision != SOURCE_REVISION:
        raise ValueError("HF dataset revision is NOT Gate I frozen commit")
    files = sorted(files, key=lambda v: v["path"])
    validate_files(files)
    projection = project_two_worker_file_assignments(files)
    payload = {
        "protocol": PROTOCOL,
        "hub_dataset_repo": DATASET_ID,
        "hub_config": DATASET_CONFIG,
        "hub_split": DATASET_SPLIT,
        "hub_repo_commit_sha": SOURCE_REVISION,
        "sample_folder": FILE_PREFIX,
        "metadata_source": "HfApi.list_repo_tree at pinned revision; no parquet body",
        "file_count": len(files),
        "file_metadata": files,
        "file_inventory_sha256": canonical_digest(files),
        "projection": projection,
        "worker_count": WORKERS,
        "code_commit": code_revision,
        "model_training_performed": False,
        "live_hf_dataloader_run": False,
        "file_equals_iterable_shard_verified": False,
        "limits": "Source sample/10BT only, file count capped at 256. "
                  "May still query Hub metadata pages, never parquet bytes. "
                  "All coverage projections are file-level hypotheses.",
    }
    return dict(payload, payload_sha256=canonical_digest(payload))


def verify_inventory(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Inventory manifest must be an object")
    payload = dict(manifest)
    observed = payload.pop("payload_sha256", None)
    if observed != canonical_digest(payload):
        raise ValueError("Inventory manifest SHA256 mismatch")
    if payload.get("protocol") != PROTOCOL:
        raise ValueError("Unrecognized inventory protocol")
    if (payload.get("hub_dataset_repo") != DATASET_ID
            or payload.get("hub_config") != DATASET_CONFIG
            or payload.get("hub_split") != DATASET_SPLIT
            or payload.get("hub_repo_commit_sha") != SOURCE_REVISION
            or payload.get("sample_folder") != FILE_PREFIX):
        raise ValueError("Inventory source dataset config or revision changed")
    files = payload.get("file_metadata")
    validate_files(files)
    if (payload.get("file_count") != len(files)
            or payload.get("file_inventory_sha256") != canonical_digest(files)):
        raise ValueError("Inventory file count or content digest mismatch")
    projection = project_two_worker_file_assignments(files)
    if payload.get("projection") != projection:
        raise ValueError("Inventory file projection changed")
    if (payload.get("worker_count") != WORKERS
            or payload.get("live_hf_dataloader_run") is not False
            or payload.get("file_equals_iterable_shard_verified") is not False
            or payload.get("model_training_performed") is not False):
        raise ValueError("Inventory evidence category / experimental scope changed")
    return manifest


def fetch_pinned_parquet_tree(api, *, pinned_revision=SOURCE_REVISION):
    """Resolve pinned repo revision and enumerate ONLY sample/10BT subtree."""
    if pinned_revision != SOURCE_REVISION:
        raise ValueError("Refuse HF branch/latest revision drift")
    info = api.dataset_info(repo_id=DATASET_ID, revision=pinned_revision)
    if getattr(info, "sha", None) != pinned_revision:
        raise ValueError("HF Hub returned wrong immutable repository commit")
    entries = api.list_repo_tree(
        repo_id=DATASET_ID, path_in_repo=FILE_PREFIX,
        recursive=True, revision=pinned_revision, repo_type="dataset"
    )
    found = []
    for entry in entries:
        path = getattr(entry, "path", None)
        if (not isinstance(path, str)
                or PurePosixPath(path).parent.as_posix() != FILE_PREFIX
                or not path.endswith(".parquet")):
            continue
        size = getattr(entry, "size", None)
        found.append({"path": path, "size": size})
        if len(found) > MAX_PARQUET_FILES:
            raise ValueError("Sample has more file metadata than permitted cap")
    return sorted(found, key=lambda v: v["path"])


def freeze_inventory(api, *, code_revision="unknown"):
    files = fetch_pinned_parquet_tree(api)
    payload = build_inventory(
        files, repo_revision=SOURCE_REVISION, code_revision=code_revision
    )
    return verify_inventory(payload)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("freeze", "verify"))
    p.add_argument("--repo", default=".")
    p.add_argument("--source", default=
                   "research/mini_mythos/results/r2/fineweb_gate_i_32")
    p.add_argument("--out", default=
                   "research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json")
    args = p.parse_args()
    root = get_repo(args.repo)
    basedir = (root / "research/mini_mythos/results").resolve()
    snapshot, out = Path(args.source).resolve(), Path(args.out).resolve()
    if not snapshot.is_relative_to(basedir) or not out.is_relative_to(basedir):
        p.error("Inputs/outputs must be in Git-ignored research results")

    if args.action == "freeze":
        if out.exists():
            p.error("Original inventory already exists; refusing overwrite")
        # Local Gate I content integrity and exact immutable SHA guard.
        real_provenance, _ = verified_real_records(snapshot)
        if real_provenance["revision"] != SOURCE_REVISION:
            raise ValueError("Gate I source is no longer the pinned HF commit")
        from huggingface_hub import HfApi
        record = freeze_inventory(HfApi(), code_revision=commit_id(root))
        atomic_json(out, record)
        print("HF Hub metadata scope:", DATASET_ID, FILE_PREFIX)
        print("Pinned HF commit:", record["hub_repo_commit_sha"])
        print("Inventory Parquet FILE count:", record["file_count"])
        print("File name+size inventory SHA256:", record["file_inventory_sha256"])
        print("File bodies downloaded:", False)
        print("File IDs are NOT verified runtime HF iterable shard IDs")
    else:
        record = verify_inventory(
            json.loads(out.read_text(encoding="utf-8"))
        )
        print("Offline pinned file inventory: VERIFIED")
        print("Pinned HF commit:", record["hub_repo_commit_sha"])
        print("File name+size inventory SHA256:", record["file_inventory_sha256"])
    native = record["projection"]["native_auto_once"]
    manual = record["projection"]["pr27_style_manual_contiguous_plus_hf_native_auto"]
    print("Native-once projected files:", native["files_seen"],
          "of", record["file_count"])
    print("Native covers all file IDs once:", native["covers_all_files_once"])
    print("Manual+HF-auto projected files:", manual["files_seen"],
          "of", record["file_count"])
    print("Manual+HF-auto missing file IDs:", manual["files_missing"])
    print("Missing sample/10BT parquet paths:", manual["missing_file_paths"])
    print("Projection only; ORIGINAL streaming loader NOT executed")
    print("No model, no GPU, no Parquet body download")
    print("Saved:", out)


if __name__ == "__main__":
    main()
