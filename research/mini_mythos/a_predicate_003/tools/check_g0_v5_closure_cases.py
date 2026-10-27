#!/usr/bin/env python3
"""G0-V5-CLOSEOUT-SPEC-001 static check of the closure rules against hand-derived design-review cases.
READS TWO JSON FILES ONLY; evaluates the machine-readable rules of closure.preflight over the case facts; starts no process, touches no G0 code.
usage: check_g0_v5_closure_cases.py g0_criteria_v5.json g0_v5_cases.json    Exit 0 = no inconsistency.   These are design reviews, not test results."""
import json, sys
crit = json.load(open(sys.argv[1])); M = json.load(open(sys.argv[2]))
CL = crit["closure"]; P = CL["preflight"]; FACTS = P["facts"]; RULES = P["rules"]
bad = []
def need(c, m):
    if not c: bad.append(m)
def cond(c, facts): return facts.get(c["fact"]) in c["in"]
def matches(rule, facts):
    if not all(cond(c, facts) for c in rule.get("applies", [])): return False
    if "when" in rule: return all(cond(c, facts) for c in rule["when"])
    return any(cond(c, facts) for c in rule["when_any"])
DIR_RULES = [r for r in RULES if r.get("scope") != "global"]; GLOB_RULES = [r for r in RULES if r.get("scope") == "global"]
def evaluate(run_dir, glob):
    hits = []
    if run_dir is not None: hits += [r for r in DIR_RULES if matches(r, run_dir)]
    facts = dict(glob)
    hits += [r for r in GLOB_RULES if matches(r, facts)]
    return hits
# ---- rule table sanity
ids = [r["id"] for r in RULES]
need(ids == ["CL-%02d" % i for i in range(1, len(ids) + 1)], "rule ids not consecutive")
need(len({r["reason"] for r in RULES}) == len(RULES), "reason codes not unique")
for r in RULES:
    need(("when" in r) != ("when_any" in r), "%s needs exactly one of when / when_any" % r["id"])
    need(r["human_action"] in P["human_actions"], "%s unknown human action" % r["id"])
    for c in r.get("applies", []) + r.get("when", []) + r.get("when_any", []):
        need(c["fact"] in FACTS, "%s unknown fact %s" % (r["id"], c["fact"]))
        if c["fact"] in FACTS:
            for v in c["in"]: need(v in FACTS[c["fact"]]["values"], "%s: value %r not allowed for %s" % (r["id"], v, c["fact"]))
GL = {"root_manual_disposition", "root_listing", "live_marker_process"}
DIRF = [f for f in FACTS if f not in GL]
covered = set(); used = {}
def check_facts(cid, rd, g, files):
    for k in g: need(k in GL, "%s global fact %s" % (cid, k))
    for k in GL: need(k in g, "%s missing global fact %s" % (cid, k))
    for k, v in g.items(): need(v in FACTS[k]["values"], "%s global %s=%r" % (cid, k, v))
    if rd is None: return
    if rd["entry"] != "real_dir":
        need(set(rd) == {"entry"}, "%s: non-directory entry carries other facts" % cid); return
    for k in DIRF: need(k in rd, "%s missing fact %s" % (cid, k))
    for k, v in rd.items():
        need(k in FACTS, "%s unknown fact %s" % (cid, k))
        if k in FACTS: need(v in FACTS[k]["values"], "%s: %s=%r not allowed" % (cid, k, v))
    ok = rd.get("closed") == "ok"
    for k in ("closed_runid", "criteria_vs_tool", "summary", "evidence"):
        need((rd.get(k) != "na") == ok, "%s: %s na-consistency (closed=%s)" % (cid, k, rd.get("closed")))
    need((rd.get("summary_binding") != "na") == (rd.get("summary") == "ok"), "%s: summary_binding na-consistency" % cid)
    need((rd.get("evidence_binding") != "na") == (rd.get("evidence") == "ok"), "%s: evidence_binding na-consistency" % cid)
    need((rd.get("criteria_vs_summary") != "na") == (ok and rd.get("summary") == "ok"), "%s: criteria_vs_summary na-consistency" % cid)
    need(rd.get("tmp") != "identical" or ok, "%s: tmp identical requires a valid marker" % cid)
    # files_present vs facts
    fp = set(files)
    need(("g0_closed.json" in fp) == (rd["closed"] != "absent"), "%s: g0_closed.json presence vs fact closed=%s" % (cid, rd["closed"]))
    need(("g0_closed.json.tmp" in fp) == (rd["tmp"] != "absent"), "%s: tmp presence vs fact" % cid)
    need(("MANUAL_DISPOSITION_REQUIRED.json" in fp) == bool(rd["manual_disposition"]), "%s: manual presence vs fact" % cid)
    for fname, key in (("g0_summary.json", "summary"), ("g0_evidence.json", "evidence")):
        if rd.get(key) not in ("na", None): need((fname in fp) == (rd[key] != "absent"), "%s: %s presence vs fact %s=%s" % (cid, fname, key, rd[key]))
