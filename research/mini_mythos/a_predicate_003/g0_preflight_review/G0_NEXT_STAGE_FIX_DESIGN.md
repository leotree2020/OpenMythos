# G0_NEXT_STAGE_FIX_DESIGN — F-8 / F-9 / F-12 / F-13 与 V2-C03 的下一阶段修复设计

**状态：`DESIGN ONLY / NOTHING IMPLEMENTED / G0 PURE TESTS NOT TESTED / G0 REAL PROCESS NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V2-SPEC-001`。冻结的 V2：`gate_g0/g0_criteria_v2.json`（`43f7eb79…`）、`E1A_GATE_G0_PREREG_V2.md`（提交 `77750c3…`）。
**本文件没有修改 `g0_run.py` / `g0_judge.py` / `g0_auth.py`（`g0_code_sha256` 仍为 `29e1253b…`），没有运行任何测试或进程。** 目的：让 ChatGPT / Grok 交叉审核，待负责人授权后按本方案实施。V2 §10 规定：实现满足这些义务并通过审核之前，不得授权任何 G0 执行。

## 0. 发现登记册（截至本阶段）

| ID | 内容 | 状态 |
|---|---|---|
| F-1 | `observer._confirmed_dead` 把已登记直接子进程的僵尸 `Z` 当已死（退出≠回收） | 开放；台架未改；G0 以 C08/C09/C10 单独证明；是否在 G1 前修台架由审核者决定 |
| F-8 | `os.waitpid(pid, 0)` 无超时 | 开放 → 本文 §2；V2 `enforcement.reap_wait` |
| F-9 | 无运行期总预算 | 开放 → 本文 §3；V2 `enforcement.total_budget`、C15 |
| F-10 | 未运行测试的两处缺陷（固定 `/tmp` 路径/无 `run()` 间谍；缺 `verbosity=2`） | **已修复**（`f847b5b`） |
| F-11 | 安全评审 §6 第 1 项「强于」措辞过强 | 已在 `G0_PREFLIGHT_REVIEW.md` 更正 |
| F-12 | `main()` 异常分支可能向别人创建的目录写 `g0_summary.json` | 开放 → 本文 §4；V2 `enforcement.summary_write` |
| **F-13（新，本阶段登记）** | `g0_run.py` 在 `os.mkdir(run_dir)` 时假定父目录 `evidence/` 已存在；当前环境该目录**不存在**，调用路径上没有任何先行创建它的逻辑 | **正式登记**；→ 本文 §1；V2 `enforcement.directories`、§3 步骤 2 |
| F-14 | C03 之外的多子条件检查（C05/C06/C11…）在提前中止后整项 UNEVALUABLE，可见部分的违规被报告为 BLOCKED 而非 FAIL | V2 已声明为限度 L-1（保守）；是否在后续版本改为按子条件评估，请交叉审核者决定 |
| F-15（次要） | V2 的 C16 要求记录登记表的内存记录数，但没有规则使用它 | 开放；建议：仅作信息项记录，或 V3 增加规则；审核者决定 |
| C03-V2 | 判定函数须实现 V2 的 C03 规则 | 开放 → 本文 §5 |

---

## 1. F-13 — 证据根目录不存在（正式登记）

### 1.1 验证（`f13_call_path_trace.txt`）

* 当前环境：`evidence/` **不存在**（`ls -d evidence` 失败）。
* 调用路径：`main()` →（授权加载成功）→ `run()` → `preflight()`（只读：对不存在的根目录用 `os.path.isdir` 跳过扫描）→ **`os.mkdir(run_dir)`（`g0_run.py:265`）**。路径上**没有任何**先行创建 `evidence/` 的逻辑：`os.makedirs` 只出现在 `:272`（授权消耗目录 `_g0_consumed`），**在 `:265` 之后**；`bench/registry.py:17` 的 `makedirs` 只创建 `dirname(reg_path)`，即运行目录本身，也在其后。
* 后果：首次真实运行必然在 `:265` 抛 `FileNotFoundError`；它在 `run()` 的 `try` 之外，`main()` 捕获后看到运行目录不存在，**不写任何摘要**，只在 stderr 打印，返回 3（BLOCKED）。授权标记在更后面创建，所以**不会被消耗**；没有任何进程被启动。即：不会产生错误的 PASS，也不会烧掉授权，但首次运行必然浪费且**没有证据文件**。
* 更正：上一轮安全评审 §3 的「`evidence/g0_<run_id>/` 可创建」一行以及 F-13 之前的相关论述不成立于「根目录不存在」的情形；原文不改动（保持被审基线），以本文为准。

