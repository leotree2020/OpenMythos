"""
The K=2 direct-lookup task of Gate E (PREREGISTRATION 1.1-1.2).

Prompts come from the archived generator gen_gate_a/levels._chains_prompt(rng,
[1, 1]) (2 distinct letters, 2 distinct root digits, shuffled statement order,
query uniform over the two statements), used unchanged. Training draws reject
held-out bodies (e_common.is_heldout); every evaluation and diagnostic set is
drawn from held-out bodies only. The independent solver is levels.solve.
"""

import random

from e_common import is_heldout
from levels import _chains_prompt, solve  # gen_gate_a/levels.py (archived)


def sample_k2(rng: random.Random):
    """One K=2 question (prompt ending in '?', answer digit), any body."""
    return _chains_prompt(rng, [1, 1])


def train_sample_k2(rng: random.Random):
    """A training question: held-out bodies are redrawn (rejection sampling)."""
    while True:
        p, a = sample_k2(rng)
        if not is_heldout(p.split("|")[0]):
            return p, a


def train_rng_k2(seed: int) -> random.Random:
    # PREREGISTRATION 2.1: Random(60_000 + seed), identical for both arms
    return random.Random(60_000 + seed)


def check(prompt, answer):
    """Independent solver agrees and the prompt is a 1-hop direct lookup."""
    return solve(prompt) == (answer, 0)
