# data-auditor, C2 work commit, round 1 (staged tree b80c9062134db0d950cd9786209862f69ffda06c, parent f8139f9; committed as 5219ff772272f5251ee18dc3d95cf54ba5d4104f)
# invocation text: data-auditor_prompt.txt; final report extracted unchanged by reports/round6/review_extract.py; trust status: pending verification (metrix/CLAUDE.md section 10), PASS for reference only
---
## data-auditor 审计报告：C2 工作提交第 1 轮（暂存树 b80c9062134db0d950cd9786209862f69ffda06c，父提交 f8139f9）

**结论：五项复算全部与 Executor 一致，没有差异，没有 BLOCKER。** 另登记 2 个 MINOR，都在防范对象之外。按 metrix/CLAUDE.md 第 10 节，data-auditor 仍是「待验证」状态，本 PASS 仅作参考。

**运行环境与限制的遵守**
- 主机 `vm`，Anthropic 云容器，只用 CPU（没有 nvidia 设备节点）。
- 只加载了 Qwen 分词器文件。30 个冒烟 checkpoint 只哈希文件字节，没有加载；ic7_05 没有 import torch。
- 没有生成、读取或统计真实 TEST。e2e 驱动里的 TEST 行都是 Executor 测试自己写的合成行。
- 只写入 `metrix/e1-pilot/audit/`，临时文件放在会话 scratchpad。暂存区没有改动：ic7_00b 在全部运行之后再次核对，index 与 b80c9062 的 6527 个条目逐项相同。

**脚本**（都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/`）
- `ic7_run_logged.sh`、`ic7_00_state.py`、`ic7_01_hashes.py`、`ic7_02_data_recheck.py`、`ic7_03_test_refusal.py`
- `ic7_04_static.py`、`ic7_04_e2e.py`、`ic7_04_trace_plugin.py`
- `ic7_05_trainings.py`、`ic7_06_smoke_labels.py`

**完整 stdout**（都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/`）
- `ic7_00_state.txt`、`ic7_00b_state_final.txt`、`ic7_01_hashes.txt`、`ic7_02_data_recheck.txt`、`ic7_03_test_refusal.txt`
- `ic7_04_static.txt`、`ic7_04a_e2e_normal.txt`、`ic7_04b_e2e_stop_after_marker.txt`、`ic7_04c_e2e_crash_after_marker.txt`
- `ic7_05_trainings.txt`、`ic7_06_smoke_labels.txt`、`ic7_99_git_status_final.txt`
- 被取代的试跑，都是我自己分析脚本的错误，已保留：
  - `ic7_04c_e2e_crash_after_marker_trial1_script_error.txt`
  - `ic7_04a_e2e_normal_trial2_script_error.txt`（运行到一半被我停掉，文件末尾附了原因说明）
  - `ic7_04b_e2e_stop_after_marker_trial2_script_error.txt`
  - `ic7_04c_e2e_crash_after_marker_trial2_script_error.txt`

记号：`$S` = `/tmp/claude-0/-home-user/14ee74de-5799-5f8c-a07c-f9bcdb0676fe/scratchpad`，`$P` = `$S/venv/bin/python`。每条命令都经 `bash ic7_run_logged.sh <stdout 文件> ...` 运行，cwd 为 audit/。

### 0. 审计对象的状态
- 命令：`$P -I -B ic7_00_state.py /home/user/OpenMythos $S/review_c2 $S/c2_smoke_final`
- 原始输出（摘录）：
  - `HEAD f8139f9… == parent: True`
  - `index entries 6527 | tree b80c9062 entries 6527 | identical (mode, blob, path): True`
  - `staged diff vs HEAD: 995436 bytes … contained in input.diff … as its tail: True`
  - `working tree == index for [src, tests, run_pilot.py]: True`
  - `smoke tree 05a76f57: 40 code entries | staged tree: 40 | identical: True`：冒烟跑的就是暂存代码。
  - `staged copies … 44 | byte-identical … 43 | different [] | not in the smoke's records ['LABEL.txt']`：仓库中的冒烟记录副本与 scratchpad 原件逐字节相同。
  - `RUNBOOK_A100.md status ['?? …']`
  - `RESULT: PASS`
- 与 Executor 的说明一致。

