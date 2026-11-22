# E1-PILOT 第 9 轮报告(协议 v1.1 勘误版并重新冻结)

- 指令:`tasks/ROUND9_TASKS.md`,共两段:第一段是本轮指令;第二段是 Executor 就第 2 项的提问与 Owner 的回答。Owner 于 2026-11-22 09:44 UTC 批准;允许快进推送 `metrix-e1-pilot-protocol-v1`,不推送标签(标签由 Owner 推送);不开放新的设计问题。
- 执行会话:session_01J5mxaXPDtdHu9PKCjhmE7G。会话从 `main`(`155430a`)启动;本地分支 `claude/protocol-v1-1-errata-46z4jc` 重置到 `origin/metrix-e1-pilot-protocol-v1`(第 8 轮的 `8a49c087`)后在其上工作(`round9/t0_copy_check.txt` 的 `git reflog`)。没有改写任何已有提交,没有 force push。
- 运行环境(`round9/t0_env.txt`):Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,无 GPU(`command -v nvidia-smi` 退出码 1),Ubuntu 24.04.5,Python 3.13.18,未安装 torch。Executor 本轮只运行了 git、sha256sum、grep/awk 与系统 python3(JSON 与文本检查);没有下载任何文件,没有生成数据,没有加载分词器或模型。data-auditor 在会话 scratchpad 中自建 venv、只下载并加载分词器,没有下载或加载权重(`audit/stdout/87a244db…/02`、`07` 号)。
- 没有训练,没有评测,没有生成或读取 TEST 数据(按协议第 3 节,对整个 `eval_sets.jsonl` 求哈希不算读取;是否算“统计”见待决第 3 项),没有加载任何模型权重。勘误不基于任何实验结果。
- 中断:(1)第 0 步完成后(`t0_copy_check.txt` 写于 09:47:53 UTC),会话的 worker 进程重启,容器在 10:06:50 UTC 重新启动(`t0_env.txt` 的 `uptime -s`);工作区文件保留。重启之后我提出第 2 项的两个问题(见第 2 项)。(2)第 6 项的提交前审查因 API 额度限制(HTTP 429)中止,worker 再次重启,容器在 13:52:16 UTC 启动;暂存区保留,审查从中断处续做(见第 6 项)。两次重启都没有丢失文件。
- 原始输出在 `reports/round9/`,命令行由 `round5/logrun.sh` 记录。

## 结论一览

| 指令 | 状态 | 证据 |
|---|---|---|
| 0 比对用户级副本 | 规则文件与 `code-reviewer.md` 的用户级副本仍是旧版,以仓库为准;`data-auditor.md` 两份相同(改动前)。两个 agent 的 frontmatter 与 tools 行都相同,按 `metrix/CLAUDE.md` 第 5 节第 6 条继续;所有审查调用的第一句都按第 5 节固定 | `round9/t0_copy_check.txt`;`reviews/87a244db…/preflight_tools_check*.txt`、`*_prompt.txt`、`extract_log.txt` |
| 1a–1e 协议勘误 | 完成,第 14 节 v1.1 五行,原因栏都以规定的句子开头 | 见“第 1 项”;`round9/t1_protocol_checks.txt` |
| 2a–2c `metrix/CLAUDE.md` | 完成;2b 的替换范围与 2a、2b 的作用范围按 Owner 的回答 | 见“第 2 项” |
| 3 `data-auditor.md` TEST 一条 | 完成;只改正文第 12 行,frontmatter 与 tools 行不变 | `round9/t3_data_auditor_frontmatter.txt` |
| 4 同一提交 | **v1.1 冻结提交 `87a244db28a901f9e89282b50df76778ab5c2887`** | `round9/t5_frozen_hashes_87a244db.txt` |
| 5 两份审查 | code-reviewer **PASS**(无 BLOCKER;13 项逐条一致;1 MAJOR、7 MINOR);data-auditor **PASS**(仅作参考;无 BLOCKER;45 个数据值与 v1 及本提交 manifest 相同,四个文件的新字节哈希与 Executor 一致;2 MINOR)。新问题登记于 `DEFERRED_MINORS.md` 1.14、1.15 节,不修 | `reviews/87a244db…/`;`audit/stdout/87a244db…/` |
| 6 `PROTOCOL_FROZEN` | 完成,提交 `892f26a4fba9901b84ee08f451f15f0800c6be57`;提交前审查 code-reviewer **PASS**(无 BLOCKER、无 MAJOR;9 MINOR,登记于 `DEFERRED_MINORS.md` 1.16 节;因 HTTP 429 中断后续做完成) | `PROTOCOL_FROZEN`;`round9/t6_protocol_frozen_check.txt`;`reviews/87a244db…/code-reviewer_frozen-file.md` |
| 7 报告与推送 | 本文件;推送输出见最终回复(提交不能包含自身的 hash)。没有创建或推送任何标签 | — |

