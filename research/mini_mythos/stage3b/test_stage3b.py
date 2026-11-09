"""Stage 3b tests on CPU: data extension, remainder-keeping packing, unfrozen training with two
learning rates (random tiny Parcae model; NOT the real weights, NOT a GPU run).

  STAGE0_UPSTREAM=/path/to/parcae python -B -m unittest test_stage3b -v
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
for sub in ("stage0", "stage1", "stage2", "stage3"):
    sys.path.insert(0, str(HERE.parent / sub))
sys.path.insert(0, str(HERE))
import build_data as B  # noqa: E402
import extend_data as X  # noqa: E402
import gpu_common as G  # noqa: E402
from packing import pack_rows_keep, packable_rows  # noqa: E402

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import torch
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


def toy_texts(n, seed=0):
    rng = np.random.default_rng(seed)
    words = ["w%d" % i for i in range(300)]
    out = []
    for i in range(n):
        k = int(rng.integers(0, 60))                         # some documents are empty-ish
        out.append(" ".join(words[j] for j in rng.integers(0, 300, size=k)))
    return out


def toy_encode(batch):
    return [[3 + int(w[1:]) for w in t.split()] for t in batch]


def sha(a, dtype):
    return hashlib.sha256(np.asarray(a).astype(dtype).tobytes()).hexdigest()


class ExtendTests(unittest.TestCase):
    def setUp(self):
        self.texts = toy_texts(3000)
        tok, lens = B.build_train(iter(self.texts), toy_encode, 5000)       # the "Stage 1" corpus
        self.s1 = {"train_tokens.u16": sha(tok, "<u2"), "train_doc_lengths.i32": sha(lens, "<i4")}
        self.s1_tok, self.s1_lens = tok, lens

    def test_reproduces_stage1_then_extends_and_drops_overlap(self):
        # plant: an evaluation window copied from a document that comes AFTER the Stage 1 part
        later = [t for t in self.texts[len(self.s1_lens) + 50:] if len(t.split()) >= 30][0]
        eval_rows = [{"tokens": toy_encode([later])[0][:20]}]
        tok, lens, rep = X.extend(iter(self.texts), toy_encode, 5000, self.s1, X.eval_ngram_set(eval_rows), 20000)
        n1 = rep["stage1_docs"]
        self.assertEqual(n1, len(self.s1_lens))
        self.assertTrue(np.array_equal(tok[:int(self.s1_lens.sum())], self.s1_tok))      # Stage 1 part first
        self.assertTrue(np.array_equal(lens[:n1], self.s1_lens))
        self.assertGreaterEqual(rep["new_docs_dropped_eval_overlap"], 1)
        planted = np.asarray(toy_encode([later])[0], dtype=np.uint16)
        starts = np.concatenate([[0], np.cumsum(lens)[:-1]])
        self.assertFalse(any(lens[i] == len(planted) and np.array_equal(tok[starts[i]:starts[i] + lens[i]], planted)
                             for i in range(n1, len(lens))))
        self.assertGreaterEqual(int(lens.sum()), 20000)
        self.assertEqual(int(lens.sum()), len(tok))
        tok2, lens2, _ = X.extend(iter(self.texts), toy_encode, 5000, self.s1, X.eval_ngram_set(eval_rows), 20000)
        self.assertTrue(np.array_equal(tok, tok2) and np.array_equal(lens, lens2))         # deterministic

    def test_refuses_a_stream_that_does_not_reproduce_stage1(self):
        bad = dict(self.s1, **{"train_tokens.u16": "0" * 64})
        with self.assertRaises(SystemExit):
            X.extend(iter(self.texts), toy_encode, 5000, bad, np.zeros(0, np.uint64), 20000)
        with self.assertRaises(SystemExit):                                                # source too small
            X.extend(iter(self.texts), toy_encode, 5000, self.s1, np.zeros(0, np.uint64), 10 ** 9)


class PackingTests(unittest.TestCase):
    def test_keeps_remainders(self):
        rng = np.random.default_rng(0)
        lengths = rng.integers(5, 300, size=400)          # many documents longer than a row
        tokens = rng.integers(3, 500, size=int(lengths.sum())).astype(np.uint16)
        rows = pack_rows_keep(tokens, lengths, 65, seed=1, buffer_size=20)
        self.assertEqual(len(rows), packable_rows(lengths, 65))
        self.assertEqual(len(rows), tokens.size // 65)    # only the final partial row is lost
        used = np.bincount(rows.ravel(), minlength=512)
        have = np.bincount(tokens, minlength=512)
        self.assertTrue((used <= have).all())
        self.assertLess(int((have - used).sum()), 65)
        self.assertTrue(np.array_equal(rows, pack_rows_keep(tokens, lengths, 65, seed=1, buffer_size=20)))
        self.assertFalse(np.array_equal(rows, pack_rows_keep(tokens, lengths, 65, seed=2, buffer_size=20)))
        self.assertEqual(len(pack_rows_keep(tokens, lengths, 65, seed=1, buffer_size=20, max_rows=7)), 7)


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f]


@unittest.skipUnless(HAVE_STACK, "torch/tokenizers/upstream not available")
class UnfrozenTests(unittest.TestCase):
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
        cls.data, cls.root = root / "data", root
        cls.common = ["--upstream", UPSTREAM, "--model-dir", str(cls.fx / "model"),
                      "--tokenizer", str(cls.fx / "tokenizer.json"), "--device", "cpu", "--threads", "1",
                      "--no-pin-check"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_script(self, where, script, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", str(where / script), *args], capture_output=True, text=True,
                              env=env)

    def train(self, out, mode, *extra):
        return self.run_script(HERE, "train.py", "--mode", mode, "--lr", "1e-3", "--extra-lr", "1e-2", "--seed", "0",
                               "--out", str(out), "--data", str(self.data), "--sets", str(self.sets),
                               "--precision", "fp32", "--tokens", str(6 * 4 * 64), "--seq-len", "64",
                               "--micro-batch", "2", "--global-batch", "4", "--steps-pair", "1,1", "--rank", "4",
                               "--ckpt-every", "2", *self.common, *extra)

    def test_unfrozen_train_resume_reload(self):
        torch.set_num_threads(1)
        native, _ = G.load_model(torch, UPSTREAM, self.fx / "model", self.fx / "tokenizer.json", "cpu", pin_check=False)
        ref = {k: v.clone() for k, v in native.state_dict().items()}
        runs = self.root / "runs"
        for mode in ("moda", "lora"):
            r = self.train(runs / ("%s_lr0.001_s0" % mode), mode)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            run = runs / ("%s_lr0.001_s0" % mode)
            self.assertFalse((run / "ckpt.pt").exists())                       # deleted at the end
            base = torch.load(run / "final_base.pt", weights_only=True)
            changed = [k for k in ref if not torch.equal(ref[k], base[k])]
            self.assertTrue(any("core_block" in k for k in changed))         # Parcae weights trained
            extra = torch.load(run / "final_params.pt", weights_only=True)
            self.assertTrue(any(float(v.abs().max()) > 0 for k, v in extra.items()
                                if k.startswith("gate") or k.endswith(".B")))    # extra component trained
            cfg = json.loads((run / "config.json").read_text())
            self.assertTrue(cfg["config"]["unfreeze"])
            self.assertGreater(cfg["trainable_params"], sum(v.numel() for v in native.parameters()))
            log = read_jsonl(run / "train_log.jsonl")
            self.assertEqual(len(log), 6)
            for row in log:                                                     # two learning rates, same shape
                self.assertAlmostEqual(row["extra_lr"] / row["lr"], 10.0, places=6)
            # reload (base + extra) reproduces the run's own dev scores
            ev = self.run_script(HERE.parent / "stage3", "eval_run.py", "--run", str(run), "--split", "dev",
                                 "--sets", str(self.sets), "--compare", str(run / "eval_dev.csv"),
                                 "--out", str(self.root / ("reload_%s.csv" % mode)), *self.common)
            self.assertEqual(ev.returncode, 0, ev.stdout + ev.stderr)
        # resume is bitwise on CPU, base weights included
        res = self.root / "res" / "moda_lr0.001_s0"
        stop = self.train(res, "moda", "--stop-after-step", "3")
        self.assertEqual(stop.returncode, 3, stop.stdout + stop.stderr)
        again = self.train(res, "moda", "--resume")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        a = torch.load(runs / "moda_lr0.001_s0" / "final_base.pt", weights_only=True)
        b = torch.load(res / "final_base.pt", weights_only=True)
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))
        a = torch.load(runs / "moda_lr0.001_s0" / "final_params.pt", weights_only=True)
        b = torch.load(res / "final_params.pt", weights_only=True)
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))

    def test_two_learning_rates_and_identity_at_start(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("s3b_train", HERE / "train.py")
        T = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(T)
        self.assertAlmostEqual(T.lr_at(0, 100, 1e-5, 0.05, 0.1) / T.lr_at(0, 100, 3e-4, 0.05, 0.1), 1e-5 / 3e-4)
        import mechanisms as M
        torch.set_num_threads(1)
        model, _ = G.load_model(torch, UPSTREAM, self.fx / "model", self.fx / "tokenizer.json", "cpu", pin_check=False)
        x = torch.randint(3, 500, (2, 40))
        torch.manual_seed(1)
        base = model(x, return_logits=True, num_steps_pair=torch.tensor([3, 0]))["logits"]
        for p in model.parameters():
            p.requires_grad_(True)                  # unfrozen
        for mode in ("moda", "lora"):
            mech = M.attach(torch, model, mode, rank=4, seed=0)
            try:
                torch.manual_seed(1)
                with torch.no_grad():
                    same = model(x, return_logits=True, num_steps_pair=torch.tensor([3, 0]))["logits"]
                self.assertTrue(torch.equal(base, same), mode)
            finally:
                mech.remove()


if __name__ == "__main__":
    unittest.main()
