"""Model-blind fresh-text preparation; exact sources and exhaustive history ledger.

Only synthetic fixtures may run before the source/spec freeze. The CLI requires
the designated data environment and an explicit frozen historical-file inventory.
"""
from __future__ import annotations
import argparse
import ast
import base64
from collections import Counter
import csv
import datetime
import gzip
import hashlib
import importlib.metadata
import io
import json
import lzma
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import struct
import sys
import tarfile
import traceback
import urllib.request
import urllib.error
import zipfile
import xml.etree.ElementTree as ET

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
DATASET = "fancyzhx/ag_news"
REVISION = "eb185aade064a813bc0b7f42de02595523103ca4"
CORPUS_RELATIVE = "data/test-00000-of-00001.parquet"
URL = "https://huggingface.co/datasets/" + DATASET + "/resolve/" + REVISION + "/" + CORPUS_RELATIVE
CORPUS_PIN = {"bytes":1234829,"sha256":"71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb"}
TOKENIZER_SHA = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
TOTAL_ROWS, PER_CLASS, WINDOW, NGRAM_TOKENS, NGRAM_WORDS = 7600, 5, 129, 32, 12
PREP_BUDGET, DISK_RESERVE = 4*1024**2, 256*1024**2
SEAL_ALLOWANCE = 65536
TEXT_KINDS = {"json","jsonl","text","python","csv","tsv","xml","parquet","arrow","npy","zip","tar","base64","gzip","xz"}
FORBIDDEN = {"torch","parcae_lm","receval","transformers"}
MAX_EXPANDED_FILE_BYTES = 512*1024**2
POLICY_MAX_BYTES = 32*1024**2
TEXT_CACHE_LIMIT = 50000
RETAINED_CORPUS = "/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v2/data/corpus.parquet"
PYTHON_RECOVERY_KEYS = ("files","raw_utf8_bytes","string_fragments","token_arrays","adjacent_string_groups","rejected_origins")
PYTHON_RECOVERY_CHAR_BUDGET = 256*1024**2


class Stop(Exception):
    def __init__(self,status,message):
        super().__init__(message);self.status=status


def require(okay,reason,status="FAIL"):
    if not okay:raise Stop(status,reason)


def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")+b"\n"
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(path):
    h,n=hashlib.sha256(),0
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024**2),b""):h.update(b);n+=len(b)
    return {"bytes":n,"sha256":h.hexdigest()}


def normalized(text):return " ".join(text.casefold().split())
def words(text):return re.findall(r"[a-z0-9]+",text.casefold())
def itergrams(sequence,n):return (tuple(sequence[i:i+n]) for i in range(len(sequence)-n+1))
def grams(sequence,n):return set(itergrams(sequence,n))
def digest_tokens(ids):return sha(struct.pack("<"+str(len(ids))+"q",*ids))
def valid_tokens(ids):return isinstance(ids,list) and all(type(x) is int and 0<=x<32768 for x in ids)


def prose_reason(text):
    if not isinstance(text,str):return "NOT_STRING"
    if "\ufffd" in text:return "REPLACEMENT_CHARACTER"
    if "\\" in text:return "LITERAL_BACKSLASH"
    if "<" in text or ">" in text:return "ANGLE_BRACKET"
    chars=[c for c in text if not c.isspace()]
    if not chars or sum(c.isalpha() for c in chars)/len(chars)<.65:return "ALPHABETIC_RATIO"
    if not any(c in text for c in ".?!"):return "NO_SENTENCE_PUNCTUATION"
    return None


def fingerprint(text,tokenize):
    ids=tokenize(text);require(valid_tokens(ids),"Original tokenizer ID contract")
    w=words(text)
    return {"normalized":normalized(text),"token32":grams(ids,32),"word12":grams(w,12),"word5":grams(w,5),"ids":ids}


def overlaps(a,b):
    reasons=[]
    if a.get("normalized") and a.get("normalized")==b.get("normalized"):reasons.append("NORMALIZED_EXACT")
    if a["token32"] & b["token32"]:reasons.append("TOKEN32")
    if a["word12"] & b["word12"]:reasons.append("WORD12")
    x,y=a["word5"],b["word5"]
    if min(len(x),len(y))>=20 and 2*len(x&y)>=min(len(x),len(y)):reasons.append("WORD5_CONTAINMENT_GE_HALF")
    return reasons


def collect_candidates(rows,tokenize):
    """No model scores; all source rows accounted, labels only fix the strata."""
    require(len(rows)==TOTAL_ROWS,"Exactly7600 AG News rows")
    candidates,ledger=[],[]
    for i,row in enumerate(rows):
        require(set(row)>={"text","label"} and type(row["label"]) is int and row["label"] in range(4),"AG News source schema")
        text,label=row["text"],row["label"]
        require(isinstance(text,str),"AG News source text schema")
        text_hash=sha(text.encode());identity={"corpus_sha256":CORPUS_PIN["sha256"],"row":i,"text_sha256":text_hash}
        record={"id":sha(canonical(identity)),"row":i,"label":label,"text_sha256":text_hash,"decision":"NOT_TESTED"}
        reason=prose_reason(text)
        if reason:record["decision"]="EXCLUDE_"+reason
        else:
            fp=fingerprint(text,tokenize);record["full_token_count"]=len(fp["ids"])
            if len(fp["ids"])<WINDOW:record["decision"]="EXCLUDE_SHORT"
            else:
                record["decision"]="ELIGIBLE_PENDING_HISTORY"
                candidates.append({**record,"text":text,"fingerprint":fp})
        ledger.append(record)
    return candidates,ledger


