# FREEZE REPORT · METRIX-E1-V1 protocol v1

| 项 | 值 |
|---|---|
| 指令 | `metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md`(Review Gate 裁决与 Owner 的冻结指令,原文;收到时间 2026-11-28 12:13:25 UTC,即本会话第一条命令 `date -u` 的输出) |
| 状态 | **PROTOCOL_FROZEN**(C4 的条件已满足:A、C 完成,冻结提交的审查无 BLOCKER) |
| 冻结提交 | `9a19e70e1bc16130368caa00bd1bf6fbc126bc8c` |
| 冻结记录 | `metrix/e1-v1/PROTOCOL_FROZEN`(提交 `e97ce77e415e72d7d29a26f16132cd9b725cbf6e`;文件 sha256 `b2bce28552650f20bb0f35c164aa6416436db419ca319414a2e1379fd40f80c4`) |
| 标签 | `metrix-e1-v1-frozen` 应指向冻结提交,**由 Owner 推送**;Executor 没有创建或推送任何标签(写本报告时 `git ls-remote origin refs/tags/metrix-e1-v1-frozen` 输出为空) |
| 分支 | `metrix-e1-v1-protocol-v1`,起点 `bc03348ad8b2390ac3df452631d63b8bfe66ad67`(与指令所写相同);只做普通推送,没有 force push,没有 PR |
| 运行环境 | Claude Code 云端容器(CPU only,没有 GPU)。系统 Python 3.13.18 没有 torch;Executor 在会话临时目录建了只含分词器相关库的 venv(transformers 5.22.2、tokenizers 0.23.3、huggingface-hub 2.4.0、pyarrow 26.0.1,没有 torch),只供 data-auditor 使用 |
| 本轮没有做的事 | 没有训练、评测、加载模型权重、使用 GPU;没有生成、实例化或读取任何 TEST(事实 QA 与损伤评测都包括在内);没有开始实现 |
| 本报告 | 不另送审查(指令 D4) |

路径约定:下文路径相对于 `metrix/e1-v1/`(另注明者除外)。

## 1. 结果

- 冻结提交:`9a19e70e1bc16130368caa00bd1bf6fbc126bc8c`(没有 BLOCKER,所以没有修复提交)。
- `PROTOCOL_FROZEN` 中冻结提交下的文件字节 SHA-256(`git cat-file blob 9a19e70e…:<路径> | sha256sum`):

```
df710d1c7ccf3acba4b2ae25df0a0c5f8a07d3cd8d1c02f3de65eae3c40a504e  metrix/e1-v1/METRIX_E1V1_PROTOCOL.md
2a35d40c7192b4f8df2dfa765714340009070d9b3e4b750cee994ae78c3e6767  metrix/e1-v1/DATA_MANIFEST.json
667943a503204d689dc7baef48583652b6947ad62694825995ac6a0d9d64a40b  metrix/e1-v1/SPLIT_MANIFEST.json
44923d80614d780a010cd9742689e2fccdc949b4144b221a8de6469e898a7bc2  metrix/e1-v1/DOSE_SPACE.json
5a05e5e7ffef7829328f2edbed2c15d4a52f2d99c4052cf30ef57a4a672588cd  metrix/e1-v1/DAMAGE_MANIFEST.json
```

  data-auditor 独立复算的值相同(`audit/stdout/f1_a_bytes_freeze.txt`)。
- 审查(各 1 轮):code-reviewer **PASS**,无 BLOCKER(1 个 MAJOR、13 个 MINOR);data-auditor **PASS**,无 BLOCKER(只作参考,信任状态“待验证”)。
- 登记未修:**15 条**(`reports/DEFERRED_MINORS.md` 第 4 节 F-1 至 F-15:code-reviewer 1 个 MAJOR、13 个 MINOR,data-auditor 1 条观察)。

## 2. 提交(本轮共 4 个,上限 5 个)

