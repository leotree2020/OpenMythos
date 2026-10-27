# F3B-D1-A-CPU-003 E1-A — 检查点：最终执行边界修复 STATIC-FIX-002（未执行）

**状态：`E1-A STATIC FIX-002 COMPLETE / PENDING CHATGPT REVIEW / EXPERIMENT NOT TESTED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

ChatGPT 第二轮静态审核（HEAD `452897c32c4f09bec86578b86906bc2bdabdce86`）：`STATIC REVIEW FAIL — CROSS-MODULE SAFETY ISSUES`。本轮只处理 FIX-002-A / B / C，未重新设计 E1-A，未改冻结预注册，未扩展候选机制。**没有运行任何台架、BV、E1-A、故障注入或测试；没有 fork、没有信号。**

## 1. Git 与范围

| 项 | 内容 |
|---|---|
| 分支 | `d1-r3-a-cpu-003-e1a-prep-20261027`（开始前远端 HEAD = 本地 HEAD = `452897c32c4f09bec86578b86906bc2bdabdce86`，工作树干净） |
| 修复提交 | `62f3ba701f36f2e330d2f42d75d8c3a36c6194e1`（台架 + 测试）；本检查点所在文档提交紧随其后（最终哈希见交付报告） |
| 预注册 | SHA-256 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`，与 `f9d3cd8` 相同，未改 |
| 改动范围 | 仅 `bench/`（`e1a_runner`、`janitor`、`observer`、`registry` 修改，`evidence` 新增）与 `tests/`（`test_e1a_staticfix.py` 适配，`test_e1a_staticfix2.py` 新增）；另有本检查点与三个索引文件的插入式块。基线之外的其它路径：无 |
| 冻结/证据对照 | CPU-001/002、`gate3_d1`、`interfaces`、`scripts`、`prereg` 相对基线 `git diff --stat`：空（无差异） |
| 旧文档 | `STATIC_REVIEW.md` 与 STATIC-FIX-001 检查点未改（历史记录）；当前哈希见第 6 节 |

## 2. FIX-002-A：最终清理集合一致性

**修复前。**
- `execute()` 的 `finally` 取**一次**节点快照 `run_level_nodes(jid)` 后清理；清理期间观察者仍在 `serve()` 中接受 `TICKET`/`CREATED`，此后出现的节点既不在快照里、也不在残余里。
- `RUN_END` 写出前没有重新核对节点集合与登记文件；`cleanup_ok` 只回答“快照里的节点是否死亡”。
- `recovery_open` 只有在 `not confirmed` 时才可能为真；janitor 在 5 s 内没退出就被 `kill_registered(only=jid)` 强制杀死，哪怕它还在承担恢复责任；janitor 中途异常退出时 `confirmed=True` 的运行仍可能报告恢复已关闭。

**修复后（`observer.py`、`e1a_runner.py`）。**
- **入口关闭：** `close_intake()` ——新的 `TICKET` 一律 `TICKET_DENIED`（不建节点、不写 INTENT）；已发放但尚未报告的票据（状态 INTENT）被**撤销**（写 ABORTED，门上写中止字节，子进程自行退出）。撤销后才到达的 `CREATED` 仍写 `FORKED`、回 `REGISTER_FAILED`，该 pid 保持残余直到确认死亡，**不登记、不放行、不发信号**。
- **不依赖快照：** `finish_cleanup(nodes)` 的 `nodes` 可为可调用对象，每一轮清理前、后以及取最终集合时都重新求值；若一轮中出现新节点则再来一轮（最多 5 轮）。`cleanup_ok` 需要“最终集合残余为空”**且**“集合稳定”（最后一轮无新增）；不稳定即使无存活进程也不算清理成功。
- **RUN_END 前核对：** `verify_run_set()` 检查节点编号 1..counter 是否都有记录、登记文件与内存写入是否一致（条数、解析问题、完整性问题、文件里出现内存不认识的节点）、是否仍有待决票据、非排除节点是否均已确认死亡；`final_cleanup()` = 入口关闭的不动点清理 + 该核对，任一不成立则 `cleanup_ok=False`，`RUN_END.cleanup_confirmed=False`（并记录 `run_set_consistent/run_set_problems`）。
- **recovery_open / janitor：** 纯函数 `recovery_state()`：仅当“清理已确认 + 无残余 + 令牌扫描干净且完整 + janitor 已启动、不再运行、退出码为 0（或在责任完全解除后由我们停止）”才为 False；其余任何情形（含 janitor 退出码 ≠ 0 / 未知）均为 True。`may_stop_janitor()` 纯函数：只有责任完全解除才允许停止仍在运行的 janitor，否则**不杀**，标记 `BLOCKED: RECOVERY DELEGATED TO THE STILL-RUNNING JANITOR`；janitor 已退出但恢复未关闭则 `BLOCKED: MANUAL DISPOSITION REQUIRED`，并写 `MANUAL_DISPOSITION_REQUIRED.json`（残余的 pid/起始时间、janitor 日志路径）。`recovery_open` 时实验判定为 `BLOCKED - recovery responsibility still open`，返回码 3。
- 试验循环每次先检查 janitor 仍在运行，否则 `RunAbort`（恢复保护已丢失）。

