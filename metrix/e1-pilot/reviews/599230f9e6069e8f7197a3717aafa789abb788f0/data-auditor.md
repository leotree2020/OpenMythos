# data-auditor raw output — Round 6 task 5, range f4d8e988..599230f9e6069e8f7197a3717aafa789abb788f0 (2 commits)
# Invoked by the Executor via Agent(subagent_type="data-auditor") in session_01J5mxaY5Chc3QrL468Vrs7f, started 2026-11-21 ~14:42:57Z; stopped at 14:49 by the usage limit (interruption.txt); resumed 2026-11-22 ~02:17Z with SendMessage (resume_message.txt).
# Invocation text: data-auditor_prompt.txt (same directory), sent verbatim. Its scripts: metrix/e1-pilot/audit/r6_*.py and the changed r5_kl_denoms.py; complete stdout of every run: metrix/e1-pilot/audit/stdout/599230f9e6069e8f7197a3717aafa789abb788f0/.
# Below the line: the final report, copied unchanged from the subagent's transcript (~/.claude/projects/<project>/subagents/agent-<id>.jsonl) by reports/round6/review_extract.py. The harness delivered it to the Executor with every line indented by 2 spaces; that indentation is not part of the report.
---
# Data Auditor 报告:Metrix E1-PILOT 第 6 轮,f4d8e988a31f99527cc0bc6be5ceacc709bda2f1..599230f9e6069e8f7197a3717aafa789abb788f0

本轮结论为 BLOCK。A–D 四项与上次复算的 4 个标准项全部与 Executor 一致;唯一不一致在 E 的覆盖范围:本轮新写的 `guard_ab.sh`、`guard_fail.sh` 按 Executor 自己的标准属于检查脚本,却没有异常保护,范围清单里也没有提到它们。这一点是对「检查脚本」的解释,Review Gate 可以裁决推翻。

## 运行情况

- **环境**:主机 `vm`,Linux 6.18.44,4 CPU,只用 CPU。Python 3.13.18(venv),transformers 5.22.2,tokenizers 0.23.3。torch 不可导入,没有 nvidia-smi,两个分词器目录里没有权重文件。只加载了分词器。
- **中断与续做**:01–05 号运行在 2026-11-21 14:47–14:49 UTC,中断前完成;06–15 号在 2026-11-22 02:17–02:21 UTC,容器重启后运行。
- **重启后的核对**:
  - 01–05 号 stdout 都完整,都以 `exit=0` 结尾。
  - 我写的脚本都能被 ast 解析。
  - scratchpad 里的中间文件与当时打印的值一致:`anchor.json` sha256 为 `8828bc4f…2408`,截断 id 列表哈希为 `f15615a4…5929`,两个窗口哈希也对得上。
  - HEAD 仍是 599230f9。
- **仓库中没有 PROTOCOL_FROZEN 文件**(01 号:`tracked … PROTOCOL_FROZEN: [] | on disk: []`;状态行为 AWAITING_REVIEW_GATE)。
  - 对 `eval_sets.jsonl` 的 test 行,只在行首 80 个字符内定位了 `split` 字段并计数,结果是 dev 400、test 800。
  - test 行没有做 JSON 解析,没有解码,也没有用任何字段计算;另外只对整个文件求了 sha256。
  - 没有生成或实例化任何 TEST 问句或 general_test 窗口。
- **路径与输出**:
  - 下文 `S=/tmp/claude-0/-home-user/efb84705-9920-5c9c-9d1c-c122dfd71ce8/scratchpad`。
  - 每个 stdout 文件开头有完整的原始命令行。所有 stdout 在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/599230f9e6069e8f7197a3717aafa789abb788f0/`,共 15 个文件,每次运行一个。
  - 中间数据在 `/tmp/claude-0/-home-user/efb84705-9920-5c9c-9d1c-c122dfd71ce8/scratchpad/audit_r6/`,没有写进仓库。
- **本轮新写的脚本**都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/`:`r6_guard.py`(我自己的异常保护)、`r6_env.py`、`r6_sources.py`、`r6_anchor.py`、`r6_general.py`、`r6_compare.py`、`r6_guard_audit.py`。另外修改了 `r5_kl_denoms.py`。
  - 它们都不导入、不调用、不复制 Executor 的代码。
  - Executor 生成的文件(`$S/r6/*.json`、`reports/round6/t2_l6_check.txt`)只在 `r6_compare.py` 里作最后比对用。

