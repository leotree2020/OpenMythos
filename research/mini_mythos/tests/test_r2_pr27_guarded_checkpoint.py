"""R2 Gate E: isolated guarded checkpoint I/O, no network/GPU/118M model."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_tokenizer_contract import create_contract
from r2_pr27_guarded_checkpoint import (
    PROTOCOL, identity_metadata, manifest_for, read_frozen_contract,
    require_real_tokenizer_identity, safe_load_bound_checkpoint,
    save_bound_checkpoint, synthetic_one_step_bundle, stream_sha256,
    validate_bundle_structure, validate_manifest_before_loading,
)


def dummy_contract():
    fp = {
        "identifier": "gpt2",
        "pinned_revision": "a" * 40,
        "len_tokenizer": 7, "maximum_token_id": 6,
        "token_to_id_sha256": "token-map-fixture",
        "backend_serialization_sha256": "rules-fixture",
        "special_tokens": {"eos_token_id": 6, "pad_token_id": 6},
    }
    return create_contract(fp)


def dummy_bundle(contract):
    return {
        "format": PROTOCOL,
        "step": 5, "tokens_seen": 100,
        "model": {"embedding.weight": torch.rand(7, 3)},
        "opt": {"state": {}, "param_groups": []},
        "cfg": {"tokenizer": "gpt2"},
        "mcfg": {"vocab_size": 7},
        "embedding_key": "embedding.weight",
        "tokenizer_metadata": identity_metadata(contract, 7),
    }


class FakeTokenizer:
    def encode(self, text, *, add_special_tokens=False):
        return [0, 1, 2, 3]


class R2GateETests(unittest.TestCase):
    def setUp(self):
        self.contract = dummy_contract()
        self.fp = self.contract["fingerprint"]
        self.bundle = dummy_bundle(self.contract)

    def test_tokenizer_bound_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ckpt, manifest = root / "checkpoint.pt", root / "manifest.json"
            saved = save_bound_checkpoint(
                ckpt, manifest, self.bundle, self.contract, self.fp)
            self.assertEqual(saved["checkpoint_sha256"], stream_sha256(ckpt))
            loaded = safe_load_bound_checkpoint(
                ckpt, manifest, self.contract, self.fp)
            self.assertTrue(torch.equal(
                loaded["model"]["embedding.weight"],
                self.bundle["model"]["embedding.weight"]
            ))
            self.assertEqual(loaded["tokenizer_metadata"],
                             self.bundle["tokenizer_metadata"])
            self.assertEqual(loaded["step"], 5)
            with self.assertRaises(FileExistsError):
                save_bound_checkpoint(
                    ckpt, manifest, self.bundle, self.contract, self.fp)

    def test_wrong_token_ids_rejected_before_weight_deserialization(self):
        with tempfile.TemporaryDirectory() as td:
            ckpt, manifest = Path(td) / "checkpoint.pt", Path(td) / "manifest.json"
            save_bound_checkpoint(ckpt, manifest, self.bundle,
                                  self.contract, self.fp)
            changed = dict(self.fp, token_to_id_sha256="swapped")
            with patch("r2_pr27_guarded_checkpoint.torch.load",
                       side_effect=AssertionError("DO NOT DESERIALIZE")):
                with self.assertRaisesRegex(ValueError, "token_to_id_sha256"):
                    safe_load_bound_checkpoint(
                        ckpt, manifest, self.contract, changed)

    def test_missing_sidecar_rejected_before_weight_deserialization(self):
        with tempfile.TemporaryDirectory() as td:
            ckpt = Path(td) / "checkpoint.pt"
            manifest = Path(td) / "missing.json"
            with patch("r2_pr27_guarded_checkpoint.torch.load",
                       side_effect=AssertionError("DO NOT DESERIALIZE")):
                with self.assertRaisesRegex(ValueError, "manifest missing"):
                    safe_load_bound_checkpoint(
                        ckpt, manifest, self.contract, self.fp)

    def test_corrupted_checkpoint_bytes_rejected_before_torch_load(self):
        with tempfile.TemporaryDirectory() as td:
            ckpt, manifest = Path(td) / "checkpoint.pt", Path(td) / "manifest.json"
            save_bound_checkpoint(ckpt, manifest, self.bundle,
                                  self.contract, self.fp)
            with ckpt.open("ab") as f:
                f.write(b"unexpected bytes")
            with patch("r2_pr27_guarded_checkpoint.torch.load",
                       side_effect=AssertionError("DO NOT DESERIALIZE")):
                with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                    safe_load_bound_checkpoint(
                        ckpt, manifest, self.contract, self.fp)

    def test_manifest_wrong_revision_and_contract_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            ckpt, manifest = Path(td) / "checkpoint.pt", Path(td) / "manifest.json"
            save_bound_checkpoint(ckpt, manifest, self.bundle,
                                  self.contract, self.fp)
            saved = json.loads(manifest.read_text())
            saved["tokenizer_metadata"]["tokenizer_revision"] = "b" * 40
            manifest.write_text(json.dumps(saved))
            with patch("r2_pr27_guarded_checkpoint.torch.load",
                       side_effect=AssertionError("DO NOT DESERIALIZE")):
                with self.assertRaisesRegex(ValueError, "revision"):
                    validate_manifest_before_loading(
                        ckpt, manifest, self.contract, self.fp)

    def test_missing_contract_metadata_or_wrong_emb_rows(self):
        bundle = copy.deepcopy(self.bundle)
        del bundle["tokenizer_metadata"]
        with self.assertRaises(ValueError):
            validate_bundle_structure(bundle, self.contract)
        bundle = copy.deepcopy(self.bundle)
        bundle["model"]["embedding.weight"] = torch.rand(6, 3)
        with self.assertRaisesRegex(ValueError, "embedding tensor rows"):
            validate_bundle_structure(bundle, self.contract)
        bundle = copy.deepcopy(self.bundle)
        bundle["mcfg"]["vocab_size"] = 9
        with self.assertRaisesRegex(ValueError, "embedding size"):
            validate_bundle_structure(bundle, self.contract)

    def test_checkpoint_metadata_cannot_use_different_tokenizer(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["cfg"]["tokenizer"] = "distilgpt2"
        with self.assertRaisesRegex(ValueError, "gpt2"):
            validate_bundle_structure(bundle, self.contract)

    def test_fake_embedding_and_optimizer_step_smoke(self):
        # The tiny demo genuinely runs a CPU optimization step but creates
        # NO production OpenMythos weights and does not download anything.
        bundle, loss = synthetic_one_step_bundle(
            self.contract, FakeTokenizer()
        )
        self.assertTrue(loss > 0)
        self.assertEqual(bundle["step"], 1)
        self.assertGreater(bundle["tokens_seen"], 0)
        self.assertEqual(bundle["model"]["embedding.weight"].shape[0], 7)
        self.assertTrue(bundle["opt"]["state"])
        self.assertTrue(validate_bundle_structure(bundle, self.contract))

    def test_contract_preflight_requires_original_pinned_gpt2_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "fake.json"
            path.write_text(json.dumps(self.contract))
            with self.assertRaisesRegex(ValueError, "EXACT"):
                read_frozen_contract(path, strict_gate=True)
            self.assertEqual(
                read_frozen_contract(path, strict_gate=False), self.contract
            )

    def test_reject_altered_manifest_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            ckpt, manifest = Path(td) / "checkpoint.pt", Path(td) / "manifest.json"
            save_bound_checkpoint(ckpt, manifest, self.bundle,
                                  self.contract, self.fp)
            saved = json.loads(manifest.read_text())
            saved["source_PR27_commit"] = "other"
            manifest.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, "source PR"):
                validate_manifest_before_loading(
                    ckpt, manifest, self.contract, self.fp)


if __name__ == "__main__":
    unittest.main()
