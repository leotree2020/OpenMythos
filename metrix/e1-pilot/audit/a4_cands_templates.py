"""A4: candidate feasibility (relation, stratum, exposure, scored-token count = len(encode(' '+c)) per sec. 5),
template normalization / hashes / L1 / L2, Y_ANSWER answer split check."""
import json, re, sys
from collections import defaultdict
from itertools import combinations
from common import *

tok = load_tok(sys.argv[1])
facts = json.load(open(sys.argv[2]))
sm = json.load(open(sys.argv[3]))
pools = defaultdict(list)
for f in facts:
    pools[(f["relation"], f["stratum"], f["exposure"], len(enc(tok, " " + f["answer"])))].append(f["answer"])
grp = defaultdict(set)
for k in pools: grp[k[:3]].add(k[3])
print("pools:", len(pools))
for k in sorted(pools): print("  ", k, "size", len(pools[k]), "distractors available", len(pools[k]) - 1)
print("(rel,stratum,exposure) groups split across >1 token count:", [k for k, v in grp.items() if len(v) > 1])
per_fact = {f["fact_id"]: len(pools[(f["relation"], f["stratum"], f["exposure"], len(enc(tok, " " + f["answer"])))]) for f in facts}
print("facts:", len(per_fact), "min pool size over facts:", min(per_fact.values()), "max:", max(per_fact.values()))
print("pools with < 4 answers:", [k for k, v in pools.items() if len(v) < 4])
print("facts with < 3 distractors:", [i for i, n in per_fact.items() if n - 1 < 3])

# templates
def norm(t):
    t = t.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    t = re.sub(r"[^a-z0-9<> ]", " ", t)
    return re.sub(r" +", " ", t).strip()
bad = 0
for t in sm["templates"]:
    n = norm(t["text"]); h = sha(n.encode("utf-8"))
    if n != t["normalized"] or h != t["normalized_sha256"]:
        bad += 1; print("  template mismatch", t["template_id"], repr(n), h)
print("templates:", len(sm["templates"]), "normalized/hash mismatches vs manifest:", bad)
hs = sorted(sha(norm(t["text"]).encode()) for t in sm["templates"])
tss = sha("\n".join(hs).encode("utf-8"))
print("template_set_sha256 recomputed:", tss, "manifest:", sm["template_freeze"]["template_set_sha256"], "match:", tss == sm["template_freeze"]["template_set_sha256"])
# compare template texts with protocol section 2.4 table
proto = open(sys.argv[4], encoding="utf-8").read()
ptab = {}
for m in re.finditer(r"^\| (capital|currency|founder|river) \| (TRAIN|DEV|TEST|Y) \| (.+) \|$", proto, re.M):
    ptab[(m.group(1), m.group(2))] = [x.strip() for x in m.group(3).split(" / ")]
mtab = defaultdict(list)
for t in sm["templates"]: mtab[(t["relation"], t["set"])].append(t["text"])
print("protocol 2.4 table == manifest template texts:", ptab == dict(mtab), "(", len(ptab), "rows )")
sets = defaultdict(set)
for t in sm["templates"]: sets[t["set"]].add(sha(norm(t["text"]).encode()))
dup = [(a, b, sets[a] & sets[b]) for a, b in combinations(sorted(sets), 2) if sets[a] & sets[b]]
print("L1 cross-set duplicate normalized hashes:", dup)
def g4(t):
    w = norm(t).split(); return {tuple(w[i:i + 4]) for i in range(len(w) - 3)}
best = (0.0, None)
for a, b in combinations(sm["templates"], 2):
    if a["set"] == b["set"]: continue
    A, B = g4(a["text"]), g4(b["text"])
    j = len(A & B) / len(A | B) if A | B else 0.0
    if j > best[0]: best = (j, (a["template_id"], b["template_id"]))
print("L2 max Jaccard word-4gram across sets:", best, "limit 0.25, within:", best[0] <= 0.25)
# Y_ANSWER: answer span ids equal to ' '+answer ids
yt = {t["relation"]: t["text"] for t in sm["templates"] if t["kind"] == "Y_ANSWER"}
ybad = 0
for f in facts:
    if f["exposure"] != "learned": continue
    s = yt[f["relation"]].replace("{A}", f["answer"]); pre = s.split(" " + f["answer"])[0]
    si, pi = enc(tok, s), enc(tok, pre)
    ybad += not (si[:len(pi)] == pi and si[len(pi):len(si) - 1] == enc(tok, " " + f["answer"]) and si[-1:] == enc(tok, "."))
print("Y_ANSWER sentences whose answer ids differ from encode(' '+answer):", ybad)
