# data-auditor final report, round 8, freeze commit 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa (parent 18076298); invoked 2026-11-22 06:05 UTC (background), interrupted by HTTP 429, resumed 08:53 UTC; invocation text: data-auditor_prompt.txt; resume: resume_message_data-auditor.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-a2ec633570a77aff6.jsonl)
---
# Data Auditor 报告：E1-PILOT 第 8 轮第 4 项，冻结提交 6a474e4a 的冻结哈希独立复算

审查对象是冻结提交 `6a474e4a5defa23dfc71b2c6bca9e15a81b517aa`，父提交 `180762987b2b0d8a18a3070edb16dd4b4c31911e`。HEAD 就是这个提交。开始前我读了仓库中的 `.claude/agents/data-auditor.md`，它与我已加载的定义一致，sha256 为 `42011228…dd833`。

**结论：48 个冻结哈希值全部一致，补充 b 的 4 个池指标也一致。** 三方指我的复算值、冻结提交中写的值、Executor 原始输出中的值。没有 BLOCKER，没有 MAJOR，没有新的 MINOR，另有 4 条观察。

## 中断与续跑
- **中断前**（06:09 UTC）：01–07 号 stdout 和 3 个 `r8b_*.py` 已写出。因 HTTP 429 中止。
- **续跑**（08:52 UTC 起）：按协调方消息继续，01–07 号不重做。续跑前确认 HEAD 仍是 6a474e4a，仓库定义文件的 sha256 没变。
- **续跑内容**：08–14 号。本报告完整覆盖 01–14 号。

## 运行环境与独立性
- **主机**：`vm`（Linux 6.18.44，4 核 CPU）。没有 GPU，也没有 nvidia-smi。
- **自建 venv**：Python 3.13.18，transformers 5.22.2，tokenizers 0.23.3，huggingface_hub 2.4.0，pyarrow 26.0.1。没有安装 torch。
- **只加载分词器**：下载目录和新建的 HF 缓存中都没有权重文件，输出为 `weight-like files: []`。
- **没有碰 TEST 数据**：
  - 没有生成、读取或统计任何 TEST 数据。
  - `eval_sets.jsonl` 只按 1 MiB 分块对整个文件求哈希，不切行、不解析、不解码。
  - TEST 模板只做归一化和哈希，不实例化。
- **外部文件全部重新下载**：放在新的空目录 `S/auditor_6a47/dl`，按固定 revision 下载。没有复用 Executor 草稿目录中的任何文件，包括 `scratchpad/r8/facts.json`。
- **路径记号**：
  - `S=/tmp/claude-0/-home-user/72f8803f-711c-5b87-8cfd-37e6a3779949/scratchpad`
  - `O=/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/6a474e4a5defa23dfc71b2c6bca9e15a81b517aa`
  - `C=6a474e4a5defa23dfc71b2c6bca9e15a81b517aa`
  - `PY=$S/auditor/venv/bin/python -I -B`
- **运行方式**：每条命令都是 `bash run_logged.sh $O/<编号文件> …`，在 `metrix/e1-pilot/audit/` 下执行。
- **没有用 Executor 代码**：
  - 脚本只 import 标准库、第三方库和我自己的 `common.py`、`r6_guard.py`。
  - 没有 import、调用或复制 `reports/` 下的任何脚本。
  - 期望值通过 `git cat-file blob $C:<path>` 从冻结提交中读取。
  - Executor 的输出只作为文本，用正则解析。
- **脚本复用**：`r8_*.py` 原样复用，没有改动，因为 92df1a60 的 stdout 引用的就是它们。本轮新写 3 个脚本：`r8b_delta.py`、`r8b_pool.py`、`r8b_compare.py`。

## 01 下载核对
- **命令**：`$PY r8_fetch.py $S/auditor_6a47/dl`
- **结果**：三个固定 revision 在 Hub 上都解析到自身，6 个文件逐一与 Hub 元数据比对：
  - Qwen 的 4 个分词器文件都是 `MATCH True`。
  - parcae `tokenizer.json`：`MATCH True`。
  - parquet：sha256 `6a3450ea…2c22`，`MATCH True`。
  - `weight-like files under out_dir: []`，`RESULT: PASS`。

