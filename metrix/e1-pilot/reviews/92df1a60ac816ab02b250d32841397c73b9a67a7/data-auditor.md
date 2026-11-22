# data-auditor final report, round 8, freeze commit 92df1a60ac816ab02b250d32841397c73b9a67a7 (parent 18076298); invoked 2026-11-22 05:40 UTC (background); invocation text: data-auditor_prompt.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-a9ef366dffbe45859.jsonl)
---
# Data Auditor 报告：E1-PILOT 第 8 轮第 4 项，独立复算全部冻结哈希

审查对象是冻结提交 `92df1a60ac816ab02b250d32841397c73b9a67a7`，父提交 `180762987b2b0d8a18a3070edb16dd4b4c31911e`，HEAD 就是这个提交。按指令要求，我先读了仓库中的 `.claude/agents/data-auditor.md`，它与已加载的定义一致。

**结果：7 项共 48 个哈希值，我的复算值、冻结提交中写的值、Executor 原始输出中的值三方全部一致。** 没有 BLOCKER。另有 3 项新的 MINOR，按指令只登记不修。

## 运行环境与独立性
- **主机与资源**：主机名 `vm`（Ubuntu 24.04.5，4 核 CPU，没有 GPU，也没有 nvidia-smi）。
- **自建 venv**：Python 3.13.18，transformers 5.22.2，tokenizers 0.23.3，huggingface_hub 2.4.0，pyarrow 26.0.1，没有安装 torch。
- **只加载分词器**：只加载了分词器，没有下载或加载任何权重。fetch 和 tokenizer 两个脚本都检查过下载目录与 HF 缓存，结果是 `weight-like files: []`。
- **没有碰 TEST 数据**：没有生成、读取或统计任何 TEST 数据。`eval_sets.jsonl` 只对整个文件求哈希。模板只做归一化和哈希，不实例化成问句。
- **下载全部重新做**：外部文件放在新的空目录 `S/dl`，按固定 revision 下载。没有复用 Executor 草稿目录里的任何文件（`.../scratchpad/venv`、`dl`、`r8`）。
- **路径记号**：下文 `S=/tmp/claude-0/-home-user/72f8803f-711c-5b87-8cfd-37e6a3779949/scratchpad/auditor`，`O=/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/92df1a60ac816ab02b250d32841397c73b9a67a7`，`C=92df1a60ac816ab02b250d32841397c73b9a67a7`。
- **运行方式**：每条命令都在 `metrix/e1-pilot/audit/` 下执行，形式是 `bash run_logged.sh $O/<编号文件> $S/venv/bin/python -I -B <脚本> ...`。
- **没有用 Executor 代码**：脚本只 import 标准库、第三方库和我自己以前写的 `common.py`、`r6_guard.py`，没有 import、调用或复制 `reports/` 下的任何脚本。期望值都通过 `git cat-file blob $C:<path>` 从冻结提交中读取。
- **下载核对**（`01_r8_fetch.txt`）：三个仓库的固定 revision 在 Hub 上都解析到自身。下载的 6 个文件逐一与 Hub 元数据（LFS sha256 或 git blob id）比对，全部 `MATCH True`。

## 第 1 项：协议与三个 JSON 的文件 sha256
- **命令**：`r8_files.py /home/user/OpenMythos $C 18076298`
- **输出文件**：`02_r8_files.txt`
- **原始输出摘录**：
```
commit 92df1a60ac816ab02b250d32841397c73b9a67a7 | parents 180762987b2b0d8a18a3070edb16dd4b4c31911e | author date 2026-11-22T05:39:23+00:00
HEAD 92df1a60ac816ab02b250d32841397c73b9a67a7 | HEAD == commit True
AUDIT_VALUE file_sha256:METRIX_E1_PROTOCOL.md 61f4b777316cb554846990aa5024d14689124340d4e972a6c77d2d663580f19a
AUDIT_VALUE file_sha256:DATA_MANIFEST.json 94ba8516044e9bf10c5ad907f2e905c5afd91833a383b7212737cf28170e8cf3
AUDIT_VALUE file_sha256:SPLIT_MANIFEST.json 2078d0456845b039459dc56e09e5868c4c8f9477dbaab106c4f4a5f924be1baa
AUDIT_VALUE file_sha256:SEARCH_SPACE.json 490d575d54b4cbd3902adb496817d89c82763ad22fa8efac8894bcb4a45a6258
```
- **四个文件的逐项核对**：每个文件都满足以下五条：
  - `git show bytes == cat-file bytes: True`
  - `working tree ... == commit blob: True`
  - `HEAD blob == commit blob: True`
  - `git diff --quiet 92df1a60 exit 0`
  - `gitattributes: (no attributes)`
