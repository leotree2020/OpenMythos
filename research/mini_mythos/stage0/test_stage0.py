"""Stage 0 tests. Pure-logic tests always run; the integration tests build a random tiny Parcae
model (NOT the real weights) and run the real scripts end to end as subprocesses.

  STAGE0_UPSTREAM=/workspaces/mythos-parcae-pinned python -B -m unittest test_stage0 -v
"""
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common          # noqa: E402
import prepare_data    # noqa: E402

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", common.DEFAULTS["upstream"])
try:
    import torch  # noqa: F401
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


class WindowTests(unittest.TestCase):
    def test_both_conditions_score_same_tokens_from_same_previous_token(self):
        t = list(range(100, 100 + 300))
        for bos in (False, True):
            ids, pos, tgt = common.build_window(t, bos)
            self.assertEqual(len(ids), common.WINDOW)
            self.assertEqual(len(pos), len(tgt), common.WINDOW - 1)
            self.assertEqual(tgt, t[1:common.WINDOW])
            for k in range(1, common.WINDOW):          # text token t[k] ...
                p = pos[k - 1]
                self.assertEqual(tgt[k - 1], t[k])
                self.assertEqual(ids[p], t[k - 1])      # ... is predicted right after t[k-1]
        ids, _, _ = common.build_window(t, True)
        self.assertEqual(ids[0], common.BOS_ID)

    def test_short_text_rejected(self):
        with self.assertRaises(ValueError):
            common.build_window(list(range(common.WINDOW)), True)


class DataTests(unittest.TestCase):
    def test_wikitext_articles(self):
        lines = ["", " = Alpha = \n", "\n", " Alpha body one .\n", " = = Section = = \n", " more alpha\n",
                 " = Beta = \n", " beta body\n"]
        arts = prepare_data.wikitext_articles(lines)
        self.assertEqual([a[0] for a in arts], ["Alpha", "Beta"])
        self.assertIn("= = Section = =", arts[0][1])
        self.assertTrue(arts[0][1].startswith("Alpha body one"))

    def test_select_filters_and_dedupes_in_order(self):
        texts = ["short", "a" * 30, "b" * 30, "a" * 30, "c" * 30]
        chosen = prepare_data.select(texts, 2, min_chars=10)
        self.assertEqual([t for _, t in chosen], ["a" * 30, "b" * 30])


class SamplingTests(unittest.TestCase):
    def setUp(self):
        if not HAVE_STACK:
            self.skipTest("torch not available")
        import generate
        self.g = generate
        self.torch = torch

    def test_greedy_and_repetition_penalty(self):
        logits = self.torch.tensor([0.0, 3.0, 2.9, -1.0])
        greedy = {"sample": False, "temperature": 1.0, "top_p": None, "rep_penalty": 1.0}
        self.assertEqual(self.g.next_token(self.torch, logits, [], greedy, None), 1)
        penal = dict(greedy, rep_penalty=1.1)
        self.assertEqual(self.g.next_token(self.torch, logits, [1], penal, None), 2)

    def test_top_p_keeps_only_nucleus(self):
        logits = self.torch.log(self.torch.tensor([0.6, 0.3, 0.05, 0.05]))
        s = {"sample": True, "temperature": 1.0, "top_p": 0.8, "rep_penalty": 1.0}
        gen = self.torch.Generator().manual_seed(0)
        picks = {self.g.next_token(self.torch, logits, [], s, gen) for _ in range(300)}
        self.assertEqual(picks, {0, 1})

    def test_float32_mass_error_does_not_matter(self):
        logits = self.torch.randn(32768, generator=self.torch.Generator().manual_seed(3)) * 5
        s = {"sample": True, "temperature": 1.0, "top_p": None, "rep_penalty": 1.0}
        gen = self.torch.Generator().manual_seed(1)
        tok = self.g.next_token(self.torch, logits.float(), [], s, gen)
        self.assertTrue(0 <= tok < 32768)


