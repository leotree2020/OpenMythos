#!/usr/bin/env python3
"""Apply PREREGISTRATION.md to results.jsonl and print the decision tables."""

import argparse
import json
import statistics


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    args = ap.parse_args()
    base, cells = {}, {}
    for line in open(args.results):
        r = json.loads(line)
        if r["type"] == "baselines":
            base[r["hops"]] = r
        else:
            cells[(r["arm"], r["seed"], r["n_loops"])] = r
    seeds = sorted({k[1] for k in cells})
    hops = sorted(int(h) for h in next(iter(cells.values()))["acc"])
    main_rows = [("openmythos", 4), ("transformer", None)]

    print("## 逐跳结果（每个种子；准确率 / 反事实双对率 / 跟随率）\n")
    print("| 组 | 种子 | " + " | ".join(f"{h} 跳" for h in hops) + " |")
    print("|---|---|" + "---|" * len(hops))
    for arm, T in main_rows:
        for s in seeds:
            r = cells[(arm, s, T)]
            print(
                f"| {arm}{'' if T is None else f' T={T}'} | {s} | "
                + " | ".join(
                    f"{pct(r['acc'][str(h)])} / {pct(r['cf_both'][str(h)])} / {pct(r['cf_follow'][str(h)])}"
                    for h in hops
                )
                + " |"
            )
    print(
        "| 参照：在题面数字里随机猜 | – | "
        + " | ".join(pct(base[h]["random_root"]) for h in hops)
        + " |"
    )

    print("\n**1 跳中链长全部相同的子集（不存在链长线索）**\n")
    for arm, T in main_rows:
        for s in seeds:
            r = cells[(arm, s, T)]
            print(
                f"- {arm} 种子 {s}：准确率 {pct(r['acc_equal_len']['1'])}，"
                f"双对率 {pct(r['cf_both_equal_len']['1'])}（n={r['n_equal_len']['1']}）"
            )

    print("\n## OpenMythos 不同 T 的准确率（参考，不参与判定）\n")
    Ts = sorted(k[2] for k in cells if k[0] == "openmythos" and k[1] == seeds[0])
    print("| 种子 | 跳数 | " + " | ".join(f"T={t}" for t in Ts) + " |")
    print("|---|---|" + "---|" * len(Ts))
    for s in seeds:
        for h in hops:
            print(
                f"| {s} | {h} | "
                + " | ".join(
                    pct(cells[("openmythos", s, t)]["acc"][str(h)]) for t in Ts
                )
                + " |"
            )

    print("\n## 训练计算量（实际块计算次数 × token 数）\n")
    for s in seeds:
        a = cells[("openmythos", s, 4)]["train_block_token_steps"]
        b = cells[("transformer", s, None)]["train_block_token_steps"]
        print(f"- 种子 {s}：openmythos / transformer = {a / b:.2f}×")

    print("\n## 判定\n")
    verdict = {}
    for arm, T in main_rows:
        one = []
        two = []
        for s in seeds:
            r = cells[(arm, s, T)]
            one.append(
                r["acc"]["1"] >= 0.90
                and r["cf_both"]["1"] >= 0.80
                and r["acc_equal_len"]["1"] >= 0.90
            )
            two.append(r["acc"]["2"] >= 0.80 and r["cf_both"]["2"] >= 0.70)
        lab = lambda v: (
            "学会"
            if all(v)
            else ("未学会" if not any(v) else f"不稳定（{sum(v)}/{len(v)}）")
        )
        verdict[arm] = all(one)
        print(f"- **{arm}**：1 跳 {lab(one)}；2 跳 {lab(two)}")
    key = (verdict["openmythos"], verdict["transformer"])
    interp = {
        (
            True,
            True,
        ): "两者都学会：原任务太难或训练不够。下一步：逐步加难度，再回到深度外推。",
        (
            False,
            True,
        ): "Transformer 学会、OpenMythos 未学会：问题出在 OpenMythos 或其训练方式。下一步：梯度诊断。",
        (
            False,
            False,
        ): "两者都未学会：训练设置问题。下一步：排查学习率、步数、损失设计。",
        (
            True,
            False,
        ): "OpenMythos 学会、Transformer 未学会：OpenMythos 计算量约为 1.8 倍。下一步：等计算量对照。",
    }[key]
    print(f"\n**按事先约定的解读：{interp}**")


if __name__ == "__main__":
    main()
