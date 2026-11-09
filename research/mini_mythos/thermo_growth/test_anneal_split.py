"""Tests for anneal_split.py on synthetic points with known structure (CPU, torch only).

  python -B -m unittest test_anneal_split -v
"""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anneal_split as A  # noqa: E402


def blobs(centres, n_each, sigma, dim, seed=0):
    gen = torch.Generator().manual_seed(seed)
    pts = []
    for c in centres:
        base = torch.zeros(dim, dtype=torch.float64)
        base[:len(c)] = torch.tensor(c, dtype=torch.float64)
        pts.append(base + sigma * torch.randn(n_each, dim, generator=gen, dtype=torch.float64))
    return torch.cat(pts, 0)


class AnnealTests(unittest.TestCase):
    def test_one_point_above_the_critical_temperature(self):
        X = blobs([(-1.0,), (1.0,)], 200, 0.1, 6)
        recs, info = A.anneal(torch, X, alpha=0.95, t_min_ratio=0.5)
        above = [r for r in recs if r["T_over_Tc1"] > 1.0]
        self.assertGreater(len(above), 3)
        self.assertTrue(all(r["K"] == 1 and r["span_dim"] == 0 for r in above))   # hot: one point
        self.assertEqual(recs[-1]["K"], 2)                                         # cooled: it split

    def test_first_split_happens_at_the_predicted_temperature(self):
        X = blobs([(-1.0,), (1.0,)], 300, 0.1, 6)
        recs, info = A.anneal(torch, X, alpha=0.97, t_min_ratio=0.3)
        first = info["first_split_observed_T"]
        self.assertIsNotNone(first)
        ratio = first / info["Tc1_predicted"]
        self.assertTrue(0.75 < ratio <= 1.0, ratio)                    # just below 2 * lambda_max
        split = next(r for r in recs if r["split_now"])
        self.assertEqual(split["K"], 2)
        self.assertEqual(split["span_dim"], 1)                         # point -> line
        self.assertEqual(split["hard_sizes"], [300, 300])              # along the real structure

    def test_point_line_plane_space(self):
        # four clusters at the corners of a regular tetrahedron (3-D structure inside 8 dims)
        s = 1.0
        corners = [(s, s, s), (s, -s, -s), (-s, s, -s), (-s, -s, s)]
        X = blobs(corners, 150, 0.08, 8, seed=1)
        recs, info = A.anneal(torch, X, alpha=0.95, t_min_ratio=0.02, k_max=4)
        spans = [r["span_dim"] for r in recs]
        self.assertEqual(spans[0], 0)
        self.assertEqual(max(spans), 3)                                # grows to the full 3-D structure
        self.assertEqual(spans, sorted(spans))                         # never shrinks
        self.assertEqual(recs[-1]["K"], 4)
        self.assertEqual(sorted(recs[-1]["hard_sizes"]), [150, 150, 150, 150])

    def test_deterministic(self):
        X = blobs([(-1.0, 0.5), (1.0, -0.5), (0.0, 1.5)], 100, 0.1, 5)
        a, _ = A.anneal(torch, X, alpha=0.9, t_min_ratio=0.05)
        b, _ = A.anneal(torch, X, alpha=0.9, t_min_ratio=0.05)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
