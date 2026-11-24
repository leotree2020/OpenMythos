# data-auditor final report, Implementation stage B second fix commit (staged; parent fdbb9def89351aa187c1b1ae9749884bc3a80fe9); invoked 2026-11-23 13:55 UTC (background); invocation text: data-auditor_prompt.txt
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a4faa067a2f21002a.jsonl)
---
## Data Auditor 报告：Metrix E1-PILOT 实现阶段 B 第二个修复提交（第 4 轮；HEAD fdbb9def89351aa187c1b1ae9749884bc3a80fe9，修复已暂存、未提交）

三项都已复算，结论都与 Executor 一致，没有不一致的项，也没有不可复算的项。
- **第 1 项**：我自己构造的 DEV 行文件与原文件的 400 条 dev 行逐字节相同、顺序相同，sha256 为 `ca433fdf9764b2a5a52179282a97016e3b2f54ed0e266991e06a9a1ecf766658`。它与 Executor 两次 pytest 运行留下的临时副本也逐字节相同。只用 DEV 行做第 2.7 节的选择，结果与用完整文件时相同，也与 data_d/general_dev.jsonl 逐条一致。
- **第 2 项**：改动之后，src/、tests/ 以及测试调用的 reports/ 脚本中，没有任何路径以文本模式打开 eval_sets.jsonl，也没有路径解码它的 test 行。l6_check.py 的文本模式读取现在只作用于 DEV 行副本，所以我第 2 轮的观察 1 已消除。verify_authorization 的三项新复核和 evaluate_model 的「TEST 只允许正式模式」检查，都在读取任何 TEST 内容之前执行。静态检查做了 20 个埋入故障的阳性对照，全部检出。
- **第 3 项**：TEST 生成器拒绝执行，没有留下产物。

**运行环境**：主机 vm（Anthropic 云容器，Linux 6.18.44），只用 CPU，/dev 下没有 nvidia 设备。Python 3.13.18，transformers 5.22.2，tokenizers 0.23.3。
- 只加载了分词器，没有实例化任何模型，也没有读取权重文件。加载 AutoTokenizer 时 transformers 会自行导入 torch，每份 stdout 的 `modules:` 行如实记录了这一点。
- 没有生成、读取或统计 TEST，没有实例化 TEST 问句。
- eval_sets.jsonl 只做了两件事：对整个文件求哈希；以二进制方式按行前缀定位 split 值并计数。非 dev 行不做 UTF-8 解码、不做 JSON 解析，字节也不写出、不比较。
- 没有运行 l6_check.py。

**独立性**：
- 本轮新写的脚本：ie_00_state.py、ie_01_devrows.py、ie_06_static.py、ie_07_static_selftest.py，由我之前的 id_ 脚本改写，或全新编写。
- 沿用、内容未改的脚本：ic_05_test_refusal.py、ib_run_logged.sh、ia_common.py。
- 所有脚本只导入标准库、ia_common，以及 tokenizers / transformers（只用分词器）。
- Executor 的代码一律用 ast 静态解析，或作为文本读取，不导入、不运行。唯一运行过的 Executor 代码是第 3 项指定的 TEST 生成器，黑盒运行一次。

