# R1 Gate E — 128 窗口扩大验证结果（已实测）

**2026-10-16 用户 Codespaces 日志确认**：97/97 单元测试 PASS（4.160 秒）；冻结的 600-step Tiny GQA Checkpoint 在更广泛的 WikiText-2 validation 上接受 128 个确定性窗口、8192 个 next-byte 目标的评估。此文档依据用户贴出的控制台输出；原始 `gate_e_validation_128.json` 在用户 Codespaces 的 Git 忽略目录，不声称已独立下载核对。

## 运行证据

- `Checkpoint step: 600`；RNG replay matched：`True`。
- `Observed supervised tokens: 153600`：是累计**包含重叠与重复**的监督目标位置，不是独立训练字节数。
- `Heldout evaluation windows: 128`，`Heldout target bytes: 8192`。
- 相同上下文窗口、相同计分目标、相同 byte tokenizer、相同 Add-1 smoothing，比较冻结权重与统计预测器。

| 方法 | NLL / byte-token ↓ | PPL ↓ |
|---|---:|---:|
| **600-step OpenMythos GQA** | **2.455182** | **11.648557** |
| 相同训练样本暴露量 Unigram | 3.212680 | 24.845576 |
| 相同训练样本暴露量 Bigram | 2.596538 | 13.417210 |
| 整个训练前缀 Bigram | 2.563204 | 12.977333 |

相较 matched Bigram，模型 PPL 低 **约 13.2%**，在 128 个窗口中有 **121 个窗口**平均 NLL 更低（胜率 94.53125%）。模型与 matched Bigram 的配对优势（Bigram − Model）是 **+0.14135590267533218 nats/byte**。固定种子、窗口重采样 2000 次的**探索性** Bootstrap 区间 `[0.12528083279945096, 0.15789727883428692]`，区间下界高于零。模型逐位置 greedy 预测空格比例 **0.341796875**。

## 研究解释及边界

这加强了 Gate D 的结论：社区 OpenMythos 的微型 recurrent 模型已经在**真实英语 byte-level 预测**中表现出优于已固定 Add-1 Unigram/Bigram 的数据拟合能力，且 128 个等长窗口下优势不是少数窗口造成。但:

- 这是**反复查看过的 validation split**：我们用同一划分指导了训练预算与实验设计，可能存在选择偏差，不能替代一次锁定的官方 test split。
- 相邻窗口虽不重叠，但语料来源段落仍可能相关；Bootstrap 区间不等于严格独立样本的确认性显著性保证。
- 统计基线只是固定 Add-1 smoothing，不能当作所有可优化 N-gram 模型的能力上限；神经网络和 N-gram 的参数数目、训练计算量也未对齐。
- 依然未实现通顺自由生成：此前三条提示词 Greedy 都陷入 `the the the ...`。单看字节 PPL 不能声称拥有推理、代码生成、长上下文能力。
- 模型架构是开源社区的假设性复刻，不是 Anthropic 内部网络结构的已证事实。

## R1 Gate E 闸门决定：通过，冻结权重

Gate E 从 1,024 字节扩展到 8,192 字节后，优势得以保持：**工程验证 PASS、固定字节统计基线对照 PASS、自由语言生成尚未达标**。

下一步严格执行 [Gate F：一次性官方 WikiText-2 test split 评估](R1_GATE_F_PLAN.md)，**不修改 600-step 模型权重或评估规则**。在测试前冻结 revision pin、前 1200 个合格 test 文本、只读取前 250,000 字节、256 × 64 个固定位置的下一字节预测、原始训练看到的数据对、Add-1 Bigram。后续转向正式 Tokenizer 和 100M+ 级 GPU 训练，避免在 dim48 toy 上继续追逐 validation PPL。

本地结果：`research/mini_mythos/results/r1/gate_e_validation_128.json`。新 GitHub 文档是控制台实测结论的文字归档，不是该本地结果文件或模型权重的上传。
