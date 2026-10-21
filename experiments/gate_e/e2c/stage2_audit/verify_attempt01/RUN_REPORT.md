# E2-c 阶段 2 正式 verify：第 01 次尝试的运行记录

- **授权**：Gate E2-c · Stage 2 Formal Verify — GO（2026-10-21），只授权一次正式 verify 及其结果的提交；不授权 freeze、盐值、test2、阶段 3 或阶段 4。
- **实现基线**：`1f6524441c2a08a583be9acc38d14b09848d11d1`
- **结论**：Stage 2 Verify PASS Candidate — Pending Independent Acceptance。这不是阶段 2 的整体 PASS，也不进入 freeze。

## 1. 启动前核对（`prelaunch_checks.txt`，05:52:52Z）

| # | 项目 | 结果 |
|---|---|---|
| 1 | 本地 HEAD = 基线 | PASS |
| 2 | 远端 `claude/openmythos-research` = 基线（`git ls-remote` 实时读取） | PASS |
| 3 | 工作区干净，没有进行中的合并、变基或拣选 | PASS |
| 4 | 冻结代码树 `4888bbe3…`（104 个文件）：自 f7a0ffe 以来只有 I2 的 4 处改动，每个文件都等于 HEAD 中的版本；驱动自己的启动检查（只读复现，不打开账本）不会拒绝 | PASS |
| 5 | 阶段 1 最终审核文件、预注册、设计审核、λ/λ₂、校准、阶段 1 环境记录、E1 清单的 sha256 都等于批准值；`stage1/` 的 tree id 与 f7a0ffe 相同；E1 题集核对通过 | PASS |
| 6 | `stage2/` 和冻结文件都不存在，也从未出现在 git 历史中 | PASS |
| 7 | 没有正在运行的 E2-c 驱动、V2 工作进程、作业、训练或启动器进程 | PASS |
| 8 | Python 3.13.16、torch 2.14.1+cu130、numpy 2.5.3、pip freeze、平台、4 核 CPU，都与阶段 1 记录相同 | PASS |
| 9 | 可用磁盘 15968 MiB；日志写在仓库之外的会话临时目录，该目录在此前的容器重启中保留了下来 | PASS |
| 10 | 没有设置任何 `E2C_*` 或 `STUB_*` 变量 | PASS |

结果：GO。核对本身没有写入仓库中的任何文件。

## 2. 启动与运行（`run_verify.sh`、`launch_record.txt`、`verify_console.txt`）

- **启动方式**：`setsid nohup bash run_verify.sh`。
  - 包装脚本用 noclobber 写一个启动标记，保证只启动一次；
  - 启动的那一刻再核对一遍 HEAD、工作区、`stage2/`、相关变量和进程；
  - 然后启动驱动，等它结束，记录真实的退出码。
- **命令**（工作目录 `experiments/gate_e/e2c`）：

  ```
  E2C_STAGE2_AUTHORIZED=verify PYTHONHASHSEED=0 /usr/bin/python3 e2c_stage2.py verify \
    --expected-commit 1f6524441c2a08a583be9acc38d14b09848d11d1 \
    --authorization "E2-c Stage2 Formal Verify GO; reviewed implementation 1f652444; single initial execution; cumulative budget 3600 seconds; verify only"
  ```

- **时间与进程**：开始于 05:53:35.307Z，结束于 05:55:29.435Z；驱动 pid 517；**退出码 0**。
- **环境变量**：
  - 两个变量只设在驱动进程上，键空间作业和 V2 工作进程继承它们。
  - 附录 A 脚本按驱动的实现，只在 `PATH` 和 `LANG` 的最小环境中运行，没有 `PYTHONHASHSEED`。它的输出与预注册逐字一致。
- **只启动了一次**：没有续跑，没有重试。

## 3. 结果

**F11**
- 附录 A 输出逐字一致：stdout sha256 为 `3b58fb66…`，等于批准值。
- 键空间作业的计数：H 12006，U 5093，R* 6913，M1* 4129，与附录 A 相同。
- 键规则：52 个字母，119,340 个键，12,006 个留出键，两种语句顺序上的不一致为 0。
- 哈希：
  - R* sha256 = `b0f8967022a7eda775dc1006f24788494adea1199af9bfa21d08297fdb103087`
  - M1* sha256 = `f8cf6235e99803f4c3684dbe06fbabbffcef56e91acba6ad7ef394382f4a680c`
  - 规则：按键字符串排序，每行一个键，以 `\n` 结尾，UTF-8 编码。键列表没有被保存。

