# data-auditor, E1-V1 round 2, item 4: protocol 6.4 item 2a (exact rational arithmetic).
# With Acq a multiple of 1/480 (240 learned facts x 2 DEV questions), check on constructed a_j sequences that the
# checkpoint saving rule of 6.7 and the bracketing / tolerance rule of 6.4 (items 1-2) agree: every endpoint of a
# qualifying bracket is saved. Rules written from the protocol text (6.4 items 1-3, 6.7); no model is used.
# Also shows what float arithmetic would do on the same grid. No Executor code is imported, called or copied.
import itertools
import json
import random
import sys
import time
from fractions import Fraction as Fr

T = [Fr("0.70"), Fr("0.80"), Fr("0.90")]
TAU = Fr("0.10")
TAU_TEST = Fr("0.05")
NPTS = 10


def iso(a, t, tau=TAU, alt_first_point=False):
    """6.4 items 1-2 on a[0..n-1] (dose points j = 1..n). Returns (lo, hi) 1-based or None (NOT_REACHED).
    alt_first_point: the other reading of the parenthesis in item 1 (a_1 >= t -> NOT_REACHED)."""
    if alt_first_point and a[0] >= t:
        return None
    for j in range(2, len(a) + 1):
        if a[j - 2] < t <= a[j - 1]:
            if t - a[j - 2] > tau or a[j - 1] - t > tau:
                return None
            return (j - 1, j)
    return None


def saved(a, targets=T, tau=TAU):
    """6.7: after dose point j, save if some t was not crossed before j (no i < j, i >= 2, with
    a_{i-1} < t <= a_i) and |a_j - t| <= tau."""
    out = set()
    for j in range(1, len(a) + 1):
        for t in targets:
            crossed = any(a[i - 2] < t <= a[i - 1] for i in range(2, j))
            if not crossed and abs(a[j - 1] - t) <= tau:
                out.add(j)
                break
    return out


def check(a, targets=T, tau=TAU, alt=False):
    s = saved(a, targets, tau)
    bad, used = [], set()
    for t in targets:
        b = iso(a, t, tau, alt)
        if b:
            used |= set(b)
            if not set(b) <= s:
                bad.append((t, b))
            lo, hi = a[b[0] - 1], a[b[1] - 1]
            w = (t - lo) / (hi - lo)
            assert 0 < w <= 1 and (1 - w) * lo + w * hi == t
    return bad, len(s - used)


