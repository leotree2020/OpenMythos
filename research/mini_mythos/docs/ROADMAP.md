# Mini-Mythos 上游继承实施顺序

## Gate 0 — 可追溯环境
- Clone 上游到 `third_party/OpenMythos`，固定 commit SHA；记录 Torch/CUDA、依赖列表和系统信息。
- 本项目的 `scripts/static_audit.py` 必须能运行，人工复核输出。

## Gate 1 — 最小正确性（当前交付）
- 在 CPU 上执行 `scripts/smoke.py`，验证 forward/backward、因果屏蔽、KV Cache、ACT 质量。
- 然后分别在 GQA、MLA 和 BF16 GPU 上运行；任何失败先定位原因，避免大规模训练。
- 执行 `scripts/pilot_train.py`；只有 loss finite 且训练评估可重复，才能进入后续。

## Gate 2 — 借力社区成果
- 将 PR #27 作为基准分支，用其 `experiments/run_all.sh` 对比独立数据与循环次数。
- 先处理 PR #26 的精度问题，然后评估 PR #15 的 FP16/validation 建议；**不自动合并**。
- GPU 长跑前验证训练评估分片不交叉、数据版本固定和 checkpoints 可重启。

## Gate 3 — 可比较架构实验
- 基线：fixed 1 / fixed 8 / randomized loops。
- 消融：移除 loop-index embedding / 移除 per-loop LoRA / 强制最终 ACT remainder。
- 指标：PPL 按 loop 的曲线、每 token FLOPs、吞吐、峰值显存、梯度范数、数值异常和任务准确率。
- 同时提供参数匹配和计算匹配对照；至少三个 seeds，统计标准差。

## Gate 4 — 安全专用训练
- 合法语料：RFC 与许可可用的安全技术知识；先做脱敏合成日志。
- 可验证网络诊断：HTTP 407、TCP RST、TLS 协商异常、Firewall ACL 冲突等。
- 训练数据、验证集、最终测试集按案例来源与时间隔离；评测使用未见过的案例。
