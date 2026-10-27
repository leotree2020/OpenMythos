# G0_V4_SPEC_REVIEW — V4 判据制定的审查记录、验收清单、案例迁移与决策可追溯性

**状态：`G0 V4 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V4-SPEC-001`（状态：待项目负责人授权，仅制定 V4 规范）。审核基准 `279eaaed1a62203abd9e2d30f0b2ab9ed302538e`。
V4 冻结提交 `753b460`（只含 `g0_criteria_v4.json`、`.sha256`、`E1A_GATE_G0_PREREG_V4.md`），本文件在其**之后**提交。
**没有修改** V1/V2/V3、`g0_run.py` / `g0_judge.py` / `g0_auth.py`、`bench/`、既有测试、E1-A 原预注册、R3、CPU-001/002、Parcae；**没有运行**纯逻辑测试、真实 G0、BV、E1-A、GPU 或训练；没有创建执行授权文件。只运行了只读取判据 / 案例文件的静态一致性检查。
**本文件中所有案例结论都是对 V4 规则的手工推导（静态案例，设计审核），不是测试 PASS。**

## 0. 关于交叉审核意见的可追溯性（必须先说）

任务文本说明 ChatGPT 与 Grok 已完成独立交叉审核，且对 F-20、F-21、F-22、DD-1…DD-5、M-2 与条件化 F3 方案的主要意见一致。**两位审核者的原文不在本会话中**，我没有引用、转述或臆造其中任何细节。V4 的每项决定依据的是**任务文本明确写出的内容**；当任务文本只给出方向、需要我形式化时，我在决策登记中标明 `derived`，并列出受影响的规则与案例，使审核者只需确认一格。**所有 V4 决定都登记为「拟由负责人批准」（`PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL`）；审核者意见一致是静态设计审查的结论，不是真实进程验证。**

## 1. 验收清单（本轮 PASS 条件）

| # | 条件 | 证据 | 状态 |
|---|---|---|---|
| 1 | V4 JSON 与预注册文字一致 | `tools/check_g0_v4_consistency.py`：检查表 / 映射表 / 规则 / 需求表 / 定义 / 流水线 / 证据模式 91 字段 / 决策 / 义务逐项核对，0 不一致；已用故意破坏的临时副本验证它会报错（见 §8 第 2 点的局限） | 满足（自检） |
| 2 | V1 / V2 / V3 哈希全部不变 | 同一检查按冻结哈希核对 6 个文件；`git diff` 对冻结提交为空；远端 blob 核对 | 满足 |
| 3 | C01–C17 与 V3→V4 映射完整 | 17 行映射（10 IDENTICAL、7 MODIFIED）及规则迁移表（V3 的每个规则编号与 V4 的每个规则编号都被提到） | 满足 |
| 4 | FID-A…E、F3 条件案例、证据流水线失败案例都有明确结果 | §3、§4、§5 | 满足 |
| 5 | 现有 51 个 V3 静态案例有 V4 判定或迁移说明 | §6：51 个全部列出，3 个裁决改变（`CE-R6`、`CE-R7`、`CE-R8b`）均附理由；`tools/check_g0_v4_matrix.py` 核对 51 个 V3 案例齐全、`v3_final` 与 V3 矩阵一致、变化必有理由 | 满足（自检） |
| 6 | 规则不存在已知矛盾 | 需求表为 `writer_clean` 的唯一陈述，文字与表由检查工具互相核对，V3 矛盾片段（「F2, F3, F4 need writer_clean」）被禁用并核对不存在；FAIL 规则无一依赖持久副本；案例的 `writer_clean` / 外来行 / 保真由案例自己的记录**机械推出**并与所触发规则的需求逐一核对 | 满足（无**已知**矛盾；§7 列出残余风险） |
| 7 | 交叉审核意见与负责人最终决策可追溯 | 判据 `decision_register` 与 §2；`stated` / `derived` 已区分，原文缺席已声明 | 满足（含声明的局限） |
| 8 | Git 提交顺序：先 V4 冻结，再审核报告与检查点 | `753b460`（只含 3 个文件）早于本文件所在提交 | 满足 |

