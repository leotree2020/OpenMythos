# data-auditor, round 2 (final) of the E1-V1 protocol authoring (staged tree f395c476606603e65d336e1ba3ac34a065c40889 = fix commit 266b64b7d8af07064b94de61b75f87723ad2d167)
# final report extracted unchanged from data-auditor_round2_transcript.jsonl by metrix/e1-pilot/reports/round6/review_extract.py (run, not modified)
---
# data-auditor 第 2 轮审计：E1-V1 协议修复（暂存树 f395c476606603e65d336e1ba3ac34a065c40889，HEAD 59761ad923674d43725167a8c79f6bdf16f531ee）

## 0. 前提、环境与范围

**定义文件**：我读了仓库中的 `.claude/agents/data-auditor.md`。它的 frontmatter tools 行是 `Read, Grep, Glob, Write, Bash`，和我已加载的定义一致，正文也相同。

**路径对应：接受，与第 1 轮相同。** 定义中的 `metrix/e1-pilot/audit/` 在本阶段对应 `metrix/e1-v1/audit/`。这一对应仍是交给 Review Gate 的待决事项。

**运行环境**：
- 主机 `vm`，Claude Code 云容器，只用 CPU，没有 GPU，没有安装 torch。
- Python 3.13.18，transformers 5.22.2，tokenizers 0.23.3，pyarrow 26.0.1，numpy 2.5.4。
- 全部用 `<S>/venv/bin/python -I -B` 运行，其中 `<S>` = /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad。
- 只加载了分词器（Qwen AutoTokenizer、parcae tokenizers.Tokenizer），没有加载任何模型权重。

**读了什么**：
- 协议、四个 JSON、SUBMISSION_NOTE。
- 交付物 diff，但没有打开其中三个 Executor .py 文件的 hunk（build_manifests.py、compute_estimate.py、sigma_planning.py，即 diff 第 498–635 行与第 688–714 行）。
- Executor 的输出文本 `reports/authoring/sigma_planning.txt`、`compute_estimate.txt`，只用于比对。
- 我第 1 轮的原文与脚本。
- Pilot 的 manifest 与 `metrix/e1-pilot/results/details/N_dev.json`。这是 split=dev 的结果文件，不是 TEST。
- Stage 1 README 的评测集表，只核对 c4 一行。
- git 元数据，用只读命令读取。

**没有 import、调用或复制 Executor 的代码。**

**TEST**：
- eval_sets.jsonl 只按行首字节用正则匹配。r2_item2 (d) 直接用了协议第 0 节写出的那条字节正则。test 行只解码捕获到的 domain、split 两个字段值，不解码其余内容，也不做 JSON 解析。
- MMLU、ARC 的 test parquet 只对整个文件求 sha256，并读文件尾的行数。
- 没有生成任何 TEST 文件。

**网络**：a7 重跑时向 Hugging Face Hub API 做了只读查询，与第 1 轮相同。

**需要说明的四件事**：
1. 本轮第一条命令里运行过一次 `git write-tree`，输出 f395c476…。如果这个树对象原本不在 `.git/objects` 中，会被写入一份。它不改动 index，也不改动工作区；其余 git 命令全部是只读的。
2. 我自己的两个脚本各有一处 bug，修好后重跑。两次首跑的输出都保留了，只是我自己的错误，不是发现：
   - `r2_item2_json.py`：检查 (f) 的文件名正则漏了大写字母，首跑因此出现 1 行 DIFF。
   - `r2_item4_fraction.py`：第 (5) 部分随机构造的 a_lo、a_hi 之间没有比较点。
3. r2_item1 的 stdout 中间夹了一条 transformers 的 warning（BPE 分词器忽略 `clean_up_tokenization_spaces=True`），是原样记录。
4. 第 1 轮的 `a6_consistency.py` 本轮没有重跑。它把第 1 轮的 HEAD、树 id 与第 1 轮 ARC 句子的正则写死了，对修改后的句子会直接报错。它的检查已改写进 `r2_item2_json.py`。

**本轮写入的文件**（全部在 `metrix/e1-v1/audit/` 下，第 1 轮的文件一个都没有改；`git diff --name-only` 为空）：
- 脚本：
  - /home/user/OpenMythos/metrix/e1-v1/audit/r2_item1_fixes.py
  - /home/user/OpenMythos/metrix/e1-v1/audit/r2_item2_json.py
  - /home/user/OpenMythos/metrix/e1-v1/audit/r2_item3_sigma.py
  - /home/user/OpenMythos/metrix/e1-v1/audit/r2_item4_fraction.py
- 完整 stdout：/home/user/OpenMythos/metrix/e1-v1/audit/stdout/ 下的 `*_round2.txt`（11 个）与 `*_round2_firstrun.txt`（2 个）。
- 临时数据（只有非 TEST 数据，**不入库**）：/home/user/OpenMythos/metrix/e1-v1/audit/tmpdata/v1data/，共 12 个文件。它们与 Executor 移出的第 1 轮副本逐字节相同。

| 文件 | sha256 |
|---|---|
| a1_hashes_round2.txt | 5c851563360427733a3de95147c7f157ef05dfc18db98f679c38cfbbd46e13cc |
| a2_leakage_round2.txt | 63c5c63850f4bb1f127884e6aa25772d5458138a6104a4eedba532eec9946a38 |
| a3_candidates_round2.txt | 06c6a9f1acc0cdbc2c846c4f25a7c6d11a7a7184280e35fcbc67c5d1c6fc3e5f |
| a4_split_round2.txt | bdf6b4ea2021a91bcecb6f43eb19c15398b8342bf0816b0a0c98e9b325c1803a |
| a5_damage_round2.txt | ea9c2091b0766e60a4c83a7df92158981768e6195758de75a285a96fbbb439ad |
| a7_hub_round2.txt | 66bc8d9ef5f9e0bcd3ed44616fd2642c029e179f6bcc833e4f3857b947b5344f |
| a8_d2_inputs_round2.txt | 357537bd3832b7cc11a69625559ebfce945c62e17f89beb729eefe2094a2f93b |
| r2_item1_fixes_round2.txt | 92091ca117334e7e25933a5f8c980c42fbc4b50b75bca914b0039355abedcbb0 |
| r2_item2_json_round2.txt | 59a24cf1ff93b3eb1a14eda6250db24860d9507e6a457f5b91766c350aa10682 |
| r2_item2_json_round2_firstrun.txt | 44350b2050edee984b0ba5d36cdce90c781ec78a29cfc3ae1b11b99beeac9a43 |
| r2_item3_sigma_round2.txt | 71c49fd322632f64168fbf8fa2d83170edbb0a2896bba4898d2efb3b83371d2c |
| r2_item4_fraction_round2.txt | 0f285c888023e0454f18e4abeabf908be65e3dc156d01ffa8b63f3a8e3a36642 |
| r2_item4_fraction_round2_firstrun.txt | 758900e5a263b2ab07721d912b64cd1d351f8a9e0b045e66627e19e4ab849ac2 |

每个脚本的运行方式：
`(echo "# host…"; echo "$ …"; <S>/venv/bin/python -I -B metrix/e1-v1/audit/<脚本>.py 2>&1; echo "exit=$?") > metrix/e1-v1/audit/stdout/<脚本>_round2.txt`

---

## 项目 1：B1、M2、M3、M4 是否已解决

### 1a. 第 1 轮脚本不改动，对修改后的 manifest 重跑

**命令**：按上面的方式依次重跑 a1_hashes、a5_damage、a2_leakage、a3_candidates、a4_split、a8_d2_inputs、a7_hub，然后执行：
```
diff <(tail -n +3 stdout/$s.txt) <(tail -n +3 stdout/${s}_round2.txt)
for f in tmpdata/v1data/*; do cmp -s $f <S>/auditor_tmpdata/tmpdata/v1data/$(basename $f) && echo "same …"; done
```

**原始输出**：
```
== a1_hashes: lines differing from round 1 (excluding header lines 1-2)
36c36
< V1 facts 320 | built in 0.5 s
---
> V1 facts 320 | built in 0.7 s
72c72
< elapsed 5.0 s
---
> elapsed 5.4 s
== a2_leakage: lines differing from round 1 (excluding header lines 1-2)
== a3_candidates: lines differing from round 1 (excluding header lines 1-2)
== a4_split: lines differing from round 1 (excluding header lines 1-2)
== a5_damage: lines differing from round 1 (excluding header lines 1-2)
== a7_hub: lines differing from round 1 (excluding header lines 1-2)
== a8_d2_inputs: lines differing from round 1 (excluding header lines 1-2)
```
```
same anchor_text.jsonl
same answer_token_counts.jsonl
same candidates.json
same d2_dev.jsonl
same d2_dev_arc.jsonl
same dev_qa.jsonl
same facts.jsonl
same general_dev.jsonl
same pilot_facts.jsonl
same train_F.jsonl
same train_S.jsonl
same train_Y.jsonl
```
```
a1_hashes        OK  26  DIFF 0  | ITEM1 (facts/templates/files part): ALL MATCH
a2_leakage       OK   9  DIFF 0  | ITEM2: ALL MATCH
a3_candidates    OK   0  DIFF 0  | ITEM3: OK
a4_split         OK  37  DIFF 0  | ITEM4: ALL MATCH
a5_damage        OK  40  DIFF 0  | ITEM5: ALL MATCH
a7_hub           OK  22  DIFF 0  | SUPPLEMENT: ALL MATCH
a8_d2_inputs     OK   0  DIFF 0  | SUPPLEMENT D2 inputs: done
a2_leakage_round2.txt:OK   L1: auditor 0 | SPLIT_MANIFEST authoring_result 0
a2_leakage_round2.txt:OK   L2: auditor 0.2 | SPLIT_MANIFEST authoring_result 0.2
a2_leakage_round2.txt:OK   L3a: auditor 0 | SPLIT_MANIFEST authoring_result 0
a2_leakage_round2.txt:OK   L3b: auditor 0 | SPLIT_MANIFEST authoring_result 0
a2_leakage_round2.txt:OK   L4: auditor 0 | SPLIT_MANIFEST authoring_result 0
a2_leakage_round2.txt:OK   L5: auditor 0 | SPLIT_MANIFEST authoring_result 0
a2_leakage_round2.txt:OK   L6: auditor {'d1_dev': 0, 'd1_dev_token_id_13grams_report_only': 0, 'd2_dev': 0, 'd2_dev_arc': 0} | SPLIT_MANIFEST authoring_result {'d1_dev': 0, 'd1_dev_token_id_13grams_report_only': 0, 'd2_dev': 0}
a2_leakage_round2.txt:OK   L7: auditor {'a': 0, 'b': 0, 'c': 0} | SPLIT_MANIFEST authoring_result {'a': 0, 'b': 0, 'c': 0}
a2_leakage_round2.txt:OK   L8: auditor {'d1_dev': 0, 'd2_dev': 0, 'd2_dev_arc': 0} | SPLIT_MANIFEST authoring_result {'d1_dev': 0, 'd2_dev': 0}
a3_candidates_round2.txt:minimum pool (other answers) over all 320 facts: 9 | minimum candidates incl. own answer: 10
a3_candidates_round2.txt:cells with a pool of other answers < 4 (protocol IMPLEMENTATION_FAIL rule; includes any cell with < 4 candidates): []
```

