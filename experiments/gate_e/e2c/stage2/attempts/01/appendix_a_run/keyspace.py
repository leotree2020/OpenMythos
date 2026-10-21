"""Feasibility counts for the E2-c design (aggregate numbers only; no set is
sampled or written). Key rule copied from e_common: key = ';'.join(sorted
statements), held-out iff sha256(key) mod 10 == 0."""
import hashlib, itertools, json, os, sys
from collections import Counter
SETS = sys.argv[1]
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIG = "0123456789"
def key(st): return ";".join(sorted(f"{v}={d}" for v, d in st))
def held(k): return int(hashlib.sha256(k.encode()).hexdigest(), 16) % 10 == 0
def stmts(body): return [(body[i], body[i + 2]) for i in range(0, len(body), 4)]
allk, H = 0, set()
for l1, l2 in itertools.combinations(LETTERS, 2):
    for d1 in DIG:
        for d2 in DIG:
            if d1 == d2: continue
            allk += 1
            k = key([(l1, d1), (l2, d2)])
            if held(k): H.add(k)
print("keys total", allk, "held-out", len(H), "share %.5f" % (len(H) / allk))
used = Counter()
U = set()
def add(name, body):
    k = key(stmts(body))
    if k in H:
        U.add(k); used[name] += 1
for name in ("dev_heldout", "test_heldout", "diag_fit", "diag_eval"):
    for line in open(os.path.join(SETS, name + ".jsonl")):
        r = json.loads(line)
        add(name, r["body"])
        for rs in r.get("root_swap", []):
            add(name + "_root_swap", rs["body"])
for line in open(os.path.join(SETS, "minpair.jsonl")):
    r = json.loads(line)
    add("minpair_xprime", r["body"])
print("E1 held-out keys used (with repeats) by set", dict(used))
print("E1 distinct held-out keys used", len(U))
R = H - U
print("remaining pool R", len(R))
# root-swap availability inside a pool
def swaps(k, pool):
    (a, b) = k.split(";")
    st = [(a[0], a[2]), (b[0], b[2])]
    out = []
    for j in range(2):
        ds = {st[0][1], st[1][1]}
        c = []
        for d in DIG:
            if d in ds: continue
            nst = list(st); nst[j] = (st[j][0], d)
            nk = key(nst)
            if nk in pool: c.append(nk)
        out.append(c)
    return out
deg = Counter()
both = 0
minopt = Counter()
for k in R:
    s = swaps(k, R)
    m = min(len(s[0]), len(s[1]))
    minopt[m] += 1
    both += m >= 1
print("keys in R with a root swap inside R for both statements", both)
print("distribution of min(#swap options) over the two statements", dict(sorted(minopt.items())))
# where do the repeated E1 usages come from (aggregate counts only)
by = {}
for name in ("dev_heldout", "test_heldout", "diag_fit", "diag_eval"):
    by[name] = set()
    if name == "test_heldout": by["test_root_swap"] = []
    for line in open(os.path.join(SETS, name + ".jsonl")):
        r = json.loads(line)
        by[name].add(key(stmts(r["body"])))
        for rs in r.get("root_swap", []):
            by["test_root_swap"].append(key(stmts(rs["body"])))
by["minpair_heldout"] = {key(stmts(json.loads(l)["body"])) for l in open(os.path.join(SETS, "minpair.jsonl")) if json.loads(l)["heldout"]}
rs = by["test_root_swap"]
print("root-swap usages", len(rs), "distinct", len(set(rs)))
for n in ("dev_heldout", "test_heldout", "diag_fit", "diag_eval", "minpair_heldout"):
    print(" root-swap keys also in", n, len(set(rs) & by[n]))
print(" minpair held-out x' keys also in diag/dev/test", len(by["minpair_heldout"] & (by["dev_heldout"] | by["test_heldout"] | by["diag_fit"] | by["diag_eval"])))
# per-statement root-swap availability inside R (for the per-statement design variant)
per = Counter()
for k in R:
    s = swaps(k, R)
    per[(len(s[0]) > 0) + (len(s[1]) > 0)] += 1
print("keys in R by number of statements with a root swap inside R", dict(sorted(per.items())))
