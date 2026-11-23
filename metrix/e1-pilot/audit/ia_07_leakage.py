"""IA-7 (audit item 2): leakage checks L1-L6, Gate 0 part (protocol section 3; SPLIT_MANIFEST leakage_checks at the
freeze commit).  Parts that involve TEST are not run (no TEST data exists or is generated; L6 = anchor vs general DEV).
Each check is computed twice: on the auditor's own data (ia_03 .. ia_06 outputs) and on the Executor's files
(read as data only); both are compared with the Executor's leakage_report.json.

  L1  normalized_sha256 (auditor's own normalization of the 32 manifest templates) of the TRAIN, DEV, TEST, Y sets
      pairwise disjoint; value = number of hashes shared by two different sets.
  L2  Jaccard of word 4-gram sets (words = normalized template split on spaces) for every pair of templates from
      different sets (all relations); value = maximum; a pair with two empty 4-gram sets counts 0 (reported).
  L3a occurrences (case-insensitive substring, summed) of each of the 40 unread entities and 40 unread answers in
      train_F, train_S, train_Y and the anchor text.
  L3b occurrences of each of the 120 learned answers in the anchor text.
  L4  occurrences of each of the 320 DEV questions, verbatim (case-sensitive substring), in train_F, train_S, train_Y
      and the anchor text (case-insensitive count reported too).
  L5  learned / unread fact_id sets intersection + number of duplicates among the 320 entity / answer strings.
  L6  number of distinct word 13-grams (str.split(), case-sensitive) shared by the 512 anchor documents and the 100
      general DEV windows; 13-grams inside one document / window only; texts = Qwen decode of the ids fed to the model
      (anchor <= 128 ids, window <= 256 ids); report only: shared Qwen token-id 13-grams.
For the Executor's files the L6 texts are the decode (auditor's tokenizer) of the Executor's "ids", and those decodes
are compared with the Executor's "text" fields.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_07_leakage.py <repo_root> <qwen_tok_dir> <my_out_dir> <executor_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from itertools import combinations
from ia_common import sha, frozen_json, read_jsonl, load_qwen, run


def normalize(text):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(c if c in "abcdefghijklmnopqrstuvwxyz0123456789<> " else " " for c in s)
    return re.sub(r" {2,}", " ", s).strip(" ")


def ngrams(seq, n):
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def template_checks(sm):
    T = sm["templates"]
    sets = {}
    for t in T:
        sets.setdefault(t["set"], set()).add(sha(normalize(t["text"]).encode("utf-8")))
    shared = sorted({h for a, b in combinations(sorted(sets), 2) for h in sets[a] & sets[b]})
    best, pairs, empty = -1.0, [], 0
    for a, b in combinations(T, 2):
        if a["set"] == b["set"]:
            continue
        ga, gb = ngrams(normalize(a["text"]).split(" "), 4), ngrams(normalize(b["text"]).split(" "), 4)
        if not ga and not gb:
            empty += 1
            j = 0.0
        else:
            j = len(ga & gb) / len(ga | gb)
        if j > best + 1e-12:
            best, pairs = j, [(a["template_id"], b["template_id"])]
        elif abs(j - best) <= 1e-12:
            pairs.append((a["template_id"], b["template_id"]))
    n_pairs = sum(1 for a, b in combinations(T, 2) if a["set"] != b["set"])
    return {"L1": len(shared), "L1_shared": shared, "L1_sets": {k: len(v) for k, v in sets.items()},
            "L2": best, "L2_pairs_at_max": pairs, "L2_pairs": n_pairs, "L2_both_empty": empty}


def data_checks(facts, F, S, Y, dev_q, anchor_texts, anchor_ids, win_texts, win_ids):
    corp = {"train_F": F, "train_S": S, "train_Y": Y, "anchor_text": anchor_texts}
    low = {k: [t.lower() for t in v] for k, v in corp.items()}
    unread = [f for f in facts if f["exposure"] == "unread"]
    learned = [f for f in facts if f["exposure"] == "learned"]
    l3a_strings = [f["entity"] for f in unread] + [f["answer"] for f in unread]
    l3a = {(s, k): sum(t.count(s.lower()) for t in low[k]) for s in l3a_strings for k in corp}
    l3b = {s: sum(t.count(s.lower()) for t in low["anchor_text"]) for s in (f["answer"] for f in learned)}
    l4 = {(q, k): sum(t.count(q) for t in corp[k]) for q in dev_q for k in corp}
    l4i = sum(t.count(q.lower()) for q in dev_q for k in corp for t in low[k])
    ids_l, ids_u = {f["fact_id"] for f in learned}, {f["fact_id"] for f in unread}
    strings = [x for f in facts for x in (f["entity"], f["answer"])]
    aw = set().union(*(ngrams(t.split(), 13) for t in anchor_texts))
    gw = set().union(*(ngrams(t.split(), 13) for t in win_texts))
    at = set().union(*(ngrams(x, 13) for x in anchor_ids))
    gt = set().union(*(ngrams(x, 13) for x in win_ids))
    return {
        "L3a": sum(l3a.values()), "L3a_strings": len(l3a_strings), "L3a_hits": {f"{s}@{k}": n for (s, k), n in l3a.items() if n},
        "L3b": sum(l3b.values()), "L3b_strings": len(l3b), "L3b_hits": {s: n for s, n in l3b.items() if n},
        "L4": sum(l4.values()), "L4_questions": len(dev_q), "L4_hits": {f"{q}@{k}": n for (q, k), n in l4.items() if n},
        "L4_case_insensitive": l4i,
        "L5": len(ids_l & ids_u) + (len(strings) - len(set(strings))), "L5_fact_id_overlap": len(ids_l & ids_u),
        "L5_duplicate_strings": len(strings) - len(set(strings)), "L5_learned": len(ids_l), "L5_unread": len(ids_u),
        "L5_strings": len(strings), "L5_duplicates_case_insensitive": len(strings) - len({s.lower() for s in strings}),
        "L6": len(aw & gw), "L6_examples": sorted(aw & gw)[:3], "L6_anchor_docs": len(anchor_texts), "L6_windows": len(win_texts),
        "L6_anchor_word_13grams": len(aw), "L6_window_word_13grams": len(gw), "L6_token_id_shared": len(at & gt),
    }


def main():
    repo, qdir, mine, exdir = sys.argv[1:5]
    ok = True
    sm = frozen_json(repo, "SPLIT_MANIFEST.json")
    lc = sm["leakage_checks"]
    limits = {"L1": lc["L1_template_hash"]["limit"], "L2": lc["L2_template_ngram"]["limit"], "L3a": lc["L3a_unread_fact"]["limit"],
              "L3b": lc["L3b_learned_answer_in_anchor"]["limit"], "L4": lc["L4_question_text"]["limit"],
              "L5": lc["L5_identity"]["limit"], "L6": lc["L6_general_text"]["limit"]}
    print("limits (freeze-commit SPLIT_MANIFEST):", limits)
    print("manifest authoring results: L1", lc["L1_template_hash"]["authoring_result"], "| L2", lc["L2_template_ngram"]["authoring_result"])
    tc = template_checks(sm)
    print("\n== L1 / L2 (templates only; identical for both data sets)")
    print(json.dumps(tc, ensure_ascii=False))
    tok = load_qwen(qdir)

    # auditor's own data
    facts = json.load(open(os.path.join(mine, "facts.json"), encoding="utf-8"))
    F = [r["text"] for r in json.load(open(os.path.join(mine, "train_F.json"), encoding="utf-8"))]
    S = [r["text"] for r in read_jsonl(os.path.join(mine, "train_S.jsonl"))]
    Y = [r["text"] for r in json.load(open(os.path.join(mine, "train_Y.json"), encoding="utf-8"))]
    D = [r["question"] for r in json.load(open(os.path.join(mine, "dev_qa.json"), encoding="utf-8"))]
    A = json.load(open(os.path.join(mine, "anchor.json"), encoding="utf-8"))
    G = json.load(open(os.path.join(mine, "general.json"), encoding="utf-8"))
    my = data_checks(facts, F, S, Y, D, [a["text"] for a in A], [a["ids"] for a in A], [g["text"] for g in G], [g["ids"] for g in G])

    # Executor's files (data only)
    efacts = read_jsonl(os.path.join(exdir, "facts.jsonl"))
    eF = [r["text"] for r in read_jsonl(os.path.join(exdir, "train_F.jsonl"))]
    eS = [r["text"] for r in read_jsonl(os.path.join(exdir, "train_S.jsonl"))]
    eY = [r["text"] for r in read_jsonl(os.path.join(exdir, "train_Y.jsonl"))]
    eD = [r["question"] for r in read_jsonl(os.path.join(exdir, "dev_qa.jsonl"))]
    eA = read_jsonl(os.path.join(exdir, "anchor_text.jsonl"))
    eG = read_jsonl(os.path.join(exdir, "general_dev.jsonl"))
    eA_dec, eG_dec = [tok.decode(r["ids"]) for r in eA], [tok.decode(r["ids"]) for r in eG]
    print("\nExecutor anchor_text.jsonl: decode(ids) == text field for", sum(a == r["text"] for a, r in zip(eA_dec, eA)), "of", len(eA),
          "| general_dev.jsonl: decode(ids) == text field for", sum(a == r["text"] for a, r in zip(eG_dec, eG)), "of", len(eG))
    ok &= all(a == r["text"] for a, r in zip(eA_dec, eA)) and all(a == r["text"] for a, r in zip(eG_dec, eG))
    ex = data_checks(efacts, eF, eS, eY, eD, eA_dec, [r["ids"] for r in eA], eG_dec, [r["ids"] for r in eG])

    print("\n== L3a-L6 on the auditor's data / on the Executor's files")
    for k in my:
        same = my[k] == ex[k]
        print(f"  {k}: auditor {my[k]} | Executor files {ex[k]} | equal {same}")
        ok &= same

    rep = json.load(open(os.path.join(exdir, "leakage_report.json"), encoding="utf-8"))
    print("\n== comparison with the Executor's leakage_report.json")
    print("report: part", rep.get("part"), "| result", rep.get("result"), "| frozen_commit", rep.get("frozen_commit"))
    ok &= rep.get("frozen_commit") == "87a244db28a901f9e89282b50df76778ab5c2887" and rep.get("part") == "gate0"
    c = rep["checks"]
    vals = {"L1": tc["L1"], "L2": tc["L2"], "L3a": my["L3a"], "L3b": my["L3b"], "L4": my["L4"], "L5": my["L5"], "L6": my["L6"]}
    rows = [
        ("L1 value", vals["L1"], c["L1"]["value"]), ("L1 shared hashes", tc["L1_shared"], c["L1"]["detail"]["shared_hashes"]),
        ("L2 value", vals["L2"], c["L2"]["value"]), ("L2 pair", [list(p) for p in tc["L2_pairs_at_max"]][:1], [c["L2"]["detail"]["pair"]]),
        ("L2 n", 4, c["L2"]["detail"]["n"]),
        ("L3a value", vals["L3a"], c["L3a"]["value"]), ("L3a strings", my["L3a_strings"], c["L3a"]["detail"]["strings"]),
        ("L3a corpora", ["anchor_text", "train_F", "train_S", "train_Y"], sorted(c["L3a"]["detail"]["corpora"])),
        ("L3a found", my["L3a_hits"], c["L3a"]["detail"]["found"]),
        ("L3b value", vals["L3b"], c["L3b"]["value"]), ("L3b strings", my["L3b_strings"], c["L3b"]["detail"]["strings"]),
        ("L3b found", my["L3b_hits"], c["L3b"]["detail"]["found"]),
        ("L4 value", vals["L4"], c["L4"]["value"]), ("L4 questions", my["L4_questions"], c["L4"]["detail"]["questions"]),
        ("L4 corpora", ["anchor_text", "train_F", "train_S", "train_Y"], sorted(c["L4"]["detail"]["corpora"])),
        ("L4 found", my["L4_hits"], c["L4"]["detail"]["found"]), ("L4 part", "DEV", c["L4"]["detail"]["part"]),
        ("L5 value", vals["L5"], c["L5"]["value"]), ("L5 fact_id_overlap", my["L5_fact_id_overlap"], c["L5"]["detail"]["fact_id_overlap"]),
        ("L5 duplicate_strings", my["L5_duplicate_strings"], c["L5"]["detail"]["duplicate_strings"]),
        ("L5 learned", my["L5_learned"], c["L5"]["detail"]["learned"]), ("L5 unread", my["L5_unread"], c["L5"]["detail"]["unread"]),
        ("L5 strings", my["L5_strings"], c["L5"]["detail"]["strings"]),
        ("L6 value", vals["L6"], c["L6"]["value"]), ("L6 anchor_documents", my["L6_anchor_docs"], c["L6"]["detail"]["anchor_documents"]),
        ("L6 windows", my["L6_windows"], c["L6"]["detail"]["windows"]), ("L6 n", 13, c["L6"]["detail"]["n"]),
        ("L6 examples", [list(x) for x in my["L6_examples"]], c["L6"]["detail"]["examples"]),
        ("L6 report-only token-id 13-grams", my["L6_token_id_shared"], c["L6"]["detail"]["report_only_token_id_ngrams"]),
    ]
    for k in limits:
        rows.append((f"{k} limit", limits[k], c[k]["limit"]))
        within = vals[k] <= limits[k]
        rows.append((f"{k} within_limit", within, c[k]["within_limit"]))
        ok &= within
    rows.append(("result", "PASS" if all(vals[k] <= limits[k] for k in limits) else "FAIL", rep["result"]))
    rows.append(("check keys", sorted(limits), sorted(c)))
    for name, a, b in rows:
        same = a == b
        ok &= same
        print(f"  {name}: auditor {a!r} | Executor report {b!r} | equal {same}")
    for k in limits:
        print(f"AUDIT_VALUE leakage:{k} {vals[k]}")
    return bool(ok)


run(main)
