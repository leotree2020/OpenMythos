# data-auditor, round 1, C4 code commit (staged tree 63121c792654e53fce2bb1418b6413b3a275c126, parent 3bc761ea1d1cb7a1bf5a7a89d4084055e4ca83d1)
# Extracted unchanged from the transcript by reports/round6/review_extract.py
---
## Data Auditor 报告：C4 代码提交，第 1 轮

**审查对象**：暂存树 63121c792654e53fce2bb1418b6413b3a275c126，父提交 3bc761ea1d1cb7a1bf5a7a89d4084055e4ca83d1，仓库 /home/user/OpenMythos。

**运行环境**：主机 `vm`，Anthropic 云容器，只用 CPU（/dev 下没有 nvidia 设备节点），Python 3.13.18（scratchpad/venv）。
- 加载模型权重：没有。只加载了分词器，加载前已核对其 4 个文件的 sha256 等于冻结 DATA_MANIFEST 中 revision 70d244cc 的值。
- 冒烟 checkpoint：只按文件字节计算哈希，没有加载。
- Executor 的测试：只作驱动子进程运行，每次只跑一个，测试内部用随机小模型。
- TEST：没有生成、读取或统计真实 TEST。

脚本都在 /home/user/OpenMythos/metrix/e1-pilot/audit/，前缀 ic11_，由我的 ic10_ 脚本改写或新写，没有 import 或复制 Executor 的检查代码。完整 stdout 在 /home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/ic11_*.txt。

---

### 0. 审查状态核对（ic11_00_state.py；运行前后各一次）
命令：
`bash ic11_run_logged.sh stdout/impl_c/ic11_00_state.txt <venv>/python -I -B ic11_00_state.py /home/user/OpenMythos <scratch>/review_c4 <scratch>/c4_smoke`
收尾时再跑一次，输出 ic11_00b_state_final.txt。

原始输出摘录：
```
a. HEAD 3bc761ea... == parent: True | review_c4/tree.txt == 63121c79: True | index entries 6953 | tree 63121c79 entries 6953 | identical: True
   staged diff ... contained in input.diff as its tail: True | input.diff starts with git diff --cached --stat HEAD: True
   input_code.diff sha256 4fc67a5d... == git diff --cached HEAD -- [src, tests, c4_mutate.py, c4_checks.sh, c4_smoke.sh]: True
   staged paths outside metrix/e1-pilot/: []
b. working tree == index for src/tests/run_pilot.py: True | code diff sha256 e8df1988... == stated: True
   c4_02_checks.txt / c4_03_smoke.txt: code diff sha256 lines [e8df1988, e8df1988] | 40-hex lines [3bc761ea, 178c9a2f, 3bc761ea, 178c9a2f] | ls-files code blocks == staged: [True, True] | script sha256 == staged blobs: all True
c. tree 178c9a2f present; diff-tree 178c9a2f..63121c79: 45 paths, kinds ['A']; paths other than c4_02, c4_03 and smoke-record copies: [] | code entries == staged: True
d. staged copies 43, byte-identical to c4_smoke/records: 43 | not copied: details/ only: True
e. IMPL_C4_RULING.md == the text quoted in my invocation: True | == review_c4/ruling_c4.txt: True
f. RUNBOOK_A100.md / IMPL_C_REPORT.md / DEFERRED_MINORS.md: working tree == index == HEAD: True
RESULT: PASS
```
与 Executor 一致。00b 与 00 只差 audit/ 下的未跟踪条目数（57 变为 79，即我的输出文件）。

### 1. ST11 估计量的独立复算（ic11_04_st11.py）
命令：`... python -I -B ic11_04_st11.py /home/user/OpenMythos <scratch>/c4_smoke`

计数来源：冻结协议文本（git cat-file 87a244db）和冻结 JSON。
- 第 7 节：每个 arm 6 个配置，共 18 次搜索；额外种子 202、303；S、Y 各 3 个种子；训练总次数 30；每次 300 步（Y 同为 300 步）。
- 第 8 节：G0.8 表格行给出 3 次重评。
- 第 10 节：系数 6 和 2。
- 第 11 节：ST11 上限 3.5 小时。
- 冻结模板：每个 fact 的问题数 DEV 2、TEST 3，比值 1.5。

