# F3-B / D1 — 冻结后哨兵测试修正（F3B-D1-FREEZE-SENTINEL-CORRECTION）

**状态：`SENTINEL FIX CANDIDATE / FINAL FREEZE REGRESSION ACCEPTANCE = PENDING CODESPACES VALIDATION`**

追加式检查点；冻结提交 `9e257788c0510d5e263d5256d4bd3cebebdb8057` 和其原始失败日志保持不变，不重写历史。ChatGPT 独立审核裁决：批准限定范围的测试与状态文档修正，不批准任何算法变更。

## 1. 原始失败与根因

| 项 | 内容 |
|---|---|
| 失败测试 | `IdentityTimeoutEnv.test_identity_labels`（`tests/test_d1_selftest.py`） |
| 失败断言 | 最后一行 `self.assertNotEqual(jread(CFG)["status"], "FROZEN")`，注释「the shipped config cannot yield a formal run yet」 |
| 根因 | 这是冻结前阶段的**哨兵断言**：它的作用是在配置尚未冻结时防止误产生正式身份。项目负责人批准最终冻结、配置 `status` 设为 `FROZEN` 之后，该断言必然失败。**不是** Reader、Verifier 或 Driver 的缺陷 |
| 原始失败日志（保留，沙箱 Python 3.13.16） | `gate3_d1/final_freeze_logs/sandbox_impact_check_after_status_change.txt`（冻结时的完整套件：54 通过、1 跳过、1 失败）；本次另存精确测试的修复前输出 `gate3_d1/sentinel_fix_logs/before_fix_test_identity_labels_sandbox.txt`（`AssertionError: 'FROZEN' == 'FROZEN'`） |

## 2. 修改内容（仅此三处）

1. `tests/test_d1_selftest.py`，**一行**（`git diff --numstat`：1 增 1 删；`test_identity_labels` 未删除，其前面的身份分类断言未动，未加 skip）：

```
- self.assertNotEqual(jread(CFG)["status"], "FROZEN")      # the shipped config cannot yield a formal run yet
+ self.assertEqual(jread(CFG)["status"], "FROZEN")  # final config freeze is approved; formal D1 execution is not
```

2. `gate3_d1/D1_ENV_FREEZE.md`：只改与当前事实直接矛盾的状态描述——标题与状态段（配置现为 `FROZEN`、最终冻结已授权、原生环境证据验收 PASS、真实 D1 仍 `NOT TESTED / NOT AUTHORIZED`）、「Python」行的「候选」措辞、「依赖安装」行、「原生环境快照」行（BLOCKED → PASS）、「正式配置冻结」行（NOT AUTHORIZED → 已完成），并新增一行「冻结后最终回归验收：PENDING CODESPACES VALIDATION」。历史版本说明（早先的 3.13.16 已被取代）、算法规则、固定依赖、30 分钟限制和尚未完成的范围均保留。
3. `gate3_d1/D1_CODE_SHA256SUMS`：重新生成，只有这两个文件对应的行变化。

**未改动**：`D1_FROZEN_CONFIG.json`（SHA-256 仍为 `0d35dc21a4beca7c2f93fc11df6806ea7bc321d2376f52e1552863f19e7d7aaa`）、读取器、验证器、驱动器（含 `identity()`）、`d1_env_manifest.py`、`d1_selftest_data.py`、`requirements-d1.txt`、`README.md`、数据参数、真实实验授权、Codespaces 日志与证据、原始提案、Parcae、模型架构（相对 `9e257788` 无 diff）。

## 3. 清单（`D1_CODE_SHA256SUMS`，10 项，10/10 OK）

| 文件 | SHA-256 |
|---|---|
| `D1_FROZEN_CONFIG.json` | `0d35dc21a4beca7c2f93fc11df6806ea7bc321d2376f52e1552863f19e7d7aaa` |
| `d1_reader.py` | `ab37c9123defbc736632e4e03db23764646dbbedd5842bfec7d72e5556b38bc0` |
| `d1_verifier.py` | `80007f9b9d0cd0a1137922e7a2ab4f7c7c7dd3b4cc1a1d82e560833c201199b6` |
| `d1_driver.py` | `111c01f25c9ea8d9978f0ca979ab64e29f8961ddf8dac9277363a1b7c6f5a209` |
| `d1_env_manifest.py` | `3fde59f5718be6b68283e257991f218cb7c5814a8cc1595a5b9a9ec02b99a5d4` |
| `d1_selftest_data.py` | `e58174f935adeff6fbeb91e82f9f141b979b266a775290b586627ff53ad98285` |
| `requirements-d1.txt` | `55b4cb927dd2def5f5b62cc828cbb49ecaf74356ae00722ab2afca928bc585bf` |
| `D1_ENV_FREEZE.md` | `410c861e4c4a14830cabf3c3fc97f0008c1ee9571dcd582a2368fec9bb5cfd3d` |
| `README.md` | `023a5d9921566508014594591550a161373ff044b0272b9d6972a21099292315` |
| `tests/test_d1_selftest.py` | `f8f7300d429ae88fd336019280d324def1190bc6e4095ad4afd29f64a660fd68` |

