# code-reviewer, round 1, C4 code commit (staged tree 63121c792654e53fce2bb1418b6413b3a275c126, parent 3bc761ea1d1cb7a1bf5a7a89d4084055e4ca83d1)
# Extracted unchanged from the transcript by reports/round6/review_extract.py
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C，C4 代码提交（按 tasks/IMPL_C4_RULING.md），第 1 轮。审查对象是暂存树 63121c792654e53fce2bb1418b6413b3a275c126，父提交 3bc761ea1d1cb7a1bf5a7a89d4084055e4ca83d1。仓库为 /home/user/OpenMythos，下文路径都相对于它。

**依据**
- scratchpad/review_c4/ 下的 input.diff、input_code.diff、tree.txt。
- 仓库代码：src/metrix_e1/pilot.py、interpretations.py、stops.py、compute.py；tests/test_run_pilot.py、test_test_data.py、test_stops.py。
- 协议 METRIX_E1_PROTOCOL.md 第 283、522、530、619、623 行。
- tasks/IMPL_C4_RULING.md、tasks/IMPL_C2_OWNER_MESSAGE.md。
- reports/IMPL_C_REPORT.md 第 191–199 行（C2 待决）。
- RUNBOOK_A100.md 第 182–200 行。

**方法**：我只用了 Read、Grep、Glob，没有运行代码、git、pytest 或变异。
- 「已验证」：引用了仓库中的录制，并写明行号。
- 「已核对仓库文件」：只读了源码或文档的文字。
- 「未验证」：推理得出。

## 一、录制核对

**代码绑定（已验证）**
- input.diff 中四个代码文件的 index 行：pilot.py e74baae、interpretations.py a0eeb88、test_run_pilot.py e038d16、test_test_data.py b11d08a。
- 它们与两份录制首尾 `git ls-files -s` 记下的 blob 相同：
  - reports/impl_c/c4_02_checks.txt:33、48、61、65 与 210、225、238、242；
  - c4_03_smoke.txt:20、23、40、45 与 305、308、325、330。
- 首尾都有 WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT。代码 diff 的 sha256 都是 e8df1988…，写树都是 178c9a2f，HEAD 都是 3bc761ea。出处：c4_02:19-22、196-199；c4_03:4-7、289-292。
- tree.txt 只有树哈希，没有 ls-tree 内容，不能用它逐个核对 blob。

**脚本 sha256（未验证）**：c4_mutate.py、c4_checks.sh、c4_smoke.sh 的 sha256 记在 c4_02:73-75 与 c4_03:48。我无法计算 sha256，所以没有核对它们与暂存 blob 的对应。

**pytest（已验证）**：326 passed（c4_02:155），比 c2d 的 324 多 2 个，正好是新测试的两个参数。两个参数实际运行了（c4_02:149-150）。

**变异（已验证）**：9 个全部测出，变异前后 sha256 相同，RESULT: PASS（c4_02:158-181）。

**TEST 隔离（已验证）**
- TEST 生成器拒绝，--out 未创建，没有 results 目录（c4_02:110-115、124）。
- 冒烟中 TEST 文件数为 0（c4_03:253）。

**冒烟（已验证）**
- 日志：「B17 estimate 2.008 h + checkpoint overhead 0.010 h = 2.019 h (ST11, bound 3.5 h)」（c4_03:55）；RESULT: PASS（c4_03:129）。
- 第 2 步记录：b17_estimate_hours 2.0084901014074954，checkpoint_overhead.seconds 36.797356973997466，st11_estimate_hours 2.018711589455828，st11 为 "within bound"（c4_03:260-275；c4_smoke_records/step2_record.json:98、118、125-128）。
- 2.0084901014 + 36.797356974 / 3600 = 2.0187115895，和正确。
- 冒烟实验记录中 B17 的 status 与 ruling 已是新值（experiment_record_smoke_20261127T130439Z.json:158-163）。

## 二、裁决第 1 项的落实

**ST11 读两者之和：已落实（静态核对；端到端测试已验证）**
- pilot.py:191-195 `return b17_hours + overhead_seconds / 3600.0`。
- preflight 在 pilot.py:646 计算这个和，写入 654 行的 "st11_estimate_hours"。
- step2 在 pilot.py:593 把 `pre["st11_estimate_hours"]` 传给 STP.st11。比较的值与记录中的值是同一个 dict 项，不可能不一致。
- 端到端测试 sum_over_bound 已通过（c4_02:149、155）。

