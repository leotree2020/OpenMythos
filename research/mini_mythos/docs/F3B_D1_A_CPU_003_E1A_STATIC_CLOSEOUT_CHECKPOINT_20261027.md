# F3B-D1-A-CPU-003 E1-A — 检查点：静态审核最终收口 STATIC-CLOSEOUT-001（未执行）

**状态：`E1-A STATIC CLOSEOUT COMPLETE / PENDING FINAL REVIEW / EXPERIMENT NOT TESTED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

ChatGPT 第三轮（HEAD `f4f10a18d346dd2cdae1752c3f377337c239a5f4`）：`STATIC REVIEW CONDITIONAL FAIL — TWO PRE-EXECUTION ISSUES`。本轮只修这两处，未引入新架构 / 候选 / GPU / 真实 D1，未改预注册（SHA-256 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）。**没有运行任何台架、BV、E1-A 或测试；没有 fork、没有信号。**

- 分支 `d1-r3-a-cpu-003-e1a-prep-20261027`；修复提交 `51d022c179b24b42c6a2d3cd7bb556c154de3ec6`；本检查点所在文档提交紧随其后（最终哈希见交付报告）。
- 改动范围仅 `bench/`（5 个文件）与 `tests/`（新增 `test_e1a_closeout.py`，适配 `test_e1a_staticfix2.py`）；另有本检查点与索引块。基线之外的其它路径：无。冻结 / 证据 / 预注册相对基线 diff：空（无差异）。

## CLOSEOUT-01 撤销票据的未确认创建责任

**缺口。** `_confirmed_dead()` 对“没有 pid、没有 FORKED”的节点一律返回“从未 fork，已死”。被撤销（或创建者报告 fork 失败）的票据正好是这种节点：创建者可能已经 fork，只是 `CREATED` 还没到。`verify_run_set` 只看状态 INTENT，撤销后状态变 ABORTED，于是整个运行可能在子进程仍存在时得到 cleanup PASS。

**区分的四种情形（`NodeRec.creation`）。**

| 情形 | 状态 | 如何确认 |
|---|---|---|
| 票据已撤销 | `UNRESOLVED_REVOKED`（`ABORTED` 记录带 `creation_unresolved`） | 仍**未**解决 |
| 已确认没有创建 | `creation_proof` = 门管道无读端（EPIPE），或观察者自己的 `os.fork` 抛异常（`NONE_PROVEN_FORK_FAILED`） | 才算解决，写 `DEAD`（含依据） |
| 已创建但 `CREATED` 未收到 | 同上：票据保持未解决 | 只有门证明才解决；**不猜 pid** |
| 已确认进程退出 | `REPORTED` 后同样以门证明确认（已登记节点沿用身份校验的 pid 路径） | `DEAD` |

**证明为什么成立。** 观察者持有门管道**写端**，并在发票后立刻关闭自己的读端副本；读端只可能被创建者（fork 之前）、其子进程（直到退出）、或尚在传输中的 `TICKET_OK` 持有。撤销的票据永不放行，所以活着的子进程一定还拿着读端。观察者对写端做非阻塞探测写：`EPIPE` ⇒ 没有任何进程持有读端 ⇒ 不会再有进程能由该票据创建，已创建的也已退出；写成功或会阻塞 ⇒ 可能仍有读端 ⇒ **不算证明**。证明不依赖 pid，因此 pid 被复用也不会误判；也不发任何信号。

**修改位置。** `observer.py`：`NodeRec.creation/creation_proof/late_created_pid`，`_on_ticket`（非阻塞门写端）、`_abort`（撤销时保留探测写端）、`_probe_gate`、`_confirmed_dead`（无身份的票据节点只认门证明）、`_on_created`（证明之后到达的 `CREATED` 仅记在内存，不写 `FORKED`、不使用其 pid，不在 `DEAD` 之后追加记录）、`mark_dead`（写出每个已确认节点的 `DEAD` 及依据）、`residual_detail`（“TICKET creation not proven absent”）、`verify_run_set`（“tickets whose creation is not proven absent”）。`registry.unresolved_tickets()`；`janitor.unresolved_report()` 把它们报告为 `alive=None`（janitor 无法探测门），因此 `RUN_END` 声称成功时也不会被 janitor 采信，除非有观察者写下的 `DEAD`。

**结果。** 票据创建无法证明为零或已退出 ⇒ `cleanup_ok=False`、`RUN_END.cleanup_confirmed=False`、`recovery_open`、实验判定 BLOCKED（保留残留风险）；晚于撤销、晚于清理集合核对的 `CREATED` 都不能把未确认的清理翻成成功。

## CLOSEOUT-02 登记文件运行生命周期

`registry.integrity_issues()` 新增 `lifecycle_issues()`：恰有一个合法的 `RUN_START`（`run_id` 字符串、`observer_pid` 整数）且位于文件首；`RUN_END` 至多一个，位于 `RUN_START` 之后、`run_id` 与之相同、`cleanup_confirmed` 为布尔值，并且是**最后一条**记录（之后不得再有任何创建 / 其它记录）；声称清理已确认的 `RUN_END` 要求除 janitor 外所有节点已有 `DEAD`；`RUN_START` 之前不得有节点记录，不得重复 `INTENT` / `DEAD`，`DEAD` 之后不得再有该节点的记录。`RUN_END` 现在写入 `run_id`。janitor 另需运行归属证据才可能退出 0：`RUN_START.observer_pid` 等于其监视的观察者，且存在以其自身 pid + 起始时间登记、角色为 janitor 的 `REGISTERED` 记录；缺失即登记文件完整性问题（退出码 5 / 6）。登记不完整时仍不猜测进程归属，只对身份已验证的完整记录发信号。

## 测试（已编写、未运行）

`tests/test_e1a_closeout.py`（纯文件 / 管道 / 进程内套接字，/proc 与 pidfd 以 mock）：票据状态；撤销票据在门可能仍有读端时整体清理失败且无信号；EPIPE 前后；证明后清理成功并记录依据；**`CREATED` 晚于撤销（证明之前 / 之后）**与**晚于清理核对**均不能翻转结果；创建者上报失败仍需门证明；观察者 fork 抛异常；登记失败的票据子进程按门而非 pid 解决；登记文件中的未解决票据与 janitor 的处理；生命周期场景——仅 `RUN_END`、缺 `RUN_START`、重复 `RUN_START` / `RUN_END`、`RUN_END` 后出现创建记录、`RUN_END` 属于别的运行 / 非法、`RUN_END` 先于 `RUN_START`、确认的 `RUN_END` 盖住未完成节点、`DEAD` 之后再有记录、重复 `INTENT`；`janitor.main` 在这些文件下绝不退出 0；缺自身登记 / 别人的登记 / 角色不符 / 观察者不符；无信号。`test_e1a_staticfix2.py` 的夹具已按新生命周期规则更新。

## 检查与完整性

AST 解析通过；`static_audit.py` 0 条违规；`e1a_runner.py --check` ok=True（`bench_code_sha256` `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`）；lint findings: 0；R3 / 决定记录 / 冻结记录前缀核对一致；`D1_CODE_SHA256SUMS` 10/10 OK；CPU-001/002、Parcae、真实 D1 未触碰；无 pyc。最小 diff：

```
.../a_predicate_003/bench/e1a_runner.py            |   2 +-
 .../mini_mythos/a_predicate_003/bench/evidence.py  |   3 +-
 .../mini_mythos/a_predicate_003/bench/janitor.py   |  32 +-
 .../mini_mythos/a_predicate_003/bench/observer.py  |  85 ++++-
 .../mini_mythos/a_predicate_003/bench/registry.py  |  77 +++++
 .../a_predicate_003/tests/test_e1a_closeout.py     | 371 +++++++++++++++++++++
 .../a_predicate_003/tests/test_e1a_staticfix2.py   |  46 ++-
 7 files changed, 585 insertions(+), 31 deletions(-)
