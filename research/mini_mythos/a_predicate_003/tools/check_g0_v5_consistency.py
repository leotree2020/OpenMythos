#!/usr/bin/env python3
"""G0-V5-CLOSEOUT-SPEC-001 consistency check: g0_criteria_v5.json <-> E1A_GATE_G0_PREREG_V5.md <-> the frozen V4, V3, V2 and V1 files, plus guards against summary/closed contradictions.
READS FILES ONLY (JSON + regex + SHA-256); starts no process.   usage: check_g0_v5_consistency.py [GATE_G0_DIR]   Exit 0 = no inconsistency."""
import hashlib, json, os, re, sys
G0 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate_g0")
sha = lambda p: hashlib.sha256(open(os.path.join(G0, p), "rb").read()).hexdigest()
FROZEN = {"g0_criteria_v1.json": "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2", "E1A_GATE_G0_PREREG.md": "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb",
          "g0_criteria_v2.json": "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438", "E1A_GATE_G0_PREREG_V2.md": "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2",
          "g0_criteria_v3.json": "653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a", "E1A_GATE_G0_PREREG_V3.md": "0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88",
          "g0_criteria_v4.json": "6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414", "E1A_GATE_G0_PREREG_V4.md": "05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42"}
bad = []
def need(c, m):
    if not c: bad.append(m)
for f, h in FROZEN.items():
    need(sha(f) == h, "frozen file %s changed" % f)
if bad:
    print("INCONSISTENCIES: %d" % len(bad)); [print("  -", b) for b in bad]; sys.exit(1)
v4 = json.load(open(os.path.join(G0, "g0_criteria_v4.json")))
raw5 = open(os.path.join(G0, "g0_criteria_v5.json"), "rb").read(); v5 = json.loads(raw5); sha5 = hashlib.sha256(raw5).hexdigest()
md = open(os.path.join(G0, "E1A_GATE_G0_PREREG_V5.md"), encoding="utf-8").read()
txt5 = raw5.decode("utf-8"); all_text = txt5 + "\n" + md
esc = lambda t: str(t).replace("|", "\\|")

# ---------------- identity and supersession
need(v5["criteria_id"] == "E1A-GATE-G0-CRITERIA-V5" and v5["schema_version"] == "e1a-gate-g0-criteria-5" and v5["stage"] == "G0", "V5 identity")
S = v5["supersedes"]
need(S["criteria_sha256"] == FROZEN["g0_criteria_v4.json"] and S["prereg_text_sha256"] == FROZEN["E1A_GATE_G0_PREREG_V4.md"] and S["criteria_id"] == v4["criteria_id"], "supersedes V4")
need(S["earlier"]["v3"]["criteria_sha256"] == FROZEN["g0_criteria_v3.json"] and S["earlier"]["v3"]["prereg_text_sha256"] == FROZEN["E1A_GATE_G0_PREREG_V3.md"], "supersedes V3 hashes")
need(S["earlier"]["v2"]["criteria_sha256"] == FROZEN["g0_criteria_v2.json"] and S["earlier"]["v1"]["criteria_sha256"] == FROZEN["g0_criteria_v1.json"], "supersedes earlier hashes")
need(v5["base_commit"] == "d127ec58c0adc90d11fb7fc59240632fc4e36d5b", "base commit")

# ---------------- the V4 -> V5 diff is exactly what v4_to_v5_changes declares
def diff_paths(a, b):
    out = set()
    for k in set(a) | set(b):
        if a.get(k) == b.get(k): continue
        if k == "checks":
            for cid in set(a[k]) | set(b[k]):
                x = {kk: vv for kk, vv in a[k].get(cid, {}).items() if kk != "v4_relation"}; y = {kk: vv for kk, vv in b[k].get(cid, {}).items() if kk != "v4_relation"}
                if x != y: out.add("checks." + cid)
        elif k == "evidence_pipeline":
            for sub in set(a[k]) | set(b[k]):
                if a[k].get(sub) == b[k].get(sub): continue
                if sub == "stages":
                    sa = {s["id"]: s for s in a[k][sub]}; sb = {s["id"]: s for s in b[k][sub]}
                    for sid in set(sa) | set(sb):
                        if sa.get(sid) != sb.get(sid): out.add("evidence_pipeline.stages." + sid)
                else: out.add("evidence_pipeline." + sub)
        else: out.add(k)
    return out
