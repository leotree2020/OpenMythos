"""Reference implementation of the E1-PILOT name generation (protocol 2.2 as fixed in round 2), used by the
round 2 checks. Tokenizer only; no model weights. Builds facts in memory; writes nothing by itself.

The three details fixed in round 2:
  1. random streams: rng_rule(DATA_SEED, "names:<relation>:<stratum>:entity") and
     rng_rule(DATA_SEED, "names:<relation>:<stratum>:answer"), one stream per cell and role;
  2. survey: the first 400 draws of the answer stream that pass the form rules (length; for natural also
     "more than one token with a leading space"), reject_if NOT applied; count the (statement-context,
     QA-context) token-count pairs; target = the most frequent pair, ties broken by the smaller pair
     (compared as a tuple);
  3. accept: the answer stream is RESTARTED (a new generator from the same purpose); draws are accepted in
     order when they pass the form rules, have the target pair and pass reject_if, until 20 are accepted.
"""
import collections
import hashlib
import json
import random

MAX_DRAWS = 20000
SURVEY = 400


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(("%s:%s" % (seed, purpose)).encode("utf-8")).digest()[:8], "big"))


def lev_le1(a, b):
    """Levenshtein distance between a and b is at most 1."""
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


class Names:
    def __init__(self, data_manifest, tokenizer):
        self.m = data_manifest
        self.ng = data_manifest["name_generation"]
        self.tok = tokenizer

    def ids(self, text):
        return self.tok.encode(text, add_special_tokens=False)

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

    def build(self, seed=None, banned=None):
        """Returns (facts, per-cell log). `banned(s)` -> True rejects a string (used for the anchor-text rule)."""
        seed = self.m["seeds"]["DATA_SEED"] if seed is None else seed
        f = self.m["facts"]
        nl, nu = f["per_cell"]["learned"], f["per_cell"]["unread"]
        accepted, facts, log = [], [], []
        for rel in f["relations"]:
            for st in f["strata"]:
                c = {"cell": "%s/%s" % (rel, st)}
                r = rng_rule(seed, "names:%s:%s:entity" % (rel, st))
                ents, n = [], 0
                while len(ents) < nl + nu:
                    if n >= MAX_DRAWS:
                        raise RuntimeError("IMPLEMENTATION_FAIL: entity stream exhausted in %s" % c["cell"])
                    s = self.draw(r, st)
                    n += 1
                    if self.form_ok(s, st) and not self.clash(s, st, accepted) and not (banned and banned(s)):
                        ents.append(s)
                        accepted.append(s)
                c["entity_draws"] = n
                r = rng_rule(seed, "names:%s:%s:answer" % (rel, st))
                survey, n = [], 0
                while len(survey) < SURVEY:
                    if n >= MAX_DRAWS:
                        raise RuntimeError("IMPLEMENTATION_FAIL: survey exhausted in %s" % c["cell"])
                    s = self.draw(r, st)
                    n += 1
                    if self.form_ok(s, st):
                        survey.append(self.pair(s))
                cnt = collections.Counter(survey)
                best = max(cnt.values())
                target = min(p for p, k in cnt.items() if k == best)
                c["target_pair"] = list(target)
                r = rng_rule(seed, "names:%s:%s:answer" % (rel, st))     # restart the same stream
                ans, n = [], 0
                while len(ans) < nl + nu:
                    if n >= MAX_DRAWS:
                        raise RuntimeError("IMPLEMENTATION_FAIL: answer stream exhausted in %s" % c["cell"])
                    s = self.draw(r, st)
                    n += 1
                    if (self.form_ok(s, st) and self.pair(s) == target and not self.clash(s, st, accepted)
                            and not (banned and banned(s))):
                        ans.append(s)
                        accepted.append(s)
                c["answer_draws"] = n
                log.append(c)
                short = "nat" if st == "natural" else "rnd"
                for i, (e, a) in enumerate(zip(ents, ans)):
                    learned = i < nl
                    facts.append({"fact_id": "E1P-%s-%s-%s-%02d" % ("L" if learned else "U", rel, short,
                                                                    (i + 1) if learned else (i - nl + 1)),
                                  "exposure": "learned" if learned else "unread", "relation": rel, "stratum": st,
                                  "entity": e, "answer": a})
        return facts, log


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(b):
    return hashlib.sha256(b).hexdigest()
