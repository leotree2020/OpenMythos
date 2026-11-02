"""Read-only independent source/selection audit; never loads a language model.

Independent selection and metric logic. Historical witness extraction reuses the
frozen preparer's container parser, explicitly; this is not a second exhaustive
historical tokenizer scan. Every historical byte pin and classification is checked.
"""
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
import struct
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import data_prepare as parser_contract

SPACE="bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON="/workspaces/mythos-depth-data-cpu312/bin/python"
CORPUS={"bytes":1234829,"sha256":"71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb"}
TOKENIZER_SHA="e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
REVISION="eb185aade064a813bc0b7f42de02595523103ca4"
URL="https://huggingface.co/datasets/fancyzhx/ag_news/resolve/"+REVISION+"/data/test-00000-of-00001.parquet"
LIMIT=32*1024**2
FORBIDDEN={"torch","parcae_lm","receval","transformers"}
KINDS={"json","jsonl","text","python","csv","tsv","xml","parquet","arrow","npy","zip","tar","base64","gzip","xz"}


class Stop(Exception):
    def __init__(self,message,status="FAIL"):super().__init__(message);self.status=status
def require(okay,message,status="FAIL"):
    if not okay:raise Stop(message,status)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
def pin(path):
    h=hashlib.sha256();n=0
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block);n+=len(block)
    return {"bytes":n,"sha256":h.hexdigest()}
def loads(raw):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,"Repeated audit JSON key");out[key]=value
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(Stop("Nonfinite audit JSON constant")))
def read(path):
    path=Path(path)
    if path.suffix==".gz":
        with gzip.open(path,"rb") as stream:raw=stream.read(LIMIT+1)
        require(len(raw)<=LIMIT,"Expanded artifact/policy bound")
    else:raw=path.read_bytes()
    return loads(raw)
def bytepin(value):return {k:value[k] for k in ("bytes","sha256")}
def ids_pin(ids):return sha(struct.pack("<"+str(len(ids))+"q",*ids))
def valid_ids(ids):return type(ids)is list and all(type(v)is int and 0<=v<32768 for v in ids)


def policies(spec):
    result={}
    for key,default in (("nontext_entries",{}),("format_entries",{}),("member_entries",{}),("extra_history_files",[]),("extra_history_inventory",{})):
        if key+"_path" in spec:
            path=Path(spec[key+"_path"])
            require(key not in spec and path.is_absolute() and path.is_file() and not path.is_symlink(),"External-only frozen policy "+key)
            require(pin(path)==spec[key+"_pin"],"Policy pin "+key);result[key]=read(path)
        else:result[key]=spec.get(key,default)
        require(type(result[key])is type(default),"Policy type "+key)
    require(not set(result["nontext_entries"])&set(result["format_entries"]),"Conflicting classification policies")
    return result


def collect_paths(spec,policy):
    paths=set();excluded={}
    for e in spec.get("excluded_roots",[]):
        require(set(e)=={"path","reason"} and Path(e["path"]).is_absolute() and bool(e["reason"]),"Explicit excluded-root schema")
        excluded[Path(e["path"])]=e["reason"]
    for rootname in spec["history_roots"]:
        root=Path(rootname);require(root.is_absolute() and root.is_dir() and not root.is_symlink(),"Historical root available","BLOCKED")
        for current,dirs,files in os.walk(root,followlinks=False):
            current=Path(current);keep=[]
            for name in dirs:
                path=current/name
                if name in (".git","__pycache__") or path in excluded:continue
                require(not path.is_symlink(),"Historical directory symlink");keep.append(name)
            dirs[:]=keep
            for name in files:
                path=current/name;require(not path.is_symlink(),"Historical file symlink");paths.add(str(path))
    paths.update(policy["extra_history_files"]);paths.update(policy["extra_history_inventory"])
    require(all(Path(p).is_absolute() for p in paths),"Absolute history paths")
    require(len(paths)==spec["expected_history_file_count"],"Full historical count")
    require(dict(Counter(Path(p).suffix.casefold() for p in paths))==spec["expected_history_suffixes"],"Full historical suffix inventory")
    return paths


