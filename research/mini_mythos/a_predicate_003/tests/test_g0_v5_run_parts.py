"""Pure-logic tests for the parts of g0_run that need no process: the release-write guard (F-18), the total budget (F-9), the evidence-root /
consumption-directory / run-directory handling (F-12 / F-13), the never-raising preflight, and AST checks of the structure of run() (bounded reap F-8,
ledger capture before the registry parse, budget checks in every loop).  WRITTEN, NOT RUN (F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001);
running them needs its own authorization.  The guard is installed only around `os.write` on a private pipe and uninstalled in `finally`;
`os.fork` is never called and no child process exists."""
import ast
import contextlib
import errno
import os
import stat
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
import g0_run as GR  # noqa: E402


def run_ast():
    return ast.parse(open(os.path.join(F.G0, "g0_run.py")).read())


def func(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


class TestReleaseWriteGuard(unittest.TestCase):
    def setUp(self):
        self.g = GR.Guard()
        self.r, self.w = os.pipe()
        self.g.install()

    def tearDown(self):
        self.g.uninstall()
        for fd in (self.r, self.w):
            with contextlib.suppress(OSError):
                os.close(fd)

    def test_a_successful_release_write_is_an_entry_with_before_after_and_result(self):
        self.g.watch_fd = self.w
        n = os.write(self.w, b"R")
        self.assertEqual(n, 1)
        e = self.g.release_writes
        self.assertEqual(len(e), 1)
        self.assertEqual((e[0]["result"], e[0]["returned"], e[0]["errno"], e[0]["error"]), ("ok", 1, None, None))
        self.assertLessEqual(e[0]["mono_before"], e[0]["mono_after"])

    def test_a_failed_release_write_is_recorded_as_an_error_with_errno_and_text_never_dropped(self):
        os.close(self.r)
        self.r = -1
        self.g.watch_fd = self.w
        with self.assertRaises(BrokenPipeError):
            os.write(self.w, b"R")
        e = self.g.release_writes
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["result"], "error")
        self.assertEqual(e[0]["errno"], errno.EPIPE)
        self.assertTrue(e[0]["error"])
        self.assertIsNone(e[0]["returned"])
        self.assertIsNotNone(e[0]["mono_after"])

    def test_other_writes_are_not_recorded(self):
        self.g.watch_fd = self.w
        os.write(self.w, b"A")
        self.g.watch_fd = None
        os.write(self.w, b"R")
        self.assertEqual(self.g.release_writes, [])

    def test_every_attempt_is_an_entry(self):
        self.g.watch_fd = self.w
        os.write(self.w, b"R")
        os.write(self.w, b"R")
        self.assertEqual(len(self.g.release_writes), 2)

    def test_the_summary_has_release_writes_and_not_the_v2_pre_write_list(self):
        s = self.g.summary()
        self.assertIn("release_writes", s)
        self.assertNotIn("release_byte_pre_write_monos", s)
        self.assertEqual(set(s), {"violations", "fork_calls", "fork_pids", "waitpid_calls", "release_writes"})

    def test_the_entries_validate_against_the_schema_type(self):
        self.g.watch_fd = self.w
        os.write(self.w, b"R")
        os.close(self.r)
        self.r = -1
        with self.assertRaises(BrokenPipeError):
            os.write(self.w, b"R")
        crit = F.criteria()
        typ = next(f["type"] for f in crit["evidence_schema"]["fields"] if f["path"] == "guard.release_writes")
        self.assertIsNone(GJ.TYPE_VALIDATORS[typ](self.g.release_writes))

    def test_the_guard_refuses_signals_exec_and_foreign_waits(self):
        # No call here can send a signal or touch a child even if the guard were missing: os.kill() without arguments is a TypeError for the
        # real function, and the wait names a pid that is certainly not a child of this process (ChildProcessError for the real function).
        with self.assertRaises(GR.GuardViolation):
            os.kill()
        with self.assertRaises(GR.GuardViolation):
            os.waitpid(999999999, os.WNOHANG)
        self.assertEqual([v["call"] for v in self.g.violations], ["os.kill", "os.waitpid"])
        self.assertEqual(self.g.fork_calls, 0)

    def test_uninstall_restores_the_original_functions(self):
        self.g.uninstall()
        self.assertIs(os.write, self.g.real["os.write"])
        self.assertIs(os.fork, self.g.real["os.fork"])
        self.assertIs(os.waitpid, self.g.real["os.waitpid"])
        self.g.install()                                           # tearDown uninstalls again