---

## A. 1a:L6(DEV 部分),判定单位为 `str.split()`

**命令**
1. `05`:`$S/venv/bin/python -I -B r6_general.py <eval_sets.jsonl> $S/dl/parcae_tok/tokenizer.json $S/dl/qwen_tok ../DATA_MANIFEST.json ../SPLIT_MANIFEST.json ../METRIX_E1_PROTOCOL.md $S/audit_r6/anchor.json $S/audit_r6/anchor_ids.json $S/audit_r6/general_summary.json`
   - 锚文本由 `03`(`r6_anchor.py`)从固定的 parquet 自建。
2. `10`:`r6_compare.py`,与 Executor 的结果比对。

**原始输出**(`05_r6_general.txt`)
```
eval_sets rows by split (split field only): {'dev': 400, 'test': 800}
dev windows kept per domain: {'books': 25, 'c4': 25, 'fineweb': 25, 'wikitext': 25} | other domains: []
rows decoded by split (counted inside decode_row): {'dev': 100} | test rows decoded: 0
general DEV canonical sha256, list of window texts (...): 363aa08742d46776e725715d0ee4c5ae9c4de1ddf96396eb333803ce818587c8
general DEV canonical sha256, list of token-id lists (same order): 2e30c443da0b09f385ba5f327d40fb051080c12dc7bc0d3cb873f0a0b01d598f
== item 1a: L6 (DEV part); anchor texts: 512 canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408
unit ws  (str.split(), JUDGED): units anchor 50413, general 18983 | shared distinct n-grams n=1..13: [2878, 2178, 454, 68, 14, 5, 3, 2, 1, 0, 0, 0, 0] | longest shared n <= 13: 9
unit tok (encode of both texts): units anchor 65531, general 24877 | shared ... [3784, 3467, 1030, 270, 106, 25, 8, 5, 4, 3, 2, 1, 0] | longest shared n <= 13: 12
unit tokid (ids fed: anchor trunc ids / window ids): ... [3784, 3467, 1030, 270, 106, 25, 8, 5, 4, 3, 2, 1, 0] | longest 12
unit w   (\w+ casefold, comparison only): units anchor 51199, general 18521 | ... [2858, 2718, 606, 94, 21, 6, 4, 2, 1, 0, 0, 0, 0] | longest 9
L6 (DEV part) shared word 13-grams, word = str.split(): 0; limit 0 -> within limit
report only, no limit: Qwen token 13-grams (encode of texts) 0 | (ids fed) 0 | \w+ casefold 0
RESULT: PASS
```

**与 Executor 是否一致:一致。** `10_r6_compare.txt` 显示 `compared items: 18, equal: 18, different: 0`。比对项包括:
- 窗口数与长度分布;
- 两个规范化哈希与锚文本哈希;
- 各 split 的行数,以及按 split 计的解码行数;
- ws、w、tok 三个单位的单位总数、n=1..13 的共享数和最长共享 n;
- 判定行、`RESULT: PASS` 与 `exit=0`;
- Executor 的 `general_dev.json`:100 个窗口的 ids 与文本逐个相同;
- Executor 的 `anchor.json`:哈希相同。

**差异:无。**

## B. 1b:每个窗口最多 256 token,不足则取全长

**命令**:同 A(`05_r6_general.txt` 中的 item 1b 段)。

