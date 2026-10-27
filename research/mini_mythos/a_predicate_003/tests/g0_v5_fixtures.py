"""Shared fixtures for the G0 V5 pure-logic tests (NOT a test module).  WRITTEN, NOT RUN (F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001).
Builds complete V5 evidence dictionaries (all 91 fields of evidence_schema), converts the compact static case records of
g0_preflight_review/g0_v4_cases.json into evidence, and builds closure run directories in temporary directories.  Nothing here starts a process."""
import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
G0 = os.path.join(A003, "gate_g0")
REVIEW = os.path.join(A003, "g0_preflight_review")
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, G0)
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402

NOW = "2026-10-28T00:00:00Z"
RUN = "g0_x"
HEX40 = "a" * 40


def bindings():
    return {"git_head": HEX40, "prereg_sha256": "b" * 64, "g0_criteria_sha256": GA.FROZEN_CRITERIA_SHA256, "g0_prereg_sha256": GA.FROZEN_PREREG_SHA256,
            "bench_code_sha256": "c" * 64, "g0_code_sha256": "d" * 64}


def good_auth():
    return {"schema": GA.AUTH_SCHEMA, "stage": "G0", "authorized_by": "owner", "authorization_id": "OWNER-G0-0001", "date": "2026-10-28",
            "expires_utc": "2026-10-29T00:00:00Z", "bindings": bindings(), "grants": dict(GA.REQUIRED_GRANTS), "not_granted": list(GA.MUST_NOT_GRANT)}


def good_ledger():
    return [
        {"seq": 1, "kind": "RUN_START", "mono": 1.01, "wall": 1.0, "run_id": RUN, "observer_pid": 100, "phase": "G0"},
        {"seq": 2, "kind": "INTENT", "mono": 1.02, "wall": 1.0, "node_id": "n1", "creator": "O", "creator_pid": 100, "role": "sleeper", "label": "g0"},
        {"seq": 3, "kind": "FORKED", "mono": 1.03, "wall": 1.0, "node_id": "n1", "pid": 200, "starttime": 5000, "creator": "O", "creator_pid": 100},
        {"seq": 4, "kind": "REGISTERED", "mono": 1.3, "wall": 1.0, "node_id": "n1", "pid": 200, "starttime": 5000, "sid": 90, "pgrp": 90, "ppid": 100, "creator": "O"},
        {"seq": 5, "kind": "RELEASED", "mono": 1.7, "wall": 1.0, "node_id": "n1"},
        {"seq": 6, "kind": "DEAD", "mono": 2.5, "wall": 1.0, "node_id": "n1", "basis": "confirmed dead from /proc"},
        {"seq": 7, "kind": "RUN_END", "mono": 2.6, "wall": 1.0, "run_id": RUN, "cleanup_confirmed": True, "aborted": None},
    ]


def snap(name, mono, children, child=None, fds=None, token=False):
    s = {"name": name, "mono": mono, "children": children, "grandchildren": [], "total_procs": 50, "enum_problems": {}, "fd_count": 10, "child": child}
    if fds is not None:
        s["fds"] = fds
    if token:
        s["token_residue"] = []
    return s


