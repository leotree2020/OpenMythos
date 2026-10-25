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
- **F3-A 最新正式验收**：Grok B1 配置/执行 `34c4414`/`3b582c7`，R1 配置/执行 `8ea2d67`/`14974c8`，最终异常校验提交 `dd36b939`。ChatGPT `docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md` 独立复核并批准 **F3-A CPU 固定输入、原生 2/2/2 Parcae、AdamW、6 步与文件恢复研究性生命周期 PASS/CLOSED（限定范围）**。三项异常恢复经过单独 checked loader/验证器，未集成到历史 R1 恢复入口；真实 DataLoader、MuonAdamW、GPU 仍未测试。
- **未开始/未验证**：独立的真实数据 DataLoader 恢复、生产 `scripts/train.py`、MuonAdamW、GPU Pilot、同计算预算质量与效率实验。F3-A 结果中的 Python 元数据 3.10.21 与 `/usr/bin/python3.11` 命令不一致，需只读注明，不能视为环境已验明。
- **证据**：`docs/R1_GATE_F_RESULT.md`、`docs/R2_GATE_Q_RESULT.md`、`gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`。

### C. 实验与工具

- **代码**：`research/mini_mythos/scripts/`、`gate2_1/`、`gate2_2/` 中非测试脚本和配置。
- **已验证**：F2-B 原生循环 PASS/CLOSED；F2-C 冻结三个梯度标量的数值检查 PASS/CLOSED（纯 fp64 原版路径仍受限）；F2-D 固定深度与 per-batch RNG/Checkpoint PASS/CLOSED。R0/R1/R2 历史阶段有已归档的限定结果。
- **已验证（2026-10-25 最新）**：Grok `fbeaf7c` 补齐每条 Mask 摘要、Checkpoint replay 精确 2、RNG 配对、权重/74 梯度验收与负例。ChatGPT `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md` 对六项声明文件 SHA-256 和 9/9 Mask 内容哈希独立校验，并正式批准 **F2-E E1–E5 PASS/CLOSED（限于冻结 Parcae 2/2/2 CPU 微型采样/Mask/重复/Checkpoint 范围）**。**E6 仍 INCONCLUSIVE**；无模型 Bug 或作者意图证明，不能将整个 F2-E 无条件标 PASS。
- **最新独立审核**：F3-A 原生 Parcae CPU 固定 6 步 B1/R1、文件恢复后 Loss/LR/参数/优化器/RNG 指纹匹配、三项异常 Checkpoint 对照完成；正式 **PASS/CLOSED（研究性冻结条件）**。原始训练 loader 没有直接整合最终 checked loader，且没有重新运行 `scripts/train.py`。证据：`docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`。
- **证据**：`docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md`、`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### D. 测试

- **代码**：`tests/`、`research/mini_mythos/tests/`、`interfaces/test_*.py`、`gate2_1/test_*.py`、`gate2_2/test_*.py`、`.github/workflows/`。
- **已验证**：R1 Gate F 记录 106/106 单元测试 PASS；不同冻结阶段有单独的测试证据。不得将历史 106 或 205/241/248 等数字当作当前 HEAD 全套测试结果。
- **已验证（最新限定范围）**：F2-E closeout 已归档 Mask SHA 并独立重建核对 9/9，严格拒绝 replay=1 且预期 ON=2/OFF=0，新增 sampler/post-backward RNG 比较、权重/梯度身份检查、FAIL exit 1 演示；限定 E1–E5 正式 PASS/CLOSED。更大模型、新种子或完整训练不在此验收内。
- **未开始/未验证**：最新 HEAD 全套单测；真实 Streaming Dataset/Tokenizer/heldout 的训练与恢复、MuonAdamW、生产 `scripts/train.py`、GPU 等均需另外验收，不可外推 F3-A 的固定小样本 PASS。
- **证据**：`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### E. 文档与证据

