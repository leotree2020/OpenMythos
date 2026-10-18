"""
M2: probes on frozen hidden states (PREREGISTRATION 4, revision 1 9.2).

    P0  emb, query position        query letter (52)          positive control >= 95%
    P1  each record point, readout queried statement slot (K) decision baseline 1/K
    P2  each record point, digit   letter of that statement (52) baseline 1/52
        positions (one copy per body: they precede the query)
    P3  each record point, readout answer digit (10)          baselines 0.10 and 1/K (decision)

Probe set per (probe, record point):
    linear_std  gate_d d2.fit_linear unchanged: fit-set standardization, then
                L-BFGS logistic regression, mean CE + 1e-3 ||W||^2 (continuity
                benchmark; every event and comparison uses it)
    linear_raw  identical except that the features are not standardized
                (the same lambda now acts on the raw scale: a contrast of
                feature scale x regularization, not of the information held)
    mlp         gate_d d2.fit_mlp unchanged, at every record point, with its
                own emb control on the same fit / eval questions
Decisions: gate_d d2.decide (revision 6 rules, c_hi for "detected", c0 for
"not detected"). The descriptive flag "明确高于随机" (lower CI bound >
c0 + 0.10 and > the shuffled control's upper bound) never replaces
"detected". OpenMythos loop points use D2-E existence semantics (single-
sample valid{t}, complete families) for every probe above. D2-F (functional
reachability, Gate D revision 6 13.3: a loop state enters only if it can
still reach the answer, R(t, readout) for P1 / P3, all K digit positions x
K queries reachable for P2) is computed as in Gate D, conditional and
descriptive only: linear_std with its shuffled control, and an MLP with its
own emb control where that linear probe detects nothing ("linear_std_F",
"mlp_F"). No event or judgment uses D2-F.
"""

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
import numpy as np
import torch
import torch.nn.functional as F

from d2 import (ALPHAS, LAMBDA, acc_ci, decide, fit_linear, fit_mlp, grouped_shuffle,  # gate_d
                majority_share, predict_linear)
from e_common import LETTERS
from e_masks import act_masks, complete, reachability
from runner import probe_points  # gate_d

DETECTED = "检测到可线性解码的信息"
NOT_DETECTED = "未检测到足够的可线性解码信息"


def fit_linear_raw(X, y, C):
    """gate_d d2.fit_linear without the standardization step (9.2)."""
    Z = X.double()
    W = torch.zeros(C, Z.shape[1], dtype=torch.double, requires_grad=True)
    b = torch.zeros(C, dtype=torch.double, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], lr=1, max_iter=500, tolerance_grad=1e-7,
                            tolerance_change=1e-12, history_size=20, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(Z @ W.T + b, y) + LAMBDA * (W * W).sum()
        loss.backward()
        return loss

    for _ in range(10):
        opt.step(closure)
        gn = torch.cat([W.grad.reshape(-1), b.grad]).abs().max().item()
        if gn <= 1e-6:
            break
    D = X.shape[1]
    return {"mu": torch.zeros(D), "sd": torch.ones(D), "W": W.detach(), "b": b.detach(), "grad_max": gn}


def baselines(K):
    return {"P0": 1 / 52, "P1": 1 / K, "P2": 1 / 52, "P3": 1 / K}, {"P0": 52, "P1": K, "P2": 52, "P3": 10}


def clearly_above_chance(r, shuffled, c0):
    lo = r["ci95"][0]
    return bool(lo > c0 + 0.10 and (shuffled is None or lo > shuffled["ci95"][1]))


def loop_index(p):
    return int(p[1:]) - 1 if p.startswith("h") and p[1:].isdigit() else None


