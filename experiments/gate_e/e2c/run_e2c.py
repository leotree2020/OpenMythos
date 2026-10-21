#!/usr/bin/env python3
"""
E2-c launcher with resumption (E2C_PREREG_DRAFT 3.5, 7.4, 8.4, 9, 13).
Written and fault-tested in stage 1 (V4); not run on real data before the
stage-3 / stage-4 authorizations. The freeze file e2c_workload_freeze.json is
made in stage 2 (e2c_stage2.py freeze).

    python experiments/gate_e/e2c/run_e2c.py --stage 3 A             first launch of stage 3
    python experiments/gate_e/e2c/run_e2c.py --stage 3 A --resume    every later launch
    python experiments/gate_e/e2c/run_e2c.py --stage 4 A --salt-file F [--resume]
    A = --approved-stage2-commit C --approved-freeze-sha256 S, both taken from
        the stage-2 review, never from a file of the working tree

Every launch checks that the freeze file has sha256 S and was added by commit
C (an ancestor of HEAD, not a shallow clone) and never changed after it; the
first launch of stage 3 binds C and S in run_freeze.json, and stage 4 runs
only with the C, S and freeze sha256 bound there.

Exit codes (E1 conventions; 9 of the preregistration):
    5  refused (F1): the code tree, preregistration, design record or E1 set
       manifest differs from the freeze; a frozen item is missing (lambda,
       lambda2, salt commitment, R* / M1* hashes) or differs from the
       approved constants; the R* / M1* record is not in the stage-4
       keyspace job's format with Appendix A's H, U, R_star, M1_star counts;
       the salt commitment is not 64 lowercase hex digits (or hashes an empty
       line); the approvals are missing, the freeze is not the approved one,
       or stage 4's freeze / approvals differ from those bound at stage 3;
       first launch over existing outputs; resume without a run freeze or
       after a frozen item changed; stage 4 before stage 3 is complete; test
       stubs without a test directory
    3  integrity failure: pairing (F8: common items, heads, lambda, digit code,
       E_W^C1 = 0 / not finite), a re-trained run differing from its kept
       attempt (F8), a non-finite loss or gradient (F7), checkpoint push /
       retrieval / hash (F5), a result or judgment differing from its ledger
       (F5), a diagnostic hard check (F6), salt / R* / M1* hashes / isolation
       of test2 (F10, nothing judged)
    4  any other error; 6 outputs missing after a stage
    7  the stage's cumulative cap is reached (F9: stage 3 42 h, stage 4 2 h)
Records (atomic writes): run_freeze.json, checkpoints_manifest.json,
pairing_ledger.json, results_ledger.json, judgments_ledger.json,
budget_ledger.json, test2_record.json.
Fault-injection tests only (e2c_launcher_tests.py): E2C_TEST_DIR redirects
every output there and E2C_TEST_CMDS (JSON) replaces train / archive /
restore / diag / keyspace / test2 / judge / sync by stubs; checkpoints are
then plain files checked by sha256. E2C_TEST_PLAN (JSON seeds, only with
E2C_TEST_DIR) shortens the run plan so a test case runs in seconds; the
freeze still carries the approved seed table.
"""

import glob
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402
import run_gate_e as E1L  # noqa: E402  E1 launcher: Stop, Launcher (queue, kill, quarantine), helpers; read-only
from e_common import ROOT, atomic_write_json  # noqa: E402

Stop, sha256_file, load_json, result_digest = E1L.Stop, E1L.sha256_file, E1L.load_json, E1L.result_digest
FREEZE_FILE = "e2c_workload_freeze.json"
CODE_GLOBS = ("experiments/gate_e/e2c/*.py", "experiments/gate_e/*.py", "experiments/gate_d/*.py",
              "experiments/basic_learn/models.py", "experiments/gen_gate_a/*.py", "experiments/budget_a/schedule.py",
              "experiments/loop_mech/*.py", "open_mythos/*.py")
REJECTION_TABLES = {20: {0: 0, 1: 0, 2: 1, 3: 3, 4: 4, 5: 6, 6: 8, 7: 9, 8: 11},
                    24: {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 5, 6: 6, 7: 8, 8: 9, 9: 11, 10: 13},
                    30: {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 3, 6: 4, 7: 6, 8: 7, 9: 9, 10: 11, 11: 12, 12: 14, 13: 15}}
APPROVED = {
    "seeds": {"openmythos": list(range(201, 225)), "transformer": list(range(201, 211)), "historical": [1, 2, 3, 4, 5]},
    "conditions": {"confirmatory": ["C0", "C1", "C2"], "historical": ["C1", "C2"]},
    "train_updates": 12000, "archive_steps": [t for t in C.D2C_STEPS if t], "d2c_steps": list(C.D2C_STEPS),
    "d2c_heavy": list(C.D2C_HEAVY), "d2c_m0": list(C.D2C_M0), "calibration_seeds": list(C.CAL_SEEDS),
    "caps_hours": {"stage3": 42, "stage4": 2}, "parallel_workers": 4,
    "alpha": {"openmythos": {"superiority_holm": 0.025, "exclusion": 0.025}, "transformer": {"superiority_holm": 0.05}},
    "rejection_tables": {str(n): {str(b): c for b, c in t.items()} for n, t in REJECTION_TABLES.items()},
    "lambda_candidates": list(C.LAMBDA_CANDIDATES), "early_window_updates": C.W_UPDATES,
}
ARMS = ("openmythos", "transformer")
# stage-2 interface: the R* / M1* record is the stage-4 keyspace job's output with Appendix A's counts (B2);
# the salt commitment is sha256(salt) as 64 lowercase hex digits, never the salt (B3)
KEYSPACE_COUNTS = {"H": 12006, "U": 5093, "R_star": 6913, "M1_star": 4129}
HEX64, HEX40 = re.compile(r"[0-9a-f]{64}\Z"), re.compile(r"[0-9a-f]{40}\Z")
EMPTY_LINE_HASHES = (hashlib.sha256(b"").hexdigest(), hashlib.sha256(b"\n").hexdigest())
ARTIFACT_PREFIX = "gate_e/e2c"
SYNC_EVERY_STATES, SYNC_EVERY_S = 10, 1200