### 1.2 最小修复方案（不是「`os.makedirs(run_dir, exist_ok=True)`」——那会静默接管已存在的目录）

**文件：`gate_g0/g0_run.py`（新增一个小节「evidence directories」，不引入新文件，避免改变 `G0_CODE_FILES`）。**

```python
class EvidenceSetupError(RuntimeError):
    pass

def ensure_dir(path, label, euid=None, lstat=os.lstat, mkdir=os.mkdir):
    """-> {'path','created_by_this_run','uid','mode','ino'}.  Creates `path` only if absent (non-recursive, 0o755); otherwise VALIDATES it.
    Never overwrites, never claims a directory somebody else created."""
    euid = os.geteuid() if euid is None else euid
    try:
        st, created = lstat(path), False
    except FileNotFoundError:
        try:
            mkdir(path, 0o755); created = True
        except FileExistsError:
            created = False                       # lost a race: validate what is there, do NOT claim it
        except OSError as e:
            raise EvidenceSetupError("cannot create %s %s: %r" % (label, path, e))
        try:
            st = lstat(path)
        except OSError as e:
            raise EvidenceSetupError("cannot stat %s %s: %r" % (label, path, e))
    except OSError as e:
        raise EvidenceSetupError("cannot stat %s %s: %r" % (label, path, e))
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise EvidenceSetupError("%s %s is not a real directory (symlink or other file type)" % (label, path))
    if st.st_uid != euid:
        raise EvidenceSetupError("%s %s is owned by uid %d, not %d" % (label, path, st.st_uid, euid))
    if st.st_mode & 0o022:
        raise EvidenceSetupError("%s %s is writable by group/other (mode %o)" % (label, path, st.st_mode & 0o7777))
    return {"path": path, "created_by_this_run": created, "uid": st.st_uid, "mode": st.st_mode & 0o7777, "ino": st.st_ino}
```

**`run()` 开头（在授权副本写入之前）：**
1. `ev["evidence_root"] = ensure_dir(GA.EVIDENCE_ROOT, "evidence root")`（父目录 `a_predicate_003/` 必须已存在，`mkdir` 非递归；不存在则失败）。
2. 运行目录：保持排他 `os.mkdir(run_dir, 0o755)`；`FileExistsError` ⇒ `EvidenceSetupError("run directory exists; not touching it")`，并**不**设置 `state["run_dir_created"]`（F-12）。成功后 `state["run_dir_created"]=True`，`ev["run_dir"]={"path":…, "created_by_this_process":True}`。
3. 授权消耗目录：把 `os.makedirs(GA.CONSUMED_DIR, exist_ok=True)` 换成 `ev["consumed_dir"] = ensure_dir(GA.CONSUMED_DIR, "consumption directory")`（不再用 `exist_ok` 静默接管）；标记文件仍用 `open(..., "x")` 排他创建。

**目录所有权规则：** 本次运行创建的目录记 `created_by_this_run=True`；已存在的目录只在「真实目录、非符号链接、属当前有效 uid、组/其他不可写」时被使用并记 `False`；否则 BLOCKED。运行目录只允许「本进程刚创建」。**不使用别的运行的证据目录**：运行目录名唯一（含时间戳 + 3 字节随机数），已存在即 BLOCKED，且不向其中写任何东西。

### 1.3 预期结果

