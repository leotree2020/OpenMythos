# Mini-Mythos / OpenMythos — 新会话强制启动规范（SOP v1）

**适用范围：** 任何新 ChatGPT / Grok / 编程 Agent 对话，包含换模型、额度恢复、重新打开 Codespaces、交接研发。**优先级：** 新会话必须先读本文、项目地图及最新检查点；旧聊天记忆只是线索，不能作为实验事实。

**最新 D1 预飞行 R2 修订检查点（2026-10-26；优先于下方 R1 检查点）：** 基准 `579ffd11ec2dba0b9cbf0eae67d7ce4e26874c19`；R1 复审结论 `PRE-FLIGHT FAIL`。新增 `research/mini_mythos/docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL_R2.md` 只修订 5 处（凡冲突以 R2 为准，v1/R1 原文保留）：CR 负例用干净前缀 + 续读 trace 整窗口逐行核算；CR3 游标合法（九步全过、不得关闭检查、仅读取循环内注入、磁盘游标不改）；CR3 固定 `δ=+1` 且 P2 只选 Token 数 ≥ 3 的行；P2 搜索区间 [600,900)、找不到 `BLOCKED(schedule)`、以实际流位置严格递增为升序判据；哈希链零起始 `H_{j+1}=SHA256(H_j ‖ block_hash_j)`、原始 32 字节摘要。**状态：`D1 PRE-FLIGHT R2 PROPOSED / PENDING CHATGPT RE-REVIEW`；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED；无下载、无 Tokenizer 拟合、无模型实例化、无训练、无 GPU。** 下一条唯一指令：等待 ChatGPT 复审与项目负责人明确授权；授权前不得执行 D1。

**最新 D1 预飞行 R1 修订检查点（2026-10-26；优先于下方 D1 v1 检查点）：** 基准 `ab6d8271f30cb49e097f3979e29f42bf0e96d545`。新增 `research/mini_mythos/docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL_R1.md` 修订 v1 的验收逻辑矛盾（v1 原文保留，凡冲突以 R1 为准）：LR/CR 两类负例、`d1_cursor_v2` 与 9 步游标校验、预先确定且升序的中断点 P1–P5（空 carry 合法）、序列化/哈希链/尾部核算、Tokenizer 行为冻结，并勘误 F3-A 参数量公式 `P(V)=206,976+320V`。**状态：`D1 PRE-FLIGHT R1 PROPOSED / PENDING CHATGPT RE-REVIEW`；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED；无下载、无 Tokenizer 拟合、无模型实例化、无训练、无 GPU。** 下一条唯一指令：等待 ChatGPT 复审与项目负责人明确授权，再先提交 D1 执行脚本冻结提交。

