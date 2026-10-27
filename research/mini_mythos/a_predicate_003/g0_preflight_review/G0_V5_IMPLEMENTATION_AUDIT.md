# G0_V5_IMPLEMENTATION_AUDIT — G0 V5 工具实现的静态审核记录与需求对应表

**状态：`G0 V5 IMPLEMENTATION COMPLETE (CODE WRITTEN) / STATIC AUDIT RECORDED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001`（授权范围：CODING AND STATIC AUDIT）。基准 `13043b91336ada8fe05227062d36d876e9cd1355`，实现分支 `d1-r3-a-cpu-003-e1a-g0-v5-impl-20261027`。
冻结判据：`g0_criteria_v5.json`，SHA-256 `d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821`（字节未变）。
**没有运行**任何纯逻辑测试、进程级测试、真实 G0、BV、E1-A、GPU 或训练；**没有创建**授权文件或真实 `evidence/` 运行目录；**没有启动**受测进程；**没有导入或执行**被审计的 G0 模块（审计只用 `ast`、正则、JSON 与文件哈希）。**代码已写完不等于测试通过：所有测试均为 `NOT TESTED`。**

## 1. 变更范围

| 文件 | 性质 | 内容 |
|---|---|---|
| `gate_g0/g0_auth.py` | 修改 | 授权绑定改为 V5（`g0_criteria_v5.json`、`E1A_GATE_G0_PREREG_V5.md`）；冻结哈希表 `FROZEN_FILES`（V1–V5 共 10 个文件）与 `frozen_problems()`；`validate()` 拒绝绑定到 V1–V4 哈希的授权（CL-08）；仍不写任何授权文件，`template()` 仍然无效 |
| `gate_g0/g0_judge.py` | 重写（纯函数） | C01–C17；C03 / C07 / C16 冻结规则；M-2；整条记录保真与保真报告；证据模式验证（91 字段）；结案标记的构造 / 验证 / 分类；CL-01…CL-23 的规则求值（读取冻结判据中的机器可读规则）；严格区分 PASS / FAIL / UNEVALUABLE / BLOCKED |
| `gate_g0/g0_run.py` | 重写 | 有界回收（F-8）、运行期总预算（F-9）、证据根 / 消耗目录 / 运行目录（F-12 / F-13）、账本与写入器序号、放行写入记录（F-18）、P0–P7 证据保存与读回流水线、K0–K7 结案标记原子发布、V5 预检（只读，CL-01…CL-23 事实采集） |
| `tests/g0_v5_fixtures.py` | 新增（辅助模块） | 完整 V5 证据构造、67 个静态案例到证据的转换、授权夹具 |
| `tests/test_g0_interlock_and_judge.py` | 重写 | 联锁 + 判定 + 源码约束，调整到 V5（68 个测试） |
| `tests/test_g0_v5_cases.py` | 新增 | 67 个 V4 规则案例、F3 条件表、FID、C07 规则（35 个测试） |
| `tests/test_g0_v5_closure_cases.py` | 新增 | 38 个结案案例（先按事实求值，再物化成真实目录读回）、标记模式（24 个测试） |
| `tests/test_g0_v5_pipeline.py` | 新增 | 19 个结案流水线案例 + 15 个 V4 流水线案例，带故障注入（29 个测试） |
| `tests/test_g0_v5_run_parts.py` | 新增 | 放行写入守卫、预算、目录、预检形态、`run()` 结构的 AST 检查（28 个测试） |
| `tools/audit_g0_v5_implementation.py` | 新增 | 静态审计 + 需求对应表（只读源码 / JSON / 哈希） |

**未修改：** V1–V5 冻结判据与文字、`bench/`、上游 Parcae、R3、CPU-001/002、其余既有测试（`test_e1a_*.py`）、E1-A 原预注册。`git diff 13043b9 -- bench` 为空。

## 2. 实现与 V5 的逐项对应表（`NOT TESTED`）

