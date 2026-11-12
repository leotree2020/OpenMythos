# E1-PILOT 第 3 轮报告

- 指令:`tasks/ROUND3_TASKS.md`(Review Gate 第 3 轮,Owner 2026-11-12 15:26 UTC 下达)
- 执行会话:session_01J5mxaTvdtnGXVnVJiiAhgU
- 运行环境:Claude Code on the web 云容器(anthropic_cloud),hostname `vm`,4 CPU,15 GiB 内存,无 GPU(`nvidia-smi: command not found`),Ubuntu 24.04.5,Python 3.13.18
- 依赖:venv 中装 transformers 5.22.2、tokenizers 0.23.3、jinja2,不装 torch。只下载了 Qwen/Qwen3-1.7B@70d244cc 的分词器与配置文件,没有下载模型权重。
- 没有训练,没有评测,没有生成或读取 TEST 数据,也没有实例化任何 TEST 模板。
- 工作提交:`596fcfad4b73fdddad607ab6bc28d4c128f3744b`(任务 3–8 与任务 2 的证据)。本报告、审查原文与 audit 脚本在其后的报告提交中,哈希见提交说明与 PR。
- 原始输出都在 `reports/round3/`。路径里的 `<TOK>` 是分词器目录,`<SCRATCH>` 是会话 scratchpad。

## 结论一览

| 任务 | 状态 | 证据 |
|---|---|---|
| 2 subagent 与规则加载 | **PASS** | `round3/t2_load_check_redo2.txt` |
| 3 metrix/ 以外改动检查 | 完成;HEAD 上 **PASS**;3 个负例均 FAIL(符合预期) | `round3/t3_outside_metrix.txt`、`round3/outside_metrix_check.py` |
| 4 BOS/EOS 规则影响核查 | 完成,见下表:无一处受影响;2 处待 Review Gate 决定 | `round3/t4_special_tokens_grep.txt`、`round3/t7_verify_scoring.txt` 的 `== task 4` 段 |
| 5 补记锚文本规则 | 完成 | 协议第 14 节 “v1-r2(Round 3 补记)” 一行 |
| 6 打分改为 `The answer is` 前缀 | 完成 | 协议第 0、2.2、5 节;`DATA_MANIFEST.json`;`round3/scoring_input.py` |
| 7 答案 token id 一致性 | **不一致数 0**(240 对) | `round3/t7_verify_scoring.txt` |
| 8 候选可行性 | 最小池 **5**,不足 4 的 cell **0** | `round3/t8_candidate_feasibility.txt` |
| 9 两个审查 | code-reviewer **PASS**;data-auditor **PASS** | `reviews/596fcfad…/` |
| 11 报告与推送 | 本文件 | — |

两个 subagent 的信任状态仍为「待验证」(metrix/CLAUDE.md 第 10 节):检出率测试还没做,所以它们的 PASS 只作参考。

## 任务 2

本会话启动时,用户级目录 `/root/.claude/agents/` 里已经有两个 agent 定义,agent 列表里也有 `code-reviewer` 与 `data-auditor`。两者都实际调用过,都有回应。它们的定义与仓库 `.claude/agents/` 下的文件逐字节相同(git blob 分别为 `204f97c4…`、`0081a866…`)。`/root/.claude/CLAUDE.md` 与 `metrix/CLAUDE.md` 逐字节相同(`a9fd24c5…`),会话一开始就在上下文里。根目录宪章启动时没有注入,checkout 之后用 Read 读了全文,所以第 5 节在上下文里。执行顺序:环境检查、agent 目录列举与两个 agent 的调用测试在任何 git 操作之前;与仓库文件的逐字节比对在只读 fetch 与 checkout 之后(`t2_load_check_redo2.txt` 第 D 段)。

## 任务 3

`reports/round3/outside_metrix_check.py` 把当前提交与 base `61d3c767` 比较,只放行三处 metrix/ 以外的改动:

1. `CLAUDE.md`:base 文件必须是新文件逐字节的前缀,追加部分只能有一个标题,即 `## 6. Metrix` 开头的第 6 节。
2. `.claude/agents/code-reviewer.md`(新增)。
3. `.claude/agents/data-auditor.md`(新增)。

