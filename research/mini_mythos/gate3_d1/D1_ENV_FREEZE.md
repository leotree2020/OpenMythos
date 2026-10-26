# D1 CPU 执行环境与依赖冻结说明（FROZEN CANDIDATE；Codespaces 环境适配审核 PASS；正式配置冻结 NOT AUTHORIZED）

状态：**没有**在任何真实数据上运行；真实 D1 `NOT TESTED / NOT AUTHORIZED`。Codespaces 环境适配（Python 3.13.8）已通过 ChatGPT 审核与交叉审核（均 PASS，限定为合成回归层面）；配置 `status` 仍是 `FROZEN_CANDIDATE__…`，**未**设为 `FROZEN`，正式配置冻结尚未授权。执行主机的**原生环境快照**（解释器路径、`pip freeze`、`pip check`、CPU/OS、Git 状态）尚未归档，状态 **BLOCKED（待项目负责人回传）**，见下文「Codespaces 环境适配结果与证据状态」。

| 项 | 冻结值（`D1_FROZEN_CONFIG.json` → `environment`） |
|---|---|
| 设备 | 仅 CPU；代码不导入 `torch`；`CUDA_VISIBLE_DEVICES` 必须为空（`d1_env_manifest.py` 检查，测试 `test_no_gpu_or_torch` 静态检查源码） |
| 并行 | 单进程、`num_workers=0`、无多进程并行；B 路径的 6 段是**串行**的 6 次独立进程调用（`python -I`） |
| Python | **real 模式要求完整补丁版本精确等于 `environment.python_full_version`，当前候选固定值为 `3.13.8`**（项目负责人的 Codespaces 隔离 CPU 虚拟环境 `/workspaces/.venvs/openmythos-d1-py3138`；早先的候选值 `3.13.16` 是 Claude 沙箱自测所用的解释器，已被取代，仅留在历史文档里）。不符 → BLOCKED。selftest 模式只要求次版本在 3.11/3.12/3.13 之内（标准库路径，供 CI 使用） |
| 库（固定版本） | `tokenizers==0.23.3`、`pyarrow==26.0.0`（real 模式强制检查）；`huggingface_hub==2.2.0`（只用于尚未编写的获取脚本，读取器/验证器不导入它）。`numpy` 不被使用，不固定。这三个固定版本相对此前的候选**没有改变**；据 Codespaces 环境适配检查点，它们在 3.13.8 环境中已安装、可导入、`pip check` PASS |
| 环境变量 | `TOKENIZERS_PARALLELISM=false`，`PYTHONHASHSEED=0`，`CUDA_VISIBLE_DEVICES=""` |
| 资源 | 窗口 2048 行约 10⁵–10⁶ 个 Token（ESTIMATE）；内存预计远低于 1 GB（ESTIMATE）；每次读取器调用都会重新编码整个窗口以重建参照流。Codespaces 上 56 项合成自测耗时 48.115 s（来自归档日志；该环境据检查点为 2 CPU，原生快照待回传）；墙钟硬上限 30 分钟 |
| 网络 | 读取器、验证器、驱动器、自测**不访问网络**。网络只在（尚未编写的）获取脚本中需要，并且需要有 `huggingface.co` 访问权限的 CPU 环境（本沙箱被代理 403 拒绝） |
| 依赖安装 | `pip install -r research/mini_mythos/gate3_d1/requirements-d1.txt`；Codespaces 隔离 venv 中的安装与 `pip check PASS` 目前仅见于环境适配检查点的陈述，原生 `pip freeze` / `pip check` 输出尚未归档（BLOCKED，待回传） |
| 超时 | 30 分钟墙钟硬上限由 `d1_driver.py` 执行：每个子进程用剩余时间做 `timeout`，上限是代码常量 1800 秒：**real 模式拒绝任何 `--timeout-seconds` 覆盖**，配置里的上限若不等于 30 分钟也拒绝（BLOCKED），selftest 的覆盖只能缩短；超时即杀掉该步，判 `BLOCKED(timeout)`，**保留磁盘上已有证据，不自动重试**，决定文件列出超时时已有的证据文件。上限范围是驱动器流水线；尚未编写的获取/Tokenizer 拟合脚本须计入同一个 30 分钟 |
| 身份标签 | `d1_driver.py` 的 `identity`：`SELFTEST_SYNTHETIC` / `REAL_CODE_PATH_NON_FORMAL` / `FORMAL_D1_CANDIDATE`。只有 `mode=real`、配置 `status == "FROZEN"`、清单含 `formal{authorization_ref, hub_revision, lfs_oid_parquet == parquet_sha256, tokenizer_fit_manifest_sha256}` 且非合成时才是 `FORMAL_D1_CANDIDATE`；合成 Parquet + 手工 BPE 永远是 `REAL_CODE_PATH_NON_FORMAL`。这是记账标签，不是安全边界 |
| 环境记录 | `d1_env_manifest.py` 进程内记录 Python、平台、库版本、环境变量、`git rev-parse HEAD`、`git status --porcelain=v1`，与上表比对，不符 → exit 4 = BLOCKED，不现场调整 |