下表由 `tools/audit_g0_v5_implementation.py` 生成：每一行的实现位置与测试位置都必须能在源码中找到（找不到则工具退出码为 1）。64 行，0 行 NOT FOUND。

| V5 requirement | V5 source | implementation | tests (written, NOT RUN) | status |
|---|---|---|---|---|
| G0-C01 preflight_clean (V5: earlier runs closed by a valid marker; residue independent) | `checks.G0-C01` | `gate_g0/g0_judge.py:602`<br>`gate_g0/g0_run.py:318`<br>`gate_g0/g0_run.py:343` | `tests/test_g0_interlock_and_judge.py:418`<br>`tests/test_g0_v5_closure_cases.py:361` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C02 authorization_and_bindings (V5 hash; '(V2)' = historical wording error) | `checks.G0-C02` | `gate_g0/g0_judge.py:609`<br>`gate_g0/g0_auth.py:39`<br>`gate_g0/g0_auth.py:119` | `tests/test_g0_interlock_and_judge.py:63`<br>`tests/test_g0_interlock_and_judge.py:63` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C03 registration_sequence_and_integrity | `checks.G0-C03` | `gate_g0/g0_judge.py:473` | `tests/test_g0_v5_cases.py:48` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C04 identity_registered_before_release (M-2) | `checks.G0-C04` | `gate_g0/g0_judge.py:620` | `tests/test_g0_interlock_and_judge.py:365` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C05 no_action_before_release (M-2) | `checks.G0-C05` | `gate_g0/g0_judge.py:631` | `tests/test_g0_interlock_and_judge.py:330` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C06 gate_descriptor_hygiene | `checks.G0-C06` | `gate_g0/g0_judge.py:650` | `tests/test_g0_interlock_and_judge.py:342` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C07 release evidence | `checks.G0-C07` | `gate_g0/g0_judge.py:546` | `tests/test_g0_v5_cases.py:294` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C08 exit_observed_unreaped | `checks.G0-C08` | `gate_g0/g0_judge.py:668` | `tests/test_g0_interlock_and_judge.py:308` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C09 reap_by_specific_pid (polls return 0) | `checks.G0-C09` | `gate_g0/g0_judge.py:682` | `tests/test_g0_interlock_and_judge.py:318` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C10 exit_status_zero | `checks.G0-C10` | `gate_g0/g0_judge.py:703` | `tests/test_g0_interlock_and_judge.py:323` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C11 process_budget (M-2) | `checks.G0-C11` | `gate_g0/g0_judge.py:707` | `tests/test_g0_interlock_and_judge.py:352` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C12 zero_signals | `checks.G0-C12` | `gate_g0/g0_judge.py:722` | `tests/test_g0_interlock_and_judge.py:277` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C13 cleanup_and_no_residue (M-2) | `checks.G0-C13` | `gate_g0/g0_judge.py:729` | `tests/test_g0_interlock_and_judge.py:370` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C14 observer_descriptor_baseline | `checks.G0-C14` | `gate_g0/g0_judge.py:754` | `tests/test_g0_interlock_and_judge.py:382` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C15 time_bounds (runtime budget) | `checks.G0-C15` | `gate_g0/g0_judge.py:759`<br>`gate_g0/g0_run.py:449` | `tests/test_g0_interlock_and_judge.py:410`<br>`tests/test_g0_v5_run_parts.py:114` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C16 evidence_complete (schema e1a-gate-g0-evidence-4) | `checks.G0-C16` | `gate_g0/g0_judge.py:765`<br>`gate_g0/g0_judge.py:233`<br>`gate_g0/g0_judge.py:197` | `tests/test_g0_interlock_and_judge.py:223`<br>`tests/test_g0_interlock_and_judge.py:215` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-C17 no_unexplained_error | `checks.G0-C17` | `gate_g0/g0_judge.py:773` | `tests/test_g0_interlock_and_judge.py:292` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-F1 (a)-(f) ledger violations | `C03-F1` | `gate_g0/g0_judge.py:357` | `tests/test_g0_v5_cases.py:197` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-F2 hole in the ledger (needs clean writer, no foreign lines) | `C03-F2` | `gate_g0/g0_judge.py:415`<br>`gate_g0/g0_judge.py:493` | `tests/test_g0_v5_cases.py:202` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-F3a fork proven, no valid INTENT | `C03-F3a` | `gate_g0/g0_judge.py:496` | `tests/test_g0_v5_cases.py:209` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-F3b release write ok, no valid REGISTERED/RELEASED | `C03-F3b` | `gate_g0/g0_judge.py:498` | `tests/test_g0_v5_cases.py:216` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-F3c gate pass proven despite append failure | `C03-F3c` | `gate_g0/g0_judge.py:500` | `tests/test_g0_v5_cases.py:223`<br>`tests/test_g0_v5_cases.py:231` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-F4 completed run with incomplete ledger | `C03-F4` | `gate_g0/g0_judge.py:505` | `tests/test_g0_v5_cases.py:243` | IMPLEMENTED (code written); tests NOT TESTED |
| C03-U0/U2/U3/U5/U1/U4 and their order | `C03-U*` | `gate_g0/g0_judge.py:524`<br>`gate_g0/g0_judge.py:538` | `tests/test_g0_v5_cases.py:253` | IMPLEMENTED (code written); tests NOT TESTED |
| C03 requirements table (writer_clean only where required) | `rules.requirements` | `gate_g0/g0_judge.py:492`<br>`gate_g0/g0_judge.py:317` | `tests/test_g0_v5_cases.py:178` | IMPLEMENTED (code written); tests NOT TESTED |
| C03 definitions: release_attempt / release_write_ok / gate_passed / gate_pass_proven | `rules.definitions` | `gate_g0/g0_judge.py:437` | `tests/test_g0_v5_cases.py:263` | IMPLEMENTED (code written); tests NOT TESTED |
| C03 disk_faithful on whole canonical records; fidelity report LOST/FOREIGN/ALTERED/PARSE/COUNT | `F-20 / M-1` | `gate_g0/g0_judge.py:273`<br>`gate_g0/g0_judge.py:69` | `tests/test_g0_v5_cases.py:128`<br>`tests/test_g0_v5_cases.py:100` | IMPLEMENTED (code written); tests NOT TESTED |
| M-2: C04/C05/C11/C13 UNEVALUABLE when the durable copy is unfaithful | `M-2` | `gate_g0/g0_judge.py:29`<br>`gate_g0/g0_judge.py:792` | `tests/test_g0_interlock_and_judge.py:441`<br>`tests/test_g0_v5_cases.py:111` | IMPLEMENTED (code written); tests NOT TESTED |
| FID-A..E (and FID-F) cases | `F-20` | `gate_g0/g0_judge.py:273` | `tests/test_g0_v5_cases.py:111`<br>`tests/test_g0_v5_cases.py:122` | IMPLEMENTED (code written); tests NOT TESTED |
| C07-F1/F2/F3 and U1..U7 | `checks.G0-C07` | `gate_g0/g0_judge.py:559`<br>`gate_g0/g0_judge.py:588` | `tests/test_g0_v5_cases.py:318`<br>`tests/test_g0_v5_cases.py:314` | IMPLEMENTED (code written); tests NOT TESTED |
| 67 V4 rule cases -> V5 judge | `g0_v4_cases.json` | `gate_g0/g0_judge.py:804` | `tests/test_g0_v5_cases.py:48` | IMPLEMENTED (code written); tests NOT TESTED |
| verdict rule: FAIL > BLOCKED > PASS; exit codes 0/1/3 | `verdict_rule` | `gate_g0/g0_judge.py:833`<br>`gate_g0/g0_judge.py:28` | `tests/test_g0_interlock_and_judge.py:299`<br>`tests/test_g0_interlock_and_judge.py:284` | IMPLEMENTED (code written); tests NOT TESTED |
| FAIL scope text | `verdict_policy` | `gate_g0/g0_judge.py:31`<br>`gate_g0/g0_run.py:789` | `tests/test_g0_interlock_and_judge.py:475` | IMPLEMENTED (code written); tests NOT TESTED |
| P0 construct: ledger + writer seq captured before the registry parse | `evidence_pipeline P0 / LEDGER` | `gate_g0/g0_run.py:610`<br>`gate_g0/g0_run.py:611` | `tests/test_g0_v5_run_parts.py:288` | IMPLEMENTED (code written); tests NOT TESTED |
| P1 strict serialisation (no default=str) | `evidence_pipeline P1` | `gate_g0/g0_judge.py:64`<br>`gate_g0/g0_run.py:762` | `tests/test_g0_v5_pipeline.py:385`<br>`tests/test_g0_interlock_and_judge.py:528` | IMPLEMENTED (code written); tests NOT TESTED |
| P2 exclusive write + fsync (+ directory fsync); never overwrite | `evidence_pipeline P2` | `gate_g0/g0_run.py:650`<br>`gate_g0/g0_run.py:642` | `tests/test_g0_v5_pipeline.py:399`<br>`tests/test_g0_v5_pipeline.py:410` | IMPLEMENTED (code written); tests NOT TESTED |
| P3 read back, verify bytes + SHA-256, strict parse | `evidence_pipeline P3` | `gate_g0/g0_run.py:671`<br>`gate_g0/g0_run.py:697` | `tests/test_g0_v5_pipeline.py:416`<br>`tests/test_g0_v5_pipeline.py:422` | IMPLEMENTED (code written); tests NOT TESTED |
| P4 validate types (once, on the read-back evidence) | `evidence_pipeline P4` | `gate_g0/g0_run.py:777` | `tests/test_g0_v5_pipeline.py:429` | IMPLEMENTED (code written); tests NOT TESTED |
| P5 judge ONLY the read-back evidence | `evidence_pipeline P5` | `gate_g0/g0_run.py:780` | `tests/test_g0_v5_pipeline.py:337`<br>`tests/test_g0_v5_pipeline.py:440` | IMPLEMENTED (code written); tests NOT TESTED |
| P6 save + verify the summary | `evidence_pipeline P6` | `gate_g0/g0_run.py:792` | `tests/test_g0_v5_pipeline.py:446`<br>`tests/test_g0_v5_pipeline.py:452`<br>`tests/test_g0_v5_pipeline.py:457` | IMPLEMENTED (code written); tests NOT TESTED |
| P7 publish the marker, return the recorded exit code; uncaught exceptions -> 3 | `evidence_pipeline P7` | `gate_g0/g0_run.py:725`<br>`gate_g0/g0_run.py:856` | `tests/test_g0_v5_pipeline.py:463`<br>`tests/test_g0_v5_pipeline.py:468` | IMPLEMENTED (code written); tests NOT TESTED |
| stderr markers of the pipeline | `evidence_pipeline` | `gate_g0/g0_run.py:764`<br>`gate_g0/g0_run.py:794`<br>`gate_g0/g0_run.py:782` | `tests/test_g0_v5_run_parts.py:332` | IMPLEMENTED (code written); tests NOT TESTED |
| closure marker g0_closed.json: schema, strict bytes, validation | `closure.marker_schema` | `gate_g0/g0_judge.py:840`<br>`gate_g0/g0_judge.py:874`<br>`gate_g0/g0_judge.py:888` | `tests/test_g0_v5_closure_cases.py:154` | IMPLEMENTED (code written); tests NOT TESTED |
| K1 build / K2 temp file O_EXCL+fsync / K3 verify | `closure.publication K1-K3` | `gate_g0/g0_run.py:732`<br>`gate_g0/g0_run.py:735` | `tests/test_g0_v5_pipeline.py:282` | IMPLEMENTED (code written); tests NOT TESTED |
| K4 os.link exclusive publication (EEXIST, no fallback) | `closure.publication K4` | `gate_g0/g0_run.py:741` | `tests/test_g0_v5_pipeline.py:289`<br>`tests/test_g0_v5_pipeline.py:295` | IMPLEMENTED (code written); tests NOT TESTED |
| K5 directory fsync / K6 verify published name / K7 exit | `closure.publication K5-K7` | `gate_g0/g0_run.py:744`<br>`gate_g0/g0_run.py:746` | `tests/test_g0_v5_pipeline.py:308`<br>`tests/test_g0_v5_pipeline.py:227` | IMPLEMENTED (code written); tests NOT TESTED |
| G0-CLOSE-UNPUBLISHED / G0-CLOSE-UNCONFIRMED and exit 3 | `closure.publication.failures` | `gate_g0/g0_run.py:727`<br>`gate_g0/g0_run.py:727` | `tests/test_g0_v5_pipeline.py:155` | IMPLEMENTED (code written); tests NOT TESTED |
| 19 closure pipeline cases | `g0_v5_cases.json pipeline_cases` | `gate_g0/g0_run.py:758` | `tests/test_g0_v5_pipeline.py:197`<br>`tests/test_g0_v5_pipeline.py:274` | IMPLEMENTED (code written); tests NOT TESTED |
| reporting rule (outcome = recorded verdict only when confirmed) | `closure.publication.reporting_rule` | `gate_g0/g0_run.py:755` | `tests/test_g0_v5_pipeline.py:241` | IMPLEMENTED (code written); tests NOT TESTED |
| temporary name never deleted | `closure.publication.no_delete` | `gate_g0/g0_run.py:36` | `tests/test_g0_interlock_and_judge.py:528`<br>`tests/test_g0_v5_pipeline.py:282` | IMPLEMENTED (code written); tests NOT TESTED |
| CL-01..CL-23 evaluated from the frozen rules (pure) | `closure.preflight.rules` | `gate_g0/g0_judge.py:947` | `tests/test_g0_v5_closure_cases.py:227`<br>`tests/test_g0_v5_closure_cases.py:249` | IMPLEMENTED (code written); tests NOT TESTED |
| closure facts collected read-only from run directories | `closure.preflight.facts` | `gate_g0/g0_run.py:282`<br>`gate_g0/g0_run.py:270`<br>`gate_g0/g0_judge.py:920` | `tests/test_g0_v5_closure_cases.py:313`<br>`tests/test_g0_v5_closure_cases.py:324` | IMPLEMENTED (code written); tests NOT TESTED |
| 38 closure cases A..K | `g0_v5_cases.json cases` | `gate_g0/g0_run.py:318` | `tests/test_g0_v5_closure_cases.py:302` | IMPLEMENTED (code written); tests NOT TESTED |
| summary existence never closes a run | `closure.principle` | `gate_g0/g0_run.py:300` | `tests/test_g0_v5_closure_cases.py:243` | IMPLEMENTED (code written); tests NOT TESTED |
| closure marker is not process-exit proof (live scan + MANUAL independent) | `CL-C / CL-20..22` | `gate_g0/g0_run.py:321`<br>`gate_g0/g0_run.py:35` | `tests/test_g0_v5_closure_cases.py:255` | IMPLEMENTED (code written); tests NOT TESTED |
| any recorded verdict may be closed, a manual disposition still blocks (CL-D) | `CL-D` | `gate_g0/g0_judge.py:947` | `tests/test_g0_v5_closure_cases.py:263` | IMPLEMENTED (code written); tests NOT TESTED |
| F-8 bounded reap (non-blocking polls) | `enforcement.reap_wait` | `gate_g0/g0_run.py:549` | `tests/test_g0_v5_run_parts.py:268`<br>`tests/test_g0_interlock_and_judge.py:501` | IMPLEMENTED (code written); tests NOT TESTED |
| F-9 total runtime budget | `enforcement.total_budget` | `gate_g0/g0_run.py:449`<br>`gate_g0/g0_run.py:520` | `tests/test_g0_v5_run_parts.py:278`<br>`tests/test_g0_v5_run_parts.py:123` | IMPLEMENTED (code written); tests NOT TESTED |
| F-12 files only into a run directory created by this process | `enforcement.summary_write` | `gate_g0/g0_run.py:425`<br>`gate_g0/g0_run.py:422` | `tests/test_g0_v5_run_parts.py:210` | IMPLEMENTED (code written); tests NOT TESTED |
| F-13 evidence root / consumption dir created-or-validated, run dir exclusive | `enforcement.directories` | `gate_g0/g0_run.py:391`<br>`gate_g0/g0_run.py:417` | `tests/test_g0_v5_run_parts.py:187`<br>`tests/test_g0_v5_run_parts.py:224` | IMPLEMENTED (code written); tests NOT TESTED |
| F-18 release writes recorded as entries (before / after / result) | `enforcement.release_evidence` | `gate_g0/g0_run.py:141`<br>`gate_g0/g0_run.py:147` | `tests/test_g0_v5_run_parts.py:33` | IMPLEMENTED (code written); tests NOT TESTED |
| single-use, V5-bound authorization; no authorization is ever written | `g0_auth` | `gate_g0/g0_auth.py:71`<br>`gate_g0/g0_auth.py:156` | `tests/test_g0_interlock_and_judge.py:153`<br>`tests/test_g0_interlock_and_judge.py:126` | IMPLEMENTED (code written); tests NOT TESTED |
| version isolation (V1..V4 frozen bytes unchanged; V1..V4 bindings void) | `CL-08` | `gate_g0/g0_auth.py:41` | `tests/test_g0_interlock_and_judge.py:140`<br>`tests/test_g0_interlock_and_judge.py:63` | IMPLEMENTED (code written); tests NOT TESTED |
| preflight never raises (BLOCKED, never FAIL) | `checks.G0-C01` | `gate_g0/g0_run.py:368` | `tests/test_g0_v5_run_parts.py:245` | IMPLEMENTED (code written); tests NOT TESTED |

