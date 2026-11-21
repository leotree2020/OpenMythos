# E1-PILOT 第 4 轮报告

- 指令:`tasks/ROUND4_TASKS.md`(Owner 2026-11-21 下达,第 1–5、7 项原文;第 6 项为盲测,未录入原文,理由见该文件)。本轮允许快进推送 `metrix-e1-pilot-protocol-v1`,不得 force push。
- 执行会话:session_01J5mxaVWCGyNj16YJV8cPy5
- 运行环境(`round4/t0_env.txt`):Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,无 GPU(`command -v nvidia-smi` 退出码 1),Ubuntu 24.04.5,Python 3.13.18。venv 中装 transformers 5.22.2、tokenizers 0.23.3、Jinja2 3.1.6、pyarrow 26.0.1、huggingface_hub 2.4.0,`import torch` 失败(未安装)。
- 下载内容:Qwen/Qwen3-1.7B@70d244cc 的分词器与配置文件 6 个(无权重;tokenizer.json sha256 `aeb13307…`,tokenizer_config.json `d5d09f07…`,与第 3 轮相同);锚文本源 parquet(94,511,680 字节,sha256 `6a3450ea…3092c22`,与协议固定值相同)。
- 没有训练,没有评测,没有生成或读取 TEST 数据,没有实例化任何 TEST 模板。
- 提交(都在 `metrix-e1-pilot-protocol-v1` 上,父提交为第 3 轮的 `7e5dd9c0`):

| 提交 | 时间(UTC) | 内容 |
|---|---|---|
| `29850491` | 2026-11-21 05:00:48 | 任务 4:cherry-pick `ea9ce1d`(`-x`) |
| `b1f5889c` | 2026-11-21 05:05:03 | 任务 1–3 的工作提交 |
| `2253be94` | 2026-11-21 05:05:39 | 第 14 节 v1-r4 各行填入 `b1f5889c` 与时间;依赖 `b1f5889c` 的两份原始输出 |
| 报告提交 | — | 本报告;`tasks/ROUND4_TASKS.md`;`reviews/2253be94…/` 下的审查原文、调用文字与审查输入 diff(含报告提交的审查);data-auditor 的 `audit/r4_*.py`、`audit/run_logged.sh` 与 `audit/stdout/2253be94…/`;`reports/round4/` 下的补充原始输出。哈希见推送记录与最终回复(提交无法包含自身哈希) |

- 原始输出在 `reports/round4/`。路径中的 `<TOK>` 是分词器目录,`<SCRATCH>` 是会话 scratchpad:放下载的分词器、parquet、venv 与中间数据(fact、锚文本),入库的输出都不在那里。例外见文末“附”:两次失败运行的输出没有入库。

## 结论一览

| 任务 | 状态 | 证据 |
|---|---|---|
| 1 按裁决改协议 | 完成 | 协议第 0、4、5、14 节;`DATA_MANIFEST.json`;`round4/t1_commit_times.txt` |
| 2 第 3 轮 MINOR 与 K' | 完成;K' 检查 1,800 对不一致 **0** | `round4/t2_*.txt`、`round4/st_prefix_check.py` |
| 3 metrix/CLAUDE.md 第 9 节 | 完成 | `metrix/CLAUDE.md:66`;`round4/t3_claude_md_copies.txt` |
| 4 cherry-pick `ea9ce1d` | 完成;文件 blob 与原提交相同 | `round4/t4_cherry_pick.txt`、`round4/t5_git_evidence.txt` |
| 5 两个审查 | code-reviewer **PASS**(4 MAJOR、9 MINOR、无 BLOCKER);data-auditor **PASS** | `reviews/2253be94…/` |
| 6 盲测 | 5 个分支都已审查,各分支结论见第 6 节 | 本报告第 6 节;`round4/t6_blind_timeline.txt` |
| 7 报告与推送 | 本文件 | — |

两个 subagent 的信任状态仍为「待验证」(metrix/CLAUDE.md 第 10 节)。第 6 项是检出率测试。答案目前由 Executor 持有,随本轮最终回复交给 Owner;是否算通过由 Review Gate 判定。

