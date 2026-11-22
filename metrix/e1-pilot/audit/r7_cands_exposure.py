"""R7: candidate feasibility (four constraints), exposure matching and leakage L3a / L3b / L4 (DEV part) / L5, using the
train_S.jsonl and candidates.json that r7_s_cands.py rebuilt (no Executor file is read).
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).
TRAIN, DEV and Y templates only; TEST templates are never instantiated.

  four constraints (agent definition item 3): same relation, same stratum, same exposure, same scored-token count
    K_st = len(encode(" " + c)) (protocol 2.2 / section 5). Per cell = (relation, stratum, exposure): number of answers
    with the cell's K_st; minimum over cells; cells with fewer than 4.
  actual candidates.json: every list's 4 members satisfy the four constraints with the fact's own answer.
  exposure (protocol 2.5): every candidate of a learned fact occurs exactly once in train_F, in train_S and in train_Y
    and 0 times in the anchor text; every candidate of an unread fact occurs 0 times (case-insensitive substrings).
  token form in S: the ids of " " + answer occur as a contiguous run in the ids of the S statement (as in train_F).
  L3a (unread entity / answer in train_F, train_S, train_Y, anchor) 0; L3b (learned answer in anchor) 0;
  L4 DEV part (DEV question verbatim, also case-insensitive, in train_F, train_S, train_Y, anchor) 0;
  L5 (learned / unread fact_id sets disjoint; 320 strings distinct) 0; split counts as in protocol 2.1 / 2.3 / 2.6.
usage: python -I r7_cands_exposure.py <qwen_tok_dir> <my_facts.json> <my train_S.jsonl> <my candidates.json>
                                      <my anchor.json> <SPLIT_MANIFEST.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter, defaultdict
from common import load_tok, enc, sha, canon
from r6_guard import run


def contains_run(seq, sub):
    n = len(sub)
    return any(seq[i:i + n] == sub for i in range(len(seq) - n + 1))


def main():
    qdir, facts_p, s_p, c_p, anchor_p, sm_p = sys.argv[1:7]
    ok = True
    tok = load_tok(qdir)
    facts = json.load(open(facts_p, encoding="utf-8"))
    S = [json.loads(l) for l in open(s_p, encoding="utf-8").read().split("\n")[:-1]]
    C = json.load(open(c_p, encoding="utf-8"))
    anchor = json.load(open(anchor_p, encoding="utf-8"))
    sm = json.load(open(sm_p, encoding="utf-8"))
    print("inputs: facts", sha(canon(facts)), "| train_S", sha(open(s_p, "rb").read()), "| candidates", sha(open(c_p, "rb").read()),
          "| anchor", sha(canon(anchor)))
    tm = defaultdict(list)
    for t in sm["templates"]:
        if t["set"] in ("TRAIN", "DEV", "Y"):
            tm[(t["relation"], t["set"], t["kind"])].append(t["text"])
    print("template kinds used:", sorted({k[1:] for k in tm}))
    byid = {f["fact_id"]: f for f in facts}
    L = [f for f in facts if f["exposure"] == "learned"]
    U = [f for f in facts if f["exposure"] == "unread"]

    def one(rel, st, kind):
        v = tm[(rel, st, kind)]
        assert len(v) == 1, (rel, st, kind)
        return v[0]

    F = [one(f["relation"], "TRAIN", "TRAIN").replace("{E}", f["entity"]).replace("{A}", f["answer"]) for f in L]
    Y = [one(f["relation"], "Y", "Y_ENTITY").replace("{E}", f["entity"]) for f in L] + \
        [one(f["relation"], "Y", "Y_ANSWER").replace("{A}", f["answer"]) for f in L]
    St = [r["text"] for r in S]
    DEV = [t.replace("{E}", f["entity"]) for f in facts for t in tm[(f["relation"], "DEV", "DEV")]]
    corp = {"train_F": F, "train_S": St, "train_Y": Y, "anchor": anchor}
    low = {k: "\n\x00\n".join(v).lower() for k, v in corp.items()}
    cnt = lambda k, s: low[k].count(s.lower())

    print("== split counts")
    cells = Counter((f["relation"], f["stratum"], f["exposure"]) for f in facts)
    print("facts", len(facts), "| learned", len(L), "| unread", len(U), "| per cell (learned, unread):",
          sorted({(cells[(r, s, "learned")], cells[(r, s, "unread")]) for (r, s, _) in cells}))
    print("TRAIN", len(F), "| S", len(St), "| Y", len(Y), "| DEV questions", len(DEV), "(learned", 2 * len(L), "unread", 2 * len(U), ")")
    ok &= (len(facts), len(L), len(U), len(F), len(St), len(Y), len(DEV)) == (160, 120, 40, 120, 120, 240, 320)
    ok &= all(cells[(r, s, "learned")] == 15 and cells[(r, s, "unread")] == 5 for (r, s, _) in cells) and len(cells) == 16
    lid, uid = {f["fact_id"] for f in L}, {f["fact_id"] for f in U}
    strings = [f[k] for f in facts for k in ("entity", "answer")]
    l5 = len(lid & uid) + (len(strings) - len(set(strings)))
    print("L5: learned & unread fact_id intersection", len(lid & uid), "| duplicate strings among", len(strings), ":",
          len(strings) - len(set(strings)), "-> limit 0:", "within" if l5 == 0 else "OVER")
    ok &= l5 == 0

    print("== four constraints: same relation, stratum, exposure and K_st = len(encode(' ' + c))")
    kst = {f["fact_id"]: len(enc(tok, " " + f["answer"])) for f in facts}
    groups = defaultdict(list)
    for f in facts:
        groups[(f["relation"], f["stratum"], f["exposure"], kst[f["fact_id"]])].append(f["fact_id"])
    per_cell = {(r, s, e): [k for k in groups if k[:3] == (r, s, e)] for (r, s, e) in cells}
    for c in sorted(cells):
        ks = per_cell[c]
        print("  cell %-28s K_st values %s | candidates per K_st %s" % ("/".join(c), [k[3] for k in ks], [len(groups[k]) for k in ks]))
    sizes = {f["fact_id"]: len(groups[(f["relation"], f["stratum"], f["exposure"], kst[f["fact_id"]])]) for f in facts}
    print("minimum candidates (incl. the true answer) over the 160 facts:", min(sizes.values()),
          "| cells with fewer than 4:", sorted({"/".join(k[:3]) for k, v in groups.items() if len(v) < 4}),
          "| cells split over more than one K_st:", [c for c, ks in per_cell.items() if len(ks) > 1])
    ok &= min(sizes.values()) >= 4 and all(len(ks) == 1 for ks in per_cell.values())
    bad = []
    for fid, cl in C.items():
        f = byid[fid]
        mem = [g for g in facts if g["answer"] in cl]
        if len(mem) != 4 or any((g["relation"], g["stratum"], g["exposure"]) != (f["relation"], f["stratum"], f["exposure"])
                                or kst[g["fact_id"]] != kst[fid] for g in mem) or f["answer"] not in cl:
            bad.append(fid)
    print("candidates.json lists violating any of the four constraints:", bad, "| lists:", len(C))
    ok &= not bad and sorted(C) == sorted(byid)

    print("== exposure matching (case-insensitive substring counts)")
    exp_bad = []
    for fid, cl in C.items():
        want = {"train_F": 1, "train_S": 1, "train_Y": 1, "anchor": 0} if byid[fid]["exposure"] == "learned" else \
               {"train_F": 0, "train_S": 0, "train_Y": 0, "anchor": 0}
        for c in cl:
            got = {k: cnt(k, c) for k in want}
            if got != want:
                exp_bad.append((fid, c, got))
    print("candidate occurrences differing from the 2.5 rule:", len(exp_bad), exp_bad[:5])
    ok &= not exp_bad
    tokbad = [r["fact_id"] for r in S if not contains_run(enc(tok, r["text"]), enc(tok, " " + byid[r["answer_fact_id"]]["answer"]))]
    print("S statements where the ids of ' ' + answer are not a contiguous run of the statement ids:", tokbad)
    ok &= not tokbad
    ent_bad = [f["fact_id"] for f in L if [cnt(k, f["entity"]) for k in ("train_F", "train_S", "train_Y")] != [1, 1, 1]]
    print("learned entities not exactly once in each of train_F, train_S, train_Y:", ent_bad)
    ok &= not ent_bad

    print("== leakage")
    l3a = {k: sum(cnt(k, f[x]) for f in U for x in ("entity", "answer")) for k in corp}
    l3b = sum(cnt("anchor", f["answer"]) for f in L)
    print("L3a unread entity/answer occurrences per corpus:", l3a, "-> limit 0:", "within" if not any(l3a.values()) else "OVER")
    print("L3b learned answers in anchor:", l3b, "-> limit 0:", "within" if l3b == 0 else "OVER")
    l4 = {k: sum(q in "\n".join(v) for q in DEV) for k, v in corp.items()}
    l4ci = {k: sum(low[k].count(q.lower()) for q in DEV) for k in corp}
    print("L4 (DEV part) verbatim DEV questions per corpus:", l4, "| case-insensitive:", l4ci, "-> limit 0:",
          "within" if not any(l4.values()) else "OVER")
    ok &= not any(l3a.values()) and l3b == 0 and not any(l4.values())
    return bool(ok)


if __name__ == "__main__":
    run(main)
