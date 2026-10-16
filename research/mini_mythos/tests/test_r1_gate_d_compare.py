"""Offline tests for R1 longitudinal checkpoint comparison and fail-closed guards."""
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from r1_gate_d_compare import summarize_artifacts


def fixture(step, start_step, ppl, matched_unigram, matched_bigram):
    hyper = {"attention": "gqa", "depth": 2, "seq_len": 64,
             "batch_size": 4, "seed": 20261016, "lr": 0.001}
    config = {"dim": 48, "vocab_size": 257}
    source = {"tokenizer": "utf8-bytes", "train": {"sha256": "train"},
              "validation": {"sha256": "validation"}}
    report = {
        "start_step": start_step, "target_step": step,
        "hyperparameters": hyper, "configuration": config,
        "source_provenance": source, "tokenizer": "utf8-bytes",
        "model_parameters": 12345,
        "heldout_after_this_run": {
            "nll": math.log(ppl), "perplexity": ppl, "tokens": 1024,
        },
    }
    return {
        "report": report,
        "checkpoint": {
            "step": step, "provenance": source,
            "hyperparameters": hyper, "cfg": config
        },
        "diagnostics": {
            "checkpoint_step": step,
            "model_heldout_and_baselines": {
                "model": {"nll": math.log(ppl), "ppl": ppl, "tokens": 1024},
                "token_statistics": {
                    "predicted_space_fraction": 1.0,
                    "target_space_fraction": 0.1943359375,
                },
            },
            "context_order_probe": {
                "windows": 16,
                "mean_probability_total_variation": 0.002,
                "reversed_minus_original_target_nll": 0.004,
            },
        },
        "exposure": {
            "checkpoint_step": step,
            "model_reference": {"perplexity": ppl},
            "comparison": {
                "checkpoint_offset_rng_matches_replay": True,
                "replay": {"supervised_target_positions": step * 4 * 64},
                "exposure_matched": {
                    "unigram": {"ppl": matched_unigram, "tokens": 1024},
                    "bigram": {"ppl": matched_bigram, "tokens": 1024},
                },
            },
        },
    }


class GateDComparisonTests(unittest.TestCase):
    def setUp(self):
        self.at60 = fixture(60, 0, 29.264, 27.513, 19.158)
        self.at200 = fixture(200, 60, 25.167, 26.951, 14.812)

    def test_valid_resumed_runs_and_better_unigram(self):
        report = summarize_artifacts([self.at60, self.at200])
        self.assertEqual(len(report["checkpoints"]), 2)
        self.assertFalse(report["checkpoints"][0]["beats_matched_unigram"])
        self.assertTrue(report["checkpoints"][1]["beats_matched_unigram"])
        self.assertFalse(report["checkpoints"][1]["beats_matched_bigram"])
        self.assertTrue(report["checkpoints"][1]["all_space_argmax"])

    def test_reject_missing_rng_replay_proof(self):
        newer = copy.deepcopy(self.at200)
        newer["exposure"]["comparison"]["checkpoint_offset_rng_matches_replay"] = False
        with self.assertRaisesRegex(ValueError, "RNG replay"):
            summarize_artifacts([self.at60, newer])

    def test_reject_provenance_drift(self):
        newer = copy.deepcopy(self.at200)
        newer["report"]["source_provenance"]["train"]["sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "drifted"):
            summarize_artifacts([self.at60, newer])

    def test_reject_mismatched_eval_loss(self):
        newer = copy.deepcopy(self.at200)
        newer["diagnostics"]["model_heldout_and_baselines"]["model"]["nll"] += 0.1
        with self.assertRaisesRegex(ValueError, "NLL mismatch"):
            summarize_artifacts([self.at60, newer])

    def test_reject_invalid_continuation(self):
        newer = copy.deepcopy(self.at200)
        newer["report"]["start_step"] = 0
        with self.assertRaisesRegex(ValueError, "resumption chain"):
            summarize_artifacts([self.at60, newer])

    def test_reject_duplicated_step(self):
        newer = copy.deepcopy(self.at200)
        newer["report"]["target_step"] = 60
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            summarize_artifacts([self.at60, newer])


if __name__ == "__main__":
    unittest.main()
