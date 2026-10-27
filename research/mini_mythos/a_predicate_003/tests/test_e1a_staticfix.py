"""Failure-path tests for F3B-D1-A-CPU-003-E1A-STATIC-FIX-001.  WRITTEN, NOT RUN (no process may be started in this round).
Every test here is PURE: no fork, no signal, no sacrificial process.  /proc and pidfd access is replaced by monkeypatching where a
code path would otherwise touch the kernel; tests that need a real process live in test_e1a_gate.py (also unrun)."""
import inspect
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import candidates as K      # noqa: E402
import common as C          # noqa: E402
import e1a_runner as RUN    # noqa: E402
import evidence as EV      # noqa: E402
import janitor as J         # noqa: E402
import observer as O        # noqa: E402
import registry as R        # noqa: E402
import scenarios as S       # noqa: E402
import sup_stub             # noqa: E402
import trial as TR          # noqa: E402
import truth as T           # noqa: E402
import validity as V        # noqa: E402

PREREG, SHA = S.load_prereg()
CHECKS = PREREG["s0_checks"]
EV_OK = [{"seq": 1, "phase": "S0", "call": "S0_START", "infra": False}, {"seq": 2, "phase": "S0", "call": "S0_VERDICT", "infra": False}]
UNSAFE = {"seq": 3, "phase": "S0", "call": "os.kill", "infra": False}


def out(v, codes=(), cited=(), **kw):
    d = {"verdict": v, "codes": list(codes), "cited_rules": list(cited), "unknown_reasons": [], "enumeration_complete": True}
    d.update(kw)
    return d