| 情形 | 结果 |
|---|---|
| `evidence/` 不存在、父目录可写 | 由本次运行创建，`created_by_this_run=True`，运行目录排他创建，运行继续 |
| `evidence/` 已存在且合规 | 使用，`created_by_this_run=False` |
| `evidence/` 是符号链接 / 普通文件 / 别的 uid / 组或其他可写 | BLOCKED（退出码 3），**不 fork，不消耗授权** |
| 创建被拒绝（权限、只读文件系统、磁盘满、父目录不存在） | 同上，错误含 `errno` 文本 |
| 竞争：别人在我们 `lstat` 与 `mkdir` 之间创建了 `evidence/` | `FileExistsError` ⇒ 当作已存在校验，记 `False` |
| 运行目录已存在 | BLOCKED，不写入该目录（F-12），不消耗授权 |

### 1.4 异常路径与错误信息的保存

* `EvidenceSetupError` 发生在运行目录建立之前或之时 ⇒ `main()` 捕获：**总是**把完整错误（含 `errno`）打印到 stderr 并返回 3；若 `evidence/` 已存在且合规，则再**排他**创建 `evidence/g0_blocked_<run_id>.json`（`open(...,"x")`，内容：`run_id`、错误文本、各绑定、时间）；若创建失败只在 stderr 报告，**不重试、不覆盖**。该文件是普通文件，预检的「未结案运行」扫描只看以 `g0_` 开头的**目录**，不受影响。
* 如果连根目录都无法使用，没有可保存的位置，唯一记录是 stderr——因此执行时负责人应把 stderr 重定向到仓库之外的日志（执行方案里写明）。
* 授权消耗目录/标记失败 ⇒ 此时运行目录已由本进程创建，异常进入 `run()` 内部的 `except` 路径，证据写入运行目录；未 fork。

### 1.5 最小测试案例（纯逻辑，使用 `TemporaryDirectory` 与注入的 `lstat/mkdir`，不启动进程）

1. 不存在 → 创建，`created_by_this_run=True`，`mode & 0o022 == 0`。
2. 已存在合规目录 → 不修改，`False`。
3. 符号链接指向合规目录 → `EvidenceSetupError`。
4. 普通文件 → `EvidenceSetupError`。
5. 以注入 `euid` 模拟别人的 uid → `EvidenceSetupError`（以 root 运行也可测）。
6. `chmod 0o777` 的目录 → `EvidenceSetupError`。
7. 注入的 `mkdir` 抛 `FileExistsError`（竞争）→ 校验后返回 `False`，不声称所有权。
8. 注入的 `mkdir` 抛 `PermissionError` / `OSError(ENOSPC)` → `EvidenceSetupError`，消息含 `errno` 文本。
9. 运行目录已存在 → `run` 前导抛错，**目录内容的哈希前后相同**（没有被写入）。
10. 授权消耗目录不再使用 `exist_ok` 静默接管：已存在但属于别的 uid → 失败。

---

## 2. F-8 — 回收等待无界

**文件：`gate_g0/g0_run.py`。**

```python
class ReapTimeout(RuntimeError):
    pass

def reap_nonblocking(try_reap, pid, deadline_s, clock, sleep, budget=None):
    """try_reap() -> (rpid, status); rpid == 0 means 'not yet'.  Polls until the one specific pid is returned, bounded by deadline_s."""
    end = clock() + deadline_s
    while True:
        rpid, status = try_reap()
        if rpid == pid:
            return rpid, status
        if rpid != 0:
            raise RuntimeError("waitpid returned a different pid %r" % (rpid,))
        if budget is not None:
            budget.check("reap")
        if clock() > end:
            raise ReapTimeout("child %d not reapable within %.1f s" % (pid, deadline_s))
        sleep(0.01)
```
`run()` 中把 `os.waitpid(rec.pid, 0)` 换成 `reap_nonblocking(lambda: os.waitpid(rec.pid, os.WNOHANG), rec.pid, budget.cap(lim["reap_deadline_s"]), C.mono, time.sleep, budget)`；`ReapTimeout`/`ChildProcessError` ⇒ `ev["deadline_hits"].append("reap")`（`ChildProcessError` 记为异常）后进入统一异常路径。**`os.waitpid` 在文件中仍只有这一个调用点**（`static_audit --dir gate_g0` 的规则不变）；守卫的 `waitpid` 包装改成 `Guard` 的方法 `wait_one(pid, options)`（仍只放行等于那一个子进程的 pid；记录 `options`、`returned`、`mono`），以便不安装就能做单元测试。（命名避开 `waitpid`，使 `audit_g0_pure_tests.py` 不把测试里对它的调用算作进程相关调用。）

