"""
Simplified multi-hop variable tracking without the root-frequency shortcut.

Same text format as experiments/loop_mech/task.py ("a=7;b=a;...|b?7"), but
every chain in a prompt gets a different root digit, so guessing among (or
the most frequent of) the digits present scores exactly 1 / #chains, and
the prompt is shorter (default 8 statements). Train on 1-2 hops; 3-4 hops
are reported for information only.
"""

import random
import string

import torch

VARS = string.ascii_letters


def seq_len(n_statements: int) -> int:
    return n_statements * 4 + 4


def make_sample(rng: random.Random, hops: int, n_statements: int, distractor_max: int):
    names = rng.sample(VARS, n_statements)
    chains = [names[: hops + 1]]
    i = hops + 1
    while i < n_statements:
        L = min(rng.randint(1, distractor_max + 1), n_statements - i)
        chains.append(names[i : i + L])
        i += L
    roots = rng.sample("0123456789", len(chains))  # distinct per prompt
    stmts = []
    for chain, root in zip(chains, roots):
        stmts.append(f"{chain[0]}={root};")
        for prev, cur in zip(chain, chain[1:]):
            stmts.append(f"{cur}={prev};")
    rng.shuffle(stmts)
    return "".join(stmts) + f"|{chains[0][-1]}?", roots[0]


def make_batch(rng, batch_size, hops_choices, n_statements=8, distractor_max=2):
    xs, ys = [], []
    for _ in range(batch_size):
        text, ans = make_sample(
            rng, rng.choice(hops_choices), n_statements, distractor_max
        )
        xs.append(list((text + ans).encode()))
        ys.append(ord(ans))
    return torch.tensor(xs, dtype=torch.long), torch.tensor(ys, dtype=torch.long)
