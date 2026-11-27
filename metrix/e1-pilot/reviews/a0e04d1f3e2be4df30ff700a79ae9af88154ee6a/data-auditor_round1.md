# data-auditor, C2 third fix commit, round 1: final report, unchanged (extracted by reports/round6/review_extract.py from data-auditor_round1_transcript.jsonl)
# staged tree c7869d358c4adf6677d0f9843937bb6f3009b67b, parent 2665ab1036b66180ef1dee6b869135a45efefaa5; invocation text: data-auditor_prompt.txt
---
## data-auditor 审计报告：C2 第三个修复提交，第 1 轮

审计对象：暂存树 c7869d358c4adf6677d0f9843937bb6f3009b67b，父提交 2665ab1036b66180ef1dee6b869135a45efefaa5。

**结论：四项任务都已复算，结果都与 Executor 一致，没有 BLOCKER。另登记 1 个 MINOR（IC10-M1），并附 3 条观察，都在防范对象之外。**

- 按 metrix/CLAUDE.md 第 10 节，data-auditor 仍是「待验证」，本次 PASS 只作参考。
- 判定范围按 C1 裁决的防范对象：按 RUNBOOK 操作时意外评测 TEST 两次，或在 ST10 不成立时评测 TEST。2026-11-27 裁决第 1 项（TEST 评测调用不 fetch，只在 begin 与 finish 时 fetch）按已接受的设计处理。

### 运行环境与限制
- 主机 `vm`，Anthropic 云容器，只用 CPU，`/dev` 下没有 nvidia 设备。
- 只加载了 Qwen 分词器。30 个冒烟 checkpoint 只对文件字节做哈希，没有加载。
- 驱动测试用的是 Executor 测试自建的随机小模型。e2e 中的 TEST 行是测试夹具写的合成行。没有生成、读取或统计真实 TEST。
- 只写入 `metrix/e1-pilot/audit/`，暂存区没有改动。证据：全部运行结束后，ic10_00b 显示 index 与 c7869d35 的 6812 个条目逐项相同，正文与 ic10_00 逐字相同。
- e2e 驱动一次只运行一个，没有并行。所有 python 调用都带 `-B`，并设 PYTHONDONTWRITEBYTECODE=1，没有写入 .pyc。

记号：`$S`=/tmp/claude-0/-home-user/14ee74de-5799-5f8c-a07c-f9bcdb0676fe/scratchpad，`$P`=`$S/venv/bin/python`。每条命令都在 audit/ 目录下以 `bash ic10_run_logged.sh <stdout 文件> …` 运行。

**脚本**，都在 /home/user/OpenMythos/metrix/e1-pilot/audit/：
- 运行与状态：ic10_run_logged.sh、ic10_00_state.py
- 数据：ic10_01_hashes.py、ic10_02_data_recheck.py、ic10_03_test_refusal.py
- 静态与数值：ic10_04_static.py、ic10_04e_lookahead.py、ic10_04e_probe.py
- 驱动：ic10_04_e2e.py、ic10_04_trace_plugin.py、ic10_04f_wiring.py、ic10_04d_branch_tests.py、ic10_04d_plugin.py
- 训练与补充：ic10_05_trainings.py、ic10_06_smoke_labels.py、ic10_07_mutation_remnants.py

**完整 stdout**，都在 /home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/：
- 状态：ic10_00_state.txt、ic10_00b_state_final.txt
- 数据：ic10_01_hashes.txt、ic10_02_data_recheck.txt、ic10_03_test_refusal.txt
- 静态与数值：ic10_04_static.txt、ic10_04e_lookahead.txt
- e2e：ic10_04a_e2e_normal.txt、ic10_04b_e2e_stop_after_marker.txt、ic10_04c_e2e_crash_after_marker.txt、ic10_04e2_e2e_st7_before_begin.txt、ic10_04d_e2e_interrupt_after_marker.txt
- 其他驱动：ic10_04f_wiring.txt、ic10_04d_branch_tests.txt
- 其余：ic10_05_trainings.txt、ic10_06_smoke_labels.txt、ic10_07_mutation_remnants.txt、ic10_99_git_status_final.txt
- 试跑与作废输出也都保留：*_trial1_script_error.txt、*_run1_superseded_plugin_change.txt。逐条原因见 ic10_0x_trials_and_script_fixes.txt：
  - 4 次失败都是我自己脚本的预期或窗口写错，与 Executor 的代码无关。
  - 4 个 run1 都是 PASS；之后插件增加了类方法包装，所以全部重跑。

