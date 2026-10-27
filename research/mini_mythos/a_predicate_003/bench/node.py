"""Node side of the GATED-SPAWN protocol: ticket client used by any creator (stub or node), and the generic node main.

Creator side:   TICKET -> TICKET_OK(+fds gate_r, ctrl) -> fork_gated -> CREATED(pid) -> REGISTERED_OK | REGISTER_FAILED
Observer side:  INTENT -> (verify + REGISTERED) -> write b"R" to gate_w -> SPEC to the child.
The creator never holds a gate write end, so it can neither release nor keep a child alive past an observer failure.
WRITTEN, NOT RUN."""
import os
import socket

import common as C
import gate
import proto


class SpawnError(RuntimeError):
    pass


def request_spawn(ch, role, label, spec):
    """Create one gated, observer-registered child of the calling process.  -> (pid, node_id)."""
    ch.send({"t": "TICKET", "role": role, "label": label, "spec": spec})
    msg, fds = ch.expect({"TICKET_OK", "TICKET_DENIED"}, C.T_REG_MAX)
    if msg["t"] != "TICKET_OK" or len(fds) != 2:
        for fd in fds:
            os.close(fd)
        raise SpawnError("ticket denied: %r" % (msg,))
    nid = msg["node_id"]
    gate_r, ctrl = fds
    try:
        pid = gate.fork_gated(gate_r, ctrl, node_main, msg.get("t_gate_max", C.T_GATE_MAX))
    except OSError as e:
        os.close(gate_r)
        os.close(ctrl)
        ch.send({"t": "CREATE_FAILED", "node_id": nid, "err": repr(e)})
        raise SpawnError("fork failed: %r" % (e,))
    os.close(gate_r)                              # creator keeps neither the gate nor the child's control socket
    os.close(ctrl)
    ch.send({"t": "CREATED", "node_id": nid, "pid": pid})
    resp, _ = ch.expect({"REGISTERED_OK", "REGISTER_FAILED"}, C.T_REG_MAX + 5.0)
    if resp["t"] != "REGISTERED_OK":
        raise SpawnError("registration failed for %s: %r" % (nid, resp))
    return pid, nid


def node_main(ctrl_fd):
    """Runs in a released generic node ('sleeper').  Reads its spec, applies its session mode, creates its declared children
    through the ticket protocol, reports its own fingerprint, then waits (bounded) for EXIT / EOF."""
    ch = proto.Channel(socket.socket(fileno=ctrl_fd))
    try:
        msg, _ = ch.expect({"SPEC"}, 10.0)
        spec = msg["spec"]
        ch.send({"t": "FIRST_ACTION", "mono": C.mono()})
        mode = spec.get("mode", "none")
        if mode == "setsid":
            os.setsid()
        elif mode == "setpgid":
            os.setpgid(0, 0)
        for child in spec.get("children", []):
            request_spawn(ch, child.get("role", "sleeper"), child["label"], child)
        ch.send({"t": "READY", "label": spec["label"], "fp": C.fingerprint(os.getpid())})
        if spec.get("exit_after_ready"):
            os._exit(0)
        deadline = C.mono() + C.T_NODE_MAX
        while True:
            left = deadline - C.mono()
            if left <= 0:
                os._exit(0)
            try:
                m, _ = ch.recv(left)
            except proto.ProtoError:
                os._exit(0)                         # EOF (observer gone) or timeout: self-terminate
            if m.get("t") == "EXIT":
                os._exit(0)
    except BaseException:
        os._exit(C.EXIT_CHILD_EXC)
