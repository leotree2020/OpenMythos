"""R2 Gate N: offline tests for ACTUAL HF shard-count inspection protocol.

Every test uses a deterministic FakeIterable (NO Hub, no documents, no
Parquet bytes, no model, no GPU). The Gate N CLI is the sole allowed
live HF metadata probe and requires existing Gate I + Gate M inputs.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import r2_pr27_live_hf_shard_metadata as gate
from r2_pr27_remote_parquet_inventory import build_inventory, canonical_digest


class FakeIterable:
    """Count-correct fake .shard; __iter__ intentionally forbidden."""

    def __init__(self, shard_ids=range(14), *, wrong_behavior=False):
        self.shard_ids = list(shard_ids)
        self.num_shards = len(self.shard_ids)
        self.wrong_behavior = wrong_behavior
        self.calls = []

    def __iter__(self):
        raise AssertionError("Gate N must NEVER iterate any Dataset")

    def shard(self, *, num_shards, index, contiguous=True):
        self.calls.append((num_shards, index, contiguous))
        if contiguous:
            from r2_pr27_remote_parquet_inventory import contiguous_indices
            ids = [
                self.shard_ids[i]
                for i in contiguous_indices(self.num_shards, index)
            ]
        else:
            ids = self.shard_ids[index::num_shards]
        if self.wrong_behavior:
            ids = ids[:-1]
        return FakeIterable(ids, wrong_behavior=self.wrong_behavior)


class GateNTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.versions = {
            "python": "3.fake", "datasets": "hf-test",
            "torch": "torch-test", "huggingface_hub": "hub-test",
            "pyarrow": "arrow-test",
        }

    def report(self, ds=None, **override):
        args = dict(
            source_sha=gate.SOURCE_REVISION,
            file_count=14,
            file_inventory_sha=gate.SOURCE_FILE_INVENTORY_SHA256,
            versions=self.versions,
        )
        args.update(override)
        return gate.build_report(ds if ds is not None else FakeIterable(), **args)

    def test_project_14_native_full_and_double_seven_missing(self):
        p = gate.project_logical_shard_indices(14)
        self.assertEqual(p["native_worker_auto_once"]["observed_logical_indices"], 14)
        self.assertTrue(p["native_worker_auto_once"]["covers_all_indices_once"])
        self.assertEqual(
            p["native_worker_auto_once"]["per_worker_counts"],
            {"0": 7, "1": 7}
        )
        d = p["pr27_manual_contiguous_plus_native_auto"]
        self.assertEqual(d["per_worker_counts"], {"0": 4, "1": 3})
        self.assertEqual(d["observed_logical_indices"], 7)
        self.assertEqual(d["missing_logical_indices"], [1, 3, 5, 7, 9, 11, 13])

    def test_13_shard_partition_uneven_and_not_hardcoded(self):
        p = gate.project_logical_shard_indices(13)
        self.assertEqual(p["native_worker_auto_once"]["observed_logical_indices"], 13)
        self.assertEqual(
            p["native_worker_auto_once"]["per_worker_counts"], {"0": 7, "1": 6}
        )
        self.assertEqual(
            p["pr27_manual_contiguous_plus_native_auto"]["observed_logical_indices"], 7
        )

    def test_fake_real_shard_method_is_called_but_dataset_never_iterated(self):
        ds = FakeIterable()
        inspected = gate.inspect_runtime_dataset(ds)
        self.assertEqual(inspected["source_num_shards"], 14)
        self.assertEqual(len(ds.calls), 4)
        self.assertEqual(ds.calls, [
            (2, 0, True), (2, 0, False),
            (2, 1, True), (2, 1, False),
        ])
        self.assertEqual(
            inspected["actual_manual_contiguous_shard_counts"], {"0": 7, "1": 7}
        )
        self.assertEqual(
            inspected["actual_noncontiguous_shard_counts"], {"0": 7, "1": 7}
        )
        self.assertEqual(
            inspected["actual_manual_then_noncontiguous_counts"], {"0": 4, "1": 3}
        )
        self.assertTrue(inspected["no_explicit_document_iteration"])

    def test_mismatched_hf_sharding_semantics_fail_closed(self):
        ds = FakeIterable(wrong_behavior=True)
        with self.assertRaisesRegex(ValueError, "shard count mismatch"):
            gate.inspect_runtime_dataset(ds)

    def test_build_and_offline_verify_real_counts_without_hub(self):
        report = self.report()
        self.assertEqual(report["actual_hf_iterable_num_shards"], 14)
        self.assertTrue(report["hf_shards_count_matches_file_count"])
        self.assertFalse(report["file_identity_to_hf_shard_identity_verified"])
        self.assertFalse(report["dataset_iteration_performed"])
        self.assertFalse(report["original_pr27_dataloader_invoked"])
        self.assertEqual(gate.verify_report(report), report)
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "runtime.json"
            file.write_text(json.dumps(report))
            self.assertEqual(gate.verify_report(json.loads(file.read_text())), report)

    def test_runtime_shards_can_differ_from_file_count(self):
        report = self.report(FakeIterable(range(13)))
        self.assertEqual(report["parquet_file_count_from_gate_m"], 14)
        self.assertEqual(report["actual_hf_iterable_num_shards"], 13)
        self.assertFalse(report["hf_shards_count_matches_file_count"])
        self.assertEqual(gate.verify_report(report), report)

    def test_tampered_runtime_manifest_or_resigned_scope_rejected(self):
        original = self.report()
        altered = copy.deepcopy(original)
        altered["actual_hf_iterable_num_shards"] = 16
        with self.assertRaisesRegex(ValueError, "SHA256"):
            gate.verify_report(altered)
        altered["report_sha256"] = canonical_digest({
            k: v for k, v in altered.items() if k != "report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "source num_shards"):
            gate.verify_report(altered)
        altered = copy.deepcopy(original)
        altered["dataset_iteration_performed"] = True
        altered["report_sha256"] = canonical_digest({
            k: v for k, v in altered.items() if k != "report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "scope overstated"):
            gate.verify_report(altered)

    def test_frozen_source_inventory_and_package_versions_rejected_on_drift(self):
        with self.assertRaisesRegex(ValueError, "Gate I"):
            self.report(source_sha="a" * 40)
        with self.assertRaisesRegex(ValueError, "file count"):
            self.report(file_count=13)
        with self.assertRaisesRegex(ValueError, "inventory SHA"):
            self.report(file_inventory_sha="b" * 64)
        with self.assertRaisesRegex(ValueError, "versions"):
            self.report(versions={"python": "3.10"})
        with self.assertRaisesRegex(ValueError, "invalid shard count"):
            gate.project_logical_shard_indices(1)

    def test_gate_m_sha_check_uses_external_independent_evidence(self):
        files = [
            {"path": f"sample/10BT/{i:03d}_00000.parquet", "size": i + 100}
            for i in range(14)
        ]
        manifest = build_inventory(files, repo_revision=gate.SOURCE_REVISION)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate-m.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "external pinned SHA"):
                gate.verify_frozen_gate_m_inventory(path)
            with patch.object(gate, "SOURCE_FILE_INVENTORY_SHA256",
                              manifest["file_inventory_sha256"]):
                self.assertEqual(
                    gate.verify_frozen_gate_m_inventory(path), manifest
                )


if __name__ == "__main__":
    unittest.main()
