"""Synthetic stdlib fixtures for data lineage/selection; no corpus/model access."""
import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("routing_data_fixtures", Path(__file__).with_name("data_prepare.py"))
data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data)


def fixture():
    rows, articles, roles, token_map = [], [], [], {}
    for i in range(60):
        title, body = f"= Article {i} =", f"article-body-{i} with text\n"
        heading = len(rows)
        rows.extend([title + "\n", body])
        key = data.sha(("source" + str(i)).encode())
        tokens = [(i * 500 + j) % 32768 for j in range(300)]
        token_map[body] = tokens
        articles.append({"source_article_key": key, "article_id": f"{i:064x}", "heading_row": heading,
                         "body_rows": [heading + 1], "text_sha256": data.sha(body.encode()), "full_token_count": 300,
                         "eligible": True, "title": title})
        for row, role in ((heading, "HEADING"), (heading + 1, "BODY")):
            roles.append({"row": row, "role": role, "source_article_key": key, "heading_row": heading})
    partition = {"articles": articles, "row_roles": roles, "rows_sha256": data.sha(data.canonical(rows))}
    corrected = {"samples": [{"index": i, **articles[i], "tokens": token_map[rows[2 * i + 1]][:257]} for i in range(32)]}
    old = {"samples": [{"index": i, "heading_row": 2 * i} for i in range(30)] + [
        {"index": 30, "heading_row": 64}, {"index": 31, "heading_row": 65}]}
    for sample in old["samples"]:
        source_heading = roles[sample["heading_row"]]["heading_row"]
        sample["tokens"] = list(token_map[rows[source_heading + 1]][:257])
    mapping = [{"old_index": s["index"], "old_heading_row": s["heading_row"],
                "reviewed_heading_row": roles[s["heading_row"]]["heading_row"],
                "source_article_key": roles[s["heading_row"]]["source_article_key"]} for s in old["samples"]]
    change = {"Status": "PASS", "Input": {"old_sha256": data.PINS["old_inputs"]["sha256"], "new_sha256": data.PINS["corrected_inputs"]["sha256"]},
              "Actual": {"old_sample_to_reviewed_source": mapping, "new_selected_heading_rows": [s["heading_row"] for s in corrected["samples"]],
                         "old_distinct_reviewed_sources": 31, "new_distinct_reviewed_sources": 32, "overlapping_reviewed_sources": 30}}
    return rows, partition, corrected, old, change, token_map


def select(f):
    rows, partition, corrected, old, change, tokens = f
    return data.select_payloads(rows, partition, corrected, old, change, lambda body: list(tokens[body]))


