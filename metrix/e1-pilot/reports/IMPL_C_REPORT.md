# E1-PILOT Implementation 阶段 C 报告

**状态:IMPLEMENTATION_READY(Implementation Task Order V1 第 13 节;阶段 C 验收见文末“阶段 C 验收”)。** C5 按 Review Gate 2026-11-28 对 C4 待决事项的裁决(`tasks/IMPL_C5_RULING.md`)只修正 RUNBOOK(一次纯文档提交,没有改代码),见 C5 节;状态仍为 IMPLEMENTATION_READY。C4 按 Review Gate 2026-11-27 对 C2、C3 待决事项的裁决(`tasks/IMPL_C4_RULING.md`)完成:代码提交 `a09e154e`(ST11 读 B17 估算 + checkpoint 开销,B17 修订)与文档提交(RUNBOOK 等),见 C4 节;状态仍为 IMPLEMENTATION_READY。C1 完成(第二次送审通过:工作提交 `ae60e0f7`、修复提交 `b48fe842`);C2 完成(工作提交 `5219ff77`,修复提交 `49fc9a35`、`dd65a361`、`a0e04d1f`,见 C2 节);C3 完成(`RUNBOOK_A100.md` 与本报告,见 C3 节)。C1 结束时曾因审查额度用尽在 C1 与 C2 之间停下;Owner 2026-11-27 的指令(`tasks/IMPL_C2_OWNER_MESSAGE.md`)之后,C2、C3 在第三个阶段 C 会话中执行(C2 节开头)。C1 的第一次送审在连续 3 轮未 PASS 后停止(`5f5cd51e`,只提交了证据);Review Gate 对 C1 的裁决(2026-11-25,`tasks/IMPL_C1_RULING.md`)之后按裁决修改、重新送审,见 C1 节“第二次送审(按裁决修改)”。C1 节其余各小节记录第一次送审,保持原样。以下开头各项是 C1(第二个阶段 C 会话)的情况;C2、C3 的会话与运行环境见 C2 节开头。

- 指令:`tasks/IMPLEMENTATION_TASK_ORDER_V1.md` 第 10 节表中 C 行、第 7、8、11 节;Owner 下达阶段 C 的消息原文 `tasks/IMPL_C_OWNER_MESSAGE.md`(两段:本会话开头的消息,含 Review Gate 补充裁决 1–6;上次阶段 C 指令原文,含 Review Gate 对阶段 B 的裁决 1–5 与阶段 C 的要求 6–10)。阶段 C 分 C1、C2、C3 三段,每段结束提交、推送、写入本报告。
- 执行会话:session_01J5mxaXeqjRSkJj9ZuGh8EJ(第二个阶段 C 会话;上一个会话 session_01J5mxaXE1WCWBQiUWaFsd9w 在第一个代码提交的两份审查 BLOCK 后停止,代码已撤回,见 `reviews/tree-65225a5a…/` 与 `1435a74..eb05e42`)。本地分支 `metrix-e1-pilot-protocol-v1` 设为 `origin/metrix-e1-pilot-protocol-v1`(`eb05e422`)后在其上工作;会话分支 `claude/brave-meitner-436eh9` 没有使用。
- 运行环境:Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,没有 nvidia 设备、没有 `nvidia-smi`,`torch.cuda.is_available()` 为 False(`impl_c/c1_00_session_start.txt`、`c1_01_env_fetch.txt`)。Python 3.13.18;依赖按 `requirements.lock` 以 `--require-hashes --no-deps` 安装到会话临时目录的 venv(安装前在 venv 内升级了 pip 本身,pip 不在锁定文件中),`pip check` 通过;torch `2.11.0+cu130`,transformers 5.22.2。
- 上次阶段 C 指令的原文不在仓库中,本会话也没有上次的对话记录;Executor 询问后 Owner 粘贴了原文,与本会话开头的消息一起原样写入 `tasks/IMPL_C_OWNER_MESSAGE.md`(第一次送审未提交;随工作提交 `ae60e0f7` 入库)。
- 没有加载任何模型权重、没有下载权重文件(下载的是 4 个分词器文件、parcae `tokenizer.json`、锚文本 parquet 与固定 revision 的 `config.json`)、没有使用 GPU。没有生成、读取或统计 TEST:TEST 闸门的测试全部用测试自己写的人造行,在临时 Git 仓库中运行(补充裁决 5)。

## Review Gate 对阶段 B 的裁决

Owner 在下达阶段 C 时转达(原文见 `tasks/IMPL_C_OWNER_MESSAGE.md` 第二段;“Review Gate 对阶段 B 的裁决(2026-11-24,作用范围:本阶段;记入 IMPL_C_REPORT.md)”)。以下逐字照录第 1–5 项,每项后写明落实情况。`interpretations.py` 中 B1–B24 的 ACCEPTED 标记引用本节第 1 项(补充裁决 2:不新建决定文件)。

1. 「B1–B24 全部接受。在阶段 C 第一个代码提交中，把 interpretations.py 每条的 status 设为「ACCEPTED（Review Gate 2026-11-24）」，使 pending() 为空。」
   - 「B3：正式运行第 8 节第 1 步，把 train_Y.jsonl 的规范化哈希写入 manifest。」
   - 「B14：G0.3、G0.9 原因为 null，附「需重新校准」注记，与 Task Order V1.2 §15.8 一致。」

   落实(C1):B1–B24 的 `status` 都是 `ACCEPTED（Review Gate 2026-11-24）`;`as_records()` 写入实验记录时每条带 `ruling`(`interpretations.RULING_REF`,指向本节第 1 项);B3、B14 带 `ruling_note`。与裁决“使 pending() 为空”的字面不一致之处:C1 第 1 轮审查后新增了解释 B25(checkpoint 哈希的定义,PENDING_REVIEW_GATE),所以 `pending()` 现为 `["B25"]`;B25 裁决之前 TEST 生成器与所有 TEST 路径都拒绝。B25 列于“待 Review Gate 决定”,须在租卡前裁决,否则第 8 步必然被拒。B14:`gate.RECALIBRATION_NOTE` 改为「需重新校准」,G0.3、G0.9(以及按 B24 同样处理的 T3)不满足时原因为 null、注记为「需重新校准」(`tests/test_gate.py::test_reasons_follow_section_9`)。B3 的 manifest 写入属于第 1 步的编排,在 C2 的 `run_pilot.py` 中实现。Task Order V1.2 不在仓库中,“与 §15.8 一致”一句 Executor 无法核对,照录。第二次送审(`ae60e0f7`):B25 已接受(Review Gate 对 C1 的裁决第 3 项,status「ACCEPTED（Review Gate 2026-11-25）」),`pending()` 为空,上述不一致已消除。
2. 「「UTF-8 解码 test 行」不属于读取 TEST：协议第 3 节把解析 split 字段排除在外，而解析必须先解码字节，所以「解码内容」指读取或使用 test 行的文字本身（分词、解析内容、用于计算）。已发生的运行都没有使用 test 行内容，不触发 ST13，Pilot 有效。保留按字节读取的现行做法。这是执行解释，不改协议文本。」

   落实:`data.build_general_dev` 仍按字节读取,没有改动。
3. 「TEST 生成器的第 4 个前提（B1–B24 全部裁决）：保留。」

   落实:保留;`test_data.check_interpretations_ruled` 与 `leakage.verify_authorization` 改为共用 `interpretations.pending_problem()`(BE9)。
4. 「B19 未在预告的停止点停下：追认；以后预告的停止点必须停下。」

   落实:B19 文字删去“To be ruled before step 8 runs.”。本阶段没有新的预告停止点。
5. 「推送记录的证据提交不经审查：确认。每阶段最后一次推送的记录，由下一阶段第 0 步的 ls-remote 代替。」

   落实:阶段 B 报告提交的推送记录 `impl_b/t14_evidence_push.txt` 已随容器回收丢失(上一个阶段 C 会话 `impl_c/t0_remote_check.txt` 末行已说明),由阶段 C 第 0 步的 `git ls-remote`(`impl_c/t0_remote_check.txt`)代替;本会话开始时再次核对(`impl_c/c1_00_session_start.txt`)。

## Review Gate 补充裁决(2026-11-24,作用范围:本阶段)

原文见 `tasks/IMPL_C_OWNER_MESSAGE.md` 第一段。落实情况:

1. 证据提交只用 `git add <明确路径>`,提交前核对 `git diff --cached --stat` 只涉及 `reports/`、`reviews/`、`audit/`(各证据提交的记录见下文)。`1435a74` 的失误与向前撤回已追认,不再处理。
2. 见上节第 1 项。
3. ST10 记录:见 C1“TEST 闸门”。
4. 「TEST 只评一次」:见 C1“TEST 闸门”。
5. 3、4 的测试全部在临时 Git 仓库中用人造行运行:`tests/test_testgate.py`。
6. CUDA:不另锁 CUDA 12.x 构建;RUNBOOK 的租用条件与检查命令在 C3。

## Review Gate 对 C1 的裁决(2026-11-25,作用范围:本阶段)

Owner 转达,原文连同首段入库为 `tasks/IMPL_C1_RULING.md`。以下逐字照录防范对象与第 1–9 项;落实情况写在 C1 节“第二次送审(按裁决修改)”。

防范对象：TEST 闸门要防的是「按规则办事的 Executor 在按 RUNBOOK 操作时，意外评测 TEST 两次，或在 ST10 不成立时评测 TEST」；不防有仓库写权限者的故意篡改（改写历史、伪造记录），这类风险由 GitHub 分支保护和审查记录承担。审查按此范围判定：范围外的边缘情况记为 MINOR 并登记，不作为 BLOCKER。调用两份审查时，把本段防范对象原文写进调用文字。

1. 采用 (a)：所有 TEST 路径都必须在 metrix-e1-pilot-protocol-v1 的检出上运行，且 HEAD 等于 fetch 后远端该分支的最新提交，否则 BLOCKED。标记检索简化为只查两处：工作区，以及远端该分支最新提交的文件树；任一处存在即拒绝。删除对 reflog、侧分支、标签和其他引用的检索。
2. 采用 check_commit_preconditions，由 begin、finish 与 TEST 驱动共用，在生成 TEST 之前检查。生成之后真实推送仍被拒绝：视为 TEST 已生成，禁止重跑，状态 BLOCKED，报告 Owner；由 Owner 决定是否批准把 ST10 记录这一个文件手工提交。
3. B25 接受：checkpoint 哈希 = train.state_sha256。在 interpretations 中写明其计算定义，status 设为 ACCEPTED（Review Gate 2026-11-25），使 pending() 为空。C2 冒烟测试中保存并重载 checkpoint，证明哈希不变。
4. 拒绝时的状态词按 Executor 提案（报告待决第 4 项）接受。
5. data-auditor 可以把 Executor 的探针当作驱动子进程运行，但预期结果须由它独立算出。
6. 远端保护：Owner 已在 GitHub 上为该分支设置禁止 force push 与删除、允许直接推送。metrix/CLAUDE.md 第 6 节的「受保护分支」指 main；在本分支直接快进推送为既定做法。只能经标签到达的标记、主机名比对，均不处理。RUNBOOK 写明这项 GitHub 设置。
7. 被取代的试跑输出按现行方式入库：接受。
8. 停止提交属于证据提交，不需补审。
9. C1 按上述修改后重新送两份审查，轮次从 1 重新计。DEFERRED_MINORS 1.29 中属于防范对象以外的项登记，不修。

## Review Gate 裁决(2026-11-27,作用范围:本阶段)

Owner 在下达 C2、C3 时转达,原文连同首段入库为 `tasks/IMPL_C2_OWNER_MESSAGE.md`。以下逐字照录,每项后写明落实情况。

1. 「TEST 评测调用不 fetch、只在 begin 与 finish 时 fetch：接受。RUNBOOK 写明「begin 到 finish 之间任何人不得推送本分支」。」

   落实:C1 节“待 Review Gate 决定”第 1 项(1.30 CD1、1.31 CE1)由此结案;`testgate` 不改。`RUNBOOK_A100.md` 第 3.8 节照录这句话(其后注明本分支即 `metrix-e1-pilot-protocol-v1`),并写明期间不得提交命令输出或在本克隆中做任何 git 操作;第 5 节写明命令输出在 begin 与 finish 之间不提交。`pilot.py` 模块说明引用本项。
