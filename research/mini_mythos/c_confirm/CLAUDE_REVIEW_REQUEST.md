# C1 训练前独立审核请求（Claude Code）

请审核固定代码提交 `8a646eb56a9bcffb9767ad9f50843f85670b2fa1`，仓库 `leotree2020/OpenMythos`，分支 `mini-mythos-c1-budget-confirm-cpu-20261031`。新增目录 `research/mini_mythos/c_confirm/`，基础为 C 分支 `b16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c`。新协议首次提交 `06794bebae186470a9a05d728b59b4f42869e6ae`。

后续 CHECKPOINT/本请求是文档，不是代码修订。旧 MES APPROVE 不能代替本次审核。Claude Code 是当前独立审核角色；Grok 已按所有者要求撤销此职能，不再是额外审批依赖。

## 审核目标

只判断这套 C1 代码/协议是否适合进入已限定的15条CPU训练。不要把准备/组件检查当成模型收益。旧 C4 开发集初筛和 MES-1 失败结论均保留。

三组 GPT/P4/C4；五种子1101/1202/1303/1404/1505。C4 复用原 c_adapters.py，不叠加辅助监督、保守更新或其他机制。训练步数4843/3116/3000、共同计数上限355663872000；预期每步计数73433088/114130944/118554624。参数65344/60224/62784，C4-P4不是等参数比较，不支持纯粹阶段特异性的因果结论。

## 聚焦检查

1. 原 C4 的轮次适配及主体是否完整注册、优化、保存、加载；不得只保存 base。新增包装器零初始化输出/主体梯度/RNG 是否与原版一致；安全 GPT 损失/logits 分路是否保持一次训练前向。
2. 三组预算、步数、样本前缀、P4/C4 初始主干及 RNG 配对；每步计数变化是否停止而非静默改预算。等计数与等样本/硬件成本必须区分。
3. 重新生成 MES H1/HC/H2 旧分配摘要并排除全部5120个规范加数对；新 C1T2048题与旧测试/校准集及训练/开发角色隔离。不能将已查看的 H1 再当新测试。prepare只生成键/层级摘要，不生成C1T或HC/H2完整答案。
4. 所有15条训练完成并核验20份快照后才能生成C1T。每个评估worker检查并解析同一份字节；文件被改动时必须阻塞，避免旧MES R02的读取缺口。重复worker失败不得覆盖已存在row/log，避免旧R03。
5. 主要C4-P4等预算、次要同3000步、GPT保护独立显示。候选选择须主要和GPT保护都PASS；不得只靠主判据exit0掩盖保护条件FAIL。预注册门槛是否忠实实现，有没有评分/配对错误。
6. 最终只读出深度4；不要把不同组的四个原生GPT块与四轮递归混为等结构。C1T只有2048道独立题，40960回答不是40960独立样本。五种子bootstrap仅诊断。

## 文件和证据

新增：PROTOCOL.md、c1_policy.py、c1_runtime.py、run_cpu.py、run_codespaces_cpu.sh、test_c1.py；必要依赖：mech_c/c_adapters.py、mech_ab接口、r1b_calibration/task.py、m2_matched/experiment.py 和固定上游接口。先看最新分支CHECKPOINT，但审核源码固定上述提交。

本地开发记录：29组件测试、15条夹具训练/15评估路径/20条件/20快照的联调、20启动保护检查。夹具不是原生结果。本机Python3.13.5/Torch2.10CPU，生产入口正确拒绝版本；原生C1依赖应为Python3.12.3/Torch2.11.0+cpu/NumPy1.26.4/einops0.8.0。

若所有者已执行prepare，读取既有 `/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1/prepared.json`；若路径不可达如实写明，不推测详细检查，不要求重跑旧实验。新分配摘要应为 `14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0`。

## 授权和边界

允许静态阅读、必要CPU组件测试及无optimizer.step的合成原生接口探针；不同构建的测试注明差异，不当作固定生产环境验收。不要修改源码、协议、数据或阈值，不提交/推送/合并；不要运行prepare/train/evaluate，不开启C1T/HC/H2评分，不新增模型训练、不用GPU、不改上游。不要用审核请求代替实际审核报告。

输出 Markdown 完整报告：实际版本/文件/环境、发现及行号/影响/最小建议、实际执行与未执行项；结论 APPROVE / CHANGES_REQUIRED / BLOCKED。APPROVE只代表可进入训练，报告完成后停止。Formal Oracle保持BLOCKED/NOT_READY，FORMAL_ACCEPTANCE_READY=False，没有G2 REAL。