两个 agent 文件被 `.gitignore:14:.claude/` 忽略,靠 `git add -f` 强制跟踪,以后改动也必须用 `-f`。这一点写进了协议第 0 节与 `SUBMISSION_NOTE.md` 第 1、5 节。第 14 节已记录。

```
$ python3 reports/round3/outside_metrix_check.py
changed outside metrix/ (base 61d3c767 .. HEAD):
  A	.claude/agents/code-reviewer.md
  A	.claude/agents/data-auditor.md
  M	CLAUDE.md
charter: base 3065 bytes, new 3586 bytes, base is exact prefix: True
charter: appended 521 bytes; headings in appended part: ['## 6. Metrix 子项目(2026-11-13 负责人决定)']
...
RESULT: PASS
```

负例都没有挂到任何分支上:临时 index 加 `git commit-tree` 造出悬空提交。

| 负例 | 结果 |
|---|---|
| 改宪章第 5 节 | `FAIL: charter: original content differs from base` |
| 追加 `## 7.` | `FAIL: ... exactly one heading, section 6` |
| 改 README | `FAIL: not allowed: M README.md` |

## 任务 4:特殊 token 逐处核查

查的是第 2 轮结束时的状态(`6675af63`;之后的 `8ce8c896` 只加了宪章第 6 节、metrix/CLAUDE.md 和 agent 文件)。grep 原文在 `t4_special_tokens_grep.txt`。分词器实测结果在 `t7_verify_scoring.txt` 的 `== task 4` 段:

- `bos_token None`,`eos_token '<|im_end|>' 151645`,`pad_token '<|endoftext|>' 151643`。
- `add_special_tokens=True` 与 `False` 编码结果相同。
- `enable_thinking=False` 时,生成提示末尾带 `<think>\n\n</think>\n\n`。

