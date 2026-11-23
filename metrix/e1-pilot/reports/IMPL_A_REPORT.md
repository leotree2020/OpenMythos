# E1-PILOT Implementation 阶段 A 报告

- 指令:`tasks/IMPLEMENTATION_TASK_ORDER_V1.md`(Implementation Task Order V1,Owner 批准 2026-11-23 01:09 JST;本阶段 = 第 10 节表中 A 行)。Owner 在下达时另给三条(消息原文 `tasks/IMPL_A_OWNER_MESSAGE.md`,报告提交审查后补入):任务书原文与阶段 A 的第一个工作提交一起提交;直接在 `metrix-e1-pilot-protocol-v1` 上工作,只做快进推送,不 force push,不推送标签,不使用会话默认分支,本阶段不经 PR;阶段 A 结束后停下,提交报告,等待下一阶段指令。
- 执行会话:session_01J5mxaX4SHCYCGz74623D33。会话从会话分支 `claude/dreamy-johnson-7tfb25`(`155430a`)启动;收到任务书之前(上一轮回复中查找任务书时)曾建本地分支 `metrix-work` 查看文件,没有提交,随后删除(`impl_a/t7_report_commit.txt` 第 3 部分的 `git reflog` 与 `git branch --list`);本地分支 `metrix-e1-pilot-protocol-v1` 设为 `origin/metrix-e1-pilot-protocol-v1`(第 9 轮的 `8149d872`)后在其上工作(`impl_a/t0_copy_check.txt` 的 `git reflog`)。会话分支没有使用。没有改写任何已有提交。
- 运行环境:Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,Ubuntu 24.04.5,没有 nvidia 设备(`impl_a/t7_report_commit.txt` 第 3 部分),`torch.cuda.is_available()` 为 False(`impl_a/t1_lock.txt`)。Python 3.13.18;依赖只从 `requirements.lock` 按哈希安装到会话临时目录的 venv。
- 中断:第 2 轮的两份审查(2026-11-22 16:54 UTC 调用,调用文字写于 16:54:17 / 16:54:27)因 API 额度限制(HTTP 429)中止;容器于 2026-11-23 01:09:37 UTC 重启,工作区、暂存区与会话临时目录都保留。01:10 UTC 核对暂存区与第 2 轮审查输入逐字节相同、两个 agent 的 frontmatter 与 tools 行相同后,约 01:11 UTC 用 SendMessage 让同一 subagent 从中断处续做(续做后 data-auditor 的第一份输出写于 01:11:15),续做消息第一句按 `metrix/CLAUDE.md` 第 5 节第 6 条(`reviews/602a39e8…/interruption_round2.txt`、`resume_message_*_round2.txt`、`extract_log.txt`)。
- 停止钩子在审查完成前多次要求提交推送;按 `metrix/CLAUDE.md` 第 5 节,我在每次提交的审查结论出来之前没有提交(这一点没有原始输出)。
- 没有训练、没有评测、没有加载任何模型权重(没有下载权重文件;只下载了 4 个分词器文件、parcae `tokenizer.json`、锚文本 parquet)、没有使用 GPU。没有生成、读取或统计 TEST:`eval_sets.jsonl` 只对整个文件求哈希、按行前缀读 `split` 字段并计数,非 dev 行不解析、不解码(指令第 3 节第 3 项:对整个文件求哈希不算统计;协议第 3 节:解析 `split` 字段、计数不算读取);没有实例化任何 TEST 问句。
- 原始输出在 `reports/impl_a/`,命令行由 `round5/logrun.sh` 记录;工作提交两轮审查的调用文字、输入与原文在 `reviews/602a39e8c4be1e1efa682a26637ad94fb919b7b8/`,修复提交的审查在 `reviews/219c4a60b1e2274fe57a7cdbe9d9606d814a8ab5/`;data-auditor 的脚本与 stdout 在 `audit/ia_*`、`audit/stdout/impl_a/`。

## 结论一览

