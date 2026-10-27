"""G1 entry: the negative gate test (ABORT, EOF, INVALID_BYTE, TIMEOUT).  WRITTEN, NOT RUN.  `--execute` is refused without a valid single-use
AUTHORIZATION_E1A_GATE_G1.json (see g1_auth.py); `--check` starts no process and reads no /proc entry of any other process.

Implements the FROZEN criteria g1_criteria_v1.json (F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001).
Four sequential tests T1_ABORT, T2_EOF, T3_INVALID_BYTE, T4_TIMEOUT: each has ONE observer-created gated child (one fork), never released (the byte b"R"
is never written, Observer.release() is trapped), ZERO signals, no descendants.  The first test that is not clearly as expected stops the run (the rest are
NOT_RUN).  Python-level guards trap kill/killpg/pidfd_send_signal/exec*/spawn*/system/popen/subprocess and allow exactly one os.fork per test (four in
total, never while a child is unreaped) and waitpid on the one specific child pid.  A Python-level trap is NOT proof that no kernel path exists.
There is no code path from here to G0, G2/G3, BV, E1-A cells, the janitor, or any signal.  On any anomaly the run stops, sends no signal, keeps the evidence
and writes MANUAL_DISPOSITION_REQUIRED.json.

The reap evidence of every test (exit observed through the pidfd, state Z before any wait, waitpid on that pid, /proc gone) is collected BEFORE any cleanup;
Observer._confirmed_dead() (zombie counted as dead) is never used in place of it.

After the run the evidence is saved, judged and closed by the pipeline P0..P7 and the closure publication K0..K7 of the criteria: construct -> strict
serialisation -> exclusive write + fsync -> read back and verify -> validate types -> judge ONLY the read-back evidence -> save and verify the summary ->
publish g1_closed.json atomically and exclusively -> exit with the recorded exit code.  Every failure is BLOCKED with exit code 3 and a marker on stderr.
Generic helpers (directories, budget, exclusive write / read-back, /proc snapshots) are imported read-only from g0_run.py; no g0_* file is modified."""
import argparse
import copy
import json
import os
import stat
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, os.path.join(A003, "gate_g0"))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import g0_judge as GJ0  # noqa: E402
import g0_run as GR  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_judge as GJ  # noqa: E402

TOKEN = "g1_run.py"                                                 # diagnostic scan marker (command line); never authorizes a signal
MANUAL = "MANUAL_DISPOSITION_REQUIRED.json"
EVIDENCE_NAME, SUMMARY_NAME, CLOSED_NAME, CLOSED_TMP_NAME = "g1_evidence.json", "g1_summary.json", "g1_closed.json", "g1_closed.json.tmp"
EVIDENCE_SCHEMA_ID = "e1a-gate-g1-evidence-1"
MAX_BOUND_BYTES = 256 * 1024 * 1024

stderr_marker, utc_now = GR.stderr_marker, GR.utc_now
Unsaved, Unverified, DirError = GR.Unsaved, GR.Unverified, GR.DirError
fsync_dir, write_exclusive, read_back, save_and_verify = GR.fsync_dir, GR.write_exclusive, GR.read_back, GR.save_and_verify
write_exclusive_json = GR.write_exclusive_json


# ------------------------------------------------------------------ pure helpers (no process is started by any of them)
def current():
    return G1A.current_bindings(GR.git_head(), GR.prereg_sha(), GR.bench_code_hash())


def token_scan(exclude):
    """Diagnostic only: live processes (not zombies, not the excluded ancestors/self) whose command line carries the G1 marker."""
    table, problems = C.scan_proc()
    found = []
    for pid, st in sorted(table.items()):
        if pid in exclude or st["state"] in ("Z", "X"):
            continue
        cmd = " ".join(C.read_cmdline(pid) or [])
        if TOKEN in cmd:
            found.append({"pid": pid, "starttime": st["starttime"], "ppid": st["ppid"], "state": st["state"], "cmdline": cmd[:160]})
    return found, problems


def blank_test(tid):
    """The shape of a test that did not run (every nullable field null)."""
    return {"ran": False, "scenario": tid, "t_gate_max": None, "node": None, "stimulus": None, "events": None, "first_action_mono": None,
            "ready_received": None, "messages_received": None, "snapshots": None, "reap": None, "cleanup": None, "timing": None, "exception": None}


def msgs(rec):
    """Number of messages the observer received from the node (FIRST_ACTION, READY, anything else)."""
    return int(rec.ready is not None) + int(rec.first_action_mono is not None) + len(rec.messages)


def in_run_assessment(t, scn, exit_status, violations, deadline_hits):
    """The in-run safety rule: -> (ok, reasons).  `ok` only when the test is clearly as expected; anything else stops the run (the remaining tests are
    NOT_RUN).  This is NOT the verdict: the judge decides from the read-back evidence."""
    reasons = []
    if exit_status != scn["expected_exit"]:
        reasons.append("exit status %r != expected %r" % (exit_status, scn["expected_exit"]))
    if t.get("messages_received") != 0 or t.get("first_action_mono") is not None or t.get("ready_received") is not False:
        reasons.append("the child sent a message / acted")
    cl = t.get("cleanup")
    if not (isinstance(cl, dict) and cl.get("cleanup_ok") is True):
        reasons.append("cleanup not ok")
    if violations:
        reasons.append("guard violations %r" % (violations,))
    if deadline_hits:
        reasons.append("deadline hits %r" % (deadline_hits,))
    return not reasons, reasons