def suffix_kind(path):
    groups={"json":["json"],"jsonl":["jsonl","ndjson"],"text":["txt","md","rst","log","stdout","stderr","out","err","lock","sha256","yaml","yml","toml"],"python":["py"],"csv":["csv"],"tsv":["tsv"],"xml":["xml"],"parquet":["parquet"],"arrow":["arrow"],"npy":["npy"],"zip":["zip"],"tar":["tar"],"gzip":["gz"],"xz":["xz"],"base64":["b64","base64"]}
    ext=Path(path).suffix.casefold().lstrip(".")
    return next((kind for kind,extensions in groups.items() if ext in extensions),None)


def audit_history(spec,policy,ledger,rehash=True):
    require(type(ledger)is list and len({r["path"] for r in ledger})==len(ledger),"Unique physical history ledger")
    paths=collect_paths(spec,policy);require(paths=={r["path"] for r in ledger},"Exact ledger and independently enumerated history union")
    require([r["path"] for r in ledger]==sorted(paths),"Frozen lexicographic history order")
    previous={};seen={};counts=Counter();notes={"duplicate_keys":0,"nonfinite_numeric_constants":0}
    overrides=policy["nontext_entries"];formats=policy["format_entries"]
    require(set(overrides)|set(formats)<=paths,"Every classified physical path retained")
    old=policy["extra_history_inventory"]
    for r in ledger:
        p=r["path"];expected=bytepin(r);path=Path(p)
        require(path.is_file() and not path.is_symlink(),"History byte source available "+p,"BLOCKED")
        if rehash:require(pin(path)==expected,"Historical byte custody "+p)
        if p in old:require(old[p]==expected,"Prior protected inventory pins unchanged "+p)
        kind=suffix_kind(p)
        for mapping,nontext in ((overrides,True),(formats,False)):
            if p in mapping:
                v=mapping[p];require(bytepin(v)==expected and bool(v.get("reason")),"Classification pin/reason "+p)
                kind="nontext" if nontext else v["kind"];require(r.get("reason")==v["reason"],"Classification reason retained")
        require(r["kind"]==kind and kind in KINDS|{"nontext"},"Frozen physical format classification "+p)
        require(type(r["strings"])is int and type(r["token_arrays"])is int and min(r["strings"],r["token_arrays"])>=0,"Historical leaf counters")
        key=expected["sha256"],expected["bytes"],kind
        if kind=="nontext":require(r["Status"]=="EXCLUDED_REGISTERED_NONTEXT" and r["strings"]==r["token_arrays"]==0,"Registered nontext receipt")
        elif key in seen:
            require(r["Status"]=="PASS_IDENTICAL_PAYLOAD" and r.get("identical_to")==seen[key] and r["strings"]==r["token_arrays"]==0,"Exact duplicate-payload parse reuse")
            require(previous[seen[key]]["Status"]=="PASS","Reuse points to actual complete parse")
        else:require(r["Status"]=="PASS" and "identical_to" not in r,"Full first-payload parse completion");seen[key]=p
        for m in r.get("classified_nontext_members",[]):
            candidates=[v for name,v in policy["member_entries"].items() if name.startswith(p+"!") and v.get("kind")=="nontext" and bytepin(v)==bytepin(m) and v.get("reason")==m.get("reason")]
            require(bool(candidates),"Container nontext member has frozen policy")
        for n in r.get("format_notes",[]):
            for key in notes:require(type(n[key])is int and n[key]>=0,"Format-note counters");notes[key]+=n[key]
        counts[r["Status"]]+=1;previous[p]=r
    return {"files":len(paths),"status_counts":dict(counts),"strings":sum(r["strings"] for r in ledger),"token_arrays":sum(r["token_arrays"] for r in ledger),"format_notes":notes,"old_inventory_paths":len(old)}


def ngrams(values,width):return {tuple(values[i:i+width]) for i in range(max(0,len(values)-width+1))}
def fingerprint(text,ids):
    terms=re.findall(r"[a-z0-9]+",text.casefold())
    return {"normalized":" ".join(text.casefold().split()),"t32":ngrams(ids,32),"w12":ngrams(terms,12),"w5":ngrams(terms,5),"ids":ids}
