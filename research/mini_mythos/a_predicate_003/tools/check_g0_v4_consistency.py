#!/usr/bin/env python3
"""G0-V4-SPEC-001 consistency check: g0_criteria_v4.json <-> E1A_GATE_G0_PREREG_V4.md <-> the frozen V3, V2 and V1 files, plus structural guards against rule contradictions.
READS FILES ONLY (JSON + regex + SHA-256); starts no process.   usage: check_g0_v4_consistency.py [GATE_G0_DIR]   Exit 0 = no inconsistency."""
import hashlib, json, os, re, sys
G0 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate_g0")
sha = lambda p: hashlib.sha256(open(os.path.join(G0, p), "rb").read()).hexdigest()
FROZEN = {"g0_criteria_v1.json": "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2", "E1A_GATE_G0_PREREG.md": "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb",
          "g0_criteria_v2.json": "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438", "E1A_GATE_G0_PREREG_V2.md": "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2",
          "g0_criteria_v3.json": "653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a", "E1A_GATE_G0_PREREG_V3.md": "0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88"}
bad = []
def need(c, m):
    if not c: bad.append(m)
for f, h in FROZEN.items():
    need(sha(f) == h, "frozen file %s changed" % f)
if bad:
    print("INCONSISTENCIES: %d" % len(bad)); [print("  -", b) for b in bad]; sys.exit(1)
v3 = json.load(open(os.path.join(G0, "g0_criteria_v3.json")))
raw4 = open(os.path.join(G0, "g0_criteria_v4.json"), "rb").read(); v4 = json.loads(raw4); sha4 = hashlib.sha256(raw4).hexdigest()
md = open(os.path.join(G0, "E1A_GATE_G0_PREREG_V4.md"), encoding="utf-8").read()
all_text = raw4.decode("utf-8") + "\n" + md

need(v4["criteria_id"] == "E1A-GATE-G0-CRITERIA-V4" and v4["schema_version"] == "e1a-gate-g0-criteria-4" and v4["stage"] == "G0", "V4 identity")
S = v4["supersedes"]
need(S["criteria_sha256"] == FROZEN["g0_criteria_v3.json"] and S["prereg_text_sha256"] == FROZEN["E1A_GATE_G0_PREREG_V3.md"], "supersedes V3 hashes")
need(S["earlier"]["v2"]["criteria_sha256"] == FROZEN["g0_criteria_v2.json"] and S["earlier"]["v1"]["criteria_sha256"] == FROZEN["g0_criteria_v1.json"], "supersedes earlier hashes")
need(set(v4["checks"]) == set(v3["checks"]) and len(v4["checks"]) == 17, "check id set differs from V3")
for k in ("limits", "exit_codes", "protocol_sequence", "snapshots", "scope", "not_in_scope", "residue_policy", "meaning_of_pass"):
    need(v4[k] == v3[k], "field %s differs from V3" % k)
need(v4["verdict_rule"][:5] == v3["verdict_rule"][:5], "first five verdict_rule lines")
for k, t in v3["enforcement"].items(): need(v4["enforcement"].get(k) == t, "enforcement.%s changed" % k)
need({"evidence_pipeline", "disk_fidelity"} <= set(v4["enforcement"]), "enforcement additions")

# ---- relations
DISK = {"G0-C04", "G0-C05", "G0-C11", "G0-C13"}
SUFFIX = " Evaluated only when the durable copy is faithful to the ledger (G0-C03 definitions.disk_faithful); otherwise UNEVALUABLE, and the C03 fidelity report lists the differences."
rel = {}
for cid, c in v4["checks"].items():
    o = v3["checks"][cid]
    need(c["name"] == o["name"] and c["on_fail"] == o["on_fail"], "%s renamed or class changed" % cid)
    rel[c["v3_relation"]] = rel.get(c["v3_relation"], 0) + 1
    if c["v3_relation"] == "IDENTICAL":
        need(c["text"] == o["text"] and "rules" not in c, "%s IDENTICAL but differs" % cid)
    else:
        need(cid in ("G0-C03", "G0-C04", "G0-C05", "G0-C07", "G0-C11", "G0-C13", "G0-C16") and c["text"] != o["text"] and c.get("note"), "%s MODIFIED unexpectedly" % cid)
    if cid in DISK:
        need(c["text"] == o["text"] + SUFFIX and c.get("reads_durable_fields"), "%s must be the V3 text + the M-2 suffix and name the durable fields it reads" % cid)
