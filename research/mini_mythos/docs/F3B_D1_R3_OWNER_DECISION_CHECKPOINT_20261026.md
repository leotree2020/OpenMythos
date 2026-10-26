# F3B-D1-R3-OWNER-DECISION-001 — 负责人决策记录与 R3 已批准候选规范：检查点

**状态：`OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION`**。R3-D01…D11 已于 2026-10-26（Asia/Tokyo）获项目负责人批准（`OWNER APPROVED — 2026-10-26`）。**这不是 R3 FROZEN，不是 REAL D1 PASS，不是任何运行授权。**仅文档；本检查点是独立文件，不被被登记的两份文件引用，因此哈希引用没有循环。

## 1. 登记（SHA-256、Git、源基准、批准日期）

| 项 | 内容 |
|---|---|
| 批准日期 / 依据 | 2026-10-26（Asia/Tokyo）；项目负责人在 ChatGPT 对话中的明确批准（经本次执行令转述）：「批准 R3-D01～D11 按 ChatGPT 推荐方案执行，D07 选择 X，参数按建议作为初始验收值」。**不含**签名、聊天链接、身份信息（未提供，不伪造） |
| 源基准 | 分支 `d1-pre-real-spec-r3-20261026`，提交 `4c1d29d9e01c6df2d3b5e796181f728cc3cb88ed` |
| 被批准决策所依据的原文 | `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（FINAL-005 版，原样保留），SHA-256 `d52856713e1dd0d53855597bedc8f3f7eec9dfeec8aece24cdafef839054bbef` |
| 工作分支 | `d1-r3-approved-candidate-20261026`（从源基准新建，ChatGPT 的 R3 草案分支不被覆盖） |
| 负责人决策记录 | `research/mini_mythos/docs/F3B_D1_R3_OWNER_DECISION_20261026.md`，SHA-256 **`6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319`** |
| 已批准候选规范 | `research/mini_mythos/docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md`，SHA-256 **`2aaea7d3ed32585c02ee0adc9daaed1e8d09913e2006d47871eb45bd6bb5fc2a`**（行数见提交） |
| Git 提交 | 本检查点随同上述文件在**同一提交**里；提交 SHA 由 Git 给出，见汇报。两个 SHA-256 都可由 `git show <提交>:<路径> \| sha256sum` 复算 |

**哈希引用方向：** 决策记录 → 草案（已存在的摘要）；候选规范 → 草案（摘要）和决策记录（仅路径）；本检查点 → 决策记录、候选规范（摘要）。没有任何文件包含自己的摘要，也没有两份文件互相包含对方的摘要。

## 2. 正式批准的 11 项决策

| ID | 已批准方案 | 状态 |
|---|---|---|
| R3-D01 | 严格分阶段获取；Tokenizer 固定前 validation/test 仅 L0，禁止 L1+ | OWNER APPROVED — 2026-10-26 |
| R3-D02 | T7 的 validation/test 扫描在 Tokenizer 固定之后 | OWNER APPROVED — 2026-10-26 |
| R3-D03 | Driver 整体前后哈希 + `stat`；接受 TOCTOU / ABA 残余风险；C-1 / C-3 为可选加强、不视为已授权 | OWNER APPROVED — 2026-10-26 |
| R3-D04 | 记录原始编码 Token 数与含 EOS 前缀的流 Token 数并核对恒等式 | OWNER APPROVED — 2026-10-26 |
| R3-D05 | 中断 BLOCKED；不自动恢复或重试；新运行新目录；R7.7 正常路径 NOT_APPLICABLE | OWNER APPROVED — 2026-10-26 |
| R3-D06 | 仅 B-LFS；B-GIT、B-XET 未经受控验证不得启用 | OWNER APPROVED — 2026-10-26 |
| R3-D07 | **方案 X**：30 分钟（`open` 到 `close`）；K3 / K4 在 `close` 后远端固定；τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s（初始验收值，需 CPU 测试，调整须有审批与变更记录） | OWNER APPROVED — 2026-10-26 |
| R3-D08 | D1 仅允许 test（及 validation）的完整性 / 行数 / Token 统计 / round-trip / 特殊字符串审计；禁止训练、模型选择、调参、质量评估 | OWNER APPROVED — 2026-10-26 |
| R3-D09 | 新脚本按最小任务独立开发、独立 CPU 验收，完成后整体重新冻结；不得修改现有冻结代码 | OWNER APPROVED — 2026-10-26 |
| R3-D10 | 授权记录在 Git 仓库，SHA-256 绑定批准版本与后续实验授权；不伪造签名 / 链接 / 身份 | OWNER APPROVED — 2026-10-26 |
| R3-D11 | 正式 `tokenizer.json` 不提交公开仓库；仅提交哈希、统计与非敏感证据 | OWNER APPROVED — 2026-10-26 |

## 3. 验收：实际检查结果

| 检查 | PASS 条件 | 实际 | 状态 |
|---|---|---|---|
| 决策完整性 | D01～D11 全部与批准内容一致 | 决策记录 11 行，逐项文字与执行令 §3 一致；候选规范第 7 节 11 行与决策记录一致，状态均为 `OWNER APPROVED — 2026-10-26`；脚本核对 ID 顺序、状态与 D07 参数 | PASS |
| D07 | 唯一执行方案是 X，参数正确 | 候选规范 11.1(f) 只有方案 X；选项 Y 的 `pin_phase`、`close.pins_*`、`OPTION_Y_*`、选项 Z、选项 B 全部不在执行条款里（仅在三处「未选定」说明里被提及）；τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s 在决策记录与候选规范中一致 | PASS |
| 规范一致性 | 无矛盾，无未解决的执行二选一 | 批准内容之间**没有**实质矛盾，未触发 BLOCKED；候选规范中无 `PENDING`（除状态语 `PENDING FINAL DOCUMENT VERIFICATION` 与 Grok 的 PENDING）、无 `PROPOSED`、无「待裁决」；账本状态机去掉 `pin_phase` 后，成功路径与 F1a / F1b / F1c / F2 / F3a / F3b 六条失败流程逐条通过注册表校验；3 个负例（无 `terminate_begin` 的 `terminate_signal` / `reap_done`、`pin_phase` 不在注册表）被拒绝 | PASS |
| 冻结保护 | SHA 清单 10/10，不修改 v1/R1/R2 | `D1_CODE_SHA256SUMS` 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN`、哈希 `0d35dc21…`；v1 `a55b2cb7…`、R1 `f92c4e79…`、R2 `1d4c3629…` 不变 | PASS |
| Git 范围 | 仅文档与检查点 | 相对源基准的变更：新增 2 个规范文件 + 1 个检查点，追加 3 个索引文件；无非 `.md` 文件；`git diff --check` 无输出 | PASS |
| 依赖图 | 重新核算节点、边和无环性 | 从候选规范第 5 节正式边列表重新构图：17 节点；`ref` 31 / `rec` 9 / `sub` 3，共 43 边；无重复、无环、层级严格递减；人读表格与边列表一致；候选规范与草案相比工件依赖没有变化（只删去选项 Y 的 `pin_phase` 说明）。完整边列表见下节 | PASS |
| 证据身份 | SHA-256 可复算，引用无循环 | 两份主要文件的 SHA-256 见第 1 节；提交后以 `git show` 复算比对；引用方向见第 1 节 | PASS（提交后复核，见汇报） |
| 执行状态 | 新机制均保持 NOT TESTED | 记录器、监督器、账本、获取、拟合、审计、清单生成、摘要模块、验收（含 `--postmortem`）、固定与 RV 工具全部未编写，保持 NOT TESTED；目标环境相关系统调用 NOT TESTED；Hub 元数据语义 NOT VERIFIED | PASS |

