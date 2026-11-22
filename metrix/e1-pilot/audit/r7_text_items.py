"""R7 text items: consistency of the round-7 changes with tasks/ROUND7_TASKS.md, item by item, plus the tokenizer
facts behind item 1f. Data Auditor's own script; no Executor code is imported, called or copied.
Exceptions -> RESULT: FAIL (r6_guard). Tokenizer files only; no model, no TEST data (no TEST template is instantiated;
the 1f demonstration strings are synthetic and the chat-template probe uses the placeholder question "Q").

Every check prints the text it found. Comparisons ignore Markdown backticks / bold markers ("`", "**") only.
PASS iff every check marked [judged] holds; lines marked [info] are reported only.
usage: python -I r7_text_items.py <repo_root> <qwen_tok_dir> <reviewed_head>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess
from r6_guard import run

BASE = "fe321cd"


def plain(s):
    return s.replace("`", "").replace("**", "")


def main():
    repo, qdir, head = sys.argv[1:4]
    ok = True
    rd = lambda p: open(os.path.join(repo, p), encoding="utf-8").read()
    proto = rd("metrix/e1-pilot/METRIX_E1_PROTOCOL.md")
    dm = json.loads(rd("metrix/e1-pilot/DATA_MANIFEST.json"))
    sm = json.loads(rd("metrix/e1-pilot/SPLIT_MANIFEST.json"))
    tasks = rd("metrix/e1-pilot/tasks/ROUND7_TASKS.md")
    claude = rd("metrix/CLAUDE.md")
    cr = rd(".claude/agents/code-reviewer.md")
    dmin = rd("metrix/e1-pilot/reports/DEFERRED_MINORS.md")
    P = plain(proto)
    lines = proto.split("\n")

    def judged(label, cond, shown=""):
        nonlocal ok
        ok &= bool(cond)
        print("[judged] %-78s %s %s" % (label, "OK " if cond else "BAD", shown))

    def row(prefix):
        r = [l for l in lines if l.startswith(prefix)]
        return r[0] if len(r) == 1 else None

    git = lambda *a: subprocess.check_output(["git", "-C", repo] + list(a), text=True)
    print("[info] HEAD", git("rev-parse", "HEAD").strip(), "| reviewed head", head)
    judged("HEAD == reviewed head", git("rev-parse", "HEAD").strip() == head)
    changed = git("diff", "--name-status", "%s..%s" % (BASE, head)).strip().split("\n")
    print("[info] files changed %s..%s:" % (BASE, head[:8]), changed)
    outside = [c for c in changed if not c.split("\t")[-1].startswith("metrix/")]
    judged("outside metrix/ only .claude/agents/code-reviewer.md changed", outside == ["M\t.claude/agents/code-reviewer.md"], outside)

    print("== 1a (section 2.7)")
    s1a = "锚文本与通用文本不得共享任何词 13-gram(定义与上限见第 3 节 L6)"
    judged("2.7 contains the 1a sentence", P.count(s1a) >= 1, repr(s1a))

    print("== 1b (L6 TEST part)")
    l6 = plain(row("| L6 |") or "")
    print("[info] L6 row:", l6)
    for s in ("时机为第 8 步生成 general_test.jsonl 之后、TEST 评测之前", "计数为跨全部文档的共享词 13-gram 种类数",
              "上限 0", "由 Executor 与 data-auditor 各自计算,结果须一致"):
        judged("L6 row contains %r" % s, s in l6)
    step8 = plain(row("8. Gate 0 通过后") or "")
    print("[info] section 8 step 8:", step8)
    judged("step 8: L6 TEST part after general_test.jsonl, before TEST, both compute, must agree",
           "在本步生成 general_test.jsonl 之后、TEST 评测之前,由 Executor 与 data-auditor 各自计算一次" in step8 and "两者的结果须一致" in step8)
    judged("step 8 no longer says 'PROTOCOL_FROZEN 之后' / 'data-auditor 运行一次'",
           "PROTOCOL_FROZEN 之后" not in step8 and "由 data-auditor 运行一次" not in step8)
    tp = sm["leakage_checks"]["L6_general_text"].get("test_part", {})
    print("[info] SPLIT_MANIFEST L6_general_text.test_part:", json.dumps(tp, ensure_ascii=False))
    judged("SPLIT_MANIFEST test_part: when / count / limit 0 / both", tp.get("limit") == 0 and "after general_test.jsonl is generated" in tp.get("when", "")
           and "distinct shared word 13-grams across all documents" in tp.get("count", "") and "each separately" in tp.get("computed_by", ""))

    print("== 1c (TEST part over limit)")
    judged("step 8 contains the 1c action", "L3–L6 任一项的 TEST 部分超限:停止,不评测 TEST,状态记为 BLOCKED,报告 Owner" in step8)
    st10 = row("| ST10 |")
    print("[info] ST10 row:", st10)
    judged("section 11 ST10 row: stop, no TEST evaluation, BLOCKED, report Owner",
           st10 is not None and all(k in st10 for k in ("停止", "不评测 TEST", "BLOCKED", "报告 Owner")))
    bl = row("| BLOCKED |")
    print("[info] section 9 BLOCKED row:", bl)
    judged("section 9 BLOCKED row mentions ST10", bl is not None and "ST10" in bl)
    print("[info] SPLIT_MANIFEST test_part_over_limit:", sm["leakage_checks"].get("test_part_over_limit"))
    judged("SPLIT_MANIFEST test_part_over_limit present", "BLOCKED" in sm["leakage_checks"].get("test_part_over_limit", ""))

    print("== 1d (G0.1)")
    g01 = plain(row("| G0.1 |") or "")
    print("[info] G0.1 row:", g01)
    judged("G0.1 contains the 1d text", "L1–L6 中涉及 TEST 的部分在 Gate 0 不要求,按第 8 步运行" in g01)
    judged("G0.1 old L6-only exception removed", "L6 在 Gate 0 只要求 DEV 部分" not in g01)
    print("[info] step 8 lists the TEST runs as:", re.findall(r"对 TEST 运行 L3–L5|L6 的 TEST 部分", step8),
          "| mentions L1 or L2:", ("L1" in step8) or ("L2" in step8))

    print("== 1e: text checks are in r7_general_dev.py (08); data in 02 and 08")

    print("== 1f (EM: delete <think>...</think> before the normalization)")
    s1f = "归一化之前,先删除输出中的 <think>…</think> 片段:从 <think> 到其后第一个 </think>(两者都含),每处都删"
    judged("section 5 contains the 1f sentence", s1f in P, repr(s1f))
    em = dm["model"]["input_convention"]["em_generation"]
    judged("DATA_MANIFEST em_generation has the deletion clause",
           "before the normalization every <think>...</think> fragment of the output is deleted" in em)
    with open(os.path.join(qdir, "tokenizer.json"), encoding="utf-8") as fh:
        added = {t["content"]: t for t in json.load(fh)["added_tokens"]}
    tcfg = json.load(open(os.path.join(qdir, "tokenizer_config.json"), encoding="utf-8"))
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(qdir, local_files_only=True)
    for t, want_id, want_special in (("<think>", 151667, False), ("</think>", 151668, False),
                                     ("<|im_end|>", 151645, True), ("<|endoftext|>", 151643, True)):
        a = added.get(t, {})
        cfg = tcfg["added_tokens_decoder"].get(str(a.get("id")), {})
        tid = tok.convert_tokens_to_ids(t)
        print("[info] %-14s tokenizer.json added_tokens id %s special %s | tokenizer_config special %s | "
              "convert_tokens_to_ids %s | in all_special_ids %s" % (t, a.get("id"), a.get("special"), cfg.get("special"),
                                                                     tid, tid in tok.all_special_ids))
        judged("%s id %d, special %s (protocol 1f)" % (t, want_id, want_special),
               a.get("id") == want_id == tid and a.get("special") is want_special and cfg.get("special") is want_special
               and (tid in tok.all_special_ids) is want_special)
    demo = tok.encode(" Kishan", add_special_tokens=False) + [151667] + tok.encode("\nx\n", add_special_tokens=False) + \
        [151668] + tok.encode(" Kishan.", add_special_tokens=False) + [151645]
    out = tok.decode(demo, skip_special_tokens=True)
    print("[info] synthetic ids", demo, "-> decode(skip_special_tokens=True) =", repr(out))
    judged("skip_special_tokens=True keeps <think> and </think>, drops <|im_end|>",
           "<think>" in out and "</think>" in out and "<|im_end|>" not in out)

    def em_norm(s):                      # protocol section 5 as written (deletion, then the normalization)
        s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
        s = s.split("\n")[0].strip()
        if s[:4].lower() == "the ":
            s = s[4:]
        return s.rstrip(".,;:!?").casefold()
    cases = [out, " <think>\n\n</think>\n\nKishan.", " Kishan<think>a</think><think>b</think>.",
             " Kishan<think>\nunclosed", " Kishan</think>.", " <think>x"]
    for c in cases:
        print("[info] EM normalization of %-45r -> %r" % (c, em_norm(c)))
    print("[info] the protocol text does not say what happens to a <think> without a following </think> (e.g. cut by the"
          " 16-token limit) or to a lone </think>; the reading above leaves both in place")
    ct = tok.apply_chat_template([{"role": "user", "content": "Q"}], tokenize=False, add_generation_prompt=True,
                                 enable_thinking=False)
    print("[info] chat template, placeholder user turn 'Q', add_generation_prompt=True, enable_thinking=False:", repr(ct))

    print("== 1g: hashes in r7_s_cands.py (04-07); section text")
    for s in ("调用方式(细节 5)", "调用方式(细节 4)", "686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e",
              "e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705"):
        judged("protocol contains %r" % s[:20], s in P)
    sp = dm["s_permutation"]
    judged("DATA_MANIFEST s_permutation keeps the old rule and adds call_order/record/line_order/hash",
           all(k in sp for k in ("rule", "call_order", "record", "line_order", "expected_train_S_canonical_sha256")))
    print("[info] protocol section 0 library row:", row("| 库版本 |"), "| Python version pinned in section 0:",
          bool(re.search(r"Python 3\.\d+", proto.split("## 1.")[0])))

    print("== section 14 (all of item 1 recorded)")
    r7rows = [l for l in lines if l.startswith("| v1-r7 |")]
    items = sorted(set(re.findall(r"第 7 轮指令第 (1[a-g]) 项", "\n".join(r7rows))))
    print("[info] v1-r7 rows:", len(r7rows), "| items cited:", items)
    judged("section 14 has v1-r7 rows citing 1a..1g", items == ["1a", "1b", "1c", "1d", "1e", "1f", "1g"])
    judged("no placeholder left (R7_TIME / R7_COMMIT)", "R7_TIME" not in proto + claude and "R7_COMMIT" not in proto + claude)
    t = git("log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d %H:%M:%S", "7fea9181")
    t_utc = subprocess.check_output(["git", "-C", repo, "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d %H:%M:%S",
                                     "7fea9181"], text=True, env=dict(os.environ, TZ="UTC")).strip()
    print("[info] commit 7fea9181 committer time UTC:", t_utc, "(local:", t.strip() + ")")
    judged("every v1-r7 row carries that time and commit", all("| %s | `7fea9181` |" % t_utc in l for l in r7rows))

    print("== item 2 (metrix/CLAUDE.md section 10; code-reviewer rule)")
    sec10 = claude.split("## 10.")[1]
    last = [l for l in sec10.split("\n") if l.strip()][-1]
    print("[info] section 10 last line:", last)
    judged("section 10 has '(出处：Review Gate 第 6 轮裁决，Owner 批准，本阶段，<UTC>)'",
           re.search(r"（出处：Review Gate 第 6 轮裁决，Owner 批准，本阶段，\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC）", last) is not None)
    rule = "引用仓库中已提交的原始输出（写明路径与行号）的判断视为已验证。"
    crl = cr.split("\n")
    judged("code-reviewer.md: new rule right after the 『未验证』 rule",
           rule in crl and crl.index(rule) == crl.index("未实际运行就作出的判断须标注『未验证』。") + 1)
    judged("code-reviewer.md frontmatter unchanged in the range",
           git("show", "%s:.claude/agents/code-reviewer.md" % BASE).split("---")[1] == cr.split("---")[1])

    print("== item 3 (DEFERRED_MINORS)")
    sec17 = dmin.split("### 1.7")[1].split("\n## ")[0]
    judged("1.7 exists with the note '正式流程代码统一要求不通过时打印 RESULT 并以非 0 退出'",
           "正式流程代码统一要求不通过时打印 RESULT 并以非 0 退出" in sec17)
    ids = re.findall(r"^\| (G\d) \|", sec17, re.M)
    print("[info] 1.7 entries:", ids, "| cite 待决第 6 项:", sec17.count("第 6 轮待决第 6 项"), "| cite 待决第 14 项:", sec17.count("第 6 轮待决第 14 项"))
    judged("1.7 covers pending items 6 (three points) and 14", ids == ["G1", "G2", "G3", "G4", "G5"] and
           all(("第 6 轮待决第 6 项第 %d 点" % k) in sec17 for k in (1, 2, 3)) and "第 6 轮待决第 14 项" in sec17)
    print("[info] DEFERRED_MINORS section 1.8 present yet:", "### 1.8" in dmin, "(the file announces it for this round's review items)")

    print("== ruling items 3 and 4 (fixed first sentence; metrix/CLAUDE.md section 5)")
    m = re.search(r"调用文字的第一句固定为：「(.+?)」", tasks)
    fixed = m.group(1)
    print("[info] fixed sentence in ROUND7_TASKS.md:", fixed)
    sec5 = claude.split("## 5.")[1].split("\n## ")[0]
    judged("CLAUDE.md section 5 contains the fixed sentence byte for byte", ("「%s」" % fixed) in sec5)
    judged("CLAUDE.md section 5: tools-line mismatch must stop, not replaceable",
           "两个版本的 tools 行不一致时必须停下,不得用此方法替代" in sec5)
    judged("CLAUDE.md section 5 attribution '第 7 轮裁决，Owner 批准，本阶段，<UTC>'",
           re.search(r"（出处：Review Gate 第 7 轮裁决，Owner 批准，本阶段，\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC）", sec5) is not None)
    for name in ("code-reviewer", "data-auditor"):
        p = os.path.join(repo, "metrix/e1-pilot/reviews", head, name + "_prompt.txt")
        first = open(p, encoding="utf-8").read().split("\n")[0]
        judged("%s prompt starts with the fixed sentence" % name, first == fixed.replace("<名称>", name), repr(first[:40]))
    print("[info] CLAUDE.md section 8: '只有「永久」的裁决可写入本文件' present:", "只有「永久」的裁决可写入本文件" in claude,
          "| 本阶段 attributions in the file:", claude.count("本阶段"))
    return bool(ok)


if __name__ == "__main__":
    run(main)
