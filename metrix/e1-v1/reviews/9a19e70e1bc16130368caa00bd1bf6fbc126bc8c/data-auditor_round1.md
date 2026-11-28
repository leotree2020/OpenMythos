# data-auditor, E1-V1 freeze, round 1, on freeze commit 9a19e70e1bc16130368caa00bd1bf6fbc126bc8c (trust status 待验证: PASS for reference only, metrix/CLAUDE.md section 10)
# invocation: data-auditor_round1_prompt.txt; launched 2026-11-28T12:24:49Z; transcript: data-auditor_round1_transcript.jsonl (copied unchanged); scripts metrix/e1-v1/audit/f1_*.py, stdout metrix/e1-v1/audit/stdout/*_freeze.txt
# extracted unchanged with metrix/e1-pilot/reports/round6/review_extract.py
---
# data-auditor：E1-V1 冻结提交审计（D2，一轮）

**结论：哈希全部复算出来了，全部一致，没有 BLOCKER。** 有两条脚本在第一次运行时出过错，错在我自己的脚本，与数据无关；两次运行的输出都保留了。

- 运行环境：主机 `vm`（Claude Code 云端容器，只用 CPU，没有 GPU，未安装 torch）。
- Python：指定的 venv（Python 3.13.18、transformers 5.22.2、tokenizers 0.23.3、pyarrow 26.0.1），每次运行都加 `-I -B`。
- 时间：2026-11-28 12:29–12:34 UTC。
- 仓库状态：HEAD = 冻结提交 `9a19e70e1bc16130368caa00bd1bf6fbc126bc8c`，工作区中这五个文件与 HEAD 相同（`git diff --stat` 为空）。
- 限制的遵守情况：
  - 只加载了分词器，没有加载模型权重，没有训练，没有评测。
  - 没有生成任何 TEST 文件（`tmp_freeze/data` 下没有 test 文件）。
  - MMLU 与 ARC 的 test parquet 只做了两件事：对整个文件求 sha256，读 `ParquetFile.metadata.num_rows`（文件尾的行数）。
  - `eval_sets.jsonl` 的 test 行只用第 0 节的字节正则匹配行首并计数，不解码，不做 JSON 解析。
- 独立性：没有读取、import、调用或复制 Executor 的任何脚本（`reports/authoring/*.py`、`reports/freeze/*`）。
  - 新脚本由我参照自己以前写的 `audit/audit_lib.py`、`a1_hashes.py`、`a5_damage.py`、`a7_hub.py` 改写。
  - 读过 Executor 的一份文本输出 `reports/freeze/rebuild_check.txt`，只用来比对结果。

**新写的脚本**（都在 `/home/user/OpenMythos/metrix/e1-v1/audit/`）：
- `f1_lib.py`：共用的辅助函数
- `f1_a_bytes.py`：项目 (a)
- `f1_b_inputs.py`：项目 (b)
- `f1_c_regen.py`：项目 (c)
- `f1_d_compare.py`：项目 (d)

**完整 stdout**（都在 `/home/user/OpenMythos/metrix/e1-v1/audit/stdout/`）：
- `f1_a_bytes_freeze.txt`
- `f1_b_inputs_freeze.txt`；第一次运行另存为 `f1_b_inputs_firstrun_freeze.txt`
- `f1_c_regen_freeze.txt`；第一次运行另存为 `f1_c_regen_firstrun_freeze.txt`
- `f1_d_compare_freeze.txt`
- `f1_e_executor_compare_freeze.txt`

下载的文件和生成的数据在 `/home/user/OpenMythos/metrix/e1-v1/audit/tmp_freeze/`（不入库）。

---

## (a) 协议与四个 JSON 的原始字节 sha256

**命令**：`.../venv/bin/python -I -B metrix/e1-v1/audit/f1_a_bytes.py`
- 每个文件用 `git cat-file blob 9a19e70e:<path>` 从提交对象读出字节，与工作区文件逐字节比对。
- 同时核对读出字节的 git blob sha1 等于 `git rev-parse <commit>:<path>`。

