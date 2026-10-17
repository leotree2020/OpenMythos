#!/usr/bin/env python3
"""
Reconstruct the training compute of each loop_mech run by replaying its RNG.

train_task.py draws, per step, n_loops (rand mechanisms only) and then the
batch from one shared random.Random(seed). Replaying the same calls gives
the exact per-step nominal depth, so the budget is computed rather than
estimated. Also reports how far the data streams of a fixed and a rand run
with the same seed diverge (they share the RNG, so they are not paired).

Nominal compute counts every loop the training step asked for. ACT-readout
runs may exit early during training once every position has halted; those
executed loops were not logged, so for *_act runs the nominal figure is an
upper bound.

    python experiments/loop_mech/train_budget.py --out experiments/loop_mech/train_budget.json
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanisms import MECHS  # noqa: E402
from task import make_batch, seq_len  # noqa: E402


def replay(mech, seed, steps, batch_size, loops, rand_max, hops, n_statements):
    rng = random.Random(seed)
    depth_mode, _ = MECHS[mech]
    depths, first_batches = [], []
    for step in range(steps):
        n = loops if depth_mode == "fixed" else rng.randint(1, rand_max)
        x, _ = make_batch(rng, batch_size, hops, n_statements)
        depths.append(n)
        if step < 50:
            first_batches.append(x)
    return depths, first_batches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--loops", type=int, default=4)
    ap.add_argument("--rand-max", type=int, default=8)
    ap.add_argument("--n-statements", type=int, default=24)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    hops = [1, 2, 3, 4]
    tokens = args.batch_size * (seq_len(args.n_statements) - 1)
    rows = []
    for seed in [int(s) for s in args.seeds.split(",")]:
        batches = {}
        for mech in MECHS:
            depths, first = replay(
                mech,
                seed,
                args.steps,
                args.batch_size,
                args.loops,
                args.rand_max,
                hops,
                args.n_statements,
            )
            batches[mech] = first
            loop_steps = sum(depths)
            rows.append(
                {
                    "mech": mech,
                    "seed": seed,
                    "steps": args.steps,
                    "nominal_loop_steps": loop_steps,
                    "mean_depth": loop_steps / args.steps,
                    "depth_hist": {d: depths.count(d) for d in sorted(set(depths))},
                    # prelude + coda (1 + 1 blocks) + nominal recurrent loops,
                    # in block-forward units per token
                    "nominal_block_token_steps": (2 * args.steps + loop_steps) * tokens,
                    "act_readout_upper_bound": MECHS[mech][1] == "act",
                }
            )
        same = sum(
            bool((a == b).all())
            for a, b in zip(batches["fixed_act"], batches["rand_act"])
        )
        rows.append(
            {"seed": seed, "paired_first50_batches_fixed_vs_rand": same, "of": 50}
        )

    fixed = {r["seed"]: r for r in rows if r.get("mech") == "fixed_act"}
    for r in rows:
        if "mech" in r:
            r["budget_vs_fixed"] = (
                r["nominal_block_token_steps"]
                / fixed[r["seed"]]["nominal_block_token_steps"]
            )
            print(
                f"{r['mech']:12s} s{r['seed']} mean depth {r['mean_depth']:.3f} "
                f"budget × {r['budget_vs_fixed']:.3f}"
            )
        else:
            print(
                f"seed {r['seed']}: identical first-50 batches fixed vs rand: "
                f"{r['paired_first50_batches_fixed_vs_rand']}/50"
            )
    with open(args.out, "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
