# F3B-D1-SPEC-R3-001 — R3 草案检查点

**状态：`DRAFT / PENDING CHATGPT REVIEW`**。不是 FROZEN，不是 PASS，不是执行授权。仅文档；追加式。

| 项 | 内容 |
|---|---|
| 基准 | `97d0faf2982f4122941d2299a23cab6ab2ba04a3`（分支 `d1-final-freeze-sentinel-fix-20261026`；开始时本地与远端一致，工作区干净，冻结清单 10/10 OK） |
| 工作分支 | `d1-pre-real-spec-r3-20261026` |
| 草案 | `docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（192 行） |
| 读取 | v1、R1、R2、Closeout 完整读取；冻结配置与 `D1_ENV_FREEZE.md` 读取相关段落；PRE-REAL-AUDIT-001 报告不在仓库内（只在上一次会话回复里），已对照原文重新核对每条冲突 |
| 没有做 | 没有改动冻结文件（v1/R1/R2、读取器、验证器、驱动器、测试、配置、清单）；没有下载数据、拟合 Tokenizer、访问网络、运行 D1、使用 GPU；没有开始 D2/D3 |

## 一致性核对（本次实际执行）

| 核对 | 预期 | 实际 |
|---|---|---|
| 草案第 1 节引用的原文片段在冻结源文件中逐字存在 | 全部找到 | **24/24** 片段在 v1、R1、`D1_ENV_FREEZE.md`、冻结配置中逐字找到（比较时去掉 Markdown 的 `*` 强调符） |
| v1/R1/R2 SHA-256 | 不变 | `a55b2cb7…`、`f92c4e79…`、`1d4c3629…` 不变 |
| 草案状态词 | 仅 DRAFT / PENDING CHATGPT REVIEW | 开头与结尾状态行均为该状态；未出现 FROZEN 或 PASS 作为 R3 的状态 |
| 待裁决事项标记 | 全部 PROPOSED / NOT APPROVED | 第 2–7 节标题带该标记；第 7 节 11 项决策（R3-D01…R3-D11）逐项列出草案建议与备选 |
| 冲突表 | S1、S2、R6 粒度、R7 Token 计数、中断行为、T1 事件日志、30 分钟预算 | 覆盖，并另发现 S8（离线切换时机）、S9（无 LFS `sha256`）、S10（身份标签可核对性） |
| 对冻结代码的断言（读取器不计算 Parquet 哈希、额外清单键被忽略、trace 的 run 记录含 `manifest_sha256`） | 与源码一致 | 与 `d1_reader.py` 一致（grep 复核） |

## 待项目负责人裁决（均 PROPOSED / NOT APPROVED）

R3-D01 validation/test 的 L1+ 操作时机（S1/S2）；R3-D02 T7 的 val/test 部分后移；R3-D03 R6 的粒度与局限；R3-D04 R7 Token 计数口径；R3-D05 中断行为；R3-D06 无 LFS `sha256` 时的替代标准；R3-D07 30 分钟预算范围；R3-D08 是否在 D1 阶段审计 test；R3-D09 新脚本集的授权与重新冻结流程；R3-D10 授权文件形式；R3-D11 `tokenizer.json` 能否入库（沿用）。

## 下一条唯一研发指令

等待 ChatGPT 复审 R3 草案并由项目负责人逐项裁决。批准前不下载、不拟合、不运行 D1、不使用 GPU、不修改冻结文件、不开始 D2/D3。

---

# F3B-D1-SPEC-R3-REVIEW-002 — R3 草案定向修订检查点（追加）

**状态：`R3 DRAFT / PENDING OWNER DECISION`**。不是 FROZEN，不是 PASS，不是执行授权。仅文档；追加式（以上内容保持原样，作为修订 1 的记录）。

| 项 | 内容 |
|---|---|
| 修订基准 | `94601916bc1fd0faa33b9f819b3a0d8cc7d61dc5`（首版草案提交，仍在 Git 历史中） |
| 分支 | `d1-pre-real-spec-r3-20261026`（普通快进推送） |
| 修改的文件 | `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（原地修订，新增第 11、12 节）；本检查点；`PROJECT_MAP.md`、`SESSION_START_PROTOCOL.md`、`PROJECT_STATUS_20261025.md`（只追加/插入块，零删除） |
| 没有做 | 没有改动 v1/R1/R2、Driver、Reader、Verifier、测试、冻结配置、`D1_CODE_SHA256SUMS`；没有下载 WikiText、拟合 Tokenizer、访问 Hub、运行 D1、训练、使用 GPU |
| 本窗口唯一的环境探测 | 只读：`CLOCK_BOOTTIME`、`CLOCK_MONOTONIC`、`CLOCK_REALTIME` 与 `/proc/sys/kernel/random/boot_id` 在**本沙箱**可读；**目标环境 NOT TESTED** |

