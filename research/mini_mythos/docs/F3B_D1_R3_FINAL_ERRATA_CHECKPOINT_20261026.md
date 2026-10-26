# F3B-D1-R3-FINAL-ERRATA-001 — R3 已批准候选规范最终勘误：检查点

**状态：`R3 APPROVED CANDIDATE / ERRATA SELF-CHECK PASS / PENDING CHATGPT FINAL VERIFICATION`**。候选规范的文件内状态仍是 `OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION`。**不是 R3 FROZEN，不是 REAL D1 PASS，不是任何运行授权。**仅文档；本检查点是独立文件，不被被登记的文件引用（没有哈希引用循环）。

## 1. 登记

| 项 | 内容 |
|---|---|
| 仓库 / 分支 | `leotree2020/OpenMythos` / `d1-r3-approved-candidate-20261026` |
| 源基准（勘误前） | `21fb57331866b6b0b1db7b24b5e416a68f20f84c` |
| 勘误后候选规范 | `research/mini_mythos/docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md`，SHA-256 **`cddb9bb2b97b7fe652781c35350f1aece8d4d58605dde25c906fa67b234fd7d4`**（**当前有效**） |
| 勘误前候选规范 | 同一路径，SHA-256 `2aaea7d3ed32585c02ee0adc9daaed1e8d09913e2006d47871eb45bd6bb5fc2a`（被本版取代；仍可在提交 `21fb57331866b6b0b1db7b24b5e416a68f20f84c` 中取得，登记在 `F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md`） |
| 负责人决策记录 | `F3B_D1_R3_OWNER_DECISION_20261026.md`，SHA-256 `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319`——**字节不变**（与勘误前一致） |
| R3 草案 FINAL-005 | `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`，SHA-256 `d52856713e1dd0d53855597bedc8f3f7eec9dfeec8aece24cdafef839054bbef`——**字节不变** |
| 批准日期 | 2026-10-26（Asia/Tokyo）；R3-D01…D11 `OWNER APPROVED — 2026-10-26`；本勘误不改变任何已批准的决策或参数 |
| Git 提交 | 与本检查点同一提交（SHA 见汇报）；候选规范的 SHA-256 可由 `git show <提交>:<路径> \| sha256sum` 复算 |

**哈希引用方向：** 本检查点 → 候选规范（摘要）、决策记录（摘要）、草案（摘要）；候选规范 → 检查点（仅路径）；没有任何文件包含自己的摘要。

## 2. 勘误内容

| ID | 位置 | 问题 | 最小修订 | 正常 / 异常路径预期 | 状态 | 残余风险 |
|---|---|---|---|---|---|---|
| ERRATA-01 | 候选规范 §11.1(d) 时间消耗说明；同步 §2.4(b)（`terminate_begin`、`driver_exit`）、§11.1 测试、§11.9(a) | 旧句「由于已发生 `terminate_begin`，结果必为 `BLOCKED(budget_exceeded)`」与 §11.1(e)、§11.9 矛盾（interrupt 与 supervisor_abort 并不必然超出预算） | 删去旧句；新增「终止原因与预算结果对照」表：正常结束；`deadline` → `EXCEEDED` / `BLOCKED(budget_exceeded)`；`interrupt` → 预算结果按总耗时与有效性，**可以是 `WITHIN_BUDGET`**，最终 `BLOCKED(interrupted)`；`supervisor_abort` → 预算结果独立判定，最终按 `run_aborted.cause`；回收未确认或预算不可证明 → `UNPROVABLE`（最高优先级），`BLOCKED(budget_unprovable)`，绝不 PASS。`driver_exit` 行区分 `terminated_by`=budget / interrupt；§11.9(a) 映射规则追加终止原因条目；新增测试 (h5)(h6)(h7) | 四种终止情形（正常、interrupt、deadline、supervisor_abort）各有预期；`UNPROVABLE` 优先于 `EXCEEDED` | 文档自检 PASS；实现 NOT TESTED | 预算结果与最终状态分开判定后，报告需同时呈现两者，实现若只写其一会误导 |
| ERRATA-02 | 候选规范 §2.4(b)（`reap_done` 行）、§11.1(d)（T7 与新 Schema 表）、预算负例 (m)(m1)–(m8)、§11.9 F2 表 | `t_kill_bt_ns` 在只发 SIGTERM 时没有合法表示；`kill_overhead_ns` 只说「单独报告」，没有存放位置、类型、公式与核对 | 不新增事件、不改冻结代码、不改参数：`reap_done` 增加必需整数字段 `kill_overhead_ns = t_reaped_bt_ns − terminate_begin.bt_ns`；`t_kill_bt_ns` 为整数（实际发送 SIGKILL，等于 KILL 行的 `bt_ns` 且 ≥ `t_term_bt_ns` + `G_term`）或 **JSON `null`**（未发送 SIGKILL；不得省略、不得写 0、不得复制其他时间点）；`t_term_bt_ns` 等于 TERM 行的 `bt_ns`；`t_reaped_bt_ns` ≤ 本行 `bt_ns`；验收核对六条；缺字段 / 类型错 / 负值 / 时间逆序 → BLOCKED `budget_unprovable`（`REAP_RECORD_INVALID`）；伪造 SIGKILL 时间、与 KILL 行不符、公式不符、KILL 早于宽限、无 KILL 却超宽限、未确认而无 KILL → FAIL `REAP_RECORD_FORGED` | 只发 SIGTERM：`t_kill_bt_ns`=`null` 通过；发了 SIGKILL：时间等于 KILL 行通过；上列异常各有预期状态 | 文档自检 PASS；实现 NOT TESTED | `G_term + 1 s` 的容差依赖监督器的 1 s 轮询粒度；目标环境 NOT TESTED |

