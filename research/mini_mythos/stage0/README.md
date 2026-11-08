# Stage 0:修正基线(加 BOS、修采样守卫、重测 8/16/32 轮)

> **结果与更正见 `STAGE0_REVIEW.md`:** Parcae 预训练没有加 BOS,正确输入是不加 BOS。本方案中“基线一律加 BOS”的前提是错的;数据中两种条件都已测量,结论按无 BOS 重新陈述。`generate.py` 已改为默认不加 BOS。

一页方案 + 运行手册。规则见仓库根目录 `CLAUDE.md`(宪章 v2.0);背景见 `../PROJECT_BRIEF.md` 和 `../AUDIT_CLAUDE_20261108.md`。

## 方案(已冻结)

**目标**:在加 BOS 的条件下,建立 Parcae-140M 原生 8/16/32 轮的可信基线曲线。不训练,不加机制。

**固定版本**:模型 `parcae-140m@236739ce`,分词器 `parcae-tokenizer@6247b5d0`,上游 Parcae `@69284c13`。脚本会核对权重、配置、分词器的 sha256,并逐张量核对官方加载器加载的结果。

**数据**(`prepare_data.py`;首次下载把 commit 和文件 sha256 写入 `data_lock.json`):

| 领域 | 来源 | 篇数 | 角色 |
|---|---|---:|---|
| `wikitext` | WikiText-2 raw test + validation,按文章正文 | 100 | 验收领域 1 |
| `c4` | C4 英文 validation 分片 0 | 100 | 验收领域 2(网页文本,异领域) |
| `fineweb` | Parcae 作者的 FineWeb-Edu 验证分片 | 100 | 同分布参照,不参与验收 |
| `wikitext_old32` | 旧深度实验的 32 个窗口(已分词) | 32 | 复测 BOS 前后差异 |

规则:每篇只取文档开头 257 个 token;按文件顺序、长度不少于 2000 字符、按 sha256 去重,确定性选择。不用 AG News,因为它的条目太短,凑不出 257 个 token。

**条件**:每个窗口 × {有 BOS, 无 BOS} × 深度 {8, 16, 32} × 2 个初始状态副本。同一窗口的所有条件共用同一种子(配对)。两种 BOS 条件都输入 256 个 token,只对同样的 255 个文本 token 打分;BOS 位置不计入 loss。

**指标**:
- 主指标:t[65..255] 的平均 NLL。
- 早期指标:t[1..64]。
- 以窗口为单位(先平均副本),报告均值、平均 PPL、bootstrap 95% CI(10000 次,种子 20261108)、中位数、正负计数、去掉影响最大窗口后的均值。
- tokens/s:每个深度单次 256 token 前向的中位耗时。
- 事后最优深度上界:用了答案,只是上界,不是可部署策略。

**采样守卫**:概率和偏离 1 超过 1e-4 才报错。FP32 正常舍入误差约 1e-5,不会误触发。测试包含负例:和为 1.01、0.5+0.6、负概率、NaN 都必须触发。

**验收**:
1. BOS 修正生效且可被检测:脚本启动时自检,去掉 BOS 后结果必须不同,否则停止。`wikitext_old32` 上报告加 BOS 前后的 NLL 差。
2. `wikitext` 和 `c4` 都给出 8/16/32 轮曲线和置信区间。
3. 结论如实写成三选一(`report.py` 自动生成;“显著”指 95% CI 完全小于 0):16 或 32 轮在两个领域都显著优于 8 轮 / 只在一个领域优于 / 不显著。不预设哪种算通过。

**停止条件**:
- 前向累计耗时超过 6 小时,`eval_depth.py` 自动停止(退出码 3)。报告进度和 tokens/s,不缩小样本硬跑。之后用同一命令可以续跑。
- 路径或导入问题 30 分钟内修不好,停下报告。

**不做**:训练、GPU、改上游、PR #24。

## 运行手册(在 Codespace 中)

预计耗时(粗估):332 个窗口,约 4000 次前向,约 3 小时;生成约 15–30 分钟。想省约 1 小时,可以在第 1 步加 `--domains wikitext,c4`,不跑 fineweb。

```bash
cd /workspaces/OpenMythos
git fetch origin mythos-stage0-baseline-v1 && git checkout mythos-stage0-baseline-v1
cd research/mini_mythos/stage0
PY=/workspaces/mythos-base-v01-cpu312/bin/python     # 冻结环境:torch 2.11.0+cpu、tokenizers、numpy
OUT=/workspaces/mythos-evidence/stage0
OLD32=/workspaces/mythos-evidence/base_v01/boundary_repair/data-20261101T134401Z/build_first/inputs.json

# 0) 单元测试(随机小模型,不是真实权重;约 1 分钟)
STAGE0_UPSTREAM=/workspaces/mythos-parcae-pinned $PY -B -m unittest test_stage0 -v

# 1) 数据(需要 pyarrow 和 huggingface_hub;冻结环境里没有,用单独的小环境)
python3 -m venv /workspaces/stage0-data-env
/workspaces/stage0-data-env/bin/pip install pyarrow huggingface_hub
/workspaces/stage0-data-env/bin/python prepare_data.py --out $OUT/data

# 2) 冒烟(每个领域 2 篇,几分钟)
$PY -B eval_depth.py --texts $OUT/data/texts.jsonl --token-windows $OLD32 --out $OUT/smoke --limit 2
$PY report.py --run $OUT/smoke

# 3) 正式评估(后台;中断后同一命令续跑)
nohup $PY -B eval_depth.py --texts $OUT/data/texts.jsonl --token-windows $OLD32 --out $OUT/depth > $OUT/depth.log 2>&1 &
tail -f $OUT/depth.log
$PY report.py --run $OUT/depth

# 4) 生成
$PY -B generate.py --out $OUT/gen
```

## 交付

把以下文件复制到本目录的 `results/` 并提交:
- `data/data_lock.json`
- `depth/config.json`、`depth/summary.json`、`depth/summary.md`、`depth/per_window.csv`
- `gen/generations.md`、`gen/generation_summary.json`
- 一页 `CHECKPOINT.md`:做了什么、三选一结论、BOS 前后差异、tokens/s、commit SHA、未解决问题、下一步

不提交:`rows.jsonl`(逐 token 数据,留在 Codespace)、原始数据文件、权重。

## 文件

| 文件 | 作用 |
|---|---|
| `common.py` | 运行时设置、输入哈希检查、官方加载器加载并逐张量核对、BOS 窗口构造、逐 token NLL |
| `prepare_data.py` | 下载并锁定数据源,选择文档开头文本 |
| `eval_depth.py` | 深度 × BOS 评估;确定性自检与 BOS 负例自检;可续跑;6 小时上限 |
| `report.py` | 汇总、对比、三选一结论、tokens/s、每窗口 CSV、事后最优深度上界 |
| `generate.py` | 加 BOS 的贪心与采样生成;FP64 概率;1e-4 质量守卫;描述性重复指标 |
| `test_stage0.py` | 12 个测试:窗口对齐、数据解析、采样与守卫负例、三选一逻辑、端到端(随机小模型,含 6 小时上限停止与续跑) |