**通用写法**：
- `S=/tmp/claude-0/-home-user/f24b86c9-a2c5-5317-8b43-751d1f505d91/scratchpad`
- 每条命令的形式：`cd /home/user/OpenMythos/metrix/e1-pilot/audit && bash ib_run_logged.sh stdout/impl_b/<NN>.txt $S/venv/bin/python -I -B <脚本> ...`
- 完整 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_b/` 下的 44–49 号文件（接前几轮的 00–43）。

---

### 0. 被审状态与固定输入

**命令**：`ie_00_state.py /home/user/OpenMythos $S $S/auditor_ib/dl $S/inputs` → `44_ie_state.txt`

**原始输出（摘录）**
```
HEAD fdbb9def89351aa187c1b1ae9749884bc3a80fe9 | == fdbb9def89351aa187c1b1ae9749884bc3a80fe9: True | branch metrix-e1-pilot-protocol-v1
unstaged changes under metrix/ (working tree vs index): []
staged files (9): t10_fix2_commit.txt, t9_fix_commit_push.txt, evaluate.py, leakage.py, test_data_hashes.py, test_evaluate.py, test_stops.py, test_test_data.py, test_train.py
staged files under metrix/e1-pilot/audit/: [] | staged files outside metrix/e1-pilot/: []
git diff --cached sha256 4fc62a3d…7f9b | review_input.diff body sha256 4fc62a3d…7f9b | identical True
(git diff --cached --stat; echo; git diff --cached) sha256 9c189cf1…bdc4 | review_input.diff sha256 9c189cf1…bdc4 | identical True
review_input.diff: sha256 9c189cf15e49fc28ba77804354f249f2b7f80bf0cb48e821ca556fa3224bbdc4 | recorded in preflight_tools_check.txt [...] | MATCH True
preflight_tools_check.txt records data-auditor_TOOLS_LINE_IDENTICAL: True / data-auditor_FRONTMATTER_IDENTICAL: True
  not in the staged change, working tree == HEAD blob: data.py / frozen.py / record.py / test_data.py / stops.py / mode.py / reports/round5/l6_check.py / round2/anchor_check.py / round2/gen_facts.py / round7/gen_s_cands.py / tests/conftest.py / tests/test_st12.py: True (each)
  (6 input files: mine | Executor | manifest | ALL EQUAL True, each; weight-like files: [] in both dirs)
research/mini_mythos/stage1/results/r1/eval_sets.jsonl: sha256 8816fe5a…a155 | manifest 8816fe5a…a155 | MATCH True
rows by split value (line prefix only): {'dev': 400, 'test': 800} | lines without the prefix key: 0
RESULT: PASS
```

我核对了仓库中的 .claude/agents/data-auditor.md：它的 frontmatter（tools 行为 `Read, Grep, Glob, Write, Bash`）与我已加载的定义相同，preflight 记录也一致。

---

### 1. DEV 行文件与第 2.7 节 general DEV 选择

**命令**：`ie_01_devrows.py /home/user/OpenMythos $S/auditor_ib/dl/parcae_tok/tokenizer.json $S/auditor_ib/dl/qwen_tok $S/data_d $S/auditor_id/out/general.json $S/auditor_ie/devrows /tmp/pytest-of-root/pytest-15/test_byte_identical_to_referen0 /tmp/pytest-of-root/pytest-14/test_byte_identical_to_referen0` → `45_ie_devrows.txt`

**做法**：
- 在二进制模式下用两个互相独立的定位器读取 split 值：
  - L1 是我前几轮用的方法：在前 80 字节内查找 `"split": "`。
  - L2 是行首锚定的方法，与测试中 `_ROW_SPLIT` 的含义相同，代码是我自己写的。
- 两个定位器在每一行上都要找到、且结果相等。
- 只把 split 为 `b"dev"` 的行按原始字节写入 `$S/auditor_ie/devrows/eval_sets_dev_rows.jsonl`。
- 第二遍按字节偏移切行（不用文件迭代），与 DEV 文件逐行归并比对。

