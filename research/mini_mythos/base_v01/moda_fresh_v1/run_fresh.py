"""Frozen-weight fresh-text validation. No training, optimizer, or dependency changes."""
from __future__ import annotations
import argparse
import datetime
import gc
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import struct
import subprocess
import sys
import time
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
DATA_PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
OLD_HEAD = "bc6d267cdd8cf9306c1bf08b369cf2b791723d3d"
OLD_FREEZE = "301cb192e8a32768146c9bb9131699ee9aad4da2"
UPSTREAM = "69284c13746e849104f738d6d1a347b1f457df76"
LIBRARY_SHA = "a52005f273e2ec8f467375e9ee506ae7d622cc97e0570c92863b5087014b3912"
SOURCE_SHA = "335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492"
WEIGHTS = "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"
CONFIG = "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"
OLD_INPUT_SHA = "b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc"
ARMS = (("fixed32", None), ("shared", 4101), ("depth", 4101), ("shared", 4202), ("depth", 4202))
EVAL_SEEDS = (5101, 5202)
RAW_BYTES = 64 * 32768 * 4
RAW_BUDGET, META_BUDGET, RESERVE = RAW_BYTES, 12 * 1024**2, 256 * 1024**2
ENV = {"OMP_NUM_THREADS":"2", "MKL_NUM_THREADS":"2", "OPENBLAS_NUM_THREADS":"1",
       "RAYON_NUM_THREADS":"1", "TOKENIZERS_PARALLELISM":"false", "CUDA_VISIBLE_DEVICES":"",
       "PYTHONDONTWRITEBYTECODE":"1", "HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1"}
STABLE = ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "seed")
EXPECTED = dict(model_loads=1, calls_started=405, calls_completed=405, bridge_calls=5,
                quality_rows=200, repeat_rows=200, train_steps=0, backward_calls=0, optimizer_steps=0)


class Stop(Exception):
    def __init__(self, status, message):
        super().__init__(message); self.status = status


def require(okay, reason, status="FAIL"):
    if not okay: raise Stop(status, reason)


def sha(data): return hashlib.sha256(data).hexdigest()
def peak_rss_bytes():
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024
def pin(path):
    h,n=hashlib.sha256(),0
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block);n+=len(block)
    return dict(bytes=n,sha256=h.hexdigest())


def read(path):
    path=Path(path)
    raw=path.read_bytes()
    if path.suffix==".gz":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: raw=stream.read(32*1024**2+1)
        require(len(raw)<=32*1024**2,"Expanded JSON bound")
    return json.loads(raw)


def encoded(value, zipped=False):
    raw=(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
    return gzip.compress(raw,compresslevel=9,mtime=0) if zipped else raw


class CheckLog:
    """Lossless append-only gzip JSONL; flush every complete check before progress."""
    def __init__(self,path):
        self.path=Path(path);self.raw=self.path.open("xb")
        self.stream=gzip.GzipFile(filename="",mode="wb",fileobj=self.raw,compresslevel=9,mtime=0)
    def write(self,line):
        self.stream.write(line);self.stream.flush();self.raw.flush()
    def close(self):
        self.stream.close();self.raw.close()


def read_checks(path):
    with gzip.open(path,"rb") as stream:raw=stream.read(32*1024**2+1)
    require(len(raw)<=32*1024**2,"Expanded check log bound")
    return [json.loads(line) for line in raw.splitlines()]


def budget_snapshot(root):
    raw=meta=0
    for path in Path(root).rglob("*"):
        if path.is_file():
            if path.name in ("final_sentinel.bin","failed_logits.bin"):
                raw+=path.stat().st_size
            else:meta+=path.stat().st_size
    return dict(raw=raw,metadata=meta,free=shutil.disk_usage(root).free)


def guard(root, path, additional=0, salvage=False):
    root,path=Path(root).resolve(),Path(path)
    require(path.is_absolute() and path.resolve().is_relative_to(root),"Confined current-run write")
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),"No output symlink")
    b=budget_snapshot(root); israw=path.name in ("final_sentinel.bin","failed_logits.bin")
    require(b["raw"]+(additional if israw else 0)<=RAW_BUDGET,"Single raw allocation","BLOCKED")
    require(b["metadata"]+(0 if israw else additional)<=META_BUDGET,"Metadata allocation","BLOCKED")
    need=additional if salvage else max(0,RAW_BUDGET-b["raw"])+max(0,META_BUDGET-b["metadata"])
    require(b["free"]>=RESERVE+need,"Remaining disk allocation and256MiB reserve","BLOCKED")
    return b


