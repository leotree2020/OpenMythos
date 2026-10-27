"""G0 entry: the first minimal controlled process-gate test.  WRITTEN, NOT RUN.  `--execute` is refused without a valid single-use
AUTHORIZATION_E1A_GATE_G0.json (see g0_auth.py); `--check` starts no process and reads no /proc entry of any other process.

Implements the FROZEN criteria g0_criteria_v5.json (F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001).
Fixed procedure (E1A_GATE_G0_PREREG_V5.md section 5): one observer, ONE sacrificial gated child, no descendants, ZERO signals.
Python-level guards trap kill/killpg/pidfd_send_signal/exec*/spawn*/system/popen/subprocess and allow exactly one os.fork and
waitpid on the one specific child pid.  A Python-level trap is NOT proof that no kernel path exists (stated in the safety review).
There is no code path from here to G1/G2/G3, BV, E1-A cells, the janitor, or any signal.  On any anomaly the run stops, sends no
signal, keeps the evidence and writes MANUAL_DISPOSITION_REQUIRED.json.

After the run the evidence is saved, judged and closed by the pipeline P0..P7 of the criteria (evidence_pipeline) and the closure
publication K0..K7 (closure.publication): construct -> strict serialisation -> exclusive write + fsync -> read back and verify ->
validate types -> judge ONLY the read-back evidence -> save and verify the summary -> publish g0_closed.json atomically and exclusively
-> exit with the recorded exit code.  Every failure is BLOCKED with exit code 3 and a marker on stderr."""
import argparse
import copy
import errno
import json
import os
import stat
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402

TOKEN = "g0_run.py"                                                 # diagnostic scan marker (command line); never authorizes a signal
SPEC = {"label": "g0", "role": "sleeper", "mode": "none", "children": []}
MANUAL = "MANUAL_DISPOSITION_REQUIRED.json"
EVIDENCE_NAME, SUMMARY_NAME, CLOSED_NAME, CLOSED_TMP_NAME = "g0_evidence.json", "g0_summary.json", "g0_closed.json", "g0_closed.json.tmp"
EVIDENCE_SCHEMA_ID = "e1a-gate-g0-evidence-4"
MAX_BOUND_BYTES = 256 * 1024 * 1024                                  # a marker that binds a larger file is treated as a size mismatch


# ------------------------------------------------------------------ pure helpers (no process is started by any of them)
def bench_code_hash():
    h = []
    for f in sorted(os.listdir(C.BENCH_DIR)):
        if f.endswith(".py"):
            h.append("%s:%s" % (f, C.sha256_file(os.path.join(C.BENCH_DIR, f))))
    return C.sha256_bytes("\n".join(h).encode())


def git_head():
    try:
        gd = os.path.join(C.REPO_ROOT, ".git")
        head = open(os.path.join(gd, "HEAD")).read().strip()
        if not head.startswith("ref: "):
            return head
        ref = head[5:]
        p = os.path.join(gd, ref)
        if os.path.exists(p):
            return open(p).read().strip()
        for line in open(os.path.join(gd, "packed-refs")):
            if line.strip().endswith(" " + ref):
                return line.split()[0]
    except OSError:
        pass
    return "UNKNOWN"


def prereg_sha():
    return C.sha256_file(C.PREREG_PATH)


def current():
    return GA.current_bindings(git_head(), prereg_sha(), bench_code_hash())


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stderr_marker(marker, **fields):
    """One line on stderr: `<MARKER> k=v ...`.  Used to mark an unsaved / unverified / unconfirmed state (criteria: the pipeline failures)."""
    parts = ["%s=%s" % (k, " ".join(str(v).split())[:300]) for k, v in fields.items()]
    print("%s %s" % (marker, " ".join(parts)), file=sys.stderr, flush=True)


# ------------------------------------------------------------------ Python-level guard
class GuardViolation(Exception):
    pass


