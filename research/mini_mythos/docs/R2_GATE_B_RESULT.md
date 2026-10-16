# R2 Gate B：固定上游 PR #27 源码审计与 RoPE BF16 损坏实测结果

**2026-10-16，用户 Codespaces 实测**：114/114 单元测试 PASS（3.971 秒）；上游 PR27 源代码固定 SHA `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`；工作分支 Git revision `82cf7aeddee4c2f32057cbe3aa623fb8fd21d435`。

## 1. 审计确认（静态源码标记）

在固定 SHA 上，`r2_pr27_static_audit.py` 的14个模式规则全部 FOUND：

| 优先级 | 规则 | 结果 |
|---|---|---|
| P0 | GPU_HARDCODE | FOUND：训练/评估依赖 CUDA |
| P0 | ROPE_COMPLEX_BUFFER_CAST | FOUND：整模型 BF16 转换会包含复杂频率缓存 |
| P0 | TRAIN_EVAL_TOKENIZER_MISMATCH | FOUND：eval 可以独立指定 tokenizer |
| P0 | DATASET_REVISION_MUTABLE | FOUND：Streaming 数据 revision 未固定 |
| P0 | LOADER_NO_RESUME_CURSOR | FOUND：checkpoint 不保存数据 cursor |
| P1 | HELDOUT_SKIP_ASSUMPTION | FOUND：`skip_docs` 分割依赖估算 |
| P1 | EVAL_UNSAFE_PICKLE | FOUND：读取 `weights_only=False` |
| P1 | LORA_PARAM_DRIFT | FOUND：1 vs 8 循环的 LoRA scale 参数行数不同 |
| P1 | BASELINE_NOT_PLAIN_TRANSFORMER | FOUND：单循环基线保留 RDT/LTI/ACT/MoE |
| P1 | LOOP_COMPUTE_NOT_MATCHED | FOUND：1 vs 8 循环计算量不同 |
| P1 | TRAIN_CHECKPOINT_RNG | FOUND：Checkpoint 不保存随机数状态 |
| P1 | ROPE_BUFFER_CODE_AUDIT | FOUND：复数 RoPE buffer 源码存在 |
| P1 | ACT_FP32_PROMOTION | FOUND：ACT 累计包含 FP32 路径 |
| INFO | FIXED_TRAIN_STEPS | FOUND：上游训练步数配置 |

**这些模式 FOUND 仅表示具体源码证据存在，不等同每项都已在真实 GPU 上触发的动态故障。** 审计输出明确：`Actual GPU PR run: NOT_PERFORMED`。

## 2. 已动态验证的核心问题：丢失 complex64 的 RoPE 相位

用户 PyTorch `2.14.1+cu130`、CPU Tiny OpenMythos：

| Buffer | 转换前虚部最大绝对值 | `model.to(dtype=torch.bfloat16)` 后 | `phase_information_lost` |
|---|---:|---|---|
| `freqs_cis` | 1.0 | `torch.bfloat16`，实数 | **True** |
| `freqs_cis_mla` | 0.99999 | `torch.bfloat16`，实数 | **True** |

同时独立 4 元素 PyTorch 最小复现：`complex before=True; after=False`。因此对这份上游代码而言，PR27 整模型 `.to(device='cuda', dtype=torch.bfloat16)` 的**复数 RoPE 相位丢失风险是真实数值错误**，不是未经验证的猜测。源文件没有修改，模型训练没有执行。

这里不能将复数 Buffer 转成实数之后再 `.to(torch.complex64)` 当作修复，因为原虚部已经不可逆地丢失。修复应在**转换之前**保留复数缓存，最保守的研究候选是保留 FP32 主参数、complex64 RoPE buffers，计算中使用 `torch.autocast(..., dtype=torch.bfloat16)` 并防止 FP32 causal mask 污染 BF16 Attention。

## 3. R2 Gate C：研究层 BF16 候选（提交未运行）

我们新增独立 [r2_bf16_autocast_candidate.py](../scripts/r2_bf16_autocast_candidate.py) 及 [CPU 单元测试](../tests/test_r2_bf16_autocast_candidate.py)，不修改 `open_mythos/main.py` 或 PR27 源码。测试同一微型 GQA/MLA 模型 FP32 与 BF16 autocast full-sequence forward，确认 logits/loss 有限、梯度非零且有限、master params 始终 FP32，以及 `freqs_cis`/`freqs_cis_mla` 的 **complex64 相位逐元素精确保留**。因已知 FP32 mask 会把 BF16 Attention score 提升 dtype、导致某些 matmul 失败，在研究层临时只覆写全序列因果 mask dtype 成 BF16，运行结束强制恢复。

**限制：此方案只用于无 KV Cache 的全序列 tiny smoke；并非正式 PR27 整模型 BF16 修复，不代表 FlashAttention、GPU BF16、完整 ACT 精度、长上下文和 118M 混合精度训练已经验证。** 新增脚本仍需用户 Codespaces 实际运行和审阅结果；不预先报告 PASS。

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_bf16_autocast_candidate.py \
  --repo . --device cpu --attentions gqa mla
```

成功时写入 `research/mini_mythos/results/r2/bf16_autocast_candidate.json`，原始报告在本地结果目录（Git ignore），以用户终端输出作为后续通过证据。

## 4. 验收与放大门槛

Gate B 的**固定上游审计 PASS**；**R2 RoPE BF16 相位损坏已证实**；但由于原版受损，**PR27 大模型 GPU 训练依旧 BLOCKED**。Gate C 候选可先证实保留相位并进行有限 BF16 CPU 前反向，随后必须处理 P0 的 tokenizer pin、一致性、数据/恢复游标、独立验证，才可以申请或启动 GPU Smoke。无真实 GPU 时不要运行 PR27 `run_all.sh`。
