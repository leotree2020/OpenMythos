"""R2 Gate I real FineWeb source provenance tests; NO network or corpus fetch."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_fineweb_source_snapshot import (
    DATASET_CONFIG, DATASET_ID, DATASET_SPLIT, MAX_SCANNED_DOCS,
    SELECTED_DOCS, capture_bounded_documents,
    check_manifest_and_snapshot, freeze, make_manifest,
    read_verified_snapshot, sha256_bytes, snapshot_blob,
    validate_revision,
)


def raw_fixture(num=50):
    return [
        {"id": f"source-{i}", "text": (
            f"Document number {i}. Training fixtures only, not a real "
            "FineWeb corpus or an evaluation split."
        )}
        for i in range(num)
    ]


def manifest_fixture():
    rows, stats = capture_bounded_documents(raw_fixture())
    return rows, make_manifest(
        rows, stats, resolved_revision="a" * 40,
        requested_revision="main", working_commit="local-fixture",
        license_label="odc-by"
    )


class FakeAPI:
    def __init__(self, sha="a"*40):
        self.sha = sha
        self.calls = []

    def dataset_info(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(sha=self.sha, cardData={"license": "odc-by"})


class GateISourceSnapshotTests(unittest.TestCase):
    def test_capture_has_frozen_document_budget_and_order(self):
        rows, stats = capture_bounded_documents(raw_fixture(40))
        self.assertEqual(len(rows), SELECTED_DOCS)
        self.assertEqual(stats["rows_scanned"], SELECTED_DOCS)
        self.assertEqual(rows[0]["source_row_index"], 0)
        self.assertEqual(rows[-1]["source_row_index"], 31)
        self.assertEqual(rows[0]["text_sha256"],
                         sha256_bytes(rows[0]["text"].encode()))
        self.assertEqual(stats["empty_rows_skipped"], 0)

    def test_skips_empty_and_large_without_changing_source_indices(self):
        records = raw_fixture(40)
        records[1]["text"] = "\n"
        records[3]["text"] = "very large source " * 30
        rows, stats = capture_bounded_documents(
            records, max_doc_bytes=180
        )
        self.assertEqual(len(rows), 32)
        self.assertEqual(stats["empty_rows_skipped"], 1)
        self.assertEqual(stats["oversized_rows_skipped"], 1)
        self.assertEqual(stats["rows_scanned"], 34)
        self.assertEqual(rows[2]["source_row_index"], 4)

    def test_insufficient_docs_or_unknown_source_schema_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "eligible"):
            capture_bounded_documents(raw_fixture(8))
        bad = raw_fixture(35)
        bad[2]["text"] = None
        with self.assertRaisesRegex(ValueError, "no string text"):
            capture_bounded_documents(bad)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            capture_bounded_documents(
                raw_fixture(), max_total_bytes=100
            )

    def test_full_snapshot_round_trip_matches_every_source_doc(self):
        rows, manifest = manifest_fixture()
        output = check_manifest_and_snapshot(
            manifest, snapshot_blob(rows)
        )
        self.assertEqual(output, rows)
        self.assertEqual(manifest["split"], "train")
        self.assertEqual(manifest["source"], DATASET_ID)
        self.assertEqual(manifest["config"], DATASET_CONFIG)
        self.assertEqual(manifest["snapshot_sha256"],
                         sha256_bytes(snapshot_blob(rows)))

    def test_changed_text_fails_before_source_payload_is_used(self):
        rows, manifest = manifest_fixture()
        new_content = snapshot_blob(rows).replace(
            b"Document number 3", b"Document number 8", 1
        )
        with self.assertRaisesRegex(ValueError, "Snapshot SHA256"):
            check_manifest_and_snapshot(manifest, new_content)
        bad = copy.deepcopy(rows)
        bad[5]["text"] += " malicious mutation"
        updated = copy.deepcopy(manifest)
        updated["snapshot_sha256"] = sha256_bytes(snapshot_blob(bad))
        updated["snapshot_bytes"] = len(snapshot_blob(bad))
        with self.assertRaisesRegex(ValueError, "Document content checksum"):
            check_manifest_and_snapshot(updated, snapshot_blob(bad))

    def test_wrong_dataset_revision_policy_or_doc_order_rejected(self):
        rows, manifest = manifest_fixture()
        changed = copy.deepcopy(manifest)
        changed["split"] = "validation"
        with self.assertRaisesRegex(ValueError, "Wrong source"):
            check_manifest_and_snapshot(changed, snapshot_blob(rows))
        changed = copy.deepcopy(manifest)
        changed["selection_policy"]["selected_documents"] = 24
        with self.assertRaisesRegex(ValueError, "selection policy"):
            check_manifest_and_snapshot(changed, snapshot_blob(rows))
        changed = copy.deepcopy(manifest)
        changed["resolved_revision"] = "main"
        with self.assertRaisesRegex(ValueError, "immutable"):
            check_manifest_and_snapshot(changed, snapshot_blob(rows))
        reordered = copy.deepcopy(rows)
        reordered[1]["source_row_index"] = 0
        changed = copy.deepcopy(manifest)
        changed["snapshot_sha256"] = sha256_bytes(snapshot_blob(reordered))
        changed["snapshot_bytes"] = len(snapshot_blob(reordered))
        with self.assertRaisesRegex(ValueError, "order"):
            check_manifest_and_snapshot(changed, snapshot_blob(reordered))

    def test_dependency_injected_freeze_pins_sha_and_offline_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fineweb"
            api = FakeAPI()
            observed = []
            def loader(dataset_id, *, name, split, streaming, revision):
                observed.append((dataset_id, name, split, streaming, revision))
                return raw_fixture(SELECTED_DOCS + 1)
            with patch("r2_fineweb_source_snapshot.commit_id",
                       return_value="test-commit"):
                manifest = freeze(
                    target, repo=Path(tmp), requested_revision="main",
                    api=api, dataset_loader=loader
                )
            self.assertEqual(api.calls, [{
                "repo_id": DATASET_ID, "revision": "main"
            }])
            self.assertEqual(observed, [(
                DATASET_ID, DATASET_CONFIG, DATASET_SPLIT, True, "a"*40
            )])
            self.assertEqual(manifest["resolved_revision"], "a" * 40)
            readback, rows = read_verified_snapshot(target)
            self.assertEqual(readback, manifest)
            self.assertEqual(len(rows), SELECTED_DOCS)
            self.assertEqual(readback["source_license_metadata"], "odc-by")
            with self.assertRaises(FileExistsError):
                freeze(target, repo=Path(tmp), requested_revision="main",
                       api=api, dataset_loader=loader)

    def test_fetch_failure_leaves_no_misleading_final_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "source"
            api = FakeAPI(sha="invalid-ref")
            with self.assertRaisesRegex(ValueError, "immutable"):
                freeze(target, repo=Path(tmp), requested_revision="main",
                       api=api, dataset_loader=lambda *a, **k: raw_fixture())
            self.assertFalse(target.exists())
            api = FakeAPI()
            with self.assertRaisesRegex(RuntimeError, "upstream stream failed"):
                freeze(
                    target, repo=Path(tmp), requested_revision="main",
                    api=api,
                    dataset_loader=lambda *a, **k:
                        (_ for _ in ()).throw(RuntimeError("upstream stream failed"))
                )
            self.assertFalse(target.exists())

    def test_wrong_sha_format_and_suspicious_doc_id_rejected(self):
        self.assertEqual(validate_revision("A" * 40), "a" * 40)
        for bad in ("main", "ff" * 19, "", None):
            with self.assertRaisesRegex(ValueError, "immutable"):
                validate_revision(bad)
        items = raw_fixture()
        items[0]["id"] = object()
        with self.assertRaisesRegex(ValueError, "document ID type"):
            capture_bounded_documents(items)


if __name__ == "__main__":
    unittest.main()
