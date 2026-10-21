#!/usr/bin/env python3
"""
I2: synthetic tests of the stage-2 driver e2c_stage2.py and of its interface
to the launcher run_e2c.py (B1 approvals, B2 R* / M1* count structure, B3
commitment only).

Every case runs in its own temporary git repository with synthetic E1 sets,
synthetic E1 freeze records, synthetic stage-1 chain records and stub jobs.
Bodies use symbols that are no letters (#$%&*+<>@^), so no real key occurs
anywhere. The real key space is never enumerated: the stage-4 keyspace job
and the Appendix A script are stubs, and E2C_KEYSPACE_STAGE is never set (a
stub records the environment it was started with). The 33 real training
streams are never drawn: V2 runs the 33 seeds on a synthetic stream of 3
updates x 4 samples. No salt exists, only commitments of simulated strings;
no test2 and no real freeze file is written. The real-mode entry points are
called only to show that they refuse before reading or writing anything.

    python3 e2c_stage2_tests.py --out PATH     (never over an existing file)

Exit 0 only if every case ends as expected.
"""

import gzip
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

import e2c_launcher_tests as LT  # noqa: E402  stub jobs of the launcher tests (V4)
import e2c_stage2 as S2  # noqa: E402
import e2c_test2 as T  # noqa: E402
import run_e2c as R  # noqa: E402

DRIVER = os.path.join(HERE, "e2c_stage2.py")
SYN = "#$%&*+<>@^"  # ten symbols, none a letter or a separator of the task format
DIG = "0123456789"
COMMITMENT = hashlib.sha256(LT.SALT.encode()).hexdigest()  # the launcher tests' simulated salt
SETS = {"dev_heldout": 6, "test_heldout": 6, "diag_fit": 6, "diag_eval": 6, "minpair": 8, "dev_seen": 6, "pool_b_k2": 6,
        "pool_c_k2": 6, "diag_fit_k4": 3}
REF_SEEDS = (1, 91, 99, 201)
EXCLUDE = ["/config.json", "/stubs/", "/stub_env.log", "/stub.py", "/cmds.json", "/salt.txt", "/other_salt.txt", "/calls.log",
           "/runs/", "/results/", "/judgments/", "/logs/", "/quarantine/", "/lfs_tmp/", "/*_ledger.json", "/run_freeze.json",
           "/checkpoints_manifest.json", "/test2_record.json", "/approvals.json", "/x.pt", "*.lock"]
KEYSPACE_STUB = r'''import json, os, sys
d = os.environ["E2C_S2_TEST_DIR"]
cfg = json.load(open(os.path.join(d, "config.json")))
with open(os.path.join(d, "stub_env.log"), "a") as f:
    f.write(json.dumps(sorted(k for k in os.environ if k.startswith("E2C"))) + "\n")
if cfg.get("stub_leak"):
    open(os.path.join(os.path.dirname(sys.argv[1]), "leak.txt"), "w").write("a=1;b=2\n")
open(sys.argv[1], "w").write(json.dumps(cfg["stub_keyspace"]))
'''
INVOCATIONS = [0]
GIT_ID = LT.GIT_ID


def git(d, *args):
    return subprocess.run(["git", *GIT_ID, *args], cwd=d, capture_output=True, text=True, check=True).stdout.strip()


def head(d):
    return git(d, "rev-parse", "HEAD")


def commit_all(d, msg):
    git(d, "add", "-A")
    git(d, "commit", "-q", "--allow-empty", "-m", msg)
    return head(d)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def bodies(rng, n, held=False):
    out = []
    while len(out) < n:
        (l1, l2), (d1, d2) = rng.sample(SYN, 2), rng.sample(DIG, 2)
        b = f"{l1}={d1};{l2}={d2};"
        if T.held(T.key(T.stmts(b))) == held and b not in out:
            out.append(b)
    return out


def held_body():
    import random
    return bodies(random.Random(9), 1, held=True)[0]


def appendix_stdout():
    return S2.appendix_a(os.path.join(HERE, "E2C_PREREG_DRAFT.md"))[1]