| 阶段 A 内容 | 状态 | 证据 |
|---|---|---|
| 阶段开始:比对 `~/.claude/` 副本,读本文件与上一阶段报告 | 完成。用户级副本仍是旧版(与第 7–9 轮相同原因),以仓库为准;两个 agent 的 frontmatter 与 tools 行相同,按 `metrix/CLAUDE.md` 第 5 节第 6 条继续 | `impl_a/t0_copy_check.txt` |
| 本文件原文入库 | 完成,与工作提交一起 | `tasks/IMPLEMENTATION_TASK_ORDER_V1.md` |
| `requirements.lock` | 完成:torch 2.11.0、transformers 5.22.2(协议第 0 节),全部带哈希;`--require-hashes --no-deps` 安装成功,`pip check` 通过;解释器 CPython 3.13.18 写入锁文件并由测试核对 | `impl_a/t1_lock.txt`;`tests/test_environment.py` |
| `frozen.py` | 完成:读 `PROTOCOL_FROZEN` 当前有效节,用 `git cat-file` 读冻结提交 `87a244db…` 的四个文件并核对哈希,12 行数据哈希与冻结提交 manifest 逐一交叉核对,模板哈希重算;任何不一致 ST12 | `impl_a/t2_fetch_generate.txt` 第 17 行(`load()` 通过;交叉核对与模板重算在 `load()` 中,失败即抛出,由此隐含,没有单独打印);`tests/test_st12.py` |
| `data.py` | 完成:四个冻结哈希全部复现(fact `406c8801…`、train_S `686fdd2f…`、candidates `e5d15c99…`、锚文本 `8828bc4f…`);与参考脚本逐字节相同;五次生成 gen1–gen5(不同进程、不同 `PYTHONHASHSEED`、工作提交前后与修复提交的代码)逐字节相同 | `impl_a/t2_fetch_generate.txt`;`tests/test_data_hashes.py` |
| `leakage.py`(不含 TEST 部分的执行) | 完成:按协议第 3 节命令运行,L1–L6 Gate 0 部分全部在上限内(L2 最大 0.2,与 manifest 的撰写值相同) | `impl_a/t3_leakage.txt` |
| 单元测试 1、10 | 全部通过(连同其它测试共 51 项) | `impl_a/t4_pytest.txt` 第二次运行(工作提交);`impl_a/t6_fix_commit.txt`(修复提交) |
| 审查 | 工作提交:code-reviewer 第 1 轮 **PASS**(无 BLOCKER;2 MAJOR、12 行 MINOR)、第 2 轮 **PASS**(无 BLOCKER;新 8 MINOR);data-auditor 第 1、2 轮 **PASS**(仅作参考,`metrix/CLAUDE.md` 第 10 节)。修复提交:code-reviewer **PASS**(无 BLOCKER、无 MAJOR;新 4 MINOR)。报告提交:code-reviewer **PASS**(无 BLOCKER;2 MAJOR、12 MINOR,按第 7–9 轮先例在本提交中改正或登记) | `reviews/602a39e8…/`;`reviews/219c4a60…/` |
| 提交与推送 | 工作提交 `602a39e8`、修复提交 `219c4a60` 已快进推送 `metrix-e1-pilot-protocol-v1`,没有推送标签;报告提交(本文件所在提交)随后推送 | `impl_a/t5_commit_push.txt`;`impl_a/t7_report_commit.txt` |

## 提交

| 提交 | 内容 |
|---|---|
| **`602a39e8c4be1e1efa682a26637ad94fb919b7b8`(工作提交,2026-11-23 01:17:08 UTC,父提交 `8149d872`)** | 任务书原文;`src/metrix_e1/`(`frozen.py`、`data.py`、`leakage.py`、`errors.py`、`_cli.py`)与协议接口转接层 `src/metrix/e1_pilot/`;`tests/`(4 个测试文件与 `conftest.py`);`requirements.lock`;`reports/impl_a/t0`–`t4`。内容即第 2 轮两份审查读到的暂存内容(`t7` 第 1 部分逐字节比对) |
| **`219c4a60b1e2274fe57a7cdbe9d9606d814a8ab5`(修复提交,2026-11-23 01:25:36 UTC)** | 第 2 轮 code-reviewer 新提 MINOR 中 N1、N3、N5–N8 的修复(`frozen.py` 与三个测试文件);`impl_a/t5_commit_push.txt`(工作提交、metrix/ 以外检查、工作提交的推送输出)、`t6_fix_commit.txt` |
| 报告提交 | 本文件;`tasks/IMPL_A_OWNER_MESSAGE.md`;`reviews/602a39e8…/`(含报告提交审查的调用文字、输入、原文与审查后改动的差异 `report_commit_post_review.diff`)、`reviews/219c4a60…/`;`audit/ia_*` 与 `audit/stdout/impl_a/`(data-auditor 写入,00–22);`DEFERRED_MINORS.md` 1.18–1.21 节与第 3 节一条;`impl_a/t7_report_commit.txt`(第 1 部分:工作提交与审查输入逐字节比对;第 2 部分:修复提交的推送;第 3 部分:审查文件的副本核对与直接提取、环境、peft 发布时间、本地分支) |

