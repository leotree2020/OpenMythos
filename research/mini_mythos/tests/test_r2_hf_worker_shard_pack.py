"""R2 Gate K: offline HF IterableDataset worker-shard/pack resume tests.

An integration test runs REAL OS worker subprocesses and locally constructed
HF IterableDataset shards. No HF Hub request, no GPU, no PR27 source changes.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_hf_worker_shard_pack import (
    CHUNK_LEN, CommittedHFStream, WORKERS,
    audit_local_hf_worker_partition, build_local_hf_source,
    compare_worker_shard_resume,
)
from r2_pr27_stream_resume import digest, local_documents, split_documents
from r2_pr27_tokenizer_contract import create_contract, describe_tokenizer


class Backend:
    def to_str(self):
        return "r2-gate-k-frozen-fake-fast-encoding"


class FakeTokenizer:
    is_fast = True
    bos_token = "<eos>"
    eos_token = "<eos>"
    unk_token = "<eos>"
    pad_token = "<eos>"
    eos_token_id = 31
    bos_token_id = 31
    unk_token_id = 31
    pad_token_id = 31
    all_special_ids = [31]
    vocab_size = 32
    backend_tokenizer = Backend()

    def __len__(self):
        return 32

    def get_vocab(self):
        return {f"token-{i}": i for i in range(32)}

    def get_added_vocab(self):
        return {}

    def encode(self, text, *, add_special_tokens=False):
        return [ord(char) % 31 for char in text]


class GateKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(min(4, torch.get_num_threads()))
        cls.tok = FakeTokenizer()
        cls.contract = create_contract(describe_tokenizer(
            cls.tok, identifier="gpt2",
            pinned_revision="a" * 40
        ))
        cls.docs = local_documents(64)
        cls.sha = digest(cls.docs)

    def cursor(self):
        return CommittedHFStream(
            source_sha=self.sha,
            contract_sha=self.contract["fingerprint_sha256"],
            seq_len=CHUNK_LEN
        )

    def test_cursor_is_only_committed_batch_hashes(self):
        cursor = self.cursor()
        for i in range(5):
            cursor.ack(i, "a" * 64)
        result = cursor.state_dict()
        self.assertEqual(result["next_committed_global_batch"], 5)
        self.assertEqual(result["emitted_chunks"], 5)
        self.assertEqual(len(result["committed_chunk_sha256"]), 5)
        self.assertNotIn("next_dispatched_id", result)
        self.assertNotIn("worker_prefetch_offsets", result)
        self.assertEqual(result["num_workers"], 2)
        self.assertEqual(result["prefetch_factor"], 2)
        other = self.cursor()
        other.load_state_dict(result)
        self.assertEqual(other.state_dict(), result)

    def test_cursor_wrong_order_and_missing_sha_fails_closed(self):
        cursor = self.cursor()
        with self.assertRaisesRegex(ValueError, "next sequential"):
            cursor.ack(3, "b" * 64)
        with self.assertRaisesRegex(ValueError, "Invalid committed"):
            cursor.ack(0, "not-sha")
        self.assertEqual(cursor.emitted, 0)

    def test_cursor_corrupted_digest_rejected(self):
        cursor = self.cursor()
        cursor.ack(0, "b" * 64)
        wrong = cursor.state_dict()
        wrong["next_committed_global_batch"] = 7
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.cursor().load_state_dict(wrong)

    def test_cursor_resigned_policy_or_source_mismatch_rejected(self):
        cursor = self.cursor()
        cursor.ack(0, "c" * 64)
        state = cursor.state_dict()
        other = self.cursor()
        other.source_sha = "f" * 64
        with self.assertRaisesRegex(ValueError, "source_sha256"):
            other.load_state_dict(state)
        changed = copy.deepcopy(state)
        changed["num_workers"] = 3
        changed["state_sha256"] = digest({
            k: v for k, v in changed.items()
            if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "num_workers"):
            self.cursor().load_state_dict(changed)

    def test_cursor_resigned_wrong_batch_history_rejected(self):
        cursor = self.cursor()
        for i in range(5):
            cursor.ack(i, "a" * 64)
        state = cursor.state_dict()
        changed = copy.deepcopy(state)
        changed["committed_chunk_sha256"] = []
        changed["state_sha256"] = digest({
            k: v for k, v in changed.items()
            if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "chunks invalid"):
            self.cursor().load_state_dict(changed)

    def test_local_hf_dataset_is_iterable_and_two_shards(self):
        from datasets import IterableDataset
        train, excluded = split_documents(self.docs)
        source = build_local_hf_source(train)
        self.assertIsInstance(source, IterableDataset)
        self.assertGreater(len(train), 12)
        part0 = list(source.shard(num_shards=2, index=0))
        part1 = list(source.shard(num_shards=2, index=1))
        texts0 = [d["text"] for d in part0]
        texts1 = [d["text"] for d in part1]
        self.assertFalse(set(texts0) & set(texts1))
        self.assertEqual(sorted(texts0 + texts1),
                         sorted([d["text"] for d in train]))
        self.assertEqual(len(part0) + len(part1), len(train))

    def test_native_hf_worker_partitions_cover_all_docs_without_duplicates(self):
        train, _ = split_documents(self.docs)
        source = build_local_hf_source(train)
        audit = audit_local_hf_worker_partition(
            source, [item["id"] for item in train]
        )
        self.assertTrue(audit["all_source_doc_ids_covered_once"])
        self.assertEqual(audit["dataset_source_shards"], WORKERS)
        self.assertEqual(sum(audit["per_worker_document_counts"]), len(train))
        self.assertTrue(all(n > 0 for n in audit["per_worker_document_counts"]))
        self.assertIn("NATIVE_AUTOSHARD", audit["partition_policy"])

    def test_explicit_worker_shard_would_leave_only_one_native_hf_shard(self):
        # Catches the documented GitHub Codespaces Gate K failure:
        # HF source.shard(2, worker_id) => 1 shard; HF will automatically
        # split that ONE shard again between TWO DataLoader workers.
        train, _ = split_documents(self.docs)
        source = build_local_hf_source(train)
        self.assertEqual(source.num_shards, 2)
        for worker_id in range(WORKERS):
            already_sharded = source.shard(
                num_shards=WORKERS, index=worker_id
            )
            self.assertEqual(already_sharded.num_shards, 1)
            self.assertLess(already_sharded.num_shards, WORKERS)

    def test_local_hf_dataset_rejects_duplicate_records(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_local_hf_source(
                [self.docs[0], self.docs[0]]
            )

    @unittest.skipUnless(sys.platform == "linux", "Gate K requires Linux")
    def test_real_worker_shard_then_pack_resume_matches_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "gate_k.pt"
            manifest = Path(tmp) / "gate_k.json"
            report = compare_worker_shard_resume(
                self.tok, self.contract, self.docs,
                checkpoint_path=ckpt, manifest_path=manifest,
                snapshot_sha=self.sha
            )
            self.assertTrue(ckpt.is_file())
            self.assertTrue(manifest.is_file())
            self.assertEqual(report["actual_os_workers"], WORKERS)
            self.assertTrue(
                report["hf_native_auto_shard_audit"]["all_source_doc_ids_covered_once"]
            )
            self.assertEqual(
                sum(report["hf_native_auto_shard_audit"]["per_worker_document_counts"]),
                report["development_training_documents"]
            )
            self.assertTrue(report["upstream_explicit_shard_double_partition_risk"])
            for pids in report["worker_pids"].values():
                self.assertEqual(len(pids), 2)
                self.assertNotEqual(pids[0], pids[1])
            self.assertGreater(
                report["worker_local_prefetched_but_uncommitted_count"], 0
            )
            self.assertEqual(report["first_resumed_global_batch"], 5)
            self.assertTrue(report["continuous_vs_resumed_trace_bitwise_equal"])
            self.assertEqual(report["maximum_absolute_loss_difference"], 0.0)
            self.assertTrue(report["model_params_bitwise_equal"])
            self.assertTrue(report["adamw_state_bitwise_equal"])
            self.assertTrue(report["committed_cursor_bitwise_equal"])
            self.assertTrue(report["python_torch_rng_bitwise_equal"])
            self.assertGreater(
                report["global_pack_vs_worker_shard_pack_mismatched_first_n_chunks"], 0
            )
            self.assertFalse(report["hf_live_streaming_used"])


if __name__ == "__main__":
    unittest.main()
