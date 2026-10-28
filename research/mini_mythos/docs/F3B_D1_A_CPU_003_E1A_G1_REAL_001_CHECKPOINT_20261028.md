# F3B-D1 CPU-003 E1-A G1 REAL 001 checkpoint (2026-10-28)

* 任务 `F3B-D1-A-CPU-003-E1A-G1-REAL-001`；分支 `d1-r3-a-cpu-003-e1a-g1-impl-20261027`；**执行时 Git SHA `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d`**（被测代码 `d175a1ab89c521ec78de9fa39fb139a0e20b1788`）；证据提交 SHA 单独记于 `a_predicate_003/g1_real_001_results/EVIDENCE_COMMIT_RECORD.md`，二者不同、不得混淆。
* 状态：**G1 REAL EXECUTED — CROSS-REVIEW PENDING。** 单次真实执行的记录判定为 PASS（run_id `g1_20261028_025922_68ac93`，退出码 0，`g1_closed.json` 已发布并校验，T1–T4 各 17 项检查全部 PASS，运行级 G1-C01/C02/C16/C17 PASS）；该判定在 ChatGPT / Grok 独立复核之前不是最终结论。
* 执行：授权 `g1_auth_20261028_025944_cc36f98a`（本地 0600、已消费、不提交 Git）；只调用一次 `--execute`；起止 2026-10-28T02:59:51Z–02:59:55Z，总时长 3.502 s；4 次 fork（pid 312–315）、零信号、零残留、零后代；T1/T2/T3 退出 111，T4 退出 112（fork 后 2.004 s）；全部 Z 态先于 wait 被观察，`waitpid` 返回特定 pid；`b"R"` 从未写入，无 RELEASED / FIRST_ACTION / READY。
* 独立核验：`independent_verify.py` 不使用 `g1_judge`，对读回的 evidence / summary / closed 逐项断言通过。
* 未改动：G1 V1 判据与预注册、G0、Bench、R3、Parcae、递归 Transformer 架构；未使用 GPU；未进入 G2 / G3 / BV / E1-A；不允许第二次真实执行。
* 局限：Python 层守卫不等于证明内核层无其它路径；G1 仅覆盖负向 gate，一次执行不是统计稳定性证据。
* 结果目录：`a_predicate_003/g1_real_001_results/`（报告、原始 stdout / stderr / 退出码 / 起止时间、检查表、独立核验、SHA256SUMS）与 `a_predicate_003/evidence/g1_20261028_025922_68ac93/`、`evidence/_g1_consumed/`。
* 唯一下一条指令：ChatGPT / Grok 对原始证据交叉复核；之后由项目负责人另行决定。**不自动进入 G2 / G3 / BV / E1-A。**
