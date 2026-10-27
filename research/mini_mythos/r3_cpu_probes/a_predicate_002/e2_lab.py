#!/usr/bin/env python3
"""F3B-D1-A-CPU-002 -- test-bench extensions for E1 (attribution safety), E2 (CA vs subprocess.Popen), E3 (CB without T5).

CPU-001's a_lab.py is imported UNCHANGED (its arms CA / CB are the objects under test).  This module only adds:
  * SpawnLab         -- Lab whose roots may share the supervisor's session (needed to build an E1 mis-configured stage);
  * run_in_fresh_session -- runs a case body in a forked session leader so a mis-attribution can only ever touch
                        sacrificial processes created by that body;
  * StrictMixin / ArmCAS / ArmCBS -- EXPERIMENTAL attribution variants (not CPU-001 arms, not proposals for R3);
  * ArmCAP           -- CA variant whose only reaper is subprocess.Popen (mitigation check for E2).
Linux only, standard library only, no network, no GPU.
"""
import json
import os
import select
import signal
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "a_predicate"))
import a_lab as L                                        # CPU-001 code, not modified
from a_lab import (ALIVE, EXITED, UNKNOWN, RUNNING, ZOMBIE, GONE, PASS, FAIL, BLOCKED, Blocked, SafetyError, Checker,
                   Target, oracle_state)


class SpawnLab(L.Lab):
    def spawn(self, spec, new_session=True):
        names = L.collect_names(spec)
        r, w = os.pipe()
        os.set_inheritable(w, True)
        pid = os.fork()
        if pid == 0:
            try:
                os.close(r)
                if new_session:
                    os.setsid()
                os.execv(sys.executable, [sys.executable, "-S", L.NODE, L.TOKEN, json.dumps(spec), str(w), self.ctl])
            finally:
                os._exit(127)
        os.close(w)
        reports, buf = [], b""
        end = L.now() + 10
        while len(reports) < len(names) and L.now() < end:
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
            st = L._oracle_stat(rep["pid"])
            if st is None or st["starttime"] != rep["starttime"]:
                raise Blocked("node %s: /proc fingerprint differs from self report" % rep["name"])
            out[rep["name"]] = rep
            self.nodes.append(rep)
            if rep["pid"] != self.sentinel_pid():
                self.allowed_pgids.add(rep["pgrp"])
        return out

    def spawn_detached(self, name, term="ignore", new_session=True):
        """A running process that is NOT a child of this supervisor (the intermediate parent exits while the subreaper
        flag is off).  With new_session=False the process keeps the supervisor's session."""
        was = L.prctl_get_subreaper()
        self.set_subreaper(False)
        try:
            nodes = self.spawn({"name": "H_" + name, "children": [{"name": name, "setsid": new_session, "term": term}]},
                               new_session=new_session)
            self.go("H_" + name, "exit", 0)
            self.wait_state(nodes["H_" + name], ZOMBIE)
            os.waitpid(nodes["H_" + name]["pid"], 0)
        finally:
            self.set_subreaper(bool(was))
        return nodes[name]


def run_in_fresh_session(body, timeout=90):
    """Fork a child that becomes a session leader and runs body(lab2) -> JSON-able dict.  The outer subreaper flag is
    cleared around the fork so that the child starts with the flag off (fork children do not inherit it)."""
    r, w = os.pipe()
    was = L.prctl_get_subreaper()
    L.prctl_set_subreaper(False)
    pid = os.fork()
    if pid == 0:
        code = 0
        try:
            os.close(r)
            os.setsid()
            lab2 = SpawnLab()
            lab2.begin()
            try:
                res = body(lab2)
            finally:
                res_cleanup = lab2.cleanup()
            res["fresh_session_cleanup"] = res_cleanup
            res["fresh_session_leader_pid"] = os.getpid()
            data = json.dumps(res, default=str)
        except BaseException as e:
            data = json.dumps({"__error__": repr(e), "__trace__": traceback.format_exc()})
            code = 1
        os.write(w, data.encode())
        os._exit(code)
    os.close(w)
    chunks, end = [], L.now() + timeout
    while L.now() < end:
        rl, _, _ = select.select([r], [], [], 0.5)
        if rl:
            c = os.read(r, 65536)
            if not c:
                break
            chunks.append(c)
    os.close(r)
    L.prctl_set_subreaper(bool(was))              # restored only after the body is done: its detached helpers must go to pid 1
    try:
        os.killpg(pid, signal.SIGKILL)           # the whole fresh session was created by us; nothing else lives there
    except ProcessLookupError:
        pass
    except PermissionError:
        pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass
    if not chunks:
        raise Blocked("fresh-session body produced no result (timeout or crash)")
    res = json.loads(b"".join(chunks).decode())
    if "__error__" in res:
        raise Blocked("fresh-session body failed: %s\n%s" % (res["__error__"], res.get("__trace__", "")[-800:]))
    return res


