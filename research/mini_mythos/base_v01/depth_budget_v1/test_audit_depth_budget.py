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
            samples.append({'article_id': str(article), 'title': 'synthetic'})
            for replica in range(3):
                for depth, offset in ((2, 0.5), (4, -0.25), (8, 0.0)):
                    rows[(article, replica, depth)] = {
                        'audited_mean_nll': 2.0 + article / 100 + replica / 10 + offset,
                        'forward_seconds': depth / 10,
                    }
        result = AUDITOR.derive_statistics(rows, samples)
        for name, delta in (('primary_d4_minus_d8', -0.25), ('secondary_d2_minus_d8', 0.5)):
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