def save(path,value,root=None,salvage=False):
    path=Path(path);raw=encoded(value,path.suffix==".gz")
    if root is not None:guard(root,path,len(raw),salvage)
    with path.open("xb") as stream:stream.write(raw)
    return dict(bytes=len(raw),sha256=sha(raw))


def raw_save(path,raw,root,salvage=False):
    require(len(raw)==RAW_BYTES,"Full scored raw shape")
    guard(root,Path(path),len(raw),salvage)
    with Path(path).open("xb") as stream:stream.write(raw)
    require(pin(path)==dict(bytes=len(raw),sha256=sha(raw)),"Raw readback identity")


def validate_data(data):
    rows=data["eval"]
    require(len(rows)==20,"Exactly20 fresh articles")
    require(len({r["id"] for r in rows})==20,"Unique article IDs")
    for r in rows:
        require(type(r["id"])is str and len(r["id"])==64 and all(c in "0123456789abcdef" for c in r["id"]),"SHA256 article ID")
        require(len(r["tokens"])==129 and all(type(x) is int and 0<=x<32768 for x in r["tokens"]),"129 token IDs")
    require(data.get("context_tokens")==128 and data.get("scored_positions")==[64,128],"Frozen score layout")
    require(data.get("eval_seeds")==list(EVAL_SEEDS),"Frozen h0 seeds")
    return rows


def schedule():
    rows=[]
    for pass_index in range(2):
        for case in range(40):
            order=[(case+j)%5 for j in range(5)]
            if pass_index:order.reverse()
            for slot,arm_index in enumerate(order):
                arm,train_seed=ARMS[arm_index]
                rows.append(dict(call_index=len(rows),pass_index=pass_index,case=case,
                    article_index=case//2,eval_seed=EVAL_SEEDS[case%2],slot=slot,
                    arm_index=arm_index,arm=arm,train_seed=train_seed))
    return rows


def identity(row):return {k:row[k] for k in ("arm","train_seed","eval_seed","article_id","article_index")}
def rowkey(row):return (row["arm"],row["train_seed"],row["eval_seed"],row["article_id"])
def stable(observer):return {k:observer[k] for k in STABLE}
def name(arm,seed):return arm if seed is None else arm+"_"+str(seed)
def label(nll,accuracy):
    if nll<=-.01 and accuracy>=-.01:return "IMPROVEMENT"
    if nll>=.01 or accuracy<-.01:return "WORSE"
    return "NO_QUALIFIED_IMPROVEMENT"


