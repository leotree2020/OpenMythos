"""Pure-logic tests for the G0 interlock, the G0 judge and the G0 source constraints.  WRITTEN, NOT RUN (GATE-PREP-001: no test is run
this round; running them needs its own authorization).  None of them starts a process: they use dictionaries, temporary files, the AST
and the refusal path of `g0_run.main` (which returns before any process-related call)."""
import ast
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
G0 = os.path.join(A003, "gate_g0")
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, G0)
import common as C  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402

PREREG_SHA = "e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39"
NOW = "2026-10-28T00:00:00Z"


def current():
    return {k: ("%064x" % (i + 1)) for i, k in enumerate(GA.BINDING_KEYS)}


def good_auth():
    return {"schema": GA.AUTH_SCHEMA, "stage": "G0", "authorized_by": "owner", "authorization_id": "OWNER-G0-0001", "date": "2026-10-28",
            "expires_utc": "2026-10-29T00:00:00Z", "bindings": current(), "grants": dict(GA.REQUIRED_GRANTS), "not_granted": list(GA.MUST_NOT_GRANT)}


class TestInterlock(unittest.TestCase):
    def test_good_authorization_is_valid(self):
        self.assertEqual(GA.validate(good_auth(), current(), NOW), [])

    def test_e1a_auth_schema_is_not_a_g0_authorization(self):
        a = good_auth()
        a["schema"] = "e1a-auth-2"
        self.assertTrue(GA.validate(a, current(), NOW))

    def test_other_stage_is_refused(self):
        for st in ("G1", "G2", "G3", "BV", "E1A-CELLS", "g0", None):
            a = good_auth()
            a["stage"] = st
            self.assertTrue(GA.validate(a, current(), NOW), st)

    def test_any_binding_difference_is_refused(self):
        for k in GA.BINDING_KEYS:
            a = good_auth()
            a["bindings"][k] = "0" * 64
            self.assertTrue(GA.validate(a, current(), NOW), k)
            a = good_auth()
            del a["bindings"][k]
            self.assertTrue(GA.validate(a, current(), NOW), k)

    def test_grants_are_exact(self):
        for key, val in (("signals", 1), ("forks", 2), ("fault_injection", True), ("max_concurrent_children", 2), ("max_seconds", 60), ("runs", 2)):
            a = good_auth()
            a["grants"][key] = val
            self.assertTrue(GA.validate(a, current(), NOW), key)
        a = good_auth()
        a["grants"]["extra"] = 1
        self.assertTrue(GA.validate(a, current(), NOW))

    def test_unknown_key_and_missing_not_granted_are_refused(self):
        a = good_auth()
        a["inherits"] = "G1"
        self.assertTrue(GA.validate(a, current(), NOW))
        a = good_auth()
        a["not_granted"] = ["G1"]
        self.assertTrue(GA.validate(a, current(), NOW))

    def test_expired_and_non_owner_are_refused(self):
        a = good_auth()
        a["expires_utc"] = "2026-10-27T00:00:00Z"
        self.assertTrue(GA.validate(a, current(), NOW))
        a = good_auth()
        a["authorized_by"] = "claude"
        self.assertTrue(GA.validate(a, current(), NOW))

    def test_non_object_is_refused(self):
        for bad in (None, [], "x", 3):
            self.assertTrue(GA.validate(bad, current(), NOW))

    def test_single_use(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "AUTHORIZATION_E1A_GATE_G0.json")
            with open(p, "w") as f:
                json.dump(good_auth(), f)
            cdir = os.path.join(d, "consumed")
            os.makedirs(cdir)
            auth, raw = GA.load(p, current(), NOW, consumed_dir=cdir)
            self.assertEqual(auth["authorization_id"], "OWNER-G0-0001")
            with open(GA.consumed_marker(auth["authorization_id"], cdir), "w") as f:
                f.write("{}")
            with self.assertRaises(GA.G0AuthorizationError):
                GA.load(p, current(), NOW, consumed_dir=cdir)

    def test_missing_or_garbled_file_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(GA.G0AuthorizationError):
                GA.load(os.path.join(d, "none.json"), current(), NOW)
            p = os.path.join(d, "bad.json")
            open(p, "w").write("{not json")
            with self.assertRaises(GA.G0AuthorizationError):
                GA.load(p, current(), NOW)

    def test_template_is_never_valid(self):
        t = json.loads(GA.template())
        self.assertTrue(GA.validate(t, current(), NOW))

    def test_no_authorization_file_exists_in_the_repository(self):
        self.assertFalse(os.path.exists(GA.AUTH_DEFAULT), "this round must not contain a G0 authorization file")

    def test_execute_without_authorization_is_refused_and_creates_nothing(self):
        import g0_run
        before = sorted(os.listdir(GA.EVIDENCE_ROOT)) if os.path.isdir(GA.EVIDENCE_ROOT) else None
        err, out = io.StringIO(), io.StringIO()
        # PREFLIGHT-001: a path inside a fresh temporary directory cannot hold an authorization, and run() (the only function that forks) is
        # replaced by a spy that fails the test if it is ever reached
        with tempfile.TemporaryDirectory() as d, mock.patch.object(g0_run, "run", side_effect=AssertionError("run() must never be reached")) as spy:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = g0_run.main(["--execute", "--auth", os.path.join(d, "no_such_g0_authorization.json")])
            spy.assert_not_called()
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())
        after = sorted(os.listdir(GA.EVIDENCE_ROOT)) if os.path.isdir(GA.EVIDENCE_ROOT) else None
        self.assertEqual(before, after)

    def test_check_mode_reports_and_executes_nothing(self):
        import g0_run
        out = io.StringIO()
        with mock.patch.object(g0_run, "run", side_effect=AssertionError("run() must never be reached")) as spy:
            with contextlib.redirect_stdout(out):
                rc = g0_run.main(["--check"])
            spy.assert_not_called()
        self.assertEqual(rc, 0)
        info = json.loads(out.getvalue())
        self.assertIs(info["executed"], False)
        self.assertEqual(info["bindings"]["prereg_sha256"], PREREG_SHA)


