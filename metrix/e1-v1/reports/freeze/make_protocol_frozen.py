#!/usr/bin/env python3
"""Writes metrix/e1-v1/PROTOCOL_FROZEN (Owner message part D3) from git objects only: the freeze commit's metadata,
the byte sha256 of the protocol and the four JSON files read with `git cat-file`, and every data / input hash read
from the four JSON files of the freeze commit (each value printed with its JSON path). Run from the repository root:

  python3 metrix/e1-v1/reports/freeze/make_protocol_frozen.py <freeze commit> <output path>
"""
import hashlib
import json
import subprocess
import sys

C, OUT = sys.argv[1], sys.argv[2]
V1 = "metrix/e1-v1/"
FIVE = ["METRIX_E1V1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "DOSE_SPACE.json", "DAMAGE_MANIFEST.json"]


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, check=True).stdout


full = git("rev-parse", C + "^{commit}").decode().strip()
parent = git("rev-parse", full + "^").decode().strip()
ctime = git("show", "-s", "--format=%ad|%cd", "--date=format-local:%Y-%m-%d %H:%M:%S UTC", full).decode().strip()
subject = git("show", "-s", "--format=%s", full).decode().strip()
blob = {f: git("cat-file", "blob", f"{full}:{V1}{f}") for f in FIVE}
j = {f: json.loads(blob[f]) for f in FIVE[1:]}
dm, dmg = j["DATA_MANIFEST.json"], j["DAMAGE_MANIFEST.json"]
sm = j["SPLIT_MANIFEST.json"]


def get(d, path):
    for k in path:
        d = d[int(k)] if isinstance(d, list) else d[k]
    return d


def row(name, manifest, path, kind):
    v = get(j[manifest], path)
    return f"| {name} | `{v}` | {kind} | `{manifest}: {'.'.join(path)}` |"


tok = dm["model"]["tokenizer"]["files_sha256"]
ds = dmg["d2"]["datasets"]
anchor_src = dm["anchor_text"]["source"]
assert anchor_src.count(" (sha256 ") == 1 and anchor_src.endswith(")"), anchor_src
rows_in = [f"| Qwen/Qwen3-1.7B @ `{dm['model']['revision']}` `{k}` | `{v}` | 文件 SHA-256 | `DATA_MANIFEST.json: model.tokenizer.files_sha256.{k}` |" for k, v in tok.items()]
rows_in += [
    f"| 锚文本来源 parquet `{anchor_src.split(' (sha256 ')[0]}` | `{anchor_src.split(' (sha256 ')[1].rstrip(')')}` | 文件 SHA-256 | `DATA_MANIFEST.json: anchor_text.source` |",
    row("D1 来源 `research/mini_mythos/stage1/results/r1/eval_sets.jsonl`", "DAMAGE_MANIFEST.json", ["d1", "source_file_sha256"], "文件 SHA-256"),
    row(f"parcae 分词器 `tokenizer.json`({dmg['d1']['decode_with']})", "DAMAGE_MANIFEST.json", ["d1", "decode_tokenizer_json_sha256"], "文件 SHA-256"),
    row(f"MMLU `cais/mmlu` @ `{ds['mmlu']['revision']}` `{ds['mmlu']['dev_source']['file']}`(D2 DEV 来源)", "DAMAGE_MANIFEST.json", ["d2", "datasets", "mmlu", "dev_source", "sha256"], "文件 SHA-256"),
    row(f"MMLU `{ds['mmlu']['test_source']['file']}`(D2 TEST 来源;第 10 节第 10 步之前只许对整个文件求哈希、读文件尾行数)", "DAMAGE_MANIFEST.json", ["d2", "datasets", "mmlu", "test_source", "sha256"], "文件 SHA-256"),
]
for part in ("dev_source", "test_source"):
    for i, x in enumerate(ds["arc"][part]):
        rows_in.append(row(f"ARC(未采用的备选)`allenai/ai2_arc` @ `{ds['arc']['revision']}` `{x['file']}`", "DAMAGE_MANIFEST.json", ["d2", "datasets", "arc", part, str(i), "sha256"], "文件 SHA-256(只作记录)"))

rows_gen = []
for k, v in dm["files"].items():
    ref = v["reference_canonical_sha256"]
    if ref is None:
        continue
    rows_gen.append(f"| `{k}` | `{ref}` | 规范化 SHA-256(参考哈希;ST12) | `DATA_MANIFEST.json: files[\"{k}\"].reference_canonical_sha256` |")
rows_gen.append(f"| `d2_dev.jsonl`(ARC,未采用的备选) | `{dm['files']['d2_dev.jsonl']['not_adopted_alternative']['arc']['reference_canonical_sha256']}` | 规范化 SHA-256(只作记录) | `DATA_MANIFEST.json: files[\"d2_dev.jsonl\"].not_adopted_alternative.arc.reference_canonical_sha256` |")
rows_other = [
    row("V1 的 320 条 fact(按协议第 2.2 节的比对方法)", "DATA_MANIFEST.json", ["name_generation", "expected_facts_canonical_sha256"], "规范化 SHA-256"),
    row("Pilot 的 160 条 fact(DATA_SEED 20261110 重新生成;预置集合)", "DATA_MANIFEST.json", ["name_generation", "preseed", "pilot_facts_canonical_sha256"], "规范化 SHA-256"),
    row("锚文本 512 篇解码文本", "DATA_MANIFEST.json", ["anchor_text", "decoded_texts_canonical_sha256"], "规范化 SHA-256"),
    row("32 个模板的集合", "SPLIT_MANIFEST.json", ["template_freeze", "template_set_sha256"], "规范化 SHA-256"),
]
TEST_FILES = [k for k, v in dm["files"].items() if v["reference_canonical_sha256"] is None]

