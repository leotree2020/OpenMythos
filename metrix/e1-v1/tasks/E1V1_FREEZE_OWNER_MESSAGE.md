# E1V1_FREEZE_OWNER_MESSAGE

- 收到时间（UTC）：2026-11-28 12:13:25 UTC。来源：收到本消息后，本会话执行的第一条命令 `date -u` 的输出（`Sat Nov 28 12:13:25 UTC 2026`）；消息本身不带时间戳。
- 运行环境：Claude Code 云端容器（CPU only），工作目录 /home/user/OpenMythos。
- 记录依据：本消息第二段与 Task Order 第 13 节第 2 条。本文件先单独提交并推送（证据提交），之后才执行被批准的动作。
- Owner 的决定以本消息的发出为准：Owner 发出本消息即表示批准 C 部分的四项（C1–C4）。

以下两条分隔线之间为消息原文，未改动。

=====

读 CLAUDE.md、metrix/CLAUDE.md、metrix/e1-v1/METRIX_E1V1_PROTOCOL.md、metrix/e1-v1/SUBMISSION_NOTE.md、metrix/e1-v1/reports/DEFERRED_MINORS.md、metrix/e1-v1/tasks/ 下两份指令。

本消息是 METRIX-E1-V1 的 Review Gate 裁决与冻结指令。Review Gate 已按 Task Order 第 13 节审查一次（六项：泄漏防护、统计伪重复、调参与剂量预算的公平、停止条件、iso-acquisition 匹配、损伤测量合格条件），结论：通过，附下列修改。本轮把修改与冻结放在一个提交里完成。

Owner 的决定以本消息的发出为准：Owner 发出本消息即表示批准 C 部分的四项。Executor 把本消息原文与收到它的 UTC 时间写入 metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md，**先提交并推送这一个文件（证据提交），再做其余任何事**（Task Order 第 13 节第 2 条）。

分支：只在 metrix-e1-v1-protocol-v1 上工作，起点应为 bc03348ad8b2390ac3df452631d63b8bfe66ad67；只做普通推送，不得 force push，不推送标签，不经 PR。全程只用 CPU，不加载模型权重，不训练，不评测，不生成或读取任何 TEST。第 0 步照旧（比对 ~/.claude/ 副本；调用审查时第一句按 metrix/CLAUDE.md 第 5 节固定）。

## A. Review Gate 要求的修改（每条写明被替换的内容；全部记入协议第 17 节，注明「Review Gate 裁决 2026-11-28」）

A1（V2-1）协议第 0 节的适用表中 B24 一行：把「照原文适用」替换为「只适用其中 T1–T3 的原因词与 T3 的读法；最终状态按本协议第 9.7 节」。

A2（V2-3）协议第 7.5 节 G-D1 一行中「每个种子:重载后的 `state_sha256` 等于 N 的 `state_sha256`」：替换为「每个种子:重载后的每个参数张量与 N 的对应张量数值相等（`torch.equal`；−0.0 与 +0.0 视为相等）；`state_sha256` 是否与 N 相同只报告」。第 4 节 Z0 的理由中「因此 Z0 的 `state_sha256` 必须与 N 相同(G-D1)」同步替换为「因此 Z0 的每个参数张量必须与 N 数值相等(G-D1)」。`DOSE_SPACE.json` 的 controls.Z0 同步。

A3（损伤指标按指标分别合格）协议第 7.5 节「**Gate D 通过** = G-D1、G-D2、G-D3、G-D4 全部满足。」一句：替换为「**Gate D 通过** = G-D1、G-D4 满足，且 G-D2、G-D3 中关于 D1 的条件（`σ_N` 有限且 > 0、三个 margin 上界、P+ 的 `D1-diff` 条件）全部满足。G-D2、G-D3 中关于 D2 的条件（`σ_N(D2)` 有限且 > 0、P+ 的 `D2` 条件）不满足时，Gate D 仍可通过，但 D2 记为 `D2_NOT_QUALIFIED`：D2 的全部数值照常计算、入库并报告，Gate M 中 D2 的比较不给结论词，不作解释。」第 9.4 节结论词汇的适用范围、第 9.6 节的词汇表（新增 `D2_NOT_QUALIFIED` 及定义）、`DAMAGE_MANIFEST.json` 同步。理由写入第 17 节：D2 的阳性对照阈值没有 Pilot 数据作依据；一把不合格的尺子不应阻止另一把已合格的尺子，主比较只用 `D1-diff`。

