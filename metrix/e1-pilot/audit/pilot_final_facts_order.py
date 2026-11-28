"""PILOT_REPORT_ORDER item 3, part 1: the fact order of facts.jsonl (needed by interpretation B10).

Data Auditor's own script, written new for this task. It does not import, call or copy any Executor code
(metrix/e1-pilot/src/, run_pilot.py, tests/, reports/round*/). CPU only. It loads the tokenizer.json of
Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e with the `tokenizers` library (no model weights,
no transformers, no torch). It does not read, generate or look for any TEST file; it instantiates no question.

facts.jsonl itself was not committed (it lived in <work>/data of the terminated machine). This script
  1. regenerates the 160 facts from the rules of protocol 2.2 (DATA_SEED 20261110), WITHOUT the anchor rule
     (the anchor texts would need the 94 MB parquet; see the note printed below);
  2. checks the canonical SHA-256 of the regenerated list against the frozen fact hash (protocol 2.2 text,
     DATA_MANIFEST name_generation.expected_facts_canonical_sha256, results/step1_record.json content_hashes.facts);
  3. writes the list as facts.jsonl bytes (protocol 0: one canonical object per line, joined by "\\n", one final
     "\\n") in memory and compares the SHA-256 of these bytes with the facts.jsonl byte_sha256 / canonical_sha256
     recorded by the formal run (results/step1_record.json environment.data_hashes["facts.jsonl"]) and with
     DATA_MANIFEST.json files["facts.jsonl"]. Equality of the byte hash proves that the line order used here IS
     the line order of the facts.jsonl of the formal run;
  4. cross-checks the regenerated answers with the answers in the committed DEV details
     (results/details/N_dev.json: candidates[answer_index] of every dev_qa and train_cb row), and rebuilds
     candidates.json (protocol 2.5 detail 5) and compares it with the frozen candidate hash and with the
     candidate lists in the committed DEV details;
  5. writes the fact order (fact_id, exposure, relation, stratum only; no entity / answer strings) to <out_json>
     for pilot_final_recompute.py.
PASS iff every check holds.
usage: <python with tokenizers> -I pilot_final_facts_order.py <repo_root> <qwen tokenizer.json> <out_json>"""
import hashlib
import json
import os
import platform
import random
import re
import socket
import sys
from collections import Counter, defaultdict

# ---- protocol 2.2 constants, transcribed from METRIX_E1_PROTOCOL.md (cross-checked with DATA_MANIFEST below)
DATA_SEED = 20261110
CANDIDATE_SEED = 20261111
RELS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
ONSETS = "b d f g k l m n p r s t v z br dr kr tr sh th".split()
NUCLEI = "a e i o u ae ia ou".split()
CODAS = ["", "", "n", "r", "l", "s", "th", "nd"]
LETTERS = "BCDFGHJKLMNPQRSTVWXZ"
DIGITS = "23456789"
CAP = 20000
FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()[:8], "big"))


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def regenerate(encode):
    def draw(r, st):
        if st == "natural":
            n = 2 if r.random() < 0.5 else 3
            s = "".join(r.choice(ONSETS) + r.choice(NUCLEI) + r.choice(CODAS) for _ in range(n))
            return s[:1].upper() + s[1:]
        u = r.random()
        n = 3 if u < 0.25 else 4 if u < 0.75 else 5
        return "".join(r.choice(LETTERS) for _ in range(n)) + "-" + "".join(r.choice(DIGITS) for _ in range(2))

    def form_ok(s, st):
        if st == "natural":
            return 4 <= len(s) <= 10 and len(encode(" " + s)) > 1
        return 6 <= len(s) <= 8

    def letter_part(s):
        return s.split("-", 1)[0]

    def conflicts(s, st, accepted):
        for a in accepted:
            if st == "natural":
                if s.lower() == a.lower() or s[:4] == a[:4] or edit_distance(s.lower(), a.lower()) <= 1:
                    return True
            else:
                if s == a or letter_part(s) == letter_part(a):
                    return True
                if len(s) == len(a) and sum(x != y for x, y in zip(s, a)) <= 1:
                    return True
        return False

    def kpair(s):
        return (len(encode(" " + s)), len(encode(s)))

    accepted, facts, log = [], [], []
    for rel in RELS:
        for st in STRATA:
            r = rng_rule(DATA_SEED, f"names:{rel}:{st}:entity")
            ents, nd = [], 0
            while len(ents) < 20:
                nd += 1
                if nd > CAP:
                    raise RuntimeError("entity stream exhausted")
                s = draw(r, st)
                if form_ok(s, st) and not conflicts(s, st, accepted):
                    ents.append(s)
                    accepted.append(s)
            ent_draws = nd
            r = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")
            survey, nd = Counter(), 0
            while sum(survey.values()) < 400:
                nd += 1
                if nd > CAP:
                    raise RuntimeError("survey exhausted")
                s = draw(r, st)
                if form_ok(s, st):
                    survey[kpair(s)] += 1
            top = max(survey.values())
            target = min(k for k, v in survey.items() if v == top)
            r = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")   # restart the answer stream (detail 3)
            ans, nd = [], 0
            while len(ans) < 20:
                nd += 1
                if nd > CAP:
                    raise RuntimeError("answer stream exhausted")
                s = draw(r, st)
                if form_ok(s, st) and kpair(s) == target and not conflicts(s, st, accepted):
                    ans.append(s)
                    accepted.append(s)
            ab = "nat" if st == "natural" else "rnd"
            for i in range(20):
                lrn = i < 15
                facts.append({"fact_id": f"E1P-{'L' if lrn else 'U'}-{rel}-{ab}-{(i + 1) if lrn else (i - 14):02d}",
                              "exposure": "learned" if lrn else "unread", "relation": rel, "stratum": st,
                              "entity": ents[i], "answer": ans[i]})
            log.append((f"{rel}/{st}", ent_draws, target, nd))
    return facts, log