原始输出摘录：
```
my runs 30 ... A runs 8, other 22 | steps 300 (Y 300)
evaluation units: DEV 34 (N + 30 runs + 3 G0.8) + TEST 16 models x 1.5 = 58 | overhead counts {"base_loads": 32, "checkpoint_reloads": 18, "checkpoints": 30, "test_file_hashes": 15, "test_models": 16, "test_state_hashes": 17}
seconds_per_step [...] -> my mean without the first 0.234157931499908 | recorded 0.234157931499908
device ledger files under the smoke's work directory: [] -> GPU seconds already used = 0
A factor 1 + (2 + 6) x 511.966667 / (6 x 118.666667) = 6.752434456929
training 0.234158 x 300 x (22 + 8 x 6.752434) = 5340.168951955 s | evaluation 58 x 32.593024364 = 1890.395413112 s | used 0
B17 estimate 2.008490101407 h
checkpoint overhead 32 x 0.377787760 + 30 x (2 x 0.121143452 + 0.049880058 + 0.258339125 + 0.032964958) + 18 x 0.258339125 + 17 x 0.121143452 + 15 x 0.032964958 = 36.797356974 s
ST11 estimate = B17 + overhead / 3600 = 2.018711589456 h | bound 3.5 h | ST11 triggers: False | B17 alone > bound: False
  b17_estimate_hours          mine 2.008490101407 | recorded 2.008490101407 | equal True
  checkpoint_overhead.seconds mine 36.797356973997 | recorded 36.797356973997 | equal True
  st11_estimate_hours         mine 2.018711589456 | recorded 2.018711589456 | equal True
  (also equal: a_factor, train_seconds, eval_seconds, evaluation_units 58, used 0, a_runs 8 / other_runs 22, counts)
  st11 'within bound' (expected 'within bound') | st11_bound_hours 3.5 | st11_reads 'b17_estimate_hours + checkpoint_overhead.seconds / 3600'
  the two renamed fields still present in the record: []
  smoke_report ST11 entries [] (expected none)
  log values ('2.008', '0.010', '2.019', '3.5') == my values at 3 decimals: True
RESULT: PASS
```
与 Executor 一致，没有差异。这些是冒烟值，不构成结论。冒烟中 B17 单独和两者之和都低于 3.5 小时，所以冒烟本身区分不了两种读法；区分由第 3 项的两个驱动完成。

### 2. 静态核对（ic11_05_static.py；对象是 index blob 与 HEAD blob 的 AST）
命令：`... python -I -B ic11_05_static.py /home/user/OpenMythos`