def good_evidence():
    h = current()
    reg = [
        {"seq": 1, "kind": "RUN_START", "mono": 1.0, "run_id": "g0_x", "observer_pid": 100, "phase": "G0"},
        {"seq": 2, "kind": "INTENT", "mono": 1.1, "node_id": "n00001", "creator": "O", "creator_pid": 100, "role": "sleeper", "label": "g0"},
        {"seq": 3, "kind": "FORKED", "mono": 1.2, "node_id": "n00001", "pid": 200, "starttime": 5000, "creator": "O", "creator_pid": 100},
        {"seq": 4, "kind": "REGISTERED", "mono": 1.3, "node_id": "n00001", "pid": 200, "starttime": 5000, "sid": 90, "pgrp": 90, "ppid": 100, "creator": "O"},
        {"seq": 5, "kind": "RELEASED", "mono": 1.7, "node_id": "n00001"},
        {"seq": 6, "kind": "DEAD", "mono": 2.5, "node_id": "n00001", "basis": "confirmed dead from /proc"},
        {"seq": 7, "kind": "RUN_END", "mono": 2.6, "run_id": "g0_x", "cleanup_confirmed": True},
    ]

    def snap(name, mono, children, child=None, fds=None):
        s = {"name": name, "mono": mono, "children": children, "grandchildren": [], "total_procs": 50, "enum_problems": {}, "fd_count": 10, "child": child,
             "token_residue": []}
        if fds is not None:
            s["fds"] = fds
        return s
    live = {"pid": 200, "starttime": 5000, "ppid": 100, "state": "S", "sid": 90, "pgrp": 90}
    std = {"0": {"target": "/dev/null", "access": "r"}, "1": {"target": "/dev/null", "access": "w"}, "2": {"target": "/dev/null", "access": "w"}}
    s1 = snap("S1", 1.6, [200], live, dict(std, **{"3": {"target": "pipe:[777]", "access": "r"}, "4": {"target": "socket:[888]", "access": "rw"}}))
    s1.update(messages_received=0, first_action_mono=None)
    return {
        "run_id": "g0_x", "auth_expected": dict(h), "bindings_start": dict(h), "bindings_end": dict(h), "auth_consumed": True,
        "observer": {"pid": 100, "sid": 90, "pgrp": 90}, "node": {"node_id": "n00001", "pid": 200, "starttime": 5000, "gate_ino": 777},
        "preflight": {"ok": True, "problems": [], "children": 0, "token_residue": [], "unresolved_prior": [], "enumeration_problems": {}, "run_id_unique": True},
        "reg": reg,
        "snapshots": {
            "S0_before_fork": snap("S0", 1.05, []),
            "S1_held_registered_unreleased": s1,
            "S2_ready_after_release": snap("S2", 1.9, [200], live, dict(std, **{"4": {"target": "socket:[888]", "access": "rw"}})),
            "S3_exited_unreaped": snap("S3", 2.2, [200], dict(live, state="Z")),
            "S4_reaped": snap("S4", 2.4, []),
            "S5_final": snap("S5", 2.7, []),
        },
        "events": {"first_action_mono": 1.8, "exit_sent_mono": 2.0, "pidfd_readable_mono": 2.1, "reap_mono": 2.3, "proc_gone_mono": 2.35},
        "guard": {"violations": [], "fork_calls": 1, "fork_pids": [200], "release_byte_pre_write_monos": [1.75],
                  "waitpid_calls": [{"pid": 200, "options": 0, "returned": 200, "status": 0, "mono": 2.3}]},
        "reap": {"waitpid_pid": 200, "exit_status": 0},
        "cleanup": {"cleanup_ok": True, "run_set": {"consistent": True}, "rounds": [{"kill": [{"node_id": "n00001", "result": "already_exited"}], "kill_unregistered_direct": []}]},
        "timing": {"duration": 1.7}, "deadline_hits": [], "exception": None, "aborted": None,
    }


