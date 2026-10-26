# gate3_d1 — D1 读取器 / 独立验证器 / 受控负例（冻结候选）

**状态：`FROZEN CANDIDATE / PENDING CHATGPT CODE REVIEW`。** 没有对真实数据运行；D1 `NOT TESTED / NOT AUTHORIZED`。设计依据：`../docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL{,_R1,_R2}.md`（R2 > R1 > v1）。

| 文件 | 作用 |
|---|---|
| `D1_FROZEN_CONFIG.json` | 机器可读的冻结参数（数据身份、窗口、游标检查顺序、调度、负例表、序列化、环境） |
| `d1_reader.py` | 读取器：9 步游标加载检查、读取循环、游标保存/恢复、trace、注入（仅 CR 用，读取循环内） |
| `d1_verifier.py` | 独立验证器：自己重建参照流/来源映射/9 步检查，不信任 trace 内任何自述 |
| `d1_driver.py` | 编排 clean A/B 与 LR1–LR9、CR1–CR3；只通过命令行调用读取器与验证器 |
| `d1_env_manifest.py` | 进程内环境记录与固定版本比对 |
| `d1_selftest_data.py` | **合成**输入生成器（仅供自测） |
| `requirements-d1.txt`、`D1_ENV_FREEZE.md` | 依赖与 CPU 环境冻结说明 |
| `D1_CODE_SHA256SUMS` | 以上文件与测试文件的 SHA-256 |
| `../tests/test_d1_selftest.py` | 合成数据自测（含对验证器的反向/篡改测试） |

读取器与验证器**互不 import、不共享函数**（`Static.test_reader_verifier_driver_are_independent` 检查）。
流水线输出**不含** D1 总体 PASS（`d1_overall = NOT_DECLARED__PIPELINE_INCOMPLETE`）；R6 读取前部分、R7、T1–T6、数据获取完整性均 NOT TESTED。
未编写（本阶段未授权）：数据获取脚本、Tokenizer 拟合脚本、validation/test split 的哈希/行数/round-trip 脚本。
