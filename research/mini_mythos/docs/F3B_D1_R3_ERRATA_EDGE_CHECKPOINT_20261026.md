# F3B-D1-R3-ERRATA-EDGE-002 — R3 已批准候选规范边界勘误：检查点

**状态：`R3 APPROVED CANDIDATE / EDGE ERRATA SELF-CHECK / PENDING CHATGPT FINAL VERIFICATION`**。候选规范的文件内状态仍是 `OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION`。**不是 R3 FROZEN，不是 REAL D1 PASS，不是任何运行授权。**仅文档；本检查点是独立文件，不被被登记的文件引用（没有哈希引用循环）。

## 1. 登记

| 项 | 内容 |
|---|---|
| 仓库 / 分支 | `leotree2020/OpenMythos` / `d1-r3-approved-candidate-20261026` |
| 源基准（本轮勘误前） | `cd0285fb22ab7e66dc3979face9f5f095ed077b9` |
| 勘误后候选规范 | `research/mini_mythos/docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md`，SHA-256 **`66a656145fc203c71b233ac872eb2eb4c24476717f95f57c1e67a5c112e242c5`**（**当前有效**） |
| 被取代的候选规范版本 | ERRATA-001 版 `cddb9bb2b97b7fe652781c35350f1aece8d4d58605dde25c906fa67b234fd7d4`（提交 `cd0285fb22ab7e66dc3979face9f5f095ed077b9`）；批准时的版本 `2aaea7d3ed32585c02ee0adc9daaed1e8d09913e2006d47871eb45bd6bb5fc2a`（提交 `21fb57331866b6b0b1db7b24b5e416a68f20f84c`） |
| 负责人决策记录 | `F3B_D1_R3_OWNER_DECISION_20261026.md`，SHA-256 `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319`——**字节不变** |
| R3 草案 FINAL-005 | `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`，SHA-256 `d52856713e1dd0d53855597bedc8f3f7eec9dfeec8aece24cdafef839054bbef`——**字节不变** |
| 历史检查点 | 前几份检查点（含 `F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md`、`F3B_D1_R3_FINAL_ERRATA_CHECKPOINT_20261026.md`）**未被修改** |
| 批准日期 | 2026-10-26（Asia/Tokyo）；R3-D01…D11 `OWNER APPROVED — 2026-10-26`；本勘误不改变任何已批准的决策或参数 |
| Git 提交 | 与本检查点同一提交（SHA 见汇报）；候选规范的 SHA-256 可由 `git show <提交>:<路径> \| sha256sum` 复算 |

**哈希引用方向：** 本检查点 → 候选规范、决策记录、草案（摘要）；候选规范 → 检查点（仅路径）；没有任何文件包含自己的摘要。

## 2. 三个边界规则

状态为文档自检结论；相关机制的实现与运行效果均为 `NOT TESTED`。**没有新增事件**；只在既有的 `terminate_signal` 行上增加字段 `result`、`errno`，在 `reap_done` 行上增加字段 `t_gone_bt_ns`。已批准的 `G_term`=10 s、`G_kill`=5 s、τ、`W` 未改。