原始输出摘录：
```
pilot.py  added ['st11_estimate_hours'] | code changed ['preflight', 'step2'] | docstring-only changed ['checkpoint_overhead_seconds', 'test_evaluation_seconds']
stops.py / compute.py bytes identical True
interpretations.py added ['=ACCEPTED_C4', '=RULING_REF_C4'] | code changed ['=ENTRIES']
HEAD  p.stop_in_step(2, ..., STP.st11, p.fz, p.contract, pre['b17_estimate_hours'])
index p.stop_in_step(2, ..., STP.st11, p.fz, p.contract, pre['st11_estimate_hours'])
references to st11 in src/ and run_pilot.py: [('pilot.py', 593, 'STP.st11')]
def st11_estimate_hours(b17_hours, overhead_seconds): ['return b17_hours + overhead_seconds / 3600.0']
callers: [('pilot.py', 'preflight', 'st11_estimate_hours(hours, overhead)')]
hours <- CP.estimate_total_hours(...) (once); overhead, counts <- checkpoint_overhead_seconds(...) (once); st11_hours <- st11_estimate_hours(hours, overhead)
out['b17_estimate_hours'] = hours | out['checkpoint_overhead'] = {'seconds': overhead, 'counts': counts} | out['st11_estimate_hours'] = st11_hours
stops.st11 condition ['not math.isfinite(estimate_hours) or estimate_hours > contract.stops.st11_hours'] | identical to HEAD: True
Pilot.run_seconds / Pilot.eval_seconds / test_evaluation_seconds / evaluation_plan / checkpoint_overhead_seconds / before_run / stop_in_step / stop_check: code identical: True (all)
string constants naming the old fields in staged src/, tests/, run_pilot.py: []
'step2_record' in src/: [('pilot.py','test_evaluate',...)] | ['preflight'] in src/: only test_evaluate | test_evaluate reads from step2: ["step2['preflight']['timing']"]
entries different from HEAD: ['B17'] | B17 status 'ACCEPTED（Review Gate 2026-11-27 修订）' ruling 'tasks/IMPL_C4_RULING.md 第 1 项'
B17 text: ST11 = B17's estimate + checkpoint overhead; 32 / 30 / 18 / 17 / 15; ST7 unchanged; no margin on TEST: all True
B17's own formula == the parent's text: True
RESULT: PASS
```
与 Executor 的说明一致：
- ST7 的三个函数（run_seconds、eval_seconds、test_evaluation_seconds）只改了文档字符串。
- stops.st11 仍是超过上限才停止。
- 两个被改名的字段在 src/、tests/、run_pilot.py 中都没有剩余读取方。
- B17 的 status、ruling、text 与裁决第 1 项一致。

### 3. test_formal_st11_reads_b17_plus_the_checkpoint_overhead 的两个参数作驱动（ic11_06_st11_tests.py 与 ic11_06_plugin.py；每次只跑一个）
命令：`... python -I -B ic11_06_st11_tests.py /home/user/OpenMythos <venv>/python <inputs> <scratch>/ic11_06a3 sum_over_bound`；sum_at_bound 用同样的命令，scratch 目录为 ic11_06b。

运行前写出的预期（原文见输出开头）：
- **sum_over_bound**：估计 3.500277777777778 > 3.5，ST11 触发。run_gate 返回 (False, "BLOCKED")。第 2 步记录带 stopped {ST11, BLOCKED}，message 含 "preflight estimate 3.500 h > 3.5 h"。实验记录 Status 为 BLOCKED、停止码 ST11。没有第 3 步记录。
- **sum_at_bound**：估计正好 3.5，不触发。run_gate 抛出 RuntimeError("injected after step 2")。第 2 步记录不带 stopped，st11 为 "within bound"。实验记录 Status 为 NOT_TESTED，消息含注入的文字。没有第 3 步记录。

实际结果（原始输出摘录）：
```
[over] st11_estimate_hours (3.0, 1801.0) -> 3.500277777777778 | stops.st11 raised Stop ST11 BLOCKED 'preflight estimate 3.500 h > 3.5 h' | run_gate returned [false, "BLOCKED"]
       remote commits: step 1 / "step 2 record (stop ST11)" / "experiment record (status BLOCKED)"; no step3_record
       step2 stopped {'code': 'ST11', 'status': 'BLOCKED', ...}; st11_estimate_hours == my sum 3.500277777777778
       experiment record Status 'BLOCKED', stop code ST11; clone clean, HEAD == remote main; 1 passed; RESULT: PASS
[at]   st11_estimate_hours (3.0, 1800.0) -> 3.5 | stops.st11 returned None | run_gate raised RuntimeError 'injected after step 2'
       remote commits: step 1 / "step 2 record" / "experiment record (status NOT_TESTED)"; no step3_record
       step2 stopped None, st11 'within bound'; experiment record Status 'NOT_TESTED', message "crash: RuntimeError('injected after step 2')"; 1 passed; RESULT: PASS
```
预期与实际完全一致，与 Executor 的测试断言一致。两次运行后本仓库的 git status、index、HEAD 都没有变化。

