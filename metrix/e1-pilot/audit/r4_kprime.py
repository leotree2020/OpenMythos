"""R4-B: K' of s_ST (protocol section 5, TRAIN closed-book check), built from the protocol text:
prefix(f) = text of the TRAIN statement before the answer; c' = " " + c; K' = K_st(c) = len(encode(" " + c)).
For every learned fact f and every learned answer c of the same cell (15 x 120 = 1,800 pairs):
  (1) tokens of prefix(f) are a prefix of the tokens of prefix(f) + " " + c
  (2) the tokens after them equal encode(" " + c), and their number equals K_st(c)
  (3) K' takes a single value per cell
Also checked with the statement's final "." appended (the text the model is trained on).
TRAIN templates come from SPLIT_MANIFEST (set == TRAIN) and are compared with my transcription of protocol 2.4.
usage: python -I r4_kprime.py <tokenizer_dir> <my_facts_json> <split_manifest>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import defaultdict
from common import load_tok, enc, TRAIN_T

tok = load_tok(sys.argv[1])
facts = json.load(open(sys.argv[2], encoding="utf-8"))
sm = json.load(open(sys.argv[3], encoding="utf-8"))
tt = {t["relation"]: t["text"] for t in sm["templates"] if t["set"] == "TRAIN"}
print("TRAIN templates (SPLIT_MANIFEST):", json.dumps(tt))
print("equal to protocol 2.4 transcription:", tt == TRAIN_T)
assert all(v.endswith(" {A}.") and v.count("{A}") == 1 and v.count("{E}") == 1 for v in tt.values())

def prefix(f):
    return tt[f["relation"]].replace("{E}", f["entity"]).split(" {A}")[0]

learned = [f for f in facts if f["exposure"] == "learned"]
pairs = not_prefix = tail_ne = k_ne = 0
dot_not_prefix = dot_tail_ne = dot_last_ne = 0
kcell = defaultdict(set)
ex = None
dot_ids = enc(tok, ".")
for f in learned:
    p = prefix(f)
    pid = enc(tok, p)
    for c in (g["answer"] for g in learned if (g["relation"], g["stratum"]) == (f["relation"], f["stratum"])):
        pairs += 1
        cid = enc(tok, " " + c)
        full = enc(tok, p + " " + c)
        not_prefix += full[:len(pid)] != pid
        tail = full[len(pid):]
        tail_ne += tail != cid
        k_ne += len(tail) != len(cid)
        kcell[f"{f['relation']}/{f['stratum']}"].add(len(tail))
        fd = enc(tok, p + " " + c + ".")
        dot_not_prefix += fd[:len(pid)] != pid
        dot_tail_ne += fd[len(pid):len(fd) - len(dot_ids)] != cid
        dot_last_ne += fd[len(fd) - len(dot_ids):] != dot_ids
        if ex is None:
            ex = (f["fact_id"], p, c, full, tail)
print("learned facts:", len(learned), "| (fact, same-cell learned answer) pairs:", pairs)
print("pairs where tokens of prefix(f) are NOT a prefix of tokens of prefix(f)+' '+c:", not_prefix)
print("pairs where the following tokens != encode(' '+c):", tail_ne)
print("pairs where the number of following tokens != K_st(c):", k_ne)
print("K' per cell:", {k: sorted(v) for k, v in sorted(kcell.items())})
print("cells with more than one K':", sum(len(v) > 1 for v in kcell.values()))
print("with the final '.': prefix not a token prefix:", dot_not_prefix, "| answer span != encode(' '+c):", dot_tail_ne, "| last token != encode('.'):", dot_last_ne)
fid, p, c, full, tail = ex
print("example", fid, "prefix(f)", json.dumps(p), "c", json.dumps(c))
print("  ids", full, "scored", tail, tok.convert_ids_to_tokens(tail))
