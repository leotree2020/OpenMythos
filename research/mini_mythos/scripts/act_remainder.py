"""An opt-in research-only ACT final-remainder intervention.

Set the final ACT probability to one with a temporary forward hook. In the
pinned upstream recurrence this makes the existing threshold branch select
`remainder = 1 - cumulative_p` at the last allowed loop. The model source,
parameters and all earlier ACT probabilities are left unchanged.
"""
from contextlib import contextmanager
import torch


@contextmanager
def act_probability_hook(model, max_loops, *, force_final=False, observed=None):
    """Temporarily instrument model.recurrent.act; always remove the hook.

    `observed`, if passed, receives detached CPU probabilities *as consumed*
    by the recurrent loop. Each forward pass needs a fresh context manager.
    """
    if not isinstance(max_loops, int) or max_loops < 1:
        raise ValueError('max_loops must be a positive integer')
    calls = 0

    def intervention(_act, _inputs, output):
        nonlocal calls
        calls += 1
        if calls > max_loops:
            raise RuntimeError('More ACT calls than the requested loop budget')
        replacement = torch.ones_like(output) if force_final and calls == max_loops else output
        if observed is not None:
            observed.append(replacement.detach().float().cpu())
        return replacement if replacement is not output else None

    handle = model.recurrent.act.register_forward_hook(intervention)
    try:
        yield
    finally:
        handle.remove()