**原始输出（摘录）**：
```
HEAD 9a19e70e1bc16130368caa00bd1bf6fbc126bc8c | freeze commit 9a19e70e1bc16130368caa00bd1bf6fbc126bc8c | HEAD == freeze commit True
commit type commit | parents ['78e79e4390aa9e465127ca52b57928714abdb633']
metrix/e1-v1/METRIX_E1V1_PROTOCOL.md  bytes 78941 | git blob 2e648d8a6e02ebfa44f175ba7058d0d2e6b6e844 (sha1 ... matches: True)
     sha256 at commit (git cat-file blob) df710d1c7ccf3acba4b2ae25df0a0c5f8a07d3cd8d1c02f3de65eae3c40a504e
     sha256 of working-tree file          df710d1c7ccf3acba4b2ae25df0a0c5f8a07d3cd8d1c02f3de65eae3c40a504e   identical bytes: True
metrix/e1-v1/DATA_MANIFEST.json    bytes 25790 | 2a35d40c7192b4f8df2dfa765714340009070d9b3e4b750cee994ae78c3e6767 (commit = working tree, identical True)
metrix/e1-v1/SPLIT_MANIFEST.json   bytes 19607 | 667943a503204d689dc7baef48583652b6947ad62694825995ac6a0d9d64a40b (identical True)
metrix/e1-v1/DOSE_SPACE.json       bytes 9056  | 44923d80614d780a010cd9742689e2fccdc949b4144b221a8de6469e898a7bc2 (identical True)
metrix/e1-v1/DAMAGE_MANIFEST.json  bytes 12665 | 5a05e5e7ffef7829328f2edbed2c15d4a52f2d99c4052cf30ef57a4a672588cd (identical True)
reference bc03348a: PROTOCOL ace4e8cb33a9f6cea662096878e49a4d939e3e892ceb7754f9ab8c7312e6e675, DATA d2e820a48736155cfacde4ec28e1411d11513d47f846432baa50f4d8df3c33da,
  SPLIT a90edc236b9bc1d479ffdcda772a6a5ba460f7a39bf2f977f8144ae57090c0eb, DOSE b2989f8c6a8743c1bcb7702c295fe1de393922c0c5c54de6ee44264345ccb9fb,
  DAMAGE 357df127a9fabdccdadbdceadcefac92b15bf85d73b8633028c863dcbe3a443a (all five changed in the freeze commit: True)
ITEM (a): ALL MATCH
```

**与 Executor 是否一致**：一致（`stdout/f1_e_executor_compare_freeze.txt`）。
- 四个 JSON 的 sha256 与 Executor `reports/freeze/rebuild_check.txt` 中 "committed" 一列的值逐个相同（equal True ×4）。
- Executor 的复建检查用的是暂存树 69ff2c43。该树中五个文件的 blob id 与冻结提交中的相同（same blob True ×5）。
- 协议文件的 sha256 在 Executor 的输出中没有记录，无从比对；冻结提交与工作区的协议文件逐字节相同。
- 差异：无。

## (b) 输入文件（从 Hugging Face 按 manifest 的 repo、revision、文件名下载，对整个文件求 sha256）

**命令**：`.../venv/bin/python -I -B metrix/e1-v1/audit/f1_b_inputs.py`
- 下载方式：`curl -L --fail`，URL 为 `https://huggingface.co/[datasets/]<repo>/resolve/<revision>/<file>`。
- 期望值从冻结提交的 manifest 读取（`git cat-file`）。
- 另外记录了 Hub 响应中的 `x-repo-commit`，以及 `x-linked-etag`：LFS 文件的这个值是 sha256，非 LFS 文件的是 git blob sha1。

