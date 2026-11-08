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


class ResumeTests(unittest.TestCase):
    def test_incomplete_last_row_is_removed_and_middle_damage_refused(self):
        import eval_depth
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "rows.jsonl"
            good = json.dumps({"doc_id": "a", "rep": 0, "bos": 1, "depth": 8, "seconds": 1.0}) + "\n"
            path.write_text(good + good.replace('"a"', '"b"') + '{"doc_id": "c", "rep"')
            rows = eval_depth.read_rows_repairing_tail(path)
            self.assertEqual([r["doc_id"] for r in rows], ["a", "b"])
            self.assertEqual(path.read_text(), good + good.replace('"a"', '"b"'))
            with open(path, "a") as f:                       # appending after repair stays valid
                f.write(good.replace('"a"', '"d"'))
            self.assertEqual(len(eval_depth.read_rows_repairing_tail(path)), 3)
            path.write_text(good + "{broken\n" + good)
            with self.assertRaises(SystemExit):
                eval_depth.read_rows_repairing_tail(path)


class VerdictTests(unittest.TestCase):
    def test_three_way_statement(self):
        import report
        def summ(hi_w, hi_c):
            dom = lambda hi: {"depth_contrasts": {"bos1_d16_minus_d8": {"ci95": [-1.0, hi]}}}
            return {"domains": {"wikitext": dom(hi_w), "c4": dom(hi_c)}}
        self.assertIn("both", report.verdict(summ(-0.01, -0.02), [8, 16])["d16"]["statement"])
        self.assertIn("only in c4", report.verdict(summ(0.01, -0.02), [8, 16])["d16"]["statement"])
        self.assertIn("not significantly", report.verdict(summ(0.01, 0.0), [8, 16])["d16"]["statement"])


class DataTests(unittest.TestCase):
    def test_wikitext_articles(self):
        lines = ["", " = Alpha = \n", "\n", " Alpha body one .\n", " = = Section = = \n", " more alpha\n",
                 " = Beta = \n", " beta body\n"]
        arts = prepare_data.wikitext_articles(lines)
        self.assertEqual([a[0] for a in arts], ["Alpha", "Beta"])
        self.assertIn("= = Section = =", arts[0][1])
        self.assertTrue(arts[0][1].startswith("Alpha body one"))

    def test_read_json_gz_column(self):
        import gzip
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(json.dumps({"text": "one", "url": "u"}) + "\n" + json.dumps({"text": "two"}) + "\n")
            self.assertEqual(prepare_data.read_column(path, "text"), ["one", "two"])

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

    def test_mass_guard_negative_and_positive(self):
        good = self.torch.softmax(self.torch.randn(32768).float(), dim=-1)    # FP32 rounding only
        self.g.check_mass(self.torch, good)
        for bad in (good * 1.01, self.torch.tensor([0.5, 0.6]), self.torch.tensor([1.2, -0.2]),
                    self.torch.tensor([float("nan"), 1.0])):
            with self.assertRaises(ValueError):
                self.g.check_mass(self.torch, bad)

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
    for domain in ("wikitext", "c4"):
        for i in range(2):
            text = " ".join(words[(j * (i + 3) + len(domain)) % len(words)] for j in range(400))
            rows.append({"domain": domain, "doc_id": "%s-%03d" % (domain, i),
                         "text_sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text})
    with open(root / "texts.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    old = {"samples": [{"tokens": [int(t) for t in tok.encode(rows[0]["text"]).ids[:257]]}]}
    (root / "old32.json").write_text(json.dumps(old))
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
        args = ["--texts", str(self.fx / "texts.jsonl"), "--out", str(out), "--depths", "2,4",
                "--token-windows", str(self.fx / "old32.json"), *self.common_args]
        r0 = run("eval_depth.py", *args, "--max-hours", "0")   # cap reached at once: clean stop
        self.assertEqual(r0.returncode, 3, r0.stdout + r0.stderr)
        self.assertIn("STOPPED", r0.stdout)
        r = run("eval_depth.py", *args)                        # same config continues and finishes
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = read_jsonl(out / "rows.jsonl")
        self.assertEqual(len(rows), 5 * 2 * 2 * 2)   # (4 texts + 1 token window) x replicas x BOS x depths
        self.assertEqual(sum(1 for x in rows if x["domain"] == "wikitext_old32"), 8)
        self.assertTrue(all(len(x["nll"]) == common.WINDOW - 1 for x in rows))
        cfg = json.loads((out / "config.json").read_text())
        self.assertTrue(cfg["state_check"]["all_equal"])
        by = {(x["doc_id"], x["rep"], x["bos"], x["depth"]): x for x in rows}
        a, b = by[("wikitext-000", 0, 1, 2)], by[("wikitext-000", 0, 0, 2)]
        self.assertEqual(a["seed"], b["seed"])
        self.assertNotEqual(a["nll"], b["nll"])         # BOS changes the prediction
        r2 = run("eval_depth.py", *args)                 # resume: nothing left to do
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertEqual(len(read_jsonl(out / "rows.jsonl")), len(rows))
        r3 = run("eval_depth.py", *[x if x != "2,4" else "2,3" for x in args], "--max-hours", "6")
        self.assertNotEqual(r3.returncode, 0)            # different config refused in same dir
        r4 = run("report.py", "--run", str(out))
        self.assertEqual(r4.returncode, 0, r4.stdout + r4.stderr)
        s = json.loads((out / "summary.json").read_text())
        self.assertEqual(sorted(s["domains"]), ["c4", "wikitext", "wikitext_old32"])
        c = s["domains"]["c4"]["depth_contrasts"]["bos1_d4_minus_d2"]
        self.assertEqual(c["n"], 2)
        self.assertIn("d2_early_bos_minus_nobos", s["domains"]["wikitext"]["bos_contrasts"])
        self.assertIn("statement", s["verdict"]["d4"])
        self.assertIn("tokens_per_second", s["timing"]["bos1_d2"])
        csv_lines = (out / "per_window.csv").read_text().splitlines()
        self.assertEqual(len(csv_lines), 1 + 5)
        self.assertTrue(csv_lines[0].startswith("domain,doc_id,bos1_d2"))

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