- **状态字段**：四个文件的状态都是 PROTOCOL_FROZEN。工作区和提交中都还没有 PROTOCOL_FROZEN 文件。
- **冻结提交中的值**：没有对应字段，这四个值要等 PROTOCOL_FROZEN 文件写入。
- **与 Executor 一致**：一致。`reports/round8/t5_frozen_hashes.txt` 与 `t1_protocol_checks.txt` 中的 4 个值相同。

## 第 2 项：160 条 fact 的规范化 SHA-256
- **命令**：`env HF_HUB_OFFLINE=1 ... r8_facts.py /home/user/OpenMythos $C $S/dl/qwen_tok $S/work/anchor_texts.json $S/work`
- **输出文件**：`04_r8_facts.txt`
- **做法**：常量按协议第 2.2 节转录，并与 manifest 逐项比对，14 项全部 True。锚文本用第 3 项我自己重建的 512 篇。
- **原始输出摘录**：
```
anchor-rule rejections: 0
facts 160 {'learned': 120, 'unread': 40} | distinct strings 320
regenerated facts canonical sha256 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | manifest 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | MATCH True
```
- **冻结提交中的值**：`name_generation.expected_facts_canonical_sha256` 为 `406c8801…6b97`，与协议第 2.2 节正文所写相同。
- **结论**：一致。
- **与 Executor 一致**：一致（`t1d_data_hashes.txt`）。8 个 cell 的抽样次数与目标数对也与 Executor 的 cell log 完全相同。

## 第 3 项：锚文本
- **命令**：`env HF_HUB_OFFLINE=1 ... r8_anchor.py /home/user/OpenMythos $C $S/dl/parquet/data/sample-100BT/train/shard_00000.parquet $S/dl/qwen_tok $S/work`
- **输出文件**：`03_r8_anchor.txt`
- **原始输出摘录**：
```
parquet sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | manifest 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | MATCH True
rows read until the 512th kept document: 527 | kept 512
documents with 128 ids / fewer: {'128': 511, '<128': 1} | total chars of the 512 texts 309172
decoded texts (512) canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | manifest 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | MATCH True
ALT decode(skip_special_tokens=True): ... equal to main texts: True
ALT tokenizers backend decode: ... equal to main texts: True
```
- **冻结提交中的值**：
  - `anchor_text.source` 中的 sha256 为 `6a3450ea…2c22`。
  - `anchor_text.decoded_texts_canonical_sha256` 为 `8828bc4f…2408`。
- **结论**：两项都一致。按 `decoded_texts_hash_rule` 实现，结果不受解码参数（是否跳过特殊 token、走哪种解码后端）影响。
- **与 Executor 一致**：一致（`t1d` 中 3 处，`t0_env` 中 1 处）。

## 第 4 项：train_S.jsonl 与 candidates.json 的规范化 SHA-256
- **命令**：`r8_s_cands.py /home/user/OpenMythos $C $S/work/facts.json $S/work`
- **输出文件**：`05_r8_s_cands.txt`
- **做法**：输入是第 2 项我自己生成的 facts。记录格式按第 1a 项，脚本输出中有 `record formats are the ones implemented here: train_S True | candidates True`。
- **原始输出摘录**：
```
train_S.jsonl rows 120 | canonical sha256 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | manifest 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | MATCH True
candidates.json keys 160 | canonical sha256 e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | manifest e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | MATCH True
train_S structure (...): True
candidates structure (...): True
written files re-parse to the same canonical hashes: True
```
- **冻结提交中的值**：
  - `s_permutation.expected_train_S_canonical_sha256` 为 `686fdd2f…bc1e`。
  - `candidates.candidate_mapping_sha256` 为 `e5d15c99…3705`。
  - 协议第 2.5、2.6 节正文所写相同。
