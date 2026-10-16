"""R1 Gate B real-text baseline/collapse diagnostics tests (offline)."""
import math
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common import get_repo, load_upstream
from r1_language_diagnostics import (
    byte_metrics, compare_heldout, context_order_probe, fitted_byte_models,
    generate_diagnostic, metrics_from_sums, validate_checkpoint
)
from r1_text_pilot import TOKENIZER_ID, make_config


class R1LanguageDiagnosticsTests(unittest.TestCase):
    def test_unigrams_bigrams_fit_training_only(self):
        train = torch.tensor([65, 66, 65, 66, 65, 67], dtype=torch.long)
        u, b = fitted_byte_models(train)
        self.assertAlmostEqual(float(u.sum()), 1., places=10)
        self.assertTrue(torch.allclose(b.sum(dim=1), torch.ones(257, dtype=torch.double)))
        self.assertGreater(float(u[65]), float(u[7]))
        self.assertGreater(float(b[65, 66]), float(b[65, 7]))
        self.assertGreater(float(b[66, 65]), float(b[66, 7]))

    def test_invalid_train_and_smoothing(self):
        with self.assertRaises(ValueError):
            fitted_byte_models(torch.tensor([65]))
        with self.assertRaises(ValueError):
            fitted_byte_models(torch.tensor([0, 257]))
        with self.assertRaises(ValueError):
            fitted_byte_models(torch.tensor([0, 1]), smoothing=0)

    def test_repeated_space_collapse_metrics(self):
        d = byte_metrics([32] * 24)
        self.assertEqual(d["space_fraction"], 1.)
        self.assertEqual(d["longest_single_byte_run"], 24)
        self.assertEqual(d["unique_bytes"], 1)
        self.assertEqual(byte_metrics([])["tokens"], 0)

    def test_nll_perplexity_math(self):
        d = metrics_from_sums(math.log(16) * 2, 2)
        self.assertAlmostEqual(d["ppl"], 16., places=8)
        self.assertIsNone(metrics_from_sums(0., 0)["nll"])

    def test_live_tiny_model_heldout_counts(self):
        module = load_upstream(get_repo("."))
        torch.manual_seed(42)
        model = module.OpenMythos(make_config(module, attention="gqa", seq_len=16))
        training = torch.randint(32, 100, (256,), generator=torch.Generator().manual_seed(2))
        validation = torch.randint(32, 100, (128,), generator=torch.Generator().manual_seed(3))
        result = compare_heldout(
            model, training, validation, seq_len=16, n_loops=2,
            n_windows=3, device="cpu"
        )
        self.assertEqual(result["model"]["tokens"], 48)
        self.assertEqual(result["bigram"]["tokens"], 48)
        self.assertEqual(result["unigram"]["tokens"], 48)
        self.assertEqual(result["uniform"]["tokens"], 48)
        self.assertAlmostEqual(
            result["uniform"]["nll"], math.log(257), places=6
        )

    def test_generation_deterministic_given_seed(self):
        module = load_upstream(get_repo("."))
        torch.manual_seed(95)
        model = module.OpenMythos(make_config(module, attention="gqa", seq_len=16))
        kwargs = {
            "n_loops": 2, "max_new_tokens": 2, "seq_len": 16,
            "device": "cpu", "mode": "sample", "seed": 51,
        }
        a = generate_diagnostic(model, "The ", **kwargs)
        b = generate_diagnostic(model, "The ", **kwargs)
        self.assertEqual(a["generated_byte_ids"], b["generated_byte_ids"])


    def test_context_order_control_last_token_only_is_invariant(self):
        class LastTokenOnly:
            def eval(self):
                return self

            def __call__(self, x, n_loops):
                return torch.nn.functional.one_hot(
                    x.long(), num_classes=257
                ).float()

        validation = torch.arange(65, dtype=torch.long)
        outcome = context_order_probe(
            LastTokenOnly(), validation, seq_len=64, n_loops=2,
            n_windows=1, device="cpu"
        )
        self.assertEqual(outcome["windows"], 1)
        self.assertEqual(outcome["mean_logits_max_abs_change"], 0.)
        self.assertEqual(outcome["mean_probability_total_variation"], 0.)
        self.assertEqual(outcome["reversed_minus_original_target_nll"], 0.)

    def test_context_order_control_detects_first_token_dependence(self):
        class FirstTokenBased:
            def eval(self):
                return self

            def __call__(self, x, n_loops):
                logits = torch.zeros(
                    (x.shape[0], x.shape[1], 257), dtype=torch.float32
                )
                for i in range(x.shape[0]):
                    logits[i, :, int(x[i, 0])] = 5.
                return logits

        validation = torch.arange(65, dtype=torch.long)
        outcome = context_order_probe(
            FirstTokenBased(), validation, seq_len=64, n_loops=2,
            n_windows=1, device="cpu"
        )
        self.assertGreater(outcome["mean_logits_max_abs_change"], 0.)
        self.assertGreater(outcome["mean_probability_total_variation"], 0.)
        self.assertEqual(outcome["argmax_changed_fraction"], 1.)

    def test_fingerprint_and_checkpoint_step_guard(self):
        module = load_upstream(get_repo("."))
        cfg = make_config(module, attention="gqa", seq_len=16)
        provenance = {
            "tokenizer": TOKENIZER_ID,
            "train": {"file_sha256": "train"},
            "validation": {"file_sha256": "val"},
        }
        hyper = {"depth": 2}
        report = {
            "target_step": 60,
            "hyperparameters": hyper,
            "source_provenance": provenance,
        }
        ckpt = {
            "format_version": 1, "cfg": asdict(cfg), "step": 60,
            "hyperparameters": hyper, "provenance": provenance,
        }
        validate_checkpoint(ckpt, report, cfg, provenance["train"], provenance["validation"])
        ckpt["step"] = 59
        with self.assertRaisesRegex(ValueError, "step"):
            validate_checkpoint(ckpt, report, cfg,
                                provenance["train"], provenance["validation"])


if __name__ == "__main__":
    unittest.main()