**结果**：修改后的 manifest 上，哈希、L1–L8 的 DEV 部分、候选可行性、split、损伤集的结果，与第 1 轮逐行相同，只有计时行不同。
- 候选池最小为 9，没有不足 4 个的 cell。
- fact_id 互斥，各 split 的数量符合协议。

### 1b. B1、M2、M3、M4 逐项核对

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/r2_item1_fixes.py`

**原始输出**（完整 stdout）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T10:04:32Z; round 2, staged tree f395c476606603e65d336e1ba3ac34a065c40889
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/r2_item1_fixes.py
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
=== B1: ARC DEV source numbers
OK   ARC ARC-Challenge/validation-00000-of-00001.parquet sha256: got 395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05 | expected 395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05
OK   ARC ARC-Easy/validation-00000-of-00001.parquet sha256: got ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74 | expected ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74
  ARC-Challenge/validation-00000-of-00001.parquet: rows 299 by number of options {3: 3, 4: 295, 5: 1}
  ARC-Easy/validation-00000-of-00001.parquet: rows 570 by number of options {3: 1, 4: 567, 5: 2}
  computed: DEV source rows 869, 4-option rows 862, other 7; shuffled order: visited 806 rows to reach 800 items, excluded 6; 4-option rows left after DEV 62; rows not visited 63
  protocol 7.1 sentence: 只用恰好 4 个选项的题(DEV 来源 869 行中 862 行为 4 个选项、7 行不是,`audit/stdout/a5_damage.txt`;撰写时按打乱顺序访问到第 806 行即凑满 800 题,其间排除 6 行)
OK   protocol 7.1 (source rows, 4-option, other, visited, items, excluded): got [869, 862, 7, 806, 800, 6] | expected [869, 862, 7, 806, 800, 6]
OK   cited file audit/stdout/a5_damage.txt contains the 869 / 862 line: got True | expected True
  protocol 15 sentence: ARC 的 DEV 来源只有 869 题(其中 862 题为 4 个选项),抽 800 题后只余 62 题
OK   protocol 15 (source rows, 4-option, drawn, left): got [869, 862, 800, 62] | expected [869, 862, 800, 62]
  SUBMISSION_NOTE sentence: 备选 ARC 800 题(按打乱顺序访问 806 行,其中 6 行因不是 4 个选项被排除;DEV 来源 869 行中共有 7 行不是 4 个选项
OK   SUBMISSION_NOTE (items, visited, excluded, source rows, other): got [800, 806, 6, 869, 7] | expected [800, 806, 6, 869, 7]
OK   DAMAGE_MANIFEST arc.authoring_dev.excluded.not_4_choices: got 6 | expected 6
OK   round-1 wrong numbers ('863', 'DEV 来源中 6 题', '余 63') left in protocol / SUBMISSION_NOTE: got [] | expected []
=== M2: L8 'text'
  SPLIT_MANIFEST L8.text: D1: the text field of the window (decode of the ids fed to the model, not the whole source document); D2: the prompt p
  protocol L8 row: | L8 | 损伤评测集中含 V1 字符串的单位数:一个 D1 窗口或一道 D2 题,只要其文本中出现 640 个 V1 字符串之一(不分大小写,且紧前、紧后的字符都不是 ASCII 字母或数字,或为文本边界)即计 1。“文本”:D1 窗口为送入模型的 id(最多 256 个)用本协议分词器解码所得的 `text` 字段(与 L6 相同,不是整篇源文档);D2 为题面 `p` | 0 | D1 DEV 0,D2 DEV 0 |
OK   protocol L8 row defines D1 text as the decoded <= 256 model ids (text field), not the source document; D2 = prompt p: got True | expected True
OK   SPLIT_MANIFEST L8.text says the same: got True | expected True
OK   DATA_MANIFEST general_dev record: text = tokenizer.decode(ids) with default arguments: got True | expected True
OK   V1 strings (distinct, lowercased): got 640 | expected 640
input qwen/tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 manifest aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 equal True
input qwen/tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 manifest d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True
input qwen/vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 manifest ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True
input qwen/merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 manifest 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True
OK   general_dev.jsonl (auditor) canonical sha256 = reference: got e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281 | expected e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281
OK   general_dev windows whose text != tokenizer.decode(ids): got 0 | expected 0
OK   general_dev windows with more than 256 ids: got 0 | expected 0
OK   L8 D1 DEV (window text field) = SPLIT authoring_result.d1_dev: got 0 | expected 0
OK   L8 D2 DEV MMLU (prompt p) = SPLIT authoring_result.d2_dev: got 0 | expected 0
OK   L8 D2 DEV ARC (prompt p), no manifest value, expected 0: got 0 | expected 0
  report only: L8 on the whole source document (reading excluded by the new text) D1 DEV 0; windows whose source document is longer than the window text 131 of 400
=== M3: L6 / L8 test_part
  SPLIT_MANIFEST L6.test_part.count: for each of general_test.jsonl and d2_test.jsonl separately: the word 13-grams of the 512 anchor documents merged into one set, those of all windows (D1) or all prompts (D2) of the file merged into another, 13-grams within each document, no concatenation across documents; the number of distinct elements of the intersection; texts = the decoded ids fed to the model (anchor <= 128 ids, window <= 256 ids) or the prompt p
  SPLIT_MANIFEST L8.test_part: as L6: counted for general_test.jsonl and d2_test.jsonl separately by Executor and data-auditor in section 10 step 10; must be equal
  protocol section 3 timing: **时机**:L1、L2 只用模板;L3a–L8 的 DEV 部分在第 10 节第 1 步运行(G0.1);L3a–L5 涉及 TEST 的部分在 `test_qa.jsonl` 生成之后运行;L6、L8 的 TEST 部分在 `general_test.jsonl`、`d2_test.jsonl` 生成之后、TEST 评测之前,由 Executor 与 data-auditor 各自计算,只输出计数,两者结果须一致(L6 的计数口径沿用 Pilot L6 的 TEST 部分,对 D1 TEST 与 D2 TEST 各自单独计数:锚文本的词 13-gram 集合分别与 `general_test.jsonl` 全部窗口、`d2_test.jsonl` 全部题面的词 13-gram 集合求交,各计交集的种类数;L8 对两个文件各计单位数);任一 TEST 部分超限或两者不一致 → ST10。
OK   L6 count: each file separately, anchor set vs the file's set, distinct elements of the intersection: got True | expected True
OK   L8 test_part: each file separately: got True | expected True
OK   protocol section 3 says the same (D1 TEST and D2 TEST counted separately; L8 per file): got True | expected True
OK   anchor_text.jsonl (auditor) canonical sha256 = reference: got 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5 | expected 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5
OK   anchor docs whose text != tokenizer.decode(ids): got 0 | expected 0
OK   anchor docs with more than 128 ids: got 0 | expected 0
OK   L6 count on general_dev.jsonl (DEV stand-in for general_test.jsonl) = authoring_result.d1_dev: got 0 | expected 0
OK   L6 count on d2_dev.jsonl MMLU (DEV stand-in for d2_test.jsonl) = authoring_result.d2_dev: got 0 | expected 0
OK   L6 count on d2_dev.jsonl ARC, no manifest value, expected 0: got 0 | expected 0
  report only: the other reading (D1 and D2 merged into one set) gives 0 on DEV; separate counts 0, 0
OK   count function on a constructed unit holding the first 13 words of anchor doc 0: got 1 | expected 1
OK   13-gram spanning the end of anchor doc 0 and the start of doc 1 is not an anchor 13-gram (no concatenation across documents): got 0 | expected 0
=== M4: DATA_MANIFEST files.*.record
  facts.jsonl: {fact_id, exposure ('learned' or 'unread'), relation, stratum ('natural' or 'random'), entity, answer}, generation order
  train_F.jsonl: {fact_id, template_id, text}, fact order
  train_S.jsonl: {fact_id, answer_fact_id, text} (Pilot 2.6)
  train_Y.jsonl: {fact_id, template_id, kind, text}; fact order, Y_ENTITY before Y_ANSWER
  dev_qa.jsonl: {fact_id, template_id, question}; fact order, then template order
  candidates.json: one JSON object {fact_id: [4 candidates]} (Pilot 2.5)
  anchor_text.jsonl: {doc: 0-based document number (anchor order), source_row: 0-based row index in the parquet file order, ids: the first at most 128 ids of encode(text, add_special_tokens=False), text: tokenizer.decode(ids) with default arguments}
  general_dev.jsonl: {domain, doc_id (of eval_sets.jsonl), ids: the first at most 256 ids fed to the model, text: tokenizer.decode(ids) with default arguments}
  d2_dev.jsonl: {item: 0-based position in the file, source_row: 0-based row index in the source list (MMLU: parquet row; ARC: index in Challenge then Easy), subject (MMLU subject; ARC item id), prompt: the D2 prompt p, answer: the correct letter}[transformers] Ignoring clean_up_tokenization_spaces=True for BPE tokenizer Qwen2Tokenizer. The clean_up_tokenization post-processing step is designed for WordPiece tokenizers and is destructive for BPE (it strips spaces before punctuation). Set clean_up_tokenization_spaces=False to suppress this warning, or set clean_up_tokenization_spaces_for_bpe_even_though_it_will_corrupt_output=True to force cleanup anyway.

  test_qa.jsonl: {fact_id, template_id, question}
  general_test.jsonl: as general_dev.jsonl
  d2_test.jsonl: as d2_dev.jsonl
OK   facts.jsonl built per record text = reference: got 4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9 | expected 4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9
OK   facts exposure values: got ['learned', 'unread'] | expected ['learned', 'unread']
OK   facts stratum values: got ['natural', 'random'] | expected ['natural', 'random']
OK   alternative reading exposure 'L'/'U' differs from reference: got True | expected True
OK   alternative reading stratum 'nat'/'rnd' differs from reference: got True | expected True
OK   train_F.jsonl (auditor) = reference: got fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511 | expected fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511
OK   train_S.jsonl (auditor) = reference: got 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6 | expected 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6
OK   train_Y.jsonl (auditor) = reference: got 82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b | expected 82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b
OK   dev_qa.jsonl (auditor) = reference: got 39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce | expected 39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce
OK   candidates.json (auditor) = reference: got 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3 | expected 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3
OK   anchor parquet sha256: got 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | expected 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22
OK   anchor_text.jsonl rebuilt per record text = reference: got 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5 | expected 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5
  anchor alternative 'doc 1-based': equal to reference False
  anchor alternative 'source_row = index among selected documents': equal to reference False
  anchor alternative 'source_row 1-based': equal to reference False
  anchor alternative 'ids = encode(text) with add_special_tokens=True': equal to reference True
  anchor alternative 'text = decode(ids, skip_special_tokens=True)': equal to reference True
  anchor alternative 'text = decode(ids, clean_up_tokenization_spaces=True)': equal to reference True
  general_dev alternative 'text = whole parcae-decoded document': equal to reference False
  general_dev alternative 'text = decode(ids, clean_up_tokenization_spaces=True)': equal to reference True
  general_dev alternative 'text = decode(ids, skip_special_tokens=True)': equal to reference True
  general_dev alternative 'ids = encode(document) with add_special_tokens=True, first 256': equal to reference True
OK   d2_dev MMLU (auditor) = reference: got f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be | expected f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be
OK   d2_dev ARC (auditor) = reference: got 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32 | expected 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32
OK   d2_dev item = 0-based position (MMLU, ARC): got (True, True) | expected (True, True)
OK   d2_dev MMLU subject = parquet subject of source_row: got True | expected True
OK   d2_dev ARC subject = item id of source_row (Challenge then Easy): got True | expected True
OK   d2_dev answer = correct letter (MMLU): got True | expected True
OK   d2_dev answer = correct letter (ARC): got True | expected True
  d2 alternative 'item 1-based' MMLU: equal to reference False
  d2 alternative 'ARC source_row = row within its own file': equal to reference False
  d2 alternative 'ARC subject = ARC-Challenge / ARC-Easy': equal to reference False
OK   TEST records defined by reference to the DEV records: got ('as general_dev.jsonl', 'as d2_dev.jsonl') | expected ('as general_dev.jsonl', 'as d2_dev.jsonl')
OK   ARC TEST order text: Challenge test then Easy test (so 'as d2_dev.jsonl' gives source_row = index in Challenge then Easy) | expected True
ITEM1 round 2: ALL MATCH
exit=0
```
（倒数第三行在文件中原文为 `OK   ARC TEST order text: Challenge test then Easy test (so 'as d2_dev.jsonl' gives source_row = index in Challenge then Easy): got True | expected True`；以 stdout 文件为准。）