def overlap(a,b):
    reasons=[]
    if a["normalized"] and a["normalized"]==b["normalized"]:reasons.append("NORMALIZED_EXACT")
    if not a["t32"].isdisjoint(b["t32"]):reasons.append("TOKEN32")
    if not a["w12"].isdisjoint(b["w12"]):reasons.append("WORD12")
    smaller=min(len(a["w5"]),len(b["w5"]))
    if smaller>=20 and len(a["w5"]&b["w5"])*2>=smaller:reasons.append("WORD5_CONTAINMENT_GE_HALF")
    return reasons
def exclusion_reason(text):
    if type(text)is not str:return "NOT_STRING"
    if "\ufffd" in text:return "REPLACEMENT_CHARACTER"
    if "\\" in text:return "LITERAL_BACKSLASH"
    if "<" in text or ">" in text:return "ANGLE_BRACKET"
    n=sum(not c.isspace() for c in text);alpha=sum(c.isalpha() for c in text)
    if not n or alpha/n<.65:return "ALPHABETIC_RATIO"
    if all(c not in text for c in (".","?","!")):return "NO_SENTENCE_PUNCTUATION"
    return None


def independent_candidates(source,ledger,tokenize,expected_rows=7600):
    require(len(source)==len(ledger)==expected_rows,"Complete source and candidate coverage")
    require(len({r["id"] for r in ledger})==expected_rows,"Unique source identities")
    eligible={}
    for i,(source_row,receipt) in enumerate(zip(source,ledger)):
        text=source_row["text"];label=source_row["label"]
        require(type(text)is str and type(label)is int and label in (0,1,2,3),"Source schema")
        identity={"corpus_sha256":CORPUS["sha256"],"row":i,"text_sha256":sha(text.encode())};cid=sha(encoded(identity))
        base={"id":cid,"row":i,"label":label,"text_sha256":identity["text_sha256"]}
        require(all(receipt.get(k)==v for k,v in base.items()),"Source-derived candidate identity "+str(i))
        reason=exclusion_reason(text)
        if reason:require(receipt=={**base,"decision":"EXCLUDE_"+reason},"Independent prose eligibility "+str(i));continue
        ids=tokenize(text);require(valid_ids(ids),"Original tokenizer IDs")
        base["full_token_count"]=len(ids)
        if len(ids)<129:require(receipt=={**base,"decision":"EXCLUDE_SHORT"},"Independent short-text exclusion "+str(i));continue
        require(receipt.get("full_token_count")==len(ids),"Complete source token count")
        require(receipt["decision"] in ("EXCLUDE_HISTORY","EXCLUDE_NEW_DUPLICATE","SELECTED","ELIGIBLE_NOT_SELECTED"),"Eligible candidate has final decision")
        eligible[cid]={**base,"text":text,"fingerprint":fingerprint(text,ids)}
    return eligible


def audit_witnesses(eligible,ledger,history,tokenize,arrow_reader,member_policy):
    """Check every claimed historical exclusion, sharing only the frozen parser."""
    h={r["path"]:r for r in history};requested={};count=0
    for r in ledger:
        if r["decision"]!="EXCLUDE_HISTORY":continue
        w=r["witness"];source=w["source"];p=source["path"]
        require(p in h and h[p]["Status"]=="PASS" and source["sha256"]==h[p]["sha256"],"Historical witness actual parsed byte source")
        require(type(w["reasons"])is list and w["reasons"]==sorted(set(w["reasons"])) and bool(w["reasons"]),"Historical witness reason list")
        requested.setdefault(p,{}).setdefault(source["location"],[]).append(r);count+=1
    checked=0
    for p,locations in requested.items():
        found=set()
        for kind,value,where in parser_contract.byte_leaves(Path(p).read_bytes(),h[p]["kind"],p,arrow_reader,member_policy=member_policy):
            if where not in locations or kind not in ("text","tokens"):continue
            if kind=="text":
                ids=tokenize(value);require(valid_ids(ids),"Witness tokenizer IDs");fp=fingerprint(value,ids)
            else:
                require(valid_ids(value),"Witness token-array IDs");fp={"normalized":None,"t32":ngrams(value,32),"w12":set(),"w5":set()}
            for r in locations[where]:
                actual=sorted(overlap(eligible[r["id"]]["fingerprint"],fp))
                require(actual==r["witness"]["reasons"],"Historical exclusion witness overlap independently recomputed")
                checked+=1
            found.add(where)
        require(found==set(locations),"Every historical exclusion witness location found")
    require(checked==count,"Historical witness exact count")
    return {"excluded_candidates":count,"distinct_witness_files":len(requested),"parser_reuse":"Frozen data_prepare.byte_leaves only; overlap/tokenization independently recomputed"}