# ------------------------------------------------------------------ Python-level guard
class GuardViolation(Exception):
    pass


class G1Guard:
    """Traps every process-creating / signalling / waiting function, allows ONE fork per test (four in total, none while a child is unreaped) and waitpid
    on the current child pid, records every write to and every close of the watched gate descriptor, and traps b"R" writes and Observer.release()."""

    def __init__(self, max_forks=4):
        self.violations, self.fork_pids, self.fork_events, self.waitpid_calls = [], [], [], []
        self.gate_writes, self.gate_closes = [], []
        self.fork_calls, self.max_forks = 0, max_forks
        self.test = None
        self.forks_this_test = 0
        self.live_pid = None
        self.allowed_pid = None
        self.watch_fd = None
        self.real = {}
        self.installed = False

    def begin_test(self, tid):
        self.test, self.forks_this_test, self.watch_fd = tid, 0, None

    def _trap(self, name):
        def trap(*a, **k):
            self.violations.append({"call": name, "mono": C.mono(), "test": self.test, "args": repr(a)[:120]})
            raise GuardViolation("G1 guard refused %s" % name)
        return trap

    def _is_pipe(self, fd):
        try:
            return stat.S_ISFIFO(os.fstat(fd).st_mode)
        except OSError:
            return False

    def fork(self):
        if self.test is None or self.forks_this_test >= 1 or self.fork_calls >= self.max_forks or self.live_pid is not None:
            self.violations.append({"call": "os.fork (not allowed now)", "mono": C.mono(), "test": self.test, "args": ""})
            raise GuardViolation("G1 allows one fork per test, four in total, and none while a child is unreaped")
        self.fork_calls += 1
        self.forks_this_test += 1
        entry = {"test": self.test, "mono_before": C.mono(), "mono_after": None, "pid": None}
        self.fork_events.append(entry)
        pid = self.real["os.fork"]()
        if pid != 0:                                          # parent only
            entry["mono_after"], entry["pid"] = C.mono(), pid
            self.fork_pids.append(pid)
            self.allowed_pid = self.live_pid = pid
        return pid

    def waitpid(self, pid, options=0):
        t = C.mono()
        if not isinstance(pid, int) or pid <= 0 or pid != self.allowed_pid:
            self.violations.append({"call": "os.waitpid", "mono": t, "test": self.test, "args": repr((pid, options))})
            raise GuardViolation("G1 allows waitpid only on the one specific child pid")
        got = self.real["os.waitpid"](pid, options)
        self.waitpid_calls.append({"test": self.test, "pid": pid, "options": options, "returned": got[0], "status": got[1], "mono": t})
        if got[0] == pid:
            self.live_pid = None
        return got

    def write(self, fd, data):
        """Every write to the watched gate descriptor is an ENTRY (byte, mono_before, mono_after, result); the entry exists before the call and a failed
        write is recorded as an error, never dropped.  A write of b"R" is trapped and recorded as a violation: it never reaches the pipe."""
        b = bytes(data)
        if b == b"R" and (fd == self.watch_fd or self._is_pipe(fd)):
            self.violations.append({"call": GJ.R_WRITE_CALL, "mono": C.mono(), "test": self.test, "args": repr(fd)})
            raise GuardViolation("G1 never writes the release byte")
        if self.watch_fd is None or fd != self.watch_fd:
            return self.real["os.write"](fd, data)
        entry = {"test": self.test, "byte": b[0] if len(b) == 1 else None, "mono_before": C.mono(), "mono_after": None, "result": "error", "returned": None,
                 "errno": None, "error": "write did not return"}
        self.gate_writes.append(entry)
        try:
            n = self.real["os.write"](fd, data)
        except OSError as e:
            entry.update(mono_after=C.mono(), result="error", errno=e.errno, error="%s: %s" % (type(e).__name__, e))
            raise
        except BaseException as e:
            entry.update(mono_after=C.mono(), result="error", errno=None, error="%s: %s" % (type(e).__name__, e))
            raise
        if n == len(b):
            entry.update(mono_after=C.mono(), result="ok", returned=n, errno=None, error=None)
        else:
            entry.update(mono_after=C.mono(), result="error", returned=n, errno=None, error="short write %r of %d" % (n, len(b)))
        return n

    def close(self, fd):
        if self.watch_fd is not None and fd == self.watch_fd:
            self.gate_closes.append({"test": self.test, "mono": C.mono(), "fd": fd})
            self.watch_fd = None
        return self.real["os.close"](fd)

    def install(self):
        import signal
        import subprocess
        import observer as O
        r = self.real
        for modname, mod, names in (("os", os, ("kill", "killpg", "system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp",
                                                "execlpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
                                                "posix_spawn", "posix_spawnp", "forkpty", "wait", "wait3", "wait4", "waitid")),
                                    ("signal", signal, ("pidfd_send_signal", "raise_signal", "pthread_kill")),
                                    ("subprocess", subprocess, ("Popen", "run", "call", "check_call", "check_output"))):
            for n in names:
                if hasattr(mod, n):
                    r[modname + "." + n] = getattr(mod, n)
                    setattr(mod, n, self._trap(modname + "." + n))
        r["os.fork"], r["os.waitpid"], r["os.write"], r["os.close"] = os.fork, os.waitpid, os.write, os.close
        r["Observer.release"] = O.Observer.release
        os.fork, os.waitpid, os.write, os.close = self.fork, self.waitpid, self.write, self.close
        O.Observer.release = self._trap(GJ.RELEASE_CALL)
        self.installed = True

    def uninstall(self):
        import signal
        import subprocess
        import observer as O
        for key, fn in self.real.items():
            modname, n = key.split(".", 1)
            setattr({"os": os, "signal": signal, "subprocess": subprocess, "Observer": O.Observer}[modname], n, fn)
        self.installed = False

    def summary(self):
        return {"violations": self.violations, "fork_calls": self.fork_calls, "fork_pids": self.fork_pids, "fork_events": self.fork_events,
                "waitpid_calls": self.waitpid_calls, "gate_writes": self.gate_writes, "gate_closes": self.gate_closes}


