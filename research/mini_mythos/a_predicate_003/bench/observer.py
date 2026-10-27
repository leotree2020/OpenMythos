"""Observer: the top-level bench process.  Owns the REG file, the lineage ledger (node records created at GATED-SPAWN
registration), the pidfd handles and the final, identity-verified cleanup.  WRITTEN, NOT RUN.

Cleanup rule: signals go only to nodes registered by this observer, only through PidfdHandle (identity confirmed at open),
never by name, command line token or process group.  Command-line scans are diagnostic reports only."""
import os
import signal
import time

import common as C
import gate
import proto
import registry as R


class NodeRec:
    def __init__(self, node_id, role, label, creator, spec):
        self.node_id, self.role, self.label, self.creator, self.spec = node_id, role, label, creator, spec
        self.state = "INTENT"                 # INTENT -> FORKED -> REGISTERED -> RELEASED | ABORTED
        self.pid = self.starttime = None
        self.fp = None                        # kernel fingerprint at registration
        self.handle = None                    # PidfdHandle
        self.sock = None                      # observer end of the node's control socket
        self.gate_w = None
        self.direct = False                   # forked by the observer itself (so the observer may waitpid it)
        self.ready = None                     # READY message
        self.first_action_mono = None
        self.ctl_eof = False
        self.exit_status = None
        self.messages = []                    # other messages received from the node
        self.trial = None                     # trial tag at creation time
        self.forked_pid = None                # pid returned by fork (direct children), kept even if registration fails
        self.gate_ino = None                  # inode of the gate pipe (BV-8: must not appear in any node)
        self.spec_send_error = None


