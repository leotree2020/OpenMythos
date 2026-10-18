"""
M1: query dependence of the output (PREREGISTRATION 4; Gate D D1 for any
family size K). Per question (body b, query q, answer y_q) on diag_eval
families: p(y_q | q) vs the mean of p(y_q | q') over the other K-1 queries,
in three normalizations (vocabulary, 10 digits, K roots); target-logit
difference; mean TV / KL between the K queries; query use J per question
(log p(y_q | q) - mean_{q'!=q} log p(y_q | q'); its body mean is Gate D's J);
P(roots), K = log P(roots); accuracy; query insensitivity (all K predictions
equal) and query-swap both-correct (all K correct) per body. Noise floor as
Gate D 10.3: everything computed twice (one batch / each body's K questions as
its own batch), eps = max |difference|; |mean| <= 10 eps is reported as
numerically indistinguishable. Simple prediction rules are descriptive only;
the formal baseline is the fixed 50% of revision 2 (10.2).
"""

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
import numpy as np
import torch

from common import summary  # gate_d (archived)

DIGITS = torch.arange(ord("0"), ord("9") + 1)
EFFECTS = ("dp_full", "dp_digit", "dp_root", "tv", "kl", "J")


def readout_logits(runner, x, g, batch=None, n_loops=None):
    if batch is None:
        return runner.run(x, n_loops=n_loops)[0][:, g.READ_POS].double()
    return torch.cat([runner.run(x[i : i + batch], n_loops=n_loops)[0][:, g.READ_POS]
                      for i in range(0, len(x), batch)]).double()


def _renorm(P, idx):
    Q = torch.zeros_like(P)
    Q[..., idx] = P[..., idx] / P[..., idx].sum(-1, keepdim=True)
    return Q


def _renorm_rows(P, roots, K):
    N = P.shape[0]
    mask = torch.zeros_like(P, dtype=torch.bool)
    mask.scatter_(2, roots.view(N, 1, K).expand(N, K, K), True)
    Q = P * mask
    return Q / Q.sum(-1, keepdim=True)


def per_question(L, y, roots, K):
    """L (KN, V) readout logits, body-major. Returns dict of (KN,) arrays and
    the predictions. For K = 4 this is gate_d d1.per_question (checked by the
    equivalence test), plus J."""
    N = len(roots)
    V = L.shape[1]
    P = torch.softmax(L, -1).view(N, K, V)
    logP = torch.log_softmax(L, -1).view(N, K, V)
    yq = y.view(N, K)
    off = ~torch.eye(K, dtype=torch.bool)

    def cross(Pn):  # (N, q, q'): p(answer of q | query q')
        return torch.stack([Pn.gather(2, yq[:, q].view(N, 1, 1).expand(N, K, 1)).squeeze(2)
                            for q in range(K)], 1)

    out = {}
    for name, Pn in (("full", P), ("digit", _renorm(P, DIGITS)), ("root", _renorm_rows(P, roots, K))):
        C = cross(Pn)
        own = C.diagonal(dim1=1, dim2=2)
        other = (C * off).sum(2) / (K - 1)
        out[f"p_correct_{name}"] = own.reshape(-1)
        out[f"dp_{name}"] = (own - other).reshape(-1)
    Cl = cross(logP)
    out["J"] = (Cl.diagonal(dim1=1, dim2=2) - (Cl * off).sum(2) / (K - 1)).reshape(-1)
    Lr = L.view(N, K, V).gather(2, roots.view(N, 1, K).expand(N, K, K))
    is_ans = torch.eye(K, dtype=torch.bool).view(1, K, K).expand(N, K, K)
    out["logit_diff"] = ((Lr * is_ans).sum(2) - (Lr * ~is_ans).sum(2) / (K - 1)).reshape(-1)
    tv = 0.5 * (P.unsqueeze(2) - P.unsqueeze(1)).abs().sum(-1)
    kl = (P.unsqueeze(2) * (logP.unsqueeze(2) - logP.unsqueeze(1))).sum(-1)
    out["tv"] = ((tv * off).sum(2) / (K - 1)).reshape(-1)
    out["kl"] = ((kl * off).sum(2) / (K - 1)).reshape(-1)
    mass = P.gather(2, roots.view(N, 1, K).expand(N, K, K)).sum(2)
    out["p_roots"] = mass.reshape(-1)
    out["K"] = mass.log().reshape(-1)
    pred = L.argmax(-1)
    out["acc"] = (pred == y).double()
    out["pred_in_roots"] = (pred.view(N, K, 1) == roots.view(N, 1, K)).any(-1).double().reshape(-1)
    return {k: v.numpy() for k, v in out.items()}, pred


def digit_preference(pred, roots, K):
    """P(pred = d | d is a root), on the fit set (Gate D D1, descriptive)."""
    pr = pred.view(len(roots), K)
    pref = {}
    for d in range(ord("0"), ord("9") + 1):
        present = (roots == d).any(1)
        if present.any():
            pref[d] = float((pr[present] == d).double().mean())
    return pref


def rule_agreement(pred, roots, pref, K):
    N = len(roots)
    pr = pred.view(N, K)
    rules = {f"statement_{k + 1}_digit": roots[:, k] for k in range(K)}
    rules["largest_root"] = roots.max(1).values
    rules["smallest_root"] = roots.min(1).values
    rank = torch.tensor([pref.get(int(d), 0.0) for d in range(256)])
    rules["model_digit_preference(fit-set)"] = roots.gather(1, rank[roots].argmax(1, keepdim=True)).squeeze(1)
    return {k: (pr == v.view(N, 1)).double().reshape(-1).numpy() for k, v in rules.items()}


def run_m1(runner, ev, fit, g, om_ref_loops=(1, 2, 8)):
    x, y, slot, bid, roots = ev
    K = g.K
    La = readout_logits(runner, x, g)
    Lb = readout_logits(runner, x, g, batch=K)
    qa, pred = per_question(La, y, roots, K)
    qb, _ = per_question(Lb, y, roots, K)
    groups = bid.numpy()
    eps = {k: float(np.abs(qa[k] - qb[k]).max()) for k in qa}
    res = {"metrics": {k: summary(v, groups) for k, v in qa.items()}, "noise_eps": eps}
    res["indistinguishable"] = {k: abs(res["metrics"][k]["mean"]) <= 10 * eps[k] for k in EFFECTS}
    N = len(roots)
    P = pred.view(N, K)
    same = (P == P[:, :1]).all(1).double().numpy()
    both = (P == y.view(N, K)).all(1).double().numpy()
    bodies = np.arange(N)
    res["query_insensitivity"] = summary(same, bodies)
    res["query_swap_all_correct"] = summary(both, bodies)
    Lf = readout_logits(runner, fit[0], g)
    pref = digit_preference(Lf.argmax(-1), fit[4], K)
    res["rules_descriptive"] = {k: summary(v, groups) for k, v in rule_agreement(pred, roots, pref, K).items()}
    res["digit_preference_fit"] = {chr(k): v for k, v in pref.items()}
    if runner.arm == "openmythos":
        res["reference_loops"] = {}
        for T in om_ref_loops:
            qT, _ = per_question(readout_logits(runner, x, g, n_loops=T), y, roots, K)
            res["reference_loops"][str(T)] = {k: summary(qT[k], groups) for k in ("acc", "tv", "dp_root")}
    return res