class ExclusionIndex:
    """Candidate-sized indexes; never retain the complete historic token corpus."""
    def __init__(self,candidates):
        self.candidates={c["id"]:c for c in candidates};self.maps={k:{} for k in ("token32","word12","word5","normalized")}
        self.matches={};self.string_count=0;self.token_array_count=0;self.text_fingerprints=0;self.text_cache_hits=0;self.text_cache=set()
        self.format_notes={"duplicate_keys":0,"nonfinite_numeric_constants":0}
        self.python_recovery={k:0 for k in PYTHON_RECOVERY_KEYS}
        for c in candidates:
            f=c["fingerprint"]
            for kind in self.maps:
                for value in ([f[kind]] if kind=="normalized" else f[kind]):self.maps[kind].setdefault(value,set()).add(c["id"])

    def add(self,fp,source):
        found={}
        for kind in ("normalized","token32","word12"):
            for value in ([fp.get(kind)] if kind=="normalized" else fp[kind]):
                for cid in self.maps[kind].get(value,()):found.setdefault(cid,set()).add({"normalized":"NORMALIZED_EXACT","token32":"TOKEN32","word12":"WORD12"}[kind])
        old=fp["word5"]
        if len(old)>=20:
            hits={}
            for value in old:
                for cid in self.maps["word5"].get(value,()):hits[cid]=hits.get(cid,0)+1
            for cid,n in hits.items():
                smaller=min(len(old),len(self.candidates[cid]["fingerprint"]["word5"]))
                if smaller>=20 and 2*n>=smaller:found.setdefault(cid,set()).add("WORD5_CONTAINMENT_GE_HALF")
        for cid,reasons in found.items():
            # Retain the first complete witness, not thousands of repeated copies.
            self.matches.setdefault(cid,{"source":source,"reasons":sorted(reasons)})

    def text(self,text,source,tokenize):
        require(isinstance(text,str),"Historical text leaf schema")
        self.string_count+=1
        if not text.strip():return
        encoded=text.encode("utf-8");cache_key=len(encoded),sha(encoded)
        if cache_key in self.text_cache:self.text_cache_hits+=1;return
        if len(self.text_cache)<TEXT_CACHE_LIMIT:self.text_cache.add(cache_key)
        self.text_fingerprints+=1
        ids=tokenize(text);require(valid_tokens(ids),"Historical original tokenizer ID contract")
        w=words(text)
        # Only candidates need indexed32/12-gram sets. Historic sequences are
        # streamed against them; no character shortcut loses byte-fallback IDs.
        self.add({"normalized":normalized(text),"token32":itergrams(ids,32),"word12":itergrams(w,12),"word5":grams(w,5)},source)

    def tokens(self,ids,source):
        self.token_array_count+=1
        self.add({"normalized":None,"token32":itergrams(ids,32),"word12":set(),"word5":set()},source)


class HistoryObject(list):
    """Ordered JSON key/value pairs, including repeated keys."""


def json_leaves(value,where="$",depth=0):
    require(depth<=256,"Historical JSON exceeds safe nesting bound","BLOCKED")
    if isinstance(value,str):yield "text",value,where
    elif isinstance(value,HistoryObject):
        for i,(k,v) in enumerate(value):yield from json_leaves(v,where+"/pair:"+str(i)+"/"+k,depth+1)
    elif isinstance(value,dict):
        for k,v in value.items():yield from json_leaves(v,where+"/"+str(k),depth+1)
    elif isinstance(value,list):
        if len(value)>=32 and valid_tokens(value):yield "tokens",value,where
        else:
            for i,v in enumerate(value):yield from json_leaves(v,where+"/"+str(i),depth+1)


def strict_json(text):
    def pairs(items):
        out={}
        for k,v in items:
            require(k not in out,"Duplicate historical JSON key","BLOCKED");out[k]=v
        return out
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite JSON constant")))


def history_json(text):
    """Read every historical value; numeric validity is not this data gate."""
    notes={"duplicate_keys":0,"nonfinite_numeric_constants":0}
    def pairs(items):
        notes["duplicate_keys"]+=len(items)-len({k for k,_ in items})
        return HistoryObject(items)
    def nonfinite(value):
        notes["nonfinite_numeric_constants"]+=1
        return None  # The original source bytes/pin retain the numeric spelling.
    return json.loads(text,object_pairs_hook=pairs,parse_constant=nonfinite),notes


def python_ast_leaves(tree,location=None):
    for node in ast.walk(tree):
        where=location or "line:"+str(node.lineno) if hasattr(node,"lineno") else location
        if isinstance(node,ast.Constant) and isinstance(node.value,str):yield "text",node.value,where
        elif isinstance(node,(ast.List,ast.Tuple)) and len(node.elts)>=32 and all(isinstance(n,ast.Constant) and type(n.value) is int and 0<=n.value<32768 for n in node.elts):yield "tokens",[n.value for n in node.elts],where


