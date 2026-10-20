#!/usr/bin/env python3
"""
V4: fault-injection tests of the E2-c launcher run_e2c.py (E2C_PREREG_DRAFT 6,
3.5, 7.4, 8.4, 9, 13). Stub jobs only, in temporary test directories
(E2C_TEST_DIR / E2C_TEST_CMDS / E2C_TEST_PLAN): nothing is trained, diagnosed,
pushed, committed or evaluated; the salt, its commitment and the R* / M1*
hashes are simulated values; test2 is never generated (its job is a stub),
and the real key space is never enumerated (the keyspace job is a stub; one
case checks that the enumeration refuses to run without a stage-2 / stage-4
authorization). The cases follow E1's launcher tests and add the E2-c ones:
pairing hash mismatch, heads mismatch, lambda mismatch, lambda2 missing,
digit code changed, E_W^C1 = 0, re-trained run differing from its kept
attempt, salt mismatch, R* / M1* commitment mismatch, test2 isolation not
zero, stage 4 before stage 3, judgments written once.
A second part runs the test2 generation and evaluation code on a synthetic
pool of NON-held-out keys only (never in R*): determinism per salt, every key
in the pool, 1-2 counterfactuals per body, fallback counting, and one
evaluation of a freshly initialized model.

Writes stage1/v4/launcher_tests.json; exit 0 only if every case ends as expected.
"""

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
GE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(GE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402

PLAN = {"openmythos": [201, 202], "transformer": [201], "historical": [1]}
SALT = "simulated-salt-for-launcher-tests-only-0123456789abcdef"
KS = {"R_star_sha256": "a" * 64, "M1_star_sha256": "b" * 64, "counts": {"H": 12006, "U": 5093, "R_star": 6913, "M1_star": 4129}}
LAM, LAM2 = {"openmythos": 0.3, "transformer": 0.1}, {"openmythos": 0.5, "transformer": 0.2}

STUB = r'''import hashlib, json, os, random, shutil, sys, time
D = os.environ["STUB_DIR"]
kind, name = sys.argv[1], sys.argv[2]
def call(msg):
    with open(os.path.join(D, "calls.log"), "a") as f:
        f.write(msg + "\n")
call(f"start {kind} {name}")
if os.environ.get("STUB_FAIL_NAME") == f"{kind}:{name}":
    sys.exit(int(os.environ.get("STUB_FAIL_CODE", "1")))
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path + ".stubtmp", "w").write(text)
    os.replace(path + ".stubtmp", path)
def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()
bad = os.environ.get("STUB_BAD", "")  # "run|field|json value"
extra = str(random.random()) if os.environ.get("STUB_NONDET_NAME") == name else ""
if kind == "train":
    cond, arm, s = name.split("_"); seed = int(s[1:]); lam = sys.argv[3] if len(sys.argv) > 3 else ""
    for t in (0, 25, 50, 75, 100, 150, 200, 300, 500, 1000, 2000, 3000, 6000, 12000):
        write(os.path.join(D, "runs", f"{name}_step{t}.pt"), f"ckpt {name} {t}{extra}")
    rec = {"cond": cond, "arm": arm, "seed": seed, "steps": 12000, "complete": True, "lam": float(lam) if lam else None,
           "init_param_sha256": f"init-{arm}-{seed}", "batch_chain": {"100": f"chain-{seed}"}, "first_batch_sha256": f"b-{seed}",
           "lr_schedule_sha256": "lr", "optimizer": {"type": "AdamW"}, "clip": 1.0, "batch_size": 64,
           "r_u": [0.1, 0.2], "kappa_u": [1.0, 0.5], "loss_every_step": [3.0, 2.9], "aux_loss_every_step": [3.9, 3.8]}
    if cond != "C0":
        rec.update({"heads_sha256": {"p": f"heads-{arm}-{seed}"}, "record_points": ["p"], "positions": [2, 6], "mask": "m", "E_W": 1.0})
    if cond == "C2":
        rec["digit_code_sha256"] = os.environ["STUB_CODE_SHA_" + str(seed)]
    if extra:
        rec["r_u"] = [0.1, float(extra)]
    if bad and bad.split("|")[0] == name:
        rec[bad.split("|")[1]] = json.loads(bad.split("|")[2])
    write(os.path.join(D, "runs", f"{name}.json.progress.json"), json.dumps(dict(rec, complete=False)))
    time.sleep(float(os.environ.get("STUB_SLEEP_TRAIN", "0")))
    write(os.path.join(D, "runs", f"{name}.json"), json.dumps(rec))
    os.remove(os.path.join(D, "runs", f"{name}.json.progress.json"))
elif kind == "archive":
    os.makedirs(os.path.join(D, "remote"), exist_ok=True)
    for f in os.listdir(os.path.join(D, "runs")):
        if f.startswith(name + "_step") and f.endswith(".pt"):
            shutil.copyfile(os.path.join(D, "runs", f), os.path.join(D, "remote", f))
elif kind == "restore":
    local = sys.argv[3]
    if os.environ.get("STUB_RESTORE_FAIL") == "1":
        sys.exit(1)
    shutil.copyfile(os.path.join(D, "remote", os.path.basename(local)), local)
elif kind == "diag":
    time.sleep(float(os.environ.get("STUB_SLEEP_DIAG", "0")))
    st = name[5:]
    run, t = st.rsplit("_step", 1)
    cond, arm, s = run.split("_")
    r = {"arm": arm, "seed": int(s[1:]), "step": int(t), "param_sha256": sha(os.path.join(D, "runs", st + ".pt")),
         "seconds": {"M1": random.random()}, "M1": {"x": st + extra}, "M2": {}, "A_lin": 0.5, "M6": {},
         "M3": {"controls": {"negative_query_swap": {"pass": True}, "positive_own_letter_emb": {"pass": True}}},
         "M0": {"pass": True}}
    write(os.path.join(D, "results", st + ".json"), json.dumps(r))
elif kind == "keyspace":
    out = sys.argv[3]
    write(out, os.environ["STUB_KEYSPACE"])
elif kind == "test2":
    out = sys.argv[3]
    path = os.path.join(os.path.dirname(out), "test2_heldout.jsonl")
    write(path, "simulated test2 (no real key)\n")
    iso = json.loads(os.environ.get("STUB_ISOLATION", '{"keys_not_in_R_star": 0, "overlap_E1_sets": 0, "overlap_training_streams": 0}'))
    write(out, json.dumps({"sha256": sha(path), "isolation": iso, "stats": {"simulated": True}}))
elif kind == "judge":
    out = sys.argv[3]
    if os.path.exists(out):
        sys.exit(3)
    cond, arm, s = name.split("_")
    t2 = sha(os.path.join(D, "judgments", "test2_heldout.jsonl"))
    write(out, json.dumps({"cond": cond, "arm": arm, "seed": int(s[1:]), "set": "test2_heldout", "test2_sha256": t2, "main": {}}))
elif kind == "sync":
    pass
call(f"done {kind} {name}")
'''


def freeze_content(d, **change):
    """The freeze as run_e2c.make_baseline makes it, in test directory d."""
    env = dict(os.environ, E2C_TEST_DIR=d)
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import run_e2c as r; "
            "print(json.dumps(r.make_baseline(r.paths(), *json.loads(sys.argv[2]))))")
    args = json.dumps([LAM, LAM2, hashlib.sha256(SALT.encode()).hexdigest(), KS])
    out = subprocess.run([sys.executable, "-c", code, HERE, args], env=env, capture_output=True, text=True, check=True)
    fz = json.loads(out.stdout)
    for k, v in change.items():
        if v is None:
            fz.pop(k, None)
        else:
            fz[k] = v
    return fz


