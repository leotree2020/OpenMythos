"""Independent ACT bookkeeping oracle for OpenMythos research.

This mirrors the ACT *weight accounting* seen in the upstream recurrent loop.
It is not an implementation or replacement of the full model.
"""
from dataclasses import dataclass
import torch


@dataclass
class ACTStats:
    weights: torch.Tensor             # (steps, batch, tokens)
    probability_mass: torch.Tensor    # (batch, tokens)
    cumulative_prob: torch.Tensor     # (batch, tokens)
    halted: torch.Tensor              # (batch, tokens) boolean


def act_accounting(probabilities: torch.Tensor, threshold: float = 0.99,
                   force_final_remainder: bool = False) -> ACTStats:
    """Replay OpenMythos's weight accounting from per-loop ACT probabilities.

    `force_final_remainder=True` represents a *research hypothesis*, NOT
    current upstream behavior. This does not change any model weights/logits.
    Calculations happen in float32, as does the upstream accumulator.
    """
    if probabilities.ndim != 3 or probabilities.shape[0] < 1:
        raise ValueError('probabilities must be [loops, batch, tokens]')
    if not (0 < threshold <= 1):
        raise ValueError('threshold must be in (0, 1]')
    if not torch.isfinite(probabilities).all() or not ((probabilities >= 0) & (probabilities <= 1)).all():
        raise ValueError('probabilities must be finite within [0, 1]')
    probs = probabilities.float()
    cumulative = torch.zeros_like(probs[0])
    mass = torch.zeros_like(cumulative)
    halted = torch.zeros_like(cumulative, dtype=torch.bool)
    weights = []
    n_steps = probs.shape[0]
    for i in range(n_steps):
        p = probs[i]
        active = (~halted)
        remainder = (1.0 - cumulative).clamp(min=0)
        terminal = cumulative + p >= threshold
        if force_final_remainder and i == n_steps - 1:
            terminal = torch.ones_like(terminal)
        weight = torch.where(terminal, remainder, p) * active.float()
        weights.append(weight)
        mass += weight
        cumulative += p * active.float()
        halted |= cumulative >= threshold
    return ACTStats(torch.stack(weights), mass, cumulative, halted)
