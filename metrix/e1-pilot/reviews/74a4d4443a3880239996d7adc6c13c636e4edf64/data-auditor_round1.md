# data-auditor final report, Implementation stage B, round 1: staged work commit (parent 0bc0eecf1f684773248c198afb94e7026dcfb16d); invoked 2026-11-23 07:39 UTC (background); invocation text: data-auditor_prompt.txt
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a3a44a2128be87b0b.jsonl)
---
## Data Auditor 报告：Metrix E1-PILOT 实现阶段 B（HEAD 0bc0eecf1f684773248c198afb94e7026dcfb16d，Executor 改动已暂存、未提交）

五项都复算完成，没有发现与 Executor 不一致的地方，也没有不可复算的项。
- 四个冻结哈希：我的值、我从 data_b 文件按协议方法读回的值、PROTOCOL_FROZEN 中的值、Executor t3 打印的值，四方相同。另外 4 个文件和 anchor 的 ids 按内容逐条一致。
- Y/F 比在两种口径下都在区间内，与 t3 第 8–10 行相同。
- 1280 条 QA 打分输入和 480 条闭卷打分输入，ids 与起点逐条一致。
- 训练序列、6 组 batch 顺序、锚文档编号、学习率因子全部一致。
- TEST 生成器拒绝执行，没有留下任何产物。

下面「观察」一节列了几个需要 Review Gate 知道的地方，都不是不一致。

**运行环境**：主机 vm（Anthropic 云容器，Linux 6.18.44），只用 CPU，/dev 下没有 nvidia 设备。Python 3.13.18（transformers 5.22.2，tokenizers 0.23.3，pyarrow 26.0.1）。
- 只加载了分词器。加载 AutoTokenizer 时 transformers 自己导入了 torch，每份 stdout 的 `modules:` 行如实列出；没有实例化任何模型，也没有下载权重文件。
- 没有生成、读取或统计 TEST，也没有实例化任何 TEST 问句。`eval_sets.jsonl` 只对整个文件求了哈希；逐行时以二进制方式定位 split 值并计数，非 dev 行不解码、不解析。

**独立性**：
- 新写的脚本：`ib_00_tag.py`、`ib_01_compare.py`、`ib_02_yratio.py`、`ib_03_scoring.py`、`ib_04_training.py`、`ib_05_test_refusal.py`、`ib_06_static.py`、`ib_run_logged.sh`。
- 数据重新生成用的是我在阶段 A 写的 `ia_00`、`ia_01`、`ia_03`–`ia_06`，内容未改（`git diff --stat HEAD -- metrix/e1-pilot/audit/` 为空）。
- 这些脚本只导入标准库、`ia_common` 和 transformers / tokenizers / pyarrow / huggingface_hub。
- Executor 的代码：`interpretations.py` 只当文字读；`test_data.py`、`leakage.py`、`data.py` 等由 `ib_06` 用 `ast` 解析，不导入、不运行。唯一运行过的 Executor 代码是第 5 项指定的 TEST 生成器，作为黑盒运行一次。

