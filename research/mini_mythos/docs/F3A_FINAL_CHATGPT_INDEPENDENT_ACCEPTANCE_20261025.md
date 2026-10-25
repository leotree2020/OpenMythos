# F3-A — ChatGPT 独立最终验收（研究性 CPU 训练生命周期，冻结范围）

日期：2026-10-25（Asia/Tokyo）  
仓库/分支：`leotree2020/OpenMythos` / `mini-mythos-p1c-gate22c-readiness`。  
本次 Grok 提交：`dd36b939457a6c6197b0026fe38854c4edd05365`。  
F3-A 初次冻结：`34c4414667e939560cae69c0a2dc58fca14f9ef5`；首次结果：`3b582c7ac8c4ac7e4473d48ee78e05b5326b8026`。  
F3-A-R1 冻结补充：`8ea2d674404c44f5887fd248ef25a33c1a622727`；正常完整状态对照：`14974c8e2a6ad11bea7b45df4242b5acbad3abfe`。  
上次 ChatGPT 冻结最后三项：`research/mini_mythos/docs/F3A_R1_CHATGPT_INDEPENDENT_REVIEW_AND_FINAL_DELTA_GATE_20261025.md`。  
当前隔离异常验收脚本：`research/mini_mythos/gate3_cpu_train/r1_final/f3a_r1_final.py`。  
上游原生 Parcae pin：`69284c13746e849104f738d6d1a347b1f457df76`（上游内容保持独立，无本次提交的上游改动）。

## 1. 正式独立审核决定与适用范围

**F3-A PASS/CLOSED — 仅限此次冻结的研究性原生 Parcae CPU 固定输入训练生命周期验证。**

接受项目：
- 随机初始化、原生 2/2/2 Prelude→Recurrent Core→Coda、247,936 参数、CPU float32、SDPA、固定输入、固定深度 `(0,2)`；
- 原生 `recpre.optim.get_optimizer("AdamW")` 返回的 CPU PyTorch AdamW；原生线性 LR scheduler，6 个 optimizer step，其中 index 0 的 LR=0，index1–5 更新参数；
- 每步 Forward、Loss、Backward、Optimizer、Scheduler 正常计算和有限梯度；
- 3 步后真实保存文件、重建模型/优化器/调度器、加载并恢复步 4–6，与连续路径在记录的 loss、LR、权重指纹、优化器完整状态摘要、调度配置、Torch/Python/NumPy RNG 指纹相同；
- 已冻结且受限的三项**异常恢复检查**：（1）错误 scheduler base_lr 被新的 checked loader 拒绝，（2）有效格式但不同的 torch RNG 状态与受信任保存状态比较后判 `FAIL:rng mismatch`，（3）保留 state_dict key 而将 `freqs_cis` shape 改错，实际 loader 抛 shape mismatch；
- 之前 R1 `bad_shape` 真正意义是 `missing_model_key`，在本轮正确重分类，旧证据不覆盖。

**本次验收不是**对 Parcae 上游 `scripts/train.py` 生产入口的验收，也不是 MuonAdamW、真实 tokenizer、真实 Streaming DataLoader 中断恢复、真实语言能力、不同长度/深度/注意力、GPU 或规模训练的证明。未证明原生 Parcae bug；F2-E 的 E6 继续 INCONCLUSIVE，其他 F2 已关闭门禁不变。

审核仅基于 GitHub 源码、结果、Git tree 与哈希的独立证据复核；**ChatGPT 没有在本地重新运行 PyTorch/Parcae**，所以不是独立 CPU 数值复现。最终状态是*证据经独立审查后的研究性范围验收*，不应宣传为完整训练框架经过生产质量验证。

## 2. 源码及三个负例的确切覆盖

### A. 错误 Scheduler 内容拒绝 — PASS（新 checked loader）

`load_checked()` 实际读取 `blob["scheduler"]` 并按预先冻结字典 `{base_lr:0.001,min_lr:0.0001,warmup_steps:1,max_steps:6}` 逐字段比较。错 `base_lr=0.5` 的程序自制二进制文件实际进入 checked loader 并抛 `ValueError: scheduler base_lr`，符合此次冻结反例。

**限制**：新的 checked loader 是 `r1_final/f3a_r1_final.py` 中隔离的验证器；原 `r1/f3a_r1.py` 中用于真实六步训练的 `load_ckpt()` **并未原地更新**。所以此项证明的是“受控 checked loader/validator 可拒绝错误 scheduler”，而**不是原始训练入口已经自动具有该校验能力**。后续在真实数据/正式训练工程里应按架构需求集成此验证，而不需要为此再次执行 F3-A 微型训练。

### B. 有效但错误 Torch RNG — PASS（受信任状态校验，不是轨迹差异的证明）

`bad_rng` 将原 checkpoint 中 `torch_rng` 的第一个字节更改为另一个值而保留 key 与相同 Tensor 格式。错误 checkpoint 被实际载入；模型/优化器重建、状态加载及 `torch.set_rng_state` 能处理该格式；`load_checked()` 对比由原受信任 checkpoint 读取的 Torch RNG SHA-256 后抛 `ValueError("rng mismatch")`。异常支路随后直接载入坏 checkpoint、不重新设置随机种子并执行了一次 forward/backward/optimizer step，最终记录 `FAIL:rng mismatch`。

**审计边界**：该 `FAIL` 基于**前向开始前的 trusted state digest mismatch**；程序**没有记录与受信任恢复路径的下一步 Loss、weights 或梯度数值差异**。因此不能声称损坏 RNG 必然造成已测量的数值失配；但它已经符合本轮门禁允许的“受信任预期 RNG 校验识别并拒绝恢复状态”的策略。 `FAIL:rng mismatch` 是**负例正确被检出的预期**，外层 `local_status=PASS` 和 Exit0 因此合理。

