#!/usr/bin/env python3
"""
Static validation of the Gate A task generators and fixed sets (no training).
Writes validation.json; exits non-zero on any hard failure.

1. Test distribution of every level (20,000 samples): hard checks, answer and
   root-position distributions, answer-free heuristics, oracle length bound.
2. C2 training distribution (1 and 2 hops mixed, 20,000 samples): the same
   hard checks reported separately for its 1-hop and 2-hop samples, the
   actual mix ratio, and per-hop query-swap availability.
3. Split overlap: training streams (3 seeds x 3000 x 64, training split)
   vs dev vs test.
4. Fixed sets (sets/*.jsonl from build_sets.py): every row and both
   counterfactuals re-checked; manifest hashes match the files.

Hard checks per sample: solver answer == generated answer; hop count as
expected; statement count; each variable assigned once; distinct roots;
root swap changes exactly one statement to a digit absent from the prompt
and the solver follows it; query swap keeps the prompt body, keeps the hop
count and the solver gives a different answer.

Heuristics (answer-free unless marked oracle):
    uniform_digit, random_root, first/last_digit_stmt,
    root_right_after_query_stmt, nearest_other_root_to_query_stmt
    rule_length_guess            random root among chains whose statement
                                 count equals the distribution's known hop
                                 count + 1 (uses only the prompt and the task
                                 rule, not the answer)
    mixture_bayes_length_guess   (C2) picks the chain-length class most likely
                                 to hold the query given the prompt's chain-
                                 length multiset, with probabilities estimated
                                 on the 1-2 hop training distribution
    oracle_same_length_class     upper bound that locates the queried chain
                                 through the answer; not an executable guess
"""

import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from levels import (  # noqa: E402
    LEVELS,
    N_STATEMENTS,
    STMT,
    make_sample,
    parse,
    query_swap,
    root_swap,
    solve,
)
from splits import N_DEV, N_TEST, dev_rng, test_rng, train_rng  # noqa: E402

N = 20000
STEPS, BS, SEEDS = 3000, 64, (1, 2, 3)
TEST_HOPS = {"A": 0, "B": 1, "C1": 1, "C2": 1}


def chi2(counts, k):
    n = sum(counts.values())
    e = n / k
    return sum((counts.get(i, 0) - e) ** 2 / e for i in range(k))


def chain_lengths(env):
    """root variable -> number of statements in its chain"""
    child = {v: k for k, v in env.items() if not v.isdigit()}
    out = {}
    for k, v in env.items():
        if v.isdigit():
            n, cur = 1, k
            while cur in child:
                cur = child[cur]
                n += 1
            out[k] = n
    return out


def check_cf(p, a, h, rs, qs, tag):
    out = []
    env, _ = parse(p)
    stmts = STMT.findall(p.split("|")[0])
    digits = {v for v in env.values() if v.isdigit()}
    p2, a2 = rs
    s2 = STMT.findall(p2.split("|")[0])
    env2, _ = parse(p2)
    d2 = [v for v in env2.values() if v.isdigit()]
    if (
        sum(x != y for x, y in zip(stmts, s2)) != 1
        or solve(p2)[0] != a2
        or a2 in digits
        or len(set(d2)) != len(d2)
    ):
        out.append((tag, "root_swap", p, p2))
    if qs is not None:
        p3, a3 = qs
        if p3.split("|")[0] != p.split("|")[0] or a3 == a or solve(p3) != (a3, h):
            out.append((tag, "query_swap", p, p3))
    return out


def check(level, p, a, exp_hops, rng, fail, tag):
    """Hard checks on one sample; returns whether a query swap was possible."""
    env, _ = parse(p)
    stmts = STMT.findall(p.split("|")[0])
    if len(stmts) != N_STATEMENTS[level] or len(env) != len(stmts):
        fail.append((tag, "statements", p))
    sol, h = solve(p)
    if sol != a or h != exp_hops:
        fail.append((tag, "solver", p, a, sol, h))
    digits = [v for v in env.values() if v.isdigit()]
    if len(set(digits)) != len(digits):
        fail.append((tag, "roots_not_distinct", p))
    qs = query_swap(p, rng)
    fail.extend(check_cf(p, a, h, root_swap(p, rng), qs, tag))
    return qs is not None


def heuristics(level, prompt, ans):
    body, q = prompt.split("|")
    stmts = STMT.findall(body)
    env = dict(stmts)
    roots = [(i, k, v) for i, (k, v) in enumerate(stmts) if v.isdigit()]
    digits = [v for _, _, v in roots]
    qpos = next(i for i, (k, _) in enumerate(stmts) if k == q[0])
    nxt = stmts[qpos + 1] if qpos + 1 < len(stmts) else None
    if nxt and nxt[1].isdigit():
        after = float(nxt[1] == ans)
    else:
        after = 1 / len(digits)
    others = [(i, v) for i, _, v in roots if i != qpos]
    if others:
        d = min(abs(i - qpos) for i, _ in others)
        near = [v for i, v in others if abs(i - qpos) == d]
        nearest = (ans in near) / len(near)
    else:
        nearest = 1 / len(digits)
    lens = chain_lengths(env)
    rule = [env[k] for k, n in lens.items() if n == TEST_HOPS[level] + 1]
    qroot = next(k for _, k, v in roots if v == ans)
    same = [k for k in lens if lens[k] == lens[qroot]]
    return {
        "uniform_digit": 0.1,
        "random_root": 1 / len(digits),
        "first_digit_stmt": float(digits[0] == ans),
        "last_digit_stmt": float(digits[-1] == ans),
        "root_right_after_query_stmt": after,
        "nearest_other_root_to_query_stmt": nearest,
        "rule_length_guess": (ans in rule) / len(rule) if rule else 1 / len(digits),
        "oracle_same_length_class": 1 / len(same),
    }


