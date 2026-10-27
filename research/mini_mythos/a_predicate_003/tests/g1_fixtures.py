"""Fixtures for the G1 CPU tests (WRITTEN, NOT RUN): builds well-typed G1 evidence of a run in which all four tests behave as expected, and small helpers to
damage it.  Pure dictionaries; no process, no file access except the frozen criteria / code files.  Used by tests/test_g1_*.py."""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
G0 = os.path.join(A003, "gate_g0")
G1 = os.path.join(A003, "gate_g1")
for p in (G1, G0, os.path.join(A003, "bench")):
    if p not in sys.path:
        sys.path.insert(0, p)
import g0_auth as GA  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_judge as GJ  # noqa: E402

TESTS = list(G1A.TESTS)
OBS = {"pid": 4000, "sid": 3900, "pgrp": 3950}
RUN_ID = "g1_20261101_120000_abc123"
EXPECT = {"T1_ABORT": 111, "T2_EOF": 111, "T3_INVALID_BYTE": 111, "T4_TIMEOUT": 112}
PLANNED = {"T1_ABORT": [65], "T2_EOF": [], "T3_INVALID_BYTE": [114], "T4_TIMEOUT": []}
KINDS = {"T1_ABORT": ["INTENT", "FORKED", "REGISTERED", "ABORTED", "DEAD"], "T2_EOF": ["INTENT", "FORKED", "REGISTERED", "DEAD"],
         "T3_INVALID_BYTE": ["INTENT", "FORKED", "REGISTERED", "DEAD"], "T4_TIMEOUT": ["INTENT", "FORKED", "REGISTERED", "DEAD"]}
T0 = 1000.0


def criteria():
    return GJ.load_criteria()


def bindings():
    return {"git_head": "1" * 40, "prereg_sha256": "2" * 64, "g0_criteria_sha256": GA.FROZEN_CRITERIA_SHA256, "g0_prereg_sha256": GA.FROZEN_PREREG_SHA256,
            "bench_code_sha256": "3" * 64, "g0_code_sha256": "4" * 64, "g1_criteria_sha256": G1A.FROZEN_G1_CRITERIA_SHA256,
            "g1_prereg_sha256": G1A.FROZEN_G1_PREREG_SHA256, "g1_code_sha256": "5" * 64, "g0_reference_sha256": G1A.G0_REFERENCE["closed_sha256"]}


def _child(i, state, sid=None, pgrp=None, ppid=None):
    return {"pid": 5000 + i, "starttime": 700000 + i, "ppid": OBS["pid"] if ppid is None else ppid, "state": state,
            "sid": OBS["sid"] if sid is None else sid, "pgrp": OBS["pgrp"] if pgrp is None else pgrp}


def _snap(name, mono, children, child, held=False, i=0):
    s = {"name": name, "children": children, "grandchildren": [], "total_procs": 80, "enum_problems": {}, "fd_count": 4, "child": child, "mono": mono}
    if held:
        gate = "pipe:[%d]" % (9000 + i)
        s["fds"] = {"0": {"target": "/dev/null", "access": "r"}, "1": {"target": "/dev/null", "access": "w"}, "2": {"target": "/dev/null", "access": "w"},
                    "3": {"target": gate, "access": "r"}, "4": {"target": "socket:[9999]", "access": "rw"}}
        s["messages_received"] = 0
        s["first_action_mono"] = None
    return s


def _kill_round(nid):
    return {"round": 1, "nodes": 1, "kill": [{"node_id": nid, "result": "already_exited"}], "kill_unregistered_direct": [], "new_nodes": []}


