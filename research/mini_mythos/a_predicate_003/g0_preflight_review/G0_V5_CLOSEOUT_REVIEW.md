# G0_V5_CLOSEOUT_REVIEW — F-23 结案标记：V5 最小修订的审查记录、反例矩阵与可追溯性

**状态：`G0 V5 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V5-CLOSEOUT-SPEC-001`。审核基准 `d127ec58c0adc90d11fb7fc59240632fc4e36d5b`。V5 冻结提交 `8530ba5ca8a211f4d9f6e490b874e3b8b0af7906`（只含 `g0_criteria_v5.json`、`.sha256`、`E1A_GATE_G0_PREREG_V5.md`），本文件在其**之后**提交。
**没有修改** V1…V4、`g0_run.py` / `g0_judge.py` / `g0_auth.py`、`bench/`、既有测试、E1-A 原预注册、R3、CPU-001/002、Parcae；**没有运行**纯逻辑测试、真实 G0、BV、E1-A、GPU 或训练；没有创建执行授权文件，没有启动受测进程。只运行了只读取判据 / 案例文件的静态检查。
**本文件中所有案例结论都是对 V5 规则的手工推导（静态案例，设计审查），不是实验 PASS，也不是测试 PASS。**

## 0. 关于审核意见的可追溯性

任务文本说明：ChatGPT 与 Grok 已完成 V4 的独立静态审核，双方确认 F-23；Grok 建议创建 `g0_closed.json`，ChatGPT 同意，但要求区分结案文件的**存在性、内容有效性、原子发布和真实进程终止**。**两位审核者的原文不在本会话中**，我没有引用或臆造其中任何细节。V5 的每项决定依据任务文本；任务文本只给方向而需要我形式化的，在决策登记中标 `derived`（CL-A、CL-B、CL-D、CL-E），请审核者确认；任务文本明确写出的标 `stated`（F-23、CL-C）。**所有 V5 决定都是「拟由负责人批准」，审核者意见一致是静态设计审查，不是真实进程验证。**

## 1. 验收清单

| # | 条件 | 证据 | 状态 |
|---|---|---|---|
| 1 | V5 判据与文字一致 | `tools/check_g0_v5_consistency.py`：检查表 17 行、V4→V5 映射 + V3→V4 附录 34 行、91 个证据字段、闭环规则 23 条、K 步骤、失败表、事实表、崩溃点、决策 15 项、义务、限度逐项核对 JSON ↔ 文字，0 不一致 | 满足（自检） |
| 2 | 旧冻结文件不变 | 同一工具核对 V1、V2、V3、V4 八个文件的 SHA-256；V5 提交只新增三个文件 | 满足 |
| 3 | 只修改了授权范围内的内容 | 工具计算 V4 → V5 实际改动的 24 个路径，要求恰等于 `v4_to_v5_changes` 声明的路径；C02…C17 逐字相同（16 项 IDENTICAL，仅 C01 MODIFIED）；V4 的 9 项决策（含 DD-1…DD-5）、`verdict_rule` 前 11 行、5 条限度逐字保留 | 满足（含一处勘误，见 §7 第 1 点） |
| 4 | F-23 反例均有明确结果 | §4（A–H 逐项）与 §5（全部 38 个案例，每个都有预检裁决、保留文件、是否需要人工处理）；§6 的 19 个流水线失败案例 | 满足 |
| 5 | 没有新增的 summary / closed 状态矛盾 | `tools/check_g0_v5_closure_cases.py` 用 JSON 中的机器可读规则对每个案例的事实求值，并核对 23 条规则每条至少被一个案例触发、事实的 na 一致性、文件存在性与事实一致性、崩溃点与流水线案例的结果；§7 列出守卫与变异测试 | 满足（无**已知**矛盾；残余风险见 §8） |
| 6 | 决策可追溯 | 判据 `decision_register`（15 项，前 9 项逐字不变）与 §2 | 满足（含声明的局限） |
| 7 | Git 顺序：先冻结 V5，再提交反例矩阵、一致性审查、映射和 checkpoint | `8530ba5`（3 个文件）早于本文件所在提交 | 满足 |

## 2. 新增决策（V5；前 9 项 V4 决策不变）

