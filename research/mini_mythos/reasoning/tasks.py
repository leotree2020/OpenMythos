"""Synthetic in-context reasoning probes (Stage R). Deterministic given a seed; English text, no
special tokens. Every item: few-shot prompt ending in "A:", a list of candidate answers (each with a
leading space) and the index of the correct one. Families and difficulty levels:

  chain    variable chains with distractors, statements shuffled: hops 1, 2, 3, 4, 6   (chance 1/10)
  order    transitive comparison chains, statements shuffled: 2, 3, 4, 5 relations     (chance 1/(n+1))
  lookup   key-value retrieval (one hop, a control): 4, 8, 16 pairs                    (chance 1/10)
  add      chained single-digit addition with sum <= 9: 2, 3, 4 terms                  (chance 1/10)

`solve(item)` re-derives every answer from the question text alone (independent of the generator).
"""
import random
import re

LEVELS = {"chain": (1, 2, 3, 4, 6), "order": (2, 3, 4, 5), "lookup": (4, 8, 16), "add": (2, 3, 4)}
SHOTS = 3
DIGITS = [" %d" % d for d in range(10)]
NAMES = ["Anna", "Ben", "Cara", "Dan", "Eva", "Finn", "Gina", "Hugo", "Ivy", "Jack", "Kate", "Leo", "Mia",
         "Nick", "Olga", "Paul"]
RELATIONS = [("taller", "tallest", "shortest"), ("older", "oldest", "youngest"), ("faster", "fastest", "slowest")]
KEYS = ["red", "blue", "green", "black", "white", "gold", "pink", "gray", "brown", "lime", "navy", "teal", "plum",
        "rose", "sand", "mint", "coal", "snow", "rust", "jade"]
LETTERS = list("abcdefghijkmnpqrstuvwxyz")


def _chain(rng, hops):
    names = rng.sample(LETTERS, hops + 3)
    chain, distract = names[:hops + 1], names[hops + 1:]
    value = rng.randrange(10)
    stmts = ["%s = %d." % (chain[0], value)] + ["%s = %s." % (chain[i], chain[i - 1]) for i in range(1, hops + 1)]
    for d in distract:
        stmts.append("%s = %d." % (d, rng.randrange(10)))
    rng.shuffle(stmts)
    return "%s What is %s?" % (" ".join(stmts), chain[-1]), str(value), DIGITS


def _order(rng, n):
    names = rng.sample(NAMES, n + 1)            # names[0] is the top of the chain
    rel, top, bottom = rng.choice(RELATIONS)
    stmts = ["%s is %s than %s." % (names[i], rel, names[i + 1]) for i in range(n)]
    rng.shuffle(stmts)
    ask_top = rng.random() < 0.5
    answer = names[0] if ask_top else names[-1]
    cands = sorted(" " + x for x in names)
    return "%s Who is the %s?" % (" ".join(stmts), top if ask_top else bottom), answer, cands


def _lookup(rng, n):
    keys = rng.sample(KEYS, n)
    vals = [rng.randrange(10) for _ in keys]
    q = rng.randrange(n)
    pairs = ", ".join("%s: %d" % (k, v) for k, v in zip(keys, vals))
    return "%s. What is %s?" % (pairs, keys[q]), str(vals[q]), DIGITS


def _add(rng, k):
    while True:
        terms = [rng.randrange(1, 6) for _ in range(k)]
        if sum(terms) <= 9:
            break
    return "%s = ?" % " + ".join(str(t) for t in terms), str(sum(terms)), DIGITS


GEN = {"chain": _chain, "order": _order, "lookup": _lookup, "add": _add}


def make_item(rng, family, level):
    blocks = []
    for _ in range(SHOTS):
        q, a, _ = GEN[family](rng, level)
        blocks.append("Q: %s\nA: %s" % (q, a))
    q, a, cands = GEN[family](rng, level)
    prompt = "\n\n".join(blocks + ["Q: %s\nA:" % q])
    return {"family": family, "level": level, "prompt": prompt, "candidates": list(cands),
            "answer": cands.index(" " + a)}


def build(seed, per_cell):
    """All cells, `per_cell` items each, in a fixed order. Returns a list of dicts."""
    out = []
    for family, levels in LEVELS.items():
        for level in levels:
            rng = random.Random("%d/%s/%d" % (seed, family, level))
            for i in range(per_cell):
                item = make_item(rng, family, level)
                item["id"] = "%s-%d-%04d" % (family, level, i)
                out.append(item)
    return out


# ------------------------------------------------------------------ independent solver (from text)

def solve(item):
    """Answer the final question from its text only; returns the candidate index."""
    q = item["prompt"].rsplit("Q: ", 1)[1].rsplit("\nA:", 1)[0]
    f = item["family"]
    if f == "chain":
        env, refs = {}, {}
        for lhs, rhs in re.findall(r"(\w) = (\w)\.", q):
            (env if rhs.isdigit() else refs)[lhs] = int(rhs) if rhs.isdigit() else rhs
        v = re.search(r"What is (\w)\?", q).group(1)
        while v not in env:
            v = refs[v]
        ans = str(env[v])
    elif f == "order":
        rel = re.findall(r"(\w+) is \w+ than (\w+)\.", q)
        bigger = {a for a, _ in rel}
        smaller = {b for _, b in rel}
        top = (bigger - smaller).pop()
        bottom = (smaller - bigger).pop()
        word = re.search(r"Who is the (\w+)\?", q).group(1)
        ans = top if word in {r[1] for r in RELATIONS} else bottom
    elif f == "lookup":
        pairs = dict(re.findall(r"(\w+): (\d)", q))
        ans = pairs[re.search(r"What is (\w+)\?", q).group(1)]
    else:
        ans = str(sum(int(x) for x in re.findall(r"\d", q.split("=")[0])))
    return item["candidates"].index(" " + ans)


def chance(item):
    return 1.0 / len(item["candidates"])
