"""A3: round-3 candidate scoring input built from protocol text (sec. 0 row 'candidate scoring input', sec. 5 s_QA).
chat(q) = chat template, single user turn, add_generation_prompt=True, enable_thinking=False, no system prompt.
scoring text = chat(q) + "The answer is" + " " + c ; scored tokens = tokens of " " + c ; nothing after c.
DEV templates only. TEST templates are never instantiated."""
import json, sys, hashlib, os
from collections import defaultdict
from common import *

tokdir, facts_path, sm_path = sys.argv[1:4]
for fn in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"):
    print(fn, "sha256", sha(open(os.path.join(tokdir, fn), "rb").read()))
tok = load_tok(tokdir)
print("tokenizer class", type(tok).__name__, "vocab", len(tok))
facts = json.load(open(facts_path))
sm = json.load(open(sm_path))
dev_t = defaultdict(list)
for t in sm["templates"]:
    if t["set"] == "DEV":
        dev_t[t["relation"]].append(t["text"])
assert all(len(v) == 2 for v in dev_t.values())

def chat(q):
    return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)

PFX = "The answer is"
print("chat('Q?') =", json.dumps(chat("Q?")))
print("chat('Q?') with enable_thinking=True =", json.dumps(tok.apply_chat_template([{"role": "user", "content": "Q?"}], tokenize=False, add_generation_prompt=True, enable_thinking=True)))

def scored_ids(q, c):
    prefix = chat(q) + PFX
    full = prefix + " " + c
    pi, fi = enc(tok, prefix), enc(tok, full)
    aligned = fi[:len(pi)] == pi
    return aligned, fi[len(pi):], fi

def train_answer_ids(f):
    st = TRAIN_T[f["relation"]].replace("{E}", f["entity"]).replace("{A}", f["answer"])
    pre, post = st.split(" " + f["answer"])
    assert post == "."
    si, pi, ti = enc(tok, st), enc(tok, pre), enc(tok, ".")
    aligned = si[:len(pi)] == pi and si[-len(ti):] == ti
    return aligned, si[len(pi):len(si) - len(ti)], st

n_pairs = mism = misalign_q = misalign_st = mism_plain = 0
ex = None
for f in facts:
    if f["exposure"] != "learned":
        continue
    a_st, tr_ids, st = train_answer_ids(f)
    misalign_st += not a_st
    for t in dev_t[f["relation"]]:
        q = t.replace("{E}", f["entity"])
        a_q, sc, full = scored_ids(q, f["answer"])
        n_pairs += 1
        misalign_q += not a_q
        mism += sc != tr_ids
        mism_plain += sc != enc(tok, " " + f["answer"])
        if ex is None:
            ex = (f, st, tr_ids, q, full, sc)
print("learned facts x DEV questions compared:", n_pairs)
print("TRAIN statements where ' '+answer is not a token-aligned span:", misalign_st)
print("scoring inputs where chat(q)+'The answer is' is not a token prefix of the full text:", misalign_q)
print("MISMATCHES scored ids vs TRAIN-statement answer ids:", mism)
print("mismatches scored ids vs encode(' '+answer):", mism_plain)
f, st, tr_ids, q, full, sc = ex
print("example", f["fact_id"], "| statement", json.dumps(st), "| TRAIN ans ids", tr_ids, tok.convert_ids_to_tokens(tr_ids))
print("  question", json.dumps(q), "| full ids", full)
print("  tokens", tok.convert_ids_to_tokens(full))
print("  scored ids", sc, tok.convert_ids_to_tokens(sc))

# K constancy: every candidate in every pool (all 160 answers, as candidates of every fact of the same
# relation/stratum/exposure), on both DEV questions of that fact
cell_K = defaultdict(set)
k_ne_kst = 0
for f in facts:
    pool = [g["answer"] for g in facts if (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])]
    for t in dev_t[f["relation"]]:
        q = t.replace("{E}", f["entity"])
        for c in pool:
            a, sc, _ = scored_ids(q, c)
            assert a
            cell_K[(f["relation"], f["stratum"])].add(len(sc))
            k_ne_kst += len(sc) != len(enc(tok, " " + c))
print("scored count != K_st (all facts x DEV q x pool candidates):", k_ne_kst)
for k in sorted(cell_K):
    print("  cell", k, "scored-token counts:", sorted(cell_K[k]))
print("cells with >1 scored-token count:", sum(len(v) > 1 for v in cell_K.values()))
