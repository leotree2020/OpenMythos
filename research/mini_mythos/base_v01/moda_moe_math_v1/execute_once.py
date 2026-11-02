"""One designated CPU math acceptance stage. Never loads pretrained weights."""
from __future__ import annotations
import argparse
import datetime
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
BASE = "76a78d1d9b3d111a832161bd7360af20383e108a"
BRANCH = "mythos-moda-moe-math-cpu-v1"
EXPECTED_REPO = Path("/workspaces/mythos-moda-moe-math-cpu-v1")
RUN = Path("/workspaces/mythos-evidence/base_v01/moda_moe_math/attempt-v1")
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
EXPERIMENT = "MYTHOS-MODA-MOE-MATH-CPU-V1"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
SOURCE = REPO / "open_mythos/moda.py"
SOURCE_SHA256 = "335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492"
SOURCE_BYTES = 42070
UPSTREAM = Path("/workspaces/mythos-parcae-pinned")
UPSTREAM_HEAD = "69284c13746e849104f738d6d1a347b1f457df76"
LOOP_REPO = Path("/workspaces/mythos-loop-index-cpu-v1")
LOOP_ROOT = LOOP_REPO / "research/mini_mythos/base_v01/loop_index_v1"
LOOP_RUN = Path("/workspaces/mythos-evidence/base_v01/loop_index/attempt-v1")
CONTROLLER = Path("research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py")
CONTROLLER_SHA = "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8"
TESTS = ("test_moda.py", "test_moe.py")
RECORD_BUDGET, RESERVE = 32 * 1024**2, 256 * 1024**2
# Includes the still-pending summary/custody/manifests, their public copies,
# checkpoint text and Git serialization overhead; no raw tensors exist here.
FINALIZATION_ALLOWANCE = 4 * 1024**2
ENV = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1",
           OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", HF_HUB_OFFLINE="1",
           TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
INVENTORY_CODE = 'import importlib.metadata as m,json;print(json.dumps(sorted((d.metadata["Name"],d.version,str(d.locate_file(""))) for d in m.distributions())))'


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def info(path):
    size, digest = 0, hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            size += len(block)
            digest.update(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True, timeout=60).strip()


def git_state(path):
    return {"head": git(path, "rev-parse", "HEAD"),
            "status": git(path, "status", "--porcelain=v1", "--untracked-files=all")}


def inventory():
    return json.loads(subprocess.check_output([PYTHON, "-I", "-B", "-c", INVENTORY_CODE], text=True, timeout=60))


def active_workers():
    names = {"execute_once.py", "test_moda.py", "test_moe.py", "run_loop.py", "audit_loop.py",
             "run_lora.py", "audit_lora.py", "run_routing.py", "run_quality.py", "run_base.py",
             "run_forward.py", "run_decode.py", "run_depth_budget.py", "mythos_launch.py"}
    found = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit() or int(item.name) == os.getpid():
            continue
        try:
            argv = (item / "cmdline").read_bytes().split(b"\0")
            match = {Path(x.decode(errors="replace")).name for x in argv if x} & names
            if match:
                found.append({"pid": int(item.name), "names": sorted(match)})
        except (OSError, ProcessLookupError):
            pass
    return found


def worker_command(name, report):
    if name not in TESTS:
        raise ValueError("Only the two frozen math suites are executable")
    return [PYTHON, "-I", "-B", str(ROOT / name), "--source", str(SOURCE),
            "--source-sha256", SOURCE_SHA256, "--report", str(report)]


def validate_report(report, expected_ids):
    actual = report.get("Actual", {})
    rows = actual.get("tests", [])
    expected = sorted(expected_ids)
    return (report.get("Status") == "PASS" and bool(expected) and len(expected) == len(set(expected))
            and actual.get("test_ids") == expected and actual.get("planned") == actual.get("run") == len(expected)
            and actual.get("counts") == {"PASS": len(expected), "FAIL": 0, "BLOCKED": 0, "NOT TESTED": 0}
            and len(rows) == len(expected)
            and sorted(r.get("Input", {}).get("test_id", "") for r in rows) == expected
            and all(r.get("Status") == "PASS" for r in rows)
            and report.get("Input", {}).get("source_sha256") == SOURCE_SHA256
            and report.get("Environment", {}).get("development_only") is False)