def make_env(nonu_held=0, **cfg_change):
    """A synthetic stage-2 setup in a fresh git repository; returns its directory."""
    import random
    d = tempfile.mkdtemp(prefix="e2c_s2_")
    git(d, "init", "-q")
    with open(os.path.join(d, ".git", "info", "exclude"), "a") as f:
        f.write("\n".join(EXCLUDE) + "\n")
    rng = random.Random(4)
    man = {}
    for name, n in SETS.items():
        rows = []
        for i, b in enumerate(bodies(rng, n)):
            r = {"body": b, "queries": [b[0], b[4]], "answers": [b[2], b[6]], "id": i}
            if name == "test_heldout":
                r["root_swap"] = [{"body": b[:2] + str((int(b[2]) + 1) % 10) + b[3:], "answer": "x"}]
            if name == "minpair":
                r["heldout"] = False
            rows.append(r)
        if name == "dev_seen" and nonu_held:
            rows[0]["body"] = held_body()
        text = "".join(json.dumps(r) + "\n" for r in rows)
        os.makedirs(os.path.join(d, "sets"), exist_ok=True)
        open(os.path.join(d, "sets", name + ".jsonl"), "w").write(text)
        man[name] = {"rows": len(rows), "bodies": len(rows), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    jdump(os.path.join(d, "sets", "manifest.json"), man)
    msha = sha(os.path.join(d, "sets", "manifest.json"))
    jdump(os.path.join(d, "e1", "workload_freeze.json"), {"basis": {"sets_manifest_sha256": msha}})
    jdump(os.path.join(d, "e1", "workload_freeze_v2.json"), {"basis": {"sets_manifest_sha256": msha}})
    jdump(os.path.join(d, "e1", "run_freeze.json"), {"sets_manifest_sha256": msha, "workload": {"basis": {"sets_manifest_sha256": msha}}})
    import numpy
    import torch
    jdump(os.path.join(d, "environment.json"), {"python": sys.version, "torch": torch.__version__, "numpy": numpy.__version__})
    cfg = {"key_rule_letters": SYN}
    for s in REF_SEEDS:  # synthetic stage-1 records: the synthetic stream's chain at updates 1-3
        r = S2.stream_check({"test": True, "cfg": cfg, "updates": 3, "batch": 4}, s, [1, 2])
        rec = {"seed": s, "steps": 3, "batch_chain": r["batch_chain"], "first_batch_sha256": r["first_batch_sha256"]}
        if s == 91:
            os.makedirs(os.path.join(d, "refs"), exist_ok=True)
            open(os.path.join(d, "refs", f"run_s{s}.json.gz"), "wb").write(gzip.compress(json.dumps(rec).encode(), mtime=0))
        else:
            jdump(os.path.join(d, "refs", f"run_s{s}.json"), rec)
    first = commit_all(d, "synthetic E1 archive and stage-1 records")
    os.makedirs(os.path.join(d, "stubs"))
    open(os.path.join(d, "stubs", "keyspace_job.py"), "w").write(KEYSPACE_STUB)
    open(os.path.join(d, "stubs", "appendix_stdout.txt"), "w").write(appendix_stdout())
    cfg.update({
        "git_root": ".", "sets_dir": "sets", "e1_anchors": [["e1/workload_freeze.json", ["basis", "sets_manifest_sha256"]],
                                                          ["e1/workload_freeze_v2.json", ["basis", "sets_manifest_sha256"]],
                                                          ["e1/run_freeze.json", ["sets_manifest_sha256"]],
                                                          ["e1/run_freeze.json", ["workload", "basis", "sets_manifest_sha256"]]],
        "e1_git_paths": ["sets", "e1"], "e1_manifest_sha256": msha, "e1_archive_commit": first,
        "code_git_root": ".", "code_base_commit": first, "allowed_changes": {},
        "environment_file": "environment.json", "reference_root": ".", "reference_globs": ["refs/*.json", "refs/*.json.gz"],
        "cap_seconds": 300, "heartbeat_seconds": 0.2, "updates": 3, "batch": 4, "workers": 2,
        "key_rule_expected_heldout": S2.key_rules(SYN)["heldout"], "stub_keyspace": LT.KS,
        "stub_appendix_stdout": "stubs/appendix_stdout.txt", "stub_keyspace_job": "stubs/keyspace_job.py"})
    cfg["reference_count"], cfg["reference_digest"] = refs_digest(d, cfg)
    cfg.update(cfg_change)
    jdump(os.path.join(d, "config.json"), cfg)
    return d


def refs_digest(d, cfg):
    refs, digest = S2.reference_records({"reference_root": d, "reference_globs": cfg["reference_globs"]})
    return len(refs), digest


def set_cfg(d, **change):
    cfg = json.load(open(os.path.join(d, "config.json")))
    for k, v in change.items():
        if v is None:
            cfg.pop(k, None)
        else:
            cfg[k] = v
    jdump(os.path.join(d, "config.json"), cfg)


def env_s2(d, **extra):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("E2C_", "STUB_"))}
    e.update(E2C_S2_TEST_DIR=d, E2C_TEST_DIR=d)
    e.update({k: str(v) for k, v in extra.items()})
    return e


def run(d, *args, env=None, timeout=300):
    INVOCATIONS[0] += 1
    return subprocess.run([sys.executable, DRIVER, *args], env=env or env_s2(d), cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout)


def verify(d, resume=False, commit=None, **kw):
    return run(d, "verify", "--expected-commit", commit or head(d), "--authorization", "synthetic test",
               *(["--resume"] if resume else []), **kw)


