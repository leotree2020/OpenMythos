# data-auditor final report, round 9, v1.1 freeze commit 87a244db28a901f9e89282b50df76778ab5c2887 (parent 8a49c087); invoked 2026-11-22 10:13 UTC (background); invocation text: data-auditor_prompt.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-aec92e96ca207c917.jsonl)
---
# data-auditor 第 9 轮第 5 项报告：v1.1 冻结提交 87a244db28a901f9e89282b50df76778ab5c2887

两项都复算完成，结果全部一致，没有 BLOCKER。
- 第 1 项：协议与三个 JSON 的新字节哈希与 Executor 的 t5 一致；三个 JSON 相对 v1 只改了 `version`（v1 → v1.1）。
- 第 2 项：45 个数据哈希（12 行 PROTOCOL_FROZEN 表值，加 32 个单模板值，加 1 个按 v1.1 第 2.2 节方法重算的 fact 值）都与 v1 相同，也与本提交 manifest 相同。

**定义与运行环境**
- 已读仓库中的 `.claude/agents/data-auditor.md`，以它为定义。第 12 行规定：只有指令明确要求执行第 8 节第 8 步 L6 TEST 时才可读 TEST。本任务没有这个要求，所以本轮没有生成、读取或统计任何 TEST 数据。`eval_sets.jsonl` 只对整个文件求了哈希，没有切行、解析或解码。
- 主机 `vm`（Anthropic 云容器），只用 CPU。临时 venv 在 `/tmp/claude-0/-home-user/1df4d82a-900e-5f17-b09e-42f6e2f7c762/scratchpad/venv`：Python 3.13.18、transformers 5.22.2、tokenizers 0.23.3、huggingface_hub 2.4.0、pyarrow 26.0.1、jinja2 3.1.6，没有装 torch。
- 只加载了分词器，没有下载或加载任何权重：02 号输出 `weight-like files under out_dir: []`，07 号输出 `weight-like files in the cache: []`。
- 下载文件和生成的数据只放在 `/tmp/claude-0/-home-user/1df4d82a-900e-5f17-b09e-42f6e2f7c762/scratchpad/auditor_87a2/`，不提交。
- 没有 import、调用、复制，也没有打开 `reports/` 下 Executor 的任何脚本（包括 `reports/round9/v11_checks.py`）。Executor 的输出只按文本用正则读取。

**新写的脚本**
- `/home/user/OpenMythos/metrix/e1-pilot/audit/r9_files.py`
- `/home/user/OpenMythos/metrix/e1-pilot/audit/r9_facts_jsonl.py`
- `/home/user/OpenMythos/metrix/e1-pilot/audit/r9_compare.py`

**复用的我自己的脚本（换成本提交）**：`r8_fetch.py`、`r8_anchor.py`、`r8_facts.py`、`r8_s_cands.py`、`r8_templates.py`、`r8_tokenizer.py`、`r8_general.py`。

**完整 stdout**：`/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/87a244db28a901f9e89282b50df76778ab5c2887/`，共 01–12 号文件。每个文件第一行是完整命令，最后是 `RESULT` 和 `exit`。

---

## 第 1 项：协议与三个 JSON 的字节哈希，以及与 v1 的差异

**命令**（输出见 `01_r9_files.txt`）
`SP=/tmp/claude-0/-home-user/1df4d82a-900e-5f17-b09e-42f6e2f7c762/scratchpad; cd /home/user/OpenMythos/metrix/e1-pilot/audit; bash run_logged.sh stdout/87a244db28a901f9e89282b50df76778ab5c2887/01_r9_files.txt $SP/venv/bin/python -I -B r9_files.py /home/user/OpenMythos 87a244db28a901f9e89282b50df76778ab5c2887 8a49c087 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa /home/user/OpenMythos/metrix/e1-pilot/reports/round9/t5_frozen_hashes_87a244db.txt`

