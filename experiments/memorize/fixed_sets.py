"""
Fixed 1-hop problem sets for the memorization diagnostic.

The 512-problem set is generated once from a fixed seed with task_v2's
generator; the 32-problem set is its first 32 problems, so Gate 1 is a
subset of Gate 2. A separate fresh held-out 1-hop set (different seed, not
the Basic Learn test set) is scored at the end for information only.
Each set's token ids are hashed so every training step can be checked
against the frozen data.
"""

import hashlib
import os
import random
import re
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "basic_learn"))

from task_v2 import STMT, make_batch  # noqa: E402

N_STATEMENTS = 8
FIXED_SEED = 31337
HELDOUT_SEED = 55555


def fixed_set(n: int):
    x, y = make_batch(random.Random(FIXED_SEED), 512, [1], N_STATEMENTS)
    return x[:n].clone(), y[:n].clone()


def heldout_set(n: int = 500):
    return make_batch(random.Random(HELDOUT_SEED), n, [1], N_STATEMENTS)


def digest(x: torch.Tensor, y: torch.Tensor) -> str:
    h = hashlib.sha256()
    h.update(x.numpy().tobytes())
    h.update(y.numpy().tobytes())
    return h.hexdigest()


def root_candidates(x: torch.Tensor):
    """Per row, the set of root digit byte ids present in the prompt."""
    out = []
    for row in x:
        body = bytes(row[:-1].tolist()).decode().split("|")[0]
        out.append({ord(v) for _, v in STMT.findall(body) if v.isdigit()})
    return out
