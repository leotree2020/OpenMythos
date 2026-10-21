#!/usr/bin/env python3
"""
Validity checks for task_v2 before any training. Writes validation.json and
prints a report; exits non-zero if a hard check fails.

Hard checks (must hold on every sample):
    - the independent solver's answer equals the generated answer
    - the queried chain has exactly `hops` links
    - every variable is assigned exactly once; every chain ends in a digit
    - root digits are distinct within a prompt
    - counterfactual: exactly one statement changes, the solver returns the
      new digit, the new digit was absent from the original prompt, and roots
      stay distinct
    - no prompt is shared between the training streams (seeds 1-3), the
      learning-curve probe set and the test set

Distribution checks (reported with a chi-square statistic):
    - answer digit uniform over 0-9
    - position of the queried root statement uniform over the 8 slots

Heuristic baselines (answer-free strategies a model could pick up instead of
following the chain), per hop count:
    random root, most frequent root, first / last digit statement in the
    prompt, root of the longest chain, root statement nearest to the query
    variable's own statement, and an oracle "follow one link then guess"
"""

import json
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from task_v2 import STMT, counterfactual, make_batch, make_sample, solve  # noqa: E402

N_STMT = 8
TRAIN_STEPS, TRAIN_BS, SEEDS = 3000, 64, (1, 2, 3)
PROBE_SEED, TEST_SEED = 777, 24680


def chains_of(env):
    """Map each root var to its chain length (#statements)."""
    child = {v: k for k, v in env.items() if not v.isdigit()}
    out = {}
    for var, val in env.items():
        if val.isdigit():
            n, cur = 1, var
            while cur in child:
                cur = child[cur]
                n += 1
            out[var] = n
    return out


def chi2(counts, k):
    n = sum(counts.values())
    e = n / k
    return sum((counts.get(i, 0) - e) ** 2 / e for i in range(k))


def heuristics(prompt, ans, rng):
    body, q = prompt.split("|")
    stmts = STMT.findall(body)
    env = dict(stmts)
    roots = [(i, k, v) for i, (k, v) in enumerate(stmts) if v.isdigit()]
    digits = [v for _, _, v in roots]
    lens = chains_of(env)
    longest = max(lens.values())
    qpos = next(i for i, (k, _) in enumerate(stmts) if k == q[0])
    near = min(abs(i - qpos) for i, _, _ in roots)
    nearest = [v for i, _, v in roots if abs(i - qpos) == near]
    one = env[q[0]]
    return {
        "random_root": 1 / len(digits),
        "majority_root": 1 / len(digits),  # all roots distinct: every digit ties
        "first_digit_stmt": float(digits[0] == ans),
        "last_digit_stmt": float(digits[-1] == ans),
        "longest_chain_root": sum(
            1 for k, v in env.items() if v.isdigit() and lens[k] == longest and v == ans
        )
        / sum(1 for k in lens if lens[k] == longest),
        "nearest_root_to_query_stmt": (ans in nearest) / len(nearest),
        "one_link_then_guess": 1.0 if one.isdigit() else 1 / len(digits),
    }


def main():
    rep = {"hard_failures": [], "per_hops": {}}
    fail = rep["hard_failures"]
    rng = random.Random(0)
    for hops in (1, 2, 3, 4):
        H, ans_c, pos_c, n_chains = Counter(), Counter(), Counter(), Counter()
        N = 20000
        for _ in range(N):
            prompt, ans = make_sample(rng, hops, N_STMT)
            body = prompt.split("|")[0]
            stmts = STMT.findall(body)
            env = dict(stmts)
            if len(env) != len(stmts) or len(stmts) != N_STMT:
                fail.append(("duplicate_or_count", prompt))
            sol, h = solve(prompt)
            if sol != ans or h != hops:
                fail.append(("solver", prompt, ans, sol, h))
            digits = [v for v in env.values() if v.isdigit()]
            if len(set(digits)) != len(digits):
                fail.append(("roots_not_distinct", prompt))
            n_chains[len(digits)] += 1
            ans_c[int(ans)] += 1
            root_var = next(k for k, v in env.items() if v == ans)
            pos_c[[k for k, _ in stmts].index(root_var)] += 1
            for k, v in heuristics(prompt, ans, rng).items():
                H[k] += v
        rep["per_hops"][hops] = {
            "n": N,
            "chains_hist": dict(sorted(n_chains.items())),
            "answer_digit_chi2_df9": round(chi2(ans_c, 10), 2),
            "root_position_chi2_df7": round(chi2(pos_c, N_STMT), 2),
            "heuristic_acc": {k: round(v / N, 4) for k, v in H.items()},
        }

    # counterfactual validity
    for hops in (1, 2, 3, 4):
        x, y = make_batch(random.Random(TEST_SEED + hops), 2000, [hops], N_STMT)
        xc, yc = counterfactual(x, TEST_SEED + 50 + hops)
        for a, b, ya, yb in zip(x, xc, y, yc):
            ta, tb = bytes(a.tolist()).decode(), bytes(b.tolist()).decode()
            pa, pb = ta[:-1], tb[:-1]
            sa, sb = STMT.findall(pa.split("|")[0]), STMT.findall(pb.split("|")[0])
            diff = [i for i, (u, v) in enumerate(zip(sa, sb)) if u != v]
            env_a, env_b = dict(sa), dict(sb)
            new = chr(int(yb))
            ok = (
                len(diff) == 1
                and solve(pb)[0] == new
                and new != chr(int(ya))
                and new not in env_a.values()
                and len({v for v in env_b.values() if v.isdigit()})
                == sum(v.isdigit() for v in env_b.values())
            )
            if not ok:
                fail.append(("counterfactual", ta, tb))

    # split overlap
    train = set()
    for s in SEEDS:
        r = random.Random(10_000 + s)
        for _ in range(TRAIN_STEPS):
            x, _ = make_batch(r, TRAIN_BS, [1, 2], N_STMT)
            train.update(bytes(row[:-1].tolist()) for row in x)
    probe = set()
    for h in (1, 2):
        x, _ = make_batch(random.Random(PROBE_SEED + h), 200, [h], N_STMT)
        probe.update(bytes(row[:-1].tolist()) for row in x)
    test = set()
    for h in (1, 2, 3, 4):
        x, _ = make_batch(random.Random(TEST_SEED + h), 500, [h], N_STMT)
        test.update(bytes(row[:-1].tolist()) for row in x)
    rep["overlap"] = {
        "train_unique_prompts": len(train),
        "train∩test": len(train & test),
        "train∩probe": len(train & probe),
        "probe∩test": len(probe & test),
    }
    for k in ("train∩test", "train∩probe", "probe∩test"):
        if rep["overlap"][k]:
            fail.append(("overlap", k, rep["overlap"][k]))

    with open(os.path.join(HERE, "validation.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(
        json.dumps(
            {k: v for k, v in rep.items() if k != "hard_failures"},
            indent=1,
            ensure_ascii=False,
        )
    )
    print("hard failures:", len(fail), fail[:3])
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