2. 「f8139f9 属于证据提交，不需补审。」

   落实:C1 节“待 Review Gate 决定”第 2 项结案;`f8139f9` 不补审。

C1 节“待 Review Gate 决定”第 3 项(C2 的时间)由本次指令回答:C2、C3 在本会话执行。

## Review Gate 对 C2、C3 待决事项的裁决(2026-11-27,作用范围:E1 Pilot 直至结束)

Owner 转达,原文连同首段入库为 `tasks/IMPL_C4_RULING.md`(下称“C4 裁决”)。以下逐字照录第 1–7 项,每项后写明落实情况;执行见“C4”节。

1. 「ST11 改为读「B17 估算 + checkpoint 开销」之和，超过 3.5 小时即停。B17 的解释文字相应修订，status 记为 ACCEPTED（Review Gate 2026-11-27 修订）。ST7 的事前判断不变，TEST 的事前估计不加余量。补测试与变异。」

   落实(C4 代码提交):C2 节“待 Review Gate 决定”第 2 项由此结案。`pilot.st11_estimate_hours` = B17 估算 + checkpoint 开销 / 3600,预检写入第 2 步记录(`st11_estimate_hours`、`checkpoint_overhead`),`step2` 的 ST11 读它;`stops.st11` 不变(超过 3.5 小时停止)。B17 的 text 写明两部分及其组成,status `ACCEPTED（Review Gate 2026-11-27 修订）`,ruling `tasks/IMPL_C4_RULING.md 第 1 项`。ST7 的事前判断(`run_seconds`、`eval_seconds`、`test_evaluation_seconds`)不变,只改文档字符串。测试与变异见“C4”节。
2. 「C2 待决第 1、3、4、5、6、7 项：全部按现行实现接受，不改代码。」

   落实:C2 节“待 Review Gate 决定”第 1、3–7 项由此结案,没有改动相关代码(包括其中写着 “for Review Gate” 的注释,见“C4”节)。
3. 「A100 上的依赖安装、输入与权重下载属于正式流程；metrix/CLAUDE.md 第 4 节「租卡后只跑正式流程」指不在租用机器上开发调试。」

   落实:C3 节“待 Review Gate 决定”第 1 项结案;RUNBOOK 开头“与 metrix/CLAUDE.md 第 4 节的关系”按此改写。
4. 「正式运行期间只含输出的手工提交（results/command_output/、audit/、reviews/）按证据提交处理，不经 code-reviewer；此前各项「本阶段」裁决在 A100 运行期间继续有效。」

   落实:C3 节“待 Review Gate 决定”第 2 项与 `DEFERRED_MINORS.md` 1.38 CL7 结案;RUNBOOK 开头“此前裁决的效力”与第 5 节“审查方式”按此改写。
5. 「两份 L6 计数不同：ST10，不运行 test-evaluate；Executor 按协议第 10 节模板手写一份 BLOCKED 实验记录，作为证据提交。」

   落实:C3 节“待 Review Gate 决定”第 3 项结案;RUNBOOK 第 3.7 节第 4、5 项(手写记录的路径、20 个字段的模板、提交方式),第 4 节例外与 ST10 一行。
6. 「主机没有 CPython 3.13.18 时，允许用 uv 安装该精确版本；装不到即停下报告 Owner。」

   落实:RUNBOOK 第 1 节 Python 与网络两行、第 3.0 节核对说明、第 3.2 节的 3.2a。本会话在 CPU 容器中核对了这条路径(`impl_c/c4_04_uv_check.txt`):容器预装的 uv 0.11.32 不列出 3.13.18 的下载;PyPI 上的 uv 0.13.10 列出(下载地址 `releases.astral.sh`)并装成,解释器报告 `Python 3.13.18`、`CPython 3.13.18`,能建 venv。所以 3.2a 用从 PyPI 新装的 uv,网络一行加入 `releases.astral.sh`(只在 3.2a 时)。没有在这个解释器上安装依赖或运行测试。
7. 「RUNBOOK 按 1、3–6 更新，删去「待 Review Gate 决定」的措辞，时长表改为 ST11 读两者之和；另写明在 A100 主机上运行 Claude Code 的前提（从仓库根目录、本分支启动，使两个 agent 定义直接加载）。」

   落实(C4 文档提交):RUNBOOK 开头与第 1、3、4、5、6 节;第 1 节新增“在 A100 主机上运行 Claude Code”。RUNBOOK 中不再有“待 Review Gate 决定”或“待决”的措辞。

## Review Gate 对 C4 待决事项的裁决(2026-11-28,作用范围:E1 Pilot 直至结束)

Owner 转达,原文连同首段入库为 `tasks/IMPL_C5_RULING.md`(下称“C5 裁决”)。以下逐字照录第 1–5 项,每项后写明落实情况;执行见“C5”节。

1. 「pilot.py 中 4 处过时注释：不改，登记。正式运行之前不再提交任何代码改动。」

   落实:C4 节“待 Review Gate 决定(C4)”第 1 项与 `DEFERRED_MINORS.md` 1.39 CM3 结案:不改,登记(CM3 的处理列与 1.39 首段)。1.39 中写着“下一个代码提交”的 CM4、CM5、CM6、CM8、CM10 在正式运行之前不会改,保持登记(1.39 首段)。C5 没有改 `src/`、`tests/`、`run_pilot.py`。
2. 「做一次纯文档提交，按 DEFERRED_MINORS 中各条「处理应为」修正 RUNBOOK：CL2、CL3、CL4、CL5、CL6、CP1、CP2、CP3、CP4。另在 RUNBOOK 第 4 节加一条总则：「任何命令以回溯或非 0 退出码结束，或出现本手册没有写到的情况：不重跑、不修补，保留输出，报告 Owner。」」

   落实(C5 文档提交):C4 节“待 Review Gate 决定(C4)”第 2 项结案。九项逐项见“C5”节“交付”,`DEFERRED_MINORS.md` 1.38、1.42 各行处理列末尾记“已修(C5 文档提交)”。总则原文写在 RUNBOOK 第 4 节开头。
3. 「CP5：确认。主机有 CPython 3.13.18 但不能建 venv（缺 ensurepip）时，同样用 uv 安装该精确版本；第 1 节与 3.0 的说明同步。」

   落实(C5 文档提交):3.2a 的条件不变;第 1 节 Python 一行、第 3.0 节的说明与 3.2a 的注释改为“没有 CPython 3.13.18,或有而不能建 venv(缺 ensurepip)”时用 uv,并引用本项;`DEFERRED_MINORS.md` 1.42 CP5 结案。
4. 「本次提交只送 code-reviewer 一轮：有 BLOCKER 则修复后再送，否则直接提交；新的 MAJOR、MINOR 只登记。不改 src/、tests/、run_pilot.py。」

   落实:见“C5”节“提交与审查(C5)”。
5. 「完成后状态仍为 IMPLEMENTATION_READY，停下。」

   落实:见“最终状态”。

## C1:BE 修复、interpretations 标记、TEST 闸门

### 第二次送审(按裁决修改)

结果:C1 完成。工作提交 `ae60e0f7`(树 `365960a0`)与修复提交 `b48fe842`(树 `ae5fcb2f`)各经两份审查(按裁决第 9 项,轮次从 1 重新计),都在第 1 轮 PASS,已快进推送(推送记录 `impl_c/c1b_push_work_commit.txt`、`c1b_push_fix_commit.txt`)。

| 提交 | 被审暂存树 | code-reviewer | data-auditor(仅作参考) | Executor 的原始输出 |
|---|---|---|---|---|
| `ae60e0f7` 工作提交 | `365960a0` | PASS(2 MAJOR、9 MINOR) | PASS(1 MINOR;评测调用不 fetch 交 Review Gate) | `impl_c/c1b_02_checks.txt`(`c1b_01` 已被取代) |
| `b48fe842` 修复提交 | `ae5fcb2f` | PASS(沿用的 MAJOR 交 Review Gate;6 MINOR) | PASS(MINOR 与提示,均在防范对象以外或只涉及描述) | `impl_c/c1b_04_checks_fix.txt`(`c1b_03` 已被取代) |

- 审查原文(`*_round1.md`)、调用文字(含防范对象原文)、调用前的 frontmatter 核对、审查输入、原始转录:`reviews/ae60e0f7…/`、`reviews/b48fe842…/`(各有 `README.txt`)。修复提交的两份审查因 API 额度上限(HTTP 429)中断,本会话进程随后重启,用固定首句续审完成(`reviews/b48fe842…/interruption.txt`、`resume_message_*.txt`)。
- data-auditor 的脚本与完整 stdout:`audit/ic5_*`(工作提交)、`audit/ic6_*`(修复提交),均在 `audit/stdout/impl_c/`。
- 问题与处理:`DEFERRED_MINORS.md` 1.30(工作提交)、1.31(修复提交);第一次送审各项按裁决的处理写入 1.29 的处理列。
- 本报告提交(只含 `reports/`、`reviews/`、`audit/`,补充裁决 1):送 code-reviewer 时因每周额度上限中断(HTTP 429,重置时间 2026-11-29 17:00 UTC),没有产生报告(`reviews/b48fe842…/code-reviewer_report-commit_*`)。按对 C1 的裁决第 8 项“停止提交属于证据提交，不需补审”的同一分类,作为证据提交提交,未经审查;见下文“待 Review Gate 决定”第 2 项。

裁决各项的落实:

1. 第 1 项:`testgate.check_checkout`(origin 的 fetch URL 的 owner/name 为 `leotree2020/OpenMythos`、检出 `metrix-e1-pilot-protocol-v1`、不是浅克隆、fetch 成功、HEAD 等于 FETCH_HEAD,否则 BLOCKED);标记、结果文件与 ST10 记录只查工作区与远端最新提交的文件树;删去 reflog、`--all`、远端全部分支的检索与 remote、branch 参数。评测调用的读法见下文“待 Review Gate 决定”第 1 项。
2. 第 2 项:`check_commit_preconditions` 由 begin、finish 与 TEST 驱动共用,驱动在生成 TEST 之前检查;生成之后真实推送被拒为 BLOCKED,提示 TEST 视为已生成、由 Owner 决定是否手工提交这一个文件(测试 `test_driver_push_refused_after_generation_counts_as_generated`)。修复提交另加:同一克隆中两个并发的 begin 至多一个拿到会话(推送的提交须含本会话标记的字节、父提交不含标记)。
3. 第 3 项:B25 为「ACCEPTED（Review Gate 2026-11-25）」,text 写明计算定义,测试按文字独立实现并与 `train.state_sha256` 比较;`pending()` 为空。“冒烟中保存并重载 checkpoint、证明哈希不变”在 C2。
4. 第 4 项:各类拒绝的状态词写在 testgate 模块文档。
5. 第 5 项:data-auditor 以子进程运行 `impl_c/c1b_gate_probe.py`,每个预期由其模型在运行前算出(`ic5_01`、`ic6_01`)。
6. 第 6 项:模块文档写明 GitHub 设置;不比较主机名,不检索只能经标签到达的标记;RUNBOOK 在 C3。
7. 第 7 项:被取代的记录照现行方式入库:`impl_c/c1b_01_checks.txt` 被 `c1b_02` 取代(`c1b_mutate.py` 中一个变异多指名了 3 个本不该失败的 begin 用例,74 个变异记为测出 73;两次所测的 src/tests 哈希相同 `adfeb518…`);`impl_c/c1b_03_checks_fix.txt` 被 `c1b_04` 取代(新增的“推送字节”变异所指名的测试中,父提交检查先拦下,记为 77/78;补测试 `test_a_marker_file_overwritten_before_the_commit_is_blocked` 后重跑,78/78)。
8. 第 8 项:停止提交 `5f5cd51e` 不补审。
9. 第 9 项:按裁决修改后重新送审,轮次从 1 计;1.29 中防范对象以外的项登记不修(见 1.29 处理列)。

检查(修复提交,`impl_c/c1b_04_checks_fix.txt`):数据重新生成并核对、四个冻结内容哈希 PASS;TEST 生成器在当前状态拒绝(原因现为 Gate 0 记录未提交),没有产物;outside_metrix_check PASS;全部 pytest 298 passed;Executor 运行探针一次(`c1b_probe_run.py`);变异 78 个全部测出,前后 src/tests 哈希相同。data-auditor 独立复算四个冻结哈希、L1–L6、候选可行性与 split,均 PASS(`ic6_02`、`ic6_06`);闸门黑盒比对 376 项一致、0 处不同,包括同一克隆中两个进程并发 begin 的四种交错(`ic6_01` R 组)。

