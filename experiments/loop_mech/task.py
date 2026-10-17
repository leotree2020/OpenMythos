"""
Multi-hop variable tracking: a task whose answer needs one step of
computation per hop, so it can only be solved at hop counts beyond the
training range if extra loops are actually used.

    "Q=4;a=Q;x=7;c=a;...;m=x;|c?4"

Each sample has `n_statements` assignments (fixed, so train and test
sequences have identical length and only the hop count changes). The queried
chain has `hops` variable-to-variable links after its digit root; the rest
are distractor chains of 0..distractor_max links, roots drawn independently
(digits repeat across chains, so the answer cannot be read off without
following the links). Statement order is shuffled.

Byte-level: token ids are ASCII codes. The loss and accuracy are on the
single answer byte after "?".
"""

import random
import string

import torch

VARS = string.ascii_letters  # 52 single-byte names
STMT_BYTES = 4  # "a=b;"


def seq_len(n_statements: int) -> int:
    # statements + "|" + var + "?" + answer
    return n_statements * STMT_BYTES + 4


def make_sample(rng: random.Random, hops: int, n_statements: int, distractor_max: int):
    """Return (text, answer_char)."""
    names = rng.sample(VARS, n_statements)
    chains = []
    # queried chain: root statement + `hops` links -> hops + 1 statements
    q_len = hops + 1
    chains.append(names[:q_len])
    i = q_len
    while i < n_statements:
        L = min(rng.randint(1, distractor_max + 1), n_statements - i)
        chains.append(names[i : i + L])
        i += L

    stmts = []
    answer = None
    for ci, chain in enumerate(chains):
        root = str(rng.randint(0, 9))
        if ci == 0:
            answer = root
        stmts.append(f"{chain[0]}={root};")
        for prev, cur in zip(chain, chain[1:]):
            stmts.append(f"{cur}={prev};")
    rng.shuffle(stmts)
    query = chains[0][-1]
    return "".join(stmts) + f"|{query}?", answer


def make_batch(
    rng: random.Random,
    batch_size: int,
    hops_choices,
    n_statements: int = 24,
    distractor_max: int = 4,
):
    """Return (x, y): x is (B, L) prompt+answer bytes, y is (B,) answer bytes."""
    xs, ys = [], []
    for _ in range(batch_size):
        hops = rng.choice(hops_choices)
        text, ans = make_sample(rng, hops, n_statements, distractor_max)
        xs.append(list((text + ans).encode()))
        ys.append(ord(ans))
    return torch.tensor(xs, dtype=torch.long), torch.tensor(ys, dtype=torch.long)