def paths():
    test, cmds = os.environ.get("E2C_TEST_DIR"), os.environ.get("E2C_TEST_CMDS")
    if cmds and not test:
        raise Stop(5, "REFUSED: E2C_TEST_CMDS only with E2C_TEST_DIR")
    base = test or HERE
    p = {k: os.path.join(base, k) for k in ("runs", "results", "judgments", "logs")}
    p.update({"quarantine": os.path.join(base, "quarantine"), "lfs_tmp": os.path.join(base, "lfs_tmp"),
              "freeze": os.path.join(base, FREEZE_FILE), "prereg": os.path.join(HERE, "E2C_PREREG_DRAFT.md"),
              "design_review": os.path.join(HERE, "DESIGN_REVIEW.md"), "sets_manifest": os.path.join(GE, "sets", "manifest.json"),
              "code_root": os.path.abspath(ROOT), "test": bool(test), "stubs": json.load(open(cmds)) if cmds else {},
              "base": base})
    for k in ("run_freeze", "checkpoints_manifest", "pairing_ledger", "results_ledger", "judgments_ledger",
              "budget_ledger", "test2_record"):
        p[k] = os.path.join(base, f"{k}.json")
    cap = os.environ.get("E2C_TEST_CAP_SECONDS") if test else None
    p["cap_override"] = float(cap) if cap else None
    return p


def code_tree(root):
    files = sorted({f for g in CODE_GLOBS for f in glob.glob(os.path.join(root, g))})
    per = {os.path.relpath(f, root): sha256_file(f) for f in files}
    return hashlib.sha256("".join(f"{k}:{v}\n" for k, v in per.items()).encode()).hexdigest(), per


def basis(p):
    tree, per = code_tree(p["code_root"])
    return {"code_tree_sha256": tree, "code_files": per, "preregistration_sha256": sha256_file(p["prereg"]),
            "design_review_sha256": sha256_file(p["design_review"]), "sets_manifest_sha256": sha256_file(p["sets_manifest"])}


def make_baseline(p, lam, lam2, salt_commitment, keyspace_hashes):
    """Content of the freeze file (made in stage 2 with the stage-1 calibration
    and the stage-2 hashes; the tests make theirs with simulated values)."""
    return dict(APPROVED, **{"lambda": lam, "lambda2": lam2, "salt_commitment_sha256": salt_commitment,
                              "keyspace": keyspace_hashes, "basis": basis(p)})


def check_baseline(fz, now):
    diff = []
    b = fz.get("basis") or {}
    for k in ("code_tree_sha256", "preregistration_sha256", "design_review_sha256", "sets_manifest_sha256"):
        if b.get(k) != now[k]:
            diff.append(f"{k}: freeze {str(b.get(k))[:12]} != now {now[k][:12]}")
    if b.get("code_tree_sha256") != now["code_tree_sha256"]:
        old, new = b.get("code_files", {}), now["code_files"]
        diff.append(f"code files changed: {sorted(f for f in set(old) | set(new) if old.get(f) != new.get(f))[:10]}")
    for k, v in APPROVED.items():
        if fz.get(k) != v:
            diff.append(f"{k}: freeze {str(fz.get(k))[:60]} != approved {str(v)[:60]}")
    for k in ("lambda", "lambda2"):
        for arm in ARMS:
            v = (fz.get(k) or {}).get(arm)
            if not (isinstance(v, (int, float)) and v > 0 and math.isfinite(v)):
                diff.append(f"{k} for {arm} missing or not a positive number")
    for arm in ARMS:
        lam, lam2 = (fz.get("lambda") or {}).get(arm), (fz.get("lambda2") or {}).get(arm)
        if isinstance(lam, (int, float)) and lam not in C.LAMBDA_CANDIDATES:
            diff.append(f"lambda for {arm} is not a candidate")
        if isinstance(lam, (int, float)) and isinstance(lam2, (int, float)) and not (lam / 10 - 1e-12 <= lam2 <= 10 * lam + 1e-12):
            diff.append(f"lambda2 for {arm} outside [lambda/10, 10 lambda]")
    sc = fz.get("salt_commitment_sha256")
    if sc is None:
        diff.append("salt commitment missing")
    elif commitment_problem(sc):
        diff.append(f"salt commitment malformed: {commitment_problem(sc)}")
    bad = keyspace_format_problem(fz.get("keyspace"))
    if bad:
        diff.append(bad)
    elif fz["keyspace"]["counts"] != KEYSPACE_COUNTS:
        diff.append(f"R* / M1* counts {fz['keyspace']['counts']} differ from Appendix A {KEYSPACE_COUNTS}")
    return diff


def commitment_problem(sc):
    if not (isinstance(sc, str) and HEX64.match(sc)):
        return "not 64 lowercase hex digits"
    if sc in EMPTY_LINE_HASHES:
        return "the sha256 of an empty line, not of a salt"
    return None


