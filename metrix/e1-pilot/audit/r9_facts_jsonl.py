"""R9-2: v1.1 section 2.2 "fact 哈希的比对方法" (round 9 item 1c) applied to the facts the auditor regenerated
(r8_facts.py), plus the definition's items 3 (candidate feasibility) and 4 (fact_id split) on the same facts.
Data Auditor's own script; no Executor code is imported, called or copied. Loads the pinned Qwen tokenizer only
(four files), never weights. No question is instantiated (no DEV / TEST item, no TEST data).
Exceptions -> RESULT: FAIL (r6_guard).

a. facts.jsonl: write the 160 regenerated facts as JSONL (section 0: one canonical object per line, joined by "\n",
   one final "\n") into <out_dir>; read it back line by line in file order; canonical SHA-256 of that JSON list
   (section 0 rule) must equal the value written in the v1.1 section 2.2 method sentence, in
   DATA_MANIFEST name_generation.expected_facts_canonical_sha256 of the commit and of the v1 freeze commit.
   The JSONL canonical_sha256 (a different byte string) is printed and must differ from that value; the 2.2
   sentence says it is not compared. Each line must carry exactly the six fields of 2.2.
b. candidate feasibility: for every fact, the number of facts (including itself) with the same relation, stratum,
   exposure and the same answer token count, token count = (len(encode(" " + answer)), len(encode(answer))),
   add_special_tokens=False; also per single count. Reported per cell (relation x stratum x exposure); the minimum
   and the cells with fewer than 4 (4-way candidates need the answer plus 3 distractors) are printed.
c. split of fact_ids: 160 distinct ids; learned = E1P-L-* (120), unread = E1P-U-* (40), disjoint; per relation x
   stratum 15 learned numbered 01-15 and 5 unread numbered 01-05; exposure field agrees with the id letter;
   the auditor's rebuilt train_S.jsonl contains only learned ids (fact_id and answer_fact_id).
PASS iff a, b (minimum >= 4) and c hold.
usage: python -I r9_facts_jsonl.py <repo_root> <commit> <v1_commit> <facts.json> <train_S.jsonl> <qwen_tok_dir> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess
from collections import Counter, defaultdict
from common import sha, canon, load_tok, enc
from r6_guard import run

FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]
RELS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]


def git_blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], capture_output=True, check=True).stdout


def main():
    repo, commit, v1, facts_path, s_path, tokdir, out_dir = sys.argv[1:8]
    ok = True
    proto = git_blob(repo, commit, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md").decode("utf-8")
    m = re.search(r"\*\*fact 哈希的比对方法\*\*:从 `facts\.jsonl` 读出 fact 列表.*?与 `([0-9a-f]{64})` 比对。", proto)
    exp_2_2 = m.group(1) if m else None
    exp_c = json.loads(git_blob(repo, commit, "metrix/e1-pilot/DATA_MANIFEST.json"))["name_generation"]["expected_facts_canonical_sha256"]
    exp_v1 = json.loads(git_blob(repo, v1, "metrix/e1-pilot/DATA_MANIFEST.json"))["name_generation"]["expected_facts_canonical_sha256"]
    print("v1.1 section 2.2 method sentence value:", exp_2_2)
    print("commit manifest value                 :", exp_c)
    print("v1 freeze-commit manifest value       :", exp_v1)
    ok &= exp_2_2 is not None and exp_2_2 == exp_c == exp_v1

    print("\n== a. facts.jsonl method (v1.1 section 2.2)")
    facts = json.load(open(facts_path, encoding="utf-8"))
    print("regenerated facts:", len(facts), "| canonical sha256 of the list as generated:", sha(canon(facts)))
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "facts.jsonl")
    with open(p, "wb") as fh:
        fh.write(b"\n".join(canon(f) for f in facts) + b"\n")
    raw = open(p, "rb").read()
    lines = raw.decode("utf-8").split("\n")
    assert lines[-1] == "", "no final newline"
    read = [json.loads(l) for l in lines[:-1]]
    fields_ok = all(list(r.keys()) == sorted(FIELDS) and set(r) == set(FIELDS) for r in read)
    h_list = sha(canon(read))
    h_jsonl = sha(b"\n".join(canon(r) for r in read) + b"\n")
    print(f"wrote {p}: lines {len(read)} | byte_sha256 {sha(raw)}")
    print(f"every line has exactly the six fields of 2.2: {fields_ok} | order of lines = generation order: {read == facts}")
    print(f"canonical sha256 of the list read from facts.jsonl {h_list} | expected {exp_c} | MATCH {h_list == exp_c}")
    print(f"facts.jsonl canonical_sha256 by the JSONL rule (not compared per 2.2) {h_jsonl} | differs from the list hash: {h_jsonl != h_list}")
    print(f"AUDIT_VALUE facts_canonical_sha256_from_jsonl {h_list}")
    ok &= len(read) == 160 and fields_ok and read == facts and h_list == exp_c and h_jsonl != h_list

    print("\n== b. candidate feasibility (same relation, stratum, exposure, answer token count)")
    tok = load_tok(tokdir)
    print("tokenizer dir files:", sorted(x for x in os.listdir(tokdir) if not x.startswith(".")), "| class", type(tok).__name__)
    kp = {f["fact_id"]: (len(enc(tok, " " + f["answer"])), len(enc(tok, f["answer"]))) for f in facts}
    cells = defaultdict(list)
    for f in facts:
        cells[(f["relation"], f["stratum"], f["exposure"])].append(f)
    mins, short = [], []
    for rel in RELS:
        for st in STRATA:
            for ex in ("learned", "unread"):
                cf = cells[(rel, st, ex)]
                c_pair = [sum(kp[g["fact_id"]] == kp[f["fact_id"]] for g in cf) for f in cf]
                c_sp = [sum(kp[g["fact_id"]][0] == kp[f["fact_id"]][0] for g in cf) for f in cf]
                c_ns = [sum(kp[g["fact_id"]][1] == kp[f["fact_id"]][1] for g in cf) for f in cf]
                mins.append(min(c_pair))
                if min(c_pair) < 4:
                    short.append((rel, st, ex, min(c_pair)))
                print(f"  {rel:<8} {st:<7} {ex:<7} facts {len(cf):>2} | token-count pairs {dict(Counter(kp[f['fact_id']] for f in cf))} "
                      f"| candidates per fact (pair) min {min(c_pair)} max {max(c_pair)} | ' '+a only min {min(c_sp)} | a only min {min(c_ns)}")
    print(f"minimum candidates per fact over all 16 cells: {min(mins)} | cells with fewer than 4: {short}")
    ok &= min(mins) >= 4 and not short

    print("\n== c. fact_id split")
    ids = [f["fact_id"] for f in facts]
    L = [i for i in ids if i.startswith("E1P-L-")]
    U = [i for i in ids if i.startswith("E1P-U-")]
    exp_ok = all((f["exposure"] == "learned") == f["fact_id"].startswith("E1P-L-") and
                 (f["exposure"] == "unread") == f["fact_id"].startswith("E1P-U-") for f in facts)
    fmt = all(re.fullmatch(r"E1P-[LU]-(capital|currency|founder|river)-(nat|rnd)-\d\d", i) for i in ids)
    per = True
    for rel in RELS:
        for st, ab in zip(STRATA, ("nat", "rnd")):
            nl = sorted(int(i[-2:]) for i in L if f"-{rel}-{ab}-" in i)
            nu = sorted(int(i[-2:]) for i in U if f"-{rel}-{ab}-" in i)
            per &= nl == list(range(1, 16)) and nu == list(range(1, 6))
    s_rows = [json.loads(l) for l in open(s_path, encoding="utf-8").read().splitlines()]
    s_ids = {r["fact_id"] for r in s_rows} | {r["answer_fact_id"] for r in s_rows}
    print(f"ids {len(ids)} distinct {len(set(ids))} | learned {len(L)} | unread {len(U)} | learned & unread {sorted(set(L) & set(U))} "
          f"| other prefixes {len(ids) - len(L) - len(U)}")
    print(f"id format: {fmt} | exposure field agrees with id: {exp_ok} | per cell learned 01-15 and unread 01-05: {per}")
    print(f"train_S rows {len(s_rows)} | ids in train_S {len(s_ids)} | all learned: {s_ids <= set(L)} | == learned set: {s_ids == set(L)}")
    ok &= len(set(ids)) == 160 and len(L) == 120 and len(U) == 40 and not (set(L) & set(U)) and fmt and exp_ok and per
    ok &= s_ids == set(L)
    return ok


run(main)
