# data-auditor final report, Implementation stage B fix commit (staged; parent 74a4d4443a3880239996d7adc6c13c636e4edf64); invoked 2026-11-23 13:35 UTC (background); invocation text: data-auditor_prompt.txt
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a6d5a0cf6ebe6b8b9.jsonl)
---
## Data Auditor 报告：Metrix E1-PILOT 实现阶段 B 修复提交（第 3 轮；HEAD 74a4d4443a3880239996d7adc6c13c636e4edf64，修复已暂存、未提交）

三项都已复算，结论都与 Executor 一致，没有不一致的项，也没有不可复算的项。
- **数据**：data_d 的 8 个文件与 data_c、data_b 逐字节相同，也与我本轮重新生成的结果、我第 2 轮的结果按内容逐条一致。四个冻结哈希从 data_d 读回后，与我的值、PROTOCOL_FROZEN、t8 的 generate 和 verify 共五方相等。t8 第 11 行的 400 / 100 与我按行前缀数出的 dev 行数、窗口数一致。
- **导出**：audit_dump_d.json 的 sha256 与 t8 记录的值相同，与 audit_dump_b.json 逐字节相同。
- **TEST 隔离**：TEST 生成器拒绝执行，没有留下任何产物。
  - `evaluate_model(split="test")`、`generate_test`、`run_test_part` 三处都在读取或使用任何 TEST 内容之前调用 `verify_authorization`。
  - 前提条件满足之前，没有任何路径解码或解析非 dev 行，也没有任何路径实例化 TEST 问句。
  - 静态检查做了 14 个埋入故障的阳性对照，全部检出。

**运行环境**：主机 vm（Anthropic 云容器，Linux 6.18.44），只用 CPU，/dev 下没有 nvidia 设备。Python 3.13.18，transformers 5.22.2，tokenizers 0.23.3，pyarrow 26.0.1。
- 只加载了分词器，没有实例化任何模型，也没有读取权重文件。加载 AutoTokenizer 时 transformers 会自行导入 torch，每份 stdout 的 `modules:` 行如实记录了这一点。
- 没有生成、读取或统计 TEST，没有实例化 TEST 问句。
- eval_sets.jsonl 只做了两件事：对整个文件求哈希；以二进制方式按行前缀定位 split 值并计数。非 dev 行不做 UTF-8 解码，也不做 JSON 解析。

**独立性**：
- 本轮新写的脚本：id_00_state.py、id_01_compare.py、id_02_dump.py、id_06_static.py、id_07_static_selftest.py，由我第 2 轮的 ic_ 脚本改写。
- 沿用、内容未改的脚本：ia_00、ia_03–ia_06、ib_00、ic_05、ib_run_logged.sh。
- 所有脚本只导入标准库、ia_common，以及 transformers / tokenizers / pyarrow。
- Executor 的代码一律用 ast 静态解析，不导入、不运行。唯一运行过的 Executor 代码是第 3 项指定的 TEST 生成器，黑盒运行一次。

**通用写法**：
- `S=/tmp/claude-0/-home-user/f24b86c9-a2c5-5317-8b43-751d1f505d91/scratchpad`
- 每条命令的形式：`cd /home/user/OpenMythos/metrix/e1-pilot/audit && bash ib_run_logged.sh stdout/impl_b/<NN>.txt $S/venv/bin/python -I -B <脚本> ...`
- 完整 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_b/` 下的 29–43 号文件（接前两轮的 00–28）。

---

### 0. 被审状态与固定输入

**命令**
- `ia_00_frozen.py /home/user/OpenMythos` → `29_ia_frozen.txt`
- `ib_00_tag.py /home/user/OpenMythos` → `30_ib_tag.txt`
- `id_00_state.py /home/user/OpenMythos $S $S/auditor_ib/dl $S/inputs` → `31_id_state.txt`

**原始输出（摘录，31 号）**
```
HEAD 74a4d4443a3880239996d7adc6c13c636e4edf64 | == 74a4d4443a3880239996d7adc6c13c636e4edf64: True | branch metrix-e1-pilot-protocol-v1
unstaged changes under metrix/ (working tree vs index): []
staged files (19): ... | staged files under metrix/e1-pilot/audit/: [] | staged files outside metrix/e1-pilot/: []
git diff --cached sha256 6e28b11c…040c | review_input.diff body sha256 6e28b11c…040c | identical True
(git diff --cached --stat; echo; git diff --cached) sha256 b314514a…8d61 | review_input.diff sha256 b314514a…8d61 | identical True
review_input.diff: sha256 b314514a…8d61 | recorded in preflight_tools_check.txt ['b314514a…8d61'] | MATCH True
  (6 input files: mine | Executor | manifest | ALL EQUAL True, every line; weight-like files: [] in both dirs)
