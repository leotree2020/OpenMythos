# F3-B / D1 — 代码冻结候选勘误 C2（最小门禁修订）

**状态：`D1 CODE FREEZE CANDIDATE C2 / PENDING CHATGPT FINAL CODE REVIEW`**

基准：`3775dc333577094d30297d3e28f9aa8d5d40039c`（C1）。ChatGPT 已静态认可 C1 的四项核心正确性修复；本轮**不**重复审计 Parcae、ACT 或 D1 方案，只做以下三项和一次只读环境盘点。C1 勘误与准备记录原样保留。

边界不变：仅 CPU 合成数据；**没有**下载 WikiText、拟合 Tokenizer、启动真实 D1、训练、使用 GPU、开始 D2/D3；冻结配置里的候选版本**未改动**。D1 仍是 `NOT TESTED / NOT AUTHORIZED`。

## 1. 三项修订：目的、输入、预期、实际、状态

环境：沙箱，Python 3.13.16，`tokenizers 0.23.3`，`pyarrow 26.0.0`，4 CPU，无 GPU，合成数据。全量输出：`gate3_d1/c2_logs/selftest_output.txt`；修订前行为：`gate3_d1/c2_logs/before_c1_code.txt`。

| 项 | 目的 | 输入 | 预期 | 实际（修订后） | 修订前（C1 代码） | 状态 |
|---|---|---|---|---|---|---|
| 1 退出码映射 | 读取器退出码 4（前置条件 BLOCKED）不得被报成 FAIL；5、1、3 及其他为 FAIL；LR 中读取器预期退出码 3，若为 4 则 BLOCKED | `reader_status` 单元用例；用桩读取器（退出码 4/5/1/3）驱动 `clean`、`all`、`negatives` | 4 → `BLOCKED`、驱动器退出码 4、决定文件 `verdict=BLOCKED`；5/1/3 → `FAIL`、退出码 1；clean 非 PASS 时 `negatives_meta` 明确记 `NOT TESTED`；negatives 中读取器 4 → 全部条目 `BLOCKED`、退出码 4 | 与预期一致 | 全部映射为 FAIL（`rc=4` 报 FAIL，退出码 1）；`negatives_meta` 缺失 | PASS（合成） |
| 2 30 分钟硬上限 | 上限为代码常量 1800 s；real 模式禁止 `--timeout-seconds`；配置里的上限不等于 30 分钟时 real 模式也拒绝；selftest 覆盖只能缩短（(0, 1800]） | real 模式 `--timeout-seconds 5`；real 模式配置上限 120 分钟；selftest `5000`/`0`/`-3`/`1500`；既有短超时用例（0.8 s） | 前三类 → 退出码 4，决定文件 `timeout_override_refused`，`steps` 为空，未创建 `clean` 目录；`1500` 被接受并记录 `wallclock_limit_seconds=1500`；0.8 s 超时用例仍 BLOCKED | 与预期一致 | real 模式接受覆盖，继续运行（`AssertionError: 1 != 4`） | PASS（合成） |
| 3 异常结果安全处理 | 验证器异常退出、结果文件缺失/畸形/与退出码不一致，一律在决定文件里记为 FAIL 或 BLOCKED；驱动器自身异常也写决定文件；验证器任何异常路径尽量留下结果文件 | `verifier_verdict` 单元用例（PASS/FAIL/BLOCKED 与文件缺失、畸形 JSON、未知 verdict、退出码与 verdict 不符、-11）；7 种桩验证器行为；真实验证器遇到不存在的源文件、缺失输入、Blocked 清单；`clean` 目录已存在导致驱动器异常；negatives 中读取器桩退出 3 但不写文件 | 退出码 0 但无结果文件 → FAIL；畸形 → FAIL；退出码 0 而 verdict 为 FAIL → FAIL；退出码 1 无文件 → FAIL；退出码 4 无文件 → BLOCKED；退出码 4 而 verdict 为 PASS → FAIL；信号终止 → FAIL；真实验证器异常 → 退出码 1 且留下 `FAIL` 结果文件（Blocked → 退出码 4 且留下 `BLOCKED` 结果文件）；驱动器异常 → 决定文件含 `driver_exception`、退出码 1 | 与预期一致 | 缺结果文件时驱动器抛 `FileNotFoundError` 回溯、无决定文件；验证器异常无结果文件；驱动器异常无决定文件（`KeyError`） | PASS（合成） |

## 2. 汇总结果

| 项目 | 结果 |
|---|---|
| C2 新增测试 | 12 项，全部 OK；在 C1 代码上 11 项失败或出错（唯一通过的是不变的 FAIL 映射） |
| 全量自测 | 49 项 OK（C1 为 37 项），约 71 s，含 `--mode real` 代码路径（合成 Parquet + 手工构造、未训练的字节级 BPE） |
| D1 真实数据实验 | **NOT TESTED / NOT AUTHORIZED** |
| R6 读取前哈希与 validation/test 隔离、R7、T1–T6、数据获取完整性 | **NOT TESTED**（不变） |
| 执行主机上的 Python/库版本 | **NOT VERIFIED**（见第 3 节） |

## 3. 只读环境盘点（`gate3_d1/c2_logs/env_inventory.txt`）

范围仅限本沙箱；项目负责人的计划执行环境（如 Codespaces）从这里无法访问，**NOT VERIFIED**。仓库内没有 devcontainer 定义。冻结配置里的候选版本**未更改**。

| 项 | 本沙箱 | 冻结候选 |
|---|---|---|
| Python 完整版本 | 3.13.16 | 3.13.16 |
| tokenizers | 0.23.3 | 0.23.3 |
| pyarrow | 26.0.0 | 26.0.0 |
| huggingface_hub | 2.2.0（系统）；2.3.0（我建的 scratch venv，仓库外） | 2.2.0（D1 读取器/验证器不使用，仅获取脚本用） |
| `d1_env_manifest.py --mode real` | 无问题 | — |
| Git | HEAD `3775dc33…`，分支 `mini-mythos-p1c-gate22c-readiness`，工作树干净（盘点时 C2 修改尚未提交） | — |

`TOKENIZERS_PARALLELISM`、`PYTHONHASHSEED` 在此沙箱 shell 里未设置（驱动器给子进程显式设置，`d1_env_manifest.py` 只强制检查 `CUDA_VISIBLE_DEVICES`）。

## 4. 仍需关注

1. 执行主机的 Python 完整补丁版本与依赖组合仍需项目负责人确认后重新冻结；本沙箱满足候选固定值只说明自测环境一致。
2. 驱动器对多项条目聚合时保持原优先级（有 BLOCKED 则整体 BLOCKED，否则 FAIL）；请复审是否更希望 FAIL 优先。
3. 未改变的缺口：获取脚本、Tokenizer 拟合与 T1–T6、validation/test 处理、`runtime_manifest.json` 生成者。

## 5. 下一条唯一指令

等待 ChatGPT 对 C2 做最终代码复审，并等项目负责人确认执行主机环境。**未获新的真实数据执行授权之前不得启动 D1，不得开始 D2/D3。**

---

**最终状态：`D1 CODE FREEZE CANDIDATE C2 / PENDING CHATGPT FINAL CODE REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
