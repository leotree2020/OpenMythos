# R2 Gate C — BF16 Autocast 候选 CPU 实测

**日期：2026-10-16；证据：用户 GitHub Codespaces 终端日志。** 当前只有 CPU 可用，PyTorch `2.14.1+cu130`。本结果验证的是研究层微型前向/反向路径，**不是** 117.8M 上游 PR27 GPU 训练。

## 真实运行与验收

- **120/120 单元测试 PASS**（4.398 秒）。
- 执行了 `python research/mini_mythos/scripts/r2_bf16_autocast_candidate.py --repo . --device cpu --attentions gqa mla`。
- GQA：BF16 logits、CE Loss `4.521300`，裁剪前 gradient norm `1.924440`，相位 `phase_preserved=True`，与 FP32 logits 的最大绝对差 `0.00234181`，**PASS**。
- MLA：BF16 logits、CE Loss `4.605480`，裁剪前 gradient norm `1.942811`，相位 `phase_preserved=True`，与 FP32 logits 的最大绝对差 `0.00261885`，**PASS**。
- 研究程序还检查非零且有限的参数梯度、FP32 master weights 与 `freqs_cis`/`freqs_cis_mla` 复数相位逐元素保留；测试已完成成功返回。
- 工具声明：`Source modified: False; real-model GPU training: NOT_PERFORMED`。
- 实验记录保存于 Git 忽略的 `research/mini_mythos/results/r2/bf16_autocast_candidate.json`，当前报告依据终端输出，未独立下载用户本地 JSON。

| 测量 | GQA | MLA |
|---|---:|---:|
| BF16 Loss | 4.521300 | 4.605480 |
| 反向梯度 Norm（裁剪前） | 1.924440 | 1.942811 |
| RoPE Complex64 相位保持 | **True** | **True** |
| MaxAbs(logits BF16-FP32) | 0.00234181 | 0.00261885 |

## 解释

已证明（限定范围）：在微型 GQA/MLA 模型与 CPU BF16 autocast 下，**保留 FP32 模型主参数、Complex64 RoPE 缓存、将全序列因果注意力 Mask 暂时调整为 BF16** 的方式能够完成一次前向、CE Loss 和反向传播，且没有像 PR27 的整模型 BF16 转换那样丢失复数相位。

未证明：正式 BF16 GPU kernel/FlashAttention 路径、长时间训练稳定性、优化器更新及恢复数值一致性、ACT 在所有深度与输入上的精度、KV Cache 分块、规模 117.8M 或更大、自然语言模型质量。日志中 FP32/BF16 logits 差异是数值比较而非明确的工程误差上限，不可单独证明训练性能无退化。

**Gate C CPU 路径 PASS，生产/GPU 集成状态 BLOCKED。** 不会自动修改 `open_mythos/main.py` 或合并未复核的 PR27 源码。

## R2 Gate D：Tokenization ID/Revision/Checkpoint Contract（研究层隔离）

下一项 P0 是上游 PR27 在训练和评估中可以加载**不同 Tokenizer**。准备冻结不可变 Hugging Face 模型 Commit、完整 token→ID 词表散列、Fast Tokenizer backend 配置散列、special Token ID、代表性 encoding probes；再严格复验同一 SHA 的 tokenizer，并为未来 checkpoint 元数据和评估器提供 fail-closed 一致性检查。

此项检查不训练语言模型、不读取 WikiText Test、不下载大模型权重；使用 PR27 实际的 `gpt2` Tokenizer，而不是前期 R1 的 UTF-8 byte tokenizer。研究层工具只提供可验证的 contract；**PR27 train.py/evaluate.py 仍未接入此 Contract，不能因此宣称正式训练评估已经受保护**。

[R2 Gate B 原始 BF16 缺陷](R2_GATE_B_RESULT.md) · [BF16 CPU 工具](../scripts/r2_bf16_autocast_candidate.py)
