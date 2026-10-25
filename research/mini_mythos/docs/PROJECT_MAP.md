# OpenMythos 项目地图（五模块 / 研发状态）

**基线**：2026-10-25 备份前冻结研究 Commit `0853051ec1791adbc54e4e8c90f2be146a0ff092`，文件清单 `research/mini_mythos/backup/PROJECT_TREE_MANIFEST_20261025.json`。**本页属于研发管理索引，不是新的实验 PASS。**

## 1. 范围和可审计统计口径

本地图覆盖 `leotree2020/OpenMythos` 仓库在上述基线的 **444 个 Git 跟踪文件 / 2,803,100 bytes**。不包含未提交工作区、外部 Parcae/AxoNN 源码、模型权重、HF 缓存或依赖包。按文件的**主要用途**排他性归类；研究用训练脚本算实验，只有正式训练入口和 pilot_train 算训练；归档的 JSON/日志归文档与证据。

| 模块 | 文件数 | Python 文件数 | bytes | 典型位置 |
|---|---:|---:|---:|---|
| 核心模型 | 5 | 5 | 94,110 | `open_mythos/` |
| 训练 | 3 | 2 | 24,480 | `training/`, `research/mini_mythos/scripts/pilot_train.py` |
| 实验与工具 | 97 | 70 | 635,081 | `research/mini_mythos/scripts/`, `gate2_1/`, `gate2_2/` |
| 测试 | 76 | 75 | 475,415 | `tests/`, `research/mini_mythos/tests/`, CI |
| 文档与证据 | 263 | 1 | 1,574,014 | `docs/`, Markdown, `evidence/`, 运行归档 |
| **合计** | **444** | **153** | **2,803,100** | |

## 最新 Git 文件树快照（2026-10-25）

2026-10-25 研究分支 `2ceb08b1db34871104a45e27e5ec2f7bc81e0ce1` 的完整递归 Git tree 经实际读取（非截断）：**470 个 Git 跟踪文件、154 个 .py 文件、3,003,079 bytes**。这是可审计的**统计基准 Commit**，其后的文档更新会使 HEAD/文件数/字节数继续变化，应以后续重新扫描为准。

| 模块（沿用原基线归类） | 当前文件数 | 当前 bytes |
|---|---:|---:|
| 核心模型 | 5 | 94,110 |
| 训练 | 3 | 24,480 |
| 实验与工具 | 98 | 639,567 |
| 测试 | 76 | 482,919 |
| 文档与证据 | 288 | 1,762,003 |
| **合计** | **470** | **3,003,079** |

统计方法：2026-10-25 原 444 文件冻结分组 + 该基线到以上 HEAD 的 Git 变更（26 个新增文件、1 个既有测试文件修改），并通过两个 Git tree 的实际文件 size 总和复核。**当前精确 LOC 仍是 NOT MEASURED**。最新详细研究状态见 `docs/PROJECT_STATUS_20261025.md`。

### F2-E 限定收口后的新统计基线

`ee1b3c8564f4cc868e73efd58e4ddc42c35e4f78` 的完整 Git tree 实测：**481 文件 / 154 Python 文件 / 3,050,894 bytes**。比上面 `2ceb08b1` 统计增加 Grok 的 F2-E closeout 实验文件、Native CPU Train Lifecycle 仅设计文档、本项目进度报告和 ChatGPT 正式审核。此表取代上表的“当前”含义；两表的 SHA/数值均作为历史快照保留。

| 模块 | 文件数 | bytes |
|---|---:|---:|
| 核心模型 | 5 | 94,110 |
| 训练 | 3 | 24,480 |
| 实验与工具 | 98 | 639,567 |
| 测试 | 76 | 484,810 |
| 文档与证据 | 299 | 1,807,927 |
| **合计** | **481** | **3,050,894** |

最新实验结论和下一阶段见 `docs/PROJECT_STATUS_20261025.md`、`docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`；精确代码行数仍为 **NOT MEASURED**。

**注意：上述为文件数量和 bytes，绝非已测得的代码行数。** 精确物理行数/非空行数/注释行数须在可访问完整 Git 工作树的执行环境运行 `python research/mini_mythos/scripts/project_map_inventory.py --repo . --output ...`。工具不能执行时标记 **NOT MEASURED**，禁止将字节数换算为 LOC。

