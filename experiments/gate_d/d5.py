"""
D5: learning signal from gradients, computed and never applied
(PREREGISTRATION 8.7, 9.1, 9.2, 9.5).

(a) per-question gradients on diag_eval families (online per-body
    accumulation; body means kept only for this state's Gram matrices):
    V_b = tr Var_b(gbar(b)), S = E_b[(1/4) sum_q |g(b,q) - gbar(b)|^2],
    S/(V_b+S), cosine between gradients of different queries of one body,
    predicted tr Var of O / P / F batches; activation gradients dL/dx_p at the
    emb record point (position 17 vs digit positions); the tied embed=head
    gradient split into input side and output side.
(b) R independent batches of 64 supervised answers per scheme O / P / F from
    pool_b: measured tr Var(G) (unbiased, bootstrap over batches) vs the
    prediction from (a); projection s = -G.u on u = grad J / |grad J|.
(c) instantaneous raw-gradient local direction (not the historical AdamW
    update): d = -E[grad L] on pool_c, grad J on diag_fit, grad K, grad L_roots,
    grad L_within on pool_c; d.grad J and d.grad K with body-bootstrap CIs;
    cosine of the decoupled weight-decay direction -theta with grad J, grad K.
Generic pieces take gradient callbacks so that synthetic_d5.py can run the
same estimators on a model with analytic answers.
"""

import numpy as np
import torch
import torch.nn.functional as F

from common import DIGIT_POS, Q_POS, READ_POS, encode, flat_grad, flat_params, group_index

# ------------------------------------------------------------ estimators


def gram_trvar(G, idx, n_boot=2000, seed=0):
    """G (n, P) float32 rows = samples. Unbiased tr Var of the rows on the
    coordinates idx, and its bootstrap distribution (resampling rows)."""
    n = G.shape[0]
    K = torch.zeros(n, n, dtype=torch.double)
    for c0 in range(0, len(idx), 65536):  # Gram matrix in float64, column chunks
        Gs = G[:, idx[c0 : c0 + 65536]].double()
        K += Gs @ Gs.T
    K = K.numpy()
    est = n / (n - 1) * (np.mean(np.diag(K)) - K.mean())
    rng = np.random.default_rng(seed)
    C = np.stack([np.bincount(rng.integers(0, n, n), minlength=n) for _ in range(n_boot)]).astype(np.float64)
    diag = C @ np.diag(K) / n
    allm = ((C @ K) * C).sum(1) / n**2
    boot = n / (n - 1) * (diag - allm)
    return float(est), boot


class FamilyAccumulator:
    """Online per-body statistics of the 4 per-question gradients."""

    def __init__(self, idx, n_bodies, P):
        self.idx = idx
        self.G = torch.zeros(n_bodies, P)  # body means (Gram matrices only)
        self.S = {g: [] for g in idx}
        self.cos = {g: [] for g in idx}
        self.n = 0

    def add(self, g4):
        gbar = g4.mean(0)
        self.G[self.n] = gbar
        r = g4 - gbar
        for g, ix in self.idx.items():
            self.S[g].append(float((r[:, ix].double() ** 2).sum(1).mean()))
            sub = g4[:, ix].double()
            nrm = sub.norm(dim=1).clamp_min(1e-30)
            c = (sub @ sub.T) / (nrm[:, None] * nrm[None, :])
            self.cos[g].append(float(c[~torch.eye(4, dtype=torch.bool)].mean()))
        self.n += 1

    def finish(self, n_boot=2000):
        G = self.G[: self.n]
        out = {}
        rng = np.random.default_rng(1)
        boot_rows = [rng.integers(0, self.n, self.n) for _ in range(n_boot)]
        for g, ix in self.idx.items():
            V, Vboot = gram_trvar(G, ix, n_boot=n_boot, seed=0)
            S_b = np.asarray(self.S[g])
            # joint bootstrap: same resampled bodies for V and S (gram_trvar uses seed 0)
            rng0 = np.random.default_rng(0)
            Sboot = np.asarray([S_b[rng0.integers(0, self.n, self.n)].mean() for _ in range(n_boot)])
            S = float(S_b.mean())
            pred = lambda V_, S_: {  # noqa: E731
                "O": (V_ + S_) / 64, "P": (V_ + S_) / 64 + (V_ - S_ / 3) / 64, "F": V_ / 16}
            pb = pred(Vboot, Sboot)
            ci = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]  # noqa: E731
            cosv = np.asarray(self.cos[g])
            out[g] = {
                "V_b": V, "V_b_ci95": ci(Vboot), "S": S, "S_ci95": ci(Sboot),
                "S_share": S / (V + S) if V + S > 0 else None,
                "S_minus_3V": S - 3 * V, "S_minus_3V_ci95": ci(Sboot - 3 * Vboot),
                "pred_trvar": {k: float(v) for k, v in pred(V, S).items()},
                "pred_trvar_ci95": {k: ci(v) for k, v in pb.items()},
                "cos_between_queries": float(cosv.mean()),
                "cos_ci95": ci(np.asarray([cosv[r].mean() for r in boot_rows])),
            }
        return out


