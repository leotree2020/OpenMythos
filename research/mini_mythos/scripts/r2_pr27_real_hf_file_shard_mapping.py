#!/usr/bin/env python3
"""Gate O: map pinned REAL HF IterableDataset logical shards -> Parquet PATHS.

This is a metadata-only source mapping using the known datasets==5.1.0
ArrowExamplesIterable.kwargs['files'] and real .shard() subviews.
It DOES NOT call iter(ds), run workers, read documents or train a model.

The HF constructor may read metadata/schema/remote file headers. Source
URLs may contain authentication query strings: NEVER log or save raw URLs.
Only allowlisted sample/10BT relative Parquet paths are preserved.

The private HF implementation is version-sensitive. Unknown wrapper,
input schema, row-group split, file path, package version, duplicate,
missing source, or unexpected partition MUST fail closed.

Gate O is stronger than Gate N (real file-to-logical-shard metadata
mapping), but is NOT measured source coverage by real PR27 workers.
"""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from common import atomic_json, commit_id, get_repo
from r2_fineweb_local_replay import SOURCE_REVISION, verified_real_records
from r2_fineweb_source_snapshot import DATASET_ID, DATASET_CONFIG, DATASET_SPLIT
from r2_pr27_live_hf_shard_metadata import (
    SOURCE_FILE_COUNT, SOURCE_FILE_INVENTORY_SHA256,
    package_versions, verify_frozen_gate_m_inventory,
    verify_report as verify_gate_n_report,
)
from r2_pr27_remote_parquet_inventory import canonical_digest, contiguous_indices

PROTOCOL = "R2_GATE_O_ACTUAL_HF_FILE_SHARD_METADATA_MAPPING_V1"
DATASETS_VERSION = "5.1.0"
WORKERS = 2
FILE_PATTERN = re.compile(r"^sample/10BT/[0-9]{3}_00000[.]parquet$")
ALLOWED_WRAPPERS = frozenset((
    "MappedExamplesIterable", "FilteredExamplesIterable",
    "SelectColumnsIterable", "RebatchedArrowExamplesIterable",
    "FormattedExamplesIterable", "BufferShuffledExamplesIterable",
    "StepExamplesIterable", "InterleavedShardsExamplesIterable",
))


def safe_relative_parquet_path(value):
    """Parse file identity from HF path WITHOUT exposing URLs or secrets."""
    if not isinstance(value, str) or len(value) > 8192 or chr(92) in value:
        raise ValueError("Unsupported private source file reference")
    parts = urlsplit(value)
    if parts.scheme not in ("", "https", "hf"):
        raise ValueError("Unsupported source scheme")
    source_path = unquote(parts.path)
    if source_path.startswith("sample/10BT/"):
        relative = source_path
    elif "/sample/10BT/" in source_path:
        relative = "sample/10BT/" + source_path.rsplit("/sample/10BT/", 1)[-1]
    else:
        raise ValueError("Source does not identify frozen sample/10BT directory")
    if FILE_PATTERN.fullmatch(relative) is None:
        raise ValueError("Source file identity not an expected sample/10BT Parquet filename")
    return relative


def extract_file_paths_from_real_hf_view(view):
    """Read *structure*, not records. Only known 5.1.0 private classes."""
    ex = getattr(view, "_ex_iterable", None)
    if ex is None:
        raise ValueError("HF source iterable missing")
    wrappers = []
    for _ in range(12):
        cls = type(ex)
        if cls.__module__ != "datasets.iterable_dataset":
            raise ValueError("Unexpected HF iterable module; refusing source mapping")
        if cls.__name__ == "ArrowExamplesIterable":
            break
        if cls.__name__ not in ALLOWED_WRAPPERS:
            raise ValueError("Unexpected HF IterableDataset wrapper: " + cls.__name__)
        wrappers.append(cls.__name__)
        ex = getattr(ex, "ex_iterable", None)
        if ex is None:
            raise ValueError("Known wrapper has no ex_iterable")
    else:
        raise ValueError("HF iterable wrapper chain exceeded bound")
    args = getattr(ex, "kwargs", None)
    if not isinstance(args, dict) or set(args) != {"files", "row_groups_list"}:
        raise ValueError("Expected Parquet Arrow source arguments unavailable")
    files, groups = args["files"], args["row_groups_list"]
    if not isinstance(files, list) or not isinstance(groups, list):
        raise ValueError("Expected concrete per-shard source list")
    if not files or len(files) != len(groups):
        raise ValueError("Parquet file/row-group list length mismatch")
    if any(value is not None for value in groups):
        raise ValueError("Row-group-specific source sharding not supported in Gate O")
    names = [safe_relative_parquet_path(value) for value in files]
    if len(set(names)) != len(names):
        raise ValueError("Repeated file identities; cannot infer one file per shard")
    n = getattr(view, "num_shards", None)
    if type(n) is not int or n != len(names):
        raise ValueError("Real view num_shards differs from source file identities")
    return names, wrappers


