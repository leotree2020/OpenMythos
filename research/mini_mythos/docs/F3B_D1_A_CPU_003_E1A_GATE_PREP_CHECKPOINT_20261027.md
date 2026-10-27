# F3B-D1-A-CPU-003 E1-A — 检查点：真实进程门控验证准备 GATE-PREP-001

**状态：`E1-A GATE G0 PREPARATION COMPLETE / PENDING CHATGPT REVIEW / REAL PROCESS TESTS NOT TESTED / BV NOT AUTHORIZED / E1-A NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED`**

授权：`F3B-D1-A-CPU-003-E1A-GATE-PREP-001`（**仅限进程门控测试准备**）。基准 HEAD `a7ce70fb71134d1098de7a50ed475b1b1518e64b`。本轮**没有**启动任何进程（除执行静态检查本身的 Python 解释器外）、**没有**发送信号、**没有**运行 `test_e1a_gate.py` 或任何进程级 / 纯逻辑测试、**没有**运行 BV / E1-A 单元 / `--execute` / `run_e1a.sh`、**没有**创建有效的 `AUTHORIZATION_E1A_GATE_G0.json`，台架 / 既有测试 / 预注册 / R3 / CPU-001 / CPU-002 / Parcae 均未改动。

## 1. Git 状态

| 提交 | 内容 |
|---|---|
| `a7ce70fb71134d1098de7a50ed475b1b1518e64b` | 基准（172 项纯逻辑测试通过） |
| `e287b952124e8aaf22098e1957c61da5359a5e2c` | **先冻结**：`g0_criteria_v1.json`(+sha256)、`E1A_GATE_G0_PREREG.md`、`E1A_GATE_TEST_INVENTORY.md`——在任何 G0 代码存在之前单独提交 |
| `943c1468b4da38dfa6635acb0b3f3605c800ca5f` | G0 入口 / 互锁 / 纯判定 / 纯测试（未运行）/ 安全评审 / 静态审计 `--dir gate_g0` |
| 本检查点提交 | 本文件 + `PROJECT_MAP.md` 末尾追加块 |

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`。工作区干净；`git check-ignore` 对全部新文件返回「未被忽略」；无 `__pycache__`/`*.pyc`。

## 2. 交付物

| # | 交付物 | 文件 | SHA-256 |
|---|---|---|---|
| 1 | 进程级测试清单（14 项，G0–G3 分类，发现 F-1/F-2/F-3） | `research/mini_mythos/a_predicate_003/gate_g0/E1A_GATE_TEST_INVENTORY.md` | `31bdd113c25eba19d671b47e3b5026ec44b24dc2978581975714436fb9fc8869` |
| 2 | G0 预注册（冻结）+ 机器可读判据（冻结） | `E1A_GATE_G0_PREREG.md` / `g0_criteria_v1.json` | `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb` / `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` |
| 3 | 独立 G0 入口 + 授权互锁 + 纯判定函数 | `g0_run.py` / `g0_auth.py` / `g0_judge.py` | `95bf60620b8958a3e734e7c475a71db58ef82b561553bdd91d8087ce92989c6a` / `45a090ba0492ce55973c91bee4d2ba0f9e09218ec3e60ced109efd85d00f20e5` / `8c05a42a349475732c8daa4ee1dd15a17e20cba5a2a2dfda677910bf5b58cebb` |
| 3b | 纯逻辑测试（**写好，未运行**） | `research/mini_mythos/a_predicate_003/tests/test_g0_interlock_and_judge.py` | `8ec64b596427d14387efe0f6d6a750c6a399d42aed4f313ba234fa77c8b83876` |
| 3c | 静态审计 `--dir gate_g0` 扩展（默认台架审计行为不变） | `research/mini_mythos/a_predicate_003/tools/static_audit.py` | `50efed1ff52e5fc640539602b15e962a51644a6d3432f68ea5beaf439aac02f5` |
| 4 | G0 安全评审 | `research/mini_mythos/a_predicate_003/gate_g0/E1A_GATE_G0_SAFETY_REVIEW.md` | `7d510ceb5138dde227957bcccd70c78cb815b197f450aff8ca82e585b1df3c83` |
| 5 | 本检查点 | 本文件 | — |

## 3. 本轮实际执行的检查（全部不启动被测进程）

| 检查 | 结果 |
|---|---|
| `ast.parse` 全部新文件 | 通过 |
| `tools/static_audit.py`（台架，默认配置） | **0 违规**（与扩展前相同） |
| `tools/static_audit.py --dir gate_g0`（G0 严格配置：禁止 fork/kill/killpg/pidfd_send_signal/exec*/spawn*/_exit/pidfd_open/setsid/setpgid、禁止 `signal.SIG*`、`waitpid` 仅 `g0_run.py` 一处） | **0 违规** |
| `g0_run.py --check`（只算绑定哈希；报告 `authorization_present: false`、`executed: false`） | 通过 |
| 判据哈希 | `g0_criteria_v1.json` = `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2`（与 `.sha256` 一致） |
| E1-A 预注册 SHA-256 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`（未变） |
| R3 / 决定记录 / 冻结记录前缀 | `66a656145fc203c7` / `6209602e7d51b1ae` / `e3bba6b0968101bf`（一致）；`D1_CODE_SHA256SUMS` 10/10 OK；`D1_FROZEN_CONFIG.json` `FROZEN` |
| `bench/`、`prereg/`、`gate3_d1/`、`r3_cpu_probes/`、既有 `tests/` 相对 `a7ce70f` 的 diff | 空 |
| Parcae 上游 `69284c13…` 工作区 | 干净，未改动 |

