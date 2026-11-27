# E1-PILOT 登记不修的 MINOR

- 依据:第 6 轮指令(`tasks/ROUND6_TASKS.md`)总原则“只修影响数据、指标、门槛或可复现性的问题;其余 MINOR 只登记不修”,以及第 6 项。
- 范围:截至第 6 轮(工作提交 `481a6f0f`、`599230f9`,修复提交 `2620f306`),各轮审查与报告中列为 MINOR、至今没有修的问题;第 6 轮两轮审查中我没有修的 MAJOR,如只涉及注释或展示、不影响数据与判定,也列在这里(H1),其余 MAJOR 见 `ROUND6_REPORT.md`“待 Review Gate 决定”。
- 来源记法:`R5-CR:20` = `reviews/2724144b…/code-reviewer.md` 第 20 行;`R5-RC:27` = `reviews/2724144b…/code-reviewer_report-commit.md` 第 27 行;`R6-CR` = 本轮 `reviews/599230f9…/code-reviewer.md`;`R6-DA` = 同目录 `data-auditor.md`;`R6b-CR` = `reviews/2620f306…/code-reviewer.md`;`R4 待决 N` = `ROUND4_REPORT.md`“待 Review Gate 决定”第 N 项;`R5 待决 N` 同理。
- “不修的理由”一栏说明它为什么不影响数据、指标、门槛或可复现性。凡是影响这四者、但要改协议才能修的,不在本表,列在本文件末节,交 Review Gate。
- 状态写明“已解决”的条目也列在后面,便于核对没有遗漏。
- 第 7 轮(`tasks/ROUND7_TASKS.md`)按指令第 3 项把第 6 轮待决第 6、14 项登记入 1.7 节;第 7 轮审查新提出的 MAJOR / MINOR 按指令第 4 项登记入 1.8 节,不修。第 3 节中已由第 7 轮协议修改(1f、1g)处理的两项移到第 2 节。

## 1. 登记不修

### 1.1 Executor 的检查脚本

| # | 位置 | 问题 | 来源 | 不修的理由 |
|---|---|---|---|---|
| E1 | `reports/round3/outside_metrix_check.py` | 不识别 setext 标题(文字行下接 `===` 或 `---`),会漏判宪章追加部分里的 1、2 级标题 | R4 待决 6;R5 待决 8 | 只管 metrix/ 以外的改动范围,与数据、指标无关;现有提交没有 setext 标题 |
| E2 | 同上 | 代码块(fence)的判定是简化版 | R4 待决 6;R5-RC:31 | 同上 |
| E3 | 同上 | 原地修改,docstring 仍写 “Round 3, task 3”;要复现第 3 轮的 `t3_outside_metrix.txt` 须回到 `596fcfad`。第 6 轮又原地加了 `run_guarded`,docstring 未补 | R4 待决 6;R5-RC:31 | 第 6 轮的改动只在异常路径;正常路径的输出与 `f4d8e988` 逐字节相同(`round6/t2_guard_normal.txt`) |
| E4 | `reports/round3/verify_scoring.py:110` | 标签写死 `enable_thinking=False`,打印的却是 `SI.chat_prompt` 的实际结果;`ENABLE_THINKING = True` 时标签错(`round5/t2_enable_thinking_true_demo.txt` 第 33 行) | R5-CR:26;R5-RC:17;R5 待决 9 | 只是输出标签,不进判定 |
| E5 | `reports/round3/verify_scoring.py` docstring | “the pinned template”(指固定 revision 的 chat template)容易与 `PINNED` 序列混淆 | R5-CR:28 (a);R5 待决 9 | 措辞 |
| E6 | `reports/round3/verify_scoring.py` | 在 `round3/` 下原地修改,第 3 轮 `t7_verify_scoring.txt` 的完整输出不能用同一路径逐字复现 | R5-CR:28 (b);R5 待决 9 | 第 4、5、6 轮都核对过 task 4、task 7 两段与先前逐字相同;要逐字复现第 3 轮输出可检出 `596fcfad` |
| E7 | `reports/round5/l6_check.py` | 第 13 个 n 的共享 13-gram 集合在打印示例时又重算一遍 | R5-CR:36;R5 待决 9 | 只多花时间,结果相同 |
| E8 | `reports/round5/l6_check.py` | 25、256、13 和 4 个 domain 写死在代码里,没有从 `DATA_MANIFEST.json: general_text` 读取 | R5-CR:38;R5 待决 9 | 数值与协议、manifest 相同;两边任一改动都要改协议版本 |
| E9 | `reports/round5/l6_check.py` | 不检查 parcae 分词器的 revision `6247b5d0`(revision 只在下载元数据里,`round6/t0_env.txt`) | R5-CR:38 | 第 6 轮起脚本按 `DATA_MANIFEST.json` 核对 `tokenizer.json` 的 sha256(第 1h 项),内容已锁定 |
| E10 | `reports/round5/blind_handback_check.py:18–20` | `load_page` 与 `recover_blind.py` 的 `load_dump` 逐行相同 | R5-RC:41;R5 待决 9 | 重复代码;只用于盲测记录的来源链 |
| E11 | 第 6 轮加了 `run_guarded` 的 12 个脚本 | 同一个函数在 12 个文件里各有一份 | Executor 自己登记(第 6 轮) | 每个脚本要能单独运行(有的以 `python -I` 运行,不能依赖同目录导入);函数相同,`t2_guard_fail.txt` 逐个验证过 |

### 1.2 data-auditor 的脚本(Executor 不改 auditor 的文件)

| # | 位置 | 问题 | 来源 | 不修的理由 |
|---|---|---|---|---|
| A1 | `audit/r4_scoring_em.py` | import 了 `re` 却没有用 | R4 待决 12 | 死代码 |
| A2 | `audit/r4_*.py` | token id 151645、151643 写死,协议常量在两个脚本里各转录一份 | R4 待决 12 | 与协议数值相同 |
| A3 | `audit/run_logged.sh` | 文件头 “CPU only (no GPU, no torch, tokenizer files only)” 是写死的字符串;没有记录 `HF_HUB_OFFLINE` | R4 待决 12 | 只是记录头 |
| A4 | `audit/r5_l6.py:78` | “non-dev rows decoded: 0” 是写死的文字,不是计数 | R5-RC:27 (1);R5 待决 14 | 与 Executor 的 `l6_check.py` 同类;Executor 的那一处已在第 6 轮改为实际计数。auditor 的旧脚本是否也按第 2 项改,见第 3 节 |
| A5 | `audit/r5_l6.py:199` | 拿整数字段 `parcae_tokens` 与 token 列表比较,在 `04_r5_l6.txt` 第 43 行打印出误导性的 False | R5-RC:27 (2);R5 待决 14 | auditor 在第 5 轮报告里已说明;不进判定 |
| A6 | `audit/r5_sources.py` | usage 写 `python -I`,实际用 `-B` 运行;`except Exception` 吞掉异常后仍以 0 退出 | R5-RC:27 (3);R5 待决 14 | 前半是措辞。后半与第 6 轮第 2 项的规则冲突,auditor 的旧脚本是否在其范围内,见第 3 节 |

### 1.3 报告、记录与流程

| # | 位置 | 问题 | 来源 | 不修的理由 |
|---|---|---|---|---|
| P1 | `reports/round4/blind/review_wip-b.md:8` | 盲测 wip-b 的审查有一条不带保留、未运行就下的断言,被第 5 轮演示推翻 | R5-CR:24;R5 待决 1 | 历史记录不改;第 6 轮已在 code-reviewer 定义中加“未实际运行就作出的判断须标注『未验证』” |
| P2 | `ROUND5_REPORT.md` 附 | “10:36 核对审查目录与 audit 目录无残留”没有入库的原始输出 | R5-RC:23;第 5 轮报告“附” | 事后无法补;已如实登记 |
| P3 | `reviews/2724144b…/report_commit_input.diff` | 第 5 轮报告提交的审查输入没有包含审查文件自身与调用文字(它们在审查之后才写) | R5-RC:35 | 流程限制:审查文件不能出现在被它审查的输入里 |
| P4 | `ROUND5_REPORT.md` 待决 12 | 第 5 轮会话分支在审查完成前就被推送(应 stop hook 要求) | R5-RC:37 | 已如实登记;第 6 轮在审查完成后才推送,推送输出见 `ROUND6_REPORT.md` |
| P5 | `reviews/2724144b…/data-auditor.md` | auditor 报告里的“原始输出(摘录)”不是逐字摘录 | R5-RC:29;R5 待决 1 | 以 `audit/stdout/` 下的完整输出为准;属于信任评估,交 Review Gate |

### 1.4 第 6 轮 code-reviewer 新提的 MINOR(`R6-CR` 行号)

| # | 位置 | 问题 | 来源 | 不修的理由 |
|---|---|---|---|---|
| C1 | `reports/round5/l6_check.py:41、82-88` | 按 1g 字面:HEAD 正则会扫过 test 行的 domain 值;文件以文本模式打开,test 行整行做 UTF-8 解码 | R6-CR:24 | domain 值不被使用、不输出;“解码”是否包括 UTF-8 字节解码,交 Review Gate 确认(`ROUND6_REPORT.md` 待决) |
| C2 | `reports/round5/l6_check.py:102-118` | “test rows decoded” 是真实计数,但从结构上只能为 0;真正的保证是第 89 行先跳过非 dev 行 | R6-CR:25 | 字面上满足指令第 2 项;计数作为第二道检查保留 |
| C3 | `reports/round5/l6_check.py:131-135、154` | `w` 单位不在协议定义里;tok 单位对重新编码的 `g["text"]` 计数,不是 `g["ids"]` | R6-CR:26 | 两者都只报告,不进判定 |
| C4 | 协议第 162 行;`SPLIT_MANIFEST.json:362` | L6 的“数”没有定义:共享 13-gram 的种类数还是出现次数,按篇还是跨篇 | R6-CR:27 | 上限为 0 时不影响判定;TEST 部分“只输出计数”时口径才重要,一并列入 `ROUND6_REPORT.md` 待决 |
| C5 | `DATA_MANIFEST.json:217-218` | 新增 `window_rule` 后,旧键 `truncate_to_model_tokens: 256` 仍保留,键名仍是“截到” | R6-CR:28 | 数值相同;data-auditor 的 `r5_l6.py` 读这个键,改名会使它失效 |
| C6 | 加了 `run_guarded` 的 12 个文件 | 函数复制了 12 份(同 E11);函数内 `import sys` 与模块顶部重复;`sys.exit(False)` 会被当作失败 | R6-CR:29 | 现有脚本都不用 bool 退出码(审查已 grep);偏安全 |
| C7 | `reports/round6/guard_ab.sh:6-8`;`round5/records_check.py:57-59` | `blind_handback_check.py`、`records_check.py` 的正常路径没有 A/B;`records_check.py` 把顶层代码移进了 `main()` | R6-CR:30 | 输入不在本容器;审查读下来语义相同 |
| C8 | `reports/round6/t1_protocol_checks.txt:1-4` | 表格与 JSON 检查在 `481a6f0f` 之前对工作区运行,`599230f9` 填入第 14 节后没有重跑 | R6-CR:31 | 已在报告提交中补跑:`round6/t1_protocol_checks_599230f9.txt`,表格 145 行 PASS,JSON 可解析,内联副本相同,占位符 0 |
| C9 | 协议第 204 行 | 归一化先“取第一行”再“去首尾空白”,以换行开头的输出 EM 为 0;“取第一行”没写用 `split("\n")` 还是 `splitlines()` | R6-CR:32 | EM 只报告,不进门槛;顺序是 1d 之前就有的写法 |
| C10 | `reports/round5/l6_check.py:36-39、128-129` | 25、256、13、4 个 domain 写死(同 E8);锚文本只打印 canonical hash,不与锁定值核对 | R6-CR:33 | `anchor_text.jsonl` 还是 `NOT_GENERATED`,没有可核对的锁定值;锚文本哈希与第 5 轮相同(`round6/t2_l6_check.txt`) |

### 1.5 第 6 轮 data-auditor 的非 BLOCK 观察(`reviews/599230f9…/data-auditor.md` 第 E 项“以下观察不构成 BLOCK”)

| # | 位置 | 问题 | 来源 | 不修的理由 |
|---|---|---|---|---|
| D1 | `round2/y_ratio.py`、`round3/candidate_feasibility_r3.py`、`round3/verify_scoring.py` | 在模块顶层导入同目录的 `names` / `scoring_input`,位置在 `run_guarded` 之外;导入失败时只有 traceback 和退出码 1,没有 `RESULT: FAIL` | R6-DA E (b) | 字面上属于第 2 项“遇异常”的范围,但只有同目录文件缺失时才会发生;auditor 评为风险低。修要再改三个旧脚本并重新审查,按总原则登记 |
| D2 | `round2/anchor_check.py`、`round5/blind_handback_check.py`、`round5/records_check.py`、`round5/recover_blind.py` | 检查不通过(不是异常)时以 1 退出,但没有 `RESULT` 行,判定只在文字或计数里 | R6-DA E (a) 前半 | 原有行为;第 2 项只管异常。与 `template_overlap.py`、`y_ratio.py` 不通过时仍以 0 退出(R6-CR:20 MAJOR)一并列入 `ROUND6_REPORT.md` 待决 |

### 1.6 第 6 轮修复提交 `2620f306` 的两份审查(`reviews/2620f306…/`,code-reviewer 记 `R6b-CR`)

| # | 位置 | 问题 | 来源 | 不修的理由 |
|---|---|---|---|---|
| H1 | `round6/guard_ab.sh`、`guard_fail.sh` | 头注释说“出错由 EXIT trap 打印 RESULT: FAIL”,但两个脚本没有 `set -e`。trap 只覆盖显式 exit(参数个数)、`set -u` 未定义变量与致命信号。影响判定的命令出错,在正常结尾判 FAIL;只用于展示的命令(`wc`、`sha256sum`、`cat`)出错,判定不受影响,可能仍输出 `RESULT: PASS` | R6b-CR MAJOR 1 | 这是注释不准与展示命令的失败,不影响判定,也不影响数据和指标。审查给 PASS,并说按现有代码几乎不会发生(文件刚被 `cmp`/`grep` 读过)。改注释需要再一轮提交与审查,按总原则登记;是否修交 Review Gate(`ROUND6_REPORT.md` 待决) |
| H2 | 同上;`t2_guard_normal_rerun.txt` 等 | harness 自己的 RESULT 行紧跟在转印的子脚本输出之后,只能靠“最后一行”区分;RESULT 只表示“新旧相同 / 失败用例表现正确”,不表示子检查都通过 | R6b-CR MINOR 1 | 输出格式;判定本身正确 |
| H3 | `round6/guard_ab.sh:37、39` | `guard_ab.sh` 没有测解释器缺失;那种情况下不出假 PASS 靠的是两次 bash 报错里行号不同 | R6b-CR MINOR 2 | 只影响这个对照脚本在异常输入下的报告方式,不影响被对照的检查脚本 |
| H4 | `round6/guard_ab.sh:14`;`guard_fail.sh:11、49` | `on_exit` 里的 `rc` 不是局部变量,与 `guard_fail.sh` 第 49 行同名;两个脚本的 `on_exit` 与结尾 4 行逐字重复 | R6b-CR MINOR 3 | 只在退出时覆盖,无害 |
| H5 | `round6/guard_ab.sh` | “identical”不检查脚本是否真的运行过:PY 指向忽略参数、输出相同的程序(如 `/bin/true`),或 OLD 与 NEW 是同一目录时,也会得 8/8、`RESULT: PASS` | 第 2 轮 data-auditor 观察 (a)(`reviews/2620f306…/data-auditor.md`) | 原有代码;本轮记录的运行中每个 case 都有非空输出、退出码 0,证据不受影响 |

### 1.7 第 6 轮待决第 6、14 项(第 7 轮指令第 3 项:登记入本文件)

**注:正式流程代码统一要求不通过时打印 RESULT 并以非 0 退出。**(第 7 轮指令第 3 项原文。本节各条都是协议撰写阶段的检查脚本与对照脚本,登记,不修。)

`R6-CR:n` = `reviews/599230f9…/code-reviewer.md` 第 n 行;`R6-DA:n` = 同目录 `data-auditor.md` 第 n 行;`R6b-CR` = `reviews/2620f306…/code-reviewer.md`。

| # | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|
| G1 | `reports/round1/template_overlap.py`、`reports/round2/y_ratio.py` | 检查不通过(L1/L2 FAIL、Y/F 比 OUTSIDE)时仍以 0 退出,也不打印 RESULT 行;只有异常时打印 `RESULT: FAIL` | 第 6 轮待决第 6 项第 1 点;R6-CR:20;R6-DA:198 | 登记,不修 |
| G2 | `reports/round2/anchor_check.py`、`reports/round5/blind_handback_check.py`、`reports/round5/records_check.py`、`reports/round5/recover_blind.py` | 检查不通过时以 1 退出,但没有 RESULT 行(同 D2) | 第 6 轮待决第 6 项第 1 点;R6-DA:197 | 登记,不修 |
| G3 | 第 6 轮排除在“检查脚本”之外的 7 个脚本,其中 `reports/round4/anchor_short_docs.py`、`reports/round5/em_special_tokens.py` 的输出是协议第 14 节 v1-r5 引用的证据 | 是否也算检查脚本;它们出异常时以 1 退出、打印 traceback,但没有 `RESULT: FAIL` | 第 6 轮待决第 6 项第 2 点;R6-CR:21;R6-DA:201 | 登记,不修 |
| G4 | data-auditor 已入库的旧脚本(第 6 轮 `audit/stdout/599230f9…/06–09` 用到的,以及 `audit/r5_sources.py`) | 是否在第 6 轮第 2 项“所有检查脚本遇异常须打印 RESULT: FAIL”的范围内;`r5_sources.py` 用 `except Exception` 吞掉异常后以 0 退出(同 A4、A6) | 第 6 轮待决第 6 项第 3 点;R6-DA:214;R5-RC:27 (3) | 登记,不修(Executor 不改 auditor 的文件) |
| G5 | `reports/round6/guard_ab.sh`、`reports/round6/guard_fail.sh` | 头注释说“出错由 EXIT trap 打印 RESULT: FAIL”,但没有 `set -e`;只用于展示的命令出错时判定不受影响,可能仍输出 `RESULT: PASS`(同 H1) | 第 6 轮待决第 14 项;R6b-CR MAJOR 1 | 登记,不修 |