## 第 1 项：协议与三个 JSON 的文件 sha256，以及工作区与本提交是否相同
- **命令**：`$PY r8_files.py /home/user/OpenMythos $C 18076298`，输出在 `02_r8_files.txt`。
- **原始输出摘录**：
```
commit 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa | parents 180762987b2b0d8a18a3070edb16dd4b4c31911e | author date 2026-11-22T06:04:41+00:00
HEAD 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa | HEAD == commit True
AUDIT_VALUE file_sha256:METRIX_E1_PROTOCOL.md 141473498582e6c67dcdd9dbe35cc4b4e18fbfe4912d74bcfdf5fb60e6593baa
AUDIT_VALUE file_sha256:DATA_MANIFEST.json 94ba8516044e9bf10c5ad907f2e905c5afd91833a383b7212737cf28170e8cf3
AUDIT_VALUE file_sha256:SPLIT_MANIFEST.json 7eb5d6edece5096ad107c4ba125fd539c2753d51e169c47556bfffeac18c7fff
AUDIT_VALUE file_sha256:SEARCH_SPACE.json 490d575d54b4cbd3902adb496817d89c82763ad22fa8efac8894bcb4a45a6258
metrix/e1-pilot/PROTOCOL_FROZEN exists in the working tree: True | in commit: False
RESULT: PASS
```
- **四个文件的逐项核对**：每个文件都满足以下五条：
  - `git show == cat-file`
  - `working tree == commit blob: True`
  - `HEAD blob == commit blob: True`
  - `git diff --quiet 6a474e4a exit 0`
  - 没有 gitattributes
- **状态字段**：三个 JSON 都是 `status 'PROTOCOL_FROZEN'`，并带 `frozen 'Owner 批准，2026-11-22 05:27 UTC'`。
- **与 Executor 一致**：一致。四个值与 `t1_protocol_checks.txt` 中的 sha256sum 输出相同（那是提交前的工作区）。与 `t5_frozen_hashes_6a474e4a.txt`（未跟踪，仅作参考）中的 `@6a474e4a` 值也相同。

## 第 2 项：全部数据哈希

### 2a. 锚文本
- **命令**：`env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $PY r8_anchor.py … $C $S/auditor_6a47/dl/parquet/…/shard_00000.parquet $S/auditor_6a47/dl/qwen_tok $S/auditor_6a47/work`
- **输出文件**：`03_r8_anchor.txt`
```
parquet sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | manifest 6a3450ea…2c22 | MATCH True
rows read until the 512th kept document: 527 | kept 512
decoded texts (512) canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | manifest 8828bc4f…2408 | MATCH True
ALT decode(skip_special_tokens=True): ... equal to main texts: True
ALT tokenizers backend decode: ... equal to main texts: True
RESULT: PASS
```

### 2b. 160 条 fact
- **命令**：`r8_facts.py … $C qwen_tok work/anchor_texts.json work`，输出在 `04_r8_facts.txt`。
- **常量核对**：14 项 manifest 常量与协议第 2.2 节的转录值全部 True。
- **原始输出摘录**：
```
anchor-rule rejections: 0
facts 160 {'learned': 120, 'unread': 40} | distinct strings 320
regenerated facts canonical sha256 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | manifest 406c8801…6b97 | MATCH True
```
- **与 92df1a60 比**：8 个 cell 的抽样次数和目标 token 数对完全相同。

### 2c. train_S.jsonl 与 candidates.json
- **命令**：`r8_s_cands.py … $C work/facts.json work`，输出在 `05_r8_s_cands.txt`。
- **原始输出摘录**：
```
record formats are the ones implemented here: train_S True | candidates True
train_S.jsonl rows 120 | canonical sha256 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | manifest 686fdd2f…bc1e | MATCH True
candidates.json keys 160 | canonical sha256 e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | manifest e5d15c99…3705 | MATCH True
train_S structure (...): True
candidates structure (...): True
RESULT: PASS
```
- **协议正文**：第 2.5、2.6 节中写的值与 manifest 相同。
- **其他读法**：6 种其他读法算出的哈希都不等于 manifest 值。

