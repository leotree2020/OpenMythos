#!/usr/bin/env python3
"""
Fault-injection tests of the resumable launcher run_gate_e.py
(PREREGISTRATION 6.6, 12.4, 12.8). Stub jobs only, in temporary test
directories (GATE_E_TEST_DIR / GATE_E_TEST_CMDS): nothing is trained,
diagnosed, evaluated on the formal test set, pushed or committed. Writes
validation/launcher_tests_v3.json (earlier records, kept: launcher_tests_v2.json
and _v2_run1.json for the resumable launcher before the baseline check,
launcher_tests.json and _run1.json for the non-resumable one); exits non-zero
if any case does not end as expected.

Every test directory gets a workload_freeze_v2.json whose baseline is made by
the launcher's own make_baseline. The 12.8 cases that change a file after the
freeze copy the whole code tree (with the preregistration, timing record and
set manifest) to a temporary directory and run that copy's own launcher, so
the code or the manifest is really changed, never the repository's.

Each case checks the exit code, the status log, and the stub call log
(calls.log): which jobs started and finished, so that a skipped, duplicated
or repeated job is visible.
"""

import glob
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

STUB = r'''import glob, json, os, random, shutil, sys, time
D = os.environ["STUB_DIR"]
kind, name = sys.argv[1], sys.argv[2]
def call(msg):
    with open(os.path.join(D, "calls.log"), "a") as f:
        f.write(msg + "\n")
call(f"start {kind} {name}")
if os.environ.get("STUB_FAIL_NAME") == f"{kind}:{name}":
    sys.exit(int(os.environ.get("STUB_FAIL_CODE", "1")))
if kind != "train":  # training stubs write first and then wait, so an interrupted attempt leaves files
    time.sleep(float(os.environ.get("STUB_SLEEP_" + kind.upper(), "0")))
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".stubtmp"
    open(tmp, "w").write(text)
    os.replace(tmp, path)
extra = str(random.random()) if os.environ.get("STUB_NONDET_NAME") == name else ""
if kind == "train":
    _, K, arm, s = name.split("_")
    if K == "K2":
        for t in (0, 25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 4500, 6000, 9000, 12000):
            write(os.path.join(D, "runs", f"K2_{arm}_{s}_step{t}.pt"), f"ckpt {arm} {s} {t}{extra}")
        write(os.path.join(D, "runs", f"K2_{arm}_{s}.json"), "{}")
    else:
        for t in (25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000):
            write(os.path.join(D, "runs", "bridge", f"A_{arm}_{s}_step{t}.pt"), f"bridge {arm} {s} {t}{extra}")
        write(os.path.join(D, "runs", "bridge", f"A_{arm}_{s}.pt"), f"bridge {arm} {s} 3000{extra}")
        write(os.path.join(D, "runs", "bridge", f"A_{arm}_{s}.json"), "{}")
if kind == "train":
    time.sleep(float(os.environ.get("STUB_SLEEP_TRAIN", "0")))
elif kind == "archive":
    _, K, arm, s = name.split("_")
    pat = f"K2_{arm}_{s}_step*.pt" if K == "K2" else os.path.join("bridge", f"A_{arm}_{s}*.pt")
    os.makedirs(os.path.join(D, "remote"), exist_ok=True)
    for f in glob.glob(os.path.join(D, "runs", pat)):
        shutil.copyfile(f, os.path.join(D, "remote", os.path.basename(f)))
elif kind == "restore":
    local = sys.argv[3]
    if os.environ.get("STUB_RESTORE_FAIL") == "1":
        sys.exit(1)
    shutil.copyfile(os.path.join(D, "remote", os.path.basename(local)), local)
elif kind == "diag":
    st = name[5:]
    wl = json.load(open(os.path.join(D, "workload_freeze_v2.json")))["frozen_workload"]
    r = {"state": st, "param_sha256": f"stub-{st}", "workload": wl, "seconds": {"M0": random.random()},
         "M0": {"pass": True}, "M1": {"x": st + extra}, "M2": {}, "M4": {}, "M6": {},
         "M3": {"controls": {"negative_query_swap": {"pass": True}, "positive_own_letter_emb": {"pass": True}}},
         "M5": {"a_tied_split": {"max_check_diff": 0.0}, "seconds": {"a": random.random()}}}
    write(os.path.join(D, "results", st + ".json"), json.dumps(r))
elif kind == "judge":
    out = os.path.join(D, "judgments", sys.argv[3] + ".json")
    if os.path.exists(out):
        sys.exit(3)
    _, arm, s = name.split("_")
    write(out, json.dumps({"arm": arm, "seed": int(s[1:]), "set": "test_heldout", "level": "stub", "main": {}}))
elif kind == "events":
    write(os.path.join(D, "events.json"), "{}")
call(f"done {kind} {name}")
'''