### 1. 四个冻结内容哈希、8 个文件哈希、第 1 步 manifest 字段
- 命令：`$P -I -B ic7_01_hashes.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2_smoke_final $S/c2_data`
- 原始输出（摘录）：
  - 四个内容哈希都是 `mine | PROTOCOL_FROZEN | smoke step1_record content_hashes | ALL EQUAL True`：
    - facts `406c8801…6b97`
    - train_S `686fdd2f…bc1e`
    - candidates `e5d15c99…3705`
    - anchor_texts `8828bc4f…2408`；我用分词器解码 ids 也得到同一个值，512 篇全部相同。
  - 8 个文件的 byte_sha256 与 canonical_sha256 同时等于以下四方：step1_record、我阶段 B 的记录、Executor 的 c2_05 清单、Executor 在 c2_data 中重新生成的字节。例如 `train_Y.jsonl byte c7430cad…6d15 canonical c7430cad…6d15 | step1_record True | my stage-B True | Executor c2_05 listing True | == c2_data bytes True`。
  - `DATA_MANIFEST.json files == mine: True | SPLIT_MANIFEST.json split_sha256 == mine: True`：
    - 我的构造：冻结的 files 中，8 个非 TEST 条目改为 GENERATED 并填入哈希；两个 TEST 条目保持 NOT_GENERATED/null；split_sha256 的 test_qa.jsonl 保持 null。
    - train_Y 的规范化哈希写在 split_sha256 中，符合 B3 裁决注记。
  - 两个 manifest 的工作区与 index 都等于冻结字节。
  - 模板：32 个模板的 normalized 与 normalized_sha256 无差异；template_set_sha256 `2b524113…e28f`，与 manifest 和 PROTOCOL_FROZEN 相等。
  - G 节：冻结的 manifest 正是 `json.dumps(indent=2, ensure_ascii=False)+"\n"` 的排版；第 1 步只改动 files 与 split_sha256 两个字段。
  - 数据目录只有 8 个数据文件加 LABEL.txt，没有 TEST 文件名。
  - `RESULT: PASS`
- 与 Executor 一致，无差异。

### 2. L1–L6（Gate 0 部分）、候选可行性、split
- 命令：`$P -I -B ic7_02_data_recheck.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2_smoke_final`
- 泄漏检查：L1、L3a、L3b、L4、L5、L6 都是 0，L2 为 0.2。三方相等：我的值、冒烟 step2_record 的值、我阶段 A 的记录。都在冻结上限内（L2 上限 0.25，其余为 0）。
- detail 逐项相等：
  - L2 的配对 (capital.TRAIN.1, capital.DEV.1) 是我算出的最大值配对之一。
  - L3a strings 80，L3b strings 120，L4 questions 320（part DEV）。
  - L5：重复字符串 0、fact_id 重叠 0，learned 120 / unread 40 / strings 320。
  - L6：锚文档 512、窗口 100、n 13，token-id 13-gram 0（只报告）。
  - 报告的 result 为 PASS。
- 候选可行性：
  - 原始输出：`minimum available 5 (stage-A record 5) | minimum pool 4 (stage-A record 4) | cells with available < 4: [] | cells with pool < 4: []`。
  - 160 个候选列表中，违反四重约束的为 0。
- split：
  - 160 个 fact_id 互不相同；learned 120、unread 40，两者不交；8 个 cell 各 15+5。
  - TRAIN 中没有 unread 的 fact。train_F 120、train_S 120、train_Y 240，每个 fact 的次数与类型都对。
  - dev_qa 320，每个 fact 两题，各对应其 relation 的一个 DEV 模板；general DEV 每个 domain 25 条；锚文本 512。
- `RESULT: PASS`。与 Executor 一致，无差异。

### 3. 冒烟没有产生 TEST 内容；TEST 生成器黑盒拒绝
- 命令：`$P -I -B ic7_03_test_refusal.py /home/user/OpenMythos $P $S/inputs $S/c2_smoke_final $S/ic7_test_out`
- 冒烟目录：`files under …/c2_smoke_final: 119 | named test_qa.jsonl / general_test.jsonl: []`；step8 的 --out 不存在。
- step8_record：命令为 `-m metrix_e1.test_data`，返回码 1，stdout 正是我预期的三行，out_exists False，test_files_under_work []，refused True。
- 我自己的运行：
  - 运行前写出的预期：stdout 为下面三行，exit 1。
  - 原始输出：
    ```
    TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
    no TEST content was generated, read or written
    RESULT: FAIL
    ```
    `exit code 1 | killed by the auditor False`
  - 与冒烟 step8 的 stdout、与 c2_05 的拒绝行都相同。
  - 运行后：--out 没有创建；数据目录、inputs、src 树、git status（audit/ 除外）都没有变化；没有 results 目录，也没有 ST10 记录。
- `RESULT: PASS`。一致。

