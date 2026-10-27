# F3B-D1-A-CPU-002 — 检查点：最小争议实验（E1 归属安全 / E2 CA×Popen / E3 CB 遗漏 T5）

**状态：`EXPERIMENT COMPLETE (ISOLATED CPU) / TOOL PASS / E1 ORIGINAL ATTRIBUTION UNSAFE WHEN ASSUMPTIONS VIOLATED / E2 CA-FIRST BREAKS Popen STATE / E3 CB OMITTED-T5 HAZARD CONFIRMED + RECOVERABLE / NO A-vs-B WINNER / PENDING CHATGPT REVIEW`**。**GROK DEFERRED**（Grok 交叉审核暂缓至 2026-10-30，不是 PASS）。冻结 R3 `SPEC FROZEN` 不变；真实 D1 `NOT AUTHORIZED`；G3～G6 `NOT TESTED`；本轮不选择最终方案，不声称 A/B 等价或实施验收完成。

## 1. Git

| 项 | 内容 |
|---|---|
| 分支 | `d1-r3-a-cpu-002-minimal-dispute-20261027`（起点 `ed4089c50cd67f91a4c621da27ba542d665f010c`，CPU-001 分支不被覆盖） |
| 预注册计划提交 | `23f60d28c37640d6090451af198491f575db01ce` |
| 正式运行使用的代码提交 | `57ea64bc41edbe8e718129335a1c08ffea1fd2e8`（运行时存在一个未跟踪的 `e2_merge.py`，不属于被测代码） |
| 最终提交 | 与本检查点同一提交（SHA 见汇报） |

## 2. CPU-001 原始记录保存位置（澄清与更正）

- **在 Git：**合并原始记录 `a_predicate/results/a_predicate_cpu_001_results.json.gz`（SHA-256 `02489a42701123c237e33654b685a8d375348e7d288a6c79fbb4d30f3c65f59b`，1860 条）、derived、单元测试输出、起点核对、完整性核对、`dev_runs/`（2 个）、`run1_before_pidfd_esrch_fix/…derived.json`；第 1 轮合并原始 JSON 仅在 Git 历史提交 `4543fb6`。
- **更正：**CPU-001 文档说「`parts/` 保留」，但仓库 `.gitignore` 第 101 行 `parts/` 使所有 `results/parts/` 目录**未进入 Git**。已把 CPU-001 两轮的分片按字节原样归档到 `a_predicate_002/results/cpu001_raw_parts_archive/`（tar.gz SHA-256：run2 `e941d4be…44f1`、run1 `bccc5fa8…ddb`，附逐文件 `.sha256` 清单），并核对 run2 分片 = 已提交合并文件（1860 = 1860）。CPU-001 目录未改动。
- CPU-002 的 `results/parts/` 已用 `git add -f` 纳入。

### 2.1 审核后补正（证据归档，提交 8bd5ff5 之后）

ChatGPT 审核指出：提交 `8bd5ff5c…` 的 GitHub 文件树里**没有** `cpu001_raw_parts_archive/`。核对属实，**是我的错误**：上文第 2 节写「已归档」时，文件只存在于本地——仓库 `.gitignore` 第 394 行 `*_archive` 把该目录**静默忽略**，`git add -A` 没有收录，而我没有用 `git ls-files` / 远端文件树核对就写成了已提交。（与 `.gitignore` 第 101 行 `parts/` 属同一类问题。）

补正（新的证据补正提交，**按原字节**，未重新生成）：本地两个 tar.gz、两个 `.sha256` 清单与原始分片均仍在且与清单一致；对它们执行了 `gzip -t`、`tar -t`、解压后逐文件 `sha256sum -c`（run2、run1 各 88/88 OK）、tar.gz 自身 SHA-256 与第 2 节登记值一致（run2 `e941d4be…f1`、run1 `bccc5fa8…ddb`）、run2 归档分片的 1860 条记录与已提交合并文件逐条相同；全部输出在 `results/cpu001_archive_verification.txt`。随后用 `git add -f` 提交，并用 `git ls-tree` 在**远端**提交上复核这四个文件存在。其余被忽略的路径只有 `__pycache__`（无关）和 CPU-001 原位的 `parts/`（其内容已由归档覆盖）。

**因此：**CPU-001 原始分片的 Git 归档验收，以补正提交为准（见汇报中的提交 SHA 与远端复核）；8bd5ff5 本身不含这些文件。

## 3. 文件与 SHA-256

