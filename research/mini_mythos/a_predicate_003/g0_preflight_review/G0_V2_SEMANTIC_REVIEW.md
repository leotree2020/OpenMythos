# G0_V2_SEMANTIC_REVIEW — F-16 C03 规则完备性 与 F-17 V1→V2 语义分类 的独立审查报告

**状态：`G0 V2 SPEC FROZEN / SEMANTIC REVIEW OPEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V2-SEMANTIC-REVIEW-001`。审核基准 HEAD `f679995c5e526610c0ea1a26e7384c9b39860aa8`。
**没有**修改冻结的 V1/V2、没有创建 V3、没有修改任何实现；**没有**运行测试、`integrity_issues()` 或任何进程。**本报告里所有「V2 字面规则」「现 judge」「integrity_issues 输出」的结论都是通读源码推出的，未经执行验证**（见 §0.3）。

## 0. 方法、分类与诚实声明

### 0.1 审查对象
* V2 规则文本：`gate_g0/g0_criteria_v2.json` → `checks.G0-C03.rules`（`C03-F1…F4`、`C03-U1/U2`、`pass_when`、`precedence`）；
* 源码：`bench/registry.py`（`integrity_issues` :61、`lifecycle_issues` :83、`fold` :146、`check_order` :218、`parse_reg` :30、`RegWriter.write` :19）、`bench/observer.py`（写入顺序 :71/:84/:99/:118/:131，`verify_run_set` :491）、`gate_g0/g0_judge.py`（当前 `c03` :51）、`gate_g0/g0_run.py`（`reg_parse_info` :363）。

### 0.2 判定「应有判定」的原则（先于下面的矩阵写下）
1. **FAIL 需要证据证明被测机制违反了协议**；
2. 在**已解析的记录**里可见的违规（「正面违规」）本身就是证明，与运行如何结束无关；
3. **缺失**只有在登记表被**佐证**时才是证明：解析报告干净 **且** 解析出的记录数 = 内存记录数 **且** 写入器的 `seq` = 内存记录数（`RegWriter.write` 在追加**之前**就递增 `seq`，`registry.py:23` 对 `:26`，所以一次失败的追加会留下序号空洞而没有任何协议违规）；
4. 其余（提前中止、登记表破损或未被佐证、台架 I/O 失败）⇒ UNEVALUABLE → BLOCKED；
5. 独立于登记表的证据（fork 次数、放行字节、子进程消息）可以证明「某动作已发生」，同样只在被佐证的登记表上用来证明前置记录缺失。

这些原则是对项目负责人在本任务与上一任务中陈述的原则（「证据充分的违规 ⇒ FAIL；因超时 / 提前中止证据不足 ⇒ UNEVALUABLE → BLOCKED；能独立证明的缺失仍 FAIL」）的**展开**，不是新增政策；但第 3 条中「佐证」的具体定义是我的提议，供交叉审核。

### 0.3 分类（报告里每个问题只取其一）
* **NO ISSUE**：V2 文字决定了与源码、原则一致的判定；
* **DOCUMENTATION ONLY**：V2 文字不完整或措辞不准，但所有可推导的读法给出**同一个**（正确的）判定；可用审查记录 / 实现设计文档补充，无需新版本；
* **SEMANTIC CHANGE REQUIRES V3**：V2 字面在某组可达证据上给出与原则不同的判定，或两种读法给出不同判定；修正会改变冻结的规则文本；
* **BLOCKED**：在问题解决之前不应授权实现 / 执行。

### 0.4 声明
下面指出的缺陷是**我写的 V2 的缺陷**：包括上一阶段我在 F1 草稿里原计划包含的「FORKED / REGISTERED 字段格式错误」在最终文字里被漏掉，以及「规则穷尽」一句过强。我没有用修改实现来掩盖判据问题：当前 `g0_judge.py` 在若干方向上与 V2 字面不同（§6），它不是 V2 的参照。

---

## 1. 结论总表