**与 Executor 是否一致**：**一致**。逐项如下。

- **B1：已解决。**
  - 协议第 7.1 节的数字 869 / 862 / 7 / 806 / 800 / 6、第 15 节的 869 / 862 / 800 / 62、SUBMISSION_NOTE 的 800 / 806 / 6 / 869 / 7，全部与我从 ARC DEV 来源独立算出的值相同。
  - 第 1 轮的错误数字（863、「DEV 来源中 6 题」）在协议与 SUBMISSION_NOTE 中都已不存在。
  - 第 7.1 节引用的 `audit/stdout/a5_damage.txt` 确实含有 869 / 862 这一行。

- **M2：已解决。**
  - SPLIT_MANIFEST 的 `L8.text` 与协议 L8 一行把 D1 的「文本」定为 `text` 字段，即送入模型的最多 256 个 id 的解码，不是整篇源文档；D2 为题面 p。
  - 这与我的实现一致。L8 在 D1 DEV、MMLU DEV、ARC DEV 上都是 0。
  - 被排除的另一种读法（整篇源文档）在 DEV 上也是 0；400 个窗口中有 131 个的源文档长于窗口。

- **M3：已解决。**
  - L6 的 `test_part.count`、L8 的 `test_part` 与协议第 3 节「时机」三处文字一致：D1 TEST 与 D2 TEST 各自单独计数，13-gram 在每篇文档内取。
  - 我按新文字写的计数函数，用于 DEV 文件时得到 0 / 0 / 0，与 authoring_result 相同。
  - 正例自检：构造的单元计 1；跨文档拼接出的 13-gram 不计入。
  - 合并计数的读法在 DEV 上同样为 0。

- **M4：已解决。**
  - 按新的 record 文字构建的 facts、anchor_text、general_dev、d2_dev（MMLU 与 ARC）全部等于参考哈希。
  - 新文字点名的取值是有区分力的：doc 改从 1 开始，source_row 改为在入选文档中的序号或改从 1 开始，text 改为整篇文档，item 改从 1 开始，ARC 的 source_row 改为文件内行号，ARC 的 subject 改为 Challenge / Easy，exposure 写 L / U，stratum 写 nat / rnd——每一种读法都会改变哈希。
  - 文字没有固定的「默认参数」细节，对哈希没有影响：`add_special_tokens=True`、`skip_special_tokens=True` 得到相同的哈希；`clean_up_tokenization_spaces=True` 在 transformers 5.22.2 中被忽略。
  - TEST 文件的 record 写为「as general_dev / as d2_dev」，与 DAMAGE_MANIFEST 的 ARC test_order（Challenge test 之后接 Easy test）一致。

- 影响（B1、M2、M3、M4 各项，修改后）：数据否，指标否，门槛否，可复现性改善，iso 否，损伤测量否。

---