## 3. 静态审计结果（没有运行任何测试）

| 检查 | 工具 | 结果 |
|---|---|---|
| 语法、未定义名、未使用导入（9 个 Python 文件） | `tools/audit_g0_v5_implementation.py` | 干净 |
| 证据模式 91 个字段的类型串都有验证器；C03 / C07 的 22 条规则编号、17 个检查、5 种保真条目类型、6 个 stderr 标记、结案标记字段、退出码表、快照名都出现在源码中 | 同上 | 0 发现 |
| 禁止调用：G0 三个模块无 `os.kill/fork/exec*/spawn*/wait*`（除守卫内部的下标调用与 `os.waitpid` 唯一一处，带 `WNOHANG`）、无 `os.rename/replace/unlink/remove/truncate`、无 `json default=` | 同上 + `tools/static_audit.py --dir gate_g0` | 0 违规 |
| 台架静态审计（默认剖面） | `tools/static_audit.py` | 0 违规 |
| V1–V5 共 10 个冻结文件、E1-A 原预注册哈希 | 同上 | 未变 |
| 授权文件 / `evidence/` 目录不存在 | 同上 | 不存在 |
| V5 规格一致性、结案案例 | `tools/check_g0_v5_consistency.py`、`tools/check_g0_v5_closure_cases.py`（读取 JSON） | 0 不一致 |
| 测试清单（只统计，不运行） | AST | 184 个测试方法，5 个文件，**全部 NOT TESTED** |

