#!/usr/bin/env python3
"""
Materialize the fixed dev and test sets of every level, with both
counterfactuals, before any model is trained. Writes sets/<level>_<split>.jsonl
and sets/manifest.json (row counts, query-swap-eligible counts, sha256).

Each row: {"prompt", "answer", "root_swap": [prompt, answer],
           "query_swap": [prompt, answer] or null}
Prompts come from splits.dev_rng / test_rng; counterfactuals use their own
fixed RNG (CF_SEED[split] + level index), drawn row by row in file order, so
which rows are query-swap eligible and what each counterfactual is are fixed
here and never depend on model results.
"""

import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from levels import LEVELS, make_sample, query_swap, root_swap  # noqa: E402
from splits import N_DEV, N_TEST, _LEVEL_IDX, dev_rng, test_rng  # noqa: E402

CF_SEED = {"dev": 44_000, "test": 43_000}
OUT = os.path.join(HERE, "sets")


def build(level, split):
    rng = dev_rng(level) if split == "dev" else test_rng(level)
    n = N_DEV if split == "dev" else N_TEST
    cf_rng = random.Random(CF_SEED[split] + _LEVEL_IDX[level])
    rows = []
    for _ in range(n):
        p, a = make_sample(level, rng, "test")
        rs = root_swap(p, cf_rng)
        qs = query_swap(p, cf_rng)
        rows.append(
            {
                "prompt": p,
                "answer": a,
                "root_swap": list(rs),
                "query_swap": list(qs) if qs else None,
            }
        )
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {}
    for level in LEVELS:
        for split in ("dev", "test"):
            rows = build(level, split)
            path = os.path.join(OUT, f"{level}_{split}.jsonl")
            text = "".join(json.dumps(r) + "\n" for r in rows)
            with open(path, "w") as f:
                f.write(text)
            manifest[f"{level}_{split}"] = {
                "rows": len(rows),
                "query_swap_eligible": sum(r["query_swap"] is not None for r in rows),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
