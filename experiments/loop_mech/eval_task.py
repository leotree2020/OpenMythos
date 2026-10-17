#!/usr/bin/env python3
"""
Accuracy grid (hops × loop depth) and loop convergence for loop_mech checkpoints.

For each checkpoint and each test depth T, reports answer accuracy per hop
count on a fixed held-out sample set, plus mean loops actually run (ACT
readout can exit early). For final-state readout it also reports the
relative state change ||h_t - h_{t-1}|| / ||h_{t-1}|| per loop at the
largest T, i.e. whether the recurrence settles or keeps moving.

    python experiments/loop_mech/eval_task.py --ckpt experiments/loop_mech/ckpts/*.pt \\
        --out experiments/loop_mech/results.jsonl
"""

import argparse
import json
import os
import random
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanisms import MECHS, apply_readout  # noqa: E402
from task import make_batch  # noqa: E402

from open_mythos import OpenMythos  # noqa: E402


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--hops", default="1,2,3,4,5,6,8,10,12")
    ap.add_argument("--n-loops", default="1,2,4,6,8,12,16,24")
    ap.add_argument("--n-per-hop", type=int, default=400)
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--data-seed", type=int, default=12345)
    ap.add_argument("--threads", type=int, default=0, help="0 = torch default")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.threads:
        torch.set_num_threads(args.threads)
    hops_list = [int(h) for h in args.hops.split(",")]
    loops_list = [int(n) for n in args.n_loops.split(",")]

    with open(args.out, "a") as out:
        for path in args.ckpt:
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            readout = MECHS[ckpt["mech"]][1]
            model = OpenMythos(ckpt["cfg"])
            model.load_state_dict(ckpt["model"])
            model = apply_readout(model.eval(), readout)
            n_calls = [0]  # injection runs once per executed loop
            model.recurrent.injection.register_forward_hook(
                lambda m, i, o: n_calls.__setitem__(0, n_calls[0] + 1)
            )

            # same held-out samples for every checkpoint and depth
            data = {}
            for hops in hops_list:
                rng = random.Random(args.data_seed * 1000 + hops)
                data[hops] = make_batch(
                    rng, args.n_per_hop, [hops], ckpt["n_statements"]
                )

            for n_loops in loops_list:
                row = {
                    "ckpt": path,
                    "mech": ckpt["mech"],
                    "seed": ckpt["seed"],
                    "trained_max_loops": ckpt["cfg"].max_loop_iters,
                    "n_loops": n_loops,
                    "acc": {},
                    "mean_loops_run": {},
                }
                for hops, (x, y) in data.items():
                    correct = 0
                    loops_run = 0.0
                    for i in range(0, len(y), args.batch_size):
                        xb, yb = x[i : i + args.batch_size], y[i : i + args.batch_size]
                        n_calls[0] = 0
                        logits = model(xb[:, :-1], n_loops=n_loops)[:, -1]
                        correct += (logits.argmax(-1) == yb).sum().item()
                        loops_run += n_calls[0] * len(yb)
                    row["acc"][hops] = correct / len(y)
                    row["mean_loops_run"][hops] = loops_run / len(y)
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(
                    f"{ckpt['mech']:12s} s{ckpt['seed']} T={n_loops:<3d} "
                    + " ".join(f"{h}:{a:.2f}" for h, a in row["acc"].items()),
                    flush=True,
                )

            if readout == "final":
                x, _ = data[max(hops_list)]
                model.recurrent.record_states = True
                model(x[:100, :-1], n_loops=max(loops_list))
                hs = model.recurrent.states
                model.recurrent.record_states = False
                rel = [((b - a).norm() / a.norm()).item() for a, b in zip(hs, hs[1:])]
                out.write(
                    json.dumps(
                        {
                            "ckpt": path,
                            "mech": ckpt["mech"],
                            "seed": ckpt["seed"],
                            "rel_step": rel,
                        }
                    )
                    + "\n"
                )


if __name__ == "__main__":
    main()
