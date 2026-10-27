"""G1 boundary tests (CPU; WRITTEN, NOT RUN -- NOT TESTED): (1) an unexpected SystemExit or exception anywhere after the command line was parsed is a start-up
error, exit code 3 -- never 1 (FAIL) and never 0 (PASS); argparse keeps 0 (--help) and 2 (usage); refusals are 2; the saved verdict code of finalize is passed
through unchanged; (2) AST checks of the safety boundary of the three G1 modules: no signal / exec / spawn / wait call except the one waitpid of the child
pid, no release of a gate, no use of Observer._confirmed_dead() or the SIGKILL cleanup of the old unittest, no overwrite.  No process is started."""
import ast
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_fixtures as F  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_run as R  # noqa: E402

SRC = {n: open(os.path.join(G1A.HERE, n + ".py"), encoding="utf-8").read() for n in ("g1_auth", "g1_judge", "g1_run")}
ARGV = ["--execute", "--auth", "/nonexistent/auth.json", "--run-id", "g1_test_start"]
EXITS = (1, "text", True, False, 0, None, 2, 3, -1)


def base_patches():
    return {(R, "current"): mock.Mock(return_value=F.bindings()), (G1A, "frozen_problems"): mock.Mock(return_value=[]),
            (G1A, "load"): mock.Mock(return_value=({"authorization_id": "OWNER-G1-TEST-0001", "bindings": F.bindings()}, b"{}")),
            (R, "safe_preflight"): mock.Mock(return_value={"ok": True}), (R, "prepare_dirs"): mock.Mock(return_value=({}, {}, {})),
            (R, "run"): mock.Mock(return_value=F.good_evidence()), (R, "finalize"): mock.Mock(return_value=0), (R.GR, "ancestors"): mock.Mock(return_value=set()),
            (G1A, "g0_reference_status"): mock.Mock(return_value={"ok": True, "problems": [], "run_id": "g0_x", "closed_sha256": "a" * 64})}


def call(argv, overrides=None, base=True, pre=None):
    """R.main with the whole start-up path stubbed; `overrides` {(module, name): replacement} replace single steps.  -> (exit code, stdout, stderr, patches)"""
    patches = base_patches() if base else {}
    patches.update(overrides or {})
    err, out = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as root, contextlib.ExitStack() as st:
        if pre:
            pre(root)
        st.enter_context(mock.patch.object(G1A, "EVIDENCE_ROOT", root))
        for (obj, name), val in patches.items():
            st.enter_context(mock.patch.object(obj, name, val))
        st.enter_context(contextlib.redirect_stderr(err))
        st.enter_context(contextlib.redirect_stdout(out))
        rc = R.main(argv)
    return rc, out.getvalue(), err.getvalue(), patches


class TestNormalAndPassThrough(unittest.TestCase):
    def test_the_stubbed_path_itself_works(self):
        rc, out, err, p = call(ARGV)
        self.assertEqual((rc, err), (0, ""))
        self.assertIn('"exit_code": 0', out)
        p[(R, "finalize")].assert_called_once()
        self.assertEqual(p[(R, "finalize")].call_args[0][1], "g1_test_start")

    def test_the_saved_verdict_code_of_finalize_is_passed_through(self):
        for code in (0, 1, 3):
            rc, out, err, _ = call(ARGV, {(R, "finalize"): mock.Mock(return_value=code)})
            self.assertEqual(rc, code)

    def test_check_mode_starts_nothing_and_prints_the_status(self):
        rc, out, err, p = call(["--check"])
        self.assertEqual((rc, err), (0, ""))
        for k in ("frozen_file_problems", "g0_reference", "authorization_present", '"executed": false'):
            self.assertIn(k, out)
        p[(R, "run")].assert_not_called()
        p[(R, "finalize")].assert_not_called()
        rc, out, err, p = call([])                                      # no flag at all behaves like --check
        self.assertEqual(rc, 0)
        p[(R, "run")].assert_not_called()

    def test_template_prints_a_non_valid_template(self):
        rc, out, err, p = call(["--template"])
        self.assertEqual(rc, 0)
        self.assertIn("TEMPLATE-NOT-VALID", out)
        p[(R, "run")].assert_not_called()


