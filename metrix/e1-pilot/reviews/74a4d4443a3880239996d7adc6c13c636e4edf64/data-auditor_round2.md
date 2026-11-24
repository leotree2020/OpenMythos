# data-auditor final report, Implementation stage B, round 2: staged work commit after the round-1 fixes (parent 0bc0eecf1f684773248c198afb94e7026dcfb16d); invoked 2026-11-23 08:06 UTC (background); invocation text: data-auditor_prompt_round2.txt
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a444cbd56cd2170be.jsonl)
---
## Data Auditor 报告：Metrix E1-PILOT 实现阶段 B 第 2 轮（HEAD 0bc0eecf1f684773248c198afb94e7026dcfb16d，Executor 的改动已暂存、未提交）

三项都已复算，没有发现与 Executor 不一致的地方，也没有不可复算的项。
- **数据**：data_c 的 8 个数据文件与 data_b 逐字节相同，与我本轮重新生成的结果、我第 1 轮的结果按内容逐条一致。四个冻结哈希按协议方法从 data_c 读回后，与我的值、PROTOCOL_FROZEN、t6 的 generate 输出、t6 的 verify 输出五方相同。
- **导出**：audit_dump_c.json 的 sha256 等于 t6 记录的值，与 audit_dump_b.json 逐字节相同。打分输入、训练序列、batch 顺序、锚文档、学习率因子重跑后全部一致。
- **TEST 隔离**：TEST 生成器拒绝执行，没有留下任何产物。src/ 里没有任何路径会在前提条件满足之前解码或解析非 dev 行，或实例化 TEST 问句。
- **仓库外的一条旧路径**：测试套件运行的 reports/round5/l6_check.py 仍以文本模式读 eval_sets.jsonl。详见「观察」第 1 条，需要 Review Gate 裁决。

**运行环境**：主机 vm（Anthropic 云容器，Linux 6.18.44），只用 CPU，/dev 下没有 nvidia 设备。Python 3.13.18（transformers 5.22.2，tokenizers 0.23.3，pyarrow 26.0.1）。
- 只加载了分词器，没有实例化任何模型，也没有读取权重文件。加载 AutoTokenizer 时 transformers 自己导入了 torch，每份 stdout 的 `modules:` 行如实记录。
- 没有生成、读取或统计 TEST，没有实例化任何 TEST 问句。
- eval_sets.jsonl 只做了两件事：对整个文件求哈希；以二进制方式按行前缀定位 split 值并计数。非 dev 行不做 UTF-8 解码，也不做 JSON 解析（ic_00、ia_06）。

**独立性**：
- 本轮新写的脚本：ic_00_state.py、ic_01_compare.py、ic_02_dump.py、ic_03_scoring.py、ic_05_test_refusal.py、ic_06_static.py、ic_07_static_selftest.py。
- ic_03 由我第 1 轮的 ib_03 改写：sha 改为取自 t6，并新增 _sliced 规则比对。ic_05 由 ib_05 改写，只改了标签。
- 沿用的脚本内容未改：ia_00、ia_03–ia_06、ib_00、ib_04、ib_run_logged.sh。
- 所有脚本只导入标准库、ia_common，以及 transformers / tokenizers / pyarrow。
- Executor 的代码一律用 ast 解析，不导入、不运行。唯一运行过的 Executor 代码是第 3 项指定的 TEST 生成器，作为黑盒运行一次。

