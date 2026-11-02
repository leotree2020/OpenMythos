"""Standard-library fixtures only. No torch import, weights, or model calls."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_smoke as smoke


class Helpers(unittest.TestCase):
    def test_exact_matrix_order(self):
        """Six fixed groups and nine calls each precede the single causal call."""
        self.assertEqual(smoke.group_plan(), [(1, 3101), (1, 3202), (16, 3101), (16, 3202), (64, 3101), (64, 3202)])
        self.assertEqual(smoke.call_plan(), [("native", 8), ("native", 16), ("native", 32),
                         ("fixed", 8), ("fixed", 16), ("fixed", 32), ("diagnostic", None),
                         ("adaptive", None), ("adaptive_repeat", None)])
        self.assertEqual(len(smoke.group_plan()) * len(smoke.call_plan()) + 1, 55)

    def test_complete_module_count_formula(self):
        """Adapter/core/readout/value embedding counts include extra readouts."""
        for depth, readouts, blocks in ((8, 1, 20), (16, 1, 36), (32, 1, 68), (16, 2, 38), (32, 3, 72)):
            c = smoke.expected_counts(depth, readouts)
            self.assertEqual(c["adapter"], depth)
            self.assertEqual(c["core"], 2 * depth)
            self.assertEqual(c["prelude"] + c["core"] + c["coda"], blocks)
            self.assertEqual(c["value_embedding"], 1 + depth + readouts)
            self.assertEqual(c["projection"], readouts)
            self.assertEqual(c["head"], readouts)
            self.assertEqual(c["final_norm"], readouts)
            self.assertEqual(c["embedding"], 1)

    def test_canonical_hash_and_nonfinite_rejection(self):
        """Metadata hashes are canonical and never silently serialize NaN/Infinity."""
        self.assertEqual(smoke.json_hash({"a": 1, "b": 2}), smoke.json_hash({"b": 2, "a": 1}))
        for bad in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                smoke.canonical({"bad": bad})

    def test_exclusive_save_preserves_existing_bytes(self):
        """Evidence creation cannot overwrite a previous attempt's file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            smoke.save(path, {"first": True})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                smoke.save(path, {"first": False})
            self.assertEqual(path.read_bytes(), before)

    def test_import_rejects_wrong_source_hash_before_execution(self):
        """A source pin mismatch blocks importing arbitrary helper code."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "helper.py"
            path.write_text("raise RuntimeError('must never execute')\n", encoding="utf-8")
            with self.assertRaises(smoke.Stop) as caught:
                smoke.load_module("smoke_invalid_helper", path, "0" * 64)
            self.assertEqual(caught.exception.status, "FAIL")
            self.assertNotIn("smoke_invalid_helper", sys.modules)

    def test_sealed_manifest_covers_all_raw_files_and_summary(self):
        """Complete fixture sealing binds public/private bytes and summary separately."""
        with tempfile.TemporaryDirectory() as tmp:
            run = smoke.Run({}, Path(tmp))
            (run.private / "sample.bin").write_bytes(b"\x00\x01fixture")
            run.calls_started = run.calls_completed = 55
            run.groups_completed = 6
            run.preservation = "PASS"
            code = smoke.seal(run, "PASS", None, 0.0)
            self.assertEqual(code, 0)
            manifest = json.loads((Path(tmp) / "FULL_MANIFEST.json").read_text())
            actual = {str(p.relative_to(tmp)).replace("\\", "/") for p in Path(tmp).rglob("*") if p.is_file()}
            self.assertEqual(actual, set(manifest["entries"]) | set(manifest["excluded"]))
            for name, expected in manifest["entries"].items():
                self.assertEqual(smoke.info(Path(tmp) / name), expected)
            public = json.loads((run.public / "GIT_BUNDLE_MANIFEST.json").read_text())
            self.assertTrue(all(name.startswith("public/") for name in public["entries"]))
            summary = json.loads((run.public / "completion.json").read_text())
            self.assertEqual(summary["quality"], "NOT TESTED")
            self.assertEqual(summary["training"], "NOT TESTED")

    def test_incomplete_run_cannot_be_sealed_as_pass(self):
        """A caller's PASS cannot turn incomplete call coverage into full acceptance."""
        with tempfile.TemporaryDirectory() as tmp:
            run = smoke.Run({}, Path(tmp))
            run.preservation = "NOT TESTED"
            self.assertEqual(smoke.seal(run, "PASS", None, 0.0), 2)
            summary = json.loads((run.public / "completion.json").read_text())
            self.assertEqual(summary["Status"], "BLOCKED")
            self.assertFalse(summary["complete_coverage"])

    def test_confirmed_change_not_masked_by_unreadable_file(self):
        """Post-stop custody preserves a proven FAIL even alongside an unreadable path."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = smoke.Run({}, base)
            path = base / "original.bin"
            path.write_bytes(b"before")
            run.protected_before = {str(path): smoke.info(path), str(base / "missing.bin"): {"bytes": 1, "sha256": "0" * 64}}
            path.write_bytes(b"after")
            try:
                self.assertEqual(smoke.preserve(run), "FAIL")
                record = json.loads((run.public / "preservation.json").read_text())
                self.assertEqual(record["Status"], "FAIL")
                self.assertIn(str(path), record["Actual"]["proven_changes"])
                self.assertTrue(record["Actual"]["read_errors"])
            finally:
                run.checks.close()
                run.rows.close()

    def test_worker_import_has_no_numerical_module(self):
        """Importing the worker/helpers cannot start torch or model construction."""
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("parcae_lm", sys.modules)


def canonical_id(test):
    ident = test.id()
    return "test_smoke_helpers." + ident.split(".", 1)[1] if ident.startswith("__main__.") else ident


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "NOT TESTED", "detail": reason})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("report already exists; will not overwrite")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Helpers)
    planned_ids = sorted(canonical_id(test) for test in suite)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded, failfast=True).run(suite)
    okay = (result.wasSuccessful() and result.testsRun == len(planned_ids) and not result.skipped
            and not result.expectedFailures and not result.unexpectedSuccesses)
    report = {"Purpose": "New smoke helper fixtures only, no model", "Environment": {"python": sys.version, "executable": sys.executable},
              "Input": {"planned_test_ids": planned_ids}, "Expected": "all exact helper tests PASS without skips",
              "Actual": {"test_ids": sorted(record["id"] for record in result.records), "planned": len(planned_ids),
                         "run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                         "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
                         "unexpected_successes": len(result.unexpectedSuccesses), "tests": result.records,
                         "unittest_output": stream.getvalue()}, "Status": "PASS" if okay else "FAIL"}
    smoke.save(args.report, report)
    print(stream.getvalue(), file=sys.stderr, end="")
    print(json.dumps({"Status": report["Status"], "tests": result.testsRun, "report": str(args.report)}), flush=True)
    return 0 if okay else 2


if __name__ == "__main__":
    sys.exit(main())