## 八项修订（详见草案第 11、12 节；每项含问题 / 原规则 / 修订规则 / 验收条件 / 残余风险 / 状态）

| # | 内容 | 草案位置 | 状态 |
|---|---|---|---|
| 1 | D07：预算账本 + `CLOCK_BOOTTIME` + `boot_id` + 绝对截止时间 + 外层监督器；重启/时钟异常/账本缺失 → `BLOCKED(budget_unprovable)`；`seq` 与 `utc` 不计时 | 11.1、12.1 | PENDING OWNER DECISION（R3-D07） |
| 2 | S6：哈希链只作完整性；关键前缀 K0–K4 外部固定（Git 推送 + 带外副本，可选签名/时间戳）；写明信任边界 | 2.3、11.2、12.2 | PENDING OWNER DECISION（R3-D01、R3-D09） |
| 3 | D03：前后哈希只证明两个检查时刻；加 `ctime_ns`；记录 TOCTOU/ABA 残余风险；C-1…C-4 可选控制 | R6.3、11.3、12.3 | PENDING OWNER DECISION（R3-D03） |
| 4 | I4：受控目录集合（含 Xet 缓存）、局限、措辞「受控范围内未发现」 | I4、11.4、12.4 | PENDING OWNER DECISION（R3-D01） |
| 5 | D06：区分 LFS SHA-256 / Git blob SHA-1 / Xet；算法标签；禁止跨算法比较；元数据不足默认 BLOCKED；**更正首版对 LFS `blob_id` 的错误用法** | 11.5、12.5 | PENDING OWNER DECISION（R3-D06） |
| 6 | D08：test 审计仅限完整性/Token 统计/round-trip；禁止训练、选择、调参、质量评估 | I8、11.6、12.6 | PENDING OWNER DECISION（R3-D08） |
| 7 | A1–A8 引用顺序与前缀哈希：层级表、`P_k` 唯一定义、S3 写入顺序、新增 BP0/PIN0–PIN4 | 第 5 节、2.3、11.7、12.7 | 已自检；ChatGPT 复核 PENDING |
| 8 | 11 项裁决保留为待批准决策记录（新增「状态」「决定人/日期/决定」栏，均未填） | 第 0 节第 6 条、第 7 节、12.8 | PENDING OWNER DECISION（R3-D01…D11） |

## 修订 2 自检（本次实际执行）

| 核对 | 预期 | 实际 |
|---|---|---|
| 第 1 节引用的原文片段逐字存在（去掉 `*` 与空白后比较，源：v1、R1、R2、`D1_ENV_FREEZE.md`、冻结配置） | 全部找到 | **20/20** 片段找到（本次切分方式按「……」拆分；首版检查点的 24 是另一种切分，不是缺失） |
| v1/R1/R2 SHA-256 | 不变 | `a55b2cb7…`、`f92c4e79…`、`1d4c3629…` 不变 |
| 引用图无环（第 5 节层级表转边列表，Kahn 拓扑排序 + 每条边指向严格更低层级） | 无环 | **17 个节点、29 条边（`BP` 的边因无数字未被脚本解析，已人工核对：A8 → BP，层级 12 < 14）；拓扑排序访问 17/17，层级检查通过** |
| 过期表述 | 无 | 「防篡改」「`seq` 时间戳」「`A3[0..seq(…)]`」仅出现在对修订前问题的描述中 |
| 状态词 | `R3 DRAFT / PENDING OWNER DECISION` | 开头与结尾状态行一致；11 项决策状态均为 `PENDING OWNER DECISION`；没有任何一项被标为已批准 |
| 冻结清单与配置 | 不变 | 见提交前复核（`D1_CODE_SHA256SUMS` 10/10、配置状态 `FROZEN` 与哈希 `0d35dc21…`） |

