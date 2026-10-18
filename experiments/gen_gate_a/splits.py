"""RNG streams for Gate A. Training, dev and test streams are separate per level."""

import random

N_DEV, N_TEST = 500, 1000
_LEVEL_IDX = {"A": 0, "B": 1, "C1": 2, "C2": 3}


def train_rng(level: str, seed: int) -> random.Random:
    # identical for both arms with the same seed (paired sample sequence)
    return random.Random(30_000 + 100 * _LEVEL_IDX[level] + seed)


def dev_rng(level: str) -> random.Random:
    return random.Random(41_000 + _LEVEL_IDX[level])


def test_rng(level: str) -> random.Random:
    return random.Random(42_000 + _LEVEL_IDX[level])
