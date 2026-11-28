读 CLAUDE.md、metrix/CLAUDE.md、metrix/e1-pilot/RUNBOOK_A100.md（全文）、metrix/e1-pilot/tasks/IMPL_C1_RULING.md、IMPL_C4_RULING.md、IMPL_C5_RULING.md。

这是 METRIX-E1-PILOT 的正式运行指令。你现在运行在 Owner 租用的 A100 主机上（Runpod 容器，root 用户，没有单独的数据卷，可用空间在根分区）。Owner 已于 2026-11-28 批准租用 A100（Review Gate 决定记录）。你是 Executor，严格按 RUNBOOK_A100.md 执行，不改任何代码、协议或文档。

先把本消息原文保存为仓库之外的 ~/FORMAL_RUN_OWNER_MESSAGE.md；在 formal 结束后的第一次证据提交中，把它复制为 metrix/e1-pilot/tasks/FORMAL_RUN_OWNER_MESSAGE.md 一并提交。

开始前的核对（任一项不符即停下报告，不要自行修正）
git rev-parse HEAD 等于 0a67c2c4382847cdc8dff1bbc8b607551a2b58e4，分支为 metrix-e1-pilot-protocol-v1，工作区干净，不是浅克隆。
code-reviewer 与 data-auditor 两个 subagent 已加载；按 metrix/CLAUDE.md 第 5 节比对仓库中两个 agent 定义与已加载定义的 frontmatter，tools 行不一致即停。
git config user.name、user.email 已设置；git push --dry-run origin HEAD:metrix-e1-pilot-protocol-v1 成功。
你在名为 metrix 的 tmux 会话中运行。

RUNBOOK 第 3.1 节的克隆与身份设置已由 Owner 完成，不要重新克隆；从第 3.0 节的变量文件开始，把 3.0、3.1 要求记录的输出照样写入 env.txt。<work>、<inputs>、venv 放在根分区下的 /root/metrix-run/ 中（先用 df -h 确认该分区可用空间 ≥ 300 GB）。

Review Gate 裁决（2026-11-28，作用范围：E1 Pilot 直至结束）
RUNBOOK 中写明了预期退出码的命令（例如 git check-ignore 以 1 为正常），按预期值判断，不适用第 4 节总则。
总则中的「保留输出」指该命令的全部输出，不论存放在哪里。
3.2a 的 uv 分支第一步失败时：停下报告，不另找安装方式。
运行期间只含输出的手工提交按证据提交处理，不经 code-reviewer；只 git add 明确路径，提交前核对 git diff --cached --stat。
设备为 NVIDIA A100 80GB PCIe 或 A100-SXM4-80GB 均可，以代码的 ST8 判定为准。
不得停止或重启这台机器；不得删除 <work> 下的任何文件。
三个必须停下等待 Owner 的点

A. 预检之后：如果 formal 因 ST11（预估超过 3.5 小时）或任何其他停止条件停下，按 RUNBOOK 第 4 节处理，报告 Owner，等待。 B. formal 结束之后（无论 Gate 0 结果如何）：停下。向 Owner 报告下列内容，等待 Owner 转达的 Review Gate 意见与对 TEST 生成的批准，未获批准不得运行第 3.6 节：

Gate 0 记录中 G0.1–G0.10 各项的数值与通过与否、最终状态词；
选定的 F、L、A 配置；被剔除的配置（如有）；
累计 GPU 秒数、峰值显存、设备全名；
最后一次推送后的 commit hash。 C. 第 3.7 节 data-auditor 计数完成、两份 L6 计数比对之后：停下，报告两份计数与 ST10 记录的内容，等待 Owner 对 TEST 评测的批准，未获批准不得运行第 3.8 节。

TEST 评测结束后：按 RUNBOOK 第 5 节提交命令输出，向 Owner 报告 T1–T3 与全部 TEST 指标、最终状态、累计 GPU 时间、最后的 commit hash，然后停下。不要删除任何文件，不要关机；由 Owner 在确认结果已推送之后终止机器。

汇报

每次停下时写明：运行环境（主机名、设备全名）、做到 RUNBOOK 的哪一节、最后的 commit hash、原始输出所在路径。任何命令以回溯或非 0 退出码结束，或出现 RUNBOOK 没有写到的情况：不重跑、不修补，保留输出，报告 Owner。
