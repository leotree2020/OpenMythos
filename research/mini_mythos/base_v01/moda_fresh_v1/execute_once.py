"""One isolated, frozen fresh-text CPU validation; zero training and no retry."""
from __future__ import annotations
import argparse
import datetime
import gzip
import hashlib
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

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
sys.path.insert(0, str(ROOT))
import storage_codec

BRANCH = "mythos-moda-fresh-cpu-v1"
BASE = "bc6d267cdd8cf9306c1bf08b369cf2b791723d3d"
CONTINUATION = "3a7f8b3ac15d4354800360961018de7c66d26be6"
EXPECTED_REPO = Path("/workspaces/mythos-moda-fresh-cpu-v1")
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
EXPERIMENT = "MYTHOS-MODA-FRESH-CPU-V1"
RUN = Path("/workspaces/mythos-evidence/base_v01/moda_fresh/attempt-v1")
PREPARATION = RUN.parent / "preparation-v2"
SPECIFICATION = RUN.parent / "specification-v1"
FRESH_PRIOR_DIRS = (RUN.parent / "preparation-v1", SPECIFICATION, RUN.parent / "stop-v1")
DATA_AUDIT = PREPARATION / "DATA_AUDIT.json"
INPUTS = PREPARATION / "data/inputs.json"
HISTORY_LEDGER = PREPARATION / "data/history_ledger.json.gz"
HISTORY_COUNT = 32244
PREPARATION_MANIFEST = PREPARATION / "data/manifest.json"
DISCOVERY_FILES = [RUN.parent/"discovery-v1.json",RUN.parent/"history-formats-v1.json"]
STORAGE_PREFLIGHT = PREPARATION / "STORAGE_PREFLIGHT.json"
FINAL_INVENTORY_DELTA_LIMIT = 65536
UPSTREAM = Path("/workspaces/mythos-parcae-pinned")
UPSTREAM_HEAD = "69284c13746e849104f738d6d1a347b1f457df76"
MODEL = Path("/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model")
TOKENIZER = MODEL.parent / "tokenizer/tokenizer.json"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
DATA_PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
OFFICIAL_PYTHON = "/workspaces/mythos-parcae-official-eval-cpu312/bin/python"
MAIN_TREE = Path("/workspaces/OpenMythos")
LOOP_REPO = Path("/workspaces/mythos-loop-index-cpu-v1")
CONTROLLER = Path("research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py")
CONTROLLER_SHA = "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8"
OLD_REPO = Path("/workspaces/mythos-moda-residual-cpu-v2")
OLD_PACKAGE = OLD_REPO / "research/mini_mythos/base_v01/moda_residual_v2"
OLD_RUN = Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2")
OLD_DATA = Path("/workspaces/mythos-evidence/base_v01/depth_lora/preparation-v1/data/inputs.json")
BASELINE_EVALUATION = Path("/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1/worker/public/evaluation.json")
MODA_SOURCE = REPO / "open_mythos/moda.py"
MODA_SOURCE_SHA = "335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492"
FIXED_PINS = {
    MODEL / "pytorch_model.bin": "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621",
    MODEL / "config.json": "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13",
    TOKENIZER: "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
}
CHECKOUTS = {
    str(UPSTREAM): UPSTREAM_HEAD,
    "/workspaces/mythos-base-v01-b1": "d88be474ebb2529c5b095e3732b1f25509f9b824",
    "/workspaces/mythos-adaptive-depth-140m-smoke-v1": "ac62e6ac1c04c54451beabc1138d651f55e383d9",
    "/workspaces/mythos-routing-feasibility-cpu-v1": "919d2db8c2ee48b1d83fd8732720b587bd8be011",
    "/workspaces/mythos-routing-feasibility-cpu-v2": "b470cec1ebc6f9a675ce5b674f2073c14d66c237",
    "/workspaces/mythos-routing-feasibility-cpu-v3": "a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683",
    "/workspaces/mythos-routing-quality-cost-cpu-v1": "e24d053f482a96bcc2ab207c1be73e4c91fcd721",
    "/workspaces/mythos-depth-lora-cpu-v1": "d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85",
    str(LOOP_REPO): "76a78d1d9b3d111a832161bd7360af20383e108a",
    "/workspaces/mythos-moda-moe-math-cpu-v1": "5d9df2733f2b04cab9515db8c51c6b37a7443bda",
    "/workspaces/mythos-moda-residual-cpu-v1": "d5d6e74888b65b757ecef075f1bd6838f712cc77",
    str(OLD_REPO): BASE,
}
OLD_RUNS = [Path("/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-" + n) for n in ("v1", "v2", "v3")]
OLD_RUNS += [Path("/workspaces/mythos-evidence/base_v01/" + s) for s in (
    "routing_quality_cost/attempt-v1", "depth_lora/attempt-v1", "loop_index/attempt-v1",
    "moda_moe_math/attempt-v1", "moda_residual/attempt-v1", "moda_residual/attempt-v2",
    "moda_residual/preparation-v2")]
OLD_PARENT_FILES = [OLD_RUN.parent / n for n in (
    "launch-v1.json", "acceptance-v1.json", "acceptance-v1.stdout", "acceptance-publication-v1.json",
    "launch-v2.json", "acceptance-v2.json", "acceptance-v2.stdout")]
