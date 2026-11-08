# Stage 1:建数据与污染检查(方案已批准,2026-11-08)

规则见根目录 `CLAUDE.md`(宪章 v2.0);基线定义见 `../stage0/STAGE0_REVIEW.md`。本阶段只做数据和原生基线,不训练、不用 GPU。

## 目的

为后续“可训练机制”实验(阶段 2 起,GPU)准备三样东西:

1. **训练语料**:与预训练同分布,足够大,让“同预算无机制微调”对照和机制组在同一份数据上公平比较。
2. **评测集**:分开发集(可反复用来调参)和测试集(只在最终比较时用),覆盖同分布和异领域。
3. **污染报告**:评测集与训练语料、与预训练语料样本的重叠程度。

另外在 CPU 上算出原生基线(8 轮、不加 BOS),并估计随机初始状态带来的噪声下限,用来判断后续实验能检测多小的差异。

## 数据

所有来源固定到 commit,文件 sha256 写入 `data_lock.json`。选择规则是确定性的:文件顺序、长度过滤、去重。

**训练语料**:从 Parcae 作者的 FineWeb-Edu `sample-100BT`(即训练用的那份数据)按固定规则取约 **5000 万 token**,不加 BOS/EOS,存成 uint16 token 文件并记录 sha256。
- 这部分数据 Parcae 很可能训练时见过。这是有意的:适配训练只“复习”,不会因为新内容本身带来收益,机制效果更干净。
- 它同时充当“预训练语料样本”(约占 100BT 的 0.05%),用于污染检查。

**评测集**:每篇文档取开头 256 个 token 作为一个窗口,不加 BOS(与阶段 0 一致)。

| 领域 | 来源 | 开发集 | 测试集 | 性质 |
|---|---|---:|---:|---|
| fineweb | FineWeb-Edu 验证分片(作者留出) | 100(即阶段 0 用过的) | 200(新) | 同分布 |
| c4 | C4 英文 validation | 100(阶段 0) | 200(新) | 网页,近分布 |
| wikitext | 开发集用阶段 0 的 100 篇;测试集从 WikiText-103 train 取新文章 | 100 | 200 | 百科 |
| books | 开发集:PG-19 validation+test(共约 150 本);测试集:PG-19 train | 100 | 200 | 远领域 |

WikiText-2 的 test+validation 合计只有约 120 篇够长的文章,所以测试集改从 WikiText-103 train 里取;PG-19 的 test 只有 100 本书,所以书籍测试集从 PG-19 train 里取。这两个 train 我们都从不用于训练。

**测试集使用规则**:只有冻结后的最终候选才能在测试集上评测;每次评测都记录在 `TEST_LOG.md`(时间、对象、commit)。调参只用开发集。

## 去重与污染检查

用 13-gram(连续 13 个 token)做重叠检测,这是常用的污染判据。

1. **训练语料 ↔ 评测集(必须干净)**:任何与训练语料有 13-gram 重叠的评测窗口,剔除后按规则补足;文档级 sha256 也不能重复。开发集与测试集之间同样互不重叠。
2. **评测集 ↔ 预训练样本(只报告)**:训练语料本身就是预训练语料的样本,所以第 1 步的命中统计同时用作预训练污染的估计。报告每个领域有命中的窗口比例和命中 token 比例。这只是下限:样本只占 0.05%,没命中不代表没见过。
3. 实现:token 序列算 64 位滚动哈希,排序后用二分查找。5000 万个 13-gram 约 400 MB 内存,Codespace(8 GB)可以承受。

## 原生基线与噪声下限(CPU)

- 开发集和测试集全部窗口(4 个领域 × 300 = 1200 个),8 轮、不加 BOS、2 个初始状态副本,用阶段 0 的代码和统计方法。
- 报告每个领域的 NLL、95% CI。
- **噪声下限**:同一窗口两个副本之间的 NLL 差的标准差。后续“机制减对照”的差异如果小于这个量级,无法和随机初始状态的波动区分。
- 预计约 2400 次前向,约 1 小时。

## 验收

1. `data_lock.json` 完整;同一命令重跑两次,所有输出文件 sha256 相同(确定性)。
2. 训练语料与开发集、测试集之间 13-gram 重叠为 0;开发集与测试集互不重叠;每个领域的开发集和测试集数量达标。如果剔除后补不足,如实报告缺口,不放宽判据。
3. 产出污染报告:各领域的命中窗口比例、命中 token 比例。
4. 产出原生基线表和噪声下限。

