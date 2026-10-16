"""No-download tests for frozen Gate F provenance, test segregation and outputs."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r1_gate_f_prepare_test import validate_test_manifest
from r1_gate_f_test import PROTOCOL, validate_frozen_inputs
from r1_text_pilot import TOKENIZER_ID


def make_fixture():
    test_sha = "f" * 64
    manifest = {
        "source": "Salesforce/wikitext",
        "config": "wikitext-2-raw-v1",
        "split": "test",
        "resolved_revision": "a" * 40,
        "revision_requested": "main",
        "file": {
            "documents": 1200, "bytes": 250001,
            "sha256": test_sha,
            "path": "/some/ignored/results/test.txt",
        },
    }
    train = {"file_sha256": "a" * 64,
             "selected_bytes_sha256": "b" * 64}
    val = {"file_sha256": "c" * 64,
           "selected_bytes_sha256": "d" * 64}
    test = {"file_sha256": test_sha,
            "selected_bytes_sha256": "e" * 64}
    report = {"tokenizer": TOKENIZER_ID,
              "hyperparameters": {"seq_len": 64, "attention": "gqa",
                                  "depth": 2}}
    checkpoint = {"step": 600}
    return report, checkpoint, manifest, train, val, test


class R1GateFTests(unittest.TestCase):
    def test_protocol_is_fixed_before_test_data_access(self):
        self.assertEqual(PROTOCOL["checkpoint_step"], 600)
        self.assertEqual(PROTOCOL["test_docs"], 1200)
        self.assertEqual(PROTOCOL["max_test_bytes"], 250000)
        self.assertEqual(PROTOCOL["test_windows"], 256)
        self.assertEqual(PROTOCOL["byte_tokenizer"], TOKENIZER_ID)

    def test_valid_test_split_and_training_segregation(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        validate_test_manifest(manifest)
        validate_frozen_inputs(report, ckpt, manifest, train, val, test)

    def test_reject_validation_disguised_as_test(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        manifest["split"] = "validation"
        with self.assertRaisesRegex(ValueError, "test split"):
            validate_frozen_inputs(report, ckpt, manifest, train, val, test)

    def test_reject_mutable_or_unresolved_revision(self):
        _, _, manifest, _, _, _ = make_fixture()
        manifest["resolved_revision"] = "main"
        with self.assertRaisesRegex(ValueError, "commit SHA"):
            validate_test_manifest(manifest)

    def test_reject_wrong_file_sha(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        test["file_sha256"] = "9" * 64
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            validate_frozen_inputs(report, ckpt, manifest, train, val, test)

    def test_reject_test_data_equal_training_prefix(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        test["selected_bytes_sha256"] = train["selected_bytes_sha256"]
        with self.assertRaisesRegex(ValueError, "duplicates"):
            validate_frozen_inputs(report, ckpt, manifest, train, val, test)

    def test_reject_changed_model_step(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        ckpt["step"] = 601
        with self.assertRaisesRegex(ValueError, "step-600"):
            validate_frozen_inputs(report, ckpt, manifest, train, val, test)

    def test_reject_changed_model_architecture(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        report["hyperparameters"]["attention"] = "mla"
        with self.assertRaisesRegex(ValueError, "model config"):
            validate_frozen_inputs(report, ckpt, manifest, train, val, test)

    def test_reject_changed_document_count(self):
        report, ckpt, manifest, train, val, test = make_fixture()
        manifest["file"]["documents"] = 1100
        with self.assertRaisesRegex(ValueError, "document selection"):
            validate_frozen_inputs(report, ckpt, manifest, train, val, test)


if __name__ == "__main__":
    unittest.main()