class TestSystemExitAndExceptions(unittest.TestCase):
    STEPS = [(R, "current"), (G1A, "frozen_problems"), (G1A, "load"), (R.GJ, "load_criteria"), (R.C, "sha256_file"), (R, "safe_preflight"), (R.GR, "ancestors"),
             (R, "prepare_dirs"), (R, "run"), (R, "finalize")]

    def test_an_unexpected_system_exit_in_any_step_gives_3_never_1_or_0(self):
        bad = []
        for obj, name in self.STEPS:
            for code in EXITS:
                rc, out, err, _ = call(ARGV, {(obj, name): mock.Mock(side_effect=SystemExit(code))})
                if rc != 3 or "G1-" not in err:
                    bad.append((name, code, rc, err[:100]))
        self.assertEqual(bad, [])

    def test_system_exit_one_is_the_named_negative_control(self):
        rc, out, err, _ = call(ARGV, {(R, "current"): mock.Mock(side_effect=SystemExit(1))})
        self.assertEqual(rc, 3)
        self.assertNotEqual(rc, 1)
        self.assertIn("G1-STARTUP-ERROR", err)
        self.assertIn("unexpected SystemExit(1)", err)

    def test_a_system_exit_zero_is_not_a_pass(self):
        rc, out, err, _ = call(ARGV, {(R, "prepare_dirs"): mock.Mock(side_effect=SystemExit(0))})
        self.assertEqual(rc, 3)

    def test_main_catches_a_system_exit_raised_by_the_whole_body(self):
        rc, out, err, _ = call(ARGV, {(R, "_main"): mock.Mock(side_effect=SystemExit(1))})
        self.assertEqual((rc, "G1-STARTUP-ERROR" in err), (3, True))

    def test_every_unexpected_exception_in_any_step_gives_3_never_1(self):
        bad = []
        for obj, name in self.STEPS:
            for exc in (RuntimeError("boom"), OSError(13, "denied"), ValueError("bad"), KeyError("k"), KeyboardInterrupt(), AssertionError("a"), MemoryError()):
                rc, out, err, _ = call(ARGV, {(obj, name): mock.Mock(side_effect=exc)})
                if rc != 3 or "G1-" not in err:
                    bad.append((name, type(exc).__name__, rc, err[:100]))
        self.assertEqual(bad, [])

    def test_check_and_template_modes_also_never_return_1(self):
        for argv, ov in ((["--check"], {(R, "current"): mock.Mock(side_effect=OSError(5, "io"))}), (["--check"], {(R, "current"): mock.Mock(side_effect=SystemExit(1))}),
                         ([], {(R, "current"): mock.Mock(side_effect=RuntimeError("x"))}), (["--template"], {(G1A, "template"): mock.Mock(side_effect=SystemExit(1))}),
                         (["--template"], {(G1A, "template"): mock.Mock(side_effect=RuntimeError("x"))})):
            rc, out, err, _ = call(argv, ov)
            self.assertEqual(rc, 3, argv)
            self.assertIn("G1-STARTUP-ERROR", err)

    def test_the_stage_is_named_in_the_marker(self):
        rc, out, err, _ = call(ARGV, {(R, "run"): mock.Mock(side_effect=RuntimeError("boom"))})
        self.assertEqual(rc, 3)
        self.assertIn("G1-RUN-ERROR", err)
        rc, out, err, _ = call(ARGV, {(R, "finalize"): mock.Mock(side_effect=RuntimeError("boom"))})
        self.assertIn("G1-PIPELINE-ERROR", err)
        rc, out, err, _ = call(ARGV, {(R, "prepare_dirs"): mock.Mock(side_effect=R.DirError("evidence root is a symlink"))})
        self.assertEqual(rc, 3)
        self.assertIn("G1-DIR-ERROR", err)


