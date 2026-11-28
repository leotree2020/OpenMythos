METRIX · E1-V1 · PROTOCOL AUTHORING

PM Task Order — V1.0（Review Gate 起草，2026-11-28；Owner 批准后生效）

方向依据：claude/metrix-vision-and-roadmap.md 第 4 节。结构沿用 E1-PILOT 的 Task Order V1.2。

0. 元数据

项	值
Task ID	METRIX-E1-V1-PROTOCOL-AUTHORING-V1.0
Owner	Project Owner（Miyaji）
Executor	Claude Code（metrix 云端环境）
阶段	PROTOCOL DESIGN
模型	Qwen/Qwen3-1.7B @ 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
起点	metrix-e1-pilot-protocol-v1 上 PILOT_REPORT_ORDER 完成后的最新提交（写明完整 hash）
新分支	metrix-e1-v1-protocol-v1
工作目录	metrix/e1-v1/（不改动 metrix/e1-pilot/ 下任何文件）
允许训练 / 评测 / 使用 GPU	否
生成或读取 V1 的 TEST	否
允许得出科学结论	否
结束状态	AWAITING_REVIEW_GATE

1. 一句话任务

写出可以冻结的 METRIX_E1V1_PROTOCOL.md 及配套契约，使未来的 Executor 不依赖任何聊天记录，就能实现并执行 METRIX-E1-V1，并得到可解释的结果。本任务只写协议：不训练、不评测、不实现实验、不生成 TEST 数据。

2. E1-V1 的科学问题

在相同的事实学习水平上，全参数微调（F）、LoRA（L）、带锚点约束的全参数微调（A）对模型通用能力的损伤各有多大。

依据（E1-PILOT 的事实，只用于提出问题，不构成结论）：F 的 TEST 准确率 0.930；DEV 通用文本 dNLL 为 F +1.09 到 +1.47、L +3.38 到 +3.95、A +0.20 到 +0.23；A 的学习量低于 F（Δ(A−F) = −0.061，EM 0.15–0.25 对 0.54–0.78）。因此不同学习水平之间的损伤不可直接比较。

E1-V1 分两个 Gate：

	•	Gate D（损伤测量合格）：证明"通用能力损伤"的测量可靠。Pilot 只验证了事实获取的测量，没有验证损伤的测量。
	•	Gate M（方法比较）：只有 Gate D 通过之后才进行，在拉平学习水平的前提下比较损伤。

3. 红线（违反任一条即本任务 FAIL）

	1. 	不训练任何模型，不运行模型评测，不使用 GPU。
	2. 	不生成、实例化、读取 V1 的 TEST 样本（事实 QA 的 TEST 与通用能力的 TEST 都包括在内）。
	3. 	不修改模型结构；不修改 metrix/e1-pilot/ 下任何文件；metrix/ 以外不改动。
	4. 	arm 只有 N、F、L、A，以及第 8 节规定的对照；不新增机制（Growth、Consolidation、RAG、多跳推理、learned controller、agent 等）。
	5. 	**不得在不同学习水平之间直接比较损伤。**任何方法间的损伤比较都必须在第 6 节定义的 iso-acquisition 点上进行。
	6. 	不涉及 Retention：不训练第二批事实，不定义、不报告"旧事实保留"的任何数字。
	7. 	不用 V1 的实验结果选择门槛。Pilot 的结果可以用于规划（方差估计、搜索范围），每一处使用都要写明来源文件与字段。
	8. 	除第 14 节列出的待决字段外，任何可执行参数不得留 TBD。每个 PROPOSED 值附一句理由或来源。
	9. 	需求互相矛盾，或执行需要训练、评测、读取 TEST：停下，返回 HALTED 并写明原因。不猜测，不自行修补需求。

4. 交付物

只在 metrix/e1-v1/ 下新建：

metrix/e1-v1/
├── METRIX_E1V1_PROTOCOL.md
├── DATA_MANIFEST.json        # 事实数据
├── SPLIT_MANIFEST.json       # 划分、模板、候选
├── DOSE_SPACE.json           # 各方法的配置与剂量阶梯
├── DAMAGE_MANIFEST.json      # 损伤评测集：来源、revision、哈希、划分
└── SUBMISSION_NOTE.md

不提交：checkpoint、权重、生成的数据集、任何 TEST 内容、评测输出。

5. 事实数据

	1. 	共 320 条 fact：240 条 learned、80 条 unread。natural 与 random 两个 stratum 各占 50%。
	2. 	全部重新生成：使用新的 DATA_SEED，不得复用 Pilot 的任何 fact、候选或 TEST 实例。协议须给出可执行的检查，证明 V1 的 fact 与 Pilot 的 fact 没有交集（实体与答案都不重合）。
	3. 	难度不变（Owner 决定，2026-11-28）：relation 种类、实体与答案的生成规则、TRAIN / DEV / TEST 的模板族、四选一候选规则，都沿用 Pilot 协议 v1.1 的定义，只扩大规模。逐条写明"沿用 Pilot 第几节"，不得只写"同 Pilot"。
	4. 	每条 learned fact：1 条 TRAIN 陈述句，至少 2 个 DEV 问法，至少 3 个 TEST 问法。模板族之间互不相交。
	5. 	泄漏契约沿用 Pilot 的 L1–L6，另加第 7.4 节的要求。
	6. 	统计单位是 fact；按 fact 聚合用 mean（Amendment A）。

