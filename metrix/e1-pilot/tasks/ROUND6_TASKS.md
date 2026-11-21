# Metrix E1-PILOT 第 6 轮指令(原文)

- 来源:Project Owner 在 Claude Code 会话 session_01J5mxaY5Chc3QrL468Vrs7f 中下达,2026-11-21(会话创建于 14:24:54 UTC)。
- 下面照录全文。

---

读 metrix/CLAUDE.md。本轮允许快进推送 metrix-e1-pilot-protocol-v1，不得 force push。
原则：只修影响数据、指标、门槛或可复现性的问题；其余 MINOR 只登记不修。报告提交不需要 code-reviewer 审查。

1. 协议修改（全部记入第 14 节）：
   a. L6 的「词」定义为 str.split()，word 13-gram 上限 0；Qwen token 13-gram 只报告。
   b. 第 2.7 节改为「每个窗口最多 256 token，不足则取全长」。
   c. n_x 定义为实际送入模型的 id 序列长度。
   d. EM 写死 do_sample=False 的贪心解码，覆盖 generation_config.json 的采样默认值；「去掉开头空格」并入归一化的去首尾空白。
   e. prefix(f) 前不加任何特殊 token。
   f. L6 的 TEST 部分在 PROTOCOL_FROZEN 之后、TEST 评测之前由 data-auditor 运行一次，只输出计数；G0.1 在 Gate 0 只要求 L6 的 DEV 部分。写入第 8 节。
   g. 定义「读取 TEST 数据」：解码 test 行内容或用其内容做任何计算。解析 split 字段、计数、对整个文件求哈希不算。
   h. DATA_MANIFEST.json 锁定 parcae tokenizer.json 与 eval_sets.jsonl 的 sha256。
   i. 转义协议表格中的 <|endoftext|> 竖线。
2. 脚本：l6_check.py 中「test rows decoded」改为实际计数，判定按 1a；所有检查脚本遇异常须打印 RESULT: FAIL 并以非 0 退出。
3. metrix/CLAUDE.md：第 10 节确认 code-reviewer「已验证」、data-auditor「待验证」，出处「Review Gate 第 5 轮裁决」；code-reviewer 定义追加：「未实际运行就作出的判断须标注『未验证』」。
4. 查明会话启动时 /root/.claude/CLAUDE.md 为何是旧版本，提出修法，不要直接修改环境设置。
5. 调用 code-reviewer 审查工作提交；调用 data-auditor 复算 1a–1c、1h 与 2，并要求它修正 r5_kl_denoms.py 中写死的 128。原始输出存入 reviews/<commit-hash>/。
6. 列出所有「登记不修」的 MINOR，写入 reports/DEFERRED_MINORS.md。
7. 报告写入 reports/ROUND6_REPORT.md，提交推送，给出 commit hash。
