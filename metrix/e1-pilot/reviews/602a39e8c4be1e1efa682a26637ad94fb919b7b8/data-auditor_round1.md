# data-auditor final report, Implementation stage A, round 1: staged work commit (parent 8149d8727b4a99ea0cc9b0a1a2ebd82bd53fa0af); invoked 2026-11-22 16:35 UTC (background); invocation text: data-auditor_prompt.txt
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a520208ed2f433b4e.jsonl)
---
## Data Auditor 报告：Metrix E1-PILOT 实现阶段 A（HEAD 8149d8727b4a99ea0cc9b0a1a2ebd82bd53fa0af，Executor 改动已暂存未提交）

四个冻结哈希都由我自己的脚本从固定来源重新生成。我的值、从 Executor 文件按协议方法读回的值、冻结值，三方全部一致。没有冻结哈希的 5 个文件，内容与我独立生成的逐条一致。L1–L6（Gate 0 部分）、候选可行性、split 都一致。没有发现不一致的地方。

**运行环境**：主机名 vm（Linux 6.18.44 容器），只用 CPU，`/dev` 下没有 nvidia 设备。Python 用指定的 venv（3.13.18、transformers 5.22.2、tokenizers 0.23.3、pyarrow 26.0.1）。只加载了分词器，没有实例化任何模型，也没有下载权重文件。加载 AutoTokenizer 时 transformers 自己导入了 torch 库，每份 stdout 最后的 `modules:` 行都如实列出。

**TEST**：没有生成、读取或统计 TEST。`eval_sets.jsonl` 只对整个文件求了哈希；逐行时只以二进制方式在行首 80 字节内定位 split 值并计数，split 不是 dev 的行一律不解码、不解析。

**独立性**：所有脚本是我在 `metrix/e1-pilot/audit/` 下新写的，即 `ia_common.py`、`ia_00`–`ia_10`、`ia_run_logged.sh`。它们只导入标准库、`ia_common`、transformers/tokenizers/pyarrow/huggingface_hub，没有导入、调用或复制 `src/` 或 `reports/` 下的任何代码。Executor 的文件只当数据读。

**通用写法**：
- `S=/tmp/claude-0/-home-user/0dff44d1-df17-5cd8-99ed-7d453ca71e71/scratchpad`
- `D=$S/auditor_ia/dl`（我重新下载的固定文件）
- `O=$S/auditor_ia/out`（我独立生成的数据）
- 每条命令的形式是 `cd metrix/e1-pilot/audit && bash ia_run_logged.sh stdout/impl_a/<NN>.txt $S/venv/bin/python -I -B <脚本> ...`
- 完整 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_a/` 下的 `00`–`11` 号文件。

---

### 0. 冻结状态与输入文件（`00_ia_frozen.txt`、`01_ia_fetch.txt`）

命令：
- `ia_00_frozen.py /home/user/OpenMythos`
- `ia_01_fetch.py /home/user/OpenMythos $D $S/inputs`

原始输出摘录：
```
  current valid version line: 当前有效版本：v1.1
  v1.1 freeze commit in the current section: 87a244db28a901f9e89282b50df76778ab5c2887 | == audit constant: True
  tag metrix-e1-pilot-frozen-v1.1 -> 87a244db28a901f9e89282b50df76778ab5c2887 | == freeze commit: True
  metrix/e1-pilot/METRIX_E1_PROTOCOL.md: listed 1e80ca31… | blob 1e80ca31… | worktree 1e80ca31… | ALL EQUAL True
  (DATA_MANIFEST d1c32cdd…, SPLIT_MANIFEST 8c2c46a1…, SEARCH_SPACE aa59e2e7…: ALL EQUAL True)
  table rows parsed: 12   (12 rows MATCH True)
  protocol (freeze commit) 2.2 fact value 406c8801… | == manifest: True   (2.5, 2.6 同样 True)
== model Qwen/Qwen3-1.7B@70d244cc…: hub resolves the revision to 70d244cc… | same True
  tokenizer.json: … sha256 aeb13307… | hub lfs sha256 aeb13307… -> True | manifest True | Executor copy … -> True
  (tokenizer_config.json d5d09f07…, vocab.json ca10d7e9…, merges.txt 8831e4f1…, parcae tokenizer.json e0021e26…,
   shard_00000.parquet 6a3450ea…: hub True | manifest True | Executor copy True)