### 4. 冒烟数据目录（ic11_01_hashes.py、ic11_02_data_recheck.py、ic11_03_test_refusal.py）
**ic11_01 哈希**：
```
four content hashes mine == PROTOCOL_FROZEN == step1_record: facts 406c8801..., train_S 686fdd2f..., candidates e5d15c99..., anchor_texts 8828bc4f... ALL EQUAL True
8 files byte/canonical == step1_record, my stage-B record, Executor c4_02 listing, c4_data bytes: all True
step1_manifest_fields == my construction: True / True; TEST entries unchanged; template_set_sha256 2b524113... equal True
tokenizer pins equal: all True | RESULT: PASS
```
**ic11_02 泄漏、候选、split**：
- 泄漏：L1 到 L6 的数值分别为 0、0.2（上限 0.25）、0、0、0、0、0，逐项和逐个 detail 都等于冒烟记录中的报告，也等于我在阶段 A 的记录。
- 候选可行性（四重约束）：最小 available 为 5，最小 pool 为 4；available 小于 4 的 cell 为 []，pool 小于 4 的 cell 为 []；candidates.json 中违反约束的条目为 0。
- split：fact_id 共 160 个，learned 120、unread 40，交集 0，每个 cell 15+5；TRAIN 和 DEV 的组成符合协议。
- RESULT: PASS。

**ic11_03 TEST 生成器黑盒拒绝**：
- 冒烟工作目录下没有 TEST 文件。
- step8 记录中的拒绝信息与我的预期三行一致。
- 我自己运行生成器一次，输出为 "TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD / no TEST content was generated, read or written / RESULT: FAIL"，exit 1；--out 没有创建；数据、输入、src 都没有变化；不存在 results 目录和 ST10 记录。
- RESULT: PASS。

以上全部与 Executor 一致。

### 5. 冒烟的 30 次训练（ic11_07_trainings.py）
```
selection recomputed from DEV details: F2 / L6 / A1 == smoke (rows equal)
step6 training_plan == my plan (30, same order): True
30 x: file sha256 == record, bytes == record, state_sha256 == reloaded_state_sha256, acc/dNLL == mine: all True
state_sha256 distinct 30 of 30; N's among them: False
G0.8 three checkpoints: max score diff 0, NLL diff 0 (== step7) | RESULT: PASS
```
与 Executor 一致。

### 补充：冒烟标签与 ST11 字段（ic11_08_smoke_labels.py）
"would stop" 列表为 ['ST3']，与按记录值推出的结果一致（ST11 读 st11_estimate_hours，值 2.0187 h）；各项标签齐全；Gate 0 为 NOT_TESTED。RESULT: PASS。

---

### 登记为 MINOR 的事项（不作为 BLOCK 理由）
1. **ST11 停止消息的显示精度。** stops.st11 的消息格式是 "%.3f h > %g h"，估计为 3.50028 h 时显示成 "3.500 h > 3.5 h"，读起来像不大于上限。比较用的是未舍入的值，结果正确。stops.py 本次没有改动，问题早已存在。
2. **RUNBOOK_A100.md 第 200 行与暂存代码不一致。** 该行仍写 "ST11 读 `b17_estimate_hours`"，并提到已删除的字段 `b17_plus_checkpoint_overhead_hours_report_only`。按 Executor 的说明，这将在下一个只改文档的提交中按裁决第 7 项修订，须在那次修好。
3. **"for Review Gate" 措辞（对调用方问题的判断）。** pilot.py 第 833、1011、1036、1067 行是注释或文档字符串，第 1007 行是一个运行时字符串（冒烟实验记录的 "Next (single)" 字段为 "Review Gate reviews the smoke report (C2)"），五处都与 HEAD 相同。从数据审计角度，裁决第 2 项写明"不改代码"，这样处理可以接受：这些措辞不影响任何正式记录的值，第 1007 行只出现在冒烟记录中，也不是"待决"的表述。需要在之后的报告中把它们登记为过时措辞。
4. **（信息）** 正式运行中 ST11 停止时，第 2 步记录没有 "st11" 字段，停止信息记在 "stopped" 中，这是预期行为。实验记录的提交信息写作 "formal formal experiment record"，多了一个词，属于既有的表面问题。

