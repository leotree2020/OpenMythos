"""A1: facts hash vs protocol, structure, split counts, L5, L3a/L3b vs anchor texts."""
import json, re, sys
from collections import Counter
from common import *

facts_path, anchor_path, sm_path = sys.argv[1], sys.argv[2], sys.argv[3]
raw = open(facts_path, "rb").read()
facts = json.loads(raw)
print("file byte sha256      :", sha(raw))
print("facts canonical sha256:", sha(canon(facts)))
print("protocol value        :", FACTS_SHA_PROTOCOL)
print("canonical match:", sha(canon(facts)) == FACTS_SHA_PROTOCOL)
print("fields:", sorted(Counter(tuple(sorted(f)) for f in facts).items()))
print("n facts:", len(facts), Counter(f["exposure"] for f in facts))
cells = Counter((f["relation"], f["stratum"], f["exposure"]) for f in facts)
for k in sorted(cells): print("  cell", k, cells[k])
# fact_id format and ordering
bad_id = []
order = []
for f in facts:
    m = re.fullmatch(r"E1P-([LU])-(capital|currency|founder|river)-(nat|rnd)-(\d\d)", f["fact_id"])
    if not m or m.group(1) != {"learned": "L", "unread": "U"}[f["exposure"]] or m.group(2) != f["relation"] \
       or m.group(3) != {"natural": "nat", "random": "rnd"}[f["stratum"]]:
        bad_id.append(f["fact_id"])
print("fact_id format/field mismatches:", len(bad_id), bad_id[:5])
exp_order = []
for r in RELATIONS:
    for s in STRATA:
        ab = {"natural": "nat", "random": "rnd"}[s]
        exp_order += [f"E1P-L-{r}-{ab}-{i:02d}" for i in range(1, 16)] + [f"E1P-U-{r}-{ab}-{i:02d}" for i in range(1, 6)]
print("fact_id order equals generation order rule:", [f["fact_id"] for f in facts] == exp_order)
L = {f["fact_id"] for f in facts if f["exposure"] == "learned"}
U = {f["fact_id"] for f in facts if f["exposure"] == "unread"}
print("L5 learned & unread fact_id intersection:", len(L & U), "; distinct fact_ids:", len(L | U))
strings = [f["entity"] for f in facts] + [f["answer"] for f in facts]
print("L5 strings:", len(strings), "distinct:", len(set(strings)), "duplicates:", len(strings) - len(set(strings)))
# form rules
def form_ok(s, st):
    if st == "natural":
        return re.fullmatch(r"[A-Z][a-z]+", s) is not None and 4 <= len(s) <= 10
    return re.fullmatch(r"[BCDFGHJKLMNPQRSTVWXZ]{3,5}-[2-9]{2}", s) is not None
print("form-rule violations:", [s for f in facts for s in (f["entity"], f["answer"]) if not form_ok(s, f["stratum"])])
# DEV split counts (instantiated from DEV templates only; TEST templates NOT used)
sm = json.load(open(sm_path))
dev_t = {}
for t in sm["templates"]:
    if t["set"] == "DEV":
        dev_t.setdefault(t["relation"], []).append(t["text"])
dev = [(f["fact_id"], t.replace("{E}", f["entity"])) for f in facts for t in dev_t[f["relation"]]]
print("DEV templates per relation:", {k: len(v) for k, v in dev_t.items()})
print("DEV questions:", len(dev), "(protocol: 160 facts x 2 = 320)", "learned:", sum(1 for i, _ in dev if i in L), "unread:", sum(1 for i, _ in dev if i in U))
print("TRAIN statements (learned only):", len(L), "(protocol 120)")
# L3a / L3b vs anchor texts (case-insensitive substring)
anchor = json.load(open(anchor_path))
texts = anchor["texts"] if isinstance(anchor, dict) else anchor
print("anchor texts:", len(texts), "canonical sha256 of texts list:", sha(canon(texts)))
blob = "\n\x00\n".join(t.lower() for t in texts)
l3a = [(f["fact_id"], s) for f in facts if f["exposure"] == "unread" for s in (f["entity"], f["answer"]) if s.lower() in blob]
l3b = [(f["fact_id"], f["answer"]) for f in facts if f["exposure"] == "learned" if f["answer"].lower() in blob]
print("L3a (anchor part) unread entity/answer hits:", len(l3a), l3a)
print("L3b learned answer hits in anchor:", len(l3b), l3b)
# also names of any role in anchor (generation anchor rule)
print("any of 320 strings in anchor:", sum(1 for s in strings if s.lower() in blob))
# L3a on train_F / train_Y corpora built from protocol templates (S: any permutation within cell keeps the same strings)
ytm = {(t["relation"], t["kind"]): t["text"] for t in sm["templates"] if t["set"] == "Y"}
F = [TRAIN_T[f["relation"]].replace("{E}", f["entity"]).replace("{A}", f["answer"]) for f in facts if f["exposure"] == "learned"]
Y = [ytm[(f["relation"], "Y_ENTITY")].replace("{E}", f["entity"]) for f in facts if f["exposure"] == "learned"] + \
    [ytm[(f["relation"], "Y_ANSWER")].replace("{A}", f["answer"]) for f in facts if f["exposure"] == "learned"]
corp = "\n\x00\n".join(x.lower() for x in F + Y)
print("L3a (train_F/train_Y part) unread hits:", sum(1 for f in facts if f["exposure"] == "unread" for s in (f["entity"], f["answer"]) if s.lower() in corp))
# exposure: each learned answer occurs exactly once in F and in Y (case-insensitive substring count)
def cnt(lines, s):
    return sum(l.lower().count(s.lower()) for l in lines)
print("learned answers with count != 1 in train_F:", [f["answer"] for f in facts if f["exposure"] == "learned" and cnt(F, f["answer"]) != 1])
print("learned answers with count != 1 in train_Y:", [f["answer"] for f in facts if f["exposure"] == "learned" and cnt(Y, f["answer"]) != 1])
# L4 (DEV part): DEV questions verbatim in F, Y, and in every possible S statement (all within-cell answer swaps; superset of any derangement)
S_all = []
for f in facts:
    if f["exposure"] != "learned": continue
    for g in facts:
        if g["exposure"] == "learned" and (g["relation"], g["stratum"]) == (f["relation"], f["stratum"]) and g is not f:
            S_all.append(TRAIN_T[f["relation"]].replace("{E}", f["entity"]).replace("{A}", g["answer"]))
allc = "\n\x00\n".join(F + Y + S_all)
print("L4 (DEV) verbatim DEV questions in F/Y/S-superset:", sum(1 for _, q in dev if q in allc), "; S-superset lines:", len(S_all))
