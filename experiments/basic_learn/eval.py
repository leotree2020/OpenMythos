#!/usr/bin/env python3
"""
Held-out evaluation for the basic-learnability experiment.

Per checkpoint and depth (OpenMythos: T = 1, 2, 4, 8; Transformer: its fixed
3 blocks), per hop count 1-4: accuracy, cf_both, cf_follow. Hops 1-2 are the
trained range; 3-4 are informational. One "baselines" row per hop: uniform
10% and guessing among the digits present (= 1 / #chains here, since roots
are distinct; the majority-root guess equals it).

    python experiments/basic_learn/eval.py --ckpt experiments/basic_learn/ckpts/*.pt \\
        --out experiments/basic_learn/results.jsonl
"""

import argparse
import json
import os
import random
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "loop_mech"))

from eval_task import baselines, counterfactual  # noqa: E402
from models import build  # noqa: E402
from task_v2 import make_batch  # noqa: E402


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--hops", default="1,2,3,4")
    ap.add_argument("--om-loops", default="1,2,4,8")
    ap.add_argument("--n-per-hop", type=int, default=500)
    ap.add_argument("--data-seed", type=int, default=24680)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    hops_list = [int(h) for h in args.hops.split(",")]

    data = None
    with open(args.out, "a") as out:
        for path in args.ckpt:
            ck = torch.load(path, map_location="cpu", weights_only=False)
            model = build(ck["arm"], ck["n_statements"])
            model.load_state_dict(ck["model"])
            model.eval()
            if data is None:
                data = {}
                for h in hops_list:
                    x, y = make_batch(
                        random.Random(args.data_seed + h),
                        args.n_per_hop,
                        [h],
                        ck["n_statements"],
                    )
                    data[h] = (x, y, *counterfactual(x, args.data_seed + 50 + h))
                    out.write(
                        json.dumps({"type": "baselines", "hops": h, **baselines(x, y)})
                        + "\n"
                    )
            depths = (
                [int(t) for t in args.om_loops.split(",")]
                if ck["arm"] == "openmythos"
                else [None]
            )
            for T in depths:
                row = {
                    "type": "cell",
                    "arm": ck["arm"],
                    "seed": ck["seed"],
                    "n_loops": T,
                    "params": ck["params"],
                    "train_block_token_steps": ck["block_token_steps"],
                    "acc": {},
                    "cf_both": {},
                    "cf_follow": {},
                }
                for h, (x, y, xc, yc) in data.items():
                    p = model(x[:, :-1], n_loops=T)[:, -1].argmax(-1)
                    pc = model(xc[:, :-1], n_loops=T)[:, -1].argmax(-1)
                    row["acc"][h] = (p == y).float().mean().item()
                    row["cf_both"][h] = ((p == y) & (pc == yc)).float().mean().item()
                    row["cf_follow"][h] = (pc == yc).float().mean().item()
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(
                    f"{ck['arm']:11s} s{ck['seed']} T={T} "
                    + " ".join(
                        f"{h}h {row['acc'][h]:.3f}/{row['cf_both'][h]:.3f}"
                        for h in hops_list
                    ),
                    flush=True,
                )


if __name__ == "__main__":
    main()