changed = diff_paths(v4, v5)
declared = set(p for x in v5["v4_to_v5_changes"] for p in x["paths"])
need(changed == declared, "changed paths differ from declared: undeclared %s, declared-but-unchanged %s" % (sorted(changed - declared), sorted(declared - changed)))
need(sorted(changed & {"checks.G0-C%02d" % i for i in range(2, 18)}) == [], "a check other than G0-C01 changed")
need([x["id"] for x in v5["v4_to_v5_changes"]] == ["V5-CH-%d" % i for i in range(1, len(v5["v4_to_v5_changes"]) + 1)], "change ids")
for k in ("limits", "exit_codes", "protocol_sequence", "snapshots", "scope", "not_in_scope", "residue_policy", "witness_dependencies", "date", "stage"):
    need(v5[k] == v4[k], "field %s differs from V4" % k)
for cid in [c for c in v5["checks"] if c != "G0-C01"]:
    x = dict(v5["checks"][cid]); x.pop("v4_relation"); need(x == v4["checks"][cid], "%s differs from V4" % cid)
need(v5["checks"]["G0-C01"]["text"] != v4["checks"]["G0-C01"]["text"], "C01 text must differ from V4")
need(set(v5["checks"]) == set(v4["checks"]) and len(v5["checks"]) == 17, "check id set")
need(all(v5["checks"][c]["on_fail"] == v4["checks"][c]["on_fail"] for c in v5["checks"]), "a failure class changed")
need({k: v for k, v in v5["verdict_rule"][:len(v4["verdict_rule"])]} if False else v5["verdict_rule"][:len(v4["verdict_rule"])] == v4["verdict_rule"], "V4 verdict_rule lines must be kept unchanged")
need(v5["decision_register"][:len(v4["decision_register"])] == v4["decision_register"], "the V4 decisions (DD-1..DD-5 and the rest) must be unchanged")
need(v5["verdict_policy"][:len(v4["verdict_policy"])] == v4["verdict_policy"] and [p["n"] for p in v5["verdict_policy"]] == list(range(1, 11)), "verdict policy")
need(all(v5["limitations"][k] == v4["limitations"][k] for k in v4["limitations"]) and {"L-6", "L-7", "L-8"} <= set(v5["limitations"]), "limitations")
sf5 = {f["path"]: f for f in v5["evidence_schema"]["fields"]}; sf4 = {f["path"]: f for f in v4["evidence_schema"]["fields"]}
need(list(sf5) == list(sf4), "evidence schema field set")
need(sorted(p for p in sf5 if sf5[p] != sf4[p]) == ["evidence_schema", "preflight"], "evidence schema: only the notes of 'evidence_schema' and 'preflight' may change")
need(all((sf5[p]["type"], sf5[p]["nullable"], sf5[p]["consumers"]) == (sf4[p]["type"], sf4[p]["nullable"], sf4[p]["consumers"]) for p in sf5), "evidence schema types / consumers changed")
need(sf5["evidence_schema"]["note"] == "must equal 'e1a-gate-g0-evidence-4'" and v5["evidence_schema"]["id"] == "e1a-gate-g0-evidence-4", "evidence schema id / V4 erratum")
# mapping
need([m["id"] for m in v5["v4_to_v5_mapping"]] == sorted(v5["checks"]), "mapping order")
rel = {}
for m in v5["v4_to_v5_mapping"]:
    c = v5["checks"][m["id"]]; rel[m["relation"]] = rel.get(m["relation"], 0) + 1
    need((m["name"], m["v4_on_fail"], m["v5_on_fail"], m["relation"]) == (c["name"], v4["checks"][m["id"]]["on_fail"], c["on_fail"], c["v4_relation"]), "mapping row %s" % m["id"])
need(rel == {"IDENTICAL": 16, "MODIFIED": 1} and v5["checks"]["G0-C01"]["v4_relation"] == "MODIFIED", "relation counts %r" % rel)
need(v5["v3_to_v4_mapping"] == v4["v3_to_v4_mapping"] and v5["rule_migration"] == v4["rule_migration"], "historical V3->V4 mapping / rule migration must be kept")