**通用写法**：
- `S=/tmp/claude-0/-home-user/f24b86c9-a2c5-5317-8b43-751d1f505d91/scratchpad`
- `D=$S/auditor_ib/dl`：我按固定 revision 重新下载的文件
- `O=$S/auditor_ib/out`：我独立生成的数据
- 每条命令的形式：`cd /home/user/OpenMythos/metrix/e1-pilot/audit && bash ib_run_logged.sh stdout/impl_b/<NN>.txt $S/venv/bin/python -I -B <脚本> ...`。`ib_run_logged.sh` 会设置 `PYTHONDONTWRITEBYTECODE=1`。
- 完整 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_b/` 下的 00–13 号文件。
- 另有两次开发时的运行没有记入 stdout：一次是用一个问句探查 `apply_chat_template` 的返回格式（只用分词器），一次是在加入 f 节之前试跑 `ib_06_static.py`。作为证据的是上面目录里的正式运行。

---

### 1. 四个冻结哈希的三方比对；其余文件按内容比对

**命令**
- `ia_00_frozen.py /home/user/OpenMythos` → `00_ia_frozen.txt`
- `ib_00_tag.py /home/user/OpenMythos` → `01_ib_tag.txt`
- `ia_01_fetch.py /home/user/OpenMythos $D $S/inputs` → `02_ia_fetch.txt`
- `ia_03_anchor.py /home/user/OpenMythos $D/parquet/data/sample-100BT/train/shard_00000.parquet $D/qwen_tok $O` → `03`
- `ia_04_facts.py /home/user/OpenMythos $D/qwen_tok $O` → `04`
- `ia_05_derived.py /home/user/OpenMythos $D/qwen_tok $O` → `05`
- `ia_06_general.py /home/user/OpenMythos $D/parcae_tok/tokenizer.json $D/qwen_tok $O` → `06`
- `ib_01_compare.py /home/user/OpenMythos $D/qwen_tok $O $S/data_b` → `07_ib_compare.txt`

**关于 `00_ia_frozen.txt` 的 RESULT: FAIL**：这次运行中唯一为假的一行是 `tag metrix-e1-pilot-frozen-v1.1 -> metrix-e1-pilot-frozen-v1.1^{commit} | == freeze commit: False`。原因是本会话的 clone 里没有本地标签（`git tag -l` 为空）。如果去 fetch 标签就会写入 audit/ 以外的 `.git`，所以我改用 `01_ib_tag.txt` 只读核对远端：
```
remote tag metrix-e1-pilot-frozen-v1.1 (peeled) -> 87a244db28a901f9e89282b50df76778ab5c2887 | == freeze commit: True
freeze commit object type in the local clone: commit | ancestor of HEAD: True
RESULT: PASS
```
`00` 的其余各行都为真：四个文件的 PROTOCOL_FROZEN 值、`git cat-file` 值、工作区值三者相同；12 行数据哈希表与 manifest 相同。

**输入文件**（`02`）：我在新目录 `$D` 重新下载了 6 个固定文件。每个文件的 Hub 元数据、冻结 manifest、Executor 在 `$S/inputs` 下的副本三方都为 True，parquet 的 sha256 是 6a3450ea…2c22。`eval_sets.jsonl` 整个文件的哈希是 8816fe5a…a155，与 manifest 相同。下载目录里没有任何权重类文件。

**重新生成**（03–06）：
- 锚文本规范化哈希 8828bc4f…2408，MATCH True
- fact 406c8801…6b97，MATCH True
- train_S 686fdd2f…c1e，MATCH True
- candidates e5d15c99…3705，MATCH True
- `eval_sets` 按行前缀计数：dev 400，test 800（只计数）

**比对原始输出**（`07`，摘录）：
```
  facts        auditor 406c8801…6b97 | from data_b 406c8801…6b97 | PROTOCOL_FROZEN 406c8801…6b97 | t3 406c8801…6b97 | ALL EQUAL True
  train_S      auditor 686fdd2f…c1e | from data_b 686fdd2f…c1e | PROTOCOL_FROZEN 686fdd2f…c1e | t3 686fdd2f…c1e | ALL EQUAL True
  candidates   auditor e5d15c99…3705 | from data_b e5d15c99…3705 | PROTOCOL_FROZEN e5d15c99…3705 | t3 e5d15c99…3705 | ALL EQUAL True
  anchor_texts auditor 8828bc4f…2408 | from data_b 8828bc4f…2408 | PROTOCOL_FROZEN 8828bc4f…2408 | t3 8828bc4f…2408 | ALL EQUAL True
  anchor texts from my decode of the Executor's ids: 8828bc4f…2408 | == PROTOCOL_FROZEN True
  element-wise equal: facts True | train_S records True | candidates True | candidates key order True
  train_F (fact_id, text): auditor 120 | Executor 120 | identical sequence True
  train_Y (fact_id, kind, text): auditor 240 | Executor 240 | identical sequence True
  dev_qa (fact_id, template_id, question): auditor 320 | Executor 320 | identical sequence True
  general_dev (domain, source doc_id, ids): auditor 100 | Executor 100 | identical sequence True
  general_dev texts ... identical sequence True
  anchor_text (source row, ids): auditor 512 | Executor 512 | identical sequence True
  anchor_text texts ... identical sequence True
data_b listing [... 8 data files, leakage_report.json] | == 8 data files + leakage_report.json True | test_qa.jsonl present False | general_test.jsonl present False
```
（stdout 中是 64 位全值。）

另外，data_b 的 8 个文件各自的 byte 与 canonical 哈希都等于 t3 第 12–19 行，也都等于我在阶段 A 记录的 gen1 byte_sha256（`stdout/impl_a/10_ia_compare.txt`）。也就是说，data_b 与阶段 A 审过的数据逐字节相同。

**与 Executor 是否一致**：一致，没有差异。

### 2. Y/F token 比（协议第 2.6 节）

**命令**：`ib_02_yratio.py /home/user/OpenMythos $D/qwen_tok $O $S/data_b` → `08_ib_yratio.txt`

**原始输出**
```
== auditor regeneration: sequences F 120 | Y 240
  with one <|endoftext|> per sequence: F 1889 | Y 2260 | ratio 1.196400 | in [0.8, 1.25]: True
  without <|endoftext|>:               F 1769 | Y 2020 | ratio 1.141888 | in [0.8, 1.25]: True