def observed_mapping(ds, expected_paths, *, version):
    if version != DATASETS_VERSION:
        raise ValueError("HF datasets version drift; Gate O only audited 5.1.0")
    if type(getattr(ds, "num_shards", None)) is not int or ds.num_shards != SOURCE_FILE_COUNT:
        raise ValueError("HF IterableDataset count differs from frozen Gate N 14")
    if (not isinstance(expected_paths, list) or
            len(expected_paths) != SOURCE_FILE_COUNT or
            len(set(expected_paths)) != SOURCE_FILE_COUNT):
        raise ValueError("Gate M frozen file metadata missing")
    names, wrappers = extract_file_paths_from_real_hf_view(ds)
    if set(names) != set(expected_paths):
        raise ValueError("Real HF files differ from frozen Gate M exact paths")
    native, manual, doubled, natural = {}, {}, {}, {}
    for wid in range(WORKERS):
        k = str(wid)
        natural[k] = names[wid::WORKERS]
        native_view = ds.shard(num_shards=WORKERS, index=wid, contiguous=False)
        manual_view = ds.shard(num_shards=WORKERS, index=wid, contiguous=True)
        double_view = manual_view.shard(
            num_shards=WORKERS, index=wid, contiguous=False
        )
        native[k], _ = extract_file_paths_from_real_hf_view(native_view)
        manual[k], _ = extract_file_paths_from_real_hf_view(manual_view)
        doubled[k], _ = extract_file_paths_from_real_hf_view(double_view)
        manual_indices = contiguous_indices(len(names), wid)
        if (native[k] != natural[k] or
                manual[k] != [names[j] for j in manual_indices] or
                doubled[k] != [names[j] for j in manual_indices[wid::WORKERS]]):
            raise ValueError("Observed real HF file-shard view disagrees with policy")
    native_flat = native["0"] + native["1"]
    double_flat = doubled["0"] + doubled["1"]
    if (set(native_flat) != set(names) or
            len(native_flat) != len(names) or
            len(double_flat) != len(set(double_flat))):
        raise ValueError("Source file cover or duplication invariant broken")
    missing = [name for name in names if name not in set(double_flat)]
    if len(double_flat) != SOURCE_FILE_COUNT // 2 or len(missing) != SOURCE_FILE_COUNT // 2:
        raise ValueError("Double-sharding negative control did not match 7/14")
    return {
        "actual_hf_source_order": names,
        "known_wrapper_chain": wrappers,
        "native_actual_files_by_worker": native,
        "manual_actual_files_by_worker": manual,
        "manual_then_native_actual_files_by_worker": doubled,
        "native_actual_source_files": len(native_flat),
        "native_covers_every_source_file_once": True,
        "manual_then_native_actual_source_files": len(double_flat),
        "manual_then_native_missing_source_files": missing,
        "source_file_to_logical_shard_mapping_verified": True,
        "original_pr27_worker_execution_observed": False,
        "actual_document_or_token_loss_measured": False,
        "no_document_iteration": True,
    }


