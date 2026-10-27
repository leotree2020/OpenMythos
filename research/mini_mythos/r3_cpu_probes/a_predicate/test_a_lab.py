#!/usr/bin/env python3
"""Tool-correctness tests for the R3-A CPU lab (F3B-D1-A-CPU-001).  These test the TEST BENCH (oracle, node topology,
fault injection, tri-state combination, source-level safety rules), not the candidate rules themselves."""
import inspect
import os
import signal
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a_lab as L
from a_lab import ALIVE, EXITED, UNKNOWN, RUNNING, ZOMBIE, GONE


class LabCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab = L.Lab()
        cls.lab.set_subreaper(True)

    @classmethod
    def tearDownClass(cls):
        cls.lab.final_cleanup()

    def setUp(self):
        self.lab.begin()

    def tearDown(self):
        r = self.lab.cleanup()
        self.assertEqual(r["residual_nodes"], [])
        self.assertEqual(r["children_of_supervisor"], [])


class TestOracleAndTopology(LabCase):
    def test_oracle_follows_running_zombie_gone(self):
        n = self.lab.spawn({"name": "R", "exit_code": 4})["R"]
        self.assertEqual(L.oracle_state(n)[0], RUNNING)
        self.lab.go("R", "exit", 4)
        self.lab.wait_state(n, ZOMBIE)
        r = os.waitpid(n["pid"], 0)
        self.assertEqual(L.decode_status(r[1]), {"kind": "exit", "code": 4})
        self.assertEqual(L.oracle_state(n)[0], GONE)

    def test_topology_reports_and_reparenting(self):
        nodes = self.lab.spawn({"name": "L", "children": [{"name": "D", "term": "ignore"}]})
        self.assertEqual(nodes["D"]["ppid"], nodes["L"]["pid"])
        self.assertEqual(nodes["D"]["sid"], nodes["L"]["sid"])
        self.lab.go("L", "exit", 0)
        self.lab.wait_state(nodes["L"], ZOMBIE)
        end = time.monotonic() + 3
        while time.monotonic() < end and L._oracle_stat(nodes["D"]["pid"])["ppid"] != os.getpid():
            time.sleep(0.003)
        self.assertEqual(L._oracle_stat(nodes["D"]["pid"])["ppid"], os.getpid(), "subreaper must adopt the orphan")

    def test_setsid_child_changes_session(self):
        nodes = self.lab.spawn({"name": "L", "children": [{"name": "D", "setsid": True}]})
        self.assertNotEqual(nodes["D"]["sid"], nodes["L"]["sid"])
        self.assertEqual(nodes["D"]["sid"], nodes["D"]["pid"])

    def test_bench_kill_status_signal(self):
        n = self.lab.spawn({"name": "R"})["R"]
        self.lab.kill_by_bench(n, signal.SIGKILL)
        self.lab.wait_state(n, ZOMBIE)
        r = os.waitpid(n["pid"], 0)
        self.assertEqual(L.decode_status(r[1]), {"kind": "signal", "sig": 9})


class TestFaultInjection(unittest.TestCase):
    def test_listdir_fault_is_scan_failure(self):
        with self.assertRaises(L.ScanFailed):
            L.FaultyProcFS(listdir_errno=5).scan()

    def test_stat_faults_are_unreadable_not_vanished(self):
        me = os.getpid()
        for kind in ("EACCES", "EIO", "garble"):
            with self.assertRaises(L.Unreadable):
                L.FaultyProcFS(stat_faults={me: kind}).stat(me)
        table, problems = L.FaultyProcFS(stat_faults={me: "EACCES"}).scan()
        self.assertIn(me, problems)
        self.assertNotIn(me, table)

    def test_missing_pid_is_vanished(self):
        with self.assertRaises(L.Vanished):
            L.ProcFS().stat(4194303)


class FakeFS(L.ProcFS):
    def __init__(self, table, problems=None):
        self.table, self.problems = table, problems or {}

    def scan(self):
        return dict(self.table), dict(self.problems)

    def stat(self, pid):
        if pid in self.problems:
            raise L.Unreadable("x")
        if pid not in self.table:
            raise L.Vanished(pid)
        return self.table[pid]


def st(pid, ppid, state="S", start=100, sid=None, pgrp=None):
    return {"state": state, "ppid": ppid, "pgrp": pgrp or pid, "sid": sid or pid, "starttime": start, "comm": "x"}


