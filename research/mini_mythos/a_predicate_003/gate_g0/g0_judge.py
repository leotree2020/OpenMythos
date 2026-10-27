"""G0 judge (PURE: dictionaries and bytes only; no process, no file access except load_criteria).  WRITTEN, NOT RUN.

Implements the FROZEN criteria g0_criteria_v5.json (E1A-GATE-G0-CRITERIA-V5; F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001):
  * G0-C01 .. G0-C17 with the frozen decision rules; G0-C03 (rules C03-F1..F4 / U0..U5 and the requirements table), G0-C07 (rules C07-F1..F3 /
    U1..U7) and G0-C16 (evidence schema) exactly as written in the criteria;
  * M-2: G0-C04, C05, C11 and C13 read the durable registry copy and are UNEVALUABLE when it is not faithful to the writer's ledger;
  * the closure marker g0_closed.json (build / validate / classify) and the historical-run closure rules CL-01 .. CL-23 (closure_reasons).
Four states are kept strictly apart: PASS, FAIL (an evaluable violation), UNEVALUABLE (evidence missing / untrustworthy / insufficient) and
BLOCKED (the verdict a check of class BLOCKED, or any UNEVALUABLE check, contributes).  A check whose evidence is missing is UNEVALUABLE;
FAIL needs evidence.  Verdict: any evaluable FAIL of a FAIL-class check -> FAIL, else any non-PASS check -> BLOCKED, else PASS.
A FAIL is a G0 bench/protocol failure; it is not evidence about the Mythos model architecture, R3 or Parcae."""
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bench"))
import g0_auth as GA  # noqa: E402

SNAPS = ("S0_before_fork", "S1_held_registered_unreleased", "S2_ready_after_release", "S3_exited_unreaped", "S4_reaped", "S5_final")
BIND_KEYS = ("git_head", "prereg_sha256", "g0_criteria_sha256", "g0_prereg_sha256", "bench_code_sha256", "g0_code_sha256")
LIFE = ("RUN_START", "INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD")          # lifecycle positions 0..5 (RUN_END is separate)
ORDER = LIFE + ("RUN_END",)
EXIT_FOR = {"PASS": 0, "FAIL": 1, "BLOCKED": 3}
DISK_DEPENDENT = ("G0-C04", "G0-C05", "G0-C11", "G0-C13")                           # M-2 (witness_dependencies.disk_dependent_checks)
OWN_EVIDENCE = ("G0-C03", "G0-C07", "G0-C16")                                       # judge their own evidence (no generic consumer invalidation)
FAIL_SCOPE = "G0 bench/protocol failure; not evidence about the Mythos model architecture"
MAX_REPORT = 50
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX_BIND = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")


def load_criteria(path=None):
    with open(path or GA.CRITERIA_PATH, encoding="utf-8") as f:
        return json.load(f)


class Uneval(Exception):
    """A check cannot be evaluated; `rule` names the frozen rule (e.g. 'C03-U0') when there is one."""

    def __init__(self, why, rule=None):
        Exception.__init__(self, why)
        self.rule = rule


def need(cond, why, rule=None):
    if not cond:
        raise Uneval(why, rule)


