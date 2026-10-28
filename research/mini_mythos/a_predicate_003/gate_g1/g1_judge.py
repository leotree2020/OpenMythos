"""G1 judge (PURE: dictionaries and bytes only; no process, no file access except load_criteria).  WRITTEN, NOT RUN.

Implements the FROZEN criteria g1_criteria_v1.json (E1A-GATE-G1-CRITERIA-V1; F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001):
  * G1-C01 .. G1-C17, judged for every test T1_ABORT, T2_EOF, T3_INVALID_BYTE, T4_TIMEOUT that ran (the run-level checks C01, C02, C16 and C17 are judged
    once and repeated in each test's row); G1-C03 (rules C03-F1..F3 / U0..U4), G1-C04 .. C07 and C10 with their F / U rules as written in the criteria;
  * M-2: G1-C04, C05, C11 and C13 read the durable registry copy and are UNEVALUABLE when it is not faithful to the writer's ledger;
  * the closure marker g1_closed.json (build / validate / classify); the closure facts and rules CL1-01 .. CL1-23 are the G0 engine applied to the G1 rules.
Four states are kept strictly apart: PASS, FAIL (an evaluable violation), UNEVALUABLE (evidence missing / untrustworthy / insufficient) and BLOCKED (the
verdict a check of class BLOCKED, or any UNEVALUABLE check, contributes).  Per test: any evaluable FAIL of a FAIL-class check -> FAIL, else any non-PASS
check -> BLOCKED, else PASS.  Run: any FAIL -> FAIL; else any BLOCKED, any non-PASS run-level check, or a test that did not run while every executed test
passed (RUN-INCOMPLETE) -> BLOCKED; else PASS.  NOT_RUN is never PASS.  A FAIL is a G1 bench/protocol failure, not evidence about the Mythos architecture.
Reuses (read-only) the strict-JSON helpers, type validators, disk-fidelity and closure engine of g0_judge.py; the G0 file is not modified."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(A003, "gate_g0"))
sys.path.insert(0, os.path.join(A003, "bench"))
import g0_judge as GJ  # noqa: E402
import g1_auth as G1A  # noqa: E402

is_int, is_num, Uneval, need = GJ.is_int, GJ.is_num, GJ.Uneval, GJ.need
strict_bytes, canon, sha256_hex, parse_strict = GJ.strict_bytes, GJ.canon, GJ.sha256_hex, GJ.parse_strict
fidelity, writer_clean = GJ.fidelity, GJ.writer_clean
classify_blob, closure_bindings, closure_reasons = GJ.classify_blob, GJ.closure_bindings, GJ.closure_reasons

CRITERIA_ID = G1A.CRITERIA_ID
TESTS = G1A.TESTS
SNAPS_TEST = ("S0_before_fork", "S1_held_registered_unreleased", "S1b_pre_stimulus", "S3_exited_unreaped", "S4_reaped", "S5_after_cleanup")
BIND_KEYS = G1A.BINDING_KEYS
EXIT_FOR = {"PASS": 0, "FAIL": 1, "BLOCKED": 3}
DISK_DEPENDENT = ("G1-C04", "G1-C05", "G1-C11", "G1-C13")                           # M-2 (witness_dependencies.disk_dependent_checks)
OWN_EVIDENCE = ("G1-C03", "G1-C07", "G1-C16")                                       # judge their own evidence (no generic consumer invalidation)
RUN_LEVEL = ("G1-C01", "G1-C02", "G1-C16", "G1-C17")
FAIL_SCOPE = "G1 bench/protocol failure; not evidence about the Mythos model architecture"
R_WRITE_CALL = "os.write(R)"                       # guard violation names shared with g1_run.py
RELEASE_CALL = "Observer.release"
R_BYTE = 82
NODE_ORDER = ("INTENT", "FORKED", "REGISTERED", "ABORTED", "DEAD")
MAX_REPORT = 50

T_BIND = ("object[10 hex strings: git_head prereg_sha256 g0_criteria_sha256 g0_prereg_sha256 bench_code_sha256 g0_code_sha256 g1_criteria_sha256 "
          "g1_prereg_sha256 g1_code_sha256 g0_reference_sha256]")
T_PREFLIGHT = ("object{ok:bool, problems:list, children:int, token_residue:list, unresolved_prior:list, enumeration_problems:object, run_id_unique:bool, "
               "fd_count:int, total_procs:int, g0_reference:object{ok:bool}}")
T_FORKS = "list[object{test:string, mono_before:number, mono_after:number|null, pid:int|null}]"
T_WAITS = "list[object{test:string, pid:int, options:int, returned:int, status:int, mono:number}]"
T_GWRITES = ("list[object{test:string, byte:int|null, mono_before:number, mono_after:number|null, result:string('ok'|'error'), returned:int|null, "
             "errno:int|null, error:string|null}]")
T_GCLOSES = "list[object{test:string, mono:number, fd:int}]"
T_OBSERVER = "object{pid:int, sid:int, pgrp:int}"
T_DIRINFO = "object{path:string, created_by_this_run:bool, uid:int, mode:int, ino:int}"
T_RUNDIR = "object{path:string, created_by_this_process:bool}"
T_NODE = "object{node_id:string, pid:int, starttime:int, gate_ino:int}"
T_REGS = "list[object{seq:int, kind:string, ...}]"
T_PARSE = "object{torn_tail:bool, corrupt_lines:int, missing:bool, unreadable:bool}"
T_RUNSET = "object{consistent:bool}"


def _bind10(v):
    if not isinstance(v, dict):
        return "not an object"
    for k in BIND_KEYS:
        if not isinstance(v.get(k), str) or not GJ.HEX_BIND.match(v[k]):
            return "key %r is not a lowercase hex digest" % k
    return None


_obj, _lst, _opt, _enum = GJ._obj, GJ._lst, GJ._opt, GJ._enum
_v_str, _v_int, _v_num, _v_bool, _v_list, _v_dict = GJ._v_str, GJ._v_int, GJ._v_num, GJ._v_bool, GJ._v_list, GJ._v_dict

TYPE_VALIDATORS = dict(GJ.TYPE_VALIDATORS)
TYPE_VALIDATORS.update({
    T_BIND: _bind10,
    T_PREFLIGHT: _obj({"ok": _v_bool, "problems": _v_list, "children": _v_int, "token_residue": _v_list, "unresolved_prior": _v_list,
                       "enumeration_problems": _v_dict, "run_id_unique": _v_bool, "fd_count": _v_int, "total_procs": _v_int,
                       "g0_reference": _obj({"ok": _v_bool})}),
    T_FORKS: _lst(_obj({"test": _v_str, "mono_before": _v_num, "mono_after": _opt(_v_num), "pid": _opt(_v_int)})),
    T_WAITS: _lst(_obj({"test": _v_str, "pid": _v_int, "options": _v_int, "returned": _v_int, "status": _v_int, "mono": _v_num})),
    T_GWRITES: _lst(_obj({"test": _v_str, "byte": _opt(_v_int), "mono_before": _v_num, "mono_after": _opt(_v_num), "result": _enum("ok", "error"),
                          "returned": _opt(_v_int), "errno": _opt(_v_int), "error": _opt(_v_str)})),
    T_GCLOSES: _lst(_obj({"test": _v_str, "mono": _v_num, "fd": _v_int})),
})


def load_criteria(path=None):
    with open(path or G1A.CRITERIA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ evidence schema validation (G1-C16, pipeline stage P4)
def _lookup(ev, path):
    cur = ev
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def validate_evidence(ev, crit):
    """Pipeline stage P4.  -> list of {path, problem, consumers}: a field that is missing, null where it may not be, of the wrong type, or declared with
    a type this judge has no validator for (never silently accepted).  A present field of the wrong type counts as missing."""
    out = []
    for f in crit["evidence_schema"]["fields"]:
        found, val = _lookup(ev, f["path"])
        if not found:
            out.append({"path": f["path"], "problem": "missing", "consumers": f["consumers"]})
        elif val is None:
            if not f["nullable"]:
                out.append({"path": f["path"], "problem": "null where the schema forbids null", "consumers": f["consumers"]})
        else:
            v = TYPE_VALIDATORS.get(f["type"])
            if v is None:
                out.append({"path": f["path"], "problem": "no validator for the declared type %r" % f["type"], "consumers": f["consumers"]})
            else:
                e = v(val)
                if e:
                    out.append({"path": f["path"], "problem": e, "consumers": f["consumers"]})
    return out


# ------------------------------------------------------------------ small helpers
def _res(ok, rule, detail):
    return {"state": "PASS" if ok else "FAIL", "rule": "" if ok else rule, "detail": detail}


def _fail(rule, detail):
    return {"state": "FAIL", "rule": rule, "detail": detail}


def _test(ev, tid):
    t = ev["tests"][tid]
    need(isinstance(t, dict), "test %s is not an object" % tid)
    return t


def _scn(crit, tid):
    return crit["scenarios"]["tests"][tid]


def _snap(t, name):
    s = t.get("snapshots")
    need(isinstance(s, dict) and isinstance(s.get(name), dict), "snapshot %s missing" % name)
    return s[name]


def _events(t):
    e = t.get("events")
    need(isinstance(e, dict), "events missing")
    return e


def _node(t):
    n = t.get("node")
    need(isinstance(n, dict) and isinstance(n.get("node_id"), str) and is_int(n.get("pid")) and is_int(n.get("starttime")), "node missing")
    return n


def _reg(ev):
    r = ev.get("reg")
    need(isinstance(r, list), "durable registry copy missing")
    return r


def _fork_event(ev, tid, rule=None):
    fes = [e for e in ev["guard"]["fork_events"] if isinstance(e, dict) and e.get("test") == tid]
    need(len(fes) == 1 and is_num(fes[0].get("mono_before")) and is_int(fes[0].get("pid")), "%d usable fork event(s) for the test" % len(fes), rule)
    return fes[0]


def _calls(ev, tid):
    return [c for c in ev["guard"]["waitpid_calls"] if isinstance(c, dict) and c.get("test") == tid]


def expected_kinds(crit, ran):
    """The ledger an executed prefix of the scenario order must show: RUN_START, the expected kinds of each executed test, RUN_END."""
    out = ["RUN_START"]
    for tid in ran:
        out += list(_scn(crit, tid)["expected_registry_kinds"])
    return out + ["RUN_END"]


# ------------------------------------------------------------------ G1-C03 (registration sequence and integrity)
def rule_f1(L, ctx):
    """C03-F1: a violation visible in the ledger itself.  -> sorted list of clause letters that fire."""
    out = set()
    kinds = [r["kind"] for r in L]
    ref = GJ._run_ref(L)
    if kinds.count("RUN_START") > 1 or kinds.count("RUN_END") > 1:
        out.add("a")
    per = {}
    for r in L:
        n = GJ._nid(r)
        if n is not None and r["kind"] in ("INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD"):
            per[(n, r["kind"])] = per.get((n, r["kind"]), 0) + 1
    if any(c > 1 for c in per.values()):
        out.add("a")
    if "RUN_START" in kinds and kinds.index("RUN_START") != 0:
        out.add("b")
    if "RUN_END" in kinds and kinds.index("RUN_END") != len(L) - 1:
        out.add("b")
    by_node = {}
    for i, r in enumerate(L):
        n = GJ._nid(r)
        if n is not None:
            by_node.setdefault(n, []).append((i, r["kind"]))
    for n, items in by_node.items():
        ks = [k for _, k in items]
        if "RELEASED" in ks and "ABORTED" in ks:
            out.add("b")
        order = [NODE_ORDER.index(k) for k in ks if k in NODE_ORDER]
        if order != sorted(order):
            out.add("b")
        if "DEAD" in ks and ks.index("DEAD") != len(ks) - 1:
            out.add("b")
    seqs = [r["seq"] for r in L]
    if any(seqs[i] <= seqs[i - 1] for i in range(1, len(seqs))):
        out.add("c")
    if any(not GJ._valid_record(r, ref) for r in L):
        out.add("d")
    ends = [r for r in L if r["kind"] == "RUN_END"]
    if any(r.get("cleanup_confirmed") is True for r in ends):
        intents = {GJ._nid(r) for r in L if r["kind"] == "INTENT"}
        dead = {GJ._nid(r) for r in L if r["kind"] == "DEAD"}
        abo = {GJ._nid(r) for r in L if r["kind"] == "ABORTED"}
        if any((n not in dead) for n in intents) or (abo - ctx["abort_nodes"]):
            out.add("e")
    return sorted(out)


def check_c03(ev, crit, tid, ctx):
    f = ctx["c03"]
    fid, ok_l, ok_w = f["fid"], f["ledger_ok"], f["writer_seq_ok"]
    L = ev["reg_memory_records"] if ok_l else None
    wc, completed = f["writer_clean"], f["completed_run"]
    no_foreign = (fid["foreign"] is False) if fid["available"] else None
    ran = ctx["ran"]
    exp_all = expected_kinds(crit, ran)
    t = ev["tests"][tid]
    scn_kinds = list(_scn(crit, tid)["expected_registry_kinds"])
    fired, clauses = [], []

    def fire(rid, why):
        fired.append((rid, why))
    if L is not None:
        c = rule_f1(L, ctx)
        if c:
            clauses = c
            fire("C03-F1", "clauses %s" % c)
        node = t.get("node") if isinstance(t, dict) else None
        nid = repr(node.get("node_id")) if isinstance(node, dict) and isinstance(node.get("node_id"), str) else None
        if wc is True and no_foreign is True and nid is not None:
            mine = [r["kind"] for r in L if GJ._nid(r) == nid]
            is_prefix = mine == scn_kinds[:len(mine)]
            if (not is_prefix) or (completed is True and mine != scn_kinds) or any(r["kind"] == "RELEASED" for r in L):
                fire("C03-F2", "kinds of the node %s %r differ from the expected %r" % (nid, mine, scn_kinds))
            intents = {GJ._nid(r) for r in L if r["kind"] == "INTENT"}
            if len(intents) > len(ran):
                fire("C03-F2", "%d nodes for %d executed tests" % (len(intents), len(ran)))
        if any(r["kind"] == "INTENT" and r.get("creator") != "O" for r in L):
            fire("C03-F3", "an INTENT whose creator is not 'O' (a ticket)")
    damage = []
    if fid["available"] and not fid["faithful"]:
        damage.append("durable copy not faithful")
    if wc is False:
        damage.append("writer not clean")
    if fid["available"] and fid["foreign"]:
        damage.append("foreign lines")
    if fired:
        rid = fired[0][0]
        return {"state": "FAIL", "rule": rid + ("(%s)" % ",".join(clauses) if rid == "C03-F1" else ""), "rules_matched": [r for r, _ in fired], "clauses": clauses,
                "detail": "; ".join("%s: %s" % x for x in fired), "credibility": {"level": "first-hand", "damage": damage},
                "report": fid["report"], "report_total": fid["total"]}
    if ok_l and ok_w and fid["available"] and completed is True and wc and fid["faithful"] and [r["kind"] for r in L] == exp_all:
        return {"state": "PASS", "rule": "", "rules_matched": [], "clauses": [], "detail": "sequence and integrity ok", "credibility": {"level": "first-hand", "damage": []},
                "report": [], "report_total": 0}
    matched = []
    if not (ok_l and ok_w and fid["available"]):
        matched.append("C03-U0")
    else:
        if not fid["faithful"] or fid["foreign"]:
            matched.append("C03-U2")
        if not wc:
            matched.append("C03-U3")
        kinds = [r["kind"] for r in L]
        if completed is False and wc and fid["faithful"] and kinds == exp_all[:len(kinds)] and len(kinds) < len(exp_all):
            matched.append("C03-U1")
        if not matched:
            matched.append("C03-U4")
    order = ["C03-U0", "C03-U2", "C03-U3", "C03-U1", "C03-U4"]
    matched.sort(key=order.index)
    return {"state": "UNEVALUABLE", "rule": matched[0], "rules_matched": matched, "clauses": [], "detail": "UNEVALUABLE %s" % matched,
            "credibility": {"level": "insufficient", "damage": damage}, "report": fid["report"], "report_total": fid["total"]}


def c03_facts(ev):
    L, ws, fid = ev.get("reg_memory_records"), ev.get("reg_writer_seq"), fidelity(ev)
    ledger_ok, ws_ok = GJ._is_rec_list(L), is_int(ws)
    return {"ledger_ok": ledger_ok, "writer_seq_ok": ws_ok, "fid": fid, "completed_run": GJ._completed(ev),
            "writer_clean": writer_clean(L, ws) if (ledger_ok and ws_ok) else None}


# ------------------------------------------------------------------ the other checks
def c01(ev, crit, tid, ctx):
    pf = ev["preflight"]
    g0 = pf.get("g0_reference")
    ok = (pf.get("ok") is True and not pf.get("problems") and pf.get("children") == 0 and not pf.get("token_residue") and not pf.get("unresolved_prior")
          and not pf.get("enumeration_problems") and pf.get("run_id_unique") is True and isinstance(g0, dict) and g0.get("ok") is True)
    return _res(ok, "C01", "preflight %s" % ({k: pf.get(k) for k in ("ok", "problems", "children", "token_residue", "unresolved_prior", "enumeration_problems",
                                                                      "run_id_unique", "g0_reference")} if not ok else "clean"))


def c02(ev, crit, tid, ctx):
    a, s, e = ev["auth_expected"], ev["bindings_start"], ev["bindings_end"]
    diffs = [k for k in BIND_KEYS if not (a.get(k) and a.get(k) == s.get(k) == e.get(k))]
    if a.get("g1_criteria_sha256") != G1A.FROZEN_G1_CRITERIA_SHA256:
        diffs.append("g1_criteria_sha256 is not the frozen G1 hash")
    if a.get("g1_prereg_sha256") != G1A.FROZEN_G1_PREREG_SHA256:
        diffs.append("g1_prereg_sha256 is not the frozen G1 text hash")
    if a.get("g0_criteria_sha256") != G1A.GA.FROZEN_CRITERIA_SHA256:
        diffs.append("g0_criteria_sha256 is not the frozen G0 V5 hash")
    if a.get("g0_prereg_sha256") != G1A.GA.FROZEN_PREREG_SHA256:
        diffs.append("g0_prereg_sha256 is not the frozen G0 V5 text hash")
    if a.get("g0_reference_sha256") != G1A.G0_REFERENCE["closed_sha256"]:
        diffs.append("g0_reference_sha256 is not the G0 REAL-001 closure marker hash")
    return _res(not diffs and ev.get("auth_consumed") is True, "C02", "binding differences %s, consumed=%s" % (diffs, ev.get("auth_consumed")))


def c04(ev, crit, tid, ctx):
    t = _test(ev, tid)
    s1, s1b = _snap(t, "S1_held_registered_unreleased"), _snap(t, "S1b_pre_stimulus")
    held, held_b = s1.get("child"), s1b.get("child")
    need(isinstance(held, dict) and isinstance(held_b, dict), "the child is absent from S1 or S1b", "C04-U2")
    node, evs = _node(t), _events(t)
    regs = [r for r in _reg(ev) if r.get("node_id") == node["node_id"] and r.get("kind") == "REGISTERED"]
    need(len(regs) == 1 and is_int(regs[0].get("pid")) and is_int(regs[0].get("starttime")) and is_num(regs[0].get("mono")),
         "durable copy has %d usable REGISTERED record(s) for the node" % len(regs), "C04-U2")
    reg = regs[0]
    fe = _fork_event(ev, tid, "C04-U2")
    pids = ev["guard"]["fork_pids"]
    idx = ctx["ran"].index(tid)
    need(len(pids) > idx, "no fork pid recorded for the test", "C04-U2")
    obs_pid = ev["observer"]["pid"]
    stim = evs.get("stimulus_mono")
    need(is_num(stim) and is_num(s1.get("mono")) and is_num(s1b.get("mono")) and is_num(t.get("t_gate_max")), "times missing", "C04-U2")
    pids_eq = reg["pid"] == held.get("pid") == held_b.get("pid") == fe["pid"] == pids[idx] == node["pid"]
    start_eq = reg["starttime"] == held.get("starttime") == held_b.get("starttime") == node["starttime"]
    ppid_ok = held.get("ppid") == held_b.get("ppid") == obs_pid
    before = reg["mono"] < stim
    if not (pids_eq and start_eq and ppid_ok and before):
        return _fail("C04-F1", "REGISTERED %r, S1 %r, S1b %r, fork pid %r, fork_pids[%d] %r, node %r, observer %r, REGISTERED before stimulus %r" % (
            {x: reg[x] for x in ("pid", "starttime")}, {x: held.get(x) for x in ("pid", "starttime", "ppid")}, {x: held_b.get(x) for x in ("pid", "starttime", "ppid")},
            fe["pid"], idx, pids[idx], {x: node[x] for x in ("pid", "starttime")}, obs_pid, before))
    margin = crit["limits"]["identity_margin_s"]
    late = [n for n, s in (("S1", s1), ("S1b", s1b)) if s["mono"] - fe["mono_before"] > t["t_gate_max"] - margin]
    need(not late, "%s taken less than %.2f s before the gate timer could expire (t_gate_max %.2f s after fork)" % (late, margin, t["t_gate_max"]), "C04-U1")
    return _res(True, "", "identity registered before the stimulus: pid/starttime/ppid agree in 7 places")


def c05(ev, crit, tid, ctx):
    t = _test(ev, tid)
    ob = ev["observer"]
    f1, u = [], []
    for name in ("S1_held_registered_unreleased", "S1b_pre_stimulus"):
        s = _snap(t, name)
        ch = s.get("child")
        need(isinstance(ch, dict), "child absent from %s" % name, "C05-U1")
        need(is_int(s.get("messages_received")), "messages_received missing in %s" % name, "C05-U1")
        if ch.get("state") != "S":
            u.append("%s: child state %r" % (name, ch.get("state")))
        if s["messages_received"] != 0 or s.get("first_action_mono") is not None:
            f1.append("%s: the child acted (messages %r, first_action %r)" % (name, s["messages_received"], s.get("first_action_mono")))
        if (ch.get("sid"), ch.get("pgrp")) != (ob["sid"], ob["pgrp"]):
            f1.append("%s: child sid/pgrp changed" % name)
    need(is_int(t.get("messages_received")) and isinstance(t.get("ready_received"), bool), "final message counters missing", "C05-U1")
    if t["messages_received"] != 0 or t["ready_received"] is not False or t.get("first_action_mono") is not None:
        f1.append("at exit: messages %r ready %r first_action %r" % (t["messages_received"], t["ready_received"], t.get("first_action_mono")))
    node = _node(t)
    if any(r.get("node_id") == node["node_id"] and r.get("kind") == "RELEASED" for r in _reg(ev)):
        f1.append("a RELEASED record exists")
    stim = t.get("stimulus")
    need(isinstance(stim, dict) and isinstance(stim.get("queued_spec"), bool), "stimulus.queued_spec missing", "C05-U1")
    if f1:
        return _fail("C05-F1", f1)
    if stim["queued_spec"] is not _scn(crit, tid)["stimulus"]["queued_spec"]:
        u.append("queued_spec %r differs from the scenario" % stim["queued_spec"])
    need(not u, "; ".join(u), "C05-U1")
    return _res(True, "", "no action without release")


def c06(ev, crit, tid, ctx):
    t = _test(ev, tid)
    gate = "pipe:[%d]" % _node(t)["gate_ino"]
    problems = []
    for name in ("S1_held_registered_unreleased", "S1b_pre_stimulus"):
        fds = _snap(t, name).get("fds")
        need(isinstance(fds, dict) and all(isinstance(v, dict) and isinstance(v.get("target"), str) for v in fds.values()), "descriptor list missing in %s" % name, "C06-U1")
        gate_fds = [(fd, v) for fd, v in fds.items() if v["target"] == gate]
        if len(gate_fds) != 1 or gate_fds[0][1].get("access") != "r":
            problems.append("%s: gate pipe descriptors %r" % (name, gate_fds))
        others = [(fd, v) for fd, v in fds.items() if v["target"] != gate and int(fd) > 2]
        if len(others) > 1 or any(not v["target"].startswith("socket:") for _, v in others):
            problems.append("%s: unexpected descriptors %r" % (name, others))
        if len(fds) > 5:
            problems.append("%s: %d descriptors" % (name, len(fds)))
    return _res(not problems, "C06-F1", problems or "descriptor hygiene ok")


def c07(ev, crit, tid, ctx):
    g = ev["guard"]
    viol, gw, gc = g.get("violations"), g.get("gate_writes"), g.get("gate_closes")
    need(isinstance(viol, list) and isinstance(gw, list) and isinstance(gc, list), "guard evidence missing", "C07-U1")
    need(not TYPE_VALIDATORS[T_GWRITES](gw) and not TYPE_VALIDATORS[T_GCLOSES](gc), "guard gate records are malformed", "C07-U1")
    f1 = [v for v in viol if isinstance(v, dict) and v.get("call") in (R_WRITE_CALL, RELEASE_CALL)]
    f1 += [w for w in gw if w.get("byte") == R_BYTE]
    if f1:
        return _fail("C07-F1", "an R write attempt or an Observer.release() call: %r" % f1)
    t = _test(ev, tid)
    plan = _scn(crit, tid)["stimulus"]
    node, evs = _node(t), _events(t)
    s1b = _snap(t, "S1b_pre_stimulus")
    need(is_num(s1b.get("mono")) and is_num(evs.get("pidfd_readable_mono")) and isinstance(t.get("stimulus"), dict), "times or stimulus record missing", "C07-U1")
    ledger = ev.get("reg_memory_records")                                  # the writer's own ledger: a RELEASED record is only ever written by Observer.release()
    need(isinstance(ledger, list), "writer ledger missing", "C07-U1")
    if any(isinstance(r, dict) and r.get("node_id") == node["node_id"] and r.get("kind") == "RELEASED" for r in ledger):
        return _fail("C07-F1", "a RELEASED record exists for the node")
    writes = [w for w in gw if w["test"] == tid]
    closes = [c for c in gc if c["test"] == tid]
    got = [w["byte"] for w in writes]
    if got != list(plan["planned_gate_bytes"]):
        return _fail("C07-F2", "gate bytes %r != planned %r" % (got, plan["planned_gate_bytes"]))
    bad_w = [w for w in writes if w["result"] != "ok" or w["returned"] != 1 or not is_num(w["mono_after"])]
    need(not bad_w, "a gate write did not complete: %r" % bad_w, "C07-U2")
    s1b_m, pr = s1b["mono"], evs["pidfd_readable_mono"]
    early = [x for x in [w["mono_before"] for w in writes] + [c["mono"] for c in closes] if x < s1b_m]
    if early:
        return _fail("C07-F3", "gate write/close at %r earlier than S1b (%r)" % (early, s1b_m))
    gate_open = t["stimulus"].get("gate_open_at_exit")
    need(isinstance(gate_open, bool), "gate_open_at_exit missing", "C07-U1")
    if plan["gate_write_end_closed_by_stimulus"]:
        inside = [c for c in closes if s1b_m <= c["mono"] <= pr]
        need(closes, "the planned close of the gate write end was not recorded", "C07-U3")
        if len(closes) != 1 or len(inside) != 1 or gate_open is not False:
            return _fail("C07-F3", "closes %r (window %r..%r), gate_open_at_exit %r" % (closes, s1b_m, pr, gate_open))
        if writes and closes[0]["mono"] < max(w["mono_after"] for w in writes):
            return _fail("C07-F3", "the gate was closed before the planned byte was written")
    else:
        if any(c["mono"] < pr for c in closes) or gate_open is not True or len(closes) > 1:
            return _fail("C07-F3", "T4-style silent gate: closes %r before the exit at %r, gate_open_at_exit %r" % (closes, pr, gate_open))
    return _res(True, "", "writes %r and closes %d as planned, no R, no release" % (got, len(closes)))


def c08(ev, crit, tid, ctx):
    t = _test(ev, tid)
    s3, evs = _snap(t, "S3_exited_unreaped"), _events(t)
    need(is_num(s3.get("mono")) and is_num(evs.get("stimulus_mono")) and is_num(evs.get("pidfd_readable_mono")), "times missing")
    obs_pid = ev["observer"]["pid"]
    early = [c for c in _calls(ev, tid) if c["mono"] < s3["mono"]]
    problems = []
    ch = s3.get("child")
    if not isinstance(ch, dict) or ch.get("state") != "Z" or ch.get("ppid") != obs_pid:
        problems.append("S3 child %r (need state Z, ppid %d)" % (ch, obs_pid))
    if early:
        problems.append("wait call before the unreaped observation: %r" % early)
    if not (evs["stimulus_mono"] <= evs["pidfd_readable_mono"] <= s3["mono"]):
        problems.append("stimulus/pidfd/S3 times not ordered")
    return _res(not problems, "C08", problems or "exited-unreaped observed before any wait")


def c09(ev, crit, tid, ctx):
    t = _test(ev, tid)
    node, evs = _node(t), _events(t)
    s3, s4 = _snap(t, "S3_exited_unreaped"), _snap(t, "S4_reaped")
    need(is_num(s3.get("mono")) and is_num(evs.get("reap_mono")) and is_num(evs.get("proc_gone_mono")), "times missing")
    calls = _calls(ev, tid)
    pid = node["pid"]
    problems = []
    if any(c["pid"] != pid for c in calls):
        problems.append("a wait call named another pid: %r" % [c["pid"] for c in calls])
    ret = [c for c in calls if c["returned"] == pid]
    if len(ret) != 1:
        problems.append("%d wait calls returned the child pid" % len(ret))
    elif not (s3["mono"] < ret[0]["mono"] <= evs["proc_gone_mono"]):
        problems.append("times EXITED_UNREAPED < REAPED <= PROC_GONE violated")
    if any(c["returned"] not in (0, pid) for c in calls):
        problems.append("a wait call returned neither 0 nor the child pid: %r" % [c["returned"] for c in calls])
    if isinstance(s4.get("child"), dict) and s4["child"].get("starttime") == node["starttime"]:
        problems.append("child still present in /proc after reap")
    if not evs["reap_mono"] >= s3["mono"]:
        problems.append("reap_mono before S3")
    return _res(not problems, "C09", problems or "reaped by specific pid, /proc entry gone")


def c10(ev, crit, tid, ctx):
    t = _test(ev, tid)
    scn = _scn(crit, tid)
    reap, evs = t.get("reap"), _events(t)
    need(isinstance(reap, dict) and is_int(reap.get("exit_status")), "reap evidence missing", "C10-U2")
    code = reap["exit_status"]
    if code == 0:
        return _fail("C10-F1", "exit status 0: the child passed the gate and finished its role")
    if code in (111, 112):
        if code != scn["expected_exit"]:
            return _fail("C10-F2", "exit status %d, expected %d" % (code, scn["expected_exit"]))
        if "timing" in scn:
            fe = _fork_event(ev, tid, "C10-U2")
            need(is_num(evs.get("pidfd_readable_mono")), "exit observation time missing", "C10-U2")
            earliest = fe["mono_before"] + scn["timing"]["exit_not_before_s_after_reference"]
            if evs["pidfd_readable_mono"] < earliest:
                return _fail("C10-F3", "112 observed %.3f s after the fork; the timer cannot fire before %.3f s" % (evs["pidfd_readable_mono"] - fe["mono_before"],
                                                                                                              scn["timing"]["exit_not_before_s_after_reference"]))
        return _res(True, "", "exit status %d as expected" % code)
    raise Uneval("exit status %r is not a gate-path status (113 = exception outside the gate, negative = killed by a signal)" % code, "C10-U1")


def c11(ev, crit, tid, ctx):
    t = _test(ev, tid)
    node = _node(t)
    ran = ctx["ran"]
    g = ev["guard"]
    need(is_int(g.get("fork_calls")), "fork_calls missing")
    fe = _fork_event(ev, tid)
    problems = []
    if g["fork_calls"] > len(ran):
        problems.append("fork calls %r for %d executed tests" % (g["fork_calls"], len(ran)))
    need(g["fork_calls"] == len(ran) or problems, "fork calls %r for %d executed tests" % (g["fork_calls"], len(ran)))
    if fe["pid"] != node["pid"]:
        problems.append("fork event pid %r != node pid %r" % (fe["pid"], node["pid"]))
    idx = ran.index(tid)
    if idx > 0:
        prev = _events(_test(ev, ran[idx - 1]))
        need(is_num(prev.get("reap_mono")), "reap time of the previous test missing")
        if not prev["reap_mono"] < fe["mono_before"]:
            problems.append("the previous child was not reaped before this fork")
    for name in SNAPS_TEST:
        s = _snap(t, name)
        need(isinstance(s.get("children"), list) and isinstance(s.get("grandchildren"), list), "children lists missing in %s" % name)
        if len(s["children"]) > 1 or s["grandchildren"]:
            problems.append("%s: children %r grandchildren %r" % (name, s["children"], s["grandchildren"]))
    if _snap(t, "S0_before_fork")["children"]:
        problems.append("S0: the observer already has a child")
    intents = [r for r in _reg(ev) if r.get("kind") == "INTENT"]
    mine = [r for r in intents if r.get("node_id") == node["node_id"]]
    if len(mine) != 1 or len(intents) != len(ran) or any(r.get("creator") != "O" for r in intents):
        problems.append("registry nodes/tickets: %r" % [(r.get("node_id"), r.get("creator")) for r in intents])
    return _res(not problems, "C11", problems or "one fork per test, one child, no descendants, no tickets")


def c12(ev, crit, tid, ctx):
    viol = ev["guard"]["violations"]
    need(isinstance(viol, list), "guard violations missing")
    t = _test(ev, tid)
    cl = t.get("cleanup")
    need(isinstance(cl, dict) and isinstance(cl.get("rounds"), list), "cleanup report missing")
    rounds = list(cl["rounds"])
    if tid == ctx["last_ran"] and isinstance(ev.get("cleanup"), dict) and isinstance(ev["cleanup"].get("rounds"), list):
        rounds += ev["cleanup"]["rounds"]
    kills = [x for rnd in rounds if isinstance(rnd, dict) for key in ("kill", "kill_unregistered_direct") for x in rnd.get(key, [])]
    bad = [x for x in kills if not (isinstance(x, dict) and x.get("result") == "already_exited")]
    return _res(not viol and not bad, "C12-F1", "violations %r, non-trivial kill entries %r" % (viol, bad))


def c13(ev, crit, tid, ctx):
    t = _test(ev, tid)
    node = _node(t)
    cl = t.get("cleanup")
    need(isinstance(cl, dict), "cleanup report missing")
    reg = _reg(ev)
    dead = [r for r in reg if r.get("node_id") == node["node_id"] and r.get("kind") == "DEAD"]
    problems = []
    if cl.get("cleanup_ok") is not True:
        problems.append("cleanup_ok %r" % cl.get("cleanup_ok"))
    if not (dead and dead[0].get("basis")):
        problems.append("no DEAD record with basis")
    for name in ("S4_reaped", "S5_after_cleanup"):
        if _snap(t, name).get("children"):
            problems.append("%s: children left %r" % (name, _snap(t, name)["children"]))
    for name in SNAPS_TEST:
        if _snap(t, name).get("enum_problems"):
            problems.append("incomplete /proc enumeration in %s" % name)
    if tid == ctx["last_ran"]:
        rc = ev.get("cleanup")
        need(isinstance(rc, dict), "final run cleanup missing")
        if rc.get("cleanup_ok") is not True:
            problems.append("final cleanup_ok %r" % rc.get("cleanup_ok"))
        if (rc.get("run_set") or {}).get("consistent") is not True:
            problems.append("run set not consistent")
        end = [r for r in reg if r.get("kind") == "RUN_END"]
        if not end or end[0].get("cleanup_confirmed") is not True:
            problems.append("RUN_END not confirmed")
        rs = ev.get("run_snapshots")
        need(isinstance(rs, dict) and isinstance(rs.get("S9_final"), dict), "final run snapshot missing")
        s9 = rs["S9_final"]
        if s9.get("children"):
            problems.append("S9: children left %r" % s9["children"])
        if s9.get("token_residue"):
            problems.append("token residue %r" % s9["token_residue"])
        if s9.get("enum_problems"):
            problems.append("incomplete /proc enumeration in S9")
    return _res(not problems, "C13", problems or "no residue")


def c14(ev, crit, tid, ctx):
    t = _test(ev, tid)
    a, b = _snap(t, "S0_before_fork").get("fd_count"), _snap(t, "S5_after_cleanup").get("fd_count")
    need(is_int(a) and is_int(b), "descriptor counts missing")
    problems = []
    if a != b:
        problems.append("test descriptors S0=%r S5=%r" % (a, b))
    if tid == ctx["last_ran"]:
        rs = ev.get("run_snapshots")
        need(isinstance(rs, dict) and isinstance(rs.get("S0_run"), dict) and isinstance(rs.get("S9_final"), dict), "run snapshots missing")
        c, d = rs["S0_run"].get("fd_count"), rs["S9_final"].get("fd_count")
        need(is_int(c) and is_int(d), "run descriptor counts missing")
        if c != d:
            problems.append("run descriptors S0_run=%r S9=%r" % (c, d))
    return _res(not problems, "C14", problems or "observer descriptors at baseline")


def c15(ev, crit, tid, ctx):
    t = _test(ev, tid)
    lim = crit["limits"]
    tm, evs = t.get("timing"), _events(t)
    need(isinstance(tm, dict) and is_num(tm.get("duration")), "no measured test duration")
    need(isinstance(ev.get("timing"), dict) and is_num(ev["timing"].get("duration")), "no measured run duration")
    need(is_num(evs.get("pidfd_readable_mono")) and is_num(evs.get("stimulus_mono")), "times missing")
    problems = []
    if tm["duration"] > lim["per_test_seconds"]:
        problems.append("test took %.3f s (limit %.1f)" % (tm["duration"], lim["per_test_seconds"]))
    if ev["timing"]["duration"] > lim["max_seconds"]:
        problems.append("run took %.3f s (limit %.1f)" % (ev["timing"]["duration"], lim["max_seconds"]))
    if ev["deadline_hits"]:
        problems.append("deadline hits %r" % ev["deadline_hits"])
    scn = _scn(crit, tid)
    if "timing" in scn:
        fe = _fork_event(ev, tid)
        if evs["pidfd_readable_mono"] - fe["mono_before"] > scn["timing"]["exit_not_after_s_after_reference"]:
            problems.append("exit observed later than %.1f s after the fork" % scn["timing"]["exit_not_after_s_after_reference"])
    elif evs["pidfd_readable_mono"] - evs["stimulus_mono"] > lim["exit_deadline_s"]:
        problems.append("exit observed later than %.1f s after the stimulus" % lim["exit_deadline_s"])
    return _res(not problems, "C15", problems or "within the time bounds")


def c16(ev, crit, tid, ctx):
    bad = list(ctx["invalid"])
    sid = crit["evidence_schema"]["id"]
    if ev.get("evidence_schema") != sid:
        bad.append({"path": "evidence_schema", "problem": "must equal %r" % sid, "consumers": "C16"})
    return _res(not bad, "C16", "evidence complete and typed" if not bad else "%d field problem(s): %r" % (len(bad), [(x["path"], x["problem"]) for x in bad[:20]]))


def c17(ev, crit, tid, ctx):
    need("exception" in ev and "aborted" in ev, "exception / aborted missing")
    problems = []
    if ev["exception"] is not None or ev["aborted"] is not None:
        problems.append("exception %r aborted %r" % (ev["exception"], ev["aborted"]))
    if ev.get("manual_disposition") is not None:
        problems.append("manual disposition required: %r" % ev["manual_disposition"])
    tests = ev["tests"]
    flags = [bool(isinstance(tests.get(x), dict) and tests[x].get("ran") is True) for x in crit["scenarios"]["order"]]
    if flags != sorted(flags, reverse=True):
        problems.append("the tests that ran are not a prefix of the scenario order: %r" % flags)
    for x in crit["scenarios"]["order"]:
        if isinstance(tests.get(x), dict) and tests[x].get("exception") is not None:
            problems.append("%s exception %r" % (x, str(tests[x]["exception"])[:200]))
    return _res(not problems, "C17", problems or "no unexplained error")


FUNCS = {"G1-C01": c01, "G1-C02": c02, "G1-C03": check_c03, "G1-C04": c04, "G1-C05": c05, "G1-C06": c06, "G1-C07": c07, "G1-C08": c08, "G1-C09": c09,
         "G1-C10": c10, "G1-C11": c11, "G1-C12": c12, "G1-C13": c13, "G1-C14": c14, "G1-C15": c15, "G1-C16": c16, "G1-C17": c17}
CHECK_IDS = tuple("G1-C%02d" % i for i in range(1, 18))


def _consumed_invalid(cid, invalid, tid):
    short = cid[3:]
    out = []
    for x in invalid:
        if short not in x["consumers"].split():
            continue
        p = x["path"]
        if p.startswith("tests."):
            if tid is None or not p.startswith("tests.%s." % tid):
                continue
        out.append(x)
    return out


def _run_check(cid, ev, crit, tid, ctx):
    try:
        if cid in DISK_DEPENDENT:
            fid = ctx["fid"]
            need(fid["available"] and fid["faithful"] is True, "M-2: the durable copy is not faithful to the ledger (see the C03 fidelity report); %s is not evaluated" % cid, "M-2")
        if cid not in OWN_EVIDENCE:
            bad = _consumed_invalid(cid, ctx["invalid"], tid)
            need(not bad, "evidence field(s) missing or of the wrong type: %r" % [(x["path"], x["problem"]) for x in bad[:6]], "C16")
        return FUNCS[cid](ev, crit, tid, ctx)
    except Uneval as e:
        return {"state": "UNEVALUABLE", "rule": e.rule or "", "detail": "UNEVALUABLE: %s" % e}
    except (KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
        return {"state": "UNEVALUABLE", "rule": "", "detail": "UNEVALUABLE: %s: %s" % (type(e).__name__, e)}


def _entry(cid, r, crit):
    spec = crit["checks"][cid]
    status = {"PASS": "PASS", "FAIL": "FAIL_EVIDENCED", "UNEVALUABLE": "UNEVALUABLE"}[r["state"]]
    return dict(r, status=status, on_fail=spec["on_fail"], name=spec["name"])


def _classify(entries):
    """-> (fails, blocks) check ids of one row."""
    fails, blocks = [], []
    for cid, e in entries.items():
        if e["status"] == "FAIL_EVIDENCED":
            (fails if e["on_fail"] == "FAIL" else blocks).append(cid)
        elif e["status"] == "UNEVALUABLE":
            blocks.append(cid)
    return fails, sorted(blocks)


def judge(ev, crit=None, criteria_sha256=None, validation=None):
    """-> {'verdict', 'exit_code', 'run_checks', 'tests': {tid: {verdict, ran, checks, fail_class, blocked_class}}, 'fail_class', 'blocked_class',
    'incomplete', 'invalid_fields', 'c03_fidelity_report'}.  Does not modify `ev`.  `validation` is the result of validate_evidence(ev, crit) when the
    pipeline already ran P4."""
    crit = crit or load_criteria()
    assert set(CHECK_IDS) == set(crit["checks"]), "judge and frozen criteria disagree on the check ids"
    if not isinstance(ev, dict):
        ev = {}
    order = list(crit["scenarios"]["order"])
    assert tuple(order) == tuple(TESTS), "judge and frozen criteria disagree on the test order"
    invalid = validate_evidence(ev, crit) if validation is None else validation
    tests = ev.get("tests") if isinstance(ev.get("tests"), dict) else {}
    ev_view = ev if tests is ev.get("tests") else dict(ev, tests={})
    ran = [x for x in order if isinstance(tests.get(x), dict) and tests[x].get("ran") is True]
    abort_nodes = set()
    for x in ran:
        if "ABORTED" in _scn(crit, x)["expected_registry_kinds"] and isinstance(tests[x].get("node"), dict) and isinstance(tests[x]["node"].get("node_id"), str):
            abort_nodes.add(repr(tests[x]["node"]["node_id"]))
    ctx = {"invalid": invalid, "fid": fidelity(ev), "criteria_sha256": criteria_sha256, "ran": ran, "last_ran": ran[-1] if ran else None,
           "c03": c03_facts(ev), "abort_nodes": abort_nodes}
    run_checks = {cid: _entry(cid, _run_check(cid, ev_view, crit, None, ctx), crit) for cid in CHECK_IDS if cid in RUN_LEVEL}
    run_fails, run_blocks = _classify(run_checks)
    rows, fails_all, blocks_all = {}, [], []
    for tid in order:
        if tid not in ran:
            rows[tid] = {"verdict": "NOT_RUN", "ran": False, "checks": {}, "fail_class": [], "blocked_class": []}
            continue
        entries = {}
        for cid in CHECK_IDS:
            entries[cid] = run_checks[cid] if cid in RUN_LEVEL else _entry(cid, _run_check(cid, ev_view, crit, tid, ctx), crit)
        fails, blocks = _classify(entries)
        rows[tid] = {"verdict": "FAIL" if fails else ("BLOCKED" if blocks else "PASS"), "ran": True, "checks": entries, "fail_class": fails, "blocked_class": blocks}
        fails_all += ["%s:%s" % (tid, c) for c in fails if c not in RUN_LEVEL]
        blocks_all += ["%s:%s" % (tid, c) for c in blocks if c not in RUN_LEVEL]
    fails_all += ["RUN:%s" % c for c in run_fails]
    blocks_all += ["RUN:%s" % c for c in run_blocks]
    verdicts = [rows[x]["verdict"] for x in ran]
    not_run = [x for x in order if x not in ran]
    incomplete = bool(not_run) and all(v == "PASS" for v in verdicts) and not run_fails and not run_blocks
    if run_fails or "FAIL" in verdicts:
        verdict = "FAIL"
    elif run_blocks or "BLOCKED" in verdicts or incomplete or not ran:
        verdict = "BLOCKED"
        if (incomplete or not ran) and "RUN-INCOMPLETE" not in blocks_all:
            blocks_all.append("RUN-INCOMPLETE")
    else:
        verdict = "PASS"
    assert crit["exit_codes"][verdict] == EXIT_FOR[verdict], "exit-code policy of the criteria differs from the judge"
    c03_report = rows[ran[0]]["checks"]["G1-C03"].get("report", []) if ran else []
    return {"verdict": verdict, "exit_code": crit["exit_codes"][verdict], "run_checks": run_checks, "tests": rows, "fail_class": fails_all,
            "blocked_class": sorted(set(blocks_all)), "incomplete": incomplete or (not ran), "invalid_fields": invalid, "c03_fidelity_report": c03_report}


IN_RUN_CHECKS = ("G1-C04", "G1-C05", "G1-C06", "G1-C07", "G1-C08", "G1-C09", "G1-C10", "G1-C11", "G1-C12", "G1-C13", "G1-C14", "G1-C15")


def judge_test_in_run(ev, crit, tid):
    """The in-run safety rule (criteria enforcement.stop_rule: stop after the first test that is not clearly as expected).  Judges ONE test of a run that is
    still in progress with the very check functions of judge(), restricted to the checks that do not need the end of the run (no RUN_START / RUN_END ledger
    comparison -> no G1-C03, no run-level C01 / C02 / C16 / C17, and the last-test parts of C12 / C13 / C14 are skipped).  `ev` is a view of the evidence so far
    (guard summary, ledger, parsed registry, tests).  Nothing here is a verdict: the authoritative verdict is judge() on the read-back evidence.
    -> {'verdict': 'PASS' | 'FAIL' | 'BLOCKED', 'non_pass': {check id: 'STATE/rule'}}; any non-PASS stops the run."""
    order = list(crit["scenarios"]["order"])
    tests = ev.get("tests") if isinstance(ev.get("tests"), dict) else {}
    ran = [x for x in order if isinstance(tests.get(x), dict) and tests[x].get("ran") is True]
    if tid not in ran:
        return {"verdict": "BLOCKED", "non_pass": {"RUN": "the test is not marked as run"}}
    ctx = {"invalid": [], "fid": fidelity(ev), "criteria_sha256": None, "ran": ran, "last_ran": None, "c03": c03_facts(ev), "abort_nodes": set()}
    entries = {cid: _entry(cid, _run_check(cid, ev, crit, tid, ctx), crit) for cid in IN_RUN_CHECKS}
    fails, blocks = _classify(entries)
    non_pass = {cid: "%s/%s" % (e["state"], e.get("rule", "")) for cid, e in entries.items() if e["status"] != "PASS"}
    return {"verdict": "FAIL" if fails else ("BLOCKED" if blocks else "PASS"), "non_pass": non_pass}


# ------------------------------------------------------------------ the closure marker g1_closed.json
MARKER_KEYS = ("closed_schema", "run_id", "criteria_id", "criteria_sha256", "evidence_sha256", "evidence_bytes", "summary_sha256", "summary_bytes",
               "recorded_verdict", "recorded_exit_code", "process_exit_proof")
MARKER_SCHEMA = "e1a-gate-g1-closed-1"
MARKER_MAX_BYTES = 4096
RUN_ID_RE = G1A.ID_RE


def marker_object_problems(o):
    """-> list of problems of an already parsed marker object (empty = schema valid)."""
    if not isinstance(o, dict):
        return ["not an object"]
    bad = []
    if set(o) != set(MARKER_KEYS):
        bad.append("keys differ: missing %s, extra %s" % (sorted(set(MARKER_KEYS) - set(o)), sorted(set(o) - set(MARKER_KEYS))))
        return bad
    if o["closed_schema"] != MARKER_SCHEMA:
        bad.append("closed_schema")
    if not (isinstance(o["run_id"], str) and RUN_ID_RE.match(o["run_id"]) and o["run_id"].startswith("g1_")):
        bad.append("run_id")
    if o["criteria_id"] != CRITERIA_ID:
        bad.append("criteria_id")
    for k in ("criteria_sha256", "evidence_sha256", "summary_sha256"):
        if not (isinstance(o[k], str) and GJ.HEX64.match(o[k])):
            bad.append(k)
    for k in ("evidence_bytes", "summary_bytes"):
        if not (is_int(o[k]) and o[k] >= 1):
            bad.append(k)
    if not (isinstance(o["recorded_verdict"], str) and is_int(o["recorded_exit_code"]) and EXIT_FOR.get(o["recorded_verdict"]) == o["recorded_exit_code"]):
        bad.append("recorded_verdict / recorded_exit_code pair")
    if o["process_exit_proof"] is not False:
        bad.append("process_exit_proof must be false")
    return bad


def build_marker(run_id, criteria_sha256, evidence_bytes, summary_bytes, verdict, exit_code):
    """K1.  -> (object, bytes).  Raises ValueError when the result would not be a valid marker."""
    o = {"closed_schema": MARKER_SCHEMA, "run_id": run_id, "criteria_id": CRITERIA_ID, "criteria_sha256": criteria_sha256,
         "evidence_sha256": sha256_hex(evidence_bytes), "evidence_bytes": len(evidence_bytes), "summary_sha256": sha256_hex(summary_bytes),
         "summary_bytes": len(summary_bytes), "recorded_verdict": verdict, "recorded_exit_code": exit_code, "process_exit_proof": False}
    bad = marker_object_problems(o)
    if bad:
        raise ValueError("closure marker would be invalid: %s" % bad)
    b = strict_bytes(o)
    if len(b) > MARKER_MAX_BYTES:
        raise ValueError("closure marker larger than %d bytes" % MARKER_MAX_BYTES)
    return o, b


def classify_marker(raw):
    """Fact `closed` for bytes that were read from a regular file.  -> (state, object or None); state in oversize_or_empty, unparsable,
    noncanonical, schema_invalid, ok."""
    if not isinstance(raw, (bytes, bytearray)) or len(raw) == 0 or len(raw) > MARKER_MAX_BYTES:
        return "oversize_or_empty", None
    try:
        o = parse_strict(bytes(raw))
    except (ValueError, RecursionError):
        return "unparsable", None
    if marker_object_problems(o):
        return "schema_invalid", None
    try:
        again = strict_bytes(o)
    except (TypeError, ValueError):
        return "schema_invalid", None
    if again != bytes(raw):
        return "noncanonical", o
    return "ok", o
