#!/usr/bin/env python3
"""F3B-D1-G1G2-CPU-001 -- synthetic CPU correctness probe for the R3 "alive target" predicate A.

R3 section 11.1(d) defines  A = (1) the direct child has not been reaped by waitpid, OR
(2) killpg(pgid, 0) still succeeds, OR (3) a re-parented descendant exists.   "A false" means
"all target processes have exited"; escalation to SIGKILL is only allowed while A is true.

This probe observes REAL Linux child processes and compares the predicate A, as literally written in R3,
with an INDEPENDENT oracle (waitid(WNOWAIT) + /proc/<pid>/stat).  It never changes the frozen R3 text:
if A disagrees with the oracle that is reported as a rule FAIL, not repaired here.

Safety: it only creates its own children (each in its own session / process group) and only signals a pid/pgid
that it spawned itself and re-verified (guard()).  Linux only, standard library only, no network.
"""
import json, os, platform, signal, subprocess, sys, time, uuid, hashlib

TOKEN = "G1G2PROBE-" + uuid.uuid4().hex[:12]
SPAWNED = {}          # pid -> {"pgid": int, "name": str, "reaped": bool}
CODES = {
    "SLEEP": "import time; time.sleep(60)",
    "QUICK_EXIT": "import sys; sys.exit(0)",
    "IGNORE_TERM": "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
}
PROCEDURES = ("NOREAP", "EVAL_THEN_REAP", "REAP_THEN_EVAL")   # the three readings R3 text permits
EXPECTED_A = {"RUNNING": True, "EXITED_UNREAPED": False, "REAPED": False}   # "A false <=> all targets exited"


class SafetyError(RuntimeError):
    pass


def t():
    return time.monotonic()


# ---------------------------------------------------------------- independent observation
def proc_stat(pid):
    """(state, ppid, pgrp) from /proc/<pid>/stat, or None if the pid does not exist."""
    try:
        with open("/proc/%d/stat" % pid, "rb") as f:
            data = f.read().decode("ascii", "replace")
    except (FileNotFoundError, ProcessLookupError):
        return None
    rest = data[data.rindex(")") + 2:].split()
    return rest[0], int(rest[1]), int(rest[2])


def waitid_peek(pid):
    """Non-consuming exit observation.  'NOCHANGE' (still running), ('EXITED', si_code, si_status), or 'NOCHILD'."""
    try:
        r = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return "NOCHILD"
    if r is None:
        return "NOCHANGE"
    return ("EXITED", r.si_code, r.si_status)


def truth(pid):
    """Independent true state, from two oracles that must agree: waitid(WNOWAIT) and /proc state."""
    for _ in range(5):
        w, st = waitid_peek(pid), proc_stat(pid)
        s = st[0] if st else None
        if w == "NOCHILD" and st is None:
            return "REAPED", {"waitid": w, "proc": None}
        if w == "NOCHANGE" and s is not None and s not in ("Z", "X"):
            return "RUNNING", {"waitid": w, "proc_state": s}
        if isinstance(w, tuple) and s == "Z":
            return "EXITED_UNREAPED", {"waitid": list(w), "proc_state": s}
        time.sleep(0.005)       # oracles may differ for an instant around an exit
    return "ORACLE_DISAGREE", {"waitid": str(w), "proc_state": s}


# ---------------------------------------------------------------- safe spawning / signalling
def spawn(name):
    code = CODES[name]
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid()
            os.execv(sys.executable, [sys.executable, "-c", code, TOKEN, name])
        finally:
            os._exit(127)
    deadline = t() + 3
    while t() < deadline:           # wait until the child has become its own group leader
        try:
            if os.getpgid(pid) == pid:
                break
        except ProcessLookupError:
            break
        time.sleep(0.002)
    SPAWNED[pid] = {"pgid": pid, "name": name, "reaped": False}
    # identity must be provable before anything may be signalled: wait until exec has happened
    # (cmdline carries the probe token) or the child is already a zombie / gone (quick-exit case).
    deadline = t() + 5
    while t() < deadline:
        st = proc_stat(pid)
        if st is None or st[0] in ("Z", "X"):
            break
        try:
            with open("/proc/%d/cmdline" % pid, "rb") as f:
                if TOKEN.encode() in f.read():
                    break
        except FileNotFoundError:
            break
        time.sleep(0.002)
    return pid


