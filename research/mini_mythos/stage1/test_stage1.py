"""Stage 1 tests: n-gram hashing, data selection/decontamination on synthetic sources, and the
baseline runner end to end on a random tiny Parcae model (NOT the real weights).

  STAGE0_UPSTREAM=/workspaces/mythos-parcae-pinned python -B -m unittest test_stage1 -v
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage0"))
import build_data  # noqa: E402
import ngrams      # noqa: E402


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def word_ids(text):
    """Deterministic toy tokenizer: one id per whitespace word."""
    return [int(hashlib.md5(w.encode()).hexdigest(), 16) % 30000 + 3 for w in text.split()]


def doc(rng, n=420):
    words = ["w%d" % rng.randrange(5000) for _ in range(n)]
    return " ".join(words)


class NgramTests(unittest.TestCase):
    def test_hash_equality_matches_naive(self):
        rng = np.random.default_rng(0)
        t = rng.integers(0, 50, size=400)
        h = ngrams.hashes(t, 5)
        grams = [tuple(t[i:i + 5]) for i in range(len(t) - 4)]
        for i in range(0, len(grams), 7):
            for j in range(0, len(grams), 11):
                self.assertEqual(h[i] == h[j], grams[i] == grams[j])

    def test_corpus_set_excludes_cross_document_ngrams(self):
        a, b = list(range(100, 120)), list(range(200, 220))
        s = ngrams.corpus_set(np.array(a + b), [20, 20])
        cross = ngrams.hashes(a[-6:] + b[:7])          # spans the boundary
        inside = ngrams.hashes(a[:13])
        self.assertFalse(ngrams.member(cross, s).any())
        self.assertTrue(ngrams.member(inside, s).all())
        self.assertEqual(len(s), 2 * (20 - 12))

    def test_overlap_coverage(self):
        s = ngrams.corpus_set(np.arange(1000, 1013), [13])
        window = [1] * 10 + list(range(1000, 1013)) + [2] * 10
        hits, total, cov = ngrams.overlap(window, s)
        self.assertEqual((hits, total), (1, len(window) - 12))
        self.assertAlmostEqual(cov, 13 / len(window))


class WikitextTests(unittest.TestCase):
    def test_streaming_bodies(self):
        lines = ["", " = A = \n", " a one\n", " = = Sub = = \n", " a two\n", " = B = \n", " b\n"]
        self.assertEqual(list(build_data.wikitext_bodies(iter(lines))), ["a one\n = = Sub = = \n a two", "b"])


class BuildTests(unittest.TestCase):
    def make_sources(self, plant=True, scarce=False):
        rng = random.Random(1)
        train = [doc(rng) for _ in range(40)]
        pools = {name: [doc(rng) for _ in range(12)] for name in
                 ("fineweb", "c4", "wikitext_dev", "wikitext_test", "books_dev", "books_test")}
        if plant:
            # c4 candidate 0 copies 20 words of a training doc -> must be rejected for train overlap
            pools["c4"][0] = " ".join(train[5].split()[100:120] + pools["c4"][0].split()[20:])
            # books test candidate 0 repeats 15 words of books dev candidate 0 -> rejected for dev overlap
            pools["books_test"][0] = " ".join(pools["books_dev"][0].split()[:15] + pools["books_test"][0].split()[15:])
        if scarce:
            pools["wikitext_test"] = pools["wikitext_test"][:2]
        sources = {"train": train, **pools}
        return lambda name: iter(list(sources[name]))

    def build(self, out, **kw):
        return build_data.build(out, self.make_sources(**kw), word_ids, lambda ts: [word_ids(t) for t in ts],
                                train_tokens=8000, n_dev=3, n_test=4, lock_info={"test": True})

    def test_selection_decontamination_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            rep1, man1 = self.build(Path(d) / "a")
            rep2, man2 = self.build(Path(d) / "b")
            self.assertEqual(man1, man2)                         # deterministic
            self.assertEqual(rep1["shortfall"], {})
            rows = read_jsonl(Path(d) / "a" / "eval_sets.jsonl")
            self.assertEqual(len(rows), 4 * (3 + 4))
            self.assertTrue(all(len(r["tokens"]) == build_data.WINDOW_TOKENS for r in rows))
            self.assertEqual(len({r["text_sha256"] for r in rows}), len(rows))
            self.assertEqual(rep1["domains"]["c4"]["with_train_overlap"], 1)
            self.assertEqual(rep1["domains"]["books"]["rejected_for_dev_overlap"], 1)
            tokens = np.frombuffer((Path(d) / "a" / "train_tokens.u16").read_bytes(), dtype="<u2")
            lengths = np.frombuffer((Path(d) / "a" / "train_doc_lengths.i32").read_bytes(), dtype="<i4")
            self.assertEqual(int(lengths.sum()), len(tokens))
            self.assertGreaterEqual(len(tokens), 8000)
            train_set = ngrams.corpus_set(tokens, lengths)
            dev_set = np.unique(np.concatenate([ngrams.hashes(r["tokens"]) for r in rows if r["split"] == "dev"]))
            for r in rows:                                       # no accepted window overlaps train
                self.assertEqual(ngrams.overlap(r["tokens"], train_set)[0], 0)
                if r["split"] == "test":                         # and no test window overlaps any dev window
                    self.assertEqual(ngrams.overlap(r["tokens"], dev_set)[0], 0)

    def test_shortfall_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            rep, _ = self.build(Path(d), scarce=True)
            self.assertEqual(rep["shortfall"], {"wikitext/test": 2})


UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import torch  # noqa: F401
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


@unittest.skipUnless(HAVE_STACK, "torch/tokenizers/upstream not available")
class BaselineTests(unittest.TestCase):
    def test_run_resume_lock_and_report(self):
        import test_stage0
        test_stage0.UPSTREAM = UPSTREAM
        with tempfile.TemporaryDirectory() as d:
            fx = test_stage0.make_fixture(Path(d) / "fx")
            from tokenizers import Tokenizer
            tok = Tokenizer.from_file(str(fx / "tokenizer.json"))
            texts = [r["text"] for r in read_jsonl(fx / "texts.jsonl")]
            with open(Path(d) / "sets.jsonl", "w") as f:
                for i, text in enumerate(texts):
                    for split in ("dev", "test"):
                        f.write(json.dumps({"domain": "c4" if i % 2 else "fineweb", "split": split,
                                            "doc_id": "x-%s-%d" % (split, i), "text_sha256": "-",
                                            "tokens": tok.encode(text, add_special_tokens=False).ids[:257]}) + "\n")
            out = Path(d) / "run"
            common = ["--sets", str(Path(d) / "sets.jsonl"), "--out", str(out), "--upstream", UPSTREAM,
                      "--model-dir", str(fx / "model"), "--tokenizer", str(fx / "tokenizer.json"),
                      "--threads", "1", "--depth", "2", "--no-pin-check"]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            run = lambda *a: subprocess.run([sys.executable, "-B", str(HERE / "baseline.py"), *a],
                                            capture_output=True, text=True, env=env)
            r0 = run("run", *common, "--max-hours", "0")
            self.assertEqual(r0.returncode, 3, r0.stdout + r0.stderr)
            r1 = run("run", *common)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            with open(out / "rows.jsonl") as f:
                self.assertEqual(sum(1 for _ in f), 8 * 2)
            import fcntl
            with open(out / "run.lock", "w") as held:
                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                r2 = run("run", *common)
            self.assertNotEqual(r2.returncode, 0)
            r3 = run("report", "--out", str(out))
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)
            b = json.loads((out / "baseline.json").read_text())
            self.assertEqual(sorted(b["groups"]), ["c4/dev", "c4/test", "fineweb/dev", "fineweb/test"])
            g = b["groups"]["c4/test"]
            self.assertEqual(g["windows"], 2)
            self.assertGreater(g["replica_noise_sd"], 0)      # different h0 seeds give different NLL


if __name__ == "__main__":
    unittest.main()
