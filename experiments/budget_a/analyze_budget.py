#!/usr/bin/env python3
"""Apply PREREGISTRATION.md (with revision 1) to the test2 evaluation."""

import json
import sys

CHANCE = 0.25
NEXT = {
    "学会": "以 12,000 步的预算重新设计 Gate A 的 B 级",
    "出现学习迹象": "诊断模型如何使用查询变量，不再单纯延长训练",
    "未满足综合学习迹象标准": "研究优化过程和学习信号，不再单纯延长训练",
}


def level_of(r, best_heuristic):
    if (
        r["acc"] >= 0.90
        and r["root_swap_both"] >= 0.80
        and r["query_swap_both"] >= 0.80
    ):
        return "学会"
    if r["acc_ci95"][0] > best_heuristic and r["query_insensitivity"] < 0.90:
        return "出现学习迹象"
    return "未满足综合学习迹象标准"


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    rows = [json.loads(l) for l in open(sys.argv[1])]
    base = next(r for r in rows if r["type"] == "baselines")
    best = max(
        v
        for k, v in base.items()
        if isinstance(v, float) and not k.startswith("oracle")
    )
    cells = [
        r
        for r in rows
        if r["type"] == "cell" and r["n_loops"] in (4, None) and r["split"] == "test2"
    ]
    keys = [(r["arm"], r["seed"]) for r in cells]
    assert (
        len(keys) == 6 and len(set(keys)) == 6
    ), f"expected 6 unique decision records, got {keys}"
    print(
        f"## A 级训练预算诊断：判定（新测试集，n={base['n']}，哈希 {base['set_sha256'][:12]}）\n"
    )
    print(f"最强的不看答案猜法：{pct(best)}\n")
    print(
        "| 组 | 种子 | 准确率 [95% CI] | 显著高于随机 | 换根双对率 | 换查询双对率 | 查询不敏感率 | 查询敏感性改善（<90%） | 等级 |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    levels = {}
    for arm in ("openmythos", "transformer"):
        lv = []
        for r in sorted((r for r in cells if r["arm"] == arm), key=lambda r: r["seed"]):
            L = level_of(r, best)
            lv.append(L)
            ci = r["acc_ci95"]
            print(
                f"| {arm} | {r['seed']} | {pct(r['acc'])} [{pct(ci[0])}, {pct(ci[1])}] | {'是' if ci[0] > best else '否'} | "
                f"{pct(r['root_swap_both'])} | {pct(r['query_swap_both'])} | {pct(r['query_insensitivity'])} | "
                f"{'是' if r['query_insensitivity'] < 0.90 else '否'} | {L} |"
            )
        levels[arm] = lv
    print("\n## 判定\n")
    summary = {}
    for arm, lv in levels.items():
        if len(set(lv)) == 1:
            summary[arm] = lv[0]
            print(f"- **{arm}**：{lv[0]}（3 个种子一致）")
        else:
            summary[arm] = "不稳定"
            print(f"- **{arm}**：不稳定（种子 1/2/3 分别为：{' / '.join(lv)}）")
    a, b = summary["openmythos"], summary["transformer"]
    if "不稳定" in (a, b):
        nxt = (
            "停止。逐个报告各种子的等级；下一步：比较不一致种子的训练动力学（另行设计）"
        )
    elif a == b:
        nxt = NEXT[a]
    else:
        nxt = "两组等级不同：比较两组的训练动力学，并做等计算量对照"
    print(f"\n**按预登记的下一步：{nxt}**")


if __name__ == "__main__":
    main()