def aggregate(rows,timings):
    require(len(rows)==200 and len({rowkey(r) for r in rows})==200,"200 unique scored rows")
    by={rowkey(r):r for r in rows};articles=sorted({r["article_id"] for r in rows})
    require(len(articles)==20,"20 scored articles")
    means={}
    for arm,seed in ARMS:
        group=[by[arm,seed,e,i] for i in articles for e in EVAL_SEEDS]
        means[name(arm,seed)]=dict(mean_nll=math.fsum(r["nll_mean"] for r in group)/40,
            correct=sum(r["correct"] for r in group),scored_observations=2560)
        means[name(arm,seed)]["accuracy"]=means[name(arm,seed)]["correct"]/2560
    comparisons={};screens={};interpretations={}
    for left,right in (("depth","fixed32"),("depth","shared"),("shared","fixed32")):
        title=left+"_vs_"+right;perseed={}
        for seed in (4101,4202):
            rseed=None if right=="fixed32" else seed;deltas=[]
            for article in articles:
                a=[by[left,seed,e,article] for e in EVAL_SEEDS];b=[by[right,rseed,e,article] for e in EVAL_SEEDS]
                deltas.append(dict(article_id=article,delta_nll=math.fsum(x["nll_mean"]-y["nll_mean"] for x,y in zip(a,b))/2,
                    delta_correct=sum(x["correct"]-y["correct"] for x,y in zip(a,b))))
            dn=math.fsum(r["delta_nll"] for r in deltas)/20;da=sum(r["delta_correct"] for r in deltas)/2560
            perseed[str(seed)]=label(dn,da)
            comparisons[title+"_"+str(seed)]=dict(delta_nll=dn,delta_accuracy=da,per_article=deltas,
                articles_improved=sum(r["delta_nll"]<0 for r in deltas),worst_article_delta_nll=max(r["delta_nll"] for r in deltas),
                screen=dn<=-.01 and da>=-.01,interpretation=perseed[str(seed)])
        screens[title]="PASS" if all(comparisons[title+"_"+str(s)]["screen"] for s in (4101,4202)) else "FAIL"
        interpretations[title]=dict(per_seed=perseed,combined=next(iter(set(perseed.values()))) if len(set(perseed.values()))==1 else "MIXED")
    require(len(timings)==400,"400 endpoint timings")
    timing={}
    for arm,seed in ARMS:
        x=[r for r in timings if (r["arm"],r["train_seed"])==(arm,seed)]
        require(len(x)==80,"80 timed calls per model")
        vals=sorted(r["endpoint_wall_ns"] for r in x)
        require(all(type(v) is int and v>0 for v in vals),"Positive monotonic endpoint timings")
        timing[name(arm,seed)]={"calls":80,"endpoint_total_seconds":sum(vals)/1e9,
            "endpoint_median_seconds":(vals[39]+vals[40])/2e9,"endpoint_p95_seconds":vals[math.ceil(.95*len(vals))-1]/1e9,
            "process_cpu_total_seconds":sum(r["endpoint_cpu_ns"] for r in x)/1e9,
            "per_pass_seconds":{str(p):sum(r["endpoint_wall_ns"] for r in x if r["pass_index"]==p)/1e9 for p in range(2)}}
    ratios={};per_pass_ratios={};per_article=[]
    for seed in (4101,4202):
        for ref in ("fixed32","shared_"+str(seed)):
            comparison="depth_"+str(seed)+"_vs_"+ref
            ratios[comparison]=timing["depth_"+str(seed)]["endpoint_total_seconds"]/timing[ref]["endpoint_total_seconds"]
            per_pass_ratios[comparison]={str(p):timing["depth_"+str(seed)]["per_pass_seconds"][str(p)]/timing[ref]["per_pass_seconds"][str(p)] for p in range(2)}
            refarm,refseed=("fixed32",None) if ref=="fixed32" else ("shared",seed)
            for article in articles:
                h=[r["endpoint_wall_ns"] for r in timings if r["article_id"]==article and (r["arm"],r["train_seed"])==("depth",seed)]
                c=[r["endpoint_wall_ns"] for r in timings if r["article_id"]==article and (r["arm"],r["train_seed"])==(refarm,refseed)]
                require(len(h)==len(c)==4,"Four h0/pass timing observations per article/arm")
                per_article.append(dict(comparison=comparison,article_id=article,history_mean_seconds=sum(h)/4e9,reference_mean_seconds=sum(c)/4e9,ratio=sum(h)/sum(c)))
    return dict(means=means,comparisons=comparisons,scientific_screens=screens,result_interpretations=interpretations,
        timing=dict(models=timing,ratios=ratios,per_pass_ratios=per_pass_ratios,paired_per_article=per_article,screen="NOT ASSESSED",scope="Pretokenized full instrumented CPU prediction endpoint; excludes raw serialization/audit/I/O; whole worker wall separately reported"))


def git(repo,*args):return subprocess.check_output(["git","-C",str(repo),*args],text=True,timeout=120).strip()
def module(path,module_name,expected):
    require(pin(path)["sha256"]==expected,"Frozen module bytes")
    spec=importlib.util.spec_from_file_location(module_name,path);m=importlib.util.module_from_spec(spec);sys.modules[module_name]=m;spec.loader.exec_module(m);return m