# ---------------- closure structure
CL = v5["closure"]; PUB = CL["publication"]; PF = CL["preflight"]; MS = CL["marker_schema"]
need([f["path"] for f in MS["fields"]] == ["closed_schema", "run_id", "criteria_id", "criteria_sha256", "evidence_sha256", "evidence_bytes", "summary_sha256", "summary_bytes", "recorded_verdict", "recorded_exit_code", "process_exit_proof"], "marker fields")
need(all(MS["fields"][i]["nullable"] is False for i in range(len(MS["fields"]))), "marker fields are not nullable")
cf = {f["path"]: f for f in MS["fields"]}
need(cf["closed_schema"]["const"] == MS["id"] == "e1a-gate-g0-closed-1" and cf["process_exit_proof"]["const"] is False and cf["criteria_id"]["const"] == v5["criteria_id"], "marker consts")
need(MS["max_bytes"] == 4096, "marker size limit")
for w in ("no default=", "no trailing newline", "allow_nan=False", "sort_keys=True"): need(w in MS["serialisation"], "marker serialisation mentions %r" % w)
for w in ("exactly the keys", "bool is never an int", "canonical form", "duplicate object keys", "regular file"): need(w in MS["validation"], "marker validation mentions %r" % w)
steps = PUB["steps"]
need([s["id"] for s in steps] == ["K%d" % i for i in range(8)], "K steps")
pub = [s["published"] for s in steps]
need(pub == [False] * 4 + [True] * 4 and steps[4]["id"] == "K4" and "os.link" in steps[4]["operation"], "published flag must switch exactly at K4 (os.link)")
need("O_EXCL" in steps[2]["operation"] and "fsync" in steps[2]["operation"] and "O_NOFOLLOW" in steps[3]["operation"] and "O_DIRECTORY" in steps[5]["operation"] and "fsync" in steps[5]["operation"], "K2/K3/K5 details")
for s in steps[1:]:
    if s["id"] == "K4": continue
    ops = s["operation"]
    for m in re.finditer(r"os\.(rename|replace|unlink|remove|truncate)", ops): need(ops[max(0, m.start() - 3):m.start()] in ("no ", "NO "), "step %s prescribes %s" % (s["id"], m.group(0)))
need("no os.rename, os.replace" in steps[4]["operation"], "K4 forbids rename / replace")
fl = PUB["failures"]
need([f["published"] for f in fl] == [False, True] and all(f["exit_code"] == 3 for f in fl), "failure table")
need("G0-CLOSE-UNPUBLISHED" in fl[0]["stderr"] and "G0-CLOSE-UNCONFIRMED" in fl[1]["stderr"], "failure markers")
need(all(("G0-CLOSE-UNPUBLISHED" in v5["evidence_pipeline"]["stages"][7]["on_failure"] and "G0-CLOSE-UNCONFIRMED" in v5["evidence_pipeline"]["stages"][7]["on_failure"]) for _ in [0]), "P7 names both markers")
need(set(re.findall(r"K\d", fl[0]["steps"])) == {"K1", "K2", "K3", "K4"} and set(re.findall(r"K\d", fl[1]["steps"])) == {"K5", "K6", "K7"}, "failure table steps")
need("never deleted" in PUB["no_delete"] and "never deleted" in PUB["summary"], "temporary file is never deleted")
# preflight rules
R = PF["rules"]; facts = PF["facts"]
need([r["id"] for r in R] == ["CL-%02d" % i for i in range(1, 24)], "rule ids")
need(len({r["reason"] for r in R}) == 23, "reason codes unique")
need([r["id"] for r in R if r.get("scope") == "global"] == ["CL-21", "CL-22", "CL-23"], "global rules")
for r in R:
    need(r["human_action"] in PF["human_actions"], "%s human action" % r["id"])
    for cnd in r["applies"] + r.get("when", []) + r.get("when_any", []):
        need(cnd["fact"] in facts and all(v in facts[cnd["fact"]]["values"] for v in cnd["in"]), "%s uses an unknown fact or value" % r["id"])
