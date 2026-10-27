# G0_PREFLIGHT_REVIEW — G0 准备审核后续：纯测试路径审计、阻塞路径分析、预注册偏差处置

**状态：`G0 PREFLIGHT REVIEW COMPLETE / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-G0-PREFLIGHT-001`。审核基准 `d8a07286d74c6d8e81b3b04b62d73a91a25ee610`（ChatGPT：`G0 PREPARATION CONDITIONAL PASS / REAL G0 NOT AUTHORIZED`）。
**本轮没有运行 G0、BV、E1-A、`test_e1a_gate.py`、任何进程级测试，也没有运行新的纯逻辑测试；没有修改冻结 V1（判据 JSON、预注册文本）、台架、G0 实现（`g0_run.py`/`g0_auth.py`/`g0_judge.py`，`g0_code_sha256` 仍为 `29e1253b…`）。** 只执行了 AST 解析、静态审计、哈希与 Git 检查。

## 0. 本轮发现的、与审核任务直接相关的问题（先说）

| # | 发现 | 处置 |
|---|---|---|
| F-8 | `g0_run.py:310` 的 `os.waitpid(rec.pid, 0)` **没有超时**（第 2 部分） | 只记录；修复属 G0 实现改动，须另行授权 |
| F-9 | `max_seconds=20` 只在结束后由 C15 评估，**没有运行期总预算**；不带显式超时的调用（`/proc` 读取、`waitpid`、文件 I/O）不受 20 s 约束（第 2 部分） | 同上 |
| F-10 | 我自己写的未运行测试里有两处缺陷，在审计中发现：① `main()` 拒绝路径测试使用 `/tmp` 下固定文件名，且没有对 `run()` 的保护；② 文件末尾 `unittest.main()` 缺 `verbosity=2`，而既有验收汇总脚本 `summarize.py` 数 `... ok` 行，会把一次全部通过的运行误判为 `FAIL/BLOCKED`（第 1 部分） | **已修复（仅 `tests/test_g0_interlock_and_judge.py`，不属于冻结项或 G0 实现）**，见 diff 与哈希 |
| F-11 | 安全评审 §6 第 1 项写「强于」，措辞过强（第 3 部分） | 本文更正；安全评审原文不改动，保持被审基线 |
| F-12 | （次要）若运行目录在预检与 `os.mkdir` 之间被别的进程创建，`run()` 抛 `FileExistsError`，`main()` 的异常分支会向**该已存在目录**写 `g0_summary.json`。`run_id` 含时间戳 + 3 字节随机数且 `main()` 已预先检查路径，概率可忽略，但行为不正确 | 只记录；修复（仅在本进程创建了目录时才写）属 G0 实现改动，须另行授权 |
| — | 偏差第 6 项（C03 在不完整运行上的处理）改变了可达路径上的裁决 | **REQUIRES V2**（第 3 部分） |

---

## 1. 纯逻辑测试 `tests/test_g0_interlock_and_judge.py`：执行路径静态审计与执行方案

### 1.1 方法与证据

`g0_preflight_review/audit_g0_pure_tests.py`（**只做 AST，不导入被审代码，不启动进程**；`--json` 另存）。输出：`test_static_audit.txt` / `test_static_audit.json`。检查：A 测试文件内的进程相关调用；B 测试调用的 `g0_run` 函数及其调用闭包（含/不含 `main→run` 边）；C 闭包内的进程相关调用；D 各被导入模块的导入期调用；E 测试数。

| 项 | 结果 |
|---|---|
| A. 测试文件内 `fork/kill/killpg/waitpid/wait*/exec*/spawn*/system/popen/Popen/pidfd_*/raise_signal/pthread_kill/setsid/setpgid/_exit/alarm` 及 `run/spawn_direct/release/final_cleanup/Observer/PidfdHandle/node_main…` 的调用 | **0** |
| B. 测试调用的 `g0_run` 函数 | 仅 `main` |
| B. 不含 `main→run` 边的调用闭包 | `main, current, bench_code_hash, git_head, prereg_sha, utc_now, write_json` |
| B. `run()`（唯一会 fork 的函数）是否在语法上从 `main` 可达 | **是**（`g0_run.py:406`），且仅在 `GA.load(...)` 成功与全部 `return 2` 拒绝返回**之后** |
| C. 上述闭包（不含 `run`）内的进程相关调用 | **0** |
| D. 被导入模块（`g0_run, g0_auth, g0_judge, common, registry`）导入期的进程相关调用 | **0**（`g0_run` 的 `subprocess` 仅在 `Guard.install()` 内导入，导入期不执行） |
| E. 测试数 | **46**（`TestInterlock` 14 + `TestJudge` 26 + `TestSourceConstraints` 6） |
| 两个调用 `main()` 的测试是否把 `run()` 换成「一旦被调用就失败」的间谍 | **是**（2/2，`mock.patch.object(g0_run, "run", side_effect=AssertionError…)` + `assert_not_called()`） |

