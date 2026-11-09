"""Thermo-B geometry measures (report only; none of them enters a pass/fail rule).

- participation_ratio(X): linear effective dimension of a point cloud, (sum l)^2 / sum l^2 over
  the eigenvalues l of its covariance. 1 for points on a line, D for an isotropic cloud in D dims.
- twonn(X): nonlinear intrinsic dimension (TwoNN, Facco et al. 2017): mu = r2 / r1 from the two
  nearest neighbours of every point; -log(1 - F(mu)) = d log(mu), fitted through the origin on the
  90% smallest mu. Identical points are merged first; points with r1 = 0 are left out.
- effective_rank(s): exp(entropy of s / sum s) of singular values (Roy & Vetterli 2007).
"""
import math


def participation_ratio(torch, X):
    X = X.double()
    X = X - X.mean(0, keepdim=True)
    s2 = torch.linalg.svdvals(X) ** 2
    tot = float(s2.sum())
    if tot <= 0:
        return None
    return tot ** 2 / float((s2 ** 2).sum())


def _two_nn_distances(torch, X, chunk=2048):
    X = X.double()
    n = X.shape[0]
    r1 = torch.empty(n, dtype=torch.float64, device=X.device)
    r2 = torch.empty(n, dtype=torch.float64, device=X.device)
    sq = (X * X).sum(1)
    for i in range(0, n, chunk):
        d2 = sq[i:i + chunk, None] + sq[None, :] - 2.0 * X[i:i + chunk] @ X.t()
        d2.clamp_(min=0.0)
        idx = torch.arange(i, min(i + chunk, n), device=X.device)
        d2[idx - i, idx] = float("inf")                       # not its own neighbour
        two = torch.topk(d2, 2, dim=1, largest=False).values.sqrt()
        r1[i:i + chunk], r2[i:i + chunk] = two[:, 0], two[:, 1]
    return r1, r2


def twonn(torch, X, fraction=0.9):
    """Returns (dimension, distinct points used) or (None, used) when too few distinct points.
    Identical rows are merged first (a duplicate would put r1 = 0 or r1 = r2)."""
    X = torch.unique(X.double().cpu(), dim=0).to(X.device)
    if X.shape[0] < 3:
        return None, int(X.shape[0])
    r1, r2 = _two_nn_distances(torch, X)
    ok = r1 > 0
    mu = (r2[ok] / r1[ok]).cpu()
    n = int(mu.numel())
    if n < 10:
        return None, n
    mu, _ = torch.sort(mu)
    keep = int(math.floor(fraction * n))
    F = torch.arange(1, n + 1, dtype=torch.float64) / n
    x = torch.log(mu[:keep])
    y = -torch.log(1.0 - F[:keep])
    den = float((x * x).sum())
    if den <= 0:
        return None, n
    return float((x * y).sum()) / den, n


def effective_rank(s):
    s = [float(v) for v in s if float(v) > 0]
    if not s:
        return 0.0
    tot = sum(s)
    return math.exp(-sum((v / tot) * math.log(v / tot) for v in s))


def adapter_summary(spectra):
    """Aggregate RankLoRA.spectra(): mean / median effective rank over the adapted layers, and the
    total squared Frobenius norm of the updates."""
    er = sorted(effective_rank(s) for s in spectra.values())
    if not er:
        return {"layers": 0}
    mid = len(er) // 2
    median = er[mid] if len(er) % 2 else 0.5 * (er[mid - 1] + er[mid])
    return {"layers": len(er), "effective_rank_mean": sum(er) / len(er), "effective_rank_median": median,
            "update_fro2_total": sum(sum(v * v for v in s) for s in spectra.values())}
