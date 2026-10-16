# OpenMythos 上游审计 v0.1（2026-10-16）

**审计范围**：公开 `main` 分支 `open_mythos/main.py`、`tokenizer.py`、`training/3b_fine_web_edu.py`、`pyproject.toml`；社区 PR #15、#26、#27 和 Issue #28。报告只是代码阅读与社区结果复核，不表示此机器已运行上游完整代码。

| ID | 级别 | 观察 / 假设 | 证据 | 后续验证 |
|---|---|---|---|---|
| A01 | P0 | 深度外推并未被社区实验支持。8-loop 固定训练在 8 loops 最佳，更多 loops 反退化；随机训练出现平台。 | [Issue #28](https://github.com/kyegomez/OpenMythos/issues/28) | 相同配置、tokenizer 和 held-out 集合复现 PPL sweep |
| A02 | P0 | `RecurrentBlock.forward` 中 `cumulative_p` 未指定 `dtype` 且使用 `still_running.float()`；直接 BF16 权重前向存在 dtype promotion 风险。 | [main.py](https://github.com/kyegomez/OpenMythos/blob/main/open_mythos/main.py), [PR #26](https://github.com/kyegomez/OpenMythos/pull/26) | BF16 动态 forward、backward 检查；不要假定 PR #26 整体适用于当前 main |
| A03 | P1 | 当前 `main.py` `_causal_mask` 已传入 `x.dtype`，因此 PR #26 的掩码问题似乎已修复；注意分支差异。 | [main.py](https://github.com/kyegomez/OpenMythos/blob/main/open_mythos/main.py) | 测试 GQA/MLA，full/cached 相同输出 |
| A04 | P1 | ACT 达到 n_loops 限制仍可能没有分配最后残余权重，导致 `h_out` 衰减；是否影响结果需量化。 | [main.py](https://github.com/kyegomez/OpenMythos/blob/main/open_mythos/main.py) | `scripts/smoke.py` ACT mass 探针 |
| A05 | P1 | 主训练脚本 `fused=True` + FP16 autocast 未显式启用 GradScaler。 | [3b_fine_web_edu.py](https://github.com/kyegomez/OpenMythos/blob/main/training/3b_fine_web_edu.py), [PR #15](https://github.com/kyegomez/OpenMythos/pull/15) | 单 GPU FP16 scale、step 与梯度有效性验证 |
| A06 | P1 | 数据流在 Checkpoint 恢复后从开头迭代，无法精确恢复样本位置。 | [3b_fine_web_edu.py](https://github.com/kyegomez/OpenMythos/blob/main/training/3b_fine_web_edu.py) | 审核数据跳过/状态恢复方式，保存 shard/offset，避免重复与泄漏 |
| A07 | P1 | 主训练入口未包含独立 held-out loss/PPL 测量；PR #15 意图补足，但其分片方案有社区反馈的重叠疑虑。 | [PR #15](https://github.com/kyegomez/OpenMythos/pull/15) | 以静态拆分的文件/文档 ID 创建隔离评测集合 |
| A08 | P2 | `MythosTokenizer` 默认依赖外部 `openai/gpt-oss-20b` tokenizer，应固定 tokenizer revision 和词表大小。 | [tokenizer.py](https://github.com/kyegomez/OpenMythos/blob/main/open_mythos/tokenizer.py) | manifest 保存名称、revision、checksum |
| A09 | P2 | `torch.load(weights_only=False)` 加载 pickle-compatible checkpoint；需要可信来源。 | [3b_fine_web_edu.py](https://github.com/kyegomez/OpenMythos/blob/main/training/3b_fine_web_edu.py) | 仅加载本地受信任 checkpoint，改用 safetensors + JSON 配置 |
| A10 | P2 | LTI Injection 保证线性项对角矩阵 `A` 谱半径小于 1；不自动证明完整非线性循环网络的全局稳定性。 | [main.py](https://github.com/kyegomez/OpenMythos/blob/main/open_mythos/main.py) | 监控隐藏状态范数、梯度范数与 loop sweep |

**重要边界**：OpenMythos README 是自主推测实现，不是 Anthropic Claude Mythos 的真实架构证明；PR #27 的单 H100 实验是社区报告，并非本项目独立复现结论。
