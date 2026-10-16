"""R1 real-text pipeline tests; all offline (no HF download or 3B training)."""
import sys
import tempfile
import unittest
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common import load_upstream, get_repo
from r1_prepare_wikitext import select_documents, write_text
from r1_text_pilot import (
    VOCAB_SIZE, TOKENIZER_ID, checkpoint_bundle, draw_batch,
    ensure_different_splits, evaluate, greedy_sample, make_config,
    resume_checkpoint, text_tokens, validation_offsets, atomic_checkpoint
)


class R1PilotTests(unittest.TestCase):
    def test_prepare_separate_text_documents_offline(self):
        rows = [{"text": ""}, {"text": "tiny"},
                {"text": "This is a complete sentence."},
                {"text": "Another sufficiently long sentence."}]
        self.assertEqual(len(select_documents(rows, 2)), 2)
        with self.assertRaisesRegex(ValueError, "No eligible"):
            select_documents([{"text": ""}], 1)
        with self.assertRaises(ValueError):
            select_documents(rows, 0)
        with tempfile.TemporaryDirectory() as d:
            info = write_text(Path(d) / "train.txt",
                              ["Sentence one is long.", "Sentence two is long."])
            self.assertEqual(info["documents"], 2)
            self.assertGreater(info["bytes"], 30)

    def test_byte_encoding_eos_and_split_guard(self):
        with tempfile.TemporaryDirectory() as d:
            left, right = Path(d) / "train.txt", Path(d) / "val.txt"
            left.write_bytes(b"one complete phrase\n\ntwo complete phrases")
            right.write_bytes(b"different validation words for the model")
            tokens, meta = text_tokens(left, 1000, seq_len=8)
            self.assertIn(256, tokens.tolist())
            self.assertEqual(meta["document_pieces"], 2)
            _, validation_meta = text_tokens(right, 1000, seq_len=8)
            ensure_different_splits(meta, validation_meta)
            with self.assertRaises(ValueError):
                ensure_different_splits(meta, meta)

    def test_validation_windows_do_not_overlap(self):
        starts = validation_offsets(token_count=1025, seq_len=64, n_windows=8)
        self.assertEqual(len(starts), 8)
        self.assertTrue(all(b - a >= 64 for a, b in zip(starts, starts[1:])))
        with self.assertRaises(ValueError):
            validation_offsets(40, 64, 4)

    def test_batches_are_deterministic_and_shifted(self):
        tokens = torch.arange(300) % VOCAB_SIZE
        a = torch.Generator().manual_seed(42)
        b = torch.Generator().manual_seed(42)
        x1, y1 = draw_batch(tokens, seq_len=16, batch_size=3, generator=a, device="cpu")
        x2, y2 = draw_batch(tokens, seq_len=16, batch_size=3, generator=b, device="cpu")
        self.assertTrue(torch.equal(x1, x2))
        self.assertTrue(torch.equal(y1, y2))
        self.assertTrue(torch.equal(x1[:, 1:], y1[:, :-1]))

    def test_actual_upstream_gqa_heldout_and_generation(self):
        module = load_upstream(get_repo("."))
        torch.manual_seed(1234)
        cfg = make_config(module, attention="gqa", seq_len=16)
        model = module.OpenMythos(cfg)
        heldout = torch.randint(0, 256, (96,), generator=torch.Generator().manual_seed(50))
        stats = evaluate(model, heldout, seq_len=16, n_loops=2,
                         n_windows=2, device="cpu")
        self.assertGreater(stats["perplexity"], 0)
        self.assertEqual(stats["tokens"], 32)
        example = greedy_sample(model, "The ", n_loops=2,
                                max_new_tokens=2, max_seq_len=16, device="cpu")
        self.assertIn("continuation", example)
        self.assertLessEqual(example["token_count"], 2)

    def test_safe_checkpoint_resume_rejects_mismatched_corpus(self):
        module = load_upstream(get_repo("."))
        torch.manual_seed(11)
        cfg = make_config(module, attention="gqa", seq_len=16)
        model = module.OpenMythos(cfg)
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
        gen = torch.Generator().manual_seed(22)
        hyper = {"seed": 11}
        provenance = {"tokenizer": TOKENIZER_ID, "train": {"sha256": "abc"}}
        x = torch.randint(0, 256, (1, 16))
        y = torch.randint(0, 256, (1, 16))
        optimizer.zero_grad()
        loss = F.cross_entropy(model(x, n_loops=2).reshape(-1, VOCAB_SIZE), y.reshape(-1))
        loss.backward()
        optimizer.step()
        before = model(x, n_loops=2).detach().clone()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "checkpoint.pt"
            atomic_checkpoint(path, checkpoint_bundle(
                model, optimizer, gen, cfg=cfg, hyperparameters=hyper,
                provenance=provenance, step=1
            ))
            other = module.OpenMythos(cfg)
            other_opt = torch.optim.AdamW(other.parameters(), lr=.001)
            other_gen = torch.Generator().manual_seed(44)
            restored_step = resume_checkpoint(
                path, other, other_opt, other_gen,
                cfg=cfg, hyperparameters=hyper, provenance=provenance
            )
            self.assertEqual(restored_step, 1)
            self.assertTrue(torch.allclose(before, other(x, n_loops=2).detach(), atol=1e-6))
            self.assertTrue(torch.equal(gen.get_state(), other_gen.get_state()))
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                resume_checkpoint(
                    path, other, other_opt, other_gen, cfg=cfg,
                    hyperparameters=hyper, provenance={"train": {"sha256": "wrong"}}
                )


if __name__ == "__main__":
    unittest.main()