class TestTriState(unittest.TestCase):
    """Pure combination logic on a fake /proc: non-child targets only, so no waitpid/waitid is involved."""

    def arm(self, table, problems=None, subreaper=True):
        a = L.ArmCA(None)
        a.fs = FakeFS(table, problems)
        a.subreaper_ok = subreaper
        base = st(5000, 4999, "S", 100)       # a non-child root (ppid is not this process)
        a.targets[5000] = L.Target(5000, base, "root", direct=True)
        a.stage_sid = 5000
        return a

    def test_alive_when_target_running(self):
        a = self.arm({5000: st(5000, 4999, "S", 100)})
        self.assertEqual(a.poll()["tri"], ALIVE)

    def test_zombie_target_is_exited(self):
        a = self.arm({5000: st(5000, 4999, "Z", 100)})
        self.assertEqual(a.poll()["tri"], EXITED)

    def test_vanished_verified_target_is_exited(self):
        self.assertEqual(self.arm({}).poll()["tri"], EXITED)

    def test_identity_mismatch_is_unknown(self):
        o = self.arm({5000: st(5000, 4999, "S", 101)}).poll()
        self.assertEqual(o["tri"], UNKNOWN)
        self.assertTrue(any("IDENTITY" in r for r in o["reasons"]))

    def test_unreadable_target_is_unknown(self):
        o = self.arm({}, {5000: "x"}).poll()
        self.assertEqual(o["tri"], UNKNOWN)

    def test_subreaper_unverified_never_exited(self):
        o = self.arm({5000: st(5000, 4999, "Z", 100)}, subreaper=False).poll()
        self.assertEqual(o["tri"], UNKNOWN)

    def test_alive_beats_unknown(self):
        t = {5000: st(5000, 4999, "S", 100), 5001: st(5001, 5000, "S", 7)}
        a = self.arm(t)
        a.poll()
        a.fs = FakeFS(t, {5001: "x"})
        self.assertEqual(a.poll()["tri"], ALIVE)

    def test_scan_failure_is_unknown(self):
        a = self.arm({})
        a.fs = L.FaultyProcFS(listdir_errno=5)
        self.assertEqual(a.poll()["tri"], UNKNOWN)

    def test_lineage_and_sid_hint_do_not_exclude_setsid(self):
        t = {5000: st(5000, 4999, "S", 100), 5001: st(5001, 5000, "S", 7, sid=5001)}     # setsid()'d descendant
        a = self.arm(t)
        a.poll()
        self.assertIn(5001, a.targets)
        self.assertEqual(a.targets[5001].how, "lineage")


class TestSignalGuards(unittest.TestCase):
    def test_pidfd_esrch_is_gone_not_unknown(self):
        a = L.ArmCA(None)
        a.fs = FakeFS({})
        tg = L.Target(5000, st(5000, 4999, "S", 100), "root")
        a.targets[5000] = tg

        def esrch(pid):
            raise ProcessLookupError(3, "x")
        a.pidfd_open = esrch
        rec = a.signal_target(tg, signal.SIGKILL)
        self.assertEqual(rec["result"], "gone_before_signal")
        self.assertEqual(tg.state, ALIVE)

    def test_pidfd_enosys_is_unknown_and_no_signal(self):
        a = L.ArmCA(None)
        a.fs = FakeFS({})
        tg = L.Target(5000, st(5000, 4999, "S", 100), "root")

        def enosys(pid):
            raise OSError(38, "x")
        a.pidfd_open = enosys
        rec = a.signal_target(tg, signal.SIGKILL)
        self.assertEqual(rec["result"], "refused_pidfd_unavailable")
        self.assertEqual(tg.state, UNKNOWN)


class TestSourceRules(unittest.TestCase):
    def test_candidates_never_wait_on_minus_one_or_p_all(self):
        for cls in (L.ArmCommon, L.ArmCA, L.ArmCB):
            src = inspect.getsource(cls)
            self.assertNotIn("waitpid(-1", src, cls.__name__)
            self.assertNotIn("P_ALL", src, cls.__name__)
            self.assertNotIn("os.killpg", src, cls.__name__)
            self.assertNotIn("os.kill(", src, cls.__name__)

    def test_cb_observes_with_wnowait_and_ca_does_not(self):
        self.assertIn("WNOWAIT", inspect.getsource(L.ArmCB._observe_child))
        self.assertNotIn("WNOWAIT", inspect.getsource(L.ArmCA._observe_child))

    def test_baseline_reap_uses_waitpid_minus_one_as_in_r3_t5(self):
        self.assertIn("waitpid(-1", inspect.getsource(L.ArmB0.t5_reap))


class TestBaselineLiteralA(LabCase):
    def test_c1_stays_true_for_unreaped_zombie_and_killpg0_succeeds(self):
        n = self.lab.spawn({"name": "R"})["R"]
        arm = L.ArmB0(self.lab, "NOREAP")
        arm.register_root(n)
        self.lab.go("R", "exit", 0)
        self.lab.wait_state(n, ZOMBIE)
        o = arm.poll()
        self.assertTrue(o["components"]["c1"])
        self.assertEqual(arm._killpg0(), "success", "this is the behaviour G1/G2 recorded on the zombie-only group")
        arm2 = L.ArmB0(self.lab, "REAP_THEN_EVAL")
        arm2.register_root(n)
        o2 = arm2.poll()
        self.assertFalse(o2["A"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
