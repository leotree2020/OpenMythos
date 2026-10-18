#!/usr/bin/env python3
"""Apply the pre-registered gate criteria to runs/g<gate>_*.json."""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CRIT = {
    1: {"min_correct": 31, "max_loss": 0.1},
    2: {"min_correct": 502, "max_loss": 0.1},
}


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    gate = int(sys.argv[1])
    c = CRIT[gate]
    runs = [
        json.load(open(f))
        for f in sorted(glob.glob(os.path.join(HERE, "runs", f"g{gate}_*.json")))
    ]
    n = runs[0]["n"]
    print(f"## Gate {gate}：{n} 道固定 1 跳题\n")
    print(
        f"通过条件（每个种子）：最终在全部 {n} 题上答对 ≥ {c['min_correct']} 题，且 loss ≤ {c['max_loss']}\n"
    )
    print(
        "| 组 | 种子 | 答对 | 准确率 | loss | 预测落在根数字内 | 首次全对的步数 | 实际步数 | 数据未变 | 训练块计算量 | 留出集准确率（仅参考） | 通过 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    verdict = {}
    for arm in ("openmythos", "transformer"):
        ok = []
        for r in sorted((r for r in runs if r["arm"] == arm), key=lambda r: r["seed"]):
            f = r["final"]
            p = (
                f["n_correct"] >= c["min_correct"]
                and f["loss"] <= c["max_loss"]
                and r["data_unchanged_all"]
            )
            ok.append(p)
            print(
                f"| {arm} | {r['seed']} | {f['n_correct']}/{n} | {pct(f['acc'])} | {f['loss']:.4f} | "
                f"{pct(f['pred_in_roots'])} | {r['first_step_all_correct'] or '未达到'} | {r['steps']} | "
                f"{'是' if r['data_unchanged_all'] else '否'} | {r['block_token_steps'] / 1e6:.2f}M | "
                f"{pct(r['heldout_info_only']['acc'])} | {'✓' if p else '✗'} |"
            )
        verdict[arm] = ok
    print("\n## 训练过程摘要（每个种子：第 1 / 500 / 1000 / 最后一次记录）\n")
    for r in sorted(runs, key=lambda r: (r["arm"], r["seed"])):
        pts = (
            [r["log"][0]]
            + [x for x in r["log"] if x["step"] in (500, 1000)]
            + [r["log"][-1]]
        )
        print(
            f"- {r['arm']} 种子 {r['seed']}："
            + "；".join(
                f"step {x['step']} loss {x['set_loss']:.3f} acc {pct(x['set_acc'])} 梯度 {x['grad_norm']:.2f} 无梯度参数 {x['params_without_grad']}"
                for x in pts
            )
        )
    print("\n## 梯度范数分部（最后一次记录，种子均值）\n")
    for arm in ("openmythos", "transformer"):
        rs = [r for r in runs if r["arm"] == arm]
        keys = rs[0]["log"][-1]["grad_norm_parts"].keys()
        print(
            f"- {arm}："
            + "，".join(
                f"{k} {sum(r['log'][-1]['grad_norm_parts'].get(k, 0) for r in rs) / len(rs):.3f}"
                for k in keys
            )
        )
    om = sum(r["block_token_steps"] for r in runs if r["arm"] == "openmythos")
    tf = sum(r["block_token_steps"] for r in runs if r["arm"] == "transformer")
    print(f"\n训练块计算量：openmythos / transformer = {om / tf:.2f}×\n")
    lab = lambda v: (
        "通过"
        if all(v)
        else ("未通过" if not any(v) else f"不稳定（{sum(v)}/{len(v)}），按未通过处理")
    )
    print("## 判定\n")
    for arm, v in verdict.items():
        print(f"- **{arm}**：{lab(v)}")
    a, b = all(verdict["openmythos"]), all(verdict["transformer"])
    if gate == 1:
        nxt = {
            (True, True): "两组都通过 Gate 1：按预登记进入 Gate 2（512 题）。",
            (
                False,
                False,
            ): "两组都未通过：停止。优先检查数据管道、梯度、loss、优化器和实现。",
        }.get((a, b), "只有一组通过：停止，不进入 Gate 2。下一步检查两种架构的训练动力学差异。")
    else:
        nxt = {
            (True, True): "两组都记住 512 题：停止。下一步设计独立的泛化实验。",
            (
                False,
                False,
            ): "两组都记不住 512 题：停止。下一步检查训练预算、容量和优化设置。",
        }.get((a, b), "只有一组记住 512 题：停止。下一步检查两种架构的训练动力学差异。")
    print(f"\n**按预登记的解读：{nxt}**")


if __name__ == "__main__":
    main()