need(rel == {"IDENTICAL": 10, "MODIFIED": 7}, "relation counts %r" % rel)
need([m["id"] for m in v4["v3_to_v4_mapping"]] == sorted(v4["checks"]), "mapping is not the ordered full list")
for m in v4["v3_to_v4_mapping"]:
    c = v4["checks"][m["id"]]
    need((m["relation"], m["name"], m["v4_on_fail"], m["v3_on_fail"]) == (c["v3_relation"], c["name"], c["on_fail"], v3["checks"][m["id"]]["on_fail"]), "mapping row %s" % m["id"])

# ---- rules
r3, r7 = v4["checks"]["G0-C03"]["rules"], v4["checks"]["G0-C07"]["rules"]
f3ids = [x["id"] for x in r3["fail_when"]]; u3ids = [x["id"] for x in r3["unevaluable_when"]]
need(f3ids == ["C03-F1", "C03-F2", "C03-F3a", "C03-F3b", "C03-F3c", "C03-F4"], "C03 fail rule ids %r" % f3ids)
need(u3ids == ["C03-U0", "C03-U2", "C03-U3", "C03-U5", "C03-U1", "C03-U4"], "C03 unevaluable ids / order %r" % u3ids)
need([x["id"] for x in r7["fail_when"]] == ["C07-F1", "C07-F2", "C07-F3"] and [x["id"] for x in r7["unevaluable_when"]] == ["C07-U%d" % i for i in range(1, 8)], "C07 rule ids")
ids = set(f3ids + u3ids + [x["id"] for x in r7["fail_when"] + r7["unevaluable_when"]])
tokens = ids | {"C03-pass_when", "C07-pass_when", "C16"}
need(sorted(p["n"] for p in v4["verdict_policy"]) == list(range(1, 9)), "verdict policy numbering")
for p in v4["verdict_policy"]: need(all(t in tokens for t in p["implemented_by"]), "policy %d names an unknown rule" % p["n"])
# requirements table: complete, no FAIL rule relies on the durable copy, text agrees with the table (single source, no contradiction)
rows = r3["requirements"]["rows"]; cols = r3["requirements"]["_columns"][1:]
need(set(rows) == set(f3ids), "requirements rows must be exactly the C03 fail rules")
for rid, row in rows.items():
    need(set(row) == set(cols), "%s row columns" % rid)
    need(row["needs_ledger"] is True and row["relies_on_durable_copy"] is False, "%s must rely on the ledger and never on the durable copy" % rid)
wc_true = sorted(r for r, row in rows.items() if row["needs_writer_clean"]); wc_false = sorted(r for r, row in rows.items() if not row["needs_writer_clean"])
need(wc_true == ["C03-F2", "C03-F3a", "C03-F3b", "C03-F4"] and wc_false == ["C03-F1", "C03-F3c"], "writer_clean requirement set %r / %r" % (wc_true, wc_false))
need(("required by C03-F2, F3a, F3b and F4 and is explicitly not required by C03-F1 and F3c") in r3["requirements"]["writer_clean_summary"], "writer_clean_summary does not match the table")
txt = {x["id"]: x["when"] for x in r3["fail_when"]}
need("Needs a clean writer" in txt["C03-F3a"] and "Needs a clean writer" in txt["C03-F3b"], "F3a/F3b text must say they need a clean writer")
need("Applies even when an append failed" in txt["C03-F3c"] and "Needs a clean writer" not in txt["C03-F3c"], "F3c text must say it applies despite an append failure")
need("no append failed" in txt["C03-F2"], "F2 text must say it needs a clean writer")
for frag in ("F2, F3, F4", "need writer_clean", "needs writer_clean", "F2, F3 and F4"):
    need(frag not in all_text, "the contradictory V3 fragment %r survives" % frag)
for m in re.finditer(r"default=str", raw4.decode("utf-8")):
    need(raw4.decode("utf-8")[max(0, m.start() - 4):m.start()].lower().endswith(("no ", "NO ".lower())), "default=str appears without a negation at %d" % m.start())
