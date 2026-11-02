"""Synthetic + random native tiny developer tests; never load saved weights.

MYTHOS_PARCAE_UPSTREAM selects the readonly pinned source. The external runner
owns runtime setup/evidence. Direct execution sets one CPU thread/determinism.
Toy tests deliberately exercise private _run; public APIs fail closed to native.
"""
from __future__ import annotations

import inspect
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adaptive_depth as ad


def same_bytes(left, right):
    return left.shape == right.shape and left.dtype == right.dtype and ad.tensor_bytes(left) == ad.tensor_bytes(right)


class Block(nn.Module):
    def __init__(self, mutate=False, error=False, random=False):
        super().__init__()
        self.mutate, self.error, self.random = mutate, error, random

    def forward(self, x, freqs=None, mask=None, **kwargs):
        if self.error:
            raise RuntimeError("injected coda exception")
        if self.random:
            torch.rand(1)
        if self.mutate:
            x.add_(100)
        return x


class ToyHead(nn.Module):
    def __init__(self, stable=True, nonfinite=False):
        super().__init__()
        self.stable, self.nonfinite = stable, nonfinite

    def forward(self, x):
        logits = torch.zeros((*x.shape[:-1], 2), dtype=torch.float32)
        if not self.stable:
            logits[..., 0] = x[..., 0] - 12.0
        if self.nonfinite:
            logits[..., 0] = float("nan")
        return logits


class Toy(nn.Module):
    """No attention/scientific claim: controlled recurrence and readout fixtures."""
    def __init__(self, stable=True, mutate=False, error=False, random=False, nonfinite=False):
        super().__init__()
        self.config = SimpleNamespace(block_size=16, padded_vocab_size=2, prelude_norm=True,
                                      n_layers_in_prelude=2, n_layers_in_recurrent_block=2,
                                      init=SimpleNamespace(logit_scale=1.0))
        self.transformer = nn.ModuleDict({
            "wte": nn.Embedding(2, 2), "prelude": nn.ModuleList([Block(), Block()]),
            "ln_prelude": nn.Identity(), "core_block": nn.ModuleList([Block(), Block()]),
            "C": nn.Identity(), "coda": nn.ModuleList([Block(mutate, error, random), Block()]),
            "ln_f": nn.Identity()})
        self.value_embeds = nn.ModuleDict()
        self.lm_head = ToyHead(stable, nonfinite)
        self.register_buffer("freqs_cis", torch.ones(1, 16, 1, 1, 2))
        self.emb_scale = 1
        self.steps, self.totals = [], []
        self.eval()

    def initialize_state(self, embeds):
        return torch.zeros_like(embeds)

    def update_recurrent_state(self, x, embeds, freqs, mask, step, total):
        self.steps.append(int(step))
        self.totals.append(int(total))
        return x + 1