### 1.8 第 7 轮审查新提出的 MAJOR / MINOR(第 7 轮指令第 4 项:登记入本文件,不修)

`R7-CR:n` = `reviews/293b806d…/code-reviewer.md` 第 n 行;`R7-DA:n` = 同目录 `data-auditor.md` 第 n 行;`R7-RC:n` = 同目录 `code-reviewer_report-commit.md` 第 n 行。第 7 轮 code-reviewer 结论 PASS,没有 BLOCKER。4 条 MAJOR 都要由 Review Gate 确认或改协议、改 `metrix/CLAUDE.md`,一并列入 `ROUND7_REPORT.md`“待 Review Gate 决定”。

| # | 严重度 | 位置 | 问题 | 来源 |
|---|---|---|---|---|
| R1 | MAJOR | `reports/round7/gen_s_cands.py:137`;协议第 2.5 节 | 指令 1g 写“用 DATA_SEED 两次独立生成 train_S.jsonl 与 candidates.json”,实现按协议第 2.5 节用 `CANDIDATE_SEED` 抽候选,`DATA_SEED` 只决定 fact;冻结哈希 `e5d15c99…` 取决于这一读法 | R7-CR:30 |
| R2 | MAJOR | 协议第 2.5、2.6 节;`DATA_MANIFEST.json: s_permutation.record`;`SPLIT_MANIFEST.json: candidates.file` | `train_S.jsonl` 的记录格式 `{fact_id, answer_fact_id, text}` 与 `candidates.json` 的对象格式由 Executor 自定;两个冻结哈希都依赖它们。另问 `train_F`、`train_Y` 是否采用一致的字段 | R7-CR:31 |
| R3 | MAJOR | 协议第 3 节 L6;`SPLIT_MANIFEST.json: L6_general_text.test_part.count` | 计数口径加了指令没有的限定“13-gram 在每篇锚文档、每个窗口之内取”;“跨全部文档”也可读成 n-gram 可以跨篇 | R7-CR:32 |
| R4 | MAJOR | `metrix/CLAUDE.md` 第 5 节第 6 条、第 10 节(对照第 8 节) | 第 8 节写“只有「永久」的裁决可写入本文件”,本轮按指令写入了两条“本阶段”的裁决,文件内部矛盾 | R7-CR:33 |
| R5 | MINOR | `metrix/CLAUDE.md` 第 10 节末行 | 同一行两个出处(第 5 轮、第 6 轮);时间取 `7fea9181` 的提交时间,第 6 轮待决第 7 项提议的是 `481a6f0f` 的时间 | R7-CR:34 |
| R6 | MINOR | `metrix/CLAUDE.md` 第 5 节第 6 条 | 超出指令原文加了“调用前比对仓库文件与已加载定义的 frontmatter”;比对整个 frontmatter,停下条件只看 tools 行;Executor 读不到实际加载的定义,只能比对用户级副本 | R7-CR:35 |
| R7 | MINOR | `reports/DEFERRED_MINORS.md` | 超出第 3 项的编辑(第 3 节两项移到第 2 节);引言引用的 1.8 节当时还不存在;“截至第 6 轮”没更新;G4 在 1.7 节与第 3 节状态不一 | R7-CR:36 |
| R8 | MINOR | `reports/DEFERRED_MINORS.md` 1.7 节 G3 | “7 个脚本”只点名 2 个,没有列全;`candidate_feasibility.py` 不在其中 | R7-CR:37 |
| R9 | MINOR | `reports/round7/gen_s_cands.py:156-158` | “self-checks: …”是固定字符串,不论结果都打印;脚本不与 manifest 中的预期哈希比对 | R7-CR:38 |
| R10 | MINOR | `reports/round7/gen_s_cands.py:46-65` | 按 facts 列表顺序取 i,没有按 fact_id 序号排序,也不断言每个 cell 恰好 15 条(顺序由 `406c8801…` 锁定,第 131 行先核对了哈希) | R7-CR:39 |
| R11 | MINOR | `reports/round7/t1_protocol_checks.txt`;`t1g_gen_s_cands.txt` | 记录的是提交前工作区中 `gen_s_cands.py` 的 sha256,manifest 改完后的 gen3 运行没有记录脚本 sha256。报告提交补了一条记录:`7fea9181` 中的该脚本 sha256 `31a28ccd…`,与工作区版本相同(`round7/t5_freeze_hashes.txt` 末条;data-auditor 14 号运行第 12 行为 `293b806d` 中的同一值) | R7-CR:40 |
| R12 | MINOR | 协议第 3 节 L6、第 8 节第 8 步 | “结果须一致”没有规定不一致时怎么办 | R7-CR:41 |
| R13 | MINOR | 协议第 3 节 L6;`DATA_MANIFEST.json: files.general_test.jsonl` | 没有写明计算词 13-gram 用的窗口文本(≤256 个 id 解码后的文本,还是截断前的全文);`general_test.jsonl` 的字段也没有定义 | R7-CR:42 |
| R14 | MINOR | 协议第 8 节 G0.1 | 新措辞字面上也覆盖 L1、L2 中涉及 TEST 模板的部分,第 8 步与 ST10 只列 L3–L6;L1、L2 已在撰写时计算,实际没有影响 | R7-CR:43 |
| R15 | MINOR | 协议第 4 节 n_x 对照第 5 节 n_w、第 2.2 节 | n_w 写明“截断后的原始 id,不解码再编码”,n_x 仍只写“实际送入模型的 id 序列长度” | R7-CR:44 |
| R16 | MINOR | `DATA_MANIFEST.json: anchor_text` | 新增 `document_rule` 后,旧键 `truncate_to_model_tokens: 128` 仍保留(同 C5) | R7-CR:45 |
| R17 | MINOR | `SPLIT_MANIFEST.json: test_split`;协议 ST10 | L3a、L3b 的规则本身没有 TEST 部分,`test_split` 与 ST10 仍写“L3–L6”;原有措辞,ST10 沿用指令原文 | R7-CR:46 |
| R18 | MINOR | 协议第 5 节 EM(1f) | 先删除 `<think>…</think>` 再“取第一行”时,`" <think>\n\n</think>\n\nKishan."` 归一化后为空串(Qwen3 在 `enable_thinking=False` 时生成提示正以 `<think>\n\n</think>\n\n` 结尾);未闭合的 `<think>`(如被 16 token 上限截断)与单独的 `</think>` 怎么处理没有规定。EM 只报告,不进门槛 | R7-DA:149 |
| R19 | MINOR | 协议第 8 节 G0.1(1d) | 同 R14 | R7-DA:153 |
| R20 | MINOR | 协议第 4 节 n_x;`DATA_MANIFEST.json: anchor_text.document_rule`(1e) | 同 R15;现有数据上两种 id 512/512 相同 | R7-DA:157 |
| R21 | MINOR | 协议第 0 节;两个 manifest(1g) | 第 0 节没有固定 Python 版本,两个哈希依赖 CPython `random.Random` 的算法(实测 3.11、3.12、3.13 相同);`files.train_S.jsonl`、`files.candidates.json`、`split_sha256.train_S.jsonl` 仍为 null,同一个值以后有两个位置,填入时须相同 | R7-DA:158 |
| R22 | 流程观察 | `metrix/CLAUDE.md` 第 8 节;第 10 节的时间;本文件 1.8 节 | 同 R4、R5;另指出当时 1.8 节尚未建立(本节即是) | R7-DA:161 |

data-auditor 结论 PASS(按 `metrix/CLAUDE.md` 第 10 节仅作参考),新提的 5 条都标为 MINOR 或流程观察。

报告提交在提交前由 code-reviewer 审查(`reviews/293b806d…/code-reviewer_report-commit.md`),结论 PASS,没有 BLOCKER。它指出的是报告与本文件自身的错误。按第 5 轮先例(第 2 节“第 5 轮报告中 MINOR 条数、行号、转述等措辞问题 | 第 5 轮报告提交中已改”),能在报告提交中改正的已改正;其余登记。被审查版本与提交版本的差异:`reviews/293b806d…/report_commit_post_review.diff`。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| RC1 | MAJOR | `ROUND7_REPORT.md` 4 处 | 第 0 步证据提交写成 `fe321cd8`,该提交不存在;实为 `fe321cd9b5b4107bf8ee6d5caab2b56f67c0ee78` | R7-RC:51 | 报告提交中已改 |
| RC2 | MAJOR | `ROUND7_REPORT.md` 冻结哈希一节 | 协议、三个 JSON 与 `metrix/CLAUDE.md` 的哈希是冻结前 `293b806d` 的值,冻结改状态后会变 | R7-RC:52 | 报告中注明;列入待决第 12 项 |
| RC3 | MINOR | 同上 | 锚文本 `8828bc4f…` 与 Qwen 6 个文件的 sha256 不在任何会冻结的文件里;`8828bc4f…` 与将来 `anchor_text.jsonl` 的 canonical 口径不同 | R7-RC:53 | 报告中注明;列入待决第 12 项 |
| RC4 | MINOR | `ROUND7_REPORT.md`;本文件 R11 | R11 已在报告提交中部分处理,R11 一行没有注明;报告只写了 `7fea9181` 中脚本的哈希 | R7-RC:54 | 已在 R11 一行注明;报告补写 `293b806d` 中的同一值 |
| RC5 | MINOR | `ROUND7_REPORT.md` 第 0 步 | 推送范围 `49471e8..fe321cd` 只适用于 `metrix-e1-pilot-protocol-v1`,会话分支是 `155430a` → `fe321cd9`;推送输出未入库 | R7-RC:55 | 报告中已分开写,注明以 reflog 为据 |
| RC6 | MINOR | `ROUND7_REPORT.md` 第 0 步 | 用户级 CLAUDE.md 副本对应 `8ce8c896` / `7e5dd9c0` 的依据在 `round6/t4_user_claude_md.txt`,不在 `t0_copy_check.txt` | R7-RC:56 | 报告中已补引用 |
| RC7 | MINOR | `ROUND7_REPORT.md` 附 | `eval_sets.jsonl` 求整文件哈希的出处漏了 `t5_freeze_hashes.txt` | R7-RC:57 | 报告中已补 |
| RC8 | MINOR | `ROUND7_REPORT.md` 任务 2、待决第 11 项;`preflight_tools_check_report-commit.txt` | 会话重启后 code-reviewer 已加载新定义,报告仍说用的是旧定义;此时 preflight 比对的 `/root` 副本已不是实际加载的定义(三方 tools 行相同) | R7-RC:58 | 报告中已注明(依据是审查方自己的陈述) |
| RC9 | MINOR | `ROUND7_REPORT.md` 提交表 | 引用的 `code-reviewer_report-commit.md` 当时还不存在;报告提交审查的调用文字、preflight 与输入文件未暂存(同 P3) | R7-RC:59 | 已一并暂存提交;审查输入不含审查文件自身,同 P3 |
| RC10 | MINOR | 本文件 1.8 节 | `R7-DA` 记法在表格之后才定义;1.8 节没有“不修的理由”一栏 | R7-RC:60 | 记法已移到表格之前;栏目未加,登记 |

### 1.9 第 8 轮审查新提出的 MAJOR / MINOR(第 8 轮指令第 4 项:只登记不修)

`R8-CR:n` = `reviews/92df1a60…/code-reviewer.md` 第 n 行;`R8-DA:n` = 同目录 `data-auditor.md` 第 n 行。第 8 轮对冻结提交的两份审查:code-reviewer PASS(2 MAJOR、9 MINOR),data-auditor PASS(仅作参考;3 MINOR,其中 1 条与 code-reviewer 的 S11 相同),都没有 BLOCKER。`92df1a60` 是冻结提交的候选,之后被冻结提交 `6a474e4a` 取代(补充 a–e 改动了协议);冻结之后协议不再改动,下列各项都不在本轮修;需要改协议或改 `metrix/CLAUDE.md` 的,列入 `ROUND8_REPORT.md`“待 Review Gate 决定”。

| # | 严重度 | 位置 | 问题 | 来源 |
|---|---|---|---|---|
| S1 | MAJOR | `metrix/CLAUDE.md` 第 8 节(第 62 行) | 1e 写入的规则要求“写入时须注明作用范围”,这条裁决自己的括注没有作用范围;指令 1e 没有给出,Executor 没有自定 | R8-CR:71 |
| S2 | MAJOR | 协议第 2.8 节(对照第 7 节“最终冻结”、第 8 节第 8 步、`DATA_MANIFEST.json: files.test_qa.jsonl.generation_allowed`;`metrix/CLAUDE.md` 第 3 节) | 第 2.8 节“冻结之后才允许生成 `test_qa.jsonl`、`general_test.jsonl`”的“冻结”没有限定,状态改为 PROTOCOL_FROZEN 后可能被读成协议冻结即可生成 TEST;`metrix/CLAUDE.md` 第 3 节的硬性禁止以“收到 PROTOCOL_FROZEN 之前”为限 | R8-CR:73 |
| S3 | MINOR | `metrix/CLAUDE.md` 第 2 节 | 仍写“E1 Pilot,状态:AWAITING_REVIEW_GATE”,与冻结后的协议不一致;改动须经 Review Gate 裁决 | R8-CR:75 |
| S4 | MINOR | `DATA_MANIFEST.json: model.tokenizer.files_sha256` | 1d 把“分词器全部文件”读成 4 个文件;第 7 轮报告列的是 Qwen 6 个文件,`config.json`、`generation_config.json` 的 sha256 仍只在报告与原始输出中 | R8-CR:77 |
| S5 | MINOR | `SPLIT_MANIFEST.json: L6_general_text.test_part.text`;协议第 3 节 L6 | L6 TEST 的文本规则没有写解码参数;tokenizers 库版本没有在第 0 节固定;两方须一致,口径不全可能导致不一致而 BLOCKED | R8-CR:79 |
| S6 | MINOR | 协议第 5 节 EM;`DATA_MANIFEST.json: em_generation` | 1c 只解决待决第 6 项第 1 点:未闭合的 `<think>`、单独的 `</think>`、“第一行”的切分方式、结尾标点去一个还是全部,仍未规定;“空白(含空格与换行)”与 “(spaces and newlines)” 措辞范围不完全相同 | R8-CR:81 |
| S7 | MINOR | `DATA_MANIFEST.json: files` | `facts`、`train_F`、`train_Y`、`dev_qa`、`general_dev`、`anchor_text.jsonl` 的记录字段仍未定义;`anchor_text.jsonl` 的 `canonical_sha256` 与 `decoded_texts_canonical_sha256` 的关系没有写明 | R8-CR:83 |
| S8 | MINOR | 协议文件头状态行;第 14 节 v1-r8 | 引用的 `PROTOCOL_FROZEN` 文件与标签在冻结提交中尚不存在;v1-r8 各行不满足表头“哈希为包含该改动的提交”(已注明原因);1a 一行写“Review Gate 第 7 轮裁决,第 8 轮指令第 1a 项”,1b–1e 只写“第 8 轮指令第 1x 项”,写法不统一 | R8-CR:85 |
| S9 | MINOR | 两个 manifest 的 `files.*`、`split_sha256` | 第 8 节第 1 步还要往两个 manifest 填哈希,`PROTOCOL_FROZEN` 中钉住的 manifest sha256 之后必然对不上;协议没有写明冻结后允许改哪些 manifest 字段 | R8-CR:87 |
| S10 | MINOR | `DATA_MANIFEST.json: model.tokenizer.files_sha256`;协议第 0 节 | 分词器文件 sha256 不符时怎么处理(是否 BLOCKED)没有规则;库版本一行写了“不一致即 BLOCKED” | R8-CR:89 |
| S11 | MINOR | `reports/round8/t1_protocol_checks.txt`(以及 `reviews/92df1a60…/review_input.diff`) | `cut -c1-200`、`cut -c1-120` 按字节截断,切断了多字节 UTF-8 字符,两个文件不是合法 UTF-8 | R8-CR:91;R8-DA:161(`audit/stdout/92df1a60…/12_r8_utf8_check.txt`:8 行) |
| S12 | MINOR | 协议第 3 节“模板冻结”;`SPLIT_MANIFEST.json: template_freeze.normalization` | 归一化规则的文字只写“合并空格”,没写去掉首尾空格;32 个冻结的 `normalized_sha256` 都要求去掉首尾空格(不去时 0/32 相同,`audit/stdout/92df1a60…/06_r8_templates.txt`)。冻结值本身消除了歧义 | R8-DA:159 |
| S13 | MINOR | `reports/round8/t1d_data_hashes.txt`;`reports/round7/t1g_gen_s_cands.txt` | 两次独立运行写成 `env PYTHONHASHSEED=n python -I …`,但 `-I` 忽略 `PYTHONHASHSEED`(`audit/stdout/92df1a60…/11_r8_hashseed_probe.txt`);脚本打印的 `PYTHONHASHSEED=0/31337` 是它读到的环境变量,不是解释器实际使用的 hash seed。两次运行实际是两个随机 hash seed,“两次逐字节相同”的结论不受影响 | R8-DA:160 |

### 1.10 第 8 轮:被取代的 `PROTOCOL_FROZEN` 草稿的提交前审查(`reviews/92df1a60…/code-reviewer_frozen-file.md`,记 `R8-FF:n`)

