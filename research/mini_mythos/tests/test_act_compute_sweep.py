"""ACT-004 depth-sweep aggregation tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from act_compute_sweep import summarize


def case(seed, delta, depth=2):
    return {
        "attention": "gqa", "requested_depth": depth, "seed": seed,
        "heldout": {"original_loss": 2.0, "forced_final_loss": 2.0 + delta},
        "paired_run_wall_seconds": 2.0,
        "train_trace": [
            {"original_actual_loops": depth, "forced_actual_loops": depth,
             "original_act_deficit_fraction": .25},
            {"original_actual_loops": depth, "forced_actual_loops": depth,
             "original_act_deficit_fraction": .75},
        ],
    }


class ComputeSweepTests(unittest.TestCase):
    def test_paired_delta_and_loop_counts(self):
        r = summarize([case(11, .1), case(22, -.1)])[0]
        self.assertAlmostEqual(r["mean_delta_loss_forced_minus_original"], 0.0)
        self.assertEqual(r["mean_original_forward_loop_calls_per_train_step"], 2)
        self.assertEqual(r["mean_forced_forward_loop_calls_per_train_step"], 2)
        self.assertEqual(r["mean_original_deficit_token_fraction_over_train_steps"], .5)
        self.assertEqual(r["mean_paired_run_wall_seconds"], 2)

    def test_grouped_by_depth(self):
        self.assertEqual(len(summarize([case(11, .1, 1), case(11, .2, 2)])), 2)

    def test_duplicate_seed_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize([case(11, .1), case(11, .2)])

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            summarize([case(11, float("inf"))])


if __name__ == "__main__":
    unittest.main()
