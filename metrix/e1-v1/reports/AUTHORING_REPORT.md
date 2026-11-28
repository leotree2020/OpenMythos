# E1-V1 协议撰写报告(METRIX-E1-V1-PROTOCOL-AUTHORING-V1.0)

| 项 | 值 |
|---|---|
| 状态 | **AWAITING_REVIEW_GATE**(协议未冻结) |
| 指令 | `tasks/E1V1_AUTHORING_OWNER_MESSAGE.md`、`tasks/E1V1_PROTOCOL_TASK_ORDER_V1.md`(原文) |
| 运行环境 | Claude Code 云容器,主机名 `vm`,只有 CPU、没有 GPU;venv 中没有 torch(不可能加载模型权重)。没有训练、没有模型评测、没有使用 GPU;没有生成、实例化或读取任何 V1 的 TEST 样本 |
| 本报告提交 | 不另送审查(Owner 的修改次数上限);只含本文件、`reports/DEFERRED_MINORS.md`、`reports/authoring/arc_dev_choice_counts.txt`、`reports/pushes/push_evidence_commit.txt` |

路径相对于 `metrix/e1-v1/`(另注明者除外)。

## 1. A 部分:Pilot 报告勘误

| 项 | 值 |
|---|---|
| 起点核对 | `metrix-e1-pilot-protocol-v1` 的最新提交为 `4535fd0985b03f6fcaf3e5f600726bfbaaef3816`(与指令相同) |
| 勘误提交(A6) | **`6e03468956208c422d0d41c08edaaf116166338c`**,一个纯文档提交:A1–A5 的改动、code-reviewer 的审查记录(`metrix/e1-pilot/reviews/tree-c20acf5690579241c76100f2a7363b1cda103041/`)与登记(`metrix/e1-pilot/reports/DEFERRED_MINORS.md` 1.45 节、第 3 节末条) |
| 审查 | code-reviewer 1 轮,结论 PASS(没有 BLOCKER;2 个 MAJOR,均标为不确定;8 个 MINOR),全部登记为 PE1–PE10,未修改 |
| 推送 | 快进 `4535fd0..6e03468`,不推送标签;两个冻结标签不变(`reports/pilot_erratum/push_erratum_commit.txt`)。此后没有再向该分支推送 |
| Executor 附加的一句 | 报告第 14 行“表格的生成方式”末尾的“例外”一句不在 A1–A5 的字面之内,用来使该段在 A1 之后仍然成立(PE10,请 Review Gate 事后确认) |

## 2. B 部分:提交

起点 `6e03468956208c422d0d41c08edaaf116166338c`,分支 `metrix-e1-v1-protocol-v1`(新建;只做普通推送,没有 force push,没有推送标签,没有 PR)。共 4 个提交(上限 6):

| # | 提交 | 内容 |
|---|---|---|
| 1 工作提交 | `59761ad923674d43725167a8c79f6bdf16f531ee` | 协议与 5 个配套文件、两份指令原文、撰写脚本与原始输出、A 部分推送记录;即第 1 轮审查的暂存树 `0e3dc49e`,原样提交 |
| 2 修复提交 | `266b64b7d8af07064b94de61b75f87723ad2d167` | 第 1 轮的修复;第 1 轮审查记录与 data-auditor 的脚本、完整 stdout;即第 2 轮审查的暂存树 `f395c476`,原样提交 |
| 3 证据提交 | `6b9b98df515cae135fa501c947b812920214ada4` | 第 2 轮审查记录、data-auditor 第 2 轮的脚本与完整 stdout、前两次推送记录;没有改动任何交付物 |
| 4 报告提交 | 本提交(hash 见最终回复) | 本报告与登记 |

推送记录:`reports/pushes/push_work_commit.txt`(新分支 `59761ad`)、`push_fix_commit.txt`(`59761ad..266b64b`)、`push_evidence_commit.txt`(`266b64b..6b9b98d`)。

## 3. 审查

