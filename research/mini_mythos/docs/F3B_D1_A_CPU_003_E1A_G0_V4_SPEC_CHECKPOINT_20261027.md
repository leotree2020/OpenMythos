# F3B-D1-A-CPU-003-E1A-G0-V4-SPEC-001 检查点

**状态：`G0 V4 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`。审核基准 HEAD `279eaaed1a62203abd9e2d30f0b2ab9ed302538e`（G0-V3-REVIEW-CLOSEOUT-001）。

## 1. 提交（顺序：先 V4 冻结，再审核报告与检查点）

| 顺序 | 完整 SHA | 内容 |
|---|---|---|
| 1 | `753b4609de831b49187b198a1832e1b08424ac88` | V4 冻结提交，**只含** `gate_g0/g0_criteria_v4.json`、`g0_criteria_v4.json.sha256`、`E1A_GATE_G0_PREREG_V4.md` |
| 2 | 见 `git log`（本检查点所在提交，仅文档 / 静态检查工具 / 案例数据） | 审核报告、案例数据、两个只读检查工具、检查输出、本检查点、`PROJECT_MAP.md` 追加块 |

## 2. 哈希（SHA-256）

| 文件 | SHA-256 | 状态 |
|---|---|---|
| `gate_g0/g0_criteria_v4.json` | `6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414` | **新，冻结** |
| `gate_g0/g0_criteria_v4.json.sha256`（文件本身） | `0a7cd1d01fded2008773de08f6d47f4328f7aa46e281b785222bce2e8d4ad4a9` | 新，冻结 |
| `gate_g0/E1A_GATE_G0_PREREG_V4.md` | `05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42` | 新，冻结 |
| `gate_g0/g0_criteria_v3.json` | `653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a` | 未变 |
| `gate_g0/E1A_GATE_G0_PREREG_V3.md` | `0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88` | 未变 |
| `gate_g0/g0_criteria_v2.json` | `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438` | 未变 |
| `gate_g0/E1A_GATE_G0_PREREG_V2.md` | `ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2` | 未变 |
| `gate_g0/g0_criteria_v1.json` | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` | 未变 |
| `gate_g0/E1A_GATE_G0_PREREG.md` | `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb` | 未变 |
| `gate_g0/g0_run.py` | `95bf60620b8958a3e734e7c475a71db58ef82b561553bdd91d8087ce92989c6a` | 未变（未修改） |
| `gate_g0/g0_judge.py` | `8c05a42a349475732c8daa4ee1dd15a17e20cba5a2a2dfda677910bf5b58cebb` | 未变（未修改） |
| `gate_g0/g0_auth.py` | `45a090ba0492ce55973c91bee4d2ba0f9e09218ec3e60ced109efd85d00f20e5` | 未变（未修改） |
| `prereg/e1_provability_table_v1.json`（E1-A 原预注册） | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` | 未变 |
| `g0_preflight_review/g0_v4_cases.json` | `714dec878ee20a62c919f9c75eab4109364e8a5bfc676085ccaff778cb7f8d0a` | 新 |
| `g0_preflight_review/G0_V4_SPEC_REVIEW.md` | `438d2cb1801e50d4e7950c97b7c952e353e839814a4f6354dd47c6343272c355` | 新 |
| `tools/check_g0_v4_consistency.py` | `af892e373332fd00735cfbbb9f34c46b0426bbd6560d2e1d23c3e2745c5aa217` | 新 |
| `tools/check_g0_v4_matrix.py` | `c2795cff62043b9ea90905cc07a3dc64481f6ddeffe62519de16c991e46638c3` | 新 |
| `g0_preflight_review/v4_consistency_check.txt` | `724d90bfbe86ddc7445d0c8b5d11806e1b46814b69e3ae99f89e371bdb133186` | 新（输出） |
| `g0_preflight_review/v4_matrix_check.txt` | `acd9fb0999e212fdba32d60706d80f188cbc01c282cbea0e983a009fbde1ea10` | 新（输出） |

（路径均相对 `research/mini_mythos/a_predicate_003/`。）

## 3. 变更范围

* 新增（冻结）：V4 判据 JSON、其 `.sha256`、V4 预注册文字。
* 新增（文档 / 工具 / 数据）：审核报告、67 个静态案例（含 15 个流水线案例）、两个只读静态检查工具及其输出、本检查点、`PROJECT_MAP.md` 追加块。
* **未修改：** V1/V2/V3 及其 `.sha256`、`g0_run.py`、`g0_judge.py`、`g0_auth.py`、`bench/`、既有测试、E1-A 原预注册、R3、CPU-001/002、Parcae 上游。
* **未创建：** 任何执行授权文件、`evidence/` 目录。

