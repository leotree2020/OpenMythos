# code-reviewer, E1-V1 freeze, round 1, on freeze commit 9a19e70e1bc16130368caa00bd1bf6fbc126bc8c
# invocation: code-reviewer_round1_prompt.txt; launched 2026-11-28T12:24:49Z; transcript: code-reviewer_round1_transcript.jsonl (copied unchanged)
# extracted unchanged with metrix/e1-pilot/reports/round6/review_extract.py
---
code-reviewer 对冻结提交 9a19e70e1bc16130368caa00bd1bf6fbc126bc8c 的第 1 轮审查

说明
- 依据：指令原文 /home/user/OpenMythos/metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md；被审 diff /home/user/OpenMythos/metrix/e1-v1/reviews/9a19e70e1bc16130368caa00bd1bf6fbc126bc8c/input_round1.diff（下称 diff）；冻结提交下的协议与四个 JSON。下文行号是工作区文件的行号，每处改动行都已和 diff 对照。
- 我只有 Read、Grep、Glob，没有运行任何命令。凡依赖运行结果的判断都标『未验证』；引用已入库原始输出的，写明路径与行号。
- 工作区里有一个目录 /home/user/OpenMythos/metrix/e1-v1/audit/tmp_freeze/，tree_round1.txt 没有列出它，里面是 MMLU、ARC 的 test parquet 等下载文件，应是本轮 data-auditor 的临时目录。它不属于被审提交，我没有读取其内容。

逐条判定
- A1：一致。协议 :39 把 B24 从「照原文适用」的列表中移出，另写一句「B24:只适用其中 T1–T3 的原因词与 T3 的读法；最终状态按本协议第 9.7 节。」替换文字与指令逐字相同。第 0 节这一处确实是段落列表而不是表，这样改是必要的；第 17 节 :463 已注明这样做的原因。:285、:324 仍引用 B24 的原因词与 T3 读法，与 A1 不冲突。
- A2：一致。G-D1 :241 与指令逐字相同；Z0 的理由 :134 已按指令替换；DOSE_SPACE.json:75 controls.Z0 已同步。另外同步了 DAMAGE_MANIFEST.json:182 的 G-D1.rule 与 DATA_MANIFEST.json:383 的 Gate D 一项（见问题 4）。`torch.equal` 按数值比较，对 −0.0 和 +0.0 返回相等，与括注一致『未验证』。
- A3：一致。:247 的替换句与指令逐字相同；9.4 的适用范围 :303 已改；9.6 :316 由「两个词」改为「三个词」，:320 新增 D2_NOT_QUALIFIED 及其定义；DAMAGE_MANIFEST.json:207、:208、:220 已同步；理由已写入 :465。替换句之后紧接的一句也改了（见问题 3），D2_NOT_QUALIFIED 的例外没有同步到 comparison.secondary（见问题 7）。
- A4：一致。:49 的追加句与指令逐字相同。数值已核对：Pilot 中 S、Y 的 dnll 为 0.9819 至 2.1450，取整为「0.98–2.14」，出处 /home/user/OpenMythos/metrix/e1-pilot/results/training_runs/S-F3-seed{101,202,303}.json:492 与 Y-F3-seed{101,202,303}.json:490。reported_values 新增一项（DATA_MANIFEST.json:400-405，gate0_record.json: d0_damage）。原有的「every training run: per dose point」一项是否已经覆盖 S、Y 在 d0 的值，可以有两种读法；但指令要求「并列」，补上是较保守的读法，在「没有就补上」的范围内。
- A5：一致。:391 的追加句与指令逐字相同，位置在缩减方案表之前。ST11 公式 :402 未改（diff:429 是上下文行）。
- A6：一致。:473-481 七项与指令逐字相同，并注明了「Review Gate 裁决 2026-11-28」。:480 末尾多一句说明 7.1、7.4 两处请求由本条答复，属于第 17 节的记录。正文 :209、:235 未改，符合「不改协议」。
- C1：一致。:378、:390、:400、:412、:415、:443 都写明 H = 9、ST7 = 9、ST11 界限 = 0.875 × 9 = 7.875，并注明 Owner 批准 2026-11-28 12:13:25 UTC。DOSE_SPACE.json:193-195 已同步。
- C2：一致。:211-213、:222-223、:444、:447 改为 MMLU @ c30699e8356da336a370243923dbaf21066bb9fe；ARC 标为「未采用的备选」。DAMAGE_MANIFEST.json:64-66、:79、:107 与 DATA_MANIFEST.json:75、:333-340 已同步。ARC 的核实记录与参考哈希都保留了（DAMAGE_MANIFEST.json:106-147、DATA_MANIFEST.json:336-340）。:214 有一句「撰写时 MMLU 与 ARC 的 DEV 抽样中都是 0 题」没有加标注，但它本身就是核实记录，可以接受。
- C3：一致。:445 与 DOSE_SPACE.json:219-220 写明主方案：每种方法 1 个配置、10 个剂量点、3 个种子。
- C4/D1：部分一致。以下各项已核对一致：
  - 状态行 :6 为 PROTOCOL_FROZEN，并写明冻结条件。
  - 四个 JSON 的 version 为 v1、status 为 PROTOCOL_FROZEN，frozen 字段四份相同（diff:54-61、:134-141、:207-214、:503-510）。
  - PROPOSED 已全部改为冻结值：Grep 全文只剩 :10 的说明文字，改动处为 :31、:123、:158、:216、:237、:351。
  - build_manifests.py 已同步。
  - 全部改动在一个提交内（diff:30-39）。

  唯一的缺口：逐字节相同的证明是对暂存树 69ff2c43 做的，不是对冻结提交本身（见问题 1）。
