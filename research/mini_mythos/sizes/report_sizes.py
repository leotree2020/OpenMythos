#!/usr/bin/env python3
"""Stage S summary across Parcae sizes: dev NLL and reasoning-probe accuracy by recurrence depth.

  python report_sizes.py --root OUT --sets reasoning_sets.jsonl --out summary.json

OUT/<size>/nll/nll_d{depth}.csv, OUT/<size>/nll/nll.json, OUT/<size>/reasoning/items_d{depth}.csv.
Sizes without results are skipped. Depth effects are paired (same windows / items), bootstrap 95% CI.
"""
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
import importlib.util  # noqa: E402

sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402

sys.path.insert(0, str(HERE.parent / "reasoning"))        # several stages have a report.py: load by path
_spec = importlib.util.spec_from_file_location("reasoning_report", HERE.parent / "reasoning" / "report.py")
RR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RR)
load_items = RR.load_items

BOOT, SEED = 10000, 20261110
ORDER = ["parcae-140m", "parcae-370m", "parcae-770m", "parcae-1.3b"]


def boot(diff, rng):
    idx = rng.integers(0, len(diff), size=(BOOT, len(diff)))
    b = np.sort(diff[idx].mean(1))
    return [float(b[int(.025 * BOOT)]), float(b[int(.975 * BOOT) - 1])]


def nll_part(d, rng):
    depths = sorted(int(p.stem.split("_d")[1]) for p in d.glob("nll_d*.csv"))
    if not depths:
        return None
    per = {k: G.read_per_window(d / ("nll_d%d.csv" % k)) for k in depths}
    ids = sorted(per[depths[0]])
    mean = {k: np.array([np.mean(per[k][i]) for i in ids]) for k in depths}
    info = json.loads((d / "nll.json").read_text()) if (d / "nll.json").exists() else {}
    o = {"parameters": info.get("parameters"), "windows": len(ids), "mean_nll": {k: float(mean[k].mean()) for k in depths},
         "domain_mean_nll": {k: v["domain_mean_nll"] for k, v in info.get("depths", {}).items()},
         "agreement_with_stage1_cpu": info.get("agreement_with_stage1_cpu"), "vs_depth8": {}}
    if 8 in mean:
        for k in depths:
            if k != 8:
                diff = mean[k] - mean[8]
                o["vs_depth8"][k] = {"diff": float(diff.mean()), "ci95": boot(diff, rng)}
    return o