## 4. V4 内容概要

* C01–C17 编号稳定：10 项与 V3 完全相同，7 项修改（C03、C04、C05、C07、C11、C13、C16）。
* F-20：`disk_faithful` 改为整条规范化 JSON 记录逐条比较；M-2：不保真 ⇒ C04/C05/C11/C13 UNEVALUABLE，C03 附保真报告；FAIL 规则不依赖持久副本，磁盘损坏既不造成错误 PASS 也不造成错误 FAIL（FID-A…F）。
* F-21：证据流水线 P0–P7（严格序列化、排他创建、fsync、读回核对、只对读回证据裁决、摘要保存核对）；保存 / 读回 / 摘要失败一律 BLOCKED、退出码 3，stderr 标记未保存状态；15 个流水线失败案例。
* F-22：C03/C07 条件规则表与需求表（`writer_clean` 单一陈述）；`release_attempt` / `release_write_ok` / `gate_passed` 分开定义；append 失败或序号缺口 ⇒ BLOCKED；`gate_pass_proven` ⇒ FAIL（C03-F3c）；无法确认或见证矛盾 ⇒ BLOCKED；FAIL 仅表示 G0 台架 / 协议失败，不表示 Mythos 架构失败。
* DD-1…DD-5 及 M-2、F3 方案：登记为 `PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL`，区分 `stated`（任务文本明确）与 `derived`（我形式化，待审核者确认：DD-1、DD-3、DD-4）。

## 5. 验收状态

| 条件 | 状态 |
|---|---|
| V4 JSON ↔ 预注册文字一致 | 满足（`check_g0_v4_consistency.py`：0 不一致；17 检查行、17 映射行、91 证据字段、8 流水线阶段、9 条决策） |
| V1/V2/V3 哈希不变 | 满足 |
| C01–C17 与 V3→V4 映射完整 | 满足 |
| FID-A…E（另含 FID-F）、F3 条件案例、流水线失败案例有明确结果 | 满足 |
| 51 个 V3 案例有 V4 判定或迁移说明 | 满足（3 个裁决改变：CE-R6 FAIL→BLOCKED〔DD-3〕、CE-R7 FAIL→BLOCKED、CE-R8b FAIL→BLOCKED〔DD-4〕）；`check_g0_v4_matrix.py`：67 案例，0 不一致；FAIL 29 / BLOCKED 37 / PASS 1 |
| 无已知规则矛盾 | 满足（残余风险见审核报告 §8） |
| 审核意见与负责人决策可追溯 | 满足，含声明的局限（见 §6.1） |
| Git 顺序：先冻结、后报告 | 满足 |

全部为**静态设计审核**，不是测试 PASS。未运行任何纯逻辑测试、真实 G0、BV、E1-A、GPU 或训练。

## 6. 未解决问题

1. ChatGPT / Grok 的审核原文不在本会话中；V4 依据任务文本。`derived` 的格（DD-1 账本取全记录、DD-3 写入失败而子进程仍通过 ⇒ BLOCKED、DD-4 无尝试记录而子进程通过 ⇒ BLOCKED）须由审核者确认；如不同意，通过 V5 修订，V4 不再修改。
2. 所有案例由手工推导；检查工具不检验 G0 代码，也不能证明推导前提真实。
3. 当前 `g0_run.py` / `g0_judge.py` / `g0_auth.py` 未实现 V4（仍绑定 V1），46 个既有纯逻辑测试未运行且将随实现改变。**G0 不得在实现并另行授权前执行。**
4. 完整记录保真的误报风险（JSON 往返改变的值）应在首次受控运行中验证。
5. 沿用的局限：L-1（C05 不保真时整项 UNEVALUABLE）、L-3（程序性义务不被判定函数验证）、L-4（fsync 不证明介质持久化）、F-1、F-14。

## 7. 下一条唯一指令

将 V4 冻结文件（`g0_criteria_v4.json`、`.sha256`、`E1A_GATE_G0_PREREG_V4.md`）交给 ChatGPT / Grok 审核；审核通过后再申请 **G0 工具实现授权**。本轮不延伸到下一阶段。
