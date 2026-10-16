# R2 — OpenMythos 上游优先的规模化准备审计

**创建：2026-10-16。阶段状态：R1 Gate F 一次性独立 test 已通过；本 R2 文档和脚本已提交，但当前 Codespaces 硬件预检尚未运行。**

## 1. 从何开始，而不是重造基础模型

本项目的目标是以现有 `kyegomez/OpenMythos` 作为**社区假设性复刻候选**：复现上游公开实现、验证其真实语言能力、找到经过证据支持的改进，而不是继续无限优化 dim48 CPU 微模型或无依据宣称获取 Anthropic Mythos 真实权重。

目前 GitHub fork `leotree2020/OpenMythos` 的 `mini-mythos-research` 分支已经完成 R0 Cache 缺陷隔离复现、GQA/MLA tiny 训练恢复检查、WikiText-2 真正训练、固定测试 Split 的字节级 PPL 对照。实测 Gate F：**106/106 tests PASS**、锁定 step600 Tiny GQA，在 16,384 个独立 Test 目标字节的 PPL **10.852968**，优于同暴露量 Add-1 Bigram **12.790071**；但仍无法连贯生成文本，且只测了固定平滑策略的简单 n-gram 基线。详见 [Gate F 归档](R1_GATE_F_RESULT.md)。

## 2. 上游代码复用候选（优先级最高）

