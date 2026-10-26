"""Unit tests for the G1/G2 probe tooling (tool correctness only; they do NOT decide G1/G2 for the R3 rule).
Real Linux children are used for every system-call-dependent test.  Run:  python3 -m unittest -v test_g1g2_probe"""
import os, signal, sys, time, unittest
import g1g2_probe as P


class ProbeTooling(unittest.TestCase):
    def tearDown(self):
        P.cleanup()

    def test_expected_a_table_follows_intent(self):
        # intent (R3 11.1(d)): A false <=> all target processes have exited
        self.assertEqual(P.EXPECTED_A, {"RUNNING": True, "EXITED_UNREAPED": False, "REAPED": False})

    def test_oracle_distinguishes_running_zombie_reaped(self):
        pid = P.spawn("SLEEP")
        self.assertTrue(P.wait_for(pid, "RUNNING"))
        self.assertEqual(P.signal_group(pid, signal.SIGKILL)["result"], "sent")
        self.assertTrue(P.wait_for(pid, "EXITED_UNREAPED"))
        s, detail = P.truth(pid)
        self.assertEqual((s, detail["proc_state"]), ("EXITED_UNREAPED", "Z"))
        # waitid(WNOWAIT) must not consume the status: still a zombie afterwards
        self.assertEqual(P.truth(pid)[0], "EXITED_UNREAPED")
        r = P.reap_nowait(pid)
        self.assertEqual(r["returned_pid"], pid)
        self.assertEqual(P.truth(pid)[0], "REAPED")

    def test_children_are_in_their_own_process_group(self):
        pid = P.spawn("SLEEP")
        self.assertEqual(os.getpgid(pid), pid)
        self.assertNotEqual(os.getpgid(pid), os.getpgrp())

    def test_guard_refuses_foreign_pids_and_own_group(self):
        with self.assertRaises(P.SafetyError):
            P.signal_group(os.getpid(), signal.SIGTERM)
        with self.assertRaises(P.SafetyError):
            P.signal_group(1, signal.SIGTERM)
        pid = P.spawn("SLEEP")
        P.SPAWNED[pid]["pgid"] = os.getpgrp()            # corrupted bookkeeping must be refused
        with self.assertRaises(P.SafetyError):
            P.signal_group(pid, signal.SIGTERM)
        P.SPAWNED[pid]["pgid"] = pid

    def test_guard_refuses_signal_after_reap(self):
        pid = P.spawn("QUICK_EXIT")
        self.assertTrue(P.wait_for(pid, "EXITED_UNREAPED"))
        P.reap_nowait(pid)
        with self.assertRaises(P.SafetyError):
            P.signal_group(pid, signal.SIGKILL)

    def test_killpg_on_zombie_only_group_is_recorded_not_assumed(self):
        # characterisation of the observed kernel behaviour (not an assertion about what R3 wants)
        pid = P.spawn("QUICK_EXIT")
        self.assertTrue(P.wait_for(pid, "EXITED_UNREAPED"))
        before = P.probe_killpg0(pid)
        self.assertIn(before, ("success", "ESRCH"))
        P.reap_nowait(pid)
        self.assertEqual(P.probe_killpg0(pid), "ESRCH")

    def test_literal_A_reflects_bookkeeping_not_exit(self):
        pid = P.spawn("QUICK_EXIT")
        self.assertTrue(P.wait_for(pid, "EXITED_UNREAPED"))
        a = P.r3_A(pid)
        self.assertTrue(a["c1_not_reaped"])              # condition (1) is bookkeeping: exit alone does not clear it
        P.reap_nowait(pid)
        a2 = P.r3_A(pid)
        self.assertFalse(a2["c1_not_reaped"])
        self.assertFalse(a2["A"])

    def test_cleanup_leaves_no_residual(self):
        for _ in range(3):
            P.spawn("SLEEP")
        rep = P.cleanup()
        self.assertEqual(rep["residual_pids_in_proc"], [])
        self.assertEqual(rep["token_scan_pids"], [])

    def test_environment_report_has_required_fields(self):
        env = P.environment()
        for k in ("kernel", "python", "git_branch", "git_commit", "proc_available", "os.waitid", "os.WNOWAIT", "probe_pid", "probe_pgid"):
            self.assertIn(k, env)
        self.assertTrue(env["proc_available"] and env["os.waitid"] and env["os.WNOWAIT"])


if __name__ == "__main__":
    unittest.main()