| # | 问题 | 结论 | 分类 |
|---|---|---|---|
| F-16.1 | 重复 FORKED / REGISTERED / RELEASED 且 seq 连续：有明确 FAIL 规则吗？ | **没有**。`integrity_issues` 本身也不报；V2 的 F1 只列了 RUN_START / RUN_END / INTENT / DEAD 的重复。在「链取每种记录的第一个」这一自然读法下，已完成运行会被判 **PASS**（CE-D1…D3）；若把链读作「每种恰好一个」，则既不 PASS、也没有任何 F 规则命名它——两种读法给出不同判定，本身就需要 V3。 | **SEMANTIC CHANGE REQUIRES V3** |
| F-16.2 | FORKED / REGISTERED 字段格式错误归入哪条 FAIL 规则？ | **没有任何一条**。F1 的「字段格式错误」仅指 RUN_START / RUN_END。`integrity_issues` 有 `MALFORMED_FORKED/REGISTERED`，V2 没有映射。 | **SEMANTIC CHANGE REQUIRES V3** |
| F-16.3 | 提前停止、REGISTERED 在而 FORKED 缺：FAIL 还是 BLOCKED？ | **同一缺失记录，V2 因 seq 是否出现空洞而给出相反判定**：有空洞 ⇒ F2 ⇒ FAIL；seq 连续 ⇒ U1 ⇒ BLOCKED。原则下的正确判定取决于登记表是否被佐证（§2.4）。 | **SEMANTIC CHANGE REQUIRES V3** |
| F-16.4 | F1–F4 是否覆盖 `integrity_issues()` 能报告的全部违规？ | **否**。24 类问题：18 类有映射（其中靠「缺失」推断的几类不可靠，见 F-16.5）、3 类**无**映射（`MALFORMED_FORKED`、`MALFORMED_REGISTERED`、创建者未登记）、3 类**部分**映射（`EMPTY_REGISTRY`、`RUN_START_COUNT`=0、`RUN_END_WITHOUT_RUN_START`）。 | **SEMANTIC CHANGE REQUIRES V3**（3 类无映射 + 重复）；空登记表 / 缺 INTENT 的提前中止：**DOCUMENTATION ONLY** |
| F-16.5（新） | F2 / F3 / F4 靠「缺失」判 FAIL，但「解析干净」不能排除整行丢失或台架写失败，会把**证据损坏 / 台架 I/O 失败误判为协议违规**（CE-F1、G1、G2、G3） | 不可靠 | **SEMANTIC CHANGE REQUIRES V3** |
| F-16.6（新） | `pass_when` 末句「规则是穷尽的」不成立；U1 把 FORKED / REGISTERED / RELEASED 称为「后期记录」，但它们缺失时（非尾部）必然伴随 seq 空洞，U1 对它们空转 | 措辞错误 + 与 F-16.5 联动 | 穷尽句：**DOCUMENTATION ONLY**；U1 范围：并入 F-16.5 的 **V3** |
| F-17.1 | C16 新增必需证据能否把旧判据下的 PASS 变成 BLOCKED？ | **能，在两种意义上**（§3.2）：对 d8a0728 实现产生的证据，形式上能；对符合 V2 的实现，只要新证据在某条路径缺失就能。键名在 V2 文字里未指明。该风险被 V2 §10 的执行门挡住。 | **DOCUMENTATION ONLY**（C16 本身）；其中「内存记录数」无规则可用的部分见 F-15 |
| F-15 | 内存记录数与磁盘解析记录数不一致：有遗漏的完整性规则吗？ | **有**。台架只在 `verify_run_set` 比较（`observer.py:505`），提前中止路径不经过它，也不覆盖 `RUN_END`；V2 的 C03 没有规则，C16 只要求「记录」。 | **SEMANTIC CHANGE REQUIRES V3** |
| F-17.2 | 其余 C01/C02/C05/C06/C09/C13/C15 的 CLARIFIED 是否真的语义不变？ | 全部决策语义不变；C02 / C05 / C06 / C15 的新文字含有判定函数不检查的程序性条件。 | **DOCUMENTATION ONLY** |
| F-17.3 | 8 项 IDENTICAL | 文字相同；语境变化（轮询回收、目录创建）不影响其决策。 | **NO ISSUE** |
| — | **按 V2 冻结文本直接实施** | 按字面实现会：把 judge 现在判 FAIL 的重复记录判 PASS；把 judge 现在判 BLOCKED 的证据损坏 / 写失败判 FAIL（15 / 23 个反例的字面判定与原则不符） | **BLOCKED（建议：先决定是否出 V3，再授权实施）** |

---

## 2. F-16 逐项审查

### 2.1 V2 规则原文（来自 JSON，未改）

* **C03-F1**（总是适用）：among the records that are present: a successor has an earlier seq than its predecessor (RELEASED before REGISTERED, REGISTERED before INTENT, FORKED before INTENT); non-monotonic or duplicated seq; more than one RUN_START, RUN_END, INTENT or DEAD; a record before RUN_START; any record after RUN_END; any record of the node after its DEAD; RELEASED and ABORTED both present; a RUN_END or RUN_START whose fields are malformed or whose run_id differs
* **C03-F2**（仅 parse_clean）：the registry itself proves a missing record: a successor is present while its required predecessor is absent (RELEASED without REGISTERED, REGISTERED without INTENT, FORKED without INTENT, DEAD without INTENT); a node record without any INTENT (orphan); a gap in seq; a RUN_END with cleanup_confirmed true while the node has no DEAD record
* **C03-F3**（仅 parse_clean）：independent evidence proves that an action took place whose preceding record is absent: no RELEASED record although release_byte_written or child_acted; no REGISTERED record although release_byte_written, child_acted or a RELEASED record exists; no INTENT record although guard.fork_calls >= 1
* **C03-F4**（仅 parse_clean 且 completed_run）：a required record is absent from a run that completed normally: any of RUN_START, INTENT, FORKED, REGISTERED, RELEASED, DEAD (with basis), RUN_END; or ABORTED is present
* **C03-U1**：early_stop AND parse_clean AND no fail rule fired: the only deviations are missing later-lifecycle records (FORKED, REGISTERED, RELEASED, DEAD, RUN_END, or an ABORTED record from a failed registration) and no independent evidence shows that an action happened without its record -> the lifecycle could not be completed, which proves nothing about the protocol
* **C03-U2**：no fail rule fired AND (the registry file is missing or unreadable, or has a torn tail or corrupt lines, or the independent evidence needed by C03-F3 is itself missing) -> the evidence is damaged or absent
* **pass_when**：completed_run AND parse_clean AND the PASS condition of the check text holds. The rules are exhaustive: a completed, parse-clean run that does not satisfy pass_when has a missing or irregular record and therefore fires C03-F1, F2 or F4; an early stop that fires no fail rule is C03-U1 or C03-U2.

### 2.2 源码事实（写入顺序与检测盲区）

