# F3B-D1 — 冻结后 CPU 回归证据归档与 Closeout

**状态：`READY FOR CLOSEOUT / CROSS-REVIEW PENDING`**（Grok 对最终哨兵修复差异的交叉审核尚未取得，不冒称完成，因此不标记 CLOSED）

追加式检查点；保留所有历史记录。范围：F3B-D1 **配置与环境准备**，不含真实 D1。

## 1. Git 与输入

| 项 | 内容 |
|---|---|
| 分支 | `d1-final-freeze-sentinel-fix-20261026` |
| 修复基准 | `6b57087c595ce795333c6636dceb32ff5b61fef3` |
| 日志提交 | `1298619e163af6257d206134e5ed031e0082947f`（作者 Shuo Yu；相对修复基准**只新增**一个文件） |
| 本会话核对方式 | 获取远端分支，快进到 `1298619`，完整读取日志（100 行，19038 字节），重新计算 SHA-256，并在该提交上重新核对冻结清单、配置、测试 diff |
| 前序冻结 | 最终配置冻结提交 `9e257788c0510d5e263d5256d4bd3cebebdb8057`（保留不变） |

## 2. 测试环境与输入

- 执行主机：项目负责人的 Codespaces，Python `3.13.8 (main, Sep 10 2026, 12:34:06) [GCC 13.3.0]`，虚拟环境 `/workspaces/.venvs/openmythos-d1-py3138`（原生环境证据已验收，见 `docs/F3B_D1_NATIVE_ENV_ACCEPTANCE_20261026.md`）。
- 依赖：tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0（固定值，未变）。
- 输入：`tests/test_d1_selftest.py` 的 56 项 CPU 合成测试；合成 `rows.jsonl`/合成 Parquet 与手工构造、未训练的字节级 BPE；日志头部标注 `mode: CPU_SYNTHETIC_ONLY`、`git_head: 6b57087c…`、生成时间 `2026-10-26T11:52:31Z`。**不是**真实 D1，没有真实数据，没有正式 Tokenizer。

## 3. 预期与实际

| 项 | 预期 | 实际（本会话据远端原始日志复核） | 结论 |
|---|---|---|---|
| 日志 SHA-256 | `be1bff0493a4da59c71b962188ac1bc3a5766b6caa26a419ea23a0ceae6fac1e` | 重新计算一致 | PASS |
| 日志提交范围 | 仅新增日志 | `A research/mini_mythos/gate3_d1/sentinel_fix_logs/codespaces_regression_py3138.txt` | PASS |
| 测试数量 | 56，且与源码一致 | 56 行唯一测试名，与源码中定义的 56 个完全一致，无缺失、无多余 | PASS |
| 结果 | 全部 ok | 55 行以 `... ok` 结尾；另 1 个测试的 `ok` 被其输出夹杂挪到行尾；摘要 `Ran 56 tests in 50.656s` / `OK` | PASS |
| SKIP / FAIL / ERROR | 0 / 0 / 0 | `skipped` 出现 0 次；`... FAIL`/`... ERROR` 0 次；unittest 的 `FAIL:`/`ERROR:` 标记 0 次；`Traceback` 0 次 | PASS |
| 退出码 | 0 | `unittest_exit: 0` | PASS |
| `test_identity_labels` | 通过 | `... ok` | PASS |
| `test_real_mode_pipeline` | 通过（合成，非真实 D1） | `... ok`，未被跳过 | PASS |
| 日志头部身份 | HEAD = 修复基准，Python 3.13.8 | `git_head: 6b57087c…`；`Python 3.13.8` | PASS |
| 冻结清单 | 10/10 OK | 本会话在 `1298619` 上 `sha256sum -c` 10/10 OK（Codespaces 日志本身未包含这一项，见第 5 节） | PASS |
| 配置 | `status = FROZEN`，哈希 `0d35dc21a4beca7c2f93fc11df6806ea7bc321d2376f52e1552863f19e7d7aaa` | 一致，第 3 行 `"status": "FROZEN"` | PASS |
| Reader / Verifier / Driver / 配置 / `d1_env_manifest.py` / `d1_selftest_data.py` / `requirements-d1.txt` / `README.md` / Codespaces 环境日志与证据 | 相对冻结提交 `9e257788` 无 diff | 无 diff | PASS |
| 测试文件相对冻结提交的变化 | 仅哨兵断言一行 | `-assertNotEqual(status,"FROZEN")` → `+assertEqual(status,"FROZEN")`，仅此一处 | PASS |
| 原生环境证据 | SHA-256 `e4e05c65…ccf1c` 不变 | 一致 | PASS |

## 4. 验收状态

| 项 | 状态 |
|---|---|
| D1 代码冻结 | **PASS** |
| 最终配置状态 `FROZEN` | **PASS** |
| Codespaces Python 3.13.8 原生环境 | **PASS** |
| 冻结后 56 项 CPU 合成回归 | **PASS**（以远端原始日志复核为准） |
| 代码变更范围审核 | **PASS** |
| Grok 对最终哨兵修复差异的交叉审核 | **PENDING**（仓库内没有对应记录，本会话也未收到） |
| F3B-D1 配置与环境准备范围 | **READY FOR CLOSEOUT / CROSS-REVIEW PENDING**；交叉审核完成后可标记 CLOSED |
| 真实 D1 | **NOT TESTED / NOT AUTHORIZED** |
| R6 剩余部分、R7、T1–T6、真实数据获取、数据获取完整性 | **NOT TESTED** |
| 获取脚本、Tokenizer 拟合脚本、`runtime_manifest.json` 生成者 | 尚未编写 |
| D2 / D3 | **NOT TESTED** |

## 5. 观察（非阻断）

1. Codespaces 日志头部只有 `generated_utc`、`git_head`、Python 版本和 `mode`，**没有**工作区状态（`git status`）和 `sha256sum -c` 输出；第 5 节命令块里要求的这两项没有被写进日志。冻结清单 10/10 与工作区状态在 Codespaces 侧因此没有直接证据；本会话在同一内容的提交上独立核对了清单（10/10）。原生环境证据（`native_env_evidence_py3138.txt`）在更早提交上已含 Codespaces 的 10/10 与干净工作区记录。
2. 日志里有一个测试的 `ok` 因其输出夹杂而出现在行尾而不是单独一行，是 unittest 对 stdout 输出的交错，不影响结果。
3. 冻结配置里的 `authorization` 段未变；`status = FROZEN` 只使 `identity()` 的正式身份路径在代码上可达，没有任何清单携带 `formal` 块，因此没有真实 D1 被授权。

## 6. 下一条唯一研发指令

获取 Grok 对「最终哨兵修复差异」（`tests/test_d1_selftest.py` 一行、`D1_ENV_FREEZE.md` 状态文字、清单两行）的交叉审核；取得 PASS 后，将 F3B-D1 配置与环境准备范围标记 CLOSED。真实 D1 需要项目负责人另行、明确地授权（包括获取脚本与 Tokenizer 拟合脚本的编写与审核），本检查点不构成该授权。不开展新的微型实验。