这份草稿是为冻结提交的候选 `92df1a60` 写的,审查结论 PASS、无 BLOCKER;审查进行中 Owner 下达补充,`92df1a60` 被取代,草稿没有提交。为新冻结提交重写 `PROTOCOL_FROZEN` 时,下表“处理”一栏写明新文件中的做法;其余只登记。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| F1 | MINOR | 草稿第 12、18 行 | 写成标签已存在,审查时还不存在;核对没有覆盖标签 | R8-FF:36 | 报告附 `git rev-parse metrix-e1-pilot-frozen^{commit}` 与 `git ls-remote --tags` 的原始输出 |
| F2 | MINOR | 草稿第 54 行 | “48 个值三方相同”说多了:4 个文件哈希只有两方;32 个模板值 Executor 侧只有“无不复现”;没提首次比对 09 失败 | R8-FF:38 | 新文件按实际情况写 |
| F3 | MINOR | 草稿第 54 行;`t5_frozen_hashes.txt` 第 2 行 | 模板集合哈希的 Executor 重算在 `t1_protocol_checks.txt`,引用漏了 | R8-FF:40 | 新文件与 `t5_frozen_hashes_6a474e4a.txt` 已补 |
| F4 | MINOR | `t5_protocol_frozen_check.txt` | 只判断值“在文件中出现”,不核对标签与值的对应 | R8-FF:42 | 新文件的核对改为按“标签 + 值”逐行比对 |
| F5 | MINOR | `t5_protocol_frozen_check.txt` | 第一次 `git archive` 解包是死步骤;说明行写在输出中途 | R8-FF:44 | 登记(旧文件保留原样) |
| F6 | MINOR | 草稿第 46 行 | 没提 `SPLIT_MANIFEST.json: split_sha256`;没说第 1 步生成的 facts、train_S、candidates 的哈希必须等于表中期望值 | R8-FF:46 | 新文件已写 |
| F7 | MINOR | 草稿第 18 行 | `sha256sum -c` 默认检出时不做换行转换 | R8-FF:48 | 新文件注明以 `git cat-file blob` 为准 |
| F8 | MINOR | 草稿第 14、18、44、52–54 行 | 路径基准不统一 | R8-FF:50 | 部分处理:新文件声明路径相对仓库根目录,多数引用已写全路径,但“依据”一节仍有只写文件名的引用,见 1.12 节 U4 |
| F9 | MINOR | 草稿第 27–44 行 | “全部数据哈希”的范围由 Executor 按 manifest 读法确定;Qwen `config.json`、`generation_config.json` 不在内(同 S4) | R8-FF:52 | 登记 |
| F10 | MINOR | 草稿第 48 行 | 没有明说本文件不是协议第 8 节第 8 步的“冻结记录” | R8-FF:54 | 新文件已写 |
| F11 | MINOR | `reviews/92df1a60…/` | 审查自身的输入文件与审查原文没有暂存;`DEFERRED_MINORS.md` 放在哪个提交没说明 | R8-FF:56 | 都随报告提交入库;`DEFERRED_MINORS.md` 在报告提交中 |

### 1.11 第 8 轮:对冻结提交 `6a474e4a` 的 code-reviewer 审查新提出的项(`reviews/6a474e4a…/code-reviewer.md`,记 `R8c-CR:n`)

结论 PASS,没有 BLOCKER。沿用的两条 MAJOR 即 1.9 节 S1(第 85 行)与 S2(第 87 行,扩展到 ST13 的“配置冻结”);沿用的 MINOR 即 1.9 节 S3–S8、S10(第 101 行);1.9 节 S9 并入下表 T1,S11 已在冻结提交中重跑的 `t1_protocol_checks.txt` 解决(第 101 行)。以下为新项,只登记不修;须改协议或 `metrix/CLAUDE.md` 的列入 `ROUND8_REPORT.md`“待 Review Gate 决定”。

| # | 严重度 | 位置 | 问题 | 来源 |
|---|---|---|---|---|
| T1 | MAJOR | 协议第 11 节 ST12(对照第 8 节第 1 步) | ST12 与第 1 步冲突:第 1 步把数据哈希写入两个 manifest 并提交,manifest 的 sha256 必然改变;数据文件的“冻结值”在冻结时是 null;“冻结值”指什么没有定义。照字面 ST12 会在第 1 步触发 BLOCKED。Owner 已知悉并选择照字面写,所以不列 BLOCKER;须在第 1 步(以及租卡)之前裁决 | R8c-CR:77 |
| T2 | MAJOR | 协议第 8 节 G0.8 | 适用范围没有定义:哪个 checkpoint、几个、覆盖哪些评测;原有的 3 个 checkpoint 与 NLL ≤ 1e-5 被删除;范围不定可在看到结果后再选 checkpoint | R8c-CR:79 |
| T3 | MAJOR | 协议第 8 节第 2 步、ST11;`metrix/CLAUDE.md` 第 4 节 | ST11 是 3.5 小时,`metrix/CLAUDE.md` 第 4 节是 3 小时;两者同时生效时 (3, 3.5] 这一段 ST11 不起作用 | R8c-CR:81 |
| T4 | MAJOR | 分支 reflog | 为把补充放进冻结提交,在本地 reset 未推送的 `92df1a60` 后重新提交,属于改写本地分支历史(`metrix/CLAUDE.md` 第 1、7 节);请在决定记录中确认;`92df1a60` 的审查与审计原始输出须随报告提交入库 | R8c-CR:83 |
| T5 | MINOR | 协议第 8 节 G0.10 | σ_d 的 bootstrap 次数、是否分 stratum、随机数 purpose、标准差自由度未写;“以最大者”是否跨 δ、跨 Δ(L−F)/Δ(A−F) 有歧义(跨 δ 恒为 δ=0.05);不影响 G0.10 是否通过 | R8c-CR:89 |
| T6 | MINOR | 协议第 8 节第 2 步、第 9 节、ST9;`SEARCH_SPACE.json` | “第一个配置”是否即 F1、种子 101;20 步之后丢弃还是计入 F1;“预估总时长”的算法;ST11 在第 9 节没有对应状态;ST9“从第 3 步重新开始”会跳过预检;`SEARCH_SPACE.json` 的 hardware.rule 与 counts 不含预检 | R8c-CR:91 |
| T7 | MINOR | 协议第 8 节 G0.8;第 10 节 | G0.8 要求确定性设置“并记录”,实验记录模板没有对应字段 | R8c-CR:93 |
| T8 | MINOR | 未跟踪的 `PROTOCOL_FROZEN` 草稿 | 仍写着被取代的 `92df1a60` 及其 sha256;须按 `6a474e4a` 重新生成并重新审查 | R8c-CR:95 |
| T9 | MINOR | `reports/round8/t1_protocol_checks.txt` | 提交前删去了第一次按字节 locale 运行的 grep 输出(文件中写明);与“原始输出不编辑”的做法不一致;以后保留失败的运行,另起一次附在后面 | R8c-CR:97 |
| T10 | MINOR | 协议第 2.5 节;`SPLIT_MANIFEST.json: candidates.pool_too_small` | 每条 fact 只抽 3 个干扰项,门槛是池 ≥ 4;`DATA_SEED` 下 unread 的池正好是 4,处在门槛上 | R8c-CR:99 |

### 1.12 第 8 轮:第 5 项提交前审查(`PROTOCOL_FROZEN`,提交 `5c8a9657`;`reviews/6a474e4a…/code-reviewer_frozen-file.md`,记 `R8d-FF:n`)

结论 PASS,没有 BLOCKER。只登记不修;须由 Review Gate 决定的列入 `ROUND8_REPORT.md`“待 Review Gate 决定”。

| # | 严重度 | 位置 | 问题 | 来源 |
|---|---|---|---|---|
| U1 | MAJOR | `PROTOCOL_FROZEN` 第 35、39 行;协议第 2.2、2.8 节 | fact 哈希 `406c8801…` 是 160 条 fact 组成的 JSON 列表的规范化哈希;第 1 步生成的是 `facts.jsonl`,按第 0 节的 JSONL 规则其 `canonical_sha256` 是另一串字节的哈希。若拿 `facts.jsonl` 的 `canonical_sha256` 去比 `406c8801…`,ST12 会在第 1 步误判 BLOCKED;协议第 2.2 节也没写明口径 | R8d-FF:80 |
| U2 | MINOR | `PROTOCOL_FROZEN` 第 52 行 | “`files` …`split_sha256` …按第 1 步生成后填写”字面上包括 TEST 的两个文件与 `split_sha256.test_qa.jsonl`,它们在第 8 步才填;同文件第 56 行已说明不授权 TEST | R8d-FF:82 |
| U3 | MINOR | `PROTOCOL_FROZEN` 第 31 行 | 引用的 `ROUND8_REPORT.md` 在第 5 项提交中尚不存在,到报告提交才有 | R8d-FF:84 |
| U4 | MINOR | `PROTOCOL_FROZEN` 第 5、41、61–63 行 | F8 只做了一部分:说“路径都相对仓库根目录”,但依据一节有几处只写了文件名;`data/sample-100BT/…` 是 HF 数据集内的路径 | R8d-FF:86 |
| U5 | MINOR | `reports/round8/t5_protocol_frozen_check_6a474e4a.txt` | `RESULT` 不含冻结 hash、提交时间、父提交、批准字样四项;提交时间用写死的字符串匹配。四项实际都为 True | R8d-FF:88 |
| U6 | MINOR | 同上 | 检查的是工作区文件,没有记录 blob id,无法与暂存的 blob 对应。提交后已补记 `5c8a9657` 中该文件的 blob id 与 sha256(`299f4fcf…`,与检查时相同;`round8/t5_tag_push.txt` 末段) | R8d-FF:90 |
| U7 | MINOR | `reports/round8/t5_frozen_hashes_6a474e4a.txt` | `git diff --stat` 不带 `--exit-code` 时退出码恒为 0,打印的 `$?` 不含信息 | R8d-FF:92 |
| U8 | MINOR | `PROTOCOL_FROZEN` 第 3、16 行 | 批准时间 05:27 早于补充 a–e(约 05:55),文件头可能被读成全部内容都在 05:27 获批 | R8d-FF:94 |
| U9 | MINOR | `reviews/6a474e4a…/` 等 | 本次审查的输入文件与原文、`92df1a60` 的记录、`DEFERRED_MINORS.md` 当时不在暂存区(同 F11)。本次审查的输入与原文已在第 5 项提交中一并提交;其余随报告提交入库 | R8d-FF:96 |
| U10 | MINOR | `PROTOCOL_FROZEN` 第 14 行 | 审查时标签还不存在(同 F1)。标签已在本地创建,推送被拒,见 `ROUND8_REPORT.md` 第 5 项 | R8d-FF:98 |

### 1.13 第 8 轮:报告提交的提交前审查(`reviews/6a474e4a…/code-reviewer_report-commit.md`,记 `R8e-RC:n`)

结论 PASS,没有 BLOCKER。报告与本文件本身的事实错误按第 7 轮的先例在报告提交中改正(差异见 `reviews/6a474e4a…/report_commit_post_review.diff`);其余只登记。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| V1 | MAJOR | `ROUND8_REPORT.md` TEST 的条件、待决第 8 项;`.claude/agents/data-auditor.md` 第 12 行;`metrix/CLAUDE.md` 第 7 节 | `PROTOCOL_FROZEN` 入库后 data-auditor 定义中的 TEST 禁令失去作用;`metrix/CLAUDE.md` 第 7 节只管“生成或评测”,不管“读取或统计”;冻结后读取或统计 TEST 只受 ST13 约束,“配置冻结”没有定义 | R8e-RC:46 | 写入待决第 8 项;以后调用 data-auditor 时在调用文字中重申 TEST 禁令 |
| V2 | MINOR | `ROUND8_REPORT.md` 提交表“报告提交”一行 | 写成 1.9、1.10 节;文件列表不全 | R8e-RC:48 | 已改 |
| V3 | MINOR | `ROUND8_REPORT.md` “补充与冻结提交的重建” | 说 `audit/r8_*.py` 随报告提交入库,实际已在 `5c8a9657` 提交 | R8e-RC:50 | 已改 |
| V4 | MINOR | 本文件 1.10 节 F8;`ROUND8_REPORT.md` | F8 写成已全部处理,与 U4 矛盾 | R8e-RC:52 | 已改为部分处理 |
| V5 | MINOR | 本文件 1.9 节导语 | 把 `92df1a60` 称为冻结提交 | R8e-RC:54 | 已改 |
| V6 | MINOR | `ROUND8_REPORT.md` 第 5 项 | 第 5 项提交前审查的 9 条 MINOR 中 2 条沿用 F1、F11,报告没写 | R8e-RC:56 | 已改 |
| V7 | MINOR | `ROUND8_REPORT.md` 第 4 项 | data-auditor 的 venv 是沿用的,不是新的 | R8e-RC:58 | 已改 |
| V8 | MINOR | `ROUND8_REPORT.md` 第 4 项 | “6 条 MAJOR 都不是执行偏差”包括 T4,等于 Executor 审查自己的行为 | R8e-RC:60 | 已删去该断言,注明 T4 由 Review Gate 确认 |
| V9 | MINOR | `ROUND8_REPORT.md` 第 6 项、待决第 13 项 | 把推送到会话分支写成已发生;会话分支远端仍是 `155430a` | R8e-RC:62 | 第 6 项已改为计划写法;推送输出见最终回复 |
| V10 | MINOR | `ROUND8_REPORT.md` 结论一览第 5 项、提交表;`PROTOCOL_FROZEN` 第 14 行 | 第 5 项没有明确状态;标签没注明仅在本地;`PROTOCOL_FROZEN` 第 14 行“同时推送”已不成立 | R8e-RC:64 | 报告已改;`PROTOCOL_FROZEN` 是否修改由 Review Gate 决定(待决第 4 项) |
| V11 | MINOR | `ROUND8_REPORT.md` 第 5 项 | “这是会话环境的策略拒绝”是推断,原始输出中没有 `[agent-proxy]` 行 | R8e-RC:66 | 已改为“原因未确认”,推断单独注明 |
| V12 | MINOR | `ROUND8_REPORT.md` 提交表 | `5c8a9657` 的提交时间在仓库中没有原始输出 | R8e-RC:68 | 已补 `git log -1 --format='%H %cI %P'`(`round8/t5_tag_push.txt` 末条) |
| V13 | MINOR | `ROUND8_REPORT.md` 1b 一行 | 引号内的文字不是协议原文 | R8e-RC:70 | 已改为逐字引用 |
| V14 | MINOR | `ROUND8_REPORT.md` 第 6 项 | `code-reviewer_report-commit*` 的通配不含另两个文件;本审查原文提交前须暂存 | R8e-RC:72 | 已逐个列出;一并暂存 |

### 1.14 第 9 轮:对 v1.1 冻结提交 `87a244db` 的 code-reviewer 审查新提出的项(`reviews/87a244db…/code-reviewer.md`,记 `R9-CR:n`)

结论 PASS,没有 BLOCKER;13 项逐条“一致”。第 9 轮指令第 5 项:新的 MAJOR/MINOR 只登记不修。W1 同时列入 `ROUND9_REPORT.md`“待 Review Gate 决定”第 1 项(见 1.16 节 Y1);W2、W3、W4、W5、W8 列入第 2–4a 项(见 1.17 节 Z5、Z6)。

| # | 严重度 | 位置 | 问题 | 来源 |
|---|---|---|---|---|
| W1 | MAJOR(审查方注明不确定) | 协议第 11 节 ST12 | 比对范围 (1)“数据内容哈希”可被读成只含规范化(canonical)哈希;`PROTOCOL_FROZEN` 所列的锚文本源 parquet、Qwen 4 个分词器文件、parcae `tokenizer.json`、`eval_sets.jsonl` 是文件字节哈希,可能落在 ST12 之外;文字与指令原文一致 | R9-CR:42 |
| W2 | MINOR | 协议第 11 节 ST12 | 现有 v1、v1.1 两个冻结提交,(2) 中的“冻结提交”没有指明是哪一个 | R9-CR:44 |
| W3 | MINOR | 协议第 9 节 BLOCKED 一行 | 仍照搬 ST12 原来的条件文字,没有带上比对范围,只靠括注“(ST12)”间接受限 | R9-CR:46 |
| W4 | MINOR | 三个 JSON 的 `frozen`;协议第 7 节内联副本 | `version` 已是 v1.1,`frozen` 仍是 v1 的批准时间;与指令“版本字段同步”一致 | R9-CR:48 |
| W5 | MINOR | `.claude/agents/data-auditor.md` 第 12 行 | 新规则的“读取”“统计”没有引用协议第 3 节对“读取 TEST 数据”的定义(计数、对整个文件求哈希不算读取);对含 test 行的 `eval_sets.jsonl` 整个文件求哈希算不算“统计 TEST”不明;文字与指令逐字一致 | R9-CR:50 |
| W6 | MINOR | `reports/round9/v11_checks.py` 第 77–90 行 | 对 1a–1d 只检查以某前缀开头的行恰好 1 行,不比对内容;`RESULT: PASS` 不能证明内容与指令一致,内容靠打印出来人工比对 | R9-CR:52 |
| W7 | MINOR | `reports/round9/t3_data_auditor_frontmatter.txt` 第 34 行 | 注释说忽略规则使 `git add -f` 成为必需,但文件已被跟踪,暂存改动通常不需要 `-f`;原始输出没有记录实际执行的 `git add` 命令 | R9-CR:54 |
| W8 | MINOR | `metrix/CLAUDE.md` 第 4 节 | 第一条已写“上限 4 小时”,新句又写“累计 GPU 时间超过 4 小时即停(协议 ST7)”,重复;“即停”没有带上 ST7 的“报告进度”;符合 Owner“只换 3 小时那句”的回答 | R9-CR:56 |

### 1.15 第 9 轮:对 v1.1 冻结提交 `87a244db` 的 data-auditor 审计提出的项(`reviews/87a244db…/data-auditor.md`,记 `R9-DA:n`)