| ID | 位置 | 问题 | 最小修订 | 正常 / 异常路径预期 | 状态 | 残余风险 |
|---|---|---|---|---|---|---|
| EDGE-01 | §11.1(d) T2–T7、§2.4(b)、`t_kill_bt_ns` 规则 | 旧规则要求 KILL 时刻 ≥ `t_term + G_term`，又要求无 KILL 时 `t_reaped − t_term ≤ G_term + 1 s`；监督器「提前确认全部退出」就不发 KILL，与「等满宽限」不能同时满足；信号发送失败没有表示 | 定义**存活目标判定 A**；T3：每个轮询周期先检查 A，**A 为假 → 记 `t_gone_bt_ns`、提前确认、不发 SIGKILL**；A 为真且 `now − t_term ≥ G_term` → 升级；TERM 未送达（`result`=`error`）可立即升级。T4：KILL **尝试**时刻（成功或失败）= `t_kill_bt_ns`，失败记真实 `errno`；`G_kill` 内仍未观察到 A 为假 → `t_gone`=`null`、`confirmed`=false。`confirmed` ⇔（`t_gone` 非 `null` 且 `residual` 为空）。`terminate_signal` 增加 `result`（sent / gone / error）与 `errno` | 提前确认 → 无 KILL，`t_kill`=`null`；宽限用尽 → KILL，时刻 ≥ `t_term + G_term`；TERM `gone`（进程组已不存在）→ 无 KILL；TERM `error` → 可立即 KILL；KILL `error` → 记真实错误，`confirmed`=false，BLOCKED | 文档自检 PASS；实现 NOT TESTED | 监督器 1 s 轮询粒度造成的 +1 s 容差；目标环境 `killpg` / `waitpid` 行为 NOT TESTED |
| EDGE-02 | §11.1(d) 的 Schema 与验收核对、预算测试 (m)–(m9)、§11.9(d) | 无 KILL 时用 `t_reaped − t_term ≤ G_term + 1 s` 判定，会把「SIGTERM 已让目标全部退出、之后回收很慢」的真实记录判成伪造 | 升级条件只看对 A 的观察（`t_gone`），**回收耗时不参与**：T5 写明回收快慢与是否升级无关。三类判定互不混用：① 记录无效 → BLOCKED `REAP_RECORD_INVALID`；② 记录内部矛盾（时间点、公式、行内容对不上）→ FAIL `REAP_RECORD_FORGED`；③ 记录真实自洽但协议未遵守或无法确认 → BLOCKED（`TERMINATION_NOT_ESCALATED` / `TERMINATION_PROTOCOL_VIOLATION` / `TERMINATION_UNCONFIRMED` / `KILL_ATTEMPT_FAILED`），不是 FORGED，绝不 PASS。给出 8 个文档例子 E1–E8（含 PASS / FAIL / BLOCKED）并规定判定顺序 | E1（提前确认、回收慢）PASS；E2（宽限后 KILL）PASS；E3（宽限用尽未升级）BLOCKED；E4（KILL 失败，真实 errno）BLOCKED；E5 / E7（矛盾）FAIL；E6（提前 KILL）BLOCKED；E8（记录无效）BLOCKED | 文档自检 PASS；验收脚本 NOT TESTED | 例子里的秒数只是示意；规则里的 +1 s 容差若与实现的轮询粒度不符需另行调整并走变更记录 |
| EDGE-03 | §11.1(d) 对照表最后一行及其后规则、§11.1(e)、§11.9(a) 映射规则、测试 (h6)(h8)、§11.9(d) | 对照表末行把预算 `UNPROVABLE` 写成最终 `BLOCKED(budget_unprovable)` 且「优先级最高」，会覆盖另一个已证实的 `FAIL`，与「`FAIL` 高于 `BLOCKED`」矛盾 | `close.result` 只表示预算结果，其优先级只在预算结果内部起作用；`UNPROVABLE` 不覆盖已证实的实验 `FAIL`（「已证实」= 该 `FAIL` 的证据本身通过有效性核对）；最终状态按 `FAIL` > `BLOCKED`、同级取最早发生者、预算类原因内部 `budget_unprovable` 优先于 `budget_exceeded`；所有原因保留；只要预算无法证明，整体验收都不能通过。负例：数据完整性 `FAIL` + 账本 `UNPROVABLE` 的三个维度输出：预算结果 `UNPROVABLE`；运行状态 `ABORTED`；最终 `FAIL(INTEGRITY_MISMATCH)`（原因列表含 `BLOCKED budget_unprovable`），`NOT_ACCEPTED`；只写 `BLOCKED(budget_unprovable)` → 验收 FAIL `STATUS_DOWNGRADED` | 无冲突时各维度独立；有 FAIL 时 FAIL 为主代码 | 文档自检 PASS；实现 NOT TESTED | 报告需同时呈现三个维度与全部原因，实现若只写其一会误导 |

## 3. 验收：实际检查结果