**原始输出**
```
windows: 100 | lengths {len: count}: {172: 1, 182: 1, 216: 1, 229: 1, 231: 2, 232: 1, 233: 1, 234: 1, 236: 1, 237: 1, 238: 1, 241: 1, 242: 1, 243: 2, 244: 2, 245: 3, 246: 4, 247: 4, 248: 2, 249: 3, 250: 5, 251: 5, 252: 2, 253: 6, 254: 4, 255: 8, 256: 36}
exactly 256: 36 | shorter than 256: 64 | shortest: 172 | longest: 256 | longer than 256: 0
per domain (min, max, number shorter than 256): {'books': (172, 256, 24), 'c4': (216, 256, 18), 'fineweb': (233, 256, 11), 'wikitext': (245, 256, 11)}
windows whose length == min(256, full Qwen length of the decoded row) (first 256, else full length): 100 of 100
windows where encode(window text) != window ids: 0 | re-encoded window text longer than 256: 0
```

**与 Executor 是否一致:一致。** 长度分布与 `t2_l6_check.txt` 完全相同(10 号文件中显示 EQUAL)。

**差异:无。**
- 协议第 2.7 节的新句子与 `DATA_MANIFEST general_text.window_rule` 都在(05 号文件前几行)。
- 没有窗口超过 256 token;按 id 计和按重新编码的文本计都是如此。

## C. 1c:n_x = 实际送入模型的 id 序列长度;修正 `r5_kl_denoms.py`

**命令**
1. `03`:`r6_anchor.py $S/dl/parquet/data/sample-100BT/train/shard_00000.parquet $S/dl/qwen_tok ../DATA_MANIFEST.json $S/audit_r6`
2. `04`:`r5_kl_denoms.py $S/dl/qwen_tok $S/audit_r6/anchor.json $S/dl/parquet/data/sample-100BT/train/shard_00000.parquet`

**对 `r5_kl_denoms.py` 的修正**
- 删掉写死的 `[128] * 512`,改为 `n_tr = [len(enc(tok, d)[:128]) for d in docs]`,直接从 parquet 文档计算。
- 与「截断后解码再重新编码」的长度逐篇比较。
- 加了异常保护。用法改为 3 个参数。

**原始输出(03)**
```
rows read 527, documents kept 512 (truncate_to_model_tokens 128)
full (untruncated) token count: min 123 | documents with fewer than 128 tokens: [(340, 123)]
truncated id length {len: count}: {123: 1, 128: 511}
re-encoded length of the decoded text {len: count}: {123: 1, 128: 511}
documents where len(re-encoded) != len(truncated ids): []
documents where re-encoded ids != truncated ids (any position): []
canonical sha256 of the 512 texts: 8828bc4f...2408 | == round 2-5 value ... True
```

**原始输出(04)**
```
decode(truncated ids) == my anchor text for all 512: True
truncated id length n_x {n: count}: {128: 511, 123: 1} | documents with n_x != 128: [(340, 123)]
per document: len(truncated ids) != len(re-encoded): [] | truncated ids != re-encoded ids: []
  s = 0..299, n_x = len(truncated ids): denominators {value: steps} {503: 2, 508: 298} | min 503 max 508 sum 152390 | steps with denominator != 508 (denominator, documents): {85: (503, [340, 341, 342, 343]), 213: (503, [340, 341, 342, 343])}
  (s = 0..299 / 1..300 × 截断 id / 重新编码,四种组合结果相同)
step 85 ... document share of the KL term (token-weighted) [0.2425, 0.2525, 0.2525, 0.2525]
```

**与 Executor 是否一致:一致。** Executor 在 `reports/round4/t1_anchor_short_docs.txt` 和 ROUND5_REPORT 待决第 6 项里说:第 340 篇只有 123 token,往返编码相同,分母为 503 与 508。我的复算相同。

**差异:无。** 需要说明的是,我第 5 轮观察 3 的前提是错的:截断 id 的分母并不是全为 508,该错误来自写死的 128,本轮已修正。

## D. 1h:两个 sha256 已锁定

**命令**:`02`:`r6_sources.py /home/user/OpenMythos <eval_sets.jsonl> $S/dl/parcae_tok/tokenizer.json`;`01`:`r6_env.py … --hub`,核对文件身份。

