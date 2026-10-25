# Mini-Mythos / OpenMythos — 全项目研发进度快照

更新日期：2026-10-25（Asia/Tokyo）  
定位：**项目治理/研究状态快照，不是新的实验或新 PASS**。  
数据基线（写报告前的研究分支）：`leotree2020/OpenMythos@2ceb08b1db34871104a45e27e5ec2f7bc81e0ce1`，分支 `mini-mythos-p1c-gate22c-readiness`。后续提交本报告将改变 HEAD，请启动时重新核对。  
源：当前 GitHub branch/commits、完整递归 Git tree（`truncated=false`）、`docs/PROJECT_MAP.md`、`docs/SESSION_START_PROTOCOL.md`、最新 `docs/F2E_B1R3_CHATGPT_INDEPENDENT_REVIEW_AND_CLAUDE_HANDOFF_20261025.md`、早期 R1/R2/F2-B/C/D 结果文档。未在本次统计中本地执行 PyTorch 模型、测试套件或训练。

## 1. 一页结论

**真实状态：CPU 数学正确性基础较扎实，但原生完整训练与可用语言能力仍未验证。当前关键门禁是 F2-E E1–E5 的限定验收证据收口；E6 探索性结果保持 INCONCLUSIVE。**

- 主要研发架构方向：保持 Prelude → Recurrent Core → Coda；随机初始化训练独立权重；上游优先，先复现再改进。**不等于已复现 Anthropic Claude Mythos 的秘密架构、权重或能力**。
- F2-B 固定范围原生循环 CPU 行为：正式 `PASS/CLOSED`。
- F2-C 固定三个 Core 梯度标量有限差分：正式 `PASS/CLOSED`（仅该范围；纯 fp64 原版路径受限）。
- F2-D 冻结固定/自动 per-batch 采样 RNG、梯度、checkpoint：正式 `PASS/CLOSED`（仅该范围）。
- F2-E B1-R3：Grok 实验 `E1–E5 LOCAL PASS`；独立审核结论 **`PARTIAL POSITIVE / NOT CLOSED`**，详见 R3 审核报告；E6 `INCONCLUSIVE`。
- 原生 Parcae CPU 训练完整生命周期（Forward→Loss→Backward→Optimizer→Scheduler→Checkpoint→Resume）：**NOT TESTED as an end-to-end frozen gate**。
- Gate 2.2-C GPU：**BLOCKED**，缺真实服务凭据/报价/预算核对/非合成证据提取器；没有实际启动 GPU pod。
- 当前用户决定：继续由 **Grok 开发与执行 CPU**，利用现有 Credit；**ChatGPT 独立交叉审核**；Claude Code 暂缓接管。此为执行者安排变更，不放宽验收门禁。

## 2. 仓库规模：实测 Git 跟踪内容，非 LOC

基线 `0853051ec1791adbc54e4e8c90f2be146a0ff092`：444 Git 文件，153 Python 文件，2,803,100 bytes。  
上述最新 HEAD：**470 Git 文件、154 Python 文件、3,003,079 bytes**。两者 Git diff 显示 +26 新文件、1 个原有研究探针修改；两次递归 Git tree 精确求和匹配，总大小增加 199,979 bytes。

以下按历史 `PROJECT_MAP.md` **同一排他五模块分类口径**算得：初版各类计数/字节 + 自基线新增 25 个文档/证据文件、1 个实验工具脚本、1 个既有测试脚本内容增量。不是用不同正则重新归类历史文件。

| 模块 | 当前文件 | Python 文件说明 | 当前 bytes | 本阶段进度 |
|---|---:|---|---:|---|
| 核心模型 | 5 | 模型源码 | 94,110 | 早期 Tiny 语言预测实验通过；规模能力未验证 |
| 训练 | 3 | 正式入口与 pilot | 24,480 | Tiny/数据恢复有历史证据；原生 end-to-end 尚未验收 |
| 实验与工具 | 98 | 新增只读 inventory 工具 | 639,567 | F2-B/C/D 限定 PASS；F2-E 待证据收口 |
| 测试 | 76 | 既有 R3 探针有修改 | 482,919 | 负例和采样/Mask 探针已完善；仍有边界 |
| 文档与证据 | 288 | 新增 25 份文件 | 1,762,003 | 可追溯性提升，仍需按阶段刷新 |
| **合计** | **470** | **Python 共 154** | **3,003,079** | |

