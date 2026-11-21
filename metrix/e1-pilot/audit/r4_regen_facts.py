"""R4-A2: regenerate the 160 facts from the text of protocol section 2.2 only (constants transcribed from the protocol),
using the anchor texts I rebuilt myself (r4_anchor.py). Writes my facts file (canonical bytes). The Executor's facts
file is read only at the very end, for the final comparison.
usage: python -I r4_regen_facts.py <tokenizer_dir> <my_anchor_json> <out_facts_json> [executor_facts_json]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter
from common import sha, canon, rng_rule, load_tok, enc, RELATIONS, STRATA, FACTS_SHA_PROTOCOL

tokdir, anchor_path, out_path = sys.argv[1:4]
tok = load_tok(tokdir)
texts = json.load(open(anchor_path, encoding="utf-8"))
print("anchor texts:", len(texts), "canonical sha256", sha(canon(texts)))
ablob = "\n\x00\n".join(t.lower() for t in texts)

# protocol 2.2 constants
DATA_SEED = 20261110
ONSETS = "b d f g k l m n p r s t v z br dr kr tr sh th".split()
NUCLEI = "a e i o u ae ia ou".split()
CODAS = ["", "", "n", "r", "l", "s", "th", "nd"]
LETTERS = "BCDFGHJKLMNPQRSTVWXZ"
DIGITS = "23456789"
CAP = 20000


def draw(rng, st):
    if st == "natural":
        n = 2 if rng.random() < 0.5 else 3
        s = "".join(rng.choice(ONSETS) + rng.choice(NUCLEI) + rng.choice(CODAS) for _ in range(n))
        return s[:1].upper() + s[1:]
    u = rng.random()
    L = 3 if u < 0.25 else 4 if u < 0.75 else 5
    return "".join(rng.choice(LETTERS) for _ in range(L)) + "-" + "".join(rng.choice(DIGITS) for _ in range(2))


def form_ok(s, st):
    if st == "natural":
        return 4 <= len(s) <= 10 and len(enc(tok, " " + s)) > 1
    return 6 <= len(s) <= 8


def levenshtein(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (x != y)))
        row = new
    return row[-1]


def letter_block(s):
    return s.split("-", 1)[0]


def rejected(s, st, accepted):
    for a in accepted:
        if st == "natural":
            if s.lower() == a.lower() or s[:4] == a[:4] or levenshtein(s.lower(), a.lower()) <= 1:
                return True
        else:
            if s == a or letter_block(s) == letter_block(a) or (len(s) == len(a) and sum(x != y for x, y in zip(s, a)) <= 1):
                return True
    return False


def kpair(s):
    return (len(enc(tok, " " + s)), len(enc(tok, s)))


accepted, facts = [], []
anchor_rejections = 0
for rel in RELATIONS:
    for st in STRATA:
        # entities
        rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:entity")
        ents, nd = [], 0
        while len(ents) < 20:
            nd += 1
            assert nd <= CAP, "IMPLEMENTATION_FAIL entity stream"
            s = draw(rng, st)
            if form_ok(s, st) and not rejected(s, st, accepted):
                if s.lower() in ablob:
                    anchor_rejections += 1
                    continue
                ents.append(s); accepted.append(s)
        ent_draws = nd
        # answers: survey of the first 400 form-valid draws
        rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")
        survey, nd = Counter(), 0
        while sum(survey.values()) < 400:
            nd += 1
            assert nd <= CAP, "IMPLEMENTATION_FAIL survey"
            s = draw(rng, st)
            if form_ok(s, st):
                survey[kpair(s)] += 1
        survey_draws = nd
        top = max(survey.values())
        target = min(k for k, v in survey.items() if v == top)
        # answers: restart the stream, accept
        rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")
        ans, nd = [], 0
        while len(ans) < 20:
            nd += 1
            assert nd <= CAP, "IMPLEMENTATION_FAIL answer stream"
            s = draw(rng, st)
            if form_ok(s, st) and kpair(s) == target and not rejected(s, st, accepted):
                if s.lower() in ablob:
                    anchor_rejections += 1
                    continue
                ans.append(s); accepted.append(s)
        ab = "nat" if st == "natural" else "rnd"
        for i in range(20):
            learned = i < 15
            facts.append({"fact_id": f"E1P-{'L' if learned else 'U'}-{rel}-{ab}-{(i + 1 if learned else i - 14):02d}",
                          "exposure": "learned" if learned else "unread", "relation": rel, "stratum": st,
                          "entity": ents[i], "answer": ans[i]})
        print(f"cell {rel}/{st}: entity_draws {ent_draws}, survey_draws {survey_draws}, target (K_st,K_qa) {target}, "
              f"survey top3 {survey.most_common(3)}, answer_draws {nd}")
print("anchor-rule rejections:", anchor_rejections)
print("facts:", len(facts), Counter(f["exposure"] for f in facts), "| distinct strings:", len({x for f in facts for x in (f['entity'], f['answer'])}))
b = canon(facts)
h = sha(b)
print("regenerated facts canonical sha256:", h)
print("protocol section 2.2 value         :", FACTS_SHA_PROTOCOL)
print("MATCH:", h == FACTS_SHA_PROTOCOL)
with open(out_path, "wb") as fh:
    fh.write(b)
print("wrote", out_path, "(canonical bytes; byte sha256 = canonical sha256)")
if len(sys.argv) > 4:
    raw = open(sys.argv[4], "rb").read()
    ex = json.loads(raw)
    print("FINAL COMPARISON with Executor facts file: equal content =", ex == facts,
          "| its byte sha256", sha(raw), "| its canonical sha256", sha(canon(ex)))