**原始输出(02)**
```
eval_sets.jsonl        8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155 | DATA_MANIFEST general_text.source_file_sha256 8816fe5a...a155 | equal True
parcae tokenizer.json  e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | DATA_MANIFEST general_text.decode_tokenizer_json_sha256 e0021e26...ea77 | equal True
Stage 1 manifest.json["eval_sets.jsonl"]   8816fe5a...a155 | == local file sha256 True | == DATA_MANIFEST True
Stage 1 data_lock.json["tokenizer_sha256"] e0021e26...ea77 | == local file sha256 True | == DATA_MANIFEST True
(eval_sets.jsonl / manifest.json / data_lock.json: tracked True | working tree == HEAD True | == base 61d3c767 True | changed base..HEAD: False | last commit b975092 2026-11-09)
general_text keys f4d8e988 -> 599230f9: added ['decode_tokenizer_json_sha256', 'source_file_sha256', 'window_rule'] | removed [] | changed []
protocol 2.7 contains `8816fe5a…a155`: True ; `e0021e26…ea77`: True
RESULT: PASS
```

01 号还确认了以下文件的 sha256 与第 5 轮记录相同,也与固定 revision 下 Hugging Face Hub 的元数据相同(`MATCH True`,共 8 个文件):Qwen 分词器的 6 个文件、parcae `tokenizer.json`、parquet。

**与 Executor 是否一致:一致。** Executor 的 `t2_l6_check.txt` 前两行为 `match True`。

**差异:无。**

## E. 第 2 项:脚本改动

**命令**
- `14`:`r6_guard_audit.py /home/user/OpenMythos f4d8e988… 599230f9…`。这是修正后的版本;11、12 号是修正前的两次运行,见文末「我自己的问题」。
- 此外还有 10 号(用我自己的数据核对 `l6_check.py` 应输出的数值)。

**1. 「test rows decoded」是否改为实际计数,判定是否按 1a:是。** 14 号第 6 段原文:
```
module constants: {... 'JUDGED': "'ws'", ...}
verdict assignment(s): ['ok = result[JUDGED] == 0']
print(s) containing 'test rows decoded': ["print('rows decoded by split: %s | test rows decoded: %d' % (dict(sorted(decoded_by_split.items())), decoded_by_split['test']))"]
nested def decode_parcae: decoded_by_split[r['split']] += 1 ; return ptok.decode(r['tokens'], skip_special_tokens=True)
checks on the decode counter: ["if set(decoded_by_split) != {'dev'}:\n    sys.exit('rows other than dev rows were decoded')"]
json.loads at line(s) [91]; `if split != 'dev': continue` at line(s) [89]; parse only after the dev filter: True
```
- `ptok.decode` 只在 `decode_parcae` 里调用;w 和 tok 两个单位只打印、不参与判定。
- 与 `t2_l6_judgment_demo.txt` 吻合:ws 有 1 个共享 13-gram 时 FAIL;只有 tok/w 有共享时仍 PASS。
- 用我自己的数据算出的所有数值都与 `t2_l6_check.txt` 相同(见 A)。

**2. 正常路径是否未变:未变(AST 证据)。** 14 号第 2、3 段:
- 11 个已有的受保护脚本,去掉 `run_guarded` 与 `__main__` 块后,AST 与 f4d8e988 完全相同:含 docstring 比较为 True,不含 docstring 比较也为 True。
- `records_check.py`:`new def main() body == old __main__ body: True`。
- `l6_check.py` 按设计有改动,被检出为 CHANGED/added,即 `HEAD`、`JUDGED`、`N`、`ngrams`。这本身也说明比较方法能检出差异。
- `table_check.py` 是本轮新增文件,在 diff 中标为 A。
- 12 个文件里的 `run_guarded` AST 只有 1 种,`__main__` 块都正好是 `run_guarded(main)`。

**run_guarded 逻辑**:按源码推理,未执行 Executor 代码。
- `main()` 正常返回,或以 None/0/1 退出:原样通过,所以输出与退出码不变。
- 字符串退出码:打印信息与 `RESULT: FAIL`,退出码 1。
- 非 0/1 的整数(例如 argparse 的 2):打印 `RESULT: FAIL`,退出码不变。
- 其它任何 BaseException:先打 traceback,再打印 `RESULT: FAIL`,退出码 1。