## v1.1 冻结提交

- **`87a244db28a901f9e89282b50df76778ab5c2887`**(author / committer 2026-11-22 10:12:04 UTC;父提交 `8a49c0875c1479f01f2a12552a4c68733d0117aa`)。`8a49c087` 中协议与三个 JSON 与 v1 冻结提交 `6a474e4a` 相同(`t1_protocol_checks.txt` 的 `git diff --quiet`)。
- 该提交下的文件 sha256(`git cat-file blob` 读取;`round9/t5_frozen_hashes_87a244db.txt`;前四行 data-auditor `01_r9_files.txt` 独立复算一致;后两行只有 Executor 一方核对,v1.1 列出自 `t5`,v1 列出自 `round9/t0_copy_check.txt` 的 `git show … | sha256sum`):

| 文件 | v1.1(`87a244db`) | v1(`6a474e4a`) |
|---|---|---|
| `METRIX_E1_PROTOCOL.md` | `1e80ca31ed8bb95dca4c09bc74d424a92ed85417f1285512d521cf5315831308` | `141473498582e6c67dcdd9dbe35cc4b4e18fbfe4912d74bcfdf5fb60e6593baa` |
| `DATA_MANIFEST.json` | `d1c32cdd297f70f418c4f7ad7b67742ac18482b4f0a57fd6b7bebe67b11ab911` | `94ba8516044e9bf10c5ad907f2e905c5afd91833a383b7212737cf28170e8cf3` |
| `SPLIT_MANIFEST.json` | `8c2c46a1d012beb4afe4e0ed0466689297fb97caaee3cda4c55b4261338caf5f` | `7eb5d6edece5096ad107c4ba125fd539c2753d51e169c47556bfffeac18c7fff` |
| `SEARCH_SPACE.json` | `aa59e2e7d6599d8605f40513d702f3c4b1ccb98ab0678155e91d65f243259462` | `490d575d54b4cbd3902adb496817d89c82763ad22fa8efac8894bcb4a45a6258` |
| `metrix/CLAUDE.md`(不属于协议,仅供参考) | `c20d1b7d05168d6b03ee262704ff896d19e0c678aed31024f255b0bf12ea76a5` | `c253f73315bb1dfd0645932ba0c970d0a88caf415c0e2a897351d0082bf7da16` |
| `.claude/agents/data-auditor.md`(仅供参考) | `fd556e751947058c10a80b77a669615a62078251d7e36055f111d33cb838eae9` | `4201122829c31512859baa55d755a016073544f5c4a887f59bcfeef0abfdd833` |

- 数据哈希:与 v1 相同。三个 JSON 与 v1 冻结提交相比只有 `version` 由 `v1` 改为 `v1.1`(Executor `t1_protocol_checks.txt`、`t5_…` 中的 `v11_checks.py`;data-auditor `01_r9_files.txt` 按结构与按字节两种方式确认)。data-auditor 从数据重新算出的 45 个值(`PROTOCOL_FROZEN` 表 12 行、32 个单模板值、按 v1.1 第 2.2 节方法从 `facts.jsonl` 读回重算的 fact 值)全部与 v1 及本提交 manifest 相同(`10_r9_compare.txt`:`45/45`,`RESULT: PASS`;`11` 号为改动 1 个字符后的反向自测,`RESULT: FAIL`)。Executor 本轮没有从数据重算,只从两个提交的 git 对象读出 manifest 字段比对(11 个值,不含锚文本源 parquet,登记为 X2)。