def guard(pid):
    """Refuse to signal anything that is not a verified child of this probe."""
    info = SPAWNED.get(pid)
    if info is None:
        raise SafetyError("pid %d was not spawned by this probe" % pid)
    pgid = info["pgid"]
    if pgid in (0, 1) or pgid == os.getpgrp() or pgid == os.getpid():
        raise SafetyError("refusing to signal own/system process group %d" % pgid)
    st = proc_stat(pid)
    if st is not None:
        if st[1] != os.getpid():
            raise SafetyError("pid %d is not our child (ppid %d)" % (pid, st[1]))
        if st[2] != pgid:
            raise SafetyError("pid %d pgrp %d != recorded %d" % (pid, st[2], pgid))
        if st[0] not in ("Z", "X"):
            try:
                with open("/proc/%d/cmdline" % pid, "rb") as f:
                    cmd = f.read()
                # an exiting process has already released its mm, so its cmdline reads empty: that is fine for an
                # unreaped child of ours (its pid cannot be recycled before we reap it); a NON-empty cmdline must carry the token
                if cmd and TOKEN.encode() not in cmd:
                    raise SafetyError("cmdline of pid %d lacks the probe token" % pid)
            except FileNotFoundError:
                pass
    return pgid


def signal_group(pid, sig):
    pgid = guard(pid)
    if SPAWNED[pid]["reaped"]:      # after reaping, the pid/pgid number may be recycled by a stranger
        raise SafetyError("pid %d already reaped; refusing to signal" % pid)
    try:
        os.killpg(pgid, sig)
        return {"result": "sent", "errno": None}
    except ProcessLookupError:
        return {"result": "gone", "errno": None}
    except OSError as e:
        return {"result": "error", "errno": e.errno}


def probe_killpg0(pid):
    """killpg(pgid, 0) -- signal 0 only checks existence; guarded anyway."""
    pgid = guard(pid)
    try:
        os.killpg(pgid, 0)
        return "success"
    except ProcessLookupError:
        return "ESRCH"
    except PermissionError:
        return "EPERM"
    except OSError as e:
        return "errno%d" % e.errno


def group_members(pgid):
    out = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            st = proc_stat(int(d))
            if st and st[2] == pgid:
                out.append({"pid": int(d), "state": st[0]})
    return out


def reap_nowait(pid):
    """waitpid(WNOHANG) -- this CONSUMES the exit status of an exited child."""
    info = SPAWNED[pid]
    try:
        r = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        info["reaped"] = True
        return {"returned_pid": None, "note": "ChildProcessError (already reaped)"}
    if r[0] == pid:
        info["reaped"] = True
        return {"returned_pid": pid, "raw_status": r[1]}
    return {"returned_pid": 0}


# ---------------------------------------------------------------- the R3 predicate A, as literally written
def r3_A(pid):
    info = SPAWNED[pid]
    c1 = not info["reaped"]                              # (1) direct child not yet reaped by waitpid
    c2_res = probe_killpg0(pid)                          # (2) killpg(pgid, 0) still succeeds
    c2 = c2_res == "success"
    reparented = []                                      # (3) re-parented descendants under this process
    for d in os.listdir("/proc"):
        if d.isdigit() and int(d) not in SPAWNED:
            st = proc_stat(int(d))
            if st and st[1] == os.getpid() and int(d) != os.getpid():
                reparented.append(int(d))
    c3 = bool(reparented)
    return {"A": c1 or c2 or c3, "c1_not_reaped": c1, "c2_killpg0": c2_res, "c2_success": c2, "c3_reparented": reparented}


def evaluate(procedure, pid):
    """Evaluate A with a given ordering relative to waitpid(WNOHANG).  Returns A plus before/after oracle truth."""
    before, _ = truth(pid)
    reap = None
    if procedure == "NOREAP":
        a = r3_A(pid)
    elif procedure == "EVAL_THEN_REAP":
        a = r3_A(pid)
        reap = reap_nowait(pid)
    elif procedure == "REAP_THEN_EVAL":
        reap = reap_nowait(pid)
        a = r3_A(pid)
    else:
        raise ValueError(procedure)
    after, _ = truth(pid)
    exp = EXPECTED_A.get(before)
    return {"procedure": procedure, "truth_before": before, "truth_after": after, "reap": reap, "A_components": a,
            "A": a["A"], "expected_A_for_truth_before": exp,
            "consistent": (exp is not None and a["A"] == exp),
            "recommends_sigkill_if_deadline": a["A"], "false_escalation": bool(a["A"] and before != "RUNNING")}


