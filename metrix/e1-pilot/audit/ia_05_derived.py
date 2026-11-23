"""IA-5: data derived from the 160 facts of ia_04_facts.py (Data Auditor's own reading of protocol 2.3-2.6; no Executor
code imported, called or copied).  Only TRAIN, DEV and Y templates are instantiated; TEST templates never are.

  train_S (2.6, detail 4; frozen hash): per cell (relation order x natural, random) one r = rng_rule(DATA_SEED,
      "s-permutation:<relation>:<stratum>"); attempt p = list(range(15)); r.shuffle(p); redraw with the same r from a
      fresh list(range(15)) while some p[i] == i; record {"fact_id": id_i, "answer_fact_id": id_p[i],
      "text": TRAIN(E = entity_i, A = answer_p[i])}; canonical JSONL hash.
  candidates (2.5, detail 5; frozen hash): per fact r = rng_rule(CANDIDATE_SEED, "cand:<fact_id>"); pool = answers of
      the other facts with the same relation, stratum, exposure in generation order; d = r.sample(pool, 3);
      c = [answer] + d; r.shuffle(c); {fact_id: c}; canonical JSON hash.
  train_F (2.3): one TRAIN statement per learned fact, fact order (120).
  train_Y (2.6): per learned fact, fact order: Y_ENTITY sentence then Y_ANSWER sentence (240); the order inside the
      file is not fixed by the protocol (my reading: fact order, the order of the 2.4 table "Y_ENTITY / Y_ANSWER").
  dev_qa (2.3, 2.4): per fact (all 160, fact order) the 2 DEV templates in table order (320), {E} = entity.
Checks of protocol requirements on the derived data:
  - Y / F token ratio in [0.80, 1.25] (2.6); the authoring numbers F 1,889 / Y 2,260 / 1.196 are recomputed;
  - Y_ANSWER: " " + answer is tokenized as in the TRAIN statement (2.6): enc(" " + A) is a contiguous slice of both
    encodings, starting right after the ids of the text before " " + A;
  - exposure matching (2.5): every candidate of a learned fact occurs exactly once (case-insensitive substring) in
    each of F, S, Y and 0 times in the anchor text; every candidate of an unread fact 0 times; learned entities
    exactly once in each of F, S, Y.
Writes train_S.jsonl, candidates.json, train_F.json, train_Y.json, dev_qa.json to <out_dir>.
usage: python -I ia_05_derived.py <repo_root> <qwen_tok_dir> <out_dir>   (reads facts.json, anchor.json)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter
from ia_common import RELS, STRATA, sha, canon, jsonl_bytes, rng_rule, frozen_json, load_qwen, enc, run

DATA_SEED, CANDIDATE_SEED = 20261110, 20261111
EOT = 151643


def build_s(facts, train_t):
    rows, tries = [], {}
    for rel in RELS:
        for st in STRATA:
            cell = [f for f in facts if (f["relation"], f["stratum"], f["exposure"]) == (rel, st, "learned")]
            assert [f["fact_id"][-2:] for f in cell] == [f"{i:02d}" for i in range(1, 16)]
            r = rng_rule(DATA_SEED, f"s-permutation:{rel}:{st}")
            n = 0
            while True:
                n += 1
                p = list(range(15))
                r.shuffle(p)
                if not any(p[i] == i for i in range(15)):
                    break
            tries[f"{rel}/{st}"] = n
            for i in range(15):
                rows.append({"fact_id": cell[i]["fact_id"], "answer_fact_id": cell[p[i]]["fact_id"],
                             "text": train_t[rel].replace("{E}", cell[i]["entity"]).replace("{A}", cell[p[i]]["answer"])})
    return rows, tries


def build_c(facts):
    out = {}
    for f in facts:
        r = rng_rule(CANDIDATE_SEED, f"cand:{f['fact_id']}")
        pool = [g["answer"] for g in facts if g["fact_id"] != f["fact_id"] and
                (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])]
        if len(pool) < 4:
            raise RuntimeError(f"IMPLEMENTATION_FAIL pool of {f['fact_id']} has {len(pool)} answers")
        d = r.sample(pool, 3)
        c = [f["answer"]] + d
        r.shuffle(c)
        out[f["fact_id"]] = c
    return out


def slice_at_boundary(tok, text, piece):
    """enc(piece) is a contiguous slice of enc(text) starting right after enc(text before piece)."""
    k = text.rindex(piece)
    full, pre, mid = enc(tok, text), enc(tok, text[:k]), enc(tok, piece)
    return full[:len(pre)] == pre and full[len(pre):len(pre) + len(mid)] == mid


def main():
    repo, qdir, out_dir = sys.argv[1:4]
    ok = True
    dm, sm = frozen_json(repo, "DATA_MANIFEST.json"), frozen_json(repo, "SPLIT_MANIFEST.json")
    ok &= (dm["seeds"]["DATA_SEED"], dm["seeds"]["CANDIDATE_SEED"]) == (DATA_SEED, CANDIDATE_SEED)
    T = {(t["relation"], t["kind"]): [] for t in sm["templates"]}
    for t in sm["templates"]:
        T[(t["relation"], t["kind"])].append(t)
    train_t = {r: T[(r, "TRAIN")][0]["text"] for r in RELS}
    facts = json.load(open(os.path.join(out_dir, "facts.json"), encoding="utf-8"))
    fh = sha(canon(facts))
    print("facts from ia_04:", len(facts), "| canonical sha256", fh, "| == frozen:", fh == dm["name_generation"]["expected_facts_canonical_sha256"])
    ok &= fh == dm["name_generation"]["expected_facts_canonical_sha256"]
    learned = [f for f in facts if f["exposure"] == "learned"]
    unread = [f for f in facts if f["exposure"] == "unread"]

    print("\n== train_S.jsonl (frozen)")
    s_rows, tries = build_s(facts, train_t)
    s_bytes = jsonl_bytes(s_rows)
    hs, exp_s = sha(s_bytes), dm["s_permutation"]["expected_train_S_canonical_sha256"]
    print("derangement attempts per cell:", tries)
    print(f"train_S rows {len(s_rows)} | canonical sha256 {hs} | frozen {exp_s} | MATCH {hs == exp_s}")
    print(f"AUDIT_VALUE train_S_canonical_sha256 {hs}")
    ok &= hs == exp_s

    print("\n== candidates.json (frozen)")
    cands = build_c(facts)
    hc, exp_c = sha(canon(cands)), sm["candidates"]["candidate_mapping_sha256"]
    print(f"candidates keys {len(cands)} | canonical sha256 {hc} | frozen {exp_c} | MATCH {hc == exp_c}")
    print(f"AUDIT_VALUE candidates_canonical_sha256 {hc}")
    ok &= hc == exp_c

    print("\n== train_F, train_Y, dev_qa (no frozen hash; my reading of 2.3 / 2.4 / 2.6)")
    F = [{"fact_id": f["fact_id"], "text": train_t[f["relation"]].replace("{E}", f["entity"]).replace("{A}", f["answer"])} for f in learned]
    Y = []
    for f in learned:
        ye, ya = T[(f["relation"], "Y_ENTITY")][0], T[(f["relation"], "Y_ANSWER")][0]
        Y.append({"fact_id": f["fact_id"], "kind": "Y_ENTITY", "text": ye["text"].replace("{E}", f["entity"])})
        Y.append({"fact_id": f["fact_id"], "kind": "Y_ANSWER", "text": ya["text"].replace("{A}", f["answer"])})
    D = []
    for f in facts:
        for t in T[(f["relation"], "DEV")]:
            D.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "question": t["text"].replace("{E}", f["entity"])})
    print("train_F", len(F), "| train_Y", len(Y), "| dev_qa", len(D))
    ok &= len(F) == 120 and len(Y) == 240 and len(D) == 320
    ok &= all("{" not in x["text"] for x in F + Y) and all("{" not in x["question"] for x in D)
    y_mixed = [y for y in Y if (y["kind"] == "Y_ENTITY" and any(g["answer"] in y["text"] for g in learned)) or
               (y["kind"] == "Y_ANSWER" and any(g["entity"] in y["text"] for g in learned))]
    print("Y sentences containing both an entity and an answer:", len(y_mixed))
    ok &= not y_mixed
    for name, rows, key in (("train_F", F, "text"), ("train_Y", Y, "text"), ("dev_qa", D, "question")):
        print(f"AUDIT_VALUE {name}_texts_canonical_sha256 {sha(canon([r[key] for r in rows]))}")

    tok = load_qwen(qdir)
    print("\n== Y / F token ratio (2.6)")
    nf = sum(len(enc(tok, r["text"])) for r in F)
    ny = sum(len(enc(tok, r["text"])) for r in Y)
    print(f"without the end-of-text token: F {nf} | Y {ny} | ratio {ny / nf:.4f}")
    print(f"with one end-of-text token (id {EOT}) per sequence: F {nf + len(F)} | Y {ny + len(Y)} | ratio {(ny + len(Y)) / (nf + len(F)):.4f}")
    ratios = (ny / nf, (ny + len(Y)) / (nf + len(F)))
    ok &= all(0.80 <= x <= 1.25 for x in ratios)
    print("authoring numbers F 1,889 / Y 2,260 reproduced by the counting with the end-of-text token:", (nf + len(F), ny + len(Y)) == (1889, 2260))

    print("\n== Y_ANSWER and TRAIN statement tokenize ' ' + answer identically (2.6)")
    bad = []
    by_id = {f["fact_id"]: f for f in facts}
    for r in Y:
        if r["kind"] != "Y_ANSWER":
            continue
        a = " " + by_id[r["fact_id"]]["answer"]
        ftext = next(x["text"] for x in F if x["fact_id"] == r["fact_id"])
        if not (slice_at_boundary(tok, r["text"], a) and slice_at_boundary(tok, ftext, a)):
            bad.append(r["fact_id"])
    print("learned facts checked:", len(learned), "| mismatches:", bad)
    ok &= not bad

    print("\n== exposure matching (2.5), case-insensitive substring counts")
    anchor = json.load(open(os.path.join(out_dir, "anchor.json"), encoding="utf-8"))
    corp = {"F": "\n".join(r["text"] for r in F).lower(), "S": "\n".join(r["text"] for r in s_rows).lower(),
            "Y": "\n".join(r["text"] for r in Y).lower()}
    anc = [a["text"].lower() for a in anchor]
    viol = []
    for f in learned:
        for c in cands[f["fact_id"]]:
            for k, txt in corp.items():
                if txt.count(c.lower()) != 1:
                    viol.append((f["fact_id"], c, k, txt.count(c.lower())))
            na = sum(t.count(c.lower()) for t in anc)
            if na:
                viol.append((f["fact_id"], c, "anchor", na))
        for k, txt in corp.items():
            if txt.count(f["entity"].lower()) != 1:
                viol.append((f["fact_id"], f["entity"], k, txt.count(f["entity"].lower())))
    for f in unread:
        for c in cands[f["fact_id"]] + [f["entity"]]:
            for k, txt in list(corp.items()) + [("anchor", "\n".join(anc))]:
                if txt.count(c.lower()):
                    viol.append((f["fact_id"], c, k, txt.count(c.lower())))
    print("learned: 4 candidates x {F,S,Y} == 1 and anchor == 0; learned entity x {F,S,Y} == 1; "
          "unread: candidates and entity x {F,S,Y,anchor} == 0 | violations:", viol[:10], "| count", len(viol))
    ok &= not viol

    open(os.path.join(out_dir, "train_S.jsonl"), "wb").write(s_bytes)
    open(os.path.join(out_dir, "candidates.json"), "wb").write(canon(cands))
    for name, rows in (("train_F.json", F), ("train_Y.json", Y), ("dev_qa.json", D)):
        open(os.path.join(out_dir, name), "wb").write(canon(rows))
    print("wrote train_S.jsonl, candidates.json, train_F.json, train_Y.json, dev_qa.json to", out_dir)
    return bool(ok)


run(main)
