"""
M5: learning signal from gradients, computed and never applied
(PREREGISTRATION 4 M5; Gate D D5 for any family size K). The estimators
gram_trvar / batch_stats and the per-scheme bootstrap seeds are gate_d d5's,
unchanged. Family-size dependent parts:
  (a) per-question gradients on the first n bodies of diag_eval:
      V_b, S = E_b[(1/K) sum_q |g(b,q) - gbar(b)|^2], S/(V_b+S), cosine
      between gradients of different queries of one body, predictions
          tr Var(G_O) = (V_b + S) / B
          tr Var(G_F) = K V_b / B
          tr Var(G_P) = (V_b + S) / B + (V_b - S/(K-1)) / B   (K = 4 only;
                        for K = 2 a pair is the full family)
  (b) R batches per scheme (K=2: O, F; K=4: O, P, F) from pool_b
  (c) d = -E[grad L] on pool_c, grad J on diag_fit, grad K, grad L_roots,
      grad L_within; d.grad J, d.grad K with body-bootstrap CIs; weight-decay
      cosines. Instantaneous raw-gradient local direction, not the AdamW
      update.
"""

import time

import numpy as np
import torch
import torch.nn.functional as F

from common import flat_grad, flat_params, group_index  # gate_d
from d5 import SCHEME_SEED, batch_stats, gram_trvar  # gate_d
from e_common import encode


class FamilyAccumulator:
    def __init__(self, idx, n_bodies, P, K, B=64):
        self.idx, self.K, self.B = idx, K, B
        self.G = torch.zeros(n_bodies, P)
        self.S = {g: [] for g in idx}
        self.cos = {g: [] for g in idx}
        self.n = 0

    def add(self, gK):
        gbar = gK.mean(0)
        self.G[self.n] = gbar
        r = gK - gbar
        off = ~torch.eye(self.K, dtype=torch.bool)
        for g, ix in self.idx.items():
            self.S[g].append(float((r[:, ix].double() ** 2).sum(1).mean()))
            sub = gK[:, ix].double()
            nrm = sub.norm(dim=1).clamp_min(1e-30)
            c = (sub @ sub.T) / (nrm[:, None] * nrm[None, :])
            self.cos[g].append(float(c[off].mean()))
        self.n += 1

    def finish(self, n_boot=2000):
        G, K, B = self.G[: self.n], self.K, self.B
        out = {}
        rng = np.random.default_rng(1)
        boot_rows = [rng.integers(0, self.n, self.n) for _ in range(n_boot)]

        def pred(V_, S_):
            p = {"O": (V_ + S_) / B, "F": K * V_ / B}
            if K == 4:
                p["P"] = (V_ + S_) / B + (V_ - S_ / (K - 1)) / B
            return p

        def ci(a):
            return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]

        for g, ix in self.idx.items():
            V, Vboot = gram_trvar(G, ix, n_boot=n_boot, seed=0)
            S_b = np.asarray(self.S[g])
            rng0 = np.random.default_rng(0)
            Sboot = np.asarray([S_b[rng0.integers(0, self.n, self.n)].mean() for _ in range(n_boot)])
            S = float(S_b.mean())
            pb = pred(Vboot, Sboot)
            cosv = np.asarray(self.cos[g])
            out[g] = {
                "V_b": V, "V_b_ci95": ci(Vboot), "S": S, "S_ci95": ci(Sboot),
                "S_share": S / (V + S) if V + S > 0 else None,
                "S_minus_(K-1)V": S - (K - 1) * V, "S_minus_(K-1)V_ci95": ci(Sboot - (K - 1) * Vboot),
                "pred_trvar": {k: float(v) for k, v in pred(V, S).items()},
                "pred_trvar_ci95": {k: ci(v) for k, v in pb.items()},
                "cos_between_queries": float(cosv.mean()),
                "cos_ci95": ci(np.asarray([cosv[r].mean() for r in boot_rows])),
                "cos_plateau_reference": -1 / (K - 1),
            }
        return out