**最新 D1 预飞行方案检查点（2026-10-26；优先于下方所有旧“下一步”与“Claude Code 暂缓”）：** 项目负责人 2026-10-26 决定由 **Claude Code 接替 Grok** 担任主要研发工程师，ChatGPT 继续独立审核。Claude Code 在 `326121990cef4064d2c2d6cdc48a0d53da3cab3e` 之上提交 `research/mini_mythos/docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，冻结 `Salesforce/wikitext` / `wikitext-2-raw-v1` / `b08601e04326c79dfdd32d625aee71d232d685c3`、train-only ByteLevel BPE（目标词表 4096，实际值待测）、单进程行/Token 游标恢复、N1–N5 负例与停止标准，并记录 D2 词表 128→4096 的参数量冲突。**状态：`D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW`；D1 未 PASS、未 CLOSED、未获执行授权；D2/D3 NOT TESTED；无下载、无 Tokenizer 拟合、无训练、无 GPU。** 下一条唯一指令：等待 ChatGPT 审核与项目负责人明确授权，再先提交 D1 执行脚本冻结提交。本沙箱无法访问 `huggingface.co`，D1 需在有 HF 访问的 CPU 环境执行。受保护文件 `gate2_1/TEST_RESULTS.json` 不在此环境，未触碰。

**最新 F3-B 设计审核检查点（2026-10-25；优先于下方所有旧“下一步”）：** Grok `103344e47184735e03727d062ce81cbae6632e47` 完成五份真实数据、数据流恢复、模型评估、D1/D2/D3 门禁与交接设计文件。ChatGPT 正式报告 `research/mini_mythos/docs/F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md`：**F3-B DESIGN DELIVERABLES PASS/CLOSED（仅设计文档交付）；D1 DRAFT / NOT FROZEN / NOT AUTHORIZED；D2/D3 NOT TESTED；无新训练。** 下一条唯一指令：Grok 只读完成 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，锁定 `Salesforce/wikitext` + `wikitext-2-raw-v1` + `b08601e04326c79dfdd32d625aee71d232d685c3`，规范 train-only BPE/真实词表、split/row/token cursor、有限恢复对照与跳/重/错位负例。D2 vocab128→4096 会改变模型参数量，不可直接沿用旧 247936 参数声明。**当前禁止实际下载/Tokenizer 拟合、CPU 真实数据实验、语言模型训练和 GPU；执行 D1 要另获项目负责人明确授权。** 旧 F3-A PASS/CLOSED 仍限于固定微型训练，R2 metadata/local synthetic PASS 不等于真实行恢复。

**当前最终 F3-A 研发生效状态（2026-10-25，优先于所有下方旧检查点）：** Grok 的最后三项异常恢复对照在 commit `dd36b939457a6c6197b0026fe38854c4edd05365` 归档，ChatGPT 正式独立审核在 `research/mini_mythos/docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md` **批准 F3-A 冻结研究性 Parcae CPU AdamW 六步训练/断点恢复生命周期 PASS/CLOSED（仅该固定微型范围）**。生产 `scripts/train.py`、MuonAdamW、真实 DataLoader 恢复、GPU **NOT TESTED**；旧 R1 训练 loader 未自动合并本次 checked loader 的所有严格条件。新会话首先读取该正式审核、最新 `PROJECT_MAP.md` 和 `PROJECT_STATUS_20261025.md`，再以 Git HEAD 确认状态。**停止一切新 F3-A 微型测试**，下一步只读研究真实数据训练/heldout/效率公平基线的独立验收设计；未经用户批准不得启动下一阶段数据训练/GPU。上次 RUN_META Python=3.10.21 而命令=/usr/bin/python3.11 的出处矛盾，保持 NOT VERIFIED 并做只读勘误。

**最新 F3-A-R1 独立审核（2026-10-25）：** Grok 已先提交 R1 冻结补充 `8ea2d674404c44f5887fd248ef25a33c1a622727`，后执行并归档 `14974c8e2a6ad11bea7b45df4242b5acbad3abfe`。ChatGPT 正式审核 `research/mini_mythos/docs/F3A_R1_CHATGPT_INDEPENDENT_REVIEW_AND_FINAL_DELTA_GATE_20261025.md`：六步正常 CPU AdamW 训练及恢复后的 A/B 权重、优化器摘要、三类 RNG、LR **限定 PASS/CLOSED**；完整 F3-A **PARTIAL / NOT CLOSED**，只剩内容级 scheduler 异常不拒绝、合法错误 RNG 未测试、所谓 bad_shape 实际是删键三项。下一步仅限现存 checkpoint 的这些异常状态校验，不重跑整个六步训练、不增加 GPU/新模型/数据规模。**本段优先于下方旧 F3-A 审核进度叙述。**

**最新 F3-A 审核检查点（2026-10-25）：** 用户已授权原生 Parcae CPU 完整训练生命周期实验，Grok 冻结配置 `34c4414667e939560cae69c0a2dc58fca14f9ef5` 并执行 `3b582c7ac8c4ac7e4473d48ee78e05b5326b8026`。独立 ChatGPT 审核 `research/mini_mythos/docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md` 判定 **F3-A PARTIAL POSITIVE / NOT CLOSED**，需补真实 RNG/optimizer/scheduler/step 对照与坏 checkpoint 加载拒绝；原始数据不覆盖。旧文中“完整 CPU 训练未授权/未执行/只有设计草案”是过期历史；完整 **PASS/CLOSED 仍未获得**。本项目仍禁止 GPU、上游源码变更和自动规模训练。

**最新负责人变更（2026-10-25）：** 用户已决定继续使用 **Grok** 做主要代码开发/CPU 研究，**ChatGPT** 独立审核，**Claude Code 暂缓接管**。R3 历史审核文件名中的 `CLAUDE_HANDOFF` 仍是必须读取的技术验收证据，但旧文中的“Claude 接管”已被最新用户授权覆盖。Grok 已完成 F2-E 最终限定证据收口，ChatGPT 独立审核批准 **F2-E E1–E5 PASS/CLOSED（仅限冻结的 CPU 微型采样/Mask/重复/Checkpoint 范围）**；E6 仍 **INCONCLUSIVE**，不得将整个 F2-E 标成全通过。Grok 继续负责下一阶段原生 CPU Training Lifecycle 的**只读审计/验收方案设计**；没有授权新完整训练执行、GPU 或架构改动。最新总览：`research/mini_mythos/docs/PROJECT_STATUS_20261025.md`，最新独立接受文件：`research/mini_mythos/docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`。

## 0. STOP 条件

未读最新 Git 状态、未明确本轮授权范围、无法确认冻结实验门禁时，**只允许只读调查与报告**；禁止 GPU、训练、修改原生 Parcae/AxoNN、清理工作区、覆盖实验原始证据。任何 AI 报告的 PASS 都必须经过证据审核。

## 1. 每次新会话启动的必读顺序（不得跳过）

1. 确认仓库 `leotree2020/OpenMythos`、当前活动分支、`git rev-parse HEAD`、`git status --porcelain=v1`、`git remote -v`。不要从旧文档猜当前 HEAD。
2. 读取 **`research/mini_mythos/docs/SESSION_START_PROTOCOL.md`（本文件）**。
3. 读取 **`research/mini_mythos/docs/PROJECT_MAP.md`**，掌握核心模型/训练/实验/测试/文档五模块的范围、代码量基线、PASS/问题/未开始事项；核对统计基线是否落后于 HEAD。
4. 读取 **`research/mini_mythos/backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`**（历史备份基线）；再查找/读取**最新**阶段检查点和对应验收门禁，不得把 2026-10-25 的备份误当作永远最新。
5. **阶段历史与最新门禁**：保留 F2-E B1/R1/R2/R3 历史冻结验收，最新 F2-E E1–E5 限定 CLOSED / E6 INCONCLUSIVE。F3-A 初始冻结、B1/R1 及历史 R1 审核均只作为研究历史；**当前最新强制读取**：`research/mini_mythos/docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`、`research/mini_mythos/docs/PROJECT_STATUS_20261025.md`、`research/mini_mythos/docs/PROJECT_MAP.md`。F3-A 冻结微型 CPU 生命周期已经限定 CLOSED，下一步为真实数据、数据流恢复和公平评测的只读方案设计。Grok 继续实施，ChatGPT 独立审核，Claude Code 暂不接管。
6. 检查原生 Parcae pin `69284c13746e849104f738d6d1a347b1f457df76`、AxoNN pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`、Python/Torch/CPU 版本、实际工作树 dirty 状态。若无环境访问，明确写 **NOT VERIFIED**，不假装已执行。
7. 对本轮计划填写：目的、适用范围、环境、输入/种子、预期与容差、实际观察、证据路径/哈希、PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT TESTED、Git 变更、未解决问题、下一条唯一指令。执行前明确当前授权；不要自动扩展任务。

