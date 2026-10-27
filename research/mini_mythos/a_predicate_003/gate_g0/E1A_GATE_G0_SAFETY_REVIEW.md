# E1A_GATE_G0_SAFETY_REVIEW — G0 安全条件、环境依赖、失败关闭与残留处理

**状态：`G0 PREPARATION / PENDING CHATGPT REVIEW / G0 NOT TESTED / EXECUTION NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-GATE-PREP-001`。基准 `a7ce70fb71134d1098de7a50ed475b1b1518e64b`。
被审对象：`g0_run.py`（入口）、`g0_auth.py`（互锁）、`g0_judge.py`（纯判定函数）、`g0_criteria_v1.json`（冻结判据）、`E1A_GATE_G0_PREREG.md`（冻结预注册）。**以上任何代码都未运行过；本文是设计层面的安全论证，不是测试结果。**

## 1. 项目负责人七条安全标准 → 机制 → 证据 → 判据

| # | 标准 | 机制（代码位置） | 证据 | 判据 |
|---|---|---|---|---|
| 1 | 未登记子进程不能执行动作 | 子进程 `gate.fork_gated`：先关闭除 {0,1,2,gate_r,ctrl} 外的描述符，再阻塞读门管道；只有恰好 `b"R"` 放行（`gate.gate_wait`）；`REGISTERED` 记录写入后才允许 `release` | S1 快照（保持 0.3 s 后）：子进程状态 `S`、无消息、sid/pgrp 未变、门管道仅一个只读描述符；`FIRST_ACTION` 时间不早于 `RELEASED` | C04 C05 C06 C07 |
| 2 | 仅已登记节点获得 RELEASE | G0 只创建一个节点；`spawn_direct(hold_release=True)` 把「登记」与「放行」拆成两步，放行由 G0 入口显式调用 `obs.release(rec)`，且仅当 `rec.state == "REGISTERED"`（`observer.release` 自带检查）；放行字节写入前后由 `os.write` 守卫记录时间 | `release_byte_pre_write_monos` 恰好 1 项；链 REGISTERED ≤ RELEASED ≤ 放行字节 ≤ FIRST_ACTION | C07 |
| 3 | 清理不得影响无关进程 | G0 **没有任何信号能力**（见 §2）；没有 `killpg`/`pkill`/按名清理；`final_cleanup` 仅在子进程**已退出且已回收**之后调用，此时 `kill_registered` 看到 pidfd 可读，只返回 `already_exited`；令牌扫描仅诊断 | 守卫违规列表为空；清理条目全为 `already_exited` | C12 C13 |
| 4 | 每个启动的进程都有明确的结束与回收证据，否则 BLOCKED | 退出（pidfd 可读 + `/proc` 状态 `Z` + ppid=观察者，且在任何 wait 之前）与回收（`waitpid(具体 pid)` 返回该 pid；其后 `/proc/<pid>` 消失）分别带时间戳；`EPIPE` 或 `/proc` 消失本身不当作清理证明 | S3、S4 快照，`waitpid_calls`，`proc_gone_mono` | C08 C09 C10 |
| 5 | 无无法解释的残留或悬挂票据 | 本测试不创建票据（登记表中恰好一个 `creator="O"` 的节点）；`verify_run_set` 核对运行集合；S5 快照检查子进程、令牌残留、`/proc` 枚举完整性；`DEAD` 须带依据；`RUN_END.cleanup_confirmed` | S5、`DEAD.basis`、`RUN_END` | C11 C13 |
| 6 | 证据绑定 Git SHA、预注册哈希、台架代码哈希 | `g0_auth.validate`：授权须逐项等于当前 `git_head`、E1-A 预注册、G0 判据、G0 预注册文本、台架代码、G0 代码哈希；运行开始与结束各算一次，必须相等 | `bindings_start == bindings_end == authorization.bindings` | C02 |
| 7 | 退出码 0 不掩盖异常 | 裁决由 `g0_judge.judge()` 对完整证据计算；任何异常、中止原因、超时、缺失证据都使裁决不是 PASS；退出码仅是裁决的函数（PASS 0 / FAIL 1 / BLOCKED 3），`run()` 之前的异常一律映射到 3 | `g0_summary.json` | C15 C16 C17 |

## 2. 零信号如何保证（以及它不能保证什么）