**原始输出（摘录）**
```
rows by split value (prefix only): {'dev': 400, 'test': 800} | rows where L1 / L2 is missing or they disagree: []
DEV row numbers in eval_sets.jsonl (runs): ['1-400']
== B. (a)
pass 2 (byte offsets) rows 1200 | DEV rows met 400 | each equal to the next DEV-file row: True | DEV-file rows 400 all consumed: True
DEV file bytes 632604 == sum of the DEV rows' lengths 632604: True
DEV-file rows whose split (L1 or L2) is not dev: []
DEV rows: strict UTF-8 + JSON, parsed split == 'dev': True | rows with a b'\r' byte: [] | rows without the final b'\n': []
DEV file read in text mode (UTF-8, universal newlines, as a text-mode reader would): 400 lines, equal to the binary rows: True
DEV file sha256 ca433fdf9764b2a5a52179282a97016e3b2f54ed0e266991e06a9a1ecf766658
metrix/e1-pilot/DATA_MANIFEST.json: working tree == freeze-commit blob: True
the test's temporary manifest (built here in memory) differs from the frozen manifest at: [('general_text', 'source_file_sha256')]
l6_check.py (read as text): manifest loads ['json.load(open(a.manifest, encoding="utf-8"))["general_text"]'] | gt[...] subscripts ['key'] | keys of the pin loop [('source_file_sha256', 'decode_tokenizer_json_sha256')]
Executor pytest copy /tmp/pytest-of-root/pytest-15/.../eval_sets_dev_rows.jsonl: bytes 632604 sha256 ca433fdf…6658 | == my DEV file byte for byte: True
  its DATA_MANIFEST_dev_rows.json differs from the frozen manifest at [('general_text', 'source_file_sha256')] | value == my DEV file sha256: True
Executor pytest copy /tmp/pytest-of-root/pytest-14/...: (同上) True / True
== C. (b)
kept per domain: complete file {books: 25, c4: 25, fineweb: 25, wikitext: 25} other domains [] | DEV file {books: 25, c4: 25, fineweb: 25, wikitext: 25} other domains []
selected rows byte-identical and in the same order: True | DEV-file row k is eval_sets row dev_numbers[k] for every selected row: True
  books: eval_sets rows 301..325 | c4: 101..125 | fineweb: 1..25 | wikitext: 201..225 (doc_id <domain>-dev-000..024)
windows: complete file 100 | DEV file 100 | identical (domain, doc_id, ids, text): True
data_d/general_dev.jsonl: rows 100 | byte sha256 957666920c91ef5b9328984d26ed0628c8a80b439d461bea49b54c2235635e73
my windows (from the DEV file) == data_d/general_dev.jsonl row by row (domain, doc_id, ids, text): True | mismatching rows []
== my round-3 regeneration .../auditor_id/out/general.json (complete file, ia_06): True
AUDIT_VALUE general_dev_ids_canonical_sha256 2e30c443…598f | texts 363aa087…87c8 (与第 3 轮 35 号相同)
RESULT: PASS
```

**(a) 结论**：DEV 行文件与原文件的 dev 行逐字节相同、顺序相同。
- 所有 dev 行都在文件的第 1–400 行，所以 DEV 文件恰好就是原文件的前 400 行。
- 测试的临时 manifest 只改了 `general_text.source_file_sha256` 一个值。
- l6_check.py 从 manifest 中只取两个 pin 值。

**(b) 结论**：只用 DEV 行时的选择与用完整文件时相同，与 data_d/general_dev.jsonl 一致。
- 每个 domain 选出的 25 行逐字节相同、顺序相同。
- 由此得到的窗口与 data_d/general_dev.jsonl、我第 3 轮的结果都一致。
- DEV 行里没有 `\r`，所以 l6_check.py 用文本模式（universal newlines）读这个文件时，看到的仍是同样的 400 行。

**与 Executor 是否一致**：一致。
- 我的 DEV 文件与 Executor 的 pytest 临时副本（pytest-14、pytest-15）逐字节相同。
- 他们的临时 manifest 与我在内存中构造的含义相同。
- 这与 test_data_hashes.py 的说明，以及 t10 第 58 行 `test_byte_identical_to_reference_scripts PASSED` 相符。

---

### 2. 静态检查：src/ 与 tests/

**命令**：
- `ie_06_static.py /home/user/OpenMythos` → `47_ie_static.txt`（281 行）
- 阳性对照：`ie_07_static_selftest.py /home/user/OpenMythos $S/auditor_ie/selftest` → `48_ie_static_selftest.txt`

#### (1) 有无路径以文本模式打开或解码 test 行

