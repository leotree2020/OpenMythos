#!/usr/bin/env python3
"""Pivot eval_ppl.py JSONL output into seed × depth tables per ablation."""

import argparse
import json
import os
import statistics
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    args = ap.parse_args()

    rows = [json.loads(line) for line in open(args.results) if line.strip()]
    cells = defaultdict(dict)  # (ablation, n_loops) -> {seed: row}
    seeds, depths, ablations = [], [], []
    for r in rows:
        seed = os.path.basename(r["ckpt"]).removesuffix(".pt")
        for lst, v in (
            (seeds, seed),
            (depths, r["n_loops"]),
            (ablations, r["ablation"]),
        ):
            if v not in lst:
                lst.append(v)
        cells[(r["ablation"], r["n_loops"])][seed] = r
    depths.sort()

    for metric in ("byte_ppl", "mean_loops_run"):
        print(f"\n### {metric}\n")
        print("| ablation | T | " + " | ".join(seeds) + " | mean |")
        print("|---|---|" + "---|" * (len(seeds) + 1))
        for a in ablations:
            for d in depths:
                vals = [cells[(a, d)][s][metric] for s in seeds if s in cells[(a, d)]]
                fmt = "{:.4f}" if metric == "byte_ppl" else "{:.2f}"
                print(
                    f"| {a} | {d} | "
                    + " | ".join(fmt.format(v) for v in vals)
                    + f" | {fmt.format(statistics.mean(vals))} |"
                )


if __name__ == "__main__":
    main()