def validate_startup_report(report, expected_ids):
    actual = report.get("Actual", {})
    return (report.get("Status") == "PASS" and len(expected_ids) == 4 and len(set(expected_ids)) == 4
            and actual.get("test_ids") == sorted(expected_ids) and actual.get("planned") == actual.get("run") == 4
            and all(actual.get(k) == 0 for k in ("failures", "errors", "skipped")))


def package_path(name):
    p = Path(name)
    if not name or p.is_absolute() or not (ROOT / p).resolve().is_relative_to(ROOT.resolve()):
        raise Stop("FAIL", "Source manifest path escapes package")
    return ROOT / p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.expected_head):
        parser.error("full execution-freeze SHA required")
    if platform.system() != "Linux" or not Path("/workspaces").is_dir():
        print("BLOCKED: designated Codespace required; no math execution")
        return 2
    if RUN.exists():
        print("BLOCKED: existing attempt retained; no retry: " + str(RUN))
        return 2
    RUN.mkdir(parents=True, exist_ok=False)
    checks, commands, protected, states, reports = [], [], {}, {}, {}
    before_env, freeze_ok, baseline_complete = None, False, False
    outcome, error = "NOT TESTED", None
    save(RUN / "CLAIM.json", {"Purpose": EXPERIMENT, "Environment": PYTHON,
        "Input": {"base": BASE, "freeze": args.expected_head, "source_sha256": SOURCE_SHA256},
        "Expected": "MoDA then MoE CPU mathematics only, stop on first BLOCKED/FAIL",
        "Actual": {"pid": os.getpid(), "argv": sys.argv}, "Status": "NOT TESTED", "utc": utc()})

    def interrupted(signum, frame):
        raise Stop("BLOCKED", "Operator interrupted by signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)

    def check(purpose, actual, expected=True, failure="FAIL"):
        row = {"Purpose": purpose, "Environment": PYTHON, "Input": {"freeze": args.expected_head},
               "Expected": expected, "Actual": actual, "Status": "PASS" if actual == expected else failure}
        checks.append(row)
        with (RUN / "operator_checks.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        if row["Status"] != "PASS":
            raise Stop(failure, purpose)

    def command(label, argv):
        process, interruption, cleanup = None, None, []
        start = utc()
        with (RUN / (label + ".stdout")).open("x") as out, (RUN / (label + ".stderr")).open("x") as err:
            try:
                process = subprocess.Popen(argv, cwd=REPO, env=ENV, stdout=out, stderr=err)
                code = process.wait(timeout=600)
            except BaseException as exc:
                interruption = repr(exc)
                if process is not None:
                    try:
                        if process.poll() is None:
                            process.send_signal(signal.SIGTERM)
                        process.wait(timeout=20)
                    except BaseException as child_error:
                        cleanup.append(repr(child_error))
                        try:
                            if process.poll() is None:
                                process.kill()
                            process.wait(timeout=5)
                        except BaseException as kill_error:
                            cleanup.append(repr(kill_error))
                code = process.returncode if process else None
        result = {"label": label, "argv": argv, "pid": process.pid if process else None,
                  "returncode": code, "started": start, "finished": utc(), "interruption": interruption,
                  "cleanup_errors": cleanup, "child_reaped": process is not None and process.poll() is not None}
        commands.append(result)
        save(RUN / (label + "_execution.json"), result)
        if interruption:
            raise Stop("BLOCKED", label + " interrupted; no retry")
        return code

    try:
        check("base checkpoint finalized", bool(re.fullmatch("[0-9a-f]{40}", BASE)), True, "BLOCKED")
        check("designated Codespace", os.environ.get("CODESPACE_NAME"), SPACE, "BLOCKED")
        check("designated interpreter", sys.executable, PYTHON, "BLOCKED")
        check("Python version", platform.python_version(), "3.12.3", "BLOCKED")
        check("isolated no bytecode", bool(sys.flags.isolated) and sys.dont_write_bytecode)
        check("designated worktree", str(REPO.resolve()), str(EXPECTED_REPO))
        check("new math branch", git(REPO, "branch", "--show-current"), BRANCH)
        check("frozen clean checkout", git_state(REPO), {"head": args.expected_head, "status": ""})
        check("base ancestry", git(REPO, "merge-base", BASE, args.expected_head), BASE)
        check("remote freeze", git(REPO, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0], args.expected_head)
        freeze_ok = True
        manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text())
        check("frozen package coverage", {"execute_once.py", "test_startup.py", "shared_helpers.py", *TESTS,
              "PROTOCOL.md", "TEST_INVENTORY.json"}.issubset(manifest))
        for name, pin in manifest.items():
            check("source bytes " + name, info(package_path(name)), pin)
        check("exclusive worker", active_workers(), [], "BLOCKED")
        check("OpenMythos source exact", info(SOURCE), {"bytes": SOURCE_BYTES, "sha256": SOURCE_SHA256})
        protected[str(SOURCE)] = info(SOURCE)
        for path, head in ((REPO, args.expected_head), (UPSTREAM, UPSTREAM_HEAD), (LOOP_REPO, BASE)):
            states[str(path)] = git_state(path)
            check("protected checkout " + str(path), states[str(path)], {"head": head, "status": ""})
            for relative in git(path, "ls-files", "-z").split("\0"):
                target = path / relative
                if relative and target.is_file():
                    protected[str(target)] = info(target)
        states["/workspaces/OpenMythos"] = git_state(Path("/workspaces/OpenMythos"))
        check("early-stop controller unchanged", info(LOOP_REPO / CONTROLLER)["sha256"], CONTROLLER_SHA)
        old_manifest = json.loads((LOOP_ROOT / "EXTERNAL_EVIDENCE_MANIFEST.json").read_text())
        check("old loop evidence manifest nonempty", bool(old_manifest))
        for name, pin in old_manifest.items():
            path = Path(name)
            check("old evidence path confined", path.is_absolute() and path.resolve().is_relative_to(LOOP_RUN))
            check("old evidence pin " + name, info(path), pin)
        for path in sorted(LOOP_RUN.rglob("*")):
            if path.is_file():
                protected[str(path)] = info(path)
        before_env = inventory()
        save(RUN / "environment_before.json", before_env)
        save(RUN / "git_before.json", states)
        save(RUN / "protected_before.json", protected)
        free = shutil.disk_usage(RUN).free
        save(RUN / "resources.json", {"disk_free_bytes": free, "records_budget_bytes": RECORD_BUDGET,
             "reserve_bytes": RESERVE, "required_bytes": RECORD_BUDGET + RESERVE,
             "meminfo": Path("/proc/meminfo").read_text(), "cpuinfo": Path("/proc/cpuinfo").read_text()})
        check("32MiB records plus256MiB reserve", free >= RECORD_BUDGET + RESERVE, True, "BLOCKED")
        baseline_complete = True
        test_inventory = json.loads((ROOT / "TEST_INVENTORY.json").read_text())
        startup_path = RUN / "test_startup_report.json"
        code = command("test_startup", [PYTHON, "-I", "-B", str(ROOT / "test_startup.py"), "--report", str(startup_path)])
        if not startup_path.is_file():
            raise Stop("BLOCKED", "startup fixture report missing")
        startup = json.loads(startup_path.read_text())
        reports["test_startup.py"] = startup
        check("startup process completed", code, 0)
        check("startup exact4 fixture coverage", validate_startup_report(startup, test_inventory["test_startup.py"]["test_ids"]))
        for name in TESTS:
            label, report_path = Path(name).stem, RUN / (Path(name).stem + "_report.json")
            print("Running CPU mathematical fixtures: " + name, flush=True)
            code = command(label, worker_command(name, report_path))
            if not report_path.is_file():
                raise Stop("BLOCKED", label + " report missing")
            report = json.loads(report_path.read_text())
            reports[name] = report
            if report.get("Status") != "PASS":
                raise Stop(report.get("Status") if report.get("Status") in ("FAIL", "BLOCKED") else "BLOCKED", label + " did not pass")
            check(label + " process completed", code, 0)
            check(label + " exact scientific fixture coverage", validate_report(report, test_inventory[name]["test_ids"]))
        current_files = [p for p in RUN.rglob("*") if p.is_file()]
        run_bytes = sum(p.stat().st_size for p in current_files)
        public_copy_bytes = sum(p.stat().st_size for p in RUN.iterdir()
                                if p.is_file() and p.suffix in (".json", ".jsonl", ".stdout", ".stderr"))
        free_after = shutil.disk_usage(RUN).free
        resource_after = {"run_bytes": run_bytes, "run_files": len(current_files),
            "planned_public_copy_bytes": public_copy_bytes,
            "finalization_allowance_bytes": FINALIZATION_ALLOWANCE,
            "projected_total_records_bytes": run_bytes + public_copy_bytes + FINALIZATION_ALLOWANCE,
            "records_budget_bytes": RECORD_BUDGET, "disk_free_bytes": free_after,
            "projected_free_after_publication": free_after - public_copy_bytes - FINALIZATION_ALLOWANCE,
            "reserve_bytes": RESERVE}
        save(RUN / "resources_after.json", resource_after)
        check("records and planned public copies fit32MiB",
              resource_after["projected_total_records_bytes"] <= RECORD_BUDGET, True, "BLOCKED")
        check("public copy and finalization retain256MiB reserve",
              resource_after["projected_free_after_publication"] >= RESERVE, True, "BLOCKED")
        outcome = "PASS"
    except BaseException as exc:
        outcome = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, subprocess.SubprocessError)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    custody = {"changed_files": [], "unreadable_files": [], "changed_git": [], "changed_environment": False}
    try:
        for name, pin in protected.items():
            try:
                if info(name) != pin:
                    custody["changed_files"].append(name)
            except OSError as exc:
                custody["unreadable_files"].append({"path": name, "error": repr(exc)})
        after_git = {name: git_state(Path(name)) for name in states}
        custody["changed_git"] = [name for name in states if states[name] != after_git[name]]
        custody["git_after"] = after_git
        if before_env is not None:
            after_env = inventory()
            save(RUN / "environment_after.json", after_env)
            custody["changed_environment"] = after_env != before_env
        custody["active_workers"] = active_workers()
        custody["cleanup_problems"] = [c for c in commands if not c["child_reaped"] or c["cleanup_errors"]]
        custody["Status"] = ("FAIL" if custody["changed_files"] or custody["changed_git"] or custody["changed_environment"] else
                             "BLOCKED" if custody["unreadable_files"] or custody["active_workers"] or custody["cleanup_problems"] else
                             "PASS" if baseline_complete else "NOT TESTED")
    except BaseException as exc:
        custody.update(Status="BLOCKED", error=repr(exc))
    if custody["Status"] == "FAIL":
        outcome = "FAIL"
    elif outcome == "PASS" and custody["Status"] != "PASS":
        outcome = "BLOCKED"
    save(RUN / "custody.json", custody)
    summary = {"Purpose": EXPERIMENT, "Environment": {"python": PYTHON, "device": "CPU", "gpu": False},
        "Input": {"base": BASE, "execution_freeze": args.expected_head, "source": str(SOURCE), "source_sha256": SOURCE_SHA256},
        "Expected": "MoDA then MoE frozen mathematical fixtures; no pretrained weights or quality experiment",
        "Actual": {"stages": {name: reports.get(name, {"Status": "NOT TESTED"}) for name in ("test_startup.py", *TESTS)},
                   "operator_checks": checks, "commands": commands, "custody": custody},
        "Status": outcome, "error": error, "quality_experiment": "NOT TESTED",
        "FORMAL_ACCEPTANCE_READY": False, "Formal_Oracle": "BLOCKED/NOT_READY", "utc": utc()}
    save(RUN / "summary.json", summary)
    print("STATUS: " + outcome + "\nEVIDENCE: " + str(RUN), flush=True)
    try:
        if not freeze_ok or active_workers() or any(not c["child_reaped"] or c["cleanup_errors"] for c in commands):
            raise RuntimeError("Publication requires frozen quiescent checkout")
        if git_state(REPO) != {"head": args.expected_head, "status": ""}:
            raise RuntimeError("Refuse to publish into changed checkout")
        if git(REPO, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0] != args.expected_head:
            raise RuntimeError("Remote freeze lease changed; original evidence preserved")
        exported = ROOT / "evidence"
        exported.mkdir(exist_ok=False)
        for path in sorted(RUN.iterdir()):
            if path.is_file() and path.suffix in (".json", ".jsonl", ".stdout", ".stderr"):
                shutil.copyfile(path, exported / path.name)
        save(ROOT / "EXTERNAL_EVIDENCE_MANIFEST.json", {str(p): info(p) for p in sorted(RUN.rglob("*")) if p.is_file()})
        checkpoint = ("# " + EXPERIMENT + " checkpoint\n\nStatus: **" + outcome + "**.\n\n"
            "Purpose: mathematical and gradient acceptance of frozen OpenMythos MoDA/MoE source; no Parcae weight loading.\n\n"
            "Base: `" + BASE + "`. Execution freeze: `" + args.expected_head + "`. Branch: `" + BRANCH + "`.\n\n"
            "Environment: designated existing Python3.12.3/Torch2.11.0+cpu; CPU deterministic, OMP/MKL2, intra2/inter1, no autocast.\n\n"
            "Input: open_mythos/moda.py SHA256 `" + SOURCE_SHA256 + "`, frozen synthetic tensors and fixtures. "
            "Expected/Actual: evidence/summary.json and each stage report contain exact coverage, numerical observations, and statuses. "
            "Unreached fixtures are NOT TESTED. Process exit alone does not establish acceptance.\n\n"
            "Custody: " + custody["Status"] + ". Prior loop evidence, upstream, controller and old checkouts preserved. "
            "Raw evidence: `" + str(RUN) + "`; publication.json is a later receipt outside the evidence seal.\n\n"
            "Unresolved: " + ("Real140M integration, quality gain, capacity/compute controls, and generalization remain NOT TESTED." if outcome == "PASS" else json.dumps(error or custody, ensure_ascii=False)) + "\n\n"
            "No B1 rerun, A5 relaxation, B2/D2-A, GPU, PR24 operation, or automatic mechanism stacking. "
            "Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n"
            "Next unique instruction: review this sealed math checkpoint. On PASS design/freeze the separate single-mechanism memory-path quality protocol; "
            "on BLOCKED/FAIL resolve only the recorded cause under a new frozen continuation. No retry or quality launch here.\n")
        with (ROOT / "CHECKPOINT.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(checkpoint)
        paths = [exported, ROOT / "EXTERNAL_EVIDENCE_MANIFEST.json", ROOT / "CHECKPOINT.md"]
        subprocess.run(["git", "-C", str(REPO), "add", "-f", "--", *map(str, paths)], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", "Record MoDA MoE CPU math checkpoint: " + outcome], check=True)
        subprocess.run(["git", "-C", str(REPO), "push", "origin", BRANCH], check=True, timeout=120)
        head = git(REPO, "rev-parse", "HEAD")
        remote = git(REPO, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0]
        if head != remote or git_state(REPO)["status"]:
            raise RuntimeError("Publication remote/clean verification failed")
        save(RUN / "publication.json", {"Status": "PASS", "head": head, "remote": remote, "branch": BRANCH})
        print("CHECKPOINT PUSHED: " + head, flush=True)
    except BaseException as exc:
        save(RUN / "publication.json", {"Status": "BLOCKED", "error": repr(exc), "experiment_status": outcome})
        print("PUBLICATION BLOCKED: " + repr(exc) + "; evidence retained", flush=True)
        return 2
    return 0 if outcome == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
