# R1 Gate B — 训练后模型、字符统计基线与生成退化

**日期**：2026-10-16。**证据**：用户 Codespaces 终端输出，尚未独立下载 `diagnostics.json` 或 `latest.pt`。目的不是证明 Anthropic Mythos 架构，而是检验当前微型 OpenMythos 对真实文本的实际学习能力。

## 执行结果

命令：`python research/mini_mythos/scripts/r1_language_diagnostics.py --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa --eval-windows 16 --generated-bytes 64`。

- 单元测试共 **80 项**，其中 **79 PASS，1 ERROR**。报错位于 `test_r1_language_diagnostics.py::test_nll_perplexity_math`：测试使用不存在的 key `perplexity`，而真实 `metrics_from_sums` 返回 `ppl`；属于**单元测试字段拼写错误，已修复并提交**，不是训练/评估数学函数故障。修复后的测试尚待用户 Codespaces 复跑。
- 诊断程序本身运行成功，重载了已有 checkpoint、校验训练报告与源文件哈希、并在相同 validation windows 复现 Heldout NLL `3.376345852506347`，和首轮报告 `3.37635` 一致。
- 数据：WikiText-2 固定下载所得本地分割；train-fitted Unigram/Bigram 在 **相同 16 个窗口、1024 byte-token targets** 上评估。Tokenizer 为 UTF-8 byte + EOS（257 个符号）。

## NLL / PPL，越低越好

| 预测器 | Heldout NLL | Heldout PPL |
|---|---:|---:|
| Uniform | 5.54907608489522 | 257.00000000000006 |
| 当前 OpenMythos tiny GQA (depth=2, 60 train steps) | 3.376345852506347 | 29.26364183593556 |
| train-fitted smoothed Unigram | 3.292847949025204 | 26.91941972542853 |
| train-fitted smoothed Bigram | **2.533472320287023** | **12.597171697232753** |

当前模型的 NLL 比 Unigram 高约 0.0835，比 Bigram 高约 0.8429；**不能宣称已学到优于简单字节统计基线的语言预测能力**。训练前后 PPL 大幅下降是真的，但只与该模型的初始状态相比，不能说明优于统计基线。

## 生成与上下文

- `Model nonspace NLL`：`3.72312668800354`（排除目标空格）；尚无相同条件下 Unigram/Bigram 细分类别指标。
- 真实目标空格比例：`0.1943359375`；模型在 teacher-forced validation 位置上 **argmax 预测空格比例：1.0**。
- 对 `The `、`Once upon a time, `、`In the beginning, `，Greedy 均生成连续 64 个空格。
- 固定采样种子 `91`、top-k 32、温度 `0.9` 时，三个不同提示词输出**同一段 64 字节字符串**（空格占比 `0.203`）。由于每个提示词使用同一随机种子且输出分布可能很接近，**这一现象不能单独证明模型数学上忽略了历史上下文**。
- 真实 context-use 尚待控制实验；不能将 Greedy 的空格塌缩等同于严格的上下文不敏感。

## 研究结论

**R1 Gate B 当前性能判定：未超过 Unigram/Bigram 基线；生成出现极端空格塌缩。**

与此相区分，**工程通路**仍通过：能加载模型、生成、计算可复现的 validation NLL、对接训练数据。这是一次有价值的负结果，不是能证明 OpenMythos/Anthropic 递归架构不合理的实验。

限制：48 hidden-dim tiny model、60 optimizer steps（约 `60×4×64 = 15360` 训练 Token 位置）、单 seed、1024 validation targets、byte-level tokenizer。验证数据来自独立的 WikiText-2 validation split，但抽样很小，不能代表广泛文本能力。

## 修复与后续实验

本次已提交：
1. **测试字段修复**：`test_nll_perplexity_math` 中 `perplexity` 改为 `ppl`（保持诊断脚本 JSON 格式一致）。
2. **只读历史上下文顺序消融**：`r1_language_diagnostics.py` 新增 `context_order_probe`，每个窗口保留最后输入字节、目标、历史 Token 直方图与长度，仅反转之前的历史字节顺序。对比最后 Token logits 变化、概率总变差、argmax 切换和下一字节 NLL。它能观察**历史顺序敏感性**，但不能证明语义理解。
3. 两项 offline/mock 回归测试，分别确保只依赖最后输入字节的模型结果不变、依赖历史字节的模型能被探针检测。