class Guard:
    def __init__(self):
        self.violations, self.fork_pids, self.waitpid_calls, self.release_writes = [], [], [], []
        self.fork_calls = 0
        self.watch_fd = None
        self.allowed_pid = None
        self.real = {}
        self.installed = False

    def _trap(self, name):
        def trap(*a, **k):
            self.violations.append({"call": name, "mono": C.mono(), "args": repr(a)[:120]})
            raise GuardViolation("G0 guard refused %s" % name)
        return trap

    def install(self):
        import signal
        import subprocess
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
        r["os.fork"], r["os.waitpid"], r["os.write"] = os.fork, os.waitpid, os.write

        def g_fork():
            if self.fork_calls >= 1:
                self.violations.append({"call": "os.fork (second)", "mono": C.mono()})
                raise GuardViolation("G0 allows exactly one fork")
            self.fork_calls += 1
            pid = r["os.fork"]()
            if pid != 0:                                     # parent only
                self.fork_pids.append(pid)
                self.allowed_pid = pid
            return pid

        def g_waitpid(pid, options=0):
            t = C.mono()
            if not isinstance(pid, int) or pid <= 0 or pid != self.allowed_pid:
                self.violations.append({"call": "os.waitpid", "mono": t, "args": repr((pid, options))})
                raise GuardViolation("G0 allows waitpid only on the one specific child pid")
            got = r["os.waitpid"](pid, options)
            self.waitpid_calls.append({"pid": pid, "options": options, "returned": got[0], "status": got[1], "mono": t})
            return got

        def g_write(fd, data):
            """F-18: every write of the release byte is an ENTRY with mono_before, mono_after and the result; the entry exists before the call, a
            failed write is recorded as an error (never dropped), and a pre-write time is never taken for a write."""
            if not (self.watch_fd is not None and fd == self.watch_fd and bytes(data) == b"R"):
                return r["os.write"](fd, data)
            entry = {"mono_before": C.mono(), "mono_after": None, "result": "error", "returned": None, "errno": None, "error": "write did not return"}
            self.release_writes.append(entry)
            try:
                n = r["os.write"](fd, data)
            except OSError as e:
                entry.update(mono_after=C.mono(), result="error", errno=e.errno, error="%s: %s" % (type(e).__name__, e))
                raise
            except BaseException as e:
                entry.update(mono_after=C.mono(), result="error", errno=None, error="%s: %s" % (type(e).__name__, e))
                raise
            if n == 1:
                entry.update(mono_after=C.mono(), result="ok", returned=n, errno=None, error=None)
            else:
                entry.update(mono_after=C.mono(), result="error", returned=n, errno=None, error="unexpected write result %r (need 1)" % (n,))
            return n

        os.fork, os.waitpid, os.write = g_fork, g_waitpid, g_write
        self.installed = True

    def uninstall(self):
        import signal
        import subprocess
        for key, fn in self.real.items():
            modname, n = key.split(".", 1)
            setattr({"os": os, "signal": signal, "subprocess": subprocess}[modname], n, fn)
        self.installed = False

    def summary(self):
        return {"violations": self.violations, "fork_calls": self.fork_calls, "fork_pids": self.fork_pids, "waitpid_calls": self.waitpid_calls,
                "release_writes": self.release_writes}


# ------------------------------------------------------------------ read-only /proc observation
def ancestors(pid):
    out, seen = set(), set()
    while pid and pid not in seen:
        seen.add(pid)
        st = C.read_stat(pid)
        if st is None:
            break
        out.add(pid)
        pid = st["ppid"]
    return out


def token_scan(exclude):
    """Diagnostic only: live processes (not zombies, not the excluded ancestors/self) whose command line carries the G0 marker."""
    table, problems = C.scan_proc()
    found = []
    for pid, st in sorted(table.items()):
        if pid in exclude or st["state"] in ("Z", "X"):
            continue
        cmd = " ".join(C.read_cmdline(pid) or [])
        if TOKEN in cmd:
            found.append({"pid": pid, "starttime": st["starttime"], "ppid": st["ppid"], "state": st["state"], "cmdline": cmd[:160]})
    return found, problems


def fd_report(pid):
    links = C.fd_links(pid)
    if links is None:
        return None
    out = {}
    for fd, target in links.items():
        access = None
        try:
            with open("/proc/%d/fdinfo/%d" % (pid, fd)) as f:
                for line in f:
                    if line.startswith("flags:"):
                        access = {0: "r", 1: "w", 2: "rw"}.get(int(line.split()[1], 8) & 3)
        except (OSError, ValueError):
            pass
        out[str(fd)] = {"target": target, "access": access}
    return out


def snapshot(name, obs_pid, child_pid=None, with_fds=False, tokens=False, exclude=()):
    table, problems = C.scan_proc()
    kids = C.children_of(table, obs_pid)
    desc = C.descendants_of(table, obs_pid)
    child = None
    if child_pid is not None and child_pid in table:
        st = table[child_pid]
        child = {"pid": child_pid, "starttime": st["starttime"], "ppid": st["ppid"], "state": st["state"], "sid": st["sid"], "pgrp": st["pgrp"]}
    s = {"name": name, "children": kids, "grandchildren": [d for d in desc if d not in kids], "total_procs": len(table),
         "enum_problems": {str(k): v for k, v in problems.items()}, "fd_count": len(os.listdir("/proc/self/fd")), "child": child}
    if with_fds and child_pid is not None:
        s["fds"] = fd_report(child_pid)
    if tokens:
        s["token_residue"], tp = token_scan(set(exclude))
        if tp:
            s["enum_problems"].update({"token_" + str(k): v for k, v in tp.items()})
    s["mono"] = C.mono()                                    # taken AFTER every observation of this snapshot
    return s