* **代码层：** `g0_judge.py`、`g0_auth.py` 不含任何进程相关调用；`g0_run.py` 中唯一的进程原语调用是 `os.waitpid(rec.pid, 0)`（一处）。`tools/static_audit.py --dir gate_g0`（G0 配置：`fork/kill/killpg/pidfd_send_signal/exec*/spawn*/_exit/pidfd_open/setsid/setpgid` 全部禁止调用、禁止 `signal.SIG*` 常量、`waitpid` 仅限 `g0_run.py`）当前为 **0 违规**；对台架本身的默认审计也仍为 **0 违规**（审计工具扩展不改变默认行为）。
* **运行层（Python 守卫，`g0_run.Guard`）：** 在 `fork` 之前安装，替换 `os.kill/killpg/system/popen/exec*/spawn*/posix_spawn*/forkpty/wait/wait3/wait4/waitid`、`signal.pidfd_send_signal/raise_signal/pthread_kill`、`subprocess.*` 为**记录并拒绝**的陷阱；`os.fork` 计数且第 2 次拒绝；`os.waitpid` 只放行等于那一个子进程 pid 的正整数；`os.write` 仅用于记录放行字节的前置时间。
* **台架里仍存在的信号路径：** `observer.kill_registered` / `kill_unregistered_direct` 经 `PidfdHandle.send` 调用 `signal.pidfd_send_signal(SIGKILL)`。G0 通过两层避免触发：① 只在子进程已退出并回收后才调用 `final_cleanup`，此时这些函数走 `already_exited` 分支；② 即使被触发，守卫的 `pidfd_send_signal` 陷阱会拒绝并把违规记入证据（C12 ⇒ FAIL）。异常路径**不**调用 `final_cleanup`。
* **限度（必须明说）：** Python 层陷阱记录为零**不能**证明所有内核路径都安全——C 扩展、`ctypes`、直接 syscall 不经过这些名字。靠的是：只导入标准库与台架模块、AST 审计禁止 `ctypes/subprocess/multiprocessing/threading` 导入（`subprocess` 仅在 `g0_run.py` 内被陷阱替换）、以及判定中对 `/proc` 的独立观察（子进程数、残留）。

## 3. 环境依赖

| 依赖 | 要求 | 不满足时 |
|---|---|---|
| Python | 3.13.16，且以 `python3 -B` 运行（否则会写 `__pycache__` 改动代码目录） | 预检 ⇒ `C01` BLOCKED，不 fork |
| 内核 | `pidfd_open`（≥5.3）、`socket.send_fds`、AF_UNIX `SOCK_SEQPACKET`；当前 6.18.44-fc-v165 | 预检 BLOCKED |
| 权限 | 同一 uid 即可（`/proc/<pid>/fd`、`fdinfo` 对自己的子进程可读）；不依赖 root、cgroup、proc connector、网络、GPU | `fd` 读取失败 ⇒ 相应证据缺失 ⇒ UNEVALUABLE ⇒ BLOCKED |
| 信号配置 | 观察者的 `SIGCHLD` 未被忽略（否则子进程被自动回收，`waitpid` 得 `ECHILD`） | 预检 BLOCKED |
| 祖先进程 | 启动 G0 的 shell/包装进程的命令行可能含 `g0_run.py`；令牌扫描**排除观察者自身及其全部祖先** | 非祖先的同名进程 ⇒ 预检 BLOCKED（失败关闭） |
| `/proc` | 完整可枚举；任何条目不可读 ⇒ 枚举不完整 | `C01`/`C13` BLOCKED |
| 磁盘 | `evidence/g0_<run_id>/` 可创建；`.gitignore` 目前不忽略 `evidence/`，但执行后提交证据前须 `git check-ignore` 验证 | 创建失败 ⇒ 预检前异常 ⇒ BLOCKED（退出码 3） |

## 4. 失败关闭行为

| 情形 | G0 的行为 | 裁决 |
|---|---|---|
| 授权文件缺失 / 格式错 / 哈希绑定不符 / 已消耗 / 过期 / stage 不是 G0 / grants 不精确 | 入口在任何文件写入、任何进程动作之前 `REFUSED`，退出码 2 | NOT TESTED |
| 预检不干净 | 运行目录已建（保存证据）但**不 fork**，授权**不**消耗 | BLOCKED |
| 授权标记写入 | 在 fork **之前**（`O_EXCL` 创建）——即使之后失败也不能重放 | — |
| 登记失败 | `observer._abort` 写 `ABORTED` 并向门写 `A`（子进程以 111 退出）；G0 不再继续；如该进程仍活着，写 `MANUAL_DISPOSITION_REQUIRED.json`（身份未验证、从未被发信号） | BLOCKED（或有证据的 FAIL） |
| 保持期内子进程有动作 | G0 停止，不放行；放行门保持，观察者退出时门 EOF ⇒ 子进程 111 退出 | FAIL（C05，有证据） |
| READY / 退出 / `/proc` 消失 超过 5 s | 记 `deadline_hits`，停止，**不发信号**，列出已验证身份写入 `MANUAL_DISPOSITION_REQUIRED.json` | BLOCKED |
| 任何其他异常 | 完整 traceback 入证据；`RUN_END(cleanup_confirmed=false)` 如实写入；不调用 `final_cleanup`；不发信号 | BLOCKED |
| 守卫拦截到任何违规调用 | 抛 `GuardViolation`，违规入证据 | FAIL（C12，证据已确认） |
| 观察者在释放前死亡 | 门管道 EOF ⇒ 子进程 111 退出（这是协议的一部分，**不是**本轮要测的内容，属 G1/G3） | — |