research/mini_mythos/stage1/results/r1/eval_sets.jsonl: sha256 8816fe5a…a155 | manifest 8816fe5a…a155 | MATCH True
rows by split value (line prefix only): {'dev': 400, 'test': 800} | lines without the prefix key: 0
RESULT: PASS
```

**29 号结果为 RESULT: FAIL，原因与前两轮相同**：
- 唯一为假的一行是本地标签那一行（本 clone 没有本地标签）。
- 除首行时间戳和 HEAD 行外，29 号与 14 号逐行相同（已用 diff 核实）。
- 30 号只读核对了远端标签，结果为 PASS：`remote tag metrix-e1-pilot-frozen-v1.1 (peeled) -> 87a244db… | == freeze commit: True`。

---

### 1. data_d 的 8 个数据文件、四个冻结哈希、t8 第 11 行

**命令**
- 先把 ia_03、ia_04、ia_05、ia_06 重新生成到新目录 `$S/auditor_id/out`，输出为 32–35 号：
  - 锚文本 8828bc4f…2408 MATCH True
  - fact 406c8801…6b97 MATCH True
  - train_S 686fdd2f…bc1e MATCH True
  - candidates e5d15c99…3705 MATCH True
  - eval_sets 只计数：`{'dev': 400, 'test': 800}`，保留窗口 100 个
  - 32–35 号与第 2 轮的 17–20 号相比，只有首行时间戳和输出目录名不同。
- 然后运行 `id_01_compare.py /home/user/OpenMythos $S/auditor_ib/dl/qwen_tok $S/auditor_id/out $S/auditor_ic/out $S/data_b $S/data_c $S/data_d` → `36_id_compare.txt`

**原始输出（摘录，36 号）**
```
== A. my regeneration of this round vs my round-2 regeneration: 9 files, each identical True
== B. four frozen hashes: auditor | read back from data_d | PROTOCOL_FROZEN | t8 generate | t8 verify
  facts        406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 x5 | ALL EQUAL True
  train_S      686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e x5 | ALL EQUAL True
  candidates   e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 x5 | ALL EQUAL True
  anchor_texts 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 x5 | ALL EQUAL True
  anchor texts from my decode of the Executor's data_d ids: 8828bc4f…2408 | == PROTOCOL_FROZEN True
  element-wise equal: facts True | train_S records True | candidates True | candidates key order True
== C. train_F 120 / train_Y 240 / dev_qa 320 / general_dev 100 (ids, texts) / anchor_text 512 (ids, texts): identical sequence True (each)
== D. (each of the 8 files) data_d == data_c True | data_d == data_b True | canonical form True | == t8 line True | == t6 line True | == t3 line True
== E. data_d listing [8 data files + leakage_report.json] True | test_qa.jsonl present False | general_test.jsonl present False
== F. t8:11 parsed: rows by split {'dev': 400, 'test': 800} | DEV rows decoded and parsed 400 | windows kept 100
my binary line-prefix count of eval_sets.jsonl: {'dev': 400, 'test': 800} | lines without the prefix key 0
  rows by split == my prefix count: True
  'DEV rows decoded and parsed' 400 == my prefix count of dev rows 400: True
  'windows kept' 100 == my general DEV windows 100 (== rows of data_d/general_dev.jsonl 100): True
  t8 lines 3-25 vs t6 lines 3-25: differing lines: 1 (line 11 only, the relabelled count line)