| # | 提交 | 内容 | 审查 | 推送记录 |
|---|---|---|---|---|
| 1 | `78e79e4390aa9e465127ca52b57928714abdb633` | 证据提交:只含 `tasks/E1V1_FREEZE_OWNER_MESSAGE.md`(消息原文与收到时间);在其余任何动作之前提交并推送(Task Order 第 13 节第 2 条) | 不审查(记录) | `reports/pushes/push_owner_message_commit.txt` |
| 2 | `9a19e70e1bc16130368caa00bd1bf6fbc126bc8c` | **冻结提交**(D1):协议、四个 JSON、`reports/authoring/build_manifests.py`、`reports/freeze/` 的重建证明 | code-reviewer、data-auditor 各 1 轮 | `reports/pushes/push_freeze_commit.txt` |
| 3 | `e97ce77e415e72d7d29a26f16132cd9b725cbf6e` | `PROTOCOL_FROZEN`(D3),只含这一个路径 | 不审查(记录) | `reports/pushes/push_protocol_frozen_commit.txt` |
| 4 | 本报告提交 | 本报告;`reviews/9a19e70e…/` 的审查原文与转录;`audit/f1_*.py` 与 `audit/stdout/*_freeze.txt`;`reports/freeze/` 的补充证据与生成脚本;`reports/DEFERRED_MINORS.md` 第 4 节;前三个提交的推送记录 | 不审查(D4) | 见回复 |

`git diff --name-only bc03348ad8b2390ac3df452631d63b8bfe66ad67 HEAD -- . ':(exclude)metrix/e1-v1'` 的输出为空:`metrix/e1-v1/` 以外没有改动。

## 3. 第 0 步

`reports/freeze/step0_compare.txt`:两个 agent 文件在仓库与 `~/.claude/agents/` 中逐字节相同,tools 行与已加载定义一致(`reviews/9a19e70e…/preflight_tools_check.txt`)。`~/.claude/CLAUDE.md` 与分支上的 `metrix/CLAUDE.md` 不同:副本仍是 E1 Pilot PROTOCOL_FROZEN(v1.1)时的状态句,也没有第 8 节 2026-11-28 的条目(与撰写阶段 `SUBMISSION_NOTE.md` 第 4 节第 9 项所记相同)。以分支上的文件为准。两次审查调用的第一句都按 `metrix/CLAUDE.md` 第 5 节第 6 条固定(`reviews/9a19e70e…/*_prompt.txt`)。

## 4. A、C 的执行(全部记入协议第 17 节)