补充：`tools/static_audit.py --dir gate_g0` = 0 违规；台架默认审计 = 0 违规。`g0_auth.py`/`g0_judge.py` 整体没有进程相关调用，因此 `main()`→`GA.load/GA.validate/GA.current_bindings/template` 的路径也无进程调用。

**结论：** 测试代码本身不 fork、不发信号、不 `waitpid`、不做故障注入；唯一的「语法可达」路径是 `main→run`，由三层挡住：① 授权加载必须成功，而测试使用 `TemporaryDirectory` 内的不存在路径（F-10 修复前是 `/tmp` 固定名，理论上可被预先放置一个有效授权文件而越过 ①）；② `run` 被失败间谍替换；③ 执行时叠加既有 `guard_runner.py`（41 个原语陷阱，`os.fork/waitpid/kill/pidfd_*/…`），任何触达都记录并使进程以 3 退出。
**限度：** 静态闭包按「模块内简单名」追踪，不是完备的别名/动态调用分析；因此仍需要 ③ 的运行期守卫，且 Python 层零违规**不**证明内核路径安全。

### 1.2 F-10 的修复（唯一一处改动，仅测试文件）

* `main()` 拒绝路径测试：授权路径改为 `TemporaryDirectory` 内的不存在文件；对 `g0_run.run` 加 `mock.patch.object(..., side_effect=AssertionError)` 间谍，两个调用 `main()` 的测试都有。
* `unittest.main()` → `unittest.main(verbosity=2)`（与既有六个测试文件一致，使 `summarize.py` 能数到 `... ok`）。
* 测试数、被测断言、期望值**不变**；`g0_code_sha256`、台架哈希、判据、预注册哈希不变。

### 1.3 纯逻辑测试执行方案（**本轮不运行**，等待负责人授权）

**授权范围建议：** 仅运行 `tests/test_g0_interlock_and_judge.py` 一个文件，经 `logic_test_results/guard_runner.py`；不得运行 `test_e1a_gate.py`、G0、BV、E1-A、`--execute`；结果目录 `g0_pure_test_results/`（须事先不存在）。

```bash
cd research/mini_mythos/a_predicate_003
R=g0_pure_test_results ; T=test_g0_interlock_and_judge
# 0. 前置条件（任一不满足则不运行）
git rev-parse HEAD ; git status --porcelain                         # = 被授权提交；输出为空
test ! -e AUTHORIZATION_E1A_GATE_G0.json && test ! -e evidence && test ! -e $R
python3 -B gate_g0/g0_run.py --check                                  # authorization_present:false, executed:false；记录绑定
python3 -B tools/static_audit.py ; python3 -B tools/static_audit.py --dir gate_g0 ; python3 -B g0_preflight_review/audit_g0_pure_tests.py   # 均 rc=0
ls /proc | grep -c '^[0-9]' > /tmp/g0pt_before ; mkdir $R
# 1. 执行（逐文件、守卫之下）
( cd tests && PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -B ../logic_test_results/guard_runner.py $T.py ../$R/$T.guard.json ) > $R/$T.output.txt 2>&1
echo $? > $R/$T.exitcode.txt
# 2. 汇总（只读保存的原始文件；沿用已审的 v2 汇总脚本）
python3 -B logic_test_results_rerun1/summarize.py $T $R/$T.output.txt $R/$T.exitcode.txt $R/$T.guard.json
# 3. 后置条件
ls /proc | grep -c '^[0-9]' > /tmp/g0pt_after ; cmp /tmp/g0pt_before /tmp/g0pt_after
git status --porcelain ; python3 -B gate_g0/g0_run.py --check ; sha256sum prereg/e1_provability_table_v1.json
```

**验收条件（全部满足才记 PASS；任何一条不满足 ⇒ 立即停止、保存完整 traceback、区分夹具 / Mock / 台架 / 环境、不要立即修复、不改判据或预注册、报告并等待审核）：**

