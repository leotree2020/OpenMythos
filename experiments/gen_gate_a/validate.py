#!/usr/bin/env python3
"""
Static validation of the Gate A task generators (no training).
Writes validation.json; exits non-zero on any hard failure.

Per level, on 20,000 generated samples:
  hard checks   solver answer == generated answer; hop count (A: 0, else 1);
                distinct root digits; each variable assigned once; statement
                count; root swap changes exactly one statement to an absent
                digit and the solver follows it; query swap changes only the
                query, keeps the hop count and the solver gives a different
                answer
  distributions answer digit and queried-root position (chi-square)
  heuristics    answer-free strategies: uniform digit; random root; first /
                last digit statement; root statement right after the query's
                own statement; root nearest to the query's statement; random
                root among chains of the queried chain's length class
                (length cue; only informative when lengths differ)
  splits        no prompt shared between the training streams (3 seeds x
                3000 x 64), the dev set and the test set
"""

import json
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from levels import (  # noqa: E402
    LEVELS,
    N_STATEMENTS,
    STMT,
    chain_ends,
    make_sample,
    parse,
    query_swap,
    root_swap,
    solve,
)
from splits import dev_rng, test_rng, train_rng, N_DEV, N_TEST  # noqa: E402

N = 20000
STEPS, BS, SEEDS = 3000, 64, (1, 2, 3)


def chi2(counts, k):
    n = sum(counts.values())
    e = n / k
    return sum((counts.get(i, 0) - e) ** 2 / e for i in range(k))


def chain_len(env, root_var):
    child = {v: k for k, v in env.items() if not v.isdigit()}
    n, cur = 1, root_var
    while cur in child:
        cur = child[cur]
        n += 1
    return n


def heuristics(prompt, ans):
    body, q = prompt.split("|")
    stmts = STMT.findall(body)
    env = dict(stmts)
    roots = [(i, k, v) for i, (k, v) in enumerate(stmts) if v.isdigit()]
    digits = [v for _, _, v in roots]
    qpos = next(i for i, (k, _) in enumerate(stmts) if k == q[0])
    nxt = stmts[qpos + 1] if qpos + 1 < len(stmts) else None
    after = (
        1.0
        if nxt and nxt[1].isdigit() and nxt[1] == ans
        else (0.0 if nxt and nxt[1].isdigit() else 1 / len(digits))
    )
    others = [(i, v) for i, _, v in roots if i != qpos]
    if others:
        d = min(abs(i - qpos) for i, _ in others)
        near = [v for i, v in others if abs(i - qpos) == d]
        nearest = (ans in near) / len(near)
    else:
        nearest = 1 / len(digits)
    lens = {k: chain_len(env, k) for _, k, _ in roots}
    qroot = next(k for _, k, v in roots if v == ans)
    same = [k for k in lens if lens[k] == lens[qroot]]
    return {
        "uniform_digit": 0.1,
        "random_root": 1 / len(digits),
        "first_digit_stmt": float(digits[0] == ans),
        "last_digit_stmt": float(digits[-1] == ans),
        "root_right_after_query_stmt": after,
        "nearest_other_root_to_query_stmt": nearest,
        "random_root_same_length_class": 1 / len(same),
    }


def main():
    rep, fail = {"levels": {}}, []
    for level in LEVELS:
        rng = random.Random(7)
        H, ans_c, pos_c, qs_avail = Counter(), Counter(), Counter(), 0
        exp_hops = 0 if level == "A" else 1
        for _ in range(N):
            p, a = make_sample(level, rng)
            env, q = parse(p)
            stmts = STMT.findall(p.split("|")[0])
            if len(stmts) != N_STATEMENTS[level] or len(env) != len(stmts):
                fail.append((level, "statements", p))
            sol, h = solve(p)
            if sol != a or h != exp_hops:
                fail.append((level, "solver", p, a, sol, h))
            digits = [v for v in env.values() if v.isdigit()]
            if len(set(digits)) != len(digits):
                fail.append((level, "roots_not_distinct", p))
            ans_c[int(a)] += 1
            rv = next(k for k, v in env.items() if v == a)
            pos_c[[k for k, _ in stmts].index(rv)] += 1
            for k, v in heuristics(p, a).items():
                H[k] += v
            # root swap
            p2, a2 = root_swap(p, rng)
            s2 = STMT.findall(p2.split("|")[0])
            diff = sum(x != y for x, y in zip(stmts, s2))
            if diff != 1 or solve(p2)[0] != a2 or a2 in digits:
                fail.append((level, "root_swap", p, p2))
            # query swap
            qs = query_swap(p, rng)
            if qs is not None:
                qs_avail += 1
                p3, a3 = qs
                if (
                    p3.split("|")[0] != p.split("|")[0]
                    or a3 == a
                    or solve(p3) != (a3, h)
                ):
                    fail.append((level, "query_swap", p, p3))
        rep["levels"][level] = {
            "seq_len": len(p) + 1,
            "statements": N_STATEMENTS[level],
            "answer_digit_chi2_df9": round(chi2(ans_c, 10), 2),
            "root_position_chi2_df%d"
            % (N_STATEMENTS[level] - 1): round(chi2(pos_c, N_STATEMENTS[level]), 2),
            "query_swap_available": round(qs_avail / N, 4),
            "heuristic_acc": {k: round(v / N, 4) for k, v in H.items()},
        }

        # split overlap
        def prompts(r, n):
            return {make_sample(level, r)[0] for _ in range(n)}

        dev, test = prompts(dev_rng(level), N_DEV), prompts(test_rng(level), N_TEST)
        train = set()
        for s in SEEDS:
            r = train_rng(level, s)
            train |= {make_sample(level, r, "train")[0] for _ in range(STEPS * BS)}
        ov = {
            "train_unique": len(train),
            "train∩dev": len(train & dev),
            "train∩test": len(train & test),
            "dev∩test": len(dev & test),
        }
        if level == "C2":
            # equal-length subset of the 1-hop test distribution (no length cue)
            r, eq = random.Random(8), 0
            for _ in range(N):
                p, _ = make_sample(level, r)
                env, _ = parse(p)
                lens = {chain_len(env, k) for k, v in env.items() if v.isdigit()}
                eq += len(lens) == 1
            rep["levels"][level]["equal_length_fraction_of_test"] = round(eq / N, 4)
        rep["levels"][level]["overlap"] = ov
        for k in ("train∩dev", "train∩test", "dev∩test"):
            if ov[k]:
                fail.append((level, "overlap", k, ov[k]))

    rep["hard_failures"] = len(fail)
    rep["examples_of_failures"] = [str(f) for f in fail[:5]]
    with open(os.path.join(HERE, "validation.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
