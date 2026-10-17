#!/usr/bin/env python3
"""R2 Gate P: REAL OS workers replay REAL HF Parquet FILE IDENTITIES only.

The 14 exact file identities are obtained from the immutable, previously
verified Gate O HF source-mapping manifest, not guessed from numbering.
Each local Arrow shard contains exactly ONE sanitized path ID, and the
two real PyTorch DataLoader workers exercise Hugging Face's actual
IterableDataset.__iter__ native noncontiguous auto-sharding path.

Compare HF-native-once against PR27-style explicit contiguous shard
per worker PLUS HF native auto-shard. No Parquet file is read by workers.
This is local in-memory identity REPLAY, not original remote PR27
DataLoader reading Parquet rows, docs or tokens. All claims explicitly
retain this distinction. CPU only, Linux only, two OS workers.

freeze checks Gate I/M/N/O immutable evidence before any workers.
verify checks an immutable manifest wholly offline without PyTorch
workers, Hugging Face Hub, or any network requests.
"""
import argparse
import gc
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys

from torch.utils.data import DataLoader, IterableDataset, get_worker_info

from common import atomic_json, commit_id, get_repo
from r2_fineweb_local_replay import (
    SOURCE_REVISION, SOURCE_SNAPSHOT_SHA256, verified_real_records,
)
from r2_pr27_live_hf_shard_metadata import (
    SOURCE_FILE_COUNT, SOURCE_FILE_INVENTORY_SHA256, verify_frozen_gate_m_inventory,
    verify_report as verify_n,
)
from r2_pr27_real_hf_file_shard_mapping import (
    DATASETS_VERSION, safe_relative_parquet_path,
    verify_report as verify_o,
)
from r2_pr27_remote_parquet_inventory import canonical_digest, contiguous_indices

PROTOCOL = "R2_GATE_P_REAL_OS_WORKER_FROZEN_FILE_ID_REPLAY_V1"
WORKERS = 2
PREFETCH = 2
MODES = ("native_once", "explicit_twice")


def source_from_frozen_paths(source_paths):
    """Construct 14 *local* Arrow shards of IDs, one row each; NO source bytes."""
    from datasets import Dataset
    if not isinstance(source_paths, list) or len(source_paths) != SOURCE_FILE_COUNT:
        raise ValueError("Gate P requires the 14 Gate O source identities")
    sanitized = [safe_relative_parquet_path(p) for p in source_paths]
    if sanitized != source_paths or len(set(sanitized)) != SOURCE_FILE_COUNT:
        raise ValueError("Non-canonical or duplicate file identity")
    source = Dataset.from_dict({"source_file_id": sanitized}).to_iterable_dataset(
        num_shards=SOURCE_FILE_COUNT
    )
    if source.num_shards != SOURCE_FILE_COUNT:
        raise ValueError("Local ID-only HF dataset has incorrect shard count")
    # 14 rows/14 shards establishes one ID per local Arrow shard.
    return source


class FileIdentityWorkerProbe(IterableDataset):
    """Real worker __iter__, HF native partition runs *inside* subprocess."""

    def __init__(self, source, mode):
        super().__init__()
        if mode not in MODES or source.num_shards != SOURCE_FILE_COUNT:
            raise ValueError("Unrecognized worker shard mode or source")
        self.source, self.mode = source, mode

    def __iter__(self):
        info = get_worker_info()
        if info is None or info.num_workers != WORKERS or info.id not in range(WORKERS):
            raise RuntimeError("Actual two Linux OS DataLoader workers required")
        view = self.source
        if self.mode == "explicit_twice":
            view = view.shard(num_shards=WORKERS, index=info.id, contiguous=True)
        # The following REAL HF iterable __iter__ performs its automatic
        # noncontiguous worker sharding within each child subprocess.
        for row in view:
            yield {
                "source_file_id": row["source_file_id"],
                "worker_id": info.id,
                "pid": os.getpid(),
                "source_num_shards_before_auto": view.num_shards,
            }


