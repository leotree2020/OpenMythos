"""Stage 3a tests on CPU with a random tiny Parcae model (NOT the real weights, NOT a GPU run).

  STAGE0_UPSTREAM=/path/to/parcae python -B -m unittest test_stage3 -v
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
sys.path.insert(0, str(HERE))                 # first: stage0 and stage2 also have a report.py
import importlib.util  # noqa: E402
import gpu_common as G  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage3_report", HERE / "report.py")   # stage0/2 have report.py too
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

UPSTREAM = os.environ.get("STAGE0_UPSTREAM", "/workspaces/mythos-parcae-pinned")
try:
    import torch
    import tokenizers  # noqa: F401
    HAVE_STACK = Path(UPSTREAM, "receval").is_dir()
except ImportError:
    HAVE_STACK = False


class VerdictTests(unittest.TestCase):
    def dom(self, delta, lo, hi):
        return {"delta_nll": delta, "ci95": [lo, hi]}

    def test_rules(self):
        good = {"books": self.dom(-0.005, -0.007, -0.003), "c4": self.dom(-0.004, -0.006, -0.002),
                "wikitext": self.dom(-0.001, -0.003, 0.001), "fineweb": self.dom(0.001, -0.001, 0.003)}
        crit, ok = R.verdict(good, {0: -0.004, 1: -0.003}, 0.001)
        self.assertTrue(ok, crit)
        self.assertEqual(crit["1_two_of_three_ood_improved"]["domains"], ["books", "c4"])
        # mean over OOD not low enough
        weak = dict(good, wikitext=self.dom(0.002, 0.0, 0.004))
        crit, ok = R.verdict(weak, {0: -0.004, 1: -0.003}, 0.001)
        self.assertFalse(ok)
        self.assertFalse(crit["2_mean_ood_delta"]["pass"])
        # a domain clearly worse
        crit, ok = R.verdict(dict(good, fineweb=self.dom(0.004, 0.002, 0.006)), {0: -0.004, 1: -0.003}, 0.001)
        self.assertFalse(crit["3_no_domain_clearly_worse"]["pass"])
        # effect within training noise
        crit, ok = R.verdict(good, {0: -0.004, 1: -0.0005}, 0.001)
        self.assertFalse(crit["4_beyond_training_noise"]["pass"])
        # CI crossing zero does not count for criterion 1
        crit, _ = R.verdict(dict(good, c4=self.dom(-0.004, -0.008, 0.0001)), {0: -0.004, 1: -0.003}, 0.001)
        self.assertEqual(crit["1_two_of_three_ood_improved"]["domains"], ["books"])


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
        cls.data, cls.root = root / "data", root
        cls.common = ["--upstream", UPSTREAM, "--model-dir", str(cls.fx / "model"),
                      "--tokenizer", str(cls.fx / "tokenizer.json"), "--device", "cpu", "--threads", "1",
                      "--no-pin-check"]
        torch.set_num_threads(1)
        cls.model, _ = G.load_model(torch, UPSTREAM, cls.fx / "model", cls.fx / "tokenizer.json", "cpu",
                                    pin_check=False)
        for p in cls.model.parameters():
            p.requires_grad_(False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def logits(self, x, steps=(3, 0), seed=1):
        torch.manual_seed(seed)
        return self.model(x, return_logits=True, num_steps_pair=torch.tensor(steps))["logits"]

    def perturb(self, mech, scale=0.5):
        gen = torch.Generator().manual_seed(7)
        with torch.no_grad():
            for k, p in mech.params.items():
                if k.startswith("gate"):
                    p.copy_(scale * (1 + torch.rand(p.shape, generator=gen)))
                else:
                    p.add_(0.05 * torch.randn(p.shape, generator=gen))

    def test_gate_zero_is_bitwise_native_and_count(self):
        from moda_p import MoDAP
        x = torch.randint(3, 500, (2, 40))
        base = self.logits(x)
        mech = MoDAP(self.model)
        try:
            self.assertTrue(torch.equal(base, self.logits(x)))
            a = self.model.transformer.core_block[0].attn
            C = self.model.config.n_embd
            n = len(self.model.transformer.core_block)
            self.assertEqual(mech.count(), n * 2 * a.n_kv_head * a.head_dim * C + n * a.n_head)
            self.perturb(mech)
            self.assertFalse(torch.equal(base, self.logits(x)))
        finally:
            mech.remove()
        self.assertTrue(torch.equal(base, self.logits(x)))           # hooks fully removed
        self.assertEqual(2 * 2 * 768 * 768 + 2 * 6, 2_359_308)       # README count for Parcae-140M
        self.assertEqual(664_464 // 8 * 28, 2_325_624)               # C-LoRA-r28 from the Stage 2 r8 count

    def reference_logits(self, mech, x, steps, seed):
        """Independent explicit implementation: core blocks written out by hand, depth attention with
        RoPE applied to both query and depth keys at the same position, explicit per-entry softmax."""
        import types
        import torch.nn.functional as F
        from parcae_lm.modules.utils import apply_rotary_emb_complex_like
        model = self.model
        core = model.transformer.core_block
        n = len(core)
        memory = []                                       # (writer layer, hidden state) in write order

        def core_forward(self_, x, input_embeds, freqs_cis, mask, step, total_steps, **kw):
            x = self_.transformer.adapter(x, input_embeds)
            for l, block in enumerate(core):
                a = block.attn
                ve_idx = str(self_.config.n_layers_in_prelude + l)
                ve = self_.value_embeds[ve_idx](self_._current_input_ids) if ve_idx in self_.value_embeds else None
                xn = block.norm_1(x)
                B, T, C = xn.shape
                q = a.c_q(xn).view(B, T, a.n_head, a.head_dim)
                k = a.c_k(xn).view(B, T, a.n_kv_head, a.head_dim)
                v = a.c_v(xn).view(B, T, a.n_kv_head, a.head_dim)
                if ve is not None and a.ve_gate is not None:
                    gate = 2 * torch.sigmoid(a.ve_gate(xn[..., :a.ve_gate_channels]))
                    v = v + gate.unsqueeze(-1) * ve.view(B, T, a.n_kv_head, a.head_dim)
                q_raw = q
                q, k = apply_rotary_emb_complex_like(q, k, freqs_cis=freqs_cis)
                q, k = F.rms_norm(q, (a.head_dim,)), F.rms_norm(k, (a.head_dim,))
                y = F.scaled_dot_product_attention(q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2),
                                                   is_causal=True).transpose(1, 2)
                if memory:
                    logits, values = [], []
                    for j, h in memory:
                        hn = core[(j + 1) % n].norm_1(h)
                        kd = F.linear(hn, mech.params["write.%d.k" % j]).view(B, T, a.n_kv_head, a.head_dim)
                        vd = F.linear(hn, mech.params["write.%d.v" % j]).view(B, T, a.n_kv_head, a.head_dim)
                        qr, kr = apply_rotary_emb_complex_like(q_raw, kd, freqs_cis=freqs_cis)
                        qr, kr = F.rms_norm(qr, (a.head_dim,)), F.rms_norm(kr, (a.head_dim,))
                        logits.append((qr * kr).sum(-1) / a.head_dim ** 0.5)       # [B, T, H]
                        values.append(vd)
                    mx = torch.stack(logits).max(0).values
                    ex = [torch.exp(z - mx) for z in logits]
                    tot = sum(ex)
                    depth = sum((e / tot).unsqueeze(-1) * vd for e, vd in zip(ex, values))
                    y = y + mech.params["gate.%d" % l].view(1, 1, -1, 1) * depth
                x = x + a.c_proj(y.reshape(B, T, C))
                x = x + block.mlp(block.norm_2(x))
                memory.append((l, x))
            return x

        model.core_block_forward = types.MethodType(core_forward, model)
        try:
            return self.logits(x, steps, seed)
        finally:
            del model.core_block_forward

    def test_matches_independent_reference(self):
        from moda_p import MoDAP
        x = torch.randint(3, 500, (2, 48))
        mech = MoDAP(self.model)
        try:
            self.perturb(mech)
            hooked = self.logits(x, (3, 0), 4)
        finally:
            mech.remove()
        ref = self.reference_logits(mech, x, (3, 0), 4)
        native = self.logits(x, (3, 0), 4)
        print("hooked-vs-reference max |diff| %.2e, vs native %.2e" % (float((hooked - ref).abs().max()), float((hooked - native).abs().max())))
        self.assertLess(float((hooked - ref).abs().max()), 1e-4)
        self.assertGreater(float((hooked - native).abs().max()), 1e-2)   # the mechanism really does something

    def test_causal(self):
        from moda_p import MoDAP
        x = torch.randint(3, 500, (1, 40))
        y = x.clone()
        y[0, 25:] = torch.randint(3, 500, (15,))
        mech = MoDAP(self.model)
        try:
            self.perturb(mech)
            a, b = self.logits(x), self.logits(y)
        finally:
            mech.remove()
        self.assertLess(float((a[0, :25] - b[0, :25]).abs().max()), 1e-5)
        self.assertGreater(float((a[0, 25:] - b[0, 25:]).abs().max()), 1e-3)

    def test_writes_from_no_grad_steps_get_gradient(self):
        from moda_p import MoDAP
        x = torch.randint(3, 500, (2, 32))
        mech = MoDAP(self.model)
        try:
            self.perturb(mech)
            torch.manual_seed(2)
            loss = self.model(x[:, :-1].contiguous(), labels=x[:, 1:].contiguous(), num_steps_pair=torch.tensor([1, 1]))["loss"]
            loss.backward()
            # write.1 is only read through the entry written in the no-gradient step (its step-1
            # entry is never read), so a gradient here proves those writes are trained
            g = mech.params["write.1.k"].grad
            self.assertIsNotNone(g)
            self.assertGreater(float(g.abs().max()), 0)
            self.assertGreater(float(mech.params["gate.0"].grad.abs().max()), 0)
        finally:
            mech.remove()

    def run_script(self, script, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", str(HERE / script), *args], capture_output=True, text=True, env=env)

    def train(self, out, mode, lr, seed=0, *extra):
        return self.run_script("train.py", "--mode", mode, "--lr", str(lr), "--seed", str(seed), "--out", str(out),
                               "--data", str(self.data), "--sets", str(self.sets), "--precision", "fp32",
                               "--tokens", str(6 * 4 * 64), "--seq-len", "64", "--micro-batch", "2",
                               "--global-batch", "4", "--steps-pair", "1,1", "--rank", "4", "--ckpt-every", "2",
                               *self.common, *extra)

    def test_end_to_end(self):
        runs = self.root / "runs"
        tb = self.run_script("token_budget.py", "--data", str(self.data), "--seq-len", "64", "--global-batch", "4")
        self.assertEqual(tb.returncode, 0, tb.stderr)
        self.assertGreater(int(tb.stdout.strip()), 6 * 4 * 64)
        for mode, lr in (("lora", 1e-3), ("moda", 1e-3), ("moda", 1e-2)):
            r = self.train(runs / ("%s_lr%g_s0" % (mode, lr)), mode, lr, 0)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ch = self.run_script("report.py", "choose", str(runs / "moda_lr0.001_s0"), str(runs / "moda_lr0.01_s0"))
        self.assertEqual(ch.returncode, 0, ch.stderr)
        lrs = {"lora": "0.001", "moda": Path(ch.stdout.strip()).name.split("_lr")[1].split("_s")[0]}
        g = self.run_script("report.py", "gate", "--runs", str(runs), "--lora", lrs["lora"], "--moda", lrs["moda"])
        self.assertEqual(g.returncode, 2, g.stdout + g.stderr)               # seed 1 missing: incomplete
        for mode in ("lora", "moda"):
            r = self.train(runs / ("%s_lr%s_s1" % (mode, lrs[mode])), mode, float(lrs[mode]), 1)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # MoDA resume is bitwise on CPU
        stop = self.train(self.root / "res" / "moda_lr0.001_s0", "moda", 1e-3, 0, "--stop-after-step", "3")
        self.assertEqual(stop.returncode, 3, stop.stdout + stop.stderr)
        res = self.train(self.root / "res" / "moda_lr0.001_s0", "moda", 1e-3, 0, "--resume")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        a = torch.load(runs / "moda_lr0.001_s0" / "final_params.pt", weights_only=True)
        b = torch.load(self.root / "res" / "moda_lr0.001_s0" / "final_params.pt", weights_only=True)
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))
        self.assertTrue(any(float(v.abs().max()) > 0 for k, v in a.items() if k.startswith("gate")))
        s = json.loads((runs / "moda_lr0.001_s0" / "summary.json").read_text())
        self.assertIn("moda_stats_dev", s)
        # native dev + MoDA-at-init reproduces it exactly
        native = self.root / "native"
        ev = self.run_script("eval_run.py", "--native", "--split", "dev", "--sets", str(self.sets),
                             "--out", str(native / "native_dev.csv"), *self.common)
        self.assertEqual(ev.returncode, 0, ev.stderr)
        ev = self.run_script("eval_run.py", "--moda-init", "--split", "dev", "--sets", str(self.sets),
                             "--compare", str(native / "native_dev.csv"), "--out", str(native / "moda_init_dev.csv"),
                             *self.common)
        self.assertEqual(ev.returncode, 0, ev.stdout + ev.stderr)
        # trained run reproduces its own dev scores when reloaded
        ev = self.run_script("eval_run.py", "--run", str(runs / "moda_lr0.001_s0"), "--split", "dev",
                             "--sets", str(self.sets), "--compare", str(runs / "moda_lr0.001_s0" / "eval_dev.csv"),
                             "--out", str(self.root / "reload.csv"), *self.common)
        self.assertEqual(ev.returncode, 0, ev.stdout + ev.stderr)
        # stage-1-style native reference for all windows (the summary takes test natives from it)
        import common
        windows = G.load_windows(self.sets, None)
        ref = {}
        for w in windows:
            ids, pos, tgt = common.build_window(w["tokens"], False)
            ref[w["doc_id"]] = [float(np.mean(common.token_nll(torch, self.model, ids, pos, tgt, 8,
                                                                G.SEED_BASE + 1000 * w["index"] + rep)[0][64:255]))
                                for rep in range(2)]
        G.write_per_window(self.root / "stage1.csv", ref, windows)
        # gate, test evaluations, summary
        g = self.run_script("report.py", "gate", "--runs", str(runs), "--lora", lrs["lora"], "--moda", lrs["moda"])
        self.assertIn(g.returncode, (0, 1), g.stdout + g.stderr)
        for mode in ("lora", "moda"):
            run = runs / ("%s_lr%s_s0" % (mode, lrs[mode]))
            ev = self.run_script("eval_run.py", "--run", str(run), "--split", "test", "--sets", str(self.sets),
                                 "--out", str(run / "eval_test.csv"), *self.common)
            self.assertEqual(ev.returncode, 0, ev.stderr)
        sm = self.run_script("report.py", "summarize", "--runs", str(runs), "--native", str(native),
                             "--stage1", str(self.root / "stage1.csv"), "--out", str(self.root / "summary.json"))
        self.assertEqual(sm.returncode, 0, sm.stdout + sm.stderr)
        o = json.loads((self.root / "summary.json").read_text())
        self.assertEqual(o["gate"]["complete"], True)
        if o["gate"]["pass"]:
            self.assertIn(o["status"], ("PASS", "FAIL"))
            self.assertIn("moda_minus_lora", o["test"])
        else:
            self.assertTrue(o["status"].startswith("FAIL (dev gate"))
        self.assertEqual(o["runs"]["lora_lr0.001_s0"]["trainable_params"],
                         json.loads((runs / "lora_lr0.001_s0" / "config.json").read_text())["trainable_params"])


if __name__ == "__main__":
    unittest.main()