class TestBudget(unittest.TestCase):
    def make(self, max_s=20.0):
        self.now = [100.0]
        p = mock.patch.object(C, "mono", lambda: self.now[0])
        p.start()
        self.addCleanup(p.stop)
        self.ev = {"deadline_hits": []}
        return GR.Budget(self.ev, max_s)

    def test_left_cap_and_check(self):
        b = self.make()
        self.assertEqual(b.left(), 20.0)
        self.assertEqual(b.cap(5.0), 5.0)
        self.now[0] += 18.0
        self.assertAlmostEqual(b.left(), 2.0)
        self.assertAlmostEqual(b.cap(5.0), 2.0)
        b.check("x")
        self.assertEqual(self.ev["deadline_hits"], [])
        self.now[0] += 3.0
        with self.assertRaises(GR.BudgetExceeded):
            b.check("loop")
        self.assertEqual(self.ev["deadline_hits"], ["total"])
        with self.assertRaises(GR.BudgetExceeded):
            b.check("again")
        self.assertEqual(self.ev["deadline_hits"], ["total"])         # recorded once
        self.assertEqual(b.cap(5.0), 0.0)

    def test_wait_records_the_phase_name_or_total(self):
        class Obs:
            def __init__(self, result):
                self.result, self.timeouts = result, []

            def wait_for(self, cond, timeout):
                self.timeouts.append(timeout)
                return self.result
        b = self.make()
        o = Obs(True)
        self.assertTrue(b.wait(o, lambda: True, "ready", 5.0))
        self.assertEqual(o.timeouts, [5.0])
        o = Obs(False)
        self.assertFalse(b.wait(o, lambda: False, "ready", 5.0))
        self.assertEqual(self.ev["deadline_hits"], ["ready"])
        self.now[0] += 17.0                                            # 3 s left: the phase deadline is capped by the total
        o = Obs(False)
        self.assertFalse(b.wait(o, lambda: False, "exit", 5.0))
        self.assertEqual(o.timeouts, [3.0])
        self.assertEqual(self.ev["deadline_hits"], ["ready", "total"])

    def test_the_criteria_limits_are_the_ones_used(self):
        lim = F.criteria()["limits"]
        self.assertEqual((lim["max_seconds"], lim["t_gate_max_s"], lim["hold_before_release_s"], lim["ready_deadline_s"], lim["exit_deadline_s"], lim["reap_deadline_s"]),
                         (20.0, 5.0, 0.3, 5.0, 5.0, 5.0))