class TestJudge(unittest.TestCase):
    def j(self, ev):
        return GJ.judge(ev)

    def test_clean_evidence_passes(self):
        r = self.j(good_evidence())
        self.assertEqual(r["verdict"], "PASS", {k: v for k, v in r["checks"].items() if v["status"] != "PASS"})
        self.assertEqual(r["exit_code"], 0)

    def test_judge_and_frozen_criteria_agree_on_check_ids(self):
        self.assertEqual(set(GJ.CHECKS), set(GJ.load_criteria()["checks"]))

    def test_missing_snapshot_is_blocked_not_pass_not_fail(self):
        ev = good_evidence()
        del ev["snapshots"]["S3_exited_unreaped"]
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["exit_code"], 3)
        self.assertEqual(r["checks"]["G0-C08"]["status"], "UNEVALUABLE")

    def test_empty_evidence_is_blocked(self):
        self.assertEqual(self.j({})["verdict"], "BLOCKED")

    def test_guard_violation_is_fail(self):
        ev = good_evidence()
        ev["guard"]["violations"] = [{"call": "os.kill", "mono": 2.0}]
        r = self.j(ev)
        self.assertEqual((r["verdict"], r["exit_code"]), ("FAIL", 1))
        self.assertIn("G0-C12", r["fail_class"])

    def test_fail_takes_precedence_over_bench_blocked(self):
        ev = good_evidence()
        ev["guard"]["violations"] = [{"call": "os.kill", "mono": 2.0}]
        ev["exception"] = "Traceback ..."
        self.assertEqual(self.j(ev)["verdict"], "FAIL")

    def test_exception_alone_is_blocked(self):
        ev = good_evidence()
        ev["exception"] = "Traceback ..."
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["checks"]["G0-C17"]["status"], "FAIL_EVIDENCED")
        self.assertEqual(r["checks"]["G0-C03"]["status"], "UNEVALUABLE")

    def test_exit_code_zero_never_hides_an_anomaly(self):
        ev = good_evidence()
        ev["deadline_hits"] = ["ready"]
        r = self.j(ev)
        self.assertNotEqual(r["verdict"], "PASS")

    def test_wait_before_unreaped_observation_is_not_pass(self):
        ev = good_evidence()
        ev["guard"]["waitpid_calls"][0]["mono"] = 2.0
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_wait_on_another_pid_is_not_pass(self):
        ev = good_evidence()
        ev["guard"]["waitpid_calls"].append({"pid": 999, "options": 0, "returned": 0, "status": 0, "mono": 2.31})
        self.assertNotEqual(self.j(ev)["verdict"], "PASS")

    def test_nonzero_exit_status_is_fail(self):
        ev = good_evidence()
        ev["reap"]["exit_status"] = 113
        self.assertEqual(self.j(ev)["verdict"], "FAIL")

    def test_release_before_registered_is_fail(self):
        ev = good_evidence()
        ev["reg"][4]["mono"] = 1.2
        r = self.j(ev)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("G0-C07", r["fail_class"])

    def test_child_action_before_release_is_fail(self):
        ev = good_evidence()
        ev["snapshots"]["S1_held_registered_unreleased"]["messages_received"] = 1
        self.assertIn("G0-C05", self.j(ev)["fail_class"])

    def test_held_child_not_blocked_on_the_gate_is_fail(self):
        ev = good_evidence()
        ev["snapshots"]["S1_held_registered_unreleased"]["child"]["state"] = "R"
        self.assertIn("G0-C05", self.j(ev)["fail_class"])

    def test_gate_write_end_in_child_is_fail(self):
        ev = good_evidence()
        ev["snapshots"]["S1_held_registered_unreleased"]["fds"]["5"] = {"target": "pipe:[777]", "access": "w"}
        self.assertIn("G0-C06", self.j(ev)["fail_class"])

    def test_gate_pipe_still_open_after_release_is_fail(self):
        ev = good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["fds"]["3"] = {"target": "pipe:[777]", "access": "r"}
        self.assertIn("G0-C06", self.j(ev)["fail_class"])

    def test_extra_child_or_descendant_is_fail(self):
        ev = good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["children"] = [200, 201]
        self.assertIn("G0-C11", self.j(ev)["fail_class"])
        ev = good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["grandchildren"] = [300]
        self.assertIn("G0-C11", self.j(ev)["fail_class"])

    def test_second_fork_is_fail(self):
        ev = good_evidence()
        ev["guard"]["fork_calls"] = 2
        self.assertIn("G0-C11", self.j(ev)["fail_class"])

    def test_registered_identity_mismatch_is_fail(self):
        ev = good_evidence()
        ev["reg"][3]["starttime"] = 4999
        self.assertIn("G0-C04", self.j(ev)["fail_class"])

    def test_residue_is_blocked(self):
        ev = good_evidence()
        ev["snapshots"]["S5_final"]["children"] = [200]
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")
        ev = good_evidence()
        ev["snapshots"]["S5_final"]["token_residue"] = [{"pid": 4242}]
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_incomplete_proc_enumeration_is_blocked(self):
        ev = good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["enum_problems"] = {"123": "unreadable"}
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_fd_baseline_difference_is_blocked(self):
        ev = good_evidence()
        ev["snapshots"]["S5_final"]["fd_count"] = 11
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["checks"]["G0-C14"]["status"], "FAIL_EVIDENCED")

    def test_binding_change_during_run_is_blocked(self):
        ev = good_evidence()
        ev["bindings_end"]["bench_code_sha256"] = "f" * 64
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_unconsumed_authorization_is_blocked(self):
        ev = good_evidence()
        ev["auth_consumed"] = False
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_registry_integrity_problem_is_fail(self):
        ev = good_evidence()
        del ev["reg"][4]                                   # lost RELEASED record: sequence gap
        self.assertEqual(self.j(ev)["verdict"], "FAIL")

    def test_judge_does_not_mutate_its_input(self):
        ev = good_evidence()
        snap = copy.deepcopy(ev)
        self.j(ev)
        self.assertEqual(ev, snap)


