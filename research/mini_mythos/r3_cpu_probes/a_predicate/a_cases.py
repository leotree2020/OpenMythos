#!/usr/bin/env python3
"""F3B-D1-A-CPU-001 -- test matrix (T-01..T-11, T-04b, plus supplementary T-14) and the runner.

Every case builds its own process topology with the lab, takes the TRUE state from the independent oracle, and
compares each arm (B0 x3 readings, CA, CB) against expectations written from the test plan's intent (RA-1..RA-12), not
from any arm's output.  Fault injection (simulated /proc failures, stale fingerprints, substituted pids) is labelled
SIMULATED in the records; it is not real-kernel evidence.
"""
import argparse
import errno
import hashlib
import json
import os
import platform
import random
import signal
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a_lab as L
from a_lab import (ALIVE, EXITED, UNKNOWN, RUNNING, ZOMBIE, GONE, PASS, FAIL, BLOCKED, Blocked, SafetyError, ARMS,
                   Checker, FaultyProcFS, Target, collateral_checks, expected_status_ok, finish_record, oracle_state)


def topo(nodes):
    return {n: {k: v for k, v in d.items() if k not in ("pidfd",)} for n, d in nodes.items()}


def setup(lab, arm, spec, root, preflight=True):
    nodes = lab.spawn(spec)
    arm.register_root(nodes[root])
    if preflight:
        pf = arm.preflight()
        if pf.get("status") == "BLOCKED":
            raise Blocked("S0 preflight failed in the lab: %s" % pf)
    return nodes


def wait_adopted_by_me(lab, node, timeout=3.0):
    end = L.now() + timeout
    while L.now() < end:
        st = L._oracle_stat(node["pid"])
        if st and st["ppid"] == lab.me:
            return st
        time.sleep(0.003)
    raise Blocked("node %s was not re-parented to the supervisor" % node["name"])


def bench_expect(tr, want_first):
    """The bench's own truth at the first poll must match the case's intended precondition, else BLOCKED."""
    pre = tr["polls"][0]["truth_pre"]
    post = tr["polls"][0]["truth_post"]
    alive_pre = any(v == RUNNING for v in pre.values())
    alive_post = any(v == RUNNING for v in post.values())
    if want_first == ALIVE and not (alive_pre and alive_post):
        raise Blocked("bench precondition: expected a running target, truth %s -> %s" % (pre, post))
    if want_first == EXITED and (alive_pre or alive_post):
        raise Blocked("bench precondition: expected all exited, truth %s -> %s" % (pre, post))


def no_sigkill(tr):
    return not any(s.get("stage") == "SIGKILL" for s in tr["signals"])


def sigkill_pids(tr):
    return sorted({s["pid"] for s in tr["signals"] if s.get("stage") == "SIGKILL" and "pid" in s})


def all_gone(ck, tr, names=None):
    tf = tr["truth_final"]
    sel = {k: v for k, v in tf.items() if names is None or k in names}
    ck.add("all_targets_gone_after_T5", all(v == GONE for v in sel.values()), "all GONE", sel)


def status(ck, arm, nodes, name, want):
    ok, got = expected_status_ok(arm, nodes[name], want)
    ck.add("exit_status_preserved:%s" % name, ok, want, got)


# ================================================================= cases
def t01(lab, arm, ck, rec):
    rec["purpose"] = "persistent child that ignores SIGTERM must not be missed by A (RA-1)"
    nodes = setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    tr = lab.run_t3(arm, ["R"], True, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    bench_expect(tr, ALIVE)
    ck.eq("first_poll_tri", tr["first_tri"], ALIVE)
    ck.eq("decision", tr["decision"], "ESCALATED")
    ck.add("no_false_escalation", not tr.get("false_escalation"))
    ck.eq("tri_after_sigkill", tr.get("after_escalation_tri"), EXITED)
    status(ck, arm, nodes, "R", ("signal", 9))
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["R"])


def _exited_root(lab, arm, ck, rec, how):
    nodes = setup(lab, arm, {"name": "R", "exit_code": 7}, "R")
    rec["topology"] = topo(nodes)
    R = nodes["R"]
    lab.wait_state(R, RUNNING)
    if how == "code7":
        lab.go("R", "exit", 7)
        want = ("exit", 7)
    else:
        lab.kill_by_bench(R, signal.SIGKILL)
        want = ("signal", 9)
    ev = lab.wait_state(R, ZOMBIE)
    rec["bench_zombie_evidence"] = ev
    rec["reference_killpg0_before_any_arm_action"] = lab.killpg0(R["pgrp"])
    members = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            st = L._oracle_stat(int(d))
            if st and st["pgrp"] == R["pgrp"]:
                members.append({"pid": int(d), "state": st["state"]})
    rec["group_members_before_any_arm_action"] = members
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    rec["reference_killpg0_after_run"] = lab.killpg0(R["pgrp"])
    try:
        os.kill(R["pid"], 0)
        k0 = "success"
    except ProcessLookupError:
        k0 = "ESRCH"
    rec["post_run_observation"] = {"kill_pid0": k0, "proc_entry_present": L._oracle_stat(R["pid"]) is not None,
                                   "oracle": oracle_state(R, timeout=1.0)[0]}
    bench_expect(tr, EXITED)
    ck.eq("first_poll_tri", tr["first_tri"], EXITED)
    ck.eq("decision", tr["decision"], "EARLY_CONFIRM")
    ck.add("no_sigkill_escalation", no_sigkill(tr), True, no_sigkill(tr))
    status(ck, arm, nodes, "R", want)
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["R"])