**V2**
- 33 个种子全部完成，每个都是 12000 次更新 × 64 个接受样本 = 768,000 个样本，留出键为 0。
- 与阶段 1 的 60 份参考记录比较了 1132 个链点：驱动报告全部相等。
- 运行后的只读独立复核（直接比较已记录的链与已提交的参考记录，没有重新生成训练流）：1132 个点，不一致 0；首批哈希 60 份都相同。
- E1 的非 U 题集（dev_seen、pool_b_k2、pool_c_k2）中的留出键为 0。

**输出文件**
- `stage2_verify.json` sha256 = `6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a`
- `v2_streams.json` sha256 = `a8bdcd34199441038442111ef28dac221ec37c7eb063b772fbbbb6750c6055fc`
- 两者都与 `summary.json`、账本中的 `published` 字段以及记录中的 `v2.streams_sha256` 一致。

**预算**
- 1 个区间：verify，PASS，`used_seconds_at_end` 113.33917 秒，上限 3600 秒。
- 没有补计，没有遗留区间。
- 发布窗口 0.92 毫秒。

**停止与审核记录**：没有 `verify_stop.json`，也没有 `budget_review_required*.json`。

**泄漏扫描**
- 驱动：51 个文件，命中 0。
- 运行后复核：`stage2/` 加控制台记录共 56 个文件，命中 0。
- 没有冻结文件、盐值或 test2 文件。

**进程与收尾**
- 运行结束后没有遗留进程。
- 账本关闭之后，写 `summary.json` 用了 0.001 秒，日志用了 0.002 秒。
- 账本关闭到进程退出约 0.8 秒，这是解释器退出的时间，按已披露的约定不计入账本。
- 没有未完成的收尾操作。

**驱动的只读 `check` 命令**：退出码 0，`pass: true`，没有 `review_pending`。运行前后 `stage2/` 的 54 个文件逐字节相同（`stage2_sha256_before_check.txt` / `stage2_sha256_after_check.txt`）。

## 4. 本目录的文件

| 文件 | 内容 |
|---|---|
| `prelaunch_checks.sh` / `.txt` | 10 项启动前核对，及其结果 |
| `readonly_prestart.py` / `prelaunch_prestart_replica.txt` | 驱动启动检查的只读复现及输出 |
| `run_verify.sh`、`launched.marker`、`launch_record.txt` | 一次性启动的包装脚本、启动标记、时间、命令、pid 和退出码 |
| `verify_console.txt` | 驱动完整的 stdout 和 stderr |
| `monitor.sh`、`ledger_status.py`、`monitor_log.txt` | 运行中的只读监视及其记录。第一次快照中账本读取脚本有引号错误，修正后重新执行；这只影响监视，不影响运行 |
| `postrun_checks.py` / `.txt` | 运行后的只读核对 |
| `driver_check_command.txt` | `e2c_stage2.py check` 的输出 |
| `SHA256SUMS.txt` | `stage2/` 全部文件和本目录全部文件的 sha256 |

`stage2/` 中的文件都按驱动写出的原样提交。锁文件 `budget_ledger_s2.json.lock` 被已有的 `*.lock` 规则排除，它是空文件。

## 5. 已知异常与未决风险

- **没有发现运行异常。**
- **`PYTHONHASHSEED`**：附录 A 脚本运行时没有 `PYTHONHASHSEED=0`（见第 2 节）。它的输出与预注册逐字一致，计数也与键空间作业相同。
- **结果的性质**：这是待独立验收的候选结果，不是阶段 2 的整体 PASS。freeze、盐值登记、test2 和阶段 3、4 都没有授权，也都没有执行。
- **预算的分配**：freeze 与 verify 共用阶段 2 的 1 小时预算，freeze 剩余约 3486.7 秒。
- **账本的计时依据**：账本按墙钟累计。本次运行中，区间长度（113.34 秒）与包装脚本记录的起止时间（114.1 秒，包括解释器退出）一致。
