"""Offline Gate E deterministic window bootstrap and evaluation checks."""
import math
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r1_gate_e_validation import (
    evaluate_windows, paired_bootstrap, quantile, summarize_windows
)
from r1_text_pilot import VOCAB_SIZE


class FixedByteLogitModel:
    def eval(self):
        return self

    def __call__(self, x, *, n_loops):
        n, t = x.shape
        logits = torch.zeros(n, t, VOCAB_SIZE, device=x.device)
        logits[..., 32] = 1.0
        return logits


class GateEValidationTests(unittest.TestCase):
    def test_constant_paired_difference_bootstrap(self):
        result = paired_bootstrap([0.3] * 12, repetitions=200, seed=42)
        self.assertAlmostEqual(result["observed_mean"], 0.3)
        self.assertAlmostEqual(result["percentile_95_interval"][0], 0.3)
        self.assertAlmostEqual(result["percentile_95_interval"][1], 0.3)

    def test_bootstrap_is_seeded_and_quantiles_ordered(self):
        a = paired_bootstrap([0.5, -0.25, 0.8, -0.2, 0.6], repetitions=200, seed=123)
        b = paired_bootstrap([0.5, -0.25, 0.8, -0.2, 0.6], repetitions=200, seed=123)
        self.assertEqual(a, b)
        low, high = a["percentile_95_interval"]
        self.assertLessEqual(low, high)
        self.assertAlmostEqual(quantile([0, 10, 20], 0.25), 5.0)

    def test_evaluate_same_targets_for_model_and_ngrams(self):
        validation = (torch.arange(128) * 3 % 64 + 32).long()
        unigram = torch.full((VOCAB_SIZE,), 1 / VOCAB_SIZE, dtype=torch.double)
        bigram = torch.full((VOCAB_SIZE, VOCAB_SIZE), 1 / VOCAB_SIZE,
                            dtype=torch.double)
        rows = evaluate_windows(
            FixedByteLogitModel(), validation, seq_len=16, loops=2,
            windows=4, device="cpu", matched_unigram=unigram,
            matched_bigram=bigram, full_bigram=bigram
        )
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(row["target_count"] for row in rows), 64)
        self.assertTrue(all(row["target_count"] == 16 for row in rows))
        self.assertTrue(all(
            math.isclose(row["matched_bigram_mean_nll"], math.log(VOCAB_SIZE),
                         abs_tol=1e-12)
            for row in rows
        ))
        result = summarize_windows(rows)
        self.assertEqual(result["target_tokens"], 64)
        self.assertEqual(result["windows"], 4)
        self.assertAlmostEqual(result["matched_bigram"]["ppl"], 257.0, places=8)
        self.assertTrue(0 <= result["argmax_predicted_space_fraction"] <= 1)

    def test_summary_direction_and_weighting(self):
        rows = [
            {"target_count": 2, "model_mean_nll": 2., "matched_unigram_mean_nll": 3.,
             "matched_bigram_mean_nll": 3., "full_corpus_bigram_mean_nll": 3.,
             "matched_bigram_minus_model_nll": 1.,
             "full_bigram_minus_model_nll": 1.,
             "predicted_space_count": 1, "target_space_count": 1,
             "top1_correct_count": 1},
            {"target_count": 6, "model_mean_nll": 3., "matched_unigram_mean_nll": 4.,
             "matched_bigram_mean_nll": 2., "full_corpus_bigram_mean_nll": 2.,
             "matched_bigram_minus_model_nll": -1.,
             "full_bigram_minus_model_nll": -1.,
             "predicted_space_count": 3, "target_space_count": 2,
             "top1_correct_count": 2},
        ]
        d = summarize_windows(rows)
        self.assertAlmostEqual(d["model"]["nll"], 2.75)
        self.assertAlmostEqual(d["matched_bigram"]["nll"], 2.25)
        self.assertEqual(d["argmax_predicted_space_fraction"], 0.5)
        self.assertEqual(d["target_space_fraction"], 0.375)
        self.assertEqual(d["fraction_windows_model_better_than_matched_bigram"], 0.5)

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            paired_bootstrap([])
        with self.assertRaises(ValueError):
            paired_bootstrap([float("nan")])
        with self.assertRaises(ValueError):
            quantile([1, 2], 1.2)
        with self.assertRaises(ValueError):
            summarize_windows([])
        validation = torch.arange(80, dtype=torch.long)
        bad = torch.full((VOCAB_SIZE,), 1 / VOCAB_SIZE)
        bi = torch.full((VOCAB_SIZE, VOCAB_SIZE), 1 / VOCAB_SIZE)
        with self.assertRaises(ValueError):
            evaluate_windows(
                FixedByteLogitModel(), validation, seq_len=16, loops=2,
                windows=2, device="cpu", matched_unigram=bad[:-1],
                matched_bigram=bi, full_bigram=bi
            )


if __name__ == "__main__":
    unittest.main()