def t02a(lab, arm, ck, rec):
    rec["purpose"] = "child exit(7), supervisor has not reaped: exited-unreaped must not make A true; status must survive"
    _exited_root(lab, arm, ck, rec, "code7")


def t02b(lab, arm, ck, rec):
    rec["purpose"] = "child killed by a signal (bench SIGKILL), unreaped: A false; signal status must survive"
    _exited_root(lab, arm, ck, rec, "sig")


def t03(lab, arm, ck, rec):
    rec["purpose"] = ("process group holds only an exited-unreaped child: A must not rely on killpg(pgid,0); "
                      "killpg0 return on THIS kernel is recorded as reference only")
    _exited_root(lab, arm, ck, rec, "code7")
    rec["killpg0_note"] = "reference_killpg0_before_any_arm_action is what killpg(pgid,0) returned on this kernel for a zombie-only group"


def t04(lab, arm, ck, rec):
    rec["purpose"] = "zombie leader + live descendant in the same group, subreaper on: descendant re-parented to the supervisor"
    nodes = setup(lab, arm, {"name": "L", "exit_code": 3, "children": [{"name": "D", "term": "ignore"}]}, "L")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["D"], RUNNING)
    lab.go("L", "exit", 3)
    lab.wait_state(nodes["L"], ZOMBIE)
    st = wait_adopted_by_me(lab, nodes["D"])
    rec["D_ppid_after_leader_exit"] = st["ppid"]
    tr = lab.run_t3(arm, ["L", "D"], True, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    bench_expect(tr, ALIVE)
    ck.eq("first_poll_tri", tr["first_tri"], ALIVE)
    ck.eq("decision", tr["decision"], "ESCALATED")
    ck.add("no_false_escalation", not tr.get("false_escalation"))
    if not arm.baseline:
        ck.eq("sigkill_only_to_live_descendant", sigkill_pids(tr), [nodes["D"]["pid"]])
    ck.eq("tri_after_sigkill", tr.get("after_escalation_tri"), EXITED)
    status(ck, arm, nodes, "L", ("exit", 3))
    status(ck, arm, nodes, "D", ("signal", 9))
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["L", "D"])