class StrictMixin:
    """EXPERIMENTAL strict attribution (CPU-002 variant, not CPU-001's arms):
       * sid_hint only if the stage root leads a session that is not the supervisor's own;
       * no closed-world orphan attribution: an unregistered child of the supervisor is ignored if it started before the stage
         root (it cannot be a stage descendant) and otherwise UNATTRIBUTABLE -> UNKNOWN;
       * descendants of registered auxiliary processes are recorded as aux_family (neither target nor UNKNOWN)."""
    strict = True

    def __init__(self, lab):
        super().__init__(lab)
        self.aux_family = {}
        self.ignored_older = set()
        self.dedicated_session = False
        self.root_starttime = 0

    def register_root(self, node):
        tg = super().register_root(node)
        self.root_starttime = tg.starttime
        self.dedicated_session = (tg.sid == tg.pid) and (tg.sid != os.getsid(0))
        return tg

    def preflight(self, setter=L.prctl_set_subreaper):
        r = dict(super().preflight(setter))
        if not self.dedicated_session:
            r["status"], r["code"] = "BLOCKED", "STAGE_SESSION_NOT_DEDICATED"
        self.preflight_result = r
        return r

    def _is_aux(self, pid, table):
        st = table.get(pid)
        return st is not None and ((pid in self.aux and self.aux[pid] == st["starttime"]) or
                                   (pid in self.aux_family and self.aux_family[pid] == st["starttime"]))

    def _discover(self, table):
        self.unattrib, self.ignored_older = set(), set()
        changed = True
        while changed:
            changed = False
            for pid, st in list(table.items()):
                if pid in self.targets or pid == self.me or self._is_aux(pid, table):
                    continue
                par = self.targets.get(st["ppid"])
                if par is not None and par.matches(table.get(st["ppid"])):
                    self.targets[pid] = Target(pid, st, "lineage")
                    changed = True
                elif self._is_aux(st["ppid"], table):
                    self.aux_family[pid] = st["starttime"]
                    changed = True
                elif self.dedicated_session and st["sid"] == self.stage_sid:
                    self.targets[pid] = Target(pid, st, "sid_hint_dedicated")
                    changed = True
                elif st["ppid"] == self.me:
                    if st["starttime"] < self.root_starttime:
                        self.ignored_older.add(pid)
                    else:
                        self.unattrib.add(pid)


class ArmCAS(StrictMixin, L.ArmCA):
    name = "CA-S"


class ArmCBS(StrictMixin, L.ArmCB):
    name = "CB-S"


class ArmCAP(L.ArmCA):
    """CA whose ONLY reaper is subprocess.Popen: status is read from Popen.poll()/returncode (mitigation check)."""
    name = "CA-P"

    def __init__(self, lab):
        super().__init__(lab)
        self.popens = {}

    def _eval(self, tg, table, problems):
        p = self.popens.get(tg.pid)
        if p is not None and not tg.reaped:             # Popen is the only reaper: ask it first, /proc may already be empty
            self._log_wait("Popen.poll", tg.pid)
            rc = p.poll()
            if rc is not None:
                tg.reaped = True
                tg.exit = {"kind": "exit", "code": rc} if rc >= 0 else {"kind": "signal", "sig": -rc}
                self.reap_log.append({"pid": tg.pid, "status": tg.exit, "phase": "poll(Popen)"})
                tg.state, tg.reason = EXITED, "reaped_by_Popen"
                return
        return super()._eval(tg, table, problems)

    def _observe_child(self, tg, st):
        p = self.popens.get(tg.pid)
        if p is None:
            return super()._observe_child(tg, st)
        self._log_wait("Popen.poll", tg.pid)
        rc = p.poll()
        if rc is None:
            tg.state, tg.reason = ALIVE, "Popen.poll_None"
            return
        tg.reaped = True
        tg.exit = {"kind": "exit", "code": rc} if rc >= 0 else {"kind": "signal", "sig": -rc}
        self.reap_log.append({"pid": tg.pid, "status": tg.exit, "phase": "poll(Popen)"})
        tg.state, tg.reason = EXITED, "reaped_by_Popen"


ARMS2 = dict(L.ARMS)
ARMS2.update({"CA-S": lambda lab: ArmCAS(lab), "CB-S": lambda lab: ArmCBS(lab), "CA-P": lambda lab: ArmCAP(lab)})
