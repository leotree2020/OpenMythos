"""Pure, CPU-safe summaries of ACT mass during A/B training."""
import torch
from act_math import act_accounting


def summarize_act_pair(original_probabilities, forced_probabilities, threshold):
    """Reconstruct ACT mass from probabilities consumed in each model forward.

    Raw probabilities are captured by ACT hooks. In the intervention arm the last
    returned probability is 1, making the upstream's existing remainder branch
    account for the final budget step. These are *forward-pass* observations.
    """
    if not original_probabilities or not forced_probabilities:
        raise ValueError('Both arms must record at least one ACT probability tensor')
    baseline = act_accounting(torch.stack(original_probabilities), threshold)
    forced = act_accounting(torch.stack(forced_probabilities), threshold)
    bm, fm = baseline.probability_mass, forced.probability_mass
    if not torch.allclose(fm, torch.ones_like(fm), atol=2e-6, rtol=0):
        raise RuntimeError('The forced-final hook failed to conserve ACT mass')
    return {
        'original_actual_loops': len(original_probabilities),
        'forced_actual_loops': len(forced_probabilities),
        'original_act_mass_min': float(bm.min()),
        'original_act_mass_mean': float(bm.mean()),
        'original_act_mass_max': float(bm.max()),
        'original_act_mass_deficit_max': float((1 - bm).clamp(min=0).max()),
        'original_act_deficit_fraction': float((bm < 1 - 1e-6).float().mean()),
        'forced_act_mass_min': float(fm.min()),
        'forced_act_mass_mean': float(fm.mean()),
    }


def first_trace_event(trace, key, *, threshold=1e-7):
    """First recorded training step whose absolute metric exceeds threshold."""
    for row in trace:
        if abs(row[key]) > threshold:
            return row['step']
    return None
