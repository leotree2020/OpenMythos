# Metrix E1-PILOT Implementation 阶段 B:Owner 下达阶段 B 时的消息(原文)

- 来源:Project Owner 在 Claude Code 会话 session_01J5mxaWPrK8siadYKyqZ5pX 中下达,2026-11-23(本阶段第 0 步写于 01:55:15 UTC,`reports/impl_b/t0_remote_check.txt`)。
- 下面照录该消息全文。

---

读 metrix/CLAUDE.md、metrix/e1-pilot/tasks/IMPLEMENTATION_TASK_ORDER_V1.md 与 reports/IMPL_A_REPORT.md。执行第 10 节阶段 B。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不得 force push，不推送标签，不经 PR。

0. 第一步：用 git ls-remote 核对远端分支与两个标签，把输出连同 reports/impl_a/t8_report_push.txt（如果还在）作为证据文件提交，不需要审查。以后每个阶段都用这种方式核对推送结果。

Review Gate 对阶段 A 的裁决（记入 IMPL_B_REPORT.md，作用范围：本阶段）：
1. 工作区冻结文件与冻结提交比对、以及无冻结哈希的数据文件与重新生成结果比对：都同意；不一致按 ST12 处理，状态为 BLOCKED。
2. L2 两模板都不足 4 词时 Jaccard 按 0 计：同意。
3. Y/F token 比每序列加 1 个 <|endoftext|>：同意；报告中同时给出加与不加该 token 的两个比值，并证明都在 [0.80, 1.25] 内。
4. 版本比对忽略本地标签（如 +cu130）：同意。阶段 C 须处理 CUDA 构建兼容性（见任务书第 8 节，Review Gate 补充：若官方提供 torch 2.11.0 的 CUDA 12.x 构建，另锁一份并带哈希；RUNBOOK 写明租用前如何确认驱动版本及选用哪份锁定文件；一次 Pilot 只用一种构建并记入实验记录）。

阶段 B 额外要求（在任务书第 6 节之外）：
5. 自实现的 LoRA：单元测试证明前向输出等于 W·x + (alpha/r)·B·A·x 的手算结果；只有 LoRA 参数可训练，base 参数全部冻结且训练后哈希不变。
6. arm A 的 KL：单元测试证明方向为 KL(p_base ‖ p_θ)，按 token 加权，与协议第 4 节一致。
7. F 与 A 为全参数训练，L 只训练 LoRA 参数；测试核对每个 arm 可训练参数的数量。

阶段 B 结束后停下，提交报告，等待阶段 C 指令。
