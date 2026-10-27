#!/usr/bin/env python3
"""F3B-D1-A-CPU-001 -- isolated three-arm CPU comparison for the R3 alive-target predicate A.

Arms:  B0 (frozen-R3 literal A, three permitted readings), CA (scheme A: targeted waitpid first, then evaluate),
       CB (scheme B: waitid(P_PID, WNOWAIT) non-consuming observation, reaping deferred to T5).
CA and CB share one common part (fingerprint registry, lineage discovery, /proc scan with error classification,
tri-state ALIVE/EXITED/UNKNOWN, pidfd-based signalling, SIGKILL pre-recheck); they differ only in how a direct child
is observed and when it is reaped.

The test bench (Lab / Oracle) builds every process itself, so the topology is KNOWN from the nodes' own reports, and
the real state of every process comes from two independent sources (pidfd readability + /proc, plus waitid(WNOWAIT)
for children) -- never from the arm under test.  Nothing here touches the frozen R3 spec or any production supervisor.
Linux only, standard library only, no network, no GPU.
"""
import ctypes
import errno
import json
import os
import platform
import random
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NODE = os.path.join(HERE, "a_node.py")
TOKEN = "ALAB-" + uuid.uuid4().hex[:12]
ALIVE, EXITED, UNKNOWN = "ALIVE", "EXITED", "UNKNOWN"
RUNNING, ZOMBIE, GONE = "RUNNING", "ZOMBIE", "GONE"
PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"
READINGS = ("NOREAP", "EVAL_THEN_REAP", "REAP_THEN_EVAL")


def now():
    return time.monotonic()


class SafetyError(RuntimeError):
    pass


class Blocked(RuntimeError):
    """The test bench could not establish the case's precondition: result is BLOCKED, not a rule verdict."""


class Vanished(Exception):
    pass


class Unreadable(Exception):
    pass


class ScanFailed(Exception):
    pass


# ---------------------------------------------------------------- prctl (stdlib ctypes)
_libc = ctypes.CDLL(None, use_errno=True)
PR_SET_CHILD_SUBREAPER, PR_GET_CHILD_SUBREAPER = 36, 37


def prctl_set_subreaper(flag):
    r = _libc.prctl(PR_SET_CHILD_SUBREAPER, int(flag), 0, 0, 0)
    return r == 0


def prctl_get_subreaper():
    v = ctypes.c_int(-1)
    r = _libc.prctl(PR_GET_CHILD_SUBREAPER, ctypes.byref(v), 0, 0, 0)
    return v.value if r == 0 else None


# ---------------------------------------------------------------- /proc access used by the ARMS (fault-injectable)
def parse_stat(data):
    i = data.rindex(")")
    rest = data[i + 2:].split()
    return {"state": rest[0], "ppid": int(rest[1]), "pgrp": int(rest[2]), "sid": int(rest[3]),
            "starttime": int(rest[19]), "comm": data[data.index("(") + 1:i]}


class ProcFS:
    def listdir(self):
        return [int(d) for d in os.listdir("/proc") if d.isdigit()]

    def stat(self, pid):
        try:
            with open("/proc/%d/stat" % pid, "rb") as f:
                data = f.read().decode("ascii", "replace")
        except (FileNotFoundError, ProcessLookupError):
            raise Vanished(pid)
        except OSError as e:
            raise Unreadable("errno %s" % e.errno)
        try:
            return parse_stat(data)
        except (ValueError, IndexError):
            raise Unreadable("parse")

    def scan(self):
        try:
            pids = self.listdir()
        except OSError as e:
            raise ScanFailed("listdir errno %s" % e.errno)
        table, problems = {}, {}
        for pid in pids:
            try:
                table[pid] = self.stat(pid)
            except Vanished:
                continue
            except Unreadable as e:
                problems[pid] = str(e)
        return table, problems


class FaultyProcFS(ProcFS):
    """Controlled fault injection (SIMULATED /proc failures -- not real kernel faults)."""

    def __init__(self, listdir_errno=None, stat_faults=None):
        self.listdir_errno = listdir_errno
        self.stat_faults = stat_faults or {}      # pid -> "EACCES" | "EIO" | "garble"

    def listdir(self):
        if self.listdir_errno:
            raise OSError(self.listdir_errno, "injected")
        return super().listdir()

    def stat(self, pid):
        f = self.stat_faults.get(pid)
        if f in ("EACCES", "EIO"):
            raise Unreadable("errno %s (injected)" % f)
        if f == "garble":
            try:
                parse_stat("garbage-without-fields")
            except (ValueError, IndexError):
                raise Unreadable("parse (injected)")
        return super().stat(pid)


# ---------------------------------------------------------------- the independent oracle (test bench only)
def _oracle_stat(pid):
    try:
        with open("/proc/%d/stat" % pid, "rb") as f:
            data = f.read().decode("ascii", "replace")
    except (FileNotFoundError, ProcessLookupError):
        return None
    rest = data[data.rindex(")") + 2:].split()
    return {"state": rest[0], "ppid": int(rest[1]), "pgrp": int(rest[2]), "sid": int(rest[3]), "starttime": int(rest[19])}