报告提交本身的提交后检查与推送输出,推送时立即用 `round5/logrun.sh` 写入 `impl_a/t8_report_push.txt`(工作区,不在本提交中),随下一阶段的第一个提交原样入库(指令第 3 节第 6 项);最终回复中给出同一输出。

## 交付物与实现

### `frozen.py`(协议第 0 节、第 11 节 ST12、`PROTOCOL_FROZEN`;指令第 3 节第 1、2 项)

- 当前有效版本:从 `PROTOCOL_FROZEN` 第 3 行“当前有效版本：v1.1”与“## v1.1(当前有效)”一节读出;该节的冻结提交 `87a244db28a901f9e89282b50df76778ab5c2887`。
- 比对范围 (2):四个文件用 `git cat-file blob 87a244db…:<路径>` 读出,SHA-256 与该节列出的值比对。包内一切协议取值都来自这四份字节,不读工作区。
- 比对范围 (1):该节引用 v1 一节“全部数据哈希”表的 12 个值(指令第 3 节第 1 项:含 parquet、分词器文件、`eval_sets.jsonl` 等文件字节哈希)。读表后,每个值再与冻结提交 manifest 中对应字段比对。文件字节哈希在使用前核对(`data.check_inputs`);四个内容哈希在生成后与 `verify`、泄漏命令中核对(`Frozen.check_data_dir`,fact 按协议第 2.2 节的比对方法;每步开始前的调用由阶段 C 的 `run_pilot.py` 接线);模板集合哈希由 32 个模板重算。
- 规则字符串(规范化序列、JSONL、`rng_rule`、模板归一化)与冻结 manifest 中的原文逐字比对,不同即停。
- 超出范围 (2) 的一项(待 Review Gate 决定第 1 项):工作区四个文件也与冻结提交比对。
- 协议第 0 节库版本:`check_library_versions` 比对 `DATA_MANIFEST.json model.libraries`(torch、transformers),不同即 ST8(BLOCKED);数据生成前执行。

### `data.py`(协议第 2 节、第 8 节第 1 步)

- 生成第 2.8 节的 8 个非 TEST 文件,按协议第 0 节规范化写出(`byte_sha256` = `canonical_sha256`)。生成顺序:锚文本 → 名字(锚文本规则)→ TRAIN/S/Y → DEV 问句 → 候选 → general DEV。
- 迁移自 `round2/names.py`、`gen_facts.py`、`anchor_check.py`、`y_ratio.py`,`round7/gen_s_cands.py`,`round5/l6_check.py`。`tests/test_data_hashes.py::test_byte_identical_to_reference_scripts` 在同一环境中运行这些参考脚本,比对 facts(规范化列表)、锚文本、`train_S.jsonl` 与 `candidates.json`(原始字节)、general DEV(domain、doc_id、ids、text):逐字节相同。
- 协议数值都从冻结 manifest 读取;manifest 把数值写在句子里的(如 “first 512 documents … at least 600 characters”),整句全匹配后取数,句子不同即停(IMPLEMENTATION_FAIL,“实现与本协议不一致”)。
- 结果(`impl_a/t2_fetch_generate.txt`):四个冻结哈希全部等于 `PROTOCOL_FROZEN`;Y/F token 数 1,889 / 2,260,比值 1.1964(协议第 2.6 节所写的值,区间 [0.80, 1.25]);第 2.5 节暴露匹配检查通过(`generate` 中的 `check_exposure` 失败即抛出,由 RESULT: PASS 隐含,没有单独打印);`eval_sets.jsonl` 行前缀计数 dev 400、test 800,解析与解码的行 100(全为 dev)。
- 8 个文件的哈希(gen1 = gen2 = gen3 = gen4 = gen5;gen5 见 `impl_a/t6_fix_commit.txt`):

