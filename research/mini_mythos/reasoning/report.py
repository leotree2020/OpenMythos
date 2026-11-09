#!/usr/bin/env python3
"""Reasoning probe report: accuracy per cell and depth with Wilson 95% intervals, the floors to beat
(nominal chance, always-most-frequent answer, for `chain` a random digit from the question), and
paired depth effects (accuracy at depth d minus depth 8, bootstrap 95% CI over items).

  python report.py --scores DIR --sets reasoning_sets.jsonl --split dev [--label native] --out OUT.json
"""
import argparse
import collections
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from score import load_items  # noqa: E402

BOOT, SEED = 10000, 20261110


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def floors(items):
    n_c = np.mean([len(i["candidates"]) for i in items])
    ans = collections.Counter(i["candidates"][i["answer"]] for i in items)
    f = {"chance": float(np.mean([1 / len(i["candidates"]) for i in items])),
         "majority": ans.most_common(1)[0][1] / len(items), "candidates": float(n_c)}
    if items[0]["family"] == "chain":
        q = [i["prompt"].rsplit("Q: ", 1)[1] for i in items]
        f["copy_digit_from_question"] = float(np.mean([1 / len(set(re.findall(r"= (\d)\.", x))) for x in q]))
    return f


def read(path):
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scores", required=True)
    p.add_argument("--sets", required=True)
    p.add_argument("--split", default="dev")
    p.add_argument("--label", default="native")
    p.add_argument("--out", required=True)
    p.add_argument("--max-per-cell", type=int, default=0, help="testing only")
    args = p.parse_args()
    items = load_items(args.sets, args.split, args.max_per_cell)
    sd = Path(args.scores)
    depths = sorted(int(x.stem.split("_d")[1]) for x in sd.glob("items_d*.csv"))
    res = {d: read(sd / ("items_d%d.csv" % d)) for d in depths}
    cells = collections.OrderedDict()
    for it in items:
        cells.setdefault((it["family"], it["level"]), []).append(it)
    rng = np.random.default_rng(SEED)
    o = {"label": args.label, "split": args.split, "depths": depths, "cells": {}}
    for (fam, lev), its in cells.items():
        ids = [i["id"] for i in its]
        c = {"n": len(ids), "floors": floors(its), "accuracy": {}, "vs_depth8": {}}
        corr = {d: np.array([int(res[d][i]["correct"]) for i in ids]) for d in depths}
        for d in depths:
            k = int(corr[d].sum())
            c["accuracy"][d] = {"acc": k / len(ids), "ci95": wilson(k, len(ids))}
        if 8 in corr:
            for d in depths:
                if d == 8:
                    continue
                diff = corr[d] - corr[8]
                idx = rng.integers(0, len(diff), size=(BOOT, len(diff)))
                b = np.sort(diff[idx].mean(1))
                c["vs_depth8"][d] = {"diff": float(diff.mean()), "ci95": [float(b[int(.025 * BOOT)]),
                                                                         float(b[int(.975 * BOOT) - 1])]}
        o["cells"]["%s-%d" % (fam, lev)] = c
    Path(args.out).write_text(json.dumps(o, indent=1) + "\n")
    L = ["# Reasoning probes: %s, %s split" % (args.label, args.split), "",
         "Accuracy [Wilson 95%%] per depth; floors: chance / always-most-frequent%s. Last columns: depth d minus depth 8 "
         "(bootstrap 95%% CI)." % (" / copy-a-digit (chain)"), "",
         "| cell | n | floors | " + " | ".join("d%d" % d for d in depths) + " | " +
         " | ".join("d%d-d8" % d for d in depths if d != 8) + " |",
         "|---|---:|---|" + "---:|" * len(depths) + "---:|" * (len(depths) - (8 in depths))]
    for name, c in o["cells"].items():
        f = c["floors"]
        fl = "%.2f / %.2f%s" % (f["chance"], f["majority"],
                                " / %.2f" % f["copy_digit_from_question"] if "copy_digit_from_question" in f else "")
        accs = " | ".join("%.3f [%.2f,%.2f]" % (c["accuracy"][d]["acc"], *c["accuracy"][d]["ci95"]) for d in depths)
        vs = " | ".join("%+.3f [%+.2f,%+.2f]" % (c["vs_depth8"][d]["diff"], *c["vs_depth8"][d]["ci95"])
                        for d in depths if d != 8 and d in c["vs_depth8"])
        L.append("| %s | %d | %s | %s | %s |" % (name, c["n"], fl, accs, vs))
    Path(args.out).with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