== Executor data_b texts: (same counts)
auditor regeneration and data_b texts give the same counts: True
  t3:8: Y / F token ratio: F 1889, Y 2260, ratio 1.1964
  t3:9: Y / F token ratio without <|endoftext|> (report only): F 1769, Y 2020, ratio 1.1419
  t3:10: both ratios within [0.8, 1.25]: with True, without True
t3 line 8 (with) == mine ...: True | line 9 (without) == mine: True | line 10 interval and both True: True
protocol 2.6 authoring numbers F 1,889 / Y 2,260 / 1.196 == the 'with' counting: True
RESULT: PASS
```

**与 Executor 是否一致**：一致。两种口径都在 [0.80, 1.25] 内。

### 3. 打分输入（协议第 0、5 节）

**命令**：`ib_03_scoring.py /home/user/OpenMythos $D/qwen_tok $O $S/audit_dump_b.json` → `09_ib_scoring.txt`

我的构造方法：
- `chat(q)` 用 `apply_chat_template(tokenize=False, add_generation_prompt=True, enable_thinking=False)`，单个 user 回合。另外与 Qwen3 的字面渲染比对，也与 tokenize=True 的结果比对。
- QA 打分输入为 `chat(q) + "The answer is" + " " + c`，起点 = len(ids) − len(encode(" " + c))。
- 闭卷输入为 prefix(f) + " " + c，起点 = len(encode(prefix))。

**原始输出**（摘录）
```
audit_dump_b.json sha256 3ba470a9…be50 | recorded in t5 3ba470a9…be50 | MATCH True
entries 1280 | chat(q) != literal Qwen3 rendering: 0 | apply_chat_template(tokenize=True) != encode(chat(q)): 0 | ids != encode(chat(q) + 'The answer is') + encode(' ' + c): 0
Executor qa_inputs 1280 | distinct keys 1280 | same key set as mine True | same order as mine True
ids differ: 0 [] | start differs: 0 []
Executor ids[start:] != encode(' ' + c): 0 | len(scored) != K_st(c): 0
facts whose 4 candidates differ in scored length: 0 | scored length per cell: {capital/natural [3], capital/random [5], currency/natural [3], currency/random [6], founder/natural [3], founder/random [5], river/natural [3], river/random [6]}
TRAIN closed-book: entries 480 | ... ids != encode(prefix) + encode(' ' + c): 0
Executor cb_inputs 480 | ... same key set True | same order as mine True
ids differ: 0 [] | start differs: 0 | prefix string differs: 0
len(scored) != K_st(c): 0 | facts whose 4 candidates differ in length: 0 | inputs containing any special-token id: 0
pairs compared 240 | mismatches by prefix encoding 0 | by offset mapping 0 [] | vs the Executor's train_F training sequence 0
recorded 28 ids | mine 28 | Executor 28 | rendered text == recorded True
   0 recorded 151644 | mine 151644 | Executor 151644 | token '<|im_start|>' | equal True
   ... (第 1–24 位逐个 equal True)
  25 recorded 444 | mine 444 | Executor 444 | token 'ĠL' | equal True | scored
  26 recorded 6130 | ... | equal True | scored
  27 recorded 940 | ... | equal True | scored
start: recorded 25 | mine 25 | Executor 25 | scored ids recorded [444, 6130, 940] | mine [444, 6130, 940]
positions not equal in all three: 0
RESULT: PASS
```

**与 Executor 是否一致**：一致。learned 答案的不一致数为 0（240 对，用三种方法核对）。第 3 轮记录的 28 个 token 逐个三方相同。

### 4. 训练输入与顺序

**命令**：`ib_04_training.py /home/user/OpenMythos $D/qwen_tok $O $S/audit_dump_b.json` → `10_ib_training.txt`

**原始输出**（摘录）
```
  train_F.jsonl: mine 120 | Executor 120 | differing sequences 0 [] | tokens incl. <|endoftext|> 1889 | ... ends with 151643 True | special ids before the last position 0
  train_S.jsonl: mine 120 | Executor 120 | differing sequences 0 [] | tokens incl. <|endoftext|> 1889 ...
  train_Y.jsonl: mine 240 | Executor 240 | differing sequences 0 [] | tokens incl. <|endoftext|> 2260 ...
  seed 101, 120 rows, batch 8: steps mine 300 | Executor 300 | differing steps 0 [] | step numbers 1..300 True | each epoch a permutation True | batch sizes {8: 300} | step 1 batch [7, 21, 0, 60, 19, 16, 78, 33]
  (seed 101/240/16, 202/120/8, 202/240/16, 303/120/8, 303/240/16: differing steps 0)