1. **写入顺序**：`INTENT`（`observer.py:71`）→ `fork` → `FORKED`（`_note_forked`，`:84`→`:99`）→ `REGISTERED`（`:118`）→ 保持期 → `RELEASED`（`:131`，早于放行字节 `:133`）→ …→ `DEAD`（`:441`）→ `RUN_END`（`g0_run.py`）。
2. **`RegWriter.write`（`registry.py:19-27`）**：`self.seq += 1`（:23）在 `C.append_jsonl`（:26）**之前**；追加失败会抛 `OSError`，但 `seq` 已被消耗，且该记录不进内存列表。
3. **`fold`（:146-168）**：同一节点同种记录**后者覆盖前者**；没有 `node_id` 的记录被忽略。
4. **`check_order`（:218-246）**：每个节点每种记录只保留**最后一个** seq 做比较；没有「REGISTERED 需要 FORKED」的规则；创建者检查只在创建者不是 `O` 时进行。
5. **`integrity_issues`（:61-80）**：SEQ_GAP_OR_REORDER（第一个异常即 `break`）、ORPHAN_RECORD、MALFORMED_FORKED、MALFORMED_REGISTERED，再加 `check_order` 与 `lifecycle_issues`；`isinstance(x, int)` 对布尔值也为真。
6. **`parse_reg`（:30-58）**：只能发现撕裂尾部、坏行、文件缺失 / 不可读；**整行消失**（行边界上的丢失）不会留下任何痕迹。

### 2.3 `integrity_issues()` 全部可报告项与 V2 规则的映射（回答 F-16.4）

| 编号 | 行 | 源码报告 | V2 规则 | 评价 |
|---|---|---|---|---|
| I1 | :68 | `SEQ_GAP_OR_REORDER` | 重排 / 重复序号：F1；**空洞：F2（需 parse_clean）** | 重排已覆盖；空洞的 FAIL 归类不可靠（F-16.5） |
| I2 | :72 | `ORPHAN_RECORD` | F2 | 有映射；依赖「缺失 = 证据」 |
| I3 | :75 | `MALFORMED_FORKED` | **无** | **未覆盖** |
| I4 | :77 | `MALFORMED_REGISTERED` | **无** | **未覆盖** |
| I5 | :230 | ORDER 非单调 seq | F1 | 覆盖 |
| I6 | :234 | RELEASED 无更早的 REGISTERED | F1（两者都在、顺序反）/ F2（REGISTERED 缺） | 覆盖；重复记录时「最后一个」语义有歧义（CE-D4） |
| I7 | :236 | REGISTERED 无更早的 INTENT | F1 / F2 | 覆盖 |
| I8 | :238 | RELEASED 与 ABORTED 并存 | F1 | 覆盖 |
| I9 | :240 | FORKED 无更早的 INTENT | F1 / F2 | 覆盖 |
| I10 | :246 | 创建者在子节点 INTENT 之前未登记 | **无**（C11 负责单节点预算） | **未覆盖**（G0 中不可达，CE-T1） |
| I11 | :93 | `EMPTY_REGISTRY` | 完整运行：F4；**提前中止：无** | 部分 |
| I12 | :98 | `RUN_START_COUNT≠1` | >1：F1；=0：仅完整运行 F4；**提前中止：无** | 部分 |
| I13 | :102 | `RUN_START_NOT_FIRST` | F1「RUN_START 之前的记录」 | 覆盖 |
| I14 | :104 | `RUN_START_ILLEGAL` | F1 | 覆盖 |
| I15 | :108 | `DUPLICATE_RUN_END` | F1 | 覆盖 |
| I16 | :112 | `RUN_END_WITHOUT_RUN_START` | 完整运行：F4；**提前中止：无** | 部分 |
| I17 | :114 | `RUN_END_BEFORE_RUN_START` | F1 | 覆盖 |
| I18 | :116 | `RUN_END_FOR_DIFFERENT_RUN` | F1 | 覆盖 |
| I19 | :118 | `RUN_END_ILLEGAL` | F1 | 覆盖 |
| I20 | :120 | `RECORD_AFTER_RUN_END` | F1 | 覆盖 |
| I21 | :126 | `CONFIRMED_RUN_END_WITH_UNFINISHED_NODES` | F2 | 覆盖；依赖「缺失 = 证据」 |
| I22 | :134 | `NODE_RECORD_BEFORE_RUN_START` | F1 | 覆盖 |
| I23 | :137 | `DUPLICATE_INTENT` | F1 | 覆盖 |
| I24 | :140 | `RECORD_AFTER_DEAD`（含第二个 DEAD） | F1 | 覆盖 |
| — | （源码**不报**） | 重复的 FORKED / REGISTERED / RELEASED；REGISTERED 无 FORKED；布尔值当整数 | **无** | 台架与 V2 **同时**盲 |

计数：24 类中 18 类有映射、3 类无映射（I3、I4、I10）、3 类部分映射（I11、I12、I16）；另有源码本身不报告的重复记录盲区。

### 2.4 逐问回答与反例（详见 §4 矩阵与 `c03_counterexamples.json`）

**Q1 重复 FORKED / REGISTERED / RELEASED（seq 连续）——没有 FAIL 规则。**
* 源码依据：`integrity_issues` 无此项；`fold` 后者覆盖前者（:146-168）；`check_order` 只留最后 seq（:218-246）；`lifecycle_issues` 只有 `DUPLICATE_INTENT`、`DUPLICATE_RUN_END`、`RECORD_AFTER_DEAD`。
* V2 的 F1 只列 RUN_START / RUN_END / INTENT / DEAD；`pass_when` 的链 `INTENT < FORKED < REGISTERED < RELEASED < DEAD` 对重复记录仍然成立（取每种的第一个）。**CE-D1 / D2 / D3：已完成运行、解析干净、`integrity_issues` 为空 ⇒ 在自然读法下 V2 字面 PASS**（另一读法「每种恰好一个」下既不 PASS 也无规则命名它）；原则下应为 FAIL（正面违规，与 V2 已判 FAIL 的重复 INTENT / DEAD 同类）。
* 现 `g0_judge.py:63-65` 对计数≠1 判 FAIL，比 V2 严。**按 V2 字面实现会放宽它。**
* CE-D4（REGISTERED 之后又出现 REGISTERED）：`check_order` 以最后一个 REGISTERED 的 seq 与 RELEASED 比较而报「RELEASED 无更早的 REGISTERED」；F1「RELEASED 先于 REGISTERED」是否适用取决于读法 ⇒ 歧义。
* 分类：**SEMANTIC CHANGE REQUIRES V3**。

