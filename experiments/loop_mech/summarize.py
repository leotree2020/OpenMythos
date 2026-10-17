#!/usr/bin/env python3
"""
Tables for loop_mech results: per mechanism, seed-mean accuracy over
hops × T, plus the questions that matter for "does extra compute help":
    - in-range (hops ≤ 4) and out-of-range (hops ≥ 5) accuracy vs T
    - per seed: does accuracy at T=24 hold up vs the best T (no overthinking)?
    - loops actually run, and loop convergence for final-state readout
"""

import argparse
import json
import statistics
from collections import defaultdict

MECH_ORDER = ["fixed_act", "fixed_final", "rand_act", "rand_final"]


def mean(xs):
    return statistics.mean(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--train-max-hops", type=int, default=4)
    args = ap.parse_args()

    rows, conv = [], []
    for line in open(args.results):
        r = json.loads(line)
        if r.get("type") == "baselines":
            continue
        (conv if "rel_step" in r else rows).append(r)

    by = defaultdict(list)  # (mech, T) -> rows over seeds
    for r in rows:
        by[(r["mech"], r["n_loops"])].append(r)
    mechs = [m for m in MECH_ORDER if any(k[0] == m for k in by)]
    loops = sorted({k[1] for k in by})
    hops = sorted({int(h) for r in rows for h in r["acc"]})
    inr = [h for h in hops if h <= args.train_max_hops]
    oor = [h for h in hops if h > args.train_max_hops]

    def acc(r, hs):
        return mean([r["acc"][str(h)] for h in hs])

    print(
        f"\n### Accuracy, hops ≤ {args.train_max_hops} (in range) / ≥ {args.train_max_hops + 1} (beyond), seed mean\n"
    )
    print("| mech | " + " | ".join(f"T={t}" for t in loops) + " |")
    print("|---|" + "---|" * len(loops))
    for m in mechs:
        cells = []
        for t in loops:
            rs = by[(m, t)]
            cells.append(
                f"{mean([acc(r, inr) for r in rs]):.2f} / {mean([acc(r, oor) for r in rs]):.2f}"
            )
        print(f"| {m} | " + " | ".join(cells) + " |")

    print("\n### Per-hop accuracy at each mech's best T for hops ≥ 5 (seed mean)\n")
    print("| mech | best T | " + " | ".join(f"h={h}" for h in hops) + " |")
    print("|---|---|" + "---|" * len(hops))
    for m in mechs:
        best_t = max(loops, key=lambda t: mean([acc(r, oor) for r in by[(m, t)]]))
        rs = by[(m, best_t)]
        print(
            f"| {m} | {best_t} | "
            + " | ".join(f"{mean([r['acc'][str(h)] for r in rs]):.2f}" for h in hops)
            + " |"
        )

    print(
        "\n### Per seed: all-hops accuracy at trained depth, best T, and T=max (overthinking check)\n"
    )
    print(
        "| mech | seed | T_train | acc@T_train | best T | acc@best | acc@T="
        + str(max(loops))
        + " | loops run @T="
        + str(max(loops))
        + " |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for m in mechs:
        seeds = sorted({r["seed"] for t in loops for r in by[(m, t)]})
        for s in seeds:
            per_t = {t: next(r for r in by[(m, t)] if r["seed"] == s) for t in loops}
            t_train = (
                4 if m.startswith("fixed") else per_t[loops[0]]["trained_max_loops"]
            )
            t_train = min(loops, key=lambda t: abs(t - t_train))
            best = max(loops, key=lambda t: acc(per_t[t], hops))
            last = per_t[max(loops)]
            print(
                f"| {m} | {s} | {t_train} | {acc(per_t[t_train], hops):.3f} | {best} | "
                f"{acc(per_t[best], hops):.3f} | {acc(last, hops):.3f} | "
                f"{mean(list(last['mean_loops_run'].values())):.1f} |"
            )

    if conv:
        print(
            "\n### Final-state readout: relative state change per loop (hardest hops, seed mean)\n"
        )
        for m in mechs:
            cs = [c["rel_step"] for c in conv if c["mech"] == m]
            if cs:
                avg = [mean(v) for v in zip(*cs)]
                pick = [0, 3, 7, 11, 15, len(avg) - 1]
                print(
                    f"- {m}: "
                    + ", ".join(
                        f"t={i + 2}: {avg[i]:.3f}" for i in pick if i < len(avg)
                    )
                )


if __name__ == "__main__":
    main()
