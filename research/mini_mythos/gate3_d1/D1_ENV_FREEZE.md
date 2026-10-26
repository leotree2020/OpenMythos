# D1 CPU 执行环境与依赖冻结说明（FROZEN CANDIDATE，待 ChatGPT 复审）

状态：仅准备阶段。**没有**在任何真实数据上运行；执行主机上的版本与网络访问均 **NOT VERIFIED**。

| 项 | 冻结值（`D1_FROZEN_CONFIG.json` → `environment`） |
|---|---|
| 设备 | 仅 CPU；代码不导入 `torch`；`CUDA_VISIBLE_DEVICES` 必须为空（`d1_env_manifest.py` 检查，测试 `test_no_gpu_or_torch` 静态检查源码） |
| 并行 | 单进程、`num_workers=0`、无多进程并行；B 路径的 6 段是**串行**的 6 次独立进程调用（`python -I`） |
| Python | **real 模式要求完整补丁版本精确等于 `environment.python_full_version`（候选固定值 `3.13.16`，即 `tokenizers 0.23.3` + `pyarrow 26.0.0` 自测所用的解释器；**执行主机上未核实**，项目负责人需确认主机的完整版本与依赖组合并重新冻结本文件后才可正式运行；不符 → BLOCKED）。selftest 模式只要求次版本在 3.11/3.12/3.13 之内（标准库路径，供 CI 使用） |
| 库（real 模式强制） | `tokenizers==0.23.3`、`pyarrow==26.0.0`（准备阶段沙箱中均已安装并被自测实际调用）。`huggingface_hub==2.2.0` 只用于尚未编写的获取脚本。`numpy` 不被使用，不固定 |
| 环境变量 | `TOKENIZERS_PARALLELISM=false`，`PYTHONHASHSEED=0`，`CUDA_VISIBLE_DEVICES=""` |
| 资源（ESTIMATE，未实测） | 窗口 2048 行约 10⁵–10⁶ 个 Token；内存预计远低于 1 GB；每次读取器调用都会重新编码整个窗口以重建参照流，预计秒级到数十秒；墙钟硬上限 30 分钟 |
| 网络 | 读取器、验证器、驱动器、自测**不访问网络**。网络只在（尚未编写的）获取脚本中需要，并且需要有 `huggingface.co` 访问权限的 CPU 环境（本沙箱被代理 403 拒绝） |
| 依赖安装 | `pip install -r research/mini_mythos/gate3_d1/requirements-d1.txt`（执行主机上是否可得 NOT VERIFIED） |
| 超时 | 30 分钟墙钟硬上限由 `d1_driver.py` 执行：每个子进程用剩余时间做 `timeout`，上限是代码常量 1800 秒：**real 模式拒绝任何 `--timeout-seconds` 覆盖**，配置里的上限若不等于 30 分钟也拒绝（BLOCKED），selftest 的覆盖只能缩短；超时即杀掉该步，判 `BLOCKED(timeout)`，**保留磁盘上已有证据，不自动重试**，决定文件列出超时时已有的证据文件。上限范围是驱动器流水线；尚未编写的获取/Tokenizer 拟合脚本须计入同一个 30 分钟 |
| 身份标签 | `d1_driver.py` 的 `identity`：`SELFTEST_SYNTHETIC` / `REAL_CODE_PATH_NON_FORMAL` / `FORMAL_D1_CANDIDATE`。只有 `mode=real`、配置 `status == "FROZEN"`、清单含 `formal{authorization_ref, hub_revision, lfs_oid_parquet == parquet_sha256, tokenizer_fit_manifest_sha256}` 且非合成时才是 `FORMAL_D1_CANDIDATE`；合成 Parquet + 手工 BPE 永远是 `REAL_CODE_PATH_NON_FORMAL`。这是记账标签，不是安全边界 |
| 环境记录 | `d1_env_manifest.py` 进程内记录 Python、平台、库版本、环境变量、`git rev-parse HEAD`、`git status --porcelain=v1`，与上表比对，不符 → exit 4 = BLOCKED，不现场调整 |

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

读取器：0 正常；3 游标被拒；4 BLOCKED（输入/前置条件）；5 自检失败。驱动器把 4 映射为 BLOCKED，其余非预期码映射为 FAIL。验证器：0 PASS / 1 FAIL / 4 BLOCKED，且结果文件必须存在并与退出码一致才算 PASS；缺失、畸形、不一致、异常退出一律 FAIL（退出码 4 且无结果文件为 BLOCKED）。驱动器自身异常也会写入决定文件（`driver_exception`，FAIL）。驱动器退出码：PASS 0，FAIL 1，BLOCKED 4。
