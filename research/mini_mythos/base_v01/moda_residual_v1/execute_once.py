"""Single designated-CPU residual-MoDA pilot; no tuning, retry, or old runner use."""
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
BRANCH = "mythos-moda-residual-cpu-v1"
BASE = "5d9df2733f2b04cab9515db8c51c6b37a7443bda"
EXPECTED_REPO = Path("/workspaces/mythos-moda-residual-cpu-v1")
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
EXPERIMENT = "MYTHOS-MODA-RESIDUAL-CPU-V1"
RUN = Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v1")
INPUTS = Path("/workspaces/mythos-evidence/base_v01/depth_lora/preparation-v1/data/inputs.json")
UPSTREAM = Path("/workspaces/mythos-parcae-pinned")
UPSTREAM_HEAD = "69284c13746e849104f738d6d1a347b1f457df76"
MODEL = Path("/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model")
TOKENIZER = MODEL.parent / "tokenizer/tokenizer.json"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
DATA_PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
OFFICIAL_PYTHON = "/workspaces/mythos-parcae-official-eval-cpu312/bin/python"
CONTROLLER = Path("research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py")
LOOP_REPO = Path("/workspaces/mythos-loop-index-cpu-v1")
MODA_SOURCE = REPO / "open_mythos/moda.py"
MODA_SOURCE_SHA = "335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492"
BASELINE_EVALUATION = Path("/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1/worker/public/evaluation.json")
BASELINE_MANIFEST = Path("/workspaces/mythos-depth-lora-cpu-v1/research/mini_mythos/base_v01/depth_lora_v1/EXTERNAL_EVIDENCE_MANIFEST.json")
FIXED_PINS = {
    MODEL / "pytorch_model.bin": "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621",
    MODEL / "config.json": "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13",
    TOKENIZER: "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
}
CONTROLLER_SHA = "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8"
CHECKOUTS = {
    "/workspaces/mythos-parcae-pinned": UPSTREAM_HEAD,
    "/workspaces/mythos-base-v01-b1": "d88be474ebb2529c5b095e3732b1f25509f9b824",
    "/workspaces/mythos-adaptive-depth-140m-smoke-v1": "ac62e6ac1c04c54451beabc1138d651f55e383d9",
    "/workspaces/mythos-routing-feasibility-cpu-v1": "919d2db8c2ee48b1d83fd8732720b587bd8be011",
    "/workspaces/mythos-routing-feasibility-cpu-v2": "b470cec1ebc6f9a675ce5b674f2073c14d66c237",
    "/workspaces/mythos-routing-feasibility-cpu-v3": "a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683",
    "/workspaces/mythos-routing-quality-cost-cpu-v1": "e24d053f482a96bcc2ab207c1be73e4c91fcd721",
    "/workspaces/mythos-depth-lora-cpu-v1": "d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85",
    "/workspaces/mythos-loop-index-cpu-v1": "76a78d1d9b3d111a832161bd7360af20383e108a",
    "/workspaces/mythos-moda-moe-math-cpu-v1": BASE,
}
OLD_RUNS = [Path("/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-" + n) for n in ("v1", "v2", "v3")]
OLD_RUNS.append(Path("/workspaces/mythos-evidence/base_v01/routing_quality_cost/attempt-v1"))
OLD_RUNS.append(Path("/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1"))
OLD_RUNS.append(Path("/workspaces/mythos-evidence/base_v01/loop_index/attempt-v1"))
OLD_RUNS.append(Path("/workspaces/mythos-evidence/base_v01/moda_moe_math/attempt-v1"))
# One pending full tensor plus four retained sentinels. All old evidence remains.
RAW_LOGITS_BUDGET = 5 * 64 * 32768 * 4
METADATA_BUDGET = 32 * 1024**2
DISK_RESERVE = 256 * 1024**2
REQUIRED_DISK_BYTES = RAW_LOGITS_BUDGET + METADATA_BUDGET + DISK_RESERVE
FINALIZATION_ALLOWANCE = 4 * 1024**2
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CUDA_VISIBLE_DEVICES="",
           OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", HF_HUB_OFFLINE="1",
           TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
INVENTORY_CODE = 'import importlib.metadata as m,json;print(json.dumps(sorted((d.metadata["Name"],d.version,str(d.locate_file(""))) for d in m.distributions())))'
TESTS = ("test_startup.py", "test_moda_adapter.py", "test_audit.py")


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def info(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True, timeout=60).strip()