## 2. 决策登记（摘要；完整字段在判据的 `decision_register`）

| ID | 主题 | V4 规则 | 来源 | 需审核者确认的格 |
|---|---|---|---|---|
| `F-20/M-1` | durable-copy fidelity | whole canonical record comparison; C03-U2 with a fidelity report | stated：stated in the task text of G0-V4-SPEC-001 (full canonical JSON record comparison instead of the triples) | —（任务文本明确写出） |
| `M-2` | disk-dependent checks | when the durable copy is not faithful, C04 C05 C11 C13 are UNEVALUABLE; violations proven by the ledger or by independent witnesses are not cancelled by damage to other fields | stated：stated in the task text (choose M-2; ledger or independent proof stays FAIL) | —（任务文本明确写出） |
| `DD-1` | ledger design | retained; the ledger is the first-hand witness for what the writer did and is itself checked against the durable copy | derived：implied by the task text ('memory ledger ... cannot be cancelled'; whole-record comparison against the ledger) | 账本取完整记录（若改为只记计数：所有缺失类 FAIL 规则降为 BLOCKED） |
| `DD-2` | hole rule when the durable copy is damaged elsewhere | retained: F2 needs a clean writer and no foreign lines, and does not need a faithful durable copy | stated：stated in the task text ('a violation already reliably proven by the ledger ... is not cancelled automatically by damage of other disk fields') | —（任务文本明确写出） |
| `DD-3` | failed release write while the child passed the gate | UNEVALUABLE (C07-U6): the witnesses contradict each other. Exception kept as FAIL (C07-F3): a FIRST_ACTION earlier than the first recorded attempt, because no recorded write can explain it | derived：task text: 'cannot confirm the pass behaviour or the witnesses contradict each other: BLOCKED' | C07-U6（写入失败而子进程仍通过 ⇒ BLOCKED；若改回 FAIL：CE-R6 变回 FAIL） |
| `DD-4` | gate passed but no release attempt recorded | UNEVALUABLE (C07-U4, C03-U5) in both cases: the pass cannot be confirmed | derived：task text: same sentence as DD-3 | C07-U4 / C03-U5（无尝试记录而子进程通过 ⇒ BLOCKED；若改回 FAIL：CE-R8b 变回 FAIL） |
| `DD-5` | child passed the gate although the REGISTERED append failed | FAIL (C03-F3c) when the pass is proven by independent credible evidence (successful release write + the child's FIRST_ACTION, in order); an append failure or seq gap alone is BLOCKED | stated：stated in the task text (append failure or gap only: BLOCKED; independent credible proof of a gate pass without valid registration: FAIL) | —（任务文本明确写出） |
| `F-21` | evidence saving and judging order | pipeline P0-P7 | stated：stated in the task text (P0-P7 in this order, no default=str, exclusive write, BLOCKED exit 3 on any failure) | —（任务文本明确写出） |
| `F-22` | C03-F3 and writer_clean | one machine-readable requirements table | stated：stated in the task text (machine-readable condition table; no contradictory writer_clean text) | —（任务文本明确写出） |

## 3. V3→V4 的 7 项 MODIFIED

| 检查 | 关系 | V3 → V4 语义变化 |
|---|---|---|
| `G0-C03` registration_sequence_and_integrity | MODIFIED | whole-record fidelity (M-1); conditional F3 (F3a / F3b / F3c) with a machine-readable requirements table; writer_clean contradiction removed; U5 added; fidelity report; gate-pass proof defined |
| `G0-C04` identity_registered_before_release | MODIFIED | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C05` no_action_before_release | MODIFIED | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C07` release_only_after_registration | MODIFIED | contradicting or unconfirmable gate-pass evidence is BLOCKED (V3 FAIL F3 / F4 become U6 / U7); early action before the attempt is FAIL (new F3); U4 broadened |
| `G0-C11` process_budget | MODIFIED | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C13` cleanup_and_no_residue | MODIFIED | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C16` evidence_complete | MODIFIED | evidence is the read-back of the saved file (pipeline P3/P4); schema id e1a-gate-g0-evidence-4; field set unchanged |

## 4. F-20：完整记录保真与 FID-A…F（M-1 / M-2）

**规则：** `disk_faithful` = 解析报告干净 ∧ 记录条数相同 ∧ 逐条 `canon(持久[i]) == canon(账本[i])`（整条记录、每个字段、同一顺序）。不保真 ⇒ `C03-U2`，C03 附保真报告；依赖持久副本字段的 C04 / C05 / C11 / C13 ⇒ UNEVALUABLE（M-2）；账本或独立见证已证明的违规不被磁盘损坏取消（FID-F）。因此磁盘损坏既不会造成错误 PASS（C03 PASS 需要保真；依赖检查 UNEVALUABLE），也不会造成错误 FAIL（所有 FAIL 规则都不依赖持久副本）。

| 案例 | 输入 | 保真报告（应记录） | C03 | 被置为 UNEVALUABLE 的依赖持久副本的检查 | 最终 | 证据可信度 |
|---|---|---|---|---|---|---|
| `FID-A` | durable RUN_END.run_id differs from RUN_START.run_id; ledger correct; triples identical — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_y confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | [{"type": "ALTERED", "seq": 7, "kind": "RUN_END", "fields": ["run_id"]}] | UNEVALUABLE C03-U2 | G0-C13, G0-C04, G0-C05, G0-C11 | **BLOCKED** | INSUFFICIENT：ledger first-hand and compliant, durable copy altered: no PASS can rest on the file and no FAIL can be blamed on the protocol |
| `FID-B` | durable REGISTERED.pid corrupted (201); ledger pid 200 and the real child pid 200 correct — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=201 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | [{"type": "ALTERED", "seq": 4, "kind": "REGISTERED", "fields": ["pid"]}] | UNEVALUABLE C03-U2 | G0-C04, G0-C05, G0-C11, G0-C13 | **BLOCKED** | INSUFFICIENT：V3 literal gave a false identity FAIL from the altered file; V4 refuses to let the file decide |
| `FID-C` | durable INTENT.creator altered to n7; ledger creator O — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=n7 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | [{"type": "ALTERED", "seq": 2, "kind": "INTENT", "fields": ["creator"]}] | UNEVALUABLE C03-U2 | G0-C11, G0-C04, G0-C05, G0-C13 | **BLOCKED** | INSUFFICIENT：a ticket node appears only in the altered file |
| `FID-D` | durable RUN_END.cleanup_confirmed flipped false->true; ledger false — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=false]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | [{"type": "ALTERED", "seq": 7, "kind": "RUN_END", "fields": ["cleanup_confirmed"]}] | UNEVALUABLE C03-U2 | G0-C13, G0-C04, G0-C05, G0-C11 | **BLOCKED** | INSUFFICIENT：ledger says unconfirmed, file says confirmed; V3 literal gave a wrong PASS |
| `FID-E` | LEDGER record altered in memory (REGISTERED.pid 201); durable copy correct (200) — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=201 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | [{"type": "ALTERED", "seq": 4, "kind": "REGISTERED", "fields": ["pid"]}] | UNEVALUABLE C03-U2 | G0-C04, G0-C05, G0-C11, G0-C13 | **BLOCKED** | INSUFFICIENT：two first-hand witnesses disagree; the file is an independent witness of the ledger |
| `FID-F` | ledger proves a duplicate RELEASED; durable RUN_END additionally altered (run_id) — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RELEASED n1 · 7 DEAD n1 basis=proc · 8 RUN_END run=g0_x confirmed=true]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RELEASED n1 · 7 DEAD n1 basis=proc · 8 RUN_END run=g0_y confirmed=true]；writer_seq=8；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | [{"type": "ALTERED", "seq": 8, "kind": "RUN_END", "fields": ["run_id"]}] | FAIL C03-F1 | G0-C13, G0-C04, G0-C05, G0-C11 | **FAIL** | MEDIUM：the violation is proven by the ledger (first-hand, independent of the file); the damage to the file is reported and does not cancel the FAIL |