def keyspace_format_problem(ks):
    """B2: the record must have exactly the fields of the stage-4 keyspace job (e2c_stage4.py keyspace), which
    stage 4 compares as a whole: two 64-hex hashes and the four counts H, U, R_star, M1_star."""
    if not (isinstance(ks, dict) and ks.get("R_star_sha256") and ks.get("M1_star_sha256") and ks.get("counts")):
        return "R* / M1* hashes missing"
    if set(ks) != {"R_star_sha256", "M1_star_sha256", "counts"} or not all(
            isinstance(ks[k], str) and HEX64.match(ks[k]) for k in ("R_star_sha256", "M1_star_sha256")):
        return "R* / M1* record not in the format of the stage-4 keyspace job"
    c = ks["counts"]
    if not (isinstance(c, dict) and set(c) == set(KEYSPACE_COUNTS) and all(type(v) is int for v in c.values())):
        return f"R* / M1* counts {c} are not the full H, U, R_star, M1_star structure"
    return None


def _git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    return r.returncode, r.stdout


def git_anchor(path, commit, sha):
    """B1: path must have sha256 `sha` and be added by `commit` (an ancestor of HEAD) and never changed after it.
    commit and sha come from the review (command line), not from any file of the working tree. Returns problems."""
    if not (isinstance(commit, str) and HEX40.match(commit)):
        return ["the approved commit is not a 40-digit lowercase hex sha"]
    if not (isinstance(sha, str) and HEX64.match(sha)):
        return ["the approved sha256 is not 64 lowercase hex digits"]
    if not os.path.isfile(path):
        return [f"{os.path.basename(path)} missing"]
    bad = []
    if sha256_file(path) != sha:
        bad.append(f"{os.path.basename(path)} has sha256 {sha256_file(path)[:12]}, not the approved {sha[:12]}")
    rc, top = _git(os.path.dirname(os.path.abspath(path)), "rev-parse", "--show-toplevel")
    if rc:
        return bad + ["not inside a git repository"]
    top = top.decode().strip()
    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(top))
    if _git(top, "rev-parse", "--is-shallow-repository")[1].decode().strip() != "false":
        return bad + ["the clone is shallow (run git fetch --unshallow first): the history cannot be checked"]
    if _git(top, "cat-file", "-e", commit + "^{commit}")[0]:
        return bad + [f"the approved commit {commit[:12]} does not exist here"]
    if _git(top, "merge-base", "--is-ancestor", commit, "HEAD")[0]:
        bad.append(f"the approved commit {commit[:12]} is not an ancestor of HEAD")
    rc, blob = _git(top, "show", f"{commit}:{rel}")
    if rc or hashlib.sha256(blob).hexdigest() != sha:
        bad.append(f"{rel} at the approved commit does not have the approved sha256")
    if _git(top, "rev-list", "HEAD", "--", rel)[1].decode().split() != [commit]:
        bad.append(f"{rel} must be added once, by the approved commit, and never changed after it")
    if _git(top, "status", "--porcelain", "--", rel)[1].strip():
        bad.append(f"{rel} differs from its committed version")
    return bad


def training_stream_seeds():
    """The 33 seeds whose training streams V2 (stage 2) and the test2 isolation check (stage 4) cover."""
    s = APPROVED["seeds"]
    return sorted(set(s["openmythos"] + s["transformer"] + s["historical"] + APPROVED["calibration_seeds"] + [C.IMPL_SEED]))


def runs_planned():
    seeds = APPROVED["seeds"]
    if os.environ.get("E2C_TEST_PLAN") and os.environ.get("E2C_TEST_DIR"):
        seeds = json.loads(os.environ["E2C_TEST_PLAN"])
    out = []
    for arm in ARMS:
        for s in seeds[arm]:
            out += [f"{c}_{arm}_s{s}" for c in APPROVED["conditions"]["confirmatory"]]
    for arm in ARMS:
        for s in seeds["historical"]:
            out += [f"{c}_{arm}_s{s}" for c in APPROVED["conditions"]["historical"]]
    return out


def historical_seeds():
    if os.environ.get("E2C_TEST_PLAN") and os.environ.get("E2C_TEST_DIR"):
        return json.loads(os.environ["E2C_TEST_PLAN"])["historical"]
    return APPROVED["seeds"]["historical"]


def split(run):
    cond, arm, s = run.split("_")
    return cond, arm, int(s[1:])


def states_planned():
    return [f"{r}_step{t}" for r in runs_planned() for t in APPROVED["d2c_steps"]]


class Launcher(E1L.Launcher):
    def start(self, name, argv):
        # E1's start uses an environment fixed at import; the stage-4 jobs need the current one
        f = open(os.path.join(self.p["logs"], f"{name}.log"), "a")
        proc = subprocess.Popen(argv, cwd=os.path.abspath(ROOT), env=dict(os.environ, PYTHONPATH=os.path.abspath(ROOT)),
                                stdout=f, stderr=f, start_new_session=True)
        self.jobs[proc.pid] = (name, proc, f)
        self.log(f"started {name} (pid {proc.pid})")

    def sync(self, msg):
        if "sync" in self.p["stubs"]:
            import shlex
            rc = subprocess.run(shlex.split(self.p["stubs"]["sync"].format(msg=msg.replace(" ", "_")))).returncode
            if rc:
                raise Stop(4, f"RUN ERROR: sync failed ({msg})")
            return
        if self.p["test"]:
            return
        cwd = os.path.abspath(ROOT)
        items = []
        for x in ("run_freeze", "checkpoints_manifest", "pairing_ledger", "results_ledger", "judgments_ledger",
                  "budget_ledger", "test2_record"):
            if os.path.exists(self.p[x]):
                items.append(self.p[x])
        for d in ("results", "judgments", "runs", "logs", "quarantine"):
            for r, dirs, fs in os.walk(self.p[d]):
                items += [os.path.join(r, f) for f in fs if not f.endswith(".pt") and ".tmp." not in f]
        items = [os.path.relpath(f, cwd) for f in sorted(items)]
        for i in range(0, len(items), 200):
            subprocess.run(["git", "add", "-f", "--"] + items[i:i + 200], cwd=cwd, check=True, capture_output=True)
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=cwd, capture_output=True, text=True).stdout.split()
        if any(f.endswith(".pt") for f in staged):
            subprocess.run(["git", "reset", "-q"], cwd=cwd)
            raise Stop(4, "RUN ERROR: a checkpoint file was about to be committed to the research branch")
        if not staged:
            return
        subprocess.run(["git", "commit", "-q", "-m", f"gate_e/e2c: run records - {msg}"], cwd=cwd, check=True)
        for i in range(5):
            if subprocess.run(["git", "push", "-q", "origin", "HEAD"], cwd=cwd, capture_output=True).returncode == 0:
                self.log(f"synced run records ({msg})")
                return
            time.sleep(2 ** (i + 1))
        raise Stop(4, f"RUN ERROR: push of the run records failed ({msg})")