- **位置**：`research/mini_mythos/docs/`、`gate2_2/evidence/`、`docs/p1b/ci/`、`backup/`、仓库 README。
- **已验证**：Git SHA 锚点、F2-B/C/D 正式独立审计、F2-E B1 证据 SHA-256 复核、独立备份分支。
- **问题**：历史文档中可能有过期的“下一步”；本地未提交 `gate2_1/TEST_RESULTS.json` 未纳入 Git 备份；旧工作区状态不能通过远端断言。
- **未开始/未验证**：每次新会话自动/人工刷新项目地图的 LOC 和 Git 状态、建立持续变化报告。
- **证据**：`backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`、`backup/PROJECT_TREE_MANIFEST_20261025.json`。

## 3. 当前研发门禁与下一阶段

1. **当前唯一下一项（仅设计）**：Grok `dd36b939` 三项异常校验获 ChatGPT `docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md` 审核批准，**F3-A 限定研究性 CPU 生命周期 PASS/CLOSED**；结束所有 F3-A 微型实验。接下来只读审计真实数据/Tokenizer/数据分片与 worker 恢复、冻结 heldout 评估与同计算预算非循环基线方案。**未授权实际真实数据训练、GPU、上游修改**；Claude Code 暂缓。
2. **之后分级执行**：先冻结真实数据、数据流恢复与公平模型评估的可复验收计划，项目负责人授权后再开展 CPU 正确性实验；真实规模吞吐/显存才考虑另行批准 GPU。
3. **再之后**：在受控的真实数据训练条件下比较模型能力、参数量/FLOPs/延迟，保持独立随机权重与循环核心不变。
4. **最后且独立批准**：GPU 门禁、规模训练、效率优化、架构创新。不能用当前微型 PASS 自动解锁 Gate 2.2-C。

## 4. 新会话强制入口

**所有新会话在执行任何代码/提出新实验前必须先读取 `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`，再读取本项目地图和最新正式检查点。** 先报告 Git HEAD、工作区 dirty 文件、最新验收门禁、五模块状态与下一条唯一批准指令。若缺少仓库/工作区访问，标记 UNKNOWN 并停止任何可能破坏数据的操作。不可从聊天记忆猜测当前 HEAD 或 PASS。

## 5. 变更控制

- 本文初版是**基线快照**，后续应以实际 Git 工作树扫描结果补充精确 LOC，不要悄悄覆盖旧基线。
- 每次阶段验收后更新：模块统计（含基线 SHA）、PASS/FAIL/BLOCKED/NOT TESTED、证据路径、剩余风险、下一步；另保留阶段检查点。
- 原始五条科研规则始终有效：CPU 优先、预设验收、上游不变、交叉审核、阶段检查点。


## F3-B 设计阶段审核（2026-10-25）

Grok `103344e47184735e03727d062ce81cbae6632e47` 提交五份研究设计文档，未提交新的训练实验。ChatGPT 独立审核见 `docs/F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md`：**F3-B DESIGN DELIVERABLES PASS/CLOSED（仅五份设计交付）**；**D1 DRAFT / NOT FROZEN / NOT AUTHORIZED**，D2/D3 NOT TESTED/NOT AUTHORIZED；官方 Parcae Tokenizer BLOCKED，GPU 未授权。

**当前唯一下一步（不跑代码、不下载/拟合 Tokenizer）**：Grok 仅编写一份 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，锁定 `Salesforce/wikitext` / `wikitext-2-raw-v1` / revision `b08601e04326c79dfdd32d625aee71d232d685c3`，冻结 BPE train-only 编码/许可/特殊 Token、单进程 source ID 与 Token cursor/断点续读、有限比较窗口及跳/重/错位负例。**D2 必须单独解决 vocab128→目标 BPE4096 时输入/输出形状与实际参数量变化**，不能仍称 247936 参数模型。Git 历史 R2 Gate M/N/O/P/Q 的文件级和本地合成专项 PASS 不代表远端逐行/DataLoader Resume PASS。

下一步仅为 D1 门禁设计提交，之后需 ChatGPT 审核和项目负责人明确 CPU D1 数据读取/Tokenizer 拟合的执行授权；不自动授权新训练、GPU 或架构变更。