def t04b(cross):
    def run(lab, arm, ck, rec):
        rec["purpose"] = ("T-04b-A: real subreaper behaviour. Part 1: S0 must be BLOCKED when the subreaper cannot be set (SIMULATED set failure). "
                          "Part 2: with the OS flag really OFF, record where the orphan goes and what the supervisor can observe; "
                          "completeness evidence is missing, so the answer must never be EXITED (RV-01 floor). "
                          "%s descendant." % ("cross-session (setsid)" if cross else "same-session"))
        if not arm.baseline:
            pf = arm.preflight(setter=lambda flag: False)
            rec["part1_preflight_with_set_failure"] = pf
            ck.eq("part1_S0_blocked_PREFLIGHT_FAILED", (pf.get("status"), pf.get("code")), ("BLOCKED", "PREFLIGHT_FAILED"))
        lab.set_subreaper(False)
        try:
            real = L.prctl_get_subreaper()
            rec["part2_os_subreaper_flag"] = real
            if real != 0:
                raise Blocked("could not clear the subreaper flag")
            spec = {"name": "L", "exit_code": 3, "children": [{"name": "D", "term": "ignore", "setsid": cross}]}
            nodes = lab.spawn(spec)
            arm.register_root(nodes["L"])
            if not arm.baseline:
                pf = arm.preflight(setter=lambda flag: False)
                rec["part2_preflight"] = pf
            rec["topology"] = topo(nodes)
            lab.wait_state(nodes["D"], RUNNING)
            lab.go("L", "exit", 3)
            lab.wait_state(nodes["L"], ZOMBIE)
            D = nodes["D"]
            end = L.now() + 3
            while L.now() < end:
                st = L._oracle_stat(D["pid"])
                if st and st["ppid"] != nodes["L"]["pid"]:
                    break
                time.sleep(0.003)
            ev = oracle_state(D)[1]
            adopter = L._oracle_stat(ev["ppid"]) if ev.get("ppid") else None
            try:
                comm = open("/proc/%d/comm" % ev["ppid"]).read().strip()
            except (OSError, TypeError):
                comm = None
            try:
                os.waitid(os.P_PID, D["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT)
                lab_wait = "waitid_call_succeeded"
            except ChildProcessError:
                lab_wait = "ECHILD (not a child of the supervisor)"
            rec["part2_orphan_behaviour"] = {"D_ppid": ev.get("ppid"), "adopter_comm": comm, "supervisor_pid": lab.me,
                                             "adopted_by_supervisor": ev.get("ppid") == lab.me, "D_sid": ev.get("sid"),
                                             "waitid_by_supervisor": lab_wait}
            ck.add("part2_orphan_not_adopted_by_supervisor (OS behaviour, observed)", ev.get("ppid") != lab.me, True, ev.get("ppid") == lab.me)
            o1 = arm.poll()
            rec["part2_poll1_D_alive"] = {"tri": o1["tri"], "reasons": o1["reasons"], "truth": lab.truths(["L", "D"])}
            want1 = UNKNOWN if cross else ALIVE
            ck.eq("part2_poll1_tri (D really running)", o1["tri"], want1)
            ck.add("part2_poll1_not_EXITED_while_D_runs", o1["tri"] != EXITED, True, o1["tri"])
            lab.kill_by_bench(D, signal.SIGKILL)
            end = L.now() + 3
            while L.now() < end and oracle_state(D, timeout=0.5)[0] == RUNNING:
                time.sleep(0.005)
            rec["part2_D_truth_after_bench_kill"] = oracle_state(D, timeout=1.0)
            o2 = arm.poll()
            rec["part2_poll2_all_exited"] = {"tri": o2["tri"], "reasons": o2["reasons"], "truth": lab.truths(["L", "D"])}
            ck.eq("part2_poll2_tri (all exited, completeness unproven)", o2["tri"], UNKNOWN)
            ck.add("part2_poll2_not_EXITED", o2["tri"] != EXITED, True, o2["tri"])
            if not arm.baseline:
                ck.add("part2_signals_none", not arm.signal_log, [], arm.signal_log)
        finally:
            lab.set_subreaper(True)
        collateral_checks(lab, arm, ck, [])
    return run


def t05(lab, arm, ck, rec):
    rec["purpose"] = "live leader + a zombie child of that live leader + a live child: arms must NOT reap the zombie (not the supervisor's child)"
    spec = {"name": "L", "term": "ignore", "children": [{"name": "Z", "exit_code": 0}, {"name": "S", "term": "ignore"}]}
    nodes = setup(lab, arm, spec, "L")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["S"], RUNNING)
    lab.go("Z", "exit", 0)
    ev = lab.wait_state(nodes["Z"], ZOMBIE)
    rec["Z_zombie_evidence"] = ev
    tr = lab.run_t3(arm, ["L", "Z", "S"], True, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    bench_expect(tr, ALIVE)
    ck.eq("first_poll_tri", tr["first_tri"], ALIVE)
    ck.eq("decision", tr["decision"], "ESCALATED")
    ck.add("no_false_escalation", not tr.get("false_escalation"))
    ck.eq("Z_still_zombie_at_recheck (arm did not reap another process's child)",
          tr["escalation"]["truth_post_recheck"]["Z"] if tr.get("escalation") else None, ZOMBIE)
    if not arm.baseline:
        ck.eq("sigkill_only_to_live_targets", sigkill_pids(tr), sorted([nodes["L"]["pid"], nodes["S"]["pid"]]))
    ck.eq("tri_after_sigkill", tr.get("after_escalation_tri"), EXITED)
    status(ck, arm, nodes, "L", ("signal", 9))
    status(ck, arm, nodes, "S", ("signal", 9))
    status(ck, arm, nodes, "Z", ("exit", 0))
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["L", "Z", "S"])


def t06(lab, arm, ck, rec):
    rec["purpose"] = "every target exited; some are RE-PARENTED zombie descendants: A false; reaped before confirmation"
    spec = {"name": "L", "exit_code": 4, "children": [{"name": "E", "exit_code": 5}]}
    nodes = setup(lab, arm, spec, "L")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["E"], RUNNING)
    lab.go("E", "exit", 5)
    lab.wait_state(nodes["E"], ZOMBIE)
    lab.go("L", "exit", 4)
    lab.wait_state(nodes["L"], ZOMBIE)
    wait_adopted_by_me(lab, nodes["E"])
    tr = lab.run_t3(arm, ["L", "E"], False, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    bench_expect(tr, EXITED)
    ck.eq("first_poll_tri", tr["first_tri"], EXITED)
    ck.eq("decision", tr["decision"], "EARLY_CONFIRM")
    ck.add("no_sigkill_escalation", no_sigkill(tr), True, no_sigkill(tr))
    status(ck, arm, nodes, "L", ("exit", 4))
    status(ck, arm, nodes, "E", ("exit", 5))
    all_gone(ck, tr)
    ck.eq("residual_empty_so_confirmed", tr["residual_after_t5"], [])
    collateral_checks(lab, arm, ck, ["L", "E"])


def t07(cross):
    def run(lab, arm, ck, rec):
        rec["purpose"] = ("re-parented LIVE descendant, leader already dead and polled once (%s). A true; escalate to the descendant"
                          % ("cross-session setsid descendant" if cross else "same group"))
        nodes = setup(lab, arm, {"name": "L", "exit_code": 0, "children": [{"name": "D", "term": "ignore", "setsid": cross}]}, "L")
        rec["topology"] = topo(nodes)
        lab.wait_state(nodes["D"], RUNNING)
        lab.go("L", "exit", 0)
        lab.wait_state(nodes["L"], ZOMBIE)
        wait_adopted_by_me(lab, nodes["D"])
        tr = lab.run_t3(arm, ["L", "D"], True, 0.3, pre_polls=1, kill_wait=1.0)
        rec["trace"] = tr
        bench_expect(tr, ALIVE)
        ck.eq("first_poll_tri", tr["first_tri"], ALIVE)
        ck.eq("decision", tr["decision"], "ESCALATED")
        ck.add("no_false_escalation", not tr.get("false_escalation"))
        ck.eq("tri_after_sigkill", tr.get("after_escalation_tri"), EXITED)
        status(ck, arm, nodes, "D", ("signal", 9))
        all_gone(ck, tr)
        collateral_checks(lab, arm, ck, ["L", "D"])
    return run


def _t08_common(lab, arm, ck, rec, tr, nodes, natural):
    rec["trace"] = tr
    ck.add("no_false_escalation (stable-exited target never escalated)", not tr.get("false_escalation"), False, tr.get("false_escalation"))
    ck.add("decision_is_defined", tr["decision"] in ("EARLY_CONFIRM", "CANCELLED_ESCALATION", "ESCALATED"), None, tr["decision"])
    ok, got = expected_status_ok(arm, nodes["R"], natural)
    sigkill_sent = any(s.get("stage") == "SIGKILL" and s.get("result") == "sent" for s in tr["signals"])
    if tr["decision"] == "ESCALATED" and sigkill_sent:
        ok2, got2 = expected_status_ok(arm, nodes["R"], ("signal", 9))
        ck.add("exit_status_present_and_legitimate", ok or ok2, "exit5 or signal9", got)
    else:
        ck.add("exit_status_natural_exit_preserved", ok, natural, got)
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["R"])