待 Review Gate 决定(C1 第二次送审):

1. **评测调用不 fetch(1.30 CD1、1.31 CE1)。** `evaluate_model(split="test")` 每次调用只在本地核对“检出 Pilot 分支且 HEAD 等于本会话的标记提交”,不 fetch;begin(写标记之前)与 finish 会 fetch。理由:每次调用都 fetch 时,网络中断会让评测中途 BLOCKED,按补充裁决 4 视为已评;而 HEAD 等于标记提交已保证所读的标记与记录就是 begin 核对过的那些。实际差别:begin 之后若有人向该分支推送,剩余模型仍会评完,到 finish 才 BLOCKED(视为已评)。两份审查都认为在防范对象内不产生“评两次”或“ST10 不成立仍评”的路径。请确认这一读法;确认之前 RUNBOOK(C3)写明 begin 到 finish 之间任何人不得向该分支推送。
2. **本报告提交未经审查。** 审查因每周额度上限中断(见上)。Executor 按裁决第 8 项把它当作证据提交提交并推送,以免审查记录只留在会话临时目录(metrix/CLAUDE.md 第 9 节)。请确认,或指示在额度恢复后补审。
3. **C2 的时间。** C2 的代码提交须经两份审查,额度恢复(2026-11-29 17:00 UTC)之前无法进行;按 Owner 指令“额度不足时在段落之间停下”,在 C1 与 C2 之间停下。C2 的编排代码与一次冒烟试跑只在会话临时目录中,未送审。

以下各小节记录第一次送审。

### 第一次送审:停止(连续 3 轮未 PASS),代码未提交

| 轮 | 被审暂存树 | code-reviewer | data-auditor | Executor 的原始输出 |
|---|---|---|---|---|
| 1 | `2408558f` | PASS(4 MAJOR、18 MINOR) | BLOCK(B05:`git log` 没有 `--full-history`,在侧分支上提交又删除、合并回来的标记找不到) | `impl_c/c1_02_checks.txt` |
| 2 | `dc4f28df` | PASS(6 MAJOR、12 MINOR) | BLOCK(暂存的探针 `impl_c/c1_gate_probe.py` 没有跟上 testgate 的接口;`src/` 的行为在 auditor 的修正副本下 214 项一致) | `impl_c/c1_03_checks_r2.txt`、`c1_04_checks_r2b.txt` |
| 3 | `9be4df2a` | PASS(2 MAJOR、11 MINOR) | BLOCK(N1、N2:检出分支不是 main 或分离 HEAD 时 `refuse_if_marker` 为 ACCEPT,与 Executor 调用说明“begin 与 marker 为 BLOCKED”不符;其余 251 项一致) | `impl_c/c1_05_checks_r3_interrupted.txt`、`c1_05b_restart_restore.txt`、`c1_06_checks_r3.txt` |

- 审查原文(`*_round1.md`、`*_round2.md`、`*_round3.md`,由 `reports/round6/review_extract.py` 从转录原样提取)、调用文字、调用前的 frontmatter 核对、审查输入、原始转录、中断与续审记录:`reviews/tree-9be4df2a…/`(`README.txt` 列出各文件)。三轮在同一个目录:三个暂存树都不是提交,用最后一个树命名(先例 `reviews/tree-65225a5a…/`)。
- data-auditor 的脚本与完整 stdout:`audit/ic2_*`(第 1 轮)、`audit/ic3_*`(第 2 轮)、`audit/ic4_*`(第 3 轮),stdout 在 `audit/stdout/impl_c/`。
- 各轮提出的问题与处理:`DEFERRED_MINORS.md` 1.27(第 1 轮)、1.28(第 2 轮)、1.29(第 3 轮,全部未处理)。
- data-auditor 的信任状态仍为「待验证」(metrix/CLAUDE.md 第 10 节);它的 BLOCK 按第 5 节第 3 条照样修复后重审,三轮都计为未 PASS。

### 第 3 轮被审暂存树的内容(未提交)

- BE2、BE9、BE10、BE12 已改并有测试;BE13 不改(`impl_b/mutate_fix3.py` 须与 `t12` 中运行的脚本逐字节相同)。
- interpretations:B1–B24 为「ACCEPTED（Review Gate 2026-11-24）」;新增 B25(checkpoint 哈希 = `train.state_sha256`)待决,裁决前 TEST 生成器与所有 TEST 路径拒绝。
- TEST 闸门(新模块 `testgate.py`,补充裁决 3–5):
  - ST10 记录由第 8 步的 TEST 驱动(`test_data.main`)写入,内容为 TEST 部分 L3–L6 的原始计数、两个 TEST 文件的 sha256、代码 commit,绑定授权;驱动自己只提交并推送这一个路径。
  - ST10 闸门只读已提交的记录,用冻结上限从原始计数重新判定(不信任自报标志);文件哈希须与授权和将要评测的行一致;data-auditor 的独立 L6 计数(`audit/st10_l6_test_count.json`)须已提交且相等。
  - 「TEST 只评一次」:评测之前先提交并推送标记(含全部 checkpoint 哈希与 N);标记出现在工作区、任一本地或远端跟踪引用的任一提交、reflog、远端任一分支时拒绝;有标记无结果视为已评,BLOCKED;远端仓库与分支固定为 `leotree2020/OpenMythos`、`metrix-e1-pilot-protocol-v1`,浅克隆 BLOCKED。
  - `evaluate_model(split="test")`:授权 → 会话与标记、ST10、模型哈希 → `require_gpu` → 登记 checkpoint。
- 测试全部在临时 Git 仓库与裸远端上用测试自己写的人造行运行(`tests/test_testgate.py`);没有生成、读取或统计真实 TEST。

### 第 3 轮被审暂存树上的检查(`impl_c/c1_06_checks_r3.txt`;运行环境同报告开头)

| 项 | 结果 | 位置 |
|---|---|---|
| 被测代码即暂存内容 | `git diff HEAD -- src tests` 的 sha256 在开头与结尾都是 `4781575f…`;data-auditor 第 3 轮独立核对相同(`audit/stdout/impl_c/ic4_00_state.txt`) | 第 120、424 行 |
| 数据重新生成、verify、四个冻结内容哈希 | PASS;data-auditor 独立复算一致(`ic4_02_content_hashes.txt`) | 第 122–153 行 |
| TEST 生成器(当前状态) | 拒绝(Gate 0 记录未提交),没有产物;data-auditor 黑盒运行结果相同(`ic4_04_test_refusal.txt`) | 第 154–170 行 |
| outside_metrix_check | PASS | 第 171–182 行 |
| pytest 全部 | 275 passed | 第 188 行 |
| 探针运行一次(`c1_probe_run.py`) | B25 待决时 begin、eval 拒绝;带 `--interpretations-ruled` 时 begin 推送标记、eval 停在 `require_gpu`、gate 第一次登记第二次拒绝、marker 为 BLOCKED;探针拒绝本仓库 | 第 190–223 行 |
| 变异(`c1_mutate_r3.py`) | 70 个全部测出,前后 src+tests 哈希相同(code-reviewer 第 3 轮指出其中两个的“测出”是附带的,1.29 CC7) | 第 224–367 行 |

- 第 3 轮正式记录之前,在会话临时目录的 worktree 中试跑过一次变异:4 个未测出,是第 3 轮补测试的起因。试跑输出与当时的脚本按 code-reviewer 第 3 轮 MAJOR 2 入库为 `impl_c/c1_04t_mutate_r3_trial.txt`、`c1_04t_mutate_r3_trial_script.py`;它们不是证据,已被 `c1_06` 取代(试跑的被测树没有记录树哈希,只有输出末尾的 src+tests 哈希 `2b86f92d…`)。

### 中断(第一次送审)

- HTTP 429:第 1 轮两份审查、第 2 轮 data-auditor 中断,用第 5 节第 6 条的固定首句续审完成;中断、续审消息与送达核对在 `reviews/tree-9be4df2a…/`。
- 容器重启:第 3 轮第一次录制(`c1_05`)中断,变异脚本当时的变异(“claim removed”)留在工作区;发现、恢复与逐文件核对见 `c1_05b_restart_restore.txt`,之后完整重跑为 `c1_06`。

### 本提交(停止提交)

- 只含 `reports/`(本报告、`DEFERRED_MINORS.md`、`impl_c/`)、`reviews/tree-9be4df2a…/`、`audit/`(第 1–3 轮)。暂存区先用 `git reset -q` 清空(工作区不变),再逐个 `git add <文件路径>`;`git diff --cached --stat` 与路径前缀核对的原始输出:`impl_c/c1_07_stop_commit_precheck.txt`。
- 本提交没有经过审查:第 5 节第 4 条要求此时停止;先例 `1435a74`。是否补审,见下文第 8 项。
- 推送记录:按 Review Gate 对阶段 B 的裁决第 5 项,由下一次会话第 0 步的 `git ls-remote` 代替。
- 没有提交的:代码与 `tasks/IMPL_C_OWNER_MESSAGE.md`(以 `input_round3.diff` 为准);会话临时目录中的 C2 编排与冒烟试跑、C3 RUNBOOK 草稿、第 3 轮问题的修复草稿。它们都没有送审,不支撑本报告的任何结论,容器回收后丢失。

### 待 Review Gate 决定(第一次送审;已由 2026-11-25 的裁决回答,见“Review Gate 对 C1 的裁决”)

1. **data-auditor 第 3 轮的 BLOCK(1.29 CC1)。** 检出分支只在传入分支参数时检查,标记与 ST10 记录的检索不传,所以在非 main 检出上 `refuse_if_marker` 为 ACCEPT;文档与 Executor 的调用说明写的是 BLOCKED。不绕过闸门:begin 写标记之前、TEST 驱动生成之前都检查检出分支。二选一:(a) `check_remote` 不论有无分支参数都核对检出分支,TEST 路径的所有 git 操作都要求在 Pilot 分支的检出上运行;(b) 只改文档与说明。Executor 倾向 (a):规则更简单,与文档一致;代价是在别的检出上不能只读地查询标记。
2. **code-reviewer 第 3 轮 MAJOR 1(1.29 CC2)。** 提交与推送的前提应在生成 TEST 之前检查。Executor 的方案:公开的 `check_commit_preconditions`(Pilot 远端与分支、没有暂存、提交者身份、HEAD 是远端分支的后代、`push --dry-run`),由 begin、finish 与 TEST 驱动共用;补测试(暂存、没有身份、落后、dry-run 失败时 BLOCKED,生成函数没有被调用、`--out` 不存在、没有记录)与变异。之后仍可能失败的情形(服务器端拒绝真实推送):ST10 记录留在工作区,拒绝任何重跑,BLOCKED。这时如何恢复,须由 Review Gate 定:例如 Owner 批准后只把这一个路径手工提交并推送(记录只含计数、哈希与提交号),或视为 TEST 已生成、本次 Pilot BLOCKED。
3. **B25**(checkpoint 哈希的定义 = `train.state_sha256`)。须在租卡前裁决,否则第 8 步必然被拒。与第 1 项裁决“使 pending() 为空”的字面不一致,见上文“Review Gate 对阶段 B 的裁决”第 1 项。
4. **拒绝的状态词(1.27 CA8、1.28 CB6)。** 环境类(远端不能列出或 fetch、远端或分支不符、浅克隆、有暂存、提交与推送的前提)为 BLOCKED;记录缺失或不绑定、模型哈希与标记不符、第二次生成 TEST、`git log` 失败为 IMPLEMENTATION_FAIL;标记与结果都在时为不带第 9 节状态的 TestAlreadyEvaluated。
5. **data-auditor 能否使用 Executor 写的黑盒探针 `c1_gate_probe.py`(1.27 CA9)。** 第 2、3 轮 data-auditor 都以子进程运行它,预期由它自写的模型在运行前算出。
6. **远端历史与远端的识别(1.28 CB8、CB19;1.29 CC4、CC9、CC15)。** 只能由远端标签到达、没有分支的标记(B17)不检索;远端的 force-push 与删分支 git 无法检测;`check_remote` 只比较 owner/name,不比较主机,也不看 push URL。前提“远端分支不丢提交(禁止 force-push 与删除)、Pilot 账户可以直接快进推送”与 metrix/CLAUDE.md 第 6 节“改动经 PR 合入,不直接推送到受保护分支”的字面关系请确认;RUNBOOK(C3)写明 GitHub 上的具体设置。
7. **被取代的试跑输出(1.29 CC3)** 是否属于第 9 节“原始输出一律写入仓库”:本提交已入库 `impl_c/c1_04t_*`。
8. **本停止提交**(本报告与 `DEFERRED_MINORS.md` 的文字)没有经过审查;是否补审。
9. **下一步。** 裁决之后,C1 工作提交按裁决修改,处理 1.29 的各项,重新送两份审查(轮次是否重新计数由 Review Gate 定);C2、C3 在 C1 提交之后进行。留给 C2 的事项不变:冒烟中保存并重载 checkpoint 后核对 `state_sha256`(1.27 CA7);begin、finish 的生产调用方(CA20),接入后 data-auditor 复审 TEST 路径(阶段 B 裁决之后的阶段 C 要求第 7 项);`state_sha256` 的耗时计入预检估算(CA21);DEV 路径的数据核对(CA23);finish 写入的结果不得含 TEST 内容。

