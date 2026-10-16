# R2 Gate L — 实际两 OS Worker、8 本地 Shard 的静默文档漏读反例：实测

**2026-10-16；用户 GitHub Codespaces 终端日志。** 使用 Gate I 已冻结的 FineWeb-Edu 32 条真实文本快照做来源验证，传给 DataLoader Worker 的只有内部 28 条开发文档的身份 SHA256；没有上传文本、执行训练、访问在线 HF 或修改 PR27。

## 逐项证据

| 指标 | Codespaces 实际输出 |
|---|---|
| 全量单元测试 | **197/197 PASS（48.077 秒）** |
| 源快照 | 已冻结真实 FineWeb-Edu 本地 snapshot，Worker 只接收来源 ID Hash |
| HF 本地 Arrow Shards | **8** |
| Worker 数 | 每个比较组 **2 个真实 OS Worker**，均正常输出 |
| 对照 A Worker PID | `{0:115426,1:115427}` |
| 负控 B Worker PID | `{0:115503,1:115504}` |
| 对照 A 规则 | `native_once`：只使用 HF PyTorch 自动 Sharding |
| A 文档覆盖 | **28/28**，`Native covered once: True` |
| 负控 B 规则 | `explicit_twice`：先显式按 Worker .shard，再由 HF 自动按 Worker Sharding |
| B 文档覆盖 | **14/28**，两位 Worker 都活着，但静默遗漏 **14 条（50%）** |
| 未被读取的内部 Train 序号 | **`[4,5,6,7,12,13,14,15,16,17,18,22,23,24]`** |
| PR27 代码变化 | **False** |
| 真实远程数据 / 模型训练 / GPU | **均未执行** |

用户本地证据在 Git 忽略目录：`research/mini_mythos/results/r2/pr27_gate_l_double_shard_coverage.json`，未由本次会话下载。失效案例既验证了**真实两个 Worker 都存活**，也验证了只检查活跃 Worker PIDs 无法发现缺失数据。

## 判定

**R2 Gate L：PASS，确认在 8 个本地 HF Arrow Shards 上，PR27 形状的显式 `.shard()` + HF 自动 Worker Sharding 会造成静默数据来源漏读。**

实验 B 的 **14/28（50%）只属于本地八分片、28 文档的固定反例**，不能升级成实际 FineWeb-Edu 远程 Parquet 文件、文档或训练 Token 必定有 50% 遗漏。真实生产环境还需核对具体 Dataset revision、配置下的实际 Shard 数量/文件顺序、`datasets` 版本与 Loader 实际执行机制。

## 后续 Gate M

限定只读取**固定 HF Dataset 版本的 `sample/10BT` Parquet 文件清单元数据**，禁止下载 Parquet 内容。记录确切文件路径、文件字节数、文件清单 Hash；按当前已测试的 HF **手动 contiguous Shard、自动 noncontiguous Worker Shard** 语义，在源文件 ID 层比较单分片与双分片的覆盖；不把源文件级投影说成远程真实 Token 漏读率。下一步才对真正 HF Streaming DataLoader 做可控范围的实验。