- B：部分一致。按字面清单，以下改动超出了「A1–A5 的句子及其同步项、C 的定值、第 17 节的记录」：
  - 标题去掉「(草案)」；
  - A3 之后的一句；
  - 指令未列出的几个 JSON 同步字段；
  - 键名与结构的改动；
  - 第 15 节标题与表头的改写；
  - 文件头「待决字段」一行；
  - build_manifests.py 的 docstring。

  逐项看，它们都是同义的一致性同步，没有加入 A、C 以外的新规则，并且都记入了第 17 节（:463-471）。DEFERRED_MINORS 中的其它条目没有被顺带修改，抽查了 V2-10、V2-11、V2-14、V2-17。

问题清单
MAJOR | /home/user/OpenMythos/metrix/e1-v1/reports/freeze/rebuild_check.txt:1,5-6,15-19 | D1 要求证明重新生成的四个 JSON 与入库的逐字节相同，但比对的是暂存树 69ff2c43，不是冻结提交 9a19e70e。两者之间的联系只有作者的一句说明，我也无法把这里的四个 sha256 与 9a19e70e 的 blob（/home/user/OpenMythos/metrix/e1-v1/reviews/9a19e70e1bc16130368caa00bd1bf6fbc126bc8c/tree_round1.txt:1-3,5：624d4f6…、6276314…、cf07ace…、158145c…）对上『未验证』 | "# Rebuild check on the staged tree 69ff2c43 of the freeze commit ..., run before the reports/freeze/ files were added; adding them changes no JSON blob." 以及 "$ git rev-parse 69ff2c43b2b0fa9c5ea76ee25bcfe44835006533" | 不需要改冻结提交。以 data-auditor 本轮对 9a19e70e 四个 JSON 字节 sha256 的独立复算为准，须分别等于 2a35d40c7192b4f8df2dfa765714340009070d9b3e4b750cee994ae78c3e6767、667943a503204d689dc7baef48583652b6947ad62694825995ac6a0d9d64a40b、44923d80614d780a010cd9742689e2fccdc949b4144b221a8de6469e898a7bc2、5a05e5e7ffef7829328f2edbed2c15d4a52f2d99c4052cf30ef57a4a672588cd；或在 D4 报告中附上 `bash metrix/e1-v1/reports/freeze/rebuild_check.sh 9a19e70e1bc16130368caa00bd1bf6fbc126bc8c` 的原始输出（脚本接受任意 tree-ish）。任一不等即升为 BLOCKER
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:1 | 标题去掉「(草案)」，不在 B 的字面清单内 | "# METRIX · E1-V1 · PROTOCOL v1" | 与 D1 的「版本字段同步」（JSON v1-draft → v1）同义；保留「草案」反而会与状态行 :6 矛盾；已记入 :471。登记，请 Review Gate 知悉
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:247 | A3 替换句之后的一句（「任一不满足 → ST14」及原因括注）也改了，超出 A3 的字面范围 | "Gate D 不通过(上述通过条件任一不满足)→ ST14 ... G-D2 或 G-D3 中关于 D1 的条件不满足时写明失败的条件编号" | 原句的「任一不满足」指 G-D1 至 G-D4 任一，保留会与 A3「D2 条件不满足时 Gate D 仍可通过」直接矛盾。改后语义与 A3 一致，没有新规则，已记入 :465。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/DAMAGE_MANIFEST.json:182; /home/user/OpenMythos/metrix/e1-v1/DATA_MANIFEST.json:383; /home/user/OpenMythos/metrix/e1-v1/DOSE_SPACE.json:220 | A2、A3、A5 的同步扩展到了指令未列出的 JSON 字段 | 旧值 "per seed: reloaded state_sha256 == N's"（diff:99）、"reduce per section 12 R1-R4 if the estimate exceeds what the Owner accepts"（diff:244） | 不同步，冻结的 manifest 就会与正文矛盾；新文字与 A2、A3、A5 同义。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/DATA_MANIFEST.json:333-340; /home/user/OpenMythos/metrix/e1-v1/DAMAGE_MANIFEST.json:63-66 | 改了键名与结构：reference_canonical_sha256 由 {mmlu, arc} 对象改为字符串，ARC 移入 not_adopted_alternative；删除 preferred，alternative 改名为 alternative_not_adopted | "reference_canonical_sha256": "f40c146a…88be"；"alternative_not_adopted": "arc" | 这与冻结前第 15 节末句「Owner 批准第 2 项之后,`DAMAGE_MANIFEST.json: d2.selected` 改为所选数据集,`d2_dev.jsonl` 的参考哈希为第 7.2 节对应的值」（diff:463）一致，也使 canonical_check 成为单值比较；ARC 哈希仍保留。副作用：撰写阶段入库的审查脚本按旧结构取 ["mmlu"]、["arc"]，在冻结提交上重跑会抛 TypeError，涉及 /home/user/OpenMythos/metrix/e1-v1/audit/a5_damage.py:181,217、/home/user/OpenMythos/metrix/e1-v1/audit/a6_consistency.py:152-153,165-166、/home/user/OpenMythos/metrix/e1-v1/audit/r2_item1_fixes.py:244-245『未验证』。这些脚本的 stdout 已入库，结论不受影响。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:134,249 | A2 只替换了「因此……」半句。前提「参数逐位不变」在 :134 与 :249 仍保留，与 :464 记录的 A2 原因（AdamW 可能把 −0.0 变为 +0.0，原始字节不同）相互矛盾 | :134 "AdamW 的更新量与 weight decay 项都乘以 learning rate,参数逐位不变,因此 Z0 的每个参数张量必须与 N 数值相等(G-D1)"；:249 "learning rate 为 0 时参数逐位不变" | 按 B 不改；判定以 G-D1 条文 :241 为准，不影响执行。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/DAMAGE_MANIFEST.json:219 | comparison.secondary 没有写 D2_NOT_QUALIFIED 的例外，同一对象的 words（:220）写了 | "words only for method comparisons on D1-all, D1-diff, D1-same, D2, marked secondary" | 以 words 与正文 :303 为准。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:404 | A5 已声明 R1–R4 不属于冻结协议，但 ST11 一段的末尾仍有缩减方案的代入规则 | "采用缩减方案时,按该方案的计数代入同一公式。" | 两者不矛盾（新版本可以沿用这个公式），只是在冻结协议内已没有可执行的对象；A5 明言 ST11 公式不改，按 B 不改。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:209,235 | 冻结正文中仍留着两处开放请求，答复只写在第 17 节 :480 | "请 Review Gate 确认这一解释"；"是否把主比较改为只用 books 与 wikitext,请 Review Gate 决定" | 与 A6「不改协议」一致；读者须结合第 17 节阅读。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:463-464 | A1、A2 的「原因」一栏写作「Review Gate 裁决 2026-11-28: …」，但指令 A1、A2 本身没有给原因。所写原因取自 /home/user/OpenMythos/metrix/e1-v1/reports/DEFERRED_MINORS.md:46,48（V2-1、V2-3；V2-3 自标「未验证」） | :464 "Review Gate 裁决 2026-11-28:learning rate 为 0 时 AdamW 可能把 −0.0 的参数变为 +0.0" | 今后写明出处为 V2-1、V2-3。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:465 | A3 改变了 Task Order 7.5 对阳性对照的要求，第 17 节没有注明这是对 Task Order 的偏离 | /home/user/OpenMythos/metrix/e1-v1/tasks/E1V1_PROTOCOL_TASK_ORDER_V1.md:113 "其 D1、D2 必须超过冻结的下限。阳性对照不过，说明尺子量不出损伤，Gate M 不进行。" | 这是 Review Gate 的裁决、Owner 已批准，本身不是问题；为便于追溯，建议在 FREEZE_REPORT 中注明。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:452 | 第 16 节要求 PROTOCOL_FROZEN 等批准写入 approvals/<序号>_<事件>.md，并记 JST 与 UTC；本次冻结批准按 Owner 消息记在 tasks/ 下，只有 UTC | /home/user/OpenMythos/metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md:3,16 | Owner 的指令优先，而且记录已先行提交（证据提交 78e79e4），但冻结协议自己的规则对它自身的冻结没有逐字满足。请 Review Gate 确认第 16 节从冻结之后的批准开始适用。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/reports/freeze/rebuild_check.sh:8,10,13 | 输出里打印的「$ 命令」与实际执行的命令不完全相同 | `echo "\$ date -u"; date -u +%Y-%m-%dT%H:%M:%SZ`；打印 `tar -x -C <tmp>` 占位；rm 打印为花括号写法 | 原始输出应逐字反映实际执行的命令。登记
MINOR | /home/user/OpenMythos/metrix/e1-v1/reports/freeze/hash_invariance.py:11-13 | 按集合比较，只能证明十六进制串的集合不变，发现不了某个哈希被移到另一个字段 | `A, B = set(rx.findall(a)), set(rx.findall(b))` | 我已按 diff 逐处核对改动行里的哈希：MMLU、ARC 参考哈希仍在各自对应的字段（diff:161-169）；第 15 节只是把缩写换成全值（diff:457-460），没有发现移位。登记

BLOCKER：无。没有代码路径生成、读取或评测 TEST，build_manifests.py 只读取 Pilot 的两个 manifest（build_manifests.py:19-20）。数据哈希与 revision 在改动行中没有变化（按 diff 逐处核对）。冻结后的规则文字与 A、C 逐条相符。

结论：PASS
