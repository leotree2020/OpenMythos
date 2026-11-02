"""Standard-library synthetic fixtures only: no model, torch or target inputs."""
import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location("routing_helper_fixtures_module", Path(__file__).with_name("run_routing.py"))
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


def valid_inputs():
    samples = []
    for index in range(16):
        tokens = list(range(index * 128, index * 128 + 128))
        samples.append({"index": index, "tokens": tokens, "source_article_key": f"key{index:02d}",
                        "article_id": f"id{index:02d}", "heading_row": index * 10,
                        "input_ids_sha256": routing.sha(routing.canonical(tokens)),
                        "raw_input_sha256": routing.sha(struct.pack("<" + "q" * 128, *tokens))})
    return {"samples": samples, "context_tokens": 128, "seeds": [3101, 3202]}


def records(depth=32):
    return [{"article_index": index, "source_article_key": f"key{index:02d}", "seed": seed,
             "selected_depth": depth, "tv_8_16": .01 if depth == 16 else .1}
            for index in range(16) for seed in (3101, 3202)]


class Helpers(unittest.TestCase):
    def test_exact128prefix_and32call_plan(self):
        """Valid input schema creates exactly article-major two-seed32call order."""
        payload = valid_inputs()
        samples = routing.validate_inputs(payload)
        self.assertEqual(len(routing.plan(samples)), 32)
        self.assertEqual(routing.plan(samples), [(i, s) for i in range(16) for s in (3101, 3202)])

    def test_boolean_token_and_wrong_prefix_hash_rejected(self):
        """Booleans cannot masquerade as token IDs and metadata cannot hide edited IDs."""
        for mutate in (lambda p: p["samples"][0]["tokens"].__setitem__(0, True),
                       lambda p: p["samples"][0]["tokens"].__setitem__(0, 4)):
            payload = valid_inputs()
            mutate(payload)
            with self.assertRaises(routing.Stop) as raised:
                routing.validate_inputs(payload)
            self.assertEqual(raised.exception.status, "FAIL")

    def test_duplicate_source_and_duplicate_prefix_rejected(self):
        """Distinct index labels cannot hide duplicated articles or input prefixes."""
        for key in ("source_article_key", "article_id", "heading_row"):
            payload = valid_inputs()
            payload["samples"][1][key] = payload["samples"][0][key]
            with self.assertRaises(routing.Stop):
                routing.validate_inputs(payload)
        payload = valid_inputs()
        for key in ("tokens", "input_ids_sha256", "raw_input_sha256"):
            payload["samples"][1][key] = copy.deepcopy(payload["samples"][0][key])
        with self.assertRaises(routing.Stop):
            routing.validate_inputs(payload)

    def test_wrong_order_length_seed_and_count_rejected(self):
        """No sample, prefix length or initialization seed can drift after freezing."""
        mutations = [lambda p: p.__setitem__("context_tokens", 64), lambda p: p.__setitem__("seeds", [3101, 7]),
                     lambda p: p["samples"].pop(), lambda p: p["samples"].reverse()]
        for mutate in mutations:
            payload = valid_inputs()
            mutate(payload)
            with self.assertRaises(routing.Stop):
                routing.validate_inputs(payload)

    def test_all32_is_no_early_exit_not_implementation_failure(self):
        """A fully valid all32 outcome must preserve a negative routing finding."""
        result = routing.summarize_routing(records(32), True)
        self.assertEqual(result["early_exit_observed"], "NO")
        self.assertEqual(result["feasibility"], "NO_EARLY_EXIT_IN_THIS_SAMPLE")
        self.assertEqual(result["selected_depth_counts"], {"16": 0, "32": 32})
        self.assertEqual(result["quality_improvement"], "NOT TESTED")

    def test_two_seed_article_summary_and_exact_threshold(self):
        """Frozen <=0.01 predicate and article-level stability are counted separately."""
        rows = records(32)
        for i in (0, 1, 2):
            rows[i].update(selected_depth=16, tv_8_16=.01)
        result = routing.summarize_routing(rows, True)
        self.assertEqual(result["selected_depth_counts"], {"16": 3, "32": 29})
        self.assertEqual(result["article_both_seeds_early"], 1)
        self.assertEqual(result["article_any_seed_early"], 2)
        self.assertEqual(result["early_exit_fraction"], 3 / 32)
        rows[0]["tv_8_16"] = .010000000000001
        with self.assertRaises(routing.Stop):
            routing.summarize_routing(rows, True)

    def test_incomplete_summary_never_interpreted_as_no_early_exit(self):
        """Partial execution cannot support a complete negative feasibility conclusion."""
        partial = routing.summarize_routing(records()[:10], False)
        self.assertEqual(partial["early_exit_observed"], "NOT TESTED")
        with self.assertRaises(routing.Stop):
            routing.summarize_routing(records()[:-1], True)

    def test_nonfinite_or_out_of_order_routing_rejected(self):
        """Recorded decisions must have finite TV and exact preregistered ordering."""
        for value in (float("nan"), float("inf"), -0.1, 1.1):
            rows = records()
            rows[0]["tv_8_16"] = value
            with self.assertRaises(routing.Stop):
                routing.summarize_routing(rows, True)
        rows = records()
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(routing.Stop):
            routing.summarize_routing(rows, True)

    def test_wrong_pinned_import_rejected_without_execution(self):
        """Source identity is checked before potentially executable module contents."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unsafe.py"
            path.write_text("raise RuntimeError('MUST NOT EXECUTE')\n", encoding="utf-8")
            with self.assertRaises(routing.Stop) as raised:
                routing.pinned_import("must_not_execute", path, "0" * 64)
            self.assertEqual(raised.exception.status, "FAIL")
            self.assertNotIn("must_not_execute", sys.modules)

    def test_seal_incomplete_cannot_claim_pass_and_manifest_binds_summary(self):
        """Zero calls cannot seal asPASS; final completion bytes are in both manifests."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public, private = root / "public", root / "private"
            public.mkdir()
            private.mkdir()
            run = SimpleNamespace(out=root, public=public, private=private, spec={}, environment={"fixture": True},
                checks=(public / "checks.jsonl").open("x"), rows=(public / "calls.jsonl").open("x"),
                save_errors=[], calls_started=0, calls_completed=0, groups_completed=0, loader_attempts=0,
                loader_returns=0, routing_records=[], preservation="NOT TESTED", check_counts={"PASS": 0, "FAIL": 0, "BLOCKED": 0})
            self.assertEqual(routing.seal(run, "PASS", None, time.monotonic()), 2)
            summary = json.loads((public / "completion.json").read_text())
            self.assertEqual(summary["Status"], "BLOCKED")
            self.assertEqual(summary["Actual"]["routing"]["early_exit_observed"], "NOT TESTED")
            full = json.loads((root / "FULL_MANIFEST.json").read_text())
            self.assertEqual(full["entries"]["public/completion.json"], routing.info(public / "completion.json"))
            with self.assertRaises(FileExistsError):
                routing.save(public / "completion.json", {"Status": "PASS"})

    def test_module_import_does_not_import_numerical_stack(self):
        """Import and helper fixtures never load Torch or native model modules."""
        for name in ("torch", "parcae_lm", "receval"):
            self.assertNotIn(name, sys.modules)


def canonical_id(test):
    ident = test.id()
    return "test_routing_helpers." + ident.split(".", 1)[1] if ident.startswith("__main__.") else ident


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
        parser.error("report exists; will not overwrite")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Helpers)
    expected = sorted(canonical_id(t) for t in suite)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded, failfast=True).run(suite)
    okay = result.wasSuccessful() and result.testsRun == len(expected) and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
    report = {"Purpose": "Routing helper developer fixtures only; no model", "Environment": {"python": sys.version, "executable": sys.executable},
        "Input": {"planned_test_ids": expected}, "Expected": "Exact helper inventory PASS without skips",
        "Actual": {"test_ids": sorted(r["id"] for r in result.records), "planned": len(expected), "run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
            "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
            "tests": result.records, "unittest_output": stream.getvalue()}, "Status": "PASS" if okay else "FAIL"}
    routing.save(args.report, report)
    print(stream.getvalue(), file=sys.stderr, end="")
    print(json.dumps({"Status": report["Status"], "tests": result.testsRun, "report": str(args.report)}), flush=True)
    return 0 if okay else 2


if __name__ == "__main__":
    sys.exit(main())
