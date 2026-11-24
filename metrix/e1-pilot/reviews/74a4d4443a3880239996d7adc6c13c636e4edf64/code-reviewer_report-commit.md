# code-reviewer final report, Implementation stage B report commit (staged; parent 493d7f9c102cae3ebb916f1d72fcc1759b26bee8); invoked 2026-11-23 (background), stopped by an API usage limit (HTTP 429), resumed 2026-11-24 after a worker restart; invocation text: code-reviewer_prompt_report-commit.txt; resume message: resume_message_code-reviewer_report-commit.txt; inputs: report_commit_input.diff, report_commit_input_src_tests_reports.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a6e190e4e566fe3b6.jsonl)
---
code-reviewer：Metrix E1-PILOT Implementation 阶段 B 报告提交（暂存，未提交；父提交 493d7f9c102cae3ebb916f1d72fcc1759b26bee8），中断后续审

结论：PASS，没有 BLOCKER。共 1 条 MAJOR、12 条 MINOR。
- MAJOR 交 Review Gate：报告“待决第 3 项”列出了 test 行被 UTF-8 解码的运行，但漏掉了一整类，即阶段 A 与阶段 B 修复前 `data.py` 自身以文本模式读取的运行。
- 上一轮 8 条 MINOR 都已修或登记充分。代码与测试改动正确；共用检查函数之后，TEST 生成器的行为不变。

审查方式：
- 两次调用（含本次续审）前都读了 /home/user/OpenMythos/.claude/agents/code-reviewer.md，tools 行为 `Read, Grep, Glob`，与已加载的定义一致。
- 只用 Read、Grep、Glob，没有执行任何命令。只靠读代码得出的判断标『未验证』。
- 引用本提交暂存、或仓库已有原始输出（文件与行号）的判断标『已验证』，与前几轮的标法相同。
- 中断记录 /tmp/claude-0/-home-user/f24b86c9-a2c5-5317-8b43-751d1f505d91/scratchpad/review_report/interruption_report-commit.txt 第 5–16 行显示：HEAD 未变；暂存内容与两份审查输入逐字节相同；没有未暂存或未跟踪的文件。所以中断前我读到的工作区内容仍然有效。这份文件不在仓库中，相关判断标『未验证』。

## 一、上一轮各项核对