## C2:run_pilot.py 与 CPU 冒烟测试

- 指令:Owner 本次消息(`tasks/IMPL_C2_OWNER_MESSAGE.md`);Implementation Task Order V1 第 4、5、7、11 节;C1 裁决第 3 项(冒烟中保存并重载 checkpoint,证明 `state_sha256` 不变);C1 节“留给 C2 的事项”(CA7、CA20、CA21、CA23;CD5、CD13、CE5)。
- 执行会话:session_01J5mxaVbRYj7wxzW5sZcUYh(第三个阶段 C 会话)。本地分支 `metrix-e1-pilot-protocol-v1` 设为 `origin/metrix-e1-pilot-protocol-v1`(`f8139f9`)后在其上工作;会话分支 `claude/metrix-c2-c3-pilot-4nwq50` 没有使用。
- 运行环境:Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,没有 nvidia 设备与 `nvidia-smi`(`impl_c/c2_00_session_start.txt`);Python 3.13.18,依赖按 `requirements.lock` 以 `--require-hashes --no-deps` 装入会话临时目录的 venv(pip 本身先升级),`pip check` 通过,torch `2.11.0+cu130`(`torch.cuda.is_available()` False),transformers 5.22.2(`impl_c/c2_01_env_fetch.txt`)。下载的只有 4 个分词器文件、parcae `tokenizer.json`、锚文本 parquet 与固定 revision 的 `config.json`;没有下载或加载任何权重,没有使用 GPU,没有生成、读取或统计 TEST。
- **起点**:指令所说的草稿分支 `wip/metrix-stage-c2` 在远端不存在(`c2_00`:`ls-remote` 只列出 `wip/metrix-stage-c`;`git fetch origin wip/metrix-stage-c2` 退出码 128)。`wip/metrix-stage-c` 中的 `run_pilot.py` 是第一次送审之前(C1 裁决之前)的草稿,接口已变且不完整,只作参考;`run_pilot.py` 与 `src/metrix_e1/pilot.py` 按当前代码重写。上一会话的 C2 草稿(报告 C1 节第 3 项“只在会话临时目录中”)随容器回收丢失。

### 交付

- `run_pilot.py`(唯一入口):子命令 `smoke --steps N`、`formal`、`test-generate`、`test-evaluate`、`fetch-model`。Task Order 第 7、11 节写的 `run_pilot.py --smoke` 实现为子命令 `smoke`(1.32 CF21);formal 系子命令没有步数参数。
- `src/metrix_e1/pilot.py`:第 8 节第 1–8 步的编排(模块说明逐项写明)。每步开始 ST12(第 2 步起含整个数据目录的 `data.verify`,CA23)、ST13 检测、formal 下的提交前提;每步结束写步记录,formal 下只提交该步路径并推送(只提交与 HEAD 不同的路径)。一步之中的停止先写并提交该步记录。
- checkpoint(C1 裁决第 3 项、B25):每次训练 `state_sha256` → `torch.save` → 重载到同结构的新模型 → 再算 `state_sha256`,相等否则 IMPLEMENTATION_FAIL;DEV 评测的是重载的模型;30 个 checkpoint 一个都不删(metrix/CLAUDE.md 第 7 节)。
- 第 1 步 formal 把 8 个非 TEST 文件的哈希写入 `DATA_MANIFEST.json files` 与 `SPLIT_MANIFEST.json split_sha256`(B3 裁决注记:train_Y 的规范化哈希),写后再 ST12;冒烟不改 manifest,只把将写入的字段写成记录。
- 预检:ST11 读 B17 的估算(原样);checkpoint 开销(CA21)与两者之和只报告,并用于 ST7 的事前判断。
- test-generate 以子进程运行 `test_data.main`(CD5、CE5);test-evaluate 是 begin / finish 的生产调用方(CA20),结果只含聚合值与每个 fact 的分数(CD13)。
- `gate.py`:新增 `n_range_values`、`n_ranges_hold`(G0.3 / T3 读的数,ST2 使用),数值不变。
- 测试 `tests/test_run_pilot.py`(23 个测试函数,参数化后 26 项;全部测试由 C1 结束时的 298 项增至 324 项),变异 `reports/impl_c/c2_mutate.py`(工作提交,17 个)、`c2_mutate_fix1.py`(修复提交,25 个)、`c2_mutate_fix2.py` 与 `c2_mutate_fix2b.py`(第二个修复提交,35 + 1 个)、`c2_mutate_fix3.py`(第三个修复提交,43 个)。

### 待 Review Gate 决定(C2;已由 2026-11-27 的裁决回答,见“Review Gate 对 C2、C3 待决事项的裁决”第 1、2 项)

1. **第 10 节“每次运行(含被停止的)提交一份”的范围(1.32 CF1、CF30;1.33 CG5)。** 现行做法:formal 在第 1 步开始之前停止(设备检查 ST8、代码未提交、连续性检查、第 1 步开始时的 ST12/ST13)时,实验记录只写到 `<work>`,不写入仓库、不推送;`Pilot()` 本身的 ST12 没有记录。理由是 c2_02 的事故:开发容器上的检出同样能通过远端与分支检查,误在别的机器上运行 formal 会把一份 BLOCKED 记录推送到本分支。test-evaluate 在本进程写入标记之前、没有停止码的拒绝不写记录(TEST 未评),其中包括第三个修复提交新增的一类:TEST 已开始或已评之后再运行,在任何带停止码的检查之前拒绝(1.34 CH1;1.35 CI8);带停止码的协议停止(ST7、ST8、ST9、ST10、ST12)写记录并推送,其中 ST8 与 formal 第 1 步之前只写 `<work>` 的做法不一致(1.34 CH6)。test-generate 成功时不写实验记录(ST10 记录即其输出),只在 ST10 超限时写(1.36 CJ11)。协议第 10 节“每次运行(含被停止的)提交一份”是否涵盖这些不写记录的拒绝,请确认,或指示区分“非 Pilot 机器”与“Pilot 机器上的第 1 步之前停止”。
2. **ST11 与 ST7 的估计量(1.32 CF10;1.33 CG2)。** ST11 读 B17 的估算(原样);checkpoint 开销(模型加载、`state_sha256`、保存、重载、文件哈希)与两者之和只报告,另用于 ST7 的事前判断(每次训练、每次评测之前;TEST 开始之前按整个 TEST 评测)。是否让 ST11 读两者之和,TEST 的事前估计是否加余量,请决定。
3. **G0.2 与 ST6 剔除的配置(1.32 CF7)。** 读法:第 7 节“出现非有限损失或分数的配置剔除”,剔除的配置不算“用到”,G0.2 不因它不满足;剔除的运行保存停止时的状态并记录其哈希,冻结记录有 30 个哈希。请确认。
4. **预检中的非有限值(1.32 CF6;1.33 CG21)。** 没有预估就不能判 ST11;现按 ST6 的“选定配置或对照”处理为 IMPLEMENTATION_FAIL。请确认或指定状态。
5. **状态词(1.32 CF13、CF27)。** formal 在 Gate 0 PASS、提交冻结记录后结束时,实验记录 Status 为 NOT_TESTED(第 9 节 PASS 要求 T1–T3;Actual 写 Gate 0 PASS);formal 崩溃为 NOT_TESTED;test-evaluate 在 begin 之后的停止或崩溃为 BLOCKED。请确认。
6. **重跑与恢复(1.32 CF11;1.33 CG8、CG9)。** 代码只拒绝不安全的重跑(没有 device ledger 的 `--work`、冻结之后的 formal、已有 checkpoint 的 `--work`);何时、从哪一步重来由 Owner 决定(RUNBOOK 第 4 节)。
7. **入口的形式(1.32 CF21)。** Task Order 写 `run_pilot.py --smoke`,实现为子命令 `run_pilot.py smoke --steps N`(formal 系子命令没有步数参数)。请确认。

### 提交与审查

| 提交 | 内容 | 被审暂存树 | code-reviewer | data-auditor(仅作参考) | Executor 的原始输出 |
|---|---|---|---|---|---|
| `5219ff77` 工作提交 | run_pilot.py、pilot.py、gate.py 辅助函数、测试 14 个、变异 17 个 | `b80c9062` | PASS(12 MAJOR、22 MINOR) | PASS(2 MINOR) | `impl_c/c2_05_checks.txt`(312 passed;17/17)、`c2_06_smoke.txt`;被取代:`c2_02`、`c2_03`、`c2_04` |
| `49fc9a35` 修复提交 | 1.32 的修复;测试 19 个;变异 25 个 | `b40224e6` | PASS(4 MAJOR、18 MINOR) | PASS(4 MINOR) | `impl_c/c2b_03_checks.txt`(317 passed;25/25)、`c2b_04_smoke.txt`;被取代:`c2b_01`、`c2b_02`(内存不足被杀)、`c2b_01b`(恢复记录) |
| `dd65a361` 第二个修复提交 | 1.33 的修复;测试 23 个;变异 35 + 1 个 | `a6ce8a0e` | PASS(3 MAJOR、9 MINOR) | PASS(2 MINOR) | `impl_c/c2c_03_checks.txt`(321 passed;34/35,未测出的一个因测试清单误指)、`c2c_04_mutate_fix2b.txt`(该变异 CAUGHT)、`c2c_02_smoke.txt`;被取代:`c2c_01` |
| `a0e04d1f` 第三个修复提交 | 1.34 的修复;测试 26 个;变异 43 个 | `c7869d35` | PASS(没有 MAJOR;8 MINOR) | PASS(1 MINOR、3 条观察) | `impl_c/c2d_01_checks.txt`(324 passed;43/43)、`c2d_02_smoke.txt` |

- 审查原文、调用文字(第一句按 metrix/CLAUDE.md 第 5 节第 6 条,含防范对象原文与 2026-11-27 裁决原文)、调用前的 tools 行核对、审查输入、原始转录:`reviews/<提交>/`(各有 `README.txt`)。data-auditor 的脚本与完整 stdout:`audit/ic7_*`、`ic8_*`、`ic9_*`、`ic10_*`,stdout 在 `audit/stdout/impl_c/`。每个提交之后的证据提交(`1900b1fe`、`0cbee197`、`2665ab10`、`cc18466f`)只含 `reports/`、`reviews/`、`audit/`,按 Review Gate 2026-11-27 裁决第 2 项的同类处理不另送审。推送记录:`impl_c/c2_push_work_commit.txt`、`c2b_push_fix_commit.txt`、`c2c_push_fix2_commit.txt`、`c2d_push_fix3_commit.txt`;所有推送都是快进,没有推送标签。
- 问题与处理:`DEFERRED_MINORS.md` 1.32(CF1–CF30)、1.33(CG1–CG22,段首更正 1.32 的 CF28、CF29)、1.34(CH1–CH12)、1.35(CI1–CI11,第三个修复提交;没有 MAJOR,都登记)。按 Task Order 第 9 节,影响协议一致性、数据、指标或隔离的 MAJOR 都已修;协议读法交 Review Gate(下文“待 Review Gate 决定”);其余登记。
- 所有轮次都没有 BLOCKER;连续 3 轮未 PASS 的情形没有出现(metrix/CLAUDE.md 第 5 节第 4 条)。data-auditor 的信任状态仍为「待验证」(第 10 节)。

### 本节执行中出现的问题(都已记录,证据入库)

