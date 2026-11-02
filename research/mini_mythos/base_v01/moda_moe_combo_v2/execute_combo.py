"""One admitted CPU combination attempt; preserve old scope and publish evidence."""
from __future__ import annotations
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

BASE = "d09d54953ff2725b702338d44e663088eeca0e69"
V7_FREEZE = "6a87446f8a146f62cae30ae75f986d2b30d30f60"
BRANCH = "mythos-moda-moe-combo-cpu-v2"
REPO = Path("/workspaces") / BRANCH
REL = "research/mini_mythos/base_v01/moda_moe_combo_v2"
ROOT = REPO / REL
OLD = Path("/workspaces/mythos-moda-fresh-cpu-v1")
OLD_REL = "research/mini_mythos/base_v01/moda_fresh_v1"
OLD_ROOT = OLD / OLD_REL
PREP = Path("/workspaces/mythos-evidence/base_v01/moda_moe_combo/preparation-v2")
RUN = Path("/workspaces/mythos-evidence/base_v01/moda_moe_combo/attempt-v2")
OUTER_LOG = Path("/workspaces/mythos-moda-moe-combo-v2.log")
PREVIOUS_REPO = Path("/workspaces/mythos-moda-moe-combo-cpu-v1")
PREVIOUS_REL = "research/mini_mythos/base_v01/moda_moe_combo_v1"
PREVIOUS_HEAD = "0f6c49fb095deab8b75ef3d140b76c76a701c35a"
PREVIOUS_RUN = Path("/workspaces/mythos-evidence/base_v01/moda_moe_combo/attempt-v1")
PREVIOUS_LOG = Path("/workspaces/mythos-moda-moe-combo-v1.log")
SCIENTIFIC_PINS = {"combo_model.py":"9152698084fcaf51e0d89aceaa5d0fa870a047f5149772c4bc9dbb6cb6dd7775",
                   "run_combo.py":"a29b6697c71bfecd1cec444e02fcb062182cb154c81986729672465d94375b56",
                   "audit_combo.py":"5fad2fa29b9780a7afa66f9a76652a570ed6ba268534f4ca115b7808aebb483e",
                   "test_combo_model.py":"1a0e9de53e5ea520946575223774708569072b3ff7d2c439025e747edd1e527a",
                   "test_audit_combo.py":"5391a24cbd7f18898b1e188757dd48a1138e70b2e2d875ee508f6fb0f250d5ce"}
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
AUDIT_PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
ENV = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1",
       "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
       "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
META, RAW, RESERVE, GIT_ALLOWANCE = 64 * 1024**2, 8388608, 256 * 1024**2, 16 * 1024**2
MAIN_EXPECTED = dict(model_loads=1, calls_started=783, calls_completed=783, identity_calls=7,
                     train_steps=128, backward_calls=128, optimizer_steps=128, quality_rows=648, full_matrix_audits=648)
RELOAD_EXPECTED = dict(model_loads=1, calls_started=9, calls_completed=9, reload_rows=9, full_matrix_audits=9)
OPERATOR_SHA = "72829d632e2699529f68046dca9b8ec8cb5826c5ce35512da374f30f569624b1"


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def sha(b): return hashlib.sha256(b).hexdigest()


def info(p):
    h, n = hashlib.sha256(), 0
    with Path(p).open("rb") as s:
        for b in iter(lambda: s.read(1048576), b""):
            h.update(b)
            n += len(b)
    return dict(bytes=n, sha256=h.hexdigest())


def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith(".gz") else b)


def bounded_protected_map(path, receipt):
    if info(path) != receipt["physical"]:
        raise Stop("FAIL", "Protected manifest physical pin")
    with gzip.open(path, "rb") as stream:
        raw = stream.read(64 * 1024**2 + 1)
    if len(raw) > 64*1024**2 or dict(bytes=len(raw), sha256=sha(raw)) != receipt["canonical"]:
        raise Stop("FAIL", "Protected manifest canonical pin/expansion")
    def unique_pairs(items):
        result = {}
        for k, value in items:
            if k in result: raise Stop("FAIL", "Duplicate physical protected path")
            result[k] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique_pairs)
    if not isinstance(value, dict) or len(value) != receipt["records"]:
        raise Stop("FAIL", "Protected manifest complete count")
    return value


def effective_memory(meminfo, maximum=None, current=None):
    host = int(dict(line.split(":", 1) for line in meminfo.splitlines())["MemAvailable"].split()[0])*1024
    limit = None if maximum in (None, "max") else int(maximum)
    used = None if current is None else int(current)
    return min(host, max(0, limit-used)) if limit is not None and used is not None else host


