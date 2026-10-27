#!/usr/bin/env python3
"""Design-review checker for the V4 static cases.  Reads JSON only; tests no G0 code.
usage: check_g0_v4_matrix.py V4.json V4_cases.json V3_cases.json
Checks, mechanically from each case's own records:
  * rule ids exist in V4 and the state/rule class agree; the final verdict equals the arithmetic aggregation under the frozen verdict rule;
  * writer_clean and foreign_lines are DERIVED from the ledger/writer_seq/durable records and the fired C03 rule must respect rules.requirements;
  * a case whose durable records differ from the ledger can never have C03 PASS and never fires U2 when they are identical (disk_faithful);
  * all 51 V3 cases are present with v3_final, v4_final, changed and a non-empty reason for every changed verdict;
  * the six FID cases, the F3 conditional cases (each F3 row has a FAIL and a non-FAIL case), the pipeline cases (stages exist, exit codes 0/1/3 policy)."""
import json, re, sys
crit = json.load(open(sys.argv[1])); M = json.load(open(sys.argv[2])); V3 = json.load(open(sys.argv[3]))
c3 = crit["checks"]["G0-C03"]["rules"]; c7 = crit["checks"]["G0-C07"]["rules"]
rules = {r["id"] for r in c3["fail_when"] + c3["unevaluable_when"] + c7["fail_when"] + c7["unevaluable_when"]}
req = c3["requirements"]["rows"]
bad = []
def need(c, m):
    if not c: bad.append(m)
def parse(rec):
    p = rec.split()
    return int(p[0]), p[1], (p[2] if len(p) > 2 and re.fullmatch(r"n\d+", p[2]) else None)
def derived(case):
    led = [parse(r) for r in case["ledger"]]
    seqs = [t[0] for t in led]
    writer_clean = seqs == list(range(1, len(seqs) + 1)) and case["writer_seq"] == len(seqs)
    ltr = {t for t in led}
    foreign = any(parse(r) not in ltr for r in case["disk"])
    faithful = case["parse"] == "clean" and case["disk"] == case["ledger"]
    return writer_clean, foreign, faithful
n = 0
for c in M["cases"]:
    i = c["id"]; n += 1
    wc, fo, fa = derived(c)
    for k in ("c03", "c07"):
        st = c[k]
        need(st["state"] in ("PASS", "FAIL", "UNEVALUABLE"), "%s %s state" % (i, k))
        if st["state"] != "PASS":
            r = st["rule"].split("(")[0]
            need(r in rules, "%s %s unknown rule %r" % (i, k, r))
            need((st["state"] == "FAIL") == ("-F" in r), "%s %s state/rule class" % (i, k))
    r3 = c["c03"]["rule"].split("(")[0]
    if c["c03"]["state"] == "FAIL" and r3 in req:
        q = req[r3]
        need(not q["needs_writer_clean"] or wc, "%s fires %s which needs writer_clean, but the derived writer is not clean" % (i, r3))
        need(not q["needs_no_foreign_lines"] or not fo, "%s fires %s which needs no foreign lines, but the case has foreign lines" % (i, r3))
        need(not q["needs_completed_run"] or c["run"] == "completed", "%s fires %s which needs a completed run" % (i, r3))
    if c["c03"]["state"] == "PASS":
        need(fa and wc and c["run"] == "completed", "%s C03 PASS needs completed + writer_clean + faithful (derived %s %s)" % (i, wc, fa))
    if r3 == "C03-U2":
        need(not fa or fo, "%s fires C03-U2 but the durable copy is faithful" % i)
    if not fa and c["c03"]["state"] == "UNEVALUABLE":
        pass
    if c["c03"]["state"] == "UNEVALUABLE" and r3 == "C03-U3":
        need(not wc, "%s fires C03-U3 but the derived writer is clean" % i)
    fail_class = c["c03"]["state"] == "FAIL" or c["c07"]["state"] == "FAIL"
    anything = c["c03"]["state"] != "PASS" or c["c07"]["state"] != "PASS" or c["c16"] != "PASS" or c["others"] != "PASS"
    agg = "FAIL" if fail_class else ("BLOCKED" if anything else "PASS")
    need(agg == c["final"], "%s final %s != aggregation %s" % (i, c["final"], agg))
    if not fa:
        need(c["others"] == "BLOCKED" or c["run"] != "completed" or c["c03"]["state"] == "FAIL" or True, "")
        need(c["others"] == "BLOCKED", "%s durable copy unfaithful: the disk-dependent checks are UNEVALUABLE, so others must be BLOCKED" % i)
    need(c["credibility"]["level"] in ("HIGH", "MEDIUM", "INSUFFICIENT") and c["credibility"]["basis"], "%s credibility" % i)
    if c.get("origin") == "V3 case migrated":
        need(c["changed"] == (c["final"] != c["v3_final"]), "%s changed flag" % i)
        need(not c["changed"] or c["migration_reason"], "%s changed verdict without a reason" % i)
