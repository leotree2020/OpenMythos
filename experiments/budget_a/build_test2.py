#!/usr/bin/env python3
"""
Build and validate the new, independent level-A test set for the training-
budget diagnostic (no training). The Gate A level-A test set has already
been analysed and is not used for this round's confirmatory decision.

Writes sets/A_test2.jsonl (+ manifest.json) with the same row format as
gen_gate_a/build_sets.py: prompts from Random(45000), counterfactuals from
Random(46000), drawn row by row. Then checks every row and both
counterfactuals, and that no prompt is shared with the Gate A level-A test
and dev sets or with the extended training streams (seeds 1-3, 12000 steps
x 64). Writes validation_test2.json; exits non-zero on any failure.
"""

import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GA = os.path.join(HERE, "..", "gen_gate_a")
sys.path.insert(0, GA)

from levels import make_sample, query_swap, root_swap, solve  # noqa: E402
from splits import train_rng  # noqa: E402
from validate import check_cf, heuristics  # noqa: E402

N_TEST, PROMPT_SEED, CF_SEED = 1000, 45_000, 46_000
MAX_STEPS, BS, SEEDS = 12_000, 64, (1, 2, 3)


def main():
    rng, cf = random.Random(PROMPT_SEED), random.Random(CF_SEED)
    rows = []
    for _ in range(N_TEST):
        p, a = make_sample("A", rng, "test")
        rs, qs = root_swap(p, cf), query_swap(p, cf)
        rows.append(
            {
                "prompt": p,
                "answer": a,
                "root_swap": list(rs),
                "query_swap": list(qs) if qs else None,
            }
        )
    os.makedirs(os.path.join(HERE, "sets"), exist_ok=True)
    text = "".join(json.dumps(r) + "\n" for r in rows)
    with open(os.path.join(HERE, "sets", "A_test2.jsonl"), "w") as f:
        f.write(text)
    sha = hashlib.sha256(text.encode()).hexdigest()
    with open(os.path.join(HERE, "sets", "manifest.json"), "w") as f:
        json.dump(
            {
                "A_test2": {
                    "rows": len(rows),
                    "sha256": sha,
                    "query_swap_eligible": sum(
                        r["query_swap"] is not None for r in rows
                    ),
                }
            },
            f,
            indent=1,
        )

    fail = []
    for r in rows:
        p, a = r["prompt"], r["answer"]
        if solve(p) != (a, 0):
            fail.append(("solver", p))
        qs = tuple(r["query_swap"]) if r["query_swap"] else None
        fail.extend(check_cf(p, a, 0, tuple(r["root_swap"]), qs, "A_test2"))
    new = {r["prompt"] for r in rows}
    old = {}
    for name in ("A_test", "A_dev"):
        old[name] = {
            json.loads(l)["prompt"]
            for l in open(os.path.join(GA, "sets", f"{name}.jsonl"))
        }
    train = set()
    for s in SEEDS:
        tr = train_rng("A", s)
        train |= {make_sample("A", tr, "train")[0] for _ in range(MAX_STEPS * BS)}
    ov = {
        "test2_unique": len(new),
        "test2∩A_test": len(new & old["A_test"]),
        "test2∩A_dev": len(new & old["A_dev"]),
        "test2∩train_12000": len(new & train),
        "train_12000_unique": len(train),
        "A_dev∩train_12000": len(old["A_dev"] & train),
    }
    for k in ("test2∩A_test", "test2∩A_dev", "test2∩train_12000", "A_dev∩train_12000"):
        if ov[k]:
            fail.append(("overlap", k, ov[k]))
    if len(new) != N_TEST:
        fail.append(("duplicate prompts in test2", N_TEST - len(new)))
    hs = [heuristics("A", r["prompt"], r["answer"]) for r in rows]
    rep = {
        "sha256": sha,
        "rows": len(rows),
        "query_swap_eligible": sum(r["query_swap"] is not None for r in rows),
        "overlap": ov,
        "heuristic_acc": {k: round(sum(h[k] for h in hs) / len(hs), 4) for k in hs[0]},
        "hard_failures": len(fail),
        "examples": [str(x) for x in fail[:3]],
    }
    with open(os.path.join(HERE, "validation_test2.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
