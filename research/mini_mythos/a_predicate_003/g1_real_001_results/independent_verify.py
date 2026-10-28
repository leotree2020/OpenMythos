"""Independent read-back verification of the G1-REAL-001 evidence (does not use g1_judge): python3 -I independent_verify.py <run_dir>"""
import json, hashlib, sys, os
rd = sys.argv[1]
e = json.load(open(rd + "/g1_evidence.json")); s = json.load(open(rd + "/g1_summary.json")); c = json.load(open(rd + "/g1_closed.json"))
raw = open(rd + "/g1_evidence.json", "rb").read(); assert hashlib.sha256(raw).hexdigest() == c["evidence_sha256"] and len(raw) == c["evidence_bytes"]
raw2 = open(rd + "/g1_summary.json", "rb").read(); assert hashlib.sha256(raw2).hexdigest() == c["summary_sha256"] and len(raw2) == c["summary_bytes"]
assert open(rd + "/g1_closed.json", "rb").read() == open(rd + "/g1_closed.json.tmp", "rb").read()
print("evidence/summary hash + closure binding ok; closed:", c["recorded_verdict"], c["recorded_exit_code"], "process_exit_proof", c["process_exit_proof"])
T = e["tests"]; order = ["T1_ABORT", "T2_EOF", "T3_INVALID_BYTE", "T4_TIMEOUT"]; g = e["guard"]; exp = {"T1_ABORT": 111, "T2_EOF": 111, "T3_INVALID_BYTE": 111, "T4_TIMEOUT": 112}
assert [f["test"] for f in g["fork_events"]] == order and g["fork_calls"] == 4 and len(set(g["fork_pids"])) == 4
assert g["violations"] == [] and e["exception"] is None and e["aborted"] is None and e["stopped_after"] is None and e["manual_disposition"] is None
assert [(w["byte"]) for w in g["gate_writes"]] == [65, 114] and all(w["byte"] != 82 for w in g["gate_writes"])
assert [x["test"] for x in g["gate_closes"]] == order
kinds = [r["kind"] for r in e["reg"]]; assert "RELEASED" not in kinds and "FIRST_ACTION" not in kinds and "READY" not in kinds
print("registry kinds:", kinds)
prev_end = 0
for i, t in enumerate(order):
    x = T[t]; ev = x["events"]; pid = x["node"]["pid"]; st = x["node"]["starttime"]; fk = g["fork_events"][i]; wp = g["waitpid_calls"][i]; S = x["snapshots"]
    assert fk["pid"] == pid and wp["pid"] == pid and wp["returned"] == pid and wp["test"] == t
    assert x["reap"]["exit_status"] == exp[t] and x["reap"]["waitpid_pid"] == pid
    assert all(r["pid"] == pid and r["starttime"] == st for r in e["reg"] if r.get("node_id") == x["node"]["node_id"] and r["kind"] in ("FORKED", "REGISTERED"))
    assert S["S1_held_registered_unreleased"]["child"]["pid"] == pid and S["S1_held_registered_unreleased"]["child"]["starttime"] == st and S["S1b_pre_stimulus"]["child"]["starttime"] == st
    assert S["S3_exited_unreaped"]["child"]["state"] == "Z" and S["S3_exited_unreaped"]["child"]["pid"] == pid
    assert S["S4_reaped"]["child"] is None and S["S4_reaped"]["children"] == [] and S["S5_after_cleanup"]["children"] == []
    assert all(k["grandchildren"] == [] for k in S.values()) and max(len(k["children"]) for k in S.values()) <= 1
    assert x["first_action_mono"] is None and x["messages_received"] == 0 and x["ready_received"] is False
    assert x["cleanup"]["cleanup_ok"] and all(k["result"] == "already_exited" for r in x["cleanup"]["rounds"] for k in r["kill"])
    assert ev["start_mono"] >= prev_end and ev["pidfd_readable_mono"] < wp["mono"]; prev_end = ev["end_mono"]
    print(t, "pid", pid, "starttime", st, "exit", x["reap"]["exit_status"], "fork->pidfd-readable %.3f s" % (ev["pidfd_readable_mono"] - fk["mono_after"]), "waitpid returned", wp["returned"], "state Z seen before wait")
t4 = T["T4_TIMEOUT"]; ev = t4["events"]; fk = g["fork_events"][3]
d = ev["pidfd_readable_mono"] - fk["mono_after"]; assert 1.8 <= d <= 5.0
m = ev["pidfd_readable_mono"] - t4["snapshots"]["S1b_pre_stimulus"]["mono"]; assert m >= 0.5
print("T4 exit %.3f s after fork (1.8-5.0 required); identity sample %.3f s before the exit (>=0.5 required)" % (d, m))
assert e["timing"]["duration"] <= 30; print("total duration %.3f s" % e["timing"]["duration"])
assert [s["tests"][t]["verdict"] for t in order] == ["PASS"] * 4 and all(len(s["tests"][t]["checks"]) == 17 and all(v["status"] == "PASS" for v in s["tests"][t]["checks"].values()) for t in order)
assert all(v["status"] == "PASS" for v in s["run_checks"].values()) and s["verdict"] == "PASS" and s["exit_code"] == 0
assert e["run_snapshots"]["S9_final"]["children"] == [] and e["run_snapshots"]["S9_final"]["token_residue"] == [] and e["cleanup"]["run_set"]["residual"] == []
print("INDEPENDENT VERIFICATION: all assertions passed (4 tests x 17 checks PASS, run checks PASS, zero signals, zero residue)")
