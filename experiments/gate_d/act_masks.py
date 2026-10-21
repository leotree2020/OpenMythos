"""
ACT masks for D2 / D4 (PREREGISTRATION 13.1-13.2, definition A).

Single-sample semantics: every mask is computed from a batch-size-1 run of
the question, so it does not depend on which other questions share a batch
(the original forward's early exit checks halted.all() over the whole batch).

    valid[i, t]     question i, run alone, still executes loop t (some
                    position had not halted before loop t)
    still[i, t, p]  position p had not halted before loop t
    R[i, t, p]      reachability: the state h_{t+1}[p] after loop t has a
                    computation path to the readout logits
                      R[T-1] = still[T-1]
                      R[t]   = still[t] | (valid[t+1] & any_{j >= p} R[t+1, j])
Transformer models have no ACT: every mask is True.
"""

import torch

from common import L_PROMPT


@torch.no_grad()
def act_masks(runner, x, n_loops=4):
    N = len(x)
    if runner.arm == "transformer":
        ones = torch.ones(N, n_loops, dtype=torch.bool)
        return {"valid": ones, "still": ones[:, :, None].expand(N, n_loops, L_PROMPT).clone()}
    valid = torch.zeros(N, n_loops, dtype=torch.bool)
    still = torch.zeros(N, n_loops, L_PROMPT, dtype=torch.bool)
    for i in range(N):
        rec = runner.run(x[i : i + 1], record={"__masks__"})[1]
        for t in range(n_loops):
            valid[i, t] = rec[f"valid{t}"][0]
            still[i, t] = rec[f"still{t}"][0]
    return {"valid": valid, "still": still}


def reachability(masks):
    still, valid = masks["still"], masks["valid"]
    N, T, P = still.shape
    R = torch.zeros_like(still)
    R[:, T - 1] = still[:, T - 1]
    for t in range(T - 2, -1, -1):
        later = R[:, t + 1].flip(1).cummax(1).values.flip(1)  # any reachable j >= p
        R[:, t] = still[:, t] | (valid[:, t + 1, None] & later)
    return R


def suffix_any(R_t):
    """(N, P) -> (N, P): any reachable position j >= p."""
    return R_t.flip(1).cummax(1).values.flip(1)


def complete(mask_q):
    """(4N,) body-major question mask -> keep only bodies with all 4 True."""
    return mask_q.view(-1, 4).all(1).repeat_interleave(4)
