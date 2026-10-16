# R2 Gate B — 上游 PR #27 源码冻结审计（CPU 优先）

**2026-10-16；审计对象是社区 [OpenMythos PR #27](https://github.com/kyegomez/OpenMythos/pull/27) 的原始提交，固定完整 SHA `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`。** 本报告已通过 GitHub 读取该 Commit 中的 6 个 `experiments/` 文件及当前 fork `open_mythos/main.py`；**尚未在用户 Codespaces 运行审计脚本，也没有训练 117.8M 模型或验证作者报告的性能**。

## R2 Gate A 当前容器结论

在用户现有 Codespaces，110/110 tests PASS，PyTorch 2.14.1+cu130，**`torch.cuda.is_available() == False`, CUDA device count 0**，空余磁盘 13.06 GiB。它可以继续 CPU 代码审计/微型测试；不是 GPU 训练环境。完整日志归档见 [R2 Gate A](R2_GATE_A_ENVIRONMENT.md)。

## PR #27 固定 Commit 里实际上有什么

| 文件 | GitHub 来源 | 审计摘要 |
|---|---|---|
| `experiments/config.py` | PR27 SHA | `mythos_150m()` 实例参数：dim 768，n_heads12，MLA，n_experts16，top-k2，expert_dim1536，max_loop_iters8，tokenizer gpt2；PR 作者声称实际约 117.8M 参数，**本 fork 还未独立实例化/计数验证** |
| `experiments/data.py` | PR27 SHA | Streaming `HuggingFaceFW/fineweb-edu`，配置 `sample-10BT`，多 Worker shard，附加 EOS；数据集没有固定不可变 revision、没有可恢复游标 |
| `experiments/train.py` | PR27 SHA | CUDA BF16 单卡、AdamW、固定/随机循环深度、梯度累积；Checkpoint 保存 `model/opt/cfg/mcfg/tokens_seen`，没有 RNG 或数据位置；无 resume 加载功能 |
| `experiments/evaluate.py` | PR27 SHA | `--loop_grid` 深度扫描，`--skip_docs 2_000_000` 作为估计的分割；评估可通过 `--tokenizer` 使用与训练不同的 Tokenizer，加载 `weights_only=False` |
| `experiments/run_all.sh` | PR27 SHA | `/workspace/OpenMythos`/`/workspace/runs` 路径硬编码，执行 8-loop 和 1-loop 两条不同计算深度的训练；实际需要 GPU，不适合直接在当前 Codespaces 执行 |
| `experiments/README.md` | PR27 SHA | 作者自报单卡 48+GB GPU，两个模型各 15k steps 等实验配置和数小时运行预期；**时间和质量未在本项目验证** |

### P0：BF16 整模型转换会破坏复数 RoPE 相位

PR27 `train.py` 使用：

```python
model = OpenMythos(mcfg).to(device=device, dtype=dtype)
```

其中 `dtype=torch.bfloat16`，但当前 fork 的 `open_mythos/main.py` 把 RoPE 预计算表作为 `complex64` buffer 注册：

```python
self.register_buffer('freqs_cis', freqs)
self.register_buffer('freqs_cis_mla', freqs_mla)
```

PyTorch 的 `nn.Module.to(dtype=torch.bfloat16)` 会将**复数 Buffer 转成实数 BF16 并丢失虚部**。我们已在单独 CPU PyTorch 2.10.0 的极简 4 元素 buffer 上**动态复现该一般 PyTorch 行为**：`complex64 → bfloat16`，触发 `Casting complex values to real discards the imaginary part` 警告。**对于真实 OpenMythos buffer 在用户 PyTorch 2.14.1+cu130 上的表现，尚需新 `r2_rope_dtype_probe.py` 测试确认。**

如果复现，RoPE 不再是完整单位复数相位旋转，而变成与位置相关的实数缩放，可能造成训练质量和位置编码数学错误；即使 forward 没抛异常也不意味着正确。此风险**独立于** [PR #26](https://github.com/kyegomez/OpenMythos/pull/26) 所述 ACT FP32 promotion / mask dtype 问题，单纯合并 PR26 不能证明保护了复数 RoPE。修复思路须先经审查：保留复数 RoPE buffer 的 `complex64`，让真实 Linear 层 BF16 路径与 ACT 计算保持兼容，或采用混合精度 autocast 而非盲目强制转换整个 Module；在真实 GPU 评估精度/速度前不修改上游核心源码。

### P0：Tokenizer / 恢复 / 验证链路

- `train.py` 中 `get_tokenizer(cfg.tokenizer)`，而 `evaluate.py` 独立从 `get_tokenizer(args.tokenizer)` 加载 Tokenizer。虽然默认都是 `gpt2`，但允许 CLI 改变可能使 Token ID 不一致；PR #27 的 GitHub 机器人审查也指出此点。应将训练 Tok name/revision/vocab special IDs 写入 Checkpoint，并在评估时强制核对。**光核对 vocab_size 不足以保证 token ID 映射相同**。
- FineWeb-Edu `streaming=True` 未固定 dataset revision。`--skip_docs 2_000_000` 的无重叠声明依赖训练文档数估算与不变数据顺序，没有保存训练实际最后文档索引作为证明。
- PR27 `train.py` 无恢复入口；保存模型/优化器但没有 Python/Torch/CUDA RNG 和 loader state。不能按 R1 那样保证恢复训练后每批数据完全相同。
- 作者并没有在 `train.py` 中做严格 Heldout 验证；只是训练完成后由 `evaluate.py` 切到估计避开前段的同一个 Streaming train split。应建立真正不可变、排除泄漏的独立 test/eval 数据链路。

### P1：原本不是等 FLOPs/参数的 Transformer 基线

- `baseline_1` 是仍包含 `RecurrentBlock`、LTI Injection、ACT、MoE 的 **单循环 OpenMythos**，**不是普通非递归 Transformer**；适合当 loop-depth 消融，但不具备独立架构基线的性质。
- 循环深度 8 vs 1 显著改变训练计算；只有比较每步训练 Token 数并不等于比较计算量。`max_loop_iters` 又控制 `LoRAAdapter.scale` 的 embedding 行数，参数量差异至少为 `7 × lora_rank = 112` 个 scale 元素（PR27 rank=16）。不能说两套完全相同参数和 FLOPs。
- Router Bias 虽存在，但 upstream PR27 训练没有显式负载统计反馈与 Bias 更新；MoE 路由健康要用 per-expert token counts、dead experts、load CV、梯度实际验证。

## 不下载模型即可在 Codespaces 复核 PR 原始代码

以下 git fetch **仅抓取 PR 提交的 Git 对象**到新的远程引用，不合并到研究分支或改写已有模型：

```bash
git pull --ff-only origin mini-mythos-research
git fetch https://github.com/kyegomez/OpenMythos.git \
  refs/pull/27/head:refs/remotes/pr27-audit
git rev-parse refs/remotes/pr27-audit
```

输出 HEAD 必须与冻结 SHA `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4` 一致；若 PR HEAD 发生变化，**不要用新 HEAD 替换冻结版本**，优先按原 commit SHA 获取历史对象并记录为何发生变化。我们的审计程序始终读该固定 SHA：

```bash
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_static_audit.py --repo .
python research/mini_mythos/scripts/r2_rope_dtype_probe.py --repo .
```

结果写到 `research/mini_mythos/results/r2/pr27_static_audit.json` 和 `rope_bf16_cpu_probe.json`，记录上游各个源码文件 SHA256、静态问题标记、实际 CPU RoPE buffer 转换现象。**这些新脚本已提交但还未得到用户 Codespaces 运行结果**；若静态规则 FOUND，仅表示某段源码存在对应证据，不代表 GPU 训练已发生。

## R2 真正的放大门槛

在选择/申请云 GPU 之前，必须完成：固定 PR 源码、保护复数 RoPE 相位、BF16 数学一致性、Tokenizer ID/hash、真正 Test/heldout 隔离、Resume + Data Cursor + RNG、MoE 负载追踪、显卡显存与预算；之后才可以批准小规模 GPU smoke（1–10 steps），而不是立刻跑 15k steps × 多组。项目不自动创建云资源，不要求在本地或公司 PC 安装软件。

**开源 PR 不等于 Anthropic 内部 Mythos 架构。** 当前结论仅属于社区独立实现代码的可靠性与复现研究。
