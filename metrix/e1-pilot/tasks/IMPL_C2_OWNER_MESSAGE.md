读 metrix/CLAUDE.md、tasks/IMPLEMENTATION_TASK_ORDER_V1.md、tasks/IMPL_C1_RULING.md、reports/IMPL_C_REPORT.md。C1 已完成（f8139f9）。C2 草稿在分支 wip/metrix-stage-c2，以它为起点。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不推送标签，不经 PR。

Review Gate 裁决（2026-11-27，作用范围：本阶段；记入 IMPL_C_REPORT.md）：
1. TEST 评测调用不 fetch、只在 begin 与 finish 时 fetch：接受。RUNBOOK 写明「begin 到 finish 之间任何人不得推送本分支」。
2. f8139f9 属于证据提交，不需补审。

执行 C2（run_pilot.py 与 CPU 冒烟测试，含保存并重载 checkpoint 后 state_sha256 不变），送两份审查，调用文字写入 tasks/IMPL_C1_RULING.md 的防范对象原文。然后执行 C3（RUNBOOK_A100.md 与最终报告），C3 只改文档时只需 code-reviewer。额度不足时在段落之间停下。阶段 C 全部验收通过后停下，状态写为 IMPLEMENTATION_READY。