### 2d. 32 个模板与 template_set_sha256
- **命令**：`r8_templates.py … $C`，输出在 `06_r8_templates.txt`。
- **原始输出摘录**：
```
manifest template texts == protocol 2.4 table (in order): True
templates whose normalized string and normalized_sha256 match: 32/32
template_set_sha256 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | manifest 2b524113…e28f | MATCH True
ALT no strip (trailing space kept): 0 /32 match
informational L1 (pairwise intersections of TRAIN/DEV/TEST/Y normalized_sha256): [] | distinct hashes 32
RESULT: PASS
```

### 2e. Qwen 分词器文件与“全部文件”核对
- **命令**：`r8_tokenizer.py … $C qwen_tok $S/auditor_6a47/hubcache`，输出在 `07_r8_tokenizer.txt`。
- **四个文件**：`merges.txt 8831e4f1…04d5`、`tokenizer.json aeb13307…dae4`、`tokenizer_config.json d5d09f07…8101`、`vocab.json ca10d7e9…0910`，全部 `MATCH True`。
- **全部文件核对**：
```
folders in tree: []
tokenizer files in tree: ['merges.txt', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json'] | == manifest keys: True
fetched into the snapshot: ['config.json', 'merges.txt', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json']
requested but absent at the revision (.no_exist): ['added_tokens.json', 'chat_template.jinja', 'special_tokens_map.json']
weight-like files in the cache: []
class Qwen2Tokenizer/Qwen2Tokenizer same True | len 151669/151669 | vocab equal True | special equal True | probe encodings equal True | chat equal True
RESULT: PASS
```
- **结论**：`files_note` 中“没有其它分词器文件”的说法成立。

### 2f. parcae tokenizer.json 与 eval_sets.jsonl
- **命令**：`r8_general.py … $C $S/auditor_6a47/dl/parcae_tok/tokenizer.json`，输出在 `08_r8_general.txt`。
- **eval_sets.jsonl 的做法**：只对整个文件求哈希。
```
parcae_tok/tokenizer.json: bytes 2326980 | sha256 e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | ... MATCH True
working tree : bytes 1899206 | sha256 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | git blob 71d6c7b5…
6a474e4a blob: ... sha256 8816fe5a…a155 | base 61d3c767 blob: ... sha256 8816fe5a…a155
git diff --quiet base..freeze exit 0 | working tree vs freeze exit 0
manifest 8816fe5a…a155 | MATCH True
abbreviation 8816fe5a…a155 in protocol: True / abbreviation e0021e26…ea77 in protocol: True
RESULT: PASS
```

### 2g. 与 92df1a60 的差异，由我从 git 对象独立重算
- **命令**：`r8b_delta.py … 92df1a60… $C`，输出在 `09_r8b_delta.txt`。没有读取 Executor 的 delta 文件。
- **原始输出摘录**：
```
same single parent: True
changed set == expected {protocol, SPLIT_MANIFEST, t1_protocol_checks, ROUND8_TASKS}: True
DATA_MANIFEST.json: blob old 2d05ae3e… | new 2d05ae3e… | identical True
SEARCH_SPACE.json: blob old 5c28fcaa… | new 5c28fcaa… | identical True
new minus candidates.pool_too_small == old (parsed JSON): True
DATA_MANIFEST.json: ... same set True / SPLIT_MANIFEST.json: old 34 distinct | new 34 distinct | same set True
hunks: 8  (sections 2.5, 8, 8, 8, 9, 9, 11, 14)
64-hex values on removed lines: [] | on added lines: []
hash sentence ... unchanged True (2.2 facts, 2.5 candidates, 2.6 train_S); abbreviated hashes old == new: True
t0_env.txt / t1d_data_hashes.txt / t0_copy_check.txt: identical True; t1_protocol_checks.txt: identical False
RESULT: PASS
```
- **结论**：与调用文字所说相符。数据哈希、DATA_MANIFEST、SEARCH_SPACE 都没有变化。

