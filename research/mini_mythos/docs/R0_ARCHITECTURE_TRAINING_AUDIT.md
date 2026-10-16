# R0 — OpenMythos 架构与训练链路审计（第一轮）

> 2026-10-16 · 目标：使用**开源 OpenMythos 作为假设性实现**，构建可训练、可评估的独立 Mythos 候选模型。**并非证明该源码等同 Anthropic 内部模型。**

## 审计范围与验证级别

审计源码路径：
- \`open_mythos/main.py\` — 1085 行；源文件 blob SHA \`65b0fa829f5371d633d2c397bde5175aa73851b4\`。
- \`open_mythos/tokenizer.py\` — Tokenizer 适配。
- \`open_mythos/variants.py\` — 模型规模配置。
- \`training/3b_fine_web_edu.py\` — 552 行预训练脚本，blob SHA \`e980302c2079ef779d81459f2551ee79156f1294\`。
- \`pyproject.toml\` — 依赖。
- 已存在的 \`research/mini_mythos/scripts/smoke.py\`、\`static_audit.py\` 及 ACT-001–004 结果。

下文 **源码确定** = 直接读到实现；**设计风险** = 推断可能有问题，但需要实际实验验证；**未验证** = 无直接证据证明有效。以前 55 项通过的测试验证的是研究工具和微型模型的部分特性，**不能替代真实语言预训练、GPU/FSDP 训练和目标模型能力的证明**。

## 1. 架构审计矩阵

| 项目 | 源码定位 | 来源分类 | 初步结论 | R0 下一验证 |
|---|---|---|---|---|
| Prelude → Recurrent → Coda | \`main.py:926-1034\` | 社区代码 | 源码确定：模型包含三段结构、权重绑定嵌入/LM head | 一致性、参数计数、权重导出 |
| 共享递归 Transformer | \`main.py:809-891\` | 社区代码 | 源码确定：\`self.block\` 在递归迭代间复用 | 固定深度对照；更深训练的稳定性 |
| GQA + MLA | \`main.py:177-424\` | 社区代码 | 源码确定：两套 Attention 和各自 KV Cache | 多 token 缓存分块 vs 全序列严格对照 |
| MoE routed/shared experts | \`main.py:456-539\` | 社区代码 | 源码确定：top-K routed + shared experts | 专家路由分布/负载/梯度 |
| MoE 无辅助损失均衡 | \`main.py:479-515\` | 社区代码 | **设计风险**：\`router_bias\` 参与选择，但 3B 训练脚本未见相应动态更新机制 | 训练中记录各专家负载，确认策略实际生效 |
| Loop-index embedding + per-depth LoRA | \`main.py:541-626\` | 社区代码 | 源码确定：不同循环有编号信号、可训练 LoRA scale | 深度外推、已训练尺度范围外行为 |
| LTI input injection | \`main.py:684-749\` | 社区代码 | 源码确定：对角 A 的元素限制在 (0,1) | **不能**从 A 的谱半径推断含 Transformer 项的整个非线性映射收缩；需数值实验 |
| ACT stopping | \`main.py:750-891\` | 社区代码 + ACT 公开研究 | 源码确定：根据 halting probability 计算输出加权和 | 与实现的实际算力节省比较 |
| **ACT 是否省计算** | \`main.py:855-889\` | 源码确定 | **关键发现**：\`self.block(combined, ...)\` 始终处理完整 token 张量，直到整个 batch 的 token 全部停止（无缓存路径）；并非任意 token 提前停止便单独省算。启用 KV Cache 后不执行 \`halted.all()\` 早退 | 记录每次实际调用/全部 token FLOPs，不将“逐 token 权重停止”误称逐 token 算力节省 |
| 词汇表 | \`tokenizer.py:1-40\` | 社区依赖 | 源码确定：\`openai/gpt-oss-20b\` Tokenizer 外部加载 | 固定版本、校验实际 vocab 与 embedding |

以上架构全是 **OpenMythos 社区作者的实现假说**。没有足够公开证据推断 Claude Mythos 必然使用这些精确模块或具体配置。

## 2. 训练与推理风险清单

| 优先级 | 项目 | 证据（源码） | 风险/影响 | 计划 |
|---|---|---|---|---|
| P0 | **没有独立 Heldout 验证流程** | \`training/3b_fine_web_edu.py:461-540\` 训练 loader 和 loss；没有 val/eval loop | 无法报告真实验证集 token NLL/PPL，无法证明模型质量或判断过拟合 | R1 前必须补齐 |
| P0 | **目前没有本项目真实预训练 Checkpoint** | ACT-001–004 使用随机 tiny model、合成 token；3B 脚本只是入口 | 不具备 Mythos 模型能力复刻证据 | 建立小模型真实文本训练与 checkpoint |
| P1 | **流式数据恢复不保存位置** | \`training/3b_fine_web_edu.py:52-54, 443-461\` | 恢复时数据可能重播；“重播可忽略”是作者假设，不能当作复现保证 | 可恢复 sampler/dataset cursor、记录已消费 token |
| P1 | **Checkpoint 不包含 RNG 状态** | \`training/3b_fine_web_edu.py:219-240,259-306\` | 即使模型/优化器可加载，也不能保证下一批随机过程重现 | 存 CPU/CUDA RNG、loader 状态 |
| P1 | **Tokenizer 未固定不可变版本** | \`tokenizer.py:1-37\` \`AutoTokenizer.from_pretrained(model_id)\` | 不同版本可能影响 token IDs/embedding；Tokenizer 特殊 token、revision 需审查 | 记录 revision + hash |
| P1 | **FP16 无 GradScaler 路径** | \`training/3b_fine_web_edu.py:401-427,483-507\` | 在无 BF16 支持 GPU 上潜在 underflow/unstable grads | 优先 BF16；如需 FP16 添加 scaling + 测试 |
| P1 | **多 token 缓存分块的 causal mask** | \`main.py:1023\` 仅 \`T×T\` mask，cache 情况 keys 长度可达 \`S>T\` | 已知源码存在尺寸设计疑点，但尚未在 Codespaces 动态确认 | 运行 \`r0_probe.py\` 的 GQA/MLA 缓存分块对照 |
| P1 | **MoE bias 没有看到训练更新** | \`main.py:482,512-515\` + \`training/3b_fine_web_edu.py\` | 负载均衡机制不一定生效 | 动态统计路由，并补专门训练策略 |
| P2 | **训练缺固定 torch random seed** | \`training/3b_fine_web_edu.py:311-550\` | 不能严格重现初始化与数据迭代 | 固定并持久化 seed、环境信息 |
| P2 | **未写入文档结束分隔符** | \`training/3b_fine_web_edu.py:100-109\` | 不同文档直接连接形成非自然语言跨界训练对 | 使用 EOS/doc separator，进行分割验证 |
| P2 | **CPU fused AdamW 兼容性** | \`training/3b_fine_web_edu.py:437-441\` | \`fused=True\` 并非所有环境支持，尤其不同 PyTorch/设备组合 | 设备与 torch 版本兼容检查 |
| P2 | **不可信 Checkpoint 反序列化** | \`training/3b_fine_web_edu.py:286\` \`weights_only=False\` | Pickle 可执行代码；仅加载可信来源 | 新的实验通道使用安全 tensor-only state dict |
| P2 | **KV Cache 分块与递归对齐** | \`main.py:239-243,391-395,860-889,1023-1053\` | 除掩码外，loop-specific cache 与停止条件也需一致性验证 | 严格对照 full/prefix/one-step/chunk |

**不宜直接下结论**：训练脚本存在 P1/P2 风险 ≠ GPU 训练一定失败；模型局部测试通过 ≠ 模型正确复刻了 Mythos；更深循环 ≠ 更强推理。

## 3. R0 自动工具

### A. 可追溯静态源代码检查

\`research/mini_mythos/scripts/r0_audit.py\`：
- 输出每条发现的源码路径、行号、状态和风险等级。
- \`PRESENT\` 只代表模式被发现；\`GAP\` 只代表特定模式未找到；\`REVIEW\` 不等于错误已经复现。
- 结果保存在 Git 忽略目录 \`research/mini_mythos/results/r0/audit.json\`。

### B. 真实上游微模型运行探针

\`research/mini_mythos/scripts/r0_probe.py\`：
1. tiny GQA/MLA 模型训练一步，保存 tensor-only 模型及 optimizer，加载并继续另一步，检查参数和 loss 的一致性。**不覆盖真正的 3B/FSDP 训练链路，也不检查数据恢复**。
2. 先喂六个 token 前缀，再以已缓存 KV 处理两个 token chunk；与完整八 token 的输出比较。异常会被捕获写入 JSON；若 \`FAIL\` 则记录具体错误，不证明 Anthropic 原模型有任何问题。
3. 两者仍使用合成 token，不是评估语言能力。

Codespaces：

\`\`\`bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r0_audit.py --repo .
python research/mini_mythos/scripts/r0_probe.py --repo .
\`\`\`

当需要让任何运行探针失败导致 CI 整体失败，追加 \`--strict\`；默认将失败记录为审计证据并正常退出。

## 4. R0 通过门槛与下一工程里程碑

- **尚未通过 R0 完整验收**。截至编写时只完成第一轮静态审计和探针代码提交；运行结果尚待 Codespaces 执行。
- 对 \`P0\` 项，下一阶段独立建立 **small-model real-text pilot**：可重复切分公开合法语料、固定 tokenizer 版本、保存安全 checkpoint、评估 Heldout token NLL/PPL，并产出生成样例；优先用小模型验证，不直接消耗 3B 级 GPU。
- 对 \`P1\` 项，将真实观察到的缓存问题、数据恢复与混精问题独立建 bugfix 实验；**不得在审计前直接改写上游 \`open_mythos/main.py\`**。
- 有完整真实文本权重和基线以后，再进行架构对照或 Mythos 行为对齐。

---

参考上游：<https://github.com/kyegomez/OpenMythos>。独立研究 Fork：<https://github.com/leotree2020/OpenMythos/tree/mini-mythos-research>。