# ------------------------------------------------------------------ reading earlier runs (read-only; facts of closure.preflight)
def read_regular(path, limit):
    """-> (state, bytes): 'ok' | 'absent' | 'not_regular' (symlink, directory, ...) | 'unreadable' | 'size_exceeds' (larger than `limit`)."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return "absent", None
    except OSError as e:
        return ("not_regular" if e.errno in (errno.ELOOP, errno.EMLINK) else "unreadable"), None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return "not_regular", None
        if st.st_size > limit:
            return "size_exceeds", None
        chunks = []
        while True:
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
        return "ok", b"".join(chunks)
    except OSError:
        return "unreadable", None
    finally:
        os.close(fd)


def read_bound(path, want_sha256, want_bytes):
    """A file bound by the closure marker.  -> (fact, parsed): absent | not_regular | unreadable | size_mismatch | hash_mismatch | unparsable | ok."""
    if want_bytes > MAX_BOUND_BYTES:
        return "size_mismatch", None
    state, raw = read_regular(path, want_bytes)
    if state == "size_exceeds":
        return "size_mismatch", None
    if state != "ok":
        return state, None
    return GJ.classify_blob(raw, want_sha256, want_bytes)


def collect_run_facts(name, path, tool_id, tool_sha):
    """The per-directory facts of closure.preflight for ONE earlier 'g0_' entry.  Reads only; creates, repairs and deletes nothing."""
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
    cstate, craw = read_regular(os.path.join(path, CLOSED_NAME), GJ.MARKER_MAX_BYTES)
    closed = None
    if cstate == "size_exceeds":
        cstate = "oversize_or_empty"
    elif cstate == "ok":
        cstate, closed = GJ.classify_marker(craw)
    f["closed"] = cstate
    f.update(closed_runid="na", criteria_vs_tool="na", criteria_vs_summary="na", summary="na", summary_binding="na", evidence="na", evidence_binding="na")
    if cstate == "ok":
        s_state, s_obj = read_bound(os.path.join(path, SUMMARY_NAME), closed["summary_sha256"], closed["summary_bytes"])
        e_state, e_obj = read_bound(os.path.join(path, EVIDENCE_NAME), closed["evidence_sha256"], closed["evidence_bytes"])
        f["summary"], f["evidence"] = s_state, e_state
        f.update(GJ.closure_bindings(name, closed, s_state, s_obj, e_state, e_obj, tool_id, tool_sha))
    tstate, traw = read_regular(os.path.join(path, CLOSED_TMP_NAME), GJ.MARKER_MAX_BYTES)
    if tstate == "absent":
        f["tmp"] = "absent"
    else:
        f["tmp"] = "identical" if (cstate == "ok" and tstate == "ok" and traw == craw) else "other"
    f["stray_closure_names"] = any(n.startswith("g0_closed") and n not in (CLOSED_NAME, CLOSED_TMP_NAME) for n in names)
    f["manual_disposition"] = MANUAL in names
    return f


def closure_preflight(ev_root, crit, live_residue):
    """CL-01..CL-23 over the evidence root.  -> (unresolved_prior list of '<entry>:<REASON>' / ':<REASON>', details dict).  Read-only."""
    tool_id, tool_sha = GA.CRITERIA_ID, C.sha256_file(GA.CRITERIA_PATH)
    glob = {"root_manual_disposition": False, "root_listing": "complete", "live_marker_process": bool(live_residue)}
    names = []
    try:
        listing = os.listdir(ev_root)
    except FileNotFoundError:
        listing = []                                           # no evidence root yet: there is no earlier run
    except OSError:
        listing = []
        glob["root_listing"] = "incomplete"
    names = sorted(n for n in listing if n.startswith("g0_"))
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


def preflight(run_dir, exclude):
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
    enum_problems = dict(enum_problems)
    enum_problems.update({"token_" + str(k): v for k, v in tp.items()})
    unresolved, details = closure_preflight(GA.EVIDENCE_ROOT, GJ.load_criteria(), residue)
    unique = not os.path.exists(run_dir)
    if kids:
        problems.append("observer already has children %r" % kids)
    return {"ok": not (problems or unresolved or residue or enum_problems or kids) and unique, "problems": problems, "children": len(kids), "token_residue": residue,
            "unresolved_prior": unresolved, "enumeration_problems": {str(k): v for k, v in enum_problems.items()}, "run_id_unique": unique,
            "fd_count": len(os.listdir("/proc/self/fd")), "total_procs": len(table), "closure": details}


def safe_preflight(run_dir, exclude):
    """The preflight never raises: an exception (for example /proc unreadable) is a clean-failing preflight, BLOCKED and never FAIL."""
    try:
        return preflight(run_dir, exclude)
    except BaseException as e:
        try:
            fdc = len(os.listdir("/proc/self/fd"))
        except OSError:
            fdc = 0
        return {"ok": False, "problems": ["preflight raised %s: %s" % (type(e).__name__, e)], "children": 0, "token_residue": [], "unresolved_prior": [],
                "enumeration_problems": {"preflight": traceback.format_exc()[-400:]}, "run_id_unique": not os.path.exists(run_dir), "fd_count": fdc, "total_procs": 0}


# ------------------------------------------------------------------ directories (F-12 / F-13)
class DirError(Exception):
    pass


def dir_info(path, created):
    st = os.lstat(path)
    return {"path": path, "created_by_this_run": bool(created), "uid": st.st_uid, "mode": stat.S_IMODE(st.st_mode), "ino": st.st_ino}


def ensure_dir(path):
    """Create `path` non-recursively (mode 0755) only if it is absent; otherwise validate it: a real directory (not a symlink), owned by the
    effective uid, not group/other-writable.  -> info dict (evidence_root / consumed_dir).  Raises DirError."""
    created = False
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        try:
            os.mkdir(path, 0o755)
            created = True
        except FileExistsError:
            pass
        except OSError as e:
            raise DirError("cannot create %s: %r" % (path, e))
        st = os.lstat(path)
    except OSError as e:
        raise DirError("cannot stat %s: %r" % (path, e))
    if not stat.S_ISDIR(st.st_mode):
        raise DirError("%s is not a real directory (symlink or file)" % path)
    if st.st_uid != os.geteuid():
        raise DirError("%s is owned by uid %d, not by the effective uid %d" % (path, st.st_uid, os.geteuid()))
    if st.st_mode & 0o022:
        raise DirError("%s is group/other-writable (mode %o)" % (path, stat.S_IMODE(st.st_mode)))
    return dir_info(path, created)


def prepare_dirs(run_dir):
    """Evidence root and consumption directory: created if absent or validated.  The run directory is created EXCLUSIVELY (mkdir fails if it exists)."""
    root = ensure_dir(GA.EVIDENCE_ROOT)
    consumed = ensure_dir(GA.CONSUMED_DIR)
    try:
        os.mkdir(run_dir, 0o755)
    except OSError as e:
        raise DirError("cannot create the run directory %s exclusively: %r" % (run_dir, e))
    return root, consumed, {"path": run_dir, "created_by_this_process": True}


def write_exclusive_json(path, obj):
    """Exclusive creation (never overwrites), strict serialisation (no default=), fsync.  Raises on any failure."""
    data = GJ.strict_bytes(obj)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        off = 0
        while off < len(data):
            n = os.write(fd, memoryview(data)[off:])
            if n <= 0:
                raise OSError(errno.EIO, "write returned %d" % n)
            off += n
        os.fsync(fd)
    finally:
        os.close(fd)


# ------------------------------------------------------------------ the total budget (F-9)
class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """limits.max_seconds is checked at every phase boundary and loop iteration while the run is in progress; a breach records the deadline
    hit 'total' and stops the run.  Phase deadlines are capped by what is left of the total."""

    def __init__(self, ev, max_seconds):
        self.ev, self.max, self.t0 = ev, float(max_seconds), C.mono()

    def left(self):
        return self.max - (C.mono() - self.t0)

    def check(self, where):
        if self.left() <= 0:
            if "total" not in self.ev["deadline_hits"]:
                self.ev["deadline_hits"].append("total")
            raise BudgetExceeded("total budget of %.1f s exhausted at %s" % (self.max, where))

    def cap(self, seconds):
        return max(0.0, min(float(seconds), self.left()))

    def wait(self, obs, cond, phase, deadline):
        """obs.wait_for with the phase deadline capped by the total budget.  -> True when cond held; False records the hit (phase name, or 'total')."""
        self.check("start of phase " + phase)
        d = self.cap(deadline)
        if obs.wait_for(cond, d):
            return True
        hit = "total" if d < float(deadline) else phase
        if hit not in self.ev["deadline_hits"]:
            self.ev["deadline_hits"].append(hit)
        return False


# ------------------------------------------------------------------ the one controlled run
def run(auth, auth_raw, run_id, run_dir, pf, dirs):
    import node
    import observer as O
    import proto

    t0 = C.mono()
    root_info, consumed_info, rundir_info = dirs
    ev = {"evidence_schema": EVIDENCE_SCHEMA_ID, "run_id": run_id, "auth_expected": auth["bindings"], "bindings_start": current(), "snapshots": {}, "events": {},
          "reap": {}, "cleanup": {"rounds": []}, "deadline_hits": [], "exception": None, "aborted": None, "auth_consumed": False, "preflight": pf,
          "evidence_root": root_info, "consumed_dir": consumed_info, "run_dir": rundir_info}
    lim = GJ.load_criteria()["limits"]
    budget = Budget(ev, lim["max_seconds"])
    guard = Guard()
    obs_pid = os.getpid()
    exclude = ancestors(obs_pid)
    ev["observer"] = {"pid": obs_pid, "sid": C.fingerprint(obs_pid)["sid"], "pgrp": C.fingerprint(obs_pid)["pgrp"]}
    rec = obs = None
    try:
        with open(os.path.join(run_dir, "authorization_used.json"), "xb") as f:
            f.write(auth_raw)
        budget.check("start")
        if not pf["ok"]:
            raise RuntimeError("preflight not clean: %r" % {k: pf[k] for k in ("problems", "unresolved_prior", "token_residue", "enumeration_problems", "children")})
        with open(GA.consumed_marker(auth["authorization_id"]), "x") as f:      # single use: consumed BEFORE the fork, even if the run later fails
            json.dump({"authorization_id": auth["authorization_id"], "run_id": run_id, "consumed_utc": utc_now(), "bindings": ev["bindings_start"]}, f)
        ev["auth_consumed"] = True
        ev["snapshots"]["S0_before_fork"] = snapshot("S0_before_fork", obs_pid, tokens=True, exclude=exclude)
        budget.check("S0")
        reg_path = os.path.join(run_dir, "registry.jsonl")
        obs = O.Observer(reg_path)
        obs.trial_tag = "G0"
        obs.reg.write("RUN_START", run_id=run_id, prereg_sha256=prereg_sha(), observer_pid=obs_pid, phase="G0")
        guard.install()
        rec = obs.spawn_direct("sleeper", "g0", dict(SPEC), node.node_main, t_gate_max=lim["t_gate_max_s"], hold_release=True)
        if rec.state != "REGISTERED":
            raise RuntimeError("child not registered: state %s, problems %r" % (rec.state, obs.problems))
        ev["node"] = {"node_id": rec.node_id, "pid": rec.pid, "starttime": rec.starttime, "gate_ino": rec.gate_ino}
        hold_end = C.mono() + lim["hold_before_release_s"]
        while C.mono() < hold_end:
            budget.check("hold")
            obs.serve(min(0.05, hold_end - C.mono()))
        s1 = snapshot("S1_held_registered_unreleased", obs_pid, rec.pid, with_fds=True)
        s1["messages_received"] = int(rec.ready is not None) + int(rec.first_action_mono is not None) + len(rec.messages)
        s1["first_action_mono"] = rec.first_action_mono
        ev["snapshots"]["S1_held_registered_unreleased"] = s1
        if s1["messages_received"] or rec.state != "REGISTERED":
            raise RuntimeError("child acted or changed state while held (messages %d, state %s)" % (s1["messages_received"], rec.state))
        budget.check("release")
        guard.watch_fd = rec.gate_w
        try:
            obs.release(rec)                                               # writes RELEASED, then the release byte (recorded by the guard)
        finally:
            guard.watch_fd = None
        if not budget.wait(obs, lambda: rec.ready is not None, "ready", lim["ready_deadline_s"]):
            raise RuntimeError("READY not received within %.1f s (or the total budget)" % lim["ready_deadline_s"])
        ev["events"]["first_action_mono"] = rec.first_action_mono
        ev["snapshots"]["S2_ready_after_release"] = snapshot("S2_ready_after_release", obs_pid, rec.pid, with_fds=True)
        budget.check("exit")
        ev["events"]["exit_sent_mono"] = C.mono()
        proto.send_msg(rec.sock, {"t": "EXIT"})                       # a control-channel message, never a signal
        if not budget.wait(obs, lambda: rec.handle.exited(), "exit", lim["exit_deadline_s"]):
            raise RuntimeError("child did not exit within %.1f s after EXIT (or the total budget)" % lim["exit_deadline_s"])
        ev["events"]["pidfd_readable_mono"] = C.mono()
        ev["snapshots"]["S3_exited_unreaped"] = snapshot("S3_exited_unreaped", obs_pid, rec.pid)
        # F-8: bounded reap -- non-blocking waitpid polls of the ONE child pid; the guard allows nothing else and records every call
        reap_by = C.mono() + budget.cap(lim["reap_deadline_s"])
        while True:
            budget.check("reap")
            pid, status = os.waitpid(rec.pid, os.WNOHANG)
            if pid == rec.pid:
                break
            if C.mono() > reap_by:
                ev["deadline_hits"].append("reap")
                raise RuntimeError("child not reaped within %.1f s" % lim["reap_deadline_s"])
            time.sleep(0.01)
        ev["events"]["reap_mono"] = C.mono()
        rec.exit_status = os.waitstatus_to_exitcode(status)
        ev["reap"] = {"waitpid_pid": pid, "exit_status": rec.exit_status, "raw_status": status}
        gone_by = C.mono() + budget.cap(lim["reap_deadline_s"])
        while C.read_stat(rec.pid) is not None:
            budget.check("proc_gone")
            if C.mono() > gone_by:
                ev["deadline_hits"].append("proc_gone")
                raise RuntimeError("/proc/%d still present after reap" % rec.pid)
            time.sleep(0.01)
        ev["events"]["proc_gone_mono"] = C.mono()
        ev["snapshots"]["S4_reaped"] = snapshot("S4_reaped", obs_pid, rec.pid)
        budget.check("cleanup")
        cl = obs.final_cleanup(grace=max(0.1, min(3.0, budget.left() / 6.0)))   # child is exited AND reaped: kill_registered finds the pidfd readable -> 'already_exited'
        ev["cleanup"] = {"cleanup_ok": cl["cleanup_ok"], "run_set": cl["run_set"], "rounds": cl["rounds"], "residual_detail": cl["residual_detail"]}
        scan, scan_problems = token_scan(exclude)
        confirmed = bool(cl["cleanup_ok"]) and not scan and not scan_problems
        obs.reg.write("RUN_END", run_id=run_id, aborted=None, cleanup_confirmed=confirmed, residual=cl["residual_after_kill"],
                      token_residue=[x["pid"] for x in scan], token_scan_problems=sorted(scan_problems))
        budget.check("end")
    except BaseException:
        ev["exception"] = traceback.format_exc()
        if rec is not None and rec.pid is not None and rec.handle is not None and not rec.handle.exited():
            ident = {"pid": rec.pid, "starttime": rec.starttime, "node_id": rec.node_id, "verified_by": "REGISTERED record + pidfd",
                     "ends_by": "EXIT message / control EOF when this observer exits / gate or node timeout; NO signal was or will be sent by G0"}
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
                         "ends_by": "abort byte already written / gate EOF when this observer exits / gate timeout %.1f s; NO signal was or will be sent by G0" % lim["t_gate_max_s"]}
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
        if rec is not None:
            ev["events"]["first_action_mono"] = rec.first_action_mono
        try:
            ev["snapshots"]["S5_final"] = snapshot("S5_final", obs_pid, (rec.pid if rec is not None else None), tokens=True, exclude=exclude)
        except Exception:
            ev["exception"] = (ev["exception"] or "") + "\nS5: " + traceback.format_exc()
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
class Unsaved(Exception):
    def __init__(self, partial, reason, sha256=None):
        Exception.__init__(self, reason)
        self.partial, self.reason, self.sha256 = partial, reason, sha256


class Unverified(Exception):
    def __init__(self, reason, written=None, read=None):
        Exception.__init__(self, reason)
        self.reason, self.written, self.read = reason, written, read


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_exclusive(path, data):
    """P2 / K2: O_EXCL creation (an existing file is never overwritten or reused), write ALL bytes, fsync the file.  Raises Unsaved."""
    sha = GJ.sha256_hex(data)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except OSError as e:
        raise Unsaved(False, "create %s: %r" % (os.path.basename(path), e), sha)
    try:
        off = 0
        while off < len(data):
            n = os.write(fd, memoryview(data)[off:])
            if n <= 0:
                raise OSError(errno.EIO, "write returned %d" % n)
            off += n
        os.fsync(fd)
    except OSError as e:
        raise Unsaved(True, "write/fsync %s: %r" % (os.path.basename(path), e), sha)
    finally:
        os.close(fd)


def read_back(path):
    """P3 / K3 / K6: read the saved file again (best effort: ask the kernel to drop its cached pages first).  Raises Unverified."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as e:
        raise Unverified("open for read-back: %r" % (e,))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Unverified("not a regular file")
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        except (AttributeError, OSError):
            pass
        chunks = []
        while True:
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
        return b"".join(chunks)
    except OSError as e:
        raise Unverified("read-back: %r" % (e,))
    finally:
        os.close(fd)