### C. 真正 Tensor shape mismatch — PASS

本次 `bad_shape()` 保留权重 state_dict 中 `freqs_cis` 的键，将其原 `[1,32,1,8,2]` 张量 reshape 为 `[512]`，让 `model.load_state_dict()` 在加载时实际抛 `RuntimeError: size mismatch for freqs_cis`。符合保留键、改变 shape 的冻结负例。该测试是模型 state_dict buffer 的形状检查，**不是对某个可训练 weight 梯度的形状证明**。

## 3. 证据完整性

原始 R1 checkpoint `research/mini_mythos/gate3_cpu_train/r1/f3a_r1_step3.pt` 和 B1/R1 全套旧实验在 `dd36b939...` 提交中均未修改。新提交仅新增一份 `docs/F3A_FINAL_DELTA_RESULT.md` 和新目录 `gate3_cpu_train/r1_final/` 文件。

独立从提交的文本文件内容重新计算 SHA-256，**5/5 与 `RUN_META.json` 完全匹配**：
- `F3A_FINAL_RESULTS.json`: `98f8278cf76f0dea8b70357cadedd99902dee446fe05c2adc2c77970f9f90f7e`
- `stdout.txt`: `5d82f1ee632d993f559fdc51a8cedcd1fe2ebdd028b5f065f31bbf6ff93f5854`
- `stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空）
- `exit_code.txt`: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`（`EXIT:0\n`）
- `f3a_r1_final.py`: `cf31025abde245f5c5c992c2fc95812a38515624a7576c93be11cff5a59a9b9a`

新损坏 checkpoint 也以三份独立的二进制 Git 文件归档；`RUN_META.json` 存储其本地 SHA256。**此审核没有独立读取/重算二进制 SHA256**：当前 GitHub 只读接口对 `.pt` 内容的 UTF-8 解码失败；只有 Git blob SHA / size 和 Grok 端报告的 SHA-256 可作为不同层次的身份依据。本差异不改变本轮源码检查器的限定验收结果。

**需要单独注明的元数据不一致**：`RUN_META.json` 的 `python` 字段写 `3.10.21`，但实际执行命令文本指定 `/usr/bin/python3.11`。运行时 interpreter version、PyTorch 实际版本和上游工作树 clean 状态未在脚本内强制存证；**准确执行环境版本 NOT VERIFIED**。这属可复现性/出处的管理风险，应由 Grok 只读校对并追加勘误记录，**无需重新跑训练或篡改现有归档**。

## 4. 正式结案与进入下一阶段条件

以下仅作为限定研究性结果完成态，与“可投入大规模真实训练”严格区分：

| 项目 | 状态 |
|---|---|
| F2-B/C/D 原生 CPU 数学 | PASS/CLOSED（历史冻结范围） |
| F2-E E1–E5 原生 CPU Mask/Checkpoint 数学 | PASS/CLOSED（历史冻结范围） |
| F2-E E6 token causal coupling | INCONCLUSIVE（保持，非本阶段阻塞） |
| **F3-A 受控 CPU 固定输入 AdamW Training Lifecycle** | **PASS/CLOSED（本次审核，冻结研究性范围）** |
| 原始 R1 loader 中内置的强制 checkpoint 完整性校验 | NOT TESTED / NOT INTEGRATED |
| 真正数据流断点恢复 / Native `scripts/train.py` / MuonAdamW | NOT TESTED |
| GPU Gate 2.2-C | BLOCKED，未授权 |

**停止追加 F3-A 微型测试**。目前下一条唯一合乎项目路线的研发工作是**设计和冻结真实数据训练与评估门禁**：官方可追踪数据集/Tokenizer、数据来源与切分、真实 Dataloader 的 shard/offset/worker/RNG 恢复、随机权重训练、同计算预算的标准 Transformer 对照、独立 heldout NLL/PPL/质量测度、FLOPs/参数量/延迟与数据污染控制。先只读分析和设计，留存配置与可复验收准则，下一阶段实际 CPU/GPU 数据训练均需单独授权。

建议在下一阶段训练设计中显式加入：checkpoint 的 Scheduler 冻结配置校验、适当 RNG 恢复身份校验、Dataset sampler/offset 和 checkpoint schema；这些是**更高一层系统集成任务**，不是重新打开 F3-A 的理由。

## 5. 检查点与未解项

- 审核基准提交 `dd36b939457a6c6197b0026fe38854c4edd05365`；本文件提交后必须重新查询真实 HEAD。
- CPU 固定微型研究接受范围：F3-A **PASS/CLOSED**；旧资料中 `PARTIAL/NOT CLOSED` 是前期历史阶段审核结果，后续应以本审核为准。
- 现场 dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` 只来自 Grok 报告，GitHub 无法验明本地未提交字节，仍不可 reset/clean/覆盖。
- `RUN_META.json` 的 Python 版本不一致：**PROVENANCE INCONSISTENCY，需只读补记，不能根据命令或元数据猜运行解释器的事实**。
- 二进制 checkpoint SHA256 **NOT INDEPENDENTLY RECOMPUTED**；Git 追踪原始与坏副本，保留原样。
- ChatGPT 审核类型：**独立静态源码+证据/哈希数学审计，并非第二次原生 CPU 运行**。
- Grok 当前实施者，ChatGPT 独立复核；Claude Code 暂不接管。
- **唯一下一阶段任务**：真实数据与可复现评估方案的**只读审计/冻结设计**，不得直接运行新训练、启动 GPU 或修改上游。