def collect(source, mode):
    if sys.platform != "linux":
        raise RuntimeError("Gate P requires real Linux OS workers")
    if mode not in MODES:
        raise ValueError("Unknown Gate P mode")
    ctx = mp.get_context("spawn")
    loader = DataLoader(
        FileIdentityWorkerProbe(source, mode),
        batch_size=None, num_workers=WORKERS,
        prefetch_factor=PREFETCH, in_order=True, persistent_workers=False,
        multiprocessing_context=ctx, timeout=45
    )
    iterator = iter(loader)
    rows, pids = [], {}
    try:
        for row in iterator:
            path = safe_relative_parquet_path(row["source_file_id"])
            wid, pid = int(row["worker_id"]), int(row["pid"])
            before_auto = int(row["source_num_shards_before_auto"])
            if wid not in (0, 1) or pid <= 0 or pid == os.getpid():
                raise ValueError("Fake or invalid worker identity")
            if wid in pids and pids[wid] != pid:
                raise ValueError("Worker PID changed during source audit")
            pids[wid] = pid
            rows.append({
                "source_file_id": path, "worker_id": wid,
                "num_shards_before_auto": before_auto,
            })
            if len(rows) > SOURCE_FILE_COUNT:
                raise ValueError("Source replay emitted too many identities")
    finally:
        del iterator
        del loader
        gc.collect()
    if set(pids) != {0, 1} or pids[0] == pids[1]:
        raise RuntimeError("Two distinct real worker PIDs not observed")
    return rows, {str(w): pids[w] for w in range(WORKERS)}


def expected_identity_paths(names, mode):
    if mode not in MODES:
        raise ValueError("Invalid mode")
    paths = {}
    for wid in range(WORKERS):
        if mode == "native_once":
            paths[str(wid)] = names[wid::WORKERS]
        else:
            indices = contiguous_indices(len(names), wid)
            paths[str(wid)] = [names[i] for i in indices[wid::WORKERS]]
    return paths


def summarize_worker_rows(names, mode, rows, pids):
    if len(names) != SOURCE_FILE_COUNT or len(set(names)) != SOURCE_FILE_COUNT:
        raise ValueError("Invalid expected source path IDs")
    expected = expected_identity_paths(names, mode)
    if (not isinstance(pids, dict) or set(pids) != {"0", "1"}
            or any(type(pids[k]) is not int or pids[k] <= 0 for k in pids)
            or pids["0"] == pids["1"]):
        raise ValueError("Invalid OS Worker PID evidence")
    observed = {str(w): [] for w in range(WORKERS)}
    expected_count = SOURCE_FILE_COUNT if mode == "native_once" else SOURCE_FILE_COUNT // 2
    before_expected = SOURCE_FILE_COUNT if mode == "native_once" else SOURCE_FILE_COUNT // 2
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise ValueError("Incorrect number of worker source identities")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "source_file_id", "worker_id", "num_shards_before_auto"
        }:
            raise ValueError("Malformed worker source record")
        wid = row["worker_id"]
        if type(wid) is not int or wid not in range(WORKERS):
            raise ValueError("Unknown worker id")
        ident = row["source_file_id"]
        if safe_relative_parquet_path(ident) != ident:
            raise ValueError("Worker emitted unverified source path")
        if row["num_shards_before_auto"] != before_expected:
            raise ValueError("Unexpected HF shard count before auto worker split")
        observed[str(wid)].append(ident)
    joined = observed["0"] + observed["1"]
    if len(set(joined)) != len(joined) or not set(joined).issubset(set(names)):
        raise ValueError("Duplicate or foreign source ID seen in workers")
    if observed != expected:
        raise ValueError("Actual worker file ID assignment disagrees with HF source mapping")
    missing = [ident for ident in names if ident not in set(joined)]
    return {
        "mode": mode,
        "actual_linux_worker_pids": pids,
        "per_worker_paths": observed,
        "per_worker_counts": {k: len(v) for k,v in observed.items()},
        "visible_shards_before_native_auto": before_expected,
        "covered_source_file_identifiers": len(joined),
        "missing_source_file_identifiers": missing,
        "covers_source_file_ids_once": len(missing) == 0 and len(joined) == len(names),
        "original_remote_parquet_read": False,
        "real_original_pr27_worker_execution": False,
    }