WL_FILE = "workload_freeze_v2.json"


def baseline(here=HERE):
    """The approved baseline as the launcher in `here` computes it (its own
    code tree, preregistration, set manifest and timing record)."""
    e = {k: v for k, v in os.environ.items() if not k.startswith(("GATE_E_TEST", "STUB_"))}
    e["PYTHONPATH"] = os.path.abspath(os.path.join(here, "..", ".."))
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import run_gate_e as r; "
            "print(json.dumps(r.make_baseline(r.paths())))")
    out = subprocess.run(["python", "-c", code, here], env=e, capture_output=True, text=True, check=True,
                         cwd=e["PYTHONPATH"])
    return json.loads(out.stdout)


WL = baseline()


def copy_tree():
    """A complete copy of the frozen code tree with the files of the baseline;
    returns the copy's experiments/gate_e directory."""
    from run_gate_e import CODE_GLOBS

    root = tempfile.mkdtemp(prefix="gate_e_tree_")
    files = {os.path.relpath(f, ROOT) for g in CODE_GLOBS for f in glob.glob(os.path.join(ROOT, g))}
    files |= {"experiments/gate_e/PREREGISTRATION.md", "experiments/gate_e/timing.json",
              "experiments/gate_e/sets/manifest.json"}
    for rel in files:
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(root, rel))
    return os.path.join(root, "experiments", "gate_e")


def setup(workload=None, default=True):
    d = tempfile.mkdtemp(prefix="gate_e_resume_")
    open(os.path.join(d, "stub.py"), "w").write(STUB)
    if workload is None and default:
        workload = WL
    if workload is not None:
        json.dump(workload, open(os.path.join(d, WL_FILE), "w"))
    st = os.path.join(d, "stub.py")
    json.dump({"train": f"python {st} train {{name}}",
               "archive": f"python {st} archive {{name}}",
               "restore": f"python {st} restore restore_{{state}} {{local}}",
               "diag": f"python {st} diag {{name}}",
               "judge": f"python {st} judge {{name}} {{file}}",
               "events": f"python {st} events events",
               "sync": f"python {st} sync {{msg}}"}, open(os.path.join(d, "cmds.json"), "w"))
    return d


def env_for(d, here=HERE, **extra):
    e = dict(os.environ, PYTHONPATH=os.path.abspath(os.path.join(here, "..", "..")), GATE_E_TEST_DIR=d,
             GATE_E_TEST_CMDS=os.path.join(d, "cmds.json"), STUB_DIR=d)
    e.update({k: str(v) for k, v in extra.items()})
    return e


def launch(d, resume=False, here=HERE, **extra):
    """Run the launcher in `here` (the repository's, or a copied tree's)."""
    argv = ["python", os.path.join(here, "run_gate_e.py")] + (["--resume"] if resume else [])
    p = subprocess.run(argv, env=env_for(d, here, **extra), capture_output=True, text=True, timeout=1200)
    return p.returncode, p.stderr