# ---- closure cases
seen = []
nv4wrong = 0
for c in M["cases"]:
    cid = c["id"]; seen.append(cid)
    check_facts(cid, c["run_dir"], c["global"], c["files_present"])
    hits = evaluate(c["run_dir"], c["global"])
    reasons = [r["reason"] for r in hits]; covered |= {r["id"] for r in hits}
    e = c["expected"]
    need(reasons == e["reasons"], "%s: derived reasons %s != expected %s" % (cid, reasons, e["reasons"]))
    need(e["result"] == ("BLOCKED" if hits else "CLOSED_OK"), "%s: result" % cid)
    acts = sorted({r["human_action"] for r in hits})
    need(acts == sorted(e["human_actions"]), "%s: human actions derived %s != %s" % (cid, acts, e["human_actions"]))
    # V4 reading: closed iff g0_summary.json exists and no MANUAL_DISPOSITION_REQUIRED.json (dir or root); live process rule unchanged
    if c["run_dir"] is not None and c["run_dir"]["entry"] == "real_dir":
        v4_ok = "g0_summary.json" in c["files_present"] and "MANUAL_DISPOSITION_REQUIRED.json" not in c["files_present"] and not c["global"]["root_manual_disposition"] and not c["global"]["live_marker_process"]
        c["_v4"] = "CLEAN" if v4_ok else "BLOCKED"
        if v4_ok and hits: nv4wrong += 1; c["_v4_wrong"] = True
        need(not (hits == [] and not v4_ok), "%s: V5 accepts what V4 blocked" % cid)
need({"A", "B", "C", "D", "E", "F", "G", "H"} <= set(seen), "cases A..H must all be present")
need(len(seen) == len(set(seen)), "duplicate case ids")
need(covered == set(ids), "rules never exercised by a case: %s" % sorted(set(ids) - covered))
# ---- pipeline cases
steps = {s["id"]: s for s in CL["publication"]["steps"]}
fail_steps = {}
for f in CL["publication"]["failures"]:
    for s in [x.strip() for x in f["steps"].split(",")]:
        if s.startswith("K"): fail_steps[s] = f