**原始输出（第二次运行，摘录）**：
```
[Qwen tokenizer] Qwen/Qwen3-1.7B @ 70d244cc... tokenizer.json        sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 | manifest ... equal True | x-repo-commit = pinned True | LFS sha256 = download True
[Qwen tokenizer] tokenizer_config.json  d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 equal True | not LFS, git blob sha1 417d038a... = download True
[Qwen tokenizer] vocab.json             ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 equal True | git blob sha1 4783fe10... True
[Qwen tokenizer] merges.txt             8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 equal True | git blob sha1 31349551... True
[anchor source] SandyResearch/fineweb-edu-shuffled @ 4d1138c0... data/sample-100BT/train/shard_00000.parquet  bytes 94511680 sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 equal True | LFS True | footer rows 53248 (no manifest value; report only)
[parcae tokenizer] SandyResearch/parcae-tokenizer @ 6247b5d0... tokenizer.json  e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 equal True | git blob sha1 3ff4f5af... True
[MMLU DEV source] cais/mmlu @ c30699e8... all/validation-00000-of-00001.parquet  66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef equal True | footer rows 1531 = 1531
[MMLU TEST source] all/test-00000-of-00001.parquet  74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7 equal True | TEST source: footer row count only, no row read: 14042 = 14042
[ARC DEV (not adopted)] ARC-Challenge/validation  395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05 equal True | rows 299 = 299
[ARC DEV (not adopted)] ARC-Easy/validation       ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74 equal True | rows 570 = 570
[ARC TEST (not adopted)] ARC-Challenge/test        62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9 equal True | footer only 1172 = 1172
[ARC TEST (not adopted)] ARC-Easy/test             4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177 equal True | footer only 2376 = 2376
downloaded-file sha256 equal to manifest: 12 of 12
[eval_sets.jsonl] bytes 1899206 | sha256 working tree 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | in freeze commit (git cat-file) same | identical True | manifest d1.source_file_sha256 equal True
   rows 1200 | rows not matching the protocol section 0 prefix regex: 0
   counts by (domain bytes, split bytes) from the row prefix only: books/c4/fineweb/wikitext: dev 100 each, test 200 each (after skipping 25: 175 = manifest 175)
ITEM (b): ALL MATCH
```

**与 manifest 是否一致**：一致，12 个下载文件全部相同，`eval_sets.jsonl` 也相同。每个下载的 `x-repo-commit` 都等于固定的 revision。

**第一次运行的说明**（`f1_b_inputs_firstrun_freeze.txt`）：第一次的结论是 "MISMATCH PRESENT"，原因是我的脚本有两处错误，数据本身没有不一致。
1. 非 LFS 文件的 `x-linked-etag` 是 git blob sha1，脚本却拿它与 sha256 比较。
2. 锚文本 parquet 在 manifest 中没有行数，脚本却拿 None 去比较。

那一次 12 个文件的 sha256 与 manifest 已经全部相同（12 of 12）。修正这两处后重新下载并重跑，结果为 ALL MATCH。

## (c) 独立重新生成全部非 TEST 数据并求规范化 SHA-256

**命令**：`.../venv/bin/python -I -B metrix/e1-v1/audit/f1_c_regen.py`
- 所用的规则与参考值都来自冻结提交中的 manifest 与协议（`git cat-file` 读取）。
- 生成的文件先写到磁盘，再读回、解析，按 `hashing` 规则重新序列化后求 SHA-256。

**原始输出（第二次运行，摘录）**：
```
anchor documents 512 | source rows scanned 527 | ids per document min 123 max 128
OK   anchor decoded texts (canonical JSON list of the 512 texts): 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408  (= DATA_MANIFEST, = Pilot manifest; protocol line 86, 2.6)
OK   anchor_text.jsonl: 2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5  (= files.anchor_text.jsonl, = anchor_text.file_canonical_sha256_authoring)
templates 32 | normalized text or normalized_sha256 differing from SPLIT_MANIFEST.templates[*]: 0 | identical to the Pilot SPLIT_MANIFEST templates list: True
OK   template_set_sha256: 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f  (= SPLIT_MANIFEST, = Pilot; protocol line 76, 2.4)
OK   Pilot facts (canonical JSON list): 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97  (= preseed.pilot_facts_canonical_sha256; protocol line 66, 2.2)
     cross-check: Pilot facts as JSONL e05561ac... = Pilot DATA_MANIFEST files.facts.jsonl True
V1 cells: entity draws 40-83, answer draws 80-270 | learned 240 | unread 80 | strings 640 distinct 640 | lowercase equal to a Pilot string 0 | fact_id shared with Pilot 0
OK   V1 facts (canonical JSON list): 0fc5ad819500e8a9f56771405af67d0fa71bafabba25bf8f4c3e5b6d684e01f4  (= expected_facts_canonical_sha256; protocol line 68, 2.2)
OK   facts.jsonl: 4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9
OK   train_F.jsonl: fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511
OK   train_S.jsonl: 7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6  (= files, = s_permutation.expected...; protocol line 84)
OK   train_Y.jsonl: 82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b  (protocol line 85)
OK   dev_qa.jsonl: 39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce
OK   candidates.json: 79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3  (= files, = SPLIT_MANIFEST candidate_mapping_sha256; protocol line 80, 2.5)
Y/F tokens: F 3802 (manifest 3802) | Y 4541 (manifest 4541) | ratio 1.194371 (manifest 1.1944)
eval_sets.jsonl: DEV rows parsed per domain {books: 100, c4: 100, fineweb: 100, wikitext: 100} | non-dev rows skipped on the prefix bytes (not decoded): 800
D1 DEV kept 400 (manifest 400) | excluded {'L8': 0, 'L6': 0} | ids per window mean 248.893 (manifest 248.893)
OK   general_dev.jsonl: e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281  (= files, = d1.dev.authoring; protocol line 220, 7.2)
letter tokens {'A': [362], 'B': [425], 'C': [356], 'D': [422]} equal True
MMLU D2 DEV items 800 | rows visited 800 | excluded {} | subjects 57 (all = manifest)
OK   d2_dev.jsonl (MMLU, adopted): f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be  (= files.d2_dev.jsonl.reference_canonical_sha256, = d2.datasets.mmlu.authoring_dev; protocol lines 222 (7.2) and 447 (15))
ARC D2 DEV items 800 | DEV source rows 869 | rows visited 806 | excluded {'not_4_choices_or_answer': 6} (manifest 6)
OK   d2_dev (ARC, not adopted alternative): 1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32  (= files.d2_dev.jsonl.not_adopted_alternative.arc..., = d2.datasets.arc.authoring_dev; protocol line 222)
TEST files generated: none ( [] )
hash checks equal: 14 of 14 | elapsed 5.3 s
ITEM (c): ALL MATCH
```