# ------------------------------------------------------------------ strict JSON helpers (shared by the pipeline and the closure marker)
def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def strict_bytes(obj):
    """The only serialisation of evidence, summary and closure marker: no default= argument, so nothing is silently converted; NaN refused."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canon(rec):
    """canon(record) of the criteria: the record as read back from JSON, sorted keys, compact separators, NaN refused."""
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def _reject_constant(name):
    raise ValueError("non-finite JSON constant %s refused" % name)


def _no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate object key %r" % (k,))
        out[k] = v
    return out


def parse_strict(raw):
    """bytes -> JSON value.  UTF-8 only; duplicate keys, NaN and Infinity are refused.  Raises ValueError (UnicodeDecodeError is one)."""
    return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys)


# ------------------------------------------------------------------ evidence schema validation (G0-C16, pipeline stage P4)
def _ok(v, pred, what):
    return None if pred(v) else "not %s" % what


def _v_str(v):
    return _ok(v, lambda x: isinstance(x, str), "a string")


def _v_int(v):
    return _ok(v, is_int, "an int (bool is not an int)")


def _v_num(v):
    return _ok(v, is_num, "a finite number (bool is not a number)")


def _v_bool(v):
    return _ok(v, lambda x: isinstance(x, bool), "a bool")


def _v_list(v):
    return _ok(v, lambda x: isinstance(x, list), "a list")


def _v_dict(v):
    return _ok(v, lambda x: isinstance(x, dict), "an object")


def _opt(f):
    return lambda v: None if v is None else f(v)


def _lst(f):
    def g(v):
        if not isinstance(v, list):
            return "not a list"
        for i, x in enumerate(v):
            e = f(x)
            if e:
                return "item %d: %s" % (i, e)
        return None
    return g


def _obj(fields):
    """fields: {key: validator}; extra keys are ignored (criteria: 'extra keys are ignored')."""
    def g(v):
        if not isinstance(v, dict):
            return "not an object"
        for k, f in fields.items():
            if k not in v:
                return "key %r missing" % k
            e = f(v[k])
            if e:
                return "key %r: %s" % (k, e)
        return None
    return g


def _enum(*vals):
    return lambda v: None if (isinstance(v, str) and v in vals) else "not one of %r" % (vals,)


def _bind6(v):
    if not isinstance(v, dict):
        return "not an object"
    for k in BIND_KEYS:
        if not isinstance(v.get(k), str) or not HEX_BIND.match(v[k]):
            return "key %r is not a lowercase hex digest" % k
    return None


def _fds(v):
    if not isinstance(v, dict):
        return "not an object"
    for k, x in v.items():
        if not (isinstance(k, str) and k.isdigit()):
            return "descriptor key %r is not a decimal string" % (k,)
        e = _obj({"target": _v_str, "access": _opt(_v_str)})(x)
        if e:
            return "fd %s: %s" % (k, e)
    return None


T_BIND_A = "object[6 hex strings: git_head prereg_sha256 g0_criteria_sha256 g0_prereg_sha256 bench_code_sha256 g0_code_sha256]"
T_BIND_B = "object[same 6 keys]"
T_OBSERVER = "object{pid:int, sid:int, pgrp:int}"
T_PREFLIGHT = ("object{ok:bool, problems:list, children:int, token_residue:list, unresolved_prior:list, enumeration_problems:object, "
               "run_id_unique:bool, fd_count:int, total_procs:int}")
T_DIRINFO = "object{path:string, created_by_this_run:bool, uid:int, mode:int, ino:int}"
T_RUNDIR = "object{path:string, created_by_this_process:bool}"
T_NODE = "object{node_id:string, pid:int, starttime:int, gate_ino:int}"
T_FDS = "object{fd:{target:string, access:string|null}}"
T_WAITS = "list[object{pid:int, options:int, returned:int, status:int, mono:number}]"
T_RELW = ("list[object{mono_before:number, mono_after:number|null, result:string('ok'|'error'), returned:int|null, errno:int|null, "
          "error:string|null}]")
T_RUNSET = "object{consistent:bool}"
T_REGS = "list[object{seq:int, kind:string, ...}]"
T_PARSE = "object{torn_tail:bool, corrupt_lines:int, missing:bool, unreadable:bool}"

TYPE_VALIDATORS = {
    "string": _v_str,
    T_BIND_A: _bind6,
    T_BIND_B: _bind6,
    "bool": _v_bool,
    T_OBSERVER: _obj({"pid": _v_int, "sid": _v_int, "pgrp": _v_int}),
    T_PREFLIGHT: _obj({"ok": _v_bool, "problems": _v_list, "children": _v_int, "token_residue": _v_list, "unresolved_prior": _v_list,
                       "enumeration_problems": _v_dict, "run_id_unique": _v_bool, "fd_count": _v_int, "total_procs": _v_int}),
    T_DIRINFO: _obj({"path": _v_str, "created_by_this_run": _v_bool, "uid": _v_int, "mode": _v_int, "ino": _v_int}),
    T_RUNDIR: _obj({"path": _v_str, "created_by_this_process": _v_bool}),
    T_NODE: _obj({"node_id": _v_str, "pid": _v_int, "starttime": _v_int, "gate_ino": _v_int}),
    "number": _v_num,
    "list[int]": _lst(_v_int),
    "int": _v_int,
    "object": _v_dict,
    "list": _v_list,
    T_FDS: _fds,
    T_WAITS: _lst(_obj({"pid": _v_int, "options": _v_int, "returned": _v_int, "status": _v_int, "mono": _v_num})),
    T_RELW: _lst(_obj({"mono_before": _v_num, "mono_after": _opt(_v_num), "result": _enum("ok", "error"), "returned": _opt(_v_int),
                       "errno": _opt(_v_int), "error": _opt(_v_str)})),
    T_RUNSET: _obj({"consistent": _v_bool}),
    "list[string]": _lst(_v_str),
    T_REGS: _lst(_obj({"seq": _v_int, "kind": _v_str})),
    T_PARSE: _obj({"torn_tail": _v_bool, "corrupt_lines": _v_int, "missing": _v_bool, "unreadable": _v_bool}),
}


def _lookup(ev, path):
    cur = ev
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def validate_evidence(ev, crit):
    """Pipeline stage P4.  -> list of {path, problem, consumers}: a field that is missing, null where it may not be, of the wrong type, or
    declared with a type this judge has no validator for (never silently accepted).  A present field of the wrong type counts as missing."""
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


# ------------------------------------------------------------------ the ledger / durable-copy witnesses (G0-C03 definitions)
def _is_rec_list(x):
    return isinstance(x, list) and all(isinstance(r, dict) and is_int(r.get("seq")) and isinstance(r.get("kind"), str) for r in x)


def _triple(r):
    return canon([r.get("seq"), r.get("kind"), r.get("node_id")])


def _info_ok(info):
    return (isinstance(info, dict) and all(isinstance(info.get(k), bool) for k in ("torn_tail", "missing", "unreadable"))
            and is_int(info.get("corrupt_lines")))


def _prefix(r):
    return canon(r)[:200]


def fidelity(ev):
    """Durable copy vs ledger on WHOLE canonical records (F-20, M-1).  Never raises.
    -> {available, faithful, foreign, parse_clean, report, total}; faithful / foreign are None when an input is missing or of the wrong type."""
    L, D, info = ev.get("reg_memory_records"), ev.get("reg"), ev.get("reg_parse_info")
    if not (_is_rec_list(L) and _is_rec_list(D) and _info_ok(info)):
        return {"available": False, "faithful": None, "foreign": None, "parse_clean": None, "report": [], "total": 0}
    try:
        cl, cd = [canon(r) for r in L], [canon(r) for r in D]
        tl, td = [_triple(r) for r in L], [_triple(r) for r in D]
    except (TypeError, ValueError):
        return {"available": False, "faithful": None, "foreign": None, "parse_clean": None, "report": [], "total": 0}
    parse_clean = (info["missing"] is False and info["unreadable"] is False and info["torn_tail"] is False and info["corrupt_lines"] == 0)
    same_count = len(D) == len(L)
    equal = same_count and all(a == b for a, b in zip(cd, cl))
    faithful = bool(parse_clean and same_count and equal)
    set_l, set_d = set(tl), set(td)
    foreign = any(t not in set_l for t in td)
    report = []
    if not faithful:
        if not parse_clean:
            report.append({"type": "PARSE", "missing": info["missing"], "unreadable": info["unreadable"], "torn_tail": info["torn_tail"],
                           "corrupt_lines": info["corrupt_lines"]})
        if not same_count:
            report.append({"type": "COUNT", "ledger": len(L), "durable": len(D)})
        for i, r in enumerate(L):
            if tl[i] not in set_d:
                report.append({"type": "LOST", "index": i, "seq": r.get("seq"), "kind": r.get("kind"), "node_id": r.get("node_id"),
                               "ledger_canon_prefix": cl[i][:200], "durable_canon_prefix": None})
        for j, r in enumerate(D):
            if td[j] not in set_l:
                report.append({"type": "FOREIGN", "index": j, "seq": r.get("seq"), "kind": r.get("kind"), "node_id": r.get("node_id"),
                               "ledger_canon_prefix": None, "durable_canon_prefix": cd[j][:200]})
        for i in range(min(len(L), len(D))):
            if cl[i] != cd[i] and tl[i] == td[i]:
                names = sorted(k for k in set(L[i]) | set(D[i]) if canon(L[i].get(k, "<absent>")) != canon(D[i].get(k, "<absent>")))
                report.append({"type": "ALTERED", "index": i, "seq": L[i].get("seq"), "kind": L[i].get("kind"), "node_id": L[i].get("node_id"), "fields": names,
                               "ledger_canon_prefix": cl[i][:200], "durable_canon_prefix": cd[i][:200]})
        if parse_clean and same_count and not equal and not any(e["type"] in ("LOST", "FOREIGN", "ALTERED") for e in report):
            idx = next(i for i in range(len(L)) if cl[i] != cd[i])           # same records in another order
            report.append({"type": "ALTERED", "index": idx, "seq": L[idx].get("seq"), "kind": L[idx].get("kind"), "node_id": L[idx].get("node_id"),
                           "fields": ["<position>"], "ledger_canon_prefix": cl[idx][:200], "durable_canon_prefix": cd[idx][:200]})
    return {"available": True, "faithful": faithful, "foreign": foreign, "parse_clean": parse_clean, "report": report[:MAX_REPORT], "total": len(report)}


def writer_clean(L, writer_seq):
    """the seq values of the ledger are exactly 1..n AND reg_writer_seq == n (no append failed)"""
    return [r["seq"] for r in L] == list(range(1, len(L) + 1)) and writer_seq == len(L)


def _valid_record(r, run_ref):
    """The type and value tests of C03-F1(d) for one record (any kind)."""
    k = r["kind"]
    if k == "RUN_START":
        return isinstance(r.get("run_id"), str) and bool(r["run_id"]) and is_int(r.get("observer_pid"))
    if k == "RUN_END":
        ok_run = isinstance(r.get("run_id"), str) and bool(r["run_id"]) and (run_ref is None or r["run_id"] == run_ref)
        return ok_run and isinstance(r.get("cleanup_confirmed"), bool)
    if k == "INTENT":
        return isinstance(r.get("node_id"), str) and isinstance(r.get("creator"), str)
    if k == "FORKED":
        return is_int(r.get("pid"))
    if k == "REGISTERED":
        return is_int(r.get("pid")) and is_int(r.get("starttime"))
    if k == "DEAD":
        return isinstance(r.get("basis"), str) and bool(r["basis"])
    return True


def _run_ref(L):
    for r in L:
        if r["kind"] == "RUN_START":
            return r.get("run_id") if (isinstance(r.get("run_id"), str) and r["run_id"]) else None
    return None


def _valid_of_kind(L, kind):
    ref = _run_ref(L)
    return [r for r in L if r["kind"] == kind and _valid_record(r, ref)]


def _nid(r):
    return repr(r.get("node_id")) if "node_id" in r else None


def rule_f1(L):
    """C03-F1: a violation visible in the ledger itself.  -> list of clause letters that fire (empty = none)."""
    out = set()
    kinds = [r["kind"] for r in L]
    first = {}
    for i, k in enumerate(kinds):
        first.setdefault(k, i)
    ref = _run_ref(L)
    # (a) duplicates
    if kinds.count("RUN_START") > 1 or kinds.count("RUN_END") > 1:
        out.add("a")
    per = {}
    for r in L:
        n = _nid(r)
        if n is not None and r["kind"] in ("INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD"):
            per[(n, r["kind"])] = per.get((n, r["kind"]), 0) + 1
    if any(c > 1 for c in per.values()):
        out.add("a")
    # (b) order
    pos = [first[k] for k in ORDER if k in first]
    if pos != sorted(pos):
        out.add("b")
    if "RUN_START" in first and first["RUN_START"] != 0:
        out.add("b")
    if "RUN_END" in first and first["RUN_END"] != len(L) - 1:
        out.add("b")
    dead_at = {}
    for i, r in enumerate(L):
        if r["kind"] == "DEAD" and _nid(r) is not None:
            dead_at.setdefault(_nid(r), i)
    for i, r in enumerate(L):
        if _nid(r) in dead_at and i > dead_at[_nid(r)]:
            out.add("b")
    rel = {_nid(r) for r in L if r["kind"] == "RELEASED"} - {None}
    abo = {_nid(r) for r in L if r["kind"] == "ABORTED"} - {None}
    if rel & abo:
        out.add("b")
    # (c) seq strictly increasing
    seqs = [r["seq"] for r in L]
    if any(seqs[i] <= seqs[i - 1] for i in range(1, len(seqs))):
        out.add("c")
    # (d) field types and values
    if any(not _valid_record(r, ref) for r in L):
        out.add("d")
    # (e) RUN_END confirms cleanup while the node has no DEAD or has an ABORTED
    ends = [r for r in L if r["kind"] == "RUN_END"]
    if any(r.get("cleanup_confirmed") is True for r in ends):
        nodes = {_nid(r) for r in L if r["kind"] == "INTENT"}
        dead = {_nid(r) for r in L if r["kind"] == "DEAD"}
        if any((n not in dead) or (n in abo) for n in nodes):
            out.add("e")
    # (f) exactly one node, no ticket
    intents = [r for r in L if r["kind"] == "INTENT"]
    if len({_nid(r) for r in intents}) > 1 or len({_nid(r) for r in L if _nid(r) is not None}) > 1 or any(r.get("creator") != "O" for r in intents):
        out.add("f")
    return sorted(out)


def has_hole(L):
    """C03 definitions.hole (+ the 'record while RUN_START is absent' clause of C03-F2)."""
    present = {k for k in LIFE if any(r["kind"] == k for r in L)}
    aborted = any(r["kind"] == "ABORTED" for r in L)
    for p, k in enumerate(LIFE):
        if k in present:
            continue
        if aborted and k in ("REGISTERED", "RELEASED"):
            continue
        if any(LIFE.index(q) > p for q in present):
            return True
    if "RUN_START" not in present and any(r["kind"] != "RUN_END" for r in L):
        return True
    return False


def tail_absence(L):
    present = [LIFE.index(k) for k in LIFE if any(r["kind"] == k for r in L)]
    absent = [LIFE.index(k) for k in LIFE if not any(r["kind"] == k for r in L)]
    return all(a > p for a in absent for p in present)


def independent(ev):
    """The independent witnesses (guard, child event).  -> dict with `available` (bool) and the C03 definitions; never raises."""
    g, e = ev.get("guard"), ev.get("events")
    pids = g.get("fork_pids") if isinstance(g, dict) else None
    rw = g.get("release_writes") if isinstance(g, dict) else None
    # Format-damaged guard evidence is NOT evidence: a record that does not have the schema type (wrong container, missing key, string / bool / NaN time,
    # unknown result, ...) makes the whole witness unavailable, so no FAIL rule can be derived from it (the checks then end UNEVALUABLE).
    if not (isinstance(pids, list) and isinstance(rw, list)) or TYPE_VALIDATORS["list[int]"](pids) or TYPE_VALIDATORS[T_RELW](rw):
        return {"available": False}
    fa = e.get("first_action_mono") if isinstance(e, dict) else None
    gate_passed = is_num(fa)

    def wrote(x):
        return x.get("result") == "ok" and is_int(x.get("returned")) and x.get("returned") == 1 and is_num(x.get("mono_after"))
    ok_writes = [x for x in rw if wrote(x)]
    proven = bool(len(ok_writes) >= 1 and gate_passed and len(rw) == 1 and ok_writes and is_num(rw[0].get("mono_after")) and fa >= rw[0]["mono_after"])
    return {"available": True, "fork_proven": len(pids) > 0, "release_attempt": len(rw) > 0, "release_write_ok": bool(ok_writes), "gate_passed": gate_passed,
            "gate_pass_proven": proven, "gate_pass_unconfirmed": bool(gate_passed and not proven), "release_writes": rw, "first_action": fa if gate_passed else None}


def _completed(ev):
    if not ("exception" in ev and "aborted" in ev and isinstance(ev.get("deadline_hits"), list)):
        return None
    if not ((ev["exception"] is None or isinstance(ev["exception"], str)) and (ev["aborted"] is None or isinstance(ev["aborted"], str))):
        return None
    return ev["exception"] is None and ev["aborted"] is None and ev["deadline_hits"] == []


def c03_facts(ev):
    """Everything C03 derives from the evidence (None entries = not derivable).  Pure; never raises."""
    L, ws, fid = ev.get("reg_memory_records"), ev.get("reg_writer_seq"), fidelity(ev)
    ledger_ok = _is_rec_list(L)
    ws_ok = is_int(ws)
    f = {"ledger_ok": ledger_ok, "writer_seq_ok": ws_ok, "durable_ok": fid["available"], "fid": fid, "completed_run": _completed(ev), "ind": independent(ev)}
    f["writer_clean"] = writer_clean(L, ws) if (ledger_ok and ws_ok) else None
    return f


def check_c03(ev, crit):
    f = c03_facts(ev)
    fid, ind = f["fid"], f["ind"]
    L = ev["reg_memory_records"] if f["ledger_ok"] else None
    wc, completed = f["writer_clean"], f["completed_run"]
    no_foreign = (fid["foreign"] is False) if fid["available"] else None
    facts = {"writer_clean": wc, "disk_faithful": fid["faithful"], "foreign_lines": fid["foreign"], "completed_run": completed,
             "independent_available": ind["available"]}
    for k in ("fork_proven", "release_attempt", "release_write_ok", "gate_passed", "gate_pass_proven", "gate_pass_unconfirmed"):
        facts[k] = ind.get(k)
    fired, clauses = [], []

    def fire(rid, why):
        fired.append((rid, why))
    if L is not None:
        c = rule_f1(L)
        if c:
            clauses = c
            fire("C03-F1", "clauses %s" % c)
        if wc is True and no_foreign is True and has_hole(L):
            fire("C03-F2", "hole in the ledger")
        v_int, v_reg, v_rel = _valid_of_kind(L, "INTENT"), _valid_of_kind(L, "REGISTERED"), _valid_of_kind(L, "RELEASED")
        if wc is True and no_foreign is True and ind["available"] and ind["fork_proven"] and not v_int:
            fire("C03-F3a", "fork proven, no valid INTENT")
        if wc is True and no_foreign is True and ind["available"] and ind["release_write_ok"] and (not v_reg or not v_rel):
            fire("C03-F3b", "release write ok, no valid REGISTERED / RELEASED")
        if no_foreign is True and ind["available"] and ind["gate_pass_proven"] and (not v_reg or not v_rel):
            fire("C03-F3c", "gate pass proven, no valid REGISTERED / RELEASED (applies despite an append failure)")
        if wc is True and no_foreign is True and completed is True:
            kinds = {r["kind"] for r in L}
            dead_ok = bool(_valid_of_kind(L, "DEAD"))
            if any(k not in kinds for k in ORDER if k != "DEAD") or not dead_ok or "ABORTED" in kinds:
                fire("C03-F4", "completed run, incomplete ledger")
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
                "detail": "; ".join("%s: %s" % x for x in fired), "facts": facts, "credibility": {"level": "first-hand", "damage": damage},
                "report": fid["report"], "report_total": fid["total"]}
    if (f["ledger_ok"] and f["writer_seq_ok"] and fid["available"] and completed is True and wc and fid["faithful"]
            and [r["kind"] for r in L] == list(ORDER)):
        return {"state": "PASS", "rule": "", "rules_matched": [], "clauses": [], "detail": "sequence and integrity ok", "facts": facts,
                "credibility": {"level": "first-hand", "damage": []}, "report": [], "report_total": 0}
    matched = []
    if not (f["ledger_ok"] and f["writer_seq_ok"] and fid["available"]):
        matched.append("C03-U0")
    else:
        if not fid["faithful"] or fid["foreign"]:
            matched.append("C03-U2")
        if not wc:
            matched.append("C03-U3")
        v_int, v_reg, v_rel = _valid_of_kind(L, "INTENT"), _valid_of_kind(L, "REGISTERED"), _valid_of_kind(L, "RELEASED")
        if ind["available"] and ((ind["fork_proven"] and not v_int) or (ind["release_write_ok"] and (not v_reg or not v_rel))
                                 or (ind["gate_passed"] and (not v_reg or not v_rel))):
            matched.append("C03-U5")
        if completed is False and tail_absence(L) and wc and fid["faithful"]:
            matched.append("C03-U1")
        if not matched:
            matched.append("C03-U4")
    order = ["C03-U0", "C03-U2", "C03-U3", "C03-U5", "C03-U1", "C03-U4"]
    matched.sort(key=order.index)
    return {"state": "UNEVALUABLE", "rule": matched[0], "rules_matched": matched, "clauses": [], "facts": facts,
            "detail": "UNEVALUABLE %s (facts %r)" % (matched, facts), "credibility": {"level": "insufficient", "damage": damage},
            "report": fid["report"], "report_total": fid["total"]}


# ------------------------------------------------------------------ G0-C07 (release evidence)
def check_c07(ev, crit):
    ind = independent(ev)
    L = ev.get("reg_memory_records")
    if not ind["available"] or not _is_rec_list(L):
        return {"state": "UNEVALUABLE", "rule": "C07-U5", "rules_matched": ["C07-U5"], "detail": "required evidence missing or of the wrong type (guard / ledger)"}
    rw, fa = ind["release_writes"], ind["first_action"]
    # "REGISTERED and RELEASED times taken from the ledger": the time of the first such record that carries one.  Whether the record is VALID is
    # judged by G0-C03 (F1(d), F3), not here -- a REGISTERED record with an unusable starttime still has a time.
    reg_m = next((r.get("mono") for r in L if r["kind"] == "REGISTERED" and is_num(r.get("mono"))), None)
    rel_m = next((r.get("mono") for r in L if r["kind"] == "RELEASED" and is_num(r.get("mono"))), None)
    b0 = rw[0].get("mono_before") if rw else None
    fired = []
    if (reg_m is not None and rel_m is not None and reg_m > rel_m) or (rel_m is not None and is_num(b0) and rel_m > b0):
        fired.append("C07-F1")
    if len(rw) > 1:
        fired.append("C07-F2")
    if rw and ind["gate_passed"] and is_num(b0) and fa < b0:
        fired.append("C07-F3")
    if fired:
        return {"state": "FAIL", "rule": fired[0], "rules_matched": fired, "detail": "evidenced: %s (REGISTERED %r, RELEASED %r, release_writes %r, first_action %r)" % (fired, reg_m, rel_m, rw, fa)}
    ok_entry = rw[0] if len(rw) == 1 else None
    success = [x for x in rw if x.get("result") == "ok" and is_int(x.get("returned")) and x.get("returned") == 1 and is_num(x.get("mono_after"))]
    if (ok_entry is not None and success and is_num(b0) and is_num(ok_entry.get("mono_after")) and reg_m is not None and rel_m is not None and is_num(fa)
            and reg_m <= rel_m <= b0 <= ok_entry["mono_after"] <= fa):
        return {"state": "PASS", "rule": "", "rules_matched": [], "detail": "attempt, success and gate pass in order"}
    attempt, passed = ind["release_attempt"], ind["gate_passed"]
    m = []
    if not attempt and not passed:
        m.append("C07-U1")
    if attempt and not success and not passed:
        m.append("C07-U2")
    if success and not passed:
        m.append("C07-U3")
    if passed and not attempt:
        m.append("C07-U4")
    times_missing = (reg_m is None or rel_m is None or any(not is_num(x.get("mono_before")) for x in rw) or any(x.get("result") == "ok" and not is_num(x.get("mono_after")) for x in rw)
                     or (passed and not is_num(fa)))
    if times_missing:
        m.append("C07-U5")
    if passed and attempt and not success:
        m.append("C07-U6")
    if passed and success and any(is_num(x.get("mono_before")) and is_num(x.get("mono_after")) and x["mono_before"] <= fa < x["mono_after"] for x in success):
        m.append("C07-U7")
    if not m:
        m.append("C07-U5")
    return {"state": "UNEVALUABLE", "rule": m[0], "rules_matched": m, "detail": "UNEVALUABLE %s" % m}


# ------------------------------------------------------------------ the other checks
def _node_rec(ev, kind, one=True):
    reg, nid = ev["reg"], ev["node"]["node_id"]
    rs = [r for r in reg if r.get("node_id") == nid and r.get("kind") == kind]
    need(len(rs) == 1 if one else len(rs) >= 1, "durable copy has %d %s record(s) for the node" % (len(rs), kind))
    return rs[0]


def c01(ev, crit, ctx):
    pf = ev["preflight"]
    ok = (pf.get("ok") is True and not pf.get("problems") and pf.get("children") == 0 and not pf.get("token_residue") and not pf.get("unresolved_prior")
          and not pf.get("enumeration_problems") and pf.get("run_id_unique") is True)
    return ok, "preflight %s" % ({k: pf.get(k) for k in ("ok", "problems", "children", "token_residue", "unresolved_prior", "enumeration_problems", "run_id_unique")} if not ok else "clean")


def c02(ev, crit, ctx):
    # The frozen text of G0-C02 says "bound to THIS criteria file (V2)": a historical wording error; the binding that is required is the V5 hash.
    a, s, e = ev["auth_expected"], ev["bindings_start"], ev["bindings_end"]
    diffs = [k for k in BIND_KEYS if not (a.get(k) and a.get(k) == s.get(k) == e.get(k))]
    if a.get("g0_criteria_sha256") != GA.FROZEN_CRITERIA_SHA256:
        diffs.append("g0_criteria_sha256 is not the frozen V5 hash")
    if a.get("g0_prereg_sha256") != GA.FROZEN_PREREG_SHA256:
        diffs.append("g0_prereg_sha256 is not the frozen V5 text hash")
    return (not diffs and ev.get("auth_consumed") is True), "binding differences %s, consumed=%s" % (diffs, ev.get("auth_consumed"))


def c04(ev, crit, ctx):
    held = ev["snapshots"]["S1_held_registered_unreleased"]["child"]
    need(isinstance(held, dict), "no held child in S1")
    reg_rec = _node_rec(ev, "REGISTERED")
    obs_pid = ev["observer"]["pid"]
    pids = ev["guard"]["fork_pids"]
    need(len(pids) >= 1, "no fork pid recorded")
    ok = (reg_rec.get("pid") == held.get("pid") == pids[0] and reg_rec.get("starttime") == held.get("starttime") and held.get("ppid") == obs_pid)
    return ok, "registered %r vs held %r, fork pids %r, observer %r" % ({x: reg_rec.get(x) for x in ("pid", "starttime")}, {x: held.get(x) for x in ("pid", "starttime", "ppid")}, pids, obs_pid)


def c05(ev, crit, ctx):
    rel = _node_rec(ev, "RELEASED")
    s1 = ev["snapshots"]["S1_held_registered_unreleased"]
    ch, ob = s1["child"], ev["observer"]
    need(isinstance(ch, dict), "no held child in S1")
    fa = ev["events"]["first_action_mono"]
    need(is_num(fa) and is_num(rel.get("mono")), "FIRST_ACTION or RELEASED time missing")
    problems = []
    if ch.get("state") != "S":
        problems.append("held child state %r" % ch.get("state"))
    if s1["messages_received"] != 0 or s1["first_action_mono"] is not None:
        problems.append("child acted before release")
    if (ch.get("sid"), ch.get("pgrp")) != (ob["sid"], ob["pgrp"]):
        problems.append("child sid/pgrp changed")
    if not fa >= rel["mono"]:
        problems.append("FIRST_ACTION earlier than RELEASED")
    return not problems, problems or "no action before release"


def c06(ev, crit, ctx):
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


def c08(ev, crit, ctx):
    s3 = ev["snapshots"]["S3_exited_unreaped"]
    obs_pid = ev["observer"]["pid"]
    early = [c for c in ev["guard"]["waitpid_calls"] if c["mono"] < s3["mono"]]
    problems = []
    if not s3["child"] or s3["child"].get("state") != "Z" or s3["child"].get("ppid") != obs_pid:
        problems.append("S3 child %r (need state Z, ppid %d)" % (s3["child"], obs_pid))
    if early:
        problems.append("wait call before the unreaped observation: %r" % early)
    if not (ev["events"]["exit_sent_mono"] < ev["events"]["pidfd_readable_mono"] <= s3["mono"]):
        problems.append("EXIT/pidfd/S3 times not ordered")
    return not problems, problems or "exited-unreaped observed before any wait"


def c09(ev, crit, ctx):
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
    if any(c["returned"] not in (0, pid) for c in calls):
        problems.append("a wait call returned neither 0 nor the child pid: %r" % [c["returned"] for c in calls])
    if s4["child"] is not None and s4["child"].get("starttime") == st:
        problems.append("child still present in /proc after reap")
    if not ev["events"]["reap_mono"] >= s3["mono"]:
        problems.append("reap_mono before S3")
    return not problems, problems or "reaped by specific pid, /proc entry gone"


def c10(ev, crit, ctx):
    return ev["reap"]["exit_status"] == 0, "exit status %r" % ev["reap"]["exit_status"]


def c11(ev, crit, ctx):
    reg = ev["reg"]
    problems = []
    if ev["guard"]["fork_calls"] != 1:
        problems.append("fork calls %r" % ev["guard"]["fork_calls"])
    for name in SNAPS:
        s = ev["snapshots"][name]
        if len(s["children"]) > 1 or s["grandchildren"]:
            problems.append("%s: children %r grandchildren %r" % (name, s["children"], s["grandchildren"]))
    intents = [r for r in reg if r.get("kind") == "INTENT"]
    if len(intents) != 1 or any(r.get("creator") != "O" for r in intents):
        problems.append("registry nodes/tickets: %r" % [(r.get("node_id"), r.get("creator")) for r in intents])
    return not problems, problems or "one fork, one child, no descendants, no tickets"


def c12(ev, crit, ctx):
    viol = ev["guard"]["violations"]
    kills = [x for rnd in ev["cleanup"]["rounds"] for key in ("kill", "kill_unregistered_direct") for x in rnd.get(key, [])]
    bad = [x for x in kills if x.get("result") != "already_exited"]
    return (not viol and not bad), "violations %r, non-trivial kill entries %r" % (viol, bad)


def c13(ev, crit, ctx):
    cl = ev["cleanup"]
    reg = ev["reg"]
    s5 = ev["snapshots"]["S5_final"]
    nid = ev["node"]["node_id"]
    dead = [r for r in reg if r.get("node_id") == nid and r.get("kind") == "DEAD"]
    end = [r for r in reg if r.get("kind") == "RUN_END"]
    problems = []
    if cl.get("cleanup_ok") is not True:
        problems.append("cleanup_ok %r" % cl.get("cleanup_ok"))
    if (cl.get("run_set") or {}).get("consistent") is not True:
        problems.append("run set not consistent")
    if not (dead and dead[0].get("basis")):
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


def c14(ev, crit, ctx):
    a, b = ev["snapshots"]["S0_before_fork"]["fd_count"], ev["snapshots"]["S5_final"]["fd_count"]
    return a == b, "observer descriptors S0=%r S5=%r" % (a, b)


def c15(ev, crit, ctx):
    d = ev["timing"]["duration"]
    need(is_num(d), "no measured duration")
    return (d <= crit["limits"]["max_seconds"] and not ev["deadline_hits"]), "duration %.3f s, deadline hits %r" % (d, ev["deadline_hits"])


def c16(ev, crit, ctx):
    bad = list(ctx["invalid"])
    sid = crit["evidence_schema"]["id"]
    if ev.get("evidence_schema") != sid:
        bad.append({"path": "evidence_schema", "problem": "must equal %r" % sid, "consumers": "C16"})
    return not bad, ("evidence complete and typed" if not bad else "%d field problem(s): %r" % (len(bad), [(x["path"], x["problem"]) for x in bad[:20]]))


def c17(ev, crit, ctx):
    need("exception" in ev and "aborted" in ev, "exception / aborted missing")
    return (ev["exception"] is None and ev["aborted"] is None), "exception %r aborted %r" % (ev["exception"], ev["aborted"])


SIMPLE = {"G0-C01": c01, "G0-C02": c02, "G0-C04": c04, "G0-C05": c05, "G0-C06": c06, "G0-C08": c08, "G0-C09": c09, "G0-C10": c10, "G0-C11": c11,
          "G0-C12": c12, "G0-C13": c13, "G0-C14": c14, "G0-C15": c15, "G0-C16": c16, "G0-C17": c17}
CHECK_IDS = tuple("G0-C%02d" % i for i in range(1, 18))


def _consumed_invalid(cid, invalid):
    short = cid[3:]
    return [x for x in invalid if short in x["consumers"].split()]


def _run_simple(cid, ev, crit, ctx):
    try:
        if cid in DISK_DEPENDENT:
            fid = ctx["fid"]
            need(fid["available"] and fid["faithful"] is True, "M-2: the durable copy is not faithful to the ledger (see the C03 fidelity report); %s is not evaluated" % cid, "M-2")
        if cid not in OWN_EVIDENCE:
            bad = _consumed_invalid(cid, ctx["invalid"])
            need(not bad, "evidence field(s) missing or of the wrong type: %r" % [(x["path"], x["problem"]) for x in bad[:6]], "C16")
        ok, detail = SIMPLE[cid](ev, crit, ctx)
        return {"state": "PASS" if ok else "FAIL", "rule": "", "detail": detail}
    except Uneval as e:
        return {"state": "UNEVALUABLE", "rule": e.rule or "", "detail": "UNEVALUABLE: %s" % e}
    except (KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
        return {"state": "UNEVALUABLE", "rule": "", "detail": "UNEVALUABLE: %s: %s" % (type(e).__name__, e)}


def judge(ev, crit=None, criteria_sha256=None, validation=None):
    """-> {'verdict', 'exit_code', 'checks': {id: {status, state, on_fail, name, rule, detail, ...}}, 'fail_class', 'blocked_class', 'invalid_fields',
    'c03_fidelity_report'}.  Does not modify `ev`.  `validation` is the result of validate_evidence(ev, crit) when the pipeline already ran P4."""
    crit = crit or load_criteria()
    assert set(CHECK_IDS) == set(crit["checks"]), "judge and frozen criteria disagree on the check ids"
    invalid = validate_evidence(ev, crit) if validation is None else validation
    ctx = {"invalid": invalid, "fid": fidelity(ev), "criteria_sha256": criteria_sha256}
    out, fails, blocks = {}, [], []
    for cid in CHECK_IDS:
        spec = crit["checks"][cid]
        if cid == "G0-C03":
            try:
                r = check_c03(ev, crit)
            except (KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
                r = {"state": "UNEVALUABLE", "rule": "C03-U0", "rules_matched": ["C03-U0"], "detail": "UNEVALUABLE: %s: %s" % (type(e).__name__, e), "report": [], "report_total": 0}
        elif cid == "G0-C07":
            try:
                r = check_c07(ev, crit)
            except (KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
                r = {"state": "UNEVALUABLE", "rule": "C07-U5", "rules_matched": ["C07-U5"], "detail": "UNEVALUABLE: %s: %s" % (type(e).__name__, e)}
        else:
            r = _run_simple(cid, ev, crit, ctx)
        status = {"PASS": "PASS", "FAIL": "FAIL_EVIDENCED", "UNEVALUABLE": "UNEVALUABLE"}[r["state"]]
        entry = dict(r, status=status, on_fail=spec["on_fail"], name=spec["name"])
        out[cid] = entry
        if status == "FAIL_EVIDENCED":
            (fails if spec["on_fail"] == "FAIL" else blocks).append(cid)
        elif status == "UNEVALUABLE":
            blocks.append(cid)
    verdict = "FAIL" if fails else ("BLOCKED" if blocks else "PASS")
    assert crit["exit_codes"][verdict] == EXIT_FOR[verdict], "exit-code policy of the criteria differs from the judge"
    return {"verdict": verdict, "exit_code": crit["exit_codes"][verdict], "checks": out, "fail_class": fails, "blocked_class": sorted(blocks),
            "invalid_fields": invalid, "c03_fidelity_report": out["G0-C03"].get("report", [])}


# ------------------------------------------------------------------ the closure marker g0_closed.json (F-23)
MARKER_KEYS = ("closed_schema", "run_id", "criteria_id", "criteria_sha256", "evidence_sha256", "evidence_bytes", "summary_sha256", "summary_bytes",
               "recorded_verdict", "recorded_exit_code", "process_exit_proof")
MARKER_SCHEMA = "e1a-gate-g0-closed-1"
MARKER_MAX_BYTES = 4096
RUN_ID_RE = GA.ID_RE


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
    if not (isinstance(o["run_id"], str) and RUN_ID_RE.match(o["run_id"]) and o["run_id"].startswith("g0_")):
        bad.append("run_id")
    if o["criteria_id"] != GA.CRITERIA_ID:
        bad.append("criteria_id")
    for k in ("criteria_sha256", "evidence_sha256", "summary_sha256"):
        if not (isinstance(o[k], str) and HEX64.match(o[k])):
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
    o = {"closed_schema": MARKER_SCHEMA, "run_id": run_id, "criteria_id": GA.CRITERIA_ID, "criteria_sha256": criteria_sha256,
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


def classify_blob(raw, want_sha256, want_bytes):
    """Fact `summary` / `evidence` for bytes read from a regular file, against the marker's binding.  -> (state, parsed or None)."""
    if len(raw) != want_bytes:
        return "size_mismatch", None
    if sha256_hex(raw) != want_sha256:
        return "hash_mismatch", None
    try:
        return "ok", parse_strict(raw)
    except (ValueError, RecursionError):
        return "unparsable", None