## 2. 启动时必须给用户的简报格式

```text
[Mini-Mythos 新会话启动检查]
仓库/分支/HEAD：
工作区状态（dirty 文件；无法读取则 UNKNOWN）：
五模块项目地图基线：Commit / 文件数 / bytes / LOC（未实测写 NOT MEASURED）：
核心模型：已验证 / 问题 / 未开始：
训练：已验证 / 问题 / 未开始：
实验：已验证 / 问题 / 未开始：
测试：已验证 / 问题 / 未开始：
文档：已验证 / 问题 / 未开始：
最近正式验收：PASS/CLOSED 与其适用范围：
当前阻塞：PENDING/FAIL/BLOCKED/INCONCLUSIVE：
本轮授权任务：
拟执行的最小实验及验收标准：
需要保护的文件：
下一条唯一指令：
```

## 3. 五条不可变研发规则

1. CPU 优先，GPU 按需；GPU 需单独明确授权和预算/风险门禁。
2. 实验先冻结目的、环境、输入、预期、容差和 PASS/FAIL/BLOCKED/NOT TESTED，保留实际和证据；命令 Exit 0 不是 PASS。
3. 原版 Parcae/AxoNN 源码不改；上游先复现；OpenMythos 研究变更隔离；不因 Tiny 实验失败擅改循环 Transformer。
4. ChatGPT 与 Grok/其他 Agent 交叉审核；不一致时保留分歧并做最小受控实验。
5. 阶段结束必须 Git 检查点：结果、HEAD/status、依赖、风险、原始证据、下一条指令。

## 4. 当前特别保护

- **不得触碰**旧 Codespaces 中可能存在的未提交 `research/mini_mythos/gate2_1/TEST_RESULTS.json`；先人工备份实际字节和哈希。
- 禁止对未知 dirty 工作区运行 `git reset --hard`、`git clean -fd` 或任何覆盖/删除指令。
- F2-E B1/B1-R1/B1-R2/B1-R3/closeout，以及 F3-A B1/R1/final 原始实验与二进制 Checkpoint 全部不可覆盖。保护本地报告 dirty 的 `gate2_1/TEST_RESULTS.json`，禁止 reset/clean。已冻结 CPU F2-E E1–E5 与 F3-A 限定 CLOSED，不继续追加微型测试；转向只读真实数据方案。
- 旧 GitHub 备份分支 `backup-mini-mythos-20261025-f2e-r1-pending` 是历史锚点，不在上面开发。
- 本 SOP **仅确认 F2-E E1–E5 和 F3-A 微型 Parcae CPU 训练生命周期在各自冻结范围 PASS/CLOSED**。E6 仍 INCONCLUSIVE；上游完整 `scripts/train.py`、MuonAdamW、真实数据恢复、模型能力、GPU 不因此 PASS。新数据训练必须额外授权，GPU 还须 Gate 2.2-C。

## 5. 每次会话结束必须更新

- 最新五模块变化：文件数、真实扫描 LOC（若执行了）、状态变化、证据来源；未测量保留 NOT MEASURED。
- 本轮 Git HEAD、commit、dirty、依赖和环境。
- 每个实验的预期/实际/结论和独立审核状态。
- 明确下次唯一任务和停止条件；写入新的阶段检查点，必要时更新 `PROJECT_MAP.md`。
- 在完成交接检查点之前不得将本阶段称为 CLOSED。

**短启动指令：**「先执行 `SESSION_START_PROTOCOL.md`，读取 `PROJECT_MAP.md` 和最新阶段检查点，汇报五模块状态与 Git/dirty/阻塞点；未经确认不要执行实验。」 