anchor: steps mine 300 | Executor 300 | same step keys True | differing steps 0 []
step 1 [4, 5, 6, 7] | step 127 [508, 509, 510, 511] | step 128 [0, 1, 2, 3] | step 300 [176, 177, 178, 179] | uses per document {2: 336, 3: 176}
lr: steps mine 300 | Executor 300 | same keys True | not bit-identical 0 [] | max |diff| 0.000e+00
increasing on 1..15, decreasing on 15..300: True | lr(15) == 1: True | lr(300) == 0.1: True
RESULT: PASS
```

**与 Executor 是否一致**：一致，按 B1–B3 的口径，全部 bit 级相同。另外按静态阅读，`train.train_run` 调用的就是导出所用的同一组函数（`batch_schedule`、`lr_at`、`anchor_docs`、`encode_corpus`），锚文档送入的是 `anchor_text.jsonl` 中的 ids。

**B1–B3 与协议原文之间的歧义**。协议原文：
- 第 2.7 节：「第 s 步使用第 (4s + i) mod 512 篇」
- 第 7 节：「顺序 | 每遍一次全排列,`rng_rule(TRAIN_SEED, "order:<epoch>")`」「warmup | 前 15 步从 0 线性上升」「scheduler | 余弦,从峰值降到第 300 步时峰值的 10%」

`10` 号输出的「alternative readings」一节算出了其它读法下的数字，只作说明，不参与比对。

- **B1 步号**：协议没有写 s 从 0 还是从 1 起。「第 300 步」支持从 1 起，即 B1。但 mod 512 的结果是 0..511，说明文档按 0 起编号；如果 s 也从 0 起，第一步用 0–3 号文档。两种读法下，300 步的锚文档全部不同（300/300）。
- **B2 warmup**：「从 0 线性上升」可以有两种理解。一种是 B2：第 1 步就是 peak/15，第 15 步达到峰值，任何一步都不为 0。另一种是常见的 0 起计数实现：第 1 步学习率为 0，第 16 步达到峰值。后一种读法下，第 1 步虽然参数不动，AdamW 的动量仍会更新，训练轨迹不同。
- **B2 余弦**：从第 15 步开始到第 300 步，第 300 步恰为 0.1。这与原文「第 300 步时峰值的 10%」一致；0 起实现的最后一步是 0.100027。
- **B3 遍号**：协议没有写遍号是 1..20 还是 0..19。如果用 0..19，300 步的 batch 全部不同。
- **B3 全排列的调用方式**：第 7 节没有写。B3 用 `r.shuffle(list(range(N)))`，与第 2.6 节细节 4 相同；如果用 `r.sample(range(120), 120)`，结果不同（第 1 个 batch 就不同）。切片方式 p[0:B]、p[B:2B]… 也没有写明。
- **Y 的行序**：batch 的下标指向 `train_Y.jsonl` 的文件行序。协议没有规定 Y 文件的行序（Executor 与我都用 fact 序、每条先 entity 后 answer），`train_F`、`train_Y` 也没有冻结哈希。因此 Y 的 batch 组成取决于一个未冻结的选择。

### 5. TEST 隔离

**黑盒运行**：`ib_05_test_refusal.py /home/user/OpenMythos $S/venv/bin/python $S/inputs $S/data_b $S/auditor_ib/test_out_b` → `11_ib_test_refusal.txt`
- 脚本在 `metrix/e1-pilot/src` 下运行指定命令一次，只加了环境变量 `PYTHONDONTWRITEBYTECODE=1`，防止在 src/ 下写 .pyc。
- 运行前已确认前提条件 2 不可能成立。
- 脚本逐行读取输出；如果出现只有生成时才会打印的行，立即终止进程。

```
metrix/e1-pilot/results/gate0_record.json: in HEAD False | in working tree False | metrix/e1-pilot/results exists False
$ .../venv/bin/python -m metrix_e1.test_data --inputs .../scratchpad/inputs --data .../scratchpad/data_b --out .../scratchpad/auditor_ib/test_out_b
----- generator stdout+stderr begin -----
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL
----- generator stdout+stderr end -----
exit code 1 | killed by the auditor False
out_dir .../test_out_b exists: False
data_b unchanged (names, sizes, mtimes, sha256): True | test_qa.jsonl / general_test.jsonl in data_b: []
inputs unchanged: True | src tree unchanged (incl. __pycache__): True | git status --porcelain --ignored --untracked-files=all -- metrix unchanged: True
results directory created: False
RESULT: PASS
```
生成器拒绝执行，没有开始生成。

**静态检查**：`ib_06_static.py /home/user/OpenMythos` → `12_ib_static.txt`
- **调用位置**：`generate_test` 和 `run_test_part` 只在 `test_data.main` 中调用；`build_test_qa` 和 `params_for_test` 只在 `generate_test` 中调用；`TestAuthorization(...)` 只在 `check_preconditions` 的最后一句构造。
- **main 的结构**：try 块里只有 `check_preconditions`。它的处理器捕获 `(PreconditionFailed, ProtocolStop)`，打印后执行 `sys.exit(1)`；其它异常不在 main 中捕获，也会在生成之前离开 main。
- **入口守卫**：`generate_test` 和 `run_test_part` 的第一句都是 isinstance 守卫，不满足即抛出异常。
- **前提条件检查本身**：`check_preconditions` 只调用 `st12`、`load`、`check_data_dir`、`check_gate0_record`、`check_selection_record`。
- **`data.build_general_dev`**：非 dev 行的 `continue` 在 `json.loads` 之前（第 3 句对第 4 句）；比较用的 split 值来自冻结的 `general_text.dev`，为 'dev'。
- **`leakage.py`**：只读 7 个非 TEST 文件；`main` 不调用 `run_test_part`；没有任何 {E}/{A} 替换。
- **模板实例化**：全包只有 `build_test_qa` 实例化 TEST 模板；其它实例化位置只用 TRAIN、Y、DEV 模板。

**结论**：在三个前提条件都满足之前，没有任何路径 JSON 解析或用分词器解码非 dev 行，也没有实例化 TEST 问句。

**与 Executor 是否一致**：一致，与 test_data.py、leakage.py 文档中的说明相符。

---

### 观察（都不是不一致，供 Review Gate 参考）

1. **eval_sets.jsonl 以文本模式打开**：`data.build_general_dev` 用 `open(eval_sets_path, encoding='utf-8')` 逐行读取，所以 Python 会把每一行、包括 test 行的字节解码成 str，然后才做行前缀匹配。test 行不做 JSON 解析，不做 token 解码，除了 split 前缀之外没有用于任何计算。
   - 这段代码在阶段 B 没有改动；阶段 A 的 code-reviewer 认为这一行为合规。
   - 我的理解是，这不构成协议第 3 节所说的「解码 test 行的内容」。
   - 不过 ST13 的后果是整个 Pilot 作废。如果 Review Gate 想彻底排除这种解读，可以要求改为二进制模式读取（我的脚本就是这样读的）。
   - 这条路径在前提条件 1（`D.verify`）中也会运行。
2. **B1–B3 的歧义**：见第 4 项。当前实现与导出的数据都按 B1–B3 计算；这些读法仍是 PENDING_REVIEW_GATE。
3. **TestAuthorization 只是约定上的保护**：它是普通类，生产代码只在 `check_preconditions` 中构造它（静态核实），但任何调用者在技术上都能直接构造。

### 运行后的 `git status --short`（原始输出，也保存在 `stdout/impl_b/13_git_status_final.txt`）
```
A  metrix/e1-pilot/reports/impl_b/dump_for_audit.py
A  metrix/e1-pilot/reports/impl_b/t0b_step0_push.txt
A  metrix/e1-pilot/reports/impl_b/t0c_copy_check.txt
A  metrix/e1-pilot/reports/impl_b/t1_env_baseline.txt
A  metrix/e1-pilot/reports/impl_b/t2_fetch_config.txt
A  metrix/e1-pilot/reports/impl_b/t3_generate_leakage.txt
A  metrix/e1-pilot/reports/impl_b/t4_pytest.txt
A  metrix/e1-pilot/reports/impl_b/t5_dump_for_audit.txt
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
?? metrix/e1-pilot/audit/stdout/impl_b/
```
已暂存的条目与调用前完全相同，都是 Executor 的改动；新增的只有 audit/ 下的未跟踪文件。`git diff --stat HEAD -- metrix/e1-pilot/audit/` 为空。

所有文件都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/` 下：
- 脚本：`ib_00_tag.py`、`ib_01_compare.py`、`ib_02_yratio.py`、`ib_03_scoring.py`、`ib_04_training.py`、`ib_05_test_refusal.py`、`ib_06_static.py`、`ib_run_logged.sh`
- 完整 stdout：`stdout/impl_b/` 下 00–13 号文件

结论：PASS