def independent_selection(eligible,ledger):
    records={r["id"]:r for r in ledger};selected=[]
    for label in (0,1,2,3):
        chosen=0
        for cid in sorted(k for k,v in eligible.items() if v["label"]==label):
            candidate=eligible[cid];row=records[cid]
            if row["decision"]=="EXCLUDE_HISTORY":continue
            duplicate=None
            for old in selected:
                reasons=overlap(candidate["fingerprint"],old["fingerprint"])
                if reasons:duplicate={"selected_id":old["id"],"reasons":reasons};break
            if duplicate:require(row["decision"]=="EXCLUDE_NEW_DUPLICATE" and row.get("witness")==duplicate,"Independent new-new exclusion");continue
            require("witness" not in row,"No unexplained eligible witness")
            if chosen==5:require(row["decision"]=="ELIGIBLE_NOT_SELECTED","Quota survivors remain unselected");continue
            require(row["decision"]=="SELECTED","First five survivors per frozen class");selected.append(candidate);chosen+=1
        require(chosen==5,"Exact five per class")
    require(len(selected)==20,"Exactly20 selected")
    return selected


def audit_payload(selected,payload,public,input_pin):
    require(payload["context_tokens"]==128 and payload["scored_positions"]==[64,128] and payload["scored_target_offsets"]==[65,129],"Frozen129-token alignment")
    require(payload["eval_seeds"]==[5101,5202] and payload["train_seeds"]==[4101,4202] and payload["optimizer_steps"]==0,"Frozen zero-training settings")
    require(len(payload["eval"])==20,"20 payload records")
    for i,(c,row) in enumerate(zip(selected,payload["eval"])):
        ids=c["fingerprint"]["ids"][:129]
        expected={"id":c["id"],"index":i,"row":c["row"],"label":c["label"],"text":c["text"],"text_sha256":c["text_sha256"],"full_row_token_count":len(c["fingerprint"]["ids"]),"tokens":ids,"window_sha256":ids_pin(ids),"input_sha256":ids_pin(ids[:128]),"scored_targets_sha256":ids_pin(ids[65:129])}
        require(row==expected,"Complete selected source/token/payload binding "+str(i))
    require(public=={"samples":[{k:v for k,v in r.items() if k not in ("text","tokens")} for r in payload["eval"]],"input_pin":input_pin,"labels":{str(k):5 for k in range(4)}},"Public selection exact private payload projection")
    provenance=payload["provenance"]
    require(provenance["dataset"]=="fancyzhx/ag_news" and provenance["revision"]==REVISION and provenance["split"]=="test" and provenance["corpus"]==CORPUS,"Original source provenance")


def verify_artifacts(prep,manifest):
    expected={"corpus.parquet","acquisition.json","inputs.json","public/selection.json","candidates.json.gz","history_ledger.json.gz"}
    require(set(manifest["artifacts"])==expected,"Complete preparation artifact manifest")
    require({str(p.relative_to(prep)) for p in prep.rglob("*") if p.is_file()}==expected|{"manifest.json"},"No unlisted preparation artifacts")
    for name,receipt in manifest["artifacts"].items():
        path=prep/name;require(not path.is_symlink(),"Artifact no symlink")
        if name.endswith(".gz"):
            require(pin(path)==receipt["physical"],"Compressed physical pin "+name)
            with gzip.open(path,"rb") as stream:raw=stream.read(LIMIT+1)
            require(len(raw)<=LIMIT and {"bytes":len(raw),"sha256":sha(raw)}==receipt["canonical"],"Lossless expanded canonical receipt "+name)
            require(encoded(loads(raw))==raw,"Canonical ledger serialization "+name)
        else:require(pin(path)==receipt,"Artifact pin "+name)