def wait_for(pid, want, timeout=5.0):
    end = t() + timeout
    while t() < end:
        s, _ = truth(pid)
        if s == want:
            return True
        time.sleep(0.005)
    return False


def cleanup():
    """Terminate and reap everything this probe spawned (only verified pids); return residual report."""
    notes = []
    for pid, info in list(SPAWNED.items()):
        try:
            if not info["reaped"]:
                s, _ = truth(pid)
                if s == "RUNNING":
                    signal_group(pid, signal.SIGKILL)
                end = t() + 5
                while t() < end:
                    try:
                        r = os.waitpid(pid, os.WNOHANG)
                    except ChildProcessError:
                        info["reaped"] = True
                        break
                    if r[0] == pid:
                        info["reaped"] = True
                        break
                    time.sleep(0.01)
        except SafetyError as e:
            notes.append("cleanup refused %d: %s" % (pid, e))
    residual = [p for p in SPAWNED if proc_stat(p) is not None]
    scan = []
    for d in os.listdir("/proc"):
        if d.isdigit() and int(d) != os.getpid():
            try:
                with open("/proc/%s/cmdline" % d, "rb") as f:
                    if TOKEN.encode() in f.read():
                        scan.append(int(d))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
    return {"spawned": sorted(SPAWNED), "residual_pids_in_proc": residual, "token_scan_pids": scan, "notes": notes}


# ---------------------------------------------------------------- cases
def case_g1_01():
    out = {"id": "G1-01", "purpose": "persistent child in its own process group is recognised as RUNNING", "runs": []}
    pid = spawn("SLEEP")
    ok = wait_for(pid, "RUNNING")
    pre = {"pid": pid, "pgid": SPAWNED[pid]["pgid"], "ppid": proc_stat(pid)[1] if proc_stat(pid) else None,
           "own_pgid": os.getpgrp(), "getpgid_child": os.getpgid(pid), "truth": truth(pid)}
    evals = [evaluate(p, pid) for p in PROCEDURES]
    out.update(precondition=pre, evaluations=evals,
               tool_status="PASS" if ok and pre["truth"][0] == "RUNNING" else "BLOCKED",
               rule_status="PASS" if all(e["consistent"] for e in evals) else "FAIL")
    return out


def case_g1_02():
    out = {"id": "G1-02", "purpose": "child exited normally, parent has not called waitpid: EXITED_UNREAPED", "evaluations": []}
    toolok = True
    for p in PROCEDURES:
        pid = spawn("QUICK_EXIT")
        ok = wait_for(pid, "EXITED_UNREAPED")
        toolok = toolok and ok
        e = evaluate(p, pid)
        e["pid"] = pid; e["precondition_reached"] = ok
        out["evaluations"].append(e)
    out.update(tool_status="PASS" if toolok else "BLOCKED",
               rule_status="PASS" if all(e["consistent"] for e in out["evaluations"]) else "FAIL")
    return out


def case_g1_03():
    out = {"id": "G1-03", "purpose": "exited child is reaped with waitpid: REAPED", "evaluations": []}
    pid = spawn("QUICK_EXIT")
    ok = wait_for(pid, "EXITED_UNREAPED")
    before = truth(pid)
    r = os.waitpid(pid, 0)
    SPAWNED[pid]["reaped"] = True
    after = truth(pid)
    a = r3_A(pid)
    exp = EXPECTED_A[after[0]] if after[0] in EXPECTED_A else None
    out.update(pid=pid, truth_before_waitpid=before, waitpid_result={"pid": r[0], "exit_status": os.waitstatus_to_exitcode(r[1])},
               truth_after_waitpid=after, A_components=a, A=a["A"], expected_A=exp, consistent=(a["A"] == exp),
               tool_status="PASS" if ok and before[0] == "EXITED_UNREAPED" and after[0] == "REAPED" else "BLOCKED",
               rule_status="PASS" if exp is not None and a["A"] == exp else "FAIL")
    return out


