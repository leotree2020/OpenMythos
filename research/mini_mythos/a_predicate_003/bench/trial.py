"""One E1-A trial: spawn the supervisor stub through GATED-SPAWN, let it build the scenario topology (SETUP), read the kernel
independently, release S0, collect the candidate output and the instrumentation log, judge, clean up through registered
identities only.  WRITTEN, NOT RUN."""
import fcntl
import os
import signal
import sys
import termios
import traceback

import common as C
import proto
import registry as R
import scenarios as S
import truth as T

STUB_PATH = os.path.join(C.BENCH_DIR, "sup_stub.py")
JANITOR_PATH = os.path.join(C.BENCH_DIR, "janitor.py")
REQUIRED_WRAPPERS = {"os.kill", "os.killpg", "os.waitpid", "os.waitid", "signal.pidfd_send_signal"}
FD_ALLOWED_MAX = 6


class RunAbort(RuntimeError):
    """A bench-level condition that makes continuing unsafe (e.g. a registered node that cannot be confirmed dead)."""


# ---------------------------------------------------------------- exec helpers (run in the gated child after RELEASE)
def _lift_fd(fd, minimum=20):
    new = fcntl.fcntl(fd, fcntl.F_DUPFD, minimum)
    os.close(fd)
    return new


def make_exec_sup(launch, tty_slave, sigchld_ignored):
    def entry(ctrl_fd):
        ctrl = _lift_fd(ctrl_fd)
        os.setsid()                                            # the supervisor is a fresh session leader in every launch context
        if launch == "L2":
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
        if launch == "L3":
            dn = os.open(os.devnull, os.O_RDWR)
            for fd in (0, 1, 2):
                os.dup2(dn, fd)
            if dn > 2:
                os.close(dn)
        if launch == "L4":
            fcntl.ioctl(tty_slave, termios.TIOCSCTTY, 0)
            for fd in (0, 1, 2):
                os.dup2(tty_slave, fd)
            if tty_slave > 2:
                os.close(tty_slave)
        if sigchld_ignored:
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)     # SIG_IGN is inherited across execve
        os.dup2(ctrl, 3, inheritable=True)
        os.close(ctrl)
        os.execve(sys.executable, [sys.executable, "-I", "-S", "-B", STUB_PATH], {"PATH": "/usr/bin:/bin"})
    return entry


def make_exec_janitor(reg_path, obs_pid, obs_start, log_path):
    def entry(ctrl_fd):
        os.execve(sys.executable, [sys.executable, "-I", "-S", "-B", JANITOR_PATH, reg_path, str(obs_pid), str(obs_start), log_path],
                  {"PATH": "/usr/bin:/bin"})
    return entry


# ---------------------------------------------------------------- helpers
def _msg(rec, types):
    for m in rec.messages:
        if m.get("t") in types:
            return m
    return None