**Q2 FORKED / REGISTERED 字段格式错误——没有规则。**
* 源码：`registry.py:74-77`（非整型 `pid`；`REGISTERED` 缺整型 `pid` / `starttime`）。V2 F1 的「字段格式错误」只指 RUN_START / RUN_END。
* **CE-M1（已完成）**：`pass_when` 要求 `integrity_issues` 为空，故不会 PASS，但 F1/F2/F4 没有一条能字面触发，而「穷尽」句断言它们会触发。**CE-M2 / M3（提前中止）**：无 F 规则、U1 不匹配 ⇒ 靠「穷尽」句落到 BLOCKED，原则下应为 FAIL（正面违规）。
* 另：布尔值通过 `isinstance(…, int)`（源码盲点，V3 应明确 `not bool`）。
* 分类：**SEMANTIC CHANGE REQUIRES V3**（低可达性：真实写入器总是写整数，但预注册要求判定在运行前确定）。

**Q3 提前停止、REGISTERED 在而 FORKED 缺——V2 字面给出两个相反的判定。**
* 真实写入器的顺序保证 `FORKED` 在 `INTENT` 与 `REGISTERED` 之间且 seq 连续（`observer.py:71,84,99,118`）。所以「REGISTERED 在、FORKED 缺」只可能是：(a) 该行事后丢失（seq 出现空洞，**CE-F1**），或 (b) 写入器缺陷使 FORKED 从未写入（seq 连续，**CE-F2**）。写失败的情形不会出现（FORKED 写失败会抛异常，REGISTERED 不会被写）。
* **V2 字面**：(a) 有空洞 + 解析干净 ⇒ F2「a gap in seq」⇒ **FAIL**；(b) 连续 ⇒ F2 的前置列表**不含**「REGISTERED 无 FORKED」，F3 只管「必须先于某动作」的记录（FORKED 在 fork **之后**写，不是任何动作的前置）⇒ U1 ⇒ **BLOCKED**。同一缺失记录，因 seq 是否空洞而判定相反。
* **原则下的判定**：(a) 登记表未被佐证（解析 5 ≠ 写入 6）⇒ **BLOCKED**；(b) 被佐证的「洞」⇒ 这是写入器违反自己的顺序，**倾向 FAIL**，但这是需要负责人 / 审核者拍板的政策点：台架自己的恢复逻辑只靠 `REGISTERED`（`registry.py:170-183` `cleanup_targets`）、`check_order` 也没有 FORKED 要求，因此缺 FORKED 对安全无影响；两种判定都有依据，必须在 V3 里**明说**而不是留给空洞与否。
* 对「提前停止时 REGISTERED 在而 FORKED 缺应判 FAIL 还是 BLOCKED」的直接回答：**不能无条件判 FAIL，也不能无条件判 BLOCKED；判 FAIL 需要登记表被佐证（解析数 = 内存数 = 写入器 seq）**；未被佐证则 BLOCKED。V2 当前文字没有这个条件。
* 分类：**SEMANTIC CHANGE REQUIRES V3**。

**Q4 F1–F4 是否覆盖 `integrity_issues()` 的全部违规——否**（§2.3 表）。另外发现三个结构性问题：
* **缺失类规则不可靠（F-16.5）**：F2/F3/F4 把「`parse_clean`」当作「缺失是真的」。但 `parse_clean` 只排除缺失文件 / 撕裂尾部 / 坏行。**CE-G1**：`RELEASED` 追加因 ENOSPC 失败 ⇒ 异常 ⇒ `RUN_END(false)` 得到下一个 seq ⇒ 空洞，解析干净 ⇒ V2 字面 **FAIL**；真实原因是台架 I/O 失败，应为 **BLOCKED**（`writer_seq=6` 对内存记录 5 条可以证明）。**CE-G2**：已完成运行，文件尾部（DEAD、RUN_END）在行边界上丢失 ⇒ F4 **FAIL**；应为 BLOCKED（解析 5 ≠ 写入 7）。**CE-G3**：头部丢失同理。
* **U1 对非尾部记录空转**：U1 把 `FORKED/REGISTERED/RELEASED` 称为「后期记录」，但它们缺失时（不在尾部）必然伴随 seq 空洞 ⇒ F2 先触发 ⇒ FAIL（FAIL 先于 U）。U1 实际只对尾部缺失（`DEAD`、`RUN_END`）起作用。
* **回落漏洞**：提前中止、解析干净、无 F 规则触发、缺失的不是 U1 列表中的记录——如 `RUN_START` 或 `INTENT`（**CE-H1**，fork 之前停止）、空文件（**CE-H2**，U2 不含「可读的空文件」）——没有任何规则匹配；「规则是穷尽的」一句把它们解释为 U1/U2，从而得到 BLOCKED。**这个结果是对的**，所以分类为 **DOCUMENTATION ONLY**；修订 V3 时应把它写成显式的默认规则「未匹配 ⇒ UNEVALUABLE」。

---

## 3. F-17 重新审核 V1 → V2 语义分类

### 3.1 逐项（17 项）

对每项问三个问题：(a) 旧判据（V1 文字）下的 PASS 在 V2 下是否可能变成非 PASS？ (b) 已审实现（d8a0728）是否本来就强制该条件？ (c) V2 新增的条件是否有证据字段支撑？