def popen_verify(d, resume=False):
    INVOCATIONS[0] += 1
    return subprocess.Popen([sys.executable, DRIVER, "verify", "--expected-commit", head(d)] + (["--resume"] if resume else []),
                            env=env_s2(d), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def freeze(d, vcommit, vsha, commitment=COMMITMENT, commit=None, extra=()):
    return run(d, "freeze", "--expected-commit", commit or head(d), "--approved-verify-commit", vcommit,
               "--approved-verify-sha256", vsha, "--salt-commitment-sha256", commitment, "--authorization", "synthetic test", *extra)


def record(d):
    p = os.path.join(d, "stage2", "stage2_verify.json")
    return json.load(open(p)) if os.path.exists(p) else None


def stop_status(d):
    p = os.path.join(d, "stage2", "verify_stop.json")
    return json.load(open(p))["status"] if os.path.exists(p) else None


def ledger(d):
    return json.load(open(os.path.join(d, "stage2", "budget_ledger_s2.json")))


def attempts(d):
    return S2.attempts_of(os.path.join(d, "stage2"))


def summary(d, n):
    return json.load(open(os.path.join(d, "stage2", "attempts", n, "summary.json")))


def approve_verify(d):
    """The review's approval of a passed verify: its outputs committed; the commit and the record's sha256."""
    c = commit_all(d, "stage-2 verify record (simulated review approval)")
    return c, sha(os.path.join(d, "stage2", "stage2_verify.json"))


def frozen(d):
    """verify, approve, freeze, commit the freeze: returns (commit, freeze sha256)."""
    r = verify(d)
    assert r.returncode == 0, r.stderr[-500:]
    vc, vs = approve_verify(d)
    f = freeze(d, vc, vs)
    assert f.returncode == 0, f.stderr[-500:]
    git(d, "add", "e2c_workload_freeze.json", "stage2")
    git(d, "commit", "-q", "-m", "stage-2 freeze (simulated)")
    return head(d), sha(os.path.join(d, "e2c_workload_freeze.json"))


def launcher(d, stage, ap, resume=False, salt=None):
    INVOCATIONS[0] += 1
    argv = [sys.executable, os.path.join(HERE, "run_e2c.py"), "--stage", str(stage), "--approved-stage2-commit", ap[0],
            "--approved-freeze-sha256", ap[1]] + (["--resume"] if resume else [])
    if stage == 4:
        argv += ["--salt-file", salt or os.path.join(d, "salt.txt")]
    return subprocess.run(argv, env=LT.env_for(d), cwd=ROOT, capture_output=True, text=True, timeout=600)


def wait_for(cond, limit=120):
    t = time.time()
    while time.time() - t < limit and not cond():
        time.sleep(0.05)


def tail(r):
    return (r.stderr or "").strip().splitlines()[-1][:220] if (r.stderr or "").strip() else ""


# ------------------------------------------------------------ cases: normal path


def verify_pass(d):
    r = verify(d)
    rec, led = record(d), ledger(d)
    env_log = open(os.path.join(d, "stub_env.log")).read()
    ok = (r.returncode == 0 and rec["status"] == "PASS" and rec["mode"] == "test" and rec["v2"]["seeds"] == S2.SEEDS_33
          and rec["v2"]["unique_seeds"] == 33 and rec["f11"]["pass"] and rec["keyspace"] == LT.KS and rec["key_rules"]["pass"]
          and rec["v2"]["accepted_samples_per_seed"] == 12 and rec["v2"]["stage1_chain_points_compared"] == 12
          and rec["leak_scan"]["key_like_hits"] == 0 and attempts(d) == ["01"] and stop_status(d) is None
          and [iv["status"] for iv in led["intervals"]] == ["PASS"] and all(iv["end"] for iv in led["intervals"])
          and "E2C_KEYSPACE_STAGE" not in env_log and "E2C_S2_STUB_KEYSPACE_STAGE" in env_log
          and os.path.exists(os.path.join(d, "stage2", "v2_streams.json")))
    return ok, f"exit {r.returncode}; 33 seeds, chain points compared {rec and rec['v2']['stage1_chain_points_compared']}; " \
               f"keyspace stub env {env_log.strip()}"


def verify_deterministic(d):
    d2 = d + "_copy"
    shutil.copytree(d, d2, symlinks=True)
    r1, r2 = verify(d), verify(d2)
    a, b = (open(os.path.join(x, "stage2", n), "rb").read() for x in (d, d2) for n in ("stage2_verify.json",))
    s1, s2 = (open(os.path.join(x, "stage2", "v2_streams.json"), "rb").read() for x in (d, d2))
    shutil.rmtree(d2, ignore_errors=True)
    return r1.returncode == 0 and r2.returncode == 0 and a == b and s1 == s2, f"exits {r1.returncode}, {r2.returncode}; records equal {a == b}"


def freeze_pass_launcher_accepts(d):
    ap = frozen(d)
    fz = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))
    chk = run(d, "check", "--approved-freeze-commit", ap[0], "--approved-freeze-sha256", ap[1])
    LT.prepare(d)
    r3 = launcher(d, 3, ap)
    r4 = launcher(d, 4, ap)
    rf = json.load(open(os.path.join(d, "run_freeze.json")))
    ok = (chk.returncode == 0 and r3.returncode == 0 and r4.returncode == 0 and fz["keyspace"] == LT.KS
          and fz["salt_commitment_sha256"] == COMMITMENT and fz["lambda"] == {"openmythos": 0.1, "transformer": 1.0}
          and fz["stage2"]["training_stream_seeds"] == S2.SEEDS_33 and rf["stage3"]["approved_stage2_commit"] == ap[0]
          and rf["stage3"]["approved_freeze_sha256"] == ap[1] == rf["stage4"]["approved_freeze_sha256"]
          and "salt" not in json.dumps(fz.get("stage2")))
    return ok, f"check {chk.returncode}, stage3 {r3.returncode}, stage4 {r4.returncode}; freeze {ap[1][:12]} at {ap[0][:12]}"


# ------------------------------------------------------------ B1: freeze written once, approvals from the review


def freeze_replaced_refused_by_launcher(d):
    ap = frozen(d)
    LT.prepare(d)
    path, rpath = os.path.join(d, "e2c_workload_freeze.json"), os.path.join(d, "stage2", "stage2_freeze_receipt.json")
    fz = json.load(open(path))
    fz["salt_commitment_sha256"] = hashlib.sha256(b"another simulated salt").hexdigest()
    open(path, "w").write(json.dumps(fz, indent=1, sort_keys=True) + "\n")
    rc = json.load(open(rpath))
    rc["freeze_sha256"] = sha(path)  # the sidecar edited to match
    open(rpath, "w").write(json.dumps(rc))
    r1 = launcher(d, 3, ap)
    r2 = launcher(d, 3, (ap[0], sha(path)))
    git(d, "commit", "-q", "-am", "edited freeze and receipt")
    r3 = launcher(d, 3, (head(d), sha(path)))
    ok = all(r.returncode == 5 and "not the approved one" in r.stderr for r in (r1, r2, r3)) and not os.path.exists(os.path.join(d, "runs"))
    return ok, f"exits {r1.returncode}, {r2.returncode}, {r3.returncode}: {tail(r3)}"