| 文件 | SHA-256 |
|---|---|
| `docs/F3B_D1_A_CPU_002_PLAN_20261027.md`（预注册 + REV-1/REV-2） | `40105cbb90f7463b513102a603a56197207389891058ecd474886b70163716e6` |
| `docs/F3B_D1_A_CPU_002_REPORT_20261027.md` | `a221c0603fd1c5b3aeb560e55efa28ca6faacaf4742b341502b25241620282e0` |
| `a_predicate_002/e2_lab.py` | `395ddb219d58f36915cff6ac0a5b49a8ae1bd65224916541acdbadf6bf5ac407` |
| `a_predicate_002/e2_cases.py` | `b2e715675a9c0d9dc94c411dbb9a48b261e6f440fa77c1cd0630edf9915ca86c` |
| `a_predicate_002/e2_merge.py` | `fd3b90a2865a3461bdff8ff257bd23505979bb9d58e6d7b93597f3964703f6b5` |
| `a_predicate_002/run_all.sh` | `af03d5927af9d8ce7820871bfa7f10c9394601d64f4eeaddf47ca6fe7b4cf716` |
| `a_predicate_002/test_e2_lab.py` | `34df873721c76bb2c310d864ab6a183fe1ede00cf4d1559911dad67cdbc86a5f` |
| `results/a_predicate_002_results.json.gz`（430 条原始记录） | `78616c7f883b4a6b6c1b5ea57b25e2a953bda25702f7cb4e8b16ab5d03469bfb` |
| `results/a_predicate_002_derived.json` | `ad3a9c972c83baf7cd0c69050116dec1ae8ea11c4148ec45894ec62345855782` |
| `results/test_e2_lab_output.txt`（11/11 OK） | `dcde6db38c30bbf064b7b2d1bd63e66dca3cbc57a47c358afaa93fb7c0f2b6e9` |
| `results/precheck_start_point_cpu002.txt` | `90d0afe41f608ccf1d29b0c73272c4766331b17ff5a0354703b35a58ef7a837d` |

`results/parts/*.json.gz`、stdout / stderr 与 `results/dev_runs/`（三份开发性冒烟结果：REV-1 / REV-2 之前的失败记录）全部保留。

## 4. 验收矩阵与结论

| 项 | 结果 |
|---|---|
| 总运行 | 430；BLOCKED 0；清理残留 0；台架异常 0 |
| E1 归属安全 | 原臂 CA/CB：阳性对照 P1/P3、辅助进程 A1–A3 全部 PASS；**封闭世界断言被违反（X1a/X1z/X2）与非独立会话（S2）共 40 次运行全部 FAIL**（非目标被杀 / 被回收）；严格变体 CA-S/CB-S 同样 40 次运行零违反，代价：从未登记的真后代 → `UNKNOWN`（P2）；内核层面确认正确启动的阶段不可能出现同会话非目标进程（S1，`EPERM` 5/5） |
| E2 CA × Popen | CA 先回收后 Popen 对退出码 7 / SIGKILL / SIGTERM 一律报告 **0**（15/15 FAIL）；CA 自有记录 100% 正确；竞态 50 次中 CA 赢 42（Popen=0）、Popen 赢 8（CA `UNKNOWN`）；无双重回收、无两方都丢状态；CA-P（Popen 唯一回收者）全 PASS；CB 在 T5 之后同样使 Popen 得 0 |
| E3 CB 遗漏 T5 | 僵尸与 pid 持续占用 225/225 个样本；迟到 T5 全部恢复、状态正确；监督器被杀后外层可凭 pidfd + 指纹清理全部（残留 0），CB 的未回收僵尸状态可读而 CA 已回收的不可恢复；异常路径无 `finally` 时 CB 遗留僵尸 5/5 |
| A/B | **无明确优劣**；归属风险是共同部分，A/B 差异集中在 Popen 兼容、T5 依赖、状态可恢复性 |

## 5. 变更纪律核对

| 项 | 实际 | 状态 |
|---|---|---|
| CPU-001 原始证据与代码（`a_predicate/`） | 相对 `ed4089c` 无差异 | PASS（见汇报中的 diff 输出） |
| 冻结 R3 / 决策记录 / 冻结记录 | SHA-256 与起点相同：`66a65614…42c5` / `6209602e…6319` / `e3bba6b0…596f` | PASS |
| `D1_CODE_SHA256SUMS` | 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN` | PASS |
| 上游 Parcae / 真实 D1 代码 / G3～G6 | 未触碰 / 未运行 | PASS |
| 预期判据 | 运行前预注册；只做了方法修订 REV-1、REV-2（保留原结果） | PASS |
| GPU / 数据下载 | 未使用 | PASS |

## 6. 未解决问题

1. 严格归属变体是否应进入 R3、可用性代价（更多 `UNKNOWN`）是否可接受；变体未在 CPU-001 的完整矩阵上重跑（NOT TESTED）。
2. Popen 的唯一回收者约定、以及「监督器是否应管理 Popen」的架构选择；E2 结论依赖 CPython 3.13.16 的 `subprocess`，其它版本 NOT TESTED。
3. 监督器异常死亡时存活目标继续运行（无 PDEATHSIG）；两臂相同。
4. E3 的 pid 1 清理时间、内存数字均为本环境单次观察。
5. 仍未测：T-12/T-13（归属专项）、T-15（整组信号）、T-16（真实 pid 复用）、其它内核、封闭世界断言的其它违反方式。
6. 沿用的未决项：D08 用途声明文本；D06 只批准 B-LFS；τ / G_term / G_kill / W 为初始验收值；GitHub 分支保护 NOT VERIFIED。

## 7. 交叉审核状态

ChatGPT：**PENDING**。Grok：**DEFERRED**（至 2026-10-30，不是 PASS）。

## 8. 下一条唯一研发指令

等待 ChatGPT 审核本轮结果；Grok 交叉审核暂缓至 2026-10-30（GROK DEFERRED）；之后由项目负责人决定是否进入 R3 修订评审或进一步的仲裁实验。不启动超出 E1/E2/E3 的新实验。
