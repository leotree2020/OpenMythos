# R2 Gate O Failure 001 — 测试前置 Gate N 污染了 Gate O 的 Shard 调用计数器

**时间：2026-10-17。证据：用户 Codespaces 提供的终端日志。** 首次拉取 Gate O 研究代码 fast-forward `04e639c..a538079` 成功。工作区原有未跟踪 `SETUP_LEOTREE2020.md`、`mini_mythos_leotree2020_overlay_v04.zip`，不属于本次修复，也未被删除、修改或加入提交。

## 首次实测结果（必须保留）

```text
Ran 10 tests in 0.013s
FAILED (failures=1)
test_actual_source_paths_exact_native_and_twice ... FAIL
File ".../test_r2_pr27_real_hf_file_shard_mapping.py", line 120
  self.assertEqual(len(self.ds.calls), 4)
AssertionError: 8 != 4
```

另 9 项通过；本次用户**没有运行全量单元测试，也没有运行真实 Gate O freeze 或 verify**。所以本次 Gate O NOT VERIFIED，不能把其余 9 项通过表述成 Gate O PASS。

## 直接根因（已通过静态代码检查）

`GateOTests.setUp()` 为构造上游验证的 `gate_n` 报告调用 `prev.build_report(self.ds, ...)`；`prev.build_report` 内部 `inspect_runtime_dataset` 在**同一个 `self.ds`** 上执行四次 `.shard` 子视图操作，令 `self.ds.calls` 先增长至 4。然后 Gate O 测试函数 `observed_mapping(self.ds,...)` 又对该对象执行四次 `.shard`，总计 8。因此最初断言 `len(self.ds.calls) == 4` 把准备阶段也算了进去。

这是**单元测试夹具（fixture）状态污染**，不是已经观察到真实 HF Parquet 正文缺失，也不影响之前 Gate N 的 214/214 PASS。

## 候选修复（GitHub 已提交，仍待用户重测）

在 `research/mini_mythos/tests/test_r2_pr27_real_hf_file_shard_mapping.py` 的 `setUp()` 中先创建**独立**的 `gate_n_source = FakeDataset(self.paths)`，再通过 `prev.build_report(gate_n_source,...)` 生成前置报告。这样 Gate O 的 `self.ds` 不被 Gate N 的 4 次元数据操作污染，原先 `len(self.ds.calls) == 4` 的严格断言**不变**。

新增测试 `test_gate_n_prerequisite_does_not_pollute_gate_o_probe`，验证 `self.ds.calls == []` 且 Gate N 的模拟来源条件仍然成立。因此本轮 Gate O 由 10 项增至 **11 项**，全量测试理论上由旧的 Gate N 基线 214 项增至 **225 项**。**225/225 尚未运行，不得提前宣称通过。**

涉及 Commit：`d33c1adf83df7194dc45e2c4d4578e35836d2733`（隔离测试夹具）、`cc031019c768747d02547b90d17e3dddec9f09d6`（新增防回归测试）。仅修改 `research/mini_mythos/tests`，没有修改原版 PR27 或 Gate I/M/N 的冻结数据、模型、脚本。

## Codespaces 重测

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_real_hf_file_shard_mapping.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py freeze --repo .
python research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py verify --repo .
```

仅当前两段测试都通过才继续执行真实 metadata-only Freeze/Verify。如果 Gate O 的真实 Hugging Face 私有结构与当前设计不符，应当保留原始报错，FAIL CLOSED，禁止因追求 PASS 擅自调整不可变来源或模拟输出。
