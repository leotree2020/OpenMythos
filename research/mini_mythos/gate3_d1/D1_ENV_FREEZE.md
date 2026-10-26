# D1 CPU 执行环境与依赖冻结说明（FROZEN CANDIDATE，待 ChatGPT 复审）

状态：仅准备阶段。**没有**在任何真实数据上运行；执行主机上的版本与网络访问均 **NOT VERIFIED**。

| 项 | 冻结值（`D1_FROZEN_CONFIG.json` → `environment`） |
|---|---|
| 设备 | 仅 CPU；代码不导入 `torch`；`CUDA_VISIBLE_DEVICES` 必须为空（`d1_env_manifest.py` 检查，测试 `test_no_gpu_or_torch` 静态检查源码） |
| 并行 | 单进程、`num_workers=0`、无多进程并行；B 路径的 6 段是**串行**的 6 次独立进程调用（`python -I`） |
| Python | 次版本号允许 3.11 / 3.12 / 3.13；进程内 `sys.version` 写入 `RUN_META.json`。准备阶段沙箱为 3.13.16 |
| 库（real 模式强制） | `tokenizers==0.23.3`、`pyarrow==26.0.0`（准备阶段沙箱中均已安装并被自测实际调用）。`huggingface_hub==2.2.0` 只用于尚未编写的获取脚本。`numpy` 不被使用，不固定 |
| 环境变量 | `TOKENIZERS_PARALLELISM=false`，`PYTHONHASHSEED=0`，`CUDA_VISIBLE_DEVICES=""` |
| 资源（ESTIMATE，未实测） | 窗口 2048 行约 10⁵–10⁶ 个 Token；内存预计远低于 1 GB；每次读取器调用都会重新编码整个窗口以重建参照流，预计秒级到数十秒；墙钟硬上限 30 分钟 |
| 网络 | 读取器、验证器、驱动器、自测**不访问网络**。网络只在（尚未编写的）获取脚本中需要，并且需要有 `huggingface.co` 访问权限的 CPU 环境（本沙箱被代理 403 拒绝） |
| 依赖安装 | `pip install -r research/mini_mythos/gate3_d1/requirements-d1.txt`（执行主机上是否可得 NOT VERIFIED） |
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
