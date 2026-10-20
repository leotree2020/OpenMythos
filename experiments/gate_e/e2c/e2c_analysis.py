#!/usr/bin/env python3
"""
Stage-4 statistical analysis of E2-c (E2C_PREREG_DRAFT 5.2, 3.5, 7.1-7.3).
Implemented and checked in stage 1 on synthetic tables and on the
measurement-set results of R3 only; it reads test2 judgments only in stage 4.

OpenMythos (7.1), the confirmatory family:
    P1 C1 vs C0, P2 C1 vs C2: paired exact McNemar (two-sided), Holm at 0.025
    (smaller p <= 0.0125, then larger p <= 0.025); sign + / 0 / -
    exclusion of Delta10 >= 0.30: (b10, c10) looked up in the frozen table;
    reported p-value = the certified upper bound p-bar of Appendix F's algorithm
    (Tango lower set, rational Bernstein branch and bound, exact ceiling to 6
    decimals), computed here with the same arithmetic
    preconditions in order: manipulation check (5.2); C0 not learned in >= 5 seeds
    decision table 3 x 3 and the modifiers BAL (3.5), SPEC, replication (5.2)
Transformer (7.2): P1, P2 at Holm 0.05 (0.025 / 0.05), no exclusion test; the
secondary t_L sign tests (Holm 0.05) and the median paired difference with a
seed bootstrap (10000, seed 0).
Descriptive: Newcombe 95% intervals, Delta12 exclusion (nominal), C2 vs C0.

    python experiments/gate_e/e2c/e2c_analysis.py --out analysis.json
"""

import argparse
import heapq
import json
import math
import os
import random
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

from e_events import NOT_HAPPENED, first_sustained  # noqa: E402  E1, read-only

C0_P2 = 1 / 52
STEPS = (0, 25, 50, 75, 100, 150, 200, 300, 500, 1000, 2000, 3000, 6000, 12000)
MANIP_STEPS = tuple(t for t in STEPS if 50 <= t <= 3000)
TABLES = {20: {0: 0, 1: 0, 2: 1, 3: 3, 4: 4, 5: 6, 6: 8, 7: 9, 8: 11},
          24: {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 5, 6: 6, 7: 8, 8: 9, 9: 11, 10: 13},
          30: {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 3, 6: 4, 7: 6, 8: 7, 9: 9, 10: 11, 11: 12, 12: 14, 13: 15}}


# ------------------------------------------------------------ exact tests


def binom_two_sided(k, n):
    """Exact two-sided binomial(1/2) p-value: min(1, 2 P(X <= min(k, n - k)))."""
    if n == 0:
        return 1.0
    m = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(m + 1)) / 2 ** n)


def mcnemar(b, c):
    return binom_two_sided(min(b, c), b + c)


def holm(pa, pb, alpha):
    """Two hypotheses: reject the smaller p if <= alpha/2, then the larger if <= alpha."""
    first = 0 if pa <= pb else 1
    p = (pa, pb)
    rej = [False, False]
    if p[first] <= alpha / 2:
        rej[first] = True
        if p[1 - first] <= alpha:
            rej[1 - first] = True
    return rej


def sign(rejected, b, c):
    return "+" if rejected and b > c else ("-" if rejected and b < c else "0")


# ------------------------------------------------------------ Appendix F algorithm (same arithmetic as certify.py)


TOL = Fr(1, 10 ** 7)
PC, PR, A0, A1 = Fr(7, 20), Fr(7, 10), Fr(3, 10), Fr(13, 20)


def in_table(b, c, n):
    t = TABLES[n]
    return b in t and c >= t[b] and b + c <= n


def decreasing_in_b(A):
    return all((b - 1, c) in A for (b, c) in A if b >= 1)


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
        left.append(cur[0])
        right.append(cur[-1])
    return left, right[::-1]


def certified_sup(cf):
    lower = max(cf[0], cf[-1])
    heap = [(-max(cf), 0, cf)]
    k = 0
    while True:
        ub = -heap[0][0]
        if ub - lower <= TOL:
            return lower, ub
        _, _, c0 = heapq.heappop(heap)
        for part in halve(c0):
            lower = max(lower, part[0], part[-1])
            k += 1
            heapq.heappush(heap, (-max(part), k, part))