# ------------------------------------------------------------------ earlier runs (read-only; facts of closure.preflight)
def collect_run_facts(name, path, tool_id, tool_sha):
    """The per-directory facts of closure.preflight for ONE earlier 'g1_' entry.  Reads only; creates, repairs and deletes nothing."""
    try:
        st = os.lstat(path)
    except OSError:
        return {"entry": "unreadable"}
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid():
        return {"entry": "not_a_directory"}
    try:
        names = os.listdir(path)
    except OSError:
        return {"entry": "unreadable"}
    f = {"entry": "real_dir"}
    cstate, craw = GR.read_regular(os.path.join(path, CLOSED_NAME), GJ.MARKER_MAX_BYTES)
    closed = None
    if cstate == "size_exceeds":
        cstate = "oversize_or_empty"
    elif cstate == "ok":
        cstate, closed = GJ.classify_marker(craw)
    f["closed"] = cstate
    f.update(closed_runid="na", criteria_vs_tool="na", criteria_vs_summary="na", summary="na", summary_binding="na", evidence="na", evidence_binding="na")
    if cstate == "ok":
        s_state, s_obj = GR.read_bound(os.path.join(path, SUMMARY_NAME), closed["summary_sha256"], closed["summary_bytes"])
        e_state, e_obj = GR.read_bound(os.path.join(path, EVIDENCE_NAME), closed["evidence_sha256"], closed["evidence_bytes"])
        f["summary"], f["evidence"] = s_state, e_state
        f.update(GJ.closure_bindings(name, closed, s_state, s_obj, e_state, e_obj, tool_id, tool_sha))
    tstate, traw = GR.read_regular(os.path.join(path, CLOSED_TMP_NAME), GJ.MARKER_MAX_BYTES)
    if tstate == "absent":
        f["tmp"] = "absent"
    else:
        f["tmp"] = "identical" if (cstate == "ok" and tstate == "ok" and traw == craw) else "other"
    f["stray_closure_names"] = any(n.startswith("g1_closed") and n not in (CLOSED_NAME, CLOSED_TMP_NAME) for n in names)
    f["manual_disposition"] = MANUAL in names
    return f


def closure_preflight(ev_root, crit, live_residue):
    """CL1-01..CL1-23 over the evidence root (the 'g1_' entries).  -> (unresolved_prior list, details dict).  Read-only."""
    tool_id, tool_sha = G1A.CRITERIA_ID, C.sha256_file(G1A.CRITERIA_PATH)
    glob = {"root_manual_disposition": False, "root_listing": "complete", "live_marker_process": bool(live_residue)}
    try:
        listing = os.listdir(ev_root)
    except FileNotFoundError:
        listing = []                                           # no evidence root yet: there is no earlier run
    except OSError:
        listing = []
        glob["root_listing"] = "incomplete"
    names = sorted(n for n in listing if n.startswith("g1_"))
    glob["root_manual_disposition"] = os.path.lexists(os.path.join(ev_root, MANUAL))
    unresolved, details = [], {}
    for n in names:
        facts = collect_run_facts(n, os.path.join(ev_root, n), tool_id, tool_sha)
        hits = [h for h in GJ.closure_reasons(facts, glob, crit) if h["scope"] == "directory"]
        details[n] = {"facts": facts, "reasons": [h["reason"] for h in hits]}
        unresolved += ["%s:%s" % (n, h["reason"]) for h in hits]
    g_hits = GJ.closure_reasons(None, glob, crit)
    unresolved += [":%s" % h["reason"] for h in g_hits]
    return unresolved, {"entries": details, "global_facts": glob, "global_reasons": [h["reason"] for h in g_hits]}