def save_and_verify(path, data):
    """P2 + P3 (evidence) and P6 (summary): exclusive write + fsync + directory fsync, read back, require identical bytes and SHA-256, parse.
    -> (bytes read back, parsed object).  Raises Unsaved or Unverified."""
    write_exclusive(path, data)
    try:
        fsync_dir(os.path.dirname(path))
    except OSError as e:
        raise Unsaved(True, "directory fsync: %r" % (e,), GJ.sha256_hex(data))
    b2 = read_back(path)
    if len(b2) != len(data) or GJ.sha256_hex(b2) != GJ.sha256_hex(data):
        raise Unverified("bytes read back differ from the bytes written", GJ.sha256_hex(data), GJ.sha256_hex(b2))
    try:
        return b2, GJ.parse_strict(b2)
    except (ValueError, RecursionError) as e:
        raise Unverified("read-back does not parse as strict JSON: %r" % (e,), GJ.sha256_hex(data), GJ.sha256_hex(b2))


def _blocked_note(run_dir, run_id, info):
    """Best effort, exclusive: g0_blocked_<run_id>.json in the run directory, else in the evidence root.  Its own failure only adds a stderr line."""
    for d in (run_dir, GA.EVIDENCE_ROOT):
        try:
            write_exclusive_json(os.path.join(d, "g0_blocked_%s.json" % run_id), info)
            return
        except Exception as e:
            last = e
    stderr_marker("G0-BLOCKED-NOTE-UNSAVED", run_id=run_id, reason=repr(last))