need(v4["checks"]["G0-C03"]["rules"]["definitions"]["gate_pass_proven"].count("exactly one release attempt") == 1, "gate_pass_proven definition")
# witness dependencies
wd = v4["witness_dependencies"]
need(sorted(wd["disk_dependent_checks"]) == sorted(DISK) and set(wd["reads_durable_fields"]) == DISK, "witness_dependencies set")
need(all(v4["checks"][c].get("reads_durable_fields") == wd["reads_durable_fields"][c] for c in DISK), "reads_durable_fields differ between checks and witness_dependencies")
# rule migration covers every V3 and V4 rule id
v3ids = set(x["id"] for x in v3["checks"]["G0-C03"]["rules"]["fail_when"] + v3["checks"]["G0-C03"]["rules"]["unevaluable_when"] + v3["checks"]["G0-C07"]["rules"]["fail_when"] + v3["checks"]["G0-C07"]["rules"]["unevaluable_when"])
mig = " ".join(m["v3"] + " " + m["v4"] for m in v4["rule_migration"])
for r in v3ids: need(r in mig, "rule_migration does not mention V3 rule %s" % r)
for r in ids: need(r in mig, "rule_migration does not mention V4 rule %s" % r)
# evidence schema: same field set as V3, new id
need([f["path"] for f in v4["evidence_schema"]["fields"]] == [f["path"] for f in v3["evidence_schema"]["fields"]] and
     [(f["type"], f["nullable"]) for f in v4["evidence_schema"]["fields"]] == [(f["type"], f["nullable"]) for f in v3["evidence_schema"]["fields"]], "evidence field set differs from V3")
need(v4["evidence_schema"]["id"] == "e1a-gate-g0-evidence-4" and "'e1a-gate-g0-evidence-4'" in v4["checks"]["G0-C16"]["text"], "evidence schema id")
ser = v4["evidence_schema"]["serialisation"]
need(all(ser[max(0, m.start() - 3):m.start()] == "no " for m in re.finditer(r"json\.loads\(json\.dumps", ser)), "an in-memory json.loads(json.dumps()) round trip must not be prescribed (only denied)")
# pipeline
st = v4["evidence_pipeline"]["stages"]
need([s["id"] for s in st] == ["P%d" % i for i in range(8)], "pipeline stages P0..P7 in order")
need([s["name"] for s in st][:3] == ["construct", "strict serialisation", "exclusive write, fsync"], "pipeline order")
need(all(s["exit_code_on_failure"] in (3, None) for s in st), "pipeline exit codes")
for s in st:
    if s["id"] in ("P1", "P2", "P3", "P6"): need(re.search(r"stderr: G0-", s["on_failure"]), "%s needs a stderr marker" % s["id"])
# decision register
dr = {d["id"]: d for d in v4["decision_register"]}
need({"F-20/M-1", "M-2", "DD-1", "DD-2", "DD-3", "DD-4", "DD-5", "F-21", "F-22"} <= set(dr), "decision register ids")
for d in dr.values():
    need(d["status"] == "PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL" and re.match(r"(stated|derived)\b", d["derivation"]) and set(d["review_status"]) == {"ChatGPT", "Grok"} and d["evidence_strength"].startswith("static design review only"), "decision %s fields" % d["id"])
need(all(dr[i]["derivation"].startswith("derived") for i in ("DD-1", "DD-3", "DD-4")), "DD-1, DD-3, DD-4 must be marked derived (reviewers to confirm)")
need({"L-1", "L-3", "L-4", "L-5", "L-2"} == set(v4["limitations"]), "limitations")
need(any(o["id"] == "PIPELINE" for o in v4["implementation_obligations"]) and any(o["id"] == "M-2" for o in v4["implementation_obligations"]), "obligations")

# ---------------- MD vs JSON
need(("SHA-256 `%s`" % sha4) in md, "MD does not quote the V4 criteria hash")
need(all(h in md for h in (FROZEN["g0_criteria_v3.json"], FROZEN["E1A_GATE_G0_PREREG_V3.md"], FROZEN["g0_criteria_v2.json"], FROZEN["g0_criteria_v1.json"])), "MD lacks frozen hashes")
chk = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (FAIL|BLOCKED) \| (IDENTICAL|MODIFIED) \| (.*) \|$", line)
    if m: chk[m.group(1)] = m.groups()[1:]
need(sorted(chk) == sorted(v4["checks"]), "MD check table")
for cid, (n, of, rl, t) in chk.items():
    c = v4["checks"][cid]; need((n, of, rl) == (c["name"], c["on_fail"], c["v3_relation"]) and t.replace("\\|", "|") == c["text"], "MD check row %s" % cid)
mp = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (\w+) → (\w+) \| \*\*(\w+)\*\* \| (.*) \|$", line)
    if m: mp[m.group(1)] = m.groups()[1:]
