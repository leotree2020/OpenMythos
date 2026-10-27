"""Supplementary CPU tests of F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001 (no process is started; every process-related function is a sentinel under
tools/run_g0_v5_cpu_tests.py):
  S-1  a start-up exception must never leave the process with exit code 1 (the FAIL code): any exception before or around the run maps to 3
       (BLOCKED), a refusal to 2;
  S-2  G0-C07 (and the F3 rules of G0-C03) must not produce a FAIL from a malformed release record: format-damaged guard evidence is
       UNEVALUABLE, never an evidenced violation; well-formed violations still FAIL (negative controls)."""
import contextlib
import copy
import io
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
import g0_run as GR  # noqa: E402

CRIT = F.criteria()


def judge(ev):
    return GJ.judge(ev, CRIT, GA.FROZEN_CRITERIA_SHA256)


class TestStartupExceptionsNeverReturnExitCodeOne(unittest.TestCase):
    ARGV = ["--execute", "--auth", "/nonexistent/auth.json", "--run-id", "g0_sup_start"]

    def call(self, argv, overrides, base=True):
        """GR.main with the whole start-up path stubbed; `overrides` {(module, name): replacement} replace single steps.  -> (exit code, stderr)"""
        patches = {}
        if base:
            patches = {(GA, "frozen_problems"): mock.Mock(return_value=[]), (GA, "load"): mock.Mock(return_value=({"authorization_id": "OWNER-G0-0001", "bindings": F.bindings()}, b"{}")),
                       (GR, "current"): mock.Mock(return_value=F.bindings()), (GR, "safe_preflight"): mock.Mock(return_value={"ok": True}),
                       (GR, "prepare_dirs"): mock.Mock(return_value=({}, {}, {})), (GR, "run"): mock.Mock(return_value=F.good_evidence()),
                       (GR, "finalize"): mock.Mock(return_value=0)}
        patches.update(overrides)
        err, out = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as root, contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(GA, "EVIDENCE_ROOT", root))
            for (obj, name), val in patches.items():
                st.enter_context(mock.patch.object(obj, name, val))
            st.enter_context(contextlib.redirect_stderr(err))
            st.enter_context(contextlib.redirect_stdout(out))
            rc = GR.main(argv)
        return rc, err.getvalue()

    def test_the_stubbed_start_up_path_itself_works(self):
        rc, err = self.call(self.ARGV, {})
        self.assertEqual((rc, err), (0, ""))

    def test_every_unexpected_exception_in_the_start_up_path_gives_3_never_1(self):
        steps = [(GR, "current"), (GA, "frozen_problems"), (GA, "load"), (GJ, "load_criteria"), (C, "sha256_file"), (GR, "safe_preflight"), (GR, "ancestors"),
                 (GR, "prepare_dirs"), (GR, "run"), (GR, "finalize")]
        bad = []
        for obj, name in steps:
            for exc in (RuntimeError("boom"), OSError(13, "denied"), ValueError("bad"), KeyError("k"), KeyboardInterrupt()):
                rc, err = self.call(self.ARGV, {(obj, name): mock.Mock(side_effect=exc)})
                if rc != 3 or "G0-" not in err:
                    bad.append((name, type(exc).__name__, rc, err[:120]))
        self.assertEqual(bad, [])

    def test_check_and_template_modes_also_never_return_1_on_an_exception(self):
        for argv in (["--check"], []):
            rc, err = self.call(argv, {(GR, "current"): mock.Mock(side_effect=OSError(5, "I/O error"))}, base=False)
            self.assertEqual(rc, 3, argv)
            self.assertIn("G0-STARTUP-ERROR", err)
        rc, err = self.call(["--template"], {(GA, "template"): mock.Mock(side_effect=RuntimeError("x"))}, base=False)
        self.assertEqual(rc, 3)

    def test_a_refusal_is_2_and_a_usage_error_is_2(self):
        rc, err = self.call(self.ARGV, {(GA, "load"): mock.Mock(side_effect=GA.G0AuthorizationError("no authorization"))})
        self.assertEqual((rc, "REFUSED" in err), (2, True))
        rc, err = self.call(self.ARGV, {(GA, "frozen_problems"): mock.Mock(return_value=["g0_criteria_v5.json: changed"])})
        self.assertEqual((rc, "REFUSED" in err), (2, True))
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                GR.main(["--no-such-option"])
        self.assertEqual(cm.exception.code, 2)

    def test_the_marker_names_the_stage_and_the_run_directory_is_not_reused(self):
        rc, err = self.call(self.ARGV, {(GR, "prepare_dirs"): mock.Mock(side_effect=GR.DirError("evidence root is a symlink"))})
        self.assertEqual(rc, 3)
        self.assertIn("G0-DIR-ERROR", err)

    def test_no_code_path_of_main_returns_1(self):
        import ast
        tree = ast.parse(open(os.path.join(F.G0, "g0_run.py")).read())
        for fname in ("main", "_main"):
            fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fname)
            for n in ast.walk(fn):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant):
                    self.assertNotEqual(n.value.value, 1, "%s() returns the FAIL code at line %d" % (fname, n.lineno))


