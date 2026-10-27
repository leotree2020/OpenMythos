"""Supervisor stub: the process under test.  Exec'd by the observer as `python -I -S sup_stub.py` with its control socket on fd 3.
BLIND: neither argv, environment nor open descriptors reveal the registry path or any role label (checked as BV-9).
Order inside this process:  instrumentation (BV-10)  ->  SETUP (topology via the ticket protocol)  ->  S0 (candidate)  ->  report.
Only candidate calls made while PHASE == 'S0' count as candidate actions.  WRITTEN, NOT RUN."""
import ctypes
import os
import signal
import socket
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C        # noqa: E402
import node as N          # noqa: E402
import proto              # noqa: E402

CTRL_FD = 3
EVENTS = []
PHASE = ["SETUP"]
ORIG = {}
_WRAPPED_OS = ("kill", "killpg", "waitpid", "waitid", "wait", "wait3", "wait4")


def ev(call, args=None, infra=False):
    EVENTS.append({"seq": len(EVENTS) + 1, "phase": PHASE[0], "call": call, "args": None if args is None else repr(args)[:200],
                   "infra": infra, "mono": C.mono()})


def _make_wrapper(name, orig):
    def wrapper(*a, **k):
        ev(name, (a, k))
        return orig(*a, **k)
    wrapper.__name__ = "e1a_wrapped_" + name.replace(".", "_")
    return wrapper


def install_instrumentation():
    """BV-10: wrap every kill / wait entry point BEFORE any candidate module is imported."""
    loaded_before = sorted(m for m in ("a_lab", "e2_lab") if m in sys.modules)
    names = []
    for n in _WRAPPED_OS:
        if hasattr(os, n):
            ORIG["os." + n] = getattr(os, n)
            setattr(os, n, _make_wrapper("os." + n, ORIG["os." + n]))
            names.append("os." + n)
    if hasattr(signal, "pidfd_send_signal"):
        ORIG["signal.pidfd_send_signal"] = signal.pidfd_send_signal
        signal.pidfd_send_signal = _make_wrapper("signal.pidfd_send_signal", ORIG["signal.pidfd_send_signal"])
        names.append("signal.pidfd_send_signal")
    return {"wrapped": names, "candidate_modules_loaded_at_install": loaded_before}


def wrappers_effective():
    out = {}
    for full, orig in ORIG.items():
        mod, attr = full.split(".")
        out[full] = getattr(sys.modules[mod], attr) is not orig
    return out


def bench_reap(pid):
    """Setup-phase wait on a helper node by SPECIFIC pid.  Bench infrastructure: tagged and excluded from candidate accounting."""
    ev("BENCH_REAP", pid, infra=True)
    deadline = C.mono() + 15.0
    while True:
        try:
            p, st = ORIG["os.waitpid"](pid, os.WNOHANG)
        except ChildProcessError:
            return "ECHILD"
        if p == pid:
            return os.waitstatus_to_exitcode(st)
        if C.mono() > deadline:
            return "TIMEOUT"
        time.sleep(0.01)


def my_prctl_get_subreaper():
    """Independent read-back (not the candidate's call path)."""
    libc = ctypes.CDLL(None, use_errno=True)
    v = ctypes.c_int(-1)
    return v.value if libc.prctl(37, ctypes.byref(v), 0, 0, 0) == 0 else None


def check_pins(pins):
    bad = []
    for name, p in pins.items():
        if C.sha256_file(p["path"]) != p["sha256"]:
            bad.append(name)
    return bad


def main():
    ch = proto.Channel(socket.socket(fileno=CTRL_FD))
    try:
        msg, _ = ch.expect({"SPEC"}, 20.0)
        st = msg["spec"]["stub"]
        ch.send({"t": "FIRST_ACTION", "mono": C.mono()})
        inst = install_instrumentation()
        sub_before = my_prctl_get_subreaper()
        names = {}
        reaps = {}
        for op in st["ops"]:
            if op["op"] == "spawn":
                pid, nid = N.request_spawn(ch, op["spec"].get("role", "sleeper"), op["label"], op["spec"])
                names[op["label"]] = {"pid": pid, "node_id": nid}
            elif op["op"] == "reap":
                reaps[op["ref"]] = bench_reap(names[op["ref"]]["pid"])
        ch.send({"t": "SETUP_DONE", "names": names, "reaps": reaps, "inst": inst, "wrappers_effective": wrappers_effective(),
                 "subreaper_before": sub_before, "sigchld_default": signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
                 "sup_pid": os.getpid()})
        go, _ = ch.expect({"GO_S0", "FINISH"}, 60.0)
        if go["t"] == "FINISH":
            os._exit(0)
        result = {"bench_error": None}
        bad = check_pins(st["pins"])
        if bad:
            result["bench_error"] = "PIN_MISMATCH: %s" % bad
        else:
            import candidates
            PHASE[0] = "S0"
            ev("S0_START")
            try:
                result["out"] = candidates.run_candidate(st["candidate"], go["root_node"], st.get("injection") or {})
            except BaseException:
                result["candidate_exception"] = traceback.format_exc()
            ev("S0_VERDICT")
            PHASE[0] = "POST"
        result["subreaper_after"] = my_prctl_get_subreaper()
        result["wrappers_effective_at_s0"] = wrappers_effective()
        result["events"] = EVENTS
        ch.send({"t": "S0_RESULT", "result": result})
        try:
            ch.expect({"FINISH", "EXIT"}, C.T_NODE_MAX)
        except proto.ProtoError:
            pass
        os._exit(0)
    except BaseException:
        try:
            ch.send({"t": "STUB_ERROR", "tb": traceback.format_exc()})
        except BaseException:
            pass
        os._exit(C.EXIT_CHILD_EXC)


if __name__ == "__main__":
    main()
