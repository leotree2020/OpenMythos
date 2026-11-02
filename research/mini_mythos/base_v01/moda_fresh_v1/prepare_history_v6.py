"""One exhaustive history exclusion after the separate train-source gate PASS."""
from __future__ import annotations
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import data_prepare as D
import freeze_history_v6 as F
import source_feasibility_v6 as S

OUT=S.FRESH/"preparation-v6"
SPEC_DIR=S.FRESH/"specification-v6"
SPEC=SPEC_DIR/"DATA_SPEC.json"
GATE=S.OUT/"manifest.json"
BUDGET=64*1024**2
RESERVE=256*1024**2
SEAL=65536
MAX_LEDGER=64*1024**2
SOURCES=("prepare_history_v6.py","test_prepare_history_v6.py","data_prepare.py","freeze_history_v6.py","source_feasibility_v6.py")
canonical=D.canonical
pin=D.pin
require=D.require


def read(path,limit=65536):
    path=Path(path);require(path.is_file() and not path.is_symlink(),"Regular receipt required: "+str(path),"BLOCKED")
    raw=path.read_bytes();require(len(raw)<=limit,"Receipt expansion bound: "+str(path),"BLOCKED")
    return D.strict_json(raw.decode("utf-8"))


def packed(path,receipt,limit=MAX_LEDGER):
    path=Path(path);require(pin(path)==receipt["physical"],"Compressed evidence physical pin: "+str(path))
    with gzip.GzipFile(fileobj=io.BytesIO(path.read_bytes())) as stream:raw=stream.read(limit+1)
    require(len(raw)<=limit,"Compressed evidence expansion bound","BLOCKED")
    require({"bytes":len(raw),"sha256":D.sha(raw)}==receipt["canonical"],"Compressed evidence canonical pin")
    value=D.strict_json(raw.decode("utf-8"));require(canonical(value)==raw,"Canonical evidence encoding")
    return value


class Writer:
    def __init__(self,out):self.out=Path(out)
    def used(self):return sum(p.stat().st_size for p in self.out.rglob("*") if p.is_file())
    def write(self,name,raw):
        path=self.out/name;require(path.resolve().is_relative_to(self.out.resolve()),"Output confinement")
        require(not path.exists(),"Refuse existing evidence: "+name,"BLOCKED")
        require(self.used()+len(raw)<=BUDGET-SEAL,"64MiB preparation allocation exceeded","BLOCKED")
        require(shutil.disk_usage(self.out).free>=len(raw)+SEAL+RESERVE,"256MiB reserve unavailable","BLOCKED")
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as stream:stream.write(raw)
        result=pin(path);require(result=={"bytes":len(raw),"sha256":D.sha(raw)},"Evidence readback")
        return result
    def json(self,name,value):return self.write(name,canonical(value))
    def compressed(self,name,value):
        raw=canonical(value);compressed=gzip.compress(raw,mtime=0,compresslevel=9)
        require(gzip.decompress(compressed)==raw,"Lossless evidence gzip")
        return {"physical":self.write(name,compressed),"canonical":{"bytes":len(raw),"sha256":D.sha(raw)}}
    def seal(self,report):
        raw=canonical(report);require(len(raw)<=SEAL,"Final manifest reserve")
        require(self.used()+len(raw)<=BUDGET,"Final preparation allocation exceeded","BLOCKED")
        require(shutil.disk_usage(self.out).free>=len(raw)+RESERVE,"Final256MiB reserve unavailable","BLOCKED")
        with (self.out/"manifest.json").open("xb") as stream:stream.write(raw)


