"""R2 Gate G: simulated two-logical-worker prefetch/commit recovery tests.

No HF/network, no real multiprocessing, no GPU, no OpenMythos PR27 weights.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_prefetch_commit import (
    OrderedCommitPrefetch, compare_with_prefetch_interruption,
    immutable_indexed_tasks,
)
from r2_pr27_stream_resume import digest, local_documents, split_documents
from r2_pr27_tokenizer_contract import create_contract, describe_tokenizer


class Backend:
    def to_str(self):
        return "gate-g-frozen-fake-byte-model"


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
        return {f"v_{i}": i for i in range(32)}

    def get_added_vocab(self):
        return {}

    def encode(self, text, *, add_special_tokens=False):
        return [ord(x) % 31 for x in text]


class GateGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = FakeTokenizer()
        cls.contract = create_contract(describe_tokenizer(
            cls.tokenizer, identifier="gpt2", pinned_revision="a" * 40
        ))
        cls.train, cls.heldout = split_documents(local_documents(64))
        cls.tasks, cls.src = immutable_indexed_tasks(
            cls.train, cls.tokenizer, cls.contract, n_tasks=28
        )

    def pool(self, source=None):
        return OrderedCommitPrefetch(
            self.tasks, source or self.src,
            self.contract["fingerprint_sha256"]
        )

    def test_workers_partition_and_out_of_order_prefetch(self):
        scheduler = self.pool()
        scheduler.complete_out_of_order()
        state = scheduler.speculative_status()
        self.assertEqual(state["committed_next_id"], 0)
        self.assertEqual(state["dispatched_next_id"], 4)
        self.assertEqual(scheduler.completion_history, [3, 2, 1, 0])
        self.assertEqual(state["worker_ids"], {
            "0": 0, "1": 1, "2": 0, "3": 1,
        })
        idx, _, _ = scheduler.ready_next()
        self.assertEqual(idx, 0)
        with self.assertRaisesRegex(ValueError, "only next ready"):
            scheduler.commit_after_optimizer(1)
        scheduler.commit_after_optimizer(0)
        self.assertEqual(scheduler.committed, 1)

    def test_speculative_work_is_redelivered_after_crash(self):
        live = self.pool()
        for index in range(5):
            actual, _, _ = live.ready_next()
            self.assertEqual(actual, index)
            live.commit_after_optimizer(index)
        live.complete_out_of_order()
        state_before = live.speculative_status()
        self.assertGreater(state_before["dispatched_next_id"], 5)
        self.assertIn(5, state_before["completed_uncommitted_ids"])
        saved = live.state_dict()
        recovered = self.pool()
        recovered.load_state_dict(saved)
        self.assertEqual(recovered.state_dict(), saved)
        self.assertEqual(recovered.ready_next()[0], 5)
        self.assertEqual(recovered.worker_for(5), 1)
        self.assertEqual(list(range(5, state_before["dispatched_next_id"])),
                         [5, 6, 7, 8])

    def test_corrupted_cursor_hash_is_rejected(self):
        state = self.pool().state_dict()
        state["next_committed_task_id"] = 2
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.pool().load_state_dict(state)

    def test_resigned_wrong_commit_digest_is_rejected(self):
        scheduler = self.pool()
        scheduler.ready_next()
        scheduler.commit_after_optimizer(0)
        bad = scheduler.state_dict()
        bad["last_committed_chunk_sha256"] = "0" * 64
        bad["state_sha256"] = digest({
            k: v for k, v in bad.items() if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.pool().load_state_dict(bad)

    def test_wrong_source_and_worker_policy_rejected(self):
        pool = self.pool()
        pool.ready_next()
        pool.commit_after_optimizer(0)
        saved = pool.state_dict()
        with self.assertRaisesRegex(ValueError, "source or worker policy"):
            self.pool(source="f" * 64).load_state_dict(saved)
        wrong = copy.deepcopy(saved)
        wrong["workers"] = 3
        wrong["state_sha256"] = digest({
            k: v for k, v in wrong.items() if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "source or worker policy"):
            self.pool().load_state_dict(wrong)

    def test_malformed_token_payload_or_indices_rejected(self):
        changed = list(self.tasks)
        changed[0] = dict(changed[0], x=changed[0]["x"].clone())
        changed[0]["x"][0] = (changed[0]["x"][0] + 1) % 31
        with self.assertRaisesRegex(ValueError, "payload checksum mismatch"):
            OrderedCommitPrefetch(
                changed, self.src, self.contract["fingerprint_sha256"]
            )
        changed = [dict(x) for x in self.tasks]
        changed[0]["task_id"] = 1
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            OrderedCommitPrefetch(
                changed, self.src, self.contract["fingerprint_sha256"]
            )

    def test_actual_adamw_checkpoint_resume_with_prefetch_bitwise(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "gate_g.pt"
            manifest = Path(tmp) / "gate_g.manifest.json"
            result = compare_with_prefetch_interruption(
                self.tokenizer, self.contract,
                checkpoint_path=file, manifest_path=manifest,
                documents=local_documents()
            )
            self.assertEqual(result["workers_simulated"], 2)
            self.assertEqual(result["real_worker_processes_started"], 0)
            self.assertEqual(result["first_replayed_after_crash_task_id"], 5)
            self.assertTrue(result["naive_dispatch_frontier_would_skip_task_ids"])
            self.assertTrue(result["trajectories_bitwise_equal"])
            self.assertEqual(result["max_abs_loss_difference"], 0.0)
            self.assertTrue(result["model_params_bitwise_equal"])
            self.assertTrue(result["optimizer_state_bitwise_equal"])
            self.assertTrue(result["committed_cursor_bitwise_equal"])
            self.assertTrue(result["python_torch_rng_bitwise_equal"])
            self.assertTrue(file.exists())
            self.assertTrue(manifest.exists())

    def test_insufficient_tasks_rejected(self):
        with self.assertRaisesRegex(ValueError, "Not enough immutable"):
            immutable_indexed_tasks(
                self.train[:1], self.tokenizer, self.contract,
                n_tasks=10_000
            )


if __name__ == "__main__":
    unittest.main()
