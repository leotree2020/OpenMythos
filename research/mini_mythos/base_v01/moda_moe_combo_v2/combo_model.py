"""Isolated fixed32 native Parcae + frozen MoDA + source sparse MoE hooks.

No weights are loaded here, and no native module is replaced. The new MoE
parameters alone are trainable. This residual stack is not the full MoDABlock.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import torch
from torch import nn

DEPTH = 32
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


def no_hooks(module):
    return not any(m._forward_hooks or m._forward_pre_hooks for m in module.modules())


def gradient_record(value):
    grad = value.grad
    return {"present": grad is not None,
            "finite": finite(grad) if grad is not None else None,
            "norm": float(grad.detach().double().norm()) if grad is not None else None,
            "nonzero": int(torch.count_nonzero(grad)) if grad is not None else None}


class MoEResidual(nn.Module):
    """One shared + four routed SwiGLU experts, top2, hidden16, alpha=0.

    All 187392 parameters at width768 train, with five zero output matrices.
    In particular initial task gradients of router and w1/w3 are zero by
    construction; later participation must be measured, not assumed.
    """
    def __init__(self, source, width=768, seed=4101):
        super().__init__()
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise ValueError("positive integer width required")
        path = Path(source.__file__)
        if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("pinned OpenMythos source differs")
        self.width, self.seed = width, seed
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            cfg = source.MoDAConfig(d_model=width, n_shared_experts=1,
                n_routed_experts=4, n_activated_experts=2, expert_hidden_dim=16,
                moe_balance_alpha=0., moe_score_func="softmax", moe_n_groups=1,
                moe_topk_groups=1, moe_route_scale=1.)
            self.moe = source.DeepSeekMoE(cfg).float()
            with torch.no_grad():
                for expert in [self.moe.shared_experts, *self.moe.experts]:
                    expert.w2.weight.zero_()
        for p in self.parameters():
            p.requires_grad_(True)
        if sum(p.numel() for p in self.parameters()) != self.expected_count():
            raise RuntimeError("source parameter count differs")
        self.route_records, self.depth_deltas = [], []

    def expected_count(self):
        return 5 * 3 * self.width * 16 + 4 * self.width

    def reset_records(self):
        self.route_records, self.depth_deltas = [], []

    def forward(self, x):
        if x.device.type != "cpu" or x.dtype != torch.float32 or x.ndim != 3 or x.shape[-1] != self.width:
            raise ValueError("CPU FP32 [batch,tokens,width] required")
        if not no_hooks(self.moe):
            raise RuntimeError("preexisting MoE instrumentation")
        captured = []
        def capture(module, inputs, result):
            weights, indices, scores = (z.detach() for z in result)
            if not finite(weights) or not finite(scores):
                raise RuntimeError("nonfinite routing")
            if indices.shape != (x.shape[0] * x.shape[1], 2) or scores.shape[-1] != 4:
                raise RuntimeError("routing shape differs")
            unique_top2_ids = bool((indices[:, 0] != indices[:, 1]).all())
            total_assignments = indices.numel()
            if not unique_top2_ids or total_assignments != 2 * len(scores) or bool(((indices < 0) | (indices >= 4)).any()):
                raise RuntimeError("routing top2 assignment invariant differs")
            ordered = scores.sort(descending=True, dim=-1).values
            mass = weights.double().sum(-1)
            entropy = -(scores.double() * scores.double().clamp_min(torch.finfo(torch.float64).tiny).log()).sum(-1)
            captured.append({"depth": len(self.route_records), "tokens": len(scores),
                "counts": torch.bincount(indices.flatten(), minlength=4).tolist(),
                "input_sha256": digest(inputs[0]), "total_assignments": total_assignments,
                "unique_top2_ids": unique_top2_ids,
                "indices_sha256": digest(indices), "weights_sha256": digest(weights),
                "soft_scores_sha256": digest(scores), "soft_scores_mean": scores.double().mean(0).tolist(),
                "weights_min": float(weights.min()), "weights_max": float(weights.max()),
                "weight_mass_mean": float(mass.mean()), "weight_mass_min": float(mass.min()),
                "weight_mass_max": float(mass.max()), "entropy_mean": float(entropy.mean()),
                "top2_margin_min": float((ordered[:, 1] - ordered[:, 2]).min())})
        handle = self.moe.gate.register_forward_hook(capture)
        try:
            delta, balance = self.moe(x.contiguous())
        finally:
            handle.remove()
        if balance is not None or self.moe.moe_balance_alpha != 0.:
            raise RuntimeError("balance loss outside this protocol")
        if len(captured) != 1 or not finite(delta):
            raise RuntimeError("invalid MoE capture/output")
        self.route_records.append(captured[0])
        if self.training and torch.is_grad_enabled():
            if not delta.requires_grad:
                raise RuntimeError("MoE graph detached")
            delta.retain_grad()
            self.depth_deltas.append(delta)
        return delta


class NativeCombo:
    """Post-injection native output -> frozen MoDA -> new MoE -> native core.

    History writes are after the second native block; the current depth never
    reads its own write. Frozen MoDA is evaluated with autograd enabled during
    training: only its instrumentation flag is false, avoiding retain_grad on
    its constant first-depth output without detaching subsequent paths.
    """
    def __init__(self, model):
        self.model, self.calls = model, 0
        self._check_base()
        self.depth_deltas, self.depth_keys, self.depth_values = [], [], []
        self.route_records, self.last_branch = [], None

    def _check_base(self):
        model = self.model
        if model.gradient_checkpointing or len(model.transformer.core_block) != 2:
            raise ValueError("fixed two-block native core without checkpointing required")
        if any(m.training for m in model.modules()):
            raise ValueError("native base must stay eval")
        if any(p.requires_grad or p.grad is not None for p in model.parameters()):
            raise ValueError("native base must stay frozen without gradients")

    def forward(self, ids, seed, moda=None, moe=None, training=False):
        if ids.device.type != "cpu" or ids.dtype != torch.long or ids.ndim != 2 or ids.shape[0] != 1 or not 1 <= ids.shape[1] <= 128:
            raise ValueError("CPU int64 batch-one length1..128 required")
        if training and moe is None:
            raise ValueError("training requires new MoE")
        if torch.is_autocast_enabled("cpu") or torch.is_autocast_enabled("cuda"):
            raise ValueError("autocast forbidden")
        self._check_base()
        model = self.model
        if not no_hooks(model):
            raise RuntimeError("preexisting native instrumentation")
        if moda is not None:
            if moda.arm != "depth" or any(m.training for m in moda.modules()):
                raise ValueError("only frozen eval depth MoDA allowed")
            if any(p.requires_grad or p.grad is not None for p in moda.parameters()):
                raise ValueError("MoDA must remain frozen without parameter gradients")
            if not no_hooks(moda):
                raise RuntimeError("preexisting MoDA instrumentation")
        if moe is not None:
            if not isinstance(moe, MoEResidual):
                raise ValueError("explicit MoEResidual required")
            enabled = [p.requires_grad for p in moe.parameters()]
            if training and not all(enabled):
                raise ValueError("all and only new MoE parameters must train")
            if not training and (any(enabled) != all(enabled) or any(p.grad is not None for p in moe.parameters())):
                raise ValueError("evaluation requires uniformly frozen/enabled MoE with no gradients")
            if not no_hooks(moe):
                raise RuntimeError("preexisting MoE instrumentation")
            moe.train(training)
            moe.reset_records()
        torch.manual_seed(seed)
        rng_before = digest(torch.get_rng_state())
        counts, h0, handles = [0, 0], [], []
        keys, values, read_lengths, write_depths = [], [], [], []
        adapter_calls = 0
        self.depth_deltas, self.depth_keys, self.depth_values = [], [], []
        self.route_records, self.last_branch = [], None
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
            result = output
            if moda is not None:
                if len(keys) != depth or len(values) != depth:
                    raise RuntimeError("missing/current/future history")
                read_lengths.append(depth)
                delta, _ = moda.read(result, keys, values, training=False)
                result = result + delta
            if moe is not None:
                result = result + moe(result)
            return result

        def core_hook(index):
            def hook(module, inputs, output):
                depth = counts[index]
                if depth >= DEPTH or adapter_calls != depth + 1 or (index == 1 and counts[0] != depth + 1):
                    raise RuntimeError("invalid core call order")
                counts[index] += 1
                if index == 1 and moda is not None:
                    if len(keys) != depth:
                        raise RuntimeError("history write order differs")
                    key, value = moda.write(output)
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
            for index, block in enumerate(model.transformer.core_block):
                handles.append(block.register_forward_hook(core_hook(index)))
            with torch.set_grad_enabled(training):
                result = model(ids, return_logits=True, num_steps_pair=torch.tensor([0, DEPTH], dtype=torch.long))
                logits = result["logits"]
            if counts != [DEPTH, DEPTH] or adapter_calls != DEPTH or len(h0) != 1:
                raise RuntimeError("native fixed32/h0 coverage differs")
            if logits is None or logits.dtype != torch.float32 or not finite(logits):
                raise RuntimeError("invalid logits")
            if training and not logits.requires_grad:
                raise RuntimeError("training graph detached")
            if moda is not None and (len(keys) != DEPTH or write_depths != list(range(DEPTH))):
                raise RuntimeError("incomplete MoDA writes")
            if moe is not None and (len(moe.route_records) != DEPTH or (training and len(moe.depth_deltas) != DEPTH)):
                raise RuntimeError("incomplete MoE depth coverage")
            self.depth_deltas = moe.depth_deltas if moe is not None else []
            self.route_records = moe.route_records if moe is not None else []
            self.depth_keys, self.depth_values = keys, values
            self.last_branch = {"moda": moda is not None, "moe": moe is not None,
                "read_lengths": read_lengths, "writer_calls": len(keys), "write_depths": write_depths}
            self.calls += 1
            completed = True
            return logits, {"h0_sha256": h0[0], "rng_before_sha256": rng_before,
                "rng_after_sha256": digest(torch.get_rng_state()), "seed": seed,
                "core_block_calls": counts, "adapter_calls": adapter_calls,
                "moda_reads": len(read_lengths), "moda_writes": len(keys),
                "moe_calls": len(self.route_records)}
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
                self.depth_deltas, self.depth_keys, self.depth_values = [], [], []
                self.route_records, self.last_branch = [], None
                if moe is not None:
                    moe.reset_records()
