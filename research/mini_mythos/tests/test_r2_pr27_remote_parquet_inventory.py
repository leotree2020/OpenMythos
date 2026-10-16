"""R2 Gate M: pinned REAL sample/10BT HF Hub file-tree metadata protocol.

ALL tests offline with injected fake Hub API. They never fetch datasets,
Parquet bodies, real source text, GPU or model checkpoints.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_remote_parquet_inventory import (
    FILE_PREFIX, MAX_PARQUET_FILES, SOURCE_REVISION,
    build_inventory, canonical_digest, contiguous_indices,
    fetch_pinned_parquet_tree, freeze_inventory,
    project_two_worker_file_assignments, validate_files,
    verify_inventory,
)


def fake_files(count=14):
    return [
        {"path": f"sample/10BT/{i:03d}_00000.parquet",
         "size": 1000000 + i * 97}
        for i in range(count)
    ]


class FakeHfApi:
    def __init__(self, files=None, *, revision=SOURCE_REVISION):
        self.files = fake_files() if files is None else files
        self.revision = revision
        self.info_calls = []
        self.tree_calls = []

    def dataset_info(self, **kwargs):
        self.info_calls.append(kwargs)
        return SimpleNamespace(sha=self.revision)

    def list_repo_tree(self, **kwargs):
        self.tree_calls.append(kwargs)
        for item in self.files:
            yield SimpleNamespace(**item)
        # Non-parquet and another config path must be ignored.
        yield SimpleNamespace(path="sample/10BT/README.txt", size=300)
        yield SimpleNamespace(path="sample/100BT/001.parquet", size=10)


class R2GateMTests(unittest.TestCase):
    def test_native_once_covers_all_file_ids_without_overlap(self):
        projection = project_two_worker_file_assignments(fake_files())
        good = projection["native_auto_once"]
        self.assertTrue(good["covers_all_files_once"])
        self.assertEqual(good["per_worker_file_counts"], {"0": 7, "1": 7})
        self.assertEqual(good["worker_file_indices"], {
            "0": [0, 2, 4, 6, 8, 10, 12],
            "1": [1, 3, 5, 7, 9, 11, 13]
        })
        self.assertEqual(good["files_missing"], 0)

    def test_pr27_manual_plus_native_projects_specific_missing_ids(self):
        projection = project_two_worker_file_assignments(fake_files())
        bad = projection["pr27_style_manual_contiguous_plus_hf_native_auto"]
        self.assertEqual(bad["worker_file_indices"]["0"], [0, 2, 4, 6])
        self.assertEqual(bad["worker_file_indices"]["1"], [8, 10, 12])
        self.assertEqual(bad["files_seen"], 7)
        self.assertEqual(bad["files_missing"], 7)
        self.assertEqual(bad["missing_file_indices"], [1, 3, 5, 7, 9, 11, 13])
        self.assertFalse(bad["covers_all_files_once"])

    def test_manual_contiguous_shard_uses_hf_uneven_split(self):
        self.assertEqual(contiguous_indices(13, 0), list(range(7)))
        self.assertEqual(contiguous_indices(13, 1), list(range(7, 13)))
        projected = project_two_worker_file_assignments(fake_files(13))
        good = projected["native_auto_once"]
        bad = projected["pr27_style_manual_contiguous_plus_hf_native_auto"]
        self.assertEqual(good["files_seen"], 13)
        self.assertEqual(bad["files_seen"], 7)
        self.assertEqual(bad["files_missing"], 6)

    def test_real_repo_tree_probe_pins_exact_repo_and_sample_subtree(self):
        api = FakeHfApi()
        files = fetch_pinned_parquet_tree(api)
        self.assertEqual(files, fake_files())
        self.assertEqual(api.info_calls, [{
            "repo_id": "HuggingFaceFW/fineweb-edu",
            "revision": SOURCE_REVISION
        }])
        self.assertEqual(api.tree_calls, [{
            "repo_id": "HuggingFaceFW/fineweb-edu",
            "path_in_repo": FILE_PREFIX,
            "recursive": True,
            "revision": SOURCE_REVISION,
            "repo_type": "dataset"
        }])

    def test_offline_inventory_freeze_verify_roundtrip(self):
        api = FakeHfApi()
        result = freeze_inventory(api, code_revision="test-research-commit")
        self.assertEqual(result["file_count"], 14)
        self.assertEqual(result["file_inventory_sha256"],
                         canonical_digest(fake_files()))
        self.assertEqual(verify_inventory(result), result)
        self.assertFalse(result["live_hf_dataloader_run"])
        self.assertFalse(result["file_equals_iterable_shard_verified"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text(json.dumps(result))
            self.assertEqual(
                verify_inventory(json.loads(path.read_text())),
                result,
            )

    def test_mutated_file_size_or_projection_rejected(self):
        original = freeze_inventory(FakeHfApi())
        changed = copy.deepcopy(original)
        changed["file_metadata"][0]["size"] += 1
        with self.assertRaisesRegex(ValueError, "manifest SHA256"):
            verify_inventory(changed)
        changed["payload_sha256"] = canonical_digest({
            k: v for k, v in changed.items() if k != "payload_sha256"
        })
        with self.assertRaisesRegex(ValueError, "content digest mismatch"):
            verify_inventory(changed)
        changed = copy.deepcopy(original)
        changed["projection"]["native_auto_once"]["files_seen"] = 2
        changed["payload_sha256"] = canonical_digest({
            k: v for k, v in changed.items() if k != "payload_sha256"
        })
        with self.assertRaisesRegex(ValueError, "projection changed"):
            verify_inventory(changed)

    def test_wrong_revision_or_path_or_file_count_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "NOT Gate I"):
            build_inventory(fake_files(), repo_revision="a" * 40)
        with self.assertRaisesRegex(ValueError, "wrong immutable"):
            fetch_pinned_parquet_tree(FakeHfApi(revision="b" * 40))
        bad = fake_files()
        bad[0]["path"] = "sample/100BT/000_00000.parquet"
        with self.assertRaisesRegex(ValueError, "Out-of-scope"):
            build_inventory(bad, repo_revision=SOURCE_REVISION)
        with self.assertRaisesRegex(ValueError, "excessive"):
            build_inventory(
                fake_files(MAX_PARQUET_FILES + 1),
                repo_revision=SOURCE_REVISION,
            )

    def test_rejects_unsorted_or_duplicate_parquet_source_files(self):
        with self.assertRaisesRegex(ValueError, "sorted, unique"):
            validate_files(list(reversed(fake_files())))
        altered = fake_files()
        altered[-1] = altered[0]
        altered.sort(key=lambda x: x["path"])
        with self.assertRaisesRegex(ValueError, "sorted, unique"):
            validate_files(altered)
        missing_size = copy.deepcopy(fake_files())
        missing_size[0]["size"] = None
        with self.assertRaisesRegex(ValueError, "invalid parquet"):
            validate_files(missing_size)
        negative = copy.deepcopy(fake_files())
        negative[0]["size"] = -1
        with self.assertRaisesRegex(ValueError, "invalid parquet"):
            validate_files(negative)


if __name__ == "__main__":
    unittest.main()