**原始输出（摘录，47 号 a、i 节）**
```
calls that open eval_sets.jsonl: [('data.py', 507, 'build_general_dev', "open(eval_sets_path, 'rb')")]
   src/metrix_e1/data.py:554 in generate: build_general_dev(p, tok, paths['eval_sets'], ...)
   src/metrix_e1/data.py:507 in build_general_dev: open(eval_sets_path, 'rb')
   src/metrix_e1/test_data.py:148 in generate_test: D.build_general_dev(pt, tok, paths['eval_sets'], ...)
   tests/test_data_hashes.py:95 in _dev_rows_only: FZ.file_sha256(out)
   tests/test_data_hashes.py:114 in test_byte_identical_to_reference_scripts: _run([rep / 'round5/l6_check.py', '--eval-sets', dev_rows, ..., '--manifest', manifest, ...
   tests/test_data_hashes.py:84 in _dev_rows_only: open(src, 'rb')
   tests/test_data_hashes.py:84 in _dev_rows_only: open(out, 'wb')
   tests/test_st12.py:72 in mini_repo: shutil.copyfile(fz.repo_root / ev, root / ev)
   tests/test_st12.py:143 in test_eval_sets_one_byte: flip(root / p.general_source)
  hits outside the expected set (...): [] | expected hits all present: True
  frozen.file_sha256 opens ["open(path, 'rb')"] | ... binary whole-file hash only: True
  tests/test_st12.py flip calls ['bytearray', 'bytes', 'len', 'read_bytes', 'write_bytes'] (...no decode): True
  _ROW_SPLIT = re.compile(b'\\{"domain": "[^"\\\\]*", "split": "([^"\\\\]*)", ') | bytes pattern anchored at the domain field, one group = the split value: True
  src = the frozen general_text.source_file under the repository root: True | open calls ["open(src, 'rb')", "open(out, 'wb')"]
  calls in the loop that take the row: [(0, '_ROW_SPLIT.match(line)'), (2, 'fo.write(line)')] | decode / json of a row anywhere in the helper: []
  `if m.group(1) == b'dev'` ...; fo.write(line) only in its body, nothing written in the else branch: True | ... True | ... True
  asserts: ["assert n == {'dev': 400, 'other': 800}", 'assert m is not None'] | ...: True
  manifest copy: ... | only general_text.source_file_sha256 replaced: True
  _run at statement 2/3/4: anchor_check.py / gen_facts.py / gen_s_cands.py | --eval-sets None
  _run at statement 6: rep / 'round5/l6_check.py' | --eval-sets dev_rows | --manifest manifest
  `dev_rows, manifest = _dev_rows_only(tmp_path)` at statement 5; l6_check.py gets --eval-sets dev_rows and --manifest manifest, no other script gets --eval-sets: True
  run by tests (module): metrix.e1_pilot.check_leakage / metrix_e1.data / metrix_e1.test_data; (script): round2/anchor_check.py False, round2/gen_facts.py False, round5/l6_check.py True, round7/gen_s_cands.py False  [mentions eval_sets]
  reports/ scripts run by tests that mention eval_sets: ['metrix/e1-pilot/reports/round5/l6_check.py'] (l6_check.py receives only the DEV-rows copy, above)
```

结论：没有任何路径以文本模式打开真实的 eval_sets.jsonl，也没有路径解码它的 test 行。各处读取方式如下：
- **src/ 的读取**：只有 data.build_general_dev 的 `open(..., 'rb')`。它在 non-dev 的 continue 之前，只做前缀匹配和 split 字段的 ascii 解码（47 号 b 节，与第 3 轮相同）。
- **tests/ 中的 `_dev_rows_only`**：以二进制模式读取，对每一行只做 `_ROW_SPLIT.match(line)`，dev 行原样写出，没有任何 decode 或 loads。
- **测试调用的 reports/ 脚本**：只有 l6_check.py 涉及 eval_sets。它收到的是 DEV 行副本和临时 manifest，第 1 项已证明该副本只含 DEV 行。
- **test_st12**：`shutil.copyfile` 是二进制复制；`flip` 对临时副本做 read_bytes、改一个字节、write_bytes；`check_inputs` 只对整个文件求哈希。三者都不解码。