# ===================================================================== FIX 1: unsafe priority; candidate exception
class TestFix1UnsafePriorityAndCandidateException(unittest.TestCase):
    def test_confirmed_unsafe_event_beats_bench_blocked(self):
        j = T.judge(PREREG, "E1A-a", "P2", out("ACCEPT"), EV_OK + [UNSAFE], ["TOPOLOGY_NOT_AS_DESIGNED: x", "NODE_DIED_UNEXPECTEDLY"])
        self.assertEqual(j["verdict"], "FAIL")
        self.assertEqual(j["suppressed_bench_reasons"], ["TOPOLOGY_NOT_AS_DESIGNED: x", "NODE_DIED_UNEXPECTEDLY"])

    def test_unsafe_event_beats_missing_output(self):
        j = T.judge(PREREG, "E1A-a", "P2", None, EV_OK + [UNSAFE], ["S0_FAILED: timeout"])
        self.assertEqual(j["verdict"], "FAIL")

    def test_unsafe_event_not_confirmed_when_instrumentation_is_untrusted(self):
        j = T.judge(PREREG, "E1A-a", "P2", out("ACCEPT"), EV_OK + [UNSAFE], ["BV-10_FAILED"], instrumentation_ok=False)
        self.assertEqual(j["verdict"], "BLOCKED")

    def test_extra_unsafe_also_has_priority(self):
        j = T.judge(PREREG, "E1A-a", "P2", out("ACCEPT"), EV_OK, ["bench"], extra_unsafe=["node dead after candidate signal"])
        self.assertEqual(j["verdict"], "FAIL")

    def test_infra_wait_and_non_s0_events_are_not_unsafe(self):
        evs = EV_OK + [{"seq": 3, "phase": "SETUP", "call": "os.waitpid", "infra": True}, {"seq": 4, "phase": "SETUP", "call": "os.kill", "infra": False}]
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", out("ACCEPT"), evs, [])["verdict"], "PASS")

    def test_candidate_exception_is_a_candidate_fail_not_bench_blocked(self):
        tb = "Traceback...\nValueError: boom"
        j = T.judge(PREREG, "E1A-a", "P2", None, EV_OK, [], candidate_exception=tb)
        self.assertEqual(j["verdict"], "FAIL")
        self.assertIn("CANDIDATE_RAISED", j["reasons"][0])
        self.assertEqual(j["candidate_exception"], tb)

    def test_candidate_exception_in_every_cell_class_is_fail(self):
        for scn in S.SCENARIO_ORDER:
            for cand in S.CANDIDATES:
                j = T.judge(PREREG, scn, cand, None, EV_OK, [], candidate_exception="x\nboom")
                self.assertEqual(j["verdict"], "FAIL", (scn, cand))

    def test_bench_reason_still_blocks_a_candidate_exception_when_nothing_unsafe_happened(self):
        j = T.judge(PREREG, "E1A-a", "P2", None, EV_OK, ["NODE_DIED_BEFORE_S0"], candidate_exception="x\nboom")
        self.assertEqual(j["verdict"], "BLOCKED")

    def test_trial_never_turns_a_candidate_exception_into_a_bench_reason(self):
        src = inspect.getsource(TR)
        self.assertNotIn('bench.append("CANDIDATE_RAISED', src)
        self.assertIn("cand_exc", src)

    def test_stub_separates_bench_load_from_candidate_logic(self):
        src = inspect.getsource(sup_stub.main)
        self.assertLess(src.index("prepare_candidate"), src.index('PHASE[0] = "S0"'))
        self.assertIn("CANDIDATE_LOAD_FAILED", src)
        self.assertIn('result["candidate_exception"]', src)

    def test_merge_events_unions_the_stream_with_the_result_log(self):
        streamed = [UNSAFE]
        merged = T.merge_events(EV_OK[:1], streamed, EV_OK)
        self.assertEqual([e["seq"] for e in merged], [1, 2, 3])
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", None, merged, ["S0_FAILED"])["verdict"], "FAIL")   # stub died, only the stream survived

    def test_stub_streams_unsafe_s0_events_before_the_call(self):
        sent = []

        class Ch:
            def send(self, obj, fds=()):
                sent.append(obj)
        old = (list(sup_stub.EVENTS), sup_stub.PHASE[0], sup_stub.CH[0])
        try:
            sup_stub.EVENTS.clear()
            sup_stub.CH[0] = Ch()
            sup_stub.PHASE[0] = "SETUP"
            sup_stub.ev("os.kill", (1,))                                  # not S0: not streamed
            sup_stub.PHASE[0] = "S0"
            sup_stub.ev("os.waitpid", (1,), infra=True)                   # infra: not streamed
            sup_stub.ev("S0_START")                                       # not an unsafe call
            sup_stub.ev("os.killpg", (1, 9))                              # streamed
            self.assertEqual([m["event"]["call"] for m in sent], ["os.killpg"])
            self.assertEqual(sent[0]["t"], "EVENT")
        finally:
            sup_stub.EVENTS[:] = old[0]
            sup_stub.PHASE[0], sup_stub.CH[0] = old[1], old[2]


