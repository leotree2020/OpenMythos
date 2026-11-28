# data-auditor, E1-V1 freeze audit, item (c): independent regeneration of every non-TEST data file
# from the rules of the protocol and the manifests of the freeze commit (read with git cat-file), on CPU
# with the tokenizer only. Canonical SHA-256 of every generated file (parsed back from disk, re-serialized
# with the hashing rule of DATA_MANIFEST.json: hashing) compared with the reference values recorded in
# the freeze commit's manifests and protocol text. Plus the Pilot fact hash and the template-set hash.
# Nothing of TEST is generated or read: no test_qa / general_test / d2_test; eval_sets.jsonl test rows are
# skipped on the row-prefix bytes (protocol section 0 regex) before any decoding; MMLU / ARC test parquets
# are not opened here at all.
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L  # noqa: E402

RESULTS = []  # (label, got, [(source, expected)])


def proto_locations(proto_lines, h):
    out, head = [], ""
    for i, line in enumerate(proto_lines, 1):
        if line.startswith("#"):
            head = line.strip()
        if h in line:
            out.append(f"line {i} ({head})")
    return out


def check(label, got, refs, proto_lines, in_protocol):
    ok = True
    print(f"\n[{label}] computed {got}")
    for src, exp in refs:
        eq = got == exp
        ok &= eq
        print(f"   {src} = {exp} | equal {eq}")
    locs = proto_locations(proto_lines, got)
    if in_protocol:
        print(f"   protocol (freeze commit) contains the computed value at: {locs if locs else 'NOWHERE'}")
        ok &= bool(locs)
    else:
        print(f"   protocol (freeze commit): not recorded there (manifest only); occurrences of the computed value: {len(locs)}")
    RESULTS.append((label, got, ok))
    return ok