1. **测试在本仓库运行了 formal(`c2_02`)。** 变异“formal takes a step count”使子进程测试真的以 formal 运行:在 CPU 上停在 ST8 后,把一份 formal 实验记录写进了本仓库的 `results/`,并尝试提交;因暂存区有内容,提交前提 BLOCKED,没有提交,远端未变(`c2_05` 第一行的 ls-remote)。若暂存区为空,这份记录会被推送。处理:第 1 步之前停止的 formal 记录只写 `<work>`(交 Review Gate);子进程测试设无效的 `GIT_DIR`;相关测试改在临时克隆上运行。误写的两个文件作为证据保存在 `impl_c/c2_02_stray_experiment_record_formal.*`(没有删除)。
2. **`/usr/bin/time` 不存在(`c2_03`)。** 冒烟没有开始;重录为 `c2_04`。
3. **并行录制被内核以内存不足杀掉(`c2b_01`、`c2b_02`)。** 杀掉后 Executor 停止仍在运行的变异,被杀的变异进程没有走到恢复文件的 `finally`,工作区 `pilot.py` 留下了一个变异(`if False:`);`c2b_01b_restore_after_kill.txt` 记录了 diff、从暂存区恢复与恢复后的核对;之后录制都单独、依次运行。data-auditor 在 `ic8_07`、`ic9_07` 中核对没有残留。
4. **变异暴露的测试缺口(`c2c_01`)与变异脚本的误指(`c2c_03`)。** `c2c_01` 按 C1 裁决第 7 项保留为被取代的记录;`c2c_03` 中因测试清单误指而未测出的一个变异由 `c2c_04` 补测(CAUGHT),见上表。
5. **笔误。** `c2d_checks.sh` 与 `c2d_01`、`c2d_02` 首行写的父提交 “2665ab17” 应为 `2665ab10`(STATE 中 `git rev-parse HEAD` 一行为准)。
6. **会话中删除的文件。** 只有 Executor 自己导入变异脚本时在 `reports/impl_c/` 下生成的 `__pycache__`(被 `.gitignore` 忽略)与一个空的 `results/` 目录(误写的两个文件移走之后);没有删除任何受跟踪或作为证据的文件。

### 冒烟测试的结果(冒烟值,不构成结论)

最终一次(`impl_c/c2d_02_smoke.txt`,记录副本 `impl_c/c2d_smoke_records/`,不含逐题明细、checkpoint 与数据文件)。冒烟报告(`run_pilot.py smoke --steps 3`,标签 `SMOKE — NOT A RESULT`,运行环境同本节开头,只用 CPU):

- 模型:Qwen3-1.7B 的 `config.json`(SHA-256 `1ddb5b89…`)缩成 2 层、hidden 64 的随机初始化同构小模型(`pilot.SMOKE_MODEL_OVERRIDES`,种子 0;冒烟记录 `small_model`);没有加载权重。设备检查跳过并记录 “smoke: device check skipped”。
- 第 1–8 步都完成,没有中断(`c2d_02` 中每步一行 “done”):第 1 步 3.7 s、第 2 步 33.2 s、第 3 步 31.1 s、第 4 步 196.1 s、第 5 步 417.7 s、第 6 步 455.8 s、第 7 步 90.9 s、第 8 步 5.1 s;进程峰值常驻内存 8278 MiB(CPU);记录 74 个文件(各步的文件清单见 `smoke_report.json` 的 `steps`,work 目录的完整清单与字节数在 `c2d_02` 末尾)。
- 30 次训练全部完成,每次 3 步(`trainings completed: 30; steps per run [3]`);30 行 “state sha256 … (unchanged after reload)”:每个 checkpoint 保存、重载到同结构的新模型后 `state_sha256` 不变(C1 裁决第 3 项)。
- G0.1–G0.10 的冒烟值(`smoke_report.json` 的 `g0_values_smoke`,判定在 `gate0_record.json`):G0.4、G0.5 不满足,其余满足;Gate 0 状态固定为 NOT_TESTED,“冒烟测试，不构成结论”。读取结果值的停止中,第 4 步的 ST3(阳性对照未过)记为 would stop 后继续(`step4_record.json`、`step7_record.json`);随机小模型训练 3 步,这些数值没有意义。
- 第 8 步:以子进程运行 TEST 生成器,退出码 1、`RESULT: FAIL`、`--out` 未创建,work 下没有 TEST 文件(`TEST files: 0`)。
- 冒烟结束后本仓库 `metrix/e1-pilot/results/` 不存在(`c2d_02` 末行),冒烟输出全部在仓库之外的 work 目录;数据、checkpoint、预检目录各有 `LABEL.txt`。

## C3:A100 操作手册与最终报告

- 指令:Owner 本次消息(“然后执行 C3(RUNBOOK_A100.md 与最终报告),C3 只改文档时只需 code-reviewer”);Task Order 第 8、11、13 节;Owner 下达阶段 C 的消息(`tasks/IMPL_C_OWNER_MESSAGE.md`)中的补充裁决 1–6 与“其余按上次阶段 C 指令的第 1、6、7、9、10 项执行”。
- 交付:`RUNBOOK_A100.md`(Task Order 第 8 节第 1–6 项:环境要求与检查命令、下载内容及其 SHA-256、从克隆到运行完毕的命令序列、预检与停止条件的操作、结果的提交、时长与费用;另含补充裁决 6 的租用条件、上次阶段 C 指令第 9 项的磁盘规划与确定性报错的处理、C1 裁决第 6 项的 GitHub 设置、2026-11-27 裁决第 1 项);本报告;`DEFERRED_MINORS.md` 1.35、1.36;原始输出 `impl_c/c3_01_final_checks.txt`(最终检查)、`c3_02_runbook_hashes.txt`(RUNBOOK 中每个哈希与 `DATA_MANIFEST.json` 或所引原始输出的对照)、`c3_hf_tree_70d244cc.txt` 与 `c3_03_hf_tree_logged.txt`(Hugging Face API 中 `Qwen/Qwen3-1.7B@70d244cc` 的文件树与 LFS 元数据;后者用 `logrun.sh` 重新获取并解析,与前者相同;没有下载权重)。录制脚本 `c3_checks.sh`、`c3_evidence.sh`。代码(`src/`、`tests/`、`run_pilot.py`)与第三个修复提交 `a0e04d1f` 相同,没有改动。
- RUNBOOK 中的数值:门槛、超参、种子、哈希由代码从冻结文件读取,RUNBOOK 只列下载后人工核对用的哈希:前 7 项是 `DATA_MANIFEST.json` 中的冻结值;模型的 `config.json` 与两个 safetensors 不是冻结值(冻结的是 revision),分别取自本阶段 CPU 环境下载时打印的值(`impl_c/c1_01_env_fetch.txt`、`c2_01_env_fetch.txt`)与 Hugging Face API 的元数据;对照的原始输出 `c3_02`。时长与费用按 Task Order 第 8 节第 6 项的 1.8 美元/小时,分别给出实际 GPU wall-clock(ST7 读)、预检时 ST11 读到的 B17 估算、B17 与 checkpoint 开销之和三个区间及其依据,写明以预检为准。手册不指定租用平台。

### 最终检查(`impl_c/c3_01_final_checks.txt`)

在第 1 轮送审之前录制。录制开始时的暂存树为 `65b95aca`;录制期间 Executor 在工作区修改了 RUNBOOK 第 2 节与本报告(末尾 `git status` 的 `AM` / `MM`),录制之后暂存了它们与 `c3_01` 本身;第 2 轮之前又只修改了文档与证据(见下)。代码部分不变:首尾都有 `INDEX_EQUALS_a0e04d1f…_FOR_SRC_TESTS_RUN_PILOT`,各轮送审树中 `src/`、`tests/`、`run_pilot.py` 的 blob 与 `a0e04d1f` 的树相同(审查输入 `tree.txt`)。内容:数据重新生成并 verify(四个冻结哈希 PASS)、TEST 生成器拒绝(`--out` 未创建)、`outside_metrix_check.py` PASS、全部 pytest `324 passed`。

### 提交与审查(C3)

| 轮 | 被审暂存树 | code-reviewer | 处理 |
|---|---|---|---|
| 1 | `d27b68da` | BLOCK(1 BLOCKER、5 MAJOR、14 MINOR) | 全部处理,见 `DEFERRED_MINORS.md` 1.36 |
| 2 | `c9dfc4ac` | PASS(没有 BLOCKER、MAJOR;10 MINOR) | 全部在文档中修正(其中提交前确认不含 TEST 文字的范围涉及隔离,按 Task Order 第 9 节必须修),见 `DEFERRED_MINORS.md` 1.37 |
| 3 | 见 `reviews/<C3 提交>/` | 见该目录 | — |

- 按 Owner 指令只送 code-reviewer(调用文字第一句按 metrix/CLAUDE.md 第 5 节第 6 条,含防范对象原文与 2026-11-27 裁决原文)。各轮的调用文字、调用前的 tools 行核对、审查输入、原始转录与原文在其后的证据提交的 `reviews/<C3 提交>/`;推送记录 `impl_c/c3_push_commit.txt` 在同一证据提交中。
- 第 1 轮的 BLOCKER:RUNBOOK 没有写上次阶段 C 指令第 9 项的“确定性模式下 CUDA 算子报错时的处理(停下报告,不得关闭确定性)”。已在 RUNBOOK 第 4 节补写;并在下文“Owner 阶段 C 各项要求的落实”中逐项核对补充裁决 1–6 与上次阶段 C 指令第 1、6、7、9、10 项,以免再漏。
- 本报告写于各轮审查之前。按 metrix/CLAUDE.md 第 5 节,审查为 PASS 才提交本提交(BLOCK 则修复后重审;连续 3 轮未 PASS 则停止),所以本提交存在即表示 C3 的 code-reviewer 在最后一轮为 PASS;最后一轮的新 MAJOR / MINOR 若不改文档,登记写入其后的证据提交。

### 待 Review Gate 决定(C3;已由 2026-11-27 的裁决回答,见“Review Gate 对 C2、C3 待决事项的裁决”第 3–5 项)

1. **租卡前:A100 上的环境安装与下载(1.36 CJ6)。** metrix/CLAUDE.md 第 4 节写“环境、下载、冒烟测试先在 CPU 环境完成;租卡后只跑正式流程”。依赖锁定、输入文件的下载与哈希核对、冒烟都已在 CPU 环境完成;A100 主机是另一台机器,须重新安装依赖、下载输入并由代码再次核对,模型权重只能在 A100 主机下载(Task Order 红线 2)。RUNBOOK 第 3.1–3.4 节因此在租用的机器上执行(约 0.5 小时,计入租用时长)。请确认。
2. **租卡前:运行期间手工提交的审查方式(1.36 CJ5)。** 命令输出(`results/command_output/`)、data-auditor 的计数文件与 audit 输出、审查原文的提交只含输出、不含代码。补充裁决 1 的“证据提交”只限 `reports/`、`reviews/`、`audit/`,作用范围是阶段 C。请决定这些提交是否按证据提交处理(不经 code-reviewer);未裁决时 RUNBOOK 第 5 节按 metrix/CLAUDE.md 第 5 节,每次提交前调用 code-reviewer(frontmatter 比对、固定第一句、原文入 `reviews/<提交>/`,都不在 begin 与 finish 之间推送)。另请一并说明:补充裁决 1,以及 RUNBOOK 依赖的其他“作用范围:本阶段”的裁决(C1 裁决第 2、6 项,2026-11-27 裁决第 1 项),在 A100 运行期间是否仍然有效(“本阶段”指 Implementation 阶段 C 还是 metrix/CLAUDE.md 第 2 节的 E1 Pilot;1.37 CK4)。
3. **两份 L6 计数不同时的实验记录(1.36 CJ11)。** RUNBOOK 第 3.7 节:Executor 比较两份计数,不同则 ST10、BLOCKED、不运行 test-evaluate、报告 Owner。这次停止没有 run_pilot 写的实验记录(协议第 10 节)。可选:由 Owner 批准运行 test-evaluate,让 begin 在写标记之前判 ST10 并写 BLOCKED 记录;或 Executor 手写一份记录。请决定。

## C4:按 Review Gate 2026-11-27 裁决(`tasks/IMPL_C4_RULING.md`)的修改

