#!/usr/bin/env python3
"""R0 differential test: original cached-chunk behavior vs isolated mask fix.

Checks GQA and MLA against un-cached full-context logits with identical weights.
Reports original defects rather than concealing them behind a fixed-only test.
"""
import argparse
import math
import traceback
from pathlib import Path

import torch

from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config, toy_batch
from r0_cache_mask import cached_chunk_forward


def compare(module, attention, *, seed=7128, tolerance=5e-4):
    torch.manual_seed(seed)
    model = module.OpenMythos(tiny_config(module, attention)).eval()
    data, _ = toy_batch(torch, 73021, seq_len=8)
    prefix, chunk = data[:, :6], data[:, 6:]
    with torch.no_grad():
        expected = model(data, n_loops=2)[:, 6:]

        original_cache = {}
        model(prefix, n_loops=2, kv_cache=original_cache, start_pos=0)
        try:
            actual_original = model(chunk, n_loops=2, kv_cache=original_cache, start_pos=6)
            original_delta = float((expected - actual_original).abs().max().detach())
            original_result = {
                "status": "PASS" if math.isfinite(original_delta)
                                   and original_delta <= tolerance else "FAIL",
                "max_abs_diff": original_delta,
            }
        except Exception as exc:
            original_result = {
                "status": "FAIL", "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
            }

        patched_cache = {}
        model(prefix, n_loops=2, kv_cache=patched_cache, start_pos=0)
        try:
            actual_patched = cached_chunk_forward(
                model, chunk, patched_cache, start_pos=6, n_loops=2)
            patched_delta = float((expected - actual_patched).abs().max().detach())
            patched_result = {
                "status": "PASS" if math.isfinite(patched_delta)
                                   and patched_delta <= tolerance else "FAIL",
                "max_abs_diff": patched_delta,
            }
        except Exception as exc:
            patched_result = {
                "status": "ERROR", "error_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "traceback": traceback.format_exc(limit=5),
            }

    return {
        "attention": attention, "seed": seed,
        "prefix_tokens": 6, "new_chunk_tokens": 2,
        "n_loops": 2, "tolerance": tolerance,
        "original": original_result, "mask_intervention": patched_result,
        "limitation": "Tiny randomly initialized CPU model. Mask intervention "
                      "temporarily overrides one model instance for sequential testing, "
                      "not a production fix or proof of Anthropic architecture.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--attentions", choices=("gqa", "mla"),
                        nargs="+", default=["gqa", "mla"])
    parser.add_argument("--strict", action="store_true",
                        help="Fail if experimental mask intervention does not pass")
    parser.add_argument("--out", default="research/mini_mythos/results/r0/cache_mask_comparison.json")
    args = parser.parse_args()
    root = get_repo(args.repo)
    destination = Path(args.out).resolve()
    if not destination.is_relative_to(root / "research/mini_mythos/results"):
        parser.error("--out must be inside research/mini_mythos/results")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    module = load_upstream(root)
    results = [compare(module, attention) for attention in args.attentions]
    atomic_json(destination, {
        "experiment": "R0 original vs research-only cached-chunk causal mask correction",
        "repository_commit": commit_id(root), "torch_version": torch.__version__,
        "results": results,
    })
    for result in results:
        original = result["original"]
        corrected = result["mask_intervention"]
        print(f"{result['attention']}: upstream={original['status']} "
              f"research_mask={corrected['status']} "
              f"research_max_abs={corrected.get('max_abs_diff', 'n/a')}")
        if corrected.get("error"):
            print("  corrected error:", corrected["error"])
    print("Saved:", destination)
    if args.strict and any(r["mask_intervention"]["status"] != "PASS" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