两次调用的第一句都按 `metrix/CLAUDE.md` 第 5 节第 6 条固定;调用前比对了仓库与 `~/.claude/` 下两个 agent 文件的 tools 行与已加载定义,一致(各轮的 `preflight_tools_check.txt`)。

| 轮 | 对象 | code-reviewer | data-auditor(“待验证”,只作参考) | 记录 |
|---|---|---|---|---|
| 1 | 暂存树 `0e3dc49e`(= 工作提交) | BLOCK:1 BLOCKER、13 MAJOR(每个都标为影响六类之一)、18 MINOR | BLOCK:B1(协议中两个 ARC 描述数字);哈希与规则独立复现;观察 M1–M8 | `reviews/tree-0e3dc49eaca9b07254e61301bc2602f8d8a39eea/`;`audit/*.py`、`audit/stdout/*.txt` |
| 2(最后一轮) | 暂存树 `f395c476`(= 修复提交) | PASS:第 1 轮 BLOCKER 与 13 个 MAJOR 逐条“已解决”(M1 引入一处新矛盾,M10 “部分解决”);新提 4 MAJOR、15 MINOR | PASS:B1、M2–M4 已解决;观察 N1–N5 | `reviews/tree-f395c476606603e65d336e1ba3ac34a065c40889/`;`audit/r2_*.py`、`audit/stdout/*_round2*.txt` |

**两份审查各用的轮数**:code-reviewer 2 轮,data-auditor 2 轮(A 部分另有 code-reviewer 1 轮)。

审查 subagent 的路径对应:code-reviewer 以 V1 协议、Task Order 与 Pilot 协议为依据;data-auditor 只写入 `metrix/e1-v1/audit/`(其定义写的是 `metrix/e1-pilot/audit/`);审查原文存到 `metrix/e1-v1/reviews/`(`metrix/CLAUDE.md` 第 5 节第 5 条写的是 `metrix/e1-pilot/reviews/`)。data-auditor 两轮都接受这一对应,并把它列为交 Review Gate 的事项。data-auditor 两轮写出的临时数据(生成的非 TEST 数据)都已移到会话临时目录,未入库。

## 4. 第 1 轮的修复(修复提交 `266b64b7`)

按 Owner 的规则,只修 BLOCKER 与影响数据、指标、门槛、可复现性、iso-acquisition 匹配或损伤测量的 MAJOR;其余登记。

| 审查项 | 修改 |
|---|---|
| R1-CR BLOCKER(第 7.6 节无来源的 margin 估计,红线 7) | 删去;G-D2 上界的规划估计改为写明来源文件与字段,脚本与输出入库(`reports/authoring/sigma_planning.*`) |
| R1-CR MAJOR 1(Pilot 解释的适用范围) | 第 0 节新增 B1–B25 的逐条适用表 |
| R1-CR MAJOR 2(ST11 无可执行公式) | 第 12 节写出完整公式,逐项标明实测量与固定常数;`compute_estimate.py` 打印两个比值 |
| R1-CR MAJOR 3(ST1、ST9、ST12 与 V1 不符;manifest 占位字段) | 第 13 节逐条写出 V1 版;manifest 在执行中不改写,删去占位字段,ST12 无豁免 |
| R1-CR MAJOR 4(Gate 0 不通过后是否跑 L、A) | 新增 ST19 |
| R1-CR MAJOR 5(边界比较的浮点误判) | 第 6.4 节第 2a 条:精确有理数算术 |
| R1-CR MAJOR 6(TEST 来源读取规则自相矛盾) | 第 0 节与 `DAMAGE_MANIFEST.json` 改为与 Pilot 第 3 节一致,写出行首正则 |
| R1-CR MAJOR 7(c4 为近分布) | 第 7.4 节说明;逐领域指标作为次要比较报告;主比较是否只用 books、wikitext 交 Review Gate |
| R1-CR MAJOR 8(margin 理由) | 第 7.6 节改写为预先登记的效应量,说明与 Pilot +0.03 的关系 |
| R1-CR MAJOR 9(结论词的 m) | 第 9.4 节改为 m(M);X 相对 N 与逐领域指标不给结论词 |
| R1-CR MAJOR 10(G-D2 不可能不通过) | 加上界;说明 Z0 只证明流程不引入波动,训练种子波动的处理方式 |
| R1-CR MAJOR 11(剂量换算口径) | 第 6.3 节写明按遍换算及理由,给出按步换算的结果;τ_DEV 的理由不再依赖跳变预测 |
| R1-CR MAJOR 12(D2 字母打分是一种解释) | 第 7.1 节写明解释与理由;列入 `SUBMISSION_NOTE.md` 第 5 节 |
| R1-CR MAJOR 13(若干 PROPOSED 值无理由) | 补 Z0 的 2 遍、d0、D2 指令、ST18 的理由 |
| R1-DA B1(ARC 的 6 / 863) | 改为 7 / 862(第 7.1、15 节;同时解决 R1-CR m5) |
| R1-DA M2、M3、M4(L8 的“文本”;L6/L8 TEST 部分按集合计数;记录字段定义) | `SPLIT_MANIFEST.json` 与 `DATA_MANIFEST.json` 写明 |

