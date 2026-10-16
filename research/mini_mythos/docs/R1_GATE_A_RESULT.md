# R1 Gate A — WikiText-2 真实文本微模型训练结果

**2026-10-16；状态：用户 Codespaces 已运行，基于终端输出记录。** 源数据文件和 `report.json`、`latest.pt` 仍保存在用户的 Codespaces，本回合没有独立下载验证文件内容。

## 运行证据

- 项目分支：`mini-mythos-research`。
- 单元测试 **73/73 PASS**（3.458 秒）。
- `Salesforce/wikitext` / `wikitext-2-raw-v1`，数据引用 `main`（**可变引用，未固定 Hub commit SHA**）。
- 按既有准备脚本选取前若干符合长度要求的 train/validation 文档：
  - Train：2000 篇，995396 bytes，`4790992d8539e04893b3e066ff65f07750517d68484fd4cb28665c5e71b0fa8b`。
  - Validation：300 篇，120904 bytes，`3508547d6576f65c2ba10f0e3ca7ac23f1cd1a6593db45b65395d7aa60e32c1b`。
- **本训练 Pilot 并未消费以上全部字节**：按程序默认最多使用 train 文件前 **250000 bytes**，validation 文件前 **50000 bytes**；最终 Token 数因文档分隔符 EOS 可能与字节数略有差异。具体选择子集 SHA 需查看 `report.json`。
- GQA、Depth 2、序列长度 64、batch 4、60 optimizer steps、Heldout 16 windows × 64 targets = **1024 计分 Token**。
- Tokenizer：UTF-8 byte (0..255) + EOS=256，257 个符号；不是官方 Anthropic Tokenizer 或 OpenMythos 原型生产 Tokenizer。

## 实测指标

| 项目 | 初始 | 60 steps 后 |
|---|---:|---:|
| Heldout token NLL | 5.51615 | 3.37635 |
| Heldout byte-token PPL | 248.675 | 29.264 |
| Train loss | 未提供 | 3.27049（最后训练批次） |

中间训练批次 Loss：step10 4.94257、20 4.25003、30 3.76856、40 3.34718、50 3.13428、60 3.27049。它们来自**不同随机训练 batch**，不是同一固定验证集的曲线点；不能把局部上升简单判断为过拟合。

生成结果为 **24 个空格**（原终端：`Sample continuation: '                        '`）。这揭示了当前模型的文本生成退化现象。Heldout PPL 降低说明模型学到部分字节级统计结构，但 **不能说明学会有意义的连续语言、推理、编程，也不能据此声称“复刻了 Claude Mythos”。**

- Checkpoint：`research/mini_mythos/results/r1/pilot_gqa/latest.pt`。
- 报告：`research/mini_mythos/results/r1/pilot_gqa/report.json`。
- 数据清单：`research/mini_mythos/results/r1/data/manifest.json`。

这些产物仅有路径和终端报告；尚未在独立环境重载、逐项验证现有文件内容，也尚未确认所有生成场景表现。此前的单元测试中只验证了受控环境下的类似 checkpoint 保存/重载。

## 判定

**R1 Gate A：PASS（最小真实文本训练通路已实际跑通）。**

- 已证明：按指定数据划分可执行训练、记录验证 PPL、保存本地 checkpoint，以及输出生成字符串。
- 未证明：长上下文推理能力、真实语言流畅性、等价于官方 Mythos、生产 3B/FSDP 可恢复训练。
- 重要限制：单训练种子、60 steps、1024 验证目标 tokens、小模型和 byte tokenizer；PPL 不能跨 tokenizer 直接比较。

## R1 Gate B — 正确性与生成质量的下一项验证

仅检查 Loss 降低不足以支撑语言能力结论。现在用**训练集统计拟合的 smoothed unigram/bigram 基线**，在完全相同的验证 windows 上对照 checkpoint 的 NLL，记录**非空格目标 Token 的模型 NLL**、预测空格比例、greedy 最高概率分布，并使用固定随机种子的 sampling 观察多样性。诊断**不训练、也不更改现有 Checkpoint**。

执行：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r1_language_diagnostics.py \
  --repo . \
  --pilot-dir research/mini_mythos/results/r1/pilot_gqa \
  --eval-windows 16 --generated-bytes 64
```

输出 `research/mini_mythos/results/r1/pilot_gqa/diagnostics.json`。应先检查是否能**重载已有 checkpoint 并重新得到 NLL≈3.37635**，再比较 unigram/bigram，确认模型是否提供了超出简单字符频率的有效信息。生成质量若仍退化，应改进语料、模型规模、训练 token 预算与正式 tokenizer，再进行真实基准验证，而非直接修改 ACT 概率权重。

**该诊断代码已提交，但尚未在用户 Codespaces 执行，因此不能预先报告 baseline 比较结果。**
