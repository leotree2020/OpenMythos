"""Gate J: offline real-source provenance/record adapter + guarded replay.

These tests do not access HF or include original FineWeb text. One optional
Linux test spawns actual DataLoader subprocesses with synthetic fixture data;
the main Codespaces CLI is responsible for exercising the real frozen data.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_fineweb_source_snapshot import (
    SELECTED_DOCS, capture_bounded_documents,
    make_manifest, snapshot_blob
)
from r2_fineweb_local_replay import (
    PROTOCOL, SOURCE_REVISION, SOURCE_SNAPSHOT_SHA256,
    assemble_provenance_report, verified_real_records
)
from r2_pr27_real_dataloader_resume import compare_actual_multiprocess_resume
from r2_pr27_tokenizer_contract import create_contract, describe_tokenizer


class Backend:
    def to_str(self):
        return "r2-gate-j-fake-fast-tokenizer"


class FakeTokenizer:
    is_fast = True
    bos_token = "<eos>"
    eos_token = "<eos>"
    unk_token = "<eos>"
    pad_token = "<eos>"
    bos_token_id = 31
    eos_token_id = 31
    unk_token_id = 31
    pad_token_id = 31
    all_special_ids = [31]
    vocab_size = 32
    backend_tokenizer = Backend()

    def __len__(self):
        return 32

    def get_vocab(self):
        return {f"j_{i}": i for i in range(32)}

    def get_added_vocab(self):
        return {}

    def encode(self, text, *, add_special_tokens=False):
        return [ord(c) % 31 for c in text]


def fake_source_rows():
    """32 synthetic source documents (not actual HF texts)."""
    return [
        {"id": f"synthetic-id-{i:03d}", "text": (
            f"This is a fixed synthetic long-form research document number {i}. "
            f"A child worker loads stable token sequences from document {i}. "
            "No FineWeb original text is stored inside repository tests. "
        ) * 2}
        for i in range(SELECTED_DOCS)
    ]


def create_fake_snapshot(folder, *, revision="a" * 40, rows=None,
                         license_label="odc-by"):
    source_rows = fake_source_rows() if rows is None else rows
    records, stats = capture_bounded_documents(source_rows)
    manifest = make_manifest(
        records, stats, resolved_revision=revision,
        requested_revision="main", working_commit="test-fixture",
        license_label=license_label
    )
    folder.mkdir(parents=True)
    raw = snapshot_blob(records)
    (folder / "snapshot.jsonl").write_bytes(raw)
    (folder / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def read_fixture(folder, manifest):
    return verified_real_records(
        folder, expected_revision=manifest["resolved_revision"],
        expected_sha=manifest["snapshot_sha256"],
        expected_text_bytes=manifest["capture_stats"]["selected_text_bytes"],
        expected_snapshot_bytes=manifest["snapshot_bytes"],
    )


class R2GateJTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(min(4, torch.get_num_threads()))
        cls.tokenizer = FakeTokenizer()
        cls.contract = create_contract(describe_tokenizer(
            cls.tokenizer, identifier="gpt2",
            pinned_revision="a" * 40
        ))

    def test_real_source_adapter_preserves_all_32_source_order_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            manifest = create_fake_snapshot(folder)
            provenance, records = read_fixture(folder, manifest)
            self.assertEqual(provenance["source_document_count"], 32)
            self.assertEqual(len(records), 32)
            self.assertEqual(
                provenance["snapshot_sha256"], manifest["snapshot_sha256"])
            self.assertEqual(
                provenance["revision"], manifest["resolved_revision"])
            self.assertNotEqual(records[0]["id"], records[1]["id"])
            self.assertIn(manifest["resolved_revision"], records[0]["id"])
            self.assertEqual(records[0]["text"], fake_source_rows()[0]["text"])

    def test_external_fixed_hash_rejects_resigned_but_changed_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            original = create_fake_snapshot(folder)
            payload = fake_source_rows()
            payload[5]["text"] += " modified synthetic bytes!"
            folder_2 = Path(tmp) / "modified"
            replaced = create_fake_snapshot(folder_2, rows=payload)
            self.assertNotEqual(original["snapshot_sha256"],
                                replaced["snapshot_sha256"])
            with self.assertRaisesRegex(ValueError, "snapshot SHA differs"):
                verified_real_records(
                    folder_2,
                    expected_revision=original["resolved_revision"],
                    expected_sha=original["snapshot_sha256"],
                    expected_text_bytes=original["capture_stats"]["selected_text_bytes"],
                    expected_snapshot_bytes=original["snapshot_bytes"],
                )

    def test_wrong_dataset_commit_rejected_even_with_same_document_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            manifest = create_fake_snapshot(folder)
            with self.assertRaisesRegex(ValueError, "source revision"):
                verified_real_records(
                    folder, expected_revision="b" * 40,
                    expected_sha=manifest["snapshot_sha256"],
                    expected_text_bytes=manifest["capture_stats"]["selected_text_bytes"],
                    expected_snapshot_bytes=manifest["snapshot_bytes"],
                )

    def test_wrong_bytes_license_and_document_policy_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            manifest = create_fake_snapshot(folder)
            with self.assertRaisesRegex(ValueError, "byte count drift"):
                verified_real_records(
                    folder,
                    expected_revision=manifest["resolved_revision"],
                    expected_sha=manifest["snapshot_sha256"],
                    expected_text_bytes=-1,
                    expected_snapshot_bytes=manifest["snapshot_bytes"]
                )
            path = folder / "manifest.json"
            changed = copy.deepcopy(manifest)
            changed["source_license_metadata"] = "unknown"
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "license metadata differs"):
                read_fixture(folder, manifest)

    def test_missing_or_corrupted_source_file_never_trains(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            manifest = create_fake_snapshot(folder)
            (folder / "snapshot.jsonl").write_bytes(b"forged")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                read_fixture(folder, manifest)

    def test_manifest_summary_drift_rejected_even_if_jsonl_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            manifest = create_fake_snapshot(folder)
            manifest["source_document_summaries"][0]["text_bytes"] = 1
            (folder / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "provenance differs"):
                read_fixture(folder, manifest)

    def test_report_fails_if_only_simulated_worker_or_wrong_recovery(self):
        source = {"source_document_count": 32}
        records = [{"id": str(i), "text": "t"} for i in range(32)]
        invalid = {
            "actual_worker_processes": False,
            "trace_bitwise_equal": True
        }
        with self.assertRaisesRegex(ValueError, "actual subprocess"):
            assemble_provenance_report(source, records, invalid)
        invalid["actual_worker_processes"] = True
        with self.assertRaisesRegex(ValueError, "divergence"):
            assemble_provenance_report(source, records, invalid)

    @unittest.skipUnless(sys.platform == "linux", "Gate J Linux OS worker test")
    def test_fixture_text_through_real_dual_process_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "source"
            manifest = create_fake_snapshot(folder)
            source, records = read_fixture(folder, manifest)
            result = compare_actual_multiprocess_resume(
                self.tokenizer, self.contract,
                checkpoint_path=Path(tmp) / "fake.pt",
                manifest_path=Path(tmp) / "fake.manifest.json",
                records=records,
            )
            report = assemble_provenance_report(
                source, records, result,
                tokenizer_contract_sha256=self.contract["fingerprint_sha256"]
            )
            self.assertEqual(report["protocol"], PROTOCOL)
            self.assertEqual(report["gate_i_real_source"]["source_document_count"], 32)
            self.assertFalse(report["official_heldout_or_test_set_created"])
            self.assertFalse(report["model_quality_evaluation_performed"])
            self.assertTrue(report["tiny_cpu_adamw_training_performed"])
            # This test intentionally supplies synthetic data. Never label it
            # as real FineWeb in a machine-readable result or test assertion.
            self.assertFalse(report["real_multiprocess_replay"]["fineweb_data_consumed"])
            self.assertFalse(report["real_multiprocess_replay"]["live_hf_streaming_consumed"])
            self.assertIn("SYNTHETIC", report["real_multiprocess_replay"]["data"])
            self.assertTrue(report["real_multiprocess_replay"]["trace_bitwise_equal"])
            self.assertEqual(report["real_multiprocess_replay"]["max_abs_loss_difference"], 0)
            self.assertEqual(report["real_multiprocess_replay"]["first_resumed_task_id"], 5)
            self.assertTrue(report["real_multiprocess_replay"]["actual_worker_fetched_but_uncommitted"])
            self.assertEqual(
                len(result["actual_os_worker_processes_observed_per_run"]["continuous"]), 2
            )


if __name__ == "__main__":
    unittest.main()