**通用写法**：
- `S=/tmp/claude-0/-home-user/f24b86c9-a2c5-5317-8b43-751d1f505d91/scratchpad`
- 每条命令的形式：`cd /home/user/OpenMythos/metrix/e1-pilot/audit && bash ib_run_logged.sh stdout/impl_b/<NN>.txt $S/venv/bin/python -I -B <脚本> ...`
- 完整 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_b/` 下的 14–28 号文件（接第 1 轮的 00–13）。

---

### 0. 被审状态与固定输入

**命令**
- `ia_00_frozen.py /home/user/OpenMythos` → `14_ia_frozen.txt`
- `ib_00_tag.py /home/user/OpenMythos` → `15_ib_tag.txt`
- `ic_00_state.py /home/user/OpenMythos $S $S/auditor_ib/dl $S/inputs` → `16_ic_state.txt`

**原始输出（摘录）**
```
HEAD 0bc0eecf1f684773248c198afb94e7026dcfb16d | == 0bc0eecf…: True | branch metrix-e1-pilot-protocol-v1
unstaged changes under metrix/ (working tree vs index): []
git diff --cached sha256 963c144e…88cf | review_input_round2.diff body sha256 963c144e…88cf | identical True
review_input_round2.diff: sha256 b562dfa8…9500 | recorded in preflight_tools_check_round2.txt b562dfa8…9500 | MATCH True
review_fixes_round2.diff: sha256 8b6c0307…05e6 | recorded … 8b6c0307…05e6 | MATCH True
  (6 input files: mine | Executor | manifest | ALL EQUAL True, every line)
research/mini_mythos/stage1/results/r1/eval_sets.jsonl: sha256 8816fe5a…a155 | manifest 8816fe5a…a155 | MATCH True
rows by split value (line prefix only): {'dev': 400, 'test': 800} | lines without the prefix key: 0
RESULT: PASS
```

`14_ia_frozen.txt` 的结果是 RESULT: FAIL，原因与第 1 轮相同：
- 唯一为假的一行是本地标签那一行（本 clone 没有本地标签）。
- 除首行时间戳外，14 号与第 1 轮的 00 号逐行相同（`diff` 为空）。
- `15_ib_tag.txt` 只读核对了远端标签，结果为 PASS：`remote tag metrix-e1-pilot-frozen-v1.1 (peeled) -> 87a244db… | == freeze commit: True`。

---

### 1. data_c 的 8 个数据文件与四个冻结哈希

**命令**
- `ia_03_anchor.py`、`ia_04_facts.py`、`ia_05_derived.py`、`ia_06_general.py` 生成到新目录 `$S/auditor_ic/out`，输出为 17–20 号：
  - 锚文本 8828bc4f…2408 MATCH True
  - fact 406c8801…6b97 MATCH True
  - train_S 686fdd2f…c1e MATCH True
  - candidates e5d15c99…3705 MATCH True
  - eval_sets 只计数：`{'dev': 400, 'test': 800}`
- `ic_01_compare.py /home/user/OpenMythos $S/auditor_ib/dl/qwen_tok $S/auditor_ic/out $S/auditor_ib/out $S/data_b $S/data_c` → `21_ic_compare.txt`

**原始输出（摘录）**
```
== A. my regeneration of this round vs my round-1 regeneration (byte comparison)
  (9 files, each: identical True)
== B. four frozen hashes: auditor | read back from data_c | PROTOCOL_FROZEN | t6 generate | t6 verify
  facts        406c8801…6b97 ×5 | ALL EQUAL True
  train_S      686fdd2f…bc1e ×5 | ALL EQUAL True
  candidates   e5d15c99…3705 ×5 | ALL EQUAL True
  anchor_texts 8828bc4f…2408 ×5 | ALL EQUAL True
  anchor texts from my decode of the Executor's data_c ids: 8828bc4f…2408 | == PROTOCOL_FROZEN True
  element-wise equal: facts True | train_S records True | candidates True | candidates key order True
