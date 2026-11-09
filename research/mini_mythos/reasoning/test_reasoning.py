"""Reasoning probe tests (CPU; random tiny Parcae model and toy tokenizer, NOT the real weights).

  STAGE0_UPSTREAM=/path/to/parcae python -B -m unittest test_reasoning -v
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
sys.path.insert(0, str(HERE.parent / "stage0"))
sys.path.insert(0, str(HERE.parent / "stage2"))
sys.path.insert(0, str(HERE))
import tasks as T  # noqa: E402
import score as S  # noqa: E402
import gpu_common as G  # noqa: E402

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import torch
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


class TaskTests(unittest.TestCase):
    def test_deterministic_and_solved(self):
        a, b = T.build(7, 30), T.build(7, 30)
        self.assertEqual(a, b)
        self.assertNotEqual(a, T.build(8, 30))
        for it in a:
            self.assertEqual(T.solve(it), it["answer"], it["id"])
            self.assertEqual(it["prompt"].count("Q: "), T.SHOTS + 1)
            self.assertTrue(it["prompt"].endswith("\nA:"))
            self.assertTrue(all(c.startswith(" ") for c in it["candidates"]))
        self.assertEqual(len(a), 30 * sum(len(v) for v in T.LEVELS.values()))

    def test_solver_is_not_the_generator(self):
        it = T.build(3, 1)[0]
        wrong = dict(it, answer=(it["answer"] + 1) % len(it["candidates"]))
        self.assertNotEqual(T.solve(wrong), wrong["answer"])

    def test_build_sets_manifest_check(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sets.jsonl"
            r = subprocess.run([sys.executable, "-B", str(HERE / "build_sets.py"), "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            man = json.loads(Path(str(out) + ".manifest.json").read_text())
            self.assertEqual(man["counts"], {"dev": 3000, "test": 4500})
            bad = Path(d) / "bad.json"
            bad.write_text(json.dumps({"sha256": "0" * 64}))
            r = subprocess.run([sys.executable, "-B", str(HERE / "build_sets.py"), "--out", str(out), "--check",
                                str(bad)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)


@unittest.skipUnless(HAVE_STACK, "torch/tokenizers/upstream not available")
class ScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_stage0
        test_stage0.UPSTREAM = UPSTREAM
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.fx = test_stage0.make_fixture(cls.root / "fx")
        from tokenizers import Tokenizer
        cls.tok = Tokenizer.from_file(str(cls.fx / "tokenizer.json"))
        torch.set_num_threads(1)
        cls.model, _ = G.load_model(torch, UPSTREAM, cls.fx / "model", cls.fx / "tokenizer.json", "cpu",
                                    pin_check=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def naive(self, enc, depth, replicas):
        """One forward per (item, candidate) and replica, no batching, no fast path."""
        out = []
        for e in enc:
            row = []
            for c in e["cands"]:
                tot = 0.0
                for rep in range(replicas):
                    x = torch.tensor([e["prompt"] + c])
                    seed, L = S.SEED_BASE + 10 * e["k"] + rep, len(e["prompt"]) + max(map(len, e["cands"]))
                    orig = type(self.model).initialize_state

                    def init(embeds, seed=seed, L=L, n=x.shape[1]):   # written out independently of score.py
                        torch.manual_seed(seed)
                        return orig(self.model, torch.zeros((1, L, embeds.shape[2]), dtype=embeds.dtype))[:, :n]
                    self.model.initialize_state = init
                    try:
                        with torch.no_grad():
                            lg = self.model(x, return_logits=True, num_steps_pair=torch.tensor([depth, 0]))["logits"]
                    finally:
                        del self.model.initialize_state
                    lp = torch.log_softmax(lg.double(), -1)[0]
                    P = len(e["prompt"])
                    tot += float(sum(lp[P - 1 + t, c[t]] for t in range(len(c))))
                row.append(tot / replicas)
            out.append(row)
        return out

    def test_batched_scoring_matches_naive_and_fast_path(self):
        items = [it for it in T.build(5, 2) if it["family"] in ("chain", "order", "add")]
        enc = [e for e in S.encode_items(self.tok, items) if len(e["prompt"]) + max(map(len, e["cands"])) <= 250]
        self.assertGreater(len(enc), 6)
        self.assertTrue(any(e["single"] for e in enc) or any(not e["single"] for e in enc))
        got = S.score_items(torch, self.model, enc, "cpu", depth=2, replicas=2, batch_tokens=700)
        ref = self.naive(enc, 2, 2)
        for g, r in zip(got, ref):
            np.testing.assert_allclose(g[:len(r)], r, atol=1e-6)
        # force the slow path everywhere: same numbers
        slow = [dict(e, single=False) for e in enc]
        got2 = S.score_items(torch, self.model, slow, "cpu", depth=2, replicas=2, batch_tokens=100000)
        print("fast/slow path max |diff| %.2e" % np.nanmax(np.abs(got - got2)))
        np.testing.assert_allclose(np.nan_to_num(got), np.nan_to_num(got2), atol=1e-5)   # float32 batch-shape noise

    def test_end_to_end_score_and_report(self):
        sets = self.root / "sets.jsonl"
        r = subprocess.run([sys.executable, "-B", str(HERE / "build_sets.py"), "--out", str(sets)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        short = self.root / "short.jsonl"            # the tiny test model only takes 256 tokens
        with open(sets) as f, open(short, "w") as g:
            for line in f:
                it = json.loads(line)
                if len(self.tok.encode(it["prompt"]).ids) + 4 <= 250:
                    g.write(line)
        sets = short
        common = ["--upstream", UPSTREAM, "--model-dir", str(self.fx / "model"), "--tokenizer",
                  str(self.fx / "tokenizer.json"), "--device", "cpu", "--threads", "1", "--no-pin-check"]
        out = self.root / "scores"
        r = subprocess.run([sys.executable, "-B", str(HERE / "score.py"), "--sets", str(sets), "--split", "dev",
                            "--depths", "2,8", "--max-per-cell", "3", "--out", str(out), *common],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, "-B", str(HERE / "report.py"), "--scores", str(out), "--sets", str(sets),
                            "--split", "dev", "--max-per-cell", "3", "--out", str(self.root / "rep.json")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rep = json.loads((self.root / "rep.json").read_text())
        self.assertGreaterEqual(len(rep["cells"]), 3)
        self.assertIn("2", rep["cells"]["add-2"]["vs_depth8"])
        self.assertTrue(Path(self.root / "rep.md").exists())


if __name__ == "__main__":
    unittest.main()