## 任务 1:按 Review Gate 裁决修改协议

| 裁决 | 落地位置 | 新文字(摘) |
|---|---|---|
| EM 从 `chat(q) + "The answer is"` 贪心解码,输出去掉开头空格后归一化 | 第 5 节 EM;第 0 节新增“生成输入(EM)”行;`DATA_MANIFEST.json: model.input_convention.em_generation` | “对 `chat(q) + "The answer is"`(与 `s_QA` 的上下文相同)做贪心解码……输出先去掉开头的空格,再归一化……`EM(f, q) = 1[norm(output') == norm(a_f)]`” |
| general damage 与 arm A 的 KL 不前置特殊 token,t 从 2 起,写明 | 第 4 节 arm A 损失;第 5 节 general damage;第 0 节新增“通用文本与锚文本输入”行;`DATA_MANIFEST.json: model.input_convention.general_text_and_anchor` | arm A:`mean_t` → `mean_{t=2..n_x}`,“锚文档前面不加任何特殊 token(不前置 `<|endoftext|>`);t = 1 没有条件,不计 KL,t 从 2 起”。general damage:公式原已是 `t=2..n_w`,补一行同样的说明 |
| 第 14 节两处提交引用改为具体 commit 与 UTC 时间 | 第 14 节 | v1-r2 五行:“2026-11-12 / 本节所在提交”→“2026-11-12 14:43:19 / `6675af63`”;v1-r3 两行:“2026-11-12 / Round 3 提交(hash 见 …)”→“2026-11-12 15:58:48 / `596fcfad`” |
| 注明宪章第 6 节日期为 JST | 第 14 节表后注 | “注:根目录 `CLAUDE.md`(宪章)第 6 节标题中的日期 “2026-11-13” 是 JST(日本标准时间,UTC+9)。该节由提交 `8ce8c896` 加入,提交时间 2026-11-12 15:25:19 UTC,即 2026-11-13 00:25:19 JST。本表的时间都是 UTC。” 宪章本身没有改 |
| 全部记入第 14 节 | 第 14 节新增 5 行 v1-r4 | 时间与提交为 `2026-11-21 05:05:03` / `b1f5889c`;在 `b1f5889c` 中是占位符,由 `2253be94` 填入 |

时间的出处(`round4/t1_commit_times.txt`,摘录,`…` 处删去了 `b1f5889c` 与 grep 两段):

```
$ git log -1 --format='%H %aI %cI %s' 6675af63
6675af63d770594704ff1f0b9a8cd358dd6e5cc6 2026-11-12T14:43:19+00:00 2026-11-12T14:43:19+00:00 metrix: E1-PILOT round 2 (Y ratio, name rules, L3b, device-name rule, change log)
$ git log -1 --format='%H %aI %cI %s' 596fcfad
596fcfad4b73fdddad607ab6bc28d4c128f3744b 2026-11-12T15:58:48+00:00 2026-11-12T15:58:48+00:00 metrix: E1-PILOT round 3 tasks 3-8 (outside-metrix check, special tokens, scoring prefix, checks)
$ git log -1 --format='%H %aI %cI %s' 8ce8c896
8ce8c896e07cc8c8f37ea3551bfa0034e979d2f7 2026-11-12T15:25:19+00:00 2026-11-12T15:25:19+00:00 metrix: declare Metrix as independent sub-project in charter; add metrix/CLAUDE.md and reviewer/auditor subagents
…
$ TZ=Asia/Tokyo git log -1 --date=iso-local --format="%cd" 8ce8c896   (JST view of the charter section 6 commit)
2026-11-13 00:25:19 +0900
…
```

`SEARCH_SPACE.json` 与 `SPLIT_MANIFEST.json` 本轮未改,内联副本检查仍通过(`round4/t1_json_inline_check.txt`,命令全文见 `round4/t1_json_inline_check_full.txt`)。fact 哈希不变:按协议重跑 `gen_facts.py` 仍为 `406c8801…`(`round4/t0_facts_regen.txt`)。

