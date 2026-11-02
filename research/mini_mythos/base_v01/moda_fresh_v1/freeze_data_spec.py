"""Freeze exact historical-format policies. Stdlib only; no acquisition/model calls."""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import data_prepare as parser

REPO=Path("/workspaces/mythos-moda-fresh-cpu-v1")
BRANCH="mythos-moda-fresh-cpu-v1"
SPACE="bookish-pancake-vwqx7rr9x5w3wxjr"
OUT=Path("/workspaces/mythos-evidence/base_v01/moda_fresh/specification-v1")
HISTORY_ROOTS=(Path("/workspaces/OpenMythos"),Path("/workspaces/mythos-evidence"))
EXCLUDED=OUT.parent
PRIOR=Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz")
PRIOR_PIN={"bytes":1181241,"sha256":"6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02"}
DISCOVERY_SHA="d8c9b5af0184ab99b6d84b3b659ca12b8666052b030def372bbed5e5420397ea"
TOKENIZER=Path("/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/tokenizer/tokenizer.json")
TOKENIZER_SHA="e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
M2_ARCHIVE="/workspaces/OpenMythos/mythos_evidence/M2L_CPU_3seeds_20261029_085315.tar.gz"
M2_PHYSICAL=Path("/workspaces/OpenMythos/mythos_evidence")
WHEEL="/workspaces/mythos-evidence/base_v01/depth_budget/preparation-v2-20261101/pyarrow-19.0.1-cp312-cp312-manylinux_2_28_x86_64.whl"
FIGURE="/workspaces/mythos-parcae-pinned/assets/main_fig-1.png"
MAX_OUTPUT=1024*1024
SEAL=64*1024
RESERVE=256*1024*1024
MAX_EXPANDED=512*1024*1024
TEXT_NAMES={".gitignore","LICENSE",".gitkeep","Dockerfile"}
TEXT_SUFFIXES={".sh",".slurm",".started"}


class Stop(Exception):pass
def require(value,why):
    if not value:raise Stop(why)