#### (2) 新复核与模式限制是否在读取 TEST 内容之前执行

**原始输出（摘录，47 号 d 节）**
```
generate_test statement 0 is LK.verify_authorization(authorization, fz.repo_root): True | readers / builders after it: [(1,'params'),...,(8,'build_general_dev')] (all at statement > 0: True)
run_test_part statement 0: 'verify_authorization(authorization, repo_root)' -> verify first True | first statement using test_qa / general_test: 5 | after the verify True
      guard statement 0: if not mode.formal:
      guard statement 1: from .leakage import verify_authorization
      guard statement 2: verify_authorization(test_authorization, repo_root)
  split check 0 < guard 1 < require_gpu 2 < first statement touching data / qa_file / gen_file 3 ('qa_file, gen_file = SPLIT_FILES[split]')
  evaluate_model: for split 'test' the formal-mode check and then verify_authorization run before anything touches the data: True
  mode.RunMode.formal: decorators ['property'] body ['return self.name == FORMAL'] | ["FORMAL = 'formal'"]
  statement 0 isinstance guard raising True | loop (statement 3) over both records ... True | NotCommitted -> raise, got != want -> raise True
  after the loop: status ... `status != 'PASS'` -> raise at 1; binding ... -> raise at 2; PROTOCOL_FROZEN parsed (OSError / ST12Error -> raise) at 3; `current != authorization.frozen_commit` -> raise at 4 | all three present: True
  raises 7 (all ImplementationFail: True) | all calls ['ImplementationFail','Path','committed_record','get','isinstance','parse_protocol_frozen','read_bytes'] | reads ['R.committed_record(...)', '(Path(repo_root) / FZ.PROTOCOL_FROZEN_REL).read_bytes()'] | TEST names used [] | ...: True
  frozen: ["PILOT_REL = 'metrix/e1-pilot'", "PROTOCOL_FROZEN_REL = PILOT_REL + '/PROTOCOL_FROZEN'"] | parse_protocol_frozen(data) ... file / git reads in it: []
  -> the three new re-checks are statements of verify_authorization, which is statement 0 of generate_test and run_test_part and runs inside the evaluate_model guard before the data: True
```

结论：两者都在读取任何 TEST 内容之前执行。
- **三项新复核的位置**：都在 verify_authorization 内部，依次是 Gate 0 status 为 PASS、freeze 记录绑定到 Gate 0 记录、授权的 frozen commit 等于 PROTOCOL_FROZEN 中的值。
- **三项新复核读取的内容**：只有两份已提交记录（git cat-file 加工作区字节）和 PROTOCOL_FROZEN。parse_protocol_frozen 不读任何文件。
- **verify_authorization 的调用位置**：它是 generate_test 和 run_test_part 的第 0 条语句。
- **evaluate_model 中的顺序**：模式检查在 `if split == 'test'` 守卫的第 0 条语句；守卫在 require_gpu 和任何数据访问之前；模式检查又在 verify_authorization 之前。

其余部分与第 3 轮相同，结果全部为 True：
- 调用位置：`evaluate_model` 在包内仍然没有调用者；`TestAuthorization` 只在 check_preconditions 中构造。
- TEST 模板实例化只有 `build_test_qa` 一处。
- 两份记录在 HEAD 上都没有提交。

tests/ 中各处 TEST 路径调用（47 号 h 节）：
- `evaluate_model(split='test')` 的两处调用都用 data_rows 和 fz.repo_root：
  - 一处用 `M.FORMAL_MODE`，会被 verify_authorization 拒绝。
  - 一处用 smoke 或 preflight 模式，在模式检查处就被拒绝。
- `generate_test` 只以 `None` 或 `TestAuthorization(None, None, None)` 调用。
- `run_test_part` 收到的 test_qa、general_test 都是 `[]`。
- 新增的 verify_authorization 和 check_preconditions 测试只做核验，之后不调用任何 TEST 路径。