eval_sets.jsonl (whole file, no line parsed): 8816fe5a… | MATCH True
weight-like files under out_dir: []
RESULT: PASS
```

我在新目录 `$D` 按固定 revision 重新下载了这些文件，与 Hub 元数据、冻结 manifest、Executor 提供的 `inputs/` 副本三方一致。

### 1. 模板哈希与 template_set_sha256（`02_ia_templates.txt`）

命令：`ia_02_templates.py /home/user/OpenMythos`

原始输出摘录：
```
protocol 2.4 table rows: 16 | manifest texts == table (in order): True
templates matching: 32 / 32
template_set_sha256 recomputed 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | manifest 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | MATCH True
no trim: templates matching 0 / 32 | set hash with a final newline equals manifest: False
RESULT: PASS
```

32 个单模板值和集合哈希都与冻结 manifest 一致。Executor 的 L1 结果 `shared_hashes: []` 与我的一致（见第 3 项）。

### 2. 四个冻结哈希：独立重新生成，并三方比对

命令：
- `ia_03_anchor.py /home/user/OpenMythos $D/parquet/data/sample-100BT/train/shard_00000.parquet $D/qwen_tok $O`
- `ia_04_facts.py /home/user/OpenMythos $D/qwen_tok $O`
- `ia_05_derived.py /home/user/OpenMythos $D/qwen_tok $O`
- `ia_10_compare.py /home/user/OpenMythos $D/qwen_tok $O $S/gen1 $S/gen2 $S/gen3`

原始输出摘录（`03`/`04`/`05`/`10`）：
```
parquet rows read up to the 512th selected document: 527 | selected 512 ...
anchor decoded texts (512) canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | frozen 8828bc4f… | MATCH True
anchor-rule rejections: 0
regenerated facts canonical sha256 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | frozen 406c8801… | MATCH True
train_S rows 120 | canonical sha256 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | frozen 686fdd2f… | MATCH True
candidates keys 160 | canonical sha256 e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | frozen e5d15c99… | MATCH True
---- 10_ia_compare.txt
facts.jsonl: 160 lines, every line exactly the 6 fields: True; anchor_text.jsonl doc == line index: True
  facts        auditor 406c8801… | Executor file 406c8801… | frozen 406c8801… | ALL THREE EQUAL True
  train_S      auditor 686fdd2f… | Executor file 686fdd2f… | frozen 686fdd2f… | ALL THREE EQUAL True
  candidates   auditor e5d15c99… | Executor file e5d15c99… | frozen e5d15c99… | ALL THREE EQUAL True
  anchor_texts auditor 8828bc4f… | Executor file 8828bc4f… | frozen 8828bc4f… | ALL THREE EQUAL True
  anchor texts from the auditor's decode of the Executor's ids: 8828bc4f… | == frozen True
  facts.jsonl JSONL canonical sha256 (not compared with the fact value, protocol 2.2): e05561ac…
  element-wise equal: facts True | train_S records True | candidates True | candidates key order True
```

各项的复算方法：
- **fact**：按协议第 2.2 节的比对方法，从 `facts.jsonl` 按行序读出 6 个字段组成列表，再求规范化哈希。
- **train_S**：解析后按 JSONL 规范化求哈希。
- **candidates**：解析后按 JSON 规范化求哈希。
- **锚文本**：取 512 个 `text` 字段组成列表求哈希；另外用我的分词器解码 Executor 的 `ids` 再算一次。

Executor 的 `t2_fetch_generate.txt` 打印的四个值与上面相同。

### 2b. 没有冻结哈希的文件：只比内容（`05`、`06`、`10`）

命令：
- `ia_06_general.py /home/user/OpenMythos $D/parcae_tok/tokenizer.json $D/qwen_tok $O`
- 以及上面的 `ia_05`、`ia_10`

原始输出摘录：
```
eval_sets lines by located split value (counts only): {'dev': 400, 'test': 800}
dev lines kept per domain: {'books': 25, 'c4': 25, 'fineweb': 25, 'wikitext': 25}
  train_F (fact_id, text): auditor 120 | Executor 120 | identical sequence True
  train_Y (fact_id, kind, text): auditor 240 | Executor 240 | identical sequence True
  dev_qa (fact_id, template_id, question): auditor 320 | Executor 320 | identical sequence True
  general_dev (domain, source doc_id, ids): auditor 100 | Executor 100 | identical sequence True
  general_dev texts: auditor 100 | Executor 100 | identical sequence True
  anchor_text (source row, ids): auditor 512 | Executor 512 | identical sequence True
  anchor_text texts: auditor 512 | Executor 512 | identical sequence True