## 第 3 项：补充 b，干扰项池大小
- **命令**：`env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $PY r8b_pool.py … $C work/facts.json work/candidates.json qwen_tok`，输出在 `10_r8b_pool.txt`。
- **做法**：输入是我自己生成的 160 条 fact，先核对其哈希为 `406c8801…`，`MATCH True`。
- **原始输出摘录**：
```
protocol contains '- 干扰项的池少于 4 个答案即 IMPLEMENTATION_FAIL,不生成合成干扰项。': lines [126]
new sentence directly follows the pool definition: True | section: ### 2.5 候选(4-way,生成数据时冻结)
section 9 IMPLEMENTATION_FAIL row mentions the 2.5 pool rule: True
pool size (count) by exposure: {'learned': [14], 'unread': [4]} | distinct answers by exposure: {'learned': [14], 'unread': [4]}
own answer never in own pool: True
minimum pool size: 4 | minimum distinct: 4
facts with pool < 4: 0 [] | with distinct < 4: 0 []
size histogram: {4: 40, 14: 120}
IMPLEMENTATION_FAIL by the 2.5 rule under DATA_SEED: False
cells: 16 (learned cells min 14, unread cells min 4)
len(encode(' ' + answer)) / len(encode(answer)) / pair: minimum 4 | facts < 4: 0 | cells with a fact < 4: [] | equal to the 3-constraint pool for every fact: True
every fact: 4 distinct candidates, true answer once, 3 distractors from its pool: True | keys 160
RESULT: PASS
```
- **四重约束**：按定义第 3 项加上答案 token 数相同这一条，最小值仍是 4，不足 4 的 cell 为 0。每个 cell 的答案 token 数对只有一种。
- **与 Executor 一致**：一致。`t1_protocol_checks.txt` 写的是 `pool sizes by exposure: {'learned': [14], 'unread': [4]} | minimum 4 | facts with pool < 4: 0`，它的输入 facts 文件 sha256 也是 `406c8801…`。

## 第 4 项：与 Executor 原始输出的汇总比对
- **命令**：`$PY r8b_compare.py /home/user/OpenMythos $C $O`，输出在 `12_r8b_compare.txt`。
- **原始输出摘录**：
```
auditor hash values read: 48 from ['02_r8_files.txt', ..., '08_r8_general.txt']
Executor t0_env.txt / t1d_data_hashes.txt / t1_protocol_checks.txt @6a474e4a: U+FFFD after decoding 0 (each)
Executor t5_frozen_hashes_6a474e4a.txt (working tree, informational) present: True
auditor hash values not used in the table: []
hash rows: 48
sizes_learned auditor [14] | Executor [14] | equal True
sizes_unread auditor [4] | Executor [4] | equal True
minimum auditor 4 | Executor 4 | equal True
facts_below_4 auditor 0 | Executor 0 | equal True
RESULT: PASS
```
- **逐行状态**：
  - 44 行是 `auditor==commit True | Executor==auditor True`。
  - 第 1 项那 4 行是 `auditor==commit n/a | Executor==auditor True`，因为提交中没有记录这四个值的字段。
  - 没有任何 False 或 NOT FOUND。
  - t5 的参考值也全部等于我的值。
- **32 个单模板值**：Executor 侧只打印了 `not reproduced: []`，所以这 32 行它的值视为 manifest 值。
- **UTF-8 核对**（`11_r8_utf8_check.txt`）：本提交中 `reports/round8/` 下 4 个文件都是 `valid UTF-8 True`。92df1a60 的 MINOR S11 在 `t1_protocol_checks.txt` 上已经消除。

## 新提出的 MAJOR / MINOR（只登记不修）
没有 BLOCKER，没有 MAJOR，也没有新的 MINOR。以下 4 条是观察：

1. **上轮两条 MINOR 仍然成立**：
   - S12：模板归一化规则的文字没写去首尾空格，见 `06` 中 `ALT no strip 0/32`。
   - S13：`t1d_data_hashes.txt` 中“PYTHONHASHSEED”的标注不实，该文件的 blob 与 92df1a60 相同。
   - 两条都已在 `DEFERRED_MINORS.md` 第 1.9 节登记。
2. **工作区中未跟踪的 `metrix/e1-pilot/PROTOCOL_FROZEN`（05:51:37）是为被取代的 92df1a60 写的。**
   - 它只写了 `92df1a60`；协议和 SPLIT_MANIFEST 的值（`61f4b777…`、`2078d045…`）不等于本提交的值（`14147349…`、`7eb5d6ed…`），见 `09` 第 g 段。
   - 它不在本提交中，Executor 已在 DEFERRED_MINORS 第 1.10 节写明要重写。
   - 第 5 项提交前必须换成以 6a474e4a 为准的内容。
