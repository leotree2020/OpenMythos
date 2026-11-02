"""CPU developer fixtures only: never imports upstream or real weights."""
import argparse
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import unittest
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


lib = module("toy_lora_model", "lora_model.py")
worker = module("toy_lora_worker", "run_lora.py")


class Toy(nn.Module):
    def __init__(self, steps=32):
        super().__init__()
        self.steps = steps
        self.gradient_checkpointing = False
        self.transformer = nn.ModuleDict({"core_block": nn.ModuleList([]), "wte": nn.Embedding(11, 4)})
        for _ in range(2):
            block = nn.Module()
            block.attn = nn.Module()
            block.attn.c_proj = nn.Linear(4, 4, bias=False)
            self.transformer.core_block.append(block)
        self.head = nn.Linear(4, 11, bias=False)
        self.eval()
        for p in self.parameters():
            p.requires_grad_(False)

    def initialize_state(self, embeds):
        return torch.randn_like(embeds) * 0.01

    def forward(self, ids, return_logits, num_steps_pair):
        assert return_logits and num_steps_pair.tolist() == [0, 32]
        self._current_input_ids = ids
        embeds = self.transformer.wte(ids)
        x = self.initialize_state(embeds) + embeds
        for _ in range(self.steps):
            for block in self.transformer.core_block:
                x = x + 0.01 * block.attn.c_proj(torch.tanh(x))
        return {"logits": self.head(x)}