6. iso-acquisition 设计（本协议的核心）

6.1 学习水平的定义：Acq = Acc(arm, DEV-QA, learned)，四选一，按 Pilot 第 5 节的打分方式。

6.2 比较点（Owner 决定，2026-11-28）：Acq = 0.70、0.80、0.90。

6.3 剂量阶梯：每种方法都要产生一条"学习量—损伤"曲线。协议须在 DOSE_SPACE.json 中冻结：

	•	剂量维度是什么（例如训练步数、学习率、LoRA rank、锚点 λ），以及每种方法的全部剂量点。每条曲线至少 5 个剂量点，范围须覆盖 0.70 到 0.90（依据 Pilot 的训练记录说明为什么预计能覆盖）。
	•	F、L、A 的配置数相同、剂量点数相同、训练 token 预算的规则相同；不相同的地方必须写明并给出计算量匹配的理由（Amendment F）。
	•	种子数（至少 3 个）与种子的用法。

6.4 iso 点的确定规则（冻结，不得由实现决定）：

	•	如何从曲线得到某个比较点上的损伤值：选最近的剂量点，或在相邻两点间插值，二者选一并写明公式。
	•	匹配容差：实际 Acq 与比较点的最大允许偏差，给出数值与理由。
	•	未达到规则：某方法的曲线没有覆盖某个比较点时，该方法在该点记为 NOT_REACHED，不参与该点的比较，不得外推。
	•	iso 点只用 DEV 确定。确定后，(方法, 配置, 剂量点) 写入选择冻结记录，之后才允许生成和评测 TEST。

6.5 TEST 上的匹配验证：在 TEST 上重新测各 iso 点的学习量。各方法在同一比较点上的 TEST 学习量之差超过冻结的容差时，该点的比较记为 MATCH_FAILED，不解释其损伤差异。

6.6 防止选择偏差：如果某个比较点上是从多个配置中选出损伤最小的一个，协议必须说明 DEV 上的选择如何不污染 TEST 上的比较（例如选择只用 DEV 的通用文本，比较只用 TEST 的通用文本，两者文档不相交）。

7. 损伤的测量

7.1 两个互相独立的指标（Owner 决定加第二个指标，2026-11-28）：

	•	D1：通用文本 dNLL。dNLL = NLL(arm) − NLL(N)，按 token 平均，定义沿用 Pilot 第 5 节，但评测集须扩大并按领域分层。
	•	D2：能力测验。一个与文本困惑度无关的指标：公开的选择题数据集上的正确率下降，dAcc = Acc(arm) − Acc(N)，用候选的条件对数似然打分。协议须提出具体数据集，固定 revision 与 sha256，写明许可证是否允许研究使用，说明题目与 V1 的虚构事实无关。

7.2 评测集：D1 与 D2 各自划分为 DEV 与 TEST，文档或题目不相交。给出每个划分的数量与确定性的抽取规则。Gate D 与 iso 点的确定只用 DEV 部分。

7.3 统计单位：D1 以文档为单位，D2 以题目为单位，做配对 bootstrap（10,000 次）。种子之间的变化单独报告。

7.4 与锚文本隔离：arm A 用锚文本做约束。损伤评测集必须包含至少一个与锚文本来源不同的领域，并且同来源与不同来源的结果分开报告；与锚文本的 n-gram 重叠检查沿用 L6 的做法。否则 A 的"损伤小"可能只是在它被约束的分布上测量。

7.5 Gate D 的条件（全部为数值，冻结）：

	•	噪声基线：N 在评测集不同抽样下的波动（bootstrap SD），以及一个不该造成损伤的对照在种子之间的波动。
	•	阴性对照：协议须定义一个不应造成损伤的条件（例如学习率为 0 的完整训练流程），其 D1、D2 必须落在冻结的范围之内。
	•	阳性对照：协议须定义一个预期造成明显损伤的条件（Pilot 的 F6 配置 dNLL 为 +5.55，可作依据），其 D1、D2 必须超过冻结的下限。阳性对照不过，说明尺子量不出损伤，Gate M 不进行。
	•	复现：同一 checkpoint 重复评测的容差。
	•	D1 与 D2 的一致性：只报告，不设门槛。

7.6 non-inferiority margin：协议冻结时写死的是计算公式（由 Gate D 的噪声基线推出，例如噪声 SD 的固定倍数），以及公式的输入来自哪条记录。数值在 Gate D 通过后计算，写入 MARGIN_RECORD 并提交，之后才允许运行 Gate M 的任何训练。不得在看到方法比较的结果之后确定或修改 margin。

8. arm 与对照

arm	定义	用途
N	冻结的基座，不训练	学习量与损伤的基线
F	全参数微调	剂量曲线
L	LoRA	剂量曲线
A	全参数微调 + 锚点约束	剂量曲线
S	打乱 entity→answer 映射	在新数据上重新确认事实测量合格，只用一个剂量点
Y	只有文风、无映射	同上
阴性对照、阳性对照	第 7.5 节	Gate D