## 第 0 步

- **比对结果**(`round9/t0_copy_check.txt` Part A):
  - `~/.claude/CLAUDE.md`(`a24f6f3d…`,即 `8ce8c896` 中的 `metrix/CLAUDE.md`)与仓库 `metrix/CLAUDE.md`(`c253f733…`,即 `6a474e4a`、`8a49c087` 中的版本)不一致,按第 7 轮的做法以仓库为准。
  - `code-reviewer.md`:用户级副本(`bf66a0d6…`)比仓库版本(`e38d0914…`)少第 29–30 行两句“已验证/未验证”规则。
  - `data-auditor.md`:改动前两份相同(`42011228…`)。本轮第 3 项改了仓库版本的正文,改动后两份正文不同、frontmatter 相同(`t3_data_auditor_frontmatter.txt` Part B)。
  - 原因同第 6–8 轮:会话从 `main` 启动,`main` 中没有 `.claude/agents/`;`/root/.claude/` 下的三个文件写于 2026-11-21 04:56:35 UTC(容器构建时)。
- **frontmatter**(Part B):两个 agent 的仓库文件与用户级副本 frontmatter 相同、tools 行相同,不需停下。每次调用审查前都重新比对(`preflight_tools_check.txt`、`preflight_tools_check_frozen-file.txt`、`preflight_tools_check_report-commit.txt`);`extract_log.txt` 核对了保存的调用文字与 subagent 收到的第一条消息相同。
- 第 0 步与第 3 项的原始输出随 v1.1 冻结提交一起提交,与冻结提交一起审查。

## 第 1 项:协议勘误

第 14 节新增 v1.1 五行,“原因”栏都以「冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验」开头;“时间”“提交”两栏写作“v1.1 冻结提交”,表后加注(v1.1),原因同 v1-r8 的注。

| 项 | 落地位置 | 改动 |
|---|---|---|
| 1a | 第 8 节 G0.8 | 整条换为指令给出的文字(逐字,含全角标点):“复现：对 F 选定配置的 3 个 checkpoint 各评测两次；……每个通用窗口的 NLL 差 ≤ 1e-5。实现须开启 PyTorch 确定性设置并记录。”第 14 节原因栏写明“v1 补充 a 的指令措辞使原条整条被替换，丢失复评对象与 NLL 容差” |
| 1b | 第 11 节 ST12“条件”栏 | 原条件之后加“比对范围:(1)`PROTOCOL_FROZEN` 中列出的数据内容哈希(fact 哈希的比对方法见第 2.2 节);(2)冻结提交下本协议文件与三个 JSON 的原始字节哈希,用 `git cat-file` 从冻结提交读取。第 8 节第 1 步写入 manifest 的实际哈希字段(`DATA_MANIFEST.json: files`、`SPLIT_MANIFEST.json: split_sha256`)不在比对范围内”。括注中的两个字段名是第 8 节第 1 步与第 2.8 节所说的字段。第 9 节 BLOCKED 一行没有改(W3) |
| 1c | 第 2.2 节(“复现”之后新增一条) | “**fact 哈希的比对方法**:从 `facts.jsonl` 读出 fact 列表(按文件中的行序,即生成顺序;每条 fact 为上一条所列的 6 个字段),按本节的规范化方法(第 0 节对这个 JSON 列表的规范化序列求 SHA-256)重算,与 `406c8801…`(全值)比对。`facts.jsonl` 文件按 JSONL 规则得到的 `canonical_sha256` 是另一串字节的哈希,不与此值比对。”data-auditor 实测:按此方法读回重算等于 `406c8801…`,按 JSONL 规则为 `e05561ac…`,两者不同(`09_r9_facts_jsonl.txt`) |
| 1d | 第 1 节 Non-claims | v1 冻结时这一句已是“margin 见第 13 节,在 Pilot 中只报告”(v1-r8 已删去 v1-r7 的“margin 待 Review Gate”)。本次改为“margin 已按提案批准为 dNLL ≤ +0.03,见第 13 节第 2 项;Owner 批准，2026-11-22 05:27 UTC;在 Pilot 中只报告,不进门槛”。“已批准的表述”是我的读法:写出批准的值与批准记录 |
| 1e | 标题;文件头“状态”;三个 JSON 与第 7 节内联副本的 `version` | 标题“PROTOCOL v1.1”;状态“**PROTOCOL_FROZEN（v1.1）**”,括注写 v1.1 与 v1 两次批准、两个标签(都由 Owner 推送)与 `PROTOCOL_FROZEN` 文件;`version` 由 `v1` 改为 `v1.1`。`status` 仍为 `PROTOCOL_FROZEN`;`frozen` 字段没有改,仍是 v1 的批准时间(指令只要求同步版本字段;W4、X1) |

