# F3-B / D1 — Codespaces 原生环境证据验收（最终归档）

**状态：`NATIVE ENVIRONMENT EVIDENCE: PASS / FINAL CONFIG FROZEN: NOT AUTHORIZED / REAL D1: NOT TESTED, NOT AUTHORIZED`**

追加式检查点，不覆盖历史文档；不改动读取器、验证器、驱动器、测试、实验参数、30 分钟限制和配置（`status` 仍是 `FROZEN_CANDIDATE__PENDING_ENV_ADAPTATION_REVIEW`，**未**设为 `FROZEN`）。

## 1. 目的、主机、输入

| 项 | 内容 |
|---|---|
| 目的 | 取得并核验项目负责人 Codespaces 的**原生**环境快照，关闭此前「执行主机环境 NOT VERIFIED / BLOCKED」一项 |
| 执行主机 | 项目负责人的 GitHub Codespaces（主机名 `codespaces-978a0f`，Linux 6.8.0-1064-azure，x86_64，2 CPU，7.8 GiB 内存），虚拟环境 `/workspaces/.venvs/openmythos-d1-py3138`，由项目负责人采集；本会话**不能**访问该主机，也没有用 Claude 沙箱代替 |
| 输入（Git） | 证据提交 `852f30e13ab108311b160c9d1b55c3823dfa9b51`（作者 Shuo Yu，只新增一个文件），其父提交 `ef6b51a59271b44ae5d0671fda8408b78aa26ba0` |
| 输入（文件） | `research/mini_mythos/gate3_d1/codespaces_env_logs/native_env_evidence_py3138.txt`，61 行，1671 字节 |
| 本会话的核验方式 | 从 GitHub 获取分支，确认远端 HEAD，快进到 `852f30e`，读取完整文件，重新计算 SHA-256，逐项与冻结配置和仓库文件比较（不依据指令文本宣布 PASS） |

## 2. 预期与实际

| 项 | 预期 | 实际 | 结论 |
|---|---|---|---|
| 文件 SHA-256 | `e4e05c650e23a4a14b3327ca668d439871ad073747c66c752726d802166ccf1c` | 本会话重新计算，完全一致 | PASS |
| 分支 HEAD / 变更范围 | 远端 `852f30e`；相对 `ef6b51a` 仅新增该证据文件 | 一致；`git diff --name-status` 只有 `A native_env_evidence_py3138.txt` | PASS |
| Python | 完整版本 `3.13.8`（配置 `python_full_version`） | `Python 3.13.8 (main, Sep 10 2026, 12:34:06) [GCC 13.3.0]` | PASS |
| 解释器与 venv | `/workspaces/.venvs/openmythos-d1-py3138/bin/python`，prefix 同目录 | executable、prefix 完全一致；`base_prefix` `/opt/python/3.13.8` | PASS |
| tokenizers / pyarrow / huggingface_hub | `0.23.3` / `26.0.0` / `2.2.0` | 导入版本与 `pip freeze` 两处都一致 | PASS |
| `pip freeze` | 已记录，含三项固定依赖 | 17 个包，无 torch / CUDA / triton 包 | PASS |
| `pip check` | 无损坏依赖，退出码 0 | `No broken requirements found.`，`pip_check_exit: 0` | PASS |
| 导入检查 | PASS | `IMPORT_CHECK: PASS` | PASS |
| CPU / OS | 记录 | Linux-6.8.0-1064-azure-x86_64，`cpu_count: 2`，内存 7.8Gi，无 swap | PASS（记录项） |
| Git 身份（采集时） | HEAD `ef6b51a`，分支正确，工作区干净 | HEAD `ef6b51a59271b44ae5d0671fda8408b78aa26ba0`，分支 `d1-codespaces-py3138-validation-20261026`，status 为空 | PASS |
| 冻结文件校验 | 10/10 OK | 证据里 10 行全部 `OK`；本会话在 `852f30e` 上独立运行 `sha256sum -c D1_CODE_SHA256SUMS`，同样 10/10 OK | PASS |
| 已验收文件未改动 | `ef6b51a..852f30e` 除证据文件外无差异；`selftest_py3138.txt` 原样 | 无差异；`selftest_py3138.txt` SHA-256 仍以 `168741c0…` 开头；配置 `status` 未变 | PASS |

采集时 HEAD 是 `ef6b51a` 而证据文件在 `852f30e` 才入库，这是预期的（证据文件在前一个提交上采集、之后才提交）。

## 3. 观察（非阻断）

1. 证据文件由项目负责人的采集脚本产生，版式与 `NATIVE_ENV_EVIDENCE_COLLECTION.md` 中的命令块不完全相同：没有 `ls -l`、`python -VV`、`lscpu`、`/etc/os-release`、`df`，但**要求的字段都在**（完整 Python 版本与路径、依赖版本、`pip freeze`、`pip check`、CPU/OS、时间、Git 状态、10 项校验）。
2. 文件末尾的 `NATIVE_ENV_CAPTURE: PASS` 和 `IMPORT_CHECK: PASS` 是采集脚本自报，本验收不依赖它们，而是按第 2 节独立核对了内容。
3. 采集时 `PYTHONHASHSEED`、`TOKENIZERS_PARALLELISM`、`CUDA_VISIBLE_DEVICES` 均未设置（`None`）。驱动器给子进程显式设置前两者并清空 `CUDA_VISIBLE_DEVICES`，`d1_env_manifest.py` 只在 `CUDA_VISIBLE_DEVICES` 非空时报问题，所以不影响；主机无 GPU 库（pip freeze 中无 torch/CUDA）。
4. 我一开始自己写的核对脚本里有一项把环境变量行 `CUDA_VISIBLE_DEVICES: None` 误当成 CUDA 包而报 FAIL；这是我的检查写法错误，不是证据问题，已改为只在 `pip freeze` 段内检查，结果无 torch/CUDA/triton。

## 4. 验收范围与正式状态

| 项 | 状态 |
|---|---|
| D1 CODE FREEZE（ChatGPT Work，C2b） | **PASS** |
| CODESPACES CPU SYNTHETIC REGRESSION（Python 3.13.8） | **PASS，56/56**（归档日志；0 SKIP，0 FAIL） |
| NATIVE ENVIRONMENT EVIDENCE | **PASS**（完整文件与 SHA-256 已核验） |
| FINAL CONFIG FROZEN（`status = FROZEN`） | **NOT AUTHORIZED** |
| REAL D1（真实 WikiText、正式 Tokenizer 拟合） | **NOT TESTED / NOT AUTHORIZED** |
| R6 剩余部分（读取前哈希与 validation/test 隔离）、R7、T1–T6、数据获取完整性 | **NOT TESTED** |
| 获取脚本、Tokenizer 拟合脚本、`runtime_manifest.json` 生成者 | 尚未编写 |
| D2 / D3 | **NOT TESTED** |

本验收**只**关闭「执行环境未核实」一项；原生环境 PASS 与合成回归 PASS 都不是真实 D1 的结果，也不构成任何真实数据执行授权。本轮没有重跑合成回归（证据中无实质性差异）。

## 5. 下一条唯一研发指令

等待项目负责人批准最终配置冻结提交（把 `status` 设为 `FROZEN`、重新生成 `D1_CODE_SHA256SUMS`、在含最新清单的提交上再核验）。批准之前不得下载数据、拟合 Tokenizer、运行真实 D1、训练、使用 GPU，也不得开始 D2/D3。
