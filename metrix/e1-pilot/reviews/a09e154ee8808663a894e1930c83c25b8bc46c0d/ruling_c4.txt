读 metrix/CLAUDE.md、tasks/IMPL_C1_RULING.md、reports/IMPL_C_REPORT.md、RUNBOOK_A100.md。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不推送标签，不经 PR。本段原文入库为 tasks/IMPL_C4_RULING.md。

Review Gate 裁决（2026-11-27，作用范围：E1 Pilot 直至结束）：
1. ST11 改为读「B17 估算 + checkpoint 开销」之和，超过 3.5 小时即停。B17 的解释文字相应修订，status 记为 ACCEPTED（Review Gate 2026-11-27 修订）。ST7 的事前判断不变，TEST 的事前估计不加余量。补测试与变异。
2. C2 待决第 1、3、4、5、6、7 项：全部按现行实现接受，不改代码。
3. A100 上的依赖安装、输入与权重下载属于正式流程；metrix/CLAUDE.md 第 4 节「租卡后只跑正式流程」指不在租用机器上开发调试。
4. 正式运行期间只含输出的手工提交（results/command_output/、audit/、reviews/）按证据提交处理，不经 code-reviewer；此前各项「本阶段」裁决在 A100 运行期间继续有效。
5. 两份 L6 计数不同：ST10，不运行 test-evaluate；Executor 按协议第 10 节模板手写一份 BLOCKED 实验记录，作为证据提交。
6. 主机没有 CPython 3.13.18 时，允许用 uv 安装该精确版本；装不到即停下报告 Owner。
7. RUNBOOK 按 1、3–6 更新，删去「待 Review Gate 决定」的措辞，时长表改为 ST11 读两者之和；另写明在 A100 主机上运行 Claude Code 的前提（从仓库根目录、本分支启动，使两个 agent 定义直接加载）。

代码提交送两份审查，调用文字写入 IMPL_C1_RULING.md 的防范对象原文；只改文档的提交只送 code-reviewer。完成后状态仍为 IMPLEMENTATION_READY，停下。