def main():
    t0 = time.time()
    os.makedirs(L.DATA, exist_ok=True)
    dm = L.git_json(L.FREEZE, "metrix/e1-v1/DATA_MANIFEST.json")
    sm = L.git_json(L.FREEZE, "metrix/e1-v1/SPLIT_MANIFEST.json")
    gm = L.git_json(L.FREEZE, "metrix/e1-v1/DAMAGE_MANIFEST.json")
    proto = L.git_blob(L.FREEZE, "metrix/e1-v1/METRIX_E1V1_PROTOCOL.md").decode("utf-8").split("\n")
    psm = L.git_json(L.FREEZE, "metrix/e1-pilot/SPLIT_MANIFEST.json")
    pdm = L.git_json(L.FREEZE, "metrix/e1-pilot/DATA_MANIFEST.json")
    import transformers
    import tokenizers
    print("python", sys.version.split()[0], "| transformers", transformers.__version__, "| tokenizers", tokenizers.__version__)
    print("manifests and protocol read from the freeze commit", L.FREEZE, "with git cat-file")
    tok = L.load_qwen_tokenizer(dm["model"]["tokenizer"]["files_sha256"])
    print("  tokenizer class", type(tok).__name__, "| <|endoftext|> id", tok.convert_tokens_to_ids("<|endoftext|>"))
    files = dm["files"]
    allok = True

    # ---------------------------------------------------------------- anchor text (2.6 / Pilot 2.7)
    import pyarrow.parquet as pq
    apath = L.local_input("SandyResearch/fineweb-edu-shuffled", "data/sample-100BT/train/shard_00000.parquet")
    print("\nanchor parquet sha256", L.file_sha256(apath))
    pf = pq.ParquetFile(apath)
    anchor, row = [], 0
    for rg in range(pf.metadata.num_row_groups):
        for txt in pf.read_row_group(rg, columns=["text"]).column("text").to_pylist():
            if len(txt) >= 600:
                ids = tok.encode(txt, add_special_tokens=False)[:128]
                anchor.append({"doc": len(anchor), "source_row": row, "ids": ids, "text": tok.decode(ids)})
            row += 1
            if len(anchor) == 512:
                break
        if len(anchor) == 512:
            break
    print(f"anchor documents {len(anchor)} | source rows scanned {row} | ids per document min {min(len(a['ids']) for a in anchor)} max {max(len(a['ids']) for a in anchor)}")
    L.write_jsonl(L.DATA + "/anchor_text.jsonl", anchor)
    anchor = L.read_jsonl(L.DATA + "/anchor_text.jsonl")
    allok &= check("anchor decoded texts (canonical JSON list of the 512 texts)", L.canon_sha([a["text"] for a in anchor]),
                   [("DATA_MANIFEST.anchor_text.decoded_texts_canonical_sha256", dm["anchor_text"]["decoded_texts_canonical_sha256"]),
                    ("Pilot DATA_MANIFEST.anchor_text.decoded_texts_canonical_sha256", pdm["anchor_text"]["decoded_texts_canonical_sha256"])],
                   proto, True)
    allok &= check("anchor_text.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/anchor_text.jsonl"),
                   [("DATA_MANIFEST.files.anchor_text.jsonl.reference_canonical_sha256", files["anchor_text.jsonl"]["reference_canonical_sha256"]),
                    ("DATA_MANIFEST.anchor_text.file_canonical_sha256_authoring", dm["anchor_text"]["file_canonical_sha256_authoring"])],
                   proto, False)
    anchor_joined = "\x00".join(a["text"].lower() for a in anchor)
    anchor_w13 = set()
    for a in anchor:
        anchor_w13 |= L.word13(a["text"])
    print("anchor distinct word 13-grams", len(anchor_w13))

    # ---------------------------------------------------------------- templates (2.4)
    tl = sm["templates"]
    bad = 0
    for t in tl:
        n = L.normalize_template(t["text"])
        if n != t["normalized"] or L.sha_text(n) != t["normalized_sha256"]:
            bad += 1
            print("   template mismatch", t["template_id"])
    print(f"\ntemplates {len(tl)} | normalized text or normalized_sha256 differing from SPLIT_MANIFEST.templates[*]: {bad} | identical to the Pilot SPLIT_MANIFEST templates list: {tl == psm['templates']}")
    allok &= bad == 0 and len(tl) == 32
    tss = L.sha_text("\n".join(sorted(L.sha_text(L.normalize_template(t["text"])) for t in tl)))
    allok &= check("template_set_sha256", tss,
                   [("SPLIT_MANIFEST.template_freeze.template_set_sha256", sm["template_freeze"]["template_set_sha256"]),
                    ("Pilot SPLIT_MANIFEST.template_freeze.template_set_sha256", psm["template_freeze"]["template_set_sha256"])],
                   proto, True)

    # ---------------------------------------------------------------- Pilot facts (2.2 change 3)
    ng = dm["name_generation"]
    pfacts, pg = L.build_facts(tok, ng, anchor_joined, 20261110, 15, 5, "E1P")
    print(f"\nPilot facts regenerated (DATA_SEED 20261110, 15 + 5 per cell): {len(pfacts)}")
    for rel, st, ed, ad, tgt in pg.log:
        print(f"   Pilot {rel}/{st}: entity draws {ed}, answer draws {ad}, target (K_st, K_qa) {tgt}")
    allok &= check("Pilot facts (canonical JSON list)", L.canon_sha(pfacts),
                   [("DATA_MANIFEST.name_generation.preseed.pilot_facts_canonical_sha256", ng["preseed"]["pilot_facts_canonical_sha256"])],
                   proto, True)
    print(f"   cross-check: Pilot facts as JSONL {L.jsonl_sha(pfacts)} | Pilot DATA_MANIFEST.files.facts.jsonl.canonical_sha256 {pdm['files']['facts.jsonl']['canonical_sha256']} | equal {L.jsonl_sha(pfacts) == pdm['files']['facts.jsonl']['canonical_sha256']}")
    pstrings = [f["entity"] for f in pfacts] + [f["answer"] for f in pfacts]

    # ---------------------------------------------------------------- V1 facts (2.1, 2.2)
    seeds = dm["seeds"]
    vfacts, vg = L.build_facts(tok, ng, anchor_joined, seeds["DATA_SEED"], 30, 10, "E1V1", preseed=pstrings)
    print(f"\nV1 facts regenerated (DATA_SEED {seeds['DATA_SEED']}, 30 + 10 per cell, accepted set pre-seeded with {len(pstrings)} Pilot strings): {len(vfacts)}")
    for rel, st, ed, ad, tgt in vg.log:
        print(f"   V1 {rel}/{st}: entity draws {ed}, answer draws {ad}, target (K_st, K_qa) {tgt}")
    nl = sum(1 for f in vfacts if f["exposure"] == "learned")
    vstr = [f["entity"] for f in vfacts] + [f["answer"] for f in vfacts]
    print(f"   learned {nl} | unread {len(vfacts) - nl} | strings {len(vstr)} distinct {len(set(vstr))} | "
          f"lowercase equal to a Pilot string {sum(1 for s in vstr if s.lower() in {p.lower() for p in pstrings})} | "
          f"fact_id shared with Pilot {len({f['fact_id'] for f in vfacts} & {f['fact_id'] for f in pfacts})}")
    allok &= nl == 240 and len(vfacts) == 320 and len(set(vstr)) == 640
    allok &= check("V1 facts (canonical JSON list)", L.canon_sha(vfacts),
                   [("DATA_MANIFEST.name_generation.expected_facts_canonical_sha256", ng["expected_facts_canonical_sha256"])],
                   proto, True)
    L.write_jsonl(L.DATA + "/facts.jsonl", vfacts)
    vfacts = L.read_jsonl(L.DATA + "/facts.jsonl")
    print(f"   facts.jsonl read back from disk, list canonical sha256 {L.canon_sha(vfacts)} (method of protocol 2.2: list of the file's rows in order)")
    allok &= L.canon_sha(vfacts) == ng["expected_facts_canonical_sha256"]
    allok &= check("facts.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/facts.jsonl"),
                   [("DATA_MANIFEST.files.facts.jsonl.reference_canonical_sha256", files["facts.jsonl"]["reference_canonical_sha256"])],
                   proto, False)

    # ---------------------------------------------------------------- corpora and candidates (2.3, 2.5, 2.6)
    F, S, Y, Q, C, pools, att = L.build_corpora(vfacts, tl, seeds["DATA_SEED"], seeds["CANDIDATE_SEED"], 30)
    print(f"\nrows: train_F {len(F)} | train_S {len(S)} | train_Y {len(Y)} | dev_qa {len(Q)} | candidates keys {len(C)}")
    print("S derangement attempts per cell", att)
    print("candidate pool sizes (learned, unread):", sorted({(fid.split('-')[1], n) for fid, n in pools.items()}))
    for name, rows in (("train_F.jsonl", F), ("train_S.jsonl", S), ("train_Y.jsonl", Y), ("dev_qa.jsonl", Q)):
        L.write_jsonl(L.DATA + "/" + name, rows)
    with open(L.DATA + "/candidates.json", "w", encoding="utf-8", newline="\n") as f:
        f.write(L.canon(C))
    allok &= check("train_F.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/train_F.jsonl"),
                   [("DATA_MANIFEST.files.train_F.jsonl.reference_canonical_sha256", files["train_F.jsonl"]["reference_canonical_sha256"])],
                   proto, False)
    allok &= check("train_S.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/train_S.jsonl"),
                   [("DATA_MANIFEST.files.train_S.jsonl.reference_canonical_sha256", files["train_S.jsonl"]["reference_canonical_sha256"]),
                    ("DATA_MANIFEST.s_permutation.expected_train_S_canonical_sha256", dm["s_permutation"]["expected_train_S_canonical_sha256"])],
                   proto, True)
    allok &= check("train_Y.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/train_Y.jsonl"),
                   [("DATA_MANIFEST.files.train_Y.jsonl.reference_canonical_sha256", files["train_Y.jsonl"]["reference_canonical_sha256"])],
                   proto, True)
    allok &= check("dev_qa.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/dev_qa.jsonl"),
                   [("DATA_MANIFEST.files.dev_qa.jsonl.reference_canonical_sha256", files["dev_qa.jsonl"]["reference_canonical_sha256"])],
                   proto, False)
    allok &= check("candidates.json", L.file_canonical_sha256_json(L.DATA + "/candidates.json"),
                   [("DATA_MANIFEST.files.candidates.json.reference_canonical_sha256", files["candidates.json"]["reference_canonical_sha256"]),
                    ("SPLIT_MANIFEST.candidates.candidate_mapping_sha256", sm["candidates"]["candidate_mapping_sha256"])],
                   proto, True)
    ftok = sum(len(tok.encode(r["text"], add_special_tokens=False)) + 1 for r in F)
    ytok = sum(len(tok.encode(r["text"], add_special_tokens=False)) + 1 for r in Y)
    au = dm["y_ratio"]["authoring"]
    print(f"\nY/F tokens: F {ftok} (manifest {au['F_tokens']}) | Y {ytok} (manifest {au['Y_tokens']}) | ratio {ytok / ftok:.6f} (manifest {au['ratio']}) | in [0.80, 1.25] {0.80 <= ytok / ftok <= 1.25}")
    allok &= ftok == au["F_tokens"] and ytok == au["Y_tokens"] and round(ytok / ftok, 4) == au["ratio"]

    # ---------------------------------------------------------------- D1 DEV (7.2)
    d1 = gm["d1"]
    v1_lower = [s.lower() for s in vstr]
    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(L.local_input("SandyResearch/parcae-tokenizer", "tokenizer.json"))
    print("\nparcae tokenizer.json sha256", L.file_sha256(L.local_input("SandyResearch/parcae-tokenizer", "tokenizer.json")))
    dev_rows = {d: [] for d in d1["domains"]}
    n_test_skipped = 0
    with open(os.path.join(L.REPO, d1["source_file"]), "rb") as f:
        for raw in f:
            m = L.ROW_PREFIX.match(raw)
            if not m:
                raise SystemExit("row without the section 0 prefix")
            if m.group(2) != b"dev":
                n_test_skipped += 1  # not decoded, not parsed
                continue
            r = json.loads(raw)  # DEV row only
            assert r["split"] == "dev" and r["domain"].encode() == m.group(1)
            dev_rows[r["domain"]].append(r)
    print(f"eval_sets.jsonl: DEV rows parsed per domain {{{', '.join(f'{d}: {len(v)}' for d, v in dev_rows.items())}}} | non-dev rows skipped on the prefix bytes (not decoded): {n_test_skipped}")
    windows, exc = [], {"L8": 0, "L6": 0}
    for dom in d1["domains"]:
        for r in dev_rows[dom][:d1["dev"]["per_domain"]]:
            full = ptok.decode(r["tokens"], skip_special_tokens=True)
            ids = tok.encode(full, add_special_tokens=False)[:256]
            text = tok.decode(ids)
            if L.l8_hit(text, v1_lower):
                exc["L8"] += 1
                continue
            if L.word13(text) & anchor_w13:
                exc["L6"] += 1
                continue
            windows.append({"domain": dom, "doc_id": r["doc_id"], "ids": ids, "text": text})
    L.write_jsonl(L.DATA + "/general_dev.jsonl", windows)
    lens = [len(w["ids"]) for w in windows]
    au = d1["dev"]["authoring"]
    print(f"D1 DEV kept {len(windows)} (manifest {au['kept']}) | excluded {exc} (manifest {au['excluded']}) | ids per window mean {round(sum(lens) / len(lens), 3)} (manifest {au['ids_per_window_mean']}) min {min(lens)} max {max(lens)}")
    allok &= len(windows) == au["kept"] and sum(exc.values()) == au["excluded"] and round(sum(lens) / len(lens), 3) == au["ids_per_window_mean"]
    allok &= check("general_dev.jsonl", L.file_canonical_sha256_jsonl(L.DATA + "/general_dev.jsonl"),
                   [("DATA_MANIFEST.files.general_dev.jsonl.reference_canonical_sha256", files["general_dev.jsonl"]["reference_canonical_sha256"]),
                    ("DAMAGE_MANIFEST.d1.dev.authoring.canonical_sha256", au["canonical_sha256"])],
                   proto, True)

    # ---------------------------------------------------------------- D2 DEV (7.1, 7.2)
    d2 = gm["d2"]
    I = "Answer the following multiple choice question with the letter of the correct option."
    letters = "ABCD"
    lt = {l: tok.encode(" " + l, add_special_tokens=False) for l in letters}
    print(f"\nletter tokens {lt} | manifest d2.letter_token_ids {d2['letter_token_ids']} | equal {all(lt[l] == [d2['letter_token_ids'][l]] for l in letters)}")
    allok &= all(lt[l] == [d2["letter_token_ids"][l]] for l in letters)

    def prompt(q, opts):
        return (I + "\n\n" + q.strip() + "\n" + "A. " + opts[0] + "\n" + "B. " + opts[1] + "\n" + "C. " + opts[2] + "\n" + "D. " + opts[3])

    import importlib.util
    has_jinja = importlib.util.find_spec("jinja2") is not None
    print("jinja2 available (needed by apply_chat_template):", has_jinja,
          "- the context-length statistic (not a hash) is computed only if available; the given venv has no jinja2 and nothing is installed into it")

    def ctx_len(p):
        s = tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True,
                                    enable_thinking=False) + "The answer is"
        return len(tok.encode(s, add_special_tokens=False))

    def build(rows, purpose, kind):
        order = list(range(len(rows)))
        L.rng_rule(seeds["DATA_SEED"], purpose).shuffle(order)
        out, ex, visited = [], {}, 0
        for idx in order:
            if len(out) == 800:
                break
            visited += 1
            r = rows[idx]
            if kind == "mmlu":
                ok4 = len(r["choices"]) == 4 and r["answer"] in (0, 1, 2, 3)
                opts = [str(c).strip() for c in r["choices"]]
                ans = letters[r["answer"]] if ok4 else None
                subj = r["subject"]
            else:
                labels = list(r["choices"]["label"])
                opts = [str(c).strip() for c in r["choices"]["text"]]
                ok4 = len(labels) == 4 and len(opts) == 4 and r["answerKey"] in labels
                ans = letters[labels.index(r["answerKey"])] if ok4 else None
                subj = r["id"]
            if not ok4:
                ex["not_4_choices_or_answer"] = ex.get("not_4_choices_or_answer", 0) + 1
                continue
            p = prompt(r["question"], opts)
            if L.l8_hit(p, v1_lower):
                ex["L8"] = ex.get("L8", 0) + 1
                continue
            if L.word13(p) & anchor_w13:
                ex["L6"] = ex.get("L6", 0) + 1
                continue
            out.append({"item": len(out), "source_row": idx, "subject": subj, "prompt": p, "answer": ans})
        return out, ex, visited

    mm = d2["datasets"]["mmlu"]
    vpath = L.local_input(mm["repo"], mm["dev_source"]["file"])
    print("MMLU validation parquet sha256", L.file_sha256(vpath))
    vrows = pq.read_table(vpath).to_pylist()  # DEV source
    md, mex, mvis = build(vrows, "d2:mmlu:validation:order", "mmlu")
    L.write_jsonl(L.DATA + "/d2_dev.jsonl", md)
    au = mm["authoring_dev"]
    print(f"MMLU D2 DEV items {len(md)} (manifest {au['items']}) | rows visited {mvis} (manifest {au['rows_visited']}) | excluded {mex} (manifest {au['excluded']}) | subjects {len({x['subject'] for x in md})} (manifest {au['subjects']})")
    allok &= (len(md) == au["items"] and mvis == au["rows_visited"] and sum(mex.values()) == au["excluded"]
              and len({x["subject"] for x in md}) == au["subjects"])
    if has_jinja:
        cl = [ctx_len(x["prompt"]) for x in md]
        print(f"   context ids mean {round(sum(cl) / len(cl), 3)} (manifest {au['context_ids_mean']}) median {statistics.median(cl)}")
    else:
        print(f"   context ids mean: not computed (no jinja2); manifest {au['context_ids_mean']}")
    allok &= check("d2_dev.jsonl (MMLU, adopted)", L.file_canonical_sha256_jsonl(L.DATA + "/d2_dev.jsonl"),
                   [("DATA_MANIFEST.files.d2_dev.jsonl.reference_canonical_sha256", files["d2_dev.jsonl"]["reference_canonical_sha256"]),
                    ("DAMAGE_MANIFEST.d2.datasets.mmlu.authoring_dev.canonical_sha256", au["canonical_sha256"])],
                   proto, True)

    ar = d2["datasets"]["arc"]
    arows = []
    for s in ar["dev_source"]:
        p = L.local_input(ar["repo"], s["file"])
        print(f"ARC {s['file']} sha256 {L.file_sha256(p)}")
        arows += pq.read_table(p).to_pylist()  # DEV sources (validation) only
    ad, aex, avis = build(arows, "d2:arc:validation:order", "arc")
    L.write_jsonl(L.DATA + "/d2_dev_arc.jsonl", ad)
    au = ar["authoring_dev"]
    print(f"ARC D2 DEV items {len(ad)} (manifest {au['items']}) | DEV source rows {len(arows)} | rows visited {avis} | excluded {aex} (manifest {au['excluded']})")
    allok &= (len(ad) == au["items"] and aex.get("not_4_choices_or_answer", 0) == au["excluded"]["not_4_choices"]
              and set(aex) <= {"not_4_choices_or_answer"})
    if has_jinja:
        acl = [ctx_len(x["prompt"]) for x in ad]
        print(f"   context ids mean {round(sum(acl) / len(acl), 3)} (manifest {au['context_ids_mean']})")
    else:
        print(f"   context ids mean: not computed (no jinja2); manifest {au['context_ids_mean']}")
    allok &= check("d2_dev (ARC, not adopted alternative)", L.file_canonical_sha256_jsonl(L.DATA + "/d2_dev_arc.jsonl"),
                   [("DATA_MANIFEST.files.d2_dev.jsonl.not_adopted_alternative.arc.reference_canonical_sha256",
                     files["d2_dev.jsonl"]["not_adopted_alternative"]["arc"]["reference_canonical_sha256"]),
                    ("DAMAGE_MANIFEST.d2.datasets.arc.authoring_dev.canonical_sha256", au["canonical_sha256"])],
                   proto, True)

    # ---------------------------------------------------------------- summary
    print("\nwritten files (audit/tmp_freeze/data), byte sha256 (written in canonical form, so equal to the canonical sha256):")
    for name in ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
                 "anchor_text.jsonl", "general_dev.jsonl", "d2_dev.jsonl", "d2_dev_arc.jsonl"]:
        print(f"   {name}: {L.file_sha256(L.DATA + '/' + name)}")
    print("TEST files generated: none (", [n for n in os.listdir(L.DATA) if "test" in n], ")")
    print("\nsummary of hash checks:")
    for label, got, ok in RESULTS:
        print(f"   {'OK  ' if ok else 'DIFF'} {label}: {got}")
    print(f"hash checks equal: {sum(1 for r in RESULTS if r[2])} of {len(RESULTS)} | elapsed {time.time() - t0:.1f} s")
    print("ITEM (c):", "ALL MATCH" if allok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