BASE_FREEZE = None


def setup(**change):
    d = tempfile.mkdtemp(prefix="e2c_v4_")
    fz = json.loads(json.dumps(BASE_FREEZE))
    for k, v in change.items():
        if v is None:
            fz.pop(k, None)
        else:
            fz[k] = v
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"), indent=1)
    open(os.path.join(d, "stub.py"), "w").write(STUB)
    py = sys.executable
    stub = f"{py} {d}/stub.py"
    cmds = {"train": stub + " train {name} {lam}", "archive": stub + " archive {name}",
            "restore": stub + " restore {state} {local}", "diag": stub + " diag {name}",
            "keyspace": stub + " keyspace keyspace {out}", "test2": stub + " test2 test2 {out}",
            "judge": stub + " judge {name} {out}", "sync": stub + " sync {msg}"}
    json.dump(cmds, open(os.path.join(d, "cmds.json"), "w"))
    open(os.path.join(d, "salt.txt"), "w").write(SALT)
    return d


def env_for(d, **extra):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("E2C_", "STUB_"))}
    e.update(E2C_TEST_DIR=d, E2C_TEST_CMDS=os.path.join(d, "cmds.json"), E2C_TEST_PLAN=json.dumps(PLAN), STUB_DIR=d,
             STUB_KEYSPACE=json.dumps(KS))
    for s in set(PLAN["openmythos"] + PLAN["transformer"] + PLAN["historical"]):
        e[f"STUB_CODE_SHA_{s}"] = C.code_sha(C.digit_code(s))
    e.update({k: str(v) for k, v in extra.items()})
    return e


