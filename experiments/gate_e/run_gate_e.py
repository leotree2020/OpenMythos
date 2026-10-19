#!/usr/bin/env python3
"""
Gate E formal launcher with resumption (PREREGISTRATION 2, 4, 5, 6.6, 9.6,
9.7, 11.3, 12). Not run before the formal-start review.

    python experiments/gate_e/run_gate_e.py            first launch
    python experiments/gate_e/run_gate_e.py --resume   every later launch

Exit codes (gate_d/run_gate_d.sh conventions, plus 7):
    5  refused: first launch over existing outputs / freeze, resume without a
       freeze, any freeze item changed (code tree, preregistration, set
       manifest, workload, state list), no frozen workload, M5(a) not 500,
       test commands without the test directory
    3  integrity failure: bridge not bitwise identical; checkpoint push,
       retrieval or hash check failed; a re-trained or re-diagnosed file
       differs from what was kept; a result or judgment differs from its
       ledger; a diagnostic state's hard check
    4  any other error (including a failed sync of the run records)
    6  expected outputs missing after a stage
    7  the 24 h cumulative diagnostic budget is reached (12.3)
The first failure stops everything: nothing new starts, running jobs are
killed, nothing later is done. Every step is in logs/run_status.txt.

Records (all written atomically: temporary file, fsync, rename):
    run_freeze.json        hashes of the code tree, the preregistration, the
                           set manifest; workload; state list (12.4.1)
    checkpoints_manifest.json  per state: file sha256, parameter hash, where
                           it is archived; per run: archive record
    results_ledger.json    per diagnosed state: sha256 of its result file
    judgments_ledger.json  per K=2 run: sha256 of its judgment, attempts
    budget_ledger.json     cumulative diagnostic wall-clock seconds over all
                           launches; never reset
Stages: T training + archive per run (12.4.4: archived runs are skipped,
unarchived ones quarantined and re-trained, overlapping files must be
bitwise identical) -> D diagnostics (12.4.2 skip rules, 12.4.3 verified
checkpoint restore, 24 h cap) -> J formal judgment, once per run (12.4.7)
-> E events -> DONE. The run records are committed and pushed to the
research branch after every archived run, every 10 diagnosed states or
20 minutes, every judgment and at the end (12.4.6).
Fault-injection tests only (launcher_tests.py): GATE_E_TEST_DIR redirects
every output there and GATE_E_TEST_CMDS (a JSON file) replaces jobs,
archive, restore and sync by stubs; checkpoints are then plain files checked
by sha256 only. Without GATE_E_TEST_DIR any GATE_E_TEST_CMDS is refused.
"""

import glob
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import (ARMS, BRIDGE_SEEDS, BRIDGE_STEPS, BUDGET, K2_SEEDS, K2_STEPS, ROOT,  # noqa: E402
                      atomic_write_json, param_hash, rebuild_init, state_name)

ENV = dict(os.environ, PYTHONPATH=os.path.abspath(ROOT))
WIDTH = 4
EXP = os.path.join(os.path.abspath(ROOT), "experiments")
CODE_GLOBS = ("experiments/gate_e/*.py", "experiments/gate_d/*.py", "experiments/basic_learn/models.py",
              "experiments/gen_gate_a/*.py", "experiments/budget_a/schedule.py", "experiments/loop_mech/*.py",
              "open_mythos/*.py")
SYNC_EVERY_STATES, SYNC_EVERY_S = 10, 1200