def normalize(raw):
    result={}
    for n,v in raw.items():
        for prefix in ("module.","_orig_mod.","model."):
            if n.startswith(prefix):n=n[len(prefix):]
        require(n not in result,"Normalized weight key collision");result[n]=v
    return result


def timed_endpoint(torch,runner,library,sample,eval_seed,banks,wall_clock=time.perf_counter_ns,cpu_clock=time.process_time_ns):
    """Complete pretokenized prediction call; no audit, raw hashing or disk I/O."""
    wall=wall_clock();cpu=cpu_clock()
    ids=torch.tensor([sample["tokens"][:128]],dtype=torch.long)
    targets=torch.tensor(sample["tokens"][1:],dtype=torch.long)
    logits,observer=runner.forward(ids,eval_seed,banks,training=False)
    metrics=library.score(logits,targets)
    cpu_ns=cpu_clock()-cpu;wall_ns=wall_clock()-wall
    return logits,observer,metrics,targets,wall_ns,cpu_ns


class Run:
    def __init__(self,spec,out):
        self.spec,self.out=spec,Path(out);self.root=Path(spec["run_root"]).resolve()
        require(self.out.resolve().is_relative_to(self.root),"Worker under current attempt")
        self.out.mkdir(exist_ok=False);self.public=self.out/"public";self.private=self.out/"private"
        self.public.mkdir();self.private.mkdir();(self.public/"rows").mkdir();(self.public/"row_audits").mkdir()
        self.log=CheckLog(self.public/"checks.jsonl.gz")
        self.actual={k:0 for k in EXPECTED};self.checks={"PASS":0,"FAIL":0,"BLOCKED":0}
        self.rows=[];self.timings=[];self.bridges=[];self.banks={};self.before={};self.adapter_before={};self.model=None;self.library=None
        self.last_raw=None;self.last_identity=None;self.sentinel=None;self.phase="initialization";self.salvage=False
        self.started=time.perf_counter();self.audit_seconds=0.;self.serialization_seconds=0.
    def check(self,purpose,okay,actual=None,status="FAIL"):
        state="PASS" if okay else status;self.checks[state]+=1
        row=dict(Purpose=purpose,Expected=True,Actual=actual,Status=state)
        line=encoded(row);guard(self.root,self.log.path,len(line)+32,self.salvage);self.log.write(line)
        if not okay:raise Stop(status,purpose)
    def save(self,name,value):return save(self.public/name,value,self.root,self.salvage)
    def call(self,runner,ids,seed,banks):
        self.check("405 call budget",self.actual["calls_started"]<405)
        guard(self.root,self.log.path)
        self.actual["calls_started"]+=1
        result=runner.forward(ids,seed,banks,training=False)
        self.actual["calls_completed"]+=1
        return result


