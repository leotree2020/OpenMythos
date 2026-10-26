# F3-B / D1 — 最终配置冻结检查点（F3B-D1-FINAL-CONFIG-FREEZE）

**状态：`D1 FINAL CONFIG FROZEN (status = "FROZEN") / PENDING CHATGPT INDEPENDENT ACCEPTANCE / REAL D1 NOT TESTED, NOT AUTHORIZED`**

追加式检查点，不覆盖历史记录（历史中的 CANDIDATE / BLOCKED / NOT TESTED 记录原样保留）。这是配置管理操作，不是模型实验。

## 1. 授权与范围

| 项 | 内容 |
|---|---|
| 授权 | 项目负责人，2026-10-26，`APPROVED — Final Configuration Freeze Only` |
| 来源基准 | 分支 `d1-codespaces-py3138-validation-20261026`，HEAD `ebb45680f7391c3fac975b7cdbf29d1a7a94ed67`（冻结前 Git SHA；本地与远端一致，工作区干净） |
| 冻结分支 | `d1-final-config-freeze-20261026`（从上述基准新建）。冻结后的提交 SHA 在最终报告中给出，不写回本文，避免循环依赖 |
| 冻结的含义 | 固定并可追溯地保存已审核通过的 D1 代码、配置、Python 执行环境与实验规则。**不**表示真实数据实验已执行，**不**表示真实 D1 PASS，**不**构成真实 D1 执行授权 |

## 2. 本次实际修改

只改 `gate3_d1/D1_FROZEN_CONFIG.json` 的两个叶子字段（结构化 JSON 比较，键集合不变）：

| 路径 | 修改前 | 修改后 |
|---|---|---|
| `/status` | `FROZEN_CANDIDATE__PENDING_ENV_ADAPTATION_REVIEW` | `FROZEN` |
| `/environment/python_full_version_status` | 说明文字以 `CANDIDATE PIN … independent config review required before final freeze` 开头 | 以 `FROZEN PIN …` 开头，并引用原生证据 SHA-256 与 3.13.8 上的 56/56 合成回归；版本值不变 |

结构化核对（修改前后逐段比较）：`design_basis`、`dataset`、`rows`、`window`、`tokenizer`、`serialization`、`cursor`、`schedule`、`negatives`、`trace`、`evidence_layout`、`authorization`、`identity_rules`、`runtime_values_not_frozen_here`、`not_tested_in_pipeline` 全部**相同**；`environment` 除 `python_full_version_status` 外相同。固定版本：Python `3.13.8`，tokenizers `0.23.3`，pyarrow `26.0.0`，huggingface_hub `2.2.0`；30 分钟墙钟限制（`wallclock_limit_minutes` 与 `wallclock_timeout.limit_minutes` 均为 30）不变。`authorization` 段（含 `this_stage` 与 `not_authorized` 清单）**未改**，因此没有为真实 D1 创造任何执行许可。

另：`D1_CODE_SHA256SUMS` 只有配置那一行变化（`2a372d2c…` → `0d35dc21…`）；本检查点文档、三个索引文件的追加块、`final_freeze_logs/` 日志是新增文件/追加内容。

## 3. 冻结文件清单与 SHA-256（10 项，`D1_CODE_SHA256SUMS`）

| 文件 | SHA-256 |
|---|---|
| `D1_FROZEN_CONFIG.json` | `0d35dc21a4beca7c2f93fc11df6806ea7bc321d2376f52e1552863f19e7d7aaa` |
| `d1_reader.py` | `ab37c9123defbc736632e4e03db23764646dbbedd5842bfec7d72e5556b38bc0` |
| `d1_verifier.py` | `80007f9b9d0cd0a1137922e7a2ab4f7c7c7dd3b4cc1a1d82e560833c201199b6` |
| `d1_driver.py` | `111c01f25c9ea8d9978f0ca979ab64e29f8961ddf8dac9277363a1b7c6f5a209` |
| `d1_env_manifest.py` | `3fde59f5718be6b68283e257991f218cb7c5814a8cc1595a5b9a9ec02b99a5d4` |
| `d1_selftest_data.py` | `e58174f935adeff6fbeb91e82f9f141b979b266a775290b586627ff53ad98285` |
| `requirements-d1.txt` | `55b4cb927dd2def5f5b62cc828cbb49ecaf74356ae00722ab2afca928bc585bf` |
| `D1_ENV_FREEZE.md` | `bb270f2bbd220d1b87546bd97db79e2ad63af1bd188b73847f0f9c7b884d73ec` |
| `README.md` | `023a5d9921566508014594591550a161373ff044b0272b9d6972a21099292315` |
| `tests/test_d1_selftest.py` | `e9584f2289099a4d5d476280c322e596d0d75f04a20bba825935e2e774a5087d` |

`sha256sum -c` 10/10 OK。读取器、验证器、驱动器的 git blob 与验收档案一致（`a8ae71ef…`、`703205fd…`、`df178f17…`）；`d1_env_manifest.py`、`d1_selftest_data.py`、`requirements-d1.txt`、`D1_ENV_FREEZE.md`、`README.md`、`tests/test_d1_selftest.py`、原始设计提案、Codespaces 日志与证据相对基准**无 diff**。