| 项 | 改动 | Executor 自行判断之处 |
|---|---|---|
| A1 | 第 0 节:B24 从“照原文适用”的列表中移出,另写“B24:只适用其中 T1–T3 的原因词与 T3 的读法；最终状态按本协议第 9.7 节。” | 指令说“适用表中 B24 一行”,但该处是一段列表,不是逐行的表 |
| A2 | 第 7.5 节 G-D1、第 4 节 Z0 理由按指令原文替换;同步 `DOSE_SPACE.json: controls.Z0.expectation` | 另同步 `DAMAGE_MANIFEST.json: gate_d.G-D1.rule` 与 `DATA_MANIFEST.json: reported_values` 的 Gate D 一项(不同步就与正文矛盾);第 4 节“参数逐位不变”与第 7.5 节理由中的同类说法按 B 未改(F-6) |
| A3 | 第 7.5 节“Gate D 通过”一句按原文替换;第 9.4 节结论词汇的适用范围、第 9.6 节新增 `D2_NOT_QUALIFIED`;`DAMAGE_MANIFEST.json`(`gate_d.pass`、`gate_d.D2_NOT_QUALIFIED`、`comparison.words`) | 紧接的下一句“任一不满足 → ST14…”与原因括注同步改为只针对通过条件(原句与 A3 直接矛盾,F-3);`reported_values` 的 Gate D 一项加 D2 的合格状态。**A3 改变了 Task Order 7.5 对阳性对照的要求**(原文“其 D1、D2 必须超过冻结的下限。阳性对照不过,说明尺子量不出损伤,Gate M 不进行”):现在只有 D1 的阳性对照阻止 Gate M,这是 Review Gate 的裁决、Owner 已批准(F-11) |
| A4 | 第 1 节 Non-claims 末尾追加指令原文;所引数值已核对(`reports/freeze/a4_dnll_check.txt`:S 0.9819–1.5216,Y 1.4576–2.1450) | `reported_values` 原来只在“every training run: per dose point”一项中隐含 F 在 d0 的值,S、Y 不是剂量曲线,也没有“并列报告”的一项,所以补上一项(`results/gate0_record.json: d0_damage`:D1-all、D1-diff、D1-same、四个逐领域值与 D2,DEV,每个种子与 seed-average) |
| A5 | 第 12 节缩减方案表之前加指令原文的一句;ST11 公式不改 | — |
| A6 | 七项确认按指令原文记入第 17 节“Review Gate 的确认”;正文不改 | 第 7.1 节“请 Review Gate 确认这一解释”与第 7.4 节“请 Review Gate 决定”按“不改协议”保留,在第 17 节注明由 A6 答复(F-9) |
| C1 | H = 9 小时;ST7 = 9 小时;ST11 界限 = 0.875 × 9 = 7.875 小时:第 12 节、第 13 节 ST7 与 ST11、第 15 节;`DOSE_SPACE.json: training_contract.gpu_hours_limit = 9` | — |
| C2 | D2 = MMLU(`cais/mmlu` @ `c30699e8356da336a370243923dbaf21066bb9fe`):第 7.1、7.2、15 节;ARC 标为“未采用的备选”,核实记录与参考哈希保留 | JSON 结构:`DAMAGE_MANIFEST.json: d2` 的 `preferred` / `alternative` 改为 `selected` = `mmlu` 与 `alternative_not_adopted`;`DATA_MANIFEST.json: files["d2_dev.jsonl"].reference_canonical_sha256` 由 `{mmlu, arc}` 改为 MMLU 的值,ARC 的值移入 `not_adopted_alternative`(F-5) |
| C3 | 主方案(每种方法 1 个配置、10 个剂量点、3 个种子):第 15 节;`DOSE_SPACE.json` 的 `pending` 改为 `owner_decisions` | — |
| C4 / D1 | 状态行 PROTOCOL_FROZEN(写明 C4 的条件);全部 PROPOSED 改为冻结值(第 0 节种子、第 4 节表头、第 6.3、7.2、7.5、11 节标题);文件头“待决字段”为“无”;第 15 节改为“原待决字段的冻结值”;四个 JSON 的 `version` v1-draft → v1、`status` → PROTOCOL_FROZEN、`frozen` 由 null 改为批准记录 | 标题去掉“(草案)”(与 JSON 版本同步;F-2) |

Owner 消息只给了 UTC 时间;对应的 JST 为 2026-11-28 21:13:25。

## 5. 冻结提交的证明

- **重新生成逐字节相同**(D1):`reports/freeze/rebuild_check.txt`(冻结提交内,对暂存树 `69ff2c43`)与 `reports/freeze/rebuild_check_freeze_commit.txt`(对冻结提交本身;回应 code-reviewer 的 MAJOR F-1)。两次都是导出树、删除四个 JSON、运行 `build_manifests.py`、与提交中的 blob 用 `cmp` 比较:四个文件都是 `IDENTICAL`。暂存树与冻结提交中协议、四个 JSON 与 `build_manifests.py` 的 blob id 相同;两者只差 `reports/freeze/` 的三个文件。
- **数据哈希与 bc03348a 时相同**:Executor 的 `hash_invariance.py` 按集合比较,协议与四个 JSON 中的 40 / 64 位十六进制串集合与 bc03348a 相同。data-auditor 按字段路径逐个比较:79 个字段(65 个 64 位、14 个 40 位)全部相同,两个方向的差集为空(`audit/stdout/f1_d_compare_freeze.txt`)。
- **数据与输入的独立复算**(data-auditor):12 个从 Hugging Face 按固定 revision 下载的输入文件与 `eval_sets.jsonl` 的 sha256 全部等于 manifest 的值(`f1_b_inputs_freeze.txt`);独立重新生成的非 TEST 数据与内容哈希 14 项全部等于参考值(`f1_c_regen_freeze.txt`,含 MMLU 与 ARC 的 `d2_dev`)。
- **`PROTOCOL_FROZEN`**:由 `reports/freeze/make_protocol_frozen.py` 只从 git 对象生成;用入库的脚本重新生成与提交的文件逐字节相同;其中 32 个不同的 64 位值都出现在 data-auditor 的 stdout 中(`reports/freeze/make_protocol_frozen.txt`)。

