"""Pure startup/interface fixtures; no Torch, model, source, target, or network."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("math_operator_fixture", ROOT / "execute_once.py")
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)


class StartupTests(unittest.TestCase):
    def test_stage_order_and_isolated_source_pinned_cli(self):
        self.assertEqual(operator.TESTS, ("test_moda.py", "test_moe.py"))
        command = operator.worker_command("test_moda.py", Path("/report.json"))
        self.assertEqual(command[:3], [operator.PYTHON, "-I", "-B"])
        self.assertEqual(Path(command[3]).name, "test_moda.py")
        self.assertEqual(command[4:], ["--source", str(operator.SOURCE), "--source-sha256", operator.SOURCE_SHA256,
                                      "--report", str(Path("/report.json"))])
        self.assertNotIn("--development", command)
        with self.assertRaises(ValueError):
            operator.worker_command("run_base.py", Path("/report.json"))

    def test_acceptance_requires_exact_pass_rows_not_exit(self):
        ids = ["a", "b"]
        report = {"Status": "PASS", "Environment": {"development_only": False},
                  "Input": {"source_sha256": operator.SOURCE_SHA256},
                  "Actual": {"test_ids": ids, "planned": 2, "run": 2,
                             "counts": {"PASS": 2, "FAIL": 0, "BLOCKED": 0, "NOT TESTED": 0},
                             "tests": [{"Input": {"test_id": i}, "Status": "PASS"} for i in ids]}}
        self.assertTrue(operator.validate_report(report, ids))
        for change in ("duplicate", "not_run", "failure", "development", "wrong_source"):
            bad = copy.deepcopy(report)
            if change == "duplicate": bad["Actual"]["tests"][1]["Input"]["test_id"] = "a"
            if change == "not_run": bad["Actual"]["run"] = 1
            if change == "failure": bad["Actual"]["tests"][1]["Status"] = "FAIL"
            if change == "development": bad["Environment"]["development_only"] = True
            if change == "wrong_source": bad["Input"]["source_sha256"] = "0" * 64
            self.assertFalse(operator.validate_report(bad, ids), change)
        startup_ids = ["a", "b", "c", "d"]
        startup = {"Status": "PASS", "Actual": {"test_ids": startup_ids, "planned": 4, "run": 4,
                    "failures": 0, "errors": 0, "skipped": 0}}
        self.assertTrue(operator.validate_startup_report(startup, startup_ids))
        startup["Actual"]["skipped"] = 1
        self.assertFalse(operator.validate_startup_report(startup, startup_ids))

    def test_new_paths_budget_and_no_overwrite(self):
        self.assertEqual(operator.BRANCH, "mythos-moda-moe-math-cpu-v1")
        self.assertEqual(operator.EXPECTED_REPO.as_posix(), "/workspaces/mythos-moda-moe-math-cpu-v1")
        self.assertFalse(operator.RUN.is_relative_to(operator.LOOP_RUN))
        self.assertEqual(operator.RECORD_BUDGET + operator.RESERVE, 301989888)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "evidence.json"
            operator.save(p, {"Status": "BLOCKED"})
            with self.assertRaises(FileExistsError):
                operator.save(p, {"Status": "PASS"})
            self.assertEqual(json.loads(p.read_text()), {"Status": "BLOCKED"})

    def test_source_containment_and_cpu_environment(self):
        self.assertEqual(operator.package_path("test_moda.py"), ROOT / "test_moda.py")
        for name in ("", "../outside.py", str(ROOT.parent / "outside.py")):
            with self.assertRaises(operator.Stop):
                operator.package_path(name)
        self.assertEqual(operator.ENV["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(operator.ENV["OMP_NUM_THREADS"], "2")
        self.assertEqual(operator.ENV["MKL_NUM_THREADS"], "2")
        self.assertEqual(operator.ENV["PYTHONDONTWRITEBYTECODE"], "1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests)
    ids = sorted(t.id() for t in suite)
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    report = {"Purpose": "Development-only math startup/interface fixtures", "Environment": sys.version,
        "Input": "Synthetic report/path objects only; no Torch or real source execution",
        "Expected": "All4 frozen fixtures complete without failures/errors/skips",
        "Actual": {"test_ids": ids, "planned": len(ids), "run": result.testsRun,
                   "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
        "Status": "PASS" if result.wasSuccessful() and result.testsRun == len(ids) and not result.skipped else "FAIL"}
    operator.save(args.report, report)
    return 0 if report["Status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
