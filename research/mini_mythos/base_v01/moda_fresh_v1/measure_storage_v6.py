"""Target stdlib complete-scope storage forecast; no model or new-data calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import execute_once_v6 as executor

MISC_EXTERNAL_ALLOWANCE=512*1024


def require(value,why):
    if not value:raise executor.Stop("BLOCKED",why)
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
def write(path,value):
    data=encoded(value)
    with path.open("xb") as stream:stream.write(data)
    return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}


def forecast(protected,payload,base_state,adapter_rows):
    require(payload.get("Status")=="PASS","Serialized worker/auditor payload proof not PASS")
    require(payload["Actual"]["measured_payload_both_copies_bytes"]==2*payload["Actual"]["measured_payload_external_bytes"],"Payload dual-copy accounting mismatch")
    packed,receipt=executor.storage_codec.pack(protected)
    states={}
    for row in adapter_rows["rows"]:
        key=row["arm"]+"_"+str(row["train_seed"])
        require(key not in states and row["arm"] in ("shared","depth") and row["train_seed"] in (4101,4202),"Frozen adapter metadata coverage")
        states[key]=row["state"]
    require(len(base_state)==63 and len(states)==4,"Exact63 base states and four adapters")
    # Before/after x external/public for both actual frozen state schemas.
    state_bytes=4*(len(encoded(base_state))+len(encoded(states)))
    parts={"worker_and_auditor_payload_both_copies":payload["Actual"]["measured_payload_both_copies_bytes"],
           "complete_protected_gzip_both_copies":2*len(packed),
           "frozen_base_and_adapter_before_after_both_copies":state_bytes,
           "remaining_operator_environment_tests_logs_both_copies_allowance":2*MISC_EXTERNAL_ALLOWANCE,
           "git_and_finalization_allowance":executor.FINALIZATION_ALLOWANCE,
           "final_inventory_gzip_growth_both_copies_allowance":2*executor.FINAL_INVENTORY_DELTA_LIMIT}
    total=sum(parts.values())
    return {"parts":parts,"projected_total_nonraw_bytes":total,"metadata_budget_bytes":executor.METADATA_BUDGET,
            "headroom_bytes":executor.METADATA_BUDGET-total,"full_inventory_receipt":receipt,
            "assumptions":{"misc_per_external_or_public_copy_bytes":MISC_EXTERNAL_ALLOWANCE,
                "misc_includes":"environment/runtime/bridges/sentinel/completion; operator checks+commands+resource/git/environment snapshots; all development reports and stdout/stderr; custody/summary. Source export/checkpoint/manifests and Git objects are covered by4MiB finalization.",
                "raw_bytes":executor.RAW_LOGITS_BUDGET,"reserve_bytes":executor.DISK_RESERVE,
                "no_protected_path_or_payload_field_removed":True,
                "forecast_is_not_a_mathematical_compression_bound":True}},receipt


def main():
    cli=argparse.ArgumentParser();cli.add_argument("--expected-head",required=True);cli.add_argument("--payload-report",type=Path,required=True);args=cli.parse_args()
    report={"Purpose":"Exact target complete historical custody scope and new evidence capacity admission","Environment":{"python":sys.version,"codespace":os.environ.get("CODESPACE_NAME"),"stdlib_only":True},
        "Input":{"base":executor.BASE,"source_head":args.expected_head,"payload_report":str(args.payload_report)},
        "Expected":{"all_history_paths":executor.HISTORY_COUNT,"all_prior_v1_v2_pins_preserved":True,"max_new_nonraw_bytes":executor.METADATA_BUDGET,"unchanged_free_reserve_bytes":executor.DISK_RESERVE,"model_calls":0,"new_source_acquisitions":0},
        "Actual":{"model_calls":0,"new_source_acquisitions":0},"Status":"BLOCKED"}
    source_receipt=HERE/"MODEL_STORAGE_PREFLIGHT_V6.json";budget_path=HERE/"MODEL_DEVELOPMENT_EVIDENCE_BUDGET_V6.json"
    for p in (executor.STORAGE_PREFLIGHT,source_receipt,budget_path):
        if p.exists():print("BLOCKED: existing storage preflight retained; no overwrite/retry");return 2
    try:
        require(os.environ.get("CODESPACE_NAME")==executor.SPACE,"Designated Codespace required")
        require(executor.REPO==executor.EXPECTED_REPO,"Designated source worktree required")
        require(bool(sys.flags.isolated) and sys.dont_write_bytecode,"Require Python -I -B")
        require(executor.git_state(executor.REPO)=={"head":args.expected_head,"status":""},"Frozen clean storage-measurement source required")
        require(executor.git(executor.REPO,"branch","--show-current")==executor.BRANCH,"Current branch binding")
        require(not executor.RUN.exists() and not executor.active_workers(),"No formal run/other workers")
        states={str(executor.REPO):executor.git_state(executor.REPO)}
        for p,head in executor.CHECKOUTS.items():
            states[p]=executor.git_state(p);require(states[p]=={"head":head,"status":""},"Original checkout changed: "+p)
        states[str(executor.MAIN_TREE)]=executor.git_state(executor.MAIN_TREE)
        pins=executor.protected_inputs();data_gate=executor.validate_data_audit(pins);protected=executor.collect_protected(states,pins)
        coverage=executor.prior_scope_preserved(protected)
        payload=json.loads(args.payload_report.read_bytes())
        base_state=json.loads((executor.OLD_RUN/"worker/public/base_state_before.json").read_bytes())
        adapters=json.loads((executor.OLD_RUN/"worker/public/adapters.json").read_bytes())
        budget,receipt=forecast(protected,payload,base_state,adapters)
        current,existing=executor.inventory_parts(protected);_,old_receipt=executor.storage_codec.pack(existing)
        report["Actual"].update(budget,coverage=coverage,independent_data_gate=data_gate,current_repository_entries=current,existing_inventory_receipt=old_receipt,payload_report_pin=executor.info(args.payload_report),disk_free_before_bytes=shutil.disk_usage(executor.REPO).free)
        require(budget["projected_total_nonraw_bytes"]<=executor.METADATA_BUDGET,"Full fields/scope exceed12MiB nonraw allocation")
        require(receipt["compressed"]["bytes"]<=executor.storage_codec.COMPRESSED_LIMIT,"Complete lossless inventory exceeds2MiB")
        require(not set(sys.modules)&{"torch","numpy","pyarrow","tokenizers","parcae_lm","receval","transformers"},"Forbidden non-stdlib import")
        report["Status"]="PASS"
        budget_report={"Purpose":"Combined actual-schema serialized payload and complete target inventory budget","Environment":report["Environment"],"Input":report["Input"],"Expected":{"projected_total_nonraw_bytes_lte":executor.METADATA_BUDGET},"Actual":budget,"Status":"PASS"}
        planned=len(encoded(report))*2+len(encoded(budget_report))
        require(shutil.disk_usage(executor.REPO).free>=executor.REQUIRED_DISK_BYTES+planned,"Formal admission floor unavailable after planned storage proof files")
        write(budget_path,budget_report)
    except Exception as exc:
        report["Status"]=getattr(exc,"status","BLOCKED");report["Actual"]["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    # Preserve an exact external/source stop receipt, including a negative forecast.
    write(executor.STORAGE_PREFLIGHT,report);write(source_receipt,report)
    print(json.dumps({"Status":report["Status"],"scope":report["Actual"].get("coverage"),"projected_total_nonraw_bytes":report["Actual"].get("projected_total_nonraw_bytes"),"headroom_bytes":report["Actual"].get("headroom_bytes"),"error":report["Actual"].get("error")}))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