结论 PASS(按 `metrix/CLAUDE.md` 第 10 节仅作参考),没有 BLOCKER;45 个数据值与 v1 及本提交 manifest 相同,四个文件的新字节哈希与 Executor 一致。只登记不修。

| # | 严重度 | 位置 | 问题 | 来源 |
|---|---|---|---|---|
| X1 | MINOR | 三个 JSON 的 `frozen` | 同 1.14 节 W4:`version` 已是 v1.1,`frozen` 仍是 v1 的批准时间,只看 JSON 看不到 v1.1 的批准时间 | R9-DA:123 |
| X2 | MINOR | `reports/round9/t5_frozen_hashes_87a244db.txt` | 每个 revision 只列了 11 个数据值,缺锚文本源 parquet 的 sha256(`PROTOCOL_FROZEN` 表有 12 行);auditor 复算的该值与 `PROTOCOL_FROZEN` 和两个 manifest 相同,不影响结论 | R9-DA:124 |

### 1.16 第 9 轮:第 6 项提交前审查(`PROTOCOL_FROZEN`,提交 `892f26a4`;`reviews/87a244db…/code-reviewer_frozen-file.md`,记 `R9b-FF:n`)

结论 PASS,没有 BLOCKER,没有 MAJOR。审查因 HTTP 429 中断后续做完成。只登记;能在报告提交中处理的注明处理方式。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| Y1 | MINOR | `PROTOCOL_FROZEN` 第 37 行;本文件 1.14 节 W1、第 3 节 | `PROTOCOL_FROZEN` 写 W1“待 Review Gate 决定”,本文件中 W1 只在“登记不修”的 1.14 节,第 3 节写“目前没有其它开放项”,两处说法不一 | R9b-FF:57 | W1 列入 `ROUND9_REPORT.md`“待 Review Gate 决定”第 1 项;1.14 节导语注明 |
| Y2 | MINOR | `PROTOCOL_FROZEN` 第 21 行 | “仓库 / 分支”写 `metrix-e1-pilot-protocol-v1`,审查时 v1.1 冻结提交还不在该远端分支上(预先陈述;同第 8 轮 V10) | R9b-FF:59 | 推送的原始输出见最终回复;推送前的远端状态见 `round9/t7_commits_remote.txt` |
| Y3 | MINOR | `PROTOCOL_FROZEN` 第 5 行 | 自述“只改了其中标签一行,并把小节标题降一级”不完整:原标题变为 v1 小节标题、路径说明移到文件开头没有写 | R9b-FF:61 | 登记;`ROUND9_REPORT.md` 第 6 项列全了改动 |
| Y4 | MINOR | `reports/round9/protocol_frozen_check.py` 第 56 行 | 变量 `s1` 赋值后未使用 | R9b-FF:63 | 登记 |
| Y5 | MINOR | `reports/round9/protocol_frozen_check.py`、`v11_checks.py` | 没有异常保护,异常时不打印 `RESULT: FAIL`(第 6 轮第 2 项的要求;是否约束后续各轮的 Executor 脚本仓库中没有明文) | R9b-FF:65 | 登记 |
| Y6 | MINOR | `reports/round9/t6_protocol_frozen_check.txt` 第 39 行 | 第一次失败的原因说明在原始输出中没有依据;修正前的脚本没有保留 | R9b-FF:67 | `ROUND9_REPORT.md` 第 6 项写出脚本修改前后的行 |
| Y7 | MINOR | `reports/round9/protocol_frozen_check.py` 第 42 行 | 检查读工作区文件,没有原始输出证明与暂存 blob 相同 | R9b-FF:69 | 提交前补记:`reviews/87a244db…/extract_log.txt` 末段 `worktree == index`,`git hash-object` 与 `:PROTOCOL_FROZEN` 都是 `ae863e96…`,sha256 `3f8a3bba…` 与检查时相同 |
| Y8 | MINOR | `audit/r9_files.py` 第 18–21、176、183 行 | docstring 把 64 位十六进制值比对写成参考项,代码把它计入 `ok`;auditor 的文件,Executor 不改 | R9b-FF:71 | 登记,由 data-auditor 处理 |
| Y9 | MINOR | `reviews/87a244db…/` | 审查时 4 个审查记录文件不在暂存区 | R9b-FF:73 | 已与本审查原文一并在 `892f26a4` 中提交 |

### 1.17 第 9 轮:报告提交的提交前审查(`reviews/87a244db…/code-reviewer_report-commit.md`,记 `R9c-RC:n`)

结论 PASS,没有 BLOCKER,没有 MAJOR。报告与本文件本身的错误按第 7、8 轮的先例在报告提交中改正(被审查的版本与提交版本的差异见 `reviews/87a244db…/report_commit_post_review.diff`);其余只登记。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| Z1 | MINOR | `ROUND9_REPORT.md` 提交表 | 第 6 项提交前审查的记录写在“报告提交”一行,实际在 `892f26a4` 中(同第 8 轮 V3) | R9c-RC:46 | 已改 |
| Z2 | MINOR | `ROUND9_REPORT.md` 第 5 项 data-auditor 一段 | “45 个值五方相同”说多了:五方都有值的只有 12 个 | R9c-RC:48 | 已改 |
| Z3 | MINOR | `ROUND9_REPORT.md` 第 5 项“原文” | `dc138737…`、`9bfb5f7b…` 是 `message` 文本的 sha256,不是写入文件的 sha256 | R9c-RC:55 | 已改 |
| Z4 | MINOR | `ROUND9_REPORT.md` v1.1 冻结提交的哈希表 | 引言说 data-auditor 独立复算一致,但 `metrix/CLAUDE.md`、`data-auditor.md` 两行 auditor 没有复算;v1 列的出处是 `t0_copy_check.txt` | R9c-RC:57 | 已改 |
| Z5 | MINOR | `ROUND9_REPORT.md`“待 Review Gate 决定” | 漏了 W3、W8、Y5、Y8 | R9c-RC:59 | 已补为待决第 4a 项 |
| Z6 | MINOR | 本文件第 3 节;1.14 节导语 | Y1 只处理了一半:第 3 节仍写“没有其它开放项” | R9c-RC:67 | 第 3 节加一条,指向 `ROUND9_REPORT.md` 待决第 1–4a 项 |
| Z7 | MINOR | `ROUND9_REPORT.md` 结论一览第 7 项、待决第 7 项 | 推送写成已发生;“没有 force push”“停止钩子……”没有原始输出;推送输出只在最终回复,不进仓库 | R9c-RC:69 | 改为计划写法,注明没有原始输出;推送输出进不进仓库列入待决第 7 项 |
| Z8 | MINOR | `ROUND9_REPORT.md` 开头 | “没有……统计 TEST 数据”是无保留断言,与待决第 3 项矛盾 | R9c-RC:75 | 已加限定 |
| Z9 | MINOR | `ROUND9_REPORT.md` 第 6 项 | 引用了没有入库的 scratchpad 比对输出;修正前的脚本没有保留(并入 Y6) | R9c-RC:77 | 报告注明只有 Executor 的描述;以后检查失败时先保存脚本副本与比对输出 |
| Z10 | MINOR | `reviews/87a244db…/` | 本次审查的调用文字、输入、调用前检查不在暂存区 | R9c-RC:79 | 与本审查原文一并在报告提交中提交 |

### 1.18 Implementation 阶段 A:工作提交 `602a39e8` 第 1 轮审查(`reviews/602a39e8…/code-reviewer_round1.md` 记 `IA1-CR:n`,`data-auditor_round1.md` 记 `IA1-DA:n`)

code-reviewer 结论 PASS,没有 BLOCKER(2 MAJOR、12 行 MINOR);data-auditor 结论 PASS(仅作参考)。按 Implementation Task Order V1 第 9 节,影响协议一致性、数据、指标或隔离的已在工作提交中修,或属于协议未覆盖、需要解释的,不改代码,交 Review Gate(见 `IMPL_A_REPORT.md`“审查”“待 Review Gate 决定”);下表是没有修或只修了一部分的项。第 1 轮 (d)(e)(f) 三项的现状由第 2 轮原文给出,来源记为 `IA2-CR`。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| AA1 | MAJOR(审查方注明不确定) | `src/metrix_e1/frozen.py` `load()` | 工作区四个冻结文件与冻结提交的比对超出协议 ST12 比对范围 (2);① 换行转换误判、② manifest 排除范围窄于协议,这两点已修;③ 是否保留这项比对 | IA1-CR:13 | ③ 交 Review Gate(`IMPL_A_REPORT.md` 待决第 1 项) |
| AA2 | MINOR | `src/metrix_e1/data.py` `verify()` | 没有冻结哈希的数据文件与重新生成结果不同时记为 ST12,标签超出范围 (1) 的字面 | IA1-CR:21 | 交 Review Gate(待决第 2 项) |
| AA3 | MINOR | `src/metrix_e1/frozen.py` `Frozen.protocol_text`、`FrozenRecord.source_sha256` | 阶段 A 中没有使用方 | IA1-CR:25 | 保留:阶段 B 从 `protocol_text` 解析门槛,`record.py` 写入 `source_sha256` |
| AA4 | MINOR | `requirements.lock` | torch 2.11.0+cu130,A100 主机须有支持 CUDA 13.0 的驱动,否则 ST8 | IA1-CR:43 | 阶段 C 写入 `RUNBOOK_A100.md`;锁文件注释已注明 |
| AA5 | MINOR | `src/metrix_e1/frozen.py` | 指令第 5 节“提供全部冻结常量”:G0、ST 门槛只在协议正文,尚未解析 | IA1-CR:45 | 阶段 B 从冻结协议正文解析,不写死 |
| AA6 | MINOR(data-auditor 说明) | 协议第 3 节 L2 | 两个模板都不足 4 个词(4 个跨集合模板对)时 Jaccard 按 0 计;协议未规定,按 1 计则 L2 超限;manifest 的撰写值 0.2 与 Executor、auditor 一致 | IA1-DA:179 | 交 Review Gate(待决第 5 项) |
| AA7 | MINOR(data-auditor 说明) | 协议第 2.6 节 | Y/F token 比的计数口径(每个序列加 1 个 `<\|endoftext\|>`)协议没写;不加时 1,769 / 2,020(1.142),两种都在区间内 | IA1-DA:180 | 交 Review Gate(待决第 5 项) |
| AA8 | MINOR(data-auditor 说明) | 模板归一化 | 不去首尾空格时 0/32 相同 | IA1-DA:181 | 同 1.9 节 S12,已登记 |
| AA9 | MINOR(第 1 轮 (d)) | 协议第 3 节命令路径 | `python -m metrix.e1_pilot.check_leakage` 需 `PYTHONPATH=metrix/e1-pilot/src`,依赖仓库根 `metrix/` 没有 `__init__.py`;须写入 RUNBOOK | IA2-CR:67 | 阶段 C 写入 `RUNBOOK_A100.md`;`IMPL_A_REPORT.md` 待决第 3 项(备案) |
| AA10 | MINOR(第 1 轮 (e)) | arm L 的 LoRA | 不用 peft;自写 LoRA 须由单元测试第 4 项覆盖(B = 0、alpha = 2 × rank、dropout 0、28 层 × 7 个模块) | IA2-CR:69 | 阶段 B |
| AA11 | MINOR(第 1 轮 (f)) | 数据文件的记录字段 | `train_F`、`train_Y`、`dev_qa`、`general_dev`、`anchor_text` 的字段协议未规定,由实现自定(与 1.9 节 S7 同一缺口:S7 是 manifest 没有定义字段) | IA2-CR:71 | 字段列于 `IMPL_A_REPORT.md` `data.py` 一节;待决第 4 项(备案) |

### 1.19 Implementation 阶段 A:工作提交 `602a39e8` 第 2 轮审查(`reviews/602a39e8…/code-reviewer_round2.md` 记 `IA2-CR:n`)

code-reviewer 结论 PASS,没有 BLOCKER;第 1 轮各项的现状见原文第一节;新提 8 条 MINOR(N1–N8)。N1、N3、N5、N6、N7、N8 在修复提交中修(`impl_a/t6_fix_commit.txt`);data-auditor 第 2 轮结论 PASS(仅作参考),没有新项。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| AB1 | MINOR(N2) | `src/metrix_e1/frozen.py` `load()` | 工作区 manifest 按解析结果比较,空白、`1.0`→`1e0` 一类一字节改动不停;按解析比较是第 8 节第 1 步改写 manifest 所必需;不影响计算 | IA2-CR:76 | 随 AA1 交 Review Gate(待决第 1 项) |
| AB2 | MINOR(N4) | `src/metrix_e1/frozen.py` `check_library_versions` | 比对发行包元数据版本并忽略 `+local` 标签(`2.11.0+cu130`、`2.11.0+cpu` 都视为 2.11.0),与 PEP 440 的 `==` 一致;元数据版本与 `torch.__version__` 在本环境不同 | IA2-CR:84 | 交 Review Gate 确认(待决第 7 项);阶段 B 的 `record.py` 同时记录两者 |

### 1.20 Implementation 阶段 A:修复提交 `219c4a60` 的提交前审查(`reviews/219c4a60…/code-reviewer.md`,记 `IAF-CR:n`)

结论 PASS,没有 BLOCKER,没有 MAJOR;N1、N3、N5、N6、N7、N8 逐条“已修,修法正确”。新提 4 条 MINOR,都是证据、引用与登记方面的缺口,在报告提交中处理。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| AC1 | MINOR | `reports/impl_a/t6_fix_commit.txt` 第 1 行 | 引用的 `reviews/602a39e8…/` 在修复提交中不存在;两轮审查原文、`interruption_round2.txt`、data-auditor 的脚本与 stdout 都还不在仓库 | IAF-CR:55 | 报告提交中入库:`reviews/602a39e8c4be1e1efa682a26637ad94fb919b7b8/`(两轮全部调用文字、输入、调用前检查、中断与续做记录、原文、提取记录)、`audit/ia_*`、`audit/stdout/impl_a/` |
| AC2 | MINOR | `src/metrix_e1/frozen.py` `FrozenRecord.source_sha256` | 是工作区原始字节的哈希;CRLF 与 LF 检出解析出同一 record,但该值不同 | IAF-CR:57 | 登记;阶段 B 的 `record.py` 写入时注明是工作区原始字节的哈希,或另记 LF 归一化后的哈希 |
| AC3 | MINOR | 本文件 | N2、N4 与第 1 轮 MAJOR #1 ③、(b)、(f) 没有登记;N4 涉及协议第 0 节的解释,须 Review Gate 确认 | IAF-CR:59 | 报告提交中登记:③ 为 AA1、(b) 为 AA2、(f) 为 AA11、N2 为 AB1、N4 为 AB2,并列入 `IMPL_A_REPORT.md`“待 Review Gate 决定”;N4(AB2)裁决前不记为已关闭 |
| AC4 | MINOR | `reports/impl_a/t5_commit_push.txt` | “工作提交即第 2 轮审查的内容”在 t5 中只有 stat 层面的证据;唯一的逐字节比对在没有入库的 `interruption_round2.txt`(提交前约 7 分钟) | IAF-CR:63 | 报告提交中补:`impl_a/t7_report_commit.txt` 第 1 部分 `git diff 8149d872 602a39e8` 与第 2 轮审查输入逐字节相同;`interruption_round2.txt` 入库;修复提交在 `git commit` 前记录了暂存区与审查输入的逐字节比较(`reviews/219c4a60…/precommit_check.txt`)。另:审查方指出推送后的 `ls-remote` 只查了分支,修复提交的推送记录(`t7` 第 2 部分)已同时列出标签 |

### 1.21 Implementation 阶段 A:报告提交的提交前审查(`reviews/602a39e8…/code-reviewer_report-commit.md`,记 `IAR-CR:n`)

