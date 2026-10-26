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