**超过 3.5 小时即停：已落实**
- stops.py:133 用严格大于 `estimate_hours > contract.stops.st11_hours`，与协议 623 行「超过 3.5 小时」一致。
- 3.5 由 contract 从协议解析（contract.py:345；test_contract.py:21）。
- 恰好 3.5 h 时不停，由 sum_at_bound 与 test_st11 检验（c4_02:168-170，已验证）。

**B17 的文字与 status：已落实（已核对仓库文件）**
- status 为 ACCEPTED_C4 =「ACCEPTED（Review Gate 2026-11-27 修订）」，ruling 为「tasks/IMPL_C4_RULING.md 第 1 项」（interpretations.py:22-23、105）。两者与裁决原文一致，测试已断言（test_test_data.py:432、442-445）。
- 文字中开销的组成与 evaluation_plan 和 checkpoint_overhead_seconds 一致（pilot.py:177-178、186-188）：
  - 32 次基座加载 = 1 + 30 + 1；
  - 30 个 checkpoint，每个计 2 次哈希、保存、重载、文件哈希；
  - 另 18 次重载 = 3 + 15；
  - 17 次 TEST 状态哈希 = 16 + 1；
  - 15 次 TEST 文件哈希。
- 「Both parts and their sum are written into the step 2 record」与 pilot.py:652-654 一致。

**ST7 的事前判断不变：已落实**
- diff 没有改动 run_seconds、eval_seconds（pilot.py:345-362）与 test_evaluation_seconds 的计算行（208-209），只改了后者的 docstring。
- 两个钉住现行 ST7 计算的变异已测出（c4_02:175-178，已验证）。

**TEST 的事前估计不加余量：已落实**
- test_run_pilot.py:268 用精确相等断言。
- 「加 10% 余量」的变异已测出（c4_02:175-176，已验证）。

**补测试与变异：已落实**，详见第四节。

**口径说明（未验证，推理；不作为问题）**
- 和中的开销包含 15 次 TEST checkpoint 文件哈希。按 test_evaluation_seconds 的 docstring（pilot.py:201-202），它们发生在 GPU 计时开始之前；而 B17 估算是 GPU 时间口径。
- 因此 ST11 读到的和略高于 GPU 时间，偏保守。
- 这与裁决「B17 估算 + checkpoint 开销」以及 C2 报告中开销的定义相符。

## 三、重点问题

**preflight 与 step2 的接线（已核对仓库文件；测试已验证）**
- 和在 preflight 中计算一次，存入第 2 步记录；step2 读的就是记录中的这个值。
- ST11 停止时：stop_in_step 先写第 2 步记录，记录带 stopped，并提交推送；然后 run_gate 写 BLOCKED 实验记录。
- 不停止时：`pre["st11"]` 写为 "within bound"。
- 两种情形都由新测试在带裸远端的克隆上检验。

**冒烟模式下 ST11 的 "would stop"（未验证）**
- ST11 仍在 SMOKE_RECORDED_STOPS 中（pilot.py:92；test_run_pilot.py:169）。冒烟中超限时由 stop_check 记下带 SMOKE_LABEL 的条目并继续运行，step2 把 `pre["st11"]` 写为 "smoke: would stop"。
- 改为读和之后，CPU 冒烟更容易记下 "would stop"，但这不影响运行。
- 这一分支本身没有测试（见问题 7）。

**第 2 步记录字段改名对其他读取方的影响（已核对仓库文件）**
- src、tests、run_pilot.py 中没有读取旧字段名的代码。
- test_evaluate 只读 `step2["preflight"]["timing"]`（pilot.py:1206），这一字段未改。
- 实验记录与冒烟报告不读第 2 步的估算字段。
- 仍引用旧字段名的有两处（见问题 1、2）：RUNBOOK_A100.md:196、200，以及 data-auditor 的历史脚本。

**B17 文字与代码是否一致**：一致（见第二节）。只有几处措辞问题，见问题 4、6。

## 四、新测试与变异是否检验所说内容