== C. train_F 120 / train_Y 240 / dev_qa 320 / general_dev 100 (ids, texts) / anchor_text 512 (ids, texts): identical sequence True (each)
== D. (each of the 8 files) data_c == data_b byte for byte True | canonical form True | == t6 line True | == t3 line True
== E. data_c listing [... 8 data files, leakage_report.json] | test_qa.jsonl present False | general_test.jsonl present False
== F. t6:11 rows by split {'dev': 400, 'test': 800} == my prefix count: True | 'rows parsed and decoded' 100 == my window count 100
RESULT: PASS
```

**与 Executor 是否一致**：一致，没有差异。
- t6 中 `data_b`/`data_c` 的 cmp 结果、t6 第 37–45 行的 verify 结果，都与我的比对相符。
- t6 第 3–25 行与 t3 相比，只有目录名不同。

---

### 2. audit_dump_c.json 与重跑的比对

**命令**
- `ic_02_dump.py /home/user/OpenMythos $S/audit_dump_b.json $S/audit_dump_c.json` → `22_ic_dump.txt`
- `ic_03_scoring.py /home/user/OpenMythos $S/auditor_ib/dl/qwen_tok $S/auditor_ic/out $S/audit_dump_c.json` → `23_ic_scoring.txt`
- `ib_04_training.py`（参数同上）→ `24_ib_training.txt`

**原始输出（摘录）**
```
t5 recorded (audit_dump_b.json): ['3ba470a97419dd34bd655e97d4d061c7de72700ae7692de37d14e1db2615be50'] | t6 recorded (audit_dump_c.json): ['3ba470a9…be50'] | t6 cmp exit 0
audit_dump_c.json sha256 3ba470a9…be50 | == t6 True | == t5 True
bytes: b 632222 | c 632222 | identical True
--- 23 ---
Executor qa_inputs 1280 | … same key set as mine True | same order as mine True
ids differ: 0 [] | start differs: 0 []
Executor ids[start:] != encode(' ' + c): 0 | len(scored) != K_st(c): 0
Executor cb_inputs 480 | … ids differ: 0 [] | start differs: 0 | prefix string differs: 0
== _sliced acceptance rules evaluated on the Executor's inputs (round 1: len(ids) - len(ctx) == K_st(c); round 2: ids[len(ctx):] == encode(' ' + c))
  qa: entries 1280 | accepted by the round-1 rule 1280 | accepted by the round-2 rule 1280 | start == len(encode(context)) 1280
  cb: entries 480 | accepted by the round-1 rule 480 | accepted by the round-2 rule 480 | start == len(encode(context)) 480
pairs compared 240 | mismatches by prefix encoding 0 | by offset mapping 0 [] | vs the Executor's train_F training sequence 0
positions not equal in all three: 0      (28-token sequence of ROUND3 task 7)
AUDIT_VALUE qa_inputs_ids_sha256 d05b57e5…9ccd   (== round 1, 09_ib_scoring.txt)
AUDIT_VALUE cb_inputs_ids_sha256 97e406d6…8d28   (== round 1)
--- 24 ---
  train_F/S/Y: differing sequences 0 | tokens incl. <|endoftext|> 1889 / 1889 / 2260
  6 schedules (seeds 101/202/303 × 120/8, 240/16): differing steps 0 each
