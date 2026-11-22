# code-reviewer final report, round 9, v1.1 freeze commit 87a244db28a901f9e89282b50df76778ab5c2887 (parent 8a49c087); invoked 2026-11-22 10:13 UTC (background); invocation text: code-reviewer_prompt.txt; input: review_input.diff
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-af49df825ac8f6064.jsonl)
---
## code-reviewer 审查：Metrix E1-PILOT 第 9 轮 v1.1 冻结提交 87a244db28a901f9e89282b50df76778ab5c2887

结论：PASS。13 项都与指令一致，没有 BLOCKER。另登记 1 条 MAJOR（不确定是否为问题）和 7 条 MINOR，都只登记、不修。

开头与范围：我已先读仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，以它为完整定义（tools: Read, Grep, Glob）。本审查没有运行任何命令，只用 Read、Grep、Glob 读取 /home/user/OpenMythos 的工作区文件和 .git 下的文本文件。

### 证据的链接方式（先说明）
- **直接读取的部分（已验证）：**
  - `.git/refs/heads/claude/protocol-v1-1-errata-46z4jc` 第 1 行为 87a244db28a901f9e89282b50df76778ab5c2887。
  - `.git/logs/HEAD` 第 5–7 行显示：分支由 155430a 重置到 8a49c087，随后只有一个提交 8a49c087 → 87a244db，时间戳 1795342324，即 10:12:04 UTC。
  - 协议、三个 JSON、metrix/CLAUDE.md、data-auditor.md 的内容，我都直接读取了工作区文件。
- **工作区内容等于提交内容这一点（未验证）：**
  - 已提交的 t1_protocol_checks.txt 第 19–26 行记录了提交前工作区的 sha256，与 t5 第 26–29、38–40 行用 git cat-file 读出的 87a244db 的 sha256 相同。
  - preflight_tools_check.txt 第 18–21 行显示，已跟踪文件没有未提交的改动。
  - 但 t5 和 preflight 都还没有提交。所以凡是依赖“工作区 = 87a244db”的判断，严格说都属于未验证。

### 逐项一致性