def audit(spec,spec_sha,prep,tokenize,arrow_reader,check):
    prep=Path(prep);manifest=read(prep/"manifest.json")
    check("Preparation completed with zero model calls",manifest["Status"]=="PASS" and manifest["source_after_status"]=="PASS" and manifest["forbidden_imports"]==[] and manifest["Actual"]["model_calls"]==0)
    check("Preparation bound frozen spec and source",manifest["Input"]["spec_sha256"]==spec_sha and manifest["Input"]["source"]==URL)
    verify_artifacts(prep,manifest);check("All artifact byte and canonical receipts",True)
    require(pin(prep/"corpus.parquet")==CORPUS,"Original corpus exact bytes")
    acquisition=read(prep/"acquisition.json")
    check("Single successful fixed source acquisition",acquisition["Status"]=="PASS" and acquisition["url"]==URL and acquisition["http_status"]==200 and acquisition["actual_response"]==CORPUS and acquisition["pin"]==CORPUS and acquisition["response_file"]=="corpus.parquet")
    policy=policies(spec);history=read(prep/"history_ledger.json.gz");historical=audit_history(spec,policy,history)
    check("Full independent inventory/classification/hash reconciliation",True,historical)
    source=arrow_reader((prep/"corpus.parquet").read_bytes(),"parquet");ledger=read(prep/"candidates.json.gz")
    eligible=independent_candidates(source,ledger,tokenize);check("All7600 source rows independently retokenized/eligibility checked",True,{"source_rows":len(source),"eligible":len(eligible)})
    witnesses=audit_witnesses(eligible,ledger,history,tokenize,arrow_reader,policy["member_entries"]);check("All positive history-exclusion witnesses",True,witnesses)
    chosen=independent_selection(eligible,ledger);check("Independent first-five-per-class and full-text new-new exclusion",True)
    payload=read(prep/"inputs.json");public=read(prep/"public/selection.json");input_pin=pin(prep/"inputs.json")
    audit_payload(chosen,payload,public,input_pin);check("Selected source text/token targets and public projection",True)
    actual=manifest["Actual"]
    check("Manifest aggregate scan/selection counters reconciled",actual["source_rows"]==7600 and actual["prose_length_eligible"]==len(eligible) and actual["historical_files"]==historical["files"] and actual["historical_strings"]==historical["strings"] and actual["historical_token_arrays"]==historical["token_arrays"] and actual["historical_format_notes"]==historical["format_notes"] and actual["excluded_by_history"]==witnesses["excluded_candidates"] and actual["selected"]==20 and actual["input_pin"]==input_pin)
    # No exhaustive old-tokenizer rescan: absence is the preparer's complete-scan
    # claim, backed here by full coverage and byte pins, not independently reproven.
    return {"source_rows":7600,"eligible":len(eligible),"selected":20,"per_class":{str(k):5 for k in range(4)},"history":historical,"historical_witnesses":witnesses,"input_pin":input_pin,"preparation_manifest":pin(prep/"manifest.json"),"selected_ids":[x["id"] for x in chosen],"new_model_calls":0,"new_source_acquisitions":0,"historical_absence_independently_rescanned":False,"historical_absence_basis":"Frozen preparer full scan; audit independently verifies complete inventory, bytes/classifications and all claimed positive exclusion witnesses; no second full-history tokenization"}


