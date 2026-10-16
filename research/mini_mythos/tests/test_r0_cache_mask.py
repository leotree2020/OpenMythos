"""R0 cached-chunk mask intervention: exact values and live upstream models."""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common import get_repo, load_upstream
from r0_cache_mask import (
    cached_chunk_forward,
    chunk_causal_mask,
    temporary_chunk_mask,
    validate_prefix_cache,
)
from r0_cache_compare import compare


class R0CacheMaskTests(unittest.TestCase):
    def test_chunk_causal_mask_offsets(self):
        mask = chunk_causal_mask(2, 3, torch.device("cpu"), torch.float32)
        self.assertEqual(tuple(mask.shape), (1, 1, 2, 5))
        self.assertEqual(mask[0, 0, 0].tolist(), [0.0, 0.0, 0.0, 0.0, float("-inf")])
        self.assertEqual(mask[0, 0, 1].tolist(), [0.0] * 5)

    def test_no_prefix_is_standard_mask(self):
        mask = chunk_causal_mask(3, 0, torch.device("cpu"), torch.float32)
        self.assertEqual(mask[0, 0, 0].tolist(), [0.0, float("-inf"), float("-inf")])
        self.assertEqual(mask[0, 0, 2].tolist(), [0.0] * 3)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            chunk_causal_mask(0, 4, "cpu", torch.float32)
        with self.assertRaises(ValueError):
            chunk_causal_mask(2, -1, "cpu", torch.float32)

    def test_prefix_cache_validation(self):
        validate_prefix_cache({"a": {"k": torch.zeros(1, 4, 2, 4)}}, 4)
        validate_prefix_cache({"a": {"c_kv": torch.zeros(1, 4, 8)}}, 4)
        with self.assertRaisesRegex(ValueError, "length mismatch"):
            validate_prefix_cache({"a": {"k": torch.zeros(1, 3, 2, 4)}}, 4)

    def test_instance_override_restored_on_exception(self):
        class FakeModel:
            @staticmethod
            def _causal_mask(t, device, dtype):
                return "original"
        model = FakeModel()
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with temporary_chunk_mask(model, 4):
                self.assertEqual(tuple(model._causal_mask(2, "cpu", torch.float32).shape), (1, 1, 2, 6))
                raise RuntimeError("deliberate")
        self.assertNotIn("_causal_mask", vars(model))
        self.assertEqual(model._causal_mask(2, "cpu", torch.float32), "original")

    def test_live_gqa_full_vs_corrected_cache(self):
        module = load_upstream(get_repo("."))
        result = compare(module, "gqa")
        self.assertEqual(result["mask_intervention"]["status"], "PASS", result)

    def test_live_mla_full_vs_corrected_cache(self):
        module = load_upstream(get_repo("."))
        result = compare(module, "mla")
        self.assertEqual(result["mask_intervention"]["status"], "PASS", result)


if __name__ == "__main__":
    unittest.main()
