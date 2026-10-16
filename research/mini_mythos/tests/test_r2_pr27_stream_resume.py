"""R2 Gate F: offline one-worker exact packed cursor, RNG + AdamW resume.

No network, no GPU or 118M model; uses deterministic fake tokenizer/32 vocab.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_tokenizer_contract import create_contract, describe_tokenizer
from r2_pr27_stream_resume import (
    PackedCursor, compare_uninterrupted_with_resume, digest,
    local_documents, split_documents
)


class Backend:
    def to_str(self):
        return "gate-f-test-byte-modulo"


class Tokenizer:
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
        return {f"t_{i}": i for i in range(32)}

    def get_added_vocab(self):
        return {}

    def encode(self, text, *, add_special_tokens=False):
        return [ord(x) % 31 for x in text]


class GateFStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = Tokenizer()
        fp = describe_tokenizer(
            cls.tokenizer, identifier="gpt2", pinned_revision="a" * 40
        )
        cls.contract = create_contract(fp)
        cls.records = local_documents(64)
        cls.train, cls.holdout = split_documents(cls.records)

    def new_stream(self, train=None):
        return PackedCursor(
            self.train if train is None else train, self.tokenizer,
            seq_len=16, contract_sha=self.contract["fingerprint_sha256"],
            eos_id=31
        )

    def test_fixed_train_holdout_deterministic_and_disjoint(self):
        another_train, another_heldout = split_documents(
            copy.deepcopy(self.records))
        self.assertEqual(another_train, self.train)
        self.assertEqual(another_heldout, self.holdout)
        self.assertGreater(len(another_heldout), 0)
        self.assertFalse(set(d["id"] for d in self.train) &
                         set(d["id"] for d in self.holdout))
        with self.assertRaisesRegex(ValueError, "Duplicate document"):
            split_documents(self.records + [self.records[0]])

    def test_packed_context_retains_exact_one_overlap_token(self):
        stream = self.new_stream()
        x1, y1 = stream.next_chunk()
        x2, y2 = stream.next_chunk()
        self.assertTrue(torch.equal(x1[1:], y1[:-1]))
        self.assertTrue(torch.equal(x2[1:], y2[:-1]))
        self.assertEqual(int(y1[-1]), int(x2[0]))
        self.assertEqual(x1.numel(), 16)
        self.assertEqual(stream.emitted, 2)

    def test_cursor_roundtrip_restores_same_next_window(self):
        before = self.new_stream()
        for _ in range(9):
            before.next_chunk()
        snapshot = before.state_dict()
        after = self.new_stream()
        after.load_state_dict(snapshot, strict_replay=True)
        self.assertEqual(after.state_dict(), snapshot)
        for _ in range(4):
            x0, y0 = before.next_chunk()
            x1, y1 = after.next_chunk()
            self.assertTrue(torch.equal(x0, x1))
            self.assertTrue(torch.equal(y0, y1))
        self.assertEqual(after.state_dict(), before.state_dict())

    def test_corrupted_cursor_checksum_refused(self):
        stream = self.new_stream()
        stream.next_chunk()
        state = stream.state_dict()
        state["buffer_ids"][0] = 17
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.new_stream().load_state_dict(state)

    def test_cursor_source_or_vocab_drift_refused_even_if_resigned(self):
        stream = self.new_stream()
        stream.next_chunk()
        bad = stream.state_dict()
        bad["source_sha"] = "c" * 64
        bad["state_sha256"] = digest({
            k: v for k, v in bad.items() if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "metadata drift"):
            self.new_stream().load_state_dict(bad)
        other = self.new_stream()
        other.contract_sha = "a" * 64
        with self.assertRaisesRegex(ValueError, "metadata drift"):
            other.load_state_dict(stream.state_dict())

    def test_replay_detects_syntactically_valid_but_wrong_buffer(self):
        stream = self.new_stream()
        for _ in range(5):
            stream.next_chunk()
        wrong = stream.state_dict()
        wrong["buffer_ids"][0] = (
            int(wrong["buffer_ids"][0]) + 1
        ) % 31
        wrong["state_sha256"] = digest({
            k: v for k, v in wrong.items() if k != "state_sha256"
        })
        with self.assertRaisesRegex(ValueError, "differs from source replay"):
            self.new_stream().load_state_dict(wrong)

    def test_actual_cpu_adamw_resume_matches_uninterrupted_bitwise(self):
        with tempfile.TemporaryDirectory() as td:
            checkpoint = Path(td) / "resume.pt"
            sidecar = Path(td) / "resume.manifest.json"
            outcome = compare_uninterrupted_with_resume(
                self.tokenizer, self.contract,
                ckpt_path=checkpoint, sidecar_path=sidecar,
                total=12, cutoff=5, records=self.records
            )
            self.assertTrue(outcome["traces_exactly_equal"])
            self.assertEqual(outcome["max_abs_loss_difference"], 0.)
            self.assertTrue(outcome["model_parameters_bitwise_equal"])
            self.assertTrue(outcome["optimizer_state_bitwise_equal"])
            self.assertTrue(outcome["stream_cursor_exactly_equal"])
            self.assertTrue(outcome["python_and_torch_rng_exactly_equal"])
            self.assertTrue(checkpoint.is_file())
            self.assertTrue(sidecar.is_file())

    def test_restore_rejects_different_stream_source(self):
        original = self.new_stream()
        original.next_chunk()
        changed = copy.deepcopy(self.train)
        changed[0]["text"] += " CHANGED"
        modified = self.new_stream(train=changed)
        with self.assertRaisesRegex(ValueError, "metadata drift"):
            modified.load_state_dict(original.state_dict())


if __name__ == "__main__":
    unittest.main()