def launch_and_interrupt(d, resume, when, here=HERE, **extra):
    """Start the launcher, send SIGTERM once when(calls) is true."""
    argv = ["python", os.path.join(here, "run_gate_e.py")] + (["--resume"] if resume else [])
    p = subprocess.Popen(argv, env=env_for(d, here, **extra), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                         text=True)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 600:
        if when(calls(d)):
            p.send_signal(signal.SIGTERM)
            break
        time.sleep(0.05)
    p.wait(timeout=120)
    return p.returncode


def calls(d):
    path = os.path.join(d, "calls.log")
    return open(path).read().splitlines() if os.path.exists(path) else []


def status(d):
    path = os.path.join(d, "logs", "run_status.txt")
    return open(path).read() if os.path.exists(path) else ""


def count(d, prefix):
    return sum(1 for c in calls(d) if c.startswith(prefix))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


OWN_SETUP = ("refuse_no_workload", "refuse_m5a", "refuse_no_cap", "first_launch_matches_baseline",
             "code_modified_after_freeze", "native_code_modified_after_freeze", "sets_manifest_modified_after_freeze",
             "code_modified_before_resume", "first_launch_baseline_items")


def run_case(fn):
    d = setup() if fn.__name__ not in OWN_SETUP else None
    try:
        ok, info = fn(d)
    except Exception as err:  # noqa: BLE001
        ok, info = False, {"exception": repr(err)}
    if d:
        info["status_tail"] = status(d).splitlines()[-3:]
        shutil.rmtree(d, ignore_errors=True)
    return fn.__name__, {"pass": bool(ok), **info}


# ------------------------------------------------------------------ cases


def all_succeed(d):
    rc, _ = launch(d)
    ok = rc == 0 and "DONE" in status(d) and "baseline check passed" in status(d)
    ok &= count(d, "done diag") == 280 and count(d, "start diag") == 280
    ok &= count(d, "done judge") == 10 and count(d, "done train") == 16 and count(d, "start sync") > 0
    return ok, {"exit": rc}


def refuse_fresh_when_frozen(d):
    rc0, _ = launch(d)
    rc, err = launch(d)
    return rc0 == 0 and rc == 5 and "--resume" in err, {"exit": rc}


def refuse_resume_without_freeze(d):
    rc, err = launch(d, resume=True)
    return rc == 5 and "without a run freeze" in err, {"exit": rc}


def refuse_nonempty_results(d):
    os.makedirs(os.path.join(d, "results"))
    open(os.path.join(d, "results", "x.json"), "w").write("{}")
    rc, err = launch(d)
    return rc == 5 and "not empty" in err, {"exit": rc}


def refuse_no_workload(_):
    d = setup(default=False)
    rc, err = launch(d)
    shutil.rmtree(d)
    return rc == 5 and "no frozen workload" in err, {"exit": rc}


def refuse_m5a(_):
    w = json.loads(json.dumps(WL))
    w["frozen_workload"]["m5a_bodies"] = 1000
    d = setup(workload=w)
    rc, err = launch(d)
    shutil.rmtree(d)
    return rc == 5 and "M5(a) at 500" in err, {"exit": rc}


def refuse_no_cap(_):
    w = json.loads(json.dumps(WL))
    w.pop("diag_cap_hours")
    d = setup(workload=w)
    rc, err = launch(d)
    shutil.rmtree(d)
    return rc == 5 and "budget cap" in err, {"exit": rc}


def refuse_cmds_without_test_dir(d):
    e = dict(os.environ, PYTHONPATH=ROOT, GATE_E_TEST_CMDS=os.path.join(d, "cmds.json"))
    p = subprocess.run(["python", os.path.join(HERE, "run_gate_e.py")], env=e, capture_output=True, text=True)
    return p.returncode == 5, {"exit": p.returncode}


def training_integrity_failure(d):
    rc, _ = launch(d, STUB_FAIL_NAME="train:train_K2_transformer_s3", STUB_FAIL_CODE=3)
    return rc == 3 and count(d, "start diag") == 0, {"exit": rc}


def archive_failure(d):
    rc, _ = launch(d, STUB_FAIL_NAME="archive:train_K2_openmythos_s2")
    return rc == 3 and "archive of train_K2_openmythos_s2" in status(d) and count(d, "start diag") == 0, {"exit": rc}