def launch(d, stage=3, resume=False, salt=None, **extra):
    argv = [sys.executable, os.path.join(HERE, "run_e2c.py"), "--stage", str(stage)] + (["--resume"] if resume else [])
    if stage == 4:
        argv += ["--salt-file", salt or os.path.join(d, "salt.txt")]
    return subprocess.run(argv, env=env_for(d, **extra), capture_output=True, text=True, cwd=ROOT)


def launch_and_interrupt(d, stage, resume, when, **extra):
    argv = [sys.executable, os.path.join(HERE, "run_e2c.py"), "--stage", str(stage)] + (["--resume"] if resume else [])
    if stage == 4:
        argv += ["--salt-file", os.path.join(d, "salt.txt")]
    p = subprocess.Popen(argv, env=env_for(d, **extra), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t0 = time.time()
    while time.time() - t0 < 60 and not when(d):
        time.sleep(0.05)
    p.send_signal(signal.SIGTERM)
    p.wait()
    return p.returncode


def calls(d):
    f = os.path.join(d, "calls.log")
    return open(f).read().splitlines() if os.path.exists(f) else []


def count(d, prefix):
    return sum(1 for c in calls(d) if c.startswith(prefix))


def status(d):
    f = os.path.join(d, "logs", "run_status.txt")
    return open(f).read() if os.path.exists(f) else ""


N_RUNS = 2 * 3 + 1 * 3 + 2 * 2
N_STATES = N_RUNS * 14
N_JUDGE = N_RUNS + 2


# ------------------------------------------------------------ cases


def all_succeed(d):
    r3 = launch(d)
    r4 = launch(d, stage=4)
    ok = (r3.returncode == 0 and r4.returncode == 0 and count(d, "done train") == N_RUNS and count(d, "done archive") == N_RUNS
          and count(d, "done diag") == N_STATES and count(d, "done judge") == N_JUDGE and count(d, "done keyspace") == 1
          and count(d, "done test2") == 1)
    r4b = launch(d, stage=4, resume=True)
    ok = ok and r4b.returncode == 0 and count(d, "start judge") == N_JUDGE
    return ok, f"stage3 {r3.returncode}, stage4 {r4.returncode}, stage4 resume {r4b.returncode}; trains {count(d, 'done train')}, " \
               f"diags {count(d, 'done diag')}, judges {count(d, 'start judge')} (written once)"


def refuse_fresh_when_frozen(d):
    launch(d)
    r = launch(d)
    return r.returncode == 5 and "continue with --resume" in r.stderr, f"exit {r.returncode}"


def refuse_resume_without_freeze(d):
    r = launch(d, resume=True)
    return r.returncode == 5 and not calls(d), f"exit {r.returncode}"


def refuse_nonempty_results(d):
    os.makedirs(os.path.join(d, "results"))
    open(os.path.join(d, "results", "x.json"), "w").write("{}")
    r = launch(d)
    return r.returncode == 5 and not calls(d), f"exit {r.returncode}"


def refuse_no_freeze(d):
    os.remove(os.path.join(d, "e2c_workload_freeze.json"))
    r = launch(d)
    return r.returncode == 5 and not calls(d), f"exit {r.returncode}"


def refuse_cmds_without_test_dir(d):
    e = env_for(d)
    e.pop("E2C_TEST_DIR")
    r = subprocess.run([sys.executable, os.path.join(HERE, "run_e2c.py"), "--stage", "3"], env=e, capture_output=True, text=True, cwd=ROOT)
    return r.returncode == 5 and not calls(d), f"exit {r.returncode}"


def lambda2_missing(d):
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz["lambda2"] = {"openmythos": LAM2["openmythos"]}
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d)
    return r.returncode == 5 and "lambda2 for transformer missing" in r.stderr and not calls(d), f"exit {r.returncode}"