原始输出：`g0_preflight_review/v5_implementation_audit.txt`、`v5_static_audit_g0.txt`、`v5_static_audit_bench.txt`、`v5_implementation_trace.md / .json`。

## 4. 已接受的审核条件如何落实

| 条件 | 落实 |
|---|---|
| CL-A：不得增加会覆盖最终结案文件的 fallback | `publish_closure` 只通过 `os.link(tmp, final, follow_symlinks=False)` 创建最终名；`link` 失败（含不支持）⇒ `G0-CLOSE-UNPUBLISHED`、退出码 3，没有 rename / replace / 直接创建；源码测试禁止 `os.rename/replace/unlink/...`，`test_no_fallback_creates_the_final_name_when_link_is_unsupported`、`test_an_existing_final_marker_is_never_replaced` |
| CL-B：文件结案与进程运行结果分离；未确认的残留进程阻断下一次运行 | 预检按文件事实判定结案（CL-01…CL-20）；存活 `g0_run.py` 进程（CL-22）与 `MANUAL_DISPOSITION_REQUIRED.json`（CL-20 / CL-21）独立评估，标记有效也阻断；退出码 ≠ 记录的退出码或出现 `G0-CLOSE-*` 时进程级结果为 BLOCKED（`publish_closure` 返回 3；已保存的文件不改写） |
| CL-D：PASS、FAIL、BLOCKED 均允许封存，但不得掩盖人工处置 | `build_marker` 接受三种合法对；CL-20 / CL-21 使合法标记仍 BLOCKED（`test_any_recorded_verdict_closes_a_run_but_not_a_manual_disposition`） |
| CL-08：严格保持历史判据版本隔离 | `g0_auth.validate` 拒绝绑定到 V1–V4 哈希的授权；`judge` 的 C02 要求绑定为冻结的 V5 哈希；标记与摘要的 `criteria_id / sha256` 必须等于运行工具的值（CL-08 规则）；`frozen_problems()` 核对 10 个冻结文件 |
| C02：保留冻结规范；`(V2)` 是历史文字错误，实际绑定用 V5 哈希 | `g0_auth.py` 文档与 `g0_judge.c02` 注释记录此事；C02 判定同时要求 `g0_criteria_sha256` / `g0_prereg_sha256` 等于冻结 V5 值；冻结 JSON 文字未改 |

