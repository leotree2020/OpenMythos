"""R2 BF16 safe candidate: CPU regressions, no CUDA or source rewrite."""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common import get_repo, load_upstream, tiny_config
from r2_bf16_autocast_candidate import (
    compare_rope, snapshot_rope, temporary_low_precision_causal_mask,
    tiny_autocast_case
)


class R2BF16AutocastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(min(4, torch.get_num_threads()))
        cls.module = load_upstream(get_repo("."))

    def test_gqa_autocast_cpu_backward_preserves_rope(self):
        result = tiny_autocast_case(self.module, "gqa", "cpu", seed=811)
        self.assertTrue(result["successful_forward_backward"])
        self.assertEqual(result["autocast_dtype"], "torch.bfloat16")
        self.assertEqual(result["master_parameter_dtype"], "torch.float32")
        self.assertGreater(result["nonzero_gradient_tensors"], 0)
        self.assertTrue(all(
            row["exactly_preserved"] for row in result["rope_buffers"]
        ))

    def test_mla_autocast_cpu_backward_preserves_rope(self):
        result = tiny_autocast_case(self.module, "mla", "cpu", seed=811)
        self.assertTrue(result["successful_forward_backward"])
        self.assertTrue(all(
            row["exactly_preserved"] for row in result["rope_buffers"]
        ))
        self.assertGreater(result["nonzero_gradient_tensors"], 0)

    def test_full_context_mask_is_bf16_and_original_is_restored(self):
        cfg = tiny_config(self.module, attention="gqa")
        model = self.module.OpenMythos(cfg)
        original_mask = model._causal_mask(8, torch.device("cpu"), torch.float32)
        self.assertEqual(original_mask.dtype, torch.float32)
        with temporary_low_precision_causal_mask(model):
            converted = model._causal_mask(8, torch.device("cpu"), torch.float32)
            self.assertEqual(converted.dtype, torch.bfloat16)
            self.assertEqual(converted.shape, (1, 1, 8, 8))
            self.assertTrue(torch.isneginf(converted[0, 0, 0, 1]))
            self.assertEqual(float(converted[0, 0, 7, 0]), 0.)
            with self.assertRaisesRegex(ValueError, "existing instance"):
                with temporary_low_precision_causal_mask(model):
                    pass
        self.assertNotIn("_causal_mask", model.__dict__)
        restored = model._causal_mask(8, torch.device("cpu"), torch.float32)
        self.assertTrue(torch.equal(restored, original_mask))
        self.assertEqual(restored.dtype, torch.float32)

    def test_mask_override_restores_on_exception(self):
        cfg = tiny_config(self.module, attention="gqa")
        model = self.module.OpenMythos(cfg)
        with self.assertRaisesRegex(RuntimeError, "expected"):
            with temporary_low_precision_causal_mask(model):
                raise RuntimeError("expected")
        self.assertNotIn("_causal_mask", model.__dict__)

    def test_corrupted_rope_buffer_is_rejected_as_unrecoverable(self):
        model = self.module.OpenMythos(tiny_config(self.module, "mla"))
        snapshot = snapshot_rope(model)
        self.assertTrue(all(
            x["exactly_preserved"] for x in compare_rope(model, snapshot)
        ))
        model.freqs_cis = model.freqs_cis.real.to(torch.bfloat16)
        with self.assertRaisesRegex(ValueError, "already discarded"):
            snapshot_rope(model)

    def test_unknown_attention_or_unavailable_gpu_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unknown attention"):
            tiny_autocast_case(self.module, "unknown")
        if not torch.cuda.is_available():
            with self.assertRaisesRegex(ValueError, "no GPU"):
                tiny_autocast_case(self.module, "gqa", device="cuda")


if __name__ == "__main__":
    unittest.main()