## Codespaces 环境适配结果与证据状态

| 项 | 状态 | 依据 |
|---|---|---|
| Python 3.13.8 下 56 项 CPU 合成测试，含 `--mode real` 合成代码路径（合成 Parquet + 手工构造、未训练的字节级 BPE） | **PASS：56 PASS，0 SKIP，0 FAIL**（耗时 48.115 s） | 原始日志 `gate3_d1/codespaces_env_logs/selftest_py3138.txt`（原样保留，SHA-256 `168741c0…46f1`）。`test_real_mode_pipeline` 只在 Python 完整版本与库版本等于配置固定值时才运行，日志里它是 ok 而不是 skipped，间接支持该主机的 Python 为 3.13.8 且 tokenizers/pyarrow 与固定值一致 |
| 环境适配审核 | **PASS**（ChatGPT 独立审核；交叉审核；限定在合成回归与配置差异层面） | 检查点 `docs/F3B_D1_CODESPACES_PY3138_CHECKPOINT_20261026.md` |
| 原生环境快照（解释器完整版本与路径、`pip freeze`、`pip check`、CPU/OS、虚拟环境路径、生成时间、Git HEAD/分支/工作区状态） | **BLOCKED：尚未归档**。Claude 会话无法访问 Codespaces（`gh codespace list` HTTP 403；没有 `/workspaces`），不得用沙箱输出冒充 | 采集命令见 `gate3_d1/codespaces_env_logs/NATIVE_ENV_EVIDENCE_COLLECTION.md`，等待项目负责人回传 |
| 真实 D1（真实 WikiText、正式 Tokenizer 拟合） | **NOT TESTED / NOT AUTHORIZED** | — |
| R6 读取前部分、R7、T1–T6、数据获取完整性 | **NOT TESTED** | 见下文「流水线尚未覆盖」 |
| 正式配置冻结（`status = "FROZEN"`） | **NOT AUTHORIZED**；本文件不宣布冻结 | 需要项目负责人授权与新的冻结提交 |

环境适配 PASS 只说明：在 Codespaces 的 Python 3.13.8 CPU 环境里，已验收的读取器、验证器、驱动器与合成测试行为一致。它**不是**真实 D1 的任何结果。

## 运行方式（执行授权之前**不得**对真实数据运行）

```
python research/mini_mythos/gate3_d1/d1_driver.py all --workdir <新目录> --mode real \
  --config research/mini_mythos/gate3_d1/D1_FROZEN_CONFIG.json --manifest <runtime_manifest.json> \
  --source parquet:<train.parquet> --tokenizer <tokenizer.json>
```

`runtime_manifest.json`（获取与 Tokenizer 拟合之后才存在，本阶段不存在）至少含 `parquet_sha256`、`tokenizer_sha256`、`actual_vocab_size`。

## 代码自测（合成数据，不是 D1 结果）

```
python -m unittest research/mini_mythos/tests/test_d1_selftest.py
```

`--mode selftest` 使用标准库字节编码器和合成 `rows.jsonl`；若安装了 pyarrow 与 tokenizers，额外用**手工构造、未训练**的字节级 BPE（无拟合）和合成 Parquet 跑一遍 `--mode real` 代码路径。

## 流水线尚未覆盖（NOT TESTED）

驱动器输出里的 `d1_overall` 恒为 `NOT_DECLARED__PIPELINE_INCOMPLETE`，`read_resume` / `negatives_meta` 只是分项结论，**不是** D1 总体结论。未覆盖项：R6 的读取前哈希与 validation/test 隔离、R7、T1–T6（Tokenizer 验收与重复拟合确定性）、数据获取完整性（Hub 列表、LFS oid、README/许可）。

## 退出码约定（C2）

读取器：0 正常；3 游标被拒；4 BLOCKED（输入/前置条件）；5 自检失败。驱动器把 4 映射为 BLOCKED，其余非预期码映射为 FAIL。验证器：0 PASS / 1 FAIL / 4 BLOCKED，且结果文件必须存在并与退出码一致才算 PASS；缺失、畸形、不一致、异常退出一律 FAIL；**唯一**的 BLOCKED 例外是退出码 4 且结果文件**不存在**（文件存在但畸形/未知 verdict/与退出码不符 → FAIL）。多项结果聚合时 **FAIL 优先于 BLOCKED**，每项状态明细保留（C2a）。驱动器自身异常也会写入决定文件（`driver_exception`，FAIL）。驱动器退出码：PASS 0，FAIL 1，BLOCKED 4。