### 4. TEST 路径的生产调用方（CA20 / CD5 / CD13 / CE5，以及 2026-11-27 裁决第 1 项）

**静态检查（AST，读取暂存 blob）**
- 命令：`$P -I -B ic7_04_static.py /home/user/OpenMythos`
- test_evaluate 中各步的源码行号依次递增，顺序正确（`all present and in this order: True`）：
  - 990 formal 模式检查
  - 992 TD.check_preconditions
  - 998 读取 TEST 文件
  - 1006 FZ.file_sha256（遍历 models[1:]，不符时 raise ProtocolStop BLOCKED）
  - 1012 begin
  - 1021 p.evaluate(split='test', test_session=session, checkpoint_name=name)：函数内唯一的评测调用，位于唯一的 `for name in models` 循环中
  - 1037 compute_test_values
  - 1038 judge_test
  - 1039 report_comparisons(…, 'test')
  - 1043 finish
- run_test_evaluate：
  - 只捕获 `(ProtocolStop, TD.PreconditionFailed)`。
  - 标记不存在时直接 return，不写记录；标记存在时在 try 之后调用 final_record。
  - TestAlreadyEvaluated 与 PreconditionFailed 的基类都是 Exception。
- 提交的 result（CD13）：
  - 键为 kind、frozen_commit、values、final、comparisons、summaries。
  - summaries 经 `_summary_record` 处理，去掉以 `general_` 开头的键。
  - 逐题明细写在 `p.work / TEST_DETAILS_DIR`；工作目录在仓库内时 `Pilot.__init__` 拒绝。
- TEST 生成（CD5/CE5）：
  - run_test_generate 只用 `subprocess.run(test_generate_command(...))`，命令为 `[sys.executable, '-m', 'metrix_e1.test_data', …]`。
  - 全包只有两个调用点：`generate_test: ['test_data.py:178 in main']`，`run_test_part: ['test_data.py:183 in main']`。
  - pilot.py 只用到 TD.check_preconditions 与 TD.PreconditionFailed。
- CA20：begin 与 finish 的调用方都只有 pilot.test_evaluate。
- fetch（裁决第 1 项）：begin 与 finish 经 check_checkout 执行 git fetch；require_test_session、_check_session_checkout、claim_checkpoint 不 fetch，与裁决一致。
- run_pilot.py：`--steps` 只加在 smoke 子解析器上；build_mode 只为 smoke 构造缩减模式。
- `RESULT: PASS`

**动态检查**（以 Executor 的测试作驱动，C1 裁决第 5 项）
- 命令：`$P -I -B ic7_04_e2e.py /home/user/OpenMythos $P $S/inputs $S/ic7_e2e_<mode>_r3 <mode>`
- 该脚本运行 `pytest -p no:cacheprovider -p ic7_04_trace_plugin --basetemp=… tests/test_run_pilot.py::test_test_evaluate_end_to_end_once`。插件是我写的透传包装，只记录调用顺序，不改任何行为。
- 判定由我的脚本根据调用记录、裸远端的 git 历史和 work 目录做出。预期在运行前打印。

normal 模式（`ic7_04a`，pytest `1 passed in 230.94s`，`RESULT: PASS`）：
- 第 1 次运行（测试改动了一个 checkpoint 文件）：只哈希了 1 个文件 F-F3-seed101.pt；没有 begin、没有评测、没有提交、没有 final_record；返回 `(False, 'BLOCKED')`；没有标记。与预期相同。
- 第 2 次运行：
  - 15 个 checkpoint 文件全部在 begin 之前核对。
  - begin 一次，只提交标记文件。
  - 16 次 evaluate_model(split=test)，顺序与远端标记中的 models 相同；16 次 claim；没有 DEV 评测。
  - compute_test_values、judge_test、report_comparisons(test)、finish、final_record 依次各调用一次。
  - finish 只提交 result；随后提交实验记录（json 与 txt）。
  - 返回 `(True, 'PIPELINE_NOT_QUALIFIED')`，与我预期的状态相同（随机小模型下 T1 不可能成立）。
- 第 3 次运行：begin 抛出 TestAlreadyEvaluated；没有评测、没有提交、没有记录。
- 远端在 fixture 之后正好 3 个提交：marker → result → 实验记录。result 中的 marker_commit 等于标记提交。
- 新增的 blob 中没有出现合成 TEST 文字（`Synthetic question`、`synthetic window`、`SYNTHETIC_T`、`synthetic-`）。result 与实验记录中都没有 `general_test*` 键，也没有逐题或逐窗口的行字段。
- 16 个逐题明细在 `<work>/test_details`，位于克隆之外；克隆与远端中都没有 TEST 文件。
- 本仓库的 git status（audit/ 除外）与 index 都没有变化。