def build_report(ds, *, gate_m, gate_n, versions, git_commit="unknown"):
    if gate_m.get("file_inventory_sha256") != SOURCE_FILE_INVENTORY_SHA256:
        raise ValueError("Gate M inventory SHA differs from independent frozen evidence")
    verify_gate_n_report(gate_n)
    if gate_n["pinned_file_inventory_sha256"] != SOURCE_FILE_INVENTORY_SHA256:
        raise ValueError("Gate N source inventory revision differs")
    if gate_n["actual_hf_iterable_num_shards"] != SOURCE_FILE_COUNT:
        raise ValueError("Gate N real num_shards differs from source")
    if not isinstance(versions, dict) or versions.get("datasets") != DATASETS_VERSION:
        raise ValueError("Gate O package versions differ from Gate N provenance")
    # All filesystem/HF references are reduced to source-relative paths.
    data = observed_mapping(
        ds, [x["path"] for x in gate_m["file_metadata"]],
        version=versions["datasets"]
    )
    payload = {
        "protocol": PROTOCOL,
        "source_dataset": DATASET_ID,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "source_revision": SOURCE_REVISION,
        "gate_m_inventory_sha256": SOURCE_FILE_INVENTORY_SHA256,
        "gate_n_report_sha256": gate_n["report_sha256"],
        "real_parquet_file_count": SOURCE_FILE_COUNT,
        "datasets_version": DATASETS_VERSION,
        "library_versions": versions,
        "git_commit": git_commit,
        "mapping": data,
        "no_training_or_gpu": True,
        "no_explicit_data_iteration": True,
        "live_pr27_dataloader_executed": False,
        "limitation": "Real HF 5.1.0 iterable source file identities and "
                      "metadata-only shard views, NOT observed OS Worker "
                      "reads, number of documents/tokens, or actual PR27 "
                      "training source coverage. Dataset construction may "
                      "access network metadata/header bytes.",
    }
    return dict(payload, report_sha256=canonical_digest(payload))