## 项目 2：四个 JSON 中与数据有关的内容，以及删去占位字段后是否丢失信息

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/r2_item2_json.py`（修好我自己的正则后第二次运行；第一次运行见 `r2_item2_json_round2_firstrun.txt`）

**原始输出**（完整 stdout）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T10:07:46Z; round 2, staged tree f395c476606603e65d336e1ba3ac34a065c40889; second run after fixing the auditor's own filename regex ([a-z] -> [A-Za-z]) in check (f) 'protocol 2.8 lists 9 non-TEST files'; first run kept as r2_item2_json_round2_firstrun.txt
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/r2_item2_json.py
=== (a) leaf diff HEAD (tree 0e3dc49e) -> index (tree f395c476)
OK   DATA_MANIFEST.json: working tree parses equal to index: got True | expected True
  DATA_MANIFEST.json: leaves HEAD 320 index 284 | removed 36 added 0 changed 6
    removed files.facts.jsonl.status = "NOT_GENERATED"
    removed files.facts.jsonl.byte_sha256 = null
    removed files.facts.jsonl.canonical_sha256 = null
    removed files.train_F.jsonl.status = "NOT_GENERATED"
    removed files.train_F.jsonl.byte_sha256 = null
    removed files.train_F.jsonl.canonical_sha256 = null
    removed files.train_S.jsonl.status = "NOT_GENERATED"
    removed files.train_S.jsonl.byte_sha256 = null
    removed files.train_S.jsonl.canonical_sha256 = null
    removed files.train_Y.jsonl.status = "NOT_GENERATED"
    removed files.train_Y.jsonl.byte_sha256 = null
    removed files.train_Y.jsonl.canonical_sha256 = null
    removed files.dev_qa.jsonl.status = "NOT_GENERATED"
    removed files.dev_qa.jsonl.byte_sha256 = null
    removed files.dev_qa.jsonl.canonical_sha256 = null
    removed files.candidates.json.status = "NOT_GENERATED"
    removed files.candidates.json.byte_sha256 = null
    removed files.candidates.json.canonical_sha256 = null
    removed files.anchor_text.jsonl.status = "NOT_GENERATED"
    removed files.anchor_text.jsonl.byte_sha256 = null
    removed files.anchor_text.jsonl.canonical_sha256 = null
    removed files.general_dev.jsonl.status = "NOT_GENERATED"
    removed files.general_dev.jsonl.byte_sha256 = null
    removed files.general_dev.jsonl.canonical_sha256 = null
    removed files.d2_dev.jsonl.status = "NOT_GENERATED"
    removed files.d2_dev.jsonl.byte_sha256 = null
    removed files.d2_dev.jsonl.canonical_sha256 = null
    removed files.test_qa.jsonl.status = "NOT_GENERATED"
    removed files.test_qa.jsonl.byte_sha256 = null
    removed files.test_qa.jsonl.canonical_sha256 = null
    removed files.general_test.jsonl.status = "NOT_GENERATED"
    removed files.general_test.jsonl.byte_sha256 = null
    removed files.general_test.jsonl.canonical_sha256 = null
    removed files.d2_test.jsonl.status = "NOT_GENERATED"
    removed files.d2_test.jsonl.byte_sha256 = null
    removed files.d2_test.jsonl.canonical_sha256 = null
    changed files.facts.jsonl.record: "{fact_id, exposure, relation, stratum, entity, answer}, generation order" -> "{fact_id, exposure ('learned' or 'unread'), relation, stratum ('natural' or 'random'), entity, answer}, gener…
    changed files.anchor_text.jsonl.record: "{doc, source_row, ids, text}" -> "{doc: 0-based document number (anchor order), source_row: 0-based row index in the parquet file order, ids: t…
    changed files.general_dev.jsonl.record: "{domain, doc_id, ids, text}" -> "{domain, doc_id (of eval_sets.jsonl), ids: the first at most 256 ids fed to the model, text: tokenizer.decode…
    changed files.d2_dev.jsonl.record: "{item, source_row, subject, prompt, answer}" -> "{item: 0-based position in the file, source_row: 0-based row index in the source list (MMLU: parquet row; ARC…
    changed files.general_test.jsonl.record: "{domain, doc_id, ids, text}" -> "as general_dev.jsonl"
    changed files.d2_test.jsonl.record: "{item, source_row, subject, prompt, answer}" -> "as d2_dev.jsonl"
OK   DATA_MANIFEST.json: every numeric leaf unchanged: got True | expected True
OK   SPLIT_MANIFEST.json: working tree parses equal to index: got True | expected True
  SPLIT_MANIFEST.json: leaves HEAD 321 index 318 | removed 5 added 2 changed 2
    removed split_sha256.train_F.jsonl = null
    removed split_sha256.train_S.jsonl = null
    removed split_sha256.train_Y.jsonl = null
    removed split_sha256.dev_qa.jsonl = null
    removed split_sha256.test_qa.jsonl = null
    added   leakage_checks.L8_fictional_strings_in_damage_sets.text = "D1: the text field of the window (decode of the ids fed to the model, not the whole source document); D2: the prompt p"
    added   actual_hashes = "the manifests are not rewritten during execution; the actual hashes of generated files go into results/step1_record.json (non-TEST) and results/st10_…
    changed leakage_checks.L6_anchor_ngram.test_part.count: "number of distinct shared word 13-grams across all documents: 13-grams are taken within each document (each a… -> "for each of general_test.jsonl and d2_test.jsonl separately: the word 13-grams of the 512 anchor documents me…
    changed leakage_checks.L8_fictional_strings_in_damage_sets.test_part: "as L6: counted by Executor and data-auditor in section 10 step 10; must be equal" -> "as L6: counted for general_test.jsonl and d2_test.jsonl separately by Executor and data-auditor in section 10…
OK   SPLIT_MANIFEST.json: every numeric leaf unchanged: got True | expected True
OK   DOSE_SPACE.json: working tree parses equal to index: got True | expected True
  DOSE_SPACE.json: leaves HEAD 146 index 146 | removed 0 added 0 changed 1
    changed training_contract.st11_bound: "0.875 * gpu_hours_limit" -> "0.875 * gpu_hours_limit; estimate E by the formula of protocol section 12 (replaces interpretation B17)"
OK   DOSE_SPACE.json: every numeric leaf unchanged: got True | expected True
OK   DAMAGE_MANIFEST.json: working tree parses equal to index: got True | expected True
  DAMAGE_MANIFEST.json: leaves HEAD 130 index 131 | removed 0 added 1 changed 5
    added   gate_d.G-D2.planning = "reports/authoring/sigma_planning.txt (expected m: D1-all 0.045, D1-diff 0.052, D1-same 0.090)"
    changed d1.reading_rule: "test rows are matched on the row-prefix bytes only until section 10 step 10 (protocol section 0)" -> "before section 10 step 10: whole-file sha256 allowed; test rows are only matched on the row-prefix bytes (the…
    changed d2.reading_rule: "before section 10 step 10 only the parquet footer (row count) of a TEST source is read (protocol section 0)" -> "before section 10 step 10: whole-file sha256 of a TEST source allowed; only the parquet footer (row count) is…
    changed gate_d.G-D2.rule: "sigma_N(D1-all), sigma_N(D1-diff), sigma_N(D1-same), sigma_N(D2) finite and > 0" -> "sigma_N(D1-all), sigma_N(D1-diff), sigma_N(D1-same), sigma_N(D2) finite and > 0; m(D1-all) <= 0.10, m(D1-diff…
    changed comparison.secondary: "all other points, metrics, DEV comparisons and per-method damages: 95% CI, words marked secondary" -> "all other points, metrics, DEV comparisons, per-domain metrics D1-books, D1-c4, D1-wikitext and per-method da…
    changed comparison.words: "superior: hi < 0 and all 3 seed estimates < 0; non-inferior: not superior, hi < m and all 3 seed estimates < … -> "for a comparison on metric M with m = m(M): superior: hi < 0 and all 3 seed estimates < 0; non-inferior: not …
OK   DAMAGE_MANIFEST.json: every numeric leaf unchanged: got True | expected True
OK   64-hex values (path, value) changed between HEAD and index: got [] | expected []
OK   removed leaves whose value is not null / 'NOT_GENERATED': got [] | expected []
  removed leaves by (file, field, value): {('DATA_MANIFEST.json', 'status', 'NOT_GENERATED'): 12, ('DATA_MANIFEST.json', 'byte_sha256', None): 12, ('DATA_MANIFEST.json', 'canonical_sha256', None): 12, ('SPLIT_MANIFEST.json', 'split_sha256.*', None): 5}
=== (b) every 64-hex value vs the auditor's own computation
  64-hex occurrences in the four JSON files: 65 | distinct 59
    DATA_MANIFEST.json:model.tokenizer.files_sha256.tokenizer.json aeb13307a71acd8f… = auditor ['file qwen/tokenizer.json']
    DATA_MANIFEST.json:model.tokenizer.files_sha256.tokenizer_config.json d5d09f07b48c3086… = auditor ['file qwen/tokenizer_config.json']
    DATA_MANIFEST.json:model.tokenizer.files_sha256.vocab.json ca10d7e9fb3ed185… = auditor ['file qwen/vocab.json']
    DATA_MANIFEST.json:model.tokenizer.files_sha256.merges.txt 8831e4f1a0444713… = auditor ['file qwen/merges.txt']
    DATA_MANIFEST.json:name_generation.expected_facts_canonical_sha256 0fc5ad819500e8a9… = auditor ['V1 facts list (canonical JSON list)']
    DATA_MANIFEST.json:name_generation.preseed.pilot_facts_canonical_sha256 406c8801c5b69ed2… = auditor ['Pilot facts list (canonical JSON list, DATA_SEED 20261110)']
    DATA_MANIFEST.json:s_permutation.expected_train_S_canonical_sha256 7ac254f6e87e017e… = auditor ['train_S.jsonl']
    DATA_MANIFEST.json:anchor_text.source 6a3450ea745ee6b6… = auditor ['file anchor parquet']
    DATA_MANIFEST.json:anchor_text.decoded_texts_canonical_sha256 8828bc4fcc5a3552… = auditor ['anchor decoded texts (canonical JSON list)']
    DATA_MANIFEST.json:anchor_text.file_canonical_sha256_authoring 2089e656819d1fe0… = auditor ['anchor_text.jsonl']
    DATA_MANIFEST.json:files.facts.jsonl.reference_canonical_sha256 4eeee6d198dede28… = auditor ['facts.jsonl']
    DATA_MANIFEST.json:files.train_F.jsonl.reference_canonical_sha256 fb1d80064c4c7796… = auditor ['train_F.jsonl']
    DATA_MANIFEST.json:files.train_S.jsonl.reference_canonical_sha256 7ac254f6e87e017e… = auditor ['train_S.jsonl']
    DATA_MANIFEST.json:files.train_Y.jsonl.reference_canonical_sha256 82314e6b4a5917d0… = auditor ['train_Y.jsonl']
    DATA_MANIFEST.json:files.dev_qa.jsonl.reference_canonical_sha256 39ea5ea1ff730cbc… = auditor ['dev_qa.jsonl']
    DATA_MANIFEST.json:files.candidates.json.reference_canonical_sha256 79600769eef1876b… = auditor ['candidates.json']
    DATA_MANIFEST.json:files.anchor_text.jsonl.reference_canonical_sha256 2089e656819d1fe0… = auditor ['anchor_text.jsonl']
    DATA_MANIFEST.json:files.general_dev.jsonl.reference_canonical_sha256 e8350160464963e6… = auditor ['general_dev.jsonl']
    DATA_MANIFEST.json:files.d2_dev.jsonl.reference_canonical_sha256.mmlu f40c146a3da500f1… = auditor ['d2_dev.jsonl MMLU']
    DATA_MANIFEST.json:files.d2_dev.jsonl.reference_canonical_sha256.arc 1ea77c8adeb84b6d… = auditor ['d2_dev.jsonl ARC']
    SPLIT_MANIFEST.json:template_freeze.template_set_sha256 2b52411326c218e9… = auditor ['template set']
    SPLIT_MANIFEST.json:candidates.candidate_mapping_sha256 79600769eef1876b… = auditor ['candidates.json']
    DAMAGE_MANIFEST.json:d1.source_file_sha256 8816fe5a39d8b89e… = auditor ['file eval_sets.jsonl (whole file)']
    DAMAGE_MANIFEST.json:d1.decode_tokenizer_json_sha256 e0021e26057088d6… = auditor ['file parcae tokenizer.json']
    DAMAGE_MANIFEST.json:d1.dev.authoring.canonical_sha256 e8350160464963e6… = auditor ['general_dev.jsonl']
    DAMAGE_MANIFEST.json:d2.datasets.mmlu.dev_source.sha256 66cdf0b090ccb657… = auditor ['file MMLU all/validation']
    DAMAGE_MANIFEST.json:d2.datasets.mmlu.test_source.sha256 74a41822ce7d3def… = auditor ['file MMLU all/test (whole file)']
    DAMAGE_MANIFEST.json:d2.datasets.mmlu.authoring_dev.canonical_sha256 f40c146a3da500f1… = auditor ['d2_dev.jsonl MMLU']
    DAMAGE_MANIFEST.json:d2.datasets.arc.dev_source[0].sha256 395a5c88d1580d69… = auditor ['file ARC ARC-Challenge/validation']
    DAMAGE_MANIFEST.json:d2.datasets.arc.dev_source[1].sha256 ed890ff1e4cef7a7… = auditor ['file ARC ARC-Easy/validation']
    DAMAGE_MANIFEST.json:d2.datasets.arc.test_source[0].sha256 62f03257e737aed2… = auditor ['file ARC ARC-Challenge/test']
    DAMAGE_MANIFEST.json:d2.datasets.arc.test_source[1].sha256 4160597d618ae851… = auditor ['file ARC ARC-Easy/test']
    DAMAGE_MANIFEST.json:d2.datasets.arc.authoring_dev.canonical_sha256 1ea77c8adeb84b6d… = auditor ['d2_dev.jsonl ARC']
    templates[*].normalized_sha256: 32 occurrences, all equal to the auditor's value: True
OK   64-hex values in the JSON files not equal to an auditor-computed value: got [] | expected []
OK   fields of a known meaning (32) whose value differs from the auditor's value of that meaning: got [] | expected []
    embedded in text (not a hash field): DATA_MANIFEST.json:anchor_text.source 6a3450ea745ee6b6… = ['file anchor parquet']
OK   TEST reference hashes (test_qa, general_test, d2_test) are null: got [None, None, None] | expected [None, None, None]
OK   64-hex values in the protocol (12) not equal to an auditor-computed value: got [] | expected []
    protocol 0fc5ad819500e8a9… = auditor ['V1 facts list (canonical JSON list)']
    protocol 1ea77c8adeb84b6d… = auditor ['d2_dev.jsonl ARC']
    protocol 2b52411326c218e9… = auditor ['template set']
    protocol 406c8801c5b69ed2… = auditor ['Pilot facts list (canonical JSON list, DATA_SEED 20261110)']
    protocol 66cdf0b090ccb657… = auditor ['file MMLU all/validation']
    protocol 74a41822ce7d3def… = auditor ['file MMLU all/test (whole file)']
    protocol 79600769eef1876b… = auditor ['candidates.json']
    protocol 7ac254f6e87e017e… = auditor ['train_S.jsonl']
    protocol 82314e6b4a5917d0… = auditor ['train_Y.jsonl']
    protocol 8828bc4fcc5a3552… = auditor ['anchor decoded texts (canonical JSON list)']
    protocol e8350160464963e6… = auditor ['general_dev.jsonl']
    protocol f40c146a3da500f1… = auditor ['d2_dev.jsonl MMLU']
=== (c) seeds, counts, rule text
OK   DATA_SEED protocol section 0 vs DATA_MANIFEST: got 20261128 | expected 20261128
OK   CANDIDATE_SEED protocol section 0 vs DATA_MANIFEST: got 20261129 | expected 20261129
OK   BOOTSTRAP_SEED protocol section 0 vs DATA_MANIFEST: got 20261130 | expected 20261130
OK   seed assignments in the protocol differing from DATA_MANIFEST outside the Pilot regeneration sentence: got [] | expected []
  seed assignments differing from DATA_MANIFEST (Pilot regeneration only): [(66, 'DATA_SEED', 20261110)]
OK   TRAIN_SEEDS protocol / DATA_MANIFEST / DOSE_SPACE / Z0 / P+: got (True, [101, 202, 303], [101, 202, 303], [101, 202, 303], [101, 202, 303]) | expected (True, [101, 202, 303], [101, 202, 303], [101, 202, 303], [101, 202, 303])
OK   DAMAGE_MANIFEST bootstrap seed / SPLIT_MANIFEST candidate seed text: got ('BOOTSTRAP_SEED = 20261130', 'CANDIDATE_SEED = 20261129') | expected ('BOOTSTRAP_SEED = 20261130', 'CANDIDATE_SEED = 20261129')
OK   name_generation rule fields equal to Pilot: got [] | expected []
OK   s_permutation rule = Pilot with 15 -> 30: got per cell, a derangement of the 30 learned answers drawn with rng_rule(DATA_SEED, 's-permutation:<relation>:<stratum>'); redraw until no fixed point | expected per cell, a derangement of the 30 learned answers drawn with rng_rule(DATA_SEED, 's-permutation:<relation>:<stratum>'); redraw until no fixed point
OK   templates identical to Pilot: got True | expected True
OK   candidates.way identical to Pilot: got True | expected True
OK   candidates.pool identical to Pilot: got True | expected True
OK   candidates.draw identical to Pilot: got True | expected True
OK   candidates.shared_by identical to Pilot: got True | expected True
OK   candidates.duplicates identical to Pilot: got True | expected True
OK   candidates.pool_too_small identical to Pilot: got True | expected True
OK   candidates.exposure_matching identical to Pilot: got True | expected True
OK   hashing rules identical to Pilot (both manifests): got True | expected True
OK   anchor_text.source identical to Pilot: got True | expected True
OK   anchor_text.selection identical to Pilot: got True | expected True
OK   anchor_text.truncate_to_model_tokens identical to Pilot: got True | expected True
OK   anchor_text.document_rule identical to Pilot: got True | expected True
OK   anchor_text.decoded_texts_canonical_sha256 identical to Pilot: got True | expected True
OK   D1 source_file identical to Pilot general_text: got True | expected True
OK   D1 source_file_sha256 identical to Pilot general_text: got True | expected True
OK   D1 decode_with identical to Pilot general_text: got True | expected True
OK   D1 decode_tokenizer_json_sha256 identical to Pilot general_text: got True | expected True
OK   D1 window_rule identical to Pilot general_text: got True | expected True
OK   facts counts (total, learned, unread, per cell): got (320, 240, 80, 30, 10) | expected (320, 240, 80, 30, 10)
OK   protocol counts 320 = 240 + 80, 30 + 10, pool 29 / 9, Y 480: got (True, True, True, True) | expected (True, True, True, True)
OK   pool sizes SPLIT_MANIFEST: got {'learned': 29, 'unread': 9} | expected {'learned': 29, 'unread': 9}
OK   Y/F authoring numbers protocol / DATA_MANIFEST: got (True, {'F_tokens': 3802, 'Y_tokens': 4541, 'ratio': 1.1944}) | expected (True, {'F_tokens': 3802, 'Y_tokens': 4541, 'ratio': 1.1944})
OK   D1 DEV 400 / D2 DEV 800 / D1 TEST 175 per domain (protocol vs DAMAGE_MANIFEST): got (True, True, True, 400, 800, 175) | expected (True, True, True, 400, 800, 175)
OK   MMLU / ARC source rows (protocol vs DAMAGE_MANIFEST): got (True, [1531, 14042, 299, 570, 1172, 2376]) | expected (True, [1531, 14042, 299, 570, 1172, 2376])
OK   ARC dev_order / test_order index ranges = rows - 1: got (True, True) | expected (True, True)
OK   MMLU dev_order / test_order list lengths: got (True, True) | expected (True, True)
OK   letter ids / prompt instruction (protocol vs DAMAGE_MANIFEST): got (True, {'A': 362, 'B': 425, 'C': 356, 'D': 422}, True, True) | expected (True, {'A': 362, 'B': 425, 'C': 356, 'D': 422}, True, True)
OK   dose ladder (protocol 6.3 vs DOSE_SPACE; steps = 30 x passes): got (True, [1, 2, 3, 4, 6, 8, 11, 16, 23, 32], True, 11) | expected (True, [1, 2, 3, 4, 6, 8, 11, 16, 23, 32], True, 11)
OK   iso parameters DOSE_SPACE (targets, tau_dev, tau_test) vs protocol 6.2 / 6.4 / 6.5: got ([0.7, 0.8, 0.9], 0.1, 0.05, True, True, True) | expected ([0.7, 0.8, 0.9], 0.1, 0.05, True, True, True)
OK   DOSE_SPACE checkpoint_retention.rule = protocol 6.7 condition: got (True, True) | expected (True, True)
  report only: DOSE_SPACE iso has no field for the exact arithmetic of protocol 6.4 item 2a: []
=== (d) reading rules
  DAMAGE d1.reading_rule: before section 10 step 10: whole-file sha256 allowed; test rows are only matched on the row-prefix bytes (the regex of protocol section 0) and counted, never decoded or JSON-parsed
  DAMAGE d2.reading_rule: before section 10 step 10: whole-file sha256 of a TEST source allowed; only the parquet footer (row count) is read; no row is read or decoded (protocol section 0)
OK   protocol section 0 allows exactly: whole-file sha256; eval_sets row-prefix match + count; parquet footer row count: got True | expected True
OK   DAMAGE d1.reading_rule matches (sha256 allowed; prefix bytes only; counted; never decoded or parsed): got True | expected True
OK   DAMAGE d2.reading_rule matches (sha256 allowed; parquet footer only; no row read or decoded): got True | expected True
  protocol regex (literal): ^\{"domain": "([^"\\]*)", "split": "([^"\\]*)", 
  eval_sets.jsonl lines 1200 | protocol-regex counts {('books', 'dev'): 100, ('books', 'test'): 200, ('c4', 'dev'): 100, ('c4', 'test'): 200, ('fineweb', 'dev'): 100, ('fineweb', 'test'): 200, ('wikitext', 'dev'): 100, ('wikitext', 'test'): 200}
OK   lines where the protocol regex and the round-1 auditor regex capture different (domain, split): got 0 | expected 0
OK   lines not matched by the protocol regex: got 0 | expected 0
OK   per (domain, split) counts protocol regex = round-1 regex: got {('fineweb', 'dev'): 100, ('c4', 'dev'): 100, ('wikitext', 'dev'): 100, ('books', 'dev'): 100, ('fineweb', 'test'): 200, ('c4', 'test'): 200, ('wikitext', 'test'): 200, ('books', 'test'): 200} | expected {('fineweb', 'dev'): 100, ('c4', 'dev'): 100, ('wikitext', 'dev'): 100, ('books', 'dev'): 100, ('fineweb', 'test'): 200, ('c4', 'test'): 200, ('wikitext', 'test'): 200, ('books', 'test'): 200}
OK   test rows per domain after skipping 25 (protocol regex): got {'books': 175, 'c4': 175, 'fineweb': 175, 'wikitext': 175} | expected {'books': 175, 'c4': 175, 'fineweb': 175, 'wikitext': 175}
=== (e) G-D2 bounds
  protocol G-D2 row: | G-D2 噪声基线 | `σ_N(M)` = N 在 M 的 DEV 集上的水平统计量的 bootstrap 标准差(10,000 次,第 8 节):M = `D1-all`(4 领域分层的窗口 NLL 均值的平均)、`D1-diff`(3 领域)、`D1-same`(fineweb)、`D2`(`Acc_D2(N)`)。四个值都必须有限且 > 0;并且由它们按第 7.6 节算出的 `m(D1-all)`、`m(D1-diff)` ≤ 0.10,`m(D1-same)` ≤ 0.20(`m(D2)` 由题数决定,最大为 2 × sqrt(0.25/800) ≈ 0.035,不另设上界)。训练种子之间的波动:P+ 三个种子的 `D1-diff`、`D2` 的样本标准差只报告;Gate M 用“每个种子的点估计同向”的要求处理种子波动(第 9.4 节) |
  DAMAGE G-D2: {'rule': 'sigma_N(D1-all), sigma_N(D1-diff), sigma_N(D1-same), sigma_N(D2) finite and > 0; m(D1-all) <= 0.10, m(D1-diff) <= 0.10, m(D1-same) <= 0.20 (m(D2) <= 2 * sqrt(0.25 / 800) by construction, no bound); P+ seed SD of D1-diff and D2 reported', 'planning': 'reports/authoring/sigma_planning.txt (expected m: D1-all 0.045, D1-diff 0.052, D1-same 0.090)'}
OK   bounds protocol (D1-all, D1-diff, D1-same) = DAMAGE_MANIFEST: got (0.1, 0.1, 0.2) | expected (0.1, 0.1, 0.2)
  2 * sqrt(0.25 / 800) = 0.035355; sqrt(0.25 / 800) = 0.017678
OK   protocol '2 × sqrt(0.25/800) ≈ 0.035' and DAMAGE '2 * sqrt(0.25 / 800)': got (True, True, 0.035) | expected (True, True, 0.035)
OK   G-D2 planning numbers protocol 7.5 vs DAMAGE planning: got (True, True) | expected (True, True)
OK   sigma_N definition: sample SD (B - 1) of 10,000 bootstrap values; m = 2 sigma_N: got (10000, True, 2) | expected (10000, True, 2)
  report only: Acc_D2(N) = 0.5 (worst case), 20 simulated 10,000-replicate bootstraps: sigma min 0.017327 max 0.018001; above sqrt(0.25/800) in 7 of 20 (2 sigma max 0.036003)
=== (f) removed placeholder fields: information lost?
OK   old files.*.{status, byte_sha256, canonical_sha256} were all NOT_GENERATED / null / null: got True | expected True
OK   old SPLIT_MANIFEST.split_sha256 values: got {'train_F.jsonl': None, 'train_S.jsonl': None, 'train_Y.jsonl': None, 'dev_qa.jsonl': None, 'test_qa.jsonl': None} | expected {'train_F.jsonl': None, 'train_S.jsonl': None, 'train_Y.jsonl': None, 'dev_qa.jsonl': None, 'test_qa.jsonl': None}
OK   files kept (same 12 entries): got ['facts.jsonl', 'train_F.jsonl', 'train_S.jsonl', 'train_Y.jsonl', 'dev_qa.jsonl', 'candidates.json', 'anchor_text.jsonl', 'general_dev.jsonl', 'd2_dev.jsonl', 'test_qa.jsonl', 'general_test.jsonl', 'd2_test.jsonl'] | expected ['facts.jsonl', 'train_F.jsonl', 'train_S.jsonl', 'train_Y.jsonl', 'dev_qa.jsonl', 'candidates.json', 'anchor_text.jsonl', 'general_dev.jsonl', 'd2_dev.jsonl', 'test_qa.jsonl', 'general_test.jsonl', 'd2_test.jsonl']
OK   every file entry keeps content / reference_canonical_sha256 / canonical_check, values unchanged: got True | expected True
OK   TEST entries keep generation_allowed unchanged: got True | expected True
OK   every split_sha256 file still has a reference hash (non-TEST) or an st10_record rule (TEST) in DATA_MANIFEST files: got [] | expected []
OK   where actual hashes go: step1_record (9 non-TEST files) and st10_record (TEST file sha256) in reported_values; SPLIT actual_hashes: got (True, True, True) | expected (True, True, True)
OK   protocol 2.8 lists 9 non-TEST files: got 9 | expected 9
OK   hashing definitions of byte_sha256 / canonical_sha256 still in both manifests: got (True, True) | expected (True, True)
OK   remaining references to split_sha256 / NOT_GENERATED in protocol and JSON files: got [] | expected []
OK   ST12: manifests not rewritten during execution; actual hashes go to results records: got (True, True) | expected (True, True)
=== (g) provenance (read-only git commands)
OK   HEAD: got 59761ad923674d43725167a8c79f6bdf16f531ee | expected 59761ad923674d43725167a8c79f6bdf16f531ee
OK   HEAD tree = round-1 staged tree: got 0e3dc49eaca9b07254e61301bc2602f8d8a39eea | expected 0e3dc49eaca9b07254e61301bc2602f8d8a39eea
OK   branch: got metrix-e1-v1-protocol-v1 | expected metrix-e1-v1-protocol-v1
OK   index entries equal tree f395c476… (git ls-files -s vs git ls-tree -r): got True | expected True
OK   unstaged changes to tracked files (git diff --name-only): got [] | expected []
OK   staged changes outside metrix/e1-v1/: got [] | expected []
OK   deliverable diff: per-file hunks equal to 'git diff --cached HEAD -- <file>' (11 files): got [] | expected []
ITEM2 round 2: ALL MATCH
exit=0
```
（第一次运行与此只差两行：`DIFF protocol 2.8 lists 9 non-TEST files: got 6 | expected 9` 与 `ITEM2 round 2: MISMATCH PRESENT`。原因是我自己的正则 `[a-z0-9_]` 漏掉了 train_F、train_S、train_Y 中的大写字母。）