anchor: differing steps 0 [] | lr: not bit-identical 0 [] | max |diff| 0.000e+00
RESULT: PASS (23, 24)
```

**与 Executor 是否一致**：一致。
- 新旧两种 _sliced 判定在全部 1760 条实际输入上都接受，所以这次改动不改变任何打分输入。
- B1–B3 文字有改动（B3 补写了 Y 行序的说明），但计算口径不变，导出逐字节相同。第 1 轮列出的 B1–B3 歧义仍然存在，仍是 PENDING_REVIEW_GATE。

---

### 3. TEST 隔离

**黑盒运行**：`ic_05_test_refusal.py /home/user/OpenMythos $S/venv/bin/python $S/inputs $S/data_c $S/auditor_ic/test_out_c` → `25_ic_test_refusal.txt`
```
metrix/e1-pilot/results/gate0_record.json: in HEAD False | in working tree False | metrix/e1-pilot/results exists False
$ …/venv/bin/python -m metrix_e1.test_data --inputs …/scratchpad/inputs --data …/scratchpad/data_c --out …/scratchpad/auditor_ic/test_out_c
----- generator stdout+stderr begin -----
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL
----- generator stdout+stderr end -----
exit code 1 | killed by the auditor False
out_dir …/test_out_c exists: False
data dir unchanged (names, sizes, mtimes, sha256): True | test_qa.jsonl / general_test.jsonl in the data dir: []
inputs unchanged: True | src tree unchanged (incl. __pycache__): True | git status --porcelain --ignored --untracked-files=all -- metrix unchanged: True
results directory created: False
RESULT: PASS
```

**静态检查**：`ic_06_static.py /home/user/OpenMythos` → `26_ic_static.txt`

data.build_general_dev（新的读取方式）：
```
  _ROW_HEAD = re.compile(b'\\{"domain": "[^"\\\\]*", "split": "([^"\\\\]*)", ') | pattern is bytes: True
  capture groups 1 | anchored at the domain field, group 1 = the split value up to the next quote: True
  open calls: ["open(eval_sets_path, 'rb')"] | exactly one open, mode 'rb', no encoding argument: True
  want: ["want = p.general_dev_split.encode('ascii')"]
    loop statement 0: m = _ROW_HEAD.match(line)
    loop statement 2: rows_by_split[m.group(1).decode('ascii', 'replace')] += 1
    loop statement 3: if m.group(1) != want:            (continue)
    loop statement 4: r = json.loads(line.decode('utf-8'))
  calls before the continue that take the row bytes: ['_ROW_HEAD.match(line)']
  decode / json calls before the continue: ["m.group(1).decode('ascii', 'replace')"]     (the split field only)
  frozen general_text.dev: "... with split == 'dev', file order" -> split value: dev
  test_data.generate_test: statement 0 'if not isinstance(authorization, LK.TestAuthorization):'; the TEST split is set at statement 7
```

test_data.py：
- main 的 try 块里只有 `check_preconditions`。它的处理器捕获 `(PreconditionFailed, ProtocolStop)`，打印后执行 `sys.exit(1)`；入口是 `run_guarded(main)`。
- `check_preconditions` 的语句顺序为：`st12, load, check_data_dir, check_gate0_record, check_selection_record, check_interpretations_ruled, TestAuthorization`（最后一句是 return）。
- `check_interpretations_ruled` 先执行 `open_ids = INT.pending()`，非空即抛出 `PreconditionFailed`。
- `ENTRIES 24 … with a status key 0 | pending now 24`：当前状态下这项检查也会拒绝。
- `_committed`、`check_gate0_record`、`check_selection_record` 不调用任何生成器或读取器。`record.committed_json` 只执行 `git cat-file blob HEAD:<rel>` 并读取工作区的同一个文件。

leakage.py：
```
  run_test_part statement 0: 'if not isinstance(authorization, TestAuthorization): raise …' -> guard True
  run_test_part: record re-check loop at statement 2 …; first statement using test_qa / general_test: 7 | re-check first True
  load_data file stems: ['facts', 'train_F', 'train_S', 'train_Y', 'dev_qa', 'anchor_text', 'general_dev']
  '{E}' / '{A}' constants in leakage.py: [] | leakage.main calls run_test_part: False
