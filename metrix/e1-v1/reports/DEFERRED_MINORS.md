# E1-V1 协议撰写:登记不修的项

- 依据:Owner 消息“修改次数上限”(`tasks/E1V1_AUTHORING_OWNER_MESSAGE.md`):每一轮只修 BLOCKER,以及影响数据、指标、门槛、可复现性、iso-acquisition 匹配或损伤测量的 MAJOR;其余 MAJOR 与全部 MINOR 只登记到本文件,不修。
- 本文件写于报告提交;第 2 轮之后没有修改任何交付物。
- 来源记法:`R1-CR m<n>` = `reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/code-reviewer_round1.md` 中第 n 个 MINOR(按出现顺序);`R1-DA M<n>` = 同目录 `data-auditor_round1.md` 的观察 Mn;`R2-…` 同理指第 2 轮(`reviews/tree-f395c476606603e65d336e1ba3ac34a065c40889/`)。
- 路径相对于 `metrix/e1-v1/`。

## 1. 第 1 轮(暂存树 `0e3dc49e`,工作提交 `59761ad9`)

code-reviewer:BLOCK(1 BLOCKER、13 MAJOR、18 MINOR);data-auditor:BLOCK(B1)与观察 M1–M8。已在修复提交中处理:BLOCKER、13 个 MAJOR(每个都被审查标为影响六类之一)、data-auditor 的 B1 与 M2、M3、M4(影响 TEST 生成与 ST10 计数的可复现性)。以下只登记。