| 候选 | 上游线索 | 我们的处理策略 |
|---|---|---|
| 正式 OpenMythos 架构 | `open_mythos/main.py`，`open_mythos/variants.py` | 沿用 Prelude / Recurrent / Coda、MoE、GQA/MLA 等现有代码；不自行从零写 Transformer。先静态分析与硬件 smoke，再决定最小修复 |
| **约 117.8M 参数真实文本训练先例** | [上游 PR #27](https://github.com/kyegomez/OpenMythos/pull/27)（`experiments/` 目录方案，MLA+MoE，FineWeb-Edu，带 loop-depth 对照） | 首选复现入口，但它是 PR 中的社区提供方案/声称，**不是当前 fork 已合并且跑通过的实验**。必须获取、固定源码 revision，检查许可证、依赖、数据顺序、tokenizer/评估对应，再在授权 GPU 上重复 smoke |
| BF16 混合精度缺陷 | [上游 PR #26](https://github.com/kyegomez/OpenMythos/pull/26) | 对照当前 branch dtype 源码，检查是否仍需修复 ACT accumulation / attention mask 与 Linear 的 dtype 兼容；必须真实 BF16 GPU forward+backward 检查，不可仅凭 PR 声明 |
| 3B 正式 FineWeb-Edu 脚本 | `training/3b_fine_web_edu.py` | **只作训练链路参考和已知问题审计**；当前内建 `mythos_3b()` 不适合作为首次未知 GPU 训练任务 |
| 正式 tokenizer | `open_mythos/tokenizer.py`（`openai/gpt-oss-20b` 适配器） | 固定 tokenizer id+不可变 revision+词表 SHA、special token、embedding vocab 严格一致；禁止在评估时替换 Tokenizer 且不审查 token ID |
| 训练数据 | `HuggingFaceFW/fineweb-edu` 或经授权的其他公开语料 | 固定数据 revision、许可、文档/样本顺序，训练与 Heldout/Test 明确隔离，支持可恢复 streaming cursor / RNG |

**上游 PR #27 的公开评审曾指出**，其 `evaluate.py` 允许使用与训练不同的 tokenizer，从而导致 embedding ID 不一致或失真 PPL；不能在未修复验证前把其结果视为证明。PR 所述 H100/A100 时间和模型损失属于提交者自报，不能当作本项目的性能保障。建议先在一个新的实验分支/隔离目录取得其真实源码及 Commit SHA，不修改 R1 已封存的基线和原始 `open_mythos/main.py`。

## 3. 当前 fork 的源码 Gate — 在 GPU 前必须检查

以下基于当前 `mini-mythos-research` 的已审源码与先前 R0 结果，是**审计待办**而非本回合已复现的大 GPU 故障：

| 严重度 | 问题 | 当前证据 | GPU Pilot 入场要求 |
|---|---|---|---|
| P0 | **正式 tokenizer 一致性** | `MythosTokenizer` 外部加载 `openai/gpt-oss-20b`，未直接固定不可变 revision | 训练/恢复/验证完全一致，记录 revision/hash/词表大小及特殊 token ID |
| P0 | **预训练脚本缺少严格独立验证与数据游标恢复** | `training/3b_fine_web_edu.py` 采用 Streaming dataset，旧脚本描述重启分片流为可接受；无已验证独立 Heldout PPL | 真实 Train/Validation/Test 分离、可重播数据位置和随机状态、断点续训结果验证 |
| P1 | **GPU BF16/FP16 计算 dtype** | [PR #26](https://github.com/kyegomez/OpenMythos/pull/26) 提出 dtype-promotion 问题；分支 mask dtype 已有修正，但 ACT 累积仍需核实 | 在实际设备上完成所选精度 forward/backward、有限 loss/grads、optimizer step 及 checkpoint round-trip |
| P1 | **多 Token 缓存分块** | 本 fork R0 复现 GQA/MLA 原始 8 vs 2 mask 错误，研究层暂时性修正已在 CPU tiny 通过 | 保留不变源代码的 GPU 评估风险提示；如需 batched chunk inference，必须单独审查、正式修复并用缓存对照测试覆盖 |
| P1 | **MoE 专家路由的负载均衡** | top-k routed/shared expert 与 bias 存在，但正式训练脚本没确认动态 bias/aux-loss 策略 | 记录 per-expert token counts、load CV、dead experts、router grads 和分布，禁止仅以 MoE 开启判断路由健康 |
| P1 | **训练成本误估** | 递归模块共享权重，不意味着每 token 只做一次 block FLOPs；ACT 在部分场景继续计算全 token | 在相同实测 token、loop 次数、FLOPs/GPU 秒以及可训练参数条件下与简单 Transformer 对照 |
| P2 | **checkpoint 安全** | 正式 3B 脚本 `weights_only=False` 反序列化 cfg | 外部 checkpoint 禁止不可信 pickle；项目内部使用 tensor/primitive-only + 安全读取，并记录哈希 |

## 4. 先实际盘点算力，再决定参数规模

新增 [r2_preflight.py](../scripts/r2_preflight.py) **只读工具**：记录当前 Git commit、源码 SHA256、Python/PyTorch 和数据组件版本、CUDA 设备数量/显存、BF16 是否支持、工作区空余存储和前述静态差距标记。**它不会下载权重、创建 GPU 模型实例或启动训练。**

运行：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_preflight.py --repo . \
  --out research/mini_mythos/results/r2/preflight.json
```

若检测不到本地 CUDA GPU，这**并不阻止 GitHub Codespaces 浏览器开发**，只说明现有容器不能直接执行所计划的 GPU 预训练；需经用户授权的 GPU 执行环境。不要求在公司 PC 本地安装任何软件。

### 单卡训练状态的量级估算（非实际峰值）

| 假设参数量 | 16 字节/参数的训练状态 GiB | 20 字节/参数的演示 GiB |
|---|---:|---:|
| 120M | 1.79 | 2.24 |
| 200M | 2.98 | 3.73 |
| 1B | 14.90 | 18.63 |

**这些数字绝对不是所需 GPU 显存报价或承诺。** 它们仅代表 BF16 参数/梯度、可能的 FP32 主权重、AdamW 动量的理想化量级；未计激活、每层 Attention、recurrent loop、MoE 路由、CUDA 内核临时工作区、显存碎片化、checkpoint staging、数据缓存、推理验证等。真实显存须从逐次 smoke 的 `torch.cuda.max_memory_allocated()` 获得；算力预算需记录实测 tokens/s、每步耗时、预算 GPU 小时/费用。

## 5. R2 首次可验证里程碑（批准 GPU 之前）

1. **源代码和版本**：审查 PR #27/26/15 与 fork 的具体差异。对待引入方案形成 SHA 和 provenance 文档；不要无验证地 merge。
2. **训练配置**：候选 100–200M MLA+MoE，正式 pinned tokenizer 和数据文档边界；记录唯一参数量、active parameters/experts per token 和实测 FLOPs。允许根据可用显存降低规模，但不得用模型名称代替真实参数计数。
3. **GPU smoke**：同一测试 batch 前向/反向、实际专家路由负载、bf16 梯度稳定性、Checkpoint resume，10–100 steps 并独立 Heldout PPL。
4. **可比较基线**：非递归 Transformer，以同训练数据 tokenizer、同预算训练 token 及 GPU 时间做公平对比；不能只比较一方 8 loops、一方 1 loop 的表面步数。
5. **放大门槛**：只有 GPU smoke、输入许可、Checkpoint 数据恢复、预算和独立 Heldout 均通过，才考虑完整 100M+ 预训练。

## 6. 用户 Codespaces 的下一条命令

先运行 `r2_preflight.py`，发回其中 GPU 是否可用、GPU 型号与 VRAM、PyTorch 版本、静态差距列表即可。**不要在本阶段运行 `training/3b_fine_web_edu.py`；它不是已经验证过的 100M GPU Pilot。**

补充：本项目的 R1 Gate F 是真正验证小模型字节级预测的可信终点，但**还不具备与 Claude Mythos 黑箱行为比较的语言能力**。后续验收必须包括文本生成、任务能力与高质量多个独立测试集，而不仅是字节级 PPL。