结论 PASS,没有 BLOCKER;2 MAJOR、12 MINOR。按第 7–9 轮的先例,报告、本文件与证据方面的问题在报告提交中处理(被审查的版本与提交版本的差异见 `reviews/602a39e8…/report_commit_post_review.diff`);本提交没有再请审查。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| AD1 | MAJOR | 两个审查目录的 `extract_log.txt` | 仓库中的审查原文、调用文字、续做消息是否就是被提取、被核对的那几份,没有原始输出(提取与核对在会话临时目录,复制没有记录) | IAR-CR:66 | `impl_a/t7_report_commit.txt` 第 3 部分:23 个仓库副本与临时目录原件逐一 `cmp` 相同;五份审查原文再次直接提取到仓库路径,正文 sha256 与 `extract_log.txt` 所记相同;报告提交审查本身直接提取到仓库路径 |
| AD2 | MAJOR | `IMPL_A_REPORT.md` 推送一节 | 报告提交的推送输出写成“见最终回复,下一阶段写入”,不符合指令第 3 节第 6 项“推送输出一律写入 reports/” | IAR-CR:68 | 推送时立即用 `logrun.sh` 写入 `impl_a/t8_report_push.txt`(工作区),随下一阶段第一个提交入库;报告与最终回复写明路径 |
| AD3 | MINOR | `IMPL_A_REPORT.md` 审查一节 | 临时目录路径与仓库文件“同名”不成立:第 1 轮输入改名为 `review_input_round1.diff` | IAR-CR:70 | 已改:写明改名对应关系 |
| AD4 | MINOR | 本文件 1.18–1.20 节、第 3 节 | (d)(e)(f) 没有登记;AC3 说 (f) 已登记但没有;第 3 节缺待决第 3、4、6 项 | IAR-CR:72 | 已补 AA9–AA11;AC3 改为逐项对应;第 3 节补上(备案项) |
| AD5 | MINOR | 本文件 1.18 节导语;`IMPL_A_REPORT.md` | “影响协议一致性……的已修”与交 Review Gate 的项矛盾 | IAR-CR:74 | 已改为“已修,或属于协议未覆盖、需要解释的,交 Review Gate” |
| AD6 | MINOR | `IMPL_A_REPORT.md` | “4 CPU、15 GiB”、peft 发布时间、`metrix-work` 删除没有原始输出 | IAR-CR:76 | `t7` 第 3 部分补 `nproc`、`free -g`、PyPI 发布时间、`git reflog` 与 `git branch --list`,报告引用之 |
| AD7 | MINOR | `IMPL_A_REPORT.md` 开头 | Owner 的批准时间与另给的三条要求在仓库中没有记录 | IAR-CR:78 | 已补 `tasks/IMPL_A_OWNER_MESSAGE.md`(消息原文) |
| AD8 | MINOR | `IMPL_A_REPORT.md` 开头 | 第 2 轮调用时间写成 16:56(原始文件为 16:54),续做写成约 01:12(01:11) | IAR-CR:80 | 报告改为 16:54、约 01:11;仓库中第 2 轮两份原文的头部(Executor 写的说明行)在直接提取时改为同样时间,正文不变(`t7` 第 3 部分) |
| AD9 | MINOR | `IMPL_A_REPORT.md` 开头 | 计数不算读取 TEST 的依据应为协议第 3 节,不是指令第 3 节第 3 项 | IAR-CR:82 | 已改为两处并列 |
| AD10 | MINOR | `IMPL_A_REPORT.md` 结论一览、`data.py` 一节 | 12 行交叉核对、模板重算、暴露匹配在 `t2` 中没有输出行 | IAR-CR:84 | 已注明由 `load()` 通过与 RESULT: PASS 隐含、没有单独打印;以后的生成命令可打印这些检查(登记,未改代码) |
| AD11 | MINOR | `IMPL_A_REPORT.md` 单元测试一节 | “各改一位”易读成每个哈希都改 | IAR-CR:86 | 已改为“各改一个(DATA_MANIFEST.json 的文件哈希、fact 的数据哈希)” |
| AD12 | MINOR | `reviews/219c4a60…/code-reviewer.md` | 原文中的 “t6:NNN”“t5:NNN” 多数是审查输入 diff 的行号 | IAR-CR:88 | 原文不改;报告审查一节写明换算(t6 = diff − 101,t5 = diff − 17) |
| AD13 | MINOR | 报告提交审查输入 | “只在 metrix/e1-pilot/ 下”只有 stat 的间接证据 | IAR-CR:90 | 提交前的 `git diff --cached --name-only` 与提交后的 `outside_metrix_check.py` 写入 `impl_a/t8_report_push.txt` |
| AD14 | MINOR | `IMPL_A_REPORT.md` 修复提交一节 | 修复提交不调用 data-auditor 是判断问题(N1 改了 ST12 参照表的读入) | IAR-CR:92 | 列入 `IMPL_A_REPORT.md` 待决第 8 项(备案) |

### 1.22 Implementation 阶段 B:工作提交 `74a4d444` 第 1 轮审查(`reviews/74a4d444…/code-reviewer_round1.md` 记 `IB1-CR:n`,`data-auditor_round1.md` 记 `IB1-DA:n`)

code-reviewer 结论 PASS,没有 BLOCKER(10 MAJOR、19 MINOR);data-auditor 结论 PASS(仅作参考),3 条观察。第 1 轮各项在第 2 轮暂存内容中的现状由第 2 轮原文第一节逐条给出(`IB2-CR:15-91`);下表只列没有修、只修了一部分或交 Review Gate 的项。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| BA1 | MAJOR | `src/metrix_e1/interpretations.py` B14 | 状态原因与第 9 节的四点张力(G0.5 三部分同一原因;G0.4 改判;G0.3、G0.9、G0.10 无原因词;可能多个原因) | IB1-CR:29 | 登记于 B14,交 Review Gate(`IMPL_B_REPORT.md` 待决第 1、5 项) |
| BA2 | MAJOR | B5(LoRA A 初始化) | 随机数已改为 `rng_rule` 给出的 `random.Random` 本身(`r.uniform`);分布与 purpose 字符串协议未规定 | IB1-CR:30 | 交 Review Gate(待决第 1 项) |
| BA3 | MAJOR | B17(预检估算) | 评测时间改为预检中实测一次 FP32 DEV 评测 × 评测单位数;估算方法协议未规定 | IB1-CR:26 | 交 Review Gate(待决第 1 项) |
| BA4 | MINOR | `stops.st13_scan` | ST13 原来只映射调用方的布尔值;已加按文件检测的 `st13_scan`,src 中没有调用方 | IB1-CR:34 | 阶段 C 由 `run_pilot` 在每步开始时调用 |
| BA5 | MINOR | `stats.immediate_gain`、`record.render_text`、`compute.cost_usd`、`compute.run_flops`、`compute.preflight_summary`、`compute.estimate_total_hours` | 已实现,没有调用方(后三个由报告提交审查补列,IBR-CR:99) | IB1-CR:37、41 | 阶段 C 接线 |
| BA6 | MINOR | `train.fetch_model_config` | 下载的 `config.json`(sha256 `1ddb5b89…`)没有冻结值可比;冒烟小模型若由它构造,来源不受 ST12 覆盖 | IB1-CR:46 | 阶段 C:RUNBOOK 与实验记录写明其哈希 |
| BA7 | — | B19 与阶段 A 预告的停止点 | 阶段 A 预告“如协议未覆盖即停下”,本阶段改为实现并列入待决 | IB1-CR:76 | 交 Review Gate 明确接受(待决第 4 项) |
| BA8 | 观察 | `data.build_general_dev` | `eval_sets.jsonl` 以文本模式读取,test 行被 UTF-8 解码 | IB1-DA:217 | 工作提交中已改为按字节读取;此前 `data.py` 自身以文本模式读取的运行列于 `IMPL_B_REPORT.md` 待决第 3 项(BE1),读法问题交 Review Gate |
| BA9 | 观察 | B1–B3 | s、epoch 的起点与置换调用方式的具体后果;`train_Y.jsonl` 的行序未冻结 | IB1-DA:222 | B3 写明行序;交 Review Gate(待决第 1 项) |
| BA10 | 观察 | `TestAuthorization` | 只是约定上的保护,任何代码都能构造 | IB1-DA:223 | 每个 TEST 路径先调用 `leakage.verify_authorization`,按已提交记录复核(1.25 节 BD1) |

### 1.23 Implementation 阶段 B:工作提交 `74a4d444` 第 2 轮审查(`reviews/74a4d444…/code-reviewer_round2.md` 记 `IB2-CR:n`,`data-auditor_round2.md` 记 `IB2-DA:n`)

code-reviewer 结论 PASS,没有 BLOCKER(2 MAJOR、15 MINOR);data-auditor 结论 PASS(仅作参考),6 条观察。两条 MAJOR 与 15 条 MINOR 在修复提交 `fdbb9def` 中处理,现状由修复提交审查原文第一节逐条给出(`IBF-CR:16-60`);下表只列没有修完或交 Review Gate 的项。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| BB1 | MAJOR(一部分) | `evaluate.evaluate_model(split="test")` | TEST 评测入口的守卫:授权复核已加(修复提交,本报告提交补齐);ST10 通过的凭据与“TEST 只评一次”没有实现 | IB2-CR:96 | 阶段 C 的硬性前提(`IMPL_B_REPORT.md`“留给阶段 C 的事项”;1.25 节 BD8) |
| BB2 | MINOR | B24(T3 含 Acc_CB(N)) | T3 原文只说 TEST-QA,实现同时检查 Acc_CB(N) | IB2-CR:102 | B24 写明,交 Review Gate(待决第 1 项) |
| BB3 | MINOR | 登记 | 第 4 个前提、render_text、cost_usd、config.json 哈希的登记不在暂存内容中 | IB2-CR:124 | 本报告提交:`IMPL_B_REPORT.md` 待决第 2 项、“留给阶段 C 的事项”;BA5、BA6 |
| BB4 | 观察 | `tests/test_data_hashes.py` → `reports/round5/l6_check.py` | 参考比对测试让 `l6_check.py` 以文本模式读取完整的 `eval_sets.jsonl`,test 行被 UTF-8 解码(不解析、不分词) | IB2-DA:213 | 第二个修复提交起只给它 DEV 行的字节副本;过去的运行是否属于读取 TEST 交 Review Gate(待决第 3 项;BC1) |
| BB5 | 观察 | `evaluate_model(split="test")` | 新路径,没有调用者;阶段 C 的驱动代码加入后需要再审 | IB2-DA:225 | 阶段 C 审查 |
| BB6 | 观察 | `test_data.check_interpretations_ruled` | 协议三个前提之外的第 4 个前提 | IB2-DA:226 | 交 Review Gate(待决第 2 项) |

### 1.24 Implementation 阶段 B:修复提交 `fdbb9def` 的提交前审查(`reviews/fdbb9def…/code-reviewer.md` 记 `IBF-CR:n`,`data-auditor.md` 记 `IBF-DA:n`)

code-reviewer 结论 PASS,没有 BLOCKER(1 MAJOR、9 MINOR);data-auditor 结论 PASS(仅作参考)。MAJOR 的代码部分与 7 条 MINOR 在第二个修复提交 `493d7f9c` 中修(现状见 `IBF2-CR:15-73`);下表是余下的项。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| BC1 | MAJOR(审查方注明不确定) | `reports/round5/l6_check.py:82`;`tests/test_data_hashes.py` | BB4 的登记不充分;每次 pytest 都让 `l6_check.py` 以文本模式解码全部 1200 行(800 行 test) | IBF-CR:63 | 代码:第二个修复提交起测试只给它 DEV 行的字节副本(脚本未改)。已执行过的运行逐条列于 `IMPL_B_REPORT.md` 待决第 3 项,交 Review Gate;裁决之前不得再对完整的 `eval_sets.jsonl` 运行 `l6_check.py` |
| BC2 | MINOR | `evaluate.evaluate_model` | ST10 凭据与“只评一次”(BB1 的另两项) | IBF-CR:69 | 同 BB1 |
| BC3 | MINOR | 审查记录 | 工作提交推送时审查原文与 auditor 输出不在仓库 | IBF-CR:81 | 本报告提交入库:`reviews/74a4d444…/`、`reviews/fdbb9def…/`、`reviews/493d7f9c…/`、`audit/ib_*`–`ie_*`、`audit/stdout/impl_b/`;推送顺序写入 `IMPL_B_REPORT.md`“提交” |
| BC4 | 观察 | `leakage.verify_authorization` | 不复核条件 1(ST12)与解释裁决 | IBF-DA:220 | 解释裁决:本报告提交起复核(BD1)。条件 1:每步开始时的 `stops.st12` 负责,`verify_authorization` 文档写明 |

### 1.25 Implementation 阶段 B:第二个修复提交 `493d7f9c` 的提交前审查(`reviews/493d7f9c…/code-reviewer.md` 记 `IBF2-CR:n`,`data-auditor.md` 记 `IBF2-DA:n`)

code-reviewer 结论 PASS,没有 BLOCKER(1 MAJOR 为 BC1 的遗留、8 MINOR);data-auditor 结论 PASS(仅作参考)。MINOR 中的代码与测试项在本报告提交中修(`impl_b/t12_fix3.txt`;本报告提交的审查见 `reviews/74a4d444…/` 的 `*_report-commit*`,登记于 1.26 节)。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| BD1 | MINOR | `leakage.verify_authorization` | 文档说复核条件 2、3 的全部内容,实际不复核选定配置构成训练计划、30 个 checkpoint 哈希、数据内容哈希与解释裁决 | IBF2-CR:78 | 已修:条件 2、3 的内容检查提到 `record.gate0_record_problem`、`freeze_record_problem`,TEST 生成器与 `verify_authorization` 共用;数据内容哈希与冻结值比较;解释裁决复核;授权的冻结提交同时与当前 PROTOCOL_FROZEN 和调用方加载的冻结文件比较(签名改为 `verify_authorization(authorization, fz, repo_root=None)`;`run_test_part`、`evaluate_model` 相应改为传 `fz`)。测试逐项去掉检查后失败(`t12` 的变异检查) |
| BD2 | MINOR | `tests/test_evaluate.py` | 非有限值测试只覆盖第一次前向,不覆盖解码循环内一步 | IBF2-CR:80 | 已修:`LateNaNStub` 第 1 次前向有限、之后 NaN;去掉循环内检查测试失败(`t12`) |
| BD3 | MINOR | `tests/test_evaluate.py` | 3 个连续空行 | IBF2-CR:82 | 已修 |
| BD4 | MINOR | `tests/test_test_data.py::test_pending_interpretations_block_test` | 依赖当前仍有待决解释 | IBF2-CR:84 | 已修:monkeypatch 出“一条待决”与“全部已裁决”两种状态 |
| BD5 | MINOR | `tests/test_data_hashes.py::_dev_rows_only` | 过滤前不核对源文件哈希;路径与计数写死 | IBF2-CR:86 | 已修:过滤前整文件 sha256 与冻结值比较;路径取 `D.params(fz).general_source`;计数与 `data.build_general_dev` 的按行前缀计数比较;manifest 副本取自冻结提交 |
| BD6 | MINOR | 审查记录 | 同 BC3 | IBF2-CR:88 | 同 BC3 |
| BD7 | MINOR | `reports/impl_b/t10_fix2_commit.txt` | grep 只显示含 `eval_sets` 的行,也不含 `reports/` | IBF2-CR:90 | `t12` 列出 src/ 与 tests/ 中全部 `open(`、`read_text(`、`read_bytes(` 调用;`reports/round5/l6_check.py` 是唯一以文本模式打开 `eval_sets.jsonl` 的文件,裁决之前不再对完整文件运行(BC1) |
| BD8 | MINOR | `evaluate.evaluate_model` | ST10 凭据与“只评一次” | IBF2-CR:92 | 同 BB1 |
| BD9 | 观察 | `leakage.verify_authorization` | 读工作区的 PROTOCOL_FROZEN,不是 HEAD blob | IBF2-DA:254 | 登记;本报告提交起另与调用方 `frozen.load` 得到的冻结提交比较 |
| BD10 | 观察 | `tests/test_st12.py` | 翻转的那个字节落在 test 行范围内;只改临时副本的原始字节,随后只对整个文件求哈希,不解码、不解析 | IBF2-DA:256 | 列入 `IMPL_B_REPORT.md` 待决第 3 项(备案) |

### 1.26 Implementation 阶段 B:报告提交的提交前审查(`reviews/74a4d444…/code-reviewer_report-commit.md` 记 `IBR-CR:n`,`data-auditor_report-commit.md` 记 `IBR-DA:n`)

code-reviewer 结论 PASS,没有 BLOCKER(1 MAJOR、12 MINOR);data-auditor 结论 PASS(仅作参考),6 条观察,35 个埋入故障全部检出。两份审查都因 HTTP 429 中断后续审完成。按阶段 A 报告提交的先例,审查之后只改报告、本文件与证据,不改代码(审查之后的改动见 `reviews/74a4d444…/report_commit_post_review.diff`);代码与测试类的项登记到阶段 C 的第一个代码提交。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| BE1 | MAJOR | `IMPL_B_REPORT.md` 待决第 3 项;BA8 | 交 Review Gate 的运行清单只列了 `l6_check.py` 的运行,漏了 `data.py` 自身在工作提交修复前以文本模式读取的运行(data generate、verify、条件 1、各次 pytest) | IBR-CR:74 | 已补:待决第 3 项逐条列出(含 `data.py` 版本的 sha256 核对与无法核实的早期版本),另补 data-auditor 冻结前第 5 轮两个以文本模式读取的脚本;BA8 改为指向第 3 项。读法仍交 Review Gate |
| BE2 | MINOR | `src/metrix_e1/leakage.py` `verify_authorization`;`tests/test_test_data.py` | 三方比较合成一个条件、一句报错,`other_protocol_frozen` 用例区分不出“与当前 PROTOCOL_FROZEN 比较”一项 | IBR-CR:76 | 登记;阶段 C 第一个代码提交中分开比较或补“授权等于 fz、不等于当前 PROTOCOL_FROZEN”的用例 |
| BE3 | MINOR | `IMPL_B_REPORT.md` 单元测试第 9 项 | “逐项去掉检查后对应用例失败”超出 `t12` 变异检查的 6 项 | IBR-CR:78 | 已改为准确列出变异了哪几项 |
| BE4 | MINOR | `IMPL_B_REPORT.md` 审查表第 1 行 | “8 条改代码”与原文不符 | IBR-CR:80 | 已改为“9 条改代码(其中 B5、B17 改后仍交 Review Gate),B14 只登记” |
| BE5 | MINOR | `IMPL_B_REPORT.md`、本文件 1.25 节 | 报告提交审查记录的位置说法不一;路径对照缺 `review_report/` | IBR-CR:82 | 已统一为 `reviews/74a4d444…/*_report-commit*`,补对照与两处改名 |
| BE6 | MINOR | `IMPL_B_REPORT.md` 提交、推送 | 报告提交的推送记录 `t13` 留在工作区,与阶段 A `t8` 丢失的情形相同 | IBR-CR:84 | 推送后立即作为证据单独提交并快进推送(Owner 第 0 项);那次推送自身的输出 `t14` 随阶段 C 第 0 步入库;列入待决第 6 项请 Review Gate 确认 |
| BE7 | MINOR | `IMPL_B_REPORT.md` 开头“中断” | 没有写第三次重启与本轮 HTTP 429 中断;中断记录不在仓库 | IBR-CR:86 | 已补;`interruption_report-commit.txt`、续审消息与核对续审消息送达的脚本入库 |
| BE8 | MINOR | `reports/impl_b/t12_fix3.txt` | 被测代码与暂存内容之间只有 stat 行数对应,没有哈希 | IBR-CR:88 | 已补 `impl_b/t12c_reviewed_code_pytest.txt`:两份审查之后在被审的暂存代码上重跑,204 passed;运行前后 `src/`、`tests/` 的树哈希相同、工作区等于暂存区,`src/`、`tests/` 部分的 diff 与审查输入的同一部分 sha256 相同 |
| BE9 | MINOR | `test_data.check_interpretations_ruled`、`leakage.verify_authorization`;`frozen.CONTENT_HASH_KEYS` 与 `Frozen.content_hashes` | 解释裁决检查仍是两份代码;`content_hashes` 另写一遍字面键 | IBR-CR:90 | 登记;阶段 C 抽 `interpretations.pending_problem()`,`content_hashes` 按 `CONTENT_HASH_KEYS` 组装 |
| BE10 | MINOR | `evaluate.evaluate_model`;`tests/test_evaluate.py` | `fz is None` 分支无测试;`LateNaNStub` 用例没断言 `values` 非空;对照写死 16 | IBR-CR:94 | 登记;阶段 C 补 |
| BE11 | MINOR | `IMPL_B_REPORT.md` 留给阶段 C 的事项 | `compute.run_flops`、`preflight_summary`、`estimate_total_hours` 没有调用方,未列 | IBR-CR:99 | 已补入报告与 BA5 |
| BE12 | MINOR | `src/metrix_e1/record.py` 末尾 | 多一个空行(W391) | IBR-CR:101 | 登记;阶段 C 删 |
| BE13 | MINOR | `reports/impl_b/mutate_fix3.py` | 变量 `SP` 未使用 | IBR-CR:103 | 登记,不改:该文件须与 `t12` 中运行的脚本逐字节相同(`t12` 末尾的 `cmp`) |
| BE14 | 观察 | `leakage.verify_authorization` | 信任调用方传入的 `fz`:四个冻结值取自 `fz.record.data_sha256`,手工构造的 Frozen 可带入别的值(与手工构造 TestAuthorization 同一类约定;不是读取 TEST 的路径) | IBR-DA:338 | 登记;阶段 C 由 `run_pilot` 只用 `frozen.load()` 的结果调用 |

