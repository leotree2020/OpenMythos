"""R2 Gate H: tests for real two-OS-process DataLoader resume.

Five pure fail-closed checks and one real spawned subprocess checkpoint
recovery. No network/GPU; actual multiprocess test runs on Linux only.
"""
import copy
import multiprocessing as mp
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_prefetch_commit import immutable_indexed_tasks
from r2_pr27_real_dataloader_resume import (
    DurableOptimizerCursor, PreindexedWorkerDataset,
    compare_actual_multiprocess_resume, make_loader,
    observed_unused_fetches, shared_read_snapshot,
)
from r2_pr27_stream_resume import digest, local_documents, split_documents
from r2_pr27_tokenizer_contract import create_contract, describe_tokenizer


class Backend:
    def to_str(self):
        return "fixed-r2-gate-h-test-rules"


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
        return {f"b_{i}": i for i in range(32)}

    def get_added_vocab(self):
        return {}

    def encode(self, text, *, add_special_tokens=False):
        return [ord(char) % 31 for char in text]


class GateHTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(min(4, torch.get_num_threads()))
        cls.tokenizer = FakeTokenizer()
        cls.contract = create_contract(describe_tokenizer(
            cls.tokenizer, identifier="gpt2", pinned_revision="a" * 40
        ))
        train, cls.heldout = split_documents(local_documents())
        cls.items, cls.source_sha = immutable_indexed_tasks(
            train, cls.tokenizer, cls.contract, n_tasks=32
        )

    def cursor(self):
        return DurableOptimizerCursor(
            self.items, self.source_sha, self.contract["fingerprint_sha256"]
        )

    def test_optimizer_ack_moves_only_after_right_task(self):
        c = self.cursor()
        with self.assertRaisesRegex(ValueError, "Only the next"):
            c.ack_after_optimizer(1, self.items[1]["chunk_sha256"])
        with self.assertRaisesRegex(ValueError, "payload SHA"):
            c.ack_after_optimizer(0, "f" * 64)
        self.assertEqual(c.emitted, 0)
        c.ack_after_optimizer(0, self.items[0]["chunk_sha256"])
        self.assertEqual(c.emitted, 1)

    def test_durable_cursor_has_no_fetched_worker_offset(self):
        c = self.cursor()
        for idx in range(5):
            c.ack_after_optimizer(idx, self.items[idx]["chunk_sha256"])
        state = c.state_dict()
        self.assertEqual(state["next_committed_task_id"], 5)
        self.assertEqual(state["workers"], 2)
        self.assertEqual(state["prefetch_factor"], 2)
        self.assertNotIn("worker_pids", state)
        self.assertNotIn("last_fetched_id", state)
        other = self.cursor()
        other.load_state_dict(state)
        self.assertEqual(other.state_dict(), state)
        self.assertEqual(other.emitted, 5)

    def test_corrupted_cursor_or_source_rejected(self):
        c = self.cursor()
        c.ack_after_optimizer(0, self.items[0]["chunk_sha256"])
        snap = c.state_dict()
        broken = copy.deepcopy(snap)
        broken["next_committed_task_id"] = 7
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.cursor().load_state_dict(broken)
        modified_source = self.cursor()
        modified_source.source_sha = "0" * 64
        with self.assertRaisesRegex(ValueError, "source/worker policy"):
            modified_source.load_state_dict(snap)

    def test_bad_payload_and_last_committed_hash_rejected(self):
        changed = list(self.items)
        first = dict(changed[0])
        first["x"] = first["x"].clone()
        first["x"][0] = (first["x"][0] + 2) % 31
        changed[0] = first
        with self.assertRaisesRegex(ValueError, "Indexed training task corrupted"):
            DurableOptimizerCursor(
                changed, self.source_sha, self.contract["fingerprint_sha256"]
            )
        snap = self.cursor().state_dict()
        bad = dict(snap)
        bad["last_committed_chunk_sha256"] = "x"
        bad["state_sha256"] = digest({
            k: v for k, v in bad.items() if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "last committed"):
            self.cursor().load_state_dict(bad)

    def test_shared_fetch_evidence_excludes_committed(self):
        context = mp.get_context("spawn")
        counts = context.Array("i", 9, lock=True)
        with counts.get_lock():
            counts[0] += 1
            counts[1] += 1
            counts[5] += 1
            counts[7] += 1
        snapshot = shared_read_snapshot(counts)
        self.assertEqual(observed_unused_fetches(snapshot, 5), [5, 7])

    @unittest.skipUnless(sys.platform == "linux", "Gate H Linux-only spawned worker smoke")
    def test_actual_two_os_worker_loader_and_resume_bitwise(self):
        with tempfile.TemporaryDirectory() as td:
            result = compare_actual_multiprocess_resume(
                self.tokenizer, self.contract,
                checkpoint_path=Path(td) / "real-workers.pt",
                manifest_path=Path(td) / "real-workers.manifest.json",
                records=local_documents()
            )
            for pids in result["actual_os_worker_processes_observed_per_run"].values():
                self.assertEqual(len(set(pids)), 2)
            for workers in result["worker_ids_seen_in_each_run"].values():
                self.assertEqual(workers, [0, 1])
            self.assertTrue(result["actual_worker_fetched_but_uncommitted"])
            self.assertTrue(all(
                i >= 5 for i in result["actual_worker_fetched_but_uncommitted"]
            ))
            self.assertEqual(result["first_resumed_task_id"], 5)
            self.assertEqual(result["max_abs_loss_difference"], 0.0)
            for flag in (
                "trace_bitwise_equal",
                "model_parameters_bitwise_equal",
                "adamw_state_bitwise_equal",
                "committed_cursor_bitwise_equal",
                "python_torch_rng_bitwise_equal",
            ):
                self.assertTrue(result[flag], flag)
            self.assertEqual(result["crash_type"],
                             "controlled iterator interruption/recreation; no SIGKILL")
            self.assertFalse(result["fineweb_data_consumed"])


if __name__ == "__main__":
    unittest.main()