def good_evidence():
    """A complete, healthy run: every check PASSES."""
    live = {"pid": 200, "starttime": 5000, "ppid": 100, "state": "S", "sid": 90, "pgrp": 90}
    std = {"0": {"target": "/dev/null", "access": "r"}, "1": {"target": "/dev/null", "access": "w"}, "2": {"target": "/dev/null", "access": "w"}}
    s1 = snap("S1_held_registered_unreleased", 1.6, [200], live, dict(std, **{"3": {"target": "pipe:[777]", "access": "r"}, "4": {"target": "socket:[888]", "access": "rw"}}))
    s1.update(messages_received=0, first_action_mono=None)
    led = good_ledger()
    return {
        "evidence_schema": "e1a-gate-g0-evidence-4", "run_id": RUN, "auth_expected": bindings(), "bindings_start": bindings(), "bindings_end": bindings(), "auth_consumed": True,
        "observer": {"pid": 100, "sid": 90, "pgrp": 90},
        "preflight": {"ok": True, "problems": [], "children": 0, "token_residue": [], "unresolved_prior": [], "enumeration_problems": {}, "run_id_unique": True,
                      "fd_count": 10, "total_procs": 50},
        "evidence_root": {"path": "/e/evidence", "created_by_this_run": False, "uid": 0, "mode": 0o755, "ino": 11},
        "consumed_dir": {"path": "/e/evidence/_g0_consumed", "created_by_this_run": True, "uid": 0, "mode": 0o755, "ino": 12},
        "run_dir": {"path": "/e/evidence/" + RUN, "created_by_this_process": True},
        "node": {"node_id": "n1", "pid": 200, "starttime": 5000, "gate_ino": 777},
        "snapshots": {
            "S0_before_fork": dict(snap("S0_before_fork", 1.0, [], None), token_residue=[]),
            "S1_held_registered_unreleased": s1,
            "S2_ready_after_release": snap("S2_ready_after_release", 1.9, [200], live, dict(std, **{"4": {"target": "socket:[888]", "access": "rw"}})),
            "S3_exited_unreaped": snap("S3_exited_unreaped", 2.2, [200], dict(live, state="Z")),
            "S4_reaped": snap("S4_reaped", 2.4, [], None),
            "S5_final": dict(snap("S5_final", 2.7, [], None), token_residue=[]),
        },
        "events": {"first_action_mono": 1.8, "exit_sent_mono": 2.0, "pidfd_readable_mono": 2.1, "reap_mono": 2.3, "proc_gone_mono": 2.35},
        "guard": {"violations": [], "fork_calls": 1, "fork_pids": [200],
                  "waitpid_calls": [{"pid": 200, "options": 1, "returned": 0, "status": 0, "mono": 2.25}, {"pid": 200, "options": 1, "returned": 200, "status": 0, "mono": 2.3}],
                  "release_writes": [{"mono_before": 1.75, "mono_after": 1.76, "result": "ok", "returned": 1, "errno": None, "error": None}]},
        "reap": {"waitpid_pid": 200, "exit_status": 0, "raw_status": 0},
        "cleanup": {"cleanup_ok": True, "run_set": {"consistent": True}, "residual_detail": [],
                    "rounds": [{"kill": [{"node_id": "n1", "result": "already_exited"}], "kill_unregistered_direct": []}]},
        "timing": {"duration": 1.7}, "deadline_hits": [], "exception": None, "aborted": None,
        "reg": copy.deepcopy(led), "reg_parse_info": {"torn_tail": False, "corrupt_lines": 0, "missing": False, "unreadable": False},
        "reg_memory_records": copy.deepcopy(led), "reg_writer_seq": len(led),
    }


# ------------------------------------------------------------------ the compact static cases of g0_v4_cases.json -> evidence
def _val(s):
    if s == "true":
        return True
    if s == "false":
        return False
    if s == "null":
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"'.*'", s):
        return s[1:-1]
    return s


