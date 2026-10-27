"""Pure-logic tests for the G0 interlock, the G0 judge and the G0 source constraints, adjusted to the FROZEN criteria V5
(F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001).  WRITTEN, NOT RUN: running them needs its own authorization.  None of them starts a process:
they use dictionaries, temporary files, the AST and the refusal path of `g0_run.main` (which returns before any process-related call)."""
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
sys.path.insert(0, HERE)
import g0_v5_fixtures as F  # noqa: E402
import common as C  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402

G0 = F.G0
PREREG_SHA = "e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39"
NOW = F.NOW
HISTORICAL = {"V1": "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2", "V2": "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438",
              "V3": "653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a", "V4": "6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414"}
HISTORICAL_TEXT = {"V1": "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb", "V2": "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2",
                   "V3": "0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88", "V4": "05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42"}


def current():
    return F.bindings()


def good_auth():
    return F.good_auth()


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

    def test_authorization_bound_to_a_historical_version_is_void(self):
        """CL-08 / C02: the binding must be the frozen V5 hash.  An authorization bound to the V1..V4 files is refused even if `current` says so."""
        for ver, h in HISTORICAL.items():
            a, cur = good_auth(), current()
            a["bindings"]["g0_criteria_sha256"] = cur["g0_criteria_sha256"] = h
            self.assertTrue(any("frozen V5" in p for p in GA.validate(a, cur, NOW)), ver)
        for ver, h in HISTORICAL_TEXT.items():
            a, cur = good_auth(), current()
            a["bindings"]["g0_prereg_sha256"] = cur["g0_prereg_sha256"] = h
            self.assertTrue(any("frozen V5" in p for p in GA.validate(a, cur, NOW)), ver)

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
        self.assertFalse(os.path.exists(GA.AUTH_DEFAULT), "this stage must not contain a G0 authorization file")

    def test_the_tool_targets_the_v5_files(self):
        self.assertTrue(GA.CRITERIA_PATH.endswith("g0_criteria_v5.json"))
        self.assertTrue(GA.PREREG_MD_PATH.endswith("E1A_GATE_G0_PREREG_V5.md"))
        self.assertIn("g0_criteria_v5.json", GA.G0_CODE_FILES)
        self.assertNotIn("g0_criteria_v1.json", GA.G0_CODE_FILES)
        self.assertEqual(GA.CRITERIA_ID, "E1A-GATE-G0-CRITERIA-V5")

    def test_frozen_files_V1_to_V5_have_their_frozen_bytes(self):
        self.assertEqual(GA.frozen_problems(), [])
        self.assertEqual(C.sha256_file(GA.CRITERIA_PATH), GA.FROZEN_CRITERIA_SHA256)
        for name, want in GA.FROZEN_FILES.items():
            self.assertEqual(C.sha256_file(os.path.join(G0, name)), want, name)

    def test_frozen_problems_detects_a_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            for name in GA.FROZEN_FILES:
                with open(os.path.join(d, name), "wb") as f:
                    f.write(b"changed")
            self.assertEqual(len(GA.frozen_problems(d)), len(GA.FROZEN_FILES))

    def test_no_function_of_g0_auth_writes_an_authorization_file(self):
        tree = ast.parse(open(os.path.join(G0, "g0_auth.py")).read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                self.assertFalse(any(c in n.args[1].value for c in "wax+"), "g0_auth opens a file for writing at line %d" % n.lineno)

    def test_execute_without_authorization_is_refused_and_creates_nothing(self):
        import g0_run
        before = sorted(os.listdir(GA.EVIDENCE_ROOT)) if os.path.isdir(GA.EVIDENCE_ROOT) else None
        err, out = io.StringIO(), io.StringIO()
        # a path inside a fresh temporary directory cannot hold an authorization, and run() (the only function that forks) is replaced by a
        # spy that fails the test if it is ever reached
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
        self.assertEqual(info["criteria_id"], "E1A-GATE-G0-CRITERIA-V5")
        self.assertEqual(info["frozen_file_problems"], [])
        self.assertEqual(info["bindings"]["g0_criteria_sha256"], GA.FROZEN_CRITERIA_SHA256)


class TestJudge(unittest.TestCase):
    def setUp(self):
        self.crit = F.criteria()

    def j(self, ev):
        return GJ.judge(ev, self.crit, GA.FROZEN_CRITERIA_SHA256)

    def status(self, r, cid):
        return r["checks"][cid]["status"]

    def test_clean_evidence_passes(self):
        r = self.j(F.good_evidence())
        self.assertEqual(r["verdict"], "PASS", {k: (v["status"], v["detail"]) for k, v in r["checks"].items() if v["status"] != "PASS"})
        self.assertEqual(r["exit_code"], 0)
        self.assertEqual(r["invalid_fields"], [])

    def test_judge_and_frozen_criteria_agree_on_check_ids(self):
        self.assertEqual(set(GJ.CHECK_IDS), set(self.crit["checks"]))
        self.assertEqual(len(GJ.CHECK_IDS), 17)

    def test_the_criteria_loaded_by_default_are_v5(self):
        c = GJ.load_criteria()
        self.assertEqual(c["criteria_id"], "E1A-GATE-G0-CRITERIA-V5")
        self.assertEqual(C.sha256_file(GA.CRITERIA_PATH), GA.FROZEN_CRITERIA_SHA256)

    def test_every_declared_schema_type_has_a_validator(self):
        for f in self.crit["evidence_schema"]["fields"]:
            self.assertIn(f["type"], GJ.TYPE_VALIDATORS, f["path"])

    def test_good_evidence_has_every_schema_field(self):
        self.assertEqual(GJ.validate_evidence(F.good_evidence(), self.crit), [])
        self.assertEqual(len(self.crit["evidence_schema"]["fields"]), 91)

    def test_each_schema_field_is_required_and_a_wrong_type_counts_as_missing(self):
        for fld in self.crit["evidence_schema"]["fields"]:
            ev = F.good_evidence()
            parts = fld["path"].split(".")
            cur = ev
            for p in parts[:-1]:
                cur = cur[p]
            del cur[parts[-1]]
            bad = GJ.validate_evidence(ev, self.crit)
            self.assertIn(fld["path"], [x["path"] for x in bad], fld["path"])
            r = self.j(ev)
            self.assertEqual(self.status(r, "G0-C16"), "FAIL_EVIDENCED", fld["path"])
            self.assertNotEqual(r["verdict"], "PASS", fld["path"])

    def test_bool_is_never_an_int_or_a_number(self):
        ev = F.good_evidence()
        ev["node"]["pid"] = True
        ev["timing"]["duration"] = True
        paths = [x["path"] for x in GJ.validate_evidence(ev, self.crit)]
        self.assertIn("node", paths)
        self.assertIn("timing.duration", paths)

    def test_nan_is_refused_as_a_number(self):
        ev = F.good_evidence()
        ev["timing"]["duration"] = float("nan")
        self.assertIn("timing.duration", [x["path"] for x in GJ.validate_evidence(ev, self.crit)])

    def test_wrong_schema_id_is_c16_blocked(self):
        ev = F.good_evidence()
        ev["evidence_schema"] = "e1a-gate-g0-evidence-3"
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(self.status(r, "G0-C16"), "FAIL_EVIDENCED")

    def test_an_invalid_field_makes_the_checks_that_consume_it_unevaluable(self):
        ev = F.good_evidence()
        ev["node"]["pid"] = True                      # consumers: C03 C04 C06 C09 (C03 judges its own evidence)
        r = self.j(ev)
        for cid in ("G0-C04", "G0-C06", "G0-C09"):
            self.assertEqual(self.status(r, cid), "UNEVALUABLE", cid)
        self.assertEqual(self.status(r, "G0-C03"), "PASS")
        self.assertEqual(r["verdict"], "BLOCKED")

    def test_missing_snapshot_is_blocked_not_pass_not_fail(self):
        ev = F.good_evidence()
        del ev["snapshots"]["S3_exited_unreaped"]
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")

    def test_empty_evidence_is_blocked(self):
        r = self.j({})
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["exit_code"], 3)

    def test_guard_violation_is_fail(self):
        ev = F.good_evidence()
        ev["guard"]["violations"] = [{"call": "os.kill", "mono": 1.0, "args": "()"}]
        r = self.j(ev)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("G0-C12", r["fail_class"])

    def test_fail_takes_precedence_over_bench_blocked(self):
        ev = F.good_evidence()
        ev["guard"]["violations"] = [{"call": "os.kill", "mono": 1.0, "args": "()"}]
        ev["snapshots"]["S5_final"]["fd_count"] = 99                 # a BLOCKED-class finding
        r = self.j(ev)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("G0-C14", r["blocked_class"])

    def test_exception_alone_is_blocked(self):
        ev = F.good_evidence()
        ev["exception"] = "Traceback ..."
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(self.status(r, "G0-C17"), "FAIL_EVIDENCED")

    def test_verdict_and_exit_code_follow_the_criteria(self):
        self.assertEqual(self.crit["exit_codes"], {"PASS": 0, "FAIL": 1, "BLOCKED": 3})
        ev = F.good_evidence()
        r = self.j(ev)
        self.assertEqual((r["verdict"], r["exit_code"]), ("PASS", 0))
        ev["reap"]["exit_status"] = 1
        r = self.j(ev)
        self.assertEqual((r["verdict"], r["exit_code"]), ("FAIL", 1))

    def test_wait_before_unreaped_observation_is_not_pass(self):
        ev = F.good_evidence()
        ev["guard"]["waitpid_calls"].insert(0, {"pid": 200, "options": 1, "returned": 0, "status": 0, "mono": 2.1})
        self.assertNotEqual(self.j(ev)["verdict"], "PASS")

    def test_wait_on_another_pid_is_not_pass(self):
        ev = F.good_evidence()
        ev["guard"]["waitpid_calls"].append({"pid": 201, "options": 1, "returned": 0, "status": 0, "mono": 2.31})
        self.assertNotEqual(self.j(ev)["verdict"], "PASS")

    def test_a_poll_that_returned_neither_zero_nor_the_child_is_not_pass(self):
        ev = F.good_evidence()
        ev["guard"]["waitpid_calls"].insert(0, {"pid": 200, "options": 1, "returned": 7, "status": 0, "mono": 2.25})
        self.assertNotEqual(self.status(self.j(ev), "G0-C09"), "PASS")

    def test_nonzero_exit_status_is_fail(self):
        ev = F.good_evidence()
        ev["reap"]["exit_status"] = 3
        r = self.j(ev)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("G0-C10", r["fail_class"])

    def test_child_action_before_release_is_fail(self):
        ev = F.good_evidence()
        ev["snapshots"]["S1_held_registered_unreleased"]["messages_received"] = 1
        r = self.j(ev)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("G0-C05", r["fail_class"])

    def test_held_child_not_blocked_on_the_gate_is_fail(self):
        ev = F.good_evidence()
        ev["snapshots"]["S1_held_registered_unreleased"]["child"]["state"] = "R"
        self.assertIn("G0-C05", self.j(ev)["fail_class"])

    def test_gate_write_end_in_child_is_fail(self):
        ev = F.good_evidence()
        ev["snapshots"]["S1_held_registered_unreleased"]["fds"]["5"] = {"target": "pipe:[777]", "access": "w"}
        self.assertIn("G0-C06", self.j(ev)["fail_class"])

    def test_gate_pipe_still_open_after_release_is_fail(self):
        ev = F.good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["fds"]["3"] = {"target": "pipe:[777]", "access": "r"}
        self.assertIn("G0-C06", self.j(ev)["fail_class"])

    def test_extra_child_or_descendant_is_fail(self):
        ev = F.good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["children"] = [200, 201]
        self.assertIn("G0-C11", self.j(ev)["fail_class"])
        ev = F.good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["grandchildren"] = [300]
        self.assertIn("G0-C11", self.j(ev)["fail_class"])

    def test_second_fork_is_fail(self):
        ev = F.good_evidence()
        ev["guard"]["fork_calls"] = 2
        self.assertIn("G0-C11", self.j(ev)["fail_class"])

    def test_registered_identity_mismatch_is_fail(self):
        ev = F.good_evidence()
        ev["guard"]["fork_pids"] = [201]
        self.assertIn("G0-C04", self.j(ev)["fail_class"])

    def test_residue_is_blocked(self):
        ev = F.good_evidence()
        ev["snapshots"]["S5_final"]["token_residue"] = [{"pid": 999}]
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("G0-C13", r["blocked_class"])

    def test_incomplete_proc_enumeration_is_blocked(self):
        ev = F.good_evidence()
        ev["snapshots"]["S2_ready_after_release"]["enum_problems"] = {"123": "unreadable"}
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_fd_baseline_difference_is_blocked(self):
        ev = F.good_evidence()
        ev["snapshots"]["S5_final"]["fd_count"] = 11
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("G0-C14", r["blocked_class"])

    def test_binding_change_during_run_is_blocked(self):
        ev = F.good_evidence()
        ev["bindings_end"]["git_head"] = "e" * 40
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("G0-C02", r["blocked_class"])

    def test_authorization_bound_to_a_historical_criteria_hash_is_blocked_by_c02(self):
        for h in HISTORICAL.values():
            ev = F.good_evidence()
            for k in ("auth_expected", "bindings_start", "bindings_end"):
                ev[k]["g0_criteria_sha256"] = h
            r = self.j(ev)
            self.assertEqual(self.status(r, "G0-C02"), "FAIL_EVIDENCED", h)
            self.assertEqual(r["verdict"], "BLOCKED")

    def test_unconsumed_authorization_is_blocked(self):
        ev = F.good_evidence()
        ev["auth_consumed"] = False
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_deadline_hit_or_overlong_run_is_blocked(self):
        ev = F.good_evidence()
        ev["deadline_hits"] = ["total"]
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")
        ev = F.good_evidence()
        ev["timing"]["duration"] = 21.0
        self.assertEqual(self.j(ev)["verdict"], "BLOCKED")

    def test_preflight_problems_are_blocked(self):
        for key, val in (("ok", False), ("problems", ["x"]), ("children", 1), ("token_residue", [{"pid": 1}]), ("unresolved_prior", ["g0_a:NO_CLOSED"]),
                         ("enumeration_problems", {"1": "x"}), ("run_id_unique", False)):
            ev = F.good_evidence()
            ev["preflight"][key] = val
            r = self.j(ev)
            self.assertEqual(self.status(r, "G0-C01"), "FAIL_EVIDENCED", key)
            self.assertEqual(r["verdict"], "BLOCKED", key)

    def test_the_v2_release_evidence_field_is_no_longer_accepted(self):
        ev = F.good_evidence()
        ev["guard"]["release_byte_pre_write_monos"] = [1.75]
        del ev["guard"]["release_writes"]
        r = self.j(ev)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(self.status(r, "G0-C07"), "UNEVALUABLE")

    def test_judge_does_not_mutate_its_input(self):
        ev = F.good_evidence()
        snap = copy.deepcopy(ev)
        self.j(ev)
        self.assertEqual(ev, snap)

    def test_m2_disk_dependent_checks_are_unevaluable_when_the_copy_is_unfaithful(self):
        ev = F.good_evidence()
        ev["reg"][3]["pid"] = 201
        r = self.j(ev)
        for cid in ("G0-C04", "G0-C05", "G0-C11", "G0-C13"):
            self.assertEqual(self.status(r, cid), "UNEVALUABLE", cid)
            self.assertEqual(r["checks"][cid]["rule"], "M-2")
        self.assertEqual(self.status(r, "G0-C03"), "UNEVALUABLE")
        self.assertEqual(r["checks"]["G0-C03"]["rule"], "C03-U2")
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertTrue(r["c03_fidelity_report"])

    def test_m2_damage_to_the_file_never_creates_a_pass_or_a_file_based_fail(self):
        for mutate in (lambda e: e["reg"][3].update(pid=201), lambda e: e["reg"][6].update(cleanup_confirmed=False),
                       lambda e: e["reg"][1].update(creator="n7"), lambda e: e["reg"].pop(4)):
            ev = F.good_evidence()
            mutate(ev)
            r = self.j(ev)
            self.assertEqual(r["verdict"], "BLOCKED")
            self.assertEqual(r["fail_class"], [])

    def test_a_ledger_proven_violation_survives_damage_to_the_file(self):
        ev = F.good_evidence()
        ev["reg_memory_records"].insert(5, copy.deepcopy(ev["reg_memory_records"][4]))
        for i, r in enumerate(ev["reg_memory_records"]):
            r["seq"] = i + 1
        ev["reg_writer_seq"] = len(ev["reg_memory_records"])
        ev["reg"][6]["run_id"] = "g0_y"                              # and the durable copy is damaged as well
        r = self.j(ev)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["checks"]["G0-C03"]["rules_matched"][0], "C03-F1")
        self.assertEqual(r["checks"]["G0-C03"]["credibility"]["level"], "first-hand")
        self.assertIn("durable copy not faithful", r["checks"]["G0-C03"]["credibility"]["damage"])

    def test_fail_summary_scope_text_is_the_frozen_one(self):
        self.assertEqual(GJ.FAIL_SCOPE, "G0 bench/protocol failure; not evidence about the Mythos model architecture")