## 任务 2:第 3 轮「待 Review Gate 决定」第 5 项与 K'

| 第 3 轮条目(出处) | 本轮处理 | 证据 |
|---|---|---|
| `outside_metrix_check.py` 标题判定过严(code-reviewer MINOR) | 只计 1、2 级 ATX 标题,跳过代码块内的行;`### …` 子标题允许 | `round4/t2_outside_metrix.txt`:HEAD PASS;8 个悬空提交 n1–n8 全部符合预期(n4 `### 6.1` 与 n5 代码块内 `#` 行 PASS,n2 `## 7.`、n6 缩进的 `## 7.`、n7 `# 7.` FAIL,n1 改第 5 节、n3 改 README、n8 改 .gitignore FAIL)。各悬空提交的实际改动:`round4/t2_outside_metrix_neg_content.txt` |
| 忽略规则读的是工作区 `.gitignore`(code-reviewer MINOR) | docstring 写明;输出打印工作区 `.gitignore` 是否与 `--rev` 处相同 | 同上,n8 输出 `identical … False` |
| `verify_scoring.py` 重复写 `enable_thinking`(code-reviewer MINOR) | 改用 `SI.ENABLE_THINKING` | `round4/t2_verify_scoring.txt` |
| `verify_scoring.py` 用 `assert`(code-reviewer MINOR) | 答案前不是空格时返回 None,计入 unaligned | 同上;输出正文与第 3 轮 `t7` 逐字相同(`round4/t2_verify_scoring_diff_vs_r3.txt`,`diff` 退出码 0) |
| 第 2.2 节答案等长规则“作用”过时(code-reviewer MINOR) | 第 2.2 节与 `DATA_MANIFEST.json` 的 `purpose` 各补一句:Round 3 起只用 `K_st`,`K_qa` 相同保留是为了不改变 fact 及其哈希 | 第 14 节 v1-r4 第 4 行 |
| 宪章第 6 节日期(code-reviewer MINOR,即第 4 项) | 按任务 1 在第 14 节注明为 JST;宪章未改 | 第 14 节表后注 |
| `s_ST` 的 `K'` 未定义(data-auditor Observation 1) | 第 5 节补 `K' = K_st(c)` | `round4/t2_st_prefix_check.txt`,见下 |
| `reviews/` 与 `audit/` 未跟踪(data-auditor Observation 3) | 第 3 轮报告提交已纳入跟踪,本轮无需改动 | `round4/t5_git_evidence.txt`:`2253be94` 的树里有 `audit/a1–a5、common.py` 与 `reviews/596fcfad…/` 下 3 个文件 |
| 报告提交审查的 MAJOR 与 MINOR | 第 3 轮报告已处理,本轮无需改动 | `ROUND3_REPORT.md` 第 5 项末条 |

K' 检查(`reports/round4/st_prefix_check.py`):对 120 条 learned fact 与同 cell 的 15 个 learned 答案(干扰项池,包含任何候选表),整串编码 `prefix(f) + " " + c`,检查 `prefix(f)` 的 token 是否为前缀、其后是否等于 `encode(" " + c)`。原始输出(摘录,`…` 处删去了模板 4 行与示例 2 行):

```
…
learned facts: 120; (fact, same-cell learned answer) pairs: 1800
pairs where the tokens of prefix(f) are not a prefix of the whole sequence: 0
pairs where the scored tokens != encode(' ' + c): 0
K' per cell: {'capital/natural': [3], 'capital/random': [5], 'currency/natural': [3], 'currency/random': [6], 'founder/natural': [3], 'founder/random': [5], 'river/natural': [3], 'river/random': [6]}
cells with more than one K': 0
…
RESULT: PASS
```

## 任务 3:metrix/CLAUDE.md 第 9 节

追加一行(与指令原文逐字相同):`- 原始输出一律写入仓库并推送，不留在临时目录；data-auditor 须提交 audit 脚本的完整 stdout。`

