"""
D3: attention patterns from reconstructed weights (PREREGISTRATION 3, 8.5, 9.4).

Primary statistic per model state: over all attention layers / loop
iterations and all heads, the maximum of the mean (over diag_eval questions)
share of the readout position's statement attention that falls on the queried
statement's 4 characters. Null: 1000 body-level permutations. In each, every
body draws one non-zero cyclic shift (1, 2 or 3) applied to all 4 of its
questions, so the 4 replacement statements of a body are a complete
permutation of its statements with no question keeping its own (body_shift);
the same max over layers x heads is taken each time. Detected iff the observed
max exceeds the null's 95th percentile and is >= 0.5. Everything else
(per layer / head values, ? -> 17, digit -> own variable) is descriptive.
OpenMythos loop iterations use only questions for which that loop ran.
"""

import numpy as np
import torch

from common import DIGIT_POS, Q_POS, READ_POS
from runner import attn_layers


def body_shift(slot, g):
    """Replacement slots for one body-level permutation: one shift in {1, 2, 3}
    per body (questions are body-major, 4 per body, in slot order)."""
    n_bodies = len(slot) // 4
    shift = torch.randint(1, 4, (n_bodies,), generator=g)
    return ((slot.view(n_bodies, 4) + shift[:, None]) % 4).reshape(-1)


def run_d3(runner, fam, n_perm=1000, seed=0):
    x, y, slot, bid, roots = fam
    _, rec, att = runner.run(x, record={"__none__"}, want_attn=True)
    layers = attn_layers(runner.arm)
    N = len(x)
    shares, w18_17, dig_var, valid = [], {}, {}, []
    for name in layers:
        w = att[name]  # (N, H, T, T)
        row = w[:, :, READ_POS, :16].reshape(N, w.shape[1], 4, 4).sum(-1)  # mass per statement
        shares.append(row / row.sum(-1, keepdim=True))  # (N, H, 4)
        w18_17[name] = w[:, :, READ_POS, Q_POS].mean(0).tolist()
        dig_var[name] = torch.stack([w[0::4, :, p, p - 2] for p in DIGIT_POS], 0).mean((0, 1)).tolist()
        if name.startswith("loop"):
            valid.append(rec[f"valid{int(name[4:])}"])
        else:
            valid.append(torch.ones(N, dtype=torch.bool))
    S = torch.stack(shares, 1).double()  # (N, Lyr, H, 4)
    V = torch.stack(valid, 1).double()  # (N, Lyr)
    # a loop iteration executed for fewer than half of the questions is left
    # out of the primary statistic (and of its null), as in D2
    used = V.sum(0) >= 0.5 * N
    V = V * used.double()
    nv = V.sum(0).clamp_min(1)

    def stat(sl):
        picked = S.gather(3, sl.view(N, 1, 1, 1).expand(N, S.shape[1], S.shape[2], 1)).squeeze(3)
        return (picked * V.unsqueeze(2)).sum(0) / nv.unsqueeze(1)  # (Lyr, H)

    obs = stat(slot)
    obs[~used] = float("-inf")
    g = torch.Generator().manual_seed(seed)
    null = []
    for _ in range(n_perm):
        alt = body_shift(slot, g)
        st = stat(alt)
        st[~used] = float("-inf")
        null.append(st.max().item())
    null = np.asarray(null)
    o_max = obs.max().item()
    li, hi = divmod(int(obs.argmax()), obs.shape[1])
    p95 = float(np.percentile(null, 95))
    return {
        "primary_max_share": o_max,
        "argmax": {"layer": layers[li], "head": hi},
        "null_p95": p95,
        "null_mean": float(null.mean()),
        "p_value": float((1 + (null >= o_max).sum()) / (1 + n_perm)),
        "decision": "检测到按查询定向的注意力" if (o_max > p95 and o_max >= 0.5) else "未检测到",
        "descriptive": {
            "share_by_layer_head": {layers[i]: obs[i].tolist() for i in range(len(layers)) if used[i]},
            "layers_left_out_not_executed": [layers[i] for i in range(len(layers)) if not used[i]],
            "n_valid_by_layer": {layers[i]: int(torch.stack(valid, 1)[:, i].sum()) for i in range(len(layers))},
            "attn_readout_to_query_token": w18_17,
            "attn_digit_to_own_variable": dig_var,
        },
    }