class Stop(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def result_digest(path):
    """sha256 of a result's content without its timing fields ("seconds",
    "M5.seconds"): the diagnostics are deterministic, their run times are not."""
    r = json.load(open(path))
    r.pop("seconds", None)
    if isinstance(r.get("M5"), dict):
        r["M5"].pop("seconds", None)
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()


def load_json(path, default=None):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def paths():
    test = os.environ.get("GATE_E_TEST_DIR")
    cmds = os.environ.get("GATE_E_TEST_CMDS")
    if cmds and not test:
        raise Stop(5, "REFUSED: GATE_E_TEST_CMDS only with GATE_E_TEST_DIR")
    base = test or HERE
    p = {k: os.path.join(base, k) for k in ("runs", "results", "judgments", "logs")}
    p["bridge"] = os.path.join(p["runs"], "bridge")
    p["quarantine"] = os.path.join(base, "quarantine")
    p["lfs_tmp"] = os.path.join(base, "lfs_tmp")  # fresh retrieval clones; never synced
    for k in ("run_freeze", "checkpoints_manifest", "results_ledger", "judgments_ledger", "budget_ledger"):
        p[k] = os.path.join(base, f"{k}.json")
    p["events"] = os.path.join(base, "events.json")
    p["workload"] = os.path.join(base if test else HERE, "workload_freeze.json")
    p["test"] = bool(test)
    p["stubs"] = json.load(open(cmds)) if cmds else {}
    p["base"] = base
    cap = os.environ.get("GATE_E_TEST_DIAG_CAP_SECONDS") if test else None
    p["cap_override"] = float(cap) if cap else None
    return p


def code_tree():
    files = sorted({f for g in CODE_GLOBS for f in glob.glob(os.path.join(os.path.abspath(ROOT), g))})
    per = {os.path.relpath(f, os.path.abspath(ROOT)): sha256_file(f) for f in files}
    tree = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in per.items()).encode()).hexdigest()
    return tree, per


def state_list():
    out = [state_name(a, 2, s, t) for a in ARMS for s in K2_SEEDS for t in K2_STEPS]
    out += [state_name(a, 4, s, t) for a in ARMS for s in BRIDGE_SEEDS for t in BRIDGE_STEPS]
    return out


def make_freeze(wl_file):
    tree, per = code_tree()
    return {"code_tree_sha256": tree, "code_files": per,
            "preregistration_sha256": sha256_file(os.path.join(HERE, "PREREGISTRATION.md")),
            "sets_manifest_sha256": sha256_file(os.path.join(HERE, "sets", "manifest.json")),
            "workload": wl_file, "states": state_list()}


class Launcher:
    def __init__(self, p):
        self.p = p
        os.makedirs(p["logs"], exist_ok=True)
        self.status = open(os.path.join(p["logs"], "run_status.txt"), "a")
        self.jobs = {}
        self.poll = 0.2 if p["test"] else 5

    def log(self, msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
        print(line, flush=True)
        self.status.write(line + "\n")
        self.status.flush()

    def cmd(self, kind, default, **fmt):
        stub = self.p["stubs"].get(kind)
        return shlex.split(stub.format(**fmt)) if stub else default

    def start(self, name, argv):
        f = open(os.path.join(self.p["logs"], f"{name}.log"), "a")
        proc = subprocess.Popen(argv, cwd=os.path.abspath(ROOT), env=ENV, stdout=f, stderr=f,
                                start_new_session=True)
        self.jobs[proc.pid] = (name, proc, f)
        self.log(f"started {name} (pid {proc.pid})")

    def kill_all(self):
        for pid, (name, proc, f) in list(self.jobs.items()):
            if proc.poll() is None:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                self.log(f"killed {name} (pid {pid})")
        for pid, (name, proc, f) in list(self.jobs.items()):
            proc.wait()
            f.close()
        self.jobs = {}

    def run_queue(self, queue, on_done=None, before_start=None, tick=None):
        """At most WIDTH jobs at once. before_start(name) may restore inputs;
        on_done(name) checks outputs; tick() runs at every poll (budget). The
        first non-zero exit or Stop ends everything."""
        queue = list(queue)
        try:
            while queue or self.jobs:
                while queue and len(self.jobs) < WIDTH:
                    name, argv = queue.pop(0)
                    if before_start:
                        before_start(name)
                    self.start(name, argv)
                time.sleep(self.poll)
                if tick:
                    tick()
                for pid, (name, proc, f) in list(self.jobs.items()):
                    rc = proc.poll()
                    if rc is None:
                        continue
                    f.close()
                    del self.jobs[pid]
                    if rc == 3:
                        raise Stop(3, f"INTEGRITY FAILURE: {name} (see {self.p['logs']})")
                    if rc != 0:
                        raise Stop(4, f"RUN ERROR: {name} exited with status {rc}")
                    self.log(f"finished {name}")
                    if on_done:
                        on_done(name)
        except Stop:
            self.kill_all()
            raise

    def quarantine(self, path, why):
        d = os.path.join(self.p["quarantine"], time.strftime("%Y%m%dT%H%M%S", time.gmtime()))
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(path))
        shutil.move(path, dst)
        self.log(f"quarantined {os.path.relpath(path, self.p['base'])} -> {os.path.relpath(dst, self.p['base'])} ({why})")
        return dst

    def sync(self, msg):
        """Commit and push the run records to the research branch (12.4.6)."""
        if "sync" in self.p["stubs"]:
            rc = subprocess.run(shlex.split(self.p["stubs"]["sync"].format(msg=msg.replace(" ", "_"))),
                                cwd=os.path.abspath(ROOT)).returncode
            if rc:
                raise Stop(4, f"RUN ERROR: sync failed ({msg})")
            return
        if self.p["test"]:
            return
        cwd = os.path.abspath(ROOT)
        items = [os.path.relpath(f, cwd) for f in sync_items(HERE)]
        for i in range(0, len(items), 200):
            subprocess.run(["git", "add", "-f", "--"] + items[i : i + 200], cwd=cwd, check=True, capture_output=True)
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=cwd, capture_output=True,
                                text=True).stdout.split()
        if any(f.endswith(".pt") for f in staged):  # never a checkpoint in the research branch
            subprocess.run(["git", "reset", "-q"], cwd=cwd)
            raise Stop(4, "RUN ERROR: a checkpoint file was about to be committed to the research branch")
        if not staged:
            return
        subprocess.run(["git", "commit", "-q", "-m", f"gate_e: formal run records - {msg}"], cwd=cwd, check=True)
        for i in range(5):
            if subprocess.run(["git", "push", "-q", "origin", "HEAD"], cwd=cwd, capture_output=True).returncode == 0:
                self.log(f"synced run records ({msg})")
                return
            time.sleep(2 ** (i + 1))
        raise Stop(4, f"RUN ERROR: push of the run records failed ({msg})")


