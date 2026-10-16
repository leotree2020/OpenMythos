#!/usr/bin/env python3
"""ACT-003 Gate B: expanded heldout paired-seed A/B on synthetic CPU data.

Runs existing act_ab.py (unchanged training semantics), collates the per-seed
heldout differences, and computes descriptive bootstrap CIs across train seeds.
This is exploratory, not a formal language-model performance benchmark.
"""
import argparse
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys

from common import atomic_json, commit_id, get_repo


def summarize(rows, *, bootstrap=2000, bootstrap_seed=20261016):
    if not rows:
        raise ValueError("At least one result is required")
    grouped = {}
    for row in rows:
        key = (row["attention"], row["requested_depth"])
        h = row["heldout"]
        delta = float(h["forced_final_loss"]) - float(h["original_loss"])
        if not math.isfinite(delta):
            raise ValueError("Nonfinite heldout loss difference")
        grouped.setdefault(key, []).append((int(row["seed"]), delta))
    output = []
    for (attention, depth), values in sorted(grouped.items()):
        values.sort()
        if len({seed for seed, _ in values}) != len(values):
            raise ValueError(f"Duplicate train seed for {attention} depth={depth}")
        differences = [delta for _, delta in values]
        mean = statistics.mean(differences)
        rng = random.Random(bootstrap_seed)
        samples = sorted(
            statistics.mean(rng.choices(differences, k=len(differences)))
            for _ in range(bootstrap)
        )
        lo = samples[int(0.025 * bootstrap)]
        hi = samples[min(bootstrap - 1, int(0.975 * bootstrap))]
        output.append({
            "attention": attention, "requested_depth": depth,
            "train_seed_count": len(values),
            "train_seeds": [seed for seed, _ in values],
            "delta_by_seed": differences,
            "mean_delta_loss_forced_minus_original": mean,
            "sample_std_delta_loss": statistics.stdev(differences) if len(differences) > 1 else None,
            "bootstrap_95_percentile_interval": [lo, hi],
            "original_better_count": sum(d > 1e-8 for d in differences),
            "forced_better_count": sum(d < -1e-8 for d in differences),
            "near_tie_count": sum(abs(d) <= 1e-8 for d in differences),
        })
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--device", choices=("cpu",), default="cpu")
    p.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33, 44, 55])
    p.add_argument("--attentions", nargs="+", choices=("gqa", "mla"), default=["gqa", "mla"])
    p.add_argument("--depths", type=int, nargs="+", default=[1, 2])
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--heldout-batches", type=int, default=100)
    p.add_argument("--heldout-seed-start", type=int, default=99001)
    p.add_argument("--bootstrap", type=int, default=2000)
    p.add_argument("--out-dir", default="research/mini_mythos/results/act003_gate_b")
    a = p.parse_args()
    if (not a.seeds or len(a.seeds) != len(set(a.seeds))
            or min(a.seeds) < 0 or not a.depths or len(a.depths) != len(set(a.depths))
            or min(a.depths) < 1 or max(a.depths) > 8 or a.steps < 1
            or a.heldout_batches < 1 or a.heldout_batches > 10000
            or a.heldout_seed_start < 0 or a.bootstrap < 100):
        p.error("Invalid seed/depth/steps/heldout/bootstrap configuration")
    repo = get_repo(a.repo)
    outdir = Path(a.out_dir).resolve()
    if not outdir.is_relative_to(repo / "research/mini_mythos/results"):
        p.error("Output directory must be within research/mini_mythos/results")
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in a.seeds:
        target = outdir / f"act_ab_seed_{seed}.json"
        cmd = [
            sys.executable, str(repo / "research/mini_mythos/scripts/act_ab.py"),
            "--repo", str(repo), "--device", "cpu",
            "--attentions", *a.attentions, "--depths", *(str(x) for x in a.depths),
            "--seed", str(seed), "--steps", str(a.steps),
            "--heldout-batches", str(a.heldout_batches),
            "--heldout-seed-start", str(a.heldout_seed_start),
            "--out", str(target),
        ]
        print(f"Running train seed={seed} ...", flush=True)
        subprocess.run(cmd, cwd=repo, check=True)
        result = json.loads(target.read_text(encoding="utf-8"))
        if (result.get("seed") != seed
                or result.get("heldout_batches") != a.heldout_batches
                or result.get("heldout_seed_start") != a.heldout_seed_start):
            raise ValueError(f"Result identity mismatch: {target}")
        expected = {(att, depth) for att in a.attentions for depth in a.depths}
        found = {(r["attention"], r["requested_depth"]) for r in result["results"]}
        if found != expected or len(result["results"]) != len(expected):
            raise ValueError(f"Missing or duplicated configurations: {target}")
        for r in result["results"]:
            if r["heldout"]["heldout_batches"] != a.heldout_batches:
                raise ValueError("Heldout batch count mismatch")
            rows.append({"seed": seed, **r})
    summary = summarize(rows, bootstrap=a.bootstrap)
    payload = {
        "experiment": "ACT-003_gate_b_expanded_heldout",
        "upstream_commit": commit_id(repo),
        "device": "cpu", "steps": a.steps,
        "seeds": a.seeds, "heldout_batches": a.heldout_batches,
        "heldout_seed_start": a.heldout_seed_start,
        "bootstrap_resamples": a.bootstrap,
        "interpretation": (
            "Paired A/B differences; positive forced-minus-original means original lower loss. "
            "Bootstrap resamples training seeds, not individual tokens. Tiny synthetic data, "
            "same heldout batches reused across seeds; exploratory descriptive intervals only."
        ),
        "summary": summary,
    }
    target = outdir / "summary.json"
    atomic_json(target, payload)
    print("attention depth N mean_delta bootstrap95 original_better forced_better")
    for r in summary:
        print(f"{r['attention']:>3} {r['requested_depth']:>5} "
              f"{r['train_seed_count']:>2} "
              f"{r['mean_delta_loss_forced_minus_original']:+.6f} "
              f"[{r['bootstrap_95_percentile_interval'][0]:+.6f}, "
              f"{r['bootstrap_95_percentile_interval'][1]:+.6f}] "
              f"{r['original_better_count']:>2} {r['forced_better_count']:>2}")
    print("Saved:", target)


if __name__ == "__main__":
    main()
