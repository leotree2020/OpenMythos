"""G1 judge cases (CPU, pure: dictionaries only; WRITTEN, NOT RUN -- NOT TESTED).  Covers the four normal negative-gate scenarios, a wrongly released R,
wrong exit codes, a FIRST_ACTION / message before release, PID / starttime mismatches, forks and signals, damaged evidence (never a wrong FAIL), NOT_RUN /
incomplete runs, time bounds, manual disposition, the closure marker and the consistency of the judge with the frozen criteria.
No process is started; nothing is read except the frozen criteria and code files."""
import copy
import hashlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_fixtures as F  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_judge as GJ  # noqa: E402

CRIT = F.criteria()
NIDS = {"T1_ABORT": "n00001", "T2_EOF": "n00002", "T3_INVALID_BYTE": "n00003", "T4_TIMEOUT": "n00004"}
J = F.judge
C = F.check


def edit_both(ev, kind, nid, **fields):
    """Change a record in the writer's ledger AND in the durable copy (a faithful disk)."""
    n = 0
    for lst in (ev["reg_memory_records"], ev["reg"]):
        for r in lst:
            if r["kind"] == kind and r.get("node_id") == nid:
                r.update(fields)
                n += 1
    assert n == 2, (kind, nid)
    return ev


def add_record(ev, nid, kind, before="DEAD", **fields):
    """Insert a record of `kind` for the node before its `before` record; renumber seq; keep ledger, durable copy and writer seq consistent."""
    L = ev["reg_memory_records"]
    idx = next(i for i, r in enumerate(L) if r["kind"] == before and r.get("node_id") == nid)
    rec = {"seq": 0, "kind": kind, "mono": L[idx]["mono"] - 0.001, "wall": L[idx]["wall"], "node_id": nid}
    rec.update(fields)
    L.insert(idx, rec)
    for i, r in enumerate(L):
        r["seq"] = i + 1
    return F.sync_ledger(ev)


def states(res, tid):
    return {cid: e["state"] for cid, e in res["tests"][tid]["checks"].items()}


