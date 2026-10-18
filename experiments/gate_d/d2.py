"""
D2: linear probes on frozen hidden states (PREREGISTRATION 3, 8.4).

    P0  emb, position 17            query letter (52)       positive control, must be >= 95%
    P1  each probe point, pos 18    queried statement slot (4)        decision baseline 0.25
    P2  each probe point, digit     letter of that statement (52)     baseline 1/52
        positions 2/6/10/14 (one copy per body: positions < 17 do not depend on the query)
    P3  each probe point, pos 18    answer digit (10)        baselines 0.10 and 0.25 (decision)

Multinomial logistic regression on standardized features (fit-set mean/std),
loss = mean CE + 1e-3 * ||W||^2, full-batch L-BFGS to convergence; fit on
diag_fit, accuracy on diag_eval with body-grouped bootstrap CIs. Grouped
shuffled-label control for every probe; planted-signal sensitivity at the last
probe point; one-hidden-layer MLP probe (width 256, fixed settings) only where
the linear probe gives "not detected", voided unless the same MLP is at
baseline on the emb record point (P1/P3 at position 18; P2 at the digit
positions, an analogous control added in the analysis plan).
OpenMythos loop points use only complete families: bodies for which that
loop was executed for all 4 queries (revision 4; was per question).
"""

import numpy as np
import torch
import torch.nn.functional as F

from common import DIGIT_POS, LETTERS, Q_POS, READ_POS, complete_family_mask, grouped_bootstrap
from runner import probe_points

LAMBDA = 1e-3
ALPHAS = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5)
C_DECISION = {"P0": 1 / 52, "P1": 0.25, "P2": 1 / 52, "P3": 0.25}
N_CLASSES = {"P0": 52, "P1": 4, "P2": 52, "P3": 10}


def fit_linear(X, y, C):
    mu, sd = X.mean(0), X.std(0).clamp_min(1e-6)
    Z = ((X - mu) / sd).double()
    W = torch.zeros(C, Z.shape[1], dtype=torch.double, requires_grad=True)
    b = torch.zeros(C, dtype=torch.double, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], lr=1, max_iter=500, tolerance_grad=1e-7,
                            tolerance_change=1e-12, history_size=20, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(Z @ W.T + b, y) + LAMBDA * (W * W).sum()
        loss.backward()
        return loss

    for _ in range(10):  # restart until the gradient criterion is met
        opt.step(closure)
        gn = torch.cat([W.grad.reshape(-1), b.grad]).abs().max().item()
        if gn <= 1e-6:
            break
    return {"mu": mu, "sd": sd, "W": W.detach(), "b": b.detach(), "grad_max": gn}


def predict_linear(p, X):
    return ((((X - p["mu"]) / p["sd"]).double()) @ p["W"].T + p["b"]).argmax(-1)


def fit_mlp(X, y, C, seed=0):
    mu, sd = X.mean(0), X.std(0).clamp_min(1e-6)
    Z = (X - mu) / sd
    g = torch.Generator().manual_seed(seed)
    W1 = (torch.randn(256, Z.shape[1], generator=g) / Z.shape[1] ** 0.5).requires_grad_()
    b1 = torch.zeros(256, requires_grad=True)
    W2 = (torch.randn(C, 256, generator=g) / 16).requires_grad_()
    b2 = torch.zeros(C, requires_grad=True)
    opt = torch.optim.Adam([W1, b1, W2, b2], lr=1e-3, weight_decay=1e-4)
    for _ in range(500):
        opt.zero_grad()
        F.cross_entropy(F.relu(Z @ W1.T + b1) @ W2.T + b2, y).backward()
        opt.step()
    params = [t.detach() for t in (W1, b1, W2, b2)]
    return lambda X2: (F.relu(((X2 - mu) / sd) @ params[0].T + params[1]) @ params[2].T + params[3]).argmax(-1)


def acc_ci(correct, groups):
    c = correct.double().numpy()
    return {"acc": float(c.mean()), "ci95": grouped_bootstrap(c, groups), "n": int(len(c))}


def decide(r, shuffled, c):
    lo, hi = r["ci95"]
    if lo >= c + 0.5 * (1 - c) and (shuffled is None or lo > shuffled["ci95"][1]):
        return "检测到可线性解码的信息"
    if hi <= c + 0.10:
        return "未检测到足够的可线性解码信息"
    return "结果不确定"


def grouped_shuffle(y, groups, kind, seed=1):
    """kind 'within': permute labels inside each body; 'across': give every
    body the labels of another body (same within-body order)."""
    g = np.random.default_rng(seed)
    y = y.clone()
    uniq = np.unique(groups)
    members = {u: np.flatnonzero(groups == u) for u in uniq}
    if kind == "within":
        for u in uniq:
            idx = members[u]
            y[idx] = y[idx[g.permutation(len(idx))]]
        return y
    perm = g.permutation(uniq)
    out = y.clone()
    for u, v in zip(uniq, perm):
        a, b = members[u], members[v]
        n = min(len(a), len(b))
        out[a[:n]] = y[b[:n]]
    return out


def features(runner, fam, points):
    """Records at the probe points (positions READ_POS, Q_POS, DIGIT_POS) and
    per-question loop validity."""
    x = fam[0]
    rec = runner.run(x, record=set(points) | {f"valid{t}" for t in range(8)})[1]
    feats = {}
    for p in points:
        r = rec[p]
        feats[p] = {"read": r[:, READ_POS], "query": r[:, Q_POS], "digits": r[:, list(DIGIT_POS)]}
    valid = {}
    for p in points:
        if p.startswith("h") and p[1:].isdigit():
            # revision 4: complete families only (all 4 queries ran the loop)
            valid[p] = complete_family_mask(rec[f"valid{int(p[1:]) - 1}"])
        else:
            valid[p] = torch.ones(len(x), dtype=torch.bool)
    return feats, valid


