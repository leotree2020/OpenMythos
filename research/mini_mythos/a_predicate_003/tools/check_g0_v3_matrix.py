#!/usr/bin/env python3
"""Design-review checker for the V3 counterexample matrix.  Reads JSON only; evaluates nothing about G0 itself.
Checks: every case names rules that exist in g0_criteria_v3.json, uses allowed states, and its FINAL verdict equals the arithmetic aggregation of its check states under the
frozen verdict rule (FAIL if an evaluable FAIL-class check failed; else BLOCKED if anything is not PASS; else PASS).  The old 23 ids must be present and their V3 verdict must equal
the 'correct_verdict' of the V2 semantic review.  This is NOT a test of any G0 code."""
import json, sys
crit_p, matrix_p, old_p = sys.argv[1:4]
crit = json.load(open(crit_p)); M = json.load(open(matrix_p)); old = json.load(open(old_p))
rules = {r["id"] for r in crit["checks"]["G0-C03"]["rules"]["fail_when"] + crit["checks"]["G0-C03"]["rules"]["unevaluable_when"]}
rules |= {r["id"] for r in crit["checks"]["G0-C07"]["rules"]["fail_when"] + crit["checks"]["G0-C07"]["rules"]["unevaluable_when"]}
bad = []
def need(c, m):
    if not c: bad.append(m)
ids = [c["id"] for c in M["cases"]]
need(len(ids) == len(set(ids)), "duplicate case ids")
oldc = {c["id"]: c for c in old["counterexamples"]}
need(set(oldc) <= set(ids), "old cases missing: %s" % sorted(set(oldc) - set(ids)))
used = set()
for c in M["cases"]:
    i = c["id"]
    for k in ("c03", "c07"):
        st = c[k]
        need(st["state"] in ("PASS", "FAIL", "UNEVALUABLE"), "%s %s state" % (i, k))
        base = "C03" if k == "c03" else "C07"
        if st["state"] != "PASS":
            r = st["rule"].split("(")[0]
            need(r in rules, "%s %s names unknown rule %r" % (i, k, st["rule"])); used.add(r)
            need((st["state"] == "FAIL") == ("-F" in r), "%s %s state/rule class mismatch %r" % (i, k, st))
    need(c["c16"] in ("PASS", "BLOCKED") and c["others"] in ("PASS", "BLOCKED"), "%s c16/others" % i)
    fail_class = c["c03"]["state"] == "FAIL" or c["c07"]["state"] == "FAIL"
    anything = c["c03"]["state"] != "PASS" or c["c07"]["state"] != "PASS" or c["c16"] != "PASS" or c["others"] != "PASS"
    agg = "FAIL" if fail_class else ("BLOCKED" if anything else "PASS")
    need(agg == c["final"], "%s final %s != aggregation %s" % (i, c["final"], agg))
    need(c["credibility"]["level"] in ("HIGH", "MEDIUM", "INSUFFICIENT") and c["credibility"]["basis"], "%s credibility" % i)
    if i in oldc:
        want = oldc[i]["correct_verdict"].split()[0]
        need(want == c["final"], "%s V3 final %s differs from the review's correct verdict %s" % (i, c["final"], want))
unused = sorted(rules - used)
print("cases:", len(ids), "| old:", len(oldc), "| new:", len(ids) - len(oldc))
from collections import Counter
print("final verdicts:", dict(Counter(c["final"] for c in M["cases"])))
print("rules exercised:", len(used), "of", len(rules), "| NOT exercised:", unused, "(C03-U4 is a fail-safe default that no enumerated combination reaches)")
need(set(unused) <= {"C03-U4"}, "rules without any case: %s" % unused)
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
sys.exit(0 if not bad else 1)