| ID | 主题 | V5 规则 | 来源 |
|---|---|---|---|
| `F-23` | summary existence is not closure | closure marker g0_closed.json created after the evidence and summary were saved and verified; preflight requires a valid marker bound to both files | stated：stated in the task text of G0-V5-CLOSEOUT-SPEC-001 (Grok proposed g0_closed.json, ChatGPT agreed with the distinctions) |
| `CL-A` | atomic exclusive publication | temporary file with O_EXCL, fsync, verify, os.link to the final name (EEXIST means never replace), directory fsync, verify; no rename / replace / direct write | derived：derived by the specifier from the task text's request to research the smallest atomic exclusive publication scheme without overwriting; os.link was chosen because it is standard library, atomic and exclusive (alternatives in closure.publication.why_not_*); reviewers to confirm |
| `CL-B` | handling of an unsynced or unconfirmed closure | a published valid marker is judged by preflight on what the files are (CLOSED_OK if all bindings hold); the process exits 3 and prints G0-CLOSE-UNCONFIRMED; the outcome is reported as BLOCKED unless exit status, absence of G0-CLOSE-* markers and read-back agree (reporting_rule) | derived：derived by the specifier from the task text (file sync failure, crash after publication, re-preflight); reviewers to confirm |
| `CL-C` | closure is not process-exit proof | the marker has process_exit_proof = false; G0-C01 evaluates live 'g0_run.py' processes and MANUAL_DISPOSITION_REQUIRED.json independently of the marker | stated：stated in the task text (the closure marker must not be taken as independent proof that the original process exited) |
| `CL-D` | preflight accepts a valid marker of any recorded verdict | a valid marker with recorded_verdict PASS, FAIL or BLOCKED closes the run; the verdict decides nothing about closure | derived：derived by the specifier (V4 C01 required a closed run, not a PASS); reviewers to confirm |
| `CL-E` | the temporary name is never deleted | g0_closed.json.tmp stays next to the marker; a byte-identical temporary file is tolerated by preflight, any other content is STRAY_CLOSURE_FILE | derived：derived by the specifier to keep V4's no-delete rule; reviewers to confirm |

## 3. F-23 与 V5 的修改

* **缺陷（只读代码证据）：** `g0_run.py` 第 224–225 行的预检把「`g0_` 目录中缺少 `g0_summary.json`」当作未结案，等价于「摘要存在 ⇒ 已结案」。V4 的 P6 以 `O_EXCL` 创建摘要后再写入、fsync、读回；任一步失败都可能留下半截或未验证的摘要，而 V4 文字却说「下一次预检会看到没有摘要的运行目录并拒绝」——两者矛盾。案例 `A2` 就是该场景。
* **V5 的修改（机器可读清单 `v4_to_v5_changes`）：** P6 失败文字、P7 改为「发布结案标记并退出」（K0–K7）、C01 对历史运行的要求、新增 `closure`（标记结构、发布、预检事实与规则 CL-01…CL-23、崩溃点）、相关的执行约束 / 裁决政策 / 限度 / 义务，以及证据模式两处说明文字。
* **不变：** C02…C17；C03 / C07 / C16 规则；DD-1…DD-5 及 V4 全部条件决策；FAIL 的归因范围。

| 变更 | 对应问题 | 涉及路径 | 内容 |
|---|---|---|---|
| `V5-CH-1` | F-23 | `evidence_pipeline.stages.P6` | a failed P6 no longer relies on a missing summary file to keep later runs out; a partial or unverified summary file is not closure and the missing marker is what blocks |
| `V5-CH-2` | F-23 | `evidence_pipeline.stages.P7`, `evidence_pipeline.stages.P5`, `evidence_pipeline.principle`, `evidence_pipeline.preserved_on_failure`, `evidence_pipeline.durability_limits`, `evidence_pipeline.overwrite_policy` | P7 publishes the closure marker (K1..K7) and returns the exit code only afterwards; P5, durability and overwrite texts adapted |
| `V5-CH-3` | F-23 | `checks.G0-C01` | C01 requires every earlier run to be closed by a valid marker and evaluates process residue independently |
| `V5-CH-4` | F-23 | `closure` | new: marker schema, atomic exclusive publication, preflight facts and rules CL-01..CL-23, crash points, what closure does and does not prove |
| `V5-CH-5` | F-23 | `enforcement`, `verdict_rule`, `verdict_policy`, `implementation_obligations`, `limitations`, `meaning_of_pass`, `amendment_policy` | enforcement, verdict policy, verdict rule, obligations, limitations and the meaning of PASS mention the closure; amendment policy points to the next file names |
| `V5-CH-6` | V4 erratum | `evidence_schema` | documentation only: the note of field 'evidence_schema' said 'e1a-gate-g0-evidence-3' while the schema id, C16 and the obligations say '-4'; the note now says '-4'. The preflight field note names the new unresolved_prior format. No field, type or consumer changed. Reviewers are asked to confirm that this correction belongs in V5 |
| `V5-CH-7` | identity | `criteria_id`, `schema_version`, `base_commit`, `supersedes`, `decision_register`, `v4_to_v5_mapping`, `v4_to_v5_changes` | identity, supersession, decision register (DD-1..DD-5 and all V4 decisions unchanged; closure decisions added), V4->V5 mapping and change list |