class TestDirectories(unittest.TestCase):
    def test_ensure_dir_creates_an_absent_directory_non_recursively_and_reports_it(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "evidence")
            info = GR.ensure_dir(p)
            self.assertTrue(info["created_by_this_run"])
            self.assertEqual((info["path"], info["uid"]), (p, os.geteuid()))
            self.assertEqual(info["mode"] & 0o022, 0)
            with self.assertRaises(GR.DirError):
                GR.ensure_dir(os.path.join(d, "no", "parent", "here"))             # never recursive

    def test_ensure_dir_validates_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "e")
            os.mkdir(p, 0o755)
            info = GR.ensure_dir(p)
            self.assertFalse(info["created_by_this_run"])
            self.assertEqual(info["ino"], os.stat(p).st_ino)

    def test_ensure_dir_refuses_a_symlink_a_file_and_a_group_or_other_writable_directory(self):
        with tempfile.TemporaryDirectory() as d:
            real = os.path.join(d, "real")
            os.mkdir(real)
            link = os.path.join(d, "link")
            os.symlink(real, link)
            with self.assertRaises(GR.DirError):
                GR.ensure_dir(link)
            f = os.path.join(d, "file")
            open(f, "w").write("x")
            with self.assertRaises(GR.DirError):
                GR.ensure_dir(f)
            w = os.path.join(d, "writable")
            os.mkdir(w)
            os.chmod(w, 0o775)
            with self.assertRaises(GR.DirError):
                GR.ensure_dir(w)
            o = os.path.join(d, "other")
            os.mkdir(o)
            os.chmod(o, 0o757)
            with self.assertRaises(GR.DirError):
                GR.ensure_dir(o)

    def test_prepare_dirs_creates_the_run_directory_exclusively(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "evidence")
            with mock.patch.object(GA, "EVIDENCE_ROOT", root), mock.patch.object(GA, "CONSUMED_DIR", os.path.join(root, "_g0_consumed")):
                run_dir = os.path.join(root, "g0_a")
                r, c, rd = GR.prepare_dirs(run_dir)
                self.assertTrue(r["created_by_this_run"] and c["created_by_this_run"])
                self.assertEqual(rd, {"path": run_dir, "created_by_this_process": True})
                self.assertTrue(stat.S_ISDIR(os.lstat(run_dir).st_mode))
                with self.assertRaises(GR.DirError):
                    GR.prepare_dirs(run_dir)                                           # an existing run directory is never reused
                r2, c2, _ = GR.prepare_dirs(os.path.join(root, "g0_b"))
                self.assertFalse(r2["created_by_this_run"] or c2["created_by_this_run"])

    def test_the_directory_infos_validate_against_the_schema(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "evidence")
            with mock.patch.object(GA, "EVIDENCE_ROOT", root), mock.patch.object(GA, "CONSUMED_DIR", os.path.join(root, "_g0_consumed")):
                r, c, rd = GR.prepare_dirs(os.path.join(root, "g0_a"))
        ev = F.good_evidence()
        ev["evidence_root"], ev["consumed_dir"], ev["run_dir"] = r, c, rd
        self.assertEqual(GJ.validate_evidence(ev, F.criteria()), [])

    def test_write_exclusive_json_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.json")
            GR.write_exclusive_json(p, {"a": 1})
            with self.assertRaises(FileExistsError):
                GR.write_exclusive_json(p, {"a": 2})
            self.assertEqual(open(p).read(), '{"a":1}')
            with self.assertRaises(TypeError):
                GR.write_exclusive_json(os.path.join(d, "n.json"), {"a": {1}})


