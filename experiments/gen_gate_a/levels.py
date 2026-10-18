"""
Task levels for Generalization Gate A. All share the byte format of the
earlier experiments ("a=7;b=a;...|b?7"); every chain in a prompt has a
different root digit; statement order is always shuffled.

    A   direct lookup     K=4 statements "v=d;", query one variable.
                          Chance among digits present = 1/4.
    B   simplest 1-hop    2 chains of exactly 2 statements ("a=b;b=3;"),
                          query the end of one. Equal chain lengths, so
                          length carries no information. Chance 1/2.
    C1  1-hop, more       4 chains of exactly 2 statements (8 statements).
        distractors       Chance 1/4.
    C2  full Basic Learn  experiments/basic_learn/task_v2.py (8 statements,
        1-hop             distractor chains of 2-3 statements). Trained on
                          1-2 hops as in Basic Learn, tested on 1 hop.
                          Training on 1 hop alone would make chain length a
                          shortcut (validate.py: 62.5% by guessing among
                          2-statement chains); mixing 1 and 2 hops removes it
                          at the training-distribution level, as in Basic
                          Learn. Chance on the 1-hop test ≈ 0.29.

Counterfactuals (for every level):
    root swap   the queried chain's root digit is replaced by a digit absent
                from the prompt; the answer must follow it
    query swap  the query is moved to the end of another chain with the same
                hop count; the answer must become that chain's root
"""

import random
import re
import string
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "..", "basic_learn"))

import task_v2  # noqa: E402

VARS = string.ascii_letters
STMT = re.compile(r"([A-Za-z])=([A-Za-z0-9]);")
LEVELS = ("A", "B", "C1", "C2")
N_STATEMENTS = {"A": 4, "B": 4, "C1": 8, "C2": 8}


def _chains_prompt(rng, lengths):
    """Chains with the given statement counts; the first chain is queried."""
    names = rng.sample(VARS, sum(lengths))
    chains, i = [], 0
    for L in lengths:
        chains.append(names[i : i + L])
        i += L
    roots = rng.sample("0123456789", len(chains))
    stmts = []
    for chain, root in zip(chains, roots):
        stmts.append(f"{chain[0]}={root};")
        for prev, cur in zip(chain, chain[1:]):
            stmts.append(f"{cur}={prev};")
    rng.shuffle(stmts)
    return "".join(stmts) + f"|{chains[0][-1]}?", roots[0]


def make_sample(level: str, rng: random.Random, split: str = "test"):
    """Return (prompt ending in '?', answer digit). For C2 the training split
    draws 1 or 2 hops; every other level and split is as described above."""
    if level == "A":
        return _chains_prompt(rng, [1, 1, 1, 1])
    if level == "B":
        return _chains_prompt(rng, [2, 2])
    if level == "C1":
        return _chains_prompt(rng, [2, 2, 2, 2])
    if level == "C2":
        hops = rng.choice([1, 2]) if split == "train" else 1
        return task_v2.make_sample(rng, hops, 8)
    raise ValueError(level)


def parse(prompt: str):
    body, q = prompt.split("|")
    return dict(STMT.findall(body)), q[0]


def solve(prompt: str):
    """Independent solver: follow assignments from the query. Returns (digit, hops)."""
    env, cur = parse(prompt)
    hops = 0
    while not env[cur].isdigit():
        cur = env[cur]
        hops += 1
    return env[cur], hops


def chain_ends(env):
    """Variables that no other statement refers to (the end of each chain)."""
    referenced = {v for v in env.values() if not v.isdigit()}
    return [k for k in env if k not in referenced]


def root_swap(prompt: str, rng: random.Random):
    env, q = parse(prompt)
    cur = q
    while not env[cur].isdigit():
        cur = env[cur]
    present = {v for v in env.values() if v.isdigit()}
    new = rng.choice([d for d in "0123456789" if d not in present])
    body = prompt.split("|")[0].replace(f"{cur}={env[cur]};", f"{cur}={new};")
    return body + "|" + q + "?", new


def query_swap(prompt: str, rng: random.Random):
    """Move the query to another chain end with the same hop count, or None."""
    env, q = parse(prompt)
    _, hops = solve(prompt)
    body = prompt.split("|")[0]
    alts = [e for e in chain_ends(env) if e != q and solve(body + f"|{e}?")[1] == hops]
    if not alts:
        return None
    e = rng.choice(alts)
    p = body + f"|{e}?"
    return p, solve(p)[0]
