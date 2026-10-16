# R1 第一阶段：真实文本训练 Pilot

日期：2026-10-16。状态：**GQA CPU Pilot 已在用户 Codespaces 完成真实文本训练（60 steps）、保存 Checkpoint，并报告 Heldout PPL 29.264。** 原始 Checkpoint/JSON 文件尚未独立取回验证。参见 [R1 Gate A 结果](R1_GATE_A_RESULT.md)。

## 目标与证据界限

R0 已确认 GQA/MLA 的多 Token KV Cache 掩码缺陷与独立修正方案；现在停止随机合成数据上的 ACT 局部优化，进入真实语言模型训练验证。

本 Pilot 使用 **未修改的 OpenMythos 上游模型**，在真实英语 WikiText-2 文本上完成训练、保留验证集、生成输出并保存**可安全加载**的 Checkpoint。

**刻意采用 257 符号的 UTF-8 byte tokenizer**（0..255 byte + EOS=256），以避免下载、版本漂移及巨大词表导致 CPU Pilot 受阻。它是工程可行性验证，不是 Claude Mythos 的推测 tokenizer，也不用于声称接近 Anthropic 模型的真实语言水平。将来需要固定适当的生产 tokenizer 和数据链路，并借助 GPU 扩展训练。

## 输入准备：真实数据，严格 train / validation 分离

首选：`Salesforce/wikitext` 的 `wikitext-2-raw-v1` 配置，分别取 train 和 validation split 中确定顺序的部分非空文本。

```bash
git pull --ff-only origin mini-mythos-research

python -m unittest discover \
  -s research/mini_mythos/tests \
  -p 'test_*.py' -v

python research/mini_mythos/scripts/r1_prepare_wikitext.py \
  --repo . \
  --revision main \
  --train-docs 2000 \
  --validation-docs 300
```

**复现要求：** Hugging Face `main` 分支是可变引用；首次下载时会记录实际文本 SHA-256。需要严格复跑时，把 `--revision` 替换为 Hugging Face dataset 仓库的**不可变 commit SHA**；并保留 `data/manifest.json` 和数据内容散列。不同数据版本不可直接比较 PPL。

输出位于 Git 忽略的：
- `research/mini_mythos/results/r1/data/train.txt`
- `research/mini_mythos/results/r1/data/validation.txt`
- `research/mini_mythos/results/r1/data/manifest.json`

如果无法联网，也可以把**授权使用、许可证允许**且来源明确的 UTF-8 纯文本分别保存为 train/validation 文件，直接运行下面的训练命令。两套文件不能完全相同，必须检查跨 split 重复内容和数据泄漏。

## 运行 GQA CPU 最小训练

```bash
python research/mini_mythos/scripts/r1_text_pilot.py \
  --repo . \
  --train-text research/mini_mythos/results/r1/data/train.txt \
  --validation-text research/mini_mythos/results/r1/data/validation.txt \
  --attention gqa \
  --depth 2 \
  --seq-len 64 \
  --batch-size 4 \
  --steps 60 \
  --eval-windows 16 \
  --out-dir research/mini_mythos/results/r1/pilot_gqa
```

查看：
- `research/mini_mythos/results/r1/pilot_gqa/report.json`：起始和最终 heldout NLL/PPL、样例生成、参数数目、使用的文档 SHA。
- `research/mini_mythos/results/r1/pilot_gqa/latest.pt`：tensor/primitive-only PyTorch Checkpoint，使用 `weights_only=True` 恢复。
- `PPL = exp(heldout_token_NLL)`，越低越好；报告 Heldout 字节 Token 数量与独立窗口数量。由于 tokenizer 是 byte-level，**不能把这里的 PPL 与不同 tokenizer 的模型 PPL 直接比较**。

可选 MLA 配置（保存到不同目录）：

```bash
python research/mini_mythos/scripts/r1_text_pilot.py \
  --repo . \
  --train-text research/mini_mythos/results/r1/data/train.txt \
  --validation-text research/mini_mythos/results/r1/data/validation.txt \
  --attention mla --depth 2 --seq-len 64 \
  --batch-size 4 --steps 60 --eval-windows 16 \
  --out-dir research/mini_mythos/results/r1/pilot_mla
```

如需将已训练 60 step 的相同实验继续到 100 step，执行同一条命令但将 `--steps 100` 并追加 `--resume`。恢复时会校验模型配置、训练超参数、Tokenizer 标识和数据 SHA；训练随机窗口的 RNG 状态也随 Checkpoint 一并恢复。

### 快速 Smoke

预先准备两份 UTF-8 文本后：

```bash
python research/mini_mythos/scripts/r1_text_pilot.py \
  --repo . \
  --train-text research/mini_mythos/results/r1/data/train.txt \
  --validation-text research/mini_mythos/results/r1/data/validation.txt \
  --attention gqa --steps 2 --seq-len 32 \
  --batch-size 2 --eval-windows 2 --generate-tokens 3 \
  --out-dir research/mini_mythos/results/r1/smoke_gqa
```

不要把 smoke 的结果当语言能力验证。

## 对 R0 风险的处理与剩余工作

本 R1 Pilot **只验证**真实文本训练的最小链路，不直接修补上游生产 `training/3b_fine_web_edu.py`。这使得训练失败/成功具有清晰的解释边界。

| 项目 | 本阶段 | 下一阶段 |
|---|---|---|
| 训练数据 | 明确区分 HF train/validation 或两份独立本地文件，记录 SHA | 数据许可证/去重/持久化不可变修订版本 |
| Tokenizer | 固定算法的 UTF8 字节编码 | 选择正式 tokenizer 并固定完整 revision/hash |
| Checkpoint | 模型 + AdamW + 随机数状态，原子写入，安全加载 | 生产训练脚本数据迭代器位置与多 GPU/FSDP 恢复 |
| 评估 | 独立 holdout NLL/PPL 和 sample | 标准语言/代码/推理基准，模型行为对齐 |
| KV Cache | 生成使用无缓存全上下文 forward，绕开已知多 token chunk 缺陷 | 原版正确性修复及 GPU FlashAttention 路径检验 |
| 算力 | CPU Tiny；随机初始化开始训练 | GPU 100M+ 参数实际模型、训练 token/FLOPs 匹配 |
| Mythos 真实性 | 使用社区推测的架构 | 公开证据矩阵和有条件的黑箱行为比较 |

最后的判定要求：**实际 Codespaces 运行 PASS、持久化 Checkpoint 可加载、真实 Heldout PPL 可重算、生成输出可复查**。代码提交本身不满足这一关卡。

## Gate B：已训练 Checkpoint 的诊断对照

首轮成功训练后，`The ` 后续 24 个 Token 全是空格。为了区分真实上下文学习和字节频率拟合，现在使用 [r1_language_diagnostics.py](../scripts/r1_language_diagnostics.py) 在**完全相同的验证窗口**计算模型相对于 train-fitted 平滑 Unigram/Bigram、均匀随机基线的 NLL，分别测量空格及非空格目标上的 Loss，并分别显示 greedy 和固定种子的 top-k sampling 文本。执行：

```bash
python research/mini_mythos/scripts/r1_language_diagnostics.py \
  --repo . \
  --pilot-dir research/mini_mythos/results/r1/pilot_gqa \
  --eval-windows 16 --generated-bytes 64
```

诊断只读取本地 Checkpoint 和语料，不执行训练或修改上游架构；会校验训练数据完整 SHA、模型配置、训练步数及已有报告的 Heldout NLL，再生成 `diagnostics.json`。增加 7 项独立离线测试。该新代码尚待 Codespaces 运行。