### 0. 审计对象的状态（ic10_00 / ic10_00b，RESULT: PASS）
- 命令：`$P -I -B ic10_00_state.py /home/user/OpenMythos $S/review_c2d $S/c2d_smoke`
- 原始输出摘录：
  - `HEAD 2665ab10… == parent: True`
  - `tree.txt listing 1223 entries == git ls-tree -r c7869d35 -- metrix/e1-pilot (1223 entries; the whole tree has 6812): True`
  - `index entries 6812 | tree c7869d35 entries 6812 | identical: True`
  - staged diff 是 input.diff 的尾部：True
  - `input_code.diff sha256 197464e0… == git diff --cached …: True`
  - `working tree == index for src/tests/run_pilot.py: True`，代码 diff 的 sha256 为 `b0a72366…`
  - c2d_01：两处 diff sha256 都等于 b0a72366；两处 ls-files 代码块都等于暂存树的代码条目；c2_mutate_fix3.py（bf635c87）与 c2d_checks.sh（3d489233）的 sha256 行共 4 条，都等于暂存 blob
  - c2d_02：两处 diff sha256、两处 ls-files 代码块都相等；写树两次都是 da82a1e1
  - `diff-tree da82a1e1..c7869d35: 46 paths, change kinds ['A']; paths other than c2d_01, c2d_02 and the smoke-record copies: [] | its code entries == the staged tree's: True`
  - 冒烟记录副本 44 个，其中 43 个与 `$S/c2d_smoke/records` 逐字节相同，另 1 个是 LABEL.txt；没复制的只有 details/
  - RUNBOOK_A100.md、c3_hf_tree_70d244cc.txt、c3_checks.sh 都是 `??`，未暂存
- 与 Executor 一致：
  - 写树 da82a1e1 到送审树之间只新增了证据文件，代码相同。
  - 录制首行与 c2d_checks.sh 第 9 行写的「2665ab17」是笔误，两份录制中 `git rev-parse HEAD` 的行给出完整父提交，与说明一致。
- 观察：c2d_02 的首尾只记录了写树、diff sha256 与 ls-files，没有记录脚本的 sha256。Executor 说「同样记录」不完全准确；两个脚本的 sha256 在 c2d_01 中有记录，所以不影响证据。

### 1. 冒烟数据目录与 TEST 生成器拒绝（ic10_01 / 02 / 03，均 RESULT: PASS）
- 命令：
  - `$P -I -B ic10_01_hashes.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2d_smoke $S/c2d_data`
  - `$P -I -B ic10_02_data_recheck.py … $S/c2d_smoke`
  - `$P -I -B ic10_03_test_refusal.py /home/user/OpenMythos $P $S/inputs $S/c2d_smoke $S/ic10_test_out`
- 四个冻结内容哈希，每个都是「我的值 = PROTOCOL_FROZEN = step1_record」，`ALL EQUAL True`：
  - facts 406c8801…6b97
  - train_S 686fdd2f…bc1e
  - candidates e5d15c99…3705
  - anchor_texts 8828bc4f…2408；我用分词器解码 512 篇锚文本的 ids 得到同一个值
- 8 个文件：byte 与 canonical 哈希同时等于 step1_record、我阶段 B 的记录、c2d_01 的清单，c2d_data 的字节也相同。
- step1_manifest_fields：`DATA_MANIFEST.json files == mine: True | SPLIT_MANIFEST.json split_sha256 == mine: True`。
  - TEST 条目保持冻结值，test_qa 为 null。
  - 两个 manifest 的工作区与 index 都等于冻结字节。
- 模板：32 个，template_set_sha256 为 2b524113…e28f，三方相等。
- L1–L6 的 Gate 0 部分：
  - L1、L3a、L3b、L4、L5、L6 都是 0；L2 为 0.2，配对 capital.TRAIN.1 / capital.DEV.1。
  - 我的值、step2 报告、我阶段 A 的记录三方相等，detail 逐项相等，result 为 PASS。
- 候选可行性：`minimum available 5 | minimum pool 4 | cells with available < 4: [] | cells with pool < 4: []`；160 个列表中违反四重约束的为 0。
- split：
  - 160 个 fact_id 互不相同，learned 120、unread 40，两者不交；8 个 cell 各 15+5。
  - TRAIN 中没有 unread 的 fact；F 120、S 120、Y 240。
  - dev_qa 320；general DEV 每个 domain 25 条；锚文本 512。
