# F3B-D1-A-CPU-003 E1-A — 执行前审核记录与检查点：G0-PREFLIGHT-001

**状态：`G0 PREFLIGHT REVIEW COMPLETE / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**

任务：`F3B-D1-A-CPU-003-E1A-G0-PREFLIGHT-001`。审核基准 `d8a07286d74c6d8e81b3b04b62d73a91a25ee610`（ChatGPT：`G0 PREPARATION CONDITIONAL PASS / REAL G0 NOT AUTHORIZED`）。
**没有运行** G0、BV、E1-A、`test_e1a_gate.py`、任何进程级测试，也**没有运行**新的纯逻辑测试；没有 fork、没有信号；没有修改冻结 V1（判据 JSON、预注册文本）、台架、G0 实现。只执行了 AST 解析、静态审计、哈希与 Git 检查。

## 1. 结论摘要（详见 `a_predicate_003/g0_preflight_review/G0_PREFLIGHT_REVIEW.md`）

| 任务 | 结论 |
|---|---|
| 1. 纯逻辑测试执行路径静态审计 | 46 个测试；测试文件、`main()`（不含 `run`）闭包、导入期均 **0** 个进程相关调用；`run()`（唯一 fork 点）仅在授权加载与拒绝返回之后可达，且两个调用 `main()` 的测试都用失败间谍替换 `run()`。已准备执行命令与 P1–P8 验收条件，**未运行**。 |
| 2. `g0_run.py` 阻塞路径 | 12 个阻塞点 + 子进程侧；有显式上限的：门 5.0 s、READY 5.0 s、退出 5.0 s、`/proc` 消失 5.0 s、保持 0.3 s、清理 3.0 s；正常路径最长约 18.7 s，失败路径最长约 15.5 s。**无上限：`os.waitpid(pid,0)`（F-8）与 `/proc`/文件 I/O，且没有运行期总预算（F-9）。** 超时一律抛异常并同时使 C15、C17 失败；挂起则无裁决、不写摘要、下一次预检 BLOCKED，不会 PASS。 |
| 3. 六项预注册偏差 | 1 S1 在保持期后拍：**ACCEPTABLE**（并更正「强于」措辞）；2 fork 前消耗授权：**ACCEPTABLE**；3 预检先于建目录：**ACCEPTABLE**；4 异常路径 `RUN_END(false)`：**ACCEPTABLE**（依赖第 6 项）；5 令牌 = 命令行含 `g0_run.py`：**ACCEPTABLE**（建议并入 V2 定义）；**6 C03 在不完整运行上：REQUIRES V2**（V1 判据与 V1 §3 第 8 步自相矛盾，实现选了「BLOCKED」读法，改变了可达路径上的裁决）。**BLOCKED：无。** |

## 2. 本轮实际改动（均不在冻结项或 G0 实现内）

| 文件 | 说明 |
|---|---|
| `a_predicate_003/tests/test_g0_interlock_and_judge.py`（未运行的测试） | 修复 F-10：`main()` 测试用 `TemporaryDirectory` 路径 + 失败间谍；`unittest.main(verbosity=2)`（否则既有 `summarize.py` 会把全部通过误判为失败）。测试数 46 与断言不变。 |
| `a_predicate_003/g0_preflight_review/audit_g0_pure_tests.py`、`test_static_audit.{txt,json}` | 只做 AST 的审计工具与输出。 |
| `a_predicate_003/g0_preflight_review/G0_PREFLIGHT_REVIEW.md` | 三项分析、执行方案、V2 提案（**未创建 V2**）。 |
| 本检查点、`PROJECT_MAP.md` 末尾追加块 | 记录。 |

## 3. Git SHA 与冻结哈希

| 项 | 值 |
|---|---|
| 基准（被审） | `d8a07286d74c6d8e81b3b04b62d73a91a25ee610` |
| 分析提交 | ``f847b5b2d3dd0196067dd4c3838430a980b689f1`` |
| E1-A 预注册 SHA-256 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`（未变） |
| `g0_criteria_v1.json` | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2`（未变） |
| `E1A_GATE_G0_PREREG.md`（V1） | `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb`（未变） |
| `bench_code_sha256` | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`（未变） |
| `g0_code_sha256` | `29e1253bad1665c102819a7aa2a894878397e0e2d505ac761b2ce1271b47ddbd`（未变 ⇒ G0 实现未动） |
| R3 / 决定记录 / 冻结记录前缀 | `66a656145fc203c7` / `6209602e7d51b1ae` / `e3bba6b0968101bf`；`D1_CODE_SHA256SUMS` 10/10 OK |
| `tests/test_g0_interlock_and_judge.py`（修复后） | ``5c6046f18bc6aaf15992f454651d0f5cbaf0067a2ed1df07109c21205572ca23`` |
| `g0_preflight_review/G0_PREFLIGHT_REVIEW.md` | ``0f5bb4d9e6af57c115ae4a2a16f928760f34ad559ddc6f9ea6b5e77ad664aff8`` |
| `g0_preflight_review/audit_g0_pure_tests.py` | ``03e5e90b3b4ffb73c18f13c654987dd93638b212909742cb581412e3f06b8558`` |
| `g0_preflight_review/test_static_audit.json` | ``f8896989ed913e82a1b41bec9a863edac9c1cad48f5c26594e6b4016f5c93b0a`` |
| 静态审计（台架默认 / `--dir gate_g0`） | 0 违规 / 0 违规 |

## 4. 未解决问题

1. **偏差 6 需要 V2**，须在第一次授权的 G0 运行**之前**出 `g0_criteria_v2.json` + `E1A_GATE_G0_PREREG_V2.md`（先单独提交、后改代码）。V2 会使 `g0_code_sha256` 变化，纯逻辑测试须在其后重跑。
2. **F-8** `waitpid` 无超时、**F-9** 无运行期总预算、**F-12** 异常分支可能向别人创建的目录写摘要：均为 G0 实现改动，须另行授权；建议修复见评审 §2.2（WNOHANG 轮询、运行期预算；不使用 `SIGALRM`；外层墙钟保护由负责人决定）。
3. **F-1** `observer._confirmed_dead` 把僵尸 `Z` 当已死（台架未改）仍待审核者在 G1 前决定。
4. 新增纯逻辑测试**未运行**，其合成证据为手写；运行需负责人单独授权（方案与验收条件已备）。
5. 与上一轮相同的限度：Python 层守卫为零不证明内核路径安全；G0 PASS 将不是 G1/G2/G3、BV、E1-A 的证据。
6. `AUTHORIZATION_E1A_GATE_G0.json` 不存在；`git_head` 绑定随每次提交变化，授权时须以当时 `g0_run.py --check` 为准。

## 5. 下一条唯一指令

**把本检查点与 `G0_PREFLIGHT_REVIEW.md` 提交 ChatGPT 复核；等待项目负责人批准下一阶段。** 下一阶段的候选（各需单独授权，不会自动开始）：(a) 起草并冻结 V2（解决偏差 6）；(b) 授权运行 46 个纯逻辑测试（方案 §1.3）；(c) 修复 F-8/F-9/F-12 的 G0 实现改动；(d) 之后才是首次受控 G0 运行。