### 本次审计自身的试跑与脚本修正
已逐条记入 stdout/impl_c/ic11_0x_trials_and_script_fixes.txt，相关输出都保留：
- ic11_04 第一次：G0.8 的正则匹配到 3 行，脚本报错。改为锚定表格行后重跑。
- ic11_06a 第一次：pytest 生成的 current 软链接让远端被找到两次，脚本判定失败。改为按 realpath 去重后重跑。
- ic11_06a 第二次：结果 PASS，但 git log 打印了全部历史（790 KB）。改为只打印测试自己的提交后重跑，以第三次为正式输出。
- 开始审计时，我在仓库里手动运行过一次 `git write-tree`，输出 63121c79。事后 stat 显示 .git/index 和该树对象的 mtime 都是 13:26:42，早于这条命令，index 条目没有变化。我的脚本都不调用 write-tree。

注：按 metrix/CLAUDE.md 第 10 节，data-auditor 的信任状态仍是"待验证"，本 PASS 只作参考。

### 运行后的 `git status --short` 原始输出
保存在 /home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/ic11_99_git_status_final.txt：
```
A  metrix/e1-pilot/reports/impl_c/c4_01_env_fetch.txt
A  metrix/e1-pilot/reports/impl_c/c4_02_checks.txt
A  metrix/e1-pilot/reports/impl_c/c4_03_smoke.txt
A  metrix/e1-pilot/reports/impl_c/c4_checks.sh
A  metrix/e1-pilot/reports/impl_c/c4_mutate.py
A  metrix/e1-pilot/reports/impl_c/c4_smoke.sh
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/experiment_record_smoke_20261127T130439Z.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/experiment_record_smoke_20261127T130439Z.txt
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/gate0_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/smoke_report.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step1_manifest_fields.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step1_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step2_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step3_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step4_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step5_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step6_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step7_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/step8_record.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A1-seed202.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A1-seed303.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/A-A6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/F-F6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L6-seed202.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/L-L6-seed303.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/S-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/S-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/S-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/Y-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/Y-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c4_smoke_records/training_runs/Y-F2-seed303.json
M  metrix/e1-pilot/src/metrix_e1/interpretations.py
M  metrix/e1-pilot/src/metrix_e1/pilot.py
A  metrix/e1-pilot/tasks/IMPL_C4_RULING.md
M  metrix/e1-pilot/tests/test_run_pilot.py
M  metrix/e1-pilot/tests/test_test_data.py
?? metrix/e1-pilot/audit/ic11_00_state.py
?? metrix/e1-pilot/audit/ic11_01_hashes.py
?? metrix/e1-pilot/audit/ic11_02_data_recheck.py
?? metrix/e1-pilot/audit/ic11_03_test_refusal.py
?? metrix/e1-pilot/audit/ic11_04_st11.py
?? metrix/e1-pilot/audit/ic11_05_static.py
?? metrix/e1-pilot/audit/ic11_06_plugin.py
?? metrix/e1-pilot/audit/ic11_06_st11_tests.py
?? metrix/e1-pilot/audit/ic11_07_trainings.py
?? metrix/e1-pilot/audit/ic11_08_smoke_labels.py
?? metrix/e1-pilot/audit/ic11_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_00b_state_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_01_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_02_data_recheck.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_03_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_04_st11.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_04_st11_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_05_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_06a_st11_sum_over_bound.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_06a_st11_sum_over_bound_run2_superseded_full_history_log.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_06a_st11_sum_over_bound_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_06b_st11_sum_at_bound.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_07_trainings.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_08_smoke_labels.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_0x_trials_and_script_fixes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic11_99_git_status_final.txt
```
暂存区内容与运行前相同（ic11_00b 的 a、b 两段与 ic11_00 一致）。新增的只有 audit/ 下的未跟踪文件。被忽略的 __pycache__ 集合与运行前相同，我的运行没有生成新的 .pyc。

结论：PASS
