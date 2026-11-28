# data-auditor, E1-V1 round 2, item 1: were round-1 B1, M2, M3, M4 fixed, and do the new texts agree
# with the auditor's own implementation and the reference hashes?
#   B1: ARC numbers in protocol 7.1 / 15 and SUBMISSION_NOTE vs the ARC DEV source data.
#   M2: SPLIT_MANIFEST L8 'text' (and protocol L8 row) vs the auditor's L8 on D1 DEV / D2 DEV.
#   M3: SPLIT_MANIFEST L6 / L8 test_part (and protocol section 3 timing text): the count function written
#       from the new text, applied to the DEV files (TEST files are not generated or read).
#   M4: DATA_MANIFEST files.*.record definitions: files built from the record text reproduce the reference
#       hashes; alternative readings give different hashes (the text is discriminating).
# Only non-TEST inputs are read. No Executor code is imported, called or copied.
import re
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

D = A.TMP + "/v1data"  # regenerated in round 2 by a1_hashes.py and a5_damage.py (same bytes as round 1)


def chk(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def main():
    ok = True
    proto = open(A.V1 + "/METRIX_E1V1_PROTOCOL.md", encoding="utf-8").read()
    note = open(A.V1 + "/SUBMISSION_NOTE.md", encoding="utf-8").read()
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    sm = A.load_json(A.V1 + "/SPLIT_MANIFEST.json")
    gm = A.load_json(A.V1 + "/DAMAGE_MANIFEST.json")
    seed = dm["seeds"]["DATA_SEED"]

    # ============================ B1 ============================
    print("=== B1: ARC DEV source numbers")
    import pyarrow.parquet as pq
    ar = gm["d2"]["datasets"]["arc"]
    rows, per_file = [], []
    for src in ar["dev_source"]:
        p = A.ARC_DIR + "/" + src["file"]
        ok &= chk(f"ARC {src['file']} sha256", A.file_sha256(p), src["sha256"])
        r = pq.read_table(p).to_pylist()
        nopt = {}
        for x in r:
            nopt[len(x["choices"]["label"])] = nopt.get(len(x["choices"]["label"]), 0) + 1
        per_file.append((src["file"], len(r), dict(sorted(nopt.items()))))
        rows += r
    for f, n, c in per_file:
        print(f"  {f}: rows {n} by number of options {c}")
    total = len(rows)
    four = sum(1 for x in rows if len(x["choices"]["label"]) == 4 and len(x["choices"]["text"]) == 4 and x["answerKey"] in x["choices"]["label"])
    not4 = total - four
    order = list(range(total))
    A.rng_rule(seed, "d2:arc:validation:order").shuffle(order)
    kept, visited, excl = 0, 0, 0
    for idx in order:
        if kept == 800:
            break
        visited += 1
        x = rows[idx]
        if len(x["choices"]["label"]) == 4 and len(x["choices"]["text"]) == 4 and x["answerKey"] in x["choices"]["label"]:
            kept += 1  # L8 / L6 exclusions are 0 for ARC DEV (a2 / a5); they are recomputed in M2 / M3 below
        else:
            excl += 1
    left4 = four - kept
    print(f"  computed: DEV source rows {total}, 4-option rows {four}, other {not4}; shuffled order: visited {visited} rows to reach {kept} items, excluded {excl}; 4-option rows left after DEV {left4}; rows not visited {total - visited}")
    m71 = re.search(r"只用恰好 4 个选项的题\(DEV 来源 (\d+) 行中 (\d+) 行为 4 个选项、(\d+) 行不是[,，]`([^`]+)`[;；]撰写时按打乱顺序访问到第 (\d+) 行即凑满 (\d+) 题[,，]其间排除 (\d+) 行\)", proto)
    print("  protocol 7.1 sentence:", m71.group(0) if m71 else None)
    if m71:
        g = [int(m71.group(i)) for i in (1, 2, 3, 5, 6, 7)]
        ok &= chk("protocol 7.1 (source rows, 4-option, other, visited, items, excluded)", g, [total, four, not4, visited, kept, excl])
        cited = A.V1 + "/" + m71.group(4)
        txt = open(cited, encoding="utf-8").read()
        ok &= chk(f"cited file {m71.group(4)} contains the 869 / 862 line", f"ARC validation rows (Challenge then Easy) {total} | by number of labels {{4: {four}" in txt, True)
    else:
        ok = False
        print("DIFF protocol 7.1 ARC sentence not found")
    m15 = re.search(r"ARC 的 DEV 来源只有 (\d+) 题\(其中 (\d+) 题为 4 个选项\)[,，]抽 (\d+) 题后只余 (\d+) 题", proto)
    print("  protocol 15 sentence:", m15.group(0) if m15 else None)
    if m15:
        ok &= chk("protocol 15 (source rows, 4-option, drawn, left)", [int(m15.group(i)) for i in range(1, 5)], [total, four, kept, left4])
    else:
        ok = False
        print("DIFF protocol 15 ARC sentence not found")
    mn = re.search(r"备选 ARC (\d+) 题\(按打乱顺序访问 (\d+) 行[,，]其中 (\d+) 行因不是 4 个选项被排除[;；]DEV 来源 (\d+) 行中共有 (\d+) 行不是 4 个选项", note)
    print("  SUBMISSION_NOTE sentence:", mn.group(0) if mn else None)
    if mn:
        ok &= chk("SUBMISSION_NOTE (items, visited, excluded, source rows, other)", [int(mn.group(i)) for i in range(1, 6)], [kept, visited, excl, total, not4])
    ok &= chk("DAMAGE_MANIFEST arc.authoring_dev.excluded.not_4_choices", ar["authoring_dev"]["excluded"]["not_4_choices"], excl)
    old_bad = [s for s in ("863", "DEV 来源中 6 题", "余 63") if s in proto or s in note]
    ok &= chk("round-1 wrong numbers ('863', 'DEV 来源中 6 题', '余 63') left in protocol / SUBMISSION_NOTE", old_bad, [])

    # ============================ M2 ============================
    print("=== M2: L8 'text'")
    l8 = sm["leakage_checks"]["L8_fictional_strings_in_damage_sets"]
    print("  SPLIT_MANIFEST L8.text:", l8["text"])
    row = [l for l in proto.splitlines() if l.startswith("| L8 |")][0]
    print("  protocol L8 row:", row)
    ok &= chk("protocol L8 row defines D1 text as the decoded <= 256 model ids (text field), not the source document; D2 = prompt p",
              all(s in row for s in ("送入模型的 id(最多 256 个)", "`text` 字段", "不是整篇源文档", "D2 为题面 `p`")), True)
    ok &= chk("SPLIT_MANIFEST L8.text says the same", all(s in l8["text"] for s in ("text field of the window", "decode of the ids fed to the model", "not the whole source document", "D2: the prompt p")), True)
    ok &= chk("DATA_MANIFEST general_dev record: text = tokenizer.decode(ids) with default arguments",
              "text: tokenizer.decode(ids) with default arguments" in dm["files"]["general_dev.jsonl"]["record"], True)
    facts = A.read_jsonl(D + "/facts.jsonl")
    v1_lower = [f["entity"].lower() for f in facts] + [f["answer"].lower() for f in facts]
    ok &= chk("V1 strings (distinct, lowercased)", len(set(v1_lower)), 640)
    tok = A.load_qwen_tokenizer(dm["model"]["tokenizer"]["files_sha256"])
    gd = A.read_jsonl(D + "/general_dev.jsonl")
    ok &= chk("general_dev.jsonl (auditor) canonical sha256 = reference", A.jsonl_sha(gd), dm["files"]["general_dev.jsonl"]["reference_canonical_sha256"])
    ok &= chk("general_dev windows whose text != tokenizer.decode(ids)", sum(1 for w in gd if w["text"] != tok.decode(w["ids"])), 0)
    ok &= chk("general_dev windows with more than 256 ids", sum(1 for w in gd if len(w["ids"]) > 256), 0)
    l8_d1 = sum(1 for w in gd if A.whole_word_hits(w["text"], v1_lower))
    md = A.read_jsonl(D + "/d2_dev.jsonl")
    ad = A.read_jsonl(D + "/d2_dev_arc.jsonl")
    l8_mm = sum(1 for x in md if A.whole_word_hits(x["prompt"], v1_lower))
    l8_arc = sum(1 for x in ad if A.whole_word_hits(x["prompt"], v1_lower))
    ok &= chk("L8 D1 DEV (window text field) = SPLIT authoring_result.d1_dev", l8_d1, l8["authoring_result"]["d1_dev"])
    ok &= chk("L8 D2 DEV MMLU (prompt p) = SPLIT authoring_result.d2_dev", l8_mm, l8["authoring_result"]["d2_dev"])
    ok &= chk("L8 D2 DEV ARC (prompt p), no manifest value, expected 0", l8_arc, 0)
    # the reading that the new text rules out: the whole parcae-decoded source document (DEV rows only)
    import json
    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(A.PARCAE_TOK)
    PREFIX = re.compile(rb'^\{"domain": "([^"\\]*)", "split": "([^"\\]*)", ')
    full = {}
    with open(A.EVAL_SETS, "rb") as f:
        for raw in f:
            m = PREFIX.match(raw)
            if m and m.group(2) == b"dev":
                r = json.loads(raw)  # dev rows only
                full[r["doc_id"]] = ptok.decode(r["tokens"], skip_special_tokens=True)
    alt = sum(1 for w in gd if A.whole_word_hits(full[w["doc_id"]], v1_lower))
    longer = sum(1 for w in gd if len(full[w["doc_id"]]) > len(w["text"]))
    print(f"  report only: L8 on the whole source document (reading excluded by the new text) D1 DEV {alt}; windows whose source document is longer than the window text {longer} of {len(gd)}")

    # ============================ M3 ============================
    print("=== M3: L6 / L8 test_part")
    l6 = sm["leakage_checks"]["L6_anchor_ngram"]
    print("  SPLIT_MANIFEST L6.test_part.count:", l6["test_part"]["count"])
    print("  SPLIT_MANIFEST L8.test_part:", l8["test_part"])
    tline = [l for l in proto.splitlines() if l.startswith("**时机**:L1、L2 只用模板")][0]
    print("  protocol section 3 timing:", tline)
    ok &= chk("L6 count: each file separately, anchor set vs the file's set, distinct elements of the intersection",
              all(s in l6["test_part"]["count"] for s in ("for each of general_test.jsonl and d2_test.jsonl separately", "512 anchor documents merged into one set",
                                                          "all windows (D1) or all prompts (D2) of the file merged into another", "13-grams within each document",
                                                          "number of distinct elements of the intersection", "anchor <= 128 ids, window <= 256 ids", "or the prompt p")), True)
    ok &= chk("L8 test_part: each file separately", "counted for general_test.jsonl and d2_test.jsonl separately" in l8["test_part"], True)
    ok &= chk("protocol section 3 says the same (D1 TEST and D2 TEST counted separately; L8 per file)",
              all(s in tline for s in ("对 D1 TEST 与 D2 TEST 各自单独计数", "`general_test.jsonl` 全部窗口", "`d2_test.jsonl` 全部题面", "各计交集的种类数", "L8 对两个文件各计单位数")), True)
    anchor = A.read_jsonl(D + "/anchor_text.jsonl")
    ok &= chk("anchor_text.jsonl (auditor) canonical sha256 = reference", A.jsonl_sha(anchor), dm["files"]["anchor_text.jsonl"]["reference_canonical_sha256"])
    ok &= chk("anchor docs whose text != tokenizer.decode(ids)", sum(1 for a in anchor if a["text"] != tok.decode(a["ids"])), 0)
    ok &= chk("anchor docs with more than 128 ids", sum(1 for a in anchor if len(a["ids"]) > 128), 0)

    def l6_count(anchor_texts, unit_texts):
        """The L6 test_part count, written from the SPLIT_MANIFEST text: per-document word 13-grams
        (str.split(), case-sensitive), merged per side, distinct elements of the intersection."""
        sa, su = set(), set()
        for t in anchor_texts:
            sa |= A.word_ngrams(t, 13)
        for t in unit_texts:
            su |= A.word_ngrams(t, 13)
        return len(sa & su)

    at = [a["text"] for a in anchor]
    c_d1 = l6_count(at, [w["text"] for w in gd])
    c_mm = l6_count(at, [x["prompt"] for x in md])
    c_arc = l6_count(at, [x["prompt"] for x in ad])
    ok &= chk("L6 count on general_dev.jsonl (DEV stand-in for general_test.jsonl) = authoring_result.d1_dev", c_d1, l6["authoring_result"]["d1_dev"])
    ok &= chk("L6 count on d2_dev.jsonl MMLU (DEV stand-in for d2_test.jsonl) = authoring_result.d2_dev", c_mm, l6["authoring_result"]["d2_dev"])
    ok &= chk("L6 count on d2_dev.jsonl ARC, no manifest value, expected 0", c_arc, 0)
    print(f"  report only: the other reading (D1 and D2 merged into one set) gives {l6_count(at, [w['text'] for w in gd] + [x['prompt'] for x in md])} on DEV; separate counts {c_d1}, {c_mm}")
    # the count function is not trivially 0: a constructed unit containing one anchor 13-gram and one spanning two documents
    w0 = at[0].split()
    probe_in = " ".join(["probe"] + w0[:13] + ["probe"])
    probe_across = " ".join(at[0].split()[-6:] + at[1].split()[:7])  # 13 words spanning anchor docs 0 and 1
    ok &= chk("count function on a constructed unit holding the first 13 words of anchor doc 0", l6_count(at, [probe_in]), 1)
    cross = A.word_ngrams(probe_across, 13)
    within = set()
    for t in at[:2]:
        within |= A.word_ngrams(t, 13)
    ok &= chk("13-gram spanning the end of anchor doc 0 and the start of doc 1 is not an anchor 13-gram (no concatenation across documents)",
              len(cross & within), 0)

    # ============================ M4 ============================
    print("=== M4: DATA_MANIFEST files.*.record")
    for n, v in dm["files"].items():
        print(f"  {n}: {v['record']}")
    ref = {n: v["reference_canonical_sha256"] for n, v in dm["files"].items()}
    # facts
    ok &= chk("facts.jsonl built per record text = reference", A.jsonl_sha(facts), ref["facts.jsonl"])
    ok &= chk("facts exposure values", sorted({f["exposure"] for f in facts}), ["learned", "unread"])
    ok &= chk("facts stratum values", sorted({f["stratum"] for f in facts}), ["natural", "random"])
    alt_f = [dict(f, exposure={"learned": "L", "unread": "U"}[f["exposure"]]) for f in facts]
    alt_s = [dict(f, stratum={"natural": "nat", "random": "rnd"}[f["stratum"]]) for f in facts]
    ok &= chk("alternative reading exposure 'L'/'U' differs from reference", A.jsonl_sha(alt_f) != ref["facts.jsonl"], True)
    ok &= chk("alternative reading stratum 'nat'/'rnd' differs from reference", A.jsonl_sha(alt_s) != ref["facts.jsonl"], True)
    # the five fact files whose record text did not change
    for n in ("train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl"):
        ok &= chk(f"{n} (auditor) = reference", A.jsonl_sha(A.read_jsonl(D + "/" + n)), ref[n])
    ok &= chk("candidates.json (auditor) = reference", A.canon_sha(A.load_json(D + "/candidates.json")), ref["candidates.json"])
    # anchor_text: rebuild from the parquet per the record text, then alternative readings
    ap = A.ANCHOR_PARQUET
    ok &= chk("anchor parquet sha256", A.file_sha256(ap), "6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22")
    pf = pq.ParquetFile(ap)
    docs, rowno = [], 0
    for rg in range(pf.metadata.num_row_groups):
        for t in pf.read_row_group(rg, columns=["text"]).column("text").to_pylist():
            if len(t) >= 600:
                docs.append((rowno, t))
            rowno += 1
            if len(docs) == 512:
                break
        if len(docs) == 512:
            break

    def anchor_rows(doc_base=0, row_mode="parquet", add_special=False, dec_kw=None):
        out = []
        for i, (r, t) in enumerate(docs):
            ids = tok.encode(t, add_special_tokens=add_special)[:128]
            src = r if row_mode == "parquet" else (i if row_mode == "selected" else r + 1)
            out.append({"doc": i + doc_base, "source_row": src, "ids": ids, "text": tok.decode(ids, **(dec_kw or {}))})
        return out

    base = anchor_rows()
    ok &= chk("anchor_text.jsonl rebuilt per record text = reference", A.jsonl_sha(base), ref["anchor_text.jsonl"])
    variants = {
        "doc 1-based": anchor_rows(doc_base=1),
        "source_row = index among selected documents": anchor_rows(row_mode="selected"),
        "source_row 1-based": anchor_rows(row_mode="plus1"),
        "ids = encode(text) with add_special_tokens=True": anchor_rows(add_special=True),
        "text = decode(ids, skip_special_tokens=True)": anchor_rows(dec_kw={"skip_special_tokens": True}),
        "text = decode(ids, clean_up_tokenization_spaces=True)": anchor_rows(dec_kw={"clean_up_tokenization_spaces": True}),
    }
    for k, rws in variants.items():
        print(f"  anchor alternative '{k}': equal to reference {A.jsonl_sha(rws) == ref['anchor_text.jsonl']}")
    # general_dev: alternative readings
    print(f"  general_dev alternative 'text = whole parcae-decoded document': equal to reference {A.jsonl_sha([dict(w, text=full[w['doc_id']]) for w in gd]) == ref['general_dev.jsonl']}")
    print(f"  general_dev alternative 'text = decode(ids, clean_up_tokenization_spaces=True)': equal to reference {A.jsonl_sha([dict(w, text=tok.decode(w['ids'], clean_up_tokenization_spaces=True)) for w in gd]) == ref['general_dev.jsonl']}")
    print(f"  general_dev alternative 'text = decode(ids, skip_special_tokens=True)': equal to reference {A.jsonl_sha([dict(w, text=tok.decode(w['ids'], skip_special_tokens=True)) for w in gd]) == ref['general_dev.jsonl']}")
    print(f"  general_dev alternative 'ids = encode(document) with add_special_tokens=True, first 256': equal to reference {A.jsonl_sha([dict(w, ids=tok.encode(full[w['doc_id']])[:256], text=tok.decode(tok.encode(full[w['doc_id']])[:256])) for w in gd]) == ref['general_dev.jsonl']}")
    # d2_dev: record fields
    mm_rows = pq.read_table(A.MMLU_DIR + "/" + gm["d2"]["datasets"]["mmlu"]["dev_source"]["file"]).to_pylist()
    ok &= chk("d2_dev MMLU (auditor) = reference", A.jsonl_sha(md), ref["d2_dev.jsonl"]["mmlu"])
    ok &= chk("d2_dev ARC (auditor) = reference", A.jsonl_sha(ad), ref["d2_dev.jsonl"]["arc"])
    ok &= chk("d2_dev item = 0-based position (MMLU, ARC)", (all(x["item"] == i for i, x in enumerate(md)), all(x["item"] == i for i, x in enumerate(ad))), (True, True))
    ok &= chk("d2_dev MMLU subject = parquet subject of source_row", all(x["subject"] == mm_rows[x["source_row"]]["subject"] for x in md), True)
    ok &= chk("d2_dev ARC subject = item id of source_row (Challenge then Easy)", all(x["subject"] == rows[x["source_row"]]["id"] for x in ad), True)
    ok &= chk("d2_dev answer = correct letter (MMLU)", all(x["answer"] == "ABCD"[mm_rows[x["source_row"]]["answer"]] for x in md), True)
    ok &= chk("d2_dev answer = correct letter (ARC)", all(x["answer"] == "ABCD"[rows[x["source_row"]]["choices"]["label"].index(rows[x["source_row"]]["answerKey"])] for x in ad), True)
    nch = 299  # rows of ARC-Challenge validation
    alt_arc_row = [dict(x, source_row=x["source_row"] if x["source_row"] < nch else x["source_row"] - nch) for x in ad]
    print(f"  d2 alternative 'item 1-based' MMLU: equal to reference {A.jsonl_sha([dict(x, item=x['item'] + 1) for x in md]) == ref['d2_dev.jsonl']['mmlu']}")
    print(f"  d2 alternative 'ARC source_row = row within its own file': equal to reference {A.jsonl_sha(alt_arc_row) == ref['d2_dev.jsonl']['arc']}")
    print(f"  d2 alternative 'ARC subject = ARC-Challenge / ARC-Easy': equal to reference {A.jsonl_sha([dict(x, subject='ARC-Challenge' if x['source_row'] < nch else 'ARC-Easy') for x in ad]) == ref['d2_dev.jsonl']['arc']}")
    ok &= chk("TEST records defined by reference to the DEV records", (dm["files"]["general_test.jsonl"]["record"], dm["files"]["d2_test.jsonl"]["record"]), ("as general_dev.jsonl", "as d2_dev.jsonl"))
    ok &= chk("ARC TEST order text: Challenge test then Easy test (so 'as d2_dev.jsonl' gives source_row = index in Challenge then Easy)",
              gm["d2"]["datasets"]["arc"]["test_order"].startswith("rows of Challenge test then Easy test (indices 0..3547)"), True)
    print("ITEM1 round 2:", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