## 5. F-22：C03-F3 的条件规则与放行证据

**需求表（唯一来源）：**

| 规则 | 账本 | writer_clean | 无外来行 | 独立证据 | 完成运行 | 依赖持久副本 |
|---|---|---|---|---|---|---|
| C03-F1 | 是 | **否** | 否 | 否 | 否 | 否 |
| C03-F2 | 是 | **是** | 是 | 否 | 否 | 否 |
| C03-F3a（fork 已发生而无有效 INTENT） | 是 | **是** | 是 | 是 | 否 | 否 |
| C03-F3b（放行字节已写入而无有效 REGISTERED / RELEASED） | 是 | **是** | 是 | 是 | 否 | 否 |
| C03-F3c（经证明的门控通过而无有效登记） | 是 | **否（明确不要求）** | 是 | 是 | 否 | 否 |
| C03-F4 | 是 | 是 | 是 | 否 | 是 | 否 |

* 只有 append 失败或序号缺口：**BLOCKED**（`C03-U3`）。
* 独立可信证据证明子进程在没有有效登记的情况下通过门控：**FAIL**（`C03-F3c`；`gate_pass_proven` = 放行写入成功 ∧ 子进程自己的 FIRST_ACTION ∧ 恰一次尝试 ∧ FIRST_ACTION 不早于 `mono_after`）。
* 无法确认通过行为（无尝试记录、写入失败、多次尝试、时间矛盾）或见证互相矛盾：**BLOCKED**（`C03-U5`、`C07-U4/U6/U7`）。
* `release_attempt`、`release_write_ok`、`gate_passed` 为三个独立定义。