**与 manifest、协议是否一致**：14 项全部一致。
- 协议中记录了值的 10 项，计算值都出现在协议对应的节内。
- `facts.jsonl`、`train_F.jsonl`、`dev_qa.jsonl`、`anchor_text.jsonl` 这四个文件级哈希，协议正文本来就不记录，只在 manifest 中有。

**第一次运行的说明**（`f1_c_regen_firstrun_freeze.txt`）：
- 第一次在计算 D2 上下文长度统计量时中止：指定的 venv 没有 jinja2，`apply_chat_template` 无法运行。
- 中止之前已经算出的哈希（锚文本到 `general_dev`）全部相同。
- 第二次运行跳过了这个统计量，我没有往 venv 里装任何包。
- 因此 `context_ids_mean`（MMLU 134.221、ARC 82.989）本轮没有复算。它不是哈希，不属于 (a)–(d)，对任何数据哈希都没有影响。

## (d) bc03348a 与冻结提交：逐字段对比全部数据哈希与输入文件哈希，并求十六进制串差集

**命令**：`.../venv/bin/python -I -B metrix/e1-v1/audit/f1_d_compare.py`
- 两个版本都从提交对象读取。
- 字段路径的映射：
  - `files.d2_dev.jsonl.reference_canonical_sha256.mmlu` 对应 `files.d2_dev.jsonl.reference_canonical_sha256`
  - `...reference_canonical_sha256.arc` 对应 `files.d2_dev.jsonl.not_adopted_alternative.arc.reference_canonical_sha256`

**原始输出（摘录；65 行逐字段的完整清单在 stdout 文件中）**：
```
EQUAL data  DATA_MANIFEST.json: files.d2_dev.jsonl.reference_canonical_sha256.arc = 1ea77c8a...  [path mapped to files.d2_dev.jsonl.not_adopted_alternative.arc.reference_canonical_sha256]
EQUAL data  DATA_MANIFEST.json: files.d2_dev.jsonl.reference_canonical_sha256.mmlu = f40c146a...  [path mapped to files.d2_dev.jsonl.reference_canonical_sha256]
summary (64-hex): base entries 65 | equal 65 | different 0 | missing in freeze 0 | new paths in freeze 0
summary (40-hex): base entries 14 | equal 14 | different 0 | missing in freeze 0 | new paths in freeze 0
protocol 64-hex (section, value) pairs of base missing in freeze: none | added in freeze: [('section 15', 'f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be')]
abbreviated hashes (8…4): base ['8816fe5a…a155'] | freeze ['8816fe5a…a155'] | same True
METRIX_E1V1_PROTOCOL.md 64-hex: distinct base 12 freeze 12 | base - freeze [] | freeze - base []   (count of f40c146a 1 -> 2)
METRIX_E1V1_PROTOCOL.md 40-hex: distinct base 5 freeze 5 | [] | []   (counts 210d026f 1 -> 2, c30699e8 1 -> 3)
DATA_MANIFEST.json 64: 18/18 [] [] | 40: 4/4 [] []    SPLIT_MANIFEST.json 64: 34/34 | 40: 2/2
DOSE_SPACE.json 64: 0/0 | 40: 2/2                     DAMAGE_MANIFEST.json 64: 11/11 | 40: 5/5   (all differences [])
ALL FIVE FILES 64-hex: distinct base 59 freeze 59 | base - freeze empty | freeze - base empty
ALL FIVE FILES 40-hex: distinct base 7 freeze 7 | base - freeze empty | freeze - base empty
hex strings with upper-case letters in the freeze files: none
ITEM (d): ALL DATA AND INPUT HASHES EQUAL
```

