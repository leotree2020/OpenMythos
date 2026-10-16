"""Offline ACT step-metrics tests; upstream is exercised by the smoke and A/B scripts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import torch
from act_dynamics import summarize_act_pair, first_trace_event


class ACTDynamicsTests(unittest.TestCase):
    def test_mass_deficit_is_detected_at_budget(self):
        p = torch.full((1, 3), 0.4)
        original = [p, p]
        forced = [p, torch.ones_like(p)]
        metrics = summarize_act_pair(original, forced, threshold=0.99)
        self.assertAlmostEqual(metrics['original_act_mass_mean'], 0.8)
        self.assertAlmostEqual(metrics['original_act_mass_deficit_max'], 0.2)
        self.assertAlmostEqual(metrics['original_act_deficit_fraction'], 1.0)
        self.assertAlmostEqual(metrics['forced_act_mass_mean'], 1.0)
        self.assertEqual(metrics['original_actual_loops'], 2)
        self.assertEqual(metrics['forced_actual_loops'], 2)

    def test_early_halt_unchanged(self):
        p = torch.full((1, 2), 0.6)
        metrics = summarize_act_pair([p, p], [p, torch.ones_like(p)], 0.99)
        self.assertAlmostEqual(metrics['original_act_mass_mean'], 1.0)
        self.assertAlmostEqual(metrics['original_act_mass_deficit_max'], 0.0)
        self.assertAlmostEqual(metrics['original_act_deficit_fraction'], 0.0)

    def test_forced_mass_validation(self):
        p = torch.full((1, 2), 0.2)
        with self.assertRaisesRegex(RuntimeError, 'conserve ACT mass'):
            summarize_act_pair([p, p], [p, p], 0.99)

    def test_missing_probabilities_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize_act_pair([], [], 0.99)

    def test_first_event_threshold(self):
        trace = [{'step': 1, 'delta': 0.0},
                 {'step': 2, 'delta': 1e-8},
                 {'step': 3, 'delta': -0.0005}]
        self.assertEqual(first_trace_event(trace, 'delta'), 3)
        self.assertIsNone(first_trace_event(trace, 'delta', threshold=0.01))


if __name__ == '__main__':
    unittest.main()