- 指令:Owner 本次消息(`tasks/IMPL_C4_RULING.md`,首段与裁决第 1–7 项):代码提交送两份审查,调用文字写入 C1 裁决的防范对象原文;只改文档的提交只送 code-reviewer;完成后状态仍为 IMPLEMENTATION_READY,停下。
- 执行会话:session_01J5mxaYCbCJdFzWS6Pah7n5(第四个阶段 C 会话)。本地分支 `metrix-e1-pilot-protocol-v1` 设为 `origin/metrix-e1-pilot-protocol-v1`(`3bc761ea`)后在其上工作;会话分支 `claude/review-gate-ruling-c4-u1cyxh` 没有使用。
- 运行环境:Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,没有 nvidia 设备与 `nvidia-smi`(`impl_c/c4_01_env_fetch.txt`);Python 3.13.18;依赖按 `requirements.lock` 以 `--require-hashes --no-deps` 装入会话临时目录的 venv(pip 先固定为 26.3),`pip check` 通过,torch `2.11.0+cu130`(`torch.cuda.is_available()` False),transformers 5.22.2。下载的只有 4 个分词器文件、parcae `tokenizer.json`、锚文本 parquet 与固定 revision 的 `config.json`(哈希与冻结值相同,`c4_01`);没有下载或加载任何权重,没有使用 GPU,没有生成、读取或统计 TEST。

### 交付

- **代码提交 `a09e154e`**(树 `63121c79`;C4 裁决第 1 项):
  - `pilot.st11_estimate_hours` = B17 估算 + checkpoint 开销 / 3600。预检把它与两部分写入第 2 步记录(`b17_estimate_hours`、`checkpoint_overhead {seconds, counts}`、`st11_estimate_hours`、`st11_reads`;原来只报告的两个字段 `checkpoint_overhead_report_only`、`b17_plus_checkpoint_overhead_hours_report_only` 由这些字段取代),`step2` 的 ST11 读 `st11_estimate_hours`。`stops.st11` 不变:超过 3.5 小时停止,等于 3.5 小时不停。
  - ST7 的事前判断(`run_seconds`、`eval_seconds`、`test_evaluation_seconds`)不变,只改文档字符串;TEST 的事前估计不加余量。`checkpoint_overhead_seconds`、`evaluation_plan` 的计算不变。
  - B17:text 写明 ST11 读两者之和及 checkpoint 开销的组成;status `ACCEPTED（Review Gate 2026-11-27 修订）`(`interpretations.ACCEPTED_C4`),ruling `tasks/IMPL_C4_RULING.md 第 1 项`(`RULING_REF_C4`)。`pending()` 仍为空。
  - 测试:`test_preflight_overhead_counts` 加 `st11_estimate_hours` 的数值断言;新增 `test_formal_st11_reads_b17_plus_the_checkpoint_overhead[sum_over_bound, sum_at_bound]`(formal 在带裸远端的临时克隆上,真实的预检;B17 估算设为 3.0 h、开销设为 1801 s / 1800 s:前者 ST11、BLOCKED、第 2 步记录带停止并已推送、没有第 3 步;后者正好 3.5 h,不停);`test_interpretations_ruled_by_review_gate` 改为 B17 的 status、ruling 与裁决原文。全部测试由 324 项增至 326 项。
  - 变异 `impl_c/c4_mutate.py` 9 个(ST11 只读 B17、不加开销、开销按分钟、预检只取 B17、在上限处即停、B17 的 status 或 text 未修订、TEST 事前估计加 10% 余量、ST7 的训练事前估计少算保存),全部测出。
  - 裁决原文 `tasks/IMPL_C4_RULING.md`(本次消息全文)随该提交入库。
- **裁决第 2 项**:没有改代码。`pilot.py` 中仍写着这些事项 “is for Review Gate” 的注释与文档字符串(`step7` 中 G0.2 对剔除配置的读法、`gate_steps` 中 Gate 0 PASS 的状态词、`run_gate` 中崩溃的状态词、`final_record` 中第 1 步之前停止的记录是否入库)按“不改代码”的字面保留,登记为 `DEFERRED_MINORS.md` 1.39 CM3,见下文“待 Review Gate 决定(C4)”第 1 项。
- **文档提交(本提交)**:`RUNBOOK_A100.md`(C4 裁决第 1、3–7 项,逐项见“Review Gate 对 C2、C3 待决事项的裁决”的落实;第 2 轮按第 1 轮审查修改,见下文);本报告;`DEFERRED_MINORS.md` 1.39、1.40;`impl_c/c4_04_uv_check.txt`(第 6 项的 uv 路径核对,第 2 轮追加 `UV_*` 变量);检查脚本与输出 `impl_c/c4_docs_checks.sh` → `c4_05_docs_checks.txt`(第 1 轮)、`c4_docs_checks_r2.sh` → `c4_06_docs_checks_r2.txt`(第 2 轮)、`c4_docs_checks_r3.sh` → `c4_09_docs_checks_r3.txt`(第 3 轮);RUNBOOK 命令的模拟:`impl_c/c4_runbook_sim.sh` → `c4_07_runbook_sim.txt`(第 2 轮:3.0 的变量文件、3.1 的 REPO 一行、3.2a 两个分支与一个新 shell;被取代的第一次运行 `c4_07_runbook_sim_trial1_script_error.txt`),`c4_runbook_sim_r3.sh` → `c4_08_runbook_sim_r3.txt`(第 3 轮:另加长命令的 `send-keys` 一行与 GPU 秒数的命令,都从 RUNBOOK 原样取出;都不含依赖安装、下载与 run_pilot.py)。

### 检查(代码提交的被审暂存树;运行环境见本节开头)

| 项 | 结果 | 位置 |
|---|---|---|
| 被测代码即暂存内容 | 首尾都有 `WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT`,代码 diff 的 sha256 首尾都是 `e8df1988…`,写树 `178c9a2f`(暂存录制与冒烟记录副本之前的树) | `impl_c/c4_02_checks.txt`、`c4_03_smoke.txt` 首尾 |
| 数据重新生成、verify、四个冻结内容哈希 | PASS | `c4_02` |
| TEST 生成器(当前状态) | 拒绝(Gate 0 记录未提交),`--out` 未创建,没有 `results/` | `c4_02` |
| outside_metrix_check | PASS | `c4_02` |
| pytest 全部 | `326 passed` | `c4_02` |
| 变异(`c4_mutate.py`) | 9 个全部测出,前后 src/tests/run_pilot 的 sha256 相同 | `c4_02` |
| 冒烟(`run_pilot.py smoke --steps 3`,单独运行) | 第 1–8 步各一行 “done”;30 次训练,30 行 “unchanged after reload”;预检一行 “B17 estimate 2.008 h + checkpoint overhead 0.010 h = 2.019 h (ST11, bound 3.5 h)”,第 2 步记录 `st11` 为 “within bound”;第 8 步生成器拒绝,`TEST files: 0`;`RESULT: PASS`(冒烟值,不构成结论) | `c4_03`;记录副本 `impl_c/c4_smoke_records/`(不含逐题明细、checkpoint 与数据文件) |

### 提交与审查(C4)

| 提交 | 内容 | 被审暂存树 | code-reviewer | data-auditor(仅作参考) |
|---|---|---|---|---|
| `a09e154e` 代码提交 | 见“交付” | `63121c79` | PASS(没有 BLOCKER、MAJOR;10 MINOR) | PASS(3 MINOR、1 条说明) |
| `c9481c85` 证据提交 | `reviews/a09e154e…/`、`audit/ic11_*` 与其 stdout、推送记录 `impl_c/c4_push_code_commit.txt` | 不送审(只含 `reports/`、`reviews/`、`audit/`,补充裁决 1) | — | — |
| 本提交(文档),第 1 轮 | 见“交付” | `7501c291` | PASS(没有 BLOCKER;1 MAJOR、12 MINOR) | 不送(只改文档;C4 裁决末段) |
| 本提交(文档),第 2 轮 | 第 1 轮的问题全部在文档中修正(`DEFERRED_MINORS.md` 1.40) | `26e3556b` | PASS(没有 BLOCKER、MAJOR;12 MINOR) | 不送 |
| 本提交(文档),第 3 轮 | 第 2 轮的问题除 CO6、CO9 外在文档中修正(`DEFERRED_MINORS.md` 1.41) | 见 `reviews/<本提交>/` | 见该目录 | 不送 |

- 代码提交的两份审查:调用文字第一句按 metrix/CLAUDE.md 第 5 节第 6 条,含 C1 裁决的防范对象原文与 `tasks/IMPL_C4_RULING.md` 全文;调用前的 tools 行核对、审查输入、原始转录与原文在 `reviews/a09e154e…/`(`README.txt`、`notes.txt`)。data-auditor 独立复算了冒烟第 2 步的 B17 估算、checkpoint 开销与两者之和(与记录相同)、以新测试的两个参数为驱动的预期(运行前写出,与结果相同)、冒烟数据与 30 次训练(`audit/stdout/impl_c/ic11_*`)。
- 文档提交只送 code-reviewer(C4 裁决末段)。本报告写于审查之前;按 metrix/CLAUDE.md 第 5 节,审查为 PASS 才提交,所以本提交存在即表示最后一轮为 PASS;各轮的调用文字、核对、输入、转录与原文,以及本提交的推送记录,在其后的证据提交的 `reviews/<本提交>/` 与 `impl_c/` 中。
- 问题与处理:`DEFERRED_MINORS.md` 1.39(代码提交两份审查的 MINOR)、1.40(文档提交第 1 轮,MAJOR CN1 为 RUNBOOK 中的变量在新的 tmux 窗口或命令调用中可能为空,已修并在会话临时目录中模拟)、1.41(文档提交第 2 轮)。第 3 轮之后的新问题登记于其后的证据提交,不再改文档(C3 的先例)。按 Task Order 第 9 节,影响协议一致性、数据、指标或隔离的已修;其中 RUNBOOK 与代码不一致(CM1)由本提交修正,其余登记。

### 本节执行中出现的问题(都已记录)

1. **过早的提取。** 等待 data-auditor 时,Executor 的等待条件匹配到转录中的工具名 “SubagentHandback”(不是调用),提取脚本提前运行,取到一条 50 字的中间文字。该结果作废,保存为 `reviews/a09e154e…/premature_extract_data-auditor_discarded.md`;正式原文是 data-auditor 交回之后重新提取的(`extract_log_round1.txt`,`notes.txt`)。
2. **会话进程重启。** 等待 data-auditor 期间本会话的工作进程重启过一次;重启后核对暂存树仍为 `63121c79`、HEAD 为 `3bc761ea`,再提交(`impl_c/c4_push_code_commit.txt` 中 `HEAD^{tree}` 为 `63121c79`)。
3. **uv 的版本。** 容器预装的 uv 0.11.32 不列出 CPython 3.13.18 的下载,PyPI 上的 uv 0.13.10 列出并装成(`c4_04`)。RUNBOOK 的 3.2a 因此从 PyPI 安装 uv(第 2 轮起固定为 0.13.10),网络一行以 `--show-urls` 显示的主机及其重定向目标为准(本阶段为 `releases.astral.sh`,只在 3.2a 时)。没有在 uv 装的解释器上安装依赖或运行测试。
4. **uv 在容器中留下的链接。** `c4_04` 中的 `uv python install`(安装目录设在会话临时目录)另在 `/root/.local/bin/python3.13` 建了指向该解释器的链接(12:47),此后本容器中 `python3.13` 先解析到它(同为 CPython 3.13.18)。所有测试、冒烟与 data-auditor 的运行都用会话开始时由 `/usr/local/bin/python3.13` 建的 venv,不受影响;`c4_07` 模拟中“主机已有 3.13.18”的分支取到的是这个链接(版本核对同样通过)。该链接在会话临时目录之外,没有删除(metrix/CLAUDE.md 第 7 节)。
5. **模拟脚本的第一次运行。** `c4_runbook_sim.sh` 在 `cd` 之后以相对路径读 RUNBOOK,第一次运行失败(`c4_07_runbook_sim_trial1_script_error.txt`,按 C1 裁决第 7 项保留);改为传绝对路径后重跑为 `c4_07`,脚本本身没有改。
6. **会话中删除的文件。** 只有会话临时目录中的文件(过早提取时复制的转录副本、模拟的临时目录);没有删除任何受跟踪或作为证据的文件。

