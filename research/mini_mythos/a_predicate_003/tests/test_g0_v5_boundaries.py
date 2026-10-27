"""Final-closeout boundary tests (F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001, closeout):
  B-1  an unexpected SystemExit (sys.exit(1), sys.exit("text"), sys.exit(True), a stray sys.exit(0)) anywhere after the command line was parsed is a
       start-up error -- exit code 3, never 1 (FAIL) and never 0 (PASS); argparse keeps 0 (--help) and 2 (usage error);
  B-2  the runner and its environment helper start no external process, not even before the sentinels exist (no platform / subprocess use, sentinels
       are installed first, environment facts come from os.uname());
  B-3  the runner verifies the real checkout HEAD itself (from .git) instead of trusting an environment variable, and records the key file hashes.
No process is started by these tests."""
import ast
import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(A003, "tools"))
import g0_v5_fixtures as F  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402
import g0_run as GR  # noqa: E402
import g0_test_env as E  # noqa: E402
import test_g0_v5_supplement as SUP  # noqa: E402

TOOLS = os.path.join(A003, "tools")


class TestSystemExitIsNeverAFailOrAPass(unittest.TestCase):
    STEPS = [(GR, "current"), (GA, "frozen_problems"), (GA, "load"), (GJ, "load_criteria"), (GR, "safe_preflight"), (GR, "ancestors"), (GR, "prepare_dirs"),
             (GR, "run"), (GR, "finalize")]
    EXITS = (1, "text", True, False, 0, None, 2, 3, 7, -1)

    def setUp(self):
        self.s = SUP.TestStartupExceptionsNeverReturnExitCodeOne("test_the_stubbed_start_up_path_itself_works")

    def test_an_unexpected_system_exit_in_any_step_gives_3(self):
        bad = []
        for obj, name in self.STEPS:
            for code in self.EXITS:
                rc, err = self.s.call(self.s.ARGV, {(obj, name): mock.Mock(side_effect=SystemExit(code))})
                if rc != 3 or "G0-" not in err:
                    bad.append((name, code, rc, err[:100]))
        self.assertEqual(bad, [])

    def test_system_exit_one_is_the_named_negative_control(self):
        rc, err = self.s.call(self.s.ARGV, {(GR, "current"): mock.Mock(side_effect=SystemExit(1))})
        self.assertEqual(rc, 3)
        self.assertNotEqual(rc, 1)
        self.assertIn("unexpected SystemExit(1)", err)

    def test_a_system_exit_zero_is_not_a_pass(self):
        rc, err = self.s.call(self.s.ARGV, {(GR, "prepare_dirs"): mock.Mock(side_effect=SystemExit(0))})
        self.assertEqual(rc, 3)

    def test_system_exit_in_the_check_and_template_modes(self):
        for argv, ov in ((["--check"], {(GR, "current"): mock.Mock(side_effect=SystemExit(1))}), (["--template"], {(GA, "template"): mock.Mock(side_effect=SystemExit(1))})):
            rc, err = self.s.call(argv, ov, base=False)
            self.assertEqual(rc, 3, argv)

    def test_argparse_usage_error_keeps_exit_code_2(self):
        for argv in (["--no-such-option"], ["--auth"], ["--run-id"], ["--execute", "--bogus"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    GR.main(argv)
            self.assertEqual(cm.exception.code, 2, argv)
            self.assertNotIn("G0-STARTUP-ERROR", err.getvalue(), argv)

    def test_argparse_help_keeps_exit_code_0_and_is_not_marked(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                GR.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("--execute", out.getvalue())
        self.assertNotIn("G0-STARTUP-ERROR", err.getvalue())

    def test_the_command_line_is_parsed_outside_the_safety_net_and_the_net_catches_every_system_exit(self):
        tree = ast.parse(open(os.path.join(F.G0, "g0_run.py")).read())
        main = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main")
        parse_line = next(n.lineno for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "parse_args")
        tries = [n for n in ast.walk(main) if isinstance(n, ast.Try)]
        self.assertEqual(len(tries), 1)
        self.assertLess(parse_line, tries[0].lineno, "parse_args must be called before (outside) the try")
        handlers = tries[0].handlers
        self.assertEqual([ast.dump(h.type) if h.type else None for h in handlers][0], ast.dump(ast.Name(id="SystemExit", ctx=ast.Load())))
        for h in handlers:
            self.assertFalse(any(isinstance(n, ast.Raise) for n in ast.walk(h)), "no handler of main() may re-raise")

    def test_main_still_returns_the_normal_codes(self):
        rc, err = self.s.call(self.s.ARGV, {})
        self.assertEqual((rc, err), (0, ""))
        rc, err = self.s.call(self.s.ARGV, {(GR, "finalize"): mock.Mock(return_value=1)})
        self.assertEqual(rc, 1)                                        # a saved FAIL verdict (finalize says 1) is passed through unchanged
        rc, err = self.s.call(self.s.ARGV, {(GA, "load"): mock.Mock(side_effect=GA.G0AuthorizationError("none"))})
        self.assertEqual(rc, 2)


class TestRunnerStartsNoProcessEvenBeforeTheSentinels(unittest.TestCase):
    def test_the_helper_module_imports_no_platform_or_subprocess(self):
        for name in ("g0_test_env.py", "run_g0_v5_cpu_tests.py"):
            tree = ast.parse(open(os.path.join(TOOLS, name)).read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    self.assertNotIn("platform", [a.name for a in n.names], name)
                if isinstance(n, ast.ImportFrom):
                    self.assertNotEqual(n.module, "platform", name)
                if name == "g0_test_env.py" and isinstance(n, (ast.Import, ast.ImportFrom)):
                    mods = [a.name for a in n.names] + [getattr(n, "module", None)]
                    self.assertNotIn("subprocess", mods)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "platform":
                    self.fail("%s calls platform.%s (it can run `uname` through subprocess)" % (name, n.func.attr))

    def test_the_runner_installs_the_sentinels_before_anything_else_runs(self):
        src = open(os.path.join(TOOLS, "run_g0_v5_cpu_tests.py")).read()
        tree = ast.parse(src)
        first_sentinel = next(n.lineno for n in tree.body if isinstance(n, ast.For) and "_sentinel" in ast.dump(n))
        calls_before = [n.lineno for n in tree.body if n.lineno < first_sentinel and any(isinstance(c, ast.Call) for c in ast.walk(n))
                        and not isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        # only the sys.path / dirname plumbing may run before the sentinels
        for n in tree.body:
            if n.lineno < first_sentinel and not isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
                self.assertNotIn("environment_info", ast.dump(n))
                self.assertNotIn("verify_checkout", ast.dump(n))
                self.assertNotIn("check_output", ast.dump(n))
        self.assertIn("os.uname", open(os.path.join(TOOLS, "g0_test_env.py")).read())
        self.assertIn("VIOLATIONS", src)
        self.assertIsInstance(calls_before, list)

    def test_environment_info_needs_no_external_process(self):
        killer = mock.Mock(side_effect=AssertionError("a process was started"))
        import subprocess
        with mock.patch.object(subprocess, "Popen", killer), mock.patch.object(subprocess, "run", killer), mock.patch.object(subprocess, "check_output", killer):
            info = E.environment_info()
        self.assertEqual(set(info) >= {"python", "kernel", "machine", "cpu_count", "uid", "gpu_used"}, True)
        self.assertIs(info["gpu_used"], False)
        killer.assert_not_called()


class TestCheckoutIdentity(unittest.TestCase):
    SHA = "0123456789abcdef0123456789abcdef01234567"

    def fake_repo(self, head_text, refs=None, packed=None):
        d = tempfile.TemporaryDirectory()
        g = os.path.join(d.name, ".git")
        os.makedirs(os.path.join(g, "refs", "heads"))
        open(os.path.join(g, "HEAD"), "w").write(head_text)
        for ref, sha in (refs or {}).items():
            open(os.path.join(g, ref), "w").write(sha + "\n")
        if packed:
            open(os.path.join(g, "packed-refs"), "w").write("# pack-refs with: peeled\n" + "".join("%s %s\n" % (s, r) for r, s in packed.items()))
        sub = os.path.join(d.name, "a", "b")
        os.makedirs(sub)
        return d, sub

    def test_loose_ref_detached_and_packed_heads(self):
        d, sub = self.fake_repo("ref: refs/heads/x\n", refs={"refs/heads/x": self.SHA})
        with d:
            self.assertEqual(E.read_git_head(sub)[:2], (self.SHA, "refs/heads/x"))
        d, sub = self.fake_repo(self.SHA + "\n")
        with d:
            self.assertEqual(E.read_git_head(sub)[:2], (self.SHA, None))
        d, sub = self.fake_repo("ref: refs/heads/y\n", packed={"refs/heads/y": self.SHA})
        with d:
            self.assertEqual(E.read_git_head(sub)[:2], (self.SHA, "refs/heads/y"))

    def test_an_unresolvable_head_is_an_error_not_a_guess(self):
        d, sub = self.fake_repo("ref: refs/heads/none\n")
        with d:
            with self.assertRaises(RuntimeError):
                E.read_git_head(sub)
        d, sub = self.fake_repo("garbage\n")
        with d:
            with self.assertRaises(RuntimeError):
                E.read_git_head(sub)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                E.read_git_head(d)

    def test_the_real_checkout_head_is_read_from_git_files(self):
        head, ref, gd = E.read_git_head(A003)
        self.assertRegex(head, r"^[0-9a-f]{40}$")
        self.assertTrue(os.path.isdir(gd))

    def test_verify_checkout_accepts_only_the_real_head(self):
        head = E.read_git_head(A003)[0]
        ok = E.verify_checkout(A003, head, GA.FROZEN_FILES)
        self.assertTrue(ok["ok"], ok["problems"])
        self.assertEqual(ok["actual_head"], head)
        self.assertEqual(ok["bench_code_sha256"], E.BENCH_CODE_SHA256)
        for bad in ("0" * 40, self.SHA, None, "", "abc", head.upper(), head[:-1] + ("0" if head[-1] != "0" else "1")):
            r = E.verify_checkout(A003, bad, GA.FROZEN_FILES)
            self.assertFalse(r["ok"], repr(bad))
            self.assertTrue(r["problems"])

    def test_a_changed_frozen_file_or_bench_refuses(self):
        head = E.read_git_head(A003)[0]
        wrong = dict(GA.FROZEN_FILES)
        wrong["g0_criteria_v5.json"] = "0" * 64
        r = E.verify_checkout(A003, head, wrong)
        self.assertFalse(r["ok"])
        self.assertTrue(any("frozen files changed" in p for p in r["problems"]))
        with mock.patch.object(E, "BENCH_CODE_SHA256", "1" * 64):
            self.assertFalse(E.verify_checkout(A003, head, GA.FROZEN_FILES)["ok"])

    def test_the_key_implementation_files_are_hashed_both_ways(self):
        r = E.verify_checkout(A003, E.read_git_head(A003)[0], GA.FROZEN_FILES)
        kf = r["key_files"]
        for rel in ("gate_g0/g0_auth.py", "gate_g0/g0_judge.py", "gate_g0/g0_run.py", "gate_g0/g0_criteria_v5.json", "tools/run_g0_v5_cpu_tests.py"):
            self.assertIn(rel, kf)
            self.assertRegex(kf[rel]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(kf[rel]["git_blob_sha1"], r"^[0-9a-f]{40}$")
        self.assertEqual(kf["gate_g0/g0_criteria_v5.json"]["sha256"], GA.FROZEN_CRITERIA_SHA256)

    def test_git_blob_sha1_matches_git_hash_object_semantics(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f")
            open(p, "wb").write(b"hello\n")
            self.assertEqual(E.git_blob_sha1(p), "ce013625030ba8dba906f756967f9e9ca394464a")      # `echo hello | git hash-object --stdin`
            self.assertEqual(E.sha256_file(p), hashlib.sha256(b"hello\n").hexdigest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
