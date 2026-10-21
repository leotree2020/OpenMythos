#!/usr/bin/env python3
"""
Accuracy grid (hops × loop depth), cost, hidden-state evolution and
shortcut / validity checks for loop_mech checkpoints.

Per checkpoint and test depth T, one "cell" row with, for every hop count:
    acc                answer accuracy on a fixed held-out sample set
    cf_both            counterfactual check: the queried chain's root digit is
                       replaced (everything else identical); fraction of pairs
                       where the model answers both the original and the
                       altered question correctly. A model that is not
                       following the chain cannot track the change.
    cf_follow          fraction of pairs where the prediction changes to the
                       new root (regardless of the original being right)
    loops_run          recurrent loops executed per forward call (ACT readout
                       may exit early; final-state readout always runs T)
    loop_tokens        loops executed × tokens (recurrent compute)
    fwd_seconds        wall time of the forward passes
plus per-loop hidden-state RMS and relative change ||h_t - h_{t-1}|| / ||h_{t-1}||
on the --state-hops samples.

A "baselines" row per hop count records answer-free reference accuracies
from the same samples: uniform 10-way chance, guessing uniformly among the
root digits present in the prompt, and always answering the most frequent
root digit.

    python experiments/loop_mech/eval_task.py --ckpt experiments/loop_mech/ckpts/*.pt \\
        --out experiments/loop_mech/results.jsonl
"""

import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanisms import MECHS, apply_readout  # noqa: E402
from task import make_batch  # noqa: E402

from open_mythos import OpenMythos  # noqa: E402

STMT = re.compile(r"([A-Za-z])=([A-Za-z0-9]);")


def parse(row: torch.Tensor):
    """Return (text, assignments dict, query var, root var of the queried chain)."""
    text = bytes(row.tolist()).decode()
    body, q = text.split("|")
    var = q[0]
    env = dict(STMT.findall(body))
    cur = var
    while not env[cur].isdigit():
        cur = env[cur]
    return text, env, var, cur


def counterfactual(x: torch.Tensor, seed: int):
    """Same prompts with the queried chain's root digit changed."""
    rng = random.Random(seed)
    xs, ys = [], []
    for row in x:
        text, env, _, root = parse(row)
        old = env[root]
        new = str(rng.choice([d for d in range(10) if str(d) != old]))
        body, tail = text.split("|")
        body = body.replace(f"{root}={old};", f"{root}={new};")
        tail = tail[:-1] + new
        xs.append(list((body + "|" + tail).encode()))
        ys.append(ord(new))
    return torch.tensor(xs, dtype=torch.long), torch.tensor(ys, dtype=torch.long)


def baselines(x: torch.Tensor, y: torch.Tensor) -> dict:
    """Answer-free reference accuracies on these samples."""
    root_guess, majority = 0.0, 0.0
    for row, ans in zip(x, y):
        _, env, _, _ = parse(row)
        roots = [v for v in env.values() if v.isdigit()]
        distinct = set(roots)
        a = chr(int(ans))
        root_guess += (a in distinct) / len(distinct)
        top = Counter(roots).most_common()
        best = [d for d, c in top if c == top[0][1]]
        majority += (a in best) / len(best)
    n = len(y)
    return {
        "uniform": 0.1,
        "random_root": root_guess / n,
        "majority_root": majority / n,
    }


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--hops", default="1,2,3,4,5,6,7,8,9,10,11,12")
    ap.add_argument("--n-loops", default="1,2,4,6,8,12,16,24")
    ap.add_argument("--n-per-hop", type=int, default=400)
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--data-seed", type=int, default=12345)
    ap.add_argument("--state-hops", type=int, default=8, help="hops for state stats")
    ap.add_argument("--threads", type=int, default=0, help="0 = torch default")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.threads:
        torch.set_num_threads(args.threads)
    hops_list = [int(h) for h in args.hops.split(",")]
    loops_list = [int(n) for n in args.n_loops.split(",")]

    data = cf = None
    with open(args.out, "a") as out:
        for path in args.ckpt:
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            readout = MECHS[ckpt["mech"]][1]
            model = OpenMythos(ckpt["cfg"])
            model.load_state_dict(ckpt["model"])
            model = apply_readout(model.eval(), readout)
            calls = {"n": 0, "rec": None}

            def hook(m, i, o, calls=calls):
                calls["n"] += 1
                if calls["rec"] is not None:
                    calls["rec"].append((i[0], o))  # (h_prev, h_new)

            model.recurrent.injection.register_forward_hook(hook)

            if data is None:  # same held-out samples for every checkpoint
                data, cf = {}, {}
                for hops in hops_list:
                    rng = random.Random(args.data_seed * 1000 + hops)
                    data[hops] = make_batch(
                        rng, args.n_per_hop, [hops], ckpt["n_statements"]
                    )
                    cf[hops] = counterfactual(data[hops][0], args.data_seed + hops)
                    out.write(
                        json.dumps(
                            {
                                "type": "baselines",
                                "hops": hops,
                                "n": args.n_per_hop,
                                **baselines(*data[hops]),
                            }
                        )
                        + "\n"
                    )

            def predict(x, n_loops, model=model, calls=calls):
                preds, loops_run, secs = [], 0.0, 0.0
                for i in range(0, len(x), args.batch_size):
                    xb = x[i : i + args.batch_size]
                    calls["n"] = 0
                    t0 = time.perf_counter()
                    logits = model(xb[:, :-1], n_loops=n_loops)[:, -1]
                    secs += time.perf_counter() - t0
                    preds.append(logits.argmax(-1))
                    loops_run += calls["n"] * len(xb)
                return torch.cat(preds), loops_run / len(x), secs

            for n_loops in loops_list:
                row = {
                    "type": "cell",
                    "ckpt": path,
                    "mech": ckpt["mech"],
                    "seed": ckpt["seed"],
                    "trained_max_loops": ckpt["cfg"].max_loop_iters,
                    "n_loops": n_loops,
                    "seq_tokens": data[hops_list[0]][0].shape[1] - 1,
                    "acc": {},
                    "cf_both": {},
                    "cf_follow": {},
                    "loops_run": {},
                    "loop_tokens": {},
                    "fwd_seconds": {},
                }
                for hops in hops_list:
                    x, y = data[hops]
                    p, run, secs = predict(x, n_loops)
                    xc, yc = cf[hops]
                    pc, _, _ = predict(xc, n_loops)
                    row["acc"][hops] = (p == y).float().mean().item()
                    row["cf_both"][hops] = ((p == y) & (pc == yc)).float().mean().item()
                    row["cf_follow"][hops] = (pc == yc).float().mean().item()
                    row["loops_run"][hops] = run
                    row["loop_tokens"][hops] = run * len(y) * row["seq_tokens"]
                    row["fwd_seconds"][hops] = secs

                # hidden-state evolution on the state-hops samples
                x, _ = data[args.state_hops]
                calls["rec"] = []
                model(x[:100, :-1], n_loops=n_loops)
                rec, calls["rec"] = calls["rec"], None
                row["h_rms_per_loop"] = [o.pow(2).mean().sqrt().item() for _, o in rec]
                row["rel_change_per_loop"] = [
                    ((o - i).norm() / i.norm()).item() for i, o in rec
                ]
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(
                    f"{ckpt['mech']:12s} s{ckpt['seed']} T={n_loops:<3d} "
                    + " ".join(f"{h}:{a:.2f}" for h, a in row["acc"].items()),
                    flush=True,
                )


if __name__ == "__main__":
    main()