**注意：bytes ≠ LOC；当前 HEAD 精确物理代码行数仍未实测（NOT MEASURED）**。当前 Git tree 统计不包含 Python 依赖、HF 下载、上游 Parcae/AxoNN 仓库、权重以及任何本地未提交文件。可在受控完整工作树执行只读脚本 `research/mini_mythos/scripts/project_map_inventory.py` 测精确行数，不可将 bytes/文件数推成 LOC。

## 3. 五模块状态：验证、短板与下一步

### A 核心模型 — 基础研究已建立，能力未成型

源码：`open_mythos/main.py`、`moda.py`、`variants.py`、`tokenizer.py` 等。
- **已验证（限定）**：R1 Tiny GQA 从随机权重训练至 600 steps，使用官方 WikiText-2 test 的字节级评估，test NLL=2.384439、PPL=10.852968；与匹配训练暴露量 Add-1 Bigram PPL=12.790071 比较具有优势。该指标属于小模型 next-byte prediction，不是聊天生成能力。
- **问题**：历史 greedy 自由生成重复；不存在连贯自然语言问答/推理/编程、对标准非循环 Transformer 的等预算质量证明，也没有可用规模的模型。
- **下一步**：待训练生命周期验收后设计公平 baseline、数据和质量评估，避免先改掉循环 Core。

### B 训练 — Pilot 有历史证据，原生端到端仍未验证

入口：`training/3b_fine_web_edu.py`、`training/requirements.txt`、`research/mini_mythos/scripts/pilot_train.py`。
- **已验证（限定）**：R1 Tiny 真实数据训练、权重/RNG checkpoint 恢复；R2 本地数据分片/worker 行为测试和部分训练准备审计。
- **问题**：原生 Parcae 从随机初始化出发的 optimizer、scheduler、checkpoint/resume、连续可复现训练尚未按**统一冻结端到端门禁**正式接受。
- **下一步**：F2-E 正式收口后，对原生 Parcae 的 CPU training lifecycle 先设计目的、输入、容差、预期、失败条件与成本；经授权再执行。

### C 实验与工具 — 原生 CPU 核心机制大多通过限定验收

- **F2-B**：原版原生循环机制/固定深度 CPU — `PASS/CLOSED`。
- **F2-C**：3 个冻结 Core 梯度 scalar 的有限差分 — `PASS/CLOSED`，非全模型理论证明。
- **F2-D**：固定与默认 per-batch 自动深度、CPU RNG/重算/梯度 — `PASS/CLOSED`，不能推广所有配置。
- **F2-E**：B1→R3 的 per-batch/per-sequence/per-token、Mask、return mean、重复性、checkpoint 结果良好；独立审核 `PARTIAL/NOT CLOSED`，并且 E6 `INCONCLUSIVE`。
- **下一步**：按现有 R3 审核的**已知、有限**缺口补全并生成一组独立新证据，不启动新研究实验维度。E6 不重新运行。

### D 测试与验收 — 偏重精度，不等于已验证所有代码

- **已验证历史**：R1 Gate F 106/106 单元测试；R2 Gate Q 241/241 + 8/8 CPU 专项（不同历史 HEAD，不得称为当前 470 文件的最新全套测试）；F2-E R3 17 个合成/受控负例检查在记录中被拒绝。
- **问题**：R3 未归档每个 Mask 的 raw bits/digest；Checkpoint replay 验收器只检查 `>=1`，而该冻结例预期精确 2；post-backward / sampler RNG 边界归档不全；74 个梯度与确切冻结 expected set 的逐名/形状校验仍需收口。未见最新 HEAD 全套单测执行凭据。
- **下一步**：Grok 仅在已授权边界内补这些条件；原始旧证据不得覆盖，ChatGPT 复核。

### E 文档与治理 — 已建立，但需防止最新任务与旧文档冲突

- **已验证**：完整项目地图、2026-10-25 恢复备份、Git SHA 锚点、R0/R1/R2/F2 系列记录、独立审核、证据 SHA256、专门新会话 SOP。
- **问题**：历史检查点内容可能过时；本地 `research/mini_mythos/gate2_1/TEST_RESULTS.json` 多次报告 dirty，其实际未提交内容不可从 GitHub 验证或恢复。
- **下一步**：保存该文件独立备份与哈希，更新每阶段 HEAD/状态/证据；在最新 SOP 标明 Grok 继续开发、Claude 延后。每次新会话仍应先读全量项目状态而非聊天记忆。

## 4. 优先级 / 进入下一阶段门禁