A4（Non-claims）协议第 1 节 Non-claims 段末尾追加一句：「另:Pilot 中只学文风的 Y 与打乱映射的 S 也有 0.98–2.14 的 DEV dNLL（`metrix/e1-pilot/results/training_runs/{S,Y}-F3-*.json: dnll`），因此本协议量到的损伤中，有多少来自学到事实本身、多少来自在模板句上训练，本协议不区分，不得就此下结论；S、Y 在 d0 的 D1、D2 与 F 在 d0 的值并列报告。bootstrap 的 CI 不含训练种子之间的变化。」并确认 `DATA_MANIFEST.json: reported_values` 含 S、Y、F 在 d0 的 D1 各项与 D2；没有就补上。

A5（V2-2）协议第 12 节缩减方案表之前加一句：「缩减方案 R1–R4 只供 Owner 决定时参考，不属于冻结的协议；本协议冻结的是主方案。采用任何缩减方案须开新的协议版本。」ST11 公式不改。

A6 不改协议、只记入第 17 节的确认：
- V2-4：阴性对照 Z0 的种子波动按构造为 0、训练种子波动由「三个种子同向」处理，按现状接受。
- V2-22：非单调曲线以第 6.4 节的形式规则为准。
- V2-24：协议可以引用已入库的审查输出作为依据。
- V1-18 与 SUBMISSION_NOTE 第 4 节第 1 项：整行 json.loads 只取 domain、split 两个字段并计数，按 Pilot 的执行解释（2026-11-24）不属于读取 TEST，不记为偏差；此后一律只匹配行首字节。
- V1-22：撰写阶段 subagent 的路径对应按现状接受；两个 agent 定义的更新留给 Implementation Task Order。
- SUBMISSION_NOTE 第 4 节第 5、6、7 项与第 5 节：主比较用 `D1-diff`（books、c4、wikitext 三个领域）接受；每种方法 1 个配置接受；HYPOTHESIS_FAIL 不使用接受；D2 对选项字母打分接受；G-D2 上界与种子波动的处理接受。
- PE1、PE7、PE10（Pilot 勘误的登记项）：按现状接受，不再修改 Pilot 分支。

## B. 不修改的范围

除 A1–A5 列出的句子与其同步项、C 部分的定值、第 17 节的记录外，不改协议与四个 JSON 的任何其它内容。DEFERRED_MINORS 中其余条目一律不修。

## C. Owner 的决定（把协议第 15 节三项待决与全部 PROPOSED 改为冻结值，注明「Owner 批准」与 E1V1_FREEZE_OWNER_MESSAGE.md 中记录的 UTC 时间）

C1 GPU 累计时间上限 H = 9 小时（ST7 = 9 小时；ST11 界限 = 0.875 × 9 = 7.875 小时）。
C2 D2 数据集 = MMLU（`cais/mmlu` @ c30699e8356da336a370243923dbaf21066bb9fe）。ARC 的内容从冻结的 manifest 与正文中标为「未采用的备选」，不删除核实记录。
C3 剂量点与配置的数量 = 主方案：每种方法 1 个配置、10 个剂量点、3 个种子。
C4 批准冻结：A、C 完成且 D 的审查无 BLOCKER 时，协议状态为 PROTOCOL_FROZEN。

## D. 冻结步骤

D1 A1–A5、A6 的记录、C1–C3 的定值、全部 PROPOSED 改为冻结值、协议状态行改为 PROTOCOL_FROZEN、四个 JSON 的版本与状态字段同步、`build_manifests.py` 同步并证明重新生成的四个 JSON 与入库的逐字节相同：全部放在**一个提交**里，这个提交就是冻结提交。
D2 对冻结提交调用 code-reviewer 一轮（只审查：与本消息 A、C 是否逐条一致；有无 BLOCKER）与 data-auditor 一轮（独立复算全部数据哈希与四个 JSON 的字节哈希；确认数据哈希与 bc03348a 时相同）。有 BLOCKER：修复后各再送一轮，这是最后一轮；仍有 BLOCKER 就停下报告。其余 MAJOR、MINOR 只登记。
D3 审查通过后，另起一个提交新建 metrix/e1-v1/PROTOCOL_FROZEN：冻结提交的完整 hash；该提交下协议与四个 JSON 的 sha256；全部数据与输入文件的哈希；Owner 批准的 UTC 时间；标签名 metrix-e1-v1-frozen（由 Owner 推送）。
D4 报告写入 metrix/e1-v1/reports/FREEZE_REPORT.md（不另送审查），与审查原文、audit 输出一起提交并推送。

修改次数上限：冻结提交 1 个；有 BLOCKER 时最多 1 个修复提交（修复提交成为新的冻结提交，D3 引用它）；本轮提交总数以 5 个为上限。

完成后回复：冻结提交的完整 hash；PROTOCOL_FROZEN 中的四个文件 sha256；两份审查的结论与轮数；登记未修的条目数。然后停下。不得开始实现，不得训练或评测。

=====