def preflight(run_dir, exclude, crit):
    problems = []
    if sys.version_info[:3] != (3, 13, 16):
        problems.append("python %s != 3.13.16" % (sys.version.split()[0],))
    if not sys.flags.dont_write_bytecode:
        problems.append("run with python -B (bytecode writing would modify the code directory)")
    if not hasattr(os, "pidfd_open") or not hasattr(__import__("socket"), "send_fds"):
        problems.append("pidfd_open / send_fds missing")
    sig = C.read_sigign(os.getpid())
    if sig is None or sig & C.SIGIGN_SIGCHLD_BIT:
        problems.append("SIGCHLD ignored or unreadable (a child would be auto-reaped)")
    table, enum_problems = C.scan_proc()
    kids = C.children_of(table, os.getpid())
    residue, tp = token_scan(exclude)
    g0_residue, g0_tp = GR.token_scan(exclude)
    enum_problems = dict(enum_problems)
    enum_problems.update({"token_" + str(k): v for k, v in tp.items()})
    enum_problems.update({"g0_token_" + str(k): v for k, v in g0_tp.items()})
    unresolved_g0, details_g0 = GR.closure_preflight(G1A.EVIDENCE_ROOT, GJ0.load_criteria(), g0_residue)       # the G0 history, with the frozen G0 V5 rules
    unresolved_g1, details_g1 = closure_preflight(G1A.EVIDENCE_ROOT, crit, residue)
    g0ref = G1A.g0_reference_status()
    unique = not os.path.exists(run_dir)
    if kids:
        problems.append("observer already has children %r" % kids)
    if not g0ref["ok"]:
        problems.append("G0 REAL-001 reference not verified: %s" % g0ref["problems"])
    all_residue = residue + g0_residue
    unresolved = unresolved_g0 + unresolved_g1
    return {"ok": not (problems or unresolved or all_residue or enum_problems or kids) and unique and g0ref["ok"], "problems": problems, "children": len(kids),
            "token_residue": all_residue, "unresolved_prior": unresolved, "enumeration_problems": {str(k): v for k, v in enum_problems.items()},
            "run_id_unique": unique, "fd_count": len(os.listdir("/proc/self/fd")), "total_procs": len(table), "g0_reference": g0ref,
            "closure": {"g0": details_g0, "g1": details_g1}}


def safe_preflight(run_dir, exclude, crit):
    """The preflight never raises: an exception (for example /proc unreadable) is a clean-failing preflight, BLOCKED and never FAIL."""
    try:
        return preflight(run_dir, exclude, crit)
    except BaseException as e:
        try:
            fdc = len(os.listdir("/proc/self/fd"))
        except OSError:
            fdc = 0
        return {"ok": False, "problems": ["preflight raised %s: %s" % (type(e).__name__, e)], "children": 0, "token_residue": [], "unresolved_prior": [],
                "enumeration_problems": {"preflight": traceback.format_exc()[-400:]}, "run_id_unique": not os.path.exists(run_dir), "fd_count": fdc,
                "total_procs": 0, "g0_reference": {"ok": False}}


def prepare_dirs(run_dir):
    """Evidence root and consumption directory: created if absent or validated.  The run directory is created EXCLUSIVELY (mkdir fails if it exists)."""
    root = GR.ensure_dir(G1A.EVIDENCE_ROOT)
    consumed = GR.ensure_dir(G1A.CONSUMED_DIR)
    try:
        os.mkdir(run_dir, 0o755)
    except OSError as e:
        raise DirError("cannot create the run directory %s exclusively: %r" % (run_dir, e))
    return root, consumed, {"path": run_dir, "created_by_this_process": True}


# ------------------------------------------------------------------ the controlled run
class _Run:
    """Mutable state shared by run() and run_test()."""


def _held_snapshot(S, name, rec):
    s = GR.snapshot(name, S.obs_pid, rec.pid, with_fds=True)
    s["messages_received"] = msgs(rec)
    s["first_action_mono"] = rec.first_action_mono
    return s


