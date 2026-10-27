# F3B-D1-A-CPU-003 E1-A — 检查点：纯逻辑测试重新执行 LOGIC-TEST-001-RERUN-001

**状态：`E1-A LOGIC TESTS EXECUTED / RESULTS PENDING REVIEW / PROCESS TESTS NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

授权：`F3B-D1-A-CPU-003-E1A-LOGIC-TEST-001-RERUN-001`（只修执行守卫，并重跑此前批准的五个纯逻辑 / Mock 测试文件）。审核基准 `8a89fb7d12d9e5bc8cf4235ad7b74d50ebd498a0`。**没有 fork、没有进程创建、没有信号；没有运行 `test_e1a_gate.py`、BV、E1-A 单元、`--execute`、`run_e1a.sh`；台架代码、测试代码、预注册均未改动。**

## 1. 守卫修复（唯一的代码改动）

`logic_test_results/guard_runner.py` 在 `runpy.run_path(...)` 之前加入 `sys.argv = [test_file]`（`git diff`：1 个文件，+1 行；41 个原语拦截逻辑原样保留）。此前失败的证据（`logic_test_results/` 下的原始文件）**未被覆盖**；本轮使用独立目录 `logic_test_results_rerun1/`。

## 2. 执行前与执行后核对

| 项 | 结果 |
|---|---|
| 执行前 HEAD（本地 = 远端） | `8a89fb7d12d9e5bc8cf4235ad7b74d50ebd498a0`，工作区无改动 |
| Python / 内核 / uid | 3.13.16 / 6.18.44-fc-v165 / 0；仅标准库 |
| 预注册 SHA-256（前、后） | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`（未变） |
| R3 / 决定记录 / 冻结记录；`D1_CODE_SHA256SUMS` | 前缀 `66a656145fc203c7…` / `6209602e7d51b1ae…` / `e3bba6b0968101bf…` 一致；10/10 OK（前、后） |
| 台架代码哈希 `bench_code_sha256`（修复前、五文件运行后） | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`（未变） |
| `bench/`、`tests/`、`prereg/`、CPU-001/002、`gate3_d1` 相对 HEAD 的 diff | 空 |
| 进程数（运行前 / 后） | 83 / 83 |
| `AUTHORIZATION_E1A_RUN.json`、`evidence/` | 均不存在 |

## 3. 逐文件结果（均通过修复后的守卫执行；每个文件都发现并实际执行了测试）

| 文件 | 测试数 | PASS | FAIL | ERROR | SKIP | 退出码 | 越界调用 | 状态 | 原始输出 |
|---|---|---|---|---|---|---|---|---|---|
| `test_e1a_logic.py` | 26 | 26 | 0 | 0 | 0 | 0 | 0 | PASS | `logic_test_results_rerun1/test_e1a_logic.output.txt` |
| `test_e1a_runner_interlock.py` | 4 | 4 | 0 | 0 | 0 | 0 | 0 | PASS | `logic_test_results_rerun1/test_e1a_runner_interlock.output.txt` |
| `test_e1a_staticfix.py` | 58 | 58 | 0 | 0 | 0 | 0 | 0 | PASS | `logic_test_results_rerun1/test_e1a_staticfix.output.txt` |
| `test_e1a_staticfix2.py` | 52 | 52 | 0 | 0 | 0 | 0 | 0 | PASS | `logic_test_results_rerun1/test_e1a_staticfix2.output.txt` |
| `test_e1a_closeout.py` | 32 | 32 | 0 | 0 | 0 | 0 | 0 | PASS | `logic_test_results_rerun1/test_e1a_closeout.output.txt` |
| **合计** | **172** | 172 | 0 | 0 | 0 | — | 0 | **全部 PASS** | |

每个文件的 `*.exitcode.txt`、`*.guard.json`（越界调用 0；41 个拦截原语）、`*.summary.json` 同目录保存。命令（逐文件）：`( cd tests && timeout 600 python3 -B ../logic_test_results/guard_runner.py <文件>.py ../logic_test_results_rerun1/<名>.guard.json ) > …/<名>.output.txt 2>&1`，环境变量 `PYTHONDONTWRITEBYTECODE=1`。

## 4. 如实记录的事件与观察

1. **验收脚本的计数缺陷（已更正，非测试失败）。** 第 1 个文件 `Ran 26 tests … OK`、退出码 0、守卫 0 次，但我的只读汇总脚本 `summarize.py` 只数到 25 个 `... ok`：`test_static_audit_reports_no_violation` 的 `ok` 因 `ResourceWarning` 写在中间而独占一行，被正则漏掉，于是我的循环按自己的验收规则停下。这不是授权所定义的“失败、错误或越界调用”（没有任何一个测试失败或出错，守卫 0 次）。我只更正了这个汇总脚本的解析（同时数 `^ok$` 等独占行），原版保存在 `summarize_v1_superseded.py`，第一次的错误汇总保存在 `test_e1a_logic.summary_v1_miscount_superseded.json`，并用保存的原始输出重新汇总第 1 个文件，随后按原顺序继续。若审核者认为此处应当停下等待确认，请指出；未修改任何测试、台架或守卫的拦截逻辑。
2. **`ResourceWarning`（只是警告，未导致失败，未修复）：** 共 74 条——`tools/static_audit.py` 里 `open(path).read()` 未关闭文件（15 条）、测试夹具里未关闭的 `open(...).write(...)`（`test_e1a_staticfix2.py`，约 36 条 + 约 12 条）、`test_e1a_closeout.py` 的未关闭 socket 对（9 条）、`test_e1a_staticfix.py` 2 条。属于测试 / 工具的卫生问题，未影响断言；按规则本轮不修改测试或工具。
3. `test_e1a_runner_interlock.py` 与 `test_e1a_staticfix.py` 各输出 1 行 `REFUSED:`，是 `RUN.main(["--execute"…])` 在授权检查处按预期返回 2 的提示。

## 5. 结论的适用范围（重要）

- 这 172 个断言**全部通过**，说明：冻结预注册的分类表与 P2 的 `s0_check`、判定函数、聚合函数、注册表 / 生命周期 / 完整性规则、janitor 的决策与退出码、授权阶段、BV 证据来源校验、票据证明逻辑，**在纯逻辑与 Mock 层面**与我写的期望一致。
- 这些测试由同一作者与代码一起编写；Mock 编码了作者对 `EPIPE`、非阻塞管道写、套接字对行为的假设。“Python 层拦截记录为 0”**只表示这五个纯逻辑测试没有调用被拦截的 Python 原语**，**不能**据此说明任何内核路径安全。
- **仍为 NOT TESTED：** `test_e1a_gate.py`（进程级）；真实 GATED-SPAWN / `EPIPE` / pidfd / `SOCK_SEQPACKET`+`SCM_RIGHTS` 行为；运行级 BV-1/2/3/6/7；E1-A 单元；E1-B/C/D；E2/E3。

## 6. 证据文件与哈希

| 文件（`logic_test_results_rerun1/`） | SHA-256 |
|---|---|
| `environment.txt` | `e60a592d048683bf6dc66053a45ca499e3f2d5366973862d2d541117c94c7cdb` |
| `summarize.py` | `3365abb7b2a24048bd8e4165c4938c73bf59d82449559515a08ddd89f9698d41` |
| `summarize_v1_superseded.py` | `8d9d09295c0ba19bd268ada23903590dd48764af12e4fbe5255c74d83bb51faa` |
| `test_e1a_closeout.exitcode.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `test_e1a_closeout.guard.json` | `93f7c6fdea87b88bc249aaa02f473f8117848299bcf3f7120c2c513b5b20b2e5` |
| `test_e1a_closeout.output.txt` | `5f4280d05c0f57ce62a0ebf2d00e7d845f8978dbf1d8f5295cc4220dc6e180a7` |
| `test_e1a_closeout.summary.json` | `8ec3843c5f3c80959685ad3dff64d3c79c6e16dfe21bb55c73d955f6068251bd` |
| `test_e1a_logic.exitcode.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `test_e1a_logic.guard.json` | `3bc333fd0582b077ca01af47a5026adb20d1a23513d871313f85e8db52941478` |
| `test_e1a_logic.output.txt` | `14a0043560828ce4564be089a129b30b2286a585709a76794eb73fe95eb12dc3` |
| `test_e1a_logic.summary.json` | `6bc6d0360f0e7c6f92d7c230b77af8ed843606e40a2d1d1bc67bda6a8c04bc8a` |
| `test_e1a_logic.summary_v1_miscount_superseded.json` | `fddd653aced27aa4c5a817bd13596c8ef16891fc0ec6b3f3a4d12f24221d1f0f` |
| `test_e1a_runner_interlock.exitcode.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `test_e1a_runner_interlock.guard.json` | `767746a92cef30ac322bc263a5a628f495cf5bfe2a5fc37d8d6a5e32d8f98b1c` |
| `test_e1a_runner_interlock.output.txt` | `5f85c4e8153ca360edaae777b41708efc7457f50f20852977457694783971ddb` |
| `test_e1a_runner_interlock.summary.json` | `7e1dc9a5a58eba0dd83b87aae26b2395425d6f812493f19afee5238f68d85bd0` |
| `test_e1a_staticfix.exitcode.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `test_e1a_staticfix.guard.json` | `56b1a8d2f11222293145b01358be2c47bd344eacbc7da3874d5b640c40fa462c` |
| `test_e1a_staticfix.output.txt` | `d00a159a8f50206320a9d2a0948b3b8ebd8a1c0dd0c163b960db623f6f89d481` |
| `test_e1a_staticfix.summary.json` | `f7faf1d7f64f45e3dc3dff3073b1f00f2a90049cb9518713991a31de3709e3fe` |
| `test_e1a_staticfix2.exitcode.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `test_e1a_staticfix2.guard.json` | `8edc8238db548db9b3f3dfcf14fc0782fe3c50e1b48dda2bbeaa015d746e3df2` |
| `test_e1a_staticfix2.output.txt` | `f697ec8c58b5fb69878021bc93159ba9f3047d3eddb86bcf4a5c3dec5cd9e8cb` |
| `test_e1a_staticfix2.summary.json` | `de02b52e0a885e53c0d45c300a4df06ee060ebf9034394c8b062a5fa96109628` |

## 7. 下一条唯一指令

将五文件测试结果（本检查点与 `logic_test_results_rerun1/`）提交 ChatGPT 独立审核；不自动进入进程级测试。进程级测试、BV、E1-A 仍需项目负责人另行授权。

R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；G3～G6 NOT TESTED；NO A-B WINNER；Grok：CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED。