def initialize(run):
    s=run.spec;t=time.perf_counter()
    run.check("Designated CPU runtime",os.environ.get("CODESPACE_NAME")==SPACE and platform.system()=="Linux" and platform.python_version()=="3.12.3"
        and sys.executable==PYTHON and sys.flags.isolated and sys.dont_write_bytecode,status="BLOCKED")
    run.check("Fresh execution source frozen",git(s["repo"],"rev-parse","HEAD")==s["freeze_commit"] and not git(s["repo"],"status","--porcelain"))
    run.check("Old accepted repository unchanged",git(s["old_repo"],"rev-parse","HEAD")==OLD_HEAD and not git(s["old_repo"],"status","--porcelain"))
    run.check("Pinned upstream unchanged",git(s["upstream"],"rev-parse","HEAD")==UPSTREAM and not git(s["upstream"],"status","--porcelain"))
    for path,expected in s["input_pins"].items():run.check("Input pin "+path,pin(path)==expected)
    run.check("Fresh data SHA",pin(s["data_path"])["sha256"]==s["data_sha256"])
    data=validate_data(read(s["data_path"]));modeldir=Path(s["model_dir"])
    run.check("Original weights/config pins",pin(modeldir/"pytorch_model.bin")["sha256"]==WEIGHTS and pin(modeldir/"config.json")["sha256"]==CONFIG)
    for k,v in ENV.items():os.environ[k]=v
    sys.path.insert(0,str(s["upstream"]))
    import torch
    torch.set_default_device("cpu");torch.set_default_dtype(torch.float32);torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True,warn_only=False)
    run.check("Frozen numerical runtime",str(torch.__version__)=="2.11.0+cpu" and not torch.cuda.is_available() and not torch.is_autocast_enabled("cpu") and not torch.is_autocast_enabled("cuda"),status="BLOCKED")
    run.save("environment.json",dict(python=sys.version,torch=str(torch.__version__),intra=torch.get_num_threads(),interop=torch.get_num_interop_threads(),deterministic=torch.are_deterministic_algorithms_enabled(),env={k:os.environ.get(k) for k in ENV}))
    library=module(Path(s["old_package"])/"moda_model.py","frozen_prior_moda_library",LIBRARY_SHA);run.library=library
    run.check("Original MoDA source",pin(s["moda_source"])["sha256"]==SOURCE_SHA)
    source=library.load_source(s["moda_source"])
    from receval.models.parcae import ModelingParcae
    from parcae_lm.attention_backends import flash_attention
    run.check("Native CPU attention backend",flash_attention._override_impl is None and not flash_attention.HAS_FA3)
    raw=normalize(torch.load(modeldir/"pytorch_model.bin",map_location="cpu",weights_only=True))
    run.model=model=ModelingParcae.from_pretrained(modeldir,device="cpu",dtype=None);run.actual["model_loads"]+=1
    model.eval();model.requires_grad_(False)
    run.check("Original architecture",type(model)is ModelingParcae and sum(p.numel() for p in model.parameters())==144323136 and len(list(model.parameters()))==61
        and len(model.state_dict())==63 and model.lm_head.weight is model.transformer.wte.weight and not model.gradient_checkpointing)
    run.check("Original state keyset",set(raw)==set(model.state_dict()))
    for n,x in model.state_dict().items():run.check("Original tensor exact "+n,x.dtype==raw[n].dtype and x.shape==raw[n].shape and library.raw(x)==library.raw(raw[n]) and x.device.type=="cpu" and library.finite(x))
    del raw;gc.collect();run.before=library.state_hashes(model);run.save("base_state_before.json",run.before)
    oldspec=read(s["old_spec_path"]);run.check("Old execution frozen",oldspec["freeze_commit"]==OLD_FREEZE and oldspec["inputs_sha256"]==OLD_INPUT_SHA)
    adapter_rows=read(s["old_adapter_rows_path"])["rows"]
    run.check("Four frozen adapters",[(r["arm"],r["train_seed"]) for r in adapter_rows]==list(ARMS[1:]))
    before={};load_times={}
    for row in adapter_rows:
        arm,seed=row["arm"],row["train_seed"];key=name(arm,seed);start=time.perf_counter()
        path=(Path(s["old_run"])/"worker"/row["path"]).resolve()
        run.check("Frozen adapter checkpoint "+key,path.is_relative_to(Path(s["old_run"]).resolve()) and pin(path)=={k:row[k] for k in ("bytes","sha256")})
        ck=torch.load(path,map_location="cpu",weights_only=True)
        run.check("Checkpoint metadata "+key,ck["arm"]==arm and ck["train_seed"]==seed and ck["steps"]==32 and ck["head_dim"]==16 and ck["rope_theta"]==10000.
            and ck["source_sha256"]==SOURCE_SHA and ck["freeze_commit"]==OLD_FREEZE and ck["inputs_sha256"]==OLD_INPUT_SHA)
        rng=library.digest(torch.get_rng_state());banks=library.MoDAResidual(arm,source,seed=seed)
        run.check("Feature construction preserves RNG "+key,library.digest(torch.get_rng_state())==rng)
        run.check("Original feature initialization "+key,banks.feature_hashes()==row["features_before"])
        banks.load_state_dict(ck["state_dict"],strict=True);banks.eval();banks.requires_grad_(False)
        run.check("Exact trained adapter state "+key,library.state_hashes(banks)==row["state"] and banks.feature_hashes()==row["features_after"])
        run.check("No trainable adapter/grad "+key,all(not p.requires_grad and p.grad is None for p in banks.parameters()))
        before[key]=library.state_hashes(banks);run.adapter_before[key]=before[key];run.banks[arm,seed]=banks;load_times[key]=time.perf_counter()-start;del ck
    run.adapter_before=before;run.save("adapters_before.json",before)
    run.check("Runtime settings survive all imports",torch.get_num_threads()==2 and torch.get_num_interop_threads()==1 and torch.are_deterministic_algorithms_enabled()
        and not torch.is_autocast_enabled("cpu") and not torch.is_autocast_enabled("cuda"))
    run.load_seconds=time.perf_counter()-t;run.adapter_load_seconds=load_times
    return torch,library,library.NativeFixed32(model),data