- 冒烟没有产生 TEST 内容：119 个文件中没有 test_qa 或 general_test；step8 记录 returncode 1、refused True。
- 生成器黑盒运行。运行前写出的预期即下面三行、exit 1；原始输出：
  ```
  TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
  no TEST content was generated, read or written
  RESULT: FAIL
  ```
  - exit 1，--out 没有创建。
  - 数据目录、inputs、src 与 git status 都没有变化。
  - 拒绝行与 c2d_01 相同。
- 与 Executor 一致。

### 2. e2e 驱动与 begin_wiring 驱动
驱动方式：Executor 的测试作为子进程运行，加我的透传追踪插件。预期在运行前打印。

**我的 TEST look-ahead 模型（夹具 timing）**：1 + 15×0.1 + 16×1×3/2 + 17×0.1 = **28.2 s**，去掉了文件哈希项。

**normal（ic10_04a：`1 passed in 241.65s`，RESULT: PASS）**
- 第 0、1、2 次运行，begin 之前的顺序都与预期相等：
  - 顺序：`TG.code_commit < start_checks('test-evaluate') < refuse_if_test_evaluated < check_preconditions < device_check`。
  - refuse_if_test_evaluated 返回前只有两条 git 命令：`['cat-file','blob','HEAD:…/test_evaluation_result.json']`、`['cat-file','blob','HEAD:…/test_evaluation_marker.json']`。
  - begin 之前没有 fetch 或 push。
- 第 0 次（N 的哈希不符）：
  - look-ahead `[28.2]`，before_run `[28.2]`。
  - 返回 `(False,'BLOCKED')`，没有记录；之后的标志为 `(False, None)`。
- 第 1 次（改动的 checkpoint 文件）：只哈希 1 个 .pt，没有 look-ahead，没有记录。
- 第 2 次（评测）：
  - begin 入口处为 `(True, True, False, False)`。
  - 16 次 TEST 评测，16 次 claim。
  - fetch 只发生在 `['begin_test_evaluation','final_record','finish_test_evaluation']` 之内，评测与 claim 之内没有 fetch。
  - 之后的标志为 `(True, False)`。
- **第 3 次**（测试把 before_run 换成抛 ST7 的函数），观察到：
  - `'refuse_if_test_evaluated': [('raise','TestAlreadyEvaluated')], 'refuse_git': [], 'check_preconditions': 0, 'device_check': 0, 'before_run': [], 'base_model': 0, 'begin': False, 'final_record': 0, 'write_experiment_record': 0, 'commit_paths': 0, 'network_git': [], 'committed_reads': 0, 'end': ('raise','TestAlreadyEvaluated'), 'flags_after': (False, None)`
  - 调用顺序以 `['test_evaluate','TG.code_commit','Pilot.start_checks','refuse_if_test_evaluated']` 开头。
  - `p.before_run events in run 3 (the ST7 raiser): 0`
  - 结果文件在工作区，所以短路，没有任何 git 命令。与预期相等。
- 远端在夹具之后只有 3 个提交：marker、result、实验记录（PIPELINE_NOT_QUALIFIED）。
- 其余：没有合成文字，没有 general_test 键或逐题字段；克隆工作区干净；本仓库没有变化。

**stop_after_marker（ic10_04b）**
- pytest 退出码 1，与预期相同。
- final_record 为 `('test-evaluate','BLOCKED',['stopped','test_begun'],True)`，停止码为 None。
- 远端为 marker 加实验记录。

**crash_after_marker（ic10_04c）**
- 退出码 1。记录为 BLOCKED `crash after the TEST marker: RuntimeError('auditor-injected…')`，test_begun 为 True。
- 记录已推送，异常原样抛出。

**st7_before_begin（ic10_04e2，补充）**
- begin 之前的部分与预期相等，然后在 before_run(28.2) 处注入 ST7。
- 记录为 BLOCKED，停止码 ST7，test_begun False，已推送。
- 远端只有 1 个提交，没有标记。标志为 `(False, None)`。

**interrupt_after_marker（ic10_04d_e2e，补充）**
- 退出码 2。记录为 BLOCKED `crash … KeyboardInterrupt(…)`，已推送，异常原样抛出。

以上 5 个模式都是 RESULT: PASS。