**test_formal_st11_reads_b17_plus_the_checkpoint_overhead（已核对；运行结果已验证 c4_02:149-150、155）**
- 替换方式有效：
  - CP.estimate_total_hours 按模块属性调用（pilot.py:643），替换生效；
  - checkpoint_overhead_seconds 与 step3 按 pilot 模块全局名调用（pilot.py:645、989），替换生效；
  - st11_estimate_hours、stops.st11、stop_in_step、step_end、final_record 都是真实的。
- 两个参数检验的内容：
  - sum_over_bound：B17 = 3.0 不超限，加上 1801 s 后超限。它能区分「读和」与「只读 B17」。
  - sum_at_bound：检验严格大于。
- 浮点相等：3.0 + 1800/3600.0 恰为 3.5；JSON 往返不改变 float。

**9 个变异（已验证 c4_02:158-181）**
- 每个变异都由所指的全部测试测出。
- 变异 1、2、4 由 sum_over_bound 测出；3、5 由 sum_at_bound 测出（5 同时由 test_st11 测出）；6、7 由 B17 测试测出；8、9 钉住现行 ST7 的计算。
- 不足：B17 文字的检验只覆盖一句话（见问题 5）。

## 五、裁决第 2 项的处理

可以接受。理由如下：
- 裁决原文是「全部按现行实现接受，不改代码」，不改动这些项涉及的代码符合字面要求。
- 留下的 "for Review Gate" 注释与 docstring 不影响行为，也不写入任何记录。
- 但它们现在与事实不符，应当登记（见问题 3）。
- 只改注释是否属于「不改代码」所禁止的范围，原文没有明说，建议请 Review Gate 确认。

## 六、问题

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:195-200 | 【已核对仓库文件】本提交之后，RUNBOOK 与代码不一致。它仍写「ST11 读 `b17_estimate_hours`」「B17 超过 3.5 小时即 ST11」，引用了已删除的字段 `b17_plus_checkpoint_overhead_hours_report_only`，并保留「只报告；C2 待决第 2 项」「若 Review Gate 决定」的措辞。照现在的 RUNBOOK 操作的人会去找不存在的字段，也会误判 ST11 的口径。Executor 已说明改在随后只改文档的提交中，这符合裁决第 7 项 | `预检之后,以第 2 步记录中的实测值为准:ST11 读 \`b17_estimate_hours\`…;\`b17_plus_checkpoint_overhead_hours_report_only\` 与第三行比较` | 随后的文档提交中把时长表与第 200 行改为 ST11 读 `st11_estimate_hours`（= `b17_estimate_hours` + `checkpoint_overhead.seconds`/3600），并写明区间上端会触发 ST11。该提交必须在任何 A100 运行之前推送；在报告中登记

MINOR | metrix/e1-pilot/audit/ic8_06_smoke_labels.py:129-147；ic9_06_smoke_labels.py:130-148；ic10_06_smoke_labels.py:131-150；ic10_04e_lookahead.py:160-166 | 【已核对仓库文件；运行后果未验证】data-auditor 的历史脚本读取已删除的字段 `checkpoint_overhead_report_only` 与 `b17_plus_checkpoint_overhead_hours_report_only`。若把它们用在 c4 及以后的冒烟记录上，会因 KeyError 失败。它们是历史证据，不应修改 | `rc = pre["checkpoint_overhead_report_only"]["counts"]` | 调用 data-auditor 时说明字段已改名（新字段为 checkpoint_overhead、st11_estimate_hours、st11_reads），由它另写新脚本；登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:830-833、1010-1011、1036、1066-1067 | 【已核对仓库文件】C2 待决第 1、3、5 项已由裁决第 2 项接受，但这些注释与 docstring 仍写「is for Review Gate (reports/IMPL_C_REPORT.md)」，现在与事实不符。按「不改代码」的字面要求不改，可以接受（见第五节） | `# reads an excluded configuration is for Review Gate (reports/IMPL_C_REPORT.md).`；`(NOT_TESTED: the word for a crash is for Review Gate, reports/IMPL_C_REPORT.md)`；`belongs in the repository is for Review Gate (protocol section 10; reports/IMPL_C_REPORT.md).` | 在 DEFERRED_MINORS 中逐行登记；请 Review Gate 确认是否允许只改注释。允许时，在下一个代码提交中改为「accepted as implemented (tasks/IMPL_C4_RULING.md item 2)」

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:52-53 | 【已核对仓库文件】模块 docstring 中的括号挂错了对象。"(st11_estimate_hours)" 跟在 "the checkpoint overhead" 后面，但开销由 checkpoint_overhead_seconds 计算，st11_estimate_hours 计算的是两者之和 | `ST11 reads the sum of B17's estimate (compute.estimate_total_hours) and the checkpoint overhead\n(st11_estimate_hours) and stops above 3.5 hours.` | 改为 "ST11 reads st11_estimate_hours = B17's estimate (compute.estimate_total_hours) + the checkpoint overhead (checkpoint_overhead_seconds) and stops above 3.5 hours"