| ID | 条件 |
|---|---|
| P1 | 退出码 0（守卫违规会使退出码为 3） |
| P2 | 输出含 `Ran 46 tests` 与结尾 `OK`；失败 0、错误 0、跳过 0、期望失败 0、意外成功 0；无 `_FailedTest`（加载错误） |
| P3 | `*.guard.json` 的 `violations` 为空；`trapped_primitives` 与 `logic_test_results_rerun1/*.guard.json` 相同（41） |
| P4 | `summarize.py` 的 `status_by_acceptance_rule = PASS`，且 `pass = 46` |
| P5 | 进程数运行前 = 运行后 |
| P6 | `git status --porcelain` 只多出 `g0_pure_test_results/`；无 `evidence/`、无 `__pycache__`/`*.pyc`、无 `AUTHORIZATION_E1A_GATE_G0.json`、`MANUAL_DISPOSITION_REQUIRED.json`、`_g0_consumed/` |
| P7 | 运行前后 `g0_run.py --check` 的六个绑定值逐项相同；E1-A 预注册 SHA-256 仍为 `e6b7ca5c…`；`g0_criteria_v1.json` 仍为 `4d3acd67…` |
| P8 | 原始输出、退出码、守卫 JSON、汇总 JSON、环境记录（git HEAD、Python、内核、uid、守卫脚本哈希、进程数）全部保存并逐文件哈希 |

**结论的适用范围（必须随结果一并声明）：** 通过只说明 `g0_auth` 互锁、`g0_judge` 判定、G0 源码约束在**手写合成证据**上与作者的期望一致；合成证据编码的是作者对真实证据形状的假设。**不是** G0 真实运行的结果，**不**证明守卫之外的内核路径安全，**不**构成 G1/G2/G3、BV、E1-A 的任何证据。作者与代码同一人，需 ChatGPT 复核断言本身。已知的无害噪声：未关闭文件的 `ResourceWarning`（`source constraints` 测试里的 `open(...).read()`），不是失败条件。

---

## 2. `g0_run.py` 全部阻塞路径：超时上限、最长等待、超时后不误报 PASS

### 2.1 阻塞点清单（行号为当前 `g0_run.py`；台架行号为 `bench/`）

| # | 位置 | 阻塞原语 | 显式上限 | 典型 | 理论最长 | 超时 / 异常后的动作 |
|---|---|---|---|---|---|---|
| 1 | 预检、快照、令牌扫描（`g0_run.py:159,189,229`，`token_scan`，`fd_report`） | 读取 `/proc/*` | **无** | < 0.1 s（约 80 个进程） | 原则上无界（内核/文件系统停顿） | 无超时；挂起 ⇒ 无裁决（见 2.3） |
| 2 | 写文件：`mkdir`、授权副本、授权标记、REG 追加、证据 | 文件 I/O | **无** | ms | 同上 | 同上 |
| 3 | `spawn_direct`→`fork_gated`→`_register`（`g0_run.py:282`） | 无等待（`pidfd_open`、`/proc` 读取、REG 追加） | 观察者侧：无；**子进程侧门等待 `t_gate_max_s=5.0`**（`gate.py:41-61`），超时 `_exit(112)` | ms | 门等待 5.0 s（观察者拖过则子进程自行 112 退出） | 之后 `release` 写门得 `BrokenPipeError`（Python 忽略 SIGPIPE）⇒ 异常路径 ⇒ BLOCKED |
| 4 | 保持循环（`:286-288`） | `serve()` 内 `poll` 切片 0.05 s | `HOLD_S=0.3` | 0.30–0.35 s | 0.35 s（`recv_msg` 2.0 s 上限仅在可读套接字无数据报时才会触发，SEQPACKET 不会） | — |
| 5 | `release`（`:296`） | `os.write(门,1 字节)`；`send_msg` SPEC | 套接字超时 10 s（`proto.py:32`） | ≈0 | 10 s（仅发送缓冲满时；本场景不会） | 异常 ⇒ BLOCKED |
| 6 | READY 等待（`:298`） | `wait_for`→`serve` | **`ready_deadline_s=5.0`** | 数 ms | 5.05 s | `deadline_hits+=["ready"]`，`RuntimeError` ⇒ 异常路径 |
| 7 | 发 `EXIT`（`:304`） | `send_msg` | 套接字 10 s | ≈0 | 10 s（同 5） | 同上 |
| 8 | 退出等待（`:305`） | `wait_for` 轮询 `pidfd` | **`exit_deadline_s=5.0`** | 数 ms | 5.05 s | `deadline_hits+=["exit"]`，异常路径 |
| 9 | **回收（`:310`）** | **`os.waitpid(pid, 0)`（阻塞）** | **无** | ≈0（此时子进程已是 `Z`） | **原则上无界** | **见 F-8** |
| 10 | `/proc` 消失循环（`:314-319`） | `time.sleep(0.01)` 轮询 | **`reap_deadline_s=5.0`** | 数 ms | 5.0 s | `deadline_hits+=["proc_gone"]`，异常路径 |
| 11 | `final_cleanup`（`:322`，`observer.py:456-486`） | `wait_for(not residual, 3.0)`；`serve(0.1)` | `grace=3.0`；循环 `max_rounds=5` 但无新节点时第 1 轮即 `break` | 0.1 s | ≈3.2 s（仅当残留判定非空，如 `/proc` 不可读） | 若遇存活子进程：`pidfd_send_signal` 被守卫陷阱拒绝 ⇒ `GuardViolation` ⇒ C12 FAIL |
| 12 | 令牌扫描、`RUN_END`、S5、`parse_reg`、写证据 | `/proc` 读取、文件 I/O | **无** | ms | 同 1 | 同 1 |
| 子进程侧 | `node_main`（`node.py:50,63`） | 等 `SPEC` ≤10 s；等 `EXIT`/EOF ≤`T_NODE_MAX`=120 s | 有 | — | 观察者退出 ⇒ 控制通道 EOF ⇒ 立即自行退出 | 不依赖观察者继续存在 |