## 4. 任务要求的 A–H 反例：预检裁决、允许保留的文件、是否需要人工处理

每一行的「预检裁决」都由 `closure.preflight.rules` 对事实求值得出（`tools/check_g0_v5_closure_cases.py`）。预检**只读**：任何文件都被保留，不删除、不重命名、不修复、不代替已终止的进程补写标记。

| 任务要求 | 案例 | 预检裁决 | 允许保留的文件 | 是否需要人工处理 |
|---|---|---|---|---|
| A. summary 存在，closed 不存在 | `A`（另见 `A2`, `A3`） | **BLOCKED**：NO_CLOSED | registry.jsonl, g0_evidence.json, g0_summary.json | 是（H1） |
| B. closed 存在但 JSON 被截断 | `B`（另见 `B2`, `B3`, `B4`, `B5`, `B6`） | **BLOCKED**：CLOSED_PARSE | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 是（H1） |
| C. closed 合法，但 summary 哈希不匹配 | `C`（另见 `C2`, `C3`, `C4`, `C5`） | **BLOCKED**：SUMMARY_HASH | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） |
| D. summary 与 evidence 相互匹配，但 closed 的 criteria_sha256 不匹配 | `D`（另见 `D2`） | **BLOCKED**：CRITERIA_MISMATCH | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） |
| E. closed 发布前进程异常终止 | `E`（另见 `F2`） | **BLOCKED**：NO_CLOSED | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json.tmp | 是（H1） |
| F. closed 发布后、目录同步前发生异常 | `F`（另见 `F3`） | **CLOSED_OK** | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 否 |
| G. closed 有效，但仍存在 MANUAL_DISPOSITION_REQUIRED 或活跃残留进程 | `G`（另见 `G2`, `G3`, `G4`） | **BLOCKED**：MANUAL_DISPOSITION | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp, MANUAL_DISPOSITION_REQUIRED.json | 是（H2） |
| H. 所有证据合法、结案标记合法、无残留 | `H`（另见 `H2`, `H3`, `H4`） | **CLOSED_OK** | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 否 |

关于 F：预检看到的是**文件**，所以 `F` 与 `F3` 的预检结果是 `CLOSED_OK`；但该运行的**进程级结果**按 `closure.publication.reporting_rule` 报告为 BLOCKED（退出码不等于记录的退出码，或出现 `G0-CLOSE-*` 标记，或被杀死），**绝不是 PASS**。`F2`（操作系统崩溃、目录项丢失）则退化为 `NO_CLOSED`。

## 5. 全部 38 个闭环案例（32 个 BLOCKED，6 个 CLOSED_OK）

「V4 读法」：V4 文字与 `g0_run.py` 第 224–225 行只看 `g0_summary.json` 是否存在（以及人工处置文件、存活进程）。按这一读法，25 个案例会被**误认为已结案**而 V5 拦下；其中不少状态（如标记被篡改）在 V4 的协议下本来不会出现，这里只用来显示规则的差别，不表示 V4 会真的产生它们。