lines = [
    "# PROTOCOL_FROZEN — METRIX-E1-V1",
    "",
    "当前有效版本:v1",
    "",
    "本文件中的路径都相对仓库根目录。",
    "",
    "Owner 批准,2026-11-28 12:13:25 UTC(收到 Owner 消息的时间;原文与条件见 `metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md`,C1–C4)。冻结的条件(C4):A、C 完成且冻结提交的审查无 BLOCKER。对冻结提交的审查(D2)各 1 轮,都没有 BLOCKER(见“依据”),所以没有修复提交,下面的冻结提交即 C4 所说的冻结提交。",
    "",
    "## 冻结提交",
    "",
    "| 项 | 值 |",
    "|---|---|",
    f"| 冻结提交(完整 hash) | `{full}` |",
    f"| 提交时间(author / committer) | {ctime.split('|')[0]} / {ctime.split('|')[1]} |",
    f"| 父提交 | `{parent}`(证据提交:Owner 消息记录) |",
    f"| 提交说明首行 | {subject} |",
    "| 标签 | `metrix-e1-v1-frozen`,指向冻结提交(由 Owner 推送;Executor 不推送标签) |",
    "| 仓库 / 分支 | `leotree2020/OpenMythos` / `metrix-e1-v1-protocol-v1` |",
    "| 内容 | Review Gate 裁决 2026-11-28 的 A1–A5 与 A6 的记录;Owner 决定 C1(H = 9 小时)、C2(D2 = MMLU)、C3(主方案)、C4(冻结);全部 PROPOSED 改为冻结值;协议状态 PROTOCOL_FROZEN;四个 JSON 的版本与状态;`build_manifests.py` 同步(协议第 17 节) |",
    "",
    "## 冻结提交下的协议文件与四个 JSON(文件字节的 SHA-256)",
    "",
    f"格式与 `sha256sum` 相同。以 `git cat-file blob {full}:<路径> | sha256sum` 为准(检出时若做换行转换,工作区字节会不同)。执行时按协议第 13 节 ST12 (2) 逐字节比对。",
    "",
    "```",
] + [f"{hashlib.sha256(blob[f]).hexdigest()}  {V1}{f}" for f in FIVE] + [
    "```",
    "",
    "## 全部数据与输入文件的哈希",
    "",
    "每个值都取自冻结提交的 JSON(右列为字段路径),与 Review Gate 审查时的版本 `bc03348ad8b2390ac3df452631d63b8bfe66ad67` 相同。文件 SHA-256 是文件原样字节的哈希;规范化 SHA-256 按协议第 0 节“哈希”的规则。执行第 1 步生成的文件与读取的输入必须等于这些值,否则 ST12。",
    "",
    "### 输入文件",
    "",
    "| 文件 | 值 | 类型 | 出处 |",
    "|---|---|---|---|",
] + rows_in + [
    "",
    "模型与分词器的 revision:`Qwen/Qwen3-1.7B` @ `" + dm["model"]["revision"] + "`(`DATA_MANIFEST.json: model.revision`)。",
    "",
    "### 生成的非 TEST 数据文件",
    "",
    "| 文件 | 值 | 类型 | 出处 |",
    "|---|---|---|---|",
] + rows_gen + [
    "",
    "### 其它内容哈希",
    "",
    "| 内容 | 值 | 类型 | 出处 |",
    "|---|---|---|---|",
] + rows_other + [
    "",
    f"32 个模板各自的 `normalized_sha256` 见 `SPLIT_MANIFEST.json: templates`(与 Pilot 相同)。`SPLIT_MANIFEST.json: candidates.candidate_mapping_sha256` 与上表 `candidates.json` 的值相同。",
    "",
    "## TEST",
    "",
    "本文件不授权生成或评测 TEST。TEST 文件(" + "、".join(f"`{t}`" for t in TEST_FILES) + ")没有参考哈希;只在协议第 10 节第 10 步、选择冻结记录提交并推送且 Owner 对 TEST 生成与评测的批准入库之后生成,其 sha256 写入 `results/st10_record.json` 与 TEST 标记。",
    "",
    "## 依据",
    "",
    "- 指令:`metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md` D1–D3。",
    f"- 审查(D2,对冻结提交,各 1 轮):`metrix/e1-v1/reviews/{full}/code-reviewer_round1.md`(PASS,无 BLOCKER;1 个 MAJOR、13 个 MINOR,按指令只登记)、`metrix/e1-v1/reviews/{full}/data-auditor_round1.md`(PASS,无 BLOCKER;按 `metrix/CLAUDE.md` 第 10 节仍为“待验证”,仅作参考;脚本 `metrix/e1-v1/audit/f1_*.py`,完整 stdout `metrix/e1-v1/audit/stdout/*_freeze.txt`)。审查原文、转录与 audit 输出随本文件之后的报告提交入库;报告 `metrix/e1-v1/reports/FREEZE_REPORT.md`。",
    "- Executor 原始输出:`metrix/e1-v1/reports/freeze/rebuild_check.txt`(冻结提交内;对暂存树 69ff2c43 重新生成的四个 JSON 与入库的逐字节相同;协议与四个 JSON 中全部 40 / 64 位十六进制串与 bc03348a 相同);`metrix/e1-v1/reports/freeze/rebuild_check_freeze_commit.txt`(同一检查直接对冻结提交运行,并显示暂存树与冻结提交中协议、四个 JSON 与 `build_manifests.py` 的 blob 相同;随报告提交入库)。本文件由 `metrix/e1-v1/reports/freeze/make_protocol_frozen.py` 从 git 对象生成(随报告提交入库)。",
    "",
]
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("wrote", OUT, "| freeze commit", full)
for f in FIVE:
    print(hashlib.sha256(blob[f]).hexdigest(), V1 + f)
