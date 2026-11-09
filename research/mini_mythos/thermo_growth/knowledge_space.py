"""A knowledge space that grows by itself where reality surprises the model (README of thermo_growth).

Parcae stays frozen: it is the foundation. Every write into the hidden state (attn.c_proj and mlp.proj
of all six blocks) can add a correction that lives in ONE shared space of k directions:

    out_l  ->  out_l + U_k (R_l,k^T x_l)          U_k: [768, k] orthonormal, shared by all writes

k starts at 0 (a point: the native model). A direction, once grown, stays (the foundation of what was
learned); how each layer uses the directions (R) keeps being refreshed by what is read.

Surprise. While a page of text is read, every write l collects M_l = sum_t g_t x_t^T, where g_t is the
gradient of the prediction error at that write: the direction in which reality pulls the hidden state.
The page is split in two halves (alternate chunks), a and b:
    structure  C = 1/2 sum_l (M_l^a M_l^bT + M_l^b M_l^aT)       noise cancels between halves
    noise      N = 1/2 sum_l (M_l^a - M_l^b)(M_l^a - M_l^b)^T     structure cancels
both restricted to the directions not yet in the space. A new direction grows by itself when the
strongest reproducible pull exceeds the strongest noise by the temperature: lambda_max(C) > T *
lambda_max(N). It grows along that pull (the top eigenvector of C). Its reads R start at 0, so the
model's output does not change at the moment it grows; the next pages fill it in.
"""
import math

import torch

PARTS = ("prelude", "core_block", "coda")


def writers(model):
    out = []
    for part in PARTS:
        for i, block in enumerate(model.transformer[part]):
            out.append(("%s.%d.attn.c_proj" % (part, i), block.attn.c_proj))
            out.append(("%s.%d.mlp.proj" % (part, i), block.mlp.proj))
    return out


class KnowledgeSpace:
    def __init__(self, model, k_max=256):
        mods = writers(model)
        self.dim = mods[0][1].out_features
        device = next(model.parameters()).device
        self.k_max, self.k = k_max, 0
        self.U = torch.zeros(self.dim, k_max, device=device)            # grown directions (columns)
        self.R = {n: torch.nn.Parameter(torch.zeros(m.in_features, k_max, device=device)) for n, m in mods}
        self.collect = False
        self.half = 0
        self.M = {}                                                      # (half, name) -> [dim, in]
        self.capture = None                                              # (name) -> store per-token g
        self.captured = {}
        self.handles = [m.register_forward_hook(self._hook(n)) for n, m in mods]

    def _hook(self, name):
        def hook(module, inputs, output):
            x = inputs[0]
            k = self.k
            R = self.R[name]
            # k may be 0: the zero-width product keeps the output in the graph (exactly + 0)
            delta = (x @ R[:, :k].to(x.dtype)) @ self.U[:, :k].t().to(x.dtype)
            out = output + delta
            if out.requires_grad and (self.collect or self.capture == name):
                xs = x.detach()

                def grad_hook(g, xs=xs):
                    gf = g.reshape(-1, g.shape[-1]).float()
                    if self.collect:
                        key = (self.half, name)
                        m = gf.t() @ xs.reshape(-1, xs.shape[-1]).float()
                        self.M[key] = self.M[key] + m if key in self.M else m
                    if self.capture == name:
                        self.captured.setdefault(name, []).append(g.detach().float().clone())
                out.register_hook(grad_hook)
            return out
        return hook

    def parameters(self):
        return list(self.R.values())

    def count(self, k=None):
        k = self.k if k is None else k
        return k * (self.dim + sum(p.shape[0] for p in self.R.values()))

    def directions(self):
        return self.U[:, :self.k]

    # ---------------------------------------------------------------- growth

    def reset_page(self):
        self.M = {}

    def surprise(self):
        """(lambda_C, lambda_N, top direction u) on the directions not yet grown."""
        names = sorted({n for _, n in self.M})
        if not names or any((h, n) not in self.M for h in (0, 1) for n in names):
            return None
        C = torch.zeros(self.dim, self.dim, dtype=torch.float64)
        N = torch.zeros(self.dim, self.dim, dtype=torch.float64)
        for n in names:
            a, b = self.M[(0, n)].double().cpu(), self.M[(1, n)].double().cpu()
            ab = a @ b.t()
            C += 0.5 * (ab + ab.t())
            d = a - b
            N += 0.5 * (d @ d.t())
        P = torch.eye(self.dim, dtype=torch.float64)
        if self.k:
            Uk = self.U[:, :self.k].double().cpu()
            P = P - Uk @ Uk.t()
        C, N = P @ C @ P, P @ N @ P
        ec, vc = torch.linalg.eigh(0.5 * (C + C.t()))
        en = torch.linalg.eigvalsh(0.5 * (N + N.t()))
        return float(ec[-1]), float(en[-1]), vc[:, -1]

    def grow(self, u):
        """Add direction u (made orthonormal to the existing ones). Output unchanged: its reads are 0."""
        if self.k >= self.k_max:
            raise RuntimeError("knowledge space is full")
        u = u.double().cpu()
        if self.k:
            Uk = self.U[:, :self.k].double().cpu()
            u = u - Uk @ (Uk.t() @ u)
            u = u - Uk @ (Uk.t() @ u)
        u = u / u.norm()
        with torch.no_grad():
            self.U[:, self.k] = u.to(self.U.device, self.U.dtype)
            for p in self.R.values():
                p[:, self.k] = 0.0
        self.k += 1
        return u

    def random_direction(self, gen):
        return torch.randn(self.dim, generator=gen, dtype=torch.float64)

    def state(self):
        return {"k": self.k, "U": self.U[:, :self.k].detach().cpu().clone(),
                "R": {n: p[:, :self.k].detach().cpu().clone() for n, p in self.R.items()}}

    def load_state(self, st):
        with torch.no_grad():
            self.k = int(st["k"])
            self.U.zero_()
            self.U[:, :self.k] = st["U"].to(self.U.device)
            for n, p in self.R.items():
                p.zero_()
                p[:, :self.k] = st["R"][n].to(p.device)

    def remove(self):
        for h in self.handles:
            h.remove()


def orthonormality_error(U):
    if U.shape[1] == 0:
        return 0.0
    G = U.double().t() @ U.double()
    return float((G - torch.eye(G.shape[0], dtype=G.dtype)).abs().max())


def rms(t):
    return math.sqrt(float(t.double().pow(2).mean())) if t.numel() else 0.0