def t08a(lab, arm, ck, rec):
    rec["purpose"] = "SIGTERM makes the child exit well before the deadline (~50 ms vs 400 ms), not yet reaped: no SIGKILL"
    nodes = setup(lab, arm, {"name": "R", "term": "delay_exit:0.05:5"}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    tr = lab.run_t3(arm, ["R"], True, 0.4, kill_wait=1.0)
    _t08_common(lab, arm, ck, rec, tr, nodes, ("exit", 5))
    ck.add("no_sigkill_escalation", no_sigkill(tr), True, no_sigkill(tr))
    ck.eq("decision", tr["decision"], "EARLY_CONFIRM")


def t08b(lab, arm, ck, rec):
    jitter = random.uniform(-0.03, 0.03)
    rec["purpose"] = "SIGTERM-to-deadline race: child exits at deadline %+.3f s (grace 0.30 s)" % jitter
    rec["jitter_s"] = round(jitter, 4)
    nodes = setup(lab, arm, {"name": "R", "term": "delay_exit:%.4f:5" % (0.3 + jitter)}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    tr = lab.run_t3(arm, ["R"], True, 0.3, poll_dt=0.01, kill_wait=1.0)
    _t08_common(lab, arm, ck, rec, tr, nodes, ("exit", 5))
    rec["race_outcome"] = tr["decision"] + ("/FALSE" if tr.get("false_escalation") else "")


def t08c(lab, arm, ck, rec):
    rec["purpose"] = "deterministic race: target exits AFTER the final recheck and BEFORE the SIGKILL is sent"
    nodes = setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
    rec["topology"] = topo(nodes)
    R = nodes["R"]
    lab.wait_state(R, RUNNING)

    def hook(**kw):
        lab.go("R", "exit", 7)
        lab.wait_state(R, ZOMBIE)
    lab.hooks["after_recheck_before_signal"] = hook
    tr = lab.run_t3(arm, ["R"], True, 0.2, kill_wait=1.0)
    rec["trace"] = tr
    ck.eq("decision", tr["decision"], "ESCALATED")
    ck.add("escalation_not_false (target was RUNNING at the recheck)", not tr.get("false_escalation"))
    sk = [s for s in tr["signals"] if s.get("stage") == "SIGKILL"]
    ck.add("sigkill_result_harmless", all(s["result"] in ("skipped_already_exited", "sent", "gone") for s in sk), None, sk)
    status(ck, arm, nodes, "R", ("exit", 7))
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["R"])


def t09(lab, arm, ck, rec):
    rec["purpose"] = ("PID/PGID reuse protection (SIMULATED stale record): a registry entry whose fingerprint no longer matches the live "
                      "process behind that pid/pgid must never be signalled")
    nodes = setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
    BY = lab.spawn_detached("BY", term="ignore")
    rec["topology"] = topo(nodes)
    rec["bystander"] = {k: v for k, v in BY.items() if k != "pidfd"}
    lab.wait_state(nodes["R"], RUNNING)
    lab.wait_state(BY, RUNNING)
    if arm.baseline:
        arm.pgid = BY["pgrp"]          # stale pgid record now pointing at somebody else's group
        arm.last_A = True
        recs = arm.signal_alive(signal.SIGKILL)
        rec["attempt"] = recs
    else:
        st = L._oracle_stat(BY["pid"])
        stale = dict(st)
        stale["starttime"] = st["starttime"] - 7
        tg = Target(BY["pid"], stale, "injected_stale_record")
        arm.targets[BY["pid"]] = tg
        r1 = arm.signal_target(tg, signal.SIGKILL)
        rec["attempt_direct"] = r1
        ck.eq("direct_signal_refused", r1["result"], "refused_identity_mismatch")
        arm.fs = L.ProcFS()
        o = arm.poll()
        rec["poll_with_stale_entry"] = {"tri": o["tri"], "reasons": o["reasons"]}
        ck.add("stale_entry_is_UNKNOWN_not_ALIVE", arm.targets[BY["pid"]].state == UNKNOWN, UNKNOWN, arm.targets[BY["pid"]].state)
        recs = arm.signal_alive(signal.SIGKILL)
        rec["attempt_signal_alive"] = recs
        ck.add("no_signal_reached_bystander_record", all(r["pid"] != BY["pid"] for r in recs), True, recs)
    time.sleep(0.15)
    ck.eq("bystander_still_running", oracle_state(BY, timeout=1.0)[0], RUNNING)
    ck.add("sentinel_alive_and_untouched", lab.sentinel_ok())


def t10(lab, arm, ck, rec):
    rec["purpose"] = "never reap another process's exit status: a non-target child of the supervisor (decoy) exits while the arm polls and reaps"
    nodes = setup(lab, arm, {"name": "R", "exit_code": 0}, "R")
    Y = lab.spawn({"name": "Y", "exit_code": 9})["Y"]
    arm.register_aux(Y)
    rec["topology"] = topo(nodes)
    rec["decoy"] = {k: v for k, v in Y.items() if k != "pidfd"}
    lab.wait_state(nodes["R"], RUNNING)
    lab.wait_state(Y, RUNNING)
    lab.go("Y", "exit", 9)
    lab.wait_state(Y, ZOMBIE)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    st_y, ev_y = oracle_state(Y, timeout=1.0)
    rec["decoy_after_arm_run"] = {"state": st_y, "evidence": ev_y}
    ck.eq("decoy_still_unreaped_zombie", st_y, ZOMBIE)
    try:
        raw = os.waitpid(Y["pid"], os.WNOHANG)
        got = L.decode_status(raw[1]) if raw[0] == Y["pid"] else None
    except ChildProcessError:
        got = None
    ck.eq("decoy_exit_status_intact_when_bench_reaps", got, {"kind": "exit", "code": 9})
    ck.eq("first_poll_tri_for_stage", tr["first_tri"], EXITED)
    ck.add("no_signal_to_decoy", not any(s.get("pid") == Y["pid"] for s in arm.signal_log if "pid" in s))
    collateral_checks(lab, arm, ck, ["R"])


def _faulty(arm, **kw):
    arm.fs = FaultyProcFS(**kw)


def t11a1(lab, arm, ck, rec):
    rec["purpose"] = "SIMULATED: /proc cannot be listed; the only known target has exited -> UNKNOWN/BLOCKED, never EXITED, no signal"
    nodes = setup(lab, arm, {"name": "R", "exit_code": 0}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    _faulty(arm, listdir_errno=errno.EIO)
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.add("no_signals", not arm.signal_log, [], arm.signal_log)
    ck.add("not_confirmed (no EXITED claim)", tr["final_poll"] != EXITED, True, tr["final_poll"])
    collateral_checks(lab, arm, ck, [])


def t11a2(lab, arm, ck, rec):
    rec["purpose"] = "SIMULATED: /proc unreadable while the target is really RUNNING at the deadline -> no escalation, BLOCKED"
    nodes = setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    _faulty(arm, listdir_errno=errno.EIO)
    tr = lab.run_t3(arm, ["R"], False, 0.2, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.add("no_new_signals", no_sigkill(tr) and not arm.signal_log, [], arm.signal_log)
    collateral_checks(lab, arm, ck, [])


def _t11b(alive):
    def run(lab, arm, ck, rec):
        rec["purpose"] = ("SIMULATED: stat of ONE target unreadable (EACCES) while the rest are %s -> %s"
                          % ("one still RUNNING" if alive else "exited", "overall ALIVE, signals only to the verified live target" if alive else "UNKNOWN"))
        spec = {"name": "L", "term": "ignore", "exit_code": 0, "children": [{"name": "E", "exit_code": 0},
                                                                          {"name": "D", "term": "ignore", "exit_code": 0}]}
        nodes = setup(lab, arm, spec, "L")
        rec["topology"] = topo(nodes)
        lab.wait_state(nodes["D"], RUNNING)
        arm.poll()                       # registers the lineage with a clean /proc
        lab.go("E", "exit", 0)
        lab.wait_state(nodes["E"], ZOMBIE)
        if not alive:
            lab.go("D", "exit", 0)
            lab.wait_state(nodes["D"], ZOMBIE)
        lab.go("L", "exit", 0)
        lab.wait_state(nodes["L"], ZOMBIE)
        wait_adopted_by_me(lab, nodes["E"])
        _faulty(arm, stat_faults={nodes["E"]["pid"]: "EACCES"})
        tr = lab.run_t3(arm, ["L", "E", "D"], alive, 0.3, kill_wait=1.0)
        rec["trace"] = tr
        if alive:
            ck.eq("first_poll_tri", tr["first_tri"], ALIVE)
            ck.eq("decision", tr["decision"], "ESCALATED")
            eff = sorted({s.get("pid", -1) for s in tr["signals"] if s.get("result") in ("sent", "gone", "error")})
            ck.eq("signals_delivered_only_to_verified_live_target_D", eff, [nodes["D"]["pid"]])
            ck.eq("tri_after_sigkill (E still unreadable)", tr.get("after_escalation_tri"), UNKNOWN)
        else:
            ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
            ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
            ck.add("no_signals", not arm.signal_log, [], arm.signal_log)
        st_e = oracle_state(nodes["E"], timeout=1.0)[0]
        ck.eq("unreadable_target_E_not_reaped_by_guess", st_e, ZOMBIE)
        collateral_checks(lab, arm, ck, ["L", "E", "D"])
    return run


def t11c1(lab, arm, ck, rec):
    rec["purpose"] = "SIMULATED: the registered fingerprint no longer matches the live process -> identity unverified -> UNKNOWN, no signal"
    nodes = setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    if arm.baseline:
        ck.add("identity_verification_exists", False, True, "frozen R3 A has no fingerprint / identity check, so a stale record cannot be detected")
        return
    arm.targets[nodes["R"]["pid"]].starttime += 1
    tr = lab.run_t3(arm, ["R"], False, 0.2, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.add("no_signals", not arm.signal_log, [], arm.signal_log)
    ck.eq("target_still_running_untouched", oracle_state(nodes["R"], timeout=1.0)[0], RUNNING)
    collateral_checks(lab, arm, ck, [])


def t11c2(lab, arm, ck, rec):
    rec["purpose"] = "SIMULATED: ECHILD from waitpid/waitid on a registered unreaped child must NOT be read as 'exited' -> UNKNOWN"
    nodes = setup(lab, arm, {"name": "R", "exit_code": 0}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)

    def echild(*a, **k):
        raise ChildProcessError(errno.ECHILD, "injected")
    if isinstance(arm, L.ArmCA):
        arm.waitpid_fn = echild
    else:
        arm.waitid_fn = echild
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.add("not_confirmed", tr["final_poll"] != EXITED, True, tr["final_poll"])
    ck.add("no_signals", not arm.signal_log, [], arm.signal_log)
    collateral_checks(lab, arm, ck, [])


def t11c3(lab, arm, ck, rec):
    rec["purpose"] = "SIMULATED: garbled /proc/<pid>/stat for the target -> UNKNOWN"
    nodes = setup(lab, arm, {"name": "R", "exit_code": 0}, "R")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    _faulty(arm, stat_faults={nodes["R"]["pid"]: "garble"})
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.add("no_signals", not arm.signal_log, [], arm.signal_log)
    collateral_checks(lab, arm, ck, [])


def t11d1(lab, arm, ck, rec):
    rec["purpose"] = "SIMULATED: subreaper not verified (get returns 0); the only known target exited -> UNKNOWN (known exited != all exited)"
    if not arm.baseline:
        arm.get_subreaper = lambda: 0
    nodes = lab.spawn({"name": "R", "exit_code": 0})
    arm.register_root(nodes["R"])
    if not arm.baseline:
        rec["preflight"] = arm.preflight()
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["R"], RUNNING)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.add("no_signals", not arm.signal_log, [], arm.signal_log)
    collateral_checks(lab, arm, ck, [])


def t11d2(lab, arm, ck, rec):
    rec["purpose"] = ("an unregistered child of the supervisor (cannot be attributed; closed-world NOT declared) coexists with an exited known target "
                      "-> UNKNOWN; the stranger must be neither signalled nor reaped")
    arm.cw_declared = False
    nodes = setup(lab, arm, {"name": "R", "exit_code": 0}, "R")
    M = lab.spawn({"name": "M", "term": "ignore"})["M"]
    rec["topology"] = topo(nodes)
    rec["stranger"] = {k: v for k, v in M.items() if k != "pidfd"}
    lab.wait_state(nodes["R"], RUNNING)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], UNKNOWN)
    ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
    ck.eq("stranger_untouched_running", oracle_state(M, timeout=1.0)[0], RUNNING)
    ck.add("no_signals", not arm.signal_log and no_sigkill(tr), [], arm.signal_log)
    collateral_checks(lab, arm, ck, [])


def t11e(lab, arm, ck, rec):
    rec["purpose"] = ("boundary (must NOT be over-conservative): a fingerprint-verified non-child descendant is reaped by its own parent and vanishes "
                      "from /proc; with every other target exited this is EXITED")
    nodes = setup(lab, arm, {"name": "L", "term": "ignore", "exit_code": 0, "children": [{"name": "G", "exit_code": 0}]}, "L")
    rec["topology"] = topo(nodes)
    lab.wait_state(nodes["G"], RUNNING)
    o0 = arm.poll()
    rec["poll0_registers_G"] = {"tri": o0["tri"], "targets": o0.get("targets")}
    lab.go("G", "exit", 0)
    lab.wait_state(nodes["G"], ZOMBIE)
    lab.go("L", "reap", 0)
    lab.wait_state(nodes["G"], GONE)
    lab.go("L", "exit", 0)
    lab.wait_state(nodes["L"], ZOMBIE)
    tr = lab.run_t3(arm, ["L", "G"], False, 0.3, kill_wait=0.5)
    rec["trace"] = tr
    bench_expect(tr, EXITED)
    ck.eq("first_poll_tri", tr["first_tri"], EXITED)
    ck.eq("decision", tr["decision"], "EARLY_CONFIRM")
    ck.add("no_signals", not arm.signal_log and no_sigkill(tr), [], arm.signal_log)
    if not arm.baseline:
        ck.eq("G_reason", tr["polls"][0]["targets"].get(str(nodes["G"]["pid"]), {}).get("reason"), "vanished_after_verified_fingerprint")
    collateral_checks(lab, arm, ck, ["L", "G"])


def t14a(lab, arm, ck, rec):
    rec["purpose"] = "TOCTOU: fingerprint correct, target (direct child) exits just before the signal; 'sent' must not be read as 'killed'"
    nodes = setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
    rec["topology"] = topo(nodes)
    R = nodes["R"]
    lab.wait_state(R, RUNNING)
    o = arm.poll()
    ck.eq("poll_before_race", o["tri"], ALIVE)

    def hook(**kw):
        lab.go("R", "exit", 7)
        lab.wait_state(R, ZOMBIE)
    lab.hooks["after_fingerprint_before_signal"] = hook
    recs = arm.signal_alive(signal.SIGKILL)
    rec["signal_records"] = recs
    lab.hooks.clear()
    ck.add("signal_result_harmless", all(r["result"] in ("sent", "gone") for r in recs), None, recs)
    t5 = None
    tr = lab.run_t3(arm, ["R"], False, 0.2, kill_wait=0.5)
    rec["trace"] = tr
    ck.eq("tri_after", tr["first_tri"], EXITED)
    status(ck, arm, nodes, "R", ("exit", 7))
    all_gone(ck, tr)
    collateral_checks(lab, arm, ck, ["R"])


def t14b(lab, arm, ck, rec):
    rec["purpose"] = ("TOCTOU: a non-child descendant is reaped by ITS parent between the fingerprint check and the signal; "
                      "pidfd must report ESRCH ('gone'), the signal can reach nobody else")
    nodes = setup(lab, arm, {"name": "L", "term": "ignore", "children": [{"name": "G", "term": "ignore"}]}, "L")
    rec["topology"] = topo(nodes)
    G = nodes["G"]
    lab.wait_state(G, RUNNING)
    o = arm.poll()
    ck.eq("poll_before_race", o["tri"], ALIVE)
    fired = {"n": 0}

    def hook(tg=None, **kw):
        if fired["n"] or (tg is not None and tg.pid != G["pid"]):
            return
        fired["n"] += 1
        lab.kill_by_bench(G, signal.SIGKILL)
        lab.wait_state(G, ZOMBIE)
        lab.go("L", "reap", 0)
        lab.wait_state(G, GONE)
    lab.hooks["after_fingerprint_before_signal"] = hook
    if arm.baseline:
        recs = arm.signal_alive(signal.SIGKILL)
    else:
        recs = [arm.signal_target(arm.targets[G["pid"]], signal.SIGKILL)]
        ck.eq("G_signal_result_is_gone (pidfd ESRCH)", recs[0]["result"], "gone")
        ck.eq("hook_fired_after_fingerprint_check", fired["n"], 1)
        recs += arm.signal_alive(signal.SIGKILL)         # now the live leader
        lab.wait_state(nodes["L"], ZOMBIE)
    lab.hooks.clear()
    rec["signal_records"] = recs
    tr = lab.run_t3(arm, ["L", "G"], False, 0.3, kill_wait=0.8)
    rec["trace"] = tr
    ck.eq("final_tri", tr["first_tri"], EXITED)
    all_gone(ck, tr, ["G"])
    collateral_checks(lab, arm, ck, ["L", "G"])


def t14c(lab, arm, ck, rec):
    rec["purpose"] = ("TEST-BENCH ONLY (no arm): (i) a naive 'check fingerprint then os.kill(pid)' implementation is exposed to substitution after the "
                      "check (SIMULATED by swapping the pid for a sacrificial bystander); (ii) pidfd semantics: a pidfd opened for a process that "
                      "later exits and is reaped answers ESRCH, a zombie accepts the signal without effect. Real kernel pid reuse is NOT tested.")
    nodes = lab.spawn({"name": "T", "term": "ignore"})
    BY1 = lab.spawn_detached("BY1", term="ignore")
    T = nodes["T"]
    lab.wait_state(T, RUNNING)
    lab.wait_state(BY1, RUNNING)
    st = L._oracle_stat(T["pid"])
    fp_ok = st["starttime"] == T["starttime"]
    pid_after_swap = BY1["pid"]                    # simulated substitution after the check
    os.kill(pid_after_swap, signal.SIGKILL)
    time.sleep(0.2)
    rec["naive_path"] = {"fingerprint_check_passed": fp_ok, "bystander_state_after_naive_kill": oracle_state(BY1, timeout=1.0)[0]}
    ck.add("(demonstration) naive path can hit the substituted process", rec["naive_path"]["bystander_state_after_naive_kill"] != RUNNING,
           "bystander not RUNNING", rec["naive_path"])
    # (ii) pidfd semantics on a bench-owned target
    pfd = os.pidfd_open(T["pid"])
    lab.kill_by_bench(T, signal.SIGKILL)
    lab.wait_state(T, ZOMBIE)
    try:
        signal.pidfd_send_signal(pfd, signal.SIGKILL)
        zres = "accepted_by_zombie_without_effect"
    except ProcessLookupError:
        zres = "ESRCH"
    os.waitpid(T["pid"], 0)
    try:
        signal.pidfd_send_signal(pfd, signal.SIGKILL)
        rres = "sent"
    except ProcessLookupError:
        rres = "ESRCH"
    os.close(pfd)
    rec["pidfd_semantics"] = {"signal_to_zombie_via_pidfd": zres, "signal_to_reaped_via_pidfd": rres}
    ck.eq("pidfd_zombie_result", zres, "accepted_by_zombie_without_effect")
    ck.eq("pidfd_reaped_result", rres, "ESRCH")
    ck.add("sentinel_alive_and_untouched", lab.sentinel_ok())


# (id, function, race?, arms, description)
CASES = [
    ("T-01", t01, False, "all"), ("T-02a", t02a, False, "all"), ("T-02b", t02b, False, "all"), ("T-03", t03, False, "all"),
    ("T-04", t04, False, "all"), ("T-04b-A1", t04b(False), False, "all"), ("T-04b-A2", t04b(True), False, "all"),
    ("T-05", t05, False, "all"), ("T-06", t06, False, "all"), ("T-07a", t07(False), False, "all"), ("T-07b", t07(True), False, "all"),
    ("T-08a", t08a, True, "all"), ("T-08b", t08b, True, "all"), ("T-08c", t08c, True, "all"),
    ("T-09", t09, False, "all"), ("T-10", t10, False, "all"),
    ("T-11a1", t11a1, False, "all"), ("T-11a2", t11a2, False, "all"), ("T-11b1", _t11b(False), False, "all"), ("T-11b2", _t11b(True), False, "all"),
    ("T-11c1", t11c1, False, "all"), ("T-11c2", t11c2, False, "ca_cb"), ("T-11c3", t11c3, False, "all"),
    ("T-11d1", t11d1, False, "all"), ("T-11d2", t11d2, False, "all"), ("T-11e", t11e, False, "all"),
    ("T-14a", t14a, True, "all"), ("T-14b", t14b, True, "all"), ("T-14c", t14c, True, "bench"),
]
ARM_ORDER = ["B0-NOREAP", "B0-EVAL_THEN_REAP", "B0-REAP_THEN_EVAL", "CA", "CB"]


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    except Exception as e:
        return "unavailable: %s" % e


def environment(lab):
    anc, p = [], os.getpid()
    while p > 1 and len(anc) < 12:
        st = L._oracle_stat(p)
        try:
            comm = open("/proc/%d/comm" % p).read().strip()
        except OSError:
            comm = "?"
        anc.append({"pid": p, "comm": comm})
        p = st["ppid"] if st else 1
    return {"kernel": platform.release(), "platform": platform.platform(), "python": sys.version, "machine": platform.machine(),
            "git_branch": sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]), "git_commit": sh(["git", "rev-parse", "HEAD"]),
            "git_status_short": sh(["git", "status", "--short"]), "uid": os.getuid(), "euid": os.geteuid(),
            "supervisor_pid": os.getpid(), "supervisor_pgid": os.getpgrp(), "ancestors": anc, "token": L.TOKEN,
            "os.pidfd_open": hasattr(os, "pidfd_open"), "signal.pidfd_send_signal": hasattr(signal, "pidfd_send_signal"),
            "os.waitid": hasattr(os, "waitid"), "os.WNOWAIT": hasattr(os, "WNOWAIT"),
            "prctl_get_subreaper_initial": L.prctl_get_subreaper(), "subreaper_log": lab.subreaper_log,
            "cpu_count": os.cpu_count(), "clk_tck": os.sysconf("SC_CLK_TCK")}