def tango_z(b, c, n, d=0.3):
    A = 2 * n
    B = -b - c + (2 * n - b + c) * d
    C = -c * d * (1 - d)
    pc = (math.sqrt(B * B - 4 * A * C) - B) / (2 * A)
    return (b - c - n * d) / math.sqrt(n * (2 * pc + d * (1 - d)))


def up6(x):
    assert isinstance(x, Fr) and x >= 0
    k = -((-x.numerator * 10 ** 6) // x.denominator)
    return f"{k // 10 ** 6}.{k % 10 ** 6:06d}"


def p_bar(b, c, n):
    """Certified upper bound of the exact unconditional p-value of (b, c)."""
    cells = [(bb, cc) for bb in range(n + 1) for cc in range(n + 1 - bb)]
    z = {x: tango_z(*x, n) for x in cells}
    A = {x for x in cells if z[x] <= z[(b, c)] + 1e-12}
    if not decreasing_in_b(A):
        raise RuntimeError("lower set not decreasing in b: the certified bound does not apply")
    lo, ub = certified_sup(bernstein(A, n))
    return up6(ub)


def exclusion(b, c, n):
    if n not in TABLES:
        return {"N": n, "reject": None, "note": "no frozen table for this N"}
    return {"N": n, "b": b, "c": c, "reject": in_table(b, c, n), "p_bar": p_bar(b, c, n)}


# ------------------------------------------------------------ descriptive


def wilson(x, n, z=1.959963984540054):
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def newcombe(a, b, c, d):
    n = a + b + c + d
    x1, x2 = a + b, a + c
    p1, p2 = x1 / n, x2 / n
    l1, u1 = wilson(x1, n)
    l2, u2 = wilson(x2, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = 0.0 if den == 0 else (a * d - b * c) / math.sqrt(den)
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return [p1 - p2 - dl, p1 - p2 + du]


def paired(x, y):
    """x, y: dict seed -> bool. a both, b x only, c y only, d none."""
    s = sorted(x)
    a = sum(x[i] and y[i] for i in s)
    b = sum(x[i] and not y[i] for i in s)
    c = sum(y[i] and not x[i] for i in s)
    return a, b, c, len(s) - a - b - c


# ------------------------------------------------------------ events (5.2)


def t_p2lin(alin):
    """alin: step -> A_lin. E1's rule: first checkpoint with A_lin <= theta whose successor meets it too."""
    theta = C0_P2 + 0.5 * (alin[0] - C0_P2)
    steps = sorted(alin)
    return first_sustained(steps, {t: (alin[t] <= theta) for t in steps}), theta


def t_l(dev_log):
    d = {x["step"]: x for x in dev_log}
    steps = sorted(d)
    return first_sustained(steps, {t: d[t]["acc"] >= 0.9 and d[t]["query_swap_both"] >= 0.8 for t in steps})


# ------------------------------------------------------------ decision table (7.1)


TABLE_TEXT = {
    ("+", "+"): "在相同训练配置及预先定义的辅助强度控制下，字母绑定监督相对数字编码辅助监督产生了更大的学习改善，并提高了学会率。不说明线性可读性是唯一机制（1.3）",
    ("+", "0"): "字母绑定监督提高了学会率；本样本不能区分它与数字编码辅助监督的差别",
    ("+", "-"): "两种辅助都可能有益，数字编码辅助监督的改善更大。与“字母内容是关键”的预期相反",
    ("0", "+"): "字母绑定监督未显著提高学会率，但优于数字编码，提示 C2 可能有害（见 C2 对 C0 的描述）",
    ("0", "0"): None,  # depends on the exclusion test
    ("0", "-"): "字母绑定监督未显著提高学会率，且不如数字编码",
    ("-", "+"): "字母绑定监督降低了学会率；它仍优于数字编码，提示两种辅助都可能有害",
    ("-", "0"): "字母绑定监督降低了学会率",
    ("-", "-"): "字母绑定监督降低了学会率，且不如数字编码",
}


def exclusion_wording(n, pb):
    return (f"在本设定（K=2、本模型规模、本训练配方、所选 λ、目标总体 M1*）和本样本量（{n} 个配对种子）下，按预先冻结的拒绝域，"
            f"精确单侧检验在 α = 0.025 下拒绝了“字母绑定监督使第 12000 步学会率至少提高 0.30”（认证 p 值上界 p̄ = {pb}）。"
            "这不证明没有效应，也不排除小于 0.30 的效应。")


def decide(s1, s2, excl, n, bal_ok, spec_ok, repl_ok):
    if (s1, s2) == ("0", "0"):
        text = ("与较大提高不相容：" + exclusion_wording(n, excl["p_bar"])) if excl and excl.get("reject") else \
            "不确定，本样本量下无法区分“无效”与“中等或较大的效应”"
    else:
        text = TABLE_TEXT[(s1, s2)]
        if excl and excl.get("reject") and (s1, s2) == ("0", "+"):
            text += "。" + exclusion_wording(n, excl["p_bar"])
    extra = []
    if s1 == "+" and excl and excl.get("reject"):
        extra.append("效应为正，但与至少 0.30 的提高不相容")
    if s2 in ("+", "-"):  # conclusions depending on P2 (first and third columns)
        if not bal_ok:
            extra.append("降级为描述性：两种辅助的早期强度或裁剪不平衡，C1 对 C2 的差异不能归因于辅助内容")
        if not spec_ok:
            extra.append("C2 也保持了字母可读性：P2 的结论只表述为“字母内容的辅助监督对数字内容的辅助监督”")
    if not repl_ok:
        extra.append("本实验的新种子没有复现 E1 的早期可读性下降")
    return {"cell": [s1, s2], "conclusion": text, "modifiers": extra}


def bal_check(pairing, arm, seeds):
    bad_e = bad_c = 0
    per = {}
    for s in seeds:
        e1, e2 = pairing[f"C1_{arm}_s{s}"], pairing[f"C2_{arm}_s{s}"]
        B = 0.0 if not e2["E_W"] else e2["E_W"] / e1["E_W"]
        dc = abs(e1["clip_share_W"] - e2["clip_share_W"])
        per[s] = {"B": B, "clip_share_diff": dc}
        bad_e += not (0.5 <= B <= 2)
        bad_c += dc > 0.20
    n = len(seeds)
    return {"per_seed": per, "energy_out_of_range": bad_e, "clip_out_of_range": bad_c,
            "pass": bad_e <= 0.25 * n and bad_c <= 0.25 * n}


def analyse_arm(arm, seeds, learned, alin, pairing, alpha, with_exclusion, dev_logs=None):
    """learned[cond][seed] -> bool; alin[cond][seed][step] -> A_lin; pairing: ledger."""
    n = len(seeds)
    out = {"N": n}
    ev = {c: {s: t_p2lin(alin[c][s])[0] for s in seeds} for c in ("C0", "C1", "C2")}
    out["t_P2lin"] = ev
    share = {c: sum(ev[c][s] != NOT_HAPPENED for s in seeds) / n for c in ev}
    up = sum(min(alin["C1"][s][t] for t in MANIP_STEPS) > min(alin["C0"][s][t] for t in MANIP_STEPS) for s in seeds)
    down = sum(min(alin["C1"][s][t] for t in MANIP_STEPS) < min(alin["C0"][s][t] for t in MANIP_STEPS) for s in seeds)
    p_sign = binom_two_sided(min(up, down), up + down)
    manip = {"C1_share_t_P2lin_not_happened": 1 - share["C1"], "cond1": 1 - share["C1"] >= 0.8,
             "sign_test": {"C1_higher": up, "C1_lower": down, "p": p_sign}, "cond2": p_sign <= 0.05 and up > down}
    manip["pass"] = manip["cond1"] and manip["cond2"]
    out["manipulation_check"] = manip
    out["replication_C0_t_P2lin_share"] = share["C0"]
    out["SPEC_C2_t_P2lin_share"] = share["C2"]
    repl_ok, spec_ok = share["C0"] >= 0.8, share["C2"] >= 0.8
    a10, b10, c10, d10 = paired(learned["C1"], learned["C0"])
    a12, b12, c12, d12 = paired(learned["C1"], learned["C2"])
    p1, p2 = mcnemar(b10, c10), mcnemar(b12, c12)
    rej = holm(p1, p2, alpha)
    s1, s2 = sign(rej[0], b10, c10), sign(rej[1], b12, c12)
    out["P1"] = {"b": b10, "c": c10, "p": p1, "rejected_holm": rej[0], "sign": s1}
    out["P2"] = {"b": b12, "c": c12, "p": p2, "rejected_holm": rej[1], "sign": s2}
    out["holm_alpha"] = alpha
    out["learned_rate"] = {c: sum(learned[c].values()) / n for c in learned}
    out["C0_not_learned"] = n - sum(learned["C0"].values())
    excl = exclusion(b10, c10, n) if with_exclusion else None
    out["exclusion_Delta10"] = excl
    bal = bal_check(pairing, arm, seeds)
    out["BAL"] = bal
    out["descriptive"] = {"newcombe95_Delta10": newcombe(a10, b10, c10, d10), "newcombe95_Delta12": newcombe(a12, b12, c12, d12),
                          "Delta12_exclusion_nominal": exclusion(b12, c12, n) if with_exclusion else None,
                          "C2_vs_C0_mcnemar_nominal": dict(zip(("a", "b", "c", "d"), paired(learned["C2"], learned["C0"])),
                                                           p=mcnemar(*paired(learned["C2"], learned["C0"])[1:3]))}
    if not manip["pass"]:
        out["verdict"] = {"status": "不可判定：操纵失败，干预效果无法按预设解释", "table_descriptive_only": True}
    elif out["C0_not_learned"] < 5:
        out["verdict"] = {"status": "学会率对比不提供信息（无改善空间）", "exclusion": "不作结论"}
    else:
        out["verdict"] = dict(status="判定", **decide(s1, s2, excl, n, bal["pass"], spec_ok, repl_ok))
    if dev_logs is not None:
        tl = {c: {s: t_l(dev_logs[c][s]) for s in seeds} for c in ("C0", "C1", "C2")}
        key = lambda v: 12001 if v == NOT_HAPPENED else v  # noqa: E731  later than any step
        res = {}
        ps = []
        for other in ("C0", "C2"):
            earlier = sum(key(tl["C1"][s]) < key(tl[other][s]) for s in seeds)
            later = sum(key(tl["C1"][s]) > key(tl[other][s]) for s in seeds)
            p = binom_two_sided(min(earlier, later), earlier + later)
            diffs = [key(tl["C1"][s]) - key(tl[other][s]) for s in seeds]
            rng = random.Random(0)
            boots = sorted(_median([diffs[rng.randrange(n)] for _ in range(n)]) for _ in range(10000))
            res[f"C1_vs_{other}"] = {"earlier": earlier, "later": later, "same": n - earlier - later, "p": p,
                                     "median_paired_difference": _median(diffs), "bootstrap95": [boots[249], boots[9749]],
                                     "note": "未发生 coded as 12001 (later than any step)"}
            ps.append(p)
        rj = holm(ps[0], ps[1], 0.05)
        res["C1_vs_C0"]["rejected_holm"], res["C1_vs_C2"]["rejected_holm"] = rj
        out["t_L_secondary"] = {"t_L": tl, "tests": res}
    return out


def _median(v):
    v = sorted(v)
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=HERE, help="directory with judgments/, results/, runs/, pairing_ledger.json")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fz = json.load(open(os.path.join(a.base, "e2c_workload_freeze.json")))
    pairing = json.load(open(os.path.join(a.base, "pairing_ledger.json")))
    out = {}
    for arm in ("openmythos", "transformer"):
        seeds = fz["seeds"][arm]
        learned = {c: {s: json.load(open(os.path.join(a.base, "judgments", f"{c}_{arm}_s{s}.json")))["main"]["learned"]
                       for s in seeds} for c in ("C0", "C1", "C2")}
        alin = {c: {s: {t: json.load(open(os.path.join(a.base, "results", f"{c}_{arm}_s{s}_step{t}.json")))["A_lin"] for t in STEPS}
                    for s in seeds} for c in ("C0", "C1", "C2")}
        dev = None
        if arm == "transformer":
            dev = {c: {s: json.load(open(os.path.join(a.base, "runs", f"{c}_{arm}_s{s}.json")))["dev_log"] for s in seeds}
                   for c in ("C0", "C1", "C2")}
        alpha = fz["alpha"][arm]["superiority_holm"]
        out[arm] = analyse_arm(arm, seeds, learned, alin, pairing, alpha, arm == "openmythos", dev)
    out["scope"] = ("OpenMythos and Transformer are separate families, each with family error rate <= 0.05; no cross-"
                    "architecture conclusion; over both families at most 0.10 (Bonferroni)")
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({arm: out[arm]["verdict"] for arm in ("openmythos", "transformer")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
