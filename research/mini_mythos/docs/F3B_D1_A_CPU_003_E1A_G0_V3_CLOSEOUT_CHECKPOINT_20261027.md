# F3B-D1-A-CPU-003 E1-A — 检查点：G0 V3 独立审核收口 G0-V3-REVIEW-CLOSEOUT-001

**状态：`G0 V3 FREEZE PASS / SEMANTIC CLOSEOUT OPEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED / GROK REVIEW PENDING`**（另：BV NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED）

任务：`F3B-D1-A-CPU-003-E1A-G0-V3-REVIEW-CLOSEOUT-001`。审核基准 `b4ca97daa303269ebe7b268f4bb00c6601723a6d`。
「G0 V3 FREEZE PASS」是 ChatGPT 对 V3 冻结提交与范围合规的结论（经项目负责人转述）。
**没有修改** V1/V2/V3，**没有创建 V4**，没有修改 `g0_run.py` / `g0_judge.py` / `g0_auth.py` / `bench/` / 既有测试；**没有运行**任何测试、真实 G0、BV、E1-A，没有启动受测进程，没有创建授权文件。所有追踪都是通读 V3 文本与源码的**静态推导（设计审核），不是测试结果**。

## 1. 结论（详见 `a_predicate_003/g0_preflight_review/G0_V3_CLOSEOUT_REVIEW.md`）

| 问题 | 结论 | 需要 V4？ |
|---|---|---|
| **F-20** `disk_faithful` 只比较 `(seq, kind, node_id)` | 成立。案例 A（持久 `RUN_END.run_id` 与 `RUN_START.run_id` 不一致，账本正确，三元组相同）：V3 字面 **错误 PASS**（C03 PASS、C13 只看 `cleanup_confirmed`），现实现 **FAIL**（`integrity_issues` 的 `RUN_END_FOR_DIFFERENT_RUN`，把文件损坏记在协议头上）。案例 B（持久 `REGISTERED.pid` 损坏，账本与真实 PID 正确）：C04 读持久副本（`g0_judge.py:31,80-83`）⇒ **错误 FAIL**，且 FAIL 压过一切。补充：C（`creator` 被改 ⇒ C11 错误 FAIL）、D（`cleanup_confirmed` 被改 ⇒ C13 错误 PASS）、E（账本被改而文件正确 ⇒ 无人发现）。L-2 把这类情形说成「保守的 BLOCKED」是错的：被**改写**不同于被**丢失**。 | **是** |
| **F-21** 「读回」 | `json.loads(json.dumps(evidence))` 是内存往返，不接触文件，发现不了写失败 / 截断 / 篡改 / 静默类型改写；V3 同时写了 C16「在从 `g0_evidence.json` 读回的证据上」、`serialisation`「内存往返」、预注册 §4 步骤 7「先判定后写文件」——三者不可同时满足。现实现 `main()` 先 `judge(ev)` 再 `write_json(default=str)`，既不读回也不校验，且摘要写失败会以退出码 1（FAIL 的退出码）终止。建议顺序 P0–P7：严格序列化 → 排他写 → fsync → **读回字节并比对** → 在读回的证据上校验字段 → **只对读回的证据裁决** → 排他写摘要并读回核对（含 `evidence_sha256`）→ 退出码取自已保存的摘要；每个阶段的失败 ⇒ BLOCKED（退出码 3）。 | **是** |
| **F-22** C03-F3 | 成立。F3 的 `when`（`g0_criteria_v3.json:847`）说「追加失败时仍适用」，`precedence`（`:879`）说「F2、F3、F4 需要 writer_clean」；冻结文本对 DD-5 给出 FAIL 与 BLOCKED 两个答案。单一规则：机器可读需求表，`writer_clean` 只被 F2 与 F4 要求；F3 不要求（方案 α；β 只是表中一格之差）。DD-5 反例：α ⇒ FAIL（MEDIUM），β ⇒ BLOCKED；其余三个相关案例两方案结果相同。 | **是** |
| DD-1…DD-5 | 保持 V3 设计基线，**待 Grok**。ChatGPT 的有条件结论原文**不在本任务收到的指令里**，未转述、未臆造。若 Grok 相反：不选边，缩成判定表的一格，由双方签字，负责人拍板（报告 §5） | 并入同一个 V4 |

**规范修订确实需要 V4**：三项都是冻结文本自身的缺陷或自相矛盾，不能靠实现者解释或审查记录补救。**一次性最小差异清单 D1–D9**（完整记录保真；读 `reg` 的检查在不保真时 UNEVALUABLE（备选：改读账本）；C03 需求表；P0–P7 流水线与摘要必需字段；映射 C03 / C16 MODIFIED、C04 / C05 / C11 / C13 CLARIFIED；DD 裁决一并写入）见报告 §6。**不创建 V4，等 Grok 与 DD 裁决。**