RESULT: PASS
```

**与 Executor 是否一致**：一致，没有差异。
- t8 第 26–35 行（cmp data_c data_d，8 个 identical，exit 0）、第 36–44 行（verify PASS）都与我的比对相符。
- data.py 本次只改了 build_general_dev 的 info 字段和打印标签：新增的 `parsed` 计数只在 non-dev 的 continue 和 json.loads 之后递增（39 号 b 节，静态核实）。
- 数据文件因此逐字节不变。第 2 轮观察 2 指出的标签问题已经修正。

---

### 2. audit_dump_d.json

**命令**：`id_02_dump.py /home/user/OpenMythos $S/audit_dump_b.json $S/audit_dump_c.json $S/audit_dump_d.json` → `37_id_dump.txt`

**原始输出（摘录）**
```
t5 recorded (audit_dump_b.json): ['3ba470a9…be50'] | t6 recorded (audit_dump_c.json): ['3ba470a9…be50'] | t8 recorded (audit_dump_d.json): ['3ba470a97419dd34bd655e97d4d061c7de72700ae7692de37d14e1db2615be50'] | t8 cmp b/d exit 0
audit_dump_d.json sha256 3ba470a97419dd34bd655e97d4d061c7de72700ae7692de37d14e1db2615be50 | == t8 True | == t5 True | == t6 True
bytes: b 632222 | c 632222 | d 632222 | d == b byte for byte True | d == c byte for byte True
t8 counts line == the dump's sizes: True
RESULT: PASS
```

**与 Executor 是否一致**：一致。
- 导出与第 1 轮逐字节相同，所以第 1、2 轮对其内容的逐条复算结论（09、10、23、24 号）原样适用于 dump_d。这些复算覆盖打分输入、训练序列、batch 顺序、锚文档和学习率因子。

---

### 3. TEST 隔离

**黑盒运行（一次）**：`ic_05_test_refusal.py /home/user/OpenMythos $S/venv/bin/python $S/inputs $S/data_d $S/auditor_id/test_out_d` → `38_ic_test_refusal.txt`
```
out_dir …/auditor_id/test_out_d exists: False
metrix/e1-pilot/results/gate0_record.json: in HEAD False | in working tree False | metrix/e1-pilot/results exists False
$ …/venv/bin/python -m metrix_e1.test_data --inputs …/scratchpad/inputs --data …/scratchpad/data_d --out …/scratchpad/auditor_id/test_out_d
----- generator stdout+stderr begin -----
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL
----- generator stdout+stderr end -----
exit code 1 | killed by the auditor False
out_dir …/test_out_d exists: False
data dir unchanged (names, sizes, mtimes, sha256): True | test_qa.jsonl / general_test.jsonl in the data dir: []
inputs unchanged: True | src tree unchanged (incl. __pycache__): True | git status --porcelain --ignored --untracked-files=all -- metrix unchanged: True
results directory created: False
RESULT: PASS
```
与 t8 第 61–77 行的拒绝原文、退出码一致。

**静态检查**：`id_06_static.py /home/user/OpenMythos` → `39_id_static.txt`

调用位置都符合预期：
```
verify_authorization: called only from [evaluate.evaluate_model, leakage.run_test_part, test_data.generate_test] | True
committed_record: called only from [leakage.verify_authorization, stops.st13_scan, test_data._committed] | True
TestAuthorization: called only from [test_data.check_preconditions] | True
generate_test / run_test_part / check_preconditions: only from test_data.main; build_test_qa / params_for_test: only from generate_test
evaluate_model: called only from [] | True
calls that open eval_sets.jsonl: [('data.py', 507, 'build_general_dev', "open(eval_sets_path, 'rb')")]
read calls whose argument names a TEST file: []
```
TEST_FILES 的每处使用只做 `.exists()` 或元组比较。

三个入口都先调用 `verify_authorization`：
```
generate_test statement 0 is LK.verify_authorization(authorization, fz.repo_root): True | readers / builders after it: [(1,'params'),(2,'check_inputs'),(3,'load_qwen_tokenizer'),(4,'params_for_test'),(5,'read_jsonl'),(6,'build_test_qa'),(8,'build_general_dev')] (all > 0: True) | TEST split set at statement 7
run_test_part statement 0: 'verify_authorization(authorization, repo_root)' -> verify first True | first statement using test_qa / general_test: 5 | after the verify True
SPLIT_FILES keys exactly dev, test: True
evaluate_model: statement 0 split check; statement 1 `if split == 'test'` calls ['verify_authorization(test_authorization, repo_root)'], no else; first statement touching data / qa_file / gen_file at 3 -> True
```

`verify_authorization` 及其下层的读取范围：
```
verify_authorization: statement 0 isinstance guard raising True | loop over both records (gate0, selection_freeze) True | committed_record(repo_root, rel, kind, authorization.frozen_commit) True | NotCommitted -> raise, got != want -> raise True | all calls ['ImplementationFail','committed_record','isinstance']
record.committed_record calls ['NotCommitted','committed_json','get']; committed_json: git cat-file blob HEAD:<rel> + the working-tree record only
stops.st13_scan: readers [] (only committed_record and (Path(d)/n).exists())
```

build_general_dev（二进制读取，非 dev 行在 continue 之前只做前缀匹配）：
```
open(eval_sets_path,'rb') only; before the non-dev continue: only _ROW_HEAD.match(line) and m.group(1).decode('ascii','replace'); json.loads(line.decode('utf-8')) at statement 4 > continue at 3; 'parsed += 1' at 5
```

前提条件与解释裁决：
- `check_preconditions` 的顺序为：st12、load、check_data_dir、check_gate0_record、check_selection_record、check_interpretations_ruled，最后才构造 TestAuthorization。
- 24 条解释全部处于 pending，所以当前状态下解释裁决检查也会拒绝。

模板实例化：
- test_data.py 中只有 `build_test_qa`。
- 其它位置只有 DEV、TRAIN、Y 的生成函数、fill 和 statement_prefix。

tests/ 中涉及 TEST 的调用都到不了 TEST 内容：
- `generate_test` 只以 `None` 或 `TestAuthorization(None, None, None)` 调用，用的是真实仓库。真实仓库里两个记录都没有提交，`verify_authorization` 会拒绝。
- `run_test_part` 两次调用的 test_qa、general_test 都是 `[]`。
- `evaluate_model(split="test")` 用的是 `fz.repo_root` 和 data_rows。data_rows 只含 data.generate 产生的非 TEST 文件，有 `assert tuple(files) == DATA_FILES` 保证。
- `test_verify_authorization_hash_branches` 在临时仓库里让授权核验通过，但只做核验，不调用任何 TEST 路径。
- 修改后的 `check_preconditions` 测试之后也不调用任何 TEST 路径。

**阳性对照**：`id_07_static_selftest.py /home/user/OpenMythos $S/auditor_id/selftest` → `40_id_static_selftest.txt`
- 做法：在源码副本上逐一植入 14 种故障，看 id_06 能否检出。M1–M3、M10、M11 是前两轮已有的类型，M4–M9、M12–M14 是针对本次改动新增的。
  - M1：以文本模式打开 eval_sets.jsonl
  - M2：在 continue 之前做 json.loads
  - M3：删去解释裁决检查
  - M4：evaluate_model 在授权核验之前访问 data
  - M5：删去 evaluate_model 中的授权核验
  - M6：generate_test 在读取 facts 之后才核验授权
  - M7：run_test_part 在核验授权之前使用 test_qa
  - M8：删去哈希比较
  - M9：st13_scan 读取 TEST 文件
  - M10：main 的 try 块里调用 generate_test
  - M11：新增一处 TEST 模板实例化
  - M12：测试向 run_test_part 传入 TEST 行
  - M13：测试用其它仓库根评测 TEST split
  - M14：evaluate_model 自己构造 TestAuthorization
- 结果：未改动的副本判 `control … RESULT: PASS`；M1–M14 全部判 `RESULT: FAIL`，与预期一致。脚本本身判 RESULT: PASS。
- 41、42 号是 id_06 单独在 M2、M8 副本上的运行，用来确认失败的原因：
  - M2：continue 之前出现了 `json.loads(line.decode('utf-8'))`。
  - M8：`got != want -> raise False`。

**与 Executor 是否一致**：一致。与 test_data.py、leakage.py、evaluate.py 文档中的说明，以及 t8 的拒绝输出相符。

---

### 观察（都不是不一致，供 Review Gate 参考）

1. **第 2 轮观察 1 仍未处理，等待 Review Gate 裁决**：`tests/test_data_hashes.py` 仍然对真实的 eval_sets.jsonl 运行 `reports/round5/l6_check.py`，后者用 `open(..., encoding='utf-8')` 以文本模式读取。
   - 39 号核实：该脚本的工作区内容 == HEAD == 0bc0eecf 的版本，本轮没有改动。
   - 这意味着 test 行会被 UTF-8 解码成 str，但不做 JSON 解析（continue 在 json.loads 之前）。
   - t8 的 pytest 又运行了一次（第 110 行 PASSED）。
2. **`verify_authorization` 只复核两份已提交记录**（formal 模式、kind、frozen_commit、sha256），不复核条件 1（ST12）和解释裁决检查。
   - 这两项只靠「TestAuthorization 只在 check_preconditions 中构造」这一约定来保证；静态核实包内确实只有这一处构造。
   - 当前两份记录都没有提交，所以任何手工构造的授权都会被拒绝。
3. **evaluate_model 在默认参数下（test_authorization=None）由 isinstance 检查拒绝**；没有调用者，阶段 C 的驱动代码加入后需要再审。
4. **过程说明**：
   - id_06 有一次试跑没有记入 stdout，结果留在 `$S/auditor_id/trial_id06.txt`。之后我只给 id_06 加了一行 l6_check.py 的 git 比对，正式结果见 39 号。
   - 41、42 号是补充运行。
   - `find metrix -newer 29_ia_frozen.txt`（排除 audit/）的结果为空。
   - 00–28 号 stdout 和 ib_、ic_ 脚本的修改时间都早于本轮，本轮没有改动它们。

### 运行后的 `git status --short`（原始输出，也保存在 `stdout/impl_b/43_git_status_final.txt`）
```
A  metrix/e1-pilot/reports/impl_b/t7_work_commit_push.txt
A  metrix/e1-pilot/reports/impl_b/t8_fix_commit.txt
M  metrix/e1-pilot/src/metrix_e1/compute.py
M  metrix/e1-pilot/src/metrix_e1/contract.py
M  metrix/e1-pilot/src/metrix_e1/data.py
M  metrix/e1-pilot/src/metrix_e1/evaluate.py
M  metrix/e1-pilot/src/metrix_e1/gate.py
M  metrix/e1-pilot/src/metrix_e1/interpretations.py
M  metrix/e1-pilot/src/metrix_e1/leakage.py
M  metrix/e1-pilot/src/metrix_e1/record.py
M  metrix/e1-pilot/src/metrix_e1/stops.py
M  metrix/e1-pilot/src/metrix_e1/test_data.py
M  metrix/e1-pilot/src/metrix_e1/train.py
M  metrix/e1-pilot/tests/test_data_hashes.py
M  metrix/e1-pilot/tests/test_evaluate.py
M  metrix/e1-pilot/tests/test_record.py
M  metrix/e1-pilot/tests/test_stops.py
M  metrix/e1-pilot/tests/test_test_data.py
M  metrix/e1-pilot/tests/test_train.py
?? metrix/e1-pilot/audit/ib_00_tag.py
?? metrix/e1-pilot/audit/ib_01_compare.py
?? metrix/e1-pilot/audit/ib_02_yratio.py
?? metrix/e1-pilot/audit/ib_03_scoring.py
?? metrix/e1-pilot/audit/ib_04_training.py
?? metrix/e1-pilot/audit/ib_05_test_refusal.py
?? metrix/e1-pilot/audit/ib_06_static.py
?? metrix/e1-pilot/audit/ib_run_logged.sh
?? metrix/e1-pilot/audit/ic_00_state.py
?? metrix/e1-pilot/audit/ic_01_compare.py
?? metrix/e1-pilot/audit/ic_02_dump.py
?? metrix/e1-pilot/audit/ic_03_scoring.py
?? metrix/e1-pilot/audit/ic_05_test_refusal.py
?? metrix/e1-pilot/audit/ic_06_static.py
?? metrix/e1-pilot/audit/ic_07_static_selftest.py
?? metrix/e1-pilot/audit/id_00_state.py
?? metrix/e1-pilot/audit/id_01_compare.py
?? metrix/e1-pilot/audit/id_02_dump.py
?? metrix/e1-pilot/audit/id_06_static.py
?? metrix/e1-pilot/audit/id_07_static_selftest.py
?? metrix/e1-pilot/audit/stdout/impl_b/
```
- 已暂存的条目都是 Executor 的改动；31 号核实了暂存内容等于 review_input.diff。
- 本轮新增的只有 audit/ 下的未跟踪文件。

所有文件都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/` 下：
- 本轮脚本：id_00_state.py、id_01_compare.py、id_02_dump.py、id_06_static.py、id_07_static_selftest.py
- 沿用的脚本：ia_00_frozen.py、ia_03_anchor.py、ia_04_facts.py、ia_05_derived.py、ia_06_general.py、ib_00_tag.py、ic_05_test_refusal.py、ib_run_logged.sh
- 完整 stdout：`stdout/impl_b/` 下 29–43 号文件

结论：PASS