def diag_integrity_failure(d):
    rc, _ = launch(d, STUB_FAIL_NAME="diag:diag_K2_openmythos_s2_step300", STUB_FAIL_CODE=3)
    return rc == 3 and count(d, "start judge") == 0, {"exit": rc}


def interrupt_during_diagnostics_then_resume(d):
    """A state recorded in the results ledger before the interruption is never
    run again. A state that finished but was not yet recorded (the launcher had
    not polled it) may run again only through quarantine + re-diagnosis +
    equality with the kept result (12.4.2)."""
    rc1 = launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 40)
    ledgered = set(json.load(open(os.path.join(d, "results_ledger.json"))))
    done_before = {c.split()[2][5:] for c in calls(d) if c.startswith("done diag")}
    rc2, _ = launch(d, resume=True)
    starts = [c.split()[2][5:] for c in calls(d) if c.startswith("start diag")]
    rerun_ledgered = [s for s in ledgered if starts.count(s) > 1]
    rerun_unledgered = [s for s in done_before - ledgered if starts.count(s) > 1]
    st = status(d)
    verified = all(f"re-diagnosed {s} equals the kept result" in st for s in rerun_unledgered)
    ok = rc1 == 130 and rc2 == 0 and not rerun_ledgered and verified and count(d, "done judge") == 10
    ok &= len(json.load(open(os.path.join(d, "results_ledger.json")))) == 280
    return ok, {"exit_first": rc1, "exit_resume": rc2, "ledgered_before_interrupt": len(ledgered),
                "finished_but_unledgered": len(done_before - ledgered), "ledgered_rerun": len(rerun_ledgered),
                "unledgered_rerun_and_verified_equal": len(rerun_unledgered) if verified else "NOT VERIFIED"}


def half_written_result(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 20)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    todo = [s for s in json.load(open(os.path.join(d, "run_freeze.json")))["states"] if s not in led]
    a, b = todo[0], todo[1]
    open(os.path.join(d, "results", f".{a}.json.tmp.999"), "w").write('{"state": "')
    open(os.path.join(d, "results", f"{b}.json"), "w").write('{"state": "' + b + '", "M0": {"pa')  # truncated
    rc, _ = launch(d, resume=True)
    st = status(d)
    ok = rc == 0 and "temporary file of an interrupted write" in st and f"{b}.json" in st and "not parseable" in st
    ok &= os.path.exists(os.path.join(d, "results", f"{b}.json")) and \
        json.load(open(os.path.join(d, "results", f"{b}.json")))["state"] == b
    return ok, {"exit": rc}


def unledgered_valid_result_differs(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 20)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    s = [x for x in json.load(open(os.path.join(d, "run_freeze.json")))["states"] if x not in led][0]
    wl = json.load(open(os.path.join(d, WL_FILE)))["frozen_workload"]
    r = {"state": s, "param_sha256": f"stub-{s}", "workload": wl, "seconds": {}, "M0": {"pass": True},
         "M1": {"x": "SOMETHING ELSE"}, "M2": {}, "M4": {}, "M6": {},
         "M3": {"controls": {"negative_query_swap": {"pass": True}, "positive_own_letter_emb": {"pass": True}}},
         "M5": {"a_tied_split": {"max_check_diff": 0.0}}}
    json.dump(r, open(os.path.join(d, "results", f"{s}.json"), "w"))
    rc, _ = launch(d, resume=True)
    return rc == 3 and f"re-diagnosed {s} differs from the kept result" in status(d), {"exit": rc}


