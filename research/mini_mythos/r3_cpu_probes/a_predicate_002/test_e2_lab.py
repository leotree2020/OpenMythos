#!/usr/bin/env python3
"""Tool-correctness tests for the CPU-002 lab extensions (not tests of the candidate rules)."""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "a_predicate"))
import e2_lab as E
import a_lab as L
from a_lab import ALIVE, EXITED, UNKNOWN, RUNNING, ZOMBIE, GONE


def st(pid, ppid, state="S", start=100, sid=None, pgrp=None):
    return {"state": state, "ppid": ppid, "pgrp": pgrp or pid, "sid": sid or pid, "starttime": start, "comm": "x"}


class FakeFS(L.ProcFS):
    def __init__(self, table):
        self.table = table

    def scan(self):
        return dict(self.table), {}

    def stat(self, pid):
        if pid not in self.table:
            raise L.Vanished(pid)
        return self.table[pid]


ME = os.getpid()


class TestStrictDiscovery(unittest.TestCase):
    def arm(self, table, root_sid=5000, root_start=100):
        a = E.ArmCAS(None)
        a.fs = FakeFS(table)
        a.subreaper_ok = True
        a.targets[5000] = L.Target(5000, st(5000, 4999, "S", root_start, sid=root_sid), "root", direct=True)
        a.stage_sid = root_sid
        a.root_starttime = root_start
        a.dedicated_session = (root_sid == 5000)
        return a

    def test_lineage_target(self):
        a = self.arm({5000: st(5000, 4999), 5001: st(5001, 5000, sid=5001)})
        a.poll()
        self.assertEqual(a.targets[5001].how, "lineage")

    def test_unregistered_child_older_than_root_is_ignored_not_unknown(self):
        a = self.arm({5000: st(5000, 4999, start=100), 6000: st(6000, ME, start=50)})
        o = a.poll()
        self.assertNotIn(6000, a.targets)
        self.assertIn(6000, a.ignored_older)
        self.assertEqual(o["tri"], ALIVE)

    def test_unregistered_child_newer_than_root_is_unattributable(self):
        a = self.arm({5000: st(5000, 4999, "Z", start=100), 6000: st(6000, ME, start=150)})
        o = a.poll()
        self.assertNotIn(6000, a.targets)
        self.assertEqual(o["tri"], UNKNOWN)

    def test_sid_hint_refused_when_session_not_dedicated(self):
        a = self.arm({5000: st(5000, 4999, sid=777), 6000: st(6000, 1, sid=777)}, root_sid=777)
        a.poll()
        self.assertNotIn(6000, a.targets)

    def test_sid_hint_used_when_dedicated(self):
        a = self.arm({5000: st(5000, 4999), 6000: st(6000, 1, sid=5000)})
        a.poll()
        self.assertEqual(a.targets[6000].how, "sid_hint_dedicated")

    def test_aux_family_is_neither_target_nor_unknown(self):
        a = self.arm({5000: st(5000, 4999, "Z"), 7000: st(7000, ME, start=120), 7001: st(7001, 7000, sid=7001, start=130)})
        a.aux[7000] = 120
        o = a.poll()
        self.assertIn(7001, a.aux_family)
        self.assertEqual(o["tri"], EXITED)
        a.fs = FakeFS({5000: st(5000, 4999, "Z"), 7001: st(7001, ME, sid=7001, start=130)})      # aux died, family member re-parented
        self.assertEqual(a.poll()["tri"], EXITED)


class TestSpawnLab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab = E.SpawnLab()
        cls.lab.set_subreaper(True)

    @classmethod
    def tearDownClass(cls):
        cls.lab.final_cleanup()

    def setUp(self):
        self.lab.begin()

    def tearDown(self):
        r = self.lab.cleanup()
        self.assertEqual(r["residual_nodes"], [])

    def test_new_session_false_shares_the_supervisors_session(self):
        n = self.lab.spawn({"name": "R"}, new_session=False)["R"]
        self.assertEqual(n["sid"], os.getsid(0))
        self.assertNotEqual(n["sid"], n["pid"])

    def test_default_spawn_leads_its_own_session(self):
        n = self.lab.spawn({"name": "R"})["R"]
        self.assertEqual(n["sid"], n["pid"])

    def test_detached_same_session_node_is_not_a_child(self):
        n = self.lab.spawn_detached("X", new_session=False)
        st0 = L._oracle_stat(n["pid"])
        self.assertNotEqual(st0["ppid"], os.getpid())
        self.assertEqual(n["sid"], os.getsid(0))

    def test_fresh_session_body_runs_in_its_own_session(self):
        outer = os.getsid(0)

        def body(lab2):
            return {"sid_inside": os.getsid(0), "is_leader": os.getsid(0) == os.getpid()}
        res = E.run_in_fresh_session(body)
        self.assertNotEqual(res["sid_inside"], outer)
        self.assertTrue(res["is_leader"])

    def test_capp_reads_status_from_popen_only(self):
        lab = self.lab
        p = subprocess.Popen([sys.executable, "-S", "-c", "import sys; sys.exit(7)"], start_new_session=True)
        end = L.now() + 5
        while L.now() < end and (L._oracle_stat(p.pid) or {}).get("state") != "Z":
            import time; time.sleep(0.003)
        st0 = L._oracle_stat(p.pid)
        node = {"name": "P", "pid": p.pid, "starttime": st0["starttime"], "sid": st0["sid"], "pgrp": st0["pgrp"], "ppid": st0["ppid"]}
        a = E.ArmCAP(lab)
        a.register_root(node)
        a.popens[p.pid] = p
        a.subreaper_ok = True
        o = a.poll()
        self.assertEqual(a.exit_status(p.pid), {"kind": "exit", "code": 7})
        self.assertEqual(p.returncode, 7)
        self.assertEqual(o["tri"], EXITED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