| 文件 | 行数 | `byte_sha256` = `canonical_sha256` |
|---|---|---|
| `facts.jsonl` | 160 | `e05561ac2d49dcc3c8f59743c5df64151983a540a32ae135fd1b10f5e0fdc828`(fact 值 `406c8801…` 按第 2.2 节从该文件读回计算) |
| `train_F.jsonl` | 120 | `3aa9ab3ca313c0a1113b91e927af51342c915e3e40dd2f20992f3d9e59b0e373` |
| `train_S.jsonl` | 120 | `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e` |
| `train_Y.jsonl` | 240 | `c7430cadb2b06dd5c144af381a8183d4c186f27f2b5acfa9d8d39da0b7626d15` |
| `dev_qa.jsonl` | 320 | `9761eb60d6c9155c2f56394aa228b1e9dfea0ae3926ab50cb21d903108bc7fde` |
| `candidates.json` | 160 键 | `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705` |
| `general_dev.jsonl` | 100 | `957666920c91ef5b9328984d26ed0628c8a80b439d461bea49b54c2235635e73` |
| `anchor_text.jsonl` | 512 | `2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5`(锚文本值 `8828bc4f…` 按 manifest 规则从 `text` 字段计算) |

  这些文件不入库(指令第 4 节;它们由固定来源完全决定)。`DATA_MANIFEST.json files` 与 `SPLIT_MANIFEST.json split_sha256` 没有写入(红线 1;按协议第 8 节第 1 步在正式运行时写入)。
- 记录字段(协议未规定,见待决第 4 项):`train_F` `{fact_id, template_id, text}`;`train_Y` `{fact_id, template_id, kind, text}`(每条 learned fact 先 Y_ENTITY 后 Y_ANSWER);`dev_qa` `{fact_id, template_id, question}`(fact 顺序,再按模板顺序);`anchor_text` `{doc, source_row, ids, text}`(`ids` 为送入模型的至多 128 个 id,`text` 为其解码);`general_dev` `{domain, doc_id, ids, text}`(`ids` 为送入模型的至多 256 个 id)。`facts.jsonl` 为第 2.2 节的 6 个字段;`train_S.jsonl`、`candidates.json` 按第 2.5、2.6 节。
- `verify`(ST12 检查,供每步开始前调用;`run_pilot.py` 的接线在阶段 C):(a)输入文件的文件字节哈希;(b)四个内容哈希;(c)8 个文件与按冻结输入重新生成的结果逐字节相同(没有冻结哈希的文件也因此受保护;待决第 2 项)。
- 下载:`python -m metrix_e1.data fetch` 只请求上述 6 个文件(模型仓库只请求 4 个分词器文件),下载后逐一核对冻结哈希。

### `leakage.py`(协议第 3 节;第 8 节第 2 步与 G0.1)

- 命令即协议第 3 节的接口:`PYTHONPATH=metrix/e1-pilot/src python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --out <DATA_DIR>/leakage_report.json`(待决第 3 项);全部在上限内才退出 0。命令先核对 `--split-manifest` 与冻结提交相同、`--data` 的四个内容哈希(ST12 范围 (1)),再做检查。
- 口径:L1 跨集合共享的归一化哈希数;L2 跨集合模板对的词 4-gram Jaccard 最大值;L3a、L3b 不分大小写子串计数(语料:train_F、train_S、train_Y、anchor_text);L4 DEV 问句逐字出现次数(语料同上,含 anchor_text:arm A 在锚文档上训练);L5 fact_id 交集 + 320 个字符串的重复数;L6 每篇文档内取词 13-gram(`str.split()`),锚文本与 general DEV 各自合并后求交,文本为送入模型的 id 的解码;token-id 13-gram 只报告。上限与 n 从冻结 `SPLIT_MANIFEST.json` 读取。
- 结果(`impl_a/t3_leakage.txt`):L1 0、L2 0.2(capital.TRAIN.1 / capital.DEV.1)、L3a 0、L3b 0、L4 0、L5 0、L6 0,token-id 13-gram 0;RESULT: PASS。与第 6 轮 `round6/t2_l6_check.txt`、manifest 的 `authoring_result` 一致。
- TEST 部分:本阶段不执行,命令也不能执行。计数函数只接收内存中的列表、不读文件,第 8 步的接线(在 TEST 生成器的前提条件之后)留给后续阶段。

### 单元测试(指令第 6 节第 1、10 项;工作提交 `impl_a/t4_pytest.txt` 第二次运行、修复提交 `impl_a/t6_fix_commit.txt`,各 51 项全部通过)