OLD_PARENT_FILES += [Path("/workspaces/mythos-moda-residual-v1.log"), Path("/workspaces/mythos-moda-residual-v2.log")]
PRIOR_V1 = OLD_RUN.parent / "attempt-v1/protected_before.json"
PRIOR_V1_PIN = {"bytes": 6460524, "sha256": "79b11ee7b68d0b84e70b14aeb29fa85b9c9f76c145a77caafb0c0b1d2ebb71a3"}
PRIOR_V1_COUNT = 25367
PRIOR_PROTECTED = OLD_RUN / "protected_before.json.gz"
PRIOR_RECEIPT = OLD_RUN / "protected_before_receipt.json"
PRIOR_PROTECTED_PIN = {"bytes":1181241,"sha256":"6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02"}
PRIOR_PROTECTED_COUNT = 25436

# New zero-training artifacts only. Old raw matrices/checkpoints remain protected.
RAW_LOGITS_BUDGET = 8 * 1024**2
METADATA_BUDGET = 12 * 1024**2
DISK_RESERVE = 256 * 1024**2
REQUIRED_DISK_BYTES = RAW_LOGITS_BUDGET + METADATA_BUDGET + DISK_RESERVE
FINALIZATION_ALLOWANCE = 4 * 1024**2
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="2",
           MKL_NUM_THREADS="2", OPENBLAS_NUM_THREADS="1", RAYON_NUM_THREADS="1", HF_HUB_OFFLINE="1",
           TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
INVENTORY_CODE = 'import importlib.metadata as m,json;print(json.dumps(sorted((d.metadata["Name"],d.version,str(d.locate_file(""))) for d in m.distributions())))'
TESTS = ("test_storage_codec.py", "test_startup.py", "test_measure_storage.py", "test_fresh.py", "test_audit_fresh.py")
EXPECTED_COUNTS = dict(model_loads=1,calls_started=405,calls_completed=405,bridge_calls=5,
                       quality_rows=200,repeat_rows=200,train_steps=0,backward_calls=0,optimizer_steps=0)

class Stop(Exception):
    def __init__(self,status,reason): super().__init__(reason); self.status=status

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
def info(path):
    h,n=hashlib.sha256(),0
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b);n+=len(b)
    return {"bytes":n,"sha256":h.hexdigest()}
def git(path,*args): return subprocess.check_output(["git","-C",str(path),*args],text=True,timeout=120).strip()
def git_state(path): return {"head":git(path,"rev-parse","HEAD"),"status":git(path,"status","--porcelain=v1","--untracked-files=all")}
def inventory(executable): return json.loads(subprocess.check_output([executable,"-I","-B","-c",INVENTORY_CODE],text=True,timeout=60))
def active_workers():
    names={"execute_once.py","run_fresh.py","audit_stream.py","run_moda.py","audit_moda.py","audit_row.py","run_lora.py",
           "audit_lora.py","run_loop.py","run_quality.py","run_routing.py","run_depth_budget.py","acceptance_review.py",
           "prepare_once.py","prepare_once_v2.py","data_prepare.py","audit_data.py"}
    found=[]
    for p in Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:
            matches={Path(x.decode(errors="replace")).name for x in (p/"cmdline").read_bytes().split(bytes([0])) if x}&names
            if matches:found.append({"pid":int(p.name),"names":sorted(matches)})
        except (OSError,ProcessLookupError):pass
    return found
def package_path(name,root=ROOT):
    p=Path(name)
    if p.is_absolute() or not name or not (root/p).resolve().is_relative_to(root.resolve()):raise Stop("FAIL","Manifest path escapes package: "+name)
    return root/p
def validate_test_report(report,ids):
    a=report.get("Actual",{})
    return (report.get("Status")=="PASS" and bool(ids) and len(ids)==len(set(ids)) and a.get("test_ids")==sorted(ids)
        and a.get("planned")==a.get("run")==len(ids)
        and all(a.get(k)==0 for k in ("failures","errors","skipped","expected_failures","unexpected_successes")))
def validate_worker_coverage(value): return value.get("Status")=="PASS" and value.get("Actual")==EXPECTED_COUNTS
def worker_command(spec,out):return [PYTHON,"-I","-B",str(ROOT/"run_fresh.py"),"--spec",str(spec),"--out",str(out)]
def audit_command(spec,worker,out):return [DATA_PYTHON,"-I","-B",str(ROOT/"audit_stream.py"),"--final","--spec",str(spec),"--worker",str(worker),"--output",str(out)]
def publication_targets():
    return [ROOT/"evidence",ROOT/"PUBLIC_EXPORT.json",ROOT/"EXTERNAL_EVIDENCE_MANIFEST.json",ROOT/"MODEL_CHECKPOINT.md"]
def publication_budget(root):
    root=Path(root);files=[p for p in root.rglob("*") if p.is_file()]
    raw=sum(p.stat().st_size for p in (root/"worker/private").glob("*.bin") if p.is_file())
    total=sum(p.stat().st_size for p in files)
    public=sum(p.stat().st_size for p in files if public_path(p.relative_to(root)))
    return {"run_bytes":total,"raw_bytes":raw,"public_copy_bytes":public,"git_finalization_allowance":FINALIZATION_ALLOWANCE,
            "projected_total_nonraw_bytes":total-raw+public+FINALIZATION_ALLOWANCE,"free_bytes":shutil.disk_usage(root).free}
