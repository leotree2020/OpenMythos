"""E1-A candidates.  Runs INSIDE the supervisor stub (the process under test).

  P0  CPU-001 ArmCA.register_root + preflight, imported UNCHANGED (hash-pinned by the stub before import)
  P1  CPU-002 ArmCAS (StrictMixin) register_root + preflight, imported UNCHANGED
  P2  the S0 candidate s0_check(): eight direct kernel-read checks; ALL failing checks are reported
P3 (proc connector) and P4 (cgroup) are not run in E1-A.
The mechanism output vocabulary is ACCEPT / BLOCKED / UNKNOWN; it is never an experiment verdict.  WRITTEN, NOT RUN."""
import ctypes
import json
import os
import signal
import sys

import common as C

_PR_SET_CHILD_SUBREAPER, _PR_GET_CHILD_SUBREAPER = 36, 37


def load_checks():
    """S0 check table (id -> rule / code) from the frozen preregistration: the single source of truth."""
    with open(C.PREREG_PATH, encoding="utf-8") as f:
        return json.load(f)["s0_checks"]


def p2_prctl_set(flag):
    libc = ctypes.CDLL(None, use_errno=True)
    return libc.prctl(_PR_SET_CHILD_SUBREAPER, int(flag), 0, 0, 0) == 0


def p2_prctl_get():
    libc = ctypes.CDLL(None, use_errno=True)
    v = ctypes.c_int(-1)
    return v.value if libc.prctl(_PR_GET_CHILD_SUBREAPER, ctypes.byref(v), 0, 0, 0) == 0 else None


def _base(cand):
    return {"candidate": cand, "verdict": None, "codes": [], "cited_rules": [], "evaluated_rules": [], "unknown_reasons": [],
            "preflight_executed": False, "detail": None}


# ---------------------------------------------------------------- P2: the S0 candidate
def build_view(root_node, declared_aux=()):
    """Kernel reads performed by the supervisor itself.  A failed /proc enumeration is recorded, never replaced by an empty table."""
    v = {"root_registered": {k: root_node[k] for k in ("pid", "starttime", "sid", "pgrp")},
         "sup_pid": os.getpid(), "sup_sid": os.getsid(0), "declared_aux": sorted(declared_aux),
         "table": None, "problems": {}, "scan_error": None}
    try:
        v["table"], v["problems"] = C.scan_proc()
    except C.ProcUnreadable as e:
        v["scan_error"] = str(e)
    v["sigchld_is_default"] = signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL
    v["sigign_mask"] = C.read_sigign(os.getpid())
    return v


def s0_check(v, sub, checks):
    """Pure function (no side effects, no signals, no waits).  `sub` = {'set_ok': bool, 'get_value': int|None}.
    Every proof rule has its premise: C1..C5 are evaluated only when C6 (the root fingerprint) holds."""
    out = _base("P2")
    defects, unknown, evaluated = set(), [], []
    reg, table, problems = v["root_registered"], v["table"], v["problems"]
    root = reg["pid"]

    evaluated.append(checks["C6"]["rule"])
    live = None
    if table is None:
        unknown.append("PROC_ENUMERATION_FAILED: %s" % v["scan_error"])
    elif root in problems:
        unknown.append("ROOT_ENTRY_UNREADABLE")
    else:
        live = table.get(root)
        if live is None or (live["starttime"], live["sid"], live["pgrp"]) != (reg["starttime"], reg["sid"], reg["pgrp"]):
            defects.add("C6")
            live = None                                   # premise of C1..C5 not met
    if live is not None:
        evaluated += [checks[c]["rule"] for c in ("C1", "C2", "C3")]
        if live["sid"] != root:
            defects.add("C1")
        if live["sid"] == v["sup_sid"]:
            defects.add("C2")
        if live["pgrp"] != root:
            defects.add("C3")
        evaluated += [checks["C4"]["rule"], checks["C5"]["rule"]]
        kids = C.children_of(table, root)
        if kids:
            defects.add("C4")
        elif problems:
            unknown.append("C4_NOT_PROVABLE_INCOMPLETE_ENUMERATION")
        extra = [p for p in C.children_of(table, v["sup_pid"]) if p != root and p not in v["declared_aux"]]
        if extra:
            defects.add("C5")
        elif problems:
            unknown.append("C5_NOT_PROVABLE_INCOMPLETE_ENUMERATION")

    evaluated.append(checks["C7"]["rule"])
    ign = v["sigign_mask"]
    if (not v["sigchld_is_default"]) or (ign is not None and ign & C.SIGIGN_SIGCHLD_BIT):
        defects.add("C7")
    elif ign is None:
        unknown.append("C7_SIGIGN_UNREADABLE")

    evaluated.append(checks["C8"]["rule"])
    if not (sub["set_ok"] and sub["get_value"] == 1):
        defects.add("C8")

    out["evaluated_rules"] = sorted(set(evaluated))
    if defects:
        out["verdict"] = "BLOCKED"
        out["codes"] = sorted(checks[c]["code_p2"] for c in defects)
        out["cited_rules"] = sorted({checks[c]["rule"] for c in defects})
    elif unknown:
        out["verdict"], out["unknown_reasons"] = "UNKNOWN", unknown
    else:
        out["verdict"] = "ACCEPT"
    out["preflight_executed"] = True
    return out


