"""
M4: attention, descriptive only (PREREGISTRATION 9.8): no randomization test,
no calibration, no p-value; not used by any event or formal judgment.
From the reconstructed attention weights (gate_d runner):
  - share of the readout position's statement attention on the queried
    statement (per layer / loop iteration and head; OpenMythos loop iteration
    t counts only questions whose readout position was still running at t,
    complete families only, as Gate D revision 4), and its max over layers x
    heads with the arg max
  - readout position -> query token attention
  - digit position -> own statement letter attention (a rough binding-head
    indicator), per head, and its max over heads
"""

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
import torch

from e_masks import complete
from runner import attn_layers  # gate_d


def run_m4(runner, fam, g):
    x, y, slot, bid, roots = fam
    K = g.K
    _, rec, att = runner.run(x, record={"__none__"}, want_attn=True)
    out = {"share_queried_by_layer_head": {}, "n_complete_questions_by_layer": {},
           "readout_to_query_token": {}, "digit_to_own_letter": {}, "digit_to_own_letter_max_head": {}}
    best = (None, None, float("-inf"))
    for name in attn_layers(runner.arm):
        w = att[name]  # (KN, H, T, T)
        N, H = w.shape[0], w.shape[1]
        row = w[:, :, g.READ_POS, : 4 * K].reshape(N, H, K, 4).sum(-1)
        share = (row / row.sum(-1, keepdim=True)).double()  # (KN, H, K)
        if name.startswith("loop"):
            v = complete(rec[f"still{int(name[4:])}"][:, g.READ_POS], K)
        else:
            v = torch.ones(N, dtype=torch.bool)
        out["n_complete_questions_by_layer"][name] = int(v.sum())
        if v.sum() > 0:
            picked = share.gather(2, slot.view(N, 1, 1).expand(N, H, 1)).squeeze(2)[v].mean(0)
            out["share_queried_by_layer_head"][name] = picked.tolist()
            h = int(picked.argmax())
            if picked[h] > best[2]:
                best = (name, h, float(picked[h]))
        out["readout_to_query_token"][name] = w[:, :, g.READ_POS, g.Q_POS].mean(0).tolist()
        dv = torch.stack([w[0::K, :, p, p - 2] for p in g.DIGIT_POS], 0).mean((0, 1))
        out["digit_to_own_letter"][name] = dv.tolist()
        out["digit_to_own_letter_max_head"][name] = float(dv.max())
    out["max_share_queried"] = {"layer": best[0], "head": best[1], "value": best[2] if best[0] else None,
                                "chance": 1 / K}
    return out