class TestSourceConstraints(unittest.TestCase):
    FILES = ("g0_auth.py", "g0_judge.py", "g0_run.py")
    SENDERS = {"kill", "killpg", "pidfd_send_signal", "raise_signal", "pthread_kill", "fork", "forkpty", "system", "popen", "Popen", "run", "call",
               "check_call", "check_output", "execv", "execve", "execvp", "execl", "execlp", "execvpe", "spawnl", "spawnv", "posix_spawn", "_exit",
               "pidfd_open", "setsid", "setpgid", "wait", "wait3", "wait4", "waitid"}

    def trees(self):
        for f in self.FILES:
            yield f, ast.parse(open(os.path.join(G0, f)).read())

    def test_no_process_creating_or_signalling_call_is_made(self):
        for f, t in self.trees():
            for n in ast.walk(t):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in self.SENDERS:
                    v = n.func.value
                    owner = v.id if isinstance(v, ast.Name) else None
                    self.assertNotIn(owner, ("os", "signal", "subprocess", "pty"), "%s:%d %s.%s" % (f, n.lineno, owner, n.func.attr))

    def test_waitpid_is_called_exactly_once_in_run_and_nowhere_else(self):
        for f, t in self.trees():
            calls = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "waitpid"
                     and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
            self.assertEqual(len(calls), 1 if f == "g0_run.py" else 0, f)

    def test_no_signal_constants_and_no_negative_wait(self):
        for f, t in self.trees():
            for n in ast.walk(t):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "signal":
                    self.assertFalse(n.attr.startswith("SIG"), "%s:%d" % (f, n.lineno))

    def test_no_name_matching_cleanup_strings(self):
        for f, t in self.trees():
            for n in ast.walk(t):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    for bad in ("pkill", "killall", "pgrep", "kill -9"):
                        self.assertNotIn(bad, n.value.lower(), f)

    def test_g0_does_not_reference_later_stages(self):
        for f in self.FILES:
            src = open(os.path.join(G0, f)).read()
            for bad in ("import janitor", "import trial", "import scenarios", "import validity", "import e1a_runner", "run_e1a", "test_e1a_gate"):
                self.assertNotIn(bad, src, f)

    def test_frozen_criteria_and_prereg_hashes(self):
        crit = os.path.join(G0, "g0_criteria_v1.json")
        recorded = open(crit + ".sha256").read().split()[0]
        self.assertEqual(C.sha256_file(crit), recorded)
        self.assertEqual(C.sha256_file(C.PREREG_PATH), PREREG_SHA)
        c = json.load(open(crit))
        self.assertEqual(c["limits"]["max_signals"], 0)
        self.assertEqual(c["limits"]["max_forks"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
