"""Root read-only custody and independent compact-metric aggregation review.

No model, Torch, NumPy, experiment retry, Git mutation, or checkpoint editing.
The only write is a new acceptance-v1.json outside the sealed attempt directory.
"""
from __future__ import annotations
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

REPO = Path("/workspaces/mythos-moda-residual-cpu-v1")
PACKAGE = "research/mini_mythos/base_v01/moda_residual_v1"
ROOT = REPO / PACKAGE
RUN = Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v1")
OUT = RUN.parent / "acceptance-v1.json"
FREEZE = "922e42f0030aae8f0062ebbc77aa45324db9f5d3"
BRANCH = "mythos-moda-residual-cpu-v1"
EXPECTED_TESTS = {"test_startup.py":8,"test_moda_adapter.py":24,"test_audit.py":13}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pin(path):
    result, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            result.update(block)
            size += len(block)
    return {"bytes":size,"sha256":result.hexdigest()}


def byte_pin(value):
    return {"bytes":len(value),"sha256":hashlib.sha256(value).hexdigest()}


def git_at(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),*args],text=True,timeout=120).strip()


def git(*args):
    return git_at(REPO,*args)


def git_bytes(ref,path):
    return subprocess.check_output(["git","-C",str(REPO),"show",ref+":"+path],timeout=120)


def live_workers():
    found=[]
    names={"run_moda.py","audit_row.py","audit_moda.py","execute_once.py","run_loop.py","run_lora.py"}
    proc=Path("/proc")
    for p in proc.iterdir():
        if not p.name.isdigit():continue
        try:
            argv=(p/"cmdline").read_bytes().split(b"\0")
            matched={Path(x.decode(errors="replace")).name for x in argv if x}&names
            if matched:found.append({"pid":int(p.name),"names":sorted(matched)})
        except (OSError,ProcessLookupError):pass
    return found


