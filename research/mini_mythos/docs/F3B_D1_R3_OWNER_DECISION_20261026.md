# F3B-D1-R3-OWNER-DECISION-001 — R3 项目负责人决策记录

**状态：`OWNER DECISION RECORD — R3-D01…D11 — OWNER APPROVED — 2026-10-26（Asia/Tokyo）`**

这份记录只登记**负责人对 R3 规范的决策**。它**不是**真实 D1 的运行授权，**不是** R3 FROZEN，**不是** REAL D1 PASS，也不是任何新脚本、数据下载、Tokenizer 拟合、训练或 GPU 的授权。

## 1. 授权依据

- **批准人：** 项目负责人。**批准日期：** 2026-10-26（Asia/Tokyo）。
- **批准内容（逐字，来自本次执行令 F3B-D1-R3-OWNER-DECISION-001 §1）：** 「项目负责人已在当前 ChatGPT 对话中明确批准：批准 R3-D01～D11 按 ChatGPT 推荐方案执行，D07 选择 X，参数按建议作为初始验收值。」
- **本记录的来源与局限：** 该批准由本次执行令转述给 Claude Code。**本记录不含**负责人的签名、聊天链接或其他身份信息——执行令没有提供这些，**这里不伪造**。批准的约束力来自上面这句话以及随后第 4 节中执行令逐项给出的方案（执行令 §3）；如两者在细节上不一致，以执行令 §3 的逐项文字为准。
- **「ChatGPT 推荐方案」的解释：** 指 R3 草案 FINAL-005 版（见第 3 节）第 7 节决策表中的「草案建议」栏，经第 4 节的逐项文字确认或具体化。

## 2. 本次授权的范围

**允许：** 建立本决策记录；编制已批准的 R3 规范候选版本；执行只读的文档一致性核对；更新项目检查点与索引；普通提交并推送文档。

**不允许（仍需各自独立授权）：** 开发任何新脚本；下载真实数据（含 WikiText）；联网访问 Hub 元数据以外的任何数据接口；拟合正式 Tokenizer；运行 D1；训练模型；使用 GPU；启动 D2/D3；**运行第一个合成 CPU 实验**（它也必须单独取得执行授权）；把 R3 标记为 FROZEN（须先经 ChatGPT 独立核对本记录与候选规范）；把 Grok 交叉复审标记为 PASS（仍 DEFERRED / PENDING）。

适用范围：仅限真实 D1 的**执行前规范**（R3），不延伸到 D2/D3。

## 3. 被批准版本的绑定

