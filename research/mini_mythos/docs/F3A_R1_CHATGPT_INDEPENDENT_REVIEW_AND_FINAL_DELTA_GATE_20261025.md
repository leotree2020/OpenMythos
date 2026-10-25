# Mini-Mythos F3-A-R1 — ChatGPT 独立审核与最终限定异常恢复门禁

日期：2026-10-25（Asia/Tokyo）  
仓库：`leotree2020/OpenMythos`；分支：`mini-mythos-p1c-gate22c-readiness`  
R1 冻结补充 Commit：`8ea2d674404c44f5887fd248ef25a33c1a622727`  
Grok R1 执行/归档 Commit：`14974c8e2a6ad11bea7b45df4242b5acbad3abfe`（其直接父提交为冻结补充）  
前次 ChatGPT F3-A 审核：`research/mini_mythos/docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md`  
R1 冻结：`research/mini_mythos/docs/F3A_R1_FROZEN_SUPPLEMENT.md`  
R1 执行脚本：`research/mini_mythos/gate3_cpu_train/r1/f3a_r1.py`  
结果目录：`research/mini_mythos/gate3_cpu_train/r1/`  
审核方法：GitHub exact pinned source/experiment JSON/code/source commit/manifest read，独立重新计算 SHA-256 与冻结 scheduler 数学；**未在 ChatGPT 环境重新运行 native PyTorch/Parcae**。二进制 checkpoint SHA256 只由 Grok 的 manifest 报告，GitHub 二进制下载未可用，**未独立复算二进制 SHA256**。

## 一、正式结论

**F3-A-R1 的正常训练及连续 vs 文件恢复轨迹：PASS / CLOSED（仅限冻结的 2/2/2 Parcae CPU、固定输入、AdamW、Linear Scheduler、6 步、3 步断点的正常路径一致性）。**

**F3-A 完整生命周期（含预先冻结的损坏 Checkpoint 内容/状态错误拒绝）：PARTIAL POSITIVE / NOT CLOSED**。关键问题在负例涵盖与已保存调度参数实际验收，不在当前正常训练数字。不得将 R1 `LOCAL PASS` 转为不加限定的 F3-A FINAL PASS。E6/F2 系列不因此重启。

无上游 Parcae/AxoNN 源码改动证据；MuonAdamW、完整 `scripts/train.py`、数据流 DataLoader 恢复、真实语言能力、GPU 均 `NOT TESTED`。

## 二、实际通过的独立审计项

1. 冻结配置与实验提交顺序正确：R1 冻结补充 `8ea2d67` 在运行结果 `14974c8` 之前，且没有改写原 F3-A 冻结/结果。
2. R1 脚本 `step()` 不再每次强制重设 seed。分支 A、B 开始前固定 seed，且 `load_ckpt()` 实际先重建模型/优化器/调度器再恢复 torch、python、numpy RNG；重新实例化期间暂用固定随机种子的行为在加载保存 RNG 后得到覆盖。
3. 6 步 A/B 结果内容中，逐步 Loss、LR、模型权重 before/after SHA、Optimizer state digest、Scheduler 新实例配置、Torch/Python/NumPy RNG digest 均完全一致。逐步权重摘要形成完整衔接链。预设 Step1 warmup `LR=0` 允许参数不变且实际不变；Step2–6 `LR>0` 参数改变。
4. 独立按照上游 linear schedule `base_lr=1e-3, min_lr=1e-4, warmup=1, max_steps=6` 重算 step 0–5 六个学习率 `0,0.001,0.00082,0.00064,0.00046,0.00028`，与 A/B 十二条数据一致。
5. Torch RNG 六个步骤 SHA 依次不同、A/B 每步相同，排除了 B1 把所有步 RNG 重置为同一种固定状态的验收漏洞。Python/NumPy RNG 在当前固定输入训练路径中没有被消耗，跨步摘要不变属于合理记录，不构成其被训练随机操作动态使用的证明。
6. 5 个构造出来的损坏 `.pt` 文件被传入 `load_ckpt()`，均报告异常；其中 `bad_bad_shape.pt` 的实际注入是删除一个模型 state_dict 的键，`model.load_state_dict()` 因缺键抛 RuntimeError，**不是张量 shape 被改坏**。
7. `pair` 在 step4/5/6 显式比较 loss/lr/weight/opt SHA/scheduler config/RNG SHA，均记录 true。脚本将主要正常路径最终值纳入 `ok` 判定，并记录 `74` 梯度与有限值。

