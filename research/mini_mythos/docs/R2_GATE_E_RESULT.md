# R2 Gate E — Tokenizer 绑定 Checkpoint 的 CPU 集成实测

**日期：2026-10-16。实际证据：用户在 GitHub Codespaces 运行并贴回控制台日志；测试文件与本地 .pt/manifest.json 未在本会话直接下载。**

## 实测内容

- 完整 `unittest`：**140/140 tests PASS**，耗时 **4.036 s**。
- `r2_pr27_guarded_checkpoint.py smoke --repo .` 在 **CPU** 上使用已缓存的官方 GPT-2 Tokenizer、4 维 Embedding/Head、50257 个 Token ID，完成一次真实的合成 AdamW 优化器更新：Loss **10.897187**。
- `smoke` 内置的保存后重载与随后独立运行 `verify --repo .` **两次**都返回 Tokenizer 身份、Contract、权重完整性 PASS。
- GPT-2 不可变 HF revision：`607a30d783dfa663caf39e06633721c8d4cfcd7e`；Embedding Tensor 实际行数 **50257**；重新加载的 checkpoint step 为 **1**。
- 验证了完整 token-ID/backend 指纹、Checkpoint Metadata、Sidecar JSON 中的 SHA-256 以及 `torch.load(weights_only=True)` 成功；之前的离线测试还覆盖了损坏 SHA、错误 Token ID、错误 Revision/Embedding 等在读权重前失败的路径。
- 终端明确声明：`Upstream PR27 train/evaluate patched: False`、`118M parameter GPU training performed: False`。

### 本地证据位置

- `research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.pt`
- `research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.manifest.json`

这两份在用户 Codespaces 的 Git 忽略目录，**没有上传至 GitHub**；本报告属于真实日志归档。

## Gate E 判定

**研究层 Tokenizer→Metadata→Checkpoint SHA→weights_only 安全读取的 CPU 全流程：PASS。**

但请明确区分：这只证明了隔离的 4 维 CPU 模型保存和读取边界，不代表 PR #27 的 `experiments/train.py` / `evaluate.py` 已受保护、正式训练可以精确恢复、HF 数据可不重不漏恢复、或 118M 模型已经在 GPU 上运行。

这里的 SHA-256 检查是防止意外损坏与不一致的**完整性**检查，**不属于恶意修改场景的可信来源认证或数字签名**。Sidecar 和权重可被同时重写的威胁模型仍需可信签名/外部 hash 锚。

## R2 Gate F：单 Worker 数据游标、随机数和 Optimizer 恢复可复现实验（未运行）

上一关未记录 FineWeb-Edu 的 streaming cursor / DataLoader prefetch queue。现新增 [r2_pr27_stream_resume.py](../scripts/r2_pr27_stream_resume.py) 和 [单元测试](../tests/test_r2_pr27_stream_resume.py)：

- 先在 CPU 的本地**合成 FineWeb-Edu 形状**（带 `id`/`text`）记录上，完全按 PR #27 的 tokenize→append EOS→seq_len+1 packed chunk→保留一个重叠 Token 的规则构造可保存的单 Worker Cursor；记录有序源 SHA、分割后的 train/heldout 文档 SHA、Tokenizer Contract SHA、next_doc_index、buffer IDs 和 emitted chunks。
- 保存 Python Random、显式 Torch Generator、完整 Tiny AdamW 参数和 Optimizer 状态到前一关已有的安全 checkpoint 形式，在输出文件中做一次真实的 interruption/resume。
- 比较连续 12 steps 与在第 5 step 停止、从 `.pt` + Sidecar 恢复后续 7 steps 的每批次 Token、循环选择、随机 mask、Loss、最终 Tensor 参数、Optimizer、Cursor、RNG 状态的逐字节相等性。
- **并不**下载真正的 FineWeb-Edu，不使用 PR27 原版多 Worker DataLoader、没有隐藏 Prefetch Queue、也没有 GPU 训练；此实验只能验证 Single Worker 协议的技术基础，**不能**关闭原版 `num_workers=2` 的生产数据游标 P0。

## 下一步 Codespaces 命令

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_stream_resume.py --repo .
```

若 Gate F 失败，应直接保留失败日志并修复研究层，不修改之前通过的 R1 Test、Gate E 权重或上游 `open_mythos/main.py`。
