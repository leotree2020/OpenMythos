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
