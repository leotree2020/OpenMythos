# E1-PILOT 登记不修的 MINOR

- 依据:第 6 轮指令(`tasks/ROUND6_TASKS.md`)总原则“只修影响数据、指标、门槛或可复现性的问题;其余 MINOR 只登记不修”,以及第 6 项。
- 范围:截至第 6 轮(工作提交 `481a6f0f`、`599230f9`,修复提交 `2620f306`),各轮审查与报告中列为 MINOR、至今没有修的问题;第 6 轮两轮审查中我没有修的 MAJOR,如只涉及注释或展示、不影响数据与判定,也列在这里(H1),其余 MAJOR 见 `ROUND6_REPORT.md`“待 Review Gate 决定”。
- 来源记法:`R5-CR:20` = `reviews/2724144b…/code-reviewer.md` 第 20 行;`R5-RC:27` = `reviews/2724144b…/code-reviewer_report-commit.md` 第 27 行;`R6-CR` = 本轮 `reviews/599230f9…/code-reviewer.md`;`R6-DA` = 同目录 `data-auditor.md`;`R6b-CR` = `reviews/2620f306…/code-reviewer.md`;`R4 待决 N` = `ROUND4_REPORT.md`“待 Review Gate 决定”第 N 项;`R5 待决 N` 同理。
- “不修的理由”一栏说明它为什么不影响数据、指标、门槛或可复现性。凡是影响这四者、但要改协议才能修的,不在本表,列在本文件末节,交 Review Gate。
- 状态写明“已解决”的条目也列在后面,便于核对没有遗漏。

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

## 2. 已在第 5、6 轮解决(核对用)

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

## 3. 不按 MINOR 登记、交 Review Gate 的开放项

下面几项原来有的标为 MINOR,但会影响指标或可复现性,修它们要改协议或改 auditor 的文件,Executor 不能自行处理。详见 `ROUND6_REPORT.md`“待 Review Gate 决定”。

- `<think>`(151667)与 `</think>`(151668)不是特殊 token,`skip_special_tokens=True` 去不掉,协议没有写(R5-CR:32 前半;R5 待决 7 第 1 点)。影响 EM。
- 第 2.6 节 S 的置换与第 2.5 节的候选抽取没有写死调用方式,只凭协议文字不能逐字节复现 `train_S.jsonl` 与 `candidates.json` 的哈希(R4 待决 8;R5 待决 8)。影响可复现性。
- 第 6 轮第 2 项“所有检查脚本”是否包括 auditor 已入库的旧脚本(A4、A6)。
