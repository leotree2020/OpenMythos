# data-auditor, round 1 of the E1-V1 protocol authoring (staged tree 0e3dc49eaca9b07254e61301bc2602f8d8a39eea = work commit 59761ad923674d43725167a8c79f6bdf16f531ee)
# final report extracted unchanged from data-auditor_round1_transcript.jsonl by metrix/e1-pilot/reports/round6/review_extract.py (run, not modified)
---
# data-auditor 第 1 轮审计：E1-V1 协议草案（暂存树 0e3dc49eaca9b07254e61301bc2602f8d8a39eea，HEAD 6e03468956208c422d0d41c08edaaf116166338c）

## 0. 前提、环境与范围

**路径对应：我接受。** 依据有三条：Task Order 第 3 节红线 3 禁止改动 metrix/e1-pilot/；metrix/CLAUDE.md 第 8 节 2026-11-28 的条目规定第 5、9、10 节的做法在 E1-V1 继续适用；V1 协议第 12 行规定 `audit/…` 相对于 `metrix/e1-v1/`。所以本轮的脚本写在 `metrix/e1-v1/audit/`，完整 stdout 写在 `metrix/e1-v1/audit/stdout/`。我的定义文件 `.claude/agents/data-auditor.md`（仓库版与已加载版逐字相同，tools 行均为 `Read, Grep, Glob, Write, Bash`）仍写的是 `metrix/e1-pilot/audit/`，这一对应作为待决事项交 Review Gate。

**运行环境**：主机 `vm`，Claude Code 云容器，只用 CPU，无 GPU，没有安装 torch。Python 3.13.18，transformers 5.22.2，tokenizers 0.23.3，pyarrow 26.0.1，用 `-I -B` 运行。只加载了分词器（AutoTokenizer，以及 parcae 的 tokenizers.Tokenizer），没有加载任何模型权重。

**读了什么**：
- 协议与四个 JSON、两份任务原文。
- Pilot 协议 v1.1 与 Pilot 的两个 manifest。
- Executor 的输出文本 `reports/authoring/v1_data_check.txt`、`d2_dataset_metadata.txt`、`v1_data_check_repeat.txt`，只用于比对。
- git 元数据。
- 另外，为了查记录字段名，我用 grep 搜索了仓库中的 .md/.json 文件。结果中出现了几行 Pilot 审查记录的文字，但没有任何代码。

**没有打开**：`metrix/e1-v1/reports/authoring/*.py`、`metrix/e1-pilot/src/`，以及 `metrix/e1-pilot/reports/` 下的任何脚本。规则全部按协议与 manifest 的文字独立实现。

**TEST**：
- eval_sets.jsonl 的 test 行只用字节正则 `^\{"domain": "([a-z0-9_]+)", "split": "([a-z]+)", ` 匹配行首后计数，不解码，不做 json 解析。只有 dev 行做了 json 解析。
- MMLU all/test 与 ARC 的两个 test parquet 只对整个文件求 sha256，并读 parquet 文件尾的 num_rows，没有读任何行。
- 没有生成任何 TEST 文件。

**我写入的文件**（全部在 audit/ 下）：
- 脚本：`/home/user/OpenMythos/metrix/e1-v1/audit/audit_lib.py`、`a1_hashes.py`、`a2_leakage.py`、`a3_candidates.py`、`a4_split.py`、`a5_damage.py`、`a6_consistency.py`、`a7_hub.py`、`a8_d2_inputs.py`。
- 完整 stdout：`/home/user/OpenMythos/metrix/e1-v1/audit/stdout/a1_hashes.txt` … `a8_d2_inputs.txt`。
- 临时数据（只有非 TEST 数据，**不入库**）：`/home/user/OpenMythos/metrix/e1-v1/audit/tmpdata/v1data/`。

stdout 文件的 sha256：

| 文件 | sha256 |
|---|---|
| a1_hashes.txt | df2340c19667a2511785564d02a9f08457ff49d6c820b9b0f0325ef3ac7d1127 |
| a2_leakage.txt | 1a7a82ef211118bfcfcaa5212fb689d7e11e9ef1e8988a70506361c50b5ae8fc |
| a3_candidates.txt | aa1d771690d40f812a206f90d53271ae9f1174f741dc42caaa5904ca5103f34e |
| a4_split.txt | 6336d9b90aa936e7e7f7287024d4ce9ab99069ceb2cc5cd46f022bf72baef88a |
| a5_damage.txt | dee88deff5e269627837d195698364e5cafb11002975e59ce7f01bb24238323f |
| a6_consistency.txt | 65996f5c5c6eddddb96ac0624bdd4135c096042aa3782103aaccc9d4b5fffd95 |
| a7_hub.txt | e147b0535f735f781ffad072724782da9e0a6345cf6360b2ccdfc2950ef34400 |
| a8_d2_inputs.txt | 6133792155ec40cf9941d2274f5c9ddd8fb58ea948febf40f82aded957c0c969 |

**一项需要说明的操作**：我的第一条命令里运行过一次 `git write-tree`，用来确认暂存树是 0e3dc49e…。它不改动任何被跟踪的文件，也不改动 index。如果该树对象原本不在 `.git/objects` 中，它会被写入一份；树 id 与调用方给出的一致，所以它多半原本就在。之后的核对全部改用只读命令（`git ls-files -s` 对 `git ls-tree -r`）。

每个脚本的运行方式相同：
`(echo "# host…"; echo "$ …"; <S>/venv/bin/python -I -B metrix/e1-v1/audit/<脚本>.py 2>&1; echo "exit=$?") > metrix/e1-v1/audit/stdout/<脚本>.txt`

其中 `<S>` = /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad。依次运行 a1、a5、a2、a3、a4、a6、a7、a8，因为 a2–a4、a8 读取 a1 与 a5 生成的临时数据。

---

