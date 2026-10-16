"""ACT-004 phase 2 aggregation and benchmark parameter validation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from act_compute_phase2 import aggregate
from act_compute_benchmark import paired_benchmark


def row(seed, original=2., forced=2.1):
    return {
        "attention": "gqa", "requested_depth": 2, "seed": seed,
        "heldout": {"original_loss": original, "forced_final_loss": forced},
        "benchmark": {
            "original": {"forward_median_seconds": .01, "backward_median_seconds": .02,
                         "actual_loops_mean": 2.},
            "forced_final": {"forward_median_seconds": .011, "backward_median_seconds": .021,
                             "actual_loops_mean": 2.},
            "forced_to_original_median_total_ratio": 1.1,
        },
    }


class Phase2Tests(unittest.TestCase):
    def test_absolute_loss_and_ratio(self):
        result = aggregate([row(11), row(22, 1.5, 1.4)])[0]
        self.assertAlmostEqual(result["original_heldout_loss_mean"], 1.75)
        self.assertAlmostEqual(result["forced_heldout_loss_mean"], 1.75)
        self.assertAlmostEqual(result["delta_loss_forced_minus_original"], 0.)
        self.assertAlmostEqual(result["forced_to_original_total_ratio_mean"], 1.1)

    def test_duplicate_seed_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            aggregate([row(11), row(11)])

    def test_bad_benchmark_args(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            paired_benchmark(None, None, 2, repeats=0)

    def test_nonfinite_loss_rejected(self):
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            aggregate([row(11, float("nan"))])


if __name__ == "__main__":
    unittest.main()
