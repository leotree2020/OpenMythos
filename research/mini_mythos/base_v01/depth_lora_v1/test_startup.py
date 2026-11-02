"""Development-only launch and evidence-interface tests, no model or network."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
module_spec = importlib.util.spec_from_file_location("depth_lora_operator_fixture", ROOT / "execute_once.py")
operator = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(operator)


class StartupTests(unittest.TestCase):
    def test_new_branch_worktree_and_base_bound(self):
        self.assertEqual(operator.BRANCH, "mythos-depth-lora-cpu-v1")
        self.assertEqual(operator.EXPECTED_REPO.as_posix(), "/workspaces/mythos-depth-lora-cpu-v1")
        self.assertEqual(operator.BASE, "e24d053f482a96bcc2ab207c1be73e4c91fcd721")

    def test_run_and_data_locations_distinct(self):
        self.assertEqual(operator.RUN.as_posix(), "/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1")
        self.assertFalse(operator.INPUTS.is_relative_to(operator.RUN))
        self.assertFalse(operator.RUN.is_relative_to(operator.EXPECTED_REPO))

    def test_launch_uses_new_worker_isolated_cpu(self):
        command = operator.worker_command(Path("/spec.json"), Path("/worker"))
        self.assertEqual(command[:3], [operator.PYTHON, "-I", "-B"])
        self.assertEqual(Path(command[3]).name, "run_lora.py")
        self.assertEqual(command[4:], ["--spec", str(Path("/spec.json")), "--out", str(Path("/worker"))])
        self.assertNotIn("--reload", command)

    def test_reload_is_separate_explicit_interface(self):
        command = operator.worker_command(Path("/spec.json"), Path("/reload"), reload=True)
        self.assertEqual(command[-1], "--reload")
        self.assertEqual(command.count("--reload"), 1)
        self.assertEqual(command[7], str(Path("/reload")))

    def test_audit_uses_no_torch_data_environment(self):
        command = operator.audit_command(Path("/run"), Path("/audit.json"))
        self.assertEqual(command[:3], [operator.DATA_PYTHON, "-I", "-B"])
        self.assertEqual(Path(command[3]).name, "audit_lora.py")
        self.assertEqual(command[4:], ["--run", str(Path("/run")), "--output", str(Path("/audit.json"))])

    def test_source_containment_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(operator.package_path("source.py", root), root / "source.py")
            for name in ("../escape.py", str(root.parent / "absolute.py"), ""):
                with self.assertRaises(operator.Stop):
                    operator.package_path(name, root)

    def test_save_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            operator.save(path, {"Status": "BLOCKED"})
            with self.assertRaises(FileExistsError):
                operator.save(path, {"Status": "PASS"})
            self.assertEqual(json.loads(path.read_text()), {"Status": "BLOCKED"})

    def test_manifest_binds_size_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bytes.bin"
            path.write_bytes(b"original")
            original = operator.info(path)
            path.write_bytes(b"tampered")
            self.assertEqual(original["bytes"], operator.info(path)["bytes"])
            self.assertNotEqual(original["sha256"], operator.info(path)["sha256"])

    def test_test_inventory_requires_exact_full_coverage(self):
        actual = {"test_ids": ["a", "b"], "planned": 2, "run": 2, "failures": 0,
                  "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}
        self.assertTrue(operator.validate_test_report({"Status": "PASS", "Actual": actual}, ["b", "a"]))
        for key in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes"):
            self.assertFalse(operator.validate_test_report({"Status": "PASS", "Actual": {**actual, key: 1}}, ["a", "b"]))
        self.assertFalse(operator.validate_test_report({"Status": "PASS", "Actual": actual}, ["a", "a"]))
        self.assertFalse(operator.validate_test_report({"Status": "FAIL", "Actual": actual}, ["a", "b"]))
        self.assertFalse(operator.validate_test_report({"Status": "PASS", "Actual": {**actual, "run": 1}}, ["a", "b"]))

    def test_main_budget_exact_not_exit_only(self):
        actual = {"calls_started": 293, "calls_completed": 293, "train_steps": 128, "eval_rows": 160,
                  "zero_control_calls": 5, "model_loads": 1, "adapters_saved": 4, "reload_calls": 0}
        self.assertTrue(operator.validate_worker_coverage({"Status": "PASS", "Actual": actual}))
        for key in actual:
            self.assertFalse(operator.validate_worker_coverage({"Status": "PASS", "Actual": {**actual, key: actual[key] + 1}}))
        self.assertFalse(operator.validate_worker_coverage({"Status": "NOT TESTED", "Actual": actual}))

    def test_reload_budget_is_four_calls_no_training(self):
        actual = {"calls_started": 4, "calls_completed": 4, "train_steps": 0, "eval_rows": 0,
                  "zero_control_calls": 0, "model_loads": 1, "adapters_saved": 0, "reload_calls": 4}
        self.assertTrue(operator.validate_worker_coverage({"Status": "PASS", "Actual": actual}, reload=True))
        self.assertFalse(operator.validate_worker_coverage({"Status": "PASS", "Actual": actual}))
        self.assertFalse(operator.validate_worker_coverage({"Status": "PASS", "Actual": {**actual, "train_steps": 1}}, reload=True))

    def test_public_allowlist_excludes_binary_and_private_paths(self):
        for name in ("summary.json", "train.stdout", "audit.json", "worker/public/completion.json", "reload/public/checks.jsonl"):
            self.assertTrue(operator.public_path(name), name)
        for name in ("worker/private/logits.bin", "worker/private/model.pt", "worker/private/inputs.json",
                     "worker/public/logits.bin", "../escape.json", "/absolute.json", "data/inputs.json"):
            self.assertFalse(operator.public_path(name), name)

    def test_cpu_environment_no_network_dependency_mutation(self):
        self.assertEqual(operator.ENV["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(operator.ENV["OMP_NUM_THREADS"], "2")
        self.assertEqual(operator.ENV["MKL_NUM_THREADS"], "2")
        self.assertEqual(operator.ENV["HF_HUB_OFFLINE"], "1")
        self.assertEqual(operator.ENV["TRANSFORMERS_OFFLINE"], "1")
        self.assertEqual(operator.ENV["PYTHONDONTWRITEBYTECODE"], "1")

    def test_prior_results_and_upstream_pins_remain(self):
        self.assertEqual(operator.CHECKOUTS["/workspaces/mythos-parcae-pinned"], "69284c13746e849104f738d6d1a347b1f457df76")
        self.assertEqual(operator.CHECKOUTS["/workspaces/mythos-routing-quality-cost-cpu-v1"], operator.BASE)
        self.assertEqual(len(operator.OLD_RUNS), 4)
        self.assertEqual(operator.CONTROLLER_SHA, "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests)
    ids = sorted(test.id() for test in suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"Purpose": "Development-only isolated startup and preservation interface fixtures",
              "Environment": {"python": sys.version, "model_loaded": False, "network_used": False},
              "Input": "Synthetic files and frozen command constants; no target/model/data execution",
              "Expected": "All frozen test IDs run without failures, errors or skips",
              "Actual": {"test_ids": ids, "planned": len(ids), "run": result.testsRun,
                         "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
                         "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses)},
              "Status": "PASS" if result.wasSuccessful() and result.testsRun == len(ids) and not result.skipped else "FAIL"}
    if args.report:
        operator.save(args.report, report)
    else:
        print(json.dumps(report, indent=2))
    return 0 if report["Status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