| ID | V2 关系 | (a) | (b) | (c) | 分类 |
|---|---|---|---|---|---|
| C01 | CLARIFIED | 形式上可能（V1 文字没列 Python 版本 / `-B` / SIGCHLD / pidfd 可用） | **是**：`preflight()` 的 `problems` 早已检查（`g0_run.py` 预检） | 有（`pf.problems`） | DOCUMENTATION ONLY |
| C02 | CLARIFIED | 否（同一次运行；绑定 V2 文件由哈希自动保证） | 部分 | **「fork 之前」的先后没有证据字段**：`auth_consumed` 只是布尔值；判定函数无法检验 | DOCUMENTATION ONLY（新增文字是程序义务，不是可检验条件） |
| C03 | MODIFIED | V1 文字与 V2 文字对重复记录都没有规则；与**已审 judge**相比，V2 字面对重复记录更松（FAIL→PASS，自然读法）、对空洞 / 丢尾部更紧（BLOCKED / FAIL 之分见矩阵）；字段错误在两版文字里都因 `integrity_issues` 非空而不 PASS，但无规则命名 | 否（现 judge 与 V2 不同） | 缺 `reg_memory_count`、`writer_seq` | **SEMANTIC CHANGE REQUIRES V3** |
| C04 | IDENTICAL | 否 | — | — | NO ISSUE |
| C05 | CLARIFIED | 否（判定函数对 S1 的检查不变） | 是 | 「在保持期末拍摄」仅可由 `S1.mono − REGISTERED.mono ≥ 0.3` 间接检验，判定函数不检验 | DOCUMENTATION ONLY |
| C06 | CLARIFIED | 否 | 是 | 同 C05 | DOCUMENTATION ONLY |
| C07–C08 | IDENTICAL | 否 | — | — | NO ISSUE（C07 读取第一个 REGISTERED / RELEASED；重复记录属于 C03） |
| C09 | CLARIFIED | 否：V1 的阻塞 `waitpid` 返回该 pid ⇒ V2 同样 PASS；V2 额外允许 `WNOHANG` 轮询 | 是（判定函数只要求恰一次返回该 pid） | 「至多 `reap_deadline_s`」可由 `reap_mono`/`proc_gone_mono` 推出，判定函数未检验 | DOCUMENTATION ONLY |
| C10–C12 | IDENTICAL | 否 | — | — | NO ISSUE |
| C13 | CLARIFIED | 否（括号里的 `RUN_END(false)` 与 V1「RUN_END confirmed」等价） | 是 | 有 | NO ISSUE |
| C14 | IDENTICAL | 否 | — | — | NO ISSUE |
| C15 | CLARIFIED | 否（超时名称多了 `reap`、`total`，语义同「没有阶段截止被触发」） | 部分 | 「运行中强制」是实现义务；证据 = `deadline_hits` | DOCUMENTATION ONLY |
| C16 | CLARIFIED | **见 §3.2** | 否 | **键名未指明** | DOCUMENTATION ONLY（C16 本身）；记录数的用途见 F-15 |
| C17 | IDENTICAL | 否 | — | — | NO ISSUE |

IDENTICAL 的 8 项：除了其决策本身不变外，我另核对了 V2 新增的程序（轮询回收、目录创建、运行期预算）不会改变它们读取的证据——C08 要求「任何 wait 调用之前」S3 已观察到 `Z`，轮询从 S3 之后开始；C14 的描述符基线不受目录创建影响（目录操作不保留描述符）。

### 3.2 C16 是否可能把旧判据下的 PASS 变为 BLOCKED？——可能，两种意义
1. **对 d8a0728 实现产生的证据**：V2 C16 要求登记表解析报告、内存记录数、证据根目录所有权记录、运行目录创建记录。当前实现只写 `reg_parse_info`，不写另三项 ⇒ 同一次干净运行在 V1 判据下 PASS，在 V2 下 UNEVALUABLE → BLOCKED。这是设计上的结果，由 V2 §10（实现符合前不得授权执行）挡住。
2. **对符合 V2 的实现**：若任何一项在**某条路径上**未被写入，C16 即 BLOCKED。正常路径可以保证；风险在于：① V2 文字没有指明键名，实现与判定函数可能各自取名（永远 BLOCKED 的典型成因）；② 「内存记录数」在 `RUN_END` 之后、解析之前取才有意义，取早了会造成假的不一致（见 F-15）。
* 结论：C16 本身为 **DOCUMENTATION ONLY**——用实现设计文档固定键名（`reg_parse_info`、`reg_memory_count`、`reg_writer_seq`、`evidence_root`、`run_dir`、`consumed_dir`）并加静态检查「判定函数要求的键 ⊆ 运行写入的键」即可；若出 V3，则把键名写进判据。

### 3.3 F-15：内存记录数与磁盘解析记录数不一致
* 台架有一处比较：`observer.verify_run_set`（`observer.py:505-506`）发现「文件记录数 ≠ 写入记录数」，使 `run_set.consistent=false` ⇒ `cleanup_ok=false` ⇒ C13 BLOCKED。限度：① 只在 `final_cleanup` 内、`RUN_END` 之前执行，**提前中止路径不经过它**（G0 异常路径不调用 `final_cleanup`）；② 不覆盖 `RUN_END` 与其后的任何丢失；③ C13 是 BLOCKED 类，而 C03 的缺失类规则在同一份证据上可判 **FAIL**，且 FAIL 优先——于是同一证据损坏会被 C13 判为 BLOCKED、被 C03 判为 FAIL，最终 FAIL（CE-G2）。
* V2 的 C03 没有使用记录数的规则；C16 只要求「记录」。`g0_run.py` 当前也不记录它。
* 遗漏的规则：**被佐证的登记表** = 解析干净 ∧ 解析数 = 内存数 ∧ 写入器 `seq` = 内存数；缺失类规则只在被佐证时有效；否则 ⇒ U2。分类：**SEMANTIC CHANGE REQUIRES V3**。

