# Mini-Mythos / OpenMythos — 新会话强制启动规范（SOP v1）

**适用范围：** 任何新 ChatGPT / Grok / 编程 Agent 对话，包含换模型、额度恢复、重新打开 Codespaces、交接研发。**优先级：** 新会话必须先读本文、项目地图及最新检查点；旧聊天记忆只是线索，不能作为实验事实。

## 0. STOP 条件

未读最新 Git 状态、未明确本轮授权范围、无法确认冻结实验门禁时，**只允许只读调查与报告**；禁止 GPU、训练、修改原生 Parcae/AxoNN、清理工作区、覆盖实验原始证据。任何 AI 报告的 PASS 都必须经过证据审核。

## 1. 每次新会话启动的必读顺序（不得跳过）

1. 确认仓库 `leotree2020/OpenMythos`、当前活动分支、`git rev-parse HEAD`、`git status --porcelain=v1`、`git remote -v`。不要从旧文档猜当前 HEAD。
2. 读取 **`research/mini_mythos/docs/SESSION_START_PROTOCOL.md`（本文件）**。
3. 读取 **`research/mini_mythos/docs/PROJECT_MAP.md`**，掌握核心模型/训练/实验/测试/文档五模块的范围、代码量基线、PASS/问题/未开始事项；核对统计基线是否落后于 HEAD。
4. 读取 **`research/mini_mythos/backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`**（历史备份基线）；再查找/读取**最新**阶段检查点和对应验收门禁，不得把 2026-10-25 的备份误当作永远最新。
5. 对当前冻结工作 F2-E，先读取历史 **`research/mini_mythos/docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`**、**`research/mini_mythos/docs/F2E_B1R1_CHATGPT_REVIEW_AND_R2_GATE_20261025.md`**，最后必须读取当前正式门禁 **`research/mini_mythos/docs/F2E_B1R2_CHATGPT_REVIEW_AND_R3_GATE_20261025.md`**。当前最新审核状态：F2-B/C/D 限定范围 PASS/CLOSED，F2-E-A 设计 PASS/CLOSED，F2-E B1-R2 **PARTIAL / E1–E5 PENDING R3（NOT CLOSED）**，E6 **INCONCLUSIVE**。
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
- F2-E B1、B1-R1、B1-R2 原始证据均不可覆盖；当前唯一获批 CPU 验收修正为最小 R3，新证据只能放 `research/mini_mythos/gate2_2/evidence/f2e/b1r3/`，先读取 R3 冻结门禁。
- 旧 GitHub 备份分支 `backup-mini-mythos-20261025-f2e-r1-pending` 是历史锚点，不在上面开发。
- 本 SOP 的建立不代表 F2-E 已 PASS，也不授权运行 GPU。

## 5. 每次会话结束必须更新

- 最新五模块变化：文件数、真实扫描 LOC（若执行了）、状态变化、证据来源；未测量保留 NOT MEASURED。
- 本轮 Git HEAD、commit、dirty、依赖和环境。
- 每个实验的预期/实际/结论和独立审核状态。
- 明确下次唯一任务和停止条件；写入新的阶段检查点，必要时更新 `PROJECT_MAP.md`。
- 在完成交接检查点之前不得将本阶段称为 CLOSED。

**短启动指令：**「先执行 `SESSION_START_PROTOCOL.md`，读取 `PROJECT_MAP.md` 和最新阶段检查点，汇报五模块状态与 Git/dirty/阻塞点；未经确认不要执行实验。」 
