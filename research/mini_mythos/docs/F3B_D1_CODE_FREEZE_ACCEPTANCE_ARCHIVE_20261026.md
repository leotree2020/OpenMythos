# F3-B / D1 — 代码冻结验收归档（C2b）与执行环境确认任务

**状态：`D1 CODE FREEZE ACCEPTED (C2b, ChatGPT Work: PASS) / D1 REAL EXPERIMENT NOT TESTED, NOT AUTHORIZED / EXECUTION ENVIRONMENT BLOCKED`**

本文件是追加式检查点，不覆盖任何历史实验文档；已验收的读取器、验证器、冻结配置未改动。

## 1. 验收记录

| 项 | 内容 |
|---|---|
| 已验收代码提交 | `0197c21ca38130e66d804961b85a15ee39634b26`（分支 `mini-mythos-p1c-gate22c-readiness`，开始本任务时本地与远端 HEAD 均为该提交，工作区干净） |
| 验收方 / 结论 | ChatGPT Work，独立 C2b 代码冻结验收，**PASS**（据项目负责人转述） |
| 证据范围 | 对 56 项 CPU 合成测试的**日志核验**（`gate3_d1/c2b_logs/selftest_output.txt`：`Ran 56 tests … OK`） |
| 限制 | 测试**未在独立环境重新执行**；Work 的审核原文不在仓库中，本记录只记载上述转述内容。56 项测试均为合成数据的代码自测，**不是 D1 证据** |
| 不构成 | 不是 D1 真实实验 PASS，不是 D1 CLOSED，不授权下载、拟合、训练、GPU、D2/D3 |

### 已验收文件的身份（取自提交 `0197c21c`）

| 文件 | git blob | SHA-256 |
|---|---|---|
| `gate3_d1/d1_reader.py` | `a8ae71ef1a03bcdce10d9979bf017742f912b96c` | `ab37c9123defbc736632e4e03db23764646dbbedd5842bfec7d72e5556b38bc0` |
| `gate3_d1/d1_verifier.py` | `703205fd4a9823cd74eaf8e221ef330bae2432d3` | `80007f9b9d0cd0a1137922e7a2ab4f7c7c7dd3b4cc1a1d82e560833c201199b6` |
| `gate3_d1/D1_FROZEN_CONFIG.json` | `69c175ac24a82dd7ba5a7ecabd546cc4a64dccbe` | `6f2ac7bbe703e19a2b8efc297ff3b7ff06211dbecfa9cf39c0371fdd5a60fabc` |
| `gate3_d1/d1_driver.py` | `df178f17de374172ef06fa0e45d9decd1311291a` | `111c01f25c9ea8d9978f0ca979ab64e29f8961ddf8dac9277363a1b7c6f5a209` |
| `gate3_d1/D1_CODE_SHA256SUMS` | `279335924300235694fe9368128dd127332f79d5` | `d231371815945cc0fc23d4a1fb6dca9ea4578a0327ca7734bf2caa1687dbecd4` |
| `tests/test_d1_selftest.py` | `b85351836b15581ee8821b0a1aa59e9292bd3095` | 见 `D1_CODE_SHA256SUMS` |

## 2. 仍未完成的状态

| 项 | 状态 |
|---|---|
| D1 真实实验（真实 WikiText / 真实 Tokenizer） | **NOT TESTED / NOT AUTHORIZED** |
| R6：读取前 Parquet 哈希与 validation/test 隔离（后半「读后哈希」已在验证器中，但仅对合成数据测过） | **NOT TESTED** |
| R7：validation/test 的哈希、行数、Token 数、round-trip | **NOT TESTED** |
| T1–T6：Tokenizer 验收与重复拟合确定性 | **NOT TESTED** |
| 数据获取完整性（Hub 文件列表、LFS oid、README/许可） | **NOT TESTED** |
| 数据获取脚本、Tokenizer 拟合脚本、`runtime_manifest.json` 生成者 | 尚未编写，需要单独授权 |
| 配置 `D1_FROZEN_CONFIG.json` 的 `status` 字段 | 仍为 `FROZEN_CANDIDATE__PENDING_CHATGPT_CODE_REVIEW`。代码验收通过**没有**改动它（已验收文件不得改）；因此驱动器的 `identity()` 仍不可能给出 `FORMAL_D1_CANDIDATE`。把它改成 `FROZEN` 是执行前的**冻结提交**步骤，需要负责人授权和新的审核 |
| 执行主机 Python 完整补丁版本与依赖组合 | **BLOCKED**（见第 3 节） |
| D2、D3 | **NOT TESTED** |

