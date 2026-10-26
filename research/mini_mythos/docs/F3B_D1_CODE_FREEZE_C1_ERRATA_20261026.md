# F3-B / D1 — 代码冻结候选勘误 C1（响应 ChatGPT 对 `090b6191` 的审核）

**状态：`D1 CODE FREEZE CANDIDATE C1 / PENDING CHATGPT RE-REVIEW`**

审核基准：`090b6191f7558a43462691bb4fa9afa4b56fed9b`（`CODE FREEZE CANDIDATE FAIL`，仅针对代码完整性验收，不否定合成自测，不代表 D1 真实实验失败）。上一份准备记录 `F3B_D1_CODE_FREEZE_PREP_20261026.md` 原样保留，本文件是对它的勘误与补充；凡冲突以本文件为准。

边界不变：只做 CPU 合成数据测试；**没有**下载 WikiText，**没有**拟合 Tokenizer，**没有**训练，**没有** GPU，**没有**改 Parcae/AxoNN，**没有**开始 D2/D3。D1 仍是 `NOT TESTED / NOT AUTHORIZED`。

## 1. 缺陷确认

在审核基准的验证器上，我把 6 个最小回归测试跑了一遍（`gate3_d1/c1_logs/old_verifier_vs_new_tests.txt`）：6 项全部失败，即旧验证器**接受**了被篡改的故障 trace（单块 `block_hash`、`chain_hash`、`tail_sha256`、`blocks_total`、control trace 的 ids）和被篡改的调度文件。这些缺陷是真实的。原因：旧 `verify_cr` 只验证 `segments` 声明与逐行分类，从不重算故障 trace 自己的块哈希与链，也没有把整个故障流与预期的唯一变异对比。

## 2. 每项修订：目的、输入、预期、实际、状态

环境（全部相同）：沙箱，Python 3.13.16，`tokenizers 0.23.3`，`pyarrow 26.0.0`，4 CPU，无 GPU，无网络访问，合成数据（`d1_selftest_data.py`，2048 个合格行，156,605 Token，2409 块，`tail_len=20`）。全量输出：`gate3_d1/c1_logs/selftest_output.txt`。