---- 05_ia_derived.txt
with one end-of-text token (id 151643) per sequence: F 1889 | Y 2260 | ratio 1.1964
learned facts checked: 120 | mismatches: []          (Y_ANSWER 与 TRAIN 句中 " "+答案 的切分相同)
... violations: [] | count 0                           (第 2.5 节暴露匹配)
```

结论：文本、id 序列、顺序、数量全部一致。Executor 的 `template_id` 字段与所用模板相符。

### 3. L1–L6 的 Gate 0 部分（L6 = 锚文本对 general DEV）（`07_ia_leakage.txt`）

命令：`ia_07_leakage.py /home/user/OpenMythos $D/qwen_tok $O $S/gen1`

原始输出摘录：
```
{"L1": 0, "L1_shared": [], ..., "L2": 0.2, "L2_pairs_at_max": [["capital.TRAIN.1", "capital.DEV.1"]], "L2_pairs": 368, "L2_both_empty": 4}
Executor anchor_text.jsonl: decode(ids) == text field for 512 of 512 | general_dev.jsonl: decode(ids) == text field for 100 of 100
  L6_anchor_word_13grams: auditor 44255 | Executor files 44255 | equal True
  L6_window_word_13grams: auditor 17780 | Executor files 17780 | equal True
  L1 value 0 | L2 value 0.2, pair capital.TRAIN.1/capital.DEV.1 | L3a 0 (80 strings) | L3b 0 (120) | L4 0 (320 questions, DEV)
  | L5 0 (learned 120, unread 40, strings 320) | L6 0 (512 docs, 100 windows) | token-id 13-grams 0
  → 与 Executor leakage_report.json 逐项 "equal True"(69 处 equal True, 0 处 equal False);result PASS == PASS