class PolicyTests(unittest.TestCase):
    def test_policy_scalar_reference(self):
        """FP64 TV agrees with an independent Python scalar softmax reference."""
        left = torch.tensor([[2.0, -1.0, 0.25]], dtype=torch.float32)
        right = torch.tensor([[1.5, -0.5, 0.75]], dtype=torch.float32)
        def scalar(values):
            weights = [math.exp(v - max(values)) for v in values]
            return [w / math.fsum(weights) for w in weights]
        p, q = scalar(left[0].tolist()), scalar(right[0].tolist())
        expected = 0.5 * math.fsum(abs(a - b) for a, b in zip(p, q))
        self.assertAlmostEqual(ad.total_variation(left, right), expected, delta=1e-15)

    def test_zero_shift_threshold_and_no_rng(self):
        """Zero TV, finite additive shift and inclusive frozen boundary are explicit."""
        x = torch.tensor([[2.0, -1.0, 0.25]], dtype=torch.float32)
        rng = ad.tensor_bytes(torch.get_rng_state())
        self.assertEqual(ad.total_variation(x, x.clone()), 0.0)
        self.assertLessEqual(ad.total_variation(x, x + 8), 1e-15)
        self.assertEqual(ad.depth_from_tv(0.01), 16)
        self.assertEqual(ad.depth_from_tv(math.nextafter(0.01, math.inf)), 32)
        self.assertEqual(ad.tensor_bytes(torch.get_rng_state()), rng)

    def test_policy_rejects_invalid(self):
        """Invalid shape, dtype, nonfinite values and out-of-domain TV fail closed."""
        good = torch.zeros(1, 2)
        for bad in (torch.zeros(2), torch.zeros(2, 2), torch.zeros(1, 1), good.double(),
                    torch.tensor([[float("nan"), 0]]), torch.tensor([[float("inf"), 0]]),
                    torch.zeros(1, 2, requires_grad=True)):
            with self.subTest(shape=tuple(bad.shape), dtype=str(bad.dtype)):
                with self.assertRaises(ValueError):
                    ad.total_variation(bad, good)
        with self.assertRaises(ValueError):
            ad.total_variation(good, torch.zeros(1, 3))
        for value in (-1, 1.1, float("nan"), float("inf"), True, "0.01"):
            with self.assertRaises(ValueError):
                ad.depth_from_tv(value)