def param_hash_of(p, path, arm):
    if p["test"]:
        return sha256_file(path)
    from e_storage import ckpt_param_hash
    return ckpt_param_hash(path, arm, 2)


# ------------------------------------------------------------ stage 3: pairing (3.5)


PAIR_COMMON = ("init_param_sha256", "batch_chain", "first_batch_sha256", "lr_schedule_sha256", "optimizer", "clip", "batch_size")


def pairing_check(p, run, rec, fz, done):
    """F8 checks of one finished run against the freeze and the finished runs
    of the same arm and seed. Returns the ledger entry; Stop(3) on any mismatch."""
    cond, arm, seed = split(run)
    bad = []
    if rec.get("cond") != cond or rec.get("arm") != arm or rec.get("seed") != seed or rec.get("steps") != APPROVED["train_updates"]:
        bad.append("run record of another run or length")
    if not rec.get("complete"):
        bad.append("run record not complete")
    if cond != "C0":
        want = fz["lambda"][arm] if cond == "C1" else fz["lambda2"][arm]
        if rec.get("lam") != want:
            bad.append(f"{'lambda' if cond == 'C1' else 'lambda2'} {rec.get('lam')} != frozen {want}")
        if not p["test"]:
            fresh = dict(zip(C.RECORD_POINTS[arm], C.heads_sha(C.make_heads(arm, seed, 128))))
            if rec.get("heads_sha256") != fresh:
                bad.append("head sha256 differs from the recomputed heads")
        if cond == "C2" and rec.get("digit_code_sha256") != C.code_sha(C.digit_code(seed)):
            bad.append("digit code differs from Random(80000 + seed)")
        if cond == "C1":
            ew = rec.get("E_W")
            if not (isinstance(ew, (int, float)) and ew > 0 and math.isfinite(ew)):
                bad.append(f"E_W^C1 = {ew} (zero or not finite)")
    for other, orec in done.items():
        oc, oa, os_ = split(other)
        if oa != arm or os_ != seed:
            continue
        for k in PAIR_COMMON:
            if rec.get(k) != orec.get(k):
                bad.append(f"{k} differs from {other}")
        if {cond, oc} == {"C1", "C2"}:
            for k in ("heads_sha256", "record_points", "positions", "mask"):
                if rec.get(k) != orec.get(k):
                    bad.append(f"{k} differs from {other}")
    if bad:
        raise Stop(3, f"INTEGRITY FAILURE (F8): pairing of {run}: {bad}")
    return {k: rec.get(k) for k in PAIR_COMMON + ("heads_sha256", "digit_code_sha256", "lam", "E_W", "clip_share_W")}


def restart_check(L, run, rec, kept):
    """3.5: a re-trained run must equal its quarantined attempt on the overlap."""
    cond, arm, seed = split(run)
    for base, old in kept.items():
        if base.endswith(".pt"):
            new = os.path.join(L.p["runs"], base)
            if os.path.exists(new) and param_hash_of(L.p, old, arm) != param_hash_of(L.p, new, arm):
                raise Stop(3, f"INTEGRITY FAILURE (F8): re-trained {base} differs from the kept attempt")
            L.log(f"re-trained {base} equals the kept attempt")
        elif base.endswith(".progress.json") or base == f"{run}.json":
            a = load_json(old) or {}
            n = len(a.get("r_u", []) or a.get("kappa_u", []))
            same = all(a.get(k, [])[:n] == rec.get(k, [])[:n] for k in ("r_u", "kappa_u", "loss_every_step", "aux_loss_every_step"))
            same = same and all(rec.get("batch_chain", {}).get(u) == v for u, v in a.get("batch_chain", {}).items())
            if not same:
                raise Stop(3, f"INTEGRITY FAILURE (F8): re-trained {run} differs from the kept attempt on updates 1-{n}")
            L.log(f"re-trained {run} equals the kept attempt on updates 1-{n}")


