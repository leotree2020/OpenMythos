"""Freeze the prior readable-history universe before new-source acquisition."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

REPO=Path("/workspaces/mythos-moda-fresh-cpu-v1")
FRESH=Path("/workspaces/mythos-evidence/base_v01/moda_fresh")
OUT=FRESH/"specification-v6"
OLD=FRESH/"specification-v1/DATA_SPEC.json"
OLD_SHA="6185f5dee8c9f95e35a967c3f8abd5754221ed02207c68244ce3d2bdc4dcb8e9"
EXCLUDED={FRESH/name for name in ("specification-v6","source-v6","preparation-v6","attempt-v6")}
MAX_OUTPUT=64*1024**2
RESERVE=256*1024**2

def pin(path):
    path=Path(path)
    assert path.is_file() and not path.is_symlink(),str(path)
    h=hashlib.sha256();n=0
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024**2),b""):h.update(block);n+=len(block)
    return {"bytes":n,"sha256":h.hexdigest()}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()+b"\n"
def read(path):return json.loads(Path(path).read_bytes())
def git(*args):return subprocess.check_output(["git","-C",str(REPO),*args],text=True).strip()
def historical_git_json(name):
    return json.loads(subprocess.check_output(["git","-C",str(REPO),"show","b3565ae427df93991bb7f78e633f3229c5930dd5:research/mini_mythos/base_v01/moda_fresh_v1/"+name]))

def repo_files():
    result=[]
    for current,dirs,files in os.walk(REPO,followlinks=False):
        parent=Path(current);keep=[]
        for name in dirs:
            child=parent/name
            if name in (".git","__pycache__"):continue
            assert not child.is_symlink(),str(child)
            keep.append(name)
        dirs[:]=keep
        for name in files:
            if name==".git":continue
            path=parent/name;assert not path.is_symlink(),str(path);result.append(path)
    return sorted(result)

def enumerate_paths(old,prior):
    paths=set(prior)
    for root in map(Path,old["history_roots"]):
        assert root.is_absolute() and root.is_dir() and not root.is_symlink()
        for current,dirs,files in os.walk(root,followlinks=False):
            parent=Path(current);keep=[]
            for name in dirs:
                child=parent/name
                if name in (".git","__pycache__") or child in EXCLUDED or child==FRESH:continue
                assert not child.is_symlink(),str(child)
                keep.append(name)
            dirs[:]=keep
            for name in files:
                path=parent/name;assert not path.is_symlink(),str(path);paths.add(str(path))
    assert len(paths)==old["expected_history_file_count"]==32244,"Original history scope changed"
    original=set(paths)
    for current,dirs,files in os.walk(FRESH,followlinks=False):
        parent=Path(current);keep=[]
        for name in dirs:
            child=parent/name
            if name in (".git","__pycache__") or child in EXCLUDED:continue
            assert not child.is_symlink(),str(child)
            keep.append(name)
        dirs[:]=keep
        for name in files:
            path=parent/name;assert not path.is_symlink(),str(path);paths.add(str(path))
    assert str(FRESH/"preparation-v2/data/corpus.parquet") in paths-original
    return sorted(paths),original

def main():
    cli=argparse.ArgumentParser();cli.add_argument("--expected-head",required=True);args=cli.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert os.environ.get("CODESPACE_NAME")=="bookish-pancake-vwqx7rr9x5w3wxjr"
    assert git("rev-parse","HEAD")==args.expected_head and not git("status","--porcelain")
    assert not (FRESH/"source-v6").exists() and not OUT.exists()
    assert shutil.disk_usage(FRESH).free>=RESERVE+MAX_OUTPUT
    OUT.mkdir()
    report={"Purpose":"Freeze complete prior history including all older fresh preparations and the whole previously read AG News test corpus before new train acquisition","Environment":{"codespace":os.environ["CODESPACE_NAME"],"python":sys.version},"Input":{"source_freeze":args.expected_head,"old_spec_sha256":OLD_SHA},"Expected":{"original_history_paths":32244,"no_dropped_paths":True,"source_acquisitions":0,"model_calls":0},"Actual":{},"Status":"BLOCKED"}
    try:
        assert pin(OLD)["sha256"]==OLD_SHA
        old=read(OLD);prior_path=Path(old["extra_history_inventory_path"])
        assert pin(prior_path)==old["extra_history_inventory_pin"]
        prior=json.loads(gzip.decompress(prior_path.read_bytes()))
        paths,original=enumerate_paths(old,prior)
        mapping={}
        for i,path in enumerate(paths):
            value=pin(path)
            if path in prior:assert value==prior[path],path
            mapping[path]=value
            if i%6000==0:print("History freeze",i,"/",len(paths),flush=True)
        assert enumerate_paths(old,prior)[0]==paths
        # Reuse sealed old-fresh custody pins, rather than accepting changed bytes.
        old_v4=historical_git_json("continuation_v4_evidence/EXTERNAL_MANIFEST.json")
        old_before=FRESH/"preparation-v4/old_fresh_before.json"
        assert pin(old_before)==old_v4[str(old_before)]
        sealed={**read(old_before),**old_v4}
        old_v5=historical_git_json("CONTINUATION_V5_EXPORT_MANIFEST.json")
        for entry in old_v5.values():sealed[entry["source"]]={key:entry[key] for key in ("bytes","sha256")}
        extra_sealed=0
        for path,value in sealed.items():
            if path not in mapping:mapping[path]=pin(path);extra_sealed+=1
            assert mapping[path]==value,path
        assert mapping[str(FRESH/"preparation-v2/data/corpus.parquet")]=={"bytes":1234829,"sha256":"71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb"}
        # Snapshot all prior isolated-worktree source/input bytes. Later new-phase
        # files cannot erase the debugging text seen before this source acquisition.
        originals=repo_files();origins={};snapshot_bytes=0
        for source in originals:
            assert not str(source).startswith(str(OUT)+"/")
            before_pin=pin(source);snapshot_bytes+=before_pin["bytes"]
            assert snapshot_bytes+2*1024**2+65536<=MAX_OUTPUT,"Repository history snapshot budget"
            dest=OUT/"repo_history_snapshot"/source.relative_to(REPO)
            dest.parent.mkdir(parents=True,exist_ok=True)
            with source.open("rb") as inp,dest.open("xb") as stream:shutil.copyfileobj(inp,stream,1024**2)
            assert pin(source)==pin(dest)==before_pin
            mapping[str(dest)]=before_pin;origins[str(dest)]={"original_path":str(source),"pin":before_pin}
        assert repo_files()==originals
        policies={}
        for name in ("nontext_entries","format_entries","member_entries"):
            path=Path(old[name+"_path"]);assert pin(path)==old[name+"_pin"];policies[name]={"path":str(path),"pin":pin(path)}
        raw=canonical(mapping);compressed=gzip.compress(raw,compresslevel=9,mtime=0)
        assert snapshot_bytes+len(compressed)+65536<=MAX_OUTPUT
        with (OUT/"history_before.json.gz").open("xb") as stream:stream.write(compressed)
        spec={"schema":"mythos-history-v6-before-source","cutoff_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"original_spec":str(OLD),"original_spec_pin":pin(OLD),"original_history_count":len(original),"history_file_count":len(mapping),"added_old_fresh_files":len(paths)-len(original),"repo_snapshot_files":len(origins),"repo_snapshot_bytes":snapshot_bytes,"repo_snapshot_origins":origins,"inventory_path":str(OUT/"history_before.json.gz"),"inventory_pin":pin(OUT/"history_before.json.gz"),"inventory_canonical_pin":{"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()},"policy_reuse":policies,"excluded_new_protocol_roots":[str(path) for path in sorted(EXCLUDED)],"prior_test_corpus":str(FRESH/"preparation-v2/data/corpus.parquet"),"source_acquisitions":0,"model_calls":0}
        spec["added_external_sealed_files"]=extra_sealed
        assert snapshot_bytes+len(compressed)+len(canonical(spec))+65536<=MAX_OUTPUT
        with (OUT/"DATA_SPEC.json").open("xb") as stream:stream.write(canonical(spec))
        report["Actual"]={"history_file_count":len(mapping),"added_old_fresh_files":spec["added_old_fresh_files"],"repo_snapshot_files":len(origins),"repo_snapshot_bytes":snapshot_bytes,"prior_test_corpus_pin":mapping[spec["prior_test_corpus"]],"spec_pin":pin(OUT/"DATA_SPEC.json"),"source_acquisitions":0,"model_calls":0}
        report["Status"]="PASS"
    except BaseException as exc:report["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        with (OUT/"FREEZE_RECEIPT.json").open("xb") as stream:stream.write(canonical(report))
        print(json.dumps(report),flush=True)
    return 0 if report["Status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