## 3. 只读核查计划执行环境

**结果：BLOCKED。** 指定的 Codespaces CPU 环境无法从本会话访问（证据：`gate3_d1/c2b_acceptance_logs/execution_env_access_probe.txt`）：`gh` 令牌无效，`gh codespace list` 返回 HTTP 403（会话被限定在仓库范围的端点），可用的 `claude-code-remote` 环境只有两个 Claude 自己的云沙箱，仓库内也没有 devcontainer 定义。

因此以下项**未核查**：执行环境的 Python 完整版本、`tokenizers`/`pyarrow`/`huggingface_hub` 实际版本、CPU/操作系统/可用内存、Git HEAD/分支/工作区状态，以及与冻结候选环境的差异。

**没有**把 Claude 沙箱当作执行环境。沙箱的早先盘点（`gate3_d1/c2_logs/env_inventory.txt`）只说明「自测环境与冻结候选一致」，不能代替执行环境。冻结配置中的候选版本**未改动**：Python `3.13.16`，`tokenizers 0.23.3`，`pyarrow 26.0.0`，`huggingface_hub 2.2.0`。

### 3.1 下一阶段的环境确认任务（由项目负责人在 Codespaces 内执行，只读）

在 Codespaces 终端的仓库根目录，把以下输出原样贴回（只读命令，不下载、不安装、不改文件）：

```
git rev-parse HEAD; git branch --show-current; git status --porcelain=v1
python3 -c "import sys,platform,os;print(sys.version);print(sys.executable);print('full','%d.%d.%d'%sys.version_info[:3]);print(platform.platform());print('cpus',os.cpu_count())"
python3 -c "import importlib.metadata as m
for k in ('tokenizers','pyarrow','huggingface_hub'):
    try: print(k, m.version(k))
    except Exception: print(k,'not installed')"
grep -E 'MemTotal|MemAvailable' /proc/meminfo; df -h . | tail -1
env | grep -E '^(CODESPACE_NAME|CUDA_VISIBLE_DEVICES|TOKENIZERS_PARALLELISM|PYTHONHASHSEED)=' | sed 's/CODESPACE_NAME=.*/CODESPACE_NAME=<set>/'
```

### 3.2 拿到输出后需要决定（均需负责人授权，本轮不做）

1. 把输出与冻结候选逐项比较；若 Python 完整补丁版本不是 `3.13.16`，或 `tokenizers`/`pyarrow` 与固定值不同，选择：改用与候选一致的环境，或在**新的冻结提交**里更新 `environment.python_full_version` 与 `pins` 并重新审核。real 模式在版本不符时会 BLOCKED。
2. 确认 `huggingface_hub` 的固定版本（只有尚未编写的获取脚本使用）。
3. 在执行环境内先跑一次 `python -m unittest research/mini_mythos/tests/test_d1_selftest.py`（合成自测，不下载）作为**独立环境重跑**——这正是 Work 日志核验之外尚未完成的一步。
4. 然后才轮到：获取脚本与 Tokenizer 拟合脚本的编写与审核、`FROZEN` 冻结提交、真实 D1 的执行授权。

## 4. 下一条唯一研发指令

项目负责人在指定 Codespaces CPU 环境内执行 3.1 的只读命令并回传输出（可选：同时在该环境跑一次合成自测）。在此之前，且未获新的真实数据执行授权前，不得下载数据、拟合 Tokenizer、执行 D1、训练、使用 GPU，不得开始 D2/D3。

---

**最终状态：`D1 CODE FREEZE ACCEPTED (C2b) / D1 REAL EXPERIMENT NOT TESTED, NOT AUTHORIZED / EXECUTION ENVIRONMENT BLOCKED`。** 未宣布 D1 PASS 或 CLOSED。