## 3. 验收：实际检查结果

| 检查 | 实际 | 状态 |
|---|---|---|
| D01～D11 的批准内容一致 | 决策记录字节不变；候选规范第 7 节 11 行与决策记录逐项一致，状态均为 `OWNER APPROVED — 2026-10-26`（脚本核对 ID、顺序与状态） | PASS |
| D07 仍然只有方案 X | 候选规范 §11.1(f) 仅方案 X；`pin_phase`、选项 Y / Z / B 只在「未选定」说明中被提及；τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s 未变 | PASS |
| 四种终止情形 | 正常、`interrupt`、`deadline`、`supervisor_abort` 的预算结果、运行状态与最终状态由对照表给出，并用小脚本按 §11.1(e) 的取值规则与对照表交叉核对 7 个组合（含 `UNPROVABLE` 优先、interrupt 可 `WITHIN_BUDGET`），全部一致 | PASS |
| `reap_done` 规则的可满足性 | 小脚本按 §11.1(d) 的规则实现一个验证函数，对 15 个合成记录（含 m 系列全部情形）逐一核对，预期状态全部相符 | PASS |
| 序列与状态机 | 成功路径及 F1a / F1b / F1c / F2 / F3a / F3b 在注册表下全部通过；3 个负例被拒绝；事件日志 29 个、账本 9 个事件，无新增 | PASS |
| 旧断言清理 | 检索「必然 BLOCKED / 结果必为 / 必为 `BLOCKED` / 由于已发生」及旧的 (m) / F2 行，候选规范中无残留 | PASS |
| 17 节点、43 边、无环 | 从候选规范第 5 节正式边列表重新构图：17 节点；`ref` 31 / `rec` 9 / `sub` 3，共 43 边；无重复、无环、层级严格递减；勘误只增加整数 / `null` 字段，不引入工件依赖 | PASS |
| 冻结清单 | `D1_CODE_SHA256SUMS` 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN`（`0d35dc21…`）；v1 `a55b2cb7…`、R1 `f92c4e79…`、R2 `1d4c3629…` 不变 | PASS |
| Git 范围 | 仅 1 个候选规范修改 + 1 个新检查点 + 3 个索引追加；无非 `.md`；`git diff --check` 无输出；决策记录与草案字节不变 | PASS |
| 第 1 节引文 | 20/20 逐字存在 | PASS |
| 新候选 SHA-256 | 已重新计算并登记于第 1 节；提交后以 `git show` 复算比对（见汇报） | PASS（提交后复核） |
| 执行状态 | 全部新机制保持 NOT TESTED；目标环境相关系统调用 NOT TESTED；Hub 元数据语义 NOT VERIFIED | PASS |

## 4. 仍待核对 / 残余风险

- 沿用决策记录第 6 节的待核对事项：D08 用途声明文本取自推荐方案的草案文本，请 ChatGPT 复核时确认。
- 沿用：D06 只批准 B-LFS 可能使 S1 BLOCKED；τ / `G_term` / `G_kill` / `W` 是初始验收值，需 CPU 测试；同一信任域的局限、远端引用不是不可伪造证明、GitHub 分支保护 NOT VERIFIED、目标环境系统调用 NOT TESTED、Driver 前后哈希只证明两个检查时刻。
- 新脚本（记录器、监督器、账本、获取、拟合、审计、清单、摘要模块、验收、固定与 RV 工具）全部未编写；真实 D1、数据下载、正式 Tokenizer 拟合、训练、GPU、D2/D3 NOT TESTED / NOT AUTHORIZED；Grok 交叉复审 DEFERRED / PENDING，不是 PASS。

## 5. 下一条唯一研发指令

等待 ChatGPT 复核这两处勘误，复核通过后进入 R3 规范正式冻结。真实 D1、正式 Tokenizer 拟合与新脚本开发仍需独立授权。
