"""P0 CPU-only fixed-batch optimization sanity check.

This is NOT the separate loop_proto A/B experiment and is NOT a
generalization or language-quality benchmark.
"""
import sys
import unittest
from pathlib import Path

import torch
import torch.nn.functional as F

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from common import get_repo, load_upstream, tiny_config, toy_batch


class CPUFixedBatchSanity(unittest.TestCase):
    def test_one_loop_can_reduce_fixed_batch_loss(self):
        torch.set_num_threads(2)
        torch.manual_seed(20261022)
        repo = get_repo(str(Path(__file__).resolve().parents[3]))
        upstream = load_upstream(repo)
        model = upstream.OpenMythos(tiny_config(upstream, "gqa")).cpu().train()
        inputs, targets = toy_batch(torch, 991, batch_size=1, seq_len=8)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.003)
        losses = []
        for _ in range(24):
            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs, n_loops=1)
            loss = F.cross_entropy(
                logits.reshape(-1, logits.shape[-1]), targets.reshape(-1)
            )
            self.assertTrue(torch.isfinite(loss).item())
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            self.assertTrue(torch.isfinite(grad_norm).item())
            optimizer.step()
            losses.append(float(loss.detach()))
        self.assertLess(
            min(losses[-5:]), losses[0] * 0.98,
            f"Fixed-batch loss failed to decrease: start={losses[0]:.4f}, "
            f"last={losses[-1]:.4f}",
        )


if __name__ == "__main__":
    unittest.main()