### 1.27 Implementation 阶段 C:C1 工作提交第 1 轮审查(暂存树 `2408558f`;`reviews/tree-9be4df2a…/code-reviewer_round1.md` 记 `IC1-CR:n`,`data-auditor_round1.md` 记 `IC1-DA:n`)

code-reviewer 结论 PASS(4 MAJOR、18 MINOR);data-auditor 结论 BLOCK(B05;仅作参考的状态,但 BLOCK 照规定修复后重审)。两份审查都因 HTTP 429 中断后续审完成(`interruption.txt`、`resume_message_*.txt`、`extract_log_round1.txt`)。第 1 轮的问题都在第 2 轮暂存树中处理,下表“处理”一列写的是第 2 轮的做法(C1 工作提交最终没有提交,见 1.29 节;各轮暂存树的代码在审查输入 `input*.diff` 中);第 2 轮审查对每一条的核对见同目录 `*_round2.md`。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CA1 | BLOCK | `testgate._ever_committed` | `git log` 没有 `--full-history`:标记在侧分支提交又删除、`--no-ff` 合并回来并删掉侧分支引用后,历史简化把它剪掉,begin 会写入第二个标记;ST10 记录与结果文件的检查同样受影响 | IC1-DA B05 | 已修:`--full-history`;测试 `test_a_marker_deleted_on_a_merged_side_branch_refuses`(断言不加该选项时 `git log` 找不到);变异“history: simplified”被测出 |
| CA2 | 观察 | `testgate._committed` | 已提交的记录是 JSON 数组时抛 AttributeError,不是拒绝 | IC1-DA (a) | 已修:非对象拒绝,两份记录各有测试 |
| CA3 | 观察 | `refuse_if_marker` | 远端其他分支上从未 fetch 的标记看不到(B11);只有结果文件、没有标记时不拒绝(B12) | IC1-DA (b) | 已修:远端全部分支 `ls-remote --heads` 后按名 fetch;结果文件存在即 TestAlreadyEvaluated;各有测试 |
| CA4 | 观察 / MINOR | `test_data.main` | `code_commit` 在生成之后才检查,代码有未提交改动时 TEST 已生成 | IC1-DA (d);IC1-CR MINOR | 已修:生成之前检查,测试断言生成函数未被调用 |
| CA5 | 观察 / MINOR | `leakage.run_test_part` 文档 | 引用不存在的 `testgate.st10_problem` | IC1-DA (e);IC1-CR MINOR | 已改为 `st10_check` |
| CA6 | MAJOR | `refuse_if_marker`、`begin_test_evaluation` | 只 fetch 调用方给的一个远端分支;远端名与分支名是自由参数 | IC1-CR MAJOR 1 | 已修一部分:查远端全部分支;标记写入远端 URL 与分支;测试“单分支落后克隆、标记在远端另一分支”。远端名与分支名在 C2 的 `run_pilot` 中固定 |
| CA7 | MAJOR | `record.selection_freeze_record`、`testgate` | checkpoint 哈希的定义(train.state_sha256)没有写明,也没有登记为解释 | IC1-CR MAJOR 2 | 文档写明;新增解释 B25(PENDING_REVIEW_GATE,交 Review Gate;裁决前所有 TEST 路径拒绝);C2 冒烟中保存、重载后核对 state_sha256 |
| CA8 | MAJOR | `testgate._refuse` | 环境类拒绝与“已评测”用 IMPLEMENTATION_FAIL | IC1-CR MAJOR 3 | 环境类改为 BLOCKED;已评测改为不带状态的 TestAlreadyEvaluated;记录缺失或不绑定仍为 ImplementationFail;状态词交 Review Gate |
| CA9 | MAJOR | `reports/impl_c/c1_gate_probe.py` | 给 data-auditor 用的黑盒探针含 Executor 的判断,是否算“Executor 的检查代码”不确定 | IC1-CR MAJOR 4 | 保留,交 Review Gate;auditor 用它的运行输出随报告提交入库 |
| CA10 | MINOR | `evaluate.evaluate_model` | checkpoint 在 GPU 检查之前登记 | IC1-CR | 已修:`require_test_session` 不登记,`require_gpu` 之后 `claim_checkpoint` |
| CA11 | MINOR | `begin_test_evaluation` | 提交与推送的前提在写标记之后才发现 | IC1-CR | 已修:身份、快进、`push --dry-run` 预检,失败 BLOCKED 且不写入;测试 |
| CA12 | MINOR | `_push` | 没有 `--no-follow-tags` | IC1-CR | 已修;测试建注释标签并设 `push.followTags=true` |
| CA13 | MINOR | `require_test_session` | 用内存中的 session.models / checkpoints | IC1-CR | 已修:用已提交标记中的值 |
| CA14 | MINOR | `begin_test_evaluation` | 冻结记录重复读取,有不可达分支 | IC1-CR | 已修:`verify_authorization` 返回两份记录 |
| CA15 | MINOR | `refuse_if_st10_record` | 不查远端 | IC1-CR | 已修:与标记相同;`test_data --remote`(默认 origin) |
| CA16 | MINOR | `evaluated_models` | 魔法数字 5 | IC1-CR | 已修 |
| CA17 | MINOR | `frozen.content_hashes` | 未按 BE9 由键列表组装 | IC1-CR | 已修:`CONTENT_HASH_BYTES`,测试用 `FZ.CONTENT_HASH_KEYS` |
| CA18 | MINOR | `c1_mutate.py` | “ancestor always true” 变异实为 TypeError;`TD` 未用 | IC1-CR | `c1_mutate.py` 按运行时原样保留(c1_02 的记录);第 2 轮用 `c1_mutate_r2.py`(改正这两点) |
| CA19 | MINOR | `testgate` 多处 | 若干闸门分支既无测试也不在变异中 | IC1-CR | 已补测试与变异(c1_04:58 个变异全部测出) |
| CA20 | MINOR | `testgate`、`evaluate` | begin / finish 等尚无生产调用方 | IC1-CR | C2 的 `run_pilot` 接入,届时 data-auditor 复审 TEST 路径 |
| CA21 | MINOR | `evaluate.evaluate_model` | 每次 TEST 调用先算 state_sha256 | IC1-CR | 已改为其余检查之后再算;正式运行的时间在 C2 的预检估算与 RUNBOOK 中说明 |
| CA22 | MINOR | `finish_test_evaluation` | `default=str` | IC1-CR | 已去掉,有测试 |
| CA23 | MINOR | `evaluate_model(split="dev")` | DEV 路径不核对行 | IC1-CR | C2:`run_pilot` 的数据每步由 ST12(`data.verify`)核对 |
| CA24 | MINOR | `c1_02_checks.txt` | 被测代码与暂存内容的对应没有哈希 | IC1-CR | 第 2 轮:c1_04 末尾记录 `git diff HEAD -- src tests` 的 sha256,与暂存内容 `git diff --cached HEAD -- src tests` 的 sha256 相同(工作提交最终没有提交,没有提交前记录) |
| CA25 | MINOR | `testgate`、`interpretations` | 行宽超过 120 | IC1-CR | testgate 已改;interpretations 中 B1–B24 的原有长行未改(内容未变) |

### 1.28 Implementation 阶段 C:C1 工作提交第 2 轮审查(暂存树 `dc4f28df`;`reviews/tree-9be4df2a…/code-reviewer_round2.md` 记 `IC2-CR:n`,`data-auditor_round2.md` 记 `IC2-DA:n`)

code-reviewer 结论 PASS(6 MAJOR、12 MINOR);data-auditor 结论 BLOCK(唯一原因:暂存的探针与接口不符;被审 src/ 的行为在修正副本下 214 项全部一致)。data-auditor 因 HTTP 429 中断后续审完成(`interruption_round2.txt`、`resume_message_data-auditor_round2.txt`;中断前发出的补充信息没有送达,内容在续审消息中重复,`info_message_data-auditor_round2.txt`)。下表“处理”一列是第 3 轮暂存树中的做法(未提交)。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CB1 | BLOCK | `reports/impl_c/c1_gate_probe.py` | 探针没有跟上接口:marker 操作参数个数错、begin 读已删除的 `session.models`;Executor 没有运行过它 | IC2-DA;IC2-CR MAJOR 3 | 已修;另加:拒绝在本仓库或 origin 为 CANONICAL_REPO 的克隆上运行;为临时仓库设 CANONICAL_REPO / PILOT_BRANCH 并打印;Executor 运行一次(`c1_probe_run.py`,输出在 c1_06) |
| CB2 | MAJOR | `evaluate.evaluate_model` | 生产路径上的 `claim_checkpoint` 没有测试执行到 | IC2-CR | 已修:新测试替换 `require_gpu` 与打分函数;变异“claim removed” |
| CB3 | MAJOR | `testgate.remote_url` 等 | 克隆 URL 中的令牌会写进标记并推送 | IC2-CR | 已修:`scrub` 去掉 user information(标记与报错);测试 |
| CB4 | MAJOR | `testgate` | remote 与分支仍是自由参数,标记中的 URL 没有核对 | IC2-CR | 已修:`CANONICAL_REPO`、`PILOT_REMOTE`、`PILOT_BRANCH` 与 `check_remote`(仓库名、分支参数、检出分支、浅克隆);测试 |
| CB5 | MAJOR | `interpretations.py`、`IMPL_C_REPORT.md` 第 17 行 | 裁决要求 `pending()` 为空,本提交新增待决的 B25;报告第 17 行与代码不符 | IC2-CR | 报告已改正;B25 列入本报告“待 Review Gate 决定” |
| CB6 | MAJOR | `testgate` 各拒绝 | 拒绝状态的遗留(TEST 已生成、git log 失败、模型哈希不符、TestAlreadyEvaluated 不是 ProtocolStop) | IC2-CR | 模块文档列出各类拒绝的状态;列入本报告“待 Review Gate 决定” |
| CB7 | MINOR | `finish_test_evaluation` | 没有核对已提交标记的字节 | IC2-CR | 已修,测试 |
| CB8 | MINOR | `_ever_committed` 等 | reflog 中的标记、浅克隆、远端历史被改写 | IC2-CR | 已加 `--reflog`;浅克隆 BLOCKED;“远端分支受保护”的前提写入模块文档与 RUNBOOK |
| CB9 | MINOR | `testgate` | 若干新分支没有测试(ST10 记录只在远端、fetch 失败、dry-run 失败) | IC2-CR | 已补测试与变异 |
| CB10 | MINOR | `tests/test_testgate.py` | 检出标记的测试只断言 “commit ” | IC2-CR | 改为 `assert_started`(“already started”与“counts as evaluated”) |
| CB11 | MINOR | `tests/test_testgate.py` | code commit 用例只用不存在的对象 | IC2-CR | 已补“另一分支上的真实提交” |
| CB12 | MINOR | `remote_heads` 文档 | “no local ref written” 不准确 | IC2-CR | 已改 |
| CB13 | MINOR | `record.committed_record` | 非对象 JSON 得到 AttributeError | IC2-CR | `record.committed_json` 抛 NotCommitted;`testgate._committed` 中重复的检查删去 |
| CB14 | MINOR | `require_test_session`、`_is_ancestor` | 死代码(返回值、`of` 参数) | IC2-CR | 已删 |
| CB15 | MINOR | `testgate.py:38`、测试空行、`evaluate` 中的 TG 导入 | 可读性 | IC2-CR | 已改 |
| CB16 | MINOR | `IMPL_C_REPORT.md`、`interpretations.py` 文档 | 登记不充分 | IC2-CR | 本停止提交登记(1.27–1.29、`IMPL_C_REPORT.md` C1 节);`interpretations.py` 文档已改 |
| CB17 | MINOR | 探针 | 没有防护(真实仓库、`--interpretations-ruled`) | IC2-CR | 拒绝在本仓库或 origin 为 CANONICAL_REPO 的克隆上运行(c1_06 中有拒绝的输出) |
| CB18 | MINOR | `test_data.main` | ST10 记录靠操作员手工提交 | IC2-CR | `test_data.main` 用 `commit_paths` 提交并推送 |
| CB19 | 观察 | data-auditor B13、B17 | 只在 reflog 中、只能从远端标签到达的标记 | IC2-DA | B13 已由 `--reflog` 覆盖;B17(远端只有标签)仍不检索,前提是远端历史不被改写(RUNBOOK) |

### 1.29 Implementation 阶段 C:C1 工作提交第 3 轮审查(暂存树 `9be4df2a`;`reviews/tree-9be4df2a…/code-reviewer_round3.md` 记 `IC3-CR`,`data-auditor_round3.md` 记 `IC3-DA`)

code-reviewer 结论 PASS(2 MAJOR、11 MINOR);data-auditor 结论 BLOCK(唯一原因:N1、N2 中 `marker` 操作为 ACCEPT,与 Executor 第 3 轮调用说明“检出分支不是 main 时 begin 与 marker 为 BLOCKED”不符;其余 251 项比对一致)。连续第 3 轮未 PASS,按 metrix/CLAUDE.md 第 5 节第 4 条停止(`5f5cd51`)。Review Gate 对 C1 的裁决(2026-11-25,`tasks/IMPL_C1_RULING.md`)之后,“处理”一列改为按裁决的处理(第二次送审,工作提交 `ae60e0f`;防范对象以外的项按裁决第 9 项登记不修)。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CC1 | BLOCK | `testgate.check_remote`、`remote_heads`;模块文档“every look-up on a remote … checks … the branch”;`check_remote` 文档;第 3 轮调用说明 | 检出分支只在传入分支参数时检查;标记与 ST10 记录的检索(经 `remote_heads`)不传,所以在非 main 检出(N1)与分离 HEAD(N2)上 `refuse_if_marker` 为 ACCEPT。不绕过闸门:begin 写标记前、TEST 驱动生成前都检查检出分支 | IC3-DA 差异汇总;静态 k | 裁决第 1 项采用 (a):所有 TEST 路径要求 Pilot 分支检出且 HEAD 等于 fetch 后的远端最新提交;只查工作区与该提交的文件树(`ae60e0f`) |
| CC2 | MAJOR | `test_data.main` | 提交与推送的前提(没有暂存、提交者身份、HEAD 是远端分支的后代、`push --dry-run`)只在 `commit_paths` 中检查,即 TEST 已生成、ST10 记录已写入工作区之后;记录留在工作区后拒绝任何重跑,也没有补交的代码路径 | IC3-CR MAJOR 1;IC3-DA INFO 2 | 裁决第 2 项:`check_commit_preconditions` 由 begin、finish、驱动共用,在生成 TEST 之前检查;生成之后推送被拒视为已生成、BLOCKED、由 Owner 决定(`ae60e0f`) |
| CC3 | MAJOR | 流程 | 第 3 轮在 worktree 中试跑变异(4 个未测出,是第 3 轮补测试的起因)的输出没有入库 | IC3-CR MAJOR 2 | 已入库(`5f5cd51`);裁决第 7 项接受 |
| CC4 | MINOR | `testgate.check_remote` | 只比较 fetch URL 的 owner/name:不比较主机(镜像、过期的本地镜像可通过),不看 push URL(pushurl 指向别处时标记写入后才 BLOCKED) | IC3-CR | 主机名比对:裁决第 6 项不处理;push URL:防范对象以外,登记不修(裁决第 9 项) |
| CC5 | MINOR | `reports/impl_c/c1_gate_probe.py` | 以本地路径克隆本仓库(origin 为本仓库路径)时探针不拒绝 | IC3-CR | 防范对象以外,登记不修(裁决第 9 项) |
| CC6 | MINOR | `tests/test_testgate.py` 凭据测试 | 只有标记一处的断言能区分有没有 scrub;没有以带凭据的 URL 作 remote 的拒绝用例;`_USERINFO` 不处理 userinfo 中未编码的 `/` | IC3-CR | 防范对象以外,登记不修(裁决第 9 项) |
| CC7 | MINOR | `c1_mutate_r3.py`;`c1_06` | `-x` 只记录第一个失败的测试:“st10 record: history / remote not searched”两个变异的测出是附带的 | IC3-CR | 新的变异脚本为每个变异指名应当失败的测试,不用 -x(`ae60e0f` 的 `c1b_mutate.py`) |
| CC8 | MINOR | `tests/test_testgate.py::test_evaluate_model_claims_after_the_gpu_check` | 只检验“GPU 检查之后登记”,没有检验“打分之前登记” | IC3-CR | 已补测试与变异(`ae60e0f`) |
| CC9 | MINOR | `testgate` 模块文档 | “远端分支受保护”与 metrix/CLAUDE.md 第 6 节“不直接推送到受保护分支”字面冲突;`push --dry-run` 不运行服务器端钩子与分支规则 | IC3-CR | 裁决第 6 项:第 6 节的“受保护分支”指 main;模块文档改为写明 GitHub 设置(`ae60e0f`);RUNBOOK 在 C3 |
| CC10 | MINOR | `test_data.py` 文档第 21–25 行;`testgate.py` 文档第 15–16 行 | “提交与推送在命令之外”已过时;ST10 记录的检索范围没写 reflog | IC3-CR;IC3-DA INFO 1 | 随模块文档改写改正(`ae60e0f`) |
| CC11 | MINOR | `IMPL_C_REPORT.md`;`testgate.py` 文档第 52–53 行;`audit/` | 登记不在被审树中;auditor 的输出未跟踪 | IC3-CR | 已登记(`5f5cd51`);audit/ 第 1–3 轮输出已入库 |
| CC12 | MINOR | `testgate.remote_heads`、`_commit_preconditions` | ls-remote 输出的 HEX40 检查、预检中 ls-remote 的失败没有测试,也不在变异中 | IC3-CR | 相应代码(`remote_heads`、预检中读远端分支)已删去(`ae60e0f`) |
| CC13 | MINOR | `tests/test_testgate.py` | 两个测试声明了未用的 `monkeypatch` | IC3-CR | 已改(`ae60e0f`) |
| CC14 | MINOR | `testgate.py`、`interpretations.py` | 超长行;断行使一行只剩半句 | IC3-CR | 已改(`ae60e0f`) |
| CC15 | 观察 | `remote_heads` | 远端只有标签指向标记、没有分支(B17)时不检索 | IC3-DA INFO 3 | 裁决第 6 项:只能经标签到达的标记不处理 |
| CC16 | 观察 | `testgate._ever_committed`、`code_commit` | 两处 raise 不经 scrub(内容是本地 `git log`、`git status` 的输出) | IC3-DA INFO 6 | 防范对象以外,登记不修 |
| CC17 | 观察 | 探针 `st10` 操作 | 不检查 B25,不读 Gate 0 与冻结记录;所有 TEST 路径先调用 `verify_authorization` | IC3-DA INFO 4 | 登记;B25 已裁决(裁决第 3 项),`pending()` 为空 |
| CC18 | 观察 | 探针 | 探针把 CANONICAL_REPO 设为临时仓库的 origin,“另一个仓库”的拒绝无法黑盒测到 | IC3-DA INFO 5 | 登记;裁决第 5 项:探针可作为驱动子进程运行 |

