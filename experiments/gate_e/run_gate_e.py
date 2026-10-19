#!/usr/bin/env python3
"""
Gate E formal launcher (PREREGISTRATION 2, 4, 5, 6.6, 9.6, 9.7, 11.3). Not
run before the formal-start review. Conventions of gate_d/run_gate_d.sh:
    exit 5  refused: an output directory is not empty, no frozen workload in
            timing.json, or a test command without the test directory
    exit 3  integrity failure (bridge not bitwise identical, storage push /
            retrieval / hash check failed, a diagnostic state's hard check)
    exit 4  any other error
    exit 6  expected result files missing afterwards
The first failure stops the run: nothing new is started, running jobs are
killed, nothing later is done; the status log keeps every step.

Stages (each job single-threaded, at most 4 at once):
    T  training: 10 K=2 runs (train_k.py, 12,000 steps) and 6 bridge runs
       (gen_gate_a/train_level.py, 3,000 steps, e_bridge.bridge_command),
       longest first. After each run, in the launcher process (git operations
       are serialized): bridge acceptance (e_bridge.accept); checkpoint
       manifest entries; LFS push of the run's new files to
       leotree2020/openmythos-artifacts (gate_e/formal/), retrieval into a
       fresh directory and both hashes checked. A run counts as archived only
       then.
    D  diagnostics: e_diag_state.py on all 280 states with the manifest check
    J  formal judgment: e_eval_test.py on test_heldout at step 12,000 (K=2)
    E  event table: e_events.py
    DONE
Fault-injection tests only (launcher_tests.py): GATE_E_TEST_DIR redirects
every output there and GATE_E_TEST_CMDS (a JSON file) replaces the job
commands and the archive step by stubs; without GATE_E_TEST_DIR any
GATE_E_TEST_CMDS is refused.
"""

import json
import os
import shlex
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import (ARMS, BRIDGE_SEEDS, BRIDGE_STEPS, BUDGET, K2_SEEDS, K2_STEPS, ROOT,  # noqa: E402
                      param_hash, rebuild_init, state_name)

ENV = dict(os.environ, PYTHONPATH=os.path.abspath(ROOT))
WIDTH = 4