### 2.2 最长等待时间

* **正常（成功）路径**：各阶段都「差一点超时」时，总和 ≈ 0.35 + 5.05 + 5.05 + 5.0 + 3.2 ≈ **18.7 s**（< 20 s），不含 #9 的无界项和 #5/#7 的 10 s 理论项。
* **失败路径**：首次超时即抛出并跳过后续阶段；最长的失败路径是「前两阶段几乎用满、`/proc` 消失循环超时」≈ 0.35 + 5.05 + 5.05 + 5.0 ≈ **15.5 s**，随后只做 ms 级收尾。
* **含理论项**：若 #5/#7 用满 10 s 套接字超时，总时长可超过 20 s，此时 C15 报 BLOCKED（不会 PASS）。
* **无界项**：#1/#2/#12 的 `/proc` 与文件 I/O，以及 **#9 `waitpid`**。

**F-8 — `waitpid(…, 0)` 无超时。** 正常情况下它立即返回：前一步已确认 pidfd 可读（进程已终止）且 S3 看到状态 `Z`。会使它长时间阻塞的情形属于异常环境：外部 `ptrace`/`strace -f` 跟踪该子进程（被跟踪者的退出通知先给跟踪者，真正的父进程要等跟踪者回收）、内核异常。`SIGCHLD` 被忽略的情形由预检拦截（那时 `waitpid` 不阻塞而是 `ECHILD`）。
**F-9 — 没有运行期总预算。** `max_seconds` 只由 C15 在结束后比较；它不会中断任何阻塞调用。判据 V1 与原授权任务里「最大持续时间」的要求，目前靠「分阶段截止时间 + 事后 C15」满足，而不是靠运行期强制。

**建议的实现修复（本轮不做，须另行授权；不改变 V1 判据）：**
1. 回收改为 `os.waitpid(pid, os.WNOHANG)` 轮询，受 `reap_deadline_s=5.0` 约束。与 V1 兼容：仍是对**那一个具体 pid** 的 `waitpid`（V1 第 6 步、C09）；守卫放行条件不变；`judge` 的 C08/C09 已核对——C09 只要求**恰好一次**返回该 pid，返回 0 的轮询调用不违反，C08 只要求所有 wait 调用都晚于 S3 观察。
2. 加入运行期预算检查 `budget()`：每个循环迭代与每个阶段边界检查 `C.mono()-t0 > max_seconds`，超出则记 `deadline_hits+=["total"]` 并抛出（它不能中断阻塞中的系统调用，但与 1 一起把无界项缩到 `/proc` 与文件 I/O）。不使用 `SIGALRM`：G0 禁止 `signal.*` 常量，也要保持零信号。
3. 由负责人决定是否在外层加**操作系统层面**的墙钟保护（例如 `timeout 60 …`）。它向观察者（不是子进程）发信号，属于 G0 范围之外的人工安全网：观察者被终止后没有裁决文件，子进程因控制通道 EOF 自行退出，下一次预检因缺 `g0_summary.json` 而 BLOCKED。**不得**把这种终止当作 PASS 的一部分。