Codespaces 运行：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r1_language_diagnostics.py \
  --repo . \
  --pilot-dir research/mini_mythos/results/r1/pilot_gqa \
  --eval-windows 16 \
  --generated-bytes 64
```

**预期**：测试错误解除、诊断仍复现既有 NLL/PPL，新增 `Reversed-context last-token delta NLL` 和 `Reversed-context mean probability TV`。结果仍需用户实际执行确认。诊断程序不会更新或覆盖已有 Checkpoint。

**下一研究优先级**：根据语境敏感性结果，决定是否进入更充足文本训练与更可信 Tokenizer 的架构复刻 Pilot；不再把 ACT 概率补全作为主线。
## Gate B 第二次验证 — 已通过（2026-10-16）

用户在 Codespaces 重新运行单元测试及只读诊断：

- **82/82 tests PASS**（3.920 秒），旧的测试字段名错误已消除。
- 已训练 60-step GQA Checkpoint 的 NLL 3.376345852506347、PPL 29.26364183593556，已重载复现。
- Unigram NLL 3.292847949025204、PPL 26.91941972542853；Bigram NLL 2.533472320287023、PPL 12.597171697232753。
- Model nonspace NLL 3.72312668800354；目标空格比例 0.1943359375，模型 argmax 预测空格比例 1.0。
- 三条提示词 greedy 继续生成 64 个空格，同采样种子的 top-k 输出是同一个乱序字节序列。
- **历史顺序消融**（16 个 heldout 窗口各一个最后目标位置，固定末尾输入字节及目标、历史字节直方图，反转前面的 63 个历史字节）：
  - reversed_minus_original_target_nll = 3.5762786865234375e-07
  - mean_probability_total_variation = 2.172332642658148e-05

**解释**：当前模型对这组历史字节的**顺序**改变几乎不敏感。这不能证明完全无视历史内容，也不能证明社区递归架构在合理规模下无效。当前训练仅 60 steps、约 15,360 个训练目标 Token 位置，重复抽样可能存在。R1 Gate B 工程正确性 PASS；语言模型能力门槛 FAIL（未超过相同 heldout windows 的 unigram/bigram 基线）。

## Gate C — 对现有架构进行控制性续训（方案，未执行）

为了区分训练步数严重不足与架构/训练实现问题，应先冻结原 60-step evidence，再以**完全相同的模型配置、随机种子、数据输入和 Tokenizer**续训到 200 步。目标是观察模型是否开始超过 Bigram 基线、减少空格塌缩，以及历史顺序敏感性是否上升。只能根据实际运行结果决定是否继续到 600 步。

以下命令保留原目录不变，复制 checkpoint 和结果后在单独目录续训；不修改核心 OpenMythos 代码：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
cp -a research/mini_mythos/results/r1/pilot_gqa research/mini_mythos/results/r1/pilot_gqa_step200
python research/mini_mythos/scripts/r1_text_pilot.py \
  --repo . \
  --train-text research/mini_mythos/results/r1/data/train.txt \
  --validation-text research/mini_mythos/results/r1/data/validation.txt \
  --attention gqa --depth 2 --seq-len 64 --batch-size 4 \
  --steps 200 --eval-windows 16 --resume \
  --out-dir research/mini_mythos/results/r1/pilot_gqa_step200
python research/mini_mythos/scripts/r1_language_diagnostics.py \
  --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step200 \
  --eval-windows 16 --generated-bytes 64
```

步数扩展不等于独立数据量扩展，验证目标仍仅 1,024 个字节。续训可能过拟合；每轮必须保留原数据 SHA、基线结果和新 Checkpoint。如果 200 步仍失败，不能单凭这个否定架构，也不能无限增加轮数；应检查注意力梯度、参数规模、数据分布及基线 Transformer。
