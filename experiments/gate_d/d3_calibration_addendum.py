#!/usr/bin/env python3
"""
D3 supplementary calibration B3' / C' (PREREGISTRATION 12; approved after the
review of 29280ea). Simulated data only. The original d3_calibration.py and
validation/d3_calibration.json are not modified. Same generator and test as
d3_calibration.py except the loop validity probabilities [0.98, 0.98, 0.85,
0.85] (expected complete-family share ~0.694 > 0.5) and the seeds. Every
simulation checks that its target layers entered the statistic (B3': loop
layers 1-4; C': the planted layer 2); one invalid simulation makes that item
"invalid". Writes validation/d3_calibration_addendum.json.
"""

import json
import os
import sys

import torch

from common import HERE, complete_family_mask, wilson
from d3 import shares_test
from d3_calibration import LOOP_LAYERS, NB, SLOT, L, H, dirichlet, legacy_test

P_VALID = [0.98, 0.98, 0.85, 0.85]
SPEC = {"B3prime": {"seed": 2025, "n_sim": 400, "targets": list(LOOP_LAYERS)},
        "Cprime": {"seed": 2026, "n_sim": 100, "targets": [2]}}


def simulate(kind, g):
    N = 4 * NB
    S = dirichlet([4.0, 2.0, 1.0, 1.0], N * L * H, g).view(N, L, H, 4)
    Vq = torch.ones(N, L, dtype=torch.bool)
    p_valid = torch.tensor(P_VALID).repeat(NB)
    for li in LOOP_LAYERS:
        Vq[:, li] = torch.rand(N, generator=g) < p_valid
    if kind == "Cprime":
        S = S.clone()
        own = torch.zeros(N, 4, dtype=torch.double)
        own[torch.arange(N), SLOT] = 1.0
        S[:, 2, 0] = 0.45 * S[:, 2, 0] + 0.55 * own
    return S.contiguous(), Vq


def main():
    rep = {"spec": {"p_valid": P_VALID, "expected_complete_share": 0.98**2 * 0.85**2, **SPEC}}
    status = {}
    for kind, sp in SPEC.items():
        g = torch.Generator().manual_seed(sp["seed"])
        p_hits = dec_hits = leg_hits = invalid = 0
        complete_share, planted_own = [], []
        for _ in range(sp["n_sim"]):
            S, Vq = simulate(kind, g)
            t = shares_test(S, Vq, SLOT, n_perm=1000, seed=int(torch.randint(0, 10**6, (1,), generator=g)))
            if not all(t["layers_used"][li] for li in sp["targets"]):
                invalid += 1
            complete_share.append([t["n_complete_bodies_by_layer"][li] / NB for li in LOOP_LAYERS])
            p_hits += t["p_value_randomization"] <= 0.05
            dec_hits += t["decision"] == "检测到按查询定向的注意力"
            if kind == "B3prime":
                leg_hits += legacy_test(S, Vq, SLOT, n_perm=1000)["above_reference"]
            else:
                m = complete_family_mask(Vq[:, 2])
                planted_own.append(float(S[torch.arange(len(S)), 2, 0, SLOT][m].mean()))
        n = sp["n_sim"]
        cs = torch.tensor(complete_share)
        r = {"n_sim": n, "invalid_simulations": invalid,
             "complete_share_loop_layers": {"min": float(cs.min()), "mean": float(cs.mean()), "max": float(cs.max())},
             "rate_p_le_0.05": p_hits / n, "rate_p_le_0.05_wilson95": wilson(p_hits, n),
             "rate_full_decision": dec_hits / n, "rate_full_decision_wilson95": wilson(dec_hits, n)}
        if kind == "B3prime":
            r["legacy_53e5492_rate_above_reference"] = leg_hits / n
            ok = r["rate_p_le_0.05_wilson95"][0] <= 0.05 and r["rate_full_decision"] <= r["rate_p_le_0.05"]
        else:
            r["planted_mean_own_share_in_complete_families"] = sum(planted_own) / len(planted_own)
            ok = r["rate_full_decision"] >= 0.9
        r["status"] = "无效（未测试到目标层）" if invalid else ("通过" if ok else "未通过")
        status[kind] = r["status"]
        rep[kind] = r
        print(kind, r, flush=True)
    rep["status"] = status
    with open(os.path.join(HERE, "validation", "d3_calibration_addendum.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(0 if all(v == "通过" for v in status.values()) else 1)


if __name__ == "__main__":
    main()
