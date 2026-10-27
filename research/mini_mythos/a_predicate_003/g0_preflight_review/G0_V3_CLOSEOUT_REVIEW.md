# G0_V3_CLOSEOUT_REVIEW — F-20 / F-21 / F-22 独立审查与 V4 必要性结论

**状态：`G0 V3 FREEZE PASS / SEMANTIC CLOSEOUT OPEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED / GROK REVIEW PENDING`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V3-REVIEW-CLOSEOUT-001`。审核基准 `b4ca97daa303269ebe7b268f4bb00c6601723a6d`。
「G0 V3 FREEZE PASS」是 ChatGPT 对 V3 冻结提交（`7c4b99c`，只含 3 个文件）及范围合规的结论（经项目负责人转述）；本文件**不**修改它。
**没有修改** V1/V2/V3、`g0_run.py` / `g0_judge.py` / `g0_auth.py`、`bench/`、既有测试；**没有创建 V4**；**没有运行**任何测试、真实 G0、BV、E1-A，也没有启动任何受测进程；没有创建授权文件。
**以下所有追踪都是通读 V3 文本与源码得出的静态推导（设计审核），不是测试结果。** 行号指审核基准 `b4ca97d` 中的文件。

## 0. 结论摘要

| 问题 | 结论 | 分类 |
|---|---|---|
| **F-20** 持久副本保真不足 | **成立。** `disk_faithful` 只比较 `(seq, kind, node_id)`（`g0_criteria_v3.json:821`），而 C04 / C05 / C11 / C13 读的恰恰是持久副本 `reg` 的其他字段（`g0_judge.py:31,80,98,176,199,207`）。案例 A：V3 字面**错误 PASS**；案例 B：V3 字面**错误 FAIL**（C04）。V3 的限度 L-2 把这种情形说成「保守的 BLOCKED」，**不对**：字段被**改动**（不是丢失）时会得到错误的 PASS 或 FAIL。 | **需要 V4** |
| **F-21** 判定前是否读回 | **不是同一个操作。** `json.loads(json.dumps(evidence))` 是内存往返，不接触文件；V3 同时写了「在从 `g0_evidence.json` 读回的证据上判定」和「先判定再写文件」（预注册 §4 步骤 7）。三处文字不能同时满足。 | **需要 V4** |
| **F-22** C03-F3 规则冲突 | **成立。** F3 的 `when`（`:847`）说「追加失败时仍适用」，`precedence`（`:879`）说「F2、F3、F4 需要 writer_clean」。同一冻结文本对 DD-5 反例给出 FAIL 和 BLOCKED 两个答案。 | **需要 V4** |
| V4 是否确实需要 | **是。** 三项都是冻结文本本身的缺陷或自相矛盾，不能靠实现者解释或审查记录补救（V1/V2/V3 不得被重新解释）。 | 见 §6 一次性最小差异清单 |
| DD-1…DD-5 | 保持 V3 的设计基线，**待 Grok 独立审核**；ChatGPT 的有条件结论文本**不在本会话收到的指令中**，本文不转述、不臆造。 | §5 |

---

## 1. F-20：磁盘证据字段保真

### 1.1 源码依据（逐行）

| 位置 | 内容 | 含义 |
|---|---|---|
| `g0_criteria_v3.json:821` | `disk_faithful` = 解析报告干净 **且** 持久副本与账本的 **`(seq, kind, node_id)` 三元组**逐项相等 | 记录里其余字段（`pid`、`starttime`、`run_id`、`cleanup_confirmed`、`creator`、`mono`、`basis`…）完全不比较 |
| `:884` | `fidelity_scope`：「记录的其他字段被改动不会被发现（已知限度）」 | V3 自己承认；但没有评估它对 C04/C13 等检查的后果 |
| `:1191`（L-2） | C04 C05 C11 C13 仍读持久副本 `reg`；「损坏时它们可能 UNEVALUABLE……保守（BLOCKED）」 | **说法不对**：缺失 ⇒ UNEVALUABLE，但**改动** ⇒ 可以得到错误的 FAIL 或 PASS |
| `g0_judge.py:30-35` `_node()` | `reg = ev["reg"]`（持久副本）；按 `node_id` 取各类记录 | 所有读 `_node()` 的检查都读持久副本 |
| `g0_judge.py:80-83` C04 | `reg_rec = k["REGISTERED"][0]`；`reg_rec["pid"] == held["pid"] == fork_pids[0]` 且 `starttime` 相等 | 读持久副本的 `pid` / `starttime` |
| `g0_judge.py:98` C05 | `first_action_mono >= k["RELEASED"][0]["mono"]` | 读持久副本的 RELEASED.mono |
| `g0_judge.py:176-178` C11 | `intents = [r for r in reg if r["kind"] == "INTENT"]`；`creator != "O"` 即票据 | 读持久副本的 `creator` |
| `g0_judge.py:199,206-207` C13 | `k["DEAD"][0].get("basis")`；`end[0].get("cleanup_confirmed") is True` | 读持久副本的 `basis`、`cleanup_confirmed` |
| `g0_criteria_v3.json`（`evidence_schema` 中 `reg`） | `list[object{seq:int, kind:string, ...}]` | C16 只验证容器与 `seq` / `kind` 的类型 |
| `registry.py:115-118` | `RUN_END_FOR_DIFFERENT_RUN`、`RUN_END_ILLEGAL` 属于 `lifecycle_issues`，**只在 `integrity_issues(reg)` 里**被发现 | V3 的 C03 不再调用它（F1(d) 只看账本）；现实现的 `g0_judge.py:72` 仍对持久副本调用它，所以现实现对案例 A 判 FAIL |

### 1.2 追踪：案例 A、B（用户要求）与三个补充案例

状态记号：P = PASS，F = FAIL（证据确认），U = UNEVALUABLE。裁决按 V3 裁决规则聚合（FAIL 类检查 C03/C04/C05/C06/C07/C10/C11/C12；BLOCKED 类其余）。

| 案例 | 输入 | V3 字面（含 C04/C05/C11/C13 读持久副本） | 现实现（ab66d18 的 judge） | 建议修复后（V4 提案） | 应有裁决 | 证据可信度 |
|---|---|---|---|---|---|---|
| `FID-A` | durable RUN_END.run_id differs from RUN_START.run_id; ledger correct; (seq, kind, node_id) triples identical — completed clean run: ledger = RUN_START, INTENT n1, FORKED(pid 200), REGISTERED(pid 200, st 5000), RELEASED, DEAD(basis), RUN_END(run_id g0_x, cleanup_confirmed true); release write ok; FIRST_ACTION 1.8; all other checks PASS; durable copy: RUN_END.run_id='g0_y' (everything else identical) | C03=P C04=P C13=P C16=P → **PASS**：C03: F1(d) reads the LEDGER (run_id g0_x == g0_x) -> no FAIL; U2 needs disk_faithful false, but disk_faithful compares triples only (g0_criteria_v3.json:821) and the triples are identical -> faithful; pass_when holds -> PASS. C04 reads REGISTERED (untouched) -> PASS. C13 reads 'reg' RUN_END and tests only cleanup_confirmed is True (g0_judge.py:207) -> PASS. C16 types the container only -> PASS | C03=F C04=P C13=P C16=P → **FAIL**：g0_judge.py:72 R.integrity_issues(reg) on the durable copy -> lifecycle_issues RUN_END_FOR_DIFFERENT_RUN (registry.py:115-116) -> C03 FAIL: damage to the file is blamed on the protocol | C03=U C04=U C13=U C16=P → **BLOCKED**：whole-record fidelity: the durable RUN_END differs from the ledger record -> disk_faithful false -> C03-U2; C04/C13 read the durable copy -> UNEVALUABLE | **BLOCKED** | INSUFFICIENT：the ledger is first-hand and shows a compliant run, but the durable copy was altered; a PASS cannot rest on an altered file and a FAIL cannot be blamed on the protocol |
| `FID-B` | durable REGISTERED.pid corrupted (201); ledger pid 200 and the real child pid 200 are correct — completed clean run: ledger = RUN_START, INTENT n1, FORKED(pid 200), REGISTERED(pid 200, st 5000), RELEASED, DEAD(basis), RUN_END(run_id g0_x, cleanup_confirmed true); release write ok; FIRST_ACTION 1.8; all other checks PASS; durable copy: REGISTERED.pid=201 | C03=P C04=F C13=P C16=P → **FAIL**：C03: ledger fine, triples identical -> PASS. C04: _node() takes REGISTERED from ev['reg'] (g0_judge.py:31,80) -> reg_rec['pid']=201 != held pid 200 (g0_judge.py:83) -> FAIL (FAIL class). C13/C16 PASS. FAIL wins over everything | C03=P C04=F C13=P C16=P → **FAIL**：same: integrity_issues sees a valid int pid; C04 FAIL | C03=U C04=U C13=U C16=P → **BLOCKED**：whole-record fidelity -> disk_faithful false -> C03-U2; C04 reads the unfaithful durable copy -> UNEVALUABLE | **BLOCKED** | INSUFFICIENT：ledger and real pid agree (pid 200); the only contradicting witness is the altered file -> a false identity FAIL under V3 literal |
| `FID-C` | durable INTENT.creator altered to 'n7'; ledger creator 'O' — completed clean run: ledger = RUN_START, INTENT n1, FORKED(pid 200), REGISTERED(pid 200, st 5000), RELEASED, DEAD(basis), RUN_END(run_id g0_x, cleanup_confirmed true); release write ok; FIRST_ACTION 1.8; all other checks PASS; durable copy: INTENT.creator='n7' | C03=P C11=F C13=P C16=P → **FAIL**：C03 PASS (ledger, triples). C11 counts tickets from ev['reg'] (g0_judge.py:176-178): creator != 'O' -> FAIL | C03=F C11=F C13=P C16=P → **FAIL**：check_order creator test (registry.py:242-246) -> C03 FAIL, and C11 FAIL | C03=U C11=U C13=U C16=P → **BLOCKED**：disk_faithful false -> U2; C11 UNEVALUABLE | **BLOCKED** | INSUFFICIENT：a ticket node appears only in the altered file |
| `FID-D` | durable RUN_END.cleanup_confirmed flipped false -> true; ledger false (transient token residue at RUN_END, S5 clean) — completed clean run: ledger = RUN_START, INTENT n1, FORKED(pid 200), REGISTERED(pid 200, st 5000), RELEASED, DEAD(basis), RUN_END(run_id g0_x, cleanup_confirmed FALSE); release write ok; FIRST_ACTION 1.8; all other checks PASS; durable copy: RUN_END.cleanup_confirmed=true; every other C13 condition holds in the snapshots | C03=P C13=P C16=P → **PASS**：C03: the VALUE of cleanup_confirmed is judged by C13 (V3 pass_when) -> PASS. C13 reads the durable RUN_END (g0_judge.py:206-207): True -> PASS (all other conditions hold) -> wrong PASS: cleanup was unconfirmed | C03=P C13=P C16=P → **PASS**：same | C03=U C13=U C16=P → **BLOCKED**：disk_faithful false -> U2; C13 reads the unfaithful durable copy -> UNEVALUABLE | **BLOCKED** | INSUFFICIENT：ledger says unconfirmed, file says confirmed; no way to know which is right from the file |
| `FID-E` | LEDGER record altered in memory (REGISTERED.pid 201); durable copy correct (200); real pid 200 — completed clean run: ledger = RUN_START, INTENT n1, FORKED(pid 200), REGISTERED(pid 200, st 5000), RELEASED, DEAD(basis), RUN_END(run_id g0_x, cleanup_confirmed true); release write ok; FIRST_ACTION 1.8; all other checks PASS; ledger REGISTERED.pid=201 (a defect mutated the in-memory dict after the append); triples identical | C03=P C04=P C13=P C16=P → **PASS**：C03: F1(d) only checks the type (int) of the ledger pid; triples identical -> faithful -> PASS; C04 reads the (correct) durable copy -> PASS. PASS by luck: the contradiction between ledger and file is never seen | C03=P C04=P C13=P C16=P → **PASS**：the current judge does not read the ledger at all | C03=U C04=U C13=U C16=P → **BLOCKED**：whole-record fidelity detects ledger != file -> U2 (the file is an independent witness of the ledger) | **BLOCKED** | INSUFFICIENT：two first-hand witnesses disagree |

### 1.3 根因

1. **保真检查弱于消费者读取的内容。** 持久副本只经三元组验证，其余字段却被四个检查直接当作一手证据读取。
2. **「损坏」被当作只会丢失，没有考虑被改写。** 丢失（行消失）会让 `reg` 里记录缺失，检查 UNEVALUABLE；改写让记录**存在但值错**，检查给出确定的 PASS 或 FAIL。
3. **违反负责人政策 P5。** 「正面违规证据与证据损坏并存时必须判断该正面证据是否仍可信」——案例 B 里 C04 的『违规』只来自被改写的文件，账本与真实 PID 都说明没有违规；V3 字面却让它无条件决定 FAIL。
4. **对称风险（案例 E）：** 账本若被缺陷改写，持久副本其实是它的独立见证，但三元组比较发现不了。

### 1.4 最小修复方案

* **M-1 完整记录保真。** `disk_faithful` 改为：解析报告干净 **且** 持久副本与账本的**完整记录**按顺序逐条相等，相等以规范化 JSON 比较：`canon(r) = json.dumps(r, sort_keys=True, separators=(",", ":"), allow_nan=False)`（账本记录与解析出的磁盘记录都已是 JSON 类型）。任一字段的差异 ⇒ 不保真 ⇒ `C03-U2`。`foreign_lines` 仍按三元组定义（出处判断），被改写但三元组相同的记录是「不保真」而不是「外来」。`fidelity_scope` 限度删除。
* **M-2 读持久副本的检查不得在不保真时给出裁决。** 增加一条全局规则（放在 `verdict_rule` 与 `witnesses.durable_copy`）：**凡读取 `reg` 的检查（C04、C05、C11、C13）在 `disk_faithful` 为假时一律 UNEVALUABLE。** 这是最小改动：四个检查的文字不变，只是它们读到的证据在不可信时不被使用；L-2 改写为这条规则。
  * 备选 M-2′：把这四个检查改读账本。判定力更强（案例 B 里 C04 可对账本评估），但改变四个检查的证据来源，差异更大；本审查推荐 M-2，供 Grok 与 ChatGPT 裁决。
* **效果（见表）：** A、B、C、D、E 在 V4 提案下全部为 **BLOCKED**；不会再有由改写的文件造成的 PASS 或 FAIL；账本与文件互为独立见证，任一被改写都得到 U2。
* **不改变：** F1–F4 只依赖账本与独立证据的设计；正面违规在账本中仍然是 FAIL（CE-R5e）；`foreign_lines` 压制缺失类规则的设计。

---

## 2. F-21：判定前是否真正读回磁盘证据

### 2.1 V3 中四处相关文字——它们不是同一个操作

| 位置 | 文字 | 操作 | 接触文件？ |
|---|---|---|---|
| `g0_criteria_v3.json:1015`（C16 text） | 「证据……as READ BACK from g0_evidence.json」 | 先写文件、再**读取该文件** | 是 |
| `:149`（`evidence_schema.validation`） | 「判定函数……on the evidence AS READ BACK from g0_evidence.json (JSON types)」 | 同上 | 是 |
| `:150`（`evidence_schema.serialisation`） | 「verdict is computed from `json.loads(json.dumps(evidence))`」 | **内存**中序列化再反序列化 | **否** |
| `E1A_GATE_G0_PREREG_V3.md:65`（§4 步骤 7） | 「组装证据 → 以读回的 JSON 类型判定（`json.loads(json.dumps(evidence))`）→ **写** `g0_evidence.json`、`g0_summary.json`」 | 先判定、**后**写文件 | 判定时文件尚不存在 |

`json.loads(json.dumps(x))` 只能把 Python 类型规整为 JSON 类型（元组→列表等）；它**不能**发现：写文件失败、写入被截断、文件被并发修改、磁盘返回与写入不同的字节，也不能发现序列化时被静默改写的值。步骤 7 的顺序（先判定后写）与 C16 / `validation` 的「读回」在逻辑上不可能同时成立。

### 2.2 现实现（`g0_run.py:414-416`）

`res = GJ.judge(ev)`（内存对象）→ `write_json(evidence)` → `write_json(summary)`。`write_json`（`:242-245`）用 `open(path, "w")`（截断、非排他）和 `json.dump(..., default=str)`——不可序列化的值被**静默转成字符串**，判定看到的是原对象（如 `set`），文件里是 `"{...}"` 字符串；离线重判会得到不同结果。没有读回，没有校验，没有对摘要的写入失败处理（异常以退出码 1 终止，而 1 是 FAIL 的退出码）。

### 2.3 建议的明确顺序（V4 提案）

| 阶段 | 操作 | 失败条件 ⇒ |
|---|---|---|
| P0 | 组装内存证据 `E`（含 `evidence_schema`；账本与 `reg_writer_seq` 在最后一次登记写入之后、解析登记文件之前取得） | 异常 ⇒ 异常路径（BLOCKED） |
| P1 | **严格序列化** `blob = json.dumps(E, sort_keys=True, allow_nan=False)` ——**不用** `default=str` | `TypeError`/`ValueError`（非 JSON 值、NaN）⇒ **BLOCKED** |
| P2 | 以排他方式（`open(path, "xb")`）写 `blob` 到 `g0_evidence.json`（仅在本进程创建的运行目录），`flush` + `fsync`，关闭，再 `fsync` 目录 | 已存在、IO 错误、短写 ⇒ **BLOCKED**（不声称裁决；stderr 给出错误与标记为 `UNSAVED` 的内存裁决；运行目录可写时另写 `g0_blocked_<run_id>.json`） |
| P3 | **读回**：重新打开文件读出全部字节 `B2`；`B2 == blob` 且 `sha256(B2)` 记录；`E2 = json.loads(B2)` | 字节不等、解析失败 ⇒ **BLOCKED** |
| P4 | 在 `E2` 上按 `evidence_schema` 验证字段 / 类型（C16 的依据） | 不符 ⇒ C16 失败（BLOCKED 类），依赖缺失字段的检查 UNEVALUABLE；**照常继续到 P5** |
| P5 | **只对 `E2` 做裁决**（判定函数永远看不到内存里的 `E`） | 判定函数异常 ⇒ **BLOCKED** |
| P6 | 排他写 `g0_summary.json`：`verdict`、`exit_code`、各检查结果、FAIL 时的 `fail_scope`、`evidence_sha256`（= P3 的哈希）、`criteria_sha256`；`flush` + `fsync`；**读回并核对**（解析成功且 `evidence_sha256` 一致） | 写入失败或读回不一致 ⇒ **BLOCKED**，退出码 3，stderr 写出 `UNSAVED VERDICT: <v>` 与证据哈希；证据文件保留；下一次预检因缺 `g0_summary.json` 而 BLOCKED |
| P7 | 退出码 = **已保存并核对**的摘要所记裁决的退出码 | — |

* 摘要与证据文件均**不覆盖**任何既有文件；一个裁决只有在证据文件与摘要都被保存并读回核对之后才算「被记录」。
* `evidence_sha256` 使摘要绑定到被判定的那一份字节，离线重判可复现。

| 案例 | 情形 | 各阶段结果 | V4 提案下的结果 | 现实现 |
|---|---|---|---|---|
| `PIPE-1` | everything succeeds | P1 serialise: ok；P2 write evidence: ok；P3 read back: bytes equal；P4 validate: ok；P5 judge: PASS；P6 summary saved+verified: ok | PASS, exit 0 | judge on in-memory ev, then write (g0_run.py:414-416): no read-back |
| `PIPE-2` | writing g0_evidence.json fails (ENOSPC, EEXIST, EROFS) | P2 write evidence: OSError | BLOCKED, exit 3; no verdict claimed; stderr carries the error and the in-memory verdict labelled UNSAVED; evidence_blocked note written if the run directory still accepts it | write_json raises after judge; the run dies with a traceback and exit code 1 (the FAIL code) |
| `PIPE-3` | the file read back differs from the bytes written (truncation, bit flip, concurrent writer) | P2 write evidence: ok；P3 read back: bytes differ | BLOCKED, exit 3 | not detected |
| `PIPE-4` | the evidence contains a non-JSON value (e.g. a set) | P1 serialise: TypeError (strict, no default=str) | BLOCKED, exit 3 | write_json(default=str) (g0_run.py:244) silently stores a string; the in-memory judge saw a set, an offline re-judge sees a string |
| `PIPE-5` | read back fine, but reg_writer_seq is the string '7' | P3 read back: ok；P4 validate: C16 type error；P5 judge: verdict computed on the READ-BACK evidence: C16 BLOCKED, C03-U0 | BLOCKED, exit 3 | no schema validation |
| `PIPE-6` | verdict FAIL computed, but g0_summary.json cannot be saved | P5 judge: FAIL；P6 summary: OSError | BLOCKED, exit 3; stderr states 'UNSAVED VERDICT: FAIL' and the evidence sha256; the evidence file remains; the next preflight sees a run directory without g0_summary.json | exception after the evidence was written; exit code 1 would read as FAIL while no summary exists |
| `PIPE-7` | summary written but its read-back sha256 does not match | P6 summary: read-back mismatch | BLOCKED, exit 3 | not checked |

---

## 3. F-22：C03-F3 的规则冲突

### 3.1 冲突文字（逐处）

| 位置 | 文字 | 对「追加失败时的 F3」 |
|---|---|---|
| `g0_criteria_v3.json:844-849`（F3；`when` 在 `:847`） | `applies`：「only when no foreign_lines and the independent evidence needed is present」；`when` 末句：「**This applies even when an append failed**: an action that happened although its precursor append failed is itself the violation」 | **适用 ⇒ FAIL** |
| `:879`（`precedence`） | 「absence-based rules (**F2, F3, F4**) **need writer_clean** and no foreign lines, because a failed append or a foreign line makes an absence uninterpretable」 | **不适用 ⇒ 被压制 ⇒ U3 ⇒ BLOCKED** |
| `:867`（U3） | 「the writer failed … (an append failed; a missing record may be explained by the failure)」 | 倾向 BLOCKED |
| 预注册 §5.1 表（`E1A_GATE_G0_PREREG_V3.md:117-118`）与 `:132` | 同上，逐字复制 | 同样冲突 |
| 反例矩阵 `CE-R4c` | 选了 FAIL（F3） | 只在矩阵里选择，冻结文本里没有 |

### 3.2 单一、无歧义的规则（V4 提案）

删除散文里的两处互相矛盾的句子，改为 **一张机器可读的需求表**（唯一来源）：

| 规则 | 需要账本 | 需要 `writer_clean` | 需要「无外来行」 | 需要独立证据 | 需要 `completed_run` |
|---|---|---|---|---|---|
| F1 | 是 | 否 | 否 | 否 | 否 |
| F2 | 是 | **是** | 是 | 否 | 否 |
| F3 | 是 | **否（明确不要求）** | 是 | 是 | 否 |
| F4 | 是 | 是（完成运行蕴含） | 是 | 否 | 是 |

文字：「`writer_clean` 只被 F2 与 F4 要求。F3 不要求：动作（放行写入已成功、子进程已通过门控、fork 已发生）与前置记录的缺失都是一手事实，追加失败可以解释缺失，但不能使动作合规。」`precedence` 中的那句改为「F2 与 F4 需要 writer_clean；F2、F3、F4 都需要无外来行」。

**理由（方案 α）：** C03 要证明的是『未登记的子进程不得行动』这一过程安全约束；若前置追加失败而子进程仍行动，被违反的恰是这个约束。要抑制这个 FAIL，就必须怀疑「动作发生了」的一手证据，而这一证据（守卫的放行写入记录、子进程自己的 FIRST_ACTION）与登记表无关。**备选 β（F3 也需要 `writer_clean`）：** 表中 F3 一格改为「是」，DD-5 反例变为 BLOCKED；这是**一格之差**，不影响其他规则。α / β 的取舍属于 DD-5，待 Grok 与 ChatGPT。

### 3.3 用 DD-5 反例验证

| 案例 | 输入 | V3 字面 | 方案 α（F3 不需要 writer_clean） | 方案 β（F3 需要 writer_clean） | 可信度 |
|---|---|---|---|---|---|
| `REL-DD5` | child passed the gate although the REGISTERED append failed (CE-R4c): ledger seq 1,2,3,5; reg_writer_seq 5; release write ok; FIRST_ACTION present — ledger = RUN_START, INTENT, FORKED, RUN_END(false)(seq 5); REGISTERED/RELEASED never appended; durable copy identical to the ledger; early stop | 歧义：F3.when (g0_criteria_v3.json:847) says it 'applies even when an append failed' -> FAIL; precedence (:879) says F2, F3 and F4 'need writer_clean' -> F3 suppressed -> U3 -> BLOCKED. The frozen text gives both answers | C03=F C07=U C16=U C15=U C17=U → **FAIL**：single rule alpha: F3 needs NO writer_clean -> gate_passed with REGISTERED absent -> C03-F3 FAIL | C03=U C07=U C16=U C15=U C17=U → **BLOCKED**：single rule beta: F3 needs writer_clean -> suppressed -> C03-U3 | MEDIUM：alpha: the gate pass and the absence of REGISTERED in the ledger are both first-hand; the append failure explains the absence but cannot excuse the action |
| `REL-FOREIGN` | F3 situation but the durable copy contains a REGISTERED line the writer never appended — as REL-DD5; durable copy additionally has '4 REGISTERED n1 pid=200' (foreign) | BLOCKED：F3 'only when no foreign_lines' -> suppressed; U2 | C03=U C07=U C16=U C15=U C17=U → **BLOCKED**：F3 needs no foreign lines -> suppressed; U2 | C03=U C07=U C16=U C15=U C17=U → **BLOCKED**：same | INSUFFICIENT：witness conflict: the file contradicts the ledger's absence |
| `REL-RUNEND` | the append of RUN_END(false) failed; every precursor is in the ledger; child passed the gate — ledger = RUN_START, INTENT, FORKED, REGISTERED, RELEASED (seq 1-5); reg_writer_seq 6; release ok; FIRST_ACTION present; durable copy identical to ledger; early stop | BLOCKED：F3 finds no absent precursor -> does not fire; U3 -> BLOCKED | C03=U C07=P C16=U C15=U C17=U → **BLOCKED**：no fail rule fires; U3 | C03=U C07=P C16=U C15=U C17=U → **BLOCKED**：same | INSUFFICIENT：writer failure; the end marker was never recorded |
| `REL-F2GATE` | REGISTERED without FORKED AND an append failed (CE-F5): F2 stays gated by writer_clean under both alpha and beta — ledger seq 1,2,4,5 = RUN_START, INTENT, REGISTERED, RUN_END(false); reg_writer_seq 5; no release; early stop | BLOCKED：F2 'only when writer_clean' -> suppressed; U3 | C03=U C07=U C16=U C15=U C17=U → **BLOCKED**：F2 requires writer_clean -> U3 | C03=U C07=U C16=U C15=U C17=U → **BLOCKED**：same | INSUFFICIENT：the missing FORKED may be explained by the failed append (owner policy: BLOCKED) |

* α：DD-5 ⇒ FAIL（MEDIUM）；β：BLOCKED；两者对 `REL-FOREIGN`、`REL-RUNEND`、`REL-F2GATE` 的结论相同，说明 α / β 的唯一差别就是 DD-5 这一类（动作已发生 + 前置追加失败）。
* 原 51 个矩阵案例中受影响的只有 `CE-R4c`；F3 触发的其余案例（`CE-P4`、`CE-R4b`、`CE-R8b`）writer 都干净，两方案结果相同；`writer_clean` 为假的其余案例（`CE-G1`、`CE-F5`、`CE-R5c`、`CE-R5d`）没有 F3 触发条件，结果也相同。

---

## 4. 规范修订是否确实需要 V4

| 项 | 能否不出 V4 而解决 | 理由 |
|---|---|---|
| F-20 | 否 | `disk_faithful` 的定义与 L-2 都是冻结文本；实现者若自行加强比较，就是偏离冻结文本；若按冻结文本实现，案例 A/B 得到错误裁决 |
| F-21 | 否 | C16 文字（读回文件）与 `serialisation`（内存往返）与步骤 7（先判定后写）三处冻结文字互相排斥，任何实现都违反其中一处 |
| F-22 | 否 | F3 的 `when` 与 `precedence` 互相矛盾，任何实现都违反其中一处 |

**结论：需要 V4。** 并且应当**只出一次**：把待 Grok 裁决的 DD-1…DD-5 一并写入，避免再出 V5。**在 Grok 报告到达之前不创建 V4。**

## 5. DD-1…DD-5：保留设计基线，等待 Grok

ChatGPT 的有条件结论：**其文本没有包含在本任务收到的指令中**，本文不转述、不推测；请项目负责人把原文附在检查点上。Grok：**GROK REVIEW PENDING**。若 Grok 给出相反意见，**不直接选择任何一方**，而是：（i）写明分歧；（ii）用下面的受控验证把分歧缩到一个**判定表中的一格**；（iii）由两位审核者对这一格的预期裁决共同签字，再由负责人拍板。

| DD | V3 冻结的设计基线 | 区分案例 | 另一读法 | 风险不对称 | 最小受控验证 |
|---|---|---|---|---|---|
| DD-1 | 账本取**全记录** | `CE-F1/G1/G2/R5a-e/F4-F6`、`FID-A…E` | 仅计数 + 序号（所有缺失类 FAIL 规则降为 BLOCKED） | 误 FAIL：把台架问题记成协议违规；误 BLOCKED：真违规被「证据不足」掩盖 | 同一判定表在两种读法下对上述案例的输出之差，由双方签字；授权的纯逻辑阶段用表驱动测试；首次受控 G0 的**干净**运行中，账本与持久副本的完整记录必须逐条相等（不等 ⇒ 账本设计不可靠） |
| DD-2 | 已佐证缺 FORKED 而持久副本在别处另有损坏 ⇒ FAIL（F2 只依赖账本） | `CE-F4` | 持久副本不保真就 BLOCKED | 同上 | 判定表中 F2 的「需要 disk_faithful」一格 |
| DD-3 | 写入失败而子进程仍有 FIRST_ACTION ⇒ C07-F3 FAIL（MEDIUM） | `CE-R6` | BLOCKED | 误 FAIL：可能是仪表缺陷；误 BLOCKED：放行泄漏被掩盖 | 判定表中 C07-F3 的一格；首次受控 G0 干净运行中，每个 FIRST_ACTION 必有且仅有一条成功的放行写入记录 |
| DD-4 | 子进程通过而无尝试记录：账本有 RELEASED ⇒ BLOCKED，无 ⇒ FAIL | `CE-R8a/b` | 两者都 BLOCKED 或都 FAIL | 同上 | 判定表中的两格；干净运行中放行写入记录的存在性 |
| DD-5 | F3 在追加失败时仍适用 ⇒ FAIL（MEDIUM） | `REL-DD5`（= `CE-R4c`） | β（F3 需要 `writer_clean`） | 误 FAIL：追加失败可能掩盖了仪表问题；误 BLOCKED：未登记子进程已行动却不被记录为 FAIL | 判定表中 F3 的 `writer_clean` 一格（§3.2 表） |

* 真实进程层面的验证只能来自负责人另行授权的首次受控 G0 **干净**运行（它只验证「在无故障时账本 = 持久副本、放行写入记录存在」）；EPIPE、追加失败、门被绕过等故障注入属于 G1–G3，不在 G0 范围。
* 本文件不替审核者做决定；V4 的 DD 槽位在 Grok 报告之后填入。

## 6. V4 一次性最小差异清单（**不创建 V4**；在 Grok 报告与 DD 裁决之后一次冻结）

| 编号 | 变更 | 解决 |
|---|---|---|
| D1 | `definitions.disk_faithful`：改为完整记录的规范化相等（`canon`）；`foreign_lines` 仍按三元组；删除 `policy_notes.fidelity_scope` 的限度，改为「任一字段被改动都会被发现」 | F-20 |
| D2 | `C03-U2` 文字：「持久记录与账本的任何差异」 | F-20 |
| D3 | 全局规则（`verdict_rule` 与 `witnesses.durable_copy`）：读取 `reg` 的检查（C04 C05 C11 C13）在 `disk_faithful` 为假时一律 UNEVALUABLE；改写 L-2。（备选 D3′：这四个检查改读账本） | F-20 |
| D4 | C03 `rules` 增加机器可读 `requirements` 需求表（§3.2），删去 `precedence` 与 F3 `when` 中互相矛盾的句子；F3 一格按 DD-5 的裁决填 | F-22 |
| D5 | `evidence_schema.validation` / `serialisation` 与 C16 文字：替换为 §2.3 的 P0–P7 流水线；`g0_summary.json` 必需字段（`verdict`、`exit_code`、`checks`、`fail_scope`、`evidence_sha256`、`criteria_sha256`）；各阶段 BLOCKED 条件 | F-21 |
| D6 | 预注册 §4 步骤 7 / 8 改为同一流水线；新增 `enforcement.evidence_pipeline` | F-21 |
| D7 | V3→V4 映射：C03 MODIFIED、C16 MODIFIED、C04 / C05 / C11 / C13 CLARIFIED（只增加「持久副本不保真 ⇒ UNEVALUABLE」）、其余 IDENTICAL；若 DD-3 / DD-4 的裁决改变 C07，则 C07 也列入 | 全部 |
| D8 | DD-1…DD-5 的裁决写入对应规则（避免 V5） | DD |
| D9 | 不变：C01–C17 编号、V3 的政策、`fail_scope`、F-14 / 程序性义务限度（除非审核者要求） | — |

**V4 不得触及：** 实现、台架、既有测试、E1-A 原预注册、R3、CPU-001/002、Parcae、任何关于 Mythos 模型架构的结论。

## 7. 依赖与未解决问题

1. **GROK REVIEW PENDING**——没有双 AI 共识。
2. ChatGPT 对 DD-1…DD-5 的有条件结论原文尚未附上（本会话未收到）。
3. 项目负责人对「是否出 V4」的决定，以及 M-2 与 M-2′、α 与 β 的取舍。
4. 仍然开放：F-14（L-1）、程序性义务不被判定函数验证、F-1（台架把僵尸当已死）、F-19 将由 D3 / D3′ 关闭。
5. 实现仍不符合 V3（更不符合将来的 V4）；46 个纯逻辑测试仍未运行。
