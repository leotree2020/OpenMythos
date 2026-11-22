# Metrix E1-PILOT 第 8 轮指令(原文)

- 来源:Project Owner 在 Claude Code 会话 session_01J5mxaUfve5PtsqZQQDkJcJ 中下达,2026-11-22(会话容器启动于 05:30:39 UTC,`reports/round8/t0_copy_check.txt`)。
- 指令中的“Review Gate 第 7 轮裁决”是 Review Gate 对 `reports/ROUND7_REPORT.md`“待 Review Gate 决定”各项的裁决。下面照录全文。
- 共两段:第一段是本轮指令;第二段是 Owner 在第 4 项审查完成、第 5 项的提交前审查进行中(约 05:55 UTC)补充的五项。补充之后,Executor 就其中两点提问,Owner 的回答也照录在第二段末尾。

---

## 第一段:本轮指令

读 metrix/CLAUDE.md。本轮执行协议冻结。Owner 已于 2026-11-22 05:27 UTC 批准冻结。允许快进推送 metrix-e1-pilot-protocol-v1 和推送标签，不得 force push。不开放新的设计问题。

0. 比对 ~/.claude/ 副本与分支文件，做法同第 7 轮；调用审查时首句按第 5 节固定。
1. 执行 Review Gate 第 7 轮裁决（全部记入第 14 节）：
   a. 写明 train_S.jsonl 每行 {fact_id, answer_fact_id, text}，candidates.json 为 {fact_id: [4 个候选]}。
   b. L6 TEST 部分：13-gram 在每篇文档内取，合并后计种类数；文本为实际送入模型的 id 解码所得。Executor 与 data-auditor 结果不一致时按 BLOCKED 处理并报告 Owner。
   c. EM：删除 <think> 段后，先去开头空白，再取第一行。
   d. DATA_MANIFEST.json 补入锚文本与 Qwen 分词器全部文件的 sha256。
   e. metrix/CLAUDE.md 第 8 节改为：「本阶段」裁决也可写入本文件，须注明作用范围，本阶段结束时失效。
2. 把所有 PROPOSED 改为冻结值：训练契约表、SEARCH_SPACE.json 的 status、第 13 节两项按提案批准（E1-V1 目标 320 条 fact，Pilot 后按 G0.10 重算；dNLL ≤ +0.03 在 Pilot 中只报告），注明「Owner 批准，2026-11-22 05:27 UTC」。
3. 协议状态行改为 PROTOCOL_FROZEN。第 1–3 项放在同一个提交里，这个提交就是冻结提交。
4. 对冻结提交调用 code-reviewer（只审查与本指令是否逐条一致、有无 BLOCKER）和 data-auditor（独立复算全部冻结哈希）。新提出的 MAJOR/MINOR 只登记不修。有 BLOCKER 就停下报告，不得进入第 5 项。
5. 审查通过后，另起一个提交新建 metrix/e1-pilot/PROTOCOL_FROZEN，内容包括：冻结提交的完整 hash；该提交下协议文件与三个 JSON 的 sha256；全部数据哈希；「Owner 批准，2026-11-22 05:27 UTC」。给冻结提交打标签 metrix-e1-pilot-frozen 并推送。
6. 报告写入 reports/ROUND8_REPORT.md，提交推送，给出冻结提交 hash 与标签推送输出。

---

## 第二段:补充(原文)

补充（对照 Task Order V1.2，放进冻结提交，全部记入第 14 节，注明「对照 Task Order V1.2 补齐」）：
a. G0.8 改为：同一 checkpoint 两次评测，候选分数差 ≤ 1e-4；某题两次中任一次最高两个候选分数差 ≤ 1e-4 时允许预测不同，其余预测须完全相同；并列判为错。实现须开启 PyTorch 确定性设置并记录。
b. 第 2.5 节：干扰项池少于 4 个答案即 IMPLEMENTATION_FAIL，不生成合成干扰项。
c. G0.10：分别用 σ_d 的 bootstrap 2.5 分位、点估计、97.5 分位计算所需 fact 数，以最大者作为 E1-V1 规划依据；写明「Pilot 的规模估计是规划估计，不是保证」。
d. 新增预检：正式运行前在 A100 上跑第一个配置的前 20 步，记录每步耗时、tokens/s、峰值显存与预估总时长；预估超过 3.5 小时即停止并报告 Owner（新增 ST11）。
e. 新增 ST12：任何数据、manifest、模板或候选的哈希，或模型、分词器版本与冻结值不一致 → 停止，BLOCKED。新增 ST13：配置冻结前读取 TEST → IMPLEMENTATION_FAIL，本次 Pilot 全部作废。

### Executor 的提问与 Owner 的回答

Executor 用提问工具问了两点(原文为英文,两题各附两个选项):
1. e 的 ST12:第 8 节第 1 步要把数据文件的哈希写入两个 manifest 并提交,manifest 的 sha256 会因此改变;照字面 ST12 会在第 1 步触发 BLOCKED。选项:“第 1 步填写的字段除外(推荐)”/“照字面写,只报告冲突”。
2. a 的 G0.8:现有 G0.8 还写了“对 F 选定配置的 3 个 checkpoint”与“每个通用窗口的 NLL 差 ≤ 1e-5”,新文字都没有提。选项:“两者都保留(推荐)”/“整条替换”。

Owner 的回答(原文):“Please run the last what I sent, it’s the additional things what I want do.”

Executor 据此按补充原文字面执行:G0.8 整条换成补充 a 的文字,ST12 照字面写;两处的后果列入 `reports/ROUND8_REPORT.md`“待 Review Gate 决定”。