| 项 | 判定 | 验证状态与证据 |
|---|---|---|
| 0 比对 ~/.claude/ 副本与分支文件，做法同第 7 轮；首句按第 5 节固定 | 一致 | **已验证**。<br>- t0_copy_check.txt 第 15–18 行：HEAD 与 origin 都是 8a49c087。<br>- 第 44–50 行：sha256；第 57–82 行：三组 diff。<br>- 第 83–93 行：各提交的 git show 哈希。<br>- 第 97–142 行：两个 agent 的 frontmatter 与 tools 行都相同。<br>- 命令集与 reports/round7/t0_copy_check.txt 第 6–114 行相同，另多比对了 data-auditor 的 frontmatter。<br>- 首句：code-reviewer_prompt.txt 第 1 行、data-auditor_prompt.txt 第 1 行与 metrix/CLAUDE.md 第 45 行的固定句逐字相同（我直接读取，但这两个文件尚未提交）。 |
| 1a G0.8 | 一致 | **已验证**。<br>- 用完整原句做正则 Grep：METRIX_E1_PROTOCOL.md:543 命中 1 处，ROUND9_TASKS.md:15 命中 1 处，文字逐字相同。<br>- 第 14 节规定的原因“v1 补充 a 的指令措辞使原条整条被替换，丢失复评对象与 NLL 容差”在 :701，Grep 命中 1 处。<br>- 全文中 G0.8 只在 :543、:570、:696、:701 出现，没有残留旧口径。 |
| 1b ST12 比对范围 | 一致 | **已验证**。<br>- :624 写明了指令要求的 (1)、(2) 两项，以及“第 8 节第 1 步写入 manifest 的实际哈希字段不在比对范围内”。<br>- 括注里的两个字段确实存在：DATA_MANIFEST.json:245 的 `"files"`、SPLIT_MANIFEST.json:394 的 `"split_sha256"`（值都是 null 或 NOT_GENERATED）。<br>- 第 8 节第 1 步（:519）写的是“把哈希写入两个 manifest 并提交”。 |
| 1c fact 哈希比对方法 | 一致 | **已验证**。<br>- :86 写明：从 facts.jsonl 读出 fact 列表，按第 2.2 节和第 0 节（:45）的 JSON 规范化方法重算，与 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 比对。<br>- 该值与 :85、PROTOCOL_FROZEN:39 相同。 |
| 1d 第 1 节 margin 措辞 | 一致 | **已验证**。<br>- :55 写明 dNLL ≤ +0.03、Owner 批准 05:27 UTC、只报告不进门槛，与第 13 节 :638、:641 一致。<br>- 说明：v1 的第 1 节原文已经不含“待 Review Gate”（v1-r8 在 :694 已改为“margin 见第 13 节,在 Pilot 中只报告”，旧行见 t1 第 69–70 行）。这次把现有的 margin 引用改成了已批准的表述，符合指令本意。 |
| 1e 版本 v1.1、JSON 同步、状态 | 一致 | **已验证**。<br>- 标题 :1、状态行 :6 为“PROTOCOL_FROZEN（v1.1）”。<br>- 三个 JSON 第 3 行为 `"version": "v1.1"`，内联副本 :298 也是 v1.1，`status` 仍为 PROTOCOL_FROZEN。<br>- t1 第 34–40 行：三个 JSON 与 6a474e4a 相比，只有 `/version` 从 v1 改为 v1.1，内联副本一致。<br>- t1 第 16–17 行：8a49c087 的协议和三个 JSON 与 6a474e4a 相同。<br>- Grep `"v1|version` 只命中三个 version 行。 |
| 全部记入第 14 节 v1.1 行并写明规定的原因 | 一致 | **已验证**。<br>- :701–705 共 5 行，都以“冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验”开头（Grep 计数 5；t1 第 59 行“5 of 5”）。<br>- t1 第 60–82 行：第 14 节之前只有 1a–1e 对应的 7 处改动；第 84 行：第 14 节“added 7 \| removed 0”。<br>- t1 第 28–30 行：table_check 结果 PASS。 |
| 2a 第 2 节状态 | 一致 | **已验证**。metrix/CLAUDE.md:21。 |
| 2b 第 4 节 | 一致 | **已验证**。<br>- :35 第一条原文不变；:36 只把末句“实测预计超过 3 小时即停下报告。”换掉，符合 ROUND9_TASKS.md:48 中 Owner“只换 3 小时那句”的回答。<br>- 数值与协议一致：ST11（:623）3.5 小时，ST7（:619）4 小时。 |
| 2c 第 8 节 1e 补注作用范围 | 一致 | **已验证**。metrix/CLAUDE.md:62 末尾为“（作用范围：永久。出处：Review Gate 第 8 轮裁决，Owner 批准，2026-11-22 09:44 UTC；…）”。 |
| 各条注明出处与作用范围 | 一致 | **已验证**。<br>- t1 第 91–94 行：精确出处串只命中 :21、:36、:62 三行。<br>- 作用范围依次为本阶段、本阶段、永久，与 ROUND9_TASKS.md:48 的 Owner 回答及 :24 一致。 |
| 3 data-auditor.md TEST 禁令 | 一致 | **已验证**（git add -f 一项除外）。<br>- .claude/agents/data-auditor.md:12 与 ROUND9_TASKS.md:27 的指令原文逐字相同（正则 Grep 各命中 1 处，文件中多一个句号）。<br>- t3_data_auditor_frontmatter.txt 第 22–24 行：改动前记录了 tools 行。<br>- 第 20、67 行：frontmatter 的 sha256 改动前后都是 65fcca0c…；第 70、76 行：与 HEAD 比 frontmatter 和 tools 行都未变；第 85 行：numstat 为 1 1。<br>- “用 git add -f”：**未验证**，原始输出中没有记录 git add 命令本身。改动已进入提交，这一结果与是否加 -f 无关。 |
| 4 第 1–3 项在同一个提交里 | 一致 | **部分已验证**。<br>- .git/logs/HEAD 第 7 行（已验证）：8a49c087 之后只有 87a244db 一个提交。<br>- 提交含全部 6 个文件：t5 第 9–23 行、review_input.diff 第 26–37 行，两者都未提交，属**未验证**。 |

另：ROUND9_TASKS.md 是否“照录全文”，我无法与 Owner 的原始消息核对，**未验证**。

### 登记的问题（只登记不修）

MAJOR | metrix/e1-pilot/METRIX_E1_PROTOCOL.md:624 | ST12 比对范围 (1)“数据内容哈希”的覆盖范围不清。按第 0 节 :45 的术语，canonical 哈希标识内容、byte 哈希标识文件，“内容哈希”可以读成只含规范化哈希。这样 PROTOCOL_FROZEN:41、:45–50 所列的锚文本源 parquet、Qwen 4 个分词器文件、parcae tokenizer.json、eval_sets.jsonl 这些文件哈希就可能落在 ST12 之外。不确定之处：读者是否会这样读；文字与指令原文一致 | “(1)`PROTOCOL_FROZEN` 中列出的数据内容哈希” | 下一版本写明 (1) 指 PROTOCOL_FROZEN“全部数据哈希”表的全部行（含文件哈希）。未验证。

