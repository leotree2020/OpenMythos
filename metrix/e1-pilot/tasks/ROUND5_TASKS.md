# Metrix E1-PILOT 第 5 轮指令(原文)

- 来源:Project Owner 在 Claude Code 会话 session_01J5mxaY5fydMdM6jLDaXWvy 中下达,2026-11-21(会话开始于约 06:26 UTC)。同一段指令先发给了第 4 轮会话 session_01J5mxaVWCGyNj16YJV8cPy5,该会话在 06:26:22 被中断,没有执行。
- 下面照录全文。

---

读 metrix/CLAUDE.md。本轮允许快进推送 metrix-e1-pilot-protocol-v1，不得 force push。

1. 按 Review Gate 第 4 轮裁决修改协议：arm A 的 KL 对 4 篇锚文档的全部 token 按 token 加权平均；EM 遇 151645 或 151643 停止，解码跳过特殊 token；写明 prefix(f) 不含答案前的空格。记入第 14 节。
2. verify_scoring.py 加写死的期望结果：用第 3 轮记录的那条 28 个 token 的打分序列做比对，并演示把 enable_thinking 改为 True 时检查会失败。
3. 把盲测的 5 次调用全文与审查原文提交到 reports/round4/blind/，核对 sha256 与仓库中已记录的一致。
4. metrix/CLAUDE.md：第 9 节追加的规则注明出处「Review Gate 第 4 轮裁决，Owner 批准，永久」；第 10 节信任状态改为「已验证（2026-11-21 盲测 3/3 检出、0 误报；每类仅 1 个样本，PASS 仍须附原始输出）」；第 7 节注明「删除文件」不含会话临时目录，但支撑结论的输出须先提交。
5. 完成 L6 泄漏检查（需要 general_dev 与 parcae 分词器，只下载分词器，不下载权重），由 data-auditor 独立复算。
6. 对修改后的提交调用 code-reviewer 与 data-auditor，原始输出存入 reviews/<commit-hash>/。
7. 报告写入 reports/ROUND5_REPORT.md，提交推送，给出 commit hash。
