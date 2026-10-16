"""Small in-memory model integration test for ACT-002; no upstream import."""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import torch
from act_counterfactual import run_experiment


class StubConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.act_threshold = .99


class StubRecurrent(torch.nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.act = torch.nn.Sequential(torch.nn.Linear(dim, 1), torch.nn.Sigmoid())
        with torch.no_grad():
            self.act[0].weight.zero_()
            self.act[0].bias.fill_(torch.logit(torch.tensor(.4)))

    def forward(self, h, loops, threshold):
        mass = torch.zeros(h.shape[:2], dtype=h.dtype, device=h.device)
        cumulative = torch.zeros_like(mass)
        halted = torch.zeros_like(mass, dtype=torch.bool)
        out = torch.zeros_like(h)
        for step in range(loops):
            h = torch.tanh(h + 0.1 * (step + 1))
            p = self.act(h).squeeze(-1)
            running = ~halted
            remainder = (1.0 - cumulative).clamp(min=0)
            w = torch.where(cumulative + p >= threshold, remainder, p) * running.float()
            out = out + w.unsqueeze(-1) * h
            cumulative = cumulative + p * running.float()
            halted = halted | (cumulative >= threshold)
            if bool(halted.all()):
                break
        return out


class StubModel(torch.nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.embed = torch.nn.Embedding(cfg.vocab_size, cfg.dim)
        self.recurrent = StubRecurrent(cfg.dim)
        self.head = torch.nn.Linear(cfg.dim, cfg.vocab_size)
        self.cfg = cfg

    def forward(self, tokens, n_loops=None):
        h = self.embed(tokens)
        h = self.recurrent(h, n_loops or self.cfg.max_loop_iters, self.cfg.act_threshold)
        return self.head(h)


class CounterfactualIntegrationTests(unittest.TestCase):
    def test_four_cells_reconstruct_before_training_update(self):
        torch.set_num_threads(1)
        module = types.SimpleNamespace(OpenMythos=StubModel, MythosConfig=StubConfig)
        r = run_experiment(module, 'gqa', 2, seed=22, steps=2, lr=0.003, device='cpu')
        self.assertEqual(len(r['train_trace']), 2)
        self.assertAlmostEqual(r['train_trace'][0]['parameter_l2_difference_pre_update'], 0.0)
        self.assertLess(r['train_trace'][0]['effects']['logits']['reconstruction_max_abs_error'], 1e-5)
        self.assertGreater(r['train_trace'][0]['effects']['logits']['direct_mechanism_same_original_weights']['max_abs'], 0.0)
        self.assertGreater(r['train_trace'][0]['original_act_deficit_fraction_original_weights'], 0.0)
        self.assertAlmostEqual(
            r['train_trace'][0]['effects']['logits']['parameter_history_under_original_act']['max_abs'],
            0.0, places=6)
        self.assertLess(r['train_trace'][0]['effects']['loss']['reconstruction_abs_error'], 1e-7)
        self.assertEqual(r['events']['first_original_mass_deficit_step'], 1)
        self.assertGreaterEqual(r['heldout']['heldout_batches'], 1)


if __name__ == '__main__':
    unittest.main()