def case_g2_01():
    out = {"id": "G2-01", "purpose": "process group holds only an exited-but-unreaped child: what does killpg(pgid,0) return", "obs": {}}
    pid = spawn("QUICK_EXIT"); pgid = SPAWNED[pid]["pgid"]
    ok = wait_for(pid, "EXITED_UNREAPED")
    o = out["obs"]
    o["truth_before"] = truth(pid)
    o["group_members_proc"] = group_members(pgid)
    o["killpg0_before_reap"] = probe_killpg0(pid)
    try:
        os.kill(pid, 0); o["kill_pid0_before_reap"] = "success"
    except ProcessLookupError:
        o["kill_pid0_before_reap"] = "ESRCH"
    reap_nowait(pid)
    o["truth_after"] = truth(pid)
    o["killpg0_after_reap"] = probe_killpg0(pid)
    o["group_members_after_reap"] = group_members(pgid)
    consistent = (o["killpg0_before_reap"] == "ESRCH")      # intent: all targets exited => condition (2) must not hold
    out.update(tool_status="PASS" if ok and o["truth_before"][0] == "EXITED_UNREAPED" and o["truth_after"][0] == "REAPED" else "BLOCKED",
               condition2_consistent_with_intent=consistent, rule_status="PASS" if consistent else "FAIL")
    return out


def simulate_t3(procedure, grace=1.0, poll=0.1, first_poll_delay=0.0):
    """Scaled-down T3 loop (probe-local timing; NOT the approved G_term).  SIGTERM a SLEEP child, then poll A each cycle."""
    pid = spawn("SLEEP"); wait_for(pid, "RUNNING")
    sig = signal_group(pid, signal.SIGTERM)
    t0 = t()
    if first_poll_delay:
        time.sleep(first_poll_delay)
    decision, polls = None, []
    while decision is None:
        now = t() - t0
        before, _ = truth(pid)
        e = evaluate(procedure, pid)       # evaluation order follows the procedure
        polls.append({"t": round(now, 3), "truth_before": e["truth_before"], "A": e["A"], "reap": e["reap"]})
        if not e["A"]:
            decision = "EARLY_CONFIRM"
        elif now >= grace:
            decision = "ESCALATE_SIGKILL"
            false_esc = e["truth_before"] != "RUNNING"
        if decision is None:
            time.sleep(poll)
    final_truth_before = polls[-1]["truth_before"]
    return {"procedure": procedure, "pid": pid, "sigterm": sig, "decision": decision, "decision_time": polls[-1]["t"],
            "truth_at_decision": final_truth_before,
            "false_escalation": decision == "ESCALATE_SIGKILL" and final_truth_before != "RUNNING", "polls": polls}


def case_g2_02():
    out = {"id": "G2-02", "purpose": "SIGTERM makes the child exit before the deadline, not yet reaped: must NOT recommend SIGKILL",
           "natural_loop": [], "deadline_race": []}
    for p in PROCEDURES:
        out["natural_loop"].append(simulate_t3(p, grace=1.0, poll=0.1))
    for p in PROCEDURES:      # first poll happens only at the deadline: child exited long before
        out["deadline_race"].append(simulate_t3(p, grace=0.5, poll=0.1, first_poll_delay=0.5))
    allruns = out["natural_loop"] + out["deadline_race"]
    out.update(tool_status="PASS" if all(r["truth_at_decision"] in ("RUNNING", "EXITED_UNREAPED", "REAPED") for r in allruns) else "BLOCKED",
               false_escalations=[{"set": s, "procedure": r["procedure"]} for s, rs in (("natural_loop", out["natural_loop"]), ("deadline_race", out["deadline_race"])) for r in rs if r["false_escalation"]])
    out["rule_status"] = "FAIL" if out["false_escalations"] else "PASS"
    return out