MINOR | metrix/e1-pilot/METRIX_E1_PROTOCOL.md:624 | 现在有 v1、v1.1 两个冻结提交（状态行 :6），(2) 中的“冻结提交”没有指明是哪一个。与指令原文一致 | “(2)冻结提交下本协议文件与三个 JSON 的原始字节哈希,用 `git cat-file` 从冻结提交读取” | 写明“当前有效版本的冻结提交”（第 6 项会在 PROTOCOL_FROZEN 开头写“当前有效版本：v1.1”，可以与此对应）。已验证（文字）。

MINOR | metrix/e1-pilot/METRIX_E1_PROTOCOL.md:575 | 第 9 节 BLOCKED 一行仍照搬 ST12 旧的条件文字，没有带上新加的比对范围，只能靠括注“(ST12)”间接受限 | “或任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致(ST12)” | 下一版本改为“ST12(比对范围见第 11 节)”。已验证（文字）。

MINOR | metrix/e1-pilot/DATA_MANIFEST.json:5、SPLIT_MANIFEST.json:5、SEARCH_SPACE.json:5、METRIX_E1_PROTOCOL.md:300 | `version` 已是 v1.1，`frozen` 仍是 v1 的批准时间，单独读 JSON 时看不出 v1.1 何时批准。与指令“版本字段同步”和 :705 一致 | `"version": "v1.1"` 之下为 `"frozen": "Owner 批准，2026-11-22 05:27 UTC"` | 登记，下一版本考虑。已验证。

MINOR | .claude/agents/data-auditor.md:12 | 新规则用了“读取”“统计”两个词，但没有引用协议第 3 节 :158 对“读取 TEST 数据”的定义（计数、对整个文件求哈希不算读取）。规则一律禁止“统计”，与协议口径不同。例如本轮要求对含 test 行的 eval_sets.jsonl 整个文件求哈希（data-auditor_prompt.txt:10），算不算“统计 TEST”不明。文字与指令逐字一致 | “其余时候一律禁止生成、读取或统计 TEST。” | 登记，由 Review Gate 决定是否引用第 3 节的定义。已验证（文字）。

MINOR | metrix/e1-pilot/reports/round9/v11_checks.py:77-90 | `want` 只检查以某前缀开头的行恰好有 1 行，不检查 1a–1d 的内容。旧版第 1 节 margin 行、旧版 G0.8 行同样能通过，所以 RESULT: PASS 不能证明内容与指令一致，内容只能靠打印出来人工比对。本审查已用逐字 Grep 独立核对 | `"section 1 margin": lambda s: s.startswith("- 不对 general damage 下 non-inferiority 结论")`、`ok &= len(hits) == 1` | 登记；以后的检查脚本对目标文字做全等比对。已验证（读代码）。

MINOR | metrix/e1-pilot/reports/round9/t3_data_auditor_frontmatter.txt:34 | 注释说 .gitignore 规则使 `git add -f` 成为必需。但第 31–33 行显示该文件已被跟踪，而 git 对已跟踪文件通常不需要 -f 就能暂存改动。原始输出也没有记录实际执行的 git add 命令 | “rerun with --no-index to show the ignore rule that makes git add -f necessary.” | 登记；以后在原始输出中记录 git add 命令本身。未验证。

MINOR | metrix/CLAUDE.md:35-36 | 第 4 节第一条已写“上限 4 小时”，新句又写“累计 GPU 时间超过 4 小时即停（协议 ST7）”，两处重复；而且“即停”没有带上 ST7 的“报告进度”。这符合 Owner“只换 3 小时那句、其余保留”的回答 | “…上限 4 小时。…”／“…累计 GPU 时间超过 4 小时即停（协议 ST7）。” | 登记。已验证（文字）。

### 相关文件
- /home/user/OpenMythos/metrix/e1-pilot/tasks/ROUND9_TASKS.md
- /home/user/OpenMythos/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
- /home/user/OpenMythos/metrix/CLAUDE.md
- /home/user/OpenMythos/.claude/agents/data-auditor.md
- /home/user/OpenMythos/metrix/e1-pilot/reports/round9/t0_copy_check.txt、t1_protocol_checks.txt、t3_data_auditor_frontmatter.txt、v11_checks.py、t5_frozen_hashes_87a244db.txt（最后一个尚未提交）
- /home/user/OpenMythos/metrix/e1-pilot/reviews/87a244db28a901f9e89282b50df76778ab5c2887/（review_input.diff、preflight_tools_check.txt、两份 prompt，均尚未提交）

结论：PASS