def source_gate(expected_sha):
    require(pin(GATE)["sha256"]==expected_sha,"Frozen source gate manifest SHA")
    gate=read(GATE);actual=gate["Actual"];inputs=gate["Input"]
    require(gate["Status"]=="PASS" and actual["eligibility_necessary_condition"]=="PASS","Source eligibility gate must PASS","BLOCKED")
    require(inputs["dataset"]==S.DATASET and inputs["revision"]==S.REVISION and inputs["split"]=="train" and inputs["url"]==S.URL and inputs["corpus"]==S.CORPUS_PIN,"Source gate train provenance")
    require(inputs["tokenizer_sha256"]==S.TOKENIZER_SHA,"Source gate original tokenizer")
    require(actual["source_rows"]==S.TOTAL_ROWS and actual["rows_per_label"]=={str(i):S.ROWS_PER_LABEL for i in range(4)},"Complete train source gate rows")
    require(all(actual[k]==S.TOTAL_ROWS for k in ("source_rows_observed","source_rows_completed","ledger_rows_retained")),"All train rows completed before history")
    require(all(actual["eligible_per_label"][str(i)]>=5 for i in range(4)),"Necessary train quota unavailable","BLOCKED")
    require(actual["source_attempts"]==1 and actual["model_calls"]==actual["optimizer_steps"]==actual["history_files_scanned"]==0,"Model-blind single source acquisition gate")
    require(all(actual[k]=="PASS" for k in ("old_fresh_after_status","input_after_status","corpus_after_status","checkout_after_status")) and not gate["forbidden_imports"],"Source gate custody/forbidden imports")
    require(actual["history_freeze"]["spec"]==pin(SPEC) and actual["history_freeze"]["receipt"]==pin(SPEC_DIR/"FREEZE_RECEIPT.json") and actual["history_freeze"]["inventory"]==pin(SPEC_DIR/"history_before.json.gz"),"Source gate bound this pre-acquisition history freeze")
    source=S.OUT/"corpus.parquet";acquisition=S.OUT/"acquisition.json";ledger=S.OUT/"candidates.json.gz"
    require(pin(source)==S.CORPUS_PIN==gate["artifacts"]["corpus.parquet"],"Retained train corpus exact bytes")
    require(pin(acquisition)==gate["artifacts"]["acquisition.json"],"Original acquisition receipt pin")
    acquired=read(acquisition)
    require(acquired["Status"]=="PASS" and acquired["http_status"]==200 and acquired["url"]==S.URL and acquired["actual_response"]==acquired["pin"]==S.CORPUS_PIN and acquired["response_file"]=="corpus.parquet" and acquired["request_attempts"]==1,"Original single successful train acquisition")
    records=packed(ledger,gate["artifacts"]["candidates.json.gz"])
    require(isinstance(records,list) and len(records)==S.TOTAL_ROWS and [r["row"] for r in records]==list(range(S.TOTAL_ROWS)),"Complete ordered source eligibility ledger")
    before={str(p):pin(p) for p in (GATE,source,acquisition,ledger,S.TOKENIZER)}
    require(before[str(S.TOKENIZER)]["sha256"]==S.TOKENIZER_SHA,"Original tokenizer exact bytes")
    reference={"schema":"mythos-train-source-reference-v6","mode":"LOCAL_PINNED_REUSE","Status":"PASS",
        "source_file":str(source),"source_pin":S.CORPUS_PIN,"original_acquisition_file":str(acquisition),"original_acquisition_pin":pin(acquisition),
        "source_gate_file":str(GATE),"source_gate_pin":pin(GATE),"eligibility_file":str(ledger),"eligibility_receipt":gate["artifacts"]["candidates.json.gz"],
        "network_requests":0,"copied_corpus_bytes":0}
    return gate,records,reference,before


def classify_history(mapping,nontext,formats):
    require(not set(nontext)&set(formats),"Conflicting historical classification policies")
    require(set(nontext)<=set(mapping) and set(formats)<=set(mapping),"Original classification scope retained")
    entries=[]
    for path,expected in sorted(mapping.items()):
        require(Path(path).is_absolute() and set(expected)=={"bytes","sha256"} and type(expected["bytes"]) is int and expected["bytes"]>=0 and re.fullmatch("[0-9a-f]{64}",expected["sha256"]),"Frozen historical pin schema")
        require(Path(path).is_file() and not any(p.is_symlink() for p in (Path(path),*Path(path).parents)),"Historical physical regular path","BLOCKED")
        require(pin(path)==expected,"Historical bytes changed: "+path)
        entry={"path":path,**expected,"kind":D.classify_name(path)}
        policy=nontext.get(path) or formats.get(path)
        if policy is not None:
            require({k:policy[k] for k in ("bytes","sha256")}==expected and bool(policy.get("reason")),"Historical override byte pin/reason")
            entry.update(kind="nontext" if path in nontext else policy["kind"],reason=policy["reason"])
        require(entry["kind"] in D.TEXT_KINDS or entry["kind"]=="nontext","Unknown historical input format: "+path,"BLOCKED")
        entries.append(entry)
    return entries