**与 Executor 是否一致**：**一致**。

- **种子**：20261128 / 20261129 / 20261130 / [101, 202, 303] 在协议与各 JSON 中一致。协议中唯一不同的 20261110 出现在重新生成 Pilot fact 的那一句，属于正当用法。
- **数量与规则文字**：与第 1 轮相同。四个 JSON 中的数值叶子全部未变。
- **参考哈希**：JSON 中 65 处、59 个不同的 64-hex 值，全部等于我自己独立算出、含义相同的值（32 个有固定含义的字段逐一核对）；协议中的 12 个也全部相同。HEAD 与暂存树之间没有任何哈希改变。
- **读取规则**：DAMAGE_MANIFEST 的 d1、d2 reading_rule 与协议第 0 节一致。协议写出的字节正则用于 1200 行时，与我第 1 轮的正则逐行捕获到相同的 (domain, split)，没有不匹配的行；每领域 test 行跳过前 25 行后为 175 行。
- **G-D2 上界**：协议第 7.5 节与 DAMAGE_MANIFEST 一致，D1-all、D1-diff 为 0.10，D1-same 为 0.20；2 × sqrt(0.25/800) = 0.035355 ≈ 0.035。
- **删去占位字段：没有丢失任何与数据有关的信息。**
  - 被删去的 41 个叶子全部是 `NOT_GENERATED` 或 `null`。
  - 12 个 files 条目的 content、reference_canonical_sha256、canonical_check、generation_allowed 原样保留。
  - 原 split_sha256 中的 5 个文件都还有参考哈希，或有 st10_record 的规则。
  - 实际哈希写到哪里由三处给出：ST12、`reported_values`（step1_record：9 个非 TEST 文件的数据哈希；st10_record：TEST 文件的 sha256），以及 SPLIT_MANIFEST 新增的 `actual_hashes`。
  - 两个 manifest 的 hashing 中对 byte_sha256、canonical_sha256 的定义仍在。
  - 协议和 JSON 中已没有对 split_sha256 或 NOT_GENERATED 的悬空引用。