def make_fixture(root):
    """Random tiny Parcae model + toy tokenizer whose special ids match BOS=0/EOS=1."""
    sys.path.insert(0, UPSTREAM)
    import parcae_lm
    from receval.models.parcae import ModelingParcae
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    root = Path(root)
    root.mkdir(parents=True)
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    corpus = ["the quick brown fox jumps over the lazy dog and the cat sat on the mat "] * 50
    trainer = trainers.BpeTrainer(vocab_size=512, special_tokens=["<|bos|>", "<|eos|>", "<|pad|>"],
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False)
    tok.train_from_iterator(corpus, trainer)
    tok.save(str(root / "tokenizer.json"))
    cfg = parcae_lm.create_config("parcae-small-140m", block_size=256, vocab_size=512, n_embd=64,
                                  intermediate_size=256, num_attention_heads=4, num_key_value_heads=4,
                                  recurrent_embedding_dimension=64, recurrent_intermediation_embedding_dimension=256)
    doc = dataclasses.asdict(cfg)
    doc["_class_name"] = "ParcaeConfig"
    (root / "model").mkdir()
    (root / "model" / "config.json").write_text(json.dumps(doc, indent=1, default=str))
    torch.manual_seed(5)
    model = ModelingParcae(cfg)
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.05 * torch.randn_like(p))
    torch.save(model.state_dict(), root / "model" / "pytorch_model.bin")
    words = "alpha beta gamma delta river mountain number seven blue green quick brown fox dog cat".split()
    rows = []
    for domain in ("fineweb", "wikitext"):
        for i in range(2):
            text = " ".join(words[(j * (i + 3) + len(domain)) % len(words)] for j in range(400))
            rows.append({"domain": domain, "doc_id": "%s-%03d" % (domain, i),
                         "text_sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text})
    with open(root / "texts.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    prompts = {"prompts": [{"id": 1, "text": "the quick brown"}, {"id": 2, "text": "a cat sat"}]}
    (root / "prompts.json").write_text(json.dumps(prompts))
    return root


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def run(script, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-B", str(HERE / script), *args], capture_output=True, text=True, env=env)
    return r


@unittest.skipUnless(HAVE_STACK, "torch/tokenizers/upstream not available")
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fx = make_fixture(Path(cls.tmp.name) / "fx")
        cls.common_args = ["--upstream", UPSTREAM, "--model-dir", str(cls.fx / "model"),
                           "--tokenizer", str(cls.fx / "tokenizer.json"), "--threads", "1", "--no-pin-check"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_eval_report_and_resume(self):
        out = Path(self.tmp.name) / "run"
        args = ["--texts", str(self.fx / "texts.jsonl"), "--out", str(out), "--depths", "2,4", *self.common_args]
        r = run("eval_depth.py", *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = read_jsonl(out / "rows.jsonl")
        self.assertEqual(len(rows), 4 * 2 * 2 * 2)   # windows x replicas x BOS x depths
        self.assertTrue(all(len(x["nll"]) == common.WINDOW - 1 for x in rows))
        cfg = json.loads((out / "config.json").read_text())
        self.assertTrue(cfg["state_check"]["all_equal"])
        by = {(x["doc_id"], x["rep"], x["bos"], x["depth"]): x for x in rows}
        a, b = by[("fineweb-000", 0, 1, 2)], by[("fineweb-000", 0, 0, 2)]
        self.assertEqual(a["seed"], b["seed"])
        self.assertNotEqual(a["nll"], b["nll"])         # BOS changes the prediction
        r2 = run("eval_depth.py", *args)                 # resume: nothing left to do
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertEqual(len(read_jsonl(out / "rows.jsonl")), len(rows))
        r3 = run("eval_depth.py", *[x if x != "2,4" else "2,3" for x in args])
        self.assertNotEqual(r3.returncode, 0)            # different config refused in same dir
        r4 = run("report.py", "--run", str(out))
        self.assertEqual(r4.returncode, 0, r4.stdout + r4.stderr)
        s = json.loads((out / "summary.json").read_text())
        self.assertEqual(sorted(s["domains"]), ["fineweb", "wikitext"])
        c = s["domains"]["fineweb"]["depth_contrasts"]["bos1_d4_minus_d2"]
        self.assertEqual(c["n"], 2)
        self.assertIn("d2_early_bos_minus_nobos", s["domains"]["wikitext"]["bos_contrasts"])

    def test_generate(self):
        out = Path(self.tmp.name) / "gen"
        r = run("generate.py", "--out", str(out), "--prompts", str(self.fx / "prompts.json"), "--max-new", "6",
                "--depth", "2", *self.common_args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = read_jsonl(out / "generations.jsonl")
        self.assertEqual(len(rows), 2 * 3)
        self.assertTrue(all(len(x["tokens"]) <= 6 for x in rows))
        self.assertTrue((out / "generations.md").exists())


if __name__ == "__main__":
    unittest.main()