def snapshot_policies(mapping,origins,policy):
    """Exact physical-byte aliases only; no binary-extension shortcut."""
    nontext=dict(policy["nontext_entries"]);formats=dict(policy["format_entries"]);members=dict(policy["member_entries"]);notes=[]
    registered={}
    for kind,table in (("nontext",nontext),("format",formats)):
        for path,value in table.items():
            key=value["bytes"],value["sha256"],Path(path).suffix.casefold()
            registered.setdefault(key,[]).append((path,"nontext" if kind=="nontext" else value["kind"],value))
    physical={}
    for path,value in mapping.items():
        if path not in origins:physical.setdefault((value["bytes"],value["sha256"],Path(path).suffix.casefold()),[]).append(path)
    for copied,origin in sorted(origins.items()):
        key=mapping[copied]["bytes"],mapping[copied]["sha256"],Path(copied).suffix.casefold();matches=registered.get(key,[])
        note={"path":copied,"pin":mapping[copied],"registered_origins":[],"member_aliases":[]}
        if matches:
            kinds={kind for _,kind,_ in matches};require(len(kinds)==1,"Conflicting identical snapshot classifications","BLOCKED")
            kind=next(iter(kinds));source_paths=sorted(p for p,_,_ in matches)
            item={**mapping[copied],"kind":kind,"reason":"Exact-byte and suffix-matched snapshot copy of registered paths: "+"; ".join(source_paths)}
            (nontext if kind=="nontext" else formats)[copied]=item
            note.update(kind=kind,registered_origins=[{"path":p,"reason":value["reason"]} for p,_,value in matches])
        for original in physical.get(key,[]):
            prefixes=[(original,copied)]
            if original.endswith((".gz",".xz")):prefixes.append((original[:-3],copied[:-3]))
            for prefix,new_prefix in prefixes:
                for name,value in policy["member_entries"].items():
                    if name==prefix or name.startswith(prefix+"!"):
                        alias=new_prefix+name[len(prefix):]
                        require(alias not in members or members[alias]==value,"Conflicting snapshot archive member classifications","BLOCKED")
                        members[alias]=value;note["member_aliases"].append({"original":name,"alias":alias,"physical_original":original})
        if note["registered_origins"] or note["member_aliases"]:notes.append(note)
    return nontext,formats,members,notes


def scope_paths(spec,old,prior,mapping):
    paths,original=F.enumerate_paths(old,prior)
    old_v4=F.historical_git_json("continuation_v4_evidence/EXTERNAL_MANIFEST.json")
    old_before=S.FRESH/"preparation-v4/old_fresh_before.json"
    require(pin(old_before)==old_v4[str(old_before)],"Sealed old-fresh before map unchanged")
    sealed={**read(old_before,MAX_LEDGER),**old_v4}
    for entry in F.historical_git_json("CONTINUATION_V5_EXPORT_MANIFEST.json").values():sealed[entry["source"]]={k:entry[k] for k in ("bytes","sha256")}
    require(all(mapping.get(p)==value for p,value in sealed.items()),"Every previously sealed external/fresh byte retained")
    origins=spec["repo_snapshot_origins"];require(isinstance(origins,dict) and len(origins)==spec["repo_snapshot_files"],"Exact repository snapshot count")
    root=SPEC_DIR/"repo_history_snapshot"
    for copied,origin in origins.items():
        copy=Path(copied);source=Path(origin["original_path"])
        require(copy.is_relative_to(root) and source.is_relative_to(S.REPO) and copy.relative_to(root)==source.relative_to(S.REPO),"Snapshot origin relative-path binding")
        require(mapping.get(copied)==origin["pin"],"Snapshot pin retained")
    observed_snapshots={str(p) for p in root.rglob("*") if p.is_file()}
    require(observed_snapshots==set(origins),"No missing/additional repository snapshot files","BLOCKED")
    expected=set(paths)|set(sealed)|set(origins)
    require(set(mapping)==expected and len(original)==32244 and original<=expected,"Full original+oldfresh+sealed+snapshot scope")
    require(spec["added_old_fresh_files"]==len(paths)-len(original) and spec["added_external_sealed_files"]==len(set(sealed)-set(paths)),"Expanded history component counts")
    require(spec["history_file_count"]==32244+spec["added_old_fresh_files"]+spec["added_external_sealed_files"]+spec["repo_snapshot_files"],"Exact expanded component count sum")
    require(sum(origin["pin"]["bytes"] for origin in origins.values())==spec["repo_snapshot_bytes"],"Snapshot byte count")
    return expected,original