def run_test(S, tid):
    """One test: spawn, hold, snapshot, stimulus, observe the exit, reap, clean up.  -> True when the test was clearly as expected (in-run safety rule)."""
    ev, obs, guard, budget, lim = S.ev, S.obs, S.guard, S.budget, S.lim
    scn = S.crit["scenarios"]["tests"][tid]
    stim = scn["stimulus"]
    t = ev["tests"][tid]
    t["ran"] = True
    t["t_gate_max"] = float(scn["t_gate_max_s"])
    t0 = C.mono()
    events = {"start_mono": t0, "hold_start_mono": None, "stimulus_mono": None, "pidfd_readable_mono": None, "reap_mono": None, "proc_gone_mono": None,
              "end_mono": None, "exit_message_mono": None}
    snaps = {}
    t["events"], t["snapshots"] = events, snaps
    t["stimulus"] = {"kind": stim["kind"], "planned_bytes": list(stim["planned_gate_bytes"]), "queued_spec": False, "gate_open_at_exit": None}
    guard.begin_test(tid)
    try:
        budget.check("start of " + tid)
        snaps["S0_before_fork"] = GR.snapshot("S0_before_fork", S.obs_pid)
        spec = dict(S.crit["scenarios"]["common"]["spec"], label=tid)
        rec = obs.spawn_direct("sleeper", tid, spec, S.node.node_main, t_gate_max=t["t_gate_max"], hold_release=True)
        S.rec = rec
        if rec.state != "REGISTERED":
            raise RuntimeError("child not registered: state %s, problems %r" % (rec.state, obs.problems))
        t["node"] = {"node_id": rec.node_id, "pid": rec.pid, "starttime": rec.starttime, "gate_ino": rec.gate_ino}
        fe = [e for e in guard.fork_events if e["test"] == tid][-1]
        events["hold_start_mono"] = C.mono()
        hold_end = events["hold_start_mono"] + lim["hold_before_stimulus_s"]
        while C.mono() < hold_end:
            budget.check("hold")
            obs.serve(min(0.05, hold_end - C.mono()))
        snaps["S1_held_registered_unreleased"] = _held_snapshot(S, "S1_held_registered_unreleased", rec)
        obs.serve(0.0)
        snaps["S1b_pre_stimulus"] = _held_snapshot(S, "S1b_pre_stimulus", rec)
        budget.check("stimulus")
        events["stimulus_mono"] = C.mono()
        kind = stim["kind"]
        if kind == "abort_held":
            S.proto.send_msg(rec.sock, {"t": "SPEC", "spec": spec})            # pre-queued: a leaking gate would act on it
            t["stimulus"]["queued_spec"] = True
            guard.watch_fd = rec.gate_w
            obs.abort_held(rec)                                               # ABORTED record, b"A" on the gate, close of the gate write end
        elif kind == "close_only":
            guard.watch_fd = rec.gate_w
            os.close(rec.gate_w)
            rec.gate_w = None
        elif kind == "write_byte":
            guard.watch_fd = rec.gate_w
            os.write(rec.gate_w, bytes(stim["planned_gate_bytes"]))
            os.close(rec.gate_w)
            rec.gate_w = None
        else:                                                                 # "none": the gate stays open and silent
            guard.watch_fd = rec.gate_w
        if kind == "none":
            wait_s = max(0.0, fe["mono_before"] + t["t_gate_max"] + lim["t4_exit_margin_s"] - C.mono())       # the fork time is the timeout reference
        else:
            wait_s = lim["exit_deadline_s"]

        def exited():
            if rec.first_action_mono is not None and events["exit_message_mono"] is None:       # a child that passed the gate is ended by a control message
                events["exit_message_mono"] = C.mono()
                try:
                    S.proto.send_msg(rec.sock, {"t": "EXIT"})
                except OSError:
                    pass
            return rec.handle.exited()
        if not budget.wait(obs, exited, "exit:" + tid, wait_s):
            raise RuntimeError("child did not exit within %.1f s after the stimulus / the gate timer (or the total budget)" % wait_s)
        events["pidfd_readable_mono"] = C.mono()
        t["stimulus"]["gate_open_at_exit"] = rec.gate_w is not None
        t["messages_received"] = msgs(rec)
        t["ready_received"] = rec.ready is not None
        t["first_action_mono"] = rec.first_action_mono
        snaps["S3_exited_unreaped"] = GR.snapshot("S3_exited_unreaped", S.obs_pid, rec.pid)
        reap_by = C.mono() + budget.cap(lim["reap_deadline_s"])
        while True:                                                           # bounded non-blocking polls of the ONE child pid; the guard records every call
            budget.check("reap")
            pid, status = os.waitpid(rec.pid, os.WNOHANG)
            if pid == rec.pid:
                break
            if C.mono() > reap_by:
                ev["deadline_hits"].append("reap:" + tid)
                raise RuntimeError("child not reaped within %.1f s" % lim["reap_deadline_s"])
            time.sleep(0.01)
        events["reap_mono"] = C.mono()
        rec.exit_status = os.waitstatus_to_exitcode(status)
        t["reap"] = {"waitpid_pid": pid, "exit_status": rec.exit_status, "raw_status": status}
        gone_by = C.mono() + budget.cap(lim["reap_deadline_s"])
        while C.read_stat(rec.pid) is not None:
            budget.check("proc_gone")
            if C.mono() > gone_by:
                ev["deadline_hits"].append("proc_gone:" + tid)
                raise RuntimeError("/proc/%d still present after reap" % rec.pid)
            time.sleep(0.01)
        events["proc_gone_mono"] = C.mono()
        snaps["S4_reaped"] = GR.snapshot("S4_reaped", S.obs_pid, rec.pid)
        if rec.gate_w is not None:                                            # T4 only: closed AFTER the exit was observed (recorded by the guard)
            os.close(rec.gate_w)
            rec.gate_w = None
        guard.watch_fd = None
        budget.check("cleanup")
        cl = obs.finish_cleanup(nodes=[rec], grace=max(0.1, min(3.0, budget.left() / 6.0)))      # only after the reap: the pidfd is readable -> 'already_exited'
        t["cleanup"] = {"cleanup_ok": cl["cleanup_ok"], "rounds": cl["rounds"], "residual_detail": cl["residual_detail"]}
        snaps["S5_after_cleanup"] = GR.snapshot("S5_after_cleanup", S.obs_pid, rec.pid)
        events["end_mono"] = C.mono()
        t["timing"] = {"duration": events["end_mono"] - t0}
        if t["timing"]["duration"] > lim["per_test_seconds"]:
            ev["deadline_hits"].append("test:" + tid)
        ok, reasons = in_run_assessment(t, scn, rec.exit_status, guard.violations, ev["deadline_hits"])
        if not ok:
            stderr_marker("G1-TEST-STOP", run_id=ev["run_id"], test=tid, reasons="; ".join(reasons))
        return ok
    except BaseException:
        t["exception"] = traceback.format_exc()[-800:]
        raise
    finally:
        guard.watch_fd = None