class TestRefusalsAndArgparse(unittest.TestCase):
    def test_refusals_are_2(self):
        rc, out, err, p = call(ARGV, {(G1A, "frozen_problems"): mock.Mock(return_value=["g0_criteria_v5.json: changed"])})
        self.assertEqual((rc, "REFUSED" in err), (2, True))
        p[(R, "run")].assert_not_called()
        rc, out, err, p = call(ARGV, {(G1A, "load"): mock.Mock(side_effect=G1A.G1AuthorizationError("no authorization"))})
        self.assertEqual((rc, "REFUSED" in err), (2, True))
        p[(R, "run")].assert_not_called()
        rc, out, err, _ = call(ARGV, {(G1A, "load"): mock.Mock(side_effect=G1A.G1AuthorizationError("authorization X was already consumed (single use)"))})
        self.assertEqual(rc, 2)
        self.assertIn("already consumed", err)

    def test_a_bad_run_id_is_refused(self):
        for rid in ("g0_20261101_000000_aaaaaa", "x", "g1", "g1_a b", "../g1_x", "g1_" + "x" * 80):
            rc, out, err, p = call(["--execute", "--run-id", rid])
            self.assertEqual(rc, 2, rid)
            p[(R, "run")].assert_not_called()

    def test_an_existing_run_directory_is_refused(self):
        rc, out, err, p = call(ARGV, pre=lambda root: os.mkdir(os.path.join(root, "g1_test_start")))
        self.assertEqual((rc, "run directory exists" in err), (2, True))
        p[(R, "run")].assert_not_called()

    def test_nothing_is_run_before_the_refusals_are_decided(self):
        rc, out, err, p = call(ARGV, {(G1A, "frozen_problems"): mock.Mock(return_value=["x"])})
        p[(R, "safe_preflight")].assert_not_called()
        p[(R, "prepare_dirs")].assert_not_called()

    def test_argparse_usage_error_keeps_exit_code_2_and_help_keeps_0(self):
        for argv in (["--no-such-option"], ["--auth"], ["--run-id"], ["--execute", "--bogus"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    R.main(argv)
            self.assertEqual(cm.exception.code, 2, argv)
            self.assertNotIn("G1-STARTUP-ERROR", err.getvalue(), argv)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                R.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("--execute", out.getvalue())
        self.assertNotIn("G1-STARTUP-ERROR", err.getvalue())

    def test_the_default_authorization_path_is_the_g1_file_outside_git(self):
        self.assertTrue(G1A.AUTH_DEFAULT.endswith("AUTHORIZATION_E1A_GATE_G1.json"))
        self.assertFalse(os.path.exists(G1A.AUTH_DEFAULT), "a G1 authorization file must not exist at this stage")


def _fn(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


class TestMainStructure(unittest.TestCase):
    def test_the_command_line_is_parsed_outside_the_safety_net_and_every_system_exit_is_caught(self):
        tree = ast.parse(SRC["g1_run"])
        main = _fn(tree, "main")
        parse_line = next(n.lineno for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "parse_args")
        tries = [n for n in ast.walk(main) if isinstance(n, ast.Try)]
        self.assertEqual(len(tries), 1)
        self.assertLess(parse_line, tries[0].lineno)
        self.assertEqual(ast.dump(tries[0].handlers[0].type), ast.dump(ast.Name(id="SystemExit", ctx=ast.Load())))
        self.assertEqual(ast.dump(tries[0].handlers[1].type), ast.dump(ast.Name(id="BaseException", ctx=ast.Load())))
        for h in tries[0].handlers:
            self.assertFalse(any(isinstance(n, ast.Raise) for n in ast.walk(h)), "no handler of main() may re-raise")

    def test_no_code_path_of_main_returns_the_fail_code_1(self):
        tree = ast.parse(SRC["g1_run"])
        for name in ("main", "_main"):
            for n in ast.walk(_fn(tree, name)):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant):
                    self.assertNotEqual(n.value.value, 1, "%s() returns the FAIL code at line %d" % (name, n.lineno))

    def test_the_run_and_the_pipeline_are_each_guarded_by_a_catch_all(self):
        tree = ast.parse(SRC["g1_run"])
        body = _fn(tree, "_main")
        handlers = [h for n in ast.walk(body) if isinstance(n, ast.Try) for h in n.handlers]
        self.assertGreaterEqual(sum(1 for h in handlers if h.type is not None and ast.dump(h.type) == ast.dump(ast.Name(id="BaseException", ctx=ast.Load()))), 2)


FORBIDDEN_ATTR = {"kill", "killpg", "pidfd_send_signal", "raise_signal", "pthread_kill", "fork", "forkpty", "system", "popen", "Popen", "run", "call", "check_call",
                  "check_output", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv",
                  "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp", "_exit", "pidfd_open", "setsid", "setpgid", "wait", "wait3", "wait4", "waitid",
                  "rename", "replace", "unlink", "remove", "truncate", "ftruncate", "renames"}


class TestSafetyBoundaryByAst(unittest.TestCase):
    def test_no_process_signal_wait_or_overwrite_call_in_any_g1_module(self):
        for key, src in SRC.items():
            for n in ast.walk(ast.parse(src)):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in ("os", "signal", "subprocess", "pty"):
                    self.assertNotIn(n.func.attr, FORBIDDEN_ATTR, "%s:%d %s.%s" % (key, n.lineno, n.func.value.id, n.func.attr))

    def test_exactly_one_waitpid_call_and_only_in_the_runner(self):
        counts = {}
        for key, src in SRC.items():
            counts[key] = len([n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "waitpid"
                               and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"])
        self.assertEqual(counts, {"g1_auth": 0, "g1_judge": 0, "g1_run": 1})

    def test_the_gate_is_never_released_and_the_bench_abort_is_used(self):
        tree = ast.parse(SRC["g1_run"])
        names = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertNotIn("release", names)
        self.assertIn("abort_held", names)
        r_consts = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == b"R"]
        self.assertEqual(len(r_consts), 1)                                   # only in the guard's comparison that traps the byte
        compares = [n for n in ast.walk(tree) if isinstance(n, ast.Compare) and any(isinstance(c, ast.Constant) and c.value == b"R" for c in n.comparators)]
        self.assertEqual(len(compares), 1)

    def test_the_zombie_as_dead_logic_and_the_sigkill_cleanup_are_not_used(self):
        used_names, imported = set(), set()
        for key, src in SRC.items():
            for n in ast.walk(ast.parse(src)):
                if isinstance(n, ast.Attribute):
                    used_names.add(n.attr)
                elif isinstance(n, ast.Name):
                    used_names.add(n.id)
                elif isinstance(n, ast.Import):
                    imported |= {a.name for a in n.names}
                elif isinstance(n, ast.ImportFrom):
                    imported.add(n.module)
        for bad in ("_confirmed_dead", "finish_trial_cleanup", "kill_registered", "kill_unregistered_direct", "GateCase"):
            self.assertNotIn(bad, used_names, bad)
        for bad in ("janitor", "trial", "scenarios", "validity", "e1a_runner"):
            self.assertNotIn(bad, imported, bad)
        self.assertIn("finish_cleanup", used_names)                         # the cleanup the G0 run also uses, only after the reap

    def test_cleanup_runs_only_after_the_reap_in_run_test(self):
        tree = ast.parse(SRC["g1_run"])
        fn = _fn(tree, "run_test")
        lines = {}
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                lines.setdefault(n.func.attr, []).append(n.lineno)
        self.assertEqual(len(lines["waitpid"]), 1)
        self.assertGreater(min(lines["finish_cleanup"]), lines["waitpid"][0])
        self.assertGreater(min(lines["finish_cleanup"]), max(lines["read_stat"]))
        self.assertLess(lines["abort_held"][0], lines["waitpid"][0])

    def test_the_closure_is_published_with_link_never_rename(self):
        self.assertIn("os.link(tmp, final, follow_symlinks=False)", SRC["g1_run"])
        self.assertNotRegex(SRC["g1_run"], r"os\.(rename|replace)\(")

    def test_no_authorization_file_is_written_by_any_module(self):
        for key, src in SRC.items():
            for n in ast.walk(ast.parse(src)):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                    if any(c in str(n.args[1].value) for c in "wa+"):
                        self.assertNotIn("AUTH_DEFAULT", ast.dump(n.args[0]), "%s:%d" % (key, n.lineno))
                        self.assertNotIn("args.auth", ast.dump(n.args[0]), "%s:%d" % (key, n.lineno))

    def test_the_runner_imports_g0_helpers_read_only_and_modifies_no_g0_file(self):
        self.assertIn("import g0_run as GR", SRC["g1_run"])
        for key, src in SRC.items():
            self.assertNotRegex(src, r"g0_(run|auth|judge)\.py[\"'],\s*[\"']w", key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