- **第 1 项**(`test_data_hashes.py`):`test_four_frozen_hashes` 从写出的文件读回,重算四个哈希,与 `PROTOCOL_FROZEN` 全值及指令给出的前缀比对;另有规范化写出、行数(期望值为协议原文写出的数,不经被测代码)与 Y/F token 数(读自冻结协议正文)、无 TEST 文件、与参考脚本逐字节相同、泄漏 Gate 0 部分通过。
- **第 10 项**(`test_st12.py`,每项断言触发的是哪一条检查):冻结提交中的四个文件各改一个字节(在临时目录中按真实冻结提交的字节建一个 git 仓库,真实仓库不动);工作区四个文件各改一个字节;`PROTOCOL_FROZEN` 中各改一个哈希的一位(`DATA_MANIFEST.json` 的文件哈希;表中 fact 的数据哈希);`eval_sets.jsonl`、4 个分词器文件、parcae `tokenizer.json`、锚文本 parquet 各改一个字节;8 个数据文件各改一个字节;命令层面 `data verify` 打印 RESULT: FAIL 并非 0 退出。正向对照:换行转换(CRLF,含 `PROTOCOL_FROZEN` 本身)与第 1 步写入的字段不触发。`PROTOCOL_FROZEN` 的说明文字(不含任何取值的字节)不在覆盖范围内。
- 其它:`test_environment.py`(解释器等于锁文件所写、库版本、ST8);`test_leakage.py`(每项检查都能检出人为植入的违规;13-gram 不跨文档;命令在违规时 RESULT: FAIL、退出 1;数据被改时 ST12 先停、不写报告)。
- 运行:`METRIX_INPUTS_DIR=<fetch 的目录> python -m pytest metrix/e1-pilot/tests`(没有该目录时相关测试失败,不跳过)。

### `requirements.lock`(指令第 5 节“依赖”)

- 直接依赖:torch 2.11.0、transformers 5.22.2、tokenizers 0.23.3、huggingface_hub 2.4.0、pyarrow 26.0.1、jinja2 3.1.6、pytest;传递依赖由 `uv pip compile --generate-hashes --python-version 3.13 --python-platform x86_64-manylinux_2_28 --exclude-newer 2026-11-08T00:00:00Z` 解析(只用发布满两周的版本)。
- 解释器:`# python: CPython 3.13.18`(参考实现用的 `random.Random` 所在版本),`test_environment.py` 核对。
- 不用 peft:arm L 的 LoRA 将在阶段 B 于包内实现(目标模块、alpha = 2 × rank、dropout 0、B 初始为 0,由单元测试第 4 项覆盖),因此不锁定。原因:依赖更少;peft 0.22.0 发布于 2026-11-19,0.21.3 发布于 2026-11-13,都晚于锁文件只取发布满两周版本的截止日 2026-11-08(`impl_a/t7_report_commit.txt` 第 3 部分)。
- PyPI 的 torch 2.11.0 Linux 轮子基于 CUDA 13.0(`torch 2.11.0+cu130`),A100 主机须有支持 CUDA 13.0 的驱动(写入阶段 C 的 RUNBOOK;登记 1.18 节)。

## 审查

审查原文都由 `round6/review_extract.py` 从本会话的 subagent 记录原样提取;`extract_log.txt` 核对了每份调用文字与 subagent 收到的第一条消息相同。每次调用前都比对了 frontmatter 与 tools 行(`preflight_tools_check*.txt`)。审查原文中 `…/scratchpad/review_work/…`、`…/review_fix/…`、`…/review_report/…` 形式的路径(会话临时目录)对应仓库中的文件:`review_work/X` → `reviews/602a39e8…/X`,但第 1 轮的 `review_work/review_input.diff` → `reviews/602a39e8…/review_input_round1.diff`(第 2 轮开始前改名);`review_fix/X` → `reviews/219c4a60…/X`;`review_report/code-reviewer_prompt.txt`、`review_input.diff`、`preflight_tools_check.txt` → `reviews/602a39e8…/code-reviewer_prompt_report-commit.txt`、`report_commit_input.diff`、`preflight_tools_check_report-commit.txt`。仓库副本与临时目录原件逐一 `cmp` 相同,报告原文又从 subagent 记录直接提取到仓库路径一次,正文的 sha256 与 `extract_log.txt` 所记相同(`impl_a/t7_report_commit.txt` 第 3 部分)。修复提交审查原文中的 “t6:NNN”“t5:NNN” 多数是 `reviews/219c4a60…/review_input.diff` 的行号:t6 的文件行号 = diff 行号 − 101,t5 = diff 行号 − 17(审查方在报告提交审查中指出)。

### 工作提交第 1 轮(`reviews/602a39e8…/review_input_round1.diff`)

