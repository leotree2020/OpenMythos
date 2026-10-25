# Mini-Mythos F3-A — ChatGPT 独立审核与一次性受控 R1 验收门禁

日期：2026-10-25（Asia/Tokyo）  
独立审核对象：Grok 冻结配置 commit `34c4414667e939560cae69c0a2dc58fca14f9ef5`；实验结果 commit `3b582c7ac8c4ac7e4473d48ee78e05b5326b8026`（结果 commit 是冻结 commit 直接后继）。  
仓库/研究分支：`leotree2020/OpenMythos` / `mini-mythos-p1c-gate22c-readiness`。  
冻结文档：`research/mini_mythos/docs/F3A_FROZEN_CONFIG.md`；实际脚本：`research/mini_mythos/gate3_cpu_train/f3a_lifecycle.py`；原始结果：`research/mini_mythos/gate3_cpu_train/F3A_RESULTS.json`。  
上游只读比对：`sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`，`recpre/optim/__init__.py`、`recpre/schedulers/base.py`、`recpre/schedulers/linear.py`、`scripts/train.py`。  
审核方法：独立查看 GitHub 源码、冻结文档、原始 JSON/日志及远端 Git tree，重新计算文本证据 SHA-256 与学习率数学预期；**没有在 ChatGPT 环境重跑原生 Parcae**；无法由现有 GitHub 文本接口独立读取/重算 3,079,307-byte 二进制 checkpoint 的 SHA-256。

## 1. 正式决策

**F3-A: PARTIAL POSITIVE / NOT CLOSED（整体完整 CPU Training Lifecycle 尚未通过正式验收）**。

积极观察：随机权重 2/2/2 原生 Parcae CPU 微模型在 AdamW 下，第 2–6 步权重 SHA 每步变化；固定输入 Loss 从 4.933872 下降到 2.713740；连续与文件恢复两条路径在 step4–6 的记录中有相同 Loss、LR、model-weight SHA。来自上游 factory 的 CPU-compatible `torch.optim.AdamW` 确实绑定 `make_opt(a_model)` 和 `make_opt(b_model)`，并在加载后绑定新的 `b2_model`，这修复了开发中最早“优化器绑定错模型”的问题。冻结先于实验是可核实事实。

**尚未证明的核心要求：真实 RNG 状态、Optimizer state、Scheduler config/step 以及 checkpoint step 的独立重载有效性和逐步等价；实际坏 checkpoint 在 loader 中被拒绝。** 这些不是可忽略的新实验方向，而是本次既定的 `Checkpoint → Resume` 验收核心。

不存在已证明的原生 Parcae Bug，也不应把本次判定称为完整实验全 FAIL；但当前 `LOCAL PASS` 无法达到原先明确授权的 **完整**生命周期验收条件。原生 `scripts/train.py`、MuonAdamW、DataLoader 恢复与 GPU 继续 `NOT TESTED`。

## 2. 冻结/原始证据和独立 checksum

冻结配置提交 `34c441...` 只新增 `F3A_FROZEN_CONFIG.md`，结果提交 `3b582c...` 新增隔离脚本/运行结果/日志及 `f3a_step3.pt`，没有更改固定上游源码。回归时保护原有 Grok 本地报告的 `research/mini_mythos/gate2_1/TEST_RESULTS.json` dirty 文件，不得清理。

精确计算 GitHub 文件正文的 SHA-256，均与 `RUN_META.json` 匹配：
- `F3A_RESULTS.json` = `2e574e33a516ee41574d2a0e0a7ba0d6ed4f327dfbcbb044d17261744f8897f0`
- `stdout.txt` = `feab80f4ee7e7c2265ce2a00aa72c4d1b7d52146767f27e58537908c79acfd61`
- `stderr.txt` = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空）
- `exit_code.txt` = `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`（`EXIT:0\n`）

独立计算的提交脚本 SHA-256 为 `f8aac2c5a9c028e9628957b094e49dcce30111b5951eec68cf468b2a5ddb2a18`，但实验 `RUN_META.json` 没记录脚本哈希或实验时 dirty 文件清单，不应把“Git 上现有脚本”当作已独立证明的“当时执行的确切脚本字节”。

**二进制 checkpoint**：远端 Git tree 确定 `f3a_step3.pt` 已被 Git 跟踪，Git blob SHA-1 为 `b351dacfa9aac7be759ade893b249ebb9485d5b8`，size `3,079,307` bytes；Grok 结果与元数据报告 checkpoint SHA-256 `1df88782176894f4e0858c1aa7b0cd371e09a60b78dd29b127fcea0bcac4686a`，**本次未独立验证该二进制 SHA-256**（连接器不支持二进制 utf-8 内容解码）。两种摘要不应混淆；Git blob 身份说明存在已提交的固定二进制，不等于与报告的 SHA-256 已交叉核对。

