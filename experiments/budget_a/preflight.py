#!/usr/bin/env python3
"""
Pre-training checks for the level-A training-budget diagnostic (no training).

1. Schedule: extended_lr equals the Gate A get_lr on steps 0-2999 and is
   2e-4 afterwards; train_level.py uses it only with --schedule extended.
2. Training data: for each formal seed, the first training batch hash equals
   the one recorded by the Gate A level-A run (same stream, both arms).
3. Reference checkpoints: the six Gate A level-A checkpoints used by the
   step-3000 comparability check exist, load, and their sha256 is recorded.
4. Test set: A_test2 loads and matches its manifest hash.
5. Verdict logic: analyze_budget.level_of on hand-made rows covers each
   category, including the case "high accuracy but query-insensitive".
"""

import hashlib
import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
GA = os.path.join(HERE, "..", "gen_gate_a")
sys.path.insert(0, HERE)
sys.path.insert(1, GA)
sys.path.append(os.path.join(HERE, "..", "memorize"))

from analyze_budget import level_of  # noqa: E402
from data import encode_rows  # noqa: E402
from eval_budget import load_test2  # noqa: E402
from levels import make_sample  # noqa: E402
from schedule import extended_lr  # noqa: E402
from splits import train_rng  # noqa: E402
from train_mem import get_lr  # noqa: E402


def main():
    rep, fail = {}, []
    if any(get_lr(s, 100, 3000, 2e-3) != extended_lr(s) for s in range(3000)):
        fail.append("schedule differs before step 3000")
    if any(extended_lr(s) != 2e-4 for s in range(3000, 12000)):
        fail.append("schedule not constant after step 3000")
    src = open(os.path.join(GA, "train_level.py")).read()
    if 'if args.schedule == "extended":' not in src or 'default="cosine"' not in src:
        fail.append("train_level.py schedule switch not found")
    rep["schedule"] = "ok"

    rep["first_batch"] = {}
    rep["reference_ckpts"] = {}
    for seed in (1, 2, 3):
        r = train_rng("A", seed)
        x, _ = encode_rows([make_sample("A", r, "train") for _ in range(64)])
        sha = hashlib.sha256(x.numpy().tobytes()).hexdigest()
        for arm in ("openmythos", "transformer"):
            rec = json.load(open(os.path.join(GA, "runs", f"A_{arm}_s{seed}.json")))
            same = rec["first_batch_sha256"] == sha
            rep["first_batch"][f"{arm}_s{seed}"] = {
                "sha": sha[:12],
                "matches_gate_a": same,
            }
            if not same:
                fail.append(f"first batch differs {arm} s{seed}")
            path = os.path.join(GA, "runs", f"A_{arm}_s{seed}.pt")
            ck = torch.load(path, map_location="cpu", weights_only=False)
            if ck["arm"] != arm or ck["seed"] != seed or ck["level"] != "A":
                fail.append(f"reference ckpt metadata {path}")
            rep["reference_ckpts"][f"{arm}_s{seed}"] = hashlib.sha256(
                open(path, "rb").read()
            ).hexdigest()[:16]

    ds = load_test2()
    rep["test2"] = {"rows": len(ds["rows"]), "sha256": ds["sha256"][:16]}

    base = 0.25
    cases = {
        "learned": (
            {
                "acc": 0.95,
                "acc_ci95": [0.93, 0.96],
                "root_swap_both": 0.9,
                "query_swap_both": 0.9,
                "query_insensitivity": 0.05,
            },
            "学会",
        ),
        "signs": (
            {
                "acc": 0.5,
                "acc_ci95": [0.47, 0.53],
                "root_swap_both": 0.3,
                "query_swap_both": 0.3,
                "query_insensitivity": 0.4,
            },
            "出现学习迹象",
        ),
        "accurate_but_query_insensitive": (
            {
                "acc": 0.7,
                "acc_ci95": [0.67, 0.73],
                "root_swap_both": 0.5,
                "query_swap_both": 0.05,
                "query_insensitivity": 0.92,
            },
            "未满足综合学习迹象标准",
        ),
        "chance": (
            {
                "acc": 0.25,
                "acc_ci95": [0.22, 0.28],
                "root_swap_both": 0.08,
                "query_swap_both": 0.0,
                "query_insensitivity": 0.99,
            },
            "未满足综合学习迹象标准",
        ),
    }
    rep["verdict_logic"] = {}
    for name, (row, want) in cases.items():
        got = level_of(row, base)
        rep["verdict_logic"][name] = got
        if got != want:
            fail.append(f"verdict {name}: {got} != {want}")

    rep["failures"] = fail
    with open(os.path.join(HERE, "preflight.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
