"""Offline tests for exact byte-pair exposure accounting (no HF download)."""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r1_exposure_baselines import (
    compare_exposures, fit_seen_ngram, heldout_ngram_metrics,
    replay_observed_pairs,
)
from r1_text_pilot import VOCAB_SIZE, draw_batch


class ExposureMatchedTests(unittest.TestCase):
    def test_replay_is_identical_to_original_draw_batch_rng(self):
        train = (torch.arange(300) * 19 % VOCAB_SIZE).long()
        seed, steps, batch, seq_len = 20261016, 4, 3, 16
        observed_x = []
        observed_y = []
        actual = torch.Generator(device="cpu").manual_seed(seed + 17)
        for _ in range(steps):
            x, y = draw_batch(
                train, seq_len=seq_len, batch_size=batch,
                generator=actual, device="cpu"
            )
            observed_x.append(x.flatten())
            observed_y.append(y.flatten())
        re_x, re_y, state, summary = replay_observed_pairs(
            train, seed=seed, steps=steps, batch_size=batch,
            seq_len=seq_len
        )
        self.assertTrue(torch.equal(re_x, torch.cat(observed_x)))
        self.assertTrue(torch.equal(re_y, torch.cat(observed_y)))
        self.assertTrue(torch.equal(state, actual.get_state()))
        self.assertEqual(summary["supervised_target_positions"], steps * batch * seq_len)
        self.assertEqual(summary["mini_batches_replayed"], steps * batch)

    def test_exact_exposure_pair_histograms(self):
        x = torch.tensor([65, 65, 65, 66, 66], dtype=torch.long)
        y = torch.tensor([66, 66, 67, 65, 65], dtype=torch.long)
        uni, bi = fit_seen_ngram(x, y)
        self.assertEqual(uni.shape, (VOCAB_SIZE,))
        self.assertEqual(bi.shape, (VOCAB_SIZE, VOCAB_SIZE))
        self.assertAlmostEqual(float(uni.sum()), 1., places=10)
        self.assertTrue(torch.allclose(
            bi.sum(dim=1), torch.ones(VOCAB_SIZE, dtype=torch.double)))
        self.assertGreater(float(uni[66]), float(uni[7]))
        self.assertGreater(float(bi[65, 66]), float(bi[65, 7]))
        self.assertGreater(float(bi[66, 65]), float(bi[66, 66]))

    def test_mismatched_rng_fails_closed(self):
        train = (torch.arange(300) % 90).long()
        validation = (torch.arange(128) % 90).long()
        _, _, state, _ = replay_observed_pairs(
            train, seed=42, steps=3, batch_size=2, seq_len=16)
        bad = torch.Generator().manual_seed(314159).get_state()
        result = compare_exposures(
            train, validation,
            hyperparameters={"seed": 42, "batch_size": 2},
            steps=3, offset_rng_state=state, seq_len=16, windows=2
        )
        self.assertTrue(result["checkpoint_offset_rng_matches_replay"])
        self.assertEqual(result["exposure_matched"]["unigram"]["tokens"], 32)
        self.assertEqual(result["full_corpus_reference"]["bigram"]["tokens"], 32)
        with self.assertRaisesRegex(ValueError, "RNG state mismatch"):
            compare_exposures(
                train, validation,
                hyperparameters={"seed": 42, "batch_size": 2},
                steps=3, offset_rng_state=bad, seq_len=16, windows=2
            )

    def test_invalid_pairs_and_window(self):
        with self.assertRaises(ValueError):
            fit_seen_ngram(torch.tensor([2, 3]), torch.tensor([3]))
        with self.assertRaises(ValueError):
            fit_seen_ngram(torch.tensor([300]), torch.tensor([1]))
        with self.assertRaises(ValueError):
            replay_observed_pairs(torch.arange(40), seed=7, steps=0,
                                  batch_size=1, seq_len=8)
        uni, bi = fit_seen_ngram(torch.tensor([1, 2]), torch.tensor([2, 3]))
        with self.assertRaises(ValueError):
            heldout_ngram_metrics(uni, bi, torch.arange(5),
                                 seq_len=16, windows=1)


if __name__ == "__main__":
    unittest.main()