def reasoning_part(d, items, rng):
    depths = sorted(int(p.stem.split("_d")[1]) for p in d.glob("items_d*.csv"))
    if not depths:
        return None
    res = {k: RR.read(d / ("items_d%d.csv" % k)) for k in depths}
    cells = collections.OrderedDict()
    for it in items:
        cells.setdefault((it["family"], it["level"]), []).append(it)
    o = {"cells": {}, "families": {}, "all": {}, "above_floor_at_d8": []}
    fam_acc = collections.defaultdict(lambda: collections.defaultdict(list))
    fam_floor = collections.defaultdict(list)
    for (fam, lev), its in cells.items():
        ids = [i["id"] for i in its]
        f = RR.floors(its)
        best = max(f["chance"], f["majority"], f.get("copy_digit_from_question", 0))
        c = {"best_floor": best, "accuracy": {}}
        for k in depths:
            n_ok = sum(int(res[k][i]["correct"]) for i in ids)
            lo, hi = RR.wilson(n_ok, len(ids))
            c["accuracy"][k] = {"acc": n_ok / len(ids), "ci95": [lo, hi]}
            fam_acc[fam][k].append(n_ok / len(ids))
        fam_floor[fam].append(best)
        if 8 in c["accuracy"] and c["accuracy"][8]["ci95"][0] > best:
            o["above_floor_at_d8"].append("%s-%d" % (fam, lev))
        o["cells"]["%s-%d" % (fam, lev)] = c
    for fam in fam_acc:
        o["families"][fam] = {"mean_best_floor": float(np.mean(fam_floor[fam])),
                              "accuracy": {k: float(np.mean(v)) for k, v in fam_acc[fam].items()}}
    ids = [i["id"] for i in items]
    corr = {k: np.array([int(res[k][i]["correct"]) for i in ids]) for k in depths}
    o["all"] = {"accuracy": {k: float(corr[k].mean()) for k in depths}, "vs_depth8": {}}
    if 8 in corr:
        for k in depths:
            if k != 8:
                diff = corr[k] - corr[8]
                o["all"]["vs_depth8"][k] = {"diff": float(diff.mean()), "ci95": boot(diff, rng)}
    return o


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", required=True)
    p.add_argument("--sets", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    rng = np.random.default_rng(SEED)
    items = load_items(args.sets, "dev")
    root = Path(args.root)
    sizes = [s for s in ORDER if (root / s).is_dir()] + sorted(
        d.name for d in root.iterdir() if d.is_dir() and d.name not in ORDER)
    o = {"sizes": {}}
    for s in sizes:
        e = {"nll": nll_part(root / s / "nll", rng) if (root / s / "nll").is_dir() else None,
             "reasoning": reasoning_part(root / s / "reasoning", items, rng) if (root / s / "reasoning").is_dir() else None}
        if e["nll"] or e["reasoning"]:
            o["sizes"][s] = e
    Path(args.out).write_text(json.dumps(o, indent=1) + "\n")

    def ci(v):
        return "%+.4f [%+.4f,%+.4f]" % (v["diff"], v["ci95"][0], v["ci95"][1])

    L = ["# Stage S: Parcae sizes x recurrence depth (dev)", "",
         "## Dev NLL (mean over 400 windows; lower is better). Depth effect = depth d minus depth 8, paired.", "",
         "| size | params | d4 | d8 | d16 | d32 | d16-d8 | d32-d8 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s, e in o["sizes"].items():
        n = e["nll"]
        if not n:
            continue
        m = n["mean_nll"]
        L.append("| %s | %s | %s | %s | %s |" % (
            s, "%.0fM" % (n["parameters"] / 1e6) if n["parameters"] else "-",
            " | ".join("%.4f" % m[k] if k in m else "-" for k in (4, 8, 16, 32)),
            ci(n["vs_depth8"][16]) if 16 in n["vs_depth8"] else "-", ci(n["vs_depth8"][32]) if 32 in n["vs_depth8"] else "-"))
    L += ["", "## Reasoning probes, accuracy by family (mean over difficulty levels); floor = best trivial strategy", "",
          "| size | family | floor | d4 | d8 | d16 | d32 |", "|---|---|---:|---:|---:|---:|---:|"]
    for s, e in o["sizes"].items():
        r = e["reasoning"]
        if not r:
            continue
        for fam, f in r["families"].items():
            L.append("| %s | %s | %.2f | %s |" % (s, fam, f["mean_best_floor"], " | ".join(
                "%.3f" % f["accuracy"][k] if k in f["accuracy"] else "-" for k in (4, 8, 16, 32))))
    L += ["", "## Reasoning probes, all 3000 items: accuracy and paired depth effect", "",
          "| size | d4 | d8 | d16 | d32 | d16-d8 | d32-d8 | cells above floor at d8 |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for s, e in o["sizes"].items():
        r = e["reasoning"]
        if not r:
            continue
        a, v = r["all"]["accuracy"], r["all"]["vs_depth8"]
        L.append("| %s | %s | %s | %s | %s |" % (
            s, " | ".join("%.3f" % a[k] if k in a else "-" for k in (4, 8, 16, 32)),
            ci(v[16]) if 16 in v else "-", ci(v[32]) if 32 in v else "-", ", ".join(r["above_floor_at_d8"]) or "none"))
    Path(args.out).with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