need(set(PF["human_actions"]) == {"H1", "H2"}, "human actions")
need([x["id"] for x in CL["crash_points"]] == ["X%d" % i for i in range(1, 8)], "crash points")
need("not proof" in CL["principle"] or "NOT proof" in CL["principle"], "principle denies process-exit proof")
need(cf["process_exit_proof"]["const"] is False and any("exited" in x for x in CL["what_closure_does_not_prove"]), "not-proves list")
# C01 text uses the rules and keeps the live-process condition independent
c01 = v5["checks"]["G0-C01"]["text"]
for w in ("closure.preflight", "CL-01..CL-20", "never makes a run closed", "independently of (1)", "g0_run.py", "MANUAL_DISPOSITION_REQUIRED.json in the evidence root", "unresolved_prior"): need(w in c01, "C01 text lacks %r" % w)
# contradictions: summary existence must not close a run anywhere in V5
for frag in ("without a closed g0_summary.json", "sees a run directory without g0_summary.json", "the next preflight sees a run directory without g0_summary.json and refuses"):
    need(frag not in txt5, "V4 fragment survives in the JSON: %r" % frag)
    need(frag not in md.replace(PF["v4_reading"], ""), "V4 fragment survives in the MD: %r" % frag)
for w in ("never closes a run", "closes nothing"):
    need(w in txt5, "V5 lacks %r" % w)
for m in re.finditer(r"default=str", txt5): need(txt5[max(0, m.start() - 4):m.start()].lower().endswith("no "), "default=str without negation at %d" % m.start())
need(all(p["policy"] for p in v5["verdict_policy"]) and v5["verdict_policy"][8]["policy"].startswith("A run is closed only by"), "policy 9")
ids = {r["id"] for r in R}
for p in v5["verdict_policy"][8:]: need(all(t in ids | {"G0-C01", "P6", "P7"} for t in p["implemented_by"]), "policy %d names an unknown rule" % p["n"])
stg = v5["evidence_pipeline"]["stages"]
need([s["id"] for s in stg] == ["P%d" % i for i in range(8)] and stg[7]["name"] == "publish the closure marker and exit", "pipeline stages")
need(all(s["exit_code_on_failure"] in (3, None) for s in stg), "pipeline exit codes")
for sid in ("P1", "P2", "P3", "P6"): need(re.search(r"stderr: G0-", stg[int(sid[1])]["on_failure"]), "%s stderr marker" % sid)
need("not closure" in stg[6]["on_failure"] or "neither is evidence of closure" in stg[6]["on_failure"], "P6 on_failure no longer equates a file with closure")
need("Only here may exit code 0 or 1 be returned" in stg[7]["operation"], "P7 exit rule")
need({"CLOSE-1", "CLOSE-2", "CLOSE-3", "PIPELINE"} <= {o["id"] for o in v5["implementation_obligations"]}, "obligations")
need(set(v5["enforcement"]) == set(v4["enforcement"]) | {"closure"}, "enforcement keys")
# decision register: V4 ones kept, new ones registered, statuses
dr = {d["id"]: d for d in v5["decision_register"]}
need(len(v5["decision_register"]) == 15 and {"F-23", "CL-A", "CL-B", "CL-C", "CL-D", "CL-E"} <= set(dr), "decision register ids")
for d in v5["decision_register"][9:]:
    need(d["status"] == "PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL" and re.match(r"(stated|derived)\b", d["derivation"]) and set(d["review_status"]) == {"ChatGPT", "Grok"} and d["evidence_strength"].startswith("static design review only"), "decision %s fields" % d["id"])
need(dr["F-23"]["derivation"].startswith("stated") and dr["CL-C"]["derivation"].startswith("stated") and all(dr[i]["derivation"].startswith("derived") for i in ("CL-A", "CL-B", "CL-D", "CL-E")), "stated / derived marking of V5 decisions")