- code-reviewer:**PASS**,无 BLOCKER;2 MAJOR、12 行 MINOR(审查方在 (a)–(f) 中另列 (d)、(e)、(f) 三项判断)(`code-reviewer_round1.md`)。
- data-auditor:**PASS**(仅作参考)。自写 `audit/ia_00`–`ia_10`,重新下载固定文件;四个冻结哈希三方一致(auditor、从 Executor 文件读回、冻结值);没有冻结哈希的 5 个文件内容逐条一致;L1–L6 与 `leakage_report.json` 逐项一致;候选可行性最小 5、池最小 4;split 正确(`data-auditor_round1.md`,`audit/stdout/impl_a/00`–`11`)。“不构成 BLOCK”的 5 条说明中,协议层面的 2 条与已登记的 S12 列入 1.18 节 AA6–AA8。

处理(指令第 9 节:影响协议一致性、数据、指标或隔离的必须修,其余登记;属于协议未覆盖、需要解释的,不改代码,交 Review Gate,见“待 Review Gate 决定”):

| 第 1 轮条目 | 处理 |
|---|---|
| MAJOR (a) 工作区比对超出 ST12 范围 (2);换行转换会误判;manifest 排除范围比协议窄 | 修:协议文件与 `SEARCH_SPACE.json` 做 CRLF→LF 后比;两个 manifest 去掉协议所说的整个 `files`、`split_sha256` 字段后按解析结果比;测试加正向对照。是否保留这项比对交 Review Gate(待决第 1 项) |
| MAJOR Python 未锁定补丁版本 | 修:锁文件写 `# python: CPython 3.13.18`,测试核对;生成时输出解释器与库版本 |
| MINOR(即 (b))重新生成比对记为 ST12 | 不改代码;交 Review Gate 确认状态标签(待决第 2 项) |
| MINOR `splitlines()` 会在 U+2028 等处断行 | 修:JSONL 只按 `\n` 切分(`frozen.parse_jsonl`),测试覆盖 |
| MINOR 死代码与未用项 | 修:删除 `TEMPLATE_SETS`、`load_qwen_tokenizer` 的 `fz`、`anchor_source` 中的 sha;`Frozen.seeds` 改为被使用;`protocol_text`、`source_sha256` 保留并注明阶段 B 用途(登记 1.18 节) |
| MINOR `E1P`、L/U 写在代码里 | 修:从 `fact_id_format` 与 `SPLIT_MANIFEST.json fact_ids` 读取并交叉核对 |
| MINOR 测试写死协议数值 | 修:Y/F token 数读自协议正文;行数先改为由 manifest 计算,第 2 轮 N5 指出期望值经被测代码计算、不独立,修复提交改为协议原文的数(注明出处) |
| MINOR `match="ST12"` 过宽 | 修:断言具体检查的信息 |
| MINOR docstring 与 `PROTOCOL_FROZEN` 覆盖范围不符 | 修 docstring;覆盖范围写在上文“单元测试” |
| MINOR 泄漏命令不核对 `--data` | 修:先做 ST12 范围 (1) 检查,测试覆盖 |
| MINOR 锁文件引用尚不存在的报告 | 修:原因直接写在锁文件注释中 |
| MINOR torch cu130 需要 CUDA 13 驱动 | 登记(阶段 C 的 RUNBOOK) |
| MINOR `frozen.py` 尚未提供 G0/ST 门槛 | 登记(阶段 B 从协议正文解析,不写死) |
| MINOR 生成前没有核对库版本 | 修:`check_library_versions`(ST8),生成前执行,测试覆盖 |

### 工作提交第 2 轮(修改后的暂存内容,`reviews/602a39e8…/review_input_round2.diff`、`review_fixes_round2.diff`)

- code-reviewer:**PASS**,无 BLOCKER(`code-reviewer_round2.md`)。第 1 轮 MAJOR #2 已修且正确;MAJOR #1 的 ①②(换行转换、排除范围)已修且正确,③ 交 Review Gate;MINOR 中“已修且正确”的为 splitlines、死代码、E1P/L/U、断言、docstring、泄漏命令的 ST12、库版本;测试写死数值一条“已修但有问题”(改由被测的 `params` 计算期望值,即 N5);锁文件的悬空引用转移到 `frozen.py` docstring(即 N7)。新提 N1–N8。
- data-auditor:**PASS**(仅作参考)。对改动后重新生成的 gen4 重做:输入三方相同、暂存源码的哈希等于 gen4 生成前打印的值;四个冻结哈希三方一致;5 个无冻结哈希文件内容一致;`leakage_report.json` 47 个叶子字段一致;split、候选可行性一致;gen4 与 gen1 的 8 个文件逐字节相同(`data-auditor_round2.md`,`audit/stdout/impl_a/12`–`22`)。
- 处理:N1、N3、N5、N6、N7、N8 在修复提交 `219c4a60` 中修;N2 随第 1 轮 MAJOR (a) ③ 交 Review Gate(待决第 1 项);N4 交 Review Gate 确认(待决第 7 项)。登记于 1.19 节。
- 工作提交 `602a39e8` 是第 2 轮读到的暂存内容,没有改动(提交前核对见 `interruption_round2.txt`;提交后 `git diff 8149d872 602a39e8` 与审查输入逐字节相同,`impl_a/t7_report_commit.txt` 第 1 部分)。

