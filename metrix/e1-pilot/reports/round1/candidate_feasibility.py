#!/usr/bin/env python3
"""Round 1, task 4: can the candidate rules of the protocol (aa0423ef) be met? Tokenizer only.

No model weights are loaded, nothing is trained or scored, no TEST question is built and no data
file is written: names are generated in memory and only counts are printed.

The four constraints on the candidates of a fact (protocol 2.2 and 2.5): the same relation, the same
stratum, the same exposure class (learned / unread), and the same answer token-count pair
(statement context with a leading space, QA context at the start of the assistant turn).

Parameters are read from DATA_MANIFEST.json. Three details are not fixed by aa0423ef and are read here
as follows (reported as a finding): the random-stream purposes 'names:<relation>:<stratum>:<role>';
the survey = the first 400 draws of the answer stream that pass the length / single-token rules; the
accept pass restarts the same stream and keeps draws with the target pair that pass reject_if.

  python3 candidate_feasibility.py --manifest metrix/e1-pilot/DATA_MANIFEST.json \
      --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --tokenizer-dir <snapshot> [--extra-seeds 20]
"""
import argparse
import collections
import hashlib
import json
import random

MAX_DRAWS = 20000


def rng_for(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(("%s:%s" % (seed, purpose)).encode("utf-8")).digest()[:8], "big"))


def lev_le1(a, b):
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


class Gen:
    def __init__(self, man, tok):
        self.ng, self.tok = man["name_generation"], tok
        self.ids = lambda t: tok.encode(t, add_special_tokens=False)

    def draw(self, r, stratum):
        g = self.ng[stratum]
        if stratum == "natural":
            n = 2 if r.random() < g["syllables"]["2"] else 3
            s = "".join(r.choice(g["onsets"]) + r.choice(g["nuclei"]) + r.choice(g["codas"]) for _ in range(n))
            return s[0].upper() + s[1:]
        u = r.random()
        p3, p4 = g["L"]["3"], g["L"]["4"]
        L = 3 if u < p3 else (4 if u < p3 + p4 else 5)
        return "".join(r.choice(g["letters"]) for _ in range(L)) + "-" + "".join(r.choice(g["digits"]) for _ in range(2))

    def form_ok(self, s, stratum):
        lo, hi = self.ng[stratum]["length_chars"]
        if not lo <= len(s) <= hi:
            return False
        return stratum != "natural" or len(self.ids(" " + s)) > 1

    @staticmethod
    def clash(s, stratum, accepted):
        if stratum == "natural":
            low = s.lower()
            return any(a.lower() == low or a[:4] == s[:4] or lev_le1(a.lower(), low) for a in accepted)
        block = s.split("-")[0]
        return any(a == s or a.split("-")[0] == block or (len(a) == len(s) and sum(x != y for x, y in zip(a, s)) <= 1)
                   for a in accepted)

    def pair(self, s):
        return (len(self.ids(" " + s)), len(self.ids(s)))


def build(gen, man, seed):
    relations, strata = man["facts"]["relations"], man["facts"]["strata"]
    nl, nu = man["facts"]["per_cell"]["learned"], man["facts"]["per_cell"]["unread"]
    accepted, facts, cells = [], [], []
    for rel in relations:
        for st in strata:
            c = {"cell": "%s/%s" % (rel, st)}
            r = rng_for(seed, "names:%s:%s:entity" % (rel, st))
            ents, n = [], 0
            while len(ents) < nl + nu and n < MAX_DRAWS:
                s = gen.draw(r, st)
                n += 1
                if gen.form_ok(s, st) and not gen.clash(s, st, accepted):
                    ents.append(s)
                    accepted.append(s)
            c["entity_draws"] = n
            r = rng_for(seed, "names:%s:%s:answer" % (rel, st))
            survey, n = [], 0
            while len(survey) < 400 and n < MAX_DRAWS:
                s = gen.draw(r, st)
                n += 1
                if gen.form_ok(s, st):
                    survey.append(gen.pair(s))
            cnt = collections.Counter(survey)
            best = max(cnt.values())
            target = min(p for p, k in cnt.items() if k == best)
            c["target_pair"] = "%d/%d" % target
            c["target_share"] = round(best / len(survey), 3)
            r = rng_for(seed, "names:%s:%s:answer" % (rel, st))
            ans, n = [], 0
            while len(ans) < nl + nu and n < MAX_DRAWS:
                s = gen.draw(r, st)
                n += 1
                if gen.form_ok(s, st) and gen.pair(s) == target and not gen.clash(s, st, accepted):
                    ans.append(s)
                    accepted.append(s)
            c["answer_draws"] = n
            c["filled"] = len(ents) == nl + nu and len(ans) == nl + nu
            cells.append(c)
            for i, (e, a) in enumerate(zip(ents, ans)):
                facts.append({"relation": rel, "stratum": st, "exposure": "learned" if i < nl else "unread",
                              "entity": e, "answer": a})
    return facts, cells, accepted