### SHA-256 独立复核

直接对提交 `14974c8` 的 GitHub UTF-8 文本重新计算，而不是照抄 Grok 报告，**4/4 已声明的可读证据 MATCH**：

- `F3A_R1_RESULTS.json`：`1eef51a658edce9d8126247181a8b87432b274b7d0fb3cdb1fbadd5ac953fc97`
- `stdout.txt`：`d11f1ea7424866d565b060ea1a1ac1d9be0259476bb5e4310bffb96c6d36be6c`
- `stderr.txt`：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空）
- `exit_code.txt`：`194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`（`EXIT:0\n`）

额外独立计算提交版探针 `f3a_r1.py` SHA-256：`a2ec4ae17600da042cb90172466984ca184a007c83a971bae79a97628fbb9944`；R1 `RUN_META.json` 未归档脚本哈希或运行时完整 Git dirty/environment，因此不能声称它是当时执行字节的独立证明。

二进制 checkpoint `f3a_r1_step3.pt` 的 Git blob SHA-1 `748c2b1e0c26cfd2daf012860f7838981934e321`，size 3,080,219 bytes；Grok 报告 SHA-256 `cfec0bd47982b5117488e2faaf8655a2f763f09cd33622f808b3b6c410a579d7`，**未独立复算此二进制**。五个恶意副本 Git blob/size 可核实，所报 SHA-256 同样尚未从实际二进制独立验证。Git blob SHA-1 与 SHA256 不可混淆。

## 三、剩余未达到 F3-A-R1 事先冻结门禁的精准缺口

### A. Saved Scheduler 内容不验证；已存在但错误配置会被忽略（实质缺口）

`load_ckpt()`（约 132–147 行）只验证 `blob["scheduler"]` 字段**存在**，随后无条件新建 `make_sched()`，并 **从未将 blob["scheduler"] 里的 base_lr/min_lr/warmup_steps/max_steps 与当前冻结配置作比较**。结果 `sched_ok` 比较的只是路径 A/B 两个相同新建配置，不能证明保存的调度器内容有效。缺失 `scheduler` 会抛错的负例虽 PASS，却不能检出 `scheduler={"base_lr":错误值,...}`。这个条件是原 F3-A 与 R1 预先冻结的 checkpoint resume config 验收核心，不能凭正常路径数值相同跳过。

### B. Valid-but-wrong RNG 负例没有执行（冻结门禁缺口）

当前 `missing_rng` 只删除 `torch_rng` 字段，检测到了缺键。没有“字段存在且合法，但随机状态错位”的负例。正常步骤中实际 RNG 比较是有效正向证据，但 `load_ckpt()` 只用 `torch.set_rng_state(blob["torch_rng"])`，对合法错误状态不会自动抛异常。无需要求 loader 自身判断随机性对错；**验收比较器必须在受控篡改恢复后检出第 4 步 RNG/状态或轨迹失配并返回 FAIL**，避免重新出现“恢复用错 RNG 仍然算 PASS”的情况。

### C. `bad_shape` 实际是 missing-key，不是 shape 错误（负例标签与事实不符）

`cases["bad_shape"] = lambda b: b["model"].pop(next(iter(b["model"])))` 删除了 state_dict 键，并未改变 Tensor 的形状。该实验是 `missing_model_key` 负例，不是坏形状检测。若维持冻结名 `bad_shape`，必须真正保留键、破坏它对应张量的 shape 并让实际 loader 拒绝。

### D. 其他披露的局限，不应导致无穷迭代