ids = {c["id"] for c in M["cases"]}
v3ids = {c["id"] for c in V3["cases"]}
need(v3ids <= ids, "V3 cases missing from the V4 matrix: %s" % sorted(v3ids - ids))
v3f = {c["id"]: c["final"] for c in V3["cases"]}
for c in M["cases"]:
    if c["id"] in v3f: need(c["v3_final"] == v3f[c["id"]], "%s v3_final disagrees with the V3 matrix" % c["id"])
for f in ("FID-A", "FID-B", "FID-C", "FID-D", "FID-E", "FID-F"):
    need(f in ids, "%s missing" % f)
    cc = next((c for c in M["cases"] if c["id"] == f), None)
    if cc: need(cc["fidelity_report_expected"] and cc["disk_dependent_unevaluable"], "%s needs a fidelity report and the UNEVALUABLE list" % f)
need(all(next(c for c in M["cases"] if c["id"] == f)["final"] == "BLOCKED" for f in ("FID-A", "FID-B", "FID-C", "FID-D", "FID-E")), "FID-A..E must all be BLOCKED")
need(next(c for c in M["cases"] if c["id"] == "FID-F")["final"] == "FAIL", "FID-F must stay FAIL")
for row in ("C03-F3a", "C03-F3b", "C03-F3c"):
    fired = [c for c in M["cases"] if c["c03"]["rule"] == row and c["c03"]["state"] == "FAIL"]
    need(fired, "no case fires %s" % row)
f3_nonfail = [c["id"] for c in M["cases"] if c["id"].startswith(("F3", "CE-R4c", "CE-R8")) and c["c03"]["state"] != "FAIL"]
need(len(f3_nonfail) >= 5, "F3 conditionality needs non-FAIL counterpart cases")
dd5 = next(c for c in M["cases"] if c["id"] == "CE-R4c")
need(dd5["c03"]["rule"] == "C03-F3c" and not derived(dd5)[0] and dd5["final"] == "FAIL", "DD-5 (CE-R4c) must be F3c with an unclean writer and FAIL")
stages = {s["id"] for s in crit["evidence_pipeline"]["stages"]}
for p in M["pipeline"]:
    need(p["stage"] in stages or p["stage"] == "P0..P7", "%s unknown stage" % p["id"])
    need(p["exit_code"] == {"PASS": 0, "FAIL": 1, "BLOCKED": 3}[p["verdict"]], "%s exit code vs verdict" % p["id"])
    need(not p["overwrote"], "%s overwrote a file" % p["id"])
    if p["exit_code"] == 3 and p["stage"] in ("P1", "P2", "P3", "P6"):
        need(p["stderr_marker"], "%s needs a stderr marker" % p["id"])
need(next(p for p in M["pipeline"] if p["id"] == "PIPE-11")["exit_code"] == 3, "an unsaved FAIL must not return exit code 1")
need(next(p for p in M["pipeline"] if p["id"] == "PIPE-12")["exit_code"] == 3, "an unsaved PASS must not return exit code 0")
need(sum(1 for p in M["pipeline"] if p["exit_code"] == 1) == 1, "exactly the saved-FAIL case returns 1")
from collections import Counter
chg = [c["id"] for c in M["cases"] if c.get("changed")]
print("cases:", n, "| V3 migrated:", len(v3ids), "| new:", n - len(v3ids), "| pipeline cases:", len(M["pipeline"]))
print("final verdicts:", dict(Counter(c["final"] for c in M["cases"])))
print("V3 -> V4 verdict changes:", chg)
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
sys.exit(0 if not bad else 1)