| # | 位置 | 涉及的特殊 token | 结论 |
|---|---|---|---|
| 1 | 协议第 0 节 “训练输入”;`DATA_MANIFEST.json` `input_convention.training` | 陈述句后接 `<|endoftext|>`(151643),前面不加任何 token | **未受影响**。宪章 3.7 要求不加 BOS/EOS,这里加了 EOS 类 token,与宪章相反。Qwen 没有 BOS(`bos_token None`),所以前面不加是该模型的默认做法,不是照搬宪章。 |
| 2 | 第 0 节 “问答输入”;`input_convention.qa` | chat template:`<|im_start|>`、`<|im_end|>`、`<think></think>` | **未受影响**。照宪章 3.7 的话不会用模板。 |
| 3 | 第 2.2 节 token 数;`name_generation.token_counts.encode`;`round1/candidate_feasibility.py:50`、`round2/names.py:50`、`round2/anchor_check.py:63` | `add_special_tokens=False` | **未受影响**。`bos_token` 为 None,实测句子上两种设置编码相同(只测了一句);只用于数 token 和截断锚文本。 |
| 4 | 第 5 节 `s_ST`(TRAIN 闭卷) | 前缀是陈述句开头的文本,前面不加任何 token | **未受影响**。与训练输入(#1)的开头一致;只对答案 token 打分。 |
| 5 | 第 5 节 EM | 生成遇到 `<|im_end|>`(151645)停止 | **未受影响**。 |
| 6 | 第 5 节 general damage:`NLL_arm(w)` 对 `t=2..n_w` 求和,窗口前不加 token | 无特殊 token | **形式与宪章 3.7 相同(“窗口从文档开头取、不加 BOS”),是否来自该规则无法从记录确认。** 对 Qwen 来说这不是错误:模型没有 BOS,第一个 token 不计分;dNLL 是相对 N 的差,这个约定对两边相同。另一种做法是前置 `<|endoftext|>` 再对 `t=1` 也计分,**由 Review Gate 决定是否改**;本轮不改。 |
| 7 | 第 4 节 arm A:`mean_t KL(p_base(·|x_<t) ‖ p_θ(·|x_<t))`,锚文档前不加 token | 无特殊 token | 与 #6 相同。另外,`t` 的范围没有写明:不加前置 token 时 `t=1` 的条件为空,应从 `t=2` 起,或者前置 `<|endoftext|>`。**协议没有覆盖,交 Review Gate**。 |
| 8 | 第 2.7 节 通用文本 `decode_with ... special tokens skipped` | parcae 分词器解码时跳过特殊 token | **未受影响**。这一步是从源数据取出纯文本,与打分输入无关。 |
| 9 | `round1/candidate_feasibility.py:170`、`round2/y_ratio.py` | 用 chat template;F/Y 计数加 endoftext | **未受影响**。与 #1、#2 一致。 |

结论:前两轮的代码与协议里,没有一处因为宪章“不加 BOS/EOS”而加了或删了特殊 token。#6、#7 两处“开头不加 token”的形式与宪章一致,但对 Qwen 也成立。是否改为前置 `<|endoftext|>`,以及 KL 求和的 `t` 范围,交 Review Gate 决定。

## 任务 5

第 14 节新增一行 “v1-r2(Round 3 补记)”:

- 时间:2026-11-12 14:43:19 UTC。
- 提交:`6675af63`。
- 位置:第 2.2 节、`DATA_MANIFEST.json: name_generation.anchor_rule`。
- 改动:生成名字时,拒绝在锚文本中出现过的字符串。
- 原因:Round 2 第 5 项把 arm A 纳入暴露匹配(L3b)。名字如果出现在锚文本里,A 对该候选的暴露会多于 F,unread 名字也会违反 L3a。在生成时拒绝,两项检查在构造上就成立。`DATA_SEED` 下这条规则没有拒绝任何名字,哈希不变(出处:`ROUND2_REPORT.md` 对照运行 3)。时间与提交见 `round3/t11_commit_times.txt`。

## 任务 6

- **打分序列**:`chat(q) + "The answer is" + " " + c`。
  - `chat(q)`:单个 user 回合,`add_generation_prompt=True`,`enable_thinking=False`(写成常量,不作参数)。
  - 只对 `" " + c` 打分,候选之后什么都不接。
  - `K = K_st`。
- **参考实现**:`reports/round3/scoring_input.py`。它会检查上下文的 token 是否是整串 token 的前缀,防止候选与前缀在边界处合并。
- **协议改动**:第 0 节新增 “候选打分输入” 一行;第 5 节 `s_QA` 已改;第 2.2 节注明 `K_qa` 只作为生成规则保留,因为改动它会改变 fact 及其哈希。`DATA_MANIFEST.json` 同步。第 14 节已记录。
- **fact 哈希不受影响**:改动后重跑 `gen_facts.py`,仍为 `406c8801…`,与改动前逐字节相同(`t0_facts_regen.txt`)。
- **没有改 EM**:任务 6 只涉及候选打分。EM 仍从裸 `chat(q)` 解码,见“待 Review Gate”第 1 项。

## 任务 7

做法:对 120 个 learned fact 的每个 DEV 问句(共 240 对),比较两组 token id:

- 打分序列中被打分的 token id;
- TRAIN 陈述句里 `" " + 答案` 片段的 token id,按字符 offset 定位。

```
learned facts: 120; (fact, DEV question) pairs compared: 240
TRAIN statements where ' ' + answer is not token-aligned: 0
mismatches (scored ids != TRAIN answer ids): 0
renderer vs apply_chat_template(continue_final_message=True) text differences: 0
scored-token counts per cell: {'capital/natural': [3], 'capital/random': [5], 'currency/natural': [3], 'currency/random': [6], 'founder/natural': [3], 'founder/random': [5], 'river/natural': [3], 'river/random': [6]}
cells with more than one scored-token count: 0
RESULT: PASS
```

**不一致数为 0。** 下面是一条完整的打分序列(E1P-L-capital-nat-01,DEV 问句 1):

```
rendered text (json-escaped): "<|im_start|>user\nWhat is the capital of Krultrouth?<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\nThe answer is Linnuth"
input_ids (28): [151644, 872, 198, 3838, 374, 279, 6722, 315, 16447, 360, 376, 2898, 30, 151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271, 785, 4226, 374, 444, 6130, 940]
tokens: ['<|im_start|>', 'user', '\n', 'What', ' is', ' the', ' capital', ' of', ' Kr', 'ul', 'tr', 'outh', '?', '<|im_end|>', '\n', '<|im_start|>', 'assistant', '\n', '<think>', '\n\n', '</think>', '\n\n', 'The', ' answer', ' is', ' L', 'inn', 'uth']
scored slice start 25, scored ids [444, 6130, 940], scored tokens [' L', 'inn', 'uth']
TRAIN statement: "The capital of Krultrouth is Linnuth."  answer ids [444, 6130, 940]
```

## 任务 8

“新的切分”按任务 6 的打分切分理解:即 `The answer is` 之后 `" " + c` 的 token 数。

```
facts 160; facts whose scored-token count depends on the DEV question: 0
facts whose scored-token count differs from K_st: 0
pools under the four constraints (relation, stratum, exposure, scored-token count): 16
  [... 16 行池明细见 t8_candidate_feasibility.txt ...]
(relation, stratum, exposure) groups split over more than one token count: 0 []
minimum pool size: 5
pools with fewer than 4 answers: 0 []
RESULT: PASS
```

摘要(非原始输出):每个 relation × stratum 中 learned 15 个、unread 5 个;K 为 natural 3,capital/founder random 5,currency/river random 6。

**最小池大小 5**(unread 各 cell,4 个可选干扰项,需要 3 个)。**不足 4 的 cell:0。**

## 任务 9:审查(原文见 `reviews/596fcfad4b73fdddad607ab6bc28d4c128f3744b/`)

- `code-reviewer.md`:**PASS**。2 条 MAJOR、6 条 MINOR,不含 BLOCKER。
  - MAJOR 1:EM 的输入与新打分不一致。
  - MAJOR 2:第 14 节的提交与时间字段不统一。原有 v1-r2 行写的“本节所在提交”现在有歧义;v1-r3 行只写了日期。
- `data-auditor.md`:**PASS**。auditor 用 `metrix/e1-pilot/audit/` 下自己写的脚本,独立重算了 fact 哈希(另外按协议文本重新生成,逐字节相同)、锚文本哈希、打分构造与 240 对 id 比对、候选可行性(最小池 5)、模板哈希、L1/L2/L3a/L3b/L4(DEV)/L5 与 split 计数,结果都一致。L6 需要 general_dev 与 parcae 分词器,不在本轮范围。
- 审查意见没有在本轮修复。两份结论都是 PASS;修复会产生新提交、需要重新审查,而且 MAJOR 1 是协议没有覆盖的设计问题。都列在下面,交 Review Gate。

## 待 Review Gate 决定

1. **EM 的输入**(两份审查都提出):EM 应改为从 `chat(q) + "The answer is"` 解码(并去掉开头空格),还是写明保留裸 `chat(q)`?
2. **general damage 与 arm A 的 KL 是否前置 `<|endoftext|>`**;KL 的 `t` 从几开始(任务 4 #6、#7)。
3. **第 14 节提交引用**:原有 v1-r2 行写的“本节所在提交”是否改成 `6675af63`?v1-r3 行补上 UTC 时间与本次的 `596fcfad`?(code-reviewer MAJOR 2)
4. 宪章第 6 节标题写的是 “2026-11-13 负责人决定”,但它的提交 `8ce8c896` 时间是 2026-11-12 15:25:19 UTC(`round3/t11_commit_times.txt`)。改宪章需要 Owner 决定,本轮未动。
5. 其余项(注明出处):
   - code-reviewer MINOR:`outside_metrix_check.py` 的标题判定过严;忽略规则读的是工作区 `.gitignore`;`verify_scoring.py` 里重复写了 `enable_thinking`,并用了 `assert`;第 2.2 节答案等长规则的“作用”文字已过时;宪章第 6 节日期(即第 4 项)。
   - data-auditor Observation 1:第 5 节 `s_ST` 的 `K'` 没有定义(按构造等于 `K_st`)。
   - data-auditor Observation 3:`reviews/` 与 `audit/` 当时未被跟踪;报告提交已把两者纳入跟踪(`audit/__pycache__/` 被 .gitignore 忽略)。
   - 报告提交的 code-reviewer(`reviews/596fcfad…/code-reviewer_report-commit.md`)PASS,1 MAJOR 6 MINOR;其 MAJOR(“对 main 运行”无原始输出)已从报告中删去,MINOR 中的措辞与出处问题已在报告中改正。
6. 审查文件的“原文”:Executor 只去掉了 harness 加的行首缩进,并在开头加了说明行,正文未改。data-auditor 正文中的 “Raw output” 是 auditor 自己摘录的,audit 脚本的完整 stdout 没有提交;Review Gate 若要求可补交。
