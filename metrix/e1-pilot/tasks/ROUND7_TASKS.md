# Metrix E1-PILOT 第 7 轮指令(原文)

- 来源:Project Owner 在 Claude Code 会话 session_01J5mxaTx8SWDUGRUNbxcnqu 中下达,2026-11-22(会话创建于 03:11:08 UTC)。
- 共两段:第一段是本轮指令;Executor 在第 0 步停下报告后,第二段是 Review Gate 的裁决。下面照录全文。
- 第二段的“选项 3”指 Executor 停下报告时列出的第 3 种做法:在本会话继续,沿用已加载的旧定义,在调用文字里写明须按仓库中的定义执行。第 0 步的比对原始输出见 `reports/round7/t0_copy_check.txt`(提交 `fe321cd`)。

---

## 第一段:本轮指令

读 metrix/CLAUDE.md。本轮是冻结补丁：只执行下列已定的修改，不开放新的设计问题。允许快进推送 metrix-e1-pilot-protocol-v1，不得 force push。

0. 先比对 ~/.claude/ 下的副本与分支上的文件。规则文件不一致：以仓库为准并在报告中注明；agent 定义不一致：停下报告。
1. 协议修改（全部记入第 14 节）：
   a. 第 2.7 节改为「不得共享任何词 13-gram（定义与上限见第 3 节 L6）」。
   b. L6 的 TEST 部分：时机为「第 8 步生成 general_test.jsonl 之后、TEST 评测之前」；计数为跨全部文档的共享词 13-gram 种类数，上限 0；由 Executor 与 data-auditor 各自计算，结果须一致。
   c. L3–L6 任一项的 TEST 部分超限：停止，不评测 TEST，状态记为 BLOCKED，报告 Owner。
   d. G0.1 改为「L1–L6 中涉及 TEST 的部分在 Gate 0 不要求，按第 8 步运行」。
   e. n_w 定义为实际送入模型的 id 序列长度（截断后的原始 id，不解码再编码）；锚文档的措辞改为「最多 128 token」。
   f. EM 归一化之前先删除输出中的 <think>…</think> 片段。
   g. 写死第 2.6 节 S 的置换与第 2.5 节候选抽取的随机流 purpose 和调用顺序；用 DATA_SEED 两次独立生成 train_S.jsonl 与 candidates.json，证明逐字节一致，把 canonical sha256 记入 manifest。
2. metrix/CLAUDE.md：第 10 节补全「（出处：Review Gate 第 6 轮裁决，Owner 批准，本阶段，<UTC 时间>）」；code-reviewer 定义中的「未验证」规则补充：「引用仓库中已提交的原始输出（写明路径与行号）的判断视为已验证」。
3. 第 6 轮待决第 6、14 项登记入 DEFERRED_MINORS.md，注明「正式流程代码统一要求不通过时打印 RESULT 并以非 0 退出」。
4. 调用 code-reviewer 与 data-auditor，只审查：修改是否与本指令逐条一致，以及是否存在 BLOCKER。新提出的 MAJOR/MINOR 登记入 DEFERRED_MINORS.md，不修。data-auditor 须独立复现 1g 的两个 sha256。
5. 报告写入 reports/ROUND7_REPORT.md，提交推送，给出 commit hash。报告末尾列出冻结时的全部哈希（fact、锚文本、train_S、candidates、模板、tokenizer、eval_sets、协议文件本身）。

---

## 第二段:Review Gate 裁决(Executor 第 0 步停下报告之后)

Review Gate 裁决：选项 3，在本会话继续执行第 7 轮。

1. 把第 0 步的比对原始输出存为 metrix/e1-pilot/reports/round7/t0_copy_check.txt。这属于证据文件，可以不经 code-reviewer 直接提交，commit message 注明「证据文件，未经 code-reviewer」。
2. 确认两个版本 code-reviewer.md 的 frontmatter（特别是 tools 行）完全相同，把原始输出记入同一文件。如果不同，停下报告。
3. 从本轮起，每次调用审查 subagent，调用文字的第一句固定为：「先读仓库中的 .claude/agents/<名称>.md，以它为你的完整定义；它与你已加载的定义冲突时，以仓库文件为准。」
4. 把第 3 项写入 metrix/CLAUDE.md 第 5 节，注明「（出处：Review Gate 第 7 轮裁决，Owner 批准，本阶段，<UTC 时间>）」，并在同一节写明：两个版本的 tools 行不一致时必须停下，不得用此方法替代。
5. 然后按原指令执行第 1–5 步。