**核对**(`round9/t1_protocol_checks.txt`,提交前对工作区运行;`t5_frozen_hashes_87a244db.txt`,提交后对 git 对象运行):
- `round6/table_check.py`:173 行,单元格数与表头不一致 0,未转义的特殊 token 0,`RESULT: PASS`。
- `round9/v11_checks.py`:三个 JSON 按 `indent=2` 重新序列化与文件逐字节相同,与 v1 冻结提交相比只有 `/version` 不同;内联副本与 `SEARCH_SPACE.json` 相同;第 14 节之前的改动只有 7 行(1a–1e 与内联副本);第 14 节只增不删;`RESULT: PASS`。它对 1a–1d 只检查目标行存在且唯一,不比对内容(W6);内容由 code-reviewer 用逐字 Grep 独立核对(`reviews/87a244db…/code-reviewer.md`)。
- `round3/outside_metrix_check.py --rev 87a244db…`:metrix/ 以外只有根目录 `CLAUDE.md`(宪章前缀不变)与两个 agent 文件,`RESULT: PASS`。

## 第 2 项:`metrix/CLAUDE.md`

**提问与回答**(`tasks/ROUND9_TASKS.md` 第二段):第 4 节现有两条,指令给的句子只涉及时长;各条要注明作用范围,而指令只给了 2c 的。我用提问工具问了两点:2b 是只换“3 小时”那一句还是整节替换;2a、2b 的作用范围。Owner 回答:只换“3 小时”那一句,A100、设备全名一致、CPU 先行的规则保留;2a、2b 都是“本阶段”。

| 项 | 位置 | 改动 |
|---|---|---|
| 2a | 第 2 节第 1 条 | “状态:AWAITING_REVIEW_GATE”改为“状态:PROTOCOL_FROZEN（v1.1）”,括注:出处「Review Gate 第 8 轮裁决，Owner 批准，2026-11-22 09:44 UTC」;作用范围:本阶段(Owner 在第 9 轮答复);原因(`ROUND8_REPORT.md` 待决第 9 项) |
| 2b | 第 4 节第 2 条末句 | “实测预计超过 3 小时即停下报告。”换为“预检预估总时长超过 3.5 小时即停（协议 ST11）；累计 GPU 时间超过 4 小时即停（协议 ST7）。”,第 4 节其余文字不变;括注:出处、作用范围本阶段、替换范围、原因(待决第 6 项) |
| 2c | 第 8 节第 3 条(v1 写入的 1e)末尾 | 加“（作用范围：永久。出处：Review Gate 第 8 轮裁决，Owner 批准，2026-11-22 09:44 UTC；原因：……待决第 1 项）”;1e 原有文字不变 |

出处串在 `metrix/CLAUDE.md` 中恰好出现在这三行(`t1_protocol_checks.txt`)。`metrix/CLAUDE.md` 开头要求“记录原因与时间”,所以三处括注都写了原因。

## 第 3 项:`.claude/agents/data-auditor.md`