def batch_stats(grad_batch, batches, idx, u, n_boot=2000):
    """grad_batch(batch) -> mean gradient over its 64 answers (flat). Returns
    per-group tr Var with bootstrap over batches, and s = -G.u statistics."""
    R = len(batches)
    G = None
    s = []
    for r, b in enumerate(batches):
        g = grad_batch(b)
        if G is None:
            G = torch.zeros(R, g.numel())
        G[r] = g
        s.append(float(-(g.double() @ u)))
    out = {"trvar": {}, "trvar_boot": {}}
    for g, ix in idx.items():
        est, boot = gram_trvar(G, ix, n_boot=n_boot, seed=2)
        out["trvar"][g] = est
        out["trvar_boot"][g] = boot
    s = np.asarray(s)
    rng = np.random.default_rng(3)
    mb = [s[rng.integers(0, R, R)].mean() for _ in range(n_boot)]
    out["s_along_u"] = {"mean": float(s.mean()), "std": float(s.std(ddof=1)),
                        "snr": float(s.mean() / s.std(ddof=1)), "p_positive": float((s > 0).mean()),
                        "mean_ci95": [float(np.percentile(mb, 2.5)), float(np.percentile(mb, 97.5))]}
    del G
    return out


# ------------------------------------------------------------ model gradients


class ModelGrads:
    def __init__(self, model):
        self.m = model
        names = [n for n, _ in model.named_parameters()]
        assert names[0] == "embed.weight", names[0]  # tied embed=head, listed once
        self.params = [p for _, p in model.named_parameters()]
        self.idx, self.P = group_index(model)
        self.store = {}
        model.embed.register_forward_hook(self._emb_hook)
        model.norm.register_forward_hook(self._norm_hook)

    def _emb_hook(self, mod, inp, out):
        if torch.is_grad_enabled():
            out.retain_grad()
        self.store["emb"] = out

    def _norm_hook(self, mod, inp, out):
        self.store["fin"] = out.detach()

    def readout(self, x):
        return self.m(x)[:, READ_POS]

    def per_question(self, x, y):
        """(4, P) per-question gradients, activation-gradient norms and the
        tied-weight split, from one batched forward and 4 backward passes."""
        logits = self.readout(x)
        losses = F.cross_entropy(logits, y, reduction="none")
        emb = self.store["emb"]
        fin = self.store["fin"][:, READ_POS]
        rows, act, tied = [], [], []
        W = self.m.embed.weight
        for q in range(len(x)):
            gr = torch.autograd.grad(losses[q], self.params + [emb, logits], retain_graph=True,
                                     allow_unused=True)
            gr = [torch.zeros_like(p) if t is None else t for t, p in zip(gr, self.params + [emb, logits])]
            g = torch.cat([t.reshape(-1) for t in gr[: len(self.params)]])
            rows.append(g)
            ge = gr[-2][q]  # (T, D) activation gradient of question q
            act.append({"pos17": ge[Q_POS].norm().item(),
                        "digits": [ge[p].norm().item() for p in DIGIT_POS]})
            inp_side = torch.zeros_like(W).index_add_(0, x[q], ge)
            out_side = torch.outer(gr[-1][q], fin[q])
            tied.append({"input_side": inp_side.norm().item(), "output_side": out_side.norm().item(),
                         "check": (inp_side + out_side - gr[0]).abs().max().item()})
        return torch.stack(rows), act, tied

    def mean_grad(self, x, y, loss_fn="ce"):
        self.m.zero_grad(set_to_none=True)
        logits = self.readout(x)
        loss = F.cross_entropy(logits, y)
        loss.backward()
        return flat_grad(self.m)

    def grad_of(self, fn):
        self.m.zero_grad(set_to_none=True)
        fn().backward()
        return flat_grad(self.m)


