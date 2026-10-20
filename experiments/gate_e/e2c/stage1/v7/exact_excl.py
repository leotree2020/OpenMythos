"""Exact unconditional test of H0: Delta >= d0 against H1: Delta < d0 for paired
binary outcomes (Delta = p_b - p_c, b = #(C1 learned, C0 not), c = #(C0 learned,
C1 not)), ordered by Tango's (1998) score statistic, p-value = sup over the
nuisance p_c on the boundary Delta = d0. Exact size over the whole null region
and exact power are computed by enumeration (no simulation). Design analysis."""
import math, sys
D0, ALPHA = 0.30, 0.025
def tango_z(b, c, n, d):
    A = 2 * n; B = -b - c + (2 * n - b + c) * d; C = -c * d * (1 - d)
    pc = (math.sqrt(B * B - 4 * A * C) - B) / (2 * A)
    var = n * (2 * pc + d * (1 - d))
    return (b - c - n * d) / math.sqrt(var), pc
def check_mle(n):
    """the closed-form restricted MLE maximizes the likelihood (numerical check)"""
    worst = 0.0
    for b in range(n + 1):
        for c in range(n + 1 - b):
            _, pc = tango_z(b, c, n, D0)
            def ll(q):
                pb = q + D0; r = 1 - pb - q
                if -1e-12 < r < 0: r = 0.0
                if q < 0 or r < 0: return -1e300
                s = 0.0
                for k, p in ((b, pb), (c, q), (n - b - c, r)):
                    if k: s += k * math.log(p) if p > 0 else -1e300
                return s
            grid = max(ll(i / 20000 * (1 - D0) / 2) for i in range(20001))
            assert -1e-12 <= pc <= (1 - D0) / 2 + 1e-12, (b, c, pc)
            worst = max(worst, grid - ll(pc))
    return worst
def pairs(n): return [(b, c) for b in range(n + 1) for c in range(n + 1 - b)]
def pmf(b, c, n, pb, pc):
    r = 1 - pb - pc
    if r < -1e-12: return 0.0
    r = max(r, 0.0)
    lg = math.lgamma(n + 1) - math.lgamma(b + 1) - math.lgamma(c + 1) - math.lgamma(n - b - c + 1)
    t = 0.0
    for k, p in ((b, pb), (c, pc), (n - b - c, r)):
        if k:
            if p <= 0: return 0.0
            t += k * math.log(p)
    return math.exp(lg + t)
def region(n, grid=4001):
    P = pairs(n)
    z = {bc: tango_z(bc[0], bc[1], n, D0)[0] for bc in P}
    order = sorted(P, key=lambda bc: z[bc])
    pval = {bc: 0.0 for bc in P}
    for i in range(grid):
        pc = i / (grid - 1) * (1 - D0) / 2
        pb = pc + D0
        cum, k = 0.0, 0
        probs = [pmf(b, c, n, pb, pc) for b, c in order]
        # cumulative over ties: P(Z <= z_obs)
        j = 0
        while j < len(order):
            zz = z[order[j]]; jj = j
            while jj < len(order) and abs(z[order[jj]] - zz) < 1e-12: jj += 1
            cum += sum(probs[j:jj])
            for t in range(j, jj): pval[order[t]] = max(pval[order[t]], cum)
            j = jj
    return {bc for bc in P if pval[bc] <= ALPHA}, pval
def rej_prob(R, n, pb, pc): return sum(pmf(b, c, n, pb, pc) for b, c in R)
def latent(p0, p1, rho):
    pb = rho * max(p1 - p0, 0) + (1 - rho) * p1 * (1 - p0)
    pc = rho * max(p0 - p1, 0) + (1 - rho) * p0 * (1 - p1)
    return pb, pc
for n in (20, 24, 30):
    R, pval = region(n)
    # exact size over the whole null region Delta >= D0 (2-D grid, step 0.0025)
    size, arg = 0.0, None
    steps = 400
    for i in range(steps + 1):
        pc = i / steps * (1 - D0) / 2
        for j in range(steps + 1):
            pb = pc + D0 + j / steps * (1 - D0 - 2 * pc)
            if pb + pc > 1 + 1e-12: continue
            s = rej_prob(R, n, pb, pc)
            if s > size: size, arg = s, (round(pb, 4), round(pc, 4))
    # fine scan of the boundary Delta = D0, where the maximum lies (20001 points)
    bsize = max(rej_prob(R, n, i / 20000 * (1 - D0) / 2 + D0, i / 20000 * (1 - D0) / 2) for i in range(20001))
    pw = {}
    for p0 in (0.2, 0.4, 0.6):
        for rho in (1.0, 0.5, 0.0):
            pw[(p0, rho)] = rej_prob(R, n, *latent(p0, p0, rho))
    print(f"N={n}: |R|={len(R)}  max exact size over H0 (Delta>=0.30, 401x401 grid) = {size:.4f} at (p_b,p_c)={arg}; boundary fine scan max = {bsize:.4f}  [nominal {ALPHA}]")
    print("   exact power at Delta=0 (latent model): " + "  ".join(f"p0={p0} rho={rho}: {v:.3f}" for (p0, rho), v in pw.items()))
    for tag, (p0, p1) in (("Delta=+0.10", (0.4, 0.5)), ("Delta=-0.10", (0.4, 0.3))):
        print(f"   exact power at {tag} (p0=0.4): " + "  ".join(f"rho={rho}: {rej_prob(R, n, *latent(p0, p1, rho)):.3f}" for rho in (1.0, 0.5, 0.0)))
print("restricted-MLE check, n=12 and n=24 (max loglik gain of a 20001-point grid over the closed form; <=0 means the closed form is the maximum):", round(check_mle(12), 10), round(check_mle(24), 10))
