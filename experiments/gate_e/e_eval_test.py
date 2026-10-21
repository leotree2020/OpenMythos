#!/usr/bin/env python3
"""
Formal judgment of one K=2 run at step 12,000 on test_heldout (PREREGISTRATION
5.3, revisions 1-2: 9.5, 10.2). Evaluated once, eval mode; OpenMythos at T=4
(T = 1, 2, 8 for reference only). Body-grouped 95% CIs (gate_d
common.grouped_bootstrap, 2000 draws, seed 0).

    学会                     accuracy >= 90%, root-swap both-correct >= 80%,
                             query-swap both-correct >= 80%
    出现学习迹象             not 学会; lower CI bound of accuracy > 50% (the
                             upper bound of any query-independent predictor on
                             complete two-query families); query insensitivity
                             < 90%
    未满足综合学习迹象标准   neither
Simple prediction rules are descriptive only.

    python experiments/gate_e/e_eval_test.py --arm openmythos --seed 1
"""

import argparse
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
from common import grouped_bootstrap  # noqa: E402  gate_d
from e_common import Geom, atomic_write_json, encode, family_tensors, jsonable, load_set, load_state  # noqa: E402

BASELINE = 0.5


def level(acc, acc_lo, rs, qs, insens):
    if acc >= 0.9 and rs >= 0.8 and qs >= 0.8:
        return "学会"
    if acc_lo > BASELINE and insens < 0.9:
        return "出现学习迹象"
    return "未满足综合学习迹象标准"


@torch.no_grad()
def evaluate(model, rows, g, n_loops=None):
    x, y, slot, bid, roots = family_tensors(rows, g)
    pred = model(x, n_loops=n_loops)[:, g.READ_POS].argmax(-1) if n_loops else model(x)[:, g.READ_POS].argmax(-1)
    N = len(rows)
    ok = (pred == y).view(N, 2)
    if "root_swap" in rows[0]:
        xr = encode([r["root_swap"][k]["body"] + "|" + r["queries"][k] + "?" for r in rows for k in range(2)], g)
        yr = torch.tensor([ord(r["root_swap"][k]["answer"]) for r in rows for k in range(2)])
        pr = (model(xr, n_loops=n_loops) if n_loops else model(xr))[:, g.READ_POS].argmax(-1)
        rs_both = (ok.reshape(-1) & (pr == yr)).double().numpy()
    else:  # sets without counterfactuals (timing on dev_heldout only); never the formal test set
        rs_both = np.full(2 * N, np.nan)
    qs_both = ok.all(1).repeat_interleave(2).double().numpy()  # partner of question q: the other query
    insens = (pred.view(N, 2)[:, 0] == pred.view(N, 2)[:, 1]).double().numpy()
    groups = bid.numpy()
    acc = ok.reshape(-1).double().numpy()
    out = {"accuracy": {"mean": float(acc.mean()), "ci95": grouped_bootstrap(acc, groups)},
           "root_swap_both": ({"mean": float(rs_both.mean()), "ci95": grouped_bootstrap(rs_both, groups)}
                              if not np.isnan(rs_both).any() else None),
           "query_swap_both": {"mean": float(qs_both.mean()), "ci95": grouped_bootstrap(qs_both, groups)},
           "query_insensitivity": {"mean": float(insens.mean()), "ci95": grouped_bootstrap(insens, np.arange(N))},
           "pred_in_roots": float((pred.view(N, 2, 1) == roots.view(N, 1, 2)).any(-1).double().mean())}
    P = pred.view(N, 2)
    out["rules_descriptive"] = {
        "statement_1_digit": float((P == roots[:, :1]).double().mean()),
        "statement_2_digit": float((P == roots[:, 1:]).double().mean()),
        "larger_root": float((P == roots.max(1, keepdim=True).values).double().mean()),
        "smaller_root": float((P == roots.min(1, keepdim=True).values).double().mean()),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--step", type=int, default=12000)
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--set", default="test_heldout")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if os.path.exists(args.out):  # PREREGISTRATION 12.4.7: a judgment is written once, never redone
        print(f"REFUSED: {args.out} exists; the formal judgment is never repeated", file=sys.stderr)
        sys.exit(3)
    torch.set_num_threads(1)
    g = Geom(2)
    model = load_state(args.arm, 2, args.seed, args.step, path=args.ckpt)
    rows = load_set(args.set)
    res = {"arm": args.arm, "seed": args.seed, "step": args.step, "set": args.set, "baseline": BASELINE,
           "main": evaluate(model, rows, g)}
    m = res["main"]
    if m["root_swap_both"] is None:
        res["level"] = "not judged: set without root-swap counterfactuals (timing only)"
    else:
        res["level"] = level(m["accuracy"]["mean"], m["accuracy"]["ci95"][0], m["root_swap_both"]["mean"],
                             m["query_swap_both"]["mean"], m["query_insensitivity"]["mean"])
    if args.arm == "openmythos":
        res["reference_loops"] = {str(T): evaluate(model, rows, g, n_loops=T)["accuracy"] for T in (1, 2, 8)}
    atomic_write_json(args.out, jsonable(res), indent=1, ensure_ascii=False)
    print(args.arm, args.seed, res["level"], m["accuracy"])


if __name__ == "__main__":
    main()
