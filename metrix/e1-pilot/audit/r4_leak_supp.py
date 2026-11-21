"""R4-D supplement (complements a1_facts.py): checks on corpora built by me from the protocol templates.
- L3a on the S-superset (every within-cell answer swap of the learned facts, a superset of any derangement)
- exposure matching for S: every learned answer occurs exactly once in ANY within-cell permutation corpus
  (checked line by line: count(a, line(f, c)) == [c == a] for every possible S line)
- L4 (DEV part), stricter form: case-insensitive substring of each DEV question in train_F, S-superset, train_Y and the anchor texts
- corpus sizes (TRAIN 120, S 120, Y 240, DEV 320) and the Y / F token ratio of protocol 2.6
DEV templates only; TEST templates are never instantiated.
usage: python -I r4_leak_supp.py <tokenizer_dir> <my_facts_json> <my_anchor_json> <split_manifest>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import defaultdict
from common import load_tok, enc, TRAIN_T

tok = load_tok(sys.argv[1])
facts = json.load(open(sys.argv[2], encoding="utf-8"))
anchor = json.load(open(sys.argv[3], encoding="utf-8"))
sm = json.load(open(sys.argv[4], encoding="utf-8"))
tm = defaultdict(list)
for t in sm["templates"]:
    if t["set"] in ("TRAIN", "DEV", "Y"):
        tm[(t["relation"], t["set"], t["kind"])].append(t["text"])
print("template kinds used:", sorted({k[1:] for k in tm}))
L = [f for f in facts if f["exposure"] == "learned"]
U = [f for f in facts if f["exposure"] == "unread"]
F = [TRAIN_T[f["relation"]].replace("{E}", f["entity"]).replace("{A}", f["answer"]) for f in L]
Y = [tm[(f["relation"], "Y", "Y_ENTITY")][0].replace("{E}", f["entity"]) for f in L] + \
    [tm[(f["relation"], "Y", "Y_ANSWER")][0].replace("{A}", f["answer"]) for f in L]
cell = defaultdict(list)
for f in L:
    cell[(f["relation"], f["stratum"])].append(f)
Ssup = []  # (line, answer used)
for f in L:
    for g in cell[(f["relation"], f["stratum"])]:
        Ssup.append((TRAIN_T[f["relation"]].replace("{E}", f["entity"]).replace("{A}", g["answer"]), g["answer"]))
DEV = [t.replace("{E}", f["entity"]) for f in facts for k, v in tm.items() if k[0] == f["relation"] and k[1] == "DEV" for t in v]
print("sizes: TRAIN", len(F), "| S (one line per learned fact)", len(L), "| S-superset lines incl. identity", len(Ssup),
      "| Y", len(Y), "| DEV", len(DEV), "(learned", 2 * len(L), "unread", 2 * len(U), ")")

lo = lambda s: s.lower()
s_blob = "\n\x00\n".join(lo(l) for l, _ in Ssup)
print("L3a S-superset: unread entity/answer hits:", sum(1 for f in U for s in (f["entity"], f["answer"]) if lo(s) in s_blob))
bad = []
for f in L:
    a = lo(f["answer"])
    for line, used in Ssup:
        if lo(line).count(a) != (used == f["answer"]):
            bad.append((f["answer"], line))
print("S exposure: (learned answer, S line) with count != [line uses that answer]:", len(bad), bad[:5])
bad_e = [(f["entity"], line) for f in L for line, _ in Ssup if lo(line).count(lo(f["entity"])) > 1]
print("S lines containing a learned entity more than once:", len(bad_e))

corp = {"train_F": [lo(x) for x in F], "S-superset": [lo(l) for l, _ in Ssup], "train_Y": [lo(x) for x in Y], "anchor": [lo(x) for x in anchor]}
for name, lines in corp.items():
    blob = "\n\x00\n".join(lines)
    print(f"L4 (DEV, case-insensitive) DEV questions found in {name}: {sum(1 for q in DEV if lo(q) in blob)}")

# protocol 2.6: Y / F token ratio (F 1,889, Y 2,260, 1.196); counted with and without the appended <|endoftext|>
fF = sum(len(enc(tok, x)) for x in F)
fY = sum(len(enc(tok, x)) for x in Y)
print(f"tokens without EOS: F {fF}, Y {fY}, Y/F {fY / fF:.3f} | with one EOS per sequence: F {fF + len(F)}, Y {fY + len(Y)}, Y/F {(fY + len(Y)) / (fF + len(F)):.3f}")