def main():
    t0 = time.time()
    print("grid: Acq = (sum over 240 learned facts of correct/2) / 240 -> multiples of 1/480")
    for t in T + [TAU, TAU_TEST]:
        print(f"  {t} * 480 = {t * 480} (integer: {(t * 480).denominator == 1}); * 720 = {t * 720} (TEST grid 1/720: {(t * 720).denominator == 1})")
    rng = random.Random(20261128)
    c = [rng.choice([0, 1, 2]) for _ in range(240)]
    acq = sum((Fr(x, 2) for x in c), Fr(0)) / 240
    print(f"  constructed Acq from per-fact Scores: {acq} = {acq * 480}/480, denominator divides 480: {480 % acq.denominator == 0}")

    eps = Fr(1, 480)
    crit = sorted({Fr(0), Fr("0.50"), Fr(1)} | {t + d for t in T for d in (-TAU - eps, -TAU, -TAU + eps, -eps, Fr(0), eps, TAU - eps, TAU, TAU + eps)} - {Fr(1) + eps})
    crit = [v for v in crit if 0 <= v <= 1]
    print(f"critical values ({len(crit)}):", [str(v) for v in crit])

    # (1) exhaustive over the critical values, sequences of length 5 (formal reading of 6.4 item 1)
    n_seq, n_bad, n_brk, n_extra = 0, 0, 0, 0
    first_bad = None
    for seq in itertools.product(crit, repeat=5):
        n_seq += 1
        bad, extra = check(list(seq))
        n_extra += extra
        n_brk += sum(1 for t in T if iso(list(seq), t))
        if bad:
            n_bad += 1
            first_bad = first_bad or (seq, bad)
    print(f"(1) exhaustive, length 5 over the critical values: sequences {n_seq} | qualifying brackets {n_brk} | sequences with a bracket endpoint not saved {n_bad} | saved but unused checkpoints (sum) {n_extra}")
    if first_bad:
        print("    first counterexample:", [str(x) for x in first_bad[0]], first_bad[1])

    # (2) random sequences of length 10: critical values; uniform grid; monotone grid
    total_bad = n_bad
    for label, gen in (("critical values, any order", lambda: [rng.choice(crit) for _ in range(NPTS)]),
                       ("grid k/480, any order", lambda: [Fr(rng.randint(0, 480), 480) for _ in range(NPTS)]),
                       ("grid k/480, non-decreasing", lambda: sorted(Fr(rng.randint(0, 480), 480) for _ in range(NPTS))),
                       ("grid, curve-like: increments k/480 with k in -24..72", None)):
        nb = nbr = nalt_diff = nalt_bad = 0
        N = 50000
        for _ in range(N):
            if gen is None:
                v, a = rng.randint(150, 330), []
                for _j in range(NPTS):
                    v = min(480, max(0, v + rng.randint(-24, 72)))
                    a.append(Fr(v, 480))
            else:
                a = gen()
            bad, _ = check(a)
            nb += bool(bad)
            total_bad += bool(bad) + bool(check(a, alt=True)[0])
            nbr += sum(1 for t in T if iso(a, t))
            bad_alt, _ = check(a, alt=True)
            nalt_bad += bool(bad_alt)
            nalt_diff += any(iso(a, t) != iso(a, t, alt_first_point=True) for t in T)
        print(f"(2) random length 10, {label}: sequences {N} | brackets {nbr} | sequences with an unsaved bracket endpoint: formal reading {nb}, other reading of the item-1 parenthesis {nalt_bad} | sequences where the two readings give different iso results {nalt_diff}")

    # (3) edge cases on the grid, exact vs float
    print("(3) edge cases (t = 0.70 unless stated), exact Fraction vs float with a_j = float mean of per-fact Scores")
    cases = {
        "a_j* - t = 0.10 exactly (0.65 -> 0.80)": [Fr("0.50"), Fr("0.65"), Fr("0.80")],
        "t - a_j*-1 = 0.10 exactly (0.60 -> 0.75)": [Fr("0.50"), Fr("0.60"), Fr("0.75")],
        "a_j* = t exactly, w = 1 (0.65 -> 0.70)": [Fr("0.50"), Fr("0.65"), Fr("0.70")],
        "a_j*-1 = t exactly is not below t (0.70 -> 0.75)": [Fr("0.50"), Fr("0.70"), Fr("0.75")],
        "both ends exactly 0.10 away (0.60 -> 0.80)": [Fr("0.50"), Fr("0.60"), Fr("0.80")],
        "t = 0.80: 0.70 -> 0.90": [Fr("0.50"), Fr("0.70"), Fr("0.90")],
        "t = 0.90: 0.80 -> 1.00": [Fr("0.50"), Fr("0.80"), Fr(1)],
    }

    def float_acq(fr):
        k = int(fr * 480)  # number of correct DEV questions among 480
        scores = [1.0] * (k // 2) + [0.5] * (k % 2) + [0.0] * (240 - k // 2 - k % 2)
        return sum(scores) / 240

    for name, a in cases.items():
        t = Fr("0.80") if name.startswith("t = 0.80") else Fr("0.90") if name.startswith("t = 0.90") else Fr("0.70")
        e_iso, e_save = iso(a, t), saved(a, [t])
        af = [float_acq(x) for x in a]
        tf = float(t)
        f_iso = iso(af, tf, 0.1)
        f_save = saved(af, [tf], 0.1)
        mixed_bad = bool(e_iso and not set(e_iso) <= f_save)
        print(f"    {name}: a = {[str(x) for x in a]} float a = {af} | exact iso {e_iso} saved {sorted(e_save)} consistent {not e_iso or set(e_iso) <= e_save}"
              f" | float iso {f_iso} saved {sorted(f_save)} | exact 6.4 with float 6.7 leaves an endpoint unsaved: {mixed_bad}")

    # (4) the same thresholds taken from DOSE_SPACE.json as floats
    ds = json.load(open("/home/user/OpenMythos/metrix/e1-v1/DOSE_SPACE.json", encoding="utf-8"))
    raw = open("/home/user/OpenMythos/metrix/e1-v1/DOSE_SPACE.json", encoding="utf-8").read()
    dsx = json.loads(raw, parse_float=Fr)
    a = [Fr("0.50"), Fr("0.65"), Fr("0.80")]
    t_from_float, tau_from_float = Fr(ds["iso"]["targets"][0]), Fr(ds["iso"]["tau_dev"])
    print(f"(4) DOSE_SPACE iso.targets[0] = {ds['iso']['targets'][0]!r}, tau_dev = {ds['iso']['tau_dev']!r}")
    print(f"    Fraction(float) gives t = {t_from_float} (== 7/10: {t_from_float == Fr('0.70')}), tau = {tau_from_float} (== 1/10: {tau_from_float == TAU})")
    print(f"    json.loads(parse_float=Fraction) gives t = {dsx['iso']['targets'][0]}, tau = {dsx['iso']['tau_dev']} (exact: {dsx['iso']['targets'][0] == Fr('0.70') and dsx['iso']['tau_dev'] == TAU})")
    print(f"    sequence {[str(x) for x in a]}: iso with Fraction('0.70'), Fraction('0.10') -> {iso(a, Fr('0.70'))}; with Fraction(0.7), Fraction(0.1) -> {iso(a, t_from_float, tau_from_float)}")

    # (5) DEV interpolation is exactly t; TEST check on the 1/720 grid
    rng2 = random.Random(7)
    lo_c = [2] * 150 + [1] * 17 + [0] * 73   # 317 / 480 correct DEV questions, below 0.70
    rng2.shuffle(lo_c)
    hi_c = list(lo_c)
    up = [i for i, x in enumerate(hi_c) if x < 2]
    for i in rng2.sample(up, 33):            # 33 more correct questions: 350 / 480, at or above 0.70
        hi_c[i] += 1
    a_lo = sum((Fr(x, 2) for x in lo_c), Fr(0)) / 240
    a_hi = sum((Fr(x, 2) for x in hi_c), Fr(0)) / 240
    t = max((x for x in T if a_lo < x <= a_hi), default=None)
    if t is not None:
        w = (t - a_lo) / (a_hi - a_lo)
        interp = sum(((1 - w) * Fr(x, 2) + w * Fr(y, 2) for x, y in zip(lo_c, hi_c)), Fr(0)) / 240
        print(f"(5) constructed facts: a_lo {a_lo} ({float(a_lo):.6f}), a_hi {a_hi} ({float(a_hi):.6f}), t {t}, w {w}; per-fact interpolated Acq = {interp} == t: {interp == t}; float(w) = {float(w)!r}")
    else:
        print(f"(5) constructed facts: a_lo {a_lo} a_hi {a_hi}: no target in (a_lo, a_hi]")
    print(f"elapsed {time.time() - t0:.1f} s")
    print("ITEM4 round 2:", "CONSISTENT" if total_bad == 0 else "INCONSISTENT", f"(sequences with an unsaved bracket endpoint over (1) and (2): {total_bad})")


if __name__ == "__main__":
    main()