### 修复提交 `219c4a60`(`reviews/219c4a60…/review_input.diff`)

- code-reviewer:**PASS**,无 BLOCKER、无 MAJOR;N1、N3、N5、N6、N7、N8 逐条“已修,修法正确”;核对 `t5`:快进推送、没有推送标签、metrix/ 以外检查 PASS(`reviews/219c4a60…/code-reviewer.md`)。新提 4 条 MINOR(证据、引用与登记),在本报告提交中处理,见 1.20 节。
- `git commit` 之前记录了暂存区与审查输入逐字节相同(`reviews/219c4a60…/precommit_check.txt`)。
- 修复提交没有调用 data-auditor:改动只在 `frozen.py`(`PROTOCOL_FROZEN` 的读入、一处异常类型、docstring)与测试,没有改数据生成、split、候选、打分或评测代码(`metrix/CLAUDE.md` 第 5 节第 2 条);改动后重新生成的 gen5 与 gen1 逐字节相同(`impl_a/t6_fix_commit.txt`)。N1 改的是 `PROTOCOL_FROZEN` 数据哈希表(ST12 范围 (1) 的参照值)的读入,是否属于“涉及数据”是判断问题(待决第 8 项)。
- 改动后:pytest 51 项通过;verify、协议泄漏命令 RESULT: PASS(`impl_a/t6_fix_commit.txt`)。

### 报告提交(`reviews/602a39e8…/report_commit_input.diff`)

- code-reviewer:**PASS**,无 BLOCKER;2 MAJOR、12 MINOR(`reviews/602a39e8…/code-reviewer_report-commit.md`)。核对一致的部分:提交号、时间、快进推送、标签不变、8 个文件的行数与哈希、四个冻结哈希、Y/F、L1–L6、pytest 次数、各轮审查条数与结论、`DEFERRED_MINORS.md` 的来源行号、提取记录与调用文字、TEST 无内容。
- 按第 7–9 轮的先例,报告、登记与证据方面的问题在本提交中改正,被审查的版本与提交版本的差异见 `reviews/602a39e8…/report_commit_post_review.diff`;两条 MAJOR:审查文件的仓库副本没有核对记录 → `t7` 第 3 部分补 `cmp`、直接提取到仓库路径与正文哈希比对;报告提交的推送输出只在回复中 → 推送时立即写入 `impl_a/t8_report_push.txt`。逐条处理见 `DEFERRED_MINORS.md` 1.21 节。本提交没有再请审查。

## 待 Review Gate 决定

以下各项没有改协议;冻结后改协议须开新版本。

