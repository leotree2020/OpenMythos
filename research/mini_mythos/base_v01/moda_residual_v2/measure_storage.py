"""Read-only exact target storage measurement; no model import or formal run."""
from __future__ import annotations
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))
import execute_once as O


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output != O.STORAGE_PREFLIGHT or args.output.exists():
        parser.error("Only the new fixed STORAGE_PREFLIGHT path is allowed; no overwrite")
    report = {"Purpose":"Exact shared-collector storage preflight before execution freeze",
        "Environment":{"python":sys.version,"executable":sys.executable,"mode":"Standard-library read-only inventory; no model"},
        "Input":{"base":O.BASE,"repo":str(O.REPO)},
        "Expected":"Complete prior scope retained; lossless roundtrip; current gzip plus64KiB planning margin+4KiB overhead <=unchanged2MiB;256MiB reserve retained",
        "Actual":{},"Status":"NOT TESTED","utc":O.utc()}
    try:
        if not (platform.system()=="Linux" and os.environ.get("CODESPACE_NAME")==O.SPACE and sys.flags.isolated and sys.dont_write_bytecode):
            raise O.Stop("BLOCKED","Designated isolated Codespace preflight required")
        if O.active_workers():raise O.Stop("BLOCKED","Active experiment worker prevents measurement")
        if O.REPO.resolve()!=O.EXPECTED_REPO or O.git(O.REPO,"branch","--show-current")!=O.BRANCH:
            raise O.Stop("FAIL","Preflight branch/worktree differs")
        head=O.git(O.REPO,"rev-parse","HEAD")
        if O.git(O.REPO,"merge-base",O.BASE,head)!=O.BASE or O.git(O.REPO,"status","--porcelain"):
            raise O.Stop("FAIL","Preflight requires clean descendant of stated base")
        states={str(O.REPO):O.git_state(O.REPO)}
        for name, expected in O.CHECKOUTS.items():
            state=O.git_state(name)
            if state!={"head":expected,"status":""}:raise O.Stop("FAIL","Historical checkout differs: "+name)
            states[name]=state
        states[str(O.MAIN_TREE)]=O.git_state(O.MAIN_TREE)
        protected=O.collect_protected(states,O.protected_inputs())
        coverage=O.prior_scope_preserved(protected)
        blob, receipt=O.storage_codec.pack(protected)
        if O.storage_codec.unpack(blob,receipt)!=protected:raise O.Stop("FAIL","Exact full-map roundtrip differs")
        current, existing=O.inventory_parts(protected)
        _, existing_receipt=O.storage_codec.pack(existing)
        projected=receipt["compressed"]["bytes"]+O.FINAL_INVENTORY_DELTA_LIMIT+4096
        free=shutil.disk_usage(O.REPO).free
        report["Actual"]={"preparation_commit":head,"record_count":len(protected),"complete_inventory_receipt":receipt,
            "existing_inventory_receipt":existing_receipt,"current_repository_entries":current,
            "prior_scope":coverage,"git_states":states,"compressed_planning_upper_bytes":projected,
            "final_inventory_delta_limit":O.FINAL_INVENTORY_DELTA_LIMIT,"compression_planning_overhead":4096,
            "physical_manifest_limit":O.storage_codec.COMPRESSED_LIMIT,"disk_free_bytes":free,
            "formal_disk_floor":O.REQUIRED_DISK_BYTES,"disk_reserve":O.DISK_RESERVE,
            "roundtrip_exact":True,"formal_run_started":False,"model_calls":0,
            "scope":"All declared physical paths preserved; only deterministic lossless serialization changes. Existing paths/pins bind exactly at formal preflight; final v2 source inventory changes have a64KiB metadata cap and actual full gzip must still fit2MiB."}
        if projected>O.storage_codec.COMPRESSED_LIMIT:raise O.Stop("BLOCKED","Measured storage forecast exceeds unchanged2MiB envelope")
        if free<O.REQUIRED_DISK_BYTES:raise O.Stop("BLOCKED","Current free space below unchanged formal disk floor")
        if any(name.split(".")[0] in ("torch","numpy","parcae_lm","receval") for name in sys.modules):
            raise O.Stop("FAIL","Numerical/model import during storage-only preflight")
        report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]=getattr(exc,"status","BLOCKED" if isinstance(exc,(OSError,O.storage_codec.StorageLimitError)) else "FAIL")
        report["error"]={"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    O.save(args.output,report)
    a=report["Actual"]
    print(json.dumps({"Status":report["Status"],"error":report.get("error"),"records":a.get("record_count"),
        "compressed":a.get("complete_inventory_receipt",{}).get("compressed"),"planning_upper":a.get("compressed_planning_upper_bytes"),
        "free":a.get("disk_free_bytes"),"output":str(args.output)},allow_nan=False))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
