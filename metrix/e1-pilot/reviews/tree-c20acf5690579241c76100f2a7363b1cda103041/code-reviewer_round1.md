# code-reviewer, the only round of the E1-PILOT report erratum (staged tree c20acf5690579241c76100f2a7363b1cda103041, parent 4535fd0985b03f6fcaf3e5f600726bfbaaef3816)
# final report extracted unchanged from code-reviewer_round1_transcript.jsonl by reports/round6/review_extract.py
---
code-reviewer 审查：暂存树 c20acf5690579241c76100f2a7363b1cda103041（HEAD 4535fd0985b03f6fcaf3e5f600726bfbaaef3816，分支 metrix-e1-pilot-protocol-v1）

运行环境：Claude Code subagent 会话，只用了 Read、Grep、Glob，没有运行 git 或任何命令，主机名没有取得。读取对象有两类：/tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/a/a_staged.diff，以及仓库工作区中的文件。下面所说的「逐字相同」，都是把元字符全部转义后用 Grep 做 ^…$ 或整段匹配得到的，相当于字符串相等。

已核对、没有问题的部分：
- A1：13 行门槛单元格（G0.1–G0.10、T1–T3）与 /home/user/OpenMythos/metrix/e1-pilot/METRIX_E1_PROTOCOL.md 第 536–545、556–558 行逐字相同。同一组模式分别匹配协议、报告工作区第 281–290、298–300 行和 diff 的「+」行，都是 13/13。同一行的实测值、出处、代码判定三列在 diff 的「-」行与「+」行中完全相同（13 行 × 2 = 26 处匹配），新增文字中没有竖线，表格列数不变。同一节第 239 行 Expected 一段说门槛「逐条列在下文 Actual 的两张表中」，替换之后这句话成立（PR1 指出的第二处位置）。
- A2：新句与 /home/user/OpenMythos/metrix/e1-pilot/reports/DEFERRED_MINORS.md 第 811 行登记的写法逐字相同（两个文件各 1 处匹配）。git 事实方面：/home/user/OpenMythos/metrix/e1-pilot/reports/pilot_final/run_commits_and_code_check.txt 第 3–4 行在 0a67c2c4..53800ef7 区间内（覆盖三个 code_commit）对所列路径做 diff --stat，结果为空。/home/user/OpenMythos/metrix/e1-pilot/results/step1_record.json 第 113 行与第 416–419 行（`manifests_changed`）记有两个 manifest 由第 1 步写入。协议第 519 行规定第 1 步「把哈希写入两个 manifest 并提交」。以上均已验证，依据是已提交的记录。
- A3：新句与指令逐字相同，接在偏差第 9 项末尾，第 9 项原有文字没有改动。
- A4：/home/user/OpenMythos/metrix/CLAUDE.md 第 21 行、第 63 行与指令逐字相同（工作区和 diff 都匹配）。/home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md 这个路径确实存在。
- A5：文字与指令逐字相同，位于「没有入库的内容」一节（报告第 457–474 行），与报告第 402 行、第 466 行以及协议第 550 行一致。
- A1–A5 要求的改动，diff 中都有，没有遗漏。

问题清单：

MAJOR（不确定） | /home/user/OpenMythos/metrix/CLAUDE.md:63（另见 :21） | 第 8 节新增的一条只写了出处、时间和作用范围，没有写原因。文件头要求「记录原因与时间」。本次 A4 正是因为同类缺陷（PR3）才给第 2 节补上原因。另外，第 21 行只有一个出处括注，却同时对应两次 2026-11-28 的裁决：PILOT_REPORT_ORDER 第 4 项（原句）和本次勘误（路径改写与补注），读者无法区分。路径改写（PR21）的原因也没有写。 | 第 63 行「（出处：Review Gate 裁决，Owner 批准，2026-11-28，永久）」；第 5 行「并记录原因与时间」；第 21 行「（出处：Review Gate 裁决，Owner 批准，2026-11-28；原因：正式运行与报告完成；作用范围：永久）」 | 这段文字是 A4 逐字给定的，Executor 不应自行修改。建议登记，并请 Review Gate 决定是否补上原因、是否把两次裁决分开标注。