def main():
    cli=argparse.ArgumentParser();cli.add_argument("--spec",type=Path,required=True);cli.add_argument("--expected-spec-sha",required=True);cli.add_argument("--prep",type=Path,required=True);cli.add_argument("--output",type=Path,required=True);args=cli.parse_args()
    report={"Purpose":"Independent read-only fresh-source, selection and custody audit","Environment":{},"Input":{"spec":str(args.spec),"spec_sha256":args.expected_spec_sha,"prep":str(args.prep)},"Expected":"All source/token/selection/coverage checks PASS before models; no historical absence overclaim","Actual":{},"Status":"NOT TESTED","checks":[]}
    def check(purpose,okay,actual=None):
        report["checks"].append({"Purpose":purpose,"Expected":True,"Actual":actual,"Status":"PASS" if okay else "FAIL"});require(okay,purpose)
    try:
        require(all(p.is_absolute() for p in (args.spec,args.prep,args.output)) and not args.output.exists() and not args.output.resolve().is_relative_to(args.prep.resolve()),"New absolute audit output outside preserved preparation")
        require(platform.system()=="Linux" and platform.python_version()=="3.12.3" and sys.executable==PYTHON and sys.flags.isolated and sys.dont_write_bytecode and os.environ.get("CODESPACE_NAME")==SPACE,"Frozen isolated data environment","BLOCKED")
        require(pin(args.spec)["sha256"]==args.expected_spec_sha,"Frozen specification bytes")
        spec=read(args.spec);require(spec["schema"]=="mythos-fresh-history-v1","History schema")
        tokenizer_path=Path(spec["tokenizer_path"]);require(pin(tokenizer_path)["sha256"]==TOKENIZER_SHA,"Original tokenizer bytes")
        versions={name:importlib.metadata.version(name) for name in ("numpy","pyarrow","tokenizers")}
        require(versions=={"numpy":"1.26.4","pyarrow":"19.0.1","tokenizers":"0.23.2"},"Frozen data dependencies","BLOCKED")
        import numpy as np
        import pyarrow as pa
        import pyarrow.parquet as pq
        from tokenizers import Tokenizer
        report["Environment"]={"python":sys.version,"executable":sys.executable,"packages":versions,"development_only":False}
        tokenizer=Tokenizer.from_file(str(tokenizer_path));tokenize=lambda text:tokenizer.encode(text,add_special_tokens=False).ids
        def arrow_reader(raw,kind):
            if kind=="npy":
                array=np.load(io.BytesIO(raw),allow_pickle=False);require(array.dtype.kind in "biufUS","Historical NPY kind")
                return [{"array":array.tolist(),"dtype":str(array.dtype)}]
            source=pa.BufferReader(raw)
            if kind=="parquet":table=pq.read_table(source)
            else:
                try:table=pa.ipc.open_file(source).read_all()
                except pa.ArrowInvalid:source.seek(0);table=pa.ipc.open_stream(source).read_all()
            return table.to_pylist()
        report["Actual"]=audit(spec,args.expected_spec_sha,args.prep,tokenize,arrow_reader,check)
        check("Frozen spec/tokenizer preserved after audit",pin(args.spec)["sha256"]==args.expected_spec_sha and pin(tokenizer_path)["sha256"]==TOKENIZER_SHA)
        check("No forbidden model-library imports",not any(n.split(".")[0] in FORBIDDEN for n in sys.modules));report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]=getattr(exc,"status","BLOCKED" if isinstance(exc,(OSError,MemoryError,KeyboardInterrupt)) else "FAIL")
        report["error"]={"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    report["Limits"]=["Audit independence is in selection/overlap/hash/coverage logic; targeted history witness container parsing uses the frozen preparer parser.","Novelty limited to frozen retained/readable project history and matching rules, not serialized checkpoint internals, external/unrecorded content, semantic equivalence or base pretraining.","No statistical, production-quality, model efficacy or efficiency acceptance implied."]
    report["check_counts"]={s:sum(c["Status"]==s for c in report["checks"]) for s in ("PASS","FAIL")};report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw=encoded(report);require(len(raw)<=65536,"Audit report within64KiB")
    require(args.output.parent.is_dir() and shutil.disk_usage(args.output.parent).free>=256*1024**2+len(raw),"Audit sealing retains256MiB reserve","BLOCKED")
    with args.output.open("xb") as stream:stream.write(raw)
    print(json.dumps({"Status":report["Status"],"checks":report["check_counts"],"Actual":report["Actual"],"error":report.get("error")},allow_nan=False))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
