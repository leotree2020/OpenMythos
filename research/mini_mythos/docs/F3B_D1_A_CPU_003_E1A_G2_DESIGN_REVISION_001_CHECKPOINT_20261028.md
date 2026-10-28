# F3B-D1 CPU-003 E1-A G2 design revision 001 checkpoint (2026-10-28)

* 任务 `F3B-D1-A-CPU-003-E1A-G2-DESIGN-REVISION-001`；**仅文档**。分支 `d1-r3-a-cpu-003-e1a-g1-closeout-g2-design-20261028`；基准提交 `8f9e8b2c027b3f6c0b738650b57af62d52dce141`（任务开始时远端 HEAD 经 `git fetch` + `FETCH_HEAD` 核对一致，本地工作树干净）；源码基线 `bench/` = `450914367c247231c51be02e13775cb001e69c5d` 的 `bench/`（与基准提交逐字节相同，零差异）。本修订的提交 SHA 见下方“Git SHA”，且与 G1 执行时 SHA `3eef8d75…` 及证据提交 SHA 不得混淆。
* 状态：**G2 DESIGN REVISION PREPARED — CROSS-REVIEW PENDING。G2 CRITERIA NOT FROZEN。G2 CPU / REAL NOT AUTHORIZED。**（G2-DESIGN-001 审核结论 CHANGES REQUIRED 仍是历史记录，未被本修订替换；本修订不是设计审核通过。）
* 修订内容（设计稿 V1，`a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md`）：F1 身份分层（声明 PID / 内核身份 / gate 持有证明 / 创建血缘）与放行前后证据分类，反例 CX-1 同父错 PID、CX-2 重复 PID、CX-3 共享 gate fd 等；F2 回收者方案 A（创建者回收）与 B（观察者 subreaper）均给出可验证设计且**不选择**，明确 `node_main` 不回收后代；F3 EXIT_OBSERVED / ZOMBIE / REAP_CONFIRMED / PROC_GONE 四态分离，DEAD / ECHILD / pidfd 可读不单独证明回收；F4–F5 socket 凭据限制与账本无法记录 CREATED / EXIT / REAPED，设计隔离的哈希链 sidecar；F6 撤回“两次稳定扫描即证明无后代”，不可证实的完整性声明保持 UNKNOWN / BLOCKED；F7 逐卡片 SUT / 独立真值 / 预防性与检测性要求；F8 不使用原 SIGKILL 清理路径的安全退出、回收与人工处置流程；F9 进程预算、判据优先级 FAIL > BLOCKED > PASS、CPU-only 与 REAL 阶段边界、全部未决选择。
* 保留：原 F1–F9 审核发现完整保存在 `gate_g2/G2_DESIGN_REVIEW_001_FINDINGS.md`；V0 原稿归档为 `gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V0_8f9e8b2.md`（除首行 HTML 注释外与基准提交该文件逐字节相同）；逐项处理与决策差异在 `gate_g2/G2_DESIGN_REVISION_001_RECORD.md`。
* 决策差异（均已记录，未擅自裁定）：审核建议 F1(2)“READY.fp.pid 相等”被误列为放行前检查，V1 改为仅检测性；审核的“两次稳定扫描”建议被撤回；审核倾向方案 A 未被采纳，选择保持 OPEN；新增观察：`Observer._register` 已有 `hold_release` 参数（`observer.py:103,124`），`fork_gated` 在放行后关闭 `gate_r`（`gate.py:77`）。尚无 ChatGPT / Grok 对设计的分歧输入，故未记录任何评审分歧。
* 已解决（仅指“设计文本已给出可被审核的规格”，并非性质成立、已测试或已冻结）：F1–F9 全部已在设计中处理，见 `G2_DESIGN_REVISION_001_RECORD.md` 的逐项表。
* OPEN 问题：**O-1…O-15**（回收者方案、预防层驱动 vs 仅检测、见证者形态与归因强度、原始声明捕获、gate 持有者枚举、范围受限的否定性声明能否出现在 PASS 中、sidecar 细节、进程预算数值、REAL 单次 vs 分次、孤儿处理、逐消息凭据需 Bench 变更、后代生成路径、总预算 vs `T_NODE_MAX=120 s`、CX-3 能否真实执行、方案 B 下 G2 与 E1-A 的证据迁移）。G2-R01 仍为 REAL 阻断项直至 O-1 冻结。
* Git 范围（相对基准提交 `8f9e8b2`）：6 个文档文件，396 行新增 / 83 行删除（含本 checkpoint 为 7 个文件）：新增 `gate_g2/G2_DESIGN_REVIEW_001_FINDINGS.md`、`gate_g2/G2_DESIGN_REVISION_001_RECORD.md`、`gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V0_8f9e8b2.md`、本 checkpoint；修改 `gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md`（V0 -> V1）、`docs/PROJECT_MAP.md`（+4）、`docs/SESSION_START_PROTOCOL.md`（+2）。**除 `gate_g2/` 与 `docs/` 外零文件变更**；对 `bench/`、`gate_g0/`、`gate_g1/`、prereg、R3、Parcae、模型、`tests/`、`tools/`、`evidence/` 的差异均为 0。
* 未做：未实现任何 G2 代码，未运行 CPU 测试，未启动真实进程，未创建授权文件，未发送信号，未使用 GPU，未冻结判据，未进入 G3 / BV / E1-A。本地 G0 / G1 授权文件（已消费、未跟踪）保持原状。
* **唯一下一条指令：** 把设计 V1 连同修订记录提交 **ChatGPT 与 Grok** 做新版设计审核，记录分歧并决定 O-1…O-15；之后由项目负责人另行决定。**不实现、不测试、不冻结 G2 判据、不进入 G3 / BV / E1-A。**

## Git SHA

* 基准提交：`8f9e8b2c027b3f6c0b738650b57af62d52dce141`
* 修订内容提交与分支最终 HEAD：见下方追加记录（单独提交，避免自引用）。