| 案例 | 情形 | 事实（非默认） | 预检裁决 | 规则 / 原因码 | 保留的文件（均不删除、不修复） | 人工处理 | V4 读法 |
|---|---|---|---|---|---|---|---|
| `A` | summary complete and verified, no g0_closed.json — the process stopped after P6 verified the summary and before K2 (crash point X1); the files are complete | closed=absent | **BLOCKED（拒绝新的真实 G0 运行）** | CL-02 `NO_CLOSED` | registry.jsonl, g0_evidence.json, g0_summary.json | 是（H1） | 视为已结案 |
| `A2` | partial summary left by a failed P6 write — P6 created g0_summary.json with O_EXCL, then the write failed halfway (ENOSPC); the process printed G0-SUMMARY-UNSAVED and exited 3 | closed=absent | **BLOCKED（拒绝新的真实 G0 运行）** | CL-02 `NO_CLOSED` | registry.jsonl, g0_evidence.json, g0_summary.json | 是（H1） | 视为已结案 |
| `A3` | everything saved, temporary marker complete but never published — crash point X3: K2 fsynced the temporary file, the process died before K4 | closed=absent, tmp=other | **BLOCKED（拒绝新的真实 G0 运行）** | CL-02 `NO_CLOSED` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `B` | g0_closed.json truncated — the marker file ends in the middle of the JSON text | closed=unparsable | **BLOCKED（拒绝新的真实 G0 运行）** | CL-04 `CLOSED_PARSE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 是（H1） | 视为已结案 |
| `B2` | g0_closed.json is empty — size 0 | closed=oversize_or_empty | **BLOCKED（拒绝新的真实 G0 运行）** | CL-03 `CLOSED_UNREADABLE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 是（H1） | 视为已结案 |
| `B3` | g0_closed.json has a trailing newline — content equals the marker plus one newline (edited by hand or by a tool) | closed=noncanonical, tmp=other | **BLOCKED（拒绝新的真实 G0 运行）** | CL-05 `CLOSED_NONCANONICAL` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `B4` | g0_closed.json has a duplicate key — {"run_id": a, ..., "run_id": b} | closed=unparsable | **BLOCKED（拒绝新的真实 G0 运行）** | CL-04 `CLOSED_PARSE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 是（H1） | 视为已结案 |
| `B5` | g0_closed.json is a symlink — the final name is a symbolic link | closed=not_regular | **BLOCKED（拒绝新的真实 G0 运行）** | CL-03 `CLOSED_UNREADABLE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 是（H1） | 视为已结案 |
| `B6` | g0_closed.json has a wrong type — recorded_exit_code is true instead of the integer 1 | closed=schema_invalid | **BLOCKED（拒绝新的真实 G0 运行）** | CL-06 `CLOSED_SCHEMA` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 是（H1） | 视为已结案 |
| `C` | valid marker, summary hash mismatch — g0_summary.json was modified after the closure (same length, different bytes) | closed=ok, summary=hash_mismatch, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-11 `SUMMARY_HASH` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C2` | valid marker, summary shorter than bound — g0_summary.json truncated | closed=ok, summary=size_mismatch, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-11 `SUMMARY_HASH` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C3` | valid marker, summary deleted — g0_summary.json is gone | closed=ok, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-09 `SUMMARY_MISSING` | registry.jsonl, g0_evidence.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | BLOCKED |
| `C4` | valid marker, evidence hash mismatch — g0_evidence.json was modified after the closure | closed=ok, summary=ok, evidence=hash_mismatch, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-16 `EVIDENCE_HASH` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C5` | valid marker, evidence missing — g0_evidence.json is gone | closed=ok, summary=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-14 `EVIDENCE_MISSING` | registry.jsonl, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C6` | valid marker, summary bound but its verdict differs from the marker — the summary has the bound hash, its verdict is PASS, the marker says recorded_verdict FAIL (an inconsistent or forged marker) | closed=ok, summary=ok, summary_binding=mismatch, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-13 `SUMMARY_BINDING` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C7` | valid marker, evidence run_id differs — the evidence has the bound hash but evidence.run_id is another run's | closed=ok, summary=ok, evidence=ok, evidence_binding=mismatch, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-18 `EVIDENCE_BINDING` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C8` | marker copied from another run — closed.run_id is another run's id; the bound hashes do not match this directory's files | closed=ok, closed_runid=mismatch, summary=hash_mismatch, evidence=hash_mismatch, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-07 `CLOSED_RUNID`, CL-11 `SUMMARY_HASH`, CL-16 `EVIDENCE_HASH` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C9` | summary has the bound hash but is not JSON — the bound summary bytes do not parse as strict JSON | closed=ok, summary=unparsable, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-12 `SUMMARY_PARSE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C10` | evidence has the bound hash but is not JSON — the bound evidence bytes do not parse | closed=ok, summary=ok, evidence=unparsable, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-17 `EVIDENCE_PARSE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `C11` | summary and evidence not regular files — g0_summary.json and g0_evidence.json are directories / symlinks | closed=ok, summary=not_regular, evidence=not_regular, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-10 `SUMMARY_UNREADABLE`, CL-15 `EVIDENCE_UNREADABLE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `D` | summary and evidence match each other, marker's criteria_sha256 differs — summary.criteria_sha256 and the running tool's hash agree with each other; closed.criteria_sha256 is another value | closed=ok, criteria_vs_tool=mismatch, criteria_vs_summary=mismatch, summary=ok, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-08 `CRITERIA_MISMATCH` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `D2` | marker agrees with the summary but not with the running tool — the run was made under another criteria hash | closed=ok, criteria_vs_tool=mismatch, summary=ok, evidence=ok, tmp=identical | **BLOCKED（拒绝新的真实 G0 运行）** | CL-08 `CRITERIA_MISMATCH` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `E` | process died before the marker was published (mid-write of the temporary file) — crash point X2: the temporary file is partial | closed=absent, tmp=other | **BLOCKED（拒绝新的真实 G0 运行）** | CL-02 `NO_CLOSED` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `F` | process died after publication, before the directory sync — crash point X4: link returned, the process was killed; the files are intact | closed=ok, summary=ok, evidence=ok, tmp=identical | **CLOSED_OK（继续 C01 的其他条件）** | 无规则触发 | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 无 | 视为已结案 |
| `F2` | operating system crash after link, directory entry lost — crash point X7: the final name did not reach the disk; the already fsynced temporary name may still exist | closed=absent, tmp=other | **BLOCKED（拒绝新的真实 G0 运行）** | CL-02 `NO_CLOSED` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `F3` | directory fsync failed (K5), process exited 3 — G0-CLOSE-UNCONFIRMED printed; the marker is published and intact | closed=ok, summary=ok, evidence=ok, tmp=identical | **CLOSED_OK（继续 C01 的其他条件）** | 无规则触发 | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 无 | 视为已结案 |
| `G` | valid marker but MANUAL_DISPOSITION_REQUIRED.json in the run directory — the run ended with a surviving process; the marker was still published for the saved files | closed=ok, summary=ok, evidence=ok, tmp=identical, manual_disposition=True | **BLOCKED（拒绝新的真实 G0 运行）** | CL-20 `MANUAL_DISPOSITION` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp, MANUAL_DISPOSITION_REQUIRED.json | 是（H2） | BLOCKED |
| `G2` | valid marker but a live process carries the g0_run.py marker — the original process (or its child) has not exited | closed=ok, summary=ok, evidence=ok, tmp=identical, live_marker_process=True | **BLOCKED（拒绝新的真实 G0 运行）** | CL-22 `LIVE_RESIDUE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H2） | BLOCKED |
| `G3` | valid marker, manual disposition and a live process — both residue evidences | closed=ok, summary=ok, evidence=ok, tmp=identical, manual_disposition=True, live_marker_process=True | **BLOCKED（拒绝新的真实 G0 运行）** | CL-20 `MANUAL_DISPOSITION`, CL-22 `LIVE_RESIDUE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp, MANUAL_DISPOSITION_REQUIRED.json | 是（H2） | BLOCKED |
| `G4` | MANUAL_DISPOSITION_REQUIRED.json in the evidence root — an earlier abnormal run left it at the root; this run directory is fine | closed=ok, summary=ok, evidence=ok, tmp=identical, root_manual_disposition=True | **BLOCKED（拒绝新的真实 G0 运行）** | CL-21 `ROOT_MANUAL_DISPOSITION` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H2） | BLOCKED |
| `H` | everything valid, no residue — recorded PASS, marker valid, bindings hold, no manual file, no live process | closed=ok, summary=ok, evidence=ok, tmp=identical | **CLOSED_OK（继续 C01 的其他条件）** | 无规则触发 | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 无 | 视为已结案 |
| `H2` | recorded FAIL is also closed — the marker records FAIL / exit 1; closure is independent of the verdict | closed=ok, summary=ok, evidence=ok, tmp=identical | **CLOSED_OK（继续 C01 的其他条件）** | 无规则触发 | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 无 | 视为已结案 |
| `H3` | recorded BLOCKED is also closed — the marker records BLOCKED / exit 3 | closed=ok, summary=ok, evidence=ok, tmp=identical | **CLOSED_OK（继续 C01 的其他条件）** | 无规则触发 | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 无 | 视为已结案 |
| `H4` | temporary name already removed by a person — marker valid, no temporary file | closed=ok, summary=ok, evidence=ok | **CLOSED_OK（继续 C01 的其他条件）** | 无规则触发 | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json | 无 | 视为已结案 |
| `I` | a different temporary file next to a valid marker — g0_closed.json.tmp with other content | closed=ok, summary=ok, evidence=ok, tmp=other | **BLOCKED（拒绝新的真实 G0 运行）** | CL-19 `STRAY_CLOSURE_FILE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `I2` | another g0_closed* file — g0_closed.json.bak next to a valid marker | closed=ok, summary=ok, evidence=ok, tmp=identical, stray_closure_names=True | **BLOCKED（拒绝新的真实 G0 运行）** | CL-19 `STRAY_CLOSURE_FILE` | registry.jsonl, g0_evidence.json, g0_summary.json, g0_closed.json, g0_closed.json.tmp | 是（H1） | 视为已结案 |
| `J` | a 'g0_' entry that is a symlink — evidence/g0_x -> elsewhere | entry=not_a_directory | **BLOCKED（拒绝新的真实 G0 运行）** | CL-01 `NOT_A_DIRECTORY` | — | 是（H1） | —（V4 无此条目判定） |
| `K` | evidence root cannot be listed completely — listdir failed / returned an error | root_listing=incomplete | **BLOCKED（拒绝新的真实 G0 运行）** | CL-23 `ROOT_LISTING_INCOMPLETE` | — | 是（H1） | —（V4 无此条目判定） |