### 2.3 超时后如何保证不误报 PASS

1. **每个有限超时都先写 `deadline_hits` 再抛异常**；所有异常在 `run()` 的 `except BaseException` 中记入 `ev["exception"]`。于是 C15（`deadline_hits` 非空）与 C17（异常非空）至少两条 BLOCKED 类检查失败，且不存在使其为空的路径。
2. **PASS 要求 17 项检查全部通过**，其中 C16 要求六个快照、五个事件时间、登记表、守卫摘要等全部存在；超时跳过的阶段缺失证据 ⇒ UNEVALUABLE ⇒ BLOCKED（`FAIL` 需要证据）。
3. **裁决只在 `main()` 末尾由 `judge()` 一次性计算**，退出码只由裁决决定（PASS 0 / FAIL 1 / BLOCKED 3）；`run()` 在受守卫段之前抛出的异常在 `main()` 被映射为 3，**绝不**映射为 1 或 0。
4. **总时长**由 C15 独立比较 `max_seconds`，即使每个阶段都在各自截止内。
5. **无界挂起（#1、#2、#9、#12）**没有裁决：不会写 `g0_summary.json`，退出码不会是 0（被终止时为信号退出码）；授权标记已在 fork 前写下，登记表缺 `RUN_END`；下一次 G0 的预检因「前次运行目录缺 `g0_summary.json`」而 BLOCKED，直到人工留痕处置。**「没有输出」从不被当作 PASS。**
6. 超时若伴随存活的子进程：不发信号，写 `MANUAL_DISPOSITION_REQUIRED.json`（已验证身份），`RUN_END(cleanup_confirmed=false)`；子进程自行结束（EXIT / 控制通道 EOF / 门超时 / `T_NODE_MAX`）。

**限度：** 以上论证来自代码阅读和本文第 1 部分式的静态检查，未经任何运行验证；#9 的无界性是真实的，不能被论证掉。

---

## 3. 安全评审 §6 六项预注册偏差的处置

处置值：`ACCEPTABLE`（实现与冻结 V1 的判定一致或更严，无需新版本）/ `REQUIRES V2`（改变了可达路径上的裁决或使冻结文本与实现矛盾，须经新版本文件）/ `BLOCKED`（不得执行）。依据优先级：**`g0_criteria_v1.json` 的 17 项判据与裁决规则是裁决的权威；`E1A_GATE_G0_PREREG.md` §3 是程序叙述。** 冻结 V1 一字不改。