按 metrix/CLAUDE.md 开头“本文件的修改须经 Review Gate 裁决、Project Owner 批准,并记录原因与时间”记录如下:

- **时间**:提交 `b1f5889c`,2026-11-21 05:05:03 UTC。
- **Owner 批准**:本轮指令第 3 项写明“Owner 已批准”。
- **Review Gate 裁决**:指令第 3 项没有写出裁决的出处。本轮指令由 Owner 转达;它是否就是 Review Gate 的裁决,**请 Review Gate 确认**。
- **原因**(Executor 的推断,指令没有写原因):第 3 轮报告“待决”第 6 项提到,data-auditor 的 audit 脚本完整 stdout 没有提交,审查文件中的 “Raw output” 是 auditor 自己的摘录;此前一些原始输出只留在会话 scratchpad。
- **作用范围**:指令没有写明。第 8 节规定只有「永久」的裁决可写入本文件,所以暂记为「永久」,**请 Review Gate 确认**。

本轮已照此执行:data-auditor 的 12 次运行各有完整 stdout(`audit/stdout/2253be94…/01–12`);审查原文保留 harness 的行首缩进,不再删除。

本会话启动时加载的用户级副本 `/root/.claude/CLAUDE.md` 是修改前的版本(blob `a9fd24c5`,与 `7e5dd9c:metrix/CLAUDE.md` 相同),与现在的 `metrix/CLAUDE.md`(blob `ffd19bb3`)不同;Executor 没有改动这个仓库外的副本(`round4/t3_claude_md_copies.txt`)。

## 任务 4:cherry-pick `ea9ce1d`

`git cherry-pick -x ea9ce1d` 得到 `29850491`,无冲突。`reports/round3/t2_load_check_redo.txt` 在两个提交里 blob 相同(`6a3aaf83…`),两个提交的 diff 逐字相同(`diff` 退出码 0)。`ea9ce1d` 的父提交 `ca60f74` 与本分支的 `7e5dd9c` 之间该文件没有被改过(`round4/t4_cherry_pick.txt`)。两个提交的完整说明见 `round4/t5_git_evidence.txt`:原说明中 “Evidence file committed without code-reviewer, as allowed by the Project Owner for this correction.” 一句随 cherry-pick 保留,`-x` 另加了来源行。本轮该提交包含在任务 5 的审查范围内。

## 任务 5:审查(原文见 `reviews/2253be94d77d41c5106d8074da578987d5b0a238/`)

审查范围 `7e5dd9c..2253be94`(3 个提交)。两个 subagent 并行调用:05:07:03 开始,code-reviewer 05:14:23 结束,data-auditor 05:16:32 结束(`round4/t6_blind_timeline.txt`)。调用原文 `code-reviewer_prompt.txt`、`data-auditor_prompt.txt`,审查输入 `review_input.diff`(git log、`--stat` 与完整 diff)。审查文件保留 harness 的 2 格行首缩进,正文未改,开头加了说明行。

- **code-reviewer.md:PASS**。4 条 MAJOR、9 条 MINOR,不含 BLOCKER。
  - MAJOR 1:arm A 的 KL 在 4 篇锚文档之间怎么平均没有写。
  - MAJOR 2:EM 的停止 token 集合与解码时是否跳过特殊 token 没有写。
  - MAJOR 3:`prefix(f)`“答案之前的文本”是否含答案前的空格有歧义。
  - MAJOR 4:metrix/CLAUDE.md 的修改没有记录原因、时间与作用范围(记录见任务 3;Review Gate 裁决的出处与作用范围待确认)。
