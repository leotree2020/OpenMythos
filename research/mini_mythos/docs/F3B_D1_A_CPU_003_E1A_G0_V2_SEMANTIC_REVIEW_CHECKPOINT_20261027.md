# F3B-D1-A-CPU-003 E1-A — 检查点：G0 V2 语义收口审核 G0-V2-SEMANTIC-REVIEW-001

**状态：`G0 V2 SPEC FROZEN / SEMANTIC REVIEW OPEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**（另：BV NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED）

任务：`F3B-D1-A-CPU-003-E1A-G0-V2-SEMANTIC-REVIEW-001`。审核基准 `f679995c5e526610c0ea1a26e7384c9b39860aa8`。
**只做源码与规则审计**：没有修改冻结的 V1/V2、没有创建 V3、没有修改任何实现；没有运行测试、`integrity_issues()` 或任何进程；报告中全部判定由通读源码得出，**未经执行验证**。

## 1. 结论（详见 `a_predicate_003/g0_preflight_review/G0_V2_SEMANTIC_REVIEW.md`）

| 问题 | 结论 | 分类 |
|---|---|---|
| F-16.1 重复 FORKED / REGISTERED / RELEASED，seq 连续 | **无 FAIL 规则**；`integrity_issues` 本身也不报；自然读法下已完成运行判 PASS | SEMANTIC CHANGE REQUIRES V3 |
| F-16.2 FORKED / REGISTERED 字段格式错误 | **无任何规则**（F1 的「字段格式错误」只指 RUN_START / RUN_END） | SEMANTIC CHANGE REQUIRES V3 |
| F-16.3 提前停止、REGISTERED 在而 FORKED 缺 | V2 字面：有 seq 空洞 ⇒ FAIL（F2），seq 连续 ⇒ BLOCKED（U1），**同一缺失记录判定相反**；正确判定取决于登记表是否被佐证 | SEMANTIC CHANGE REQUIRES V3（含一个需负责人拍板的政策点） |
| F-16.4 F1–F4 是否覆盖 `integrity_issues()` | **否**：24 类中 18 类有映射、3 类无映射（MALFORMED_FORKED、MALFORMED_REGISTERED、创建者未登记）、3 类部分映射（空登记表、RUN_START 数为 0、RUN_END 无 RUN_START）；另有源码本身不报的重复记录盲区 | V3（无映射 + 重复）；空文件 / 缺 INTENT 的提前中止为 DOCUMENTATION ONLY |
| F-16.5（新）缺失类 FAIL 规则不可靠 | `RegWriter.write` 在追加前递增 `seq`（`registry.py:23` 对 `:26`），写失败留下空洞；行边界上的丢失 `parse_clean` 看不见 ⇒ 把台架 I/O 失败 / 证据损坏误判为协议违规（CE-G1/G2/G3） | SEMANTIC CHANGE REQUIRES V3 |
| F-16.6（新）「规则穷尽」句不成立；U1 对非尾部记录空转 | 穷尽句：靠它落到的 BLOCKED 是对的；U1 范围并入上一行 | DOCUMENTATION ONLY / 并入 V3 |
| F-17 C16 新增必需证据 | **可能**把旧判据下的 PASS 变成 BLOCKED：对 d8a0728 实现的证据形式上必然；对符合 V2 的实现，只要新证据在某路径缺失（键名 V2 未指明）。被 V2 §10 挡住 | DOCUMENTATION ONLY |
| F-15 内存记录数 ≠ 解析记录数 | **有遗漏的规则**：台架只在 `verify_run_set` 比较（`observer.py:505`），提前中止路径不经过；C03 无规则；同一损坏会被 C13 判 BLOCKED、被 C03 判 FAIL，最终 FAIL | SEMANTIC CHANGE REQUIRES V3 |
| 其余 CLARIFIED（C01 C02 C05 C06 C09 C13 C15） | 决策语义不变；C02 / C05 / C06 / C15 的新文字含判定函数不检验的程序性条件 | DOCUMENTATION ONLY（C13：NO ISSUE） |
| 8 项 IDENTICAL | 语境变化不影响决策 | NO ISSUE |
| **按 V2 冻结文本直接实施** | 15 / 23 个反例的 V2 字面判定与应有判定不同：会把现 judge 判 FAIL 的重复记录判 PASS，把现 judge 判 BLOCKED 的证据损坏 / 写失败判 FAIL | **BLOCKED（建议：先决定是否出 V3，再授权实施）** |

反例矩阵：23 个（含 6 个正向控制）；V2 字面与应有判定不同 15 个；现 judge 与应有判定不同 9 个（含 3 个控制组：提前中止分支对正面违规与独立证据是盲的）。机器可读版 `c03_counterexamples.json`。

## 2. 建议修订范围（供交叉审核；**未创建 V3**）

只动 C03（规则）与 C16（证据键名），编号 C01–C17 不变；V1/V2 文件原样保留，新文件先单独冻结提交、再改实现。要点：S1 被佐证登记表（解析干净 ∧ 解析数 = 内存数 ∧ 写入器 seq = 内存数）；S2 正面违规补全（重复 FORKED / REGISTERED / RELEASED、字段类型错误且排除布尔、创建者未登记、多节点）；S3 「洞」规则取代空洞 / 前置缺失 / 孤儿；S4 未被佐证 ⇒ U2；S5 U1 收窄为尾部缺失并加显式默认「未匹配 ⇒ UNEVALUABLE」；S6 F3 仅在被佐证时；S7 **政策点**：被佐证的「缺 FORKED 有 REGISTERED」判 FAIL 还是 BLOCKED；S8 C16 写明确切键名且每条路径都写；S9 C02 / C05 / C06 的程序性条件要么加证据键要么明确不属于判定；S10（可选）F-14 子条件独立评估。

## 3. Git 状态与哈希

| 项 | 值 |
|---|---|
| 审核基准（本任务开始时 HEAD） | `f679995c5e526610c0ea1a26e7384c9b39860aa8` |
| V2 冻结提交（未动） | `77750c38998489c3093f80439b52c3c5269db059` |
| V1 冻结提交（未动） | `e287b952124e8aaf22098e1957c61da5359a5e2c` |
| 本阶段提交 | 包含本文件的提交（完整 SHA 见推送记录与 `git log`；一个提交自身的 SHA 无法写进它自己的内容）（仅文档 / 审查记录 / 数据；不含任何代码、判据、测试改动） |
| `g0_criteria_v2.json` | `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438`（未变） |
| `E1A_GATE_G0_PREREG_V2.md` | `ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2`（未变） |
| `g0_criteria_v1.json` / `E1A_GATE_G0_PREREG.md` | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` / `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb`（未变） |
| E1-A 预注册 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`（未变） |
| `bench_code_sha256` / `g0_code_sha256` | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0` / `29e1253bad1665c102819a7aa2a894878397e0e2d505ac761b2ce1271b47ddbd`（均未变） |
| `g0_preflight_review/G0_V2_SEMANTIC_REVIEW.md` | `fbcd1e68491622f851bdccbbea65b287786868d8af9de8404510f77f9bf37595` |
| `g0_preflight_review/c03_counterexamples.json` | `69e89c23a39a6ff801a17cdd869281fe09245aafdf00ad2f2d2b7532780741b5` |
| 一致性检查（`tools/check_g0_v2_consistency.py`，重跑） | 0 不一致 |
| R3 / 决定记录 / 冻结记录前缀；`D1_CODE_SHA256SUMS` | `66a656145fc203c7` / `6209602e7d51b1ae` / `e3bba6b0968101bf`；10/10 OK |