def pools(gen, facts):
    p = collections.defaultdict(list)
    for f in facts:
        p[(f["relation"], f["stratum"], f["exposure"], gen.pair(f["answer"]))].append(f["answer"])
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--tokenizer-dir", required=True)
    ap.add_argument("--extra-seeds", type=int, default=20)
    a = ap.parse_args()
    man = json.load(open(a.manifest, encoding="utf-8"))
    sm = json.load(open(a.split_manifest, encoding="utf-8"))
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    gen = Gen(man, tok)
    seed = man["seeds"]["DATA_SEED"]
    facts, cells, accepted = build(gen, man, seed)
    print("DATA_SEED %d: per cell" % seed)
    for c in cells:
        print("  " + json.dumps(c))
    print("facts: %d, distinct strings: %d of %d" % (len(facts), len(set(accepted)), len(accepted)))
    P = pools(gen, facts)
    print("pools under the four constraints (relation, stratum, exposure, token pair): %d" % len(P))
    for (rel, st, ex, pr), v in sorted(P.items()):
        print("  %-8s %-7s %-7s pair %d/%d: %2d answers -> %2d possible distractors per fact (3 needed)" % (
            rel, st, ex, pr[0], pr[1], len(v), len(v) - 1))
    sizes = [len(v) for v in P.values()]
    short = [k for k, v in P.items() if len(v) < 4]
    print("minimum pool size: %d; pools with fewer than 4 candidates: %d %s" % (min(sizes), len(short), short))
    split_by = collections.Counter(k[:3] for k in P)
    print("(relation, stratum, exposure) groups split over more than one token pair: %d" % sum(v > 1 for v in split_by.values()))

    # boundary consistency on TRAIN statements and DEV questions (no TEST template is used)
    tpl = {}
    for t in sm["templates"]:
        tpl.setdefault((t["relation"], t["kind"]), []).append(t["text"])
    ids = gen.ids

    def chat(q):
        return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
    bad_st = bad_qa = 0
    for f in facts:
        st = tpl[(f["relation"], "TRAIN")][0].replace("{E}", f["entity"]).replace("{A}", f["answer"])
        cut = st.rindex(f["answer"])
        if ids(st) != ids(st[:cut].rstrip(" ")) + ids(" " + f["answer"]) + ids(st[cut + len(f["answer"]):]):
            bad_st += 1
        for q in tpl[(f["relation"], "DEV")]:
            c = chat(q.replace("{E}", f["entity"]))
            if ids(c + f["answer"]) != ids(c) + ids(f["answer"]):
                bad_qa += 1
    print("boundary: TRAIN statements whose tokens != prefix + ' answer' + rest: %d of %d" % (bad_st, len(facts)))
    print("boundary: DEV prompts whose tokens != chat(question) + answer tokens: %d of %d" % (bad_qa, 2 * len(facts)))

    # Y / F token ratio of the training corpora (protocol 2.6 requires [0.80, 1.25])
    f_tok = y_tok = 0
    for f in facts:
        if f["exposure"] != "learned":
            continue
        f_tok += len(ids(tpl[(f["relation"], "TRAIN")][0].replace("{E}", f["entity"]).replace("{A}", f["answer"]))) + 1
        y_tok += len(ids(tpl[(f["relation"], "Y_ENTITY")][0].replace("{E}", f["entity"]))) + 1
        y_tok += len(ids(tpl[(f["relation"], "Y_ANSWER")][0].replace("{A}", f["answer"]))) + 1
    print("token count per pass (statements + endoftext): train_F %d, train_Y %d, ratio Y/F %.3f (protocol 2.6: [0.80, 1.25])" % (
        f_tok, y_tok, y_tok / f_tok))

    # robustness: the same construction with other data seeds
    worst = []
    for k in range(1, a.extra_seeds + 1):
        fs, cs, acc = build(gen, man, seed + 1000 * k)
        P2 = pools(gen, fs)
        worst.append((all(c["filled"] for c in cs), min(len(v) for v in P2.values()), max(c["answer_draws"] for c in cs),
                      len(set(acc)) == len(acc)))
    print("robustness over %d other data seeds: all cells filled %d/%d, minimum pool %d, largest answer draws %d (limit %d), "
          "all strings distinct %d/%d" % (len(worst), sum(w[0] for w in worst), len(worst), min(w[1] for w in worst),
                                          max(w[2] for w in worst), MAX_DRAWS, sum(w[3] for w in worst), len(worst)))


if __name__ == "__main__":
    main()