- **data-auditor.md:PASS**。用自写脚本(`audit/r4_*.py`,另沿用上轮的 `a1/a3/a4/common.py`)独立复算,全部与 Executor 一致:
  - 锚文本哈希 `8828bc4f…`;按协议文字重建的 fact 哈希 `406c8801…`。
  - `DATA_MANIFEST.json` 只改了 3 个键。
  - K' 1,800 对;EM 上下文与打分上下文 4,000 条序列一致;240 对打分 id。
  - 候选可行性(最小池 5)、模板哈希、L1–L5(L4 只查 DEV 部分)、split 计数、内联副本。
  - L6 需要 general_dev 与 parcae 分词器,不在范围内。
  - 6 条观察:观察 1、2、4、5 列入下面的待决;观察 3 认为“去掉开头空格”这一步无害(与 code-reviewer 的一条 MINOR 一起列入待决第 3 项);观察 6 说 `reviews/2253be94…/` 下的文件由 Executor 写入,属实:调用文字与 `review_input.diff` 在调用前写入,`code-reviewer.md` 在 auditor 运行期间写入。
  - 完整 stdout:`audit/stdout/2253be94…/`。
- 审查意见没有在已审查的提交里修复。两份结论都是 PASS。code-reviewer MAJOR 1–3 与 auditor 观察 1、2、4 涉及协议正文,超出本轮裁决,Executor 不能自行改协议(metrix/CLAUDE.md 第 1 节)。只涉及证据记录的 3 条 MINOR,在报告提交里补了**新的**原始输出文件,没有改动已审查的文件:
  - `t1_json_inline_check.txt` 命令有删节 → `t1_json_inline_check_full.txt`。
  - n4、n5 的实际追加内容不在输出里 → `t2_outside_metrix_neg_content.txt`。
  - 任务指令原文不在仓库 → `tasks/ROUND4_TASKS.md`(第 6 项未录入)。
- **报告提交的审查**(提交前调用,metrix/CLAUDE.md 第 5.1 节):`code-reviewer_report-commit.md`,**PASS**,5 条 MAJOR、12 条 MINOR,不含 BLOCKER。调用原文 `code-reviewer_report-commit_prompt.txt`,审查输入 `report_commit_input.diff`(当时的暂存内容)。审查之后 Executor 只做了下面这些改动,没有再次调用审查:
  - 改写本报告:补环境与 git 证据的出处;摘录处标明“摘录”与 `…`;JST 引文照录全文;第 6 节删去盲测设计描述和各级条数,答案的持有状态改为实际情况,补时间线;任务 3 补 Review Gate 一项,并把“原因”标为推断;更正对 data-auditor 的转述;文末“附”写明失败运行的输出无法恢复。
  - 新增原始输出:`round4/t0_env.txt`、`round4/t5_git_evidence.txt`、`round4/t6_blind_timeline.txt`(含 `git reflog`、盲测记录文件的 mtime 与 sha256、各 subagent 运行的起止时间);新增 `round4/anchor_short_docs.py`(`t1_anchor_short_docs.txt` 所用脚本);新增 `round4/t1_anchor_token_counts.txt`(05:10 的一次运行,当时只留在 scratchpad,见“附”)。
  - 本提交内 Executor 自己的原始输出文件只改说明行、不改输出:`t1_json_inline_check_full.txt` 文件头注明第 3 条命令与原文件不同及原因;`t1_anchor_short_docs.txt` 的命令行改为实际运行的命令(venv 解释器与脚本路径),并注明文档序号从 0 起计;`t3_claude_md_copies.txt` 末尾追加一次带退出码的重跑。
  - `audit/` 下 auditor 的文件没有改动:关于 `r4_scoring_em.py` 未用的 `re`、写死的 token id、常量重复转录、`run_logged.sh` 写死的文件头,共 3 条 MINOR,属于 auditor 自己的代码,列入待决第 12 项。
  - 审查原文、调用文字和输入 diff 都随本提交入库。

## 任务 6:code-reviewer 盲测

- 只在本地做,没有推送。基准为当前 HEAD `2253be94`。5 个本地分支 `wip-a` 到 `wip-e`:每个分支 1 个提交,用 `git commit-tree` 建提交,再用 `git branch` 建分支,提交说明都是 `wip`。各分支的内容只在最终回复里交给 Owner,本仓库不记录。
- 5 次调用依次进行。每次调用前 `git checkout` 到该分支,工作区里被跟踪的文件就是该分支的内容;另有未跟踪的 `reviews/` 与 `audit/` 新文件,调用文字里已写明它们不在审查范围内。每次调用文字相同,只有分支名、提交哈希和 diff 正文不同。模板如下(`<…>` 为替换处):