# ---------------- MD vs JSON
need(("SHA-256 `%s`" % sha5) in md, "MD does not quote the V5 criteria hash")
need(all(h in md for h in FROZEN.values() if h not in (FROZEN["E1A_GATE_G0_PREREG.md"], FROZEN["E1A_GATE_G0_PREREG_V2.md"], FROZEN["E1A_GATE_G0_PREREG_V3.md"])), "MD lacks frozen criteria hashes")
chk = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (FAIL|BLOCKED) \| (IDENTICAL|MODIFIED) \| (.*) \|$", line)
    if m: chk[m.group(1)] = m.groups()[1:]
need(sorted(chk) == sorted(v5["checks"]), "MD check table")
for cid, (n, of, rl, t) in chk.items():
    c = v5["checks"][cid]; need((n, of, rl) == (c["name"], c["on_fail"], c["v4_relation"]) and t.replace("\\|", "|") == c["text"], "MD check row %s" % cid)
mp = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (\w+) → (\w+) \| \*\*(\w+)\*\* \| (.*) \|$", line)
    if m: mp.setdefault(m.group(1), []).append(m.groups()[1:])
need(sorted(mp) == sorted(v5["checks"]) and all(len(v) == 2 for v in mp.values()), "MD mapping tables (V4->V5 and the V3->V4 appendix)")
for m in v5["v4_to_v5_mapping"]:
    need((m["name"], m["v4_on_fail"], m["v5_on_fail"], m["relation"], m["note"]) in [tuple(x) for x in mp.get(m["id"], [])], "MD V4->V5 mapping row %s" % m["id"])
for m in v5["v3_to_v4_mapping"]:
    need((m["name"], m["v3_on_fail"], m["v4_on_fail"], m["relation"], m["note"]) in [tuple(x) for x in mp.get(m["id"], [])], "MD V3->V4 mapping row %s" % m["id"])
for x in v5["v4_to_v5_changes"]:
    need(("| `%s` | %s | %s | %s |" % (x["id"], x["finding"], ", ".join("`%s`" % p for p in x["paths"]), esc(x["change"]))) in md, "MD change row %s" % x["id"])
r3, r7 = v5["checks"]["G0-C03"]["rules"], v5["checks"]["G0-C07"]["rules"]
for r in r3["fail_when"] + r3["unevaluable_when"] + r7["fail_when"] + r7["unevaluable_when"]:
    need(("| `%s` |" % r["id"]) in md and r["when"].replace("|", "\\|") in md, "MD rule %s" % r["id"])
rows = r3["requirements"]["rows"]; cols = r3["requirements"]["_columns"][1:]
for rid, row in rows.items(): need(("| `%s` | %s |" % (rid, " | ".join("是" if row[c] else "否" for c in cols))) in md, "MD requirements row %s" % rid)
for k, t in list(r3["definitions"].items()) + list(r3["witnesses"].items()) + list(r3["policy_notes"].items()): need(("**%s**：%s" % (k, t)) in md, "MD definition/witness/note %s" % k)
need(r3["pass_when"] in md and r3["precedence"] in md and r7["pass_when"] in md, "MD pass/precedence")
for m in v5["rule_migration"]: need(("| %s | %s | %s | %s |" % tuple(x.replace("|", "\\|") for x in (m["v3"], m["v4"], m["status"], m["note"]))) in md, "MD migration row %s" % m["v4"])
for p in v5["verdict_policy"]: need(("| %d | %s | %s |" % (p["n"], p["policy"], ", ".join("`%s`" % x for x in p["implemented_by"]))) in md, "MD policy %d" % p["n"])
for d in v5["decision_register"]: need(("| `%s` | %s |" % (d["id"], d["topic"])) in md, "MD decision %s" % d["id"])
sch = {}
for line in md.splitlines():
    m = re.match(r"^\| `([A-Za-z0-9_.]+)` \| (.*?) \| (是|否) \| ((?:C\d\d)(?: C\d\d)*) \| (.*) \|$", line)
    if m and (("." in m.group(1)) or m.group(1) in sf5): sch[m.group(1)] = m.groups()[1:]
need(set(sch) == set(sf5), "MD schema rows differ")
for p, f in sf5.items():
    if p in sch:
        t, n, cons, note = sch[p]
        need((t.replace("\\|", "|"), n, cons, note.replace("\\|", "|")) == (f["type"], "是" if f["nullable"] else "否", f["consumers"], f["note"]), "MD schema row %s" % p)