**原始输出摘录**
```
commit 87a244db28a901f9e89282b50df76778ab5c2887 | parents 8a49c0875c1479f01f2a12552a4c68733d0117aa | author date 2026-11-22T10:12:04+00:00 | committer date 2026-11-22T10:12:04+00:00
HEAD 87a244db28a901f9e89282b50df76778ab5c2887 | HEAD == commit True
commits after v1 that touch the four files: ['87a244db28a901f9e89282b50df76778ab5c2887'] | only the commit under audit: True
PROTOCOL_FROZEN: commit blob sha256 299f4fcf1dc69b88bca3d24c344206fbd51f93c8d0a796774df94d56720f2bdf | working tree identical: True
   87a244db blob: bytes 85203 | sha256 1e80ca31ed8bb95dca4c09bc74d424a92ed85417f1285512d521cf5315831308 | git blob id 7f39e291... (recomputed 7f39e291...)
   git show bytes == cat-file bytes: True | working tree ... == blob: True | HEAD blob == blob: True | git diff --quiet exit 0
   Executor t5 value(s) ['1e80ca31...1308'] | == auditor: True
   v1 6a474e4a blob: ... sha256 141473498582... | PROTOCOL_FROZEN 141473498582... | Executor t5 v1 ['141473498582...'] | all equal: True
AUDIT_VALUE file_sha256:METRIX_E1_PROTOCOL.md 1e80ca31ed8bb95dca4c09bc74d424a92ed85417f1285512d521cf5315831308
AUDIT_VALUE file_sha256:DATA_MANIFEST.json d1c32cdd297f70f418c4f7ad7b67742ac18482b4f0a57fd6b7bebe67b11ab911
AUDIT_VALUE file_sha256:SPLIT_MANIFEST.json 8c2c46a1d012beb4afe4e0ed0466689297fb97caaee3cda4c55b4261338caf5f
AUDIT_VALUE file_sha256:SEARCH_SPACE.json aa59e2e7d6599d8605f40513d702f3c4b1ccb98ab0678155e91d65f243259462
(v1: 141473498582… / 94ba8516… / 7eb5d6ed… / 490d575d…, all == PROTOCOL_FROZEN and Executor t5 v1 lines)
-- DATA_MANIFEST.json: parsed without duplicate keys | structural differences: [('/version', 'value', 'v1', 'v1.1')] | only /version v1 -> v1.1: True
   v1 bytes contain '"version": "v1",' 1 time(s); replacing it by '"version": "v1.1",' gives the v1.1 bytes exactly: True
-- SPLIT_MANIFEST.json: ... [('/version', 'value', 'v1', 'v1.1')] ... True ... True
-- SEARCH_SPACE.json:  ... [('/version', 'value', 'v1', 'v1.1')] ... True ... True
   status v1 'PROTOCOL_FROZEN' -> v1.1 'PROTOCOL_FROZEN' | frozen v1 'Owner 批准，2026-11-22 05:27 UTC' -> v1.1 'Owner 批准，2026-11-22 05:27 UTC'
distinct 64-hex values: v1 3 | v1.1 3 | in v1 not in v1.1 [] | new in v1.1 []
section-7 inline copy of SEARCH_SPACE.json parses; == SEARCH_SPACE.json (parsed): True | ... | inline version: v1.1
RESULT: PASS
```

**结论**
- 四个文件的字节都用 `git cat-file` 和 `git show` 从 87a244db 读取。工作区、HEAD、`git diff --quiet` 三处都与该提交相同，也没有 gitattributes 换行转换。
- 新 sha256 与 Executor 的 `t5_frozen_hashes_87a244db.txt` 一致，也与 Executor 提交前 `round9/t1_protocol_checks.txt` 中的 sha256sum 一致（见 10 号输出）。
- v1 的四个文件哈希与 PROTOCOL_FROZEN 一致，也与 t5 中的 v1 行一致。
- 三个 JSON 在结构上只有 `/version` 一处由 v1 改为 v1.1，字节上也只差这一处替换。
- 无差异。

## 第 2 项：全部数据哈希复算，并与 v1 和本提交比对