## 项目 1：哈希

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/a1_hashes.py`

**原始输出**（完整 stdout，与 `stdout/a1_hashes.txt` 相同）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:33:00Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a1_hashes.py
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
python 3.13.18 | transformers 5.22.2 | tokenizers 0.23.3
input qwen/tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 manifest aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 equal True
input qwen/tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 manifest d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True
input qwen/vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 manifest ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True
input qwen/merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 manifest 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True
tokenizer class Qwen2Tokenizer | <|endoftext|> id 151643
OK   anchor parquet sha256 (manifest anchor_text.source): got 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | expected 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22
anchor docs 512 | source rows scanned 527 | last source_row 526 | ids per doc min/max 123 128
OK   anchor decoded texts canonical sha256 (JSON list): got 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | expected 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408
OK   anchor decoded texts = Pilot manifest value: got 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | expected 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408
OK   anchor_text.jsonl canonical sha256 {doc, source_row, ids, text}: got 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5 | expected 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5
OK   anchor_text.jsonl = Pilot generated file hash: got 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5 | expected 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5
templates V1 32 | Pilot 32 | identical lists True
templates normalized text / normalized_sha256 mismatches: 0
OK   template_set_sha256: got 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | expected 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f
OK   template_set_sha256 = Pilot: got 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | expected 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f
templates per (relation, kind): [(('capital', 'DEV'), 2), (('capital', 'TEST'), 3), (('capital', 'TRAIN'), 1), (('capital', 'Y_ANSWER'), 1), (('capital', 'Y_ENTITY'), 1), (('currency', 'DEV'), 2), (('currency', 'TEST'), 3), (('currency', 'TRAIN'), 1), (('currency', 'Y_ANSWER'), 1), (('currency', 'Y_ENTITY'), 1), (('founder', 'DEV'), 2), (('founder', 'TEST'), 3), (('founder', 'TRAIN'), 1), (('founder', 'Y_ANSWER'), 1), (('founder', 'Y_ENTITY'), 1), (('river', 'DEV'), 2), (('river', 'TEST'), 3), (('river', 'TRAIN'), 1), (('river', 'Y_ANSWER'), 1), (('river', 'Y_ENTITY'), 1)]
Pilot facts 160 | built in 0.3 s
  Pilot cell capital/natural: entity_draws 28 answer_draws 84 target [3, 3]
  Pilot cell capital/random: entity_draws 20 answer_draws 52 target [5, 5]
  Pilot cell currency/natural: entity_draws 31 answer_draws 82 target [3, 3]
  Pilot cell currency/random: entity_draws 20 answer_draws 46 target [6, 6]
  Pilot cell founder/natural: entity_draws 30 answer_draws 81 target [3, 3]
  Pilot cell founder/random: entity_draws 21 answer_draws 45 target [5, 5]
  Pilot cell river/natural: entity_draws 34 answer_draws 89 target [3, 3]
  Pilot cell river/random: entity_draws 20 answer_draws 42 target [6, 6]
OK   Pilot facts canonical sha256 (JSON list): got 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | expected 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
OK   Pilot facts.jsonl canonical (Pilot manifest files.facts.jsonl): got e05561ac2d49dcc3c8f59743c5df64151983a540a32ae135fd1b10f5e0fdc828 | expected e05561ac2d49dcc3c8f59743c5df64151983a540a32ae135fd1b10f5e0fdc828
OK   Pilot train_F.jsonl: got 3aa9ab3ca313c0a1113b91e927af51342c915e3e40dd2f20992f3d9e59b0e373 | expected 3aa9ab3ca313c0a1113b91e927af51342c915e3e40dd2f20992f3d9e59b0e373
OK   Pilot train_S.jsonl: got 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | expected 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e
OK   Pilot train_Y.jsonl: got c7430cadb2b06dd5c144af381a8183d4c186f27f2b5acfa9d8d39da0b7626d15 | expected c7430cadb2b06dd5c144af381a8183d4c186f27f2b5acfa9d8d39da0b7626d15
OK   Pilot dev_qa.jsonl: got 9761eb60d6c9155c2f56394aa228b1e9dfea0ae3926ab50cb21d903108bc7fde | expected 9761eb60d6c9155c2f56394aa228b1e9dfea0ae3926ab50cb21d903108bc7fde
OK   Pilot candidates.json: got e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | expected e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705
Pilot strings 320 | distinct 320
V1 facts 320 | built in 0.5 s
  V1 cell capital/natural: entity_draws 81 answer_draws 188 target [3, 3] | survey counts {(2, 2): 25, (2, 3): 25, (3, 3): 145, (3, 4): 38, (4, 3): 1, (4, 4): 122, (4, 5): 12, (5, 4): 1, (5, 5): 27, (5, 6): 1, (6, 6): 3}
  V1 cell capital/random: entity_draws 40 answer_draws 87 target [6, 6] | survey counts {(4, 4): 4, (4, 5): 2, (5, 5): 145, (5, 6): 11, (6, 5): 10, (6, 6): 193, (6, 7): 5, (7, 6): 2, (7, 7): 27, (8, 7): 1}
  V1 cell currency/natural: entity_draws 67 answer_draws 196 target [3, 3] | survey counts {(2, 2): 36, (2, 3): 25, (3, 3): 163, (3, 4): 26, (4, 4): 111, (4, 5): 13, (5, 5): 24, (6, 6): 2}
  V1 cell currency/random: entity_draws 40 answer_draws 80 target [6, 6] | survey counts {(4, 4): 2, (4, 5): 3, (5, 5): 155, (5, 6): 16, (6, 5): 14, (6, 6): 182, (6, 7): 4, (7, 7): 23, (8, 8): 1}
  V1 cell founder/natural: entity_draws 77 answer_draws 270 target [3, 3] | survey counts {(2, 2): 35, (2, 3): 26, (3, 3): 142, (3, 4): 32, (4, 4): 131, (4, 5): 16, (5, 5): 18}
  V1 cell founder/random: entity_draws 40 answer_draws 92 target [5, 5] | survey counts {(4, 4): 1, (4, 5): 1, (5, 4): 3, (5, 5): 168, (5, 6): 15, (6, 5): 16, (6, 6): 168, (6, 7): 2, (7, 6): 4, (7, 7): 21, (8, 8): 1}
  V1 cell river/natural: entity_draws 83 answer_draws 229 target [3, 3] | survey counts {(2, 2): 32, (2, 3): 20, (3, 3): 150, (3, 4): 35, (4, 3): 1, (4, 4): 121, (4, 5): 14, (5, 5): 25, (5, 6): 1, (6, 6): 1}
  V1 cell river/random: entity_draws 40 answer_draws 111 target [6, 6] | survey counts {(4, 4): 1, (4, 5): 2, (5, 4): 1, (5, 5): 169, (5, 6): 16, (6, 5): 10, (6, 6): 171, (6, 7): 2, (7, 6): 2, (7, 7): 25, (8, 8): 1}
OK   V1 facts canonical sha256 (JSON list) = DATA_MANIFEST expected_facts_canonical_sha256: got 0fc5ad819500e8a9f56771405af67d0fa71bafabba25bf8f4c3e5b6d684e01f4 | expected 0fc5ad819500e8a9f56771405af67d0fa71bafabba25bf8f4c3e5b6d684e01f4
OK   V1 facts.jsonl canonical (JSONL) = files.facts.jsonl.reference_canonical_sha256: got 4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9 | expected 4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9
S derangement attempts per cell {'capital/natural': 6, 'capital/random': 1, 'currency/natural': 10, 'currency/random': 2, 'founder/natural': 4, 'founder/random': 2, 'river/natural': 1, 'river/random': 1}
rows: train_F 240 | train_S 240 | train_Y 480 | dev_qa 640 | candidates keys 320
OK   train_F.jsonl: got fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511 | expected fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511
OK   train_S.jsonl: got 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6 | expected 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6
OK   train_S.jsonl = s_permutation.expected_train_S_canonical_sha256: got 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6 | expected 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6
OK   train_Y.jsonl: got 82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b | expected 82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b
OK   dev_qa.jsonl: got 39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce | expected 39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce
OK   candidates.json: got 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3 | expected 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3
OK   candidates.json = SPLIT_MANIFEST candidate_mapping_sha256: got 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3 | expected 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3
Y/F tokens: F 3802 Y 4541 ratio 1.194371 in [0.80, 1.25] True
OK   F tokens: got 3802 | expected 3802
OK   Y tokens: got 4541 | expected 4541
OK   ratio (4 d.p.): got 1.1944 | expected 1.1944
exposure matching train_F (F, L, A, Z0, P+): violations (case-insensitive substring count) 0 | (whole-word, per-text) 0
exposure matching train_S (S): violations (case-insensitive substring count) 0 | (whole-word, per-text) 0
exposure matching train_Y (Y): violations (case-insensitive substring count) 0 | (whole-word, per-text) 0
exposure matching anchor_text (A): candidates occurring 0 (expected 0)
exposure matching total violations 0
written facts.jsonl byte_sha256 4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9
written train_F.jsonl byte_sha256 fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511
written train_S.jsonl byte_sha256 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6
written train_Y.jsonl byte_sha256 82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b
written dev_qa.jsonl byte_sha256 39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce
written candidates.json byte_sha256 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3
written anchor_text.jsonl byte_sha256 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5
elapsed 5.0 s
ITEM1 (facts/templates/files part): ALL MATCH
exit=0
```

**与 Executor 是否一致**：**一致**。
- Pilot 的 160 条 fact 等于 406c8801…；我的实现也重现了 Pilot 冻结的 train_F、train_S、train_Y、dev_qa、candidates 与 facts.jsonl 的哈希，说明记录格式的读法正确。
- V1 的哈希全部相同：facts 列表 0fc5ad81…，facts.jsonl 4eeee6d1…，train_F、train_S、train_Y、dev_qa、candidates、anchor_text.jsonl，锚文本解码文本 8828bc4f…。
- 32 个模板的 normalized 文本与 normalized_sha256 全部相同，template_set_sha256 = 2b524113…。
- Y/F = 3802 / 4541 = 1.1944。暴露匹配违规 0。
- 各 cell 的抽取次数与 v1_data_check.txt 逐项相同（entity 40–83 次，answer 80–270 次）。

---

