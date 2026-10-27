# G0_V5_PURE_TEST_REPORT — G0 V5 CPU 正确性测试验收报告

任务：`F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001`。基准 `33fb344253bebc6ba03531233955aa45ab99cbea`；最终测试对象 `e623dd45da8c3811d6fbe6a1f3cea378fc00e0be`（修复与补充测试之后）。

**最终状态：`CPU TESTS PASS` / `REAL G0 NOT AUTHORIZED`**
范围声明：`CPU TESTS PASS` 只表示 198 个纯逻辑 / 文件级 CPU 测试在进程安全哨兵之下全部通过，且本阶段发现的 2 个实现缺陷已修复并回归。**它不表示真实进程行为已被验证**：`run()`、`Guard.install()` 对真实 `fork` 的路径、`/proc` 快照、`preflight()` 的 `/proc` 部分、台架观察者交互都没有被执行（那需要真实 G0 授权）。

## 1. 执行方式与隔离

* 测试入口：`tools/run_g0_v5_cpu_tests.py`。在导入任何测试之前，它把 **所有** 创建 / 信号 / 等待进程的函数替换为会抛出并计数的哨兵（`os.fork*`、`os.kill*`、`os.exec*`、`os.spawn*`、`os.system/popen`、`os.wait*`、`os.waitpid`、`os.pidfd_open`、`os.setsid/setpgid`、`signal.pidfd_send_signal/raise_signal/pthread_kill`、`subprocess.*`）。哨兵触发次数必须为 0 才算 PASS：**两次最终运行均为 0**。（哨兵在第一次启动时即被验证有效：`platform.platform()` 内部调用 `subprocess`，被哨兵拦下，见 T-0b。）
* 隔离：`TMPDIR` 指向本次运行的新临时目录；流水线测试把 `GA.EVIDENCE_ROOT` 重定向到临时根；仓库的 `evidence/` 目录与授权文件均不存在；`python3 -B`，无字节码文件；不使用 GPU；未修改 `bench/`、Parcae、V1–V5 冻结文件、既有 `test_e1a_*.py`。
* 清单检查（运行前）：测试中只有两处出现 `--execute`：授权文件不存在的拒绝路径（`run` 被替换成会失败的间谍）与 `PIPE-15`（`prepare_dirs / run / finalize` 全部被替换）；`os.kill` 仅出现在证据夹具的字符串和一处守卫测试里，该处在运行前改为 `os.kill()`（无参数，无法发信号）与指向非子进程 pid 的等待，见 T-0。
* 环境：Python 3.13.16，Linux 6.18.44-fc-v165，4 CPU，uid 0，临时目录所在文件系统 ext4（硬链接与 `fsync` 在其上可用）。

## 2. 结果

| 组（按任务规定的顺序） | 测试数 | PASS | FAIL | ERROR |
|---|---|---|---|---|
| g1 判定器 / 证据保真 / 结案规则（67 个规则案例、F3 条件表、FID、C07、结案规则 38 案例按事实求值、标记模式、`TestJudge`） | 91 | 91 | 0 | 0 |
| g2 目录 / 管道 / 故障注入（38 案例物化目录、19 + 15 个流水线案例、守卫、预算、目录、AST 结构） | 66 | 66 | 0 | 0 |
| g3 联锁与源码约束 | 27 | 27 | 0 | 0 |
| g4 补充：启动异常不返回 1、C07 面对格式损坏的放行记录 | 14 | 14 | 0 | 0 |
| **合计** | **198** | **198** | **0** | **0** |

* 两次最终运行（`final_run1/2.json`）逐测试状态完全一致（确定性）；全部测试耗时合计约 1.4 s。
* **变异检查**（临时副本，不是仓库代码）：10 种对实现的故意破坏（F3c 要求干净写入器、删除 M-2、把序号缺口当 FAIL、用 `os.replace` 代替 `os.link`、启动错误映射到 1、标记接受尾部换行、删除 CL-02、C07 在格式损坏列表上再次 FAIL、去掉 `O_EXCL`、跳过 P7）全部被测试发现（`mutation_results.txt`）。
* 静态审计：`audit_g0_v5_implementation.py` 0 发现（66 行需求对应表，0 未找到）；`static_audit.py --dir gate_g0` 0 违规；V5 规格一致性检查与结案案例检查 0 不一致。

## 3. 失败登记（每一次失败：输入、预期、实际、环境、SHA、状态）

环境（除另注）：Python 3.13.16 / Linux 6.18.44 / uid 0 / 哨兵开启。「SHA」= 运行时的 HEAD `33fb344…`（加上当时未提交的修改）。原始输出保存在本目录的 `prefix_*.json`。

### 3.1 实现缺陷（代码已最小修复）