class DataTests(unittest.TestCase):
    def test_old_only_source_and_split_formula_are_excluded(self):
        """A formula-fragment window maps to its parent; old-only source stays excluded."""
        f = fixture()
        inputs, selection = select(f)
        self.assertEqual(selection["counts"]["excluded_union_sources"], 33)
        self.assertEqual(selection["old_sample_to_reviewed_source"][31]["reviewed_heading_row"], 64)
        self.assertIn(f[1]["articles"][32]["source_article_key"], selection["excluded_union_sources"])
        self.assertEqual([s["heading_row"] for s in inputs["samples"]], list(range(66, 98, 2)))

    def test_order_is_hash_ranking_not_partition_order(self):
        """Reordering partition articles cannot silently choose a different cohort."""
        f = fixture()
        expected = select(f)
        f[1]["articles"].reverse()
        self.assertEqual(select(f), expected)

    def test_exact_body_prefix_and_both_hash_encodings(self):
        """128 body tokens exclude heading content and bind JSON/int64 byte identities."""
        f = fixture()
        inputs, selection = select(f)
        sample = inputs["samples"][0]
        expected = f[5][f[0][67]][:128]
        self.assertEqual(sample["tokens"], expected)
        self.assertEqual(len(sample["tokens"]), 128)
        self.assertEqual(sample["input_ids_sha256"], data.sha(data.canonical(expected)))
        self.assertEqual(sample["raw_input_sha256"], data.sha(struct.pack("<" + "q" * 128, *expected)))
        self.assertEqual(inputs["seeds"], [3101, 3202])
        self.assertTrue(all("tokens" not in s and "title" not in s for s in selection["selected"]))
        self.assertTrue(all("labels" not in s and "target_ids" not in s for s in inputs["samples"]))

    def test_old_mapping_tamper_rejected(self):
        """A plausible source-count summary cannot replace the exact historical row map."""
        f = fixture()
        f[4]["Actual"]["old_sample_to_reviewed_source"][31]["reviewed_heading_row"] = 62
        with self.assertRaisesRegex(data.Stop, "selection-change"):
            select(f)

    def test_body_tamper_rejected(self):
        """Changed source body is rejected before tokenizing the selected prefix."""
        f = fixture()
        f[0][67] += "changed"
        with self.assertRaisesRegex(data.Stop, "body hash"):
            select(f)

    def test_invalid_token_or_token_count_rejected(self):
        """Boolean IDs and truncated tokenizer outputs are invalid token evidence."""
        for value in ([True] * 300, [1] * 299):
            f = fixture()
            f[5][f[0][67]] = value
            with self.assertRaisesRegex(data.Stop, "token coverage"):
                select(f)

    def test_duplicate_prefix_does_not_pass_distinct_source_gate(self):
        """Distinct article IDs alone cannot authorize duplicate input prefixes."""
        f = fixture()
        f[5][f[0][69]] = list(f[5][f[0][67]])
        with self.assertRaisesRegex(data.Stop, "Distinct selected prefix"):
            select(f)

    def test_historical_prefix_duplicate_rejected_even_for_new_source(self):
        """Source disjointness does not excuse reusing an old128-token model input."""
        f = fixture()
        f[5][f[0][67]][:128] = f[3]["samples"][0]["tokens"][:128]
        with self.assertRaisesRegex(data.Stop, "duplicates historical"):
            select(f)

    def test_missing_source_or_changed_historical_counts_rejected(self):
        """Coverage or exposure-count changes stop the frozen selection."""
        f = fixture()
        f[1]["articles"].pop()
        with self.assertRaisesRegex(data.Stop, "Exactly60"):
            select(f)
        f = fixture()
        f[3]["samples"][31]["heading_row"] = 66
        with self.assertRaisesRegex(data.Stop, "exclusion counts"):
            select(f)

    def test_exclusive_evidence_save_and_no_model_imports(self):
        """Existing evidence cannot be overwritten; helper import cannot load a model."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            data.save(path, {"first": True})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                data.save(path, {"second": True})
            self.assertEqual(path.read_bytes(), original)
        self.assertEqual(data.forbidden_imports(), [])


def test_id(test):
    ident = test.id()
    return "test_data." + ident.split(".", 1)[1] if ident.startswith("__main__.") else ident


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": test_id(test), "Purpose": test.shortDescription(), "Status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": test_id(test), "Status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": test_id(test), "Status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"id": test_id(test), "Status": "NOT TESTED", "detail": reason})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if not args.report.is_absolute() or args.report.exists():
        parser.error("report must be a new absolute path")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DataTests)
    expected = sorted(test_id(t) for t in suite)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded, failfast=True).run(suite)
    passed = result.wasSuccessful() and result.testsRun == len(expected) and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
    report = {"Purpose": "Synthetic data-lineage and selection fixtures only", "Environment": {"python": sys.version, "executable": sys.executable},
              "Input": {"planned_test_ids": expected}, "Expected": "All exact fixture tests pass; no model/corpus access",
              "Actual": {"test_ids": sorted(r["id"] for r in result.records), "planned": len(expected), "run": result.testsRun,
                         "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
                         "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
                         "tests": result.records, "unittest_output": stream.getvalue()}, "Status": "PASS" if passed else "FAIL"}
    data.save(args.report, report)
    print(stream.getvalue(), file=sys.stderr, end="")
    print(json.dumps({"Status": report["Status"], "tests": result.testsRun}), flush=True)
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