## 6. 审查

| 审查 | 轮数 | 结论 | 原文 | 其它记录 |
|---|---|---|---|---|
| code-reviewer | 1 | PASS;无 BLOCKER;A1–A6、C1–C3 一致,C4/D1 与 B“部分一致”(见下) | `reviews/9a19e70e1bc16130368caa00bd1bf6fbc126bc8c/code-reviewer_round1.md` | 调用文字、转录、启动时间、输入 diff、tree、提取日志在同一目录 |
| data-auditor | 1 | PASS;无 BLOCKER(只作参考,`metrix/CLAUDE.md` 第 10 节) | `reviews/9a19e70e1bc16130368caa00bd1bf6fbc126bc8c/data-auditor_round1.md` | 脚本 `audit/f1_a_bytes.py`、`f1_b_inputs.py`、`f1_c_regen.py`、`f1_d_compare.py`、`f1_lib.py`;完整 stdout `audit/stdout/*_freeze.txt`(含两份第一次运行的输出) |

code-reviewer 的“部分一致”:C4/D1 一项指重建证明是对暂存树做的(F-1,已附对冻结提交本身的输出,冻结提交不改);B 一项指标题、A3 之后的一句、JSON 的同步字段与键名、第 15 节标题与表头、文件头“待决字段”一行、`build_manifests.py` 的 docstring 超出 B 的字面清单,审查认为都是同义的一致性同步,没有加入 A、C 以外的规则。两次审查同时在后台运行;code-reviewer 看到了 data-auditor 的临时目录 `audit/tmp_freeze/`,没有读取其内容。

## 7. 事件与偏差(如实列出)

1. 冻结提交的重建证明最初只对暂存树做(F-1);报告提交补了对冻结提交本身的检查,冻结提交未改。
2. data-auditor 的两个脚本第一次运行出错(脚本本身的错误:拿非 LFS 文件的 git blob sha1 与 sha256 比较,拿 manifest 中没有的行数作比较;以及 venv 没有 jinja2,`apply_chat_template` 无法运行)。两次输出都已入库;第一次运行时 12 个文件的 sha256 已全部相同。`context_ids_mean` 本轮没有复算(F-15)。venv 是 Executor 建的,没有装 jinja2。
3. data-auditor 下载的文件与生成的非 TEST 数据(`audit/tmp_freeze/`,约 115 MB,其中有 MMLU 与 ARC 的 test parquet 原文件,只求过整个文件的 sha256 并读了文件尾的行数)已从仓库移到会话临时目录,没有入库。按 data-auditor 的报告与该目录的文件清单,没有生成任何 TEST 文件。
4. 撰写阶段的 audit 脚本按旧的 JSON 结构取 `d2_dev` 的参考哈希,在冻结提交上重跑会出错(F-5,未验证);它们的 stdout 已入库,结论不受影响。
5. 第 16 节规定批准记在 `approvals/`、写 JST 与 UTC;本次冻结批准按 Owner 消息记在 `tasks/E1V1_FREEZE_OWNER_MESSAGE.md`,只有 UTC(F-12)。

## 8. 待 Review Gate / Owner

- Owner:推送标签 `metrix-e1-v1-frozen`,指向 `9a19e70e1bc16130368caa00bd1bf6fbc126bc8c`。
- Review Gate 确认或知悉:F-12(第 16 节是否从冻结之后的批准开始适用);F-2(标题去掉“(草案)”)。
- 本轮登记的其余条目(F-1、F-3 至 F-11、F-13 至 F-15)按指令只登记。之后的任何协议改动都需要 Owner 批准的新版本(协议第 16 节)。
- 下一步是 Implementation Task Order(其中包括 V1-22 所说的两个 agent 定义的更新)。本轮没有开始实现,没有训练或评测。
