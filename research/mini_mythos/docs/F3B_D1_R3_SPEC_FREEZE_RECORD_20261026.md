# F3B-D1-R3-SPEC-FREEZE-001 — R3 正式规范冻结记录

**正式状态：`R3 SPEC FROZEN / IMPLEMENTATION NOT TESTED / REAL D1 NOT AUTHORIZED`**

本记录**只冻结规范文档的字节版本**。它不冻结任何尚未存在的新脚本，不授权任何实验，不授权真实 D1。本记录自身以 Git 提交为准；它引用的两份冻结文件**不得再编辑、重新格式化或改写**。

## 1. 冻结对象（字节版本）

| 对象 | 路径 | SHA-256（完整） |
|---|---|---|
| R3 规范（已批准候选版，边界勘误后） | `research/mini_mythos/docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md` | `66a656145fc203c71b233ac872eb2eb4c24476717f95f57c1e67a5c112e242c5` |
| 项目负责人决策记录（R3-D01…D11） | `research/mini_mythos/docs/F3B_D1_R3_OWNER_DECISION_20261026.md` | `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319` |

这两份文件在本次冻结所依据的 Git 基准提交里的字节与上表完全一致（冻结前后逐一复算）。**冻结的含义：**上表的字节版本自本记录的提交起正式生效；此后任何字节变化都意味着它不再是本次冻结的 R3，须按第 6 节走变更流程。

## 2. 冻结依据

| 项 | 内容 |
|---|---|
| 仓库 / 基准分支 | `leotree2020/OpenMythos` / `d1-r3-approved-candidate-20261026` |
| Git 基准提交 | `79273d127548e2462026c2ae000dc2499798f5bd` |
| 冻结指令 | F3B-D1-R3-SPEC-FREEZE-001，日期 2026-10-26（Asia/Tokyo） |
| ChatGPT 独立审核结论（经冻结指令转述） | `R3 DOCUMENT ACCEPTANCE PASS / READY FOR SPEC FREEZE` |
| 负责人批准 | R3-D01…D11 `OWNER APPROVED — 2026-10-26`（见决策记录；本次冻结**没有**新增或改变任何决策） |
| 授权范围 | 仅规范冻结记录、检查点与项目索引 |

**历史（保留，不改写）：** R3 草案 FINAL-005 版 `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（SHA-256 `d52856713e1dd0d53855597bedc8f3f7eec9dfeec8aece24cdafef839054bbef`）及此前各轮的失败与修订记录、各检查点原样保留。候选规范此前的字节版本（批准时 `2aaea7d3…`、ERRATA-001 版 `cddb9bb2…`）已被本次冻结的版本取代，仍可在 Git 历史中取得。

## 3. 冻结的内容（摘要；以冻结文件为准）

- **R3-D01…D11 已批准：** D01 严格分阶段获取（Tokenizer 固定前 validation/test 仅 L0）；D02 T7 的 validation/test 扫描在 Tokenizer 固定之后；D03 Driver 整体前后哈希加 `stat`，接受 TOCTOU/ABA 残余风险，C-1 / C-3 为可选加强且**不视为已授权实施**；D04 两种 Token 计数口径加恒等式；D05 中断 BLOCKED、不自动恢复、新运行新目录、R7.7 正常路径 `NOT_APPLICABLE`；D06 仅 B-LFS；D07 方案 X；D08 仅完整性与统计审计；D09 新脚本最小任务独立开发、独立 CPU 验收、整体重新冻结；D10 授权记录在 Git 并以 SHA-256 绑定；D11 正式 `tokenizer.json` 不提交公开仓库。
- **D07 唯一执行方案是 X：** 主预算 30 分钟（账本 `open` 到 `close`）；K3 / K4 在 `close` 之后远端固定；初始验收值 τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s；参数适用性需 CPU 测试，调整须有审批与变更记录。选项 Y、选项 Z、选项 B 不属于执行条款。
- **D08 用途声明摘要：** `usage_declaration` 的对象摘要 `sha256:72e378a7b8b0d4a4066e429ef994bd6850fe0ba7788103fc81aa5e83bd85f310`（规范 JSON：`{"prohibited":["training","model_selection","hyperparameter_tuning","early_stopping","checkpoint_selection","quality_evaluation","threshold_setting","tokenizer_refit_or_adjustment","design_change_from_audit_results","reporting_as_model_metric"],"purpose":"integrity_and_tokenizer_statistics_only"}`）。**待核对事项沿用：**该文本取自推荐方案的草案文本，决策记录第 6 节已登记，供 ChatGPT 与负责人核对。
- **终止与预算规则（已通过 ERRATA-001 / EDGE-002）：** 终止原因与预算结果分开判定；`reap_done` 的终止时间字段 Schema 与三类判定（记录无效 BLOCKED、内部矛盾 FAIL、协议未遵守或无法确认 BLOCKED）；预算 `UNPROVABLE` 不覆盖已证实的实验 `FAIL`，所有原因保留，预算无法证明则整体验收不能通过。

## 4. 验收结果（冻结前的实际核对）

| 检查 | 实际 | 状态 |
|---|---|---|
| 冻结对象 SHA-256 | 两份文件与第 1 节的值完全一致 | PASS |
| 17 节点、43 边依赖图 | 从规范第 5 节正式边列表重新构图：17 节点；`ref` 31 / `rec` 9 / `sub` 3，共 43 边；无重复、无环、层级严格递减 | PASS |
| 负责人决策一致 | 规范第 7 节 11 行与决策记录逐项一致，状态均为 `OWNER APPROVED — 2026-10-26`；D07 仅方案 X，参数一致 | PASS |
| 序列与状态机 | 成功路径与 F1a / F1b / F1c / F2 / F3a / F3b 通过注册表校验；负例被拒绝 | PASS |
| 终止与优先级规则的可满足性 | 按文档规则实现的验证函数对合成记录与优先级组合的核对全部一致（分析，不是仓库测试） | PASS |
| 冻结清单与上游 | `D1_CODE_SHA256SUMS` 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN`（SHA-256 `0d35dc21a4beca7c2f93fc11df6806ea7bc321d2376f52e1552863f19e7d7aaa`，清单 SHA-256 `f4105ec350e47f3a4ce65a8b2e3a8db50a8c71a8ece44c7810685814b6f4f78c`） | PASS |
| v1 / R1 / R2 | v1 `a55b2cb7a9e04d3b38dd4657b08bc90c478ef31204b5435e8916e3bbb362ba9e`；R1 `f92c4e792dcb83108ac9c00a11d60fe5cb2111c1ed146f8f3b67842a943a1d7a`；R2 `1d4c36298c05eb6676049013b76fed88284ec378aa61383e2f415f6b7f8f05d9`——不变 | PASS |
| Git 范围 | 相对 D1 冻结 Closeout 基准 `97d0faf2982f4122941d2299a23cab6ab2ba04a3`，没有任何非 `.md` 文件变化；冻结代码、配置、测试未变 | PASS |
| 研发实验 | 没有执行任何研发实验；没有下载数据、拟合 Tokenizer、运行 D1、使用 GPU，没有修改上游 Parcae | PASS |

