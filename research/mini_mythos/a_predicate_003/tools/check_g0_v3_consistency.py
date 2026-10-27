#!/usr/bin/env python3
"""G0-V3-SPEC-001 consistency check: g0_criteria_v3.json <-> E1A_GATE_G0_PREREG_V3.md <-> the frozen V2 and V1 files.  READS FILES ONLY (JSON + regex + SHA-256); starts no process.
usage: check_g0_v3_consistency.py [GATE_G0_DIR]   Exit 0 = no inconsistency."""
import hashlib, json, os, re, sys

G0 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate_g0")
sha = lambda p: hashlib.sha256(open(os.path.join(G0, p), "rb").read()).hexdigest()
V1_C = "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2"
V1_M = "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb"
V2_C = "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438"
V2_M = "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2"
bad = []
def need(c, m):
    if not c: bad.append(m)

need(sha("g0_criteria_v1.json") == V1_C and sha("E1A_GATE_G0_PREREG.md") == V1_M, "V1 files changed")
need(sha("g0_criteria_v2.json") == V2_C, "V2 criteria changed")
if bad:
    print("INCONSISTENCIES: %d" % len(bad))
    for b in bad: print("  -", b)
    sys.exit(1)                      # a frozen file changed: stop before parsing anything
v1 = json.load(open(os.path.join(G0, "g0_criteria_v1.json"))); v2 = json.load(open(os.path.join(G0, "g0_criteria_v2.json")))
raw3 = open(os.path.join(G0, "g0_criteria_v3.json"), "rb").read(); v3 = json.loads(raw3); sha3 = hashlib.sha256(raw3).hexdigest()
md = open(os.path.join(G0, "E1A_GATE_G0_PREREG_V3.md"), encoding="utf-8").read()
v2md = sha("E1A_GATE_G0_PREREG_V2.md")

need(v3["criteria_id"] == "E1A-GATE-G0-CRITERIA-V3" and v3["schema_version"] == "e1a-gate-g0-criteria-3" and v3["stage"] == "G0", "V3 identity")
S = v3["supersedes"]
need(S["criteria_sha256"] == V2_C and S["prereg_text_sha256"] == v2md and S["earlier"]["criteria_sha256"] == V1_C and S["earlier"]["prereg_text_sha256"] == V1_M, "V3 supersedes hashes")
need(set(v3["checks"]) == set(v2["checks"]) and len(v3["checks"]) == 17, "check id set differs from V2")
for k in ("limits", "exit_codes", "protocol_sequence", "snapshots", "scope", "not_in_scope", "residue_policy", "meaning_of_pass"):
    need(v3[k] == v2[k], "field %s differs from V2" % k)
need(v3["verdict_rule"][:5] == v2["verdict_rule"][:5], "V2's first five verdict_rule lines not preserved")
for k, t in v2["enforcement"].items():
    need(v3["enforcement"].get(k) == t, "enforcement.%s changed" % k)
need({"release_evidence", "registry_ledger"} <= set(v3["enforcement"]), "enforcement lacks the V3 additions")
rel = {"IDENTICAL": 0, "MODIFIED": 0}
for cid, c in v3["checks"].items():
    o = v2["checks"][cid]
    need(c["name"] == o["name"] and c["on_fail"] == o["on_fail"], "%s renamed or failure class changed" % cid)
    rel[c["v2_relation"]] = rel.get(c["v2_relation"], 0) + 1
    if c["v2_relation"] == "IDENTICAL":
        need(c["text"] == o["text"] and "rules" not in c, "%s IDENTICAL but differs" % cid)
    else:
        need(cid in ("G0-C03", "G0-C07", "G0-C16") and c["text"] != o["text"] and c.get("note"), "%s MODIFIED without being one of C03/C07/C16, or unchanged" % cid)
need(rel == {"IDENTICAL": 14, "MODIFIED": 3}, "relation counts %r" % rel)
need([m["id"] for m in v3["v2_to_v3_mapping"]] == sorted(v3["checks"]), "mapping is not the ordered full list")
for m in v3["v2_to_v3_mapping"]:
    c = v3["checks"][m["id"]]
    need((m["relation"], m["name"], m["v3_on_fail"], m["v2_on_fail"]) == (c["v2_relation"], c["name"], c["on_fail"], v2["checks"][m["id"]]["on_fail"]), "mapping row %s" % m["id"])
r3, r7 = v3["checks"]["G0-C03"]["rules"], v3["checks"]["G0-C07"]["rules"]
ids3 = [x["id"] for x in r3["fail_when"]] + [x["id"] for x in r3["unevaluable_when"]]
ids7 = [x["id"] for x in r7["fail_when"]] + [x["id"] for x in r7["unevaluable_when"]]
need([x["id"] for x in r3["fail_when"]] == ["C03-F1", "C03-F2", "C03-F3", "C03-F4"], "C03 fail rule ids")
need([x["id"] for x in r3["unevaluable_when"]] == ["C03-U0", "C03-U2", "C03-U3", "C03-U1", "C03-U4"], "C03 unevaluable rule ids / order")
need([x["id"] for x in r7["fail_when"]] == ["C07-F1", "C07-F2", "C07-F3", "C07-F4"] and [x["id"] for x in r7["unevaluable_when"]] == ["C07-U1", "C07-U2", "C07-U3", "C07-U4", "C07-U5"], "C07 rule ids")
tokens = set(ids3 + ids7) | {"C03-pass_when", "C07-pass_when", "C16"}
for p in v3["verdict_policy"]:
    need(all(t in tokens for t in p["implemented_by"]), "policy %d names an unknown rule" % p["n"])