def lambda_not_candidate(d):
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz["lambda"]["openmythos"] = 0.5
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d)
    return r.returncode == 5 and not calls(d), f"exit {r.returncode}"


def salt_commitment_missing(d):
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz.pop("salt_commitment_sha256")
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d)
    return r.returncode == 5 and "salt commitment missing" in r.stderr, f"exit {r.returncode}"


def approved_item_changed(d):
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz["alpha"]["openmythos"]["exclusion"] = 0.05
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d)
    return r.returncode == 5 and "alpha" in r.stderr, f"exit {r.returncode}"


def code_tree_differs(d):
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz["basis"]["code_files"]["experiments/gate_e/e2c/train_e2c.py"] = "0" * 64
    fz["basis"]["code_tree_sha256"] = "0" * 64
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d)
    return r.returncode == 5 and "train_e2c.py" in r.stderr, f"exit {r.returncode}"


def preregistration_differs(d):
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz["basis"]["preregistration_sha256"] = "0" * 64
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d)
    return r.returncode == 5 and "preregistration_sha256" in r.stderr, f"exit {r.returncode}"


def freeze_changed_before_resume(d):
    rc = launch_and_interrupt(d, 3, False, lambda d: count(d, "done train") >= 2, STUB_SLEEP_TRAIN=0.3)
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    fz["lambda2"]["transformer"] = 0.3
    json.dump(fz, open(os.path.join(d, "e2c_workload_freeze.json"), "w"))
    r = launch(d, resume=True)
    return r.returncode == 5 and "freeze_file_sha256" in r.stderr, f"interrupted {rc}, resume exit {r.returncode}"


def training_integrity_failure(d):
    r = launch(d, STUB_FAIL_NAME="train:C1_openmythos_s201", STUB_FAIL_CODE=3)
    return r.returncode == 3 and count(d, "start diag") == 0, f"exit {r.returncode} (F7 non-finite: train exits 3)"


def archive_failure(d):
    r = launch(d, STUB_FAIL_NAME="archive:C0_openmythos_s201")
    return r.returncode == 3 and count(d, "start diag") == 0, f"exit {r.returncode}"


def pairing_chain_mismatch(d):
    r = launch(d, STUB_BAD='C2_openmythos_s201|batch_chain|{"100": "other"}')
    return r.returncode == 3 and "batch_chain differs" in status(d) and count(d, "start diag") == 0, f"exit {r.returncode}"


def pairing_init_mismatch(d):
    r = launch(d, STUB_BAD='C1_transformer_s201|init_param_sha256|"other"')
    return r.returncode == 3 and "init_param_sha256 differs" in status(d), f"exit {r.returncode}"


def heads_mismatch(d):
    r = launch(d, STUB_BAD='C2_openmythos_s202|heads_sha256|{"p": "other"}')
    return r.returncode == 3 and "heads_sha256 differs" in status(d), f"exit {r.returncode}"


def lambda_mismatch(d):
    r = launch(d, STUB_BAD="C1_openmythos_s201|lam|0.1")
    return r.returncode == 3 and "lambda 0.1 != frozen 0.3" in status(d), f"exit {r.returncode}"


def digit_code_changed(d):
    r = launch(d, STUB_BAD='C2_transformer_s201|digit_code_sha256|"' + "c" * 64 + '"')
    return r.returncode == 3 and "digit code differs" in status(d), f"exit {r.returncode}"


def e_w_c1_zero(d):
    r = launch(d, STUB_BAD="C1_openmythos_s202|E_W|0.0")
    return r.returncode == 3 and "E_W^C1 = 0.0" in status(d), f"exit {r.returncode}"


def diag_integrity_failure(d):
    r = launch(d, STUB_FAIL_NAME="diag:diag_C1_openmythos_s201_step75", STUB_FAIL_CODE=3)
    return r.returncode == 3, f"exit {r.returncode} (F6)"


