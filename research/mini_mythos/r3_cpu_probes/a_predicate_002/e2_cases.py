#!/usr/bin/env python3
"""F3B-D1-A-CPU-002 -- E1 (attribution safety), E2 (CA vs subprocess.Popen), E3 (CB without T5).  Criteria are the ones
pre-registered in docs/F3B_D1_A_CPU_002_PLAN_20261027.md; they are not adjusted after the fact.
Every record carries evidence_kind in {REAL_KERNEL, SIMULATED, INSTRUMENTED}."""
import argparse
import errno
import gc
import json
import os
import random
import signal
import subprocess
import sys
import threading
import time
import traceback
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "a_predicate"))
import e2_lab as E
import a_lab as L
import a_cases as C
from a_lab import ALIVE, EXITED, UNKNOWN, RUNNING, ZOMBIE, GONE, PASS, FAIL, BLOCKED, Blocked, Checker, oracle_state
from e2_lab import SpawnLab, ARMS2, run_in_fresh_session

ORIG = ("CA", "CB")
STRICT = ("CA-S", "CB-S")
E1_ARMS = list(ORIG + STRICT)


def nt_checks(lab, arm, ck, nontargets, expect, tag=""):
    """K1 zero-kill, K2 zero-reap on the bench-created non-target nodes (name -> node)."""
    ids = {(n["pid"], n["starttime"]): name for name, n in nontargets.items()}
    sent = [s for s in arm.signal_log if s.get("result") in ("sent", "gone", "error") and (s.get("pid"), s.get("starttime")) in ids]
    ck.add("K1_no_signal_delivered_to_non_target" + tag, not sent, [], sent)
    pids = {n["pid"] for n in nontargets.values()}
    badw = [w for w in arm.wait_calls if w["pid"] in pids]
    ck.add("K2_no_wait_call_on_non_target" + tag, not badw, [], badw)
    for name, want in expect.items():
        ck.eq("K_non_target_final_state:%s%s" % (name, tag), oracle_state(nontargets[name], timeout=1.0)[0], want)


def sigkill_delivered_pids(tr):
    return sorted({s.get("pid") for s in tr["signals"] if s.get("stage") == "SIGKILL" and s.get("result") in ("sent", "gone", "error")})