def validate_publication_budget(value):
    if value["projected_total_nonraw_bytes"]>METADATA_BUDGET:raise Stop("BLOCKED","Closure evidence/public copies exceed12MiB nonraw allocation")
    if value["free_bytes"]-value["public_copy_bytes"]-FINALIZATION_ALLOWANCE<DISK_RESERVE:raise Stop("BLOCKED","Publication capacity unavailable; external evidence retained")
    return value
def public_path(relative):
    p=Path(relative)
    if p.is_absolute() or ".." in p.parts:return False
    if len(p.parts)==1:return p.name in ("protected_before.json.gz","audit.json.gz") or p.suffix in (".json",".jsonl",".stdout",".stderr")
    return len(p.parts)>=3 and p.parts[:2]==("worker","public") and (p.suffix in (".json",".jsonl") or p.name.endswith(".json.gz") or p.name=="checks.jsonl.gz")
def protected_inputs():
    result={}
    for p,h in {**FIXED_PINS,LOOP_REPO/CONTROLLER:CONTROLLER_SHA,MODA_SOURCE:MODA_SOURCE_SHA}.items():
        pin=info(p)
        if pin["sha256"]!=h:raise Stop("FAIL","Frozen source/input differs: "+str(p))
        result[str(p)]=pin
    for p,pin in json.loads((ROOT/"INPUT_MANIFEST.json").read_text()).items():
        if not Path(p).is_absolute() or Path(p).resolve().is_relative_to(RUN):raise Stop("FAIL","Input path is not external absolute")
        if info(p)!=pin:raise Stop("FAIL","Frozen input differs: "+p)
        result[p]=pin
    return result
def validate_data_audit(pins):
    """No new model work without a frozen independent prepared-data receipt."""
    required=(DATA_AUDIT,INPUTS,PREPARATION_MANIFEST,SPECIFICATION/"DATA_SPEC.json")
    for path in required:
        if str(path) not in pins or info(path)!=pins[str(path)]:raise Stop("FAIL","Independent data gate missing/changed pin: "+str(path))
    report=json.loads(DATA_AUDIT.read_bytes());actual=report.get("Actual",{});inputs=report.get("Input",{})
    if report.get("Status")!="PASS":raise Stop("BLOCKED","Independent data audit has not passed")
    checks=report.get("checks",[])
    if not checks or any(c.get("Status")!="PASS" for c in checks) or report.get("check_counts")!={"PASS":len(checks),"FAIL":0}:raise Stop("FAIL","Independent data audit check coverage")
    if report.get("Environment",{}).get("development_only")is not False or report["Environment"].get("executable")!=DATA_PYTHON:raise Stop("FAIL","Actual target data audit required")
    if inputs.get("spec")!=str(SPECIFICATION/"DATA_SPEC.json") or inputs.get("spec_sha256")!=pins[str(SPECIFICATION/"DATA_SPEC.json")]["sha256"] or inputs.get("prep")!=str(PREPARATION/"data"):raise Stop("FAIL","Independent audit source/preparation binding")
    for key,path in (("audit_source_pin",ROOT/"audit_data.py"),("shared_parser_pin",ROOT/"data_prepare.py"),("tokenizer_pin",TOKENIZER),("source_pin",PREPARATION/"data/corpus.parquet")):
        if inputs.get(key)!=info(path):raise Stop("FAIL","Independent audit code/tokenizer/source pin: "+key)
    if inputs.get("tokenizer_path")!=str(TOKENIZER) or actual.get("source_pin")!=inputs["source_pin"]:raise Stop("FAIL","Independent audit tokenizer/source identity")
    if actual.get("input_pin")!=pins[str(INPUTS)] or actual.get("preparation_manifest")!=pins[str(PREPARATION_MANIFEST)]:raise Stop("FAIL","Independent audit selected bytes binding")
    if actual.get("source_rows")!=7600 or actual.get("selected")!=20 or actual.get("per_class")!={str(i):5 for i in range(4)} or actual.get("history",{}).get("files")!=HISTORY_COUNT:raise Stop("FAIL","Independent audit complete source/history/selection coverage")
    if actual.get("new_model_calls")!=0 or actual.get("new_source_acquisitions")!=0 or actual.get("historical_absence_independently_rescanned")is not False:raise Stop("FAIL","Independent data audit execution/claim boundary")
    data=json.loads(INPUTS.read_bytes())
    if actual.get("selected_ids")!=[r["id"] for r in data["eval"]] or len(set(actual["selected_ids"]))!=20:raise Stop("FAIL","Independent data audit selected ID binding")
    return {"report_pin":pins[str(DATA_AUDIT)],"input_pin":pins[str(INPUTS)],"history_files":HISTORY_COUNT,"selected":20,"historical_absence_independently_rescanned":False}