另核对：第 1 节原文引文 20/20 逐字存在；候选规范保留草案的历史指引，不删除草案、历史 FAIL 与修订记录。

## 4. 依赖图证据（重新计算）

**节点（17）：** A1(层级 0)、BP0(层级 0)、PIN0(层级 1)、A2(层级 1)、LP1(层级 2)、PIN1(层级 3)、A4(层级 4)、LP2(层级 5)、PIN2(层级 6)、A5(层级 7)、A6(层级 8)、A7(层级 9)、LP3(层级 10)、PIN3(层级 11)、BP(层级 12)、PIN4(层级 13)、A8(层级 14)

**`ref` 边（31）：** 1. PIN0 → BP0；2. A2 → A1；3. PIN1 → LP1；4. A4 → A1；5. A4 → A2；6. A4 → LP1；7. A4 → PIN1；8. PIN2 → LP2；9. A5 → A1；10. A5 → A4；11. A5 → LP2；12. A5 → PIN2；13. A6 → A2；14. A6 → A4；15. A6 → A5；16. A7 → A6；17. PIN3 → LP3；18. PIN4 → BP；19. A8 → A1；20. A8 → A2；21. A8 → A4；22. A8 → A5；23. A8 → A6；24. A8 → A7；25. A8 → LP3；26. A8 → BP；27. A8 → PIN0；28. A8 → PIN1；29. A8 → PIN2；30. A8 → PIN3；31. A8 → PIN4

**`rec` 边（9）：** LP1 → A1；LP1 → A2；LP1 → PIN0；LP2 → A4；LP2 → PIN1；LP3 → A5；LP3 → A6；LP3 → A7；LP3 → PIN2

**`sub` 边（3）：** LP2 → LP1；LP3 → LP2；BP → BP0

## 5. 未解决风险与待核对事项

- **用途声明文本（R3-D08）：** 执行令只写「按 ChatGPT 推荐方案」，未另行提供文本；决策记录第 6 节取草案文本（摘要 `sha256:72e378a7…f310`）。**请 ChatGPT 独立核对时确认这一取值**；若负责人另有文本，须新建带日期的变更记录。
- **S1 可能 BLOCKED：** D06 只批准 B-LFS；若真实 Hub 元数据不含 `lfs.sha256` 或语义不符，S1 将 BLOCKED，需先做单独授权的仅 L0 元数据验证任务。
- **参数适用性：** τ、`G_term`、`G_kill`、`W` 是初始验收值，需 CPU 测试；调整须带审批的变更记录。
- 沿用：信任域局限、远端引用不是不可伪造证明、带外核对依赖人工、GitHub 分支保护 NOT VERIFIED；`CLOCK_BOOTTIME`、`PR_SET_CHILD_SUBREAPER`、`PR_SET_PDEATHSIG`、`/proc` 扫描、`waitpid` 状态区分在目标环境 NOT TESTED；Driver 前后哈希仍只证明两个检查时刻；后验结论由同一信任域脚本产生。
- 候选规范中除 R3-D01…D11 之外的细则（事件注册表、RV、摘要边界、失败路径收尾等）是为实施决策所必需的具体化，随候选提交 ChatGPT 独立核对；核对通过前不冻结。
- 真实 D1、真实数据下载、正式 Tokenizer 拟合、训练、GPU、D2/D3：NOT TESTED / NOT AUTHORIZED；新脚本开发与第一个合成 CPU 实验各需单独授权；Grok 交叉复审 DEFERRED / PENDING，不是 PASS。

## 6. 下一条唯一研发指令

等待 ChatGPT 独立核对正式 R3 候选规范和批准记录。审核通过后，才能正式冻结 R3。真实 D1、正式 Tokenizer 拟合及新脚本开发仍需独立授权。