class ToyExecutionTests(unittest.TestCase):
    def setUp(self):
        self.ids = torch.tensor([[0, 1, 0]], dtype=torch.long)

    def test_stable_true_early_exit_and_counts(self):
        """Stable fixture executes exactly 16 updates, 2 readouts, and one policy."""
        m = Toy()
        result = ad._run(m, self.ids, "adaptive")
        self.assertEqual(result.selected_depth, 16)
        self.assertEqual(m.steps, list(range(16)))
        self.assertEqual(m.totals, [32] * 16)
        self.assertEqual(result.counts["h0_calls"], 1)
        self.assertEqual(result.counts["prelude_block_calls"], 2)
        self.assertEqual(result.counts["total_block_calls"], 38)
        self.assertEqual(result.counts["projection_calls"], 2)
        self.assertEqual(result.counts["head_calls"], 2)
        self.assertEqual(result.counts["policy_evaluations"], 1)
        self.assertEqual(result.counts["policy_softmax_calls"], 2)
        self.assertEqual(result.counts["policy_vocabulary_elements"], 4)
        self.assertFalse(hasattr(m, "_current_input_ids"))

    def test_unstable_continues_without_restart(self):
        """Unstable fixture continues the same state to 32 with 3 readouts."""
        m = Toy(stable=False)
        result = ad._run(m, self.ids, "adaptive")
        self.assertEqual(result.selected_depth, 32)
        self.assertGreater(result.tv_8_16, ad.TV_THRESHOLD)
        self.assertEqual(m.steps, list(range(32)))
        self.assertEqual(result.counts["h0_calls"], 1)
        self.assertEqual(result.counts["total_block_calls"], 72)
        self.assertEqual(result.counts["head_calls"], 3)
        self.assertEqual(result.counts["readouts"], 3)

    def test_stable_can_be_wrong(self):
        """A synthetic wrong prediction can be stable: early exit is no quality proof."""
        result = ad._run(Toy(stable=True), self.ids, "adaptive")
        synthetic_expected_token = 1  # Test oracle only; never supplied to controller.
        self.assertEqual(result.selected_depth, 16)
        self.assertEqual(result.tv_8_16, 0.0)
        self.assertNotEqual(int(result.last_logits.argmax(-1).item()), synthetic_expected_token)

    def test_fixed_budgets_and_invalid_budget(self):
        """Fixed controls perform exactly the requested budget and only one readout."""
        for depth, total in ((8, 20), (16, 36), (32, 68)):
            m = Toy()
            r = ad._run(m, self.ids, "fixed", depth)
            self.assertEqual(m.steps, list(range(depth)))
            self.assertEqual(r.counts["total_block_calls"], total)
            self.assertEqual(r.counts["readouts"], 1)
            self.assertEqual(r.counts["policy_evaluations"], 0)
            self.assertIsNone(r.tv_8_16)
        for depth in (0, 7, 33, True, 16.0):
            m = Toy()
            with self.assertRaises(ValueError):
                ad._run(m, self.ids, "fixed", depth)
            self.assertEqual(m.steps, [])

    def test_readout_inplace_cannot_contaminate_state(self):
        """Even an in-place toy coda cannot corrupt the resumed recurrence."""
        plain = ad._run(Toy(stable=False), self.ids, "checkpoints")
        mutated = ad._run(Toy(stable=False, mutate=True), self.ids, "checkpoints")
        self.assertEqual(plain.recurrent_state_sha256, mutated.recurrent_state_sha256)
        self.assertEqual(mutated.counts["recurrent_updates"], 32)
        self.assertNotEqual(ad.tensor_bytes(plain.last_logits), ad.tensor_bytes(mutated.last_logits))

    def test_restores_attribute_on_success_exception_and_rng_failure(self):
        """Temporary native input IDs restore their original identity on every exit."""
        for kwargs in ({}, {"error": True}, {"random": True}, {"nonfinite": True}):
            m = Toy(**kwargs)
            previous = object()
            m._current_input_ids = previous
            before = self.ids.clone()
            if kwargs:
                with self.assertRaises((ValueError, RuntimeError)):
                    ad._run(m, self.ids, "adaptive")
            else:
                ad._run(m, self.ids, "adaptive")
            self.assertIs(m._current_input_ids, previous)
            self.assertTrue(same_bytes(self.ids, before))
        m = Toy(error=True)
        with self.assertRaises(RuntimeError):
            ad._run(m, self.ids, "adaptive")
        self.assertFalse(hasattr(m, "_current_input_ids"))

    def test_input_and_no_labels_interface(self):
        """Batch, context, dtype, token bounds fail; labels/cache/masks are absent."""
        invalid = (torch.zeros(2, 3, dtype=torch.long), torch.zeros(1, 0, dtype=torch.long),
                   torch.zeros(1, 17, dtype=torch.long), self.ids.float(),
                   torch.tensor([[-1]]), torch.tensor([[2]]), self.ids[0])
        for ids in invalid:
            m = Toy()
            with self.assertRaises(ValueError):
                ad._run(m, ids, "adaptive")
            self.assertEqual(m.steps, [])
        for function in (ad.adaptive_next_token, ad.fixed_next_token, ad.diagnostic_checkpoints):
            params = inspect.signature(function).parameters
            self.assertFalse(set(params) & {"labels", "targets", "attention_mask", "position_ids", "past_key_values"})
            self.assertFalse(any(p.kind == p.VAR_KEYWORD for p in params.values()))
        with self.assertRaises(TypeError):
            ad.adaptive_next_token(Toy(), self.ids, labels=self.ids)


class NativeTinyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        upstream = Path(os.environ.get("MYTHOS_PARCAE_UPSTREAM", str(Path(__file__).resolve().parents[2] / "mythos_parcae_pinned")))
        sys.path.insert(0, str(upstream.resolve()))
        try:
            from parcae_lm.models.parcae import Parcae, ParcaeConfig
            from receval.models.parcae import ModelingParcae
        except ImportError as exc:
            raise unittest.SkipTest(f"native tiny NOT TESTED: unavailable native dependencies: {exc}")
        cls.Parcae, cls.Config, cls.Modeling = Parcae, ParcaeConfig, ModelingParcae

    def setUp(self):
        torch.manual_seed(12345)
        config = self.Config.from_name("parcae-small-140m", block_size=16, vocab_size=64,
                                      padded_vocab_size=64, padding_multiple=1, n_embd=32,
                                      intermediate_size=128, recurrent_embedding_dimension=32,
                                      recurrent_intermediation_embedding_dimension=128,
                                      num_attention_heads=2, num_key_value_heads=2,
                                      init_strategy="scaled", init_orthogonal=True)
        self.model = self.Modeling(config).eval()
        self.ids = torch.tensor([[1, 4, 3, 9, 2]], dtype=torch.long)
        self.rng = torch.get_rng_state().clone()

    def observe_h0(self, call):
        code = self.model.initialize_state.__func__.__code__
        records = []
        previous_profile = sys.getprofile()
        self.assertIsNone(previous_profile, "fixture requires no existing profiler")
        def profile(frame, event, value):
            if event == "return" and frame.f_code is code and frame.f_locals.get("self") is self.model:
                rng = ad.tensor_bytes(torch.get_rng_state())
                records.append((ad.tensor_sha256(value), ad.tensor_sha256(torch.get_rng_state())))
                self.assertEqual(ad.tensor_bytes(torch.get_rng_state()), rng)
        try:
            sys.setprofile(profile)
            result = call()
        finally:
            sys.setprofile(previous_profile)
        self.assertEqual(len(records), 1)
        return result, records[0]

    def native(self, depth):
        torch.set_rng_state(self.rng.clone())
        with torch.no_grad():
            out, self.last_native_h0 = self.observe_h0(
                lambda: self.model(self.ids, return_logits=True, num_steps_pair=torch.tensor([depth, 0])))
        return out["logits"][:, -1, :].clone(), ad.tensor_bytes(torch.get_rng_state())

    def test_fixed_and_resumed_match_native_bytes_all_depths(self):
        """Native random tiny: fixed/resumed logits at 8/16/32 match native bytes."""
        torch.set_rng_state(self.rng.clone())
        observed, observed_h0 = self.observe_h0(lambda: ad.diagnostic_checkpoints(self.model, self.ids))
        self.assertEqual(observed.h0_sha256, observed_h0[0])
        self.assertEqual(len(set(observed.recurrent_state_sha256.values())), 3)
        self.assertEqual(len({ad.tensor_bytes(x) for x in observed.checkpoint_logits.values()}), 3)
        for depth in ad.DEPTHS:
            expected, rng_after = self.native(depth)
            self.assertEqual(self.last_native_h0, observed_h0)
            torch.set_rng_state(self.rng.clone())
            fixed = ad.fixed_next_token(self.model, self.ids, depth=depth)
            self.assertTrue(same_bytes(expected, observed.checkpoint_logits[depth]))
            self.assertTrue(same_bytes(expected, fixed.last_logits))
            self.assertEqual(fixed.h0_sha256, observed.h0_sha256)
            self.assertEqual(fixed.recurrent_state_sha256[depth], observed.recurrent_state_sha256[depth])
            self.assertEqual(ad.tensor_bytes(torch.get_rng_state()), rng_after)

    def test_adaptive_native_identity_counts_and_immutability(self):
        """Selected native output is exact; actual hooks verify call counts/state preservation."""
        states = {k: ad.tensor_bytes(v) for k, v in self.model.state_dict().items()}
        ids_before = ad.tensor_bytes(self.ids)
        previous = object()
        self.model._current_input_ids = previous
        actual = dict(prelude=0, core=0, coda=0, projection=0, head=0)
        handles = []
        def hook(name):
            def observe(module, args, out):
                actual[name] += 1
            return observe
        for key, mods in (("prelude", self.model.transformer.prelude),
                          ("core", self.model.transformer.core_block),
                          ("coda", self.model.transformer.coda),
                          ("projection", [self.model.transformer.C]), ("head", [self.model.lm_head])):
            handles.extend(m.register_forward_hook(hook(key)) for m in mods)
        try:
            torch.set_rng_state(self.rng.clone())
            out = ad.adaptive_next_token(self.model, self.ids)
        finally:
            for handle in handles:
                handle.remove()
        self.assertIs(self.model._current_input_ids, previous)
        self.assertEqual(states, {k: ad.tensor_bytes(v) for k, v in self.model.state_dict().items()})
        self.assertEqual(ad.tensor_bytes(self.ids), ids_before)
        for key, count_key in (("prelude", "prelude_block_calls"), ("core", "core_block_calls"),
                               ("coda", "coda_block_calls"), ("projection", "projection_calls"), ("head", "head_calls")):
            self.assertEqual(actual[key], out.counts[count_key])
        expected, _ = self.native(out.selected_depth)
        self.assertTrue(same_bytes(expected, out.last_logits))
        self.assertFalse(out.last_logits.requires_grad)
        self.assertIn(out.selected_depth, (16, 32))

    def test_native_prefix_isolation_and_repeat(self):
        """Only supplied prefix is scored; separate calls restart h0 and repeat exactly."""
        for length in (1, 3, 5):
            prefix = self.ids[:, :length].clone()
            torch.set_rng_state(self.rng.clone())
            one = ad.adaptive_next_token(self.model, prefix)
            torch.set_rng_state(self.rng.clone())
            two = ad.adaptive_next_token(self.model, prefix)
            self.assertTrue(same_bytes(one.last_logits, two.last_logits))
            self.assertEqual(one.h0_sha256, two.h0_sha256)
            self.assertEqual(one.counts["h0_calls"], 1)
            torch.set_rng_state(self.rng.clone())
            with torch.no_grad():
                native = self.model(prefix, return_logits=True,
                                    num_steps_pair=torch.tensor([one.selected_depth, 0]))["logits"][:, -1, :]
            self.assertTrue(same_bytes(one.last_logits, native))
            self.assertEqual(tuple(one.last_logits.shape), (1, 64))

    def test_native_causal_suffix_control(self):
        """Same-length future suffix changes cannot affect earlier checkpoint logits."""
        mutated = self.ids.clone()
        mutated[:, 3:] = (mutated[:, 3:] + 1) % 64
        def captured(ids):
            outputs = []
            def hook(module, args, value):
                outputs.append(value.detach().clone())
            handle = self.model.lm_head.register_forward_hook(hook)
            try:
                torch.set_rng_state(self.rng.clone())
                result = ad.diagnostic_checkpoints(self.model, ids)
            finally:
                handle.remove()
            self.assertEqual(len(outputs), 3)
            return result, outputs
        original, before = captured(self.ids)
        changed, after = captured(mutated)
        self.assertEqual(original.h0_sha256, changed.h0_sha256)
        for x, y in zip(before, after):
            self.assertTrue(same_bytes(x[:, :3, :], y[:, :3, :]))
        self.assertTrue(any(not same_bytes(x[:, 3:, :], y[:, 3:, :]) for x, y in zip(before, after)))

    def test_native_fail_closed_configuration_and_autocast(self):
        """Native public guard rejects training, non-FP32, fused/config and autocast paths."""
        self.model.train()
        with self.assertRaises(ValueError):
            ad.adaptive_next_token(self.model, self.ids)
        self.model.eval()
        for name, value in (("use_fused_head", "full-triton"), ("state_init", "zero"),
                            ("mean_recurrence", 16), ("recurrent_iteration_method", "per-token")):
            previous = getattr(self.model.config, name)
            setattr(self.model.config, name, value)
            try:
                with self.assertRaises(ValueError):
                    ad.adaptive_next_token(self.model, self.ids)
            finally:
                setattr(self.model.config, name, previous)
        with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
            with self.assertRaises(ValueError):
                ad.adaptive_next_token(self.model, self.ids)
        self.model.double()
        with self.assertRaises(ValueError):
            ad.adaptive_next_token(self.model, self.ids)


if __name__ == "__main__":
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    unittest.main(verbosity=2)
