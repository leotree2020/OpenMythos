"""
Stage-1 run-time ledger and job pool (E2C_PREREG_DRAFT 8.4: stage 1 counts
all runs, hard cap 6 h, accumulated over every launch and never reset; F9,
exit 7, when reached).

What is counted: the wall-clock time during which at least one stage-1 job
(pre-check, training, diagnostic, calibration, test) runs, i.e. the length of
the union of all job intervals. Parallel jobs are not counted twice; time
between jobs (writing code, reading results) is not a run and is not
counted. Every interval is written when it opens and its end is refreshed
every HEARTBEAT seconds, so a container restart loses at most one heartbeat;
an interval found open at a later start whose process no longer exists is
closed at its last heartbeat and listed under "closed_after_interruption".
Version 2 (after gate 2's first launch): every read-modify-write holds an
exclusive file lock (fcntl) across processes, intervals are addressed by a
unique id, and an open interval of a process that is still alive is left
open. Version 1 (kept as stage1/s1_budget_v1_used_until_gate2.py) had no
cross-process lock and closed every open interval at a start, which wrote two
spurious "closed_after_interruption" entries for jobs still running (their
intervals kept being refreshed and closed normally; see the interim audit).
Supplements (version 2, after the interim audit): time known to have run but
not covered by any interval is added as a named supplement; the total is the
union of the intervals plus the supplements (gate 2's first launch: 15 s,
at most one heartbeat between its last heartbeat 10:53:30 and its kill).

    with Ledger().job("gate1"):
        run_pool([...], ledger)
"""

import fcntl
import json
import os
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE1 = os.path.join(HERE, "stage1")
LEDGER = os.path.join(STAGE1, "budget_ledger_s1.json")
CAP_SECONDS = 6 * 3600
HEARTBEAT = 15
AUTHORIZED_UTC = "2026-10-20 (STAGE 1 EXECUTION GO; baseline 974e9322233d3e84fda67b8866cd453122d13b3f)"


class CapReached(Exception):
    pass