def run_trial(obs, prereg, item, pins, run):
    """-> trial record dict.  Never raises for trial-level problems (they become bench-BLOCKED); raises RunAbort when cleanup fails."""
    scn, cand, launch = item["scenario"], item["candidate"], item["launch"]
    recipe = S.RECIPES[scn]
    rec = {"trial": item, "scenario_evidence_kind": prereg["scenarios"][scn]["evidence_kind"], "prereg_sha256": run["prereg_sha"],
           "bench_reasons": [], "start_wall": C.wall()}
    bench, out, events, extra_unsafe = rec["bench_reasons"], None, [], []
    setup, cand_exc, instr = None, None, {"setup": None, "s0": None}
    obs.trial_tag = item["trial_id"]
    pty_master = pty_slave = None
    sup = None
    try:
        if launch == "L4":
            try:
                pty_master, pty_slave = os.openpty()
            except OSError as e:
                bench.append("PTY_UNAVAILABLE: %r" % (e,))
        if not bench:
            spec = {"label": "SUP", "role": "supervisor", "mode": "none", "children": [], "exit_after_ready": False,
                    "stub": {"scenario": scn, "candidate": cand, "ops": recipe["ops"], "injection": recipe.get("injection") or {},
                             "pins": pins}}
            keep = [pty_slave] if pty_slave is not None else []
            sup = obs.spawn_direct("supervisor", "SUP", spec, make_exec_sup(launch, pty_slave, bool(recipe.get("sigchld_ignored"))),
                                   extra_keep=keep)
            if pty_slave is not None:
                os.close(pty_slave)
                pty_slave = None
            if sup.state != "RELEASED":
                bench.append("SUP_NOT_RELEASED: %s" % sup.state)
        if not bench:
            ok = obs.wait_for(lambda: _msg(sup, ("SETUP_DONE", "STUB_ERROR")) is not None, C.T_SETUP)
            setup = _msg(sup, ("SETUP_DONE",))
            if not ok or setup is None:
                err = _msg(sup, ("STUB_ERROR",))
                bench.append("SETUP_FAILED: %s" % (err["tb"] if err else "timeout"))
        if not bench:
            labels = S.all_labels(recipe)
            if not obs.wait_for(lambda: all(obs.find(l) is not None and obs.find(l).ready is not None for l in labels), 10.0):
                bench.append("NODES_NOT_READY: %s" % [l for l in labels if obs.find(l) is None or obs.find(l).ready is None])
        if setup is not None:
            instr["setup"] = _setup_instrumentation_ok(setup)
        if not bench:
            _pre_s0(obs, prereg, scn, recipe, sup, setup, rec, bench)
        if not bench:
            root = obs.find("root")
            rr = root.ready["fp"]
            proto.send_msg(sup.sock, {"t": "GO_S0", "root_node": {"pid": root.pid, "starttime": rr["starttime"], "sid": rr["sid"], "pgrp": rr["pgrp"]}})
            ok = obs.wait_for(lambda: _msg(sup, ("S0_RESULT", "STUB_ERROR")) is not None, C.T_S0)
            res = _msg(sup, ("S0_RESULT",))
            if not ok or res is None:
                err = _msg(sup, ("STUB_ERROR",))
                bench.append("S0_FAILED: %s" % (err["tb"] if err else "timeout"))
            else:
                _post_s0(obs, prereg, scn, cand, recipe, sup, res["result"], rec, bench, extra_unsafe)
                out, events = res["result"].get("out"), res["result"].get("events", [])
                cand_exc = res["result"].get("candidate_exception")
                instr["s0"] = all((res["result"].get("wrappers_effective_at_s0") or {"x": False}).values())
    except RunAbort:
        raise
    except Exception:
        bench.append("BENCH_EXCEPTION: " + traceback.format_exc())
    finally:
        rec["cleanup"] = _cleanup(obs, sup)
        if pty_slave is not None:
            os.close(pty_slave)
        if pty_master is not None:
            os.close(pty_master)                    # closed only after cleanup: a hang-up must not race the FINISH message
    rec["ledger_check"] = R.check_order(obs.trial_records())
    if rec["ledger_check"]:
        bench.append("LEDGER_ORDER_VIOLATION: %s" % rec["ledger_check"][:3])
    if obs.problems:
        bench.append("OBSERVER_PROBLEMS: %s" % obs.problems[:3])
        obs.problems.clear()
    if not rec["cleanup"]["cleanup_ok"]:
        raise RunAbort("cleanup NOT confirmed in %s (recovery responsibility stays open): %s" % (item["trial_id"], rec["cleanup"]["residual_detail"]))
    streamed = [m["event"] for m in sup.messages if m.get("t") == "EVENT"] if sup is not None else []
    events = T.merge_events(events, streamed)                       # live stream survives a stub that died after the unsafe call
    instrumentation_ok = bool(instr["setup"]) and instr["s0"] is not False
    rec["candidate_output"] = out
    rec["events"] = events
    rec["streamed_unsafe_events"] = streamed
    rec["judgement"] = T.judge(prereg, scn, cand, out, events, bench, extra_unsafe, instrumentation_ok, cand_exc)
    rec["verdict"] = rec["judgement"]["verdict"]
    rec["registry_records"] = obs.trial_records()
    rec["end_wall"] = C.wall()
    obs.trial_tag = "RUN"
    return rec


def _setup_instrumentation_ok(sd):
    inst = sd["inst"]
    return bool(REQUIRED_WRAPPERS <= set(inst["wrapped"]) and not inst["candidate_modules_loaded_at_install"] and all(sd["wrappers_effective"].values()))