def freeze_written_once(d):
    ap = frozen(d)
    rpath = os.path.join(d, "stage2", "stage2_freeze_receipt.json")
    before = (ap[1], sha(rpath))
    vc = json.load(open(os.path.join(d, "e2c_workload_freeze.json")))["stage2"]
    r = freeze(d, vc["verify_commit"], vc["verify_record_sha256"])
    return (r.returncode == 5 and "written once" in r.stderr and (sha(os.path.join(d, "e2c_workload_freeze.json")), sha(rpath)) == before,
            f"second freeze exit {r.returncode}: {tail(r)}")


def freeze_needs_approved_record(d):
    r0 = verify(d)
    out = []
    rp = os.path.join(d, "stage2", "stage2_verify.json")
    out.append(freeze(d, head(d), sha(rp)))  # (a) record not committed
    vc, vs = approve_verify(d)
    out.append(freeze(d, vc, "0" * 64))  # (b) wrong sha256
    open(os.path.join(d, "note.txt"), "w").write("x\n")
    c2 = commit_all(d, "a commit that does not add the record")
    out.append(freeze(d, c2, vs))  # (c) a commit that did not add it
    open(rp, "a").write(" ")
    c3 = commit_all(d, "record edited after its commit")
    out.append(freeze(d, c3, sha(rp)))  # (d) changed after its first commit
    ok = r0.returncode == 0 and all(r.returncode == 5 and "not the approved record" in r.stderr for r in out) \
        and not os.path.exists(os.path.join(d, "e2c_workload_freeze.json"))
    return ok, f"verify {r0.returncode}; freeze exits {[r.returncode for r in out]}"


def freeze_commitment_only(d):
    r0 = verify(d)
    vc, vs = approve_verify(d)
    out = []
    for bad in (COMMITMENT.upper(), COMMITMENT[:63], "g" * 64, hashlib.sha256(b"").hexdigest(), hashlib.sha256(b"\n").hexdigest(),
                "ab" * 24, LT.SALT):
        out.append(freeze(d, vc, vs, commitment=bad).returncode)
    base = ["freeze", "--expected-commit", head(d), "--approved-verify-commit", vc, "--approved-verify-sha256", vs]
    parse = [run(d, *base, "--salt-commitment-sha256", COMMITMENT, "--salt-file", os.path.join(d, "salt.txt")).returncode,
             run(d, *base, "--salt", LT.SALT).returncode, run(d, *base, "--salt-commitment", COMMITMENT).returncode]
    none = not os.path.exists(os.path.join(d, "e2c_workload_freeze.json"))
    good = freeze(d, vc, vs)
    ok = r0.returncode == 0 and out == [5] * 7 and parse == [2, 2, 2] and none and good.returncode == 0
    return ok, f"malformed commitments {out}; salt arguments rejected by the parser {parse}; valid commitment {good.returncode}"


def freeze_code_changed_since_verify(d):
    code = os.path.join(d, "code")
    for rel in ("experiments/gate_e/e2c/a.py", "experiments/gate_e/b.py"):
        os.makedirs(os.path.dirname(os.path.join(code, rel)), exist_ok=True)
        open(os.path.join(code, rel), "w").write("x = 1\n")
    commit_all(d, "synthetic code tree")
    set_cfg(d, code_root="code")
    r0 = verify(d)
    vc, vs = approve_verify(d)
    open(os.path.join(code, "experiments/gate_e/e2c/a.py"), "w").write("x = 2\n")
    commit_all(d, "code change after the approved verify")
    r = freeze(d, vc, vs)
    return (r0.returncode == 0 and r.returncode == 5 and "changed since the approved verify" in r.stderr
            and not os.path.exists(os.path.join(d, "e2c_workload_freeze.json")), f"verify {r0.returncode}, freeze {r.returncode}: {tail(r)}")


# ------------------------------------------------------------ F11 and the R* / M1* record (B2)


def f11_counts(d):
    out = []
    for k in ("H", "U", "R_star", "M1_star"):
        e = make_env(stub_keyspace=dict(LT.KS, counts=dict(LT.KS["counts"], **{k: LT.KS["counts"][k] + 1})))
        r = verify(e)
        v2_started = os.path.isdir(os.path.join(e, "stage2", "attempts", "01", "v2"))
        again = verify(e, resume=True)
        out.append((k, r.returncode, stop_status(e), record(e) is None, v2_started, again.returncode))
        shutil.rmtree(e, ignore_errors=True)
    ok = all(rc == 3 and st == "F11" and norec and not v2 and ag == 5 for _, rc, st, norec, v2, ag in out)
    return ok, f"{out} (exit, stop status, no record, V2 started, later launch)"


def f11_appendix_output(d):
    p = os.path.join(d, "stubs", "appendix_stdout.txt")
    open(p, "w").write(open(p).read().replace("6913", "6914"))
    r = verify(d)
    return r.returncode == 3 and stop_status(d) == "F11" and record(d) is None, f"exit {r.returncode}, stop {stop_status(d)}"


def keyspace_record_format(d):
    out = []
    for ks in (dict(LT.KS, counts={"R_star": 6913, "M1_star": 4129}), dict(LT.KS, extra="x"), dict(LT.KS, R_star_sha256="z" * 64)):
        e = make_env(stub_keyspace=ks)
        r = verify(e)
        out.append((r.returncode, stop_status(e)))
        shutil.rmtree(e, ignore_errors=True)
    return all(o == (3, "INTEGRITY_FAILURE") for o in out), f"{out} (an integrity failure, not F11)"


