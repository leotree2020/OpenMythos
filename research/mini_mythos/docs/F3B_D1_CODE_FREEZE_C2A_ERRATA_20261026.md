# F3-B / D1 — 代码冻结候选微型勘误 C2a

**状态：`D1 CODE FREEZE CANDIDATE C2a / PENDING CHATGPT FINAL CODE REVIEW`**

基准：`f28f32b6d1514f15ccf680f752f5c414322cab51`（C2）。只做两项；不扩大审计范围。读取器、冻结配置、历史设计文档及既有正确性检查未改（`d1_reader.py`、`D1_FROZEN_CONFIG.json`、`d1_verifier.py` 相对 C2 无 diff）。边界不变：仅 CPU 合成数据，未下载 WikiText、未拟合 Tokenizer、未启动真实 D1、未训练、无 GPU、未开始 D2/D3。D1 `NOT TESTED / NOT AUTHORIZED`。C2 勘误第 4 节第 2 点（聚合 BLOCKED 优先）被本文件取代。

| 项 | 目的 | 输入 | 预期 | 实际（C2a） | C2 代码上 | 状态 |
|---|---|---|---|---|---|---|
| 1 `verifier_verdict()` | 区分「结果文件不存在」与「存在但不可解析」。退出码 4 **且文件不存在**才 BLOCKED；畸形 JSON、空文件、`[]`、未知 verdict、缺 `verdict` 键、退出码与 verdict 不符、路径是目录，均为 FAIL | 单元：退出码 4 配 6 种不可用文件内容 + 目录 + 缺失文件 + 合法 BLOCKED 记录；驱动器：桩验证器退出 4 并写畸形/空/未知 verdict 文件，及退出 4 并写合法 BLOCKED 记录 | 不可用文件 → FAIL（驱动器退出码 1）；缺失文件 → BLOCKED；合法 BLOCKED 记录 → BLOCKED（退出码 4）；其余映射不变 | 与预期一致 | 退出码 4 + 畸形文件被记为 BLOCKED（`'BLOCKED' != 'FAIL'`，驱动器 `(4,'BLOCKED') != (1,'FAIL')`） | PASS（合成） |
| 2 聚合 FAIL 优先 | 新增 `aggregate()`：FAIL > BLOCKED > PASS；空列表与未知值按 FAIL；每项状态与原因保留，`negatives_meta` 新增 `counts` 与 `aggregation` 说明 | 单元：9 种组合；驱动器：LR1 读取器退出 4（BLOCKED），其余读取器退出 3 且无证据（真实验证器 FAIL） | 整体 FAIL、驱动器退出码 1；`items.LR1=BLOCKED` 仍可见；`counts={PASS:0,FAIL:11,BLOCKED:1}`；全 BLOCKED 仍为 BLOCKED（退出码 4，沿用 C2 用例） | 与预期一致 | 整体 BLOCKED、退出码 4（`(4,'BLOCKED','BLOCKED') != (1,'FAIL','FAIL')`）；`aggregate` 不存在 | PASS（合成） |

## 测试汇总

环境：沙箱，Python 3.13.16，`tokenizers 0.23.3`，`pyarrow 26.0.0`，4 CPU，无 GPU，合成数据。

| 项目 | 结果 |
|---|---|
| C2a 相关 4 项测试（`test_verifier_verdict_mapping` 扩充、`test_exit4_with_unparseable_result_is_fail_through_the_driver`、`test_aggregate_precedence`、`test_mixed_negative_results_report_fail_and_keep_item_detail`） | 在 C2 代码上全部失败/出错（`gate3_d1/c2a_logs/before_c2_code.txt`），在 C2a 上全部通过 |
| 全量自测 | 52 项 OK（C2 为 49 项），约 81 s（`gate3_d1/c2a_logs/selftest_output.txt`） |
| 真实数据 D1 / R6 读取前部分 / R7 / T1–T6 / 数据获取完整性 | **NOT TESTED** |
| 执行主机 Python 与库版本 | **NOT VERIFIED**（候选值未改） |

下一条唯一指令：等待 ChatGPT 最终代码复审与项目负责人确认执行主机环境；未获新的真实数据执行授权前不得启动 D1，不得开始 D2/D3。

**最终状态：`D1 CODE FREEZE CANDIDATE C2a / PENDING CHATGPT FINAL CODE REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