def query_chain_len(prompt):
    env, cur = parse(prompt)
    n = 1
    while not env[cur].isdigit():
        cur = env[cur]
        n += 1
    return n


def main():
    rep, fail = {"levels": {}}, []

    for level in LEVELS:
        rng = random.Random(7)
        H, ans_c, pos_c, qs_avail = Counter(), Counter(), Counter(), 0
        for _ in range(N):
            p, a = make_sample(level, rng, "test")
            qs_avail += check(level, p, a, TEST_HOPS[level], rng, fail, f"{level}/test")
            env, _ = parse(p)
            stmts = STMT.findall(p.split("|")[0])
            ans_c[int(a)] += 1
            rv = next(k for k, v in env.items() if v == a)
            pos_c[[k for k, _ in stmts].index(rv)] += 1
            for k, v in heuristics(level, p, a).items():
                H[k] += v
        k = N_STATEMENTS[level]
        rep["levels"][level] = {
            "seq_len": len(p) + 1,
            "statements": k,
            "test_hops": TEST_HOPS[level],
            "answer_digit_chi2_df9": round(chi2(ans_c, 10), 2),
            f"root_position_chi2_df{k - 1}": round(chi2(pos_c, k), 2),
            "query_swap_available": round(qs_avail / N, 4),
            "heuristic_acc_test_distribution": {
                kk: round(v / N, 4) for kk, v in H.items()
            },
        }

    # C2 training distribution, 1 and 2 hops checked separately
    rng = random.Random(9)
    by_hop = defaultdict(lambda: {"n": 0, "query_swap_available": 0})
    table = defaultdict(Counter)  # chain-length multiset -> Counter(query chain length)
    for _ in range(N):
        p, a = make_sample("C2", rng, "train")
        h = solve(p)[1]
        by_hop[h]["n"] += 1
        by_hop[h]["query_swap_available"] += check(
            "C2", p, a, h, rng, fail, f"C2/train/{h}hop"
        )
        env, _ = parse(p)
        table[tuple(sorted(chain_lengths(env).values()))][query_chain_len(p)] += 1
    rep["C2_training_distribution"] = {
        f"{h}_hop": {
            "n": d["n"],
            "fraction": round(d["n"] / N, 4),
            "query_swap_available": round(d["query_swap_available"] / d["n"], 4),
        }
        for h, d in sorted(by_hop.items())
    }
    if set(by_hop) != {1, 2}:
        fail.append(("C2/train", "hop_mix", sorted(by_hop)))

    # mixture-Bayes length guess, evaluated on the 1-hop test distribution
    rng, s = random.Random(10), 0.0
    for _ in range(N):
        p, a = make_sample("C2", rng, "test")
        env, _ = parse(p)
        lens = chain_lengths(env)
        M = tuple(sorted(lens.values()))
        cnt = Counter(lens.values())
        best = max(cnt, key=lambda L: table[M][L] / cnt[L])
        cand = [env[kk] for kk, n in lens.items() if n == best]
        s += (a in cand) / len(cand)
    rep["levels"]["C2"]["heuristic_acc_test_distribution"][
        "mixture_bayes_length_guess"
    ] = round(s / N, 4)
    rng, eq = random.Random(8), 0
    for _ in range(N):
        p, _ = make_sample("C2", rng, "test")
        env, _ = parse(p)
        eq += len(set(chain_lengths(env).values())) == 1
    rep["levels"]["C2"]["equal_length_fraction_of_test"] = round(eq / N, 4)

    # split overlap
    for level in LEVELS:
        r = dev_rng(level)
        dev = {make_sample(level, r, "test")[0] for _ in range(N_DEV)}
        r = test_rng(level)
        test = {make_sample(level, r, "test")[0] for _ in range(N_TEST)}
        train = set()
        for s_ in SEEDS:
            r = train_rng(level, s_)
            train |= {make_sample(level, r, "train")[0] for _ in range(STEPS * BS)}
        ov = {
            "train_unique": len(train),
            "train∩dev": len(train & dev),
            "train∩test": len(train & test),
            "dev∩test": len(dev & test),
        }
        rep["levels"][level]["overlap"] = ov
        for kk in ("train∩dev", "train∩test", "dev∩test"):
            if ov[kk]:
                fail.append((level, "overlap", kk, ov[kk]))

    # fixed sets
    sets_dir = os.path.join(HERE, "sets")
    manifest = json.load(open(os.path.join(sets_dir, "manifest.json")))
    for name, meta in manifest.items():
        level = name.split("_")[0]
        text = open(os.path.join(sets_dir, f"{name}.jsonl")).read()
        if hashlib.sha256(text.encode()).hexdigest() != meta["sha256"]:
            fail.append((name, "hash"))
        rows = [json.loads(line) for line in text.splitlines()]
        for row in rows:
            p, a = row["prompt"], row["answer"]
            if solve(p) != (a, TEST_HOPS[level]):
                fail.append((name, "solver", p))
            qs = tuple(row["query_swap"]) if row["query_swap"] else None
            fail.extend(
                check_cf(p, a, TEST_HOPS[level], tuple(row["root_swap"]), qs, name)
            )
        meta["checked_rows"] = len(rows)
    rep["fixed_sets"] = manifest

    rep["hard_failures"] = len(fail)
    rep["examples_of_failures"] = [str(f) for f in fail[:5]]
    with open(os.path.join(HERE, "validation.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
