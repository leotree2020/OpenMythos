#!/usr/bin/env python3
"""Apply PREREGISTRATION.md section 8/9 to one level's eval output."""

import json
import sys

NEXT = {
    "both": {
        "A": "进入 B 级",
        "B": "进入 C1 级",
        "C1": "进入 C2 级",
        "C2": "Gate A 完成：下一步回到多跳与深度外推的设计",
    },
    "one": "停止。下一步：比较两组在该级别上的训练动力学",
    "none": {
        "A": "停止。下一步：在 A 级上检查训练预算是否是瓶颈",
        "B": "停止。下一步：诊断一跳组合，检查模型是否找到了中间变量",
        "C1": "停止。下一步：研究干扰链数量的影响（介于 B 和 C1 之间）",
        "C2": "停止。下一步：区分是链长混合，还是 1/2 跳混合训练导致失败",
    },
}


def pct(x):
    return "–" if x is None else f"{100 * x:.1f}%"


def main():
    path = sys.argv[1]
    rows = [json.loads(l) for l in open(path)]
    base = next(r for r in rows if r["type"] == "baselines")
    level = base["level"]
    cells = [r for r in rows if r["type"] == "cell" and r["n_loops"] in (4, None)]
    print(
        f"## {level} 级判定（{base['split']} 集，n={base['n']}，查询交换可评测 {base['n_query_swap']} 题）\n"
    )
    print(
        "| 组 | 种子 | 准确率 [95% CI] | 根交换双对率 | 查询交换双对率 [95% CI] | 等链长子集 | 落在根内 | 通过 |"
    )
    print("|---|---|---|---|---|---|---|---|")
    verdict = {}
    for arm in ("openmythos", "transformer"):
        ok = []
        for r in sorted((r for r in cells if r["arm"] == arm), key=lambda r: r["seed"]):
            p = (
                r["acc"] >= 0.90
                and r["root_swap_both"] >= 0.80
                and r.get("query_swap_both", 0) >= 0.80
            )
            if level == "C2":
                p = p and r["acc_equal_length"] >= 0.90
            ok.append(p)
            ci = r["acc_ci95"]
            qci = r.get("query_swap_both_ci95")
            print(
                f"| {arm} | {r['seed']} | {pct(r['acc'])} [{pct(ci[0])}, {pct(ci[1])}] | {pct(r['root_swap_both'])} | "
                f"{pct(r.get('query_swap_both'))} [{pct(qci[0]) if qci else '–'}, {pct(qci[1]) if qci else '–'}] | "
                f"{pct(r.get('acc_equal_length'))} | {pct(r['pred_in_roots'])} | {'✓' if p else '✗'} |"
            )
        verdict[arm] = ok
    heur = {
        k: v
        for k, v in base.items()
        if k
        not in (
            "type",
            "level",
            "split",
            "set_sha256",
            "n",
            "n_query_swap",
            "n_equal_length",
        )
    }
    best = max((v for k, v in heur.items() if not k.startswith("oracle")), default=None)
    print("\n参照（同一批题）：" + "，".join(f"{k} {pct(v)}" for k, v in heur.items()))
    print(f"最强的不看答案的猜法：{pct(best)}")
    lab = lambda v: (
        "通过"
        if all(v)
        else ("未通过" if not any(v) else f"不稳定（{sum(v)}/{len(v)}），按未通过处理")
    )
    print("\n## 判定\n")
    for arm, v in verdict.items():
        print(f"- **{arm}**：{lab(v)}")
    a, b = all(verdict["openmythos"]), all(verdict["transformer"])
    nxt = (
        NEXT["both"][level]
        if a and b
        else (NEXT["none"][level] if not a and not b else NEXT["one"])
    )
    print(f"\n**按预登记的下一步：{nxt}**")


if __name__ == "__main__":
    main()