def bridges(run,torch,library,runner):
    s=run.spec;old=read(s["old_data_path"]);run.check("Old sentinel data unchanged",pin(s["old_data_path"])["sha256"]==OLD_INPUT_SHA)
    sample=old["eval"][0];ids=torch.tensor([sample["tokens"][:128]],dtype=torch.long)
    prior=read(s["old_evaluation_path"])["rows"];native=read(s["baseline_evaluation_path"])["rows"]
    for arm,seed in ARMS:
        run.phase="old bridge "+name(arm,seed)
        refs=[r for r in (native if arm=="fixed32" else prior) if r["arm"]==arm and r["train_seed"]==seed and r["article_id"]==sample["id"] and r["eval_seed"]==5101]
        run.check("Unique old reference "+name(arm,seed),len(refs)==1,status="BLOCKED");ref=refs[0]
        logits,observer=run.call(runner,ids,5101,run.banks.get((arm,seed)))
        raw=library.raw(logits[0,64:].contiguous());run.last_raw=raw;run.last_identity=dict(kind="bridge",arm=arm,train_seed=seed,article_id=sample["id"],eval_seed=5101)
        run.check("Historical exact logits and h0/RNG "+name(arm,seed),sha(raw)==ref["logits_sha256"] and stable(observer)==stable(ref["observer"]),status="BLOCKED")
        run.bridges.append(dict(arm=arm,train_seed=seed,article_id=sample["id"],eval_seed=5101,logits_sha256=sha(raw),observer=observer,Status="PASS"))
        run.actual["bridge_calls"]+=1;run.last_raw=None;del raw,logits
    run.save("oldbridges.json",dict(Status="PASS",rows=run.bridges))