def unledgered_valid_result_equal(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 20)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    s = [x for x in json.load(open(os.path.join(d, "run_freeze.json")))["states"] if x not in led][0]
    wl = json.load(open(os.path.join(d, WL_FILE)))["frozen_workload"]
    r = {"state": s, "param_sha256": f"stub-{s}", "workload": wl, "seconds": {"M0": 123.0}, "M0": {"pass": True},
         "M1": {"x": s}, "M2": {}, "M4": {}, "M6": {},
         "M3": {"controls": {"negative_query_swap": {"pass": True}, "positive_own_letter_emb": {"pass": True}}},
         "M5": {"a_tied_split": {"max_check_diff": 0.0}, "seconds": {"a": 9.0}}}  # timings differ, content equal
    json.dump(r, open(os.path.join(d, "results", f"{s}.json"), "w"))
    rc, _ = launch(d, resume=True)
    return rc == 0 and f"re-diagnosed {s} equals the kept result" in status(d), {"exit": rc}


def ledger_hash_mismatch(d):
    rc0, _ = launch(d)
    s = "K2_openmythos_s1_step300"
    path = os.path.join(d, "results", f"{s}.json")
    r = json.load(open(path))
    r["M1"] = {"x": "tampered"}
    json.dump(r, open(path, "w"))
    before = sha(path)
    n_diag = count(d, "start diag")
    rc, _ = launch(d, resume=True)
    return (rc0 == 0 and rc == 3 and sha(path) == before and count(d, "start diag") == n_diag
            and "differs from its ledger" in status(d)), {"exit": rc}


def checkpoint_restored(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 5)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    s = [x for x in json.load(open(os.path.join(d, "run_freeze.json")))["states"]
         if x not in led and x.startswith("K2_")][0]
    m = json.load(open(os.path.join(d, "checkpoints_manifest.json")))["states"][s]
    os.remove(m["local"])
    rc, _ = launch(d, resume=True)
    return rc == 0 and f"restored {s}" in status(d) and sha(m["local"]) == m["sha256"], {"exit": rc}


def checkpoint_restore_fails(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 5)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    s = [x for x in json.load(open(os.path.join(d, "run_freeze.json")))["states"]
         if x not in led and x.startswith("K2_openmythos")][0]
    m = json.load(open(os.path.join(d, "checkpoints_manifest.json")))["states"][s]
    os.remove(m["local"])
    before = sum(1 for c in calls(d) if c == f"start diag diag_{s}")  # it may have started before the interruption
    rc, _ = launch(d, resume=True, STUB_RESTORE_FAIL=1)
    after = sum(1 for c in calls(d) if c == f"start diag diag_{s}")
    return rc == 3 and f"restore of {s} failed" in status(d) and after == before, \
        {"exit": rc, "starts_before_resume": before, "starts_after_resume": after}


def workload_changed(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 5)
    w = json.load(open(os.path.join(d, WL_FILE)))
    w["frozen_workload"]["m5b_batches"] = 100
    json.dump(w, open(os.path.join(d, WL_FILE), "w"))
    rc, err = launch(d, resume=True)
    return rc == 5 and "workload" in err, {"exit": rc, "refusal": err.strip()[:300]}


def freeze_item_changed(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 5)
    f = json.load(open(os.path.join(d, "run_freeze.json")))
    f["preregistration_sha256"] = "0" * 64
    json.dump(f, open(os.path.join(d, "run_freeze.json"), "w"))
    rc, err = launch(d, resume=True)
    return rc == 5 and "preregistration_sha256" in err, {"exit": rc, "refusal": err.strip()[:300]}


def budget_cap_not_reset(d):
    rc1, _ = launch(d, GATE_E_TEST_DIAG_CAP_SECONDS=1.5, STUB_SLEEP_DIAG=0.4)
    b1 = json.load(open(os.path.join(d, "budget_ledger.json")))["diag_seconds"]
    n1 = count(d, "start diag")
    rc2, _ = launch(d, resume=True, GATE_E_TEST_DIAG_CAP_SECONDS=1.5, STUB_SLEEP_DIAG=0.4)
    b2 = json.load(open(os.path.join(d, "budget_ledger.json")))
    ok = rc1 == 7 and rc2 == 7 and b1 >= 1.5 and b2["diag_seconds"] >= b1 and count(d, "start diag") == n1
    ok &= len(b2["launches"]) == 2 and "BUDGET EXCEEDED" in status(d)
    return ok, {"exit_first": rc1, "exit_resume": rc2, "diag_seconds": b2["diag_seconds"], "states_started": n1}


