#!/usr/bin/env python3
"""
M5(a) sample size: precision with the first 500 vs all 1000 bodies of the K=2
diag_eval (review of the implementation report: the per-process memory of
1000 body-mean gradients is about 2.4 GB). Non-formal seed-99 K=2 models
(init and 200 steps, both arms). The 500-body result uses exactly the first
500 bodies of the same accumulation (nested), so the two differ only in n.
Reports V_b, S, S/(V_b+S), the between-query cosine and S - (K-1) V_b with
their bootstrap CIs and CI widths for the groups total, attn_all and
embed=head. Writes validation/m5_precision.json. Nothing here is a pass /
fail check; it informs the sampling rule of a preregistration revision.
"""

import argparse
import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import Geom, jsonable, load_set, load_state, rebuild_init  # noqa: E402
from e_m5 import FamilyAccumulator, ModelGrads, _prompts  # noqa: E402

GROUPS = ("total", "attn_all", "embed=head")
KEYS = ("V_b", "S", "S_share", "cos_between_queries", "S_minus_(K-1)V")
CI = {"V_b": "V_b_ci95", "S": "S_ci95", "cos_between_queries": "cos_ci95", "S_minus_(K-1)V": "S_minus_(K-1)V_ci95"}


def subset(acc, n):
    sub = FamilyAccumulator.__new__(FamilyAccumulator)
    sub.idx, sub.K, sub.B = acc.idx, acc.K, acc.B
    sub.G = acc.G[:n]
    sub.S = {k: v[:n] for k, v in acc.S.items()}
    sub.cos = {k: v[:n] for k, v in acc.cos.items()}
    sub.n = n
    return sub.finish()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    args = ap.parse_args()
    torch.set_num_threads(1)
    g = Geom(2)
    ev = load_set("diag_eval")
    out = {}
    for arm in ("openmythos", "transformer"):
        for label, model in (("init", rebuild_init(arm, 2, 99)),
                             ("step200", load_state(arm, 2, 99, 200, path=os.path.join(
                                 args.scratch, f"k2a_{arm}", f"K2_{arm}_s99_step200.pt")))):
            model.eval()
            mg = ModelGrads(model, g)
            idx = {k: mg.idx[k] for k in GROUPS}
            acc = FamilyAccumulator(idx, len(ev), mg.P, 2)
            for r in ev:
                x, y = _prompts([r], [range(2)], g)
                acc.add(mg.per_question(x, y)[0])
            mg.remove()
            res = {}
            for n in (500, len(ev)):
                f = subset(acc, n)
                res[str(n)] = {grp: {k: {"value": f[grp][k],
                                         "ci95": f[grp].get(CI.get(k, ""), None),
                                         "ci_width": (f[grp][CI[k]][1] - f[grp][CI[k]][0]) if k in CI else None}
                                     for k in KEYS} for grp in GROUPS}
            res["width_ratio_500_over_1000"] = {
                grp: {k: res["500"][grp][k]["ci_width"] / res[str(len(ev))][grp][k]["ci_width"]
                      for k in CI if res[str(len(ev))][grp][k]["ci_width"]} for grp in GROUPS}
            res["sign_of_S_minus_(K-1)V_lower_bound"] = {
                n: {grp: res[n][grp]["S_minus_(K-1)V"]["ci95"][0] > 0 for grp in GROUPS} for n in ("500", str(len(ev)))}
            out[f"{arm}_{label}"] = res
            del acc
            print(arm, label, json.dumps(res["width_ratio_500_over_1000"]), flush=True)
    with open(os.path.join(HERE, "validation", "m5_precision.json"), "w") as f:
        json.dump(jsonable(out), f, indent=1)


if __name__ == "__main__":
    main()