def archive(L, run, manifest):
    p = L.p
    cond, arm, seed = split(run)
    files = [(t, os.path.join(p["runs"], f"{run}_step{t}.pt")) for t in APPROVED["d2c_steps"]]
    if "archive" in p["stubs"]:
        import shlex
        rc = subprocess.run(shlex.split(p["stubs"]["archive"].format(name=run))).returncode
        if rc:
            raise Stop(3, f"INTEGRITY FAILURE (F5): archive of {run} (stub exit {rc})")
        for t, f in files:
            manifest["states"][f"{run}_step{t}"] = {"local": f, "published": None if t == 0 else f"{ARTIFACT_PREFIX}/{run}_step{t}.pt",
                                                    "sha256": sha256_file(f), "param_sha256": sha256_file(f)}
        manifest["archived_runs"][run] = {"stub": True}
        return
    from e_storage import ARTIFACTS_URL, entry, push_files, retrieve_and_verify
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.abspath(ROOT), capture_output=True, text=True).stdout.strip()
    ents = []
    for t, f in files:
        pub = None if t == 0 else f"{ARTIFACT_PREFIX}/{run}_step{t}.pt"
        e = entry(f, pub, arm, 2, seed, t, commit, f"train_e2c.py --cond {cond}")
        e["local"] = f
        manifest["states"][f"{run}_step{t}"] = e
        if pub:
            ents.append(e)
    try:
        pushed = push_files([(e["local"], e["published"]) for e in ents], "/home/user/openmythos-artifacts", ARTIFACTS_URL,
                            f"gate_e/e2c: checkpoints of {run}")
        fresh = os.path.join(p["lfs_tmp"], f"fresh_{run}_{int(time.time())}")
        ver = retrieve_and_verify(ents, ARTIFACTS_URL, fresh)
    except Exception as err:  # noqa: BLE001
        raise Stop(3, f"INTEGRITY FAILURE (F5): storage of {run}: {err}")
    bad = [k for k, v in ver.items() if not (v["file_sha256"] and v["param_sha256"])]
    if bad:
        raise Stop(3, f"INTEGRITY FAILURE (F5): retrieved files differ for {run}: {bad}")
    shutil.rmtree(fresh, ignore_errors=True)
    manifest["archived_runs"][run] = {"pushed_commit": pushed, "files": len(ents)}
    L.log(f"archived {run}: {len(ents)} files, commit {pushed}, both hashes verified")


def restore(L, manifest, st):
    import shlex
    p, e = L.p, manifest["states"][st]
    if "restore" in p["stubs"]:
        rc = subprocess.run(shlex.split(p["stubs"]["restore"].format(state=st, local=e["local"]))).returncode
        if rc or not (os.path.exists(e["local"]) and sha256_file(e["local"]) == e["sha256"]):
            raise Stop(3, f"INTEGRITY FAILURE (F5): restore of {st} failed")
        L.log(f"restored {st} (stub), sha256 verified")
        return
    if e.get("published") is None:  # step 0: rebuilt initialization, checked by its parameter hash
        from e_common import param_hash, rebuild_init
        run = st.rsplit("_step", 1)[0]
        cond, arm, seed = split(run)
        m = rebuild_init(arm, 2, seed)
        if param_hash(m) != e["param_sha256"]:
            raise Stop(3, f"INTEGRITY FAILURE (F5): rebuilt initialization of {st} differs")
        from e_common import atomic_torch_save
        atomic_torch_save({"K": 2, "task": "k2", "cond": cond, "lam": None, "arm": arm, "seed": seed, "step": 0,
                           "model": m.state_dict()}, e["local"])
        L.log(f"rebuilt {st} (initialization), parameter hash verified")
        return
    from e_storage import ARTIFACTS_URL, retrieve_and_verify
    fresh = os.path.join(p["lfs_tmp"], f"restore_{st}_{int(time.time())}")
    try:
        v = retrieve_and_verify([e], ARTIFACTS_URL, fresh)[e["published"]]
    except Exception as err:  # noqa: BLE001
        raise Stop(3, f"INTEGRITY FAILURE (F5): retrieval of {st} failed: {err}")
    if not (v["file_sha256"] and v["param_sha256"]):
        raise Stop(3, f"INTEGRITY FAILURE (F5): retrieved {st} does not match the manifest")
    tmp = e["local"] + ".restore.tmp"
    shutil.copyfile(os.path.join(fresh, e["published"]), tmp)
    os.replace(tmp, e["local"])
    shutil.rmtree(fresh, ignore_errors=True)
    L.log(f"restored {st} from LFS, both hashes verified")


def validate_result(path, st, manifest):
    r = load_json(path)
    if not isinstance(r, dict):
        return "not parseable"
    run, t = st.rsplit("_step", 1)
    cond, arm, seed = split(run)
    if r.get("arm") != arm or r.get("seed") != seed or r.get("step") != int(t):
        return "result of another state"
    if r.get("param_sha256") != manifest["states"].get(st, {}).get("param_sha256"):
        return "parameter hash differs from the checkpoint manifest"
    need = ["M1", "M2", "A_lin"] + (["M3", "M6"] if int(t) in C.D2C_HEAVY else []) + (["M0"] if int(t) in C.D2C_M0 else [])
    missing = [k for k in need if k not in r]
    if missing:
        return f"missing {missing}"
    if "M0" in r and r["M0"].get("pass") is not True:
        return "M0 not passed"
    if "M3" in r:
        c = r["M3"].get("controls", {})
        if not (c.get("negative_query_swap", {}).get("pass") is True and c.get("positive_own_letter_emb", {}).get("pass") is True):
            return "M3 controls not passed"
    return None