| 案例 | 输入 | C03 | C07 | 最终 | 证据可信度 |
|---|---|---|---|---|---|
| `F3A-1` | fork proven, INTENT never written, writer clean — 账本[1 RUN_START run=g0_x · 2 RUN_END run=g0_x confirmed=false]；writer_seq=2；early stop (exception)；fork=1；放行写入[无]；子进程[none] | FAIL C03-F3a | UNEVALUABLE C07-U1 | **FAIL** | MEDIUM：the guard recorded the fork's pid; the ledger is gapless and identical to the file: the intent was never attempted |
| `F3A-2` | fork proven, INTENT append failed (seq 2 consumed), writer NOT clean — 账本[1 RUN_START run=g0_x · 3 RUN_END run=g0_x confirmed=false]；writer_seq=3；early stop (exception)；fork=1；放行写入[无]；子进程[none] | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U1 | **BLOCKED** | INSUFFICIENT：single witness and an append failure: the missing INTENT may be explained by the failure |
| `F3B-1` | release write ok, RELEASED never written, child did not pass, writer clean — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RUN_END run=g0_x confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[none] | FAIL C03-F3b | UNEVALUABLE C07-U3 | **FAIL** | MEDIUM：the guard proves the byte was written; the clean ledger proves RELEASED was never attempted; only one witness for the write |
| `F3B-2` | release write ok, RELEASED append failed (seq 5 consumed), child did not pass, writer NOT clean — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 6 RUN_END run=g0_x confirmed=false]；writer_seq=6；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[none] | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U3 | **BLOCKED** | INSUFFICIENT：append failure plus a single witness (the code cannot write the byte after a failed RELEASED append): not confirmable |
| `F3C-2` | gate passed and a write ok, but FIRST_ACTION lies inside the write (1.78 in [1.75, 1.80)); REGISTERED absent; writer NOT clean — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 5 RUN_END run=g0_x confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.80 returned=1]；子进程[FIRST_ACTION@1.78] | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U7 | **BLOCKED** | INSUFFICIENT：the times contradict, so the pass is not proven (gate_pass_proven false); F3c does not apply |
| `F3C-3` | gate pass proven, REGISTERED present but invalid (starttime null) — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=null · 5 RELEASED n1 · 6 RUN_END run=g0_x confirmed=false]；writer_seq=6；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | FAIL C03-F1 | PASS  | **FAIL** | HIGH：the invalid field is visible in the ledger (F1(d)); the proven gate pass also fires F3c: no VALID registration existed |
| `F3C-4` | gate pass proven, REGISTERED absent from the ledger, but the durable copy has a REGISTERED line the writer never appended — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 RELEASED n1 · 5 RUN_END run=g0_x confirmed=false]；**持久副本**[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 RELEASED n1 · 5 RUN_END run=g0_x confirmed=false · 6 REGISTERED n1 pid=200 st=5000]；writer_seq=5；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U5 | **BLOCKED** | INSUFFICIENT：witness conflict: the file contradicts the ledger's absence; F3c requires no foreign lines |
| `F3-GAP` | append failure / seq gap ONLY: no independent evidence of any action beyond the fork — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 5 RUN_END run=g0_x confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[无]；子进程[none] | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U1 | **BLOCKED** | INSUFFICIENT：owner policy: an append failure or a gap alone is BLOCKED |
| `F3C-6` | witnesses contradict: the only release write failed (EPIPE), the child nevertheless passed, REGISTERED absent, writer NOT clean — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 5 RUN_END run=g0_x confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[error EPIPE b=1.75 a=1.7501 errno=32]；子进程[FIRST_ACTION@1.8] | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U6 | **BLOCKED** | INSUFFICIENT：the pass is unconfirmed (no successful write): owner policy BLOCKED |
| `CE-R4c` | child produced FIRST_ACTION although the REGISTERED append failed (seq 4 consumed) — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 5 RUN_END confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | FAIL C03-F3c | UNEVALUABLE C07-U5 | **FAIL** | MEDIUM：contradiction between first-hand facts (append failed, yet the gate was released and passed); a G0 bench/protocol failure, with a possible instrumentation defect noted |
| `CE-R8a` | child passed the gate; no release attempt recorded; RELEASED is in the ledger — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RUN_END confirmed=false]；writer_seq=6；early stop (exception)；fork=1；放行写入[无]；子进程[FIRST_ACTION@1.8] | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U4 | **BLOCKED** | INSUFFICIENT：instrumentation and child disagree; reported as an inconsistency, not as a protocol verdict |
| `CE-R8b` | child passed the gate; no release attempt recorded; RELEASED absent — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RUN_END confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[无]；子进程[FIRST_ACTION@1.8] | UNEVALUABLE C03-U5 | UNEVALUABLE C07-U4 | **BLOCKED** | HIGH：a child cannot pass the gate without a release path; ledger gapless and identical to the file |
| `CE-R6` | child produced FIRST_ACTION although the only release write failed (EPIPE) — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RUN_END confirmed=false]；writer_seq=6；early stop (exception)；fork=1；放行写入[error EPIPE b=1.75 a=1.7501 errno=32]；子进程[FIRST_ACTION@1.8] | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U6 | **BLOCKED** | MEDIUM：failed-write record and FIRST_ACTION are both first-hand and contradict each other: the gate was passed without a successful release (or a second writer exists) |
| `CE-R7` | FIRST_ACTION earlier than the completion of the release write — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis · 7 RUN_END confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.80 returned=1]；子进程[FIRST_ACTION@1.78] | PASS  | UNEVALUABLE C07-U7 | **BLOCKED** | HIGH：one monotonic clock; the child acted before the write had returned |
| `CE-R7b` | FIRST_ACTION BEFORE the release was attempted (1.70 < mono_before 1.75), attempt recorded — 账本[1 RUN_START run=g0_x · 2 INTENT n1 creator=O · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 DEAD n1 basis=proc · 7 RUN_END run=g0_x confirmed=true]；writer_seq=7；completed；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.70] | PASS  | FAIL C07-F3 | **FAIL** | HIGH：the child acted before any release attempt began; no recorded write can explain it (new C07-F3) |
| `CE-P4` | release written and child acted, RELEASED record never written — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RUN_END confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | FAIL C03-F3b | UNEVALUABLE C07-U5 | **FAIL** | HIGH：release write and FIRST_ACTION are first-hand; ledger gapless and identical to the durable copy |
| `CE-R4b` | child produced FIRST_ACTION; RELEASED never written; registry complete and gapless otherwise — 账本[1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RUN_END confirmed=false]；writer_seq=5；early stop (exception)；fork=1；放行写入[ok b=1.75 a=1.76 returned=1]；子进程[FIRST_ACTION@1.8] | FAIL C03-F3b | UNEVALUABLE C07-U5 | **FAIL** | HIGH：the child's FIRST_ACTION and the successful release write are first-hand; ledger gapless and identical to the file |

