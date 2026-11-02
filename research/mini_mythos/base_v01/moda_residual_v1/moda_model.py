"""Research-only differentiable MoDA residual hooks for fixed32 native Parcae.

No upstream files or base modules are replaced. This module never loads weights.
All gradients flow through all32 native recurrent calls; checkpointing is forbidden.
"""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import sys
import torch
from torch import nn
from torch.nn import functional as F

DEPTH, HEAD_DIM, THETA = 32, 16, 10000.0
SOURCE_SHA256 = "335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492"


def raw(value):
    return value.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def finite(value):
    return bool(torch.isfinite(value).all())


def state_hashes(model):
    return {name: {"shape": list(x.shape), "dtype": str(x.dtype), "sha256": digest(x)}
            for name, x in model.state_dict().items()}


def load_source(path):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("pinned OpenMythos MoDA source differs")
    spec = importlib.util.spec_from_file_location("frozen_moda_residual_source", path)
    source = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = source
    spec.loader.exec_module(source)
    return source


class MoDAResidual(nn.Module):
    """Frozen source reader/writers; only its zero-initialized output is trained."""
    def __init__(self, arm, source, width=768, seed=4101, head_dim=HEAD_DIM):
        super().__init__()
        if arm not in ("shared", "depth") or head_dim < 2 or head_dim % 2 or width < head_dim:
            raise ValueError("unsupported MoDA arm/width/head dimension")
        self.arm, self.width, self.seed, self.head_dim = arm, width, seed, head_dim
        self.rotate = source.apply_rotary_emb
        # Source constructors consume random numbers; isolate them so native
        # h0 pairing is not affected. Both arms build exactly the same features.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            cfg = source.MoDAConfig(d_model=width, n_heads_q=1, n_heads_kv=1,
                head_dim=head_dim, max_seq_len=128, rope_base=THETA, attn_dropout=0.)
            self.attn = source.MoDAAttention(cfg).float()
            with torch.no_grad():
                self.attn.o_proj.weight.zero_()
            self.k_write = nn.Linear(width, head_dim, bias=False, dtype=torch.float32)
            self.v_write = nn.Linear(width, head_dim, bias=False, dtype=torch.float32)
            self.rope = source.RotaryEmbedding(head_dim, 128, THETA).float()
        for parameter in self.parameters():
            parameter.requires_grad_(False)
        self.attn.o_proj.weight.requires_grad_(True)
        self.eval()

    def expected_count(self):
        return self.width * self.head_dim

    def trainable_parameters(self):
        return [self.attn.o_proj.weight]

    def feature_hashes(self):
        tensors = [("parameter." + n, p) for n, p in self.named_parameters() if n != "attn.o_proj.weight"]
        tensors += [("buffer." + n, p) for n, p in self.named_buffers()]
        return {name: {"shape": list(value.shape), "dtype": str(value.dtype), "sha256": digest(value)}
                for name, value in tensors}

    def read(self, x, keys, values, training=False):
        if x.shape[-1] != self.width or x.shape[1] > 128 or len(keys) != len(values):
            raise ValueError("MoDA read shape/cache mismatch")
        if any(m._forward_hooks or m._forward_pre_hooks for m in self.modules()):
            raise RuntimeError("preexisting MoDA instrumentation")
        cos, sin = self.rope(x.shape[1])
        captured = []
        handle = self.attn.o_proj.register_forward_pre_hook(lambda module, args: captured.append(args[0]))
        try:
            delta = self.attn(x, keys if self.arm == "depth" else [],
                              values if self.arm == "depth" else [], cos, sin)
        finally:
            handle.remove()
        if len(captured) != 1 or not finite(delta):
            raise RuntimeError("invalid MoDA output/capture")
        if training:
            delta.retain_grad()
        return delta, captured[0].detach()

    def write(self, state):
        batch, length, _ = state.shape
        cos, sin = self.rope(length)
        key = self.k_write(state).reshape(batch, length, 1, self.head_dim).transpose(1, 2)
        value = self.v_write(state).reshape(batch, length, 1, self.head_dim).transpose(1, 2)
        key = self.rotate(key, cos, sin)
        if not finite(key) or not finite(value):
            raise RuntimeError("nonfinite history write")
        return key, value


def depth_output_contributions(banks, deltas, features):
    """Per-depth local dL/dW_o, including the complete downstream derivative."""
    if len(deltas) != DEPTH or len(features) != DEPTH:
        raise RuntimeError("exactly32 branch outputs and features required")
    result = []
    for delta, feature in zip(deltas, features):
        if delta.grad is None or not finite(delta.grad) or not finite(feature):
            raise RuntimeError("missing/nonfinite depth branch gradient")
        if delta.shape[:-1] != feature.shape[:-1] or delta.shape[-1] != banks.width or feature.shape[-1] != banks.head_dim:
            raise RuntimeError("branch derivative/feature shape mismatch")
        result.append(delta.grad.reshape(-1, banks.width).T @ feature.reshape(-1, banks.head_dim))
    return result


