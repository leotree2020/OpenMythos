"""
D3: attention patterns from reconstructed weights (PREREGISTRATION 3, 8.5, 9.4).

Primary statistic per model state: over all attention layers / loop
iterations and all heads, the maximum of the mean (over diag_eval questions)
share of the readout position's statement attention that falls on the queried
statement's 4 characters (shares_test).
Revision 4 (proposed after the review of 53e5492, pending approval):
  - OpenMythos loop iterations keep only complete families (bodies whose 4
    questions all ran that loop); a loop enters if >= half of the bodies do
  - exact randomization test: one cyclic shift per body uniform on
    {0, 1, 2, 3}; p-value from the max over layers x heads; decision
    p <= 0.05 and statistic >= 0.5; the non-zero-shift mismatch reference of
    revision 1 is still reported, descriptively
Everything else (per layer / head values, ? -> 17, digit -> own variable)
is descriptive.
"""

import numpy as np
import torch

from common import DIGIT_POS, Q_POS, READ_POS, complete_family_mask
from runner import attn_layers


def body_shift(slot, g, include_identity=True):
    """Replacement slots for one body-level relabelling: one cyclic shift per
    body applied to its 4 questions (body-major, slot order). With
    include_identity the shift is uniform on {0, 1, 2, 3} (the full cyclic
    group: an exact randomization test, revision 4); without, on {1, 2, 3}
    (the pre-registered mismatch reference, kept as a descriptive quantity)."""
    n_bodies = len(slot) // 4
    lo = 0 if include_identity else 1
    shift = torch.randint(lo, 4, (n_bodies,), generator=g)
    return ((slot.view(n_bodies, 4) + shift[:, None]) % 4).reshape(-1)


def shares_test(S, Vq, slot, n_perm=1000, seed=0):
    """S (N, L, H, 4): per question, layer, head the share of the readout's
    statement attention on each statement slot; Vq (N, L) question-level loop
    validity. Body-level complete-family filtering; a layer enters only if
    >= half of the bodies are complete. Statistic: max over used layers x
    heads of the mean share on the queried slot. Randomization p-value over
    the cyclic group (identity included) with the same max (controls the
    family-wise error over layers x heads within one model state); the
    mismatch reference (non-zero shifts, the pre-registered null) is reported
    descriptively. Decision: p <= 0.05 and statistic >= 0.5."""
    N, L = Vq.shape
    V = torch.stack([complete_family_mask(Vq[:, i]) for i in range(L)], 1).double()
    used = V.sum(0) >= 0.5 * N
    V = V * used.double()
    nv = V.sum(0).clamp_min(1)

    def stat(sl):
        picked = S.gather(3, sl.view(N, 1, 1, 1).expand(N, S.shape[1], S.shape[2], 1)).squeeze(3)
        st = (picked * V.unsqueeze(2)).sum(0) / nv.unsqueeze(1)  # (L, H)
        st[~used] = float("-inf")
        return st

    obs = stat(slot)
    o_max = obs.max().item()
    g = torch.Generator().manual_seed(seed)
    rand = np.asarray([stat(body_shift(slot, g, True)).max().item() for _ in range(n_perm)])
    g2 = torch.Generator().manual_seed(seed + 1)
    mism = np.asarray([stat(body_shift(slot, g2, False)).max().item() for _ in range(n_perm)])
    p = float((1 + (rand >= o_max).sum()) / (1 + n_perm))
    return {
        "primary_max_share": o_max if used.any() else None,
        "argmax": divmod(int(obs.argmax()), obs.shape[1]) if used.any() else None,
        "p_value_randomization": p,
        "mismatch_reference_p95": float(np.percentile(mism, 95)),
        "mismatch_reference_mean": float(mism.mean()),
        "layers_used": used.tolist(),
        "n_complete_bodies_by_layer": (V.sum(0) / 4).tolist(),
        "decision": "检测到按查询定向的注意力" if (used.any() and p <= 0.05 and o_max >= 0.5) else "未检测到",
        "obs_by_layer_head": obs,
    }


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
    S = torch.stack(shares, 1).double()  # (N, L, H, 4)
    Vq = torch.stack(valid, 1)  # (N, L)
    t = shares_test(S, Vq, slot, n_perm=n_perm, seed=seed)
    obs = t.pop("obs_by_layer_head")
    used = t["layers_used"]
    if t["argmax"] is not None:
        li, hi = t["argmax"]
        t["argmax"] = {"layer": layers[li], "head": hi}
    t["descriptive"] = {
        "share_by_layer_head": {layers[i]: obs[i].tolist() for i in range(len(layers)) if used[i]},
        "layers_left_out_not_executed": [layers[i] for i in range(len(layers)) if not used[i]],
        "n_valid_questions_by_layer": {layers[i]: int(Vq[:, i].sum()) for i in range(len(layers))},
        "n_complete_bodies_by_layer": dict(zip(layers, t.pop("n_complete_bodies_by_layer"))),
        "attn_readout_to_query_token": w18_17,
        "attn_digit_to_own_variable": dig_var,
    }
    t["layers_used"] = [layers[i] for i in range(len(layers)) if used[i]]
    return t