#### 阳性对照（48 号）

做法：在源码副本上逐一植入故障，看 ie_06 能否检出。未改动的副本判 `control ... expected PASS -> True`；20 个故障全部判 `RESULT: FAIL`，每一个都是 `expected FAIL -> True`。脚本本身判 RESULT: PASS。

本轮新增的 14 个故障：
- N1：`_dev_rows_only` 以文本模式打开文件
- N2：把真实的 eval_sets.jsonl 交给 l6_check.py
- N3：在前缀匹配之前对每行做 decode
- N4：把非 dev 行也写入副本
- N5：临时 manifest 还改了另一个值
- N6：删去模式检查
- N7：模式检查移到数据访问之后
- N8：删去 status 复核
- N9：删去绑定复核
- N10：放宽 status 复核（接受 NOT_TESTED）
- N11：verify_authorization 读取一个 TEST 文件
- N12：test_st12 以文本方式读取 eval_sets
- N13：flip 先解码再修改
- N14：删去 PROTOCOL_FROZEN 复核

沿用上一轮的 6 个故障：M1、M2、M5、M6、M7、M8。

**与 Executor 是否一致**：一致。
- t10 第 23–26 行的 grep 只列出 `data.py:507 open(eval_sets_path, "rb")` 和 `test_data_hashes.py:81 src = ...`。这与我枚举到的、对真实文件的两处二进制打开相同（后者在第 84 行打开第 81 行的 src）。
- 改动中 verify_authorization 与 evaluate_model 的文档说明，与静态结构相符。

---

### 3. TEST 生成器黑盒运行（一次）

**命令**：`ic_05_test_refusal.py /home/user/OpenMythos $S/venv/bin/python $S/inputs $S/data_d $S/auditor_ie/test_out_e` → `46_ic_test_refusal.txt`

**原始输出（摘录）**
```
out_dir .../auditor_ie/test_out_e exists: False
metrix/e1-pilot/results/gate0_record.json: in HEAD False | in working tree False | metrix/e1-pilot/results exists False
$ .../venv/bin/python -m metrix_e1.test_data --inputs .../scratchpad/inputs --data .../scratchpad/data_d --out .../scratchpad/auditor_ie/test_out_e
----- generator stdout+stderr begin -----
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL
----- generator stdout+stderr end -----
exit code 1 | killed by the auditor False
refused (non-zero exit, last line RESULT: FAIL, refusal line present): True
out_dir .../test_out_e exists: False
data dir unchanged (names, sizes, mtimes, sha256): True | test_qa.jsonl / general_test.jsonl in the data dir: []
inputs unchanged: True | src tree unchanged (incl. __pycache__): True | git status --porcelain --ignored --untracked-files=all -- metrix unchanged: True
results directory created: False
RESULT: PASS
```

运行后我又执行了一次 `ls $S/auditor_ie/test_out_e`，结果为「No such file or directory」。

**与 Executor 是否一致**：一致。拒绝信息的三行与退出码 1，与 t10 第 27–33 行逐字相同，两边的输出目录都不存在。

---

### 观察（都不是不一致，供 Review Gate 参考）

