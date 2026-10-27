#!/usr/bin/env python3
"""Design-review checker for the V3 closeout cases (F-20 / F-22).  Reads JSON only; tests no G0 code.
For every case and every column with states: the final verdict must equal the arithmetic aggregation of the check states under the V3 verdict rule
(FAIL if an evaluable FAIL-class check failed; else BLOCKED if anything is not PASS; else PASS), using the failure classes of g0_criteria_v3.json.
The proposed-fix column (v4_proposed / alpha / beta) must equal the stated 'correct' verdict where one is stated.  usage: crit.json cases.json"""
import json, sys
crit = json.load(open(sys.argv[1])); D = json.load(open(sys.argv[2]))
cls = {k.replace("G0-", ""): v["on_fail"] for k, v in crit["checks"].items()}
bad = []
def need(c, m):
    if not c: bad.append(m)
def agg(states):
    fail = any(s == "FAIL" and cls.get(k, "BLOCKED") == "FAIL" for k, s in states.items())
    anything = any(s != "PASS" for s in states.values())
    return "FAIL" if fail else ("BLOCKED" if anything else "PASS")
n = 0
for c in D["f20"] + D["f22"]:
    for name in ("v3_literal", "current_impl", "v4_proposed", "alpha", "beta"):
        col = c.get(name)
        if not col: continue
        st = col["states"]
        if "AMBIGUOUS" in st.values():
            need(col["final"] is None, "%s %s ambiguous column must have final null" % (c["id"], name)); continue
        need(all(k in cls for k in st), "%s %s unknown check ids %s" % (c["id"], name, sorted(set(st) - set(cls))))
        need(col["final"] == agg(st), "%s %s final %s != aggregation %s" % (c["id"], name, col["final"], agg(st))); n += 1
    if c["correct"] in ("PASS", "FAIL", "BLOCKED"):
        need(c["v4_proposed"]["final"] == c["correct"] if "v4_proposed" in c else c["alpha"]["final"] == c["correct"] == c["beta"]["final"], "%s proposed column != correct" % c["id"])
    need(c["credibility"]["level"] in ("HIGH", "MEDIUM", "INSUFFICIENT"), "%s credibility" % c["id"])
dd5 = next(c for c in D["f22"] if c["id"] == "REL-DD5")
need(dd5["alpha"]["final"] == "FAIL" and dd5["beta"]["final"] == "BLOCKED" and dd5["v3_literal"]["final"] is None, "DD-5 must show alpha FAIL / beta BLOCKED / V3 literal ambiguous")
wrong = [c["id"] for c in D["f20"] if c["v3_literal"]["final"] != c["correct"]]
wrong_cur = [c["id"] for c in D["f20"] if c["current_impl"]["final"] != c["correct"]]
print("F-20 cases:", len(D["f20"]), "| F-22 cases:", len(D["f22"]), "| pipeline cases:", len(D["pipeline"]), "| columns aggregated:", n)
print("F-20: V3 literal differs from the correct verdict in", wrong, "; current implementation differs in", wrong_cur)
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
sys.exit(0 if not bad else 1)