- **交付物 diff**：11 个文件的 hunk 与 `git diff --cached HEAD` 逐字节相同，暂存树就是 f395c476…。
- 这一项只有 N1 一处小的措辞问题，见问题清单。

---

## 项目 3：sigma_planning.txt 的独立复算

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/r2_item3_sigma.py`

**原始输出**（完整 stdout）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T10:08:28Z; round 2, staged tree f395c476606603e65d336e1ba3ac34a065c40889
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/r2_item3_sigma.py
input /home/user/OpenMythos/metrix/e1-pilot/results/details/N_dev.json sha256 32c963faef4d9b78a5257c5f444010e6b7a7bf113f40d968994fd9daa9fc4ade
fields: kind evaluation_details | label None | mode formal | model N | split dev
OK   split of the file: got DEV | expected DEV
OK   windows per domain: got {'books': 25, 'c4': 25, 'fineweb': 25, 'wikitext': 25} | expected {'books': 25, 'c4': 25, 'fineweb': 25, 'wikitext': 25}
OK   doc_ids are <domain>-dev-000..024 (the first 25 DEV rows, contained in V1 D1 DEV): got True | expected True
OK   all NLL finite: got True | expected True
domain books    n 25 mean NLL 3.5531 SD(n-1) 0.5516 SD(n) 0.5404
domain c4       n 25 mean NLL 2.9840 SD(n-1) 0.4317 SD(n) 0.4230
domain fineweb  n 25 mean NLL 2.9414 SD(n-1) 0.4517 SD(n) 0.4426
domain wikitext n 25 mean NLL 2.8912 SD(n-1) 0.3520 SD(n) 0.3449
OK   Executor per-domain mean / SD (4 d.p.) = auditor mean / SD(n-1): got {'books': (3.5531, 0.5516), 'c4': (2.984, 0.4317), 'fineweb': (2.9414, 0.4517), 'wikitext': (2.8912, 0.352)} | expected {'books': (3.5531, 0.5516), 'c4': (2.984, 0.4317), 'fineweb': (2.9414, 0.4517), 'wikitext': (2.8912, 0.352)}
D1-all   analytic, SD(n-1), 100 windows per domain: sigma_N 0.0226  m = 2 sigma 0.0452
D1-all   analytic, SD(n), 100 windows per domain: sigma_N 0.0222  m = 2 sigma 0.0443
D1-diff  analytic, SD(n-1), 100 windows per domain: sigma_N 0.0261  m = 2 sigma 0.0523
D1-diff  analytic, SD(n), 100 windows per domain: sigma_N 0.0256  m = 2 sigma 0.0512
D1-same  analytic, SD(n-1), 100 windows per domain: sigma_N 0.0452  m = 2 sigma 0.0903
D1-same  analytic, SD(n), 100 windows per domain: sigma_N 0.0443  m = 2 sigma 0.0885
OK   Executor sigma_N / m (4 d.p.) = auditor analytic with SD(n-1): got {'D1-all': (0.0226, 0.0452), 'D1-diff': (0.0261, 0.0523), 'D1-same': (0.0452, 0.0903)} | expected {'D1-all': (0.0226, 0.0452), 'D1-diff': (0.0261, 0.0523), 'D1-same': (0.0452, 0.0903)}
OK   protocol 7.5 planning m (D1-all, D1-diff, D1-same) = auditor 2 sigma rounded to 3 d.p.: got (0.045, 0.052, 0.09) | expected (0.045, 0.052, 0.09)
OK   planning m within the G-D2 bounds (0.10, 0.10, 0.20): got (True, True, True) | expected (True, True, True)
ratio sigma(D1-same) / sigma(D1-all) = 1.997 (protocol 7.5: 'about 2 times')
OK   Executor D2 line (sigma bound, m bound) = auditor: got (0.0177, 0.0354) | expected (0.0177, 0.0354)
G-D3 D2 threshold 0.05 / sigma bound 0.0177 = 2.83 (protocol 7.5: 'about 3 times')
D1-all   bootstrap (10,000): 25 windows/domain sigma 0.0441 -> x 1/2 for 100/domain 0.0220; 100 windows/domain (Pilot windows x 4) sigma 0.0225  m 0.0449
D1-diff  bootstrap (10,000): 25 windows/domain sigma 0.0516 -> x 1/2 for 100/domain 0.0258; 100 windows/domain (Pilot windows x 4) sigma 0.0257  m 0.0514
D1-same  bootstrap (10,000): 25 windows/domain sigma 0.0875 -> x 1/2 for 100/domain 0.0437; 100 windows/domain (Pilot windows x 4) sigma 0.0446  m 0.0892
ITEM3 round 2: ALL MATCH
exit=0
```

