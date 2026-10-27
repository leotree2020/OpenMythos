"""G1 mutation tests (CPU; WRITTEN, NOT RUN -- NOT TESTED).  Each mutation is a one-line source change of g1_judge.py / g1_run.py that would let a wrong
result through (a leaked gate, a wrong exit code, a lost zombie / reap requirement, an unfaithful durable copy treated as evidence, an incomplete run called
PASS, an unconditional exit code, ...).  The mutated source is executed as a separate module object (the repository files are never changed) and a targeted
evidence case must give a DIFFERENT result than the real judge -- i.e. the case discriminates and the check is not vacuous.  No process is started."""
import contextlib
import io
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_fixtures as F  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_judge as GJ  # noqa: E402
import g1_run as R  # noqa: E402

CRIT = F.criteria()
SHA = G1A.FROZEN_G1_CRITERIA_SHA256


def load_mutant(filename, repl):
    path = os.path.join(G1A.HERE, filename)
    with open(path, encoding="utf-8") as f:
        src = f.read()
    for old, new in repl:
        assert src.count(old) == 1, "mutation anchor not unique in %s: %r" % (filename, old)
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_" + filename[:-3])
    mod.__file__ = path
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


def state(res, tid, cid):
    e = res["tests"][tid]["checks"][cid]
    return e["state"], e["rule"]


def with_violation(call):
    ev = F.good_evidence()
    ev["guard"]["violations"].append({"call": call, "mono": 1.0, "test": "T1_ABORT", "args": ""})
    return ev


def t4_late_identity():
    return F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.snapshots.S1b_pre_stimulus.mono": 1031.6})


def released_t2():
    ev = F.good_evidence()
    L = ev["reg_memory_records"]
    idx = next(i for i, r in enumerate(L) if r["kind"] == "DEAD" and r.get("node_id") == "n00002")
    L.insert(idx, {"seq": 0, "kind": "RELEASED", "mono": L[idx]["mono"] - 0.001, "wall": L[idx]["wall"], "node_id": "n00002"})
    for i, r in enumerate(L):
        r["seq"] = i + 1
    return F.sync_ledger(ev)


def altered_durable():
    ev = F.good_evidence()
    ev["reg"][2]["label"] = "tampered"
    return ev


