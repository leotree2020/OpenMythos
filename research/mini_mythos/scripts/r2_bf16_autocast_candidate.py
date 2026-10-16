#!/usr/bin/env python3
"""R2 Gate C: reversible BF16-autocast candidate for OpenMythos tiny models.

Why:
PR #27 calls OpenMythos(...).to(device="cuda", dtype=torch.bfloat16).
This casts complex64 RoPE buffers to real BF16 and permanently loses phase.

Candidate (research overlay only):
  1. Move the FP32 model to the device WITHOUT requesting any dtype conversion.
     Preserve RoPE complex64 buffers exactly.
  2. Run only forward matmuls under torch.autocast(device_type, bf16).
  3. Override the *instance* full-sequence causal mask dtype to bf16 during the
     autocast region. Without that, a float32 mask added to bf16 attention logits
     may upcast them and break the following bf16 value matmul.
  4. Leave all master parameters float32 and compute CE loss in float32.

This is a tiny CPU numerical and gradient smoke test, NOT a fix of all upstream
FP16/BF16 paths, flash attention caching, production PR #27 or 118M training.
Do NOT use this as an unreviewed production training wrapper.
"""
import argparse
from contextlib import contextmanager
from pathlib import Path

import torch
import torch.nn.functional as F

from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config, toy_batch


ROPE_NAMES = ("freqs_cis", "freqs_cis_mla")


def snapshot_rope(model):
    saved = {}
    for name in ROPE_NAMES:
        value = getattr(model, name)
        if not torch.is_complex(value) or value.dtype != torch.complex64:
            raise ValueError(
                f"{name} is no longer complex64. Construct a fresh FP32 model: "
                "casting complex64 to BF16 has already discarded phase information."
            )
        saved[name] = value.detach().clone()
    return saved


def compare_rope(model, original):
    rows = []
    for name in ROPE_NAMES:
        now = getattr(model, name)
        before = original[name]
        preserved = (now.dtype == torch.complex64 and
                     torch.equal(now.cpu(), before.cpu()))
        rows.append({
            "buffer": name,
            "dtype": str(now.dtype),
            "complex": bool(now.is_complex()),
            "max_original_imaginary_abs": float(before.imag.abs().max()),
            "exactly_preserved": bool(preserved),
        })
    return rows


@contextmanager
def temporary_low_precision_causal_mask(model, target_dtype=torch.bfloat16):
    """Fix *full-context* attention mask promotion while retaining original API.

    Only safe for a no-cache seq_len x seq_len mask. This does NOT correct the
    separate R0 cached multi-token chunk causal-mask defect.
    """
    if target_dtype not in (torch.bfloat16, torch.float16):
        raise ValueError("Only torch bfloat16/float16 mask types supported")
    if "_causal_mask" in model.__dict__:
        raise ValueError("Refuse to override an existing instance mask implementation")
    original = model._causal_mask

    def mask_override(seq_len, device, dtype):
        if not isinstance(seq_len, int) or seq_len < 2:
            raise ValueError("Expected a full-context sequence length >= 2")
        return original(seq_len, device, target_dtype)

    model._causal_mask = mask_override
    try:
        yield
    finally:
        del model._causal_mask