class Stop(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def paths():
    test = os.environ.get("GATE_E_TEST_DIR")
    cmds = os.environ.get("GATE_E_TEST_CMDS")
    if cmds and not test:
        raise Stop(5, "REFUSED: GATE_E_TEST_CMDS only with GATE_E_TEST_DIR")
    base = test or HERE
    p = {k: os.path.join(base, k) for k in ("runs", "results", "judgments", "logs")}
    p["bridge"] = os.path.join(p["runs"], "bridge")
    p["manifest"] = os.path.join(base, "checkpoints_manifest.json")
    p["events"] = os.path.join(base, "events.json")
    p["timing"] = os.path.join(base, "timing.json") if test else os.path.join(HERE, "timing.json")
    p["test"] = bool(test)
    p["stubs"] = json.load(open(cmds)) if cmds else {}
    return p


class Launcher:
    def __init__(self, p):
        self.p = p
        os.makedirs(p["logs"], exist_ok=True)
        self.status = open(os.path.join(p["logs"], "run_status.txt"), "a")
        self.jobs = {}

    def log(self, msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
        print(line, flush=True)
        self.status.write(line + "\n")
        self.status.flush()

    def start(self, name, argv):
        f = open(os.path.join(self.p["logs"], f"{name}.log"), "w")
        proc = subprocess.Popen(argv, cwd=os.path.abspath(ROOT), env=ENV, stdout=f, stderr=f,
                                start_new_session=True)
        self.jobs[proc.pid] = (name, proc, f)
        self.log(f"started {name} (pid {proc.pid})")

    def kill_all(self):
        for pid, (name, proc, f) in list(self.jobs.items()):
            if proc.poll() is None:
                os.killpg(pid, signal.SIGTERM)
                self.log(f"killed {name} (pid {pid})")
        for pid, (name, proc, f) in list(self.jobs.items()):
            proc.wait()
            f.close()
        self.jobs = {}

    def run_queue(self, queue, on_done=None):
        """queue: list of (name, argv). Runs at most WIDTH at once; the first
        non-zero exit (or on_done raising Stop) stops everything."""
        queue = list(queue)
        try:
            while queue or self.jobs:
                while queue and len(self.jobs) < WIDTH:
                    self.start(*queue.pop(0))
                time.sleep(0.2 if self.p["test"] else 5)
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

    def cmd(self, kind, default, **fmt):
        stub = self.p["stubs"].get(kind)
        return shlex.split(stub.format(**fmt)) if stub else default


# ------------------------------------------------------------------ stages


def training_queue(L):
    p = L.p
    k2_save = ",".join(str(s) for s in K2_STEPS if s)
    q = []
    for arm in ARMS:
        for s in K2_SEEDS:
            q.append((f"train_K2_{arm}_s{s}", L.cmd("train", [
                "python", "experiments/gate_e/train_k.py", "--task", "k2", "--arm", arm, "--seed", str(s),
                "--steps", "12000", "--save-at", k2_save, "--ckpt-dir", p["runs"],
                "--out", os.path.join(p["runs"], f"K2_{arm}_s{s}.json")], name=f"train_K2_{arm}_s{s}", out=p["runs"])))
    from e_bridge import bridge_command

    for arm in ARMS:
        for s in BRIDGE_SEEDS:
            ref = os.path.join(BUDGET, f"A_{arm}_s{s}_step3000.pt")
            q.append((f"train_K4_{arm}_s{s}", L.cmd("train", bridge_command(
                arm, s, os.path.join(p["bridge"], f"A_{arm}_s{s}.json"), ref), name=f"train_K4_{arm}_s{s}", out=p["bridge"])))
    q.sort(key=lambda j: (0 if "K2_openmythos" in j[0] else 1 if "K2" in j[0] else 2 if "openmythos" in j[0] else 3))
    return q


def run_files(p, name):
    """(K, arm, seed, [(step, local path, published path or None)])."""
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
                out.append((t, None, None))  # rebuilt, hash only
            elif t == 3000:
                out.append((t, os.path.join(p["bridge"], f"A_{arm}_s{seed}.pt"), None))  # = budget_a file, hash only
            else:
                f = os.path.join(p["bridge"], f"A_{arm}_s{seed}_step{t}.pt")
                out.append((t, f, f"gate_e/formal/A_{arm}_s{seed}_step{t}.pt"))
    return K, arm, seed, out


def archive_run(L, name, manifest):
    """Bridge acceptance, manifest entries, LFS push and verified retrieval of
    one finished training run. Raises Stop(3) on any failure."""
    p = L.p
    K, arm, seed, files = run_files(p, name)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.abspath(ROOT), capture_output=True,
                            text=True).stdout.strip()
    if "archive" in p["stubs"]:
        rc = subprocess.run(shlex.split(p["stubs"]["archive"].format(name=name)), cwd=os.path.abspath(ROOT)).returncode
        if rc:
            raise Stop(3, f"INTEGRITY FAILURE: archive of {name} (stub exit {rc})")
        for t, f, pub in files:
            manifest["states"][state_name(arm, K, seed, t)] = {"param_sha256": f"stub-{name}-{t}", "published": pub}
        return
    from e_bridge import accept
    from e_storage import ARTIFACTS_URL, ckpt_param_hash, entry, push_files, retrieve_and_verify

    if K == 4:
        ok, why = accept(0, os.path.join(p["bridge"], f"A_{arm}_s{seed}.json"),
                         os.path.join(p["bridge"], f"A_{arm}_s{seed}.pt"),
                         os.path.join(BUDGET, f"A_{arm}_s{seed}_step3000.pt"), arm)
        L.log(f"bridge acceptance {name}: {ok} {why}")
        if not ok:
            raise Stop(3, f"INTEGRITY FAILURE: bridge {name} is not bitwise identical to budget_a ({why})")
    ents = []
    for t, f, pub in files:
        st = state_name(arm, K, seed, t)
        if f is None:
            m = rebuild_init(arm, K, seed)
            manifest["states"][st] = {"param_sha256": param_hash(m), "source": "rebuilt initialization"}
            continue
        if pub is None:
            manifest["states"][st] = {"param_sha256": ckpt_param_hash(f, arm, K),
                                      "source": f"bitwise identical to {os.path.relpath(os.path.join(BUDGET, f'A_{arm}_s{seed}_step3000.pt'), ROOT)}"}
            continue
        e = entry(f, pub, arm, K, seed, t, commit, "train_k.py --task k2" if K == 2 else "train_level.py (bridge)")
        ents.append(e)
        manifest["states"][st] = e
    try:
        pushed = push_files([(os.path.join(p["runs"] if K == 2 else p["bridge"], os.path.basename(e["published"])),
                              e["published"]) for e in ents], "/home/user/openmythos-artifacts", ARTIFACTS_URL,
                            f"gate_e: formal checkpoints of {name}")
        fresh = os.path.join(p["logs"], f"fresh_{name}")
        ver = retrieve_and_verify(ents, ARTIFACTS_URL, fresh)
    except Exception as err:  # noqa: BLE001  any storage error stops the run
        raise Stop(3, f"INTEGRITY FAILURE: storage of {name}: {err}")
    bad = [k for k, v in ver.items() if not (v["file_sha256"] and v["param_sha256"])]
    if bad:
        raise Stop(3, f"INTEGRITY FAILURE: retrieved files differ for {name}: {bad}")
    subprocess.run(["rm", "-rf", fresh])
    manifest["archived_runs"][name] = {"pushed_commit": pushed, "files": len(ents)}
    L.log(f"archived {name}: {len(ents)} files, commit {pushed}, both hashes verified")


def diag_queue(L):
    p = L.p
    q = []
    for K, seeds, steps in ((2, K2_SEEDS, K2_STEPS), (4, BRIDGE_SEEDS, BRIDGE_STEPS)):
        for arm in ARMS:
            for s in seeds:
                for t in steps:
                    name = state_name(arm, K, s, t)
                    ck = None
                    if K == 2:
                        ck = os.path.join(p["runs"], f"K2_{arm}_s{s}_step{t}.pt")
                    elif t == 3000:
                        ck = os.path.join(p["bridge"], f"A_{arm}_s{s}.pt")
                    elif t:
                        ck = os.path.join(p["bridge"], f"A_{arm}_s{s}_step{t}.pt")
                    argv = ["python", "experiments/gate_e/e_diag_state.py", "--arm", arm, "--K", str(K),
                            "--seed", str(s), "--step", str(t), "--out-dir", p["results"],
                            "--workload", p["timing"], "--manifest", p["manifest"]]
                    if ck:
                        argv += ["--ckpt", ck]
                    q.append((f"diag_{name}", L.cmd("diag", argv, name=f"diag_{name}", state=name, out=p["results"])))
    q.sort(key=lambda j: 0 if "openmythos" in j[0] else 1)
    return q


def main():
    try:
        p = paths()
        for d in ("runs", "results", "judgments"):
            if os.path.exists(p[d]) and os.listdir(p[d]):
                raise Stop(5, f"REFUSED: {p[d]} is not empty")
        try:
            wl = json.load(open(p["timing"]))["frozen_workload"]
        except (OSError, KeyError, ValueError):
            raise Stop(5, "REFUSED: no frozen workload in timing.json")
        if wl.get("m5a_bodies") != 500:
            raise Stop(5, "REFUSED: frozen workload does not keep M5(a) at 500 bodies (11.3)")
        for d in ("runs", "bridge", "results", "judgments"):
            os.makedirs(p[d], exist_ok=True)
        L = Launcher(p)
    except Stop as s:
        print(s, file=sys.stderr)
        return s.code
    manifest = {"states": {}, "archived_runs": {}}

    def save_manifest():
        with open(p["manifest"], "w") as f:
            json.dump(manifest, f, indent=1)

    def on_train_done(name):
        archive_run(L, name, manifest)
        save_manifest()

    def handler(signum, frame):
        L.log("launcher interrupted")
        L.kill_all()
        sys.exit(130)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    try:
        L.log(f"launch gate E: workload {wl}")
        L.run_queue(training_queue(L), on_done=on_train_done)
        n_runs = len(ARMS) * (len(K2_SEEDS) + len(BRIDGE_SEEDS))
        if len(manifest["archived_runs"]) != n_runs:
            raise Stop(6, f"RESULT CHECK FAILED: {len(manifest['archived_runs'])} of {n_runs} runs archived")
        L.log(f"all {n_runs} training runs done and archived")
        L.run_queue(diag_queue(L))
        n_states = len(ARMS) * (len(K2_SEEDS) * len(K2_STEPS) + len(BRIDGE_SEEDS) * len(BRIDGE_STEPS))
        n = len([f for f in os.listdir(p["results"]) if f.endswith(".json")])
        if n != n_states:
            raise Stop(6, f"RESULT CHECK FAILED: {n} of {n_states} result files")
        L.log(f"all {n_states} states diagnosed")
        L.run_queue([(f"judge_{arm}_s{s}", L.cmd("judge", [
            "python", "experiments/gate_e/e_eval_test.py", "--arm", arm, "--seed", str(s),
            "--ckpt", os.path.join(p["runs"], f"K2_{arm}_s{s}_step12000.pt"),
            "--out", os.path.join(p["judgments"], f"K2_{arm}_s{s}.json")], name=f"judge_{arm}_s{s}",
            file=f"K2_{arm}_s{s}", out=p["judgments"]))
            for arm in ARMS for s in K2_SEEDS])
        n = len([f for f in os.listdir(p["judgments"]) if f.endswith(".json")])
        if n != len(ARMS) * len(K2_SEEDS):
            raise Stop(6, f"RESULT CHECK FAILED: {n} of {len(ARMS) * len(K2_SEEDS)} judgments")
        L.run_queue([("events", L.cmd("events", [
            "python", "experiments/gate_e/e_events.py", "--results", p["results"], "--runs", p["runs"],
            "--out", p["events"]], name="events", out=p["events"]))])
        L.log("DONE")
        return 0
    except Stop as s:
        L.log(str(s))
        L.log(f"stopped with exit {s.code}")
        return s.code
    except Exception as err:  # noqa: BLE001
        L.kill_all()
        L.log(f"RUN ERROR: launcher: {err!r}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
