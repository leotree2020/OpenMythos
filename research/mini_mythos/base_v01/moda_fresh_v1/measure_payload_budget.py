"""Development-only serialized payload forecast, no real model or project text."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_fresh as f
import audit_stream as audit


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path,required=True);args=parser.parse_args()
    import numpy as np
    rng=np.random.default_rng(74123);results=[]
    # Twenty independently populated FP32 matrices give realistic varying numeric
    # spellings/compression. Actual runtime size guards remain the hard bound.
    for _ in range(20):
        x=rng.uniform(-50,50,size=(64,32768)).astype("<f4")
        results.append(audit.compute(np,x.tobytes(),[0]*64))
    del x
    counts={};maxima={};rows=[];timings=[];first={}
    def add(category,value,zipped=False):
        n=len(f.encoded(value,zipped));counts[category]=counts.get(category,0)+n;maxima[category]=max(maxima.get(category,0),n)
    spec_sha=f.sha(b"budget-spec");data_sha=f.sha(b"budget-data")
    for p in f.schedule():
        article=f.sha(("article%02d"%p["article_index"]).encode());key=p["case"],p["arm_index"]
        observer=dict(h0_sha256=f.sha(str(p["case"]).encode()),rng_before_sha256=f.sha(str(p["eval_seed"]).encode()),rng_after_sha256=f.sha(("after"+str(p["eval_seed"])).encode()),seed=p["eval_seed"],core_block_calls=[32,32],adapter_calls=32)
        if p["pass_index"]:
            result=results[first[key]%20]
        else:
            first[key]=len(rows);result=results[len(rows)%20]
        time={**p,"article_id":article,"observer":observer,"logits_sha256":result["raw"]["sha256"],"endpoint_wall_ns":1902345678+p["call_index"]*11731,"endpoint_cpu_ns":2890765432+p["call_index"]*37111};timings.append(time)
        if p["pass_index"]:continue
        n=len(rows);arm=p["arm"];rowfile="public/rows/row_%03d.json.gz"%n;auditfile="public/row_audits/row_%03d.json.gz"%n
        row={**p,"article_id":article,"observer":observer,"logits_sha256":result["raw"]["sha256"],**result["metrics"],
            "worker_per_token":{k:result["columns"][k] for k in ("nll","predictions")},"targets_sha256":f.sha(b"target"),"shape":[64,32768],"dtype":"float32-le",
            "row_input_file":rowfile,"row_audit_file":auditfile,"branch_trace":dict(arm=arm,writer_calls=0 if arm=="fixed32" else 32,
                write_depths=[] if arm=="fixed32" else list(range(32)),read_lengths=[] if arm=="fixed32" else list(range(32)) if arm=="depth" else [0]*32)}
        rows.append(row);add("individual_rows_gzip",row,True)
        raw=f.encoded(row,True)
        receipt=dict(Purpose="Independent NumPy fresh-text stream audit",Environment=dict(python="3.12.3 (main, Apr 13 2026) [GCC 13.3.0]",numpy="1.26.4",executable=f.DATA_PYTHON,development_only=False),
            Input=dict(spec_sha256=spec_sha,data_sha256=data_sha,identity=f.identity(row),row_input=dict(bytes=len(raw),sha256=f.sha(raw))),Expected="Frozen byte-bound numeric evidence",Actual=result,Status="PASS",checks=[],check_counts=dict(PASS=0,FAIL=0),utc="2026-11-02T12:34:56.789012+00:00")
        add("row_audits_gzip",receipt,True)
        command=[f.DATA_PYTHON,"-I","-B","/workspaces/"+"a"*170+"/audit_stream.py","--spec","/workspaces/"+"b"*190+"/spec.json","--row","/workspaces/"+"c"*180+"/"+rowfile,"--output","/workspaces/"+"d"*170+"/"+auditfile]
        add("audit_process_gzip",dict(command=command,returncode=0,stdout=json.dumps(dict(Status="PASS",checks=dict(PASS=0,FAIL=0),error=None))+"\n",stderr=""),True)
    add("combined_evaluation_gzip",dict(rows=rows),True);add("combined_timing_gzip",dict(rows=timings),True)
    summary=f.aggregate(rows,timings);add("results_json",summary)
    # A successful run has approximately2,800 checks;3,200 distinct long labels
    # provide an explicit forecast allowance. Full logs are not suppressed.
    checks=[dict(Purpose="Bounded fixture input/state/identity/scoring/route check number%04d"%i,Expected=True,Actual=dict(fixture_number=i,detail="unchanged exact byte validation"),Status="PASS") for i in range(3200)]
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        log=f.CheckLog(Path(tmp)/"checks.jsonl.gz")
        for check in checks:log.write(f.encoded(check))
        log.close();assert f.read_checks(log.path)==checks
        counts["worker_checks_jsonl_gzip"]=log.path.stat().st_size;maxima["worker_checks_jsonl_gzip"]=log.path.stat().st_size
    finalchecks=[dict(Purpose="Independent complete per-row identity/numerics/byte/command binding number%04d"%i,Expected=True,Actual=None,Status="PASS") for i in range(1900)]
    auditpins={"/workspaces/mythos-evidence/base_v01/moda_fresh/attempt-v1/worker/public/row_audits/row_%03d.json.gz"%i:dict(bytes=16384,sha256=f.sha(str(i).encode())) for i in range(200)}
    add("final_audit_gzip",dict(Purpose="Independent fresh-text final audit",Environment=dict(python="3.12.3",numpy="1.26.4",executable=f.DATA_PYTHON,development_only=False),Input=dict(spec_sha256=spec_sha,data_sha256=data_sha),Expected="Frozen byte-bound numeric evidence",Actual={**summary,"audit_receipt_pins":auditpins,"rows":200,"repeats":200,"live_full_audited_rows":200,"retrospective_full_rows_recomputed":1,"retrospective_full_rows_unavailable":199},Status="PASS",checks=finalchecks,check_counts=dict(PASS=1900,FAIL=0),utc="2026-11-02T12:34:56.789012+00:00"),True)
    subtotal=sum(counts.values())
    report=dict(Purpose="Serialized fresh worker/auditor payload forecast",Environment=dict(python=sys.version,numpy=np.__version__,development_only=True),
        Input=dict(real_model=False,real_data=False,synthetic_full_matrices=20,rng_seed=74123,format="Current run_fresh/audit_stream schemas;lossless gzip where implemented;bounded long paths and varied numeric values"),
        Expected="Measure all200 first-pass receipts/rows,400 timings,full3,200-check and1,900-final-check logs without pruning fields;combine with target fullscope and explicit remaining allowances beforefreeze",
        Actual=dict(single_external_copy_bytes=counts,max_per_artifact_bytes=maxima,measured_payload_external_bytes=subtotal,measured_payload_both_copies_bytes=2*subtotal),Status="PASS",
        Unmeasured_allowances_required=["Base63 state+four adapter state reports,environment,bridges,sentinel/completion,worker stdout/stderr and exceptional logs", "Operator reports,tests,source/input manifests and custody/summary/checkpoint/public/export manifests", "Both complete protected-inventory gzip copies,actualtargetmeasurement", "Git/finalization allowance4MiB within12MiB total"],
        Limits="Forecast from synthetic serialization,notmathematical compression bound. Mustpassactualtargetbudget/runtimecaps. No numerical/scientific evidence.")
    with args.report.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    print(json.dumps(report["Actual"]))


if __name__=="__main__":main()