**test_test_evaluate_begin_wiring 三个参数（ic10_04f：`3 passed in 63.08s`，RESULT: PASS；全部预期一次运行即相等）**
- crash_after_begin：
  - 运行 A：begin 之前与 normal 相同；begin 入口处为 `(True, False, False)`。第 2 次 control_evaluation 抛出 RuntimeError。
  - 运行 A 的 claim 为 `['N']`，begun 为 `[True]`。final_record 为 `('test-evaluate','BLOCKED',['crashed','test_begun'],True,None,'BLOCKED')`，message 为 `crash after the TEST marker: RuntimeError('injected crash in the second TEST evaluation')`。
  - 运行 A 抛出 RuntimeError，标志为 `(True, False)`。
  - 运行 B：refuse_if_test_evaluated 抛出 ProtocolStop（「already started」），之前**只有 1 条 git 命令** `cat-file blob HEAD:<result>`，因为标记在工作区。
  - 运行 B 没有 check_preconditions、device check、begin、final_record，也没有 fetch；返回 `(False,'BLOCKED')`，标志为 `(False, None)`。
  - 远端为 marker 加实验记录，共 2 个提交；记录 Status BLOCKED，test_begun True。
- refused_inside_begin：
  - begin 入口处为 `(True, False, False)`；begin 抛出 `BLOCKED: injected: a dry-run push to origin fails`。
  - 网络命令只有 `[('fetch', 在 begin 内)]`，没有 push。
  - 没有记录，标志为 `(True, False)`，远端 0 个提交，工作区没有标记。
- wrong_work：
  - code_commit 之后，start_checks 抛出「device ledger」。
  - refuse_if_test_evaluated、check_preconditions、device check（含类方法）都没有调用。
  - 没有记录、没有网络命令，返回 `(False,'BLOCKED')`，q 的标志为 `(False, None)`，work 以 another_work 结尾，远端 0 个提交。

### 3. 静态核对与数值
- 命令：
  - `$P -I -B ic10_04_static.py /home/user/OpenMythos`
  - `$P -I -B ic10_04e_lookahead.py /home/user/OpenMythos $P $S/inputs $S/c2d_smoke $S/ic10_04e`

**test_evaluate 的源码顺序**
- 行号：formal 检查 1169 < 重置 1171 < TG.code_commit 1172 < start_checks 1173 < refuse_if_test_evaluated 1174 < check_preconditions 1175 < device_check 1177 < … < before_run(look_ahead) 1204 < … < marker_before_begin 1210 < begin_called 1211 < begin 1212。
- 开头 10 条顶层语句与预期逐条相等。
- 两个标志的赋值只有 4 处：`__init__` 的 False/None、重置、begin 前的两行。

**refuse_if_test_evaluated（只读、不 fetch）**
- 只调用 `present`、`(p.root / rel).exists`、`TG._blob`、`TG.TestAlreadyEvaluated`、`ProtocolStop`。
- 两个 if 依次为 `present(TG.RESULT_REL)` → raise TestAlreadyEvaluated，`present(TG.MARKER_REL)` → `ProtocolStop(None,'BLOCKED',…)`。
- 没有写操作，没有 _git、check_checkout 或 'fetch' 字面量。
- `TG._blob` 只运行 `git -C root cat-file blob spec`。
- 唯一调用者是 test_evaluate。
- 它之前的 start_checks 只抛 `ProtocolStop(None…`，code_commit 只抛 ImplementationFail（停止码为 None）。所以 ST12、ST8、ST7 这些带停止码的停止都在它之后。
- TestAlreadyEvaluated 在 pilot.py 中只由 refuse_if_test_evaluated 抛出，在 testgate 中只由 refuse_if_marker 抛出。

**run_test_evaluate**：三个处理分支不变，`p.close_clock(); raise` 不写记录。

**test_evaluation_seconds**
- 代码：`load_s + checkpoints*reload_s + test_models*per_eval + test_state_hashes*hash_s`，其中 checkpoints = test_models − 1，不读 file_hash_s。
- 用冒烟第 2 步的 timing 独立计算：`0.350864 + 15×0.231198 + 16×31.155098×3/2 + 17×0.108639 = 753.388035540 s`。
- 代码返回 753.388035540，相等。比上一轮公式少 0.394833 s，即 15 个文件哈希。

**evaluation_plan 与 checkpoint_overhead_seconds（只报告）**
- 计数：`{'base_loads':32,'checkpoints':30,'checkpoint_reloads':18,'test_state_hashes':17,'test_file_hashes':15,'test_models':16}`，代码、我的计算、冒烟记录三方相等。
- 秒数：`32×load + 30×(2h+save+reload+file) + 18×reload + 17×h + 15×file = 33.475394762 s`，代码、我的计算、step2 记录三方相等。
- B17 加上该值为 1.809081970 h，与记录相等。st11_reads 为 `b17_estimate_hours`。

