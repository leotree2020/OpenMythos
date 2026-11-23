# data-auditor final report, Implementation stage A, round 2: data of the staged work commit after the round-1 fixes (gen4), committed unchanged as 602a39e8c4be1e1efa682a26637ad94fb919b7b8; invoked 2026-11-22 16:54 UTC (background), interrupted by HTTP 429, resumed 2026-11-23 01:11 UTC; invocation text: data-auditor_prompt_round2.txt; resume: resume_message_data-auditor_round2.txt
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-ab58901572f482778.jsonl)
---
Metrix E1-PILOT 实现阶段 A，数据审计第 2 轮（接中断继续）。对象是 gen4，结论 PASS。

**运行环境**
- 主机 vm：Linux 6.18.44 容器，只有 CPU，`/dev` 下没有 nvidia 设备。
- 解释器：`/tmp/claude-0/-home-user/0dff44d1-df17-5cd8-99ed-7d453ca71e71/scratchpad/venv/bin/python`（Python 3.13.18，transformers 5.22.2，torch 2.11.0）。
- 只加载了 tokenizer（Qwen tokenizer 和 parcae tokenizer.json），没有构建或加载任何模型权重。
- 没有 import、调用或复制 Executor 的代码。Executor 的源码只在第 12 号里按字节求了哈希。
- TEST：eval_sets.jsonl 只对整个文件求哈希，并按行前缀定位 split 后计数（dev 400，test 800）。非 dev 行一律不解析、不解码。没有实例化任何 TEST 问句。
- 仓库状态：HEAD 8149d8727b4a99ea0cc9b0a1a2ebd82bd53fa0af，暂存区与中断记录一致。

**中断后的处理**
- 重启后先核对了状态：仓库中的 data-auditor.md 已读，与已加载定义的 frontmatter 一致。stdout/impl_a/ 下只有 00–11。gen4 的 9 个文件 sha256 与中断前一致。
- 中断前我只跑过一次没有留档的 `sha256sum gen1/* gen4/*` 和一次 diff。正式证据以下面 12–22 号的留档输出为准。

**新写的脚本和中间数据**
- 新脚本：`/home/user/OpenMythos/metrix/e1-pilot/audit/ia_11_r2_inputs.py`、`/home/user/OpenMythos/metrix/e1-pilot/audit/ia_12_r2_bytes.py`。
- 复用的第 1 轮脚本：ia_03 至 ia_10。
- 我用自己的脚本把数据重新生成到一个新目录 `/tmp/claude-0/-home-user/0dff44d1-df17-5cd8-99ed-7d453ca71e71/scratchpad/auditor_ia/out_r2`。这是会话临时目录，第 1 轮的 auditor_ia/out 也放在同一位置。仓库内只写入了 audit/。
- 完整 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_a/12_*.txt` 到 `22_*.txt`。

下文命令中 SP 指 `/tmp/claude-0/-home-user/0dff44d1-df17-5cd8-99ed-7d453ca71e71/scratchpad`，PY 指 `$SP/venv/bin/python -I -B`。所有命令都经 `ia_run_logged.sh` 运行，工作目录为 audit/。

---
## 0. 输入完整性、gen4 的来源、重新生成我的数据（第 12–16 号）

**命令**
```
PY ia_11_r2_inputs.py /home/user/OpenMythos $SP/auditor_ia/dl $SP/inputs $SP/gen4          -> 12_ia_r2_inputs.txt
PY ia_03_anchor.py  /home/user/OpenMythos $SP/auditor_ia/dl/parquet/data/sample-100BT/train/shard_00000.parquet $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2   -> 13
PY ia_04_facts.py   /home/user/OpenMythos $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2   -> 14
PY ia_05_derived.py /home/user/OpenMythos $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2   -> 15
PY ia_06_general.py /home/user/OpenMythos $SP/auditor_ia/dl/parcae_tok/tokenizer.json $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2   -> 16
```

**原始输出（摘录）**
```
  qwen_tok/tokenizer.json: auditor aeb13307... | Executor aeb13307... | manifest aeb13307... | ALL EQUAL True
  (tokenizer_config / vocab / merges / parcae tokenizer.json / parquet 6a3450ea...: ALL EQUAL True)