def labels(fam, rows):
    x, y, slot, bid, roots = fam
    letters = torch.tensor([LETTERS.index(chr(c)) for c in x[:, Q_POS].tolist()])
    digit = y - ord("0")
    stmt_letters = torch.tensor([[LETTERS.index(r["queries"][k]) for k in range(4)] for r in rows])
    return {"P0": letters, "P1": slot, "P3": digit, "P2": stmt_letters}


def run_d2(runner, fit_fam, fit_rows, ev_fam, ev_rows):
    points = probe_points(runner.arm)
    Ff, Vf = features(runner, fit_fam, points)
    Fe, Ve = features(runner, ev_fam, points)
    Lf, Le = labels(fit_fam, fit_rows), labels(ev_fam, ev_rows)
    gf, ge = fit_fam[3].numpy(), ev_fam[3].numpy()
    first_f = torch.arange(0, len(gf), 4)  # first question of each body
    first_e = torch.arange(0, len(ge), 4)
    res = {"probes": {}, "mlp": {}, "planted": {}}

    def data(probe, p):
        """(Xfit, yfit, gfit, Xev, yev, gev) for a probe at point p."""
        if probe in ("P0", "P1", "P3"):
            key = "query" if probe == "P0" else "read"
            mf, me = Vf[p], Ve[p]
            return (Ff[p][key][mf], Lf[probe][mf], gf[mf.numpy()],
                    Fe[p][key][me], Le[probe][me], ge[me.numpy()])
        mf, me = Vf[p][first_f], Ve[p][first_e]
        Xf = Ff[p]["digits"][first_f][mf].reshape(-1, Ff[p]["digits"].shape[-1])
        Xe = Fe[p]["digits"][first_e][me].reshape(-1, Fe[p]["digits"].shape[-1])
        yf = Lf["P2"][mf].reshape(-1)
        ye = Le["P2"][me].reshape(-1)
        bf = np.repeat(np.flatnonzero(mf.numpy()), 4)
        be = np.repeat(np.flatnonzero(me.numpy()), 4)
        return Xf, yf, bf, Xe, ye, be

    plan = [("P0", "emb")] + [(pr, p) for pr in ("P1", "P2", "P3") for p in points]
    for probe, p in plan:
        Xf, yf, bf, Xe, ye, be = data(probe, p)
        key = f"{probe}@{p}"
        if len(np.unique(bf)) < 0.5 * len(fit_rows) or len(np.unique(be)) < 0.5 * len(ev_rows):
            res["probes"][key] = {"skipped": "loop not executed for most questions",
                                  "n_fit_bodies": int(len(np.unique(bf))), "n_eval_bodies": int(len(np.unique(be)))}
            continue
        C = N_CLASSES[probe]
        m = fit_linear(Xf, yf, C)
        r = acc_ci(predict_linear(m, Xe) == ye, be)
        r["fit_grad_max"] = m["grad_max"]
        kind = "within" if probe == "P1" else "across"
        ms = fit_linear(Xf, grouped_shuffle(yf, bf, kind), C)
        sh = acc_ci(predict_linear(ms, Xe) == ye, be)
        r["shuffled"] = sh
        c = C_DECISION[probe]
        r["baseline_decision"] = c
        if probe == "P3":
            r["baseline_unconditional"] = 0.10
        r["decision"] = decide(r, sh, c) if probe != "P0" else (
            "正对照通过" if r["acc"] >= 0.95 else "正对照未通过")
        res["probes"][key] = r

    # MLP probes where the linear probe detected nothing
    need = [k for k, v in res["probes"].items()
            if v.get("decision") == "未检测到足够的可线性解码信息"]
    if need:
        ctrl = {}
        for probe in ("P1", "P3", "P2"):
            Xf, yf, bf, Xe, ye, be = data(probe, "emb")
            f = fit_mlp(Xf, yf, N_CLASSES[probe])
            cr = acc_ci(f(Xe) == ye, be)
            cr["at_baseline"] = cr["ci95"][1] <= C_DECISION[probe] + 0.10
            ctrl[probe] = cr
        res["mlp"]["emb_controls"] = ctrl
        for key in need:
            probe, p = key.split("@")
            Xf, yf, bf, Xe, ye, be = data(probe, p)
            f = fit_mlp(Xf, yf, N_CLASSES[probe])
            r = acc_ci(f(Xe) == ye, be)
            r["void"] = not ctrl[probe]["at_baseline"]
            r["decision"] = "作废（控制未通过）" if r["void"] else decide(r, None, C_DECISION[probe])
            res["mlp"][key] = r

    # planted-signal sensitivity at the last probe point (P1 at pos 18, P2 at digits)
    last = points[-1]
    g = torch.Generator().manual_seed(7)
    for probe in ("P1", "P2"):
        Xf, yf, bf, Xe, ye, be = data(probe, last)
        C = N_CLASSES[probe]
        R = torch.randn(C, Xf.shape[1], generator=g)
        R = R / R.norm(dim=1, keepdim=True)
        scale = Xf.norm(dim=1).mean()
        out = {}
        for a in ALPHAS:
            m = fit_linear(Xf + a * scale * R[yf], yf, C)
            r = acc_ci(predict_linear(m, Xe + a * scale * R[ye]) == ye, be)
            r["decision"] = decide(r, None, C_DECISION[probe])
            out[str(a)] = r
        det = [a for a in ALPHAS if out[str(a)]["decision"] == "检测到可线性解码的信息"]
        res["planted"][f"{probe}@{last}"] = {"by_alpha": out, "smallest_detected_alpha": det[0] if det else None,
                                            "mean_feature_norm": float(scale)}
    return res