* **预期：** 正常情况 1–2 次轮询即返回（子进程此时已是 `Z`）；`waitpid_calls` 里有 0..n 条 `returned=0` 与恰好 1 条 `returned=pid`，满足 V2 的 C09/C08（`judge` 已兼容，不用改）。
* **异常路径：** 5 s 内未返回 ⇒ `deadline_hits+=["reap"]`、异常路径（不发信号，MANUAL_DISPOSITION，`RUN_END(false)`）⇒ BLOCKED；外部 `ptrace` 等情形不再无界阻塞。
* **最小测试：** ① `reap_nonblocking` 用假时钟与假 `try_reap`：`(0,0),(0,0),(pid,0)` ⇒ 返回；永远 `(0,0)` ⇒ `ReapTimeout`；返回别的 pid ⇒ `RuntimeError`；② `Guard.wait_one` 注入假的真实 `waitpid`：放行具体 pid、拒绝 `-1`/`0`/别的 pid 并记录违规；③ `judge`：轮询序列 `[0,0,pid]` ⇒ C09 PASS；只有 `[0,0]` ⇒ C09 不为 PASS；两次返回 pid ⇒ 不为 PASS；④ AST：`g0_run.py` 中恰一个 `os.waitpid` 调用，且第二个参数是 `os.WNOHANG`（加入 `static_audit --dir gate_g0` 的 G0 配置）。

## 3. F-9 — 无运行期总预算

**文件：`gate_g0/g0_run.py`。**

```python
class BudgetExceeded(RuntimeError):
    pass

class Budget:
    def __init__(self, limit_s, hits, clock=C.mono):
        self.limit, self.hits, self.clock, self.t0 = limit_s, hits, clock, clock()
    def elapsed(self): return self.clock() - self.t0
    def remaining(self): return self.limit - self.elapsed()
    def cap(self, phase_s): return max(0.0, min(phase_s, self.remaining()))
    def note(self):                        # record only (used after the child is reaped: cleanup is never skipped)
        if self.remaining() <= 0 and "total" not in self.hits: self.hits.append("total")
    def check(self, phase=""):             # record and raise (before the child is reaped)
        self.note()
        if self.remaining() <= 0: raise BudgetExceeded("total budget %.1f s exceeded in %s" % (self.limit, phase))
```
使用点（`run()`）：`budget = Budget(lim["max_seconds"], ev["deadline_hits"])` 紧随 `t0`；`check()` 位于：fork 之前、保持循环每次迭代、每个 `wait_for` 的条件函数里（`lambda: (budget.check("ready"), rec.ready is not None)[1]`）、每次快照之前、回收轮询（以上均 `check()`，会抛出）；`/proc` 消失循环在回收之后，只 `note()`；各阶段截止时间用 `budget.cap(lim["…_deadline_s"])`，阶段超时时若 `budget.remaining() <= 0` 记 `"total"` 而不是阶段名；回收之后（子进程已不存在）只 `note()` 不 `raise`，使清理与 `RUN_END` 不被跳过；`final_cleanup(grace=budget.cap(3.0))`（至少 0.1 s）。

* **预期：** 所有**有界**等待总计不超过 `max_seconds` 加一个轮询片（≈0.05 s）；超限 ⇒ `deadline_hits` 含 `total`、异常路径 ⇒ BLOCKED（C15 与 C17 失败）。
* **仍然无界（须如实保留在审核中）：** `/proc` 读取、文件 I/O、`send_msg` 的 10 s 套接字超时（一次最多 10 s，随后下一次 `check()` 触发）。预算检查**不能**中断一个已在阻塞的系统调用；也**不使用** `SIGALRM`（G0 禁止信号与 `signal.*` 常量）。外层操作系统墙钟保护是否使用，由负责人决定（见 `G0_PREFLIGHT_REVIEW.md` §2.2 第 3 点）。
* **异常路径：** 子进程仍存活时超限 ⇒ 与其他异常相同（不发信号，写 `MANUAL_DISPOSITION_REQUIRED.json`，`RUN_END(false)`）。
* **最小测试（假时钟）：** 低于限额不记录；到达限额 `check` 记录**恰好一次** `total` 并抛 `BudgetExceeded`；`note` 只记录不抛；`cap` 的取值（含 0）；`judge`：`deadline_hits=["total"]` ⇒ C15 不为 PASS 且 `verdict != PASS`。