def sync_items(base):
    """Files of the run records to commit (12.4.6): the records, results,
    judgments, training logs, launcher logs and quarantined non-checkpoint
    files. Never a checkpoint (.pt), a temporary file, or the LFS clones."""
    items = [os.path.join(base, x) for x in ("run_freeze.json", "checkpoints_manifest.json", "results_ledger.json",
                                             "judgments_ledger.json", "budget_ledger.json", "events.json")
             if os.path.exists(os.path.join(base, x))]
    for d in ("results", "judgments", "runs", "logs", "quarantine"):
        for root, dirs, fs in os.walk(os.path.join(base, d)):
            dirs[:] = [x for x in dirs if x != ".git"]
            items += [os.path.join(root, f) for f in fs if not f.endswith(".pt") and ".tmp." not in f]
    return sorted(items)


# ------------------------------------------------------------ checkpoints


def run_files(p, name):
    """(K, arm, seed, [(step, local path or None, published path or None)])."""
    _, K, arm, s = name.split("_")
    K, seed = int(K[1:]), int(s[1:])
    out = []
    if K == 2:
        for t in K2_STEPS:
            f = os.path.join(p["runs"], f"K2_{arm}_s{seed}_step{t}.pt")
            out.append((t, f, f"gate_e/formal/K2_{arm}_s{seed}_step{t}.pt"))
    else:
        for t in BRIDGE_STEPS:
            if t == 0:
                out.append((t, None, None))  # rebuilt initialization, hash only
            elif t == 3000:
                out.append((t, os.path.join(p["bridge"], f"A_{arm}_s{seed}.pt"), None))  # = budget_a file
            else:
                out.append((t, os.path.join(p["bridge"], f"A_{arm}_s{seed}_step{t}.pt"),
                            f"gate_e/formal/A_{arm}_s{seed}_step{t}.pt"))
    return K, arm, seed, out


def run_outputs(p, name):
    """Every local file a training run writes (for quarantine)."""
    _, K, arm, s = name.split("_")
    if K == "K2":
        return glob.glob(os.path.join(p["runs"], f"K2_{arm}_{s}_step*.pt")) + \
            glob.glob(os.path.join(p["runs"], f"K2_{arm}_{s}.json"))
    return glob.glob(os.path.join(p["bridge"], f"A_{arm}_{s}*"))


def file_ok(p, path, entry):
    if not (path and os.path.exists(path)):
        return False
    return sha256_file(path) == entry.get("sha256")


