# F3B-D1-A-CPU-003 E1-A — 检查点：静态审核修复 STATIC-FIX-001（未执行）

**状态：`E1-A STATIC FIX COMPLETE / PENDING CHATGPT RE-REVIEW / EXPERIMENT NOT TESTED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

ChatGPT 对提交 `3b9414a5d937c2a764bb4ef0ff4452c147e6d8d6` 的结论：`PREREGISTRATION ACCEPTED / BENCH STATIC REVIEW FAIL / EXPERIMENT NOT TESTED`。本轮只修复四项缺陷并核查 `/proc` 枚举不完整时的 BLOCKED 判定。**没有运行任何台架代码或测试；没有 fork、没有信号、没有 BV 故障注入；预注册未改动。**

## 1. Git 与范围

| 项 | 内容 |
|---|---|
| 分支 | `d1-r3-a-cpu-003-e1a-prep-20261027`（开始前远端 HEAD = 本地 HEAD = `3b9414a5d937c2a764bb4ef0ff4452c147e6d8d6`，工作树干净） |
| 修复提交 | `9ab867305652f02acc1117cb89337e623e7ba790`（台架 + 测试）；本检查点所在的文档提交紧随其后（最终哈希见交付报告） |
| 预注册 | `prereg/e1_provability_table_v1.json` SHA-256 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`，**与 `f9d3cd8` 相同，未改动**；侧文件未改 |
| 改动范围 | 仅 `bench/`（10 个文件）与 `tests/`（4 个文件，其中新增 `test_e1a_staticfix.py`）；此外仅本检查点与三个索引文件的插入式块。基线之外的其它路径：无 |
| 冻结/证据对照 | 相对基线，CPU-001/002、`gate3_d1`、`interfaces`、`scripts`、`prereg` 的 `git diff --stat`：空（无差异） |
| `STATIC_REVIEW.md` | **未改**；它描述的是 `3b9414a` 版本，其中的文件哈希表已过期，当前哈希见第 7 节 |

## 2. 缺陷一：unsafe 事件优先于台架 BLOCKED；候选自身异常不得记为台架 BLOCKED

**根因。** `truth.judge()` 先检查 `bench_reasons` 再检查 unsafe：任何同时成立的台架原因（拓扑不符、节点意外死亡、S0 结果丢失）都会把已确认的 unsafe 事件盖成 BLOCKED。`sup_stub` 把候选逻辑内的异常与台架导入失败混在同一个 `try` 里，`trial` 又把它记为 `bench.append("CANDIDATE_RAISED")`，使机制自身崩溃变成台架 BLOCKED。另外事件只在 `S0_RESULT` 里一次性返回——桩在 unsafe 调用后死亡，证据就丢了。

**修改位置。**
- `truth.judge`：新的优先级 ① 已确认 unsafe → FAIL（同时成立的台架原因保存在 `suppressed_bench_reasons`）② 台架原因 → BLOCKED ③ 候选异常 → FAIL ④ 无输出 / 证据不足 → BLOCKED ⑤ 冻结的第 3–5 步。“已确认”＝由已验证到位的插桩看到（`instrumentation_ok`：安装时包装齐全、候选模块尚未导入、S0 时包装仍有效）；插桩不可信则 unsafe 不算确认 ⇒ BLOCKED。新增 `truth.merge_events`。
- `sup_stub.ev()`：S0 阶段、非 infra 的 unsafe 调用在**调用之前**经控制通道发出 `EVENT` 消息；`trial.run_trial` 把该实时流与结果日志按 `seq` 合并。
- `sup_stub.main`：导入候选模块与读预注册移到 S0 之前的 `candidates.prepare_candidate()`，失败 ⇒ `CANDIDATE_LOAD_FAILED`（台架）；S0 内候选逻辑抛出的异常 ⇒ `candidate_exception`。
- `trial`：候选异常不再进入 `bench_reasons`，作为参数交给 `judge`。
- `common.UNSAFE_CALLS`：stub 与 truth 共用同一集合。

**预期效果。** 已确认的 unsafe ⇒ FAIL，不论拓扑 / 清理 / 结果丢失；候选崩溃 ⇒ 该单元 FAIL 并保留回溯；台架自己的缺陷仍 BLOCKED（台架原因先于候选异常）。

