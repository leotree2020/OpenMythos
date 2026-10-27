"""G0 judge (PURE).  Applies the FROZEN criteria g0_criteria_v1.json to an evidence dictionary.  WRITTEN, NOT RUN.
A check whose evidence is missing is UNEVALUABLE (-> BLOCKED); FAIL needs evidence.  Precedence: evidenced FAIL > BLOCKED > PASS."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bench"))
import registry as R  # noqa: E402

SNAPS = ("S0_before_fork", "S1_held_registered_unreleased", "S2_ready_after_release", "S3_exited_unreaped", "S4_reaped", "S5_final")
EVENT_KEYS = ("exit_sent_mono", "pidfd_readable_mono", "reap_mono", "proc_gone_mono", "first_action_mono")
BIND_KEYS = ("git_head", "prereg_sha256", "g0_criteria_sha256", "g0_prereg_sha256", "bench_code_sha256", "g0_code_sha256")


def load_criteria(path=None):
    with open(path or os.path.join(HERE, "g0_criteria_v1.json"), encoding="utf-8") as f:
        return json.load(f)


class Uneval(Exception):
    pass


def need(cond, why):
    if not cond:
        raise Uneval(why)


def _node(ev):
    reg = ev["reg"]
    intents = [r for r in reg if r["kind"] == "INTENT"]
    need(len(intents) >= 1, "no INTENT record")
    nid = ev["node"]["node_id"]
    return reg, nid, {k: [r for r in reg if r.get("node_id") == nid and r["kind"] == k] for k in ("INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD", "ABORTED")}


def c01(ev, crit):
    pf = ev["preflight"]
    ok = (pf.get("ok") is True and not pf.get("problems") and pf.get("children") == 0 and not pf.get("token_residue") and not pf.get("unresolved_prior")
          and not pf.get("enumeration_problems") and pf.get("run_id_unique") is True)
    return ok, "preflight %s" % ({k: pf.get(k) for k in ("ok", "problems", "children", "token_residue", "unresolved_prior", "enumeration_problems", "run_id_unique")} if not ok else "clean")


def c02(ev, crit):
    a, s, e = ev["auth_expected"], ev["bindings_start"], ev["bindings_end"]
    diffs = [k for k in BIND_KEYS if not (a.get(k) and a.get(k) == s.get(k) == e.get(k))]
    return (not diffs and ev.get("auth_consumed") is True), "binding differences %s, consumed=%s" % (diffs, ev.get("auth_consumed"))


def c03(ev, crit):
    reg, nid, k = _node(ev)
    kinds = [r["kind"] for r in reg]
    need(len(kinds) > 0, "empty registry")
    problems = ["ORDER: " + x for x in R.check_order(reg)]       # evidence of a protocol-order violation holds even for an incomplete run
    if problems or (ev.get("exception") is None and ev.get("aborted") is None):
        if kinds[0] != "RUN_START" or kinds.count("RUN_START") != 1:
            problems.append("RUN_START not unique/first")
        if kinds[-1] != "RUN_END" or kinds.count("RUN_END") != 1:
            problems.append("RUN_END not unique/last")
        pos = []
        for kind in ("INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD"):
            idx = [i for i, r in enumerate(reg) if r.get("node_id") == nid and r["kind"] == kind]
            if len(idx) != 1:
                problems.append("%s count %d" % (kind, len(idx)))
            else:
                pos.append(idx[0])
        if len(pos) == 5 and pos != sorted(pos):
            problems.append("node records out of order %s" % pos)
        if k["ABORTED"]:
            problems.append("ABORTED present")
        problems += R.integrity_issues(reg)
        return not problems, problems or "sequence and integrity ok"
    raise Uneval("run did not complete (exception/abort): completeness of the registry sequence cannot be judged")


def c04(ev, crit):
    reg, nid, k = _node(ev)
    held = ev["snapshots"]["S1_held_registered_unreleased"]["child"]
    reg_rec = k["REGISTERED"][0]
    obs_pid = ev["observer"]["pid"]
    ok = (reg_rec["pid"] == held["pid"] == ev["guard"]["fork_pids"][0] and reg_rec["starttime"] == held["starttime"] and held["ppid"] == obs_pid)
    return ok, "registered %r vs held %r, fork pids %r, observer %r" % ({x: reg_rec.get(x) for x in ("pid", "starttime")}, {x: held.get(x) for x in ("pid", "starttime", "ppid")},
                                                                         ev["guard"]["fork_pids"], obs_pid)


def c05(ev, crit):
    reg, nid, k = _node(ev)
    s1 = ev["snapshots"]["S1_held_registered_unreleased"]
    ch, ob = s1["child"], ev["observer"]
    problems = []
    if ch["state"] != "S":
        problems.append("held child state %r" % ch["state"])
    if s1["messages_received"] != 0 or s1["first_action_mono"] is not None:
        problems.append("child acted before release")
    if (ch["sid"], ch["pgrp"]) != (ob["sid"], ob["pgrp"]):
        problems.append("child sid/pgrp changed")
    if not ev["events"]["first_action_mono"] >= k["RELEASED"][0]["mono"]:
        problems.append("FIRST_ACTION earlier than RELEASED")
    return not problems, problems or "no action before release"


def c06(ev, crit):
    s1, s2 = ev["snapshots"]["S1_held_registered_unreleased"], ev["snapshots"]["S2_ready_after_release"]
    gate = "pipe:[%d]" % ev["node"]["gate_ino"]
    fds = s1["fds"]
    problems = []
    gate_fds = [(fd, v) for fd, v in fds.items() if v["target"] == gate]
    if len(gate_fds) != 1 or gate_fds[0][1]["access"] != "r":
        problems.append("held: gate pipe descriptors %r" % gate_fds)
    others = [(fd, v) for fd, v in fds.items() if v["target"] != gate and int(fd) > 2]
    if len(others) > 1 or any(not v["target"].startswith("socket:") for _, v in others):
        problems.append("held: unexpected descriptors %r" % others)
    if len(fds) > 5:
        problems.append("held: %d descriptors" % len(fds))
    if any(v["target"] == gate for v in s2["fds"].values()):
        problems.append("after release the gate pipe is still open")
    return not problems, problems or "descriptor hygiene ok"


def c07(ev, crit):
    reg, nid, k = _node(ev)
    pre = ev["guard"]["release_byte_pre_write_monos"]
    need(len(pre) == 1, "release byte write not recorded exactly once")
    chain = [k["REGISTERED"][0]["mono"], k["RELEASED"][0]["mono"], pre[0], ev["events"]["first_action_mono"]]
    return chain == sorted(chain), "REGISTERED <= RELEASED <= release byte <= FIRST_ACTION: %r" % chain


def c08(ev, crit):
    s3 = ev["snapshots"]["S3_exited_unreaped"]
    obs_pid = ev["observer"]["pid"]
    early = [c for c in ev["guard"]["waitpid_calls"] if c["mono"] < s3["mono"]]
    problems = []
    if not s3["child"] or s3["child"]["state"] != "Z" or s3["child"]["ppid"] != obs_pid:
        problems.append("S3 child %r (need state Z, ppid %d)" % (s3["child"], obs_pid))
    if early:
        problems.append("wait call before the unreaped observation: %r" % early)
    if not (ev["events"]["exit_sent_mono"] < ev["events"]["pidfd_readable_mono"] <= s3["mono"]):
        problems.append("EXIT/pidfd/S3 times not ordered")
    return not problems, problems or "exited-unreaped observed before any wait"


def c09(ev, crit):
    pid, st = ev["node"]["pid"], ev["node"]["starttime"]
    calls = ev["guard"]["waitpid_calls"]
    s3, s4 = ev["snapshots"]["S3_exited_unreaped"], ev["snapshots"]["S4_reaped"]
    problems = []
    if any(c["pid"] != pid for c in calls):
        problems.append("a wait call named another pid: %r" % [c["pid"] for c in calls])
    ret = [c for c in calls if c["returned"] == pid]
    if len(ret) != 1:
        problems.append("%d wait calls returned the child pid" % len(ret))
    elif not (s3["mono"] < ret[0]["mono"] <= ev["events"]["proc_gone_mono"]):
        problems.append("times EXITED_UNREAPED < REAPED <= PROC_GONE violated")
    if s4["child"] is not None and s4["child"]["starttime"] == st:
        problems.append("child still present in /proc after reap")
    if not ev["events"]["reap_mono"] >= s3["mono"]:
        problems.append("reap_mono before S3")
    return not problems, problems or "reaped by specific pid, /proc entry gone"


def c10(ev, crit):
    need(ev["reap"]["exit_status"] is not None, "no exit status")
    return ev["reap"]["exit_status"] == 0, "exit status %r" % ev["reap"]["exit_status"]


def c11(ev, crit):
    reg = ev["reg"]
    problems = []
    if ev["guard"]["fork_calls"] != 1:
        problems.append("fork calls %r" % ev["guard"]["fork_calls"])
    for name in SNAPS:
        s = ev["snapshots"][name]
        if len(s["children"]) > 1 or s["grandchildren"]:
            problems.append("%s: children %r grandchildren %r" % (name, s["children"], s["grandchildren"]))
    intents = [r for r in reg if r["kind"] == "INTENT"]
    if len(intents) != 1 or any(r.get("creator") != "O" for r in intents):
        problems.append("registry nodes/tickets: %r" % [(r.get("node_id"), r.get("creator")) for r in intents])
    return not problems, problems or "one fork, one child, no descendants, no tickets"


def c12(ev, crit):
    viol = ev["guard"]["violations"]
    kills = [x for rnd in ev["cleanup"].get("rounds", []) for key in ("kill", "kill_unregistered_direct") for x in rnd.get(key, [])]
    bad = [x for x in kills if x.get("result") != "already_exited"]
    return (not viol and not bad), "violations %r, non-trivial kill entries %r" % (viol, bad)


def c13(ev, crit):
    cl = ev["cleanup"]
    reg, nid, k = _node(ev)
    s5 = ev["snapshots"]["S5_final"]
    end = [r for r in reg if r["kind"] == "RUN_END"]
    problems = []
    if cl.get("cleanup_ok") is not True:
        problems.append("cleanup_ok %r" % cl.get("cleanup_ok"))
    if (cl.get("run_set") or {}).get("consistent") is not True:
        problems.append("run set not consistent")
    if not (k["DEAD"] and k["DEAD"][0].get("basis")):
        problems.append("no DEAD record with basis")
    if s5["children"]:
        problems.append("children left %r" % s5["children"])
    if s5.get("token_residue"):
        problems.append("token residue %r" % s5["token_residue"])
    if any(ev["snapshots"][n]["enum_problems"] for n in SNAPS):
        problems.append("incomplete /proc enumeration in a snapshot")
    if not end or end[0].get("cleanup_confirmed") is not True:
        problems.append("RUN_END not confirmed")
    return not problems, problems or "no residue"


def c14(ev, crit):
    a, b = ev["snapshots"]["S0_before_fork"]["fd_count"], ev["snapshots"]["S5_final"]["fd_count"]
    return a == b, "observer descriptors S0=%r S5=%r" % (a, b)


def c15(ev, crit):
    d = ev["timing"]["duration"]
    return (d <= crit["limits"]["max_seconds"] and not ev["deadline_hits"]), "duration %.3f s, deadline hits %r" % (d, ev["deadline_hits"])


def c16(ev, crit):
    missing = []
    for k in ("observer", "bindings_start", "bindings_end", "auth_expected", "guard", "node", "reg", "reap", "cleanup", "timing", "preflight", "events"):
        if k not in ev:
            missing.append(k)
    for n in SNAPS:
        if n not in ev.get("snapshots", {}) or "mono" not in ev["snapshots"][n]:
            missing.append("snapshot " + n)
    for k in EVENT_KEYS:
        if ev.get("events", {}).get(k) is None:
            missing.append("event " + k)
    return not missing, "missing %r" % missing


def c17(ev, crit):
    return (ev.get("exception") is None and ev.get("aborted") is None), "exception %r aborted %r" % (ev.get("exception"), ev.get("aborted"))


CHECKS = {"G0-C01": c01, "G0-C02": c02, "G0-C03": c03, "G0-C04": c04, "G0-C05": c05, "G0-C06": c06, "G0-C07": c07, "G0-C08": c08, "G0-C09": c09,
          "G0-C10": c10, "G0-C11": c11, "G0-C12": c12, "G0-C13": c13, "G0-C14": c14, "G0-C15": c15, "G0-C16": c16, "G0-C17": c17}


def judge(ev, crit=None):
    """-> {'verdict', 'exit_code', 'checks': {id: {status, on_fail, detail}}, 'fail_class': [...], 'blocked_class': [...]}"""
    crit = crit or load_criteria()
    assert set(CHECKS) == set(crit["checks"]), "judge and frozen criteria disagree on the check ids"
    out, fails, blocks = {}, [], []
    for cid in sorted(CHECKS):
        on_fail = crit["checks"][cid]["on_fail"]
        try:
            ok, detail = CHECKS[cid](ev, crit)
            status = "PASS" if ok else "FAIL_EVIDENCED"
        except (Uneval, KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
            ok, detail, status = False, "UNEVALUABLE: %s: %s" % (type(e).__name__, e), "UNEVALUABLE"
        out[cid] = {"status": status, "on_fail": on_fail, "name": crit["checks"][cid]["name"], "detail": detail}
        if status == "FAIL_EVIDENCED":
            (fails if on_fail == "FAIL" else blocks).append(cid)
        elif status == "UNEVALUABLE":
            blocks.append(cid)
    verdict = "FAIL" if fails else ("BLOCKED" if blocks else "PASS")
    return {"verdict": verdict, "exit_code": crit["exit_codes"][verdict], "checks": out, "fail_class": fails, "blocked_class": sorted(blocks)}