- **结论**：两项都一致。另外 6 种其他读法算出的哈希都不等于 manifest 值，说明 manifest 值确实只对应写明的调用方式。
- **与 Executor 一致**：一致（`t1d`）。

## 第 5 项：32 个模板的 normalized_sha256 与 template_set_sha256
- **命令**：`r8_templates.py /home/user/OpenMythos $C`
- **输出文件**：`06_r8_templates.txt`，32 行逐条输出都在其中。
- **原始输出摘录**：
```
manifest template texts == protocol 2.4 table (in order): True
templates whose normalized string and normalized_sha256 match: 32/32
template_set_sha256 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | manifest 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | MATCH True
ALT no strip (trailing space kept): 0 /32 match
```
- **结论**：一致。
- **与 Executor 一致**：一致。`t1_protocol_checks.txt` 写的是 `not reproduced: []`，重算的集合哈希也是 `2b524113…`。

## 第 6 项：Qwen3-1.7B@70d244cc 分词器文件
- **命令**：`r8_tokenizer.py /home/user/OpenMythos $C $S/dl/qwen_tok $S/hubcache`
- **输出文件**：`07_r8_tokenizer.txt`
- **原始输出摘录**：
```
merges.txt sha256 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 | ... MATCH True
tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 | ... MATCH True
tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 | ... MATCH True
vocab.json sha256 ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 | ... MATCH True
folders in tree: []
tokenizer files in tree: ['merges.txt', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json'] | == manifest keys: True
fetched into the snapshot: ['config.json', 'merges.txt', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json']
requested but absent at the revision (.no_exist): ['added_tokens.json', 'chat_template.jinja', 'special_tokens_map.json']
weight-like files in the cache: []
class Qwen2Tokenizer/Qwen2Tokenizer same True | len 151669/151669 | vocab equal True | special equal True | probe encodings equal True | chat equal True
```
- **冻结提交中的值**：`model.tokenizer.files_sha256` 中的 4 个值。
- **结论**：一致。
- **"全部文件"核对**：
  - 该 revision 的完整文件树（递归列出，共 12 个文件，没有子目录）中，分词器文件正好是这 4 个。
  - transformers 5.22.2 加载分词器时还会去取 `added_tokens.json`、`chat_template.jinja`、`special_tokens_map.json`，这三个文件在该 revision 中都不存在。它另外会取 `config.json`，这不是分词器文件。
  - 只含 4 个文件的目录加载出的分词器，与从 Hub 加载的完全相同。
  - 所以 `files_note` 中"没有其它分词器文件"的说法成立。
- **与 Executor 一致**：一致（`t0_env` 与 `t1d` 中各 2 处）。

## 第 7 项：parcae tokenizer.json 与 eval_sets.jsonl
- **命令**：`r8_general.py /home/user/OpenMythos $C $S/dl/parcae_tok/tokenizer.json`
- **输出文件**：`08_r8_general.txt`
- **做法**：eval_sets.jsonl 只按 1 MiB 分块对整个文件求哈希，不切行、不解析、不解码。
- **原始输出摘录**：
```
... parcae_tok/tokenizer.json: bytes 2326980 | sha256 e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | ... MATCH True
working tree : bytes 1899206 | sha256 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | git blob 71d6c7b58bdfbbbd4233ef31773dcffce259900e
92df1a60 blob: ... sha256 8816fe5a...a155 | base 61d3c767 blob: ... sha256 8816fe5a...a155
git diff --quiet base..freeze exit 0 | working tree vs freeze exit 0
manifest 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | MATCH True
```
- **冻结提交中的值**：
  - `general_text.decode_tokenizer_json_sha256` 为 `e0021e26…ea77`。
  - `general_text.source_file_sha256` 为 `8816fe5a…a155`。
  - 协议第 2.7 节中的两个缩写都能在正文中找到。
- **结论**：两项都一致。
- **与 Executor 一致**：一致（`t0_env`）。