def tiny_autocast_case(module, attention, device="cpu", seed=20261016):
    if attention not in ("gqa", "mla"):
        raise ValueError("Unknown attention mechanism")
    if device not in ("cpu", "cuda"):
        raise ValueError("This candidate only uses cpu or cuda")
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but no GPU device is available")
    torch.manual_seed(seed)
    config = tiny_config(module, attention=attention)
    model = module.OpenMythos(config).to(device=device)
    original_buffers = snapshot_rope(model)
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError("Candidate requires FP32 master parameters")
    x, y = toy_batch(
        torch, seed, batch_size=2, seq_len=8, device=device
    )
    model.train()

    # Same FP32 weights/inputs. This is a numerical reference, NOT a quality
    # benchmark. Training labels are deterministic synthetic tokens.
    model.zero_grad(set_to_none=True)
    fp32_logits = model(x, n_loops=2).detach().float()

    model.zero_grad(set_to_none=True)
    with temporary_low_precision_causal_mask(model):
        with torch.autocast(device_type=device, dtype=torch.bfloat16):
            bf16_logits = model(x, n_loops=2)
            loss = F.cross_entropy(
                bf16_logits.float().reshape(-1, config.vocab_size),
                y.reshape(-1),
            )
    if not torch.isfinite(loss.detach()):
        raise RuntimeError("BF16-autocast cross-entropy loss not finite")
    loss.backward()

    nonzero_grads = sum(
        p.grad is not None and bool(torch.any(p.grad != 0))
        for p in model.parameters()
    )
    gradient_norm = torch.nn.utils.clip_grad_norm_(
        model.parameters(), max_norm=1.0
    )
    if not torch.isfinite(gradient_norm):
        raise RuntimeError("BF16-autocast gradient norm not finite")
    if nonzero_grads == 0:
        raise RuntimeError("No gradients propagated through BF16 forward")
    if any(p.grad is not None and not torch.isfinite(p.grad).all()
           for p in model.parameters()):
        raise RuntimeError("Nonfinite BF16-autocast parameter gradients")

    # Make sure BF16 forward produced BF16 logits and that the original
    # complex buffers remain bit-identical and full FP32 master params intact.
    if bf16_logits.dtype != torch.bfloat16:
        raise RuntimeError(f"Expected BF16 logits, got {bf16_logits.dtype}")
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise RuntimeError("FP32 master parameter dtype was modified")
    phase_rows = compare_rope(model, original_buffers)
    if not all(row["exactly_preserved"] for row in phase_rows):
        raise RuntimeError("Complex RoPE buffers changed during autocast")
    delta = float((bf16_logits.detach().float() - fp32_logits).abs().max())

    return {
        "attention": attention,
        "device": device,
        "model_parameters": sum(p.numel() for p in model.parameters()),
        "autocast_dtype": str(bf16_logits.dtype),
        "master_parameter_dtype": "torch.float32",
        "loss": float(loss.detach()),
        "grad_norm_pre_clip": float(gradient_norm),
        "nonzero_gradient_tensors": nonzero_grads,
        "max_abs_fp32_vs_bf16_logit_delta": delta,
        "rope_buffers": phase_rows,
        "successful_forward_backward": True,
        "full_sequence_only": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--attentions", nargs="+", choices=("gqa", "mla"),
                   default=["gqa", "mla"])
    p.add_argument("--out",
                   default="research/mini_mythos/results/r2/bf16_autocast_candidate.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    dest = Path(a.out).resolve()
    if not dest.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Output must be under research/mini_mythos/results")
    if dest.exists():
        p.error("Refusing to overwrite previous R2 candidate results")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    module = load_upstream(root)
    results = [
        tiny_autocast_case(module, attention, device=a.device)
        for attention in a.attentions
    ]
    report = {
        "experiment": "R2 Gate C research-only BF16 autocast tiny forward/backward",
        "source_commit": commit_id(root),
        "torch_version": torch.__version__,
        "test_type": "tiny synthetic CPU/GPU implementation smoke, not language training",
        "model_core_source_modified": False,
        "candidate": "FP32 master weights + BF16 autocast + temporary BF16 "
                     "full-context causal mask; leave complex64 RoPE buffers untouched",
        "results": results,
        "limitations": "No PR #27 117.8M run, no FSDP, no flash attention CUDA, "
                       "no optimizer step/resume/data cursor or real text quality. "
                       "Separate original KV-cache chunk bug is not repaired.",
    }
    atomic_json(dest, report)
    for row in results:
        print(
            f"{row['attention']}: BF16={row['autocast_dtype']} "
            f"loss={row['loss']:.6f} grad_norm={row['grad_norm_pre_clip']:.6f} "
            f"phase_preserved={all(b['exactly_preserved'] for b in row['rope_buffers'])} "
            f"fp32_vs_bf16_max_delta={row['max_abs_fp32_vs_bf16_logit_delta']:.8f} "
            "PASS"
        )
    print("Source modified: False; real-model GPU training: NOT_PERFORMED")
    print("Saved:", dest)


if __name__ == "__main__":
    main()