class TestNormalScenarios(unittest.TestCase):
    def test_complete_run_passes_in_all_four_tests(self):
        res = J(F.good_evidence())
        self.assertEqual((res["verdict"], res["exit_code"], res["incomplete"]), ("PASS", 0, False))
        for tid in F.TESTS:
            self.assertEqual(res["tests"][tid]["verdict"], "PASS", (tid, states(res, tid)))
            self.assertEqual(len(res["tests"][tid]["checks"]), 17)
            self.assertTrue(all(e["state"] == "PASS" for e in res["tests"][tid]["checks"].values()), (tid, states(res, tid)))
        self.assertEqual((res["fail_class"], res["blocked_class"]), ([], []))

    def test_the_good_evidence_is_well_typed(self):
        self.assertEqual(GJ.validate_evidence(F.good_evidence(), CRIT), [])
        self.assertEqual(len(CRIT["evidence_schema"]["fields"]), 88)

    def test_scenario_table_is_the_reviewed_design(self):
        sc = CRIT["scenarios"]
        self.assertEqual(sc["order"], ["T1_ABORT", "T2_EOF", "T3_INVALID_BYTE", "T4_TIMEOUT"])
        for tid in F.TESTS:
            self.assertEqual(sc["tests"][tid]["expected_exit"], F.EXPECT[tid])
            self.assertEqual(sc["tests"][tid]["stimulus"]["planned_gate_bytes"], F.PLANNED[tid])
            self.assertEqual(sc["tests"][tid]["expected_registry_kinds"], F.KINDS[tid])
        self.assertEqual([sc["tests"][t]["t_gate_max_s"] for t in F.TESTS], [5.0, 5.0, 5.0, 2.0])
        self.assertNotIn(82, [b for t in F.TESTS for b in sc["tests"][t]["stimulus"]["planned_gate_bytes"]])         # R is never planned
        self.assertEqual(sc["tests"]["T3_INVALID_BYTE"]["stimulus"]["planned_gate_bytes"], [ord("r")])

    def test_each_test_is_judged_on_its_own_expected_code(self):
        res = J(F.good_evidence())
        for tid in F.TESTS:
            self.assertIn("exit status %d as expected" % F.EXPECT[tid], C(res, tid, "G1-C10")["detail"])

    def test_run_level_checks_are_repeated_in_every_row(self):
        res = J(F.good_evidence())
        for cid in GJ.RUN_LEVEL:
            for tid in F.TESTS:
                self.assertIs(C(res, tid, cid), res["run_checks"][cid])

    def test_judge_does_not_modify_the_evidence(self):
        ev = F.good_evidence()
        before = copy.deepcopy(ev)
        J(ev)
        self.assertEqual(ev, before)

    def test_frozen_files_have_their_frozen_hashes(self):
        for name, want in G1A.FROZEN_G1_FILES.items():
            with open(os.path.join(G1A.HERE, name), "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), want, name)

    def test_there_are_exactly_17_checks_and_the_g0_requirements_are_not_copied(self):
        self.assertEqual(sorted(CRIT["checks"]), sorted(GJ.CHECK_IDS))
        self.assertEqual(len(GJ.CHECK_IDS), 17)
        text = " ".join(c["text"] for c in CRIT["checks"].values())
        self.assertNotIn("exit_status_zero", " ".join(c["name"] for c in CRIT["checks"].values()))
        self.assertIn("never written", CRIT["scenarios"]["common"]["note"])
        self.assertIn("RELEASED record", text)          # only as a violation, never as a requirement
        res = J(F.good_evidence())
        self.assertFalse(any(r["kind"] == "RELEASED" for r in F.good_evidence()["reg"]))
        self.assertEqual(res["verdict"], "PASS")


class TestWrongRelease(unittest.TestCase):
    def test_an_r_write_attempt_in_the_guard_is_c07_f1_and_fails_the_run(self):
        ev = F.good_evidence()
        ev["guard"]["violations"].append({"call": GJ.R_WRITE_CALL, "mono": 1.0, "test": "T2_EOF", "args": "7"})
        res = J(ev)
        for tid in F.TESTS:
            self.assertEqual((C(res, tid, "G1-C07")["state"], C(res, tid, "G1-C07")["rule"]), ("FAIL", "C07-F1"))
            self.assertEqual(C(res, tid, "G1-C12")["state"], "FAIL")
        self.assertEqual((res["verdict"], res["exit_code"]), ("FAIL", 1))

    def test_an_r_byte_in_the_recorded_gate_writes_is_c07_f1(self):
        ev = F.mutate(F.good_evidence(), **{"guard.gate_writes.1.byte": 82})
        res = J(ev)
        self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C07")["rule"], "C07-F1")
        self.assertEqual(res["verdict"], "FAIL")

    def test_observer_release_call_is_c07_f1(self):
        ev = F.good_evidence()
        ev["guard"]["violations"].append({"call": GJ.RELEASE_CALL, "mono": 1.0, "test": "T1_ABORT", "args": ""})
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C07")["rule"], "C07-F1")
        self.assertEqual(res["verdict"], "FAIL")

    def test_a_released_record_fails_c03_c05_and_c07(self):
        ev = add_record(F.good_evidence(), NIDS["T2_EOF"], "RELEASED")
        res = J(ev)
        self.assertEqual(C(res, "T2_EOF", "G1-C03")["state"], "FAIL")
        self.assertEqual(C(res, "T2_EOF", "G1-C05")["rule"], "C05-F1")
        self.assertEqual(C(res, "T2_EOF", "G1-C07")["rule"], "C07-F1")
        self.assertEqual(res["verdict"], "FAIL")

    def test_an_unplanned_extra_byte_is_c07_f2(self):
        ev = F.good_evidence()
        ev["guard"]["gate_writes"].append({"test": "T2_EOF", "byte": 65, "mono_before": 1010.43, "mono_after": 1010.431, "result": "ok", "returned": 1,
                                           "errno": None, "error": None})
        res = J(ev)
        self.assertEqual((C(res, "T2_EOF", "G1-C07")["state"], C(res, "T2_EOF", "G1-C07")["rule"]), ("FAIL", "C07-F2"))

    def test_the_wrong_byte_instead_of_the_planned_one_is_c07_f2(self):
        res = J(F.mutate(F.good_evidence(), **{"guard.gate_writes.1.byte": 88}))
        self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C07")["rule"], "C07-F2")

    def test_t4_gate_closed_before_the_exit_was_observed_is_c07_f3(self):
        ev = F.good_evidence()
        ev["guard"]["gate_closes"][3]["mono"] = 1030.5
        res = J(ev)
        self.assertEqual(C(res, "T4_TIMEOUT", "G1-C07")["rule"], "C07-F3")
        res2 = J(F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.stimulus.gate_open_at_exit": False}))
        self.assertEqual(C(res2, "T4_TIMEOUT", "G1-C07")["rule"], "C07-F3")

    def test_a_missing_planned_close_is_unevaluable_not_fail(self):
        ev = F.good_evidence()
        ev["guard"]["gate_closes"] = [c for c in ev["guard"]["gate_closes"] if c["test"] != "T2_EOF"]
        res = J(ev)
        self.assertEqual((C(res, "T2_EOF", "G1-C07")["state"], C(res, "T2_EOF", "G1-C07")["rule"]), ("UNEVALUABLE", "C07-U3"))
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_gate_write_that_errored_is_unevaluable(self):
        ev = F.mutate(F.good_evidence(), **{"guard.gate_writes.0.result": "error", "guard.gate_writes.0.returned": None, "guard.gate_writes.0.errno": 32,
                                            "guard.gate_writes.0.error": "BrokenPipeError"})
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C07")["rule"], "C07-U2")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_stimulus_before_the_pre_stimulus_snapshot_is_c07_f3(self):
        ev = F.mutate(F.good_evidence(), **{"guard.gate_writes.0.mono_before": 1000.2})
        self.assertEqual(C(J(ev), "T1_ABORT", "G1-C07")["rule"], "C07-F3")


class TestWrongExitCode(unittest.TestCase):
    def run_with(self, tid, code):
        return J(F.mutate(F.good_evidence(), **{"tests.%s.reap.exit_status" % tid: code}))

    def test_swapped_gate_codes_are_c10_f2_fail(self):
        for tid, code in (("T1_ABORT", 112), ("T2_EOF", 112), ("T3_INVALID_BYTE", 112), ("T4_TIMEOUT", 111)):
            res = self.run_with(tid, code)
            self.assertEqual((C(res, tid, "G1-C10")["state"], C(res, tid, "G1-C10")["rule"]), ("FAIL", "C10-F2"), tid)
            self.assertEqual(res["verdict"], "FAIL", tid)

    def test_exit_status_zero_is_c10_f1_fail(self):
        for tid in F.TESTS:
            res = self.run_with(tid, 0)
            self.assertEqual(C(res, tid, "G1-C10")["rule"], "C10-F1")
            self.assertEqual(res["verdict"], "FAIL")

    def test_exit_113_or_a_signal_status_is_unevaluable_never_fail(self):
        for code in (113, -9, -15, 1, 2, 137):
            res = self.run_with("T1_ABORT", code)
            self.assertEqual((C(res, "T1_ABORT", "G1-C10")["state"], C(res, "T1_ABORT", "G1-C10")["rule"]), ("UNEVALUABLE", "C10-U1"), code)
            self.assertEqual((res["verdict"], res["exit_code"]), ("BLOCKED", 3), code)

    def test_a_non_integer_exit_status_is_unevaluable(self):
        for bad in ("111", True, None, 111.0):
            res = self.run_with("T2_EOF", bad)
            self.assertEqual(C(res, "T2_EOF", "G1-C10")["state"], "UNEVALUABLE", repr(bad))
            self.assertNotEqual(res["verdict"], "FAIL", repr(bad))

    def test_a_112_earlier_than_the_gate_timer_can_fire_is_c10_f3_with_the_fork_as_reference(self):
        ev = F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.events.pidfd_readable_mono": 1030.05 + 1.0})
        res = J(ev)
        self.assertEqual((C(res, "T4_TIMEOUT", "G1-C10")["state"], C(res, "T4_TIMEOUT", "G1-C10")["rule"]), ("FAIL", "C10-F3"))
        # the reference is the fork time, not the start of the test or the stimulus: a 112 at fork + 1.9 s is accepted (limit 1.8 s)
        ok = J(F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.events.pidfd_readable_mono": 1030.05 + 1.9}))
        self.assertNotEqual(C(ok, "T4_TIMEOUT", "G1-C10")["state"], "FAIL")

    def test_the_check_is_per_test_only_the_wrong_test_fails(self):
        res = self.run_with("T3_INVALID_BYTE", 112)
        self.assertEqual(res["tests"]["T1_ABORT"]["verdict"], "PASS")
        self.assertEqual(res["tests"]["T2_EOF"]["verdict"], "PASS")
        self.assertEqual(res["tests"]["T3_INVALID_BYTE"]["verdict"], "FAIL")


class TestActionBeforeRelease(unittest.TestCase):
    def test_a_message_before_release_in_a_held_snapshot_is_c05_f1(self):
        for snap in ("S1_held_registered_unreleased", "S1b_pre_stimulus"):
            res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.%s.messages_received" % snap: 1}))
            self.assertEqual((C(res, "T2_EOF", "G1-C05")["state"], C(res, "T2_EOF", "G1-C05")["rule"]), ("FAIL", "C05-F1"), snap)
            self.assertEqual(res["verdict"], "FAIL")

    def test_first_action_ready_or_messages_at_exit_are_c05_f1(self):
        for path, val in (("first_action_mono", 1010.45), ("ready_received", True), ("messages_received", 2)):
            res = J(F.mutate(F.good_evidence(), **{"tests.T3_INVALID_BYTE.%s" % path: val}))
            self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C05")["rule"], "C05-F1", path)
            self.assertEqual(res["verdict"], "FAIL", path)

    def test_first_action_in_a_held_snapshot_is_c05_f1(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S1_held_registered_unreleased.first_action_mono": 1000.3}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C05")["rule"], "C05-F1")

    def test_a_changed_sid_or_pgrp_is_c05_f1(self):
        for key in ("sid", "pgrp"):
            res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S1b_pre_stimulus.child.%s" % key: 123}))
            self.assertEqual(C(res, "T1_ABORT", "G1-C05")["rule"], "C05-F1", key)

    def test_a_child_in_another_state_is_unevaluable_not_fail(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S1_held_registered_unreleased.child.state": "R"}))
        self.assertEqual((C(res, "T2_EOF", "G1-C05")["state"], C(res, "T2_EOF", "G1-C05")["rule"]), ("UNEVALUABLE", "C05-U1"))
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_child_absent_from_a_held_snapshot_is_unevaluable(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S1_held_registered_unreleased.child": None}))
        self.assertEqual(C(res, "T2_EOF", "G1-C04")["rule"], "C04-U2")
        self.assertEqual(C(res, "T2_EOF", "G1-C05")["state"], "UNEVALUABLE")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_the_queued_spec_probe_must_match_the_scenario(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.stimulus.queued_spec": False}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C05")["state"], "UNEVALUABLE")
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.stimulus.queued_spec": True}))
        self.assertEqual(C(res, "T2_EOF", "G1-C05")["state"], "UNEVALUABLE")

    def test_the_gate_write_end_in_the_child_is_c06_f1(self):
        ev = F.good_evidence()
        ev["tests"]["T3_INVALID_BYTE"]["snapshots"]["S1_held_registered_unreleased"]["fds"]["5"] = {"target": "pipe:[%d]" % 9002, "access": "w"}
        res = J(ev)
        self.assertEqual((C(res, "T3_INVALID_BYTE", "G1-C06")["state"], C(res, "T3_INVALID_BYTE", "G1-C06")["rule"]), ("FAIL", "C06-F1"))


class TestIdentity(unittest.TestCase):
    def test_registered_pid_differs_from_the_held_child(self):
        ev = edit_both(F.good_evidence(), "REGISTERED", NIDS["T1_ABORT"], pid=4999)
        res = J(ev)
        self.assertEqual((C(res, "T1_ABORT", "G1-C04")["state"], C(res, "T1_ABORT", "G1-C04")["rule"]), ("FAIL", "C04-F1"))
        self.assertEqual(res["verdict"], "FAIL")

    def test_starttime_differences_are_c04_f1(self):
        for path in ("tests.T2_EOF.snapshots.S1b_pre_stimulus.child.starttime", "tests.T2_EOF.snapshots.S1_held_registered_unreleased.child.starttime",
                     "tests.T2_EOF.node.starttime"):
            res = J(F.mutate(F.good_evidence(), **{path: 1}))
            self.assertEqual(C(res, "T2_EOF", "G1-C04")["rule"], "C04-F1", path)

    def test_fork_pid_and_fork_event_must_agree(self):
        res = J(F.mutate(F.good_evidence(), **{"guard.fork_pids.1": 777}))
        self.assertEqual(C(res, "T2_EOF", "G1-C04")["rule"], "C04-F1")
        ev = F.good_evidence()
        ev["guard"]["fork_events"][2]["pid"] = 778
        res = J(ev)
        self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C04")["rule"], "C04-F1")
        self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C11")["state"], "FAIL")

    def test_a_wrong_ppid_is_c04_f1(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T3_INVALID_BYTE.snapshots.S1_held_registered_unreleased.child.ppid": 1}))
        self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C04")["rule"], "C04-F1")

    def test_registered_after_the_stimulus_is_c04_f1(self):
        ev = edit_both(F.good_evidence(), "REGISTERED", NIDS["T2_EOF"], mono=1011.0)
        self.assertEqual(C(J(ev), "T2_EOF", "G1-C04")["rule"], "C04-F1")

    def test_t4_identity_taken_too_late_for_the_gate_timer_is_unevaluable_never_pass(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.snapshots.S1b_pre_stimulus.mono": 1031.6}))
        self.assertEqual((C(res, "T4_TIMEOUT", "G1-C04")["state"], C(res, "T4_TIMEOUT", "G1-C04")["rule"]), ("UNEVALUABLE", "C04-U1"))
        self.assertEqual((res["tests"]["T4_TIMEOUT"]["verdict"], res["verdict"]), ("BLOCKED", "BLOCKED"))
        res = J(F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.snapshots.S1_held_registered_unreleased.mono": 1031.6}))
        self.assertEqual(C(res, "T4_TIMEOUT", "G1-C04")["rule"], "C04-U1")

    def test_no_or_two_registered_records_are_unevaluable(self):
        ev = F.good_evidence()
        for lst in (ev["reg_memory_records"], ev["reg"]):
            lst[:] = [r for r in lst if not (r["kind"] == "REGISTERED" and r.get("node_id") == NIDS["T2_EOF"])]
        for i, r in enumerate(ev["reg_memory_records"]):
            r["seq"] = i + 1
        F.sync_ledger(ev)
        res = J(ev)
        self.assertEqual(C(res, "T2_EOF", "G1-C04")["state"], "UNEVALUABLE")
        self.assertNotEqual(res["verdict"], "PASS")


class TestForksAndSignals(unittest.TestCase):
    def test_more_forks_than_executed_tests_is_c11_fail(self):
        res = J(F.mutate(F.good_evidence(), **{"guard.fork_calls": 5}))
        for tid in F.TESTS:
            self.assertEqual(C(res, tid, "G1-C11")["state"], "FAIL")
        self.assertEqual(res["verdict"], "FAIL")

    def test_fewer_forks_than_executed_tests_is_unevaluable(self):
        res = J(F.mutate(F.good_evidence(), **{"guard.fork_calls": 3}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C11")["state"], "UNEVALUABLE")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_guard_violation_is_c12_fail(self):
        ev = F.good_evidence()
        ev["guard"]["violations"].append({"call": "os.kill", "mono": 1.0, "test": "T2_EOF", "args": "(5001, 9)"})
        res = J(ev)
        for tid in F.TESTS:
            self.assertEqual((C(res, tid, "G1-C12")["state"], C(res, tid, "G1-C12")["rule"]), ("FAIL", "C12-F1"))
        self.assertEqual((res["verdict"], res["exit_code"]), ("FAIL", 1))

    def test_a_cleanup_kill_entry_that_is_not_already_exited_is_c12_fail(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.cleanup.rounds.0.kill.0.result": "sent"}))
        self.assertEqual(C(res, "T2_EOF", "G1-C12")["state"], "FAIL")
        self.assertEqual(res["verdict"], "FAIL")
        res = J(F.mutate(F.good_evidence(), **{"cleanup.rounds.0.kill.0.result": "sent"}))
        self.assertEqual(C(res, "T4_TIMEOUT", "G1-C12")["state"], "FAIL")                 # the run-wide cleanup is attributed to the last executed test

    def test_two_fork_events_for_one_test_are_not_evaluable_never_pass(self):
        ev = F.good_evidence()
        ev["guard"]["fork_events"].append(dict(ev["guard"]["fork_events"][1]))
        res = J(ev)
        self.assertEqual(C(res, "T2_EOF", "G1-C11")["state"], "UNEVALUABLE")
        self.assertNotEqual(res["verdict"], "PASS")

    def test_a_wait_call_naming_another_pid_blocks_c09(self):
        ev = F.good_evidence()
        ev["guard"]["waitpid_calls"].append({"test": "T2_EOF", "pid": 12345, "options": 1, "returned": 0, "status": 0, "mono": 1010.55})
        res = J(ev)
        e = C(res, "T2_EOF", "G1-C09")
        self.assertEqual((e["state"], e["status"], e["on_fail"]), ("FAIL", "FAIL_EVIDENCED", "BLOCKED"))
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_wait_before_the_unreaped_observation_blocks_c08(self):
        ev = F.good_evidence()
        ev["guard"]["waitpid_calls"].insert(0, {"test": "T1_ABORT", "pid": 5000, "options": 1, "returned": 0, "status": 0, "mono": 1000.45})
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C08")["state"], "FAIL")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_the_zombie_state_is_required_not_assumed(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S3_exited_unreaped.child.state": "S"}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C08")["status"], "FAIL_EVIDENCED")
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S3_exited_unreaped.child": None}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C08")["status"], "FAIL_EVIDENCED")

    def test_no_wait_call_that_returned_the_pid_blocks_c09(self):
        ev = F.good_evidence()
        ev["guard"]["waitpid_calls"] = [c for c in ev["guard"]["waitpid_calls"] if c["test"] != "T3_INVALID_BYTE"]
        res = J(ev)
        self.assertEqual(C(res, "T3_INVALID_BYTE", "G1-C09")["state"], "FAIL")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_proc_entry_still_present_after_the_reap_blocks_c09(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S4_reaped.child": {"pid": 5000, "starttime": 700000, "ppid": 4000, "state": "S", "sid": 1, "pgrp": 1}}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C09")["state"], "FAIL")

    def test_two_children_or_a_grandchild_in_a_snapshot_is_c11_fail(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S1_held_registered_unreleased.children": [5001, 5099]}))
        self.assertEqual(C(res, "T2_EOF", "G1-C11")["state"], "FAIL")
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S3_exited_unreaped.grandchildren": [6000]}))
        self.assertEqual(C(res, "T2_EOF", "G1-C11")["state"], "FAIL")
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S0_before_fork.children": [4999]}))
        self.assertEqual(C(res, "T2_EOF", "G1-C11")["state"], "FAIL")

    def test_a_ticket_intent_is_c03_f3_and_c11_fail(self):
        ev = edit_both(F.good_evidence(), "INTENT", NIDS["T2_EOF"], creator="n00001")
        res = J(ev)
        self.assertEqual((C(res, "T2_EOF", "G1-C03")["state"], C(res, "T2_EOF", "G1-C03")["rule"]), ("FAIL", "C03-F3"))
        self.assertEqual(C(res, "T2_EOF", "G1-C11")["state"], "FAIL")

    def test_a_child_not_yet_reaped_when_the_next_fork_happened_is_c11_fail(self):
        ev = F.good_evidence()
        ev["guard"]["fork_events"][1]["mono_before"] = ev["tests"]["T1_ABORT"]["events"]["reap_mono"] - 0.1
        self.assertEqual(C(J(ev), "T2_EOF", "G1-C11")["state"], "FAIL")


class TestEvidenceDamage(unittest.TestCase):
    """Damaged or untrustworthy evidence is UNEVALUABLE (BLOCKED), never a wrong FAIL; well-formed violations still FAIL (negative controls)."""

    def test_an_altered_durable_copy_blocks_and_disables_the_disk_dependent_checks(self):
        ev = F.good_evidence()
        ev["reg"][2]["label"] = "tampered"
        res = J(ev)
        self.assertEqual((C(res, "T1_ABORT", "G1-C03")["state"], C(res, "T1_ABORT", "G1-C03")["rule"]), ("UNEVALUABLE", "C03-U2"))
        for cid in GJ.DISK_DEPENDENT:
            self.assertEqual((C(res, "T1_ABORT", cid)["state"], C(res, "T1_ABORT", cid)["rule"]), ("UNEVALUABLE", "M-2"), cid)
        self.assertEqual((res["verdict"], res["exit_code"]), ("BLOCKED", 3))
        self.assertEqual(res["c03_fidelity_report"][0]["type"], "ALTERED")

    def test_a_lost_record_in_the_durable_copy_blocks(self):
        ev = F.good_evidence()
        del ev["reg"][5]
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C03")["rule"], "C03-U2")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_foreign_line_in_the_durable_copy_blocks(self):
        ev = F.good_evidence()
        ev["reg"].append({"seq": 99, "kind": "RELEASED", "mono": 1.0, "wall": 1.0, "node_id": "n00002"})
        res = J(ev)
        self.assertEqual(C(res, "T2_EOF", "G1-C03")["state"], "UNEVALUABLE")
        self.assertNotEqual(res["verdict"], "FAIL")

    def test_a_seq_gap_or_append_failure_alone_is_blocked_never_fail(self):
        ev = F.good_evidence()
        for r in ev["reg_memory_records"][6:]:
            r["seq"] += 1
        F.sync_ledger(ev)
        res = J(ev)
        self.assertEqual((C(res, "T1_ABORT", "G1-C03")["state"], C(res, "T1_ABORT", "G1-C03")["rule"]), ("UNEVALUABLE", "C03-U3"))
        self.assertEqual(res["verdict"], "BLOCKED")
        res = J(F.mutate(F.good_evidence(), reg_writer_seq=99))
        self.assertEqual(C(res, "T1_ABORT", "G1-C03")["rule"], "C03-U3")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_wrong_kinds_with_a_clean_writer_and_faithful_disk_are_c03_f2(self):
        ev = F.good_evidence()
        L = ev["reg_memory_records"]
        L[:] = [r for r in L if not (r["kind"] == "FORKED" and r.get("node_id") == NIDS["T3_INVALID_BYTE"])]
        for i, r in enumerate(L):
            r["seq"] = i + 1
        F.sync_ledger(ev)
        res = J(ev)
        self.assertEqual((C(res, "T3_INVALID_BYTE", "G1-C03")["state"], C(res, "T3_INVALID_BYTE", "G1-C03")["rule"]), ("FAIL", "C03-F2"))
        self.assertEqual(res["verdict"], "FAIL")

    def test_a_duplicated_run_start_is_c03_f1_a(self):
        ev = F.good_evidence()
        L = ev["reg_memory_records"]
        L.insert(1, dict(L[0]))
        for i, r in enumerate(L):
            r["seq"] = i + 1
        F.sync_ledger(ev)
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C03")["state"], "FAIL")
        self.assertIn("a", C(res, "T1_ABORT", "G1-C03")["clauses"])
        self.assertEqual(res["verdict"], "FAIL")

    def test_a_run_end_confirming_cleanup_while_a_node_has_no_dead_is_c03_f1_e(self):
        ev = F.good_evidence()
        L = ev["reg_memory_records"]
        L[:] = [r for r in L if not (r["kind"] == "DEAD" and r.get("node_id") == NIDS["T4_TIMEOUT"])]
        for i, r in enumerate(L):
            r["seq"] = i + 1
        F.sync_ledger(ev)
        res = J(ev)
        self.assertIn("e", C(res, "T1_ABORT", "G1-C03")["clauses"])
        self.assertEqual(res["verdict"], "FAIL")

    def test_an_aborted_record_outside_t1_is_f1_e_when_cleanup_is_confirmed(self):
        ev = add_record(F.good_evidence(), NIDS["T3_INVALID_BYTE"], "ABORTED")
        res = J(ev)
        self.assertIn("e", C(res, "T3_INVALID_BYTE", "G1-C03")["clauses"])

    def test_format_damaged_guard_records_are_unevaluable_never_fail(self):
        for path, val in (("guard.gate_writes.0.byte", "A"), ("guard.gate_writes.0.mono_before", "1.0"), ("guard.gate_writes.0.result", "maybe"),
                          ("guard.gate_closes.0.fd", True), ("guard.gate_writes", "x"), ("guard.gate_closes", None), ("guard.violations", None)):
            res = J(F.mutate(F.good_evidence(), **{path: val}))
            self.assertEqual((C(res, "T1_ABORT", "G1-C07")["state"], C(res, "T1_ABORT", "G1-C07")["rule"]), ("UNEVALUABLE", "C07-U1"), path)
            self.assertNotEqual(res["verdict"], "FAIL", path)
            self.assertEqual(res["verdict"], "BLOCKED", path)

    def test_a_missing_guard_key_is_unevaluable(self):
        ev = F.good_evidence()
        del ev["guard"]["gate_closes"]
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C07")["state"], "UNEVALUABLE")
        self.assertEqual(C(res, "T1_ABORT", "G1-C16")["state"], "FAIL")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_times_of_the_wrong_type_are_unevaluable_not_fail(self):
        for path in ("tests.T1_ABORT.events.pidfd_readable_mono", "tests.T1_ABORT.events.stimulus_mono", "tests.T1_ABORT.events.reap_mono",
                     "tests.T1_ABORT.snapshots.S3_exited_unreaped.mono", "tests.T1_ABORT.snapshots.S1b_pre_stimulus.mono"):
            res = J(F.mutate(F.good_evidence(), **{path: "1.0"}))
            self.assertNotEqual(res["verdict"], "FAIL", path)
            self.assertNotEqual(res["verdict"], "PASS", path)

    def test_wrong_typed_fields_make_c16_fail_and_the_run_blocked(self):
        for path, val in (("auth_consumed", 1), ("observer.pid", "x"), ("guard.fork_calls", True), ("tests.T2_EOF.ran", 1), ("reg_writer_seq", "9"),
                          ("preflight.ok", "yes"), ("run_id", 7)):
            res = J(F.mutate(F.good_evidence(), **{path: val}))
            self.assertEqual(C(res, "T1_ABORT", "G1-C16")["state"], "FAIL", path)
            self.assertNotEqual(res["verdict"], "PASS", path)

    def test_wrong_schema_id_is_c16(self):
        res = J(F.mutate(F.good_evidence(), evidence_schema="e1a-gate-g0-evidence-4"))
        self.assertEqual(C(res, "T1_ABORT", "G1-C16")["state"], "FAIL")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_missing_tests_object_or_non_dict_evidence_does_not_crash_and_is_blocked(self):
        ev = F.good_evidence()
        del ev["tests"]
        res = J(ev)
        self.assertEqual((res["verdict"], res["exit_code"]), ("BLOCKED", 3))
        self.assertTrue(all(res["tests"][t]["verdict"] == "NOT_RUN" for t in F.TESTS))
        for bad in ("x", None, [], 3):
            res = GJ.judge(bad, CRIT, G1A.FROZEN_G1_CRITERIA_SHA256)
            self.assertEqual(res["verdict"], "BLOCKED", repr(bad))

    def test_the_run_level_preflight_failure_blocks_every_test(self):
        res = J(F.mutate(F.good_evidence(), **{"preflight.unresolved_prior": ["g1_x:NO_CLOSED"]}))
        self.assertEqual(res["verdict"], "BLOCKED")
        for tid in F.TESTS:
            self.assertEqual(C(res, tid, "G1-C01")["state"], "FAIL")
            self.assertEqual(C(res, tid, "G1-C01")["on_fail"], "BLOCKED")
        res = J(F.mutate(F.good_evidence(), **{"preflight.g0_reference.ok": False}))
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_binding_differences_block_c02(self):
        for path, val in (("bindings_end.git_head", "9" * 40), ("auth_expected.g1_criteria_sha256", "7" * 64), ("bindings_start.g1_code_sha256", "8" * 64),
                          ("auth_consumed", False)):
            res = J(F.mutate(F.good_evidence(), **{path: val}))
            self.assertEqual(C(res, "T1_ABORT", "G1-C02")["state"], "FAIL", path)
            self.assertEqual(res["verdict"], "BLOCKED", path)
        ev = F.good_evidence()
        for k in ("auth_expected", "bindings_start", "bindings_end"):
            ev[k]["g0_reference_sha256"] = "6" * 64
        self.assertEqual(C(J(ev), "T1_ABORT", "G1-C02")["state"], "FAIL")

    def test_negative_control_unplanned_pid_reuse_like_evidence_still_fails_when_well_formed(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S1_held_registered_unreleased.child.pid": 6000}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C04")["state"], "FAIL")


class TestNotRunAndIncomplete(unittest.TestCase):
    def test_a_run_that_stopped_early_but_passed_so_far_is_blocked_not_pass(self):
        res = J(F.good_evidence(ran=2))
        self.assertEqual((res["verdict"], res["exit_code"], res["incomplete"]), ("BLOCKED", 3, True))
        self.assertEqual([res["tests"][t]["verdict"] for t in F.TESTS], ["PASS", "PASS", "NOT_RUN", "NOT_RUN"])
        self.assertIn("RUN-INCOMPLETE", res["blocked_class"])

    def test_nothing_ran_is_blocked(self):
        res = J(F.good_evidence(ran=0))
        self.assertEqual((res["verdict"], res["incomplete"]), ("BLOCKED", True))

    def test_not_run_after_a_failed_test_is_legitimate_and_the_verdict_is_fail(self):
        ev = F.mutate(F.good_evidence(ran=2), **{"tests.T2_EOF.reap.exit_status": 112})
        ev["stopped_after"] = "T2_EOF"
        res = J(ev)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertEqual([res["tests"][t]["verdict"] for t in F.TESTS], ["PASS", "FAIL", "NOT_RUN", "NOT_RUN"])
        self.assertFalse(res["incomplete"])

    def test_not_run_after_a_blocked_test_is_blocked(self):
        ev = F.mutate(F.good_evidence(ran=2), **{"tests.T2_EOF.reap.exit_status": 113})
        res = J(ev)
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertEqual(res["tests"]["T3_INVALID_BYTE"]["verdict"], "NOT_RUN")

    def test_tests_that_ran_must_be_a_prefix_of_the_order(self):
        ev = F.mutate(F.good_evidence(ran=2), **{"tests.T1_ABORT.ran": False})
        res = J(ev)
        self.assertEqual(C(res, "T2_EOF", "G1-C17")["state"], "FAIL")
        self.assertNotEqual(res["verdict"], "PASS")

    def test_not_run_is_never_counted_as_evidence_of_a_pass(self):
        res = J(F.good_evidence(ran=3))
        self.assertNotEqual(res["verdict"], "PASS")
        self.assertEqual(res["tests"]["T4_TIMEOUT"]["checks"], {})


class TestTimeBounds(unittest.TestCase):
    def test_t4_exit_observed_later_than_5s_after_the_fork_blocks(self):
        ev = F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.events.pidfd_readable_mono": 1030.05 + 5.2, "guard.gate_closes.3.mono": 1035.3})
        res = J(ev)
        e = C(res, "T4_TIMEOUT", "G1-C15")
        self.assertEqual((e["state"], e["status"], e["on_fail"]), ("FAIL", "FAIL_EVIDENCED", "BLOCKED"))
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_exit_later_than_the_deadline_after_the_stimulus_blocks(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.events.pidfd_readable_mono": 1010.42 + 5.5}))
        self.assertEqual(C(res, "T2_EOF", "G1-C15")["state"], "FAIL")

    def test_a_test_or_run_over_its_budget_blocks(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.timing.duration": 7.5}))
        self.assertEqual((C(res, "T1_ABORT", "G1-C15")["state"], res["verdict"]), ("FAIL", "BLOCKED"))
        res = J(F.mutate(F.good_evidence(), **{"timing.duration": 31.0}))
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_deadline_hit_prevents_pass(self):
        ev = F.mutate(F.good_evidence(), deadline_hits=["exit:T1_ABORT"])
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C15")["state"], "FAIL")
        self.assertEqual(C(res, "T1_ABORT", "G1-C03")["state"], "UNEVALUABLE")
        self.assertEqual(res["verdict"], "BLOCKED")

    def test_a_missing_duration_is_unevaluable(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.timing": None}))
        self.assertEqual(C(res, "T1_ABORT", "G1-C15")["state"], "UNEVALUABLE")


class TestManualDispositionAndErrors(unittest.TestCase):
    def test_manual_disposition_blocks(self):
        ev = F.mutate(F.good_evidence(), manual_disposition={"pid": 5001, "starttime": 700001, "node_id": "n00002"})
        res = J(ev)
        self.assertEqual(C(res, "T1_ABORT", "G1-C17")["state"], "FAIL")
        self.assertEqual((res["verdict"], res["exit_code"]), ("BLOCKED", 3))

    def test_exception_aborted_or_test_exception_block(self):
        for path, val in (("exception", "Traceback ..."), ("aborted", "stopped"), ("tests.T3_INVALID_BYTE.exception", "RuntimeError: x")):
            res = J(F.mutate(F.good_evidence(), **{path: val}))
            self.assertEqual(res["verdict"], "BLOCKED", path)

    def test_an_exception_alone_never_gives_fail(self):
        res = J(F.mutate(F.good_evidence(ran=1), exception="boom", stopped_after=None))
        self.assertNotEqual(res["verdict"], "FAIL")

    def test_residue_or_unconfirmed_cleanup_blocks_c13(self):
        for path, val in (("tests.T2_EOF.cleanup.cleanup_ok", False), ("cleanup.cleanup_ok", False), ("cleanup.run_set.consistent", False)):
            res = J(F.mutate(F.good_evidence(), **{path: val}))
            self.assertEqual(res["verdict"], "BLOCKED", path)
        ev = F.good_evidence()
        ev["run_snapshots"]["S9_final"]["token_residue"] = [{"pid": 1}]
        self.assertEqual(J(ev)["verdict"], "BLOCKED")
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S4_reaped.children": [5001]}))
        self.assertEqual(C(res, "T2_EOF", "G1-C13")["state"], "FAIL")

    def test_a_changed_descriptor_count_blocks_c14(self):
        res = J(F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S5_after_cleanup.fd_count": 6}))
        self.assertEqual((C(res, "T2_EOF", "G1-C14")["state"], res["verdict"]), ("FAIL", "BLOCKED"))
        res = J(F.mutate(F.good_evidence(), **{"run_snapshots.S9_final.fd_count": 5}))
        self.assertEqual(res["verdict"], "BLOCKED")


class TestInRunJudgement(unittest.TestCase):
    """The in-run safety rule uses the very check functions of the judge, so the first test that is not PASS is also the last one executed."""

    def view(self, ev=None):
        return F.good_evidence(ran=2) if ev is None else ev

    def test_a_clean_partial_run_passes_for_every_executed_test(self):
        for tid in ("T1_ABORT", "T2_EOF"):
            res = GJ.judge_test_in_run(self.view(), CRIT, tid)
            self.assertEqual((res["verdict"], res["non_pass"]), ("PASS", {}), tid)

    def test_only_checks_that_do_not_need_the_end_of_the_run_are_used(self):
        self.assertEqual(GJ.IN_RUN_CHECKS, tuple("G1-C%02d" % i for i in range(4, 16)))
        for cid in ("G1-C01", "G1-C02", "G1-C03", "G1-C16", "G1-C17"):
            self.assertNotIn(cid, GJ.IN_RUN_CHECKS)
        self.assertTrue(set(GJ.IN_RUN_CHECKS) <= set(GJ.CHECK_IDS))

    def test_run_level_and_end_of_run_parts_do_not_matter_in_run(self):
        ev = self.view()
        L = ev["reg_memory_records"]
        L[:] = [r for r in L if r["kind"] != "RUN_END"]
        F.sync_ledger(ev)
        ev["cleanup"] = None
        ev["run_snapshots"] = {}
        ev["preflight"]["ok"] = False
        res = GJ.judge_test_in_run(ev, CRIT, "T2_EOF")
        self.assertEqual(res["verdict"], "PASS", res)

    def test_the_evidence_is_not_modified(self):
        ev = self.view()
        before = copy.deepcopy(ev)
        GJ.judge_test_in_run(ev, CRIT, "T1_ABORT")
        self.assertEqual(ev, before)

    def test_a_test_that_is_not_marked_as_run_is_not_pass(self):
        res = GJ.judge_test_in_run(self.view(), CRIT, "T3_INVALID_BYTE")
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertIn("RUN", res["non_pass"])

    def test_each_evidenced_violation_stops_the_run_with_fail(self):
        def extra_byte(ev):
            ev["guard"]["gate_writes"].append({"test": "T2_EOF", "byte": 65, "mono_before": 1010.43, "mono_after": 1010.431, "result": "ok", "returned": 1, "errno": None, "error": None})
            return ev

        def gate_end(ev):
            ev["tests"]["T2_EOF"]["snapshots"]["S1_held_registered_unreleased"]["fds"]["5"] = {"target": "pipe:[9001]", "access": "w"}
            return ev

        def violation(call):
            def f(ev):
                ev["guard"]["violations"].append({"call": call, "mono": 1.0, "test": "T2_EOF", "args": ""})
                return ev
            return f

        def ticket(ev):
            return edit_both(ev, "INTENT", NIDS["T2_EOF"], creator="n00001")
        cases = [("identity mismatch", lambda ev: F.mutate(ev, **{"tests.T2_EOF.snapshots.S1b_pre_stimulus.child.pid": 6000}), "G1-C04"),
                 ("registered pid differs", lambda ev: edit_both(ev, "REGISTERED", NIDS["T2_EOF"], pid=4999), "G1-C04"),
                 ("message before release", lambda ev: F.mutate(ev, **{"tests.T2_EOF.snapshots.S1_held_registered_unreleased.messages_received": 1}), "G1-C05"),
                 ("gate write end in the child", gate_end, "G1-C06"), ("extra gate byte", extra_byte, "G1-C07"), ("R write attempt", violation(GJ.R_WRITE_CALL), "G1-C07"),
                 ("wrong exit code", lambda ev: F.mutate(ev, **{"tests.T2_EOF.reap.exit_status": 112}), "G1-C10"),
                 ("exit status 0", lambda ev: F.mutate(ev, **{"tests.T2_EOF.reap.exit_status": 0}), "G1-C10"),
                 ("second fork", lambda ev: F.mutate(ev, **{"guard.fork_calls": 3}), "G1-C11"), ("ticket", ticket, "G1-C11"),
                 ("signal call", violation("os.kill"), "G1-C12")]
        for name, build, cid in cases:
            res = GJ.judge_test_in_run(build(self.view()), CRIT, "T2_EOF")
            self.assertEqual(res["verdict"], "FAIL", name)
            self.assertIn(cid, res["non_pass"], name)

    def test_each_unconfirmed_condition_stops_the_run_with_blocked(self):
        cases = [("exit 113", {"tests.T2_EOF.reap.exit_status": 113}, "G1-C10"), ("no zombie observed", {"tests.T2_EOF.snapshots.S3_exited_unreaped.child.state": "S"}, "G1-C08"),
                 ("cleanup not ok", {"tests.T2_EOF.cleanup.cleanup_ok": False}, "G1-C13"), ("descriptors changed", {"tests.T2_EOF.snapshots.S5_after_cleanup.fd_count": 6}, "G1-C14"),
                 ("test over budget", {"tests.T2_EOF.timing.duration": 7.5}, "G1-C15"), ("deadline hit", {"deadline_hits": ["exit:T2_EOF"]}, "G1-C15"),
                 ("child absent at S1", {"tests.T2_EOF.snapshots.S1_held_registered_unreleased.child": None}, "G1-C04")]
        for name, change, cid in cases:
            res = GJ.judge_test_in_run(F.mutate(self.view(), **change), CRIT, "T2_EOF")
            self.assertEqual(res["verdict"], "BLOCKED", name)
            self.assertIn(cid, res["non_pass"], name)

    def test_an_unfaithful_durable_copy_stops_the_run(self):
        ev = self.view()
        ev["reg"][2]["label"] = "tampered"
        res = GJ.judge_test_in_run(ev, CRIT, "T2_EOF")
        self.assertEqual(res["verdict"], "BLOCKED")
        self.assertTrue({"G1-C04", "G1-C05", "G1-C11", "G1-C13"} <= set(res["non_pass"]))

    def test_the_in_run_judgement_agrees_with_the_final_judge_on_the_same_test(self):
        for build in (lambda e: e, lambda e: F.mutate(e, **{"tests.T2_EOF.snapshots.S1b_pre_stimulus.child.pid": 6000}),
                      lambda e: F.mutate(e, **{"tests.T2_EOF.reap.exit_status": 113}), lambda e: F.mutate(e, **{"tests.T2_EOF.reap.exit_status": 0})):
            ev = build(self.view())
            final = J(ev)
            in_run = GJ.judge_test_in_run(ev, CRIT, "T2_EOF")
            in_run_checks = {cid: final["tests"]["T2_EOF"]["checks"][cid]["state"] for cid in GJ.IN_RUN_CHECKS}
            if any(st != "PASS" for st in in_run_checks.values()):
                self.assertNotEqual(in_run["verdict"], "PASS")                      # a check of the final judge that fails also stops the run
            else:
                self.assertEqual(in_run["verdict"], "PASS")


class TestClosureMarker(unittest.TestCase):
    def build(self, verdict="PASS", code=0):
        return GJ.build_marker("g1_20261101_120000_abc123", "a" * 64, b"evidence", b"summary", verdict, code)

    def test_build_and_classify_roundtrip(self):
        obj, raw = self.build()
        self.assertEqual(GJ.classify_marker(raw)[0], "ok")
        self.assertEqual(set(obj), set(GJ.MARKER_KEYS))
        self.assertIs(obj["process_exit_proof"], False)
        self.assertEqual((obj["closed_schema"], obj["criteria_id"]), ("e1a-gate-g1-closed-1", "E1A-GATE-G1-CRITERIA-V1"))
        self.assertEqual(obj["evidence_sha256"], hashlib.sha256(b"evidence").hexdigest())
        for v, c in (("FAIL", 1), ("BLOCKED", 3)):
            self.assertEqual(GJ.classify_marker(self.build(v, c)[1])[0], "ok")

    def test_impossible_pairs_and_foreign_run_ids_are_refused(self):
        for v, c in (("PASS", 1), ("FAIL", 0), ("BLOCKED", 1), ("PASS", True), ("MAYBE", 0), ("PASS", 3)):
            with self.assertRaises(ValueError):
                self.build(v, c)
        with self.assertRaises(ValueError):
            GJ.build_marker("g0_20261101_120000_abc123", "a" * 64, b"e", b"s", "PASS", 0)
        with self.assertRaises(ValueError):
            GJ.build_marker("g1_x", "z" * 64, b"e", b"s", "PASS", 0)

    def test_classification_of_damaged_markers(self):
        obj, raw = self.build()
        self.assertEqual(GJ.classify_marker(raw + b"\n")[0], "noncanonical")
        self.assertEqual(GJ.classify_marker(raw.replace(b",", b", ", 1))[0], "noncanonical")
        self.assertEqual(GJ.classify_marker(b"")[0], "oversize_or_empty")
        self.assertEqual(GJ.classify_marker(b"x" * 5000)[0], "oversize_or_empty")
        self.assertEqual(GJ.classify_marker(raw[:-5])[0], "unparsable")
        self.assertEqual(GJ.classify_marker(b'{"a":1,"a":2}')[0], "unparsable")
        self.assertEqual(GJ.classify_marker(b'{"x": NaN}')[0], "unparsable")
        self.assertEqual(GJ.classify_marker(GJ.strict_bytes(dict(obj, extra=1)))[0], "schema_invalid")
        self.assertEqual(GJ.classify_marker(GJ.strict_bytes(dict(obj, process_exit_proof=True)))[0], "schema_invalid")
        self.assertEqual(GJ.classify_marker(GJ.strict_bytes(dict(obj, recorded_exit_code=1)))[0], "schema_invalid")
        self.assertEqual(GJ.classify_marker(GJ.strict_bytes(dict(obj, closed_schema="e1a-gate-g0-closed-1")))[0], "schema_invalid")
        self.assertEqual(GJ.classify_marker(GJ.strict_bytes(dict(obj, run_id="g0_20261027_144311_479c54")))[0], "schema_invalid")
        self.assertEqual(GJ.classify_marker(None)[0], "oversize_or_empty")

    def test_marker_does_not_prove_process_exit(self):
        self.assertIn("process_exit_proof must be false", GJ.marker_object_problems(dict(self.build()[0], process_exit_proof=True)))


class TestJudgeMatchesTheFrozenCriteria(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(GJ.EXIT_FOR, CRIT["exit_codes"])
        self.assertEqual(tuple(GJ.SNAPS_TEST), tuple(CRIT["snapshots"]["per_test"]))
        self.assertEqual(set(GJ.DISK_DEPENDENT), set(CRIT["witness_dependencies"]["disk_dependent_checks"]))
        self.assertEqual(tuple(GJ.MARKER_KEYS), tuple(f["path"] for f in CRIT["closure"]["marker_schema"]["fields"]))
        self.assertEqual((GJ.MARKER_SCHEMA, GJ.MARKER_MAX_BYTES), (CRIT["closure"]["marker_schema"]["id"], CRIT["closure"]["marker_schema"]["max_bytes"]))
        self.assertEqual(tuple(GJ.TESTS), tuple(CRIT["scenarios"]["order"]))
        self.assertEqual(tuple(GJ.BIND_KEYS), tuple(CRIT["authorization"]["bindings"]))
        self.assertEqual(GJ.CRITERIA_ID, CRIT["criteria_id"])

    def test_every_schema_type_has_a_validator(self):
        declared = {f["type"] for f in CRIT["evidence_schema"]["fields"]}
        self.assertEqual([t for t in declared if t not in GJ.TYPE_VALIDATORS], [])

    def test_every_rule_id_is_implemented_in_the_judge(self):
        src = open(os.path.join(G1A.HERE, "g1_judge.py"), encoding="utf-8").read()
        for c in CRIT["checks"].values():
            for group in ("fail_when", "unevaluable_when"):
                for r in c.get("rules", {}).get(group, []):
                    self.assertIn('"%s"' % r["id"], src, r["id"])

    def test_authorization_constants_match_the_criteria(self):
        a = CRIT["authorization"]
        self.assertEqual(G1A.REQUIRED_GRANTS, a["grants"])
        self.assertEqual(set(G1A.MUST_NOT_GRANT), set(a["not_granted"]))
        self.assertEqual(G1A.G0_REFERENCE, a["g0_reference"])
        self.assertEqual((G1A.AUTH_SCHEMA, G1A.STAGE), (a["schema"], a["stage"]))
        self.assertEqual(list(G1A.G1_CODE_FILES), a["g1_code_files"])
        self.assertEqual(set(G1A.ALLOWED_KEYS), set(a["allowed_keys"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