def history_spec(expected_sha):
    require(pin(SPEC)["sha256"]==expected_sha,"Frozen expanded history spec SHA")
    spec=read(SPEC,8*1024**2);freeze=read(SPEC_DIR/"FREEZE_RECEIPT.json")
    require(spec["schema"]=="mythos-history-v6-before-source" and freeze["Status"]=="PASS","Expanded history freeze PASS required","BLOCKED")
    require(freeze["Actual"]["spec_pin"]==pin(SPEC),"History freeze binds actual spec")
    require(spec["source_acquisitions"]==spec["model_calls"]==0 and spec["original_history_count"]==32244,"History frozen before new source")
    require(set(spec["excluded_new_protocol_roots"])=={str(p) for p in F.EXCLUDED},"Only explicit new protocol roots excluded")
    require(Path(spec["inventory_path"])==SPEC_DIR/"history_before.json.gz","Exact expanded inventory path")
    mapping=packed(spec["inventory_path"],{"physical":spec["inventory_pin"],"canonical":spec["inventory_canonical_pin"]})
    require(isinstance(mapping,dict) and len(mapping)==spec["history_file_count"],"Complete expanded history map")
    require(Path(spec["original_spec"])==F.OLD and spec["original_spec_pin"]["sha256"]==F.OLD_SHA and pin(F.OLD)==spec["original_spec_pin"],"Original history specification preserved")
    old=read(F.OLD);prior=D.policy_mapping(old,"extra_history_inventory")
    _,original=scope_paths(spec,old,prior,mapping)
    require(spec["added_old_fresh_files"]>0,"Expanded old-fresh scope required")
    test_corpus=S.FRESH/"preparation-v2/data/corpus.parquet"
    require(spec["prior_test_corpus"]==str(test_corpus) and str(test_corpus) in set(mapping)-original and mapping[str(test_corpus)]==D.CORPUS_PIN,"All previously read AGNews test bytes added to history")
    before={str(p):pin(p) for p in (SPEC,SPEC_DIR/"FREEZE_RECEIPT.json",Path(spec["inventory_path"]),F.OLD)}
    policy={}
    for key in ("nontext_entries","format_entries","member_entries"):
        reused=spec["policy_reuse"][key]
        require(reused=={"path":old[key+"_path"],"pin":old[key+"_pin"]},"Original full classification policy reused")
        policy[key]=D.policy_mapping(old,key);before[reused["path"]]=reused["pin"]
    nontext,formats,members,aliases=snapshot_policies(mapping,spec["repo_snapshot_origins"],policy)
    entries=classify_history(mapping,nontext,formats)
    before.update(mapping)
    return spec,entries,members,before,old,prior,aliases


