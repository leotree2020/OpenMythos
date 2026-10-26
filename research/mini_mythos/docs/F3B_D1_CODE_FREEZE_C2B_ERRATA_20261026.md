# F3-B / D1 — 代码冻结候选 C2b（两个遗漏边界问题）

**状态：`D1 CODE FREEZE CANDIDATE C2b / PENDING CHATGPT FINAL ACCEPTANCE`**

基准：`796cc6138caaedf8a45d9abd12554ef62235e77d`（C2a）。只修两个边界问题；不重新设计或重构 D1。只改 `gate3_d1/d1_driver.py` 与 `tests/test_d1_selftest.py`（外加代码哈希清单、本文档、日志与索引检查点）。`d1_reader.py`、`d1_verifier.py`、`D1_FROZEN_CONFIG.json`、历史 v1/R1/R2/C1/C2/C2a 文档**未改**；CR1/CR2/CR3 的注入行为与验收规则未改。C2a 勘误关于聚合的说明继续有效，本文件补足 CR 内部的同一规则。

环境（全部测试相同）：沙箱，Python 3.13.16，`tokenizers 0.23.3`，`pyarrow 26.0.0`，4 CPU，无 GPU，合成数据；基准 Git `796cc613…`，工作树含 C2b 修改。仅 CPU 合成测试。

## Fix 1：CR 内部 FAIL > BLOCKED > PASS

- **Purpose**：每个 CR 负例有两个读取器（故障、对照）。原逻辑只要有一个 BLOCKED 就把整项记为 BLOCKED，掩盖了另一个读取器的 FAIL。
- **修改**：新增 `cr_reader_verdict(rc_fault, rc_control)`，用既有 `aggregate()` 合并两个读取器状态；结果条目新增 `readers`，分别保留故障/对照读取器的退出码与状态。
- **Input**：单元：(4,1)(1,4)(4,4)(0,4)(4,0)(5,0)(0,5)(0,0)(3,0)(0,3)；驱动器：桩读取器让 CR1=(故障 4, 对照 1)、CR2=(故障 1, 对照 4)、CR3=(4,4)，LR 读取器退出 3。
- **Expected**：CR1 FAIL，CR2 FAIL，CR3 BLOCKED；`readers` 明细逐一保留；整体 FAIL（退出码 1）；单元表：(4,1)(1,4)(5,0)(0,5)(3,0)(0,3)=FAIL，(4,4)(0,4)(4,0)=BLOCKED，(0,0)=PASS。
- **Actual（C2b）**：与预期一致。**Actual（C2a 基准）**：CR1、CR2 被记为 BLOCKED（`('BLOCKED','BLOCKED','BLOCKED') != ('FAIL','FAIL','BLOCKED')`）；`cr_reader_verdict` 不存在。
- **Verdict**：PASS（合成）。

## Fix 2：非字符串 verdict

- **Purpose**：`verifier_verdict()` 在做 `verdict in VERDICT_EXIT` 之前必须确认是字符串；列表、字典是不可哈希的，原先会抛 `TypeError`。
- **修改**：`isinstance(verdict, str)` 检查；`aggregate()` 同样加了字符串检查，避免不可哈希成员抛错（同一文件内的一行加固）。
- **Input**：结果文件 `{"verdict":[]}`、`{"verdict":{}}`、`{"verdict":null}`、`{"verdict":123}`、`{"verdict":true}`，退出码 0/1/4；驱动器层用桩验证器写这些文件并退出 0；保持不变的行为：4+文件缺失、4+合法 BLOCKED、4+畸形/未知 verdict、0+合法 PASS、1+合法 FAIL、4+合法 PASS（不一致）；`aggregate(["PASS", []])`、`aggregate([{}])`。
- **Expected**：五种输入全部 FAIL 且不抛异常（驱动器层 `read_resume=FAIL`、退出码 1、决定文件没有 `driver_exception`）；4+缺失 → BLOCKED；4+合法 BLOCKED → BLOCKED；4+畸形/未知 → FAIL；0+合法 PASS → PASS；不一致 → FAIL；`aggregate` 对不可哈希成员返回 FAIL。
- **Actual（C2b）**：与预期一致。**Actual（C2a 基准）**：`TypeError: unhashable type: 'list'`；驱动器层对应测试在基准上出错（具体错误行未捕获进日志）。
- **Verdict**：PASS（合成）。

## 全量合成回归

| 项目 | 结果 |
|---|---|
| C2b 新增测试 4 项（含 3 项最小回归 + 驱动器层 1 项） | C2a 基准上全部失败/出错（`gate3_d1/c2b_logs/before_c2a_code.txt`），C2b 上全部通过 |
| 全量 D1 合成回归 | 56 项 OK（C2a 为 52 项），约 87 s，含 `--mode real` 代码路径（`gate3_d1/c2b_logs/selftest_output.txt`） |
| 真实数据 D1、R6 读取前部分、R7、T1–T6、数据获取完整性 | **NOT TESTED** |
| 执行主机 Python 完整版本与依赖组合 | **BLOCKED（独立项目，NOT VERIFIED）**；候选版本未改 |

## 完整性检查

- `d1_reader.py`、`d1_verifier.py`、`D1_FROZEN_CONFIG.json` 的 SHA-256 与 C2a 一致；
- v1 `a55b2cb7…`、R1 `f92c4e79…`、R2 `1d4c3629…` 未变，C1/C2/C2a 勘误文档未改；
- 三个索引文件只追加；`D1_CODE_SHA256SUMS` 已重新生成并核对；
- 未触碰 Parcae/AxoNN；无二进制产物。

## 剩余项与下一步

- 剩余 NOT TESTED：真实数据 D1、R6 读取前哈希与 validation/test 隔离、R7、T1–T6、数据获取完整性；获取脚本、Tokenizer 拟合脚本、`runtime_manifest.json` 生成者尚未编写。
- 剩余 BLOCKED：执行主机 Python 完整补丁版本与依赖组合，待项目负责人确认。
- 下一条唯一指令：等待 ChatGPT 最终验收 C2b，并等项目负责人确认执行主机环境；未获新的真实数据执行授权前不得启动 D1，不得开始 D2/D3。

**最终状态：`D1 CODE FREEZE CANDIDATE C2b / PENDING CHATGPT FINAL ACCEPTANCE`。** 未宣布 D1 PASS 或 CLOSED。
