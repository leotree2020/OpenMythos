# code-reviewer, C3 commit, round 3: final report, unchanged (extracted by reports/round6/review_extract.py from code-reviewer_round3_transcript.jsonl)
# staged tree 2d7f7bca79214fdce313f5d6a37c71e44d4afc7f, parent cc18466f8d327f37c6f6dd272b8e264d239ee386; invocation text: prompt_cr_round3.txt
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 3 段（C3：RUNBOOK_A100.md 与最终报告），第 3 轮。暂存树 2d7f7bca79214fdce313f5d6a37c71e44d4afc7f，父提交 cc18466f8d327f37c6f6dd272b8e264d239ee386。

## 方法

- 先读了仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，以它为定义（tools 行：Read, Grep, Glob），与我实际可用的工具一致。
- 只用了 Read、Grep、Glob。没有运行 git、pytest、shell 命令或任何代码。
- 工作区三份文档与 input_round2_to_round3.diff 的新增行一致。抽查了：
  - RUNBOOK:59–64、118、131、178
  - IMPL_C_REPORT.md:259、266、268
  - DEFERRED_MINORS.md:682–697
- tree.txt 中三份文档的 blob 与第 2 轮不同，与 diff 的 index 一致：RUNBOOK 4e7faac（:6）、DEFERRED_MINORS ad962a9（:524）、IMPL_C_REPORT 5a64b6c（:527）。对比的是 tree_round2.txt 的 :6、:524、:527。
- 代码与 a0e04d1f 相同（已验证，抽查 8 个 blob）：
  - 涉及：run_pilot.py、compute.py、data.py、pilot.py、stops.py、test_data.py、testgate.py、tests/test_run_pilot.py。
  - 位置：tree.txt:1240、1245、1247、1255、1258–1260、1285，对 reviews/a0e04d1f…/tree.txt:1173、1178、1180、1188、1191–1193、1218，也对 tree_round2.txt 的同号行。
  - input_round2_to_round3.diff 只涉及三份文档。input.diff 的 stat 只列出 metrix/e1-pilot/ 下 9 个文档与证据文件。
- 下文行号都是工作区文件的行号。
- 标注规则：
  - 「已验证」：引用了仓库文件，并写明行号。
  - 「算术」：按文件中的数字计算，没有运行代码。
  - 其余标「未验证」。

## 一、第 2 轮各项的处理（CK1–CK10）

- **CK1：已修且正确（已验证，读文件与代码）。**
  - RUNBOOK:93–96 把 formal 结束后的处理分成两种。识别用的字符串 “the run stopped before step 1: not committed” 与代码一致：pilot.py:1062，由 p.log 打印到 stdout 并 flush（pilot.py:212）。
  - 记录路径 `<work>/experiment_record_formal_<开始时间>.json` 与 pilot.py:964–967 一致。
  - RUNBOOK:175 加了同样的例外。
  - formal、test-generate、test-evaluate 的输出文件名带 `$(date -u …)`，见 RUNBOOK:86、103、124。
  - 两种情况的划分还有一个缺口，见问题 3。
- **CK2：已修且正确（已验证，读文件）。**
  - RUNBOOK:110 的调用文字禁止用 Read、cat 等显示内容的方式打开 TEST 文件，并要求脚本只打印计数、哈希与行数，与 data-auditor.md:12（“只输出计数”）一致。
  - 提交前逐行查看的范围已扩展到 audit stdout、data-auditor 原文与转录（RUNBOOK:118、176）。这符合 Task Order:56 “不提交……任何 TEST 内容”。
  - 转录是否入库的说法前后不一，见问题 5。
- **CK3：RUNBOOK 已修且正确；报告未同步（已验证）。**
  - RUNBOOK:178 改为“不含 src/、tests/、run_pilot.py，只含输出与 data-auditor 的审计脚本”。后备规则补上了 frontmatter 比对、固定第一句、原文入 reviews/ 并推送，以及不在 begin 与 finish 之间推送。这些与 metrix/CLAUDE.md 第 5 节第 5、6 条一致。
  - 但 IMPL_C_REPORT.md:259 仍写“只含输出、不含代码”，见问题 1。
- **CK4：RUNBOOK 已修；报告已修但有问题（已验证）。**
  - RUNBOOK:178 不再断言“阶段 C”。报告 :259 已请 Review Gate 说明各项“本阶段”裁决在 A100 运行期间是否有效，所列 C1 裁决第 2、6 项与 IMPL_C1_RULING.md:3 的“作用范围：本阶段”一致。
  - 但同一项前半句仍断言“作用范围是阶段 C”，见问题 1。
- **CK5：已修且正确（代码部分已验证；命令未运行，未验证）。**
  - RUNBOOK:59–64 先 `df -h` 选分区，再设 WORK、INPUTS。环境检查 tee 到 env.txt，3.1–3.3 的输出用 tee -a 追加（:70、75、78）。
  - “代码不核对 Python 的补丁版本”属实：ST8 只核对设备与 DATA_MANIFEST 中 model.libraries 的库版本（stops.py:98–107；frozen.py:248–261）。
  - 遗留问题见问题 2。
