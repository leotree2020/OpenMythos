# data-auditor, E1-V1 round 1, item 1: hashes.
# Regenerates (CPU, tokenizer only) the anchor text, the Pilot facts (DATA_SEED 20261110) and the
# V1 facts and non-TEST fact files from the protocol / manifest text, and compares every hash with
# the manifests. Writes the generated data to audit/tmpdata/v1data (not to be committed).
import os
import sys
import time

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402  (the auditor's own helper, written for this audit)

OUT = A.TMP + "/v1data"
os.makedirs(OUT, exist_ok=True)


def cmp(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def main():
    t0 = time.time()
    allok = True
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    sm = A.load_json(A.V1 + "/SPLIT_MANIFEST.json")
    pdm = A.load_json(A.PILOT + "/DATA_MANIFEST.json")
    psm = A.load_json(A.PILOT + "/SPLIT_MANIFEST.json")
    import transformers, tokenizers  # noqa
    print("python", sys.version.split()[0], "| transformers", transformers.__version__, "| tokenizers", tokenizers.__version__)
    tok = A.load_qwen_tokenizer(dm["model"]["tokenizer"]["files_sha256"])
    print("tokenizer class", type(tok).__name__, "| <|endoftext|> id", tok.convert_tokens_to_ids("<|endoftext|>"))

    # ---------------- anchor text ----------------
    exp_anchor_src = "6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22"
    got = A.file_sha256(A.ANCHOR_PARQUET)
    allok &= cmp("anchor parquet sha256 (manifest anchor_text.source)", got, exp_anchor_src)
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(A.ANCHOR_PARQUET)
    anchor, row = [], 0
    for rg in range(pf.metadata.num_row_groups):
        col = pf.read_row_group(rg, columns=["text"]).column("text").to_pylist()
        for txt in col:
            if len(txt) >= 600:
                ids = tok.encode(txt, add_special_tokens=False)[:128]
                anchor.append({"doc": len(anchor), "source_row": row, "ids": ids, "text": tok.decode(ids)})
            row += 1
            if len(anchor) == 512:
                break
        if len(anchor) == 512:
            break
    print("anchor docs", len(anchor), "| source rows scanned", row, "| last source_row", anchor[-1]["source_row"],
          "| ids per doc min/max", min(len(a["ids"]) for a in anchor), max(len(a["ids"]) for a in anchor))
    allok &= cmp("anchor decoded texts canonical sha256 (JSON list)", A.canon_sha([a["text"] for a in anchor]),
                 dm["anchor_text"]["decoded_texts_canonical_sha256"])
    allok &= cmp("anchor decoded texts = Pilot manifest value", dm["anchor_text"]["decoded_texts_canonical_sha256"],
                 pdm["anchor_text"]["decoded_texts_canonical_sha256"])
    allok &= cmp("anchor_text.jsonl canonical sha256 {doc, source_row, ids, text}", A.jsonl_sha(anchor),
                 dm["files"]["anchor_text.jsonl"]["reference_canonical_sha256"])
    allok &= cmp("anchor_text.jsonl = Pilot generated file hash", dm["files"]["anchor_text.jsonl"]["reference_canonical_sha256"],
                 pdm["files"]["anchor_text.jsonl"]["canonical_sha256"])
    A.write_jsonl(OUT + "/anchor_text.jsonl", anchor)
    anchor_joined = "\x00".join(a["text"].lower() for a in anchor)

    # ---------------- templates ----------------
    tl = sm["templates"]
    ptl = psm["templates"]
    print("templates V1", len(tl), "| Pilot", len(ptl), "| identical lists", tl == ptl)
    allok &= (tl == ptl)
    nbad = 0
    for t in tl:
        n = A.normalize_template(t["text"])
        h = A.sha_text(n)
        if n != t["normalized"] or h != t["normalized_sha256"]:
            nbad += 1
            print("  template mismatch", t["template_id"], repr(n), h)
    print("templates normalized text / normalized_sha256 mismatches:", nbad)
    allok &= nbad == 0
    tss = A.sha_text("\n".join(sorted(A.sha_text(A.normalize_template(t["text"])) for t in tl)))
    allok &= cmp("template_set_sha256", tss, sm["template_freeze"]["template_set_sha256"])
    allok &= cmp("template_set_sha256 = Pilot", sm["template_freeze"]["template_set_sha256"], psm["template_freeze"]["template_set_sha256"])
    kinds = {}
    for t in tl:
        kinds[(t["relation"], t["kind"])] = kinds.get((t["relation"], t["kind"]), 0) + 1
    print("templates per (relation, kind):", sorted(kinds.items()))

    # ---------------- Pilot facts ----------------
    t1 = time.time()
    pfacts, pg = A.build_facts(tok, anchor_joined, 20261110, 15, 5, "E1P")
    print("Pilot facts", len(pfacts), "| built in %.1f s" % (time.time() - t1))
    for (rel, st, ed, ad, tgt, _c) in pg.log:
        print(f"  Pilot cell {rel}/{st}: entity_draws {ed} answer_draws {ad} target {tgt}")
    allok &= cmp("Pilot facts canonical sha256 (JSON list)", A.canon_sha(pfacts), dm["name_generation"]["preseed"]["pilot_facts_canonical_sha256"])
    allok &= cmp("Pilot facts.jsonl canonical (Pilot manifest files.facts.jsonl)", A.jsonl_sha(pfacts), pdm["files"]["facts.jsonl"]["canonical_sha256"])
    # Pilot derived files: calibrate the record formats against the frozen Pilot hashes
    pF, pS, pY, pQ, pC, ppools, _ = A.build_corpora(pfacts, tl, 20261110, 20261111, 15)
    allok &= cmp("Pilot train_F.jsonl", A.jsonl_sha(pF), pdm["files"]["train_F.jsonl"]["canonical_sha256"])
    allok &= cmp("Pilot train_S.jsonl", A.jsonl_sha(pS), pdm["files"]["train_S.jsonl"]["canonical_sha256"])
    allok &= cmp("Pilot train_Y.jsonl", A.jsonl_sha(pY), pdm["files"]["train_Y.jsonl"]["canonical_sha256"])
    allok &= cmp("Pilot dev_qa.jsonl", A.jsonl_sha(pQ), pdm["files"]["dev_qa.jsonl"]["canonical_sha256"])
    allok &= cmp("Pilot candidates.json", A.canon_sha(pC), pdm["files"]["candidates.json"]["canonical_sha256"])
    pilot_strings = [f["entity"] for f in pfacts] + [f["answer"] for f in pfacts]
    print("Pilot strings", len(pilot_strings), "| distinct", len(set(pilot_strings)))

    # ---------------- V1 facts ----------------
    t1 = time.time()
    vfacts, vg = A.build_facts(tok, anchor_joined, dm["seeds"]["DATA_SEED"], 30, 10, "E1V1", preseed=pilot_strings)
    print("V1 facts", len(vfacts), "| built in %.1f s" % (time.time() - t1))
    for (rel, st, ed, ad, tgt, c) in vg.log:
        print(f"  V1 cell {rel}/{st}: entity_draws {ed} answer_draws {ad} target {tgt} | survey counts {c}")
    allok &= cmp("V1 facts canonical sha256 (JSON list) = DATA_MANIFEST expected_facts_canonical_sha256",
                 A.canon_sha(vfacts), dm["name_generation"]["expected_facts_canonical_sha256"])
    allok &= cmp("V1 facts.jsonl canonical (JSONL) = files.facts.jsonl.reference_canonical_sha256",
                 A.jsonl_sha(vfacts), dm["files"]["facts.jsonl"]["reference_canonical_sha256"])
    F, Sx, Y, Q, C, pools, s_att = A.build_corpora(vfacts, tl, dm["seeds"]["DATA_SEED"], dm["seeds"]["CANDIDATE_SEED"], 30)
    print("S derangement attempts per cell", s_att)
    print("rows: train_F", len(F), "| train_S", len(Sx), "| train_Y", len(Y), "| dev_qa", len(Q), "| candidates keys", len(C))
    allok &= cmp("train_F.jsonl", A.jsonl_sha(F), dm["files"]["train_F.jsonl"]["reference_canonical_sha256"])
    allok &= cmp("train_S.jsonl", A.jsonl_sha(Sx), dm["files"]["train_S.jsonl"]["reference_canonical_sha256"])
    allok &= cmp("train_S.jsonl = s_permutation.expected_train_S_canonical_sha256", A.jsonl_sha(Sx), dm["s_permutation"]["expected_train_S_canonical_sha256"])
    allok &= cmp("train_Y.jsonl", A.jsonl_sha(Y), dm["files"]["train_Y.jsonl"]["reference_canonical_sha256"])
    allok &= cmp("dev_qa.jsonl", A.jsonl_sha(Q), dm["files"]["dev_qa.jsonl"]["reference_canonical_sha256"])
    allok &= cmp("candidates.json", A.canon_sha(C), dm["files"]["candidates.json"]["reference_canonical_sha256"])
    allok &= cmp("candidates.json = SPLIT_MANIFEST candidate_mapping_sha256", A.canon_sha(C), sm["candidates"]["candidate_mapping_sha256"])

    # ---------------- Y / F token ratio ----------------
    ftok = sum(len(tok.encode(r["text"], add_special_tokens=False)) + 1 for r in F)
    ytok = sum(len(tok.encode(r["text"], add_special_tokens=False)) + 1 for r in Y)
    ratio = ytok / ftok
    print(f"Y/F tokens: F {ftok} Y {ytok} ratio {ratio:.6f} in [0.80, 1.25] {0.80 <= ratio <= 1.25}")
    au = dm["y_ratio"]["authoring"]
    allok &= cmp("F tokens", ftok, au["F_tokens"]) & cmp("Y tokens", ytok, au["Y_tokens"]) & cmp("ratio (4 d.p.)", round(ratio, 4), au["ratio"])

    # ---------------- exposure matching ----------------
    corpora = {"train_F (F, L, A, Z0, P+)": [r["text"] for r in F], "train_S (S)": [r["text"] for r in Sx],
               "train_Y (Y)": [r["text"] for r in Y]}
    viol_sub, viol_word = 0, 0
    learned_ids = {f["fact_id"] for f in vfacts if f["exposure"] == "learned"}
    for name, texts in corpora.items():
        low = [t.lower() for t in texts]
        vs, vw = 0, 0
        for fid, cs in C.items():
            want = 1 if fid in learned_ids else 0
            for c in cs:
                cl = c.lower()
                n_sub = sum(t.count(cl) for t in low)
                n_word = sum(1 for t in texts if A.whole_word_hits(t, [cl]))
                vs += n_sub != want
                vw += n_word != want
        print(f"exposure matching {name}: violations (case-insensitive substring count) {vs} | (whole-word, per-text) {vw}")
        viol_sub += vs
        viol_word += vw
    allanchor = [a["text"] for a in anchor]
    an = sum(1 for cs in C.values() for c in cs if any(c.lower() in t.lower() for t in allanchor))
    print(f"exposure matching anchor_text (A): candidates occurring {an} (expected 0)")
    print("exposure matching total violations", viol_sub + viol_word + an)
    allok &= (viol_sub + viol_word + an) == 0

    # ---------------- answer token lengths (also used by item 3) ----------------
    kst = {f["fact_id"]: len(tok.encode(" " + f["answer"], add_special_tokens=False)) for f in vfacts}
    kqa = {f["fact_id"]: len(tok.encode(f["answer"], add_special_tokens=False)) for f in vfacts}
    A.write_jsonl(OUT + "/answer_token_counts.jsonl", [{"fact_id": k, "K_st": kst[k], "K_qa": kqa[k]} for k in kst])

    # ---------------- write data ----------------
    A.write_jsonl(OUT + "/facts.jsonl", vfacts)
    A.write_jsonl(OUT + "/train_F.jsonl", F)
    A.write_jsonl(OUT + "/train_S.jsonl", Sx)
    A.write_jsonl(OUT + "/train_Y.jsonl", Y)
    A.write_jsonl(OUT + "/dev_qa.jsonl", Q)
    with open(OUT + "/candidates.json", "w", encoding="utf-8") as f:
        f.write(A.canon(C))
    A.write_jsonl(OUT + "/pilot_facts.jsonl", pfacts)
    for name in ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json", "anchor_text.jsonl"]:
        print(f"written {name} byte_sha256 {A.file_sha256(OUT + '/' + name)}")
    print("elapsed %.1f s" % (time.time() - t0))
    print("ITEM1 (facts/templates/files part):", "ALL MATCH" if allok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
