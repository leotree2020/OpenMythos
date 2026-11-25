# Implementation 阶段 C:Owner 下达的消息原文

两段原文,由 Owner 在本会话(2026-11-24)中给出,按其要求原样入库(“请把本段与今天的补充裁决一起，原文入库为 tasks/IMPL_C_OWNER_MESSAGE.md。”)。第一段是本会话开头的消息;第二段是 Executor 询问上次阶段 C 指令原文(仓库中没有)后 Owner 粘贴的原文。两段之间的分隔线与本说明由 Executor 加入,其余逐字照录。

---

## 一、本会话开头的消息(2026-11-24)

读 metrix/CLAUDE.md、tasks/IMPLEMENTATION_TASK_ORDER_V1.md、reports/IMPL_B_REPORT.md。阶段 C 上次中途停止：两份审查 BLOCK，代码已撤回，见 reviews/tree-65225a5a…/ 与 1435a74..eb05e42。上次的草稿在分支 wip/metrix-stage-c，可以参考，但必须重新送审。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不推送标签，不经 PR。

阶段 C 分为三段，每段结束提交、推送、写入报告：
C1：BE 修复、interpretations 标记、TEST 闸门
C2：run_pilot.py 与 CPU 冒烟测试
C3：RUNBOOK_A100.md 与最终报告
额度不足时在段落之间停下。

Review Gate 补充裁决（2026-11-24，作用范围：本阶段）：
1. 证据提交只能 git add 明确路径；提交前核对 git diff --cached --stat 只涉及 reports/、reviews/、audit/。1435a74 的失误与向前撤回予以追认。
2. interpretations 的 ACCEPTED 标记引用 IMPL_C_REPORT.md「Review Gate 对阶段 B 的裁决」一节，不新建决定文件。
3. ST10 记录由第 8 步的 TEST 驱动代码生成，内容为：L3–L6 TEST 部分的原始计数、test_qa.jsonl 与 general_test.jsonl 的 sha256、代码 commit。评测 TEST 前，闸门用冻结上限从原始计数重新判定，不信任任何自报标志；文件哈希须与授权绑定；data-auditor 的独立计数须已提交且一致。
4. 「TEST 只评一次」：开始 TEST 评测之前，先提交并推送标记（含全部 checkpoint 哈希）；标记存在即拒绝再评。中途崩溃也视为已评，状态 BLOCKED，报告 Owner。
5. 3 和 4 都用人造的假 TEST 行，在临时 Git 仓库里测试，不得生成或读取真实 TEST。
6. CUDA：不另锁 CUDA 12.x 构建。RUNBOOK 规定只租 nvidia-smi 显示 CUDA ≥ 13.0（驱动 ≥ 580）的机器，并写明租用前的检查命令。

其余按上次阶段 C 指令的第 1、6、7、9、10 项执行。阶段 C 全部验收通过后停下，状态写为 IMPLEMENTATION_READY。

---

## 二、上次阶段 C 指令原文(Owner 在本会话中粘贴)

上次阶段 C 指令原文（Review Gate 2026-11-24）：  Review Gate 对阶段 B 的裁决（2026-11-24，作用范围：本阶段；记入 IMPL_C_REPORT.md）： 1. B1–B24 全部接受。在阶段 C 第一个代码提交中，把 interpretations.py 每条的 status 设为「ACCEPTED（Review Gate 2026-11-24）」，使 pending() 为空。    - B3：正式运行第 8 节第 1 步，把 train_Y.jsonl 的规范化哈希写入 manifest。    - B14：G0.3、G0.9 原因为 null，附「需重新校准」注记，与 Task Order V1.2 §15.8 一致。 2. 「UTF-8 解码 test 行」不属于读取 TEST：协议第 3 节把解析 split 字段排除在外，而解析必须先解码字节，所以「解码内容」指读取或使用 test 行的文字本身（分词、解析内容、用于计算）。已发生的运行都没有使用 test 行内容，不触发 ST13，Pilot 有效。保留按字节读取的现行做法。这是执行解释，不改协议文本。 3. TEST 生成器的第 4 个前提（B1–B24 全部裁决）：保留。 4. B19 未在预告的停止点停下：追认；以后预告的停止点必须停下。 5. 推送记录的证据提交不经审查：确认。每阶段最后一次推送的记录，由下一阶段第 0 步的 ls-remote 代替。  阶段 C 的要求（任务书第 7、8、11 节之外）： 6. 先处理 DEFERRED_MINORS 1.26 节的 BE2、BE9、BE10、BE12、BE13，送审。 7. TEST 评测的两个硬性前提：ST10 通过的已提交记录；「TEST 只评一次」的已提交标记，再次评测前拒绝。都要有测试。evaluate_model(split="test") 的调用方加入后，data-auditor 复审 TEST 路径。（本项的具体做法以今天补充裁决第 3–5 项为准。） 8. （已由今天补充裁决第 6 项取代：不另锁 CUDA 12.x 构建。） 9. RUNBOOK 写明磁盘规划（FP32 全模型 checkpoint 约 6.9 GB/个）、确定性模式下 CUDA 算子报错时的处理（停下报告，不得关闭确定性）。 10. 冒烟测试的小模型如果由 config.json 构造，写明其 sha256。  请把本段与今天的补充裁决一起，原文入库为 tasks/IMPL_C_OWNER_MESSAGE.md。