## 5. 每个文件被修改的轮数

“修改轮数”= 文件首次写成之后被修改的次数(修改只发生在第 1 轮之后的修复中;第 2 轮之后没有修改任何交付物)。

| 文件 | 修改轮数 |
|---|---|
| `METRIX_E1V1_PROTOCOL.md` | 1 |
| `DATA_MANIFEST.json` | 1 |
| `SPLIT_MANIFEST.json` | 1 |
| `DOSE_SPACE.json` | 1 |
| `DAMAGE_MANIFEST.json` | 1 |
| `SUBMISSION_NOTE.md` | 1 |
| `reports/authoring/build_manifests.py` | 1 |
| `reports/authoring/compute_estimate.py` 与 `compute_estimate.txt`(重新生成) | 1 |
| `reports/authoring/sigma_planning.py` 与 `sigma_planning.txt` | 0(在修复提交中新建) |
| `reports/authoring/v1_data_check.py` 与其三个输出、`d2_dataset_metadata.txt` | 0 |
| `tasks/` 两份原文 | 0 |
| A 部分:`metrix/e1-pilot/reports/PILOT_FINAL_REPORT.md`、`metrix/CLAUDE.md` | 0(一个文档提交写成,审查后没有修改) |

## 6. 登记未修的条目数

| 范围 | 条目数 | 位置 |
|---|---|---|
| A 部分(勘误提交的审查) | 10(PE1–PE10) | `metrix/e1-pilot/reports/DEFERRED_MINORS.md` 1.45 节 |
| B 部分第 1 轮 | 21 | `reports/DEFERRED_MINORS.md` 第 1 节(另有 2 条标为已修正) |
| B 部分第 2 轮 | 24(其中 MAJOR 4 条) | 同上第 2 节 |
| B 部分合计 | 45 | 同上第 3 节 |

## 7. 待 Review Gate / Owner 决定

1. 第 15 节三项待决(Owner):GPU 累计时间上限 H(建议 9 小时);D2 数据集(建议 MMLU,备选 ARC);剂量点与配置的数量(主方案与 R1–R4)。
2. 第 2 轮 code-reviewer 的 4 个 MAJOR(第 2 轮之后按 Owner 规则不修):V2-1 B24 与第 9.7 节的最终状态规则冲突;V2-2 缩减方案下 ST11 的比值与计数;V2-3 learning rate 为 0 时带符号零可能使 Z0 的 `state_sha256` 与 N 不同(G-D1 会误判;实现前须决定改用逐张量数值相等);V2-4 训练种子波动的阴性对照。
3. `SUBMISSION_NOTE.md` 第 4 节第 1、5、8 项与第 5 节列出的解释(D2 字母打分、c4、G-D2 上界)。
4. `reports/DEFERRED_MINORS.md` 中的 V1-18、V1-22、V2-22、V2-24。
5. A 部分的 PE1、PE7、PE10。