def git_state(path):
    return {"head": git(path, "rev-parse", "HEAD"),
            "status": git(path, "status", "--porcelain=v1", "--untracked-files=all")}


def active_workers():
    workers = []
    names = {"execute_once.py", "run_moda.py", "audit_moda.py", "audit_row.py", "run_lora.py", "audit_lora.py", "data_lora.py", "run_smoke.py",
             "run_routing.py", "run_quality.py", "run_depth_budget.py", "mythos_launch.py",
             "observe_official.py", "run_base.py", "run_forward.py", "run_decode.py"}
    for item in Path("/proc").iterdir():
        if not item.name.isdigit() or int(item.name) == os.getpid():
            continue
        try:
            argv = (item / "cmdline").read_bytes().split(b"\0")
            match = {Path(x.decode(errors="replace")).name for x in argv if x} & names
            if match:
                workers.append({"pid": int(item.name), "names": sorted(match)})
        except (OSError, ProcessLookupError):
            pass
    return workers


def worker_command(spec, out, reload=False):
    command = [PYTHON, "-I", "-B", str(ROOT / "run_moda.py"), "--spec", str(spec), "--out", str(out)]
    return command + (["--reload"] if reload else [])


def audit_command(run, out):
    return [DATA_PYTHON, "-I", "-B", str(ROOT / "audit_moda.py"), "--run", str(run), "--output", str(out)]


def package_path(name, root=ROOT):
    candidate = Path(name)
    if candidate.is_absolute() or not name or not (root / candidate).resolve().is_relative_to(root.resolve()):
        raise Stop("FAIL", "Manifest path escapes package: " + name)
    return root / candidate


