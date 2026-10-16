"""ACT-002 exact four-cell decomposition unit tests (no upstream import)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import torch
from act_counterfactual_math import factorial_effects


class CounterfactualMathTests(unittest.TestCase):
    def setUp(self):
        self.labels = torch.tensor([[0, 1]])
        self.oo = torch.tensor([[[0.0, 0.2], [0.1, -0.1]]])

    def test_identical_four_cells_have_zero_effects(self):
        result = factorial_effects(self.oo, self.oo, self.oo, self.oo, self.labels)
        for key in ('total_deployed', 'direct_mechanism_same_original_weights',
                    'parameter_history_under_original_act', 'policy_parameter_interaction'):
            self.assertEqual(result['logits'][key]['max_abs'], 0.0)
        self.assertEqual(result['loss']['total_deployed_delta'], 0.0)

    def test_exact_three_part_decomposition_with_interaction(self):
        fo = self.oo + 0.5
        of = self.oo + 1.0
        ff = self.oo + 2.0
        r = factorial_effects(self.oo, fo, of, ff, self.labels)
        self.assertAlmostEqual(r['logits']['direct_mechanism_same_original_weights']['max_abs'],
                               .5, places=5)
        self.assertAlmostEqual(r['logits']['parameter_history_under_original_act']['max_abs'],
                               1.0, places=5)
        self.assertAlmostEqual(r['logits']['policy_parameter_interaction']['max_abs'],
                               .5, places=5)
        self.assertAlmostEqual(r['logits']['total_deployed']['max_abs'],
                               2.0, places=5)
        self.assertLess(r['logits']['reconstruction_max_abs_error'], 1e-6)

    def test_loss_effects_reconstruct_total(self):
        fo = self.oo + torch.tensor([[[.1, -.2], [.3, .1]]])
        of = self.oo + torch.tensor([[[.2, -.1], [-.1, .2]]])
        ff = self.oo + torch.tensor([[[-.4, .6], [.5, -.2]]])
        r = factorial_effects(self.oo, fo, of, ff, self.labels)
        effects = r['loss']
        self.assertAlmostEqual(
            effects['total_deployed_delta'],
            effects['direct_mechanism_same_original_weights_delta']
            + effects['parameter_history_under_original_act_delta']
            + effects['policy_parameter_interaction_delta'],
            places=6)
        self.assertLess(effects['reconstruction_abs_error'], 1e-7)

    def test_pure_history_when_act_policy_is_identical(self):
        different = self.oo + torch.tensor([[[.1, .2], [.2, -.3]]])
        r = factorial_effects(self.oo, self.oo, different, different, self.labels)
        self.assertEqual(r['logits']['direct_mechanism_same_original_weights']['max_abs'], 0)
        self.assertEqual(r['logits']['policy_parameter_interaction']['max_abs'], 0)
        self.assertGreater(r['logits']['parameter_history_under_original_act']['max_abs'], 0)

    def test_invalid_shapes_and_nonfinite_values(self):
        with self.assertRaises(ValueError):
            factorial_effects(self.oo, self.oo[:, :1], self.oo, self.oo, self.labels)
        with self.assertRaises(ValueError):
            factorial_effects(self.oo, self.oo, self.oo, self.oo, self.labels[:, :1])
        with self.assertRaises(ValueError):
            factorial_effects(self.oo, self.oo, self.oo, torch.full_like(self.oo, float('nan')), self.labels)


if __name__ == '__main__':
    unittest.main()