def restore(L, manifest, state):
    """Bring a missing or mismatching checkpoint back from the LFS archive,
    verified (12.4.3); never regenerated. Stop(3) if that fails."""
    p = L.p
    e = manifest["states"][state]
    local = e["local"]
    if "restore" in p["stubs"]:
        rc = subprocess.run(shlex.split(p["stubs"]["restore"].format(state=state, local=local)),
                            cwd=os.path.abspath(ROOT)).returncode
        if rc or not file_ok(p, local, e):
            raise Stop(3, f"INTEGRITY FAILURE: restore of {state} failed (stub exit {rc})")
        L.log(f"restored {state} (stub), sha256 verified")
        return
    if not e.get("published"):
        raise Stop(3, f"INTEGRITY FAILURE: {state} is missing locally and is not archived in LFS")
    from e_storage import ARTIFACTS_URL, retrieve_and_verify

    fresh = os.path.join(p["lfs_tmp"], f"restore_{state}_{int(time.time())}")
    try:
        ver = retrieve_and_verify([e], ARTIFACTS_URL, fresh)
    except Exception as err:  # noqa: BLE001
        raise Stop(3, f"INTEGRITY FAILURE: retrieval of {state} failed: {err}")
    v = ver[e["published"]]
    if not (v["file_sha256"] and v["param_sha256"]):
        raise Stop(3, f"INTEGRITY FAILURE: retrieved {state} does not match the manifest ({v})")
    os.makedirs(os.path.dirname(local), exist_ok=True)
    tmp = local + ".restore.tmp"
    shutil.copyfile(os.path.join(fresh, e["published"]), tmp)
    os.replace(tmp, local)
    shutil.rmtree(fresh, ignore_errors=True)
    if not file_ok(p, local, e):
        raise Stop(3, f"INTEGRITY FAILURE: restored {state} differs after copying")
    L.log(f"restored {state} from LFS, both hashes verified")


def archive_run(L, name, manifest, kept):
    """Bridge acceptance; comparison with quarantined files of an earlier
    attempt; manifest entries; LFS push and verified retrieval. Stop(3) on any
    failure."""
    p = L.p
    K, arm, seed, files = run_files(p, name)
    for t, f, pub in files:  # 12.4.4: a re-trained file must equal the kept one
        if f and os.path.basename(f) in kept:
            old = kept[os.path.basename(f)]
            same = sha256_file(old) == sha256_file(f) if p["test"] else _param_hash_file(old, arm, K) == _param_hash_file(f, arm, K)
            if not same:
                raise Stop(3, f"INTEGRITY FAILURE: re-trained {os.path.basename(f)} differs from the kept attempt")
            L.log(f"re-trained {os.path.basename(f)} equals the kept attempt")
    if "archive" in p["stubs"]:
        rc = subprocess.run(shlex.split(p["stubs"]["archive"].format(name=name)), cwd=os.path.abspath(ROOT)).returncode
        if rc:
            raise Stop(3, f"INTEGRITY FAILURE: archive of {name} (stub exit {rc})")
        for t, f, pub in files:
            st = state_name(arm, K, seed, t)
            manifest["states"][st] = {"local": f, "published": pub,
                                      "sha256": sha256_file(f) if f and os.path.exists(f) else None,
                                      "param_sha256": f"stub-{st}"}
        manifest["archived_runs"][name] = {"stub": True}
        return
    from e_bridge import accept
    from e_storage import ARTIFACTS_URL, entry, push_files, retrieve_and_verify

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.abspath(ROOT), capture_output=True,
                            text=True).stdout.strip()
    if K == 4:
        ref = os.path.join(BUDGET, f"A_{arm}_s{seed}_step3000.pt")
        ok, why = accept(0, os.path.join(p["bridge"], f"A_{arm}_s{seed}.json"),
                         os.path.join(p["bridge"], f"A_{arm}_s{seed}.pt"), ref, arm)
        L.log(f"bridge acceptance {name}: {ok} {why}")
        if not ok:
            raise Stop(3, f"INTEGRITY FAILURE: bridge {name} is not bitwise identical to budget_a ({why})")
    ents = []
    for t, f, pub in files:
        st = state_name(arm, K, seed, t)
        if f is None:
            manifest["states"][st] = {"local": None, "published": None, "sha256": None,
                                      "param_sha256": param_hash(rebuild_init(arm, K, seed)),
                                      "source": "rebuilt initialization"}
        elif pub is None:
            ref = os.path.join(BUDGET, f"A_{arm}_s{seed}_step3000.pt")
            manifest["states"][st] = {"local": ref, "published": None, "sha256": sha256_file(ref),
                                      "param_sha256": _param_hash_file(ref, arm, K),
                                      "source": "archived budget_a file, bitwise identical to the bridge run"}
        else:
            e = entry(f, pub, arm, K, seed, t, commit, "train_k.py --task k2" if K == 2 else "train_level.py (bridge)")
            e["local"] = f
            ents.append(e)
            manifest["states"][st] = e
    try:
        pushed = push_files([(e["local"], e["published"]) for e in ents], "/home/user/openmythos-artifacts",
                            ARTIFACTS_URL, f"gate_e: formal checkpoints of {name}")
        fresh = os.path.join(p["lfs_tmp"], f"fresh_{name}_{int(time.time())}")
        ver = retrieve_and_verify(ents, ARTIFACTS_URL, fresh)
    except Exception as err:  # noqa: BLE001
        raise Stop(3, f"INTEGRITY FAILURE: storage of {name}: {err}")
    bad = [k for k, v in ver.items() if not (v["file_sha256"] and v["param_sha256"])]
    if bad:
        raise Stop(3, f"INTEGRITY FAILURE: retrieved files differ for {name}: {bad}")
    shutil.rmtree(fresh, ignore_errors=True)
    manifest["archived_runs"][name] = {"pushed_commit": pushed, "files": len(ents)}
    L.log(f"archived {name}: {len(ents)} files, commit {pushed}, both hashes verified")