def verify_report(record, *, gate_m, gate_n):
    if not isinstance(record, dict):
        raise ValueError("Gate O report not a mapping")
    body = dict(record)
    signature = body.pop("report_sha256", None)
    if signature != canonical_digest(body):
        raise ValueError("Gate O report SHA mismatch")
    if (body.get("protocol") != PROTOCOL or
            body.get("source_dataset") != DATASET_ID or
            body.get("config") != DATASET_CONFIG or
            body.get("split") != DATASET_SPLIT or
            body.get("source_revision") != SOURCE_REVISION or
            body.get("gate_m_inventory_sha256") != SOURCE_FILE_INVENTORY_SHA256):
        raise ValueError("Gate O immutable source identity mismatch")
    verify_gate_n_report(gate_n)
    if (body.get("gate_n_report_sha256") != gate_n["report_sha256"] or
            gate_m.get("file_inventory_sha256") != SOURCE_FILE_INVENTORY_SHA256):
        raise ValueError("Gate O previous Gate M/N evidence mismatch")
    if body.get("real_parquet_file_count") != SOURCE_FILE_COUNT or body.get("datasets_version") != DATASETS_VERSION:
        raise ValueError("Gate O format or dataset count drift")
    versions = body.get("library_versions")
    if not isinstance(versions, dict) or versions.get("datasets") != DATASETS_VERSION:
        raise ValueError("Gate O package version provenance corrupted")
    mapping = body.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError("Gate O source mapping absent")
    names = mapping.get("actual_hf_source_order")
    expected = [x["path"] for x in gate_m["file_metadata"]]
    if (not isinstance(names, list) or
            len(names) != SOURCE_FILE_COUNT or
            len(set(names)) != len(names) or set(names) != set(expected)):
        raise ValueError("Gate O source paths fail inventory comparison")
    for i, name in enumerate(names):
        if safe_relative_parquet_path(name) != name:
            raise ValueError("Gate O source paths must be sanitized")
    derived_native, derived_manual, derived_double = {}, {}, {}
    for wid in range(WORKERS):
        indices = contiguous_indices(len(names), wid)
        k = str(wid)
        derived_native[k] = names[wid::WORKERS]
        derived_manual[k] = [names[j] for j in indices]
        derived_double[k] = [names[j] for j in indices[wid::WORKERS]]
    missing = [name for name in names if name not in (derived_double["0"] + derived_double["1"])]
    required = {
        "native_actual_files_by_worker": derived_native,
        "manual_actual_files_by_worker": derived_manual,
        "manual_then_native_actual_files_by_worker": derived_double,
        "native_actual_source_files": SOURCE_FILE_COUNT,
        "native_covers_every_source_file_once": True,
        "manual_then_native_actual_source_files": SOURCE_FILE_COUNT // 2,
        "manual_then_native_missing_source_files": missing,
        "source_file_to_logical_shard_mapping_verified": True,
        "original_pr27_worker_execution_observed": False,
        "actual_document_or_token_loss_measured": False,
        "no_document_iteration": True,
    }
    if any(mapping.get(k) != v for k,v in required.items()):
        raise ValueError("Gate O HF source mapping payload inconsistent")
    if any(body.get(k) is not v for k,v in [
        ("no_training_or_gpu", True),
        ("no_explicit_data_iteration", True),
        ("live_pr27_dataloader_executed", False),
    ]):
        raise ValueError("Gate O scope overstated")
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("freeze", "verify"))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--source", default="research/mini_mythos/results/r2/fineweb_gate_i_32")
    ap.add_argument("--gate-m", default="research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json")
    ap.add_argument("--gate-n", default="research/mini_mythos/results/r2/pr27_gate_n_live_hf_shard_metadata.json")
    ap.add_argument("--out", default="research/mini_mythos/results/r2/pr27_gate_o_real_hf_file_shard_mapping.json")
    args = ap.parse_args()
    root = get_repo(args.repo)
    base = (root / "research/mini_mythos/results").resolve()
    source, m_path, n_path, out = (
        Path(p).resolve() for p in (args.source, args.gate_m, args.gate_n, args.out)
    )
    if any(not p.is_relative_to(base) for p in (source,m_path,n_path,out)):
        ap.error("Gate O files must reside in ignored research results")
    if args.action == "freeze" and out.exists():
        ap.error("Gate O report exists; refusing overwrite")
    _, _ = verified_real_records(source)  # verify Gate I independently
    gate_m = verify_frozen_gate_m_inventory(m_path)
    gate_n = verify_gate_n_report(json.loads(n_path.read_text(encoding="utf-8")))
    if args.action == "freeze":
        from datasets import load_dataset
        versions = package_versions()
        if versions["datasets"] != DATASETS_VERSION:
            raise ValueError("Installed HF datasets not 5.1.0; no private-source inference")
        ds = load_dataset(
            DATASET_ID, name=DATASET_CONFIG, split=DATASET_SPLIT,
            streaming=True, revision=SOURCE_REVISION
        )
        report = build_report(
            ds, gate_m=gate_m, gate_n=gate_n, versions=versions,
            git_commit=commit_id(root)
        )
        verify_report(report, gate_m=gate_m, gate_n=gate_n)
        atomic_json(out, report)
        print("REAL pinned HF source-file mapping inspected (NO record iteration)")
    else:
        report = verify_report(
            json.loads(out.read_text(encoding="utf-8")),
            gate_m=gate_m, gate_n=gate_n
        )
        print("Offline Gate O HF real file-shard mapping: VERIFIED")
    m = report["mapping"]
    print("Dataset revision:", report["source_revision"])
    print("Real HF logical shards:", len(m["actual_hf_source_order"]))
    print("Actual file-to-shard identity mapped:", m["source_file_to_logical_shard_mapping_verified"])
    print("Native actual file-path coverage:", m["native_actual_source_files"], "of", SOURCE_FILE_COUNT)
    print("Manual + HF native actual file-path coverage:",
          m["manual_then_native_actual_source_files"], "of", SOURCE_FILE_COUNT)
    print("Actual source paths missing from nested metadata views:",
          m["manual_then_native_missing_source_files"])
    print("Original PR27 OS Worker observed:", False)
    print("Real source document/token loss measured:", False)
    print("No explicit source record iteration, no training, no GPU")
    print("Saved:", out)


if __name__ == "__main__":
    main()
