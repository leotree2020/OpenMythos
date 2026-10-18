#!/usr/bin/env python3
"""
Validation of the D5 estimators (PREREGISTRATION 8.7.5, 9.5) on a synthetic
4-choice linear softmax model whose gradient covariance is known exactly.

Population: n bodies x 4 queries, features phi(b, q) = alpha * u_b + beta * w_bq,
label y = q, logits = W phi. Per-question gradients (softmax - onehot) phi^T
are computed in closed form and checked against autograd. From the full
population: exact V_pop (body-mean variance) and S, and the analytic tr Var of
O / P / F batches (bodies drawn with replacement). Checks:
  1. FamilyAccumulator (online) == direct computation from all stored
     gradients (relative difference <= 1e-6)
  2. measured tr Var of R batches (batch_stats) contains the analytic value in
     its 95% bootstrap CI, for O, P and F
  3. two settings, one with S > 3 V and one with S < 3 V: the measured sign of
     tr Var(P) - tr Var(O) agrees with the analytic sign
Writes validation/synthetic_d5.json; exits 1 on any failure.
"""

import json
import os
import sys

import numpy as np
import torch

from common import HERE
from d5 import FamilyAccumulator, batch_stats

D, NB, R = 16, 400, 4000


def population(alpha, beta, seed):
    g = torch.Generator().manual_seed(seed)
    u = torch.randn(NB, 1, D, generator=g, dtype=torch.double)
    w = torch.randn(NB, 4, D, generator=g, dtype=torch.double)
    phi = alpha * u + beta * w
    W = torch.randn(4, D, generator=g, dtype=torch.double) * 0.3
    p = torch.softmax(phi @ W.T, -1)  # (NB, 4 queries, 4 classes)
    onehot = torch.eye(4, dtype=torch.double).expand(NB, 4, 4)
    grads = torch.einsum("bqc,bqd->bqcd", p - onehot, phi).reshape(NB, 4, -1)
    # autograd check on a few questions
    Wt = W.clone().requires_grad_(True)
    for b, q in ((0, 0), (5, 2), (17, 3)):
        loss = torch.nn.functional.cross_entropy((phi[b, q] @ Wt.T)[None], torch.tensor([q]))
        (ga,) = torch.autograd.grad(loss, Wt)
        assert (ga.reshape(-1) - grads[b, q]).abs().max() < 1e-12
    return grads


def analytic(grads):
    gbar = grads.mean(1)
    V = float(((gbar - gbar.mean(0)) ** 2).sum(1).mean())  # population variance
    S = float(((grads - gbar[:, None]) ** 2).sum(2).mean())
    return V, S, {"O": (V + S) / 64, "P": (V + S) / 64 + (V - S / 3) / 64, "F": V / 16}


def sample_batches(rng, scheme):
    out = []
    for _ in range(R):
        if scheme == "O":
            out.append([(int(b), [int(rng.integers(4))]) for b in rng.integers(0, NB, 64)])
        elif scheme == "P":
            out.append([(int(b), sorted(rng.choice(4, 2, replace=False).tolist())) for b in rng.integers(0, NB, 32)])
        else:
            out.append([(int(b), [0, 1, 2, 3]) for b in rng.integers(0, NB, 16)])
    return out


def main():
    rep, fail = {}, []
    for name, alpha, beta in (("S_gt_3V", 0.2, 1.0), ("S_lt_3V", 1.5, 0.15)):
        grads = population(alpha, beta, seed=11)
        V, S, an = analytic(grads)
        P_ = grads.shape[2]
        idx = {"total": torch.arange(P_), "half": torch.arange(P_ // 2)}
        acc = FamilyAccumulator(idx, NB, P_)
        for b in range(NB):
            acc.add(grads[b].float())
        est = acc.finish(n_boot=500)["total"]
        gbar = grads.mean(1)
        V_direct = float(((gbar - gbar.mean(0)) ** 2).sum(1).sum() / (NB - 1))
        rel = {"V": abs(est["V_b"] - V_direct) / V_direct, "S": abs(est["S"] - S) / S}
        r = {"V_pop": V, "S": S, "S_gt_3V": S > 3 * V, "analytic_trvar": an,
             "online_vs_direct_rel_diff": rel, "measured": {}}
        if max(rel.values()) > 1e-6:
            fail.append((name, "online accumulation", rel))
        rng = np.random.default_rng(5)
        u = torch.randn(P_, dtype=torch.double)
        u /= u.norm()
        boot = {}
        for scheme in ("O", "P", "F"):
            batches = sample_batches(rng, scheme)
            gb = lambda bt: torch.stack([grads[b, q] for b, qs in bt for q in qs]).mean(0).float()  # noqa: E731
            st = batch_stats(gb, batches, idx, u, n_boot=500)
            bt = st["trvar_boot"]["total"]
            boot[scheme] = bt
            ci = [float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))]
            inside = ci[0] <= an[scheme] <= ci[1]
            r["measured"][scheme] = {"trvar": st["trvar"]["total"], "ci95": ci, "analytic_inside_ci": inside}
            if not inside:
                fail.append((name, scheme, an[scheme], ci))
        sign_meas = float(np.median(boot["P"] - boot["O"]))
        sign_an = an["P"] - an["O"]
        r["P_minus_O"] = {"analytic": sign_an, "measured_median": sign_meas,
                          "same_sign": (sign_meas > 0) == (sign_an > 0)}
        if not r["P_minus_O"]["same_sign"]:
            fail.append((name, "sign", sign_an, sign_meas))
        rep[name] = r
    rep["failures"] = [str(f) for f in fail]
    os.makedirs(os.path.join(HERE, "validation"), exist_ok=True)
    with open(os.path.join(HERE, "validation", "synthetic_d5.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
