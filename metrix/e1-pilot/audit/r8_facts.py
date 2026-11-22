"""R8-2: regenerate the 160 facts (protocol 2.2) and compare their canonical SHA-256 with the freeze commit
(DATA_MANIFEST.json name_generation.expected_facts_canonical_sha256 and the 2.2 "复现" sentence of the protocol).
Data Auditor's own script (generation logic is the auditor's own r4_regen_facts.py, rewritten as a function here);
no Executor code is imported, called or copied (not reports/round2/names.py / gen_facts.py).
Exceptions -> RESULT: FAIL (r6_guard).

Constants are transcribed from the protocol text (section 2.2) and cross-checked against the freeze-commit manifest
(name_generation.*, seeds.*, facts.*). The anchor rule uses the 512 texts that r8_anchor.py rebuilt from the
parquet (their hash is checked again here). The tokenizer directory holds only the four tokenizer files.
Writes <out_dir>/facts.json (canonical bytes) for r8_s_cands.py. Prints AUDIT_VALUE lines.
PASS iff the regenerated facts hash equals the freeze-commit manifest value (== protocol 2.2 value) and the
manifest constants equal the transcribed ones.
usage: python -I r8_facts.py <repo_root> <commit> <qwen_tok_dir> <anchor_texts.json> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess
from collections import Counter
from common import sha, canon, rng_rule, load_tok, enc
from r6_guard import run

# protocol 2.2 / section 0, transcribed
DATA_SEED = 20261110
RELS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
ONSETS = "b d f g k l m n p r s t v z br dr kr tr sh th".split()
NUCLEI = "a e i o u ae ia ou".split()
CODAS = ["", "", "n", "r", "l", "s", "th", "nd"]
LETTERS = "BCDFGHJKLMNPQRSTVWXZ"
DIGITS = "23456789"
CAP = 20000


def git_blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], capture_output=True, check=True).stdout


def levenshtein(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (x != y)))
        row = new
    return row[-1]


def generate(tok, texts):
    ablob = "\n\x00\n".join(t.lower() for t in texts)

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

    def rejected(s, st, accepted):
        for a in accepted:
            if st == "natural":
                if s.lower() == a.lower() or s[:4] == a[:4] or levenshtein(s.lower(), a.lower()) <= 1:
                    return True
            else:
                if s == a or s.split("-", 1)[0] == a.split("-", 1)[0] or \
                        (len(s) == len(a) and sum(x != y for x, y in zip(s, a)) <= 1):
                    return True
        return False

    def kpair(s):
        return (len(enc(tok, " " + s)), len(enc(tok, s)))

    accepted, facts, log, anchor_rej = [], [], [], 0
    for rel in RELS:
        for st in STRATA:
            rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:entity")
            ents, nd = [], 0
            while len(ents) < 20:
                nd += 1
                assert nd <= CAP, "IMPLEMENTATION_FAIL entity stream"
                s = draw(rng, st)
                if form_ok(s, st) and not rejected(s, st, accepted):
                    if s.lower() in ablob:
                        anchor_rej += 1
                        continue
                    ents.append(s); accepted.append(s)
            ent_draws = nd
            rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")
            survey, nd = Counter(), 0
            while sum(survey.values()) < 400:
                nd += 1
                assert nd <= CAP, "IMPLEMENTATION_FAIL survey"
                s = draw(rng, st)
                if form_ok(s, st):
                    survey[kpair(s)] += 1
            top = max(survey.values())
            target = min(k for k, v in survey.items() if v == top)
            rng = rng_rule(DATA_SEED, f"names:{rel}:{st}:answer")       # restart the answer stream
            ans, nd = [], 0
            while len(ans) < 20:
                nd += 1
                assert nd <= CAP, "IMPLEMENTATION_FAIL answer stream"
                s = draw(rng, st)
                if form_ok(s, st) and kpair(s) == target and not rejected(s, st, accepted):
                    if s.lower() in ablob:
                        anchor_rej += 1
                        continue
                    ans.append(s); accepted.append(s)
            ab = "nat" if st == "natural" else "rnd"
            for i in range(20):
                learned = i < 15
                facts.append({"fact_id": f"E1P-{'L' if learned else 'U'}-{rel}-{ab}-{(i + 1 if learned else i - 14):02d}",
                              "exposure": "learned" if learned else "unread", "relation": rel, "stratum": st,
                              "entity": ents[i], "answer": ans[i]})
            log.append({"cell": f"{rel}/{st}", "entity_draws": ent_draws, "target_pair": list(target), "answer_draws": nd})
    return facts, log, anchor_rej


def main():
    repo, commit, tokdir, anchor_path, out_dir = sys.argv[1:6]
    ok = True
    dm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/DATA_MANIFEST.json"))
    proto = git_blob(repo, commit, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md").decode("utf-8")
    ng = dm["name_generation"]
    exp = ng["expected_facts_canonical_sha256"]
    m22 = re.search(r"规范化 SHA-256 必须等于 `([0-9a-f]{64})`。参考实现 `reports/round2/names.py`", proto)
    print("freeze-commit manifest expected_facts_canonical_sha256:", exp)
    print("freeze-commit protocol 2.2 value                      :", m22.group(1) if m22 else None)
    ok &= bool(m22) and m22.group(1) == exp
    checks = [
        ("seeds.DATA_SEED", dm["seeds"]["DATA_SEED"], DATA_SEED),
        ("facts.relations", dm["facts"]["relations"], RELS),
        ("facts.strata", dm["facts"]["strata"], STRATA),
        ("natural.onsets", ng["natural"]["onsets"], ONSETS),
        ("natural.nuclei", ng["natural"]["nuclei"], NUCLEI),
        ("natural.codas", ng["natural"]["codas"], CODAS),
        ("natural.length_chars", ng["natural"]["length_chars"], [4, 10]),
        ("random.letters", ng["random"]["letters"], LETTERS),
        ("random.digits", ng["random"]["digits"], DIGITS),
        ("random.length_chars", ng["random"]["length_chars"], [6, 8]),
        ("max_draws_per_stream", ng["max_draws_per_stream"], CAP),
        ("expected_facts_fields", ng["expected_facts_fields"], ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]),
        ("streams.entity", ng["streams"]["entity"], "rng_rule(DATA_SEED, 'names:<relation>:<stratum>:entity')"),
        ("streams.answer", ng["streams"]["answer"], "rng_rule(DATA_SEED, 'names:<relation>:<stratum>:answer')"),
    ]
    for name, got, want in checks:
        print(f"  manifest {name} == transcribed: {got == want}")
        ok &= got == want
    texts = json.load(open(anchor_path, encoding="utf-8"))
    ah = sha(canon(texts))
    print("anchor texts:", len(texts), "| canonical sha256", ah, "| == manifest anchor_text.decoded_texts_canonical_sha256:",
          ah == dm["anchor_text"]["decoded_texts_canonical_sha256"])
    ok &= ah == dm["anchor_text"]["decoded_texts_canonical_sha256"]
    tok = load_tok(tokdir)
    print("tokenizer dir files:", sorted(x for x in os.listdir(tokdir) if not x.startswith(".")))
    facts, log, anchor_rej = generate(tok, texts)
    for c in log:
        print("  cell", json.dumps(c))
    print("anchor-rule rejections:", anchor_rej)
    strings = [x for f in facts for x in (f["entity"], f["answer"])]
    print("facts", len(facts), dict(Counter(f["exposure"] for f in facts)), "| distinct strings", len(set(strings)))
    ok &= len(facts) == 160 and len(set(strings)) == 320
    h = sha(canon(facts))
    print(f"regenerated facts canonical sha256 {h} | manifest {exp} | MATCH {h == exp}")
    print(f"AUDIT_VALUE facts_canonical_sha256 {h}")
    ok &= h == exp
    print("first fact:", json.dumps(facts[0], ensure_ascii=False), "| last fact:", json.dumps(facts[-1], ensure_ascii=False))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "facts.json"), "wb") as fh:
        fh.write(canon(facts))
    print("wrote", os.path.join(out_dir, "facts.json"))
    return ok


run(main)