# (name, replacements, evidence, test id or None, check id or None, what to compare)
JUDGE_MUTATIONS = [
    ("exit 113 treated as a gate status", [('if code in (111, 112):', 'if code in (111, 112, 113):')], F.mutate(F.good_evidence(), **{"tests.T1_ABORT.reap.exit_status": 113}), "T1_ABORT", "G1-C10"),
    ("expected exit code not compared", [('if code != scn["expected_exit"]:', 'if False:')], F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.reap.exit_status": 111}), "T4_TIMEOUT", "G1-C10"),
    ("an R write is not looked for", [('f1 = [v for v in viol if isinstance(v, dict) and v.get("call") in (R_WRITE_CALL, RELEASE_CALL)]', 'f1 = []')],
     with_violation(GJ.R_WRITE_CALL), "T1_ABORT", "G1-C07"),
    ("a release call is not looked for", [('f1 = [v for v in viol if isinstance(v, dict) and v.get("call") in (R_WRITE_CALL, RELEASE_CALL)]', 'f1 = []')],
     with_violation(GJ.RELEASE_CALL), "T2_EOF", "G1-C07"),
    ("sid / pgrp change not looked for", [('if (ch.get("sid"), ch.get("pgrp")) != (ob["sid"], ob["pgrp"]):', 'if False:')],
     F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S1b_pre_stimulus.child.sid": 123}), "T1_ABORT", "G1-C05"),
    ("a message before release not looked for", [('if s["messages_received"] != 0 or s.get("first_action_mono") is not None:', 'if False:')],
     F.mutate(F.good_evidence(), **{"tests.T2_EOF.snapshots.S1_held_registered_unreleased.messages_received": 1}), "T2_EOF", "G1-C05"),
    ("the zombie state is not required", [('if not isinstance(ch, dict) or ch.get("state") != "Z" or ch.get("ppid") != obs_pid:', 'if False:')],
     F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S3_exited_unreaped.child.state": "S"}), "T1_ABORT", "G1-C08"),
    ("a wait call on another pid is accepted", [('if any(c["pid"] != pid for c in calls):', 'if False:')], None, "T2_EOF", "G1-C09"),
    ("pid identity not compared", [('pids_eq = reg["pid"] == held.get("pid") == held_b.get("pid") == fe["pid"] == pids[idx] == node["pid"]', 'pids_eq = True')],
     F.mutate(F.good_evidence(), **{"tests.T1_ABORT.snapshots.S1b_pre_stimulus.child.pid": 6000}), "T1_ABORT", "G1-C04"),
    ("identity margin before the gate timer ignored", [('late = [n for n, s in (("S1", s1), ("S1b", s1b)) if s["mono"] - fe["mono_before"] > t["t_gate_max"] - margin]', 'late = []')],
     t4_late_identity(), "T4_TIMEOUT", "G1-C04"),
    ("an unfaithful durable copy is trusted (M-2 removed)", [('need(fid["available"] and fid["faithful"] is True, "M-2: the durable copy', 'need(True, "M-2: the durable copy')],
     altered_durable(), "T1_ABORT", "G1-C04"),
    ("more forks than tests accepted", [('if g["fork_calls"] > len(ran):', 'if False:')], F.mutate(F.good_evidence(), **{"guard.fork_calls": 5}), "T1_ABORT", "G1-C11"),
    ("guard violations ignored by zero_signals", [('return _res(not viol and not bad, "C12-F1"', 'return _res(not bad, "C12-F1"')], with_violation("os.kill"), "T1_ABORT", "G1-C12"),
    ("per-test time bound ignored", [('if tm["duration"] > lim["per_test_seconds"]:', 'if False:')], F.mutate(F.good_evidence(), **{"tests.T1_ABORT.timing.duration": 7.5}), "T1_ABORT", "G1-C15"),
    ("a T4 gate closed before the exit accepted", [('if any(c["mono"] < pr for c in closes) or gate_open is not True or len(closes) > 1:', 'if False:')],
     F.mutate(F.good_evidence(), **{"guard.gate_closes.3.mono": 1030.5}), "T4_TIMEOUT", "G1-C07"),
    ("a RELEASED record not recognised by the sequence check", [('if (not is_prefix) or (completed is True and mine != scn_kinds) or any(r["kind"] == "RELEASED" for r in L):', 'if False:')],
     released_t2(), "T2_EOF", "G1-C03"),
    ("a 112 earlier than the timer accepted", [('if evs["pidfd_readable_mono"] < earliest:', 'if False:')],
     F.mutate(F.good_evidence(), **{"tests.T4_TIMEOUT.events.pidfd_readable_mono": 1031.05}), "T4_TIMEOUT", "G1-C10"),
]


class TestMutationAnchors(unittest.TestCase):
    def test_every_anchor_occurs_exactly_once_in_the_current_source(self):
        for name, repl, _, _, _ in JUDGE_MUTATIONS:
            src = open(os.path.join(G1A.HERE, "g1_judge.py"), encoding="utf-8").read()
            for old, new in repl:
                self.assertEqual(src.count(old), 1, name)
                self.assertNotEqual(old, new, name)


class TestJudgeMutations(unittest.TestCase):
    def test_each_mutant_gives_a_different_result_than_the_real_judge_on_its_case(self):
        for name, repl, ev, tid, cid in JUDGE_MUTATIONS:
            with self.subTest(name):
                if ev is None:
                    ev = F.good_evidence()
                    ev["guard"]["waitpid_calls"].append({"test": "T2_EOF", "pid": 12345, "options": 1, "returned": 0, "status": 0, "mono": 1010.55})
                real = GJ.judge(ev, CRIT, SHA)
                mutant = load_mutant("g1_judge.py", repl).judge(ev, CRIT, SHA)
                self.assertNotEqual(state(real, tid, cid)[0], "PASS", "the real judge must not pass the case")
                self.assertNotEqual(state(real, tid, cid), state(mutant, tid, cid), name)

    def test_a_mutant_that_calls_an_incomplete_run_pass(self):
        ev = F.good_evidence(ran=2)
        real = GJ.judge(ev, CRIT, SHA)
        mutant = load_mutant("g1_judge.py", [('elif run_blocks or "BLOCKED" in verdicts or incomplete or not ran:', 'elif run_blocks or "BLOCKED" in verdicts or not ran:')]).judge(ev, CRIT, SHA)
        self.assertEqual((real["verdict"], mutant["verdict"]), ("BLOCKED", "PASS"))

    def test_a_mutant_that_does_not_let_a_failed_test_fail_the_run(self):
        ev = F.mutate(F.good_evidence(), **{"tests.T1_ABORT.reap.exit_status": 0})
        real = GJ.judge(ev, CRIT, SHA)
        mutant = load_mutant("g1_judge.py", [('if run_fails or "FAIL" in verdicts:', 'if run_fails:')]).judge(ev, CRIT, SHA)
        self.assertEqual((real["verdict"], mutant["verdict"]), ("FAIL", "PASS"))

    def test_a_wrong_exit_code_table_is_caught_by_the_judge_itself(self):
        ev = F.mutate(F.good_evidence(), **{"tests.T1_ABORT.reap.exit_status": 0})
        mutant = load_mutant("g1_judge.py", [('EXIT_FOR = {"PASS": 0, "FAIL": 1, "BLOCKED": 3}', 'EXIT_FOR = {"PASS": 0, "FAIL": 0, "BLOCKED": 3}')])
        with self.assertRaises(AssertionError):
            mutant.judge(ev, CRIT, SHA)

    def test_a_mutant_that_accepts_a_non_canonical_marker(self):
        obj, raw = GJ.build_marker("g1_20261101_120000_abc123", "a" * 64, b"e", b"s", "PASS", 0)
        mutant = load_mutant("g1_judge.py", [('if again != bytes(raw):', 'if False:')])
        self.assertEqual((GJ.classify_marker(raw + b"\n")[0], mutant.classify_marker(raw + b"\n")[0]), ("noncanonical", "ok"))

    def test_a_mutant_that_lets_a_marker_claim_process_exit_proof(self):
        obj, _ = GJ.build_marker("g1_20261101_120000_abc123", "a" * 64, b"e", b"s", "PASS", 0)
        bad = dict(obj, process_exit_proof=True)
        mutant = load_mutant("g1_judge.py", [('if o["process_exit_proof"] is not False:', 'if False:')])
        self.assertTrue(GJ.marker_object_problems(bad))
        self.assertEqual(mutant.marker_object_problems(bad), [])


class TestRunnerMutations(unittest.TestCase):
    def guard(self, mod):
        g = mod.G1Guard()
        calls = {"fork": 0, "write": [], "wait": []}

        def fork():
            calls["fork"] += 1
            return 7000 + calls["fork"]

        def waitpid(pid, opts=0):
            calls["wait"].append(pid)
            return (pid, 0)

        def write(fd, data):
            calls["write"].append((fd, bytes(data)))
            return len(data)
        g.real = {"os.fork": fork, "os.waitpid": waitpid, "os.write": write, "os.close": lambda fd: None}
        return g, calls

    def test_a_guard_that_allows_a_second_fork(self):
        repl = [('if self.test is None or self.forks_this_test >= 1 or self.fork_calls >= self.max_forks or self.live_pid is not None:', 'if self.test is None:')]
        for mod, expect_raise in ((R, True), (load_mutant("g1_run.py", repl), False)):
            g, calls = self.guard(mod)
            g.begin_test("T1_ABORT")
            g.fork()
            if expect_raise:
                with self.assertRaises(mod.GuardViolation):
                    g.fork()
            else:
                g.fork()
                self.assertEqual(calls["fork"], 2)

    def test_a_guard_that_lets_the_release_byte_through(self):
        repl = [('if b == b"R" and (fd == self.watch_fd or self._is_pipe(fd)):', 'if False:')]
        g, calls = self.guard(R)
        g.begin_test("T2_EOF")
        g.watch_fd = 7
        with self.assertRaises(R.GuardViolation):
            g.write(7, b"R")
        self.assertEqual(calls["write"], [])
        m = load_mutant("g1_run.py", repl)
        g2, calls2 = self.guard(m)
        g2.begin_test("T2_EOF")
        g2.watch_fd = 7
        g2.write(7, b"R")
        self.assertEqual(calls2["write"], [(7, b"R")])

    def test_a_guard_that_allows_waiting_for_any_child(self):
        repl = [('if not isinstance(pid, int) or pid <= 0 or pid != self.allowed_pid:', 'if False:')]
        g, calls = self.guard(R)
        g.begin_test("T1_ABORT")
        g.fork()
        with self.assertRaises(R.GuardViolation):
            g.waitpid(-1, 0)
        m = load_mutant("g1_run.py", repl)
        g2, calls2 = self.guard(m)
        g2.begin_test("T1_ABORT")
        g2.fork()
        g2.waitpid(-1, 0)
        self.assertEqual(calls2["wait"], [-1])

    def test_a_guard_that_does_not_record_the_close_of_the_gate(self):
        repl = [('if self.watch_fd is not None and fd == self.watch_fd:', 'if False:')]
        for mod, want in ((R, 1), (load_mutant("g1_run.py", repl), 0)):
            g, _ = self.guard(mod)
            g.begin_test("T2_EOF")
            g.watch_fd = 7
            g.close(7)
            self.assertEqual(len(g.gate_closes), want)

    def test_an_in_run_rule_that_ignores_the_exit_status(self):
        repl = [('if exit_status != scn["expected_exit"]:', 'if False:')]
        t = {"messages_received": 0, "first_action_mono": None, "ready_received": False, "cleanup": {"cleanup_ok": True}}
        self.assertFalse(R.in_run_assessment(t, {"expected_exit": 111}, 112, [], [])[0])
        self.assertTrue(load_mutant("g1_run.py", repl).in_run_assessment(t, {"expected_exit": 111}, 112, [], [])[0])

    def test_a_pipeline_whose_closure_returns_zero_for_every_verdict(self):
        repl = [('return s2["exit_code"]', 'return 0')]
        mod = load_mutant("g1_run.py", repl)
        ev = F.mutate(F.good_evidence(), **{"tests.T1_ABORT.reap.exit_status": 0})
        for m, want in ((R, 1), (mod, 0)):
            with tempfile.TemporaryDirectory() as d, mock.patch.object(G1A, "EVIDENCE_ROOT", d), contextlib.redirect_stderr(io.StringIO()):
                run_dir = os.path.join(d, F.RUN_ID)
                os.mkdir(run_dir)
                self.assertEqual(m.finalize(ev, F.RUN_ID, run_dir, CRIT, SHA), want)

    def test_a_main_that_lets_system_exit_through(self):
        repl = [('reason="unexpected SystemExit(%r)" % (e.code,))\n        return 3', 'reason="unexpected SystemExit(%r)" % (e.code,))\n        raise')]
        with contextlib.redirect_stderr(io.StringIO()):
            with mock.patch.object(R, "_main", side_effect=SystemExit(1)):
                self.assertEqual(R.main([]), 3)
            m = load_mutant("g1_run.py", repl)
            with mock.patch.object(m, "_main", side_effect=SystemExit(1)):
                with self.assertRaises(SystemExit):
                    m.main([])

    def test_all_runner_anchors_occur_exactly_once(self):
        src = open(os.path.join(G1A.HERE, "g1_run.py"), encoding="utf-8").read()
        for old in ('if self.test is None or self.forks_this_test >= 1 or self.fork_calls >= self.max_forks or self.live_pid is not None:',
                    'if b == b"R" and (fd == self.watch_fd or self._is_pipe(fd)):', 'if not isinstance(pid, int) or pid <= 0 or pid != self.allowed_pid:',
                    'if self.watch_fd is not None and fd == self.watch_fd:', 'if exit_status != scn["expected_exit"]:', 'return s2["exit_code"]',
                    'reason="unexpected SystemExit(%r)" % (e.code,))\n        return 3'):
            self.assertEqual(src.count(old), 1, old)


if __name__ == "__main__":
    unittest.main(verbosity=2)