def _param_hash_file(path, arm, K):
    from e_storage import ckpt_param_hash

    return ckpt_param_hash(path, arm, K)


# ------------------------------------------------------------ results


def validate_result(path, state, manifest, wl):
    """12.4.2: complete, parseable, hard checks passed, hashes and workload
    as frozen. Returns None if valid, else the reason."""
    r = load_json(path)
    if not isinstance(r, dict):
        return "not parseable"
    if r.get("state") != state:
        return "state name differs"
    if r.get("param_sha256") != manifest["states"].get(state, {}).get("param_sha256"):
        return "parameter hash differs from the checkpoint manifest"
    if r.get("workload") != wl:
        return "workload differs from the frozen workload"
    for k in ("M0", "M1", "M2", "M3", "M4", "M5", "M6", "seconds"):
        if k not in r:
            return f"missing {k}"
    if r["M0"].get("pass") is not True:
        return "M0 not passed"
    c = r["M3"].get("controls", {})
    if not (c.get("negative_query_swap", {}).get("pass") is True and c.get("positive_own_letter_emb", {}).get("pass") is True):
        return "M3 controls not passed"
    if not (r["M5"].get("a_tied_split", {}).get("max_check_diff", 1.0) <= 1e-6):
        return "M5 tied-weight split check not passed"
    return None


def validate_judgment(path, name):
    r = load_json(path)
    if not isinstance(r, dict) or "level" not in r or "main" not in r:
        return "not a complete judgment"
    _, arm, s = name.split("_")
    if r.get("arm") != arm or str(r.get("seed")) != s[1:] or r.get("set") != "test_heldout":
        return "judgment of another run or set"
    return None


# ------------------------------------------------------------ main