def _pidfd_exited(fd):
    r, _, _ = select.select([fd], [], [], 0)
    return bool(r)


def oracle_state(node, timeout=2.0):
    """True state of a node the test bench created: RUNNING / ZOMBIE / GONE (+ evidence).  Two independent sources must
    agree: (pidfd readable) x (/proc state), and for children of this process also waitid(WNOWAIT)."""
    me = os.getpid()
    end = now() + timeout
    last = None
    while True:
        st = _oracle_stat(node["pid"])
        present = st is not None and st["starttime"] == node["starttime"]
        exited_fd = _pidfd_exited(node["pidfd"])
        wid = None
        if present and st["ppid"] == me:
            try:
                r = os.waitid(os.P_PID, node["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT)
                wid = "NOCHANGE" if r is None else ("EXITED", r.si_code, r.si_status)
            except ChildProcessError:
                wid = "NOCHILD"
        last = {"proc_state": st["state"] if present else None, "pidfd_exited": exited_fd, "waitid": wid,
                "ppid": st["ppid"] if present else None, "sid": st["sid"] if present else None}
        if not present and exited_fd:
            return GONE, last
        if present and st["state"] in ("Z", "X") and exited_fd and (wid is None or isinstance(wid, tuple)):
            return ZOMBIE, last
        if present and st["state"] not in ("Z", "X") and not exited_fd and wid in (None, "NOCHANGE"):
            return RUNNING, last
        if now() > end:
            return "ORACLE_DISAGREE", last
        time.sleep(0.003)


def decode_status(raw):
    code = os.waitstatus_to_exitcode(raw)
    return {"kind": "exit", "code": code} if code >= 0 else {"kind": "signal", "sig": -code}


def decode_siginfo(si_code, si_status):
    if si_code == os.CLD_EXITED:
        return {"kind": "exit", "code": si_status}
    return {"kind": "signal", "sig": si_status}


# ---------------------------------------------------------------- arms
class Target:
    def __init__(self, pid, st, how, direct=False):
        self.pid, self.starttime, self.sid, self.pgrp, self.how = pid, st["starttime"], st["sid"], st["pgrp"], how
        self.direct = direct
        self.was_child = st["ppid"] == os.getpid()
        self.reaped = False
        self.exit = None              # CA: recorded when waitpid consumes the status
        self.observed = None          # CB: waitid(WNOWAIT) observation
        self.t5_exit = None           # CB: status returned by the T5 waitpid
        self.state, self.reason = ALIVE, None
        self.notes = []

    def matches(self, st):
        return st is not None and st["starttime"] == self.starttime

    def brief(self):
        return {"pid": self.pid, "state": self.state, "reason": self.reason, "how": self.how, "reaped": self.reaped}


class ArmBase:
    name = "?"
    baseline = False

    def __init__(self, lab):
        self.lab = lab
        self.me = os.getpid()
        self.fs = ProcFS()
        self.signal_log = []
        self.reap_log = []
        self.wait_calls = []          # every waitpid/waitid the arm issued, with the independent oracle's view of the target's ppid
        self.polls = 0

    def _log_wait(self, kind, pid):
        st = _oracle_stat(pid)
        self.wait_calls.append({"kind": kind, "pid": pid, "oracle_ppid": st["ppid"] if st else None, "poll_index": self.polls})

    def hook(self, name, **kw):
        h = self.lab.hooks.get(name)
        if h:
            h(**kw)


class ArmCommon(ArmBase):
    """Common part of CA and CB (proposal section 3): identity registry, lineage discovery, tri-state, pidfd signalling."""

    def __init__(self, lab):
        super().__init__(lab)
        self.targets = {}
        self.aux = {}
        self.stage_sid = None
        self.cw_declared = True
        self.subreaper_ok = False
        self.get_subreaper = prctl_get_subreaper
        self.unattrib = set()
        self.preflight_result = None
        self.waitpid_fn = os.waitpid
        self.waitid_fn = os.waitid
        self.pidfd_open = os.pidfd_open
        self.last_obs = None

    # -- S0
    def preflight(self, setter=prctl_set_subreaper):
        ok_set = setter(True)
        v = self.get_subreaper()
        self.subreaper_ok = bool(ok_set) and v == 1
        self.preflight_result = {"set_ok": bool(ok_set), "get_value": v,
                                 "status": "OK" if self.subreaper_ok else "BLOCKED", "code": None if self.subreaper_ok else "PREFLIGHT_FAILED"}
        return self.preflight_result

    # -- registration
    def register_root(self, node):
        st = self.fs.stat(node["pid"])
        fp = (st["starttime"], st["sid"], st["pgrp"])
        if fp != (node["starttime"], node["sid"], node["pgrp"]):
            raise Blocked("root fingerprint %s differs from the node's own report" % (fp,))
        tg = Target(node["pid"], st, "root", direct=True)
        self.targets[node["pid"]] = tg
        self.stage_sid = st["sid"]
        return tg

    def register_aux(self, node):
        self.aux[node["pid"]] = node["starttime"]

    # -- discovery (proposal 3.2: lineage closure, continuous registration, closed-world orphans, sid only as a hint)
    def _cw_ok(self):
        return self.cw_declared and not self.aux

    def _discover(self, table):
        self.unattrib = set()
        changed = True
        while changed:
            changed = False
            for pid, st in list(table.items()):
                if pid in self.targets or pid == self.me:
                    continue
                if pid in self.aux and self.aux[pid] == st["starttime"]:
                    continue
                par = self.targets.get(st["ppid"])
                how = None
                if par is not None and par.matches(table.get(st["ppid"])):
                    how = "lineage"
                elif st["sid"] == self.stage_sid:
                    how = "sid_hint"
                elif st["ppid"] == self.me:
                    if self._cw_ok():
                        how = "closed_world_orphan"
                    else:
                        self.unattrib.add(pid)
                if how:
                    self.targets[pid] = Target(pid, st, how)
                    changed = True

    # -- evaluation of one target (shared; direct-child observation differs per arm)
    def _eval(self, tg, table, problems):
        if tg.reaped:
            tg.state, tg.reason = EXITED, "reaped_by_arm"
            return
        if tg.pid in problems:
            tg.state, tg.reason = UNKNOWN, "UNKNOWN_TARGET_UNREADABLE"
            return
        st = table.get(tg.pid)
        if st is None:
            if tg.was_child:
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_OBSERVATION_CONFLICT:unreaped_child_absent_from_proc"
            else:
                tg.state, tg.reason = EXITED, "vanished_after_verified_fingerprint"
            return
        if st["starttime"] != tg.starttime:
            tg.state, tg.reason = UNKNOWN, "UNKNOWN_IDENTITY_UNVERIFIED"
            return
        if (st["sid"], st["pgrp"]) != (tg.sid, tg.pgrp):
            tg.notes.append("sid/pgrp changed %s->%s" % ((tg.sid, tg.pgrp), (st["sid"], st["pgrp"])))
            tg.sid, tg.pgrp = st["sid"], st["pgrp"]
        if st["ppid"] == self.me:
            tg.was_child = True
            self._observe_child(tg, st)
        else:
            if st["state"] in ("Z", "X"):
                tg.state, tg.reason = EXITED, "proc_state_%s" % st["state"]
            else:
                tg.state, tg.reason = ALIVE, "proc_state_%s" % st["state"]

    def _pass(self):
        try:
            table, problems = self.fs.scan()
        except ScanFailed as e:
            return {"scan_failed": str(e)}
        self._discover(table)
        for tg in list(self.targets.values()):
            self._eval(tg, table, problems)
        stray = sorted(p for p in problems if p not in self.targets)
        return {"table_n": len(table), "problems": problems, "stray_unreadable": stray, "target_pids": sorted(self.targets)}

    def poll(self):
        self.polls += 1
        p1 = self._pass()
        if "scan_failed" in p1:
            for tg in self.targets.values():
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_PROC_UNREADABLE"
            return self._finish(UNKNOWN, ["UNKNOWN_PROC_UNREADABLE"], p1)
        p2 = self._pass()
        if "scan_failed" in p2:
            for tg in self.targets.values():
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_PROC_UNREADABLE"
            return self._finish(UNKNOWN, ["UNKNOWN_PROC_UNREADABLE"], p2)
        reasons = []
        if p1["target_pids"] != p2["target_pids"]:
            reasons.append("UNKNOWN_DISCOVERY_INCOMPLETE:target_set_changed_between_scans")
        if p2["stray_unreadable"]:
            reasons.append("UNKNOWN_DISCOVERY_INCOMPLETE:unreadable_unregistered_pids")
        if not self.subreaper_ok:
            reasons.append("UNKNOWN_DISCOVERY_INCOMPLETE:subreaper_unverified")
        if self.unattrib:
            reasons.append("UNKNOWN_DISCOVERY_INCOMPLETE:unattributable_children_of_supervisor")
        tgs = list(self.targets.values())
        for tg in tgs:
            if tg.state == UNKNOWN:
                reasons.append(tg.reason)
        if any(tg.state == ALIVE for tg in tgs):
            tri = ALIVE
        elif any(tg.state == UNKNOWN for tg in tgs) or reasons:
            tri = UNKNOWN
        else:
            tri = EXITED
        return self._finish(tri, reasons, p2)

    def _finish(self, tri, reasons, p):
        obs = {"tri": tri, "A": {ALIVE: True, EXITED: False, UNKNOWN: None}[tri], "reasons": reasons,
               "targets": {str(pid): tg.brief() for pid, tg in self.targets.items()}}
        self.last_obs = obs
        return obs

    # -- signalling (pidfd first, then fingerprint check, then send; proposal 3.3)
    def signal_target(self, tg, sig):
        rec = {"pid": tg.pid, "starttime": tg.starttime, "sig": int(sig), "result": None}
        self.signal_log.append(rec)
        if tg.state != ALIVE:
            rec["result"] = "refused_not_alive"
            return rec
        try:
            fd = self.pidfd_open(tg.pid)
        except OSError as e:
            if e.errno == errno.ESRCH:          # the process no longer exists: gone, not a capability problem
                rec.update(result="gone_before_signal", errno=e.errno)
                return rec
            tg.state, tg.reason = UNKNOWN, "UNKNOWN_PIDFD_UNAVAILABLE"
            rec.update(result="refused_pidfd_unavailable", errno=e.errno)
            return rec
        try:
            try:
                st = self.fs.stat(tg.pid)
            except Vanished:
                rec["result"] = "gone_before_signal"
                return rec
            except Unreadable:
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_TARGET_UNREADABLE"
                rec["result"] = "refused_unreadable"
                return rec
            if st["starttime"] != tg.starttime:
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_IDENTITY_UNVERIFIED"
                rec["result"] = "refused_identity_mismatch"
                return rec
            if st["state"] in ("Z", "X"):
                rec["result"] = "skipped_already_exited"
                return rec
            self.hook("after_fingerprint_before_signal", tg=tg)
            try:
                signal.pidfd_send_signal(fd, sig)
                rec["result"] = "sent"
            except ProcessLookupError:
                rec["result"] = "gone"
            except OSError as e:
                rec.update(result="error", errno=e.errno)
        finally:
            os.close(fd)
        return rec

    def signal_alive(self, sig):
        return [self.signal_target(tg, sig) for tg in list(self.targets.values()) if tg.state == ALIVE]

    # -- bookkeeping shared by T5
    def residual(self):
        out = []
        for tg in self.targets.values():
            try:
                st = self.fs.stat(tg.pid)
            except (Vanished, Unreadable):
                continue
            if st["starttime"] == tg.starttime:
                out.append({"pid": tg.pid, "proc_state": st["state"], "ppid": st["ppid"]})
        return out

    def exit_status(self, pid):
        raise NotImplementedError


class ArmCA(ArmCommon):
    """Scheme A: targeted waitpid(pid, WNOHANG) first -- the exit status is saved at the moment it is consumed."""
    name = "CA"

    def _observe_child(self, tg, st):
        for attempt in range(3):
            self._log_wait("waitpid", tg.pid)
            try:
                r = self.waitpid_fn(tg.pid, os.WNOHANG)
            except ChildProcessError:
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_OBSERVATION_CONFLICT:ECHILD_on_unreaped_child"
                return
            if r[0] == tg.pid:
                tg.reaped = True
                tg.exit = decode_status(r[1])
                tg.exit["raw"] = r[1]
                self.reap_log.append({"pid": tg.pid, "status": tg.exit, "phase": "poll"})
                tg.state, tg.reason = EXITED, "reaped_by_arm"
                return
            if st["state"] not in ("Z", "X"):
                tg.state, tg.reason = ALIVE, "waitpid_returned_0"
                return
            time.sleep(0.002)
            try:
                st = self.fs.stat(tg.pid)
            except (Vanished, Unreadable):
                break
        tg.state, tg.reason = UNKNOWN, "UNKNOWN_OBSERVATION_CONFLICT:waitpid_0_but_proc_zombie"

    def t5_reap(self):
        recs = []
        for tg in self.targets.values():
            if tg.reaped or tg.state != EXITED:
                continue
            try:
                st = self.fs.stat(tg.pid)
            except (Vanished, Unreadable):
                continue
            if st["starttime"] == tg.starttime and st["ppid"] == self.me and st["state"] in ("Z", "X"):
                self._log_wait("waitpid_T5", tg.pid)
                try:
                    r = self.waitpid_fn(tg.pid, os.WNOHANG)
                except ChildProcessError:
                    continue
                if r[0] == tg.pid:
                    tg.reaped = True
                    tg.exit = decode_status(r[1])
                    recs.append({"pid": tg.pid, "status": tg.exit, "phase": "T5"})
        self.reap_log += recs
        return {"reaped": recs, "residual": self.residual()}

    def exit_status(self, pid):
        tg = self.targets.get(pid)
        return tg.exit if tg else None


class ArmCB(ArmCommon):
    """Scheme B: waitid(P_PID, ..., WNOWAIT) observation only; reaping is deferred to T5 and done per verified pid."""
    name = "CB"

    def _observe_child(self, tg, st):
        for attempt in range(3):
            self._log_wait("waitid", tg.pid)
            try:
                r = self.waitid_fn(os.P_PID, tg.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            except ChildProcessError:
                tg.state, tg.reason = UNKNOWN, "UNKNOWN_OBSERVATION_CONFLICT:ECHILD_on_unreaped_child"
                return
            if r is not None:
                if tg.observed is None:
                    tg.observed = decode_siginfo(r.si_code, r.si_status)
                tg.state, tg.reason = EXITED, "waitid_exited_not_consumed"
                return
            if st["state"] not in ("Z", "X"):
                tg.state, tg.reason = ALIVE, "waitid_nochange"
                return
            time.sleep(0.002)
            try:
                st = self.fs.stat(tg.pid)
            except (Vanished, Unreadable):
                break
        tg.state, tg.reason = UNKNOWN, "UNKNOWN_OBSERVATION_CONFLICT:waitid_nochange_but_proc_zombie"

    def t5_reap(self):
        recs = []
        for tg in self.targets.values():
            if tg.reaped or tg.state != EXITED or tg.observed is None:
                continue
            try:
                st = self.fs.stat(tg.pid)
            except (Vanished, Unreadable):
                continue
            if st["starttime"] == tg.starttime and st["ppid"] == self.me and st["state"] in ("Z", "X"):
                self._log_wait("waitpid_T5", tg.pid)
                try:
                    r = os.waitpid(tg.pid, os.WNOHANG)       # per-pid, identity re-verified just above
                except ChildProcessError:
                    continue
                if r[0] == tg.pid:
                    tg.reaped = True
                    tg.t5_exit = decode_status(r[1])
                    recs.append({"pid": tg.pid, "status": tg.t5_exit, "phase": "T5"})
        self.reap_log += recs
        return {"reaped": recs, "residual": self.residual()}

    def exit_status(self, pid):
        tg = self.targets.get(pid)
        return (tg.t5_exit or tg.observed) if tg else None


class ArmB0(ArmBase):
    """Frozen-R3 literal predicate: A = (1) direct child not yet reaped OR (2) killpg(pgid,0) succeeds OR
    (3) a re-parented descendant (an unregistered process whose ppid is this supervisor) exists.
    Three readings of the evaluation order relative to waitpid(WNOHANG); T5 reaps with waitpid(-1, WNOHANG).
    Signalling follows R3: killpg of the recorded process group (the lab only refuses groups it did not create)."""
    baseline = True

    def __init__(self, lab, reading):
        super().__init__(lab)
        assert reading in READINGS
        self.reading = reading
        self.name = "B0-" + reading
        self.pid = None
        self.pgid = None
        self.reaped = False
        self.exit = None
        self.reap_statuses = {}
        self.last_A = None

    def preflight(self, setter=None):
        # the frozen R3 has no subreaper rule; the lab keeps the flag on so that re-parented descendants can exist at all
        return {"status": "N/A", "note": "no S0 subreaper precondition in frozen R3"}

    def register_root(self, node):
        self.pid, self.pgid = node["pid"], node["pgrp"]

    def register_aux(self, node):
        pass

    def _reap_root(self):
        if self.reaped:
            return
        try:
            r = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            self.reaped = True
            return
        if r[0] == self.pid:
            self.reaped = True
            self.exit = decode_status(r[1])

    def _killpg0(self):
        try:
            os.killpg(self.pgid, 0)
            return "success"
        except ProcessLookupError:
            return "ESRCH"
        except PermissionError:
            return "EPERM"

    def _A(self):
        c1 = not self.reaped
        c2 = self._killpg0() == "success"
        c3 = False
        try:
            table, _ = self.fs.scan()
            c3 = any(st["ppid"] == self.me and pid != self.pid for pid, st in table.items())
        except ScanFailed:
            c3 = False            # the literal predicate has no way to express "cannot scan"
        return c1 or c2 or c3, {"c1": c1, "c2": c2, "c3": c3}

    def poll(self):
        self.polls += 1
        if self.reading == "NOREAP":
            a, comp = self._A()
        elif self.reading == "EVAL_THEN_REAP":
            a, comp = self._A()
            self._reap_root()
        else:
            self._reap_root()
            a, comp = self._A()
        self.last_A = a
        tri = ALIVE if a else EXITED
        return {"tri": tri, "A": a, "reasons": [], "components": comp, "targets": {}}

    def signal_alive(self, sig):
        recs = []
        if sig == signal.SIGKILL and not self.last_A:
            return recs                     # escalation only while A is true; the stage's SIGTERM (R3 T2) is unconditional
        rec = {"pgid": self.pgid, "sig": int(sig), "result": None}
        self.signal_log.append(rec)
        if self.pgid not in self.lab.allowed_pgids:
            raise SafetyError("lab refuses to signal pgid %s (not created by the lab)" % self.pgid)
        self.hook("after_fingerprint_before_signal", tg=None)
        try:
            os.killpg(self.pgid, sig)
            rec["result"] = "sent"
        except ProcessLookupError:
            rec["result"] = "gone"
        except OSError as e:
            rec.update(result="error", errno=e.errno)
        recs.append(rec)
        return recs

    def t5_reap(self):
        recs = []
        while True:
            try:
                r = os.waitpid(-1, os.WNOHANG)      # R3 T5 as written (the proposal flags this as unsafe)
            except ChildProcessError:
                break
            if r[0] == 0:
                break
            st = decode_status(r[1])
            self.reap_statuses[r[0]] = st
            if r[0] == self.pid:
                self.reaped, self.exit = True, st
            recs.append({"pid": r[0], "status": st, "phase": "T5"})
        self.reap_log += recs
        return {"reaped": recs, "residual": []}

    def residual(self):
        return []

    def exit_status(self, pid):
        if pid == self.pid and self.exit:
            return self.exit
        return self.reap_statuses.get(pid)


ARMS = {
    "B0-NOREAP": lambda lab: ArmB0(lab, "NOREAP"),
    "B0-EVAL_THEN_REAP": lambda lab: ArmB0(lab, "EVAL_THEN_REAP"),
    "B0-REAP_THEN_EVAL": lambda lab: ArmB0(lab, "REAP_THEN_EVAL"),
    "CA": lambda lab: ArmCA(lab),
    "CB": lambda lab: ArmCB(lab),
}


# ---------------------------------------------------------------- the lab
def collect_names(spec):
    out = [spec["name"]]
    for c in spec.get("children", []):
        out += collect_names(c)
    return out


class Checker:
    def __init__(self):
        self.checks = []

    def add(self, name, ok, expected=None, actual=None):
        self.checks.append({"name": name, "ok": bool(ok), "expected": expected, "actual": actual})
        return bool(ok)

    def eq(self, name, actual, expected):
        return self.add(name, actual == expected, expected, actual)

    def failed(self):
        return [c for c in self.checks if not c["ok"]]


class Lab:
    def __init__(self):
        self.workdir = tempfile.mkdtemp(prefix="alab-")
        self.ctl = None
        self.nodes = []
        self.hooks = {}
        self.allowed_pgids = set()
        self.sentinel = None
        self.me = os.getpid()
        self.subreaper_log = []

    # -- environment
    def set_subreaper(self, flag):
        ok = prctl_set_subreaper(flag)
        self.subreaper_log.append({"set": bool(flag), "ok": ok, "get": prctl_get_subreaper()})
        return ok

    def begin(self):
        self.ctl = tempfile.mkdtemp(prefix="ctl-", dir=self.workdir)
        self.nodes = []
        self.hooks = {}
        self.allowed_pgids = set()

    # -- spawning
    def spawn(self, spec, as_child=True):
        names = collect_names(spec)
        r, w = os.pipe()
        os.set_inheritable(w, True)
        pid = os.fork()
        if pid == 0:
            try:
                os.close(r)
                os.setsid()
                os.execv(sys.executable, [sys.executable, "-S", NODE, TOKEN, json.dumps(spec), str(w), self.ctl])
            finally:
                os._exit(127)
        os.close(w)
        reports, buf = [], b""
        end = now() + 10
        while len(reports) < len(names) and now() < end:
            rl, _, _ = select.select([r], [], [], 0.2)
            if rl:
                chunk = os.read(r, 4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    reports.append(json.loads(line))
        os.close(r)
        if len(reports) != len(names):
            raise Blocked("node reports incomplete: got %d of %d (%s)" % (len(reports), len(names), names))
        out = {}
        for rep in reports:
            rep["pidfd"] = os.pidfd_open(rep["pid"])
            st = _oracle_stat(rep["pid"])
            if st is None or st["starttime"] != rep["starttime"]:
                raise Blocked("node %s: /proc fingerprint differs from self report" % rep["name"])
            rep["is_root_of_spawn"] = rep["pid"] == pid
            out[rep["name"]] = rep
            self.nodes.append(rep)
            if rep["pid"] != self.sentinel_pid():
                self.allowed_pgids.add(rep["pgrp"])
        return out

    def sentinel_pid(self):
        return self.sentinel["pid"] if self.sentinel else None

    def spawn_detached(self, name, term="ignore"):
        """A running process that is NOT a child of this supervisor (double-spawned with the subreaper flag off, so it is
        adopted by a process outside this one).  Used for the bystander sentinel and for bystanders in the reuse tests."""
        was = prctl_get_subreaper()
        self.set_subreaper(False)
        try:
            nodes = self.spawn({"name": "H_" + name, "children": [{"name": name, "setsid": True, "term": term}]})
            self.go("H_" + name, "exit", 0)
            self.wait_state(nodes["H_" + name], ZOMBIE)
            os.waitpid(nodes["H_" + name]["pid"], 0)
        finally:
            self.set_subreaper(bool(was))
        node = nodes[name]
        if node["pgrp"] in self.allowed_pgids and self.sentinel_pid() == node["pid"]:
            self.allowed_pgids.discard(node["pgrp"])
        return node

    def start_sentinel(self):
        self.begin()
        self.sentinel = None
        node = self.spawn_detached("SENTINEL")
        self.sentinel = node
        self.allowed_pgids.discard(node["pgrp"])
        st, ev = oracle_state(node)
        if st != RUNNING or ev.get("ppid") == self.me:
            raise Blocked("sentinel not running as a non-child: %s %s" % (st, ev))
        return node

    def sentinel_ok(self):
        st, ev = oracle_state(self.sentinel, timeout=1.0)
        return st == RUNNING

    # -- control
    def go(self, name, action, code=0):
        path = os.path.join(self.ctl, "go.%s.%s" % (name, action))
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(str(code))
        os.rename(tmp, path)

    def wait_state(self, node, want, timeout=5.0):
        end = now() + timeout
        last = None
        while now() < end:
            st, ev = oracle_state(node, timeout=0.5)
            last = (st, ev)
            if st == want:
                return ev
            time.sleep(0.003)
        raise Blocked("node %s did not reach %s (last %s)" % (node["name"], want, last))

    def node(self, name):
        for n in self.nodes:
            if n["name"] == name:
                return n
        raise KeyError(name)

    def truths(self, names):
        out = {}
        for n in names:
            st, ev = oracle_state(self.node(n))
            if st == "ORACLE_DISAGREE":
                raise Blocked("oracle disagreement on %s: %s" % (n, ev))
            out[n] = st
        return out

    def kill_by_bench(self, node, sig=signal.SIGKILL):
        """Test-bench action (NOT an arm action): kill a node through the pidfd the bench opened."""
        signal.pidfd_send_signal(node["pidfd"], sig)

    def killpg0(self, pgid):
        try:
            os.killpg(pgid, 0)
            return "success"
        except ProcessLookupError:
            return "ESRCH"
        except PermissionError:
            return "EPERM"

    def hook(self, name, **kw):
        h = self.hooks.get(name)
        if h:
            h(**kw)

    # -- the simulated T3/T4/T5 controller (probe-local timing; NOT the approved G_term)
    def run_t3(self, arm, names, send_term, grace, poll_dt=0.03, pre_polls=0, kill_wait=3.0, expect_first=None):
        tr = {"polls": [], "decision": None, "signals": [], "first_tri": None, "escalation": None, "post": []}
        for _ in range(pre_polls):
            arm.poll()
        if send_term:
            p0 = arm.poll()                # fresh observation before the stage's SIGTERM (signals only go to verified ALIVE targets)
            tr["pre_term_poll"] = {"tri": p0["tri"], "reasons": p0["reasons"]}
        t0 = now()
        if send_term:
            for rec in arm.signal_alive(signal.SIGTERM):
                rec = dict(rec)
                rec["stage"] = "SIGTERM"
                tr["signals"].append(rec)
        while True:
            tp = self.truths(names)
            obs = arm.poll()
            tq = self.truths(names)
            tr["polls"].append({"t": round(now() - t0, 3), "truth_pre": tp, "truth_post": tq, "tri": obs["tri"], "A": obs["A"],
                                "reasons": obs["reasons"], "targets": obs.get("targets")})
            if tr["first_tri"] is None:
                tr["first_tri"] = obs["tri"]
            if obs["tri"] == EXITED:
                tr["decision"] = "EARLY_CONFIRM"
                break
            if obs["tri"] == UNKNOWN:
                tr["decision"] = "BLOCKED_UNKNOWN"
                break
            if now() - t0 >= grace:
                tp2 = self.truths(names)
                o2 = arm.poll()                    # SIGKILL pre-recheck
                tq2 = self.truths(names)
                tr["recheck"] = {"truth_pre": tp2, "truth_post": tq2, "tri": o2["tri"], "reasons": o2["reasons"]}
                if o2["tri"] == EXITED:
                    tr["decision"] = "CANCELLED_ESCALATION"
                    break
                if o2["tri"] == UNKNOWN:
                    tr["decision"] = "BLOCKED_UNKNOWN"
                    break
                self.hook("after_recheck_before_signal")
                sigs = arm.signal_alive(signal.SIGKILL)
                for rec in sigs:
                    rec = dict(rec)
                    rec["stage"] = "SIGKILL"
                    tr["signals"].append(rec)
                tr["decision"] = "ESCALATED"
                tr["escalation"] = {"truth_pre_recheck": tp2, "truth_post_recheck": tq2}
                tr["false_escalation"] = all(v != RUNNING for v in tp2.values()) and all(v != RUNNING for v in tq2.values())
                break
            time.sleep(poll_dt)
        if tr["decision"] == "ESCALATED":
            end = now() + kill_wait
            while now() < end:
                o = arm.poll()
                tr["post"].append({"tri": o["tri"], "reasons": o["reasons"]})
                if o["tri"] in (EXITED, UNKNOWN):
                    break
                time.sleep(0.01)
            tr["after_escalation_tri"] = tr["post"][-1]["tri"] if tr["post"] else None
        pre = {}
        for n in names:                    # what an outside observer sees BEFORE T5 (after the arm's own polling)
            node = self.node(n)
            st0 = _oracle_stat(node["pid"])
            try:
                os.kill(node["pid"], 0)
                k0 = "success"
            except ProcessLookupError:
                k0 = "ESRCH"
            pre[n] = {"proc_state": st0["state"] if st0 and st0["starttime"] == node["starttime"] else None, "kill_pid_0": k0}
        tr["pre_t5_observation"] = pre
        tr["t5"] = arm.t5_reap()
        tr["final_poll"] = arm.poll()["tri"]
        tr["residual_after_t5"] = arm.residual()
        tr["truth_final"] = self.truths(names)
        tr["elapsed"] = round(now() - t0, 3)
        if expect_first is not None:
            first_truth = tr["polls"][0]["truth_pre"]
            tr["bench_precondition"] = first_truth
        return tr

    # -- cleanup and residual scan (bench-owned nodes only; pidfd-verified)
    def cleanup(self, keep_sentinel=True):
        notes = []
        for node in list(self.nodes):
            if keep_sentinel and self.sentinel and node["pid"] == self.sentinel["pid"]:
                continue
            st, ev = oracle_state(node, timeout=0.5)
            if st == RUNNING:
                try:
                    signal.pidfd_send_signal(node["pidfd"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        end = now() + 6
        pending = [n for n in self.nodes if not (keep_sentinel and self.sentinel and n["pid"] == self.sentinel["pid"])]
        while pending and now() < end:
            still = []
            for node in pending:
                st = _oracle_stat(node["pid"])
                if st is None or st["starttime"] != node["starttime"]:
                    continue
                if st["ppid"] == self.me:
                    try:
                        os.waitpid(node["pid"], os.WNOHANG)
                    except ChildProcessError:
                        pass
                still.append(node)
            pending = [n for n in still if (_oracle_stat(n["pid"]) or {}).get("starttime") == n["starttime"]]
            if pending:
                time.sleep(0.01)
        residual = []
        for node in self.nodes:
            if keep_sentinel and self.sentinel and node["pid"] == self.sentinel["pid"]:
                continue
            st = _oracle_stat(node["pid"])
            if st is not None and st["starttime"] == node["starttime"]:
                residual.append({"name": node["name"], "pid": node["pid"], "state": st["state"], "ppid": st["ppid"]})
        scan = []
        for d in os.listdir("/proc"):
            if d.isdigit() and int(d) != self.me:
                try:
                    with open("/proc/%s/cmdline" % d, "rb") as f:
                        c = f.read()
                except OSError:
                    continue
                if TOKEN.encode() in c and not (self.sentinel and int(d) == self.sentinel["pid"]):
                    scan.append(int(d))
        kids = []
        for d in os.listdir("/proc"):
            if d.isdigit():
                st = _oracle_stat(int(d))
                if st and st["ppid"] == self.me and int(d) != self.me:
                    kids.append(int(d))
        for node in self.nodes:
            try:
                os.close(node["pidfd"])
            except OSError:
                pass
        shutil.rmtree(self.ctl, ignore_errors=True)
        self.nodes = []
        return {"residual_nodes": residual, "token_scan_pids": scan, "children_of_supervisor": kids, "notes": notes}

    def final_cleanup(self):
        out = {}
        if self.sentinel:
            try:
                signal.pidfd_send_signal(self.sentinel["pidfd"], signal.SIGKILL)
            except ProcessLookupError:
                pass
            time.sleep(0.2)
            st = _oracle_stat(self.sentinel["pid"])
            out["sentinel_after_kill"] = None if st is None else st["state"]
        shutil.rmtree(self.workdir, ignore_errors=True)
        return out


# ---------------------------------------------------------------- common checks
def expected_status_ok(arm, node, want):
    got = arm.exit_status(node["pid"])
    if got is None:
        return False, got
    if want[0] == "exit":
        return got.get("kind") == "exit" and got.get("code") == want[1], got
    return got.get("kind") == "signal" and got.get("sig") == want[1], got


def collateral_checks(lab, arm, ck, allowed_names):
    ck.add("sentinel_alive_and_untouched", lab.sentinel_ok())
    if arm.baseline:
        bad = [s for s in arm.signal_log if s.get("pgid") not in lab.allowed_pgids]
    else:
        ok_pids = {(lab.node(n)["pid"], lab.node(n)["starttime"]) for n in allowed_names}
        bad = [s for s in arm.signal_log if (s["pid"], s["starttime"]) not in ok_pids and s["result"] in ("sent", "gone", "error")]
    ck.add("no_signal_to_non_target", not bad, [], bad)
    if not arm.baseline:
        badw = [w for w in arm.wait_calls if w["oracle_ppid"] not in (None, lab.me)]
        ck.add("wait_calls_only_on_own_children", not badw, [], badw)


def finish_record(rec, ck):
    rec["checks"] = ck.checks
    failed = ck.failed()
    rec["status"] = FAIL if failed else PASS
    rec["failed_checks"] = [c["name"] for c in failed]
    return rec