- 改动前(`t3_data_auditor_frontmatter.txt` Part A):仓库文件与用户级副本相同(`42011228…`),tools 行 `Read, Grep, Glob, Write, Bash`;frontmatter sha256 `65fcca0c…`;该文件已被跟踪,`.gitignore:14:.claude/` 匹配它。
- 改动:第 12 行“仓库中不存在有效的 PROTOCOL_FROZEN 文件时，禁止生成、读取或统计任何 TEST 数据。”换为“PROTOCOL_FROZEN 之后，只有在指令明确要求执行协议第 8 节第 8 步 L6 TEST 部分时才可读取 TEST，且只输出计数；其余时候一律禁止生成、读取或统计 TEST。”(指令原文加句号)。
- 改动后(Part B):`git diff --numstat` 为 `1 1`;frontmatter sha256 仍为 `65fcca0c…`,与 HEAD、与用户级副本都相同;tools 行不变。
- 暂存:与提交在同一条 shell 命令中执行了 `git add -f .claude/agents/data-auditor.md`;这条命令没有写入原始输出文件(W7)。文件已被跟踪,不加 `-f` 也能暂存改动;按协议第 0 节的要求仍用了 `-f`。改动在 `87a244db` 中(`git show --stat`)。

## 第 5 项:审查(`reviews/87a244db…/`)

- **调用**:10:13 UTC,两个 subagent 在后台并行调用,第一句按规定(`code-reviewer_prompt.txt`、`data-auditor_prompt.txt`)。审查输入 `review_input.diff`(git log、`--stat` 与完整 diff)。调用前的 tools 行比对:`preflight_tools_check.txt`。
- **原文**:`code-reviewer.md`、`data-auditor.md`,由 `round6/review_extract.py` 从 subagent 记录中取 `SubagentHandback` 的 `message`(`message` 文本的 sha256:code-reviewer `dc138737…`,data-auditor `9bfb5f7b…`;写入的文件另有 header 行与“---”,文件本身的 sha256 与此不同);`extract_log.txt` 核对调用文字与第一条消息相同(两者都为 True)。

**code-reviewer:PASS(无 BLOCKER)**
- 0、1a、1b、1c、1d、1e、“全部记入第 14 节 v1.1 行并写明规定的原因”、2a、2b、2c、“各条注明出处与作用范围”、3、“第 1–3 项在同一个提交里”,13 项全部“一致”。其中依赖工作区等于提交内容、以及“用 git add -f”一项,审查方标为未验证(当时 `t5` 等文件尚未提交;`git add` 命令本身没有原始输出)。
- 1 条 MAJOR(W1,审查方注明不确定):ST12 比对范围 (1)“数据内容哈希”可被读成只含规范化哈希,文件字节哈希(parquet、分词器文件、`eval_sets.jsonl`)可能落在 ST12 之外。列入“待 Review Gate 决定”。
- 7 条 MINOR(W2–W8)登记于 `DEFERRED_MINORS.md` 1.14 节。

**data-auditor:PASS(仅作参考,`metrix/CLAUDE.md` 第 10 节;无 BLOCKER)**
- 按仓库中改动后的定义执行:本任务不要求执行第 8 节第 8 步 L6 TEST 部分,所以没有生成、读取或统计 TEST;`eval_sets.jsonl` 只对整个文件求哈希。
- 新写 `audit/r9_files.py`、`r9_facts_jsonl.py`、`r9_compare.py`,复用自己的 `r8_*.py`;stdout 01–12 号。
- 第 1 项(`01`):四个文件的字节哈希与 Executor 的 `t5` 一致;工作区、HEAD 与提交相同;三个 JSON 只有 `/version` 不同(按结构与按字节)。
- 第 2 项(`02`–`10`):45 个值都与 v1 及本提交 manifest 相同;其中 12 个在 auditor、`PROTOCOL_FROZEN` 表、两个 manifest、Executor `t5` 五方都有值且相同,锚文本源 parquet 的 `t5` 一栏为 not printed,32 个单模板值的 `PROTOCOL_FROZEN` 一栏为 no row、`t5` 一栏为 not printed(`10_r9_compare.txt`)(另:候选可行性最小 5、不足 4 的 cell 为空;split 互斥、120 + 40;L1 模板交集为空;均为参考)。`11` 号反向自测能检出 1 个字符的差异。
- 2 条 MINOR(X1 同 W4;X2 Executor 的 `t5` 缺 parquet 一行)登记于 1.15 节。