def execute(run,torch,library,runner,data):
    first={};paired={}
    for planned in schedule():
        run.phase="fresh pass%d call%d"%(planned["pass_index"],planned["call_index"])
        sample=data[planned["article_index"]];arm,seed=planned["arm"],planned["train_seed"]
        # Gate and its disk traversal are outside the prediction endpoint timer.
        run.check("405 call budget",run.actual["calls_started"]<405);guard(run.root,run.log.path)
        run.actual["calls_started"]+=1
        logits,observer,metrics,targets,wall_ns,cpu_ns=timed_endpoint(torch,runner,library,sample,planned["eval_seed"],run.banks.get((arm,seed)))
        run.actual["calls_completed"]+=1
        serialization=time.perf_counter();raw=library.raw(logits[0,64:].contiguous());rawsha=sha(raw)
        run.serialization_seconds+=time.perf_counter()-serialization
        row={**planned,"article_id":sample["id"],"logits_sha256":rawsha,"observer":observer,"branch_trace":runner.last_branch,**metrics}
        run.last_raw=raw;run.last_identity=identity(row)
        run.check("Full scored shape and finite metrics",len(raw)==RAW_BYTES and all(math.isfinite(metrics[k]) for k in ("nll_mean","nll_sum")) and metrics["target_count"]==64)
        pair=planned["article_index"],planned["eval_seed"]
        if pair not in paired:paired[pair]=stable(observer)
        run.check("Paired actual h0/RNG across all models",stable(observer)==paired[pair])
        run.check("No gradient graph during validation",not logits.requires_grad and all(p.grad is None and not p.requires_grad for b in run.banks.values() for p in b.parameters()))
        branch=runner.last_branch
        run.check("Exact history route",branch["arm"]==arm and branch["writer_calls"]==(0 if arm=="fixed32" else 32)
            and branch["write_depths"]==([] if arm=="fixed32" else list(range(32)))
            and branch["read_lengths"]==([] if arm=="fixed32" else (list(range(32)) if arm=="depth" else [0]*32)))
        timing={**planned,"article_id":sample["id"],"endpoint_wall_ns":wall_ns,"endpoint_cpu_ns":cpu_ns,"logits_sha256":rawsha,"observer":observer}
        run.timings.append(timing)
        key=rowkey(row)
        if planned["pass_index"]==0:
            n=len(run.rows);columns=logits[0,64:].double();gold=columns.gather(1,targets[64:,None]).squeeze(1);peak=columns.max(-1).values
            nll=(peak-gold)+torch.exp(columns-peak[:,None]).sum(-1).log()
            row.update(worker_per_token=dict(nll=nll.tolist(),predictions=columns.argmax(-1).tolist()),shape=[64,32768],dtype="float32-le",
                targets_sha256=sha(struct.pack("<64q",*sample["tokens"][65:129])),row_input_file="public/rows/row_%03d.json.gz"%n,
                row_audit_file="public/row_audits/row_%03d.json.gz"%n)
            rowpath=run.out/row["row_input_file"];save(rowpath,row,run.root)
            output=run.out/row["row_audit_file"]
            command=[DATA_PYTHON,"-I","-B",str(Path(__file__).with_name("audit_stream.py")),"--spec",str(run.spec["spec_path"]),"--row",str(rowpath),"--output",str(output)]
            audit_start=time.perf_counter()
            try:result=subprocess.run(command,input=raw,capture_output=True,timeout=60)
            except subprocess.TimeoutExpired as exc:
                run.audit_seconds+=time.perf_counter()-audit_start
                run.save("row_audits/process_%03d.json.gz"%n,dict(command=command,returncode=None,timeout_seconds=60,
                    stdout=(exc.stdout or b"").decode(errors="replace"),stderr=(exc.stderr or b"").decode(errors="replace")))
                raise Stop("BLOCKED","Independent row audit timeout; child killed/reaped by subprocess.run") from exc
            run.audit_seconds+=time.perf_counter()-audit_start
            run.save("row_audits/process_%03d.json.gz"%n,dict(command=command,returncode=result.returncode,stdout=result.stdout.decode(errors="replace"),stderr=result.stderr.decode(errors="replace")))
            receipt=read(output) if output.is_file() else {}
            run.check("Independent full streamed row audit",result.returncode==0 and receipt.get("Status")=="PASS",dict(returncode=result.returncode,status=receipt.get("Status")),
                status="BLOCKED" if receipt.get("Status")=="BLOCKED" else "FAIL")
            run.check("Auditor byte and identity binding",receipt["Actual"]["raw"]==dict(bytes=RAW_BYTES,sha256=rawsha) and receipt["Input"]["identity"]==identity(row)
                and receipt["Input"]["row_input"]==pin(rowpath) and receipt["Input"]["spec_sha256"]==pin(run.spec["spec_path"])["sha256"])
            run.rows.append(row);first[key]=row;run.actual["quality_rows"]+=1
            del columns,gold,peak,nll
        else:
            ref=first[key]
            run.check("Second-pass exact logits observer and metrics",rawsha==ref["logits_sha256"] and observer==ref["observer"] and all(metrics[k]==ref[k] for k in metrics))
            run.actual["repeat_rows"]+=1
            if planned["call_index"]==399:
                run.check("Predeclared final sentinel identity",planned["article_index"]==19 and planned["eval_seed"]==5202 and (arm,seed)==("depth",4202))
                path=run.private/"final_sentinel.bin";raw_save(path,raw,run.root)
                run.sentinel=dict(identity=identity(row),path="private/final_sentinel.bin",raw=pin(path),first_pass_row=ref["row_input_file"],first_pass_audit=ref["row_audit_file"])
                run.save("sentinel.json",run.sentinel)
        run.last_raw=None
        print(json.dumps(dict(call=planned["call_index"]+1,pass_index=planned["pass_index"],arm=arm,train_seed=seed,quality_rows=run.actual["quality_rows"],repeat_rows=run.actual["repeat_rows"])),flush=True)
        del logits,raw,targets
    run.save("evaluation.json.gz",dict(rows=run.rows));run.save("timing.json.gz",dict(rows=run.timings))
    run.save("results.json",aggregate(run.rows,run.timings))
    run.check("Complete zero-training execution budget",run.actual==EXPECTED,run.actual)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--spec",type=Path,required=True);parser.add_argument("--out",type=Path,required=True);args=parser.parse_args()
    require(args.spec.is_absolute() and args.out.is_absolute(),"Absolute launch paths")
    spec=read(args.spec);spec["spec_path"]=str(args.spec.resolve());run=Run(spec,args.out);status="NOT TESTED";error=None;preservation="NOT TESTED"
    def interrupted(signum,frame):raise Stop("BLOCKED","Interrupted signal "+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        torch,library,runner,data=initialize(run);bridges(run,torch,library,runner);execute(run,torch,library,runner,data);status="PASS"
    except BaseException as exc:
        status=getattr(exc,"status","BLOCKED" if isinstance(exc,(OSError,MemoryError,KeyboardInterrupt,subprocess.TimeoutExpired)) else "FAIL")
        error=dict(type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc(),phase=run.phase)
    finally:
        run.salvage=status!="PASS"
        if run.salvage and run.last_raw is not None and not (run.private/"final_sentinel.bin").exists():
            try:
                raw_save(run.private/"failed_logits.bin",run.last_raw,run.root,True)
                run.save("failed_raw.json",dict(identity=run.last_identity,pin=pin(run.private/"failed_logits.bin")))
            except BaseException as exc:
                error={"original":error,"failed_raw_preservation_error":repr(exc)}
        try:
            if run.model is not None and run.before:
                after=run.library.state_hashes(run.model);run.save("base_state_after.json",after)
                run.check("Base63states and zero gradients preserved",after==run.before and all(not p.requires_grad and p.grad is None for p in run.model.parameters()))
                adapters={name(a,s):run.library.state_hashes(b) for (a,s),b in run.banks.items()};run.save("adapters_after.json",adapters)
                run.check("All frozen adapter states preserved",adapters==run.adapter_before and all(not p.requires_grad and p.grad is None for b in run.banks.values() for p in b.parameters()))
                run.check("No lingering native hooks",not any(m._forward_hooks or m._forward_pre_hooks for m in run.model.modules()))
                preservation="PASS"
        except BaseException as exc:
            status="FAIL";preservation="FAIL";error={"original":error,"custody_error":repr(exc)};run.salvage=True
        if status!="PASS":
            for filename,value in (("partial_evaluation.json.gz",dict(rows=run.rows)),("partial_timing.json.gz",dict(rows=run.timings))):
                try:run.save(filename,value)
                except BaseException:pass
        report=dict(Purpose="Frozen MoDA fresh-text quality and complete pretokenized CPU endpoint cost",Environment=dict(mode="CPU FP32;2intra/1inter;zero training"),
            Input=dict(freeze=spec["freeze_commit"],prior=OLD_HEAD,data_sha256=spec["data_sha256"]),Expected=EXPECTED,Actual=run.actual,Status=status,error=error,
            preservation=preservation,checks=run.checks,seconds=time.perf_counter()-run.started,load_seconds=getattr(run,"load_seconds",None),
            adapter_load_seconds=getattr(run,"adapter_load_seconds",None),audit_seconds=run.audit_seconds,serialization_seconds=run.serialization_seconds,
            peak_rss_bytes=peak_rss_bytes(),peak_rss_scope="whole worker Linux lifetime inclloading/auditorchestration",
            sentinel=run.sentinel,raw_limit="One last-call sentinel retained;other199 unique fresh full matrices streamed and independently audited but unavailable retrospectively",
            Formal_Oracle="BLOCKED/NOT_READY",FORMAL_ACCEPTANCE_READY=False,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        run.log.close();save(run.public/"completion.json",report,run.root,status!="PASS")
        print(json.dumps({k:report[k] for k in ("Status","Actual","checks","error","seconds")}),flush=True)
    return 0 if status=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