1. **工作区副本的比对**(第 1 轮 MAJOR (a) ③;第 2 轮 N2):`frozen.load()` 在协议 ST12 比对范围 (2)(`git cat-file`)之外,还把工作区的四个文件与冻结提交比对,不同按 ST12 停。依据是指令第 6 节第 10 项“篡改任一冻结文件……的一个字节，运行立即停止”;协议范围 (2) 只写 `git cat-file`。包内取值只来自冻结提交,这项比对不改变任何计算。两个 manifest 按解析结果比较(第 8 节第 1 步会改写它们),所以空白、数字写法一类的一字节改动不会停(N2)。请决定保留(现状)还是删除。
2. **没有冻结哈希的数据文件**(第 1 轮 MINOR (b)):`train_F`、`train_Y`、`dev_qa`、`general_dev` 与 `anchor_text` 的 `ids` 没有冻结哈希,第 1 步写入 manifest 的哈希又不在 ST12 范围内。`data.verify` 把它们与按冻结输入重新生成的结果逐字节比对,不同记为 ST12(BLOCKED)。这满足指令第 6 节第 10 项“篡改任一……数据文件”,但 ST12 的标签超出协议范围 (1) 的字面。请确认状态标签。
3. **协议第 3 节的命令路径**:`python -m metrix.e1_pilot.check_leakage` 不能对应仓库中的目录(`metrix/e1-pilot` 有连字符),现放在 `metrix/e1-pilot/src/metrix/e1_pilot/`(无逻辑的转接层,实现在 `src/metrix_e1/leakage.py`),须 `PYTHONPATH=metrix/e1-pilot/src`,依赖仓库根 `metrix/` 没有 `__init__.py`(namespace package)。code-reviewer 判为与协议、指令一致;阶段 C 写入 RUNBOOK。请备案。
4. **记录字段**(第 1 轮 (f)):协议第 2.8 节说字段见 `DATA_MANIFEST.json`,但 manifest 对 `train_F`、`train_Y`、`dev_qa`、`general_dev`、`anchor_text` 只写了 content。所选字段见上文 `data.py` 一节,请备案。
5. **data-auditor 的两条协议层面说明**(登记 1.18 节):L2 中两个模板都不足 4 个词时 Jaccard 按 0 计(协议未规定;按 1 计则 L2 超限);Y/F token 比按“每个序列加 1 个 `<|endoftext|>`”计(协议给出的 1,889 / 2,260 只有这样才能复现,但协议没写口径)。
6. **L4 的语料**(第 1 轮 (c),code-reviewer 判为与协议一致、比只查 train_* 更严):包括 `anchor_text`。请备案。
7. **库版本的比对方法**(第 2 轮 N4):`check_library_versions` 比对发行包元数据的版本,并忽略 `+local` 标签(`2.11.0+cu130` 视为 2.11.0,`2.11.0+cpu` 同样),与 PEP 440 的 `==` 一致;本环境 `torch.__version__` 为 `2.11.0+cu130`,元数据版本为 `2.11.0`。这是对协议第 0 节“不一致即 BLOCKED”的执行解释,请确认;裁决前不视为关闭。阶段 B 的 `record.py` 同时记录两者。
8. **修复提交没有调用 data-auditor**(报告提交审查 MINOR):修复提交改了 `PROTOCOL_FROZEN` 数据哈希表的读入(CRLF → LF,变量改名),这张表是 ST12 范围 (1) 的参照值;数据生成等代码没有改,gen5 与 gen1 逐字节相同。是否属于 `metrix/CLAUDE.md` 第 5 节第 2 条的“涉及数据”是判断问题,请备案。

## 留给阶段 B、C 的事项

- 阶段 B:从冻结协议正文解析 G0、ST 门槛与训练契约数值(`frozen.protocol_text`),不写死;arm L 的 LoRA 在包内实现;`record.py` 写入 `PROTOCOL_FROZEN` 字节哈希(`FrozenRecord.source_sha256`,注明是工作区原始字节的哈希,1.20 节 AC2)、解释器与库版本(元数据版本与 `__version__`);泄漏检查 TEST 部分的接线放在 TEST 生成器的前提条件之后(协议第 8 节第 8 步“对 TEST 运行 L3–L5”中 L3、L5 对 TEST 的具体含义,届时如协议未覆盖即停下报告)。
- 阶段 C:RUNBOOK 写明 `PYTHONPATH=metrix/e1-pilot/src`、CUDA 13.0 驱动要求、`python -m pip install --require-hashes --no-deps -r requirements.lock`、CPython 3.13.18 的获取;第 1 步写 manifest 时以冻结提交的字节为底(冒烟模式不写正式 manifest)。

## 推送

- 工作提交 `602a39e8`:`8149d872..602a39e8`,快进;推送前后的远端状态与推送输出在 `impl_a/t5_commit_push.txt`(随修复提交入库)。
- 修复提交 `219c4a60`:`602a39e8..219c4a60`,快进;推送前后远端的分支与 `metrix-*` 标签(两个标签不变)在 `impl_a/t7_report_commit.txt` 第 2 部分(随本提交入库)。
- 本报告提交:提交前的暂存文件清单、提交后的 metrix/ 以外检查与推送输出,推送时立即写入 `impl_a/t8_report_push.txt`(工作区,不在本提交中),随下一阶段的第一个提交原样入库(指令第 3 节第 6 项);最终回复中也给出。会话容器在下一阶段之前被回收时,该文件随之丢失,届时以 `git ls-remote` 重新核对远端状态。
- 没有 force push,没有推送或创建任何标签,没有使用会话默认分支 `claude/dreamy-johnson-7tfb25`,没有开 PR。
