# code-reviewer, E1-PILOT final report commit 946ff2c3 (staged tree f90600cf), the only round (tasks/PILOT_REPORT_ORDER.md item 5); final report extracted unchanged from code-reviewer_round1_transcript.jsonl
---
code-reviewer 审查结果：E1-PILOT 最终报告提交（暂存树 f90600cf0aec5153a26eae2c21b5e7b68821addf，父提交 308d5f1319d78e521aefd35d86706f841cd02f2c）

运行环境：本会话的 Claude Code 云容器（只有 CPU）。我只用 Read、Grep、Glob 读文件，没有运行任何脚本，也没有执行 git。

结论：PASS。没有 BLOCKER；有 4 条 MAJOR、19 条 MINOR，按指令只登记，不修改。

**数值核对（已验证，直接对照 results/ 原始记录）**
报告中的数值，我逐项对照了 results/ 下的原始记录，没有发现与记录不一致的值，也没有发现不实的出处。核对范围：
- Environment 与各提交号、全部冻结哈希与数据哈希、31 个 state_sha256；
- G0.1–G0.10 与 T1–T3 的实测值和代码判定；
- 第 6 节的 40 个比较格（point_exact、%.4f 点估计、CI 端点）和 40 个 Spill 格；
- 16 个模型的 Acc、EM、FPR，30 条 dNLL 与 PPL%，G0.10 的全部 σ_d、n、半宽；
- 30 次训练的 token、FLOPs、wall_seconds、checkpoint 秒数；
- 各步耗时与峰值显存、预检、ST11、GPU 两段计时、费用算术；
- 留存清单的文件数与总字节；
- data-auditor 的 432 / 238 / 194 / 0 / 1.110e-16 / 173 / 140 / 46 / 213 / 246 / 11520（audit/stdout/pilot_final_recompute.txt:796-802）。

30 次训练的合计（9000 步、1155660、1228720、1.1976e16、1.6913e16、2915.84、1419.05）是我按记录逐条手算的，没有运行脚本。

**Non-claims 与覆盖面**
- 报告第 427-431 行与协议第 51-55 行逐字相同。
- 全文没有机制结论或优劣判断。我对「有效、更好、优于、提升、损害、表明」等词做了检索，命中的只有 Non-claims 原文和描述性用语。
- 协议第 10 节的 20 个字段齐全且顺序正确；Owner 指令第 2 项要求的各部分都有。

**metrix/CLAUDE.md**
diff 只改了第 21 行这一句，文字与 PILOT_REPORT_ORDER.md 第 4 项逐字一致。

**说明**
门槛文字我对照的是工作区中的协议文件。它与冻结提交 87a244db 下的字节是否相同，我没有计算哈希，属『未验证』。

---

严重度 | 文件:行号 | 问题 | 证据 | 建议

MAJOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:281-290, 298-300（生成处 reports/pilot_final/report_fragments.py:141-179）；另见 :239 | 「门槛(协议第 8 节)」一列是改写和删节，不是协议原文。所有数值都对，但漏了限定条件，T3 还把解释 B24 混进了标为协议的列。:239 却称门槛「逐条列在下文」。 | 协议:536「L1–L6 中涉及 TEST 的部分在 Gate 0 不要求,按第 8 步运行」被删；:537「所有用到的损失…」被写成「所有损失…」；:541「(真实映射,DEV-QA,learned)」与 :542「(DEV-QA,learned)」被删；:543「对 F 选定配置的 3 个 checkpoint 各评测两次」「并列判为错」「实现须开启 PyTorch 确定性设置并记录」被删；:545 的公式、δ 集合、「以最大者作为规划依据」「按 n 重抽样验证 CI 半宽」被删；报告 :300「(含 Acc_CB(N),解释 B24)」。门槛串在脚本中是硬编码，不读协议，也不读 Acceptance 记录。 | 由 Review Gate 决定：改为逐字引用协议第 8 节表格，或把列名改为「门槛摘要」并在 :239 说明这是摘要。

MAJOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:449（偏差第 7 项） | 「这些提交之间代码、测试、依赖锁定、协议与冻结文件无改动」不准确。四个冻结文件中有两个（DATA_MANIFEST.json、SPLIT_MANIFEST.json）在 0a67c2c4 与 53800ef7 之间被第 1 步改写过。这是协议第 8 节第 1 步要求的改动，ST12 也不比对这些字段，但所引核对没有覆盖这两个文件。:73 列的是具体路径，那里是准确的。 | reports/pilot_final/run_commits_and_code_check.txt:3 的 diff 路径表不含这两个 manifest；同文件:6「2 metrix/e1-pilot」；results/step1_record.json:113 `"M metrix/e1-pilot/DATA_MANIFEST.json\n M metrix/e1-pilot/SPLIT_MANIFEST.json"`、:417-418；提交 f6e875a1「non-TEST data hashes written into the manifests」（run_commits_and_code_check.txt:34）。 | 改为与 :73 相同的路径表述，并注明两个 manifest 由第 1 步按协议写入哈希（ST12 比对范围外）。

