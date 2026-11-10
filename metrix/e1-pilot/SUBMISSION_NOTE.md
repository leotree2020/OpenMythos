# SUBMISSION NOTE — METRIX-E1-PILOT-PROTOCOL-AUTHORING-V1

状态:AUTHORING 完成 → **AWAITING_REVIEW_GATE**。未进入实现或运行。

## 1. 改了什么

只新增 `metrix/e1-pilot/` 下 5 个文件,仓库其它文件未改动:

| 文件 | 内容 |
|---|---|
| `METRIX_E1_PROTOCOL.md` | 主交付物,第 0–13 节 |
| `DATA_MANIFEST.json` | 模型、种子、事实与名字的生成规则、通用文本与锚文本来源、数据文件的哈希占位(全部 `NOT_GENERATED`) |
| `SPLIT_MANIFEST.json` | fact_id 与 split 规则、32 个模板及其哈希、候选规则、6 项泄漏检查与执行接口 |
| `SEARCH_SPACE.json` | 6 个 arm、F/L/A 各 6 个配置、训练契约(PROPOSED) |
| `SUBMISSION_NOTE.md` | 本文件 |

出处:base `leotree2020/OpenMythos` @ `mythos-idea-thermo-v1` @ `61d3c76705b28cc2ee334abc5bf1baaac4fc30dc`;authoring branch `metrix-e1-pilot-protocol-v1`。

## 2. Task Order 原文中互相冲突之处的处理

按 “Mandatory consistency amendments A–L” 执行(其明文规定覆盖冲突措辞):

| 条款 | 落地位置 |
|---|---|
| A 聚合函数固定为 mean | 协议第 5 节 |
| B Gate 0 只用 TRAIN 与 DEV;TEST 冻结后只评一次 | 第 7、8 节 |
| C 4-way 候选打分可执行 | 第 2.5、5 节;`SPLIT_MANIFEST.json: candidates` |
| D unread 用真实答案测外溢;不定义 NONE | 第 5 节 |
| E 泄漏分为模板泄漏与事实泄漏 | 第 3 节 L1–L6 |
| F 训练预算与优化契约 | 第 7 节;`SEARCH_SPACE.json: training_contract` |
| G floor / ceiling 数值化 | 第 8 节 G0.3、G0.9 |
| H 负对照数值化 | 第 8 节 G0.6、G0.7 |
| I 复现容差数值化 | 第 8 节 G0.8 |
| J Git 出处 | 第 0 节 |
| K 规范化哈希 | 第 0 节;两个 manifest 的 `hashing` |
| L PENDING 只剩 3 项 | 第 13 节 |

模型:Project Owner 于 2026-11-10 指定 `Qwen/Qwen3-1.7B`(revision 见协议第 0 节),因此不是待定项。

## 3. 需要 Review Gate 拍板的字段(PENDING_REVIEW_GATE,共 3 项)

1. **E1-V1 目标 fact 数** — PROPOSED:320(240 learned + 80 unread),Pilot 后按 G0.10 的公式重算。理由:配对差标准差取 0.5 时,检出 0.10 的差约需 196 条 learned fact。
2. **general-damage non-inferiority margin** — PROPOSED:dNLL ≤ +0.03(约 +3% PPL)。理由:与本仓库此前使用的容忍幅度一致;Pilot 中只报告。
3. **CPU wall-clock 上限** — PROPOSED:内存 < 48 GB 的 CPU 机器上限为 0;整个 Pilot 在 ≥ 40 GB 显存的单张 GPU 上执行,上限 4 小时。理由:FP32 全参微调需要约 27.5 GB 加激活。

## 4. Reviewer 应重点看的三处

1. **第 2.5 节与第 5 节(候选打分)**:干扰项只取自同 relation、同 stratum、同暴露类别的答案,并要求 cell 内答案 token 数相同。这是防止“见过这个词”或长度差异替代事实知识的唯一机制;若规则有漏洞,主指标会虚高。
2. **第 4 节 arm A 的定义与第 2.7 节**:anchor 写成“在锚文本上对 base 的 KL”,不在事实陈述句上计算;锚文本与 general damage 的通用文本来源不同且做 13-gram 去重。这是对 Task Order 中 “anchor 正则” 的具体化,需要确认。
3. **第 8 节(Gate 0 数值与 TEST 确认 T1–T3)**:G0.3、G0.6、G0.7、G0.9 的界限,以及“PASS = Gate 0 全过且 T1–T3 全过”的定义,决定 Pilot 的结论;DEV-only 选择与 S/Y 继承规则也在这里闭合。

## 5. 如何验证本次提交

```bash
cd metrix/e1-pilot
python3 -c "import json;[json.load(open(f)) for f in ('DATA_MANIFEST.json','SPLIT_MANIFEST.json','SEARCH_SPACE.json')];print('json ok')"
# 内联副本与 SEARCH_SPACE.json 一致
python3 - <<'PY'
import re
doc = open('METRIX_E1_PROTOCOL.md', encoding='utf-8').read()
block = re.search(r"```json\n(.*?)```", doc, re.S).group(1)
assert block == open('SEARCH_SPACE.json', encoding='utf-8').read(), 'inline copy differs'
print('inline copy identical')
PY
# 模板哈希与 L1、L2 可重算:归一化规则见 SPLIT_MANIFEST.json: template_freeze
git -C "$(git rev-parse --show-toplevel)" diff --stat 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc HEAD -- . ':(exclude)metrix'    # 应为空:除 metrix/ 外没有改动
```

## 6. Agent 自检清单

- [x] 未产生任何训练 / 评测 artifact。
- [x] 未读取或落地 TEST 数据(只列出 TEST 模板与生成规则)。
- [x] 6 个 arm 与已批准结构一致,未新增。
- [x] S / Y 明确继承 F 冻结配置,未单独调参。
- [x] Bootstrap 单位为 fact,文档中显式写出伪重复说明。
- [x] 聚合函数已选定并写死(mean)。
- [x] Gate 0 全部门槛为数字,非描述。
- [x] Failure taxonomy 为固定集合,含升级规则。
- [x] `SEARCH_SPACE.json` 与文档内联副本一致。
- [x] PENDING_REVIEW_GATE 项为 3,全部落在允许列表内。
- [x] 本文件列出:改了哪些文件、哪些字段需要 Review Gate 拍板、Reviewer 应重点看哪三处。