def parse_rec(text, mono_override=None):
    """'3 FORKED n1 pid=200' -> record.  Defaults are VALID values; explicit tokens override them (st=null, pid='200', pid=true, creator=n2 ...)."""
    toks = text.split()
    seq, kind = int(toks[0]), toks[1]
    rec = {"seq": seq, "kind": kind, "mono": 1.0 + 0.01 * seq, "wall": 1.0}
    kv = {}
    node = None
    for t in toks[2:]:
        if re.fullmatch(r"n\d+", t):
            node = t
        elif "=" in t:
            k, v = t.split("=", 1)
            kv[k] = _val(v)
        elif t == "basis":
            kv["basis"] = "proc"
    if kind == "RUN_START":
        rec.update(run_id=kv.get("run", RUN), observer_pid=100, phase="G0")
    elif kind == "RUN_END":
        rec.update(run_id=kv.get("run", RUN), cleanup_confirmed=kv.get("confirmed", False), aborted=None)
    elif kind == "INTENT":
        rec.update(node_id=node, creator=kv.get("creator", "O"), creator_pid=100, role="sleeper", label="g0")
    elif kind == "FORKED":
        rec.update(node_id=node, pid=kv.get("pid", 200), starttime=5000, creator="O", creator_pid=100)
    elif kind == "REGISTERED":
        rec.update(node_id=node, pid=kv.get("pid", 200), starttime=kv.get("st", 5000), sid=90, pgrp=90, ppid=100, creator="O")
    elif kind == "RELEASED":
        rec.update(node_id=node)
    elif kind == "DEAD":
        rec.update(node_id=node, basis=("confirmed dead from /proc" if kv.get("basis", "proc") else None))
    if mono_override is not None and kind == "RELEASED":
        rec["mono"] = mono_override
    return rec


def parse_rw(text):
    """'ok b=1.75 a=1.76 returned=1' / 'error EPIPE b=1.75 a=1.76 errno=32'"""
    toks = text.split()
    kv = dict(t.split("=", 1) for t in toks if "=" in t)
    if toks[0] == "ok":
        return {"mono_before": float(kv["b"]), "mono_after": float(kv["a"]), "result": "ok", "returned": int(kv["returned"]), "errno": None, "error": None}
    return {"mono_before": float(kv["b"]), "mono_after": float(kv["a"]), "result": "error", "returned": None, "errno": int(kv["errno"]), "error": toks[1]}


def case_evidence(case):
    """Evidence for one static case (the other checks stay healthy; an early stop removes the evidence a stopped run cannot have)."""
    ev = good_evidence()
    rel_mono = None
    m = re.search(r"RELEASED\.mono taken as ([0-9.]+)", case.get("note", ""))
    if m:
        rel_mono = float(m.group(1))
    ev["reg_memory_records"] = [parse_rec(r, rel_mono) for r in case["ledger"]]
    ev["reg"] = [parse_rec(r, rel_mono) for r in case["disk"]]
    ev["reg_writer_seq"] = case["writer_seq"]
    ev["guard"]["fork_calls"] = case["fork_calls"]
    ev["guard"]["fork_pids"] = list(case["fork_pids"]) if case.get("fork_pids") else ([200] if case["fork_calls"] == 1 else [])
    ev["guard"]["release_writes"] = [parse_rw(x) for x in case["release_writes"]]
    ch = case["child"]
    ev["events"]["first_action_mono"] = float(ch.split("@")[1]) if ch.startswith("FIRST_ACTION@") else None
    if case["run"].startswith("early"):
        ev["exception"] = "RuntimeError: early stop (static case)"
        for k in ("exit_sent_mono", "pidfd_readable_mono", "reap_mono", "proc_gone_mono"):
            ev["events"].pop(k, None)
        ev["snapshots"].pop("S3_exited_unreaped", None)
        ev["snapshots"].pop("S4_reaped", None)
        ev["reap"] = {}
    cid = case["id"]
    if cid == "CE-E1":
        del ev["reg_memory_records"], ev["reg_writer_seq"]
    elif cid == "CE-E2":
        ev["evidence_schema"] = "e1a-gate-g0-evidence-3"
    elif cid == "CE-E3":
        ev["reg_writer_seq"] = str(case["writer_seq"])
    elif cid == "CE-E4":
        ev["node"]["pid"] = True
    return ev


def load_v4_cases():
    return json.load(open(os.path.join(REVIEW, "g0_v4_cases.json")))


def load_v5_cases():
    return json.load(open(os.path.join(REVIEW, "g0_v5_cases.json")))


def criteria():
    return GJ.load_criteria()
