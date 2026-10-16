# R1 Gate D — 600-step Tiny OpenMythos 真实文本训练结果

**日期：2026-10-16；状态：用户 GitHub Codespaces 已实际完成 600-step 续训、只读诊断、匹配暴露量 Bigram/Unigram 比较与 60/200/600 自动一致性验证。** 数据源是用户贴出的完整终端日志；未将本地二进制权重上传到 GitHub。

## 验收事实

- `Resumed from step 200`：从 200-step 的独立 Checkpoint 副本续训到累计 **600 optimizer steps**，没有重训、覆盖先前 checkpoint。
- Tiny OpenMythos **GQA**, depth=2, dim=48, seq_len=64, batch_size=4, 257 类 UTF-8 byte+EOS Tokenizer，真实 WikiText-2 语料选择前缀。模型训练目标位置累计 `600 × 4 × 64 = 153600`；存在重复随机窗口，不能等同 153600 个独立字节。
- `r1_gate_d_compare.py` 确认三个实验模型配置、数据指纹、Heldout 计分 Token 数、Checkpoint 步数、恢复链、RNG offset 精确重放全部一致。
- 当前 **600-step Gate D 的单元测试数量未由本轮终端日志提供**；上一阶段 86/86 PASS，不应虚构本轮单元测试结果。

## 同条件 60/200/600 曲线

| 项目 | Step 60 | Step 200 | Step 600 |
|---|---:|---:|---:|
| 模型 Heldout NLL ↓ | 3.376346 | 3.225532 | **2.417668** |
| 模型 Heldout PPL ↓ | 29.263642 | 25.166962 | **11.219663** |
| 相同 SGD target 暴露量 Unigram PPL ↓ | 27.512917 | 26.951090 | 26.951234 |
| 相同 SGD target 暴露量 Bigram PPL ↓ | 19.158092 | 14.811675 | **13.021447** |
| 教师强制验证的 argmax 空格预测比例 | 1.0 | 1.0 | **0.3251953125** |
| 反转历史字节顺序平均概率 TV | 0.0000217 | 0.0024494 | **0.2147814** |

600-step 模型 PPL 11.219663 与同暴露量 Bigram PPL 13.021447 相比，**更低约 13.8%**；与整个训练前缀估计的 Bigram PPL 12.597172 相比也更低。在相同验证窗口和 Tokenizer 上，模型目前确实已经优于这些给定超参数的字节级 Bigram/Unigram 统计基线。但统计基线使用固定 Add-1 smoothing，尚不能声称击败了经过独立调参的最强 n-gram 或证明深层语义理解。

## 真实生成能力仍然不达标

- 60/200 步的连续空格塌缩已经消失；600-step Greedy 对三个不同提示词均重复 `the the the ...`，只有常见字符模式，没有连续有意义语句。
- 固定温度 0.9、top-k 32、seed=91 的采样给出若干类英语词样的碎片，随着提示词改变产生不同输出；例如 `wollas 101 tein massir...`，但整体依旧不连贯。
- Model nonspace NLL **2.8187007668704696**，比 200 步的 3.5756125681328053 下降；预测空格比例 **0.3252**，接近但仍高于实际验证目标空格的 **0.1943359375**。

## 上下文消融的正确解释

- 600-step 的 reverse-history mean TV = **0.21478137630037963**，说明对反转之前 63 字节顺序有明显预测分布敏感性。
- Reverse-history target NLL 差（reversed minus original）= **−0.036499857902526855**，即这 16 个最后字节目标中**反转历史上下文反而使 NLL 平均略下降**。
- 因此不能称模型已经证明“正确理解句法语义”或“原始历史顺序预测更好”；这里只能确认结构上的上下文敏感性和特定 Heldout 上优于所列字节统计基线。

## 研究结论与下一闸门

**R1 Gate D：工程可复现性 PASS；最小统计预测能力 PASS（相对固定 Add-1 Bigram）；文本连贯生成 FAIL；Mythos 架构真实性仍 UNKNOWN。**

遵守 Gate D 的预定截止点：**不再对这只 48 维 CPU Tiny 模型追加 1000/2000 步训练**。下一步先用**同一 600-step checkpoint**在更多的独立 validation windows 上进行一次更稳健的读操作评估，记录 matched Bigram 与模型每个窗口的配对差异；原先的 16 个窗口（1024 目标字节）不能直接当作广泛语言建模的结论。之后再转向可信 Tokenizer、100M+ GPU 规模、上游复现及标准 Transformer 预算对照。

现有本地证据：

- `research/mini_mythos/results/r1/pilot_gqa_step600/latest.pt`
- `research/mini_mythos/results/r1/pilot_gqa_step600/report.json`
- `research/mini_mythos/results/r1/pilot_gqa_step600/diagnostics.json`
- `research/mini_mythos/results/r1/pilot_gqa_step600/exposure_baselines.json`
- `research/mini_mythos/results/r1/gate_d_comparison.json`

**所有文件属于 Git 忽略目录，并未自动上传。** 本报告只使用用户 Codespaces 终端可见结果，不能宣称已复现 Anthropic Mythos 内部权重或训练配方。