| 项 | 内容 |
|---|---|
| 仓库 / 起始分支 | `leotree2020/OpenMythos` / `d1-pre-real-spec-r3-20261026` |
| 基准提交 | `4c1d29d9e01c6df2d3b5e796181f728cc3cb88ed` |
| 被批准决策所依据的 R3 原文 | `research/mini_mythos/docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（FINAL-005 版，保持原样，不被覆盖） |
| 该文件的 SHA-256 | `d52856713e1dd0d53855597bedc8f3f7eec9dfeec8aece24cdafef839054bbef` |
| ChatGPT 独立审核结论 | `R3 DOCUMENT REVIEW PASS / READY FOR OWNER DECISION`（这不是 R3 FROZEN，也不是 REAL D1 PASS） |
| 冻结输入（未改动） | v1 `a55b2cb7a9e04d3b38dd4657b08bc90c478ef31204b5435e8916e3bbb362ba9e`；R1 `f92c4e792dcb83108ac9c00a11d60fe5cb2111c1ed146f8f3b67842a943a1d7a`；R2 `1d4c36298c05eb6676049013b76fed88284ec378aa61383e2f415f6b7f8f05d9`；`D1_FROZEN_CONFIG.json` `0d35dc21a4beca7c2f93fc11df6806ea7bc321d2376f52e1552863f19e7d7aaa`（`status = FROZEN`）；`D1_CODE_SHA256SUMS` `f4105ec350e47f3a4ce65a8b2e3a8db50a8c71a8ece44c7810685814b6f4f78c`（10 项全部 OK） |

**哈希引用方向（避免循环）：** 本记录引用上表的**更早存在**的文件摘要，**不包含**自身的摘要，也**不包含**候选规范的摘要。候选规范按**路径**引用本记录，不含本记录的摘要。本记录与候选规范各自的 SHA-256 登记在独立的检查点 `F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md` 里；检查点不被它们引用。依赖方向：草案 ← 本记录；草案 ← 候选规范（路径引用本记录）；本记录、候选规范 ← 检查点。

## 4. 逐项决策

每一项的状态均为：**`OWNER APPROVED — 2026-10-26`**。草案编号指 R3 草案 FINAL-005 版的章节。

| ID | 已批准方案 | 对应条款 | 适用范围与限制 | 未被选定的备选（保留为历史，**不得执行**） | 状态 |
|---|---|---|---|---|---|
| R3-D01 | 严格分阶段获取。Tokenizer 固定（`tokenizer_hash_logged`）之前，validation/test 仅允许 L0 元数据操作，**禁止 L1 及以上**。缺席见证按 11.4：只能表述为「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象」，接受「不能证明从未访问」的局限。 | 2.1、2.2、I1、I4、11.4 | 适用于真实 D1 的获取与拟合脚本 | 选项 B（允许 L1、L2） | OWNER APPROVED — 2026-10-26 |
| R3-D02 | T7 对 validation/test 的扫描在 Tokenizer 固定之后进行（取代 R1 §8「先检查三个 split」）；train 部分仍在拟合之前。 | 4.3 T7 | 同上 | 保留 R1 原文 | OWNER APPROVED — 2026-10-26 |
| R3-D03 | 对**整个** Driver 运行做前后各一次文件哈希加 `stat`（含 `ctime_ns`）检查；明示只证明两个检查时刻一致；最终读后快照与闸门结论先于 K3 写入；**明确接受 TOCTOU / ABA 残余风险**。C-1（私有只读副本）、C-3（inotify 监视）只是**可选加强，不视为已授权实施**——采用必须另行授权。 | R6.1–R6.6、11.3 | 冻结 Driver 之外实施 | 每个子进程前后各一次（需改冻结 Driver）；C-2 `chattr +i`；C-4 | OWNER APPROVED — 2026-10-26 |
| R3-D04 | 记录原始编码 Token 数（`tokens_encode_only`）与包含 EOS 前缀的流 Token 数（`tokens_total`），并核对恒等式（差等于该 split 的 EOS 前缀个数）。 | R7.4 | validation/test 审计 | 只选其一 | OWNER APPROVED — 2026-10-26 |
| R3-D05 | 中断时 `BLOCKED`；不自动恢复、不重试；新运行必须使用新的运行目录与新的事件日志；R7.7 正常路径写 `NOT_APPLICABLE`（不是 PASS）；中断与其他失败统一走 `run_aborted` 终点与 11.9 的收尾顺序，监督器不写 PASS。 | R7.7、2.4、11.9 | 同上 | 允许在阶段边界续跑 | OWNER APPROVED — 2026-10-26 |
| R3-D06 | **目前仅批准 B-LFS 完整性基础**（SHA-256 内容摘要与 Hub 的 LFS `sha256` 比较，同时核对大小）。B-GIT、B-XET 在元数据语义未经受控验证之前**不得启用**；元数据不足一律 `BLOCKED`；摘要带算法标签、禁止跨算法比较。 | 11.5、11.8 | 三个 split 必须都具备 B-LFS 基础，否则整体 BLOCKED。Hub 元数据字段语义 **NOT VERIFIED**；做仅 L0 的元数据验证任务需单独授权 | 立即接受 B-GIT | OWNER APPROVED — 2026-10-26 |
| R3-D07 | **选择方案 X。** 详见第 5 节。 | 11.1、11.9 | 同上 | 选项 Y、选项 Z、`CLOCK_MONOTONIC` | OWNER APPROVED — 2026-10-26 |
| R3-D08 | D1 阶段对 test（及 validation）**仅允许**文件完整性、行数、合格行数、一级标题行数、Token 统计、round-trip、特殊字符串计数的审计；**不得用于**训练、模型选择、超参数调整、早停、检查点选择或模型质量评估。输出遵循统一 Schema `d1_heldout_audit_v1`（`usage_declaration` 在 Envelope，`statistics` 严格限定）。用途限制始终生效。 | I6、I8、R7.6、11.6 | 同上 | 推迟 test 审计到 D3 | OWNER APPROVED — 2026-10-26 |
| R3-D09 | 新脚本按**最小任务**独立开发、独立 CPU 验收，**全部完成后整体重新冻结**；**不得修改现有冻结代码**。外部固定默认：Git 普通推送 + 远端内容验证 RV + 审核者带外副本。事件注册表（2.4）与摘要格式边界（11.8）作为这些脚本的共同规格。 | 2.4、11.2、11.8 | 本记录**不授权**开发任何脚本；每个任务需单独授权 | 分批冻结；签名提交 / 外部时间戳 | OWNER APPROVED — 2026-10-26 |
| R3-D10 | 授权记录保存在 Git 仓库，并以 SHA-256 绑定被批准的版本与后续每次实验授权（`authorization_ref` 指向仓库里已提交的授权记录文件，并记录其 SHA-256）。**不伪造**负责人签名、聊天链接或未经提供的身份信息。 | 第 6 节 | 同上 | 由负责人另定 | OWNER APPROVED — 2026-10-26 |
| R3-D11 | 正式 `tokenizer.json` **不提交**公开仓库；仅提交其哈希、统计及允许公开的非敏感证据。 | v1 §3.5、§11 | 同上 | — | OWNER APPROVED — 2026-10-26 |

## 5. R3-D07 的唯一执行方案：X

不保留 X / Y 二选一。选项 Y 的失败路径变换、`pin_phase`、`close.pins_*` 字段以及选项 Z 不属于已批准的执行条款（它们保留在 R3 草案 FINAL-005 版里作为历史）。

- **预算：** 主预算 **30 分钟**，区间为账本 `open` 行到 `close` 行（`CLOCK_BOOTTIME`，`close.bt_ns − open.bt_ns ≤ budget_ns`）。`seq` 与 `utc` 不参与耗时数值。
- **K3、K4 的固定在 `close` 之后：** 预算**包含** S0–S5 的全部活动、K0 / K1 / K2 的推送与远端验证、SIGTERM / SIGKILL 与回收、最终残留检查、`close` 的写入；预算**不包含** K3 / K4 的推送与验证（阶段 `W`）、S6 验收、人工复核。
- **执行顺序（成功路径）：** `read_phase_closed` → 阶段末尾的回收与残留检查 → `stage_end(S5)` → `close` → K3 推送与 RV → K4 推送与 RV → `wrapup_end` → S6。失败路径的终点是 `run_aborted`，其余相同（11.9）。
- **初始参数（作为初始验收值）：**

| 参数 | 初始值 | 含义 |
|---|---|---|
| `budget_ns` | 30 分钟 | 主预算（数值沿用冻结配置，不改动） |
| τ | **5 s** | 相邻账本行 `|Δwall − Δbt|` 的容差，超过 → `anomaly` |
| `G_term` | **10 s** | SIGTERM 之后等待自行退出的时间 |
| `G_kill` | **5 s** | SIGKILL 之后等待回收的时间 |
| `W` | **600 s** | 收尾阶段上限：`wrapup_end.bt_ns − close.bt_ns ≤ W` |

- **参数的性质与变更规则：** 这些值是**初始验收值**，其在目标环境里是否适用需要 CPU 测试；**调整必须保留审批与变更记录**：每次调整新建一份带日期的记录文件（文件名形如 `F3B_D1_R3_PARAMETER_CHANGE_<日期>.md`），写明旧值、新值、理由、支持的 CPU 测试证据与负责人批准，并以 SHA-256 绑定；**不就地改写本记录**。未经这样的记录，任何脚本不得使用不同的值。

## 6. R3-D08 用途声明的批准文本

按「推荐方案」，已批准的 `usage_declaration` 为 R3 草案 11.6 中的草案文本，其规范 JSON 为：

`{"prohibited":["training","model_selection","hyperparameter_tuning","early_stopping","checkpoint_selection","quality_evaluation","threshold_setting","tokenizer_refit_or_adjustment","design_change_from_audit_results","reporting_as_model_metric"],"purpose":"integrity_and_tokenizer_statistics_only"}`

其**对象摘要**（规范 JSON 的 UTF-8 字节，不加换行）为 `sha256:72e378a7b8b0d4a4066e429ef994bd6850fe0ba7788103fc81aa5e83bd85f310`。验收脚本以此值作为已批准摘要。

> **待核对事项：** 执行令只写了「按 ChatGPT 推荐方案」，没有另行提供用途声明的文本；这里取草案文本作为批准文本。请 ChatGPT 在独立核对时（以及负责人在需要时）确认这一取值；若负责人另有文本，须新建一份带日期的变更记录并更新摘要，不得就地改写。

## 7. 本记录登记的未授权事项与未解决项

- 新脚本（记录器、预算账本与监督器、获取、拟合、审计、清单生成、摘要模块、验收（含 `--postmortem`）、固定与 RV 工具）：**全部未编写**；每个任务需单独授权，独立 CPU 验收，最后整体重新冻结。
- 真实 D1、真实数据下载、正式 Tokenizer 拟合、训练、GPU、D2/D3：**NOT TESTED / NOT AUTHORIZED**。
- 第一个合成 CPU 实验：需**单独**取得执行授权。
- R3 FROZEN：须待 ChatGPT 独立核对正式候选规范与本记录之后，由后续指令决定。
- Grok 交叉复审：DEFERRED / PENDING，**不是 PASS**。
- 未验证事项（原样保留）：Hub 元数据字段语义与 Xet 行为；`CLOCK_BOOTTIME`、`PR_SET_CHILD_SUBREAPER`、`PR_SET_PDEATHSIG`、`/proc` 扫描、`waitpid` 状态区分在目标环境；GitHub 分支保护。
- 一个必须提前知道的后果：D06 只批准 B-LFS。若真实 Hub 元数据不返回 `lfs.sha256`（或语义不符），S1 将按规范 `BLOCKED`，需要先做单独授权的仅 L0 元数据验证任务。