## 项目 2：泄漏 L1–L8（DEV 部分）

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/a2_leakage.py`

**原始输出**（完整）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:35:28Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a2_leakage.py
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
L1 set sizes {'TRAIN': 4, 'DEV': 8, 'TEST': 12, 'Y': 8} | pairwise intersections 0 | duplicate normalized hashes among all 32 0
L2 max word 4-gram Jaccard over pairs from different sets 0.2 pair ('capital.TRAIN.1', 'capital.DEV.1') (same-relation max 0.2); limit 0.25 ok True
L3a unread strings 160 occurrences per corpus {'train_F': 0, 'train_S': 0, 'train_Y': 0, 'anchor_text': 0} total 0
L3b learned answers in anchor_text 0 | report only: learned entities in anchor_text 0
L4 DEV questions 640 verbatim occurrences in train_F/S/Y/anchor 0 | case-insensitive (report only) 0
L5 learned/unread fact_id intersection 0 | strings 640 duplicates 0 | case-insensitive duplicates (report) 0 | answer values used more than once 0
L6 anchor word 13-grams 44255 | D1 DEV windows 400 word 13-grams 72033 shared 0 | token-id 13-grams (report only) shared 0
L6 D2 DEV MMLU items 800 word 13-grams 58870 shared 0 | D2 DEV ARC items 800 word 13-grams 31866 shared 0
L7 (a) 0 | (b) same stratum 0 [] | report: (b) against any Pilot string 0 | (c) 0 | Pilot strings 320 fact_ids 160
L8 units with a V1 string (whole word, case-insensitive): D1 DEV 0 | D2 DEV MMLU 0 | D2 DEV ARC 0
   report only, without the boundary condition (plain substring): D1 DEV 2 | MMLU 0 | ARC 0
     substring-only hit: books-dev-055 string 'mishes' context 'en with skirmishes and onfalls'
     substring-only hit: fineweb-dev-023 string 'disu' context 'fallen into disuse, it can b'
L4 manifest dev_questions 640 | auditor 640
OK   L1: auditor 0 | SPLIT_MANIFEST authoring_result 0
OK   L2: auditor 0.2 | SPLIT_MANIFEST authoring_result 0.2
OK   L3a: auditor 0 | SPLIT_MANIFEST authoring_result 0
OK   L3b: auditor 0 | SPLIT_MANIFEST authoring_result 0
OK   L4: auditor 0 | SPLIT_MANIFEST authoring_result 0
OK   L5: auditor 0 | SPLIT_MANIFEST authoring_result 0
OK   L6: auditor {'d1_dev': 0, 'd1_dev_token_id_13grams_report_only': 0, 'd2_dev': 0, 'd2_dev_arc': 0} | SPLIT_MANIFEST authoring_result {'d1_dev': 0, 'd1_dev_token_id_13grams_report_only': 0, 'd2_dev': 0}
OK   L7: auditor {'a': 0, 'b': 0, 'c': 0} | SPLIT_MANIFEST authoring_result {'a': 0, 'b': 0, 'c': 0}
OK   L8: auditor {'d1_dev': 0, 'd2_dev': 0, 'd2_dev_arc': 0} | SPLIT_MANIFEST authoring_result {'d1_dev': 0, 'd2_dev': 0}
all L1-L8 DEV parts within limits: True
ITEM2: ALL MATCH
input qwen/tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 manifest aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 equal True
input qwen/tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 manifest d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True
input qwen/vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 manifest ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True
input qwen/merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 manifest 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True
report only: V1 facts generated WITHOUT the Pilot preseed differ from the V1 facts in 150 of 320 facts; canonical 2dc06296dff94d513acf8e8ed23107cdb5d8f2116ebd56731430a8f54049a364
report only: without the preseed L7 (a) would be 0, (b) would be 37
exit=0
```

**与 Executor 是否一致**：**一致**。L1–L8 的 DEV 部分全部等于 SPLIT_MANIFEST 的 authoring_result，全部在上限内。

另有两项补充：
- ARC 备选集的 L6、L8 也都是 0。manifest 中没有这一记录。
- 预置 Pilot 字符串（2.2 第 3 处改动）确实起了作用：不预置时，有 37 个 V1 字符串会对 Pilot 字符串触发 reject_if，320 条 fact 中有 150 条不同。

---

## 项目 3：候选可行性（同 relation、同 stratum、同暴露类别、答案 token 数相同）

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/a3_candidates.py`

**原始输出**（完整）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:36:11Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a3_candidates.py
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
input qwen/tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 manifest aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 equal True
input qwen/tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 manifest d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True
input qwen/vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 manifest ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True
input qwen/merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 manifest 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True
cell (relation/stratum/exposure): facts | distinct K_st | pool (other answers, 4 constraints, K_st) min/max | candidates available incl. own answer min | (K_st, K_qa) pool min
  capital/natural/learned: 30 | K_st [3] | pool 29/29 | candidates 30 | 29
  capital/natural/unread: 10 | K_st [3] | pool 9/9 | candidates 10 | 9
  capital/random/learned: 30 | K_st [6] | pool 29/29 | candidates 30 | 29
  capital/random/unread: 10 | K_st [6] | pool 9/9 | candidates 10 | 9
  currency/natural/learned: 30 | K_st [3] | pool 29/29 | candidates 30 | 29
  currency/natural/unread: 10 | K_st [3] | pool 9/9 | candidates 10 | 9
  currency/random/learned: 30 | K_st [6] | pool 29/29 | candidates 30 | 29
  currency/random/unread: 10 | K_st [6] | pool 9/9 | candidates 10 | 9
  founder/natural/learned: 30 | K_st [3] | pool 29/29 | candidates 30 | 29
  founder/natural/unread: 10 | K_st [3] | pool 9/9 | candidates 10 | 9
  founder/random/learned: 30 | K_st [5] | pool 29/29 | candidates 30 | 29
  founder/random/unread: 10 | K_st [5] | pool 9/9 | candidates 10 | 9
  river/natural/learned: 30 | K_st [3] | pool 29/29 | candidates 30 | 29
  river/natural/unread: 10 | K_st [3] | pool 9/9 | candidates 10 | 9
  river/random/learned: 30 | K_st [6] | pool 29/29 | candidates 30 | 29
  river/random/unread: 10 | K_st [6] | pool 9/9 | candidates 10 | 9
minimum pool (other answers) over all 320 facts: 9 | minimum candidates incl. own answer: 10
cells with a pool of other answers < 4 (protocol IMPLEMENTATION_FAIL rule; includes any cell with < 4 candidates): []
note: protocol 2.5 / Pilot 2.5 rule 'pool < 4 -> IMPLEMENTATION_FAIL' counts the other answers; pool sizes per manifest {'learned': 29, 'unread': 9}
candidates.json: facts 320 keys 320 | lists violating (4 distinct, own answer included, same relation/stratum/exposure, same K_st): 0
position of the true answer among the 4 candidates (report only): {0: 82, 1: 91, 2: 82, 3: 65}
DEV-QA scored sequences n 2560 total ids 78032 mean 30.481 | context+candidate ids != context ids + encode(' '+c): 0 | questions whose 4 scored lengths differ: 0
TRAIN closed-book sequences n 960 total ids 13288 mean 13.842 | prefix+candidate ids != prefix ids + encode(' '+c): 0
TRAIN statements whose answer ids differ from encode(' ' + answer) after prefix(f): 0 of 240
Executor (v1_data_check.txt): DEV-QA n 2560 sum 78032 mean 30.481; TRAIN closed-book n 960 sum 13288 mean 13.842
ITEM3: OK
exit=0
```

**与 Executor 是否一致**：**一致**。
- 最小池为 9（unread），learned 为 29。没有不足 4 个的 cell。Executor 的记录是 "min pool 9, max 29"。
- 16 个 (relation, stratum, exposure) 组合各自只有一个 K_st 值。
- candidates.json 的 320 个候选表全部满足四重约束。
- 在 QA 语境与 TRAIN 闭卷语境中，被打分的 id 等于 `encode(" " + c)`，没有不一致。
- 序列统计与 Executor 相同。

---