**命令**（cwd 为 audit/；`O=stdout/87a244db28a901f9e89282b50df76778ab5c2887`；`DL=$SP/auditor_87a2/dl`；`W=$SP/auditor_87a2/work`；每条都经 `bash run_logged.sh $O/<编号文件> ...` 运行）
- 02：`$SP/venv/bin/python -I -B r8_fetch.py $DL`
- 03：`... r8_anchor.py /home/user/OpenMythos 87a244db28a901f9e89282b50df76778ab5c2887 $DL/parquet/data/sample-100BT/train/shard_00000.parquet $DL/qwen_tok $W`
- 04：`... r8_facts.py /home/user/OpenMythos 87a244db… $DL/qwen_tok $W/anchor_texts.json $W`
- 05：`... r8_s_cands.py /home/user/OpenMythos 87a244db… $W/facts.json $W`
- 06：`... r8_templates.py /home/user/OpenMythos 87a244db…`
- 07：`... r8_tokenizer.py /home/user/OpenMythos 87a244db… $DL/qwen_tok $SP/auditor_87a2/hfcache`
- 08：`... r8_general.py /home/user/OpenMythos 87a244db… $DL/parcae_tok/tokenizer.json`
- 09：`... r9_facts_jsonl.py /home/user/OpenMythos 87a244db… 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa $W/facts.json $W/train_S.jsonl $DL/qwen_tok $W`
- 10：`... r9_compare.py /home/user/OpenMythos 87a244db… 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa $O`
- 11：反向自测。把 05 号的副本中 train_S 的值改动 1 个字符后再跑 r9_compare，结果是 `ALL EQUAL False`、`all values equal: 44/45`、`RESULT: FAIL`、`pipeline status 1`，说明比对脚本能检出不一致。

02–09 号全部是 `RESULT: PASS`、`exit=0`。

**原始输出摘录**（`10_r9_compare.txt`；每行依次为：auditor 值 | PROTOCOL_FROZEN 表值 | 6a474e4a manifest | 87a244db manifest | Executor t5 的 v1 值 / 本提交值）

| 项 | auditor 值 | 结果 |
|---|---|---|
| facts（160 条） | 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97 | 五方相同 |
| facts（按 v1.1 第 2.2 节从 facts.jsonl 读回重算） | 406c8801… | 五方相同 |
| 锚文本 512 篇解码文本 | 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 | 五方相同 |
| 锚文本源 parquet | 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22 | 前四方相同；Executor t5 没有打印这一项 |
| train_S.jsonl | 686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e | 五方相同 |
| candidates.json | e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705 | 五方相同 |
| template_set_sha256 | 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f | 五方相同；32 个单模板值都与两个 manifest 相同（06 号：`32/32`） |
| Qwen tokenizer.json | aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 | 五方相同 |
| Qwen tokenizer_config.json | d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101 | 五方相同 |
| Qwen vocab.json | ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 | 五方相同 |
| Qwen merges.txt | 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 | 五方相同 |
| parcae tokenizer.json | e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | 五方相同 |
| eval_sets.jsonl（只对整个文件求哈希） | 8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | 五方相同 |

10 号输出汇总行：
```
all 12 PROTOCOL_FROZEN data rows mapped: True
data rows: 45 | all values equal: 45/45
auditor values not used in the table: []
RESULT: PASS
```

**其他检查结果**
- **下载来源（02 号）**：三个固定 revision 在 Hub 上都解析回自身。7 个下载文件的大小和 LFS sha256 / git blob id 都与 Hub 元数据一致（`MATCH True`）。
- **分词器文件（07 号）**：该 revision 的仓库树里，分词器文件正好是 manifest 列出的 4 个。transformers 实际请求的分词器文件也是这 4 个。只含这 4 个文件的目录加载出的分词器与从 Hub 加载的相同，词表、特殊 token、探针编码和 chat template 都一致。
- **eval_sets.jsonl（08 号）**：工作区、87a244db 和基线 61d3c767 三处的 blob 相同（`71d6c7b5…`）。
- **v1.1 第 2.2 节的 fact 比对方法（09 号）**：
  - 把重新生成的 fact 写成 facts.jsonl，按行读回后的 JSON 列表规范化哈希等于 406c8801…（`MATCH True`）。
  - 按 JSONL 规则得到的 canonical_sha256 是 `e05561ac…`，与上面的值不同。这符合 2.2 节「不与此值比对」的写法。
