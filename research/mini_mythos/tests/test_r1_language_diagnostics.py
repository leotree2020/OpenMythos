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
    byte_metrics, compare_heldout, fitted_byte_models, generate_diagnostic,
    metrics_from_sums, validate_checkpoint
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
        self.assertGreater(float(b[65, 66]), float(b[66, 65]))

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
        self.assertAlmostEqual(d["perplexity"], 16., places=8)
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