静态案例：F-20 五个、F-22 四个（含 DD-5 的 α / β 两列）、流水线七个；`tools/check_g0_v3_closeout_cases.py`（只读 JSON）对 26 个裁决列做聚合核对，0 不一致，并已用三种故意破坏验证它会报错。

## 2. Git 状态与依赖

| 项 | 值 |
|---|---|
| 审核基准（本任务开始时 HEAD） | `b4ca97daa303269ebe7b268f4bb00c6601723a6d` |
| V3 冻结提交（未动，只含 3 个文件） | `7c4b99c581b306700fb6363abf417bc4b17127ea` |
| V2 / V1 冻结提交（未动） | `77750c38998489c3093f80439b52c3c5269db059` / `e287b952124e8aaf22098e1957c61da5359a5e2c` |
| 本阶段提交 | 包含本文件的提交（完整 SHA 见推送记录与 `git log`；一个提交自身的 SHA 无法写进它自己的内容）；仅审查报告、静态案例、一个只读检查工具及其输出、本检查点、`PROJECT_MAP` 追加块 |
| 依赖（未满足） | ① Grok 审核报告；② ChatGPT 对 DD-1…DD-5 的有条件结论原文（请负责人附上）；③ 负责人对「出 V4」「M-2 或 M-2′」「α 或 β」的决定 |

## 3. 冻结哈希（全部未变）与新增文件哈希

| 文件 | SHA-256 |
|---|---|
| `gate_g0/g0_criteria_v3.json` | `653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a` |
| `gate_g0/E1A_GATE_G0_PREREG_V3.md` | `0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88` |
| `gate_g0/g0_criteria_v3.json.sha256`（文件本身） | `34fb1f4e5904e45b759cd0b3098f5b4c03387127cd0844790570afbd45b47727` |
| `gate_g0/g0_criteria_v2.json` / `E1A_GATE_G0_PREREG_V2.md` | `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438` / `ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2` |
| `gate_g0/g0_criteria_v1.json` / `E1A_GATE_G0_PREREG.md` | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` / `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb` |
| E1-A 预注册 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| `bench_code_sha256` / `g0_code_sha256`（均未变；当前实现仍绑定 V1 文件） | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0` / `29e1253bad1665c102819a7aa2a894878397e0e2d505ac761b2ce1271b47ddbd` |
| `g0_preflight_review/G0_V3_CLOSEOUT_REVIEW.md` | `bfa2c30976e3f67b6b7e2bac90cb6cf62345f90648f93b16d250c90ab0307221` |
| `g0_preflight_review/g0_v3_closeout_cases.json` | `1af6bb4741dd5352f95026a754bf00733391b8d2d73c436d350e9c1cf22f503b` |
| `tools/check_g0_v3_closeout_cases.py` | `e92331f36d89ea390f14f7521f1ade37c526471cd824a8a04298313b6d89c2c5` |
| `g0_preflight_review/v3_closeout_cases_check.txt` | `7eba9fb57f18cc56702f2cbb8d3717e9fb7f2e54e7f63bae1213e95e41f190ce` |
| R3 / 决定记录 / 冻结记录前缀；`D1_CODE_SHA256SUMS` | `66a656145fc203c7` / `6209602e7d51b1ae` / `e3bba6b0968101bf`；10/10 OK |

重跑的只读检查：V3 一致性 0 不一致；V3 51 案例矩阵 0 不一致；静态审计（台架 / `--dir gate_g0`）0 / 0 违规。

## 4. 未解决问题

1. **GROK REVIEW PENDING**；没有双 AI 共识；ChatGPT 的 DD 有条件结论原文待附。
2. V4 尚未创建；在 Grok 报告与 DD-1…DD-5 裁决之前不创建，以免再出 V5。
3. M-2（四个检查在持久副本不保真时 UNEVALUABLE）与备选 M-2′（改读账本）、F3 的 α / β 需要裁决。
4. 沿用：F-14（L-1）、程序性义务不被判定函数验证（C02 / C05 / C06 / C15）、F-1（台架把僵尸当已死）。
5. 实现不符合 V3，更不符合将来的 V4；46 个纯逻辑测试仍未运行；本阶段没有运行任何测试。
6. `AUTHORIZATION_E1A_GATE_G0.json` 不存在；`evidence/` 不存在。

## 5. 下一条唯一指令

**将 `G0_V3_CLOSEOUT_REVIEW.md` 与 `g0_v3_closeout_cases.json` 提交 ChatGPT 与 Grok 审核；待 Grok 报告到达并裁决 DD-1…DD-5、M-2/M-2′、α/β 之后，再由负责人决定是否授权制定 V4。不授权实现，不运行任何测试，不创建 V4，不创建执行授权文件。**