def repeated_restarts_during_judgment(d):
    rc1 = launch_and_interrupt(d, False, lambda c: sum(x.startswith("done judge") for x in c) >= 3,
                               STUB_SLEEP_JUDGE=0.3)
    rc2 = launch_and_interrupt(d, True, lambda c: sum(x.startswith("done judge") for x in c) >= 6,
                               STUB_SLEEP_JUDGE=0.3)
    rc3, _ = launch(d, resume=True)
    rc4, _ = launch(d, resume=True)  # after DONE: nothing is judged again
    j = json.load(open(os.path.join(d, "judgments_ledger.json")))
    done = [c.split()[2] for c in calls(d) if c.startswith("done judge")]
    ok = rc3 == 0 and rc4 == 0 and len(done) == 10 and len(set(done)) == 10
    ok &= all(v.get("sha256") for v in j.values()) and len(j) == 10
    return ok, {"exits": [rc1, rc2, rc3, rc4], "judgments_written": len(done),
                "attempts": {k: v.get("attempts") for k, v in j.items()}}


def judgment_without_ledger_recovered(d):
    rc0, _ = launch(d)
    jl = json.load(open(os.path.join(d, "judgments_ledger.json")))
    jl["judge_transformer_s4"].pop("sha256")
    json.dump(jl, open(os.path.join(d, "judgments_ledger.json"), "w"))
    n = count(d, "start judge")
    rc, _ = launch(d, resume=True)
    ok = rc0 == 0 and rc == 0 and count(d, "start judge") == n and "recorded, not redone" in status(d)
    return ok, {"exit": rc}


def retrain_after_interruption_equal(d):
    rc1 = launch_and_interrupt(d, False, lambda c: sum(x.startswith("done train") for x in c) >= 6,
                               STUB_SLEEP_TRAIN=0.3)
    victims = unarchived_with_files(d)
    rc2, _ = launch(d, resume=True)
    st = status(d)
    ok = rc1 == 130 and rc2 == 0 and bool(victims) and "unarchived attempt" in st and "equals the kept attempt" in st
    return ok, {"exits": [rc1, rc2], "unarchived_attempts": victims}


def unarchived_with_files(d):
    m = json.load(open(os.path.join(d, "checkpoints_manifest.json")))
    out = []
    for c in calls(d):
        if not c.startswith("start train "):
            continue
        n = c.split()[2]
        _, K, arm, s = n.split("_")
        log = os.path.join(d, "runs", f"K2_{arm}_{s}.json") if K == "K2" else \
            os.path.join(d, "runs", "bridge", f"A_{arm}_{s}.json")
        if n not in m["archived_runs"] and os.path.exists(log):
            out.append(n)
    return out


def retrain_after_interruption_differs(d):
    launch_and_interrupt(d, False, lambda c: sum(x.startswith("done train") for x in c) >= 6, STUB_SLEEP_TRAIN=0.3)
    victims = unarchived_with_files(d)
    if not victims:
        return False, {"note": "no unarchived attempt with files after the interruption"}
    rc, _ = launch(d, resume=True, STUB_NONDET_NAME=victims[0])
    return rc == 3 and "differs from the kept attempt" in status(d), {"exit": rc, "victim": victims[0]}


# ------------------------------------------------- 12.8: the approved freeze baseline


def nothing_started(d):
    return not calls(d) and not os.path.exists(os.path.join(d, "run_freeze.json"))


def in_copied_tree(body):
    """Copy the code tree, write the baseline of the copy (the freeze), then
    run body(d, here); `here` is the copy's experiments/gate_e."""
    here = copy_tree()
    d = setup(workload=baseline(here))
    try:
        return body(d, here)
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(os.path.dirname(os.path.dirname(here)), ignore_errors=True)


