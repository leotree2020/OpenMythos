# MES-1 Claude Code review — owner-supplied report

## Provenance and governance note (ChatGPT registration, 2026-10-31)

The project owner supplied the full report below in the conversation. This file is a Markdown transcription of that supplied report, with HTML whitespace artifacts removed. It is NOT a byte-for-byte retrieval of the reviewer's original scratchpad file, an authenticated reviewer signature, or a new execution by ChatGPT. The reviewer-reported tests and limitations remain attributed to Claude Code. Original claimed location: `/tmp/claude-0/-home-user/2c7c9a9c-fc7c-5adb-90a5-e297bc6c2a17/scratchpad/tools/MES1_CLAUDE_REVIEW_20261031.md`.

Reviewed execution source: **7bcb08f480d0bda2dba5b1351442190001492782**. Verdict: **APPROVE, scope-limited pre-training review only**. No model-quality acceptance or training execution follows from this verdict.

The owner has explicitly replaced Grok's independent-review role with Claude Code. The original report's wording about Grok remaining DEFERRED is retained below as received; it is not an additional current approval requirement. Historical Grok reports retain their attribution, and no pending Grok item is retroactively marked PASS. Current workflow: ChatGPT development and Claude Code independent review; disagreements require evidence and, when necessary, a minimal controlled experiment.

---

# MES-1 训练前独立审核(Claude Code)

- **审核人**:Claude Code。这不是 Grok 审核,Grok 审核继续 DEFERRED。
- **日期**:2026-10-31。仓库 `leotree2020/OpenMythos`,Draft PR #22。
- **审核代码提交**:`7bcb08f480d0bda2dba5b1351442190001492782`。我用 `git archive` 取出,没有动任何 worktree。
- **其他提交**:`1fe7213` 与 7bcb08f 只差 `CHECKPOINT.md`(文档)。PR 相对基础 `4cf60b05` 只改 `multi_exit_study/`,目录外没有差异。
- **读过的文件(全部行)**:
  - `PROTOCOL.md`、`CHECKPOINT.md`(7bcb08f 与 1fe7213 两版)
  - `mes_policy.py`、`mes_runtime.py`、`run_cpu.py`、`run_codespaces_cpu.sh`、`test_mes.py`
  - `evidence/gpt_interface_fix_20261031.json`
  - 依赖:`mech_ab/{mechanisms,metrics,run_cpu}.py`、`r1b_calibration/task.py`、`m2_matched/experiment.py`
  - 固定上游 `models/gpt/gpt.py`(blob `33ee7872…` 与记录一致)和 `models/parcae/*`
- **继承文件**:五个继承文件的 SHA-256 与 `mes_policy.py:113-119` 的 `INHERITED` 常量一致。固定上游全程干净。

## 总体结论:APPROVE(范围受限)

7 个文件按行读完,未发现阻塞项。有 3 个 LOW 和 3 个 INFO,都不要求改阈值、协议或架构。训练前仍需你自己用 `--review-report --reviewer --review-approved` 提交。

**限制:`prepared.json` 无法读取。**

- `/workspaces/...` 在本环境不存在,全盘 `find / -name prepared.json` 无结果,上传目录只有请求文件和 M2-L 文件。
- 终端报告的 SHA-256 `d6ec93cb…0678` 我没有核验。它的 `code_head`、逐种子预检和 `pip-freeze` 我也没有核验,不做推测。
- 我没有要求重跑 prepare。作为替代,我用 7bcb08f 源码重新算了预算和持出分配摘要,你可以和自己的文件比对:
  - `holdouts.H1.allocation_sha256` = `92cf3818dbeb838e62c3937f836ecd3f4c94190ca7b6a9719e0b1a1e0156a6ce`
  - `holdouts.HC.allocation_sha256` = `18ec9725035bb257b0bf62a3ab7f38961a69c42878f522ad41f1daa01d85fab4`
  - `holdouts.H2.allocation_sha256` = `e6256d5ff6cd99e113ac07b7c373953f5e3b9c9bfd6a689d7e90904064350543`
  - 预算:GPT/P2/P4/A = 5941/5433/3822/3000 步,上限 436285440000,与 checkpoint 表一致。
- 训练 worker 本身也会在 prepared 的源码身份或起点哈希不一致时拒绝启动(`mes_runtime.py:141,147`)。

## 发现

