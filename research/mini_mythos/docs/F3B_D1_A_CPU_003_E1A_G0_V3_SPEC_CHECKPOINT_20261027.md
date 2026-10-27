# F3B-D1-A-CPU-003 E1-A — 检查点：G0 V3 最小语义修订 G0-V3-SPEC-001

**状态：`G0 V3 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / G0 PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED / GROK REVIEW PENDING`**（另：BV NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED）

任务：`F3B-D1-A-CPU-003-E1A-G0-V3-SPEC-001`。审核基准 `ab66d183752eb8b74f38225a5ebc1187dd2da565`。
**没有修改** V1/V2、`g0_run.py` / `g0_judge.py` / `g0_auth.py`、`bench/`、既有测试；**没有运行**纯逻辑测试、真实 G0、BV、E1-A、GPU 或训练；**没有创建**执行授权文件或 `evidence/`。只执行了 JSON/正则/哈希一致性检查、静态审计与 Git 检查。反例结论是手工推导的**静态反例（设计审核），不是测试 PASS**。

## 1. 提交顺序（先冻结，后文档）

| 顺序 | 提交 | 内容 |
|---|---|---|
| 1 | `e287b952124e8aaf22098e1957c61da5359a5e2c` | V1 冻结（未动） |
| 2 | `77750c38998489c3093f80439b52c3c5269db059` | V2 冻结（未动） |
| 3 | `ab66d183752eb8b74f38225a5ebc1187dd2da565` | 审核基准（V2 语义审查） |
| 4 | `7c4b99c581b306700fb6363abf417bc4b17127ea` | **V3 冻结提交，只含 3 个文件**：`g0_criteria_v3.json`、`g0_criteria_v3.json.sha256`、`E1A_GATE_G0_PREREG_V3.md` |
| 5 | 包含本文件的提交 | 审查报告、反例矩阵、两个只读检查工具及其输出、本检查点、`PROJECT_MAP` 追加块；**不含**任何代码 / 判据 / 测试改动 |

## 2. V3 做了什么（详见 `g0_preflight_review/G0_V3_SPEC_REVIEW.md`）

* **编号稳定：** `G0-C01…C17` 不增不拆不改名；**14 项与 V2 逐字相同，3 项 MODIFIED：C03、C07、C16**。完整 V2→V3 映射表在预注册 §0 与 JSON `v2_to_v3_mapping`。
* **C03：** 见证模型——账本（写入器自己成功追加的记录）+ 独立证据（守卫 / 子进程）判违规，持久副本只做保真检查；**seq 空洞从不单独成为 FAIL 证明**；重复 FORKED / REGISTERED / RELEASED、字段损坏、多节点 ⇒ FAIL；「洞」规则需要写入器无失败且无外来行；已佐证的 REGISTERED 缺 FORKED ⇒ FAIL（负责人政策），完整性无法证明 ⇒ BLOCKED；追加失败 / 持久副本损坏或外来行 / 提前中止且无违规证明 ⇒ BLOCKED；损坏只压制依赖被损坏见证的规则，FAIL 不无条件优先。
* **C07（F-18）：** 放行「尝试」「成功写入」「通过门控」是三个独立事实；写入前时间戳不再被当作写入证明；写入失败而子进程仍通过 ⇒ FAIL；失败 / 成功写入但子进程没通过 ⇒ BLOCKED。
* **C16：** `evidence_schema`（`e1a-gate-g0-evidence-3`，91 个字段）给出字段路径、类型、可否 null、使用者；在读回的 JSON 类型上、先于所有检查验证；只符合 V2 的证据在 V3 下 C16 失败 ⇒ BLOCKED（PASS→BLOCKED，已标记）。
* **FAIL 归因：** 每个 FAIL 都是 **G0 台架 / 协议失败**，不是关于 Mythos 模型架构、R3 或 Parcae 的证据（`fail_scope`）。

## 3. 反例验证设计

51 个静态反例（23 个旧 + 28 个新：F-18 的 18 个、C03 边界 5 个、C16 的 5 个），每个给出输入、预期 C03 / C07 / C16 状态、最终裁决与证据可信度。FAIL 27 · BLOCKED 23 · PASS 1；可信度 HIGH 25 · MEDIUM 10 · INSUFFICIENT 16。23 个旧反例的 V3 裁决与 V2 审查定的「应有判定」一致（其中 15 个与 V2 字面不同）。`tools/check_g0_v3_matrix.py`：0 不一致（规则编号、状态 / 类别、算术聚合）。**这些是设计审核，不是测试 PASS。**

## 4. 完整 SHA-256

