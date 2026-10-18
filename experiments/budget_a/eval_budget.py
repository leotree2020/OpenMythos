#!/usr/bin/env python3
"""
Evaluate the final (step 12,000) checkpoints of the level-A training-budget
diagnostic on the new test set sets/A_test2.jsonl (hash checked against
sets/manifest.json). Intermediate checkpoints are evaluated on the dev set
only (--split dev). OpenMythos is judged at T=4; T=1, 2, 8 informational.

Per checkpoint and depth: accuracy with Wilson 95% CI, root-swap and
query-swap both-correct rates (with CIs), query insensitivity (prediction
unchanged when only the query changes), root-swap follow rate,
prediction-in-roots. A "baselines" row gives the answer-free heuristics.
"""

import argparse
import hashlib
import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
GA = os.path.join(HERE, "..", "gen_gate_a")
sys.path.insert(0, GA)
sys.path.append(os.path.join(HERE, "..", "basic_learn"))

from data import encode_rows, load_set, roots_of  # noqa: E402
from eval_level import wilson  # noqa: E402
from models import build  # noqa: E402
from validate import heuristics  # noqa: E402


def load_test2():
    text = open(os.path.join(HERE, "sets", "A_test2.jsonl")).read()
    want = json.load(open(os.path.join(HERE, "sets", "manifest.json")))["A_test2"][
        "sha256"
    ]
    sha = hashlib.sha256(text.encode()).hexdigest()
    if sha != want:
        raise RuntimeError("A_test2 does not match its manifest hash")
    rows = [json.loads(l) for l in text.splitlines()]
    x, y = encode_rows([(r["prompt"], r["answer"]) for r in rows])
    x_rs, y_rs = encode_rows([tuple(r["root_swap"]) for r in rows])
    qs_idx = [i for i, r in enumerate(rows) if r["query_swap"]]
    x_qs, y_qs = encode_rows([tuple(rows[i]["query_swap"]) for i in qs_idx])
    return {
        "rows": rows,
        "x": x,
        "y": y,
        "x_rs": x_rs,
        "y_rs": y_rs,
        "qs_idx": torch.tensor(qs_idx),
        "x_qs": x_qs,
        "y_qs": y_qs,
        "roots": [roots_of(r["prompt"]) for r in rows],
        "sha256": sha,
    }


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--split", default="test2", choices=["test2", "dev"])
    ap.add_argument("--om-loops", default="4,1,2,8")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ds = load_test2() if args.split == "test2" else load_set("A", "dev")
    rows = ds["rows"]
    with open(args.out, "a") as out:
        hs = [heuristics("A", r["prompt"], r["answer"]) for r in rows]
        out.write(
            json.dumps(
                {
                    "type": "baselines",
                    "split": args.split,
                    "set_sha256": ds["sha256"],
                    "n": len(rows),
                    **{k: sum(h[k] for h in hs) / len(hs) for k in hs[0]},
                }
            )
            + "\n"
        )
        for path in args.ckpt:
            ck = torch.load(path, map_location="cpu", weights_only=False)
            model = build(ck["arm"], 4)
            model.load_state_dict(ck["model"])
            model.eval()
            for T in (
                [int(t) for t in args.om_loops.split(",")]
                if ck["arm"] == "openmythos"
                else [None]
            ):
                f = lambda x: model(x[:, :-1], n_loops=T)[:, -1].argmax(
                    -1
                )  # noqa: E731
                p, pr, pq = f(ds["x"]), f(ds["x_rs"]), f(ds["x_qs"])
                ok = p == ds["y"]
                rs_both = ok & (pr == ds["y_rs"])
                qs_both = ok[ds["qs_idx"]] & (pq == ds["y_qs"])
                row = {
                    "type": "cell",
                    "split": args.split,
                    "ckpt": path,
                    "arm": ck["arm"],
                    "seed": ck["seed"],
                    "step": ck.get("step", "final"),
                    "n_loops": T,
                    "n": len(rows),
                    "acc": ok.float().mean().item(),
                    "acc_ci95": wilson(int(ok.sum()), len(rows)),
                    "root_swap_both": rs_both.float().mean().item(),
                    "root_swap_both_ci95": wilson(int(rs_both.sum()), len(rows)),
                    "query_swap_both": qs_both.float().mean().item(),
                    "query_swap_both_ci95": wilson(int(qs_both.sum()), len(qs_both)),
                    "query_insensitivity": (p[ds["qs_idx"]] == pq)
                    .float()
                    .mean()
                    .item(),
                    "root_swap_follow": (pr == ds["y_rs"]).float().mean().item(),
                    "pred_in_roots": sum(int(a) in c for a, c in zip(p, ds["roots"]))
                    / len(rows),
                }
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(
                    f"{ck['arm']:11s} s{ck['seed']} step {row['step']} T={T} acc {row['acc']:.3f} "
                    f"qs {row['query_swap_both']:.3f} insens {row['query_insensitivity']:.3f}"
                )


if __name__ == "__main__":
    main()