# ------------------------------------------------------------ main


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=[3, 4])
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--salt-file")
    ap.add_argument("--approved-stage2-commit", help="commit that added the freeze file, from the stage-2 review")
    ap.add_argument("--approved-freeze-sha256", help="sha256 of the freeze file, from the stage-2 review")
    a = ap.parse_args()
    try:
        p = paths()
        fz = load_json(p["freeze"])
        if not fz:
            raise Stop(5, f"REFUSED: no freeze file ({FREEZE_FILE})")
        now = basis(p)
        now["freeze_file_sha256"] = sha256_file(p["freeze"])
        diffs = check_baseline(fz, now)
        if diffs:
            raise Stop(5, "REFUSED: the current state differs from the freeze: " + "; ".join(diffs))
        rf_key = f"stage{a.stage}"
        rf = load_json(p["run_freeze"], {})
        if not a.resume:
            if rf.get(rf_key):
                raise Stop(5, f"REFUSED: stage {a.stage} was launched before; continue with --resume")
            if a.stage == 3:
                for d in ("runs", "results"):
                    if os.path.exists(p[d]) and os.listdir(p[d]):
                        raise Stop(5, f"REFUSED: {p[d]} is not empty")
        else:
            if not rf.get(rf_key):
                raise Stop(5, f"REFUSED: --resume without a stage-{a.stage} run freeze")
            changed = [k for k in now if rf[rf_key].get(k) != now[k]]
            if changed:
                raise Stop(5, f"REFUSED: frozen items changed since the first launch of stage {a.stage}: {changed}")
        if a.stage == 4:
            man = load_json(p["checkpoints_manifest"], {"archived_runs": {}})
            rl = load_json(p["results_ledger"], {})
            if not (all(r in man["archived_runs"] for r in runs_planned()) and all(s in rl for s in states_planned())):
                raise Stop(5, "REFUSED: stage 4 before stage 3 is complete")
            if not a.salt_file or not os.path.exists(a.salt_file):
                raise Stop(5, "REFUSED: stage 4 needs --salt-file")
        # B1: the freeze is trusted only through the review's approvals and the git history, not the working tree
        approvals = {"approved_stage2_commit": a.approved_stage2_commit, "approved_freeze_sha256": a.approved_freeze_sha256}
        if not all(approvals.values()):
            raise Stop(5, f"REFUSED: stage {a.stage} needs --approved-stage2-commit and --approved-freeze-sha256 from the stage-2 review")
        bad = git_anchor(p["freeze"], a.approved_stage2_commit, a.approved_freeze_sha256)
        if bad:
            raise Stop(5, "REFUSED: the freeze file is not the approved one: " + "; ".join(bad))
        if a.resume and any(rf[rf_key].get(k) != v for k, v in approvals.items()):
            raise Stop(5, f"REFUSED: the approvals differ from the first launch of stage {a.stage}")
        if a.stage == 4:
            s3 = rf.get("stage3") or {}
            if any(s3.get(k) != v for k, v in approvals.items()) or s3.get("freeze_file_sha256") != now["freeze_file_sha256"]:
                raise Stop(5, "REFUSED: the freeze or its approvals differ from those bound at the first launch of stage 3")
        for d in ("runs", "results", "judgments", "logs"):
            os.makedirs(p[d], exist_ok=True)
        L = Launcher(p)
    except Stop as s:
        print(s, file=sys.stderr)
        return s.code
    if not a.resume:
        rf[rf_key] = dict(now, **approvals, created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        atomic_write_json(p["run_freeze"], rf, indent=1)
    cap_s = p["cap_override"] or APPROVED["caps_hours"][rf_key] * 3600
    budget = load_json(p["budget_ledger"], {})
    bud = budget.setdefault(rf_key, {"seconds": 0.0, "launches": [], "cap_seconds": cap_s})
    launch = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "resume": a.resume, "seconds": 0.0}
    bud["launches"].append(launch)
    last = {"t": time.time(), "sync_t": time.time(), "n": 0}

    def save(path, obj):
        atomic_write_json(path, obj, indent=1)

    def tick():
        t = time.time()
        bud["seconds"] += t - last["t"]
        launch["seconds"] += t - last["t"]
        last["t"] = t
        save(p["budget_ledger"], budget)
        if bud["seconds"] >= cap_s:
            raise Stop(7, f"BUDGET EXCEEDED (F9): stage {a.stage} cumulative {bud['seconds'] / 3600:.2f} h >= cap {cap_s / 3600:.2f} h")

    def handler(signum, frame):
        L.log(f"launcher interrupted (signal {signum})")
        L.kill_all()
        tick_safe()
        sys.exit(130)

    def tick_safe():
        try:
            tick()
        except Stop:
            pass

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    try:
        tick()
        L.log(f"freeze check passed: code tree {now['code_tree_sha256'][:12]}, preregistration {now['preregistration_sha256'][:12]}, "
              f"lambda {fz['lambda']}, lambda2 {fz['lambda2']}; stage {a.stage} {'resume' if a.resume else 'launch'}, "
              f"used {bud['seconds'] / 3600:.2f} h of {cap_s / 3600:.0f} h")
        if a.stage == 3:
            stage3(L, p, fz, tick, save)
        else:
            stage4(L, p, fz, a.salt_file, tick, save)
        tick()
        L.log("DONE")
        L.sync(f"stage {a.stage} done")
        return 0
    except Stop as s:
        L.kill_all()
        L.log(str(s))
        L.log(f"stopped with exit {s.code}")
        tick_safe()
        return s.code
    except Exception as err:  # noqa: BLE001
        L.kill_all()
        L.log(f"RUN ERROR: launcher: {err!r}")
        tick_safe()
        return 4