**3. 覆盖范围是否完整:不完整。** 这是本报告唯一的不一致项。
- Executor 在 ROUND6_REPORT.md(未跟踪,不在审计区间内)给出的标准是:「输出通过/不通过判定的脚本(RESULT 行、PASS/FAIL 或 inside/OUTSIDE 字样,或按判定设置退出码)… 共 12 个」。没加保护的只列了 7 个 .py 外加 `l6_judgment_demo.py`。
- 14 号第 7 段显示,本轮新写的 `reports/round6/guard_ab.sh` 与 `guard_fail.sh` 符合这条标准:
  - 两者都打印 True/False 判定;
  - 最后一行 `[ "$same_all" = "${#cases[@]}" ]` / `[ "$ok_all" = … ]` 就是判定退出码;
  - 两个脚本只有 `set -u`,没有 `set -e`。
- 但它们在任何路径上都不打印 `RESULT: FAIL`,Executor 的范围清单也没有提到它们。
- 按源码推断(未运行,因为不得调用 Executor 代码):缺参数时 `set -u` 会报 unbound variable、以 1 退出;cmp 失败时最后一行判定为假、以非 0 退出。所以它们会非 0 退出,但缺少 `RESULT: FAIL` 这一行。

**与 Executor 是否一致**
- 「test rows decoded」与判定:一致。
- 12 个受保护脚本的异常路径与正常路径:一致。
- 范围:不一致。按 Executor 自己的标准应有 14 个,另 2 个未覆盖。

**差异**:`guard_ab.sh`、`guard_fail.sh` 未满足「遇异常须打印 RESULT: FAIL」。修法有两种,任选其一:
1. 给这两个脚本加错误处理和 RESULT 行;
2. 由 Review Gate 裁定测试用的 harness 不算「检查脚本」,并在报告里把标准写准确。

**以下观察不构成 BLOCK**
- (a) 检查失败(不是异常)时的路径:
  - `anchor_check.py`、`blind_handback_check.py`、`records_check.py`、`recover_blind.py` 以 1 退出但没有 RESULT 行,判定只体现在文字或计数里。`run_guarded` 会把 1 原样放行。
  - `template_overlap.py`、`y_ratio.py` 检查失败时仍以 0 退出,判定只在文字里。
  - 这些都是原有行为,也不在第 2 项「遇异常」的字面范围内。
- (b) `y_ratio.py`、`candidate_feasibility_r3.py`、`verify_scoring.py` 在模块顶层导入同目录的 `names` / `scoring_input`,位置在保护之外。导入失败时只有 traceback、退出码 1,没有 `RESULT: FAIL`。风险低。
- (c) 有 3 个脚本只输出计数、不输出判定:`round4/anchor_short_docs.py`、`round5/em_special_tokens.py`、`round1/candidate_feasibility.py`。前两个的输出在协议第 14 节被引作证据。Executor 明确把它们排除在范围外,请 Review Gate 确认。

---

## 复算项目 1–4(标准项,在 HEAD 的 manifest 上重跑)

| 项 | 命令(stdout 文件) | 原始输出要点 | 与 Executor |
|---|---|---|---|
| 1 哈希 | `06` `r4_regen_facts.py`;`07` `a4_cands_templates.py`;`03`、`05` | facts canonical `406c8801…6b97`(MATCH True,与 Executor 的 facts.json 内容相同);32 个模板与 manifest 的 hash 不一致数 0;`template_set_sha256` 为 `2b524113…e28f`,match True;锚文本 `8828bc4f…2408`;general DEV 的两个哈希同 A。DATA_MANIFEST 中各数据文件仍是 NOT_GENERATED/null,无可比对的值 | 一致 |
| 2 L1–L6 | `07`、`08` `a1_facts.py`、`09` `r4_leak_supp.py`、`05` | L1 重复数 0;L2 最大 0.2(上限 0.25);L3a 与 L3b 都是 0;L4(DEV)为 0;L5 交集 0、重复 0;L6(DEV,str.split())为 0。涉及 TEST 的部分没有运行(没有 PROTOCOL_FROZEN) | 一致 |
| 3 候选可行性 | `07` | 16 个池按 relation × stratum × exposure × K_st 四重约束划分;同一 (relation, stratum, exposure) 组内 token 数不分裂;最小池 5(unread 池,可用干扰项 4);不足 4 的 cell 为 0 | 一致 |
| 4 split | `08`、`05` | fact_id 共 160 个互不相同,learned 与 unread 交集 0;learned 120、unread 40,每个 cell 15/5;DEV 问句 320 = 160×2;TRAIN 120;general DEV 100 = 25×4;eval_sets 的 dev/test 行数为 400/800(只计数) | 一致 |