```

| 文件 | SHA-256 |
|---|---|
| `bench/e1a_runner.py` | `7a89d7ffd225af29c8055da69935e0c64a0e4c3d920787c0329cf44448c442f7` |
| `bench/evidence.py` | `7aa46a6914058bd4bfcda8872de23c9fc7f4124e7d49dadb830d13d6482c92a1` |
| `bench/janitor.py` | `fc355eea2570fa8ce72909f5e8a8de400be66e9796135ae992d0878eb71c2511` |
| `bench/observer.py` | `de865603451878d39b94a2d2b503b4cab14cc571e4ac865053a250b0ec156bb1` |
| `bench/registry.py` | `25540f7c7451174ff60fd6ad055c9f0d9f9fb8913878e949dc9d8239fc9b9865` |
| `tests/test_e1a_closeout.py` | `90c9e0c2f3fbb241fc3146a9ee259490c16c3e8fd7b18b2fabc43bdb003fed51` |
| `tests/test_e1a_staticfix2.py` | `59f7b542f9c7ff19bd2696227baf81c0e460b4ebf47fc9b1807b482a3a169fa3` |

## 尚存风险

1. 全部新增路径从未执行；新测试同样未跑，可能含错误（尤其依赖 `EPIPE` 语义、非阻塞管道写与套接字对的行为，均属设计假设）。
2. 门证明的前提是：只有创建者、其子进程和在途 `TICKET_OK` 持有读端，且子进程不复制它（`node_main` 不复制）；节点代码若将来复制该描述符，证明就会偏保守（读端不消失 ⇒ 永远“未证明”，不会误判成功）。
3. 无法证明的票据保持 BLOCKED，需人工处置；janitor 不能探测观察者的门，因此观察者崩溃后遗留的未解决票据只能被报告，不能被它解决。
4. `lifecycle_issues` 对登记文件的形状要求严格（全新运行目录、序号 1..n）；任何偏离都会让 janitor 退出 5 / 6（保守方向）。
5. 之前各轮列出的既有限制仍在（插桩不覆盖 `ctypes` 直调；授权与证据同 uid；R2 / R3 等）。

## 下一条唯一指令

提交最终代码（提交 `51d022c179b24b42c6a2d3cd7bb556c154de3ec6` 与本检查点）供 ChatGPT 最后复核；未经项目负责人单独授权不执行实验、BV 或任何进程级测试。

R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；G3～G6 NOT TESTED；NO A-B WINNER；Grok：CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED。
