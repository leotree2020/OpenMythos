# code-reviewer, C3 commit, round 2: final report, unchanged (extracted by reports/round6/review_extract.py from code-reviewer_round2_transcript.jsonl)
# staged tree c9dfc4ac45e78e847cb5654a9cc0385d8b800d3d, parent cc18466f8d327f37c6f6dd272b8e264d239ee386; invocation text: prompt_cr_round2.txt
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 3 段（C3：RUNBOOK_A100.md 与最终报告），第 2 轮。暂存树 c9dfc4ac45e78e847cb5654a9cc0385d8b800d3d，父提交 cc18466f8d327f37c6f6dd272b8e264d239ee386。

## 方法

- 先读了仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，以它为定义（tools 行：Read, Grep, Glob）。
- 只用了 Read、Grep、Glob。没有运行 git、pytest 或任何代码。
- 工作区三份文档的内容与 input_round1_to_round2.diff 的新增行一致（抽查 RUNBOOK:136、IMPL_C_REPORT.md:294、DEFERRED_MINORS.md:661）。tree.txt 中 RUNBOOK 的 blob 5467ebe 与 diff 的 index 相同。下文行号都是工作区文件的行号。
- 代码与 a0e04d1f 相同（已验证，逐行比对）：
  - 对比范围：tree.txt 第 1240–1292 行，对 /home/user/OpenMythos/metrix/e1-pilot/reviews/a0e04d1f3e2be4df30ff700a79ae9af88154ee6a/tree.txt 第 1173–1225 行。
  - 涉及的文件：run_pilot.py、src/metrix_e1/ 的 19 个文件、src/metrix/e1_pilot/ 的 2 个文件、tests/ 的 18 个文件，blob 逐个相同。
  - input.diff 的 stat 只列出 metrix/e1-pilot/ 下的 9 个文档与证据文件。
- 标注规则：
  - 「已验证」：引用了仓库文件或已提交的原始输出，并写明行号。
  - 「算术」：按文件中的数字计算，没有运行代码。
  - 其余标「未验证」。

## 一、第 1 轮各项的处理（CJ1–CJ20）

- **CJ1（BLOCKER）：已修，正确（已验证，读代码）。**
  - RUNBOOK:136 写明立即停下，不得关闭确定性，不得改 CUBLAS_WORKSPACE_CONFIG、TF32、cuDNN 或代码，不得重跑。
  - 文中对代码行为的描述与代码一致：
    - set_determinism 在 Pilot() 中、CUDA 初始化前调用（pilot.py:225；compute.py:27–45）。
    - 设置写入实验记录（pilot.py:962）。
    - formal 崩溃时写 NOT_TESTED 记录：第 1 步之后提交，之前只写到 <work>，然后重新抛出（pilot.py:1026–1038、1060–1063）。
    - test-evaluate 写标记之前崩溃不写记录，之后写 BLOCKED（pilot.py:1300–1308）。
  - 报告新增了“Owner 阶段 C 各项要求的落实”（IMPL_C_REPORT.md:261–275），对表中各行逐项核对。表的范围有一处小问题，见问题 8。