def validate_test_report(report, test_ids):
    actual = report.get("Actual", {})
    return (report.get("Status") == "PASS" and bool(test_ids) and len(test_ids) == len(set(test_ids))
            and actual.get("test_ids") == sorted(test_ids)
            and actual.get("planned") == actual.get("run") == len(test_ids)
            and all(actual.get(key) == 0 for key in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")))


def validate_worker_coverage(completion, reload=False):
    expected = ({"calls_started": 4, "calls_completed": 4, "train_steps": 0, "eval_rows": 0,
                 "zero_control_calls": 0, "model_loads": 1, "adapters_saved": 0, "reload_calls": 4}
                if reload else
                {"calls_started": 293, "calls_completed": 293, "train_steps": 128, "eval_rows": 160,
                 "zero_control_calls": 5, "model_loads": 1, "adapters_saved": 4, "reload_calls": 0})
    return completion.get("Status") == "PASS" and all(completion.get("Actual", {}).get(k) == v for k, v in expected.items())


def public_path(relative):
    """Never export raw tensors, checkpoints, inputs or source text."""
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts:
        return False
    if len(p.parts) == 1:
        return p.suffix in (".json", ".jsonl", ".stdout", ".stderr")
    return (len(p.parts) >= 3 and p.parts[0] in ("worker", "reload") and p.parts[1] == "public"
            and p.suffix in (".json", ".jsonl"))


def evidence_progress(run):
    progress = {"live_audits": {"PASS":0,"FAIL":0,"BLOCKED":0},
                "retention_actions":{"historical_bridge":0,"sentinel":0,"audited_then_discarded":0},
                "retained_new_sentinel_files":0,"pending_new_raw_files":0,"read_errors":[]}
    for path in sorted((run/"worker/public/row_audits").glob("row_*.json")):
        try:
            status=json.loads(path.read_text()).get("Status")
            if status in progress["live_audits"]:progress["live_audits"][status]+=1
            else:progress["read_errors"].append(str(path))
        except (OSError,ValueError):progress["read_errors"].append(str(path))
    ledger=run/"worker/public/retention.jsonl"
    if ledger.is_file():
        try:
            for line in ledger.read_text().splitlines():
                action=json.loads(line).get("action")
                if action in progress["retention_actions"]:progress["retention_actions"][action]+=1
                else:progress["read_errors"].append(str(ledger))
        except (OSError,ValueError):progress["read_errors"].append(str(ledger))
    progress["retained_new_sentinel_files"]=len(list((run/"worker/private").glob("sentinel_row_*.bin")))
    progress["pending_new_raw_files"]=len(list((run/"worker/private").glob("pending_row_*.bin")))
    progress["remaining_live_audits"]="NOT TESTED" if progress["live_audits"]["PASS"]<160 else "NONE"
    return progress


def inventory(executable):
    return json.loads(subprocess.check_output([executable, "-I", "-B", "-c", INVENTORY_CODE], text=True, timeout=60))


def resources():
    mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    result = {"mem_available_bytes": int(mem["MemAvailable"].split()[0]) * 1024,
              "disk_free_bytes": shutil.disk_usage(RUN).free, "cpu_count": os.cpu_count(), "platform": platform.platform(),
              "disk_budget": {"raw_logits": RAW_LOGITS_BUDGET, "metadata_checkpoints": METADATA_BUDGET,
                              "reserve": DISK_RESERVE, "required_bytes": REQUIRED_DISK_BYTES}}
    for name, filename in (("cpuinfo", "/proc/cpuinfo"), ("loadavg", "/proc/loadavg"),
                           ("memory_max", "/sys/fs/cgroup/memory.max"), ("memory_current", "/sys/fs/cgroup/memory.current"),
                           ("cpu_max", "/sys/fs/cgroup/cpu.max")):
        path = Path(filename)
        result[name] = path.read_text() if path.is_file() else None
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.expected_head):
        parser.error("--expected-head must be a full frozen commit SHA")
    if platform.system() != "Linux" or not Path("/workspaces").is_dir():
        print("BLOCKED: designated Codespace required; no model started")
        return 2
    if RUN.exists():
        print("BLOCKED: existing attempt retained, no retry: " + str(RUN))
        return 2
    RUN.mkdir(parents=True, exist_ok=False)
    checks, commands, protected, states, inventories = [], [], {}, {}, {}
    outcome, error, freeze_ok, baseline_complete, scientific = "NOT TESTED", None, False, False, "NOT TESTED"
    main_completion, reload_completion = None, None
    save(RUN / "CLAIM.json", {"Purpose": EXPERIMENT, "Environment": PYTHON,
         "Input": {"base": BASE, "freeze": args.expected_head},
         "Expected": "One frozen CPU pilot, no tuning/retry; scientific screens separate from engineering status",
         "Actual": {"pid": os.getpid(), "argv": sys.argv}, "Status": "NOT TESTED", "utc": utc()})

    def interrupted(signum, frame):
        raise Stop("BLOCKED", "Operator received signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)

    def check(purpose, actual, expected=True, failure="FAIL"):
        row = {"Purpose": purpose, "Environment": PYTHON, "Input": {"freeze": args.expected_head},
               "Expected": expected, "Actual": actual, "Status": "PASS" if actual == expected else failure}
        checks.append(row)
        with (RUN / "operator_checks.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        if row["Status"] != "PASS":
            raise Stop(failure, purpose)

    def command(label, argv, timeout):
        process, interruption, cleanup = None, None, []
        started = utc()
        with (RUN / (label + ".stdout")).open("x") as stdout, (RUN / (label + ".stderr")).open("x") as stderr:
            try:
                process = subprocess.Popen(argv, cwd=REPO, env=ENV, stdout=stdout, stderr=stderr)
                code = process.wait(timeout=timeout)
            except BaseException as exc:
                interruption = repr(exc)
                if process is not None:
                    try:
                        if process.poll() is None:
                            process.send_signal(signal.SIGTERM)
                        process.wait(timeout=20)
                    except BaseException as stop_error:
                        cleanup.append(repr(stop_error))
                        try:
                            if process.poll() is None:
                                process.kill()
                            process.wait(timeout=5)
                        except BaseException as kill_error:
                            cleanup.append(repr(kill_error))
                code = process.returncode if process else None
        row = {"label": label, "argv": argv, "pid": process.pid if process else None, "returncode": code,
               "started": started, "finished": utc(), "interruption": interruption, "cleanup_errors": cleanup,
               "child_reaped": process is not None and process.poll() is not None}
        commands.append(row)
        save(RUN / (label + "_execution.json"), row)
        if interruption:
            raise Stop("BLOCKED", label + " interrupted; no retry")
        return code

    def accept_stage(path, code, purpose):
        if not path.is_file():
            raise Stop("BLOCKED", purpose + " completion missing")
        value = json.loads(path.read_text())
        if value.get("Status") != "PASS":
            raise Stop(value.get("Status") if value.get("Status") in ("FAIL", "BLOCKED") else "BLOCKED", purpose + " did not pass")
        check(purpose + " process exit", code, 0)
        return value

    try:
        check("designated Codespace", os.environ.get("CODESPACE_NAME"), SPACE, "BLOCKED")
        check("correct interpreter", sys.executable, PYTHON, "BLOCKED")
        check("Python version", platform.python_version(), "3.12.3", "BLOCKED")
        check("isolated no bytecode", bool(sys.flags.isolated) and sys.dont_write_bytecode)
        check("designated worktree", str(REPO.resolve()), str(EXPECTED_REPO))
        check("correct new branch", git(REPO, "branch", "--show-current"), BRANCH)
        check("frozen clean checkout", git_state(REPO), {"head": args.expected_head, "status": ""})
        check("requested base ancestry", git(REPO, "merge-base", BASE, args.expected_head), BASE)
        check("remote frozen head", git(REPO, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0], args.expected_head)
        freeze_ok = True
        manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text())
        check("required frozen source coverage", {"execute_once.py", "moda_model.py", "run_moda.py", "audit_moda.py", "audit_row.py",
              "PROTOCOL.md", "TEST_INVENTORY.json", "INPUT_MANIFEST.json", "DEVELOPMENT_EVIDENCE_BUDGET.json", *TESTS}.issubset(manifest))
        for name, pin in manifest.items():
            check("source bytes " + name, info(package_path(name)), pin)
        check("exclusive model worker", active_workers(), [], "BLOCKED")
        states[str(REPO)] = git_state(REPO)
        for name, head in CHECKOUTS.items():
            states[name] = git_state(Path(name))
            check("protected checkout " + name, states[name], {"head": head, "status": ""})
        main_tree = Path("/workspaces/OpenMythos")
        states[str(main_tree)] = git_state(main_tree)
        save(RUN / "git_before.json", states)
        for executable in (PYTHON, DATA_PYTHON, OFFICIAL_PYTHON):
            inventories[executable] = inventory(executable)
        save(RUN / "environment_before.json", inventories)
        resource = resources()
        save(RUN / "resources.json", resource)
        check("available memory >=3GiB", resource["mem_available_bytes"] >= 3 * 1024**3, True, "BLOCKED")
        check("free disk covers compact evidence budget plus reserve", resource["disk_free_bytes"] >= REQUIRED_DISK_BYTES, True, "BLOCKED")
        budget_proof = json.loads((ROOT / "DEVELOPMENT_EVIDENCE_BUDGET.json").read_text())
        check("pre-frozen serialized evidence budget proof", budget_proof.get("Status") == "PASS"
              and budget_proof["Actual"]["projected_total_nonraw_bytes"] <= METADATA_BUDGET)
        if resource["memory_max"] and resource["memory_max"].strip() != "max":
            check("available cgroup memory >=3GiB", int(resource["memory_max"]) - int(resource["memory_current"]) >= 3 * 1024**3, True, "BLOCKED")
        for path, sha in {**FIXED_PINS, LOOP_REPO / CONTROLLER: CONTROLLER_SHA, MODA_SOURCE: MODA_SOURCE_SHA}.items():
            actual = info(path)
            check("fixed input " + str(path), actual["sha256"], sha)
            protected[str(path)] = actual
        input_manifest = json.loads((ROOT / "INPUT_MANIFEST.json").read_text())
        check("frozen prepared data pin present", str(INPUTS) in input_manifest)
        for name, pin in input_manifest.items():
            path = Path(name)
            check("input manifest absolute and outside attempt", path.is_absolute() and not path.resolve().is_relative_to(RUN))
            check("prepared input " + name, info(path), pin)
            protected[name] = pin
        # Preserve tracked source, existing main-checkout edits, and prior raw records.
        for name in states:
            checkout = Path(name)
            tracked = git(checkout, "ls-files", "-z").split("\0")
            untracked = git(checkout, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if checkout == main_tree else []
            for relative in tracked + untracked:
                path = checkout / relative
                if relative and path.is_file():
                    protected[str(path)] = info(path)
        for old in OLD_RUNS:
            check("old run retained " + str(old), old.is_dir())
            for path in sorted(old.rglob("*")):
                if path.is_file():
                    protected[str(path)] = info(path)
        save(RUN / "protected_before.json", protected)
        check("protected manifest within2MiB fixture envelope", (RUN/"protected_before.json").stat().st_size <= 2*1024**2, True, "BLOCKED")
        baseline_manifest = json.loads(BASELINE_MANIFEST.read_text())
        baseline_pin = baseline_manifest[str(BASELINE_EVALUATION)]
        check("sealed historical F32 evaluation", info(BASELINE_EVALUATION), baseline_pin)
        baseline_complete = True
        test_inventory = json.loads((ROOT / "TEST_INVENTORY.json").read_text())
        for filename in TESTS:
            label = Path(filename).stem
            print("Development checks: " + filename, flush=True)
            report_path = RUN / (label + "_report.json")
            test_command = [PYTHON, "-I", "-B", str(ROOT / filename), "--report", str(report_path)]
            if filename == "test_moda_adapter.py":
                test_command += ["--source", str(MODA_SOURCE)]
            code = command(label, test_command, 300)
            test_report = accept_stage(report_path, code, label)
            check(label + " exact coverage", validate_test_report(test_report, test_inventory[filename]["test_ids"]))
        spec = {"repo": str(REPO), "upstream": str(UPSTREAM), "model_dir": str(MODEL), "data_path": str(INPUTS),
                "output": str(RUN / "worker"), "freeze_commit": args.expected_head, "expected_head": args.expected_head,
                "branch": BRANCH, "inputs_sha256": input_manifest[str(INPUTS)]["sha256"],
                "moda_source": str(MODA_SOURCE), "moda_source_sha256": MODA_SOURCE_SHA,
                "baseline_evaluation_path": str(BASELINE_EVALUATION), "baseline_evaluation_pin": baseline_pin}
        save(RUN / "spec.json", spec)
        print("Running frozen residual-MoDA CPU pilot once. Progress: " + str(RUN / "train.stdout"), flush=True)
        code = command("train", worker_command(RUN / "spec.json", RUN / "worker"), 3600)
        main_completion = accept_stage(RUN / "worker/public/completion.json", code, "main worker")
        check("main complete frozen call/step coverage", validate_worker_coverage(main_completion))
        code = command("reload", worker_command(RUN / "spec.json", RUN / "reload", reload=True), 300)
        reload_completion = accept_stage(RUN / "reload/public/completion.json", code, "new process reload")
        check("reload complete frozen coverage", validate_worker_coverage(reload_completion, reload=True))
        code = command("audit", audit_command(RUN, RUN / "audit.json"), 600)
        audit = accept_stage(RUN / "audit.json", code, "independent audit")
        scientific = audit.get("Actual", {}).get("scientific_screens", "NOT TESTED")
        check("scientific screens recorded", scientific != "NOT TESTED")
        sentinel_bytes = sum(p.stat().st_size for p in (RUN / "worker/private").glob("sentinel_row_*.bin"))
        run_bytes = sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file())
        public_bytes = sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file() and public_path(p.relative_to(RUN)))
        after_resource = {"run_bytes":run_bytes,"sentinel_bytes":sentinel_bytes,"planned_public_copy_bytes":public_bytes,
             "finalization_allowance_bytes":FINALIZATION_ALLOWANCE,"metadata_budget_bytes":METADATA_BUDGET,
             "projected_total_nonraw_bytes":run_bytes-sentinel_bytes+public_bytes+FINALIZATION_ALLOWANCE,
             "disk_free_bytes":shutil.disk_usage(RUN).free,"reserve_bytes":DISK_RESERVE}
        save(RUN / "compact_budget_after.json", after_resource)
        check("four complete retained sentinels", sentinel_bytes, 4*64*32768*4)
        check("metadata checkpoint publiccopy finalization within32MiB", after_resource["projected_total_nonraw_bytes"] <= METADATA_BUDGET, True, "BLOCKED")
        check("aftercopy preserves256MiB reserve", after_resource["disk_free_bytes"]-public_bytes-FINALIZATION_ALLOWANCE >= DISK_RESERVE, True, "BLOCKED")
        outcome = "PASS"
    except BaseException as exc:
        outcome = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, KeyboardInterrupt, subprocess.SubprocessError)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    custody = {"changed_files": [], "unreadable_files": [], "changed_git": [], "changed_environments": []}
    try:
        for name, pin in protected.items():
            try:
                if info(name) != pin:
                    custody["changed_files"].append(name)
            except OSError as exc:
                custody["unreadable_files"].append({"path": name, "error": repr(exc)})
        custody["git_after"] = {name: git_state(Path(name)) for name in states}
        custody["changed_git"] = [name for name in states if states[name] != custody["git_after"][name]]
        env_after = {executable: inventory(executable) for executable in inventories}
        save(RUN / "environment_after.json", env_after)
        custody["changed_environments"] = [name for name in inventories if inventories[name] != env_after[name]]
        custody["active_workers"] = active_workers()
        custody["cleanup_problems"] = [c for c in commands if not c["child_reaped"] or c["cleanup_errors"]]
        custody["Status"] = ("FAIL" if any(custody[k] for k in ("changed_files", "changed_git", "changed_environments")) else
                             "BLOCKED" if any(custody[k] for k in ("unreadable_files", "active_workers", "cleanup_problems")) else
                             "PASS" if baseline_complete else "NOT TESTED")
    except BaseException as exc:
        custody.update(Status="BLOCKED", error=repr(exc))
    if custody["Status"] == "FAIL":
        outcome = "FAIL"
    elif custody["Status"] != "PASS" and outcome == "PASS":
        outcome = "BLOCKED"
    save(RUN / "custody.json", custody)
    try:
        save(RUN / "resources_after.json", resources())
    except OSError as exc:
        save(RUN / "resources_after.json", {"Status": "BLOCKED", "error": repr(exc)})
    # Re-read an interrupted worker's partial completion for an honest checkpoint.
    for mode in ("worker", "reload"):
        path = RUN / mode / "public/completion.json"
        if path.is_file():
            try:
                if mode == "worker":
                    main_completion = json.loads(path.read_text())
                else:
                    reload_completion = json.loads(path.read_text())
            except (OSError, ValueError):
                pass
    progress=evidence_progress(RUN)
    report = {"Purpose": "Residual MoDA history attention versus frozen fixed32, with current-sequence attention adaptation control",
              "Environment": {"model_python": PYTHON, "audit_python": DATA_PYTHON, "mode": "CPU FP32;2 intra/1 inter; existing dependencies"},
              "Input": {"base": BASE, "execution_freeze": args.expected_head, "data": str(INPUTS)},
              "Expected": "128 optimizer steps;293 main calls;4 new-process reload calls; full32 gradients; base unchanged; independent audit",
              "Actual": {"main_completion": main_completion, "reload_completion": reload_completion,
                         "scientific_screens": scientific, "operator_checks": checks, "commands": commands, "custody": custody,
                         "evidence_progress":progress},
              "Status": outcome, "error": error, "formal_launch_attempted": any(c["label"] == "train" for c in commands),
              "scientific_screens": scientific, "FORMAL_ACCEPTANCE_READY": False, "Formal_Oracle": "BLOCKED/NOT_READY", "utc": utc()}
    save(RUN / "summary.json", report)
    print("STATUS: " + outcome + "\nEVIDENCE: " + str(RUN), flush=True)
    try:
        quiescence = active_workers()
        check_publish = not quiescence and all(c["child_reaped"] and not c["cleanup_errors"] for c in commands)
        save(RUN / "publication_quiescence.json", {"Status": "PASS" if check_publish else "BLOCKED", "active_workers": quiescence})
        if not freeze_ok or not check_publish or git_state(REPO) != {"head": args.expected_head, "status": ""}:
            raise RuntimeError("Unsafe to publish automatically; original external evidence retained")
        if git(REPO,"ls-remote","origin","refs/heads/"+BRANCH).split()[0] != args.expected_head:
            raise RuntimeError("Remote execution-freeze lease changed; evidence preserved")
        final_public_bytes=sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file() and public_path(p.relative_to(RUN)))
        if shutil.disk_usage(RUN).free < final_public_bytes+FINALIZATION_ALLOWANCE+DISK_RESERVE:
            raise RuntimeError("Insufficient publication space while retaining256MiB reserve; external evidence preserved")
        exported = ROOT / "evidence"
        exported.mkdir(exist_ok=False)
        copies = []
        for path in sorted(RUN.rglob("*")):
            if path.is_file() and public_path(path.relative_to(RUN)):
                relative = path.relative_to(RUN)
                dest = exported / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                copies.append(str(relative))
        save(ROOT / "PUBLIC_EXPORT.json", {"files": copies, "raw_logits_or_adapters_exported": False,
             "input_tokens_or_source_text_exported": False, "policy": "Root reports/logs and worker/reload public JSON only"})
        save(ROOT / "EXTERNAL_EVIDENCE_MANIFEST.json", {str(p): info(p) for p in sorted(RUN.rglob("*")) if p.is_file()})
        checkpoint = ("# " + EXPERIMENT + " checkpoint\n\nEngineering Status: **" + outcome + "**.\n\n"
            "Base: `" + BASE + "`. Execution freeze: `" + args.expected_head + "`. Branch: `" + BRANCH + "`.\n\n"
            "Purpose: test fixed32 residual MoDA history attention against native frozen fixed32; current-sequence attention is a secondary adaptation control. "
            "Environment: existing CPU FP32 runtime, Python3.12.3/Torch2.11.0+cpu,2 intra-op/1 inter-op threads; no GPU or dependency change.\n\n"
            "Input: frozen16 training and16 evaluation articles,129 tokens each, reused from the LoRA development benchmark; not a fresh generalization test. Both trained arms have12288 output-projection parameters. Two training seeds;32 steps each per trained arm. "
            "Expected/Actual: see evidence/summary.json, worker/public/completion.json, reload/public/completion.json and audit.json. "
            "Missing stages remain NOT TESTED. Command exit alone is not an acceptance criterion.\n\n"
            "Scientific screens: " + json.dumps(scientific, ensure_ascii=False) + ". These are exploratory local quality screens, not population confirmation. "
            "Screen FAIL is a valid negative result and is separate from engineering execution failure.\n\n"
            "Raw evidence: `" + str(RUN) + "`; EXTERNAL_EVIDENCE_MANIFEST.json binds raw files at seal. "
            "Git holds public reports and manifests. Actual retained audit and disposal progress: " + json.dumps(progress,ensure_ascii=False) + ". "
            "Unreached rows remain NOT TESTED. Only completed PASS row audits support a full-live-audit statement. "
            "Historical F32 files are retained in the old run; completed new sentinels are retained here. "
            "Compact statistics/hashes do not permit retrospective full-logit re-audit for any successfully discarded nonsentinel candidate rows. "
            "Adapter checkpoints and original data remain external. publication.json is a later receipt outside that seal.\n\n"
            "Custody: " + custody["Status"] + ". Old evidence, upstream, base weights and early-stop controller/threshold retained. "
            "No B1 rerun/A5 relaxation/B2/D2-A/PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n"
            "Unresolved: " + ("limited output-projection adaptation, memory-path capacity versus compute, frozen random feature conditioning, pretraining overlap and generalization" if outcome == "PASS" else json.dumps(error or custody, ensure_ascii=False)) + "\n\n"
            "Next unique instruction: review this checkpoint and independent audit; preserve all results without tuning. "
            "On BLOCKED/FAIL resolve only its recorded cause in a separately frozen continuation. No retry or automatic mechanism stacking.\n")
        with (ROOT / "CHECKPOINT.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(checkpoint)
        paths = [exported, ROOT / "CHECKPOINT.md", ROOT / "EXTERNAL_EVIDENCE_MANIFEST.json", ROOT / "PUBLIC_EXPORT.json"]
        subprocess.run(["git", "-C", str(REPO), "add", "-f", "--", *map(str, paths)], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", "Record residual-MoDA CPU pilot checkpoint: " + outcome], check=True)
        subprocess.run(["git", "-C", str(REPO), "push", "origin", BRANCH], check=True, timeout=120)
        head = git(REPO, "rev-parse", "HEAD")
        remote = git(REPO, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0]
        if head != remote or git_state(REPO)["status"]:
            raise RuntimeError("Publication remote/clean verification failed")
        save(RUN / "publication.json", {"Status": "PASS", "head": head, "remote": remote, "branch": BRANCH})
        print("CHECKPOINT PUSHED: " + head, flush=True)
    except BaseException as exc:
        save(RUN / "publication.json", {"Status": "BLOCKED", "error": repr(exc), "experiment_status": outcome})
        print("CHECKPOINT PUBLICATION BLOCKED: " + repr(exc) + "; external evidence preserved", flush=True)
        return 2
    return 0 if outcome == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