# ===================================================================== FIX 2: cleanup responsibility
class TestFix2RegistryResponsibility(unittest.TestCase):
    def reg(self, d):
        return R.RegWriter(os.path.join(d, "reg.jsonl"))

    def test_aborted_registered_node_without_dead_is_still_a_target(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            w.write("INTENT", node_id="a", creator="O")
            w.write("REGISTERED", node_id="a", pid=11, starttime=5)
            w.write("ABORTED", node_id="a", reason="x")
            self.assertEqual([t["node_id"] for t in R.cleanup_targets(R.parse_reg(w.path)[0])], ["a"])
            w.write("DEAD", node_id="a")
            self.assertEqual(R.cleanup_targets(R.parse_reg(w.path)[0]), [])

    def test_forked_but_unregistered_is_unresolved_never_a_target(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            w.write("INTENT", node_id="a", creator="O")
            w.write("FORKED", node_id="a", pid=11, starttime=5)
            w.write("ABORTED", node_id="a", reason="registration failed")
            recs = R.parse_reg(w.path)[0]
            self.assertEqual(R.cleanup_targets(recs), [])
            self.assertEqual([u["node_id"] for u in R.unresolved_forked(recs)], ["a"])
            w.write("DEAD", node_id="a")
            self.assertEqual(R.unresolved_forked(R.parse_reg(w.path)[0]), [])

    def test_intent_only_has_no_known_process_and_no_responsibility_record(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            w.write("INTENT", node_id="a", creator="O")
            recs = R.parse_reg(w.path)[0]
            self.assertEqual((R.cleanup_targets(recs), R.unresolved_forked(recs)), ([], []))

    def test_registered_node_is_no_longer_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            w.write("INTENT", node_id="a", creator="O")
            w.write("FORKED", node_id="a", pid=11, starttime=5)
            w.write("REGISTERED", node_id="a", pid=11, starttime=5)
            self.assertEqual(R.unresolved_forked(R.parse_reg(w.path)[0]), [])

    def test_check_order_flags_forked_before_intent(self):
        self.assertTrue(R.check_order([{"seq": 1, "kind": "FORKED", "node_id": "a"}]))

    def test_janitor_reports_unresolved_alive_without_signalling(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            me = {"state": "S", "starttime": 5, "ppid": 1, "pgrp": 1, "sid": 1, "comm": "x"}
            w.write("INTENT", node_id="a", creator="O")
            w.write("FORKED", node_id="a", pid=4242, starttime=5)
            with mock.patch.object(C, "read_stat", return_value=me):
                full = J.run_cleanup_full(w.path, signal_fn=mock.Mock(side_effect=AssertionError("must not signal")), skip_pids=())
            self.assertEqual(full["targets"], [])
            self.assertEqual([(u["node_id"], u["alive"]) for u in full["unresolved"]], [("a", True)])

    def test_unreadable_proc_counts_as_alive_not_as_gone(self):
        recs = [{"seq": 1, "kind": "INTENT", "node_id": "a"}, {"seq": 2, "kind": "FORKED", "node_id": "a", "pid": 4242, "starttime": 5}]
        with mock.patch.object(C, "read_stat", side_effect=C.ProcUnreadable("EIO")):
            self.assertIsNone(J.unresolved_report(recs)[0]["alive"])


class TestFix2ObserverResidual(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.obs = O.Observer(os.path.join(self.tmp.name, "registry.jsonl"))
        self.obs.trial_tag = "T"

    def tearDown(self):
        self.tmp.cleanup()

    def node(self, state, forked_pid=4242, forked_start=5, pid=None, starttime=None, direct=False):
        r = O.NodeRec("n%d" % (len(self.obs.nodes) + 1), "x", "L", "O", {})
        r.trial, r.state, r.forked_pid, r.forked_starttime, r.pid, r.starttime, r.direct = "T", state, forked_pid, forked_start, pid, starttime, direct
        self.obs.nodes[r.node_id] = r
        return r

    @staticmethod
    def st(state="S", start=5):
        return {"state": state, "starttime": start, "ppid": 1, "pgrp": 1, "sid": 1, "comm": "x"}

    def test_aborted_forked_process_that_is_still_alive_stays_residual(self):
        r = self.node("ABORTED")
        with mock.patch.object(C, "read_stat", return_value=self.st()):
            self.assertEqual(self.obs.residual(), [r.node_id])

    def test_aborted_process_is_released_only_on_positive_evidence_of_death(self):
        r = self.node("ABORTED")
        for case, expect_left in ((None, False), (self.st("Z"), False), (self.st("X"), False), (self.st("S", start=6), False), (self.st("S"), True)):
            with mock.patch.object(C, "read_stat", return_value=case):
                self.assertEqual(bool(self.obs.residual()), expect_left, case)
        with mock.patch.object(C, "read_stat", side_effect=C.ProcUnreadable("EIO")):
            self.assertEqual(self.obs.residual(), [r.node_id])

    def test_failed_registration_without_known_starttime_cannot_be_declared_dead_by_pid_alone(self):
        r = self.node("ABORTED", forked_start=None)
        with mock.patch.object(C, "read_stat", return_value=self.st(start=999)):
            self.assertEqual(self.obs.residual(), [r.node_id])         # same pid alive, identity unknowable -> keep the responsibility

    def test_registered_aborted_node_uses_registered_identity(self):
        r = self.node("ABORTED", pid=4242, starttime=5)
        with mock.patch.object(C, "process_is_dead", return_value=False):
            self.assertEqual(self.obs.residual(), [r.node_id])
        with mock.patch.object(C, "process_is_dead", return_value=True):
            self.assertEqual(self.obs.residual(), [])

    def test_unverified_identity_is_never_signalled_and_makes_cleanup_fail(self):
        r = self.node("ABORTED", direct=False)
        with mock.patch.object(C, "read_stat", return_value=self.st()), mock.patch.object(C, "PidfdHandle") as H:
            rep = self.obs.finish_cleanup(grace=0.05)
        H.assert_not_called()
        self.assertFalse(rep["cleanup_ok"])
        self.assertEqual(rep["residual_detail"][0]["identity"], "UNVERIFIED (never signalled)")
        self.assertNotEqual(r.state, "DEAD")

    def test_mark_dead_writes_dead_only_after_confirmation(self):
        r = self.node("ABORTED")
        with mock.patch.object(C, "read_stat", return_value=self.st()):
            self.obs.mark_dead()
        self.assertEqual([x for x in self.obs.reg.records if x["kind"] == "DEAD"], [])
        with mock.patch.object(C, "read_stat", return_value=None):
            self.obs.mark_dead()
        self.assertEqual([x["node_id"] for x in self.obs.reg.records if x["kind"] == "DEAD"], [r.node_id])
        self.assertEqual(r.state, "DEAD")

    def test_direct_unregistered_child_is_killed_through_a_pidfd_only_while_unreaped(self):
        r = self.node("ABORTED", direct=True)
        fake = mock.Mock()
        fake.send.return_value = "sent"
        with mock.patch.object(C, "read_stat", return_value=self.st()), mock.patch.object(C, "PidfdHandle", return_value=fake) as H:
            res = self.obs.kill_unregistered_direct()
        H.assert_called_once_with(4242, 5)
        fake.send.assert_called_once()
        self.assertEqual(res[0]["result"], "sent")
        r.exit_status = 111                                           # reaped: no further signal
        with mock.patch.object(C, "read_stat", return_value=self.st()), mock.patch.object(C, "PidfdHandle") as H2:
            self.assertEqual(self.obs.kill_unregistered_direct(), [])
        H2.assert_not_called()

    def test_forked_record_is_written_when_the_pid_becomes_known(self):
        r = O.NodeRec("n9", "x", "L", "O", {})
        self.obs.nodes["n9"] = r
        with mock.patch.object(C, "read_stat", return_value=self.st(start=7)):
            self.obs._note_forked(r, 4242, 1)
        rec = [x for x in self.obs.reg.records if x["kind"] == "FORKED"][0]
        self.assertEqual((rec["pid"], rec["starttime"], r.forked_pid), (4242, 7, 4242))

    def test_run_level_nodes_exclude_only_the_given_ids(self):
        a, b = self.node("RELEASED"), self.node("ABORTED")
        self.assertEqual([x.node_id for x in self.obs.run_level_nodes({a.node_id})], [b.node_id])


# ===================================================================== FIX 3: RUN_END / janitor exit conditions
class TestFix3RunEndAndJanitor(unittest.TestCase):
    INTENT = {"seq": 1, "kind": "INTENT", "node_id": "a"}
    REG = {"seq": 2, "kind": "REGISTERED", "node_id": "a", "pid": 4242, "starttime": 5}

    def run_end(self, **kw):
        return dict({"seq": 9, "kind": "RUN_END"}, **kw)

    def test_no_run_end_observer_alive_waits_observer_dead_cleans(self):
        self.assertEqual(J.decide([self.INTENT, self.REG], False), "WAIT")
        self.assertEqual(J.decide([self.INTENT, self.REG], True), "CLEANUP")

    def test_run_end_without_or_with_false_confirmation_never_lifts_responsibility(self):
        for end in (self.run_end(), self.run_end(cleanup_confirmed=False), self.run_end(cleanup_confirmed=None), self.run_end(cleanup_confirmed="yes")):
            self.assertEqual(J.decide([self.INTENT, self.REG, end], False), "CLEANUP", end)
            self.assertEqual(J.decide([self.INTENT, self.REG, end], True), "CLEANUP", end)

    def test_confirmed_run_end_is_verified_before_it_is_trusted(self):
        recs = [self.INTENT, self.REG, self.run_end(cleanup_confirmed=True)]
        with mock.patch.object(C, "process_is_dead", return_value=True):
            self.assertEqual(J.decide(recs, False), "EXIT_CONFIRMED")
        with mock.patch.object(C, "process_is_dead", return_value=False):
            self.assertEqual(J.decide(recs, False), "CLEANUP")                    # claimed clean, but a registered node is alive
        with mock.patch.object(C, "process_is_dead", side_effect=C.ProcUnreadable("EIO")):
            self.assertEqual(J.decide(recs, False), "CLEANUP")

    def test_confirmed_run_end_with_an_unresolved_forked_process_is_not_trusted(self):
        recs = [self.INTENT, {"seq": 2, "kind": "FORKED", "node_id": "a", "pid": 4242, "starttime": 5}, self.run_end(cleanup_confirmed=True)]
        alive = {"state": "S", "starttime": 5, "ppid": 1, "pgrp": 1, "sid": 1, "comm": "x"}
        with mock.patch.object(C, "read_stat", return_value=alive):
            self.assertEqual(J.decide(recs, False), "CLEANUP")
        with mock.patch.object(C, "read_stat", return_value=None):
            self.assertEqual(J.decide(recs, False), "EXIT_CONFIRMED")

    def test_dead_marked_nodes_do_not_block_a_confirmed_run_end(self):
        recs = [self.INTENT, self.REG, {"seq": 3, "kind": "DEAD", "node_id": "a"}, self.run_end(cleanup_confirmed=True)]
        self.assertEqual(J.decide(recs, False), "EXIT_CONFIRMED")

    def test_cleanup_that_cannot_be_confirmed_is_reported_incomplete(self):
        full = {"targets": [{"result": "sent"}], "unresolved": [], "reg_info": {}}
        with mock.patch.object(J, "run_cleanup_full", return_value=full), mock.patch.object(J.R, "parse_reg", return_value=([self.INTENT, self.REG], {})), \
                mock.patch.object(C, "process_is_dead", return_value=False), mock.patch.object(J.time, "sleep"):
            clear, last = J.cleanup_until_clear("x", None, attempts=3, interval=0)
        self.assertFalse(clear)

    def test_cleanup_confirmed_when_everything_is_gone(self):
        with mock.patch.object(J, "run_cleanup_full", return_value={"targets": [], "unresolved": []}), \
                mock.patch.object(J.R, "parse_reg", return_value=([self.INTENT, self.REG], {})), mock.patch.object(C, "process_is_dead", return_value=True):
            self.assertTrue(J.cleanup_until_clear("x", None, attempts=2, interval=0)[0])

    def test_janitor_has_no_silent_exit_paths(self):
        src = inspect.getsource(J.main)
        self.assertNotIn("LIFETIME_CAP_NO_ACTION", src)
        self.assertNotIn("RUN_END_SEEN_NO_ACTION", src)
        self.assertIn("final_exit_code", src)                                     # STATIC-FIX-002-B: exit code from cleanup AND integrity

    def test_runner_writes_run_end_with_the_confirmation_after_the_final_cleanup(self):
        src = inspect.getsource(RUN.execute)
        self.assertIn("cleanup_confirmed=confirmed", src)
        self.assertLess(src.index("obs.final_cleanup(jid)"), src.index('obs.reg.write("RUN_END"'))
        self.assertLess(src.index("token_scan("), src.index('obs.reg.write("RUN_END"'))
        self.assertIn("recovery_open", src)
        self.assertIn("scan_problems", src)                                       # an unreadable /proc during the scan is "not confirmed"

    def test_last_run_end(self):
        self.assertIsNone(R.last_run_end([self.INTENT]))
        self.assertEqual(R.last_run_end([self.run_end(cleanup_confirmed=False, seq=5), self.run_end(cleanup_confirmed=True, seq=6)])["seq"], 6)


# ===================================================================== FIX 4: independently authorizable phases
def auth(**phases):
    return {"schema": RUN.AUTH_SCHEMA, "authorized_by": "owner", "authorization_id": "T1", "prereg_sha256": SHA, "bench_code_sha256": "c" * 64, "phases": phases}


CELLS_ONE = {RUN.PHASE_CELLS: {"cells": ["E1A-a:P2"], "max_reps": 1, "sweep": False}}
BV_ONE = {RUN.PHASE_BV: {"checks": ["BV-7"]}}


class TestFix4Phases(unittest.TestCase):
    def plan(self, a, phase, **kw):
        return RUN.build_execution_plan(PREREG, a, phase, **kw)

    def test_a_single_cell_authorization_never_implies_a_bv_check(self):
        p = self.plan(auth(**CELLS_ONE), "cells", only=["E1A-a:P2"], reps=1)
        self.assertEqual(p["bv_checks"], [])
        self.assertEqual([(t["scenario"], t["candidate"]) for t in p["trials"]], [("E1A-a", "P2")])
        self.assertTrue(p["partial"])

    def test_cells_phase_refuses_every_bv_request(self):
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**CELLS_ONE, **BV_ONE), "cells", only=["E1A-a:P2"], reps=1, bv=["BV-7"])

    def test_bv_phase_needs_its_own_authorization_and_explicit_ids(self):
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**CELLS_ONE), "bv", bv=["BV-7"])                       # cells authorization does not cover BV
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**BV_ONE), "bv")                                       # no implicit "all"
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**BV_ONE), "bv", bv=["BV-7", "BV-2"])                  # BV-2 (fault injection) not authorized
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**BV_ONE), "bv", bv=["BV-99"])
        p = self.plan(auth(**BV_ONE), "bv", bv=["BV-7"])
        self.assertEqual((p["bv_checks"], p["trials"]), (["BV-7"], []))

    def test_bv_phase_refuses_cell_options(self):
        for kw in ({"only": ["E1A-a:P2"]}, {"reps": 1}, {"all_cells": True}, {"no_sweep": False}):
            with self.assertRaises(RUN.AuthorizationError):
                self.plan(auth(**BV_ONE), "bv", bv=["BV-7"], **kw)

    def test_cells_beyond_the_authorization_are_refused(self):
        a = auth(**CELLS_ONE)
        for kw in ({"only": ["E1A-a:P1"], "reps": 1}, {"only": ["E1A-b:P2"], "reps": 1}, {"only": ["E1A-a:P2"], "reps": 2},
                   {"only": ["E1A-a:P2"], "reps": 0}, {"only": ["E1A-a:P2"], "reps": 1, "no_sweep": False}, {"all_cells": True, "reps": 1},
                   {"reps": 1}, {"only": ["E1A-a:P2"]}, {"only": ["nonsense"], "reps": 1}):
            with self.assertRaises(RUN.AuthorizationError, msg=kw):
                self.plan(a, "cells", **kw)

    def test_missing_or_unknown_phase_is_refused(self):
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**BV_ONE), "cells", only=["E1A-a:P2"], reps=1)
        with self.assertRaises(RUN.AuthorizationError):
            self.plan(auth(**CELLS_ONE), "everything")

    def test_all_cells_and_sweep_only_when_explicitly_authorized(self):
        a = auth(**{RUN.PHASE_CELLS: {"cells": "ALL", "max_reps": 20, "sweep": True}})
        p = self.plan(a, "cells", all_cells=True, reps=20, no_sweep=False)
        self.assertEqual(len(p["trials"]), PREREG["repetitions"]["planned_trials"]["total"])
        self.assertFalse(p["partial"])
        self.assertEqual(p["bv_checks"], [])

    def test_authorization_is_bound_to_prereg_and_bench_code_and_schema(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.json")
            good = auth(**CELLS_ONE)
            json.dump(good, open(p, "w"))
            self.assertEqual(RUN.load_authorization(p, SHA, "c" * 64)["authorization_id"], "T1")
            for bad in (dict(good, prereg_sha256="0" * 64), dict(good, bench_code_sha256="d" * 64), dict(good, authorized_by="claude"),
                        dict(good, schema="e1a-auth-1"), dict(good, authorization_id=""), dict(good, phases={})):
                json.dump(bad, open(p, "w"))
                with self.assertRaises(RUN.AuthorizationError, msg=bad):
                    RUN.load_authorization(p, SHA, "c" * 64)
            with self.assertRaises(RUN.AuthorizationError):
                RUN.load_authorization(os.path.join(d, "missing.json"), SHA, "c" * 64)

    def test_run_all_requires_an_explicit_known_subset_and_does_nothing_otherwise(self):
        for bad in ([], ["BV-99"], ["BV-7", "nope"]):
            with self.assertRaises(ValueError):
                V.run_all(None, "/nonexistent-must-not-be-created", bad)         # raises before touching anything
        self.assertFalse(os.path.exists("/nonexistent-must-not-be-created"))

    def test_id_lists_agree(self):
        self.assertEqual(tuple(RUN.V_RUN_LEVEL_IDS), tuple(V.RUN_LEVEL_IDS))
        self.assertEqual(set(V.FAULT_INJECTING), set(V.RUN_LEVEL_IDS))

    def test_execute_runs_validity_checks_only_when_the_plan_lists_them(self):
        src = inspect.getsource(RUN.execute)
        self.assertIn('if plan["bv_checks"]:', src)
        self.assertEqual(src.count("V.run_all("), 1)
        self.assertLess(src.index('if plan["bv_checks"]:'), src.index("V.run_all("))

    def test_main_has_no_default_phase_and_refuses_without_authorization(self):
        self.assertEqual(RUN.main(["--execute"]), 2)
        self.assertEqual(RUN.main(["--execute", "--phase", "cells", "--only", "E1A-a:P2", "--reps", "1"]), 2)    # no authorization file exists
        self.assertFalse(os.path.exists(RUN.AUTH_DEFAULT))

    def test_cell_results_need_a_verified_owner_binding_not_a_path(self):
        a = auth(**CELLS_ONE)                                                    # no bv_binding at all
        counted, detail = EV.evaluate_counting(a, True, SHA, "c" * 64)
        self.assertFalse(counted)
        self.assertFalse(detail["verified"])
        self.assertFalse(EV.evaluate_counting(a, False, SHA, "c" * 64)[0])      # nothing to count
        with self.assertRaises(SystemExit):                                      # the old user-supplied evidence path no longer exists
            RUN.main(["--execute", "--phase", "cells", "--bv-evidence", "x.json"])

    def test_summary_marks_uncounted_and_bv_only_runs(self):
        s = RUN.summarize(PREREG, [], [], True, None, False, (), True)
        self.assertTrue(s["experiment_verdict"].startswith("NO CELLS RUN"))
        plan = S.plan_trials(PREREG, reps=1, only_cells={("E1A-a", "P2")}, only_sweep=False)
        s = RUN.summarize(PREREG, plan, [], False, None, True, (), False)
        self.assertTrue(s["experiment_verdict"].startswith("SMOKE"))


# ===================================================================== /proc enumeration incompleteness => BLOCKED
class TestEnumerationIncomplete(unittest.TestCase):
    def test_enumeration_reasons(self):
        self.assertEqual(T.enumeration_reasons({}, "t"), [])
        self.assertIn("TRUTH_ENUMERATION_INCOMPLETE", T.enumeration_reasons({7: "EACCES"}, "pre-S0")[0])

    def test_incomplete_candidate_enumeration_blocks_instead_of_pass_or_fail(self):
        expected_pass = out("ACCEPT", enumeration_complete=False)
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", expected_pass, EV_OK, [])["verdict"], "BLOCKED")           # no determinate PASS
        wrong = out("UNKNOWN", unknown_reasons=["C4_NOT_PROVABLE_INCOMPLETE_ENUMERATION"])
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", wrong, EV_OK, [])["verdict"], "BLOCKED")                  # no mechanism FAIL
        self.assertEqual(T.judge(PREREG, "E1A-e1", "P1", out("UNKNOWN", unknown_reasons=["PROC_ENUMERATION_FAILED: x"]), EV_OK, [])["verdict"], "BLOCKED")
        blocked_wrong_codes = out("BLOCKED", ["ROOT_NOT_SESSION_LEADER"], ["PR-S0-1"], enumeration_complete=False)
        self.assertEqual(T.judge(PREREG, "E1A-b", "P2", blocked_wrong_codes, EV_OK, [])["verdict"], "BLOCKED")
        for cand in ("P0", "P1"):                                                                                  # adapters have no enumeration -> unaffected
            self.assertEqual(T.judge(PREREG, "E1A-a", cand, out("ACCEPT"), EV_OK, [])["verdict"], "PASS")

    def test_unsafe_event_still_wins_over_incomplete_enumeration(self):
        j = T.judge(PREREG, "E1A-a", "P2", out("UNKNOWN", enumeration_complete=False), EV_OK + [UNSAFE], [])
        self.assertEqual(j["verdict"], "FAIL")

    def test_s0_check_reports_enumeration_completeness(self):
        t = {1000: {"state": "S", "ppid": 1, "pgrp": 1000, "sid": 1000, "starttime": 1, "comm": "x"},
             1001: {"state": "S", "ppid": 1000, "pgrp": 1001, "sid": 1001, "starttime": 2, "comm": "x"}}

        def view(**kw):
            v = {"root_registered": {"pid": 1001, "starttime": 2, "sid": 1001, "pgrp": 1001}, "sup_pid": 1000, "sup_sid": 1000, "declared_aux": [],
                 "table": t, "problems": {}, "scan_error": None, "sigchld_is_default": True, "sigign_mask": 0}
            v.update(kw)
            return v
        ok = {"set_ok": True, "get_value": 1}
        self.assertTrue(K.s0_check(view(), ok, CHECKS)["enumeration_complete"])
        o = K.s0_check(view(problems={55: "EACCES"}), ok, CHECKS)
        self.assertEqual((o["verdict"], o["enumeration_complete"]), ("UNKNOWN", False))          # never ACCEPT on partial evidence
        o = K.s0_check(view(table=None, scan_error="listdir"), ok, CHECKS)
        self.assertEqual((o["verdict"], o["enumeration_complete"]), ("UNKNOWN", False))

    def test_trial_blocks_on_incomplete_observer_enumeration_before_and_after_s0(self):
        self.assertIn("enumeration_reasons(problems, \"pre-S0\")", inspect.getsource(TR._pre_s0))
        self.assertIn("enumeration_reasons(problems, \"post-S0\")", inspect.getsource(TR._post_s0))

    def test_stray_reasons_ignore_zombies_only(self):
        sup = mock.Mock(pid=1000)
        obs = mock.Mock()
        reg_node = mock.Mock(pid=1001)
        obs.trial_nodes.return_value = [mock.Mock(pid=1000), reg_node]
        table = {1000: {"ppid": 1, "state": "S"}, 1001: {"ppid": 1000, "state": "S"}, 1002: {"ppid": 1000, "state": "S"}, 1003: {"ppid": 1000, "state": "Z"}}
        self.assertIn("1002", TR._stray_reasons(obs, sup, table, "t")[0])
        self.assertNotIn("1003", TR._stray_reasons(obs, sup, table, "t")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