---

## 4. 最小反例矩阵（共 23 个；机器可读版 `c03_counterexamples.json`）

「应有判定」依 §0.2。**15 个反例的 V2 字面判定与应有判定不同**（含 7 个靠「穷尽」句落到 BLOCKED 的未定义情形）；**9 个反例的现 judge 与应有判定不同**（包括 3 个控制组：`CE-P2/P3/P4`，说明现 judge 的提前中止分支对正面违规与独立证据是盲的）。控制组 `CE-P1…P5` 与 `CE-F3` 表明 V2 中有效的规则确实有效。

| ID | 问 | 场景 / 成因 | 登记记录（seq 种类 节点…） | 关键证据 | 应有判定 | V2 字面规则 | 现 judge（d8a0728） | 分类 |
|---|---|---|---|---|---|---|---|---|
| `CE-D1` | Q1 | duplicate FORKED, consecutive seq (completed run) — second FORKED record written/duplicated for the same node | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 FORKED n1 pid=200 · 5 REGISTERED n1 pid=200 st=5000 · 6 RELEASED n1 · 7 DEAD n1 basis · 8 RUN_END confirmed=true | completed_run=True, parse_clean=True, mem_count=8, parsed_count=8, writer_seq=8, fork_calls=1 | **FAIL** | **PASS**：no rule: F1 lists duplicates only for RUN_START/RUN_END/INTENT/DEAD; pass_when holds (integrity_issues empty; chain INTENT<FORKED<REGISTERED<RELEASED<DEAD holds for the first of each) | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-D2` | Q1 | duplicate REGISTERED with different pid, both before RELEASED (completed run) — second REGISTERED written (e.g. a re-registration) | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 REGISTERED n1 pid=201 st=5001 · 6 RELEASED n1 · 7 DEAD n1 basis · 8 RUN_END confirmed=true | completed_run=True, parse_clean=True, mem_count=8, parsed_count=8, writer_seq=8, fork_calls=1 | **FAIL** | **PASS**：no rule for duplicate REGISTERED; C04/C07 read the first REGISTERED only (g0_judge.py c04/c07 use k['REGISTERED'][0]) | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-D3` | Q1 | duplicate RELEASED, consecutive seq (completed run) — second RELEASED record | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RELEASED n1 · 7 DEAD n1 basis · 8 RUN_END confirmed=true | completed_run=True, parse_clean=True, mem_count=8, parsed_count=8, writer_seq=8, fork_calls=1 | **FAIL** | **PASS**：no rule for duplicate RELEASED | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-D4` | Q1 | REGISTERED, RELEASED, then a second REGISTERED (completed run) — late duplicate REGISTERED | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 REGISTERED n1 pid=200 st=5000 · 7 DEAD n1 basis · 8 RUN_END confirmed=true | completed_run=True, parse_clean=True, mem_count=8, parsed_count=8, writer_seq=8, fork_calls=1 | **FAIL** | **AMBIGUOUS**：integrity_issues is non-empty (check_order reports 'RELEASED without earlier REGISTERED' because the LAST REGISTERED seq 6 > RELEASED seq 5), so pass_when fails; F1 'RELEASED before REGISTERED' fits only if read against the last REGISTERED. No rule names the duplicate | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-D5` | Q1 | duplicate FORKED, early stop — as CE-D1 but the run stopped at the READY wait | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 FORKED n1 pid=200 · 5 REGISTERED n1 pid=200 st=5000 · 6 RELEASED n1 · 7 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=7, parsed_count=7, writer_seq=7, fork_calls=1, release_byte_written=True | **FAIL** | **UNDEFINED -> BLOCKED**：no F rule; U1 needs 'only missing later-lifecycle records' which is false; the sentence 'an early stop that fires no fail rule is U1 or U2' then implies BLOCKED | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-M1` | Q2 | REGISTERED with starttime null (completed run) — malformed critical field | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=null · 5 RELEASED n1 · 6 DEAD n1 basis · 7 RUN_END confirmed=true | completed_run=True, parse_clean=True, mem_count=7, parsed_count=7, writer_seq=7, fork_calls=1 | **FAIL** | **NOT PASS, rule unnamed**：pass_when requires integrity_issues empty, so no PASS; but none of F1-F4 names malformed FORKED/REGISTERED fields (F1's malformed clause covers only RUN_START/RUN_END). The 'exhaustive' sentence claims F1/F2/F4 fires; none does literally | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-M2` | Q2 | REGISTERED with starttime null, early stop — as CE-M1, run stopped at the READY wait | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=null · 5 RELEASED n1 · 6 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=6, parsed_count=6, writer_seq=6, fork_calls=1, release_byte_written=True | **FAIL** | **UNDEFINED -> BLOCKED**：no F rule; U1 does not match (nothing missing); sentence implies BLOCKED | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-M3` | Q2 | FORKED with pid as string, early stop — malformed FORKED field | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid='200' · 4 REGISTERED n1 pid=200 st=5000 · 5 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=5, parsed_count=5, writer_seq=5, fork_calls=1 | **FAIL** | **UNDEFINED -> BLOCKED**：as CE-M2 | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-F1` | Q3 | early stop, REGISTERED present, FORKED line lost, seq gap, counts disagree — a clean-boundary line loss after writing (disk/tamper) | 1 RUN_START · 2 INTENT n1 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=6, parsed_count=5, writer_seq=6, fork_calls=1, release_byte_written=True | **BLOCKED** | **FAIL**：F2 'a gap in seq' with parse_clean (torn_tail=false, corrupt_lines=0 because the whole line vanished) -> FAIL | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-F2` | Q3 | early stop, REGISTERED present, FORKED never written, contiguous seq, counts agree — writer skipped FORKED (a writer defect; the real writer always writes FORKED between INTENT and REGISTERED, observer.py:71,84,99,118) | 1 RUN_START · 2 INTENT n1 · 3 REGISTERED n1 pid=200 st=5000 · 4 RELEASED n1 · 5 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=5, parsed_count=5, writer_seq=5, fork_calls=1, release_byte_written=True | **FAIL (recommended; owner decision)** | **BLOCKED**：no F rule (F2's predecessor list lacks REGISTERED-without-FORKED; F3 covers only records that must PRECEDE an action, FORKED is written after the fork); U1 lists FORKED as a 'later-lifecycle' record although it precedes REGISTERED | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-F3` | Q3 | completed run without FORKED, contiguous seq, counts agree — as CE-F2 but the run completed | 1 RUN_START · 2 INTENT n1 · 3 REGISTERED n1 pid=200 st=5000 · 4 RELEASED n1 · 5 DEAD n1 basis · 6 RUN_END confirmed=true | completed_run=True, parse_clean=True, mem_count=6, parsed_count=6, writer_seq=6, fork_calls=1 | **FAIL** | **FAIL**：F4 (required record absent, completed, parse_clean) | **FAIL** | NO ISSUE |
| `CE-G1` | Q4 | registry append failed (ENOSPC) for RELEASED, then RUN_END(false) written — bench I/O failure: RegWriter.write increments seq BEFORE the append, so a failed append consumes a seq number | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 6 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=5, parsed_count=5, writer_seq=6, fork_calls=1, release_byte_written=False | **BLOCKED** | **FAIL**：F2 'a gap in seq' with parse_clean (the failed append wrote nothing) -> FAIL | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-G2` | Q4 | completed run, DEAD and RUN_END lines lost at the end of the file — clean-boundary tail loss after the run | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 | completed_run=True, parse_clean=True, mem_count=7, parsed_count=5, writer_seq=7, fork_calls=1 | **BLOCKED** | **FAIL**：F4 (completed, parse_clean, DEAD/RUN_END absent) -> FAIL | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-G3` | Q4 | RUN_START line lost at the head — clean-boundary head loss | 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RELEASED n1 · 6 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=6, parsed_count=5, writer_seq=6, fork_calls=1, release_byte_written=True | **BLOCKED** | **FAIL**：F2 gap (first seq is 2) | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-H1` | Q4 | early stop before the fork: only RUN_START and RUN_END(false) — e.g. an exception while installing the guard | 1 RUN_START · 2 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=2, parsed_count=2, writer_seq=2, fork_calls=0 | **BLOCKED** | **UNDEFINED -> BLOCKED**：U1's list of tolerated missing records omits INTENT (and RUN_START); F3 needs fork_calls >= 1; the exhaustiveness sentence resolves it to BLOCKED | **BLOCKED** | DOCUMENTATION ONLY |
| `CE-H2` | Q4 | empty registry file, early stop — exception before the first write | （空文件） | completed_run=False, parse_clean=True, mem_count=0, parsed_count=0, writer_seq=0, fork_calls=0 | **BLOCKED** | **UNDEFINED -> BLOCKED**：readable empty file is neither 'missing' nor 'torn' (parse_reg: lines=[b''] -> torn False), so U2 does not name it; sentence resolves | **BLOCKED** | DOCUMENTATION ONLY |
| `CE-H3` | Q4 | RUN_END(false) without RUN_START, contiguous seq, counts agree — writer defect (RUN_START is always the first write, g0_run.py) | 1 INTENT n1 · 2 FORKED n1 pid=200 · 3 REGISTERED n1 pid=200 st=5000 · 4 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=4, parsed_count=4, writer_seq=4, fork_calls=1 | **FAIL (recommended)** | **UNDEFINED -> BLOCKED**：I12/I16 (RUN_START_COUNT, RUN_END_WITHOUT_RUN_START) are not mapped by any F rule; F4 needs a completed run | **BLOCKED** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-T1` | Q4 | child INTENT whose creator is not yet registered (early stop) — ticket granted to an unregistered creator; unreachable in G0 (spec children=[]), listed for rule completeness (integrity issue I10) | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 INTENT n2 creator=n1 · 5 REGISTERED n1 pid=200 st=5000 · 6 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=6, parsed_count=6, writer_seq=6, fork_calls=1 | **FAIL** | **UNDEFINED -> BLOCKED**：I10 (registry.py:242-246) is not mapped by any C03 rule; C11 owns the one-node budget but is UNEVALUABLE after an early stop (limitation L-1) | **FAIL** | SEMANTIC CHANGE REQUIRES V3 |
| `CE-P1` | control | RELEASED has a smaller seq than REGISTERED (both present) — order violation | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 RELEASED n1 · 5 REGISTERED n1 pid=200 st=5000 | completed_run=False, parse_clean=True, mem_count=5, parsed_count=5, writer_seq=5, fork_calls=1 | **FAIL** | **FAIL**：F1 | **FAIL** | NO ISSUE |
| `CE-P2` | control | duplicate INTENT — positive violation | 1 RUN_START · 2 INTENT n1 · 3 INTENT n1 | completed_run=False, parse_clean=True, mem_count=3, parsed_count=3, writer_seq=3, fork_calls=1 | **FAIL** | **FAIL**：F1 (more than one INTENT) | **BLOCKED** | NO ISSUE |
| `CE-P3` | control | record after RUN_END — positive violation | 1 RUN_START · 2 INTENT n1 · 3 RUN_END confirmed=false · 4 FORKED n1 pid=200 | completed_run=False, parse_clean=True, mem_count=4, parsed_count=4, writer_seq=4, fork_calls=1 | **FAIL** | **FAIL**：F1 | **BLOCKED** | NO ISSUE |
| `CE-P4` | control | early stop; release byte written and child acted, RELEASED record absent; registry corroborated — release before the durable RELEASED record | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 · 5 RUN_END confirmed=false | completed_run=False, parse_clean=True, mem_count=5, parsed_count=5, writer_seq=5, fork_calls=1, release_byte_written=True, child_acted=True | **FAIL** | **FAIL**：F3 | **BLOCKED** | NO ISSUE |
| `CE-P5` | control | early stop, only DEAD and RUN_END missing at the tail, no release — stopped before release | 1 RUN_START · 2 INTENT n1 · 3 FORKED n1 pid=200 · 4 REGISTERED n1 pid=200 st=5000 | completed_run=False, parse_clean=True, mem_count=4, parsed_count=4, writer_seq=4, fork_calls=1, release_byte_written=False | **BLOCKED** | **BLOCKED**：U1 | **BLOCKED** | NO ISSUE |

