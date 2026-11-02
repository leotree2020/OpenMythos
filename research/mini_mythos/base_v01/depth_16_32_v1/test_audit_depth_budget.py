"""Development-only standard-library tests; no model, real corpus or run evidence.

Run with the frozen target interpreter after review. These tests establish helper
behavior only and cannot establish a language-model or formal-experiment result.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).with_name('audit_depth_budget.py')
SPEC = importlib.util.spec_from_file_location('depth_budget_auditor_under_test', SOURCE)
AUDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDITOR)
SUMMARY_SPEC = importlib.util.spec_from_file_location('depth_budget_summary_under_test', SOURCE.with_name('independent_summary.py'))
SUMMARY = importlib.util.module_from_spec(SUMMARY_SPEC)
SUMMARY_SPEC.loader.exec_module(SUMMARY)


class AuditHelpersTest(unittest.TestCase):
    def test_strict_json_rejects_duplicate_keys_and_nonfinite_literals(self):
        for value in ('{"a":1,"a":2}', '{"outer":{"a":1,"a":2}}',
                      '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AUDITOR.strict_json(value)
        self.assertEqual(AUDITOR.strict_json('{"a":[0,1.5,null]}'), {'a': [0, 1.5, None]})

    def test_nearest_rank_percentiles_use_endpoint_order_statistics(self):
        values = list(reversed(range(10000)))
        self.assertEqual(AUDITOR.nearest_rank(values, 0.025), 249)
        self.assertEqual(AUDITOR.nearest_rank(values, 0.975), 9749)
        self.assertEqual(AUDITOR.nearest_rank([7], 0.025), 7)
        self.assertEqual(AUDITOR.nearest_rank([2, 1], 0.5), 1)

    def test_known_constant_article_contrasts_preserve_sign_and_ppl(self):
        # Analytic oracle: equal per-article effects make every bootstrap draw
        # identical in exact arithmetic, irrespective of sampled article order.
        rows, samples = {}, []
        for article in range(32):
            samples.append({'article_id': str(article), 'title': 'synthetic',
                            'source_article_key': str(article), 'heading_row': article * 10})
            for replica in range(3):
                for depth, offset in ((8, 0.0), (16, -0.25), (32, 0.5)):
                    rows[(article, replica, depth)] = {
                        'audited_mean_nll': 2.0 + article / 100 + replica / 10 + offset,
                        'forward_seconds': depth / 10,
                    }
        result = AUDITOR.derive_statistics(rows, samples)
        for name, delta in (('primary_d16_minus_d8', -0.25), ('secondary_d32_minus_d8', 0.5)):
            contrast = result['paired_contrasts'][name]
            self.assertAlmostEqual(contrast['mean_delta_nll'], delta, places=12)
            for endpoint in contrast['exploratory_bootstrap_percentile_interval']:
                self.assertAlmostEqual(endpoint, delta, places=12)
            for replica_delta in contrast['per_replica_mean_delta_nll'].values():
                self.assertAlmostEqual(replica_delta, delta, places=12)
            self.assertEqual(contrast['article_sign_counts']['negative' if delta < 0 else 'positive'], 32)
        self.assertAlmostEqual(result['per_depth']['8']['mean_nll'], 2.255, places=12)
        self.assertAlmostEqual(result['per_depth']['8']['ppl'], math.exp(2.255), places=12)
        self.assertEqual(result['statistical_confirmation'], 'NOT TESTED')
        self.assertEqual(result['hardware_efficiency'], 'NOT TESTED')
        self.assertEqual([result['per_depth'][str(depth)]['prelude_core_coda_block_passes'] for depth in (8, 16, 32)], [20, 36, 68])

    def test_corrected_source_binding_rejects_same_source_and_heading_tampering(self):
        articles, samples, decisions = [], [], []
        for index, heading in enumerate((1, 20)):
            title = '= Synthetic %d =' % index
            key = AUDITOR.canonical_digest({'corpus_sha256': AUDITOR.CORPUS, 'heading_row': heading, 'title': title})
            article = {'source_article_key': key, 'heading_row': heading, 'title': title,
                       'article_id': str(index) * 64, 'body_rows': [heading + 1], 'text_sha256': 'a' * 64,
                       'full_token_count': 300}
            articles.append(article)
            samples.append(dict(article, index=index))
            decisions.append({'row': heading, 'decision': 'ACCEPT_TITLE'})
        partition = {'corpus_sha256': AUDITOR.CORPUS, 'rows_sha256': 'b' * 64, 'articles': articles}
        ledger = {'corpus_sha256': AUDITOR.CORPUS, 'rows_sha256': 'b' * 64,
                  'accepted_heading_rows': [1, 20], 'decisions': decisions}
        self.assertEqual(AUDITOR.corrected_source_errors(samples, partition, ledger), [])
        duplicated = [samples[0], dict(samples[0], index=1)]
        self.assertTrue(AUDITOR.corrected_source_errors(duplicated, partition, ledger))
        changed = [dict(samples[0], heading_row=2), samples[1]]
        self.assertTrue(AUDITOR.corrected_source_errors(changed, partition, ledger))

    def test_independent_summary_matches_analytic_effects_and_detects_changed_ci(self):
        # Power-of-two fractions provide a simple exact arithmetic oracle.
        with tempfile.TemporaryDirectory(prefix='depth-summary-development-') as directory:
            path = Path(directory) / 'rows.jsonl'
            samples, audit_rows = [], {}
            with path.open('w', encoding='utf-8') as handle:
                for article in range(32):
                    identity = hashlib.sha256(str(article).encode()).hexdigest()
                    samples.append({'article_id': identity, 'title': 'synthetic',
                                    'source_article_key': identity, 'heading_row': article * 10})
                    for replica in range(3):
                        for depth, effect in ((8, 0.0), (16, -0.25), (32, 0.5)):
                            mean = 2.0 + article / 32 + replica / 8 + effect
                            row = {'article_index': article, 'replica': replica, 'depth': depth,
                                   'article_id': identity, 'source_article_key': identity, 'heading_row': article * 10,
                                   'h0_sha256': '1' * 64, 'rng_before_sha256': '2' * 64, 'rng_after_sha256': '3' * 64,
                                   'nll': [mean] * 192, 'logsumexp': [mean + 1] * 192, 'target_logits': [1.0] * 192,
                                   'mean_nll': mean}
                            handle.write(json.dumps(row) + '\n')
                            audit_rows[(article, replica, depth)] = {'audited_mean_nll': mean, 'forward_seconds': 1.0}
            _, actual, errors, blockers = SUMMARY.inspect_rows(path)
            self.assertEqual(errors, [])
            self.assertEqual(blockers, [])
            audit_report = {'Status': 'PASS', 'Actual': {'scientific_results': AUDITOR.derive_statistics(audit_rows, samples)}}
            self.assertEqual(SUMMARY.compare_audit(actual, audit_report), [])
            contrast = actual['scientific_results']['paired_contrasts']['primary_d16_minus_d8']
            self.assertEqual(contrast['mean_delta_nll'], -0.25)
            self.assertEqual(contrast['exploratory_bootstrap_percentile_interval'], [-0.25, -0.25])
            audit_report['Actual']['scientific_results']['paired_contrasts']['primary_d16_minus_d8']['exploratory_bootstrap_percentile_interval'][0] = -0.5
            self.assertTrue(SUMMARY.compare_audit(actual, audit_report))

    def test_terminal_success_cannot_hide_error_or_cleanup_failure(self):
        for field, value in [('error', {'type': 'RuntimeError'}), ('cleanup_errors', ['cleanup failed'])]:
            with self.subTest(field=field):
                audit = AUDITOR.Audit(Path('unused'), Path('unused_inputs'))
                completion = {'status': 'PASS', 'error': None, 'cleanup_errors': []}
                completion[field] = value
                audit.check_terminal(completion)
                self.assertTrue(audit.failures)
        audit = AUDITOR.Audit(Path('unused'), Path('unused_inputs'))
        audit.check_terminal({'status': 'PASS', 'error': None, 'cleanup_errors': []})
        self.assertFalse(audit.failures or audit.blockers)

    def test_recorded_blocker_is_not_relabelled_as_implementation_failure(self):
        audit = AUDITOR.Audit(Path('unused'), Path('unused_inputs'))
        audit.check_terminal({'status': 'BLOCKED', 'error': {'message': 'resource unavailable'}, 'cleanup_errors': []})
        self.assertTrue(audit.blockers)
        self.assertFalse(audit.failures)
        missing = AUDITOR.Audit(Path('unused'), Path('unused_inputs'))
        missing.check_terminal({'status': 'PASS'})
        self.assertTrue(missing.blockers)

    def test_missing_run_evidence_never_produces_scientific_results(self):
        with tempfile.TemporaryDirectory(prefix='depth-audit-development-') as directory:
            root = Path(directory)
            run = root / 'empty_run'
            run.mkdir()
            samples = []
            for index in range(32):
                digest = hashlib.sha256(str(index).encode('ascii')).hexdigest()
                samples.append({'index': index, 'article_id': digest, 'text_sha256': digest,
                                'source_article_key': digest, 'heading_row': index * 10,
                                'title': 'synthetic fixture', 'tokens': [1] * 257,
                                'input_ids_sha256': AUDITOR.canonical_digest([1] * 256),
                                'target_ids_sha256': AUDITOR.canonical_digest([1] * 256),
                                'scored_target_ids_sha256': AUDITOR.canonical_digest([1] * 192)})
            inputs = root / 'synthetic_inputs.json'
            inputs.write_text(json.dumps({'samples': samples}), encoding='utf-8')
            original = inputs.read_bytes()
            audit = AUDITOR.Audit(run, inputs)
            audit.audit()
            self.assertTrue(audit.blockers)
            self.assertIsNone(audit.actual.get('scientific_results'))
            self.assertEqual(inputs.read_bytes(), original)
            self.assertEqual(list(run.iterdir()), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
