读 metrix/CLAUDE.md、tasks/IMPL_C4_RULING.md、RUNBOOK_A100.md、reports/DEFERRED_MINORS.md 1.38 与 1.42 节。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不推送标签，不经 PR。本段原文入库为 tasks/IMPL_C5_RULING.md。

Review Gate 裁决（2026-11-28，作用范围：E1 Pilot 直至结束）：
1. pilot.py 中 4 处过时注释：不改，登记。正式运行之前不再提交任何代码改动。
2. 做一次纯文档提交，按 DEFERRED_MINORS 中各条「处理应为」修正 RUNBOOK：CL2、CL3、CL4、CL5、CL6、CP1、CP2、CP3、CP4。另在 RUNBOOK 第 4 节加一条总则：「任何命令以回溯或非 0 退出码结束，或出现本手册没有写到的情况：不重跑、不修补，保留输出，报告 Owner。」
3. CP5：确认。主机有 CPython 3.13.18 但不能建 venv（缺 ensurepip）时，同样用 uv 安装该精确版本；第 1 节与 3.0 的说明同步。
4. 本次提交只送 code-reviewer 一轮：有 BLOCKER 则修复后再送，否则直接提交；新的 MAJOR、MINOR 只登记。不改 src/、tests/、run_pilot.py。
5. 完成后状态仍为 IMPLEMENTATION_READY，停下。