class ModelGrads:
    def __init__(self, model, g):
        self.m, self.g = model, g
        names = [n for n, _ in model.named_parameters()]
        assert names[0] == "embed.weight", names[0]
        self.params = [p for _, p in model.named_parameters()]
        self.idx, self.P = group_index(model)
        self.store = {}
        self.hooks = [model.embed.register_forward_hook(self._emb_hook),
                      model.norm.register_forward_hook(self._norm_hook)]

    def remove(self):
        for h in self.hooks:
            h.remove()

    def _emb_hook(self, mod, inp, out):
        if torch.is_grad_enabled():
            out.retain_grad()
        self.store["emb"] = out

    def _norm_hook(self, mod, inp, out):
        self.store["fin"] = out.detach()

    def readout(self, x):
        return self.m(x)[:, self.g.READ_POS]

    def per_question(self, x, y):
        g = self.g
        logits = self.readout(x)
        losses = F.cross_entropy(logits, y, reduction="none")
        emb = self.store["emb"]
        fin = self.store["fin"][:, g.READ_POS]
        rows, act, tied = [], [], []
        W = self.m.embed.weight
        for q in range(len(x)):
            gr = torch.autograd.grad(losses[q], self.params + [emb, logits], retain_graph=True, allow_unused=True)
            gr = [torch.zeros_like(p) if t is None else t for t, p in zip(gr, self.params + [emb, logits])]
            rows.append(torch.cat([t.reshape(-1) for t in gr[: len(self.params)]]))
            ge = gr[-2][q]
            act.append({"query_pos": ge[g.Q_POS].norm().item(), "digits": [ge[p].norm().item() for p in g.DIGIT_POS]})
            inp_side = torch.zeros_like(W).index_add_(0, x[q], ge)
            out_side = torch.outer(gr[-1][q], fin[q])
            tied.append({"input_side": inp_side.norm().item(), "output_side": out_side.norm().item(),
                         "check": (inp_side + out_side - gr[0]).abs().max().item()})
        return torch.stack(rows), act, tied

    def mean_grad(self, x, y):
        self.m.zero_grad(set_to_none=True)
        F.cross_entropy(self.readout(x), y).backward()
        return flat_grad(self.m)

    def grad_of(self, fn):
        self.m.zero_grad(set_to_none=True)
        fn().backward()
        return flat_grad(self.m)


def _prompts(rows, which, g):
    ps, ys = [], []
    for r, slots in zip(rows, which):
        for k in slots:
            ps.append(r["body"] + "|" + r["queries"][k] + "?")
            ys.append(ord(r["answers"][k]))
    return encode(ps, g), torch.tensor(ys)


def J_value(mg, rows):
    K = mg.g.K
    x, y = _prompts(rows, [range(K)] * len(rows), mg.g)
    N = len(rows)
    logP = torch.log_softmax(mg.readout(x), -1).view(N, K, -1)
    yq = y.view(N, K)
    M = torch.stack([logP.gather(2, yq[:, q].view(N, 1, 1).expand(N, K, 1)).squeeze(2) for q in range(K)], 1)
    off = ~torch.eye(K, dtype=torch.bool)
    return (M.diagonal(dim1=1, dim2=2) - (M * off).sum(2) / (K - 1)).mean()


def chunked_grad(mg, rows, fn, chunk=125):
    total = None
    for i in range(0, len(rows), chunk):
        part = rows[i : i + chunk]
        gr = mg.grad_of(lambda: fn(part) * (len(part) / len(rows)))
        total = gr if total is None else total + gr
    return total


def root_terms(mg, rows):
    K = mg.g.K
    x, y = _prompts(rows, [range(K)] * len(rows), mg.g)
    logP = torch.log_softmax(mg.readout(x), -1)
    roots = torch.tensor([[ord(a) for a in r["answers"]] for r in rows]).repeat_interleave(K, 0)
    lpr = torch.logsumexp(logP.gather(1, roots), -1)
    lpy = logP.gather(1, y.view(-1, 1)).squeeze(1)
    return {"K": lpr.mean(), "L_roots": (-lpr).mean(), "L_within": (-(lpy - lpr)).mean()}