def python_leaves(text,name):
    """Keep valid AST behavior; conservatively recover malformed retained source.

    Never execute source or evaluate expressions. Every quote/bracket origin is
    considered independently, including origins after an unmatched triple quote.
    Whole raw source remains a text witness; this is not program reconstruction.
    """
    try:tree=ast.parse(text,filename=name)
    except (SyntaxError,ValueError) as syntax:
        note={k:0 for k in PYTHON_RECOVERY_KEYS};note.update(files=1,raw_utf8_bytes=len(text.encode("utf-8")),
            raw_source_covered=True,semantic_reconstruction=False,
            syntax_error={"type":type(syntax).__name__,"line":getattr(syntax,"lineno",None),"offset":getattr(syntax,"offset",None),"message":getattr(syntax,"msg",str(syntax))})
        yield "text",text,"python_raw_source"
        origins=set();work=0;decoded={}
        for q,c in enumerate(text):
            if c not in "\"'":continue
            origins.add((q,q))
            for length in (1,2):
                start=q-length
                if start>=0 and text[start:q].casefold() in {"r","u","b","f","br","rb","fr","rf"} and (start==0 or not (text[start-1].isalnum() or text[start-1]=="_")):origins.add((start,q))
        for start,q in sorted(origins):
            quote=text[q];delimiter=quote*3 if text.startswith(quote*3,q) else quote
            at=q+len(delimiter);end=None
            while at<len(text):
                work+=1;require(work<=PYTHON_RECOVERY_CHAR_BUDGET,"Malformed Python lexical recovery resource bound","BLOCKED")
                if text[at]=="\\":at+=2;continue
                if len(delimiter)==1 and text[at] in "\r\n":break
                if text.startswith(delimiter,at):end=at+len(delimiter);break
                at+=1
            if end is None:note["rejected_origins"]+=1;continue
            fragment=text[start:end]
            try:subtree=ast.parse(fragment,mode="eval")
            except (SyntaxError,ValueError):note["rejected_origins"]+=1;continue
            leaves=list(python_ast_leaves(subtree,"python_literal:"+str(start)+":"+str(end)))
            for typ,value,where in leaves:
                note["string_fragments" if typ=="text" else "token_arrays"]+=1
                yield typ,value,where
            if isinstance(subtree.body,ast.Constant) and isinstance(subtree.body.value,str):decoded[start]=(end,subtree.body.value)
        # Preserve implicit adjacent literal concatenations, including comments
        # and line breaks. This can over-exclude; no expression is executed.
        for start,(end,value) in sorted(decoded.items()):
            parts=[value];cursor=end;seen={start}
            while True:
                at=cursor
                while at<len(text):
                    if text[at].isspace():at+=1;continue
                    if text[at]=="#":
                        newline=text.find("\n",at);at=len(text) if newline<0 else newline+1;continue
                    break
                work+=max(1,at-cursor)
                require(work<=PYTHON_RECOVERY_CHAR_BUDGET,"Malformed Python adjacent recovery resource bound","BLOCKED")
                if at not in decoded or at in seen:break
                seen.add(at);cursor,next_value=decoded[at];parts.append(next_value)
                work+=cursor-at
                require(work<=PYTHON_RECOVERY_CHAR_BUDGET,"Malformed Python adjacent recovery resource bound","BLOCKED")
            if len(parts)>1:
                work+=sum(map(len,parts))
                require(work<=PYTHON_RECOVERY_CHAR_BUDGET,"Malformed Python adjacent recovery resource bound","BLOCKED")
                note["adjacent_string_groups"]+=1
                yield "text","".join(parts),"python_adjacent:"+str(start)+":"+str(cursor)
        for start,c in enumerate(text):
            if c not in "[(":continue
            end=text.find("]" if c=="[" else ")",start+1)
            work+=(len(text)-start if end<0 else end-start+1)
            require(work<=PYTHON_RECOVERY_CHAR_BUDGET,"Malformed Python lexical recovery resource bound","BLOCKED")
            if end<0:continue
            try:value=ast.literal_eval(text[start:end+1])
            except (SyntaxError,ValueError,TypeError):continue
            if isinstance(value,tuple):value=list(value)
            if isinstance(value,list) and len(value)>=32 and valid_tokens(value):
                note["token_arrays"]+=1;yield "tokens",value,"python_tokens:"+str(start)+":"+str(end+1)
        yield "python_recovery",note,"python_recovery_summary"
    else:yield from python_ast_leaves(tree)


def detect_container(data):
    if data.startswith(b"PK\x03\x04"):return "zip"
    if data.startswith(b"\x1f\x8b"):return "gzip"
    if data.startswith(b"\xfd7zXZ\0"):return "xz"
    if len(data)>=262 and data[257:262]==b"ustar":return "tar"
    if data.lstrip().startswith((b"{",b"[")):return "json"
    return None