class TestC07MalformedReleaseRecords(unittest.TestCase):
    def ev(self, **changes):
        e = F.good_evidence()
        for path, val in changes.items():
            cur = e
            parts = path.split("__")
            for p in parts[:-1]:
                cur = cur[p]
            cur[parts[-1]] = val
        return e

    def good_entry(self):
        return {"mono_before": 1.75, "mono_after": 1.76, "result": "ok", "returned": 1, "errno": None, "error": None}

    def malformed_lists(self):
        g = self.good_entry
        out = {
            "two empty objects": [{}, {}],
            "two objects without times": [{"result": "ok"}, {"result": "ok"}],
            "string times": [dict(g(), mono_before="1.75"), dict(g(), mono_before="1.77")],
            "null times": [dict(g(), mono_before=None), dict(g(), mono_before=None)],
            "bool times": [dict(g(), mono_before=True), dict(g(), mono_before=False)],
            "nan times": [dict(g(), mono_before=float("nan")), dict(g(), mono_before=float("inf"))],
            "unknown result": [dict(g(), result="maybe"), dict(g(), result="maybe")],
            "missing result": [{k: v for k, v in g().items() if k != "result"}, {k: v for k, v in g().items() if k != "result"}],
            "returned as string": [dict(g(), returned="1"), dict(g(), returned="1")],
            "returned as bool": [dict(g(), returned=True), dict(g(), returned=True)],
            "errno as string": [dict(g(), result="error", returned=None, errno="32"), g()],
            "non-object item first": [3, g()],
            "non-object item second": [g(), None],
            "string items": ["ok", "ok"],
            "list in list": [[g()], [g()]],
        }
        return out

    def test_a_malformed_list_never_gives_a_c07_fail_or_a_run_fail(self):
        bad = []
        for name, rw in self.malformed_lists().items():
            for first_action in (1.8, None):
                e = self.ev(guard__release_writes=copy.deepcopy(rw), events__first_action_mono=first_action)
                r = judge(e)
                c7 = r["checks"]["G0-C07"]
                if c7["state"] != "UNEVALUABLE" or r["verdict"] == "FAIL" or "G0-C03" in r["fail_class"]:
                    bad.append((name, first_action, c7["state"], c7["rule"], r["verdict"], r["fail_class"]))
        self.assertEqual(bad, [])

    def test_release_writes_of_the_wrong_container_type_is_unevaluable(self):
        for val in (None, {}, "x", 3, {"mono_before": 1.0}, (1, 2)):
            e = self.ev(guard__release_writes=val)
            r = judge(e)
            self.assertEqual(r["checks"]["G0-C07"]["state"], "UNEVALUABLE", repr(val))
            self.assertNotEqual(r["verdict"], "FAIL", repr(val))

    def test_a_non_numeric_first_action_is_not_a_gate_pass_and_never_a_fail(self):
        for val in ("1.8", True, False, float("nan"), [1.8], {"a": 1}):
            e = self.ev(events__first_action_mono=val)
            r = judge(e)
            self.assertNotEqual(r["checks"]["G0-C07"]["state"], "FAIL", repr(val))
            self.assertNotEqual(r["verdict"], "FAIL", repr(val))

    def test_ledger_times_of_the_wrong_type_never_give_a_c07_fail(self):
        for bad in ("1.7", None, True, float("nan"), [1]):
            e = self.ev()
            e["reg_memory_records"][4]["mono"] = bad          # RELEASED
            e["reg"][4]["mono"] = bad
            r = judge(e)
            self.assertNotEqual(r["checks"]["G0-C07"]["state"], "FAIL", repr(bad))
            e = self.ev()
            e["reg_memory_records"][3]["mono"] = bad          # REGISTERED
            e["reg"][3]["mono"] = bad
            self.assertNotEqual(judge(e)["checks"]["G0-C07"]["state"], "FAIL", repr(bad))

    def test_malformed_fork_pids_do_not_make_c03_fail(self):
        base = F.case_evidence(next(c for c in F.load_v4_cases()["cases"] if c["id"] == "F3A-1"))      # F3a fires on a well-formed fork_pids
        self.assertEqual(GJ.check_c03(copy.deepcopy(base), CRIT)["state"], "FAIL")
        for bad in (["x"], [True], [1.5], "200", {"pid": 200}, [None]):
            e = copy.deepcopy(base)
            e["guard"]["fork_pids"] = bad
            self.assertNotEqual(GJ.check_c03(e, CRIT)["state"], "FAIL", repr(bad))

    def test_malformed_release_records_do_not_make_c03_f3_fire(self):
        base = F.case_evidence(next(c for c in F.load_v4_cases()["cases"] if c["id"] == "F3B-1"))      # F3b fires on a well-formed record
        self.assertEqual(GJ.check_c03(copy.deepcopy(base), CRIT)["rules_matched"][0], "C03-F3b")
        for name, rw in self.malformed_lists().items():
            e = copy.deepcopy(base)
            e["guard"]["release_writes"] = copy.deepcopy(rw)
            self.assertNotEqual(GJ.check_c03(e, CRIT)["state"], "FAIL", name)

    def test_negative_controls_well_formed_violations_still_fail(self):
        g = self.good_entry
        e = self.ev(guard__release_writes=[g(), dict(g(), mono_before=1.77, mono_after=1.78)])
        r = judge(e)
        self.assertEqual((r["checks"]["G0-C07"]["state"], r["checks"]["G0-C07"]["rule"], r["verdict"]), ("FAIL", "C07-F2", "FAIL"))
        e = self.ev(events__first_action_mono=1.7)
        r = judge(e)
        self.assertEqual((r["checks"]["G0-C07"]["rule"], r["verdict"]), ("C07-F3", "FAIL"))
        e = self.ev()
        e["reg_memory_records"][4]["mono"] = 1.9
        e["reg"][4]["mono"] = 1.9
        self.assertEqual(judge(e)["checks"]["G0-C07"]["rule"], "C07-F1")

    def test_a_well_formed_list_with_an_extra_unknown_key_is_still_well_formed(self):
        e = self.ev()
        e["guard"]["release_writes"][0]["note"] = "extra keys are ignored"
        self.assertEqual(judge(e)["checks"]["G0-C07"]["state"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
