#!/usr/bin/env python3
"""
Event times and their order (PREREGISTRATION 5.1-5.2, revision 1 9.4,
revision 2 10.1), computed mechanically from results/<state>.json and the
training logs. An event happens at the first checkpoint that meets its
condition and whose next checkpoint meets it too (the last checkpoint needs
no successor); otherwise "未发生".

    t_R      M1 P(roots) >= 0.9
    t_P2lin  A_lin(t) <= c0 + 0.5 (A_lin(0) - c0); A_lin = max over the digit-
             position record points except emb of the linear_std P2 accuracy
    t_P2mlp  the same with the MLP accuracy (void probes left out)
    t_M3     every computable digit-position record point except emb is "not
             detected" (sigma = 0 points excluded and listed)
    t_G      M5 total-parameter cosine between queries <= 0.5 x (-1/(K-1))
    t_Q      M1 query insensitivity < 0.9 and lower CI bound of J > 0
    t_L      dev_heldout accuracy >= 0.9 and query-swap both-correct >= 0.8
             (training log; K=2 only)
Order per run: earlier / same checkpoint / later; across seeds 一致 (all),
多数 (4 of 5, K=2 only), else 不一致.

    python experiments/gate_e/e_events.py --results results --runs runs --out events.json
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import ARMS, BRIDGE_SEEDS, BRIDGE_STEPS, K2_SEEDS, K2_STEPS, state_name  # noqa: E402

C0_P2 = 1 / 52
NOT_HAPPENED = "未发生"
EVENTS = ("t_R", "t_P2lin", "t_P2mlp", "t_M3", "t_G", "t_Q", "t_L")
PAIRS = (("t_P2lin", "t_R"), ("t_Q", "t_R"), ("t_P2mlp", "t_R"), ("t_G", "t_R"), ("t_P2lin", "t_G"))


def first_sustained(steps, cond):
    """cond: dict step -> bool or None (missing). First step meeting the
    condition whose successor meets it too."""
    for i, s in enumerate(steps):
        if cond.get(s) is not True:
            continue
        if i == len(steps) - 1 or cond.get(steps[i + 1]) is True:
            return s
    return NOT_HAPPENED


def a_max(m2, kind):
    best = None
    for k, v in m2[kind].items():
        if not k.startswith("P2@") or k == "P2@emb" or "acc" not in v or v.get("void"):
            continue
        best = v["acc"] if best is None else max(best, v["acc"])
    return best


def conditions(res, K, train_log=None):
    steps = sorted(res)
    c = {e: {} for e in EVENTS}
    a0 = {kind: a_max(res[steps[0]]["M2"], kind) for kind in ("linear_std", "mlp")}
    for s in steps:
        r = res[s]
        c["t_R"][s] = r["M1"]["metrics"]["p_roots"]["mean"] >= 0.9
        for ev, kind in (("t_P2lin", "linear_std"), ("t_P2mlp", "mlp")):
            a = a_max(r["M2"], kind)
            c[ev][s] = None if a is None or a0[kind] is None else a <= C0_P2 + 0.5 * (a0[kind] - C0_P2)
        c["t_M3"][s] = r["M3"]["t_M3_condition"]["all_not_detected"]
        c["t_G"][s] = r["M5"]["a_per_question"]["total"]["cos_between_queries"] <= 0.5 * (-1 / (K - 1))
        c["t_Q"][s] = (r["M1"]["query_insensitivity"]["mean"] < 0.9 and r["M1"]["metrics"]["J"]["ci95"][0] > 0)
    if train_log is not None:
        dev = {d["step"]: d for d in train_log["dev_log"]}
        for s in steps:
            d = dev.get(s)
            c["t_L"][s] = None if d is None else (d["acc"] >= 0.9 and d["query_swap_both"] >= 0.8)
    return c


def relation(a, b, steps):
    if a == NOT_HAPPENED and b == NOT_HAPPENED:
        return "都未发生"
    if a == NOT_HAPPENED:
        return "前者未发生"
    if b == NOT_HAPPENED:
        return "后者未发生"
    ia, ib = steps.index(a), steps.index(b)
    return "早于" if ia < ib else ("同时" if ia == ib else "晚于")


def consistency(rels, K):
    vals = list(rels.values())
    top = max(set(vals), key=vals.count)
    n = vals.count(top)
    if n == len(vals):
        return {"relation": top, "label": "一致"}
    if K == 2 and n == 4 and len(vals) == 5:
        return {"relation": top, "label": "多数"}
    return {"relation": None, "label": "不一致", "counts": {v: vals.count(v) for v in set(vals)}}


def analyse(results_dir, runs_dir):
    out = {}
    for K, seeds, steps in ((2, K2_SEEDS, K2_STEPS), (4, BRIDGE_SEEDS, BRIDGE_STEPS)):
        for arm in ARMS:
            per_seed = {}
            for seed in seeds:
                res = {}
                for t in steps:
                    p = os.path.join(results_dir, f"{state_name(arm, K, seed, t)}.json")
                    res[t] = json.load(open(p))
                tl = None
                if K == 2:
                    tl = json.load(open(os.path.join(runs_dir, f"K2_{arm}_s{seed}.json")))
                c = conditions(res, K, tl)
                ev = {e: first_sustained(list(steps), c[e]) for e in EVENTS if c[e]}
                per_seed[seed] = {"events": ev,
                                  "relations": {f"{a} vs {b}": relation(ev[a], ev[b], list(steps))
                                                for a, b in PAIRS if a in ev and b in ev}}
            rels = {}
            for a, b in PAIRS:
                key = f"{a} vs {b}"
                if all(key in v["relations"] for v in per_seed.values()):
                    rels[key] = consistency({s: v["relations"][key] for s, v in per_seed.items()}, K)
            out[f"K{K}_{arm}"] = {"per_seed": per_seed, "across_seeds": rels}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results"))
    ap.add_argument("--runs", default=os.path.join(HERE, "runs"))
    ap.add_argument("--out", default=os.path.join(HERE, "events.json"))
    args = ap.parse_args()
    out = analyse(args.results, args.runs)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v["across_seeds"] for k, v in out.items()}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