## 4. F-12 — 摘要只写入本进程创建的目录

**文件：`gate_g0/g0_run.py`。** `run(auth, raw, run_id, run_dir, state)` 增加可变参数 `state={"run_dir_created": False}`，在 `os.mkdir(run_dir)` 成功后立即置 `True`；`main()` 的异常分支仅当 `state["run_dir_created"]` 为真时才写 `g0_summary.json`，否则只打印 stderr（以及 §1.4 的 `g0_blocked_<run_id>.json`）。正常路径同样只在 `state` 为真时写 `g0_evidence.json` / `g0_summary.json`。

* **预期：** 运行目录由别的进程创建（竞争或重复 `run_id`）时，本进程不向其中写任何字节，返回 3。
* **最小测试（`mock.patch.object(g0_run, "run")`，不 fork）：** ① `run` 抛 `FileExistsError` 且 `state` 为假 ⇒ 预先放置的目录里文件哈希不变、`main` 返回 3；② `run` 先置 `state` 为真再抛异常 ⇒ 写入 BLOCKED 摘要；③ 正常返回 ⇒ 写 `g0_evidence.json` 与 `g0_summary.json`。

## 5. V2-C03 — 判定函数实现

**文件：`gate_g0/g0_judge.py`。** 用 V2 `checks.G0-C03.rules` 重写 `c03`（不再用「`problems or complete` 才评估」的 V1 实现）：
```
facts: parse_clean (reg_parse_info), completed_run, release_byte_written (guard.release_byte_pre_write_monos),
       child_acted (events.first_action_mono / S1.messages_received / S2 exists)
F1 (always)            : positive violations among parsed records
F2 (parse_clean only)  : predecessor-absent, orphan, seq gap, RUN_END(confirmed) without DEAD
F3 (parse_clean only)  : action happened (independent evidence) but the preceding record is absent
F4 (parse_clean & completed) : a required record is absent / ABORTED present
any F fires -> FAIL (evidence = the rule id + the offending records)
else U1 (early stop, parse_clean, only later-lifecycle records missing) or U2 (registry missing/unreadable/torn/corrupt, or F3's evidence missing) -> UNEVALUABLE
else PASS (completed, parse_clean, pass condition holds)
```
`g0_run.py` 增加证据字段：`reg_memory_count`（`len(obs.reg.records)`；F-15：仅记录）、`evidence_root`、`consumed_dir`、`run_dir`；`g0_judge.c16` 的必需键相应扩展；`c15` 的名称集合含 `reap`、`total`；`load_criteria` 默认路径改为 `g0_criteria_v2.json`。

**C03 最小测试矩阵（纯逻辑，合成证据）：**

