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
        books, rep = BK.select_books(iter(texts), enc, eval_shas, eval_set, 5, 1000, prepare=BK.unwrap)
        self.assertEqual(rep["eval_book"], 1)
        self.assertEqual(rep["eval_overlap"], 1)
        self.assertEqual(len(books), 5)
        self.assertTrue(all(len(b["read"]) == 1000 and [len(t) for t in b["tail"]] == [257, 257] for b in books))
        with tempfile.TemporaryDirectory() as tmp:
            BK.write(Path(tmp), books[:3], rep, {"params": {}}, heldout=books[3:])
            tokens, rows = BK.load(tmp)
            self.assertEqual(len(tokens), 3000)
            self.assertTrue(np.array_equal(tokens[1000:2000], books[1]["read"]))
            held = BK.load_heldout(tmp)
            self.assertEqual(len(held), 2)
            self.assertEqual(held[0]["windows"][1], books[3]["read"][257:514].tolist())

    def test_unwrap(self):
        text = "Call me Ishmael. Some years\nago, never mind how\n  long precisely.\n\n\nHaving little\nmoney.\n"
        self.assertEqual(BK.unwrap(text), "Call me Ishmael. Some years ago, never mind how long precisely.\n\n"
                                          "Having little money.")


class RuleTests(unittest.TestCase):
    def test_cool_factor_and_retention(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("grow_mod", HERE / "grow.py")
        GR = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(GR)
        self.assertEqual(GR.cool_factor(5, 5, 4), 1.0)
        self.assertEqual(GR.cool_factor(7, 5, 4), 0.5)
        self.assertEqual(GR.cool_factor(9, 5, 4), 0.0)
        self.assertEqual(GR.cool_factor(30, 5, 4), 0.0)                 # frozen for good
        self.assertEqual(GR.cool_factor(30, 5, 0), 1.0)                 # never cools
        # stability guard: which rows diverged, and the penalty on a hidden state that grew
        flags, ref = GR.blown([100.0, 520.0], [100.0, 98.0, 102.0, 100.0, 520.0], 2.5)
        self.assertEqual((flags, ref), ([False, True], 100.0))
        self.assertEqual(GR.blown([5.0], [], 2.5)[0], [False])          # nothing to compare with yet
        nat = torch.full((2, 4), 10.0)
        keep = torch.tensor([1.0, 1.0])
        self.assertEqual(float(GR.norm_penalty(torch, nat.clone(), nat, 1.5, keep)), 0.0)
        self.assertEqual(float(GR.norm_penalty(torch, 1.4 * nat, nat, 1.5, keep)), 0.0)     # inside the limit
        grown = nat.clone()
        grown[1] = 30.0                                                  # row 1 is 3x native
        import math
        want = math.log(3 / 1.5) ** 2 / 2                                # mean over both rows
        self.assertAlmostEqual(float(GR.norm_penalty(torch, grown, nat, 1.5, keep)), want, places=6)
        self.assertEqual(float(GR.norm_penalty(torch, grown, nat, 1.5, torch.tensor([1.0, 0.0]))), 0.0)   # row left out
        self.assertEqual(float(GR.norm_penalty(torch, grown, nat, 1.5, torch.tensor([0.0, 0.0]))), 0.0)   # no row kept
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tails.jsonl"
            rows = [{"books_read": 1, "per_book": {"0": -0.10, "1": 0.0, "2": 0.0}},
                    {"books_read": 2, "per_book": {"0": -0.08, "1": -0.20, "2": 0.0}},
                    {"books_read": 3, "per_book": {"0": -0.05, "1": -0.10, "2": -0.30}}]
            p.write_text("".join(json.dumps(r) + "\n" for r in rows))
            r = GR.retention(p)
            self.assertAlmostEqual(r["book_gain_right_after"], 0.2)          # mean of 0.10, 0.20, 0.30
            self.assertAlmostEqual(r["book_gain_at_end"], 0.15)              # mean of 0.05, 0.10, 0.30
            self.assertAlmostEqual(r["book_gain_lost"], 0.05)
            self.assertAlmostEqual(r["book_gain_kept_fraction"], (0.5 + 0.5 + 1.0) / 3)
            self.assertEqual(GR.specific(p), {})                             # old logs without never-read books
            # what a book leaves beyond the general level (differences are model - native, so gain = -value)
            rows = [{"books_read": 0, "per_book": {"0": 0.0, "1": 0.0}, "heldout": 0.0},
                    {"books_read": 1, "per_book": {"0": -0.10, "1": -0.02}, "heldout": -0.02},
                    {"books_read": 2, "per_book": {"0": -0.12, "1": -0.11}, "heldout": -0.05}]
            p.write_text("".join(json.dumps(r) + "\n" for r in rows))
            sp = GR.specific(p)
            self.assertAlmostEqual(sp["specific_per_book"][0]["immediate"], 0.10 - 0.02)          # jump - tide
            self.assertAlmostEqual(sp["specific_per_book"][0]["retained"], 0.12 - 0.05)
            self.assertAlmostEqual(sp["specific_per_book"][1]["immediate"], (0.11 - 0.02) - (0.05 - 0.02))
            self.assertAlmostEqual(sp["specific_per_book"][1]["retained"], (0.11 - 0.02) - (0.05 - 0.02))
            self.assertAlmostEqual(sp["specific_gain_immediate"], (0.08 + 0.06) / 2)
            self.assertAlmostEqual(sp["specific_retention"], (0.07 + 0.06) / (0.08 + 0.06))
            self.assertAlmostEqual(sp["heldout_gain_end"], 0.05)


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
            BK.write(root / "books", books, {}, {"params": {}}, heldout=books[:1])
            common = ["--data", str(root / "books"), "--sets", str(root / "sets.jsonl"), "--upstream", UPSTREAM,
                      "--model-dir", str(fx / "model"), "--tokenizer", str(fx / "tokenizer.json"), "--threads", "1",
                      "--no-pin-check", "--precision", "fp32", "--seq-len", "64", "--micro-batch", "2", "--page", "2",
                      "--steps-pair", "1,1", "--eval-every", "1", "--per-domain", "1", "--lr", "1e-2",
                      "--t0", "0.0", "--t-min", "0.0"]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            runs = {}
            for mode, extra in (("auto", []), ("schedule", ["--k-target", "3"]), ("static", ["--k-target", "3"]),
                                ("unfrozen", ["--unfreeze", "--base-lr", "1e-3"]),
                                ("protected", ["--unfreeze", "--base-lr", "1e-3", "--anchor", "1.0", "--crystallize", "1",
                                               "--norm-limit", "1.5"]),
                                ("plain", ["--unfreeze", "--base-lr", "1e-3", "--anchor", "1.0", "--norm-limit", "1.5",
                                           "--eval-every", "2"])):
                outd = root / mode
                r = subprocess.run([sys.executable, "-B", str(HERE / "grow.py"), "--mode",
                                    {"unfrozen": "auto", "protected": "auto", "plain": "none"}.get(mode, mode),
                                    "--out", str(outd),
                                    *common, *extra], capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                runs[mode] = json.loads((outd / "summary.json").read_text())
                ev = read_jsonl(outd / "evals.jsonl")
                self.assertEqual(ev[0]["own_books_unread"], 0.0)            # start == native, exactly
                self.assertEqual(ev[0]["heldout_books"], 0.0)
                self.assertEqual([e["books_read"] for e in ev], [0, 2, 3] if mode == "plain" else [0, 1, 2, 3])
                log = read_jsonl(outd / "read_log.jsonl")
                self.assertEqual(len(log), 3 * 4)                         # 3 books x 4 micro-batches
                self.assertLess(runs[mode]["orthonormality_error"], 1e-6)
            self.assertGreaterEqual(runs["auto"]["k_final"], 1)           # T = 0: grows on any structure
            self.assertEqual(runs["schedule"]["k_final"], 3)
            self.assertEqual(runs["static"]["k_final"], 3)
            # unfrozen: the native baseline (frozen copy) is the same as in the frozen run; Parcae moved
            na = [r["native"] for r in read_jsonl(root / "auto" / "read_log.jsonl")]
            nu = [r["native"] for r in read_jsonl(root / "unfrozen" / "read_log.jsonl")]
            self.assertEqual(na, nu)
            self.assertTrue(runs["unfrozen"]["unfreeze"])
            self.assertGreater(max(runs["unfrozen"]["base_relative_change"].values()), 0.0)
            self.assertTrue((root / "unfrozen" / "final_base.pt").exists())
            # protected: the anchor is exactly 0 at the start (the model is the native one), every read book
            # is re-scored after each book, and the retention summary is there
            plog = read_jsonl(root / "protected" / "read_log.jsonl")
            self.assertLess(plog[0]["kl_to_native"], 1e-9)
            self.assertGreater(max(r["kl_to_native"] for r in plog), 0.0)
            tails = read_jsonl(root / "protected" / "tails.jsonl")
            self.assertEqual([t["books_read"] for t in tails], [0, 1, 2, 3])
            self.assertEqual(tails[0]["heldout"], 0.0)                     # the start is the native model
            self.assertIn("specific_gain_retained", runs["protected"])
            # plain control: no knowledge space at all, Parcae itself learns; between full checks only the
            # book just read, the next book and the never-read books are scored
            self.assertEqual(runs["plain"]["k_final"], 0)
            self.assertGreater(max(runs["plain"]["base_relative_change"].values()), 0.0)
            ptails = read_jsonl(root / "plain" / "tails.jsonl")
            self.assertEqual([t["books_read"] for t in ptails], [0, 1, 2, 3])
            self.assertEqual(sorted(ptails[1]["per_book"]), ["0", "1"])
            self.assertEqual(sorted(ptails[2]["per_book"]), ["0", "1", "2"])
            self.assertIsNotNone(ptails[1]["heldout"])
            self.assertEqual(runs["plain"]["specific_books"], 3)
            self.assertIn("book_gain_kept_fraction", runs["protected"])
            self.assertIn("forgetting_ppl_pct", runs["protected"])
            # stability: norms logged for every chunk in every run; the penalty only with the guard on
            self.assertTrue(all(r["native_norm"] > 0 and r["model_norm"] > 0 for r in plog))
            self.assertTrue(all(r["norm_penalty"] is not None for r in plog))
            self.assertTrue(all(r["norm_penalty"] is None for r in read_jsonl(root / "auto" / "read_log.jsonl")))
            self.assertEqual(plog[0]["norm_penalty"], 0.0)                 # the model starts as the native one
            pev = read_jsonl(root / "protected" / "evals.jsonl")
            self.assertEqual(pev[0]["diverged_windows"], pev[0]["native_diverged_windows"])
            self.assertAlmostEqual(pev[0]["max_hidden_norm_ratio"], 1.0, places=5)
            self.assertIn("read_chunks_model_only_diverged", runs["protected"])
            g = read_jsonl(root / "auto" / "growth.jsonl")
            grown = [e for e in g if e["grew"]]
            self.assertTrue(all("tokens_behind" in e for e in grown))


if __name__ == "__main__":
    unittest.main()