def closure_bindings(entry_name, closed, summary_state, summary, evidence_state, evidence, tool_criteria_id, tool_criteria_sha256):
    """The binding facts of one run directory.  `closed` is a valid marker object; *_state is the fact of the bound file ('ok' when its bytes match
    the marker's size / SHA-256 and parse); summary / evidence are the parsed values (used only when the state is 'ok').
    -> dict closed_runid, criteria_vs_tool, criteria_vs_summary, summary_binding, evidence_binding ('na' where not defined)."""
    f = {"closed_runid": "match" if closed["run_id"] == entry_name else "mismatch",
         "criteria_vs_tool": "match" if (closed["criteria_id"] == tool_criteria_id and closed["criteria_sha256"] == tool_criteria_sha256) else "mismatch",
         "criteria_vs_summary": "na", "summary_binding": "na", "evidence_binding": "na"}
    if summary_state == "ok":
        if isinstance(summary, dict):
            same_c = summary.get("criteria_id") == closed["criteria_id"] and summary.get("criteria_sha256") == closed["criteria_sha256"]
            f["criteria_vs_summary"] = "match" if same_c else "mismatch"
            pair = EXIT_FOR.get(summary.get("verdict")) if isinstance(summary.get("verdict"), str) else None
            ok = (summary.get("run_id") == closed["run_id"] and summary.get("evidence_sha256") == closed["evidence_sha256"]
                  and summary.get("verdict") == closed["recorded_verdict"] and is_int(summary.get("exit_code"))
                  and summary.get("exit_code") == closed["recorded_exit_code"] and pair is not None and pair == summary.get("exit_code"))
            f["summary_binding"] = "match" if ok else "mismatch"
        else:
            f["criteria_vs_summary"], f["summary_binding"] = "mismatch", "mismatch"
    if evidence_state == "ok":
        f["evidence_binding"] = "match" if (isinstance(evidence, dict) and evidence.get("run_id") == closed["run_id"]) else "mismatch"
    return f


def _cond(c, facts):
    return facts.get(c["fact"]) in c["in"]


def closure_reasons(run_facts, glob, crit):
    """CL-01 .. CL-23 over one run directory's facts (None = no directory, global rules only) and the global facts.
    -> list of matched rules {id, reason, human_action, scope}.  Pure; the rules are read from the frozen criteria (closure.preflight.rules)."""
    hits = []
    for r in crit["closure"]["preflight"]["rules"]:
        glob_rule = r.get("scope") == "global"
        facts = glob if glob_rule else run_facts
        if facts is None:
            continue
        if not all(_cond(c, facts) for c in r.get("applies", [])):
            continue
        fired = all(_cond(c, facts) for c in r["when"]) if "when" in r else any(_cond(c, facts) for c in r["when_any"])
        if fired:
            hits.append({"id": r["id"], "reason": r["reason"], "human_action": r["human_action"], "scope": "global" if glob_rule else "directory"})
    return hits