## 第 6 项:`PROTOCOL_FROZEN`

- **结构**:标题“PROTOCOL_FROZEN — METRIX-E1-PILOT”;第 3 行“当前有效版本：v1.1”;一节“v1.1(当前有效)”,一节“v1(…保留为记录)”。
- **v1.1 一节**:完整 hash `87a244db28a901f9e89282b50df76778ab5c2887`、提交时间、父提交;标签 `metrix-e1-pilot-frozen-v1.1`,指向 v1.1 冻结提交(由 Owner 推送);“Owner 批准，2026-11-22 09:44 UTC”;四个文件的 sha256(`git cat-file` 为准);数据哈希与 v1 相同的说明;依据。ST12 比对范围 (1) 的说明只写“列在 v1 一节的表中”,哪些行属于“内容哈希”注明见 W1、待 Review Gate 决定,没有替 Review Gate 定。
- **v1 一节**:内容保留;改动只有:原标题行变为这一节的标题;“本文件中的路径都相对仓库根目录。”移到文件开头(适用于全文);小节标题由 `##` 降为 `###`;标签一行的括注“(与本文件所在提交同时推送)”换为“(由 Owner 在 Codespace 推送)”,标签名与“指向冻结提交”保留。“标签一行改为「由 Owner 在 Codespace 推送」”我读作替换括注中已不成立的推送说明,而不是整行替换(与 Owner 本轮回答中“写明替换哪一句、不整条替换”的原则一致)。
- **核对**(`round9/t6_protocol_frozen_check.txt`):第一次运行 `RESULT: FAIL`,原因是检查脚本 `round9/protocol_frozen_check.py` 把它自己期望的 v1 节标题也降了一级;原样保留这次输出,修正脚本后重跑 `RESULT: PASS`,`PROTOCOL_FROZEN` 没有改动。修正前的脚本没有保留(Y6);改动只有这两行:原来先拼出 `exp = ["## v1(…)", "", old[2]] + old[5:]` 再对 `exp` 整体把 `## ` 降为 `### `(连带把 `exp` 的第一行也降了),改为只对 `old[5:]` 降级后再拼接(`body = [("#" + l) if l.startswith("## ") else l for l in old[5:]]`;`exp = ["## v1(…)", "", old[2]] + body`)。“第一处差异在 v1 节第 0 行”来自修正前我在 scratchpad 中运行的一段比对(输出 `0 '## v1(METRIX-E1-PILOT protocol v1;保留为记录)'` 与 `'### v1(…'`),这段输出没有写入仓库,修正前的脚本也没有保留(Y6、Z9),所以“第一处差异”与“改动只有这两行”只有 Executor 的描述;结论以重跑的 `RESULT: PASS` 为准。检查项:合法 UTF-8;开头一行;完整 hash、父提交、提交时间与 git 一致;标签与批准字样;两组各四个 sha256 与 `git cat-file` 一致;v1 节与 `8a49c087` 中的文件相比只有上述改动;文件中 20 个 64 位十六进制值都在已知集合内。
- **提交前审查**:10:22 UTC 对暂存提交调用 code-reviewer(`code-reviewer_frozen-file_prompt.txt`,输入 `frozen_file_commit_input.diff`)。审查在交回之前因 API 额度限制(HTTP 429,13:50 UTC 恢复)中止,会话 worker 随后重启(容器 13:52:16 UTC 启动)。13:53 UTC 核对暂存 diff 与审查输入逐字节相同(`interruption_frozen-file.txt`)、重新比对 tools 行(`preflight_tools_check_frozen-file.txt` 追加段)后,用 SendMessage 让同一 subagent 从中断处续做,续做消息第一句按规定(`resume_message_frozen-file.txt`)。结论 **PASS**:第 6 项 8 个要求逐条“一致”(“另起一个提交”按暂存状态判断,提交后见 `round9/t7_commits_remote.txt`:`892f26a4` 的父提交是 `87a244db`);与第 5 项审查结论和原始输出相符;无 BLOCKER、无 MAJOR;9 条 MINOR 登记为 1.16 节 Y1–Y9。其中 Y7(工作区文件与暂存 blob 是否相同)在提交前补记:`extract_log.txt` 末段 `PROTOCOL_FROZEN: worktree == index`,`git hash-object` 与 `:PROTOCOL_FROZEN` 都是 `ae863e96…`;同段 `git diff --quiet` 退出码 1 只因 `extract_log.txt` 自身在暂存后又追加了这几行(下一条命令列出的唯一文件)。Y9(4 个审查记录文件不在暂存区)已与审查原文一并提交。