def prereg_changed(d):
    copy = os.path.join(d, "prereg_copy.md")
    t = open(os.path.join(HERE, "E2C_PREREG_DRAFT.md"), encoding="utf-8").read()
    open(copy, "w", encoding="utf-8").write(t.replace("remaining pool R 6913", "remaining pool R 6914", 1))
    commit_all(d, "a modified copy of the preregistration")
    set_cfg(d, prereg="prereg_copy.md")
    r = verify(d)
    return r.returncode == 5 and "preregistration" in r.stderr and not attempts(d), f"exit {r.returncode}: {tail(r)}"


# ------------------------------------------------------------ E1 sets (7.4 step 1)


def e1_sets_mismatch(d):
    out = []
    for how in ("byte", "extra_file", "anchor", "uncommitted"):
        e = make_env()
        if how == "byte":
            p = os.path.join(e, "sets", "diag_eval.jsonl")
            open(p, "w").write(open(p).read().replace("#", "$", 1))
        elif how == "extra_file":
            open(os.path.join(e, "sets", "other.jsonl"), "w").write("{}\n")
        elif how == "anchor":
            jdump(os.path.join(e, "e1", "run_freeze.json"), {"sets_manifest_sha256": "0" * 64, "workload": {"basis": {}}})
        if how != "uncommitted":
            commit_all(e, f"E1 tampered: {how}")
        else:
            open(os.path.join(e, "sets", "pool_b_k2.jsonl"), "a").write(" ")
        r = verify(e)
        out.append((how, r.returncode, bool(attempts(e))))
        shutil.rmtree(e, ignore_errors=True)
    return all(rc == 5 and not att for _, rc, att in out), f"{out} (exit, attempt made)"


def e1_set_changed_during_run(d):
    set_cfg(d, stub_mutate_file={"seed": 201, "update": 2, "path": os.path.join(d, "sets", "pool_c_k2.jsonl")})
    r = verify(d)
    return r.returncode == 3 and stop_status(d) == "INTEGRITY_FAILURE" and "changed during the run" in r.stderr, \
        f"exit {r.returncode}: {tail(r)}"


# ------------------------------------------------------------ V2 (integrity failure, not F11)


def v2_heldout_in_stream(d):
    set_cfg(d, stub_inject_heldout={"seed": 205, "update": 2, "body": held_body()})
    r = verify(d)
    return (r.returncode == 3 and stop_status(d) == "INTEGRITY_FAILURE_V2" and record(d) is None and "seed 205" in r.stderr,
            f"exit {r.returncode}, stop {stop_status(d)}: {tail(r)}")


def v2_reference_chain_mismatch(d):
    p = os.path.join(d, "refs", "run_s99.json")
    rec = json.load(open(p))
    rec["batch_chain"]["2"] = "0" * 64
    jdump(p, rec)
    commit_all(d, "a stage-1 chain record differing from the stream")
    cfg = json.load(open(os.path.join(d, "config.json")))
    set_cfg(d, reference_digest=refs_digest(d, cfg)[1])  # the reference set as approved: V2 itself must catch it
    r = verify(d)
    return r.returncode == 3 and stop_status(d) == "INTEGRITY_FAILURE_V2" and "update 2 differs" in r.stderr, f"exit {r.returncode}: {tail(r)}"


def v2_reference_files_changed(d):
    p = os.path.join(d, "refs", "run_s201.json")
    rec = json.load(open(p))
    rec["batch_chain"]["3"] = "0" * 64
    jdump(p, rec)
    commit_all(d, "a stage-1 chain record changed after its approval")
    r = verify(d)
    return r.returncode == 5 and "reference chains" in r.stderr and not attempts(d), f"exit {r.returncode}: {tail(r)}"


def v2_non_u_set_heldout(d):
    e = make_env(nonu_held=1)
    r = verify(e)
    st = stop_status(e)
    shutil.rmtree(e, ignore_errors=True)
    return r.returncode == 3 and st == "INTEGRITY_FAILURE_V2" and "dev_seen" in r.stderr, f"exit {r.returncode}, stop {st}: {tail(r)}"


def v2_missing_seed(d):
    set_cfg(d, stub_skip_seed=224)
    r = verify(d)
    return r.returncode == 6 and "seed 224" in r.stderr and record(d) is None, f"exit {r.returncode}: {tail(r)}"


def v2_seed_table(d):
    want = list(range(1, 6)) + [91, 92, 93, 99] + list(range(201, 225))
    ok = S2.SEEDS_33 == want and len(set(want)) == 33 and R.training_stream_seeds() == want
    return ok, f"{len(S2.SEEDS_33)} seeds = run_e2c.training_stream_seeds() {R.training_stream_seeds() == want}"


# ------------------------------------------------------------ interruption, resumption, budget, launch state


def interrupt_and_resume(d):
    set_cfg(d, stub_sleep_per_update=0.3)
    p = popen_verify(d)
    v2 = os.path.join(d, "stage2", "attempts", "01", "v2")
    wait_for(lambda: os.path.isdir(v2) and len(os.listdir(v2)) >= 2)
    p.send_signal(signal.SIGTERM)
    p.wait()
    st1 = summary(d, "01")["status"]
    set_cfg(d, stub_sleep_per_update=None)
    r = verify(d, resume=True)
    led = ledger(d)
    ok = (p.returncode == 130 and st1 == "INTERRUPTED" and r.returncode == 0 and attempts(d) == ["01", "02"]
          and [iv["status"] for iv in led["intervals"]] == ["INTERRUPTED", "PASS"] and led["used_seconds"] > 0
          and record(d)["status"] == "PASS")
    return ok, f"interrupted {p.returncode} ({st1}), resume {r.returncode}; intervals {[iv['status'] for iv in led['intervals']]}"