## 仍待裁决（均 PENDING OWNER DECISION）

R3-D01…R3-D11 全部。修订 2 影响的建议内容：D01（缺席见证范围）、D03（R6 局限与可选控制）、D06（完整性基础）、D07（计时方式）、D08（用途限制）、D09（含外部固定方式）。**没有任何一项被批准。**

## 下一条唯一研发指令

等待 ChatGPT 审核 R3 修订稿及项目负责人正式批准。批准前不下载、不拟合、不运行 D1、不使用 GPU、不修改冻结文件、不开始 D2/D3。

---

# F3B-D1-SPEC-R3-REVIEW-003 — R3 第三轮最小修订检查点（追加）

**状态：`R3 DRAFT / PENDING OWNER DECISION`**。不是 FROZEN，不是 PASS，不是 OWNER APPROVED，不是执行授权。仅文档；追加式（以上各节保持原样，作为修订 1、修订 2 的历史记录）。

## 上一轮的审核结论（如实记载）

修订 2（提交 `eeea55269df485d3e6305a82a3c478ef141a2788`）经 ChatGPT Work 独立审核，结论为 **FAIL**；ChatGPT 对 GitHub 上的 R3 原文复核后，提出 FIX-01…FIX-08 八项问题（预算与终止协议未闭合、远端 pin 的验证只看引用、K3 与最终读后哈希的先后不明、摘要标签与冻结接口冲突、事件名未统一、I4 措辞、test 输出白名单与 `usage_declaration` 矛盾、依赖图统计）。修订 2 的检查点里写的「引用图 17 个节点、29 条边」**不准确**：当时的解析方式只识别带数字的节点名，漏掉了 `PIN4 → BP` 与 `A8 → BP` 两条边（正确的 `ref` 边数是 31）。上方修订 2 的原记录**保留不改**，此处追加更正。