need(sorted(p["n"] for p in v3["verdict_policy"]) == [1, 2, 3, 4, 5, 6], "verdict policy numbering")
es = v3["evidence_schema"]; paths = [f["path"] for f in es["fields"]]
need(len(paths) == len(set(paths)), "duplicate evidence paths")
need(es["id"] == "e1a-gate-g0-evidence-3" and ("'%s'" % es["id"]) in v3["checks"]["G0-C16"]["text"], "evidence schema id not named in C16")
need(all(re.fullmatch(r"(C\d\d)( C\d\d)*|C16", f["consumers"]) for f in es["fields"]), "consumers must list check ids")
need({"reg_memory_records", "reg_writer_seq", "reg", "reg_parse_info", "guard.release_writes", "evidence_schema", "consumed_dir", "evidence_root", "run_dir"} <= set(paths), "required evidence paths missing")
need("guard.release_byte_pre_write_monos" not in paths, "the pre-write list must not be an evidence field in V3")
need(all(f["type"] and isinstance(f["nullable"], bool) for f in es["fields"]), "schema rows need type and nullable")
need(any(a["id"] == "SUMMARY" for a in v3["implementation_obligations"]), "fail_scope obligation")

# ---------------- MD vs JSON
need(("SHA-256 `%s`" % sha3) in md, "MD does not quote the V3 criteria hash")
need(all(h in md for h in (V1_C, V2_C, v2md)), "MD lacks V1/V2 hashes")
rows = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (FAIL|BLOCKED) \| (IDENTICAL|MODIFIED) \| (.*) \|$", line)
    if m: rows[m.group(1)] = m.groups()[1:]
need(sorted(rows) == sorted(v3["checks"]), "MD check table")
for cid, (name, of, rl, text) in rows.items():
    c = v3["checks"][cid]
    need((name, of, rl) == (c["name"], c["on_fail"], c["v2_relation"]) and text.replace("\\|", "|") == c["text"], "MD check row %s" % cid)
mp = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (\w+) → (\w+) \| \*\*(\w+)\*\* \| (.*) \|$", line)
    if m: mp[m.group(1)] = m.groups()[1:]
need(sorted(mp) == sorted(v3["checks"]), "MD mapping table")
for cid, (name, a, b, r, note) in mp.items():
    m = next(x for x in v3["v2_to_v3_mapping"] if x["id"] == cid)
    need((name, a, b, r, note) == (m["name"], m["v2_on_fail"], m["v3_on_fail"], m["relation"], m["note"]), "MD mapping row %s" % cid)
for r in r3["fail_when"] + r3["unevaluable_when"] + r7["fail_when"] + r7["unevaluable_when"]:
    need(("| `%s` |" % r["id"]) in md and r["when"].replace("|", "\\|") in md, "MD rule %s" % r["id"])
need(r3["pass_when"] in md and r3["precedence"] in md and r7["pass_when"] in md, "MD pass/precedence text")
for k, t in r3["definitions"].items(): need(("**%s**：%s" % (k, t)) in md, "MD definition %s" % k)
for k, t in r3["witnesses"].items(): need(("**%s**：%s" % (k, t)) in md, "MD witness %s" % k)
for k, t in r3["policy_notes"].items(): need(("**%s**：%s" % (k, t)) in md, "MD policy note %s" % k)
sch = {}
for line in md.splitlines():
    m = re.match(r"^\| `([A-Za-z0-9_.]+)` \| (.*?) \| (是|否) \| ((?:C\d\d)(?: C\d\d)*) \| (.*) \|$", line)
    if m and "." in m.group(1) or (m and m.group(1) in paths): sch[m.group(1)] = m.groups()[1:]
need(set(sch) == set(paths), "MD schema table paths differ (missing %s extra %s)" % (sorted(set(paths) - set(sch))[:3], sorted(set(sch) - set(paths))[:3]))
for f in es["fields"]:
    if f["path"] in sch:
        t, n, cons, note = sch[f["path"]]
        need((t.replace("\\|", "|"), n, cons, note.replace("\\|", "|")) == (f["type"], "是" if f["nullable"] else "否", f["consumers"], f["note"]), "MD schema row %s" % f["path"])
for p in v3["verdict_policy"]:
    need(("| %d | %s |" % (p["n"], p["policy"])) in md, "MD policy row %d" % p["n"])
for o in v3["implementation_obligations"]: need(("**%s**：%s" % (o["id"], o["requirement"])) in md, "MD obligation %s" % o["id"])
for k, t in v3["enforcement"].items(): need(("**%s**：%s" % (k, t)) in md, "MD enforcement %s" % k)
for line in v3["verdict_rule"]: need(("* %s" % line) in md, "MD verdict_rule line")
need("fail_scope" in md and "not evidence about the Mythos model architecture" in md, "MD fail_scope statement")
need("AUTHORIZATION_E1A_GATE_G0.json" in md and "不创建" in md, "MD authorization statement")
need("14 项与 V2 文字逐字相同（IDENTICAL），3 项语义改变（MODIFIED：**C03、C07、C16**）" in md, "MD relation-count sentence")

print("V3 criteria sha256:", sha3)
print("V1/V2 files unchanged:", sha("g0_criteria_v1.json") == V1_C and sha("g0_criteria_v2.json") == V2_C)
print("relations:", rel, "| checks:", len(v3["checks"]), "| MD check rows:", len(rows), "| MD mapping rows:", len(mp), "| schema fields:", len(paths), "| MD schema rows:", len(sch))
print("INCONSISTENCIES: %d" % len(bad))
for b in bad: print("  -", b)
sys.exit(0 if not bad else 1)