| 顺序 | 阶段 | 当前判定 | 阶段出口 |
|---:|---|---|---|
| 1 | F2-E 最终有限收口 | **进行中，E1–E5 尚未 CLOSED** | Mask 摘要与预期内容匹配、精确 replay、RNG 边界、权重/梯度身份与负例、独立审核通过 |
| 2 | Native Parcae CPU Training Lifecycle 设计 | **NOT STARTED as unified new gate** | 冻结 forward/loss/backward/optimizer/scheduler/checkpoint/resume 验收和环境/证据方案 |
| 3 | Native CPU 生命周期执行 | **NOT TESTED / separate authorization** | 更新参数/损失与停止恢复等价性通过；原始日志/哈希可审计 |
| 4 | Mini-Mythos 从随机权重的训练与公平基线 | **尚待系统化验证** | 同参数/数据/计算预算可比较的质量、FLOPs、稳定性、推理成本 |
| 5 | GPU Pilot / 扩规模 / 新机制 | **BLOCKED / separate GPU gate** | 环境、凭据/余额/报价、预算、非合成证据链与独立授权齐全 |

**不制造统一“完成百分比”：** 不同技术任务不可按文件数/测试数直接折算工程进度。当前最优先不是继续扩大 F2-E 探针，而是及时收口并建设真实训练系统。

## 5. 当前研发执行与授权

2026-10-25 最新用户决定：**Grok 继续主要代码开发和 CPU 研究执行（利用已有 Credit），Claude Code 暂不切换，ChatGPT 独立审计与冻结门禁复核。**

用户已经授权 Grok：
1. 在原有固定配置内完成 R3 审核记录的**最终、有限** F2-E 证据收口；
2. 之后可以**只读审计/设计** Native Parcae CPU Training Lifecycle 的验收方案，但**不可自行运行**新的端到端训练；
3. 不修改原生 Parcae/AxoNN，不变更 Prelude→Recurrent Core→Coda，不启动 GPU、不新增 E6 实验，不重复正式 CLOSED 的 F2-B/C/D。

原始 B1/B1-R1/B1-R2/B1-R3 证据全部不可覆盖。未见上述最终收口的新远端 Git 提交（截至本快照的 Git HEAD）。用户授权更换实施者不等于任何新增计算授权或验收放宽。

## 6. 当前要保护的文件与下一条指令

- **重要保护**：历史上 Grok 报告未提交的 `research/mini_mythos/gate2_1/TEST_RESULTS.json`，必须由持有 Codespaces 工作区者先只读核验/备份；GitHub 不可看到其 dirty 内容。
- 上游 Parcae pin `69284c13746e849104f738d6d1a347b1f457df76`；AxoNN pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`。
- **下一条唯一执行指令（Grok）**：按 `docs/F2E_B1R3_CHATGPT_INDEPENDENT_REVIEW_AND_CLAUDE_HANDOFF_20261025.md` 已冻结的剩余条目，在 CPU 限定完成一组不覆盖历史的验收补证据，Git 提交，`PENDING CHATGPT REVIEW` 停止；可以同时完成**下一阶段只读源码分析及计划**，但不得执行原生完整训练。
- **接管任何新会话**：先读 `docs/SESSION_START_PROTOCOL.md`、`docs/PROJECT_MAP.md`、此快照和最新阶段检查点；核对真实 HEAD/dirty。已有旧时间点历史“Claude 接管”措辞以本快照更新的当前用户决策为准，其他约束仍有效。

## 7. 主要证据索引

- Tiny 真实文本：`research/mini_mythos/docs/R1_GATE_F_RESULT.md`
- R2 分片：`research/mini_mythos/docs/R2_GATE_Q_RESULT.md`
- F2-B/C/D：`research/mini_mythos/docs/F2B_FINAL_ACCEPTANCE_20261024.md`、`F2C_FINAL_ACCEPTANCE_20261024.md`、`F2D_FINAL_CPU_ACCEPTANCE_20261025.md`
- F2-E 最新审核：`research/mini_mythos/docs/F2E_B1R3_CHATGPT_INDEPENDENT_REVIEW_AND_CLAUDE_HANDOFF_20261025.md`
- GPU 约束：`research/mini_mythos/gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`
- 工作流与备份：`research/mini_mythos/docs/SESSION_START_PROTOCOL.md`、`research/mini_mythos/backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`

**本报告仅做现有源码/历史证据状态整合，没有新模型实验、没有人工制造 PASS。**