1. **我第 2 轮的观察 1 已消除**。测试中 l6_check.py 的文本模式读取，现在只作用于只含 DEV 行的副本。l6_check.py 本身没有改动（44 号：工作区 == HEAD）。
2. **verify_authorization 仍不复核条件 1（ST12）和解释裁决检查**，其文档也写明了这一点。这两项仍靠 check_preconditions 和每一步开始时的 ST12 保证。我第 3 轮观察 2 的其余部分（status、绑定、frozen commit）已由本次改动补上。
3. **PROTOCOL_FROZEN 读的是工作区文件**：新的 PROTOCOL_FROZEN 复核读取 `repo_root` 工作区中的 PROTOCOL_FROZEN，不是 HEAD blob。这与 TEST 隔离无关，仅作记录。
4. **测试会构造一个真实的授权对象**：`test_check_preconditions_calls_the_interpretation_check` 现在会在桩条件下，由 check_preconditions 构造一个 TestAuthorization。它没有被交给任何 TEST 路径；在真实仓库中，记录没有提交，verify_authorization 也会拒绝它。
5. **test_st12 的 flip 改的是 test 行范围内的一个字节**：flip 修改临时副本的中间字节（第 949603 字节）。按文件总字节 1899206 和 DEV 部分 632604 字节计算，这个位置落在 test 行范围内。它只改原始字节，随后只对整个文件求哈希，不解码、不解析。这一点在本次改动之前就已存在。
6. **过程说明**：
   - ie_06 在正式记录前有 4 次试跑，没有记入 stdout，结果在 `$S/auditor_ie/trial1_ie06.txt` 至 `trial4_ie06.txt`。修改都只针对我自己脚本的预期写法，没有改变判定对象：
     - 预期命中集合补上了 DEV 副本的写出、哈希和 l6_check 调用，因为副本的文件名含 eval_sets；
     - 子进程模块识别限定为 `sys.executable` 开头的列表，原先误把 `git commit -m` 当成模块；
     - 修正了 write 调用比较的写法和顺序；
     - 给各项检查补上显式布尔输出。
   - ie_07 有 1 次试跑，在 `$S/auditor_ie/trial_ie07.txt`，结果与正式记录相同。
   - 我以二进制方式读取了 Executor 的 pytest 临时目录 `/tmp/pytest-of-root/pytest-14`、`/tmp/pytest-of-root/pytest-15`：先比对整个文件；确认与我的 DEV 文件相同后，才解析临时 manifest。
   - 本轮在 audit/ 中只新增了 ie_00、ie_01、ie_06、ie_07 四个脚本和 44–49 号 stdout，以前的文件都没有改动（`find -newer 43_git_status_final.txt` 已核实）。
7. **信任状态**：按 metrix/CLAUDE.md 第 10 节，data-auditor 仍为「待验证」，本 PASS 仅作参考。

### 运行后的 `git status --short`（原始输出，也在 `stdout/impl_b/49_git_status_final.txt`）
```
A  metrix/e1-pilot/reports/impl_b/t10_fix2_commit.txt
A  metrix/e1-pilot/reports/impl_b/t9_fix_commit_push.txt
M  metrix/e1-pilot/src/metrix_e1/evaluate.py
M  metrix/e1-pilot/src/metrix_e1/leakage.py
M  metrix/e1-pilot/tests/test_data_hashes.py
M  metrix/e1-pilot/tests/test_evaluate.py
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
?? metrix/e1-pilot/audit/ie_00_state.py
?? metrix/e1-pilot/audit/ie_01_devrows.py
?? metrix/e1-pilot/audit/ie_06_static.py
?? metrix/e1-pilot/audit/ie_07_static_selftest.py
?? metrix/e1-pilot/audit/stdout/impl_b/
--- files under metrix/ newer than stdout/impl_b/44_ie_state.txt, audit/ excluded:
metrix/e1-pilot/audit
--- end
 9 files changed, 393 insertions(+), 22 deletions(-)
0
```
- 已暂存的 9 项都是 Executor 的改动。44 号核实了暂存内容等于 review_input.diff，工作区相对暂存区没有未暂存的改动（末行的 0）。
- find 只列出了 audit/ 目录本身：audit 下新增了文件，目录的修改时间随之变化。
- 本轮新增的只有 audit/ 下的未跟踪文件。

所有文件都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/` 下：
- 本轮脚本：ie_00_state.py、ie_01_devrows.py、ie_06_static.py、ie_07_static_selftest.py
- 沿用的脚本：ic_05_test_refusal.py、ib_run_logged.sh、ia_common.py
- 完整 stdout：`stdout/impl_b/` 下 44–49 号文件

结论：PASS
