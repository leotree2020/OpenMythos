# R1 Gate D — 600 步受控训练与闭环验收

**日期：2026-10-16；状态：准备完成，600-step 尚未执行。** Gate C 86/86 tests PASS；60/200 checkpoint 的 RNG 恢复重放均匹配、15,360 / 51,200 个监督目标。当前模型 200-step heldout PPL=25.166962，matched unigram=26.951090，matched bigram=14.811675；argmax 全空格。详见 [Gate C 结果](R1_GATE_C_RESULT.md)。

## 为什么只追加一次到 600 steps

观察 60→200 步，Heldout PPL、nonspace NLL、历史顺序 TV 改善，但预测仍塌缩；要用**唯一变化为训练步数**的实验判断这种趋势会否转化为更好的上下文预测，而非改动 ACT 权重或假设 OpenMythos 架构有错。600 steps 是本轮 Tiny CPU 实验的截止点，不会自动继续提高到 1000/2000 steps。

## Codespaces：保留前两份证据，复制到 600 步独立目录

先验证 Git 同步并测试（不要重复执行复制，如果目标目录已存在）：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v

test -f research/mini_mythos/results/r1/pilot_gqa_step200/latest.pt
test ! -e research/mini_mythos/results/r1/pilot_gqa_step600
cp -a research/mini_mythos/results/r1/pilot_gqa_step200 \
  research/mini_mythos/results/r1/pilot_gqa_step600
```

训练：

```bash
python research/mini_mythos/scripts/r1_text_pilot.py \
  --repo . \
  --train-text research/mini_mythos/results/r1/data/train.txt \
  --validation-text research/mini_mythos/results/r1/data/validation.txt \
  --attention gqa --depth 2 --seq-len 64 --batch-size 4 \
  --steps 600 --eval-windows 16 --resume \
  --out-dir research/mini_mythos/results/r1/pilot_gqa_step600
```

**验证重要约束**：打印 `Resumed from step 200`（不是从 0/60 开始）；配置、seed、learning rate 与原本一致；`--steps 600` 是累计 optimizer steps 而不是额外 600 步。训练目标字节位置累计 `600×4×64=153,600` 次，允许随机窗口重复，不能解读成唯一语料大小。

训练结束后执行诊断及精确暴露基线（只读，不改权重）：

```bash
python research/mini_mythos/scripts/r1_language_diagnostics.py \
  --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step600 \
  --eval-windows 16 --generated-bytes 64

python research/mini_mythos/scripts/r1_exposure_baselines.py \
  --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step600 \
  --eval-windows 16
```

最后运行 [r1_gate_d_compare.py](../scripts/r1_gate_d_compare.py) 自动审核 60/200/600 的完整继承链：

```bash
python research/mini_mythos/scripts/r1_gate_d_compare.py \
  --repo . \
  --pilot-dirs \
    research/mini_mythos/results/r1/pilot_gqa \
    research/mini_mythos/results/r1/pilot_gqa_step200 \
    research/mini_mythos/results/r1/pilot_gqa_step600
```

比较器会拒绝：Checkpoint steps 不递增、恢复来源不衔接、模型配置/Tokenizer/数据指纹漂移、评估 Token 数不同、诊断 NLL 与 Checkpoint 报告不一致、SGD offset RNG 重放未验证、暴露量计数不匹配。产物在 Git 忽略的 `research/mini_mythos/results/r1/gate_d_comparison.json`。

## Gate D 结束条件

| 条件 | 解读和后续路线 |
|---|---|
| 600 steps 仍全部预测空格，且未优于 matched Bigram | **停止继续延长当前 48 维 CPU Toy**。优先审计真实参数梯度、Attention 学习、模型容量、Tokenization；准备 GPU 正式实验 |
| 600 steps PPL 下降且历史 TV 上升，但生成仍无意义 | 有继续拟合的证据，**不是**语言能力通过；仍结束 Toy 长训，转向正式 Tokenizer 与可复现 GPU 训练 |
| 显著降低空格塌缩、超过 matched Bigram 且生成不再纯字符噪声 | 确认 Toy 已有基础语言建模能力，再验证多个 seeds、扩大 Heldout 和实际 Transformer 对照 |

以上都不是 Claude Mythos 的精确复刻证明。不能通过调整验证窗口、Tokenization 或高频空格处理来人为提高对照成绩。本阶段仍不修改上游 `open_mythos/main.py`。
