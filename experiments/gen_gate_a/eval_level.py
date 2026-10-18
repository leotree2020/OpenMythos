#!/usr/bin/env python3
"""
Evaluate final checkpoints of one level on its fixed set (test by default;
the smoke test uses --split dev so the test set is not touched before the
formal runs). OpenMythos is judged at T=4; T=1, 2, 8 are informational.

Per checkpoint and depth: accuracy with Wilson 95% CI, root-swap and
query-swap both-correct rates (query swap on its pre-fixed eligible rows,
with their count), counterfactual follow rates, prediction-in-roots, and for
C2 the equal-length subset. A "baselines" row gives the answer-free
heuristics and the oracle length bound on the same rows.
"""

import argparse
import json
import math
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "basic_learn"))

from data import load_set  # noqa: E402
from levels import N_STATEMENTS, parse  # noqa: E402
from models import build  # noqa: E402
from validate import TEST_HOPS, chain_lengths, heuristics  # noqa: E402


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--split", default="test", choices=["test", "dev"])
    ap.add_argument("--om-loops", default="4,1,2,8")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    first = torch.load(args.ckpt[0], map_location="cpu", weights_only=False)
    level = first["level"]
    ds = load_set(level, args.split)
    rows = ds["rows"]
    eq = torch.tensor(
        [len(set(chain_lengths(parse(r["prompt"])[0]).values())) == 1 for r in rows]
    )
    with open(args.out, "a") as out:
        hs = [heuristics(level, r["prompt"], r["answer"]) for r in rows]
        out.write(
            json.dumps(
                {
                    "type": "baselines",
                    "level": level,
                    "split": args.split,
                    "set_sha256": ds["sha256"],
                    "n": len(rows),
                    "n_query_swap": len(ds["qs_idx"]),
                    "n_equal_length": int(eq.sum()),
                    **{k: sum(h[k] for h in hs) / len(hs) for k in hs[0]},
                }
            )
            + "\n"
        )
        for path in args.ckpt:
            ck = torch.load(path, map_location="cpu", weights_only=False)
            assert ck["level"] == level
            model = build(ck["arm"], N_STATEMENTS[level])
            model.load_state_dict(ck["model"])
            model.eval()
            depths = [int(t) for t in args.om_loops.split(",")]
            for T in depths if ck["arm"] == "openmythos" else [None]:
                f = lambda x: model(x[:, :-1], n_loops=T)[:, -1].argmax(
                    -1
                )  # noqa: E731
                p = f(ds["x"])
                ok = p == ds["y"]
                pr = f(ds["x_rs"])
                row = {
                    "type": "cell",
                    "level": level,
                    "split": args.split,
                    "arm": ck["arm"],
                    "seed": ck["seed"],
                    "n_loops": T,
                    "n": len(rows),
                    "acc": ok.float().mean().item(),
                    "acc_ci95": wilson(int(ok.sum()), len(rows)),
                    "root_swap_both": (ok & (pr == ds["y_rs"])).float().mean().item(),
                    "root_swap_follow": (pr == ds["y_rs"]).float().mean().item(),
                    "pred_in_roots": sum(int(a) in c for a, c in zip(p, ds["roots"]))
                    / len(rows),
                }
                if len(ds["qs_idx"]):
                    pq = f(ds["x_qs"])
                    both = ok[ds["qs_idx"]] & (pq == ds["y_qs"])
                    row["n_query_swap"] = len(ds["qs_idx"])
                    row["query_swap_both"] = both.float().mean().item()
                    row["query_swap_both_ci95"] = wilson(int(both.sum()), len(both))
                    row["query_swap_follow"] = (pq == ds["y_qs"]).float().mean().item()
                if level == "C2":
                    row["n_equal_length"] = int(eq.sum())
                    row["acc_equal_length"] = ok[eq].float().mean().item()
                    row["acc_equal_length_ci95"] = wilson(
                        int(ok[eq].sum()), int(eq.sum())
                    )
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(
                    f"{level} {ck['arm']:11s} s{ck['seed']} T={T} acc {row['acc']:.3f} "
                    f"rs {row['root_swap_both']:.3f} qs {row.get('query_swap_both', float('nan')):.3f}"
                )


if __name__ == "__main__":
    main()