need(sorted(mp) == sorted(v4["checks"]), "MD mapping table")
for cid, (n, a, b, r, note) in mp.items():
    m = next(x for x in v4["v3_to_v4_mapping"] if x["id"] == cid)
    need((n, a, b, r, note) == (m["name"], m["v3_on_fail"], m["v4_on_fail"], m["relation"], m["note"]), "MD mapping row %s" % cid)
for r in r3["fail_when"] + r3["unevaluable_when"] + r7["fail_when"] + r7["unevaluable_when"]:
    need(("| `%s` |" % r["id"]) in md and r["when"].replace("|", "\\|") in md, "MD rule %s" % r["id"])
for rid, row in rows.items():
    line = "| `%s` | %s |" % (rid, " | ".join("是" if row[c] else "否" for c in cols))
    need(line in md, "MD requirements row %s" % rid)
for k, t in list(r3["definitions"].items()) + list(r3["witnesses"].items()) + list(r3["policy_notes"].items()):
    need(("**%s**：%s" % (k, t)) in md, "MD definition/witness/note %s" % k)
need(r3["pass_when"] in md and r3["precedence"] in md and r7["pass_when"] in md, "MD pass/precedence")
for m in v4["rule_migration"]: need(("| %s | %s | %s | %s |" % tuple(x.replace("|", "\\|") for x in (m["v3"], m["v4"], m["status"], m["note"]))) in md, "MD migration row %s" % m["v4"])
for p in v4["verdict_policy"]: need(("| %d | %s |" % (p["n"], p["policy"])) in md, "MD policy %d" % p["n"])
for d in v4["decision_register"]: need(("| `%s` | %s |" % (d["id"], d["topic"])) in md, "MD decision %s" % d["id"])
sch = {}
for line in md.splitlines():
    m = re.match(r"^\| `([A-Za-z0-9_.]+)` \| (.*?) \| (是|否) \| ((?:C\d\d)(?: C\d\d)*) \| (.*) \|$", line)
    if m and (("." in m.group(1)) or m.group(1) in [f["path"] for f in v4["evidence_schema"]["fields"]]): sch[m.group(1)] = m.groups()[1:]
paths = [f["path"] for f in v4["evidence_schema"]["fields"]]
need(set(sch) == set(paths), "MD schema rows differ")
for f in v4["evidence_schema"]["fields"]:
    if f["path"] in sch:
        t, n, cons, note = sch[f["path"]]
        need((t.replace("\\|", "|"), n, cons, note.replace("\\|", "|")) == (f["type"], "是" if f["nullable"] else "否", f["consumers"], f["note"]), "MD schema row %s" % f["path"])
for s in st: need(("| `%s` | %s |" % (s["id"], s["name"])) in md and s["operation"].replace("|", "\\|") in md and s["on_failure"].replace("|", "\\|") in md, "MD pipeline stage %s" % s["id"])
for k, t in v4["evidence_pipeline"]["preserved_on_failure"].items(): need(("**%s**：%s" % (k, t)) in md, "MD preserved %s" % k)
for k, t in v4["limitations"].items(): need(("**%s**：%s" % (k, t)) in md, "MD limitation %s" % k)
for o in v4["implementation_obligations"]: need(("**%s**：%s" % (o["id"], o["requirement"])) in md, "MD obligation %s" % o["id"])
for k, t in v4["enforcement"].items(): need(("**%s**：%s" % (k, t)) in md, "MD enforcement %s" % k)
for line in v4["verdict_rule"]: need(("* %s" % line) in md, "MD verdict_rule")
need("10 项与 V3 文字逐字相同（IDENTICAL），7 项 MODIFIED（**C03、C04、C05、C07、C11、C13、C16**）" in md, "MD relation-count sentence")
need("拟由项目负责人批准的决策，不是已完成的真实验证" in md and "fail_scope" in md and "AUTHORIZATION_E1A_GATE_G0.json" in md and "不创建" in md, "MD statements")
print("V4 criteria sha256:", sha4)
print("V1/V2/V3 files unchanged:", all(sha(f) == h for f, h in FROZEN.items()))
print("relations:", rel, "| checks:", len(v4["checks"]), "| MD check rows:", len(chk), "| MD mapping rows:", len(mp), "| schema fields:", len(paths), "| MD schema rows:", len(sch), "| pipeline stages:", len(st), "| decisions:", len(dr))
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
sys.exit(0 if not bad else 1)
