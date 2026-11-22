"""R8-4: rebuild train_S.jsonl (protocol 2.6, detail 4) and candidates.json (protocol 2.5, detail 5) from the facts
that r8_facts.py regenerated, with the record formats of round 8 item 1a, and compare their canonical SHA-256 with
the freeze commit:
  DATA_MANIFEST.json s_permutation.expected_train_S_canonical_sha256   (record: files."train_S.jsonl".record)
  SPLIT_MANIFEST.json candidates.candidate_mapping_sha256               (record: files."candidates.json".record)
Data Auditor's own script; no Executor code is imported, called or copied (not reports/round7/gen_s_cands.py).
Standard library only for the build (no tokenizer, no model, no TEST data: only the four TRAIN templates are
instantiated). Exceptions -> RESULT: FAIL (r6_guard).

S: per cell (order capital, currency, founder, river x natural, random) one r = rng_rule(DATA_SEED,
   "s-permutation:<relation>:<stratum>"); attempt: p = list(range(15)); r.shuffle(p); redraw (same r, fresh
   list(range(15))) while some p[i] == i; learned facts 01..15 -> i = 0..14; record
   {"fact_id": id_i, "answer_fact_id": id_p[i], "text": TRAIN(E=entity_i, A=answer_p[i])}; JSONL hash rule.
C: per fact r = rng_rule(CANDIDATE_SEED, "cand:<fact_id>"); pool = answers of the other facts with the same
   relation, stratum, exposure in fact generation order; d = r.sample(pool, 3); c = [a_f] + d; r.shuffle(c);
   candidates.json = {fact_id: c}; canonical JSON hash.
ALT readings (informational) show which rule details the hashes depend on.
PASS iff both hashes equal the freeze-commit values, the protocol text carries the same values, the record formats in
the manifests are the ones implemented, and the structural checks hold.
usage: python -I r8_s_cands.py <repo_root> <commit> <facts.json> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess
from collections import Counter
from common import sha, canon, rng_rule, TRAIN_T
from r6_guard import run

RELS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
DATA_SEED, CANDIDATE_SEED = 20261110, 20261111


def git_blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], capture_output=True, check=True).stdout


def jsonl(records):
    return b"\n".join(canon(r) for r in records) + b"\n"


def build_s(facts, tmpl, mode="main"):
    rows, attempts = [], {}
    for rel in RELS:
        for st in STRATA:
            cell = [f for f in facts if f["relation"] == rel and f["stratum"] == st and f["exposure"] == "learned"]
            assert [int(f["fact_id"][-2:]) for f in cell] == list(range(1, 16)), (rel, st)
            r = rng_rule(DATA_SEED, f"s-permutation:{rel}:{st}")
            n = 0
            p = list(range(15))
            while True:
                n += 1
                if mode != "alt_no_reset":
                    p = list(range(15))
                r.shuffle(p)
                if all(p[i] != i for i in range(15)):
                    break
            attempts[f"{rel}/{st}"] = n
            if mode == "alt_inverse":
                q = [0] * 15
                for i, j in enumerate(p):
                    q[j] = i
                p = q
            for i in range(15):
                text = tmpl[rel].replace("{E}", cell[i]["entity"]).replace("{A}", cell[p[i]]["answer"])
                rec = {"fact_id": cell[i]["fact_id"], "answer_fact_id": cell[p[i]]["fact_id"], "text": text}
                if mode == "alt_text_only":
                    rec = {"fact_id": cell[i]["fact_id"], "text": text}
                rows.append(rec)
    return rows, attempts


def build_c(facts, mode="main"):
    out = {}
    for f in facts:
        r = rng_rule(CANDIDATE_SEED, f"cand:{f['fact_id']}")
        pool = [g["answer"] for g in facts if g is not f and g["relation"] == f["relation"]
                and g["stratum"] == f["stratum"] and g["exposure"] == f["exposure"]]
        if mode == "alt_sorted_pool":
            pool = sorted(pool)
        d = r.sample(pool, 3)
        c = [f["answer"]] + d
        if mode == "alt_answer_last":
            c = d + [f["answer"]]
        r.shuffle(c)
        out[f["fact_id"]] = c
    return out


def main():
    repo, commit, facts_path, out_dir = sys.argv[1:5]
    ok = True
    dm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/DATA_MANIFEST.json"))
    sm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/SPLIT_MANIFEST.json"))
    proto = git_blob(repo, commit, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md").decode("utf-8")
    exp_s = dm["s_permutation"]["expected_train_S_canonical_sha256"]
    exp_c = sm["candidates"]["candidate_mapping_sha256"]
    print("freeze-commit manifest: train_S", exp_s, "| candidates", exp_c)
    p_s = re.search(r"`train_S\.jsonl` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`", proto)
    p_c = re.search(r"`candidates\.json` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`", proto)
    print("freeze-commit protocol 2.6 value:", p_s and p_s.group(1), "| 2.5 value:", p_c and p_c.group(1))
    ok &= bool(p_s and p_c) and p_s.group(1) == exp_s and p_c.group(1) == exp_c
    print("seeds:", dm["seeds"]["DATA_SEED"], dm["seeds"]["CANDIDATE_SEED"],
          "| == transcribed:", (dm["seeds"]["DATA_SEED"], dm["seeds"]["CANDIDATE_SEED"]) == (DATA_SEED, CANDIDATE_SEED))
    ok &= (dm["seeds"]["DATA_SEED"], dm["seeds"]["CANDIDATE_SEED"]) == (DATA_SEED, CANDIDATE_SEED)
    rec_s = dm["files"]["train_S.jsonl"]["record"]
    rec_c = dm["files"]["candidates.json"]["record"]
    print("files.train_S.jsonl.record  :", rec_s)
    print("files.candidates.json.record:", rec_c)
    print("s_permutation.record        :", dm["s_permutation"]["record"])
    print("candidates.file             :", sm["candidates"]["file"])
    fmt_s = rec_s.startswith('one object per line {"fact_id", "answer_fact_id", "text"}')
    fmt_c = rec_c.startswith("one JSON object {fact_id: [4 candidates]}")
    print("record formats are the ones implemented here: train_S", fmt_s, "| candidates", fmt_c)
    ok &= fmt_s and fmt_c
    tmpl_m = {t["relation"]: t["text"] for t in sm["templates"] if t["kind"] == "TRAIN"}
    print("TRAIN templates (manifest) == transcribed protocol 2.4:", tmpl_m == TRAIN_T)
    ok &= tmpl_m == TRAIN_T
    facts = json.load(open(facts_path, encoding="utf-8"))
    fh = sha(canon(facts))
    print("facts:", len(facts), "| canonical sha256", fh, "| == manifest:", fh == dm["name_generation"]["expected_facts_canonical_sha256"])
    ok &= fh == dm["name_generation"]["expected_facts_canonical_sha256"]

    rows, attempts = build_s(facts, TRAIN_T)
    b_s = jsonl(rows)
    h_s = sha(b_s)
    print("S derangement attempts per cell:", json.dumps(attempts))
    print(f"train_S.jsonl rows {len(rows)} | canonical sha256 {h_s} | manifest {exp_s} | MATCH {h_s == exp_s}")
    print(f"AUDIT_VALUE train_S_canonical_sha256 {h_s}")
    ok &= h_s == exp_s
    cands = build_c(facts)
    b_c = canon(cands)
    h_c = sha(b_c)
    print(f"candidates.json keys {len(cands)} | canonical sha256 {h_c} | manifest {exp_c} | MATCH {h_c == exp_c}")
    print(f"AUDIT_VALUE candidates_canonical_sha256 {h_c}")
    ok &= h_c == exp_c
    print("first S row:", rows[0]["text"], "| first candidates:", json.dumps(cands[facts[0]["fact_id"]]))

    # structural checks
    learned = [f for f in facts if f["exposure"] == "learned"]
    by_id = {f["fact_id"]: f for f in facts}
    s_ok = len(rows) == 120 and all(set(r) == {"fact_id", "answer_fact_id", "text"} for r in rows)
    s_ok &= [r["fact_id"] for r in rows] == [f["fact_id"] for f in learned]
    s_ok &= all(r["fact_id"] != r["answer_fact_id"] and r["fact_id"][:-2] == r["answer_fact_id"][:-2] for r in rows)
    s_ok &= Counter(r["answer_fact_id"] for r in rows) == Counter(f["fact_id"] for f in learned)
    s_ok &= all(r["text"] == TRAIN_T[by_id[r["fact_id"]]["relation"]].replace("{E}", by_id[r["fact_id"]]["entity"])
                .replace("{A}", by_id[r["answer_fact_id"]]["answer"]) for r in rows)
    corpus = "\n".join(r["text"] for r in rows).lower()
    s_ok &= all(corpus.count(f["entity"].lower()) == 1 and corpus.count(f["answer"].lower()) == 1 for f in learned)
    s_ok &= all(corpus.count(f["entity"].lower()) == 0 and corpus.count(f["answer"].lower()) == 0
                for f in facts if f["exposure"] == "unread")
    print("train_S structure (keys, line order, derangement within cell, each learned entity/answer exactly once, "
          "unread 0, text = TRAIN template):", s_ok)
    c_ok = set(cands) == set(by_id) and len(cands) == 160
    for fid, c in cands.items():
        f = by_id[fid]
        pool = {g["answer"] for g in facts if g is not f and g["relation"] == f["relation"]
                and g["stratum"] == f["stratum"] and g["exposure"] == f["exposure"]}
        c_ok &= len(c) == 4 and len(set(c)) == 4 and c.count(f["answer"]) == 1 and set(c) - {f["answer"]} <= pool
    print("candidates structure (160 keys, 4 distinct, true answer once, distractors from the 2.5 pool):", c_ok)
    ok &= s_ok and c_ok

    for label, h in (("ALT S record without answer_fact_id", sha(jsonl(build_s(facts, TRAIN_T, "alt_text_only")[0]))),
                     ("ALT S inverse permutation", sha(jsonl(build_s(facts, TRAIN_T, "alt_inverse")[0]))),
                     ("ALT S redraw without resetting p", sha(jsonl(build_s(facts, TRAIN_T, "alt_no_reset")[0]))),
                     ("ALT S JSONL without final newline", sha(b_s[:-1])),
                     ("ALT C pool sorted", sha(canon(build_c(facts, "alt_sorted_pool")))),
                     ("ALT C answer appended last before shuffle", sha(canon(build_c(facts, "alt_answer_last"))))):
        print(f"{label}: {h} | equals manifest value: {h in (exp_s, exp_c)}")
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "train_S.jsonl"), "wb").write(b_s)
    open(os.path.join(out_dir, "candidates.json"), "wb").write(b_c)
    rs = [json.loads(l) for l in open(os.path.join(out_dir, "train_S.jsonl"), encoding="utf-8").read().splitlines()]
    rc = json.load(open(os.path.join(out_dir, "candidates.json"), encoding="utf-8"))
    rt = sha(jsonl(rs)) == h_s and sha(canon(rc)) == h_c
    print("written files re-parse to the same canonical hashes:", rt)
    ok &= rt
    return ok


run(main)
