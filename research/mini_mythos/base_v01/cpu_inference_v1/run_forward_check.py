"""Frozen CPU inference coordinator; no numerical imports or old runner calls."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.metadata
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

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
REPO = Path("/workspaces/mythos-base-v01-rope-diag-v11")
REL = Path("research/mini_mythos/base_v01/cpu_inference_v1")
BRANCH = "mythos-base-v01-cpu-inference-v1"
BASE = "2fec45b01b7cb09ee7d4e3a3f00426549f0d1eb1"
UPSTREAM = Path("/workspaces/mythos-parcae-pinned")
UPSTREAM_SHA = "69284c13746e849104f738d6d1a347b1f457df76"
B1_REPO = Path("/workspaces/mythos-base-v01-b1")
B1_SHA = "d88be474ebb2529c5b095e3732b1f25509f9b824"
B1_RUN = Path("/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z")
ROPE_RUN = Path("/workspaces/mythos-evidence/base_v01/rope_diag/rope-v11-20261101T051150Z")
LOAD_RUN = Path("/workspaces/mythos-evidence/base_v01/load_integrity/load-v1-20261101T055439Z")
VENV = Path("/workspaces/mythos-base-v01-cpu312")
EVIDENCE_ROOT = Path("/workspaces/mythos-evidence/base_v01/cpu_inference")
MODEL_DIR = B1_RUN / "downloads/model"
TOKENIZER = B1_RUN / "downloads/tokenizer/tokenizer.json"
BASE_REL = Path("research/mini_mythos/base_v01")
FROZEN_FILES = ("run_forward_check.py", "worker.py", "inference_checks.py", "tokenizer_checks.py", "PROTOCOL.md", "README_USAGE.md", "STATIC_REVIEW.md")
RUNTIME_ENV = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
PINS = {
    B1_RUN / "manifest.json": (1372, "2ac1ca86c540f3b044304b3abf3951dcbf4d8adf9499056959293cbf315cf962"),
    B1_RUN / "env_check.json": (7825, "55373ba603a91745dcabdaa3e09e24bc916d2b7f3f2cd9251ef88b3006c977cd"),
    ROPE_RUN / "FULL_MANIFEST.json": (42773, "1e8c2ac5a35e52ce71a633ffaab8636de0e90eacb3ea6f1323e63d3e01ac04f5"),
    LOAD_RUN / "FULL_MANIFEST.json": (129670, "fbef83e3acb8e98446d2bff5dabe7b3d89c26dc891549c3895b40bcc64b788e4"),
    REPO / BASE_REL / "load_integrity_v1/state_checks.py": (14760, "2f1238e8b4b17ede1cc56b6ca40ae57a89f1acd797ac881bbebb892790381ed4"),
    B1_REPO / BASE_REL / "requirements.lock": (2881, "84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e"),
}

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return {"size": Path(path).stat().st_size, "sha256": h.hexdigest()}
def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True,
                                   env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).strip()
def git_state(repo):
    return {"head": git(repo,"rev-parse","HEAD"), "branch":git(repo,"branch","--show-current"),
            "status":git(repo,"status","--porcelain=v1","--untracked-files=all","--ignored")}

class Stop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason); self.status, self.reason, self.actual = status, reason, actual

class Run:
    def __init__(self, root, implementation):
        self.root, self.implementation = root, implementation
        self.public, self.private = root / "public", root / "private"
        self.public.mkdir(); self.private.mkdir()
        self.files, self.trees, self.git_before = {}, {}, {}
        self.protection_complete = False
        self.checks = []
        self.status, self.phase, self.stop = "NOT TESTED", "F0", None
        self.gates = {f"F{i}":"NOT TESTED" for i in range(6)}
        self.workers = {}
    def require(self, condition, status, reason, actual, expected=True):
        row = {"utc":utc(),"gate":self.phase,"Purpose":reason,
               "Environment":{"codespace":SPACE,"python":sys.executable,"implementation_commit":self.implementation},
               "Input":"Frozen local artifacts and protocol", "Expected":expected,"Actual":actual,
               "Status":"PASS" if condition else status}
        self.checks.append(row); save(self.public / f"check_{len(self.checks):03d}.json", row)
        if not condition: raise Stop(status, reason, actual)
    def protect(self, p, expected=None):
        p=Path(p)
        if p.is_symlink() or p.resolve()!=p: raise Stop("BLOCKED","Ambiguous protected path",str(p))
        v=digest(p)
        if expected is not None and v!=expected: raise Stop("BLOCKED","Frozen artifact mismatch",{"path":str(p),"actual":v,"expected":expected})
        self.files[str(p)]=v

def preflight(run):
    run.require(os.environ.get("CODESPACE_NAME")==SPACE,"BLOCKED","Designated Codespace",os.environ.get("CODESPACE_NAME"),SPACE)
    run.require(sys.executable==str(VENV/"bin/python") and sys.prefix==str(VENV) and platform.python_version()=="3.12.3",
                "BLOCKED","Frozen interpreter",{"executable":sys.executable,"prefix":sys.prefix,"version":platform.python_version()})
    run.require(Path(__file__).resolve()==REPO/REL/"run_forward_check.py","BLOCKED","Frozen coordinator location",str(Path(__file__).resolve()))
    for repo, head in ((UPSTREAM,UPSTREAM_SHA),(B1_REPO,B1_SHA),(REPO,None)):
        state=git_state(repo); run.git_before[str(repo)]=state
        run.require(not state["status"] and (head is None or state["head"]==head),"BLOCKED","Clean protected checkout",{"path":str(repo),**state})
    run.require(run.git_before[str(REPO)]["branch"]==BRANCH,"BLOCKED","Isolated inference branch",run.git_before[str(REPO)]["branch"],BRANCH)
    git(REPO,"merge-base","--is-ancestor",BASE,run.implementation)
    git(REPO,"merge-base","--is-ancestor",run.implementation,"HEAD")
    changed=git(REPO,"diff","--name-only",BASE,"HEAD").splitlines()
    run.require(bool(changed) and all(n.startswith(str(REL)+"/") for n in changed),"BLOCKED","Only new inference stage changed",changed)
    for name in FROZEN_FILES:
        p=REPO/REL/name
        blob=subprocess.check_output(["git","-C",str(REPO),"show",f"{run.implementation}:{REL/name}"])
        run.require(p.read_bytes()==blob,"BLOCKED","Frozen source bytes",name)
        run.protect(p)
    for p,(size,sha) in PINS.items(): run.protect(p,{"size":size,"sha256":sha})
    for tree, manifest in ((B1_RUN,"manifest.json"),(ROPE_RUN,"FULL_MANIFEST.json"),(LOAD_RUN,"FULL_MANIFEST.json")):
        for item in json.loads((tree/manifest).read_text())["files"]:
            p=(tree/item["path"]).resolve(); p.relative_to(tree)
            run.protect(p,{"size":item["size"],"sha256":item["sha256"]})
        members=sorted(str(p.relative_to(tree)) for p in tree.rglob("*") if p.is_file())
        run.trees[str(tree)]=members
        for n in members:
            if str(tree/n) not in run.files: run.protect(tree/n)
    for name in git(UPSTREAM,"ls-files").splitlines(): run.protect(UPSTREAM/name)
    for name in ("prompts_v1.json","tokenizer_probes_v1.json"):
        p=REPO/BASE_REL/name
        blob=subprocess.check_output(["git","-C",str(REPO),"show",f"{BASE}:{BASE_REL/name}"])
        run.require(p.read_bytes()==blob,"BLOCKED","Frozen prompt/probe input unchanged",name)
        run.protect(p)
    history=json.loads((B1_RUN/"env_check.json").read_text())
    packages={re.sub(r"[-_.]+","-",d.metadata["Name"]).lower():d.version for d in importlib.metadata.distributions() if d.metadata.get("Name")}
    run.require(packages==history["dependencies"]["distributions"],"BLOCKED","Complete dependency inventory",packages,history["dependencies"]["distributions"])
    for name,sha in history["code_identity"]["file_sha256"].items():
        p=B1_REPO/BASE_REL/name; run.protect(p)
        run.require(run.files[str(p)]["sha256"]==sha,"BLOCKED","B1 implementation unchanged",name)
    free=shutil.disk_usage(EVIDENCE_ROOT).free
    available=int(next(x.split()[1] for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")))*1024
    run.require(free>=2*1024**3 and available>=3*1024**3,"BLOCKED","Resource floor",{"disk_free":free,"mem_available":available},"2 GiB disk; 3 GiB available memory")
    run.protection_complete=True
    save(run.private/"protected_before.json",{"files":run.files,"trees":run.trees,"git":run.git_before})
    run.gates["F0"]="PASS"

def run_one_worker(run, name, reference=None):
    out=run.root/name
    command=[str(VENV/"bin/python"),"-B",str(REPO/REL/"worker.py"),"--output",str(out),"--implementation-commit",run.implementation]
    if reference: command += ["--reference",str(reference)]
    save(run.public/f"{name}_launch.json",{"utc":utc(),"command":command,"coordinator_pid":os.getpid(),"timeout_seconds":3600})
    env=dict(os.environ,**RUNTIME_ENV,PYTHONPYCACHEPREFIX=str(run.private/name/"pycache"))
    with (run.private/f"{name}.stdout.log").open("xb") as stdout, (run.private/f"{name}.stderr.log").open("xb") as stderr:
        try: result=subprocess.run(command,stdout=stdout,stderr=stderr,env=env,timeout=3600)
        except subprocess.TimeoutExpired as exc: raise Stop("BLOCKED","Worker exceeded frozen 3600-second budget",name) from exc
    summary_path=out/"public/summary.json"
    run.require(summary_path.is_file(),"BLOCKED","Worker produced terminal evidence",name)
    summary=json.loads(summary_path.read_text()); run.workers[name]=summary
    for gate in ("F1","F2","F3"):
        if name=="first": run.gates[gate]=summary.get("gates",{}).get(gate,"NOT TESTED")
    worker_status=summary.get("status")
    if name=="first" and worker_status!="PASS":
        run.phase=(summary.get("stop") or {}).get("phase","F1")
    run.require(worker_status=="PASS" and result.returncode==0,
                worker_status if worker_status in ("FAIL","BLOCKED") else "BLOCKED",
                "Worker scientific and execution checks",{"returncode":result.returncode,"summary":summary},"PASS evidence and exit 0")
    return summary

def seal(run):
    audit={"changes":[],"unavailable":[],"files":{},"git":{},"trees":{},"complete_baseline":run.protection_complete}
    for name,expected in run.files.items():
        try:
            actual=digest(name); audit["files"][name]={"actual":actual,"expected":expected,"unchanged":actual==expected}
            if actual!=expected: audit["changes"].append(name)
        except Exception as exc: audit["unavailable"].append({"path":name,"error":str(exc)})
    for name,expected in run.git_before.items():
        try:
            actual=git_state(name); audit["git"][name]={"actual":actual,"expected":expected,"unchanged":actual==expected}
            if actual!=expected: audit["changes"].append(name)
        except Exception as exc: audit["unavailable"].append({"path":name,"error":str(exc)})
    for name,expected in run.trees.items():
        actual=sorted(str(p.relative_to(name)) for p in Path(name).rglob("*") if p.is_file())
        audit["trees"][name]={"added":sorted(set(actual)-set(expected)),"removed":sorted(set(expected)-set(actual))}
        if actual!=expected: audit["changes"].append(name)
    invariant_status="FAIL" if audit["changes"] else "PASS" if run.protection_complete and not audit["unavailable"] else "BLOCKED"
    audit["file_integrity_status"]=invariant_status
    audit["both_workers_completed_post_inference_state_check"]=(set(run.workers)=={"first","reload"} and all(w.get("status")=="PASS" for w in run.workers.values()))
    run.gates["F5"]=(invariant_status if invariant_status!="PASS" or audit["both_workers_completed_post_inference_state_check"] else "NOT TESTED")
    save(run.public/"invariance.json",audit)
    if invariant_status=="FAIL" or (invariant_status=="BLOCKED" and run.status=="PASS"):
        run.status=invariant_status
        if run.stop is None: run.stop={"reason":"Protected state audit failed","gate":"F5"}
    summary={"experiment":"MYTHOS-CPU-INFERENCE-V1","run_id":run.root.name,"utc":utc(),
             "engineering_status":run.status,"gates":run.gates,"stop_reason":run.stop,
             "implementation_commit":run.implementation,"execution_head":git(REPO,"rev-parse","HEAD"),
             "branch":BRANCH,"workers":run.workers,"protected_file_count":len(run.files),
             "language_quality":"PENDING AI REVIEW" if run.status=="PASS" else "NOT TESTED",
             "formal_run_started":True,"historical_B1_A5":"BLOCKED","A5_threshold":1e-6,
             "training_and_resume":"NOT TESTED","save_pretrained_roundtrip":"NOT TESTED",
             "Formal_Oracle":"BLOCKED / NOT_READY","FORMAL_ACCEPTANCE_READY":False}
    raw=(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode("utf-8")
    entries=[{"path":str(p.relative_to(run.root)),**digest(p),"class":"public" if "public" in p.relative_to(run.root).parts else "private"}
             for p in sorted(run.root.rglob("*")) if p.is_file()]
    entries.append({"path":"public/summary.json","size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"class":"public"})
    save(run.root/"FULL_MANIFEST.json",{"files":entries,"excluded":["FULL_MANIFEST.json","public/GIT_BUNDLE_MANIFEST.json"]})
    save(run.public/"GIT_BUNDLE_MANIFEST.json",{"files":[e for e in entries if e["class"]=="public"],"excluded":["public/GIT_BUNDLE_MANIFEST.json"],"raw_logits_exported":False})
    with (run.public/"summary.json").open("xb") as f:f.write(raw)
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("--execute",action="store_true");p.add_argument("--implementation-commit",required=True);p.add_argument("--run-id",required=True)
    args=p.parse_args()
    if not args.execute or not re.fullmatch(r"inference-v1-\d{8}T\d{6}Z",args.run_id) or not re.fullmatch(r"[0-9a-f]{40}",args.implementation_commit):
        p.error("Explicit execution, frozen 40-hex implementation and unique UTC run-id required")
    EVIDENCE_ROOT.mkdir(parents=True,exist_ok=True)
    root=EVIDENCE_ROOT/args.run_id;root.mkdir()  # exclusive, never retry/overwrite
    run=Run(root,args.implementation_commit)
    def interrupted(signum, frame):raise Stop("BLOCKED","Coordinator interrupted",signum)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        save(run.private/"CLAIM.json",{"utc":utc(),"pid":os.getpid(),"argv":sys.argv,"run_id":args.run_id})
        preflight(run);run.phase="F1"
        first=run_one_worker(run,"first")
        run.phase="F4"
        second=run_one_worker(run,"reload",root/"first")
        run.require(first["pid"]!=second["pid"] and first["process_started"]!=second["process_started"],"FAIL","Independent interpreter reload",{"first":first["pid"],"reload":second["pid"]})
        run.gates["F4"]="PASS";run.status="PASS"
    except Stop as exc:
        run.status=exc.status;run.gates[run.phase]=exc.status;run.stop={"gate":run.phase,"reason":exc.reason,"actual":exc.actual}
    except BaseException as exc:
        run.status="BLOCKED";run.gates[run.phase]="BLOCKED";run.stop={"gate":run.phase,"reason":str(exc)}
        try:save(run.public/"exception.json",{"traceback":traceback.format_exc()})
        except BaseException as save_exc:run.stop["evidence_save_error"]=repr(save_exc)
    try:
        result=seal(run);print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    except BaseException:
        emergency={"status":"BLOCKED","traceback":traceback.format_exc(),"original_status":run.status,"stop":run.stop}
        try:save(root/"EMERGENCY.json",emergency)
        except BaseException:print(json.dumps(emergency,ensure_ascii=False),file=sys.stderr,flush=True)
        return 2
    return 0 if run.status=="PASS" else 2

if __name__=="__main__":sys.exit(main())