## 2. 模块状态：已验证 / 问题 / 尚未开始

### A. 核心模型

- **代码**：`open_mythos/main.py`（模型主体）、`moda.py`、`variants.py`、`tokenizer.py`、`__init__.py`。
- **已验证（有限范围）**：早期 R1 CPU Tiny GQA 真实 WikiText-2 字节级预测，step600 test NLL 2.384439 / PPL 10.852968；匹配暴露量 Add-1 Bigram PPL 12.790071。原生 Parcae 独立复现的 F2-B/C/D 验收**不能直接外推为本目录所有模型配置 PASS**。
- **问题**：Tiny 自由生成重复，连贯语言生成/推理/编程尚无能力证明；不同动态采样模式 n/k 语义的作者意图 UNKNOWN。
- **未开始/未验证**：同预算非递归 Transformer 公平对照、规模化模型质量证明、真实能力基准。
- **证据**：`docs/R1_GATE_F_RESULT.md`、`docs/F2B_FINAL_ACCEPTANCE_20261024.md`、`docs/F2C_FINAL_ACCEPTANCE_20261024.md`。

### B. 训练

- **代码**：`training/3b_fine_web_edu.py`、`training/requirements.txt`、研究 pilot 入口 `scripts/pilot_train.py`。
- **已验证（有限范围）**：R1 Tiny 真实文本训练及 checkpoint 重放；R2 分片、数据流、恢复方面的独立 CPU 证据。并非原生 Parcae 完整训练入口已 PASS。
- **问题**：F3-A 已获得 CPU 执行授权并完成首次冻结实验（Grok `34c4414` 冻结，`3b582c7` 结果）：6 步 AdamW 固定输入训练的第 2–6 步更新参数、Loss 下降、文件恢复后 Loss/LR/权重与连续训练匹配。但是 `step()` 每步重置 RNG、Checkpoint step/scheduler 元数据未强制验收、optimizer/RNG 完整状态未逐步比较、坏 Checkpoint 负例未执行 loader；ChatGPT 审核 **F3-A PARTIAL POSITIVE / NOT CLOSED**。Gate 2.2-C GPU 仍 BLOCKED。
- **未开始/未验证**：F3-A 完整 RNG/optimizer/scheduler/step 恢复等价性的最小 R1 修正及正式复核；原生 `scripts/train.py`、MuonAdamW、DataLoader 恢复、GPU Pilot 和规模训练仍未验证。
- **证据**：`docs/R1_GATE_F_RESULT.md`、`docs/R2_GATE_Q_RESULT.md`、`gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`。

### C. 实验与工具

- **代码**：`research/mini_mythos/scripts/`、`gate2_1/`、`gate2_2/` 中非测试脚本和配置。
- **已验证**：F2-B 原生循环 PASS/CLOSED；F2-C 冻结三个梯度标量的数值检查 PASS/CLOSED（纯 fp64 原版路径仍受限）；F2-D 固定深度与 per-batch RNG/Checkpoint PASS/CLOSED。R0/R1/R2 历史阶段有已归档的限定结果。
- **已验证（2026-10-25 最新）**：Grok `fbeaf7c` 补齐每条 Mask 摘要、Checkpoint replay 精确 2、RNG 配对、权重/74 梯度验收与负例。ChatGPT `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md` 对六项声明文件 SHA-256 和 9/9 Mask 内容哈希独立校验，并正式批准 **F2-E E1–E5 PASS/CLOSED（限于冻结 Parcae 2/2/2 CPU 微型采样/Mask/重复/Checkpoint 范围）**。**E6 仍 INCONCLUSIVE**；无模型 Bug 或作者意图证明，不能将整个 F2-E 无条件标 PASS。
- **已执行但待验收**：Grok 已在先冻结 `docs/F3A_FROZEN_CONFIG.md` 后，执行原生 Parcae 2/2/2、固定输入、AdamW、linear scheduler、6 步 CPU 训练与 3 步断点文件恢复；局部学习信号与模型权重一致性证据积极。但依 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md` 正式总体 **NOT CLOSED**。下一步仅补验收器真实状态恢复/负例，不做新架构；Claude Code 暂缓接管。
- **证据**：`docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md`、`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### D. 测试

