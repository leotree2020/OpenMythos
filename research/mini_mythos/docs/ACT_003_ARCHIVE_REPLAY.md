# ACT-003：实验归档与受控复跑

**状态：** 工具和研究步骤已编写；原始 JSON 仍在用户的 Codespaces 中。只有在那里实际执行打包命令，才会产生历史实验的归档文件。

本阶段保持原始上游 open_mythos/main.py 不变。目标是归档完整原始结果、记录代码/环境来源，并通过相同实现重新执行 ACT-002 的正反对照。

## 1. 证据来源和范围

当前 [ACT-001/ACT-002 研究报告](ACT_001_002_RESEARCH_REPORT.md) 的表格来自已提供的 Codespaces 终端输出。原始结果是 research/mini_mythos/results/ 下的 JSON 文件，而不是报告摘要。

默认必须存在以下 10 个文件（相对于 results/）：

| 类别 | 文件 |
|---|---|
| ACT-001 GQA 诊断 | act_gqa.json |
| ACT-001 MLA 诊断 | act_mla.json |
| ACT-002 GQA 阳性对照 | act002_gqa_seed22.json |
| ACT-002 MLA 阴性对照 | act002_mla_seed22.json |
| ACT-002 MLA 阳性对照 | act002_mla_seed44.json |
| 五个 ACT-001 种子 | multiseed/act_ab_seed_11.json、_22.json、_33.json、_44.json、_55.json |

此外，会包含存在于明确白名单里的 smoke、provenance、audit 和其他相关 JSON。**不会扫描未知 JSON、生产日志或任意用户目录，更不会自动上传数据。**

## 2. 从 Codespaces 一键归档

在已有的 mini-mythos-research 分支仓库根目录运行：

    git pull --ff-only origin mini-mythos-research

    python -m unittest discover \
      -s research/mini_mythos/tests \
      -p "test_*.py" -v

    python research/mini_mythos/scripts/evidence_archive.py pack --repo .

生成：

    research/mini_mythos/archives/act001_act002_evidence.zip

期望显示 completeness=complete；如果缺失任意必需结果，默认失败，不会伪装成完整归档。--allow-partial 仅用于有意识地检查不完整结果，不满足正式归档完成条件。

归档中有 manifest.json：记录每份原始 JSON 的 SHA-256、字节大小、路径、原始运行 commit，以及归档时的 Git HEAD、关键代码文件 SHA-256、Python/PyTorch/Transformers 版本。**归档时的 Git HEAD 并不等于每份历史数据的运行 commit**；不能把两者混同。

## 3. 校验完整性

    python research/mini_mythos/scripts/evidence_archive.py verify \
      research/mini_mythos/archives/act001_act002_evidence.zip

    sha256sum research/mini_mythos/archives/act001_act002_evidence.zip

校验 ZIP 文件清单、重复路径、异常路径、JSON 身份、字节数和 SHA-256；不自动解压到磁盘。SHA-256 能检测文件修改或损坏，但不是数字签名，也不能单独证明数据发布方身份。

证据包和复跑摘要默认位于 Git 忽略的 archives 目录。不要把包含公司内部数据的文件带入研究代码；对于本项目的合成数据 ZIP，分享或上传前也必须人工检查。

## 4. ACT-002 三组受控复跑

    python research/mini_mythos/scripts/evidence_replay.py \
      --repo . \
      --archive research/mini_mythos/archives/act001_act002_evidence.zip \
      --cases gqa22 mla22 mla44 \
      --out research/mini_mythos/archives/act003_replay_summary.json

该程序仅从归档中读取三组已知 ACT-002 的实验参数，并调用本地 act_counterfactual.py 在 CPU 上重新执行。不会执行 JSON 中任意命令、不会联网、也不会上传报告。

默认拒绝归档时的源码 SHA-256 或 Python/PyTorch 版本与当前环境不符。允许有意识地用 --allow-source-drift 或 --allow-env-drift 放宽，但不建议用于正式复现论证。

复核首次 ACT 质量缺口、同权重直接效应、参数分离、交互项、训练长度，以及四格 Heldout Loss 和 Total/Direct/History/Interaction 的差值。默认数值容差为绝对 0.0001 / 相对 0.0001，必要时可修改。程序会显示每组 PASS、DIFF 或 ERROR，并保存 replay_summary.json；有任何一组不是 PASS 就返回非零退出码。

**严格的术语界限：** 这是同一套代码的重复执行（re-execution），并不等于独立团队、独立实现和真实数据上的科学复现。

## 5. Gate A 验收

- 十个必需实验结果都存在，归档 completeness=complete。
- ZIP manifest 和 SHA-256 验证 PASS。
- 原始各实验 commit、归档时 Git 提交和核心源码哈希都被保留并明确区分。
- GQA22、MLA22、MLA44 三组受控复跑全部 PASS，或如实记录 DIFF/ERROR。
- 归档内容已人工检查，确认无未授权数据。

之后才进入 ACT-003 Gate B：冻结环境、扩大 Heldout 批次、更多种子、停止阈值与循环预算扫描，以及计算量匹配的真实数据消融研究。
