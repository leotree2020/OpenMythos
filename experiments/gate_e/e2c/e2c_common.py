"""
Shared pieces of E2-c (E2C_PREREG_DRAFT 2, 3.1-3.5, 5.3): conditions, the
fixed auxiliary heads, the auxiliary labels, the record-point capture by
forward hooks on the native modules, the direct error signal r_u, the batch
hash chain and the ACT statistics. E1 modules are imported read-only; the
model code (open_mythos/, basic_learn/models.py) is not modified.

Record points (3.3, D3 main plan; always valid under ACT):
    openmythos   e        output of the last prelude block
                 h1       output of the LTI injection of loop 0 (the first
                          loop always runs)
                 h_out    output of the recurrent block (ACT-weighted sum)
                 coda_out output of the last coda block (before the final norm)
    transformer  out0, out1, out2   outputs of the three blocks
These are the same tensors as gate_d/runner.py's record points of the same
names (checked in V1 against the Runner).

Auxiliary heads (3.3): one linear map d_model -> 52 per record point, no
bias, drawn from torch.Generator().manual_seed(90000 + seed) in record-point
order with the default nn.Linear weight distribution U(-1/sqrt(d), 1/sqrt(d))
(the preregistration fixes "random, fixed, not trained"; this distribution is
fixed here before any calibration run and not tuned). Plain tensors with
requires_grad False, outside the model and the optimizer.

Labels at the digit positions 2 and 6: C1 the letter of the statement
(LETTERS index, 52 classes); C2 c(digit), c an injection of the 10 digits into
the 52 classes, c = random.Random(80000 + seed).sample(range(52), 10).
"""

import hashlib
import json
import math
import os
import random
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(GE, "..", ".."))
if GE not in sys.path:
    sys.path.insert(0, GE)

import e_common  # noqa: E402,F401  (puts the archived modules on sys.path)
from e_common import LETTERS, atomic_write_json, param_hash  # noqa: E402,F401

CONDS = ("C0", "C1", "C2")
DIGIT_POS = (2, 6)
VAR_POS = (0, 4)
N_CLASSES = 52
RECORD_POINTS = {"openmythos": ("e", "h1", "h_out", "coda_out"), "transformer": ("out0", "out1", "out2")}
HEAD_SEED_BASE, CODE_SEED_BASE = 90_000, 80_000
LAMBDA_CANDIDATES = (0.03, 0.1, 0.3, 1.0)
CAL_SEEDS = (91, 92, 93)
IMPL_SEED = 99
W_UPDATES = 300  # early window W = updates 1..300 (3.5)
CAL_STEPS = (0, 25, 50, 75, 100, 150, 200, 300, 500, 1000, 2000, 3000)
D2C_STEPS = (0, 25, 50, 75, 100, 150, 200, 300, 500, 1000, 2000, 3000, 6000, 12000)
D2C_HEAVY = (0, 75, 150, 3000, 12000)
D2C_M0 = (0, 12000)
CLIP = 1.0


# ---------------------------------------------------------------- heads, labels, code


def make_heads(arm, seed, dim):
    g = torch.Generator().manual_seed(HEAD_SEED_BASE + seed)
    bound = 1.0 / math.sqrt(dim)
    return [(torch.rand(N_CLASSES, dim, generator=g) * 2 - 1) * bound for _ in RECORD_POINTS[arm]]


def heads_sha(heads):
    return [hashlib.sha256(W.contiguous().numpy().tobytes()).hexdigest() for W in heads]


def digit_code(seed):
    return random.Random(CODE_SEED_BASE + seed).sample(range(N_CLASSES), 10)


def code_sha(code):
    return hashlib.sha256(json.dumps(code).encode()).hexdigest()


def aux_labels(rows, cond, code=None):
    """(B, 2) class labels at the digit positions 2, 6 of 'a=3;b=7;|b?'."""
    out = []
    for p, _ in rows:
        if cond == "C1":
            out.append([LETTERS.index(p[v]) for v in VAR_POS])
        elif cond == "C2":
            out.append([code[int(p[d])] for d in DIGIT_POS])
        else:
            raise ValueError(cond)
    return torch.tensor(out, dtype=torch.long)


# ---------------------------------------------------------------- record points