def rebuild_candidates(rows,tokenize,gate_ledger,ledger,total_rows=S.TOTAL_ROWS,rows_per_label=S.ROWS_PER_LABEL):
    candidates=[];labels=Counter();eligible=Counter();decisions=Counter()
    for i,row in enumerate(rows):
        require(i<total_rows and i<len(gate_ledger),"Train row overflow")
        require(isinstance(row,dict) and set(row)>={"text","label"},"Train text/label schema")
        text,label=row["text"],row["label"]
        require(isinstance(text,str) and type(label) is int and label in range(4),"Train source types")
        identity={"corpus_sha256":S.CORPUS_PIN["sha256"],"row":i,"text_sha256":D.sha(text.encode("utf-8"))}
        record={"id":D.sha(canonical(identity)),"row":i,"label":label,"text_sha256":identity["text_sha256"],"decision":"NOT_TESTED","full_token_count":None,"tokenization_started":False,"tokenization_performed":False}
        ledger.append(record);labels[label]+=1;reason=D.prose_reason(text)
        if reason:record["decision"]="EXCLUDE_"+reason
        else:
            record["tokenization_started"]=True
            ids=tokenize(text);require(D.valid_tokens(ids),"Original tokenizer ID contract")
            record.update(full_token_count=len(ids),tokenization_performed=True,decision="EXCLUDE_SHORT" if len(ids)<129 else "ELIGIBLE_PENDING_HISTORY")
            if len(ids)>=129:
                word_list=D.words(text)
                fingerprint={"normalized":D.normalized(text),"ids":ids,"token32":D.grams(ids,32),"word12":D.grams(word_list,12),"word5":D.grams(word_list,5)}
                candidates.append({**record,"text":text,"fingerprint":fingerprint});eligible[label]+=1
        require(record==gate_ledger[i],"Rebuilt eligibility differs from frozen source gate at row "+str(i))
        decisions[record["decision"]]+=1
    require(len(ledger)==len(gate_ledger)==total_rows and labels==Counter({i:rows_per_label for i in range(4)}),"Complete train row/label coverage")
    require(len({r["id"] for r in ledger})==total_rows,"Unique train identities")
    require(all(eligible[i]>=5 for i in range(4)),"Insufficient unchanged pre-history quota","BLOCKED")
    return candidates,{"source_rows":len(ledger),"rows_per_label":{str(i):labels[i] for i in range(4)},"eligible_per_label":{str(i):eligible[i] for i in range(4)},"prose_length_eligible":len(candidates),"decisions":dict(sorted(decisions.items()))}


def payload(selected):
    result=D.selected_payload(selected)
    result["provenance"]={"dataset":S.DATASET,"revision":S.REVISION,"split":"train","corpus":dict(S.CORPUS_PIN),
        "role":"Project-new news-domain evaluation from the source's train split, with zero model training and complete registered history exclusion; base pretraining overlap unknown",
        "license":"unknown; source research/noncommercial description retained; no raw text exported to Git"}
    return result


def checkout(expected_head):
    require(S.git(S.REPO,"rev-parse","HEAD")==expected_head and not S.git(S.REPO,"status","--porcelain"),"Frozen clean implementation checkout","BLOCKED")
    require(S.git(S.REPO,"branch","--show-current")==S.BRANCH and S.git(S.REPO,"merge-base",S.BASE,expected_head)==S.BASE,"Authorized continuation ancestry/branch","BLOCKED")
    require(S.git(S.UPSTREAM,"rev-parse","HEAD")==S.UPSTREAM_HEAD and not S.git(S.UPSTREAM,"status","--porcelain"),"Read-only upstream remains clean")
    for name in SOURCES:
        frozen=subprocess.check_output(["git","-C",str(S.REPO),"show",expected_head+":research/mini_mythos/base_v01/moda_fresh_v1/"+name])
        require(pin(HERE/name)["sha256"]==D.sha(frozen),"Frozen source bytes: "+name)