**判断点（请审核者确认）：** 冻结预注册的判定函数把“台架不可验证 ⇒ BLOCKED”写在第 1 步、“不安全事件 ⇒ FAIL”写在第 2 步，但第 2 步同时写明 *regardless of anything else*。本次实现按“已确认的 unsafe 优先”解读，与审核指令一致；**未改预注册文本**。候选异常 ⇒ FAIL 是对“候选未产生任何机制状态”的保守处理，不是预注册里的显式条文。

## 3. 缺陷二：登记状态改变不得解除清理责任

**根因。** `observer.residual()` 只看状态为 `REGISTERED/RELEASED` 的节点，`ABORTED` 或登记失败（`rec.pid` 为空）的节点被当作不存在；`mark_dead` 同理。`registry.cleanup_targets()` 排除 `ABORTED`。结果：已 fork、尚未确认退出的进程可以不在残余集合里，清理被报告为成功，RUN_END 也会写出。

**修改位置。**
- `registry`：新增 `FORKED` 记录（pid 一知道就写）；`cleanup_targets` 不再排除 `ABORTED`，只有 `DEAD` 才解除；新增 `unresolved_forked()`（已 fork 但未登记、未确认死亡）与 `last_run_end()`；`check_order` 检查 `FORKED` 先于 `INTENT` 的违规。
- `observer`：`NodeRec.forked_pid/forked_starttime`，`_note_forked()` 在 `spawn_direct` 与 `_on_created` 登记之前写 `FORKED`；`_confirmed_dead()` 只在**有正面证据**时为真（已登记按登记身份；未登记按 pid + 起始时间，`/proc` 不可读 ⇒ 未确认；起始时间未知而同 pid 仍存活 ⇒ 未确认）；`residual()`、`residual_detail()`、`mark_dead()`（只对已确认的写 `DEAD`）、`finish_cleanup(nodes)`、`kill_unregistered_direct()`（只对观察者自己的、未回收的直接子进程经 pidfd 发 SIGKILL）、`reap_direct`、`run_level_nodes()`。身份未验证的非直接子进程**绝不发信号**，保持残余 ⇒ `cleanup_ok=False` ⇒ `RunAbort`。
- `janitor.run_cleanup_full` / `unresolved_report`：ABORTED 但已登记且无 `DEAD` 的节点仍是目标；FORKED-only 节点只报告 `alive`，不发信号。

**预期效果。** 登记失败、ABORTED、`/proc` 不可读都不会让清理被误报为完成；残余在确认死亡前一直计入。

## 4. 缺陷三：RUN_END 与 Janitor 退出条件

**根因。** 运行器的 `finally` 无条件写 `RUN_END`；janitor 看到 `RUN_END` 就“无动作”退出，观察者异常退出但已写 `RUN_END` 时也不清理；寿命上限 900/3600 s 到期时静默 `LIFETIME_CAP_NO_ACTION`；清理中途失败仍返回 0。

**修改位置。**
- `e1a_runner.execute`：`finally` 中先对**整个运行**的所有节点（除 janitor）做 `finish_cleanup`，再做仅诊断的令牌扫描，然后写 `RUN_END{cleanup_confirmed, residual, token_residue, token_scan_problems}`。残余、未登记的令牌进程、扫描时 `/proc` 不可读，任一成立 ⇒ `cleanup_confirmed=False`。之后等待 janitor（未确认时最长 40 s），记录 `janitor_exit`；摘要新增 `cleanup_confirmed`、`recovery_open`、`final_residual`，`recovery_open` 时返回码 3。
- `janitor.decide()`（纯决策）：无 `RUN_END` 且观察者存活 ⇒ WAIT；观察者已死 ⇒ CLEANUP；`RUN_END` 的 `cleanup_confirmed` 不是 `True`（含缺失 / 字符串）⇒ CLEANUP；声称 `True` 时仍**只读复核**，登记节点仍存活或有存活的未解决进程 ⇒ CLEANUP；否则 EXIT_CONFIRMED。`cleanup_until_clear()` 反复清理直到确认，否则 `EXIT_INCOMPLETE=4`。删除了静默退出路径与观察者存活时的寿命上限。

**预期效果。** 异常退出、清理不完整都不会提前解除恢复责任；`RUN_END` 的“成功”声明必须经 janitor 复核。

## 5. 缺陷四：BV 与单格测试必须可独立授权

**根因。** `--execute` 无论 `--only`/`--reps` 如何，都先无条件运行 `validity.run_all`（BV-1/2/3/6/7，含 fork、观察者死亡模拟、SIGKILL），所以“单格冒烟”会隐含执行未授权的故障测试；授权文件只是一个哈希加一个 `scope` 子串。

