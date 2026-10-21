"""Certified (rational-arithmetic) upper bounds for the exclusion test of
PREREGISTRATION 7.1 (design analysis only).
Model: per seed a 3-cell multinomial (b: C1 only learned, c: C0 only learned,
r: rest) with probabilities (p_b, p_c, p_r); Delta = p_b - p_c; H0: Delta >= 3/10.
Reduction to the boundary: if a set A of (b, c) is decreasing in b ((b, c) in A
and b >= 1 imply (b - 1, c) in A), moving probability mass from r to b can only
lower P(A) (coupling: a trial that turns from r into b raises b only). Every
null point (p_b, p_c) is reached from the boundary point (p_c + 3/10, p_c) by
such moves, so sup over H0 = sup over the boundary. On the boundary, with
t in [0, 1]: p_c = 7/20 t, p_b = 3/10 (1 - t) + 13/20 t, p_r = 7/10 (1 - t);
P(A) is a polynomial of degree N in t, written exactly in the Bernstein basis.
The maximum Bernstein coefficient over a subinterval bounds the polynomial
there from above; branch and bound with de Casteljau halving until
upper - lower <= TOL gives a certified upper bound (lower = exact values at
interval ends). All arithmetic in fractions.Fraction."""
import heapq, math
from fractions import Fraction as Fr
TOL = Fr(1, 10**7)
PC, PR, A0, A1 = Fr(7, 20), Fr(7, 10), Fr(3, 10), Fr(13, 20)
TABLE = {  # frozen rejection regions of PREREGISTRATION 7.1: b -> c_min (and b + c <= N)
    20: {0: 0, 1: 0, 2: 1, 3: 3, 4: 4, 5: 6, 6: 8, 7: 9, 8: 11},
    24: {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 5, 6: 6, 7: 8, 8: 9, 9: 11, 10: 13},
    30: {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 3, 6: 4, 7: 6, 8: 7, 9: 9, 10: 11, 11: 12, 12: 14, 13: 15},
}
def region(n): return {(b, c) for b, cm in TABLE[n].items() for c in range(cm, n - b + 1)}
def decreasing_in_b(A): return all((b - 1, c) in A for (b, c) in A if b >= 1)
def bernstein(A, n):
    coef = [Fr(0)] * (n + 1)
    for b, c in A:
        r = n - b - c
        K = Fr(math.factorial(n), math.factorial(b) * math.factorial(c) * math.factorial(r)) * PC ** c * PR ** r
        for k in range(b + 1):
            coef[c + k] += K * math.comb(b, k) * A0 ** (b - k) * A1 ** k / math.comb(n, c + k)
    return coef
def halve(cf):
    left, right, cur = [cf[0]], [cf[-1]], cf[:]
    while len(cur) > 1:
        cur = [(cur[i] + cur[i + 1]) / 2 for i in range(len(cur) - 1)]
        left.append(cur[0]); right.append(cur[-1])
    return left, right[::-1]
def certified_sup(cf):
    lower = max(cf[0], cf[-1]); heap = [(-max(cf), 0, cf)]; k = 0
    while True:
        ub = -heap[0][0]
        if ub - lower <= TOL: return lower, ub
        _, _, c0 = heapq.heappop(heap)
        for part in halve(c0):
            lower = max(lower, part[0], part[-1]); k += 1
            heapq.heappush(heap, (-max(part), k, part))
def tango_z(b, c, n, d=0.3):
    A = 2 * n; B = -b - c + (2 * n - b + c) * d; C = -c * d * (1 - d)
    pc = (math.sqrt(B * B - 4 * A * C) - B) / (2 * A)
    return (b - c - n * d) / math.sqrt(n * (2 * pc + d * (1 - d)))
def up6(x):  # exact ceiling of a nonnegative Fraction to 6 decimals, integer arithmetic only (no float)
    assert isinstance(x, Fr) and x >= 0
    k = -((-x.numerator * 10**6) // x.denominator)
    return f"{k // 10**6}.{k % 10**6:06d}"
for n in (20, 24, 30):
    R = region(n)
    lo, ub = certified_sup(bernstein(R, n))
    # every lower set of the Tango ordering must be decreasing in b (p-value sets)
    cells = [(b, c) for b in range(n + 1) for c in range(n + 1 - b)]
    z = {bc: tango_z(*bc, n) for bc in cells}
    zl_ok = all(decreasing_in_b({x for x in cells if z[x] <= z[bc] + 1e-12}) for bc in cells)
    # the frozen region is a lower set of the Tango ordering
    zmax_in = max(z[x] for x in R); is_lower = R == {x for x in cells if z[x] <= zmax_in + 1e-12}
    print(f"N={n}: |R|={len(R)} R decreasing in b: {decreasing_in_b(R)}; R is a Tango lower set: {is_lower}; "
          f"all Tango lower sets decreasing in b: {zl_ok}; certified sup over H0 of P(reject) in "
          f"[{float(lo):.7f}, {float(ub):.7f}] -> certified upper bound {up6(ub)} (nominal 0.025)", flush=True)
# certified p-value upper bounds for N = 24 at the edge cells of the table and just outside it
n = 24
cells = [(b, c) for b in range(n + 1) for c in range(n + 1 - b)]
z = {bc: tango_z(*bc, n) for bc in cells}
for bc in ((0, 0), (2, 0), (3, 0), (3, 1), (5, 5), (5, 4), (10, 13), (10, 12), (11, 13)):
    A = {x for x in cells if z[x] <= z[bc] + 1e-12}
    lo, ub = certified_sup(bernstein(A, n))
    print(f"N=24 (b,c)={bc}: in frozen table {bc in region(n)}; certified p-value upper bound {up6(ub)} (sup in [{float(lo):.7f}, {float(ub):.7f}])", flush=True)