- **代码**：`tests/`、`research/mini_mythos/tests/`、`interfaces/test_*.py`、`gate2_1/test_*.py`、`gate2_2/test_*.py`、`.github/workflows/`。
- **已验证**：R1 Gate F 记录 106/106 单元测试 PASS；不同冻结阶段有单独的测试证据。不得将历史 106 或 205/241/248 等数字当作当前 HEAD 全套测试结果。
- **已验证（最新限定范围）**：F2-E closeout 已归档 Mask SHA 并独立重建核对 9/9，严格拒绝 replay=1 且预期 ON=2/OFF=0，新增 sampler/post-backward RNG 比较、权重/梯度身份检查、FAIL exit 1 演示；限定 E1–E5 正式 PASS/CLOSED。更大模型、新种子或完整训练不在此验收内。
- **未开始/未验证**：最新 HEAD 全量回归执行；原生 Parcae CPU 训练生命周期设计评审、冻结和正式执行；GPU 数值对照需要另外满足 Gate 2.2-C 条件并授权。
- **证据**：`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### E. 文档与证据

- **位置**：`research/mini_mythos/docs/`、`gate2_2/evidence/`、`docs/p1b/ci/`、`backup/`、仓库 README。
- **已验证**：Git SHA 锚点、F2-B/C/D 正式独立审计、F2-E B1 证据 SHA-256 复核、独立备份分支。
- **问题**：历史文档中可能有过期的“下一步”；本地未提交 `gate2_1/TEST_RESULTS.json` 未纳入 Git 备份；旧工作区状态不能通过远端断言。
- **未开始/未验证**：每次新会话自动/人工刷新项目地图的 LOC 和 Git 状态、建立持续变化报告。
- **证据**：`backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`、`backup/PROJECT_TREE_MANIFEST_20261025.json`。

## 3. 当前研发门禁与下一阶段

1. **当前研发进度与唯一下一项建议**：用户已授权 F3-A CPU 完整训练链，Grok 已完成冻结配置（`34c4414`）、首次执行（`3b582c7`）。ChatGPT 最新审核 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md` 判定总体 **PARTIAL / NOT CLOSED**：CPU 训练 Loss/权重与模型恢复后权重的正向证据通过，但需要一次限定的 F3-A-R1 RNG/optimizer/scheduler/checkpoint-step/真实负例补验证，先写冻结补充后执行、保留原版数据，交 ChatGPT 再审。**不授权 GPU、数据集/规模训练、上游源码变更**；Claude Code 暂缓。
2. **之后先设计/审核再执行**：原生 Parcae CPU Training Lifecycle（forward → loss → backward → optimizer → scheduler → checkpoint → resume），包括冻结预期/实际/梯度和恢复标准。
3. **再之后**：真实数据、Tokenizer、heldout、模型能力和非循环基线。
4. **最后且独立批准**：GPU 门禁、规模训练、效率优化、架构创新。不能用当前微型 PASS 自动解锁 Gate 2.2-C。

## 4. 新会话强制入口

**所有新会话在执行任何代码/提出新实验前必须先读取 `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`，再读取本项目地图和最新正式检查点。** 先报告 Git HEAD、工作区 dirty 文件、最新验收门禁、五模块状态与下一条唯一批准指令。若缺少仓库/工作区访问，标记 UNKNOWN 并停止任何可能破坏数据的操作。不可从聊天记忆猜测当前 HEAD 或 PASS。

## 5. 变更控制

- 本文初版是**基线快照**，后续应以实际 Git 工作树扫描结果补充精确 LOC，不要悄悄覆盖旧基线。
- 每次阶段验收后更新：模块统计（含基线 SHA）、PASS/FAIL/BLOCKED/NOT TESTED、证据路径、剩余风险、下一步；另保留阶段检查点。
- 原始五条科研规则始终有效：CPU 优先、预设验收、上游不变、交叉审核、阶段检查点。
