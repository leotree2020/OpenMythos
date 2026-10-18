"""
ACT masks for Gate E (PREREGISTRATION 4: Gate D revision 6 single-sample
semantics, gate_d/act_masks.py, with the prompt length and family size of
the task geometry). The reachability recursion is gate_d's, unchanged.

    valid[i, t]     question i, run alone, still executes loop t
    still[i, t, p]  position p had not halted before loop t
Transformer models have no ACT: every mask is True.
M6 (ACT summary) is computed from the same masks.
"""

import torch

from act_masks import reachability  # noqa: F401  gate_d (archived), generic in shape


@torch.no_grad()
def act_masks(runner, x, g, n_loops=4):
    N = len(x)
    if runner.arm == "transformer":
        ones = torch.ones(N, n_loops, dtype=torch.bool)
        return {"valid": ones, "still": ones[:, :, None].expand(N, n_loops, g.L).clone()}
    valid = torch.zeros(N, n_loops, dtype=torch.bool)
    still = torch.zeros(N, n_loops, g.L, dtype=torch.bool)
    for i in range(N):
        rec = runner.run(x[i : i + 1], record={"__masks__"})[1]
        for t in range(n_loops):
            valid[i, t] = rec[f"valid{t}"][0]
            still[i, t] = rec[f"still{t}"][0]
    return {"valid": valid, "still": still}


def complete(mask_q, K):
    """(KN,) body-major question mask -> keep only bodies with all K True."""
    return mask_q.view(-1, K).all(1).repeat_interleave(K)


def m6_summary(masks, g):
    """M6: per loop, share of questions still executing it and, per position,
    share not yet halted; the loops in which the readout position takes part."""
    still = masks["still"].float()
    read = still[:, :, g.READ_POS].mean(0)
    return {
        "valid_by_loop": masks["valid"].float().mean(0).tolist(),
        "still_by_loop_position": still.mean(0).tolist(),
        "readout_still_by_loop": read.tolist(),
        "readout_stops_after_loop": next((t - 1 for t in range(len(read)) if read[t] == 0), None),
    }
