"""Research-only differentiable loop-index hooks for fixed32 native Parcae.

No upstream files or base modules are replaced. This module never loads weights.
All gradients flow through all32 native recurrent calls; checkpointing is forbidden.
"""
from __future__ import annotations
import hashlib
import math
import torch
from torch import nn
from torch.nn import functional as F

DEPTH, LOOP_DIM, THETA = 32, 96, 10000.0


def raw(value):
    return value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def finite(value):
    return bool(torch.isfinite(value).all())


def state_hashes(model):
    return {name: {"shape": list(x.shape), "dtype": str(x.dtype), "sha256": digest(x)}
            for name, x in model.state_dict().items()}


class LoopGains(nn.Module):
    """Matched 96 gains: fixed sinusoidal depth code versus constant ones."""
    def __init__(self, arm, width=768, seed=4101, loop_dim=LOOP_DIM):
        super().__init__()
        if arm not in ("shared", "depth") or loop_dim < 2 or loop_dim % 2 or width < loop_dim:
            raise ValueError("unsupported loop arm/width/code dimension")
        self.arm, self.width, self.seed, self.loop_dim = arm, width, seed, loop_dim
        self.gain = nn.Parameter(torch.zeros(loop_dim, dtype=torch.float32))
        frequencies = 1.0 / (THETA ** (torch.arange(0, loop_dim, 2, dtype=torch.float32) / loop_dim))
        codes = []
        for depth in range(DEPTH):
            angles = depth * frequencies
            codes.append(torch.cat((angles.sin(), angles.cos())))
        code = torch.stack(codes) if arm == "depth" else torch.ones(DEPTH, loop_dim, dtype=torch.float32)
        self.register_buffer("code", code)

    def delta(self, depth):
        if not 0 <= depth < DEPTH:
            raise ValueError("invalid depth")
        return F.pad(self.gain * self.code[depth], (0, self.width - self.loop_dim))

    def expected_count(self):
        return self.loop_dim

    def coverage(self, gradients=False):
        value = self.gain.grad if gradients else self.gain.detach()
        if value is None or not finite(value):
            raise RuntimeError("missing/nonfinite loop gain gradient or value")
        return {"gain": [[bool(x != 0) for x in value]]}


def depth_gain_contributions(banks, deltas):
    """Per-depth dL/dgain before summing depths, excluding padded channels."""
    if len(deltas) != DEPTH:
        raise RuntimeError("exactly32 delta gradients required")
    result = []
    for depth, delta in enumerate(deltas):
        if delta.grad is None or tuple(delta.grad.shape) != (banks.width,) or not finite(delta.grad):
            raise RuntimeError("missing/nonfinite/wrong-shape depth delta gradient")
        result.append(delta.grad[:banks.loop_dim] * banks.code[depth])
    return result


