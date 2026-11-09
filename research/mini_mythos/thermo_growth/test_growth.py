"""Tests for the growing knowledge space (CPU).

Pure tests use a toy network with Parcae's layout (attn.c_proj, mlp.proj in prelude/core_block/coda).
The model test runs grow.py end to end on the random tiny Parcae fixture (skipped without the pinned
upstream checkout).

  STAGE0_UPSTREAM=/path/to/parcae python -B -m unittest test_growth -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
for sub in ("stage0", "stage1", "stage2"):
    sys.path.insert(0, str(HERE.parent / sub))
sys.path.insert(0, str(HERE))
import books as BK  # noqa: E402
import knowledge_space as KS  # noqa: E402

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False

D = 16


class Attn(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.c_v = torch.nn.Linear(D, D, bias=False)
        self.c_proj = torch.nn.Linear(D, D, bias=False)

    def forward(self, x):
        return self.c_proj(torch.tanh(self.c_v(x)))


class MLP(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = torch.nn.Linear(D, 3 * D, bias=False)
        self.proj = torch.nn.Linear(3 * D, D, bias=False)

    def forward(self, x):
        return self.proj(torch.relu(self.fc(x)) ** 2)


class Block(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.attn, self.mlp = Attn(), MLP()

    def forward(self, x):
        x = x + 0.5 * self.attn(x)
        return x + 0.5 * self.mlp(x)


class Toy(torch.nn.Module):
    def __init__(self, seed=0):
        super().__init__()
        torch.manual_seed(seed)
        self.transformer = torch.nn.ModuleDict({p: torch.nn.ModuleList([Block()]) for p in KS.PARTS})
        for p in self.parameters():
            p.requires_grad_(False)

    def forward(self, x):
        for part in KS.PARTS:
            for b in self.transformer[part]:
                x = b(x)
        return x


def page_surprise(model, ks, target_fn, seed):
    """Two halves of a page with an MSE 'reality'; returns ks.surprise()."""
    gen = torch.Generator().manual_seed(seed)
    ks.reset_page()
    ks.collect = True
    for half in (0, 1, 0, 1):
        ks.half = half
        x = torch.randn(64, D, generator=gen)
        out = model(x)
        loss = (out - target_fn(x, out.detach(), gen)).pow(2).sum()
        loss.backward()
        for p in ks.parameters():
            p.grad = None
    ks.collect = False
    return ks.surprise()


class SpaceTests(unittest.TestCase):
    def setUp(self):
        self.x = torch.randn(5, D, generator=torch.Generator().manual_seed(1))

    def test_growth_preserves_output_and_space_is_orthonormal(self):
        m = Toy()
        base = m(self.x)
        ks = KS.KnowledgeSpace(m, k_max=8)
        self.assertTrue(torch.equal(m(self.x), base))                   # k = 0: the native model
        gen = torch.Generator().manual_seed(2)
        for _ in range(5):
            before = m(self.x)
            ks.grow(ks.random_direction(gen))
            # growing: output unchanged (the new reads are 0; only the summation order of the
            # matrix product can move the last bit)
            self.assertLess(float((m(self.x) - before).abs().max()), 1e-6)
            with torch.no_grad():
                for p in ks.parameters():
                    p[:, :ks.k] += 0.1 * torch.randn(p[:, :ks.k].shape, generator=gen)
        self.assertLess(KS.orthonormality_error(ks.directions()), 1e-6)          # stored in float32
        self.assertEqual(ks.count(), 5 * (D + 3 * (D + 3 * D)))         # k * (dim + reads of 3 blocks x (D + 3D))
        ks.k = 0
        self.assertTrue(torch.equal(m(self.x), base))                    # switching the space off: native

    def test_corrections_stay_in_the_space(self):
        m = Toy()
        ks = KS.KnowledgeSpace(m, k_max=8)
        gen = torch.Generator().manual_seed(3)
        for _ in range(3):
            ks.grow(ks.random_direction(gen))
        with torch.no_grad():
            for p in ks.parameters():
                p[:, :3] = torch.randn(p[:, :3].shape, generator=gen)
        U = ks.directions().double()
        P = torch.eye(D, dtype=torch.float64) - U @ U.t()
        for name, mod in KS.writers(m):
            x = torch.randn(7, mod.in_features, generator=gen)
            delta = mod(x) - torch.nn.functional.linear(x, mod.weight)
            self.assertLess(float((delta.double() @ P).abs().max()), 1e-5, name)   # only inside span(U)

    def test_surprise_finds_a_real_direction_and_not_noise(self):
        m = Toy()
        ks = KS.KnowledgeSpace(m, k_max=8)
        v = torch.zeros(D)
        v[3] = 1.0
        lam_c, lam_n, u = page_surprise(m, ks, lambda x, out, g: out + 2.0 * v, seed=0)        # reality: shift along v
        self.assertGreater(lam_c, 10 * lam_n)
        self.assertGreater(abs(float(u.float() @ v)), 0.9)
        lam_c, lam_n, _ = page_surprise(m, ks, lambda x, out, g: out + torch.randn(out.shape, generator=g), seed=0)
        self.assertLess(lam_c, lam_n)                                                          # pure noise: no growth
        grown = ks.grow(u)                                            # once grown, that pull is no longer "new"
        lam_c2, lam_n2, u2 = page_surprise(m, ks, lambda x, out, g: out + 2.0 * v, seed=0)
        self.assertLess(abs(float(u2 @ grown)), 1e-8)                 # the next direction is a new one
        # the strongest pull is gone from what counts as new (in a multi-layer network one reality shift
        # pulls different layers in different directions, so one direction does not absorb all of it)
        self.assertLess(lam_c2, 0.5 * lam_c)

    def test_state_roundtrip(self):
        m = Toy()
        ks = KS.KnowledgeSpace(m, k_max=8)
        gen = torch.Generator().manual_seed(4)
        for _ in range(2):
            ks.grow(ks.random_direction(gen))
        with torch.no_grad():
            for p in ks.parameters():
                p[:, :2] = torch.randn(p[:, :2].shape, generator=gen)
        out = m(self.x)
        st = ks.state()
        ks.remove()
        m2 = Toy()
        ks2 = KS.KnowledgeSpace(m2, k_max=8)
        ks2.load_state(st)
        self.assertTrue(torch.equal(m2(self.x), out))


class BookTests(unittest.TestCase):
    def test_select_skips_eval_books_and_overlaps(self):
        import ngrams
        rng = np.random.default_rng(0)
        texts, ids = [], {}
        for i in range(8):
            paras = [" ".join("w%d" % int(t) for t in rng.integers(0, 500, size=100)) for _ in range(30)]
            texts.append("\n\n".join(paras))
        enc = lambda t: [3 + int(w[1:]) for w in t.split()]      # noqa: E731
        bad = enc(texts[2])[1500:1540]                             # an eval window taken from book 2's body
        eval_set = np.unique(ngrams.hashes(np.asarray(bad, dtype=np.uint32)))
        eval_shas = {BK.B.sha256_bytes(texts[4].encode())}         # book 4 is an eval book
        books, rep = BK.select_books(iter(texts), enc, eval_shas, eval_set, 5, 1000)
        self.assertEqual(rep["eval_book"], 1)
        self.assertEqual(rep["eval_overlap"], 1)
        self.assertEqual(len(books), 5)
        self.assertTrue(all(len(b["read"]) == 1000 and [len(t) for t in b["tail"]] == [257, 257] for b in books))
        with tempfile.TemporaryDirectory() as tmp:
            BK.write(Path(tmp), books, rep, {"params": {}})
            tokens, rows = BK.load(tmp)
            self.assertEqual(len(tokens), 5000)
            self.assertTrue(np.array_equal(tokens[1000:2000], books[1]["read"]))


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


@unittest.skipUnless(HAVE_STACK, "tokenizers/upstream not available")
class ModelTests(unittest.TestCase):
    def test_grow_end_to_end_on_tiny_parcae(self):
        import test_stage0
        test_stage0.UPSTREAM = UPSTREAM
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fx = test_stage0.make_fixture(root / "fx")
            from tokenizers import Tokenizer
            tok = Tokenizer.from_file(str(fx / "tokenizer.json"))
            texts = [r["text"] for r in read_jsonl(fx / "texts.jsonl")]
            with open(root / "sets.jsonl", "w") as f:
                for i, text in enumerate(texts):
                    f.write(json.dumps({"domain": ["fineweb", "c4", "wikitext", "books"][i], "split": "dev",
                                        "doc_id": "dev-%d" % i, "text_sha256": "-",
                                        "tokens": tok.encode(text, add_special_tokens=False).ids[:257]}) + "\n")
            rng = np.random.default_rng(5)
            books = [{"sha256": str(i), "char_offset": 0, "read": rng.integers(3, 500, 8 * 65).astype(np.uint16),
                      "tail": [rng.integers(3, 500, 257).tolist() for _ in range(2)]} for i in range(3)]
            BK.write(root / "books", books, {}, {"params": {}})
            common = ["--data", str(root / "books"), "--sets", str(root / "sets.jsonl"), "--upstream", UPSTREAM,
                      "--model-dir", str(fx / "model"), "--tokenizer", str(fx / "tokenizer.json"), "--threads", "1",
                      "--no-pin-check", "--precision", "fp32", "--seq-len", "64", "--micro-batch", "2", "--page", "2",
                      "--steps-pair", "1,1", "--eval-every", "1", "--per-domain", "1", "--lr", "1e-2",
                      "--t0", "0.0", "--t-min", "0.0"]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            runs = {}
            for mode, extra in (("auto", []), ("schedule", ["--k-target", "3"]), ("static", ["--k-target", "3"])):
                outd = root / mode
                r = subprocess.run([sys.executable, "-B", str(HERE / "grow.py"), "--mode", mode, "--out", str(outd),
                                    *common, *extra], capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                runs[mode] = json.loads((outd / "summary.json").read_text())
                ev = read_jsonl(outd / "evals.jsonl")
                self.assertEqual(ev[0]["own_books_unread"], 0.0)            # start == native, exactly
                self.assertEqual([e["books_read"] for e in ev], [0, 1, 2, 3])
                log = read_jsonl(outd / "read_log.jsonl")
                self.assertEqual(len(log), 3 * 4)                         # 3 books x 4 micro-batches
                self.assertLess(runs[mode]["orthonormality_error"], 1e-6)
            self.assertGreaterEqual(runs["auto"]["k_final"], 1)           # T = 0: grows on any structure
            self.assertEqual(runs["schedule"]["k_final"], 3)
            self.assertEqual(runs["static"]["k_final"], 3)
            g = read_jsonl(root / "auto" / "growth.jsonl")
            grown = [e for e in g if e["grew"]]
            self.assertTrue(all("tokens_behind" in e for e in grown))


if __name__ == "__main__":
    unittest.main()