def byte_leaves(data,kind,name,arrow_reader=None,depth=0,member_policy=None):
    require(depth<=4 and len(data)<=MAX_EXPANDED_FILE_BYTES,"Historical container expansion bound","BLOCKED")
    member_policy=member_policy or {}
    policy=member_policy.get(name)
    if policy is not None:
        require({"bytes":len(data),"sha256":sha(data)}=={k:policy[k] for k in ("bytes","sha256")},"Frozen archive member pin: "+name)
        require(bool(policy.get("reason")),"Frozen archive member classification reason")
        if policy["kind"]=="nontext":
            yield "nontext",{"bytes":len(data),"sha256":sha(data),"reason":policy["reason"]},name;return
        kind=policy["kind"]
    if kind in ("json","jsonl","text","python","csv","tsv","xml"):
        text=data.decode("utf-8-sig",errors="strict")
        if kind=="json":
            value,notes=history_json(text)
            if any(notes.values()):yield "format_note",notes,"$"
            yield from json_leaves(value)
        elif kind=="jsonl":
            for i,line in enumerate(text.splitlines()):
                if line.strip():
                    value,notes=history_json(line);where="line:"+str(i+1)
                    if any(notes.values()):yield "format_note",notes,where
                    yield from json_leaves(value,where)
        elif kind=="python":
            yield from python_leaves(text,name)
        elif kind in ("csv","tsv"):
            for i,row in enumerate(csv.reader(io.StringIO(text),delimiter="," if kind=="csv" else "\t")):
                for j,value in enumerate(row):yield "text",value,f"row:{i}/column:{j}"
        elif kind=="xml":
            require("<!DOCTYPE" not in text.upper() and "<!ENTITY" not in text.upper(),"Historical XML entities not supported","BLOCKED")
            for i,value in enumerate(ET.fromstring(text).itertext()):yield "text",value,"textnode:"+str(i)
        else:yield "text",text,"whole_file"
    elif kind in ("parquet","arrow","npy"):
        require(arrow_reader is not None,"Historical columnar reader unavailable","BLOCKED")
        for i,row in enumerate(arrow_reader(data,kind)):yield from json_leaves(row,"row:"+str(i))
    elif kind in ("gzip","xz"):
        reader=gzip.GzipFile(fileobj=io.BytesIO(data),mode="rb") if kind=="gzip" else lzma.LZMAFile(io.BytesIO(data),mode="rb")
        with reader as f:
            expanded=f.read(MAX_EXPANDED_FILE_BYTES+1)
        subname=name[:-3] if name.endswith((".gz",".xz")) else name+"!decoded"
        subkind=classify_name(subname) or detect_container(expanded)
        require(subkind in TEXT_KINDS,"Unknown historical gzip member format","BLOCKED")
        yield from byte_leaves(expanded,subkind,subname,arrow_reader,depth+1,member_policy)
    elif kind=="base64":
        decoded=base64.b64decode(b"".join(data.split()),validate=True)
        subkind=detect_container(decoded)
        require(subkind in TEXT_KINDS,"Unknown historical base64 payload format","BLOCKED")
        yield from byte_leaves(decoded,subkind,name+"!base64",arrow_reader,depth+1,member_policy)
    elif kind=="zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names=set();expanded=0
            for item in z.infolist():
                require(item.filename not in names,"Duplicate historical archive member","BLOCKED");names.add(item.filename)
                if item.is_dir():continue
                expanded+=item.file_size;require(expanded<=MAX_EXPANDED_FILE_BYTES,"Historical archive expansion bound","BLOCKED")
                member_name=name+"!"+item.filename
                subkind=member_policy.get(member_name,{}).get("kind",classify_name(item.filename))
                require(subkind in TEXT_KINDS or subkind=="nontext","Unknown historical archive member format: "+member_name,"BLOCKED")
                for typ,value,where in byte_leaves(z.read(item),subkind,member_name,arrow_reader,depth+1,member_policy):yield typ,value,item.filename+"/"+where
    elif kind=="tar":
        with tarfile.open(fileobj=io.BytesIO(data),mode="r:") as archive:
            names=set();expanded=0
            for item in archive:
                require(item.name not in names,"Duplicate historical tar member","BLOCKED");names.add(item.name)
                if item.isdir():continue
                require(item.isfile(),"Historical tar special member unsupported","BLOCKED")
                expanded+=item.size;require(expanded<=MAX_EXPANDED_FILE_BYTES,"Historical tar expansion bound","BLOCKED")
                member_name=name+"!"+item.name;subkind=member_policy.get(member_name,{}).get("kind",classify_name(item.name))
                require(subkind in TEXT_KINDS or subkind=="nontext","Unknown historical tar member format: "+member_name,"BLOCKED")
                stream=archive.extractfile(item);require(stream is not None,"Unreadable historical tar member","BLOCKED")
                for typ,value,where in byte_leaves(stream.read(MAX_EXPANDED_FILE_BYTES+1),subkind,member_name,arrow_reader,depth+1,member_policy):yield typ,value,item.name+"/"+where
    else:raise Stop("BLOCKED","Unknown potential historical input format: "+kind)


def classify_name(name):
    suffix=Path(name).suffix.casefold()
    return {".json":"json",".jsonl":"jsonl",".ndjson":"jsonl",".txt":"text",".md":"text",".rst":"text",".log":"text",".stdout":"text",".stderr":"text",".out":"text",".err":"text",".lock":"text",".sha256":"text",".yaml":"text",".yml":"text",".toml":"text",".csv":"csv",".tsv":"tsv",".xml":"xml",".py":"python",".parquet":"parquet",".arrow":"arrow",".npy":"npy",".zip":"zip",".tar":"tar",".gz":"gzip",".xz":"xz",".b64":"base64",".base64":"base64"}.get(suffix)


def policy_value(spec,key,default):
    if key+"_path" not in spec:return spec.get(key,default)
    require(key not in spec,"Policy may not have both inline and path forms")
    p=Path(spec[key+"_path"]);require(p.is_absolute() and p.is_file() and not p.is_symlink(),"Policy path required","BLOCKED")
    require(pin(p)==spec[key+"_pin"],"Frozen policy file pin: "+key)
    data=p.read_bytes()
    if p.suffix==".gz":
        with gzip.GzipFile(fileobj=io.BytesIO(data),mode="rb") as f:data=f.read(POLICY_MAX_BYTES+1)
        require(len(data)<=POLICY_MAX_BYTES,"Policy decompression bound","BLOCKED")
    value=strict_json(data.decode("utf-8"))
    return value


def policy_mapping(spec,key):
    value=policy_value(spec,key,{})
    require(isinstance(value,dict),"Policy mapping schema: "+key)
    return value


