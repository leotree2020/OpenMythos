"""Gate L: HF double-shard source coverage regression and two OS worker test.

No network, no real text, no checkpoint/model/optimizer/GPU. Uses synthetic
source identity fixtures only; CLI runs on pinned Gate I hashed doc IDs.
"""
import sys
import unittest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_double_shard_coverage import (
    SHARDS, WORKERS, CoverageProbe, collect_worker_coverage, compare_modes,
    make_digest_source, summarize,
)
from r2_pr27_stream_resume import digest, split_documents


def fake_records(n=32):
    return [{"id": f"synthetic-local-hash-id-{i:03d}",
             "text": "TEST FIXTURE ONLY"} for i in range(n)]


class GateLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = fake_records()
        cls.train, cls.excluded = split_documents(cls.records)
        cls.source, cls.ids = make_digest_source(cls.train)

    def test_eight_shard_source_contains_only_identity_hashes(self):
        self.assertEqual(self.source.num_shards, SHARDS)
        rows = list(self.source)
        self.assertEqual(len(rows), len(self.train))
        self.assertEqual(set(rows[0]), {"source_digest"})
        self.assertEqual(set(r["source_digest"] for r in rows), set(self.ids))
        self.assertNotIn("TEST FIXTURE", repr(rows))

    def test_fails_on_missing_source_or_duplicates(self):
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            make_digest_source(self.train[:5])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            make_digest_source(self.train + [self.train[0]])

    def test_rejects_unknown_mode(self):
        with self.assertRaisesRegex(ValueError, "Invalid source"):
            CoverageProbe(self.source, "unsupported")

    def test_summary_distinguishes_committed_source_coverage(self):
        pids = {"0": 1001, "1": 1002}
        rows = [
            {"doc": h, "worker": i % 2, "before_auto": SHARDS}
            for i, h in enumerate(self.ids)
        ]
        result = summarize(self.ids, rows, pids)
        self.assertTrue(result["all_docs_covered_once"])
        self.assertEqual(result["missing_docs"], 0)
        self.assertEqual(result["duplicate_docs"], 0)
        result_half = summarize(self.ids, rows[:8], pids)
        self.assertFalse(result_half["all_docs_covered_once"])
        self.assertEqual(result_half["missing_docs"], len(self.ids) - 8)
        self.assertEqual(result_half["missing_source_order_indices"],
                         list(range(8, len(self.ids))))

    def test_rejects_duplicate_or_forged_worker_records(self):
        pids = {"0": 1001, "1": 1002}
        rows = [
            {"doc": self.ids[0], "worker": 0, "before_auto": SHARDS},
            {"doc": self.ids[0], "worker": 1, "before_auto": SHARDS},
        ]
        with self.assertRaisesRegex(ValueError, "multiple"):
            summarize(self.ids, rows, pids)
        rows[1]["doc"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            summarize(self.ids, rows, pids)

    def test_rejects_invalid_provenance(self):
        with self.assertRaisesRegex(ValueError, "source digest"):
            compare_modes(
                self.records, source_sha="main",
                revision="a" * 40,
                expected_train=len(self.train),
                expected_excluded=len(self.excluded),
            )
        with self.assertRaisesRegex(ValueError, "source version"):
            compare_modes(
                self.records, source_sha="a" * 64,
                revision="main",
                expected_train=len(self.train),
                expected_excluded=len(self.excluded),
            )

    @unittest.skipUnless(sys.platform == "linux", "Gate L requires Linux OS workers")
    def test_real_os_workers_show_silent_double_partition_loss(self):
        report = compare_modes(
            self.records, source_sha=digest(self.records), revision="a" * 40,
            expected_train=len(self.train),
            expected_excluded=len(self.excluded),
        )
        good = report["native_hf_auto_once"]
        bad = report["upstream_style_explicit_plus_hf_auto"]
        self.assertEqual(report["local_arrow_shards"], 8)
        self.assertTrue(good["all_docs_covered_once"])
        self.assertEqual(good["observed_docs"], len(self.train))
        self.assertEqual(good["missing_docs"], 0)
        self.assertGreater(bad["missing_docs"], 0)
        self.assertLess(bad["observed_docs"], len(self.train))
        self.assertEqual(bad["source_shards_before_hf_auto"], [4])
        self.assertEqual(good["source_shards_before_hf_auto"], [8])
        self.assertEqual(bad["duplicate_docs"], 0)
        self.assertEqual(bad["unknown_docs"], 0)
        for arm in (good, bad):
            pids = arm["actual_worker_pids"]
            self.assertEqual(set(pids), {"0", "1"})
            self.assertNotEqual(pids["0"], pids["1"])
            self.assertTrue(all(n > 0 for n in arm["per_worker_document_counts"].values()))
        self.assertTrue(report["counterexample_demonstrated"])
        self.assertFalse(report["true_remote_parquet_coverage_measured"])
        self.assertTrue(report["no_model_training"])


if __name__ == "__main__":
    unittest.main()