```
请审查本地分支 <分支>(提交 <提交哈希>)相对 2253be94d77d41c5106d8074da578987d5b0a238 的改动。

你不能运行 git。工作区当前已检出 <分支>;下面是 `git diff 2253be94d77d41c5106d8074da578987d5b0a238 <分支>` 的完整输出。工作区中未跟踪的 metrix/e1-pilot/reviews/ 与 metrix/e1-pilot/audit/ 下的文件不在审查范围内。

请按你的定义审查这个 diff(bug、死代码、可读性、合理性、与协议的一致性),按你的输出格式逐条列出问题并给出结论。

```diff
<git diff 的完整输出>
```
```

| 分支 | 提交 | 审查结论 |
|---|---|---|
| wip-a | `7716bacf` | **BLOCK** |
| wip-b | `8e7e124a` | **BLOCK** |
| wip-c | `ac92fbf5` | **PASS** |
| wip-d | `26b4e745` | **BLOCK** |
| wip-e | `4d0f247a` | **PASS** |

- **时间线**(`round4/t6_blind_timeline.txt`):第 4 轮的两份审查分别在 05:14:23、05:16:32 结束;05:17:48 才第一次 checkout 到 `wip-a`;每次盲测调用都在该分支 checkout 之后开始、下一次 checkout 之前结束;05:24:43 切回 `metrix-e1-pilot-protocol-v1`;报告提交的审查 05:27:42 开始。任务 5 的两份审查运行期间,工作区没有 checkout 到任何 `wip-*` 分支。
- **记录**:每次调用的完整文字与审查原文没有写进仓库,因为 diff 本身就是答案。它们在会话容器的 `/root/.blind_r4/`(`prompt_wip-*.txt`、`review_wip-*.md`)。10 个文件的 sha256 已写入 `round4/t6_blind_timeline.txt`,答案公布后补交原文时,可以核对它们未被改动。这些文件将随本轮最终回复作为文件交给 Owner。这与本轮新加的第 9 节“原始输出一律写入仓库”冲突;按第 6 项“只在本地做”和“不写进仓库”执行,见待决第 9 项。

## 待 Review Gate 决定

1. **arm A 的 KL 在 4 篇锚文档之间怎么平均**(code-reviewer MAJOR 1):一种是把全部 (文档, t≥2) 位置合在一起平均,另一种是先对每篇求均值、再对 4 篇求均值。两种只在篇长不同时有差别,而篇长确实不同:512 篇里索引 340(从 0 起计)的一篇只有 123 个 token,其余 511 篇都是 128(`round4/t1_anchor_short_docs.txt`;存下的文本重新编码后的分布见 `round4/t1_anchor_token_counts.txt`)。data-auditor 观察 4 还提出:n_x 应取存下的文本重新编码后的长度,还是取原始截断的 id 长度。在现有数据上两者相同:索引 340 的那篇解码后再编码与原 id 逐个相同,其余篇都是 128。
2. **EM 的解码细节**(code-reviewer MAJOR 2;data-auditor 观察 1、2):
   - 停止 token 只有 151645,还是 {151645, 151643}?训练输入在每句后接 151643。
   - 输出是否包含停止 token,解码时是否 `skip_special_tokens`。
   - 固定 revision 的 `generation_config.json` 默认采样(do_sample=true、temperature 0.6、top_k 20、top_p 0.95,eos [151645, 151643]),实现时必须显式改成贪心解码。
