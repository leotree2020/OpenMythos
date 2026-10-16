# R1 Gate E — 扩展验证窗口与配对统计测试

**2026-10-16；实验已在 Codespaces 完成，97/97 tests PASS；结果详见 [Gate E Result](R1_GATE_E_RESULT.md)。** R1 Gate D 已在真实 WikiText-2 validation 的 16 个各 64 字节窗口上得到 600-step PPL 11.219663，优于 matched Add-1 Bigram 13.021447；依然 Greedy 重复 `the`，不能声称是有实际语言能力的 Mythos。

## 目标

保持 600-step Checkpoint、训练语料、模型架构、Tokenizer、seed、n-gram Add-1 smoothing、验证数据划分完全不变，仅将确定性验证窗口从**16 个扩展到 128 个**（每窗 64 个目标 byte-token，计分 **8192 个目标**，不足则自动以实际可用窗口数计）。这一步既不会微调权重，也不触碰真实模型源码，不会覆盖既有 `report.json`/`diagnostics.json`/`exposure_baselines.json`。

在相同 128 个验证窗口上测量：神经模型、与 SGD 看过的字节对精确匹配的 Unigram/Bigram、训练前缀完整统计的 Bigram。对每一个窗口记录相同目标上的 byte-level NLL，计算 Bigram − Model 的 paired NLL 差：**正数意味着模型更好**。生成以窗口为重采样单位的探索性 bootstrap 95% 区间（固定随机种子、2000 次），以及模型获胜的窗口比例。

这些窗口仍来自已经多次使用的 **validation** 数据，不是完全未见过的官方 Test Set。Bootstrap 也可能受同一文档的相关窗口影响而过于乐观，不能作模型已证明达到某种显著水平的声明。

## Codespaces 运行命令

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v

python research/mini_mythos/scripts/r1_gate_e_validation.py \
  --repo . \
  --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step600 \
  --eval-windows 128 \
  --out research/mini_mythos/results/r1/gate_e_validation_128.json
```

必须看到 `Checkpoint step: 600`、`Offset RNG matches checkpoint: True`、窗口数/目标字节、四类模型 NLL/PPL 及 paired 区间。脚本拒绝覆盖已有输出；若该输出已存在，请指定新文件名而不是删除历史结果。

## 判定与接续路线

- 如果配对比较仍显示模型在大多数窗口和整体平均 NLL 上低于 matched Bigram：将这当作**真实且有限的字符级上下文建模证据**；不再消耗 CPU 继续训练这只 dim48 的模型。下一项是**上游优先**的 Tokenizer/训练代码审查，规划 100M+ GPU Pilot 和公平 Transformer 对照。
- 如果 128-window 优势消失、置信区间含零或模型只在少数窗口获益：Gate D 的 16-window 胜出视为有样本敏感性的探索性发现；不要改验证规则选择更好结果，也不要因此立刻修改 ACT，先对模型评估流程和扩展数据规模进行审计。
- 无论哪种结果，都不能将社区 OpenMythos 的 Prelude→Recurrent→Coda 等实现当作 Anthropic Mythos 的已证实内部架构。复刻架构真实性必须依赖独立公开证据。

### 已知限制

- 固定 Add-1 unigram/bigram 不是独立调参的最强 n-gram；今后应在训练集内部留出开发集调 smoothing，并在一次锁定后用**从未用于实验选择的 WikiText Test Set**进行确认。
- 只测试 600-step GQA tiny byte model，未训练 MLA、MoE 的大规模语言权重，尚无可比的 Transformer 真实预算基线。
- 差值单位是 **nats / byte-token**，不能和不同 Tokenizer 的 Token PPL 直接比较。

[Gate D 实测结果](R1_GATE_D_RESULT.md) | [新实验脚本](../scripts/r1_gate_e_validation.py) | [离线单元测试](../tests/test_r1_gate_e_validation.py)
