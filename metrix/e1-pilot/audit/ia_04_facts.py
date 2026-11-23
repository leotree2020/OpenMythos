"""IA-4: the 160 facts (protocol 2.1 / 2.2, DATA_MANIFEST name_generation at the freeze commit), regenerated from
DATA_SEED with the anchor rule applied against the 512 anchor texts built by ia_03_anchor.py.
Frozen value: canonical SHA-256 of the JSON list of the 160 facts (fields fact_id, exposure, relation, stratum,
entity, answer) in generation order (protocol 2.2 "复现" and "fact 哈希的比对方法").
Constants are transcribed from the protocol text and compared with the freeze-commit manifest.
Writes <out_dir>/facts.json (the list) and <out_dir>/facts_k.json ({fact_id: [K_st, K_qa]}).
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ia_04_facts.py <repo_root> <qwen_tok_dir> <out_dir>   (reads <out_dir>/anchor.json)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter
from ia_common import RELS, STRATA, sha, canon, rng_rule, frozen_json, load_qwen, enc, run

DATA_SEED = 20261110
ONSETS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "br", "dr", "kr", "tr", "sh", "th"]
NUCLEI = ["a", "e", "i", "o", "u", "ae", "ia", "ou"]
CODAS = ["", "", "n", "r", "l", "s", "th", "nd"]
LETTERS, DIGITS = "BCDFGHJKLMNPQRSTVWXZ", "23456789"
MAX_DRAWS = 20000
FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]


def edit_distance_le1(a, b):
    """True iff Levenshtein(a, b) <= 1."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(x != y for x, y in zip(a, b)) == 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


class Gen:
    def __init__(self, tok, anchor_texts):
        self.tok = tok
        self.anchor_lower = [t.lower() for t in anchor_texts]
        self.accepted = []
        self.anchor_rejections = 0

    def draw(self, rng, stratum):
        if stratum == "natural":
            n = 2 if rng.random() < 0.5 else 3
            s = "".join(rng.choice(ONSETS) + rng.choice(NUCLEI) + rng.choice(CODAS) for _ in range(n))
            return s[0].upper() + s[1:]
        u = rng.random()
        L = 3 if u < 0.25 else 4 if u < 0.75 else 5
        return "".join(rng.choice(LETTERS) for _ in range(L)) + "-" + "".join(rng.choice(DIGITS) for _ in range(2))

    def form_ok(self, s, stratum):
        if stratum == "natural":
            return 4 <= len(s) <= 10 and len(enc(self.tok, " " + s)) > 1
        return 6 <= len(s) <= 8

    def conflicts(self, s, stratum):
        for a in self.accepted:
            if stratum == "natural":
                if s.lower() == a.lower() or s[:4] == a[:4] or edit_distance_le1(s.lower(), a.lower()):
                    return True
            else:
                block_s = s.split("-")[0] if "-" in s else s
                block_a = a.split("-")[0] if "-" in a else a
                if s == a or block_s == block_a or (len(s) == len(a) and sum(x != y for x, y in zip(s, a)) <= 1):
                    return True
        return False

    def in_anchor(self, s):
        q = s.lower()
        return any(q in t for t in self.anchor_lower)

    def k(self, s):
        return (len(enc(self.tok, " " + s)), len(enc(self.tok, s)))

    def accept_if_ok(self, s, stratum):
        if self.conflicts(s, stratum):
            return False
        if self.in_anchor(s):
            self.anchor_rejections += 1
            return False
        self.accepted.append(s)
        return True