MAJOR（不确定） | metrix/CLAUDE.md:21 | 新句只写了时间和出处，没有写原因和作用范围。文件头要求修改「记录原因与时间」，第 8 节要求写入本文件的裁决「须注明作用范围」。不确定之处：文字是 Owner 指令逐字给定的，且要求「只改这一句」。 | 新行：「…结果见 reports/PILOT_FINAL_REPORT.md（出处：Review Gate 裁决，Owner 批准，2026-11-28）」；旧行带「作用范围：本阶段…；原因：…」；metrix/CLAUDE.md 文件头第 5 行、第 8 节第 3 条。 | 交 Review Gate 裁决是否补注作用范围与原因；在此之前不改。

MAJOR（不确定） | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:451（偏差第 9 项） | 正式运行指令的停止点 C 要求等待 Owner 批准 TEST 评测后才能运行第 3.8 节，实际是直接进入的：test-evaluate 在 07:25:03Z 启动，距 772b9247（07:24:30Z）33 秒。报告只引用了 tasks/PILOT_REPORT_ORDER.md 中的有条件批准，没有写明这是对停止点 C 的替代，也没有写明该批准原文直到本提交才入库。不确定之处：裁决可能在运行前就口头下达。 | tasks/FORMAL_RUN_OWNER_MESSAGE.md:29「C. …等待 Owner 对 TEST 评测的批准，未获批准不得运行第 3.8 节」；RUNBOOK_A100.md:7；reports/pilot_final/run_commits_and_code_check.txt:21-22；tasks/PILOT_REPORT_ORDER.md:8。 | 在第 9 项补一句：停止点 C 由有条件批准替代，该批准原文首次入库于本提交。是否作为偏差列出由 Review Gate 决定。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:14 | 「下文的数值表由 report_fragments.py…生成,未手工录入」说得过宽。有些表不在脚本生成的片段中，是手写的；这些表的值我已逐项核对，都正确。 | report_fragments.md 只有 environment、commits、hashes、checkpoints、gate0、test、comparisons、spill、per_model、dnll、g010、compute 这些片段；报告 :162-167（选定配置）、:243、:249-261（Stop Conditions）、:461-470、:478-486（data-auditor）不在其中。 | 改为「下文由脚本生成的表格（片段名…）」，或注明哪些表是手写的。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:14；report_fragments.py:4-5 | 「小数为 %.4f(另注明者除外)」以及 docstring「'%.6f' where stated」，与实际用到的 %.5f（dNLL）、%.2f（PPL、秒数）、%.4e（FLOPs）不符，这些也没有注明。 | report_fragments.py:247 `"%.5f | %.2f"`、:285 `%.4e … %.2f | %.2f`、:262 `%.6f`。 | 在 :14 列出各列实际使用的格式。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:28 | 报告称这是 template.Purpose 原文，但省略了记录中的前缀「**唯一问题**:」。 | results/experiment_record_formal_20261128T045921Z.json:1394；results/experiment_record_test-evaluate_20261128T072505Z.json:911。 | 补上前缀，或不再称「原文」。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:260（ST12 行） | 「fetch.txt 的各项下载哈希 `= frozen`」不准确：权重和 config.json 并没有标 `= frozen`。:446 的表述是准确的。 | results/command_output/fetch.txt:12「(not a weight file)」、:17-18「(downloaded from the frozen revision)」。 | 改用 :446 的表述。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:445（偏差第 3 项） | 「主机预装 pip 26.2.2」不确切：被替换的是新建 venv 中的 pip。 | results/command_output/env.txt:51-60（`$PY -m pip install pip==26.3` 中「Found existing installation: pip 26.2.2」）；RUNBOOK_A100.md:109-111。 | 改为「venv 中原有的 pip 26.2.2」。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:443（偏差第 1 项） | 「与全部训练、评测记录一致」：仓库里没有逐次评测的设备记录，只有 30 条训练记录和两份实验记录。:257 的表述是准确的。 | results/ 中含 device 字段的只有 training_runs/*.json、step1_record.json 和两份实验记录（Grep "device" 计数）。 | 改用 :257 的表述。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:162, 169 | 字段路径写成 `selection.*.ranking` / `selection.*.rows`，但 step4 中没有按 arm 嵌套。 | results/step4_record.json:10-19（`selection.ranking`、`selection.rows`）；results/step5_record.json:5-7（`selection.A.ranking`）。 | 改为 step4 `selection.ranking`；step5 `selection.<L|A>.ranking`。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:265 | `run F-F3-seed101` 只在实验记录模板中有，step4 的 positive_control 没有 run 字段。 | results/step4_record.json:5-9；experiment_record_formal…json:1389-1392。 | 注明 run 的出处只有实验记录模板。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:459 vs :470 | 导语说「以下内容都在 <work> 或 <inputs> 中」，但表中的 venv（/root/metrix-run/metrix-venv）两者都不是。 | results/command_output/test_generate_20261128T072042Z.txt:1（`/root/metrix-run/metrix-venv/bin/python`）。 | 导语中加上 venv。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:321-411 | 协议第 8 节列为只报告的 AllCorrect，以及第 5 节规定记为 NOT_TESTED 的 Retention，报告都没有提到。Owner 指令第 2 项没有要求这两项。 | METRIX_E1_PROTOCOL.md:550「只报告、不进门槛:…EM、AllCorrect…」、:238「Retention 记为 NOT_TESTED」。 | 可补一句：AllCorrect 的逐 fact 值在 summaries 的 all_correct_* 中；Retention 为 NOT_TESTED。

MINOR | metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md:79-97 | 冻结身份表没有列出标签与提交的对应关系，只在表头 :9 提到了 step0 文件。 | reports/pilot_final/step0_ls_remote.txt:4-7（`metrix-e1-pilot-frozen-v1.1^{}` → 87a244db…）。 | 可在冻结身份表加一行。

MINOR | metrix/e1-pilot/reports/pilot_final/report_fragments.py:101, 103, 120, 125, 301 | 输出文字声称某些值「均为」「两字段同值」「同字段」「step%s_record.json step_info.seconds」相同，但代码只打印其中一处，没有比较。我手工核对过，这些值确实相同。 | :101 只格式化 `ter["frozen_commit"]`；:103 只取 working_tree 字段；:120 不读 marker 的 test_files_sha256；:301 不读 stepN 的 seconds。 | 让代码实际比较这些值（不一致时报错），或删去这些断言。

MINOR | metrix/e1-pilot/reports/pilot_final/report_fragments.py:304 | 「F-F1-seed101 前 20 步」是硬编码的魔法值，记录中有对应字段。 | results/step2_record.json:124 `"run": "F-F1-seed101"`、:129 `"steps": 20`。 | 改为读 `pre["run"]`、`pre["steps"]`。

MINOR | metrix/e1-pilot/reports/pilot_final/report_fragments.py:259-260 | `def ns` 定义在 for 循环体内，依赖闭包中的 `n`，不利于阅读。 | `for comp in …: … def ns(delta): return … n[...]` | 移到循环外，把 n 作为参数传入。

MINOR | metrix/e1-pilot/reports/pilot_final/report_tables.py:17-21, 76, 105 | RUNS 列表是硬编码的，与 report_fragments.py:242 读取的 step6_record.json training_plan 重复；「30 runs」是字面量。 | results/step6_record.json:76-107。 | 改为从 training_plan 读取，计数用 len(RUNS)。

MINOR | metrix/e1-pilot/reports/pilot_final/report_tables.py:94 vs report_fragments.py:278 | 两个脚本的步数合计来源不同：一个用 accounting.steps，一个用 steps_run。当前两者都是 300。 | :94 `for k in ("fact_tokens", "train_flops", "wall_seconds", "steps")`；report_fragments.py:278 `rec["steps_run"]`。 | 统一使用 steps_run。

MINOR | metrix/e1-pilot/reports/pilot_final/report_tables.py:134 | RUNBOOK 的规划数值是打印出的字面量，但在 report_tables.txt:63 中看起来像计算结果。数值本身与 RUNBOOK_A100.md:260、:273 一致。 | `print("RUNBOOK_A100.md section 6 planning: unit price 1.8 USD/h; rental 3.6-9.0 USD; GPU part 2.2-5.6 USD")` | 注明是引文，或从 RUNBOOK 中读取。

MINOR | metrix/CLAUDE.md:21 | 路径「reports/PILOT_FINAL_REPORT.md」从 metrix/CLAUDE.md 看会解析成 metrix/reports/…，不存在；本文件其他引用都写全 metrix/e1-pilot/…。这是 Owner 给定的原文。 | metrix/CLAUDE.md 第 4 节、第 8 节引用 `metrix/e1-pilot/reports/ROUND8_REPORT.md`。 | 交 Review Gate 决定，在此之前不改。

MINOR（未验证） | metrix/CLAUDE.md:21 | 仅供参考：状态改为「已完成」后，按第 8 节，「本阶段」的裁决（第 4 节末句、第 5 节第 6 条、第 10 节）是否随之失效，本提交没有说明。 | metrix/CLAUDE.md 第 8 节「「本阶段」的裁决在本阶段结束时失效」。 | 由 Review Gate 确认阶段是否已结束。

结论：PASS