| 上一轮项目 | 判断 | 依据 |
|---|---|---|
| MAJOR：l6_check.py 过去的运行如何定性 | 已登记，交 Review Gate。BC1 写明裁决前不再对完整文件运行，这一条充分。但运行清单不完整，见第二节 MAJOR | IMPL_B_REPORT.md:134-139；DEFERRED_MINORS.md BC1『已验证』 |
| MINOR 1：verify_authorization 的缺口 | 已修，正确。测试有一处不再能区分，见第二节 MINOR 1 | 见下方说明 |
| MINOR 2：循环内非有限值 | 已修，正确 | test_evaluate.py:179-199。t12_fix3.txt:68-69：去掉循环内检查后 `test_nonfinite_logits_stop_em_generation` 失败『已验证』 |
| MINOR 3：多余空行 | 已修 | test_evaluate.py:177-178 现在是 2 个空行『未验证』 |
| MINOR 4：解释裁决测试依赖当前状态 | 已修，正确 | 见下方说明 |
| MINOR 5：_dev_rows_only | 已修，正确 | 见下方说明 |
| MINOR 6：审查记录未入库 | 已修 | 见下方说明 |
| MINOR 7：t10 的 grep 口径 | 已修 | t12_fix3.txt:18-59 列出了 src/、tests/ 中全部 `open(`、`read_text(`、`read_bytes(` 调用，eval_sets.jsonl 只以 "rb" 打开（data.py:507、test_data_hashes.py:88）『已验证』。我对 reports/*.py 做了 Grep，只有 round5/l6_check.py:82 以文本模式打开它，与 BD7 的说法一致『未验证』 |
| MINOR 8：ST10 凭据与“只评一次” | 登记充分 | IMPL_B_REPORT.md“留给阶段 C 的事项”写明两项是硬性前提，缺任一项不进入 TEST 评测；DEFERRED_MINORS BB1、BC2、BD8 一致『已验证』 |

各项说明：

**MINOR 1（verify_authorization）**
- leakage.py:227-247 现在复核以下各项：
  - 授权的冻结提交，同时等于当前 PROTOCOL_FROZEN 与 fz.record.commit；
  - 两份记录已提交，且 sha256 与授权所带一致；
  - `R.gate0_record_problem`、`R.freeze_record_problem`（与生成器共用）；
  - 数据内容哈希与冻结值比较（`fz.data_hash`）；
  - `INT.pending()` 为空。
- 文档字符串准确写明了复核的各项，以及“不复核条件 1”。
- t12_fix3.txt:67-88 的变异检查：去掉 pending、冻结记录内容、fz 提交、checkpoint、数据哈希中的任一项，对应用例都会失败『已验证』。

**MINOR 4（解释裁决测试）**
- test_test_data.py:185-193 用 monkeypatch 构造两种状态：一条待决（正则以 `$` 锚定），以及全部已裁决。不再依赖 INT.ENTRIES 的当前内容。
- t12_fix3.txt:267 PASSED『已验证』。

**MINOR 5（_dev_rows_only）**
- test_data_hashes.py:84-100：
  - 过滤前用 `FZ.file_sha256(src)` 与 `fz.data_hash("eval_sets")` 比较；
  - 路径取 `D.params(fz).general_source`；
  - manifest 副本取 `copy.deepcopy(fz.data_manifest)`。
- 计数改与 `rows_by_split` 比较。它与 data.py 用的是同一个正则、读的是同一个文件，独立性不如原来写死的 400/800，但已能发现正则不匹配的情况。
- t12_fix3.txt:120 PASSED『已验证』。

**MINOR 6（审查记录入库）**
- t12b_review_records_copy.txt:3-8：三个目录 `diff -r` 都是 exit=0。
- t12b_review_records_copy.txt:9-26：auditor 试跑输出逐个 `cmp` 都是 exit=0。
- t12b_review_records_copy.txt:41-42：`review_input.diff` 与 `review_input_round1.diff` 的 sha256 相同。
- 我用 Glob 核对，audit/ib_*、ic_*、id_*、ie_*、stdout/impl_b/00–49 号与 trials/ 都在『已验证』。

**共用函数之后，TEST 生成器的行为是否不变**
- test_data.check_gate0_record 与 check_selection_record 改为调用 record.py:194-220 的共用函数。
- 检查顺序不变：先训练计划，再数据哈希、checkpoint、绑定。异常类不变（PreconditionFailed）。只有报错文字变了。
- 生成器传入的仍是数据目录的内容哈希（test_data.py:91）。
- t12_fix3.txt:82-88：去掉 record.py 中的 checkpoint 检查或数据哈希检查后，`test_selection_record_condition[checkpoint]`、`[data_hashes]` 失败。这证明生成器确实走共用函数『已验证』。
- t12_fix3.txt:60-66：当前状态下拒绝运行，exit=1，没有输出目录『已验证』。

**TEST 隔离**
- 三个 TEST 入口的第一条语句都是 verify_authorization：test_data.py:126、leakage.py:256、evaluate.py:318-324（evaluate.py 先做模式检查）。
- test_generation_needs_authorization 断言两种手造授权都在任何读取之前被拒（`called == []`）。
- t12_fix3.txt:250 PASSED『已验证』。

## 二、问题清单

MAJOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:134-139；DEFERRED_MINORS.md:363（BA8） | 待决第 3 项交给 Review Gate 的“已经发生的、以文本模式读取完整文件的运行”只列了 l6_check.py 的运行，漏掉了包内 data.py 的运行。data-auditor 第 1 轮观察 1 指出：工作提交修复之前，`data.build_general_dev` 用文本模式打开 eval_sets.jsonl。这个状态从阶段 A 就存在，前提条件 1 的 `D.verify` 也会走这条路径。所以以下运行在严读法下同样解码了 test 行，清单中都没有：阶段 A 的 `metrix_e1.data generate` 与 `verify`（impl_a/t2_fetch_generate.txt:27、47、78、92、122、154；t6_fix_commit.txt:21、45）；阶段 B 修复前的 impl_b/t1_env_baseline.txt:97、t3_generate_leakage.txt:3、36；以及修复前 TEST 生成器拒绝运行时的条件 1。已列出的 pytest 运行也经由 data.py 解码，不只经由 l6_check.py。这个读法问题本身（上一轮的 MAJOR）仍待 Review Gate 裁决；严读法下的后果是 ST13，所以交给裁决方的清单应当完整。不确定之处：阶段 A 运行 t2 时 data.py 是否已经是文本模式，我只能核实 0bc0eecf 时的状态 | reviews/74a4d444…/review_input_round2.diff:1715 `-    with open(eval_sets_path, encoding="utf-8") as fh:`（相对 0bc0eecf）；data-auditor_round1.md:217-221；impl_a/t2、t6、impl_b/t1、t3 中的命令行『已验证』。t2 当时的读法『未验证』 | 在第 3 项中补一条：“包内 data.py 在工作提交修复之前以文本模式读取，已执行的运行：……（逐个文件与行号，含 data generate、verify 与条件 1）”。BA8 的处理改为指向第 3 项，不再只指向 BB4

MINOR | metrix/e1-pilot/src/metrix_e1/leakage.py:227-229；metrix/e1-pilot/tests/test_test_data.py:243、255 | 三方比较合成了一个条件，报错文字也只有一句，所以 `other_protocol_frozen` 用例不再能区分“与当前 PROTOCOL_FROZEN 比较”这一项。若把条件改成 `authorization.frozen_commit == fz.record.commit`（去掉 `current`），该用例在授权 "1"*40 时仍会抛出同一句含 "PROTOCOL_FROZEN names" 的错误，测试照样通过。没有任何用例构造“授权等于 fz 的冻结提交、但不等于当前 PROTOCOL_FROZEN”的情况。t12 的变异只去掉了 fz 这一侧 | `if not authorization.frozen_commit == current == fz.record.commit:`；VERIFY_CASES `"other_protocol_frozen": "PROTOCOL_FROZEN names"`『未验证』 | 两项分开比较、分开报错；或增加一个用例，让 fz.record.commit 等于授权、而 _repo 中的 PROTOCOL_FROZEN 指向另一个提交

MINOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:104 | 说法超出证据。报告写“授权复核各分支（冻结提交与当前 PROTOCOL_FROZEN、……哈希；Gate 0 状态；选定配置、……绑定；待决解释），逐项去掉检查后对应用例失败（t12）”。t12 的变异只有 6 项：循环内 NaN、pending、整个 freeze_record_problem 调用、fz 提交、checkpoint、数据哈希。Gate 0 状态、sha256 比对、当前 PROTOCOL_FROZEN、选定配置、绑定都没有单独做变异；其中当前 PROTOCOL_FROZEN 一项按上一条实际检不出 | mutate_fix3.py:5-13；t12_fix3.txt:67-88『已验证』 | 改为准确列出 t12 变异了哪几项，其余写明“由用例的 match 串覆盖（未做变异）”；或补做变异

MINOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:118 | 数字与审查原文不符。报告说“MAJOR 1–10 中 8 条改代码，B5、B14、B17 交 Review Gate”，8 + 3 = 11，而 MAJOR 只有 10 条。第 2 轮原文显示改了代码的有 9 条（含 B5 的 r.uniform 与 B17 的估算方法），只登记、未改代码的只有 B14 | reviews/74a4d444…/code-reviewer_round2.md:17-61（MAJOR 6、10 都是“已修”）『已验证』 | 改为“9 条改代码（其中 B5、B17 改后仍交 Review Gate），B14 只登记”

MINOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:9、114；metrix/e1-pilot/reports/DEFERRED_MINORS.md:393 | 两份文件对报告提交审查记录的位置说法不一。报告说放在 `reviews/74a4d444…/` 的 `*_report-commit*`（阶段 A 的先例），DEFERRED_MINORS 1.25 说放在 `reviews/<报告提交>/`。另外，第 114 行的路径对照只写了 review_work/、review_fix/、review_fix2/，没有写本轮输入所在的 review_report/ | `本报告提交的审查见 reviews/<报告提交>/`，对比 `按阶段 A 的先例放在这里的报告提交审查 *_report-commit*`『已验证』 | 统一为一个位置，并在对照中补上 `review_report/X → reviews/74a4d444…/X`（或实际采用的目录）

MINOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:50、156 | 本报告提交的推送输出 t13 计划留在工作区，到阶段 C 的第一个提交才入库。本报告第 31 行自己记载了同样做法的后果：阶段 A 的 impl_a/t8_report_push.txt 因容器回收而丢失。这不符合 metrix/CLAUDE.md 第 9 节“原始输出一律写入仓库并推送，不留在临时目录” | `impl_a/t8_report_push.txt 已不在（阶段 A 容器回收，任何提交中都没有）`；Glob reports/impl_a/ 中只有 t0–t7『已验证』 | 推送后立即做一个只含 t13 的证据提交并快进推送（同第 0 步 0bc0eecf 的做法），或交 Review Gate 明确接受这一延迟

MINOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:6 | “中断”一段只写了两次重启。本轮审查因 HTTP 429 中止，随后第三次重启（uptime -s 2026-11-24 03:30:52）；中断后的核对记录 interruption_report-commit.txt 也不在暂存内容中 | 中断记录第 1–3 行『未验证』（会话临时目录，未入库） | 审查后补入报告的“中断”一段，并把中断记录与审查原文一起入库，放入 report_commit_post_review.diff

MINOR | metrix/e1-pilot/reports/impl_b/t12_fix3.txt:6-15、309 | 被测代码与暂存内容之间只有 `git diff --stat` 的行数对应（8 个文件，+183 −91，与暂存 stat 一致），没有哈希。变异后源码已复原，只能由随后 204 passed 间接证明 | t12 只有 `git diff --stat HEAD` 与 `git status --short`『已验证』 | 以后在 pytest 前后各记录一次 `git diff HEAD -- src tests | sha256sum`，并与审查输入中的同一部分比较

MINOR | metrix/e1-pilot/src/metrix_e1/test_data.py:81-83；leakage.py:245-247；frozen.py:75-76、297-302 | 重复逻辑：
- 记录内容检查已经共用，解释裁决检查却仍是两份同样的代码，报错文字也相同；
- CONTENT_HASH_KEYS 的注释说它是 `Frozen.content_hashes` 的键，但 content_hashes 自己另写了一遍字面键，二者只靠 test_four_frozen_hashes 绑定 | `open_ids = INT.pending()` 出现两处；`"facts": …, "train_S": …` 为字面量『未验证』 | 抽一个 `interpretations.pending_problem()` 供两处调用；content_hashes 按 CONTENT_HASH_KEYS 组装，或在构造后断言键相同

MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:322-323；metrix/e1-pilot/tests/test_evaluate.py:199-200 | 测试细节：
- `fz is None` 分支没有测试；
- LateNaNStub 用例没有断言 `e.value.values` 非空，空列表也能使 `all(...)` 为 True（第一个用例断言了）；
- 对照里写死 16，没有用 `ev.max_new_tokens` | `assert late.calls == 2 and e.value.stop == "ST6" and all(v != v for v in e.value.values)`；`== [[374] * 16]`『未验证』 | 补 `fz=None` 的用例，断言里加上 `e.value.values and`，并改用 `contract.evaluation.max_new_tokens`

MINOR | metrix/e1-pilot/reports/IMPL_B_REPORT.md:148 | “只在阶段 C 接线的函数”不完整。compute.run_flops、compute.preflight_summary、compute.estimate_total_hours 在 src 中同样没有调用方，前两个在第 1 轮死代码 MINOR 中点过名，1.22 节 BA5 也没有列 | Grep 在 src 中只命中它们的定义（compute.py:163、190、213）『未验证』 | 补入这份列表与 BA5

MINOR | metrix/e1-pilot/src/metrix_e1/record.py:221 | 文件末尾多了一个空行（W391） | diff 中 `+    return None` 之后是一行只有 `+` 的空行『未验证』 | 删去

MINOR | metrix/e1-pilot/reports/impl_b/mutate_fix3.py:3 | 变量 SP 赋值后从未使用 | `SP, PY = sys.argv[1], sys.argv[2]`『未验证』 | 删去 SP，或用它来记录临时目录

## 三、核对后未发现问题的部分

- **t11_fix2_commit_push.txt**『已验证』：
  - 第 7-8 行：493d7f9c 的 diff 与审查输入逐字节相同。
  - 第 10-21 行：metrix/ 以外的检查 RESULT: PASS。
  - 第 33-39 行：快进推送 `fdbb9de..493d7f9`。
  - 第 22-28、40-46 行：推送前后两个标签不变。
- **审查记录中的数字与原文一致**『已验证』，引用的行号都在原文中：
  - 第 1 轮 10 MAJOR、19 MINOR（code-reviewer_round1.md:21-51），3 条观察（data-auditor_round1.md:217-223）；
  - 第 2 轮 2 MAJOR、15 MINOR（code-reviewer_round2.md:94-126），6 条观察；
  - 修复提交 1 MAJOR、9 MINOR，4 条观察；
  - 第二个修复提交 1 MAJOR、8 MINOR，7 条观察、20 个埋入故障全部检出（data-auditor.md:8、195、250-266）；
  - 逐个核对存在：BA1–BA10、BB1–BB6、BC1–BC4、BD1–BD10 的来源行号（IB1-CR:26/29/30/34/37/41/46/76、IB1-DA:217/222/223、IB2-CR:96/102/124、IB2-DA:213/225/226、IBF-CR:63/69/81、IBF-DA:220、IBF2-CR:78–92、IBF2-DA:254/256）。
- **DEFERRED_MINORS 遗漏核对**：此前各轮未修的项都已登记，或已由后续审查确认修复。例外是第二节 MAJOR（data.py 的运行）与 run_flops / preflight_summary 两项。
- **报告中的其它数字**：
  - Y/F 比值与 t3_generate_leakage.txt:8-10 一致；
  - 204 passed 见 t12_fix3.txt:309；198 passed 见 t10；
  - 待决第 3 项引用的 round5/t5_l6_check.txt、round6/t2_l6_check.txt、round6/t2_l6_judgment_demo.txt 都存在；
  - pytest 运行的文件与行号与 Grep 一致（impl_a/t4:42、131，t6:70；impl_b/t1:118、t4:3、t6:79、t8:86）『已验证』。
- **供参考**：data-auditor 的 id_06、ie_06 静态脚本按旧签名写死了比较串（例如 `"verify_authorization(authorization, repo_root)"`），对本提交重跑会判不一致。这属于 data-auditor 自己的脚本，不是本提交的问题『未验证』。

结论：PASS