### 1.30 Implementation 阶段 C:C1 第二次送审,工作提交 `ae60e0f7`(暂存树 `365960a0`)的第 1 轮审查(`reviews/ae60e0f7…/code-reviewer_round1.md` 记 `IC4-CR`,`data-auditor_round1.md` 记 `IC4-DA`)

按 Review Gate 对 C1 的裁决(`tasks/IMPL_C1_RULING.md`)修改后重新送审,轮次从 1 计。code-reviewer 结论 PASS(2 MAJOR、9 MINOR);data-auditor 结论 PASS(仅作参考,metrix/CLAUDE.md 第 10 节;1 MINOR、1 个交 Review Gate 的读法、2 条提示)。两份结论都是 PASS,工作提交按被审的暂存树提交;下表的代码项在修复提交中处理(“处理”一列),其审查见 1.31。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CD1 | MAJOR | `testgate.require_test_session`、`_check_session_checkout` | 评测调用不 fetch,与裁决第 1 项字面不同;唯一的实际差别:begin 之后有人向远端推送时,剩余模型仍会评完,到 finish 才 BLOCKED | IC4-CR MAJOR 1;IC4-DA MINOR-2 | 读法不变,交 Review Gate 确认(`IMPL_C_REPORT.md` C1 节“待 Review Gate 决定”);补测试 `test_evaluation_calls_do_not_fetch_finish_does`;RUNBOOK 写明 begin 到 finish 之间任何人不得向该分支推送 |
| CD2 | MAJOR | `testgate.begin_test_evaluation` | 同一克隆中两个并发的 begin 可以都拿到会话(第二个在第一个写标记之前通过 `refuse_if_marker`;或另一提交落在本次提交与推送之间) | IC4-CR MAJOR 2 | 已修:推送之后核对推送的提交含本会话标记的字节、其父提交不含标记,否则 BLOCKED(视为已评);三个测试、两个变异 |
| CD3 | MINOR | `evaluate.evaluate_model` | `split="test"` 且 `with_s_mapping` 时,参数检查在登记与打分之后,白白用掉唯一一次 TEST 评测 | IC4-CR | 已修:移到函数开头、TEST 闸门之前;测试与变异 |
| CD4 | MINOR | `testgate.commit_paths` 等 | `sleep=time.sleep` 默认值在定义时绑定,驱动测试真实睡眠 | IC4-CR | 已修:默认 None,调用时取 `time.sleep` |
| CD5 | MINOR | `test_data.generate_test`、`leakage.run_test_part` | 库函数本身不做检出检查,只靠 main 先调用 | IC4-CR | 文档写明 main 是唯一调用方(run_pilot.py 以子进程运行 main);C2 审查时核对 |
| CD6 | MINOR | `testgate.check_checkout` | BLOCKED 文字建议 “push the local commits”,与裁决第 2 项(由 Owner 决定)不符 | IC4-CR | 已改:TEST 路径产生的本地提交只在 Owner 决定后推送 |
| CD7 | MINOR | `tests/test_testgate.py` | “评测调用不 fetch” 没有测试固定 | IC4-CR | 已补(同 CD1) |
| CD8 | MINOR | `testgate._where` | `git cat-file -e` 的任何失败都当作“不存在” | IC4-CR | 登记不修(防范对象以外;tip 刚经 rev-parse 验证) |
| CD9 | MINOR | `tests/test_testgate.py` | 测试名与内容不符(只构造“较早提交中删去”一种情形) | IC4-CR | 已改名 `test_a_marker_deleted_in_a_later_commit_is_not_searched` |
| CD10 | MINOR | `test_data.main` | TEST 文件写出之后、ST10 记录写入之前崩溃,可换 --out 或换机器再次生成(内容相同) | IC4-CR | 登记不修(防范对象以外,不涉及评测);RUNBOOK 写明按 BLOCKED 报告 Owner |
| CD11 | MINOR | `IMPL_C_REPORT.md`、`c1b_01_checks.txt`、本文件 1.29 | 引用的 C1 小节不存在;c1b_01 未标明被取代;1.29 的处理列未更新 | IC4-CR | 本报告提交:写入小节、标明 c1b_01 与 c1b_03 被取代、更新 1.29 |
| CD12 | MINOR | `testgate.finish_test_evaluation`、`claim_checkpoint` | session 为 None 时抛 AttributeError,不是拒绝 | IC4-DA MINOR-1 | 已修:守卫以 `isinstance(session, TestSession)` 开头;测试与变异 |
| CD13 | 提示 | C2 | 结果文件的内容由调用方决定,须不含 TEST 原文 | IC4-DA | C2:`pilot.test_evaluate` 只写聚合指标与每个 fact 的分数(不含题目文字;general_* 行不写;逐题明细在仓库外);C2 审查核对 |
| CD14 | 提示 | 检索范围 | 只在 index 中的标记或 ST10 记录不在检索范围内,但 begin 与驱动被“有暂存”挡住 | IC4-DA | 登记 |
| CD15 | 观察 | data-auditor | 生成之后真实推送被拒的路径无法黑盒复现(需要真实 TEST) | IC4-DA | 登记;单元测试 `test_driver_push_refused_after_generation_counts_as_generated` 用替身覆盖 |

### 1.31 Implementation 阶段 C:C1 修复提交 `b48fe842`(暂存树 `ae5fcb2f`)的第 1 轮审查(`reviews/b48fe842…/code-reviewer_round1.md` 记 `IC5-CR`,`data-auditor_round1.md` 记 `IC5-DA`)

code-reviewer 结论 PASS(1.30 CD1 的 MAJOR 沿用、交 Review Gate;6 MINOR);data-auditor 结论 PASS(仅作参考;MINOR 与提示)。两份审查都因 HTTP 429 中断,本会话进程重启后续审完成(`interruption.txt`、`resume_message_*.txt`)。1.30 中各项的核对见两份原文第一节。下表为本轮新提出的项;都不改代码(防范对象以外、只涉及描述或测试区分度),代码项随 C2 或之后的提交在必要时处理。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CE1 | MAJOR | `testgate.require_test_session` | 同 CD1(评测调用不 fetch),沿用,待 Review Gate 确认 | IC5-CR | 交 Review Gate(`IMPL_C_REPORT.md` C1 节“待 Review Gate 决定”);RUNBOOK 写明 begin 到 finish 之间不得向该分支推送 |
| CE2 | MINOR | `tests/test_testgate.py::test_a_commit_of_another_begin_between_commit_and_push_is_blocked` | 该情形两项检查都会触发,单独不能检验任何一项;文档只写“字节不同” | IC5-CR | 登记;单项由另外两个测试区分(`c1b_04`) |
| CE3 | MINOR | `testgate._blob`、begin 的父提交检查 | `git cat-file blob` 的任何失败都当作“没有标记”,父提交检查因此偏向放行 | IC5-CR | 防范对象以外,登记不修(与 CD8 同类) |
| CE4 | MINOR | `tests/test_testgate.py::test_s_mapping_on_test_is_refused_before_the_gate` | 在 CPU 上靠 GPU 检查先拒绝测出变异,没有让“先登记再丢弃”真的发生 | IC5-CR | 登记;检查位于 require_gpu 之前,结论成立 |
| CE5 | MINOR | `test_data.generate_test` 文档 | 把“run_pilot.py 以子进程运行 main”写成现状,而 run_pilot.py 在 C2 才加入 | IC5-CR | C2 提交加入 run_pilot.py 后成为现状;C2 审查核对 |
| CE6 | MINOR | `tests/test_testgate.py::test_driver_checks_the_commit_preconditions_before_generating` | 没有替换 sleep,变异运行时真实睡 14 s | IC5-CR | 登记(只影响变异运行的耗时) |
| CE7 | MINOR | 报告、`c1b_01`、`c1b_03`、本文件 | 同 CD11 | IC5-CR | 本报告提交 |
| CE8 | MINOR | begin 的字节比较 | 标记路径上有 git clean filter 或换行转换时,提交的 blob 与写入的字节不同,BLOCKED 文字归因为“另一个 begin” | IC5-DA MINOR-A | 防范对象以外,登记不修(结果安全:没有评测,按已评处理,由 Owner 决定) |
| CE9 | MAJOR(读法) | 同 CE1 | 评测调用不 fetch | IC5-DA MINOR-2 | 同 CE1 |
| CE10 | 描述 | Executor 的修复说明 | 写“新增 3 个变异”,实为 4 个变异名(含 `finish: any session`),总数 78 无误 | IC5-DA MINOR-C | 登记 |
| CE11 | 提示 | `evaluate_model` | with_s_mapping 的新顺序无法用探针黑盒验证(探针没有这个参数) | IC5-DA | 登记;静态核对与测试、变异覆盖 |

### 1.32 Implementation 阶段 C:C2 工作提交 `5219ff77`(暂存树 `b80c9062`)的第 1 轮审查(`reviews/5219ff77…/code-reviewer_round1.md` 记 `IC7-CR`,`data-auditor_round1.md` 记 `IC7-DA`)

code-reviewer 结论 PASS(12 MAJOR、22 MINOR;下表 CF13–CF29 中有几项合并);data-auditor 结论 PASS(仅作参考;IC7-M1、IC7-M2)。按 Implementation Task Order V1 第 9 节,影响协议一致性、数据、指标或隔离的项在修复提交中修;协议的读法交 Review Gate(`IMPL_C_REPORT.md` C2 节“待 Review Gate 决定”);其余登记。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CF1 | MAJOR | `pilot.final_record` | 第 1 步之前停止的 formal 运行只在 <work> 写记录,与第 10 节“含被停止的”不相容;情形列举不全;`Pilot()` 中的 ST12 没有记录 | IC7-CR | 读法交 Review Gate(待决第 1 项);文档补全情形(含 A100 上的 ST8、第 1 步开始时的 ST12/ST13、连续性检查、`Pilot()` 中的 ST12) |
| CF2 | MAJOR | `run_test_generate`、`run_test_evaluate` | ST10 停止没有实验记录 | IC7-CR | 已修:test-generate 在已提交的 ST10 记录超限时写并提交记录(BLOCKED、ST10);test-evaluate 在 begin 的 ST10 闸门停止时写记录;测试与变异 |
| CF3 | MAJOR | 第 2–4 步 | ST1、ST11、ST2、ST3 在 step_end 之前抛出:该步记录不写,已写的训练记录与明细不提交,Actual 只有一句话 | IC7-CR | 已修:`Pilot.stop_in_step` 先写并提交该步记录(含 leakage、预检、G0.3 值、阳性对照);停止或崩溃时未提交的记录与实验记录一起提交;Actual 含已到达的步与步记录;测试与变异 |
| CF4 | MAJOR | `run_test_evaluate` | 标记之后的非 ProtocolStop 崩溃不写记录 | IC7-CR;IC7-DA IC7-M1 | 已修:标记存在时捕获任何异常,写并提交 BLOCKED 记录后重新抛出;测试与变异 |
| CF5 | MAJOR | ST7 | 事前判断只用训练时间;评测前 next_seconds=0;TEST 在 begin 之前不判断能否评完 | IC7-CR | 已修:训练前含保存、重载、哈希与 DEV 评测;评测前含加载与评测;begin 之前以已提交的第 2 步记录估计整个 TEST 评测(`test_evaluation_seconds`)作为 ST7 的 next_seconds |
| CF6 | MAJOR | N、G0.8、预检、TEST 的评测 | 非有限值不经 stops.st6,状态成为 NOT_TESTED / BLOCKED | IC7-CR | 已修:`control_evaluation` 经 st6(选定配置或对照,IMPLEMENTATION_FAIL);预检的非有限值同样处理(没有预估就不能判 ST11;读法交 Review Gate,待决第 4 项) |
| CF7 | MAJOR | 第 7 步 G0.2、`step8_freeze` | 被剔除的配置:G0.2 输入写死;冻结记录取哈希 KeyError | IC7-CR | 已修 KeyError:剔除的运行保存停止时的状态并记录其 state_sha256,冻结记录有 30 个哈希(测试:提交链测试中注入 F6 非有限);G0.2 的读法(剔除的配置不算“用到”)写在代码注释,交 Review Gate(待决第 3 项) |
| CF8 | MAJOR | `step8_freeze` | 冻结记录前没有 ST12、ST13,没有第 8 步记录 | IC7-CR | 已修:`step_start(8)` / `step_end(8)` |
| CF9 | MAJOR | 冒烟第 8 步 | 在已有 formal 记录的检出上,冒烟的“拒绝”测试会真的生成 TEST | IC7-CR | 已修:HEAD 或工作区中有 Gate 0、冻结或 ST10 记录时拒绝启动子进程;测试与变异 |
| CF10 | MAJOR | 预检 | ST11 读“B17 + checkpoint 开销”,与已裁决的 B17 不一致;文件哈希与 begin 的哈希漏计 | IC7-CR | 已改:ST11 只读 B17 的估算(原样);checkpoint 开销(补上文件哈希与 begin 的哈希)与两者之和只报告,并用于 ST7 的事前判断;是否让 ST11 读和,交 Review Gate(待决第 2 项) |
| CF11 | MAJOR | 重跑 | 同一 --work 因 checkpoint 存在而失败;换 --work 则 ledger/clock 从头;确定性记录与 HEAD 相同导致 BLOCKED | IC7-CR | 已修:只提交与 HEAD 不同的路径;连续性检查(已有 formal 步记录而 --work 中没有 device ledger 时拒绝;已有冻结记录时 formal 拒绝);重跑方式由 Owner 决定(RUNBOOK) |
| CF12 | MAJOR | 测试 | formal 独有的提交链、冻结记录、实验记录提交没有执行过 | IC7-CR | 已修:`test_formal_commit_chain_through_the_freeze_record`(临时克隆 + 裸远端,第 1–8 步的提交、冻结记录、TEST 生成器的前提成立);变异 |
| CF13 | MINOR | `gate_steps` | Gate 0 PASS 时实验记录 Status 写 PASS | IC7-CR | 已改为 NOT_TESTED(Actual 写 Gate 0 PASS);交 Review Gate(待决第 5 项) |
| CF14 | MINOR | 实验记录文件名 | 固定,重跑覆盖 | IC7-CR | 已修:文件名带开始时间 |
| CF15 | MINOR | `test_evaluate` | 标记之前 NotCommitted/KeyError 以 traceback 退出 | IC7-CR | 已修:转为 BLOCKED 拒绝 |
| CF16 | MINOR | `first_load` | 没有 CUDA 时 TypeError | IC7-CR | 已修:经 `compute.check_device`(ST8) |
| CF17 | MINOR | `test_evaluate` | GPU 时钟段在 try/finally 之外打开 | IC7-CR | 已修 |
| CF18 | MINOR | `_name`、`g0`、`G08_REEVALUATIONS`、smoke 配置重复 | 可读性 | IC7-CR | 已修 |
| CF19 | MINOR | 文档 | outside_repo 的例外;引用尚不存在的报告与 RUNBOOK 节 | IC7-CR | 已改(2026-11-27 裁决改引 `tasks/IMPL_C2_OWNER_MESSAGE.md`;RUNBOOK 在 C3) |
| CF20 | MINOR | 测试 | 路径清单含 formal 不写的 step8;负向检查对本仓库写 | IC7-CR | formal 现在写第 8 步记录;负向检查改用测试自己的目录 |
| CF21 | MINOR | `run_pilot.py` | 指令写 `--smoke`,实现为子命令 smoke | IC7-CR | 登记;报告与 RUNBOOK 写明 |
| CF22 | MINOR | fetch-model | 下载前不做设备检查 | IC7-CR | 已修:先做 ST8 |
| CF23 | MINOR | `save_checkpoint` | `del model` 不能释放调用方的引用 | IC7-CR | 已改:删去,注释写明 |
| CF24 | MINOR | e2e 测试 | 没有检查实验记录 | IC7-CR | 已补 |
| CF25 | MINOR | formal 重跑 | 冻结后可再次运行 formal | IC7-CR | 已修(连续性检查) |
| CF26 | MINOR | `test_evaluate` | N 的哈希没有与第 3 步记录比对 | IC7-CR | 已修:begin 之前比对,不符 BLOCKED |
| CF27 | MINOR | 崩溃的状态词 | NOT_TESTED | IC7-CR | formal 的崩溃仍为 NOT_TESTED,标记之后的崩溃为 BLOCKED;交 Review Gate(待决第 5 项) |
| CF28 | MINOR | 原始输出 | 录制在 write-tree 05a76f57 上,送审树 b80c9062 | IC7-CR | 修复提交的录制在送审树上首尾记录 STATE |
| CF29 | MINOR | `c2_mutate.py` | 在本仓库工作区改写源文件 | IC7-CR | 登记(finally 恢复并比对哈希;未发生) |
| CF30 | MINOR | 标记之前的拒绝不写记录 | 第 10 节的读法 | IC7-DA IC7-M2 | 交 Review Gate(待决第 1 项一并) |