## 3. FIX-002-B：登记文件完整性

**修复前。**
- janitor 忽略 `parse_reg` 返回的 `missing / corrupt_lines / torn_tail`：缺失文件 ⇒ “没有目标”；撕裂末行被默默丢弃；损坏行被计数但无人读取。
- `parse_reg` 接受任意 JSON：非对象行（如 `[1]`）或缺 `kind` 的对象会在 `fold()` 里抛 `AttributeError/KeyError`，janitor 崩溃而无任何结构化记录。
- 序号缺口（丢失记录）、没有 INTENT 的孤儿记录、`pid` 不是整数的 REGISTERED 都使节点对清理规则“不可见”，却不影响退出码。

**修复后（`registry.py`、`janitor.py`）。**
- `parse_reg`：非对象、无已知 `kind`、`seq` 非整数的行都计入 `corrupt_lines`；不可读文件返回 `missing+unreadable`。
- `integrity_issues(records)`：序号必须恰为 1..n（缺口 / 重复 / 乱序）、孤儿记录、畸形 `FORKED`/`REGISTERED`、以及 `check_order` 违规。
- `reg_integrity()`：状态 `OK / MISSING / CORRUPT / TORN_TAIL`（撕裂末行先重读最多 3 次，容忍观察者正在追加）。**与清理状态分开记录**：独立事件 `REG_INTEGRITY_ALERT`，退出事件 `JANITOR_EXIT` 里分别写 `cleanup_state` 与 `reg_integrity`。
- `decide_with_integrity()`：文件不完整时永远不会 `EXIT_CONFIRMED`；观察者仍在运行时不会因此清理活动节点（由观察者自己的 `verify_run_set` 报告）。
- 退出码：`final_exit_code(cleanup_clear, integrity_ok)` —— 0 需要两者皆好；清理好而文件不好 = 5；文件好而清理未确认 = 4；两者皆坏 = 6。
- **不发信号的范围不变且更明确：** 仅对有 INTENT + 完整 REGISTERED（整数 pid/起始时间）的节点，先 `pidfd_open` 再核对起始时间后才发 SIGKILL；孤儿、畸形、撕裂、仅 FORKED 的进程一律不发信号（FORKED-only 仅报告）。GATED-SPAWN 的协议目标未改。

## 4. FIX-002-C：BV 证据来源

**修复前。** 单元结果是否计数取决于 `--bv-evidence PATH` 指向的 JSON：只检查其自报的 `meta.prereg_sha256 / bench_code_sha256 / checks_run` 与 `results[*].ok`。任何人手写这样一个 JSON 即可让单元“计数”；没有任何东西证明 BV 真的跑过、由谁授权、与哪次运行对应。