def build_report(*, gate_m, gate_n, gate_o, source_snapshot_sha, versions,
                 git_commit="unknown"):
    verify_n(gate_n)
    verify_o(gate_o, gate_m=gate_m, gate_n=gate_n)
    if gate_o["source_revision"] != SOURCE_REVISION:
        raise ValueError("Gate O source SHA mismatch")
    if gate_o["gate_m_inventory_sha256"] != SOURCE_FILE_INVENTORY_SHA256:
        raise ValueError("Gate M file SHA mismatch")
    if source_snapshot_sha != SOURCE_SNAPSHOT_SHA256:
        raise ValueError("Gate P Gate I immutable source snapshot SHA differs")
    if (not isinstance(versions, dict)
            or versions.get("datasets") != DATASETS_VERSION
            or versions != gate_n.get("package_versions")
            or versions != gate_o.get("library_versions")):
        raise ValueError("Gate P actual library versions differ from Gate N/O")
    paths = gate_o["mapping"]["actual_hf_source_order"]
    source = source_from_frozen_paths(paths)
    native_rows, native_pid = collect(source, MODES[0])
    twice_rows, twice_pid = collect(source, MODES[1])
    good = summarize_worker_rows(paths, MODES[0], native_rows, native_pid)
    bad = summarize_worker_rows(paths, MODES[1], twice_rows, twice_pid)
    if not good["covers_source_file_ids_once"] or bad["covers_source_file_ids_once"]:
        raise ValueError("Expected two-worker negative control did not fire")
    payload = {
        "protocol": PROTOCOL,
        "source_dataset": gate_o["source_dataset"],
        "dataset_config": gate_o["config"],
        "source_revision": SOURCE_REVISION,
        "real_fineweb_snapshot_sha256": source_snapshot_sha,
        "gate_m_inventory_sha256": SOURCE_FILE_INVENTORY_SHA256,
        "gate_n_report_sha256": gate_n["report_sha256"],
        "gate_o_report_sha256": gate_o["report_sha256"],
        "real_hf_source_order": paths,
        "real_file_identity_count": SOURCE_FILE_COUNT,
        "local_one_id_per_arrow_shard": True,
        "real_os_workers_per_mode": WORKERS,
        "native_hf_auto_once": good,
        "manual_plus_native_hf_auto": bad,
        "datasets_version": DATASETS_VERSION,
        "package_versions": versions,
        "research_git_commit": git_commit,
        "no_source_text_sent_to_workers": True,
        "no_remote_parquet_rows_read": True,
        "model_training_performed": False,
        "gpu_training_performed": False,
        "original_pr27_dataloader_executed": False,
        "limits": "REAL pinned HF file identifiers replayed through 14 "
                  "LOCAL HF Arrow shards, one identity per shard, "
                  "with two actual Linux OS PyTorch workers per arm. "
                  "NOT original remote Parquet readers, docs or tokens.",
    }
    return dict(payload, report_sha256=canonical_digest(payload))