覆盖的字段一共 79 个，65 个 64 位、14 个 40 位，两个版本的值全部相同：
- 64 位：全部数据参考哈希（9 个非 TEST 文件、facts 列表、Pilot facts、锚文本解码文本、`train_S` 期望值、候选映射、模板集合、32 个模板各自的 `normalized_sha256`），以及全部输入文件哈希（Qwen 4 个分词器文件、锚文本 parquet、parcae `tokenizer.json`、`eval_sets.jsonl`、MMLU 2 个、ARC 4 个）。
- 40 位：Hub revision 与 git 提交。

**两个版本之间的差集**：协议与四个 JSON 中，40 位与 64 位十六进制串的差集在两个方向上都为空。

**与 Executor 是否一致**：一致。各文件不同十六进制串的数量，我的 64 位与 40 位之和为 17、22、36、2、16，与 Executor `rebuild_check.txt` 记录的数量相同，差集也同为空（`f1_e_executor_compare_freeze.txt`）。

**说明**（只报告，不构成不一致）：
1. 协议中的 87a244db 一项显示为 "ONLY BASE / ONLY FREEZE"，只是因为它所在的标题由「PROTOCOL v1(草案)」改成了「PROTOCOL v1」。值相同，行号都是第 9 行。
2. 冻结版协议第 15 节（第 444、447 行）与第 17 节（第 469 行）新出现了 f40c146a、c30699e8、210d026f。它们是已有值的再次引用，没有新的值。
3. JSON 的逐叶子差异清单中（只报告）：
   - `reported_values[7..12]` 显示为 "changed"，原因是第 7 项新插入了一条（A4 的 `d0_damage`），后面各条的下标都后移了一位；
   - 其余差异都属于 A1–A5 与 C1–C4 规定的文字或状态字段，没有一处涉及数据计数或数据哈希。

---

## 运行后的 `git status --short` 原始输出
```
?? metrix/e1-v1/audit/f1_a_bytes.py
?? metrix/e1-v1/audit/f1_b_inputs.py
?? metrix/e1-v1/audit/f1_c_regen.py
?? metrix/e1-v1/audit/f1_d_compare.py
?? metrix/e1-v1/audit/f1_lib.py
?? metrix/e1-v1/audit/stdout/f1_a_bytes_freeze.txt
?? metrix/e1-v1/audit/stdout/f1_b_inputs_firstrun_freeze.txt
?? metrix/e1-v1/audit/stdout/f1_b_inputs_freeze.txt
?? metrix/e1-v1/audit/stdout/f1_c_regen_firstrun_freeze.txt
?? metrix/e1-v1/audit/stdout/f1_c_regen_freeze.txt
?? metrix/e1-v1/audit/stdout/f1_d_compare_freeze.txt
?? metrix/e1-v1/audit/stdout/f1_e_executor_compare_freeze.txt
?? metrix/e1-v1/audit/tmp_freeze/
?? metrix/e1-v1/reviews/9a19e70e1bc16130368caa00bd1bf6fbc126bc8c/
```
- `metrix/e1-v1/reviews/9a19e70e.../` 在我开始之前就已经是未跟踪状态（我第一条命令的输出里就有），是 Executor 的文件，不是我写的。
- 没有任何已跟踪文件被修改：`git diff --name-only HEAD -- metrix/e1-v1/audit` 为空，已有的 audit 文件都没有改动。
- `tmp_freeze/` 不入库，按指令由 Executor 之后移出仓库。

我的 PASS 只作参考：信任状态为「待验证」（metrix/CLAUDE.md 第 10 节）。

结论：PASS