def generate(tok, anchor_texts):
    g = Gen(tok, anchor_texts)
    facts, log = [], []
    for rel in RELS:
        for st in STRATA:
            rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:entity")
            ents, nd = [], 0
            while len(ents) < 20:
                nd += 1
                if nd > MAX_DRAWS:
                    raise RuntimeError("IMPLEMENTATION_FAIL entity stream exhausted")
                s = g.draw(rng, st)
                if g.form_ok(s, st) and g.accept_if_ok(s, st):
                    ents.append(s)
            ent_draws = nd
            rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")
            survey, nd, used = Counter(), 0, 0
            while used < 400:
                nd += 1
                if nd > MAX_DRAWS:
                    raise RuntimeError("IMPLEMENTATION_FAIL survey")
                s = g.draw(rng, st)
                if g.form_ok(s, st):
                    used += 1
                    survey[g.k(s)] += 1
            best = max(survey.values())
            target = sorted(p for p, c in survey.items() if c == best)[0]
            rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")     # restart the answer stream
            ans, nd = [], 0
            while len(ans) < 20:
                nd += 1
                if nd > MAX_DRAWS:
                    raise RuntimeError("IMPLEMENTATION_FAIL answer stream exhausted")
                s = g.draw(rng, st)
                if g.form_ok(s, st) and g.k(s) == target and g.accept_if_ok(s, st):
                    ans.append(s)
            short = {"natural": "nat", "random": "rnd"}[st]
            for i in range(20):
                learned = i < 15
                idx = i + 1 if learned else i - 14
                facts.append({"fact_id": f"E1P-{'L' if learned else 'U'}-{rel}-{short}-{idx:02d}",
                              "exposure": "learned" if learned else "unread", "relation": rel, "stratum": st,
                              "entity": ents[i], "answer": ans[i]})
            log.append(f"{rel}/{st}: entity draws {ent_draws} | survey top pairs {survey.most_common(3)} -> target "
                       f"{target} | answer draws {nd}")
    return facts, log, g


def main():
    repo, qdir, out_dir = sys.argv[1:4]
    ok = True
    dm = frozen_json(repo, "DATA_MANIFEST.json")
    ng = dm["name_generation"]
    for name, got, want in (("seeds.DATA_SEED", dm["seeds"]["DATA_SEED"], DATA_SEED),
                            ("facts.relations", dm["facts"]["relations"], RELS), ("facts.strata", dm["facts"]["strata"], STRATA),
                            ("natural.onsets", ng["natural"]["onsets"], ONSETS), ("natural.nuclei", ng["natural"]["nuclei"], NUCLEI),
                            ("natural.codas", ng["natural"]["codas"], CODAS), ("natural.length_chars", ng["natural"]["length_chars"], [4, 10]),
                            ("random.letters", ng["random"]["letters"], LETTERS), ("random.digits", ng["random"]["digits"], DIGITS),
                            ("random.length_chars", ng["random"]["length_chars"], [6, 8]),
                            ("max_draws_per_stream", ng["max_draws_per_stream"], MAX_DRAWS),
                            ("expected_facts_fields", ng["expected_facts_fields"], FIELDS)):
        print(f"manifest {name} == transcribed protocol value: {got == want}")
        ok &= got == want
    anchor = json.load(open(os.path.join(out_dir, "anchor.json"), encoding="utf-8"))
    texts = [a["text"] for a in anchor]
    ah = sha(canon(texts))
    print("anchor texts from ia_03:", len(texts), "| canonical sha256", ah, "| == frozen:", ah == dm["anchor_text"]["decoded_texts_canonical_sha256"])
    ok &= ah == dm["anchor_text"]["decoded_texts_canonical_sha256"]
    tok = load_qwen(qdir)
    facts, log, g = generate(tok, texts)
    for line in log:
        print("  cell", line)
    print("anchor-rule rejections:", g.anchor_rejections)
    strings = [x for f in facts for x in (f["entity"], f["answer"])]
    print("facts", len(facts), "| exposure", dict(Counter(f["exposure"] for f in facts)), "| distinct strings", len(set(strings)),
          "| distinct lowercased", len({s.lower() for s in strings}))
    ok &= len(facts) == 160 and len(set(strings)) == 320
    h = sha(canon(facts))
    exp = ng["expected_facts_canonical_sha256"]
    print(f"regenerated facts canonical sha256 {h} | frozen {exp} | MATCH {h == exp}")
    print(f"AUDIT_VALUE facts_canonical_sha256 {h}")
    ok &= h == exp
    kk = {f["fact_id"]: list(g.k(f["answer"])) for f in facts}
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "facts.json"), "wb").write(canon(facts))
    open(os.path.join(out_dir, "facts_k.json"), "wb").write(canon(kk))
    print("first fact", json.dumps(facts[0]), "| last fact", json.dumps(facts[-1]))
    print("wrote facts.json and facts_k.json to", out_dir)
    return bool(ok)


run(main)
