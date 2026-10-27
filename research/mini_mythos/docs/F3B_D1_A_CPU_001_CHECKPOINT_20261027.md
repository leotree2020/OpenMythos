# F3B-D1-A-CPU-001 — 检查点：R3-A 最小 CPU 受控对照实验（B0 / CA / CB）

**状态：`EXPERIMENT COMPLETE (ISOLATED CPU) / TOOL PASS / B0 DEFECTS REPRODUCED / CA & CB PASS ON AUTHORIZED MATRIX / NO A-vs-B WINNER / PENDING CHATGPT REVIEW / GROK DEFERRED`**。冻结 R3 `SPEC FROZEN` 不变；真实 D1 `NOT AUTHORIZED`；G3～G6 `NOT TESTED`（未启动）。

## 1. Git

| 项 | 内容 |
|---|---|
| 分支 | `d1-r3-a-cpu-validation-20261027`（建在文档分支 `d1-r3-a-revision-proposal-20261027` 的 `a12241ef1a8a7441215554a530c946e3dde6f4e0` 上；它是指令基准 `cc474f56ae77882fa77cfe4e7deb0e6b5d4305e8` 的直接后代，仅含 REVIEW-002 的文档修订；此偏差已在报告第 1 节说明） |
| 正式运行（第 2 轮）使用的代码提交 | `4543fb6e5b75dce431396ffb96e6049815dbce64`，运行时工作区干净 |
| 最终提交 | 与本检查点同一提交（SHA 见汇报） |

## 2. 文件与 SHA-256

| 文件 | SHA-256 |
|---|---|
| `F3B_D1_A_CPU_001_REPORT_20261027.md` | `312147f9dfba0d0ace23db5748fe4452d1bd8c42cd9d9aa315282486daf67fa1` |
| `a_predicate/a_lab.py` | `3b843ccd1da56c3237e767753b0f09b4088cc10f9589565003a6bcf11c9b07e4` |
| `a_predicate/a_cases.py` | `95ceb02637b84dc370b35c4289cb5288cf7a54cad9b6c05f576edfe013ca9dff` |
| `a_predicate/a_node.py` | `8437ef551fab8537374a6e4d2c30d184dc504c8b63b8610311a67c22a8c24315` |
| `a_predicate/a_merge.py` | `49aeb4f5159cc649e4ca68f0012c0b64591082f544ea44f083f337e56bc88ceb` |
| `a_predicate/run_all.sh` | `0ce8fad063984ae579ce4b4ad7693f629d7b5e83b0b8118ddadc3672c694794f` |
| `a_predicate/test_a_lab.py` | `7c8b11d801aa08a3e34e005004f8892ef9c0a918d70dae8e6592eaa7cc8cee99` |
| `results/a_predicate_cpu_001_results.json.gz`（1860 条原始记录） | `02489a42701123c237e33654b685a8d375348e7d288a6c79fbb4d30f3c65f59b` |
| `results/a_predicate_cpu_001_derived.json` | `46e9baa433485decf8d23a691ca9c02c5fad2290823ab82b6a29af6a61649fb2` |
| `results/test_a_lab_output.txt`（22/22 OK） | `bdaf0012ffd97d2daa893d72e30df61ab8a9d15f862d41082b8927a44dedadb7` |
| `results/precheck_start_point_20261027.txt` | `c371f09af91485f8f6aec28fc2e9b2c46a064e88ff4ac28135cb5fb038e5903b` |

`a_merge.py` 在第 2 轮运行之后才改为读 / 写 gzip（其余代码文件与第 2 轮运行时的提交 `4543fb6` 相同）。每用例的 `parts/*.json.gz`、stdout / stderr、第 1 轮（`run1_before_pidfd_esrch_fix/`）与开发记录（`dev_runs/`）均保留，未覆盖。

## 3. 结果汇总（详见报告）

- 运行总数 1860；BLOCKED 0；清理残留 0；台架工具异常 0。
- B0：NOREAP 71 PASS / 289 FAIL；EVAL_THEN_REAP 155 / 205；REAP_THEN_EVAL 225 / 135 —— G1-02 与 G2-01 复现，G2-02 部分复现。
- **CA 365/365 PASS；CB 365/365 PASS**；零越界信号、零误回收、零退出状态丢失；判定矩阵 CA = CB 逐格相同。
- 差别仅在：pid 释放时机（CA 早）、僵尸滞留与 T5 依赖（CB）、退出状态来源。**无明确优劣。**
- `killpg(pgid,0)` 对只剩僵尸的组在本内核（6.18.44-fc-v165）15/15 返回 `success`。

## 4. 变更纪律核对

| 项 | 实际 | 状态 |
|---|---|---|
| 冻结 R3 / 决策记录 / 冻结记录 | 与起点哈希相同：`66a65614…42c5` / `6209602e…6319` / `e3bba6b0…596f` | PASS（见汇报中的实际核对输出） |
| `D1_CODE_SHA256SUMS` | 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN` | PASS |
| v1 / R1 / R2、Driver / Reader / Verifier、上游 Parcae | 未触碰（相对 `a12241e` 的 Git diff 只含新增文件） | PASS |
| G1/G2 原始证据 | `r3_cpu_probes/g1g2/` 相对 `a12241e` 无差异 | PASS |
| 方案 A/B 写入冻结 R3 | 没有；也没有选定最终方案 | PASS |
| G3～G6 / 真实 D1 / GPU / 数据下载 | 未运行 | PASS |

## 5. 交叉审核状态

ChatGPT：对本实验 **PENDING**。Grok：**DEFERRED**（不是 PASS）。若意见不同，保留分歧，由最小裁决实验回答（需单独授权）。

## 6. 未解决问题

1. A / B 的取舍证据不足；本矩阵区分力有限（报告第 9 节）。
2. 未运行：T-12a/b、T-13a/b、T-15、T-16（NOT PLANNED）、T-04b-B（策略，待负责人）、漏 T5 / `Popen` 互操作 / 高并发回收的仲裁实验。
3. 真实 pid 复用、其它内核、pidfd 不可用的真实行为、封闭世界断言被违反后的误归属：未验证。
4. 条件 (3) 在冻结 R3 中是否排除僵尸的文字歧义：B0 的 T-04/05/06/07 FAIL 依赖于「包含僵尸」读法。
5. 沿用的未决项：D08 用途声明文本；D06 只批准 B-LFS；τ / G_term / G_kill / W 为初始验收值；GitHub 分支保护 NOT VERIFIED。

## 7. 下一条唯一研发指令

等待 ChatGPT 独立审核与 Grok 交叉审核，再由项目负责人决定是否进入最小争议实验及 R3 修订评审。