**before_run 的调用点**
- 第 3 步为 `p.before_run(p.eval_seconds('load') + (p.pre['hash_s'] if p.pre else 0.0))`，下一句是 `model = p.base_model()`。
- 其余 6 处与上一轮相同；冒烟 timing 下第 3 步的值为 31.6146 s。
- 训练运行：非 A 93.494993826 s，A 447.044688907 s，30 个逐个相等；训练项之和等于 B17 的 train_seconds。

**其余静态结果（c–h）**：CD13、test-generate、smoke 第 8 步、CA20、fetch（begin 与 finish 有 fetch，require_test_session、_check_session_checkout、claim_checkpoint 没有）、run_pilot.py，都 PASS。

**分支测试（ic10_04d：`6 passed`，PASS）**
- 运行了本轮改动的 6 个测试，没有启动生成器子进程。
- test-generate 测试中 st10_over_limit 的结果为 `[[], ['L4']]`；第 4 次调用在 start_checks 处被拒绝，与预期相同。

### 4. 冒烟的 30 次训练（ic10_05，RESULT: PASS）
- 命令：`$P -I -B ic10_05_trainings.py /home/user/OpenMythos $S/c2d_smoke`
- 我从 DEV 明细复算的选定配置为 F2、L6（L5 与 L6 都是 61/240，按 dNLL 选 L6）、A1，排名与记录相同。
- 30 个运行名与我推出的计划相同，顺序也相同，excluded 为 []。
- 逐项核对：
  - 文件 SHA-256 与字节数都等于记录。
  - state 等于 reloaded，30/30。
  - 30 个哈希互不相同，都不等于 N。
  - Acc 与 dNLL 等于我的复算值。
- G0.8：三个种子的分数差、NLL 差、预测差异都是 0。
- 限制同前几轮：重载后的哈希无法在不加载权重的前提下独立复算。

### 补充
- **ic10_06**：
  - 76 个 JSON 都带 SMOKE 标签；Gate 0 为 NOT_TESTED；would-stop 为 `['ST3']`；没有任何步记录带 stopped 字段。
  - overhead 计数与秒数都等于记录（差 0）；B17 为 1.7998 h，ST11 在界内。
- **ic10_07**：c2_mutate_fix3.py 的 43 个变异，原文在暂存的 pilot.py 和 run_pilot.py 中各恰好出现 1 次；暂存与工作区字节相同，没有残留的变异。
  - 我没有重跑变异；c2d_01 的 `mutations 43, caught 43` 按记录接受。
  - begin_called、marker_before_begin、重置这三项变异由 crash_after_begin 测出。我按代码推导，三项各自会让「记录已写」或「远端不变」的断言失败，与 c2d_01 的 CAUGHT 一致。

### 修复逐条核对（本人范围内）
| 项 | 结论 | 依据 |
|---|---|---|
| MAJOR 1（TEST 评过之后，带停止码的停止不再写记录） | 已修且正确 | 静态 a2；e2e normal 第 3 次运行：抛 ST7 的函数没有被调用，没有记录，远端不变 |
| MAJOR 2（错误的 --work） | 已修且正确 | 静态 a；wiring 的 wrong_work |
| MAJOR 3（两个标志的真实设置） | 已修且正确 | wiring 的 crash_after_begin 与 refused_inside_begin；e2e 各次运行之后的标志 |
| IC9-M1（重置标志） | 已修且正确 | 静态 a；crash_after_begin 运行 B 的标志为 (False, None)，不写记录 |
| IC9-M2（overhead 按 reload_s 计算） | 已修且正确 | ic10_04e、ic10_06 三方相等 |
| test_evaluation_seconds 去掉文件哈希、第 3 步加 hash_s | 已修且正确 | 静态 i、j；753.388 s 相等；e2e 28.2 s |
| run_test_generate 的断言与拒绝情形 | 已补 | ic10_04d |
| 裁决第 1 项（不 fetch） | 符合 | 第 2 次运行的 fetch 只在 begin、finish、final_record 之内 |