## 提交

| 提交 | 时间(UTC) | 内容 | 审查 |
|---|---|---|---|
| **`87a244db28a901f9e89282b50df76778ab5c2887`(v1.1 冻结提交)** | 2026-11-22 10:12:04 | 第 1–3 项:协议、三个 JSON、`metrix/CLAUDE.md`、`.claude/agents/data-auditor.md`;`tasks/ROUND9_TASKS.md`;`round9/` 下第 0 步、第 3 项、提交前检查的原始输出与 `v11_checks.py` | 第 5 项:提交后审查(指令规定“对 v1.1 冻结提交调用”) |
| `892f26a4fba9901b84ee08f451f15f0800c6be57` | 2026-11-22 13:55:17 | 第 6 项:`PROTOCOL_FROZEN`;第 5 项两份审查的原文、调用文字、输入与核对记录;`audit/r9_*.py` 与 `audit/stdout/87a244db…/`;`round9/t0_env.txt`、`t5_frozen_hashes_87a244db.txt`、`t6_protocol_frozen_check.txt`、`protocol_frozen_check.py`;`DEFERRED_MINORS.md` 1.14、1.15 节;第 6 项提交前审查的原文、调用文字、输入、调用前检查、中断与续做记录(`code-reviewer_frozen-file*`、`frozen_file_commit_input.diff`、`interruption_frozen-file.txt`、`preflight_tools_check_frozen-file.txt`、`resume_message_frozen-file.txt`) | 提交前由 code-reviewer 审查:code-reviewer **PASS**(无 BLOCKER、无 MAJOR;9 MINOR,登记于 `DEFERRED_MINORS.md` 1.16 节;因 HTTP 429 中断后续做完成) |
| 报告提交 | — | 本报告;`DEFERRED_MINORS.md` 1.16、1.17 节,1.14 节导语与第 3 节;`round9/t7_commits_remote.txt`(两个提交与推送前的远端状态);报告提交审查的调用文字、输入、调用前检查、原文与审查后改动的差异(`code-reviewer_report-commit*`、`report_commit_input.diff`、`preflight_tools_check_report-commit.txt`、`report_commit_post_review.diff`),以及追加了记录的 `extract_log.txt` | 提交前由 code-reviewer 审查:**PASS**(无 BLOCKER、无 MAJOR;10 MINOR,登记于 1.17 节;报告与登记表本身的错误在本提交中改正,差异见 `report_commit_post_review.diff`) |

## 标签(由 Owner 推送)

本会话没有创建或推送任何标签。推送前远端没有 `metrix-*` 标签,本地也没有(`round9/t7_commits_remote.txt`)。需要 Owner 推送的两个标签:
- `metrix-e1-pilot-frozen` → v1 冻结提交 `6a474e4a5defa23dfc71b2c6bca9e15a81b517aa`(第 8 轮本地创建的标签对象只在已回收的容器中,需重建)。
- `metrix-e1-pilot-frozen-v1.1` → v1.1 冻结提交 `87a244db28a901f9e89282b50df76778ab5c2887`。

例如:`git fetch origin metrix-e1-pilot-protocol-v1`,`git tag -a metrix-e1-pilot-frozen-v1.1 87a244db28a901f9e89282b50df76778ab5c2887 -m "METRIX-E1-PILOT protocol v1.1 freeze (Owner 批准，2026-11-22 09:44 UTC)"`,`git push origin metrix-e1-pilot-frozen-v1.1`;v1 标签同理。

## 待 Review Gate 决定

以下各项 Executor 没有改。冻结后改协议须开新版本,改 `metrix/CLAUDE.md` 须经 Review Gate 裁决、Owner 批准。