MAJOR（不确定） | /home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:14、:451、:474；/home/user/OpenMythos/metrix/CLAUDE.md:21、:63 | 本次勘误依据的 2026-11-28 裁决（A1–A5）原文，在 HEAD 和暂存 diff 中都找不到。因此以下引用在仓库内无法核对：第 14 行的「A1」编号、第 474 行自称的「原文」、第 451 行提到的「Review Gate 的决定记录」。报告第 5 行的「依据」也只列了 tasks/PILOT_REPORT_ORDER.md。不确定之处：Executor 可能打算在之后的证据提交中再把裁决入库。 | /home/user/OpenMythos/metrix/e1-pilot/tasks/ 下没有对应的文件。在 metrix/e1-pilot 中搜索「16:19」（不含 reviews/），只命中报告第 451 行和无关的 reports/impl_c/c2_02_checks_superseded.txt:101。先例是 /home/user/OpenMythos/metrix/e1-pilot/tasks/PILOT_REPORT_ORDER.md:1 写的「本段原文入库为 tasks/PILOT_REPORT_ORDER.md」。 | 建议在本提交或紧接着的证据提交中把裁决原文入库，并在报告的依据行注明。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:300 | 按 A1 逐字替换后，报告中已没有任何地方提到解释 B24，但 T3 的实测值列仍然包含 Acc_CB。原文中「(含 Acc_CB(N),解释 B24)」所提供的出处就此丢失。不过协议「满足 G0.3 的同样范围」本身已经包含 Acc_CB(N)，影响不大。 | 在报告中搜索 `B24`，0 处；第 300 行仍有「Acc_CB 0.2750」；B24 见 /home/user/OpenMythos/metrix/e1-pilot/results/experiment_record_formal_20261128T045921Z.json:214–217（protocol "8 (T1-T3), 9"） | 建议登记。以后可以在出处列或表格下方注明 B24。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:449 | A2 新句的后半句「两个 manifest 由第 1 步…写入哈希字段」只引用了 run_commits_and_code_check.txt，而这个文件里没有出现两个 manifest 的文件名。这件事本身是真的，已验证。 | run_commits_and_code_check.txt 第 6 行只有「2 metrix/e1-pilot」；第 34 行 f6e875a1 的提交说明为 "non-TEST data hashes written into the manifests"；直接证据在 step1_record.json:113 与 :416–419 | 建议登记。正文与 DEFERRED_MINORS.md:811 逐字一致，不要改正文；以后可以补引 step1_record.json 的 `manifests_changed`。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:503（另见 :490、:14） | 「本轮产出」表中关于 metrix/CLAUDE.md 第 2 节的描述已经过时：本提交之后，该句已不等于 PILOT_REPORT_ORDER 第 4 项的原文，第 8 节新增的一条也没有提到。第 490 行的「本提交」指的是最终报告提交，第 14 行又称「勘误提交」，而且没有写 hash，报告中的自指称呼不统一。 | 第 503 行「状态一句按 `tasks/PILOT_REPORT_ORDER.md` 第 4 项改写」；第 490 行「随后提交在本提交的审查记录目录 `reviews/<本提交>/`」；第 14 行「已在勘误提交中」 | 建议登记。以后在报告中加一行勘误记录，写明勘误提交的 hash 和 A1–A5 各自改动的位置。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:451（对照 :441） | 该节导语说明内容「按 `results/command_output/` 与两份实验记录如实列出(时间为 UTC…)」，但 A3 新句的来源是仓库外的决定记录，时间用的是 JST。新句接在「等待期间 GPU 计时不累计」之后，「该有条件批准」与它所指的内容之间隔了一句。换算成 UTC：16:19–16:20 JST 即 07:19–07:20Z，早于 test-generate 启动的 07:20:42Z；17:24 JST 即 08:24Z，晚于结果提交（07:42:43Z）和留存清单（07:47:37Z）。与第 9 项的时间线不矛盾。换算是心算的，未验证。 | 第 441 行导语；第 451 行末句 | 文字是 A3 给定的，登记即可。以后可以附上 UTC 换算。

MINOR | /home/user/OpenMythos/metrix/CLAUDE.md:63（对照 :45、:62、:76） | 新条目规定第 5、10 节的做法延续到 E1-V1，但第 5 节第 6 条（:45）和第 10 节（:76）的括注仍标着「本阶段」，而第 8 节第 3 条（:62）规定「本阶段」的裁决在阶段结束时失效。新条目没有写明它取代这些标注，只能从「永久」且更具体来推定。第 1–3 节也没有提到，例如第 3 节以「收到 PROTOCOL_FROZEN 之前」为条件，是否适用于 E1-V1 没有说明。这条只部分回答了 PR22（DEFERRED_MINORS.md:831）。 | :45 与 :76 的「本阶段」；:62「「本阶段」的裁决在本阶段结束时失效」 | 文字是 A4 逐字给定的。建议登记，请 Review Gate 确认。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/pilot_final/report_fragments.py:143、:179（以及 140–179 行中的其他门槛字符串） | 生成脚本里仍然硬编码着改写过的旧门槛文字，所以 /home/user/OpenMythos/metrix/e1-pilot/reports/pilot_final/report_fragments.md:113、:131 与报告已经不一致。第 14 行的「例外」已经如实说明了这一点，而 A1 本来就只要求改报告。 | `"| G0.2 | 所有损失、分数、NLL 为有限值 |…"`；`"| T3 | N 在 TEST-QA 上满足 G0.3 的同样范围(含 Acc_CB(N),解释 B24) |…"` | 建议登记。E1-V1 复用这个脚本时，改为从协议读取或逐字引用。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/DEFERRED_MINORS.md:810–813、:830–831、:868 | 暂存树中 PR1–PR4、PR21、PR22 的处理仍是「登记,交 Review Gate」，第 3 节最后一条仍写着「报告与 metrix/CLAUDE.md 在裁决之前不改」。本提交之后这些状态都已过时。第 14 行的「例外」把读者指向 PR1，而 PR1 显示的仍是待决。A1–A5 没有要求本提交修改这个文件，所以不算遗漏。 | 第 868 行「报告与 `metrix/CLAUDE.md` 在裁决之前不改」 | 建议在登记本轮 MINOR 时一并写明：PR1–PR4、PR21、PR22 已按 2026-11-28 裁决 A1–A4 处理。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:14 | 「例外」一句不在 A1–A5 的字面范围内，是 Executor 自己加的。内容核对属实：两张表的表头都是「门槛(协议第 8 节)」（第 279、296 行）；DEFERRED_MINORS.md:810 确有 PR1；report_fragments.md:113、:131 中该列与报告不同。如果没有这一句，同一段的「未手工录入」「逐字嵌入」在 A1 之后就不再成立，所以加上是合理的。 | 「例外:Gate 0 与 T1–T3 两张表的“门槛(协议第 8 节)”一列已在勘误提交中…替换为协议第 8 节对应行的原文,与 `report_fragments.md` 中该列不同。」 | 建议在提交说明中向 Review Gate 写明，这是 A1 之外的附带修改，请其事后确认。

结论：PASS