def interrupt_during_diagnostics_then_resume(d):
    rc = launch_and_interrupt(d, 3, False, lambda d: count(d, "done diag") >= 10, STUB_SLEEP_DIAG=0.05)
    r = launch(d, resume=True)
    done = [c for c in calls(d) if c.startswith("done diag")]
    return (rc == 130 and r.returncode == 0 and len(set(done)) == N_STATES and count(d, "done train") == N_RUNS,
            f"interrupted {rc}, resume {r.returncode}, distinct diagnosed {len(set(done))}, trains {count(d, 'done train')}")


def retrain_after_interruption_equal(d):
    rc = launch_and_interrupt(d, 3, False, lambda d: os.path.exists(os.path.join(d, "runs", "C0_openmythos_s201.json.progress.json")),
                              STUB_SLEEP_TRAIN=5)
    r = launch(d, resume=True)
    return (r.returncode == 0 and "re-trained C0_openmythos_s201 equals the kept attempt" in status(d),
            f"interrupted {rc}, resume {r.returncode}")


def retrain_after_interruption_differs(d):
    rc = launch_and_interrupt(d, 3, False, lambda d: os.path.exists(os.path.join(d, "runs", "C0_openmythos_s201.json.progress.json")),
                              STUB_SLEEP_TRAIN=5, STUB_NONDET_NAME="C0_openmythos_s201")
    r = launch(d, resume=True, STUB_NONDET_NAME="C0_openmythos_s201")
    return r.returncode == 3 and "differs from the kept attempt" in status(d), f"interrupted {rc}, resume {r.returncode}"


def half_written_result(d):
    launch_and_interrupt(d, 3, False, lambda d: count(d, "done diag") >= 5, STUB_SLEEP_DIAG=0.05)
    open(os.path.join(d, "results", ".x.json.tmp.123"), "w").write("{")
    r = launch(d, resume=True)
    return r.returncode == 0 and "temporary file of an interrupted write" in status(d), f"resume {r.returncode}"


def unledgered_result_differs(d):
    launch(d)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    st = "C1_openmythos_s201_step150"
    led.pop(st)
    json.dump(led, open(os.path.join(d, "results_ledger.json"), "w"))
    r = launch(d, resume=True, STUB_NONDET_NAME=f"diag_{st}")
    return r.returncode == 3 and "differs from the kept result" in status(d), f"resume {r.returncode}"


def unledgered_result_equal(d):
    launch(d)
    led = json.load(open(os.path.join(d, "results_ledger.json")))
    led.pop("C1_openmythos_s201_step150")
    json.dump(led, open(os.path.join(d, "results_ledger.json"), "w"))
    r = launch(d, resume=True)
    return r.returncode == 0 and count(d, "done diag diag_C1_openmythos_s201_step150") == 2, f"resume {r.returncode}"


def ledger_hash_mismatch(d):
    launch(d)
    open(os.path.join(d, "results", "C0_transformer_s201_step75.json"), "a").write(" ")
    r = launch(d, resume=True)
    return r.returncode == 3 and "differs from its ledger entry" in status(d), f"resume {r.returncode}"


def checkpoint_restored(d):
    rc = launch_and_interrupt(d, 3, False, lambda d: count(d, "done archive") >= N_RUNS, STUB_SLEEP_DIAG=0.3)
    os.remove(os.path.join(d, "runs", "C2_transformer_s201_step3000.pt"))
    r = launch(d, resume=True)
    return r.returncode == 0 and count(d, "done restore") >= 1, f"interrupted {rc}, resume {r.returncode}"


def checkpoint_restore_fails(d):
    launch_and_interrupt(d, 3, False, lambda d: count(d, "done archive") >= N_RUNS, STUB_SLEEP_DIAG=0.3)
    os.remove(os.path.join(d, "runs", "C2_transformer_s201_step3000.pt"))
    r = launch(d, resume=True, STUB_RESTORE_FAIL=1)
    return r.returncode == 3, f"resume {r.returncode}"


def budget_cap_not_reset(d):
    r1 = launch(d, E2C_TEST_CAP_SECONDS=1.0, STUB_SLEEP_DIAG=0.05)
    r2 = launch(d, resume=True, E2C_TEST_CAP_SECONDS=1.0)
    b = json.load(open(os.path.join(d, "budget_ledger.json")))["stage3"]
    return (r1.returncode == 7 and r2.returncode == 7 and len(b["launches"]) == 2 and b["seconds"] >= 1.0,
            f"exits {r1.returncode}, {r2.returncode}; cumulative {b['seconds']:.2f} s over {len(b['launches'])} launches")


