# E1-PILOT Implementation 阶段 C 报告

**状态:C1 完成(第二次送审通过:工作提交 `ae60e0f7`、修复提交 `b48fe842`);因审查额度用尽(恢复时间 2026-11-29 17:00 UTC),在 C1 与 C2 之间停下。** 第一次送审在连续 3 轮未 PASS 后停止(`5f5cd51e`,只提交了证据);Review Gate 对 C1 的裁决(2026-11-25,`tasks/IMPL_C1_RULING.md`)之后按裁决修改、重新送审,见 C1 节“第二次送审(按裁决修改)”。C1 节其余各小节记录第一次送审,保持原样。

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