def verify_inventory(spec):
    entries=spec.get("history_entries")
    explicit_entries=entries is not None
    if entries is not None:
        require(isinstance(entries,list) and entries,"Nonempty frozen history inventory")
        require(len({e["path"] for e in entries})==len(entries),"Duplicate historical physical path")
    observed=set();excluded=[]
    exclusions=spec.get("excluded_roots",[])
    for e in exclusions:require(set(e)=={"path","reason"} and Path(e["path"]).is_absolute() and bool(e["reason"]),"Explicit history exclusion schema")
    for root_name in spec["history_roots"]:
        root=Path(root_name);require(root.is_absolute() and root.is_dir() and not root.is_symlink(),"Historical root unavailable: "+root_name,"BLOCKED")
        for current,dirs,files in os.walk(root,followlinks=False):
            parent=Path(current)
            keep=[]
            for name in dirs:
                child=parent/name
                if name in (".git","__pycache__"):continue
                hit=next((e for e in exclusions if child==Path(e["path"])),None)
                if hit:excluded.append(hit);continue
                require(not child.is_symlink(),"Unregistered historical directory symlink: "+str(child),"BLOCKED");keep.append(name)
            dirs[:]=keep
            for name in files:
                p=parent/name;require(not p.is_symlink(),"Historical file symlink: "+str(p),"BLOCKED");observed.add(str(p))
    explicit=policy_value(spec,"extra_history_files",[])
    require(isinstance(explicit,list),"Extra historical file list schema")
    require(all(Path(p).is_absolute() for p in explicit),"Absolute extra historical file paths")
    observed.update(explicit)
    old=policy_mapping(spec,"extra_history_inventory")
    require(all(Path(p).is_absolute() and set(v)=={"bytes","sha256"} and type(v["bytes"]) is int and v["bytes"]>=0 and re.fullmatch("[0-9a-f]{64}",v["sha256"]) for p,v in old.items()),"Prior history inventory schema")
    observed.update(old)
    if "expected_history_file_count" in spec:
        require(len(observed)==spec["expected_history_file_count"],"Historical file count changed since approved discovery","BLOCKED")
    if "expected_history_suffixes" in spec:
        require(dict(Counter(Path(p).suffix.casefold() for p in observed))==spec["expected_history_suffixes"],"Historical suffix counts changed since approved discovery","BLOCKED")
    if entries is None:
        require(spec.get("discover_before_acquisition") is True,"Explicit historical enumeration mode required")
        overrides=policy_mapping(spec,"nontext_entries")
        formats=policy_mapping(spec,"format_entries")
        require(not set(overrides)&set(formats),"Conflicting historical classifications")
        require(set(overrides).issubset(observed),"Registered nontext path absent","BLOCKED")
        require(set(formats).issubset(observed),"Registered format path absent","BLOCKED")
        entries=[]
        for path in sorted(observed):
            p=Path(path);kind=classify_name(path);actual=pin(p)
            if path in old:require(actual==old[path],"Prior protected history changed: "+path)
            entry={"path":path,**actual,"kind":kind}
            if path in overrides:
                override=overrides[path]
                require(actual=={k:override[k] for k in ("bytes","sha256")} and bool(override.get("reason")),"Registered nontext pin/reason: "+path)
                entry.update(kind="nontext",reason=override["reason"])
            if path in formats:
                override=formats[path]
                require(actual=={k:override[k] for k in ("bytes","sha256")} and bool(override.get("reason")),"Registered format pin/reason: "+path)
                require(override["kind"] in TEXT_KINDS,"Registered text/container kind")
                entry.update(kind=override["kind"],reason=override["reason"])
            require(entry["kind"] is not None,"Unclassified potential old input: "+path,"BLOCKED");entries.append(entry)
    else:require(observed=={e["path"] for e in entries},"Frozen history enumeration changed","BLOCKED")
    for e in entries:
        p=Path(e["path"]);require(p.is_absolute() and p.is_file() and not p.is_symlink(),"Historical file missing: "+str(p),"BLOCKED")
        # Discovery mode already hashed and checked these exact bytes above.
        if explicit_entries:require(pin(p)=={k:e[k] for k in ("bytes","sha256")},"Historical source pin changed: "+str(p))
        if str(p) in old:require({k:e[k] for k in ("bytes","sha256")}==old[str(p)],"Prior inventory pin retained: "+str(p))
        require(e["kind"] in TEXT_KINDS or (e["kind"]=="nontext" and bool(e.get("reason"))),"Unclassified historical input: "+str(p),"BLOCKED")
    return entries


def scan_history(entries,index,tokenize,arrow_reader=None,ledger=None,member_policy=None):
    ledger=[] if ledger is None else ledger;seen={}
    for position,e in enumerate(entries):
        if position%500==0:print(json.dumps({"phase":"history_scan","files_completed":position,"files_total":len(entries),"string_leaves":index.string_count,"text_fingerprints":index.text_fingerprints,"text_cache_hits":index.text_cache_hits}),flush=True)
        row={**e,"Status":"NOT TESTED","strings":0,"token_arrays":0}
        ledger.append(row)
        if e["kind"]=="nontext":row.update(Status="EXCLUDED_REGISTERED_NONTEXT");continue
        key=e["sha256"],e["bytes"],e["kind"]
        if key in seen:row.update(Status="PASS_IDENTICAL_PAYLOAD",identical_to=seen[key]);continue
        old_s,old_t=index.string_count,index.token_array_count
        try:
            for typ,value,where in byte_leaves(Path(e["path"]).read_bytes(),e["kind"],e["path"],arrow_reader,member_policy=member_policy):
                source={"path":e["path"],"location":where,"sha256":e["sha256"]}
                if typ=="text":index.text(value,source,tokenize)
                elif typ=="tokens":index.tokens(value,source)
                elif typ=="nontext":row.setdefault("classified_nontext_members",[]).append({"location":where,**value})
                elif typ=="format_note":
                    row.setdefault("format_notes",[]).append({"location":where,**value})
                    for k,v in value.items():index.format_notes[k]+=v
                elif typ=="python_recovery":
                    row.setdefault("python_recovery",[]).append({"location":where,**value})
                    for k in PYTHON_RECOVERY_KEYS:index.python_recovery[k]+=value[k]
                else:raise Stop("FAIL","Unknown historical leaf kind: "+typ)
            row.update(Status="PASS",strings=index.string_count-old_s,token_arrays=index.token_array_count-old_t);seen[key]=e["path"]
        except BaseException as exc:
            row.update(Status=getattr(exc,"status","BLOCKED"),error=repr(exc))
            raise Stop(row["Status"],"Historical parse failed: "+e["path"]+": "+repr(exc)) from exc
    return ledger


