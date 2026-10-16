"""R2 PR27 GPT2 revision/token-ID/embedding contract offline tests.

These tests never fetch a tokenizer or weight file. A fake FastTokenizer
tests fail-closed identity rules independently from Hugging Face availability.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_tokenizer_contract import (
    CONTRACT_VERSION, PROBES, checkpoint_tokenizer_guard, create_contract,
    describe_tokenizer, sha256_canonical, validate_contract, validate_source_id
)


REVISION = "a" * 40


class Backend:
    def __init__(self, serialized):
        self.serialized = serialized

    def to_str(self):
        return self.serialized


class FakeFastTokenizer:
    is_fast = True
    bos_token = "<eos>"
    eos_token = "<eos>"
    unk_token = "<eos>"
    pad_token = "<eos>"
    bos_token_id = 2
    eos_token_id = 2
    unk_token_id = 2
    pad_token_id = 2
    all_special_ids = [2]
    vocab_size = 3

    def __init__(self, vocab=None, backend="tokenizer-rules-v1"):
        self.vocab = vocab or {"a": 0, "b": 1, "<eos>": 2}
        self.backend_tokenizer = Backend(backend)

    def __len__(self):
        return len(self.vocab)

    def get_vocab(self):
        return dict(self.vocab)

    def get_added_vocab(self):
        return {}

    def encode(self, text, *, add_special_tokens=False):
        return [0 if char.isspace() else 1 for char in text]


class R2TokenizerContractTests(unittest.TestCase):
    def setUp(self):
        self.actual = describe_tokenizer(
            FakeFastTokenizer(), identifier="gpt2",
            pinned_revision=REVISION
        )
        self.contract = create_contract(self.actual)

    def test_fingerprint_and_identical_eval_tokenizer(self):
        self.assertEqual(len(PROBES), 6)
        self.assertEqual(self.contract["version"], CONTRACT_VERSION)
        self.assertEqual(self.actual["vocab_size_property"], 3)
        self.assertEqual(self.actual["len_tokenizer"], 3)
        self.assertEqual(len(self.actual["encoding_probes"]), len(PROBES))
        self.assertTrue(validate_contract(
            self.contract, candidate=copy.deepcopy(self.actual),
            embedding_rows=3
        ))

    def test_reject_token_id_swap_with_same_vocabulary_size(self):
        switched = describe_tokenizer(
            FakeFastTokenizer(vocab={"a": 1, "b": 0, "<eos>": 2}),
            identifier="gpt2", pinned_revision=REVISION
        )
        self.assertEqual(switched["len_tokenizer"], self.actual["len_tokenizer"])
        with self.assertRaisesRegex(ValueError, "token_to_id_sha256"):
            validate_contract(self.contract, candidate=switched)

    def test_reject_backend_rule_change_even_with_same_token_ids(self):
        changed = describe_tokenizer(
            FakeFastTokenizer(backend="tokenizer-rules-v2"),
            identifier="gpt2", pinned_revision=REVISION
        )
        with self.assertRaisesRegex(ValueError, "backend_serialization_sha256"):
            validate_contract(self.contract, candidate=changed)

    def test_reject_mutable_revision_and_unapproved_tokenizer(self):
        for bad in ("main", "", "deadbeef"):
            with self.assertRaisesRegex(ValueError, "40-hex"):
                validate_source_id("gpt2", bad)
        with self.assertRaisesRegex(ValueError, "gpt2"):
            validate_source_id("distilgpt2", REVISION)

    def test_reject_forged_contract_hash(self):
        changed = copy.deepcopy(self.contract)
        changed["fingerprint"]["special_tokens"]["pad_token_id"] = 1
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            validate_contract(changed, candidate=self.actual)

    def test_reject_wrong_special_tokens_even_when_vocab_identical(self):
        changed = copy.deepcopy(self.actual)
        changed["special_tokens"]["pad_token_id"] = 1
        with self.assertRaisesRegex(ValueError, "special_tokens"):
            validate_contract(self.contract, candidate=changed)

    def test_reject_missing_or_insufficient_embedding_vocab(self):
        with self.assertRaisesRegex(ValueError, "embedding vocab"):
            validate_contract(self.contract, candidate=self.actual,
                              embedding_rows=2)
        with self.assertRaisesRegex(ValueError, "embedding vocab"):
            validate_contract(self.contract, candidate=self.actual,
                              embedding_rows=4)

    def test_checkpoint_identity_must_be_serialized_and_match(self):
        checkpoint = {
            "tokenizer_contract_sha256": self.contract["fingerprint_sha256"],
            "tokenizer_revision": REVISION,
            "embedding_vocab_rows": 3,
        }
        self.assertTrue(checkpoint_tokenizer_guard(checkpoint, self.contract))
        for field, bad in (
            ("tokenizer_contract_sha256", "9" * 64),
            ("tokenizer_revision", "b" * 40),
            ("embedding_vocab_rows", 2),
        ):
            altered = dict(checkpoint)
            altered[field] = bad
            with self.assertRaises(ValueError):
                checkpoint_tokenizer_guard(altered, self.contract)
        with self.assertRaises(ValueError):
            checkpoint_tokenizer_guard({}, self.contract)

    def test_tokenizer_extra_ids_beyond_pr27_embedding(self):
        t = FakeFastTokenizer(vocab={"a": 0, "b": 1, "<eos>": 2, "<new>": 3})
        with self.assertRaisesRegex(ValueError, "added tokens"):
            describe_tokenizer(t, identifier="gpt2", pinned_revision=REVISION)

    def test_hash_is_order_invariant_for_json_mappings(self):
        self.assertEqual(sha256_canonical({"b": 2, "a": 1}),
                         sha256_canonical({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