class NativeFixed32:
    """One observer wrapper per model; hooks exist only during each forward.

    Counter values only select parameters during the actual native forward.
    Backward uses the saved tensor graph, never a replay or mutable depth value.
    """
    def __init__(self, model):
        self.model = model
        if model.gradient_checkpointing:
            raise ValueError("activation checkpointing is outside this protocol")
        if len(model.transformer.core_block) != 2:
            raise ValueError("exactly two recurrent blocks required")
        if any(p.requires_grad for p in model.parameters()):
            raise ValueError("base parameters must all be frozen")
        if any(m.training for m in model.modules()):
            raise ValueError("base model must stay in eval mode")
        self.calls = 0
        self.depth_deltas = []

    def forward(self, ids, seed, banks=None, training=False):
        if ids.device.type != "cpu" or ids.dtype != torch.long or ids.ndim != 2 or ids.shape[0] != 1:
            raise ValueError("CPU int64 batch-one input required")
        if training and banks is None:
            raise ValueError("training requires explicit loop gain parameters")
        if torch.is_autocast_enabled("cpu") or torch.is_autocast_enabled("cuda"):
            raise ValueError("autocast forbidden")
        model = self.model
        if model.gradient_checkpointing or any(m.training for m in model.modules()):
            raise ValueError("native mode changed")
        if any(p.requires_grad or p.grad is not None for p in model.parameters()):
            raise ValueError("base gradient enabled/present")
        if any(m._forward_hooks or m._forward_pre_hooks for m in model.modules()):
            raise RuntimeError("preexisting model instrumentation")
        torch.manual_seed(seed)
        rng_before = digest(torch.get_rng_state())
        counts, h0, handles = [0, 0], [], []
        adapter_calls = 0
        self.depth_deltas = []
        original_init = model.initialize_state
        init_owned = "initialize_state" in model.__dict__
        init_stored = model.__dict__.get("initialize_state")
        ids_owned = "_current_input_ids" in model.__dict__
        ids_stored = model.__dict__.get("_current_input_ids")

        def observe_init(embeds):
            state = original_init(embeds)
            if state.device.type != "cpu" or state.dtype != torch.float32 or not finite(state):
                raise RuntimeError("invalid native h0")
            h0.append(digest(state))
            return state

        def adapter_hook(module, inputs, output):
            nonlocal adapter_calls
            depth = adapter_calls
            if depth >= DEPTH:
                raise RuntimeError("too many native recurrence calls")
            adapter_calls += 1
            if banks is None:
                return output
            if output.shape[-1] != banks.width or output.dtype != torch.float32 or output.device.type != "cpu":
                raise RuntimeError("loop adapter output mismatch")
            delta = banks.delta(depth)
            if training:
                delta.retain_grad()
                self.depth_deltas.append(delta)
            return output + delta

        def core_observer(block):
            def observe(module, inputs):
                counts[block] += 1
            return observe

        try:
            model.initialize_state = observe_init
            adapter = model.transformer.adapter
            if adapter._forward_hooks or adapter._forward_pre_hooks:
                raise RuntimeError("preexisting adapter instrumentation")
            handles.append(adapter.register_forward_hook(adapter_hook))
            for i, block in enumerate(model.transformer.core_block):
                if block._forward_hooks or block._forward_pre_hooks:
                    raise RuntimeError("preexisting recurrent instrumentation")
                handles.append(block.register_forward_pre_hook(core_observer(i)))
            with torch.set_grad_enabled(training):
                result = model(ids, return_logits=True, num_steps_pair=torch.tensor([0, DEPTH], dtype=torch.long))
                logits = result["logits"]
            if counts != [DEPTH, DEPTH] or adapter_calls != DEPTH or len(h0) != 1:
                raise RuntimeError("native fixed32/h0 coverage mismatch")
            if logits is None or logits.dtype != torch.float32 or not finite(logits):
                raise RuntimeError("invalid logits")
            if training and not logits.requires_grad:
                raise RuntimeError("training graph detached")
            self.calls += 1
            return logits, {"h0_sha256": h0[0], "rng_before_sha256": rng_before,
                            "rng_after_sha256": digest(torch.get_rng_state()),
                            "core_block_calls": counts, "adapter_calls": adapter_calls, "seed": seed}
        finally:
            for handle in handles:
                handle.remove()
            if init_owned:
                model.initialize_state = init_stored
            else:
                delattr(model, "initialize_state")
            if ids_owned:
                model._current_input_ids = ids_stored
            elif "_current_input_ids" in model.__dict__:
                delattr(model, "_current_input_ids")


def score(logits, targets, start=64):
    if logits.ndim != 3 or logits.shape[0] != 1 or targets.ndim != 1 or logits.shape[1] != len(targets):
        raise ValueError("next-token target alignment differs")
    values = logits[0, start:].detach().double()
    target = targets[start:]
    peak = values.max(dim=-1).values
    gold = values.gather(1, target[:, None]).squeeze(1)
    nll = (peak - gold) + torch.log(torch.exp(values - peak[:, None]).sum(-1))
    if not finite(nll):
        raise RuntimeError("nonfinite NLL")
    return {"nll_mean": float(nll.mean()), "nll_sum": float(nll.sum()),
            "correct": int((values.argmax(-1) == target).sum()), "target_count": len(target)}