for s in stg: need(("| `%s` | %s |" % (s["id"], s["name"])) in md and esc(s["operation"]) in md and esc(s["on_failure"]) in md, "MD pipeline stage %s" % s["id"])
for k, t in v5["evidence_pipeline"]["preserved_on_failure"].items(): need(("**%s**：%s" % (k, t)) in md, "MD preserved %s" % k)
for k, t in v5["limitations"].items(): need(("**%s**：%s" % (k, t)) in md, "MD limitation %s" % k)
for o in v5["implementation_obligations"]: need(("**%s**：%s" % (o["id"], o["requirement"])) in md, "MD obligation %s" % o["id"])
for k, t in v5["enforcement"].items(): need(("**%s**：%s" % (k, t)) in md, "MD enforcement %s" % k)
for line in v5["verdict_rule"]: need(("* %s" % line) in md, "MD verdict_rule")
for f in MS["fields"]: need(("| `%s` | %s | 否 | %s | %s |" % (f["path"], esc(f["type"]), ("`%s`" % f["const"]) if f["const"] is not None else "—", esc(f["note"]))) in md, "MD marker field %s" % f["path"])
for s in steps: need(("| `%s` | %s | %s | %s |" % (s["id"], s["name"], esc(s["operation"]), "是" if s["published"] else "否")) in md, "MD step %s" % s["id"])
for f in fl: need(("| %s | %s | %d | `%s` | %s | %s |" % (f["steps"], "是" if f["published"] else "否", f["exit_code"], esc(f["stderr"]), esc(f["on_disk"]), esc(f["next_preflight"]))) in md, "MD failure row %s" % f["steps"])
for k, f in facts.items(): need(("| `%s` | %s | %s |" % (k, esc(", ".join(str(x) for x in f["values"])), esc(f["meaning"]))) in md, "MD fact %s" % k)
for r in R:
    need(("| `%s` | `%s` | %s |" % (r["id"], r["reason"], r.get("scope", "目录"))) in md and ("%s：%s" % (r["human_action"], esc(r["text"]))) in md, "MD closure rule %s" % r["id"])
for x in CL["crash_points"]: need(("| `%s` | %s | closed=%s, tmp=%s | %s |" % (x["id"], esc(x["after"]), x["facts"]["closed"], x["facts"]["tmp"], x["next_preflight"])) in md, "MD crash point %s" % x["id"])
for t in (CL["defect_in_v4"], CL["principle"], PUB["summary"], PUB["why_not_direct_write"], PUB["why_not_rename"], PUB["why_link"], PUB["exit_code_rule"], PUB["reporting_rule"], PUB["no_delete"], PF["scope"], PF["result"], PF["allowed_files"], PF["v4_reading"], MS["serialisation"], MS["validation"]):
    need(t in md, "MD lacks closure text %r" % t[:60])
for t in CL["what_closure_proves"] + CL["what_closure_does_not_prove"]: need(("* %s" % t) in md, "MD proves / not-proves item")
for k, t in PF["human_actions"].items(): need(("**%s**：%s" % (k, t)) in md, "MD human action %s" % k)
need("16 项 IDENTICAL，1 项 MODIFIED（**C01**）" in md, "MD relation-count sentence")
need("拟由项目负责人批准的决策，不是已完成的真实验证" in md and "fail_scope" in md and "AUTHORIZATION_E1A_GATE_G0.json" in md and "不创建" in md, "MD statements")
print("V5 criteria sha256:", sha5)
print("V1..V4 files unchanged:", all(sha(f) == h for f, h in FROZEN.items()))
print("changed paths (V4->V5):", len(changed), "= declared:", changed == declared)
print("relations:", rel, "| checks:", len(v5["checks"]), "| MD check rows:", len(chk), "| MD mapping rows:", sum(len(v) for v in mp.values()), "| schema fields:", len(sf5), "| MD schema rows:", len(sch))
print("closure: marker fields", len(MS["fields"]), "| steps", len(steps), "| preflight rules", len(R), "| crash points", len(CL["crash_points"]), "| pipeline stages", len(stg), "| decisions", len(dr))
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
sys.exit(0 if not bad else 1)