RESULT: PASS
```

每项检查都分别在我的数据和 Executor 的文件上算了一次，两边相同，并且与 `leakage_report.json` 的值、limit、within_limit、detail 逐项相同。

### 4. 候选可行性（`08_ia_feasibility.txt`）

命令：`ia_08_feasibility.py $D/qwen_tok $O $S/gen1`

原始输出摘录：
```
capital/natural/learned  15 {(3, 3): 15}  15  14 ... (16 cells; learned min available 15 / pool 14; unread 5 / 4)
minimum available candidates per fact (incl. the true answer): 5 | cells with available < 4: []
minimum distractor pool per fact: 4 | cells with pool < 4: []
auditor candidates.json: ... violating the four constraints [] (count 0) | position of the true answer {0: 41, 1: 38, 2: 45, 3: 36}
Executor candidates.json: ... violating the four constraints [] (count 0) | position of the true answer {0: 41, 1: 38, 2: 45, 3: 36}
```

四重约束指同 relation、同 stratum、同暴露类别、答案 token 数（K_st）相同。最小值是：每个 fact 可用候选 5 个（含真答案），干扰项池 4 个。不足 4 个的 cell：无。Executor 没有单独输出可行性数字，所以改为比对它的 `candidates.json`：与我的内容一致，0 处违反约束。

### 5. Split（`09_ia_split.txt`）

命令：`ia_09_split.py /home/user/OpenMythos $O $S/gen1`

原始输出摘录（两份数据相同）：
```
[Executor] facts 160 distinct 160 | learned 120 unread 40 | learned & unread 0 | ... 8 cells x (15 + 5) True | indices L01-15, U01-05 True
[Executor] TRAIN: train_F 120 | train_S 120 | train_Y 240 | unread fact_ids in TRAIN files [] | ...: True
[Executor] DEV: dev_qa 320 | every fact twice, once per DEV template of its relation: True | learned 240 unread 80
[Executor] candidates keys 160 == fact_ids True | general DEV windows 100 per domain {...25 each} | anchor documents 512
Executor directory listing: [...] | files with 'test' in the name: []
RESULT: PASS
```

fact_id 互斥，各 split 的数量都符合协议。我的数据与 Executor 的文件结果相同。

---

### 不构成 BLOCK 的说明

1. **gen1 早于最后一次修改**：gen1 生成于 16:27，早于 `data.py` 的最后一次修改（16:32）。按 Executor 的 t2 日志，gen3 在 16:34 生成，用的是 sha256 为 `efa35625…` 的 `data.py`。我用 `git cat-file blob :path` 核对过，这正是暂存区的那个 blob。gen2、gen3 的 8 个数据文件都与 gen1 逐字节相同（`10` 号文件 C 段）。由于我不运行 Executor 的代码，“gen3 由暂存代码生成”这一点只能依据 Executor 的日志。
2. **manifest 中的数据文件哈希仍为空**：两个 manifest 里的数据文件字段仍是 `NOT_GENERATED`，`split_sha256` 仍是 null（任务单红线 1 不允许改这三个 JSON）。所以与 manifest 比对只能针对四个冻结内容哈希。8 个文件的 byte/canonical 哈希改为与 Executor 的 t2 日志比对：全部相同。
3. **L2 中两边都是空集的模板对**：有 4 个跨集合模板对，两边都不足 4 个词（founder.DEV.1 对 4 个 Y_ANSWER 模板），4-gram 集合都是空的。我把这种情况按 0 计；manifest 的 authoring_result 是 0.2，Executor 也报 0.2，可见做法相同。协议没有规定这种情况；如果按 1 计，L2 会超过上限。DEFERRED_MINORS 中没有找到这一条，建议作为 MINOR 登记。
4. **Y/F token 比值的计数口径**：协议写的 1,889 / 2,260 只有在每个序列多计 1 个 endoftext 时才能复现。不计时是 1,769 / 2,020（比值 1.142）。两种口径都在 [0.80, 1.25] 内，但协议没写计数口径，属于 MINOR。
5. **模板归一化不去首尾空格时 0/32 相同**：这与已登记的 DEFERRED_MINORS S12 一致，本次复现。

### 运行后的 `git status --short` 原始输出（`11_git_status_final.txt`）
```
A  metrix/e1-pilot/reports/impl_a/t0_copy_check.txt
A  metrix/e1-pilot/reports/impl_a/t1_lock.txt
A  metrix/e1-pilot/reports/impl_a/t2_fetch_generate.txt
A  metrix/e1-pilot/reports/impl_a/t3_leakage.txt
A  metrix/e1-pilot/reports/impl_a/t4_pytest.txt
A  metrix/e1-pilot/requirements.lock
A  metrix/e1-pilot/src/metrix/e1_pilot/__init__.py
A  metrix/e1-pilot/src/metrix/e1_pilot/check_leakage.py
A  metrix/e1-pilot/src/metrix_e1/__init__.py
A  metrix/e1-pilot/src/metrix_e1/_cli.py
A  metrix/e1-pilot/src/metrix_e1/data.py
A  metrix/e1-pilot/src/metrix_e1/errors.py
A  metrix/e1-pilot/src/metrix_e1/frozen.py
A  metrix/e1-pilot/src/metrix_e1/leakage.py
A  metrix/e1-pilot/tasks/IMPLEMENTATION_TASK_ORDER_V1.md
A  metrix/e1-pilot/tests/conftest.py
A  metrix/e1-pilot/tests/test_data_hashes.py
A  metrix/e1-pilot/tests/test_leakage.py
A  metrix/e1-pilot/tests/test_st12.py
?? metrix/e1-pilot/audit/ia_00_frozen.py
?? metrix/e1-pilot/audit/ia_01_fetch.py
?? metrix/e1-pilot/audit/ia_02_templates.py
?? metrix/e1-pilot/audit/ia_03_anchor.py
?? metrix/e1-pilot/audit/ia_04_facts.py
?? metrix/e1-pilot/audit/ia_05_derived.py
?? metrix/e1-pilot/audit/ia_06_general.py
?? metrix/e1-pilot/audit/ia_07_leakage.py
?? metrix/e1-pilot/audit/ia_08_feasibility.py
?? metrix/e1-pilot/audit/ia_09_split.py
?? metrix/e1-pilot/audit/ia_10_compare.py
?? metrix/e1-pilot/audit/ia_common.py
?? metrix/e1-pilot/audit/ia_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_a/
```

暂存的 19 个 A 行与审计开始时完全相同，我的改动只有 `audit/` 下的新增文件，`git diff --stat` 为空。我生成的中间数据在 `$S/auditor_ia/out/`，不入库，可以按上面的命令重新生成。

按 `metrix/CLAUDE.md` 第 10 节，data-auditor 仍是“待验证”，这个 PASS 仅作参考。

结论：PASS