## 6. P6 / P7 失败案例与崩溃点（19 个）

进程退出码规则：K1…K7 全部成功时为记录的退出码（0、1 或 3）；任何失败为 3。报告规则：只有退出码等于记录的退出码、无 `G0-CLOSE-*` 标记且标记经读回仍有效时，结果才是记录的裁决；否则报告 BLOCKED。

| 案例 | 失败步骤 | 情形 | 已发布 | 进程退出码 | stderr 标记 | 磁盘上（标记 / 临时文件） | 下一次预检 | 报告的结果 | 人工处理 |
|---|---|---|---|---|---|---|---|---|---|
| `PC-P2` | P2 | g0_evidence.json cannot be written (ENOSPC) | 否 | 3 | G0-EVIDENCE-UNSAVED | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-P3` | P3 | read-back bytes differ from the written bytes | 否 | 3 | G0-EVIDENCE-UNVERIFIED | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-P5` | P5 | the judge raises an exception | 否 | 3 | G0-JUDGE-ERROR | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-P6a` | P6 | summary write fails halfway | 否 | 3 | G0-SUMMARY-UNSAVED | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-P6b` | P6 | summary read-back differs | 否 | 3 | G0-SUMMARY-UNSAVED | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-P6c` | P6 | summary fsync fails | 否 | 3 | G0-SUMMARY-UNSAVED | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K1` | K1 | marker serialisation or validation raises (for example an impossible verdict / exit pair) | 否 | 3 | G0-CLOSE-UNPUBLISHED | absent / absent | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K2a` | K2 | g0_closed.json.tmp already exists (EEXIST) | 否 | 3 | G0-CLOSE-UNPUBLISHED | absent / other | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K2b` | K2 | temporary file write fails halfway (ENOSPC) | 否 | 3 | G0-CLOSE-UNPUBLISHED | absent / other | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K2c` | K2 | temporary file fsync fails (EIO) | 否 | 3 | G0-CLOSE-UNPUBLISHED | absent / other | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K3` | K3 | read-back of the temporary file differs | 否 | 3 | G0-CLOSE-UNPUBLISHED | absent / other | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K4a` | K4 | link fails with EEXIST: a foreign file occupies g0_closed.json | 否 | 3 | G0-CLOSE-UNPUBLISHED | schema_invalid / other | BLOCKED：CLOSED_SCHEMA | BLOCKED | 是（H1） |
| `PC-K4b` | K4 | link is not supported (EPERM / ENOTSUP / EXDEV) | 否 | 3 | G0-CLOSE-UNPUBLISHED | absent / other | BLOCKED：NO_CLOSED | BLOCKED | 是（H1） |
| `PC-K5` | K5 | directory fsync fails after link | 是 | 3 | G0-CLOSE-UNCONFIRMED | ok / identical | CLOSED_OK | BLOCKED | 无 |
| `PC-K6` | K6 | read-back of the published name differs | 是 | 3 | G0-CLOSE-UNCONFIRMED | noncanonical / other | BLOCKED：CLOSED_NONCANONICAL | BLOCKED | 是（H1） |
| `PC-K7` | K7 | uncaught exception after K6 verified | 是 | 3 | G0-CLOSE-UNCONFIRMED | ok / identical | CLOSED_OK | BLOCKED | 无 |
| `PC-K7b` | K7 | uncaught exception right after link returned | 是 | 3 | G0-CLOSE-UNCONFIRMED | ok / identical | CLOSED_OK | BLOCKED | 无 |
| `PC-OK` | — | none: all of K1..K7 succeed | 是 | 1 | — | ok / identical | CLOSED_OK | FAIL | 无 |
| `PC-OK2` | — | none | 是 | 0 | — | ok / identical | CLOSED_OK | PASS | 无 |

**崩溃点（`closure.crash_points`，与判据逐项一致）：**

| 崩溃点 | 发生在 | 磁盘事实 | 下一次预检 |
|---|---|---|---|
| `X1` | P6 verified, before K2 creates the temporary file | closed=absent, tmp=absent | NO_CLOSED |
| `X2` | K2 started writing (process killed mid-write) | closed=absent, tmp=other | NO_CLOSED |
| `X3` | K2 fsynced, before K4 | closed=absent, tmp=other | NO_CLOSED |
| `X4` | K4 returned, before K5 (process killed) | closed=ok, tmp=identical | CLOSED_OK |
| `X5` | K5 returned, before K6 (process killed) | closed=ok, tmp=identical | CLOSED_OK |
| `X6` | K6 verified, before the process exits (process killed) | closed=ok, tmp=identical | CLOSED_OK |
| `X7` | K4 returned, then the operating system crashed before the directory entry reached the disk | closed=absent, tmp=other | NO_CLOSED |

## 7. 最小原子排他发布方案的研究（K0–K7）

没有运行任何实验；以下基于 POSIX 语义与 Python 标准库文档的推理。**未在本机文件系统上验证**；硬链接支持和 `fsync` 行为必须在获得实现授权后用表驱动 / 进程级测试验证，且需单独授权。

| 方案 | 结论 | 理由 |
|---|---|---|
| 以最终名 `O_EXCL` 创建，再逐步写入 | **拒绝** | 最终名在写入过程中就可见且内容不全；中途失败与「正在结案」不可区分——正是任务禁止的方式 |
| 写临时文件再 `os.rename` / `os.replace` | **拒绝** | POSIX `rename` 会静默覆盖已存在的目标；先检查再改名有竞争窗口，不满足「不覆盖既有文件」 |
| `renameat2(RENAME_NOREPLACE)` | **不采用** | 原子且排他，但标准库不暴露，需 `ctypes` / 系统调用，增加平台依赖；V5 保持仅标准库 |
| 目录 / 锁文件（`mkdir`、`flock`） | **不采用** | 解决互斥而非「最终名完整出现」，仍需写入内容，不解决问题 |
| **临时文件 `O_EXCL` + fsync + 读回 + `os.link` 到最终名 + 目录 fsync + 读回** | **采用** | `link(2)` 原子且在目标存在时返回 `EEXIST`，最终名一出现就指向已 fsync 且已核对的 inode；标准库、无需特权。代价：临时名作为同一 inode 的第二个名字保留（G0 从不删除），且文件系统须支持硬链接（不支持则 BLOCKED，无回退，见 L-7） |

处理要点：文件同步失败（K2 / K5）、发布后崩溃（X4–X6）、操作系统崩溃（X7）、以及重新预检时的判定，分别见 §6 的案例和崩溃点表；**预检永不补全一次结案**。

## 8. 一致性守卫与变异测试（静态；不是 G0 测试）

* `tools/check_g0_v5_consistency.py`（JSON ↔ 文字；V1–V4 哈希；V4→V5 路径差集 = 声明；C02…C17 与 V4 逐字相同；V4 的决策 / 政策 / 限度 / 前 11 行裁决规则保持；`g0_summary.json` 存在即结案的 V4 说法不残留；`default=str` 只在否定语境出现；`os.rename` / `os.replace` 只在 K4 的否定语境出现；K 步骤的「已发布」标志恰在 K4 翻转；失败表覆盖 K1–K7）。
* `tools/check_g0_v5_closure_cases.py`（用判据中的规则对案例事实求值；规则表自身的合法性：编号连续、原因码唯一、事实与取值存在；23 条规则全部被案例触发；每个案例的预期原因 = 求值结果；V5 不会接受 V4 读法下已被拦下的状态）。
* **变异测试（在临时副本上，故意破坏后检查工具必须报错）：** 一致性检查 7 种（改一条规则的文字、改 C05 文本、重新插入 V4 的「摘要即结案」片段、把「从不结案」改成「有时结案」、允许 `os.rename`、把 K5 的已发布标志改为否、改动 V4 冻结文件一个字节……）全部被发现；案例检查 9 种（改预期原因、改一条规则的条件、删除规则 CL-19、错误的 stderr 标记、错误的退出码、错误的崩溃点结论、事实与文件不一致、把案例 A 改判 CLOSED_OK……）8 种被发现；第 9 种「从案例 A 的文件列表中去掉摘要」未被报错——因为 `closed` 缺失时 `summary` 事实按定义是 `na`，文件列表此时不参与一致性核对，这是设计如此，不是漏检。另有一次我自己写错的变异（破坏了 JSON 语法）作废并重做。
* 这些检查**不检验任何 G0 代码**，也不能证明推导的前提真实（如「链接返回之后最终名才存在」「`fsync` 返回后数据已落盘」）。

## 9. 残余风险与未解决问题

1. **范围外的一处勘误（请审核者裁定）：** V4 的证据模式字段 `evidence_schema` 的说明写着 `-3`，而模式标识 / C16 / 义务写 `-4`。为避免把已知矛盾带入最终规范，V5 把该说明改成 `-4`（V5-CH-6，仅文字，字段 / 类型 / 使用者不变）。这略超出任务限定的四个修改点；若审核者认为不应放在 V5，可只撤销这一项。
2. **审核者原文缺席；** `derived` 的决定（CL-A、CL-B、CL-D、CL-E）需确认：用 `os.link`；已发布但未确认的标记按文件判定为已结案、进程级结果报告 BLOCKED；任何记录的裁决（含 FAIL / BLOCKED）都使运行结案；临时名从不删除。
3. **文件系统必须支持硬链接（L-7）；** 否则运行结束时无法发布标记，运行目录永久阻止后续运行，直到有人处理。V5 不规定运行前的探测（那会在 fork 之前增加文件操作），建议负责人在授权时确认证据根所在文件系统；也可由审核者决定是否要增加探测。
4. **标记不是签名（L-6）；** 有目录写权限者可以伪造一个一致的标记；绑定只能发现不一致与意外损坏。
5. **已保存的摘要 / 标记可能记录 PASS 而该次运行的结果是 BLOCKED**（K5 / K6 / K7 失败时）；报告规则规定看退出码和 `G0-CLOSE-*` 标记，而不是看文件里的裁决。这是有意的取舍（不覆盖已保存文件）。
6. **当前代码不满足 V5：** `g0_run.py` 的预检仍只看摘要是否存在，也没有证据流水线、结案标记；`g0_judge.py` / `g0_auth.py` 仍绑定 V1。46 个既有纯逻辑测试未运行且将随实现改变。实现前不得授权任何 G0 执行。
7. 沿用的限度：L-1、L-3、L-4、L-5、F-1、F-14。

## 10. 下一阶段（须另行授权）

将 V5 冻结文件交给 ChatGPT / Grok 做**一次限定范围的最终审核**；通过后申请 **G0 工具实现授权**（不再扩大规范版本）。实现范围：`gate_g0/g0_run.py`（V4 的流水线 + K0–K7 + 预检规则 CL-01…CL-23 + 事实采集）、`gate_g0/g0_judge.py`（C03 / C07 / C16 与 M-2；C01 的预检原因格式）、`gate_g0/g0_auth.py`（指向 V5）、更新 `tests/test_g0_interlock_and_judge.py`、把本文件的 38 + 19 个案例转成表驱动夹具、`tools/static_audit.py` 与 `audit_g0_pure_tests.py` 的扩展。全部为纯逻辑测试；运行任何测试都需单独授权。