| # | 来源 | 位置 | 问题(摘要;原文见来源) | 处理 |
|---|---|---|---|---|
| V1-1 | R1-CR m1 | `reports/authoring/v1_data_check.py:45` | 常量 `D1_PER_DOMAIN` 未使用 | 登记 |
| V1-2 | R1-CR m2 | `reports/authoring/compute_estimate.py` | `test_points` 未使用;`min(doses, 5)`、L 保存 2.0 秒、预检 `20 * 1.0` 未在输出中标为假设;Y 的步时用了 F 的(batch 8) | 登记(ST11 公式在协议第 12 节写明了各计数;Y 按 t_F 估算已在公式中注明) |
| V1-3 | R1-CR m3 | `reports/authoring/v1_data_check.txt` | D2 的 L6、L8 只打印 ok,不打印计数;没有 ARC DEV 的 L6、L8 行 | 登记(data-auditor 独立算得 MMLU、ARC 均为 0:`audit/stdout/a5_damage.txt`,R1-DA M1) |
| V1-4 | R1-CR m4 | `reports/authoring/v1_data_check_repeat.txt` | 第二次运行的完整 stdout 没有入库 | 登记 |
| V1-5 | R1-CR m5 | 协议第 7.1、15 节 | ARC 的“6 题”“863 题”是外推 | **已修正**(与 data-auditor 的 B1 是同一处,B1 为 BLOCK 项,随修复提交 `266b64b7` 修正);不计入“登记未修” |
| V1-6 | R1-CR m6 | 协议第 12 节 | 括号 checkpoint 上限写为 9 × 10,应为 9 × 6 | 登记 |
| V1-7 | R1-CR m7 | 协议第 9.1 节 | “只报告”清单比 Pilot 第 8 节少了 DEV 上的 EM 与各 arm 的 dNLL,没有写明为改动 | 登记(DEV 上不做 EM,第 5 节;各 arm 的 dNLL 在剂量曲线中报告) |
| V1-8 | R1-CR m8 | `SPLIT_MANIFEST.json`、`DATA_MANIFEST.json` | 从 Pilot manifest 复制的出处注记(如 `added: round 2`)未标明属于 Pilot;L6 count 只提 general_test | count 已随 R1-DA M3 修改;出处注记登记 |
| V1-9 | R1-CR m9 | 协议文件头 | “执行只需本文件、四个 JSON 与外部来源”与正文依赖 Pilot 实现代码、Pilot 实验记录、`compute_estimate.py` 不符 | 登记(ST11 公式已写入正文;解释的原文仍在 Pilot 实验记录中) |
| V1-10 | R1-CR m10 | 协议第 7.3 节 | Task Order 说 D1 以文档为单位,协议写“窗口”,没写一篇文档只取一个窗口 | 登记(Stage 1 README:每篇文档取开头 256 token 作为一个窗口) |
| V1-11 | R1-CR m11 | `DAMAGE_MANIFEST.json` | D2 重抽次数写死 `k=800`,R2 缩减方案下不对 | 登记(应为 k = 题目数) |
| V1-12 | R1-CR m12 | 协议第 6.4 节第 1 条 | 括注“包括第 1 个剂量点已 ≥ t 的情形”有两种读法 | 登记(正文的定义 j* = 满足 a_{j−1} < t ≤ a_j 的最小 j 是确定的;括注只是举例) |
| V1-13 | R1-CR m13 | 协议第 10 节第 6 步 | ST3 触发时种子 101 在第 11 遍停还是跑满 32 遍,没写 | 登记 |
| V1-14 | R1-CR m14 | `DATA_MANIFEST.json: reported_values` | 缺“3 个种子点估计的最小值、最大值与样本标准差” | 登记(协议第 7.3、8 节已要求报告) |
| V1-15 | R1-CR m15 | 协议第 7.5 节 G-D5 | 在全部剂量点上算 Spearman 相关,同一曲线上的点不独立(只报告) | 登记 |
| V1-16 | R1-CR m16 | 协议第 7.1 节 | fineweb 与锚文本同属一个仓库,引用的 README 里没有仓库名(仓库名在 `research/mini_mythos/stage1/results/r1/data_lock.json`) | 登记(data-auditor 已按 data_lock.json 核实同来源,R1-DA 正面结果) |
| V1-17 | R1-CR m17 | `reports/authoring/build_manifests.py` | V1 的哈希是脚本中的字面量,不是从 v1_data_check 输出解析 | 登记(code-reviewer 与 data-auditor 都已逐个核对一致) |
| V1-18 | R1-CR m18 | `SUBMISSION_NOTE.md` 第 4 节第 1 项 | 曾用 json.loads 整行解析 eval_sets.jsonl 的 test 行;与 Pilot 先例(v1-r6)一致但比 V1 第 0 节的新规则宽,仓库中无证据可复核 | 登记,交 Review Gate |
| V1-19 | R1-DA M1 | `reports/authoring/v1_data_check.txt` | 同 V1-3 | 登记 |
| V1-20 | R1-DA M5 | 协议第 0 节 | TEST 行首匹配原先以代码位置定义 | **已修正**(修复 R1-CR 的 TEST 来源读取规则 MAJOR 时把正则写入正文,`266b64b7`);不计入“登记未修” |
| V1-21 | R1-DA M6 | D2 DEV(MMLU) | 800 题中 2 题有重复的选项文本(数据集本身的性质) | 登记,不修 |
| V1-22 | R1-DA M7 | 流程 | 两个 subagent 定义中的 e1-pilot 路径(audit/、reviews/)在 E1-V1 中的对应 | 登记,交 Review Gate(`SUBMISSION_NOTE.md` 第 4 节第 8 项) |
| V1-23 | R1-DA M8 | 流程 | data-auditor 运行过一次 `git write-tree`(只写入可能已存在的树对象,不改 index 与跟踪文件) | 登记(披露) |

第 1 轮登记未修:21 条(V1-1 至 V1-23,除 V1-5、V1-20;V1-8 中 L6 count 一半已随 R1-DA M3 修正,出处注记一半未修,按未修计)。

## 2. 第 2 轮(暂存树 `f395c476`,修复提交 `266b64b7`;最后一轮)

code-reviewer:PASS(第 1 轮 BLOCKER 与 13 个 MAJOR 逐条为“已解决”或“部分解决”;新提 4 个 MAJOR、15 个 MINOR);data-auditor:PASS(只作参考;B1、M2–M4 已解决;观察 N1–N5)。按 Owner 的上限,第 2 轮之后无论结论如何都停止修改,以下全部只登记;4 个 MAJOR 交 Review Gate(`reports/AUTHORING_REPORT.md` 第 5 节)。