def first_launch_matches_baseline(_):
    """Normal first launch: the copy is unchanged after its freeze."""
    def body(d, here):
        b = json.load(open(os.path.join(d, WL_FILE)))["basis"]
        keys = ("code_tree_sha256", "preregistration_sha256", "sets_manifest_sha256", "timing_json_sha256")
        copy_same = all(b[k] == WL["basis"][k] for k in keys)  # the copy is the repository's code
        rc, _ = launch(d, here=here)
        st = status(d)
        f = json.load(open(os.path.join(d, "run_freeze.json")))
        freeze_same = all(f[k] == b[k] for k in keys)
        ok = rc == 0 and copy_same and freeze_same and "baseline check passed" in st and "DONE" in st
        ok &= count(d, "done diag") == 280 and count(d, "done judge") == 10 and count(d, "done train") == 16
        return ok, {"exit": rc, "copy_equals_repository_baseline": copy_same, "run_freeze_equals_baseline": freeze_same,
                    "status": [x for x in st.splitlines() if "baseline check" in x or "DONE" in x]}
    return in_copied_tree(body)


def modified_after_freeze(rel, change, expect, absent=()):
    def body(d, here):
        path = os.path.join(os.path.dirname(os.path.dirname(here)), rel)
        change(path)
        rc, err = launch(d, here=here)
        ok = rc == 5 and "approved freeze baseline" in err and all(x in err for x in expect)
        ok &= not any(x in err for x in absent) and nothing_started(d)
        return ok, {"exit": rc, "changed": rel, "nothing_started": nothing_started(d), "refusal": err.strip()[:500]}
    return in_copied_tree(body)


def append_comment(path):
    with open(path, "a") as f:
        f.write("\n# changed after the freeze\n")


def code_modified_after_freeze(_):
    rel = "experiments/gate_e/e_m3.py"
    return modified_after_freeze(rel, append_comment, ("code_tree_sha256", rel), ("sets_manifest_sha256",))


def native_code_modified_after_freeze(_):
    rel = "open_mythos/main.py"
    return modified_after_freeze(rel, append_comment, ("code_tree_sha256", rel), ("sets_manifest_sha256",))


def sets_manifest_modified_after_freeze(_):
    def change(path):
        m = json.load(open(path))
        m["diag_eval"]["sha256"] = "0" * 64  # as if a set had been regenerated
        json.dump(m, open(path, "w"), indent=1)
    return modified_after_freeze("experiments/gate_e/sets/manifest.json", change, ("sets_manifest_sha256",),
                                 ("code_tree_sha256",))


def code_modified_before_resume(_):
    def body(d, here):
        rc1 = launch_and_interrupt(d, False, lambda c: sum(x.startswith("done diag") for x in c) >= 5, here=here)
        n = len(calls(d))
        rel = "experiments/gate_e/e_m2.py"
        append_comment(os.path.join(os.path.dirname(os.path.dirname(here)), rel))
        rc, err = launch(d, resume=True, here=here)
        ok = rc1 == 130 and rc == 5 and "code_tree_sha256" in err and rel in err and len(calls(d)) == n
        return ok, {"exit_first": rc1, "exit_resume": rc, "calls_after_resume": len(calls(d)) - n,
                    "refusal": err.strip()[:500]}
    return in_copied_tree(body)


