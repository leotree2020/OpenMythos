"""Offline tests for the *diagnostic oracle*; do not imply upstream passed."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import torch
from act_math import act_accounting


class ACTAccountingTests(unittest.TestCase):
    def test_exhausted_depth_loses_probability_mass(self):
        p = torch.full((2, 1, 3), .10)
        baseline = act_accounting(p, threshold=.99)
        self.assertTrue(torch.allclose(baseline.probability_mass, torch.full((1, 3), .20)))
        forced = act_accounting(p, threshold=.99, force_final_remainder=True)
        self.assertTrue(torch.allclose(forced.probability_mass, torch.ones(1, 3)))
        self.assertTrue(torch.allclose(forced.weights[-1], torch.full((1, 3), .9)))

    def test_crossing_threshold_assigns_remainder_once(self):
        p = torch.full((5, 1, 2), .6)
        for force in (False, True):
            result = act_accounting(p, threshold=.99, force_final_remainder=force)
            self.assertTrue(torch.allclose(result.probability_mass, torch.ones(1, 2)))
            self.assertTrue(torch.allclose(result.weights[0], torch.full((1, 2), .6)))
            self.assertTrue(torch.allclose(result.weights[1], torch.full((1, 2), .4)))
            self.assertTrue(torch.equal(result.weights[2:], torch.zeros_like(result.weights[2:])))

    def test_position_dependent_probabilities(self):
        p = torch.tensor([[[.1, .6]], [[.2, .6]], [[.2, .6]]])
        result = act_accounting(p)
        self.assertAlmostEqual(result.probability_mass[0, 0].item(), .5, places=5)
        self.assertAlmostEqual(result.probability_mass[0, 1].item(), 1., places=5)

    def test_reject_invalid_inputs(self):
        for probs in (torch.tensor([.3]), torch.ones(2, 2), torch.full((2, 1, 1), float('nan')),
                      torch.full((2, 1, 1), 1.01)):
            with self.assertRaises(ValueError):
                act_accounting(probs)

    def test_low_precision_input_float32_bookkeeping(self):
        p = torch.full((3, 2, 2), .2, dtype=torch.bfloat16)
        output = act_accounting(p, force_final_remainder=True)
        self.assertEqual(output.probability_mass.dtype, torch.float32)
        self.assertTrue(torch.allclose(output.probability_mass, torch.ones(2, 2)))


if __name__ == '__main__':
    unittest.main()
