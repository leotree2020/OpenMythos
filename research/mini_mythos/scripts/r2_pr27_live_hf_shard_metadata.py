#!/usr/bin/env python3
"""Gate N: inspect REAL pinned FineWeb-Edu HF Streaming shard COUNTS.

HF datasets.load_dataset(streaming=True, revision=<frozen-SHA>) is used
solely to construct an IterableDataset and inspect num_shards, then call
.shard(2,worker_id) without iteration. No DataLoader or model is run.

WARNING: construction MAY trigger metadata, schema or file-header I/O.
No zero-network-byte assertion is made. Native file/shard identity and
real OS worker coverage are NOT proven by counting shards alone.

freeze validates the exact Gate I source snapshot and Gate M immutable
file inventory BEFORE remote construction; verify is strictly offline.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform

from common import atomic_json, commit_id, get_repo
from r2_fineweb_local_replay import SOURCE_REVISION, verified_real_records
from r2_fineweb_source_snapshot import DATASET_ID, DATASET_CONFIG, DATASET_SPLIT
from r2_pr27_remote_parquet_inventory import (
    canonical_digest, contiguous_indices, verify_inventory,
)

PROTOCOL = "R2_GATE_N_ACTUAL_HF_STREAMING_SHARD_METADATA_V1"
WORKERS = 2
SOURCE_FILE_COUNT = 14
SOURCE_FILE_INVENTORY_SHA256 = (
    "0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209"
)
MAX_SHARDS = 4096


def verify_frozen_gate_m_inventory(path):
    manifest = verify_inventory(json.loads(Path(path).read_text(encoding="utf-8")))
    if manifest["file_count"] != SOURCE_FILE_COUNT:
        raise ValueError("Frozen Gate M file count differs from 14-file evidence")
    if manifest["file_inventory_sha256"] != SOURCE_FILE_INVENTORY_SHA256:
        raise ValueError("Frozen Gate M inventory differs from external pinned SHA")
    if manifest["hub_repo_commit_sha"] != SOURCE_REVISION:
        raise ValueError("Frozen Gate M repo commit differs from Gate I")
    return manifest


def package_versions():
    versions = {"python": platform.python_version()}
    for name in ("datasets", "torch", "huggingface_hub", "pyarrow"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def project_logical_shard_indices(count):
    """Shard-ID assignment model; NOT file paths, docs or actual worker output."""
    if not isinstance(count, int) or isinstance(count, bool) or not 2 <= count <= MAX_SHARDS:
        raise ValueError("Actual HF streaming Dataset has invalid shard count")
    native, double = {}, {}
    for wid in range(WORKERS):
        native[str(wid)] = list(range(wid, count, WORKERS))
        manual = contiguous_indices(count, wid)
        double[str(wid)] = manual[wid::WORKERS]

    def audit(assignments):
        combined = [v for w in range(WORKERS) for v in assignments[str(w)]]
        if len(set(combined)) != len(combined):
            raise ValueError("Logical shard projection duplicated IDs")
        missing = sorted(set(range(count)) - set(combined))
        if len(combined) + len(missing) != count:
            raise ValueError("Logical shard coverage arithmetic failed")
        return {
            "per_worker_counts": {
                str(w): len(assignments[str(w)]) for w in range(WORKERS)
            },
            "logical_indices_by_worker": assignments,
            "observed_logical_indices": len(combined),
            "missing_logical_indices": missing,
            "missing_logical_count": len(missing),
            "covers_all_indices_once": len(missing) == 0,
        }

    return {
        "source_num_shards": count,
        "workers": WORKERS,
        "native_worker_auto_once": audit(native),
        "pr27_manual_contiguous_plus_native_auto": audit(double),
    }


def inspect_runtime_dataset(ds):
    """ACTUAL HF .shard view counts only. This never invokes iter(ds)."""
    n = getattr(ds, "num_shards", None)
    if not isinstance(n, int) or isinstance(n, bool) or not 2 <= n <= MAX_SHARDS:
        raise ValueError("Real HF dataset returned unexpected num_shards")
    projected = project_logical_shard_indices(n)
    manual_counts, native_counts, double_counts = {}, {}, {}
    for wid in range(WORKERS):
        key = str(wid)
        manual = ds.shard(num_shards=WORKERS, index=wid, contiguous=True)
        native = ds.shard(num_shards=WORKERS, index=wid, contiguous=False)
        double = manual.shard(
            num_shards=WORKERS, index=wid, contiguous=False
        )
        counts = (manual.num_shards, native.num_shards, double.num_shards)
        if any(not isinstance(k, int) or isinstance(k, bool) for k in counts):
            raise ValueError("HF shard view returned noninteger count")
        if counts[0] != len(contiguous_indices(n, wid)):
            raise ValueError("HF manual contiguous shard count mismatch")
        if counts[1] != projected["native_worker_auto_once"]["per_worker_counts"][key]:
            raise ValueError("HF native noncontiguous shard count mismatch")
        if counts[2] != projected[
            "pr27_manual_contiguous_plus_native_auto"
        ]["per_worker_counts"][key]:
            raise ValueError("HF double-shard count mismatch")
        manual_counts[key], native_counts[key], double_counts[key] = counts

    return {
        "source_num_shards": n,
        "actual_dataset_class": type(ds).__module__ + "." + type(ds).__qualname__,
        "actual_manual_contiguous_shard_counts": manual_counts,
        "actual_noncontiguous_shard_counts": native_counts,
        "actual_manual_then_noncontiguous_counts": double_counts,
        "logical_shard_id_projection": projected,
        "no_explicit_document_iteration": True,
    }


def build_report(
    ds, *, source_sha, file_count, file_inventory_sha,
    versions, git_commit="unknown"
):
    if source_sha != SOURCE_REVISION:
        raise ValueError("Dataset must be pinned to Gate I frozen revision")
    if file_count != SOURCE_FILE_COUNT:
        raise ValueError("Unexpected Gate M file count")
    if file_inventory_sha != SOURCE_FILE_INVENTORY_SHA256:
        raise ValueError("Gate M immutable file inventory SHA drift")
    if not isinstance(versions, dict) or any(
        not isinstance(versions.get(k), str) or not versions[k]
        for k in ("python", "datasets", "torch", "huggingface_hub", "pyarrow")
    ):
        raise ValueError("Required runtime package versions missing")
    inspected = inspect_runtime_dataset(ds)
    payload = {
        "protocol": PROTOCOL,
        "hf_dataset_repo": DATASET_ID,
        "hf_config": DATASET_CONFIG,
        "hf_split": DATASET_SPLIT,
        "pinned_repo_commit": SOURCE_REVISION,
        "pinned_file_inventory_sha256": SOURCE_FILE_INVENTORY_SHA256,
        "parquet_file_count_from_gate_m": file_count,
        "actual_hf_iterable_num_shards": inspected["source_num_shards"],
        "hf_shards_count_matches_file_count": inspected["source_num_shards"] == file_count,
        "file_identity_to_hf_shard_identity_verified": False,
        "runtime_inspection": inspected,
        "package_versions": versions,
        "research_git_commit": git_commit,
        "load_dataset_invoked": True,
        "original_pr27_dataloader_invoked": False,
        "dataset_iteration_performed": False,
        "model_training_performed": False,
        "gpu_training_performed": False,
        "network_note": "HF construction may read remote metadata, schema or "
                        "Parquet headers; network bytes were not measured.",
        "caution": "Counts measured from actual HF Dataset. Logical shard "
                   "indices are a projection, NOT observed actual Worker "
                   "file/document coverage, and not mapped to file paths.",
    }
    return dict(payload, report_sha256=canonical_digest(payload))


def verify_report(report):
    if not isinstance(report, dict):
        raise ValueError("Gate N manifest must be JSON object")
    body = dict(report)
    observed_sha = body.pop("report_sha256", None)
    if observed_sha != canonical_digest(body):
        raise ValueError("Gate N manifest SHA256 mismatch")
    if (body.get("protocol") != PROTOCOL or
            body.get("hf_dataset_repo") != DATASET_ID or
            body.get("hf_config") != DATASET_CONFIG or
            body.get("hf_split") != DATASET_SPLIT or
            body.get("pinned_repo_commit") != SOURCE_REVISION or
            body.get("parquet_file_count_from_gate_m") != SOURCE_FILE_COUNT or
            body.get("pinned_file_inventory_sha256") != SOURCE_FILE_INVENTORY_SHA256):
        raise ValueError("Gate N frozen dataset/inventory contract mismatch")
    versions = body.get("package_versions")
    if not isinstance(versions, dict) or any(
        not isinstance(versions.get(k), str) or not versions[k]
        for k in ("python", "datasets", "torch", "huggingface_hub", "pyarrow")
    ):
        raise ValueError("Gate N package metadata corrupted")
    n = body.get("actual_hf_iterable_num_shards")
    model = project_logical_shard_indices(n)
    inspection = body.get("runtime_inspection")
    if not isinstance(inspection, dict) or inspection.get("source_num_shards") != n:
        raise ValueError("Gate N source num_shards inconsistent")
    if inspection.get("logical_shard_id_projection") != model:
        raise ValueError("Gate N logical projection inconsistent")
    if (
        inspection.get("actual_manual_contiguous_shard_counts") != {
            str(w): len(contiguous_indices(n, w)) for w in range(WORKERS)
        } or
        inspection.get("actual_noncontiguous_shard_counts") !=
            model["native_worker_auto_once"]["per_worker_counts"] or
        inspection.get("actual_manual_then_noncontiguous_counts") !=
            model["pr27_manual_contiguous_plus_native_auto"]["per_worker_counts"]
    ):
        raise ValueError("Gate N actual shard view counts inconsistent")
    if body.get("hf_shards_count_matches_file_count") is not (n == SOURCE_FILE_COUNT):
        raise ValueError("Gate N file and shard count relation inconsistent")
    for name, expected in (
        ("file_identity_to_hf_shard_identity_verified", False),
        ("load_dataset_invoked", True),
        ("original_pr27_dataloader_invoked", False),
        ("dataset_iteration_performed", False),
        ("model_training_performed", False),
        ("gpu_training_performed", False),
    ):
        if body.get(name) is not expected:
            raise ValueError("Gate N evidence scope overstated: " + name)
    if inspection.get("no_explicit_document_iteration") is not True:
        raise ValueError("Gate N document iteration metadata incorrect")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("freeze", "verify"))
    p.add_argument("--repo", default=".")
    p.add_argument("--source", default=
                   "research/mini_mythos/results/r2/fineweb_gate_i_32")
    p.add_argument("--file-inventory", default=
                   "research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json")
    p.add_argument("--out", default=
                   "research/mini_mythos/results/r2/pr27_gate_n_live_hf_shard_metadata.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    base = (root / "research/mini_mythos/results").resolve()
    source, inventory, output = [
        Path(value).resolve()
        for value in (a.source, a.file_inventory, a.out)
    ]
    if any(not pth.is_relative_to(base) for pth in (source, inventory, output)):
        p.error("Gate I/M/N paths must stay in Git-ignored research results")
    if a.action == "freeze":
        if output.exists():
            p.error("Gate N result exists: refuse overwrite")
        real, _ = verified_real_records(source)
        previous = verify_frozen_gate_m_inventory(inventory)
        if real["revision"] != SOURCE_REVISION:
            raise ValueError("Gate I snapshot source revision altered")
        from datasets import load_dataset
        # No explicit iteration, DataLoader or model creation.
        dataset = load_dataset(
            DATASET_ID, name=DATASET_CONFIG, split=DATASET_SPLIT,
            streaming=True, revision=SOURCE_REVISION
        )
        result = build_report(
            dataset, source_sha=real["revision"],
            file_count=previous["file_count"],
            file_inventory_sha=previous["file_inventory_sha256"],
            versions=package_versions(), git_commit=commit_id(root)
        )
        verify_report(result)
        atomic_json(output, result)
        print("REAL frozen HF streaming Dataset constructed (NO iteration)")
    else:
        result = verify_report(
            json.loads(output.read_text(encoding="utf-8"))
        )
        print("Offline true HF shard-count evidence: VERIFIED")
    scan = result["runtime_inspection"]
    assign = scan["logical_shard_id_projection"]
    print("Pinned HF dataset commit:", result["pinned_repo_commit"])
    print("Actual ds.num_shards:", result["actual_hf_iterable_num_shards"])
    print("Frozen sample-10BT Parquet file count:", result["parquet_file_count_from_gate_m"])
    print("HF shard count equals file count:", result["hf_shards_count_matches_file_count"])
    print("Actual manual contiguous .shard counts:", scan["actual_manual_contiguous_shard_counts"])
    print("Actual native noncontiguous .shard counts:", scan["actual_noncontiguous_shard_counts"])
    print("Actual manual-then-noncontiguous .shard counts:",
          scan["actual_manual_then_noncontiguous_counts"])
    print("Native logical shard IDs projected coverage:",
          assign["native_worker_auto_once"]["observed_logical_indices"],
          "of", scan["source_num_shards"])
    print("Double logical shard IDs projected coverage:",
          assign["pr27_manual_contiguous_plus_native_auto"]["observed_logical_indices"],
          "of", scan["source_num_shards"])
    print("Double logical shard IDs projected missing:",
          assign["pr27_manual_contiguous_plus_native_auto"]["missing_logical_indices"])
    print("Environment versions:", result["package_versions"])
    print("HF file-to-shard identity verified:", False)
    print("Original PR27 DataLoader executed:", False)
    print("No explicit document iteration, no model or GPU")
    print("HF Dataset construction may access metadata/schema/file headers")
    print("Saved:", output)


if __name__ == "__main__":
    main()