| 文件 | SHA-256 |
|---|---|
| `gate_g0/g0_criteria_v3.json` | `653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a` |
| `gate_g0/E1A_GATE_G0_PREREG_V3.md` | `0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88` |
| `gate_g0/g0_criteria_v3.json.sha256`（文件本身） | `34fb1f4e5904e45b759cd0b3098f5b4c03387127cd0844790570afbd45b47727` |
| `gate_g0/g0_criteria_v2.json`（V2，未变） | `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438` |
| `gate_g0/E1A_GATE_G0_PREREG_V2.md`（V2，未变） | `ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2` |
| `gate_g0/g0_criteria_v1.json`（V1，未变） | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` |
| `gate_g0/E1A_GATE_G0_PREREG.md`（V1，未变） | `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb` |
| E1-A 预注册 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`（未变） |
| `bench_code_sha256` / `g0_code_sha256`（均未变；当前实现仍绑定 V1 文件） | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0` / `29e1253bad1665c102819a7aa2a894878397e0e2d505ac761b2ce1271b47ddbd` |
| `g0_preflight_review/G0_V3_SPEC_REVIEW.md` | `18599c860a467b42e5927b39f2c1f2fbbfa37ddcc6d335b9e127ab87523a335a` |
| `g0_preflight_review/g0_v3_counterexamples.json` | `6b4c91f4b0262a032b4b730b0e6ff91d221cecf0daab36e7ea8dae5407627560` |
| `tools/check_g0_v3_consistency.py` | `e9054fa423df35ebf9924e0f9897969eff36c417a57e3707ca17a289b294aab4` |
| `tools/check_g0_v3_matrix.py` | `22cffd0d73e76070c990ceb412b33454a1328e9a17370e29a4b3f540347672fa` |
| `g0_preflight_review/v3_consistency_check.txt` / `v3_matrix_check.txt` | `4c369f66ba6c2e257f8a72b67fec265ec46a1e0cd167225a2bf1a840014e4d40` / `b9c72f14436554263ae61d31d5b6eb4a025161e6035bbc888aaa3a3f483c7a70` |
| R3 / 决定记录 / 冻结记录前缀；`D1_CODE_SHA256SUMS` | `66a656145fc203c7` / `6209602e7d51b1ae` / `e3bba6b0968101bf`；10/10 OK |

静态审计（台架默认 / `--dir gate_g0`）0 / 0 违规；V2 一致性检查工具重跑 0 不一致。

## 5. 双 AI 审核状态

* ChatGPT：项目负责人转述已独立审核 V2 语义审查并**同意需要 V3**；针对本 V3 文本的审核**尚未收到**。
* Grok：**GROK REVIEW PENDING**。
* **分歧：无法记录**（没有 Grok 报告）。**不得声称双 AI 已达成共识。**

## 6. 未解决问题

1. **GROK REVIEW PENDING**，且 ChatGPT 尚未审 V3 文本。
2. 需两位审核者裁决的设计点：DD-1（账本取全记录，而不是只记录数）、DD-2（已佐证缺 FORKED 而持久副本另有损坏 ⇒ 仍 FAIL）、DD-3（写入失败而子进程仍通过门控 ⇒ FAIL，MEDIUM）、DD-4（无尝试记录时，账本有无 RELEASED 决定 BLOCKED 或 FAIL）、DD-5（REGISTERED 追加失败而子进程仍通过 ⇒ FAIL）。
3. 沿用的限度：F-14（L-1，C05/C06/C11 整项 UNEVALUABLE）、F-19（L-2，C04/C05/C11/C13 仍读持久副本）、程序性义务不被判定函数验证（C02/C05/C06/C15）、保真检查只比较三元组、F-1（台架把僵尸当已死）。
4. 实现不符合 V3（`g0_run.py` 只记录写入前时间戳、无账本 / 证据模式 / 目录所有权 / 有界回收 / 运行期预算；`g0_judge.py` / `g0_auth.py` 绑定 V1 文件）；既有 46 个纯逻辑测试**未运行**且将随实现改变。
5. `C03-U4` 按构造不可达，仅为保险默认；反例矩阵是描述性字符串，实现阶段需转成结构化证据夹具。
6. `AUTHORIZATION_E1A_GATE_G0.json` 不存在；`evidence/` 不存在。

## 7. 下一阶段（须另行授权）的实现文件与测试范围

`gate_g0/g0_run.py`（F-18 守卫前后记录、账本与写入器序号、`evidence_schema`、目录所有权、有界回收、运行期预算、摘要写入条件与 `fail_scope`）、`gate_g0/g0_judge.py`（C03 / C07 / C16 V3 规则，从 V3 JSON 读 `evidence_schema`）、`gate_g0/g0_auth.py`（指向 V3）、`tests/test_g0_interlock_and_judge.py`（更新）、新增 `tests/test_g0_v3_judge.py`（51 案例表驱动 + 模式类型规则）与 `tests/test_g0_v3_fixes.py`（F-8 / F-9 / F-12 / F-13 / F-18）、`tools/static_audit.py` G0 配置与 `audit_g0_pure_tests.py` 扩展。测试全部为纯逻辑（注入假时钟 / 假 `os.write` / 假 `try_reap`），沿用 `guard_runner` 的 41 个原语陷阱；运行任何测试都需单独授权。详见报告 §7。

## 8. 下一条唯一指令

**将 V3 文件（`g0_criteria_v3.json`、`E1A_GATE_G0_PREREG_V3.md`）、`G0_V3_SPEC_REVIEW.md` 与 `g0_v3_counterexamples.json` 提交 ChatGPT 与 Grok 审核；在 Grok 报告到达并裁决 DD-1…DD-5 之前，不授权实现，不运行任何测试，不创建执行授权文件。**