def run_one(lab, cid, fn, armname, rep):
    lab.begin()
    rec = {"case": cid, "arm": armname, "repeat": rep, "supervisor_pid": os.getpid()}
    ck = Checker()
    t0 = L.now()
    try:
        arm = ARMS[armname](lab) if armname in ARMS else None
        fn(lab, arm, ck, rec)
        finish_record(rec, ck)
        rec["tool_ok"] = True
    except Blocked as e:
        rec["status"], rec["blocked_reason"], rec["tool_ok"] = BLOCKED, str(e), False
        rec["checks"] = ck.checks
    except SafetyError as e:
        rec["status"], rec["blocked_reason"], rec["tool_ok"] = BLOCKED, "SAFETY: " + str(e), False
        rec["checks"] = ck.checks
    except Exception as e:
        rec["status"], rec["blocked_reason"], rec["tool_ok"] = BLOCKED, "tool exception: %r" % e, False
        rec["traceback"] = traceback.format_exc()
        rec["checks"] = ck.checks
    finally:
        try:
            lab.set_subreaper(True)
        except Exception:
            pass
        rec["cleanup"] = lab.cleanup()
    rec["elapsed_s"] = round(L.now() - t0, 3)
    cl = rec["cleanup"]
    rec["cleanup_clean"] = not (cl["residual_nodes"] or cl["token_scan_pids"] or cl["children_of_supervisor"])
    return rec


