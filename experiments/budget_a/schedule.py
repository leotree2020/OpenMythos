"""
Learning-rate schedule for the level-A training-budget diagnostic.

Steps 0..2999 follow exactly the Gate A / Basic Learn schedule
(memorize/train_mem.get_lr with warmup 100, total 3000, peak 2e-3: linear
warmup, then cosine down to 10% of peak). From step 3000 on the rate is held
at that schedule's end value, 0.1 x peak = 2e-4, until the pre-registered
maximum step.
"""

import math

PEAK, WARMUP, COSINE_STEPS = 2e-3, 100, 3000


def base_lr(step, warmup=WARMUP, total=COSINE_STEPS, max_lr=PEAK):
    # identical to experiments/memorize/train_mem.get_lr
    if step < warmup:
        return max_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.1 * max_lr + 0.9 * max_lr * 0.5 * (1 + math.cos(math.pi * progress))


def extended_lr(step):
    return base_lr(step) if step < COSINE_STEPS else 0.1 * PEAK
