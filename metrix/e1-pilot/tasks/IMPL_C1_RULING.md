读 metrix/CLAUDE.md、tasks/IMPLEMENTATION_TASK_ORDER_V1.md、reports/IMPL_C_REPORT.md（C1 节）。如果工作区没有 C1 的代码，以 reviews/tree-9be4df2a…/input_round3.diff 为起点恢复。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不推送标签，不经 PR。

Review Gate 对 C1 的裁决（2026-11-25，作用范围：本阶段；原文连同本段入库为 tasks/IMPL_C1_RULING.md，并记入 IMPL_C_REPORT.md）：

防范对象：TEST 闸门要防的是「按规则办事的 Executor 在按 RUNBOOK 操作时，意外评测 TEST 两次，或在 ST10 不成立时评测 TEST」；不防有仓库写权限者的故意篡改（改写历史、伪造记录），这类风险由 GitHub 分支保护和审查记录承担。审查按此范围判定：范围外的边缘情况记为 MINOR 并登记，不作为 BLOCKER。调用两份审查时，把本段防范对象原文写进调用文字。

1. 采用 (a)：所有 TEST 路径都必须在 metrix-e1-pilot-protocol-v1 的检出上运行，且 HEAD 等于 fetch 后远端该分支的最新提交，否则 BLOCKED。标记检索简化为只查两处：工作区，以及远端该分支最新提交的文件树；任一处存在即拒绝。删除对 reflog、侧分支、标签和其他引用的检索。
2. 采用 check_commit_preconditions，由 begin、finish 与 TEST 驱动共用，在生成 TEST 之前检查。生成之后真实推送仍被拒绝：视为 TEST 已生成，禁止重跑，状态 BLOCKED，报告 Owner；由 Owner 决定是否批准把 ST10 记录这一个文件手工提交。
3. B25 接受：checkpoint 哈希 = train.state_sha256。在 interpretations 中写明其计算定义，status 设为 ACCEPTED（Review Gate 2026-11-25），使 pending() 为空。C2 冒烟测试中保存并重载 checkpoint，证明哈希不变。
4. 拒绝时的状态词按 Executor 提案（报告待决第 4 项）接受。
5. data-auditor 可以把 Executor 的探针当作驱动子进程运行，但预期结果须由它独立算出。
6. 远端保护：Owner 已在 GitHub 上为该分支设置禁止 force push 与删除、允许直接推送。metrix/CLAUDE.md 第 6 节的「受保护分支」指 main；在本分支直接快进推送为既定做法。只能经标签到达的标记、主机名比对，均不处理。RUNBOOK 写明这项 GitHub 设置。
7. 被取代的试跑输出按现行方式入库：接受。
8. 停止提交属于证据提交，不需补审。
9. C1 按上述修改后重新送两份审查，轮次从 1 重新计。DEFERRED_MINORS 1.29 中属于防范对象以外的项登记，不修。

C1 提交后继续 C2（run_pilot.py 与 CPU 冒烟测试）、C3（RUNBOOK_A100.md 与最终报告）；额度不足时在段落之间停下。阶段 C 全部验收通过后停下，状态写为 IMPLEMENTATION_READY。