## 项目 4：split

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/a4_split.py`

**原始输出**（完整）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:36:54Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a4_split.py
OK   fact_ids unique: got 320 | expected 320
OK   fact_ids not matching E1V1-<L|U>-<relation>-<nat|rnd>-<NN>: got 0 | expected 0
OK   fact_id prefix inconsistent with exposure / relation / stratum fields: got 0 | expected 0
OK   learned ∩ unread: got 0 | expected 0
OK   total facts: got 320 | expected 320
OK   learned: got 240 | expected 240
OK   unread: got 80 | expected 80
  cell capital/natural: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell capital/random: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell currency/natural: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell currency/random: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell founder/natural: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell founder/random: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell river/natural: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  cell river/random: learned 30 (01..30 True) unread 10 (01..10 True) order learned-then-unread True
  stratum natural: facts 160 learned 120 unread 40
  stratum random: facts 160 learned 120 unread 40
OK   train_F rows: got 240 | expected 240
OK   train_F: every learned fact exactly once: got True | expected True
OK   train_F rows of unread facts: got 0 | expected 0
OK   train_F rows not using a TRAIN template: got 0 | expected 0
OK   train_S rows: got 240 | expected 240
OK   train_S fact_id / answer_fact_id of unread facts: got 0 | expected 0
OK   train_S fixed points (fact_id == answer_fact_id): got 0 | expected 0
OK   train_S answer_fact_id outside the fact's cell: got 0 | expected 0
OK   train_S: fact_id and answer_fact_id each a permutation of the learned set: got True | expected True
OK   train_Y rows: got 480 | expected 480
OK   train_Y: every learned fact one Y_ENTITY and one Y_ANSWER: got True | expected True
OK   train_Y rows not using a Y template: got 0 | expected 0
OK   dev_qa rows (320 x 2): got 640 | expected 640
OK   dev_qa: every fact (learned and unread) exactly 2 questions: got True | expected True
OK   dev_qa rows not using a DEV template: got 0 | expected 0
OK   dev_qa distinct (fact_id, template_id): got 640 | expected 640
TEST templates 12 (3 per relation) -> TEST-QA would be 320 x 3 = 960 questions (protocol 5: 960); not generated
OK   TEST templates per relation: got {'capital': 3, 'currency': 3, 'founder': 3, 'river': 3} | expected {'capital': 3, 'currency': 3, 'founder': 3, 'river': 3}
OK   TEST files generated by the auditor: got [] | expected []
OK   D1 DEV windows per domain: got {'books': 100, 'c4': 100, 'fineweb': 100, 'wikitext': 100} | expected {'books': 100, 'c4': 100, 'fineweb': 100, 'wikitext': 100}
OK   D1 DEV doc_ids unique: got 400 | expected 400
OK   D1 DEV doc_ids not of the form <domain>-dev-NNN: got 0 | expected 0
OK   D1 DEV windows with > 256 ids: got 0 | expected 0
OK   D2 DEV MMLU items: got 800 | expected 800
OK   D2 DEV MMLU distinct source_row: got 800 | expected 800
OK   D2 DEV MMLU item numbering 0..799: got True | expected True
OK   D2 DEV MMLU distinct prompts: got 800 | expected 800
OK   D2 DEV ARC items: got 800 | expected 800
OK   D2 DEV ARC distinct source_row: got 800 | expected 800
OK   D2 DEV ARC distinct prompts: got 800 | expected 800
OK   D2 DEV answer letters all in A-D: got True | expected True
ITEM4: ALL MATCH
exit=0
```

**与 Executor 是否一致**：**一致**。
- fact_id 两两互斥，learned 与 unread 交集为 0。每个 cell 30 learned + 10 unread。每个 stratum 120 + 40。
- TRAIN 240 条，S 240 条（无不动点，置换不出 cell），Y 480 条，DEV 640 问。
- D1 DEV 400 个窗口（每领域 100），D2 DEV 800 题。
- 以上均符合协议 2.1、2.3、2.6、7.2。

---

## 项目 5：损伤评测集

**命令**：
- `<S>/venv/bin/python -I -B metrix/e1-v1/audit/a5_damage.py`
- 补充：`a7_hub.py`，向 Hugging Face Hub API 做只读查询；`a8_d2_inputs.py`

**原始输出 a5**（完整）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:34:14Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a5_damage.py
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
input qwen/tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 manifest aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 equal True
input qwen/tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 manifest d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True
input qwen/vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 manifest ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True
input qwen/merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 manifest 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True
V1 strings for L8: 640 distinct lowercase 640
anchor distinct word 13-grams 44255 | token-id 13-grams 59331
OK   eval_sets.jsonl sha256: got 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | expected 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155
OK   parcae tokenizer.json sha256: got e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | expected e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77
eval_sets rows by (domain, split) from row prefixes: {('books', 'dev'): 100, ('books', 'test'): 200, ('c4', 'dev'): 100, ('c4', 'test'): 200, ('fineweb', 'dev'): 100, ('fineweb', 'test'): 200, ('wikitext', 'dev'): 100, ('wikitext', 'test'): 200} | rows without the prefix: 0
OK   D1 books dev rows: got 100 | expected 100
OK   D1 books test rows after skipping the first 25 (Pilot TEST windows): got 175 | expected 175
   books: test rows 200; needed for D1 TEST 100; slack before exclusions 75
OK   D1 c4 dev rows: got 100 | expected 100
OK   D1 c4 test rows after skipping the first 25 (Pilot TEST windows): got 175 | expected 175
   c4: test rows 200; needed for D1 TEST 100; slack before exclusions 75
OK   D1 fineweb dev rows: got 100 | expected 100
OK   D1 fineweb test rows after skipping the first 25 (Pilot TEST windows): got 175 | expected 175
   fineweb: test rows 200; needed for D1 TEST 100; slack before exclusions 75
OK   D1 wikitext dev rows: got 100 | expected 100
OK   D1 wikitext test rows after skipping the first 25 (Pilot TEST windows): got 175 | expected 175
   wikitext: test rows 200; needed for D1 TEST 100; slack before exclusions 75
