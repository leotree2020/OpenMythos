#!/usr/bin/env python3
"""CPU-only probe for PR #27's model.to(dtype=torch.bfloat16) RoPE cast.

Do not train, call CUDA, write checkpoints, or mutate OpenMythos source.
Instantiates only a tiny model and a separate 4-element artificial buffer.
The probe records the *actual* complex64 → real bf16 conversion behavior.
"""
import argparse
import warnings
from pathlib import Path

import torch

from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config


def demonstrate_complex_to_bf16():
    """Pure PyTorch repro independent of model source or GPU availability."""
    class Phase(torch.nn.Module):
        def __init__(self):
            super().__init__()
            x = torch.arange(4, dtype=torch.float32) * 0.4
            self.register_buffer("phase", torch.polar(torch.ones_like(x), x))
    obj = Phase()
    initial = obj.phase.clone()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        obj.to(dtype=torch.bfloat16)
    return {
        "before_dtype": str(initial.dtype),
        "after_dtype": str(obj.phase.dtype),
        "original_complex": bool(initial.is_complex()),
        "after_complex": bool(obj.phase.is_complex()),
        "original_max_abs_imag": float(initial.imag.abs().max()),
        "remaining_imaginary_phase": None
            if not obj.phase.is_complex() else float(obj.phase.imag.abs().max()),
        "warning_excerpts": [
            str(note.message)[:250] for note in notices
        ],
    }


def test_tiny_upstream_buffers(module):
    """Construct a tiny instance, watch its actual RoPE buffers get cast."""
    torch.manual_seed(20261016)
    cfg = tiny_config(module, attention="mla")
    model = module.OpenMythos(cfg)
    originals = {}
    for name in ("freqs_cis", "freqs_cis_mla"):
        buffer = getattr(model, name)
        if not torch.is_complex(buffer):
            raise AssertionError(f"{name} must start as complex RoPE phases")
        originals[name] = buffer.detach().clone()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        model = model.to(device="cpu", dtype=torch.bfloat16)
    items = []
    for name, original in originals.items():
        after = getattr(model, name)
        items.append({
            "name": name,
            "before_dtype": str(original.dtype),
            "after_dtype": str(after.dtype),
            "before_complex": bool(original.is_complex()),
            "after_complex": bool(after.is_complex()),
            "original_max_imaginary_abs": float(original.imag.abs().max()),
            "phase_information_lost": bool(
                original.imag.abs().max() > 0
                and not after.is_complex()
            ),
        })
    return {
        "buffers": items,
        "warning_excerpts": [str(note.message)[:250] for note in notices],
        "model_parameters_allocated": sum(p.numel() for p in model.parameters()),
        "model_training_performed": False,
        "scope": "Tiny MLA OpenMythos instance on CPU; this only checks "
                 "buffer dtype and phase integrity, not 118M GPU BF16 training.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--out", default="research/mini_mythos/results/r2/rope_bf16_cpu_probe.json")
    args = p.parse_args()
    root = get_repo(args.repo)
    destination = Path(args.out).resolve()
    if not destination.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Output must be under research/mini_mythos/results")
    if destination.exists():
        p.error("Refusing to overwrite existing probe evidence")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    module = load_upstream(root)
    pure = demonstrate_complex_to_bf16()
    upstream = test_tiny_upstream_buffers(module)
    result = {
        "experiment": "R2 CPU-only RoPE complex-to-bf16 corruption probe",
        "git_revision": commit_id(root),
        "torch_version": torch.__version__,
        "device": "cpu",
        "pytorch_minimal": pure,
        "actual_tiny_upstream_model": upstream,
        "interpretation": "If phase_information_lost is true, calling model.to("
                          "dtype=bf16) directly corrupts the RoPE precomputed "
                          "complex buffer. Remedy is to preserve complex64 "
                          "buffers and cast only real floating weights, followed "
                          "by actual GPU BF16/FP16 tests before full training. "
                          "The original upstream model is not patched here.",
    }
    atomic_json(destination, result)
    print("PyTorch version:", torch.__version__)
    print("Toy pure PyTorch: complex before=", pure["original_complex"],
          "after=", pure["after_complex"])
    for row in upstream["buffers"]:
        print(row["name"], "original phase max abs imaginary=",
              round(row["original_max_imaginary_abs"], 6),
              "dtype after bf16 conversion=", row["after_dtype"],
              "phase_information_lost=", row["phase_information_lost"])
    print("Source files modified: False")
    print("Model training performed: False")
    print("Saved:", destination)


if __name__ == "__main__":
    main()
