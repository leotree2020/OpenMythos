# R2 Gate A：当前 Codespaces 环境预检实测

**2026-10-16；证据为用户提供的 Codespaces 终端输出。** 当前分支 `mini-mythos-research`，运行时 Git revision `3f19ce5c5f804d79c9d3ecab5a5890a49b505e4c`。

## 单元测试与硬件

| 项目 | 实测结果 |
|---|---|
| 全量单元测试 | **110/110 PASS，3.850s** |
| PyTorch | `2.14.1+cu130`（包含 CUDA 构建，并不代表实际 GPU 可用） |
| `torch.cuda.is_available()` | **False** |
| CUDA device count | **0** |
| 当前容器剩余磁盘 | **13.06 GiB** |
| GPU 训练审批布尔值 | **False**（预检仅盘点，没有授权或 GPU） |

**判定**：当前 Codespaces 环境能运行 CPU 单元测试、微型模型和源码审计；**不能在其中直接启动 GPU 训练**。切勿以 PyTorch 安装版字符串含 `cu130` 就推断已经有 NVIDIA GPU。13.06 GiB 是运行当刻本地可用空间，不是永久配额。

## 原版生产训练链路尚缺的准备度

| 状态 | 标记 | 含义 |
|---|---|---|
| GAP | R2_DATA_CURSOR | Streaming FineWeb-Edu 恢复缺少可验证数据游标 |
| GAP | R2_TOKENIZER_REVISION | Tokenizer 不可变 revision/hash 及 train/eval 一致性未固定 |
| GAP | R2_CHECKPOINT_TRUST | 正式脚本仍使用反序列化不可信 Pickle 的方式 |
| GAP | R2_HELDOUT_EVAL | 正式 3B 脚本没有单独来源的已验证 Heldout NLL/PPL |
| REVIEW | R2_ACT_FP16_BF16 | ACT、混合精度、Attention dtype 仍需微型/真实 GPU 验证 |
| REVIEW | R2_MOE_BALANCING | Router Bias 与专家负载均衡训练策略仍需实际追踪 |
| GAP | R2_CACHE_CHUNK | 上游模型多 Token KV Cache 原版掩码问题仍未在核心文件修复 |

注意：部分 GAP 是静态规则探针的模式匹配结果，**不是所有 GPU 环境下都必然发生的运行时异常**。R1 的 tiny overlay 安全 checkpoint、heldout 和 GPU 无关回归成果不能自动视为修复了上游正式 3B/118M 训练脚本。

## Gate A 结论与下一动作

**Gate A：CPU 研发条件 PASS，GPU 预训练条件 BLOCKED（无设备；且源码存在 P0/P1 训练闭环缺口）。**

下一步优先按 [R2 上游准备审计](R2_UPSTREAM_READINESS.md) 取得 PR #27 固定 Commit 的源码并在 CPU 做差异/版本审计，验证 Tokenizer、RoPE、ACT、Checkpoint 等，保留上游主体不变。不得在本容器运行 `experiments/run_all.sh` 或 `training/3b_fine_web_edu.py`。

原始 JSON 位于用户当前 Codespaces `research/mini_mythos/results/r2/preflight.json`；此报告没有复制完整 JSON，也没有访问本地 GPU。