def first_launch_baseline_items(_):
    """Every item of the baseline file is checked at the first launch."""
    def put(*keys, value):
        def f(w):
            for k in keys[:-1]:
                w = w[k]
            w[keys[-1]] = value
        return f

    variants = {
        "workload_level_1": (put("frozen_workload", "level", value=1), "frozen_workload"),
        "workload_m5b_100": (put("frozen_workload", "m5b_batches", value=100), "frozen_workload"),
        "workload_mlp_off": (put("frozen_workload", "mlp_p13_when_linear_detected", value=False), "frozen_workload"),
        "diag_cap_48h": (put("diag_cap_hours", value=48), "diag_cap_hours"),
        "parallel_workers_8": (put("parallel_workers", value=8), "parallel_workers"),
        "k2_train_steps_6000": (put("k2", "train_steps", value=6000), "k2"),
        "bridge_seeds_1_2": (put("bridge", "seeds", value=[1, 2]), "bridge"),
        "n_states_279": (put("n_states", value=279), "n_states"),
        "basis_code_tree": (put("basis", "code_tree_sha256", value="0" * 64), "code_tree_sha256"),
        "basis_preregistration": (put("basis", "preregistration_sha256", value="0" * 64), "preregistration_sha256"),
        "basis_sets_manifest": (put("basis", "sets_manifest_sha256", value="0" * 64), "sets_manifest_sha256"),
        "basis_timing": (put("basis", "timing_json_sha256", value="0" * 64), "timing_json_sha256"),
        "no_basis": (lambda w: w.pop("basis"), "no approved baseline"),
    }
    out, ok = {}, True
    for name, (change, expect) in variants.items():
        w = json.loads(json.dumps(WL))
        change(w)
        d = setup(workload=w)
        rc, err = launch(d)
        sub = rc == 5 and "approved freeze baseline" in err and expect in err and nothing_started(d)
        out[name] = {"pass": sub, "exit": rc, "refusal": err.strip()[:300]}
        ok &= sub
        shutil.rmtree(d, ignore_errors=True)
    return ok, {"variants": out}


def sync_never_includes_checkpoints(_):
    from run_gate_e import sync_items

    d = tempfile.mkdtemp(prefix="gate_e_sync_")
    for rel in ("results/a.json", "runs/K2_x_step0.pt", "runs/K2_x.json", "runs/bridge/A_x.pt",
                "quarantine/2026/K2_x_step0.pt", "quarantine/2026/r.json", "logs/run_status.txt",
                "results/.r.json.tmp.12", "logs/sub/.git/config", "run_freeze.json"):
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        open(os.path.join(d, rel), "w").write("x")
    items = [os.path.relpath(f, d) for f in sync_items(d)]
    shutil.rmtree(d)
    ok = not any(i.endswith(".pt") or ".tmp." in i or "/.git/" in i for i in items)
    ok &= set(items) == {"results/a.json", "runs/K2_x.json", "quarantine/2026/r.json", "logs/run_status.txt",
                         "run_freeze.json"}
    return ok, {"items": items}


CASES = [all_succeed, refuse_fresh_when_frozen, refuse_resume_without_freeze, refuse_nonempty_results,
         refuse_no_workload, refuse_m5a, refuse_no_cap, refuse_cmds_without_test_dir, training_integrity_failure,
         archive_failure, diag_integrity_failure, interrupt_during_diagnostics_then_resume, half_written_result,
         unledgered_valid_result_differs, unledgered_valid_result_equal, ledger_hash_mismatch, checkpoint_restored,
         checkpoint_restore_fails, workload_changed, freeze_item_changed, budget_cap_not_reset,
         repeated_restarts_during_judgment, judgment_without_ledger_recovered, retrain_after_interruption_equal,
         retrain_after_interruption_differs,
         # 12.8
         first_launch_matches_baseline, code_modified_after_freeze, native_code_modified_after_freeze,
         sets_manifest_modified_after_freeze, code_modified_before_resume, first_launch_baseline_items]


def main():
    out = {}
    for fn in CASES:
        name, r = run_case(fn)
        out[name] = r
        print(f"{name}: {'pass' if r['pass'] else 'FAIL'} {({k: v for k, v in r.items() if k not in ('pass', 'status_tail')})}",
              flush=True)
    name, r = "sync_never_includes_checkpoints", sync_never_includes_checkpoints(None)
    out[name] = {"pass": bool(r[0]), **r[1]}
    print(f"{name}: {'pass' if r[0] else 'FAIL'}", flush=True)
    res = {"cases": out, "pass": all(v["pass"] for v in out.values()),
           "tested_baseline": {k: v for k, v in WL["basis"].items() if k != "code_files"}}
    with open(os.path.join(HERE, "validation", "launcher_tests_v3.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("PASS" if res["pass"] else "FAIL")
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