**修复后（新 `evidence.py`、`e1a_runner.py`）。**
- BV 运行由**运行器**在运行目录里写下：`authorization_used.json`（运行开始时对授权文件的逐字拷贝）、`environment.json`（含授权文件哈希）、`plan.json`、`validity.json`（含 run_id、authorization_id）、`registry.jsonl`（观察者的追加式登记，含 `RUN_START` / `RUN_END`）、`summary.json`，最后由 `build_attestation()` **从这些原始文件重新计算**出 `bv_attestation.json`（各文件 SHA-256、结果摘要、run id、authorization_id、预注册 / 代码哈希、`attestation_sha256`）。
- 单元授权必须由**负责人**在 `phases["E1A-CELLS"]["bv_binding"] = {run_id, bv_authorization_id, attestation_sha256}` 里绑定该次 BV 运行；命令行不再接受证据路径（`--bv-evidence` 已删除）。
- `verify_bv_provenance()` 从原始文件重新推导并核对：运行目录名合法、不是链接、位于证据根下；七个文件齐全；存储的证明与其自身摘要、与重新计算值、与负责人绑定的摘要三者一致；run id、授权 id、预注册哈希、代码哈希一致；运行阶段为 `bv` 且五项运行级检查**全部**执行并通过、各自清理已确认；授权拷贝为负责人签发、绑定同一预注册 / 代码并授予全部五项；`summary`（无中止、清理已确认、恢复关闭、janitor 退出 0、无单元）；登记文件无撕裂 / 损坏 / 完整性问题、`RUN_START` 与运行匹配、`RUN_END` 为最后一条且清理已确认、BV-1/2/3/6 各有且仅有一个带预期状态序列的登记节点、没有 SUP 节点。任一不满足 ⇒ 强制 `SMOKE - not counted`。
- 事后修改任一原始文件都会改变摘要，与负责人批准的摘要不符。

## 5. 修复前后行为对照与测试（均未运行）

| 问题 | 修复前 | 修复后 |
|---|---|---|
| A | 清理期间新建的节点不被清理也不进残余；RUN_END 前不核对；强杀仍在承担责任的 janitor；janitor 异常退出可被掩盖 | 入口先关闭并撤销在途票据；每轮重读节点集合到不动点；RUN_END 前核对整个运行集合；janitor 只在责任解除后才可被停止；异常退出 / 未确认 / 残余 ⇒ `recovery_open` + 人工处置标记 |
| B | 缺失 / 损坏 / 撕裂的登记文件不影响退出码；非对象行使 janitor 崩溃；序号缺口与孤儿记录静默 | 完整性单独评估、单独记录；任何不完整都不可能退出 0（5 / 6）；仅对身份已验证的完整记录发信号 |
| C | 手写 `ok:true` 的 JSON 即可让单元计数 | 必须有负责人签发的绑定，并由原始记录重新推导；否则强制 SMOKE |

**已编写、未执行的测试**（`tests/test_e1a_staticfix2.py`，纯文件 / 管道 / 进程内套接字对，/proc 与 pidfd 以 mock 代替）：`TestFix002AIntake`（入口关闭拒绝、在途票据撤销与中止字节、撤销后的 CREATED 记录且保持残余、重新开放）、`TestFix002AFixpoint`（清理中新增节点被下一轮捕获、永不稳定的集合不算清理成功、禁止使用陈旧快照、运行集合核对失败 ⇒ 不成功）、`TestFix002AVerifyRunSet`（缺记录 / 文件被改 / 文件含未知节点 / 待决票据 / 未确认节点）、`TestFix002ARecoveryState`（逐项失败 ⇒ 恢复保持打开；运行中的 janitor 不被杀；`execute` 源码约束）、`TestFix002BIntegrity`（缺失 / 不可读 / 各类损坏行 / 撕裂末行重读 / 序号缺口 / 孤儿 / 畸形 REGISTERED 与 FORKED / 决策与退出码表 / 无法识别的进程从不发信号 / `janitor.main` 端到端在损坏文件下绝不返回 0）、`TestFix002CProvenance`（真实一致的运行通过；无绑定 / 篡改结果、登记、摘要、授权拷贝 / 手写证明 / 摘要不符 / 身份字段不符 / 仅部分检查 / 缺 BV2 节点 / 清理未确认 / 路径技巧与符号链接 / 缺文件 / 非 BV 阶段 / 运行器接线）。此外 `test_e1a_staticfix.py` 已按新 API 适配。**运行级 BV、E1-A 单元、E1-B/C/D、E2/E3、真实 D1、GPU：未触及。**

## 6. 静态检查与哈希

AST 解析全部通过；`static_audit.py` 0 条违规；`check_prereg_schema.py` ok=True；`e1a_runner.py --check` ok=True（`bench_code_sha256` `14f281cff4ee187a4f93be582703bb4eb0096ff78e9f64e41d994d26d70d40df`）；AST lint：lint findings: 0。