- **CK6：已修且正确（已验证，读代码）。**
  - 两行输出与 run_pilot.py:72–75 一致。“completed” 只在 finish 成功、且实验记录已提交时打印：pilot.py:1242、1309，以及 1071–1074 的提交失败会重新抛出。
  - :133 写明“无论结果如何，不得重跑”。
  - 对输出的说明不完整，见问题 4。
- **CK7：已修且正确（算术，并读代码）。**
  - a_factor − 1 = 6.7524 − 1 ≈ 5.75，与 compute.py:221–222 的公式一致。
  - 34 个训练当量 = 22 + 8 × 1.5。
  - “ST7 的事前判断与 ST11 都按 a_factor 放大 A” 属实（pilot.py:344；compute.py:223）。
  - 1.5 倍已标为“未实测”。
- **CK8：已修且正确（已验证）。**
  - IMPL_C_REPORT.md:236、253 改为“第 1、6、7、9、10 项”，与 IMPL_C_OWNER_MESSAGE.md:25 一致。
  - :268 新增第 1–5 项一行，内容与 IMPL_C_OWNER_MESSAGE.md:31 的裁决 1–5 对应，落实见报告 :15–31。第 2–5 项超出 Owner 所列，但它们是记录性的裁决，无害。
  - :266 注明“只列一例”。
- **CK9：已修且正确（已验证）。**
  - 两条报错文字与 compute.py:33、44 一致。
  - set_determinism 在 Pilot() 中运行（pilot.py:225）。
  - 异常由 run_guarded 打出回溯后退出（_cli.py:24–29）。
- **CK10：已修且正确（已验证）。**
  - 第 1 步：step_start(1) 的 ST12 不传数据目录（pilot.py:360；stops.py:142–145），随后 step1 调用 D.generate（pilot.py:546），generate 调用 check_inputs（data.py:538）。
  - 第 2 步起：data.verify 先核对 content，再调用 generate（data.py:604–605）。
  - RUNBOOK:34、44 的写法因此准确。

**DEFERRED_MINORS 1.37 基本如实（已验证）。**
- :688–697 的 CK1–CK10 与我第 2 轮的 10 条 MINOR 逐条对应，没有遗漏。
- “按 Task Order 第 9 节必须修”与 IMPLEMENTATION_TASK_ORDER_V1.md:129 一致。
- 不如实之处：CK3、CK4 记“已修”，但报告中仍有残留（问题 1）。

## 二、TEST 路径（防范对象内；按 RUNBOOK 与代码推演，未运行，未验证）

没有找到按 RUNBOOK 操作会评测 TEST 两次，或在 ST10 不成立时评测 TEST 的路径。依据：
- 本轮只改了文档，TEST 命令本身没有变。
- :133 加了“无论结果如何，不得重跑”。第二次运行仍被 refuse_if_test_evaluated 拒绝（pilot.py:1252–1263）。
- 后备规则新增的各次提交与推送都在 3.8 之前（RUNBOOK:118、178）。若某次审查为 BLOCK，计数文件不会提交，begin 会在写标记之前拒绝：它需要已提交的 data-auditor 计数，并重新判 ST10。
- 3.7 的新增要求（不显示 TEST 内容、提交前逐行查看）只减少泄漏风险，不影响闸门。