def run(auth, auth_raw, run_id, run_dir, pf, dirs, crit):
    import node
    import observer as O
    import proto

    t0 = C.mono()
    root_info, consumed_info, rundir_info = dirs
    lim = crit["limits"]
    order = list(crit["scenarios"]["order"])
    ev = {"evidence_schema": EVIDENCE_SCHEMA_ID, "run_id": run_id, "auth_expected": auth["bindings"], "bindings_start": current(), "preflight": pf,
          "evidence_root": root_info, "consumed_dir": consumed_info, "run_dir": rundir_info, "cleanup": None, "run_snapshots": {}, "exception": None,
          "aborted": None, "stopped_after": None, "deadline_hits": [], "manual_disposition": None, "auth_consumed": False,
          "tests": {tid: blank_test(tid) for tid in order}}
    budget = GR.Budget(ev, lim["max_seconds"])
    guard = G1Guard(lim["max_forks"])
    obs_pid = os.getpid()
    exclude = GR.ancestors(obs_pid)
    ev["observer"] = {"pid": obs_pid, "sid": C.fingerprint(obs_pid)["sid"], "pgrp": C.fingerprint(obs_pid)["pgrp"]}
    S = _Run()
    S.ev, S.guard, S.budget, S.lim, S.crit, S.obs_pid, S.rec, S.node, S.proto, S.obs = ev, guard, budget, lim, crit, obs_pid, None, node, proto, None
    obs = None
    try:
        with open(os.path.join(run_dir, "authorization_used.json"), "xb") as f:
            f.write(auth_raw)
        budget.check("start")
        if not pf["ok"]:
            raise RuntimeError("preflight not clean: %r" % {k: pf[k] for k in ("problems", "unresolved_prior", "token_residue", "enumeration_problems", "children", "g0_reference")})
        with open(G1A.consumed_marker(auth["authorization_id"]), "x") as f:      # single use: consumed BEFORE the first fork, even if the run later fails
            json.dump({"authorization_id": auth["authorization_id"], "run_id": run_id, "consumed_utc": utc_now(), "bindings": ev["bindings_start"]}, f)
        ev["auth_consumed"] = True
        ev["run_snapshots"]["S0_run"] = GR.snapshot("S0_run", obs_pid)
        budget.check("S0_run")
        reg_path = os.path.join(run_dir, "registry.jsonl")
        obs = O.Observer(reg_path)
        obs.trial_tag = "G1"
        S.obs = obs
        obs.reg.write("RUN_START", run_id=run_id, prereg_sha256=GR.prereg_sha(), observer_pid=obs_pid, phase="G1")
        guard.install()
        for tid in order:
            if not run_test(S, tid):
                ev["stopped_after"] = tid
                break
        budget.check("cleanup")
        cl = obs.final_cleanup(grace=max(0.1, min(3.0, budget.left() / 6.0)))
        ev["cleanup"] = {"cleanup_ok": cl["cleanup_ok"], "run_set": cl["run_set"], "rounds": cl["rounds"], "residual_detail": cl["residual_detail"]}
        scan, scan_problems = token_scan(exclude)
        confirmed = bool(cl["cleanup_ok"]) and not scan and not scan_problems
        obs.reg.write("RUN_END", run_id=run_id, aborted=None, cleanup_confirmed=confirmed, residual=cl["residual_after_kill"],
                      token_residue=[x["pid"] for x in scan], token_scan_problems=sorted(scan_problems))
        budget.check("end")
    except BaseException:
        ev["exception"] = traceback.format_exc()
        rec = S.rec
        if rec is None and obs is not None and obs.nodes:
            rec = list(obs.nodes.values())[-1]
        if rec is not None and rec.pid is not None and rec.handle is not None and not rec.handle.exited():
            ident = {"pid": rec.pid, "starttime": rec.starttime, "node_id": rec.node_id, "verified_by": "REGISTERED record + pidfd",
                     "ends_by": "gate byte / EOF / gate timer (EXIT message for a child that passed the gate); NO signal was or will be sent by G1"}
            _manual(run_dir, run_id, ident, ev)
        elif rec is not None and rec.pid is None and rec.forked_pid is not None:
            try:
                st = C.read_stat(rec.forked_pid)
            except C.ProcUnreadable:
                st = {"state": "UNREADABLE"}
            if st is None or st["state"] in ("Z", "X"):
                pass                                                  # gone or exited-unreaped: nothing alive to dispose of
            else:
                ident = {"pid": rec.forked_pid, "starttime": rec.forked_starttime, "node_id": rec.node_id, "verified_by": "NONE (registration failed; never signalled)",
                         "ends_by": "abort byte already written / gate EOF when this observer exits / gate timer; NO signal was or will be sent by G1"}
                _manual(run_dir, run_id, ident, ev)
        if obs is not None and not any(r["kind"] == "RUN_END" for r in obs.reg.records):
            try:                                                      # honest end marker: cleanup NOT confirmed (a person decides; no signal)
                obs.reg.write("RUN_END", run_id=run_id, aborted=ev["exception"].strip().splitlines()[-1][:200], cleanup_confirmed=False)
            except Exception:
                ev["exception"] += "\nRUN_END not written: " + traceback.format_exc()
    finally:
        guard.uninstall()
        ev["guard"] = guard.summary()
        ev["bindings_end"] = current()
        try:
            s9 = GR.snapshot("S9_final", obs_pid)
            s9["token_residue"], tp = token_scan(exclude)
            if tp:
                s9["enum_problems"].update({"token_" + str(k): v for k, v in tp.items()})
            ev["run_snapshots"]["S9_final"] = s9
        except Exception:
            ev["exception"] = (ev["exception"] or "") + "\nS9: " + traceback.format_exc()
        ev["timing"] = {"duration": C.mono() - t0}
        # LEDGER: the writer's own records and seq, captured after the last registry write and BEFORE the registry file is parsed
        ev["reg_memory_records"] = copy.deepcopy(obs.reg.records) if obs is not None else []
        ev["reg_writer_seq"] = obs.reg.seq if obs is not None else 0
        try:
            import registry as R
            ev["reg"], info = R.parse_reg(os.path.join(run_dir, "registry.jsonl"))
            ev["reg_parse_info"] = info
        except Exception:
            ev["exception"] = (ev["exception"] or "") + "\nREG: " + traceback.format_exc()
    return ev