def encoded(value):return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def sha(data):return hashlib.sha256(data).hexdigest()
def pin(path):
    require(path.is_file() and not path.is_symlink(),"Missing or symlink file: "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as stream:
        while chunk:=stream.read(1024*1024):h.update(chunk)
    return {"bytes":path.stat().st_size,"sha256":h.hexdigest()}
def strict(data):return parser.strict_json(data.decode("utf-8-sig"))
def read_bounded_gzip(path,limit):
    with gzip.GzipFile(fileobj=io.BytesIO(path.read_bytes())) as stream:data=stream.read(limit+1)
    require(len(data)<=limit,"Gzip expansion bound");return data


def enumerate_union(roots,prior,excluded):
    observed=set(prior)
    for root in roots:
        require(root.is_absolute() and root.is_dir() and not root.is_symlink(),"Historical root missing: "+str(root))
        for current,dirs,files in os.walk(root,followlinks=False):
            parent=Path(current);keep=[]
            for name in dirs:
                child=parent/name
                if name in (".git","__pycache__") or child==excluded:continue
                require(not child.is_symlink(),"Historical directory symlink: "+str(child));keep.append(name)
            dirs[:]=keep
            for name in files:
                p=parent/name;require(not p.is_symlink(),"Historical file symlink: "+str(p));observed.add(str(p))
    require(all(Path(p).is_absolute() and Path(p).is_file() and not Path(p).is_symlink() for p in observed),"Prior/union path unavailable")
    return sorted(observed)


def known_binary_reason(path):
    """Called only after exact discovery allowlist membership and byte pin checks."""
    p=PurePosixPath(path)
    if p.suffix==".bin":
        if p.name=="pytorch_model.bin":return "Exact discovered pretrained tensor checkpoint; not deserialized as a text corpus."
        if "rng" in p.name.lower():return "Exact discovered serialized RNG-state bytes; not language text."
        return "Exact discovered raw numerical model/logit/state evidence; no text deserialization."
    require(p.suffix==".pt","Unsupported discovered binary suffix")
    return "Exact discovered serialized model/adapter/training or loader-state tensor checkpoint; not deserialized. Text novelty excludes arbitrary serialized internals."


def text_exception(name,data):
    p=PurePosixPath(name)
    if p.name in TEXT_NAMES or p.suffix in TEXT_SUFFIXES:
        data.decode("utf-8-sig",errors="strict")
        return "text","Explicit known UTF-8 source/license/marker text; retained in history scan."
    if p.suffix==".raw":
        strict(data)
        return "json","Exact discovered acquisition JSON with .raw suffix; parsed as strict JSON."
    raise Stop("Unregistered potential historical format: "+name)


def archive_policy(path,discovered,physical_pin):
    """Only exact discovery members, and exact M2L checkpoint copies may be nontext."""
    raw=path.read_bytes();fmt=discovered["container"]["format"]
    expected={v["name"]:v["bytes"] for v in discovered["container"]["members"]}
    require(len(expected)==len(discovered["container"]["members"]),"Duplicate discovery archive member")
    policies={};observed={};total=0
    virtual=str(path)[:-3] if str(path).endswith(".gz") else str(path)
    def member(name,size,data):
        nonlocal total
        require(name not in observed,"Duplicate archive member: "+name)
        total+=size;require(total<=MAX_EXPANDED,"Archive expansion bound")
        require(expected.get(name)==size and len(data)==size,"Archive member discovery differs: "+name)
        observed[name]=size;kind=parser.classify_name(name)
        if kind is not None:return
        vname=virtual+"!"+name;info={"bytes":size,"sha256":sha(data)}
        if PurePosixPath(name).suffix==".pt":
            require(str(path)==M2_ARCHIVE and PurePosixPath(name).parts[0]=="m2_long_v1" and ".." not in PurePosixPath(name).parts,"Unregistered archive binary: "+vname)
            match=physical_pin(M2_PHYSICAL/name)
            require(info==match,"Archive checkpoint differs from exact retained physical copy: "+vname)
            policies[vname]={**info,"kind":"nontext","reason":"Exact M2L archive tensor checkpoint, byte-identical to retained physical checkpoint; serialized internals are outside readable-text novelty."}
        else:
            kind,reason=text_exception(name,data)
            policies[vname]={**info,"kind":kind,"reason":reason}
    if fmt=="zip":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for item in archive.infolist():
                if item.is_dir():continue
                require((item.external_attr>>16)&0o170000 != 0o120000,"Archive symlink unsupported")
                require(total+item.file_size<=MAX_EXPANDED,"Archive expansion bound")
                member(item.filename,item.file_size,archive.read(item))
    else:
        require(fmt=="tar","Unsupported archive policy format")
        with tarfile.open(fileobj=io.BytesIO(raw),mode="r:*") as archive:
            for item in archive:
                if item.isdir():continue
                require(item.isfile(),"Archive special member unsupported")
                require(total+item.size<=MAX_EXPANDED,"Archive expansion bound")
                stream=archive.extractfile(item);require(stream is not None,"Unreadable archive member")
                member(item.name,item.size,stream.read(MAX_EXPANDED+1))
    require(observed==expected,"Archive member set differs from frozen discovery")
    return policies


def build_policies(paths,prior,discovery):
    actual=discovery["Actual"]
    require(len(paths)==actual["count"]==32244,"History count differs from frozen discovery")
    require(dict(collections.Counter(Path(p).suffix.lower() for p in paths))==actual["suffixes"],"History suffix inventory differs")
    binaries={str(PurePosixPath(g["parent"])/v["name"]):v["bytes"] for g in actual["binary_groups"] for v in g["files"]}
    require(set(binaries)=={p for p in paths if Path(p).suffix.lower() in (".bin",".pt")},"Exact binary allowlist differs")
    special={v["path"]:v for v in actual["special"]}
    pins={};nontext={};formats={};members={}
    def checked(path):
        key=str(path)
        if key not in pins:
            pins[key]=pin(path)
            if key in prior:require(pins[key]==prior[key],"Previously protected file changed: "+key)
        return pins[key]
    for name in paths:
        p=Path(name);kind=parser.classify_name(name)
        if name in binaries:
            value=checked(p);require(value["bytes"]==binaries[name],"Discovered binary size changed")
            nontext[name]={**value,"reason":known_binary_reason(name)}
        elif name in (WHEEL,FIGURE):
            value=checked(p);require(value["bytes"]==special[name]["bytes"],"Nontext discovery size changed")
            with p.open("rb") as stream:header=stream.read(8)
            require((name==WHEEL and value["bytes"]==42087026 and header[:2]==b"PK") or (name==FIGURE and value["bytes"]==146577 and header==b"\x89PNG\r\n\x1a\n"),"Known software/figure format changed")
            nontext[name]={**value,"reason":"Exact retained PyArrow software wheel, not a language corpus." if name==WHEEL else "Exact upstream architectural figure PNG, not readable text."}
        elif kind is None:
            value=checked(p);registered,reason=text_exception(name,p.read_bytes())
            formats[name]={**value,"kind":registered,"reason":reason}
        if name in special and special[name].get("container",{}).get("format") in ("zip","tar"):
            value=checked(p);require(value["bytes"]==special[name]["bytes"],"Archive discovery size changed")
            require(kind in ("zip","gzip"),"Unexpected physical archive suffix")
            formats[name]={**value,"kind":kind,"reason":"Exact archive/member allowlist checked before acquisition; all readable members retained."}
            added=archive_policy(p,special[name],checked)
            require(not set(added)&set(members),"Duplicate virtual member policy");members.update(added)
    require(len(nontext)==4647,"Expected exact 4,645 tensor files plus one wheel and one PNG")
    require(sum(v["kind"]=="nontext" for v in members.values())==18,"Expected exact 18 M2L archived checkpoints")
    require(not set(nontext)&set(formats),"Conflicting classifications")
    return nontext,formats,members


def serialize_outputs(nontext,formats,members,discovery):
    payloads={name+".json.gz":gzip.compress(encoded(value),compresslevel=9,mtime=0) for name,value in (("nontext_entries",nontext),("format_entries",formats),("member_entries",members))}
    spec={"schema":"mythos-fresh-history-v1","tokenizer_path":str(TOKENIZER),"history_roots":[str(p) for p in HISTORY_ROOTS],"excluded_roots":[{"path":str(EXCLUDED),"reason":"New experiment specification/preparation/run namespace; contains no prior training/debug history."}],"discover_before_acquisition":True,"extra_history_inventory_path":str(PRIOR),"extra_history_inventory_pin":PRIOR_PIN,"expected_history_file_count":32244,"expected_history_suffixes":discovery["Actual"]["suffixes"]}
    for name,raw in payloads.items():
        key=name.removesuffix(".json.gz");spec[key+"_path"]=str(OUT/name);spec[key+"_pin"]={"bytes":len(raw),"sha256":sha(raw)}
    payloads["DATA_SPEC.json"]=encoded(spec)+b"\n"
    require(sum(map(len,payloads.values()))+SEAL<=MAX_OUTPUT,"Specification exceeds frozen 1 MiB output budget")
    return payloads


def write_exclusive(path,raw):
    require(not path.exists(),"Refusing overwrite: "+str(path))
    with path.open("xb") as stream:stream.write(raw)


def main():
    cli=argparse.ArgumentParser();cli.add_argument("--expected-head",required=True);args=cli.parse_args()
    report={"Purpose":"Freeze complete historical input-format classifications before any new source acquisition","Environment":{"runtime":"stdlib only","codespace":os.environ.get("CODESPACE_NAME"),"python":sys.version},"Input":{"expected_head":args.expected_head,"discovery_canonical_sha256":DISCOVERY_SHA,"prior_inventory":str(PRIOR),"prior_inventory_pin":PRIOR_PIN},"Expected":{"history_files":32244,"binary_files":4645,"archived_nontext_members":18,"max_output_bytes":MAX_OUTPUT,"reserve_bytes":RESERVE,"new_source_acquisitions":0,"model_calls":0},"Actual":{"new_source_acquisitions":0,"model_calls":0,"outputs":{}},"Status":"BLOCKED"}
    created=False
    try:
        require(os.environ.get("CODESPACE_NAME")==SPACE,"Designated Codespace required")
        require(HERE==REPO/"research/mini_mythos/base_v01/moda_fresh_v1","Designated isolated worktree required")
        require(bool(sys.flags.isolated) and sys.dont_write_bytecode,"Require Python -I -B")
        git=lambda *a:subprocess.check_output(["git","-C",str(REPO),*a],text=True).strip()
        require(git("rev-parse","HEAD")==args.expected_head and git("branch","--show-current")==BRANCH,"Frozen source/branch required")
        require(not git("status","--porcelain"),"Frozen source tree must be clean")
        require(not OUT.exists(),"Existing specification attempt; no overwrite/retry")
        require(shutil.disk_usage(OUT.parent).free>=RESERVE+MAX_OUTPUT,"Specification disk reserve unavailable")
        OUT.mkdir();created=True
        discovery=strict((HERE/"HISTORY_FORMAT_DISCOVERY.json").read_bytes())
        require(sha(encoded(discovery))==DISCOVERY_SHA and discovery["Status"]=="PASS" and not discovery["Actual"]["missing"],"Frozen discovery changed")
        require(pin(PRIOR)==PRIOR_PIN,"Prior inventory bytes changed")
        prior=strict(read_bounded_gzip(PRIOR,32*1024*1024));require(len(prior)==25436,"Prior inventory entry count")
        require(pin(TOKENIZER)["sha256"]==TOKENIZER_SHA,"Frozen tokenizer changed")
        paths=enumerate_union(HISTORY_ROOTS,prior,EXCLUDED)
        nontext,formats,members=build_policies(paths,prior,discovery)
        payloads=serialize_outputs(nontext,formats,members,discovery)
        require(shutil.disk_usage(OUT).free>=RESERVE+sum(map(len,payloads.values()))+SEAL,"Actual specification payload exceeds free disk")
        for name,raw in payloads.items():
            write_exclusive(OUT/name,raw);report["Actual"]["outputs"][name]={"bytes":len(raw),"sha256":sha(raw)}
        require(enumerate_union(HISTORY_ROOTS,prior,EXCLUDED)==paths,"History path set changed during classification")
        require(pin(PRIOR)==PRIOR_PIN,"Prior inventory changed during classification")
        report["Actual"].update(history_files=len(paths),nontext_files=len(nontext),explicit_format_files=len(formats),archive_member_policies=len(members),archived_nontext_members=sum(v["kind"]=="nontext" for v in members.values()),payload_bytes=sum(map(len,payloads.values())),free_disk_after_bytes=shutil.disk_usage(OUT).free,forbidden_modules_loaded=sorted(set(sys.modules)&{"torch","numpy","pyarrow","tokenizers","parcae_lm","receval","transformers"}))
        require(not report["Actual"]["forbidden_modules_loaded"],"Unexpected numerical/model import")
        report["Status"]="PASS"
    except Exception as exc:
        report["Actual"]["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()};report["Status"]="BLOCKED"
    raw=encoded(report)+b"\n"
    if created:
        require(len(raw)<=SEAL,"Specification receipt exceeds reserved seal")
        write_exclusive(OUT/"SPECIFICATION_RECEIPT.json",raw)
    print(raw.decode(),end="")
    return 0 if report["Status"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