| 文件 | SHA-256 |
|---|---|
| `bench/e1a_runner.py` | `b561af884950859b19fd8a4c37309cbd71cd3933190501984ecf526be8f967f9` |
| `bench/evidence.py` | `3fe2e7f792bcdfc77482cfff5d36c198985a816bf4ca660eaaa40b6bcc47bea0` |
| `bench/janitor.py` | `38bfacc02db9c502bf13696fd65747fcef8f0e6b64f407dcb095744d02a4258f` |
| `bench/observer.py` | `c075dd75e64669b97520725540b0c9b1dc42baaaf8363d046cfe84eb9f3f1772` |
| `bench/registry.py` | `209bdb2c0c6e3e226f9b9d4f726734b2c0f1f8034d94d9a65a240dc54cdb28c8` |
| `tests/test_e1a_staticfix.py` | `ef50d7c9bcbc19016910c117a44b8518af39965ceca86e679296658fed57dd26` |
| `tests/test_e1a_staticfix2.py` | `5fb2af5c7983c29a6c0799d16035bc2be7eb6b4be0450a8649c9c21d61170b28` |

## 7. 完整性

| 项 | 结果 |
|---|---|
| 冻结 R3 / 决定记录 / 冻结记录 | 前缀 `66a656145fc203c7…` / `6209602e7d51b1ae…` / `e3bba6b0968101bf…` 核对一致 |
| `D1_CODE_SHA256SUMS` | 10/10 OK |
| 预注册文件与侧文件 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`，无 diff |
| CPU-001/002 代码与证据、Parcae、真实 D1 | 无 diff / 未触碰 |
| `__pycache__` / `.pyc` | 未提交 |
| 推送后远端树 | 见交付报告 |

## 8. 尚存风险

1. **全部新增路径从未执行**（入口门、不动点清理、运行集合核对、janitor 完整性分支、证据校验）；新测试同样未跑，可能含错误。
2. 证据来源的锚点是**负责人的审阅**：能写证据目录的人若在负责人审阅之前伪造出一整套彼此一致的 BV 运行，文件逻辑本身发现不了。缓解：先把 BV 运行目录提交到 Git、由负责人审阅后再签发 `bv_binding`；授权文件与证据同属一个 uid，不构成安全边界。
3. 登记文件“撕裂末行”判断依赖重读窗口（3 次 × 0.2 s）；观察者仍在追加时的瞬时撕裂只产生告警，不触发清理；运行结束后仍撕裂则必然退出 5（保守）。
4. 责任被委托给仍在运行的 janitor 时，运行器退出后会留下该 janitor 进程（设计如此，需人工查看 `janitor_actions.jsonl`）；身份无法确认的进程仍不会被任何组件发信号，只能人工处置。
5. `integrity_issues` 要求登记序号恰为 1..n：只适用于每次全新运行目录；若将来允许续写同一登记文件会产生误报（保守方向）。
6. 令牌扫描把任何含 `bench/sup_stub.py` 的残留进程（例如上次崩溃遗留）视为“未确认”，会使新运行 BLOCKED（有意为之）。
7. 之前的既有限制仍在：插桩不覆盖 `ctypes` 直调 libc 的 kill/wait；`CREATED` 从未到达观察者的进程只能由谱系对账 / 令牌扫描发现（ERRATA-002 R1/R5）；janitor 与观察者同时失效无自动清理（R2）；pid 复用且起始时间相同（R3）。
8. 授权绑定代码哈希：此后任何代码修改使既有授权与 `bv_binding` 同时失效（有意为之）；BV 运行需在最终代码上重做。

## 9. 下一条唯一指令

把本轮修复（提交 `62f3ba701f36f2e330d2f42d75d8c3a36c6194e1` 与本检查点）提交给 ChatGPT 复核。完成后停止，等待审核和项目负责人**单独授权**；未经授权不运行任何 CPU-003 进程级测试、BV 或 E1-A。首次受控运行须以 `e1a-auth-2` 授权文件分阶段、逐项授权（BV 阶段先行并提交证据，再由负责人签发含 `bv_binding` 的单元授权）。

R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；G3～G6 NOT TESTED；NO A-B WINNER；Grok：CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED。
