"""Gate O: fake HF 5.1.0 metadata sources ONLY; ZERO remote requests.

All simulated views reject __iter__ to prove no records are consumed.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import r2_pr27_real_hf_file_shard_mapping as gate
import r2_pr27_live_hf_shard_metadata as prev
from r2_pr27_remote_parquet_inventory import canonical_digest, contiguous_indices


class ArrowExamplesIterable:
    """Fake instance that emulates ONLY the metadata shape of HF 5.1.0."""
    def __init__(self, files, groups=None):
        self.kwargs = {
            "files": list(files),
            "row_groups_list": [None] * len(files) if groups is None else groups,
        }

ArrowExamplesIterable.__module__ = "datasets.iterable_dataset"


class MappedExamplesIterable:
    def __init__(self, child):
        self.ex_iterable = child

MappedExamplesIterable.__module__ = "datasets.iterable_dataset"


def filenames(count=14):
    return [f"sample/10BT/{i:03d}_00000.parquet" for i in range(count)]


class FakeDataset:
    def __init__(self, names, *, wrapped=False):
        self.names = list(names)
        self.num_shards = len(self.names)
        self.calls = []
        raw = ArrowExamplesIterable(self.names)
        self._ex_iterable = MappedExamplesIterable(raw) if wrapped else raw

    def __iter__(self):
        raise AssertionError("Gate O must NEVER iterate")

    def shard(self, *, num_shards, index, contiguous=True):
        self.calls.append((num_shards, index, contiguous))
        if contiguous:
            selected = [self.names[i] for i in contiguous_indices(len(self.names), index)]
        else:
            selected = self.names[index::num_shards]
        return FakeDataset(selected)


class GateOTests(unittest.TestCase):
    def setUp(self):
        self.paths = filenames()
        self.ds = FakeDataset(self.paths)
        self.versions = {
            "python":"3.14.2", "datasets":"5.1.0", "torch":"2.14.1",
            "huggingface_hub":"2.2.0", "pyarrow":"26.0.0",
        }
        self.gate_m = {
            "file_inventory_sha256": gate.SOURCE_FILE_INVENTORY_SHA256,
            "file_metadata": [{"path": f, "size": 10000+i} for i,f in enumerate(self.paths)]
        }
        # Gate N prerequisite preparation must not mutate the Gate O probe.
        # Otherwise Gate N's four .shard() calls pollute the exact-call
        # assertion in test_actual_source_paths_exact_native_and_twice.
        gate_n_source = FakeDataset(self.paths)
        self.gate_n = prev.build_report(
            gate_n_source,
            source_sha=gate.SOURCE_REVISION,
            file_count=14,
            file_inventory_sha=gate.SOURCE_FILE_INVENTORY_SHA256,
            versions=self.versions
        )

    def report(self, ds=None):
        return gate.build_report(
            self.ds if ds is None else ds,
            gate_m=self.gate_m, gate_n=self.gate_n,
            versions=self.versions, git_commit="synthetic"
        )

    def test_safe_path_normalization_strips_secrets_from_output(self):
        source = "hf://datasets/HuggingFaceFW/fineweb-edu@pin/sample/10BT/001_00000.parquet?token=SECRET"
        self.assertEqual(gate.safe_relative_parquet_path(source), self.paths[1])
        http = "https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu/resolve/pin/sample/10BT/002_00000.parquet?access=PRIVATE"
        self.assertEqual(gate.safe_relative_parquet_path(http), self.paths[2])
        self.assertEqual(gate.safe_relative_parquet_path(self.paths[0]), self.paths[0])

    def test_rejects_malicious_or_unrelated_paths_without_secret_leak(self):
        for x in (
            "https://site.test/other/10BT/002_00000.parquet?token=LEAK",
            "https://site.test/sample/10BT/002_00000.parquet/EXTRA?token=LEAK",
            "file:///tmp/sample/10BT/002_00000.parquet?token=LEAK",
            "https://site.test/sample/10BT/002_00000.parquet.exe?token=LEAK",
            "hf://datasets/a@b/sample/10BT/../../bad.parquet?token=LEAK",
        ):
            with self.subTest(x=x):
                with self.assertRaises(ValueError) as err:
                    gate.safe_relative_parquet_path(x)
                self.assertNotIn("LEAK", str(err.exception))

    def test_actual_source_paths_exact_native_and_twice(self):
        result = gate.observed_mapping(self.ds, self.paths, version="5.1.0")
        self.assertEqual(result["actual_hf_source_order"], self.paths)
        self.assertEqual(result["native_actual_files_by_worker"]["0"], self.paths[0::2])
        self.assertEqual(result["native_actual_files_by_worker"]["1"], self.paths[1::2])
        self.assertEqual(result["manual_then_native_actual_files_by_worker"]["0"],
                         [self.paths[i] for i in (0,2,4,6)])
        self.assertEqual(result["manual_then_native_actual_files_by_worker"]["1"],
                         [self.paths[i] for i in (8,10,12)])
        self.assertEqual(result["manual_then_native_missing_source_files"],
                         [self.paths[i] for i in (1,3,5,7,9,11,13)])
        self.assertEqual(result["manual_then_native_actual_source_files"], 7)
        self.assertEqual(len(self.ds.calls), 4)
        self.assertTrue(result["no_document_iteration"])

    def test_mapping_uses_actual_order_not_sorted_filename_hypothesis(self):
        reverse = FakeDataset(list(reversed(self.paths)))
        mapped = gate.observed_mapping(reverse, self.paths, version="5.1.0")
        self.assertEqual(mapped["actual_hf_source_order"], list(reversed(self.paths)))
        self.assertEqual(mapped["manual_then_native_missing_source_files"], [
            reverse.names[i] for i in (1,3,5,7,9,11,13)
        ])

    def test_compatible_wrapper_is_unwrapped_without_any_iteration(self):
        ds = FakeDataset(self.paths, wrapped=True)
        mapped = gate.observed_mapping(ds, self.paths, version="5.1.0")
        self.assertEqual(mapped["known_wrapper_chain"], ["MappedExamplesIterable"])
        self.assertEqual(mapped["native_actual_source_files"], 14)

    def test_unknown_wrapper_and_row_group_rejected(self):
        class StrangeIterable:
            __module__ = "datasets.iterable_dataset"
            def __init__(self, raw): self.ex_iterable = raw
        bad = FakeDataset(self.paths)
        bad._ex_iterable = StrangeIterable(bad._ex_iterable)
        with self.assertRaisesRegex(ValueError, "Unexpected HF IterableDataset wrapper"):
            gate.observed_mapping(bad, self.paths, version="5.1.0")
        bad = FakeDataset(self.paths)
        bad._ex_iterable.kwargs["row_groups_list"][0] = (0,)
        with self.assertRaisesRegex(ValueError, "Row-group-specific"):
            gate.observed_mapping(bad, self.paths, version="5.1.0")

    def test_wrong_schema_or_duplicate_file_identity_rejected(self):
        bad = FakeDataset(self.paths)
        bad._ex_iterable.kwargs.pop("row_groups_list")
        with self.assertRaisesRegex(ValueError, "arguments unavailable"):
            gate.observed_mapping(bad, self.paths, version="5.1.0")
        bad = FakeDataset(self.paths)
        bad._ex_iterable.kwargs["files"][3] = self.paths[2]
        with self.assertRaisesRegex(ValueError, "Repeated file"):
            gate.observed_mapping(bad, self.paths, version="5.1.0")
        bad = FakeDataset(self.paths)
        bad._ex_iterable.kwargs["files"][3] = "sample/10BT/999_00000.parquet"
        with self.assertRaisesRegex(ValueError, "differ from frozen"):
            gate.observed_mapping(bad, self.paths, version="5.1.0")

    def test_wrong_hf_version_or_real_shard_count_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "version drift"):
            gate.observed_mapping(self.ds, self.paths, version="5.2.0")
        ds = FakeDataset(self.paths)
        ds.num_shards = 13
        with self.assertRaisesRegex(ValueError, "Gate N 14"):
            gate.observed_mapping(ds, self.paths, version="5.1.0")

    def test_manifest_offline_roundtrip_and_tamper_detection(self):
        manifest = self.report()
        self.assertTrue(manifest["mapping"]["source_file_to_logical_shard_mapping_verified"])
        self.assertFalse(manifest["mapping"]["original_pr27_worker_execution_observed"])
        self.assertEqual(gate.verify_report(manifest, gate_m=self.gate_m, gate_n=self.gate_n), manifest)
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "gate-o.json"
            fp.write_text(json.dumps(manifest))
            self.assertEqual(gate.verify_report(json.loads(fp.read_text()),
                                                gate_m=self.gate_m, gate_n=self.gate_n), manifest)
        tampered = copy.deepcopy(manifest)
        tampered["mapping"]["manual_then_native_missing_source_files"] = []
        with self.assertRaisesRegex(ValueError, "SHA"):
            gate.verify_report(tampered, gate_m=self.gate_m, gate_n=self.gate_n)
        tampered["report_sha256"] = canonical_digest({
            k:v for k,v in tampered.items() if k != "report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "mapping payload inconsistent"):
            gate.verify_report(tampered, gate_m=self.gate_m, gate_n=self.gate_n)

    def test_report_does_not_upgrade_to_real_remote_worker_loss(self):
        manifest = self.report()
        manifest["mapping"]["actual_document_or_token_loss_measured"] = True
        manifest["report_sha256"] = canonical_digest({
            k:v for k,v in manifest.items() if k != "report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "mapping payload inconsistent"):
            gate.verify_report(manifest, gate_m=self.gate_m, gate_n=self.gate_n)
        manifest = self.report()
        manifest["live_pr27_dataloader_executed"] = True
        manifest["report_sha256"] = canonical_digest({
            k:v for k,v in manifest.items() if k != "report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "scope overstated"):
            gate.verify_report(manifest, gate_m=self.gate_m, gate_n=self.gate_n)


if __name__ == "__main__":
    unittest.main()