def summarize(results, arms):
    cases = []
    for cid, _, _, _ in CASES:
        cases.append(cid)
    matrix = {}
    for cid in cases:
        for a in arms + ["BENCH"]:
            rs = [r for r in results if r["case"] == cid and r["arm"] == a]
            if not rs:
                continue
            n = {PASS: 0, FAIL: 0, BLOCKED: 0}
            for r in rs:
                n[r["status"]] += 1
            if n[FAIL]:
                v = FAIL
            elif n[BLOCKED]:
                v = BLOCKED
            else:
                v = PASS
            fails = {}
            for r in rs:
                for c in r.get("failed_checks", []):
                    fails[c] = fails.get(c, 0) + 1
            blk = sorted({r.get("blocked_reason", "")[:120] for r in rs if r["status"] == BLOCKED})
            matrix.setdefault(cid, {})[a] = {"verdict": v, "counts": n, "runs": len(rs), "failed_checks": fails, "blocked": blk}
    return matrix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--race-repeat", type=int, default=50)
    ap.add_argument("--only", default=None, help="comma separated case ids")
    ap.add_argument("--arms", default=",".join(ARM_ORDER))
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=20261027)
    a = ap.parse_args()
    random.seed(a.seed)
    lab = L.Lab()
    results, run_error = [], None
    try:
        lab.set_subreaper(False)           # the sentinel must be adopted by a process outside this supervisor
        lab.start_sentinel()
        lab.set_subreaper(True)
        env = environment(lab)
        env["sentinel"] = {k: v for k, v in lab.sentinel.items() if k != "pidfd"}
        arms = [x for x in a.arms.split(",") if x]
        only = set(a.only.split(",")) if a.only else None
        for cid, fn, race, which in CASES:
            if only and cid not in only:
                continue
            reps = a.race_repeat if race else a.repeat
            targets = ["BENCH"] if which == "bench" else (["CA", "CB"] if which == "ca_cb" else arms)
            targets = [t for t in targets if t == "BENCH" or t in arms]
            for armname in targets:
                for rep in range(1, reps + 1):
                    r = run_one(lab, cid, fn, armname, rep)
                    results.append(r)
                    if not lab.sentinel_ok():
                        raise RuntimeError("sentinel was disturbed during %s/%s/%d -- stopping" % (cid, armname, rep))
                print("%-9s %-18s %s" % (cid, armname, {s: sum(1 for r in results if r["case"] == cid and r["arm"] == armname and r["status"] == s) for s in (PASS, FAIL, BLOCKED)}), flush=True)
    except Exception as e:
        run_error = "%r\n%s" % (e, traceback.format_exc())
        print("RUN ERROR", run_error, file=sys.stderr)
    finally:
        fin = lab.final_cleanup()
    out = {"experiment": "F3B-D1-A-CPU-001", "environment": env if 'env' in dir() else None, "args": vars(a), "results": results,
           "matrix": summarize(results, [x for x in a.arms.split(",") if x]), "final_cleanup": fin, "run_error": run_error,
           "cleanup_unclean_runs": [(r["case"], r["arm"], r["repeat"]) for r in results if not r["cleanup_clean"]],
           "tool_not_ok_runs": [(r["case"], r["arm"], r["repeat"], r.get("blocked_reason")) for r in results if not r["tool_ok"]]}
    text = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n"
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    print(json.dumps({"matrix": {c: {k: v["verdict"] for k, v in d.items()} for c, d in out["matrix"].items()},
                      "unclean": out["cleanup_unclean_runs"][:5], "tool_not_ok": len(out["tool_not_ok_runs"]), "run_error": bool(run_error)}, indent=1))


if __name__ == "__main__":
    main()