def _prompts(rows, which):
    ps, ys = [], []
    for r, slots in zip(rows, which):
        for k in slots:
            ps.append(r["body"] + "|" + r["queries"][k] + "?")
            ys.append(ord(r["answers"][k]))
    return encode(ps), torch.tensor(ys)


def J_value(mg, rows):
    """Query use: mean over bodies of (1/4) sum_q [log p(y_q|q) - mean_{q'!=q} log p(y_q|q')]."""
    x, y = _prompts(rows, [range(4)] * len(rows))
    N = len(rows)
    logP = torch.log_softmax(mg.readout(x), -1).view(N, 4, -1)
    yq = y.view(N, 4)
    M = torch.stack([logP[:, :, :].gather(2, yq[:, q].view(N, 1, 1).expand(N, 4, 1)).squeeze(2)
                     for q in range(4)], 1)  # (N, q, q')
    off = ~torch.eye(4, dtype=torch.bool)
    J = (M.diagonal(dim1=1, dim2=2) - (M * off).sum(2) / 3).mean()
    return J


def chunked_grad(mg, rows, fn, chunk=125):
    """Gradient of the mean over all rows of fn(rows_chunk) (a per-chunk mean)."""
    total = None
    for i in range(0, len(rows), chunk):
        part = rows[i : i + chunk]
        g = mg.grad_of(lambda: fn(part) * (len(part) / len(rows)))
        total = g if total is None else total + g
    return total


def root_terms(mg, rows):
    x, y = _prompts(rows, [range(4)] * len(rows))
    logP = torch.log_softmax(mg.readout(x), -1)
    roots = torch.tensor([[ord(a) for a in r["answers"]] for r in rows]).repeat_interleave(4, 0)
    lpr = torch.logsumexp(logP.gather(1, roots), -1)  # log P(roots)
    lpy = logP.gather(1, y.view(-1, 1)).squeeze(1)
    return {"K": lpr.mean(), "L_roots": (-lpr).mean(), "L_within": (-(lpy - lpr)).mean()}