def history_inputs():
    preparation=json.loads(PREPARATION_MANIFEST.read_bytes())
    if preparation.get("Status")!="PASS" or preparation.get("source_after_status")!="PASS":raise Stop("BLOCKED","Fresh data preparation/custody not accepted")
    receipt=preparation["artifacts"]["history_ledger.json.gz"]
    if info(HISTORY_LEDGER)!=receipt["physical"]:raise Stop("FAIL","Prepared history ledger physical pin differs")
    with gzip.open(HISTORY_LEDGER,"rb") as f:raw=f.read(32*1024**2+1)
    if len(raw)>32*1024**2:raise Stop("BLOCKED","History ledger expansion exceeds32MiB")
    if {"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}!=receipt["canonical"]:raise Stop("FAIL","Prepared history ledger canonical pin differs")
    rows=json.loads(raw);result={}
    if len(rows)!=HISTORY_COUNT or preparation["Actual"].get("historical_files")!=len(rows):raise Stop("FAIL","Complete32244 history ledger required")
    for row in rows:
        path=row["path"];pin={k:row[k] for k in ("bytes","sha256")}
        if path in result or not Path(path).is_absolute() or Path(path).is_symlink():raise Stop("FAIL","Invalid or duplicate history path")
        if row.get("Status") not in ("PASS","PASS_IDENTICAL_PAYLOAD","EXCLUDED_REGISTERED_NONTEXT"):raise Stop("BLOCKED","Incomplete historical parse/classification")
        if info(path)!=pin:raise Stop("FAIL","Historical input changed after preparation: "+path)
        result[path]=pin
    return result
def collect_protected(states,initial=None):
    protected=dict(initial or {})
    def protect(path):
        if path.is_symlink():raise Stop("BLOCKED","Protected file symlink: "+str(path))
        key=str(path);actual=info(path)
        if key in protected and protected[key]!=actual:raise Stop("FAIL","Repeated protected path changed during collection: "+key)
        protected[key]=actual
    for p,pin in history_inputs().items():
        if p in protected and protected[p]!=pin:raise Stop("FAIL","Historical and input pins disagree: "+p)
        protected[p]=pin
    for name in states:
        tree=Path(name);paths=git(tree,"ls-files","-z").split("\0")
        if tree==MAIN_TREE:paths+=git(tree,"ls-files","--others","--exclude-standard","-z").split("\0")
        for rel in paths:
            p=tree/rel
            if rel and p.is_file():protect(p)
    for root in [*OLD_RUNS,PREPARATION,*FRESH_PRIOR_DIRS]:
        if not root.is_dir():raise Stop("BLOCKED","Required preserved directory unavailable: "+str(root))
        for p in sorted(root.rglob("*")):
            # The preflight cannot include its own receipt; it is separately byte-bound before/after.
            if p.is_file() and p!=STORAGE_PREFLIGHT:protect(p)
    # The original attempt had no model run. Preserve every old fresh-phase
    # receipt/log/policy/stop file as well as the new prepared data/audit. Only
    # this unused formal attempt and the self-referential preflight are excluded.
    for p in sorted(RUN.parent.rglob("*")):
        if p==RUN or p.is_relative_to(RUN) or p==STORAGE_PREFLIGHT:continue
        if p.is_symlink():raise Stop("BLOCKED","Fresh continuation symlink: "+str(p))
        if p.is_file():protect(p)
    for p in [*OLD_PARENT_FILES,*DISCOVERY_FILES]:protect(p)
    return protected
def prior_scope_preserved(protected):
    if info(PRIOR_PROTECTED)!=PRIOR_PROTECTED_PIN or info(PRIOR_V1)!=PRIOR_V1_PIN:raise Stop("FAIL","Prior inventory bytes differ")
    old=storage_codec.read_manifest(PRIOR_PROTECTED,json.loads(PRIOR_RECEIPT.read_text()))
    older=json.loads(PRIOR_V1.read_text())
    if len(old)!=PRIOR_PROTECTED_COUNT or len(older)!=PRIOR_V1_COUNT:raise Stop("FAIL","Prior scope count differs")
    for label,mapping in (("v1",older),("v2",old)):
        bad=[p for p,pin in mapping.items() if protected.get(p)!=pin]
        if bad:raise Stop("FAIL","Prior "+label+" protection reduced or changed: "+bad[0])
    return {"original_v1_count":len(older),"original_count":len(old),"current_count":len(protected),
            "all_original_paths_and_pins_preserved":True,"original_manifest":PRIOR_PROTECTED_PIN}
def inventory_parts(protected):
    current,existing={},{}
    for p,pin in protected.items():(current if Path(p).is_relative_to(REPO) else existing)[p]=pin
    return current,existing
def validate_storage_preflight(protected,receipt):
    if info(STORAGE_PREFLIGHT)!=info(ROOT/"STORAGE_PREFLIGHT.json"):raise Stop("FAIL","Frozen storage receipt bytes differ")
    proof=json.loads(STORAGE_PREFLIGHT.read_text())
    if proof.get("Status")!="PASS":raise Stop("BLOCKED","Target storage preflight has not passed")
    a=proof["Actual"];current,existing=inventory_parts(protected);_,er=storage_codec.pack(existing)
    if er!=a["existing_inventory_receipt"]:raise Stop("FAIL","Premeasured existing protection scope/bytes changed")
    measured=a["current_repository_entries"]
    if not set(measured).issubset(current):raise Stop("FAIL","Prepared current-repository path removed")
    changes={p:pin for p,pin in current.items() if measured.get(p)!=pin}
    delta=len(json.dumps(changes,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())+1
    if delta>FINAL_INVENTORY_DELTA_LIMIT:raise Stop("BLOCKED","Final frozen inventory delta exceeds64KiB")
    if receipt["compressed"]["bytes"]>storage_codec.COMPRESSED_LIMIT:raise Stop("BLOCKED","Complete gzip exceeds2MiB")
    return {"preflight_pin":info(STORAGE_PREFLIGHT),"existing_inventory_receipt":er,"changed_entries":len(changes),"delta_bytes":delta,"compressed_bytes":receipt["compressed"]["bytes"]}
def resources():
    mem=dict(line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines())
    result={"mem_available_bytes":int(mem["MemAvailable"].split()[0])*1024,"disk_free_bytes":shutil.disk_usage(RUN if RUN.exists() else REPO).free,
            "cpu_count":os.cpu_count(),"platform":platform.platform(),"disk_budget":{"raw_logits":RAW_LOGITS_BUDGET,"metadata":METADATA_BUDGET,"reserve":DISK_RESERVE,"required_bytes":REQUIRED_DISK_BYTES}}
    for n,p in (("cpuinfo","/proc/cpuinfo"),("loadavg","/proc/loadavg"),("memory_max","/sys/fs/cgroup/memory.max"),("memory_current","/sys/fs/cgroup/memory.current"),("cpu_max","/sys/fs/cgroup/cpu.max")):
        result[n]=Path(p).read_text() if Path(p).is_file() else None
    return result
def make_spec(freeze,pins):
    return {"repo":str(REPO),"freeze_commit":freeze,"expected_head":freeze,"branch":BRANCH,"old_repo":str(OLD_REPO),
        "old_package":str(OLD_PACKAGE),"old_run":str(OLD_RUN),"model_dir":str(MODEL),"upstream":str(UPSTREAM),
        "moda_source":str(MODA_SOURCE),"moda_source_sha256":MODA_SOURCE_SHA,"data_path":str(INPUTS),"data_sha256":pins[str(INPUTS)]["sha256"],
        "old_spec_path":str(OLD_RUN/"spec.json"),"old_adapter_rows_path":str(OLD_RUN/"worker/public/adapters.json"),
        "old_evaluation_path":str(OLD_RUN/"worker/public/evaluation.json"),"old_data_path":str(OLD_DATA),
        "baseline_evaluation_path":str(BASELINE_EVALUATION),"input_pins":pins,"run_root":str(RUN)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--expected-head",required=True);args=parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}",args.expected_head):parser.error("Full frozen commit required")
    if platform.system()!="Linux" or not Path("/workspaces").is_dir():print("BLOCKED: designated Codespace required");return 2
    if RUN.exists():print("BLOCKED: prior attempt preserved, no retry");return 2
    RUN.mkdir(parents=True,exist_ok=False)
    checks,commands,protected,states,environments=[],[],{},{},{}
    outcome,error,freeze_ok,protection_complete="NOT TESTED",None,False,False
    completion,audit,scientific=None,None,"NOT TESTED"
    save(RUN/"CLAIM.json",{"Purpose":EXPERIMENT,"Environment":PYTHON,"Input":{"base":BASE,"freeze":args.expected_head},"Expected":"Single frozen zero-training CPU validation","Actual":{"pid":os.getpid(),"argv":sys.argv},"Status":"NOT TESTED","utc":utc()})
    def interrupted(signum,frame):
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        raise Stop("BLOCKED","Operator interrupted by signal "+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def check(purpose,actual,expected=True,failure="FAIL"):
        record={"Purpose":purpose,"Environment":PYTHON,"Input":{"freeze":args.expected_head},"Expected":expected,"Actual":actual,"Status":"PASS" if actual==expected else failure}
        checks.append(record)
        with (RUN/"operator_checks.jsonl").open("a",encoding="utf-8") as out:out.write(json.dumps(record,allow_nan=False)+"\n")
        if record["Status"]!="PASS":raise Stop(failure,purpose)
    def command(label,argv,timeout):
        proc=None;interruption=None;cleanup=[];started=utc()
        with (RUN/(label+".stdout")).open("x") as stdout,(RUN/(label+".stderr")).open("x") as stderr:
            try:proc=subprocess.Popen(argv,cwd=REPO,env=ENV,stdout=stdout,stderr=stderr,start_new_session=True);code=proc.wait(timeout=timeout)
            except BaseException as exc:
                interruption=repr(exc)
                if proc is not None:
                    try:
                        os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=20)
                    except ProcessLookupError:pass
                    except BaseException as stop_error:
                        cleanup.append(repr(stop_error))
                        try:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
                        except ProcessLookupError:pass
                        except BaseException as kill_error:cleanup.append(repr(kill_error))
                code=proc.returncode if proc else None
        row={"label":label,"argv":argv,"pid":proc.pid if proc else None,"returncode":code,"started":started,"finished":utc(),"interruption":interruption,"cleanup_errors":cleanup,"child_reaped":proc is not None and proc.poll() is not None}
        commands.append(row);save(RUN/(label+"_execution.json"),row)
        if interruption:raise Stop("BLOCKED",label+" interrupted; no retry")
        if active_workers():raise Stop("BLOCKED","Worker descendants remain after "+label)
        return code
    def accept(path,code,label):
        if not path.is_file():raise Stop("BLOCKED",label+" completion missing")
        value=json.loads(gzip.decompress(path.read_bytes()) if path.suffix==".gz" else path.read_bytes())
        if value.get("Status")!="PASS":raise Stop(value.get("Status") if value.get("Status") in ("BLOCKED","FAIL") else "BLOCKED",label+" did not pass")
        check(label+" exit",code,0);return value
    try:
        check("designated Codespace",os.environ.get("CODESPACE_NAME"),SPACE,"BLOCKED")
        check("correct interpreter",sys.executable,PYTHON,"BLOCKED");check("Python version",platform.python_version(),"3.12.3","BLOCKED")
        check("isolated no bytecode",bool(sys.flags.isolated) and sys.dont_write_bytecode)
        check("worktree",str(REPO.resolve()),str(EXPECTED_REPO));check("branch",git(REPO,"branch","--show-current"),BRANCH)
        check("frozen clean checkout",git_state(REPO),{"head":args.expected_head,"status":""})
        check("new model publication paths unused",all(not p.exists() for p in publication_targets()),True,"BLOCKED")
        check("base ancestry",git(REPO,"merge-base",BASE,args.expected_head),BASE)
        check("blocked continuation ancestry",git(REPO,"merge-base",CONTINUATION,args.expected_head),CONTINUATION)
        check("remote freeze",git(REPO,"ls-remote","origin","refs/heads/"+BRANCH).split()[0],args.expected_head);freeze_ok=True
        manifest=json.loads((ROOT/"SOURCE_MANIFEST.json").read_text())
        check("required source coverage",{"execute_once.py","run_fresh.py","audit_stream.py","audit_data.py","storage_codec.py","PROTOCOL.md","STORAGE_BUDGET.md","STORAGE_PREFLIGHT.json","INPUT_MANIFEST.json","TEST_INVENTORY.json","DEVELOPMENT_EVIDENCE_BUDGET.json",*TESTS}.issubset(manifest))
        for name,pin in manifest.items():check("source "+name,info(package_path(name)),pin)
        check("exclusive worker",active_workers(),[],"BLOCKED")
        states[str(REPO)]=git_state(REPO)
        for p,head in CHECKOUTS.items():states[p]=git_state(p);check("old checkout "+p,states[p],{"head":head,"status":""})
        states[str(MAIN_TREE)]=git_state(MAIN_TREE);save(RUN/"git_before.json",states)
        environments={p:inventory(p) for p in (PYTHON,DATA_PYTHON,OFFICIAL_PYTHON)};save(RUN/"environment_before.json",environments)
        res=resources();save(RUN/"resources.json",res)
        check("memory >=3GiB",res["mem_available_bytes"]>=3*1024**3,True,"BLOCKED")
        if res["memory_max"] and res["memory_max"].strip()!="max":check("cgroup available >=3GiB",int(res["memory_max"])-int(res["memory_current"])>=3*1024**3,True,"BLOCKED")
        check("complete new artifact budget plus reserve",res["disk_free_bytes"]>=REQUIRED_DISK_BYTES,True,"BLOCKED")
        proof=json.loads((ROOT/"DEVELOPMENT_EVIDENCE_BUDGET.json").read_text())
        check("pre-frozen serialized evidence budget",proof.get("Status")=="PASS" and proof["Actual"]["projected_total_nonraw_bytes"]<=METADATA_BUDGET)
        pins=protected_inputs();check("prepared data pin present",str(INPUTS) in pins)
        save(RUN/"independent_data_gate.json",validate_data_audit(pins))
        protected=collect_protected(states,pins);coverage=prior_scope_preserved(protected);save(RUN/"protected_scope.json",coverage)
        receipt=storage_codec.write_manifest(RUN/"protected_before.json.gz",protected);save(RUN/"protected_before_receipt.json",receipt)
        check("complete lossless scope roundtrip",storage_codec.read_manifest(RUN/"protected_before.json.gz",receipt)==protected)
        save(RUN/"storage_preflight_validation.json",validate_storage_preflight(protected,receipt));protection_complete=True
        tests=json.loads((ROOT/"TEST_INVENTORY.json").read_text())
        for name in TESTS:
            print("Development checks: "+name,flush=True);label=Path(name).stem;report=RUN/(label+"_report.json")
            code=command(label,[PYTHON,"-I","-B",str(ROOT/name),"--report",str(report)],300)
            value=accept(report,code,label);check(label+" exact coverage",validate_test_report(value,tests[name]["test_ids"]))
        spec=make_spec(args.expected_head,pins);save(RUN/"spec.json",spec)
        print("Running frozen fresh-text CPU validation once; progress: "+str(RUN/"validation.stdout"),flush=True)
        code=command("validation",worker_command(RUN/"spec.json",RUN/"worker"),3600)
        completion=accept(RUN/"worker/public/completion.json",code,"zero-training worker")
        check("complete zero-training coverage",validate_worker_coverage(completion))
        code=command("audit",audit_command(RUN/"spec.json",RUN/"worker",RUN/"audit.json.gz"),600)
        audit=accept(RUN/"audit.json.gz",code,"independent final audit");scientific=audit.get("Actual",{}).get("scientific_screens","NOT TESTED")
        check("scientific screens recorded",scientific!="NOT TESTED")
        raw=sum(p.stat().st_size for p in (RUN/"worker/private").glob("*.bin"))
        total=sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file());public=sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file() and public_path(p.relative_to(RUN)))
        final={"run_bytes":total,"raw_bytes":raw,"public_copy_bytes":public,"git_finalization_allowance":FINALIZATION_ALLOWANCE,
               "projected_total_nonraw_bytes":total-raw+public+FINALIZATION_ALLOWANCE,"free_bytes":shutil.disk_usage(RUN).free}
        save(RUN/"artifact_budget_after.json",final)
        check("one final success sentinel",raw,RAW_LOGITS_BUDGET)
        check("all nonraw and public/Git copies within12MiB",final["projected_total_nonraw_bytes"]<=METADATA_BUDGET,True,"BLOCKED")
        check("publication retains256MiB",final["free_bytes"]-public-FINALIZATION_ALLOWANCE>=DISK_RESERVE,True,"BLOCKED")
        outcome="PASS"
    except BaseException as exc:
        outcome=getattr(exc,"status","BLOCKED" if isinstance(exc,(OSError,KeyboardInterrupt,subprocess.SubprocessError,storage_codec.StorageLimitError)) else "FAIL")
        error={"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    custody={"changed_files":[],"unreadable_files":[],"changed_git":[],"changed_environments":[]}
    try:
        if (RUN/"protected_before.json.gz").is_file() and (RUN/"protected_before_receipt.json").is_file():
            if storage_codec.read_manifest(RUN/"protected_before.json.gz",json.loads((RUN/"protected_before_receipt.json").read_text()))!=protected:raise Stop("FAIL","Stored complete map differs")
        if (ROOT/"STORAGE_PREFLIGHT.json").is_file() and info(STORAGE_PREFLIGHT)!=info(ROOT/"STORAGE_PREFLIGHT.json"):custody["changed_files"].append(str(STORAGE_PREFLIGHT))
        for p,pin in protected.items():
            try:
                if info(p)!=pin:custody["changed_files"].append(p)
            except OSError as exc:custody["unreadable_files"].append({"path":p,"error":repr(exc)})
        after={p:git_state(p) for p in states};custody["git_after"]=after;custody["changed_git"]=[p for p in states if states[p]!=after[p]]
        env_after={p:inventory(p) for p in environments};save(RUN/"environment_after.json",env_after);custody["changed_environments"]=[p for p in environments if environments[p]!=env_after[p]]
        custody["active_workers"]=active_workers();custody["cleanup_problems"]=[c for c in commands if not c["child_reaped"] or c["cleanup_errors"]]
        custody["Status"]="FAIL" if any(custody[k] for k in ("changed_files","changed_git","changed_environments")) else "BLOCKED" if any(custody[k] for k in ("unreadable_files","active_workers","cleanup_problems")) else "PASS" if protection_complete else "NOT TESTED"
    except BaseException as exc:custody.update(Status=getattr(exc,"status","BLOCKED"),error=repr(exc))
    if custody["Status"]=="FAIL":outcome="FAIL"
    elif outcome=="PASS" and custody["Status"]!="PASS":outcome="BLOCKED"
    save(RUN/"custody.json",custody)
    partial=RUN/"worker/public/completion.json"
    if completion is None and partial.is_file():
        try:completion=json.loads(partial.read_text())
        except (OSError,ValueError):pass
    report={"Purpose":"Frozen F32/S/H fresh project-unseen text quality and complete CPU cost validation","Environment":{"python":PYTHON,"audit_python":DATA_PYTHON,"device":"CPU"},
        "Input":{"base":BASE,"execution_freeze":args.expected_head,"data":str(INPUTS)},"Expected":EXPECTED_COUNTS,
        "Actual":{"completion":completion,"commands":commands,"operator_checks":checks,"custody":custody,"protection_complete":protection_complete,"scientific_screens":scientific},
        "Status":outcome,"error":error,"formal_launch_attempted":any(c["label"]=="validation" for c in commands),"scientific_screens":scientific,
        "FORMAL_ACCEPTANCE_READY":False,"Formal_Oracle":"BLOCKED/NOT_READY","utc":utc()}
    save(RUN/"summary.json",report);print("STATUS: "+outcome,flush=True)
    try:
        active=active_workers();save(RUN/"publication_quiescence.json",{"Status":"PASS" if not active else "BLOCKED","active_workers":active})
        if active or any(not c["child_reaped"] or c["cleanup_errors"] for c in commands):raise RuntimeError("Workers not quiescent; preserve external evidence")
        if not freeze_ok or git_state(REPO)!={"head":args.expected_head,"status":""}:raise RuntimeError("Frozen checkout changed; external evidence retained")
        if git(REPO,"ls-remote","origin","refs/heads/"+BRANCH).split()[0]!=args.expected_head:raise RuntimeError("Remote publication lease changed")
        # Recompute after custody/environment/summary/quiescence records exist.
        # The unchanged4MiB allowance covers ensuing small publication receipts,
        # checkpoint/source manifests and Git finalization.
        closing_budget=validate_publication_budget(publication_budget(RUN))
        exported=ROOT/"evidence";exported.mkdir(exist_ok=False);copies=[]
        for p in sorted(RUN.rglob("*")):
            if p.is_file() and public_path(p.relative_to(RUN)):
                rel=p.relative_to(RUN);dest=exported/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);copies.append(str(rel))
        save(ROOT/"PUBLIC_EXPORT.json",{"files":copies,"raw_logits_or_adapters_exported":False,"input_tokens_or_source_text_exported":False})
        save(ROOT/"EXTERNAL_EVIDENCE_MANIFEST.json",{str(p):info(p) for p in sorted(RUN.rglob("*")) if p.is_file()})
        checkpoint=("# "+EXPERIMENT+" checkpoint\n\nEngineering Status: **"+outcome+"**. Base `"+BASE+"`; execution freeze `"+args.expected_head+"`; branch `"+BRANCH+"`.\n\n"
            "Purpose: zero-training fresh-text transfer and complete CPU time comparison for native fixed32, two frozen shared-control adapters and two frozen MoDA history adapters. Environment: designated Codespace, existing Python3.12.3/Torch2.11.0+cpu/NumPy1.26.4,2 intra/1 inter threads. No GPU or dependency change.\n\n"
            "Input:20 frozen project-unseen texts,129 tokens each,64 scored targets;2 h0 seeds;5 configurations;2 measured passes. Five old sentinel bridges are separate warmups. Expected:405 model calls,200 unique quality rows,200 exact repeat rows; zero updates/backward/optimizer. Actual: see evidence/summary.json and audit.json.gz; unreached work remains NOT TESTED.\n\n"
            "Scientific screens: "+json.dumps(scientific)+". Frozen margins unchanged: each adapter training seed deltaNLL<=-0.01 and deltaAccuracy>=-0.01. Negative scientific screens are valid findings, not engineering errors. Timing is descriptive and is not equal-compute superiority.\n\n"
            "Evidence: `"+str(RUN)+"`; full external pins in EXTERNAL_EVIDENCE_MANIFEST.json, public copies in evidence/. Planned custody: each of200 unique scored matrices receives full live independent NumPy audit through a bounded pipe; pass2 must reproduce each full matrix hash. Actual completed coverage: "+json.dumps(completion.get("Actual",{}) if completion else "NOT TESTED")+". Only the last repeat matrix is retained after complete success, and final audit recomputes it; the other199 unique full matrices cannot be reconstructed from compact statistics. Earlier numerical/audit failures retain the current full matrix instead and stop. Unreached audits/repeats remain NOT TESTED. Old raw matrices/weights/adapters remain unchanged.\n\n"
            "Custody: "+custody["Status"]+"; complete protection-map acceptance established: "+str(protection_complete)+". The required scope includes original v1/v2 maps, full historical ledger and all prior fresh-phase stop/preparation records; unreached checks are not claimed as passed. Storage uses lossless gzip without dropping physical paths. New protocol8MiB raw +12MiB nonraw +256MiB reserve; source/data preparation already consumes disk before admission. No upstream/threshold writes, B1 rerun/B2/D2-A/mechanism stacking/PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n"
            "Unresolved: "+(json.dumps(error or custody) if outcome!="PASS" else "limited20-text sample, source/domain specificity, unknown base-pretraining overlap, only frozen output-projection adaptation, non-independent AI review and small timing sample")+".\n\n"
            "Next unique instruction: read this checkpoint and independently review the quality, timing and preservation evidence; do not tune or repeat this attempt. Resolve any BLOCKED/FAIL only in a separately frozen continuation. No next mechanism starts automatically.\n")
        with (ROOT/"MODEL_CHECKPOINT.md").open("x",encoding="utf-8",newline="\n") as f:f.write(checkpoint)
        paths=publication_targets()
        subprocess.run(["git","-C",str(REPO),"add","-f","--",*map(str,paths)],check=True)
        subprocess.run(["git","-C",str(REPO),"commit","-m","Record frozen fresh-text MoDA CPU validation: "+outcome],check=True)
        subprocess.run(["git","-C",str(REPO),"push","origin",BRANCH],check=True,timeout=120)
        head=git(REPO,"rev-parse","HEAD");remote=git(REPO,"ls-remote","origin","refs/heads/"+BRANCH).split()[0]
        if head!=remote or git_state(REPO)["status"]:raise RuntimeError("Publication remote/clean check failed")
        save(RUN/"publication.json",{"Status":"PASS","head":head,"remote":remote,"branch":BRANCH,"postclosure_budget":closing_budget});print("CHECKPOINT PUSHED: "+head,flush=True)
    except BaseException as exc:
        save(RUN/"publication.json",{"Status":"BLOCKED","error":repr(exc),"experiment_status":outcome});print("PUBLICATION BLOCKED: "+repr(exc),flush=True);return 2
    return 0 if outcome=="PASS" else 2

if __name__=="__main__":raise SystemExit(main())