## 4. 未解决问题

1. **是否出 V3**：本报告建议在授权实现之前先决定（V2 字面实现会放宽现 judge 的重复记录检查，并把证据损坏 / 写失败判成 FAIL）。V3 须走「先冻结判据、再改代码」。
2. **政策点 S7**（被佐证的缺 FORKED：FAIL 还是 BLOCKED）与 **佐证的定义**（§0.2 第 3 条是我的提议）需要交叉审核者 / 负责人决定。
3. F-14（C03 之外检查的整项 UNEVALUABLE，限度 L-1）仍开放；F-1（僵尸当已死）仍开放。
4. 实现仍不符合 V2（仍绑定 V1 文件路径，未实现 F-8 / F-9 / F-12 / F-13）；46 个纯逻辑测试仍未运行；若出 V3，上述实现设计与测试矩阵需要对应修订。
5. 本报告的所有判定（`integrity_issues` 输出、V2 字面结果、现 judge 结果）都是通读源码得出的；获得纯逻辑执行授权后，可用 `c03_counterexamples.json` 机械核对。
6. `AUTHORIZATION_E1A_GATE_G0.json` 不存在；`evidence/` 不存在。

## 5. 下一条唯一指令

**将 `G0_V2_SEMANTIC_REVIEW.md` 与 `c03_counterexamples.json` 交给 ChatGPT 和 Grok 交叉审核，并等待项目负责人决定是否出 V3；不自动创建 V3，不修改实现，不运行测试。**