class TestPreflightShape(unittest.TestCase):
    def test_safe_preflight_never_raises_and_returns_a_schema_valid_blocking_result(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(GR, "preflight", side_effect=OSError(errno.EACCES, "/proc unreadable")):
                pf = GR.safe_preflight(os.path.join(d, "g0_x"), set())
        self.assertIs(pf["ok"], False)
        self.assertTrue(pf["problems"])
        self.assertIsNone(GJ.TYPE_VALIDATORS[next(f["type"] for f in F.criteria()["evidence_schema"]["fields"] if f["path"] == "preflight")](pf))
        ev = F.good_evidence()
        ev["preflight"] = pf
        r = GJ.judge(ev, F.criteria(), GA.FROZEN_CRITERIA_SHA256)
        self.assertEqual(r["checks"]["G0-C01"]["status"], "FAIL_EVIDENCED")
        self.assertEqual(r["verdict"], "BLOCKED")

    def test_the_real_preflight_result_has_the_schema_fields(self):
        fields = ("ok", "problems", "children", "token_residue", "unresolved_prior", "enumeration_problems", "run_id_unique", "fd_count", "total_procs")
        src = open(os.path.join(F.G0, "g0_run.py")).read()
        for k in fields:
            self.assertIn('"%s"' % k, src)


class TestRunStructure(unittest.TestCase):
    """AST checks of run(): the structure the criteria require, without executing it."""

    def test_the_reap_is_a_bounded_non_blocking_poll_inside_a_loop_with_a_budget_check(self):
        run = func(run_ast(), "run")
        loops = [n for n in ast.walk(run) if isinstance(n, ast.While) and "waitpid" in ast.dump(n)]
        self.assertEqual(len(loops), 1)
        d = ast.dump(loops[0])
        self.assertIn("WNOHANG", d)
        self.assertIn("budget", d)
        self.assertIn("reap_deadline_s", ast.dump(run))
        self.assertIn("'reap'", ast.dump(loops[0]).replace('"', "'"))

    def test_every_loop_and_phase_boundary_checks_the_budget(self):
        run = func(run_ast(), "run")
        loops = [n for n in ast.walk(run) if isinstance(n, ast.While)]
        self.assertGreaterEqual(len(loops), 3)
        for lp in loops:
            self.assertIn("budget", ast.dump(lp), "a loop of run() does not check the total budget (F-9)")
        calls = [n for n in ast.walk(run) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("check", "wait") and isinstance(n.func.value, ast.Name)
                 and n.func.value.id == "budget"]
        self.assertGreaterEqual(len(calls), 10)

    def test_the_ledger_is_captured_before_the_registry_file_is_parsed(self):
        run = func(run_ast(), "run")
        lines = {}
        for n in ast.walk(run):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value in ("reg_memory_records", "reg_writer_seq", "reg") and isinstance(n.ctx, ast.Store):
                lines.setdefault(n.slice.value, n.lineno)
        self.assertLess(lines["reg_memory_records"], lines["reg"])
        self.assertLess(lines["reg_writer_seq"], lines["reg"])
        src = ast.dump(run)
        self.assertIn("deepcopy", src)

    def test_the_run_directory_is_not_created_by_run_and_the_authorization_copy_is_exclusive(self):
        run = func(run_ast(), "run")
        for n in ast.walk(run):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("mkdir", "makedirs"):
                self.fail("run() must not create directories itself (prepare_dirs does, exclusively)")
        self.assertIn("'xb'", ast.dump(run).replace('"', "'"))

    def test_the_release_goes_through_the_guard_watch_and_is_reset_in_finally(self):
        run = func(run_ast(), "run")
        tries = [n for n in ast.walk(run) if isinstance(n, ast.Try) and "release" in ast.dump(n) and "watch_fd" in ast.dump(n)]
        self.assertTrue(tries)
        self.assertTrue(any("watch_fd" in ast.dump(t.finalbody[0]) for t in tries if t.finalbody))

    def test_main_creates_directories_only_after_a_clean_read_only_preflight_attempt(self):
        main = func(run_ast(), "_main")
        seq = [name for _, name in sorted((n.lineno, n.func.id) for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name))]
        self.assertLess(seq.index("safe_preflight"), seq.index("prepare_dirs"))
        self.assertLess(seq.index("prepare_dirs"), seq.index("run"))
        self.assertLess(seq.index("run"), seq.index("finalize"))

    def test_publish_closure_calls_the_steps_in_the_order_of_the_criteria(self):
        fn = func(run_ast(), "publish_closure")
        names = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute):
                    names.append((n.lineno, n.func.attr))
                elif isinstance(n.func, ast.Name):
                    names.append((n.lineno, n.func.id))
        order = [x for _, x in sorted(names) if x in ("build_marker", "write_exclusive", "read_back", "link", "fsync_dir")]
        self.assertEqual(order, ["build_marker", "write_exclusive", "read_back", "link", "fsync_dir", "read_back"])
        self.assertIn("follow_symlinks", ast.dump(fn))

    def test_every_marker_of_the_criteria_is_emitted(self):
        src = open(os.path.join(F.G0, "g0_run.py")).read()
        for m in ("G0-EVIDENCE-UNSAVED", "G0-EVIDENCE-UNVERIFIED", "G0-JUDGE-ERROR", "G0-SUMMARY-UNSAVED", "G0-CLOSE-UNPUBLISHED", "G0-CLOSE-UNCONFIRMED"):
            self.assertIn(m, src)
        crit = F.criteria()
        for m in ("G0-EVIDENCE-UNSAVED", "G0-EVIDENCE-UNVERIFIED", "G0-JUDGE-ERROR", "G0-SUMMARY-UNSAVED"):
            self.assertIn(m, str(crit["evidence_pipeline"]))
        for m in ("G0-CLOSE-UNPUBLISHED", "G0-CLOSE-UNCONFIRMED"):
            self.assertIn(m, str(crit["closure"]))

    def test_the_code_hash_covers_the_v5_criteria_and_all_three_modules(self):
        self.assertEqual(GA.G0_CODE_FILES, ("g0_auth.py", "g0_judge.py", "g0_run.py", "g0_criteria_v5.json"))
        h = GA.g0_code_hash()
        self.assertEqual(len(h), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