def run_d5(model, ev_rows, fit_rows, pool_b, pool_c, n_bodies_a=500, R=200, n_boot=2000):
    import time

    mg = ModelGrads(model)
    idx = mg.idx
    res = {"seconds": {}}
    t0 = time.time()
    # ---------------- (c) directions first (u is needed by (b))
    gJ = chunked_grad(mg, fit_rows, lambda part: J_value(mg, part)).double()
    with torch.no_grad():
        J0 = float(J_value(mg, fit_rows))
    gK = chunked_grad(mg, pool_c, lambda part: root_terms(mg, part)["K"]).double()
    gLr = chunked_grad(mg, pool_c, lambda part: root_terms(mg, part)["L_roots"]).double()
    gLw = chunked_grad(mg, pool_c, lambda part: root_terms(mg, part)["L_within"]).double()
    theta = flat_params(model).double()
    d = torch.zeros(mg.P, dtype=torch.double)
    per_body = {g: {"dJ": [], "dK": []} for g in idx}
    for r in pool_c:
        x, y = _prompts([r], [range(4)])
        db = -mg.mean_grad(x, y).double()
        d += db / len(pool_c)
        for g, ix in idx.items():
            per_body[g]["dJ"].append(float(db[ix] @ gJ[ix]))
            per_body[g]["dK"].append(float(db[ix] @ gK[ix]))
    cos = lambda a, b: float(a @ b / (a.norm() * b.norm())) if a.norm() > 0 and b.norm() > 0 else None  # noqa: E731
    rng = np.random.default_rng(4)
    nb = len(pool_c)
    boots = [rng.integers(0, nb, nb) for _ in range(n_boot)]
    ci = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]  # noqa: E731
    dirs = {}
    for g, ix in idx.items():
        dJ, dK = np.asarray(per_body[g]["dJ"]), np.asarray(per_body[g]["dK"])
        dirs[g] = {
            "d_dot_gradJ": float(dJ.mean()), "d_dot_gradJ_ci95": ci([dJ[b].mean() for b in boots]),
            "d_dot_gradK": float(dK.mean()), "d_dot_gradK_ci95": ci([dK[b].mean() for b in boots]),
            "cos_d_gradJ": cos(d[ix], gJ[ix]), "cos_d_gradK": cos(d[ix], gK[ix]),
            "norm_grad_L_roots": float(gLr[ix].norm()), "norm_grad_L_within": float(gLw[ix].norm()),
            "cos_grad_L_within_gradJ": cos(-gLw[ix], gJ[ix]),
            "weight_decay_cos_gradJ": cos(-theta[ix], gJ[ix]), "weight_decay_cos_gradK": cos(-theta[ix], gK[ix]),
            "norm_gradJ": float(gJ[ix].norm()), "norm_d": float(d[ix].norm()),
        }
    with torch.no_grad():
        rt = root_terms(mg, pool_c)
    res["c_local_direction"] = {"note": "instantaneous raw-gradient local direction, not the historical AdamW update",
                                "J_fit": J0, "K_pool_c": float(rt["K"]), "L_roots": float(rt["L_roots"]),
                                "L_within": float(rt["L_within"]), "groups": dirs}
    u = gJ / gJ.norm()
    res["seconds"]["c"] = time.time() - t0
    t0 = time.time()
    # ---------------- (a) per-question gradients
    acc = FamilyAccumulator(idx, n_bodies_a, mg.P)
    acts, tied = [], []
    for r in ev_rows[:n_bodies_a]:
        x, y = _prompts([r], [range(4)])
        g4, a, t = mg.per_question(x, y)
        acc.add(g4)
        acts += a
        tied += t
    res["a_per_question"] = acc.finish(n_boot=n_boot)
    del acc
    p17 = np.asarray([a["pos17"] for a in acts])
    dig = np.asarray([a["digits"] for a in acts])  # (4N, 4) in slot order
    slot = np.tile(np.arange(4), len(acts) // 4)
    own = dig[np.arange(len(acts)), slot]
    others = (dig.sum(1) - own) / 3
    res["a_activation_grad"] = {
        "pos17_mean": float(p17.mean()), "queried_digit_mean": float(own.mean()),
        "other_digits_mean": float(others.mean()), "ratio_pos17_to_digits": float(p17.mean() / dig.mean()),
    }
    res["a_tied_split"] = {
        "input_side_mean_norm": float(np.mean([t["input_side"] for t in tied])),
        "output_side_mean_norm": float(np.mean([t["output_side"] for t in tied])),
        "max_check_diff": float(max(t["check"] for t in tied)),
    }
    if res["a_tied_split"]["max_check_diff"] > 1e-6:
        raise RuntimeError(f"tied-weight split check failed: {res['a_tied_split']['max_check_diff']}")
    res["seconds"]["a"] = time.time() - t0
    t0 = time.time()
    # ---------------- (b) batch noise of O / P / F
    by_scheme = {}
    for row in pool_b:
        by_scheme.setdefault(row["scheme"], {}).setdefault(row["batch"], []).append(row)
    res["b_batches"] = {}
    measured_boot = {}
    for scheme in ("O", "P", "F"):
        batches = [by_scheme[scheme][b] for b in range(R)]
        st = batch_stats(lambda rows: mg.mean_grad(*_prompts(rows, [r["slots"] for r in rows])),
                         batches, idx, u, n_boot=n_boot)
        measured_boot[scheme] = st.pop("trvar_boot")
        res["b_batches"][scheme] = st
    cmp = {}
    for g in idx:
        row = {}
        for scheme in ("O", "P", "F"):
            mb = measured_boot[scheme][g]
            m_ci = [float(np.percentile(mb, 2.5)), float(np.percentile(mb, 97.5))]
            p_ci = res["a_per_question"][g]["pred_trvar_ci95"][scheme]
            row[scheme] = {"measured": res["b_batches"][scheme]["trvar"][g], "measured_ci95": m_ci,
                           "predicted": res["a_per_question"][g]["pred_trvar"][scheme], "predicted_ci95": p_ci,
                           "cis_overlap": not (m_ci[1] < p_ci[0] or p_ci[1] < m_ci[0])}
        diff = measured_boot["P"][g] - measured_boot["O"][g]
        row["P_minus_O_ci95"] = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]
        diffF = measured_boot["F"][g] - measured_boot["O"][g]
        row["F_minus_O_ci95"] = [float(np.percentile(diffF, 2.5)), float(np.percentile(diffF, 97.5))]
        cmp[g] = row
    res["b_vs_a"] = cmp
    res["seconds"]["b"] = time.time() - t0
    return res