def stage4_before_stage3(d):
    r = launch(d, stage=4)
    return r.returncode == 5 and "before stage 3 is complete" in r.stderr and not calls(d), f"exit {r.returncode}"


def salt_mismatch(d):
    launch(d)
    bad = os.path.join(d, "wrong_salt.txt")
    open(bad, "w").write("another-simulated-salt")
    r = launch(d, stage=4, salt=bad)
    return (r.returncode == 3 and "differs from the frozen commitment" in status(d) and count(d, "start keyspace") == 0
            and count(d, "start judge") == 0, f"exit {r.returncode}")


def commitment_mismatch(d):
    launch(d)
    r = launch(d, stage=4, STUB_KEYSPACE=json.dumps(dict(KS, R_star_sha256="d" * 64)))
    return (r.returncode == 3 and "R* / M1* recomputed differ" in status(d) and count(d, "start test2") == 0
            and count(d, "start judge") == 0, f"exit {r.returncode}")


def isolation_not_zero(d):
    launch(d)
    r = launch(d, stage=4, STUB_ISOLATION=json.dumps({"keys_not_in_R_star": 0, "overlap_E1_sets": 1, "overlap_training_streams": 0}))
    return r.returncode == 3 and "isolation of test2 not zero" in status(d) and count(d, "start judge") == 0, f"exit {r.returncode}"


def judgment_never_redone(d):
    launch(d)
    launch(d, stage=4)
    jl = json.load(open(os.path.join(d, "judgments_ledger.json")))
    open(os.path.join(d, "judgments", "C1_openmythos_s201.json"), "a").write(" ")
    r = launch(d, stage=4, resume=True)
    return (r.returncode == 3 and "never redone" in status(d) and count(d, "start judge") == N_JUDGE and len(jl) == N_JUDGE,
            f"exit {r.returncode}")


def judgment_without_ledger_recovered(d):
    launch(d)
    rc = launch_and_interrupt(d, 4, False, lambda d: count(d, "done judge") >= 3, STUB_SLEEP_DIAG=0)
    jl = json.load(open(os.path.join(d, "judgments_ledger.json")))
    done = [k for k, v in jl.items() if v.get("sha256")]
    if done:
        jl[done[0]].pop("sha256")
        json.dump(jl, open(os.path.join(d, "judgments_ledger.json"), "w"))
    r = launch(d, stage=4, resume=True)
    dn = [c for c in calls(d) if c.startswith("done judge")]
    rec = json.load(open(os.path.join(d, "judgments_ledger.json")))
    recovered = [k for k, v in rec.items() if v.get("recovered")]
    # every judgment file found without a ledger hash is recorded, never redone: the one whose hash was removed,
    # and any whose file was written just before the interruption
    return (r.returncode == 0 and len(dn) == len(set(dn)) == N_JUDGE and bool(done) and done[0] in recovered,
            f"interrupted {rc}, resume {r.returncode}, judgments written {len(dn)} (each once), recovered {recovered}")


def keyspace_guard():
    import e2c_test2 as T
    os.environ.pop("E2C_KEYSPACE_STAGE", None)
    try:
        T.keyspace(os.path.join(GE, "sets"))
    except T.NotAuthorized as e:
        return True, f"refused: {e}"
    return False, "enumeration was not refused"


