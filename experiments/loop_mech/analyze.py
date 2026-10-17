#!/usr/bin/env python3
"""
Decision tables for the 2×2 multi-hop experiment, applying the thresholds in
PREREGISTRATION.md mechanically. Writes markdown to stdout and, with --json,
the numbers behind every table.

    python experiments/loop_mech/analyze.py experiments/loop_mech/results.jsonl \\
        --budget experiments/loop_mech/train_budget.json --json analysis.json
"""

import argparse
import json
import statistics
from collections import defaultdict

MECHS = ["fixed_act", "fixed_final", "rand_act", "rand_final"]
GROUPS = {
    "1–4": range(1, 5),
    "5–8": range(5, 9),
    "9–12": range(9, 13),
    "5–12": range(5, 13),
}
CORE_T = [4, 8, 16, 24]

# PREREGISTRATION.md thresholds
LEARN_ACC, LEARN_CF = 0.80, 0.60
GAP_T4, GAIN, ABOVE_BASE, CF_GAIN, IN_DROP = 0.15, 0.05, 0.10, 0.05, 0.02


def m(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def f(x, pct=True, sign=False):
    if x is None:
        return "–"
    s = f"{100 * x:+.1f}" if sign else f"{100 * x:.1f}"
    return s + ("%" if pct else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--budget", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    base, cells = {}, {}
    for line in open(args.results):
        r = json.loads(line)
        if r["type"] == "baselines":
            base[r["hops"]] = r
        elif r["type"] == "cell":
            cells[(r["mech"], r["seed"], r["n_loops"])] = r
    mechs = [x for x in MECHS if any(k[0] == x for k in cells)]
    seeds = sorted({k[1] for k in cells})
    Ts = sorted({k[2] for k in cells})
    hops_avail = sorted(int(h) for h in next(iter(cells.values()))["acc"])

    def g(mech, seed, T, key, grp):
        r = cells.get((mech, seed, T))
        if r is None:
            return None
        return m([r[key].get(str(h)) for h in GROUPS[grp] if h in hops_avail])

    def bl(grp, key="majority_root"):
        return m([base[h][key] for h in GROUPS[grp] if h in base])

    out = {"baselines": {}, "acc": {}, "verdict": {}}
    P = print

    P("## A. 参照基线（不追踪链条也能得到的准确率）\n")
    P("| 组 | 均匀随机 | 随机猜出现过的根 | 猜出现最多的根 |")
    P("|---|---|---|---|")
    for grp in GROUPS:
        row = [bl(grp, "uniform"), bl(grp, "random_root"), bl(grp, "majority_root")]
        out["baselines"][grp] = row
        P(f"| {grp} 跳 | " + " | ".join(f(x) for x in row) + " |")

    cols = [
        ("1 跳", [1]),
        ("2 跳", [2]),
        ("3 跳", [3]),
        ("4 跳", [4]),
        ("5–8 跳", list(range(5, 9))),
        ("9–12 跳", list(range(9, 13))),
    ]

    def gh(mech, seed, T, key, hs):
        r = cells.get((mech, seed, T))
        return (
            None
            if r is None
            else m([r[key].get(str(h)) for h in hs if h in hops_avail])
        )

    out["core"] = {}
    for key, title in (
        ("acc", "准确率"),
        ("cf_both", "反事实双对率 cf_both（原题与改根后的题都答对）"),
        ("cf_follow", "反事实跟随率 cf_follow（改根后答案跟着变成新根）"),
    ):
        for T in (4, 8):
            P(f"\n## 核心表：逐跳{title}，T={T}（每个种子分别列出）\n")
            P("| 机制 | 种子 | " + " | ".join(c for c, _ in cols) + " |")
            P("|---|---|" + "---|" * len(cols))
            for mech in mechs:
                for s in seeds:
                    v = [gh(mech, s, T, key, hs) for _, hs in cols]
                    out["core"].setdefault(key, {}).setdefault(str(T), {}).setdefault(
                        mech, {}
                    )[str(s)] = v
                    P(f"| {mech} | {s} | " + " | ".join(f(x) for x in v) + " |")
            if key == "acc":
                for bk, bn in (
                    ("majority_root", "捷径基线：猜出现最多的根"),
                    ("random_root", "参照：随机猜出现过的根"),
                    ("uniform", "参照：均匀随机"),
                ):
                    v = [m([base[h][bk] for h in hs if h in base]) for _, hs in cols]
                    P(f"| {bn} | – | " + " | ".join(f(x) for x in v) + " |")
    out["core_cols"] = [c for c, _ in cols]

    P("\n## B. 绝对准确率（每个种子；T=4 / 8 / 16 / 24）\n")
    for grp in ["1–4", "5–8", "9–12"]:
        P(f"\n**{grp} 跳**（猜出现最多的根：{f(bl(grp))}）\n")
        P("| 机制 | 种子 | " + " | ".join(f"T={t}" for t in CORE_T) + " |")
        P("|---|---|" + "---|" * len(CORE_T))
        for mech in mechs:
            for s in seeds:
                vals = [g(mech, s, t, "acc", grp) for t in CORE_T]
                out["acc"].setdefault(mech, {}).setdefault(str(s), {})[grp] = dict(
                    zip(CORE_T, vals)
                )
                P(f"| {mech} | {s} | " + " | ".join(f(v) for v in vals) + " |")

    P("\n## C. 同一模型增加 T 后的准确率变化（相对 T=4，百分点）\n")
    P("| 机制 | 种子 | 1–4 跳 T=8 | T=16 | T=24 | 5–12 跳 T=8 | T=16 | T=24 |")
    P("|---|---|---|---|---|---|---|---|")
    for mech in mechs:
        for s in seeds:
            d = []
            for grp in ["1–4", "5–12"]:
                a4 = g(mech, s, 4, "acc", grp)
                d += [
                    (
                        None
                        if a4 is None or g(mech, s, t, "acc", grp) is None
                        else g(mech, s, t, "acc", grp) - a4
                    )
                    for t in (8, 16, 24)
                ]
            P(f"| {mech} | {s} | " + " | ".join(f(x, sign=True) for x in d) + " |")

    P("\n## D. 每个种子的 T—准确率曲线（全部深度）\n")
    P("| 机制 | 种子 | 组 | " + " | ".join(f"T={t}" for t in Ts) + " |")
    P("|---|---|---|" + "---|" * len(Ts))
    curves = {}
    for mech in mechs:
        for s in seeds:
            for grp in ["1–4", "5–8", "9–12"]:
                vals = [g(mech, s, t, "acc", grp) for t in Ts]
                curves.setdefault(mech, {}).setdefault(str(s), {})[grp] = vals
                P(
                    f"| {mech} | {s} | {grp} | "
                    + " | ".join(f(v, pct=False) for v in vals)
                    + " |"
                )
    out["curves"] = {"T": Ts, "data": curves}

    P("\n## E. 反事实检查 cf_both（原题和改根后的题都答对的比例）\n")
    P("| 机制 | 种子 | 1–4 跳 T=4 | 5–12 跳 T=4 | 5–12 跳 T=8 | 5–12 跳 T=16 |")
    P("|---|---|---|---|---|---|")
    for mech in mechs:
        for s in seeds:
            v = [g(mech, s, 4, "cf_both", "1–4")] + [
                g(mech, s, t, "cf_both", "5–12") for t in (4, 8, 16)
            ]
            P(f"| {mech} | {s} | " + " | ".join(f(x) for x in v) + " |")

    P("\n## F. 推理成本（种子均值，全部跳数平均）\n")
    P(
        "| 机制 | T | 实际循环数/次 | 循环计算量（相对同机制 T=4） | 墙钟时间（相对同机制 T=4） |"
    )
    P("|---|---|---|---|---|")
    cost = {}
    for mech in mechs:
        for t in CORE_T:
            lr = m(
                [
                    m(list(cells[(mech, s, t)]["loops_run"].values()))
                    for s in seeds
                    if (mech, s, t) in cells
                ]
            )
            lt = m(
                [
                    sum(cells[(mech, s, t)]["loop_tokens"].values())
                    / sum(cells[(mech, s, 4)]["loop_tokens"].values())
                    for s in seeds
                    if (mech, s, t) in cells and (mech, s, 4) in cells
                ]
            )
            ws = m(
                [
                    sum(cells[(mech, s, t)]["fwd_seconds"].values())
                    / sum(cells[(mech, s, 4)]["fwd_seconds"].values())
                    for s in seeds
                    if (mech, s, t) in cells and (mech, s, 4) in cells
                ]
            )
            cost.setdefault(mech, {})[t] = (lr, lt, ws)
            P(f"| {mech} | {t} | {lr:.2f} | {lt:.2f}× | {ws:.2f}× |")
    out["inference_cost"] = cost

    if args.budget:
        bud = [r for r in json.load(open(args.budget)) if "mech" in r]
        P("\n## G. 训练计算量（RNG 回放得到的名义值）\n")
        P("| 机制 | 种子 | 平均训练深度 | 相对 fixed |")
        P("|---|---|---|---|")
        for r in bud:
            P(
                f"| {r['mech']} | {r['seed']} | {r['mean_depth']:.3f} | {r['budget_vs_fixed']:.3f}× |"
            )
        out["train_budget"] = bud

    P("\n## H. 隐藏状态（8 跳样本，T=24，种子均值）\n")
    P(
        "| 机制 | 第 1 轮 RMS | 最后一轮 RMS | 第 4 轮相对变化 | 最后一轮相对变化 | 实际轮数 |"
    )
    P("|---|---|---|---|---|---|")
    states = {}
    for mech in mechs:
        rs = [cells[(mech, s, max(Ts))] for s in seeds if (mech, s, max(Ts)) in cells]
        rms0 = m([r["h_rms_per_loop"][0] for r in rs])
        rmsL = m([r["h_rms_per_loop"][-1] for r in rs])
        rel4 = m(
            [
                (
                    r["rel_change_per_loop"][3]
                    if len(r["rel_change_per_loop"]) > 3
                    else None
                )
                for r in rs
            ]
        )
        relL = m([r["rel_change_per_loop"][-1] for r in rs])
        n = m([len(r["h_rms_per_loop"]) for r in rs])
        states[mech] = {
            "rms_first": rms0,
            "rms_last": rmsL,
            "rel4": rel4,
            "rel_last": relL,
            "loops": n,
            "per_seed": {
                str(r["seed"]): {
                    "rms": r["h_rms_per_loop"],
                    "rel": r["rel_change_per_loop"],
                }
                for r in rs
            },
        }
        P(
            f"| {mech} | {rms0:.2f} | {rmsL:.2f} | {f"{rel4:.3f}" if rel4 is not None else '–'} | {relL:.3f} | {n:.1f} |"
        )
    out["states"] = states

    P("\n## I. 按预先登记标准的判定\n")
    for mech in mechs:
        train_T = [4] if mech.startswith("fixed") else [4, 8]
        learned = []
        for s in seeds:
            best = max(train_T, key=lambda t: g(mech, s, t, "acc", "1–4") or 0)
            learned.append(
                (
                    s,
                    best,
                    g(mech, s, best, "acc", "1–4"),
                    g(mech, s, best, "cf_both", "1–4"),
                )
            )
        ok1 = all(
            a is not None and a >= LEARN_ACC and c >= LEARN_CF for _, _, a, c in learned
        )
        P(f"\n**{mech}**")
        P(
            "- 判定一（学会范围内任务）："
            + ("满足" if ok1 else "不满足")
            + "；"
            + "，".join(
                f"种子{s} T={t}: acc {f(a)} cf {f(c)}" for s, t, a, c in learned
            )
        )
        checks = defaultdict(list)
        for s in seeds:
            a = {t: g(mech, s, t, "acc", "5–12") for t in Ts}
            ain = {t: g(mech, s, t, "acc", "1–4") for t in Ts}
            cf = {t: g(mech, s, t, "cf_both", "5–12") for t in Ts}
            bt = max((8, 16), key=lambda t: a[t])
            checks["T=4 能力不足"].append(ain[4] - a[4] >= GAP_T4)
            checks["T=8、16 均有收益"].append(
                a[8] - a[4] >= GAIN and a[16] - a[4] >= GAIN
            )
            checks["高于捷径且 cf 同步提升"].append(
                a[bt] - bl("5–12") >= ABOVE_BASE and cf[bt] - cf[4] >= CF_GAIN
            )
            checks["范围内不退化"].append(
                ain[4] - ain[8] <= IN_DROP and ain[4] - ain[16] <= IN_DROP
            )
            checks["T=24 不倒退"].append(a[24] >= a[4])
        ok2 = ok1 and all(all(v) for v in checks.values())
        for k, v in checks.items():
            P(
                f"- {k}："
                + " / ".join("✓" if x else "✗" for x in v)
                + "（种子 "
                + " / ".join(map(str, seeds))
                + "）"
            )
        verdict = (
            "有证据支持"
            if ok2
            else (
                "学会了任务，但没有可靠的深度收益"
                if ok1
                else "未学会范围内任务，不能评估深度外推"
            )
        )
        P(f"- **结论：{verdict}**")
        out["verdict"][mech] = {
            "learned": ok1,
            "depth_gain": ok2,
            "checks": checks,
            "learned_detail": learned,
            "text": verdict,
        }

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1, default=str)


if __name__ == "__main__":
    main()
