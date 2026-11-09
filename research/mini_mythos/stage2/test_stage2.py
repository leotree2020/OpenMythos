"""Stage 2 tests on CPU with a random tiny Parcae model (NOT the real weights, NOT a GPU run).

  STAGE0_UPSTREAM=/path/to/parcae python -B -m unittest test_stage2 -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage0"))
import gpu_common as G  # noqa: E402

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import torch
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


class PackingTests(unittest.TestCase):
    def test_best_fit_rows(self):
        rng = np.random.default_rng(0)
        lengths = rng.integers(5, 90, size=200)
        tokens = rng.integers(3, 500, size=int(lengths.sum())).astype(np.uint16)
        a = G.pack_rows(tokens, lengths, 65, seed=1, buffer_size=20)
        b = G.pack_rows(tokens, lengths, 65, seed=1, buffer_size=20)
        c = G.pack_rows(tokens, lengths, 65, seed=2, buffer_size=20)
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, c))
        self.assertEqual(a.shape[1], 65)
        starts = set(np.concatenate([[0], np.cumsum(lengths)[:-1]]).tolist())
        doc_heads = {tuple(tokens[s:s + 3]) for s in starts}
        for row in a:                                   # every row starts at a document start
            self.assertIn(tuple(row[:3]), doc_heads)
        self.assertFalse((a == 0).any())                # no BOS / padding inserted
        self.assertGreater(a.size, 0.6 * tokens.size)   # most tokens used


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f]


@unittest.skipUnless(HAVE_STACK, "torch/tokenizers/upstream not available")
class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_stage0
        test_stage0.UPSTREAM = UPSTREAM
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.fx = test_stage0.make_fixture(root / "fx")
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(cls.fx / "tokenizer.json"))
        texts = [r["text"] for r in read_jsonl(cls.fx / "texts.jsonl")]
        cls.sets = root / "eval_sets.jsonl"
        with open(cls.sets, "w") as f:
            for i, text in enumerate(texts):
                for split in ("dev", "test"):
                    f.write(json.dumps({"domain": ["fineweb", "c4", "wikitext", "books"][i], "split": split,
                                        "doc_id": "%s-%d" % (split, i), "text_sha256": "-",
                                        "tokens": tok.encode(text, add_special_tokens=False).ids[:257]}) + "\n")
        rng = np.random.default_rng(3)
        lengths = rng.integers(20, 200, size=300).astype("<i4")
        (root / "data").mkdir()
        rng.integers(3, 512, size=int(lengths.sum())).astype("<u2").tofile(root / "data" / "train_tokens.u16")
        lengths.tofile(root / "data" / "train_doc_lengths.i32")
        cls.data = root / "data"
        cls.root = root
        cls.common = ["--upstream", UPSTREAM, "--model-dir", str(cls.fx / "model"),
                      "--tokenizer", str(cls.fx / "tokenizer.json"), "--device", "cpu", "--threads", "1",
                      "--no-pin-check"]
        torch.set_num_threads(1)
        cls.model, _ = G.load_model(torch, UPSTREAM, cls.fx / "model", cls.fx / "tokenizer.json", "cpu",
                                    pin_check=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_script(self, script, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", str(HERE / script), *args], capture_output=True, text=True, env=env)

    def test_lora_starts_identical_to_native(self):
        x = torch.randint(3, 500, (2, 32))
        steps = torch.tensor([2, 0])
        torch.manual_seed(1)
        base = self.model(x, return_logits=True, num_steps_pair=steps)["logits"]
        lora = G.LoRA(torch, self.model, rank=4, alpha=8, seed=0)
        try:
            torch.manual_seed(1)
            same = self.model(x, return_logits=True, num_steps_pair=steps)["logits"]
            self.assertTrue(torch.equal(base, same))
            with torch.no_grad():
                for name, p in lora.params.items():
                    if name.endswith(".B"):
                        p.add_(0.01)
            torch.manual_seed(1)
            moved = self.model(x, return_logits=True, num_steps_pair=steps)["logits"]
            self.assertFalse(torch.equal(base, moved))
            self.assertGreater(lora.count(), 0)
        finally:
            lora.remove()

    def test_batched_cpu_seeded_eval_matches_stage1_single_window_scoring(self):
        import common
        windows = G.load_windows(self.sets, "dev")
        per = G.evaluate(torch, self.model, windows, "cpu", depth=2, replicas=2, batch=3)
        for w in windows:
            ids, pos, tgt = common.build_window(w["tokens"], False)
            for rep in range(2):
                nll, _ = common.token_nll(torch, self.model, ids, pos, tgt, 2, G.SEED_BASE + 1000 * w["index"] + rep)
                self.assertAlmostEqual(per[w["doc_id"]][rep], float(np.mean(nll[64:255])), places=5)

    def train(self, out, mode, lr, *extra):
        return self.run_script("train.py", "--mode", mode, "--lr", str(lr), "--seed", "0", "--out", str(out),
                               "--data", str(self.data), "--sets", str(self.sets), "--precision", "fp32",
                               "--tokens", str(6 * 4 * 64), "--seq-len", "64", "--micro-batch", "2",
                               "--global-batch", "4", "--steps-pair", "1,1", "--rank", "4", "--ckpt-every", "2",
                               *self.common, *extra)

    def test_train_resume_evaluate_and_report(self):
        runs = self.root / "runs"
        full = self.train(runs / "lora_lr0.001_s0", "lora", 1e-3)
        self.assertEqual(full.returncode, 0, full.stdout + full.stderr)
        stop = self.train(runs / "lora_lr0.001_s0_resume", "lora", 1e-3, "--stop-after-step", "3")
        self.assertEqual(stop.returncode, 3, stop.stdout + stop.stderr)
        resumed = self.train(runs / "lora_lr0.001_s0_resume", "lora", 1e-3, "--resume")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        a = torch.load(runs / "lora_lr0.001_s0" / "final_params.pt", weights_only=True)
        b = torch.load(runs / "lora_lr0.001_s0_resume" / "final_params.pt", weights_only=True)
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))            # bitwise resume on CPU
        self.assertFalse(all(torch.equal(v, torch.zeros_like(v)) for k, v in a.items() if k.endswith(".B")))
        r = self.train(runs / "full_lr0.0001_s0", "full", 1e-4)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = read_jsonl(runs / "full_lr0.0001_s0" / "train_log.jsonl")
        self.assertEqual(len(log), 6)
        # native evaluation + agreement against a CPU reference written by the Stage 1 scoring path
        import common
        windows = G.load_windows(self.sets, "dev")
        ref = {}
        for w in windows:
            ids, pos, tgt = common.build_window(w["tokens"], False)
            ref[w["doc_id"]] = [float(np.mean(common.token_nll(torch, self.model, ids, pos, tgt, 8,
                                                                G.SEED_BASE + 1000 * w["index"] + rep)[0][64:255]))
                                for rep in range(2)]
        G.write_per_window(self.root / "cpu_ref.csv", ref, windows)
        ev = self.run_script("evaluate.py", "--sets", str(self.sets), "--cpu-reference", str(self.root / "cpu_ref.csv"),
                             "--out", str(self.root / "native"), *self.common)
        self.assertEqual(ev.returncode, 0, ev.stdout + ev.stderr)
        self.assertTrue(json.loads((self.root / "native" / "agreement.json").read_text())["pass"])
        # LR choice and summary
        ch = self.run_script("report.py", "choose", str(runs / "lora_lr0.001_s0"))
        self.assertEqual(ch.stdout.strip(), str(runs / "lora_lr0.001_s0"))
        sm = self.run_script("report.py", "summarize", "--native", str(self.root / "native"), "--runs", str(runs),
                             "--out", str(self.root / "summary.json"), "--price-per-hour", "0.7", "--hours", "1")
        self.assertEqual(sm.returncode, 0, sm.stdout + sm.stderr)
        s = json.loads((self.root / "summary.json").read_text())
        self.assertTrue(s["resume"]["lora_lr0.001_s0_resume"]["bitwise_equal"])
        self.assertIn("lora", s["chosen_lr"])
        self.assertIn("usd_per_10M_train_tokens_lora", s["cost"])


if __name__ == "__main__":
    unittest.main()