## 3. 冻结数值与上游实现逐项检查

- `seed=42`，CPU float32、SDPA、Prelude/Core/Coda=2/2/2，`247,936` 参数；固定 `num_steps_pair=(0,2)`、batch2×seq8、vocab128；输入 SHA `c527c98f0b9c3f41d5db6817bbf4f78a8b272e4c35fd721b141eb00217001c45`，初始权重 SHA `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`。
- 上游 `get_optimizer("AdamW", allow_fusion=False, use_apex_adamw=False)` 返回 PyTorch AdamW 类；脚本 `make_opt(actual_model)` 给当前参与训练的模型绑定参数。`MuonAdamW` 和原生 `scripts/train.py` 不是本次运行路径。
- 上游 `LinearLRScheduler` 对 `warmup_steps=1`, `max_steps=6`, `base_lr=0.001`, `min_lr=0.0001`：step indices 0–5 的预期 LR 恰为 `[0, .001, .00082, .00064, .00046, .00028]`。独立逐条重算，与 A、B 所有 6 步记录一致。
- 连续路径与恢复路径 A/B 的 **6 步全部**记录了完全相同的 Loss、LR、before/after weight SHA，且连续的 after/before hash 链正确。第 2–6 步 changed=true；第 1 步因 LR=0，changed=false。
- 记录的 74 梯度及 finite=true 每步为积极证据；源码仅计算 `len(grads)`，并未在正式 PASS 条件中强制 `len(grads)==74` 或验证预期梯度名字、非零条件。
- 来源元数据缺 Python/PyTorch/CPU threads、精确脚本 SHA、上游工作区 clean/status 的运行时预检证据；上游 pin 仅为源码常量，`main()` 没执行 Git HEAD/dirty/import path 的强制断言。因此 Grok 报告的上游干净不能凭脚本强制验收为已独立确认。

**冻结判定冲突**：`F3A_FROZEN_CONFIG.md` 的 STOP 原文要求“optimizer does not change a parameter”就停止，但 warmup 第 0 索引 LR=0 已冻结，实际 Step1 无参数变化并继续执行。这个数学行为是合理的，不表示优化器坏了；**但缺少预先写下的零 LR 豁免**，因此按字面原冻结 STOP 条款未满足，不能事后悄悄改为全 PASS。下一轮应在新的冻结补充文档中显式记录这项设计冲突并预设 “LR=0 预期不更新；LR>0 时必须更新” 的新的、可审核的阶段规则，保留本次原始记录和相反的历史冻结规则不改。

## 4. 四项与完整 Training Lifecycle 相关的实际接受缺口

### A. RNG 每步被重置，恢复 RNG 无因果检验能力 — 关键

脚本 `step()` 在每次前向前执行 `set_seed()`（约第 92 行），每一步都将 Torch、Python、NumPy RNG 重设为常量 42。`load_ckpt()` 虽然载入 checkpoint 中的三类 RNG 状态，但下一步立刻重置。因此即使加载时 RNG 状态错误，只要它可读，A/B loss 和权重仍可能完全匹配。这不构成连续训练 RNG state vs file resume RNG state 等价性验收。现有 `rng_state()` 函数写了却未在路径 A/B 正式验收中调用。

### B. 仅比较 Loss/LR/模型权重，未比较 Optimizer state、RNG、步数

`pair` 的实际判定仅为 `loss_ok`, `lr_ok`, `weight_ok`（约第 181–188 行），额外要求 `changed` 和 `finite`。`opt_steps` 只是单个 param id 0 的 step 指标，没有逐步对比实际 optimizer `exp_avg`, `exp_avg_sq`, 所有 param group、所有 step 与 A/B state dict；也没有检查完整 RNG 状态、Scheduler 以及 checkpoint data-position/step 的有效性。

### C. checkpoint 的 `step` 和 `scheduler` 元数据被存储但未验收

`save_ckpt()` 储存 `step=3` 和部分 scheduler 配置，但 `load_ckpt()` 重新 `make_sched()`，**没有校验**保存的 `blob["step"]` 和 `blob["scheduler"]`；实际后续路径使用调用方硬编码 `run(3,3,...)`，不是读取被保存的步数。错误 step=9 或错误 scheduler 配置仍可能被忽略。上游真实 `scripts/train.py` 也存在重建 scheduler（因配置可能变化）的策略，因此不是说“必须 pickle scheduler Python 对象”，而是必须**明确验证与冻结配置、预期步号一致的重建策略**。

### D. 负例是字典检查而非调用 Loader 的拒绝测试

`bad.pop("optimizer")` 后的 `neg["missing_optimizer"] = "optimizer" not in bad` 等只证明字典已经被修改，而非 `load_ckpt()` 拒绝了损坏的 checkpoint。`wrong_step` 只是 `bad["step"] != 3`；当前 loader **实际上没有读取/验证**该字段。也未覆盖 `scheduler` 缺失/损坏、参数形状错误等既定负例。不能把 `negatives=true` 宣传为恢复器确实具有错误检出能力。

