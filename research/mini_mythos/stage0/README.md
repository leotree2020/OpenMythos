# Stage 0:修正基线(加 BOS、修采样、重测深度)

一页方案 + 运行手册。背景见 `../AUDIT_CLAUDE_20261108.md` 和 `../PROJECT_BRIEF.md`。

## 方案

**目的**:给原生 Parcae-140M 建立可信的基线。之前的评测都漏了 BOS(训练和官方评测都有),生成质量判据不合理,采样守卫有 bug。本阶段不训练、不加机制。

**数据**(`prepare_data.py`,固定版本,首次下载时把 commit 与文件 sha256 写入 `data_lock.json`):
- `fineweb`:Parcae 作者的 FineWeb-Edu 验证分片(`SandyResearch/fineweb-edu-shuffled`,`val/` 下第一个文件),最多 100 篇。与预训练同分布。
- `wikitext`:WikiText-2 raw 测试集,按文章正文,最多 100 篇(实际约 60 篇)。异领域,并可与旧的 32 窗口实验对照。
- 每篇只取文档开头 257 个 token;按文件顺序、长度过滤(≥2000 字符)、去重,确定性选择。

**条件**:每个窗口 × {有 BOS, 无 BOS} × 深度 {8, 16, 32} × 2 个初始状态副本。同一窗口内所有条件共用同一随机种子(配对)。两种 BOS 条件都输入 256 个 token,并对同一批 255 个文本 token 打分。

**指标**:
- 主指标:文本 token t[65..255] 的平均 NLL(每个 token 前至少有 64 个上下文)。
- 早期指标:t[1..64](BOS 影响最大的地方)。
- 统计单位是窗口(先平均副本)。报告均值、中位数、bootstrap 95% CI(10000 次)、正负计数、去掉影响最大窗口后的均值、困惑度变化百分比。
- 耗时:每种条件单次前向的中位秒数。
- 事后最优深度上界:对每个窗口选“NLL 不超过最优 0.01 nats 的最便宜深度”,报告平均成本(相对固定 32 轮)。这一项用了答案,只是上界,不是可部署策略。

**事先定好的判断规则**:
1. BOS:基线一律加 BOS。若 fineweb 在深度 8 的主指标上“有 BOS 减无 BOS”的 95% CI 完全大于 0(加了反而更差),停下排查加载或分词问题。
2. 深度:某领域中,只有当“深度 d 减深度 8”的 CI 完全小于 0 时,才写“更深有帮助”;同时报告幅度和耗时倍数。
3. 自适应深度是否值得继续:只有 fineweb 上的事后最优上界能把成本降到固定 32 轮的 75% 以下,才值得继续研究按文本路由。否则这条线关闭。
4. 生成:只做描述,不设自动 PASS/FAIL。输出给人或 AI 阅读。

**不做**:训练、GPU、改上游、改权重、KV cache。

## 运行手册(在 Codespace 中)

预计耗时(粗估,2 线程):深度评估约 1.5–2.5 小时,生成约 15–30 分钟。中断后用同样命令重跑会自动续跑。

```bash
cd /workspaces/OpenMythos            # 或任何检出本分支的目录
git fetch origin mythos-stage0-baseline-v1 && git checkout mythos-stage0-baseline-v1
cd research/mini_mythos/stage0
PY=/workspaces/mythos-base-v01-cpu312/bin/python   # 冻结环境:torch 2.11.0+cpu、tokenizers、numpy
OUT=/workspaces/mythos-evidence/stage0

# 0) 单元测试(随机小模型,不是真实权重;约 1 分钟)
STAGE0_UPSTREAM=/workspaces/mythos-parcae-pinned $PY -B -m unittest test_stage0 -v

# 1) 数据(需要 pyarrow;冻结环境里没有,就用一个单独的小环境)
python3 -m venv /workspaces/stage0-data-env
/workspaces/stage0-data-env/bin/pip install pyarrow huggingface_hub
/workspaces/stage0-data-env/bin/python prepare_data.py --out $OUT/data

# 2) 冒烟(每个领域 2 篇,几分钟),确认能跑通
$PY -B eval_depth.py --texts $OUT/data/texts.jsonl --out $OUT/smoke --limit 2
$PY report.py --run $OUT/smoke

# 3) 正式深度评估(可后台运行;中断后同命令续跑)
nohup $PY -B eval_depth.py --texts $OUT/data/texts.jsonl --out $OUT/depth > $OUT/depth.log 2>&1 &
tail -f $OUT/depth.log
$PY report.py --run $OUT/depth

# 4) 生成
$PY -B generate.py --out $OUT/gen
```

## 提交什么

把这些小文件复制到 `results/` 后提交:`data/data_lock.json`、`depth/config.json`、`depth/summary.json`、`depth/summary.md`、`gen/generations.md`、`gen/generation_summary.json`。

不提交:`rows.jsonl`(逐 token 数据,约 10 MB,留在 Codespace)、原始 parquet、权重。

## 文件

| 文件 | 作用 |
|---|---|
| `common.py` | 运行时设置、固定输入哈希检查、官方加载器加载并逐张量核对、BOS 窗口构造、逐 token NLL |
| `prepare_data.py` | 下载并锁定两个数据源,选择文档开头文本 |
| `eval_depth.py` | 深度 × BOS 评估,逐行写出,可续跑,含确定性自检 |
| `report.py` | 汇总统计、对比、事后最优深度上界、耗时 |
| `generate.py` | 加 BOS 的贪心与采样生成(FP64 概率,修复旧守卫问题),描述性重复指标 |
| `test_stage0.py` | 9 个测试:窗口对齐、数据解析、采样、端到端(随机小模型) |
