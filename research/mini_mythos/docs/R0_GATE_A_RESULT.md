# R0 Gate A — 第一轮运行结果与 KV Cache 根因验证

**日期**：2026-10-16。**证据来源**：用户 Codespaces 终端输出；原始 JSON 留在 Codespaces 的 Git 忽略目录，未独立读取。没有 Anthropic 私有模型参与本次实验。

## 1. 已经实际执行并确认的结果

- 已在 `mini-mythos-research` 分支同步到 `1a6d9e9`。
- 全套单元测试：**60/60 PASS**（22.292 s）。
- `r0_audit.py`：识别原型架构和训练/Tokenizer 的若干研究准备度 GAP；这是文本模式审计，不是行为测试。
- `r0_probe.py`：
  - GQA tiny model + AdamW checkpoint 保存、恢复、下一步训练对齐：**PASS**。
  - MLA tiny model + AdamW checkpoint 保存、恢复、下一步训练对齐：**PASS**。
  - GQA 多 Token 缓存分块（6-token 前缀 + 2-token 新 chunk）：**FAIL**。
  - MLA 多 Token 缓存分块（相同场景）：**FAIL**。
  - 两项 FAIL 均报告 `The size of tensor a (8) must match the size of tensor b (2) at non-singleton dimension 3`。

上述失败发生在多 token **cached chunk** 场景，**不意味着单 token 的缓存生成一定错误**；先前的单 token Cache 等价 smoke 已通过。

## 2. 根因假设（静态源码依据）

- `open_mythos/main.py:1023`：`mask = self._causal_mask(T, device, x.dtype) if T > 1 else None`；
- `OpenMythos._causal_mask` 只构造 `T × T`；
- `main.py:239-243` 的 GQA 和 `main.py:391-395` 的 MLA 都会将缓存的 K/V 或压缩 latent 拼接到现有 Token 之前；
- 在前缀 `P=6`、新增 chunk `T=2` 时，Attention logits 是 `2 × 8`，却试图和 `2 × 2` mask 相加；报错和形状分析吻合。

对有前缀的 causal chunk，正确掩码是 `(1, 1, T, P+T)`，第 `i` 个新增 Token 可见所有列 `0..P+i`。

**验证状态**：形状根因有源码和运行错误支持；完整修复是否足以恢复 GQA/MLA logits 等价，仍需下一轮实验确认。

## 3. 研究分支的非侵入修复实验

- [r0_cache_mask.py](../scripts/r0_cache_mask.py)：建立正确前缀掩码，检查 cache 条目长度与 `start_pos` 一致；在单次推理中给**模型实例**临时覆盖 `_causal_mask` 并确保恢复。
- [r0_cache_compare.py](../scripts/r0_cache_compare.py)：在**同一权重**下分别跑原版和修正 mask 的 prefix/chunk 推理，与完整非缓存 forward 进行输出比较；生成 JSON。
- [test_r0_cache_mask.py](../tests/test_r0_cache_mask.py)：验证掩码矩阵、异常恢复、错误参数，以及 GQA/MLA 真实微模型的 full-vs-chunk 数值等价。
- 对之前参数差异的 PyTorch warning，`r0_probe.py` 已改为 `detach()` 后取数值。

该补丁 **不改写** `open_mythos/main.py`。它是仅用于串行研究的 instance-level 临时覆盖方案，**不支持共享模型并发场景**。GQA 在使用 FlashAttention 的 GPU 路径仍需额外测试；CPU fallback 通过也不代表 FlashAttention 等价。

## 4. Codespaces 下一次执行

```bash
git pull --ff-only origin mini-mythos-research

python -m unittest discover \
  -s research/mini_mythos/tests \
  -p 'test_*.py' -v

python research/mini_mythos/scripts/r0_cache_compare.py \
  --repo . --attentions gqa mla --strict
```

输出文件：
`research/mini_mythos/results/r0/cache_mask_comparison.json`。

**预期观察**（仍需真实执行验证）：

- `upstream=FAIL`：原版仍触发尺寸异常；
- `research_mask=PASS`：校正掩码后与完整模型 logits 相符；
- 如修正后仍失败，保留 FAIL 原始证据，进一步检查 RoPE、分块因果性、ACT 权重与循环深度 Cache 一致性，不做无根据归因。

## 5. R0 Gate A 状态

**已完成**：静态源码审计、微模型参数恢复实验、原版 KV Cache 多 token 故障复现、隔离修复及可运行验证代码。

**尚未完成**：隔离修复动态复核、真实训练脚本恢复一致性、Heldout PPL、Tokenizer revision 固定、3B FSDP/BF16 检验，以及 GPU 版本多 token Cache 等价。不能宣布 R0 完整通过，也没有任何真正 Claude Mythos 架构一致性证据。

下一阶段 R1 的硬性要求仍是：真正的文本训练、可加载权重、稳定的 Heldout NLL/PPL、真实生成样例与训练数据来源可复现。


## 6. R0 Gate A 第二轮：隔离掩码修复已经通过（2026-10-16）

用户在 Codespaces 执行了：

    python research/mini_mythos/scripts/r0_cache_compare.py --repo . --attentions gqa mla --strict

收到的终端输出：

    gqa: upstream=FAIL research_mask=PASS research_max_abs=2.9802322387695312e-08
    mla: upstream=FAIL research_mask=PASS research_max_abs=2.9802322387695312e-08
    Saved: /workspaces/OpenMythos/research/mini_mythos/results/r0/cache_mask_comparison.json

配套单元测试此前已在 Codespaces 执行，**67/67 PASS**（3.245 秒）。原版在“6-token 前缀 + 2-token chunk”的模型场景触发掩码维度不匹配；独立研究修复后 GQA/MLA 的最大绝对 logits 偏差均为 2.9802322387695312e-08，远小于预设 5e-4 容差。

**结论：R0 多 token cached-chunk causal-mask 缺陷的定位及 CPU 微模型隔离修复验证完成。** 原版实现仍存在相同缺陷，且未直接修改 open_mythos/main.py。

**尚存边界：** 单一初始化种子、单一长度切分、随机 tiny model、CPU；GPU FlashAttention 路径、非等长分块、实际长上下文以及生产服务安全性尚未验证；只校正 attention mask，不代表实现了完整的目标 Mythos。原始 JSON 仍留在用户 Codespaces，本报告以用户终端日志为依据。