---

## 5. 建议修订范围（供交叉审核；**不创建 V3**）

**范围原则：** 只动 C03（规则）与 C16（证据键名）；`G0-C01…C17` 编号不变；其余检查不动；V1/V2 文件原样保留；新文件先单独冻结提交，再改实现。

| 编号 | 修订 | 解决 |
|---|---|---|
| S1 | 定义 `registry_corroborated` = `parse_clean` ∧ `len(parsed) == reg_memory_count` ∧ `reg_writer_seq == reg_memory_count`；新增证据键 `reg_memory_count`、`reg_writer_seq`（在最后一次写入之后、解析之前取） | F-15、F-16.5 |
| S2 | F1（正面违规）增加：同一节点出现多于一个 FORKED / REGISTERED / RELEASED；FORKED / REGISTERED / INTENT / DEAD 字段类型错误（pid、starttime 为 `int` 且非 `bool`，node_id 为非空 `str`）；创建者未先登记（I10）；多于一个节点 | F-16.1、F-16.2 |
| S3 | 新增「洞」规则（仅 `registry_corroborated`）：同一节点生命周期里较早的记录缺失而较晚的记录存在，或 RUN_START / INTENT 缺失而其后有记录 ⇒ FAIL；取代「seq 空洞」「前置缺失」「孤儿」三条缺失类文字 | F-16.3、F-16.4 |
| S4 | 未被佐证（空洞、计数不符、`writer_seq` 不符、行边界丢失）⇒ U2 | F-16.5、F-15 |
| S5 | U1 收窄为「尾部缺失」（`DEAD`、`RUN_END`、失败登记的 `ABORTED`），并把「fork 之前停止（`fork_calls = 0`）时缺 `INTENT` / `RUN_START`」「可读的空文件」列入；删除 FORKED / REGISTERED / RELEASED；增加显式默认规则「未匹配 ⇒ UNEVALUABLE」 | F-16.6、CE-H1/H2 |
| S6 | F3 保持（独立证据证明动作已发生而前置记录缺失），仅在 `registry_corroborated` 时有效 | CE-P4 |
| S7 | **政策点**：被佐证的「缺 FORKED 而有 REGISTERED」（CE-F2）判 FAIL 还是 BLOCKED——需负责人 / 审核者决定并写明 | F-16.3 |
| S8 | C16：把必需证据的**确切键名**写入判据，并要求每条路径（含异常路径）都写入 | F-17.1 |
| S9 | C02 / C05 / C06：要么增加证据键（`auth_consumed_mono < INTENT.mono`；`S1.mono − REGISTERED.mono ≥ hold`）并成为可检验条件，要么明确它们只是程序义务、不属于该检查的判定 | F-17.2 |
| S10 | （可选，独立决定）F-14：C05 / C06 / C11 等多子条件检查按子条件独立评估 | L-1 |