## 4. 执行时的绑定值（`g0_run.py --check` 输出；任何一项改变都使授权失效）

| 绑定 | 值 |
|---|---|
| `git_head`（以执行时为准，提交本检查点后会变） | 须由负责人在授权时重新取 `--check` 输出 |
| `prereg_sha256` | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| `g0_criteria_sha256` | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` |
| `g0_prereg_sha256` | `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb` |
| `bench_code_sha256` | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`（与 `fcb6de8` 以来相同） |
| `g0_code_sha256` | 见 `g0_run.py --check`（`g0_auth.py`/`g0_judge.py`/`g0_run.py`/`g0_criteria_v1.json` 的组合哈希；在审核通过之后不得再改这些文件） |

## 5. 依赖

CPU；Python 3.13.16 且 `python3 -B`；内核 ≥5.3 `pidfd_open`（当前 6.18.44-fc-v165）；`socket.send_fds`；`SOCK_SEQPACKET`；同一 uid；无 cgroup / proc connector / 网络 / GPU / 额外特权。详见安全评审 §3。

## 6. 未解决问题与待审核者决定

1. **F-1：** `observer._confirmed_dead` 把已登记直接子进程的僵尸 `Z` 当作已死（退出≠回收）。台架未改（改了会使 172 项证据对应的代码哈希失效）。G0 以 C08/C09/C10 单独证明二者之分；**是否在 G1 之前修台架由审核者决定**。
2. **F-2：** `test_e1a_gate.py` 不能充当 G0（其 teardown 用 SIGKILL，且 14 个测试多为 G1–G3 / E1-A 单元类）。G0 是独立入口，不与它共享执行路径。
3. **F-4/F-5/F-6：** 台架内 `final_cleanup` 的 SIGKILL 路径靠「仅在已回收后调用」+ 守卫陷阱规避；`os.write` 守卫是被测路径上的插桩；令牌扫描在共享主机上可能因无关进程名而失败关闭（见安全评审 §7）。
4. **与冻结预注册字面步骤的 6 处实现差异**（均更严或更诚实，判据 JSON 未变）见安全评审 §6，审核者可要求以 `*_v2` 文件修订，不得改冻结文件。
5. **F-7：** 新增纯逻辑测试**未运行**；其合成证据为手写。首次受控运行之前应由另行授权的纯逻辑测试执行验证。
6. Python 层守卫为零 **不能** 证明所有内核路径安全；G0 的 PASS 不是 G1/G2/G3、BV、EPIPE 撤销证明、票据后代、janitor 恢复、观察者死亡或任何 E1-A 单元的证据。
7. 授权文件仅有 schema 与互锁；`AUTHORIZATION_E1A_GATE_G0.json` **不存在**；`g0_run.py --template` 只打印一个故意无效的模板。

## 7. 下一条唯一指令

**把 G0 准备材料（本检查点所列 1–4 项）提交 ChatGPT 独立审核，等待项目负责人另行批准第一次受控 G0 运行。** 不得自动执行任何测试；G0 之后的 G1–G3、BV、E1-A 各需单独授权。