## 5. 状态声明

| 项 | 状态 |
|---|---|
| R3 规范 | **SPEC FROZEN**（仅限第 1 节两份文件的字节版本） |
| 实现（记录器、监督器、预算账本、获取、拟合、审计、清单生成、摘要模块、验收含 `--postmortem`、固定与 RV 工具等全部新机制） | **未编写；NOT TESTED** |
| 真实 D1、真实数据下载、正式 Tokenizer 拟合 | **NOT AUTHORIZED** |
| 第一个合成 CPU 实验 | 需**单独**取得执行授权 |
| 训练、GPU、D2/D3 | NOT TESTED / NOT AUTHORIZED |
| Grok 交叉复审 | **DEFERRED**（不是 PASS） |

## 6. 冻结后的变更规则

本次**只冻结规范文档**，不冻结尚未存在的新脚本（它们按 R3-D09 逐个开发、逐个 CPU 验收，全部完成后整体重新冻结）。

任何**改变 R3 已批准行为**的后续修改，必须依次：
1. 记录变更原因；
2. 形成**独立的修订文件**（不得就地改写冻结版本）；
3. 执行必要的 CPU 受控实验；
4. 由 ChatGPT 独立审核；
5. 涉及负责人决策的变更，**重新取得负责人批准**；
6. 产生新的规范版本、新的 SHA-256 与新的检查点。

不得偷偷修改本次冻结版本。参数（τ、`G_term`、`G_kill`、`W`）的调整另按决策记录第 5 节的变更记录规则执行。

## 7. 后续 CPU 测试门禁（全部 NOT TESTED）

下列是实现阶段必须通过的受控 CPU 测试门禁。**它们不因规范冻结而自动判 PASS**；每一项在被单独授权并实际执行之前，状态都是 NOT TESTED。

| # | 门禁 | 状态 |
|---|---|---|
| G1 | `waitpid(WNOHANG)` 与「存活目标 A」的正确协调（A 的三个条件：直接子进程未回收、`killpg(pgid, 0)` 仍成功、有被重新挂靠的后代） | NOT TESTED |
| G2 | 进程已退出但尚未被回收时，**不得**错误认定仍需 SIGKILL | NOT TESTED |
| G3 | SIGTERM 使目标提前退出、且回收较慢的情形（提前确认、无 KILL、`t_kill_bt_ns`=`null`、回收慢不判伪造） | NOT TESTED |
| G4 | TERM / KILL 返回 `ESRCH`、`EPERM` 等异常时，`terminate_signal` 的 `result` / `errno` 与 `reap_done` 的如实记录 | NOT TESTED |
| G5 | 子进程、进程组、被重新挂靠后代的生命周期（含 `PR_SET_CHILD_SUBREAPER`、`PR_SET_PDEATHSIG`、`/proc` 扫描在目标环境的行为） | NOT TESTED |
| G6 | 预算 `UNPROVABLE` 与数据完整性 `FAIL` 并存时的状态优先级（最终 `FAIL`、原因保留、整体 `NOT_ACCEPTED`、`STATUS_DOWNGRADED` 检出） | NOT TESTED |

此外沿用的 NOT TESTED / NOT VERIFIED：Hub 元数据字段语义与 Xet 行为；`CLOCK_BOOTTIME` 等系统调用在目标环境的行为；GitHub 分支保护；`G_term + 1 s` 容差对监督器 1 s 轮询粒度的依赖；τ / `G_term` / `G_kill` / `W` 的目标环境适用性。

## 8. 下一条唯一研发指令

等待单独授权后，启动第一个合成数据 CPU 正确性实验。**本冻结记录不授权该实验**；在取得该授权之前，不下载 WikiText，不拟合正式 Tokenizer，不运行真实 D1，不修改上游 Parcae，不使用 GPU，不启动 D2/D3。