06–09 号用的是此前已入库的旧 auditor 脚本,它们没有异常保护;本轮规则只覆盖新写的脚本。四次运行都是 `exit=0`、没有 traceback,没有触发异常路径。

## 我自己的问题(已修正)
- **11 号的标签错误**:`r6_guard_audit.py` 第一次运行的第 4 段标签有误,例如把 `raise SystemExit('…')` 标成「原样放行」。12、14 号已改正,其余行与 11 号逐行相同。
- **假 PASS**:13 号(我的脚本在异常时 FAIL 的演示)暴露出 `r6_guard_audit.py` 在旧 revision 不存在时给出假 PASS。
  - 已改为先 `rev-parse --verify` 两个 revision,并要求旧版本缺失的文件在 diff 中标为 A。
  - 15 号:不存在的 revision 现在输出 `RESULT: FAIL (exception)`、`exit 2`。
  - 14 号是修正后对正确区间的运行,结论不变。
- **异常演示**:13 号中我本轮的 7 个脚本在缺参数或缺文件时,都输出且只输出一行 `RESULT: FAIL (exception)`,退出码为 2。

## `git status --short` 原始输出(最后一次运行,HEAD 599230f9e6069e8f7197a3717aafa789abb788f0)
```
 M metrix/e1-pilot/audit/r5_kl_denoms.py
?? metrix/e1-pilot/audit/r6_anchor.py
?? metrix/e1-pilot/audit/r6_compare.py
?? metrix/e1-pilot/audit/r6_env.py
?? metrix/e1-pilot/audit/r6_general.py
?? metrix/e1-pilot/audit/r6_guard.py
?? metrix/e1-pilot/audit/r6_guard_audit.py
?? metrix/e1-pilot/audit/r6_sources.py
?? metrix/e1-pilot/audit/stdout/599230f9e6069e8f7197a3717aafa789abb788f0/
?? metrix/e1-pilot/reports/DEFERRED_MINORS.md
?? metrix/e1-pilot/reports/ROUND6_REPORT.md
?? metrix/e1-pilot/reports/round6/review_extract.py
?? metrix/e1-pilot/reports/round6/t1_protocol_checks_599230f9.txt
?? metrix/e1-pilot/reports/round6/t4_after_restart.txt
?? metrix/e1-pilot/reviews/599230f9e6069e8f7197a3717aafa789abb788f0/
```

`audit/` 以外的未跟踪文件都不是我写的,stat 时间如下:
- `ROUND6_REPORT.md` 为 11-21 14:46:20;`review_extract.py` 为 14:46:35;`reviews/` 下的 prompt 与 diff 为 14:41–14:42。这些都早于我第一次写入的时间 14:47。
- `interruption.txt`、`resume_message.txt` 为 11-22 02:16:38;`t4_after_restart.txt` 为 02:16:50。
- `code-reviewer.md` 为 02:19:24;`t1_protocol_checks_599230f9.txt` 为 02:19:43;`DEFERRED_MINORS.md` 为 02:19:56。
- 最后这几个文件是我工作期间由 Executor 或协调方写入的。

我只写入了 `metrix/e1-pilot/audit/` 与 scratchpad。按 metrix/CLAUDE.md 第 10 节,data-auditor 仍为「待验证」,本结论仅作参考。

结论：BLOCK