class NativeFixed32:
    """Native full32 with a branch after injection and writes after core block2."""
    def __init__(self, model):
        self.model = model
        if model.gradient_checkpointing:
            raise ValueError("activation checkpointing is outside this protocol")
        if len(model.transformer.core_block) != 2:
            raise ValueError("exactly two recurrent blocks required")
        if any(p.requires_grad for p in model.parameters()) or any(m.training for m in model.modules()):
            raise ValueError("base must be frozen and eval")
        self.calls = 0
        self.depth_deltas, self.depth_features = [], []
        self.depth_keys, self.depth_values = [], []
        self.last_branch = None

    def forward(self, ids, seed, banks=None, training=False):
        if ids.device.type != "cpu" or ids.dtype != torch.long or ids.ndim != 2 or ids.shape[0] != 1 or ids.shape[1] > 128:
            raise ValueError("CPU int64 batch-one <=128 input required")
        if training and banks is None:
            raise ValueError("training requires explicit MoDA output parameters")
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
        keys, values, read_lengths, write_depths = [], [], [], []
        self.depth_deltas, self.depth_features = [], []
        self.depth_keys, self.depth_values = [], []
        self.last_branch = None
        original_init = model.initialize_state
        init_owned, init_stored = "initialize_state" in model.__dict__, model.__dict__.get("initialize_state")
        ids_owned, ids_stored = "_current_input_ids" in model.__dict__, model.__dict__.get("_current_input_ids")
        completed = False

        def observe_init(embeds):
            state = original_init(embeds)
            if state.device.type != "cpu" or state.dtype != torch.float32 or not finite(state):
                raise RuntimeError("invalid native h0")
            h0.append(digest(state))
            return state

        def adapter_hook(module, inputs, output):
            nonlocal adapter_calls
            depth = adapter_calls
            if depth >= DEPTH or counts != [depth, depth]:
                raise RuntimeError("invalid native recurrence order")
            adapter_calls += 1
            if banks is None:
                return output
            if len(keys) != depth or len(values) != depth:
                raise RuntimeError("history includes missing/current/future depth")
            read_lengths.append(depth if banks.arm == "depth" else 0)
            delta, feature = banks.read(output, keys, values, training)
            if training:
                self.depth_deltas.append(delta)
                self.depth_features.append(feature)
            return output + delta

        def core_hook(index):
            def hook(module, inputs, output):
                depth = counts[index]
                if depth >= DEPTH or adapter_calls != depth + 1:
                    raise RuntimeError("invalid core call order")
                if index == 1 and counts[0] != depth + 1:
                    raise RuntimeError("second core block precedes first")
                counts[index] += 1
                if index == 1 and banks is not None:
                    if len(keys) != depth:
                        raise RuntimeError("history write order differs")
                    key, value = banks.write(output)
                    if training:
                        if key.requires_grad:
                            key.retain_grad()
                        if value.requires_grad:
                            value.retain_grad()
                    keys.append(key)
                    values.append(value)
                    write_depths.append(depth)
            return hook

        try:
            model.initialize_state = observe_init
            handles.append(model.transformer.adapter.register_forward_hook(adapter_hook))
            for i, block in enumerate(model.transformer.core_block):
                handles.append(block.register_forward_hook(core_hook(i)))
            with torch.set_grad_enabled(training):
                result = model(ids, return_logits=True, num_steps_pair=torch.tensor([0, DEPTH], dtype=torch.long))
                logits = result["logits"]
            if counts != [DEPTH, DEPTH] or adapter_calls != DEPTH or len(h0) != 1:
                raise RuntimeError("native fixed32/h0 coverage mismatch")
            if logits is None or logits.dtype != torch.float32 or not finite(logits):
                raise RuntimeError("invalid logits")
            if training and not logits.requires_grad:
                raise RuntimeError("training graph detached")
            if banks is not None and (len(keys) != DEPTH or write_depths != list(range(DEPTH))):
                raise RuntimeError("incomplete history writes")
            self.last_branch = {"arm": banks.arm if banks is not None else "fixed32", "read_lengths": read_lengths,
                                "writer_calls": len(keys), "write_depths": write_depths}
            self.depth_keys, self.depth_values = keys, values
            self.calls += 1
            completed = True
            return logits, {"h0_sha256": h0[0], "rng_before_sha256": rng_before,
                "rng_after_sha256": digest(torch.get_rng_state()), "core_block_calls": counts,
                "adapter_calls": adapter_calls, "seed": seed}
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
            if not completed:
                self.depth_deltas, self.depth_features = [], []
                self.depth_keys, self.depth_values = [], []


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