| ID | 严重度 | 位置 | 问题 | 影响 | 最小修复(可选) |
| --- | --- | --- | --- | --- | --- |
| R01 | LOW | `mes_policy.py:259-265`,`run_cpu.py:156-157` | 顶层 `status=PASS` 和 `exit_code` 只由主判据决定。合成数据下"主判据 PASS、GPT 保护 FAIL"仍返回 `exit_code 0`。PROTOCOL 第 25 行规定保护条件独立,所以这是设计如此。 | 只看退出码可能漏掉 GPT/P2 保护条件失败。 | 在 `exit_code` 旁加一行五项筛查汇总,或在报告模板里写明五项都要看。不改阈值。 |
| R02 | LOW | `run_cpu.py:140` 对 `186-188` | evaluate worker 读取 `H1.json` 时不核对父进程记录的 `H1_file_sha256`,也不重跑 `verify_training`。屏障本身没被绕过:H1 只在 `run_cpu.py:134-139` 的 `verify_training` 之后才生成,worker 还需要 `training.json` 为 PASS。 | `H1.json` 若被损坏或改动,会被静默评分。 | worker 内加 `require(file_sha(H1.json)==result.json['H1_file_sha256'])`。 |
| R03 | LOW | `mes_runtime.py:142`,`run_cpu.py:194-200` | 手动对已存在的 job 目录再启动 train worker 时,`mkdir(exist_ok=False)` 失败,异常处理会把已有 `row.json` 的状态改写为 BLOCKED/FAIL。只有在 `training.json` 仍为 PARTIAL(父进程被杀)时才可能触发。 | 会改动已有的部分证据。 | 仅当本进程创建了 job 目录时才写 `error.log` 和状态。 |
| R04 | INFO | `run_cpu.py:90-96` | 批次前缀和 RNG 前缀配对要等 20 条轨迹全部训练完才检查。 | 不匹配时浪费算力。 | 我用原生模型对 P2/P4/A 做了 3 步检查(种子 101),RNG 序列一致,无需改动。 |
| R05 | INFO | `test_mes.py:36-42` | 仓库测试用类 Parcae 夹具加严格 GPT 签名。证据 JSON 里提到的"40 个固定 GPT forward 用例"不在仓库里。 | 真实 GPT 的覆盖靠你的 prepare 运行和我的原生检查。 | 后续提交加一个原生 GPT 回归测试。 |
| R06 | INFO | 范围 | 已声明的解释限制依然存在:A-M2L-01(两个 Parcae 张量共 8,320 个参数始终没有梯度)会混杂 GPT 与 Parcae 的比较;预算是受支持算子的计数而非硬件成本;便宜的组会重复见到更多样本;40 个条件共用同一批 2048 题;1 个百分点约等于 20.5 题;只有五个种子。 | 只影响解读。 | 无。 |

## 五个重点问题

1. **GPT 损失与 logits 接口:PASS。**
   - 固定上游的 `GPT.forward` 只在无标签分支定义 `outputs`,且只有 `return_logits` 为真时才返回 logits。
   - `GPTPath.forward`(`mes_runtime.py:61-67`)只调用一次原生前向,用 `return_logits = labels is None`。
   - 原生检查(真实固定 GPT,种子 101):
     - 训练时只有 1 次原生调用,`return_logits=False`;损失、RNG 和全部梯度与 `m2.call` 逐位相等,没有 None 梯度。
     - 推理时 1 次无标签调用,logits 逐位相等。
     - `gpt_objective_check` 误差 0.0,它在计数探针之外,且用 `no_grad` 和 `fork_rng`。
   - 上游没有改动。
2. **多轮监督 A:PASS。**
   - 损失是 0.75·CE(第 4 轮) + 0.25·CE(第 2 轮),在同一条 4 步轨迹上,第 2 轮状态不 detach。
   - 读出用原生 C、coda、ln_f 和输出头(`mechanisms.py:15-26,97-110`)。
   - 公式误差 0.0,包装器没有新增参数。
   - P2 是专门按 2 轮训练的,和原生 `num_steps_pair=[0,2]` 逐位相等。
   - 教师强制只出现在训练和单列的 CE 指标里。生成时只把模型自己生成的 token 回灌(`mech_ab/run_cpu.py:192-208`,单测核对了长度 6、7、8、9)。