## 5. 实现中的解释与判断（需要审核者确认；没有修改 V5）

1. **消耗目录（可能的冻结文字冲突，标记为待裁定）：** `enforcement.directories` 写「运行目录与消耗目录排他创建」，而 `implementation_obligations.F-13` 写「证据根与消耗目录**创建或验证**，运行目录排他」。同一授权的消耗标记已是 `open(..., "x")` 排他；若消耗目录本身也要求「排他创建（已存在即失败）」，则第二次授权永远无法运行。实现采用 F-13：不存在则非递归创建（0755），存在则验证（真实目录、非符号链接、属当前有效 uid、组 / 其他不可写）。
2. **案例标签与冻结规则文字的差异（状态一致，规则编号不同）：** `CE-E1` 记录 `C07-U1`，但冻结 C07-U1 要求「没有放行尝试」，而该案例有尝试且缺账本，实现报告 `C07-U5`；`F3C-2`、`F3C-6` 的记录取最后一条匹配的 C07 规则（U7 / U6），实现按编号列出全部匹配规则（U5 在前）。测试对状态做精确断言，对规则编号用「记录的编号 ∈ `rules_matched`」，`CE-E1` 单独列别名。
3. **C07 的 REGISTERED / RELEASED 时间** 取账本中第一条带数值 `mono` 的同类记录，不要求记录有效（有效性由 C03 的 F1(d) / F3 判断）；否则 `CE-M1`、`F3C-3` 会因 `starttime=null` 被错判为 C07 UNEVALUABLE。
4. **P4 的「需要失败字段的检查为 UNEVALUABLE」** 实现为：对 C01、C02、C04–C06、C08–C15、C17，若模式中以该检查为使用者的字段缺失或类型错误，则该检查 UNEVALUABLE。C03、C07、C16 不用这条泛规则，而用各自的类型化取值（U0 / U5），因为它们的规则要把「子进程未通过门控」（`first_action_mono` 为空）当作有意义的状态。
5. **U0 的范围** 在冻结文字列出的四项（账本、写入器序号、持久副本、解析信息）之外，对 `exception / aborted / deadline_hits` 缺失时 `completed_run` 不可得（F4 不触发，落到 U4）；F3 规则要求独立见证可得。
6. **`git_head` 等绑定值** 必须是 40 或 64 位小写十六进制，`UNKNOWN`（无法读取 `.git`）使 C16 失败（fail-closed）。
7. **预检在创建任何目录之前执行**（只读）；证据根不存在 ⇒ 没有更早的运行。预检本身抛出异常 ⇒ 一个 `ok=false` 的预检结果（BLOCKED，不是 FAIL）。证据里 `preflight` 多一个键 `closure`（事实与原因明细），冻结模式允许额外键。
8. **预算** 从 `run()` 开始计时（与 `timing.duration` 同一基准）；预检与目录创建的时间不计入。清理阶段的 `grace` 取 `min(3.0, 剩余/6)`，因为台架的 `final_cleanup` 内部循环不可改动（`bench/` 不变）。
9. **冻结标记之外新增的 stderr 标记** 仅用于冻结文字留白的情形，且退出码均为 3：`G0-DIR-ERROR`（目录创建 / 验证失败）、`G0-RUN-ERROR`（`run()` 自身抛出）、`G0-PIPELINE-ERROR`（流水线外泄异常，对应 PIPE-15）、`G0-BLOCKED-NOTE-UNSAVED`（P2 的可选说明文件也写不出）。
10. **`entry` 事实** 在目录不属于有效 uid 时也记为 `not_a_directory`（冻结事实含义：「真实目录、属有效 uid」）。
11. 被拒绝的方案：`renameat2(RENAME_NOREPLACE)`（需要 `ctypes`）、直接创建最终名（V5 禁止）、`os.replace`（会覆盖）。