D1 DEV kept 400 | excluded {'L8': 0, 'L6': 0} []
D1 DEV kept per domain {'books': 100, 'c4': 100, 'fineweb': 100, 'wikitext': 100}
OK   general_dev.jsonl canonical sha256: got e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281 | expected e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281
OK   general_dev.jsonl = DAMAGE_MANIFEST d1.dev.authoring.canonical_sha256: got e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281 | expected e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281
OK   D1 DEV kept: got 400 | expected 400
OK   D1 DEV excluded: got 0 | expected 0
D1 DEV ids per window {'n': 400, 'sum': 99557, 'mean': 248.893, 'min': 172, 'median': 253.0, 'max': 256}
OK   D1 DEV ids_per_window_mean: got 248.893 | expected 248.893
report only: D1 DEV rows whose full (untruncated) decoded text contains a V1 string as a whole word: 0
report only: V1 D1 DEV uses all 100 dev rows per domain, so it contains the 100 Pilot D1 DEV windows (first 25 dev rows per domain); both are DEV
letter tokens {'A': [362], 'B': [425], 'C': [356], 'D': [422]}
OK   ' A'..' D' single-token ids: got {'A': [362], 'B': [425], 'C': [356], 'D': [422]} | expected {'A': [362], 'B': [425], 'C': [356], 'D': [422]}
OK   MMLU validation sha256: got 66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef | expected 66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef
OK   MMLU test sha256 (whole file): got 74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7 | expected 74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7
OK   MMLU validation rows: got 1531 | expected 1531
OK   MMLU test rows (parquet footer only): got 14042 | expected 14042
MMLU validation columns ['answer', 'choices', 'question', 'subject']
MMLU validation rows by number of choices {4: 1531} | answers outside 0-3 0
MMLU D2 DEV items 800 | rows visited 800 | excluded {}
OK   d2_dev.jsonl (MMLU) canonical sha256: got f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be | expected f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be
OK   d2_dev.jsonl (MMLU) = DATA_MANIFEST files.d2_dev.jsonl.mmlu: got f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be | expected f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be
OK   MMLU DEV items: got 800 | expected 800
OK   MMLU DEV excluded: got 0 | expected 0
OK   MMLU DEV rows_visited: got 800 | expected 800
OK   MMLU DEV subjects: got 57 | expected 57
MMLU DEV answer letters {'A': 197, 'B': 195, 'C': 199, 'D': 209}
MMLU DEV context ids per item (chat(p) + 'The answer is') {'n': 800, 'sum': 107377, 'mean': 134.221, 'min': 51, 'median': 103.0, 'max': 781}
OK   MMLU DEV context_ids_mean: got 134.221 | expected 134.221
MMLU validation rows not used by D2 DEV: 731
OK   ARC ARC-Challenge/validation-00000-of-00001.parquet sha256: got 395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05 | expected 395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05
OK   ARC ARC-Challenge/validation-00000-of-00001.parquet rows: got 299 | expected 299
OK   ARC ARC-Easy/validation-00000-of-00001.parquet sha256: got ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74 | expected ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74
OK   ARC ARC-Easy/validation-00000-of-00001.parquet rows: got 570 | expected 570
OK   ARC ARC-Challenge/test-00000-of-00001.parquet sha256 (whole file): got 62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9 | expected 62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9
OK   ARC ARC-Challenge/test-00000-of-00001.parquet rows (parquet footer only): got 1172 | expected 1172
OK   ARC ARC-Easy/test-00000-of-00001.parquet sha256 (whole file): got 4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177 | expected 4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177
OK   ARC ARC-Easy/test-00000-of-00001.parquet rows (parquet footer only): got 2376 | expected 2376
ARC validation rows (Challenge then Easy) 869 | by number of labels {4: 862, 3: 4, 5: 3} | label sets [('1', '2', '3', '4'), ('A', 'B', 'C'), ('A', 'B', 'C', 'D'), ('A', 'B', 'C', 'D', 'E')]
ARC D2 DEV items 800 | rows visited 806 | excluded {'not_4_choices_or_answer': 6}
OK   d2_dev.jsonl (ARC) canonical sha256: got 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32 | expected 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32
OK   d2_dev.jsonl (ARC) = DATA_MANIFEST files.d2_dev.jsonl.arc: got 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32 | expected 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32
OK   ARC DEV items: got 800 | expected 800
OK   ARC DEV excluded not_4_choices: got 6 | expected 6
ARC DEV other exclusions (L8, L6): {}
ARC validation rows remaining after DEV: 63 | 4-choice rows in DEV source 862
ARC DEV context ids per item {'n': 800, 'sum': 66391, 'mean': 82.989, 'min': 50, 'median': 78.0, 'max': 182}
OK   ARC DEV context_ids_mean: got 82.989 | expected 82.989
ARC DEV answer letters {'A': 206, 'B': 202, 'C': 205, 'D': 187}
written general_dev.jsonl byte_sha256 e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281
written d2_dev.jsonl byte_sha256 f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be
written d2_dev_arc.jsonl byte_sha256 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32
ITEM5: ALL MATCH
exit=0
```

**原始输出 a7**（完整）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:40:49Z; read-only Hugging Face Hub API queries via curl
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a7_hub.py
OK   Hub cais/mmlu@c30699e8 all/validation-00000-of-00001.parquet LFS oid = manifest sha256: got 66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef | expected 66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef
OK   Hub cais/mmlu@c30699e8 all/test-00000-of-00001.parquet LFS oid = manifest sha256: got 74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7 | expected 74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7
OK   Hub allenai/ai2_arc@210d026f ARC-Challenge/validation-00000-of-00001.parquet LFS oid = manifest sha256: got 395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05 | expected 395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05
OK   Hub allenai/ai2_arc@210d026f ARC-Easy/validation-00000-of-00001.parquet LFS oid = manifest sha256: got ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74 | expected ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74
OK   Hub allenai/ai2_arc@210d026f ARC-Challenge/test-00000-of-00001.parquet LFS oid = manifest sha256: got 62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9 | expected 62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9
OK   Hub allenai/ai2_arc@210d026f ARC-Easy/test-00000-of-00001.parquet LFS oid = manifest sha256: got 4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177 | expected 4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177
OK   Hub Qwen/Qwen3-1.7B@70d244cc tokenizer.json LFS oid = manifest sha256: got aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 | expected aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4
OK   Hub Qwen/Qwen3-1.7B@70d244cc tokenizer_config.json (not LFS) git blob id = git blob sha1 of the local file whose sha256 is the manifest value: got 417d038a63fa3de29cfde265caedae14d1a58d92 | expected 417d038a63fa3de29cfde265caedae14d1a58d92
OK      local tokenizer_config.json sha256 = manifest: got d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 | expected d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101
OK   Hub Qwen/Qwen3-1.7B@70d244cc vocab.json (not LFS) git blob id = git blob sha1 of the local file whose sha256 is the manifest value: got 4783fe10ac3adce15ac8f358ef5462739852c569 | expected 4783fe10ac3adce15ac8f358ef5462739852c569
OK      local vocab.json sha256 = manifest: got ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 | expected ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910
OK   Hub Qwen/Qwen3-1.7B@70d244cc merges.txt (not LFS) git blob id = git blob sha1 of the local file whose sha256 is the manifest value: got 31349551d90c7606f325fe0f11bbb8bd5fa0d7c7 | expected 31349551d90c7606f325fe0f11bbb8bd5fa0d7c7
OK      local merges.txt sha256 = manifest: got 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 | expected 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5
OK   Hub SandyResearch/parcae-tokenizer@6247b5d0 tokenizer.json (not LFS) git blob id = git blob sha1 of the local file whose sha256 is the manifest value: got 3ff4f5afe2dfdf3ce41b55073f68ee89d79cb74f | expected 3ff4f5afe2dfdf3ce41b55073f68ee89d79cb74f
OK      local tokenizer.json sha256 = manifest: got e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | expected e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77
OK   Hub SandyResearch/fineweb-edu-shuffled@4d1138c0 data/sample-100BT/train/shard_00000.parquet LFS oid = manifest sha256: got 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | expected 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22
OK   Hub cais/mmlu revision resolves to itself: got c30699e8356da336a370243923dbaf21066bb9fe | expected c30699e8356da336a370243923dbaf21066bb9fe
OK   Hub cais/mmlu@c30699e8 cardData.license: got mit | expected mit
OK   Hub allenai/ai2_arc revision resolves to itself: got 210d026faf9955653af8916fad021475a3f00453 | expected 210d026faf9955653af8916fad021475a3f00453
OK   Hub allenai/ai2_arc@210d026f cardData.license: got cc-by-sa-4.0 | expected cc-by-sa-4.0
OK   Hub Qwen/Qwen3-1.7B revision resolves to itself: got 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e | expected 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
OK   Hub Qwen/Qwen3-1.7B@70d244cc cardData.license: got apache-2.0 | expected apache-2.0
ARC ARC-Challenge/validation-00000-of-00001.parquet: rows 299 by number of options {3: 3, 4: 295, 5: 1}
ARC ARC-Easy/validation-00000-of-00001.parquet: rows 570 by number of options {3: 1, 4: 567, 5: 2}
ARC DEV source total by number of options {3: 4, 4: 862, 5: 3}: 4-option rows 862, other 7
SUPPLEMENT: ALL MATCH
exit=0
```

**原始输出 a8**（完整）：
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:41:59Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a8_d2_inputs.py
[transformers] PyTorch was not found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
input qwen/tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 manifest aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 equal True
input qwen/tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 manifest d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True
input qwen/vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 manifest ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True
input qwen/merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 manifest 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True
d2_dev.jsonl: items 800 | (item, letter) pairs where the scored continuation is not exactly the single letter token after the context ids: 0 | report only: items with repeated option texts 2
   chat template ends with: 'end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\nThe answer is'
d2_dev_arc.jsonl: items 800 | (item, letter) pairs where the scored continuation is not exactly the single letter token after the context ids: 0 | report only: items with repeated option texts 0
   chat template ends with: 'end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\nThe answer is'
SUPPLEMENT D2 inputs: done
exit=0
```

**与 Executor 是否一致**：哈希、数量、排除数**全部一致**。
- D1 DEV：general_dev.jsonl e8350160…，400 个窗口，排除 0。
- D2 DEV：MMLU f40c146a…，800 题，排除 0，访问 800 行，57 个学科；ARC 1ea77c8a…，800 题，排除 not_4_choices 6 题。
- eval_sets 的 test 行按行首计数：每领域 200 行，跳过前 25 行后剩 175 行，与协议和 manifest 相同。
- D2 来源文件的 sha256 与行数（test 只读文件尾）：MMLU 1531 / 14042，ARC 299 / 570 / 1172 / 2376，全部相同。Hub 上的 LFS oid、revision、许可证也独立核对一致。

**不一致**：协议中两句关于 ARC DEV 来源的描述性数字与数据不符，见下方问题 B1。manifest 中的 excluded = 6 本身是对的。

---

## 项目 6：协议与 JSON 中与数据有关的部分是否一致

**命令**：`<S>/venv/bin/python -I -B metrix/e1-v1/audit/a6_consistency.py`

**原始输出**：完整 stdout 在 `stdout/a6_consistency.txt`（sha256 65996f5c…fd95）。下面逐行原样照录，只有超过 400 字符的 6 行被截断，并标有「…[本行截断；全文见 stdout 文件]」，这 6 行都是 OK 行。
```
# host: vm (Claude Code cloud container, CPU only, no GPU, torch not installed); 2026-11-28T09:39:25Z
$ /tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/venv/bin/python -I -B metrix/e1-v1/audit/a6_consistency.py
64-hex values in the protocol: 12
  0fc5ad819500… in JSON: 1 ['DATA_MANIFEST.json:name_generation.expected_facts_canonical_sha256']
  1ea77c8adeb8… in JSON: 2 ['DATA_MANIFEST.json:files.d2_dev.jsonl.reference_canonical_sha256.arc', 'DAMAGE_MANIFEST.json:d2.datasets.arc.authoring_dev.canonical_sha256']
  2b52411326c2… in JSON: 1 ['SPLIT_MANIFEST.json:template_freeze.template_set_sha256']
  406c8801c5b6… in JSON: 1 ['DATA_MANIFEST.json:name_generation.preseed.pilot_facts_canonical_sha256']
  66cdf0b090cc… in JSON: 1 ['DAMAGE_MANIFEST.json:d2.datasets.mmlu.dev_source.sha256']
  74a41822ce7d… in JSON: 1 ['DAMAGE_MANIFEST.json:d2.datasets.mmlu.test_source.sha256']
  79600769eef1… in JSON: 2 ['DATA_MANIFEST.json:files.candidates.json.reference_canonical_sha256', 'SPLIT_MANIFEST.json:candidates.candidate_mapping_sha256']
  7ac254f6e87e… in JSON: 2 ['DATA_MANIFEST.json:s_permutation.expected_train_S_canonical_sha256', 'DATA_MANIFEST.json:files.train_S.jsonl.reference_canonical_sha256']
  82314e6b4a59… in JSON: 1 ['DATA_MANIFEST.json:files.train_Y.jsonl.reference_canonical_sha256']
  8828bc4fcc5a… in JSON: 1 ['DATA_MANIFEST.json:anchor_text.decoded_texts_canonical_sha256']
  e83501604649… in JSON: 2 ['DATA_MANIFEST.json:files.general_dev.jsonl.reference_canonical_sha256', 'DAMAGE_MANIFEST.json:d1.dev.authoring.canonical_sha256']
  f40c146a3da5… in JSON: 2 ['DATA_MANIFEST.json:files.d2_dev.jsonl.reference_canonical_sha256.mmlu', 'DAMAGE_MANIFEST.json:d2.datasets.mmlu.authoring_dev.canonical_sha256']
