# data-auditor, E1-V1 round 1, item 5: damage evaluation sets (DEV only).
# Builds D1 DEV (general_dev.jsonl) and D2 DEV (MMLU, alternative ARC) from the DAMAGE_MANIFEST /
# protocol 7.2 text, compares hashes and counts; counts eval_sets.jsonl test rows from row-prefix
# bytes only (no decoding, no json parsing of test rows); D2 TEST sources: whole-file sha256 and
# parquet footer row counts only (no row is read).
import re
import statistics
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

OUT = A.TMP + "/v1data"
PREFIX = re.compile(rb'^\{"domain": "([a-z0-9_]+)", "split": "([a-z]+)", ')


def cmp(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def stats(xs):
    return {"n": len(xs), "sum": sum(xs), "mean": round(sum(xs) / len(xs), 3), "min": min(xs),
            "median": statistics.median(xs), "max": max(xs)}


def main():
    allok = True
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    gm = A.load_json(A.V1 + "/DAMAGE_MANIFEST.json")
    tok = A.load_qwen_tokenizer(dm["model"]["tokenizer"]["files_sha256"])
    facts = A.read_jsonl(OUT + "/facts.jsonl")
    v1_strings = [f["entity"] for f in facts] + [f["answer"] for f in facts]
    v1_lower = [s.lower() for s in v1_strings]
    print("V1 strings for L8:", len(v1_strings), "distinct lowercase", len(set(v1_lower)))
    anchor = A.read_jsonl(OUT + "/anchor_text.jsonl")
    anchor_word13 = set()
    anchor_id13 = set()
    for a in anchor:
        anchor_word13 |= A.word_ngrams(a["text"])
        anchor_id13 |= A.id_ngrams(a["ids"])
    print("anchor distinct word 13-grams", len(anchor_word13), "| token-id 13-grams", len(anchor_id13))

    # ================= D1 =================
    d1 = gm["d1"]
    allok &= cmp("eval_sets.jsonl sha256", A.file_sha256(A.EVAL_SETS), d1["source_file_sha256"])
    allok &= cmp("parcae tokenizer.json sha256", A.file_sha256(A.PARCAE_TOK), d1["decode_tokenizer_json_sha256"])
    counts, unmatched = {}, 0
    dev_rows = {}
    test_rank = {}
    with open(A.EVAL_SETS, "rb") as f:
        for lineno, raw in enumerate(f):
            m = PREFIX.match(raw)
            if not m:
                unmatched += 1
                continue
            dom, split = m.group(1).decode(), m.group(2).decode()
            counts[(dom, split)] = counts.get((dom, split), 0) + 1
            if split == "dev":
                import json
                r = json.loads(raw)  # dev rows only
                assert r["domain"] == dom and r["split"] == "dev"
                dev_rows.setdefault(dom, []).append((lineno, r))
            # test rows: nothing beyond the prefix match above
    print("eval_sets rows by (domain, split) from row prefixes:", dict(sorted(counts.items())), "| rows without the prefix:", unmatched)
    for dom in d1["domains"]:
        allok &= cmp(f"D1 {dom} dev rows", counts.get((dom, "dev"), 0), d1["dev"]["per_domain"])
        avail = counts.get((dom, "test"), 0) - 25
        allok &= cmp(f"D1 {dom} test rows after skipping the first 25 (Pilot TEST windows)", avail, d1["test"]["available_per_domain_after_skip"])
        print(f"   {dom}: test rows {counts.get((dom, 'test'), 0)}; needed for D1 TEST {d1['test']['per_domain']}; slack before exclusions {avail - d1['test']['per_domain']}")
    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(A.PARCAE_TOK)
    windows, excluded = [], {"L8": 0, "L6": 0}
    excl_detail = []
    for dom in d1["domains"]:
        for lineno, r in dev_rows[dom]:
            full = ptok.decode(r["tokens"], skip_special_tokens=True)
            ids = tok.encode(full, add_special_tokens=False)[:256]
            text = tok.decode(ids)
            if A.whole_word_hits(text, v1_lower):
                excluded["L8"] += 1
                excl_detail.append(("L8", r["doc_id"]))
                continue
            if A.word_ngrams(text) & anchor_word13:
                excluded["L6"] += 1
                excl_detail.append(("L6", r["doc_id"]))
                continue
            windows.append({"domain": dom, "doc_id": r["doc_id"], "ids": ids, "text": text, "_full": full})
    print("D1 DEV kept", len(windows), "| excluded", excluded, excl_detail)
    per = {}
    for w in windows:
        per[w["domain"]] = per.get(w["domain"], 0) + 1
    print("D1 DEV kept per domain", per)
    rec = [{k: w[k] for k in ("domain", "doc_id", "ids", "text")} for w in windows]
    allok &= cmp("general_dev.jsonl canonical sha256", A.jsonl_sha(rec), dm["files"]["general_dev.jsonl"]["reference_canonical_sha256"])
    allok &= cmp("general_dev.jsonl = DAMAGE_MANIFEST d1.dev.authoring.canonical_sha256", A.jsonl_sha(rec), d1["dev"]["authoring"]["canonical_sha256"])
    allok &= cmp("D1 DEV kept", len(rec), d1["dev"]["authoring"]["kept"])
    allok &= cmp("D1 DEV excluded", sum(excluded.values()), d1["dev"]["authoring"]["excluded"])
    st = stats([len(w["ids"]) for w in windows])
    print("D1 DEV ids per window", st)
    allok &= cmp("D1 DEV ids_per_window_mean", st["mean"], d1["dev"]["authoring"]["ids_per_window_mean"])
    # also: L8 on the full parcae-decoded text (stricter than the window text), report only
    full_hits = sum(1 for w in windows if A.whole_word_hits(w["_full"], v1_lower))
    print("report only: D1 DEV rows whose full (untruncated) decoded text contains a V1 string as a whole word:", full_hits)
    # Pilot D1 DEV = first 25 dev rows per domain: overlap with V1 D1 DEV (allowed, both DEV), report
    print("report only: V1 D1 DEV uses all 100 dev rows per domain, so it contains the 100 Pilot D1 DEV windows (first 25 dev rows per domain); both are DEV")
    A.write_jsonl(OUT + "/general_dev.jsonl", rec)

    # ================= D2 =================
    import pyarrow.parquet as pq
    d2 = gm["d2"]
    letters = "ABCD"
    lt = {l: tok.encode(" " + l, add_special_tokens=False) for l in letters}
    print("letter tokens", lt)
    allok &= cmp("' A'..' D' single-token ids", {l: v for l, v in lt.items()}, {l: [i] for l, i in d2["letter_token_ids"].items()})
    I = "Answer the following multiple choice question with the letter of the correct option."

    def prompt(question, options):
        p = I + "\n\n" + question.strip() + "\n"
        p += "A. " + options[0] + "\n" + "B. " + options[1] + "\n" + "C. " + options[2] + "\n" + "D. " + options[3]
        return p

    def ctx_len(p):
        s = tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True,
                                    enable_thinking=False) + "The answer is"
        return len(tok.encode(s, add_special_tokens=False))

    seed = dm["seeds"]["DATA_SEED"]

    def build(rows, purpose, kind):
        order = list(range(len(rows)))
        A.rng_rule(seed, purpose).shuffle(order)
        out, exc, visited = [], {}, 0
        for idx in order:
            if len(out) == 800:
                break
            visited += 1
            r = rows[idx]
            if kind == "mmlu":
                opts = [str(c).strip() for c in r["choices"]]
                ok4 = len(r["choices"]) == 4 and r["answer"] in (0, 1, 2, 3)
                ans = letters[r["answer"]] if ok4 else None
                subj = r["subject"]
            else:
                labels = list(r["choices"]["label"])
                opts = [str(c).strip() for c in r["choices"]["text"]]
                ok4 = len(labels) == 4 and len(opts) == 4 and r["answerKey"] in labels
                ans = letters[labels.index(r["answerKey"])] if ok4 else None
                subj = r["id"]
            if not ok4:
                exc["not_4_choices_or_answer"] = exc.get("not_4_choices_or_answer", 0) + 1
                continue
            p = prompt(r["question"], opts)
            if A.whole_word_hits(p, v1_lower):
                exc["L8"] = exc.get("L8", 0) + 1
                continue
            if A.word_ngrams(p) & anchor_word13:
                exc["L6"] = exc.get("L6", 0) + 1
                continue
            out.append({"item": len(out), "source_row": idx, "subject": subj, "prompt": p, "answer": ans})
        return out, exc, visited

    # ---- MMLU ----
    mm = d2["datasets"]["mmlu"]
    vpath = A.MMLU_DIR + "/" + mm["dev_source"]["file"]
    tpath = A.MMLU_DIR + "/" + mm["test_source"]["file"]
    allok &= cmp("MMLU validation sha256", A.file_sha256(vpath), mm["dev_source"]["sha256"])
    allok &= cmp("MMLU test sha256 (whole file)", A.file_sha256(tpath), mm["test_source"]["sha256"])
    vrows = pq.read_table(vpath).to_pylist()
    allok &= cmp("MMLU validation rows", len(vrows), mm["dev_source"]["rows"])
    allok &= cmp("MMLU test rows (parquet footer only)", pq.ParquetFile(tpath).metadata.num_rows, mm["test_source"]["rows"])
    print("MMLU validation columns", sorted(vrows[0].keys()))
    ncho = {}
    for r in vrows:
        ncho[len(r["choices"])] = ncho.get(len(r["choices"]), 0) + 1
    print("MMLU validation rows by number of choices", ncho, "| answers outside 0-3", sum(1 for r in vrows if r["answer"] not in (0, 1, 2, 3)))
    md, mexc, mvis = build(vrows, "d2:mmlu:validation:order", "mmlu")
    print("MMLU D2 DEV items", len(md), "| rows visited", mvis, "| excluded", mexc)
    allok &= cmp("d2_dev.jsonl (MMLU) canonical sha256", A.jsonl_sha(md), mm["authoring_dev"]["canonical_sha256"])
    allok &= cmp("d2_dev.jsonl (MMLU) = DATA_MANIFEST files.d2_dev.jsonl.mmlu", A.jsonl_sha(md), dm["files"]["d2_dev.jsonl"]["reference_canonical_sha256"]["mmlu"])
    allok &= cmp("MMLU DEV items", len(md), mm["authoring_dev"]["items"])
    allok &= cmp("MMLU DEV excluded", sum(mexc.values()), mm["authoring_dev"]["excluded"])
    allok &= cmp("MMLU DEV rows_visited", mvis, mm["authoring_dev"]["rows_visited"])
    subj = len({x["subject"] for x in md})
    allok &= cmp("MMLU DEV subjects", subj, mm["authoring_dev"]["subjects"])
    let = {l: sum(1 for x in md if x["answer"] == l) for l in letters}
    print("MMLU DEV answer letters", let)
    cl = [ctx_len(x["prompt"]) for x in md]
    cst = stats(cl)
    print("MMLU DEV context ids per item (chat(p) + 'The answer is')", cst)
    allok &= cmp("MMLU DEV context_ids_mean", cst["mean"], mm["authoring_dev"]["context_ids_mean"])
    print("MMLU validation rows not used by D2 DEV:", len(vrows) - mvis)
    A.write_jsonl(OUT + "/d2_dev.jsonl", md)

    # ---- ARC ----
    ar = d2["datasets"]["arc"]
    arows = []
    for src in ar["dev_source"]:
        p = A.ARC_DIR + "/" + src["file"]
        allok &= cmp(f"ARC {src['file']} sha256", A.file_sha256(p), src["sha256"])
        rows = pq.read_table(p).to_pylist()
        allok &= cmp(f"ARC {src['file']} rows", len(rows), src["rows"])
        arows += rows
    for src in ar["test_source"]:
        p = A.ARC_DIR + "/" + src["file"]
        allok &= cmp(f"ARC {src['file']} sha256 (whole file)", A.file_sha256(p), src["sha256"])
        allok &= cmp(f"ARC {src['file']} rows (parquet footer only)", pq.ParquetFile(p).metadata.num_rows, src["rows"])
    nl = {}
    for r in arows:
        nl[len(r["choices"]["label"])] = nl.get(len(r["choices"]["label"]), 0) + 1
    print("ARC validation rows (Challenge then Easy)", len(arows), "| by number of labels", nl,
          "| label sets", sorted({tuple(r["choices"]["label"]) for r in arows}))
    ad, aexc, avis = build(arows, "d2:arc:validation:order", "arc")
    print("ARC D2 DEV items", len(ad), "| rows visited", avis, "| excluded", aexc)
    allok &= cmp("d2_dev.jsonl (ARC) canonical sha256", A.jsonl_sha(ad), ar["authoring_dev"]["canonical_sha256"])
    allok &= cmp("d2_dev.jsonl (ARC) = DATA_MANIFEST files.d2_dev.jsonl.arc", A.jsonl_sha(ad), dm["files"]["d2_dev.jsonl"]["reference_canonical_sha256"]["arc"])
    allok &= cmp("ARC DEV items", len(ad), ar["authoring_dev"]["items"])
    allok &= cmp("ARC DEV excluded not_4_choices", aexc.get("not_4_choices_or_answer", 0), ar["authoring_dev"]["excluded"]["not_4_choices"])
    print("ARC DEV other exclusions (L8, L6):", {k: v for k, v in aexc.items() if k != "not_4_choices_or_answer"})
    print("ARC validation rows remaining after DEV:", len(arows) - avis, "| 4-choice rows in DEV source", nl.get(4, 0))
    acl = [ctx_len(x["prompt"]) for x in ad]
    ast = stats(acl)
    print("ARC DEV context ids per item", ast)
    allok &= cmp("ARC DEV context_ids_mean", ast["mean"], ar["authoring_dev"]["context_ids_mean"])
    print("ARC DEV answer letters", {l: sum(1 for x in ad if x["answer"] == l) for l in letters})
    A.write_jsonl(OUT + "/d2_dev_arc.jsonl", ad)
    for name in ["general_dev.jsonl", "d2_dev.jsonl", "d2_dev_arc.jsonl"]:
        print(f"written {name} byte_sha256 {A.file_sha256(OUT + '/' + name)}")
    print("ITEM5:", "ALL MATCH" if allok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