## 6. F-21：证据流水线失败案例（15 个）

| 案例 | 阶段 | 失败情形 | 裁决 / 退出码 | stderr 标记 | 保留的证据 | 覆盖了他人文件？ | 备注 |
|---|---|---|---|---|---|---|---|
| `PIPE-1` | P0..P7 | none | PASS / 0 | — | evidence + summary, both verified | 否 |  |
| `PIPE-2` | P1 | a non-JSON value (a set) in the evidence | BLOCKED / 3 | G0-EVIDENCE-UNSAVED | nothing on disk; registry and run directory remain | 否 | V3-era code would have used default=str and stored a string |
| `PIPE-3` | P1 | NaN in the evidence | BLOCKED / 3 | G0-EVIDENCE-UNSAVED | nothing on disk | 否 |  |
| `PIPE-4` | P2 | g0_evidence.json already exists (another run or an earlier attempt) | BLOCKED / 3 | G0-EVIDENCE-UNSAVED | the existing file untouched | 否 |  |
| `PIPE-5` | P2 | ENOSPC / EIO / EROFS while writing; short write that cannot be completed | BLOCKED / 3 | G0-EVIDENCE-UNSAVED | a partial g0_evidence.json created by this process (not deleted); optional g0_blocked note | 否 |  |
| `PIPE-6` | P2 | fsync of the file or of the directory fails | BLOCKED / 3 | G0-EVIDENCE-UNSAVED | the written file (durability not guaranteed) | 否 |  |
| `PIPE-7` | P3 | the bytes read back differ from the bytes written (truncation, bit flip, concurrent writer) | BLOCKED / 3 | G0-EVIDENCE-UNVERIFIED | the saved file as read, not repaired; both hashes on stderr | 否 |  |
| `PIPE-8` | P3 | the file is not a regular file or does not parse as strict JSON | BLOCKED / 3 | G0-EVIDENCE-UNVERIFIED | the saved file | 否 |  |
| `PIPE-9` | P4 | reg_writer_seq is the string '7' in the read-back evidence | BLOCKED / 3 | — | evidence + summary (C16 BLOCKED, C03-U0) | 否 | the pipeline continues: the type error is a C16 finding, not a pipeline failure |
| `PIPE-10` | P5 | the judge raises an exception | BLOCKED / 3 | G0-JUDGE-ERROR | the verified evidence file; no summary | 否 |  |
| `PIPE-11` | P6 | verdict FAIL computed, the summary cannot be written | BLOCKED / 3 | G0-SUMMARY-UNSAVED | the verified evidence file; stderr carries verdict=FAIL and evidence_sha256 | 否 | exit code 1 is NOT returned: a FAIL is recorded only when its summary was saved and verified |
| `PIPE-12` | P6 | verdict PASS computed, the summary cannot be written | BLOCKED / 3 | G0-SUMMARY-UNSAVED | the verified evidence file | 否 | no PASS is claimed or returned as exit code 0 |
| `PIPE-13` | P6 | the summary reads back with a different hash | BLOCKED / 3 | G0-SUMMARY-UNSAVED | the evidence file and the unverified summary | 否 |  |
| `PIPE-14` | P7 | FAIL verdict saved and verified | FAIL / 1 | — | evidence + summary with fail_scope | 否 |  |
| `PIPE-15` | P7 | an uncaught exception escapes main | BLOCKED / 3 | G0-JUDGE-ERROR | whatever was saved | 否 | main maps any uncaught exception to 3, never to Python's default exit code 1 (the FAIL code) |