def save(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    b = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    if str(p).endswith(".gz"): b = gzip.compress(b, compresslevel=9, mtime=0)
    if shutil.disk_usage(p.parent).free < len(b) + RESERVE:
        raise Stop("BLOCKED", "Reserve unavailable for evidence write")
    with p.open("xb") as s: s.write(b)


def git(tree, *a): return subprocess.check_output(["git", "-C", str(tree), *a], timeout=120).decode().strip()


def git_state(tree):
    return dict(head=git(tree, "rev-parse", "HEAD"), status=git(tree, "status", "--porcelain=v1", "--untracked-files=all"))


def old_operator():
    p = OLD_ROOT / "execute_once_v7.py"
    if info(p)["sha256"] != OPERATOR_SHA: raise Stop("FAIL", "Original V7 operator byte binding")
    codec = OLD_ROOT / "storage_codec.py"
    if info(codec)["sha256"] != "f6a0be70d911b3f0c0f5de1b2e30c4513aba2a169e6af6e1f3ea7b589d1e01d7":
        raise Stop("FAIL", "Original storage codec byte binding")
    sys.path.insert(0, str(OLD_ROOT))
    spec = importlib.util.spec_from_file_location("inherited_frozen_moda_operator", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def prior_scope_closure(protected, original):
    """All prior physical paths persist; committed pointer changes are explicit."""
    changes = []
    prefix = str(OLD) + "/"
    for path, before in original.items():
        if path not in protected:
            raise Stop("FAIL", "Missing prior V7 protected path: " + path)
        now = protected[path]
        if now == before: continue
        if not path.startswith(prefix):
            raise Stop("FAIL", "Old evidence outside published source changed: " + path)
        rel = path[len(prefix):]
        a = subprocess.check_output(["git", "-C", str(OLD), "show", V7_FREEZE + ":" + rel], timeout=120)
        b = subprocess.check_output(["git", "-C", str(OLD), "show", BASE + ":" + rel], timeout=120)
        if before != dict(bytes=len(a), sha256=sha(a)) or now != dict(bytes=len(b), sha256=sha(b)):
            raise Stop("FAIL", "Unpublished source drift: " + path)
        changes.append(dict(path=path, prior=before, current=now, committed_from=V7_FREEZE, committed_to=BASE))
    return dict(original_paths=len(original), all_paths_retained=True, immutable_paths_unchanged=len(original)-len(changes),
                exact_published_source_advances=changes)


def committed_previous(relative):
    return subprocess.check_output(["git", "-C", str(PREVIOUS_REPO), "show", PREVIOUS_HEAD+":"+PREVIOUS_REL+"/"+relative], timeout=120)


def anchored_previous(relative):
    raw = committed_previous("evidence/"+relative)
    if (PREVIOUS_RUN/relative).read_bytes() != raw:
        raise Stop("FAIL", "Closed prior run differs from committed blob: "+relative)
    # Bind compressed bytes first; protected-map expansion is checked only by
    # bounded_protected_map below, never an unbounded gzip.decompress here.
    if relative.endswith(".gz"):
        if len(raw) > 4*1024**2: raise Stop("BLOCKED", "Prior complete map physical envelope")
        return raw
    return json.loads(raw)


def previous_gate():
    if git_state(PREVIOUS_REPO) != dict(head=PREVIOUS_HEAD, status=""):
        raise Stop("BLOCKED", "Prior failed attempt checkout drift")
    summary, custody = anchored_previous("summary.json"), anchored_previous("custody.json")
    if summary["Status"] != "FAIL" or summary["error"]["reason"] != "Complete target test inventory startup" or summary["Actual"]["main"] is not None:
        raise Stop("FAIL", "Continuation is only for recorded startup-fixture stop before any model")
    if custody["Status"] != "PASS" or any(custody[k] for k in ("changed_files", "unreadable_files", "changed_git", "changed_environments", "active_workers", "cleanup_errors")):
        raise Stop("FAIL", "Full previous closure/custody not established")
    publication = read(PREVIOUS_RUN/"publication.json")
    if publication.get("Status") != "PASS" or publication.get("head") != PREVIOUS_HEAD or publication.get("remote") != PREVIOUS_HEAD:
        raise Stop("BLOCKED", "Prior publication not closed")
    if not PREVIOUS_LOG.is_file(): raise Stop("BLOCKED", "Required previous operator log")
    for name, digest in SCIENTIFIC_PINS.items():
        raw = committed_previous(name)
        if sha(raw) != digest or info(ROOT/name)["sha256"] != digest:
            raise Stop("FAIL", "Unchanged scientific implementation/test required: "+name)
    return summary


def merge_expected(expected, source):
    for path, value in source.items():
        p = Path(path)
        if not p.is_absolute() or ".." in p.parts or str(p) != path:
            raise Stop("FAIL", "Noncanonical protected pathname: "+path)
        if path in expected and expected[path] != value:
            raise Stop("FAIL", "Conflicting prior source pins: "+path)
        expected[path] = value


def hash_paths(paths, expected=None, label="protection", workers=4):
    """Hash every distinct pathname once. Different paths never deduplicate."""
    paths = sorted(set(map(str, paths)))
    validate_parent_paths(paths)
    expected = expected or {}
    result = {}
    def calculate(path):
        p = Path(path)
        if not p.is_absolute() or ".." in p.parts or str(p) != path:
            raise Stop("FAIL", "Noncanonical protected pathname: "+path)
        if p.is_symlink(): raise Stop("BLOCKED", "Protected leaf symlink: "+path)
        value = info(p)
        if path in expected and expected[path] != value:
            raise Stop("FAIL", "Protected input bytes changed: "+path)
        return path, value
    # At most four in-flight file reads. Do not queue the entire history after
    # the first failed future; propagate its error and join the in-flight reads.
    iterator = iter(paths)
    pool = ThreadPoolExecutor(max_workers=workers)
    pending = set()
    try:
        for _ in range(workers):
            path = next(iterator, None)
            if path is not None: pending.add(pool.submit(calculate, path))
        while pending:
            completed, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                path, value = future.result()
                result[path] = value
            for _ in completed:
                path = next(iterator, None)
                if path is not None: pending.add(pool.submit(calculate, path))
            if len(result) % 1000 < len(completed) or len(result) == len(paths):
                print(json.dumps(dict(phase=label, verified_paths=len(result), expected_paths=len(paths),
                                      verified_bytes=sum(v["bytes"] for v in result.values()))), flush=True)
    finally:
        for future in pending: future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)
    if len(result) != len(paths): raise Stop("FAIL", "Incomplete protected path traversal")
    return result


def validate_parent_paths(paths):
    parents = sorted({str(parent) for path in paths for parent in Path(path).parents})
    for parent in parents:
        if Path(parent).is_symlink():
            raise Stop("BLOCKED", "Protected directory symlink ambiguity: "+parent)
    return dict(ancestor_directories=len(parents), ancestor_names_sha256=sha(json.dumps(parents,separators=(",", ":")).encode()),
                directory_symlinks=0, checked=True)


def collect(states, inherited):
    previous_gate()
    receipt = anchored_previous("protected_receipt.json")
    anchored_previous("protected_before.json.gz")
    previous = bounded_protected_map(PREVIOUS_RUN/"protected_before.json.gz", receipt)
    expected = {}
    merge_expected(expected, previous)
    # All required older maps are subsets of the anchored complete V1 map;
    # verify that fact with their original byte-bound decoder, not reported counts.
    old = inherited.storage_codec.read_manifest(inherited.PRIOR_PROTECTED, read(inherited.PRIOR_RECEIPT))
    older = read(inherited.PRIOR_V1)
    for scope in (old, older):
        for p, value in scope.items():
            if previous.get(p) != value: raise Stop("FAIL", "Old protection scope reduced in inherited manifest: "+p)
    inherited_paths = json.loads(committed_previous("EXTERNAL_EVIDENCE_MANIFEST.json"))
    merge_expected(expected, inherited_paths)
    paths = set(expected)
    for name in states:
        tree = Path(name)
        rels = git(tree, "ls-files", "-z").split("\0")
        if tree == inherited.MAIN_TREE:
            rels += git(tree, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
        for rel in rels:
            p = tree/rel
            if rel and (p.is_file() or p.is_symlink()): paths.add(str(p))
    # Discover all new prior run/receipt files while leaving this attempt's
    # mutable output namespace out of its own immutable input inventory.
    base = Path("/workspaces/mythos-evidence/base_v01")
    for p in base.rglob("*"):
        if p == RUN or p.is_relative_to(RUN): continue
        if p.is_file() or p.is_symlink(): paths.add(str(p))
    paths.update((str(PREVIOUS_LOG), str(Path("/workspaces/mythos-moda-model-v7.log"))))
    protected = hash_paths(paths, expected, "protection_before")
    if any(protected.get(p) != value for p, value in previous.items()): raise Stop("FAIL", "Full prior physical scope/pins must persist")
    return protected, dict(previous_head=PREVIOUS_HEAD, previous_paths=len(previous), current_paths=len(protected),
                           all_previous_paths_and_pins_unchanged=True, original_v1_paths=len(older), original_v2_paths=len(old),
                           same_path_hash_once=True, different_paths_never_deduplicated=True, io_workers=4,
                           prior_custody="PASS", inherited_old_source_advances=anchored_previous("protected_scope.json"))


def validate_count_report(value, expected):
    return value.get("Status") == "PASS" and value.get("preservation") == "PASS" and value.get("Actual") == expected


def valid_helper_report(value, inventory):
    actual = value.get("Actual", {})
    ids = inventory["test_ids"]
    if value.get("Status") != "PASS" or not ids or len(ids) != len(set(ids)):
        return False
    if actual.get("run") != len(ids) or actual.get("planned") != len(ids) or actual.get("test_ids") != ids:
        return False
    for key in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes"):
        observed = actual.get(key)
        if isinstance(observed, list):
            if observed: return False
        elif type(observed) is int:
            if observed != 0: return False
        else:
            return False
    return True


def inherited_suite(name, inventory, environments):
    if name not in ("model", "audit"):
        raise Stop("FAIL", "Only unchanged complete source-math suites inherit")
    report = anchored_previous(name+".json")
    if not valid_helper_report(report, inventory): raise Stop("FAIL", "Previous complete helper inventory: "+name)
    previous_summary = anchored_previous("summary.json")
    commands = [c for c in previous_summary["Actual"]["commands"] if c["label"] == name]
    if len(commands) != 1 or commands[0]["returncode"] != 0 or not commands[0]["child_reaped"] or commands[0]["cleanup_errors"] or commands[0]["argv"][0] != PYTHON:
        raise Stop("FAIL", "Actual previous target helper process proof: "+name)
    if anchored_previous("environment_after.json") != environments or anchored_previous("environment_before.json") != environments:
        raise Stop("BLOCKED", "Source readiness cannot inherit changed dependency environment")
    if name == "model":
        env, inputs = report["Environment"], report["Input"]
        if env.get("executable") != PYTHON or not env["python"].startswith("3.12.3 ") or env.get("torch") != "2.11.0+cpu":
            raise Stop("FAIL", "Actual target model-helper environment")
        expected = dict(source_sha256="335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492",
                        moda_library_sha256="a52005f273e2ec8f467375e9ee506ae7d622cc97e0570c92863b5087014b3912",
                        model_source_sha256=SCIENTIFIC_PINS["combo_model.py"], test_source_sha256=SCIENTIFIC_PINS["test_combo_model.py"])
        if any(inputs.get(k) != v for k,v in expected.items()) or inputs.get("real_model_loads") != 0:
            raise Stop("FAIL", "Previous model-helper source/weights boundary")
    else:
        if report["Environment"].get("numpy") != "1.26.4" or not report["Environment"]["python"].startswith("3.12.3 "):
            raise Stop("FAIL", "Previous numerical-helper target environment")
        for filename in ("audit_combo.py", "test_audit_combo.py"):
            if report["Input"]["source_pins"][filename] != info(ROOT/filename):
                raise Stop("FAIL", "Numerical helper source pin changed: "+filename)
    return dict(Purpose="Inherit byte-identical completed target source readiness, without rerunning or relabeling", Status="PASS",
                Input=dict(previous_commit=PREVIOUS_HEAD, suite=name), Expected=dict(complete_test_ids=inventory["test_ids"]),
                Actual=dict(previous_test_count=report["Actual"]["run"], new_test_processes=0, environment_unchanged=True,
                            committed_report_sha256=sha(committed_previous("evidence/"+name+".json")), inherited=True))


def public_path(relative):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or "private" in p.parts: return False
    if len(p.parts) == 1:
        return p.suffix in (".json", ".stdout", ".stderr") or p.name.endswith(".json.gz")
    return len(p.parts) >= 3 and p.parts[0] in ("worker", "reload") and p.parts[1] == "public"


def publication_budget(root):
    files = [p for p in Path(root).rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    raw = sum(p.stat().st_size for p in files if p.name in ("final_sentinel.bin", "failed_scored_logits.bin"))
    public = sum(p.stat().st_size for p in files if public_path(p.relative_to(root)))
    free = shutil.disk_usage(root).free
    preparation = sum(p.stat().st_size for p in PREP.rglob("*") if p.is_file()) if PREP.exists() else 0
    outer = OUTER_LOG.stat().st_size if OUTER_LOG.is_file() else 0
    value = dict(run_bytes=total, raw_bytes=raw, public_copy_bytes=public, git_finalization_allowance=GIT_ALLOWANCE,
                 preparation_bytes=preparation, outer_operator_stdout_bytes=outer,
                 projected_nonraw_bytes=total-raw+public+preparation+outer+GIT_ALLOWANCE, free_bytes=free)
    if raw > RAW or value["projected_nonraw_bytes"] > META or free < public+GIT_ALLOWANCE+RESERVE:
        raise Stop("BLOCKED", "Actual evidence/publication budget exceeded")
    return value


def public_argv(args):
    result = list(args)
    for i, value in enumerate(args[:-1]):
        if value == "--targets-json": result[i+1] = "REDACTED_SHA256:"+sha(args[i+1].encode())
    return result


def active_workers():
    names = {"run_combo.py", "audit_combo.py", "execute_combo.py", "execute_once.py", "execute_once_v6.py", "execute_once_v7.py",
             "measure_storage_v7.py", "source_feasibility_v6.py", "prepare_history_v6.py", "audit_history_v6.py", "measure_storage_v6.py",
             "run_fresh.py", "audit_stream.py", "run_moda.py", "audit_moda.py", "audit_row.py", "run_lora.py", "audit_lora.py",
             "run_loop.py", "run_quality.py", "run_routing.py", "run_depth_budget.py", "acceptance_review.py", "prepare_once.py",
             "prepare_once_v2.py", "prepare_once_v4.py", "prepare_once_v5.py", "data_prepare.py", "audit_data.py"}
    found = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit() or int(d.name) == os.getpid(): continue
        try:
            args = (d/"cmdline").read_bytes().split(b"\0")
            # Exact executed script arguments; do not match our text command or
            # unrelated terminal names containing an experiment string.
            if any(Path(os.fsdecode(a)).name in names for a in args[1:] if a):
                found.append(dict(pid=int(d.name), argv=public_argv([os.fsdecode(a) for a in args if a])))
        except (OSError, ValueError): pass
    return found


def validate_source_manifest(root):
    manifest = read(Path(root)/"SOURCE_MANIFEST.json")
    if not manifest or not isinstance(manifest, dict): raise Stop("FAIL", "Nonempty source manifest required")
    for rel, value in manifest.items():
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or not (Path(root)/p).is_file() or (Path(root)/p).is_symlink(): raise Stop("FAIL", "Source path invalid")
        if info(Path(root)/p) != value: raise Stop("FAIL", "Frozen source differs: " + rel)
    return manifest


def build_spec(freeze):
    s = read(OLD_ROOT/"evidence_v7/spec.json")
    s.update(repo=str(REPO), freeze_commit=freeze, expected_head=freeze, base_commit=BASE, branch=BRANCH,
             run_root=str(RUN), audit_python=AUDIT_PYTHON, loader=str(OLD_ROOT/"run_fresh.py"),
             v7_evaluation_path=str(Path(s["run_root"])/"worker/public/evaluation.json.gz"))
    s["wiki_data"] = dict(path=s["old_data_path"], pin=info(s["old_data_path"]))
    s["news_data"] = dict(path=s["data_path"], pin=info(s["data_path"]))
    return s


def command(label, argv, timeout, commands):
    entry = dict(label=label, argv=argv, timeout_seconds=timeout, child_reaped=False, cleanup_errors=[])
    commands.append(entry)
    started = time.perf_counter()
    with (RUN/(label+".stdout")).open("xb") as stdout, (RUN/(label+".stderr")).open("xb") as stderr:
        process = None
        try:
            process = subprocess.Popen(argv, cwd=REPO, env={**os.environ, **ENV}, stdout=stdout, stderr=stderr, start_new_session=True)
            entry["pid"] = process.pid
            entry["returncode"] = process.wait(timeout=timeout)
        except BaseException as exc:
            entry["exception"] = repr(exc)
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=20)
                except BaseException:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    try: process.wait(timeout=10)
                    except BaseException as e: entry["cleanup_errors"].append(repr(e))
            entry["returncode"] = process.poll() if process else None
            raise Stop("BLOCKED", "Child command interrupted/timed out: " + label) from exc
        finally:
            entry["child_reaped"] = process is None or process.poll() is not None
            entry["seconds"] = time.perf_counter()-started
    return entry["returncode"]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--expected-head", required=True)
    args = cli.parse_args()
    if RUN.exists(): raise SystemExit("Attempt already exists; no repeat")
    RUN.mkdir(parents=True)
    checks, commands, protected, environments, states = [], [], {}, {}, {}
    custody, status, error, inherited = {}, "NOT TESTED", None, None
    main_report = reload_report = final_audit = None
    def interrupted(signum, frame): raise Stop("BLOCKED", "Operator interrupted by signal "+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    def check(label, condition, failure="FAIL"):
        checks.append(dict(Purpose=label, Expected=True, Actual=bool(condition), Status="PASS" if condition else failure))
        if not condition: raise Stop(failure, label)
    try:
        check("Designated isolated CPU operator", os.environ.get("CODESPACE_NAME") == "bookish-pancake-vwqx7rr9x5w3wxjr"
              and platform.python_version() == "3.12.3" and sys.executable == PYTHON and sys.flags.isolated and sys.dont_write_bytecode, "BLOCKED")
        check("Execution freeze shape", re.fullmatch("[0-9a-f]{40}", args.expected_head) is not None)
        check("Clean exact experiment branch", git_state(REPO) == dict(head=args.expected_head, status="") and git(REPO, "branch", "--show-current") == BRANCH)
        check("Remote freeze lease", git(REPO, "ls-remote", "origin", "refs/heads/"+BRANCH).split()[0] == args.expected_head)
        validate_source_manifest(ROOT)
        check("Latest accepted original experiment", git_state(OLD) == dict(head=BASE, status=""))
        check("No concurrent experiment worker", not active_workers(), "BLOCKED")
        restored = read(PREP/"restore.json")
        check("Real target source/input recovery", restored["Status"] == "PASS" and restored["Actual"]["model_calls"] == 0)
        for p, value in restored["Actual"]["pins"].items(): check("Restore pin " + p, info(p) == value)
        meminfo = Path("/proc/meminfo").read_text()
        maximum = Path("/sys/fs/cgroup/memory.max").read_text().strip() if Path("/sys/fs/cgroup/memory.max").exists() else None
        current = Path("/sys/fs/cgroup/memory.current").read_text().strip() if Path("/sys/fs/cgroup/memory.current").exists() else None
        check("Cgroup memory budget available", maximum is not None and current is not None, "BLOCKED")
        resources = dict(mem_available_bytes=effective_memory(meminfo, maximum, current), memory_max=maximum, memory_current=current, meminfo=meminfo, disk_free_bytes=shutil.disk_usage(REPO).free,
                         cpu=Path("/proc/cpuinfo").read_text(), loadavg=Path("/proc/loadavg").read_text(), limits=dict(raw=RAW, metadata=META, reserve=RESERVE, git_allowance=GIT_ALLOWANCE))
        save(RUN/"resources.json", resources)
        check("At least4GiB available memory", resources["mem_available_bytes"] >= 4*1024**3, "BLOCKED")
        check("Whole frozen disk allocation available", resources["disk_free_bytes"] >= RAW+META+RESERVE, "BLOCKED")
        inherited = old_operator()
        previous_gate()
        states = {p: git_state(p) for p in (str(REPO), str(PREVIOUS_REPO), str(OLD), str(inherited.OLD_REPO), str(inherited.MAIN_TREE), str(inherited.UPSTREAM))}
        save(RUN/"git_before.json", states)
        environments = {p: inherited.inventory(p) for p in (PYTHON, AUDIT_PYTHON, inherited.OFFICIAL_PYTHON)}
        save(RUN/"environment_before.json", environments)
        protected, coverage = collect(states, inherited)
        save(RUN/"protected_before.json.gz", protected)
        packed = RUN/"protected_before.json.gz"
        check("Full protected map within4MiB", packed.stat().st_size <= 4*1024**2, "BLOCKED")
        canonical = (json.dumps(protected,sort_keys=True,separators=(",", ":"),allow_nan=False)+"\n").encode()
        receipt = dict(records=len(protected), physical=info(packed), canonical=dict(bytes=len(canonical),sha256=sha(canonical)))
        check("Full protected map lossless roundtrip", bounded_protected_map(packed, receipt) == protected)
        save(RUN/"protected_scope.json", coverage)
        save(RUN/"protected_receipt.json", receipt)
        # Format-level size evidence is pre-frozen; all actual phase guards remain.
        forecast = read(ROOT/"EVIDENCE_BUDGET_ATTEMPT3.json")
        check("Pre-frozen complete serialized evidence forecast", forecast["Status"] == "PASS" and forecast["Actual"]["projected_total_nonraw_bytes"] <= META)
        for name, value in read(ROOT/"TEST_INVENTORY.json").items():
            if value.get("inherited"):
                carried = inherited_suite(name, value, environments)
                save(RUN/("inherited_"+name+".json"), carried)
                check("Inherited exact completed target readiness "+name, carried["Status"] == "PASS")
                continue
            report = RUN/(name+".json")
            argv = [PYTHON, "-I", "-B", str(ROOT/value["script"]), "--report", str(report)]
            if value.get("source"):
                argv += ["--source", str(OLD/"open_mythos/moda.py"), "--moda-library", str(inherited.OLD_PACKAGE/"moda_model.py")]
            code = command(name, argv, 600, commands)
            observed = read(report) if report.exists() else {}
            check("Complete target test inventory " + name, code == 0 and valid_helper_report(observed, value))
        spec = build_spec(args.expected_head)
        save(RUN/"spec.json", spec)
        print("Running source MoE native/H CPU training and9-condition evaluation; progress: "+str(RUN/"main.stdout"), flush=True)
        code = command("main", [PYTHON, "-I", "-B", str(ROOT/"run_combo.py"), "--spec", str(RUN/"spec.json"), "--out", str(RUN/"worker")], 7200, commands)
        main_report = read(RUN/"worker/public/completion.json") if (RUN/"worker/public/completion.json").exists() else {}
        check("Main783 calls and128 optimizer steps accepted", code == 0 and validate_count_report(main_report, MAIN_EXPECTED), main_report.get("Status") if main_report.get("Status") in ("BLOCKED", "FAIL") else "BLOCKED" if not main_report and code != 0 else "FAIL")
        publication_budget(RUN)
        code = command("reload", [PYTHON, "-I", "-B", str(ROOT/"run_combo.py"), "--spec", str(RUN/"spec.json"), "--out", str(RUN/"reload"), "--reload"], 600, commands)
        reload_report = read(RUN/"reload/public/completion.json") if (RUN/"reload/public/completion.json").exists() else {}
        check("New process9 exact reload calls accepted", code == 0 and validate_count_report(reload_report, RELOAD_EXPECTED), reload_report.get("Status") if reload_report.get("Status") in ("BLOCKED", "FAIL") else "BLOCKED" if not reload_report and code != 0 else "FAIL")
        code = command("final_audit", [AUDIT_PYTHON, "-I", "-B", str(ROOT/"audit_combo.py"), "--final", "--run-dir", str(RUN), "--spec", str(RUN/"spec.json")], 600, commands)
        final_audit = json.loads((RUN/"final_audit.stdout").read_bytes())
        save(RUN/"audit.json.gz", final_audit)
        check("Independent retained-evidence final numeric audit", code == 0 and final_audit.get("Status") == "PASS")
        check("Exactly one last-reload full raw sentinel", sum(p.stat().st_size for p in RUN.rglob("*.bin")) == RAW)
        save(RUN/"artifact_budget.json", publication_budget(RUN))
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, KeyboardInterrupt, MemoryError, subprocess.SubprocessError)) else "FAIL")
        error = dict(type=type(exc).__name__, reason=str(exc), traceback=traceback.format_exc())
    try:
        custody = dict(changed_files=[], unreadable_files=[], changed_git=[], changed_environments=[], active_workers=active_workers(),
                       cleanup_errors=[c for c in commands if not c["child_reaped"] or c["cleanup_errors"]])
        if protected and bounded_protected_map(RUN/"protected_before.json.gz", read(RUN/"protected_receipt.json")) != protected:
            raise Stop("FAIL", "Full protection map changed before custody close")
        if protected:
            observed = hash_paths(protected, label="protection_after")
            custody["changed_files"] = [p for p,value in protected.items() if observed.get(p) != value]
        custody["git_after"] = {p: git_state(p) for p in states}
        custody["changed_git"] = [p for p in states if states[p] != custody["git_after"][p]]
        env_after = {p: inherited.inventory(p) for p in environments} if inherited else {}
        custody["changed_environments"] = [p for p in environments if environments[p] != env_after[p]]
        save(RUN/"environment_after.json", env_after)
        custody["Status"] = "FAIL" if custody["changed_files"] or custody["changed_git"] or custody["changed_environments"] else "BLOCKED" if custody["unreadable_files"] or custody["active_workers"] or custody["cleanup_errors"] else "PASS" if protected else "NOT TESTED"
        if custody["Status"] == "FAIL": status = "FAIL"
        elif status == "PASS" and custody["Status"] != "PASS": status = "BLOCKED"
    except BaseException as exc:
        custody.update(Status=getattr(exc,"status","BLOCKED"), error=repr(exc))
        if custody["Status"] == "FAIL": status = "FAIL"
        elif status == "PASS": status = "BLOCKED"
    save(RUN/"custody.json", custody)
    report = dict(Purpose="Frozen MoDA/MoE recipe composition CPU pilot", Environment=dict(device="CPU", python=PYTHON, audit_python=AUDIT_PYTHON),
                  Input=dict(base=BASE, freeze=args.expected_head, branch=BRANCH), Expected=dict(main=MAIN_EXPECTED, reload=RELOAD_EXPECTED, total_calls=792),
                  Actual=dict(main=main_report, reload=reload_report, audit_status=final_audit.get("Status") if final_audit else "NOT TESTED", custody=custody,
                              checks=checks, commands=commands), Status=status, error=error,
                  Formal_Oracle="BLOCKED/NOT_READY", FORMAL_ACCEPTANCE_READY=False)
    save(RUN/"summary.json", report)
    print("STATUS: "+status, flush=True)
    try:
        if active_workers() or any(not c["child_reaped"] or c["cleanup_errors"] for c in commands): raise Stop("BLOCKED", "Cannot publish with active workers")
        check("Final clean local freeze", git_state(REPO) == dict(head=args.expected_head, status=""))
        check("Final publication remote lease", git(REPO, "ls-remote", "origin", "refs/heads/"+BRANCH).split()[0] == args.expected_head)
        closing = publication_budget(RUN)
        export = ROOT/"evidence"
        export.mkdir(exist_ok=False)
        copies = []
        for p in sorted(RUN.rglob("*")):
            if p.is_file() and public_path(p.relative_to(RUN)):
                rel = p.relative_to(RUN)
                target = export/rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
                if info(target) != info(p): raise Stop("FAIL", "Public copy byte identity: "+str(rel))
                copies.append(str(rel))
        save(ROOT/"EXTERNAL_EVIDENCE_MANIFEST.json", {str(p): info(p) for p in sorted(RUN.rglob("*")) if p.is_file()})
        save(ROOT/"PUBLIC_EXPORT.json", dict(files=copies, corpus_or_adapter_tensors_exported=False))
        checkpoint = "# MoDA + MoE CPU V2 operational continuation checkpoint\n\nEngineering status: **"+status+"**. Scientific base `"+BASE+"`; prior stopped attempt `"+PREVIOUS_HEAD+"`; execution freeze `"+args.expected_head+"`; branch `"+BRANCH+"`.\n\n"
        checkpoint += "Purpose: source-MoE residual training in native and frozen-MoDA backgrounds, then separate9-condition inference evaluation. Environment: existing designated CPU Python3.12.3/Torch2.11+cpu,2intra/1inter; native and all old adapter weights unchanged. OriginalWiki16train/16eval plus previously exposedAG20 are development/regression sets. No fresh-test or causal routing/combined-training synergy claim.\n\n"
        checkpoint += "Expected792 calls:7 initial full128-position identity controls,128 full32-step BPTT/optimizer calls,648 quality calls,9 new-process reload sentinels. Actual main/reload counters are in evidence/summary.json; scientific screenFAIL is a valid outcome, distinct from engineering failure. Unreached work is NOT TESTED.\n\n"
        checkpoint += "Readiness evidence:35 target source-math checks (17 model/18 audit) are inherited only after exact committed-report/source/test/environment binding; they were not rerun or relabeled as new execution. The corrected startup fixture and new full-scope I/O controls run separately with their frozen current test inventory. All V1 FAIL records and its complete closed protection map remain preserved. Every distinct absolute path is byte-hashed once before and once after this attempt, with4 joined I/O threads only during those protection stages; identical content at different paths is never deduplicated.\n\n"
        checkpoint += "All old physical protection scope retained, with only exact prior committed source-pointer advances documented in protected_scope.json. Custody: "+custody["Status"]+". Evidence external `"+str(RUN)+"`; published compact reports and full-stream audit receipts in evidence/. Only one final8MiB raw sentinel or current failure scored matrix retained; other full matrices are not retrospectively reconstructible. Frozen source input/state/optimizer binaries and corpus IDs remain external.\n\n"
        checkpoint += "Unresolved: "+json.dumps(error or ["Small reused development data", "Prior-H additional training history", "No parameter/compute matched causal routing control", "Only9 reload sentinels, not648 full repeat", "Non-independent AI review", "Independent generalization/statistical confirmation NOT TESTED"])+".\n\n"
        checkpoint += "Scientific results require independent review of final audit and per-domain quality/CPU time; no candidate is promoted on command exit. No upstream edits, A5/controller threshold changes, B1 rerun, B2/D2-A, GPU or PR24 merge. Formal OracleBLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n"
        checkpoint += "Next unique instruction: read and independently reconcile the per-domain evidence; after engineeringPASS, execute the separately frozen zero-training additions of existing depthLoRA/loop-index and then adaptive controller from PROGRAM.md. ScientificFAIL does not itself cancel those registered combinations; BLOCKED/engineeringFAIL stops dependent work with evidence.\n"
        with (ROOT/"CHECKPOINT.md").open("x", encoding="utf-8", newline="\n") as stream: stream.write(checkpoint)
        latest = dict(path=REL+"/CHECKPOINT.md", Status=status, execution_freeze=args.expected_head, expected_model_calls=792, base=BASE)
        save(ROOT/"LATEST_CHECKPOINT.json", latest)
        subprocess.run(["git", "-C", str(REPO), "add", "-f", "--", str(export), str(ROOT/"EXTERNAL_EVIDENCE_MANIFEST.json"), str(ROOT/"PUBLIC_EXPORT.json"), str(ROOT/"CHECKPOINT.md"), str(ROOT/"LATEST_CHECKPOINT.json")], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", "Record isolated MoDA/MoE CPU recipe pilot: "+status], check=True)
        subprocess.run(["git", "-C", str(REPO), "push", "origin", BRANCH], check=True, timeout=120)
        head = git(REPO, "rev-parse", "HEAD")
        remote = git(REPO, "ls-remote", "origin", "refs/heads/"+BRANCH).split()[0]
        if head != remote or git_state(REPO)["status"]: raise Stop("BLOCKED", "Publication remote/clean verification")
        save(RUN/"publication.json", dict(Status="PASS", head=head, remote=remote, postclosure_budget=closing))
        print("CHECKPOINT PUSHED: "+head, flush=True)
    except BaseException as exc:
        save(RUN/"publication.json", dict(Status="BLOCKED", experiment_status=status, error=repr(exc)))
        print("PUBLICATION BLOCKED: "+repr(exc), flush=True)
        return 2
    return 0 if status == "PASS" else 2


if __name__ == "__main__": raise SystemExit(main())
