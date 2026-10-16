#!/usr/bin/env python3
"""R0 CPU runtime probes: tiny training checkpoint and cached chunk correctness.

These probes exercise the real upstream OpenMythos model but do NOT execute
the production 3B FSDP training script or measure real language ability.
"""
import argparse
import math
import tempfile
import traceback
from pathlib import Path

import torch
import torch.nn.functional as F

from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config, toy_batch


def loss(model, x, y):
    logits = model(x, n_loops=2)
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), y.reshape(-1))


def train_step(model, optimizer, x, y):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    value = loss(model, x, y)
    value.backward()
    optimizer.step()
    return float(value.detach())


def checkpoint_roundtrip(module, attention):
    """Verify model+AdamW state saved after 1 step reproduces the next step."""
    torch.manual_seed(7127)
    cfg = tiny_config(module, attention)
    first = module.OpenMythos(cfg)
    first_optim = torch.optim.AdamW(first.parameters(), lr=.001)
    x, y = toy_batch(torch, 73011, seq_len=8)
    train_step(first, first_optim, x, y)

    with tempfile.TemporaryDirectory(prefix="mini_mythos_r0_") as folder:
        path = Path(folder) / "safe_cpu_probe.pt"
        # Only tensor dictionaries and primitive types; no pickled config class.
        torch.save({"model": first.state_dict(),
                    "optimizer": first_optim.state_dict()}, path)
        bundle = torch.load(path, map_location="cpu", weights_only=True)

    torch.manual_seed(999)
    second = module.OpenMythos(cfg)
    second.load_state_dict(bundle["model"])
    second_optim = torch.optim.AdamW(second.parameters(), lr=.001)
    second_optim.load_state_dict(bundle["optimizer"])

    with torch.no_grad():
        first.eval()
        second.eval()
        lhs = first(x, n_loops=2)
        rhs = second(x, n_loops=2)
        pre_diff = float((lhs - rhs).abs().max())

    nx, ny = toy_batch(torch, 73012, seq_len=8)
    loss_a = train_step(first, first_optim, nx, ny)
    loss_b = train_step(second, second_optim, nx, ny)
    max_delta = max(float((a.detach() - b.detach()).abs().max())
                    for a, b in zip(first.parameters(), second.parameters()))
    good = max(pre_diff, max_delta, abs(loss_a - loss_b)) <= 1e-5
    return {
        "name": "tiny_model_optimizer_checkpoint_resume",
        "status": "PASS" if good else "FAIL",
        "attention": attention, "logit_max_abs_diff": pre_diff,
        "next_step_param_max_abs_diff": max_delta,
        "next_step_loss_abs_diff": abs(loss_a - loss_b),
        "scope": "tiny independent CPU state_dict test, not 3B trainer/FSDP or data iterator resume",
    }


def cached_chunk_equivalence(module, attention):
    """Compare split [prefix + 2-token chunk] against full causal recompute."""
    torch.manual_seed(7128)
    model = module.OpenMythos(tiny_config(module, attention)).eval()
    x, _ = toy_batch(torch, 73021, seq_len=8)
    with torch.no_grad():
        full = model(x, n_loops=2)
        cache = {}
        model(x[:, :6], n_loops=2, kv_cache=cache, start_pos=0)
        try:
            tail = model(x[:, 6:], n_loops=2, kv_cache=cache, start_pos=6)
        except (RuntimeError, ValueError, IndexError) as exc:
            return {
                "name": "multi_token_cached_chunk_equivalence",
                "status": "FAIL", "attention": attention,
                "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "scope": "prefill prefix of 6 tokens followed by 2-token cached chunk",
            }
    delta = float((full[:, -2:] - tail).abs().max())
    return {
        "name": "multi_token_cached_chunk_equivalence",
        "status": "PASS" if math.isfinite(delta) and delta <= 5e-4 else "FAIL",
        "attention": attention, "logit_max_abs_diff": delta,
        "tolerance": 5e-4,
        "scope": "prefill prefix of 6 tokens followed by 2-token cached chunk",
    }


def run_probe(fn, name, attention):
    try:
        return fn()
    except Exception as exc:
        return {
            "name": name, "attention": attention,
            "status": "ERROR", "error": repr(exc),
            "traceback": traceback.format_exc(limit=6),
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--attentions", choices=("gqa", "mla"), nargs="+", default=["gqa", "mla"])
    p.add_argument("--out", default="research/mini_mythos/results/r0/probes.json")
    p.add_argument("--strict", action="store_true", help="exit 1 when any probe fails")
    args = p.parse_args()
    root = get_repo(args.repo)
    output = Path(args.out).resolve()
    if not output.is_relative_to(root / "research/mini_mythos/results"):
        p.error("--out must be within research/mini_mythos/results")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    module = load_upstream(root)
    probes = []
    for attention in args.attentions:
        probes.append(run_probe(
            lambda a=attention: checkpoint_roundtrip(module, a),
            "tiny_model_optimizer_checkpoint_resume", attention
        ))
        probes.append(run_probe(
            lambda a=attention: cached_chunk_equivalence(module, a),
            "multi_token_cached_chunk_equivalence", attention
        ))
    atomic_json(output, {
        "stage": "R0 CPU model runtime probes",
        "repository_commit": commit_id(root), "torch_version": torch.__version__,
        "limitations": "Tiny random CPU models; no real text; no pretrained weights; no production trainer or GPU path. FAIL of cached chunks is an implementation/readiness issue, not evidence about Anthropic Mythos.",
        "probes": probes,
    })
    for item in probes:
        print(f"{item['status']:6} {item['attention']:3} {item['name']}")
        if item.get("error"):
            print("  ", item["error"][:240])
    print("Saved:", output)
    if args.strict and any(item["status"] != "PASS" for item in probes):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