def select(candidates,ledger,index,per_class=PER_CLASS):
    by_id={r["id"]:r for r in ledger};selected=[]
    for label in range(4):
        count=0
        for c in sorted((c for c in candidates if c["label"]==label),key=lambda c:c["id"]):
            record=by_id[c["id"]]
            if c["id"] in index.matches:record.update(decision="EXCLUDE_HISTORY",witness=index.matches[c["id"]]);continue
            duplicate=None
            for other in selected:
                why=overlaps(c["fingerprint"],other["fingerprint"])
                if why:duplicate={"selected_id":other["id"],"reasons":why};break
            if duplicate:record.update(decision="EXCLUDE_NEW_DUPLICATE",witness=duplicate);continue
            if count>=per_class:record["decision"]="ELIGIBLE_NOT_SELECTED";continue
            record["decision"]="SELECTED";selected.append(c);count+=1
        require(count==per_class,"Insufficient fixed-class eligible novel records: "+str(label),"BLOCKED")
    require(len(selected)==4*per_class and len({c["id"] for c in selected})==len(selected),"Exact selected coverage")
    return sorted(selected,key=lambda c:(c["label"],c["id"]))


def selected_payload(selected):
    samples=[]
    for i,c in enumerate(selected):
        ids=c["fingerprint"]["ids"][:129]
        samples.append({"id":c["id"],"index":i,"row":c["row"],"label":c["label"],"text":c["text"],"text_sha256":c["text_sha256"],
                        "full_row_token_count":len(c["fingerprint"]["ids"]),"tokens":ids,"window_sha256":digest_tokens(ids),
                        "input_sha256":digest_tokens(ids[:128]),"scored_targets_sha256":digest_tokens(ids[65:129])})
    return {"eval":samples,"context_tokens":128,"scored_positions":[64,128],"scored_target_offsets":[65,129],
            "eval_seeds":[5101,5202],"train_seeds":[4101,4202],"optimizer_steps":0,
            "provenance":{"dataset":DATASET,"revision":REVISION,"split":"test","corpus":CORPUS_PIN,
            "role":"Project-new news-domain test under explicit historical exclusion policy; base pretraining overlap unknown","license":"unknown; original source describes research/noncommercial use; no raw text exported to Git"}}


class BudgetWriter:
    def __init__(self,out,shared_paths=()):self.out=Path(out);self.shared_paths=tuple(Path(p) for p in shared_paths)
    def used(self):
        paths={p.resolve() for root in (self.out,*self.shared_paths) for p in root.rglob("*") if p.is_file()}
        return sum(p.stat().st_size for p in paths)
    def write(self,name,data):
        dest=self.out/name;require(dest.resolve().is_relative_to(self.out.resolve()),"Output confinement")
        used=self.used()
        require(used+len(data)<=PREP_BUDGET-SEAL_ALLOWANCE,"4MiB preparation allocation (including64KiB seal) exceeded","BLOCKED")
        require(shutil.disk_usage(self.out).free>=len(data)+SEAL_ALLOWANCE+DISK_RESERVE,"256MiB disk reserve plus64KiB seal unavailable","BLOCKED")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as stream:stream.write(data)
        require(dest.read_bytes()==data,"Output exact readback")
        return {"bytes":len(data),"sha256":sha(data)}
    def json(self,name,value):return self.write(name,canonical(value))
    def compressed(self,name,value):
        raw=canonical(value);out=io.BytesIO()
        with gzip.GzipFile(fileobj=out,mode="wb",filename="",mtime=0,compresslevel=9) as f:f.write(raw)
        data=out.getvalue();require(gzip.decompress(data)==raw,"Compressed ledger exact roundtrip")
        return {"physical":self.write(name,data),"canonical":{"bytes":len(raw),"sha256":sha(raw)}}


def acquire(writer):
    request=urllib.request.Request(URL,headers={"User-Agent":"OpenMythos-frozen-data-acquisition"})
    receipt={"url":URL,"expected":CORPUS_PIN,"Status":"NOT TESTED"};data=bytearray();error=None
    try:
        try:response=urllib.request.urlopen(request,timeout=60)
        except urllib.error.HTTPError as exc:response=exc
        with response:
            receipt.update(final_url=response.url,http_status=response.status,content_length=response.headers.get("Content-Length"))
            while len(data)<=CORPUS_PIN["bytes"]:
                chunk=response.read(min(65536,CORPUS_PIN["bytes"]+1-len(data)))
                if not chunk:break
                data.extend(chunk)
    except BaseException as exc:error=exc;receipt["error"]={"type":type(exc).__name__,"message":str(exc)}
    data=bytes(data);actual={"bytes":len(data),"sha256":sha(data)};receipt["actual_response"]=actual
    receipt["response_body_limit_bytes"]=CORPUS_PIN["bytes"]+1
    okay=error is None and receipt.get("http_status")==200 and actual==CORPUS_PIN
    receipt["Status"]="PASS" if okay else ("FAIL" if error is None and receipt.get("http_status")==200 else "BLOCKED")
    raw_name="corpus.parquet" if okay else "failed_acquisition_response.bin"
    try:receipt["pin"]=writer.write(raw_name,data);receipt["response_file"]=raw_name
    except BaseException as exc:receipt["storage_error"]=repr(exc);receipt["Status"]="BLOCKED"
    writer.json("acquisition.json",receipt)
    if receipt["Status"]!="PASS":raise Stop(receipt["Status"],"Source acquisition failed; observed response evidence saved: "+json.dumps({"http_status":receipt.get("http_status"),"actual_response":actual,"error":receipt.get("error"),"storage_error":receipt.get("storage_error")}))
    return data,receipt


