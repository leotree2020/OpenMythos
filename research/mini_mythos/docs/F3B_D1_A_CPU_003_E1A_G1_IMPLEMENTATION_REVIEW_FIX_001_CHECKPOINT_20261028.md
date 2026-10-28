# F3B-D1 CPU-003 E1-A G1 implementation — review fix 001 checkpoint (2026-10-28)

* 基准（ChatGPT 审核）`453fe4eba09a61564c71a1fb3f5d0041ba789e9f`；分支 `d1-r3-a-cpu-003-e1a-g1-impl-20261027`；修复提交 `a5d9168972156c9017a9b1b3e64463e302b3b0cf`（其后只增审核输出、报告、本 checkpoint、PROJECT_MAP）。
* 状态：**G1 IMPLEMENTATION COMPLETE（审核修复已应用）/ STATIC AUDIT RECORDED / CPU TESTS NOT TESTED / G1 REAL NOT AUTHORIZED。** G1 V1 判据与预注册不变（`1992d75d…1257` / `37487237…cd69`），未创建 V2；G0、Bench、R3、Parcae、`g1_auth.py`、设计文件不变；未运行任何测试，未创建授权文件。
* 修复 1：`run()` 异常路径不再使用 `S.rec`（可能是上一测试的旧节点）。新增 `alive_nodes` / `report_residue`：检查本轮**全部**节点（已登记经 pidfd；已 fork 未登记 / 登记失败经 /proc，身份未核验；/proc 不可读按存活）以及 guard 记录的未回收子进程（spawn_direct 尚未返回），按既有规则写 MANUAL_DISPOSITION，不发信号；`run_test` 先清 `S.rec`，异常时记录 `stopped_after`。
* 修复 2：CPU runner 验收逻辑移入无副作用的 `tools/g1_test_acceptance.py`：只有完整选择、`ast` 发现的全部预期测试 ID（289 个唯一 ID，来自全部 `tests/test_g1_*.py`）各执行一次且 PASS、0 SKIP / FAIL / ERROR / 加载错误 / 哨兵违规才是 PASS；`--groups` 诊断运行最多 INCOMPLETE；记录 skip / expectedFailure / unexpectedSuccess；退出码 0 / 1 / 3。
* 修复 3（停止规则核对）：冻结定义“首个不明显符合预期的测试后停止”与任务要求“首个非 PASS 停止”。最小反例：T2 退出码 111、无消息、清理 ok，但 REGISTERED pid ≠ S1b 所见 pid（C04 FAIL 类），旧规则继续 fork T3/T4。只调整实施层：`g1_judge.judge_test_in_run` 用判定器自己的 C04–C15 检查函数判定当前证据，`in_run_assessment(..., judged)` 任何非 PASS 即停；C01/C02/C03/C16/C17 与末测试的 C12–C14 末尾部分需要运行结束，留给最终判定。
* 负控制（只写未跑）：289 个测试（judge_cases 102、auth_preflight 38、run_parts 68、boundaries 28、mutations 23、runner_acceptance 30），含残留路径 17 个、in-run 判定、runner 验收 30 个及新变异测试。
* 静态审计：`tools/audit_g1_implementation.py`（AST / JSON / 哈希 / 正则 / git diff，不执行被审代码）FINDINGS 0；追溯 38 行，NOT FOUND 0；基准 `48d241f`→HEAD 仅 G1 文件；`453fe4e`→修复提交仅 `g1_run.py`、`g1_judge.py`、测试、工具。结果目录 `research/mini_mythos/a_predicate_003/g1_impl_static_audit/`（旧版保留于 `review_base_453fe4e/`）。
* 未解决：固定样本与判定器（含 in-run 判定）仅人工对账；`run` / `run_test` 无法脱离进程做单元测试；in-run 读 registry 时 /proc 枚举偶发问题只会导致更早停止（BLOCKED / RUN-INCOMPLETE，不会 PASS）；`EXPECTED_TOTAL_TESTS` 须随测试增减同步（审计核对）。
* 唯一下一条指令：ChatGPT / Grok 复核本修复；通过后由项目负责人**单独**授权 G1 CPU 测试（完整运行须按上述验收规则 PASS）；真实 G1 另需单独授权。