stop_after_marker 模式（`ic7_04b`，`RESULT: PASS`）：
- 插件在第 3 次 TEST 评测时注入 ProtocolStop(BLOCKED)。
- 实际：final_record('test-evaluate', 'BLOCKED') 被调用并推送；远端 = marker、实验记录（Status BLOCKED，stop 消息含注入文字）；没有 result。
- 验证了「标记之后的停止写实验记录」。

crash_after_marker 模式（`ic7_04c`，`RESULT: PASS`，即观察与我的预测相同）：
- 插件在第 3 次 TEST 评测时注入 RuntimeError。
- 实际：远端只有标记提交；远端和克隆工作区中都没有实验记录；run_test_evaluate 抛出 RuntimeError。见下面的 MINOR IC7-M1。

与 Executor 的说明一致：顺序、标记之前的拒绝不写记录、标记之后的停止写记录、CD13、CD5 均成立。唯一的出入是说明中的「标记存在之后的任何停止都写实验记录」只对 ProtocolStop 类的停止成立，非 ProtocolStop 的崩溃不写记录。

说明：我最初的预期没有给出模型顺序（只给了集合），实际比较用的是 fixture 的顺序，并核对它等于标记中的顺序。我原先预期逐题明细里含题目文字，这是错的：明细行含 template_id、分数和预测，不含题目文字。这些都在 trial 文件中可见，最终三次运行的预期都在运行前打印。

### 5. 冒烟的 30 次训练
- 命令：`$P -I -B ic7_05_trainings.py /home/user/OpenMythos $S/c2_smoke_final`
- 选定配置由我从 DEV 逐题明细独立复算，规则为「最高 Acc → dNLL 较低 → 学习率较低 → 编号较小」：
  - F：全部 Acc 1/4，按 dNLL 选 F2，排名 F2, F1, F4, F3, F6, F5。
  - L：L5 与 L6 并列 61/240，按 dNLL 选 L6。
  - A：选 A1。
  - 三个排名都与 step4/step5 相同，rows 的 (acc, dNLL) 差值 < 1e-12。
- 训练计划由我从冻结的 SEARCH_SPACE.json 推出，共 30 个运行名：
  - 18 次搜索（seed101）
  - F-F2、L-L6、A-A1 各加 seed202、seed303
  - S-F2、Y-F2 各 3 个种子
- 以下都与我的计划相同：step6 的 training_plan（顺序也相同）、runs_completed、30 个记录、30 个 .pt 文件（另有 LABEL.txt）。
- 每个运行逐项核对：
  - meta 全部为 True：smoke、标签、arm/config/seed/phase、steps_run = mode_steps = 3、contract_steps = 300。
  - 文件 SHA-256 等于记录中的 checkpoint.file_sha256，字节数也相等。
  - state_sha256 等于 reloaded_state_sha256（30/30）。
  - 30 个 state 哈希互不相同，且都不等于 N 的哈希。
  - 我复算的 Acc 与 dNLL 等于记录值。
  - smoke_report 中 30 次训练全部完成。
- G0.8：三个 checkpoint 的分数差 0、NLL 差 0、预测差异 0，与 step7 相同。
- `RESULT: PASS`。一致。
- 限制：reload 后的 state 哈希是 Executor 在进程内算的。独立复算必须加载权重，这是我被禁止的，所以只核对了记录中两值相等与文件字节哈希。

### 补充：冒烟输出的标签与停止记录
- 命令：`$P -I -B ic7_06_smoke_labels.py /home/user/OpenMythos $S/c2_smoke_final`
- 76 个 JSON 记录全部带 SMOKE 标签与 mode smoke；txt 记录首行是标签；data/、checkpoints/、preflight/ 各有 LABEL.txt。
- Gate 0 为 NOT_TESTED，附「冒烟测试，不构成结论」；实验记录 Status NOT_TESTED，20 个字段；记录了 "smoke: device check skipped"。
- 记录的 would-stop 为 [ST11, ST3]，等于从记录值按冻结阈值推出的结果：Acc_CB 0.25 < 0.9；预估 7.305 h > 3.5 h。
- `RESULT: PASS`