def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _atomic(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def union_seconds(intervals):
    spans = sorted((i["start"], i["end"]) for i in intervals if i["end"] is not None)
    total, cur = 0.0, None
    for s, e in spans:
        if cur is None or s > cur[1]:
            if cur:
                total += cur[1] - cur[0]
            cur = [s, e]
        else:
            cur[1] = max(cur[1], e)
    if cur:
        total += cur[1] - cur[0]
    return total


class Ledger:
    def __init__(self, path=LEDGER, cap=CAP_SECONDS):
        self.path, self.cap = path, cap
        self.lock = threading.Lock()
        self.lockf = path + ".lock"
        if not os.path.exists(path):
            _atomic(path, {"scope": "stage 1, all runs (8.4): union of the wall-clock intervals of every job",
                           "cap_seconds": cap, "authorized": AUTHORIZED_UTC, "never_reset": True,
                           "intervals": [], "closed_after_interruption": [], "total_seconds": 0.0})
        def close_dead(d):
            if d["cap_seconds"] != cap:
                raise SystemExit(f"ledger cap {d['cap_seconds']} differs from {cap}")
            for i in d["intervals"]:
                if i.get("open") and not _alive(i.get("pid")):
                    i["open"] = False
                    d["closed_after_interruption"].append({"label": i["label"], "start": i["start"], "last_heartbeat": i["end"],
                                                          "note": "process gone; closed at its last heartbeat"})
        self._rw(close_dead)

    def _rw(self, fn):
        with self.lock, open(self.lockf, "a") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                d = json.load(open(self.path))
                fn(d)
                d["total_seconds"] = union_seconds(d["intervals"]) + sum(x["seconds"] for x in d.get("supplements", []))
                _atomic(self.path, d)
                return d
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def add_supplement(self, label, seconds, note):
        def add(d):
            sup = d.setdefault("supplements", [])
            if not any(x["label"] == label for x in sup):
                sup.append({"label": label, "seconds": seconds, "note": note, "added": time.time()})
        return self._rw(add)

    def total(self):
        return json.load(open(self.path))["total_seconds"]

    def remaining(self):
        return self.cap - self.total()

    def job(self, label):
        return _Job(self, label)


class _Job:
    def __init__(self, ledger, label):
        self.l, self.label = ledger, label
        self.stop = threading.Event()
        self.cap_reached = threading.Event()

    def __enter__(self):
        if self.l.total() >= self.l.cap:
            raise CapReached(f"stage-1 cap reached before {self.label}")
        now = time.time()
        import uuid
        self.id = uuid.uuid4().hex

        def add(d):
            d["intervals"].append({"label": self.label, "start": now, "end": now, "open": True, "pid": os.getpid(), "id": self.id})
        self.l._rw(add)
        self.t = threading.Thread(target=self._beat, daemon=True)
        self.t.start()
        return self

    def _touch(self, close=False):
        t = time.time()

        def upd(d):
            i = next(x for x in d["intervals"] if x.get("id") == self.id)
            i["end"] = t
            if close:
                i["open"] = False
        d = self.l._rw(upd)
        if d["total_seconds"] >= self.l.cap:
            self.cap_reached.set()

    def _beat(self):
        while not self.stop.wait(HEARTBEAT):
            self._touch()

    def __exit__(self, *exc):
        self.stop.set()
        self.t.join()
        self._touch(close=True)
        return False


def run_pool(jobs, job_ctx, width=4, log_dir=None, on_done=None, poll=2.0):
    """jobs: list of (name, argv). Runs up to `width` at a time; the first job
    that exits non-zero, or `on_done(name)` returning a reason, stops the pool:
    nothing new starts and running jobs are killed. Returns (status, info):
    ("ok", None) | ("failed", (name, rc or reason)) | ("cap", None)."""
    pending, running, done = list(jobs), {}, []
    log_dir = log_dir or os.path.join(STAGE1, "logs")
    os.makedirs(log_dir, exist_ok=True)

    def kill_all():
        for p, _ in running.values():
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for p, f in running.values():
            p.wait()
            f.close()

    while pending or running:
        if job_ctx.cap_reached.is_set():
            kill_all()
            return "cap", None
        while pending and len(running) < width:
            name, argv = pending.pop(0)
            f = open(os.path.join(log_dir, f"{name}.log"), "w")
            p = subprocess.Popen(argv, stdout=f, stderr=subprocess.STDOUT, start_new_session=True,
                                 env=dict(os.environ, PYTHONHASHSEED="0"))
            running[name] = (p, f)
            print(f"[{time.strftime('%H:%M:%S')}] start {name}", flush=True)
        time.sleep(poll)
        for name in list(running):
            p, f = running[name]
            rc = p.poll()
            if rc is None:
                continue
            f.close()
            del running[name]
            print(f"[{time.strftime('%H:%M:%S')}] end {name} rc={rc}", flush=True)
            if rc != 0:
                kill_all()
                return "failed", (name, rc)
            reason = on_done(name) if on_done else None
            if reason:
                kill_all()
                return "failed", (name, reason)
            done.append(name)
    return "ok", None


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1] == "exec" and sys.argv[3] == "--":
        # any other stage-1 run (development smoke tests included) under the ledger
        led = Ledger()
        with led.job(sys.argv[2]) as j:
            rc = subprocess.call(sys.argv[4:], env=dict(os.environ, PYTHONHASHSEED="0"))
        print(f"[ledger] {sys.argv[2]} rc={rc}; stage-1 total {led.total():.0f} s")
        sys.exit(rc)
    d = json.load(open(LEDGER))
    print(json.dumps({k: v for k, v in d.items() if k != "intervals"}, indent=1))
    print(f"total {d['total_seconds'] / 3600:.3f} h of {d['cap_seconds'] / 3600:.0f} h; intervals {len(d['intervals'])}")
    sys.exit(0)