def synthetic_generation():
    """test2 generation / evaluation code on a synthetic pool of training-
    distribution (non-held-out) keys only; none is in R*."""
    import e2c_test2 as T
    import itertools
    import random
    letters = "abcdefghij"
    pool = set()
    for l1, l2 in itertools.combinations(letters, 2):
        for d1 in T.DIG:
            for d2 in T.DIG:
                if d1 != d2:
                    k = T.key([(l1, d1), (l2, d2)])
                    if not T.held(k):
                        pool.add(k)
    pool = set(random.Random(5).sample(sorted(pool), 2400))
    assert not any(T.held(k) for k in pool)
    M1 = {k for k in pool if any(T.swap_options(k, j, pool) for j in (0, 1))}
    a1, s1 = T.generate("synthetic-salt-A", pool, M1, n=300)
    a2, _ = T.generate("synthetic-salt-A", pool, M1, n=300)
    b1, _ = T.generate("synthetic-salt-B", pool, M1, n=300)
    keys = [T.key(T.stmts(r["body"])) for r in a1] + [T.key(T.stmts(s["body"])) for r in a1 for s in r["root_swaps"]]
    ok = {"deterministic_per_salt": T.serialize_test2(a1) == T.serialize_test2(a2),
          "salt_changes_set": T.serialize_test2(a1) != T.serialize_test2(b1),
          "all_keys_in_pool": all(k in pool for k in keys), "one_or_two_swaps": all(1 <= len(r["root_swaps"]) <= 2 for r in a1),
          "main_bodies_distinct": len({T.key(T.stmts(r["body"])) for r in a1}) == 300,
          "swap_changes_only_its_statement": all(T.stmts(s["body"])[1 - s["slot"]] == T.stmts(r["body"])[1 - s["slot"]]
                                                 and T.stmts(s["body"])[s["slot"]][1] != T.stmts(r["body"])[s["slot"]][1]
                                                 for r in a1 for s in r["root_swaps"]),
          "fallback_counted": s1["fallback_pairs"] == sum(s["fallback"] for r in a1 for s in r["root_swaps"])}
    import torch
    from models import build
    torch.manual_seed(0)
    m = build("transformer", 2)
    m.eval()
    ev = T.evaluate(m, a1[:50])
    ok["evaluation_runs"] = set(ev) >= {"accuracy", "query_swap_both", "root_swap_both", "learned", "level"}
    return all(ok.values()), json.dumps(dict(ok, stats=s1, eval_level=ev["level"]))


CASES = [all_succeed, refuse_fresh_when_frozen, refuse_resume_without_freeze, refuse_nonempty_results, refuse_no_freeze,
         refuse_cmds_without_test_dir, lambda2_missing, lambda_not_candidate, salt_commitment_missing, approved_item_changed,
         code_tree_differs, preregistration_differs, freeze_changed_before_resume, training_integrity_failure, archive_failure,
         pairing_chain_mismatch, pairing_init_mismatch, heads_mismatch, lambda_mismatch, digit_code_changed, e_w_c1_zero,
         diag_integrity_failure, interrupt_during_diagnostics_then_resume, retrain_after_interruption_equal,
         retrain_after_interruption_differs, half_written_result, unledgered_result_differs, unledgered_result_equal,
         ledger_hash_mismatch, checkpoint_restored, checkpoint_restore_fails, budget_cap_not_reset, stage4_before_stage3,
         salt_mismatch, commitment_mismatch, isolation_not_zero, judgment_never_redone, judgment_without_ledger_recovered]


def main():
    global BASE_FREEZE
    out_dir = os.path.join(HERE, "stage1", "v4")
    os.makedirs(out_dir, exist_ok=True)
    d0 = tempfile.mkdtemp(prefix="e2c_v4_base_")
    BASE_FREEZE = freeze_content(d0)
    shutil.rmtree(d0, ignore_errors=True)
    res = {}
    for fn in CASES:
        d = setup()
        t = time.time()
        try:
            ok, info = fn(d)
        except Exception as e:  # noqa: BLE001
            ok, info = False, f"exception {e!r}"
        res[fn.__name__] = {"pass": bool(ok), "info": info, "seconds": round(time.time() - t, 1)}
        print(f"{'PASS' if ok else 'FAIL'} {fn.__name__}: {info}", flush=True)
        if ok:
            shutil.rmtree(d, ignore_errors=True)
        else:
            res[fn.__name__]["dir"] = d
    for fn in (keyspace_guard, synthetic_generation):
        try:
            ok, info = fn()
        except Exception as e:  # noqa: BLE001
            ok, info = False, f"exception {e!r}"
        res[fn.__name__] = {"pass": bool(ok), "info": info}
        print(f"{'PASS' if ok else 'FAIL'} {fn.__name__}: {info[:300]}", flush=True)
    res["all_pass"] = all(v["pass"] for v in res.values() if isinstance(v, dict))
    json.dump(res, open(os.path.join(out_dir, "launcher_tests.json"), "w"), indent=1, ensure_ascii=False)
    print("V4", "PASS" if res["all_pass"] else "FAIL", f"{sum(v['pass'] for v in res.values() if isinstance(v, dict))}/{len(res) - 1}")
    sys.exit(0 if res["all_pass"] else 3)


if __name__ == "__main__":
    main()