MINOR | metrix/e1-pilot/tests/test_test_data.py:446；reports/impl_c/c4_mutate.py:83-85；src/metrix_e1/interpretations.py:211-216 | 【已核对仓库文件；推理，未验证】B17 文字的检验只断言一句 "B17's estimate + the checkpoint overhead"。文字中写死的计数（32、30、18、17、15）与 evaluation_plan 没有关联。以后若计数或开销公式改了而文字没改，没有测试会失败；只删开销组成那一句的变异也测不出 | `assert "B17's estimate + the checkpoint overhead" in recs[16]["text"]` | 在测试中断言文字中的各个计数等于 P.evaluation_plan(contract) 的对应值，例如检查 "x 32 base-model loads"、"x 18 further checkpoint reloads" 等子串；或登记

MINOR | metrix/e1-pilot/src/metrix_e1/compute.py:6；tests/test_stops.py:4 | 【已核对仓库文件】B17 修订后，「preflight estimate」指的是两者之和，而这两处仍把 compute.estimate_total_hours 称为 ST11 读的预检估算 | compute.py:6 `interpretations B17 (preflight estimate)`；test_stops.py:4 `and the preflight estimate feeding ST11.` | 改为 "B17's estimate (one part of ST11's estimate, pilot.st11_estimate_hours)"；或登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:594（else 分支）；tests/ | 【已核对 tests：没有任何测试走到这一分支】冒烟模式下 ST11 "would stop" 的分支（`pre["st11"] = "smoke: would stop"`，以及 smoke_stops 中带标签的 ST11 条目）没有测试。c4 冒烟是 "within bound"（c4_03:272，已验证），也没有走到它。通用的 stop_check 路径只用 ST2 测过（test_run_pilot.py:156-169）。这是原有缺口，与本次改动无关，本次只是让它更容易被触发 | `pre["st11"] = "within bound" if ok else "smoke: would stop"` | 加一个冒烟模式的单元测试：把估算替换为 3.6 h，断言第 2 步记录中 st11 为 "smoke: would stop"、smoke_stops 中有 ST11 与 SMOKE_LABEL、运行继续；或登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:646、655、658-659 | 【已核对仓库文件】局部变量 `st11_hours` 存的是估算值，而同一处的 `p.contract.stops.st11_hours` 是上限，两者同名不同义，并在同一个 log 调用中并列出现 | `st11_hours = st11_estimate_hours(hours, overhead)` …… `st11_hours, p.contract.stops.st11_hours))` | 把局部变量改名为 `st11_estimate`

MINOR | metrix/e1-pilot/src/metrix_e1/stops.py:134（本次未改）；tests/test_run_pilot.py:763 | 【推理，未验证】ST11 的停止消息用 %.3f 显示。改为读和之后，紧贴上限的情形更可能出现：1801 s 时消息为 "preflight estimate 3.500 h > 3.5 h"，读者会以为两边相等。不影响判定 | `"preflight estimate %.3f h > %g h" % (estimate_hours, contract.stops.st11_hours)` | 消息中同时给出秒数，或用更多位小数；登记

MINOR | metrix/e1-pilot/src/metrix_e1/interpretations.py:12-15 | 【已核对仓库文件】B1–B24 的说明记了作用范围（"scope: this stage"），而 B17 修订的说明没有记裁决的作用范围（「E1 Pilot 直至结束」）。metrix/CLAUDE.md 第 8 节要求裁决写入决定记录时注明作用范围；interpretations 会写入每份实验记录 | `Review Gate revised B17 on\n2026-11-27 (tasks/IMPL_C4_RULING.md item 1: ST11 reads …): status\nACCEPTED_C4, reference RULING_REF_C4.` | 在 docstring 中补上 "(scope: E1 Pilot until its end)"；或在 IMPL_C_REPORT 的决定记录中注明，并登记

结论：PASS