## 6. 标记为 BLOCKED（待裁定或待真实环境）的条款

没有发现「根本无法按冻结文字实现」的条款。以下条目在不修改 V5 的前提下**无法在本阶段定论**，故标记 BLOCKED：

| 编号 | 内容 | 需要 |
|---|---|---|
| B-1 | §5 第 1 点：消耗目录「排他创建」与「创建或验证」两句冻结文字的冲突 | 审核者 / 负责人裁定；若裁定为「排他」，需要新版本号处理 |
| B-2 | §5 第 2 点：`CE-E1` 记录标签与冻结 C07-U1 文字不符 | 审核者确认以冻结文字为准（实现已如此） |
| B-3 | `os.link`、`fsync`、`O_NOFOLLOW`、`posix_fadvise`、`pidfd` 在目标文件系统与内核上的实际行为（L-4 / L-7） | 获得授权后的纯逻辑 / 进程级测试，以及对证据根所在文件系统的确认 |
| B-4 | 所有 184 个测试方法的实际通过情况 | CPU 纯逻辑测试授权 |

## 7. 未运行的测试与预期的分诊

本阶段**没有运行任何测试**，也没有用任何临时脚本执行判定函数。测试由手工逐项对照实现推演编写；推演中发现并已修正的问题包括：C07 时间来源（§5 第 3 点）、闭环案例物化时 `tmp` / 同长度不匹配的构造、`Budget` 正则。下一阶段运行时最可能出现的失败来源：案例夹具的默认值（`g0_v5_fixtures.parse_rec`）、`unittest.mock` 补丁 `os.fsync` / `os.link` 的全局影响、临时目录权限、`Python` 版本检查（`preflight` 的 3.13.16 要求不在测试路径中）。

## 8. 下一步

将本分支交给 ChatGPT / Grok 审核；通过后**仅申请 CPU 纯逻辑测试授权**（不自动启动真实 G0）。测试范围：上列 5 个测试文件（184 个测试方法）与既有 `tools/static_audit.py`；不含进程级测试，不含真实 G0。