def resume_nondeterministic(d):
    set_cfg(d, stub_sleep_per_update=0.3)
    p = popen_verify(d)
    done = os.path.join(d, "stage2", "attempts", "01", "v2", "seed_002.json")
    wait_for(lambda: os.path.exists(done))
    p.send_signal(signal.SIGTERM)
    p.wait()
    set_cfg(d, stub_sleep_per_update=None, stub_nondet_seeds=[2])  # seed 2 has no stage-1 record: only the attempt comparison sees it
    r = verify(d, resume=True)
    return (p.returncode == 130 and r.returncode == 3 and "differs from attempt 01" in r.stderr and record(d) is None,
            f"interrupted {p.returncode}, resume {r.returncode}: {tail(r)}")


def crash_then_resume(d):
    set_cfg(d, stub_crash_after="v2_streams")
    r1 = verify(d)
    set_cfg(d, stub_crash_after=None)
    r2 = verify(d, resume=True)
    led = ledger(d)
    iv1 = led["intervals"][0]
    ok = (r1.returncode == 9 and r2.returncode == 0 and iv1["status"] == "stale" and "process gone" in iv1["closed_by"]
          and record(d)["status"] == "PASS" and attempts(d) == ["01", "02"])
    return ok, f"crash exit {r1.returncode}, resume {r2.returncode}; first interval {iv1['status']} ({iv1.get('closed_by')})"


def budget_cap(d):
    set_cfg(d, cap_seconds=1.0, stub_sleep_per_update=0.2)
    r1 = verify(d)
    r2 = verify(d, resume=True)
    led = ledger(d)
    ok = (r1.returncode == 7 and r2.returncode == 7 and [iv["status"] for iv in led["intervals"]] == ["BUDGET_CAP", "BUDGET_CAP"]
          and led["used_seconds"] >= 1.0 and record(d) is None and stop_status(d) is None)
    return ok, f"exits {r1.returncode}, {r2.returncode}; used {led['used_seconds']} s of 1 s over {len(led['intervals'])} launches"


def stale_interval(d):
    os.makedirs(os.path.join(d, "stage2"))
    base = {"stage": 2, "cap_seconds": 300, "intervals": [{"id": 1, "label": "verify", "pid": 999999, "pid_start": "1",
                                                           "start": time.time() - 5, "heartbeat": time.time() - 4, "end": None,
                                                           "status": None}]}
    jdump(os.path.join(d, "stage2", "budget_ledger_s2.json"), base)
    r1 = verify(d)
    iv = ledger(d)["intervals"][0]
    e = make_env()
    os.makedirs(os.path.join(e, "stage2"))
    live = dict(base["intervals"][0], pid=os.getpid(), pid_start=S2._proc_start(os.getpid()))
    jdump(os.path.join(e, "stage2", "budget_ledger_s2.json"), dict(base, intervals=[live]))
    r2 = verify(e)
    shutil.rmtree(e, ignore_errors=True)
    return (r1.returncode == 0 and iv["status"] == "stale" and r2.returncode == 5 and "another stage-2 process" in r2.stderr,
            f"dead pid: exit {r1.returncode}, interval {iv['status']}; live pid: exit {r2.returncode}")


def launch_state(d):
    os.makedirs(os.path.join(d, "stage2", "attempts", "01"))
    a = verify(d)
    shutil.rmtree(os.path.join(d, "stage2", "attempts"))
    b = verify(d, resume=True)
    c0 = verify(d)
    c = verify(d, resume=True)
    ok = (a.returncode == 5 and "continue with --resume" in a.stderr and b.returncode == 5 and "without an earlier attempt" in b.stderr
          and c0.returncode == 0 and c.returncode == 5 and "written once" in c.stderr)
    return ok, f"first launch over an attempt {a.returncode}, resume without attempt {b.returncode}, pass {c0.returncode}, after pass {c.returncode}"


def git_state(d):
    a = verify(d, commit="0" * 40)
    open(os.path.join(d, "untracked.txt"), "w").write("x\n")
    b = verify(d)
    os.remove(os.path.join(d, "untracked.txt"))
    os.makedirs(os.path.join(d, "experiments", "gate_e", "e2c"))
    open(os.path.join(d, "experiments", "gate_e", "e2c", "extra.py"), "w").write("x = 1\n")
    commit_all(d, "a code file outside the allowed changes")
    c = verify(d)
    set_cfg(d, allowed_changes={"experiments/gate_e/e2c/extra.py": "A"})
    e = verify(d)
    ok = (a.returncode == 5 and "not the reviewed commit" in a.stderr and b.returncode == 5 and "uncommitted changes" in b.stderr
          and c.returncode == 5 and "differ from the allowed" in c.stderr and e.returncode == 0)
    return ok, f"wrong HEAD {a.returncode}, dirty tree {b.returncode}, unallowed code change {c.returncode}, allowed {e.returncode}"


def inputs_mismatch(d):
    out = []
    e = make_env()
    rec = json.load(open(os.path.join(e, "environment.json")))
    jdump(os.path.join(e, "environment.json"), dict(rec, torch="0.0"))
    commit_all(e, "another environment")
    out.append(("environment", verify(e).returncode))
    shutil.rmtree(e, ignore_errors=True)
    for key, src in (("lambda_file", "stage1/gate4/lambda_selected.json"), ("calibration_file", "stage1/gate4/calibration.json")):
        e = make_env()
        c = json.load(open(os.path.join(HERE, src)))
        if key == "lambda_file":
            c["lambda2"]["openmythos"] = 0.1411
        else:
            c["selection_summary"]["lambda2"]["openmythos"] = 0.1411
        jdump(os.path.join(e, "copy.json"), c)
        commit_all(e, "a changed copy")
        set_cfg(e, **{key: "copy.json"})
        out.append((key, verify(e).returncode))
        shutil.rmtree(e, ignore_errors=True)
    return all(rc == 5 for _, rc in out), f"{out}"