3. **预算、步数、批次配对:PASS。**
   - 原生探针(批 32×9,无更新,种子 101)得到 GPT 73433088、P2 80289792、P4 114130944、A 145428480,等于 `EXPECTED_COUNTS`。步数 5941/5433/3822/3000,最大余量 0.017643%(低于 0.1%),A 的读出和反向已计入。
   - `torch.randint(...)[:steps]` 的前缀性质我对 3000/3822/5433 都验证了。
   - 优化器和裁剪与协议一致。P2/P4/A 的训练 RNG 前缀一致,GPT 只做种子匹配,与声明一致。
   - 种子 202–505 的计数我没有重新探针。
4. **H1 隔离、训练后才评估、快照、评分:PASS(静态加数据检查)。**
   - `h1_examples` 只在 `evaluate` 里、`verify_training` 之后调用(`run_cpu.py:138`)。prepare 只存摘要。HC/H2 从不带标签生成。
   - 数据检查:
     - H1/HC/H2 为 2048/1024/2048 对,每个进位层 512/256/512。
     - 均为规范形式,三者两两互斥。
     - 与 train/development 的键重叠为 0。
     - 每个进位层的保留池至少 8306 对。
   - 评估前核对快照文件 SHA、元数据和加载后权重摘要(`mes_runtime.py:199-207`),评估后权重不变。
   - 40 个条件由 `mes_policy.py:226-229` 枚举。生成只用题目,答案只用于评分。
   - 快照回读不是恢复重放,代码里已标 NOT TESTED。
5. **主要判据与保护条件:PASS。**
   - 主判据:均值提升 ≥ 0.01 且每个种子 ≥ −0.01;P4 均值 > 0.99 则 BLOCKED。
   - GPT 和 P2 保护条件为均值与每个配对损失 ≤ 0.01。
   - 深度收益要求每个种子严格提高、carry0 损失 ≤ 0.01、A@2 有天花板判定。
   - 边界测试:
     - 恰好 +1 个百分点 → PASS
     - 某个种子 −1 个百分点 → PASS
     - 某个种子 −1.1 个百分点 → FAIL
     - P4 均值 0.99 → 不 BLOCKED
     - P4 均值 0.9901 → BLOCKED
   - 对合成的、经 JSON 往返的行跑通了完整 `summarize`(无键错误)。交叉 bootstrap(5000 次,种子 731031)在方法间共享种子和题目索引。
   - 数值性训练失败 → FAIL(退出码 1),来源或证据问题 → BLOCKED(退出码 2)。
   - 唯一类似误报 PASS 的风险是 R01,属于解读层面。

## 实际执行的检查

| 检查 | 结果 |
| --- | --- |
| `git fetch`、`git archive`(7bcb08f、基础、协议、checkpoint 提交)和 diff 统计 | 完成;PR 只改 `multi_exit_study/` |
| `python -m unittest test_mes -v`(venv:Python 3.12.3、torch 2.11.0+cu130、numpy 1.26.4、einops 0.8.0,CPU) | **29/29 PASS**(夹具测试,不是原生验收) |
| 原生诊断 `tools/mes1_native_diag.py`(真实固定 GPT/Parcae,种子 101,只做前向/反向,**无 optimizer.step**):FLOP 探针、GPT 两条路径、P2 等价、A 公式、RNG 配对 | 结果如上,退出码 0 |
| 策略/数据诊断 `tools/mes1_policy_diag.py`(无模型、无 H1 标签):分配、互斥、randint 前缀、合成行上的 summarize、判据边界 | 结果如上 |
| 重算持出分配摘要 | 见上文 |

环境说明:我的 torch 是 `2.11.0+cu130`,不是要求的 `2.11.0+cpu`。我绕过了 `ab.runtime()` 直接跑组件,所以这不是固定生产环境的复现(FLOP 计数仍然吻合)。固定上游 `git status` 为空。没有提交、推送、合并,也没有往仓库写任何文件。

## 未执行或无法验证

- `prepared.json` 的字节、SHA-256、`code_head`、逐种子预检和 `pip-freeze`:无法读取。
- 以下均未执行:
  - `prepare`、`train`、`evaluate`、H1 评分、HC/H2
  - 任何优化器更新
  - 原生模型上的 20 条轨迹和 worker 子进程完整流程
  - 启动脚本的实际执行(只做了静态阅读)
  - 检查点恢复重放
  - 种子 202–505 的原生探针
  - 各组参与梯度的参数数
  - 硬件成本与效率
  - MES-2/3
- 正式 Oracle 仍为 BLOCKED/NOT_READY,`FORMAL_ACCEPTANCE_READY=False`,没有 G2 REAL、GPU 或上游改动。

审核到此停止,没有启动训练。
