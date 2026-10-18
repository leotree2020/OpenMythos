#!/usr/bin/env python3
"""
Regression tests for the same-subset MLP control of D2 (fix after the review
of 053a771): every MLP probe's emb control uses exactly the probe's own fit /
eval questions. Constructed data and a non-formal smoke model only. Writes
validation/mlp_control_tests.json; exits 1 on any failure.
  1 constructed: emb-control features that encode the label only for a
    subset A of bodies -> the control fails on subset A (probe void), passes
    on a disjoint subset B (probe kept): different subsets give different
    control results, and a failing control voids the probe
  2 a control built on other questions than the probe is rejected
  3 smoke model: every MLP result (D2-E and D2-F) carries its own control,
    evaluated on the same number of eval questions as the probe
"""

import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HERE, family_tensors, load_diag, load_state  # noqa: E402
from d2 import mlp_with_control, run_d2  # noqa: E402
from runner import Runner  # noqa: E402

res, fail = {}, []
g = torch.Generator().manual_seed(0)
n_b = 200  # bodies; 4 questions each, labels = slot (P1)
y = torch.arange(4).repeat(n_b)
groups = np.repeat(np.arange(n_b), 4)
noise = torch.randn(4 * n_b, 64, generator=g)
leaky = noise.clone()
leaky[:, :4] += 4.0 * torch.nn.functional.one_hot(y, 4).float()
A = groups < 100  # bodies 0-99: emb control features leak the label
emb_feat = torch.where(torch.from_numpy(A)[:, None], leaky, noise)
probe_feat = torch.randn(4 * n_b, 64, generator=g)  # uninformative probe features


def split(mask, X):
    m = torch.from_numpy(mask)
    fit = m & torch.from_numpy(groups % 2 == 0)
    ev = m & torch.from_numpy(groups % 2 == 1)
    return (X[fit], y[fit], groups[fit.numpy()], X[ev], y[ev], groups[ev.numpy()])


rA = mlp_with_control(split(A, probe_feat), split(A, emb_feat), "P1")
rB = mlp_with_control(split(~A, probe_feat), split(~A, emb_feat), "P1")
res["1_constructed"] = {
    "subset_A": {"control_acc": rA["emb_control"]["acc"], "control_at_baseline": rA["emb_control"]["at_baseline"],
                 "probe_void": rA["void"], "decision": rA["decision"]},
    "subset_B": {"control_acc": rB["emb_control"]["acc"], "control_at_baseline": rB["emb_control"]["at_baseline"],
                 "probe_void": rB["void"], "decision": rB["decision"]},
}
if not (not rA["emb_control"]["at_baseline"] and rA["void"] and rA["decision"] == "作废（控制未通过）"
        and rB["emb_control"]["at_baseline"] and not rB["void"]):
    fail.append("1")

try:
    mlp_with_control(split(A, probe_feat), split(~A, emb_feat), "P1")
    res["2_mismatched_control_rejected"] = False
    fail.append("2")
except AssertionError:
    res["2_mismatched_control_rejected"] = True

rows = load_diag("timing")
fr, er = rows[:50], rows[50:]
m = load_state("openmythos", 99, 60, path=os.path.join(HERE, "..", "budget_a", "smoke", "run1_openmythos.pt"))
d2 = run_d2(Runner(m), family_tensors(fr), fr, family_tensors(er), er)
checks = {}
for part, probes in (("mlp", "probes"), ("mlp_F", "probes_F")):
    for k, v in d2[part].items():
        lin = d2[probes][k]
        checks[f"{part}:{k}"] = {"has_own_control": "emb_control" in v,
                                 "same_n_eval": v.get("emb_control", {}).get("n") == v["n"] == lin["n"],
                                 "void": v["void"]}
res["3_smoke_model"] = checks
if not checks or not all(c["has_own_control"] and c["same_n_eval"] for c in checks.values()):
    fail.append("3")

res["failures"] = fail
with open(os.path.join(HERE, "validation", "mlp_control_tests.json"), "w") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fail else 0)
