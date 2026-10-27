# F3B-D1-A-CPU-003 E1-A — 检查点：纯逻辑测试 LOGIC-TEST-001（第 1 个文件被执行框架缺陷阻断，已暂停）

**状态：`E1-A LOGIC TESTS NOT COMPLETED — BLOCKED AT FILE 1 BY AN EXECUTION-GUARD DEFECT / RESULTS PENDING REVIEW / PROCESS TESTS NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

授权：`F3B-D1-A-CPU-003-E1A-LOGIC-TEST-001`（仅纯逻辑 / Mock 测试）。基准 `fcb6de850767c333b04b10c92d47616781028aad`。**没有任何真实测试断言被执行；没有 fork、没有信号、没有进程创建。**

## 1. 执行前核对（全部通过）

| 项 | 结果 |
|---|---|
| 本地 / 远端 HEAD | 均为 `fcb6de850767c333b04b10c92d47616781028aad`，分支 `d1-r3-a-cpu-003-e1a-prep-20261027`，工作区无改动 |
| 预注册 SHA-256 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| R3 / 决定记录 / 冻结记录 | 前缀 `66a656145fc203c7…` / `6209602e7d51b1ae…` / `e3bba6b0968101bf…` 一致；`D1_CODE_SHA256SUMS` 10/10 |
| CPU-001/002 与冻结代码 | 相对 CPU-003 设计基线 `6a089f5` 的 `git diff --stat` 为空 |
| Python / 内核 / 依赖 | 3.13.16；6.18.44-fc-v165；uid 0；仅标准库 |
| 授权文件 / 证据目录 | `AUTHORIZATION_E1A_RUN.json` 不存在，`evidence/` 不存在（因此所有 `--execute` 调用在授权检查处返回 2） |
| 静态核对五个测试的调用路径 | 文件中出现的 `kill` / `waitpid` / `fork` 均为事件名字符串、被 mock 的调用（`gate.fork_gated`、`PidfdHandle`、`cleanup_until_clear`）或在授权检查处即返回的拒绝路径；被导入的台架模块顶层只有 `sys.path` 设置；`test_e1a_gate.py` 未被五个文件导入。**未发现越界路径。** |

## 2. 执行框架（防御性补充，未改任何测试）

`logic_test_results/guard_runner.py`：把一个**未修改**的测试文件当作 `__main__` 运行，并在此之前把 41 个会创建进程、发信号、等待、`exec`、`pidfd_open`、`setsid` 的原语替换成记录器（调用即抛 `BOUNDARY VIOLATION` 并使运行以 3 退出 ⇒ BLOCKED）。每个文件的命令：`( cd tests && timeout 600 python3 -B ../logic_test_results/guard_runner.py <file>.py ../logic_test_results/<name>.guard.json )`，原始输出与退出码分别保存。

## 3. 结果

| 文件 | 退出码 | 通过 / 失败 / 错误 / 跳过 | 状态 |
|---|---|---|---|
| `test_e1a_logic.py` | 1 | 0 / 0 / 2 加载错误（均不是测试断言）/ 0 | **BLOCKED（执行框架缺陷）— 测试断言 NOT TESTED** |
| `test_e1a_runner_interlock.py` | — | 未运行（按规则在首个非 0 后暂停） | NOT TESTED |
| `test_e1a_staticfix.py` | — | 未运行 | NOT TESTED |
| `test_e1a_staticfix2.py` | — | 未运行 | NOT TESTED |
| `test_e1a_closeout.py` | — | 未运行 | NOT TESTED |
| `test_e1a_gate.py` | — | 不属于授权范围，未运行 | NOT AUTHORIZED |

守卫记录：越界调用 0 次；进程数运行前 / 后均为 81。

**完整输出（`test_e1a_logic.output.txt`）：**
```
test_e1a_logic (unittest.loader._FailedTest.test_e1a_logic) ... ERROR
 (unittest.loader._FailedTest.) ... ERROR
ERROR: test_e1a_logic (unittest.loader._FailedTest.test_e1a_logic)
AttributeError: module '__main__' has no attribute 'test_e1a_logic'
ERROR:  (unittest.loader._FailedTest.)
AttributeError: module '__main__' has no attribute ''
Ran 2 tests in 0.000s
FAILED (errors=2)
```

## 4. 根因分类（未修复，等待审核）

- **类别：执行框架（本轮新增的 `guard_runner.py`）缺陷；不是测试夹具、Mock、台架实现或环境问题。**
- **机理：** 守卫以 `python3 guard_runner.py <test_file> <guard_json>` 启动，`sys.argv` 里留着这两个参数；测试文件末尾的 `unittest.main(verbosity=2)` 把 `argv[1:]` 当作要加载的测试名，于是去 `__main__` 里找名为 `test_e1a_logic`（来自 `test_e1a_logic.py`）和 `''`（来自 JSON 路径）的属性，两个“加载失败”条目就是那 2 个 ERROR。测试类本身从未被收集或执行（文件的导入阶段已成功）。
- **建议的最小修复（**未应用**）：** 在 `runpy.run_path` 之前令 `sys.argv = [test_file]`。只改执行框架，不触及测试、台架、预注册或判据。
- 按授权的失败规则：保存了完整输出，**没有**立即修复，**没有**继续运行后四个文件，等待审核；是否按上述方式修正并从第 1 个文件重新开始，需要审核者和项目负责人确认。

## 5. 证据文件与哈希

| 文件（`logic_test_results/`） | SHA-256 |
|---|---|
| `environment.txt` | `804ea51da3bd573af7ac910384959acf22ae8f679f7b9ad9162b5072b15200bc` |
| `guard_runner.py` | `f260b4b6b4a477b93fe3d602d19951c31044ca1b8636ec578322c900d9402327` |
| `test_e1a_logic.exitcode.txt` | `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865` |
| `test_e1a_logic.guard.json` | `3bc333fd0582b077ca01af47a5026adb20d1a23513d871313f85e8db52941478` |
| `test_e1a_logic.output.txt` | `c4a19fbc5ee7f6bf6e7ec85944281afdbe464890644eff1210b9ccdfd19df25a` |

## 6. 未解决问题与下一条指令

1. 五个纯逻辑测试文件的所有断言仍是 **NOT TESTED**（它们从未运行过，首次运行可能暴露测试代码或台架缺陷）。
2. 台架代码、测试代码、预注册均未改动（台架代码哈希 `bench_code_sha256` 不变）。

**下一条唯一指令：** 审核者 / 项目负责人确认是否允许仅修正 `guard_runner.py` 的 argv 传递（一行），然后按原授权范围从 `test_e1a_logic.py` 起重新逐文件执行。未获确认前不继续；进程级测试、BV、E1-A 仍未授权。

R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；G3～G6 NOT TESTED；NO A-B WINNER；Grok：CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED。
