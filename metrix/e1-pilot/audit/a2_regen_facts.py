"""A2: independent regeneration of the 160 facts from protocol section 2.2 text only."""
import json, sys
from collections import Counter
from common import *

tok = load_tok(sys.argv[1])
anchor = json.load(open(sys.argv[2]))
texts = anchor["texts"] if isinstance(anchor, dict) else anchor
ablob = "\n\x00\n".join(t.lower() for t in texts)
DATA_SEED = 20261110
ONS = "b d f g k l m n p r s t v z br dr kr tr sh th".split()
NUC = "a e i o u ae ia ou".split()
COD = ["", "", "n", "r", "l", "s", "th", "nd"]
LET = "BCDFGHJKLMNPQRSTVWXZ"
DIG = "23456789"

def draw(rng, st):
    if st == "natural":
        n = 2 if rng.random() < 0.5 else 3
        s = "".join(rng.choice(ONS) + rng.choice(NUC) + rng.choice(COD) for _ in range(n))
        return s[0].upper() + s[1:]
    u = rng.random()
    L = 3 if u < 0.25 else 4 if u < 0.75 else 5
    return "".join(rng.choice(LET) for _ in range(L)) + "-" + "".join(rng.choice(DIG) for _ in range(2))

def form(s, st):
    if st == "natural":
        return 4 <= len(s) <= 10 and len(enc(tok, " " + s)) > 1
    return 6 <= len(s) <= 8

def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def seg(s):
    return s.split("-")[0]

def conflict(s, st, acc):
    for a in acc:
        if st == "natural":
            if s.lower() == a.lower() or s[:4] == a[:4] or lev(s.lower(), a.lower()) <= 1:
                return True
        else:
            if s == a or seg(s) == seg(a) or (len(s) == len(a) and sum(x != y for x, y in zip(s, a)) <= 1):
                return True
    return False

K = lambda s: (len(enc(tok, " " + s)), len(enc(tok, s)))
accepted = []
facts = []
log = []
for r in RELATIONS:
    for st in STRATA:
        rng = rng_rule(DATA_SEED, f"names:{r}:{st}:entity")
        ents, n = [], 0
        while len(ents) < 20:
            n += 1; assert n <= 20000, "IMPLEMENTATION_FAIL"
            s = draw(rng, st)
            if form(s, st) and not conflict(s, st, accepted) and s.lower() not in ablob:
                ents.append(s); accepted.append(s)
        rng = rng_rule(DATA_SEED, f"names:{r}:{st}:answer")
        stats, n = Counter(), 0
        while sum(stats.values()) < 400:
            n += 1; assert n <= 20000
            s = draw(rng, st)
            if form(s, st):
                stats[K(s)] += 1
        target = sorted(stats.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        rng = rng_rule(DATA_SEED, f"names:{r}:{st}:answer")
        ans, n = [], 0
        while len(ans) < 20:
            n += 1; assert n <= 20000
            s = draw(rng, st)
            if form(s, st) and K(s) == target and not conflict(s, st, accepted) and s.lower() not in ablob:
                ans.append(s); accepted.append(s)
        ab = {"natural": "nat", "random": "rnd"}[st]
        for i in range(20):
            lu, idx = ("L", i + 1) if i < 15 else ("U", i - 14)
            facts.append({"fact_id": f"E1P-{lu}-{r}-{ab}-{idx:02d}", "exposure": "learned" if lu == "L" else "unread",
                          "relation": r, "stratum": st, "entity": ents[i], "answer": ans[i]})
        log.append((r, st, target, dict(stats.most_common(3))))
for x in log: print("cell", x[0], x[1], "target (K_st,K_qa) =", x[2], "top stats", x[3])
h = sha(canon(facts))
print("regenerated facts canonical sha256:", h)
print("protocol value                    :", FACTS_SHA_PROTOCOL)
print("match:", h == FACTS_SHA_PROTOCOL)
given = json.load(open(sys.argv[3]))
print("equal to Executor data file:", given == facts)
