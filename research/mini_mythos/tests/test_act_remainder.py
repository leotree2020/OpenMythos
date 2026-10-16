"""Offline tests for hook semantics; they do NOT test upstream model quality."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import torch
from act_remainder import act_probability_hook


class Tiny(torch.nn.Module):
    def __init__(self, probability):
        super().__init__()
        self.act = torch.nn.Sequential(torch.nn.Linear(1, 1), torch.nn.Sigmoid())
        with torch.no_grad():
            self.act[0].weight.zero_()
            self.act[0].bias.fill_(torch.logit(torch.tensor(probability)))
        self.threshold = 0.99

    def forward(self, x, depth):
        cumulative = torch.zeros_like(x[..., 0])
        halted = torch.zeros_like(cumulative, dtype=torch.bool)
        mass = torch.zeros_like(cumulative)
        for _ in range(depth):
            p = self.act(x).squeeze(-1)
            running = ~halted
            remainder = (1.0 - cumulative).clamp(min=0)
            weight = torch.where(cumulative + p >= self.threshold, remainder, p)
            mass = mass + weight * running.float()
            cumulative = cumulative + p * running.float()
            halted = halted | (cumulative >= self.threshold)
            if halted.all():
                break
        return mass


class ToyModel(torch.nn.Module):
    def __init__(self, probability):
        super().__init__()
        self.recurrent = Tiny(probability)

    def forward(self, x, depth):
        return self.recurrent(x, depth)


class FinalRemainderHookTests(unittest.TestCase):
    def setUp(self):
        self.x = torch.zeros(2, 3, 1)

    def test_forces_final_remainder_only_at_budget(self):
        m = ToyModel(0.2)
        self.assertTrue(torch.allclose(m(self.x, 2), torch.full((2, 3), .4)))
        with act_probability_hook(m, 2, force_final=True):
            self.assertTrue(torch.allclose(m(self.x, 2), torch.ones(2, 3)))
        self.assertTrue(torch.allclose(m(self.x, 2), torch.full((2, 3), .4)))

    def test_early_halt_preserved(self):
        m = ToyModel(0.6)
        a = m(self.x, 4)
        with act_probability_hook(m, 4, force_final=True):
            b = m(self.x, 4)
        self.assertTrue(torch.allclose(a, b))
        self.assertTrue(torch.allclose(b, torch.ones(2, 3)))

    def test_hook_is_removed_on_exception(self):
        m = ToyModel(0.2)
        with self.assertRaisesRegex(RuntimeError, 'test exception'):
            with act_probability_hook(m, 1, force_final=True):
                raise RuntimeError('test exception')
        self.assertEqual(len(m.recurrent.act._forward_hooks), 0)

    def test_gradients_exist_and_match_final_remainder(self):
        m = ToyModel(0.2)
        with act_probability_hook(m, 2, force_final=True):
            mass = m(self.x, 2)
        mass.sum().backward()
        # Completing the remaining mass makes this toy output constant.
        self.assertTrue(torch.allclose(mass, torch.ones(2, 3)))
        grad = m.recurrent.act[0].bias.grad
        self.assertIsNotNone(grad)
        self.assertTrue(torch.isfinite(grad).all())
        self.assertTrue(torch.allclose(grad, torch.zeros_like(grad), atol=1e-6))

    def test_invalid_budget(self):
        with self.assertRaises(ValueError):
            with act_probability_hook(ToyModel(.2), 0, force_final=True):
                pass


if __name__ == '__main__':
    unittest.main()