3. **unread 池大小恰好等于阈值 4，余量为 0。** 冻结数据下不会触发，但以后若减少每个 cell 的 unread fact 数，就会触发 IMPLEMENTATION_FAIL。
4. **范围外，交 Review Gate 判断。** `t6_supplement_recommit.txt` 记录 Executor 对未推送的 92df1a60 做了 `git reset --soft`。这是否属于 `metrix/CLAUDE.md` 第 7 节所说的“改写 Git 历史”，不属于数据审计的范围。

## 本轮未做的检查
本次调用的范围是第 4 项冻结哈希加补充 b。定义中的 L2–L6 和 split 数量这次没有重跑：数据文件在冻结时都是 `NOT_GENERATED`，而本提交的数据输入与 92df1a60 逐字节相同（见 `09`）。L1 的模板交集为 `[]`（见 `06`）。

按 `metrix/CLAUDE.md` 第 10 节，data-auditor 仍为“待验证”，本 PASS 仅作参考。

## 文件
- **新脚本**：
  - `/home/user/OpenMythos/metrix/e1-pilot/audit/r8b_delta.py`
  - `/home/user/OpenMythos/metrix/e1-pilot/audit/r8b_pool.py`
  - `/home/user/OpenMythos/metrix/e1-pilot/audit/r8b_compare.py`
- **复用但未改动**：`/home/user/OpenMythos/metrix/e1-pilot/audit/r8_*.py`
- **完整 stdout**：`/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/6a474e4a5defa23dfc71b2c6bca9e15a81b517aa/` 下的 01–14 号文件。
  - 13 号记录了 audit/ 以外各条目的修改时间。我在本轮的第一次写入是 06:07:46。
  - audit/ 以外的条目都不是我写的：`DEFERRED_MINORS.md` 写于 06:06:13，`reviews/6a474e4a…/` 下的 interruption、resume_message、preflight 写于 08:52:27，其余写于 05:39–06:05。
- 下载、venv 和中间数据都在仓库之外的 `$S/auditor_6a47`、`$S/auditor/venv`。

## git status --short（14_git_status_final.txt 原文）
```
 M metrix/e1-pilot/reports/DEFERRED_MINORS.md
?? metrix/e1-pilot/PROTOCOL_FROZEN
?? metrix/e1-pilot/audit/r8_anchor.py
?? metrix/e1-pilot/audit/r8_compare.py
?? metrix/e1-pilot/audit/r8_facts.py
?? metrix/e1-pilot/audit/r8_fetch.py
?? metrix/e1-pilot/audit/r8_files.py
?? metrix/e1-pilot/audit/r8_general.py
?? metrix/e1-pilot/audit/r8_hashseed_probe.py
?? metrix/e1-pilot/audit/r8_s_cands.py
?? metrix/e1-pilot/audit/r8_templates.py
?? metrix/e1-pilot/audit/r8_tokenizer.py
?? metrix/e1-pilot/audit/r8_utf8_check.py
?? metrix/e1-pilot/audit/r8b_compare.py
?? metrix/e1-pilot/audit/r8b_delta.py
?? metrix/e1-pilot/audit/r8b_pool.py
?? metrix/e1-pilot/audit/stdout/6a474e4a5defa23dfc71b2c6bca9e15a81b517aa/
?? metrix/e1-pilot/audit/stdout/92df1a60ac816ab02b250d32841397c73b9a67a7/
?? metrix/e1-pilot/reports/ROUND8_REPORT.md
?? metrix/e1-pilot/reports/round8/t5_frozen_hashes.txt
?? metrix/e1-pilot/reports/round8/t5_frozen_hashes_6a474e4a.txt
?? metrix/e1-pilot/reports/round8/t5_protocol_frozen_check.txt
?? metrix/e1-pilot/reports/round8/t6_supplement_recommit.txt
?? metrix/e1-pilot/reviews/6a474e4a5defa23dfc71b2c6bca9e15a81b517aa/
?? metrix/e1-pilot/reviews/92df1a60ac816ab02b250d32841397c73b9a67a7/
```

结论：PASS
