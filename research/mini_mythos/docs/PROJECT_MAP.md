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
- **问题**：原生 Parcae Optimizer/Scheduler/RNG/权重恢复的端到端生命周期未统一验收；Gate 2.2-C 的真实证据提取器、执行环境、GPU 预算/授权门禁仍未解锁。
- **未开始/未验证**：原生完整 CPU 生命周期冻结验收、经批准的 GPU Pilot、规模训练。
- **证据**：`docs/R1_GATE_F_RESULT.md`、`docs/R2_GATE_Q_RESULT.md`、`gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`。

### C. 实验与工具

- **代码**：`research/mini_mythos/scripts/`、`gate2_1/`、`gate2_2/` 中非测试脚本和配置。
- **已验证**：F2-B 原生循环 PASS/CLOSED；F2-C 冻结三个梯度标量的数值检查 PASS/CLOSED（纯 fp64 原版路径仍受限）；F2-D 固定深度与 per-batch RNG/Checkpoint PASS/CLOSED。R0/R1/R2 历史阶段有已归档的限定结果。
- **问题**：F2-E B1-R3 已修复遗漏 Mask/错误 step 检出，验证 n/k、Mask 内容/写回、per-token E4/E5，原始证据及实际探针五项 SHA 独立 MATCH；但 R3 冻结要求中的每 Mask 原始位或摘要归档缺失、精确 checkpoint replay==2 未被验收器强制、post-backward RNG 边界未记录等问题仍在。**E1–E5 正向证据积极，正式全项 NOT CLOSED，转 Claude Code 限定收口**。E6 INCONCLUSIVE，原生 Parcae bug 未证明。
- **未开始/未验证**：Claude Code 先只读接管审核；经单独授权后仅完成 R3 冻结证据/断言的狭义收口，不引入新实验维度；之后规划原生完整 CPU 训练链和架构对照。
- **证据**：`docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md`、`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### D. 测试

- **代码**：`tests/`、`research/mini_mythos/tests/`、`interfaces/test_*.py`、`gate2_1/test_*.py`、`gate2_2/test_*.py`、`.github/workflows/`。
- **已验证**：R1 Gate F 记录 106/106 单元测试 PASS；不同冻结阶段有单独的测试证据。不得将历史 106 或 205/241/248 等数字当作当前 HEAD 全套测试结果。
- **问题**：R3 已拒绝遗漏/额外 Mask、step=999、翻转真实 Mask 位、NaN/零/缺失/额外梯度，并核验写回 x_new/xk；但归档删去原始 Mask 且未存 SHA，回放精确次数仅按 >=1 判断，RNG 未记录 backward 后和 sampler 边界，尚不足冻结全项最终验收。
- **未开始/未验证**：Claude Code 接管只读审计；待授权的限界性 F2-E 验收证据收口；之后训练生命周期回归及另行授权 GPU 数值对照。
- **证据**：`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### E. 文档与证据

- **位置**：`research/mini_mythos/docs/`、`gate2_2/evidence/`、`docs/p1b/ci/`、`backup/`、仓库 README。
- **已验证**：Git SHA 锚点、F2-B/C/D 正式独立审计、F2-E B1 证据 SHA-256 复核、独立备份分支。
- **问题**：历史文档中可能有过期的“下一步”；本地未提交 `gate2_1/TEST_RESULTS.json` 未纳入 Git 备份；旧工作区状态不能通过远端断言。
- **未开始/未验证**：每次新会话自动/人工刷新项目地图的 LOC 和 Git 状态、建立持续变化报告。
- **证据**：`backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`、`backup/PROJECT_TREE_MANIFEST_20261025.json`。

## 3. 当前研发门禁与下一阶段

1. **当前唯一无需新增实验授权的下一步**：Claude Code 按 `docs/SESSION_START_PROTOCOL.md` 完成只读研发接管；必须阅读最新 `docs/F2E_B1R3_CHATGPT_INDEPENDENT_REVIEW_AND_CLAUDE_HANDOFF_20261025.md`。如用户另行授权，仅按报告列出的 R3 剩余档案与验收断言做限定收口；不自动实验、GPU 或架构变更。
2. **之后先设计/审核再执行**：原生 Parcae CPU Training Lifecycle（forward → loss → backward → optimizer → scheduler → checkpoint → resume），包括冻结预期/实际/梯度和恢复标准。
3. **再之后**：真实数据、Tokenizer、heldout、模型能力和非循环基线。
4. **最后且独立批准**：GPU 门禁、规模训练、效率优化、架构创新。不能用当前微型 PASS 自动解锁 Gate 2.2-C。

## 4. 新会话强制入口

**所有新会话在执行任何代码/提出新实验前必须先读取 `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`，再读取本项目地图和最新正式检查点。** 先报告 Git HEAD、工作区 dirty 文件、最新验收门禁、五模块状态与下一条唯一批准指令。若缺少仓库/工作区访问，标记 UNKNOWN 并停止任何可能破坏数据的操作。不可从聊天记忆猜测当前 HEAD 或 PASS。

## 5. 变更控制

- 本文初版是**基线快照**，后续应以实际 Git 工作树扫描结果补充精确 LOC，不要悄悄覆盖旧基线。
- 每次阶段验收后更新：模块统计（含基线 SHA）、PASS/FAIL/BLOCKED/NOT TESTED、证据路径、剩余风险、下一步；另保留阶段检查点。
- 原始五条科研规则始终有效：CPU 优先、预设验收、上游不变、交叉审核、阶段检查点。
