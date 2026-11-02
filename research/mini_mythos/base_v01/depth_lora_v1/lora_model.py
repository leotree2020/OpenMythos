"""Research-only differentiable LoRA hooks for fixed32 native Parcae.

No upstream files or base modules are replaced. This module never loads weights.
All gradients flow through all32 native recurrent calls; checkpointing is forbidden.
"""
from __future__ import annotations
import hashlib
import math
import torch
from torch import nn
from torch.nn import functional as F

DEPTH, RANK, ALPHA = 32, 2, 2


def raw(value):
    return value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def finite(value):
    return bool(torch.isfinite(value).all())


def state_hashes(model):
    return {name: {"shape": list(x.shape), "dtype": str(x.dtype), "sha256": digest(x)}
            for name, x in model.state_dict().items()}


class LoRABanks(nn.Module):
    def __init__(self, arm, width=768, seed=4101):
        super().__init__()
        if arm not in ("shared", "depth") or width < 2:
            raise ValueError("unsupported LoRA arm/width")
        self.arm, self.width, self.seed = arm, width, seed
        self.banks = 1 if arm == "shared" else DEPTH
        generator = torch.Generator(device="cpu").manual_seed(seed)
        self.A, self.B = nn.ParameterList(), nn.ParameterList()
        for _ in range(2):
            # Both arms start from exactly the same per-block A; depth banks
            # are equal initially, then independently learned. No global RNG use.
            a = torch.empty(RANK, width, dtype=torch.float32)
            a.uniform_(-1 / math.sqrt(width), 1 / math.sqrt(width), generator=generator)
            self.A.append(nn.Parameter(a.repeat(self.banks, 1, 1)))
            self.B.append(nn.Parameter(torch.zeros(self.banks, width, RANK)))

    def delta(self, block, depth, x):
        if block not in (0, 1) or not 0 <= depth < DEPTH:
            raise ValueError("invalid block/depth")
        bank = 0 if self.arm == "shared" else depth
        return F.linear(F.linear(x, self.A[block][bank]), self.B[block][bank]) * (ALPHA / RANK)

    def expected_count(self):
        return 2 * self.banks * 2 * RANK * self.width

    def coverage(self, gradients=False):
        result = {}
        for label, parameters in (("A", self.A), ("B", self.B)):
            result[label] = []
            for p in parameters:
                value = p.grad if gradients else p.detach()
                if value is None:
                    raise RuntimeError("missing LoRA gradient")
                if not finite(value):
                    raise RuntimeError("nonfinite LoRA value")
                result[label].append([bool(x.abs().max() > 0) for x in value])
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

    def forward(self, ids, seed, banks=None, training=False):
        if ids.device.type != "cpu" or ids.dtype != torch.long or ids.ndim != 2 or ids.shape[0] != 1:
            raise ValueError("CPU int64 batch-one input required")
        if training and banks is None:
            raise ValueError("training requires explicit LoRA parameters")
        if torch.is_autocast_enabled("cpu") or torch.is_autocast_enabled("cuda"):
            raise ValueError("autocast forbidden")
        model = self.model
        if model.gradient_checkpointing or any(m.training for m in model.modules()):
            raise ValueError("native mode changed")
        if any(p.requires_grad or p.grad is not None for p in model.parameters()):
            raise ValueError("base gradient enabled/present")
        torch.manual_seed(seed)
        rng_before = digest(torch.get_rng_state())
        counts, h0, handles = [0, 0], [], []
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

        def make_hook(block):
            def hook(module, inputs, output):
                depth = counts[block]
                if depth >= DEPTH:
                    raise RuntimeError("too many native recurrence calls")
                counts[block] += 1
                if banks is None:
                    return output
                return output + banks.delta(block, depth, inputs[0])
            return hook

        try:
            model.initialize_state = observe_init
            for i, block in enumerate(model.transformer.core_block):
                projection = block.attn.c_proj
                if projection._forward_hooks or projection._forward_pre_hooks:
                    raise RuntimeError("preexisting projection instrumentation")
                handles.append(projection.register_forward_hook(make_hook(i)))
            with torch.set_grad_enabled(training):
                result = model(ids, return_logits=True, num_steps_pair=torch.tensor([0, DEPTH], dtype=torch.long))
                logits = result["logits"]
            if counts != [DEPTH, DEPTH] or len(h0) != 1:
                raise RuntimeError("native fixed32/h0 coverage mismatch")
            if logits is None or logits.dtype != torch.float32 or not finite(logits):
                raise RuntimeError("invalid logits")
            if training and not logits.requires_grad:
                raise RuntimeError("training graph detached")
            self.calls += 1
            return logits, {"h0_sha256": h0[0], "rng_before_sha256": rng_before,
                            "rng_after_sha256": digest(torch.get_rng_state()),
                            "c_proj_calls": counts, "seed": seed}
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