def publish_closure(run_dir, run_id, criteria_sha256, b2, bs2, s2):
    """P7 = closure.publication K1..K7.  Never overwrites, never deletes the temporary name.  -> the process exit code: the recorded exit code when
    K1..K7 all succeeded, otherwise 3 with G0-CLOSE-UNPUBLISHED (nothing published) or G0-CLOSE-UNCONFIRMED (the link returned) on stderr."""
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
        marker = "G0-CLOSE-UNCONFIRMED" if published else "G0-CLOSE-UNPUBLISHED"
        stderr_marker(marker, run_id=run_id, step=step, verdict=verdict, evidence_sha256=GJ.sha256_hex(b2), summary_sha256=GJ.sha256_hex(bs2),
                      closed_sha256=closed_sha, reason="%s: %s" % (type(e).__name__, getattr(e, "reason", e)))
        return 3


def finalize(ev, run_id, run_dir, crit, crit_sha):
    """Pipeline P0..P7.  `ev` is the evidence constructed in memory (P0).  -> the process exit code."""
    pipe = {"P0": "constructed"}
    try:
        b = GJ.strict_bytes(ev)                                                                            # P1
    except (TypeError, ValueError, RecursionError) as e:
        stderr_marker("G0-EVIDENCE-UNSAVED", run_id=run_id, stage="P1", reason="%s: %s" % (type(e).__name__, e))
        return 3
    pipe["P1"] = {"sha256": GJ.sha256_hex(b), "bytes": len(b)}
    try:
        b2, e2 = save_and_verify(os.path.join(run_dir, EVIDENCE_NAME), b)                                  # P2 + P3
    except Unsaved as e:
        stderr_marker("G0-EVIDENCE-UNSAVED", run_id=run_id, stage="P2", sha256=e.sha256, partial=str(e.partial).lower(), reason=e.reason)
        _blocked_note(run_dir, run_id, {"run_id": run_id, "stage": "P2", "reason": e.reason, "sha256": e.sha256, "partial": e.partial})
        return 3
    except Unverified as e:
        stderr_marker("G0-EVIDENCE-UNVERIFIED", run_id=run_id, stage="P3", written_sha256=e.written, read_sha256=e.read, reason=e.reason)
        return 3
    pipe["P2"], pipe["P3"] = "saved", "read back and verified"
    invalid = GJ.validate_evidence(e2, crit)                                                               # P4: does not stop the pipeline
    pipe["P4"] = {"invalid_fields": len(invalid)}
    try:
        res = GJ.judge(e2, crit, crit_sha, validation=invalid)                                             # P5: ONLY the read-back evidence
    except BaseException as e:
        stderr_marker("G0-JUDGE-ERROR", run_id=run_id, reason="%s: %s" % (type(e).__name__, e))
        return 3
    pipe["P5"] = {"verdict": res["verdict"]}
    summary = {"run_id": run_id, "criteria_id": crit["criteria_id"], "criteria_sha256": crit_sha, "evidence_sha256": GJ.sha256_hex(b2), "verdict": res["verdict"],
               "exit_code": res["exit_code"], "checks": res["checks"], "c03_fidelity_report": res["c03_fidelity_report"], "fail_class": res["fail_class"],
               "blocked_class": res["blocked_class"], "pipeline": pipe, "scope": "G0 only; not evidence for G1/G2/G3, BV or E1-A"}
    if res["verdict"] == "FAIL":
        summary["fail_scope"] = GJ.FAIL_SCOPE
    try:
        bs = GJ.strict_bytes(summary)                                                                      # P6
        bs2, s2 = save_and_verify(os.path.join(run_dir, SUMMARY_NAME), bs)
    except (Unsaved, Unverified, TypeError, ValueError, RecursionError) as e:
        stderr_marker("G0-SUMMARY-UNSAVED", run_id=run_id, verdict=res["verdict"], evidence_sha256=GJ.sha256_hex(b2), reason="%s: %s" % (type(e).__name__, getattr(e, "reason", e)))
        return 3
    return publish_closure(run_dir, run_id, crit_sha, b2, bs2, s2)                                         # P7