need(set("K1 K2 K3 K4 K5 K6".split()) <= set(fail_steps), "failure table does not cover K1..K6")
pl = {s["id"]: s for s in crit["evidence_pipeline"]["stages"]}
for p in M["pipeline_cases"]:
    cid = p["id"]; st = p["failing_step"]; e = p["expected"]
    rd = {"ok": dict(M["defaults"]["run_dir"]), }.get(p["closed_after"])
    if p["closed_after"] == "ok": rd = dict(M["defaults"]["run_dir"])
    else:
        rd = dict(M["defaults"]["run_dir"]); rd.update(closed=p["closed_after"], tmp=p["tmp_after"], closed_runid="na", criteria_vs_tool="na", criteria_vs_summary="na", summary="na", summary_binding="na", evidence="na", evidence_binding="na")
    if p["closed_after"] == "ok": rd["tmp"] = p["tmp_after"]
    check_facts(cid, rd, M["defaults"]["global"], p["files_present"])
    hits = evaluate(rd, M["defaults"]["global"]); covered |= {r["id"] for r in hits}
    need([r["reason"] for r in hits] == e["next_preflight_reasons"], "%s: next preflight %s != %s" % (cid, [r["reason"] for r in hits], e["next_preflight_reasons"]))
    need(sorted({r["human_action"] for r in hits}) == sorted(e["human_actions"]), "%s: human actions" % cid)
    if st is None:
        need(e["process_exit_code"] == p["recorded"]["exit_code"] and e["reportable_outcome"] == p["recorded"]["verdict"] and p["published"] and not p["stderr_marker"], "%s: success case" % cid)
    else:
        need(e["process_exit_code"] == 3 and e["reportable_outcome"] == "BLOCKED", "%s: a failure must exit 3 and report BLOCKED" % cid)
        if st.startswith("K"):
            need(st in steps, "%s unknown step" % cid)
            if st in steps: need(p["published"] == steps[st]["published"] or (st == "K4" and not p["published"]), "%s: published flag vs step" % cid)
            f = fail_steps.get(st) or fail_steps.get("K5")
            need(f["published"] == p["published"] or st == "K7", "%s: published flag vs failure table" % cid)
            if st == "K7": need(p["published"], "%s: K7 is after publication" % cid)
            marker = "G0-CLOSE-UNCONFIRMED" if p["published"] else "G0-CLOSE-UNPUBLISHED"
            need(p["stderr_marker"] == marker and marker in f["stderr"], "%s: stderr marker %s" % (cid, p["stderr_marker"]))
        else:
            need(st in pl and p["stderr_marker"] in pl[st]["on_failure"], "%s: marker %s not in pipeline %s on_failure" % (cid, p["stderr_marker"], st))
            need(not p["published"] and p["closed_after"] == "absent", "%s: a P-stage failure never publishes" % cid)
    if p["published"] and st is not None: need(p["closed_after"] != "absent", "%s: published but no marker" % cid)
    if not p["published"]: need("g0_closed.json" not in p["files_present"] or p["closed_after"] != "ok", "%s: unpublished run shows a valid marker" % cid)
# ---- crash points
for x in CL["crash_points"]:
    rd = dict(M["defaults"]["run_dir"]); fx = x["facts"]
    if fx["closed"] != "ok": rd.update(closed=fx["closed"], tmp=fx["tmp"], closed_runid="na", criteria_vs_tool="na", criteria_vs_summary="na", summary="na", summary_binding="na", evidence="na", evidence_binding="na")
    else: rd["tmp"] = fx["tmp"]
    hits = evaluate(rd, M["defaults"]["global"])
    need(("CLOSED_OK" if not hits else hits[0]["reason"]) == x["next_preflight"], "crash point %s: derived %s != declared %s" % (x["id"], [h["reason"] for h in hits], x["next_preflight"]))
need(covered == set(ids), "rules not exercised after pipeline cases: %s" % sorted(set(ids) - covered))
from collections import Counter
res = Counter(c["expected"]["result"] for c in M["cases"])
print("closure cases:", len(M["cases"]), dict(res), "| pipeline cases:", len(M["pipeline_cases"]), "| crash points:", len(CL["crash_points"]))
print("rules:", len(ids), "all exercised:", covered == set(ids))
print("cases that V4 (summary-existence reading) would have accepted but V5 blocks:", nv4wrong)
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
json.dump({"cases": [{"id": c["id"], "v4": c.get("_v4"), "v4_wrongly_accepted": bool(c.get("_v4_wrong"))} for c in M["cases"]]}, open(sys.argv[2] + ".derived.json", "w")) if len(sys.argv) > 3 and sys.argv[3] == "--derive" else None
sys.exit(1 if bad else 0)