| # | 场景 | 期望 |
|---|---|---|
| 1 | 完整、干净 | PASS |
| 2 | 提前中止（READY 超时）：登记表有 INTENT/FORKED/REGISTERED/RELEASED，无 DEAD、`RUN_END(false)` | C03 UNEVALUABLE → 整体 BLOCKED（U1） |
| 3 | 同 2，但 RELEASED 的 seq 在 REGISTERED 之前 | C03 FAIL（F1），整体 FAIL |
| 4 | 提前中止，放行字节已写入（独立证据）但无 RELEASED 记录 | FAIL（F3） |
| 5 | 提前中止，子进程已发 `FIRST_ACTION` 但无 REGISTERED 记录 | FAIL（F3） |
| 6 | 提前中止，仅缺 FORKED/DEAD/RUN_END，没有放行 | UNEVALUABLE（U1） |
| 7 | 完整运行但缺 DEAD | FAIL（F4） |
| 8 | 登记表有撕裂尾部 + 提前中止 | UNEVALUABLE（U2） |
| 9 | 撕裂尾部 + 有 seq 缺口（解析不干净） | UNEVALUABLE（缺口不被归因，F2 不适用） |
| 10 | 撕裂尾部 + 两条 RUN_END（正面违规） | FAIL（F1 对破损文件仍适用） |
| 11 | 干净解析 + seq 缺口 | FAIL（F2） |
| 12 | `RUN_END` 之后还有记录 | FAIL（F1） |
| 13 | `RUN_END(confirmed=true)` 但节点无 DEAD | FAIL（F2） |
| 14 | 登记表文件缺失 | UNEVALUABLE（U2） |
| 15 | 优先级：提前中止 + F1 + 撕裂尾部 | FAIL（F 先于 U） |
| 16 | 判据 JSON 与判定函数的检查 id 集合一致（V2 文件） | 一致 |

---

## 6. 文件级修改清单（下一阶段；本阶段均未修改）

| 文件 | 修改 | 影响 |
|---|---|---|
| `gate_g0/g0_run.py` | `ensure_dir`/`EvidenceSetupError`（F-13）；`reap_nonblocking`/`ReapTimeout` + `Guard.wait_one`（F-8）；`Budget`/`BudgetExceeded` 与使用点（F-9）；`state` 参数与摘要写入条件（F-12）；新证据字段；`import stat` | `g0_code_sha256` 变化 |
| `gate_g0/g0_judge.py` | 按 V2 重写 `c03`；`c15`/`c16` 名称与必需键；`load_criteria` 默认指向 V2 | 同上 |
| `gate_g0/g0_auth.py` | `CRITERIA_PATH`→`g0_criteria_v2.json`，`PREREG_MD_PATH`→`E1A_GATE_G0_PREREG_V2.md`，`G0_CODE_FILES` 中的判据文件改为 V2 | 同上；V1 绑定的授权自动失效 |
| `tests/test_g0_interlock_and_judge.py` | 哈希/路径测试指向 V2；合成证据补新字段；检查 id 与 V2 一致 | 测试数改变，须重算验收数字 |
| `tests/test_g0_v2_fixes.py`（新） | §1.5、§2–§4 的最小测试、§5 的矩阵 | **未运行**，运行需单独授权 |
| `tools/static_audit.py` | G0 配置增加：`os.waitpid` 的第二个参数必须是 `os.WNOHANG`；允许 `stat`、`os.lstat`、`os.geteuid`、`os.mkdir` | 默认（台架）审计行为不变 |
| `g0_preflight_review/audit_g0_pure_tests.py` | 审计对象扩展到两个测试文件 | 测试数 = 两个文件之和 |
| `gate_g0/g0_criteria_v2.json`、`E1A_GATE_G0_PREREG_V2.md`、V1 文件 | **不改** | 冻结 |
| `bench/`、E1-A 预注册、R3、CPU-001/002、Parcae | **不改** | — |

**实施顺序（各步均需负责人授权）：** ① ChatGPT/Grok 交叉审核 V2 与本设计 → ② 负责人授权实施 → ③ 实现（先 `g0_auth`/`g0_judge`，再 `g0_run`）→ ④ 静态审计两种配置 + `check_g0_v2_consistency.py` + 对照 V2 §10 逐项核对 → ⑤ 写出新的绑定哈希 → ⑥ 再交叉审核实现 → ⑦ 负责人授权运行纯逻辑测试 → ⑧ 才可能授权第一次受控 G0 运行。

## 7. 本阶段未做

没有修改 `g0_run.py`/`g0_judge.py`/`g0_auth.py`，没有运行 46 个纯逻辑测试或任何进程级测试，没有 G0 / BV / E1-A 运行，没有创建 `AUTHORIZATION_E1A_GATE_G0.json`，没有创建 `evidence/`；`bench/`、E1-A 原预注册、R3、CPU-001/002、Parcae 上游未改动。