def retained_source(writer,source_file):
    source=Path(source_file);original=source.parent/"acquisition.json"
    require(source.is_absolute() and str(source)==RETAINED_CORPUS,"Exact retained preparation-v2 corpus path required","BLOCKED")
    require(source.is_file() and original.is_file() and not any(p.is_symlink() for p in (source,original,*source.parents)),"Retained source/provenance regular paths required","BLOCKED")
    before={str(source):pin(source),str(original):pin(original)}
    require(before[str(source)]==CORPUS_PIN,"Retained source exact bytes")
    require(before[str(original)]["bytes"]<=65536,"Original acquisition receipt bounded","BLOCKED")
    old=strict_json(original.read_text(encoding="utf-8"))
    require(old.get("Status")=="PASS" and old.get("url")==URL and old.get("http_status")==200 and old.get("actual_response")==CORPUS_PIN and old.get("pin")==CORPUS_PIN and old.get("response_file")=="corpus.parquet","Original successful pinned acquisition provenance")
    with source.open("rb") as stream:data=stream.read(CORPUS_PIN["bytes"]+1)
    require({"bytes":len(data),"sha256":sha(data)}==CORPUS_PIN,"Retained source readback bytes")
    for path,expected in before.items():require(pin(path)==expected,"Retained source/provenance changed during read")
    common={"mode":"LOCAL_PINNED_REUSE","Status":"PASS","source_file":str(source),"source_pin":CORPUS_PIN,
            "original_acquisition_file":str(original),"original_acquisition_pin":before[str(original)],"network_requests":0,"copied_corpus_bytes":0}
    reference={"schema":"mythos-local-corpus-reference-v1",**common}
    reference_pin=writer.json("source_reference.json",reference)
    acquisition={**common,"url":URL,"expected":CORPUS_PIN,"source_reference_pin":reference_pin}
    writer.json("acquisition.json",acquisition)
    return data,acquisition,before


class ParseOnlyIndex(ExclusionIndex):
    """Validate complete parsing without loading/calling an original tokenizer."""
    def __init__(self):super().__init__([])
    def text(self,text,source,tokenize):
        require(isinstance(text,str),"Historical preflight text schema")
        text.encode("utf-8");self.string_count+=1
    def tokens(self,ids,source):
        require(valid_tokens(ids),"Historical preflight token-array schema")
        self.token_array_count+=1


def preflight_projection(ledger):
    required=("path","bytes","sha256","kind","Status");optional=("reason","identical_to")
    rows=[{**{k:row[k] for k in required},**{k:row[k] for k in optional if k in row}} for row in ledger]
    raw=canonical(rows)
    return {"schema":"mythos-history-format-projection-v1","records":len(rows),"canonical":{"bytes":len(raw),"sha256":sha(raw)}}