## 资源与停止条件

- CPU 总耗时上限 3 小时;磁盘剩余低于 2 GB 时停止。原始下载文件处理完即删除,只保留 token 文件和锁定文件。
- 路径或导入问题 30 分钟内修不好就停下报告。
- 不做:训练、GPU、改上游、PR #24。

## 交付

`data_lock.json`、各集合的文档 id 和 sha256 清单、污染报告、基线汇总、一页 `CHECKPOINT.md`。token 文件留在运行机器上,可以按锁定文件在任何机器上重建,GPU 机器就这样拿数据。

## 负责人决定(2026-11-08)

远领域用书籍(PG-19);训练语料 5000 万 token;测试集只给冻结候选用,并记录每一次使用。

## 运行手册(Codespace)

数据构建会单独占用约 4 GB 内存,**不要和评估同时跑**。数据从 Hugging Face 流式读取,只取用到的部分,磁盘占用约 0.3 GB。

```bash
cd /workspaces/OpenMythos && git fetch origin mythos-stage1-data-v1 && git checkout mythos-stage1-data-v1
cd research/mini_mythos/stage1
PY=/workspaces/mythos-base-v01-cpu312/bin/python
DPY=/workspaces/stage0-data-env/bin/python
OUT=/workspaces/mythos-evidence/stage1

# 0) 数据环境补装(分词器版本必须与冻结环境一致)
/workspaces/stage0-data-env/bin/pip install "tokenizers==0.23.2" numpy pyarrow huggingface_hub

# 1) 测试(合成数据 + 随机小模型,约 1 分钟)
STAGE0_UPSTREAM=/workspaces/mythos-parcae-pinned $PY -B -m unittest test_stage1 -v

# 2) 冒烟:小规模确认所有数据源都能解析和读取(几分钟)
$DPY build_data.py --out $OUT/smoke --train-tokens 200000 --n-dev 3 --n-test 3

# 3) 正式构建,跑两次验证确定性(两次 manifest.json 必须完全相同)
$DPY build_data.py --out $OUT/data
$DPY build_data.py --out $OUT/data_check --lock $OUT/data/data_lock.json
diff $OUT/data/manifest.json $OUT/data_check/manifest.json && echo DETERMINISTIC && rm -rf $OUT/data_check

# 4) 原生基线(约 1 小时;中断后同一命令续跑)
nohup $PY -B baseline.py run --sets $OUT/data/eval_sets.jsonl --out $OUT/baseline > $OUT/baseline.log 2>&1 &
$PY baseline.py report --out $OUT/baseline
```

如果书籍源 `deepmind/pg19` 无法解析,脚本会自动尝试 `emozilla/pg19`,实际使用的源写入 `data_lock.json`。两个都失败就停止并报告,不要换成别的数据集。

**交付到 `stage1/results/`**:`data_lock.json`、`contamination.json`、`manifest.json`、`eval_sets.jsonl`(约 2 MB,只含 token id,方便 GPU 机器直接使用)、`baseline.json`、`baseline.md`,以及一页 `CHECKPOINT.md`。训练 token 文件(约 100 MB)不进 Git,GPU 机器按 `data_lock.json` 重建。

## 文件

| 文件 | 作用 |
|---|---|
| `ngrams.py` | 13-gram 哈希、训练语料集合(不跨文档)、成员查询、重叠统计 |
| `build_data.py` | 数据源解析与锁定、流式读取、训练语料、开发/测试集选择与去污染、污染报告、manifest |
| `baseline.py` | 原生基线(8 轮、无 BOS、2 副本),可续跑,带运行锁;报告含噪声下限 |
| `test_stage1.py` | 7 个测试:哈希正确性、跨文档排除、植入污染被剔除、开发/测试互斥、确定性、缺口如实报告、基线端到端 |

## 原需负责人决定的事项(已决定,见上)

1. **远领域选什么**:书籍(PG-19,推荐,风格与网页差别大)还是代码?
2. **训练语料规模**:5000 万 token 是否合适?这决定阶段 2 的 GPU 时长。粗估每次训练在单卡上几分钟到半小时。
3. **测试集规则**:是否接受“只给冻结候选用,并记录每一次使用”?

## 之后(仅预告,不在本阶段)

阶段 2(GPU 试点):在 GPU 上复现原生基线并与 CPU 结果核对;实测训练吞吐,校准预算;跑通“同预算无机制微调”对照。需要负责人批准 GPU 预算。
