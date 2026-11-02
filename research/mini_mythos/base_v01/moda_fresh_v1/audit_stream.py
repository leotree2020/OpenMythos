"""Independent NumPy stream audit and final receipt reaggregation; no Torch import."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import struct
import sys
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_fresh as contract


def require(okay,reason):
    if not okay:raise ValueError(reason)


def compute(np,raw,targets):
    require(len(raw)==contract.RAW_BYTES,"Exactly8MiB streamed scored matrix")
    require(len(targets)==64 and all(type(x)is int and 0<=x<32768 for x in targets),"64 scored targets")
    values=np.frombuffer(raw,dtype="<f4").reshape(64,32768)
    require(bool(np.isfinite(values).all()),"All2097152 logits finite")
    x=values.astype(np.float64);maximum=x.max(axis=1);gold=x[np.arange(64),np.asarray(targets)]
    shifted=np.log(np.exp(x-maximum[:,None]).sum(axis=1));nll=(maximum-gold)+shifted
    predictions=np.argmax(values,axis=1);top1=x[np.arange(64),predictions].copy()
    x[np.arange(64),predictions]=-np.inf;second=np.argmax(x,axis=1);top2=x[np.arange(64),second].copy()
    columns=dict(nll=nll.tolist(),predictions=predictions.tolist(),gold=gold.tolist(),max=maximum.tolist(),shifted_logsumexp=shifted.tolist(),
        logsumexp=(maximum+shifted).tolist(),top1=top1.tolist(),top2=top2.tolist(),top2_indices=second.tolist(),margin=(top1-top2).tolist())
    chunks=[]
    for i,start in enumerate(range(0,len(raw),1048576)):
        chunk=raw[start:start+1048576];c=np.frombuffer(chunk,dtype="<f4").astype(np.float64)
        chunks.append(dict(index=i,offset=start,bytes=len(chunk),sha256=contract.sha(chunk),sum64=float(c.sum()),sum_squares64=float((c*c).sum()),min64=float(c.min()),max64=float(c.max())))
    return dict(raw=dict(bytes=len(raw),sha256=contract.sha(raw)),columns=columns,chunks=chunks,finite_components=2097152,
        metrics=dict(nll_mean=float(nll.mean()),nll_sum=float(nll.sum()),correct=int((predictions==np.asarray(targets)).sum()),target_count=64))


def compare_worker(row,result):
    a=row["worker_per_token"];b=result["columns"]
    require(len(a["nll"])==len(a["predictions"])==64,"64 worker token metrics")
    require(all(type(x) in (int,float) and math.isfinite(x) for x in a["nll"]),"Finite worker token metrics")
    require(max(abs(x-y) for x,y in zip(a["nll"],b["nll"]))<=1e-10,"Independent per-token NLL")
    require(a["predictions"]==b["predictions"],"Independent exact argmax")
    for k in ("nll_mean","nll_sum"):
        require(math.isfinite(row[k]) and abs(row[k]-result["metrics"][k])<=1e-10,"Independent aggregate "+k)
    for k in ("correct","target_count"):require(row[k]==result["metrics"][k],"Independent count "+k)


def metrics_from_columns(columns,targets):
    keys=("nll","predictions","gold","max","shifted_logsumexp","logsumexp","top1","top2","top2_indices","margin")
    require(set(columns)==set(keys) and all(len(columns[k])==64 for k in keys),"Complete64-token audit columns")
    for k in keys:
        if k in ("predictions","top2_indices"):
            require(all(type(v)is int and 0<=v<32768 for v in columns[k]),"Valid prediction IDs")
        else:require(all(type(v)in(int,float) and math.isfinite(v) for v in columns[k]),"Finite audit columns")
    for i in range(64):
        c=columns
        require(abs(c["nll"][i]-(c["max"][i]-c["gold"][i]+c["shifted_logsumexp"][i]))<=1e-10,"Compact stable NLL identity")
        require(abs(c["logsumexp"][i]-(c["max"][i]+c["shifted_logsumexp"][i]))<=1e-10,"Compact logsumexp identity")
        require(c["top1"][i]==c["max"][i] and c["predictions"][i]!=c["top2_indices"][i],"Compact top IDs")
        require(c["margin"][i]>=0 and abs(c["margin"][i]-(c["top1"][i]-c["top2"][i]))<=1e-10,"Compact top2 margin")
    return dict(nll_mean=math.fsum(columns["nll"])/64,nll_sum=math.fsum(columns["nll"]),
        correct=sum(x==y for x,y in zip(columns["predictions"],targets)),target_count=64)


def validate_timing(timings,rows,data):
    plan=independent_schedule();require(len(timings)==400,"400 timed endpoints")
    by={contract.rowkey(r):r for r in rows};paired={}
    for observed,expected in zip(timings,plan):
        require(all(observed[k]==v for k,v in expected.items()),"Frozen cyclic/reverse Latin ordering")
        require(observed["article_id"]==data[expected["article_index"]]["id"],"Timing article identity")
        require(type(observed["endpoint_wall_ns"])is int and observed["endpoint_wall_ns"]>0 and type(observed["endpoint_cpu_ns"])is int and observed["endpoint_cpu_ns"]>0,"Valid complete endpoint durations")
        ref=by[contract.rowkey(observed)]
        require(observed["logits_sha256"]==ref["logits_sha256"] and observed["observer"]==ref["observer"],"Both timing passes exact first-pass outputs")
        pair=expected["article_index"],expected["eval_seed"]
        state=contract.stable(observed["observer"])
        require(state["seed"]==expected["eval_seed"],"Actual paired seed")
        if pair not in paired:paired[pair]=state
        require(state==paired[pair],"All5conditions and2passes paired actual h0/RNG")
    for p in range(2):
        for a in range(5):
            for slot in range(5):
                require(sum(r["pass_index"]==p and r["arm_index"]==a and r["slot"]==slot for r in timings)==8,"Exact balanced arm-position counts")


def independent_schedule():
    plan=[]
    for index in range(400):
        pass_index=index//200;within=index%200;case=within//5;slot=within%5
        arm_index=(case+(slot if pass_index==0 else 4-slot))%5
        arm,train_seed=contract.ARMS[arm_index]
        plan.append(dict(call_index=index,pass_index=pass_index,case=case,article_index=case//2,
            eval_seed=5101 if case%2==0 else 5202,slot=slot,arm_index=arm_index,arm=arm,train_seed=train_seed))
    return plan


def independent_aggregate(rows,timings):
    """Separate auditor implementation; never call worker aggregate/label/schedule."""
    require(len(rows)==200 and len(timings)==400,"Complete final population")
    articles=sorted({r["article_id"] for r in rows});require(len(articles)==20,"Twenty equal-weight articles")
    by={(r["arm"],r["train_seed"],r["eval_seed"],r["article_id"]):r for r in rows};require(len(by)==200,"Unique independent rows")
    means={};models={}
    for arm,seed in contract.ARMS:
        key=arm if seed is None else "%s_%d"%(arm,seed)
        group=[r for r in rows if r["arm"]==arm and r["train_seed"]==seed]
        require(len(group)==40,"Forty quality cases per model")
        total_correct=sum(r["correct"] for r in group)
        means[key]=dict(mean_nll=math.fsum(r["nll_mean"] for r in group)/40,correct=total_correct,scored_observations=2560,accuracy=total_correct/2560)
        timed=[r for r in timings if r["arm"]==arm and r["train_seed"]==seed];require(len(timed)==80,"Eighty repeated timings per model")
        durations=sorted(r["endpoint_wall_ns"] for r in timed)
        require(all(type(x)is int and x>0 for x in durations),"Positive wall duration")
        models[key]=dict(calls=80,endpoint_total_seconds=sum(durations)/1000000000,
            endpoint_median_seconds=(durations[39]+durations[40])/2000000000,endpoint_p95_seconds=durations[75]/1000000000,
            process_cpu_total_seconds=sum(r["endpoint_cpu_ns"] for r in timed)/1000000000,
            per_pass_seconds={str(p):sum(r["endpoint_wall_ns"] for r in timed if r["pass_index"]==p)/1000000000 for p in (0,1)})
    comparisons={};screens={};interpretations={}
    for left,right in (("depth","fixed32"),("depth","shared"),("shared","fixed32")):
        title=left+"_vs_"+right;seedlabels={};seedpasses=[]
        for seed in (4101,4202):
            bseed=None if right=="fixed32" else seed;deltas=[]
            for article in articles:
                d1=by[left,seed,5101,article]["nll_mean"]-by[right,bseed,5101,article]["nll_mean"]
                d2=by[left,seed,5202,article]["nll_mean"]-by[right,bseed,5202,article]["nll_mean"]
                dc=by[left,seed,5101,article]["correct"]+by[left,seed,5202,article]["correct"]-by[right,bseed,5101,article]["correct"]-by[right,bseed,5202,article]["correct"]
                deltas.append(dict(article_id=article,delta_nll=math.fsum((d1,d2))/2,delta_correct=dc))
            dn=math.fsum(x["delta_nll"] for x in deltas)/20;da=sum(x["delta_correct"] for x in deltas)/2560
            passed=dn<=-0.01 and da>=-0.01
            interpretation="IMPROVEMENT" if passed else "WORSE" if dn>=0.01 or da<-.01 else "NO_QUALIFIED_IMPROVEMENT"
            seedlabels[str(seed)]=interpretation;seedpasses.append(passed)
            comparisons[title+"_"+str(seed)]=dict(delta_nll=dn,delta_accuracy=da,per_article=deltas,
                articles_improved=sum(x["delta_nll"]<0 for x in deltas),worst_article_delta_nll=max(x["delta_nll"] for x in deltas),screen=passed,interpretation=interpretation)
        screens[title]="PASS" if seedpasses==[True,True] else "FAIL"
        interpretations[title]=dict(per_seed=seedlabels,combined=seedlabels["4101"] if seedlabels["4101"]==seedlabels["4202"] else "MIXED")
    ratios={};perpass={};paired=[]
    for seed in (4101,4202):
        for reference in ("fixed32","shared_"+str(seed)):
            hname="depth_"+str(seed);comparison=hname+"_vs_"+reference
            ratios[comparison]=models[hname]["endpoint_total_seconds"]/models[reference]["endpoint_total_seconds"]
            perpass[comparison]={str(p):models[hname]["per_pass_seconds"][str(p)]/models[reference]["per_pass_seconds"][str(p)] for p in (0,1)}
            refarm,refseed=("fixed32",None) if reference=="fixed32" else ("shared",seed)
            for article in articles:
                htotal=ctotal=hn=cn=0
                for r in timings:
                    if r["article_id"]!=article:continue
                    if r["arm"]=="depth" and r["train_seed"]==seed:htotal+=r["endpoint_wall_ns"];hn+=1
                    if r["arm"]==refarm and r["train_seed"]==refseed:ctotal+=r["endpoint_wall_ns"];cn+=1
                require(hn==cn==4,"Four paired timing observations per article/model")
                paired.append(dict(comparison=comparison,article_id=article,history_mean_seconds=htotal/4000000000,reference_mean_seconds=ctotal/4000000000,ratio=htotal/ctotal))
    return dict(means=means,comparisons=comparisons,scientific_screens=screens,result_interpretations=interpretations,
        timing=dict(models=models,ratios=ratios,per_pass_ratios=perpass,paired_per_article=paired,screen="NOT ASSESSED",
            scope="Pretokenized full instrumented CPU prediction endpoint; excludes raw serialization/audit/I/O; whole worker wall separately reported"))


def same_recursive(a,b,tolerance=1e-10):
    if type(a)is dict:return type(b)is dict and set(a)==set(b) and all(same_recursive(v,b[k],tolerance) for k,v in a.items())
    if type(a)is list:return type(b)is list and len(a)==len(b) and all(same_recursive(x,y,tolerance) for x,y in zip(a,b))
    if type(a)is float:return type(b)in(int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tolerance
    return type(a)is type(b) and a==b


def final_audit(spec,worker,np,check):
    worker=Path(worker);data=contract.validate_data(contract.read(spec["data_path"]))
    completion=contract.read(worker/"public/completion.json")
    check("Exact successful zero-training worker",completion["Status"]=="PASS" and completion["preservation"]=="PASS" and completion["Actual"]==contract.EXPECTED)
    checks=contract.read_checks(worker/"public/checks.jsonl.gz")
    check("All recorded checks reconciled",all(c["Status"]=="PASS" for c in checks) and completion["checks"]==dict(PASS=len(checks),FAIL=0,BLOCKED=0))
    before=contract.read(worker/"public/base_state_before.json");after=contract.read(worker/"public/base_state_after.json")
    check("Native63states unchanged",len(before)==63 and before==after)
    b=contract.read(worker/"public/adapters_before.json");a=contract.read(worker/"public/adapters_after.json")
    old_adapters=contract.read(spec["old_adapter_rows_path"])["rows"]
    check("All4adapterstates frozen",b==a=={contract.name(r["arm"],r["train_seed"]):r["state"] for r in old_adapters})
    bridges=contract.read(worker/"public/oldbridges.json")
    check("Five prior exact bridges",bridges["Status"]=="PASS" and len(bridges["rows"])==5 and [(r["arm"],r["train_seed"]) for r in bridges["rows"]]==list(contract.ARMS))
    oldrows=contract.read(spec["old_evaluation_path"])["rows"];baserows=contract.read(spec["baseline_evaluation_path"])["rows"]
    for row in bridges["rows"]:
        candidates=[x for x in (baserows if row["arm"]=="fixed32" else oldrows) if contract.rowkey(x)==contract.rowkey(row)]
        check("Frozen bridge evidence "+contract.name(row["arm"],row["train_seed"]),len(candidates)==1 and row["logits_sha256"]==candidates[0]["logits_sha256"]
            and contract.stable(row["observer"])==contract.stable(candidates[0]["observer"]))
    rows=contract.read(worker/"public/evaluation.json.gz")["rows"];timings=contract.read(worker/"public/timing.json.gz")["rows"]
    check("Exactly200 unique first-pass rows",len(rows)==200 and len({contract.rowkey(r) for r in rows})==200)
    recomputed=[];audit_pins={}
    for number,row in enumerate(rows):
        expected=independent_schedule()[number]
        check("First-pass frozen order "+str(number),all(row[k]==v for k,v in expected.items()))
        sample=data[row["article_index"]];targets=sample["tokens"][65:129]
        check("Row token/article binding "+str(number),row["article_id"]==sample["id"] and row["targets_sha256"]==contract.sha(struct.pack("<64q",*targets))
            and row["shape"]==[64,32768] and row["dtype"]=="float32-le")
        rowpath=worker/("public/rows/row_%03d.json.gz"%number);auditpath=worker/("public/row_audits/row_%03d.json.gz"%number)
        check("Row copy identity "+str(number),contract.read(rowpath)==row and row["row_input_file"]==str(rowpath.relative_to(worker)) and row["row_audit_file"]==str(auditpath.relative_to(worker)))
        receipt=contract.read(auditpath);audit_pins[str(auditpath)]=contract.pin(auditpath)
        check("Live independent stream audit "+str(number),receipt["Status"]=="PASS" and receipt["Input"]["identity"]==contract.identity(row)
            and receipt["Input"]["row_input"]==contract.pin(rowpath) and receipt["Input"]["spec_sha256"]==contract.pin(spec["spec_path"])["sha256"]
            and receipt["Actual"]["raw"]==dict(bytes=contract.RAW_BYTES,sha256=row["logits_sha256"]) and receipt["Actual"]["finite_components"]==2097152)
        check("Auditor environment and data binding "+str(number),receipt["Environment"]["numpy"]=="1.26.4" and receipt["Environment"]["development_only"] is False
            and receipt["Environment"]["executable"]==contract.DATA_PYTHON and receipt["Input"]["data_sha256"]==spec["data_sha256"])
        process=contract.read(worker/("public/row_audits/process_%03d.json.gz"%number))
        check("Audit process successful "+str(number),process["returncode"]==0 and process["command"]==[contract.DATA_PYTHON,"-I","-B",str(Path(__file__).resolve()),"--spec",str(spec["spec_path"]),"--row",str(rowpath),"--output",str(auditpath)])
        branch=row["branch_trace"];arm=row["arm"]
        check("Full32 native/history route "+str(number),row["observer"]["core_block_calls"]==[32,32] and row["observer"]["adapter_calls"]==32
            and branch["arm"]==arm and branch["writer_calls"]==(0 if arm=="fixed32" else 32)
            and branch["write_depths"]==([] if arm=="fixed32" else list(range(32)))
            and branch["read_lengths"]==([] if arm=="fixed32" else list(range(32)) if arm=="depth" else [0]*32))
        metrics=metrics_from_columns(receipt["Actual"]["columns"],targets)
        check("Root token metric reconstruction "+str(number),same_recursive(metrics,receipt["Actual"]["metrics"]) and all(abs(metrics[k]-row[k])<=1e-10 for k in metrics))
        compare_worker(row,receipt["Actual"])
        chunks=receipt["Actual"]["chunks"]
        check("8 bound chunk descriptors "+str(number),len(chunks)==8 and all(c["index"]==i and c["offset"]==i*1048576 and c["bytes"]==1048576
            and len(c["sha256"])==64 and all(math.isfinite(c[k]) for k in ("sum64","sum_squares64","min64","max64")) for i,c in enumerate(chunks)))
        recomputed.append({**row,**metrics})
    validate_timing(timings,rows,data);check("All400 balanced timing/identity entries",True)
    summary=independent_aggregate(recomputed,timings);saved=contract.read(worker/"public/results.json")
    check("Scientific and timing aggregates independently reconstructed",same_recursive(summary,saved))
    sentinel=contract.read(worker/"public/sentinel.json");last=timings[-1]
    check("Predeclared last-call sentinel",last["call_index"]==399 and last["article_index"]==19 and last["eval_seed"]==5202 and last["arm"]=="depth" and last["train_seed"]==4202
        and sentinel["identity"]==contract.identity(last) and sentinel["path"]=="private/final_sentinel.bin")
    path=worker/"private/final_sentinel.bin";raw=path.read_bytes()
    check("Retained sentinel exact complete matrix",contract.pin(path)==sentinel["raw"]==dict(bytes=contract.RAW_BYTES,sha256=last["logits_sha256"]))
    row=next(r for r in rows if contract.rowkey(r)==contract.rowkey(last));result=compute(np,raw,data[19]["tokens"][65:129]);receipt=contract.read(worker/row["row_audit_file"])
    check("Final sentinel independent full recomputation",same_recursive(result,receipt["Actual"]))
    check("Exactly one retained full raw",list(worker.glob("private/*.bin"))==[path])
    check("No forbidden numerical/model libraries",not any(n.split(".")[0] in ("torch","parcae_lm","receval","transformers") for n in sys.modules))
    return {**summary,"rows":200,"repeats":200,"retained_sentinel":sentinel,"live_full_audited_rows":200,
        "retrospective_full_rows_recomputed":1,"retrospective_full_rows_unavailable":199,"audit_receipt_pins":audit_pins,
        "worker_seconds":completion["seconds"],"load_seconds":completion["load_seconds"],"audit_seconds":completion["audit_seconds"],"serialization_seconds":completion["serialization_seconds"],
        "peak_rss_bytes":completion["peak_rss_bytes"],"evidence_limit":"One full final sentinel recomputed;199 other full fresh matrices audited live through stdin, compact records cannot reconstruct them"}


def main():
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--row",type=Path);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--final",action="store_true");p.add_argument("--worker",type=Path);args=p.parse_args()
    report=dict(Purpose="Independent NumPy fresh-text stream audit" if not args.final else "Independent fresh-text final audit",Environment={},Input={},Expected="Frozen byte-bound numeric evidence",Actual={},Status="NOT TESTED",checks=[])
    def check(purpose,okay,actual=None):
        report["checks"].append(dict(Purpose=purpose,Expected=True,Actual=actual,Status="PASS" if okay else "FAIL"));require(okay,purpose)
    spec=None
    try:
        require(args.spec.is_absolute() and args.output.is_absolute(),"Absolute audit paths")
        spec=contract.read(args.spec);spec["spec_path"]=str(args.spec.resolve())
        require(platform.system()=="Linux" and platform.python_version()=="3.12.3" and sys.executable==contract.DATA_PYTHON and sys.flags.isolated and sys.dont_write_bytecode
            and os.environ.get("CODESPACE_NAME")==contract.SPACE,"Frozen isolated target audit environment")
        import numpy as np
        require(np.__version__=="1.26.4","Frozen NumPy version")
        report["Environment"]=dict(python=sys.version,numpy=np.__version__,executable=sys.executable,development_only=False)
        require(contract.pin(spec["data_path"])["sha256"]==spec["data_sha256"],"Frozen fresh input bytes")
        report["Input"]=dict(spec_sha256=contract.pin(args.spec)["sha256"],data_sha256=spec["data_sha256"])
        if args.final:
            require(args.worker is not None and args.worker.is_absolute() and args.row is None,"Final audit CLI")
            report["Actual"]=final_audit(spec,args.worker,np,check)
        else:
            require(args.row is not None and args.row.is_absolute() and args.worker is None,"Stream audit CLI")
            row=contract.read(args.row);data=contract.validate_data(contract.read(spec["data_path"]))
            sample=data[row["article_index"]];targets=sample["tokens"][65:129]
            require(row["pass_index"]==0 and row["article_id"]==sample["id"] and row["targets_sha256"]==contract.sha(struct.pack("<64q",*targets)),"Auditor independent target binding")
            raw=sys.stdin.buffer.read(contract.RAW_BYTES+1)
            require(len(raw)==contract.RAW_BYTES and contract.sha(raw)==row["logits_sha256"],"Exact bounded stream bytes/hash")
            result=compute(np,raw,targets);compare_worker(row,result)
            report["Input"].update(identity=contract.identity(row),row_input=contract.pin(args.row));report["Actual"]=result
        require(not any(n.split(".")[0] in ("torch","parcae_lm","receval","transformers") for n in sys.modules),"Independent auditor imports")
        report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]="BLOCKED" if isinstance(exc,(OSError,MemoryError,KeyboardInterrupt)) else "FAIL"
        report["error"]=dict(type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
    report["check_counts"]={s:sum(c["Status"]==s for c in report["checks"]) for s in ("PASS","FAIL")}
    report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    contract.save(args.output,report,Path(spec["run_root"]) if spec else None,report["Status"]!="PASS")
    print(json.dumps(dict(Status=report["Status"],checks=report["check_counts"],error=report.get("error"))))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