| 项 | 内容 |
|---|---|
| 修订基准 | `eeea55269df485d3e6305a82a3c478ef141a2788`（分支 `d1-pre-real-spec-r3-20261026`，开始时本地与远端一致，工作区干净，冻结清单 10/10 OK） |
| 修改的文件 | `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（原地修订：新增 2.4 事件注册表、第 5 节正式边列表、11.1/11.2/11.4/11.6/11.7 重写、11.8 新增、第 14 节修订 3 记录）；本检查点；`PROJECT_MAP.md`、`SESSION_START_PROTOCOL.md`、`PROJECT_STATUS_20261025.md`（只追加/插入块，零删除） |
| 没有做 | 没有改动 v1/R1/R2、Driver、Reader、Verifier、测试、冻结配置、`D1_CODE_SHA256SUMS`、原始历史证据；没有下载 WikiText、拟合 Tokenizer、访问 Hub、运行 D1、训练、使用 GPU、启动 D2/D3；没有运行任何 Schema 或实现测试（只做文档自检脚本，脚本在会话的临时目录，未入库） |

## 验收表：FIX-01…FIX-08

「状态」是**文档自检**的结论（文档内部无矛盾、规则可执行、残余风险明确）；相应机制的**实现与运行效果**均为 `NOT TESTED`（相关脚本尚未编写）。

| ID | 审核输入 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| FIX-01 | §11.1、R3-D07 | 状态转换、监督器、子进程组终止与回收、SIGTERM/SIGKILL 时间计入、`close` 的时机与失败处理、预算包含的收尾活动、K4 与 30 分钟预算无循环 | 11.1(b) 状态转换表；(c) 监督器不变量（同一 `boot_id` / 账本、`start_new_session`、子收割者）；(d) 终止协议 T1–T7；(e) `close` 前提与写失败处理；(f) 选项 X / 选项 Y 各给出可实施顺序（X：K3/K4 在 `close` 后、受 `W` 约束；Y：固定在预算内、K4' 不含 `close`）；(h) 全部不可证明情形均为 BLOCKED。自检脚本验证：规范顺序中的账本事件走完 `NEW→OPEN→STAGE→…→CLOSED→DONE` 合法路径，且所有账本事件均已登记。不修改冻结 Driver 的超时机制 | **PASS（文档自检）**；实现与运行 NOT TESTED |
| FIX-02 | §11.2 | 获取远端实际提交对象并读取 `pin_Kn.json` 内容；核对 SHA-256、规范序列化、前缀哈希、`line_count`、`run_id`、`name`、祖先关系；明确 BLOCKED / FAIL；保留带外副本；K1 之后才允许 S4 | 11.2 的 RV 程序步骤 1–10 与负例表（含「`ls-remote` 提交 SHA 一致而内容不同 → FAIL」）；门禁 `G_S4` 要求 K0、K1 在 S4 内重新 RV；2.4 登记 `pin_remote_verified`、`gate_check`；自检脚本验证规范顺序中 `pin_remote_verified`(K1) → `gate_check`(G_S4) → `online_switch` → 首个 validation `download_start`，且 `tokenizer_hash_logged` 更早 | **PASS（文档自检）**；RV 实现 NOT TESTED；GitHub 分支保护 NOT VERIFIED |
| FIX-03 | §4.1、§5、§11.2、§11.3 | 最终读后哈希与闸门结论进入被固定的 K3 前缀；先收集子进程状态再算哈希；K3 最后固定 | K3 终点改为 `read_phase_closed`；新增 `children_reaped`、`gate_result`、`read_phase_closed`；顺序 `driver_exit → children_reaped → manifest_written(A7) → post_read_snapshot → gate_result×3 → read_phase_closed → pin_pushed(K3)`；新增 R6.6 与 `R6_POST_NOT_PINNED`；同步 2.4、第 5 节、11.2、11.3、R6.1/R6.2；TOCTOU/ABA 说明保留。自检脚本验证上述先后与「紧邻」关系，并核对工件落在的前缀 | **PASS（文档自检）** |
| FIX-04 | §5、§11.5、Manifest Schema | 新证据可带标签，冻结键保持裸格式；新模块负责解析；不得写入带前缀的冻结键；非法标签、跨算法、格式错误、摘要不符的预期；Schema 对照表 | 新增 11.8：格式定义、Schema 对照表（`parquet_sha256`、`tokenizer_sha256`、`actual_vocab_size`、`formal.*`、冻结输出文件、新证据各一行）、解析与比较规则、预期结果表；11.5 规则 1 改为指向 11.8；已用 grep 核对冻结代码的正则（`d1_reader.py` 27–28 行 `HEX64/HEX40`；`d1_driver.py` 31 行 `H64`；`d1_verifier.py` 29–30 行 `H64/H40`）及 `identity()` 对 `formal` 键的要求（`d1_driver.py` 45–54 行）与对照表一致。未修改任何冻结代码 | **PASS（文档自检）**；摘要模块与生成器 NOT TESTED（未编写） |
| FIX-05 | §2.3、§4、§5、§11.1–11.2 | 唯一事件注册表；全部事件名已声明；无同名异义；顺序可满足 | 新增 2.4：事件日志 28 个事件、预算账本 10 个事件；列出阶段、必填字段、重复、前置、后置、所属前缀、异常状态；附工件写入点表与规范顺序。自检脚本结果：规范顺序中使用的事件全部已登记；已登记但不在规范顺序里的只有条件事件（`interrupted`；账本的 `terminate_begin`、`terminate_signal`、`reap_done`、`anomaly`、`pin_phase`）；全文反引号标识符经人工复核，没有未登记的事件名；工件落入的前缀（A1、A2、PIN0 → LP1；A4、PIN1 → LP2；A5、A6、A7、PIN2 → LP3；A8、PIN3、PIN4 → 无）与第 5 节的 `rec` 边逐条一致 | **PASS（文档自检）** |
| FIX-06 | §2、I4、§11.4、验收矩阵 | 统一表述；不声称零访问；区分观测事实 / 记录器承诺 / 静态检查 / 残余风险；PASS 仅限受控检查 | 统一为「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象」；§2.1、I4、I5、R6.4、T1、11.4 同步；11.4 分层表四层；PASS 定义；验收模板检查「证明从未访问」类措辞。全文检索无肯定性的零访问主张（仅有否定句与负例） | **PASS（文档自检）** |
| FIX-07 | I6、R7.6、§11.6 | 统一 Schema；`usage_declaration` 属 Envelope；statistics 内不得有文本 / Token ID / 逐行 / 评估指标；规范文本及哈希核对；缺 / 多 / 错 / 嵌套的处理；正负例 | 11.6：`d1_heldout_audit_v1` 的键集合表；禁止项；草案 `usage_declaration` 规范 JSON 与其对象摘要（`sha256:72e378a7…f310`，**草案值，非批准值**）；核对方式（批准前一律 BLOCKED `USAGE_DECLARATION_UNAPPROVED`）；10 行预期结果表；1 个正例与 7 个负例（仅示意，未运行）；I6、R7.6 同步；用途限制始终生效 | **PASS（文档自检）**；Schema 校验器 NOT TESTED |
| FIX-08 | §5、§11.7、§12.7、检查点 | 从正式边列表重新构图；17 节点与全部边；拓扑排序与层级递减；核对 BP、BP0、PIN0–PIN4；保留 29 边的历史记录并追加更正；差异则 FAIL | 见下节：节点 17；`ref` 31 条（与 Work 复核一致）；`rec` 9 条；`sub` 3 条；三类合并 43 条，均无环、层级严格递减；人读表格与正式边列表一致 | **PASS（文档自检）** |

额外检查：

| 检查 | 预期 | 实际 | 状态 |
|---|---|---|---|
| Git 变更仅文档 | 仅 5 个 `.md` | 见提交的文件清单 | PASS |
| 冻结清单 | `D1_CODE_SHA256SUMS` 10/10 OK | 10/10 OK；配置 `status = FROZEN`，SHA-256 前 16 位 `0d35dc21a4beca7c` | PASS |
| v1/R1/R2 | SHA-256 不变 | `a55b2cb7…`、`f92c4e79…`、`1d4c3629…` 不变 | PASS |
| R3-D01…D11 | 无擅自批准 | 11 行全部为 `PENDING OWNER DECISION`，决定栏均为空；`APPROVED` 仅出现在否定/说明性文字里 | PASS |
| 第 1 节原文引文 | 逐字存在 | 20/20 片段找到（去掉 `*` 与空白后比较） | PASS |
| 依赖图 | 17 节点、`ref` 31 边、无环 | 17 / 31 / 无环（见下） | PASS |
| 事件注册表与条款一致 | 无未声明事件、无不可满足的顺序 | 见 FIX-05 | PASS |
| 新旧摘要格式不破坏冻结接口 | 冻结键裸格式、不改冻结代码 | 见 FIX-04 | PASS |
| 空白 | `git diff --check` 无输出 | 无输出 | PASS |

综合结论：**`R3 REVISION-003 DOCUMENT SELF-CHECK PASS`**。这只表示文档自检通过；**不是** R3 FROZEN，**不是** REAL D1 PASS，**不是** R3 OWNER APPROVED。

## FIX-08 证据：依赖图（由脚本从第 5 节正式边列表重新构造）

方法：解析第 5 节代码块中的 `node` / `ref` / `rec` / `sub` 行（节点名按空白分隔的任意记号解析，不依赖带数字的正则）；(1) Kahn 拓扑排序访问数 = 节点数；(2) 每条边的目标层级严格小于起点层级；(3) 与人读表格交叉核对（层级一致；表格里「→」右侧的集合等于 `ref` 边集合）；(4) 由 2.4 规范顺序推出的各前缀内的 `manifest_written` / `pin_pushed` 集合，等于 `rec` 边集合。结果：节点 17；`ref` 31；`rec` 9；`sub` 3；合并 43；全部通过，无重复边。

**节点（17）：** A1(层级 0)、BP0(层级 0)、PIN0(层级 1)、A2(层级 1)、LP1(层级 2)、PIN1(层级 3)、A4(层级 4)、LP2(层级 5)、PIN2(层级 6)、A5(层级 7)、A6(层级 8)、A7(层级 9)、LP3(层级 10)、PIN3(层级 11)、BP(层级 12)、PIN4(层级 13)、A8(层级 14)

**`ref` 边（31）：**

1. PIN0 → BP0
2. A2 → A1
3. PIN1 → LP1
4. A4 → A1
5. A4 → A2
6. A4 → LP1
7. A4 → PIN1
8. PIN2 → LP2
9. A5 → A1
10. A5 → A4
11. A5 → LP2
12. A5 → PIN2
13. A6 → A2
14. A6 → A4
15. A6 → A5
16. A7 → A6
17. PIN3 → LP3
18. PIN4 → BP
19. A8 → A1
20. A8 → A2
21. A8 → A4
22. A8 → A5
23. A8 → A6
24. A8 → A7
25. A8 → LP3
26. A8 → BP
27. A8 → PIN0
28. A8 → PIN1
29. A8 → PIN2
30. A8 → PIN3
31. A8 → PIN4

**`rec` 边（9）：** LP1 → A1；LP1 → A2；LP1 → PIN0；LP2 → A4；LP2 → PIN1；LP3 → A5；LP3 → A6；LP3 → A7；LP3 → PIN2

**`sub` 边（3）：** LP2 → LP1；LP3 → LP2；BP → BP0

**对修订 2 记录的更正：** 修订 2 的解析只识别带数字的节点名，因此把 `BP` 当成不存在，漏计 `PIN4 → BP`（上表第 18 条）与 `A8 → BP`（第 26 条），得到 29 条。上面的 31 条是重新计数的结果，**不是**照抄 Work 的数字；计数与 Work 一致。

## 仍待裁决（均 PENDING OWNER DECISION）

R3-D01…R3-D11 全部。修订 3 影响的建议内容：D03（K3 终点与 R6.6）、D07（终止协议；收尾方案二选一：选项 X / 选项 Y；参数 τ、`G_term`、`G_kill`、`W`）、D08（统一 Schema）、D09（RV、摘要模块与冻结接口边界、事件注册表）。**没有任何一项被批准。**

## 未解决的残余风险

- 账本、事件日志与固定记录的信任域局限（同用户可改写、记录器之外的操作、固定点之后的窗口）；远端引用不是不可伪造证明；带外核对依赖人工；GitHub 分支保护 NOT VERIFIED。
- `CLOCK_BOOTTIME`、`PR_SET_CHILD_SUBREAPER`、`/proc` 扫描、`chattr +i`、inotify 在目标环境 NOT TESTED。
- Hub 元数据字段语义、Xet 后端是否返回 `lfs.sha256` NOT VERIFIED。
- Driver 前后哈希仍只证明两个检查时刻（TOCTOU/ABA）。
- 全部新脚本（记录器、预算账本与监督器、获取、拟合、审计、清单生成、摘要模块、验收、固定与 RV 工具）尚未编写；真实 D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED；Grok 交叉复审仍 PENDING。

## 下一条唯一研发指令

等待 ChatGPT 对第三轮 R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。批准前不下载、不拟合、不运行 D1、不使用 GPU、不修改冻结文件、不开始 D2/D3。
