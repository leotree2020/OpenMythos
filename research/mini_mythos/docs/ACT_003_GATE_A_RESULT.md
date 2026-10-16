# ACT-003 Gate A 验证记录

**项目：** Mini-Mythos / leotree2020/OpenMythos  
**分支：** mini-mythos-research  
**阶段：** Gate A — Evidence Archive & Controlled Replay  
**状态：** PASS（根据用户提供的 Codespaces 控制台结果）  
**来源：** 用户实际运行以下代码并提供输出；此次报告提交并未将原始 ZIP / Replay JSON 上传到 GitHub，也未独立读取其字节内容。

## 1. 代码测试

Codespaces 控制台：

- 运行 \`python -m unittest discover -s research/mini_mythos/tests -p "test_*.py" -v\`
- **Ran 42 tests in 1.506s**
- **OK**

包括 ACT-001 / ACT-002 的研究逻辑测试和 ACT-003 的归档、哈希篡改、路径检查、来源漂移、结果比较等测试。

## 2. Evidence Archive

打包命令：

    python research/mini_mythos/scripts/evidence_archive.py pack --repo .

校验命令：

    python research/mini_mythos/scripts/evidence_archive.py verify \
      research/mini_mythos/archives/act001_act002_evidence.zip

用户控制台显示：

- **Archived 14 JSON files**
- **completeness=complete**
- **PASS: verified 14 JSON files**
- **Completeness: complete**
- **SHA-256:** \`787ace0458d1a3e049291648d9a7111a0d12e5d1cc113882fbebf8ccbcbc417d\`
- **Location:** \`research/mini_mythos/archives/act001_act002_evidence.zip\`（原 Codespaces）

哈希只表明该次打包输出的字节指纹。其余人员只有取得**实际 ZIP 文件**并计算一致哈希，才能验证拿到的文件与此记录一致。manifest 中的归档时 Git HEAD 不应与各原始运行的 commit 混为一谈。

## 3. ACT-002 受控复跑

命令：

    python research/mini_mythos/scripts/evidence_replay.py \
      --repo . --cases gqa22 mla22 mla44

终端输出：

| 案例 | 归档 ΔLoss | 复跑 ΔLoss | 结果 |
|---|---:|---:|---|
| GQA / Seed 22 | +0.021204 | +0.021204 | PASS |
| MLA / Seed 22 | +0.000000 | +0.000000 | PASS |
| MLA / Seed 44 | +0.013720 | +0.013720 | PASS |

Replay JSON 在原 Codespaces 的：

    research/mini_mythos/archives/act003_replay_summary.json

PASS 依据工具自身的比对方法：实验身份、训练长度、首次事件记录以及四格 Heldout 标量数据在默认绝对/相对容差 1e-4 范围内一致。此摘要不能代替完整 train_trace 的逐值审计。

## 4. Gate A 结论

- 证据归档在用户 Codespaces 中生成并通过校验，且标记为 complete。
- 三组机制阳性/阴性对照在相同实现和环境下重新执行，全部 PASS。
- 至此，**Gate A 的本地完整性和受控重执行目标达到**。
- 尚未取得经过独立审查的 ZIP 副本、数字签名、独立环境运行记录或真实预训练模型数据。不能称为第三方独立复现或发表级质量证明。
- 原始 JSON 和 replay 文件应在明确审查内容后存入适当的长期归档位置；不要把包含内部或敏感数据的结果提交到公共仓库。

## 5. 下一阶段（ACT-003 Gate B）

1. 使用扩大后的**固定 Heldout 集**对比 Original ACT 和 Forced Final Remainder ACT。
2. 增加随机种子，报告分布和区间而不是只报告均值。
3. 在**固定初始化/冻结参数**和**受控训练**两种条件下，扫描 ACT 阈值与最大循环预算。
4. 记录实际循环次数、tokens、耗时（并在可能时估计 FLOPs），避免仅按指定深度比较效率。
5. 仅在明确的计算预算和模型输入分布匹配后，讨论性能收益。

参见 [ACT-003 归档与受控复跑说明](ACT_003_ARCHIVE_REPLAY.md) 和 [ACT-001 / ACT-002 报告](ACT_001_002_RESEARCH_REPORT.md)。
