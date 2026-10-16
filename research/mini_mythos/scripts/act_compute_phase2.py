#!/usr/bin/env python3
"""ACT-004 phase 2: absolute heldout losses and paired CPU timing by depth."""
import argparse
import inspect
import math
from pathlib import Path
import statistics

import torch
from act_ab import run_arm
from common import atomic_json, commit_id, get_repo, load_upstream


def aggregate(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["attention"], row["requested_depth"]), []).append(row)
    out = []
    for (attention, depth), cases in sorted(groups.items()):
        if len({r["seed"] for r in cases}) != len(cases):
            raise ValueError("Duplicate seed")
        def mean(fn):
            values = [fn(r) for r in cases]
            if not all(math.isfinite(v) for v in values):
                raise ValueError("Nonfinite metric")
            return statistics.mean(values)
        out.append({
            "attention": attention, "depth": depth, "seeds": len(cases),
            "original_heldout_loss_mean": mean(lambda r: r["heldout"]["original_loss"]),
            "forced_heldout_loss_mean": mean(lambda r: r["heldout"]["forced_final_loss"]),
            "delta_loss_forced_minus_original": mean(
                lambda r: r["heldout"]["forced_final_loss"] - r["heldout"]["original_loss"]),
            "original_forward_median_seconds_mean": mean(
                lambda r: r["benchmark"]["original"]["forward_median_seconds"]),
            "forced_forward_median_seconds_mean": mean(
                lambda r: r["benchmark"]["forced_final"]["forward_median_seconds"]),
            "original_backward_median_seconds_mean": mean(
                lambda r: r["benchmark"]["original"]["backward_median_seconds"]),
            "forced_backward_median_seconds_mean": mean(
                lambda r: r["benchmark"]["forced_final"]["backward_median_seconds"]),
            "forced_to_original_total_ratio_mean": mean(
                lambda r: r["benchmark"]["forced_to_original_median_total_ratio"]),
            "original_actual_loops_mean": mean(
                lambda r: r["benchmark"]["original"]["actual_loops_mean"]),
            "forced_actual_loops_mean": mean(
                lambda r: r["benchmark"]["forced_final"]["actual_loops_mean"]),
        })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33])
    p.add_argument("--attentions", choices=("gqa", "mla"), nargs="+", default=["gqa", "mla"])
    p.add_argument("--depths", type=int, nargs="+", default=[1, 2, 4])
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--heldout-batches", type=int, default=100)
    p.add_argument("--warmup", type=int, default=3)
    p.add_argument("--repeats", type=int, default=15)
    p.add_argument("--out", default="research/mini_mythos/results/act004/phase2.json")
    a = p.parse_args()
    if (not a.seeds or min(a.seeds) < 0 or len(set(a.seeds)) != len(a.seeds)
            or not a.depths or min(a.depths) < 1 or max(a.depths) > 8
            or len(set(a.depths)) != len(a.depths) or a.steps < 1
            or not 1 <= a.heldout_batches <= 10000 or a.warmup < 0 or a.repeats < 1):
        p.error("Invalid experiment parameters")
    root = get_repo(a.repo)
    target = Path(a.out).resolve()
    if not target.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Output must be under research/mini_mythos/results")
    torch.set_num_threads(min(4, torch.get_num_threads()))
    module = load_upstream(root)
    source = inspect.getsource(module.RecurrentBlock.forward)
    if not all(fragment in source for fragment in (
        "remainder = (1.0 - cumulative_p).clamp(min=0)",
        "cumulative_p + p >= self.cfg.act_threshold",
        "weight = weight * still_running.float()",
    )):
        raise RuntimeError("Upstream ACT implementation changed")
    rows = []
    for attention in a.attentions:
        for depth in a.depths:
            for seed in a.seeds:
                print(f"Running {attention} depth={depth} seed={seed}", flush=True)
                result = run_arm(
                    module, attention, depth, device="cpu", seed=seed,
                    steps=a.steps, lr=.003,
                    heldout_seeds=range(99001, 99001 + a.heldout_batches),
                    benchmark_warmup=a.warmup, benchmark_repeats=a.repeats,
                )
                result["seed"] = seed
                rows.append(result)
                print(
                    f"  heldout_original={result['heldout']['original_loss']:.6f} "
                    f"heldout_forced={result['heldout']['forced_final_loss']:.6f} "
                    f"timing_ratio={result['benchmark']['forced_to_original_median_total_ratio']:.3f}",
                    flush=True
                )
    summary = aggregate(rows)
    atomic_json(target, {
        "experiment": "ACT-004_phase2_trained_arm_CPU_benchmark",
        "upstream_commit": commit_id(root), "torch": torch.__version__,
        "seeds": a.seeds, "steps": a.steps, "heldout_batches": a.heldout_batches,
        "warmup": a.warmup, "repeats": a.repeats,
        "limitations": "CPU wall-clock only, not FLOPs; includes ACT hook overhead. "
                       "Order alternates but noise remains. Repeated same synthetic batch "
                       "for timing. Fixed optimizer steps, not matched FLOPs. "
                       "Absolute loss across depth compares separately trained tiny models.",
        "summary": summary, "results": rows,
    })
    print("attention depth original_loss forced_loss delta_loss timing_ratio")
    for r in summary:
        print(f"{r['attention']:>3} {r['depth']:>5} "
              f"{r['original_heldout_loss_mean']:.6f} "
              f"{r['forced_heldout_loss_mean']:.6f} "
              f"{r['delta_loss_forced_minus_original']:+.6f} "
              f"{r['forced_to_original_total_ratio_mean']:.3f}")
    print("Saved:", target)


if __name__ == "__main__":
    main()
