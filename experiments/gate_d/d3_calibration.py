#!/usr/bin/env python3
"""
Negative controls and calibration of the D3 test (revision 4), on simulated
attention shares only (no model, no diagnostic data). Writes
validation/d3_calibration.json; exits 1 on any failure.

  A  reviewer's counterexample (review of 53e5492): in one loop layer every
     query of a body has the same shares [0.5, 0.5, 0, 0] but only slots 0
     and 1 ran the loop; all other layers / heads uniform. The 53e5492 test
     (question-level validity, non-zero-shift reference) must report
     "detected"; the revision-4 test must not.
  B  calibration under the null (no query-directed attention), 400 simulated
     model states each, 1000 relabellings, 500 bodies x 6 layers x 4 heads:
       B1 shares identical across the 4 queries of a body
       B2 shares drawn i.i.d. per question with a positional bias
       B3 as B2, plus query-dependent loop validity (slot-dependent ACT
          stopping) in the loop layers
     Pass: for p <= 0.05 alone, the Wilson 95% lower bound of the false
     positive rate is <= 0.05 (not above nominal); and the full decision
     (p <= 0.05 and statistic >= 0.5) fires in no more than that. The 53e5492
     test is run on B3 for comparison (expected to be inflated).
  C  power: one loop layer / head with own-slot preference (mean share on
     the queried statement about 0.6), with B3's selection; detection rate
     reported (pass if >= 0.9).
  D  D2 analogue: with question-level selection the slot labels of a loop
     point are no longer balanced (decision baseline 0.25 no longer holds);
     complete families keep them balanced.
"""

import json
import os
import sys

import numpy as np
import torch

from common import HERE, complete_family_mask, wilson
from d3 import body_shift, shares_test

NB, L, H = 500, 6, 4
LOOP_LAYERS = (1, 2, 3, 4)  # layers 1-4 play the loop iterations, 0 and 5 prelude / coda
SLOT = torch.arange(4).repeat(NB)


def legacy_test(S, Vq, slot, n_perm=1000, seed=0):
    """D3 test as committed in 53e5492 (question-level validity, non-zero shifts)."""
    N = S.shape[0]
    V = Vq.double()
    used = V.sum(0) >= 0.5 * N
    V = V * used.double()
    nv = V.sum(0).clamp_min(1)

    def stat(sl):
        picked = S.gather(3, sl.view(N, 1, 1, 1).expand(N, S.shape[1], S.shape[2], 1)).squeeze(3)
        st = (picked * V.unsqueeze(2)).sum(0) / nv.unsqueeze(1)
        st[~used] = float("-inf")
        return st

    o = stat(slot).max().item()
    g = torch.Generator().manual_seed(seed)
    null = np.asarray([stat(body_shift(slot, g, include_identity=False)).max().item() for _ in range(n_perm)])
    p95 = float(np.percentile(null, 95))
    return {"obs": o, "p95": p95, "detected": o > p95 and o >= 0.5, "above_reference": o > p95}


def dirichlet(alpha, n, g):
    gam = torch.distributions.Gamma(torch.tensor(alpha, dtype=torch.double), torch.tensor(1.0, dtype=torch.double))
    torch.manual_seed(int(torch.randint(0, 2**31 - 1, (1,), generator=g)))
    x = gam.sample((n,))
    return x / x.sum(-1, keepdim=True)


def simulate(kind, g):
    """S (4NB, L, H, 4), Vq (4NB, L)."""
    N = 4 * NB
    bias = [4.0, 2.0, 1.0, 1.0]
    if kind == "B1":
        S = dirichlet(bias, NB * L * H, g).view(NB, 1, L, H, 4).expand(NB, 4, L, H, 4).reshape(N, L, H, 4)
    else:
        S = dirichlet(bias, N * L * H, g).view(N, L, H, 4)
    Vq = torch.ones(N, L, dtype=torch.bool)
    if kind in ("B3", "C"):
        p_valid = torch.tensor([0.95, 0.95, 0.6, 0.6]).repeat(NB)
        for li in LOOP_LAYERS:
            Vq[:, li] = torch.rand(N, generator=g) < p_valid
    if kind == "C":
        S = S.clone()
        own = torch.zeros(N, 4, dtype=torch.double)
        own[torch.arange(N), SLOT] = 1.0
        S[:, 2, 0] = 0.45 * S[:, 2, 0] + 0.55 * own  # mean share on own slot ~0.6
    return S.contiguous(), Vq


def main():
    rep, fail = {}, []
    # A: counterexample
    N = 4 * NB
    S = torch.full((N, L, H, 4), 0.25, dtype=torch.double)
    S[:, 2] = torch.tensor([0.5, 0.5, 0.0, 0.0], dtype=torch.double)
    Vq = torch.ones(N, L, dtype=torch.bool)
    Vq[:, 2] = (SLOT < 2)
    leg = legacy_test(S, Vq, SLOT)
    new = shares_test(S, Vq, SLOT)
    new.pop("obs_by_layer_head")
    rep["A_counterexample"] = {"legacy_53e5492": leg, "revision4": {k: new[k] for k in (
        "primary_max_share", "p_value_randomization", "layers_used", "decision")}}
    if not (leg["detected"] and new["decision"] == "未检测到"):
        fail.append("A")
    # B: calibration under the null; C: power
    g = torch.Generator().manual_seed(2024)
    for kind, n_sim in (("B1", 400), ("B2", 400), ("B3", 400), ("C", 100)):
        p_hits = dec_hits = leg_hits = 0
        for _ in range(n_sim):
            S, Vq = simulate(kind, g)
            t = shares_test(S, Vq, SLOT, n_perm=1000, seed=int(torch.randint(0, 10**6, (1,), generator=g)))
            p_hits += t["p_value_randomization"] <= 0.05
            dec_hits += t["decision"] == "检测到按查询定向的注意力"
            if kind == "B3":
                leg_hits += legacy_test(S, Vq, SLOT, n_perm=1000)["above_reference"]
        r = {"n_sim": n_sim, "rate_p_le_0.05": p_hits / n_sim, "rate_p_le_0.05_wilson95": wilson(p_hits, n_sim),
             "rate_full_decision": dec_hits / n_sim}
        if kind == "B3":
            r["legacy_rate_above_reference"] = leg_hits / n_sim
        rep[kind] = r
        print(kind, r, flush=True)
        if kind.startswith("B") and (r["rate_p_le_0.05_wilson95"][0] > 0.05 or r["rate_full_decision"] > r["rate_p_le_0.05"]):
            fail.append(kind)
        if kind == "C" and r["rate_full_decision"] < 0.9:
            fail.append("C")
    # D: D2 label balance under selection
    Vt = (SLOT < 2) | (torch.rand(N, generator=g) < 0.6)
    q_sel = SLOT[Vt]
    cf = complete_family_mask(Vt)
    rep["D_d2_label_balance"] = {
        "question_level_selection_slot_shares": torch.bincount(q_sel, minlength=4).double().div(len(q_sel)).tolist(),
        "complete_family_slot_shares": torch.bincount(SLOT[cf], minlength=4).double().div(int(cf.sum())).tolist(),
    }
    if max(abs(x - 0.25) for x in rep["D_d2_label_balance"]["complete_family_slot_shares"]) > 1e-12:
        fail.append("D")
    rep["failures"] = fail
    with open(os.path.join(HERE, "validation", "d3_calibration.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