def _test_object(i, tid, s):
    """One executed test whose timeline starts at monotonic time `s`."""
    pid, nid = 5000 + i, "n%05d" % (i + 1)
    timer = tid == "T4_TIMEOUT"
    exit_at = s + 2.1 if timer else s + 0.5
    s3, call = exit_at + 0.01, exit_at + 0.02
    reap, gone = call + 0.001, call + 0.006
    s4 = gone + 0.01
    events = {"start_mono": s, "hold_start_mono": s + 0.09, "stimulus_mono": s + 0.42, "pidfd_readable_mono": exit_at, "reap_mono": reap, "proc_gone_mono": gone,
              "end_mono": s4 + 0.1, "exit_message_mono": None}
    snaps = {"S0_before_fork": _snap("S0_before_fork", s + 0.01, [], None),
             "S1_held_registered_unreleased": _snap("S1_held_registered_unreleased", s + 0.40, [pid], _child(i, "S"), True, i),
             "S1b_pre_stimulus": _snap("S1b_pre_stimulus", s + 0.41, [pid], _child(i, "S"), True, i),
             "S3_exited_unreaped": _snap("S3_exited_unreaped", s3, [pid], _child(i, "Z")),
             "S4_reaped": _snap("S4_reaped", s4, [], None),
             "S5_after_cleanup": _snap("S5_after_cleanup", s4 + 0.09, [], None)}
    code = EXPECT[tid]
    return {"ran": True, "scenario": tid, "t_gate_max": 2.0 if timer else 5.0, "node": {"node_id": nid, "pid": pid, "starttime": 700000 + i, "gate_ino": 9000 + i},
            "stimulus": {"kind": {"T1_ABORT": "abort_held", "T2_EOF": "close_only", "T3_INVALID_BYTE": "write_byte", "T4_TIMEOUT": "none"}[tid],
                         "planned_bytes": list(PLANNED[tid]), "queued_spec": tid == "T1_ABORT", "gate_open_at_exit": timer},
            "events": events, "first_action_mono": None, "ready_received": False, "messages_received": 0, "snapshots": snaps,
            "reap": {"waitpid_pid": pid, "exit_status": code, "raw_status": code * 256},
            "cleanup": {"cleanup_ok": True, "rounds": [_kill_round(nid)], "residual_detail": []}, "timing": {"duration": events["end_mono"] - s}, "exception": None}


def _blank(tid):
    return {"ran": False, "scenario": tid, "t_gate_max": None, "node": None, "stimulus": None, "events": None, "first_action_mono": None, "ready_received": None,
            "messages_received": None, "snapshots": None, "reap": None, "cleanup": None, "timing": None, "exception": None}