### 新登记（范围外，记为 MINOR 或观察，不构成 BLOCK）
- **IC10-M1**：只作报告的 checkpoint_overhead 没有计入第 3 步对 N 的那 1 次 state 哈希（1×hash_s）。第 3 步的事前估计已经计入了这一项，两处口径不一致。不影响 ST11（读的是 B17）。
- **观察 1**：refuse_if_test_evaluated 只看本地的工作区与 HEAD，按裁决第 1 项不 fetch。
  - 假如在一个没有 pull 的旧克隆上运行，而 TEST 已在别处评过，那么带停止码的停止会把记录写进工作区。
  - 但 final_record 的 precommit 会因 HEAD 不是远端最新提交而不提交；begin 也会在 fetch 之后拒绝。所以 TEST 不会被评测两次。
  - 按 RUNBOOK 只有一个克隆，走不到这个情形。
- **观察 2**：final_record 也会 fetch（check_commit_preconditions），发生在评测结束或停止之后，与裁决的意图不冲突。
- **观察 3**：c2d_02 没有记录脚本 sha256，见第 0 项。

### 运行后 `git status --short` 的原始输出（ic10_99_git_status_final.txt）
```
M  metrix/e1-pilot/reports/DEFERRED_MINORS.md
A  metrix/e1-pilot/reports/impl_c/c2_mutate_fix3.py
A  metrix/e1-pilot/reports/impl_c/c2d_01_checks.txt
A  metrix/e1-pilot/reports/impl_c/c2d_02_smoke.txt
A  metrix/e1-pilot/reports/impl_c/c2d_checks.sh
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/LABEL.txt
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/experiment_record_smoke_20261127T093836Z.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/experiment_record_smoke_20261127T093836Z.txt
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/gate0_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/smoke_report.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step1_manifest_fields.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step1_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step2_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step3_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step4_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step5_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step6_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step7_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/step8_record.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A1-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A1-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/A-A6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/F-F6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L6-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/L-L6-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/S-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/S-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/S-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/Y-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/Y-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2d_smoke_records/training_runs/Y-F2-seed303.json
M  metrix/e1-pilot/src/metrix_e1/pilot.py
M  metrix/e1-pilot/tests/test_run_pilot.py
?? metrix/e1-pilot/RUNBOOK_A100.md
?? metrix/e1-pilot/audit/ic10_00_state.py
?? metrix/e1-pilot/audit/ic10_01_hashes.py
?? metrix/e1-pilot/audit/ic10_02_data_recheck.py
?? metrix/e1-pilot/audit/ic10_03_test_refusal.py
?? metrix/e1-pilot/audit/ic10_04_e2e.py
?? metrix/e1-pilot/audit/ic10_04_static.py
?? metrix/e1-pilot/audit/ic10_04_trace_plugin.py
?? metrix/e1-pilot/audit/ic10_04d_branch_tests.py
?? metrix/e1-pilot/audit/ic10_04d_plugin.py
?? metrix/e1-pilot/audit/ic10_04e_lookahead.py
?? metrix/e1-pilot/audit/ic10_04e_probe.py
?? metrix/e1-pilot/audit/ic10_04f_wiring.py
?? metrix/e1-pilot/audit/ic10_05_trainings.py
?? metrix/e1-pilot/audit/ic10_06_smoke_labels.py
?? metrix/e1-pilot/audit/ic10_07_mutation_remnants.py
?? metrix/e1-pilot/audit/ic10_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_00_state_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_00b_state_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_01_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_02_data_recheck.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_03_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04a_e2e_normal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04a_e2e_normal_run1_superseded_plugin_change.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04a_e2e_normal_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04b_e2e_stop_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04b_e2e_stop_after_marker_run1_superseded_plugin_change.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04c_e2e_crash_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04c_e2e_crash_after_marker_run1_superseded_plugin_change.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04d_branch_tests.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04d_branch_tests_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04d_e2e_interrupt_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04e2_e2e_st7_before_begin.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04e2_e2e_st7_before_begin_run1_superseded_plugin_change.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04e2_e2e_st7_before_begin_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04e_lookahead.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_04f_wiring.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_05_trainings.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_06_smoke_labels.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_07_mutation_remnants.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_0x_trials_and_script_fixes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic10_99_git_status_final.txt
?? metrix/e1-pilot/reports/impl_c/c3_checks.sh
?? metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt
exit=0
```
- RUNBOOK_A100.md、c3_checks.sh、c3_hf_tree_70d244cc.txt 是 Executor 的 C3 草稿，不是我写的。
- 除 audit/ 之外，没有新增或改动的路径。暂存的条目与送审树 c7869d35 相同。

结论：PASS