class Recorder:
    """Forward hooks on the native modules; the hooks return None, so the
    forward pass is the model's own. `states` holds, after each forward,
    the record-point tensors (with their autograd graph) in RECORD_POINTS
    order; `act_p` the ACT halting probabilities of every executed loop
    (OpenMythos)."""

    def __init__(self, model, arm, want_states=True, want_act=True):
        self.arm, self.handles = arm, []
        self.states, self.act_p, self._h1 = {}, [], None
        if want_states:
            if arm == "openmythos":
                self._hook(model.prelude[-1], "e")
                self._hook(model.recurrent.injection, "h1", first_only=True)
                self._hook(model.recurrent, "h_out")
                self._hook(model.coda[-1], "coda_out")
            else:
                for i, layer in enumerate(model.layers):
                    self._hook(layer, f"out{i}")
        if want_act and arm == "openmythos":
            self.handles.append(model.recurrent.act.register_forward_hook(
                lambda mod, inp, out: self.act_p.append(out.detach())))
        self.thr = model.cfg.act_threshold if arm == "openmythos" else None

    def _hook(self, mod, name, first_only=False):
        def fn(m, inp, out):
            if first_only and name in self.states:
                return None
            self.states[name] = out
            return None
        self.handles.append(mod.register_forward_hook(fn))

    def reset(self):
        self.states, self.act_p = {}, []

    def ordered(self):
        return [self.states[n] for n in RECORD_POINTS[self.arm]]

    @torch.no_grad()
    def act_stats(self, read_pos):
        """Loops executed; after each loop the share of halted positions (all
        positions, and the readout position), recomputed with the native
        arithmetic of RecurrentBlock.forward from the recorded p."""
        if self.arm != "openmythos":
            return None
        p0 = self.act_p[0]
        halted = torch.zeros_like(p0, dtype=torch.bool)
        cum = torch.zeros_like(p0)
        out = {"loops": len(self.act_p), "halted_share": [], "readout_halted_share": []}
        for p in self.act_p:
            still = ~halted
            cum = cum + p * still.float()
            halted = halted | (cum >= self.thr)
            out["halted_share"].append(float(halted.double().mean()))
            out["readout_halted_share"].append(float(halted[:, read_pos].double().mean()))
        return out

    def remove(self):
        for h in self.handles:
            h.remove()


# ---------------------------------------------------------------- auxiliary loss


def aux_terms(states, heads, labels, detach=False):
    """L_aux = (1/R) sum_r 1/(64*2) sum_{b, p in {2,6}} CE(W_r h_{b,p}^{(r)}, y_{b,p}) (3.3).
    detach=True: the R1' negative control (states detached; no gradient
    reaches the model). Returns (L_aux, logits per record point)."""
    Ls, zs = [], []
    for h, W in zip(states, heads):
        hs = h[:, list(DIGIT_POS), :]
        if detach:
            hs = hs.detach()
        z = hs @ W.T
        Ls.append(F.cross_entropy(z.reshape(-1, N_CLASSES), labels.reshape(-1)))
        zs.append(z)
    return sum(Ls) / len(Ls), zs


@torch.no_grad()
def direct_signal_norm(zs, heads, labels, lam):
    """r_u (3.5): Frobenius norm of the direct error signal of lam * L_aux on
    all supervised states, before clipping: for record point r,
    d(lam L_aux)/d h_{b,p}^{(r)} = lam / (R * B * 2) * (softmax(z) - onehot(y)) W_r,
    each record point taken as an input of its own head only (the direct path).
    Computed in float64."""
    R = len(zs)
    tot = 0.0
    for z, W in zip(zs, heads):
        zd = z.detach().double()
        n = zd.shape[0] * zd.shape[1]
        G = torch.softmax(zd, -1)
        G = G - F.one_hot(labels, N_CLASSES).double()
        g = (lam / (R * n)) * (G @ W.double())
        tot += float((g * g).sum())
    return math.sqrt(tot)


def param_grad_norm(L_aux, params):
    """||d L_aux / d theta|| by autograd.grad (not accumulated into .grad; R1'')."""
    gs = torch.autograd.grad(L_aux, params, retain_graph=True, allow_unused=True)
    return math.sqrt(sum(float(g.double().pow(2).sum()) for g in gs if g is not None))


def kappa(gnorm):
    """Clipping coefficient of clip_grad_norm_(max_norm=1.0), in its own arithmetic."""
    return float(torch.clamp(CLIP / (gnorm + 1e-6), max=1.0))


class HashChain:
    """sha256 chain over the token tensors of the training batches (3.5)."""

    def __init__(self):
        self.d = b""

    def update(self, x):
        self.d = hashlib.sha256(self.d + x.contiguous().numpy().tobytes()).digest()
        return self.d.hex()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def state_dict_equal(a, b):
    """Bitwise equality of two state dicts (same keys, same dtypes, same bytes)."""
    if list(a.keys()) != list(b.keys()):
        return False
    return all(a[k].dtype == b[k].dtype and a[k].shape == b[k].shape and torch.equal(a[k], b[k])
               and a[k].contiguous().numpy().tobytes() == b[k].contiguous().numpy().tobytes() for k in a)