| # | 偏差 | 处置 | 依据 |
|---|---|---|---|
| 1 | S1 在 0.3 s 保持期**之后**拍摄（V1 叙述：S1 后保持 0.3 s） | **ACCEPTABLE**（并更正「强于」一词，F-11） | C05 判的是「已登记未释放期间」子进程的状态：`S`、无消息、sid/pgrp 未变、`FIRST_ACTION` 不早于 `RELEASED`——不规定拍摄时点。实现用 `serve()` 在整个保持期排空消息，故累计的消息数 `messages_received` 覆盖整个保持期，状态与描述符取自保持期末。**并非严格更强**：少了「登记后立即」那一个时点样本；但这个时点样本对子进程是否阻塞在门上没有额外判别力（保持期内任何消息都会被累计，静默动作两种拍法都看不到）。V1 叙述自己也有缺口：判据只有一个 S1，若 S1 在保持之前拍，保持期无证据。判据 JSON 未被放宽。建议并入 V2 的叙述文本；若要 belt-and-braces，可在实现里同时拍「登记后」与「保持后」两个快照（超集）。 |
| 2 | 授权标记在 fork **之前**消耗（V1 第 7 步写在末尾） | **ACCEPTABLE** | C02 要求「消耗了一个有效的单次授权」，实现满足且更严：失败的运行同样不能重放，符合「单次使用」。预检不干净时标记**未**消耗（`auth_consumed=False` ⇒ C02 BLOCKED），不会白白烧掉授权。对 PASS 条件无放宽。 |
| 3 | 预检在运行目录创建**之前**（`run_id` 唯一性 = 目录尚不存在） | **ACCEPTABLE** | V1 第 1 步本就把预检排在最前，并把 `run_id` 唯一列入预检；实现直接用「目录不存在」判定，并用 `os.mkdir`（排他）闭合检查与创建之间的竞争——竞争失败 ⇒ `FileExistsError` ⇒ 在受守卫段之前，`main()` 映射为 BLOCKED（3）（该分支的写文件行为见 F-12，概率可忽略）。无裁决类别变化。 |
| 4 | 异常路径写 `RUN_END(cleanup_confirmed=false)`（V1 第 8 步未提） | **ACCEPTABLE** | 不放宽任何判据：C13 要求 `RUN_END` **confirmed**，false 使 C13 失败；C17 因异常失败。它只让登记表生命周期完整（`lifecycle_issues` 对 false 不要求所有节点 `DEAD`），符合台架既有「RUN_END false ⇒ 仍欠恢复」语义。**依赖第 6 项的处理**才能避免它被误读，因此应与第 6 项同入 V2 叙述。 |
| 5 | 令牌扫描标记 = 命令行含 `g0_run.py`（V1 C01 写「bench token」，未定义） | **ACCEPTABLE**（建议并入 V2 定义） | V1 的「令牌」未定义，环境变量方案不可行（`/proc/<pid>/environ` 反映启动时环境，运行时 `os.environ` 修改不可见）。命令行标记是台架既有 `truth.token_scan` 的做法；失败关闭（共享主机上的无关进程会使预检 BLOCKED，不会放行）；观察者自身及全部祖先被排除。C01/C13 另外检查「观察者子进程数」与「`/proc` 枚举完整」。限度：不能发现不带该标记的残留——V1 同样不能。 |
| 6 | C03 在不完整运行上：仅「顺序违规」可判 FAIL，缺失记录一律 UNEVALUABLE | **REQUIRES V2**（须在第一次授权 G0 运行**之前**） | 这是唯一一处**改变可达路径上裁决**的偏差。按 V1 字面：C03 是 FAIL 类，内容含「`DEAD` … `RUN_END` last and unique」；任何超时 / 异常的运行都缺这些记录，C03 就是**可评估的失败**，裁决规则①给出 **FAIL**（优先于 BLOCKED）。而 V1 §3 第 8 步与 §5 写的是「超时或异常：判 BLOCKED」。**V1 自相矛盾**，实现选了第 8 步的读法（BLOCKED）。可达例子：READY 超过 5 s（环境缓慢）——V1 字面 ⇒ FAIL（冤枉被测机制），实现 ⇒ BLOCKED。预注册要求裁决在运行前确定，不能留给实现者解释，所以须用 V2 把它写明：C03 拆成 (a) 顺序 / 完整性违规（FAIL，任何登记表上都可评估）与 (b) 完成性（BLOCKED 类，仅对已完成的运行评估）。 |

**BLOCKED 项：无。** 没有一项使 G0 不得执行的偏差；第 6 项要求在执行**之前**出 V2。

### 3.1 V2 的变更清单（提案；**本轮不创建**）

1. `g0_criteria_v2.json` / `E1A_GATE_G0_PREREG_V2.md`（新文件；V1 两个文件与 `e287b95` 原样保留，V1 哈希 `4d3acd67…` 不变）。
2. 判据：C03 拆分如上；其余 16 项原文保留（C01 增补令牌的定义）。
3. 叙述：并入第 1–5 项的文字对齐（保持期后拍 S1、fork 前消耗授权、预检先于目录创建、异常路径 `RUN_END(false)`、令牌定义）。
4. 如另行授权实现修复（F-8/F-9）：把「回收为对具体 pid 的 `WNOHANG` 轮询」和「运行期总预算」写入 V2 第 6、8 步的叙述（与 V1 兼容，属文字对齐）。
5. 机械影响：`g0_auth.CRITERIA_PATH/PREREG_MD_PATH`、`g0_judge.load_criteria` 默认路径、`test_frozen_criteria_and_prereg_hashes` 需指向 V2 ⇒ `g0_code_sha256` 变化 ⇒ 纯逻辑测试须在 V2 提交之后重跑。**遵守「先冻结后写码」：V2 文件先单独提交，再改代码，再审核。**

---

## 4. 未改动与未运行

没有 fork、没有信号、没有进程级测试、没有 G0 / BV / E1-A / `test_e1a_gate.py`、没有 `--execute`、没有新的纯逻辑测试运行；没有有效的 `AUTHORIZATION_E1A_GATE_G0.json`；台架、`prereg/`、冻结 V1 判据与预注册文本、`g0_run.py`/`g0_auth.py`/`g0_judge.py`、R3 / CPU-001 / CPU-002 / Parcae 均未改动。