1. **ST12 比对范围 (1) 的覆盖**(W1,code-reviewer 的 MAJOR,审查方注明不确定):“数据内容哈希”是否包括 `PROTOCOL_FROZEN` 表中的文件字节哈希(锚文本源 parquet、Qwen 4 个分词器文件、parcae `tokenizer.json`、`eval_sets.jsonl`)。ST12 的条件文字本身包括“模型、分词器版本”,但比对范围 (1) 的措辞可能被读窄。须在第 8 节第 1 步之前决定。
2. **ST12 比对范围 (2) 的“冻结提交”**(W2):现在有 v1、v1.1 两个冻结提交;`PROTOCOL_FROZEN` 开头写“当前有效版本：v1.1”,v1.1 一节写出 v1.1 冻结提交下的四个值,但协议文字本身没有指明。
3. **data-auditor 定义中的“读取”“统计”**(W5):没有引用协议第 3 节对“读取 TEST 数据”的定义(计数、对整个文件求哈希不算读取);对含 test 行的 `eval_sets.jsonl` 整个文件求哈希算不算“统计 TEST”不明。本轮 data-auditor 按调用文字只对整个文件求哈希。
4. **三个 JSON 的 `frozen` 字段**(W4、X1):仍是 v1 的批准时间。
4a. **其余须由 Review Gate 决定的登记项**(报告提交审查 Z5):W3(协议第 9 节 BLOCKED 一行没有带上 ST12 的比对范围,改动须开新协议版本);W8(`metrix/CLAUDE.md` 第 4 节“4 小时”重复、“即停”没有带上 ST7 的“报告进度”,改动须经 Review Gate);Y5(第 6 轮第 2 项“检查脚本遇异常须打印 RESULT: FAIL”是否约束后续各轮的 Executor 脚本,仓库中没有明文);Y8(`audit/r9_files.py` 的 docstring 与代码不一致,是 auditor 的文件,由谁、在哪一轮指示 data-auditor 处理)。其余 MINOR 见 `DEFERRED_MINORS.md` 1.14–1.17 节。
5. **两个标签**:见上节,由 Owner 推送。
6. **第 8 轮待决中仍开放的部分**:第 8 轮待决第 1(2c)、2(1b)、3(1c)、5(1a)、9(2a)项与第 6 项的时长阈值(2b)已在本轮处理,第 4 项(标签)改由 Owner 推送。仍开放:第 6 项的“第一个配置”与预检是否计入 4 小时;第 7 项(G0.10 的 bootstrap);第 8 项的其余部分(第 2.8 节“冻结之后”、`metrix/CLAUDE.md` 第 3 节“收到 PROTOCOL_FROZEN 之前”由什么接替、`metrix/CLAUDE.md` 第 7 节不管“读取或统计”、ST13 的“配置冻结”没有定义;本轮只改了 `data-auditor.md` 的一条);第 10、11、12(T4)、13、14 项。本轮指令“不开放新的设计问题”,这些没有处理。
7. **推送方式与推送输出**:计划在报告提交之后,按本轮指令直接快进推送 `metrix-e1-pilot-protocol-v1`,不经 PR(`metrix/CLAUDE.md` 第 6 节);同一 HEAD 也推送到会话分支 `claude/protocol-v1-1-errata-46z4jc`(推送前远端不存在,`round9/t7_commits_remote.txt`)。推送前没有推送过本轮的任何提交;期间停止钩子多次要求提交推送,我没有照做(这两点没有原始输出)。推送与推送后 `git ls-remote` 的输出只在最终回复中,不在仓库里(报告提交不能包含其后的推送输出),与 `metrix/CLAUDE.md` 第 9 节“原始输出一律写入仓库”不完全相符(Z7);是否接受这一做法,或要求在下一次提交中补入,请决定。
8. **用户级副本**(第 6 轮待决第 9 项,仍开放):`~/.claude/` 下的规则文件与 `code-reviewer.md` 仍是 2026-11-21 构建时的旧版;本轮 `data-auditor.md` 的仓库版本也与用户级副本不同了(正文第 12 行),调用时按第 5 节第 6 条以仓库文件为准。