### 1.33 Implementation 阶段 C:C2 修复提交 `49fc9a35`(暂存树 `b40224e6`)的第 1 轮审查(`reviews/49fc9a35…/code-reviewer_round1.md` 记 `IC8-CR`,`data-auditor_round1.md` 记 `IC8-DA`)

code-reviewer 结论 PASS(4 MAJOR、18 MINOR);data-auditor 结论 PASS(仅作参考;IC8-M1–M4)。处理原则同 1.32。**1.32 的两处更正**(IC8-DA IC8-M3):CF28 的处理写“修复提交的录制在送审树上首尾记录 STATE”,实际录制时的写树是 `6071ea72`,送审树 `b40224e6` 多出的是证据文件,两者代码相同(data-auditor `ic8_00`);CF29 写“未发生”,实际在 `c2b_01` 被杀时发生了一次,已恢复(`c2b_01b_restore_after_kill.txt`;data-auditor `ic8_07` 无残留)。1.32 的文字保持原样,以本段为准。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CG1 | MAJOR | `Pilot.run_seconds` | 对每个训练都乘 A 因子(B17 只对 A) | IC8-CR;IC8-DA IC8-M4 | 已修:只对 arm A;`eval_seconds` 按先加载什么(load / reload / 已在内存)计;补 file_hash_s;测试与变异 |
| CG2 | MAJOR | `test_evaluation_seconds` | 15 个 checkpoint 按 load_s 计(实际为 reload_s);没有余量 | IC8-CR | 已修 reload_s;是否加余量交 Review Gate(待决第 2 项一并);测试与变异 |
| CG3 | MAJOR | `run_test_evaluate` | 以“工作区有标记”判断已开始:TEST 评过之后再运行,TestAlreadyEvaluated 被记成崩溃,提交 BLOCKED 记录 | IC8-CR;IC8-DA IC8-M1 | 已修:`begun_by_this_process`(本进程调用了 begin、调用前没有标记、现在有);TestAlreadyEvaluated 单独处理(不写记录,原样抛出);e2e 断言该次拒绝不推送任何提交;变异 |
| CG4 | MAJOR | 测试 | formal 下步内停止的提交、未提交记录的补交、test-generate 的 ST10 记录、ST7 事前判断的接线、N 哈希不符都没有测试 | IC8-CR;IC8-DA IC8-M2 | 已补:`test_formal_stop_and_crash_commit_what_was_written[st3/crash]`、`test_test_generate_records_an_st10_stop_of_its_own_run`、提交链与 e2e 中对 before_run 收到的 next_seconds 的断言、e2e 中 N 哈希不符的拒绝;变异 |
| CG5 | MINOR | `run_test_evaluate` | begin 之前的 ST7、ST8、ST9、ST12 不写记录 | IC8-CR | 已改:begin 之前带停止码的协议停止写记录;没有停止码的拒绝不写(交 Review Gate,待决第 1 项一并) |
| CG6 | MINOR | `run_seconds`、`eval_seconds` | 漏计 file_hash_s;G0.8 前用 load_s;内存中的模型多计 load_s | IC8-CR | 已修(CG1) |
| CG7 | MINOR | `run_test_generate` | 不设 code_commit;已有的超限 ST10 记录会再记一次 | IC8-CR;IC8-DA IC8-M2 | 已修:设 code_commit;只在本次运行之前 HEAD 没有 ST10 记录时记录;测试 |
| CG8 | MINOR | `start_checks` | 第 1 步提交后、第一次加载模型前停止,同一 --work 重跑被拒,消息不准确 | IC8-CR | 消息写明两种可能;登记(重跑由 Owner 决定) |
| CG9 | MINOR | 重跑 | 同一 --work 重跑到第 4 步才失败 | IC8-CR | 已修:formal 在 --work 中已有 checkpoint 时于第 1 步之前拒绝;测试与变异 |
| CG10 | MINOR | `smoke_model_config` | 没有用 smoke_config | IC8-CR | 已修 |
| CG11 | MINOR | `Pilot.commit` | 提交之前就从 uncommitted 中移除 | IC8-CR | 已修:提交成功之后移除 |
| CG12 | MINOR | `final_record` | 补交可能包括 Gate 0 与冻结记录 | IC8-CR | 登记(内容在写出前已校验;范围外) |
| CG13 | MINOR | `test_evaluate` | 读 TEST 文件与 load_data 在 try 之外 | IC8-CR | 已修:一并转为 BLOCKED |
| CG14 | MINOR | `pilot.py` | 调用 testgate 私有的 `_blob` | IC8-CR | 登记 |
| CG15 | MINOR | 引用 | 指向尚未写入的 IMPL_C_REPORT C2 节 | IC8-CR | 报告提交写入 C2 节与 2026-11-27 裁决 |
| CG16 | MINOR | `c2b_checks.sh` | 用法行文件名错 | IC8-CR | 保持原样(已运行);`c2c_checks.sh` 改正,STATE 加 `git ls-files -s` |
| CG17 | MINOR | `c2_mutate_fix1.py` | parse 的成对替换分支是死代码 | IC8-CR | 保持原样(已运行);`c2_mutate_fix2.py` 删去 |
| CG18 | MINOR | 录制 | 写树与送审树不同 | IC8-CR;IC8-DA IC8-M3 | 同 CF28 更正;`c2c_checks.sh` 的 STATE 记录 `git ls-files -s` |
| CG19 | MINOR | 变异 | 在本仓库工作区改写源文件,已发生一次 | IC8-CR | 登记;录制单独运行、不与冒烟并行 |
| CG20 | MINOR | 标记之后的处理 | 不包括 KeyboardInterrupt | IC8-CR | 已修:begin 之后捕获 BaseException,写记录后原样抛出;测试 |
| CG21 | MINOR | 预检的非有限值 | 记为 IMPLEMENTATION_FAIL | IC8-CR | 交 Review Gate(待决第 4 项) |
| CG22 | MINOR | `run_test_generate` | 不做 start_checks | IC8-CR | 已修:检查 device ledger(同一个 --work) |

### 1.34 Implementation 阶段 C:C2 第二个修复提交 `dd65a361`(暂存树 `a6ce8a0e`)的第 1 轮审查(`reviews/dd65a361…/code-reviewer_round1.md` 记 `IC9-CR`,`data-auditor_round1.md` 记 `IC9-DA`)

code-reviewer 结论 PASS(3 MAJOR、9 MINOR);data-auditor 结论 PASS(仅作参考;IC9-M1、IC9-M2)。处理原则同 1.32。

| # | 严重度 | 位置 | 问题 | 来源 | 处理 |
|---|---|---|---|---|---|
| CH1 | MAJOR | `test_evaluate` | TEST 评过之后再运行,begin 之前的 ST7/ST8/ST9 写并推送 BLOCKED 记录 | IC9-CR | 已修:`refuse_if_test_evaluated` 在任何带停止码的检查之前只读检查:有结果则 TestAlreadyEvaluated,有标记无结果则没有停止码的 BLOCKED,都不写记录;e2e 在 before_run 抛 ST7 时断言远端不变;变异 |
| CH2 | MAJOR | `test_evaluate` | 错误的 --work 先被 check_preconditions 的 ST12 停下,写并推送 ST12 记录 | IC9-CR | 已修:code_commit、start_checks、已评检查移到 check_preconditions 之前;测试 `test_test_evaluate_begin_wiring[wrong_work]`;变异 |
| CH3 | MAJOR | `test_evaluate` 的两个标志 | 真实的设置没有测试执行 | IC9-CR | 已补:`test_test_evaluate_begin_wiring[crash_after_begin]`(真实 begin 之后第 2 次评测崩溃:记录 test_begun true 并推送;同一 Pilot 再运行:没有停止码的拒绝、远端不变)、`[refused_inside_begin]`(begin 中写标记之前拒绝:不写记录);对两行与重置各一个变异 |
| CH4 | MINOR | `test_evaluation_seconds` | 15 个文件哈希在 GPU 时钟打开之前,不应计入;计数名借用 | IC9-CR | 已修:去掉文件哈希;加载次数为 test_models − 1 |
| CH5 | MINOR | 第 3 步、S 的估计 | N 的哈希、S 的 s_mapping 漏计 | IC9-CR | 第 3 步加 hash_s;S 登记(与 B17 同口径) |
| CH6 | MINOR | test-evaluate 的 ST8 | 推送记录,与 formal 第 1 步之前的处理不一致 | IC9-CR | 交 Review Gate(待决第 1 项一并) |
| CH7 | MINOR | 标志 | test_evaluate 开头不重置 | IC9-CR;IC9-DA IC9-M1 | 已修;变异 |
| CH8 | MINOR | `run_test_generate` | code_commit、start_checks 没有测试 | IC9-CR | 已补断言与拒绝情形;变异 |
| CH9 | MINOR | 测试 | `_formal_on_clone` 文档;records 测试文档;300 写死;提交链用 training_plan 筛 | IC9-CR | 已改 |
| CH10 | MINOR | `c2_mutate_fix2.py`、`fix2b`、`c2c_04` | fix2 中该变异仍指名 E2E;fix2b 有未用常量;fix2b 的字节没有被输出绑定 | IC9-CR | 保持原样(已运行);`c2_mutate_fix3.py` 只指名能到达的测试;`c2d_checks.sh` 的 STATE 记录所运行脚本的 sha256 |
| CH11 | MINOR | IMPL_C_REPORT | C2 节与 2026-11-27 裁决尚未写入 | IC9-CR | 修复提交之后的报告提交写入 |
| CH12 | MINOR | `checkpoint_overhead_seconds` | 50 次加载都按 load_s,与 TEST 估计的 reload_s 不一致(只报告) | IC9-DA IC9-M2 | 已修:基座加载按 load_s,checkpoint 重载按 reload_s |

## 2. 已在第 5–7 轮解决(核对用)

| 原条目 | 来源 | 处理 |
|---|---|---|
| `l6_check.py` 的 “test rows decoded: 0” 是写死的文字 | R5-CR:34;R5 待决 9 | 第 6 轮第 2 项:改为按 split 计数,并要求非 dev 的解码数为 0(`round6/t2_l6_check.txt`) |
| `l6_check.py` 的 tok 单位标为参考却参与判定 | R5-CR:36;R5 待决 9 | 第 6 轮第 1a、2 项:判定只看 `str.split()`;`w` 与 tok 单位只报告(`round6/t2_l6_judgment_demo.txt`) |
| `l6_check.py` 循环变量名 `split` 易误读 | R5-CR:36 | 第 6 轮改名为 `units_of`(该函数新增了真正的 `split` 变量,不改会混淆) |
| parcae 分词器按 Stage 1 `data_lock.json` 核对;`eval_sets.jsonl` 没有锁定 sha256 | R5-CR:38;R5 待决 9 | 第 6 轮第 1h 项:`DATA_MANIFEST.json` 锁定两个 sha256,脚本按 manifest 核对 |
| `st_prefix_check.py`、`verify_scoring.py` 没有例子时抛 TypeError / IndexError,不打印 `RESULT:` 行 | R4 待决 7;R5-CR:28 (c);R5-RC:31 | 第 6 轮第 2 项:异常时打印 `RESULT: FAIL`、非 0 退出(`round6/t2_guard_fail.txt`)。抛出的仍是 traceback,不是专门的提示 |
| n_x 取重新编码长度还是截断 id 长度 | R5-CR:30;R5-RC:25 | 第 6 轮第 1c 项 |
| `prefix(f)` 前加不加特殊 token | R5-CR:30;R4 待决 4 后半 | 第 6 轮第 1e 项 |
| `generation_config.json` 默认采样,协议没写覆盖 | R5-CR:32 后半;R4 待决 2 第 3 点 | 第 6 轮第 1d 项 |
| “去掉开头空格”的含义 | R4 待决 3 | 第 6 轮第 1d 项 |
| 对整个 `eval_sets.jsonl` 求 sha256、解析 test 行是否算读取 TEST | R5-RC:33;R5 待决 3 | 第 6 轮第 1g 项;`l6_check.py` 对 test 行只读 `split` 字段 |
| 协议表格中未转义的竖线 | R5 待决 10 | 第 6 轮第 1i 项(`round6/t1_protocol_checks.txt`) |
| `audit/r5_kl_denoms.py` 把截断 id 长度写死为 128 | R5-RC:27 (4);R5 待决 6、14 | 第 6 轮第 5 项由 data-auditor 修正(见 `ROUND6_REPORT.md` 任务 5) |
| 第 5 轮报告中 MINOR 条数、行号、转述等措辞问题 | R5-RC:15、17、19、21、31、39 | 第 5 轮报告提交中已改 |
| `guard_ab.sh`、`guard_fail.sh` 按判定设置退出码,却没有异常保护与 RESULT 行(data-auditor BLOCK) | R6-DA E3 | 修复提交 `2620f306`(复核结果见 `ROUND6_REPORT.md` 任务 5) |
| `t2_harness_fail.txt` 中两次不经管道的运行,完整输出只在 scratchpad | R6b-CR MAJOR 2 | 报告提交中原样入库:`round6/t2_harness_fail_ab_missing_old.out.txt`、`t2_harness_fail_missing_py.out.txt`(sha256 与 scratchpad 中的文件相同,`round6/t2_harness_fail_outputs.txt`) |
| `t1_protocol_checks.txt` 是在 `599230f9` 填入第 14 节之前运行的 | R6-CR:31 | 报告提交中对 `599230f9` 的已提交内容重跑:`round6/t1_protocol_checks_599230f9.txt` |
| `<think>`(151667)与 `</think>`(151668)不是特殊 token,`skip_special_tokens=True` 去不掉,协议没有写 | R5-CR:32 前半;R5 待决 7 第 1 点;R6 待决 11 第 1 点 | 第 7 轮第 1f 项:EM 归一化之前先删除 `<think>…</think>` 片段(协议第 5 节,第 14 节 v1-r7) |
| 第 2.6 节 S 的置换与第 2.5 节的候选抽取没有写死调用方式,只凭协议文字不能逐字节复现 `train_S.jsonl` 与 `candidates.json` | R4 待决 8;R5 待决 8;R6 待决 11 第 2 点 | 第 7 轮第 1g 项:写死调用方式与记录格式,两次独立生成逐字节一致,规范化 SHA-256 写入协议与 manifest(`reports/round7/t1g_gen_s_cands.txt`) |

## 3. 不按 MINOR 登记、交 Review Gate 的开放项

下面几项原来有的标为 MINOR,但会影响指标或可复现性,修它们要改协议或改 auditor 的文件,Executor 不能自行处理。

- 第 6 轮第 2 项“所有检查脚本”是否包括 auditor 已入库的旧脚本(A4、A6):第 7 轮指令第 3 项将其登记入 1.7 节 G4。本节目前没有其它开放项;第 7 轮审查新提出的项见 1.8 节。
- 第 9 轮:1.14 节 W1(MAJOR)、W2、W3、W4/X1、W5、W8,1.16 节 Y5、Y8 须由 Review Gate 决定,列于 `ROUND9_REPORT.md`“待 Review Gate 决定”第 1–4a 项(1.16 节 Y1、1.17 节 Z6)。
- Implementation 阶段 A:1.18 节 AA1、AA2、AA6、AA7,1.19 节 AB1、AB2 须由 Review Gate 决定;AA9(命令路径)、AA11(记录字段)、L4 的语料含 `anchor_text`、1.21 节 AD14(修复提交没有调用 data-auditor)请 Review Gate 备案。都列于 `IMPL_A_REPORT.md`“待 Review Gate 决定”(第 1–8 项)。
- Implementation 阶段 B:1.22 节 BA1–BA3、BA7、BA9,1.23 节 BB2、BB4、BB6,1.24 节 BC1 须由 Review Gate 决定;1.25 节 BD10 请 Review Gate 备案。都列于 `IMPL_B_REPORT.md`“待 Review Gate 决定”(第 1–5 项)。BB1 / BC2 / BD8(ST10 凭据与“TEST 只评一次”)是阶段 C 的硬性前提。
- Implementation 阶段 B 报告提交:1.26 节 BE1(待决第 3 项的运行清单)与 BE6(推送记录的证据提交不经审查,待决第 6 项)请 Review Gate 决定或确认。
