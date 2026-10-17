# R2 Gate Q — PR27 双重分片修复候选：Codespaces 实测结果

**2026-10-17，用户 Codespaces 回传完整终端测试日志。状态：研究候选本地验证已通过；原版 PR #27 不受修改。**

## 实测事实

| 项目 | 结果 |
|---|---|
| Git 分支更新 | `mini-mythos-research` fast-forward `0ed065b..ecfc0cc` |
| Gate Q 单项回归 | **8/8 PASS，0.080 秒** |
| 研究项目全量单元测试 | **241/241 PASS，58.202 秒** |
| 双 Worker 使用的来源 | **本地合成** 14 个 HF Arrow Shards，文本 `ID:0` 至 `ID:13` |
| 本地来源身份覆盖 | **14/14，每 Worker 7**，无重复 |
| 双重分片修复方式 | 研究-only loader 不执行显式 `.shard()`，使用 HF native worker split 一次 |
| EOS、跨文档打包与 `(x,y)` | 通过单元测试验证，保留 PR27 逻辑 |
| 来源与 Revision 锁定、skip_docs guard | 单测通过 |
| 远端真实 Parquet 读取 | **未进行** |
| 原版上游 PR27 被修改 | **没有** |
| 真实模型/GPU 训练 | **未进行** |

## 新发现：Python 3.14 `fork()` 风险

本轮在 Linux 两个真实 Worker 单元测试中出现以下**非致命警告**：

```text
/usr/local/python/3.14.2/lib/python3.14/multiprocessing/popen_fork.py:70:
DeprecationWarning: This process ... is multi-threaded, use of fork()
may lead to deadlocks in the child.
```

这条警告不推翻本轮的 8/8 与 241/241 PASS，但指出实验设施存在可避免的多线程 fork 死锁风险。下一候选改为 **`spawn`** 新解释器子进程，同时使用可 pickle 的模块顶层 Worker 测试类与 `worker_init_fn`，在每个子进程安装**本地 14 条合成 HF 数据工厂**，避免 `fork` 继承父进程 monkeypatch。原始候选 loader 行为不能因单测切换启动方式而改变。

## 与 PR #27 关系

固定上游源码 `kyegomez/OpenMythos` PR #27、head commit `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4` 的 `experiments/data.py` 包含 Worker 内手动 `ds.shard(...)`，随后 `for doc in ds` 触发 HF native worker auto-shard。研究 loader 已在本地同语义路径证明：删除重复手动分片可恢复合成身份覆盖率。它尚**不构成**原版远程训练文件、文档、Token 级覆盖测量，更不构成权重层面的 Claude Mythos 复刻证明。

## 下一步

1. 保留本次已验证 241/241 作为不可变基线。
2. 创建**单独**本地可 pickle 的合成 HF 工厂与 `spawn` Worker 测试，禁止网络访问，拒绝非固定来源参数。
3. 再次在 Codespaces 运行专项和全量测试，检查 `spawn` 测试是否 PASS、两个 PID 和各 7 个身份覆盖是否一致、`fork` 警告是否消失。
4. 最小上游代码差异对照仅在研究文件中实现/记录；不要直接改动未合并 PR27 的原版源文件。