def main(argv=None):
    """Entry point.  ANY exception that escapes the start-up or the run is mapped to exit code 3 (BLOCKED) with a marker on stderr -- never to Python's
    default exit code 1, which is the FAIL code.  Usage errors (argparse) keep their SystemExit(2); a refusal is 2."""
    try:
        return _main(argv)
    except SystemExit:
        raise
    except BaseException as e:
        stderr_marker("G0-STARTUP-ERROR", reason="%s: %s" % (type(e).__name__, e))
        return 3


def _main(argv=None):
    ap = argparse.ArgumentParser(description="G0 minimal process-gate test.  --execute needs a valid single-use G0 authorization.")
    ap.add_argument("--check", action="store_true", help="print bindings and authorization status; starts no process")
    ap.add_argument("--template", action="store_true", help="print a NON-VALID authorization template")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--auth", default=GA.AUTH_DEFAULT)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)
    if args.template:
        print(GA.template())
        return 0
    cur = current()
    if args.check or not args.execute:
        info = {"stage": "G0", "criteria_id": GA.CRITERIA_ID, "bindings": cur, "frozen_file_problems": GA.frozen_problems(), "authorization_file": args.auth,
                "authorization_present": os.path.exists(args.auth), "executed": False}
        if os.path.exists(args.auth):
            try:
                GA.load(args.auth, cur, utc_now())
                info["authorization_valid"] = True
            except GA.G0AuthorizationError as e:
                info["authorization_valid"] = False
                info["authorization_problem"] = str(e)
        print(json.dumps(info, indent=1))
        return 0
    fp = GA.frozen_problems()
    if fp:
        print("REFUSED: frozen files differ: %s" % "; ".join(fp), file=sys.stderr)
        return 2
    try:
        auth, raw = GA.load(args.auth, cur, utc_now())
    except GA.G0AuthorizationError as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    run_id = args.run_id or ("g0_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + "_" + os.urandom(3).hex())
    if not GA.ID_RE.match(run_id) or not run_id.startswith("g0_"):
        print("REFUSED: run id %r" % run_id, file=sys.stderr)
        return 2
    run_dir = os.path.join(GA.EVIDENCE_ROOT, run_id)
    if os.path.exists(run_dir):
        print("REFUSED: run directory exists", file=sys.stderr)
        return 2
    crit = GJ.load_criteria()
    crit_sha = C.sha256_file(GA.CRITERIA_PATH)
    pf = safe_preflight(run_dir, ancestors(os.getpid()))                  # read-only; BEFORE any directory is created
    try:
        dirs = prepare_dirs(run_dir)
    except DirError as e:
        stderr_marker("G0-DIR-ERROR", run_id=run_id, reason=e)
        return 3
    try:
        ev = run(auth, raw, run_id, run_dir, pf, dirs)
    except BaseException:
        stderr_marker("G0-RUN-ERROR", run_id=run_id, reason=traceback.format_exc().strip().splitlines()[-1])
        return 3
    try:
        rc = finalize(ev, run_id, run_dir, crit, crit_sha)
    except BaseException as e:
        stderr_marker("G0-PIPELINE-ERROR", run_id=run_id, reason="%s: %s" % (type(e).__name__, e))
        return 3
    print(json.dumps({"run_id": run_id, "exit_code": rc}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
