"""
Simplified multi-hop variable tracking without the root-frequency shortcut.

Same text format as experiments/loop_mech/task.py ("a=7;b=a;...|b?7"), with
three changes that remove shortcuts found in the original task:
    - every chain in a prompt gets a different root digit, so guessing among
      (or the most frequent of) the digits present scores 1 / #chains
    - distractor chains have 2-3 statements (1-2 links), the same lengths as
      the queried chain over the training range (1-2 hops), so "pick a root
      of a multi-statement chain" is no better than chance
    - the counterfactual swaps the queried root for a digit absent from the
      prompt, so distinct roots still hold after the swap
Default 8 statements. Train on 1-2 hops; 3-4 hops are informational (their
queried chain is longer than any distractor, see validate.py).
"""

import random
import re
import string

import torch

VARS = string.ascii_letters
STMT = re.compile(r"([A-Za-z])=([A-Za-z0-9]);")


def seq_len(n_statements: int) -> int:
    return n_statements * 4 + 4


def _distractor_lengths(rng: random.Random, remaining: int):
    """Split `remaining` statements into chains of 2 or 3 statements."""
    out = []
    while remaining:
        if remaining in (2, 3):
            L = remaining
        elif remaining == 4:
            L = 2
        else:
            L = rng.choice((2, 3))
        out.append(L)
        remaining -= L
    return out


def make_sample(rng: random.Random, hops: int, n_statements: int = 8):
    names = rng.sample(VARS, n_statements)
    chains = [names[: hops + 1]]
    i = hops + 1
    for L in _distractor_lengths(rng, n_statements - i):
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


def make_batch(rng, batch_size, hops_choices, n_statements=8):
    xs, ys = [], []
    for _ in range(batch_size):
        text, ans = make_sample(rng, rng.choice(hops_choices), n_statements)
        xs.append(list((text + ans).encode()))
        ys.append(ord(ans))
    return torch.tensor(xs, dtype=torch.long), torch.tensor(ys, dtype=torch.long)


def solve(prompt: str):
    """Independent solver: follow assignments from the query. Returns (digit, hops)."""
    body, q = prompt.split("|")
    env = dict(STMT.findall(body))
    cur, hops = q[0], 0
    while not env[cur].isdigit():
        cur = env[cur]
        hops += 1
    return env[cur], hops


def counterfactual(x: torch.Tensor, seed: int):
    """Swap the queried chain's root for a digit not present in the prompt."""
    rng = random.Random(seed)
    xs, ys = [], []
    for row in x:
        text = bytes(row.tolist()).decode()
        body, tail = text.split("|")
        env = dict(STMT.findall(body))
        cur = tail[0]
        while not env[cur].isdigit():
            cur = env[cur]
        old = env[cur]
        present = {v for v in env.values() if v.isdigit()}
        new = rng.choice([d for d in "0123456789" if d not in present])
        body = body.replace(f"{cur}={old};", f"{cur}={new};")
        xs.append(list((body + "|" + tail[:-1] + new).encode()))
        ys.append(ord(new))
    return torch.tensor(xs, dtype=torch.long), torch.tensor(ys, dtype=torch.long)
