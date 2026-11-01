"""Synthetic data-selection contract; no real corpus, tokenizer, Torch or model."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boundary_parser import BoundaryStop
from build_inputs import build_payloads, semantic_review_matches


CORPUS = "c" * 64


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def ledger_for(rows, accepted, body=()):
    return {"row_count": len(rows), "corpus_sha256": CORPUS, "rows_sha256": canonical_hash(rows),
            "decisions": [{"row": index, "row_sha256": hashlib.sha256(rows[index].encode("utf-8")).hexdigest(),
                           "title": rows[index].strip(), "decision": "ACCEPT_TITLE" if index in accepted else "BODY",
                           "reason": "Explicit synthetic fixture decision"} for index in sorted([*accepted, *body])]}


class FakeTokenizer:
    def __init__(self, by_text):
        self.by_text, self.calls = by_text, []
    def encode(self, text, add_special_tokens):
        if add_special_tokens is not False:
            raise AssertionError("Unexpected special token injection")
        self.calls.append((text, add_special_tokens))
        class Encoding:
            pass
        result = Encoding()
        result.ids = self.by_text[text][:]
        return result


class InputContract(unittest.TestCase):
    def test_production_semantic_gate_requires_two_matching_resolved_approvals(self):
        rows = ["= A =\n", "body\n"]
        ledger = ledger_for(rows, [0])
        self.assertFalse(semantic_review_matches(ledger))
        ledger["accepted_heading_rows"] = [0]
        ledger["semantic_review"] = {"root": {"verdict": "APPROVE", "accepted_heading_rows": [0]},
                                     "independent": {"verdict": "APPROVE", "accepted_heading_rows": [0]},
                                     "agreement": True, "unresolved_rows": [],
                                     "not_human_or_external_independent_review": True}
        self.assertTrue(semantic_review_matches(ledger))
        for field, value in (("verdict", "REQUEST CHANGES"), ("accepted_heading_rows", [1])):
            changed = json.loads(json.dumps(ledger))
            changed["semantic_review"]["independent"][field] = value
            self.assertFalse(semantic_review_matches(changed))
        ledger["semantic_review"]["unresolved_rows"] = [0]
        self.assertFalse(semantic_review_matches(ledger))

    def test_boundary_eligibility_rank_and_next_token_hashes(self):
        rows = ["= Z =\n", "longZ\n", "= A =\n", "longA\n", "= Short =\n", "short\n"]
        ledger = ledger_for(rows, [0, 2, 4])
        encodings = {"longZ\n": list(range(300)), "longA\n": list(range(1000, 1257)), "short\n": [7] * 256}
        tokenizer = FakeTokenizer(encodings)
        partition, inputs, counts = build_payloads(rows, ledger, CORPUS, tokenizer, selection_count=2)
        self.assertEqual([a["full_token_count"] for a in partition["articles"]], [300, 257, 256])
        self.assertEqual([a["eligible"] for a in partition["articles"]], [True, True, False])
        self.assertEqual(counts["eligible_article_count"], 2)
        expected = sorted([(hashlib.sha256((rows[i].strip() + "\n" + rows[i+1]).encode()).hexdigest(), i)
                           for i in [0, 2]])
        self.assertEqual([sample["heading_row"] for sample in inputs["samples"]], [i for _, i in expected])
        self.assertEqual(tokenizer.calls, [("longZ\n", False), ("longA\n", False), ("short\n", False)])
        for sample in inputs["samples"]:
            original = encodings[rows[sample["heading_row"] + 1]]
            self.assertEqual(sample["tokens"], original[:257])
            self.assertEqual(sample["input_ids_sha256"], canonical_hash(original[:256]))
            self.assertEqual(sample["target_ids_sha256"], canonical_hash(original[1:257]))
            self.assertEqual(sample["scored_target_ids_sha256"], canonical_hash(original[65:257]))
            self.assertEqual(sample["window_sha256"], canonical_hash(original[:257]))
        self.assertNotIn("parts", partition["articles"][0])
        self.assertNotIn("heading_text", partition["articles"][0])
        self.assertNotIn("leading_parts", partition)
        self.assertEqual(len(partition["all_row_sha256"]), 6)

    def test_formula_is_encoded_in_same_body_without_normalization_or_added_separator(self):
        rows = ["\n", "= Article =\r\n", " lead  \n", "\n", "= x =\n", "\n", "tail\t"]
        body = " lead  \n\n= x =\n\ntail\t"
        tokenizer = FakeTokenizer({body: list(range(257))})
        partition, inputs, _ = build_payloads(rows, ledger_for(rows, [1], [4]), CORPUS, tokenizer, selection_count=1)
        self.assertEqual(tokenizer.calls, [(body, False)])
        self.assertEqual(inputs["samples"][0]["body_rows"], [2, 3, 4, 5, 6])
        self.assertEqual(partition["leading_rows"], [0])

    def test_insufficient_sources_never_adapts_selection_count(self):
        rows = ["= A =\n", "body\n"]
        with self.assertRaises(BoundaryStop) as caught:
            build_payloads(rows, ledger_for(rows, [0]), CORPUS, FakeTokenizer({"body\n": list(range(257))}), selection_count=2)
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertEqual(caught.exception.actual, {"eligible": 1, "required": 2})

    def test_bad_token_id_and_duplicate_body_are_not_silently_selected(self):
        rows = ["= A =\n", "body\n"]
        for bad in (32768, -1, True, 1.5):
            with self.assertRaises(BoundaryStop) as caught:
                build_payloads(rows, ledger_for(rows, [0]), CORPUS,
                               FakeTokenizer({"body\n": [bad] + list(range(256))}), selection_count=1)
            self.assertEqual(caught.exception.status, "FAIL")
        repeated = ["= A =\n", "body\n", "= B =\n", "body\n"]
        tokenizer = FakeTokenizer({"body\n": list(range(257))})
        with self.assertRaises(BoundaryStop) as caught:
            build_payloads(repeated, ledger_for(repeated, [0, 2]), CORPUS, tokenizer, selection_count=1)
        self.assertEqual(caught.exception.reason, "Duplicate body content")
        self.assertEqual(tokenizer.calls, [])

    def test_repeat_builds_are_identical_and_do_not_mutate_input_rows_or_ledger(self):
        rows = ["= A =\n", "body\n"]
        ledger = ledger_for(rows, [0])
        before = json.dumps({"rows": rows, "ledger": ledger}, sort_keys=True)
        one = build_payloads(rows, ledger, CORPUS, FakeTokenizer({"body\n": list(range(257))}), selection_count=1)
        two = build_payloads(rows, ledger, CORPUS, FakeTokenizer({"body\n": list(range(257))}), selection_count=1)
        self.assertEqual(one, two)
        self.assertEqual(json.dumps({"rows": rows, "ledger": ledger}, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
