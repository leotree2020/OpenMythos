"""Unit tests for ACT-003 Gate B paired train-seed summaries."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from act_gate_b import summarize


def row(seed, delta, attention="gqa", depth=2):
    return {
        "seed": seed, "attention": attention, "requested_depth": depth,
        "heldout": {"original_loss": 2.0, "forced_final_loss": 2.0 + delta},
    }


class GateBTests(unittest.TestCase):
    def test_positive_delta_means_original_lower(self):
        s = summarize([row(11, .1), row(22, .2)], bootstrap=200)
        self.assertEqual(len(s), 1)
        self.assertAlmostEqual(s[0]["mean_delta_loss_forced_minus_original"], .15)
        self.assertEqual(s[0]["original_better_count"], 2)
        self.assertEqual(s[0]["forced_better_count"], 0)

    def test_negative_delta_means_forced_lower(self):
        s = summarize([row(11, -.1), row(22, -.2)], bootstrap=200)
        self.assertEqual(s[0]["forced_better_count"], 2)

    def test_bootstrap_is_deterministic(self):
        rows = [row(11, .1), row(22, -.2), row(33, .3)]
        self.assertEqual(summarize(rows, bootstrap=200),
                         summarize(list(reversed(rows)), bootstrap=200))

    def test_reject_duplicate_seeds(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize([row(11, .1), row(11, .2)], bootstrap=200)

    def test_reject_nonfinite(self):
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            summarize([row(11, float("nan"))], bootstrap=200)


if __name__ == "__main__":
    unittest.main()
