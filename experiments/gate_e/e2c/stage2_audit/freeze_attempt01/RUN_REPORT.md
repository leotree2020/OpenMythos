# E2-c 阶段 2 正式 freeze：第 01 次尝试的运行记录

- **授权**：E2-c Stage 2 Formal Freeze — GO。会话消息 uuid `a2916bd6-6d44-4871-a3f2-80fc30364bc2`，2026-10-21T12:18:57.293Z。原文见 `authorization_freeze_GO.txt`，元数据见 `.meta.json`。只授权这一次 freeze、运行后的只读核验和归档；阶段 3 和阶段 4 都没有授权。
- **结论**：Stage 2 Freeze PASS Candidate — Pending Independent Acceptance。这不是独立验收结论。

## 依据

| 项目 | 值 |
|---|---|
| 已独立验收的 verify | `e79acc6e7a39e1ec4e720d9a66ec05bc8848f150` |
| `stage2_verify.json` | `6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a` |
| 批准的 r2 准备包 | sha256 `5b3e84ce34f576847c355c9acc132ffa97a5e1605c29b7e6b770ee50bca6e0e2`。启动前确认：r2 目录中所列文件全部一致，所用 6 个脚本与包内逐字节相同（见 `scripts_used_sha256.txt`；脚本副本在 `scripts_used/`） |
| 审核方的承诺值 | `52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc`。盐值明文由审核方保管，本次没有生成、索取或使用 |

## 启动与运行

- **启动前**：没有启动标记，也没有启动记录或输出文件；仓库处于 e79acc6，工作区干净。
- **启动方式**：在 r2 目录中，以 `setsid nohup` 启动 `run_freeze.sh` 一次，并设置 `REVIEWER_SALT_COMMITMENT_SHA256`（批准值）和 `FREEZE_GO_REFERENCE`（上述授权消息的标识）。包装器自身的输出 `wrapper_out.txt` 为空。
- **启动瞬间的核对**（`launch_guards.txt`）：G1–G13 全部通过，包括承诺值与批准值逐字相等，以及 GO 引用存在。
- **命令**（`launch_record.txt` 第 4 行）：

  ```
  E2C_STAGE2_AUTHORIZED=freeze PYTHONHASHSEED=0 /usr/bin/python3 e2c_stage2.py freeze \
    --expected-commit e79acc6e7a39e1ec4e720d9a66ec05bc8848f150 \
    --approved-verify-commit e79acc6e7a39e1ec4e720d9a66ec05bc8848f150 \
    --approved-verify-sha256 6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a \
    --salt-commitment-sha256 52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc \
    --authorization "E2-c Stage2 Formal Freeze GO; accepted verify e79acc6; single initial execution; shared cumulative budget 3600 seconds; freeze only"
  ```

  工作目录为 `experiments/gate_e/e2c`。
- **时间与进程**：开始 12:19:57.346Z，结束 12:21:21.030Z；驱动 pid 376；**退出码 0**。
- **只启动了一次**：没有重试，没有使用 resume 或 stale-supplement。
- **驱动输出**：
  - stdout：`{"freeze_sha256": "d0ffdab0…5f1"}`；
  - stderr：发布窗口 0.70 ms，以及驱动给出的提交提示。

## 输出

| 文件 | sha256 |
|---|---|
| `e2c_workload_freeze.json` | `d0ffdab01a7e66e0dfe6a55cdddcfa163c39a5645ed43e49a0c03784853ec5f1` |
| `stage2/stage2_freeze_receipt.json` | `5a5c6933c686ef09e6f2f40be56290cb0c35b44ae3ff3b15f31cc8df79209837` |
| `stage2/budget_ledger_s2.json`（更新后） | `40c1a3770301b9b42ad8bd39163c8729d0c26e56df6b59de6282f2e2075462df` |
| `stage2_verify.json`、`v2_streams.json` | 不变：`6331b06a…`、`a8bdcd34…` |

## 预算

- **区间 1（verify）**：不变，113.339170 秒。
- **区间 2（freeze）**：PASS，已关闭，起于 12:19:57.344Z，止于 12:21:11.301Z，时长 73.957045 秒。
- **累计**：由区间重算为 187.296214 秒，等于账本记录（`used_seconds` 187.296，`used_seconds_at_end` 187.296214），严格小于 3600 秒。
- **上限**：顶层和两个区间都是 3600。
- **剩余**：3412.703786 秒。

## 运行后核验

`postrun_out.txt`，在把任何审计文件加入仓库之前运行，退出码 0，20/20 通过。核对内容：
- 退出码为 0；
- 工作区的变化恰好是三项：冻结文件新增、回执新增、账本修改；
- verify 输出不变，verify 区间不变；
- freeze 区间已关闭、状态 PASS，pid 一致；
- 预算上限、重算的累计用时及其精度；
- 没有停止或审核记录，没有遗留进程；
- 冻结文件的哈希在账本、回执和 stdout 中一致；
- 命令、回执和冻结文件中的承诺值都与批准值逐字相等；
- 回执和冻结文件绑定了 verify 的哈希和提交、训练流、33 个种子、E1 清单及 13 个逐题集哈希、代码树、R*/M1*、λ/λ₂；
- 启动器的 `check_baseline` 没有差异；
- 没有键样式的文本。

## 收尾（只记录，不断言原因）

见 `closing_window_facts.txt`：
- 账本在 12:21:11.301Z 关闭，进程在 12:21:21.030Z 结束，相差 **9.729 秒**，这段时间没有计入账本。verify 那次是 0.795 秒。
- 账本关闭之后，仓库中（包括 `.git`）没有任何文件被修改；冻结文件、回执和账本都在关闭前或关闭时写好。
- 即使计入这段时间，累计也是 197.025 秒，不影响 F9。
- **原因未通过细分记录确认**。这段时长是否属于"异常耗时"，由独立验收判断。

## 偏差与说明

1. **收尾时长**：9.729 秒，见上节，原因未确认。
2. **容器重启**：本次启动前约 7 分钟，容器重启过一次（启动时的开机时长为 423 秒）。仓库和 r2 目录都完好，启动瞬间的核对全部通过。
3. **脚本头部**：`freeze_guards.sh` 头部打印的是 "freeze guards r1"，因为 r2 只修改了两处指定位置。日志中 G11 一行给出的 r2 路径可以说明实际运行的是 r2 的脚本。