**修改位置。**
- 授权模式 `e1a-auth-2`：必须 `authorized_by=owner`、`prereg_sha256`、**`bench_code_sha256`**（绑定被审核的代码修订）、`phases`：`BV-SELFTEST{checks:[...]}` 与 `E1A-CELLS{cells:[...]|"ALL", max_reps, sweep}`。
- `e1a_runner.build_execution_plan()`（纯函数）：`--execute` 必须显式 `--phase bv|cells`。`bv`：必须显式 `--bv` 列表且每个 id 都被授权，不带任何单元选项，**不运行任何单元**；`cells`：必须显式 `--only`（或被授权的 `--all-cells`）与 `--reps`（≤ `max_reps`），扫描仅在授权时可选，**不带 `--bv`，不运行任何 BV**。
- `validity.run_all(obs, dir, only)`：`only` 必填，不存在隐含的“全部”；`RUN_LEVEL_IDS`、`FAULT_INJECTING` 标明哪些检查注入故障。
- 单元结果是否“计数”：需 `--bv-evidence`（先前被授权的 BV 运行产出的 `validity.json`，且预注册哈希、代码哈希、五项检查全部通过且全部执行过）；否则摘要为 `SMOKE - not counted`。BV-only 运行摘要为 `NO CELLS RUN`。
- 每次试验内的 BV-4/5/8/9/10 是对活动进程的只读核对，随单元运行，不属于运行级故障注入。

**预期效果。** 单格参数不会触发 BV；BV 需逐项授权；授权随代码修订失效。

## 6. `/proc` 独立真值枚举不完整

- 观察者侧：`trial._pre_s0` / `_post_s0` 对 `scan_proc()` 返回的 `problems` 调用 `truth.enumeration_reasons` ⇒ 台架 BLOCKED（此前被静默忽略，清洁场景里被漏掉的子进程会得到“拓扑如设计”的假象）。
- 候选侧：P2 的输出新增 `enumeration_complete`；`judge` 在 `enumeration_complete is False` 或 `unknown_reasons` 含枚举标记时判 BLOCKED（`EVIDENCE_INSUFFICIENT`），因此既不会因 UNKNOWN 在 UNPROVABLE 单元上得到“确定 PASS”，也不会因漏检缺陷得到错误的机制 FAIL。unsafe 事件仍优先。
- 仍保持：`listdir` 失败 ⇒ `ProcUnreadable` ⇒ 台架 BLOCKED；令牌扫描 `/proc` 不可读 ⇒ `cleanup_confirmed=False`。

## 7. 本轮实际执行 / 未执行

已执行（均只读，不启动进程）：AST 解析；`tools/static_audit.py`（0 条违规）；`tools/check_prereg_schema.py`（ok=True）；`e1a_runner.py --check`（ok=True，`bench_code_sha256` `bae25cedb72bcafe6002c2f8207354c2f4aeb59a017653721b571a216d3bef9d`）；AST 版 lint（lint findings: 0）；文件哈希与 Git 检查。

**尚未执行（全部只写不跑）：**
- `tests/test_e1a_staticfix.py`（新增，纯逻辑 + 对 `/proc`、pidfd 的 mock）：`TestFix1UnsafePriorityAndCandidateException`、`TestFix2RegistryResponsibility`、`TestFix2ObserverResidual`、`TestFix3RunEndAndJanitor`、`TestFix4Phases`、`TestEnumerationIncomplete`。
- `tests/test_e1a_gate.py`（进程级）：新增 `TestStaticFixProcessPaths`（登记失败后仍保留清理责任直到确认死亡；`RUN_END` 未确认时 janitor 清理；janitor 不信任虚假的确认）；原有门协议 / BV / 单次试验冒烟测试均未运行。
- `tests/test_e1a_logic.py`、`test_e1a_runner_interlock.py`（已按新语义更新）。
- 运行级 BV-1/2/3/6/7 与任何 E1-A 单元：NOT TESTED；E1-B/C/D/E2/E3、真实 D1、GPU：未触及。

## 8. 修改后文件哈希