def main():
    resume = "--resume" in sys.argv[1:]
    try:
        p = paths()
        wl_file = load_json(p["workload"])
        wl = (wl_file or {}).get("frozen_workload")
        if not wl:
            raise Stop(5, "REFUSED: no frozen workload (workload_freeze.json)")
        if wl.get("m5a_bodies") != 500:
            raise Stop(5, "REFUSED: frozen workload does not keep M5(a) at 500 bodies (11.3)")
        cap_s = p["cap_override"] or float(wl_file.get("diag_cap_hours", 0)) * 3600
        if cap_s <= 0:
            raise Stop(5, "REFUSED: no diagnostic budget cap in workload_freeze.json")
        freeze_now = make_freeze(wl_file)
        if not resume:
            if os.path.exists(p["run_freeze"]):
                raise Stop(5, "REFUSED: a run freeze exists; continue with --resume")
            for d in ("runs", "results", "judgments"):
                if os.path.exists(p[d]) and os.listdir(p[d]):
                    raise Stop(5, f"REFUSED: {p[d]} is not empty")
        else:
            old = load_json(p["run_freeze"])
            if not old:
                raise Stop(5, "REFUSED: --resume without a run freeze")
            changed = [k for k in ("code_tree_sha256", "preregistration_sha256", "sets_manifest_sha256", "workload",
                                   "states") if old.get(k) != freeze_now[k]]
            if changed:
                files = [f for f in set(old.get("code_files", {})) | set(freeze_now["code_files"])
                         if old.get("code_files", {}).get(f) != freeze_now["code_files"].get(f)]
                raise Stop(5, f"REFUSED: frozen items changed since the first launch: {changed} {files[:10]}")
        for d in ("runs", "bridge", "results", "judgments"):
            os.makedirs(p[d], exist_ok=True)
        L = Launcher(p)
    except Stop as s:
        print(s, file=sys.stderr)
        return s.code
    if not resume:
        freeze_now["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_write_json(p["run_freeze"], freeze_now, indent=1)
    manifest = load_json(p["checkpoints_manifest"], {"states": {}, "archived_runs": {}})
    rledger = load_json(p["results_ledger"], {})
    jledger = load_json(p["judgments_ledger"], {})
    budget = load_json(p["budget_ledger"], {"diag_seconds": 0.0, "launches": []})
    budget["cap_seconds"] = cap_s
    launch = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "resume": resume, "diag_seconds": 0.0}
    budget["launches"].append(launch)

    def save(path, obj):
        atomic_write_json(path, obj, indent=1)

    def handler(signum, frame):
        L.log(f"launcher interrupted (signal {signum})")
        L.kill_all()
        save(p["budget_ledger"], budget)
        sys.exit(130)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    try:
        L.log(f"{'resume' if resume else 'launch'} gate E: workload {wl}, diagnostic cap {cap_s / 3600:.2f} h, "
              f"used so far {budget['diag_seconds'] / 3600:.2f} h")
        save(p["budget_ledger"], budget)

        # ---------------- T: training + archive
        k2_save = ",".join(str(s) for s in K2_STEPS if s)
        from e_bridge import bridge_command

        queue, kept = [], {}
        names = [f"train_K2_{a}_s{s}" for a in ARMS for s in K2_SEEDS] + \
                [f"train_K4_{a}_s{s}" for a in ARMS for s in BRIDGE_SEEDS]
        for name in names:
            if name in manifest["archived_runs"]:
                continue
            for f in run_outputs(p, name):  # an earlier, unarchived attempt: keep it aside
                kept[os.path.basename(f)] = L.quarantine(f, f"unarchived attempt of {name}")
            _, K, arm, s = name.split("_")
            seed = int(s[1:])
            if K == "K2":
                argv = ["python", "experiments/gate_e/train_k.py", "--task", "k2", "--arm", arm, "--seed", str(seed),
                        "--steps", "12000", "--save-at", k2_save, "--ckpt-dir", p["runs"],
                        "--out", os.path.join(p["runs"], f"K2_{arm}_s{seed}.json")]
                out = p["runs"]
            else:
                argv = bridge_command(arm, seed, os.path.join(p["bridge"], f"A_{arm}_s{seed}.json"),
                                      os.path.join(BUDGET, f"A_{arm}_s{seed}_step3000.pt"))
                out = p["bridge"]
            queue.append((name, L.cmd("train", argv, name=name, out=out)))
        queue.sort(key=lambda j: (0 if "K2_openmythos" in j[0] else 1 if "K2" in j[0] else 2 if "openmythos" in j[0] else 3))

        def on_train_done(name):
            archive_run(L, name, manifest, kept)
            save(p["checkpoints_manifest"], manifest)
            L.sync(f"archived {name}")

        if queue:
            L.run_queue(queue, on_done=on_train_done)
        n_runs = len(names)
        if len([n for n in names if n in manifest["archived_runs"]]) != n_runs:
            raise Stop(6, f"RESULT CHECK FAILED: {len(manifest['archived_runs'])} of {n_runs} runs archived")
        L.log(f"all {n_runs} training runs done and archived")

        # ---------------- D: diagnostics
        for tmp in glob.glob(os.path.join(p["results"], ".*.tmp.*")):
            L.quarantine(tmp, "temporary file of an interrupted write")
        expect, queue = {}, []
        for st in state_list():
            path = os.path.join(p["results"], f"{st}.json")
            led = rledger.get(st)
            exists = os.path.exists(path)
            if led and exists:
                if sha256_file(path) != led["sha256"]:
                    raise Stop(3, f"INTEGRITY FAILURE: {st} result differs from its ledger entry (file left untouched)")
                why = validate_result(path, st, manifest, wl)
                if why:
                    raise Stop(3, f"INTEGRITY FAILURE: ledgered result {st} is not valid: {why}")
                continue
            if led and not exists:
                expect[st] = ("ledger", led["digest"])
            elif exists:
                why = validate_result(path, st, manifest, wl)
                kept_path = L.quarantine(path, f"result without ledger entry ({why or 'valid'})")
                if why is None:
                    expect[st] = ("kept", result_digest(kept_path))
            K = 2 if st.startswith("K2_") else 4
            _, arm, s, t = st.split("_")
            argv = ["python", "experiments/gate_e/e_diag_state.py", "--arm", arm, "--K", str(K), "--seed", s[1:],
                    "--step", t[4:], "--out-dir", p["results"], "--workload", p["workload"],
                    "--manifest", p["checkpoints_manifest"]]
            local = manifest["states"].get(st, {}).get("local")
            if local:
                argv += ["--ckpt", local]
            queue.append((f"diag_{st}", L.cmd("diag", argv, name=f"diag_{st}", state=st, out=p["results"])))
        queue.sort(key=lambda j: 0 if "openmythos" in j[0] else 1)
        L.log(f"diagnostics: {len(state_list()) - len(queue)} states already complete, {len(queue)} to run")
        last = {"t": time.time(), "sync_t": time.time(), "n": 0}

        def tick():
            now = time.time()
            budget["diag_seconds"] += now - last["t"]
            launch["diag_seconds"] += now - last["t"]
            last["t"] = now
            save(p["budget_ledger"], budget)
            if budget["diag_seconds"] >= cap_s:
                raise Stop(7, f"BUDGET EXCEEDED: cumulative diagnostic time {budget['diag_seconds'] / 3600:.2f} h "
                              f">= cap {cap_s / 3600:.2f} h")

        def before_diag(name):
            if budget["diag_seconds"] >= cap_s:
                raise Stop(7, f"BUDGET EXCEEDED: cumulative diagnostic time {budget['diag_seconds'] / 3600:.2f} h "
                              f">= cap {cap_s / 3600:.2f} h")
            st = name[5:]
            e = manifest["states"].get(st)
            if e is None:
                raise Stop(3, f"INTEGRITY FAILURE: {st} has no checkpoint manifest entry")
            if e.get("local") and not file_ok(p, e["local"], e):
                restore(L, manifest, st)

        def on_diag_done(name):
            st = name[5:]
            path = os.path.join(p["results"], f"{st}.json")
            if not os.path.exists(path):
                raise Stop(6, f"RESULT CHECK FAILED: {st} wrote no result")
            why = validate_result(path, st, manifest, wl)
            if why:
                raise Stop(3, f"INTEGRITY FAILURE: result of {st} not valid: {why}")
            dg = result_digest(path)
            if st in expect and expect[st][1] != dg:
                raise Stop(3, f"INTEGRITY FAILURE: re-diagnosed {st} differs from the {expect[st][0]} result")
            if st in expect:
                L.log(f"re-diagnosed {st} equals the {expect[st][0]} result (timing fields excluded)")
            rledger[st] = {"sha256": sha256_file(path), "digest": dg,
                           "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            save(p["results_ledger"], rledger)
            last["n"] += 1
            if last["n"] % SYNC_EVERY_STATES == 0 or time.time() - last["sync_t"] > SYNC_EVERY_S:
                L.sync(f"{len(rledger)} states diagnosed")
                last["sync_t"] = time.time()

        if budget["diag_seconds"] >= cap_s and queue:
            raise Stop(7, f"BUDGET EXCEEDED: cumulative diagnostic time {budget['diag_seconds'] / 3600:.2f} h "
                          f">= cap {cap_s / 3600:.2f} h")
        if queue:
            L.run_queue(queue, on_done=on_diag_done, before_start=before_diag, tick=tick)
        n_states = len(state_list())
        if len([s for s in state_list() if s in rledger]) != n_states:
            raise Stop(6, f"RESULT CHECK FAILED: {len(rledger)} of {n_states} states in the results ledger")
        L.log(f"all {n_states} states diagnosed ({budget['diag_seconds'] / 3600:.2f} h of {cap_s / 3600:.0f} h)")
        L.sync("all states diagnosed")

        # ---------------- J: formal judgment, once per run
        queue = []
        for arm in ARMS:
            for s in K2_SEEDS:
                name = f"judge_{arm}_s{s}"
                path = os.path.join(p["judgments"], f"K2_{arm}_s{s}.json")
                led = jledger.get(name)
                exists = os.path.exists(path)
                if led and led.get("sha256"):
                    if not exists or sha256_file(path) != led["sha256"]:
                        raise Stop(3, f"INTEGRITY FAILURE: judgment {name} missing or differs from its ledger; "
                                      "it is never redone")
                    continue
                if exists:
                    why = validate_judgment(path, name)
                    if why:
                        raise Stop(3, f"INTEGRITY FAILURE: judgment file of {name} not valid ({why}); never redone")
                    jledger[name] = {"sha256": sha256_file(path), "recovered": True,
                                     "attempts": (led or {}).get("attempts", 1)}
                    save(p["judgments_ledger"], jledger)
                    L.log(f"judgment {name} found complete without ledger entry: recorded, not redone")
                    continue
                if led and led.get("attempts"):
                    L.log(f"judgment {name}: earlier attempt produced no file; one more attempt")
                local = manifest["states"][state_name(arm, 2, s, 12000)]["local"]
                queue.append((name, L.cmd("judge", [
                    "python", "experiments/gate_e/e_eval_test.py", "--arm", arm, "--seed", str(s), "--ckpt", local,
                    "--out", path], name=name, file=f"K2_{arm}_s{s}", out=p["judgments"])))

        def before_judge(name):
            led = jledger.setdefault(name, {})
            led["attempts"] = led.get("attempts", 0) + 1
            save(p["judgments_ledger"], jledger)
            arm, s = name.split("_")[1:]
            st = state_name(arm, 2, int(s[1:]), 12000)
            e = manifest["states"][st]
            if not file_ok(p, e["local"], e):
                restore(L, manifest, st)

        def on_judge_done(name):
            arm, s = name.split("_")[1:]
            path = os.path.join(p["judgments"], f"K2_{arm}_{s}.json")
            if not os.path.exists(path):
                raise Stop(6, f"RESULT CHECK FAILED: {name} wrote no judgment")
            why = validate_judgment(path, name)
            if why:
                raise Stop(3, f"INTEGRITY FAILURE: judgment of {name} not valid: {why}")
            jledger[name]["sha256"] = sha256_file(path)
            save(p["judgments_ledger"], jledger)
            L.sync(f"judgment {name}")

        if queue:
            L.run_queue(queue, on_done=on_judge_done, before_start=before_judge)
        n_j = len(ARMS) * len(K2_SEEDS)
        if len([k for k, v in jledger.items() if v.get("sha256")]) != n_j:
            raise Stop(6, f"RESULT CHECK FAILED: {len(jledger)} of {n_j} judgments")

        # ---------------- E: events
        L.run_queue([("events", L.cmd("events", [
            "python", "experiments/gate_e/e_events.py", "--results", p["results"], "--runs", p["runs"],
            "--out", p["events"]], name="events", out=p["events"]))])
        L.log("DONE")
        L.sync("DONE")
        return 0
    except Stop as s:
        L.log(str(s))
        L.log(f"stopped with exit {s.code}")
        save(p["budget_ledger"], budget)
        return s.code
    except Exception as err:  # noqa: BLE001
        L.kill_all()
        L.log(f"RUN ERROR: launcher: {err!r}")
        save(p["budget_ledger"], budget)
        return 4


if __name__ == "__main__":
    sys.exit(main())