# ============================================================ E1
def e1_p1(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E1-P1 positive control: setsid descendant registered before its parent dies (continuity)")
    nodes = C.setup(lab, arm, {"name": "R", "term": "ignore", "children": [{"name": "Cc", "setsid": True, "term": "ignore"}]}, "R")
    rec["topology"] = C.topo(nodes)
    lab.wait_state(nodes["Cc"], RUNNING)
    arm.poll()
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    C.wait_adopted_by_me(lab, nodes["Cc"])
    tr = lab.run_t3(arm, ["R", "Cc"], True, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    ck.eq("first_poll_tri", tr["first_tri"], ALIVE)
    ck.eq("decision", tr["decision"], "ESCALATED")
    ck.eq("sigkill_delivered_only_to_C", sigkill_delivered_pids(tr), [nodes["Cc"]["pid"]])
    ck.eq("tri_after_sigkill", tr.get("after_escalation_tri"), EXITED)
    C.status(ck, arm, nodes, "Cc", ("signal", 9))
    C.status(ck, arm, nodes, "R", ("exit", 0))
    C.all_gone(ck, tr)
    nt_checks(lab, arm, ck, {}, {})


def e1_p2(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E1-P2 late first poll: descendant orphaned before it was ever registered. Safe = attributed and killed correctly, OR UNKNOWN with no signal")
    nodes = C.setup(lab, arm, {"name": "R", "term": "ignore", "children": [{"name": "Cc", "setsid": True, "term": "ignore"}]}, "R")
    rec["topology"] = C.topo(nodes)
    lab.wait_state(nodes["Cc"], RUNNING)
    lab.go("R", "exit", 0)
    lab.wait_state(nodes["R"], ZOMBIE)
    C.wait_adopted_by_me(lab, nodes["Cc"])
    tr = lab.run_t3(arm, ["R", "Cc"], True, 0.3, kill_wait=1.0)
    rec["trace"] = tr
    ft = tr["first_tri"]
    rec["outcome"] = "attributed" if ft == ALIVE else ft
    ck.add("first_poll_tri_is_a_safe_outcome (ALIVE or UNKNOWN, never EXITED)", ft in (ALIVE, UNKNOWN), "ALIVE|UNKNOWN", ft)
    if ft == ALIVE:
        ck.eq("decision", tr["decision"], "ESCALATED")
        ck.eq("sigkill_delivered_only_to_C", sigkill_delivered_pids(tr), [nodes["Cc"]["pid"]])
        C.status(ck, arm, nodes, "Cc", ("signal", 9))
    else:
        ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
        ck.add("no_signal_delivered", not [s for s in arm.signal_log if s.get("result") in ("sent", "gone", "error")], [], arm.signal_log)
        ck.eq("C_untouched", oracle_state(nodes["Cc"], timeout=1.0)[0], RUNNING)
    nt_checks(lab, arm, ck, {}, {})


def e1_p3(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E1-P3 sid_hint positive control: subreaper OFF, same-session descendant adopted by pid 1, stage root leads a dedicated session")
    lab.set_subreaper(False)
    try:
        nodes = lab.spawn({"name": "R", "term": "ignore", "children": [{"name": "D", "term": "ignore"}]})
        arm.register_root(nodes["R"])
        rec["preflight"] = arm.preflight(setter=lambda flag: False)
        rec["topology"] = C.topo(nodes)
        lab.wait_state(nodes["D"], RUNNING)
        lab.go("R", "exit", 0)
        lab.wait_state(nodes["R"], ZOMBIE)
        end = L.now() + 3
        while L.now() < end and L._oracle_stat(nodes["D"]["pid"])["ppid"] == nodes["R"]["pid"]:
            time.sleep(0.003)
        rec["D_ppid_after_leader_exit"] = L._oracle_stat(nodes["D"]["pid"])["ppid"]
        tr = lab.run_t3(arm, ["R", "D"], True, 0.3, kill_wait=1.0)
        rec["trace"] = tr
        ck.eq("first_poll_tri (sid_hint finds D)", tr["first_tri"], ALIVE)
        ck.eq("decision", tr["decision"], "ESCALATED")
        ck.eq("sigkill_delivered_only_to_D", sigkill_delivered_pids(tr), [nodes["D"]["pid"]])
        rec["D_attribution"] = [t.how for t in arm.targets.values() if t.pid == nodes["D"]["pid"]]
        C.status(ck, arm, nodes, "R", ("exit", 0))
        nt_checks(lab, arm, ck, {}, {})
    finally:
        lab.set_subreaper(True)


def _aux_nodes(lab, arm, killY_before_poll=None):
    pass


def e1_a(variant):
    def run(lab, arm, ck, rec):
        desc = {"a1": "aux Y with child YC alive; stage exited -> EXITED, aux family untouched",
                "a2": "aux Y dies AFTER its child was registered as aux family; YC re-parented to the supervisor. Safe = EXITED (aux_family) or UNKNOWN",
                "a3": "aux Y dies BEFORE any poll; YC re-parented, created after the stage root. Must be UNKNOWN"}[variant]
        rec.update(evidence_kind="REAL_KERNEL", purpose="E1-%s %s" % (variant.upper(), desc))
        R = C.setup(lab, arm, {"name": "R", "exit_code": 0}, "R")["R"]
        yn = lab.spawn({"name": "Y", "term": "ignore", "exit_code": 9, "children": [{"name": "YC", "term": "ignore"}]})
        Y, YC = yn["Y"], yn["YC"]
        arm.register_aux(Y)
        rec["topology"] = C.topo({"R": R, "Y": Y, "YC": YC})
        lab.wait_state(R, RUNNING)
        lab.wait_state(YC, RUNNING)
        if variant in ("a1", "a2"):
            arm.poll()
        if variant in ("a2", "a3"):
            lab.kill_by_bench(Y, signal.SIGKILL)
            lab.wait_state(Y, ZOMBIE)
            C.wait_adopted_by_me(lab, YC)
        lab.go("R", "exit", 0)
        lab.wait_state(R, ZOMBIE)
        tr = lab.run_t3(arm, ["R"], False, 0.3, kill_wait=0.5)
        rec["trace"] = tr
        ft = tr["first_tri"]
        rec["outcome"] = ft
        if variant == "a1":
            ck.eq("first_poll_tri", ft, EXITED)
            ck.eq("decision", tr["decision"], "EARLY_CONFIRM")
            ck.eq("Y_alive", oracle_state(Y, timeout=1.0)[0], RUNNING)
        elif variant == "a2":
            ck.add("first_poll_tri_is_safe (EXITED or UNKNOWN)", ft in (EXITED, UNKNOWN), "EXITED|UNKNOWN", ft)
        else:
            ck.eq("first_poll_tri (cannot attribute YC)", ft, UNKNOWN)
            ck.eq("decision", tr["decision"], "BLOCKED_UNKNOWN")
        ck.add("no_signal_delivered", not [s for s in arm.signal_log if s.get("result") in ("sent", "gone", "error")], [], arm.signal_log)
        exp = {"YC": RUNNING}
        exp["Y"] = RUNNING if variant == "a1" else ZOMBIE
        nt_checks(lab, arm, ck, {"Y": Y, "YC": YC}, exp)
    return run


def e1_x(variant):
    def run(lab, arm, ck, rec):
        desc = {"x1a": "assertion violated: unrelated RUNNING child X created BEFORE the stage root (cw_declared=True, no aux)",
                "x1z": "assertion violated: unrelated EXITED-unreaped child X (code 9) created BEFORE the stage root",
                "x2": "assertion violated: unrelated RUNNING child X created AFTER the stage root (cannot be told from a real orphan)"}[variant]
        rec.update(evidence_kind="REAL_KERNEL", purpose="E1-%s %s" % (variant.upper(), desc))
        arm.cw_declared = True
        if variant in ("x1a", "x1z"):
            X = lab.spawn({"name": "X", "term": "ignore", "exit_code": 9})["X"]
        nodes = C.setup(lab, arm, {"name": "R", "term": "ignore"}, "R")
        if variant == "x2":
            time.sleep(0.05)
            X = lab.spawn({"name": "X", "term": "ignore", "exit_code": 9})["X"]
        rec["topology"] = C.topo({"R": nodes["R"], "X": X})
        rec["X_starttime_after_root"] = X["starttime"] > nodes["R"]["starttime"]
        lab.wait_state(X, RUNNING)
        lab.wait_state(nodes["R"], RUNNING)
        if variant == "x1z":
            lab.go("X", "exit", 9)
            lab.wait_state(X, ZOMBIE)
        tr = lab.run_t3(arm, ["R"], True, 0.3, kill_wait=1.0)
        rec["trace"] = tr
        rec["attributed_X"] = [t.how for t in arm.targets.values() if t.pid == X["pid"]]
        ck.eq("R_is_terminated", tr["truth_final"]["R"], GONE)
        ck.add("R_was_signalled", any(s.get("pid") == nodes["R"]["pid"] and s.get("result") == "sent" for s in tr["signals"]), True, tr["signals"])
        if variant == "x2":
            ck.add("final_state_is_UNKNOWN_or_X_excluded_never_a_confirmed_EXITED_claim_on_X",
                   arm.last_obs["tri"] in (UNKNOWN, EXITED) and (arm.last_obs["tri"] == UNKNOWN or arm.last_obs["targets"].get(str(X["pid"])) is None),
                   "UNKNOWN or X not a target", {"tri": arm.last_obs["tri"], "X_target": str(X["pid"]) in arm.last_obs["targets"]})
        exp = {"X": ZOMBIE if variant == "x1z" else RUNNING}
        nt_checks(lab, arm, ck, {"X": X}, exp)
        if variant == "x1z":
            try:
                r = os.waitid(os.P_PID, X["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT)
                got = {"kind": "exit", "code": r.si_status} if r is not None else None
            except ChildProcessError:
                got = None
            ck.eq("X_exit_status_still_readable_by_bench", got, {"kind": "exit", "code": 9})
    return run


def e1_s1(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E1-S1 can a non-stage process be in the stage's session? setpgid() across sessions; session members vs lineage")
    nodes = lab.spawn({"name": "R", "term": "ignore", "children": [{"name": "Cc", "term": "ignore"}, {"name": "Ee", "setsid": True, "term": "ignore"}]})
    B = lab.spawn({"name": "B", "term": "ignore"}, new_session=False)["B"]
    R = nodes["R"]
    rec["topology"] = C.topo(dict(nodes, B=B))
    members = sorted(int(d) for d in os.listdir("/proc") if d.isdigit() and (L._oracle_stat(int(d)) or {}).get("sid") == R["sid"])
    ck.eq("members_of_stage_session_are_exactly_R_and_its_same_session_descendant", members, sorted([R["pid"], nodes["Cc"]["pid"]]))
    ck.add("setsid_descendant_is_NOT_in_the_stage_session", nodes["Ee"]["sid"] != R["sid"], True, nodes["Ee"]["sid"])
    ck.add("bystander_B_shares_the_supervisors_session_not_the_stage_session", B["sid"] == os.getsid(0) and B["sid"] != R["sid"], True, {"B_sid": B["sid"], "sup_sid": os.getsid(0)})
    res_exec = "success"
    try:
        os.setpgid(B["pid"], R["pgrp"])           # B has already exec'd: the kernel answers EACCES before it looks at sessions
    except OSError as e:
        res_exec = errno.errorcode.get(e.errno, str(e.errno))
    rec["v1_method_setpgid_on_exec_child_observation_only"] = res_exec
    r_, w_ = os.pipe()
    cpid = os.fork()                               # a child that has NOT exec'd, in the supervisor's session
    if cpid == 0:
        msg = "success"
        try:
            os.setpgid(0, R["pgrp"])
        except OSError as e:
            msg = errno.errorcode.get(e.errno, str(e.errno))
        os.write(w_, msg.encode())
        os._exit(0)
    os.close(w_)
    res = os.read(r_, 64).decode()
    os.close(r_)
    os.waitpid(cpid, 0)
    rec["setpgid_unexec_child_into_stage_group"] = res
    ck.eq("kernel_refuses_moving_a_process_into_another_session (v2 method)", res, "EPERM")
    st = L._oracle_stat(B["pid"])
    ck.add("B_still_outside_stage_group", st["pgrp"] != R["pgrp"], True, st["pgrp"])


def e1_s2(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose=("E1-S2 MIS-CONFIGURED stage: root R is NOT a session leader (shares the supervisor's session), an unrelated non-child X sits in the same "
                                                    "session. Run inside a dedicated fresh session so only sacrificial processes can be touched"))
    name = arm.name

    def body(lab2):
        ck2, rec2 = Checker(), {}
        lab2.sentinel = lab.sentinel
        lab2.set_subreaper(True)
        arm2 = ARMS2[name](lab2)
        R = lab2.spawn({"name": "R", "term": "ignore"}, new_session=False)["R"]
        X = lab2.spawn_detached("X", term="ignore", new_session=False)
        mysid = os.getsid(0)
        rec2["topology"] = {"R": {k: v for k, v in R.items() if k != "pidfd"}, "X": {k: v for k, v in X.items() if k != "pidfd"}, "supervisor_sid": mysid, "supervisor_pid": os.getpid()}
        if not (R["sid"] == mysid and X["sid"] == mysid and R["sid"] != R["pid"]):
            raise Blocked("bench could not build the mis-configured topology")
        st = L._oracle_stat(X["pid"])
        rec2["X_ppid"] = st["ppid"]
        ck2.add("X_is_not_a_child_of_the_supervisor", st["ppid"] != os.getpid(), True, st["ppid"])
        arm2.register_root(R)
        pf = arm2.preflight()
        rec2["preflight"] = pf
        if getattr(arm2, "strict", False):
            ck2.eq("S0_blocks_non_dedicated_session", (pf["status"], pf.get("code")), ("BLOCKED", "STAGE_SESSION_NOT_DEDICATED"))
        lab2.wait_state(X, RUNNING)
        tr = lab2.run_t3(arm2, ["R"], True, 0.3, kill_wait=1.0)
        rec2["trace"] = tr
        rec2["X_attribution"] = [t.how for t in arm2.targets.values() if t.pid == X["pid"]]
        nt_checks(lab2, arm2, ck2, {"X": X}, {"X": RUNNING})
        return {"checks": ck2.checks, "rec": rec2}
    res = run_in_fresh_session(body)
    ck.checks.extend(res["checks"])
    rec.update(res["rec"])
    rec["fresh_session_cleanup"] = res["fresh_session_cleanup"]
    cl = res["fresh_session_cleanup"]
    if cl["residual_nodes"] or cl["token_scan_pids"]:
        raise Blocked("fresh session left residue: %s" % cl)


# ============================================================ E2
CHILD = ("import os,sys,time\n"
         "ctl,mode,code=sys.argv[1],sys.argv[2],int(sys.argv[3])\n"
         "while True:\n"
         "    if mode=='exit' and os.path.exists(os.path.join(ctl,'go')): sys.exit(code)\n"
         "    time.sleep(0.002)\n")


def popen_stage(lab, mode, code=0):
    p = subprocess.Popen([sys.executable, "-S", "-c", CHILD, lab.ctl, mode, str(code), L.TOKEN], start_new_session=True)
    end = L.now() + 5
    while L.now() < end:
        try:
            with open("/proc/%d/cmdline" % p.pid, "rb") as f:
                if L.TOKEN.encode() in f.read():
                    break
        except OSError:
            pass
        time.sleep(0.002)
    st = L._oracle_stat(p.pid)
    node = {"name": "P", "pid": p.pid, "starttime": st["starttime"], "sid": st["sid"], "pgrp": st["pgrp"], "ppid": st["ppid"], "pidfd": os.pidfd_open(p.pid)}
    lab.nodes.append(node)
    lab.allowed_pgids.add(node["pgrp"])
    return p, node


def lab_go(lab):
    with open(os.path.join(lab.ctl, "go"), "w") as f:
        f.write("1")


def truth_rc(truth):
    return truth[1] if truth[0] == "exit" else -truth[1]


def e2_0(kind):
    def run(lab, arm, ck, rec):
        rec.update(evidence_kind="REAL_KERNEL", purpose="E2-00 control: Popen alone (validity of the Popen/Python side)")
        p, node = popen_stage(lab, "exit" if kind == "exit7" else "sleep", 7)
        if kind == "exit7":
            lab_go(lab); want = 7
        elif kind == "sigkill":
            lab.kill_by_bench(node, signal.SIGKILL); want = -9
        else:
            os.kill(p.pid, signal.SIGTERM); want = -15
        rc = p.wait(timeout=10)
        rec["popen_wait"] = rc
        ck.eq("popen_wait_returncode", rc, want)
    return run


def e2_basic(kind):
    def run(lab, arm, ck, rec):
        rec.update(evidence_kind="REAL_KERNEL", purpose="E2 %s: arm reaps first, Popen reads later; CA record and Popen state checked separately" % kind)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            p, node = popen_stage(lab, "exit" if kind == "exit7" else "sleep", 7)
            arm.register_root(node)
            if isinstance(arm, E2ARMP):
                arm.popens[p.pid] = p
            arm.preflight()
            rec["popen_returncode_before"] = p.returncode
            if kind == "exit7":
                lab_go(lab); truth = ("exit", 7)
            elif kind == "sigkill":
                lab.kill_by_bench(node, signal.SIGKILL); truth = ("signal", 9)
            else:
                recs = arm.signal_alive(signal.SIGTERM)
                rec["sigterm_records"] = recs
                ck.eq("arm_sigterm_result", recs[0]["result"], "sent")
                truth = ("signal", 15)
            lab.wait_state(node, ZOMBIE)
            o = arm.poll()
            rec["arm_poll_tri"] = o["tri"]
            arm_status = arm.exit_status(p.pid)
            rec["ca_record"] = arm_status
            rec["popen_returncode_after_arm_poll_attribute"] = p.returncode
            rc_poll = p.poll()
            rc_wait = p.wait(timeout=10)
            rec.update(popen_poll=rc_poll, popen_wait=rc_wait)
            try:
                os.waitid(os.P_PID, p.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                second_copy = "waitid_found_a_status"
            except ChildProcessError:
                second_copy = "ECHILD"
            rec["kernel_second_status_copy"] = second_copy
            del p
            gc.collect()
        want_rec = {"kind": truth[0], ("code" if truth[0] == "exit" else "sig"): truth[1]}
        got = {k: v for k, v in (arm_status or {}).items() if k in ("kind", "code", "sig")}
        ck.eq("C1_arm_record_equals_truth", got, want_rec)
        ck.eq("C2_popen_returncode_equals_truth_after_poll", rc_poll, truth_rc(truth))
        ck.eq("C2_popen_returncode_equals_truth_after_wait", rc_wait, truth_rc(truth))
        ck.eq("C3_no_second_status_copy_in_kernel", second_copy, "ECHILD")
        ck.eq("C4_no_zombie_left", oracle_state(node, timeout=1.0)[0], GONE)
        rw = [str(x.message)[:80] for x in w if issubclass(x.category, ResourceWarning)]
        ck.add("C4_no_ResourceWarning", not rw, [], rw)
        rec["fail_mode"] = "popen_reports_%s_instead_of_%s" % (rc_wait, truth_rc(truth)) if rc_wait != truth_rc(truth) else None
    return run


def e2_04(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E2-04 Popen reaps first (p.wait()), then the arm polls: the arm must not claim a status it does not hold")
    p, node = popen_stage(lab, "exit", 7)
    arm.register_root(node)
    if isinstance(arm, E2ARMP):
        arm.popens[p.pid] = p
    arm.preflight()
    lab_go(lab)
    lab.wait_state(node, ZOMBIE)
    rc = p.wait(timeout=10)
    o = arm.poll()
    rec.update(popen_wait=rc, arm_tri=o["tri"], arm_reasons=o["reasons"], arm_record=arm.exit_status(p.pid))
    ck.eq("popen_has_the_true_status", rc, 7)
    if isinstance(arm, E2ARMP):
        ck.eq("CA-P_reads_the_same_true_status_from_Popen", {k: v for k, v in (arm.exit_status(p.pid) or {}).items() if k in ("kind", "code")}, {"kind": "exit", "code": 7})
    else:
        ck.eq("C1_arm_does_not_claim_EXITED_without_a_status", (o["tri"], arm.exit_status(p.pid)), (UNKNOWN, None))


def e2_05(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E2-05 race: Popen.wait() in a thread vs arm.poll(); child exits at a random moment")
    p, node = popen_stage(lab, "exit", 7)
    arm.register_root(node)
    if isinstance(arm, E2ARMP):
        arm.popens[p.pid] = p
    arm.preflight()
    out = {}
    th = threading.Thread(target=lambda: out.__setitem__("rc", p.wait(timeout=10)))
    th.start()
    delay = random.uniform(0.0, 0.03)
    time.sleep(delay)
    lab_go(lab)
    end = L.now() + 5
    tri = None
    while L.now() < end:
        o = arm.poll()
        tri = o["tri"]
        if tri in (EXITED, UNKNOWN):
            break
        time.sleep(0.001)
    th.join(10)
    rec.update(delay_s=round(delay, 4), arm_tri=tri, popen_rc=out.get("rc"), arm_record=arm.exit_status(p.pid))
    arm_true = (arm.exit_status(p.pid) or {}).get("code") == 7 and (arm.exit_status(p.pid) or {}).get("kind") == "exit"
    popen_true = out.get("rc") == 7
    rec["holders"] = {"arm": arm_true, "popen": popen_true}
    ck.add("C1_arm_never_records_a_wrong_status", arm.exit_status(p.pid) in (None,) or arm_true, "None or true", arm.exit_status(p.pid))
    ck.add("C3_exactly_one_holder_of_the_true_status_or_both_by_design", (arm_true != popen_true) or (arm_true and popen_true and isinstance(arm, E2ARMP)), "XOR", rec["holders"])
    ck.add("C2_popen_returncode_equals_truth", popen_true, 7, out.get("rc"))
    ck.eq("C4_no_zombie_left", oracle_state(node, timeout=1.0)[0], GONE)
    rec["race_outcome"] = "arm_won" if arm_true and not popen_true else "popen_won" if popen_true and not arm_true else "both" if arm_true and popen_true else "neither"


def e2_06(lab, arm, ck, rec):
    rec.update(evidence_kind="INSTRUMENTED", purpose="E2-06 after the arm reaped, Popen.terminate()/kill()/send_signal() must not call os.kill (no signal to a possibly reused pid). os.kill is counted, not executed")
    p, node = popen_stage(lab, "exit", 7)
    arm.register_root(node)
    arm.preflight()
    lab_go(lab)
    lab.wait_state(node, ZOMBIE)
    arm.poll()
    calls = []
    real = os.kill
    os.kill = lambda pid, sig: calls.append((pid, int(sig)))
    try:
        p.terminate(); p.kill(); p.send_signal(signal.SIGTERM)
    finally:
        os.kill = real
    rec["os_kill_calls"] = calls
    rec["popen_returncode"] = p.returncode
    ck.eq("os_kill_call_count_after_arm_reaped", len(calls), 0)


def e2_08(order):
    def run(lab, arm, ck, rec):
        rec.update(evidence_kind="REAL_KERNEL", purpose="E2-08 CB with Popen, order %s" % order)
        p, node = popen_stage(lab, "exit", 7)
        arm.register_root(node)
        arm.preflight()
        lab_go(lab)
        lab.wait_state(node, ZOMBIE)
        o = arm.poll()
        ck.eq("cb_observes_exit_without_consuming", (o["tri"], oracle_state(node, timeout=1.0)[0]), (EXITED, ZOMBIE))
        if order == "a":
            t5 = arm.t5_reap()
            rc = p.poll()
            rec.update(cb_t5=t5["reaped"], popen_poll=rc, cb_record=arm.exit_status(p.pid))
            ck.eq("C1_cb_record_equals_truth", {k: v for k, v in (arm.exit_status(p.pid) or {}).items() if k in ("kind", "code")}, {"kind": "exit", "code": 7})
            ck.eq("C2_popen_returncode_equals_truth", rc, 7)
        else:
            rc = p.poll()
            o2 = arm.poll()
            t5 = arm.t5_reap()
            rec.update(popen_poll=rc, cb_tri_after=o2["tri"], cb_reasons=o2["reasons"], cb_t5=t5["reaped"])
            ck.eq("C2_popen_returncode_equals_truth", rc, 7)
            ck.eq("C1_cb_does_not_claim_a_false_status (UNKNOWN allowed)", o2["tri"], UNKNOWN)
        ck.eq("C4_no_zombie_left", oracle_state(node, timeout=1.0)[0], GONE)
    return run


E2ARMP = E.ArmCAP


# ============================================================ E3
def sample_states(lab, nodes, duration, step=0.5):
    samples = []
    t0 = L.now()
    while True:
        row = {"t": round(L.now() - t0, 2)}
        for n, node in nodes.items():
            st = L._oracle_stat(node["pid"])
            try:
                os.kill(node["pid"], 0)
                k0 = "success"
            except ProcessLookupError:
                k0 = "ESRCH"
            row[n] = {"proc": st["state"] if st and st["starttime"] == node["starttime"] else None, "kill0": k0}
        samples.append(row)
        if L.now() - t0 >= duration:
            return samples
        time.sleep(step)


def e3_01(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL (T5 omission is the injected fault)", purpose="E3-01 exited targets observed, T5 skipped: do zombies / pids persist, then does a LATE T5 recover everything")
    spec = {"name": "R", "exit_code": 1, "term": "ignore", "children": [{"name": "C%d" % i, "exit_code": i + 1} for i in range(1, 5)]}
    nodes = C.setup(lab, arm, spec, "R")
    rec["topology"] = C.topo(nodes)
    truth = {"R": 1, "C1": 2, "C2": 3, "C3": 4, "C4": 5}
    lab.wait_state(nodes["C4"], RUNNING)
    arm.poll()
    for n in ("C1", "C2", "C3", "C4"):
        lab.go(n, "exit", truth[n])
        lab.wait_state(nodes[n], ZOMBIE)
    lab.go("R", "exit", 1)
    lab.wait_state(nodes["R"], ZOMBIE)
    for n in ("C1", "C2", "C3", "C4"):
        C.wait_adopted_by_me(lab, nodes[n])
    o = arm.poll()
    rec["arm_tri_after_exits"] = o["tri"]
    ck.eq("arm_confirms_all_exited", o["tri"], EXITED)
    samples = sample_states(lab, nodes, 4.0)
    rec["samples"] = samples
    nz = sum(1 for s in samples for n in nodes if s[n]["proc"] == "Z")
    nk = sum(1 for s in samples for n in nodes if s[n]["kill0"] == "success")
    tot = len(samples) * len(nodes)
    rec["zombie_samples"] = nz; rec["kill0_success_samples"] = nk; rec["total_samples"] = tot
    if isinstance(arm, L.ArmCB):
        ck.add("PREDICTION_cb_zombies_persist_for_the_whole_window", nz == tot, tot, nz)
        ck.add("PREDICTION_cb_pids_remain_occupied_kill0_succeeds", nk == tot, tot, nk)
    else:
        ck.add("PREDICTION_ca_leaves_no_zombie", nz == 0, 0, nz)
    t5 = arm.t5_reap()
    rec["late_t5"] = t5["reaped"]
    for n, code in truth.items():
        C.status(ck, arm, nodes, n, ("exit", code))
    ck.eq("RECOVERY_residual_after_late_T5", t5["residual"], [])
    ck.eq("RECOVERY_all_gone", {n: oracle_state(node, timeout=1.0)[0] for n, node in nodes.items()}, {n: GONE for n in nodes})
    C.collateral_checks(lab, arm, ck, list(nodes))


def e3_01b(lab, arm, ck, rec):
    rec.update(evidence_kind="REAL_KERNEL", purpose="E3-01b bulk: 300 children exit unreaped; pid slots and /proc entries; per-pid recovery")
    K = 300
    def meminfo():
        d = {}
        for line in open("/proc/meminfo"):
            k, v = line.split(":")
            if k in ("MemAvailable", "Slab", "SUnreclaim"):
                d[k] = int(v.split()[0])
        return d
    before = meminfo()
    kids = []
    for i in range(K):
        pid = os.fork()
        if pid == 0:
            os._exit(i % 256)
        kids.append((pid, i % 256, None))
    kids = [(pid, code, L._oracle_stat(pid)) for pid, code, _ in kids]
    end = L.now() + 10
    while L.now() < end and sum(1 for pid, _, _ in kids if (L._oracle_stat(pid) or {}).get("state") == "Z") < K:
        time.sleep(0.01)
    zomb = sum(1 for pid, _, _ in kids if (L._oracle_stat(pid) or {}).get("state") == "Z")
    after = meminfo()
    rec["pid_max"] = int(open("/proc/sys/kernel/pid_max").read())
    import resource
    rec["RLIMIT_NPROC"] = resource.getrlimit(resource.RLIMIT_NPROC)
    rec["zombies_counted"] = zomb
    rec["pid_range"] = [min(k[0] for k in kids), max(k[0] for k in kids)]
    rec["meminfo_kB_before_after"] = {"before": before, "after": after}
    ck.eq("all_300_children_are_unreaped_zombies", zomb, K)
    p = os.fork()
    if p == 0:
        os._exit(0)
    os.waitpid(p, 0)
    ck.add("process_creation_still_possible_with_300_zombies", True)
    bad = []
    for pid, code, _ in kids:
        r = os.waitpid(pid, 0)
        if L.decode_status(r[1]) != {"kind": "exit", "code": code}:
            bad.append(pid)
    ck.eq("RECOVERY_every_status_correct_when_reaped_per_pid", bad, [])
    ck.eq("RECOVERY_no_zombie_left", sum(1 for pid, _, _ in kids if L._oracle_stat(pid) is not None), 0)


def sup_main(arm_name, wfd):
    os.setsid()
    lab2 = SpawnLab()
    lab2.begin()
    arm = ARMS2[arm_name](lab2)
    nodes = lab2.spawn({"name": "R", "exit_code": 3, "term": "ignore", "children": [{"name": "E", "exit_code": 5}, {"name": "D", "term": "ignore"}]})
    Y = lab2.spawn({"name": "Y", "exit_code": 9})["Y"]
    arm.register_root(nodes["R"])
    arm.register_aux(Y)
    arm.preflight()
    lab2.wait_state(nodes["D"], RUNNING)
    arm.poll()
    lab2.go("E", "exit", 5); lab2.wait_state(nodes["E"], ZOMBIE)
    lab2.go("R", "exit", 3); lab2.wait_state(nodes["R"], ZOMBIE)
    lab2.go("Y", "exit", 9); lab2.wait_state(Y, ZOMBIE)
    C.wait_adopted_by_me(lab2, nodes["E"])
    C.wait_adopted_by_me(lab2, nodes["D"])
    o = arm.poll()
    info = {n: {k: v for k, v in d.items() if k != "pidfd"} for n, d in dict(nodes, Y=Y).items()}
    rep = {"nodes": info, "arm_tri": o["tri"], "arm_exit_records_in_memory": {n: arm.exit_status(info[n]["pid"]) for n in ("R", "E", "D")},
           "sup_pid": os.getpid()}
    os.write(wfd, (json.dumps(rep, default=str) + "\n").encode())
    time.sleep(120)


def e3_02(subreaper_on):
    def run(lab, arm, ck, rec):
        rec.update(evidence_kind="REAL_KERNEL (SIGKILL of the supervisor is the injected abnormal exit)",
                   purpose="E3-02%s supervisor SIGKILLed with no T5/cleanup; outer reaper %s" % ("a" if subreaper_on else "b", "is a subreaper" if subreaper_on else "has the subreaper flag OFF (orphans go to pid 1)"))
        r, w = os.pipe()
        os.set_inheritable(w, True)
        sup = os.fork()
        if sup == 0:
            try:
                os.close(r)
                sup_main(arm.name, w)
            finally:
                os._exit(0)
        os.close(w)
        supfd = os.pidfd_open(sup)
        data = b""
        end = L.now() + 20
        while L.now() < end and b"\n" not in data:
            rl, _, _ = __import__("select").select([r], [], [], 0.3)
            if rl:
                c = os.read(r, 65536)
                if not c:
                    break
                data += c
        os.close(r)
        if b"\n" not in data:
            signal.pidfd_send_signal(supfd, signal.SIGKILL)
            os.waitpid(sup, 0)
            raise Blocked("supervisor produced no report")
        rep = json.loads(data.split(b"\n")[0])
        nodes = {}
        for n, d in rep["nodes"].items():
            d = dict(d)
            try:
                d["pidfd"] = os.pidfd_open(d["pid"])
                lab.nodes.append(d)
            except OSError as e:
                d["pidfd"] = None
                d["pidfd_error"] = errno.errorcode.get(e.errno)
            nodes[n] = d
        rec["supervisor_report"] = {"arm_tri": rep["arm_tri"], "exit_records_in_supervisor_memory": rep["arm_exit_records_in_memory"],
                                    "pidfd_open_after_supervisor_polls": {n: (d.get("pidfd_error") or "ok") for n, d in nodes.items()}}
        if not subreaper_on:
            lab.set_subreaper(False)
        try:
            signal.pidfd_send_signal(supfd, signal.SIGKILL)           # abnormal exit: no T5, no cleanup
            os.waitpid(sup, 0)
            os.close(supfd)
            t_death = L.now()
            time.sleep(0.3)
            truth = {"R": ("exit", 3), "E": ("exit", 5), "Y": ("exit", 9)}
            obs = {}
            for n, d in nodes.items():
                if d["pidfd"] is None:
                    obs[n] = {"state": GONE, "pidfd": d["pidfd_error"], "status_recoverable": False}
                    continue
                st, ev = oracle_state(d, timeout=1.0)
                row = {"state": st, "ppid_after_supervisor_death": ev.get("ppid"), "adopted_by_outer": ev.get("ppid") == os.getpid()}
                obs[n] = row
            rec["after_supervisor_death"] = obs
            # outer recovery path: pidfd + fingerprint only, per-pid
            for n, d in nodes.items():
                row = obs[n]
                if d["pidfd"] is None:
                    continue
                if row["state"] == RUNNING:
                    signal.pidfd_send_signal(d["pidfd"], signal.SIGKILL)
                    row["killed_by_outer_pidfd"] = True
                    truth[n] = ("signal", 9)
                    if row.get("adopted_by_outer"):
                        lab.wait_state(d, ZOMBIE, timeout=5)
                if row.get("adopted_by_outer") and L._oracle_stat(d["pid"]) is not None:
                    try:
                        r2 = os.waitid(os.P_PID, d["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT)
                        row["status_readable_before_reap"] = (L.decode_siginfo(r2.si_code, r2.si_status) if r2 else None)
                    except ChildProcessError:
                        row["status_readable_before_reap"] = None
                    rr = os.waitpid(d["pid"], os.WNOHANG)
                    row["reaped_status"] = L.decode_status(rr[1]) if rr[0] == d["pid"] else None
            gone_at = {}
            end = t_death + 12
            while L.now() < end and len(gone_at) < len(nodes):
                for n, d in nodes.items():
                    if n in gone_at:
                        continue
                    st0 = L._oracle_stat(d["pid"]) if d["pidfd"] is not None else None
                    if st0 is None or st0["starttime"] != d["starttime"]:
                        gone_at[n] = round(L.now() - t_death, 2)
                time.sleep(0.02)
            rec["seconds_after_supervisor_death_until_node_gone"] = gone_at
            rec["truth"] = {k: list(v) for k, v in truth.items()}
            final = {n: (oracle_state(d, timeout=1.0)[0] if d["pidfd"] is not None else GONE) for n, d in nodes.items()}
            rec["final_states"] = final
            ck.eq("RECOVERY_no_stage_process_left", final, {n: GONE for n in nodes})
            if subreaper_on:
                if arm.name == "CB":
                    ck.add("PREDICTION_cb_unreaped_zombie_statuses_are_recoverable_by_the_outer_reaper",
                           all(obs[n].get("status_readable_before_reap") == {"kind": "exit", "code": truth[n][1]} for n in ("R", "E")),
                           {"R": 3, "E": 5}, {n: obs[n].get("status_readable_before_reap") for n in ("R", "E")})
                else:
                    ck.add("PREDICTION_ca_already_reaped_statuses_are_not_recoverable", all(obs[n]["state"] == GONE and not obs[n].get("status_readable_before_reap") for n in ("R", "E")),
                           "R,E gone, no status", {n: obs[n] for n in ("R", "E")})
                ck.eq("decoy_Y_status_intact_for_outer", obs["Y"].get("reaped_status"), {"kind": "exit", "code": 9})
                ck.eq("live_orphan_D_adopted_by_outer_and_cleaned_by_pidfd", (obs["D"].get("adopted_by_outer"), obs["D"].get("killed_by_outer_pidfd"), obs["D"].get("reaped_status")),
                      (True, True, {"kind": "signal", "sig": 9}))
            else:
                ck.add("orphans_adopted_by_pid1_not_outer", all(not obs[n].get("adopted_by_outer") for n in obs if obs[n]["state"] != GONE), True, {n: obs[n].get("ppid_after_supervisor_death") for n in obs})
            ck.add("sentinel_alive_and_untouched", lab.sentinel_ok())
        finally:
            lab.set_subreaper(True)
    return run


class InjectedFault(Exception):
    pass


def e3_03(protected):
    def run(lab, arm, ck, rec):
        rec.update(evidence_kind="REAL_KERNEL (exception injection)", purpose="E3-03 exception between observation and T5; protected = try/finally T5")
        nodes = C.setup(lab, arm, {"name": "R", "exit_code": 4}, "R")
        R = nodes["R"]
        lab.wait_state(R, RUNNING)
        lab.go("R", "exit", 4)
        lab.wait_state(R, ZOMBIE)
        raised = False
        try:
            try:
                o = arm.poll()
                rec["tri"] = o["tri"]
                raise InjectedFault("between observation and T5")
            finally:
                if protected:
                    arm.t5_reap()
        except InjectedFault:
            raised = True
        ck.add("fault_was_injected", raised)
        st = oracle_state(R, timeout=1.0)[0]
        rec["state_after_exception_path"] = st
        ck.eq("CRITERION_no_zombie_left_after_the_exception_path", st, GONE)
        if protected:
            C.status(ck, arm, nodes, "R", ("exit", 4))
    return run


# ============================================================ registry & runner
def mk_e3_03_arm(base, protected):
    def f(lab):
        a = ARMS2[base](lab)
        a.name = base + ("-finally" if protected else "-nofinally")
        return a
    return f


ARMS2["CB-nofinally"] = mk_e3_03_arm("CB", False)
ARMS2["CB-finally"] = mk_e3_03_arm("CB", True)
ARMS2["CA-nofinally"] = mk_e3_03_arm("CA", False)

CASES = [
    # id, fn, repeats-kind, arms
    ("E1-P1", e1_p1, "n", E1_ARMS), ("E1-P2", e1_p2, "n", E1_ARMS), ("E1-P3", e1_p3, "n", E1_ARMS),
    ("E1-A1", e1_a("a1"), "n", E1_ARMS), ("E1-A2", e1_a("a2"), "n", E1_ARMS), ("E1-A3", e1_a("a3"), "n", E1_ARMS),
    ("E1-X1a", e1_x("x1a"), "n", E1_ARMS), ("E1-X1z", e1_x("x1z"), "n", E1_ARMS), ("E1-X2", e1_x("x2"), "n", E1_ARMS),
    ("E1-S1", e1_s1, "n", ["BENCH"]), ("E1-S2", e1_s2, "n", E1_ARMS),
    ("E2-00a", e2_0("exit7"), "n", ["POPEN"]), ("E2-00b", e2_0("sigkill"), "n", ["POPEN"]), ("E2-00c", e2_0("sigterm"), "n", ["POPEN"]),
    ("E2-01", e2_basic("exit7"), "n", ["CA", "CA-P"]), ("E2-02", e2_basic("sigkill"), "n", ["CA", "CA-P"]), ("E2-03", e2_basic("sigterm"), "n", ["CA", "CA-P"]),
    ("E2-04", e2_04, "n", ["CA", "CA-P", "CB"]), ("E2-05", e2_05, "race", ["CA", "CA-P"]), ("E2-06", e2_06, "n", ["CA"]),
    ("E2-08a", e2_08("a"), "n", ["CB"]), ("E2-08b", e2_08("b"), "n", ["CB"]),
    ("E3-01", e3_01, "n", ["CB", "CA"]), ("E3-01b", e3_01b, "n", ["BENCH"]),
    ("E3-02a", e3_02(True), "n", ["CB", "CA"]), ("E3-02b", e3_02(False), "n", ["CB", "CA"]),
    ("E3-03", e3_03(False), "n", ["CB-nofinally", "CA-nofinally"]), ("E3-03p", e3_03(True), "n", ["CB-finally"]),
]


def run_one(lab, cid, fn, armname, rep):
    lab.begin()
    rec = {"case": cid, "arm": armname, "repeat": rep, "supervisor_pid": os.getpid()}
    ck = Checker()
    t0 = L.now()
    try:
        arm = ARMS2[armname](lab) if armname in ARMS2 else None
        fn(lab, arm, ck, rec)
        C.finish_record(rec, ck)
        rec["tool_ok"] = True
    except Blocked as e:
        rec["status"], rec["blocked_reason"], rec["tool_ok"] = BLOCKED, str(e), False
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--race-repeat", type=int, default=50)
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=20261027)
    a = ap.parse_args()
    random.seed(a.seed)
    lab = SpawnLab()
    results, run_error, env = [], None, None
    try:
        lab.set_subreaper(False)
        lab.start_sentinel()
        lab.set_subreaper(True)
        env = C.environment(lab)
        env["sentinel"] = {k: v for k, v in lab.sentinel.items() if k != "pidfd"}
        only = set(a.only.split(",")) if a.only else None
        for cid, fn, kind, arms in CASES:
            if only and cid not in only:
                continue
            reps = a.race_repeat if kind == "race" else a.repeat
            for armname in arms:
                for rep in range(1, reps + 1):
                    r = run_one(lab, cid, fn, armname, rep)
                    results.append(r)
                    if not lab.sentinel_ok():
                        raise RuntimeError("sentinel disturbed during %s/%s/%d" % (cid, armname, rep))
                print("%-8s %-14s %s" % (cid, armname, {s: sum(1 for r in results if r["case"] == cid and r["arm"] == armname and r["status"] == s) for s in (PASS, FAIL, BLOCKED)}), flush=True)
    except Exception as e:
        run_error = "%r\n%s" % (e, traceback.format_exc())
        print("RUN ERROR", run_error, file=sys.stderr)
    finally:
        fin = lab.final_cleanup()
    out = {"experiment": "F3B-D1-A-CPU-002", "environment": env, "args": vars(a), "results": results, "final_cleanup": fin, "run_error": run_error,
           "cleanup_unclean_runs": [(r["case"], r["arm"], r["repeat"]) for r in results if not r["cleanup_clean"]],
           "tool_not_ok_runs": [(r["case"], r["arm"], r["repeat"], r.get("blocked_reason")) for r in results if not r["tool_ok"]]}
    if a.out:
        with open(a.out, "w") as f:
            f.write(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n")


if __name__ == "__main__":
    main()
