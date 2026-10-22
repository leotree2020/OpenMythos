# P1-B CI 验收记录

本文件记录 PR #4（P1-B）在 GitHub Actions 上的验收过程。P1-B 的数值检查结果见 `P1_B_RESULT.md`，本文件不改动其内容。

## 当前状态

| 项目 | 状态 | 依据 |
|---|---|---|
| P1-B 六项必需检查 | PASS | commit `b3b5053846e257aadc4d313f6998ae9798540f07`，`P1_B_RESULT.md` |
| P1-B 复跑一致性 | PASS | 第二个进程 + fresh clone 复跑，4 个 JSON 完全一致 |
| 仓库 CI `offline-tests`（PR #4） | 待重跑 | 首次失败原因是既有 workflow 缺 `datasets`，与 P1-B 无关；修复见 PR #5 |
| 仓库 CI `upstream-smoke`（PR #4） | 待重跑 | 首次因 `offline-tests` 失败被跳过 |

PR #4 保持 Draft，不合并。

## 1. 首次失败：run 39771515620

- Run：https://github.com/leotree2020/OpenMythos/actions/runs/39771515620 （PR #4，head `b3b5053`，base `mini-mythos-research` @ `98a80dd`）
- `offline-tests`：Ran 236 tests，FAILED (errors=11)。11 个 ERROR 全部是 `ModuleNotFoundError: No module named 'datasets'`：
  - `test_r2_hf_worker_shard_pack`：6 个测试
  - `test_r2_pr27_double_shard_coverage`：`setUpClass` 失败，整类未执行
  - `test_r2_pr27_native_once_data_candidate`：模块导入失败（记为 1 个 `_FailedTest`）
  - `test_r2_pr27_os_worker_file_identity_replay`：3 个测试
- `upstream-smoke (gqa/mla)`：因 `needs: offline-tests` 被跳过，无日志。
- 236 与本地 251 的差额来自上面两处整类 / 整模块未执行。
- 完整日志：`ci/run39771515620_offline-tests.log`。安装步骤只装了 `torch>=2.1,<3` 和 `transformers>=4.40,<6`。

### 原因

`.github/workflows/mini-mythos-smoke.yml` 的 `offline-tests` 没有安装 `datasets`。上述四个 R2 测试模块用 `datasets` 构建本地 HF Dataset 夹具（不访问网络），而 `datasets>=2.18.0` 本来就是仓库在 `pyproject.toml` / `requirements.txt` 中声明的依赖。

`mini-mythos-research` 自 run 281 起已是红色（例如 run 39012685679），P0 PR #2 与 P1-A PR #3 同样失败。P1-B 没有新增测试，也没有修改任何被测代码。

## 2. 修复：独立 PR #5

- PR：https://github.com/leotree2020/OpenMythos/pull/5 （分支 `mini-mythos-ci-datasets-fix-20261022`，commit `ecb5921a0f3ed845fd985d8fd40b3c16d0877af2`）
- 改动：`offline-tests` 的安装行加上 `'datasets>=2.18.0,<6'`。只改这一行 workflow，不改测试、断言、模型或 Parcae。
- Run：https://github.com/leotree2020/OpenMythos/actions/runs/39774588958
  - `offline-tests`：Ran 251 tests，OK（datasets 5.1.0）。完整日志：`ci/run39774588958_offline-tests.log`。
  - `upstream-smoke`：见下文更新。

## 3. 本地复现与验证（Python 3.11 venv，与 CI 相同的安装行）

| 环境 | 结果 | 日志 |
|---|---|---|
| torch 2.14.1 + transformers 5.20.2，无 datasets | Ran 236 tests，FAILED (errors=11)，与 CI 一致 | `ci/local_py311_without_datasets.log` |
| 另装 datasets 5.1.0（pyarrow 26.0.0），P1-B 分支 | Ran 251 tests，OK | `ci/local_py311_with_datasets_p1b_branch.log` |
| `upstream-smoke` 全部步骤本地镜像，gqa | 11 步全部 rc=0 | `ci/local_upstream_smoke_gqa.log` |
| `upstream-smoke` 全部步骤本地镜像，mla | 9 步全部 rc=0 | `ci/local_upstream_smoke_mla.log` |

修复分支（base + workflow 修改）本地同样是 Ran 251 tests，OK。

## 4. PR #4 在修复后的 workflow 上重跑

为了不把 CI 修改混入 P1-B 分支，PR #4 的 base 暂时改为 `mini-mythos-ci-datasets-fix-20261022`。PR #4 的 diff 仍然只有 P1-B 文件。PR #5 合并进 `mini-mythos-research` 后，PR #4 的 base 改回 `mini-mythos-research`。

重跑结果：待本次 push 触发的 run 完成后补充。