S 与 Y 沿用 Pilot 的定义和数值门槛（G0.6、G0.7），用 F 的一个冻结剂量点，不独立调参。

9. Gate 与比较

9.1 Gate 0（事实测量再确认）：沿用 Pilot 的 G0.1–G0.9 的数值；F 的上限检查（G0.9）改为对最高剂量点报告、不设门槛，因为难度不变是 Owner 的决定，写明这一点。

9.2 Gate D：第 7.5 节。

9.3 Gate M 的比较：在每个比较点上报告 Δ损伤(L−F)、Δ损伤(A−F)，D1 与 D2 各一组，含 95% CI。

9.4 主比较只有一个族：协议须指定唯一的主比较（例如 Acq = 0.80 上的 D1），其余全部为次要比较。写明多重比较的处理规则。主比较的结论词汇（non-inferior / inferior / superior / inconclusive）用数值条件定义。

9.5 TEST：Gate 0、Gate D、iso 点的确定都只用 TRAIN 与 DEV。TEST（事实 QA 与损伤评测）在选择冻结之后只评一次，沿用 Pilot 的 ST10、标记与"只评一次"的闸门。

9.6 失败分类：只用 Pilot 协议第 9 节的固定词汇，另加本任务引入的 NOT_REACHED、MATCH_FAILED，各给出定义。

10. 算力与硬件

	1. 	硬件沿用单张 NVIDIA A100 80GB，设备全名在一次运行内不得改变。
	2. 	**GPU 累计时间上限：OWNER 待决。**不得沿用 Pilot 的 4 小时，不得自行填写数值。
	3. 	协议须给出估算，供 Owner 决定：训练次数、评测次数、checkpoint 数量与磁盘占用；依据 Pilot 的实测（results/step2_record.json、各 training_runs/*.json、实验记录中的算力核算）推算的总 GPU 时间与租用时间；按每小时 2.14 美元的费用。
	4. 	另给出至少一个缩减方案（例如减少剂量点、减少配置、减少种子），写明每个方案省多少时间、损失什么。
	5. 	预检（ST11）与超时即停（ST7）的机制保留，阈值与上限挂钩。

11. 停止条件与实验记录

沿用 Pilot 协议第 10、11 节，并补入：Gate D 未通过即停、MARGIN_RECORD 未提交即运行 Gate M 的训练（IMPLEMENTATION_FAIL）、iso 点确定之前读取 TEST。

12. Non-claims 与范围外

E1-V1 不能确立：持续学习是否有效；旧事实的保留（Retention，归 E2）；长期记忆；成长与扩容的价值；巩固机制的价值；多跳推理；在其他模型或更大规模上的表现；Metrix 架构的优越性。

范围外：E2 及之后的阶段；第二批事实；任何新机制；部署与推理服务；模型结构改动；题目加难（Owner 决定留到以后）。

13. 治理（吸取 Pilot 的教训）

	1. 	Review Gate 只有一次，只检查六项：泄漏防护；统计伪重复；调参与剂量预算的公平；可执行的停止条件；iso-acquisition 匹配的有效性；损伤测量的合格条件。不是扩大范围的机会。未通过的部分最多修订两轮；与这六项无关的 MAJOR、MINOR 只登记。
	2. 	批准必须入库：Owner 的每一次批准（冻结、租卡、TEST 生成、TEST 评测）由 Executor 把原文、时间与条件写入仓库的记录文件并提交，之后才执行被批准的动作。
	3. 	审查与证据的做法沿用 metrix/CLAUDE.md：每个提交前调用 code-reviewer；涉及数据、划分、候选或评测定义时再调用 data-auditor；原始输出入库；证据提交只含明确路径。
	4. 	Review Gate 的修改指令一律写明被替换的原句，不使用笼统的"改为"。
	5. 	协议冻结后的任何改动需要 Owner 批准的新版本。

14. 允许留给 Review Gate / Owner 的待决字段

只有这三项可以标为 PENDING：

	1. 	GPU 累计时间上限（Owner）。
	2. 	D2 能力测验所用的数据集（协议提出首选与一个备选，Owner 批准其一）。
	3. 	剂量点与配置的数量，在第 10 节的估算超出 Owner 可接受的范围时调整。

其余可执行参数都必须有具体的、附理由的 PROPOSED 值。

15. 提交格式

Executor 的最终回复包含四部分：

	1. 	SUBMISSION_NOTE.md 全文。
	2. 	全部 PROPOSED 值的表，每个附一句理由。
	3. 	第 14 节三项待决字段：建议值与理由；算力估算与缩减方案。
	4. 	最可能存在科学有效性缺陷的三个章节及原因。

不包含：实验结果、机制层面的意见、无关建议。

16. 最终状态

提交前：PROTOCOL DESIGN。提交后：AWAITING_REVIEW_GATE。Owner 批准后：PROTOCOL_FROZEN。冻结之后另发 Implementation Task Order；不得在本 Task ID 下实现或执行 E1-V1。
