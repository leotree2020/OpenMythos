"""E1-A bench tests -- PROCESS LEVEL (forks gated sacrificial processes, writes SIGKILL through identity-confirmed pidfds).
WRITTEN, NOT RUN.  Run only after the owner separately authorizes the first controlled CPU run."""
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
import common as C          # noqa: E402
import janitor as J         # noqa: E402
import node as N            # noqa: E402
import observer as O        # noqa: E402
import registry as R        # noqa: E402
import scenarios as S       # noqa: E402
import trial as TR          # noqa: E402
import validity as V        # noqa: E402

SLEEPER = {"label": "t", "role": "sleeper", "mode": "setsid", "children": [], "exit_after_ready": False}


class GateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.obs = O.Observer(os.path.join(self.tmp.name, "registry.jsonl"))
        self.obs.trial_tag = "TEST"

    def tearDown(self):
        reports = []
        for tag in sorted({r.trial for r in self.obs.nodes.values() if r.trial}):    # validity checks use their own tags
            self.obs.trial_tag = tag
            reports.append(self.obs.finish_trial_cleanup())
        self.tmp.cleanup()
        for rep in reports:
            self.assertTrue(rep["cleanup_ok"], rep)


class TestGateProtocol(GateCase):
    def test_released_node_reports_ready_with_its_own_session(self):
        rec = self.obs.spawn_direct("t", "T", dict(SLEEPER), N.node_main)
        self.assertEqual(rec.state, "RELEASED")
        self.assertTrue(self.obs.wait_for(lambda: rec.ready is not None, 5.0))
        self.assertEqual(rec.ready["fp"]["sid"], rec.pid)

    def test_unreleased_node_does_nothing_and_abort_ends_it(self):
        self.assertTrue(V.bv1_unreleased_cannot_act(self.obs)["ok"])

    def test_silent_gate_times_out_with_exit_112(self):
        self.assertTrue(V.bv3_gate_silent_timeout(self.obs)["ok"])

    def test_observer_death_closes_the_gate(self):
        self.assertTrue(V.bv2_observer_death_before_register(self.obs, self.tmp.name)["ok"])

    def test_closing_the_gate_write_end_ends_the_child_with_exit_111(self):
        rec = self.obs.spawn_direct("t", "T", dict(SLEEPER), N.node_main, hold_release=True)
        os.close(rec.gate_w)
        rec.gate_w = None
        self.assertTrue(self.obs.wait_for(lambda: C.process_is_dead(rec.pid, rec.starttime), 5.0))
        self.obs.reap_direct()
        self.assertEqual(rec.exit_status, C.EXIT_GATE_ABORT)

    def test_descendants_are_registered_through_tickets_and_ordered(self):
        spec = dict(SLEEPER, label="parent", children=[{"label": "kid", "role": "sleeper", "mode": "none", "children": [], "exit_after_ready": False}])
        rec = self.obs.spawn_direct("t", "parent", spec, N.node_main)
        self.assertTrue(self.obs.wait_for(lambda: self.obs.find("kid") is not None and self.obs.find("kid").ready is not None, 8.0))
        kid = self.obs.find("kid")
        self.assertEqual(kid.fp["ppid"], rec.pid)
        self.assertEqual(R.check_order(self.obs.trial_records()), [])

    def test_no_gate_write_end_leaks_into_nodes(self):
        rec = self.obs.spawn_direct("t", "T", dict(SLEEPER), N.node_main)
        self.assertTrue(self.obs.wait_for(lambda: rec.ready is not None, 5.0))
        import truth
        self.assertEqual(truth.fd_hygiene_reasons(rec.pid, [r.gate_ino for r in self.obs.trial_nodes()], TR.FD_ALLOWED_MAX), [])

    def test_janitor_refuses_a_wrong_identity_and_acts_on_the_right_one(self):
        self.assertTrue(V.bv6_janitor_refuses_wrong_identity(self.obs, self.tmp.name)["ok"])

    def test_janitor_ignores_intent_only_and_torn_records(self):
        self.assertTrue(V.bv7_janitor_ignores_intent_only_and_torn(self.tmp.name)["ok"])


