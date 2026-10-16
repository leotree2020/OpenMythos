# Mini-Mythos 第二轮执行记录 (2026-10-16)

## 已完成的可核验工作

- 复查 OpenMythos 上游仓库公开源代码：`open_mythos/main.py` 的 `RecurrentBlock.forward`/ACT 权重逻辑、`GQAttention`/`MLAttention`，`pyproject.toml` 与训练入口。
- 新增 `act_math.py`，独立模拟官方源码中的停止权重累加算法（仅数学部分）。
- 新增 5 个离线单元测试，并与原先 3 个数据流水线测试合并，总计 **8/8 PASS**。
- 新增 `act_diagnostics.py`，用于在真实上游模型运行时记录停止权重质量，不修改模型。
- 更新 GitHub Actions：同时安装 PyTorch 与 `transformers`，GQA/MLA 分开执行，保存 JSON 报告；增加 GQA 两深度小规模训练通路测试。

## 可重复的 ACT 数学现象

原始逻辑：只有当 `cumulative_p + p >= threshold` 时，才分配 `remainder = 1-cumulative_p`；否则分配 `p`。达到最大循环次数但尚未达到阈值，没有额外分配机制。

示例：阈值 0.99、循环 2 次、每次 p=0.1，则原始权重为 0.1+0.1=0.2；强制最后余量的候选规则是 0.1+0.9=1.0。注意候选规则是**假说**，不能从数值质量单独推导语言模型指标变好。

## 未完成、禁止误述的事项

- 当前运行环境无法联网克隆 GitHub，也未加载上游代码，不可声称完成 GQA/MLA/KV Cache 真实动态验证。
- GitHub 账号连接已确认，但本次可用操作接口中没有 Repository 写入工具；尚未 Fork、Push 或触发真实 GitHub Actions。
- 还没有运行 PR #27 的 GPU 训练或复现其 PPL 结果。
- 没有更改模型架构与权重，也不宣称任何 Mythos 级能力。

## 下一道门槛 / 判定标准

1. 在真实 Fork 中运行 CPU smoke 并抓取 `commit SHA` + GQA/MLA 报告；若 cache equivalence、mask 或梯度测试 FAIL，优先处理。
2. 收集 ACT mass 在 1、2、4、8 loops 下的分布；如明显不足，评估是否构成实验混杂因素。
3. 执行 PR #27 原始实验前，核查 tokenizer 与数据版本、eval/train 不交叉、训练预算，并把复现组固定为 `baseline_1/fixed_8/random`。
4. 只在训练过的权重上使用同一 held-out 数据检验 ACT 修正候选，比较 PPL、收敛、tokens/s、显存，并至少重复多个随机种子。
