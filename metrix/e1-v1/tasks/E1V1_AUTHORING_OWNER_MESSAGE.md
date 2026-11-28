读 CLAUDE.md、metrix/CLAUDE.md、metrix/e1-pilot/METRIX_E1_PROTOCOL.md（协议 v1.1 全文）、metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md、metrix/e1-pilot/reports/DEFERRED_MINORS.md 1.44 节与第 3 节、metrix/e1-pilot/results/ 下的记录。

本消息分两部分：A 是对 Pilot 报告的一次勘误（在 Pilot 分支上，一个提交）；B 是 Owner 于 2026-11-28 17:24 JST 批准的 METRIX-E1-V1 协议撰写 Task Order V1.0。先做 A，再做 B。把本消息在「=====」之前的部分原文存为 metrix/e1-v1/tasks/E1V1_AUTHORING_OWNER_MESSAGE.md（在 B 的第一个工作提交中提交）。

第 0 步照旧：比对 ~/.claude/ 下的副本与分支上的文件；调用审查 subagent 时第一句按 metrix/CLAUDE.md 第 5 节固定。全程只用 CPU，不加载模型权重，不训练，不评测，不生成或读取 TEST。

A. Pilot 报告勘误（Review Gate 裁决，2026-11-28，Owner 知悉）

确认 metrix-e1-pilot-protocol-v1 的最新提交为 4535fd0985b03f6fcaf3e5f600726bfbaaef3816，然后在该分支上做一个纯文档提交，只送 code-reviewer 一轮（有 BLOCKER 才修复后再送，其余登记），快进推送，不推送标签：

A1（PR1）PILOT_FINAL_REPORT.md 中 Gate 0 与 T1–T3 两张表的「门槛」一列：替换为协议第 8 节对应行的原文，不改写、不删节。
A2（PR2）报告偏差第 7 项中「协议与冻结文件无改动」一句：替换为 DEFERRED_MINORS 1.44 中已登记的更正写法（两个 manifest 由第 8 节第 1 步按协议写入哈希；协议正文与 SEARCH_SPACE.json 无改动）。
A3（PR4）在报告「运行中的偏差与事件」中保留现有记述，并补一句：Review Gate 的决定记录已把该有条件批准记为 Owner 于 2026-11-28 约 16:19–16:20 JST 作出、17:24 JST 由 Owner 确认。
A4（PR3、PR21、PR22）metrix/CLAUDE.md 第 2 节的状态句：把其中的「reports/PILOT_FINAL_REPORT.md」替换为「metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md」，并在句末括注内补「原因：正式运行与报告完成；作用范围：永久」。另在第 8 节末尾追加一条：「E1 Pilot 结束后，第 4 节（算力，含 4 小时上限）只适用于 E1 Pilot，不延续；第 5、6、7、9、10 节的做法在 E1-V1 阶段继续适用，直到 E1-V1 的协议或 Task Order 另有规定（出处：Review Gate 裁决，Owner 批准，2026-11-28，永久）。」
A5 在报告「没有入库的内容」一节补记责任说明原文：「TEST 通用文本的 NLL 与 dNLL 未写入入库的结果文件，机器终止后无法恢复。终止机器的建议由 Review Gate 提出，当时称汇总结果均已入库，这一说法对 TEST 的 dNLL 不成立。该数值在 Pilot 中只报告、不进 T1–T3，最终状态不受影响。」
A6 给出勘误提交的完整 hash。此后不再向 metrix-e1-pilot-protocol-v1 推送任何提交。

B. E1-V1 协议撰写

B1 从 A6 的提交新建分支 metrix-e1-v1-protocol-v1，记录起点的完整 hash。只在这个新分支上工作，只做普通推送，不得 force push，不推送标签，不经 PR。
B2 把下面「=====」之间的内容原文存为 metrix/e1-v1/tasks/E1V1_PROTOCOL_TASK_ORDER_V1.md，与第一个工作提交一起提交。
B3 执行 Task Order。完成后按其第 15 节的四部分格式回复，状态写为 AWAITING_REVIEW_GATE，然后停下。

补充说明（Review Gate，作用范围：E1-V1 协议撰写）：

	•	Owner 已决定：比较点为 DEV 准确率 0.70、0.80、0.90；加第二个损伤指标；题目难度不变、规模 320 条。
	•	吸取 Pilot 的教训，协议须规定：协议要求报告的每一个数值（包括只报告、不进门槛的指标，以及 TEST 上的损伤指标）的汇总值都写入入库的结果文件；并规定在终止机器之前由 data-auditor 核对「协议要求报告的每个数值都能只从仓库得到」，核对通过才可终止。
	•	额度不足时在自然的段落之间停下并提交已完成的部分，不要在审查进行到一半时提交。

修改次数上限（Owner 要求，2026-11-28 17:43 JST；与 Task Order 冲突时以本段为准）：

	•	A 部分：只有 1 个文档提交、1 轮 code-reviewer。除 BLOCKER 外不再修改。
	•	B 部分：协议与 5 个配套文件写成后一次送审。code-reviewer 与 data-auditor 各最多 2 轮；第 2 轮之后无论结论如何都停止修改，提交现状与审查原文，交 Review Gate。
	•	每一轮只修 BLOCKER，以及影响数据、指标、门槛、可复现性、iso-acquisition 匹配或损伤测量的 MAJOR。其余 MAJOR 与全部 MINOR 只登记到 metrix/e1-v1/reports/DEFERRED_MINORS.md，不修。
	•	不为措辞、格式、路径写法或记录的完整性单独开修改轮次；报告提交不另送审查。
	•	B 部分的提交总数以 6 个为上限（工作提交、最多 2 个修复提交、报告提交、证据提交各算在内）；需要超过时停下报告原因。
	•	最终回复中写明：每个文件被修改的轮数、两份审查各用了几轮、登记未修的条目数。
	•	提出 D2 数据集时，只能使用能在本环境核实 revision 与 sha256 的公开数据集；核实不了就列为待决并说明原因，不得凭记忆填写哈希。
