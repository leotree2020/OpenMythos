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