## 汇总比对
- **命令**：`r8_compare.py /home/user/OpenMythos $C $O`
- **首次运行**（`09_r8_compare.txt`，原样保留）：失败，`UnicodeDecodeError`。原因是 Executor 的 `t1_protocol_checks.txt` 不是合法的 UTF-8（见 MINOR 3）。
- **修正后重跑**（`10_r8_compare_rerun.txt`）：解析 Executor 文本时改用 errors="replace"。最后输出为 `rows: 48`、`auditor values not used in the table: []`、`RESULT: PASS`。每一行都是 `auditor==commit True` 且 `Executor==auditor True`，第 1 项那 4 行没有 manifest 字段，显示为 n/a。

## 新提出的 MAJOR / MINOR（只登记不修）
没有 BLOCKER，也没有 MAJOR。

1. **MINOR：模板归一化规则的文字没有写去掉首尾空格。** `SPLIT_MANIFEST.template_freeze.normalization` 和协议第 3 节"模板冻结"都只写了"合并空格"，没写去首尾空格。但 32 个冻结哈希都要求去掉首尾空格：不去时 `ALT no strip: 0 /32 match`（`06_r8_templates.txt`）。冻结值本身已经消除了这个歧义，只是规则文字不完整。
2. **MINOR：Executor 原始输出中的 PYTHONHASHSEED 标注不实。** `t1d_data_hashes.txt` 和第 7 轮的 `round7/t1g_gen_s_cands.txt` 都写了"不同 PYTHONHASHSEED"的两次运行，用的是 `env PYTHONHASHSEED=n python -I`。但 `-I` 会忽略这个环境变量（`11_r8_hashseed_probe.txt`：`with -I the variable is IGNORED`）。两次运行实际用的是两个随机 hash seed，所以"两次逐字节相同"的结论仍然成立，只是标注不对。PROTOCOL_FROZEN 文件和报告不应再沿用"PYTHONHASHSEED=0/31337"这个说法。
3. **MINOR（格式问题）：冻结提交中的 `reports/round8/t1_protocol_checks.txt` 不是合法的 UTF-8。** 有 8 行在 200 或 120 字节处被截断，切在汉字的多字节序列中间（`12_r8_utf8_check.txt`）。不影响任何哈希。

## 文件
- **脚本**：`/home/user/OpenMythos/metrix/e1-pilot/audit/` 下的 `r8_fetch.py`、`r8_files.py`、`r8_anchor.py`、`r8_facts.py`、`r8_s_cands.py`、`r8_templates.py`、`r8_tokenizer.py`、`r8_general.py`、`r8_compare.py`、`r8_hashseed_probe.py`、`r8_utf8_check.py`。
- **完整 stdout**：`/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/92df1a60ac816ab02b250d32841397c73b9a67a7/01_…15_*.txt`。其中 09 是失败的首次运行，原样保留。14 记录了 audit/ 以外 4 个条目的修改时间。

## git status --short（15_git_status_final.txt 原文）
```
 M metrix/e1-pilot/reports/DEFERRED_MINORS.md
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
?? metrix/e1-pilot/audit/stdout/92df1a60ac816ab02b250d32841397c73b9a67a7/
?? metrix/e1-pilot/reports/round8/t5_frozen_hashes.txt
?? metrix/e1-pilot/reviews/92df1a60ac816ab02b250d32841397c73b9a67a7/
```
**audit/ 以外的条目都不是我写的。** 它们是 Executor 和 code-reviewer 流程同时写入的，修改时间见 `14_outside_audit_mtimes.txt`：
- `reviews/92df…/` 下的 prompt、diff、preflight 写于 05:39:41–05:40:00。
- `t5_frozen_hashes.txt` 写于 05:40:29，文件头写明 "Written by the Executor"。
- 这些都早于我本轮的第一个文件（05:42:41）。
- `reviews/…/code-reviewer.md` 与 `extract_log.txt` 写于 05:46:22。
- `DEFERRED_MINORS.md` 的修改写于 05:46:41，内容是 Executor 新增的第 1.9 节。

我的所有写入都在 `metrix/e1-pilot/audit/` 下；下载、venv 和中间数据在仓库之外的 `$S` 目录。

按 `metrix/CLAUDE.md` 第 10 节，data-auditor 仍为"待验证"，本 PASS 仅作参考。

结论：PASS