40-hex values (commits / revisions) in the protocol: ['210d026faf9955653af8916fad021475a3f00453', '6e03468956208c422d0d41c08edaaf116166338c', '70d244cc86ccca08cf5af4e1e306ecf908b1ad5e', '87a244db28a901f9e89282b50df76778ab5c2887', 'c30699e8356da336a370243923dbaf21066bb9fe']
  210d026faf9955653af8916fad021475a3f00453 in JSON: ['DAMAGE_MANIFEST.json:d2.datasets.arc.revision'] | git cat-file -t: not a local object
  6e03468956208c422d0d41c08edaaf116166338c in JSON: ['DATA_MANIFEST.json:origin.start_commit', 'SPLIT_MANIFEST.json:origin.start_commit', 'DOSE_SPACE.json:origin.start_commit'] | git cat-file -t: commit
  70d244cc86ccca08cf5af4e1e306ecf908b1ad5e in JSON: ['DATA_MANIFEST.json:model.revision', 'DATA_MANIFEST.json:model.tokenizer.revision'] | git cat-file -t: not a local object
  87a244db28a901f9e89282b50df76778ab5c2887 in JSON: ['DATA_MANIFEST.json:origin.pilot_protocol', 'SPLIT_MANIFEST.json:origin.pilot_protocol', 'DOSE_SPACE.json:origin.pilot_protocol'] | git cat-file -t: commit
  c30699e8356da336a370243923dbaf21066bb9fe in JSON: ['DAMAGE_MANIFEST.json:d2.datasets.mmlu.revision'] | git cat-file -t: not a local object
OK   abbreviated 8816fe5a…a155 expands to exactly one JSON value: got 1 | expected 1
OK   abbreviated c30699e8… matches exactly one JSON value: got 1 | expected 1
OK   abbreviated 210d026f… matches exactly one JSON value: got 1 | expected 1
protocol seed assignments (line, name, value): [(31, 'DATA_SEED', 20261128), (31, 'CANDIDATE_SEED', 20261129), (31, 'BOOTSTRAP_SEED', 20261130), (62, 'DATA_SEED', 20261128), (64, 'DATA_SEED', 20261110), (78, 'CANDIDATE_SEED', 20261129)]
  value differing from DATA_MANIFEST at line 64: DATA_SEED = 20261110 | Pilot regeneration context: True