| # | 来源 | 严重度 | 位置 | 问题(摘要;原文见来源) | 影响(审查所注) | 处理 |
|---|---|---|---|---|---|---|
| V2-1 | R2-CR MAJOR 1 | MAJOR | 协议第 0 节适用表、第 9.7 节 | B24 列为“照原文适用”,但 B24 的最终状态规则(Gate 0 与 T1–T3 → PASS)与第 9.7 节(主比较 NOT_REACHED / MATCH_FAILED 时的最终状态)冲突;应改为只适用 T1–T3 的原因词与 T3 的读法 | 门槛(最终状态)、可复现性 | 登记,交 Review Gate(第 2 轮之后不修) |
| V2-2 | R2-CR MAJOR 2 | MAJOR | 协议第 12 节 ST11 公式;`reports/authoring/compute_estimate.txt` | 采用缩减方案时,正文的固定比值 1.26、0.53 与 compute_estimate.txt 中 R2、R4 的比值 1.41、0.84 不一致;R1–R4 的各项计数没有列出 | 门槛(ST11)、可复现性;只在采用缩减方案时 | 登记,交 Review Gate |
| V2-3 | R2-CR MAJOR 3 | MAJOR(未验证) | 协议第 4 节 Z0、第 7.5 节 G-D1;`DOSE_SPACE.json` controls.Z0 | learning rate 为 0 时,AdamW 的 `addcdiv_(…, value=-0.0)` 可能把存为 −0.0 的参数变成 +0.0:数值相等、原始字节不同,B25 的 `state_sha256` 会不同,G-D1 误判为 IMPLEMENTATION_FAIL;可选做法:G-D1 的参数一致性改用逐张量数值相等(`torch.equal`),`state_sha256` 只报告 | 门槛(G-D1 → Gate D)、损伤测量 | 登记,交 Review Gate(实现前须决定) |
| V2-4 | R2-CR MAJOR 4 | MAJOR(不确定) | 协议第 7.5 节 | 第 1 轮 M10 的剩余部分:Task Order 7.5 的“不该造成损伤的对照在种子之间的波动”仍由 Z0 按构造给出 0;训练种子波动只由 P+ 报告、在 Gate M 中以“每个种子同向”处理 | 损伤测量、门槛 | 登记,交 Review Gate |
| V2-5 | R2-CR m1 | MINOR | 协议第 0 节适用表 | B10 原文“mean of the 120 drawn values”在 V1 应为 240,应列入“改写后适用” | — | 登记 |
| V2-6 | R2-CR m2 | MINOR | 协议第 0 节适用表 | B3 的 ruling_note 要求第 1 步把 train_Y 的哈希写入 manifest,与 ST12“不改写 JSON”字面冲突(V1 已有参考哈希,实际不会执行) | — | 登记 |
| V2-7 | R2-CR m3 | MINOR | 协议第 3 节第 1 条 | 删去占位字段后仍写“参考哈希与生成状态” | — | 登记 |
| V2-8 | R2-CR m4 | MINOR | 协议第 6.4 节第 2a 条 | 精确算术的范围没有覆盖 G0.4、G0.5、ST3、T1 的阈值比较 | — | 登记 |
| V2-9 | R2-CR m5 | MINOR | 协议第 6.4 节第 2a 条 | (1 − w) 取 float(1 − w) 还是 1 − float(w) 未写;所列“浮点量”应只是 d 与 e(e 是整数) | — | 登记 |
| V2-10 | R2-CR m6 | MINOR | `DOSE_SPACE.json` iso | 没有登记第 2a 条;targets、tau 是 JSON 浮点数,`Fraction(0.7)` 不等于 7/10 | — | 登记(同 R2-DA N2) |
| V2-11 | R2-CR m7 | MINOR | `DATA_MANIFEST.json: reported_values` | 预检一项没有列 ST11 公式的 t_load、t_save、t_reload、G;Gate D 一项没有列 P+ 三个种子的标准差 | — | 登记 |
| V2-12 | R2-CR m8 | MINOR | 协议第 7.5 节;`DAMAGE_MANIFEST.json` | “m(D2) 最大为 2 × sqrt(0.25/800)”“by construction”不严格(bootstrap 的 Monte Carlo 误差;R2 下题数为 400) | — | 登记(同 R2-DA N1) |
| V2-13 | R2-CR m9 | MINOR | 协议第 12 节 ST11 公式 | Y(batch 16)的步数按 t_F 计时,偏低,量级小 | — | 登记(同 V1-2) |
| V2-14 | R2-CR m10 | MINOR | 协议第 4 节 | Z0 的理由“2 遍走过训练流程的每一段代码”不准确:Z0 不做剂量点评测,不走第 6.7 节的条件保存 | — | 登记 |
| V2-15 | R2-CR m11 | MINOR | 协议第 6.3 节 | 换算没有计入 V1 第 1 遍的 warmup(各方法越过 0.70 的遍数约后移 0.5 遍;覆盖结论不变) | — | 登记 |
| V2-16 | R2-CR m12 | MINOR | 协议第 7.1 节 | ARC 的 862、7 以 data-auditor 的 stdout 为出处,而 data-auditor 为“待验证”;Executor 的参考构建只访问了 806 行(Executor 在报告提交中另行计数并入库:Challenge 295 + Easy 567 = 862,`reports/authoring/arc_dev_choice_counts.txt`) | — | 登记(同 R2-DA N5) |
| V2-17 | R2-CR m13 | MINOR | 协议第 10 节第 1 步 | 核对范围写“第 2 节与 DAMAGE_MANIFEST.json”,ST12(1) 写三个 manifest | — | 登记 |
| V2-18 | R2-CR m14 | MINOR | 协议第 13 节 ST9 | ST9 在第 9 步之后触发时从第 2 步重来,会在看过 DEV 方法比较之后重算 margin,与第 7.6 节冲突 | — | 登记 |
| V2-19 | R2-CR m15 | MINOR | 协议第 10、12 节 | 第 9 步等待 Owner 批准的时间是否计入累计 GPU 时间、ST7 的前瞻如何估算下一步耗时,没有写 | — | 登记 |
| V2-20 | R2-DA N1 | 观察 | `DAMAGE_MANIFEST.json`、协议第 7.5 节 | 同 V2-12 | 全部否 | 登记 |
| V2-21 | R2-DA N2 | 观察 | `DOSE_SPACE.json` iso | 同 V2-10;只有实现不按第 2a 条取值时才影响 | 可复现性、iso(低) | 登记 |
| V2-22 | R2-DA N3 | 观察 | 协议第 6.4 节第 1 条 | 同 V1-12;非单调曲线上两种读法在 50,000 个类曲线序列中 718 个结果不同,单调序列中为 0;第 6.7 节在两种读法下都没有漏存端点 | 可复现性、iso(少见情形) | 登记,请 Review Gate 确认以形式规则为准 |
| V2-23 | R2-DA N4 | 观察 | `DATA_MANIFEST.json` anchor_text 的 record | `encode(text, …)` 中的 text 指源文档,与字段 `text` 同名 | 全部否 | 登记 |
| V2-24 | R2-DA N5 | 观察 | 协议第 7.1 节 | 同 V2-16:协议引用审查方的输出作为依据是否允许 | 全部否 | 登记,交 Review Gate |

第 2 轮登记未修:24 条(V2-1 至 V2-24;其中 4 个 MAJOR)。

## 3. 合计

登记未修 45 条(第 1 轮 21 条,第 2 轮 24 条)。交 Review Gate 决定或确认的:V2-1 至 V2-4(第 2 轮的 4 个 MAJOR)、V1-18、V1-22、V2-22、V2-24,以及 `SUBMISSION_NOTE.md` 第 4、5 节列出的事项。
