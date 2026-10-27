# F3B-D1-A-CPU-003 E1-A — 检查点：G0 V2 判据冻结 G0-V2-SPEC-001

**状态：`G0 V2 SPEC FROZEN / IMPLEMENTATION NOT CONFORMING / G0 PURE TESTS NOT TESTED / G0 REAL PROCESS NOT AUTHORIZED / BV NOT AUTHORIZED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED`**

任务：`F3B-D1-A-CPU-003-E1A-G0-V2-SPEC-001`。审核基准 `e0ffef9b4a81e9d11266a09475271f4c57669c8d`。
**没有修改** `g0_run.py` / `g0_judge.py` / `g0_auth.py`、台架、E1-A 原预注册、R3、CPU-001/002、Parcae；**没有运行** 46 个纯逻辑测试、G0、BV、E1-A、`test_e1a_gate.py` 或任何进程；**没有创建** `AUTHORIZATION_E1A_GATE_G0.json`，也没有创建 `evidence/`。只执行了 JSON/正则/哈希一致性检查、静态审计、AST 解析与 Git 检查。

## 1. 提交顺序（先冻结，后文档）

| 顺序 | 提交 | 内容 |
|---|---|---|
| 1 | `e287b952124e8aaf22098e1957c61da5359a5e2c` | V1 冻结（`g0_criteria_v1.json`、`E1A_GATE_G0_PREREG.md`、测试清单）——**此后字节不变**（`git log` 只有这一个提交触及两个 V1 文件） |
| 2 | `e0ffef9b4a81e9d11266a09475271f4c57669c8d` | 上一轮审核基准 |
| 3 | ``77750c38998489c3093f80439b52c3c5269db059`` | **V2 冻结提交，只含 3 个文件**：`g0_criteria_v2.json`、`g0_criteria_v2.json.sha256`、`E1A_GATE_G0_PREREG_V2.md` |
| 4 | 本检查点所在提交 | 仅文档 / 审查记录 / 一致性检查工具与输出 / checkpoint，**不含**任何 G0 代码改动 |

## 2. V2 做了什么

* **C03（唯一语义改变）：** 有充分证据证明登记记录顺序或完整性违规 ⇒ **FAIL**（包括：登记表自身证明的违规；登记表缺记录但**独立于登记表的证据**证明相应动作已发生，例如已写放行字节却无 `RELEASED` 记录；完整运行却缺记录）。因超时 / 提前中止 / 登记表破损而证据不足 ⇒ **UNEVALUABLE → BLOCKED**。破损文件只保留「正面违规」（存在的记录自相违反），不信任「缺失类」推断。FAIL 规则先评估，提前中止**不会**掩盖已证明的违规。V1 的 C03 与 §3 第 8 步的矛盾在 V2 中明确写出，V1 未被重新解释（V1 下从未执行过任何运行）。
* **检查编号稳定：** `G0-C01…C17` 不增不拆不改名；**8 项 IDENTICAL**（C04 C07 C08 C10 C11 C12 C14 C17，文字逐字相同）、**8 项 CLARIFIED**（C01 C02 C05 C06 C09 C13 C15 C16，决策语义不变）、**1 项 MODIFIED**（C03）。完整映射表在 V2 预注册 §0 与 JSON 的 `v1_to_v2_mapping`。
* **六项文字偏差正式处理**（预注册 §9）：1 S1 保持期后拍 → §3 步骤 3、C05/C06；2 fork 前消耗授权 → §3 步骤 2、C02；3 预检先于建目录 → §3 步骤 1–2、C01；4 异常路径 `RUN_END(false)` → §3 步骤 8、C13/C03；5 令牌定义 → C01；6 C03 → 本次 MODIFIED。
* **一致性检查：** `tools/check_g0_v2_consistency.py`（只读 JSON/正则/SHA-256）逐项核对 JSON ↔ 文字 ↔ V1：17 个检查行、17 个映射行、规则 ID、偏差表、义务表、哈希引用，**0 不一致**；我另外用 4 种故意破坏的副本验证了它能报错（文字改动、失败类别改动、哈希引用改动、IDENTICAL 项被改）。输出 `g0_preflight_review/v2_consistency_check.txt`。

## 3. F-13（正式登记）

