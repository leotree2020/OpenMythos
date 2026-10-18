#!/usr/bin/env python3
"""Apply PREREGISTRATION.md (with revision 1) to the test2 evaluation."""

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

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
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_jsonl")
    ap.add_argument("--split", default="test2", choices=["test2", "dev"])
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--runs-dir", default=None)
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    rows = [json.loads(l) for l in open(args.eval_jsonl)]
    bases = [r for r in rows if r["type"] == "baselines"]
    assert len(bases) == 1, f"expected 1 baselines record, got {len(bases)}"
    base = bases[0]
    assert base["split"] == args.split, base["split"]
    if args.split == "test2":
        man = json.load(open(os.path.join(HERE, "sets", "manifest.json")))["A_test2"]
        assert base["set_sha256"] == man["sha256"], "test2 hash differs from manifest"
        assert base["n"] == man["rows"] == 1000, base["n"]
    best = max(
        v
        for k, v in base.items()
        if isinstance(v, float) and not k.startswith("oracle")
    )
    cells = [
        r
        for r in rows
        if r["type"] == "cell" and r["n_loops"] in (4, None) and r["split"] == args.split
    ]
    keys = sorted((r["arm"], r["seed"]) for r in cells)
    want = sorted((a, s) for a in ("openmythos", "transformer") for s in seeds)
    # exactly one decision record for each of OpenMythos and Transformer x
    # each pre-registered seed: no missing, duplicated or foreign records
    assert keys == want, f"decision records {keys}, expected {want}"
    for r in cells:
        assert r["n"] == base["n"], (r["arm"], r["seed"], r["n"])
        assert (r["n_loops"] == 4) == (r["arm"] == "openmythos"), r
        if args.runs_dir:
            ck = os.path.join(args.runs_dir, f"A_{r['arm']}_s{r['seed']}.pt")
            assert os.path.normpath(r["ckpt"]) == os.path.normpath(ck), (r["ckpt"], ck)
    print(
        f"## A 级训练预算诊断：判定（{'新测试集' if args.split == 'test2' else '开发集（仅测试流程，不是正式判定）'}，n={base['n']}，哈希 {base['set_sha256'][:12]}）\n"
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
