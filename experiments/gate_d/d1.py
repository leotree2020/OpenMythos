"""
D1: query dependence of the output distribution (PREREGISTRATION 3, 8.3, 10.3).

Per question (body b, query q, answer y_q) on the 4-query families of
diag_eval: p(y_q | q) vs p(y_q | other queries of the same body), in three
normalizations (full 256-token vocabulary, the 10 digits, the 4 root digits);
the target logit difference; mean TV and KL between the output distributions
of the 4 queries; which simple rule reproduces the model's prediction; the
formed output preference P(roots) and K = log P(roots). All CIs resample whole
bodies. Noise floor (10.3): every per-question metric is computed twice, once
with all 2000 questions in one batch and once with each body's 4 questions as
their own batch; eps = max |difference|. A mean effect with |mean| <= 10 eps is
reported as numerically indistinguishable.
"""

import numpy as np
import torch

from common import READ_POS, summary

DIGITS = torch.arange(ord("0"), ord("9") + 1)
EFFECTS = ("dp_full", "dp_digit", "dp_root", "tv", "kl")


def readout_logits(runner, x, batch=None, n_loops=None):
    if batch is None:
        return runner.run(x, n_loops=n_loops)[0][:, READ_POS].double()
    return torch.cat(
        [runner.run(x[i : i + batch], n_loops=n_loops)[0][:, READ_POS] for i in range(0, len(x), batch)]
    ).double()


def per_question(L, y, roots, bid):
    """L (4N, V) readout logits ordered body-major; returns dict of (4N,) arrays."""
    N = len(roots)
    V = L.shape[1]
    P = torch.softmax(L, -1).view(N, 4, V)
    logP = torch.log_softmax(L, -1).view(N, 4, V)
    yq = y.view(N, 4)
    out = {}
    # p(answer of query q | query q') for all q, q'  -> (N, 4, 4) [q, q']
    def cross(Pn):
        return torch.stack([Pn[:, :, :].gather(2, yq[:, q].view(N, 1, 1).expand(N, 4, 1)).squeeze(2)
                            for q in range(4)], 1)  # (N, q, q')

    off = ~torch.eye(4, dtype=torch.bool)
    for name, Pn in (
        ("full", P),
        ("digit", _renorm(P, DIGITS)),
        ("root", _renorm_rows(P, roots)),
    ):
        C = cross(Pn)
        own = C.diagonal(dim1=1, dim2=2)
        other = (C * off).sum(2) / 3
        out[f"p_correct_{name}"] = own.reshape(-1)
        out[f"dp_{name}"] = (own - other).reshape(-1)
    Lr = L.view(N, 4, V).gather(2, roots.view(N, 1, 4).expand(N, 4, 4))  # logits of the 4 roots
    is_ans = torch.eye(4, dtype=torch.bool).view(1, 4, 4).expand(N, 4, 4)
    out["logit_diff"] = ((Lr * is_ans).sum(2) - (Lr * ~is_ans).sum(2) / 3).reshape(-1)
    tv = 0.5 * (P.unsqueeze(2) - P.unsqueeze(1)).abs().sum(-1)  # (N, q, q')
    kl = (P.unsqueeze(2) * (logP.unsqueeze(2) - logP.unsqueeze(1))).sum(-1)
    out["tv"] = ((tv * off).sum(2) / 3).reshape(-1)
    out["kl"] = ((kl * off).sum(2) / 3).reshape(-1)
    mass = P.gather(2, roots.view(N, 1, 4).expand(N, 4, 4)).sum(2)
    out["p_roots"] = mass.reshape(-1)
    out["K"] = mass.log().reshape(-1)
    pred = L.argmax(-1)
    out["acc"] = (pred == y).double()
    out["pred_in_roots"] = (pred.view(N, 4, 1) == roots.view(N, 1, 4)).any(-1).double().reshape(-1)
    return {k: v.numpy() for k, v in out.items()}, pred


def _renorm(P, idx):
    Q = torch.zeros_like(P)
    Q[..., idx] = P[..., idx] / P[..., idx].sum(-1, keepdim=True)
    return Q


def _renorm_rows(P, roots):
    N = P.shape[0]
    mask = torch.zeros_like(P, dtype=torch.bool)
    mask.scatter_(2, roots.view(N, 1, 4).expand(N, 4, 4), True)
    Q = P * mask
    return Q / Q.sum(-1, keepdim=True)


def rule_agreement(pred, roots, pref):
    """Share of questions whose prediction equals each simple rule's choice."""
    N = len(roots)
    pr = pred.view(N, 4)
    r = roots
    rules = {f"statement_{k + 1}_digit": r[:, k] for k in range(4)}
    rules["largest_root"] = r.max(1).values
    rules["smallest_root"] = r.min(1).values
    rules["root_nearest_query(=statement_4)"] = r[:, 3]
    rules["root_farthest_query(=statement_1)"] = r[:, 0]
    rank = torch.tensor([pref.get(int(d), 0.0) for d in range(256)])
    rules["model_digit_preference(fit-set)"] = r.gather(1, rank[r].argmax(1, keepdim=True)).squeeze(1)
    return {k: (pr == v.view(N, 1)).double().reshape(-1).numpy() for k, v in rules.items()}


def digit_preference(pred, roots):
    """P(pred = d | d is a root), estimated on the fit set."""
    N = len(roots)
    pr = pred.view(N, 4)
    pref = {}
    for d in range(ord("0"), ord("9") + 1):
        present = (roots == d).any(1)
        if present.any():
            pref[d] = float((pr[present] == d).double().mean())
    return pref


def run_d1(runner, ev, fit, om_ref_loops=(1, 2, 8)):
    x, y, slot, bid, roots = ev
    La = readout_logits(runner, x)
    Lb = readout_logits(runner, x, batch=4)
    qa, pred = per_question(La, y, roots, bid)
    qb, _ = per_question(Lb, y, roots, bid)
    groups = bid.numpy()
    eps = {k: float(np.abs(qa[k] - qb[k]).max()) for k in qa}
    res = {"metrics": {k: summary(v, groups) for k, v in qa.items()}, "noise_eps": eps}
    res["indistinguishable"] = {
        k: abs(res["metrics"][k]["mean"]) <= 10 * eps[k] for k in EFFECTS
    }
    Lf = readout_logits(runner, fit[0])
    pref = digit_preference(Lf.argmax(-1), fit[4])
    res["rules"] = {k: summary(v, groups) for k, v in rule_agreement(pred, roots, pref).items()}
    res["digit_preference_fit"] = {chr(k): v for k, v in pref.items()}
    N = len(roots)
    res["argmax_same_for_all_4_queries"] = float((pred.view(N, 4) == pred.view(N, 4)[:, :1]).all(1).double().mean())
    if runner.arm == "openmythos":
        res["reference_loops"] = {}
        for T in om_ref_loops:
            qT, _ = per_question(readout_logits(runner, x, n_loops=T), y, roots, bid)
            res["reference_loops"][str(T)] = {k: summary(qT[k], groups) for k in ("acc", "tv", "dp_root")}
    return res, qa