class Observer:
    def __init__(self, reg_path):
        self.reg = R.RegWriter(reg_path)
        self.reg_path = reg_path
        self.nodes = {}
        self.counter = 0
        self.problems = []                    # bench-level problems (each makes the trial BLOCKED)
        self.trial_tag = None

    # ------------------------------------------------------------ node creation by the observer itself
    def _new_id(self):
        self.counter += 1
        return "n%05d" % self.counter

    def spawn_direct(self, role, label, spec, entry, extra_keep=(), t_gate_max=C.T_GATE_MAX, hold_release=False):
        nid = self._new_id()
        rec = NodeRec(nid, role, label, "O", spec)
        rec.direct = True
        rec.trial = self.trial_tag
        self.nodes[nid] = rec
        gate_r, gate_w = os.pipe()
        obs_end, node_end = proto.socketpair()
        rec.sock, rec.gate_w = obs_end, gate_w
        rec.gate_ino = os.fstat(gate_w).st_ino
        self.reg.write("INTENT", node_id=nid, creator="O", creator_pid=os.getpid(), role=role, label=label, mode=spec.get("mode"),
                       t_gate_max=t_gate_max, trial=self.trial_tag)
        try:
            pid = gate.fork_gated(gate_r, node_end.fileno(), entry, t_gate_max, extra_keep)
        except OSError as e:
            os.close(gate_r)
            node_end.close()
            self._abort(rec, "fork failed: %r" % (e,))
            return rec
        os.close(gate_r)
        node_end.close()
        rec.state = "FORKED"
        rec.forked_pid = pid
        self._register(rec, pid, os.getpid(), hold_release)
        return rec

    # ------------------------------------------------------------ registration / release / abort
    def _register(self, rec, pid, creator_pid, hold_release=False):
        """Verify the forked child's identity and lineage, write REGISTERED, only then release.  Fail closed."""
        try:
            fp = C.fingerprint(pid)
            if fp is None:
                raise C.IdentityError("child %d vanished before registration" % pid)
            handle = C.PidfdHandle(pid, fp["starttime"])
            fp2 = C.fingerprint(pid)
            if fp2 is None or fp2["starttime"] != fp["starttime"]:
                handle.close()
                raise C.IdentityError("fingerprint changed during registration")
            if fp2["ppid"] != creator_pid:
                handle.close()
                raise C.IdentityError("ppid %d != creator pid %d" % (fp2["ppid"], creator_pid))
            rec.pid, rec.starttime, rec.fp, rec.handle = pid, fp["starttime"], fp2, handle
            self.reg.write("REGISTERED", node_id=rec.node_id, pid=pid, starttime=fp["starttime"], sid=fp2["sid"], pgrp=fp2["pgrp"],
                           ppid=fp2["ppid"], creator=rec.creator, creator_pid=creator_pid, role=rec.role, label=rec.label)
            rec.state = "REGISTERED"
        except (C.IdentityError, C.ProcUnreadable, OSError) as e:
            self._abort(rec, "registration failed: %r" % (e,))
            return False
        if not hold_release:
            self.release(rec)
        return True

    def release(self, rec):
        if rec.state != "REGISTERED":
            raise RuntimeError("release of %s in state %s" % (rec.node_id, rec.state))
        self.reg.write("RELEASED", node_id=rec.node_id)        # REGISTERED is durable before the release byte is written
        try:
            os.write(rec.gate_w, b"R")
        finally:
            os.close(rec.gate_w)
            rec.gate_w = None
        rec.state = "RELEASED"
        try:
            proto.send_msg(rec.sock, {"t": "SPEC", "spec": rec.spec})
        except OSError as e:                      # an exec'd node (janitor) may already have closed its control end
            rec.spec_send_error = repr(e)

    def _abort(self, rec, reason, expected=False):
        self.reg.write("ABORTED", node_id=rec.node_id, reason=reason)
        if rec.gate_w is not None:
            try:
                os.write(rec.gate_w, b"A")
            except OSError:
                pass
            os.close(rec.gate_w)
            rec.gate_w = None
        rec.state = "ABORTED"
        if not expected:
            self.problems.append("%s aborted: %s" % (rec.node_id, reason))

    def abort_held(self, rec, reason="held node aborted by bench (validity check)"):
        self._abort(rec, reason, expected=True)

    # ------------------------------------------------------------ message service
    def _live_socks(self):
        return {r.sock: r for r in self.nodes.values() if r.sock is not None and not r.ctl_eof}

    def serve(self, timeout):
        socks = self._live_socks()
        if not socks:
            if timeout > 0:
                time.sleep(timeout)
            return
        by_fd = {s.fileno(): r for s, r in socks.items()}
        for fd in C.poll_ready(list(by_fd), timeout):
            self._handle(by_fd[fd])

    def _handle(self, rec):
        try:
            msg, fds = proto.recv_msg(rec.sock, 2.0)
        except proto.ProtoEOF:
            rec.ctl_eof = True
            return
        except proto.ProtoTimeout:
            return
        except proto.ProtoError as e:
            rec.ctl_eof = True
            self.problems.append("%s protocol error: %r" % (rec.node_id, e))
            return
        t = msg.get("t")
        for fd in fds:
            os.close(fd)                                        # nodes never send descriptors to the observer
        if t == "TICKET":
            self._on_ticket(rec, msg)
        elif t == "CREATED":
            self._on_created(rec, msg)
        elif t == "CREATE_FAILED":
            child = self.nodes.get(msg.get("node_id"))
            if child is not None:
                self._abort(child, "creator reported fork failure: %s" % msg.get("err"))
        elif t == "READY":
            rec.ready = msg
        elif t == "FIRST_ACTION":
            rec.first_action_mono = msg.get("mono")
        else:
            rec.messages.append(msg)

    def _on_ticket(self, creator, msg):
        if creator.state != "RELEASED":
            proto.send_msg(creator.sock, {"t": "TICKET_DENIED", "why": "creator not released"})
            return
        nid = self._new_id()
        spec = msg.get("spec") or {}
        child = NodeRec(nid, msg.get("role", "sleeper"), msg.get("label", "?"), creator.node_id, spec)
        self.nodes[nid] = child
        gate_r, gate_w = os.pipe()
        obs_end, node_end = proto.socketpair()
        child.sock, child.gate_w = obs_end, gate_w
        child.creator_pid = creator.pid
        child.trial = self.trial_tag
        child.gate_ino = os.fstat(gate_w).st_ino
        self.reg.write("INTENT", node_id=nid, creator=creator.node_id, creator_pid=creator.pid, role=child.role, label=child.label,
                       mode=spec.get("mode"), t_gate_max=C.T_GATE_MAX, trial=self.trial_tag)
        try:
            proto.send_msg(creator.sock, {"t": "TICKET_OK", "node_id": nid, "t_gate_max": C.T_GATE_MAX}, fds=[gate_r, node_end.fileno()])
        finally:
            os.close(gate_r)
            node_end.close()

    def _on_created(self, creator, msg):
        child = self.nodes.get(msg.get("node_id"))
        if child is None or child.creator != creator.node_id or child.state != "INTENT":
            self.problems.append("CREATED for unknown/foreign ticket %r from %s" % (msg, creator.node_id))
            return
        child.state = "FORKED"
        ok = self._register(child, int(msg["pid"]), creator.pid)
        try:
            proto.send_msg(creator.sock, {"t": "REGISTERED_OK" if ok else "REGISTER_FAILED", "node_id": child.node_id})
        except (OSError, proto.ProtoError) as e:
            self.problems.append("could not answer creator %s: %r" % (creator.node_id, e))

    def wait_for(self, cond, timeout):
        deadline = C.mono() + timeout
        while True:
            if cond():
                return True
            left = deadline - C.mono()
            if left <= 0:
                return False
            self.serve(min(0.05, left))

    def trial_nodes(self):
        return [r for r in self.nodes.values() if r.trial == self.trial_tag]

    def find(self, label):
        for r in self.trial_nodes():
            if r.label == label and r.state == "RELEASED":
                return r
        return None

    def trial_records(self):
        ids = {r.node_id for r in self.trial_nodes()}
        return [x for x in self.reg.records if x.get("node_id") in ids]

    # ------------------------------------------------------------ cleanup (registered identities only)
    def kill_registered(self, only=None):
        """SIGKILL every still-running registered node of the CURRENT trial through its identity-confirmed pidfd.  -> per-node results."""
        out = []
        for r in self.trial_nodes():
            if only is not None and r.node_id not in only:
                continue
            if r.handle is None:
                continue
            if r.handle.exited():
                out.append({"node_id": r.node_id, "result": "already_exited"})
                continue
            out.append({"node_id": r.node_id, "result": r.handle.send(signal.SIGKILL)})
        return out

    def reap_direct(self, timeout=5.0):
        """waitpid by specific pid on the observer's own children (never -1)."""
        deadline = C.mono() + timeout
        for r in self.trial_nodes():
            if not r.direct or r.forked_pid is None or r.exit_status is not None:
                continue
            while True:
                try:
                    pid, status = os.waitpid(r.forked_pid, os.WNOHANG)
                except ChildProcessError:
                    r.exit_status = "ECHILD"
                    break
                if pid == r.forked_pid:
                    r.exit_status = os.waitstatus_to_exitcode(status)
                    break
                if C.mono() > deadline:
                    break
                time.sleep(0.01)

    def residual(self):
        """Registered nodes that are not provably dead (identity from /proc fingerprint, independent of the pidfd)."""
        left = []
        for r in self.trial_nodes():
            if r.pid is None or r.state not in ("REGISTERED", "RELEASED"):
                continue
            try:
                if not C.process_is_dead(r.pid, r.starttime):
                    left.append(r.node_id)
            except C.ProcUnreadable:
                left.append(r.node_id)
        return left

    def mark_dead(self):
        still = set(self.residual())
        for r in self.trial_nodes():
            if r.pid is not None and r.state in ("REGISTERED", "RELEASED") and r.node_id not in still:
                self.reg.write("DEAD", node_id=r.node_id)
                r.state = "DEAD"
                if r.handle is not None:
                    r.handle.close()
                    r.handle = None
                if r.sock is not None:
                    try:
                        r.sock.close()
                    except OSError:
                        pass
                    r.sock = None

    def finish_trial_cleanup(self, grace=3.0):
        """Kill -> reap -> verify.  -> report dict.  Never signals anything that is not a registered, identity-confirmed node."""
        report = {"kill": self.kill_registered()}
        self.wait_for(lambda: not self.residual(), grace)
        self.reap_direct()
        res = self.residual()
        report["residual_after_kill"] = res
        report["cleanup_ok"] = not res
        if not res:
            self.mark_dead()
        return report