## 4. 验收：预期、实际、结论

| 项 | 执行环境 | 预期 | 实际 | 结论 |
|---|---|---|---|---|
| 精确测试 `test_identity_labels`（修复前，冻结基准 `9e257788`） | Claude 沙箱，Python 3.13.16 | FAIL（证实根因） | `AssertionError: 'FROZEN' == 'FROZEN'` | 已复现 |
| 精确测试 `test_identity_labels`（修复后） | Claude 沙箱，Python 3.13.16 | PASS | `Ran 1 test … OK` | **PASS** |
| 完整 56 项合成回归（修复后） | Claude 沙箱，Python 3.13.16，tokenizers 0.23.3，pyarrow 26.0.0 | 55 PASS，1 SKIP（`RealModeCodePath`：补丁版本 ≠ 3.13.8 的设计门禁），0 FAIL，0 ERROR | `Ran 56 tests in 30.694s`，`OK (skipped=1)`；`test_identity_labels ... ok`；被跳过的正是 `test_real_mode_pipeline` | **PASS（仅沙箱层面）** |
| SHA-256 清单 | 沙箱 | 10/10；只有两行变化；配置哈希不变 | 10/10 OK；变化的恰是 `D1_ENV_FREEZE.md` 与 `tests/test_d1_selftest.py`；配置哈希不变 | PASS |
| 其他冻结文件 | 沙箱 | 相对 `9e257788` 无 diff | 无 diff | PASS |
| `git diff --check` | 沙箱 | 干净 | 干净 | PASS |
| **Codespaces 最终回归**（Python 3.13.8，期望 56 PASS / 0 SKIP / 0 FAIL / 0 ERROR，`test_identity_labels` 与 `test_real_mode_pipeline` 通过） | Codespaces | — | **尚未执行** | **NOT TESTED（PENDING CODESPACES VALIDATION）** |
| 真实 D1；R6 剩余、R7、T1–T6、数据获取完整性 | — | — | — | NOT TESTED / NOT AUTHORIZED |
| D2 / D3 | — | — | — | NOT TESTED |

沙箱日志：`gate3_d1/sentinel_fix_logs/after_fix_regression_sandbox_py31316.txt`。沙箱结果**不能**替代 Codespaces 结果，**不**宣布 56/56 PASS，**不**宣布本阶段 CLOSED。

依赖（沙箱，仅供对照）：Python 3.13.16、tokenizers 0.23.3、pyarrow 26.0.0。冻结的执行环境不变：Python 3.13.8、tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0。

## 5. Codespaces 回归：安全命令（由项目负责人在 Python 3.13.8 环境执行）

这些命令只运行合成测试：不下载、不联网、不拟合、不用 GPU；测试只在临时目录写文件。

```bash
cd /workspaces/OpenMythos-D1
git status --short                                  # 必须为空，否则先停下
git fetch origin d1-final-freeze-sentinel-fix-20261026
git checkout d1-final-freeze-sentinel-fix-20261026
git pull --ff-only
git rev-parse HEAD                                  # 必须等于最终报告里的修复提交 SHA
(cd research/mini_mythos/gate3_d1 && sha256sum -c D1_CODE_SHA256SUMS)   # 必须 10/10 OK
PY=/workspaces/.venvs/openmythos-d1-py3138/bin/python
"$PY" -c "import sys;print(sys.version)"            # 必须是 3.13.8
{ echo "# Codespaces regression $(date -u +%FT%TZ)"; echo "head: $(git rev-parse HEAD)";
  "$PY" -m unittest -v research/mini_mythos/tests/test_d1_selftest.py 2>&1; echo "unittest_exit: $?"; } \
  > research/mini_mythos/gate3_d1/sentinel_fix_logs/codespaces_regression_py3138.txt
grep -E "^Ran |^OK|^FAILED|skipped|test_identity_labels|test_real_mode_pipeline" research/mini_mythos/gate3_d1/sentinel_fix_logs/codespaces_regression_py3138.txt
```

通过标准：`Ran 56 tests`、`OK`（无 `skipped`）、`test_identity_labels ... ok`、`test_real_mode_pipeline ... ok`、`unittest_exit: 0`。把该日志文件提交到修复分支（或贴出内容），由审核方独立核对。

## 6. 下一条唯一研发指令

等待项目负责人回传 Codespaces CPU 合成回归结果，并交由 ChatGPT 与 Grok 交叉审核最终最小差异。在此之前：FINAL FREEZE REGRESSION ACCEPTANCE = PENDING CODESPACES VALIDATION；不得下载 WikiText、拟合 Tokenizer、执行真实 D1、训练、使用 GPU 或启动 D2/D3。