## 4. 环境与证据

- Python 3.13.8（Codespaces 隔离 venv `/workspaces/.venvs/openmythos-d1-py3138`），tokenizers 0.23.3，pyarrow 26.0.0，huggingface_hub 2.2.0。
- 原生环境证据：`gate3_d1/codespaces_env_logs/native_env_evidence_py3138.txt`，SHA-256 `e4e05c650e23a4a14b3327ca668d439871ad073747c66c752726d802166ccf1c`，本轮重新计算一致，未改动（验收文档 `F3B_D1_NATIVE_ENV_ACCEPTANCE_20261026.md`）。
- Codespaces 56 项 CPU 合成回归：56 PASS / 0 SKIP / 0 FAIL（`selftest_py3138.txt`，原样保留，SHA-256 以 `168741c0…` 开头）。**本轮没有在 Codespaces 重新运行。**

## 5. 本轮测试

| 项 | 执行环境 | 内容 | 结果 |
|---|---|---|---|
| 影响检查：合成测试套件 | **Claude 沙箱**，Python 3.13.16（不是 Codespaces 的 3.13.8），tokenizers 0.23.3，pyarrow 26.0.0 | 状态改动后、提交前运行一次，日志 `gate3_d1/final_freeze_logs/sandbox_impact_check_after_status_change.txt` | 56 项：54 PASS，1 skipped（`RealModeCodePath`，因 Python 补丁版本 ≠ 3.13.8，设计如此），**1 FAIL：`test_identity_labels`**（见第 6 节） |
| Git diff 范围 / `git diff --check` | 沙箱 | 仅 `D1_FROZEN_CONFIG.json`（2 行）与 `D1_CODE_SHA256SUMS`（1 行）等预期文件；`git diff --check` 无输出 | PASS |
| 配置 JSON 解析与结构化比较 | 沙箱 | 见第 2 节 | PASS |
| SHA-256 10/10 | 沙箱 | `sha256sum -c` | PASS |

沙箱结果**不能**替代 Codespaces 结果。

## 6. 已知限制（必须由项目负责人决定）

1. **测试里的过期哨兵断言与冻结状态冲突。** `tests/test_d1_selftest.py` 的 `test_identity_labels` 最后一行断言 `jread(CFG)["status"] != "FROZEN"`（注释：“the shipped config cannot yield a formal run yet”）。该断言本来就是为冻结前设计的哨兵，状态设为 `FROZEN` 后必然失败。本次授权明确禁止修改测试源码，所以**没有改**。后果：在冻结提交上运行完整套件会得到 1 个失败（其余 54 项通过，1 项按设计跳过；在 Codespaces 3.13.8 上预计 55 通过 + 1 失败，**未实测**）；CI 若运行该文件，会显示这 1 个失败。这不是运行逻辑的变化——被测代码未改。若要消除，需要单独授权改动该断言（最小改动：把该行改成断言 `== "FROZEN"` 或删除）；但测试文件在冻结清单内，改动会改变其 SHA-256，需要再次重新生成清单并重新验收，因此不应擅自处理。
2. `FROZEN` 状态使 `identity()` 的 `FORMAL_D1_CANDIDATE` 路径在代码上变得可达，但它还要求清单里的 `formal` 块（`authorization_ref`、`hub_revision`、`lfs_oid_parquet`、`tokenizer_fit_manifest_sha256`）。没有人创建过这样的清单，因此没有任何运行被授权。
3. 配置里的 `authorization.this_stage`（“code and frozen-config preparation only”）与 `pins_note` 中“No real WikiText acquisition or D1 execution authorized”保持原文，与冻结后的现实一致，未改。

## 7. 预期、实际与结论

| 项目 | 预期 | 实际 | 结论 |
|---|---|---|---|
| 最终冻结授权 | APPROVED | 项目负责人指令 | APPROVED |
| 来源基准 | `ebb45680…`，干净 | 一致 | PASS |
| `status` | `FROZEN` | 配置第 3 行 `"status": "FROZEN"`，解析验证 | PASS |
| JSON 完整性 | 可解析，键集合不变 | 是 | PASS |
| 10 项 SHA-256 | 10/10 | 10/10 | PASS |
| 核心实现与测试源码未改动 | 无 diff | 无 diff | PASS |
| 实验与授权约束未改变 | 结构化比较相同 | 相同 | PASS |
| 原生环境证据不变 | SHA-256 `e4e05c65…` | 一致 | PASS |
| 合成测试套件在冻结配置下全绿 | 全部通过 | 沙箱：1 FAIL（过期哨兵，见 6.1） | **FAIL（已知，已披露，等待决定）** |
| 真实 D1 | — | — | NOT TESTED / NOT AUTHORIZED |
| R6 剩余部分、R7、T1–T6、数据获取完整性 | — | — | NOT TESTED |
| 获取脚本、Tokenizer 拟合脚本、`runtime_manifest.json` 生成者 | — | 尚未编写 | NOT TESTED |
| D2 / D3 | — | — | NOT TESTED |

## 8. 下一条唯一研发指令

等待 ChatGPT 独立验收最终冻结提交，并由项目负责人决定 6.1 的哨兵断言如何处理。不得自动开始真实数据获取或 D1 实验。