**与 Executor 是否一致**：**一致**。
- 每领域的均值与样本标准差（分母 n−1）与 sigma_planning.txt 逐位相同（4 位小数）。
- 按 σ = sqrt(Σ SD²/100) / 领域数 得到 m = 0.0452 / 0.0523 / 0.0903，取 3 位为 0.045 / 0.052 / 0.090，与协议第 7.5 节和 DAMAGE_MANIFEST 的 planning 相同，全部在上界之内。
- D2 一行 0.0177 / 0.0354 相同。
- 协议中的两处「约 2 倍」「约 3 倍」分别为 1.997 与 2.83。
- 按 DAMAGE_MANIFEST 的分层 bootstrap 规则另做 10,000 次模拟，得到 m ≈ 0.045 / 0.051 / 0.089，与解析值相符。

规划估计的说明（只报告）：
- 这里的标准差只来自每领域 25 个窗口。
- 用上面打印的数值相除：D1-diff 的标准差要大到约 1.9 倍（0.10 / 0.0523）才会触到上界；D1-all、D1-same 约为 2.2 倍。
- 这个计算只作规划，不进记录，所以对数据、指标、门槛、可复现性、iso、损伤测量都没有影响。

---

## 项目 4：协议第 6.4 节第 2a 条（精确有理数），第 6.7 节的保存规则与第 6.4 节的夹逼规则是否一致

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/r2_item4_fraction.py`（第二次运行；第一次运行见 `r2_item4_fraction_round2_firstrun.txt`，只有第 (5) 部分和计时行不同）

**原始输出**（完整 stdout）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T10:12:03Z; round 2, staged tree f395c476606603e65d336e1ba3ac34a065c40889; second run: part (5) construction made deterministic (first run's random construction had no target in (a_lo, a_hi]); first run kept as r2_item4_fraction_round2_firstrun.txt
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/r2_item4_fraction.py
grid: Acq = (sum over 240 learned facts of correct/2) / 240 -> multiples of 1/480
  7/10 * 480 = 336 (integer: True); * 720 = 504 (TEST grid 1/720: True)
  4/5 * 480 = 384 (integer: True); * 720 = 576 (TEST grid 1/720: True)
  9/10 * 480 = 432 (integer: True); * 720 = 648 (TEST grid 1/720: True)
  1/10 * 480 = 48 (integer: True); * 720 = 72 (TEST grid 1/720: True)
  1/20 * 480 = 24 (integer: True); * 720 = 36 (TEST grid 1/720: True)
  constructed Acq from per-fact Scores: 79/160 = 237/480, denominator divides 480: True
critical values (16): ['0', '1/2', '287/480', '3/5', '289/480', '67/96', '7/10', '337/480', '383/480', '4/5', '77/96', '431/480', '9/10', '433/480', '479/480', '1']
(1) exhaustive, length 5 over the critical values: sequences 1048576 | qualifying brackets 491328 | sequences with a bracket endpoint not saved 0 | saved but unused checkpoints (sum) 2422256
(2) random length 10, critical values, any order: sequences 50000 | brackets 30725 | sequences with an unsaved bracket endpoint: formal reading 0, other reading of the item-1 parenthesis 0 | sequences where the two readings give different iso results 10610
(2) random length 10, grid k/480, any order: sequences 50000 | brackets 8375 | sequences with an unsaved bracket endpoint: formal reading 0, other reading of the item-1 parenthesis 0 | sequences where the two readings give different iso results 1448
(2) random length 10, grid k/480, non-decreasing: sequences 50000 | brackets 62172 | sequences with an unsaved bracket endpoint: formal reading 0, other reading of the item-1 parenthesis 0 | sequences where the two readings give different iso results 0
(2) random length 10, grid, curve-like: increments k/480 with k in -24..72: sequences 50000 | brackets 94467 | sequences with an unsaved bracket endpoint: formal reading 0, other reading of the item-1 parenthesis 0 | sequences where the two readings give different iso results 718
(3) edge cases (t = 0.70 unless stated), exact Fraction vs float with a_j = float mean of per-fact Scores
    a_j* - t = 0.10 exactly (0.65 -> 0.80): a = ['1/2', '13/20', '4/5'] float a = [0.5, 0.65, 0.8] | exact iso (2, 3) saved [2, 3] consistent True | float iso None saved [2] | exact 6.4 with float 6.7 leaves an endpoint unsaved: True
    t - a_j*-1 = 0.10 exactly (0.60 -> 0.75): a = ['1/2', '3/5', '3/4'] float a = [0.5, 0.6, 0.75] | exact iso (2, 3) saved [2, 3] consistent True | float iso (2, 3) saved [2, 3] | exact 6.4 with float 6.7 leaves an endpoint unsaved: False
    a_j* = t exactly, w = 1 (0.65 -> 0.70): a = ['1/2', '13/20', '7/10'] float a = [0.5, 0.65, 0.7] | exact iso (2, 3) saved [2, 3] consistent True | float iso (2, 3) saved [2, 3] | exact 6.4 with float 6.7 leaves an endpoint unsaved: False
    a_j*-1 = t exactly is not below t (0.70 -> 0.75): a = ['1/2', '7/10', '3/4'] float a = [0.5, 0.7, 0.75] | exact iso None saved [2] consistent True | float iso None saved [2] | exact 6.4 with float 6.7 leaves an endpoint unsaved: False
    both ends exactly 0.10 away (0.60 -> 0.80): a = ['1/2', '3/5', '4/5'] float a = [0.5, 0.6, 0.8] | exact iso (2, 3) saved [2, 3] consistent True | float iso None saved [2] | exact 6.4 with float 6.7 leaves an endpoint unsaved: True
    t = 0.80: 0.70 -> 0.90: a = ['1/2', '7/10', '9/10'] float a = [0.5, 0.7, 0.9] | exact iso (2, 3) saved [2, 3] consistent True | float iso None saved [3] | exact 6.4 with float 6.7 leaves an endpoint unsaved: True
    t = 0.90: 0.80 -> 1.00: a = ['1/2', '4/5', '1'] float a = [0.5, 0.8, 1.0] | exact iso (2, 3) saved [2, 3] consistent True | float iso (2, 3) saved [2, 3] | exact 6.4 with float 6.7 leaves an endpoint unsaved: False
(4) DOSE_SPACE iso.targets[0] = 0.7, tau_dev = 0.1
    Fraction(float) gives t = 3152519739159347/4503599627370496 (== 7/10: False), tau = 3602879701896397/36028797018963968 (== 1/10: False)
    json.loads(parse_float=Fraction) gives t = 7/10, tau = 1/10 (exact: True)
    sequence ['1/2', '13/20', '4/5']: iso with Fraction('0.70'), Fraction('0.10') -> (2, 3); with Fraction(0.7), Fraction(0.1) -> None
(5) constructed facts: a_lo 317/480 (0.660417), a_hi 35/48 (0.729167), t 7/10, w 19/33; per-fact interpolated Acq = 7/10 == t: True; float(w) = 0.5757575757575758
elapsed 114.0 s
ITEM4 round 2: CONSISTENT (sequences with an unsaved bracket endpoint over (1) and (2): 0)
exit=0
```