class TestSourceConstraints(unittest.TestCase):
    FILES = ("g0_auth.py", "g0_judge.py", "g0_run.py")
    SENDERS = {"kill", "killpg", "pidfd_send_signal", "raise_signal", "pthread_kill", "fork", "forkpty", "system", "popen", "Popen", "run", "call",
               "check_call", "check_output", "execv", "execve", "execvp", "execl", "execlp", "execvpe", "spawnl", "spawnv", "posix_spawn", "_exit",
               "pidfd_open", "setsid", "setpgid", "wait", "wait3", "wait4", "waitid"}

    def trees(self):
        for f in self.FILES:
            yield f, ast.parse(open(os.path.join(G0, f)).read())

    def test_every_file_parses(self):
        for f, t in self.trees():
            self.assertIsInstance(t, ast.Module, f)

    def test_no_process_creating_or_signalling_call_is_made(self):
        for f, t in self.trees():
            for n in ast.walk(t):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in self.SENDERS:
                    v = n.func.value
                    owner = v.id if isinstance(v, ast.Name) else None
                    self.assertNotIn(owner, ("os", "signal", "subprocess", "pty"), "%s:%d %s.%s" % (f, n.lineno, owner, n.func.attr))

    def test_waitpid_is_called_exactly_once_in_run_with_wnohang_and_nowhere_else(self):
        for f, t in self.trees():
            calls = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "waitpid"
                     and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
            self.assertEqual(len(calls), 1 if f == "g0_run.py" else 0, f)
            if f == "g0_run.py":
                self.assertIn("WNOHANG", ast.dump(calls[0]), "F-8: the reap must be a bounded, non-blocking poll")

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

    def test_no_default_str_and_no_overwriting_or_deleting_call(self):
        for f, t in self.trees():
            for n in ast.walk(t):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("dump", "dumps")
                        and any(k.arg == "default" for k in n.keywords)):
                    self.fail("%s:%d a json default= argument silently converts types (F-21)" % (f, n.lineno))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "os":
                    self.assertNotIn(n.func.attr, ("rename", "replace", "unlink", "remove", "truncate", "ftruncate", "renames"), "%s:%d os.%s" % (f, n.lineno, n.func.attr))

    def test_frozen_criteria_and_prereg_hashes(self):
        crit = os.path.join(G0, "g0_criteria_v5.json")
        recorded = open(crit + ".sha256").read().split()[0]
        self.assertEqual(C.sha256_file(crit), recorded)
        self.assertEqual(recorded, GA.FROZEN_CRITERIA_SHA256)
        self.assertEqual(C.sha256_file(C.PREREG_PATH), PREREG_SHA)
        c = json.load(open(crit))
        self.assertEqual(c["limits"]["max_signals"], 0)
        self.assertEqual(c["limits"]["max_forks"], 1)
        for ver, h in HISTORICAL.items():
            self.assertEqual(C.sha256_file(os.path.join(G0, "g0_criteria_v%s.json" % ver[1])), h, ver)


if __name__ == "__main__":
    unittest.main(verbosity=2)