def good_evidence(ran=4):
    """Evidence of a run whose first `ran` tests behaved exactly as expected (ran=4: the complete PASS run).  For ran < 4 the run is incomplete."""
    tests, ledger, forks, calls, writes, closes, pids = {}, [], [], [], [], [], []
    seq = [0]

    def rec(kind, mono, **fields):
        seq[0] += 1
        r = {"seq": seq[0], "kind": kind, "mono": mono, "wall": 1793112000.0 + mono - T0}
        r.update(fields)
        ledger.append(r)
    rec("RUN_START", T0 - 1.0, run_id=RUN_ID, prereg_sha256="2" * 64, observer_pid=OBS["pid"], phase="G1")
    for i, tid in enumerate(TESTS):
        if i >= ran:
            tests[tid] = _blank(tid)
            continue
        s = T0 + 10.0 * i
        t = _test_object(i, tid, s)
        tests[tid] = t
        pid, nid, ev = 5000 + i, "n%05d" % (i + 1), t["events"]
        rec("INTENT", s + 0.02, node_id=nid, creator="O", creator_pid=OBS["pid"], role="sleeper", label=tid, mode="setsid", t_gate_max=t["t_gate_max"], trial="G1")
        rec("FORKED", s + 0.06, node_id=nid, pid=pid, starttime=700000 + i, creator="O", creator_pid=OBS["pid"], role="sleeper", label=tid)
        rec("REGISTERED", s + 0.08, node_id=nid, pid=pid, starttime=700000 + i, sid=OBS["sid"], pgrp=OBS["pgrp"], ppid=OBS["pid"], creator="O",
            creator_pid=OBS["pid"], role="sleeper", label=tid)
        if tid == "T1_ABORT":
            rec("ABORTED", s + 0.43, node_id=nid, reason="held node aborted by bench (validity check)", creation_unresolved=False)
        rec("DEAD", ev["end_mono"] - 0.05, node_id=nid, basis="confirmed dead from /proc")
        forks.append({"test": tid, "mono_before": s + 0.05, "mono_after": s + 0.06, "pid": pid})
        pids.append(pid)
        calls.append({"test": tid, "pid": pid, "options": 1, "returned": pid, "status": EXPECT[tid] * 256, "mono": ev["reap_mono"] - 0.001})
        if PLANNED[tid]:
            writes.append({"test": tid, "byte": PLANNED[tid][0], "mono_before": s + 0.43, "mono_after": s + 0.431, "result": "ok", "returned": 1, "errno": None,
                           "error": None})
        closes.append({"test": tid, "mono": s + 0.44 if tid != "T4_TIMEOUT" else ev["proc_gone_mono"] + 0.02, "fd": 7})
    rec("RUN_END", T0 + 10.0 * ran, run_id=RUN_ID, aborted=None, cleanup_confirmed=True, residual=[], token_residue=[], token_scan_problems=[])
    s_run = _snap("S0_run", T0 - 2.0, [], None)
    s9 = _snap("S9_final", T0 + 10.0 * ran + 1.0, [], None)
    s9["token_residue"] = []
    ev = {"evidence_schema": "e1a-gate-g1-evidence-1", "run_id": RUN_ID, "auth_expected": bindings(), "bindings_start": bindings(), "bindings_end": bindings(),
          "auth_consumed": True,
          "preflight": {"ok": True, "problems": [], "children": 0, "token_residue": [], "unresolved_prior": [], "enumeration_problems": {}, "run_id_unique": True,
                        "fd_count": 4, "total_procs": 80, "g0_reference": {"ok": True, "problems": [], "run_id": G1A.G0_REFERENCE["run_id"],
                                                                         "closed_sha256": G1A.G0_REFERENCE["closed_sha256"]}},
          "evidence_root": {"path": "/e", "created_by_this_run": False, "uid": 0, "mode": 493, "ino": 1},
          "consumed_dir": {"path": "/e/_g1_consumed", "created_by_this_run": True, "uid": 0, "mode": 493, "ino": 2},
          "run_dir": {"path": "/e/" + RUN_ID, "created_by_this_process": True}, "observer": dict(OBS),
          "guard": {"violations": [], "fork_calls": ran, "fork_pids": pids, "fork_events": forks, "waitpid_calls": calls, "gate_writes": writes, "gate_closes": closes},
          "reg_memory_records": ledger, "reg_writer_seq": len(ledger), "reg": copy.deepcopy(ledger),
          "reg_parse_info": {"torn_tail": False, "corrupt_lines": 0, "missing": False, "unreadable": False},
          "cleanup": {"cleanup_ok": True, "run_set": {"consistent": True, "problems": [], "nodes": ran}, "rounds": [_kill_round("n00001")], "residual_detail": []},
          "run_snapshots": {"S0_run": s_run, "S9_final": s9}, "exception": None, "aborted": None, "stopped_after": None, "deadline_hits": [],
          "timing": {"duration": 5.0}, "manual_disposition": None, "tests": tests}
    return ev


def mutate(ev, **changes):
    """deepcopy of `ev` with dotted-path changes: mutate(ev, **{'tests.T1_ABORT.reap.exit_status': 112}).  Use '/' instead of '.' inside keys is not needed."""
    out = copy.deepcopy(ev)
    for path, val in changes.items():
        cur = out
        parts = path.split(".")
        for p in parts[:-1]:
            cur = cur[int(p)] if isinstance(cur, list) else cur[p]
        if isinstance(cur, list):
            cur[int(parts[-1])] = val
        else:
            cur[parts[-1]] = val
    return out


def sync_ledger(ev):
    """After editing ev['reg_memory_records'] make the durable copy and the writer seq consistent with it (an honest writer and a faithful disk)."""
    ev["reg"] = copy.deepcopy(ev["reg_memory_records"])
    ev["reg_writer_seq"] = len(ev["reg_memory_records"])
    return ev


def judge(ev):
    crit = criteria()
    return GJ.judge(ev, crit, G1A.FROZEN_G1_CRITERIA_SHA256)


def check(res, tid, cid):
    return res["tests"][tid]["checks"][cid]