def _manual(run_dir, run_id, ident, ev):
    try:
        write_exclusive_json(os.path.join(run_dir, MANUAL), {"run_id": run_id, "alive": ident, "decision": "a person decides"})
    except Exception:
        ev["exception"] = (ev["exception"] or "") + "\n%s not written: %s" % (MANUAL, traceback.format_exc())
    ev["manual_disposition"] = ident


# ------------------------------------------------------------------ the evidence pipeline P0..P7 and the closure publication K0..K7
def _blocked_note(run_dir, run_id, info):
    """Best effort, exclusive: g1_blocked_<run_id>.json in the run directory, else in the evidence root.  Its own failure only adds a stderr line."""
    last = None
    for d in (run_dir, G1A.EVIDENCE_ROOT):
        try:
            write_exclusive_json(os.path.join(d, "g1_blocked_%s.json" % run_id), info)
            return
        except Exception as e:
            last = e
    stderr_marker("G1-BLOCKED-NOTE-UNSAVED", run_id=run_id, reason=repr(last))


def publish_closure(run_dir, run_id, criteria_sha256, b2, bs2, s2):
    """P7 = closure.publication K1..K7.  Never overwrites, never deletes the temporary name.  -> the process exit code: the recorded exit code when
    K1..K7 all succeeded, otherwise 3 with G1-CLOSE-UNPUBLISHED (nothing published) or G1-CLOSE-UNCONFIRMED (the link returned) on stderr."""
    tmp, final = os.path.join(run_dir, CLOSED_TMP_NAME), os.path.join(run_dir, CLOSED_NAME)
    published, step, closed_sha, bc = False, "K1", "-", None
    verdict = s2.get("verdict") if isinstance(s2, dict) else None
    try:
        obj, bc = GJ.build_marker(run_id, criteria_sha256, b2, bs2, s2["verdict"], s2["exit_code"])          # K1
        closed_sha = GJ.sha256_hex(bc)
        step = "K2"
        write_exclusive(tmp, bc)                                                                           # K2: O_EXCL + fsync
        step = "K3"
        raw = read_back(tmp)
        if raw != bc or GJ.classify_marker(raw)[0] != "ok":
            raise Unverified("temporary marker differs from the bytes written or is not a valid marker")
        step = "K4"
        os.link(tmp, final, follow_symlinks=False)                                                         # K4: atomic, exclusive (EEXIST)
        published = True
        step = "K5"
        fsync_dir(run_dir)
        step = "K6"
        raw = read_back(final)
        if raw != bc or GJ.classify_marker(raw)[0] != "ok":
            raise Unverified("published marker differs from the bytes written or is not a valid marker")
        step = "K7"
        return s2["exit_code"]
    except BaseException as e:
        marker = "G1-CLOSE-UNCONFIRMED" if published else "G1-CLOSE-UNPUBLISHED"
        stderr_marker(marker, run_id=run_id, step=step, verdict=verdict, evidence_sha256=GJ.sha256_hex(b2), summary_sha256=GJ.sha256_hex(bs2),
                      closed_sha256=closed_sha, reason="%s: %s" % (type(e).__name__, getattr(e, "reason", e)))
        return 3


