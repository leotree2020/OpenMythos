# Metrix E1-PILOT 第 4 轮指令(tasks 1–5、7 原文)

- 来源:Project Owner 在 Claude Code 会话 session_01J5mxaVWCGyNj16YJV8cPy5 中下达,2026-11-21(会话开始于约 04:56 UTC)。
- 下面照录第 1–5、7 项与开头一句。第 6 项(审查 subagent 的盲测)没有录入:原文列出了要埋入的 bug 类型,写进仓库会让以后读仓库的审查 subagent 看到;该项的执行情况见 `reports/ROUND4_REPORT.md` 第 6 节。

---

读 metrix/CLAUDE.md。本轮允许快进推送 metrix-e1-pilot-protocol-v1，不得 force push。

1. 按 Review Gate 裁决修改协议：EM 改为从 chat(q) + "The answer is" 贪心解码，输出去掉开头空格后归一化；general damage 与 arm A 的 KL 都不前置特殊 token，t 从 2 起，写明；第 14 节两处提交引用改为具体 commit 与 UTC 时间，并注明宪章第 6 节日期为 JST。全部记入第 14 节。
2. 修复第 3 轮报告「待 Review Gate 决定」第 5 项列出的全部 MINOR，并补定义 s_ST 中的 K'。
3. 在 metrix/CLAUDE.md 第 9 节追加一条：「原始输出一律写入仓库并推送，不留在临时目录；data-auditor 须提交 audit 脚本的完整 stdout。」（Owner 已批准）
4. 把 claude/charming-cerf-hmu4ny 上的 ea9ce1d（t2 更正记录）cherry-pick 到本分支。
5. 对修改后的提交调用 code-reviewer 与 data-auditor，原始输出存入 reviews/<commit-hash>/。
6. (未录入,见上)
7. 报告写入 reports/ROUND4_REPORT.md（第 6 项只写 5 个分支各自的审查结论，不写答案），提交并推送，给出 commit hash。