def verify_report(report, *, gate_m, gate_n, gate_o):
    if not isinstance(report, dict):
        raise ValueError("Gate P report not a JSON object")
    core = dict(report)
    digest = core.pop("report_sha256", None)
    if digest != canonical_digest(core):
        raise ValueError("Gate P report SHA256 mismatch")
    if (core.get("protocol") != PROTOCOL
            or core.get("source_dataset") != gate_o["source_dataset"]
            or core.get("dataset_config") != gate_o["config"]
            or core.get("source_revision") != SOURCE_REVISION
            or core.get("gate_m_inventory_sha256") != SOURCE_FILE_INVENTORY_SHA256
            or core.get("real_file_identity_count") != SOURCE_FILE_COUNT
            or core.get("real_os_workers_per_mode") != WORKERS
            or core.get("datasets_version") != DATASETS_VERSION):
        raise ValueError("Gate P immutable policy mismatch")
    verify_n(gate_n)
    verify_o(gate_o, gate_m=gate_m, gate_n=gate_n)
    if (core.get("gate_n_report_sha256") != gate_n["report_sha256"]
            or core.get("gate_o_report_sha256") != gate_o["report_sha256"]):
        raise ValueError("Gate P Gate N/O linked report hash mismatch")
    names = gate_o["mapping"]["actual_hf_source_order"]
    if core.get("real_hf_source_order") != names:
        raise ValueError("Gate P source paths differ from live Gate O verified metadata")
    if (not isinstance(core.get("package_versions"),dict)
            or core["package_versions"] != gate_n.get("package_versions")
            or core["package_versions"] != gate_o.get("library_versions")
            or core["package_versions"].get("datasets") != DATASETS_VERSION):
        raise ValueError("Gate P installed versions mismatch Gate N/O")
    if core.get("real_fineweb_snapshot_sha256") != SOURCE_SNAPSHOT_SHA256:
        raise ValueError("Gate P Gate I immutable source snapshot SHA mismatch")
    if any(core.get(key) is not val for key,val in [
        ("local_one_id_per_arrow_shard", True),
        ("no_source_text_sent_to_workers", True),
        ("no_remote_parquet_rows_read", True),
        ("model_training_performed", False),
        ("gpu_training_performed", False),
        ("original_pr27_dataloader_executed", False),
    ]):
        raise ValueError("Gate P evidence scope overstated")
    for key,mode in [
        ("native_hf_auto_once", MODES[0]),
        ("manual_plus_native_hf_auto", MODES[1])
    ]:
        part = core.get(key)
        if not isinstance(part,dict) or part.get("mode") != mode:
            raise ValueError("Gate P Worker arm missing")
        if (part.get("original_remote_parquet_read") is not False
                or part.get("real_original_pr27_worker_execution") is not False):
            raise ValueError("Gate P worker evidence scope corrupted")
        reconstructed_rows = [
            {"source_file_id": path, "worker_id": wid,
             "num_shards_before_auto": part.get("visible_shards_before_native_auto")}
            for wid in range(WORKERS)
            for path in (part.get("per_worker_paths") or {}).get(str(wid), [])
        ]
        expected_summary = summarize_worker_rows(
            names, mode, reconstructed_rows,
            part.get("actual_linux_worker_pids")
        )
        if part != expected_summary:
            raise ValueError("Gate P worker file-ID coverage digest or schema altered")
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("freeze","verify"))
    ap.add_argument("--repo",default=".")
    ap.add_argument("--source",default="research/mini_mythos/results/r2/fineweb_gate_i_32")
    ap.add_argument("--gate-m",default="research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json")
    ap.add_argument("--gate-n",default="research/mini_mythos/results/r2/pr27_gate_n_live_hf_shard_metadata.json")
    ap.add_argument("--gate-o",default="research/mini_mythos/results/r2/pr27_gate_o_real_hf_file_shard_mapping.json")
    ap.add_argument("--out",default="research/mini_mythos/results/r2/pr27_gate_p_os_worker_file_identity_replay.json")
    args=ap.parse_args()
    root=get_repo(args.repo)
    base=(root/"research/mini_mythos/results").resolve()
    source_path,m_path,n_path,o_path,out=(
        Path(p).resolve() for p in (args.source,args.gate_m,args.gate_n,args.gate_o,args.out)
    )
    if any(not p.is_relative_to(base) for p in (source_path,m_path,n_path,o_path,out)):
        ap.error("All Gate P sources and reports must be in ignored results")
    if args.action=="freeze" and out.exists():
        ap.error("Gate P previous report exists; refusing overwrite")
    source_info,_=verified_real_records(source_path)
    gate_m=verify_frozen_gate_m_inventory(m_path)
    gate_n=verify_n(json.loads(n_path.read_text(encoding="utf-8")))
    gate_o=verify_o(
        json.loads(o_path.read_text(encoding="utf-8")),
        gate_m=gate_m,gate_n=gate_n
    )
    if args.action=="freeze":
        from r2_pr27_live_hf_shard_metadata import package_versions
        report=build_report(
            gate_m=gate_m,gate_n=gate_n,gate_o=gate_o,
            source_snapshot_sha=source_info["snapshot_sha256"],
            versions=package_versions(),git_commit=commit_id(root)
        )
        verify_report(report,gate_m=gate_m,gate_n=gate_n,gate_o=gate_o)
        atomic_json(out,report)
        print("Two real Linux Worker arms completed with pinned source FILE IDs only")
    else:
        report=verify_report(
            json.loads(out.read_text(encoding="utf-8")),
            gate_m=gate_m,gate_n=gate_n,gate_o=gate_o
        )
        print("Offline Gate P OS worker file-identity replay: VERIFIED")
    good=report["native_hf_auto_once"]
    bad=report["manual_plus_native_hf_auto"]
    print("Pinned HF dataset commit:",report["source_revision"])
    print("Original HF frozen file identities:",report["real_file_identity_count"])
    print("Native actual Worker PIDs:",good["actual_linux_worker_pids"])
    print("Double actual Worker PIDs:",bad["actual_linux_worker_pids"])
    print("Native real-file-ID coverage:",good["covered_source_file_identifiers"],"of",SOURCE_FILE_COUNT)
    print("Manual + HF native real-file-ID coverage:",
          bad["covered_source_file_identifiers"],"of",SOURCE_FILE_COUNT)
    print("Missing source file paths in local identity replay:",
          bad["missing_source_file_identifiers"])
    print("Actual remote Parquet records read:",False)
    print("Original PR27 DataLoader ran:",False)
    print("No source text in workers, no model or GPU")
    print("Saved:",out)


if __name__=="__main__":
    main()