## 三、问题

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:259（另见 :249；DEFERRED_MINORS.md:690–691） | 【已验证，读文件】C3 待决第 2 项仍保留第 2 轮指出的两处说法：“只含输出、不含代码”（CK3(b)），以及断言“作用范围是阶段 C”（CK4）。同一项后半句却请 Review Gate 说明“本阶段”指阶段 C 还是 E1 Pilot，自相矛盾，也与已改正的 RUNBOOK:178 不一致。所以 1.37 中 CK3、CK4 的“已修”，以及审查表 :249 的“全部在文档中修正”，不完全如实。这只影响 Review Gate 读到的文字，不影响 TEST 闸门 | :259 “…审查原文的提交只含输出、不含代码。补充裁决 1 的“证据提交”只限 `reports/`、`reviews/`、`audit/`,作用范围是阶段 C。” | 改为“不含 src/、tests/、run_pilot.py，只含输出与 data-auditor 的审计脚本”；删去“作用范围是阶段 C”，或改为“作用范围：本阶段（含义见下文的问题）”；1.37 的 CK3、CK4 如实记录

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:24、59–64、73–75、81 | 【读文件已验证；空间大小与 pip 缓存位置未验证】(a) 第 3.0 节只为 `<work>`、`<inputs>` 选分区。venv 仍在 `~/metrix-venv`，pip 默认把 wheel 缓存在 `~/.cache/pip`；第 1 节磁盘表却把“依赖约 6 GB”算在 `<work>` 所在分区。租用机的根分区常常较小，安装可能因空间不足失败，此时已在计费。(b) :64 的核对清单没有第 1 节的 glibc ≥ 2.28。(c) env.txt 与 fetch.txt 不带时间，重跑 3.0 或 3.4 时第一条 tee（不带 -a）会覆盖前一次输出 | :73 `python3.13 -m venv ~/metrix-venv`；:24 “`<work>` 所在分区至少 300 GB 可用:…+ 依赖约 6 GB” | venv 放在所选分区上（例如 `$WORK/../metrix-venv`），pip 加 `--no-cache-dir`，或写明家目录所在分区须留约 15 GB；:64 加上 glibc；env.txt、fetch.txt 同样带时间，或写明不得重跑这两步而须报告

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:93–96、141、145 | 【已验证，读代码】formal 命令输出的两种处理，靠“记录在 results/ 并已提交”与输出中的 “stopped before step 1” 区分。但 Pilot() 内的失败两种标志都没有：读冻结文件时的 ST12、设置确定性失败、`--work` 在仓库内的 ImplementationFail（pilot.py:216–225；run_pilot.py:64；_cli.py:24–29）。这些失败只有回溯，Executor 无法从 :95–96 判断是否提交 formal_<时间>.txt。属防范对象之外 | :96 “第 1 步开始之前的停止(输出中有 “the run stopped before step 1: not committed”…)” | 第二种情况改为“输出中有该行，或以回溯退出而 results/ 中没有本次的实验记录”：不提交，报告 Owner

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:131 | 【已验证，读代码】输出的说明只列了两种行，没有覆盖以回溯结束的三种情况，这三种都只打印回溯与 `RESULT: FAIL`：(a) TestAlreadyEvaluated 被重新抛出（pilot.py:1297–1299）；(b) 标记写出之后崩溃或 Ctrl-C，先写并提交 BLOCKED 记录，再重新抛出（pilot.py:1300–1311）；(c) finish 已推送结果，但实验记录提交失败，重新抛出（pilot.py:1071–1074）。第二次运行仍被代码拒绝，:133 也禁止重跑，属防范对象之外 | run_pilot.py:74 `print("test-evaluate %s: %s" % ("completed" if ok else "stopped or refused", status))`，只在 run_test_evaluate 正常返回时执行 | 在 :131 后补一句：以回溯结束时，看 `results/` 中是否已有 `test_evaluation_marker.json` 或 `test_evaluation_result.json`；有则 TEST 视为已评，不得重跑，连同输出报告 Owner

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:118、176 | 【已验证，读文件】转录是否入库说法不一。:118 与 :176 要求提交前逐行查看 data-auditor 的“原文与转录”，但 :118 列出的 `reviews/<该提交>/` 内容只有“原始输出、调用文字与 frontmatter 核对”，没有转录 | :118 “data-auditor 的原始输出、调用文字与 frontmatter 核对存入 `metrix/e1-pilot/reviews/<该提交>/`” | 写明转录是否入库；入库就列进 :118

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:139 | 【已验证，读代码；这是第 2 轮已有的文字，本轮未改】“一般规则：除下列情形外，任何停止都由 run_pilot 写出实验记录”不适用于 formal 中的 Ctrl-C。run_gate 只捕获 Exception（pilot.py:1021–1031），KeyboardInterrupt 在 finally 之后直接抛出，到不了 final_record（:1032），所以没有实验记录。:28 只写了 SIGHUP，:168 只写了 test-evaluate 的 Ctrl-C。属防范对象之外 | pilot.py:1026 `except Exception as e:` | 在第 4 节例外中补一句：formal 被 Ctrl-C 或 SIGHUP 结束时没有实验记录，不得重跑，连同命令输出报告 Owner

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:178 | 【已验证，读文件；裁决属 Review Gate】后备规则有两个缺口。(a) 规则要求“每次提交前调用 code-reviewer”，又要求把审查原文提交并推送；存放原文的这次提交按同一规则也要先审，形成无穷递归。阶段 C 靠补充裁决 1 与 C1 裁决第 8 项把这类提交视为证据提交，而这正是待决的问题。(b) 没有写运行期间审查为 BLOCK 时怎么办（metrix/CLAUDE.md 第 5 节第 3、4 条）。可能有人为了赶在租期内完成而修改 audit 脚本或输出。代码在 begin 中仍会拒绝，所以不影响 TEST 闸门 | :178 “未裁决时按 metrix/CLAUDE.md 第 5 节:每次提交前调用 code-reviewer…;审查原文存入 `metrix/e1-pilot/reviews/<提交>/` 并推送” | 写明存放审查原文的提交不再送审（或一并交 Review Gate 裁决）；BLOCK 时停下，不修改输出，不运行 3.8，报告 Owner。在 C3 待决第 2 项中一并列出

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:237 | 【已验证，读文件】C3 节“交付”只列了 `DEFERRED_MINORS.md` 1.35、1.36，没有列本次新增的 1.37 | :237 “本报告;`DEFERRED_MINORS.md` 1.35、1.36;” | 改为“1.35–1.37”

没有 BLOCKER，也没有 MAJOR。第 2 轮的 CK1–CK10 都已处理：CK3、CK4 在 RUNBOOK 中正确，在报告 :259 中有残留（问题 1）；其余各项正确。上面 8 条 MINOR 都在防范对象之外，或只涉及措辞、操作细节与报告的如实性。

结论：PASS