def key_rules_mismatch(d):
    set_cfg(d, key_rule_expected_heldout=json.load(open(os.path.join(d, "config.json")))["key_rule_expected_heldout"] + 1)
    r = verify(d)
    return r.returncode == 3 and stop_status(d) == "INTEGRITY_FAILURE" and "key rules" in r.stderr, f"exit {r.returncode}: {tail(r)}"


def leak_scan_hit(d):
    set_cfg(d, stub_leak=True)
    r = verify(d)
    return r.returncode == 3 and "key-like" in r.stderr and record(d) is None, f"exit {r.returncode}: {tail(r)}"


def checkpoint_access_blocked(d):
    set_cfg(d, stub_open_checkpoint=201)
    r = verify(d)
    return (r.returncode == 3 and stop_status(d) == "INTEGRITY_FAILURE" and not os.path.exists(os.path.join(d, "x.pt")),
            f"exit {r.returncode}, x.pt created {os.path.exists(os.path.join(d, 'x.pt'))}: {tail(r)}")


# ------------------------------------------------------------ real entry points refuse; units


def real_entry_refuses(d):
    real_out, real_fz = os.path.join(HERE, "stage2"), os.path.join(HERE, "e2c_workload_freeze.json")
    before = (os.path.exists(real_out), os.path.exists(real_fz))
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("E2C_", "STUB_"))}
    hc = git(ROOT, "rev-parse", "HEAD")
    cases = {"verify": ["verify", "--expected-commit", hc],
             "verify_with_text_only": ["verify", "--expected-commit", hc, "--authorization", "text without the variable"],
             "freeze": ["freeze", "--expected-commit", hc, "--approved-verify-commit", hc, "--approved-verify-sha256", "0" * 64,
                        "--salt-commitment-sha256", COMMITMENT],
             "worker": ["_v2-worker", "--attempt", d, "--seeds", "1"]}
    out = {k: run(d, *v, env=clean) for k, v in cases.items()}
    out["test_dir_in_real_mode"] = run(d, "verify", "--expected-commit", hc, env=dict(clean, E2C_TEST_DIR=d))
    out["keyspace_variable_set"] = run(d, "verify", "--expected-commit", hc, env=dict(clean, E2C_KEYSPACE_STAGE="0"))
    out["test_mode_with_authorization"] = run(d, "verify", "--expected-commit", head(d), env=env_s2(d, E2C_STAGE2_AUTHORIZED="x"))
    after = (os.path.exists(real_out), os.path.exists(real_fz))
    ok = all(r.returncode == 5 for r in out.values()) and before == after == (False, False) and not attempts(d)
    return ok, f"{ {k: r.returncode for k, r in out.items()} }; e2c/stage2 and the real freeze exist before / after: {before} / {after}"


def unit_write_once(d):
    p = os.path.join(d, "w.json")
    S2.write_once(p, b"one")
    try:
        S2.write_once(p, b"two")
        second = "written"
    except FileExistsError:
        second = "refused"
    S2.write_once_or_same(p, b"one")
    try:
        S2.write_once_or_same(p, b"two")
        third = "accepted"
    except S2.S2Stop as s:
        third = f"exit {s.code}"
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import e2c_stage2 as S\n"
            "try:\n    S.write_once(sys.argv[2], sys.argv[3].encode()); print('won')\nexcept FileExistsError:\n    print('lost')")
    q = os.path.join(d, "race.json")
    procs = [subprocess.Popen([sys.executable, "-c", code, HERE, q, str(i)], stdout=subprocess.PIPE, text=True) for i in range(6)]
    res = sorted(p.communicate()[0].strip() for p in procs)
    leftovers = [f for f in os.listdir(d) if ".tmp." in f]
    ok = open(p, "rb").read() == b"one" and second == "refused" and third == "exit 3" and res.count("won") == 1 and not leftovers
    return ok, f"second write {second}, different content {third}; race of 6 writers {res}; temporary files left {leftovers}"


def unit_appendix_a(d):
    script, stdout, letters = S2.appendix_a(os.path.join(HERE, "E2C_PREREG_DRAFT.md"))
    from e_common import LETTERS
    copy = os.path.join(d, "p.md")
    t = open(os.path.join(HERE, "E2C_PREREG_DRAFT.md"), encoding="utf-8").read()
    open(copy, "w", encoding="utf-8").write(t.replace("if d1 == d2: continue", "if d1 == d2:  continue", 1))
    try:
        S2.appendix_a(copy)
        tampered = "accepted"
    except S2.S2Stop as s:
        tampered = f"exit {s.code}"
    ok = (hashlib.sha256(script.encode()).hexdigest() == S2.APPENDIX_A_SCRIPT_SHA256 and letters == LETTERS == T.LETTERS
          and stdout.startswith("keys total 119340 held-out 12006") and "remaining pool R 6913" in stdout
          and S2.leak_scan(texts=[script, stdout])["key_like_hits"] == 0 and tampered == "exit 5")
    return ok, f"script {S2.APPENDIX_A_SCRIPT_SHA256[:12]} rebuilt from the preregistration text; tampered copy {tampered}"


