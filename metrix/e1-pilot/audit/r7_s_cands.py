"""R7-1g: independent rebuild of train_S.jsonl (protocol 2.6, detail 4) and candidates.json (protocol 2.5, detail 5)
from the 160 facts that the auditor regenerated itself (r4_regen_facts.py), and comparison of their canonical SHA-256
with the values written into the protocol and the manifests in round 7.
Data Auditor's own script; no Executor code is imported, called or copied (in particular not reports/round7/gen_s_cands.py
and not reports/round2/names.py). Standard library only (no tokenizer, no model, no TEST data: only the four TRAIN
templates are instantiated). Exceptions -> RESULT: FAIL (r6_guard).

Rules implemented, as read from the protocol text (quoted in the output):
  seeds, rng_rule, canonical JSON / JSONL ............ section 0 ("种子", "哈希")
  cell order, fact order .............................. section 2.2 ("生成顺序")
  TRAIN templates ...................................... section 2.4 table (cross-checked with SPLIT_MANIFEST templates)
  S: one r per cell, p = list(range(15)), r.shuffle(p), redraw from list(range(15)) with the same r while p[i] == i;
     learned facts 01..15 -> i = 0..14; statement i = TRAIN({E}=entity_i, {A}=answer_p[i]);
     record {"fact_id", "answer_fact_id", "text"}; lines in cell order, then i ....... section 2.6 detail 4
  candidates: r = rng_rule(CANDIDATE_SEED, "cand:<fact_id>"); pool = answers of the other facts of the same relation,
     stratum and exposure in fact generation order; d = r.sample(pool, 3); c = [a_f] + d; r.shuffle(c);
     candidates.json = {fact_id: c} ...................................................... section 2.5 detail 5
Alternative readings are computed as well (labelled ALT); each is printed with the sentence of the protocol that
excludes it, so that one can see which sentences determine the hash.

PASS iff: the facts hash equals 406c8801...; the protocol and manifest seeds / templates agree; the two hashes of this
build equal the two expected values given in the round-7 audit request, which must also be the values in the protocol
text and the manifests; the written files re-parse to the same canonical bytes; the structural checks hold.
usage: python -I r7_s_cands.py <my_facts.json> <protocol.md> <DATA_MANIFEST.json> <SPLIT_MANIFEST.json> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, platform, re
from collections import Counter
from common import sha, canon, rng_rule, FACTS_SHA_PROTOCOL
from r6_guard import run

EXPECTED_S = "686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e"      # round-7 audit request
EXPECTED_C = "e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705"      # round-7 audit request
RELS = ["capital", "currency", "founder", "river"]                                   # protocol 2.2 "生成顺序"
STRATA = ["natural", "random"]


def jsonl_bytes(records):
    # protocol section 0: one canonical object per line, joined by "\n", one final "\n"
    return b"\n".join(canon(r) for r in records) + b"\n"


def build_s(facts, train_t, data_seed, mode="main"):
    """mode: main | alt_inverse | alt_no_reset"""
    rows, attempts = [], {}
    for rel in RELS:
        for st in STRATA:
            cell = sorted((f for f in facts if f["relation"] == rel and f["stratum"] == st and f["exposure"] == "learned"),
                          key=lambda f: int(f["fact_id"][-2:]))
            assert [int(f["fact_id"][-2:]) for f in cell] == list(range(1, 16)), (rel, st)
            r = rng_rule(data_seed, "s-permutation:%s:%s" % (rel, st))
            n, p = 0, list(range(15))
            while True:
                if mode != "alt_no_reset":
                    p = list(range(15))
                r.shuffle(p)
                n += 1
                if all(p[i] != i for i in range(15)):
                    break
                assert n < 10000
            attempts["%s/%s" % (rel, st)] = n
            if mode == "alt_inverse":
                q = [0] * 15
                for i, j in enumerate(p):
                    q[j] = i
                p = q
            for i, f in enumerate(cell):
                g = cell[p[i]]
                rows.append({"fact_id": f["fact_id"], "answer_fact_id": g["fact_id"],
                             "text": train_t[rel].replace("{E}", f["entity"]).replace("{A}", g["answer"])})
    return rows, attempts


def build_c(facts, seed, mode="main"):
    """mode: main | alt_data_seed (seed passed in) | alt_sorted_pool | alt_answer_last | alt_shuffle_pool"""
    out = {}
    for f in facts:
        pool = [g["answer"] for g in facts
                if (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])
                and g["fact_id"] != f["fact_id"]]
        if mode == "alt_sorted_pool":
            pool = sorted(pool)
        r = rng_rule(seed, "cand:%s" % f["fact_id"])
        if mode == "alt_shuffle_pool":
            pp = list(pool)
            r.shuffle(pp)
            d = pp[:3]
        else:
            d = r.sample(pool, 3)
        c = (d + [f["answer"]]) if mode == "alt_answer_last" else ([f["answer"]] + d)
        r.shuffle(c)
        out[f["fact_id"]] = c
    return out


def main():
    facts_path, proto_path, dm_path, sm_path, out_dir = sys.argv[1:6]
    ok = True
    print("python", sys.version.split()[0], platform.python_implementation(), sys.executable,
          "| PYTHONHASHSEED", os.environ.get("PYTHONHASHSEED"), "| pid", os.getpid())
    proto = open(proto_path, encoding="utf-8").read()
    dm = json.load(open(dm_path, encoding="utf-8"))
    sm = json.load(open(sm_path, encoding="utf-8"))

    # ---- seeds and rng rule (section 0)
    ds = int(re.search(r"`DATA_SEED = (\d+)`", proto).group(1))
    cs = int(re.search(r"`CANDIDATE_SEED = (\d+)`", proto).group(1))
    rule_txt = re.search(r"`(random\.Random\(int\.from_bytes\(sha256\([^`]+)`", proto).group(1)
    print("section 0 seeds: DATA_SEED", ds, "CANDIDATE_SEED", cs, "| DATA_MANIFEST seeds:",
          dm["seeds"]["DATA_SEED"], dm["seeds"]["CANDIDATE_SEED"])
    print("section 0 rng rule text:", rule_txt)
    ok &= ds == dm["seeds"]["DATA_SEED"] and cs == dm["seeds"]["CANDIDATE_SEED"]
    hash_line = [l for l in proto.split("\n") if l.startswith("**哈希**")][0]
    print("section 0 hash rule:", hash_line)

    # ---- TRAIN templates (2.4) vs SPLIT_MANIFEST
    train_t = {}
    for m in re.finditer(r"^\| (capital|currency|founder|river) \| TRAIN \| (.+) \|$", proto, re.M):
        train_t[m.group(1)] = m.group(2).strip()
    sm_train = {t["relation"]: t["text"] for t in sm["templates"] if t["set"] == "TRAIN"}
    print("2.4 TRAIN templates:", json.dumps(train_t, ensure_ascii=False))
    print("2.4 TRAIN templates == SPLIT_MANIFEST TRAIN templates:", train_t == sm_train)
    ok &= train_t == sm_train and sorted(train_t) == RELS

    # ---- protocol sentences used (2.5 detail 5, 2.6 detail 4)
    for key in ("**调用方式(细节 5)**", "`candidates.json`:", "**调用方式(细节 4)**", "cell 内的 learned fact 按 fact_id",
                "`train_S.jsonl` 每行一个对象", "- **干扰项的池**", "- 抽取:"):
        lines = [l.strip() for l in proto.split("\n") if key in l]
        print("protocol:", lines[0] if lines else "NOT FOUND: " + key)
        ok &= len(lines) == 1

    # ---- facts
    raw = open(facts_path, "rb").read()
    facts = json.loads(raw)
    fh = sha(canon(facts))
    print("my facts:", len(facts), "| canonical sha256", fh, "| == 406c8801... (protocol 2.2)", fh == FACTS_SHA_PROTOCOL)
    ok &= fh == FACTS_SHA_PROTOCOL
    order = [(f["relation"], f["stratum"]) for f in facts]
    cells_in_order = list(dict.fromkeys(order))
    print("fact order: cells", ["%s/%s" % c for c in cells_in_order], "| contiguous:", len(cells_in_order) == 8 and
          all(order[k] == cells_in_order[k // 20] for k in range(160)))

    # ---- main build
    rows, attempts = build_s(facts, train_t, ds)
    s_bytes = jsonl_bytes(rows)
    cands = build_c(facts, cs)
    c_bytes = canon(cands)
    hs, hc = sha(s_bytes), sha(c_bytes)
    print("S derangement attempts per cell:", json.dumps(attempts))
    print("train_S.jsonl: rows", len(rows), "| bytes", len(s_bytes), "| canonical sha256", hs)
    print("   expected (audit request)                  ", EXPECTED_S, "| equal", hs == EXPECTED_S)
    print("candidates.json: keys", len(cands), "| bytes", len(c_bytes), "| canonical sha256", hc)
    print("   expected (audit request)                  ", EXPECTED_C, "| equal", hc == EXPECTED_C)
    ok &= hs == EXPECTED_S and hc == EXPECTED_C
    print("first S row:", rows[0], "| first candidates:", next(iter(cands.items())))

    # ---- expected values as written in the repository
    v_dm = dm["s_permutation"]["expected_train_S_canonical_sha256"]
    v_sm = sm["candidates"]["candidate_mapping_sha256"]
    print("DATA_MANIFEST s_permutation.expected_train_S_canonical_sha256 == mine:", v_dm == hs,
          "| SPLIT_MANIFEST candidates.candidate_mapping_sha256 == mine:", v_sm == hc)
    print("occurrences in protocol text: train_S hash", proto.count(hs), "| candidates hash", proto.count(hc))
    ok &= v_dm == hs and v_sm == hc and proto.count(hs) == 1 and proto.count(hc) == 1
    print("other manifest slots (informational): DATA_MANIFEST files.train_S.jsonl",
          dm["files"]["train_S.jsonl"], "| files.candidates.json", dm["files"]["candidates.json"],
          "| SPLIT_MANIFEST split_sha256.train_S.jsonl", sm["split_sha256"]["train_S.jsonl"])

    # ---- write and re-parse
    os.makedirs(out_dir, exist_ok=True)
    ps, pc = os.path.join(out_dir, "train_S.jsonl"), os.path.join(out_dir, "candidates.json")
    with open(ps, "wb") as fh_:
        fh_.write(s_bytes)
    with open(pc, "wb") as fh_:
        fh_.write(c_bytes)
    b1, b2 = open(ps, "rb").read(), open(pc, "rb").read()
    re_s = jsonl_bytes([json.loads(l) for l in b1.decode("utf-8").split("\n")[:-1]])
    re_c = canon(json.loads(b2))
    print("written files: byte sha256", sha(b1), sha(b2), "| re-parsed canonical == written bytes:", re_s == b1, re_c == b2)
    ok &= re_s == b1 and re_c == b2 and sha(b1) == hs and sha(b2) == hc

    # ---- structural checks
    byid = {f["fact_id"]: f for f in facts}
    learned = [f for f in facts if f["exposure"] == "learned"]
    unread = [f for f in facts if f["exposure"] == "unread"]
    chk = {}
    chk["S rows == 120, one per learned fact, in fact order"] = [r["fact_id"] for r in rows] == [f["fact_id"] for f in learned]
    chk["S no fixed point (answer_fact_id != fact_id)"] = all(r["fact_id"] != r["answer_fact_id"] for r in rows)
    chk["S answer_fact_id within the same cell, each used once"] = all(
        byid[r["answer_fact_id"]]["relation"] == byid[r["fact_id"]]["relation"]
        and byid[r["answer_fact_id"]]["stratum"] == byid[r["fact_id"]]["stratum"]
        and byid[r["answer_fact_id"]]["exposure"] == "learned" for r in rows) and \
        sorted(r["answer_fact_id"] for r in rows) == sorted(f["fact_id"] for f in learned)
    S_text = "\n".join(r["text"] for r in rows).lower()
    chk["S each learned entity and answer exactly once (case-insensitive substring)"] = all(
        S_text.count(f[k].lower()) == 1 for f in learned for k in ("entity", "answer"))
    chk["S unread entities / answers 0 times (L3a, S part)"] = all(S_text.count(f[k].lower()) == 0 for f in unread for k in ("entity", "answer"))
    true_lines = {train_t[f["relation"]].replace("{E}", f["entity"]).replace("{A}", f["answer"]) for f in learned}
    chk["S contains no true TRAIN statement"] = not any(r["text"] in true_lines for r in rows)
    chk["candidates: 160 keys == fact ids"] = sorted(cands) == sorted(byid)
    chk["candidates: 4 distinct, true answer exactly once"] = all(
        len(c) == 4 and len(set(c)) == 4 and c.count(byid[k]["answer"]) == 1 for k, c in cands.items())
    chk["candidates: distractors from the 2.5 pool (same relation, stratum, exposure)"] = all(
        x in {g["answer"] for g in facts if (g["relation"], g["stratum"], g["exposure"]) ==
              (byid[k]["relation"], byid[k]["stratum"], byid[k]["exposure"])} for k, c in cands.items() for x in c)
    pos = Counter(c.index(byid[k]["answer"]) for k, c in cands.items())
    print("position of the true answer among the 4 candidates {pos: count}:", dict(sorted(pos.items())))
    for k, v in chk.items():
        print("check:", k, "->", v)
        ok &= v

    # ---- alternative readings (each excluded by a sentence of the protocol)
    print("== ALT readings (hash differs => the quoted sentence is what fixes the result)")
    alts = [
        ("S ALT inverse permutation ({A} of statement i = answer of fact q[i], p[q[i]] = i)",
         sha(jsonl_bytes(build_s(facts, train_t, ds, "alt_inverse")[0])), hs,
         "2.6: `{A}` 取第 `p[i]` 条 fact 的 answer"),
        ("S ALT redraw by shuffling the previous p again (no reset)",
         sha(jsonl_bytes(build_s(facts, train_t, ds, "alt_no_reset")[0])), hs,
         "2.6: 用同一个 `r` 再从 `list(range(15))` 开始抽"),
        ("S ALT record without answer_fact_id ({fact_id, text})",
         sha(jsonl_bytes([{"fact_id": r["fact_id"], "text": r["text"]} for r in rows])), hs,
         "2.6: `train_S.jsonl` 每行一个对象 {fact_id, answer_fact_id, text}"),
        ("S ALT plain text lines (no JSON)",
         sha(("\n".join(r["text"] for r in rows) + "\n").encode("utf-8")), hs, "2.6 record format"),
        ("C ALT seed DATA_SEED instead of CANDIDATE_SEED (literal reading of round-7 item 1g '用 DATA_SEED')",
         sha(canon(build_c(facts, ds))), hc, "2.5: 用 `rng_rule(CANDIDATE_SEED, \"cand:<fact_id>\")`"),
        ("C ALT pool sorted alphabetically", sha(canon(build_c(facts, cs, "alt_sorted_pool"))), hc,
         "2.5: 池按第 2.2 节的 fact 生成顺序排列"),
        ("C ALT c = d + [a_f]", sha(canon(build_c(facts, cs, "alt_answer_last"))), hc, "2.5: 令 `c = [a_f] + d`"),
        ("C ALT shuffle the pool and take 3 instead of r.sample", sha(canon(build_c(facts, cs, "alt_shuffle_pool"))), hc,
         "2.5: 依次调用 `d = r.sample(池, 3)`"),
    ]
    for name, h, main_h, why in alts:
        print("  %-100s %s | differs from main: %s | excluded by %s" % (name, h, h != main_h, why))
    print("  note: 'a new generator per attempt' is not an executable alternative: the same purpose gives the same first"
          " shuffle, so a cell whose first shuffle has a fixed point would never terminate (2.6 says 用同一个 r)")
    return bool(ok)


if __name__ == "__main__":
    run(main)