def main():
    """Verify the already sealed preflight BLOCKED outcome; never resume it."""
    if OUT.exists():
        print(json.dumps({"Status":"BLOCKED","reason":"acceptance-v1.json already exists; retained without overwrite"}))
        return 2
    result_commit="e83c2411de4da98eb933ca227ddff198c17bdfb6"
    expected_protected={"bytes":6460524,"sha256":"79b11ee7b68d0b84e70b14aeb29fa85b9c9f76c145a77caafb0c0b1d2ebb71a3"}
    reason="protected manifest within2MiB fixture envelope"
    report={"Purpose":"Root verification of sealed preflight BLOCKED result and prior-file custody",
        "Environment":{"python":sys.version,"mode":"Read-only standard-library audit; no model/Torch/NumPy"},
        "Input":{"execution_freeze":FREEZE,"blocked_checkpoint":result_commit,"run":str(RUN)},
        "Expected":"Verify original BLOCKED facts, no model/tests launched, and exact preserved evidence; no gate changes or retry",
        "Actual":{},"Status":"NOT TESTED","checks":[]}
    def check(name,okay,actual=None):
        report["checks"].append({"Purpose":name,"Expected":True,"Actual":actual,"Status":"PASS" if okay else "FAIL"})
        if not okay:raise ValueError(name)
    def confined(base,relative):
        candidate=Path(relative);path=(base/candidate).resolve()
        if candidate.is_absolute() or not path.is_relative_to(base.resolve()):
            raise ValueError("Evidence path escapes declared root: "+str(relative))
        return path
    try:
        publication=read(RUN/"publication.json")
        head=git("rev-parse","HEAD")
        remote=git("ls-remote","origin","refs/heads/"+BRANCH).split()[0]
        check("Published BLOCKED checkpoint and clean review descendant",publication["Status"]=="PASS"
              and publication["head"]==publication["remote"]==result_commit and publication["branch"]==BRANCH
              and git("merge-base",result_commit,head)==result_commit and git("merge-base",FREEZE,head)==FREEZE
              and head==remote and not git("status","--porcelain"),{"result_commit":result_commit,"review_head":head,"remote":remote})
        workers=live_workers()
        check("No running experiment worker",not workers,workers)
        summary,custody,claim=(read(RUN/name) for name in ("summary.json","custody.json","CLAIM.json"))
        check("Original BLOCKED status and reason unchanged",summary["Status"]=="BLOCKED"
              and summary["error"]["reason"]==reason and summary["Input"]["execution_freeze"]==FREEZE
              and claim["Input"]["freeze"]==FREEZE and claim["Status"]=="NOT TESTED")
        commands=summary["Actual"]["commands"]
        check("No formal model or developer-test launch",commands==[] and summary["formal_launch_attempted"] is False
              and summary["Actual"]["main_completion"] is None and summary["Actual"]["reload_completion"] is None,
              {"commands":commands,"formal_launch_attempted":summary["formal_launch_attempted"]})
        check("No worker/reload directories or test reports",not (RUN/"worker").exists() and not (RUN/"reload").exists()
              and not list(RUN.glob("test_*_report.json")) and not (RUN/"spec.json").exists())
        check("Scientific outcomes remain NOT TESTED",summary["scientific_screens"]=="NOT TESTED"
              and summary["Actual"]["scientific_screens"]=="NOT TESTED" and summary["FORMAL_ACCEPTANCE_READY"] is False)
        operator_checks=[json.loads(line) for line in (RUN/"operator_checks.jsonl").read_text().splitlines()]
        stops=[r for r in operator_checks if r["Status"]!="PASS"]
        check("Single unchanged preflight stopping gate",len(stops)==1 and stops[0]["Status"]=="BLOCKED"
              and stops[0]["Purpose"]==reason and stops[0]["Expected"] is True and stops[0]["Actual"] is False,
              {"PASS":sum(x["Status"]=="PASS" for x in operator_checks),"stops":stops})
        check("Frozen2MiB gate was actually exceeded",pin(RUN/"protected_before.json")==expected_protected
              and expected_protected["bytes"]>2*1024**2,
              {"frozen_envelope_bytes":2*1024**2,"actual":expected_protected})
        check("Operator custody accurately remains NOT TESTED",custody["Status"]=="NOT TESTED"
              and not any(custody.get(k) for k in ("changed_files","unreadable_files","changed_git",
                                                  "changed_environments","active_workers","cleanup_problems")))
        source_manifest=read(ROOT/"SOURCE_MANIFEST.json")
        check("Frozen source manifest unchanged",pin(ROOT/"SOURCE_MANIFEST.json")==byte_pin(git_bytes(FREEZE,PACKAGE+"/SOURCE_MANIFEST.json")))
        for name,expected in source_manifest.items():
            check("Frozen source bytes "+name,pin(confined(ROOT,name))==expected==byte_pin(git_bytes(FREEZE,PACKAGE+"/"+name)))
        inputs=read(ROOT/"INPUT_MANIFEST.json")
        for name,expected in inputs.items():check("Frozen input bytes "+name,pin(name)==expected)
        external=read(ROOT/"EXTERNAL_EVIDENCE_MANIFEST.json")
        for name,expected in external.items():
            path=Path(name)
            check("Sealed external bytes "+name,path.is_absolute() and path.resolve().is_relative_to(RUN.resolve()) and pin(path)==expected)
        current_files={str(p) for p in RUN.rglob("*") if p.is_file() and p.name!="publication.json"}
        check("Complete external evidence seal",set(external)==current_files,{"sealed":len(external),"current":len(current_files)})
        exported=read(ROOT/"PUBLIC_EXPORT.json");public=exported["files"]
        check("Public policy preserved",len(public)==len(set(public)) and exported["raw_logits_or_adapters_exported"] is False
              and exported["input_tokens_or_source_text_exported"] is False)
        for name in public:check("Public exact byte copy "+name,pin(confined(ROOT/"evidence",name))==pin(confined(RUN,name)))
        protected=read(RUN/"protected_before.json")
        check("Complete recorded protected inventory",len(protected)==25367,len(protected))
        mismatches=[]
        verified=0
        for name,expected in protected.items():
            try:
                actual=pin(name)
                if actual!=expected:
                    mismatches.append({"path":name,"expected":expected,"actual":actual})
                    break
                verified+=1
            except OSError as exc:
                mismatches.append({"path":name,"expected":expected,"error":repr(exc)})
                break
        check("All recorded prior files retain exact bytes",not mismatches and verified==len(protected),
              {"count":len(protected),"verified":verified,"source_manifest_pin":expected_protected,"mismatches":mismatches})
        old_git=read(RUN/"git_before.json")
        old_git_verified={}
        for name,expected in old_git.items():
            if Path(name).resolve()==REPO.resolve():continue
            actual={"head":git_at(name,"rev-parse","HEAD"),"status":git_at(name,"status","--porcelain=v1","--untracked-files=all")}
            check("Old checkout preserved "+name,actual==expected,actual)
            old_git_verified[name]=actual
        check("Recorded dependencies unchanged",read(RUN/"environment_before.json")==read(RUN/"environment_after.json"))
        test_inventory=read(ROOT/"TEST_INVENTORY.json")
        check("Planned45 developer tests remained planned",{name:len(test_inventory[name]["test_ids"]) for name in EXPECTED_TESTS}==EXPECTED_TESTS)
        resources_before=read(RUN/"resources.json")
        resources_after=read(RUN/"resources_after.json")
        check("No prohibited numerical imports",not any(name.split(".")[0] in ("torch","numpy","parcae_lm","receval") for name in sys.modules))
        report["Actual"]={"experiment_status":"BLOCKED","scientific_conclusion":"NOT TESTED",
            "root_preservation_reverification":"PASS","operator_custody_original_status":"NOT TESTED",
            "blocked_reason":reason,"protected_manifest":expected_protected,"frozen_envelope_bytes":2*1024**2,
            "protected_files_verified":len(protected),"source_files_verified":len(source_manifest),"input_files_verified":len(inputs),
            "external_files_verified":len(external),"public_copies_verified":len(public),"old_git_verified":old_git_verified,
            "commands":commands,"formal_launch_attempted":False,"developer_tests_executed":0,
            "planned_developer_tests":EXPECTED_TESTS,"model_worker_directories":0,"live_audited_rows":0,
            "result_commit":result_commit,"review_code_commit":head,"claim":claim,
            "resources_before":resources_before,"resources_after":resources_after,
            "current_disk_free_bytes":shutil.disk_usage(RUN).free,
            "scope":"Evidence/custody verification only. The frozen2MiB envelope blocked before any developer test or real-model worker. No threshold changed, no retry, no model computation, no scientific efficacy result."}
        report["Status"]="PASS"
    except BaseException as exc:
        report["Status"]="BLOCKED" if isinstance(exc,(OSError,MemoryError,subprocess.SubprocessError,KeyboardInterrupt)) else "FAIL"
        report["error"]={"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    report["check_counts"]={s:sum(c["Status"]==s for c in report["checks"]) for s in ("PASS","FAIL")}
    with OUT.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write("\n")
    a=report["Actual"]
    print(json.dumps({"Status":report["Status"],"checks":report["check_counts"],"error":report.get("error"),
        "experiment_status":a.get("experiment_status"),"protected_manifest":a.get("protected_manifest"),
        "protected_files_verified":a.get("protected_files_verified"),"commands":a.get("commands"),
        "current_disk_free_bytes":a.get("current_disk_free_bytes"),"output":str(OUT)},allow_nan=False))
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())


