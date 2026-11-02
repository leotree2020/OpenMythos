"""CPU developer fixtures only: never imports upstream or real weights."""
import argparse
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import unittest
from unittest import mock
from types import SimpleNamespace
import tempfile
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


lib = module("toy_loop_model", "loop_model.py")
worker = module("toy_loop_worker", "run_loop.py")


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
        self.steps = steps
        self.gradient_checkpointing = False
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


class LoopTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(123)
        self.model = Toy()
        self.runner = lib.NativeFixed32(self.model)
        self.ids = torch.tensor([[1, 2, 3, 4, 5]])

    def bank(self, arm="depth", seed=4101):
        return lib.LoopGains(arm, width=4, seed=seed, loop_dim=2)

    def test_equal_parameter_budgets_zero_initialization(self):
        for arm in ("shared", "depth"):
            bank = lib.LoopGains(arm)
            self.assertEqual(sum(p.numel() for p in bank.parameters()), 96)
            self.assertEqual(bank.expected_count(), 96)
            self.assertEqual(torch.count_nonzero(bank.gain), 0)
            self.assertEqual(list(bank.code.shape), [32, 96])
            self.assertFalse(bank.code.requires_grad)
            self.assertEqual(bank.code.dtype, torch.float32)

    def test_initialization_does_not_consume_global_rng(self):
        before = lib.raw(torch.get_rng_state())
        for arm in ("shared", "depth"):
            self.bank(arm)
        self.assertEqual(before, lib.raw(torch.get_rng_state()))

    def test_native_formula_and_concat_sin_then_cos(self):
        bank = lib.LoopGains("depth")
        frequency = 1 / (10000.0 ** (torch.arange(0, 96, 2, dtype=torch.float32) / 96))
        for depth in range(32):
            angles = depth * frequency
            expected = torch.cat([angles.sin(), angles.cos()])
            self.assertEqual(lib.raw(expected), lib.raw(bank.code[depth]))
        self.assertTrue(torch.equal(bank.code[0, :48], torch.zeros(48)))
        self.assertTrue(torch.equal(bank.code[0, 48:], torch.ones(48)))

    def test_shared_code_constant_without_normalization(self):
        bank = lib.LoopGains("shared")
        self.assertEqual(lib.raw(bank.code), lib.raw(torch.ones(32, 96)))

    def test_zero_gain_bitwise_native_all_configs(self):
        base, meta = self.runner.forward(self.ids, 5101)
        for seed in (4101, 4202):
            for arm in ("shared", "depth"):
                value, observed = self.runner.forward(self.ids, 5101, self.bank(arm, seed))
                self.assertEqual(lib.raw(value), lib.raw(base))
                self.assertEqual(meta, observed)

    def test_seed_changes_h0_not_gain_initialization(self):
        a, b = self.bank(seed=4101), self.bank(seed=4202)
        self.assertEqual(lib.state_hashes(a), lib.state_hashes(b))
        _, first = self.runner.forward(self.ids, 5101, a)
        _, second = self.runner.forward(self.ids, 5202, b)
        self.assertNotEqual(first["h0_sha256"], second["h0_sha256"])

    def test_delta_prefix_broadcast_equation(self):
        bank = self.bank()
        with torch.no_grad():
            bank.gain.copy_(torch.tensor([.25, -.5]))
        for depth in (0, 7, 31):
            expected = torch.cat([bank.gain * bank.code[depth], torch.zeros(2)])
            self.assertEqual(lib.raw(bank.delta(depth)), lib.raw(expected))
            self.assertEqual(bank.delta(depth).shape, (4,))

    def test_new_hook_prefix_invariant_under_future_token_changes(self):
        # The toy is pointwise: this tests the new hook's lack of future-token
        # dependence, not the inherited upstream attention mask itself.
        changed = self.ids.clone()
        changed[:, 3:] = torch.tensor([[8, 9]])
        for arm in ("shared", "depth"):
            bank = self.bank(arm)
            with torch.no_grad():
                bank.gain.copy_(torch.tensor([.03, -.02]))
            first, first_meta = self.runner.forward(self.ids, 5101, bank)
            second, second_meta = self.runner.forward(changed, 5101, bank)
            self.assertEqual(first_meta["h0_sha256"], second_meta["h0_sha256"])
            self.assertEqual(lib.raw(first[:, :3]), lib.raw(second[:, :3]))
            self.assertNotEqual(lib.raw(first[:, 3:]), lib.raw(second[:, 3:]))

    def test_padded_or_zero_code_gradients_do_not_count_as_gain_path(self):
        bank = self.bank()
        deltas = [torch.zeros(4, requires_grad=True) for _ in range(32)]
        for delta in deltas:
            delta.grad = torch.tensor([0., 0., 3., 4.])
        self.assertTrue(all(not bool(x.abs().max() > 0) for x in lib.depth_gain_contributions(bank, deltas)))
        deltas[0].grad = torch.tensor([1., 0., 3., 4.])
        # At t=0 the sine code is zero: raw dL/ddelta is not dL/dgain.
        self.assertEqual(lib.depth_gain_contributions(bank, deltas)[0].tolist(), [0., 0.])
        deltas[0].grad[1] = 2
        self.assertEqual(lib.depth_gain_contributions(bank, deltas)[0].tolist(), [0., 2.])

    def test_full32_gradients_zero_gain_no_shortcut(self):
        for arm in ("shared", "depth"):
            bank = self.bank(arm)
            original = lib.state_hashes(self.model)
            before = worker.per_bank_hashes(lib, bank)
            optimizer = torch.optim.AdamW(bank.parameters(), lr=.001, weight_decay=0, foreach=False)
            values, meta = self.runner.forward(self.ids, 5101, bank, training=True)
            values.square().mean().backward()
            self.assertEqual(meta["adapter_calls"], 32)
            self.assertEqual(meta["core_block_calls"], [32, 32])
            self.assertEqual(len(self.runner.depth_deltas), 32)
            self.assertTrue(all(d.grad is not None and lib.finite(d.grad) and bool(d.grad.abs().max() > 0)
                                for d in self.runner.depth_deltas))
            contributions = [d.grad[:bank.loop_dim] * bank.code[t]
                             for t, d in enumerate(self.runner.depth_deltas)]
            self.assertTrue(all(bool(x.abs().max() > 0) for x in contributions))
            # Native autograd accumulates shared-gain contributions in reverse
            # graph order; allow only ordinary FP32 summation roundoff here.
            torch.testing.assert_close(torch.stack(contributions).sum(0), bank.gain.grad,
                                       rtol=1e-6, atol=1e-7)
            self.assertTrue(any(bank.coverage(True)["gain"][0]))
            self.assertTrue(all(p.grad is None for p in self.model.parameters()))
            optimizer.step()
            self.assertNotEqual(before, worker.per_bank_hashes(lib, bank))
            self.assertEqual(original, lib.state_hashes(self.model))

    def test_last_depth_delta_gradient_matches_explicit_autograd(self):
        bank = self.bank()
        values, _ = self.runner.forward(self.ids, 5101, bank, training=True)
        loss = values.square().mean()
        expected = torch.autograd.grad(loss, self.runner.depth_deltas[-1], retain_graph=True)[0]
        # retain_grad also records autograd.grad; clear before the independent
        # backward call so this comparison does not add the same VJP twice.
        self.runner.depth_deltas[-1].grad = None
        loss.backward()
        self.assertTrue(torch.equal(expected, self.runner.depth_deltas[-1].grad))

    def test_hook_forward_and_gradient_match_explicit32_unroll(self):
        for arm in ("shared", "depth"):
            bank = self.bank(arm)
            with torch.no_grad():
                bank.gain.copy_(torch.tensor([.003, -.002]))
            actual, _ = self.runner.forward(self.ids, 5101, bank, training=True)
            actual.square().mean().backward()
            actual_gradient = bank.gain.grad.clone()
            bank.gain.grad = None
            torch.manual_seed(5101)
            embeds = self.model.transformer.wte(self.ids)
            x = self.model.initialize_state(embeds)
            frequencies = 1.0 / (10000.0 ** (torch.arange(0, 2, 2, dtype=torch.float32) / 2))
            for depth in range(32):
                angles = depth * frequencies
                code = torch.cat((angles.sin(), angles.cos())) if arm == "depth" else torch.ones(2)
                delta = torch.cat((bank.gain * code, torch.zeros(2)))
                x = self.model.transformer.adapter(x, embeds) + delta
                for block in self.model.transformer.core_block:
                    x = block(x)
            expected = self.model.head(x)
            expected.square().mean().backward()
            self.assertEqual(lib.raw(actual), lib.raw(expected))
            self.assertEqual(lib.raw(actual_gradient), lib.raw(bank.gain.grad))

    def test_second_forward_restarts_depth_counters(self):
        bank = self.bank()
        a, am = self.runner.forward(self.ids, 5101, bank)
        b, bm = self.runner.forward(self.ids, 5101, bank)
        self.assertEqual(lib.raw(a), lib.raw(b))
        self.assertEqual(am, bm)
        self.assertNotIn("initialize_state", self.model.__dict__)
        self.assertNotIn("_current_input_ids", self.model.__dict__)

    def test_existing_instance_attributes_restored(self):
        original = self.model.initialize_state
        self.model.initialize_state = original
        self.model._current_input_ids = "sentinel"
        self.runner.forward(self.ids, 5101)
        self.assertIs(self.model.initialize_state, original)
        self.assertEqual(self.model._current_input_ids, "sentinel")

    def test_wrong_depth_fails_and_removes_hooks(self):
        for count in (31, 33):
            self.model.steps = count
            with self.assertRaises(RuntimeError):
                self.runner.forward(self.ids, 5101)
            self.assertTrue(all(not m._forward_hooks and not m._forward_pre_hooks for m in self.model.modules()))
            self.assertNotIn("initialize_state", self.model.__dict__)

    def test_nonfinite_gain_fails_and_removes_hooks(self):
        bank = self.bank("shared")
        with torch.no_grad():
            bank.gain.fill_(float("nan"))
        with self.assertRaisesRegex(RuntimeError, "logits"):
            self.runner.forward(self.ids, 5101, bank)
        self.assertTrue(all(not m._forward_hooks and not m._forward_pre_hooks for m in self.model.modules()))

    def test_preexisting_hook_rejected_and_preserved(self):
        handle = self.model.transformer.adapter.register_forward_hook(lambda m, a, o: o)
        try:
            with self.assertRaisesRegex(RuntimeError, "preexisting"):
                self.runner.forward(self.ids, 5101)
            self.assertEqual(len(self.model.transformer.adapter._forward_hooks), 1)
        finally:
            handle.remove()

    def test_no_activation_checkpointing(self):
        self.model.gradient_checkpointing = True
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            lib.NativeFixed32(self.model)

    def test_train_mode_and_base_grad_rejected(self):
        self.model.train()
        with self.assertRaises(ValueError):
            lib.NativeFixed32(self.model)
        self.model.eval()
        next(self.model.parameters()).requires_grad_(True)
        with self.assertRaises(ValueError):
            lib.NativeFixed32(self.model)

    def test_checkpoint_reload_exact(self):
        bank = self.bank()
        with torch.no_grad():
            bank.gain.fill_(.002)
        before, observed = self.runner.forward(self.ids, 5101, bank)
        stream = io.BytesIO()
        torch.save(bank.state_dict(), stream)
        stream.seek(0)
        other = self.bank(seed=999)
        other.load_state_dict(torch.load(stream, weights_only=True), strict=True)
        after, current = self.runner.forward(self.ids, 5101, other)
        self.assertEqual(lib.raw(before), lib.raw(after))
        self.assertEqual(observed, current)

    def test_scoring_no_second_shift_and_first_argmax(self):
        logits = torch.tensor([[[1., 1., 0.], [0., 2., 0.], [0., 0., 3.]]])
        result = lib.score(logits, torch.tensor([0, 1, 2]), start=0)
        expected = (math.log(2 + math.exp(-1)) + math.log(1 + 2 * math.exp(-2)) + math.log(1 + 2 * math.exp(-3))) / 3
        self.assertAlmostEqual(result["nll_mean"], expected, places=12)
        self.assertEqual(result["correct"], 3)

    def test_input_dtype_dimensions_and_depth_bounds(self):
        with self.assertRaises(ValueError):
            self.runner.forward(self.ids.float(), 5101)
        for depth in (-1, 32):
            with self.assertRaises(ValueError):
                self.bank().delta(depth)
        for args in (("unknown", 4, 2), ("depth", 4, 3), ("depth", 4, 6)):
            with self.assertRaises(ValueError):
                lib.LoopGains(args[0], width=args[1], loop_dim=args[2])

    def test_frozen_data_and_disjointness(self):
        data = {k: [{"id": k + str(i), "tokens": [offset + i] * 129} for i in range(16)]
                for k, offset in (("train", 0), ("eval", 16))}
        self.assertIs(worker.validate_data(data), data)
        data["eval"][0]["tokens"] = data["train"][0]["tokens"]
        with self.assertRaises(ValueError):
            worker.validate_data(data)

    def test_training_h0_pairing_and_bounds(self):
        self.assertEqual(worker.training_h0_seed(4101, 0), 1410100)
        self.assertEqual(len({worker.training_h0_seed(s, t) for s in (4101, 4202) for t in range(32)}), 64)
        with self.assertRaises(ValueError):
            worker.training_h0_seed(4101, 32)

    def test_disk_reserve_blocks_before_write_and_never_overwrites(self):
        reserve = 256 * 1024 ** 2
        payload = b"exact frozen FP32 bytes"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logits.bin"
            with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=reserve + len(payload) - 1)):
                with self.assertRaises(worker.Stop) as caught:
                    worker.save_raw_logits(path, payload)
                self.assertEqual(caught.exception.status, "BLOCKED")
                self.assertFalse(path.exists())
            with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=reserve + len(payload))):
                worker.save_raw_logits(path, payload)
                self.assertEqual(path.read_bytes(), payload)
                with self.assertRaises(FileExistsError):
                    worker.save_raw_logits(path, payload)
                self.assertEqual(path.read_bytes(), payload)

    def test_nested_optimizer_finiteness_and_coordinate_hashes(self):
        self.assertTrue(worker.finite_tree(torch, {"state": [{"moment": torch.ones(2)}, 32]}))
        self.assertFalse(worker.finite_tree(torch, {"state": [{"moment": torch.tensor([float("inf")])}]}))
        bank = self.bank()
        before = worker.per_bank_hashes(lib, bank)
        with torch.no_grad():
            bank.gain[1] = .01
        after = worker.per_bank_hashes(lib, bank)
        self.assertEqual(before["gain"][0][0], after["gain"][0][0])
        self.assertNotEqual(before["gain"][0][1], after["gain"][0][1])

    def test_optimizer_complete_steps_and_corruption(self):
        bank = self.bank()
        optimizer = torch.optim.AdamW(bank.parameters(), lr=.001, weight_decay=0, foreach=False)
        bank.gain.grad = torch.ones_like(bank.gain)
        optimizer.step()
        state = optimizer.state_dict()
        self.assertTrue(worker.optimizer_state_valid(torch, state, steps=1))
        self.assertFalse(worker.optimizer_state_valid(torch, state, steps=32))
        next(iter(state["state"].values()))["exp_avg"].fill_(float("nan"))
        self.assertFalse(worker.optimizer_state_valid(torch, state, steps=1))


def test_ids(suite):
    result = []
    for item in suite:
        result.extend(test_ids(item) if isinstance(item, unittest.TestSuite) else [item.id()])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LoopTests)
    ids = sorted(test_ids(suite))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    actual = {"test_ids": ids, "planned": len(ids), "run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses)}
    okay = result.wasSuccessful() and result.testsRun == len(ids) and not result.skipped
    worker.save(args.report, {"Purpose": "Developer CPU toy loop-index/gradient/launch-contract checks only",
        "Environment": {"torch": str(torch.__version__), "python": sys.version}, "Input": "Random tiny fixtures, no real model/weights/data",
        "Expected": "All planned tests PASS without skips", "Actual": actual, "Status": "PASS" if okay else "FAIL",
        "failures": [(case.id(), text) for case, text in result.failures + result.errors]})
    return 0 if okay else 1


if __name__ == "__main__":
    sys.exit(main())