### 登记的问题（都在防范对象之外，记为 MINOR，不构成 BLOCK）
- **IC7-M1（MINOR）：标记提交之后发生非 ProtocolStop 的崩溃，不写实验记录。**
  - 位置：`src/metrix_e1/pilot.py` 的 run_test_evaluate 只捕获 ProtocolStop 与 PreconditionFailed。
  - 后果：标记推送之后若出现其他类型的异常（RuntimeError、CUDA OOM、KeyError 等），该次运行没有实验记录（ic7_04c 实测）。这与协议第 10 节「每次运行（含被停止的）提交一份」以及 run_gate 对崩溃也写记录的做法不一致。
  - 为何不构成「评两次」：标记留在仓库中，重跑时 refuse_if_marker 判为 BLOCKED。按静态阅读，该次重跑会写入并提交 BLOCKED 记录。
  - 建议：照 run_gate 的做法，标记存在时对任何异常先写记录再重新抛出。
- **IC7-M2（MINOR，协议第 10 节的读法）：标记之前被拒绝的 test-evaluate 不写实验记录。**这是 Executor 明示的设计，动态检查也证实了。是否符合第 10 节「含被停止的」，请 Review Gate 确认。

### 审计期间仓库中出现的、不是我写入的文件
- `metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt`：mtime 04:00:46 UTC，文件头为 "Stage C, C3 … Executor, host vm"。
- `metrix/e1-pilot/RUNBOOK_A100.md`：mtime 04:00:52 UTC。
- 两者都不在暂存树中；我的脚本都不引用它们。看来是 Executor 并行在做的 C3 草稿，不属于本次审查对象。

### 运行后 `git status --short` 的原始输出（`ic7_99_git_status_final.txt`）
```
A  metrix/e1-pilot/reports/impl_c/c2_00_session_start.txt
A  metrix/e1-pilot/reports/impl_c/c2_01_env_fetch.txt
A  metrix/e1-pilot/reports/impl_c/c2_02_checks_superseded.txt
A  metrix/e1-pilot/reports/impl_c/c2_02_stray_experiment_record_formal.json
A  metrix/e1-pilot/reports/impl_c/c2_02_stray_experiment_record_formal.txt
A  metrix/e1-pilot/reports/impl_c/c2_03_smoke_superseded.txt
A  metrix/e1-pilot/reports/impl_c/c2_04_smoke_superseded.txt
A  metrix/e1-pilot/reports/impl_c/c2_05_checks.txt
A  metrix/e1-pilot/reports/impl_c/c2_06_smoke.txt
A  metrix/e1-pilot/reports/impl_c/c2_checks.sh
A  metrix/e1-pilot/reports/impl_c/c2_mutate.py
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/LABEL.txt
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/experiment_record_smoke.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/experiment_record_smoke.txt
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/gate0_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/smoke_report.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step1_manifest_fields.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step1_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step2_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step3_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step4_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step5_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step6_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step7_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/step8_record.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A1-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A1-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/A-A6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/F-F6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L6-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/L-L6-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/S-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/S-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/S-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/Y-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/Y-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2_smoke_records/training_runs/Y-F2-seed303.json
A  metrix/e1-pilot/run_pilot.py
M  metrix/e1-pilot/src/metrix_e1/gate.py
A  metrix/e1-pilot/src/metrix_e1/pilot.py
A  metrix/e1-pilot/tasks/IMPL_C2_OWNER_MESSAGE.md
A  metrix/e1-pilot/tests/test_run_pilot.py
?? metrix/e1-pilot/RUNBOOK_A100.md
?? metrix/e1-pilot/audit/ic7_00_state.py
?? metrix/e1-pilot/audit/ic7_01_hashes.py
?? metrix/e1-pilot/audit/ic7_02_data_recheck.py
?? metrix/e1-pilot/audit/ic7_03_test_refusal.py
?? metrix/e1-pilot/audit/ic7_04_e2e.py
?? metrix/e1-pilot/audit/ic7_04_static.py
?? metrix/e1-pilot/audit/ic7_04_trace_plugin.py
?? metrix/e1-pilot/audit/ic7_05_trainings.py
?? metrix/e1-pilot/audit/ic7_06_smoke_labels.py
?? metrix/e1-pilot/audit/ic7_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_00b_state_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_01_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_02_data_recheck.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_03_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04a_e2e_normal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04a_e2e_normal_trial2_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04b_e2e_stop_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04b_e2e_stop_after_marker_trial2_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04c_e2e_crash_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04c_e2e_crash_after_marker_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_04c_e2e_crash_after_marker_trial2_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_05_trainings.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_06_smoke_labels.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic7_99_git_status_final.txt
?? metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt
exit=0
```
（RUNBOOK_A100.md 与 reports/impl_c/c3_hf_tree_70d244cc.txt 不是我写的，见上节。）

结论：PASS