### 待 Review Gate 决定(C4;第 1、2 项已由 2026-11-28 的裁决回答,见“Review Gate 对 C4 待决事项的裁决”;第 3 项仍待 Owner 确认,转列于 C5 节)

1. **只改注释是否属于“不改代码”(1.39 CM3)。** C2 待决第 1、3、5 项已按现行实现接受,但 `pilot.py` 中 4 处注释或文档字符串仍写 “is for Review Gate”;冒烟实验记录的 “Next (single)” 为 “Review Gate reviews the smoke report (C2)”(只出现在冒烟记录中)。Executor 按裁决第 2 项的字面没有改动。请指示:允许时,在下一个代码提交中只改这些措辞为“按现行实现接受(`tasks/IMPL_C4_RULING.md` 第 2 项)”,送两份审查。
2. **1.38 中 RUNBOOK 的操作细节(CL2–CL6)。** C3 第 3 轮登记、处理列写“正式运行指令之前修正”的几项(venv 与 pip 缓存的分区、glibc、`env.txt` 与 `fetch.txt` 带时间;`Pilot()` 内失败、以回溯结束的 test-evaluate、Ctrl-C 结束的 formal 怎样处理;第 3.7 节列入转录)不在 C4 裁决第 7 项所列的修改之内,本提交没有改。请指示是否在下达正式运行指令之前,以只改文档的提交修正(送 code-reviewer)。
3. **RUNBOOK 中的分工(1.41 CO6)。** RUNBOOK 第 1 节写为:Claude Code 在 A100 主机上的安装与登录,以及第 3.0–3.1 节(驱动检查、tmux 会话、变量文件、克隆与检出),由 Owner 或 Owner 指定的人完成,之后由 Claude Code 接手。C4 裁决第 7 项只要求写明前提,没有指定由谁做。请 Owner 确认这一分工,或指定其他做法。
4. **提请注意(不需裁决):** 按 RUNBOOK 第 6 节的规划区间,ST11 读到的和约 1.6–4.2 小时,区间上端超过 3.5 小时。若 A100 上实测落在上端,`formal` 会在第 2 步以 ST11 停止(BLOCKED),此时已用掉环境安装、下载与预检的租用时间(约 0.6 小时)。

## C5:按 Review Gate 2026-11-28 裁决(`tasks/IMPL_C5_RULING.md`)的 RUNBOOK 修正

- 指令:Owner 本次消息(`tasks/IMPL_C5_RULING.md`,首段与裁决第 1–5 项):直接在 `metrix-e1-pilot-protocol-v1` 上工作,只做快进推送,不推送标签,不经 PR;一次纯文档提交,只送 code-reviewer 一轮(有 BLOCKER 则修复后再送,否则直接提交;新的 MAJOR、MINOR 只登记);不改 `src/`、`tests/`、`run_pilot.py`;完成后状态仍为 IMPLEMENTATION_READY,停下。
- 执行会话:session_01J5mxaWUR9DL7AWpZWbGZsH(第五个阶段 C 会话)。本地分支 `metrix-e1-pilot-protocol-v1` 设为 `origin/metrix-e1-pilot-protocol-v1`(`377bc736`)后在其上工作;会话分支 `claude/c5-ruling-runbook-update-sikcvi` 没有使用。
- 运行环境:Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,没有 nvidia 设备与 `nvidia-smi`;系统 Python 3.13.18(`/usr/local/bin/python3.13`,有 ensurepip)(`impl_c/c5_00_session_start.txt`)。RUNBOOK 命令的模拟按 s3_2 把 `requirements.lock` 装入会话临时目录中的 venv,并按 s3_4_data、s3_4_config 下载分词器、锚文本 parquet 与固定 revision 的 `config.json`(`impl_c/c5_01_runbook_sim.txt`);没有下载或加载任何权重,没有使用 GPU,没有生成、读取或统计 TEST。

### 交付

- 裁决原文 `tasks/IMPL_C5_RULING.md`(本次消息全文)。
- `RUNBOOK_A100.md`(C5 裁决第 2、3 项;逐项与 `DEFERRED_MINORS.md` 各行处理列末尾的“已修(C5 文档提交)”对应):
  - CL2:变量文件加 `VENV`(所选分区上的 `metrix-venv`),3.2 的 venv 建在 `$VENV`;两次 pip 加 `--no-cache-dir`,锁定文件的安装以 `TMPDIR=$VENV.tmp` 运行;第 1 节磁盘一行写明 venv 与安装时的临时文件在该分区、家目录只放变量文件(及 3.2a 走 uv 分支时的 uv 与解释器);第 3.0 节核对加 glibc ≥ 2.28;`env.txt`、`fetch.txt` 只用 `tee -a` 追加、每段以 `date -u` 开头,命令不自行重跑。
  - CL3:第 3.5 节之后加第三种情况:以回溯退出且工作区 `results/` 中没有本次的实验记录(开始时间不早于 `formal_<时间>.txt` 的时间)时,不提交,连同命令输出报告 Owner。
  - CL4:第 3.8 节加一段:以回溯结束的三种情况;`results/` 中已有标记或结果则 TEST 视为已评、不得重跑,报告 Owner;都没有时同样不重跑,报告 Owner。
  - CL5:第 3.7 节第 3 项列入 data-auditor 的转录(`data-auditor_transcript.jsonl`),第 5 节同步。
  - CL6:第 4 节例外加一条:`formal` 被 Ctrl-C 或 SIGHUP 结束时没有实验记录,不得重跑,不提交,报告 Owner。
  - CP1:第 3 节把 8 条长命令逐条标出窗口名(`s3_2a`、`s3_2`、`s3_4_data`、`s3_4_config`、`s3_4_model`、`formal`、`test_generate`、`test_evaluate`),每个脚本只放一条长命令;第 1 节写明 `.end` 只有脚本最后一行的退出码、前一条 `exit=0` 且第 3 节的核对通过才发送下一条;3.6、3.8 的 `git pull --ff-only` 在 Claude Code 中前台运行,成功后再发送;s3_2a 之后核对 `env.txt` 中最后一个 `PY313=` 行的下一行为 `CPython 3.13.18`,s3_2 之后核对末行为 pip check 的 “No broken requirements found.”;send 一行的前提(`$WORK` 不含空格、窗口 shell 认识 `$?`)写明。
  - CP2:第 5 节列入长命令的 `<窗口名>.sh.txt`、`<窗口名>.end.txt`,提交前 `git check-ignore -v` 应无输出、退出码 1;占位符分为 `<窗口名>` 与 `<输出文件名>`。
  - CP3:第 1 节改为“test-generate 写出 TEST 文件之后、test-evaluate 写出标记之后不得重跑;此前的拒绝是否重发由 Owner 决定”;Owner 决定重发时用新的窗口名。
  - CP4:GPU 秒数的命令取 `t = time.time()`,经 `GpuClock` 的构造参数 `now` 传入,打印累计秒数、`open`、`t` 与其 UTC 时间;不再调用私有方法 `_state()`。
  - CP5(裁决第 3 项):第 1 节 Python 一行、第 3.0 节说明与 3.2a 注释同步为“没有 CPython 3.13.18,或有而不能建 venv(缺 ensurepip)”时用 uv。
  - 总则(裁决第 2 项):第 4 节开头照录原文,后接一句:本手册对某种结束已写明的其余处理(提交输出、手写记录)照做,“保留输出”指不删除、不改动 `<work>/command_output/` 中的文件(见下文“待 Review Gate 决定(C5)”第 2 项)。各处“不自行重跑”引用总则。
  - 开头“依据”加 C5 裁决。
- `DEFERRED_MINORS.md`:1.38 首段与 CL2–CL6、1.39 首段与 CM3(裁决第 1 项)、1.42 首段与 CP1–CP5 的处理列;第 3 节加 C5 一条。
- 本报告:开头、“Review Gate 对 C4 待决事项的裁决”、C4 节“待 Review Gate 决定(C4)”的标题、本节、验收第 8 项与“最终状态”。
- 证据:`impl_c/c5_00_session_start.txt`;RUNBOOK 命令的模拟 `impl_c/c5_runbook_sim.sh` → `c5_01_runbook_sim.txt`;文档检查 `impl_c/c5_docs_checks.sh` → `c5_02_docs_checks.txt`(被取代的第一次运行 `c5_docs_checks_trial1.sh` → `c5_02_docs_checks_trial1_script_error.txt`,见下文“本节执行中出现的问题”第 2 项)。

### 检查(本节开头的运行环境)

| 项 | 结果 | 位置 |
|---|---|---|
| 3.0 的变量文件与 `env.txt` 一行、3.1 的 REPO 与身份两行(从 RUNBOOK 原样取出,占位符换成会话临时目录中的“分区”,在 `env -i` 的 shell 中运行) | 退出码 0;变量文件含 `VENV`;`env.txt` 各段以 `date -u` 开头,只追加 | `impl_c/c5_01_runbook_sim.txt` |
| 长命令 `s3_2a`:按第 1 节写脚本(第一行 + RUNBOOK 中的各行),用第 1 节的 send 一行在 `env -i` 的 shell 中发送 | `s3_2a.end` 为 `exit=0`;`env.txt` 中 `PY313=/usr/local/bin/python3.13` 的下一行是 `CPython 3.13.18`(主机分支;uv 分支没有运行,c4_08 运行过) | `c5_01` |
| 长命令 `s3_2`:venv 在 `$VENV`,两次 pip `--no-cache-dir`,锁定文件的安装以 `TMPDIR=$VENV.tmp` | `exit=0`;`env.txt` 末行 `No broken requirements found.`;安装期间 `$VENV.tmp` 最大约 2.6 GiB(每 2 秒取样,180 次),结束后 4 KiB;HOME 下没有 `.cache`;venv 4.8 GB | `c5_01` |
| 长命令 `s3_4_data`、`s3_4_config`(各用一个窗口名,写入同一个 `fetch.txt`) | 都是 `exit=0`;6 个冻结输入的 SHA-256 与冻结值相同,`config.json` 为 `1ddb5b89…`;`fetch.txt` 两段各以 `date -u` 开头 | `c5_01` |
| 3.7 的 GPU 秒数命令(两个人造 `gpu_clock.json`) | 只有已关闭的段:`15.5 None <t> <UTC>`;有未关闭的段(开始于 t₀):`111.108… <t₀> <t> <UTC>`,即 10 + (t − t₀) | `c5_01` |
| 第 5 节的文件名(`env.txt`、`formal_<时间>.txt`、`formal.sh.txt`、`formal.end.txt`)与 `.gitignore` | `git check-ignore -v` 无输出,退出码 1 | `c5_01` |
| 文档检查:暂存路径的 blob 与 diff 的 sha256(首尾);`src/`、`tests/`、`run_pilot.py` 与父提交相同;暂存路径都在 `metrix/e1-pilot/` 下;总则原文在 RUNBOOK 中;旧占位符、私有方法、家目录 venv、待决措辞不再出现;8 条长命令都有标注;`env.txt`、`fetch.txt` 没有不带 `-a` 的 `tee`;3.7 的手写记录模板与协议第 10 节的 20 个字段一致;`outside_metrix_check` | 见 `c5_02`(本报告写于其运行之前;任一项不符则不送审、不提交) | `impl_c/c5_02_docs_checks.txt` |

没有覆盖:3.3(要 CUDA)、`s3_4_model`(权重只在 A100 主机下载)、`formal`、`test-generate`、`test-evaluate`,以及 3.2a 的 uv 分支。模拟中 tmux 服务器由模拟脚本的 shell 启动,使窗口带上本容器的 HTTPS 代理设置(A100 主机上没有);send 一行本身在 `env -i` 的 shell 中运行。

### 提交与审查(C5)

| 提交 | 内容 | 被审暂存树 | code-reviewer | data-auditor |
|---|---|---|---|---|
| 本提交(文档),唯一一轮 | 见“交付” | 见 `reviews/<本提交>/` | 见该目录 | 不送(只改文档;裁决第 4 项) |

- 只送 code-reviewer 一轮(裁决第 4 项):调用文字第一句按 metrix/CLAUDE.md 第 5 节第 6 条,含 C1 裁决的防范对象原文与 `tasks/IMPL_C5_RULING.md` 全文;调用前核对仓库文件与已加载定义的 tools 行。本报告写于审查之前;审查有 BLOCKER 则修复后再送,没有才提交,所以本提交存在即表示最后一轮没有 BLOCKER。调用文字、核对、输入、转录与原文,本提交的推送记录,以及本轮新的 MAJOR、MINOR 的登记(`DEFERRED_MINORS.md` 1.43),在其后的证据提交中。