## 5. 残留处理

* G0 **从不**向任何进程发信号，也不会按名称/命令行/进程组清理。
* 子进程自身的结束机制（依次生效）：控制通道 `EXIT` 消息；观察者退出 ⇒ 控制通道 EOF；门超时 5 s（尚未放行时）；`T_NODE_MAX`=120 s。
* 若运行后仍有存活的 G0 子进程：`MANUAL_DISPOSITION_REQUIRED.json` 列出 `pid/starttime/node_id` 与「如何结束」；**由人决定**。下一次 G0 的预检会因「前次运行目录缺 `g0_summary.json` 或含 `MANUAL_DISPOSITION_REQUIRED.json`」而 BLOCKED，直到人处理并留痕。
* 已退出但未被回收的子进程（异常路径）在观察者退出后由 init 回收；这一情形在证据中以 S3/S5 状态可见。

## 6. 与冻结预注册文本的差异（须审核者知悉）

实现时有六处与 `E1A_GATE_G0_PREREG.md` 第 3 节的字面步骤不同。它们都使检查**更严**或**更诚实**，没有一处放宽判据；`g0_criteria_v1.json` 的 17 项判据一字未改（哈希 `4d3acd67…` 不变）。若审核者认为需要把这些写回预注册，应走 v2 文件，而不是改冻结文件：

1. **S1 在保持期之后拍摄**（预注册写作「S1 快照后保持 0.3 s」）。这样 S1 证明的是「保持 0.3 s 之后仍未动作」，强于「拍摄瞬间未动作」。
2. **授权标记在 fork 之前消耗**（预注册第 7 步写在末尾）。更严：失败的运行也不能重放。
3. **预检在运行目录创建之前**执行，`run_id` 唯一性即「目录尚不存在」。
4. **异常路径写 `RUN_END(cleanup_confirmed=false)`**，使登记文件生命周期完整，不让「缺 RUN_END」被误判为协议违规。
5. **令牌扫描标记是命令行含 `g0_run.py`**：`/proc/<pid>/environ` 反映的是进程启动时的环境，运行时 `os.environ` 的修改不可见，所以环境变量令牌不可行。
6. **C03 在不完整运行上只允许因「顺序违规」判 FAIL**，缺失记录一律 UNEVALUABLE（遵循「FAIL 需要证据」）。

## 7. 已知发现与待审核者决定

* **F-1（沿用库存）：** `observer._confirmed_dead` 对已登记节点用 `process_is_dead`，把僵尸 `Z` 当作已死。对直接子进程而言这是「已退出、未回收」，不是「已回收」。台架**未修改**（修改会改变代码哈希，使 172 项纯逻辑测试证据失效）。G0 用 C08/C09/C10 单独证明退出≠回收。是否在 G1 之前修台架由审核者决定。
* **F-4（新，桌面核对）：** `final_cleanup` 自带 SIGKILL 能力（见 §2）。G0 的两层规避已就位，但这条路径本身属于 G3 的被测对象，G0 不应依赖它。建议审核者确认「仅在已回收后才调用」这一条件在代码中确实无旁路（`g0_run.run` 中 `final_cleanup` 紧随 S4，位于同一 `try`，任何前序异常都跳过它）。
* **F-5（新）：** `g0_run.Guard` 的 `os.write` 包装对所有 `os.write` 调用多一次整数比较；仅在 `watch_fd` 非空时做字节比较。影响可忽略，但属于被测路径上的插桩，须在报告中披露。
* **F-6（新）：** 令牌扫描读取全部 `/proc/*/cmdline`；在共享主机上可能因无关进程名含 `g0_run.py`（如 `grep`）而 BLOCKED。失败关闭，不会放行。
* **F-7（新）：** `tests/test_g0_interlock_and_judge.py` 已写但**未运行**（本轮只允许静态检查）。其中的合成证据是手写的，需在首次受控运行之前由获得授权的纯逻辑测试执行验证。

## 8. 本轮没有做的事

没有 fork、没有创建进程、没有发送信号、没有运行 `test_e1a_gate.py` 或任何进程级测试、没有 BV、没有 E1-A 单元、没有 `--execute`、没有创建有效的 `AUTHORIZATION_E1A_GATE_G0.json`、没有修改冻结预注册 / R3 / CPU-001 / CPU-002 / Parcae / `bench/` / 既有 `tests/`、没有 GPU / 训练 / 真实 D1。
