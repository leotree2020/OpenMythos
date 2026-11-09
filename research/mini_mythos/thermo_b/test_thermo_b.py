"""Thermo-B tests on CPU.

Pure tests (schedule, RankLoRA on a toy network, geometry estimators, gate/report rules) need only
torch and numpy. Model tests use the random tiny Parcae fixture (NOT the real weights, NOT a GPU run)
and are skipped when the pinned upstream checkout is not available.

  STAGE0_UPSTREAM=/path/to/parcae python -B -m unittest test_thermo_b -v
"""
import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
for sub in ("stage0", "stage2", "stage3", "stage3b"):
    sys.path.insert(0, str(HERE.parent / sub))
sys.path.insert(0, str(HERE))                 # first: stage0/2/3 have a report.py too
import importlib.util  # noqa: E402

import torch  # noqa: E402
import gpu_common as G  # noqa: E402
import geometry as GEO  # noqa: E402
from rank_lora import RankLoRA, Schedule, curve_steps, stage_starts  # noqa: E402

_spec = importlib.util.spec_from_file_location("thermo_report", HERE / "report.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


# ------------------------------------------------------------------ toy network with the Parcae layout

class Block(torch.nn.Module):
    def __init__(self, d):
        super().__init__()
        self.attn = torch.nn.Sequential(torch.nn.Linear(d, d))
        self.mlp = torch.nn.Sequential(torch.nn.Linear(d, 2 * d), torch.nn.GELU(), torch.nn.Linear(2 * d, d))

    def forward(self, x):
        x = x + self.attn(x)
        return x + self.mlp(x)


class Toy(torch.nn.Module):
    def __init__(self, d=16, seed=0):
        super().__init__()
        torch.manual_seed(seed)
        self.transformer = torch.nn.ModuleDict({
            "prelude": torch.nn.ModuleList([Block(d)]),
            "core_block": torch.nn.ModuleList([Block(d), Block(d)]),
            "coda": torch.nn.ModuleList([Block(d)]),
            "ln_f": torch.nn.LayerNorm(d)})
        for p in self.parameters():
            p.requires_grad_(False)

    def forward(self, x):
        for part in ("prelude", "core_block", "coda"):
            for b in self.transformer[part]:
                x = b(x)
        return self.transformer["ln_f"](x)


class ScheduleTests(unittest.TestCase):
    def test_expand_stages(self):
        s = Schedule("expand", 60)
        self.assertEqual(s.starts, [0, 10, 20, 30, 40, 50])
        self.assertEqual([s.rank(t) for t in (0, 9, 10, 29, 30, 49, 50, 59)], [1, 1, 2, 4, 8, 16, 28, 28])
        self.assertEqual(s.new_components(0), (0, 1))
        self.assertEqual(s.new_components(15), (1, 2))
        self.assertEqual(s.new_components(55), (16, 28))
        u = Schedule("expand", 61)
        self.assertEqual(u.starts, [0, 10, 20, 30, 40, 50])
        self.assertEqual(u.stage_len(5), 11)
        self.assertEqual(sum(u.stage_len(k) for k in range(6)), 61)

    def test_temperature_anneals_within_each_stage(self):
        s = Schedule("expand", 60, t0=1.0, anneal=0.5)
        self.assertEqual(s.temperature(0), 1.0)
        self.assertAlmostEqual(s.temperature(2), 0.6)
        self.assertEqual(s.temperature(5), 0.0)
        self.assertEqual(s.temperature(9), 0.0)
        self.assertEqual(s.temperature(10), 1.0)           # hot again when the next components open
        self.assertAlmostEqual(s.temperature(53), 0.4)
        self.assertTrue(all(Schedule("expand", 60).temperature(t) == 0.0 for t in range(60)))

    def test_full_and_invalid(self):
        f = Schedule("full", 60)
        self.assertTrue(all(f.rank(t) == 28 for t in range(60)))
        self.assertEqual(f.new_components(30), (0, 28))
        self.assertEqual(f.temperature(0), 0.0)
        for bad in (lambda: Schedule("full", 60, t0=1.0), lambda: Schedule("expand", 60, ranks=(1, 4, 2, 28)),
                    lambda: Schedule("expand", 60, ranks=(1, 2, 16)), lambda: Schedule("expand", 5),
                    lambda: Schedule("expand", 60, ranks=(0, 28)), lambda: Schedule("other", 60)):
            self.assertRaises(ValueError, bad)

    def test_curve_points(self):
        self.assertEqual(curve_steps(60), [0, 10, 20, 30, 40, 50, 60])
        self.assertEqual(curve_steps(1525), [0] + stage_starts(1525, 6)[1:] + [1525])
        self.assertEqual(curve_steps(6, 3), [0, 2, 4, 6])


class RankLoRATests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.x = torch.randn(3, 5, 16, generator=torch.Generator().manual_seed(1))

    def randomize_B(self, lora, seed=2):
        gen = torch.Generator().manual_seed(seed)
        with torch.no_grad():
            for k in sorted(lora.params):
                if k.endswith(".B"):
                    lora.params[k].copy_(torch.randn(lora.params[k].shape, generator=gen))

    def test_full_mask_is_bitwise_the_stage3_lora(self):
        a, b = Toy(), Toy()
        ref = G.LoRA(torch, a, rank=6, alpha=12, seed=0)
        new = RankLoRA(torch, b, rank=6, alpha=12, seed=0)
        self.assertEqual(set(ref.params), set(new.params))
        self.assertEqual(ref.count(), new.count())
        self.randomize_B(ref)
        self.randomize_B(new)
        for k in ref.params:
            self.assertTrue(torch.equal(ref.params[k], new.params[k]), k)
        self.assertTrue(torch.equal(a(self.x), b(self.x)))

    def test_zero_B_is_native_at_any_rank(self):
        m = Toy()
        base = m(self.x)
        lora = RankLoRA(torch, m, rank=6, alpha=12, seed=3)
        for r in (0, 1, 3, 6):
            lora.set_rank(r)
            self.assertTrue(torch.equal(m(self.x), base), r)
        self.randomize_B(lora)
        lora.set_rank(0)                                   # mask 0 is the native model, exactly
        self.assertTrue(torch.equal(m(self.x), base))

    def test_locked_components_untouched_and_unlock_preserves_output(self):
        m = Toy()
        lora = RankLoRA(torch, m, rank=6, alpha=12, seed=0)
        init = {k: v.detach().clone() for k, v in lora.params.items()}
        lora.set_rank(2)
        opt = torch.optim.AdamW(lora.parameters(), lr=1e-2, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0)
        target = torch.randn(3, 5, 16, generator=torch.Generator().manual_seed(5))
        for _ in range(5):
            loss = (m(self.x) - target).pow(2).mean()
            loss.backward()
            for name, g in lora.component_views(2, 6):
                self.assertEqual(float(g.abs().max()), 0.0, name)       # locked: exactly zero gradient
            opt.step()
            opt.zero_grad(set_to_none=False)
        for name, v in lora.component_views(2, 6, grads=False):
            ref = init[name][2:6] if name.endswith(".A") else init[name][:, 2:6]
            self.assertTrue(torch.equal(v, ref), name)                  # bitwise unchanged
        trained = [float(v.abs().max()) for n, v in lora.component_views(0, 2, grads=False) if n.endswith(".B")]
        self.assertTrue(max(trained) > 0)                               # the open ones did train
        before = m(self.x)
        lora.set_rank(4)
        self.assertTrue(torch.equal(m(self.x), before))                 # opening more ranks: same output
        lora.set_rank(6)
        self.assertTrue(torch.equal(m(self.x), before))

    def test_gradient_noise_only_on_new_components(self):
        m = Toy()
        lora = RankLoRA(torch, m, rank=6, alpha=12, seed=0)
        self.randomize_B(lora)
        with torch.no_grad():                               # components 2..3 just opened: B columns 0
            for k, v in lora.params.items():
                if k.endswith(".B"):
                    v[:, 2:4] = 0
        lora.set_rank(4)
        (m(self.x) ** 2).mean().backward()
        orig = {k: v.grad.clone() for k, v in lora.params.items()}
        n = lora.add_gradient_noise(torch, 2, 4, 0.5, seed=0, step=7)
        self.assertGreater(n, 0)
        z = []
        for k, p in lora.params.items():
            g, o = p.grad, orig[k]
            if k.endswith(".A"):
                self.assertTrue(torch.equal(g, o), k)      # A rows of new comps have zero gradient: no noise
            else:
                self.assertTrue(torch.equal(g[:, :2], o[:, :2]) and torch.equal(g[:, 4:], o[:, 4:]), k)
                rms = float(o[:, 2:4].double().pow(2).mean().sqrt())
                z.append(((g[:, 2:4] - o[:, 2:4]) / (0.5 * rms)).flatten())
        z = torch.cat(z)
        self.assertLess(abs(float(z.std()) - 1.0), 0.2)
        g1 = {k: v.grad.clone() for k, v in lora.params.items()}
        for k, p in lora.params.items():                    # same (seed, step) -> same noise
            p.grad.copy_(orig[k])
        lora.add_gradient_noise(torch, 2, 4, 0.5, seed=0, step=7)
        self.assertTrue(all(torch.equal(g1[k], p.grad) for k, p in lora.params.items()))
        for k, p in lora.params.items():
            p.grad.copy_(orig[k])
        lora.add_gradient_noise(torch, 2, 4, 0.5, seed=0, step=8)
        self.assertFalse(all(torch.equal(g1[k], p.grad) for k, p in lora.params.items()))
        for k, p in lora.params.items():
            p.grad.copy_(orig[k])
        self.assertEqual(lora.add_gradient_noise(torch, 2, 4, 0.0, seed=0, step=7), 0)
        self.assertTrue(all(torch.equal(orig[k], p.grad) for k, p in lora.params.items()))

    def test_spectra_match_explicit_svd(self):
        m = Toy()
        lora = RankLoRA(torch, m, rank=6, alpha=12, seed=0)
        self.randomize_B(lora)
        lora.set_rank(3)
        spec = lora.spectra(torch)
        for name, s in spec.items():
            A, B = lora.params[name + ".A"].double(), lora.params[name + ".B"].double()
            ref = torch.linalg.svdvals(lora.scale * B[:, :3] @ A[:3])[:3]
            self.assertTrue(np.allclose(sorted(s, reverse=True), ref.tolist(), rtol=1e-9, atol=1e-12), name)
        lora.set_rank(0)
        self.assertTrue(all(v == [] for v in lora.spectra(torch).values()))


class GeometryTests(unittest.TestCase):
    def embed(self, X, D=30, seed=0):
        q, _ = torch.linalg.qr(torch.randn(D, D, generator=torch.Generator().manual_seed(seed), dtype=torch.float64))
        return X.double() @ q[:X.shape[1]]

    def test_twonn_recovers_known_dimensions(self):
        gen = torch.Generator().manual_seed(0)
        t = torch.rand(1500, generator=gen, dtype=torch.float64) * 4 * math.pi
        curve = self.embed(torch.stack([torch.cos(t), torch.sin(t), 0.3 * t], 1))
        d1, n1 = GEO.twonn(torch, curve)
        self.assertEqual(n1, 1500)
        self.assertTrue(0.85 < d1 < 1.2, d1)
        plane = self.embed(torch.rand(2000, 2, generator=gen, dtype=torch.float64))
        d2, _ = GEO.twonn(torch, plane)
        self.assertTrue(1.7 < d2 < 2.3, d2)
        cloud = self.embed(torch.randn(3000, 6, generator=gen, dtype=torch.float64))
        d6, _ = GEO.twonn(torch, cloud)
        self.assertTrue(4.8 < d6 < 7.2, d6)
        self.assertEqual(GEO.twonn(torch, torch.zeros(50, 8)), (None, 1))      # all duplicates
        doubled = torch.cat([plane, plane, plane[:500]], 0)                     # duplicates are merged
        self.assertEqual(GEO.twonn(torch, doubled), GEO.twonn(torch, plane))

    def test_participation_ratio_and_effective_rank(self):
        gen = torch.Generator().manual_seed(1)
        iso = torch.randn(5000, 8, generator=gen, dtype=torch.float64)
        self.assertTrue(7.5 < GEO.participation_ratio(torch, self.embed(iso)) < 8.5)
        line = self.embed(torch.randn(500, 1, generator=gen, dtype=torch.float64))
        self.assertAlmostEqual(GEO.participation_ratio(torch, line), 1.0, places=6)
        self.assertIsNone(GEO.participation_ratio(torch, torch.zeros(10, 4)))
        self.assertAlmostEqual(GEO.effective_rank([1, 1, 1, 1]), 4.0)
        self.assertAlmostEqual(GEO.effective_rank([2.0, 0.0, 0.0]), 1.0)
        self.assertEqual(GEO.effective_rank([]), 0.0)
        s = GEO.adapter_summary({"a": [1, 1], "b": [1, 0], "c": [1, 1, 1, 1]})
        self.assertEqual(s["layers"], 3)
        self.assertAlmostEqual(s["effective_rank_median"], 2.0)
        self.assertAlmostEqual(s["update_fro2_total"], 7.0)


class ReportTests(unittest.TestCase):
    def make(self, root, values):
        for name, ood in values.items():
            d = Path(root) / name
            d.mkdir(parents=True)
            means = {"books": ood, "c4": ood, "wikitext": ood, "fineweb": 2.8}
            (d / "summary.json").write_text(json.dumps({"dev_domain_mean_nll": means}))

    def test_gate_candidate_and_completeness(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make(tmp, {"full_lr0.0001_s0": 3.000, "full_lr0.0001_s1": 3.001,
                            "expand_lr0.0003_s0": 2.998, "expand_lr0.0003_s1": 2.999,
                            "thermo_lr0.0003_s0": 2.995, "thermo_lr0.0003_s1": 2.997,
                            "expand_lr0.001_s0": 2.5})                     # other LR: ignored
            g = R.gate(tmp, "1e-4", "3e-4")
            self.assertTrue(g["complete"] and g["pass"])
            self.assertEqual(g["candidate_arm"], "thermo")
            self.assertEqual(g["candidate_run"], "thermo_lr0.0003_s0")
            self.assertEqual(g["control_run"], "full_lr0.0001_s0")
            self.assertAlmostEqual(g["noise_floor_ood_dev"], 0.002)
            self.assertAlmostEqual(g["hypotheses_dev_ood"]["H1_expand_minus_full"][0], -0.002)
            self.assertEqual(Path(R.choose([Path(tmp) / "expand_lr0.0003_s0", Path(tmp) / "expand_lr0.001_s0"])).name,
                             "expand_lr0.001_s0")
        with tempfile.TemporaryDirectory() as tmp:
            self.make(tmp, {"full_lr0.0001_s0": 3.000, "full_lr0.0001_s1": 2.990,
                            "expand_lr0.0003_s0": 2.998, "expand_lr0.0003_s1": 2.999,
                            "thermo_lr0.0003_s0": 3.010, "thermo_lr0.0003_s1": 3.010})
            g = R.gate(tmp, "1e-4", "3e-4")
            self.assertTrue(g["complete"])
            self.assertEqual(g["candidate_arm"], "expand")
            self.assertFalse(g["pass"])                                    # seed 1 loses to C
        with tempfile.TemporaryDirectory() as tmp:
            self.make(tmp, {"full_lr0.0001_s0": 3.0, "full_lr0.0001_s1": 3.0, "expand_lr0.0003_s0": 2.9,
                            "expand_lr0.0003_s1": 2.9, "thermo_lr0.0003_s0": 2.9})
            g = R.gate(tmp, "1e-4", "3e-4")
            self.assertFalse(g["complete"] or g["pass"])
            self.assertEqual(g["missing"], ["thermo_s1"])

    def test_tokens_to_reach(self):
        pts = [(0, 3.0), (10, 2.8), (20, 2.7)]
        self.assertAlmostEqual(R.tokens_to_reach(pts, 2.75), 15.0)
        self.assertEqual(R.tokens_to_reach(pts, 3.1), 0.0)
        self.assertEqual(R.tokens_to_reach(pts, 2.7), 20.0)
        self.assertIsNone(R.tokens_to_reach(pts, 2.6))


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


@unittest.skipUnless(HAVE_STACK, "tokenizers/upstream not available")
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
        cls.data, cls.root = root / "data", root
        cls.common = ["--upstream", UPSTREAM, "--model-dir", str(cls.fx / "model"),
                      "--tokenizer", str(cls.fx / "tokenizer.json"), "--device", "cpu", "--threads", "1",
                      "--no-pin-check"]
        torch.set_num_threads(1)
        model, _ = G.load_model(torch, UPSTREAM, cls.fx / "model", cls.fx / "tokenizer.json", "cpu", pin_check=False)
        windows = G.load_windows(cls.sets, "dev")
        cls.native_csv = root / "native_dev.csv"
        G.write_per_window(cls.native_csv, G.evaluate(torch, model, windows, "cpu"), windows)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_script(self, where, script, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", str(where / script), *args], capture_output=True, text=True,
                              env=env)

    def train(self, out, arm, *extra):
        return self.run_script(HERE, "train.py", "--arm", arm, "--lr", "1e-2", "--seed", "0",
                               "--out", str(out), "--data", str(self.data), "--sets", str(self.sets),
                               "--native-dev", str(self.native_csv),
                               "--precision", "fp32", "--tokens", str(6 * 4 * 64), "--seq-len", "64",
                               "--micro-batch", "2", "--global-batch", "4", "--steps-pair", "1,1",
                               "--rank", "4", "--ranks", "1,2,4", "--ckpt-every", "2",
                               "--probe-per-domain", "1", "--probe-tokens", "20", *self.common, *extra)

    def test_identity_at_start_on_parcae(self):
        model, _ = G.load_model(torch, UPSTREAM, self.fx / "model", self.fx / "tokenizer.json", "cpu", pin_check=False)
        twin = copy.deepcopy(model)
        for p in list(model.parameters()) + list(twin.parameters()):
            p.requires_grad_(False)
        x = torch.randint(3, 500, (2, 40))

        def logits(m):
            torch.manual_seed(1)
            return m(x, return_logits=True, num_steps_pair=torch.tensor([3, 0]))["logits"]
        base = logits(model)
        lora = RankLoRA(torch, model, rank=4, alpha=8, seed=0)
        for r in (1, 4):
            lora.set_rank(r)
            self.assertTrue(torch.equal(logits(model), base), r)
        ref = G.LoRA(torch, twin, rank=4, alpha=8, seed=0)
        gen = torch.Generator().manual_seed(4)
        with torch.no_grad():
            for k in sorted(lora.params):
                if k.endswith(".B"):
                    v = 0.05 * torch.randn(lora.params[k].shape, generator=gen)
                    lora.params[k].copy_(v)
                    ref.params[k].copy_(v)
        self.assertTrue(torch.equal(logits(model), logits(twin)))        # full mask == Stage 3a LoRA
        self.assertFalse(torch.equal(logits(model), base))

    def test_curve_scores_equal_evaluate(self):
        spec = importlib.util.spec_from_file_location("thermo_train", HERE / "train.py")
        T = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(T)
        model, _ = G.load_model(torch, UPSTREAM, self.fx / "model", self.fx / "tokenizer.json", "cpu", pin_check=False)
        windows = G.load_windows(self.sets, "dev")
        feats, per = T.features(torch, model, windows, "cpu", 5)
        ref = G.evaluate(torch, model, windows, "cpu", replicas=1)
        self.assertEqual(per, ref)                                      # bitwise, replica 0
        for d, f in feats.items():
            self.assertEqual(tuple(f["windows"].shape)[0], 1)
            self.assertEqual(tuple(f["tokens"].shape)[0], 5)

    def test_arms_curve_resume_reload(self):
        runs = self.root / "runs"
        for arm in ("full", "expand", "thermo"):
            run = runs / ("%s_lr0.01_s0" % arm)
            r = self.train(run, arm)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            log = read_jsonl(run / "train_log.jsonl")
            self.assertEqual([x["rank"] for x in log], [4] * 6 if arm == "full" else [1, 1, 2, 2, 4, 4])
            temps = [x["temperature"] for x in log]
            self.assertEqual(temps, [1.0, 0.0, 1.0, 0.0, 1.0, 0.0] if arm == "thermo" else [0.0] * 6)
            if arm == "thermo":
                self.assertGreater(log[2]["noised_entries"], 0)
            curve = read_jsonl(run / "curve.jsonl")
            self.assertEqual([c["step"] for c in curve], [0, 2, 4, 6])
            self.assertLessEqual(curve[0]["init_vs_native_max_abs_diff"], 1e-6)
            for level in ("tokens", "windows"):
                self.assertIsNone(curve[0]["geometry"]["pooled"][level]["pr_dh"])      # dh = 0 at the start
                self.assertGreater(curve[-1]["geometry"]["pooled"][level]["dh_rms"], 0)
                self.assertIn("twonn_h", curve[0]["geometry"]["domains"]["books"][level])
            ev = self.run_script(HERE.parent / "stage3", "eval_run.py", "--run", str(run), "--split", "dev",
                                 "--sets", str(self.sets), "--compare", str(run / "eval_dev.csv"),
                                 "--out", str(self.root / ("reload_%s.csv" % arm)), *self.common)
            self.assertEqual(ev.returncode, 0, ev.stdout + ev.stderr)       # Stage 3a loader reproduces it
        # resume is bitwise, noise and learning curve included
        res = self.root / "res" / "thermo_lr0.01_s0"
        stop = self.train(res, "thermo", "--stop-after-step", "3")
        self.assertEqual(stop.returncode, 3, stop.stdout + stop.stderr)
        again = self.train(res, "thermo", "--resume")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        a = torch.load(runs / "thermo_lr0.01_s0" / "final_params.pt", weights_only=True)
        b = torch.load(res / "final_params.pt", weights_only=True)
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))
        ca, cb = read_jsonl(runs / "thermo_lr0.01_s0" / "curve.jsonl"), read_jsonl(res / "curve.jsonl")
        self.assertEqual([c["dev_rep0_domain_mean_nll"] for c in ca], [c["dev_rep0_domain_mean_nll"] for c in cb])
        # measuring the curve does not change the training (RNG restored)
        quiet = self.root / "quiet" / "expand_lr0.01_s0"
        q = self.train(quiet, "expand", "--no-eval")
        self.assertEqual(q.returncode, 0, q.stdout + q.stderr)
        a = torch.load(runs / "expand_lr0.01_s0" / "final_params.pt", weights_only=True)
        b = torch.load(quiet / "final_params.pt", weights_only=True)
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))
        # a changed configuration is refused
        bad = self.train(runs / "expand_lr0.01_s0", "expand", "--t0", "2.0", "--anneal", "0.25")
        self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
