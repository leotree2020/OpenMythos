#!/usr/bin/env python3
"""ACT-004 phase 1: compute-aware ACT depth sweep (CPU, synthetic tokens).

Uses the existing paired A/B trainer, preserving identical initialization,
training batches, optimizer steps, and heldout seeds within each configuration.
Reports measured *paired run* wall time, not per-arm speedup or FLOPs.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys
import time

import torch
from act_ab import run_arm
from common import atomic_json, commit_id, get_repo, load_upstream


def summarize(rows):
    groups = {}
    for row in rows:
        key = (row["attention"], row["requested_depth"])
        groups.setdefault(key, []).append(row)
    summary = []
    for (attention, depth), cases in sorted(groups.items()):
        if len({r["seed"] for r in cases}) != len(cases):
            raise ValueError("Duplicate seed in configuration")
        deltas = []
        times = []
        loops_a = []
        loops_b = []
        deficit = []
        for case in cases:
            h = case["heldout"]
            delta = h["forced_final_loss"] - h["original_loss"]
            if not math.isfinite(delta):
                raise ValueError("Nonfinite heldout difference")
            deltas.append(delta)
            times.append(case["paired_run_wall_seconds"])
            trace = case["train_trace"]
            if not trace:
                raise ValueError("Missing train trace")
            loops_a.append(statistics.mean(t["original_actual_loops"] for t in trace))
            loops_b.append(statistics.mean(t["forced_actual_loops"] for t in trace))
            deficit.append(statistics.mean(t["original_act_deficit_fraction"] for t in trace))
        summary.append({
            "attention": attention,
            "requested_depth": depth,
            "train_seed_count": len(cases),
            "mean_delta_loss_forced_minus_original": statistics.mean(deltas),
            "delta_loss_by_seed": {str(r["seed"]): d for r, d in zip(cases, deltas)},
            "mean_paired_run_wall_seconds": statistics.mean(times),
            "mean_original_forward_loop_calls_per_train_step": statistics.mean(loops_a),
            "mean_forced_forward_loop_calls_per_train_step": statistics.mean(loops_b),
            "mean_original_deficit_token_fraction_over_train_steps": statistics.mean(deficit),
        })
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33])
    parser.add_argument("--attentions", choices=("gqa", "mla"), nargs="+", default=["gqa", "mla"])
    parser.add_argument("--depths", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--heldout-batches", type=int, default=30)
    parser.add_argument("--heldout-seed-start", type=int, default=99001)
    parser.add_argument("--lr", type=float, default=0.003)
    parser.add_argument("--out", default="research/mini_mythos/results/act004/sweep.json")
    args = parser.parse_args()
    if (not args.seeds or min(args.seeds) < 0 or len(set(args.seeds)) != len(args.seeds)
            or not args.depths or min(args.depths) < 1 or max(args.depths) > 8
            or len(set(args.depths)) != len(args.depths)
            or args.steps < 1 or args.heldout_batches < 1
            or args.heldout_batches > 10000 or args.heldout_seed_start < 0
            or not math.isfinite(args.lr) or args.lr <= 0):
        parser.error("Invalid sweep configuration")
    root = get_repo(args.repo)
    out = Path(args.out).resolve()
    if not out.is_relative_to(root / "research/mini_mythos/results"):
        parser.error("--out must be under research/mini_mythos/results")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    module = load_upstream(root)
    import inspect
    source = inspect.getsource(module.RecurrentBlock.forward)
    if not all(part in source for part in (
        "remainder = (1.0 - cumulative_p).clamp(min=0)",
        "cumulative_p + p >= self.cfg.act_threshold",
        "weight = weight * still_running.float()",
    )):
        raise RuntimeError("Upstream ACT implementation changed; re-audit the intervention")
    rows = []
    for attention in args.attentions:
        for depth in args.depths:
            for seed in args.seeds:
                print(f"Running {attention} depth={depth} seed={seed}", flush=True)
                start = time.perf_counter()
                result = run_arm(
                    module, attention, depth, device="cpu", seed=seed,
                    steps=args.steps, lr=args.lr,
                    heldout_seeds=range(
                        args.heldout_seed_start,
                        args.heldout_seed_start + args.heldout_batches
                    ),
                )
                elapsed = time.perf_counter() - start
                result["seed"] = seed
                result["paired_run_wall_seconds"] = elapsed
                rows.append(result)
                h = result["heldout"]
                print(f"  delta_loss={h['forced_final_loss'] - h['original_loss']:+.6f} "
                      f"paired_wall_s={elapsed:.2f}", flush=True)
    payload = {
        "experiment": "ACT-004_phase1_depth_sweep",
        "upstream_commit": commit_id(root),
        "torch": torch.__version__,
        "device": "cpu",
        "seeds": args.seeds,
        "steps": args.steps,
        "lr": args.lr,
        "heldout_batches": args.heldout_batches,
        "heldout_seed_start": args.heldout_seed_start,
        "limitations": (
            "Paired run wall time includes initialization, two-arm training, "
            "diagnostics, and heldout evaluation; it is NOT per-arm latency or FLOPs. "
            "ACT probability-hook count records executed global recurrent calls, "
            "not per-token active FLOPs. Synthetic toy data only."
        ),
        "summary": summarize(rows),
        "results": rows,
    }
    atomic_json(out, payload)
    print("\nattention depth N mean_delta paired_wall_s original_loops forced_loops deficit_fraction")
    for row in payload["summary"]:
        print(
            f"{row['attention']:>3} {row['requested_depth']:>5} "
            f"{row['train_seed_count']:>2} "
            f"{row['mean_delta_loss_forced_minus_original']:+.6f} "
            f"{row['mean_paired_run_wall_seconds']:.2f} "
            f"{row['mean_original_forward_loop_calls_per_train_step']:.2f} "
            f"{row['mean_forced_forward_loop_calls_per_train_step']:.2f} "
            f"{row['mean_original_deficit_token_fraction_over_train_steps']:.3f}"
        )
    print("Saved:", out)


if __name__ == "__main__":
    main()