## 5. 唯一建议的下一轮：F3-A-R1 有限验收器收口（非新模型研究）

不再启动其他架构/采样/模型规模实验。保留 2/2/2、同一 CPU PyTorch/SDPA、同一随机初始化、固定输入和 AdamW+linear schedule、总六步、中断在三步、数值容差；**不覆盖首次运行记录**。下一轮只补真实生命周期的因果验证，完成后停止交 ChatGPT 审核。

预设接受：
1. 在每条独立训练分支开始前**只初始化一次**随机数状态。训练 `step()` 内禁止每步 `set_seed()`。在不中断路径 A 的 step3 完成后，以及 B save/restore 前后与 step4/5/6 之后，记录 Torch/Python/NumPy RNG 的精确哈希/严格比较，并故意扰动/篡改 checkpoint RNG 验证恢复是否真会影响并触发失败。相同种子两条路径一致，恢复重建模型后 **不允许以每步重置随机种子掩盖问题**。
2. 比较 checkpoint restore 的 **模型全部参数、optimizer 完整参数组和动量状态**、scheduler 冻结重建元数据（允许无状态 scheduler）、完成 step/next_step 和三类 RNG，逐步比较 A/B step4、5、6 的上述状态（张量按原冻结 `atol=1e-6,rtol=1e-5`，整数/step、key、RNG 和预期精确身份严格相等）；此外保留 Loss、LR、weight SHA 逐步对照。
3. 在真正加载文件时使用独立损坏副本执行负例：丢 `optimizer`、丢 `torch_rng`、改 `step`、丢或破坏 `scheduler`、改模型权重 shape、错配置。错误必须被真实 loader 或正式 checker 拒绝并产生预定非零退出，不能用 `"key" not in dict` 冒充 PASS。
4. 每步审计全部预期梯度名字/shape/finite/必要非零和全部相关 optimizer 参数是否确实绑定当前模型，保存环境、真实 Parcae pin/clean、执行脚本 SHA、Git dirty、输入/模型/checkpoint 及日志 SHA；旧二进制及历史证据全部保留。大文件如将继续 Git 跟踪，请写明 Git blob SHA 和本地计算的 SHA-256；由独立审核说明可复核范围。
5. **先创建单独 R1 冻结验收补充**，如实记载历史零 LR STOP 规则矛盾（不悄悄修改首次冻结配置），预先声明此轮 `lr=0 -> no parameter change expected` 且 `lr>0 -> at least one expected parameter change`。如果不愿采用这项明示补充，可另选预先冻结且不会产生 LR=0 的新 warmup 配置，但那已经是**独立新配置**，必须单独标记不能回填旧结果。
6. 不改变模型/上游，保持 fixed-depth (0,2)、AdamW、六步、同输入、CPU；不测试 MuonAdamW、DataLoader、完整 `scripts/train.py`、GPU。若发现确实需要动上游，标记 BLOCKED 提交原因，不自行修改。
7. 把 R1 当作**一次**完整训练生命周期验收器修正和受控 CPU 运行；若仍有不可测的额外边界，分类记录局限，不无限补 F3 probe；在新目录归档后以 `PENDING CHATGPT REVIEW` 停止，未审核不得自行 `CLOSED`。

## 6. 下一阶段与授权/STOP

本文件是独立审计结论，不修改上游或当前已提交训练脚本。当前 F3-A B1 已经执行，研发已有真实性能有限的观察，不应因测试脚本不足就否认学习信号。

**F3-A 正式整体出口仍为 NOT CLOSED。** 继续前必须读取当前 Git HEAD/SOP/map 和本门禁。项目负责人此前授权的是 CPU 端到端验证，R1 属于同一门禁的必要修正，但执行人员仍需确认本次明确的受控 R1 补充范围；严禁自行进入 GPU/新架构/数据规模扩展。

正式验收分项：
- `F3-A CPU fixed-input AdamW weight update and six-step loss observation`: **POSITIVE OBSERVED (LOCAL PASS evidence)**。
- `F3-A file resume model weights/loss/LR equality for steps4–6`: **POSITIVE OBSERVED**。
- `F3-A full optimizer/scheduler/RNG/step checkpoint-resume equivalence and corrupt-file rejection`: **NOT PROVED / NOT CLOSED**。
- `F3-A overall`: **PARTIAL POSITIVE / NOT CLOSED**。
- `MuonAdamW, native scripts/train.py, DataLoader recovery, GPU`: **NOT TESTED**。
- `Known native Parcae bug`: **NOT ESTABLISHED**。

Next sole action: **freeze bounded F3-A-R1 harness/runtime-state verification gate, correct isolated CPU script, run once and archive new evidence, STOP for independent review**.