- `main()` 无强制检查上游 Parcae commit/clean/import 路径、全套参数名/shape/nonzero；脚本 `grad_count` 主要判断路径 A，而 A/B 记录均恰好 74。当前仅可声明固定微型研究配置通过，不能声明原生全部训练配置正确。
- `state_sha(opt.state_dict())` 包括所有嵌套值与 Tensor 内容摘要，用于本轮 A/B exact comparison；不是另行实现的逐张量 atol/rtol 报告，也未独立二次 PyTorch runtime 重算，故应明确审核边界。
- `torch.load(weights_only=False)` **只能针对受信任、自己产生的 checkpoint**。未来真实外部数据/下载的权重严禁用此不安全默认值；本次测试只用仓库内本地 checkpoint 与程序自身构造的负例。
- 没有验证其它调度种类、MuonAdamW、生产 `scripts/train.py` / DataLoader、GPU；Python/NumPy RNG 本次没有动态消耗，不得扩大推论。

## 四、下一步：一次限定的 F3-A-R1 最终验收增补（不增加全程训练轮次）

不再重复 6 步 A/B 正常训练。不改原来 B1/R1 数据，保留 Git 中二进制和日志、dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json`。只针对上述异常恢复验收的三项，运行**隔离的文件加载和极短恢复检验**：

1. 从已有已提交 R1 checkpoint（勿覆盖）新建带 **正确键但错误 scheduler 配置** 的文件，修订隔离 validator/loader 以与冻结 config 逐字段比较并抛 FAIL；新文件按 `f3a_r1_` 衍生命名/新目录存证，不覆盖历史。执行实际 loader 拒绝，记录原因。
2. 从同一 checkpoint 新建 **合法格式但不同 torch RNG state** 的错误文件；执行真实 loader 并跑最少下一步，要求由正式状态/轨迹验收器检出 RNG 失配（或实现明确安全的受信任预期 RNG 校验）且返回 FAIL。不得通过删除字段代替本测试；不得在下一个 step 内重设种子。
3. 新增真正改变 Tensor shape（保留 state_dict key）的错误 checkpoint，经实际 loader 拒绝。将旧 `bad_bad_shape` 正确重新分类为 `missing_model_key` 而非重写原始结果。
4. 审核清楚当前 R1 中可用的连续 step3 / step4 的 trusted RNG 预期以及无状态 scheduler 重建规则；允许合法重建 scheduler，但不可忽略错误的已存配置。保留模型/优化器/数据/6 步冻结范围、所有数值容差。
5. 补归档使用的实际脚本 SHA-256、Python/PyTorch/CPU 环境、上游 SHA 与工作树状态、文件哈希以及完整通过/拒绝原因。除必要的 1 个恢复 step 外，不再重复整个 6 步训练，也不新增随机种子、模型规模、采样模式、GPU 或上游改动。
6. 本次若因二进制限制无法在第三方审核者处复算 checkpoint SHA，不因此要求反复训练；记录 SHA-256 为本地执行端报告值，Git blob SHA 为可独立核验值即可。
7. 完成后停止交 ChatGPT 做一次审核。若负例合格并且正常 R1 结果保留原样，可将 F3-A 的**正常固定输入 CPU AdamW 训练 + 本轮规定异常恢复范围**关闭。后续进入真正有价值的真实训练数据/可复现数据流 Gate 的方案审计，不要再追加无关微型探针。

**本次门禁为审计建议，是否运行追加的极短恢复实验遵从用户已有 CPU 授权及当前最新项目治理/STOP 条件；不意味着允许 GPU 或生产训练。**

## 五、正式阶段状态

- F2-B/C/D：`PASS/CLOSED`（先前限定范围）。
- F2-E E1–E5：`PASS/CLOSED`（先前冻结 CPU 微型范围），E6 `INCONCLUSIVE`。
- F3-A 正常固定输入、AdamW 六步以及 A/B 文件 Resume 观测状态：**PASS/CLOSED（这一限定正常路径）**。
- F3-A 完整 frozen checkpoint 异常恢复验收：**PARTIAL / NOT CLOSED（上述 3 个精准负例缺口）**。
- F3-A 整体生命周期：**PARTIAL POSITIVE / NOT CLOSED**。
- 原生 `scripts/train.py`、MuonAdamW、DataLoader 恢复、GPU：`NOT TESTED`。
- 上游 Parcae 原生 Bug：`NOT ESTABLISHED`。
- 下一条指令：**一次限定的校验器负例增补，最多 1 个受控恢复 Step，归档证据，停止。**