def finalize(ev, run_id, run_dir, crit, crit_sha):
    """Pipeline P0..P7.  `ev` is the evidence constructed in memory (P0).  -> the process exit code."""
    pipe = {"P0": "constructed"}
    try:
        b = GJ.strict_bytes(ev)                                                                            # P1
    except (TypeError, ValueError, RecursionError) as e:
        stderr_marker("G1-EVIDENCE-UNSAVED", run_id=run_id, stage="P1", reason="%s: %s" % (type(e).__name__, e))
        return 3
    pipe["P1"] = {"sha256": GJ.sha256_hex(b), "bytes": len(b)}
    try:
        b2, e2 = save_and_verify(os.path.join(run_dir, EVIDENCE_NAME), b)                                  # P2 + P3
    except Unsaved as e:
        stderr_marker("G1-EVIDENCE-UNSAVED", run_id=run_id, stage="P2", sha256=e.sha256, partial=str(e.partial).lower(), reason=e.reason)
        _blocked_note(run_dir, run_id, {"run_id": run_id, "stage": "P2", "reason": e.reason, "sha256": e.sha256, "partial": e.partial})
        return 3
    except Unverified as e:
        stderr_marker("G1-EVIDENCE-UNVERIFIED", run_id=run_id, stage="P3", written_sha256=e.written, read_sha256=e.read, reason=e.reason)
        return 3
    pipe["P2"], pipe["P3"] = "saved", "read back and verified"
    invalid = GJ.validate_evidence(e2, crit)                                                               # P4: does not stop the pipeline
    pipe["P4"] = {"invalid_fields": len(invalid)}
    try:
        res = GJ.judge(e2, crit, crit_sha, validation=invalid)                                             # P5: ONLY the read-back evidence
    except BaseException as e:
        stderr_marker("G1-JUDGE-ERROR", run_id=run_id, reason="%s: %s" % (type(e).__name__, e))
        return 3
    pipe["P5"] = {"verdict": res["verdict"]}
    summary = {"run_id": run_id, "criteria_id": crit["criteria_id"], "criteria_sha256": crit_sha, "evidence_sha256": GJ.sha256_hex(b2), "verdict": res["verdict"],
               "exit_code": res["exit_code"], "run_checks": res["run_checks"], "tests": res["tests"], "c03_fidelity_report": res["c03_fidelity_report"],
               "fail_class": res["fail_class"], "blocked_class": res["blocked_class"], "incomplete": res["incomplete"], "pipeline": pipe,
               "scope": "G1 only; not evidence for G0, G2/G3, BV or E1-A"}
    if res["verdict"] == "FAIL":
        summary["fail_scope"] = GJ.FAIL_SCOPE
    try:
        bs = GJ.strict_bytes(summary)                                                                      # P6
        bs2, s2 = save_and_verify(os.path.join(run_dir, SUMMARY_NAME), bs)
    except (Unsaved, Unverified, TypeError, ValueError, RecursionError) as e:
        stderr_marker("G1-SUMMARY-UNSAVED", run_id=run_id, verdict=res["verdict"], evidence_sha256=GJ.sha256_hex(b2), reason="%s: %s" % (type(e).__name__, getattr(e, "reason", e)))
        return 3
    return publish_closure(run_dir, run_id, crit_sha, b2, bs2, s2)                                         # P7


# ------------------------------------------------------------------ command line
def _parser():
    ap = argparse.ArgumentParser(description="G1 negative gate test (ABORT, EOF, INVALID_BYTE, TIMEOUT).  --execute needs a valid single-use G1 authorization.")
    ap.add_argument("--check", action="store_true", help="print bindings and authorization status; starts no process")
    ap.add_argument("--template", action="store_true", help="print a NON-VALID authorization template")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--auth", default=G1A.AUTH_DEFAULT)
    ap.add_argument("--run-id", default=None)
    return ap


def main(argv=None):
    args = _parser().parse_args(argv)           # outside the safety net: argparse may exit 0 (--help) / 2 (usage error)
    try:
        return _main(args)
    except SystemExit as e:                     # ANY SystemExit after parsing -> start-up error (never 1 = FAIL, never 0 = PASS)
        stderr_marker("G1-STARTUP-ERROR", reason="unexpected SystemExit(%r)" % (e.code,))
        return 3
    except BaseException as e:
        stderr_marker("G1-STARTUP-ERROR", reason="%s: %s" % (type(e).__name__, e))
        return 3


def _main(args):
    if args.template:
        print(G1A.template())
        return 0
    cur = current()
    if args.check or not args.execute:
        info = {"stage": "G1", "criteria_id": G1A.CRITERIA_ID, "bindings": cur, "frozen_file_problems": G1A.frozen_problems(), "g0_reference": G1A.g0_reference_status(),
                "authorization_file": args.auth, "authorization_present": os.path.exists(args.auth), "executed": False}
        if os.path.exists(args.auth):
            try:
                G1A.load(args.auth, cur, utc_now())
                info["authorization_valid"] = True
            except G1A.G1AuthorizationError as e:
                info["authorization_valid"] = False
                info["authorization_problem"] = str(e)
        print(json.dumps(info, indent=1))
        return 0
    fp = G1A.frozen_problems()
    if fp:
        print("REFUSED: frozen files differ: %s" % "; ".join(fp), file=sys.stderr)
        return 2
    try:
        auth, raw = G1A.load(args.auth, cur, utc_now())
    except G1A.G1AuthorizationError as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    run_id = args.run_id or ("g1_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + "_" + os.urandom(3).hex())
    if not G1A.ID_RE.match(run_id) or not run_id.startswith("g1_"):
        print("REFUSED: run id %r" % run_id, file=sys.stderr)
        return 2
    run_dir = os.path.join(G1A.EVIDENCE_ROOT, run_id)
    if os.path.exists(run_dir):
        print("REFUSED: run directory exists", file=sys.stderr)
        return 2
    crit = GJ.load_criteria()
    crit_sha = C.sha256_file(G1A.CRITERIA_PATH)
    pf = safe_preflight(run_dir, GR.ancestors(os.getpid()), crit)               # read-only; BEFORE any directory is created
    try:
        dirs = prepare_dirs(run_dir)
    except DirError as e:
        stderr_marker("G1-DIR-ERROR", run_id=run_id, reason=e)
        return 3
    try:
        ev = run(auth, raw, run_id, run_dir, pf, dirs, crit)
    except BaseException:
        stderr_marker("G1-RUN-ERROR", run_id=run_id, reason=traceback.format_exc().strip().splitlines()[-1])
        return 3
    try:
        rc = finalize(ev, run_id, run_dir, crit, crit_sha)
    except BaseException as e:
        stderr_marker("G1-PIPELINE-ERROR", run_id=run_id, reason="%s: %s" % (type(e).__name__, e))
        return 3
    print(json.dumps({"run_id": run_id, "exit_code": rc}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
