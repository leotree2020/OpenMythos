"""Read-only root closure of MoDA v2: no model, Torch, NumPy, or retry.

The only write is a new acceptance-v2.json beside the sealed attempt-v2 directory.
For PASS, reaggregate audited per-token records and verify retained raw hashes.
This cannot retrospectively recover the124 discarded full candidate matrices.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import traceback

REPO=Path("/workspaces/mythos-moda-residual-cpu-v2")
PACKAGE="research/mini_mythos/base_v01/moda_residual_v2"
ROOT=REPO/PACKAGE
RUN=Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2")
OUT=RUN.parent/"acceptance-v2.json"
BRANCH="mythos-moda-residual-cpu-v2"
BASE="d5d6e74888b65b757ecef075f1bd6838f712cc77"
PRIOR=RUN.parent/"attempt-v1/protected_before.json"
PRIOR_PIN={"bytes":6460524,"sha256":"79b11ee7b68d0b84e70b14aeb29fa85b9c9f76c145a77caafb0c0b1d2ebb71a3"}
STABLE=("h0_sha256","rng_before_sha256","rng_after_sha256","seed")
IDENTITY=("arm","train_seed","eval_seed","article_id","article_index")
RAW_BYTES=8388608
MAIN_COUNTS=dict(calls_started=293,calls_completed=293,train_steps=128,eval_rows=160,
                 zero_control_calls=5,model_loads=1,adapters_saved=4,reload_calls=0)
RELOAD_COUNTS=dict(calls_started=4,calls_completed=4,train_steps=0,eval_rows=0,
                   zero_control_calls=0,model_loads=1,adapters_saved=0,reload_calls=4)


def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def lines(path):return [json.loads(line) for line in Path(path).read_text().splitlines()]
def sha(data):return hashlib.sha256(data).hexdigest()
def byte_pin(data):return {"bytes":len(data),"sha256":sha(data)}
def pin(path):
    h,n=hashlib.sha256(),0
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block);n+=len(block)
    return {"bytes":n,"sha256":h.hexdigest()}
def git_at(repo,*args):return subprocess.check_output(["git","-C",str(repo),*args],text=True,timeout=120).strip()
def git(*args):return git_at(REPO,*args)
def git_bytes(ref,path):return subprocess.check_output(["git","-C",str(REPO),"show",ref+":"+path],timeout=120)
def confined(base,relative):
    candidate=Path(relative);path=(base/candidate).resolve()
    if candidate.is_absolute() or not path.is_relative_to(base.resolve()):raise ValueError("Evidence path escapes root")
    return path
def key(row):return tuple(row[k] for k in IDENTITY[:4])
def identity(row):return {k:row[k] for k in IDENTITY}
def close(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-10
def label(nll,accuracy):
    if nll<=-.01 and accuracy>=-.01:return "IMPROVEMENT"
    if nll>=.01 or accuracy<-.01:return "WORSE"
    return "NO_QUALIFIED_IMPROVEMENT"
def workers():
    names={"execute_once.py","run_moda.py","audit_row.py","audit_moda.py","run_loop.py","run_lora.py"};found=[]
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():continue
        try:
            matched={Path(x.decode(errors="replace")).name for x in (p/"cmdline").read_bytes().split(b"\0") if x}&names
            if matched:found.append({"pid":int(p.name),"names":sorted(matched)})
        except (OSError,ProcessLookupError):pass
    return found


def verify_files(mapping,check,purpose):
    verified=0;differences=[]
    for name,expected in mapping.items():
        try:
            actual=pin(name)
            if actual!=expected:
                differences.append({"path":name,"expected":expected,"actual":actual});break
            verified+=1
        except OSError as exc:
            differences.append({"path":name,"expected":expected,"error":repr(exc)});break
    check(purpose,not differences and verified==len(mapping),
          {"expected_count":len(mapping),"verified":verified,"first_differences":differences})
    return verified


def verify_success(summary,inventory,check):
    worker=RUN/"worker";spec=read(RUN/"spec.json");data=read(spec["data_path"])
    check("Frozen data SHA",pin(spec["data_path"])["sha256"]==spec["inputs_sha256"])
    check("Frozen16+16 distinct articles",len(data["train"])==len(data["eval"])==16
          and len({r["id"] for split in ("train","eval") for r in data[split]})==32
          and all(len(r["tokens"])==129 for split in ("train","eval") for r in data[split]))
    completion=read(worker/"public/completion.json");reload=read(RUN/"reload/public/completion.json");audit=read(RUN/"audit.json")
    for name,value,budget in (("main",completion,MAIN_COUNTS),("reload",reload,RELOAD_COUNTS)):
        check(name+" exact completed budget",value["Status"]=="PASS" and value["preservation"]=="PASS" and value["Actual"]==budget)
        journal=lines((worker if name=="main" else RUN/"reload")/"public/checks.jsonl")
        counts={s:sum(r["Status"]==s for r in journal) for s in ("PASS","FAIL","BLOCKED")}
        check(name+" engineering checks reconciled",counts==value["checks"] and counts["FAIL"]==counts["BLOCKED"]==0)
        before=read((worker if name=="main" else RUN/"reload")/"public/base_state_before.json")
        after=read((worker if name=="main" else RUN/"reload")/"public/base_state_after.json")
        check(name+" native63-state identity",len(before)==63 and before==after)
    check("Independent NumPy final audit completed",audit["Status"]=="PASS" and audit["check_counts"]["FAIL"]==0
          and all(r["Status"]=="PASS" for r in audit["checks"]) and audit["Actual"]["rows"]==160
          and audit["Actual"]["retained_full_rows_recomputed"]==36 and audit["Actual"]["retrospective_full_logits_unavailable_rows"]==124)
    check("Operator scientific screens bound to final audit",summary["scientific_screens"]==summary["Actual"]["scientific_screens"]==audit["Actual"]["scientific_screens"])
    test_counts={}
    for name,expected in inventory.items():
        report=read(RUN/(Path(name).stem+"_report.json"));actual=report["Actual"];ids=expected["test_ids"]
        check("Exact target test coverage "+name,report["Status"]=="PASS" and actual["test_ids"]==ids
              and len(set(ids))==len(ids)==actual["run"]==actual["planned"]
              and all(actual[k]==0 for k in ("failures","errors","skipped","expected_failures","unexpected_successes")))
        test_counts[name]=len(ids)
    expected_labels=[Path(name).stem for name in ("test_storage_codec.py","test_startup.py","test_moda_adapter.py","test_audit.py")]+["train","reload","audit"]
    commands=summary["Actual"]["commands"]
    check("Single frozen ordered execution",[c["label"] for c in commands]==expected_labels
          and all(c["returncode"]==0 and c["child_reaped"] and not c["cleanup_errors"] and c["interruption"] is None for c in commands))
    training=lines(worker/"public/training.jsonl");by_train={(r["arm"],r["train_seed"],r["step"]):r for r in training}
    expected_training={(a,s,t) for a in ("shared","depth") for s in (4101,4202) for t in range(32)}
    check("Exactly128 unique optimizer steps",len(training)==128 and set(by_train)==expected_training)
    for arm,seed,step in sorted(expected_training):
        row=by_train[arm,seed,step]
        check("Train identity and route "+str((arm,seed,step)),row["article_id"]==data["train"][step%16]["id"]
              and row["h0_seed"]==1000000+100*seed+step and row["optimizer_step"]==step+1
              and row["targets"]==128 and row["epoch"]==step//16 and math.isfinite(row["loss"])
              and row["observer"]["adapter_calls"]==32 and row["observer"]["core_block_calls"]==[32,32])
        if arm=="depth":check("Paired training h0/RNG "+str((seed,step)),row["observer"]==by_train["shared",seed,step]["observer"])
    adapters=read(worker/"public/adapters.json");by_adapter={(r["arm"],r["train_seed"]):r for r in adapters["rows"]}
    check("Four adapters saved",adapters["Status"]=="PASS" and len(adapters["rows"])==4
          and set(by_adapter)=={(a,s) for a in ("shared","depth") for s in (4101,4202)})
    for (arm,seed),adapter in by_adapter.items():
        check("Adapter counts, frozen features and checkpoint "+str((arm,seed)),adapter["trainable_parameters"]==12288 and adapter["steps"]==32
              and adapter["features_before"]==adapter["features_after"] and all(adapter["depth_gradient_coverage"])
              and len(adapter["depth_gradient_coverage"])==32 and adapter["gradient_coverage"] is True
              and adapter["parameter_changes"]=={"o_proj":True}
              and pin(confined(worker,adapter["path"]))=={"bytes":adapter["bytes"],"sha256":adapter["sha256"]})
    for seed in (4101,4202):check("Paired frozen feature initialization "+str(seed),by_adapter["shared",seed]["features_before"]==by_adapter["depth",seed]["features_before"])
    evaluation=read(worker/"public/evaluation.json");rows=evaluation["rows"]
    samples={r["id"]:r for r in data["eval"]};article_ids=list(samples)
    required={(a,s,e,i) for a,s in [("fixed32",None)]+[(a,s) for a in ("shared","depth") for s in (4101,4202)] for e in (5101,5202) for i in article_ids}
    check("Exactly160 unique final cases",evaluation["Status"]=="PASS" and len(rows)==160 and len({key(r) for r in rows})==160 and {key(r) for r in rows}==required)
    ledger=lines(worker/"public/retention.jsonl");by_ledger={key(r["identity"]):r for r in ledger}
    check("Exactly160 unique retention outcomes",len(ledger)==160 and set(by_ledger)==required)
    baseline_path=Path(spec["baseline_evaluation_path"]);check("Historical evaluation pin",pin(baseline_path)==spec["baseline_evaluation_pin"])
    baseline_root=baseline_path.parents[1];baseline_rows={key(r):r for r in read(baseline_path)["rows"] if r["arm"]=="fixed32"}
    records={};retention={"historical_bridge":0,"sentinel":0,"audited_then_discarded":0};retained={};h0={}
    for index,row in enumerate(rows):
        rowkey=key(row);entry=by_ledger[rowkey];row_path=confined(worker,row["row_input_file"]);receipt_path=confined(worker,row["row_audit_file"])
        receipt=read(receipt_path);actual=receipt["Actual"];columns=actual["columns"]
        check("Row binding "+str(index),read(row_path)==row and receipt["Status"]=="PASS" and receipt["Environment"]["development_only"] is False
              and receipt["Input"]["row_input"]==pin(row_path) and receipt["Input"]["identity"]==identity(row)
              and receipt["Input"]["spec_sha256"]==pin(RUN/"spec.json")["sha256"]
              and entry["identity"]==identity(row) and entry["audit_sha256"]==pin(receipt_path)["sha256"])
        check("Row full tensor audit identity "+str(index),row["shape"]==[64,32768] and row["dtype"]=="float32-le"
              and actual["raw"]=={"bytes":RAW_BYTES,"sha256":row["logits_sha256"]} and actual["finite_components"]==64*32768)
        check("Row frozen article index "+str(index),type(row["article_index"]) is int and 0<=row["article_index"]<16
              and data["eval"][row["article_index"]]["id"]==row["article_id"])
        targets=samples[row["article_id"]]["tokens"][65:129]
        check("Row exact targets "+str(index),len(targets)==64 and sha(struct.pack("<64q",*targets))==row["targets_sha256"])
        names={"nll","predictions","gold","max","shifted_logsumexp","logsumexp","top1","top2","top2_indices","margin"}
        check("Row64 finite columns "+str(index),set(columns)==names and all(isinstance(v,list) and len(v)==64 for v in columns.values())
              and all(type(x) is int and 0<=x<32768 for n in ("predictions","top2_indices") for x in columns[n])
              and all(type(x) in (int,float) and math.isfinite(x) for n in names-{"predictions","top2_indices"} for x in columns[n]))
        nll=[(columns["max"][i]-columns["gold"][i])+columns["shifted_logsumexp"][i] for i in range(64)]
        check("Row independently reconstructed64NLL "+str(index),all(close(nll[i],columns["nll"][i])
              and close(columns["logsumexp"][i],columns["max"][i]+columns["shifted_logsumexp"][i])
              and columns["top1"][i]==columns["max"][i] and columns["predictions"][i]!=columns["top2_indices"][i]
              and columns["margin"][i]>=0 and columns["margin"][i]==columns["top1"][i]-columns["top2"][i] for i in range(64)))
        metrics={"nll_mean":math.fsum(nll)/64,"nll_sum":math.fsum(nll),"correct":sum(p==t for p,t in zip(columns["predictions"],targets)),"target_count":64}
        check("Row root-worker-auditor agreement "+str(index),all(close(metrics[k],row[k]) and close(metrics[k],actual["metrics"][k]) for k in ("nll_mean","nll_sum"))
              and metrics["correct"]==row["correct"]==actual["metrics"]["correct"] and row["target_count"]==64
              and row["worker_per_token"]["predictions"]==columns["predictions"] and len(row["worker_per_token"]["nll"])==64
              and all(close(a,b) for a,b in zip(nll,row["worker_per_token"]["nll"])))
        check("Row8 chunk identities "+str(index),len(actual["chunks"])==8 and all(c["index"]==i and c["offset"]==i*1048576 and c["bytes"]==1048576
              and re.fullmatch("[0-9a-f]{64}",c["sha256"]) is not None and all(math.isfinite(c[k]) for k in ("sum64","sum_squares64","min64","max64")) for i,c in enumerate(actual["chunks"])))
        kind="historical_bridge" if row["arm"]=="fixed32" else "sentinel" if row["article_index"]==0 and row["eval_seed"]==5101 else "audited_then_discarded"
        retention[kind]+=1;raw=Path(row["raw_path"])
        check("Row declared retention and confinement "+str(index),row["retention"]==entry["action"]==kind and raw.is_absolute()
              and raw.resolve().parent==(worker/"private").resolve() and entry["raw_path"]==str(raw)
              and entry["raw_sha256"]==row["logits_sha256"] and entry["raw_after_audit"]==actual["raw"])
        retained_path=None
        if kind=="historical_bridge":
            old=baseline_rows[rowkey];reference=actual["baseline_reference"];retained_path=confined(baseline_root,old["logits_file"])
            check("Row original baseline bridge "+str(index),identity(old)==identity(row) and old["logits_sha256"]==row["logits_sha256"]
                  and old["targets_sha256"]==row["targets_sha256"] and old["h0_sha256"]==row["h0_sha256"]
                  and all(old["observer"][k]==row["observer"][k] for k in STABLE)
                  and reference["path"]==entry["retained_path"]==str(retained_path) and reference["pin"]==actual["raw"]
                  and reference["evaluation_pin"]==spec["baseline_evaluation_pin"] and entry["raw_exists_after"] is False and not raw.exists())
        elif kind=="sentinel":
            retained_path=confined(worker,row["logits_file"])
            check("Row trained sentinel retained "+str(index),retained_path==raw.resolve() and entry["retained_path"]==str(raw)
                  and entry["raw_exists_after"] is True and raw.is_file() and not raw.is_symlink())
        else:
            check("Row only audited temporary removed "+str(index),not raw.exists() and entry["raw_exists_after"] is False
                  and entry["retained_path"] is None and row["logits_file"] is None and actual["baseline_reference"] is None)
        if retained_path is not None:
            check("Row retained full raw SHA "+str(index),pin(retained_path)==actual["raw"]);retained[str(retained_path)]=actual["raw"]
        state={k:row["observer"][k] for k in STABLE};pair=row["article_id"],row["eval_seed"]
        check("Row paired actual initialization "+str(index),state.get("seed")==row["eval_seed"] and state["h0_sha256"]==row["h0_sha256"] and (pair not in h0 or state==h0[pair]))
        h0[pair]=state;records[rowkey]=metrics
    check("Exact36 retained and124 declared discards",retention=={"historical_bridge":32,"sentinel":4,"audited_then_discarded":124}
          and len(retained)==36 and retained==audit["Actual"]["retained_raw_manifest"] and not list((worker/"private").glob("pending_row_*.bin")))
    means={}
    for arm,seed in [("fixed32",None)]+[(a,s) for a in ("shared","depth") for s in (4101,4202)]:
        group=[records[arm,seed,e,i] for i in article_ids for e in (5101,5202)];name=arm if seed is None else f"{arm}_{seed}"
        means[name]={"mean_nll":math.fsum(r["nll_mean"] for r in group)/32,"correct":sum(r["correct"] for r in group),"scored_observations":2048}
        means[name]["accuracy"]=means[name]["correct"]/2048
        check("Root aggregate "+name,close(means[name]["mean_nll"],audit["Actual"]["means"][name]["mean_nll"])
              and all(means[name][k]==audit["Actual"]["means"][name][k] for k in ("correct","scored_observations","accuracy")))
    comparisons={};screens={};interpretations={}
    for a,b in (("shared","fixed32"),("depth","fixed32"),("depth","shared")):
        pairname=a+"_vs_"+b;per_seed={}
        for seed in (4101,4202):
            other=None if b=="fixed32" else seed;articles=[]
            for article in article_ids:
                left=[records[a,seed,e,article] for e in (5101,5202)];right=[records[b,other,e,article] for e in (5101,5202)]
                articles.append({"article_id":article,"delta_nll":math.fsum(l["nll_mean"]-r["nll_mean"] for l,r in zip(left,right))/2,
                                 "delta_correct":sum(l["correct"]-r["correct"] for l,r in zip(left,right))})
            dn=math.fsum(r["delta_nll"] for r in articles)/16;da=sum(r["delta_correct"] for r in articles)/2048
            name=pairname+"_"+str(seed);passed=dn<=-.01 and da>=-.01;per_seed[str(seed)]=label(dn,da)
            comparisons[name]={"delta_nll":dn,"delta_accuracy":da,"screen":passed,"interpretation":per_seed[str(seed)],"per_article":articles}
            old=audit["Actual"]["comparisons"][name]
            check("Root paired scientific comparison "+name,close(dn,old["delta_nll"]) and da==old["delta_accuracy"] and passed==old["screen"]
                  and per_seed[str(seed)]==old["interpretation"] and len(old["per_article"])==16
                  and all(x["article_id"]==y["article_id"] and close(x["delta_nll"],y["delta_nll"]) and x["delta_correct"]==y["delta_correct"] for x,y in zip(articles,old["per_article"])))
        screens[pairname]="PASS" if all(comparisons[pairname+"_"+str(s)]["screen"] for s in (4101,4202)) else "FAIL"
        combined=next(iter(set(per_seed.values()))) if len(set(per_seed.values()))==1 else "MIXED"
        interpretations[pairname]={"per_seed":per_seed,"combined":combined}
        check("Root two-seed screen "+pairname,screens[pairname]==audit["Actual"]["scientific_screens"][pairname]["Status"]
              and per_seed==audit["Actual"]["result_interpretations"][pairname]["per_seed"] and combined==audit["Actual"]["result_interpretations"][pairname]["combined"])
    reload_rows=read(RUN/"reload/public/reload.json")["rows"]
    check("Four exact sentinel reload results",len(reload_rows)==4 and {(r["arm"],r["train_seed"]) for r in reload_rows}==set(by_adapter))
    for r in reload_rows:
        reference=next(x for x in rows if x["arm"]==r["arm"] and x["train_seed"]==r["train_seed"] and x["article_index"]==0 and x["eval_seed"]==5101)
        check("Reload same logits and state "+str((r["arm"],r["train_seed"])),r["Status"]=="PASS" and r["logits_sha256"]==reference["logits_sha256"] and r["observer"]==reference["observer"])
    return {"target_tests":test_counts,"target_tests_total":sum(test_counts.values()),"main_counts":completion["Actual"],"reload_counts":reload["Actual"],
            "means":means,"comparisons":comparisons,"scientific_screens":screens,"result_interpretations":interpretations,"retention_counts":retention,
            "live_audited_rows":160,"retained_full_raw_hashes_verified":36,"root_full_logits_recomputed":0,"unavailable_full_candidate_rows":124,
            "main_seconds":completion["seconds"],"reload_seconds":reload["seconds"],"main_peak_rss_bytes":completion["peak_rss_bytes"],"reload_peak_rss_bytes":reload["peak_rss_bytes"],
            "evidence_limit":"Root reaggregated per-token live-audit records and verified36 raw hashes; it did not recompute full logits.124 full candidate matrices are unavailable retrospectively. Reused development data, not fresh generalization/statistical/production/equal-compute confirmation."}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--expected-freeze",required=True);args=parser.parse_args();freeze=args.expected_freeze
    if not re.fullmatch("[0-9a-f]{40}",freeze):parser.error("Full frozen commit SHA required")
    if OUT.exists():print("BLOCKED: existing acceptance-v2.json retained; no overwrite");return 2
    report={"Purpose":"Root read-only closure and independent metric aggregation for MoDA v2",
            "Environment":{"python":sys.version,"mode":"Standard library only; no model/Torch/NumPy"},
            "Input":{"freeze":freeze,"run":str(RUN)},"Expected":"Verify sealed outcome and full preservation; independently reaggregate complete PASS evidence without a model retry",
            "Actual":{},"Status":"NOT TESTED","checks":[]}
    def check(name,okay,actual=None):
        report["checks"].append({"Purpose":name,"Expected":True,"Actual":actual,"Status":"PASS" if okay else "FAIL"})
        if not okay:raise ValueError(name)
    try:
        publication=read(RUN/"publication.json");result_commit=publication["head"];head=git("rev-parse","HEAD")
        check("Clean published result and review descendant",publication["Status"]=="PASS" and result_commit==publication["remote"]
              and publication["branch"]==BRANCH and git("branch","--show-current")==BRANCH and not git("status","--porcelain")
              and git("ls-remote","origin","refs/heads/"+BRANCH).split()[0]==head
              and git("merge-base",freeze,result_commit)==freeze and git("merge-base",BASE,freeze)==BASE and git("merge-base",result_commit,head)==result_commit,
              {"result_commit":result_commit,"review_head":head})
        check("No active experiment workers",not workers())
        summary=read(RUN/"summary.json");custody=read(RUN/"custody.json");claim=read(RUN/"CLAIM.json")
        outcome=summary["Status"];check("Sealed outcome and freeze bound",outcome in ("PASS","BLOCKED","FAIL") and summary["Input"]["execution_freeze"]==freeze
              and claim["Input"]["freeze"]==freeze and summary["FORMAL_ACCEPTANCE_READY"] is False)
        manifest=read(ROOT/"SOURCE_MANIFEST.json")
        check("Frozen source manifest bytes",pin(ROOT/"SOURCE_MANIFEST.json")==byte_pin(git_bytes(freeze,PACKAGE+"/SOURCE_MANIFEST.json")))
        for name,expected in manifest.items():check("Source pin "+name,pin(confined(ROOT,name))==expected==byte_pin(git_bytes(freeze,PACKAGE+"/"+name)))
        inputs=read(ROOT/"INPUT_MANIFEST.json");verify_files(inputs,check,"All frozen input bytes")
        external=read(ROOT/"EXTERNAL_EVIDENCE_MANIFEST.json")
        check("External seal confined",all(Path(n).is_absolute() and Path(n).resolve().is_relative_to(RUN.resolve()) for n in external))
        verify_files(external,check,"All sealed external files")
        check("Complete external file set",set(external)=={str(p) for p in RUN.rglob("*") if p.is_file() and p.name!="publication.json"})
        export=read(ROOT/"PUBLIC_EXPORT.json");public=export["files"]
        check("Public export policy",len(public)==len(set(public)) and export["raw_logits_or_adapters_exported"] is False and export["input_tokens_or_source_text_exported"] is False)
        for name in public:check("Public byte copy "+name,pin(confined(ROOT/"evidence",name))==pin(confined(RUN,name)))
        check("Original protected inventory immutable",pin(PRIOR)==PRIOR_PIN)
        prior=read(PRIOR);check("Original25367 protected objects",len(prior)==25367)
        compressed,receipt_path=RUN/"protected_before.json.gz",RUN/"protected_before_receipt.json"
        complete_protection=compressed.is_file() and receipt_path.is_file()
        if complete_protection:
            codec_spec=importlib.util.spec_from_file_location("verified_storage_codec",ROOT/"storage_codec.py")
            codec=importlib.util.module_from_spec(codec_spec);codec_spec.loader.exec_module(codec)
            receipt=read(receipt_path);protected=codec.read_manifest(compressed,receipt)
            check("Full original protection scope retained",all(protected.get(n)==p for n,p in prior.items()) and len(protected)>=len(prior))
            check("Compressed2MiB bound intact",receipt["compressed"]["bytes"]<=2097152)
            protected_receipt=receipt
        else:
            check("Unreached manifest permitted only for stopped execution",outcome!="PASS")
            protected=prior;protected_receipt={"scope":"Original25367 only; new full manifest unavailable","prior_pin":PRIOR_PIN}
        count=verify_files(protected,check,"Protected objects exact-byte preservation")
        git_before=read(RUN/"git_before.json") if (RUN/"git_before.json").is_file() else {}
        for name,expected in git_before.items():
            if Path(name).resolve()==REPO.resolve():continue
            actual={"head":git_at(name,"rev-parse","HEAD"),"status":git_at(name,"status","--porcelain=v1","--untracked-files=all")}
            check("Old Git preserved "+name,actual==expected,{"head":actual["head"],"status_sha256":sha(actual["status"].encode())})
        if (RUN/"environment_before.json").is_file():check("Recorded dependencies unchanged",read(RUN/"environment_before.json")==read(RUN/"environment_after.json"))
        check("No recorded custody change",not any(custody.get(k) for k in ("changed_files","unreadable_files","changed_git","changed_environments","active_workers","cleanup_problems")))
        inventory=read(ROOT/"TEST_INVENTORY.json");commands=summary["Actual"]["commands"]
        expected_labels=[Path(n).stem for n in ("test_storage_codec.py","test_startup.py","test_moda_adapter.py","test_audit.py")]+["train","reload","audit"]
        check("No duplicate or out-of-order stage launch",[c["label"] for c in commands]==expected_labels[:len(commands)]
              and all(c["child_reaped"] and not c["cleanup_errors"] for c in commands)
              and summary["formal_launch_attempted"]==any(c["label"]=="train" for c in commands))
        result={"experiment_status":outcome,"result_commit":result_commit,"review_code_commit":head,"source_files_verified":len(manifest),
                "input_files_verified":len(inputs),"external_files_verified":len(external),"public_copies_verified":len(public),
                "protected_files_verified":count,"complete_new_protection_verified":complete_protection,"protected_receipt":protected_receipt,
                "operator_custody_original_status":custody["Status"],"commands_executed":[c["label"] for c in commands],
                "planned_tests":{n:len(x["test_ids"]) for n,x in inventory.items()},"current_disk_free_bytes":shutil.disk_usage(RUN).free}
        if outcome=="PASS":
            check("Full custody PASS",custody["Status"]=="PASS" and complete_protection)
            result.update(verify_success(summary,inventory,check))
        else:
            check("Stopped execution has recorded cause",summary.get("error") is not None or custody["Status"]!="PASS")
            result.update({"stopping_reason":summary.get("error"),"scientific_screens_recorded":summary["scientific_screens"],
                "partial_main_completion":summary["Actual"]["main_completion"],"partial_reload_completion":summary["Actual"]["reload_completion"],
                "evidence_progress":summary["Actual"]["evidence_progress"],"scope":"Closure/preservation only; unreached stages remain NOT TESTED. Original engineering outcome is unchanged."})
        check("No forbidden numerical import",not any(x.split(".")[0] in ("torch","numpy","parcae_lm","receval") for x in sys.modules))
        report["Actual"]=result;report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]="BLOCKED" if isinstance(exc,(OSError,MemoryError,subprocess.SubprocessError,KeyboardInterrupt)) else "FAIL"
        report["error"]={"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat();report["check_counts"]={s:sum(c["Status"]==s for c in report["checks"]) for s in ("PASS","FAIL")}
    with OUT.open("x",encoding="utf-8",newline="\n") as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write("\n")
    result=report["Actual"]
    print(json.dumps({"Status":report["Status"],"checks":report["check_counts"],"experiment_status":result.get("experiment_status"),
        "error":report.get("error"),"means":result.get("means"),"screens":result.get("scientific_screens"),
        "protected_files":result.get("protected_files_verified"),"output":str(OUT)},allow_nan=False))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