```

全包范围：
- 打开 eval_sets.jsonl 的调用只有 `data.py:506 build_general_dev open(eval_sets_path, 'rb')`。
- 调用位置都符合预期：generate_test、run_test_part 只在 main；build_test_qa、params_for_test 只在 generate_test；TestAuthorization 只在 check_preconditions；check_interpretations_ruled 只在 check_preconditions。
- `evaluate_model` 在包内和 dump 脚本中都没有调用者。
- 指向 TEST 材料的常量都不在预期位置之外（`stray: []`）。
- 模板实例化：test_data.py 中只有 `build_test_qa`；其它位置只有 DEV、TRAIN、Y 的生成函数、fill 和 `statement_prefix`。

tests/：
- `generate_test(fz, None, …)` 只用 None 调用。
- `run_test_part` 的两次调用，test_qa 与 general_test 都传 `[]`。
- 没有任何测试调用 build_test_qa、params_for_test，也没有用 split="test" 调用 evaluate_model。

**结论**：在三个前提条件和新增的解释裁决检查都满足之前，包内（src/metrix_e1）没有任何路径对非 dev 行做 UTF-8 解码、JSON 解析或 token 解码，也没有实例化 TEST 问句。仓库内包以外的路径见「观察」第 1 条。

**静态检查的阳性对照**：`ic_07_static_selftest.py /home/user/OpenMythos $S/auditor_ic/selftest` → `27_ic_static_selftest.txt`
- 做法：复制 ic_06 要读的文件，逐一植入 6 种故障：
  - M1：以文本模式打开 eval_sets.jsonl
  - M2：在 continue 之前做 json.loads
  - M3：删去解释裁决检查
  - M4：在记录复核之前使用 test_qa
  - M5：在 try 块中调用 generate_test
  - M6：新增一个 TEST 模板实例化
- 结果：未改动的副本 ic_06 判 PASS；M1–M6 都判 RESULT: FAIL，与预期一致。脚本本身判 RESULT: PASS。
- 说明：27 号是第二次运行。第一次运行的结论相同，只是诊断行的排序不便阅读，输出被覆盖。

**与 Executor 是否一致**：一致。与 test_data.py、leakage.py、data.py 文档中的说明相符。

---

### 观察（都不是不一致，供 Review Gate 参考）

1. **还有一条以文本模式读取 eval_sets.jsonl 的路径**：`tests/test_data_hashes.py::test_byte_identical_to_reference_scripts` 会对真实的 eval_sets.jsonl 运行 `reports/round5/l6_check.py`，后者用 `open(a.eval_sets, encoding='utf-8')` 读取。
   - 这意味着每一行、包括 test 行，都会被 Python 从 UTF-8 解码成 str。
   - test 行不做 JSON 解析（continue 在 json.loads 之前，静态核实），也不做 token 解码。
   - 这个测试在 t4 和 t6 的 pytest 中都运行过（PASSED），而且在 HEAD 中已经存在（阶段 A）。
   - 第 1 轮我只检查了 src/ 和 dump 脚本，漏报了这条路径。
   - 按我第 1 轮的理解，这不构成协议第 3 节所说的读取 TEST，所以不判 BLOCK。
   - 但 Executor 本轮修改的目的是「连 UTF-8 解码也不做」（data.py 文档原文），这个目的只在 data.py 中实现。
   - 如果 Review Gate 采用严格读法，这条路径需要同样处理；而且在严格读法下，它在过去的运行中已经发生过。因此请 Review Gate 明确裁决采用哪种读法。
2. **t6 第 11 行（t3 第 11 行相同）的标签不准确**：`rows parsed and decoded: 100`。
   - 按静态结构，build_general_dev 会对全部 400 条 dev 行做 UTF-8 解码和 JSON 解析（json.loads 在每域 25 条的上限之前执行）。
   - 100 只是保留下来、用 parcae 分词器解码的窗口数。
   - 只涉及 dev 行，不影响 TEST，也不影响数据。第 1 轮我也没有指出这一点。
3. **evaluate_model(split="test") 是新路径**：目前没有调用者。它只从传入的 data 字典中读取 test_qa.jsonl 和 general_test.jsonl，不接触 eval_sets，也不实例化模板。阶段 C 的驱动代码加入后需要再审。
4. **check_interpretations_ruled 是协议三个前提条件之外的第 4 个前提**（Executor 已注明）。24 条解释都处于 pending 状态。Gate 0 记录提交之后，TEST 仍会被这项检查拒绝，直到 Review Gate 逐条裁决。
5. **test_st12 的处理方式**：它用 `shutil.copyfile` 把真实的 eval_sets.jsonl 按字节复制到 pytest 临时目录，再翻转中间的一个字节，只做整文件哈希检查。全程按字节处理，不解码。仅供参考。
6. **过程说明**：
   - ic_06 和 ic_07 各有一次试跑没有记入 stdout，作为证据的是 26、27 号。
   - 21 号 F 节中的 dev/test 计数是直接引用 16 号 ic_00 的计算结果，不是重新计算。
   - 我在 scratchpad 中临时生成过一个 cached diff 和一个 selftest 试跑目录，都已删除；`find metrix -newer 14_ia_frozen.txt`（排除 audit/）的结果为空。

### 运行后的 `git status --short`（原始输出，也保存在 `stdout/impl_b/28_git_status_final.txt`）
```
A  metrix/e1-pilot/reports/impl_b/dump_for_audit.py
A  metrix/e1-pilot/reports/impl_b/t0b_step0_push.txt
A  metrix/e1-pilot/reports/impl_b/t0c_copy_check.txt
A  metrix/e1-pilot/reports/impl_b/t1_env_baseline.txt
A  metrix/e1-pilot/reports/impl_b/t2_fetch_config.txt
A  metrix/e1-pilot/reports/impl_b/t3_generate_leakage.txt
A  metrix/e1-pilot/reports/impl_b/t4_pytest.txt
A  metrix/e1-pilot/reports/impl_b/t5_dump_for_audit.txt
A  metrix/e1-pilot/reports/impl_b/t6_fix_round.txt
A  metrix/e1-pilot/src/metrix_e1/compute.py
A  metrix/e1-pilot/src/metrix_e1/contract.py
M  metrix/e1-pilot/src/metrix_e1/data.py
M  metrix/e1-pilot/src/metrix_e1/errors.py
A  metrix/e1-pilot/src/metrix_e1/evaluate.py
A  metrix/e1-pilot/src/metrix_e1/gate.py
A  metrix/e1-pilot/src/metrix_e1/interpretations.py
M  metrix/e1-pilot/src/metrix_e1/leakage.py
A  metrix/e1-pilot/src/metrix_e1/mode.py
A  metrix/e1-pilot/src/metrix_e1/record.py
A  metrix/e1-pilot/src/metrix_e1/stats.py
A  metrix/e1-pilot/src/metrix_e1/stops.py
A  metrix/e1-pilot/src/metrix_e1/test_data.py
A  metrix/e1-pilot/src/metrix_e1/train.py
A  metrix/e1-pilot/tasks/IMPL_B_OWNER_MESSAGE.md
M  metrix/e1-pilot/tests/conftest.py
A  metrix/e1-pilot/tests/test_arm_a.py
A  metrix/e1-pilot/tests/test_contract.py
M  metrix/e1-pilot/tests/test_data_hashes.py
A  metrix/e1-pilot/tests/test_evaluate.py
A  metrix/e1-pilot/tests/test_gate.py
A  metrix/e1-pilot/tests/test_lora.py
A  metrix/e1-pilot/tests/test_record.py
A  metrix/e1-pilot/tests/test_scoring.py
A  metrix/e1-pilot/tests/test_stats.py
A  metrix/e1-pilot/tests/test_stops.py
A  metrix/e1-pilot/tests/test_test_data.py
A  metrix/e1-pilot/tests/test_train.py
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
?? metrix/e1-pilot/audit/stdout/impl_b/
```
- 已暂存的条目都是 Executor 的改动；ic_00 核实了暂存内容等于 review_input_round2.diff 的正文。
- 新增的只有 audit/ 下的未跟踪文件。
- 第 1 轮的 ib_ 脚本和 00–13 号 stdout 的修改时间都早于本轮，本轮没有改动它们。

所有文件都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/` 下：
- 本轮脚本：ic_00_state.py、ic_01_compare.py、ic_02_dump.py、ic_03_scoring.py、ic_05_test_refusal.py、ic_06_static.py、ic_07_static_selftest.py
- 沿用的脚本：ia_00_frozen.py、ia_03_anchor.py、ia_04_facts.py、ia_05_derived.py、ia_06_general.py、ib_00_tag.py、ib_04_training.py、ib_run_logged.sh
- 完整 stdout：`stdout/impl_b/` 下 14–28 号文件

结论：PASS