def run_m2(runner, fit_fam, fit_rows, ev_fam, ev_rows, g, mlp_p13_when_detected=True,
           masks=None):
    """masks: optional precomputed (fit, eval) act masks (reused by M3/M6)."""
    K = g.K
    C_DECISION, N_CLASSES = baselines(K)
    points = probe_points(runner.arm)
    Mf, Me = masks if masks is not None else (act_masks(runner, fit_fam[0], g), act_masks(runner, ev_fam[0], g))

    def features(fam):
        rec = runner.run(fam[0], record=set(points))[1]
        return {p: {"read": rec[p][:, g.READ_POS], "query": rec[p][:, g.Q_POS],
                    "digits": rec[p][:, list(g.DIGIT_POS)]} for p in points}

    Ff, Fe = features(fit_fam), features(ev_fam)
    Rf, Re = reachability(Mf), reachability(Me)

    def labels(fam, rows):
        x, y, slot, bid, roots = fam
        return {"P0": torch.tensor([LETTERS.index(chr(c)) for c in x[:, g.Q_POS].tolist()]),
                "P1": slot, "P3": y - ord("0"),
                "P2": torch.tensor([[LETTERS.index(r["queries"][k]) for k in range(K)] for r in rows])}

    Lf, Le = labels(fit_fam, fit_rows), labels(ev_fam, ev_rows)
    gf, ge = fit_fam[3].numpy(), ev_fam[3].numpy()
    first_f, first_e = torch.arange(0, len(gf), K), torch.arange(0, len(ge), K)

    def masks_for(M, R, p, mode):
        n = M["valid"].shape[0]
        t = loop_index(p)
        if t is None:
            return torch.ones(n, dtype=torch.bool), torch.ones(n // K, dtype=torch.bool)
        if mode == "E":
            q = complete(M["valid"][:, t], K)
            return q, q.view(-1, K)[:, 0]
        q = complete(R[:, t, g.READ_POS], K)
        body = R[:, t][:, list(g.DIGIT_POS)].all(1).view(-1, K).all(1)  # K positions x K queries
        return q, body

    def data(probe, p, feat_point=None, mode="E"):
        fp = feat_point or p
        qf, bfm = masks_for(Mf, Rf, p, mode)
        qe, bem = masks_for(Me, Re, p, mode)
        if probe in ("P0", "P1", "P3"):
            key = "query" if probe == "P0" else "read"
            return (Ff[fp][key][qf], Lf[probe][qf], gf[qf.numpy()],
                    Fe[fp][key][qe], Le[probe][qe], ge[qe.numpy()])
        D = Ff[fp]["digits"].shape[-1]
        Xf = Ff[fp]["digits"][first_f][bfm].reshape(-1, D)
        Xe = Fe[fp]["digits"][first_e][bem].reshape(-1, D)
        return (Xf, Lf["P2"][bfm].reshape(-1), np.repeat(np.flatnonzero(bfm.numpy()), K),
                Xe, Le["P2"][bem].reshape(-1), np.repeat(np.flatnonzero(bem.numpy()), K))

    def linear(probe, Xf, yf, bf, Xe, ye, be, raw):
        C = N_CLASSES[probe]
        fit = fit_linear_raw if raw else fit_linear
        m = fit(Xf, yf, C)
        r = acc_ci(predict_linear(m, Xe) == ye, be)
        r["fit_grad_max"] = m["grad_max"]
        kind = "within" if probe == "P1" else "across"
        ms = fit(Xf, grouped_shuffle(yf, bf, kind), C)
        sh = acc_ci(predict_linear(ms, Xe) == ye, be)
        r["shuffled"] = sh
        c0 = C_DECISION[probe]
        mshare = majority_share(yf)
        c_hi = max(c0, mshare)
        r.update({"baseline_c0": c0, "baseline_c_hi": c_hi, "fit_majority_share": mshare,
                  "n_eval_bodies": int(len(np.unique(be)))})
        if probe == "P3":
            r["baseline_unconditional"] = 0.10
        if probe == "P0":
            r["decision"] = "正对照通过" if r["acc"] >= 0.95 else "正对照未通过"
        else:
            r["decision"] = decide(r, sh, c_hi, c0)
            r["clearly_above_chance(descriptive)"] = clearly_above_chance(r, sh, c0)
        return r

    def mlp(probe, p, mode="E"):
        c0 = C_DECISION[probe]
        Xf, yf, bf, Xe, ye, be = data(probe, p, mode=mode)
        Cf, cyf, cbf, Ce, cye, cbe = data(probe, p, feat_point="emb", mode=mode)
        assert torch.equal(yf, cyf) and torch.equal(ye, cye) and (bf == cbf).all() and (be == cbe).all()
        fc = fit_mlp(Cf, cyf, N_CLASSES[probe])
        ctrl = acc_ci(fc(Ce) == cye, cbe)
        ctrl["at_baseline"] = ctrl["ci95"][1] <= c0 + 0.10
        f = fit_mlp(Xf, yf, N_CLASSES[probe])
        r = acc_ci(f(Xe) == ye, be)
        r["emb_control"] = ctrl
        r["void"] = not ctrl["at_baseline"]
        c_hi = max(c0, majority_share(yf))
        r["decision"] = "作废（控制未通过）" if r["void"] else decide(r, None, c_hi, c0)
        r["clearly_above_chance(descriptive)"] = (not r["void"]) and clearly_above_chance(r, None, c0)
        return r

    res = {"linear_std": {}, "linear_raw": {}, "mlp": {}, "linear_std_F": {}, "mlp_F": {}, "planted": {},
           "semantics": "single-sample ACT masks; D2-E existence for every probe; D2-F conditional, descriptive"}
    plan = [("P0", "emb")] + [(pr, p) for pr in ("P1", "P2", "P3") for p in points]
    for probe, p in plan:
        key = f"{probe}@{p}"
        Xf, yf, bf, Xe, ye, be = data(probe, p)
        if len(np.unique(bf)) < 0.5 * len(fit_rows) or len(np.unique(be)) < 0.5 * len(ev_rows):
            skip = {"skipped": "fewer than half of the bodies are complete for this point",
                    "n_fit_bodies": int(len(np.unique(bf))), "n_eval_bodies": int(len(np.unique(be)))}
            res["linear_std"][key] = res["linear_raw"][key] = skip
            if probe != "P0":
                res["mlp"][key] = skip
            continue
        res["linear_std"][key] = linear(probe, Xf, yf, bf, Xe, ye, be, raw=False)
        res["linear_raw"][key] = linear(probe, Xf, yf, bf, Xe, ye, be, raw=True)
        if probe == "P0":
            continue
        if probe in ("P1", "P3") and not mlp_p13_when_detected and \
                res["linear_std"][key]["decision"] == DETECTED:
            res["mlp"][key] = {"skipped": "workload level: linear probe detected (P1/P3 only)"}
            continue
        res["mlp"][key] = mlp(probe, p)

    # D2-F (OpenMythos loop points; Gate D rules: MLP only where linear detects nothing)
    for probe, p in plan:
        if probe == "P0" or loop_index(p) is None:
            continue
        key = f"{probe}@{p}"
        Xf, yf, bf, Xe, ye, be = data(probe, p, mode="F")
        if len(np.unique(bf)) < 0.5 * len(fit_rows) or len(np.unique(be)) < 0.5 * len(ev_rows):
            res["linear_std_F"][key] = {"skipped": "fewer than half of the bodies are complete for this point",
                                        "n_fit_bodies": int(len(np.unique(bf))), "n_eval_bodies": int(len(np.unique(be)))}
            continue
        res["linear_std_F"][key] = linear(probe, Xf, yf, bf, Xe, ye, be, raw=False)
        if res["linear_std_F"][key]["decision"] == NOT_DETECTED:
            res["mlp_F"][key] = mlp(probe, p, mode="F")

    last = points[-1]
    gen = torch.Generator().manual_seed(7)
    for probe in ("P1", "P2"):
        Xf, yf, bf, Xe, ye, be = data(probe, last)
        C = N_CLASSES[probe]
        Rp = torch.randn(C, Xf.shape[1], generator=gen)
        Rp = Rp / Rp.norm(dim=1, keepdim=True)
        scale = Xf.norm(dim=1).mean()
        out = {}
        for a in ALPHAS:
            m = fit_linear(Xf + a * scale * Rp[yf], yf, C)
            r = acc_ci(predict_linear(m, Xe + a * scale * Rp[ye]) == ye, be)
            r["decision"] = decide(r, None, C_DECISION[probe])
            out[str(a)] = r
        det = [a for a in ALPHAS if out[str(a)]["decision"] == DETECTED]
        res["planted"][f"{probe}@{last}"] = {"by_alpha": out, "smallest_detected_alpha": det[0] if det else None,
                                            "mean_feature_norm": float(scale)}
    return res, (Mf, Me)
