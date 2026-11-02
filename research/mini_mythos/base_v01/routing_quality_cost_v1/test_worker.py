"""Synthetic stdlib-only controls; never imports Torch, weights or real data."""
import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import platform
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("quality_worker_under_test", ROOT / "run_quality.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerTests(unittest.TestCase):
    def test_opposite_balanced_pair_orders(self):
        """Each case changes first arm between rounds; each round is balanced."""
        for case in range(32):
            self.assertEqual(worker.arm_order(case, 0), tuple(reversed(worker.arm_order(case, 1))))
        for round_index in (0, 1):
            self.assertEqual(sum(worker.arm_order(c, round_index)[0] == "adaptive" for c in range(32)), 16)

    def test_exact_timing_plan_and_warmups(self):
        """The immutable plan gives2 unscored warmups and128 measured calls."""
        plan = worker.timing_plan()
        self.assertEqual(plan[:2], [("warmup", None, 0, 0, "fixed32"), ("warmup", None, 0, 1, "adaptive")])
        self.assertEqual(len(plan), 130)
        self.assertEqual(len(set(plan)), 130)
        for round_index in (0, 1):
            measured = [r for r in plan if r[0] == "timed" and r[1] == round_index]
            self.assertEqual(len(measured), 64)
            self.assertEqual({(r[2], r[4]) for r in measured}, {(c, a) for c in range(32) for a in ("adaptive", "fixed32")})

    def test_api_timer_encloses_complete_invocation(self):
        """Clock boundaries surround the complete callable without extra work."""
        events = []
        times = iter((5.0, 8.0))
        def clock():
            events.append("clock")
            return next(times)
        def invoke():
            events.extend(["validation", "core", "policy", "readout", "hashes"])
            return "output"
        cpu_times = iter((1.0, 3.0))
        result, elapsed, cpu_elapsed = worker.measure_api(invoke, clock, lambda: next(cpu_times))
        self.assertEqual((result, elapsed, cpu_elapsed), ("output", 3.0, 2.0))
        self.assertEqual(events, ["clock", "validation", "core", "policy", "readout", "hashes", "clock"])

    def test_timer_does_not_retry_failed_call(self):
        """A failed API invocation propagates immediately and is called once."""
        events = []
        def invoke():
            events.append("invoke")
            raise RuntimeError("fixture failure")
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            worker.measure_api(invoke, lambda: 1.0)
        self.assertEqual(events, ["invoke"])

    def fixture_reference(self):
        record = {"selected_depth": 16, "library_h0_sha256": "h0", "rng_before_sha256": "before",
                  "rng_after_sha256": "after", "input_sha256": "input", "tv_8_16": 0.003,
                  "library_counts": {"core_block_calls": 32, "head_calls": 2}}
        result = SimpleNamespace(selected_depth=16, h0_sha256="h0", rng_before_sha256="before",
                                 rng_after_sha256="after", prefix_sha256="input", tv_8_16=0.003,
                                 counts={"core_block_calls": 32, "head_calls": 2})
        return result, record

    def test_reference_accepts_exact_outputs_and_state(self):
        """The positive control accepts identical logits/state/counters."""
        result, record = self.fixture_reference()
        self.assertTrue(worker.reference_matches(result, record, b"fp32", b"fp32"))

    def test_reference_rejects_output_and_each_identity_drift(self):
        """Timing reuse cannot silently alter logits, routing, h0, RNG or counts."""
        result, record = self.fixture_reference()
        self.assertFalse(worker.reference_matches(result, record, b"fp32", b"fp33"))
        for name, value in {"selected_depth": 32, "h0_sha256": "other", "rng_before_sha256": "other",
                            "rng_after_sha256": "other", "prefix_sha256": "other", "tv_8_16": 0.004,
                            "counts": {"core_block_calls": 32, "head_calls": 3}}.items():
            changed = copy.deepcopy(result)
            setattr(changed, name, value)
            self.assertFalse(worker.reference_matches(changed, record, b"fp32", b"fp32"), name)

    def test_total_budget_includes_all_phases(self):
        """Warmups and timed calls count toward the hard194-forward ceiling."""
        def check(purpose, okay, actual, expected):
            if not okay:
                raise worker.Stop("FAIL", purpose)
        run = SimpleNamespace(calls_started=64, warmup_started=2, timed_started=127, check=check)
        worker.check_budget(run)
        self.assertEqual(worker.total_started(run), 193)
        run.timed_started = 128
        with self.assertRaises(worker.Stop):
            worker.check_budget(run)

    def test_invalid_case_and_round_rejected(self):
        """No out-of-budget case or third round can enter the schedule."""
        for case, round_index in ((-1, 0), (32, 0), (True, 0), (0, 2)):
            with self.assertRaises(ValueError):
                worker.arm_order(case, round_index)

    def test_import_is_stdlib_only(self):
        """Discovery/tests cannot initialize a numerical/model runtime."""
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("numpy", sys.modules)
        self.assertNotIn("parcae_lm", sys.modules)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if not args.report.is_absolute():
        parser.error("absolute report path required")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkerTests)
    planned = sorted(test.id().replace("__main__.", "test_worker.") for test in suite)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    failed = {test.id().replace("__main__.", "test_worker.") for test, _ in result.failures + result.errors}
    actual = {"test_ids": planned, "planned": len(planned), "run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
              "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
              "tests": [{"id": name, "Status": "FAIL" if name in failed else "PASS"} for name in planned],
              "unittest_output": output.getvalue()}
    report = {"Purpose": "Stdlib worker scheduling, budget, timing-boundary and identity controls",
              "Environment": {"python": sys.version, "platform": platform.platform(), "torch_imported": "torch" in sys.modules},
              "Input": {"worker_sha256": worker.info(ROOT / "run_quality.py")["sha256"], "planned_test_ids": planned},
              "Expected": "Exact declared coverage;0 failures/errors/skips; no numerical imports",
              "Actual": actual, "Status": "PASS" if result.wasSuccessful() and result.testsRun == len(planned)
              and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses else "FAIL"}
    with args.report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(output.getvalue())
    return 0 if report["Status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
