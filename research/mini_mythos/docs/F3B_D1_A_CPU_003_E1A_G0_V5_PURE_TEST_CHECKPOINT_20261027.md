# F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001 检查点

**最终状态：`CPU TESTS PASS`（198 / 198；2 个实现缺陷已修复并回归）／ `REAL G0 NOT AUTHORIZED`**

基准 `33fb344253bebc6ba03531233955aa45ab99cbea`；分支 `d1-r3-a-cpu-003-e1a-g0-v5-impl-20261027`。测试与修复提交（最终测试对象）：`e623dd45da8c3811d6fbe6a1f3cea378fc00e0be`；验收报告、结果与本检查点在其后的提交中。

## 1. 结果摘要

* 198 个 CPU 测试（g1 91 · g2 66 · g3 27 · g4 补充 14）全部 PASS，两次最终运行逐测试一致；进程安全哨兵触发 0 次；无 fork、无信号、无外部进程、无 GPU；`evidence/` 与授权文件不存在。
* 变异检查：10 / 10 种对实现的故意破坏被测试发现。
* 本阶段发现并修复的实现缺陷：**D-1**（启动异常泄漏为退出码 1 ⇒ `main` 包装器，一律 3，拒绝 2）；**D-2**（格式损坏的放行 / fork 记录产生错误 FAIL ⇒ 见证不可用，C07 UNEVALUABLE，C03 F3 不触发）。测试自身缺陷 T-0…T-3 已修正。每次失败的输入、预期、实际、环境、SHA、状态见 `g0_v5_pure_test_results/G0_V5_PURE_TEST_REPORT.md` §3。
* V1–V5 冻结判据、`bench/`、Parcae、R3、CPU-001/002、既有 `test_e1a_*.py` 未修改；未改变任何模型架构。

## 2. 哈希（SHA-256；路径相对 `research/mini_mythos/a_predicate_003/`）

| 文件 | SHA-256 |
|---|---|
| `gate_g0/g0_judge.py`（D-2 修复后） | `a52b0214343ae1125e8baaa4725ec8b38693c5e6795ced57682c7df8274a1e1f` |
| `gate_g0/g0_run.py`（D-1 修复后） | `6521380f3b3e1cf7f298db54bd3c14c064b2382e427670a02cbc950ae6992fad` |
| `gate_g0/g0_auth.py`（未变） | `15899a2e6cca5172b9355696b07afbc0e7a411797041198b9f936276f23e0cab` |
| `tools/run_g0_v5_cpu_tests.py` | `8ba845702e7257c30e491fb85be6b257c0cbc2995c452aee8d43068f2085a670` |
| `tests/test_g0_v5_supplement.py` | `3a363c207c911e8d60e87ba2120ca07977c0c2583fd9a87d1ebd6dcdbb492935` |
| `g0_v5_pure_test_results/final_run1.json` | `0fa50456909df77d698e852b385023aad1cfbe761d5e8abb7d6a874072f766bb` |
| `g0_v5_pure_test_results/final_run2.json` | `73759e7ff9196f46b44100db067bf6271eaa95e777e784499fd618b1e73e45bf` |
| `g0_v5_pure_test_results/G0_V5_PURE_TEST_REPORT.md` | `a309a43e99cf77235db1a575317d4eaef07b5ee000d235cb39c0193fa281e99a` |
| `gate_g0/g0_criteria_v5.json`（冻结，未变） | `d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821` |
| `gate_g0/E1A_GATE_G0_PREREG_V5.md`（冻结，未变） | `8338f4a0e20e37ad791d35eb876aca23f3e86e6f16fa9e2d84fd4ac82ef6e25c` |

## 3. 未解决 / 未验证

1. B-1 / B-2（规格裁定）仍待审核者；B-3：`pidfd`、真实 `fork`、`/proc` 快照、`run()` 全程、观察者与子进程交互**从未被执行**，`CPU TESTS PASS` 不覆盖它们。
2. 流水线耐久性（L-4）、标记不是签名（L-6）、需硬链接文件系统（L-7）沿用。

## 4. 下一条唯一指令

将本分支交给 ChatGPT / Grok 审核；通过后，就**真实 G0 执行**向项目负责人另行申请授权。在得到明确授权之前不创建授权文件、不运行 `g0_run.py --execute`。