| 文件 | SHA-256 |
|---|---|
| `bench/candidates.py` | `353978ac5277f8a79b9e8845eb269407c65205c0d086f57005685549a3140dab` |
| `bench/common.py` | `bc87edb1c41cbe88d13e4e3835b0526d3b4006f5f2038963034fcbe48707e700` |
| `bench/e1a_runner.py` | `0632aacdc36b6a073f2853d20abad6a2553af05160e51bf50b888a7794dce2ea` |
| `bench/janitor.py` | `1ace7f79d57c535f1de687a9c86b5a52f9987def3fbbff0f3427c4a5b70e89b9` |
| `bench/observer.py` | `47188cc6901fb6bf6047119413e10ede2a4c59d257242e9d7e3db878a16e79a7` |
| `bench/registry.py` | `92134496db6001844843bb4f4e644c3f942562a0e2b022ca5746db18e211bc20` |
| `bench/sup_stub.py` | `5bdd5ad9f6599b90d7c73e991d316ec462be227d19ac2d15a8bc017994aa18cb` |
| `bench/trial.py` | `3c2be02cecaa401a7a47d5574ec03083b018540ca3eb5582aa1f88902831da1a` |
| `bench/truth.py` | `6e0b7c39889b19f134633b1f131d43aa668af1e57cb42edcc8097461da2e634a` |
| `bench/validity.py` | `e4b79126b1229b9f831001a4c2355b26dc748e354eb27542dee05ac15f17f6bb` |
| `tests/test_e1a_gate.py` | `589fe2452c8d10faec749a9ff72f0de174489a87a9d7466f4dbd8023495acf5e` |
| `tests/test_e1a_logic.py` | `6ecbd9db9cab2127f12a2c11728a64e0794272e25298a95464d6fb5bda104317` |
| `tests/test_e1a_runner_interlock.py` | `7dc44da46668fbb460204287e4945706602b91750bf0af9132b3027b72da9e33` |
| `tests/test_e1a_staticfix.py` | `4547b4b14272444694f0939c1871a854d87472915d72e9ce3fea5247da59c567` |

## 9. 完整性检查

| 项 | 结果 |
|---|---|
| 冻结 R3 / 决定记录 / 冻结记录 | 前缀 `66a656145fc203c7…` / `6209602e7d51b1ae…` / `e3bba6b0968101bf…` 均核对一致 |
| `D1_CODE_SHA256SUMS` | 10/10 OK |
| 预注册文件与侧文件 | SHA-256 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`，无 diff |
| CPU-001/002 代码与证据、Parcae、真实 D1 | 无 diff / 未触碰 |
| `__pycache__` / `.pyc` | 未提交（已清理，且被 `research/mini_mythos/.gitignore` 忽略） |
| 推送后远端树 | 见交付报告（逐文件 blob 比对） |

## 10. 剩余风险

1. **全部进程级路径仍从未执行**，新增的 `FORKED`/`DEAD` 记录、janitor 重试、`EVENT` 流、授权阶段都是新代码，可能含台架缺陷；新测试同样未跑。
2. “已确认 unsafe 优先”与“候选异常 ⇒ FAIL”是对预注册第 1/2 步顺序的解读与保守补充，需 ChatGPT 确认（第 2 节）。
3. 插桩只覆盖 Python 层的 `os.kill/killpg/wait*` 与 `signal.pidfd_send_signal`；候选若经 `ctypes` 直接调用 libc 的 `kill`/`wait` 不会被看见（既有限制）。
4. 由第三方创建者 fork、但 `CREATED` 消息从未到达观察者的进程，观察者不知道其 pid，只能由谱系对账 / 令牌扫描（仅诊断）发现（ERRATA-002 R1/R5 的既有残余）。
5. 身份无法确认的进程不会被任何组件发信号，只会让 `cleanup_confirmed=False`、`recovery_open=True`，需人工处理；janitor 与观察者同时失效仍无自动清理（R2）；pid 复用且起始时间相同的概率极低但非零（R3）。
6. 授权绑定代码哈希：此后任何代码修改都使既有授权失效（有意为之）。
7. 观察者侧枚举不完整现在是 BLOCKED：若环境中 `/proc` 条目不可读（如 `hidepid`），会提高台架 BLOCKED 率；当前环境 uid 0，预计不受影响，未实测。

## 11. 下一条唯一指令

把最小代码修复（提交 `9ab867305652f02acc1117cb89337e623e7ba790` 及本检查点）提交给 ChatGPT 复核。**未经项目负责人另行授权，不运行任何 CPU-003 进程级测试**；首次受控运行须以 `e1a-auth-2` 授权文件分阶段、逐项授权。

R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；G3～G6 NOT TESTED；NO A-B WINNER；Grok：CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED。
