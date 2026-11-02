"""CPU prefix-only adaptive recurrence for pinned, unmodified Parcae.

No weights, data, labels, sampling, cache, training, or file persistence are used
here. The 0.01 TV threshold is an unvalidated engineering candidate. Call counts
are operation counts, not FLOPs or a claim of speedup. Source digests below are
canonical LF digests; the experiment owner must additionally guard raw upstream
bytes, Git revision, environment, weights and the model state before/after.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
import time
from typing import Any

import torch

UPSTREAM_COMMIT = "69284c13746e849104f738d6d1a347b1f457df76"
DEPTHS = (8, 16, 32)
TV_THRESHOLD = 0.01
SOURCE_SHA256 = {
    "parcae_lm/models/parcae/parcae.py": "c0d792379c3e965ec75bbe88dbdcf500392a12fd0c67f8a484543b2398470c3d",
    "parcae_lm/modules/blocks.py": "96232cf3543dcf7674d5610d1cb2e1c6bb0aae3c5a244d42db79b502c3d70ea3",
    "parcae_lm/modules/mixer.py": "7706683f5ce886db336fef84a290eb37f3fed6aff72f682203de4829c4ef5c4c",
    "parcae_lm/modules/injection.py": "a163acbf86824ba58fb741cae9e1b04c51eb0a4b3cb5d354492b412670a74f48",
    "parcae_lm/models/parcae/config.py": "e9a5e7515b8f5261191491964e4ea45fdb09f633bd55835d604fd544f41e0d18",
    "parcae_lm/models/config.py": "6c44badecd52f2a58ce3d3a14b70bcb64a181ea058b9bde99cbfbf76d917df95",
    "parcae_lm/modules/basic.py": "b2b38a8ab0fe6754c41634969d3fa52a6d1aab1a63e3757a63da69dc73ba63cc",
    "parcae_lm/modules/norms.py": "888cb97a5e29ef5b49b23eb39d83aa75cd126a5425a78ac75caa47923a3e16ba",
    "parcae_lm/modules/mlp.py": "5e108d54fc2890bb6327110bb7da9e81ba3b7beeb9142fac0de9d74fbde1edad",
    "parcae_lm/modules/utils.py": "e21f09ac8b6c33ac43837877c352c723a97218166a139dd0e9e8222dd7b3b2c5",
    "parcae_lm/attention_backends/flash_attention.py": "aaafb0a7ff405c2d8ebf02c25d493d0181971c254009d7b8ea54ab2b29c47179",
    "receval/models/parcae.py": "14363edd0b425f6d264517ae6d8f941a394313899425e97aaff596efddb2b382",
}


def tensor_bytes(value: torch.Tensor) -> bytes:
    return value.detach().cpu().contiguous().numpy().tobytes(order="C")


def tensor_sha256(value: torch.Tensor) -> str:
    return hashlib.sha256(tensor_bytes(value)).hexdigest()


def _finite_fp32(value: torch.Tensor, name: str) -> None:
    if (not isinstance(value, torch.Tensor) or value.device.type != "cpu"
            or value.dtype != torch.float32 or value.requires_grad):
        raise ValueError(f"{name} must be detached CPU FP32")
    if not bool(torch.isfinite(value).all()):
        raise ValueError(f"{name} contains nonfinite values")


def _validate_logits(value: torch.Tensor) -> None:
    _finite_fp32(value, "policy logits")
    if value.ndim != 2 or value.shape[0] != 1 or value.shape[1] < 2:
        raise ValueError("policy logits must have shape [1, vocabulary >= 2]")


@torch.no_grad()
def total_variation(logits8: torch.Tensor, logits16: torch.Tensor) -> float:
    """FP64 softmax TV of final-position FP32 logits, without RNG use."""
    _validate_logits(logits8)
    _validate_logits(logits16)
    if logits8.shape != logits16.shape:
        raise ValueError("policy vocabulary shapes differ")
    p = torch.softmax(logits8.to(torch.float64), dim=-1)
    q = torch.softmax(logits16.to(torch.float64), dim=-1)
    value = float((0.5 * torch.abs(p - q).sum()).item())
    if not (0.0 <= value <= 1.0):
        raise ValueError("invalid total variation")
    return value


def depth_from_tv(value: float) -> int:
    """Inclusive, frozen threshold; no stop-at-8 branch or tuning parameter."""
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= 1:
        raise ValueError("TV must be finite and in [0, 1]")
    return 16 if value <= TV_THRESHOLD else 32


@dataclass
class PrefixResult:
    mode: str
    selected_depth: int
    last_logits: torch.Tensor
    checkpoint_logits: dict[int, torch.Tensor]
    recurrent_state_sha256: dict[int, str]
    h0_sha256: str
    prefix_sha256: str
    tv_8_16: float | None
    counts: dict[str, int]
    policy_seconds: float
    rng_before_sha256: str
    rng_after_sha256: str


def _validate_input(model: Any, prefix_ids: torch.Tensor) -> None:
    if (not isinstance(prefix_ids, torch.Tensor) or prefix_ids.device.type != "cpu"
            or prefix_ids.dtype != torch.long or prefix_ids.ndim != 2
            or prefix_ids.shape[0] != 1):
        raise ValueError("prefix_ids must be CPU int64 [1, length], batch one only")
    if not 1 <= prefix_ids.shape[1] <= model.config.block_size:
        raise ValueError("empty prefix or context budget exceeded")
    if int(prefix_ids.min()) < 0 or int(prefix_ids.max()) >= model.config.padded_vocab_size:
        raise ValueError("token ID outside vocabulary")


def _validate_model(model: Any) -> None:
    """Fail closed to pinned native methods and the official structural subset.

    Width/vocabulary/context may shrink for random tiny developer fixtures.
    Supports 2/2/2, diagonal, like-init, ReLU2/RMSNorm, tied CPU FP32 only.
    This is deliberately not a generic Parcae/Transformer adapter.
    """
    from parcae_lm.models.parcae.parcae import Parcae
    from receval.models.parcae import ModelingParcae
    from parcae_lm.attention_backends import flash_attention

    if type(model) not in (Parcae, ModelingParcae):
        raise ValueError("only exact pinned native Parcae/ModelingParcae types supported")
    source = inspect.getsourcefile(Parcae)
    if source is None:
        raise ValueError("native source unavailable")
    root = Path(source).resolve().parents[3]
    for name, expected in SOURCE_SHA256.items():
        actual = hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError(f"unsupported native source: {name}")
    for name in ("initialize_state", "update_recurrent_state", "core_block_forward", "iterate_forward", "forward"):
        if getattr(getattr(model, name), "__func__", None) is not getattr(Parcae, name):
            raise ValueError(f"native method overridden: {name}")
    if any(module.training for module in model.modules()):
        raise ValueError("all modules must be in eval mode")
    if model.gradient_checkpointing or model.monitoring or model.extreme_monitoring:
        raise ValueError("checkpointing/monitoring is unsupported")
    if torch.is_autocast_enabled("cpu") or torch.is_autocast_enabled("cuda"):
        raise ValueError("autocast is unsupported")
    if flash_attention._override_impl is not None or flash_attention.HAS_FA3:
        raise ValueError("only native CPU SDPA fallback without overrides supported")
    required = {
        "injection_type": "diagonal", "state_init": "like-init", "prelude_norm": True,
        "n_layers_in_prelude": 2, "n_layers_in_recurrent_block": 2, "n_layers_in_coda": 2,
        "mean_recurrence": 8, "use_fused_head": "pytorch", "block_class_name": "TransformerPreNormBlock",
        "norm_class_name": "RMSNorm", "mlp_class_name": "BaseMLP", "nonlin_name": "ReLU2",
        "qk_norm": True, "tie_embeddings": True, "bias": False, "qk_bias": False,
        "randomize_positions_from": None, "logit_softcap": None, "clip_qkv": None,
        "simple_ops": False, "strategy": "single", "use_abacus": False,
        "debias_attention": False, "center_attention": False, "attn_impl": "flash",
    }
    c = model.config
    for name, expected in required.items():
        if getattr(c, name, object()) != expected:
            raise ValueError(f"unsupported config {name}")
    if (c.recurrent_iteration_method not in ("per-batch", "per-sequence")
            or model.recurrent_iteration_method != c.recurrent_iteration_method
            or c.recurrent_embedding_dimension != c.n_embd
            or c.recurrent_intermediation_embedding_dimension != c.intermediate_size
            or c.num_attention_heads != c.num_key_value_heads
            or c.recurrent_block_config.num_attention_heads != c.num_attention_heads
            or c.n_embd < 32 or c.n_embd % c.num_attention_heads
            or c.rope_settings.use_rope is not True
            or c.rope_settings.rope_base != 50_000 or c.rope_settings.rope_condense_ratio != 1):
        raise ValueError("unsupported recurrent dimensions/routing/RoPE")
    if (len(model.transformer.prelude), len(model.transformer.core_block), len(model.transformer.coda)) != (2, 2, 2):
        raise ValueError("actual block lengths differ from supported config")
    if model.lm_head.weight is not model.transformer.wte.weight:
        raise ValueError("tied embeddings are not tied")
    for name, value in list(model.named_parameters()) + list(model.named_buffers()):
        if value.device.type != "cpu" or (value.is_floating_point() and value.dtype != torch.float32):
            raise ValueError(f"unsupported device/dtype: {name}")


@torch.no_grad()
def _run(model: Any, prefix_ids: torch.Tensor, mode: str, fixed_depth: int | None = None) -> PrefixResult:
    """Internal execution also exercised with explicit toy test fixtures."""
    _validate_input(model, prefix_ids)
    if mode not in ("adaptive", "fixed", "checkpoints"):
        raise ValueError("invalid execution mode")
    if mode == "fixed" and (type(fixed_depth) is not int or fixed_depth not in DEPTHS):
        raise ValueError("fixed depth must be 8, 16 or 32")
    if mode != "fixed" and fixed_depth is not None:
        raise ValueError("fixed depth only belongs to fixed mode")
    ids = prefix_ids.clone()
    before_rng = tensor_sha256(torch.get_rng_state())
    old_exists = hasattr(model, "_current_input_ids")
    old_ids = getattr(model, "_current_input_ids", None)
    counts = dict(embedding_calls=0, prelude_block_calls=0, prelude_norm_calls=0,
                  h0_calls=0, recurrent_updates=0, adapter_calls=0, core_block_calls=0,
                  projection_calls=0, coda_block_calls=0, final_norm_calls=0, head_calls=0,
                  readouts=0, policy_evaluations=0, policy_softmax_calls=0,
                  policy_vocabulary_elements=0, readout_clone_elements=0,
                  value_embedding_calls=0)
    logits_by_depth, state_hashes = {}, {}
    tv, policy_seconds = None, 0.0
    budget = fixed_depth if mode == "fixed" else 32
    planned_readouts = (fixed_depth,) if mode == "fixed" else DEPTHS
    try:
        model._current_input_ids = ids
        freqs = model.freqs_cis[:, :ids.shape[1]]
        counts["embedding_calls"] += 1
        embeds = model.transformer.wte(ids)
        if model.emb_scale != 1:
            embeds = embeds * model.emb_scale
        for i, block in enumerate(model.transformer.prelude):
            ve = model.value_embeds[str(i)](ids) if str(i) in model.value_embeds else None
            counts["value_embedding_calls"] += int(ve is not None)
            counts["prelude_block_calls"] += 1
            embeds = block(embeds, freqs, None, ve=ve)
        if model.config.prelude_norm:
            counts["prelude_norm_calls"] += 1
            embeds = model.transformer.ln_prelude(embeds)
        _finite_fp32(embeds, "prelude")
        counts["h0_calls"] += 1
        state = model.initialize_state(embeds)
        _finite_fp32(state, "h0")
        h0_hash = tensor_sha256(state)
        total = torch.tensor(budget, dtype=torch.long, device="cpu")
        for step in range(budget):
            # The pinned core never reads step/total_steps. Source guard above is
            # required: a future depth-conditioned core cannot share this proof.
            counts["recurrent_updates"] += 1
            counts["adapter_calls"] += 1
            counts["core_block_calls"] += len(model.transformer.core_block)
            counts["value_embedding_calls"] += sum(
                str(model.config.n_layers_in_prelude + i) in model.value_embeds
                for i in range(len(model.transformer.core_block)))
            state = model.update_recurrent_state(state, embeds, freqs, None,
                                                 torch.tensor(step, dtype=torch.long), total)
            _finite_fp32(state, "recurrent state")
            depth = step + 1
            if depth not in planned_readouts:
                continue
            state_before = tensor_bytes(state)
            state_hashes[depth] = hashlib.sha256(state_before).hexdigest()
            readout_rng = tensor_bytes(torch.get_rng_state())
            # Clone is intentional even though native C currently allocates.
            # Readout hooks/in-place operations cannot alias recursive state.
            x = state.clone()
            counts["readout_clone_elements"] += state.numel()
            counts["projection_calls"] += 1
            x = model.transformer.C(x)
            offset = model.config.n_layers_in_prelude + model.config.n_layers_in_recurrent_block
            for i, block in enumerate(model.transformer.coda):
                key = str(offset + i)
                ve = model.value_embeds[key](ids) if key in model.value_embeds else None
                counts["value_embedding_calls"] += int(ve is not None)
                counts["coda_block_calls"] += 1
                x = block(x, freqs, None, ve=ve)
            counts["final_norm_calls"] += 1
            x = model.transformer.ln_f(x)
            counts["head_calls"] += 1
            logits = model.lm_head(x).float() * model.config.init.logit_scale
            _finite_fp32(logits, "readout logits")
            if tuple(logits.shape) != (1, ids.shape[1], model.config.padded_vocab_size):
                raise ValueError("unexpected readout shape")
            if tensor_bytes(state) != state_before:
                raise RuntimeError("readout mutated recurrence state")
            if tensor_bytes(torch.get_rng_state()) != readout_rng:
                raise RuntimeError("readout consumed CPU RNG")
            counts["readouts"] += 1
            logits_by_depth[depth] = logits[:, -1, :].clone()
            if mode == "adaptive" and depth == 16:
                policy_rng = tensor_bytes(torch.get_rng_state())
                start = time.perf_counter()
                tv = total_variation(logits_by_depth[8], logits_by_depth[16])
                selected = depth_from_tv(tv)
                policy_seconds = time.perf_counter() - start
                counts["policy_evaluations"] += 1
                counts["policy_softmax_calls"] += 2
                counts["policy_vocabulary_elements"] += 2 * model.config.padded_vocab_size
                if tensor_bytes(torch.get_rng_state()) != policy_rng:
                    raise RuntimeError("policy consumed CPU RNG")
                if selected == 16:
                    break
        counts["total_block_calls"] = sum(counts[k] for k in
            ("prelude_block_calls", "core_block_calls", "coda_block_calls"))
        return PrefixResult(mode, depth, logits_by_depth[depth], logits_by_depth,
                            state_hashes, h0_hash, tensor_sha256(ids), tv, counts,
                            policy_seconds, before_rng, tensor_sha256(torch.get_rng_state()))
    finally:
        if old_exists:
            model._current_input_ids = old_ids
        elif hasattr(model, "_current_input_ids"):
            delattr(model, "_current_input_ids")


@torch.no_grad()
def adaptive_next_token(model: Any, prefix_ids: torch.Tensor) -> PrefixResult:
    """Adapt one entire supplied prefix to depth 16 or 32; never accepts labels."""
    _validate_model(model)
    return _run(model, prefix_ids, "adaptive")


@torch.no_grad()
def fixed_next_token(model: Any, prefix_ids: torch.Tensor, *, depth: int) -> PrefixResult:
    """No policy/intermediate readout: one native-depth control at 8/16/32."""
    _validate_model(model)
    return _run(model, prefix_ids, "fixed", depth)


@torch.no_grad()
def diagnostic_checkpoints(model: Any, prefix_ids: torch.Tensor) -> PrefixResult:
    """Development identity control: always resume 8->16->32 with 3 readouts."""
    _validate_model(model)
    return _run(model, prefix_ids, "checkpoints")
