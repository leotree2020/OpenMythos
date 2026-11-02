"""Tiny CPU development fixtures; never loads native Parcae model weights."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import combo_model as C

LIB_SHA = "a52005f273e2ec8f467375e9ee506ae7d622cc97e0570c92863b5087014b3912"
SOURCE, LIB, ARGS = None, None, None
ATOL, RTOL = 2e-6, 2e-5


def load_library(path):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != LIB_SHA:
        raise RuntimeError("frozen MoDA library differs")
    spec = importlib.util.spec_from_file_location("combo_fixture_frozen_moda", path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


class Injection(nn.Module):
    def forward(self, x, embeds):
        return .9 * x + .1 * embeds


class Core(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(4, 4, bias=False)
    def forward(self, x):
        return x + .01 * self.linear(torch.tanh(x))


class Toy(nn.Module):
    def __init__(self, steps=32):
        super().__init__()
        self.steps, self.gradient_checkpointing = steps, False
        self.transformer = nn.ModuleDict({"core_block": nn.ModuleList([Core(), Core()]),
            "wte": nn.Embedding(11, 4), "adapter": Injection()})
        self.head = nn.Linear(4, 11, bias=False)
        self.eval()
        for p in self.parameters():
            p.requires_grad_(False)
    def initialize_state(self, embeds):
        return torch.randn_like(embeds) * .01
    def forward(self, ids, return_logits, num_steps_pair):
        assert return_logits and num_steps_pair.tolist() == [0, 32]
        self._current_input_ids = ids
        embeds = self.transformer.wte(ids)
        x = self.initialize_state(embeds)
        for _ in range(self.steps):
            x = self.transformer.adapter(x, embeds)
            for block in self.transformer.core_block:
                x = block(x)
        return {"logits": self.head(x)}


def expert_dense(expert, x):
    gated = x @ expert.w1.weight.T
    return ((gated * torch.sigmoid(gated)) * (x @ expert.w3.weight.T)) @ expert.w2.weight.T


def dense_moe(moe, x):
    flat = x.reshape(-1, x.shape[-1])
    scores = torch.softmax(flat @ moe.gate.weight.T, dim=-1, dtype=torch.float32)
    indices = torch.argsort(scores, descending=True, dim=-1)[:, :2]
    selected = torch.zeros_like(scores).scatter(1, indices, scores.gather(1, indices))
    all_experts = torch.stack([expert_dense(e, flat) for e in moe.experts], dim=1)
    result = expert_dense(moe.shared_experts, flat) + (all_experts * selected[:, :, None]).sum(1)
    return result.reshape_as(x)


def explicit(model, ids, seed, moda=None, moe=None):
    """Independent schedule without hooks; MoE computes every expert densely."""
    torch.manual_seed(seed)
    embeds = model.transformer.wte(ids)
    x = model.initialize_state(embeds)
    keys, values = [], []
    if moda is not None:
        cos, sin = moda.rope(ids.shape[1])
    for _ in range(32):
        x = .9 * x + .1 * embeds
        if moda is not None:
            x = x + moda.attn(x, keys, values, cos, sin)
        if moe is not None:
            x = x + dense_moe(moe.moe, x)
        for block in model.transformer.core_block:
            x = x + .01 * (torch.tanh(x) @ block.linear.weight.T)
        if moda is not None:
            key = (x @ moda.k_write.weight.T).reshape(1, ids.shape[1], 1, moda.head_dim).transpose(1, 2)
            value = (x @ moda.v_write.weight.T).reshape(1, ids.shape[1], 1, moda.head_dim).transpose(1, 2)
            half = key.shape[-1] // 2
            key = torch.cat((key[..., :half] * cos[..., :half] - key[..., half:] * sin[..., :half],
                key[..., half:] * cos[..., half:] + key[..., :half] * sin[..., half:]), -1)
            keys.append(key)
            values.append(value)
    return x @ model.head.weight.T


def make_moda(nonzero=True):
    result = LIB.MoDAResidual("depth", SOURCE, width=4, head_dim=2, seed=4101)
    with torch.no_grad():
        result.attn.o_proj.weight.fill_(.002 if nonzero else 0.)
    for p in result.parameters():
        p.requires_grad_(False)
    return result.eval()


def make_moe(nonzero=False):
    result = C.MoEResidual(SOURCE, width=4, seed=4101)
    if nonzero:
        with torch.no_grad():
            for expert in [result.moe.shared_experts, *result.moe.experts]:
                expert.w2.weight.copy_(torch.linspace(-.005, .005, expert.w2.weight.numel()).reshape_as(expert.w2.weight))
    return result


class ComboTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(123)
        self.model, self.ids = Toy(), torch.tensor([[1, 2, 3, 4, 5]])
        self.runner = C.NativeCombo(self.model)

    def exact(self, a, b):
        self.assertEqual(C.raw(a), C.raw(b))

    def close(self, a, b):
        torch.testing.assert_close(a, b, atol=ATOL, rtol=RTOL)

    def test_01_source_pin_and_parameter_budget(self):
        self.assertEqual(hashlib.sha256(Path(SOURCE.__file__).read_bytes()).hexdigest(), C.SOURCE_SHA256)
        moe = C.MoEResidual(SOURCE)
        self.assertEqual(sum(p.numel() for p in moe.parameters()), 187392)
        self.assertTrue(all(p.requires_grad for p in moe.parameters()))
        self.assertEqual(len(list(moe.parameters())), 16)
        self.assertIsNone(moe.moe.gate.bias)
        self.assertEqual(moe.moe.moe_balance_alpha, 0.)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.py"
            path.write_text("bad source")
            with mock.patch.object(SOURCE, "__file__", str(path)), self.assertRaisesRegex(ValueError, "source differs"):
                make_moe()

    def test_02_rng_fork_seed_pair_and_noop_outputs(self):
        before = C.raw(torch.get_rng_state())
        first, second = make_moe(), make_moe()
        self.assertEqual(before, C.raw(torch.get_rng_state()))
        self.assertEqual(C.state_hashes(first), C.state_hashes(second))
        self.assertNotEqual(C.state_hashes(first), C.state_hashes(C.MoEResidual(SOURCE, width=4, seed=4202)))
        x = torch.randn(1, 5, 4)
        self.exact(first(x), torch.zeros_like(x))

    def test_03_zero_moe_native_and_frozen_moda_identity(self):
        moda, moe = make_moda(), make_moe()
        for background in (None, moda):
            expected, a = self.runner.forward(self.ids, 5101, moda=background)
            actual, b = self.runner.forward(self.ids, 5101, moda=background, moe=moe)
            self.exact(actual, expected)
            for key in ("seed", "h0_sha256", "rng_before_sha256", "rng_after_sha256"):
                self.assertEqual(a[key], b[key])
            self.assertEqual(b["moe_calls"], 32)

    def test_04_frozen_moda_matches_old_runner_bitwise(self):
        moda = make_moda()
        expected, old = LIB.NativeFixed32(self.model).forward(self.ids, 5101, banks=moda)
        actual, obs = self.runner.forward(self.ids, 5101, moda=moda)
        self.exact(actual, expected)
        for key in old:
            self.assertEqual(obs[key], old[key])

    def test_05_dense_reference_forward_and_full_parameter_vjp(self):
        moe = make_moe(True)
        other = copy.deepcopy(moe)
        x = torch.randn(1, 7, 4, requires_grad=True)
        xx = x.detach().clone().requires_grad_()
        with torch.no_grad():
            for layer in (moe, other):
                layer.moe.gate.weight.zero_()
                layer.moe.gate.weight[:, 0] = torch.tensor([.5, .2, -.3, -.7])
            x[:, :, 0] = 1.
            xx[:, :, 0] = 1.
        actual, expected = moe(x), dense_moe(other.moe, xx)
        self.close(actual, expected)
        actual.square().sum().backward()
        expected.square().sum().backward()
        self.close(x.grad, xx.grad)
        for name, p in moe.named_parameters():
            q = dict(other.named_parameters())[name]
            self.close(torch.zeros_like(p) if p.grad is None else p.grad, torch.zeros_like(q) if q.grad is None else q.grad)
        self.assertGreater(moe.route_records[0]["top2_margin_min"], .01)
        self.assertLess(moe.route_records[0]["weight_mass_mean"], 1.)
        self.assertEqual(moe.route_records[0]["input_sha256"], C.digest(x.reshape(-1, 4)))
        self.assertEqual(moe.route_records[0]["total_assignments"], 14)
        self.assertIs(moe.route_records[0]["unique_top2_ids"], True)

    def test_06_hook_full32_matches_explicit_unroll_forward_and_gradients(self):
        moda, moe = make_moda(), make_moe(True)
        other = copy.deepcopy(moe)
        actual, _ = self.runner.forward(self.ids, 5101, moda, moe, True)
        expected = explicit(self.model, self.ids, 5101, copy.deepcopy(moda), other)
        self.close(actual, expected)
        actual.square().mean().backward()
        expected.square().mean().backward()
        for name, p in moe.named_parameters():
            q = dict(other.named_parameters())[name]
            self.close(torch.zeros_like(p) if p.grad is None else p.grad, torch.zeros_like(q) if q.grad is None else q.grad)
        self.assertTrue(all(p.grad is None for p in moda.parameters()))
        self.assertTrue(all(p.grad is None for p in self.model.parameters()))

    def test_07_initial_router_zero_later_ce_participation(self):
        moe, moda = make_moe(), make_moda()
        optimizer = torch.optim.AdamW(moe.parameters(), lr=.001, weight_decay=0., foreach=False)
        output, _ = self.runner.forward(self.ids, 5101, moda, moe, True)
        torch.nn.functional.cross_entropy(output.reshape(-1, 11), torch.tensor([2, 3, 4, 5, 6])).backward()
        self.assertEqual(int(torch.count_nonzero(moe.moe.gate.weight.grad)), 0)
        self.assertEqual(int(torch.count_nonzero(moe.moe.shared_experts.w1.weight.grad)), 0)
        self.assertGreater(float(moe.moe.shared_experts.w2.weight.grad.norm()), 0.)
        self.assertEqual(len(self.runner.depth_deltas), 32)
        self.assertTrue(all(C.gradient_record(z)["present"] and C.gradient_record(z)["finite"] for z in self.runner.depth_deltas))
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        output, _ = self.runner.forward(self.ids, 5101, moda, moe, True)
        torch.nn.functional.cross_entropy(output.reshape(-1, 11), torch.tensor([2, 3, 4, 5, 6])).backward()
        self.assertGreater(float(moe.moe.gate.weight.grad.norm()), 0.)
        self.assertGreater(float(moe.moe.shared_experts.w1.weight.grad.norm()), 0.)
        self.assertEqual({id(p) for group in optimizer.param_groups for p in group["params"]}, {id(p) for p in moe.parameters()})
        self.assertTrue(all(p.grad is None for p in moda.parameters()))

    def test_08_frozen_moda_preserves_history_autograd_and_last_write_unused(self):
        moda, moe = make_moda(), make_moe(True)
        before = C.state_hashes(moda)
        output, _ = self.runner.forward(self.ids, 5101, moda, moe, True)
        output.square().mean().backward()
        self.assertEqual([z.grad is not None for z in self.runner.depth_keys], [True] * 31 + [False])
        self.assertEqual([z.grad is not None for z in self.runner.depth_values], [True] * 31 + [False])
        self.assertTrue(any(float(z.grad.norm()) > 0 for z in self.runner.depth_values[:-1]))
        self.assertEqual(before, C.state_hashes(moda))

    def test_09_counts_histories_reset_and_no_unused_moda_branch(self):
        moe = make_moe(True)
        a, obs = self.runner.forward(self.ids, 5101, moe=moe)
        self.assertEqual(obs["core_block_calls"], [32, 32])
        self.assertEqual((obs["moda_reads"], obs["moda_writes"]), (0, 0))
        self.assertEqual(self.runner.depth_keys, [])
        self.assertEqual(len(moe.route_records), 32)
        self.assertTrue(all(sum(r["counts"]) == 10 for r in moe.route_records))
        self.assertTrue(all(r["total_assignments"] == 10 and r["unique_top2_ids"] for r in moe.route_records))
        self.assertEqual([r["depth"] for r in moe.route_records], list(range(32)))
        b, _ = self.runner.forward(self.ids, 5101, moe=moe)
        self.exact(a, b)
        self.assertEqual(len(moe.route_records), 32)
        self.runner.forward(self.ids, 5101, moda=make_moda(), moe=moe)
        self.assertEqual(self.runner.last_branch["read_lengths"], list(range(32)))
        self.assertEqual(self.runner.last_branch["write_depths"], list(range(32)))

    def test_10_future_tokens_cannot_change_prefix(self):
        moda, moe = make_moda(), make_moe(True)
        a, _ = self.runner.forward(self.ids, 5101, moda, moe)
        changed = self.ids.clone()
        changed[:, 3:] = torch.tensor([[8, 9]])
        b, _ = self.runner.forward(changed, 5101, moda, moe)
        # Changed future routes can change GEMM batch shapes. This is a
        # cross-path numeric comparison with the frozen dense/VJP tolerance;
        # identical-input, zero-output, and reload comparisons stay bitwise.
        self.close(a[:, :3], b[:, :3])
        self.assertFalse(torch.allclose(a[:, 3:], b[:, 3:], atol=ATOL, rtol=RTOL))

    def test_11_midcall_exception_cleans_every_hook_and_state(self):
        moda, moe = make_moda(), make_moe()
        original = self.model.initialize_state
        self.model._current_input_ids = "preserved sentinel"
        with mock.patch.object(moda, "write", side_effect=RuntimeError("injected failure")):
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                self.runner.forward(self.ids, 5101, moda, moe, True)
        self.assertEqual(self.model.initialize_state, original)
        self.assertEqual(self.model._current_input_ids, "preserved sentinel")
        self.assertTrue(C.no_hooks(self.model) and C.no_hooks(moda) and C.no_hooks(moe))
        self.assertEqual(moe.route_records, [])
        self.assertEqual(self.runner.calls, 0)
        self.runner.forward(self.ids, 5101, moda, moe)

    def test_12_failure_inside_gate_removes_capture(self):
        moe = make_moe()
        with mock.patch.object(moe.moe.gate, "forward", side_effect=RuntimeError("gate failure")):
            with self.assertRaisesRegex(RuntimeError, "gate failure"):
                self.runner.forward(self.ids, 5101, moe=moe)
        self.assertTrue(C.no_hooks(moe) and C.no_hooks(self.model))

    def test_13_reject_bad_modes_hooks_and_training_scope(self):
        moe, moda = make_moe(), make_moda()
        moda.attn.o_proj.weight.requires_grad_(True)
        with self.assertRaisesRegex(ValueError, "MoDA must remain frozen"):
            self.runner.forward(self.ids, 5101, moda, moe, True)
        with self.assertRaisesRegex(ValueError, "requires new MoE"):
            self.runner.forward(self.ids, 5101, training=True)
        h = self.model.transformer.adapter.register_forward_hook(lambda m, a, o: None)
        try:
            with self.assertRaisesRegex(RuntimeError, "preexisting"):
                self.runner.forward(self.ids, 5101, moe=moe)
        finally:
            h.remove()
        self.model.train()
        with self.assertRaisesRegex(ValueError, "eval"):
            self.runner.forward(self.ids, 5101, moe=moe)

    def test_14_wrong_depth_rejected_and_cleaned(self):
        for depth in (31, 33):
            model = Toy(depth)
            runner = C.NativeCombo(model)
            with self.assertRaises(RuntimeError):
                runner.forward(self.ids, 5101, moe=make_moe())
            self.assertTrue(C.no_hooks(model))
            self.assertNotIn("initialize_state", model.__dict__)
            self.assertNotIn("_current_input_ids", model.__dict__)

    def test_15_noncontiguous_moe_input_preserves_values(self):
        moe = make_moe(True)
        x = torch.randn(1, 4, 7).transpose(1, 2)
        self.assertFalse(x.is_contiguous())
        self.exact(moe(x), moe(x.contiguous()))

    def test_16_new_process_reload_exact(self):
        moda, moe = make_moda(), make_moe(True)
        expected, observer = self.runner.forward(self.ids, 5101, moda, moe)
        with tempfile.TemporaryDirectory() as td:
            state, receipt = Path(td) / "state.pt", Path(td) / "result.json"
            torch.save({"model": self.model.state_dict(), "moda": moda.state_dict(), "moe": moe.state_dict(), "ids": self.ids}, state)
            result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                "--source", ARGS.source, "--moda-library", ARGS.moda_library,
                "--reload-input", str(state), "--reload-output", str(receipt)], capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            actual = json.loads(receipt.read_text())
            self.assertEqual(actual, {"logits": C.digest(expected), "observer": observer, "routes": self.runner.route_records})

    def test_17_frozen_moe_evaluation_and_mixed_flags_rejected(self):
        moe = make_moe(True)
        expected, _ = self.runner.forward(self.ids, 5101, moe=moe)
        moe.requires_grad_(False)
        actual, _ = self.runner.forward(self.ids, 5101, moe=moe)
        self.exact(actual, expected)
        self.assertFalse(actual.requires_grad)
        with self.assertRaisesRegex(ValueError, "must train"):
            self.runner.forward(self.ids, 5101, moe=moe, training=True)
        moe.moe.gate.weight.requires_grad_(True)
        with self.assertRaisesRegex(ValueError, "uniformly"):
            self.runner.forward(self.ids, 5101, moe=moe)
        moe.requires_grad_(False)
        moe.moe.gate.weight.grad = torch.zeros_like(moe.moe.gate.weight)
        with self.assertRaisesRegex(ValueError, "no gradients"):
            self.runner.forward(self.ids, 5101, moe=moe)


def main():
    global SOURCE, LIB, ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--moda-library", required=True)
    parser.add_argument("--report")
    parser.add_argument("--reload-input")
    parser.add_argument("--reload-output")
    ARGS = parser.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    LIB = load_library(ARGS.moda_library)
    SOURCE = LIB.load_source(ARGS.source)
    if ARGS.reload_input:
        saved = torch.load(ARGS.reload_input, map_location="cpu", weights_only=True)
        model, moda, moe = Toy(), make_moda(), make_moe()
        model.load_state_dict(saved["model"], strict=True)
        moda.load_state_dict(saved["moda"], strict=True)
        moe.load_state_dict(saved["moe"], strict=True)
        runner = C.NativeCombo(model)
        logits, observer = runner.forward(saved["ids"], 5101, moda, moe)
        with open(ARGS.reload_output, "x", encoding="utf-8") as stream:
            json.dump({"logits": C.digest(logits), "observer": observer, "routes": runner.route_records}, stream, sort_keys=True)
        return 0
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ComboTests)
    ids = [test.id() for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"Purpose": "Tiny CPU development validation of isolated frozen-MoDA plus trainable source-MoE stack",
        "Environment": {"development_only": True, "python": sys.version, "executable": sys.executable,
                        "torch": torch.__version__, "device": "cpu", "threads": torch.get_num_threads()},
        "Input": {"source_sha256": C.SOURCE_SHA256, "moda_library_sha256": LIB_SHA,
                  "model_source_sha256": hashlib.sha256((ROOT / "combo_model.py").read_bytes()).hexdigest(),
                  "test_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "real_model_loads": 0, "width": 4},
        "Expected": {"tests": len(ids), "failures": 0, "errors": 0, "skipped": 0,
                     "atol": ATOL, "rtol": RTOL},
        "Actual": {"planned": len(ids), "run": result.testsRun, "test_ids": ids,
                   "failures": [{"test": t.id(), "traceback": msg} for t, msg in result.failures],
                   "errors": [{"test": t.id(), "traceback": msg} for t, msg in result.errors],
                   "skipped": result.skipped, "expected_failures": result.expectedFailures,
                   "unexpected_successes": [t.id() for t in result.unexpectedSuccesses]},
        "Status": "PASS" if result.wasSuccessful() and not result.skipped and result.testsRun == len(ids) else "FAIL"}
    if ARGS.report:
        with open(ARGS.report, "x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return 0 if report["Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