| 编号 | 输入 | 预期 | 实际 | 状态 |
|---|---|---|---|---|
| **D-1** 启动异常泄漏为退出码 1 | `g0_run.main(["--execute", ...])` 在启动路径的任一步（`current`、`frozen_problems`、`load`、`load_criteria`、`sha256_file`、`safe_preflight`、`ancestors`、`prepare_dirs`）抛出 `RuntimeError / OSError / ValueError / KeyError / KeyboardInterrupt`；以及 `--check` 模式下 `current()` 抛出 `OSError` | 返回 3 并在 stderr 打印 `G0-` 标记（拒绝为 2；绝不是 1，因为 1 是 FAIL 码） | 异常逃出 `main`（`prefix_g4_run1.json`：`test_every_unexpected_exception_in_the_start_up_path_gives_3_never_1` 与 `test_check_and_template_modes_also_never_return_1_on_an_exception` 为 ERROR）；作为脚本运行时 Python 对未捕获异常的默认退出码就是 1 | FAIL → 已修复 → PASS |
| **D-2** 格式损坏的放行 / 创建记录产生错误 FAIL | `guard.release_writes = [{}, {}]`（共 15 种畸形列表：时间为字符串 / null / bool / NaN、`result` 未知或缺失、`returned` / `errno` 类型错误、非对象元素、列表套列表；`first_action_mono` 为 1.8 或 null）；`guard.fork_pids = ["x"]`；`string times` + 一个成功的放行写入 | C07 为 UNEVALUABLE、总裁决不是 FAIL、C03 的 F3 规则不触发（格式损坏的证据不是证据） | C07 在 15 个畸形列表 × 2 的组合中的 22 个给出 `FAIL C07-F2` 且总裁决 FAIL；C03 的 F3a（`fork_pids=["x"]`）与 F3b / F3c（字符串时间）被触发 | FAIL → 已修复 → PASS |

D-1 修复（`g0_run.py`）：`main()` 变为包装器，`SystemExit` 原样抛出（argparse 用法错误仍为 2），其他任何异常（含 `KeyboardInterrupt`）打印 `G0-STARTUP-ERROR` 并返回 3；原函数改名 `_main`。
D-2 修复（`g0_judge.py` 的 `independent()`）：`guard.fork_pids` 与 `guard.release_writes` 必须通过冻结模式的类型验证器（`list[int]`、`list[object{mono_before, mono_after, result, returned, errno, error}]`），否则整个独立见证为 *不可用*；C07 因而 UNEVALUABLE（U5），C03 的 F3 规则 *不能触发*（与 V5 文字「证据缺失的规则不能触发」一致）。良构的违规（两次放行写入、放行前行动、RELEASED 晚于尝试）的负控制仍然 FAIL。**没有修改 V1–V5。**

### 3.2 测试自身缺陷（只改测试 / 运行器）

| 编号 | 输入 | 预期 | 实际 | 状态 |
|---|---|---|---|---|
| T-0 | 守卫测试里 `os.kill(os.getpid(), 0)` 与 `os.waitpid(-1, WNOHANG)` | 测试不得发送信号 / 触碰子进程，即使守卫失效 | 运行前的清单检查发现；改为无参数 `os.kill()` 与对 pid 999999999 的等待 | 已在首次运行前修正 |
| T-0b | 运行器收集环境信息时调用 `platform.platform()` | 哨兵之前完成 | `platform` 内部通过 `subprocess.check_output(['uname','-p'])`，被哨兵拦下（证明哨兵有效） | 运行器改为先收集后安装哨兵 |
| T-1 | `Harness.fin(**{(module, name): value})` | 14 个流水线测试可执行 | 14 个 `ERROR: TypeError: keywords must be strings`（`prefix_g23_run1.json`；`**` 的键必须是字符串） | 改为 `fin(ev, patches={...})` |
| T-2 | `test_cases_with_an_injected_fault` 比较 `files_present` | 案例记录里已经是真实文件名 | `KeyError: 'registry.jsonl'`（把文件名当键查表）`prefix_g2_run2.json` | 直接比较 `sorted(files_present)` |
| T-3 | `test_release_write_ok_needs_a_returned_value_of_exactly_one` 在 D-2 修复之后 | `returned=True` 时 `release_write_ok` 为假 | `KeyError`（该记录现在格式损坏 ⇒ 见证不可用，没有该键）`prefix_all_run1.json` | 断言改为 `available` 为假（语义更强） |

所有 T-* 都发生在测试代码；在每一次修复后重跑了受影响的组，最后全量重跑两次，198 / 198 PASS。

## 4. 仍然存在的限制与未验证项

* **B-1 / B-2（规格裁定）**：消耗目录「排他创建」与「创建或验证」两句冻结文字、`CE-E1` 的案例标签，仍待审核者裁定；实现与测试按审核报告的解释，未改 V5。
* **B-3（真实环境）**：硬链接（`os.link`）与 `fsync` 在测试用 ext4 临时目录上有效（已验证）；`pidfd`、真实 `fork`、`/proc` 读取、真实观察者 / 子进程交互、`run()` 全程**未被任何测试执行**，只能由真实 G0 验证。
* 流水线的耐久性（页缓存与介质）仍属 L-4 的范围。
* 变异检查证明测试对上述 10 类缺陷敏感，但不证明没有其他缺陷。

## 5. 下一步

将本分支交给 ChatGPT / Grok 审核。若通过，下一条唯一指令是：就**真实 G0 执行**向项目负责人另行申请授权（含授权文件的创建、受测子进程的启动）；在得到明确授权之前不得执行。