files under the auditor's dl dir (without .cache): [6 个文件] | weight-like: []
== 3. eval_sets.jsonl (whole file, no line read): 8816fe5a...a155 | manifest 8816fe5a...a155 | MATCH True
  data.py: staged blob 8a531939... | working tree 8a531939... | printed before the gen4 run 8a531939... | ALL EQUAL True
  frozen.py 5abeeccb... / leakage.py 5e1d4374... / errors.py 9766d215...: ALL EQUAL True
  src/metrix_e1/frozen.py: 2026-11-22 16:51:25 UTC ... gen4/*.jsonl: 2026-11-22 16:52:33 UTC, gen4/leakage_report.json 16:52:38 UTC
RESULT: PASS
13: anchor decoded texts (512) canonical sha256 8828bc4f...2408 | frozen 8828bc4f...2408 | MATCH True ... RESULT: PASS
14: regenerated facts canonical sha256 406c8801...6b97 | frozen 406c8801...6b97 | MATCH True ... RESULT: PASS
15: train_S ... 686fdd2f...bc1e | frozen ... MATCH True; candidates e5d15c99...3705 | frozen ... MATCH True; Y/F 1889/2260 1.1964; exposure violations: [] ... RESULT: PASS
16: eval_sets lines by located split value (counts only): {'dev': 400, 'test': 800}; non-dev lines: only located and counted ...; windows 100 ... RESULT: PASS
```

**与 Executor 是否一致：一致**
- 输入文件三方相同：我的副本、Executor 的副本、冻结 manifest。
- 暂存区中 data.py、frozen.py、leakage.py、errors.py 的哈希，等于 Executor 在 t2_fetch_generate.txt 中 gen4 生成前打印的值。
- gen4 的 mtime 晚于最后一次代码改动。

---
## 第 2 项：四个冻结哈希的三方比对，对象 gen4（第 17 号）

**命令**
```
PY ia_10_compare.py /home/user/OpenMythos $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2 $SP/gen4 $SP/gen1   -> 17_ia_compare_gen4.txt
```

**原始输出**
```
facts.jsonl: 160 lines, every line exactly the 6 fields: True; anchor_text.jsonl doc == line index: True
  facts        auditor 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | Executor file 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | frozen 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | ALL THREE EQUAL True
  train_S      auditor 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | Executor file 686fdd2f...bc1e | frozen 686fdd2f...bc1e | ALL THREE EQUAL True
  candidates   auditor e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | Executor file e5d15c99...3705 | frozen e5d15c99...3705 | ALL THREE EQUAL True
  anchor_texts auditor 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | Executor file 8828bc4f...2408 | frozen 8828bc4f...2408 | ALL THREE EQUAL True
  anchor texts from the auditor's decode of the Executor's ids: 8828bc4f...2408 | == frozen True
  element-wise equal: facts True | train_S records True | candidates True | candidates key order True
RESULT: PASS
```

**与 Executor 是否一致：一致**
- t2_fetch_generate.txt 中 gen4 的 "frozen content hash ... read back from gen4" 四个值，以及 t3_leakage.txt 中 "ST12 range (1)" 的四个值，都等于上面三方相同的值。

---
## 第 2b 项：没有冻结哈希的文件，按内容比对（第 17 号第 B 节）

**原始输出**
```
  train_F (fact_id, text): auditor 120 | Executor 120 | identical sequence True
    Executor train_F template_id == <relation>.TRAIN.1: True
  train_Y (fact_id, kind, text): auditor 240 | Executor 240 | identical sequence True
    Executor train_Y template_id == <relation>.<kind>.1: True
  dev_qa (fact_id, template_id, question): auditor 320 | Executor 320 | identical sequence True
    Executor dev_qa template_id is a DEV template of the fact's relation: True
  general_dev (domain, source doc_id, ids): auditor 100 | Executor 100 | identical sequence True
  general_dev texts: auditor 100 | Executor 100 | identical sequence True
    general_dev n_w total: auditor 24877 | Executor 24877
  anchor_text (source row, ids): auditor 512 | Executor 512 | identical sequence True
  anchor_text texts: auditor 512 | Executor 512 | identical sequence True
```
第 C 节：gen4 的 8 个数据文件，字节就是规范形式（bytes are the canonical form True）。

**与 Executor 是否一致：一致**
- 内容序列完全相同。
- t2 报告中 gen4 各文件的 byte_sha256，等于我对 gen4 求得的值。

---
## 第 3 项：L1–L6 的 Gate 0 部分，与 gen4/leakage_report.json 逐项比对（第 18 号、第 21 号第 B 节）

**命令**
```
PY ia_07_leakage.py /home/user/OpenMythos $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2 $SP/gen4   -> 18_ia_leakage_gen4.txt
PY ia_12_r2_bytes.py /home/user/OpenMythos/metrix/e1-pilot/audit $SP/gen1 $SP/gen4 $SP/auditor_ia/out $SP/auditor_ia/out_r2   -> 21_ia_r2_bytes.txt
```

**原始输出（第 18 号摘录）**
```
{"L1": 0, "L1_shared": [], "L1_sets": {"TRAIN": 4, "DEV": 8, "TEST": 12, "Y": 8}, "L2": 0.2, "L2_pairs_at_max": [["capital.TRAIN.1", "capital.DEV.1"]], "L2_pairs": 368, "L2_both_empty": 4}
Executor anchor_text.jsonl: decode(ids) == text field for 512 of 512 | general_dev.jsonl: decode(ids) == text field for 100 of 100
  L3a/L3b/L4/L5/L6 (auditor data vs Executor files): all equal True; L6_anchor_word_13grams 44255, L6_window_word_13grams 17780, L6_token_id_shared 0
report: part gate0 | result PASS | frozen_commit 87a244db28a901f9e89282b50df76778ab5c2887
  L1 value 0 | L2 value 0.2, pair [['capital.TRAIN.1','capital.DEV.1']], n 4 | L3a 0 (strings 80) | L3b 0 (strings 120) | L4 0 (questions 320, part 'DEV') | L5 0 (learned 120, unread 40, strings 320) | L6 0 (anchor_documents 512, windows 100, n 13, examples [], token-id 0)
  （以上每一项，以及各项的 limit、within_limit、result、check keys：auditor | Executor report | equal True）
RESULT: PASS
```

**原始输出（第 21 号第 B 节摘录）**
```
gen1 sha256 6ea9c7ff...eac2 | gen4 sha256 6ea9c7ff...eac2 | byte-identical True | gen1 == round-1 record 6ea9c7ff...eac2 True
leaves 47 | not compared in ia_07: [('checks.L6.detail.part', 'DEV (anchor_text vs general_dev)')] | ia_07 comparisons without a leaf: []
checks.L6.detail.part names the Gate 0 part (anchor text vs general DEV windows, no TEST): True
```

**与 Executor 是否一致：一致**
- 报告共 47 个叶子字段，全部与我的值相等或已核对。
- ia_07 没有逐项比对的唯一字段是 L6.detail.part，已在第 21 号补查。

---
## 第 5 项：split（第 19 号）

**命令**
```
PY ia_09_split.py /home/user/OpenMythos $SP/auditor_ia/out_r2 $SP/gen4   -> 19_ia_split_gen4.txt
```

**原始输出**
```
[Executor] facts 160 distinct 160 | learned 120 unread 40 | learned & unread 0 | id format True | L/U letter, relation, stratum consistent True | 8 cells x (15 + 5) True | indices L01-15, U01-05 True
[Executor] TRAIN: train_F 120 | train_S 120 | train_Y 240 | unread fact_ids in TRAIN files [] | each learned fact once in F and S, once as S answer (same cell, not itself), twice in Y (Y_ENTITY + Y_ANSWER): True
[Executor] DEV: dev_qa 320 | every fact twice, once per DEV template of its relation: True | learned 240 unread 80
[Executor] candidates keys 160 == fact_ids True | general DEV windows 100 per domain {'books': 25, 'c4': 25, 'fineweb': 25, 'wikitext': 25} | anchor documents 512
Executor directory listing: [8 个数据文件 + leakage_report.json] | files with 'test' in the name: []
working-tree SPLIT_MANIFEST split_sha256: {... 'test_qa.jsonl': None}
RESULT: PASS
```
我自己的数据（[auditor] 行）结果相同。

**与 Executor 是否一致：一致**
- fact_id 互斥，各 split 数量符合协议 2.1、2.3、2.6、2.7 和冻结 manifest。
- 与 t2 报告的行数一致：160、120、120、240、320、160、100、512。

---
## 补充：候选可行性，对象 gen4（第 20 号；任务未要求，按定义第 3 项一并执行）

**命令**
```
PY ia_08_feasibility.py $SP/auditor_ia/dl/qwen_tok $SP/auditor_ia/out_r2 $SP/gen4   -> 20_ia_feasibility_gen4.txt
```

**原始输出**
```
minimum available candidates per fact (incl. the true answer): 5 | cells with available < 4: []
minimum distractor pool per fact: 4 | cells with pool < 4: []
Executor candidates.json: keys 160 | lists violating the four constraints [] (count 0) | position of the true answer {0: 41, 1: 38, 2: 45, 3: 36}
RESULT: PASS
```

**与 Executor 是否一致：一致**

---
## gen4 与 gen1 的 8 个数据文件是否逐字节相同（第 21 号第 A、C 节）

**原始输出**
```
  facts.jsonl: gen1 21489 bytes sha256 e05561ac... | gen4 21489 bytes sha256 e05561ac... | byte-identical True | gen1 == round-1 record ... True
  train_F.jsonl 3aa9ab3c... / train_S.jsonl 686fdd2f... / train_Y.jsonl c7430cad... / dev_qa.jsonl 9761eb60... / candidates.json e5d15c99... / general_dev.jsonl 95766692... / anchor_text.jsonl 2089e656...: byte-identical True, gen1 == round-1 record True
8 data files gen4 byte-identical to gen1: True
C. auditor regeneration round 2 vs round 1: 9 files, all byte-identical True
RESULT: PASS
```

**结论：8 个文件全部逐字节相同**
- gen1 自第 1 轮以来没有变化。
- leakage_report.json 也逐字节相同。
- 我第 2 轮重新生成的数据与第 1 轮逐字节相同。

---
## 说明
- `data-auditor` 的信任状态仍为「待验证」，按 metrix/CLAUDE.md 第 10 节，本 PASS 仅作参考。
- 我没有执行 Executor 的代码，所以不能直接证明 gen4 是由暂存代码生成的。能确认的是：暂存源码的哈希等于 gen4 生成前打印的哈希，文件时间顺序吻合，gen4 的内容与我独立复算的结果完全相同。

## 运行后 git status --short 的原始输出（也在 22_git_status_final_r2.txt；`git diff --stat` 输出为空）
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
A  metrix/e1-pilot/tests/test_environment.py
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
?? metrix/e1-pilot/audit/ia_11_r2_inputs.py
?? metrix/e1-pilot/audit/ia_12_r2_bytes.py
?? metrix/e1-pilot/audit/ia_common.py
?? metrix/e1-pilot/audit/ia_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_a/
```
暂存的 A 行与第 2 轮开始时相同。未跟踪的改动只在 metrix/e1-pilot/audit/ 下。

结论：PASS