`g0_run.py:265` 的 `os.mkdir(run_dir)` 假定 `evidence/` 已存在；当前环境不存在，调用路径上无先行创建逻辑（证据 `g0_preflight_review/f13_call_path_trace.txt`）。后果：首次真实运行必然 `FileNotFoundError` → `main()` 找不到运行目录、不写摘要、返回 3（BLOCKED）；授权标记尚未创建，所以**不会被消耗**，也没有进程被启动——不会误报 PASS，但会白跑一次且没有证据文件。最小修复（不是 `makedirs(exist_ok=True)`）：`ensure_dir` 只在不存在时非递归创建（0755），否则校验（真实目录、非符号链接、属当前有效 uid、组/其他不可写）并记录所有权；运行目录仍排他创建、不覆盖；创建失败 ⇒ BLOCKED，错误写 stderr，并在 `evidence/` 可用时排他创建 `g0_blocked_<run_id>.json`；绝不使用别的运行的目录。**本阶段只设计，不修改 `g0_run.py`。** 详见 `G0_NEXT_STAGE_FIX_DESIGN.md` §1。

## 4. 下一阶段修复清单（`g0_preflight_review/G0_NEXT_STAGE_FIX_DESIGN.md`）

F-8（回收等待有界：`WNOHANG` 轮询）、F-9（运行期总预算 `Budget`）、F-12（摘要只写入本进程创建的目录）、F-13（证据根目录所有权）、V2-C03（判定函数按规则实现），每项给出：文件级修改、预期结果、异常路径、最小测试案例；另含 C03 的 16 行测试矩阵、文件级修改清单与实施顺序。**均未实现。**

## 5. 完整 SHA-256

| 文件 | SHA-256 |
|---|---|
| `gate_g0/g0_criteria_v2.json` | `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438` |
| `gate_g0/E1A_GATE_G0_PREREG_V2.md` | `ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2` |
| `gate_g0/g0_criteria_v2.json.sha256`（文件本身） | `3fb256c9f4acb94929c62f3394bb8cdf307c3d632ea6889cac72c2bc89762aa7` |
| `gate_g0/g0_criteria_v1.json`（V1，未变） | `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2` |
| `gate_g0/E1A_GATE_G0_PREREG.md`（V1，未变） | `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb` |
| E1-A 预注册 `prereg/e1_provability_table_v1.json` | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| `bench_code_sha256`（未变） | `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0` |
| `g0_code_sha256`（未变，当前实现仍绑定 V1 文件路径） | `29e1253bad1665c102819a7aa2a894878397e0e2d505ac761b2ce1271b47ddbd` |
| `g0_preflight_review/G0_NEXT_STAGE_FIX_DESIGN.md` | `df2ef695b9a188349913058b0cbea63cf7cd5fb86c7c106610ed49a609cf369c` |
| `g0_preflight_review/f13_call_path_trace.txt` | `838d94d2340d0c6bdec99172894b8f9e54ac19d0fff10ab84487b84622dcd0ee` |
| `tools/check_g0_v2_consistency.py` | `3af2088f1fac3f9f130377f55aebdc0eaaaffd617ddf10502ba62b327b064058` |
| `g0_preflight_review/v2_consistency_check.txt` | `a7ad0715fe5c4204993627692ed42d3f1f12cad7041431c3884f283c023b1239` |
| R3 / 决定记录 / 冻结记录前缀 | `66a656145fc203c7` / `6209602e7d51b1ae` / `e3bba6b0968101bf`；`D1_CODE_SHA256SUMS` 10/10 OK |

## 6. 未解决问题

1. **实现不符合 V2**（`g0_run.py` / `g0_judge.py` / `g0_auth.py` 仍是上一版：绑定 V1 文件、C03 旧逻辑、无 F-8/9/12/13 修复）。V2 预注册 §10 规定：实现并通过审核之前不得授权任何 G0 执行。
2. F-1（僵尸当已死，台架未改）、F-14（C03 之外检查的整项 UNEVALUABLE，限度 L-1）、F-15（C16 要求记录登记表内存记录数，但没有规则使用它）——请交叉审核者决定；若要改动判据文字，须走 V3，不得改 V2。
3. 46 个纯逻辑测试仍**未运行**；实现修改后测试数与合成证据都会变，须重新审计后再申请运行授权。
4. V2 的程序部分（目录创建、有界回收、运行期预算）描述的是**目标**行为；若审核者认为其中某项不应进入冻结文本，应在实施之前提出，否则只能走 V3。
5. Python 层守卫为零不证明内核路径安全；G0 PASS 将不是 G1/G2/G3、BV、E1-A 的证据。
6. `AUTHORIZATION_E1A_GATE_G0.json` 不存在；`evidence/` 不存在。

## 7. 下一条唯一指令

**将 V2 文件（`g0_criteria_v2.json`、`E1A_GATE_G0_PREREG_V2.md`）和修复设计（`G0_NEXT_STAGE_FIX_DESIGN.md`）交给 ChatGPT / Grok 交叉审核，待项目负责人授权实施。** 不自动修改 G0 实现，不运行 46 个纯逻辑测试，不创建 G0 执行授权文件。