- **CJ2：已修，正确（已验证）。**
  - 命令输出改为 <work>/command_output/*.txt 与 results/command_output/*.txt（RUNBOOK:53、73、79–84、96、117、166）。
  - git check-ignore 的原始输出：/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c3_02_runbook_hashes.txt:49–54。两个 .txt 路径为 NOT_IGNORED；logs/ 被 .gitignore:65 忽略，*.log 被 .gitignore:141 忽略。
  - 我读了 .gitignore 全文，没有其它模式匹配 fetch.txt、formal.txt、test_generate.txt、test_evaluate.txt。
- **CJ3：已修，正确（算术）。**
  - checkpoint 开销：80×10 + 152×5 = 1,560 s = 26 min；80×20 + 152×20 = 4,640 s = 77 min。去掉 15 次计时外的文件哈希，为 24.75–72.3 min。
  - 训练：34 × 300 × 0.1–0.3 s = 17–51 min。评测：58 × 0.5–1 min = 29–58 min。
  - GPU 时间合计：74–186 min，即 1.2–3.1 h。费用：2.2–5.6 美元。按租用 2–5 小时计：3.6–9.0 美元。
  - RUNBOOK:180、185、189 与报告验收第 8 项（:288）一致。
- **CJ4：已修，正确（已验证 + 算术）。**
  - B17 公式与 compute.py:213–228 一致。
  - a_factor = 6.7524，T_anchor = 511.97，T_fact = 118.67（c2d_smoke_records/step2_record.json:97、100、122）。
  - B17 区间：22 + 8×6.75 = 76 个训练当量；76×300×0.1–0.3 s = 0.63–1.90 h，加评测 0.48–0.97 h、已用 GPU 0.05–0.08 h，约 1.2–3.0 h。
  - checkpoint 开销按 pilot.checkpoint_overhead_seconds 计算（pilot.py:181–187）：下界 32×10 + 30×30 + 18×10 + 17×5 + 15×5 = 1,560 s；上界 4,640 s；即 0.43–1.29 h。B17 与它之和约 1.6–4.2 h。
  - 字段名 b17_estimate_hours、b17_plus_checkpoint_overhead_hours_report_only 与 step2_record.json:98、108 相同。
  - 风险已写入“最终状态”（IMPL_C_REPORT.md:294）。
  - 措辞有一处不准确，见问题 7。
- **CJ5：已修，但有小问题（已验证，读文件）。**
  - 3.7 的四步覆盖了 data-auditor 的 frontmatter 比对、调用文字第一句、脚本与 stdout 的位置、reviews/ 的存放，并要求都在 3.8 之前完成（RUNBOOK:103–112）。
  - 手工提交的审查方式已列为 C3 待决第 2 项，并写了后备规则。
  - 后备规则没有写 code-reviewer 一侧的义务；“不含代码”的说法也不准确。见问题 3。
- **CJ6：已修。** RUNBOOK:9 写明与 metrix/CLAUDE.md 第 4 节的关系；报告 C3 待决第 1 项（IMPL_C_REPORT.md:257），标为“租卡前”（RUNBOOK:7）。
- **CJ7：已修**（RUNBOOK:7）。
- **CJ8：已修**（RUNBOOK:34、44）。“每一步开始时的 ST12”有残留的不准确，见问题 10。
- **CJ9：已修，正确（已验证）。**
  - RUNBOOK:120 写的顺序与 pilot.test_evaluate 一致：pilot.py:1172–1177、1189–1197、1204（before_run 中先 ST9 再 ST7，pilot.py:393–400）、1205–1212。
  - RUNBOOK:53 写明“整个 Pilot 只用这一个克隆”。
  - DEFERRED_MINORS.md:645（CI3）与 :648（CI6）的处理说明已更正，与 RUNBOOK 一致。
- **CJ10：已修，正确（已验证）。** RUNBOOK:130–134 与代码一致：文件名 pilot.py:964；第 1 步之前停止的例外 pilot.py:1052–1063；test-generate pilot.py:1118–1137；test-evaluate pilot.py:1272–1309。
- **CJ11：已修，正确（已验证）。**
  - RUNBOOK:99、112 与 test_data.py:198–199 的输出行一致；该行经子进程直通 tee（pilot.py:1130）。
  - begin 仍从已提交记录判 ST10，并绑定 general_test_sha256（testgate.py:376–385）。
  - 新增内容已写入 C2 待决第 1 项（IMPL_C_REPORT.md:193）与 C3 待决第 3 项（:259）。
- **CJ12：已修。** RUNBOOK:122 与 IMPL_C2_OWNER_MESSAGE.md:4 的引号内原句逐字相同；报告 :66 已改。
- **CJ13：已修。** pip 26.3 与 c2_01_env_fetch.txt:7 一致；RUNBOOK:23 写明须预装 Python。但 Python 版本检查不在命令序列中，见问题 5。
- **CJ14：已修**（RUNBOOK:28、53、58、159）。
- **CJ15：已修**（RUNBOOK:15、56–57）。
- **CJ16：已修。** 覆盖了 test_generate.txt、test_evaluate.txt 与 <work>/test/ 全部文件（RUNBOOK:167、170）。3.7 的提交有同类缺口，见问题 2。
- **CJ17：已修（已验证）。** IMPL_C_REPORT.md:240–242 写明了录制时的写树与录制后只改文档；代码相同的依据我已独立核对（见“方法”）。
- **CJ18：已修（已验证）。** c3_02 逐个对照了 DATA_MANIFEST.json 中的哈希（:20–23、228、230、237）与所引原始输出。c3_03 用 logrun 录制，记录了解析命令，比对结果为 “same as c3_hf_tree_70d244cc.txt: True”。
- **CJ19：已修（已验证）。** IMPL_C_REPORT.md:286 引用的阶段 A、B、C 审查文件都存在，最后一行都是“结论：PASS”。例如：
  - reviews/602a39e8…/code-reviewer_round2.md:117
  - reviews/219c4a60…/code-reviewer.md:96
  - reviews/74a4d444…/code-reviewer_round2.md:149
  - reviews/fdbb9def…/code-reviewer.md:83
  - reviews/493d7f9c…/code-reviewer.md:94
  - reviews/a0e04d1f…/code-reviewer_round1.md:114
- **CJ20：已修**（IMPL_C_REPORT.md:294）。

**DEFERRED_MINORS 1.35、1.36 如实（已验证）。**
- 1.36（DEFERRED_MINORS.md:655–680）记“1 BLOCKER、5 MAJOR、14 MINOR”。与我第 1 轮原文逐条对应：CJ1–CJ6 对应 BLOCKER 与 5 个 MAJOR，CJ7–CJ20 对应 14 个 MINOR，没有遗漏。各条处理说明与本轮文件内容相符。
- 1.35 只改了 CI3、CI6 两条的处理列，新内容属实。

## 二、TEST 路径（防范对象内；未验证，读代码与文件）

没有找到按 RUNBOOK 操作会评测 TEST 两次，或在 ST10 不成立时评测 TEST 的路径。依据：
- 3.7 的两次推送与命令输出的提交都在 3.8 之前（RUNBOOK:111、166）。begin 到 finish 之间明确禁止推送与 git 操作（RUNBOOK:122、166）。
- 3.7 第 4 步的人工比较只是额外一层：
  - begin 仍从已提交记录重新判 ST10，并绑定 general_test_sha256（testgate.py:351–386），且在写标记之前。
  - 带停止码的拒绝写记录（pilot.py:1285–1296）。
  - C3 待决第 3 项中“运行 test-evaluate、让 begin 判 ST10”的选项，同样在写标记之前拒绝。
- 确定性报错一段禁止重跑。标记存在后，refuse_if_test_evaluated 拒绝（pilot.py:1252–1263）；begin 中的 refuse_if_marker 仍会检查。

## 三、IMPLEMENTATION_READY

按 Owner 指令的定义（IMPL_C2_OWNER_MESSAGE.md:7，“阶段 C 全部验收通过后……状态写为 IMPLEMENTATION_READY”）成立：
- 验收第 1–7 项的原始输出与第 1 轮相同，代码不变。
- 第 8 项以本轮 PASS 为前提。
- 尚待 Review Gate 决定的事项已写明“请 Review Gate 确认；若裁决要求改代码，状态退回 C2”。

## 四、问题

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:91、132、166 | 【已验证，读文件与代码】formal 在第 1 步之前停止时，手册的两处指示矛盾：第 91 行要求“无论结果如何”都提交命令输出，第 132 行说这种停止“不写入仓库、不推送”（代码同此设计，pilot.py:1052–1063）。照第 91 行做，会把非 Pilot 机器上这次停止的 formal.txt 推送到本分支；之后重跑时，同名 formal.txt 还会被覆盖。属防范对象之外 | RUNBOOK:91 “`formal` 结束后:无论结果如何,停下,按第 5 节提交命令输出”；RUNBOOK:132 “不写入仓库、不推送,由 Executor 连同命令输出报告 Owner” | 第 91 行区分两种情况：第 1 步开始之后的结束或停止，提交命令输出；第 1 步之前的停止，不提交，连同输出报告 Owner。命令输出文件名可带开始时间

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:111、167–168 | 【已验证，读文件；后果未验证】提交前确认“不含 TEST 文字”的要求只覆盖 test_generate.txt 和 test_evaluate.txt。3.7 第 3 步还会提交 data-auditor 读过 general_test.jsonl 之后的完整 stdout（audit/stdout/）和原始输出（reviews/<该提交>/；按本阶段惯例还含原始转录），这些都没有同样的检查。Task Order 规定“不提交……任何 TEST 内容”（tasks/IMPLEMENTATION_TASK_ORDER_V1.md:56），而回溯信息或转录中的工具结果都可能带出窗口文字。同类问题见 CJ16 | RUNBOOK:167 “提交 `test_generate.txt`、`test_evaluate.txt` 之前逐行查看,确认不含 TEST 题目、答案或通用文本的文字” | 把这一检查扩展到 3.7 的 audit stdout、data-auditor 原文与转录；并在 3.7 第 1 步的调用文字中写明：不得用 Read 打开 TEST 文件，脚本只打印计数与哈希

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:169、111 | 【已验证，读文件】运行期间手工提交的审查说明不完整。(a) 后备规则“每次提交前调用 code-reviewer”没有写 metrix/CLAUDE.md 第 5 节第 5、6 条的要求：调用前比对 frontmatter、固定第一句、审查原文存入 reviews/<提交>/ 并推送；也没有写推送时机须在 3.8 之前或 finish 之后。3.7 只为 data-auditor 写了这些。(b) 说这些提交“只含输出、不含代码”不准确：3.7 第 3 步的提交含 data-auditor 的审计脚本（Python） | RUNBOOK:169 “这些手工提交只含输出、不含代码”；RUNBOOK:111 “Executor 提交计数文件、audit 脚本与完整 stdout” | 在后备规则中补上 code-reviewer 的上述义务与推送时机（不在 begin 与 finish 之间）；措辞改为“不含 src/、tests/、run_pilot.py，只含输出与 data-auditor 的审计脚本”

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:169；/home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:258 | 【已核对；“本阶段”的含义我不确定】手册断言“补充裁决 1 的作用范围是阶段 C”，但 metrix/CLAUDE.md 第 2 节的“当前阶段”是“E1 Pilot”。同时，手册在 A100 运行期间依赖另几项同为“本阶段”的裁决：C1 裁决第 2、6 项（RUNBOOK:30、155–160）与 2026-11-27 裁决第 1 项（RUNBOOK:122）。若“本阶段”指 Implementation 阶段 C，这几项在运行时也已失效；若指 E1 Pilot，补充裁决 1 在运行时仍有效。手册对同一措辞读法不一。此事已交 Review Gate（C3 待决第 2 项），不影响 TEST 闸门 | IMPL_C_OWNER_MESSAGE.md:17 “作用范围：本阶段”；metrix/CLAUDE.md 第 2 节 “E1 Pilot,状态:PROTOCOL_FROZEN（v1.1）（…作用范围：本阶段…）” | 不要断言“阶段 C”；在 C3 待决第 2 项中请 Review Gate 一并说明：手册依赖的各项“本阶段”裁决在 A100 运行期间是否有效

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:22–25、56–76 | 【已验证，读文件与代码】第 1 节表中的多数检查命令不在第 3 节的命令序列里：`python3.13 --version`、`ldd --version`、`df -h <work>`、`free -g`、`git config`。3.0 的 nvidia-smi 与 3.3 的 torch 检查也没有 tee 下来，所以租用条件（CUDA ≥ 13.0、A100 80GB）没有入库的原始输出（metrix/CLAUDE.md 第 9 节）。`WORK=~/metrix-work` 写死在家目录，而磁盘要求是 <work> 所在分区 ≥ 300 GB；空间不足时，formal 会在保存 checkpoint 时崩溃并浪费 GPU 时间。Python 补丁版本不由代码核对：ST8 只核对设备与库版本（stops.py:98–107） | RUNBOOK:72 `export INPUTS=~/metrix-inputs WORK=~/metrix-work`；RUNBOOK:57 `nvidia-smi`（没有 tee） | 在 3.0–3.3 中依次列出表中各项检查，tee 到 `$WORK/command_output/env.txt` 并与 fetch.txt 一起提交；写明先用 `df -h` 选定满足 300 GB 的分区，再设置 WORK

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:117–124 | 【已验证，读代码】手册没有说明 test-evaluate 输出的含义：评测完整结束、但最终状态不是 PASS（如 HYPOTHESIS_FAIL）时，最后一行也是 `RESULT: FAIL`，Executor 可能误读为评测失败。第二次运行会被拒绝（pilot.py:1252–1263），不会评两次，属防范对象之外 | run_pilot.py:73 `passed = ok and status == "PASS"` | 在 3.8 后写明：“test-evaluate completed: <状态>” 表示 TEST 已评完；RESULT 只表示最终状态是否为 PASS；无论哪种情况都不得重跑

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:178 | 【算术，按第 10 节系数；1.5 倍未验证】“它们的计算量相对于每步的参数更新很小”在 FLOP 意义上不成立。锚文本部分每步约 8·P·512 ≈ 7.0e12 FLOPs，事实部分约 6·P·119 ≈ 1.2e12，比值约 5.75，正是 a_factor − 1（compute.py:221–222）。1.5 倍只能来自 bf16 autocast 下的吞吐假设（train.py:409–421）。预检只测 F1，不测 A 的步时（RUNBOOK:128），所以“以预检为准”管不到 A 的实际耗时。由于 ST7 事前判断与 ST11 都按 a_factor 放大 A（pilot.py:344；compute.py:223），估计偏保守，不构成风险 | RUNBOOK:178 “它们的计算量相对于每步的参数更新很小,实际 wall-clock 按 1.5 倍计” | 改为“按 bf16 吞吐估计约 1.5 倍（未实测）；预检不含 A，A 的实际步时在第 5 步第一次 A 训练的记录中才可见”

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:236、252、261–275 | 【已核对】落实表称“逐项核对补充裁决 1–6 与上次阶段 C 指令第 6–10 项”，但 Owner 写的是“第 1、6、7、9、10 项”（IMPL_C_OWNER_MESSAGE.md:25）。第 1 项（B1–B24、B3、B14）在表中没有一行；其落实在“Review Gate 对阶段 B 的裁决”一节（IMPL_C_REPORT.md:15–19）与 C2 节（:185），可以核对。所以这不是落实上的遗漏，而是表的范围写错。另外，补充裁决 1 一行的证据只列了 `c1_07_stop_commit_precheck.txt` 加一个“等” | IMPL_C_REPORT.md:252 “逐项核对补充裁决 1–6 与上次阶段 C 指令第 6–10 项” | 表中加一行“上次指令第 1 项（及第 2–5 项）：见‘Review Gate 对阶段 B 的裁决’”；第 236、252 行改为“第 1、6、7、9、10 项”；补充裁决 1 一行列全各证据提交的核对输出，或注明只列代表

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:136 | 【已验证，读代码】确定性一段只写了“某个算子报错”（训练或评测中，第 1 步之后），没有写确定性设置本身失败的情形。`compute.set_determinism` 在 Pilot() 中运行（pilot.py:225），可能抛出 “CUDA already initialised …” 或 “determinism settings did not take effect”（compute.py:32–44）。这时与 Pilot() 的 ST12 一样，没有任何实验记录，run_pilot.py 打出回溯后退出（run_pilot.py:64；_cli.py:24–29）。处理原则相同，只是记录的说法不同 | compute.py:33 `raise RuntimeError("CUDA already initialised without %s=%s" % (DETERMINISM_ENV, want))` | 在该段末补一句：设置确定性本身失败时没有实验记录，同样停下，连同命令输出报告 Owner，不得改设置

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:34、44 | 【已验证，读代码】“每一步开始时的 ST12”核对 7 个冻结值，这一说法不准确：第 1 步开始时的 ST12 不传数据目录，不核对输入（pilot.py:360；stops.py:142–145）；第 1 步的输入由 generate 中的 check_inputs 核对（data.py:201–205）。两者合起来覆盖完整，问题只在措辞 | pilot.py:360 `self.fz = STP.st12(self.root, self.inputs, self.data_dir if k > 1 else None)` | 改为“第 1 步由 generate 核对，第 2 步起每步开始时的 ST12（data.verify）核对”

没有 BLOCKER，也没有 MAJOR。第 1 轮的 BLOCKER 与 5 个 MAJOR 都已正确处理；上面 10 条 MINOR 都在防范对象之外，或只涉及措辞与证据的完整性。

结论：PASS