def main():
    p=argparse.ArgumentParser();p.add_argument("--spec",type=Path,required=True);p.add_argument("--expected-spec-sha",required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--source-file",type=Path);p.add_argument("--history-preflight-only",action="store_true");args=p.parse_args()
    require(not (args.source_file and args.history_preflight_only),"Preflight never reads a source corpus","BLOCKED")
    require(args.out.is_absolute() and not args.out.exists(),"New absolute preparation output required","BLOCKED")
    args.out.mkdir(parents=True,exist_ok=False)
    shared=(args.out.parent/"history-preflight",) if args.source_file else ()
    writer=BudgetWriter(args.out,shared_paths=shared)
    report={"Purpose":"Freeze project-new AGNews text without model scores, with exhaustive registered historical exclusion",
            "Environment":{"python":sys.version,"executable":sys.executable},"Input":{"spec":str(args.spec),"spec_sha256":args.expected_spec_sha,"source":URL},
            "Expected":{"records":20,"per_class":5,"tokens":129,"training_steps":0,"model_imports":[]},"Actual":{},"Status":"NOT TESTED"}
    report["Input"].update(history_preflight_only=args.history_preflight_only,source_file=str(args.source_file) if args.source_file else None)
    if args.history_preflight_only:
        report["Purpose"]="Complete frozen historical format/parser preflight without source acquisition, tokenization or model";report["Expected"]={"historical_files":32244,"parse_completed":True,"tokenizer_calls":0,"new_source_acquisitions":0,"model_calls":0}
        report["Actual"]={"historical_files":0,"historical_files_completed":0,"parse_completed":False,"model_calls":0,"tokenizer_calls":0,"new_source_acquisitions":0}
    entries=[];ledger=[];history_ledger=[];index=None;before={};artifacts={}
    def interrupted(signum,frame):
        report["interruption"]={"signal":signum,"scope":"Stop requested; no acquisition/model retry"}
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        raise Stop("BLOCKED","Preparation interrupted by signal "+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        require(os.environ.get("CODESPACE_NAME")==SPACE and platform.system()=="Linux" and platform.python_version()=="3.12.3" and sys.executable==PYTHON and sys.flags.isolated and sys.dont_write_bytecode,"Designated isolated data environment","BLOCKED")
        require(pin(args.spec)["sha256"]==args.expected_spec_sha,"Frozen history spec SHA")
        spec=strict_json(args.spec.read_text(encoding="utf-8"));require(spec["schema"]=="mythos-fresh-history-v1","History spec schema")
        if args.source_file:require(shared[0].is_dir() and (shared[0]/"manifest.json").is_file(),"Completed sibling history preflight required","BLOCKED")
        require(shutil.disk_usage(args.out).free>=max(0,PREP_BUDGET-writer.used())+DISK_RESERVE,"Remaining combined4MiB preparation plus256MiB reserve unavailable","BLOCKED")
        entries=verify_inventory(spec);before={e["path"]:{k:e[k] for k in ("bytes","sha256")} for e in entries}
        before[str(args.spec)]=pin(args.spec)
        for name in ("nontext_entries","format_entries","member_entries","extra_history_files","extra_history_inventory"):
            if name+"_path" in spec:before[spec[name+"_path"]]=spec[name+"_pin"]
        tokenizer_path=Path(spec["tokenizer_path"]);require(pin(tokenizer_path)["sha256"]==TOKENIZER_SHA,"Original tokenizer SHA")
        before[str(tokenizer_path)]=pin(tokenizer_path)
        versions={n:importlib.metadata.version(n) for n in ("pyarrow","numpy","tokenizers")}
        require(versions=={"pyarrow":"19.0.1","numpy":"1.26.4","tokenizers":"0.23.2"},"Existing data dependency versions","BLOCKED");report["Environment"]["packages"]=versions
        import pyarrow as pa
        import pyarrow.parquet as pq
        import numpy as np
        def arrow_reader(data,kind):
            if kind=="npy":
                array=np.load(io.BytesIO(data),allow_pickle=False)
                require(array.dtype.kind in "biufUS","Unsupported historical NPY dtype","BLOCKED")
                return [{"array":array.tolist(),"dtype":str(array.dtype)}]
            source=pa.BufferReader(data)
            if kind=="parquet":table=pq.read_table(source)
            else:
                try:table=pa.ipc.open_file(source).read_all()
                except pa.ArrowInvalid:source.seek(0);table=pa.ipc.open_stream(source).read_all()
            return table.to_pylist()
        if args.history_preflight_only:
            index=ParseOnlyIndex();scan_history(entries,index,None,arrow_reader,ledger=history_ledger,member_policy=policy_mapping(spec,"member_entries"))
            report["Actual"]={"historical_files":len(entries),"historical_files_completed":len(history_ledger),"parse_completed":True,"historical_strings":index.string_count,"historical_token_arrays":index.token_array_count,"historical_format_notes":index.format_notes,"historical_python_recovery":index.python_recovery,"model_calls":0,"tokenizer_calls":0,"new_source_acquisitions":0}
        else:
            from tokenizers import Tokenizer
            tokenizer=Tokenizer.from_file(str(tokenizer_path));tokenize=lambda s:tokenizer.encode(s,add_special_tokens=False).ids
            if args.source_file:
                corpus,acquisition,source_pins=retained_source(writer,args.source_file);before.update(source_pins)
                artifacts["source_reference.json"]=pin(args.out/"source_reference.json")
            else:
                corpus,acquisition=acquire(writer);artifacts["corpus.parquet"]=acquisition["pin"]
            artifacts["acquisition.json"]=pin(args.out/"acquisition.json")
            rows=arrow_reader(corpus,"parquet");candidates,ledger=collect_candidates(rows,tokenize)
            index=ExclusionIndex(candidates);scan_history(entries,index,tokenize,arrow_reader,ledger=history_ledger,member_policy=policy_mapping(spec,"member_entries"))
            chosen=select(candidates,ledger,index);payload=selected_payload(chosen)
            artifacts["inputs.json"]=writer.json("inputs.json",payload)
            public=[{k:v for k,v in row.items() if k not in ("text","tokens")} for row in payload["eval"]]
            artifacts["public/selection.json"]=writer.json("public/selection.json",{"samples":public,"input_pin":artifacts["inputs.json"],"labels":{i:sum(s["label"]==i for s in chosen) for i in range(4)}})
            report["Actual"]={"source_rows":len(rows),"prose_length_eligible":len(candidates),"historical_files":len(entries),"historical_strings":index.string_count,"historical_token_arrays":index.token_array_count,"historical_text_fingerprints":index.text_fingerprints,"historical_text_cache_hits":index.text_cache_hits,"historical_format_notes":index.format_notes,"historical_python_recovery":index.python_recovery,"excluded_by_history":len(index.matches),"selected":len(chosen),"input_pin":artifacts["inputs.json"],"model_calls":0,"new_source_acquisitions":0 if args.source_file else 1,"copied_corpus_bytes":0 if args.source_file else CORPUS_PIN["bytes"]}
        report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]=getattr(exc,"status","BLOCKED" if isinstance(exc,(OSError,MemoryError)) else "FAIL")
        report["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        forbidden=sorted(n for n in sys.modules if n.split(".")[0] in FORBIDDEN)
        report["forbidden_imports"]=forbidden
        if forbidden:report["Status"]="FAIL"
        try:
            if report.get("interruption"):report["source_after_status"]="NOT TESTED: interrupted; parent must verify custody after worker exit"
            else:
                for path,expected in before.items():require(pin(path)==expected,"Historical file changed during preparation: "+path)
                report["source_after_status"]="PASS"
            if args.history_preflight_only:
                report["Actual"].update(history_ledger_projection=preflight_projection(history_ledger),historical_files=len(entries),historical_files_completed=len(history_ledger),model_calls=0,tokenizer_calls=0,new_source_acquisitions=0)
                findings=[r for r in history_ledger if r.get("python_recovery") or r.get("format_notes") or r.get("error") or r["Status"] in ("FAIL","BLOCKED")]
                artifacts["preflight_findings.json.gz"]=writer.compressed("preflight_findings.json.gz",findings)
            else:
                artifacts["candidates.json.gz"]=writer.compressed("candidates.json.gz",ledger)
                artifacts["history_ledger.json.gz"]=writer.compressed("history_ledger.json.gz",history_ledger)
        except BaseException as exc:report["Status"]=getattr(exc,"status","FAIL");report["sealing_error"]=repr(exc)
        for path in args.out.rglob("*"):
            if path.is_file() and str(path.relative_to(args.out)) not in artifacts:artifacts[str(path.relative_to(args.out))]=pin(path)
        report["artifacts"]=artifacts;report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        # A bounded stop record remains mandatory even after an allocation gate.
        encoded=canonical(report);require(len(encoded)<=65536,"Preparation report unexpectedly exceeds64KiB")
        with (args.out/"manifest.json").open("xb") as stream:stream.write(encoded)
    print(json.dumps({"Status":report["Status"],"Actual":report["Actual"],"error":report.get("error"),"sealing_error":report.get("sealing_error")},allow_nan=False))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
