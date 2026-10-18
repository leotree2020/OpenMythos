#!/usr/bin/env python3
"""
Regression tests for the three fixes made after the pre-launch review of
8a2bc7d (implementation deviations found before any formal diagnostic; no
hypothesis, threshold or frozen data changed). Non-formal models and data
only (seed-99 smoke checkpoints, the timing set). Writes
validation/regression_fixes.json; exits 1 on any failure.
  1. D3: body-level permutation (body_shift) - every body's 4 replacement
     slots form a complete permutation with no fixed point; the null
     distribution is reproducible for a fixed seed and differs for another.
  2. D5: bootstrap resamples of the O / P / F schemes are independent
     (different index sequences); synthetic_d5.py (rerun separately) checks
     the P - O CI against the analytic difference.
  3. D4: relative_effect - zero and near-zero denominators give
     "无法稳定估计", valid denominators give the ratio.
"""

import json
import os
import sys

import numpy as np
import torch

from common import HERE, family_tensors, load_diag, load_state
from d3 import body_shift, run_d3
from d4 import relative_effect
from d5 import SCHEME_SEED, gram_trvar
from runner import Runner

res, fail = {}, []

# 1. D3
slot = torch.arange(4).repeat(500)
g = torch.Generator().manual_seed(0)
perm_ok, fixed_points, shifts = True, 0, set()
for _ in range(200):
    alt = body_shift(slot, g).view(500, 4)
    perm_ok &= bool((alt.sort(1).values == torch.arange(4)).all())
    fixed_points += int((alt == torch.arange(4)).sum())
    shifts |= set(((alt[:, 0] - 0) % 4).tolist())
    perm_ok &= bool(((alt - torch.arange(4)) % 4 == ((alt[:, :1] - 0) % 4)).all())  # one shift per body
model = load_state("openmythos", 99, 60, path=os.path.join(HERE, "..", "budget_a", "smoke", "run1_openmythos.pt"))
fam = family_tensors(load_diag("timing"))
a = run_d3(Runner(model), fam, n_perm=200, seed=0)
b = run_d3(Runner(model), fam, n_perm=200, seed=0)
c = run_d3(Runner(model), fam, n_perm=200, seed=1)
res["d3_body_level_permutation"] = {
    "complete_permutation_one_shift_per_body": perm_ok, "fixed_points": fixed_points,
    "shifts_seen": sorted(shifts), "reproducible_same_seed": a["null_p95"] == b["null_p95"] and a["p_value"] == b["p_value"],
    "differs_other_seed": a["null_mean"] != c["null_mean"],
}
r = res["d3_body_level_permutation"]
if not (r["complete_permutation_one_shift_per_body"] and r["fixed_points"] == 0 and r["shifts_seen"] == [1, 2, 3]
        and r["reproducible_same_seed"] and r["differs_other_seed"]):
    fail.append("d3")

# 2. D5 independent bootstrap seeds
G = torch.randn(50, 30)
ix = torch.arange(30)
boots = {s: gram_trvar(G, ix, n_boot=500, seed=SCHEME_SEED[s])[1] for s in ("O", "P", "F")}
same = gram_trvar(G, ix, n_boot=500, seed=SCHEME_SEED["O"])[1]
corr = {f"{x}-{y}": float(np.corrcoef(boots[x], boots[y])[0, 1]) for x, y in (("O", "P"), ("O", "F"), ("P", "F"))}
res["d5_independent_bootstrap"] = {
    "seeds": SCHEME_SEED, "distinct_seeds": len(set(SCHEME_SEED.values())) == 3,
    "corr_between_schemes_same_data": corr, "corr_same_seed_same_data": float(np.corrcoef(boots["O"], same)[0, 1]),
}
r = res["d5_independent_bootstrap"]
if not (r["distinct_seeds"] and max(abs(v) for v in corr.values()) < 0.2 and r["corr_same_seed_same_data"] > 0.999):
    fail.append("d5")

# 3. D4 relative effect guard
cases = {"zero_den": (1.0, 0.0, 1e-7), "near_zero_den": (1.0, 5e-7, 1e-7),
         "den_at_10eps": (1.0, 1e-6, 1e-7), "valid_negative_den": (1.0, -2e-6, 1e-7), "valid_den": (0.5, 1.0, 1e-7)}
out = {k: relative_effect(*v) for k, v in cases.items()}
res["d4_relative_effect_guard"] = out
if not (out["zero_den"] == out["near_zero_den"] == out["den_at_10eps"] == "无法稳定估计"
        and abs(out["valid_negative_den"] + 5e5) < 1e-6 and out["valid_den"] == 0.5):
    fail.append("d4")

res["failures"] = fail
with open(os.path.join(HERE, "validation", "regression_fixes.json"), "w") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fail else 0)
