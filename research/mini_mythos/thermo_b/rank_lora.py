"""Thermo-B: rank-expanding LoRA and its schedule (see README.md).

RankLoRA is the Stage 2/3 LoRA (forward hooks, B initialised to 0, scale alpha / r_max) with a 0/1
mask over its r_max components:  y = W x + scale * B diag(m) A x.

- Locked components (m = 0) get exactly zero gradient, so AdamW (weight decay 0) leaves them
  bitwise unchanged; their B columns therefore stay 0 until they are unlocked.
- Unlocking sets m = 1 for the next components. Their B columns are still 0, so the model output
  does not change at the moment of unlocking (function-preserving expansion).
- With the mask all ones the hook computes exactly what the Stage 3a C-LoRA hook computes
  (multiplying by 1.0 is exact), so the full-rank control is the Stage 3a control.

Schedule: "full" keeps rank r_max from the first step (control C). "expand" splits the run into
len(ranks) stages of equal length (integer steps) and unlocks ranks 1 -> 2 -> 4 -> 8 -> 16 -> 28.
Optional temperature (arm T): during the first `anneal` fraction of each stage, Gaussian noise is
added to the gradients of the components unlocked in that stage, with standard deviation
T(step) * rms(their gradient) per tensor; T falls linearly from t0 to 0. The noise generator is
re-seeded from (seed, step), so a resumed run draws the same noise.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402

RANKS = (1, 2, 4, 8, 16, 28)


def stage_starts(total_steps, n_stages):
    """First optimizer step of each of n_stages equal stages."""
    return [k * total_steps // n_stages for k in range(n_stages)]


def curve_steps(total_steps, n_points=len(RANKS)):
    """Steps (= optimizer steps done) at which the learning curve is measured: 0, then the end of
    each of the n_points equal stages. The same points are used for every arm."""
    return [0] + [s for s in stage_starts(total_steps, n_points)[1:]] + [total_steps]


class Schedule:
    def __init__(self, kind, total_steps, ranks=RANKS, max_rank=28, t0=0.0, anneal=0.5):
        if kind not in ("full", "expand"):
            raise ValueError("schedule must be full or expand")
        if t0 < 0 or not 0 < anneal <= 1:
            raise ValueError("bad temperature settings")
        if kind == "full":
            if t0 > 0:
                raise ValueError("the temperature belongs to the expand schedule only")
            ranks = (max_rank,)
        else:
            ranks = tuple(int(r) for r in ranks)
            if list(ranks) != sorted(set(ranks)) or ranks[0] < 1 or ranks[-1] != max_rank:
                raise ValueError("ranks must increase strictly from >= 1 and end at the maximum rank")
            if total_steps < len(ranks):
                raise ValueError("fewer optimizer steps than stages")
        self.kind, self.total, self.max_rank = kind, int(total_steps), int(max_rank)
        self.ranks, self.t0, self.anneal = ranks, float(t0), float(anneal)
        self.starts = stage_starts(self.total, len(ranks))

    def stage(self, step):
        k = 0
        for i, s in enumerate(self.starts):
            if step >= s:
                k = i
        return k

    def rank(self, step):
        return self.ranks[self.stage(step)]

    def new_components(self, step):
        """(lo, hi): the components unlocked at the start of the stage containing `step`."""
        k = self.stage(step)
        return (self.ranks[k - 1] if k else 0), self.ranks[k]

    def stage_len(self, k):
        end = self.starts[k + 1] if k + 1 < len(self.starts) else self.total
        return end - self.starts[k]

    def temperature(self, step):
        if self.t0 <= 0:
            return 0.0
        k = self.stage(step)
        window = self.anneal * self.stage_len(k)
        tau = step - self.starts[k]
        return self.t0 * max(0.0, 1.0 - tau / window) if window > 0 else 0.0

    def describe(self):
        return {"kind": self.kind, "ranks": list(self.ranks), "stage_starts": self.starts,
                "t0": self.t0, "anneal": self.anneal}


class RankLoRA(G.LoRA):
    def __init__(self, torch, model, rank=28, alpha=56, seed=0):
        device = next(model.parameters()).device
        self.max_rank = rank
        self.mask = torch.ones(rank, device=device)       # hooks read it in place
        super().__init__(torch, model, rank=rank, alpha=alpha, seed=seed)
        self.active = rank

    def _hook(self, A, B):
        scale, mask = self.scale, self.mask

        def hook(module, inputs, output):
            x = inputs[0]
            return output + ((x @ A.t().to(x.dtype)) * mask.to(x.dtype)) @ B.t().to(x.dtype) * scale
        return hook

    def set_rank(self, r):
        import torch
        if not 0 <= r <= self.max_rank:
            raise ValueError("rank out of range")
        with torch.no_grad():
            self.mask.zero_()
            self.mask[:r] = 1.0
        self.active = r

    def component_views(self, lo, hi, grads=True):
        """(name, view) of components lo..hi-1: rows of A, columns of B (gradients or values)."""
        for name in sorted(self.params):
            p = self.params[name]
            t = p.grad if grads else p.data
            if t is None:
                continue
            yield name, (t[lo:hi] if name.endswith(".A") else t[:, lo:hi])

    def add_gradient_noise(self, torch, lo, hi, temperature, seed, step):
        """Add N(0, (temperature * rms)^2) to the gradients of components lo..hi-1, per tensor.
        Returns the number of gradient entries that received noise."""
        if temperature <= 0 or hi <= lo:
            return 0
        gen = torch.Generator().manual_seed(1_000_003 * (int(seed) + 1) + int(step))
        n = 0
        for _, g in self.component_views(lo, hi):
            rms = float(g.double().pow(2).mean().sqrt())
            if rms == 0.0:
                continue                                  # e.g. A rows while their B columns are still 0
            noise = torch.randn(tuple(g.shape), generator=gen, dtype=torch.float32)
            g.add_(noise.to(device=g.device, dtype=g.dtype) * (temperature * rms))
            n += g.numel()
        return n

    def spectra(self, torch):
        """Singular values of every active update dW = scale * B diag(m) A (via two thin QRs)."""
        out = {}
        r = self.active
        names = sorted({k[:-2] for k in self.params})
        for name in names:
            A, B = self.params[name + ".A"].detach(), self.params[name + ".B"].detach()
            if r == 0:
                out[name] = []
                continue
            qa, ra = torch.linalg.qr(A[:r].double().t())          # A_r^T = Qa Ra
            qb, rb = torch.linalg.qr(B[:, :r].double())           # B_r = Qb Rb
            out[name] = (torch.linalg.svdvals(rb @ ra.t()) * self.scale).cpu().tolist()
        return out