class TestStaticFixProcessPaths(GateCase):
    """Process-level failure paths for STATIC-FIX-001 (fix 2 and fix 3).  Pure-logic counterparts: test_e1a_staticfix.py."""

    def test_failed_registration_keeps_cleanup_responsibility_until_death_is_confirmed(self):
        real = C.fingerprint

        def wrong_ppid(pid):
            fp = real(pid)
            return None if fp is None else dict(fp, ppid=fp["ppid"] + 1)
        with mock.patch.object(C, "fingerprint", wrong_ppid):
            rec = self.obs.spawn_direct("t", "T", dict(SLEEPER), N.node_main)
        self.assertEqual(rec.state, "ABORTED")
        self.assertIsNotNone(rec.forked_pid)
        self.assertTrue([x for x in self.obs.reg.records if x["kind"] == "FORKED" and x["node_id"] == rec.node_id])   # known from fork on
        rep = self.obs.finish_cleanup(grace=5.0)
        self.assertTrue(rep["cleanup_ok"], rep)
        self.assertEqual(rec.exit_status, C.EXIT_GATE_ABORT)                    # the gated child saw the abort byte
        self.assertEqual(rec.state, "DEAD")
        self.assertTrue([x for x in self.obs.reg.records if x["kind"] == "DEAD" and x["node_id"] == rec.node_id])
        self.obs.problems.clear()

    def test_janitor_cleans_up_when_run_end_does_not_confirm_cleanup(self):
        rec = self.obs.spawn_direct("t", "T", dict(SLEEPER), N.node_main)
        self.assertTrue(self.obs.wait_for(lambda: rec.ready is not None, 5.0))
        self.obs.reg.write("RUN_END", aborted="runner exception", cleanup_confirmed=False)
        records = R.parse_reg(self.obs.reg_path)[0]
        self.assertEqual(J.decide(records, False), "CLEANUP")
        clear, _ = J.cleanup_until_clear(self.obs.reg_path, None, attempts=10, interval=0.2)
        self.assertTrue(clear)
        self.assertTrue(C.process_is_dead(rec.pid, rec.starttime))
        self.obs.reap_direct()

    def test_janitor_does_not_trust_a_false_confirmation(self):
        rec = self.obs.spawn_direct("t", "T", dict(SLEEPER), N.node_main)
        self.assertTrue(self.obs.wait_for(lambda: rec.ready is not None, 5.0))
        self.obs.reg.write("RUN_END", aborted=None, cleanup_confirmed=True)     # a lie: the registered node is alive
        self.assertEqual(J.decide(R.parse_reg(self.obs.reg_path)[0], False), "CLEANUP")


class TestFullTrialSmoke(GateCase):
    """One real E1A-a trial per candidate: topology as designed, blindness, hygiene, instrumentation, verdict, clean cleanup."""

    def run_one(self, scn, cand):
        prereg, sha = S.load_prereg()
        item = {"kind": "cell", "scenario": scn, "candidate": cand, "rep": 0, "launch": "L1", "trial_id": "TSMOKE"}
        from e1a_runner import pins_from_prereg
        rec = TR.run_trial(self.obs, prereg, item, pins_from_prereg(prereg), {"prereg_sha": sha})
        self.obs.trial_tag = "TEST"
        return rec

    def test_correct_configuration_is_accepted_by_all_candidates(self):
        for cand in ("P0", "P1", "P2"):
            rec = self.run_one("E1A-a", cand)
            self.assertEqual(rec["bench_reasons"], [], rec["bench_reasons"])
            self.assertEqual(rec["verdict"], "PASS", rec["judgement"])

    def test_session_sharing_root_is_blocked_by_p2_and_missed_by_p0(self):
        self.assertEqual(self.run_one("E1A-b", "P2")["verdict"], "PASS")
        self.assertEqual(self.run_one("E1A-b", "P0")["verdict"], "FAIL")        # frozen capability finding, not a tuned prediction


if __name__ == "__main__":
    unittest.main(verbosity=2)