**结果：一致。**
- 0.70、0.80、0.90、0.10、0.05 都正好落在 1/480 网格上（也都落在 TEST 的 1/720 网格上），所以 a_j = t、a_j − t = 0.10 这样的边界值确实会出现。
- 按 2a 的精确有理数算术，第 6.7 节的保存规则覆盖了第 6.4 节每一个合格夹逼区间的两端：
  - 长度为 5 的序列在 16 个临界值上穷举 1,048,576 条，共 491,328 个夹逼区间，未保存的端点为 0。
  - 长度为 10 的随机序列 4 × 50,000 条，未保存的端点同样为 0。
- 保存规则是夹逼端点的超集。多保存的 checkpoint 只占磁盘，协议本来就不删除 checkpoint。
- 插值验证：w ∈ (0, 1]，DEV 上逐 fact 插值得到的 Acq 恰好等于 t（7/10，w = 19/33）。
- 浮点算术会在边界上出错，这正说明 2a 必要：
  - 0.65 → 0.80（t = 0.70）、0.60 → 0.80、0.70 → 0.90（t = 0.80）这三例，浮点算术判为 NOT_REACHED，精确算术判为合格。
  - 如果第 6.4 节用精确算术、第 6.7 节用浮点，这三例都会漏存一个端点。
- 与 Executor 的对应：协议在这一点上没有 Executor 的数值可以比对。我的结论是，协议文字的说法「按第 6.4 节，任何合格的夹逼两端都满足这个条件」在 2a 的算术下成立。
- 影响：数据否，指标否，门槛否，可复现性否，iso 否（2a 使两条规则一致），损伤测量否。N2、N3 两条观察见问题清单。

---

## 问题清单（每项注明是否影响：数据 / 指标 / 门槛 / 可复现性 / iso-acquisition 匹配 / 损伤测量）

**第 1 轮的问题**：
- **B1**：已解决（项目 1b）。
- **M2、M3、M4**：已解决，与我的实现和参考哈希一致（项目 1b）。
- **M1**：本轮未涉及。v1_data_check.txt 未改动，SPLIT_MANIFEST 的值独立复算仍为 0。
- **M5**：已由协议第 0 节写出字节正则而解决，并已验证（项目 2 (d)）。
- **M6、M8**：不变。M8 本轮的对应披露见第 0 节第 1 条。
- **M7**：仍交 Review Gate。

**本轮新登记的观察**（都不构成不一致，所以都不判 BLOCK）：

- **N1（措辞）**：DAMAGE_MANIFEST 写「m(D2) <= 2 * sqrt(0.25 / 800) by construction」，协议第 7.5 节写「最大为 2 × sqrt(0.25/800) ≈ 0.035」，sigma_planning.txt 写「m <= 0.0354」。
  - 这对总体值成立。但有限次（10,000 次）bootstrap 的样本标准差可能略超过它：在 Acc = 0.5 时，20 次模拟中有 7 次超过 sqrt(0.25/800)，2σ 最大为 0.0360（项目 2 (e)）。
  - m(D2) 不设上界，按 bootstrap 的实际结果取值，所以这只是措辞。
  - 影响：数据否，指标否，门槛否，可复现性否，iso 否，损伤测量否。

- **N2（实现隐患）**：DOSE_SPACE.json 的 `iso` 用 JSON 数字存 0.7 / 0.8 / 0.9 / 0.1 / 0.05，没有提到第 2a 条。
  - 如果实现从这里取值并做 `Fraction(float)`，阈值不是精确值：0.65 → 0.80 会从合格变成 NOT_REACHED（项目 4 (4)）。
  - 协议第 2a 条已明确写出 `Fraction("0.70")` 的取法；`json.loads(parse_float=Fraction)` 也能得到精确值。所以文字之间并不矛盾。
  - 影响：只有当实现不按 2a 取值时，才影响可复现性与 iso 匹配。低。数据、指标、门槛、损伤测量否。

- **N3（第 6.4 节第 1 条括号的读法，本轮之前就存在）**：「(…包括第 1 个剂量点已 ≥ t 的情形)」可以读成「a_1 ≥ t 即 NOT_REACHED」。
  - 对非单调曲线（a_1 ≥ t，之后跌到 t 以下，再越过 t），这种读法与形式规则（j ≥ 2 的最小越过点）给出不同的结果。
  - 两种读法结果不同的序列数：单调不减的序列中为 0；带回落的类曲线序列中为 718 / 50,000（项目 4 (2)）。
  - 两种读法下，第 6.7 节都没有漏存端点。
  - 影响：只在这种少见情形下影响 iso 匹配的可复现性。数据、指标、门槛、损伤测量否。建议 Review Gate 确认以形式规则为准。

- **N4（措辞）**：anchor_text.jsonl 的 record 中，「encode(text, …)」里的 text 指源文档，与字段 `text` = decode(ids) 同名。
  - DATA_MANIFEST 的 `anchor_text.decoded_texts_hash_rule` 写的是「encode(document i, …)」，已经消除了歧义。
  - 「默认参数」的几种变体对哈希没有影响（项目 1b）。
  - 影响：全部为否。

- **N5（治理，只登记）**：协议第 7.1 节把 ARC 数字的出处写成 data-auditor 的输出 `audit/stdout/a5_damage.txt`。这个文件已在暂存树中，内容与数据相符。是否允许协议引用审查方的输出作为依据，交 Review Gate。影响：全部为否。

**本轮没有审计的内容**：
- DOSE_SPACE 的 st11_bound 与第 12 节 ST11 公式中的常数。这些是算力，不是数据；项目 2 (a) 只列出了文字改动。
- Executor 各 .py 文件的代码。那是 code-reviewer 的职责，我没有打开。

**信任状态提醒**：按 metrix/CLAUDE.md 第 10 节，data-auditor 仍是「待验证」，本 PASS 只作参考。

---

## git status --short（运行全部脚本之后的原始输出）
```
M  metrix/e1-v1/DAMAGE_MANIFEST.json
M  metrix/e1-v1/DATA_MANIFEST.json
M  metrix/e1-v1/DOSE_SPACE.json
M  metrix/e1-v1/METRIX_E1V1_PROTOCOL.md
M  metrix/e1-v1/SPLIT_MANIFEST.json
M  metrix/e1-v1/SUBMISSION_NOTE.md
A  metrix/e1-v1/audit/a1_hashes.py
A  metrix/e1-v1/audit/a2_leakage.py
A  metrix/e1-v1/audit/a3_candidates.py
A  metrix/e1-v1/audit/a4_split.py
A  metrix/e1-v1/audit/a5_damage.py
A  metrix/e1-v1/audit/a6_consistency.py
A  metrix/e1-v1/audit/a7_hub.py
A  metrix/e1-v1/audit/a8_d2_inputs.py
A  metrix/e1-v1/audit/audit_lib.py
A  metrix/e1-v1/audit/stdout/a1_hashes.txt
A  metrix/e1-v1/audit/stdout/a2_leakage.txt
A  metrix/e1-v1/audit/stdout/a3_candidates.txt
A  metrix/e1-v1/audit/stdout/a4_split.txt
A  metrix/e1-v1/audit/stdout/a5_damage.txt
A  metrix/e1-v1/audit/stdout/a6_consistency.txt
A  metrix/e1-v1/audit/stdout/a7_hub.txt
A  metrix/e1-v1/audit/stdout/a8_d2_inputs.txt
M  metrix/e1-v1/reports/authoring/build_manifests.py
M  metrix/e1-v1/reports/authoring/compute_estimate.py
M  metrix/e1-v1/reports/authoring/compute_estimate.txt
A  metrix/e1-v1/reports/authoring/sigma_planning.py
A  metrix/e1-v1/reports/authoring/sigma_planning.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/README.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/code-reviewer_round1.md
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/code-reviewer_round1_prompt.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/code-reviewer_round1_transcript.jsonl
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/data-auditor_round1.md
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/data-auditor_round1_prompt.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/data-auditor_round1_transcript.jsonl
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/extract_log.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/input_round1.diff
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/launch_time_round1.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/preflight_tools_check.txt
A  metrix/e1-v1/reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/tree_round1.txt
?? metrix/e1-v1/audit/r2_item1_fixes.py
?? metrix/e1-v1/audit/r2_item2_json.py
?? metrix/e1-v1/audit/r2_item3_sigma.py
?? metrix/e1-v1/audit/r2_item4_fraction.py
?? metrix/e1-v1/audit/stdout/a1_hashes_round2.txt
?? metrix/e1-v1/audit/stdout/a2_leakage_round2.txt
?? metrix/e1-v1/audit/stdout/a3_candidates_round2.txt
?? metrix/e1-v1/audit/stdout/a4_split_round2.txt
?? metrix/e1-v1/audit/stdout/a5_damage_round2.txt
?? metrix/e1-v1/audit/stdout/a7_hub_round2.txt
?? metrix/e1-v1/audit/stdout/a8_d2_inputs_round2.txt
?? metrix/e1-v1/audit/stdout/r2_item1_fixes_round2.txt
?? metrix/e1-v1/audit/stdout/r2_item2_json_round2.txt
?? metrix/e1-v1/audit/stdout/r2_item2_json_round2_firstrun.txt
?? metrix/e1-v1/audit/stdout/r2_item3_sigma_round2.txt
?? metrix/e1-v1/audit/stdout/r2_item4_fraction_round2.txt
?? metrix/e1-v1/audit/stdout/r2_item4_fraction_round2_firstrun.txt
?? metrix/e1-v1/audit/tmpdata/
```
- `git diff --name-only` 为空，`git ls-files -s` 与 `git ls-tree -r f395c476…` 逐项相同。我没有改动任何被跟踪的文件，第 1 轮的 audit 文件也没有改。
- 新增内容只有 `metrix/e1-v1/audit/` 下的未跟踪文件。
- 入库时只提交 `audit/r2_*.py` 与 `audit/stdout/*_round2*.txt`。`audit/tmpdata/`（/home/user/OpenMythos/metrix/e1-v1/audit/tmpdata/v1data/）是生成的非 TEST 数据，不要提交。

结论：PASS