def run_m5(model, ev_rows, fit_rows, pool_b, pool_c, g, n_bodies_a=500, R=200, n_boot=2000):
    K = g.K
    schemes = ("O", "P", "F") if K == 4 else ("O", "F")
    mg = ModelGrads(model, g)
    idx = mg.idx
    res = {"seconds": {}, "schemes": list(schemes)}
    t0 = time.time()
    gJ = chunked_grad(mg, fit_rows, lambda part: J_value(mg, part)).double()
    with torch.no_grad():
        J0 = float(J_value(mg, fit_rows))
    gK = chunked_grad(mg, pool_c, lambda part: root_terms(mg, part)["K"]).double()
    gLr = chunked_grad(mg, pool_c, lambda part: root_terms(mg, part)["L_roots"]).double()
    gLw = chunked_grad(mg, pool_c, lambda part: root_terms(mg, part)["L_within"]).double()
    theta = flat_params(model).double()
    d = torch.zeros(mg.P, dtype=torch.double)
    per_body = {k: {"dJ": [], "dK": []} for k in idx}
    for r in pool_c:
        x, y = _prompts([r], [range(K)], g)
        db = -mg.mean_grad(x, y).double()
        d += db / len(pool_c)
        for k, ix in idx.items():
            per_body[k]["dJ"].append(float(db[ix] @ gJ[ix]))
            per_body[k]["dK"].append(float(db[ix] @ gK[ix]))

    def cos(a, b):
        return float(a @ b / (a.norm() * b.norm())) if a.norm() > 0 and b.norm() > 0 else None

    rng = np.random.default_rng(4)
    nb = len(pool_c)
    boots = [rng.integers(0, nb, nb) for _ in range(n_boot)]

    def ci(a):
        return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]

    dirs = {}
    for k, ix in idx.items():
        dJ, dK = np.asarray(per_body[k]["dJ"]), np.asarray(per_body[k]["dK"])
        dirs[k] = {
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
    acc = FamilyAccumulator(idx, n_bodies_a, mg.P, K)
    acts, tied = [], []
    for r in ev_rows[:n_bodies_a]:
        x, y = _prompts([r], [range(K)], g)
        gK_, a, t = mg.per_question(x, y)
        acc.add(gK_)
        acts += a
        tied += t
    res["a_per_question"] = acc.finish(n_boot=n_boot)
    del acc
    qp = np.asarray([a["query_pos"] for a in acts])
    dig = np.asarray([a["digits"] for a in acts])
    slot = np.tile(np.arange(K), len(acts) // K)
    own = dig[np.arange(len(acts)), slot]
    others = (dig.sum(1) - own) / (K - 1)
    res["a_activation_grad"] = {"query_pos_mean": float(qp.mean()), "queried_digit_mean": float(own.mean()),
                                "other_digits_mean": float(others.mean()),
                                "ratio_query_pos_to_digits": float(qp.mean() / dig.mean())}
    res["a_tied_split"] = {"input_side_mean_norm": float(np.mean([t["input_side"] for t in tied])),
                           "output_side_mean_norm": float(np.mean([t["output_side"] for t in tied])),
                           "max_check_diff": float(max(t["check"] for t in tied))}
    if res["a_tied_split"]["max_check_diff"] > 1e-6:
        raise RuntimeError(f"tied-weight split check failed: {res['a_tied_split']['max_check_diff']}")
    res["seconds"]["a"] = time.time() - t0
    t0 = time.time()
    by_scheme = {}
    for row in pool_b:
        by_scheme.setdefault(row["scheme"], {}).setdefault(row["batch"], []).append(row)
    res["b_batches"], measured_boot = {}, {}
    for scheme in schemes:
        batches = [by_scheme[scheme][b] for b in range(R)]
        st = batch_stats(lambda rows: mg.mean_grad(*_prompts(rows, [r["slots"] for r in rows], g)),
                         batches, idx, u, n_boot=n_boot, seed=SCHEME_SEED[scheme])
        measured_boot[scheme] = st.pop("trvar_boot")
        res["b_batches"][scheme] = st
    cmp = {}
    for k in idx:
        row = {}
        for scheme in schemes:
            mb = measured_boot[scheme][k]
            m_ci = [float(np.percentile(mb, 2.5)), float(np.percentile(mb, 97.5))]
            p_ci = res["a_per_question"][k]["pred_trvar_ci95"][scheme]
            row[scheme] = {"measured": res["b_batches"][scheme]["trvar"][k], "measured_ci95": m_ci,
                           "predicted": res["a_per_question"][k]["pred_trvar"][scheme], "predicted_ci95": p_ci,
                           "cis_overlap": not (m_ci[1] < p_ci[0] or p_ci[1] < m_ci[0])}
        for scheme in schemes[1:]:
            diff = measured_boot[scheme][k] - measured_boot["O"][k]
            row[f"{scheme}_minus_O_ci95"] = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]
        cmp[k] = row
    res["b_vs_a"] = cmp
    res["seconds"]["b"] = time.time() - t0
    mg.remove()
    model.zero_grad(set_to_none=True)
    return res