OK   seed assignments differing from DATA_MANIFEST outside the Pilot regeneration sentence: got [] | expected []
protocol section 0 seeds {'DATA_SEED': 20261128, 'CANDIDATE_SEED': 20261129, 'BOOTSTRAP_SEED': 20261130}
OK   DATA_SEED protocol vs DATA_MANIFEST: got 20261128 | expected 20261128
OK   CANDIDATE_SEED protocol vs DATA_MANIFEST: got 20261129 | expected 20261129
OK   BOOTSTRAP_SEED protocol vs DATA_MANIFEST: got 20261130 | expected 20261130
OK   TRAIN_SEEDS protocol vs DATA_MANIFEST: got True | expected True
OK   DOSE_SPACE training seeds: got [101, 202, 303] | expected [101, 202, 303]
OK   DOSE_SPACE Z0 / P+ seeds: got ([101, 202, 303], [101, 202, 303]) | expected ([101, 202, 303], [101, 202, 303])
OK   DAMAGE_MANIFEST bootstrap seed text: got BOOTSTRAP_SEED = 20261130 | expected BOOTSTRAP_SEED = 20261130
OK   seeds differ from Pilot (20261110-20261112): got set() | expected set()
OK   CANDIDATE_SEED text in SPLIT_MANIFEST: got CANDIDATE_SEED = 20261129 | expected CANDIDATE_SEED = 20261129
  name_generation.answer_token_length_rule differs from Pilot: Pilot {"survey": "from the start of the answer stream, the first 400 draws that satisfy the form rules (reject_if and the anchor rule are NOT applied; repeats count); | V1 {"survey": "from the start of the answer stream, the first 400 draws that satisfy the form rules (reject_if and the anchor rule are NOT applied; repeats count);
  name_generation.authoring_draws differs from Pilot: Pilot null | V1 "reports/authoring/v1_data_check.txt (entity 40-83, answer 80-270 draws per cell)"
  name_generation.changes_from_pilot differs from Pilot: Pilot null | V1 ["DATA_SEED 20261128", "40 accepted per role and cell (30 learned + 10 unread)", "accepted set pre-seeded with the 320 Pilot strings"]
  name_generation.entity_procedure differs from Pilot: Pilot "draw from the entity stream in order; accept draws that satisfy the form rules, reject_if and the anchor rule, until 20 are accepted" | V1 "draw from the entity stream in order; accept draws that satisfy the form rules, reject_if and the anchor rule, until 40 are accepted"
  name_generation.expected_facts_canonical_sha256 differs from Pilot: Pilot "406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97" | V1 "0fc5ad819500e8a9f56771405af67d0fa71bafabba25bf8f4c3e5b6d684e01f4"
  name_generation.order differs from Pilot: Pilot "cells in the order relation (capital, currency, founder, river) x stratum (natural, random); within a cell entities first, then answers; within a role the firs | V1 "cells in the order relation (capital, currency, founder, river) x stratum (natural, random); within a cell entities first, then answers; within a role the firs
  name_generation.preseed differs from Pilot: Pilot null | V1 {"rule": "before the first draw the accepted set holds the 320 entity and answer strings of the E1-PILOT facts, so reject_if also rejects strings equal or close
  name_generation.reference_implementation differs from Pilot: Pilot "metrix/e1-pilot/reports/round2/names.py" | V1 "metrix/e1-v1/reports/authoring/v1_data_check.py (Names.build)"
OK   name_generation rule fields equal to Pilot (natural, random, draw, streams, scope, anchor rule, token counts, max draws): got [] | expected []
OK   s_permutation rule equal to Pilot apart from counts: got per cell, a derangement of the 30 learned answers drawn with rng_rule(DATA_SEED, 's-permutation:<relation>:<stratum>'); redraw until no fixed point | expected per cell, a derangement of the 30 learned answers drawn with rng_rule(DATA_SEED, 's-permutation:<relation>:<stratum>'); redraw until no fixed point
OK   templates identical to Pilot SPLIT_MANIFEST: got True | expected True
OK   template_freeze normalization identical to Pilot: got replace {E} by <ENTITY> and {A} by <ANSWER>, lowercase, replace every character outside [a-z0-9<> ] by a space, collapse spaces | expected replace {E} by <ENTITY> and {A} by <ANSWER>, lowercase, replace every character outside [a-z0-9<> ] by a space, collapse spaces
OK   candidates.way identical to Pilot: got 4 | expected 4
OK   candidates.pool identical to Pilot: got answers of the other facts with the same relation, stratum and exposure class (learned / unread) | expected answers of the other facts with the same relation, stratum and exposure class (learned / unread)
OK   candidates.draw identical to Pilot: got 3 distractors without replacement and the order of the 4 candidates from rng_rule(CANDIDATE_SEED, 'cand:<fact_id>') | expected 3 distractors without replacement and the order of the 4 candidates from rng_rule(CANDIDATE_SEED, 'cand:<fact_id>')
OK   candidates.shared_by identical to Pilot: got all templates, splits and arms of the fact | expected all templates, splits and arms of the fact
OK   candidates.duplicates identical to Pilot: got forbidden | expected forbidden
OK   candidates.pool_too_small identical to Pilot: got a distractor pool with fewer than 4 answers: IMPLEMENTATION_FAIL; no synthetic distractors are generated (protocol 2.5; supplement b, Task Order V1.2) | expected a distractor pool with fewer than 4 answers: IMPLEMENTATION_FAIL; no synthetic distractors are generated (protocol 2.5; supplement b, Task Order V1.2)
OK   candidates.exposure_matching identical to Pilot: got every candidate of a learned fact occurs exactly once in the training corpus of F, L, A, S and Y; every candidate of an unread fact occurs zero times | expected every candidate of a learned fact occurs exactly once in the training corpus of F, L, A, S and Y; every candidate of an unread fact occurs zero times
OK   hashing rules identical to Pilot: got ({'encoding': 'UTF-8', 'serialization': "json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)", 'jsonl': "one canonical object per line, joined by '\\n', one final '\\n'", 'hash': 'SHA-256', 'byte_sha256': 'SHA-256 of the file bytes exactly as stored (LF newlines)', 'canonical_sha256': 'SHA-256 of the canonical seria …[本行截断；全文见 stdout 文件]
OK   anchor_text.source identical to Pilot: got SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de, data/sample-100BT/train/shard_00000.parquet (sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22) | expected SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de, data/sample-100BT/train/shard_00000.parquet (sha256 6a3450ea745ee6b68 …[本行截断；全文见 stdout 文件]
OK   anchor_text.selection identical to Pilot: got first 512 documents in file order with at least 600 characters | expected first 512 documents in file order with at least 600 characters
OK   anchor_text.truncate_to_model_tokens identical to Pilot: got 128 | expected 128
OK   anchor_text.document_rule identical to Pilot: got each document has at most 128 tokens of the protocol tokenizer (the first 128); a document with fewer tokens is used at its full length | expected each document has at most 128 tokens of the protocol tokenizer (the first 128); a document with fewer tokens is used at its full length
OK   anchor_text.decoded_texts_canonical_sha256 identical to Pilot: got 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | expected 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408
OK   D1 source_file identical to Pilot general_text: got research/mini_mythos/stage1/results/r1/eval_sets.jsonl | expected research/mini_mythos/stage1/results/r1/eval_sets.jsonl
OK   D1 source_file_sha256 identical to Pilot general_text: got 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | expected 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155
OK   D1 decode_with identical to Pilot general_text: got SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c, special tokens skipped | expected SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c, special tokens skipped
OK   D1 decode_tokenizer_json_sha256 identical to Pilot general_text: got e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | expected e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77
OK   D1 window_rule identical to Pilot general_text: got each window has at most 256 tokens of the protocol tokenizer (the first 256); a window with fewer tokens is used at its full length; the ids fed to the model are these truncated ids themselves, not decoded and re-encoded; n_w (protocol section 5) is their number | expected each window has at most 256 tokens of the protocol tokenizer (the fir …[本行截断；全文见 stdout 文件]
OK   model / tokenizer identical to Pilot: got ('Qwen/Qwen3-1.7B', '70d244cc86ccca08cf5af4e1e306ecf908b1ad5e', {'tokenizer.json': 'aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4', 'tokenizer_config.json': 'd5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101', 'vocab.json': 'ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910', 'merges.txt': '8831e4f1a044 …[本行截断；全文见 stdout 文件]
OK   320 = 240 + 80 in protocol 2.1: got True | expected True
OK   per cell 30 + 10 (protocol vs DATA_MANIFEST): got True | expected True
OK   pool 29 / 9 (protocol 2.5 vs SPLIT_MANIFEST): got True | expected True
OK   Y 480 sentences (protocol 2.6 vs DATA_MANIFEST files): got True | expected True
OK   Y/F authoring numbers protocol vs manifest: got True | expected True
OK   D1 DEV 400 / D2 DEV 800 (protocol 7.2 vs DAMAGE_MANIFEST): got True | expected True
OK   D1 TEST 175 per domain (protocol vs DAMAGE_MANIFEST): got True | expected True
OK   MMLU rows (protocol vs DAMAGE_MANIFEST): got True | expected True
OK   ARC rows (protocol vs DAMAGE_MANIFEST): got True | expected True
protocol 7.1 ARC sentence: 只用恰好 4 个选项的题(撰写时 DEV 来源中 6 题不是 4 个选项)
protocol 15 ARC sentence: ARC 的 DEV 来源只有 869 题(其中 863 题为 4 个选项),抽 800 题后余量很小 
DAMAGE_MANIFEST arc.authoring_dev.excluded: {'not_4_choices': 6} (see a5_damage.txt: DEV source rows by number of labels)
OK   D2 letter ids protocol vs DAMAGE_MANIFEST: got True | expected True
OK   D2 prompt instruction text protocol vs DAMAGE_MANIFEST: got True | expected True
OK   D2 seeds/purposes protocol vs manifest: got True | expected True
OK   ladder_steps = 30 * ladder_passes: got [30, 60, 90, 120, 180, 240, 330, 480, 690, 960] | expected [30, 60, 90, 120, 180, 240, 330, 480, 690, 960]
OK   ladder in protocol 6.3: got True | expected True
OK   steps per pass: 240/8 and 480/16: got (30, 30) | expected (30, 30)
OK   anchor schedule covers the longest run (960 steps): got 960 | expected 960
OK   d0 = 11 passes in the ladder: got True | expected True
OK   manifest hash 'facts list' written in the protocol: got True | expected True
OK   manifest hash 'pilot facts' written in the protocol: got True | expected True
OK   manifest hash 'candidates' written in the protocol: got True | expected True
OK   manifest hash 'train_S' written in the protocol: got True | expected True
OK   manifest hash 'train_Y' written in the protocol: got True | expected True
OK   manifest hash 'anchor decoded' written in the protocol: got True | expected True
OK   manifest hash 'template set' written in the protocol: got True | expected True
OK   manifest hash 'general_dev' written in the protocol: got True | expected True
OK   manifest hash 'd2_dev mmlu' written in the protocol: got True | expected True
OK   manifest hash 'd2_dev arc' written in the protocol: got True | expected True
OK   manifest hash 'mmlu validation file' written in the protocol: got True | expected True
OK   manifest hash 'mmlu test file' written in the protocol: got True | expected True
reference hashes present only in DATA_MANIFEST (protocol refers to DATA_MANIFEST.json: files): {'train_F.jsonl': False, 'dev_qa.jsonl': False, 'facts.jsonl': False, 'anchor_text.jsonl': False}
OK   candidate hash DATA_MANIFEST vs SPLIT_MANIFEST: got 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3 | expected 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3
OK   train_S hash DATA_MANIFEST files vs s_permutation: got 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6 | expected 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6
OK   general_dev hash DATA_MANIFEST vs DAMAGE_MANIFEST: got e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281 | expected e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281
OK   d2_dev hashes DATA_MANIFEST vs DAMAGE_MANIFEST: got {'mmlu': 'f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be', 'arc': '1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32'} | expected {'mmlu': 'f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be', 'arc': '1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32'}
OK   anchor file hash DATA_MANIFEST files vs anchor_text.file_canonical_sha256_authoring: got 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5 | expected 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5
OK   L-check authoring results DATA_MANIFEST pilot_disjointness vs SPLIT L7: got 0 | expected 0
OK   L8 applies_to (SPLIT) = the four damage files: got ['general_dev', 'general_test', 'd2_dev', 'd2_test'] | expected ['general_dev', 'general_test', 'd2_dev', 'd2_test']
L6 test_part.count text (SPLIT_MANIFEST): number of distinct shared word 13-grams across all documents: 13-grams are taken within each document (each anchor document, each window), never across documents; the word 13-grams of the 512 anchor documents are merged into one set, those of all general_test.jsonl windows into another, and the number of distinct elements of their intersection is counted
L6 test_part.pairs (SPLIT_MANIFEST): ['anchor_text vs general_test.jsonl', 'anchor_text vs d2_test.jsonl']
git HEAD 6e03468956208c422d0d41c08edaaf116166338c | branch metrix-e1-v1-protocol-v1
git log -1 6e03468…: 6e03468956208c422d0d41c08edaaf116166338c metrix: E1-PILOT report erratum (Review Gate ruling 2026-11-28, A1-A5), review record, findings registered Ruling relayed by the Owner (items A1-A5); documents only, no training, evaluation, GPU use or TEST access (Claude Code cloud container, CPU only). - reports/PILOT_FINAL_REPORT.md: Gate 0 and T1-T3 threshold column replaced by th …[本行截断；全文见 stdout 文件]
git log -1 87a244d…: 87a244db28a901f9e89282b50df76778ab5c2887 metrix: E1-PILOT round 9 v1.1 freeze commit (protocol errata 1a-1e, metrix/CLAUDE.md 2a-2c, data-auditor TEST rule)
OK   Pilot PROTOCOL_FROZEN mentions 87a244db…: got True | expected True
OK   Pilot protocol at HEAD equal to Pilot protocol at the v1.1 freeze commit: got True | expected True
OK   Pilot SPLIT_MANIFEST templates at freeze commit = V1 templates: got True | expected True
OK   staged changes outside metrix/e1-v1/: got [] | expected []
OK   index entries equal tree 0e3dc49e… (git ls-files -s vs git ls-tree -r): got True | expected True
index entries 7229 | tree entries 7229
ITEM6: ALL MATCH
exit=0
```

**与 Executor 是否一致**：协议与四个 JSON 在数据相关部分**一致**：
- 种子：第 64 行的 20261110 是重新生成 Pilot fact 时用的，属于正当用法。
- 数量与规则文字：名字生成、S、模板、候选、哈希规则、锚文本、D1 来源都与 Pilot manifest 相同，只有列明的三处改动不同。
- 协议中出现的 12 个全长哈希都能在 JSON 中找到。
- 起点提交与 Pilot 冻结提交都存在。暂存改动只在 metrix/e1-v1/ 内。

**不一致**：B1。脚本把这两句原文打印了出来，但没有判定；真实数值来自 a5 与 a7 的输出。

---

## 问题清单（每项注明是否影响：数据 / 指标 / 门槛 / 可复现性 / iso-acquisition 匹配 / 损伤测量）

**B1（按定义判 BLOCK 的唯一一项）：协议中 ARC DEV 来源的两个数字与数据不符。**
- 原句一，第 7.1 节：「只用恰好 4 个选项的题(撰写时 DEV 来源中 6 题不是 4 个选项)」
- 原句二，第 15 节第 2 行：「ARC 的 DEV 来源只有 869 题(其中 863 题为 4 个选项),抽 800 题后余量很小」
- 实际数据（a5、a7）：DEV 来源 869 行中，4 个选项的 862 行，不是 4 个选项的 **7** 行。其中 Challenge validation 有 3 行是 3 个选项、1 行是 5 个选项；Easy validation 有 1 行是 3 个选项、2 行是 5 个选项。
- 「6」是按打乱顺序访问到第 806 行、凑满 800 题时排除的行数，所以 DAMAGE_MANIFEST 的 `arc.authoring_dev.excluded.not_4_choices = 6` 作为排除数是对的，但协议把它写成了「DEV 来源中 6 题」。863 看起来是由 869 − 6 推出来的，应为 862。800 题之外可用的 4 选项题有 62 题，不是 63 题。
- 影响：数据否（d2_dev_arc 的哈希已重现）；指标否；门槛否；可复现性否（可执行的规则没有歧义）；iso 否；损伤测量否。它只影响第 15 节待决第 2 项（Owner 选择 D2）的事实依据，「余量很小」这一结论不变。
- 按 Owner 的修改规则，这一项是否修改，由 Executor 与 Review Gate 按规则处理。

**以下各项不构成不一致，只登记：**

- **M1（证据不完整）**：Executor 的 `v1_data_check.txt` 有两行打印了 ok 却没有数字：「CHECK L6 anchor vs D2 DEV word 13-grams ok」与「CHECK L8 D2 DEV items containing a V1 string ok」。它也没有 ARC DEV 的 L6、L8 行。但 SPLIT_MANIFEST 记录 d2_dev = 0，协议 7.1 也写明 MMLU 与 ARC 都是 0。我独立算得 MMLU 0/0、ARC 0/0，数值正确。六类影响全部为否，只是记录不完整。
- **M2（规则文字有歧义）**：L8 的「其文本」对 D1 窗口没有定义清楚：可以指窗口的 text（256 个 id 的解码），也可以指整篇源文档。DEV 部分按两种读法都是 0（a5 中「full (untruncated)」一行为 0）。影响可复现性与 D1 TEST 的数据：只有当某个 V1 字符串只出现在 TEST 文档第 256 个 token 之后，两种实现才会排除不同的窗口。概率低，但是一个潜在的分歧点。
- **M3（规则文字不完整）**：SPLIT_MANIFEST 中 L6 的 `test_part.count` 只写了「general_test.jsonl 的窗口」，而 pairs 里还列了 d2_test，没有说明 D2 是单独成一个集合计数，还是与 D1 合并计数。影响可复现性，范围仅限 ST10 中 Executor 与 auditor 两个计数是否相等。由于生成时已经排除了重叠，两种口径都应为 0。低。
- **M4（字段含义靠实现与哈希确定）**：以下字段只写了「沿用 Pilot 第 2.7 节与其实现格式」，文字中没有定义：
  - anchor_text.jsonl 的 `doc`、`source_row`（从 0 起的 parquet 行号）；
  - general_dev 的 `text`（= `tokenizer.decode(ids)`，默认参数）；
  - d2 的 `item`、`source_row`（ARC 为 Challenge validation 之后接 Easy validation 的序号）；
  - facts 的 `exposure` 取值（learned / unread）。

  我按自然读法实现，全部与参考哈希相同，所以 DEV 文件已被哈希固定。TEST 文件没有参考哈希，沿用同样的格式。影响可复现性（只读文字能否实现），已由 DEV 的哈希缓解。
- **M5**：协议第 0 节用代码位置（`metrix/e1-pilot/src/metrix_e1/data.py: _ROW_HEAD`）来定义 TEST 行首的匹配方式，文字中没有写出前缀本身。实际前缀为 `{"domain": "<d>", "split": "<s>", `，1200 行全部符合。六类影响全部为否。
- **M6（观察）**：MMLU DEV 的 800 题中有 2 题存在重复的选项文本。这是数据集本身的性质，不违反任何规则。对损伤测量的影响可以忽略（单题噪声），不建议修改。
- **M7（流程，交 Review Gate）**：
  - 本轮的路径对应（定义文件写 e1-pilot/audit，本轮用 e1-v1/audit）。
  - metrix/CLAUDE.md 第 5 节第 5 条规定审查原文存到 `metrix/e1-pilot/reviews/`，与红线 3 冲突，而 V1 协议第 16 节写的是 `reviews/`（相对 e1-v1）。

  六类影响全部为否。
- **M8（披露）**：见第 0 节，`git write-tree` 运行过一次。

**正面结果**：
- 预置 Pilot 字符串确实生效（不预置时 L7b 为 37）。
- D1 的 fineweb 窗口来自 SandyResearch/fineweb-edu-shuffled@4d1138c0 的 `data/val/train/` 分片（据 `research/mini_mythos/stage1/results/r1/data_lock.json`），锚文本来自同一仓库的 `data/sample-100BT/train/shard_00000.parquet`。两者是不同的文件、同一个来源，所以 same / diff 的划分成立。
- 每领域在跳过 Pilot TEST 行之后还有 175 行，取 100 行之前有 75 行的余量。

---

## git status --short（运行全部脚本之后的原始输出）
```
A  metrix/e1-v1/DAMAGE_MANIFEST.json
A  metrix/e1-v1/DATA_MANIFEST.json
A  metrix/e1-v1/DOSE_SPACE.json
A  metrix/e1-v1/METRIX_E1V1_PROTOCOL.md
A  metrix/e1-v1/SPLIT_MANIFEST.json
A  metrix/e1-v1/SUBMISSION_NOTE.md
A  metrix/e1-v1/reports/authoring/build_manifests.py
A  metrix/e1-v1/reports/authoring/compute_estimate.py
A  metrix/e1-v1/reports/authoring/compute_estimate.txt
A  metrix/e1-v1/reports/authoring/d2_dataset_metadata.txt
A  metrix/e1-v1/reports/authoring/v1_data_check.py
A  metrix/e1-v1/reports/authoring/v1_data_check.txt
A  metrix/e1-v1/reports/authoring/v1_data_check_repeat.txt
A  metrix/e1-v1/reports/pilot_erratum/push_erratum_commit.txt
A  metrix/e1-v1/tasks/E1V1_AUTHORING_OWNER_MESSAGE.md
A  metrix/e1-v1/tasks/E1V1_PROTOCOL_TASK_ORDER_V1.md
?? metrix/e1-v1/audit/
```
- 16 个暂存文件是被审对象，我没有改动：`git diff` 为空，index 与树 0e3dc49e… 逐项相同。
- 唯一的新增内容是未跟踪的 `metrix/e1-v1/audit/`。入库时只提交 `audit/*.py` 与 `audit/stdout/*.txt`。`audit/tmpdata/` 是生成的非 TEST 数据，不要提交。

结论：BLOCK