| 项 | 目的 | 输入 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|
| P0-1 故障 trace 完整性 | `verify_cr` 对故障 trace 与 control trace **同样**重算每块 `block_hash`；用实际块重算链并核对 `chain_hash`；核对块号连续、`blocks_total`、`blocks_this_run`、`stream_token_pos`、EOF tail 的 `tail_len/tail_sha256/长度`、恢复的 carry 位于输出流开头。不要求故障链等于正常参照链 | 单块 `block_hash` 改、`chain_hash` 改、`tail_sha256` 改、`blocks_total`/`stream_token_pos`/`tail_len` 各 +1、块号跳号、control 的 id 改/哈希改 | 全部 FAIL（退出码 1，且失败项名含 `fault trace integrity` 或 `control trace integrity`） | 全部 FAIL；正常 CR1/CR2/CR3 仍 meta-PASS | PASS（合成） |
| P0-2 全局来源顺序 | 验证器按冻结的 CR 定义独立构造故障后 Token 流与来源片段序列（`fault_plan` / `expected_run`），要求实际流（ids、块哈希、尾部、链、位置）与整窗口来源顺序（前缀 + carry + 续读）与之完全一致；保留逐行分类，但它不能单独宣告 meta-PASS | 构造自洽伪造 trace（块哈希、链、尾部、片段全部正确）：(a) 恰好等于预期 → 应通过；(b) CR1 预期流中交换两个相邻整行；(c) CR2 同样交换 | (a) PASS；(b)(c) FAIL，且 (b) 中逐行分类项仍是 PASS、全局项 `(d')` 为 FAIL（证明旧逻辑会放过） | 与预期一致 | PASS（合成） |
| P0-3 对抗性单测 | 补齐要求的回归测试 | 见 `tests/test_d1_selftest.py` 中 `test_cr_*`、`test_forged_*` | 要求的四类都存在，正常 CR 仍通过 | 37 项全部 OK（含 13 项新增）；旧验证器上 6 项失败 | PASS（合成） |
| P0-4 调度独立重算 | `verify_clean` 用冻结规则重算 P1–P5（`build_schedule`），与保存的 `schedule.json` 逐字段比较，期望值用重算结果；P1、P5 再单独对照规则 | 把 P3 的 `stream_pos` 加 65（仍升序、carry 仍为 32） | FAIL，且 `schedule recomputed …` 项失败 | 与预期一致；旧验证器无此项 | PASS（合成） |
| P1-5 real 模式与正式身份分离 | 新增身份标签 `SELFTEST_SYNTHETIC / REAL_CODE_PATH_NON_FORMAL / FORMAL_D1_CANDIDATE` 与 `d1_formal_experiment` | 合成 Parquet + 手工 BPE 的 real 模式；`identity()` 的 6 种清单组合 | 合成/非 FROZEN 配置/缺 `formal` 块/oid 不符/授权引用为空 → 非正式；随附配置状态为 `FROZEN_CANDIDATE…`，因此当前不可能产生正式身份 | 与预期一致 | PASS（合成）。注：这是记账标签，不是安全边界 |
| P1-6 Python 完整补丁版本 | 配置新增 `python_full_version`，real 模式要求精确相等；selftest 只要求次版本在 3.11–3.13 | 把固定版本改成 `0.0.0` | real → exit 4（BLOCKED）；selftest → exit 0 | 与预期一致 | **未闭合**：候选固定值 `3.13.16` 是自测所用解释器，**执行主机的完整版本与依赖组合 NOT VERIFIED**，需项目负责人确认后重新冻结 |
| P1-7 30 分钟硬超时 | 驱动器给每个子进程设剩余时间 `timeout`；超时杀掉该步、判 `BLOCKED(timeout)`、保留已有证据、列出已有证据文件、不重试 | `--timeout-seconds 0.8`（仅测试覆盖；正式值取配置 1800 秒） | 退出码 4；决定文件含 `BLOCKED(timeout)`；`RUN_META.json` 仍在；没有命令被重复执行；最后一步为 `TIMEOUT_KILLED` | 与预期一致 | PASS（合成）。范围仅限驱动器流水线 |
| P1-8 未完成项显式 NOT TESTED | 决定文件新增 `not_tested`（R6 读取前哈希与 validation/test 隔离、R7、T1–T6、数据获取完整性）与恒定的 `d1_overall = NOT_DECLARED__PIPELINE_INCOMPLETE`；`verify_clean` 结果新增 `scope` 与 `not_tested` | 完整合成流水线 | 无任何总体 D1 PASS；文本不含 "D1 PASS" | 与预期一致 | PASS（合成） |

## 3. 其它变动（为配合上述修订的必要改动）

- `verify_clean`、`verify_cr` 对畸形证据（缺键、类型错）返回 FAIL（退出码 1）而不是崩溃。
- 真实模式测试 `RealModeCodePath` 现在仅在 Python 完整版本与库版本等于冻结固定值时运行，否则跳过（原先在 CI 的库版本下会因固定版本检查而误失败）。
- `D1_ENV_FREEZE.md`、`README.md` 更新；`D1_CODE_SHA256SUMS` 重新生成。

## 4. 仍需关注

1. **P1-6 未闭合**：执行主机的 Python 完整补丁版本和依赖组合需要项目负责人确认。
2. 30 分钟上限目前只约束驱动器；尚未编写的获取与 Tokenizer 拟合脚本必须计入同一个 30 分钟。
3. 缺口清单（获取脚本、Tokenizer 拟合与 T1–T6、validation/test 处理、`runtime_manifest.json` 生成者）不变。
4. `expected_run` / `fault_plan` 在验证器里按冻结的 CR 定义实现，与读取器的「读取计划」注入是两份独立代码；请复审二者是否对 CR1/CR2/CR3 的定义理解一致。

## 5. 下一条唯一指令

等待 ChatGPT 对 C1 修订复审，并等项目负责人确认执行主机的 Python 完整版本与依赖组合。**未获新的真实数据执行授权之前不得启动 D1，不得开始 D2/D3。**

---

**最终状态：`D1 CODE FREEZE CANDIDATE C1 / PENDING CHATGPT RE-REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
