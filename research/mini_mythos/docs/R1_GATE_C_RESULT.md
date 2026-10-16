# R1 Gate C — 200 步续训与下一轮公平性控制

**日期：2026-10-16。状态：200-step GQA 续训及 Gate B 诊断已经在用户 Codespaces 执行，基于终端日志。** Git 忽略的 Checkpoint、数据文件和本地 JSON 尚未独立下载检查。

## 本次实验

- 从原有 60-step Checkpoint 拷贝成 `results/r1/pilot_gqa_step200` 后使用 `--resume`，日志确认 `Resumed from step 60`。
- 保持相同架构：tiny GQA，depth=2，seq_len=64，batch_size=4，byte tokenizer 257 类，WikiText-2 本地 train/validation，种子/超参数与原实验一致。
- 续训到 step=200（累计优化步数 200），默认学习率与数据前缀上限不变，训练目标位置累计 `200 × 4 × 64 = 51200`，**不是唯一训练 token 数**。
- Checkpoint 保存于 `results/r1/pilot_gqa_step200/latest.pt`；训练结果 `report.json`；只读诊断 `diagnostics.json`。

## 60 vs 200 steps：同一验证窗与统计基线

| 指标 | Step 60 | Step 200 | 说明 |
|---|---:|---:|---|
| Heldout NLL ↓ | 3.3763458525 | **3.2255321092** | 下降 0.150814 |
| Heldout PPL ↓ | 29.2636418 | **25.1669622** | 相对下降约 14.0% |
| Full-corpus Unigram PPL ↓ | 26.9194197 | 26.9194197 | Step 200 略优于该基线 |
| Full-corpus Bigram PPL ↓ | **12.5971717** | **12.5971717** | 模型仍远落后 |
| Model nonspace NLL ↓ | 3.7231267 | **3.5756126** | 对非空格目标也有所改善 |
| 预测空格比例 | 100% | 100% | Greedy 严重塌缩仍存在 |
| Reverse-history Δ NLL | 3.576e-7 | **0.00494069** | 历史顺序扰动导致的目标 NLL 改变增强 |
| Reverse-history mean TV | 2.172e-5 | **0.00244942** | 约为 60 steps 的 113 倍 |

注意：上面 Unigram/Bigram 是用**整个当前训练语料前缀**估计的（训练代码默认读约 250000 bytes），而模型 200 步仅看到**51200 次带重复抽样的 next-byte 监督位置**，暴露数据量与训练方式不同；PPL 比较是预测性能标尺，**不是公平同样本预算的机制优劣证据**。

## 生成实测

- Teacher-forced 验证目标空格约 `0.1943359375`，模型所有位置 argmax 仍预测空格。
- Greedy 的三个提示词都是 64 个空格，说明连续生成退化尚未解决。
- 固定采样温度 0.9 / top-k 32 / seed=91 的三条输出现在有少量差别，但仍是无连贯语义的字符流。
- Reverse-history 只交换了过去 63 字节的顺序、保持最后输入和目标不变；TV 增大说明模型对**这类输入改变**的敏感性升高，不足以证明有意义地理解上下文，也不是完整的 causal attribution。

## Gate C 结论

**H1（训练严重不足）获得支持：随着训练步数增长，Heldout NLL 下降、非空格 NLL 下降、历史顺序敏感性增大。** 但仅凭这组 60/200 步对比，无法排除 H2（模型容量、架构、训练机制或 tokenizer 限制）；尤其 Greedy 仍百分之百选择空格，且远落后 Bigram。

## 下一项实验：精确复现相同 SGD 数据暴露量的 n-gram 对照

新增脚本 `research/mini_mythos/scripts/r1_exposure_baselines.py`：

1. 从真实 Checkpoint 和训练报告加载 seed、batch size、seq len、steps、数据 SHA。
2. 按 `r1_text_pilot.py` 的独立 `torch.Generator(seed + 17)` 严格重放每次 SGD batch 的**随机 offset**。
3. 将重放后的 Generator state 和 Checkpoint 的 `offset_rng_state` **逐字节比较**；不一致直接报错，不能继续声称同数据暴露。
4. 只在模型实际看到的 `(previous byte, next byte)` 监督样本上估计 Add-1 Unigram/Bigram；重复训练位置按实际重复次数计数。
5. 在同一 16 个 Heldout windows 上计算 NLL/PPL，同时保留旧版 full-corpus n-gram 作为参考。

这仅匹配 n-gram 的**训练样本身份与暴露次数**，不匹配模型容量、计算量或优化目标，因此是比原有基线更可解释的控制，但仍不是完整公平架构对比。

### Codespaces 命令（新脚本尚待运行）

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v

python research/mini_mythos/scripts/r1_exposure_baselines.py \
  --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa \
  --eval-windows 16

python research/mini_mythos/scripts/r1_exposure_baselines.py \
  --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step200 \
  --eval-windows 16
```

输出：各实验目录内 `exposure_baselines.json`。如果状态匹配检查 FAIL，保留错误证据并检查数据 / RNG 重放，不要手动调整统计值。

### 后续决定

分析 60/200 步的 matched n-gram 结果后再考虑续训到 600 步，或尽快构建更加合适的正式 Tokenizer 与 100M+ GPU Pilot。在目前证据下，不能宣称已经复刻了 Anthropic Mythos。