def main():
    repo, tok_path, out_json = sys.argv[1:4]
    e1 = os.path.join(repo, "metrix", "e1-pilot")
    ok = True
    print(f"host {socket.gethostname()} | {platform.platform()} | python {sys.version.split()[0]} | CPU only")
    import tokenizers
    print(f"tokenizers {tokenizers.__version__} (tokenizer.json only; no transformers, no torch, no weights)")
    dm = json.load(open(os.path.join(e1, "DATA_MANIFEST.json"), encoding="utf-8"))
    proto = open(os.path.join(e1, "METRIX_E1_PROTOCOL.md"), encoding="utf-8").read()
    step1 = json.load(open(os.path.join(e1, "results", "step1_record.json"), encoding="utf-8"))
    sfr = json.load(open(os.path.join(e1, "results", "selection_freeze_record.json"), encoding="utf-8"))
    spm = json.load(open(os.path.join(e1, "SPLIT_MANIFEST.json"), encoding="utf-8"))

    print("\n== 0. tokenizer file")
    tb = open(tok_path, "rb").read()
    want = dm["model"]["tokenizer"]["files_sha256"]["tokenizer.json"]
    print(f"tokenizer.json bytes {len(tb)} sha256 {sha(tb)} | DATA_MANIFEST model.tokenizer.files_sha256 {want} | MATCH {sha(tb) == want}")
    print(f"DATA_MANIFEST model.tokenizer repo/revision: {dm['model']['tokenizer']['repo']}@{dm['model']['tokenizer']['revision']}")
    ok &= sha(tb) == want
    tk = tokenizers.Tokenizer.from_file(tok_path)

    def encode(s):
        return tk.encode(s, add_special_tokens=False).ids

    print("\n== 1. constants transcribed from protocol 2.2 vs DATA_MANIFEST")
    ng = dm["name_generation"]
    checks = [("seeds.DATA_SEED", dm["seeds"]["DATA_SEED"], DATA_SEED),
              ("seeds.CANDIDATE_SEED", dm["seeds"]["CANDIDATE_SEED"], CANDIDATE_SEED),
              ("facts.relations", dm["facts"]["relations"], RELS), ("facts.strata", dm["facts"]["strata"], STRATA),
              ("name_generation.natural.onsets", ng["natural"]["onsets"], ONSETS),
              ("name_generation.natural.nuclei", ng["natural"]["nuclei"], NUCLEI),
              ("name_generation.natural.codas", ng["natural"]["codas"], CODAS),
              ("name_generation.random.letters", ng["random"]["letters"], LETTERS),
              ("name_generation.random.digits", ng["random"]["digits"], DIGITS),
              ("name_generation.max_draws_per_stream", ng["max_draws_per_stream"], CAP),
              ("name_generation.expected_facts_fields", ng["expected_facts_fields"], FIELDS)]
    for name, got, exp in checks:
        print(f"  {name}: manifest == transcribed {got == exp}")
        ok &= got == exp
    print(f"  name_generation.order: {ng['order']}")

    print("\n== 2. regeneration (protocol 2.2, anchor rule NOT applied)")
    print("note: the anchor rule (reject strings occurring in the 512 anchor texts) is not applied because the anchor")
    print("      texts are not available on this host without downloading the parquet. This cannot make a wrong list")
    print("      pass: the result is accepted only if its canonical hash equals the frozen fact hash below. My own")
    print("      round-9 regeneration WITH the anchor rule recorded 'anchor-rule rejections: 0'")
    print("      (metrix/e1-pilot/audit/stdout/87a244db28a901f9e89282b50df76778ab5c2887/04_r8_facts.txt).")
    facts, log = regenerate(encode)
    for cell, ed, tgt, adr in log:
        print(f"  cell {cell:<17} entity draws {ed:>3} | target (K_st, K_qa) {tgt} | answer draws {adr:>3}")
    strings = [x for f in facts for x in (f["entity"], f["answer"])]
    print(f"facts {len(facts)} {dict(Counter(f['exposure'] for f in facts))} | distinct strings {len(set(strings))}")
    ok &= len(facts) == 160 and len(set(strings)) == 320

    print("\n== 3. canonical hash of the fact list (protocol 2.2 method)")
    m = re.search(r"\*\*复现\*\*:按以上规则,`DATA_SEED = 20261110` 生成的 160 条 fact.*?必须等于 `([0-9a-f]{64})`", proto)
    h_list = sha(canon(facts))
    refs = {"protocol 2.2 '复现' sentence": m.group(1) if m else None,
            "DATA_MANIFEST name_generation.expected_facts_canonical_sha256": ng["expected_facts_canonical_sha256"],
            "results/step1_record.json content_hashes.facts": step1["content_hashes"]["facts"],
            "results/selection_freeze_record.json data_content_hashes.facts": sfr["data_content_hashes"]["facts"]}
    print(f"regenerated list canonical sha256: {h_list}")
    for k, v in refs.items():
        print(f"  {k}: {v} | MATCH {v == h_list}")
        ok &= v == h_list

    print("\n== 4. facts.jsonl bytes (protocol 0 JSONL rule) vs the byte hash recorded by the formal run")
    jsonl = b"\n".join(canon(f) for f in facts) + b"\n"
    h_bytes = sha(jsonl)
    rec = step1["environment"]["data_hashes"]["facts.jsonl"]
    man = dm["files"]["facts.jsonl"]
    print(f"facts.jsonl rebuilt in memory: {len(jsonl)} bytes, {jsonl.count(bytes([10]))} lines, sha256 {h_bytes}")
    for k, v in [("results/step1_record.json environment.data_hashes['facts.jsonl'].byte_sha256", rec["byte_sha256"]),
                 ("results/step1_record.json environment.data_hashes['facts.jsonl'].canonical_sha256", rec["canonical_sha256"]),
                 ("DATA_MANIFEST.json files['facts.jsonl'].byte_sha256", man["byte_sha256"]),
                 ("DATA_MANIFEST.json files['facts.jsonl'].canonical_sha256", man["canonical_sha256"])]:
        print(f"  {k}: {v} | MATCH {v == h_bytes}")
        ok &= v == h_bytes
    print(f"results/step1_record.json data_generation.rows['facts.jsonl']: {step1['data_generation']['rows']['facts.jsonl']}")
    ok &= step1["data_generation"]["rows"]["facts.jsonl"] == 160
    # reading the lines back in file order gives the same list (the line order is the list order)
    back = [json.loads(x) for x in jsonl.decode("utf-8").split("\n")[:-1]]
    print(f"lines read back in file order == regenerated list: {back == facts} | every line has exactly the six 2.2 fields: "
          f"{all(set(x) == set(FIELDS) for x in back)}")
    ok &= back == facts and all(set(x) == set(FIELDS) for x in back)

    print("\n== 5. cross-check with committed DEV details (results/details/N_dev.json)")
    nd = json.load(open(os.path.join(e1, "results", "details", "N_dev.json"), encoding="utf-8"))
    ans = {f["fact_id"]: f["answer"] for f in facts}
    det_ans, det_cands, bad = defaultdict(set), defaultdict(set), []
    for part in ("dev_qa", "train_cb"):
        for row in nd["evaluation"][part]:
            det_ans[row["fact_id"]].add(row["candidates"][row["answer_index"]])
            det_cands[row["fact_id"]].add(tuple(row["candidates"]))
    for fid, a in ans.items():
        if det_ans.get(fid) != {a}:
            bad.append(fid)
    print(f"fact_ids in details {len(det_ans)} | == regenerated ids {set(det_ans) == set(ans)} | facts whose details answer "
          f"!= regenerated answer: {bad}")
    ok &= set(det_ans) == set(ans) and not bad
    # candidates.json, protocol 2.5 detail 5
    cands = {}
    for f in facts:
        pool = [g["answer"] for g in facts if g["relation"] == f["relation"] and g["stratum"] == f["stratum"]
                and g["exposure"] == f["exposure"] and g["fact_id"] != f["fact_id"]]
        r = rng_rule(CANDIDATE_SEED, f"cand:{f['fact_id']}")
        d = r.sample(pool, 3)
        c = [f["answer"]] + d
        r.shuffle(c)
        cands[f["fact_id"]] = c
    hc = sha(canon(cands))
    for k, v in [("SPLIT_MANIFEST candidates.candidate_mapping_sha256", spm["candidates"]["candidate_mapping_sha256"]),
                 ("results/step1_record.json content_hashes.candidates", step1["content_hashes"]["candidates"])]:
        print(f"rebuilt candidates.json canonical sha256 {hc} | {k} {v} | MATCH {hc == v}")
        ok &= hc == v
    cbad = [fid for fid in cands if det_cands.get(fid) != {tuple(cands[fid])}]
    print(f"facts whose candidate list in N_dev.json differs from the rebuilt one: {cbad}")
    ok &= not cbad

    print("\n== 6. fact order")
    rule = []
    for rel in RELS:
        for ab in ("nat", "rnd"):
            rule += [f"E1P-L-{rel}-{ab}-{i:02d}" for i in range(1, 16)] + [f"E1P-U-{rel}-{ab}-{i:02d}" for i in range(1, 6)]
    order = [f["fact_id"] for f in facts]
    print(f"order of facts.jsonl (confirmed by the byte hash above) == protocol 2.2 generation-order rule "
          f"(cells capital..river x natural, random; per cell L-01..15 then U-01..05): {order == rule}")
    ok &= order == rule
    id_ok = all((f["exposure"] == "learned") == f["fact_id"].startswith("E1P-L-") and
                (f["stratum"] == "natural") == (f["fact_id"].split("-")[3] == "nat") and
                f["relation"] == f["fact_id"].split("-")[2] for f in facts)
    print(f"exposure / stratum / relation fields agree with the fact_id pattern of SPLIT_MANIFEST fact_ids: {id_ok}")
    ok &= id_ok
    for ex in ("learned", "unread"):
        for st in STRATA:
            ids = [f["fact_id"] for f in facts if f["exposure"] == ex and f["stratum"] == st]
            print(f"  {ex:<7} {st:<7}: {len(ids):>3} facts, in facts.jsonl order first {ids[:2]} ... last {ids[-1]}")
    out = {"what": "fact order of facts.jsonl of the formal run (B10), regenerated by pilot_final_facts_order.py",
           "confirmation": {"facts_jsonl_sha256_rebuilt": h_bytes,
                            "step1_record_facts_jsonl_byte_sha256": rec["byte_sha256"],
                            "fact_list_canonical_sha256": h_list,
                            "byte_hash_match": h_bytes == rec["byte_sha256"],
                            "list_hash_match": h_list == ng["expected_facts_canonical_sha256"]},
           "facts": [{k: f[k] for k in ("fact_id", "exposure", "relation", "stratum")} for f in facts]}
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"wrote {out_json} (fact_id, exposure, relation, stratum of the 160 facts in facts.jsonl order)")
    return ok


if __name__ == "__main__":
    try:
        res = main()
    except BaseException:
        import traceback
        sys.stdout.flush()
        traceback.print_exc(file=sys.stdout)
        print("RESULT: FAIL (exception)")
        sys.exit(2)
    print("RESULT: PASS" if res else "RESULT: FAIL")
    sys.exit(0 if res else 1)