def unit_tripwires(d):
    code = ("import os, sys; sys.path.insert(0, sys.argv[1]); import e2c_stage2 as S, e2c_test2 as T\n"
            "out = []\n"
            "try:\n    T.keyspace('x')\nexcept T.NotAuthorized:\n    out.append('guard')\n"
            "S.install_guards(True)\n"
            "for f in (T.keyspace, T.training_stream_keys, T.generate):\n"
            "    try:\n        f('x')\n    except RuntimeError as e:\n        out.append('tripwire' if 'TRIPWIRE' in str(e) else 'other')\n"
            "try:\n    open(os.path.join(sys.argv[2], 'y.pt'), 'w')\nexcept S.CheckpointAccess:\n    out.append('audit')\n"
            "print(','.join(out))")
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("E2C_", "STUB_"))}
    r = subprocess.run([sys.executable, "-c", code, HERE, d], env=clean, capture_output=True, text=True)
    got = r.stdout.strip()
    return got == "guard,tripwire,tripwire,tripwire,audit" and not os.path.exists(os.path.join(d, "y.pt")), \
        f"{got or r.stderr[-200:]} (keyspace() refuses without E2C_KEYSPACE_STAGE; test-mode tripwires; checkpoint audit hook)"


def unit_chain_definition(d):
    """The batch-chain definition of V2 is train_e2c.py's (same lines), and its generator E1's."""
    tr = open(os.path.join(HERE, "train_e2c.py")).read()
    s2 = open(DRIVER).read()
    need_tr = ["rng = train_rng_k2(args.seed)", "draw = lambda: train_sample_k2(rng)", "rows = [draw() for _ in range(args.batch_size)]",
               "x, y = encode_rows(rows)", "first_batch_sha = hashlib.sha256(x.numpy().tobytes()).hexdigest()", "cv = chain.update(x)",
               "if step1 % 100 == 0 or step1 == args.steps:", "chain = C.HashChain() if records else None", "from data import encode_rows"]
    need_s2 = ["rng = train_rng_k2(seed)", "draw, encode = (lambda: train_sample_k2(rng)), encode_rows", "rows = [draw() for _ in range(batch)]",
               "x, _ = encode(rows)", "first = hashlib.sha256(x.numpy().tobytes()).hexdigest()", "cv = chain.update(x)",
               "if step1 % 100 == 0 or step1 == updates or step1 in extra:", "chain, log, hits, n, first, extra = C.HashChain()",
               "from data import encode_rows", "from e_task import train_rng_k2, train_sample_k2"]
    miss = [x for x in need_tr if x not in tr] + [x for x in need_s2 if x not in s2]
    return not miss, f"missing lines {miss}" if miss else "train_e2c.py and e2c_stage2.stream_check share the stream and chain lines"


CASES = [verify_pass, verify_deterministic, freeze_pass_launcher_accepts, freeze_replaced_refused_by_launcher, freeze_written_once,
         freeze_needs_approved_record, freeze_commitment_only, freeze_code_changed_since_verify, f11_counts, f11_appendix_output,
         keyspace_record_format, prereg_changed, e1_sets_mismatch, e1_set_changed_during_run, v2_heldout_in_stream,
         v2_reference_chain_mismatch, v2_reference_files_changed, v2_non_u_set_heldout, v2_missing_seed, v2_seed_table,
         interrupt_and_resume, resume_nondeterministic, crash_then_resume, budget_cap, stale_interval, launch_state, git_state,
         inputs_mismatch, key_rules_mismatch, leak_scan_hit, checkpoint_access_blocked, real_entry_refuses, unit_write_once,
         unit_appendix_a, unit_tripwires, unit_chain_definition]


def main():
    if "--out" not in sys.argv:
        sys.exit("usage: e2c_stage2_tests.py --out PATH")
    out_path = os.path.abspath(sys.argv[sys.argv.index("--out") + 1])
    if os.path.exists(out_path):
        sys.exit(f"REFUSED: {out_path} exists; an earlier result is never overwritten")
    if any(k in os.environ for k in ("E2C_KEYSPACE_STAGE", "E2C_STAGE2_AUTHORIZED", "E2C_S2_TEST_DIR")):
        sys.exit("REFUSED: the tests run without E2C_KEYSPACE_STAGE, E2C_STAGE2_AUTHORIZED and E2C_S2_TEST_DIR")
    names = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    res = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cases": {}}
    t0 = time.time()
    for fn in CASES:
        if names and fn.__name__ not in names:
            continue
        d = make_env()
        n0, t = INVOCATIONS[0], time.time()
        try:
            ok, info = fn(d)
        except Exception as e:  # noqa: BLE001
            ok, info = False, f"exception {e!r}"
        res["cases"][fn.__name__] = {"pass": bool(ok), "info": info, "seconds": round(time.time() - t, 1),
                                     "invocations": INVOCATIONS[0] - n0}
        print(f"{'PASS' if ok else 'FAIL'} {fn.__name__}: {info}", flush=True)
        if ok:
            shutil.rmtree(d, ignore_errors=True)
        else:
            res["cases"][fn.__name__]["dir"] = d
    res.update(finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), seconds=round(time.time() - t0, 1),
               invocations=INVOCATIONS[0], passed=sum(c["pass"] for c in res["cases"].values()), total=len(res["cases"]),
               code_sha256={f: sha(os.path.join(HERE, f)) for f in ("e2c_stage2.py", "e2c_stage2_tests.py", "run_e2c.py",
                                                                    "e2c_launcher_tests.py")})
    res["all_pass"] = res["passed"] == res["total"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    S2.write_once(out_path, (json.dumps(res, indent=1, ensure_ascii=False) + "\n").encode())
    print("I2 stage-2 tests", "PASS" if res["all_pass"] else "FAIL", f"{res['passed']}/{res['total']}, {res['invocations']} invocations")
    sys.exit(0 if res["all_pass"] else 3)


if __name__ == "__main__":
    main()
