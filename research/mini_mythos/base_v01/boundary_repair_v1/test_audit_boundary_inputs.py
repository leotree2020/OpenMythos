"""Synthetic standard-library tests for the independent audit, never real data."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('audit_boundary_inputs.py')
SPEC = importlib.util.spec_from_file_location('independent_boundary_audit_under_test', SOURCE)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
FIXTURE_CORPUS = '1' * 64


def fixture_ledger(rows, accepted):
    decisions = []
    for index, row in enumerate(rows):
        if not (row.strip().startswith('=') or row.strip().endswith('=')):
            continue
        decisions.append({'row': index, 'row_sha256': hashlib.sha256(row.encode()).hexdigest(),
                          'title': row.strip(), 'decision': 'ACCEPT_TITLE' if index in accepted else 'BODY',
                          'reason': 'Explicit synthetic fixture classification; not an automatic syntax rule',
                          'prev_row_sha256': hashlib.sha256(rows[index - 1].encode()).hexdigest() if index else None,
                          'next_row_sha256': hashlib.sha256(rows[index + 1].encode()).hexdigest() if index + 1 < len(rows) else None,
                          'structural_context': {'before_blank': index == 0 or not rows[index - 1].strip(),
                                                 'after_blank': index + 1 == len(rows) or not rows[index + 1].strip()}})
    review = {'verdict': 'APPROVE', 'accepted_heading_rows': accepted, 'review_inventory_sha256': '2' * 64}
    return {'corpus_sha256': FIXTURE_CORPUS, 'row_count': len(rows),
            'rows_sha256': AUDIT.digest(AUDIT.canonical(rows)), 'decisions': decisions,
            'accepted_heading_rows': accepted,
            'semantic_review': {'root': dict(review), 'independent': dict(review, report_sha256='3' * 64),
                                'agreement': True, 'unresolved_rows': [], 'not_human_or_external_independent_review': True}}


class IndependentBoundaryAuditTest(unittest.TestCase):
    def test_isolated_formula_and_nested_section_remain_exact_source_body(self):
        rows = ['', ' = Alpha = \n', '', ' α  \r\n', '', ' = x + y = \n', '',
                ' == Details == \n', ' tail\t\n', '', '= Beta =\n', ' second body\n']
        ledger = fixture_ledger(rows, [1, 10])
        partition = AUDIT.independently_partition(rows, ledger, FIXTURE_CORPUS)
        AUDIT.validate_review(ledger, [1, 10])
        self.assertEqual(len(partition['articles']), 2)
        self.assertEqual(partition['articles'][0]['body_rows'], list(range(2, 10)))
        self.assertEqual(partition['row_roles'][5]['role'], 'BODY')
        self.assertEqual(partition['row_roles'][7]['role'], 'BODY')
        self.assertEqual([entry['row'] for entry in partition['row_roles']], list(range(len(rows))))
        expected_body = '\u03b1'  # Ensure Unicode/whitespace are not silently normalized.
        self.assertIn(expected_body, rows[3])
        self.assertEqual(partition['articles'][0]['text_sha256'], hashlib.sha256(''.join(rows[2:10]).encode()).hexdigest())
        self.assertEqual(partition['corpus_utf8_sha256'], hashlib.sha256(''.join(rows).encode()).hexdigest())

    def test_missing_candidate_and_changed_neighbor_evidence_block(self):
        rows = ['= Article =\n', 'body\n', '= formula =\n', 'tail\n']
        ledger = fixture_ledger(rows, [0])
        incomplete = copy.deepcopy(ledger)
        incomplete['decisions'].pop()
        with self.assertRaises(AUDIT.AuditStop) as caught:
            AUDIT.independently_partition(rows, incomplete, FIXTURE_CORPUS)
        self.assertEqual(caught.exception.status, 'BLOCKED')
        changed = copy.deepcopy(ledger)
        changed['decisions'][1]['prev_row_sha256'] = '0' * 64
        with self.assertRaises(AUDIT.AuditStop) as caught:
            AUDIT.independently_partition(rows, changed, FIXTURE_CORPUS)
        self.assertEqual(caught.exception.status, 'BLOCKED')

    def test_nonblank_leading_content_and_review_disagreement_block(self):
        rows = ['lost body\n', '= Title =\n', 'body\n']
        ledger = fixture_ledger(rows, [1])
        with self.assertRaises(AUDIT.AuditStop) as caught:
            AUDIT.independently_partition(rows, ledger, FIXTURE_CORPUS)
        self.assertEqual(caught.exception.status, 'BLOCKED')
        ledger['semantic_review']['independent']['accepted_heading_rows'] = []
        with self.assertRaises(AUDIT.AuditStop):
            AUDIT.validate_review(ledger, [1])

    def test_duplicate_body_sources_fail_even_with_distinct_titles(self):
        rows = ['= First =\n', 'same body\n', '= Second =\n', 'same body\n']
        with self.assertRaises(AUDIT.AuditStop) as caught:
            AUDIT.independently_partition(rows, fixture_ledger(rows, [0, 2]), FIXTURE_CORPUS)
        self.assertEqual(caught.exception.status, 'FAIL')

    def test_every_body_is_tokenized_and_fixed_window_shapes_are_preserved(self):
        rows = ['= First =\n', 'A' * 300, '= Second =\n', 'B' * 400, '= Short =\n', 'short']
        partition = AUDIT.independently_partition(rows, fixture_ledger(rows, [0, 2, 4]), FIXTURE_CORPUS)
        calls = []

        def encode(text):
            calls.append(text)
            return [ord(char) for char in text]

        samples, eligible = AUDIT.independently_tokenize(rows, partition, encode, selected_count=2)
        self.assertEqual(calls, ['A' * 300, 'B' * 400, 'short'])
        self.assertEqual(eligible, 2)
        self.assertEqual([article['eligible'] for article in partition['articles']], [True, True, False])
        for sample in samples:
            self.assertEqual(len(sample['tokens']), 257)
            token = 65 if sample['heading_row'] == 0 else 66
            self.assertEqual(sample['tokens'], [token] * 257)
            expected_192 = ('[' + ','.join([str(token)] * 192) + ']').encode()
            self.assertEqual(sample['scored_target_ids_sha256'], hashlib.sha256(expected_192).hexdigest())
            self.assertNotEqual(sample['target_ids_sha256'], sample['scored_target_ids_sha256'])

    def test_strict_json_rejects_duplicate_and_nonfinite_evidence(self):
        for value in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}'):
            with self.subTest(value=value), self.assertRaises(AUDIT.AuditStop):
                AUDIT.strict_json(value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