def case_g2_03():
    out = {"id": "G2-03", "purpose": "a genuinely running child (ignores SIGTERM) must not be missed by A", "evaluations": []}
    pid = spawn("IGNORE_TERM")
    ok = wait_for(pid, "RUNNING")
    end = t() + 3
    while t() < end:       # confirm independently that SIGTERM is ignored before signalling
        try:
            with open("/proc/%d/status" % pid) as f:
                sigign = [l for l in f if l.startswith("SigIgn")][0].split()[1]
            if int(sigign, 16) & (1 << (signal.SIGTERM - 1)):
                break
        except (FileNotFoundError, IndexError):
            pass
        time.sleep(0.01)
    out["sigterm_ignored_confirmed"] = bool(int(sigign, 16) & (1 << (signal.SIGTERM - 1)))
    out["sigterm"] = signal_group(pid, signal.SIGTERM)
    time.sleep(0.5)
    out["truth_after_sigterm_grace"] = truth(pid)
    out["evaluations"] = [evaluate(p, pid) for p in PROCEDURES]
    out["escalation_applied"] = signal_group(pid, signal.SIGKILL)       # only our own verified child
    wait_for(pid, "EXITED_UNREAPED")
    out["truth_after_sigkill"] = truth(pid)
    reap_nowait(pid)
    out["truth_final"] = truth(pid)
    out.update(tool_status="PASS" if ok and out["sigterm_ignored_confirmed"] and out["truth_after_sigterm_grace"][0] == "RUNNING" and out["truth_after_sigkill"][0] == "EXITED_UNREAPED" else "BLOCKED",
               rule_status="PASS" if all(e["consistent"] and e["A"] for e in out["evaluations"]) else "FAIL")
    return out


CASES = [case_g1_01, case_g1_02, case_g1_03, case_g2_01, case_g2_02, case_g2_03]


def environment():
    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
        except Exception as e:
            return "unavailable: %s" % e
    cg = ""
    try:
        with open("/proc/1/cgroup") as f:
            cg = f.read()[:200]
    except OSError:
        pass
    return {"kernel": platform.release(), "platform": platform.platform(), "python": sys.version, "machine": platform.machine(),
            "git_branch": sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]), "git_commit": sh(["git", "rev-parse", "HEAD"]),
            "proc_available": os.path.isdir("/proc") and os.path.exists("/proc/self/stat"),
            "os.waitid": hasattr(os, "waitid"), "os.WNOWAIT": hasattr(os, "WNOWAIT"), "os.WEXITED": hasattr(os, "WEXITED"),
            "os.P_PID": hasattr(os, "P_PID"), "os.waitpid": hasattr(os, "waitpid"), "os.killpg": hasattr(os, "killpg"),
            "container_hints": {"dockerenv": os.path.exists("/.dockerenv"), "pid1_cgroup_head": cg},
            "probe_pid": os.getpid(), "probe_pgid": os.getpgrp(), "probe_ppid": os.getppid(), "token": TOKEN}


def run(repeat=1):
    env = environment()
    results, errors = [], []
    try:
        for i in range(repeat):
            for c in CASES:
                t0 = t()
                try:
                    r = c()
                except Exception as e:           # tool failure => BLOCKED for the case
                    r = {"id": c.__name__, "tool_status": "BLOCKED", "rule_status": "NOT TESTED", "exception": repr(e)}
                    errors.append(repr(e))
                r["repeat"] = i + 1; r["elapsed_s"] = round(t() - t0, 3)
                results.append(r)
    finally:
        residual = cleanup()
    summary = {}
    for cid in ("G1-01", "G1-02", "G1-03", "G2-01", "G2-02", "G2-03"):
        rs = [r for r in results if r["id"] == cid]
        summary[cid] = {"tool_status": "PASS" if rs and all(r["tool_status"] == "PASS" for r in rs) else "BLOCKED",
                        "rule_status": ("FAIL" if any(r["rule_status"] == "FAIL" for r in rs) else
                                        "PASS" if rs and all(r["rule_status"] == "PASS" for r in rs) else "NOT TESTED")}
    g1 = [summary[k]["rule_status"] for k in ("G1-01", "G1-02", "G1-03")]
    g2 = [summary[k]["rule_status"] for k in ("G2-01", "G2-02", "G2-03")]
    gate = lambda xs: "FAIL" if "FAIL" in xs else ("PASS" if all(x == "PASS" for x in xs) else "NOT TESTED")
    return {"experiment": "F3B-D1-G1G2-CPU-001", "environment": env, "repeat": repeat, "results": results, "case_summary": summary,
            "tool_overall": "PASS" if all(v["tool_status"] == "PASS" for v in summary.values()) else "BLOCKED",
            "gate_G1_rule": gate(g1), "gate_G2_rule": gate(g2), "residual_check": residual, "errors": errors}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.repeat)
    text = json.dumps(res, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    print(json.dumps({k: res[k] for k in ("case_summary", "tool_overall", "gate_G1_rule", "gate_G2_rule", "residual_check")}, indent=2, sort_keys=True))