## 7. 全部 67 个静态案例中的 V3 迁移（51 个）

共 67 个案例 = 51 个 V3 案例（迁移）+ 16 个新案例；FAIL 29 · BLOCKED 37 · PASS 1。51 个 V3 案例中 3 个裁决改变（`CE-R6`、`CE-R7`、`CE-R8b`），其余裁决不变（其中规则编号变化见规则迁移表）。

| 案例 | V3 → V4 裁决 | 变化 | C03 规则 | C07 规则 | 迁移说明 |
|---|---|---|---|---|---|
| `CE-D1` | FAIL → FAIL | 否 | FAIL C03-F1(a) | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-D2` | FAIL → FAIL | 否 | FAIL C03-F1(a) | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-D3` | FAIL → FAIL | 否 | FAIL C03-F1(a) | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-D4` | FAIL → FAIL | 否 | FAIL C03-F1(a) | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-D5` | FAIL → FAIL | 否 | FAIL C03-F1(a) | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-M1` | FAIL → FAIL | 否 | FAIL C03-F1(d) | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-M2` | FAIL → FAIL | 否 | FAIL C03-F1(d) | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-M3` | FAIL → FAIL | 否 | FAIL C03-F1(d) | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-F1` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-F2` | FAIL → FAIL | 否 | FAIL C03-F2 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-F3` | FAIL → FAIL | 否 | FAIL C03-F2 | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-G1` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-G2` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | PASS  | M-2: C13 reads the durable copy (DEAD / RUN_END) and is UNEVALUABLE when it is unfaithful; the final verdict is unchanged (BLOCKED) |
| `CE-G3` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-H1` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-H2` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-H3` | FAIL → FAIL | 否 | FAIL C03-F2 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-T1` | FAIL → FAIL | 否 | FAIL C03-F1(f) | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-P1` | FAIL → FAIL | 否 | FAIL C03-F1(b) | FAIL C07-F1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-P2` | FAIL → FAIL | 否 | FAIL C03-F1(a) | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-P3` | FAIL → FAIL | 否 | FAIL C03-F1(b) | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-P4` | FAIL → FAIL | 否 | FAIL C03-F3b | UNEVALUABLE C07-U5 | V3 C03-F3 is split; the clean-writer release-without-record branch is C03-F3b (C03-F3c also applies); verdict unchanged |
| `CE-P5` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R1` | PASS → PASS | 否 | PASS  | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R2` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U2 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R2b` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U2 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R3` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R4a` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R4b` | FAIL → FAIL | 否 | FAIL C03-F3b | UNEVALUABLE C07-U5 | as CE-P4 |
| `CE-R4c` | FAIL → FAIL | 否 | FAIL C03-F3c | UNEVALUABLE C07-U5 | DD-5: the proven gate pass is a FAIL even though the REGISTERED append failed (F3c ignores writer_clean); verdict unchanged, the rule text is now unambiguous |
| `CE-R5a` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R5b` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R5c` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R5d` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R5e` | FAIL → FAIL | 否 | FAIL C03-F1(a) | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R6` | FAIL → BLOCKED | **是** | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U6 | DD-3: a failed write recorded by the guard and a FIRST_ACTION from the child contradict each other; V3 FAIL becomes BLOCKED |
| `CE-R7` | FAIL → BLOCKED | **是** | PASS  | UNEVALUABLE C07-U7 | FIRST_ACTION lies between mono_before and mono_after: the times contradict (the child cannot have received SPEC before the write returned); V3 FAIL becomes BLOCKED. A FIRST_ACTION BEFORE mono_before is the new FAIL (CE-R7b) |
| `CE-R8a` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U1 | UNEVALUABLE C07-U4 | C07-U4 now covers every gate pass without a recorded attempt; unchanged for this case |
| `CE-R8b` | FAIL → BLOCKED | **是** | UNEVALUABLE C03-U5 | UNEVALUABLE C07-U4 | DD-4: a gate pass without any recorded attempt cannot be confirmed (the instrumentation may have missed the write); V3 FAIL becomes BLOCKED |
| `CE-R9` | FAIL → FAIL | 否 | PASS  | FAIL C07-F1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-R10` | FAIL → FAIL | 否 | PASS  | FAIL C07-F2 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-C1` | FAIL → FAIL | 否 | FAIL C03-F4 | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-C2` | BLOCKED → BLOCKED | 否 | PASS  | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-F4` | FAIL → FAIL | 否 | FAIL C03-F2 | UNEVALUABLE C07-U3 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-F5` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U3 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-F6` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U2 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-E1` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U0 | UNEVALUABLE C07-U1 | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-E2` | BLOCKED → BLOCKED | 否 | PASS  | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-E3` | BLOCKED → BLOCKED | 否 | UNEVALUABLE C03-U0 | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-E4` | BLOCKED → BLOCKED | 否 | PASS  | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |
| `CE-E5` | FAIL → FAIL | 否 | FAIL C03-F1(d) | PASS  | 规则编号与判定不变（或仅规则重命名，见规则迁移表） |

## 8. 残余风险与未解决问题

1. **`derived` 的决定需要审核者确认：** DD-1（账本取全记录）、DD-3、DD-4。若审核者与我的推导不同，只需改对应的一格（上表最后一列），并通过 V5 修订——V4 一经冻结不再修改。
2. **案例由手工推导；** 检查工具核对规则编号、状态 / 类别一致、聚合算术、以及用案例自己的记录推出的 `writer_clean` / 外来行 / 保真与所触发规则的需求是否相容。它**不**检验任何 G0 代码，也不能证明推导的前提（如「代码总是先写 RELEASED 再写放行字节」）是真实的。
3. **V4 描述的是目标行为：** 当前 `g0_run.py` 只记录写入前时间戳、无账本 / 证据模式 / 目录所有权 / 有界回收 / 运行期预算 / 流水线，`g0_judge.py` / `g0_auth.py` 仍绑定 V1 文件。实现前不得授权任何 G0 执行。
4. **完整记录保真的误报风险：** 若合法写入的记录含有 JSON 往返会改变的值，会产生假的 BLOCKED。P1 的严格序列化禁止 `default=`，账本与持久副本都是 JSON 类型，浮点用最短往返表示；未发现已知反例，但这是首次受控运行应当验证的一点（干净运行中账本与持久副本必须逐条相等）。
5. **C05 在持久副本不保真时整项 UNEVALUABLE**（沿用 L-1），它的『子进程在放行前行动』子条件因此不再单独判定；该事实仍由不依赖持久副本的 C07-F3（FIRST_ACTION 早于首次尝试）捕获。
6. **L-4：** `fsync` 成功与字节级读回相等不能证明存储介质已持久化；失败即 BLOCKED，成功只是用户态进程所能得到的最好证据。
7. 沿用：F-14（L-1）、程序性义务不被判定函数验证（L-3，C02 / C05 / C06 / C15）、F-1（台架把僵尸当已死）。
8. 46 个既有纯逻辑测试仍未运行，且将随实现改变；本阶段没有运行任何测试。

## 9. 下一阶段（须另行授权）

将 V4 冻结文件交给 ChatGPT / Grok 审核；审核通过后再申请 **G0 工具实现授权**。实现范围（沿用 V3 报告 §7 并更新）：`gate_g0/g0_run.py`（守卫前后记录、账本与写入器序号、`evidence_schema`、目录所有权、有界回收、运行期预算、P0–P7 流水线、摘要字段）、`gate_g0/g0_judge.py`（C03 / C07 / C16 与 M-2、保真报告、需求表）、`gate_g0/g0_auth.py`（指向 V4）、更新 `tests/test_g0_interlock_and_judge.py`、新增表驱动测试（67 个案例转成结构化夹具）与流水线 / 守卫单元测试、`tools/static_audit.py` 与 `audit_g0_pure_tests.py` 的扩展。全部为纯逻辑测试；运行任何测试都需单独授权。