3. **“去掉开头空格”的含义**(code-reviewer MINOR;data-auditor 观察 3):只去 U+0020 时,这一步被后面的“去首尾空白”覆盖,不影响结果(auditor 在 16,000 个模拟输出上验证:有无这一步结果相同);如果指去掉包括换行在内的全部空白,它会改变“第一行”取到的内容。
4. **`prefix(f)` 的措辞与 s_ST 的输入**(code-reviewer MAJOR 3、MINOR):“答案之前的文本”是否含答案前的空格?`st_prefix_check.py` 与 auditor 都按不含空格计算。`prefix(f)` 前面加不加特殊 token,协议也只能从“训练输入”一行推断。
5. **metrix/CLAUDE.md 修改的裁决出处、原因与作用范围**:见任务 3,请确认。
6. **`outside_metrix_check.py`**(code-reviewer MINOR):
   - 不识别 setext 标题(文字行下接 `===` 或 `---`),会漏判。
   - 代码块的判定是简化版。
   - 脚本是原地修改的,docstring 仍写 “Round 3, task 3”。要复现第 3 轮的 `t3_outside_metrix.txt`,须回到 `596fcfad`。
7. **两个检查脚本没有例子时会崩溃**(code-reviewer MINOR):`st_prefix_check.py` 与 `verify_scoring.py` 在没有可用例子时解包 None,抛出 TypeError,不打印 `RESULT:` 行(退出码仍非 0)。
8. **生成方法写得不够细**(data-auditor 观察 5,上轮遗留):第 2.6 节 S 的置换与第 2.5 节的候选抽取没有写死调用方式,数据生成后只凭协议文字无法逐字节复现 `train_S.jsonl` 与 `candidates.json` 的哈希。
9. **盲测原始记录与新第 9 节冲突**:按第 6 项,调用原文与审查原文没有入库,只入库了 sha256。是否在答案公布后补交原文,请决定。报告第 6 节保留的调用模板是否也应删去(报告提交审查 MAJOR 2),请决定。
10. **推送方式**:按本轮指令直接快进推送 `metrix-e1-pilot-protocol-v1`,没有经 PR(metrix/CLAUDE.md 第 6 节);同一 HEAD 也快进推送到本会话分支 `claude/metrix-e1-pilot-round4-minluk`。
11. **用户级副本**:`/root/.claude/CLAUDE.md` 未同步(code-reviewer MINOR;见任务 3)。
12. **auditor 脚本的 3 条 MINOR**(报告提交审查):`r4_scoring_em.py` import 了 `re` 却没有用;token id 151645、151643 写死,协议第 2.2 节的常量在两个脚本里各转录一份;`run_logged.sh` 的文件头 “CPU only (no GPU, no torch, tokenizer files only)” 是写死的字符串,也没有记录 `HF_HUB_OFFLINE`。这些是 auditor 的代码,Executor 没有改。
13. **临时目录里删除的文件**(报告提交审查 MAJOR 5):metrix/CLAUDE.md 第 7 节“删除任何文件”须等人工指令。这一条是否也管 scratchpad 里的临时文件,请明确。本轮的情况见“附”。

## 附:没有入库的两次失败运行,以及补入库的一次运行

- 第 1 次查锚文本长度时,我自己写的比较代码抛了 StopIteration。那次的输出文件在 scratchpad,我已删除,无法恢复。之后重写脚本重跑,入库的是重跑结果(`t1_anchor_short_docs.txt`,脚本 `anchor_short_docs.py`)。那次运行在抛错之前已打印出与重跑相同的一行:索引 340 的文档全文只有 123 个 token。这一行来自我当时看到的终端输出,没有文件可以作证。
- 生成 `t1_json_inline_check_full.txt` 时,第 1 次用 `tee /dev/stderr` 记录 heredoc 正文,文件被截断,内容错乱。之后用 `sed` 打印正文再重跑,覆盖了那个文件。错乱的版本没有保留,无法恢复。
- 05:10:10 统计锚文本重新编码后 token 数的一次运行(成功,512 篇中 511 篇 128、1 篇 123),输出当时只写在 scratchpad。本次补入库为 `round4/t1_anchor_token_counts.txt`:命令行一行改写为实际调用(venv 解释器、从 `<SCRATCH>` 运行);当时没有把 inline 脚本写进文件,文件末尾按会话记录补录了脚本正文,并注明是补录。