- **候选可行性（09 号，同 relation、同 stratum、同暴露类别、同答案 token 数四重约束）**：16 个 cell 中，learned 每个 fact 有 15 个候选，unread 有 5 个。最小值 5；不足 4 个的 cell：`[]`。
- **split（09 号）**：160 个 fact_id 互不相同，其中 learned 120 个、unread 40 个，两者交集为空。每个 cell 的 learned 编号为 01–15，unread 为 01–05。train_S 中出现的 id 正好等于 learned 集合。
- **L1（06 号，仅供参考）**：TRAIN / DEV / TEST / Y 四组模板的 normalized_sha256 两两交集为 `[]`。
- **其他泄漏检查**：L2–L6 不在本次指令范围内，没有重跑。L6 的 TEST 部分按定义第 12 行禁止执行。

**是否与 Executor 一致**：一致。t5 中两个各 11 个值的列表（6a474e4a 与 87a244db）全部等于 auditor 值。

## 只登记、不修改的观察

1. **MINOR**：三个 JSON 的 `frozen` 字段在 v1.1 中仍是 `"Owner 批准，2026-11-22 05:27 UTC"`（v1 的批准时间），`version` 已经是 v1.1。这与指令第 1e 项「只同步版本字段」一致，协议第 14 节 v1.1 行也写明了「`frozen` 字段不变」。但只看 JSON 的人看不到 v1.1 的批准时间（09:44 UTC）。
2. **MINOR**：Executor 的 `t5_frozen_hashes_87a244db.txt` 对每个 revision 只列了 11 个数据值，没有锚文本源 parquet 的 sha256；PROTOCOL_FROZEN 表有 12 行。auditor 复算的这一值与 PROTOCOL_FROZEN 和两个 manifest 都相同，所以不影响结论，只是 Executor 本轮的原始输出少覆盖了 1 行。
3. **说明**：Executor 的 t0_env 写明本轮没有下载、没有生成数据、没有加载分词器。所以本轮从数据重新算出哈希的只有 auditor；Executor 的 t5 是从两个提交的 git 对象中读出 manifest 字段再比对。
4. **说明**：运行期间工作区新出现了 `metrix/e1-pilot/reports/round9/t0_env.txt`。文件 mtime 是 10:14:45 UTC，文件头写着「Written by the Executor」，不是 auditor 写的。Executor 的 t5 在审计前后的 sha256 都是 `5d9a83bd…`，没有变化。
5. **信任状态**：按 `metrix/CLAUDE.md` 第 10 节，data-auditor 仍为「待验证」，本 PASS 仅作参考。

## git status --short（运行后原始输出，见 `12_git_status_final.txt`）
```
?? metrix/e1-pilot/audit/r9_compare.py
?? metrix/e1-pilot/audit/r9_facts_jsonl.py
?? metrix/e1-pilot/audit/r9_files.py
?? metrix/e1-pilot/audit/stdout/87a244db28a901f9e89282b50df76778ab5c2887/
?? metrix/e1-pilot/reports/round9/t0_env.txt
?? metrix/e1-pilot/reports/round9/t5_frozen_hashes_87a244db.txt
?? metrix/e1-pilot/reviews/87a244db28a901f9e89282b50df76778ab5c2887/
exit=0
```
auditor 只写入了 `metrix/e1-pilot/audit/` 下的上述 3 个脚本和 stdout 目录。其余未跟踪项都是 Executor 的文件：t5 和 reviews 目录在审计开始前已存在，t0_env 是 Executor 在 10:14:45 写入的。没有已跟踪文件被修改。

结论：PASS
