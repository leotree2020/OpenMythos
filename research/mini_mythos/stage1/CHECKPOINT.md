# Stage 1 checkpoint(2026-11-09,修订 1 补跑后)

状态:**修订 1 补跑完成,验收全部 PASS**,等待负责人宣布 CLOSED。方案见 `README.md`(含“修订 1”)。第一次运行(`f3278265`)的结果保留在 `results/`,本次结果在 `results/r1/`。**以 `results/r1/` 为阶段 1 的正式数据和基线。**

## 做了什么

- Codespace(2 核 CPU,未用 GPU),代码 `d22dd165`。按 README 末尾的补跑步骤执行。
- 测试:`test_stage1` 9 个全部通过。
- 数据构建两次:02:24:08–02:26:48 和 02:26:56–02:28:59。
- 原生基线:02:29:35–约 03:28,共 3490 s,2400 次前向。
- 验收脚本 `verify_stage1.py` 在 `data_r1` 上重新核对,结果在 `results/r1/acceptance_check.json`。
- CPU 合计约 1.1 h(上限 3 h)。

## 结果

**确定性**:两次构建的 `manifest.json` 相同;5 个输出文件(训练 token、文档长度、`eval_sets.jsonl`、`examined.jsonl`、`contamination.json`)逐字节相同。`data_lock.json` 只有 `revision` 字段不同:第二次用 `--lock`,把 `"main"` 记成了解析后的 commit;各来源的 `commit`、文件 sha256 和大小全部一致。第二次的 lock 保留在运行机器上(`data_r1_check_lock.json`)。

**只有 books 变化**:`compare_sets.py` 的输出是 books CHANGED,c4/fineweb/wikitext identical,退出码 0。基线也印证了这一点:这三个领域 900 个窗口的逐窗口 NLL 与第一次完全相同,两个副本的最大差都是 0。

**训练语料不变**:`train_tokens.u16` 和 `train_doc_lengths.i32` 与第一次逐字节相同。

**去污染**:评测窗口与训练语料的 13-gram 重叠为 0;开发集与测试集共享的 13-gram 为 0;没有重复的 sha256 或 id;每个领域开发集 100、测试集 200,无缺口。

**书籍候选**:共检查 312 个(第一次是 584)。其中 4 个(1.3%)与训练语料有 13-gram 重叠,已剔除;因与开发集重叠剔除 8 个(第一次是 283)。抽查解码的窗口都是正文(经文、小说对话、散文),不再是前言。

**原生基线**(深度 8,无 BOS,t[65..255],单位 nats/token;其他三个领域的数字与第一次相同,见 `results/r1/baseline.md`):

| 书籍 | 开发集 NLL [95% CI] | 测试集 NLL [95% CI] | 开发/测试差 | 副本噪声 SD | 均值的 h0 噪声 SE |
|---|---|---|---:|---:|---:|
| 修订前 | 3.1375 [2.967, 3.308] | 3.7103 [3.627, 3.789] | 0.573 | 0.025–0.026 | 0.0013–0.0018 |
| **修订 1** | 3.7655 [3.670, 3.864] | 3.6994 [3.638, 3.762] | **0.066** | **0.0021–0.0025** | 0.00012–0.00015 |

其他领域作对照:开发/测试差为 0.028(c4)、0.119(fineweb)、0.035(wikitext);副本噪声 SD 为 0.0006–0.0007。

- 书籍开发/测试差 0.066,落在其他领域的范围内,且小于两边 CI 的半宽(约 0.06–0.10)。
- 书籍副本噪声 SD 仍约是其他领域的 3–4 倍(修订前约 35 倍)。逐窗口 |副本差| 的中位数:书籍 0.0007–0.0008,其他领域 0.0005–0.0006,差距在 1.5 倍以内,说明 SD 偏大主要来自少数窗口。对领域均值的影响约 1e-4,仍远小于窗口之间的差异。修订 1 对此只要求报告,不设门槛。

## 证据

- 仓库 `results/r1/`:`data_lock.json`、`manifest.json`、`contamination.json`、`eval_sets.jsonl`(sha256 `8816fe5a…`)、`baseline.json/.md`、`baseline_config.json`(权重/配置/分词器无不匹配,state_check 63/63 相同)、`per_window.csv`、`acceptance_check.json`。
- 测试集使用已记入 `TEST_LOG.md`。
- 运行机器 `/workspaces/mythos-evidence/stage1/`:`data_r1/`(含训练 token)、`baseline_r1/rows.jsonl`(sha256 `6bd61b6a…`)、`build_r1_1.log`、`build_r1_2.log`、`baseline_r1.log`、`data_r1_check_lock.json`。第一次运行的 `data/`、`baseline/` 未改动。

## 未解决

1. 书籍副本噪声 SD 仍约是其他领域的 3–4 倍(见上),只报告。
2. (沿用)GitHub Actions 的 stage 1 workflow 未触发,要触发需要 workflow 在默认分支上。不影响本次运行。

## 下一步

负责人宣布阶段 1 CLOSED;然后准备阶段 2 GPU 试点方案,需要批准 GPU 预算。阶段 2 使用 `results/r1/eval_sets.jsonl`。