**不需要 V3 的部分（DOCUMENTATION ONLY）**：C01、C02、C05、C06、C09、C13、C15 的文字补充；穷尽句的措辞；空文件 / 缺 INTENT 的提前中止——可在实现设计文档中固定。

## 6. 现 `g0_judge.py` 与 V2 字面、应有判定的关系（为什么不能「照着实现改」）

* 现 judge 比 V2 字面**严**的地方：重复记录、字段错误在**完整运行**上判 FAIL（V2 字面 PASS）。
* 现 judge 比 V2 字面**松**的地方：提前中止分支只调用 `check_order`，对 `lifecycle_issues` 的正面违规（重复 INTENT、`RUN_END` 之后有记录）以及独立证据（放行字节已写）**看不见**，给出 BLOCKED（CE-P2/P3/P4、D5、M2、M3）。
* 现 judge 与 V2 字面**同样错**的地方：对 CE-G2 判 FAIL（完整运行丢尾部）。
* 因此既不能把现 judge 当作 V2 的参照实现，也不应通过修补实现来使两者「看起来一致」：问题在判据文字。

## 7. 本阶段未做

没有修改 V1 / V2、没有创建 V3、没有修改 `g0_run.py` / `g0_judge.py` / `g0_auth.py`、台架、E1-A 原预注册、R3、CPU-001/002、Parcae；没有运行测试、`integrity_issues()` 或任何进程；没有创建 `AUTHORIZATION_E1A_GATE_G0.json` 或 `evidence/`。