def run_p2(node, setter=None, getter=None):
    setter, getter = setter or p2_prctl_set, getter or p2_prctl_get
    set_ok = bool(setter(True))
    val = getter()
    return s0_check(build_view(node), {"set_ok": set_ok, "get_value": val}, load_checks())


# ---------------------------------------------------------------- P0 / P1: pinned CPU-001 / CPU-002 code
def _load_cpu001():
    if C.CPU001_DIR not in sys.path:
        sys.path.insert(0, C.CPU001_DIR)
    import a_lab
    return a_lab


def _load_cpu002():
    if C.CPU002_DIR not in sys.path:
        sys.path.insert(0, C.CPU002_DIR)
    import e2_lab
    return e2_lab


_CITES = {"ROOT_FINGERPRINT_MISMATCH": ["PR-S0-6"], "PREFLIGHT_FAILED": ["PR-S0-8"],
          "STAGE_SESSION_NOT_DEDICATED": ["PR-S0-1", "PR-S0-2"]}
_EVAL = {"P0": ["PR-S0-6", "PR-S0-8"], "P1": ["PR-S0-1", "PR-S0-2", "PR-S0-6", "PR-S0-8"]}


def _run_arm(cand, arm, lab_mod, node, setter, getter):
    out = _base(cand)
    out["evaluated_rules"] = list(_EVAL[cand])
    arm.get_subreaper = getter
    try:
        arm.register_root(node)
    except lab_mod.Blocked as e:
        out.update(verdict="BLOCKED", codes=["ROOT_FINGERPRINT_MISMATCH"], cited_rules=list(_CITES["ROOT_FINGERPRINT_MISMATCH"]), detail=str(e))
        return out
    r = arm.preflight(setter)
    out["preflight_executed"] = True
    out["detail"] = {"status": r.get("status"), "code": r.get("code"), "set_ok": r.get("set_ok"), "get_value": r.get("get_value")}
    if r.get("status") == "OK":
        out["verdict"] = "ACCEPT"
    else:
        code = r.get("code")
        out.update(verdict="BLOCKED", codes=[code], cited_rules=list(_CITES.get(code, [])))
    return out


def run_p0(node, setter=None, getter=None):
    L = _load_cpu001()
    return _run_arm("P0", L.ArmCA(None), L, node, setter or L.prctl_set_subreaper, getter or L.prctl_get_subreaper)


def run_p1(node, setter=None, getter=None):
    L = _load_cpu001()
    E = _load_cpu002()
    return _run_arm("P1", E.ArmCAS(None), L, node, setter or L.prctl_set_subreaper, getter or L.prctl_get_subreaper)


def apply_injection(node, injection):
    """-> (node, setter, getter) after the scenario's injection (SIMULATED scenarios f / h1 / h2 only)."""
    setter = getter = None
    if injection.get("starttime_delta"):
        node = dict(node, starttime=node["starttime"] + int(injection["starttime_delta"]))
    if injection.get("setter") == "fail":
        setter = lambda flag: False            # noqa: E731
    if injection.get("getter") is not None:
        getter = lambda: int(injection["getter"])   # noqa: E731
    return node, setter, getter


def run_candidate(cand, node, injection):
    node, setter, getter = apply_injection(node, injection or {})
    fn = {"P0": run_p0, "P1": run_p1, "P2": run_p2}[cand]
    return fn(node, setter, getter)