class LoRATests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(123)
        self.model = Toy()
        self.runner = lib.NativeFixed32(self.model)
        self.ids = torch.tensor([[1, 2, 3, 4, 5]])

    def test_parameter_budgets_and_zero_B(self):
        for arm, count in (("shared", 6144), ("depth", 196608)):
            bank = lib.LoRABanks(arm)
            self.assertEqual(sum(p.numel() for p in bank.parameters()), count)
            self.assertTrue(all(torch.count_nonzero(p) == 0 for p in bank.B))

    def test_initialization_does_not_consume_global_rng(self):
        before = lib.raw(torch.get_rng_state())
        lib.LoRABanks("depth", width=4)
        self.assertEqual(before, lib.raw(torch.get_rng_state()))

    def test_shared_depth_A_initial_values_paired(self):
        for seed in (4101, 4202):
            shared = lib.LoRABanks("shared", width=4, seed=seed)
            depth = lib.LoRABanks("depth", width=4, seed=seed)
            for i in range(2):
                for j in range(32):
                    self.assertEqual(lib.raw(shared.A[i][0]), lib.raw(depth.A[i][j]))

    def test_zero_lora_bitwise_native_all_configs(self):
        base, meta = self.runner.forward(self.ids, 5101)
        for seed in (4101, 4202):
            for arm in ("shared", "depth"):
                value, current = self.runner.forward(self.ids, 5101, lib.LoRABanks(arm, 4, seed))
                self.assertEqual(lib.raw(value), lib.raw(base))
                self.assertEqual(meta, current)

    def test_depth_index_is_independent_parameter_bank(self):
        bank = lib.LoRABanks("depth", width=4)
        with torch.no_grad():
            bank.B[0][7].fill_(1)
        x = torch.ones(1, 2, 4)
        self.assertTrue(torch.count_nonzero(bank.delta(0, 6, x)) == 0)
        self.assertTrue(torch.count_nonzero(bank.delta(0, 7, x)) > 0)
        self.assertTrue(torch.count_nonzero(bank.delta(1, 7, x)) == 0)

    def test_delta_matches_explicit_linear_algebra(self):
        bank = lib.LoRABanks("depth", width=4)
        with torch.no_grad():
            bank.B[1][31].copy_(torch.arange(8).reshape(4, 2) / 10)
        x = torch.randn(2, 3, 4)
        expected = (x @ bank.A[1][31].T) @ bank.B[1][31].T
        torch.testing.assert_close(bank.delta(1, 31, x), expected, rtol=0, atol=0)

    def test_all32_banks_receive_gradients_and_update(self):
        bank = lib.LoRABanks("depth", width=4)
        base = lib.state_hashes(self.model)
        initial_banks = worker.per_bank_hashes(lib, bank)
        optimizer = torch.optim.AdamW(bank.parameters(), lr=.001, weight_decay=0, foreach=False)
        value, meta = self.runner.forward(self.ids, 5101, bank, training=True)
        value.square().mean().backward()
        coverage = bank.coverage(True)
        self.assertEqual(meta["c_proj_calls"], [32, 32])
        self.assertTrue(all(all(row) for row in coverage["B"]))
        self.assertFalse(any(any(row) for row in coverage["A"]))
        optimizer.step()
        self.assertTrue(all(all(row) for row in bank.coverage()["B"]))
        self.assertEqual(base, lib.state_hashes(self.model))
        self.assertTrue(all(p.grad is None for p in self.model.parameters()))
        optimizer.zero_grad(set_to_none=True)
        value, _ = self.runner.forward(self.ids, 5101, bank, training=True)
        value.square().mean().backward()
        self.assertTrue(all(all(row) for row in bank.coverage(True)["A"]))
        optimizer.step()
        final_banks = worker.per_bank_hashes(lib, bank)
        self.assertTrue(all(a != b for label in initial_banks for old, new in zip(initial_banks[label], final_banks[label]) for a, b in zip(old, new)))

    def test_second_forward_restarts_depth_counters(self):
        bank = lib.LoRABanks("depth", width=4)
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
        self.model.steps = 31
        with self.assertRaisesRegex(RuntimeError, "coverage"):
            self.runner.forward(self.ids, 5101)
        self.assertTrue(all(not m._forward_hooks for m in self.model.modules()))
        self.assertNotIn("initialize_state", self.model.__dict__)

    def test_nonfinite_adapter_fails_and_removes_hooks(self):
        bank = lib.LoRABanks("shared", width=4)
        with torch.no_grad():
            bank.B[0].fill_(float("nan"))
        with self.assertRaisesRegex(RuntimeError, "logits"):
            self.runner.forward(self.ids, 5101, bank)
        self.assertTrue(all(not m._forward_hooks for m in self.model.modules()))

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
        bank = lib.LoRABanks("depth", width=4)
        with torch.no_grad():
            for b in bank.B:
                b.fill_(.002)
        before, observed = self.runner.forward(self.ids, 5101, bank)
        stream = io.BytesIO()
        torch.save(bank.state_dict(), stream)
        stream.seek(0)
        other = lib.LoRABanks("depth", width=4, seed=999)
        other.load_state_dict(torch.load(stream, weights_only=True), strict=True)
        after, after_observed = self.runner.forward(self.ids, 5101, other)
        self.assertEqual(lib.raw(before), lib.raw(after))
        self.assertEqual(observed, after_observed)

    def test_scoring_no_second_shift_and_first_argmax(self):
        logits = torch.tensor([[[1., 1., 0.], [0., 2., 0.], [0., 0., 3.]]])
        result = lib.score(logits, torch.tensor([0, 1, 2]), start=0)
        expected = ((math.log(2 + math.exp(-1))) + math.log(1 + 2 * math.exp(-2)) + math.log(1 + 2 * math.exp(-3))) / 3
        self.assertAlmostEqual(result["nll_mean"], expected, places=12)
        self.assertEqual(result["correct"], 3)

    def test_input_dtype_and_bank_bounds(self):
        with self.assertRaises(ValueError):
            self.runner.forward(self.ids.float(), 5101)
        with self.assertRaises(ValueError):
            lib.LoRABanks("depth", width=4).delta(0, 32, torch.ones(1, 1, 4))

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

    def test_nested_optimizer_finiteness_and_bank_updates(self):
        self.assertTrue(worker.finite_tree(torch, {"state": [{"moment": torch.ones(2)}, 32]}))
        self.assertFalse(worker.finite_tree(torch, {"state": [{"moment": torch.tensor([float("inf")])}]}))
        banks = lib.LoRABanks("depth", width=4)
        before = worker.per_bank_hashes(lib, banks)
        with torch.no_grad():
            banks.B[1][8].fill_(.01)
        after = worker.per_bank_hashes(lib, banks)
        self.assertEqual(before["A"], after["A"])
        self.assertNotEqual(before["B"][1][8], after["B"][1][8])
        self.assertEqual(before["B"][1][:8], after["B"][1][:8])

    def test_optimizer_complete_steps_and_corruption(self):
        bank = lib.LoRABanks("depth", width=4)
        optimizer = torch.optim.AdamW(bank.parameters(), lr=.001, weight_decay=0, foreach=False)
        for p in bank.parameters():
            p.grad = torch.ones_like(p)
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
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LoRATests)
    ids = sorted(test_ids(suite))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    actual = {"test_ids": ids, "planned": len(ids), "run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses)}
    okay = result.wasSuccessful() and result.testsRun == len(ids) and not result.skipped
    worker.save(args.report, {"Purpose": "Developer CPU toy LoRA/gradient/launch-contract checks only",
        "Environment": {"torch": str(torch.__version__), "python": sys.version}, "Input": "Random tiny fixtures, no real model/weights/data",
        "Expected": "All planned tests PASS without skips", "Actual": actual, "Status": "PASS" if okay else "FAIL",
        "failures": [(case.id(), text) for case, text in result.failures + result.errors]})
    return 0 if okay else 1


if __name__ == "__main__":
    sys.exit(main())