def stage3(L, p, fz, tick, save):
    manifest = load_json(p["checkpoints_manifest"], {"states": {}, "archived_runs": {}})
    pairing = load_json(p["pairing_ledger"], {})
    rledger = load_json(p["results_ledger"], {})
    save_at = ",".join(str(t) for t in APPROVED["archive_steps"])
    queue, kept = [], {}
    for run in runs_planned():
        if run in manifest["archived_runs"]:
            continue
        cond, arm, seed = split(run)
        outs = glob.glob(os.path.join(p["runs"], f"{run}_step*.pt")) + glob.glob(os.path.join(p["runs"], f"{run}.json*"))
        kept[run] = {os.path.basename(f): L.quarantine(f, f"unarchived attempt of {run}") for f in outs}
        argv = ["python", "experiments/gate_e/e2c/train_e2c.py", "--cond", cond, "--arm", arm, "--seed", str(seed),
                "--steps", str(APPROVED["train_updates"]), "--save-at", save_at, "--ckpt-dir", p["runs"],
                "--out", os.path.join(p["runs"], f"{run}.json")]
        if cond != "C0":
            argv += ["--lam", repr(fz["lambda"][arm] if cond == "C1" else fz["lambda2"][arm])]
        lam = "" if cond == "C0" else repr(fz["lambda"][arm] if cond == "C1" else fz["lambda2"][arm])
        queue.append((f"train_{run}", L.cmd("train", argv, name=run, out=p["runs"], lam=lam)))
    queue.sort(key=lambda j: 0 if "openmythos" in j[0] else 1)
    done = {r: load_json(os.path.join(p["runs"], f"{r}.json")) for r in manifest["archived_runs"]}

    def on_train(name):
        run = name[6:]
        rec = load_json(os.path.join(p["runs"], f"{run}.json"))
        if not rec:
            raise Stop(6, f"RESULT CHECK FAILED: {run} wrote no run record")
        restart_check(L, run, rec, kept.get(run, {}))
        pairing[run] = pairing_check(p, run, rec, fz, done)
        save(p["pairing_ledger"], pairing)
        done[run] = rec
        archive(L, run, manifest)
        save(p["checkpoints_manifest"], manifest)
        L.sync(f"archived {run}")

    if queue:
        L.run_queue(queue, on_done=on_train, tick=tick)
    if not all(r in manifest["archived_runs"] for r in runs_planned()):
        raise Stop(6, f"RESULT CHECK FAILED: {len(manifest['archived_runs'])} of {len(runs_planned())} runs archived")
    L.log(f"all {len(runs_planned())} runs trained, paired and archived")
    for tmp in glob.glob(os.path.join(p["results"], ".*.tmp.*")):
        L.quarantine(tmp, "temporary file of an interrupted write")
    expect, queue = {}, []
    for st in states_planned():
        path = os.path.join(p["results"], f"{st}.json")
        led, exists = rledger.get(st), os.path.exists(path)
        if led and exists:
            if sha256_file(path) != led["sha256"]:
                raise Stop(3, f"INTEGRITY FAILURE (F5): {st} result differs from its ledger entry")
            continue
        if led and not exists:
            expect[st] = ("ledger", led["digest"])
        elif exists:
            why = validate_result(path, st, manifest)
            kp = L.quarantine(path, f"result without ledger entry ({why or 'valid'})")
            if why is None:
                expect[st] = ("kept", result_digest(kp))
        run, t = st.rsplit("_step", 1)
        cond, arm, seed = split(run)
        argv = ["python", "experiments/gate_e/e2c/d2c.py", "--arm", arm, "--seed", str(seed), "--step", t,
                "--ckpt", manifest["states"][st]["local"], "--out", path]
        queue.append((f"diag_{st}", L.cmd("diag", argv, name=f"diag_{st}", state=st, out=p["results"])))
    queue.sort(key=lambda j: 0 if "openmythos" in j[0] else 1)

    def before(name):
        st = name[5:]
        e = manifest["states"][st]
        if not (os.path.exists(e["local"]) and sha256_file(e["local"]) == e["sha256"]):
            restore(L, manifest, st)

    def on_diag(name):
        st = name[5:]
        path = os.path.join(p["results"], f"{st}.json")
        if not os.path.exists(path):
            raise Stop(6, f"RESULT CHECK FAILED: {st} wrote no result")
        why = validate_result(path, st, manifest)
        if why:
            raise Stop(3, f"INTEGRITY FAILURE (F6): result of {st} not valid: {why}")
        dg = result_digest(path)
        if st in expect and expect[st][1] != dg:
            raise Stop(3, f"INTEGRITY FAILURE: re-diagnosed {st} differs from the {expect[st][0]} result")
        rledger[st] = {"sha256": sha256_file(path), "digest": dg, "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        save(p["results_ledger"], rledger)
        last_n = len(rledger)
        if last_n % SYNC_EVERY_STATES == 0:
            L.sync(f"{last_n} states diagnosed")

    if queue:
        L.run_queue(queue, on_done=on_diag, before_start=before, tick=tick)
    if not all(s in rledger for s in states_planned()):
        raise Stop(6, f"RESULT CHECK FAILED: {len(rledger)} of {len(states_planned())} states diagnosed")
    L.log(f"all {len(states_planned())} states diagnosed")


def judgment_invalid(path, run, test2_sha):
    j = load_json(path) or {}
    cond, arm, seed = split(run)
    if (j.get("cond"), j.get("arm"), j.get("seed"), j.get("set"), j.get("test2_sha256")) != (cond, arm, seed, "test2_heldout", test2_sha):
        return "not a complete judgment of this run on this test2"
    return None


def stage4(L, p, fz, salt_file, tick, save):
    salt = open(salt_file).read().strip()
    if hashlib.sha256(salt.encode()).hexdigest() != fz["salt_commitment_sha256"]:
        raise Stop(3, "INTEGRITY FAILURE (F10): sha256(salt) differs from the frozen commitment; nothing is judged")
    L.log("salt matches the frozen commitment")
    os.environ["E2C_KEYSPACE_STAGE"] = "4"  # inherited by the stage-4 jobs (Launcher.start)
    rec = load_json(p["test2_record"], {})
    ks_out = os.path.join(p["judgments"], "keyspace_stage4.json")
    if not os.path.exists(ks_out):
        L.run_queue([("keyspace", L.cmd("keyspace", ["python", "experiments/gate_e/e2c/e2c_stage4.py", "keyspace", "--out", ks_out],
                                        out=ks_out))], tick=tick)
    ks = load_json(ks_out) or {}
    want = fz["keyspace"]
    if (ks.get("R_star_sha256"), ks.get("M1_star_sha256"), ks.get("counts")) != (want["R_star_sha256"], want["M1_star_sha256"], want["counts"]):
        raise Stop(3, "INTEGRITY FAILURE (F10): R* / M1* recomputed differ from the frozen hashes; nothing is judged")
    L.log("R* and M1* equal the frozen hashes and counts")
    t2_out = os.path.join(p["judgments"], "test2_generation.json")
    if not os.path.exists(t2_out):
        seeds = training_stream_seeds()
        L.run_queue([("test2", L.cmd("test2", ["python", "experiments/gate_e/e2c/e2c_stage4.py", "test2", "--salt-file", salt_file,
                                               "--seeds", ",".join(map(str, seeds)), "--out", t2_out], out=t2_out))], tick=tick)
    t2 = load_json(t2_out) or {}
    t2_path = os.path.join(p["judgments"], "test2_heldout.jsonl")
    if not os.path.exists(t2_path) or sha256_file(t2_path) != t2.get("sha256"):
        raise Stop(3, "INTEGRITY FAILURE (F10): test2 file missing or differs from its generation record")
    if rec.get("sha256") and rec["sha256"] != t2["sha256"]:
        raise Stop(3, "INTEGRITY FAILURE (F10): test2 differs from the recorded one")
    iso = t2.get("isolation") or {}
    if not iso or any(v != 0 for v in iso.values()):
        raise Stop(3, f"INTEGRITY FAILURE (F10): isolation of test2 not zero ({iso}); nothing is judged")
    rec.update({"sha256": t2["sha256"], "isolation": iso, "stats": t2.get("stats")})
    save(p["test2_record"], rec)
    L.log(f"test2 sha256 {t2['sha256'][:12]}, isolation all zero")
    manifest = load_json(p["checkpoints_manifest"])
    jl = load_json(p["judgments_ledger"], {})
    e1man = load_json(os.path.join(GE, "checkpoints_manifest.json"))["states"]
    targets = runs_planned() + [f"C0_{arm}_s{s}" for arm in ARMS for s in historical_seeds()]
    queue = []
    for run in targets:
        cond, arm, seed = split(run)
        path = os.path.join(p["judgments"], f"{run}.json")
        led = jl.get(run)
        if led and led.get("sha256"):
            if not os.path.exists(path) or sha256_file(path) != led["sha256"]:
                raise Stop(3, f"INTEGRITY FAILURE (F5): judgment {run} missing or differs from its ledger; never redone")
            continue
        if os.path.exists(path):  # written but not ledgered (interrupted): checked like a finished one, never redone
            why = judgment_invalid(path, run, rec["sha256"])
            if why:
                raise Stop(3, f"INTEGRITY FAILURE: judgment of {run} found without ledger entry is {why}; never redone")
            jl[run] = {"sha256": sha256_file(path), "recovered": True, "attempts": (led or {}).get("attempts", 1)}
            save(p["judgments_ledger"], jl)
            L.log(f"judgment {run} found complete without ledger entry: recorded, not redone")
            continue
        hist_c0 = cond == "C0" and seed in APPROVED["seeds"]["historical"]
        if hist_c0:  # E1's run (R2 reproduced it); its archived step-12000 checkpoint, both hashes verified
            e = e1man[f"K2_{arm}_s{seed}_step12000"]
            ck = e["local"]
            if not p["test"] and not (os.path.exists(ck) and sha256_file(ck) == e["sha256"]):
                from e_storage import ARTIFACTS_URL, retrieve_and_verify
                fresh = os.path.join(p["lfs_tmp"], f"e1_{run}_{int(time.time())}")
                v = retrieve_and_verify([e], ARTIFACTS_URL, fresh)[e["published"]]
                if not (v["file_sha256"] and v["param_sha256"]):
                    raise Stop(3, f"INTEGRITY FAILURE (F5): E1 checkpoint of {run} does not match E1's manifest")
                ck = os.path.join(fresh, e["published"])
        else:
            ck = manifest["states"][f"{run}_step12000"]["local"]
        argv = ["python", "experiments/gate_e/e2c/e2c_stage4.py", "judge", "--arm", arm, "--seed", str(seed), "--cond", cond,
                "--ckpt", ck, "--test2", t2_path, "--out", path]
        queue.append((f"judge_{run}", L.cmd("judge", argv, name=run, out=path)))

    def before(name):
        run = name[6:]
        led = jl.setdefault(run, {})
        led["attempts"] = led.get("attempts", 0) + 1
        save(p["judgments_ledger"], jl)

    def on_judge(name):
        run = name[6:]
        path = os.path.join(p["judgments"], f"{run}.json")
        if not os.path.exists(path):
            raise Stop(6, f"RESULT CHECK FAILED: {run} wrote no judgment")
        why = judgment_invalid(path, run, rec["sha256"])
        if why:
            raise Stop(3, f"INTEGRITY FAILURE: judgment of {run} is {why}")
        jl[run]["sha256"] = sha256_file(path)
        save(p["judgments_ledger"], jl)
        L.sync(f"judgment {run}")

    if queue:
        L.run_queue(queue, on_done=on_judge, before_start=before, tick=tick)
    if not all(jl.get(r, {}).get("sha256") for r in targets):
        raise Stop(6, "RESULT CHECK FAILED: judgments missing")


if __name__ == "__main__":
    sys.exit(main())
