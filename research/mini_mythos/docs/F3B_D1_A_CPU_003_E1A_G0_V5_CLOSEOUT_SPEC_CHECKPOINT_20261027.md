# F3B-D1-A-CPU-003-E1A-G0-V5-CLOSEOUT-SPEC-001 检查点

**状态：`G0 V5 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED`**

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`。审核基准 HEAD `d127ec58c0adc90d11fb7fc59240632fc4e36d5b`（G0-V4-SPEC-001）。

## 1. 提交（顺序：先 V5 冻结，再反例矩阵 / 一致性审查 / 映射 / checkpoint）

| 顺序 | 完整 SHA | 内容 |
|---|---|---|
| 1 | `8530ba5ca8a211f4d9f6e490b874e3b8b0af7906` | V5 冻结提交，**只含** `gate_g0/g0_criteria_v5.json`、`g0_criteria_v5.json.sha256`、`E1A_GATE_G0_PREREG_V5.md` |
| 2 | 见 `git log`（本检查点所在提交，仅文档 / 静态检查工具 / 案例数据） | 审核报告、案例数据、两个只读静态检查工具及其输出、本检查点、`PROJECT_MAP.md` 追加块 |

## 2. 哈希（SHA-256；路径相对 `research/mini_mythos/a_predicate_003/`）

| 文件 | SHA-256 | 状态 |
|---|---|---|
| `gate_g0/g0_criteria_v5.json` | `d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821` | **新，冻结** |
| `gate_g0/g0_criteria_v5.json.sha256`（文件本身） | `fe9515b7d645c53a8ed358dc2f8da4ad8853c15023b44b720fc1d2be9edad15c` | 新，冻结 |
| `gate_g0/E1A_GATE_G0_PREREG_V5.md` | `8338f4a0e20e37ad791d35eb876aca23f3e86e6f16fa9e2d84fd4ac82ef6e25c` | 新，冻结 |
| `gate_g0/g0_criteria_v4.json` | `6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414` | 未变 |
| `gate_g0/E1A_GATE_G0_PREREG_V4.md` | `05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42` | 未变 |
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
| `g0_preflight_review/g0_v5_cases.json` | `8e3628d0ab492de2c0085514c53500f8be96b5563a118399b3fff99ca6573d95` | 新 |
| `g0_preflight_review/G0_V5_CLOSEOUT_REVIEW.md` | `e7f0d5cea7564e9cf89c39dbe20e0d38a3b6c14c6a2f98d388ca18e7c425c224` | 新 |
| `tools/check_g0_v5_consistency.py` | `ddd17fd9307b3ca42be0c10b03621c3b164fd83806ed773c6cc5156b417d23ac` | 新 |
| `tools/check_g0_v5_closure_cases.py` | `65ed2fefebf0f9eeccd201f62917dff7efa6ffc640fe7a52f4ff44de6bcf8441` | 新 |
| `g0_preflight_review/v5_consistency_check.txt` | `15b2bc3e3bc95aaaa80aff589b52a34ea80c80c064e23b8561e67a2533d0fdb2` | 新（输出） |
| `g0_preflight_review/v5_closure_cases_check.txt` | `e18da525e47958ece2663cb1333335910f3f40e7fe7b5162ebb6a6678f0777a8` | 新（输出） |

## 3. 变更范围

* 新增（冻结）：V5 判据 JSON、其 `.sha256`、V5 预注册文字。
* 新增（文档 / 工具 / 数据）：审核报告（含 A–H 反例、38 个闭环案例、19 个 P6/P7 失败案例、7 个崩溃点、发布方案研究）、案例数据、两个只读静态检查工具及其输出、本检查点、`PROJECT_MAP.md` 追加块。
* **V5 相对 V4 实际改动的 24 个路径恰等于判据 `v4_to_v5_changes` 声明的路径**（检查工具核对）：P5/P6/P7 与流水线说明文字、C01、新增 `closure`、执行约束 / 裁决政策 / 裁决规则 / 限度 / 义务 / PASS 含义 / 修订政策、决策登记（追加 6 项）、V4→V5 映射与变更清单、证据模式两处说明文字、标识与取代关系。
* **未修改：** V1–V4 及其 `.sha256`、`g0_run.py`、`g0_judge.py`、`g0_auth.py`、`bench/`、既有测试、E1-A 原预注册、R3、CPU-001/002、Parcae 上游。
* **未创建：** 任何执行授权文件、`evidence/` 目录；未启动任何受测进程。

## 4. V5 内容概要

* **F-23：** 摘要文件存在不再等于结案。新增 `g0_closed.json`（schema `e1a-gate-g0-closed-1`，11 个字段：run_id、criteria_id / criteria_sha256、evidence_sha256 / 字节数、summary_sha256 / 字节数、recorded_verdict、recorded_exit_code、格式版本、`process_exit_proof=false`）。
* **原子排他发布（K0–K7）：** 临时文件 `O_EXCL` → fsync → 读回核对 → `os.link` 到最终名（目标已存在则 `EEXIST`，永不覆盖）→ 目录 fsync → 读回核对 → 以记录的退出码退出；临时名从不删除；不用 rename / replace / 直接创建最终文件。
* **失败与异常：** K1–K4 失败 ⇒ `G0-CLOSE-UNPUBLISHED`、退出码 3；K5–K7 或链接后的异常 ⇒ `G0-CLOSE-UNCONFIRMED`、退出码 3；已保存的文件永不被改动。报告规则：只有退出码 = 记录的退出码、无 `G0-CLOSE-*`、标记读回仍有效时，结果才是记录的裁决，否则报告 BLOCKED。
* **预检（C01）：** 事实 + 23 条机器可读规则 CL-01…CL-23；有效标记还必须绑定经哈希核对的摘要与证据，标准形式、run_id / criteria 一致，无人工处置文件；存活进程扫描**独立于**标记；任何不满足 ⇒ BLOCKED、拒绝新的真实 G0 运行；预检只读，不修复、不补全。
* 不变：C02–C17、C03 / C07 / C16 规则、DD-1…DD-5 及 V4 全部决策；FAIL 仅表示 G0 台架 / 协议失败。

## 5. 验收状态

| 条件 | 状态 |
|---|---|
| V5 判据与文字一致 | 满足（`check_g0_v5_consistency.py`：0 不一致；17 检查行、34 映射行、91 证据字段、23 条预检规则、决策 15 项） |
| 旧冻结文件不变 | 满足（V1–V4 共 8 个文件哈希核对） |
| F-23 反例（A–H）均有明确结果 | 满足（`check_g0_v5_closure_cases.py`：38 个闭环案例 = 32 BLOCKED + 6 CLOSED_OK；19 个流水线案例；7 个崩溃点；23 条规则全部被触发；0 不一致） |
| 没有新增 summary / closed 状态矛盾 | 满足（无**已知**矛盾；V4 的「摘要即结案」说法在 V5 中不残留，由检查工具核对；变异测试：一致性检查 7 种全部发现，案例检查 9 种中 8 种发现，第 9 种为设计上的无关改动） |
| Git 顺序：先冻结，后反例矩阵 / 审查 / checkpoint | 满足 |

全部为**静态设计审查**，不是测试 PASS，也不是实验结果。未运行任何纯逻辑测试、真实 G0、BV、E1-A、GPU 或训练。

## 6. 剩余限制与未解决问题

1. **勘误超出限定范围（请审核者裁定）：** V4 证据模式字段 `evidence_schema` 的说明写 `-3`，其余处写 `-4`；V5 改为 `-4`（V5-CH-6，仅文字）。若审核者认为不应放入 V5，可只撤销这一项。
2. ChatGPT / Grok 的审核原文不在本会话；`derived` 的决定 CL-A（`os.link`）、CL-B（已发布未确认的标记按文件判定、进程级结果报告 BLOCKED）、CL-D（任何记录的裁决都使运行结案）、CL-E（临时名不删除）需审核者确认；`stated`：F-23、CL-C。
3. 证据根所在文件系统须支持硬链接（L-7）；V5 不规定运行前探测。标记不是签名（L-6）；已保存的摘要 / 标记在 K5–K7 失败时可能记录 PASS 而该次结果是 BLOCKED（L-8，由报告规则处理）。
4. 案例由手工推导；检查工具不检验任何 G0 代码，也不证明推导前提（`link` / `fsync` 的语义）在目标文件系统上成立。
5. 当前 `g0_run.py` / `g0_judge.py` / `g0_auth.py` **不满足 V5**；46 个既有纯逻辑测试未运行且将随实现改变。**实现并另行授权之前不得执行任何 G0。**

## 7. 下一条唯一指令

将 V5 冻结文件（`g0_criteria_v5.json`、`.sha256`、`E1A_GATE_G0_PREREG_V5.md`）交给 ChatGPT / Grok 做**一次限定范围的最终审核**；通过后申请 **G0 工具实现授权**。本轮不延伸到下一阶段，不再无故扩大规范版本。