| 检查 | 实际 | 状态 |
|---|---|---|
| D01～D11 的批准内容一致 | 决策记录字节不变；候选规范第 7 节 11 行与决策记录逐项一致（状态均为 `OWNER APPROVED — 2026-10-26`） | PASS |
| D07 仍只有方案 X，参数不变 | 候选规范 §11.1(f) 仅方案 X；τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s 未变；`pin_phase` 与选项 Y / Z / B 只在「未选定」说明中出现 | PASS |
| 终止规则的可满足性（对文档规则的分析，不是仓库测试） | 按 §11.1(d) 实现一个三类判定（无效 / 矛盾 / 协议或不可确认）的验证函数，对 19 个合成记录（E1–E8 及其变体、TERM `gone` / `error`、`errno` 配对）逐一核对，状态与代码全部与文档表一致；其中 E1、E2、m8、m9 为 PASS，E3 / E4 / E6 / 提前 KILL 为 BLOCKED，E5 / E7 为 FAIL，E8 为 BLOCKED（无效） | PASS |
| 优先级规则 | 对 4 个原因组合（完整性 FAIL + 预算 UNPROVABLE、顺序互换、interrupt + UNPROVABLE、EXCEEDED + UNPROVABLE）核对最终主代码，全部与 §11.1(d) 规则一致 | PASS |
| 终止情形 | 正常、`interrupt`、`deadline`、`supervisor_abort` 的预算结果 / 运行状态 / 最终状态表保持（ERRATA-001 通过的内容未重写），对照表末行已按 EDGE-03 修正 | PASS |
| 序列与状态机 | 成功路径与 F1a / F1b / F1c / F2 / F3a / F3b 在注册表下通过；3 个负例被拒绝；事件日志 29 个、账本 9 个事件，无新增事件 | PASS |
| 17 节点、43 边、无环 | 从候选规范第 5 节正式边列表重新构图：17 节点；`ref` 31 / `rec` 9 / `sub` 3，共 43 边；无重复、无环、层级严格递减；勘误只增加字段，不引入工件依赖 | PASS |
| 冻结清单 | `D1_CODE_SHA256SUMS` 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN`（`0d35dc21…`）；v1 `a55b2cb7…`、R1 `f92c4e79…`、R2 `1d4c3629…` 不变 | PASS |
| Git 范围 | 仅候选规范 1 个文件修改、本检查点 1 个新增、3 个索引追加；无非 `.md`；`git diff --check` 无输出；决策记录、草案与此前各检查点字节不变 | PASS |
| 第 1 节引文 | 20/20 逐字存在 | PASS |
| 新候选 SHA-256 | 已重新计算并登记于第 1 节；提交后以 `git show` 复算比对（见汇报） | PASS（提交后复核） |
| 执行状态 | 全部新机制保持 NOT TESTED；目标环境系统调用 NOT TESTED；Hub 元数据语义 NOT VERIFIED | PASS |

## 4. 仍待核对 / 残余风险

- 沿用：D08 用途声明文本取自推荐方案的草案文本，请 ChatGPT 复核时确认；D06 只批准 B-LFS 可能使 S1 BLOCKED；τ / `G_term` / `G_kill` / `W` 是初始验收值，需 CPU 测试；同一信任域的局限、远端引用不是不可伪造证明、GitHub 分支保护 NOT VERIFIED、目标环境系统调用 NOT TESTED、Driver 前后哈希只证明两个检查时刻。
- 本轮新增：`G_term + 1 s` 容差依赖监督器的 1 s 轮询粒度；`t_gone_bt_ns` 是监督器的观察时刻，不是进程真实退出时刻（观察延迟至多一个轮询周期）。
- 新脚本全部未编写；真实 D1、数据下载、正式 Tokenizer 拟合、训练、GPU、D2/D3 NOT TESTED / NOT AUTHORIZED；Grok 交叉复审 DEFERRED / PENDING，不是 PASS。

## 5. 下一条唯一研发指令

等待 ChatGPT 对上述边界勘误作最终确认，再执行 R3 正式冻结。真实 D1、正式 Tokenizer 拟合与新脚本开发仍需独立授权。