def _pre_s0(obs, prereg, scn, recipe, sup, setup, rec, bench):
    labels = S.all_labels(recipe)
    sd = setup
    rec["setup_done"] = {k: sd[k] for k in ("names", "reaps", "inst", "wrappers_effective", "subreaper_before", "sigchld_default")}
    if any(v in ("TIMEOUT", "ECHILD") for v in sd["reaps"].values()):
        bench.append("SETUP_REAP_FAILED: %s" % sd["reaps"])
    inst = sd["inst"]
    if not _setup_instrumentation_ok(sd):
        bench.append("BV-10_FAILED: instrumentation not in place before candidate import: %r" % (inst,))
    table, problems = C.scan_proc()
    bench += T.enumeration_reasons(problems, "pre-S0")
    root = obs.find("root")
    dead = [l for l in S.expected_alive_labels(recipe) if obs.find(l) is None or C.process_is_dead(obs.find(l).pid, obs.find(l).starttime)]
    if dead:
        bench.append("NODE_DIED_BEFORE_S0: %s" % dead)
        return
    sigign = C.read_sigign(sup.pid)
    observed, notes = T.kernel_defects({"pid": root.pid}, sup.pid, table, problems, sigign)
    live = table.get(root.pid)
    sup_st = table.get(sup.pid)
    by = []
    if "X" in labels:
        x = obs.find("X")
        by += T.bystander_reasons("X", table.get(x.pid) if x else None, sup.pid, sup_st["sid"] if sup_st else None, True)
    rec["truth_prereadback"] = {"observed_real_defects": sorted(observed), "notes": notes, "root_live": live, "sup": sup_st,
                                "sup_sigign": sigign, "root_report": root.ready["fp"]}
    bench += T.topology_reasons(S.expected_real_defects(prereg, scn), observed, root.ready["fp"], live, sd["subreaper_before"], by)
    bench += _stray_reasons(obs, sup, table, "BV-5_FAILED(pre-S0)")      # (incomplete enumeration was already reported above)
    # BV-8 / BV-9 / BV-4 timing
    inos = [r.gate_ino for r in obs.trial_nodes() if r.gate_ino is not None]
    for r in obs.trial_nodes():
        if r.state == "RELEASED" and r.pid is not None and not C.process_is_dead(r.pid, r.starttime):
            bench += T.fd_hygiene_reasons(r.pid, inos, FD_ALLOWED_MAX)
    bench += T.blindness_reasons(sup.pid, [obs.reg_path, "registry.jsonl", "sleeper", "GATED"])
    released = {x["node_id"]: x["mono"] for x in obs.trial_records() if x["kind"] == "RELEASED"}
    for r in obs.trial_nodes():
        if r.first_action_mono is not None and r.node_id in released and r.first_action_mono < released[r.node_id]:
            bench.append("BV-4_FAILED: %s acted before its RELEASED record" % r.node_id)


def _stray_reasons(obs, sup, table, tag):
    """BV-5 / R5 reconciliation: nothing in the supervisor's descendant tree, and no child of a registered node, may be unregistered."""
    registered = {r.pid for r in obs.trial_nodes() if r.pid is not None}
    desc = set(C.descendants_of(table, sup.pid))
    stray = [p for p in table if (p in desc or table[p]["ppid"] in registered) and p not in registered and table[p]["state"] not in ("Z", "X")]
    return ["%s: unregistered live processes in the scenario lineage: %s" % (tag, sorted(stray))] if stray else []


def _post_s0(obs, prereg, scn, cand, recipe, sup, result, rec, bench, extra_unsafe):
    table, problems = C.scan_proc()
    bench += T.enumeration_reasons(problems, "post-S0")
    bench += _stray_reasons(obs, sup, table, "BV-5_FAILED(post-S0)")
    rec["stub_result_meta"] = {k: result.get(k) for k in ("bench_error", "candidate_exception", "subreaper_after", "wrappers_effective_at_s0")}
    if result.get("bench_error"):
        bench.append("STUB_BENCH_ERROR: %s" % result["bench_error"])
    # a candidate exception is NOT a bench condition: it is passed to T.judge as a mechanism outcome (FAIL)
    if not all((result.get("wrappers_effective_at_s0") or {"x": False}).values()):
        bench.append("BV-10_FAILED: wrappers not effective at S0")
    bench += T.order_reasons(result.get("events", []))
    out = result.get("out")
    if out is not None and out.get("preflight_executed"):
        inj = recipe.get("injection") or {}
        want = 0 if inj.get("setter") == "fail" else 1
        if result.get("subreaper_after") != want:
            bench.append("TRUTH_SOURCES_DISAGREE: independent subreaper read %r != expected %r" % (result.get("subreaper_after"), want))
    dead = [l for l in S.expected_alive_labels(recipe) if obs.find(l) is None or C.process_is_dead(obs.find(l).pid, obs.find(l).starttime)]
    if sup is not None and C.process_is_dead(sup.pid, sup.starttime):
        dead.append("SUP")
    if dead:
        if T.candidate_unsafe_events(result.get("events", [])):
            extra_unsafe.append("node(s) dead after a candidate signal/wait: %s" % dead)
        else:
            bench.append("NODE_DIED_UNEXPECTEDLY: %s" % dead)


def _cleanup(obs, sup):
    if sup is not None and sup.sock is not None and sup.state == "RELEASED":
        try:
            proto.send_msg(sup.sock, {"t": "FINISH"})
        except (OSError, proto.ProtoError):
            pass
    return obs.finish_trial_cleanup()