def acquisition_ancestry(gate,expected_head):
    freeze=read(SPEC_DIR/"FREEZE_RECEIPT.json");source_head=gate["Input"]["freeze"]
    require(re.fullmatch("[0-9a-f]{40}",source_head) and freeze["Input"]["source_freeze"]==source_head,"History and source acquisition freeze A agree")
    require(S.git(S.REPO,"merge-base",source_head,expected_head)==source_head,"Source acquisition freeze A is ancestor of preparation freeze B")
    pins={}
    for name in S.SOURCES:
        original=subprocess.check_output(["git","-C",str(S.REPO),"show",source_head+":research/mini_mythos/base_v01/moda_fresh_v1/"+name])
        require(pin(HERE/name)["sha256"]==D.sha(original),"Original acquisition source unchanged since A: "+name)
        pins[str(HERE/name)]=pin(HERE/name)
    return source_head,pins


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--expected-head",required=True);parser.add_argument("--expected-spec-sha",required=True);parser.add_argument("--expected-gate-sha",required=True);args=parser.parse_args()
    require(re.fullmatch("[0-9a-f]{40}",args.expected_head) and all(re.fullmatch("[0-9a-f]{64}",v) for v in (args.expected_spec_sha,args.expected_gate_sha)),"Full frozen source/spec/gate identities","BLOCKED")
    require(not OUT.exists(),"Single new preparation-v6 only; no retry","BLOCKED")
    require(os.name=="posix" and Path("/workspaces").is_dir(),"Designated target required","BLOCKED")
    require(S.FRESH.is_dir() and not any(p.is_symlink() for p in (S.FRESH,*S.FRESH.parents)),"Regular evidence parent required","BLOCKED")
    OUT.mkdir(parents=True,exist_ok=False);writer=Writer(OUT)
    report={"Purpose":"Exhaustive project-history and new-new exclusion of all eligible train-source candidates before model evaluation","Environment":{"python":sys.version,"executable":sys.executable,"codespace":os.environ.get("CODESPACE_NAME")},"Input":{"implementation":args.expected_head,"spec_sha256":args.expected_spec_sha,"source_gate_sha256":args.expected_gate_sha,"source":S.URL,"corpus":S.CORPUS_PIN},"Expected":{"source_rows":120000,"selected":20,"per_class":5,"tokens":129,"new_source_acquisitions":0,"model_calls":0},"Actual":{"new_source_acquisitions":0,"copied_corpus_bytes":0,"model_calls":0,"optimizer_steps":0},"Status":"NOT TESTED"}
    before={};ledger=[];history=[];artifacts={};index=None;old=None;prior=None;spec=None;checked=False
    def interrupted(signum,frame):
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        report["interruption"]={"signal":signum};raise D.Stop("BLOCKED","Preparation interrupted; no retry")
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        require(os.environ.get("CODESPACE_NAME")==S.SPACE and platform.python_version()=="3.12.3" and sys.executable==S.PYTHON and sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize and HERE==S.PACKAGE,"Designated isolated data runtime","BLOCKED")
        checkout(args.expected_head);checked=True
        require(shutil.disk_usage(OUT).free>=BUDGET+RESERVE,"64MiB preparation allocation plus256MiB reserve unavailable","BLOCKED")
        gate,gate_ledger,reference,source_before=source_gate(args.expected_gate_sha);before.update(source_before)
        source_head,acquisition_pins=acquisition_ancestry(gate,args.expected_head);before.update(acquisition_pins);report["Input"]["acquisition_freeze"]=source_head
        artifacts["source_reference.json"]=writer.json("source_reference.json",reference)
        spec,entries,members,history_before,old,prior,aliases=history_spec(args.expected_spec_sha);before.update(history_before)
        artifacts["snapshot_policy_aliases.json.gz"]=writer.compressed("snapshot_policy_aliases.json.gz",aliases)
        before.update({str(HERE/name):pin(HERE/name) for name in SOURCES})
        artifacts["protected_before.json.gz"]=writer.compressed("protected_before.json.gz",before)
        versions={name:importlib.metadata.version(name) for name in S.VERSIONS};require(versions==S.VERSIONS,"Frozen data dependencies","BLOCKED");report["Environment"]["packages"]=versions
        runtime={"TOKENIZERS_PARALLELISM":"false","RAYON_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","CUDA_VISIBLE_DEVICES":""}
        report["Environment"]["env_before"]={k:os.environ.get(k) for k in runtime};os.environ.update(runtime);report["Environment"]["env_effective"]=runtime
        import pyarrow as pa
        import pyarrow.parquet as pq
        import numpy as np
        from tokenizers import Tokenizer
        tokenizer=Tokenizer.from_file(str(S.TOKENIZER));tokenize=lambda text:tokenizer.encode(text,add_special_tokens=False).ids
        with pq.ParquetFile(reference["source_file"]) as parquet:
            require(parquet.metadata.num_rows==S.TOTAL_ROWS,"Frozen train parquet row count")
            rows=(row for batch in parquet.iter_batches(batch_size=1024,columns=["text","label"]) for row in batch.to_pylist())
            candidates,actual=rebuild_candidates(rows,tokenize,gate_ledger,ledger)
        report["Actual"].update(actual)
        require(all(actual[k]==gate["Actual"][k] for k in ("source_rows","rows_per_label","eligible_per_label","prose_length_eligible","decisions")),"All source-gate aggregate decisions reconciled")
        def columnar(raw,kind):
            if kind=="npy":
                array=np.load(io.BytesIO(raw),allow_pickle=False);require(array.dtype.kind in "biufUS","Historical NPY dtype","BLOCKED")
                return [{"array":array.tolist(),"dtype":str(array.dtype)}]
            buffer=pa.BufferReader(raw)
            if kind=="parquet":return pq.read_table(buffer).to_pylist()
            try:return pa.ipc.open_file(buffer).read_all().to_pylist()
            except pa.ArrowInvalid:buffer.seek(0);return pa.ipc.open_stream(buffer).read_all().to_pylist()
        index=D.ExclusionIndex(candidates);D.scan_history(entries,index,tokenize,columnar,ledger=history,member_policy=members)
        require(len(history)==len(entries) and all(r["Status"] in ("PASS","PASS_IDENTICAL_PAYLOAD","EXCLUDED_REGISTERED_NONTEXT") for r in history),"Complete successful history scope")
        chosen=D.select(candidates,ledger,index);inputs=payload(chosen)
        artifacts["inputs.json"]=writer.json("inputs.json",inputs)
        public=[{k:v for k,v in r.items() if k not in ("text","tokens")} for r in inputs["eval"]]
        artifacts["public/selection.json"]=writer.json("public/selection.json",{"samples":public,"input_pin":artifacts["inputs.json"]})
        report["Actual"].update(selected=len(chosen),per_class={str(i):sum(r["label"]==i for r in chosen) for i in range(4)},input_pin=artifacts["inputs.json"],source_gate_bridge="PASS",history_exclusion_complete=True,new_new_exclusion_complete=True)
        report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]=getattr(exc,"status","BLOCKED" if isinstance(exc,(OSError,MemoryError,subprocess.SubprocessError,KeyboardInterrupt,importlib.metadata.PackageNotFoundError)) else "FAIL")
        report["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        report["Actual"].update(candidate_rows_retained=len(ledger),historical_files_completed=len(history))
        if spec is not None:report["Actual"]["historical_files"]=spec["history_file_count"]
        if index is not None:report["Actual"].update(historical_strings=index.string_count,historical_token_arrays=index.token_array_count,historical_text_fingerprints=index.text_fingerprints,historical_text_cache_hits=index.text_cache_hits,historical_format_notes=index.format_notes,historical_python_recovery=index.python_recovery,historical_jsonl_recovery=index.jsonl_recovery,excluded_by_history=len(index.matches))
        for name,value in (("candidates.json.gz",ledger),("history_ledger.json.gz",history)):
            try:artifacts[name]=writer.compressed(name,value)
            except BaseException as exc:report.setdefault("sealing_errors",[]).append({"path":name,"error":repr(exc)});report["Status"]="BLOCKED" if report["Status"]!="FAIL" else "FAIL"
        try:
            if report.get("interruption"):report["source_after_status"]="NOT TESTED: interrupted; parent must verify custody"
            else:
                for path,expected in before.items():require(pin(path)==expected,"Protected input changed: "+path)
                if old is not None:
                    scope_paths(spec,old,prior,{r["path"]:{k:r[k] for k in ("bytes","sha256")} for r in entries})
                if checked:checkout(args.expected_head)
                report["source_after_status"]="PASS" if before else "NOT TESTED"
        except BaseException as exc:report["Status"]="FAIL";report["custody_error"]={"type":type(exc).__name__,"message":str(exc)}
        report["forbidden_imports"]=sorted(n for n in sys.modules if n.split(".")[0] in D.FORBIDDEN)
        if report["forbidden_imports"]:report["Status"]="FAIL"
        report["artifacts"]=artifacts;report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        report["Actual"]["evidence_bytes_before_manifest"]=writer.used();writer.seal(report)
    print(json.dumps({"Status":report["Status"],"Actual":report["Actual"],"error":report.get("error")},allow_nan=False),flush=True)
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