### 本节执行中出现的问题(都已记录)

1. **两个空目录。** 用 `git check-ignore` 核对第 5 节的文件名时,先建了 `metrix/e1-pilot/results/` 与其下的 `command_output/`,随即删除(都是本会话所建,其中从来没有文件;`git check-ignore` 不需要路径存在,`c5_01` 中的核对是在它们不存在时运行的)。没有删除任何受跟踪或作为证据的文件;会话临时目录中的模拟目录不入库。
2. **文档检查的第一次运行。** `c5_docs_checks.sh` 第一次运行时,“总则原文在 RUNBOOK 中”一项用 `grep -o` 的多字节括号表达式取原文;本容器的 locale 为 POSIX,表达式没有匹配,取到空串,`grep -c` 于是数出 RUNBOOK 的全部 275 行,退出码仍为 0,这一项的结果无效(其余各项不受影响)。按 C1 裁决第 7 项保留:输出 `impl_c/c5_02_docs_checks_trial1_script_error.txt`,当时的脚本 `c5_docs_checks_trial1.sh`(sha256 与该输出中记录的 `31d7bc5d…` 相同)。改为用 Python 以 UTF-8 读两个文件、原文为空或在 RUNBOOK 中不是恰好一次即失败,重跑为 `c5_02`。

### 待 Review Gate 决定(C5)

1. **RUNBOOK 中的分工(1.41 CO6,转自 C4 第 3 项,C5 裁决没有涉及)。** RUNBOOK 第 1 节写为:Claude Code 在 A100 主机上的安装与登录,以及第 3.0–3.1 节,由 Owner 或 Owner 指定的人完成,之后由 Claude Code 接手。请 Owner 确认这一分工,或指定其他做法。
2. **提请注意:总则之后的一句。** 总则原文之后,Executor 加了一句说明它与已写处理的关系(第 3.5 节之后与第 5 节的提交输出、第 3.7 节第 5 项的手写记录照做;“保留输出”指不删除、不改动输出文件)。这是 Executor 的读法:总则的四个动作(不重跑、不修补、保留输出、报告 Owner)与提交输出不冲突。若 Review Gate 认为总则之下这些提交也应等 Owner 指示,请指示,RUNBOOK 删去该句并相应修改。
3. **提请注意:处理列之外的两处补充。** (a) CL2 的处理列写的是 venv 放在所选分区与 `--no-cache-dir`;Executor 另让锁定文件的安装以 `TMPDIR=$VENV.tmp` 运行,因为 pip 不用缓存时仍把下载的 wheel 暂存在 `TMPDIR`(默认 `/tmp`,常在根分区),不改变装入的内容(`c5_01` 记录了安装期间 `$VENV.tmp` 的大小)。(b) CP1 的问题列含 send 一行的两个前提(`$WORK` 不含空格、shell 认识 `$?`),处理列没有列;Executor 在第 1 节与第 3.0 节写明了这两个前提,没有改 send 一行本身。
4. **提请注意(不需裁决,同 C4 第 4 项):** ST11 读到的和的规划区间上端超过 3.5 小时。

## Owner 阶段 C 各项要求的落实

| 要求(`tasks/IMPL_C_OWNER_MESSAGE.md`) | 落实 | 证据 |
|---|---|---|
| 补充裁决 1:证据提交只 `git add` 明确路径,只涉及 `reports/`、`reviews/`、`audit/` | 各证据提交均如此 | 只列一例:`impl_c/c1_07_stop_commit_precheck.txt`;其余证据提交可由 `git show --stat <提交>` 核对 |
| 补充裁决 2:ACCEPTED 标记引用本报告“Review Gate 对阶段 B 的裁决” | C1 | 本报告该节第 1 项落实 |
| 上次指令第 1–5 项(对阶段 B 的裁决:B1–B24 与 B3、B14;UTF-8 解码;生成器第 4 个前提;B19;推送记录) | C1;B3 的 manifest 写入在 C2 的第 1 步 | 本报告“Review Gate 对阶段 B 的裁决”一节;C2 节“交付” |
| 补充裁决 3:ST10 记录与闸门 | C1(`testgate`、`test_data`) | C1 节;`tests/test_testgate.py` |
| 补充裁决 4:TEST 只评一次(标记) | C1;C2 的 test-evaluate 为生产调用方 | C1、C2 节;`tests/test_run_pilot.py::test_test_evaluate_end_to_end_once` 等 |
| 补充裁决 5:用人造 TEST 行在临时仓库中测试 | C1、C2 | 同上 |
| 补充裁决 6:只租 CUDA ≥ 13.0(驱动 ≥ 580)的机器,写明租用前的检查命令 | RUNBOOK 第 1 节开头与第 3.0 节 | `RUNBOOK_A100.md` |
| 上次指令第 6 项:BE2、BE9、BE10、BE12、BE13 | C1 | C1 节 |
| 上次指令第 7 项:TEST 评测的两个硬性前提及测试;调用方加入后 data-auditor 复审 TEST 路径 | C1;C2 中 data-auditor 复审(`audit/ic7_*`–`ic10_*` 的 e2e 驱动) | C1、C2 节 |
| 上次指令第 8 项:已由补充裁决 6 取代 | — | — |
| 上次指令第 9 项:RUNBOOK 写明磁盘规划(约 6.9 GB/个)与确定性报错的处理 | RUNBOOK 第 1 节“磁盘”、第 4 节“确定性模式下的 CUDA 算子报错” | `RUNBOOK_A100.md` |
| 上次指令第 10 项:冒烟小模型由 config.json 构造时写明其 SHA-256 | `1ddb5b89…`,写在冒烟记录 `smoke_report.json` 的 `small_model.config_json_sha256` 与本报告 C2 节 | `impl_c/c2d_smoke_records/smoke_report.json` |

## 阶段 C 验收(Task Order 第 11 节)

| # | 验收项 | 结果 | 证据(原始输出) |
|---|---|---|---|
| 1 | 单元测试全部通过,原始输出入库 | 满足 | 第三个修复提交的被审暂存树:`impl_c/c2d_01_checks.txt`(`324 passed`);C3 的暂存树(代码相同):`impl_c/c3_01_final_checks.txt`(`324 passed`;首尾 `INDEX_EQUALS_a0e04d1f…`);C4 代码提交的被审暂存树:`impl_c/c4_02_checks.txt`(`326 passed`) |
| 2 | 四个冻结哈希由正式代码重新生成,完全一致;data-auditor 独立复算一致 | 满足(data-auditor 的结论仅作参考,metrix/CLAUDE.md 第 10 节) | `c2d_01`、`c3_01`:`metrix_e1.data generate` 与 `verify`;冒烟第 1 步(`c2d_02`);C4:`c4_02`、冒烟 `c4_03`;data-auditor:`audit/stdout/impl_c/ic10_01_hashes.txt`、`ic11_01_hashes.txt`(以及 `ic7_*`–`ic9_*`) |
| 3 | `run_pilot.py --smoke` 从第 1 步跑到第 7 步无中断,30 次训练全部完成,冒烟报告完整 | 满足(入口为子命令 `run_pilot.py smoke --steps 3`,C2 待决第 7 项) | `impl_c/c2d_02_smoke.txt`:第 1–8 步各一行 “done”,30 行训练(每行 “unchanged after reload”),冒烟报告(每步耗时、峰值内存、文件数,G0.1–G0.10 的冒烟值,`trainings completed: 30`),work 目录文件清单与标签;记录副本 `impl_c/c2d_smoke_records/`。C4 代码提交上重跑:`impl_c/c4_03_smoke.txt`、`c4_smoke_records/`(同样完整) |
| 4 | TEST 生成器在当前状态下拒绝运行;全程没有任何 TEST 内容产生 | 满足 | `c2d_01`、`c3_01`:`metrix_e1.test_data` 退出码 1、`RESULT: FAIL`、`--out` 未创建;冒烟第 8 步以子进程运行生成器,拒绝,work 下没有 TEST 文件(`c2d_02`;C4:`c4_02`、`c4_03`);测试中的 TEST 行都是测试自写的人造行,在临时仓库中 |
| 5 | 正式模式下无法使用冒烟的缩减参数(有测试证明) | 满足 | `tests/test_run_pilot.py::test_formal_commands_have_no_step_option`、`test_only_smoke_builds_a_shortened_mode`;变异 “formal takes a step count” 等被测出(`c2d_01` 变异段) |
| 6 | 每个工作提交的 code-reviewer 为 PASS 且无 BLOCKER | 满足 | 阶段 A:工作提交 `602a39e8`、修复提交 `219c4a60`(`reports/IMPL_A_REPORT.md`;`reviews/602a39e8…/code-reviewer_round1.md`、`_round2.md`,`reviews/219c4a60…/code-reviewer.md`)。阶段 B:`74a4d444`、`fdbb9def`、`493d7f9c`(`reports/IMPL_B_REPORT.md`;`reviews/74a4d444…/code-reviewer_round1.md`、`_round2.md`,`reviews/fdbb9def…/`、`reviews/493d7f9c…/code-reviewer.md`)。阶段 C:`ae60e0f7`、`b48fe842`(C1),`5219ff77`、`49fc9a35`、`dd65a361`、`a0e04d1f`(C2),各 `reviews/<提交>/code-reviewer_round1.md`;C3 提交(只改文档,最后一轮 PASS 才提交,见 C3 节);C4 代码提交 `a09e154e`(`reviews/a09e154e…/code-reviewer_round1.md`)与 C4 文档提交(见 C4 节)。另:第一次阶段 C 尝试中误入代码的 `1435a74` 已向前撤回并由补充裁决 1 追认(本报告开头);C1 第一次送审的 3 轮未 PASS 没有提交代码(停止提交 `5f5cd51e`) |
| 7 | `outside_metrix_check.py` 通过 | 满足 | `c2d_01`、`c3_01`、`c4_02`、`c4_05`:`reports/round3/outside_metrix_check.py` 输出 `RESULT: PASS` |
| 8 | `RUNBOOK_A100.md` 完整,含时长与费用估算 | 满足(C3 提交在 code-reviewer PASS 之后才提交) | `RUNBOOK_A100.md` 第 1–6 节对应 Task Order 第 8 节第 1–6 项;第 6 节:实际 GPU wall-clock 约 1.2–3.1 小时,GPU 部分费用约 2.2–5.6 美元(按租用时长约 3.6–9.0 美元);另列预检时 ST11 读到的估算(B17 估算 + checkpoint 开销,C4 裁决第 1 项)约 1.6–4.2 小时,区间上端超过 3.5 小时会触发 ST11。C4 文档提交按 C4 裁决第 7 项更新;C5 文档提交按 C5 裁决第 2、3 项修正操作细节(C5 节) |

## 最终状态

**IMPLEMENTATION_READY**(Task Order 第 13 节)。之后由 Owner 决定是否租用 A100 并执行正式运行;正式运行另发运行指令。

C2 节“待 Review Gate 决定”第 1–7 项与 C3 节第 1–3 项已由 Review Gate 2026-11-27 的裁决(`tasks/IMPL_C4_RULING.md`)回答:第 2 项(ST11)改了代码并经两份审查(C4 代码提交 `a09e154e`),其余按现行实现接受或只改 RUNBOOK(C4 文档提交)。新的待决事项见 C4 节“待 Review Gate 决定(C4)”:只改注释是否允许(第 1 项),1.38 中 RUNBOOK 操作细节的修正时机(第 2 项),RUNBOOK 中第 3.0–3.1 节与 Claude Code 安装的分工(第 3 项,请 Owner 确认)。Executor 认为这些都不阻碍 IMPLEMENTATION_READY。

C4 节的第 1、2 项与 1.42 CP5 已由 Review Gate 2026-11-28 的裁决(`tasks/IMPL_C5_RULING.md`)回答:注释不改,登记;RUNBOOK 的操作细节由 C5 文档提交修正(只改文档,只送 code-reviewer 一轮);CP5 确认。正式运行之前不再提交代码改动。尚待回答的见 C5 节“待 Review Gate 决定(C5)”(第 1 项分工请 Owner 确认;第 2、3 项提请注意)。状态仍为 **IMPLEMENTATION_READY**,停下,等待 Owner 的下一步指令。
