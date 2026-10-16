#!/usr/bin/env python3
"""R2 upstream-first, safe, read-only compute/training preflight.

Inspect current Codespaces/GPU environment and SHA-pin the upstream source files.
Does not download a model, allocate model weights or start any training.
Memory rows are rough single-device AdamW state estimates, *not* hardware quotes.
Never record auth tokens, environment variable values, user identifiers or paths
outside of the selected repository. See R2_UPSTREAM_READINESS.md.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys

from common import atomic_json, commit_id, get_repo


SOURCE_PATHS = (
    "open_mythos/main.py",
    "open_mythos/variants.py",
    "open_mythos/tokenizer.py",
    "training/3b_fine_web_edu.py",
    "pyproject.toml",
)
PARAM_CANDIDATES = (120_000_000, 200_000_000, 1_000_000_000)


def sha256_of_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def memory_estimates(parameter_counts=PARAM_CANDIDATES):
    """Bounds: weights+gradients+AdamW states, excludes activation and overhead.

    16 bytes/param: bf16 weights (2), fp32 master (4), fp16/bf16 grads (2),
    fp32 AdamW moments m and v (8). Actual framework/dtype/sharding may vary.
    20 bytes/param: approximate fp32 weight(4)+grad(4)+m(4)+v(4)+padding(4)
    high-side illustration, *not* a guaranteed upper bound for full training.
    """
    out = []
    for count in parameter_counts:
        if not isinstance(count, int) or count <= 0:
            raise ValueError("Parameter count must be a positive integer")
        out.append({
            "parameter_count": count,
            "base_training_state_gib_at_16_bytes_per_param":
                round(count * 16 / 2**30, 3),
            "illustrative_state_gib_at_20_bytes_per_param":
                round(count * 20 / 2**30, 3),
            "excluded": "activations (recurrent loops), attention, CUDA buffers, "
                        "optimizer temporaries, dataloader, RoPE cache, fragmentation, "
                        "communication and checkpoint staging",
        })
    return out


def static_blockers(sources):
    """Source-level review flags only; presence/absence is NOT a runtime result."""
    train = sources["training/3b_fine_web_edu.py"]
    tok = sources["open_mythos/tokenizer.py"]
    main = sources["open_mythos/main.py"]
    findings = [
        {
            "id": "R2_DATA_CURSOR",
            "requires_review": "Streaming training dataset cursor after resume",
            "flag": "GAP" if "load_dataset(" in train and
                             "dataset_state" not in train else "REVIEW",
            "source": "training/3b_fine_web_edu.py",
            "reason": "Streaming loader may restart at shard beginning without data offset.",
        },
        {
            "id": "R2_TOKENIZER_REVISION",
            "requires_review": "Immutable tokenizer identifier/revision/hash",
            "flag": "GAP" if "from_pretrained" in tok and
                             "revision=" not in tok else "REVIEW",
            "source": "open_mythos/tokenizer.py",
            "reason": "External tokenizer may change and must match train/eval vocab IDs.",
        },
        {
            "id": "R2_CHECKPOINT_TRUST",
            "requires_review": "Safe serializer in production training",
            "flag": "GAP" if "weights_only=False" in train else "REVIEW",
            "source": "training/3b_fine_web_edu.py",
            "reason": "Loading untrusted pickle checkpoint is unsafe.",
        },
        {
            "id": "R2_HELDOUT_EVAL",
            "requires_review": "Explicit separately sourced heldout NLL/PPL in 3B script",
            "flag": "GAP" if "validation_loader" not in train and
                             "val_loader" not in train else "REVIEW",
            "source": "training/3b_fine_web_edu.py",
            "reason": "Training loss alone cannot benchmark language model quality.",
        },
        {
            "id": "R2_ACT_FP16_BF16",
            "requires_review": "Dtype propagation through ACT and attention",
            "flag": "REVIEW",
            "source": "open_mythos/main.py",
            "reason": "Check fp32 ACT accumulators, attention mask dtype and "
                      "mixed precision against public PR #26; must test under GPU.",
        },
        {
            "id": "R2_MOE_BALANCING",
            "requires_review": "MoE expert load-balance update actually executed",
            "flag": "REVIEW",
            "source": "open_mythos/main.py;training/3b_fine_web_edu.py",
            "reason": "Router bias presence alone is not load-balance assurance.",
        },
        {
            "id": "R2_CACHE_CHUNK",
            "requires_review": "Production multi-token KV cache mask",
            "flag": "GAP" if "_causal_mask(T, device, x.dtype)" in main else "REVIEW",
            "source": "open_mythos/main.py",
            "reason": "R0 verified original chunk-caching error; isolated research "
                      "mask correction is not merged into upstream.",
        },
    ]
    return findings


def build_report(repo, torch_module):
    src = {p: (repo / p).read_text(encoding="utf-8") for p in SOURCE_PATHS}
    disk = shutil.disk_usage(repo)
    hardware = {
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "pytorch_version": torch_module.__version__,
        "cuda_runtime_version": torch_module.version.cuda,
        "cuda_available": bool(torch_module.cuda.is_available()),
        "cuda_device_count": int(torch_module.cuda.device_count()),
        "local_disk_free_gib": round(disk.free / 2**30, 2),
        "gpus": [],
    }
    if hardware["cuda_available"]:
        for i in range(hardware["cuda_device_count"]):
            properties = torch_module.cuda.get_device_properties(i)
            hardware["gpus"].append({
                "index": i, "name": properties.name,
                "vram_total_gib": round(properties.total_memory / 2**30, 2),
                "compute_capability": "%d.%d" % (
                    properties.major, properties.minor
                ),
                "bf16_supported": bool(
                    torch_module.cuda.is_bf16_supported()
                ),
            })
    packages = {}
    for package in ("datasets", "transformers", "huggingface-hub", "flash-attn",
                    "accelerate", "safetensors"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    flags = static_blockers(src)
    return {
        "experiment": "R2 upstream-first infrastructure and training readiness preflight",
        "repository_commit": commit_id(repo),
        "source_sha256": {
            path: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for path, text in src.items()
        },
        "hardware": hardware,
        "dependency_versions": packages,
        "source_review": flags,
        "illustrative_single_device_training_state": memory_estimates(),
        "gpu_go": False,
        "gpu_go_reason": "The script only inventories hardware and lists known "
                         "source gaps. A successful inventory is not authorization "
                         "to launch training or evidence that a GPU run will fit.",
        "next_action": "Resolve P0 tokenizer/training-resume/heldout, obtain a real "
                       "GPU memory/time budget, and review PR #27 (~117.8M) "
                       "upstream training prototype before any training job.",
        "warnings": [
            "No model weights allocated or training launched.",
            "Memory numbers exclude activation/recurrent/attention/optimizer overhead.",
            "No secrets or environment variable values captured.",
            "Source pattern flags are review aids, not model behavior tests.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--out", default="research/mini_mythos/results/r2/preflight.json")
    a = p.parse_args()
    repo = get_repo(a.repo)
    out = Path(a.out).resolve()
    if not out.is_relative_to(repo / "research/mini_mythos/results"):
        p.error("Output must be beneath research/mini_mythos/results")
    if out.exists():
        p.error("R2 preflight output already exists; choose a new --out")
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("PyTorch is required to inventory the compute environment") from exc
    report = build_report(repo, torch)
    atomic_json(out, report)
    print("Git revision:", report["repository_commit"])
    print("PyTorch:", report["hardware"]["pytorch_version"])
    print("CUDA available:", report["hardware"]["cuda_available"])
    print("CUDA devices:", report["hardware"]["cuda_device_count"])
    for item in report["hardware"]["gpus"]:
        print("GPU:", item["name"], "VRAM GiB:", item["vram_total_gib"],
              "BF16:", item["bf16_supported"])
    print("Local disk free GiB:", report["hardware"]["local_disk_free_gib"])
    print("Missing/reviewed source requirements:")
    for finding in report["source_review"]:
        print(f"  [{finding['flag']}] {finding['id']}: "
              f"{finding['requires_review']}")
    print("GPU training approved:", report["gpu_go"])
    print("Saved:", out)


if __name__ == "__main__":
    main()
