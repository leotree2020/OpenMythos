"""R2 preflight static check and memory arithmetic tests; no GPU required."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from r2_preflight import (
    SOURCE_PATHS, build_report, memory_estimates, static_blockers
)


class FakeCuda:
    @staticmethod
    def is_available():
        return False

    @staticmethod
    def device_count():
        return 0


class R2PreflightTests(unittest.TestCase):
    def test_memory_state_is_explicit_lower_scope_not_gpu_quote(self):
        estimates = memory_estimates([120_000_000, 200_000_000])
        self.assertEqual(len(estimates), 2)
        self.assertAlmostEqual(
            estimates[0]["base_training_state_gib_at_16_bytes_per_param"],
            round(120_000_000 * 16 / 2**30, 3)
        )
        self.assertIn("recurrent loops", estimates[0]["excluded"])
        with self.assertRaises(ValueError):
            memory_estimates([0])

    def test_static_gaps_are_labeled_not_runtime_errors(self):
        sources = {
            "training/3b_fine_web_edu.py":
                "from datasets import load_dataset\n"
                'state = torch.load(path, weights_only=False)\n',
            "open_mythos/tokenizer.py":
                'encoding = AutoTokenizer.from_pretrained("model")\n',
            "open_mythos/main.py":
                "mask = self._causal_mask(T, device, x.dtype)\n",
        }
        items = static_blockers(sources)
        by_id = {item["id"]: item for item in items}
        self.assertEqual(by_id["R2_TOKENIZER_REVISION"]["flag"], "GAP")
        self.assertEqual(by_id["R2_CHECKPOINT_TRUST"]["flag"], "GAP")
        self.assertEqual(by_id["R2_CACHE_CHUNK"]["flag"], "GAP")
        self.assertEqual(by_id["R2_MOE_BALANCING"]["flag"], "REVIEW")

    def test_cpu_codespace_report_without_network_or_gpu_allocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for filename in SOURCE_PATHS:
                p = root / filename
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("synthetic content", encoding="utf-8")
            fake_torch = SimpleNamespace(
                __version__="test-version",
                version=SimpleNamespace(cuda=None),
                cuda=FakeCuda(),
            )
            with patch("r2_preflight.commit_id", return_value="fixture-commit"):
                report = build_report(root, fake_torch)
            self.assertFalse(report["gpu_go"])
            self.assertFalse(report["hardware"]["cuda_available"])
            self.assertEqual(report["hardware"]["cuda_device_count"], 0)
            self.assertEqual(len(report["source_sha256"]), len(SOURCE_PATHS))
            self.assertTrue(report["source_review"])
            self.assertEqual(report["repository_commit"], "fixture-commit")
            self.assertNotIn("environment_variables", report)

    def test_source_flags_need_human_review_even_if_present(self):
        sources = {
            "training/3b_fine_web_edu.py":
                "from datasets import load_dataset\n"
                'checkpoint = torch.load(path, weights_only=True)\n'
                "val_loader = make_validation_loader()\n"
                "dataset_state = checkpoint['dataset_state']\n",
            "open_mythos/tokenizer.py":
                "encoding = AutoTokenizer.from_pretrained(model, revision=sha)",
            "open_mythos/main.py":
                "mask = self._causal_mask(T, device, x.dtype, prefix)",
        }
        by_id = {x["id"]: x for x in static_blockers(sources)}
        self.assertEqual(by_id["R2_DATA_CURSOR"]["flag"], "REVIEW")
        self.assertEqual(by_id["R2_TOKENIZER_REVISION"]["flag"], "REVIEW")
        self.assertEqual(by_id["R2_CACHE_CHUNK"]["flag"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
