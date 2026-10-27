# F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001 检查点

**状态：`G0 V5 IMPLEMENTATION COMPLETE (CODE WRITTEN) / STATIC AUDIT RECORDED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**

授权范围：CODING AND STATIC AUDIT。基准 `13043b91336ada8fe05227062d36d876e9cd1355`（G0-V5-CLOSEOUT-SPEC-001）。实现分支 `d1-r3-a-cpu-003-e1a-g0-v5-impl-20261027`。

## 1. 提交

| 顺序 | 完整 SHA | 内容 |
|---|---|---|
| 1 | `ee76022a409c12dd628d6f814e9f9a7d10961b54` | 实现代码：`g0_auth.py`、`g0_judge.py`、`g0_run.py` |
| 2 | `12994f36f90e42fd7ae647fa12166003be4365fa` | 测试（5 个文件 + 夹具）与静态审计工具 |
| 3 | 见 `git log`（本检查点所在提交） | 静态审核报告、需求对应表、审计输出、本检查点、`PROJECT_MAP.md` 追加块 |

## 2. 哈希（SHA-256；路径相对 `research/mini_mythos/a_predicate_003/`）

| 文件 | SHA-256 | 状态 |
|---|---|---|
| `gate_g0/g0_auth.py` | `15899a2e6cca5172b9355696b07afbc0e7a411797041198b9f936276f23e0cab` | 修改 |
| `gate_g0/g0_judge.py` | `3892966769b2543f1990bc279bc20ce2f645c04836ecd0164bd6ff3a9656108e` | 重写 |
| `gate_g0/g0_run.py` | `1ae866cf8523f624552d20a98a704e03dfadf616c4717342a0f2daed5232bc5b` | 重写 |
| `tests/test_g0_interlock_and_judge.py` | `5e41a0158a53160c3e54dd1b384e70518baaa7e2e991740490c75c468fc0a6ae` | 重写（68 个测试，NOT TESTED） |
| `tests/test_g0_v5_cases.py` | `a65a7ebc4cd3c21979a5798b1291809fd92c5365383049381ab3016befa06f0e` | 新（35 个，NOT TESTED） |
| `tests/test_g0_v5_closure_cases.py` | `178781b0d4518370384c229af025a2797d82993a0cd23ad0d2476bac424abc7f` | 新（24 个，NOT TESTED） |
| `tests/test_g0_v5_pipeline.py` | `65174402a0ab8e85288766d0e2a457364c0c83e9ccfe2de4b0b8d5d5edad504b` | 新（29 个，NOT TESTED） |
| `tests/test_g0_v5_run_parts.py` | `66c735242db53089c81e5c1b421c7d742a7a8c58c90a4bda57bfaf7aa799fbcb` | 新（28 个，NOT TESTED） |
| `tests/g0_v5_fixtures.py` | `e78a8edd972ee059526e127662c80917c35b1bef80a4fc56ed01fc3126556615` | 新（夹具，不是测试） |
| `tools/audit_g0_v5_implementation.py` | `33b794ccbb386cf2bea96a4099f3bd34794edf10460e9a04fd0958dff5e9c419` | 新（只读静态审计） |
| `g0_preflight_review/G0_V5_IMPLEMENTATION_AUDIT.md` | `02c55858852fff4f6efcfeb7cb8bfb1a0ae23669794bd409270ef681915b6073` | 新 |
| `g0_preflight_review/v5_implementation_trace.md` / `.json` | `e671e44567f3266582fc9f7de19267f857c2b5c1b19105bc43dfcb63452d7c25` / `b2556fc9f4cb28deadba5e73ff69879d268488d657b218ee19907c366e8a61e0` | 新（需求对应表） |
| `g0_preflight_review/v5_implementation_audit.txt` | `9fcaa04e6cf78b786be3b4108fea8bdc5969f693a91c40753584aeb148e3a2cb` | 新（审计输出） |
| `g0_preflight_review/v5_static_audit_g0.txt` / `_bench.txt` | `f33d7ce456c831f38ca0def45a191df07dfa235144151d71091db721f1bec5ac` / `49e1b5a412e4adfedbc4979b3ce500f96495825bf9ac98e446645ab47220a2a8` | 新（既有 AST 审计输出） |
| `gate_g0/g0_criteria_v5.json` | `d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821` | **未变（冻结）** |
| `gate_g0/E1A_GATE_G0_PREREG_V5.md` | `8338f4a0e20e37ad791d35eb876aca23f3e86e6f16fa9e2d84fd4ac82ef6e25c` | **未变（冻结）** |
| `gate_g0/g0_criteria_v5.json.sha256`（文件） | `fe9515b7d645c53a8ed358dc2f8da4ad8853c15023b44b720fc1d2be9edad15c` | 未变 |
| `prereg/e1_provability_table_v1.json`（E1-A 原预注册） | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` | 未变 |
| bench 代码聚合哈希（`bench_code_sha256`，基准与当前相同） | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0` | 未变 |

V1–V4 冻结判据与文字的哈希同样未变（由 `g0_auth.FROZEN_FILES` 与审计工具核对）。

## 3. 依赖

* Python 3.13.16（以 `python3 -B` 运行，仅标准库）；Linux 内核特性：`pidfd_open`、`socket.send_fds`、硬链接（`os.link`）、`O_NOFOLLOW`、`O_DIRECTORY`、`fsync`、`posix_fadvise`（尽力）。
* 台架模块（**未改动**）：`bench/common.py`、`observer.py`、`registry.py`、`node.py`、`proto.py`、`gate.py`。
* 冻结判据 `g0_criteria_v5.json`（`closure.preflight.rules` 由 `g0_judge.closure_reasons` 在运行时读取）。
* 不使用 GPU，不改变 Transformer / Mythos 模型架构。

## 4. 验收状态

| 条件 | 状态 |
|---|---|
| 实现与 V5 各项要求的逐项对应表 | 完成（64 行，0 行未找到；`v5_implementation_trace.md`） |
| 只读源码审计、AST / 语法结构审查、Git diff 检查 | 完成：9 个 Python 文件语法 / 未定义名 / 未使用导入干净；`static_audit.py` 0 违规；`git diff 13043b9 -- bench` 为空；V1–V5 与 E1-A 预注册哈希未变；无授权文件、无 `evidence/` |
| 未运行的测试标明 NOT TESTED | 是：184 个测试方法全部 NOT TESTED |
| 无法实现或与冻结判据冲突的条款标记 BLOCKED，不自行修改 V5 | 是：B-1…B-4（见审核报告 §6）；V5 未改 |
| 在独立实现分支提交代码、静态审核报告和 checkpoint | 是 |

代码已写完**不是**测试 PASS；本阶段没有任何测试 / 判定函数被执行。

## 5. 未解决问题

1. **B-1：** 冻结文字对消耗目录有两种说法（「排他创建」与「创建或验证」）；实现按 F-13（创建或验证）。需要裁定。
2. **B-2：** `CE-E1` 的案例标签（`C07-U1`）与冻结 C07-U1 文字不符；实现与冻结文字一致（`C07-U5`），测试对该案例用别名。
3. **B-3：** `os.link` / `fsync` / `pidfd` 等在目标环境的真实行为；L-6（标记不是签名）、L-7（需硬链接）、L-8 沿用。
4. **B-4：** 184 个测试尚未运行；测试由手工推演编写，可能存在夹具或补丁层面的错误，需要在测试授权后分诊。
5. `g0_preflight_review/audit_g0_pure_tests.py` 是针对旧 46 个测试的历史审计脚本，未更新。
6. 真实 G0 仍未授权；`AUTHORIZATION_E1A_GATE_G0.json` 不存在；`g0_run.py --execute` 在没有有效 V5 授权时拒绝（退出码 2）。

## 6. 下一条唯一指令

将本实现分支交给 ChatGPT / Grok 审核；通过后**仅申请 CPU 纯逻辑测试授权**（`tests/test_g0_*.py` 的 5 个文件与 `tools/static_audit.py`）。不自动启动真实 G0，不创建授权文件，不运行进程级测试。
