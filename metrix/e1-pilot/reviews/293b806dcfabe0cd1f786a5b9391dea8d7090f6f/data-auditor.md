# data-auditor final report, round 7, range fe321cd..293b806dcfabe0cd1f786a5b9391dea8d7090f6f; invoked 2026-11-22 03:27 UTC (background); stopped by HTTP 429 before handing back (interruption.txt); resumed about 03:48 UTC with resume_message.txt; invocation text: data-auditor_prompt.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-afbf454a35fc2a174.jsonl)
---
仓库文件 `.claude/agents/data-auditor.md` 的 tools 行（第 4 行）：`tools: Read, Grep, Glob, Write, Bash`。
该文件的 sha256 为 4201122829c3…，与用户级副本相同（见 reviews/293b806…/preflight_tools_check.txt），所以本次按仓库定义执行。

# Metrix E1-PILOT 第 7 轮数据审计（fe321cd..293b806dcfabe0cd1f786a5b9391dea8d7090f6f）

两个 1g 哈希都已用我自己的脚本复现，与 Executor 的文件逐字节相同。本轮 01–16 号运行全部 exit=0，没有发现 BLOCKER。

- **运行环境**：主机 vm（Anthropic 云容器），只用 CPU。没有 torch，没有模型权重，只有分词器文件。仓库中没有 PROTOCOL_FROZEN（01）。
- **中断与续跑**：上一次运行在 01–15 号全部完成后中断。按协调方要求，本次只补跑了 16 号 git status，其余检查没有重做。
- **输出位置**：每次运行的完整 stdout 放在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/293b806dcfabe0cd1f786a5b9391dea8d7090f6f/`，一次运行一个文件，开头是命令行。
- **本轮新写的脚本**：`/home/user/OpenMythos/metrix/e1-pilot/audit/` 下的 r7_s_cands.py、r7_general_dev.py、r7_text_items.py、r7_cands_exposure.py、r7_compare.py。它们出异常时打印 `RESULT: FAIL` 并以 2 退出，检查不通过时以 1 退出。
- **沿用的旧脚本**：r6_env.py、r6_anchor.py、r4_regen_facts.py、a4_cands_templates.py、a1_facts.py。
- **独立性**：没有 import、调用或复制 Executor 的代码。有一点需要说明：我读 review_input.diff 时看到了 gen_s_cands.py 的前约 60 行（diff 第 305–372 行），随即跳过了其余部分。我的实现只依据协议文字，写法也不同（例如按 fact_id 序号取 i）。
- **TEST 数据**：eval_sets.jsonl 用二进制模式读，test 行只定位 split 字节并计数，连 UTF-8 解码都没有做。没有实例化任何 TEST 问句或 general_test 窗口。

## 1. 第 1g 项：两个 sha256 的独立复现（必做项）

**命令**（`SP` 为 scratchpad，cwd 为 audit/）：
- 03：`$SP/venv/bin/python -I -B r4_regen_facts.py $SP/dl/qwen_tok $SP/audit_r7/anchor.json $SP/audit_r7/facts.json`，锚文本取自 02 号 r6_anchor.py 的输出。
- 04：`$SP/venv/bin/python -I -B r7_s_cands.py $SP/audit_r7/facts.json ../METRIX_E1_PROTOCOL.md ../DATA_MANIFEST.json ../SPLIT_MANIFEST.json $SP/audit_r7/run1`
- 05–07：同一脚本再跑三次，每次换解释器或 PYTHONHASHSEED，输出写到不同目录：
  - 05：`/usr/bin/python3.11`
  - 06：`/usr/bin/python3.12`
  - 07：3.13 加 `PYTHONHASHSEED=4711`
- 13：`r7_compare.py`。这是唯一读取 Executor 文件的脚本，只在最后做比对。

**原始输出**（03、04–07、13）：
- **160 条 fact**：规范化 SHA-256 为 `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97`，`MATCH: True`；锚文本规则拒绝 0 个名字（03）。
- **train_S.jsonl**：120 行，15033 字节，规范化 SHA-256 为 `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e`，equal True（04）。
- **candidates.json**：160 个键，10453 字节，规范化 SHA-256 为 `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705`，equal True（04）。
- **跨版本**：Python 3.11.18、3.12.3、3.13.18 三个解释器得到的两个哈希相同（05–07）。
- **每个 cell 的置换抽取次数**：`{"capital/natural": 3, "capital/random": 5, "currency/natural": 1, "currency/random": 6, "founder/natural": 2, "founder/random": 1, "river/natural": 2, "river/random": 6}`
- **其余核对**：
  - 两个哈希在 DATA_MANIFEST、SPLIT_MANIFEST 中的值和协议正文中的值都等于我的结果。
  - 写出的文件重新解析后，规范化字节与原字节相同。
  - 结构检查全部为 True：S 中没有不动点，每个 entity 和 answer 各出现 1 次，unread 出现 0 次，不含任何真实映射；每条 fact 4 个不同候选，真实答案恰好出现 1 次，干扰项都来自协议 2.5 规定的池。

**与 Executor 是否一致：一致。** 13 号比对结果：
- facts.json 的字节、512 篇锚文本的规范化列表都 IDENTICAL。
- 我的 run1、run2、run_py311、run_py312 与 Executor 的 gen1、gen2、gen3 逐字节比较，共 24 对，全部 IDENTICAL。
- Executor 记录的数值与我的输出也全部 IDENTICAL：每个 cell 的抽取次数、第一行 S 句与第一组候选、各 cell 的抽取次数与目标 (K_st, K_qa)、think 两个 token 的 id 与特殊标记、decode 的结果。

**协议文字能否唯一确定结果**：能。我把每一种合理的替代写法都算了一遍（04 号的 ALT 段），哈希都不同，而每一种都被协议里的一句话排除：

| 替代写法 | 排除它的协议原文 | 得到的哈希（前 8 位） |
|---|---|---|
| 用逆置换 | 2.6：`{A}` 取第 `p[i]` 条 fact 的 answer | c882c38b |
| 重抽时不重置 p | 2.6：用同一个 r 再从 `list(range(15))` 开始抽 | b0b61e7d |
| 记录里不写 answer_fact_id | 2.6：记录格式 | 8305be74 |
| 候选用 DATA_SEED 抽 | 2.5：`rng_rule(CANDIDATE_SEED, …)` | e75be66d |
| 池按字母排序 | 2.5：池按第 2.2 节的 fact 生成顺序排列 | d78a6a49 |
| `c = d + [a_f]` | 2.5：令 `c = [a_f] + d` | 26c0bf16 |
| 打乱池后取前 3 个，不用 sample | 2.5：`d = r.sample(池, 3)` | 223d5a91 |

协议文字之外唯一的依赖，是 CPython `random.Random` 的算法（见第 8 节 MINOR M4）。

关于指令 1g 原文“用 DATA_SEED 两次独立生成 … candidates.json”：如果候选真的用 DATA_SEED 抽，哈希会是 e75be66d。协议 2.5 的旧文与新文都写 CANDIDATE_SEED；Executor 按协议做，并在 t1g_gen_s_cands.txt 的开头写明了这一点。我判为一致，这里只作说明。

## 2. 模板哈希与数据哈希（标准项 1）

**命令**：01 r6_env.py（加 `--hub`）、02 r6_anchor.py、11 a4_cands_templates.py、08 r7_general_dev.py、14 `bash -c 'git show HEAD:<f> | sha256sum …'`

**原始输出**：
- **分词器与源文件（01）**：6 个分词器文件、parcae tokenizer.json、parquet 与第 5 轮的记录相同，与 Hub 元数据比对 MATCH True；没有权重文件。
- **锚文本（02）**：parquet 的 sha256 与固定值一致；512 篇文本的规范化 SHA-256 为 8828bc4f…，与第 2–6 轮相同。
- **模板（11）**：32 个模板逐条复算后 0 个不一致；template_set_sha256 为 2b524113…，与 manifest 一致；协议 2.4 节的表格与 manifest 中的模板文本相同。
- **通用文本源（08）**：eval_sets.jsonl 为 8816fe5a…，parcae tokenizer.json 为 e0021e26…，两者都等于 DATA_MANIFEST 中的值。
- **已提交文件（14）**：HEAD 中协议、三个 JSON、metrix/CLAUDE.md、两个 agent 文件、gen_s_cands.py 的 sha256，与 t1_protocol_checks.txt、t1g_gen_s_cands.txt 中记录的值逐一相同；工作树中没有已跟踪文件的改动。

**一致。**

## 3. L1–L6（只做非 TEST 部分；TEST 部分按第 8 步执行）

**命令**：11、12 a1_facts.py、10 r7_cands_exposure.py、08

**原始输出**：
- **L1**：跨集合重复的模板哈希为 []。
- **L2**：词 4-gram Jaccard 最大为 0.2（capital.TRAIN.1 与 capital.DEV.1），上限 0.25。
- **L3a**（unread 的 entity/answer，在实际的 train_F/S/Y 与锚文本中）：`{'train_F': 0, 'train_S': 0, 'train_Y': 0, 'anchor': 0}`
- **L3b**：0。
- **L4（DEV 部分）**：区分大小写与不区分大小写都是 0。
- **L5**：fact_id 交集 0，320 个字符串重复 0。
- **L6（DEV 部分）**：按第 1b 项新口径计数（跨全部文档的种类数），共享词 13-gram 为 0；只报告的 Qwen id 13-gram 也是 0。

**一致**，与 Executor 和我第 6 轮的结果相同（第 6 轮 general DEV 的两个哈希 363aa087、2e30c443 也相同）。

## 4. 候选可行性（四重约束）

**命令**：10、11

**原始输出**：
- 16 个 (relation, stratum, exposure) cell 各只有一个 K_st 值；learned cell 各 15 个候选，unread cell 各 5 个。
- 最小值为 5；不足 4 个的 cell：[]。
- 实际的 candidates.json 共 160 组，违反四重约束的：[]。
- 暴露匹配（learned 在 F/S/Y 各恰好 1 次、锚文本 0 次；unread 全为 0 次）的偏差：0。
- S 句中 `' ' + answer` 的 id 都以连续片段出现：例外为 []。

**一致。**

## 5. split

**命令**：10、12

**原始输出**：
- 160 条 fact = learned 120 + unread 40；每个 cell 都是 (15, 5)。
- fact_id 格式与顺序符合规则；learned 与 unread 的交集为 0。
- TRAIN 120、S 120、Y 240、DEV 问句 320（learned 240、unread 80）。
- TEST 没有生成。

**一致。**

## 6. 第 1a–1f 项、第 2、3 项、裁决第 3、4 项是否与指令一致

**命令**：09 `r7_text_items.py /home/user/OpenMythos $SP/dl/qwen_tok 293b806…`；1e 的数据见 02 与 08。09 中带 [judged] 标记的判定全部为 OK，最后是 RESULT: PASS。

- **1a**：第 2.7 节已改为该句。
- **1b**：L6 一行写明了时机、计数口径、上限 0、由双方各自计算；第 8 步已改；manifest 新增 `test_part`。
- **1c**：第 8 步、ST10、第 9 节 BLOCKED 一行、执行接口、manifest 的 `test_part_over_limit` 都已写入。
- **1d**：G0.1 保留了“L1–L6 全部在上限内”，并把例外改为指令原文。
- **1e**：
  - 文字：n_w 句、2.7 节与 2.2 节的“每篇最多 128 token”、manifest 的 `window_rule` 与 `document_rule` 都在；协议第 14 节以外没有旧措辞。
  - 数据：锚文档 n_x 为 511 篇 128、1 篇 123（第 340 篇）；DEV 窗口 n_w 为 36 个 256、64 个更短，最短 172，没有超过 256 的。
  - 先解码再编码会改变的窗口数为 0、锚文档数为 0，所以“数值不变”的说法属实。
- **1f**：
  - id 151667、151668 在 tokenizer.json 的 added_tokens 与 tokenizer_config 中的 special 都是 False，也不在 all_special_ids 中。
  - `skip_special_tokens=True` 解码后两者仍然保留。
  - 151645、151643 是特殊 token。
  - 结果与 Executor 的 t1f_think_tokens.txt 相同。
- **第 14 节**：有 7 行 v1-r7，分别引用 1a–1g；时间与提交 2026-11-22 03:25:59 / `7fea9181` 和 git 记录一致；没有遗留占位符。
- **第 2 项**：
  - metrix/CLAUDE.md 第 10 节已补全出处。
  - code-reviewer.md 的新规则紧接在『未验证』规则之后，frontmatter 没有改动。
  - 这个范围内 metrix/ 以外只改了 `.claude/agents/code-reviewer.md`。
- **第 3 项**：DEFERRED_MINORS 1.7 节有 G1–G5，覆盖第 6 轮待决第 6 项的三点与第 14 项，并有指定的注。所引审查原文的行号我逐条核对过，都对得上。
- **裁决第 1、2 项**：fe321cd 的提交信息写有“证据文件，未经 code-reviewer”；t0_copy_check.txt 的 Part B 记录了 frontmatter 与 tools 行相同。
- **裁决第 3、4 项**：两份调用文字的第一句与 ROUND7_TASKS.md 中的固定句逐字节相同；第 5 节第 6 条有这句话、“tools 行不一致时必须停下”和出处。

**一致。**

## 7. BLOCKER

无。

## 8. 新提出的问题（全部为 MINOR，按指令登记，不修）

- **M1（1f）**：先删除再“取第一行”时：
  - `" <think>\n\n</think>\n\nKishan."` 归一化后为 `''`（09）。而 Qwen3 的标准格式正是 `<think>\n\n</think>\n\n`：chat template 在 enable_thinking=False 时的生成提示就以它结尾。
  - 没有闭合的 `<think>`（例如被 16 token 的上限截断）和单独出现的 `</think>`，协议没有规定怎么处理。
  - EM 只报告、不进门槛（协议第 546 行），所以只影响次指标。
- **M2（1d）**：
  - 照字面，G0.1 现在豁免的“涉及 TEST 的部分”也包括 L1、L2 中含 TEST 模板的那些对；但第 8 步只运行 L3–L5 和 L6 的 TEST 部分。
  - L1、L2 在撰写时已经算过（11 号：L1 为 0，L2 为 0.2），模板也由 template_set_sha256 冻结，所以对数据没有影响。
  - 措辞照搬指令原文，Executor 的写法与指令一致。
- **M3（1e）**：“不解码再编码”只写给了 n_w；第 4 节的 n_x（第 186 行）和 `anchor_text.document_rule` 没有写锚文档送入模型的是哪种 id。在现有数据上两者 512/512 相同（02），没有数值影响；指令对锚文档也只要求改为“最多 128 token”，所以 Executor 一致。
- **M4（1g）**：
  - 第 0 节没有固定 Python 版本（库版本一行只写了 torch 和 transformers），两个哈希依赖 CPython `random.Random` 的算法。实测 3.11、3.12、3.13 结果相同。
  - 另外，DATA_MANIFEST 的 `files.train_S.jsonl`、`files.candidates.json` 以及 SPLIT_MANIFEST 的 `split_sha256.train_S.jsonl` 仍为 null，期望值写在 `s_permutation` 和 `candidates` 两个字段里。同一个值有两个位置，以后填入时必须相同。
- **M5（流程观察，不属于数据，交 Review Gate）**：
  - metrix/CLAUDE.md 第 8 节规定“只有「永久」的裁决可写入本文件”，但第 7 轮指令第 2 项与裁决第 4 项都要求写入「本阶段」的出处。Executor 是照指令做的。
  - 第 10 节的 <UTC 时间> 填的是 7fea9181 的提交时间。第 6 轮报告待决第 7 项当时提议的是 481a6f0f 的时间（2026-11-21 14:41:02），指令没有说明该用哪一个。
  - DEFERRED_MINORS 中预告的 1.8 节尚未建立，预期在审查之后补上。

按 metrix/CLAUDE.md 第 10 节，data-auditor 仍为「待验证」，本 PASS 仅作参考。

## git status --short 原始输出（16_git_status.txt，2026-11-22 03:49:09 UTC，HEAD 293b806dcfabe0cd1f786a5b9391dea8d7090f6f）

```
?? metrix/e1-pilot/audit/r7_cands_exposure.py
?? metrix/e1-pilot/audit/r7_compare.py
?? metrix/e1-pilot/audit/r7_general_dev.py
?? metrix/e1-pilot/audit/r7_s_cands.py
?? metrix/e1-pilot/audit/r7_text_items.py
?? metrix/e1-pilot/audit/stdout/293b806dcfabe0cd1f786a5b9391dea8d7090f6f/
?? metrix/e1-pilot/reviews/293b806dcfabe0cd1f786a5b9391dea8d7090f6f/
```

`reviews/293b806…/` 是 Executor 在调用我之前写的，不是我创建的。我只在 audit/ 下写入；`git diff HEAD --stat` 为空。

结论：PASS
