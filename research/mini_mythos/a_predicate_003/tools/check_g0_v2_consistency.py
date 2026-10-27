#!/usr/bin/env python3
"""G0-V2-SPEC-001 consistency check between g0_criteria_v2.json (machine-readable) and E1A_GATE_G0_PREREG_V2.md (text), and between V2 and the
frozen V1 files.  READS FILES ONLY (JSON + regex + SHA-256); imports nothing from the bench; starts no process.
usage: check_g0_v2_consistency.py [GATE_G0_DIR]     (default: the gate_g0 directory next to ../gate_g0 of this file's repo location)
Exit 0 = no inconsistency."""
import hashlib
import json
import os
import re
import sys

G0 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate_g0")
sha = lambda p: hashlib.sha256(open(os.path.join(G0, p), "rb").read()).hexdigest()
V1_CRIT_SHA = "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2"
V1_MD_SHA = "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb"
bad = []


def need(cond, msg):
    if not cond:
        bad.append(msg)


need(sha("g0_criteria_v1.json") == V1_CRIT_SHA, "V1 criteria file hash changed")
need(sha("E1A_GATE_G0_PREREG.md") == V1_MD_SHA, "V1 prereg text hash changed")
v1 = json.load(open(os.path.join(G0, "g0_criteria_v1.json")))
raw2 = open(os.path.join(G0, "g0_criteria_v2.json"), "rb").read()
v2 = json.loads(raw2)
sha2 = hashlib.sha256(raw2).hexdigest()
md = open(os.path.join(G0, "E1A_GATE_G0_PREREG_V2.md"), encoding="utf-8").read()

# ---- JSON vs V1
need(v2["criteria_id"] == "E1A-GATE-G0-CRITERIA-V2" and v2["schema_version"] == "e1a-gate-g0-criteria-2" and v2["stage"] == "G0", "V2 identity fields")
need(v2["supersedes"]["criteria_sha256"] == V1_CRIT_SHA and v2["supersedes"]["prereg_text_sha256"] == V1_MD_SHA, "V2 supersedes hashes do not name the frozen V1 files")
need(set(v2["checks"]) == set(v1["checks"]) and len(v2["checks"]) == 17, "check id set differs from V1 (V2 must keep exactly C01..C17)")
for k in ("limits", "exit_codes", "protocol_sequence", "snapshots", "scope", "not_in_scope", "residue_policy", "meaning_of_pass"):
    need(v2[k] == v1[k], "field %s differs from V1" % k)
need(v2["verdict_rule"][:len(v1["verdict_rule"])] == v1["verdict_rule"], "V1 verdict_rule is not preserved verbatim as the prefix")
rel_count = {"IDENTICAL": 0, "CLARIFIED": 0, "MODIFIED": 0}
for cid, c in v2["checks"].items():
    o = v1["checks"][cid]
    rel_count[c["v1_relation"]] = rel_count.get(c["v1_relation"], 0) + 1
    need(c["name"] == o["name"], "%s renamed" % cid)
    need(c["on_fail"] == o["on_fail"], "%s failure class changed" % cid)
    if c["v1_relation"] == "IDENTICAL":
        need(c["text"] == o["text"], "%s declared IDENTICAL but its text differs" % cid)
        need("rules" not in c, "%s IDENTICAL but has rules" % cid)
    elif c["v1_relation"] == "CLARIFIED":
        need(c["text"] != o["text"] and c.get("note"), "%s declared CLARIFIED but text unchanged or no note" % cid)
    elif c["v1_relation"] == "MODIFIED":
        need(cid == "G0-C03" and "rules" in c, "only G0-C03 may be MODIFIED, with rules")
    else:
        need(False, "%s unknown relation" % cid)
need(rel_count == {"IDENTICAL": 8, "CLARIFIED": 8, "MODIFIED": 1}, "relation counts %r" % rel_count)
need([m["id"] for m in v2["v1_to_v2_mapping"]] == sorted(v2["checks"]), "mapping table is not the full ordered id list")
for m in v2["v1_to_v2_mapping"]:
    c = v2["checks"][m["id"]]
    need((m["relation"], m["v2_name"], m["v2_on_fail"], m["v1_name"], m["v1_on_fail"]) == (c["v1_relation"], c["name"], c["on_fail"], v1["checks"][m["id"]]["name"], v1["checks"][m["id"]]["on_fail"]),
         "mapping row %s disagrees with checks/V1" % m["id"])
r = v2["checks"]["G0-C03"]["rules"]
need([x["id"] for x in r["fail_when"]] == ["C03-F1", "C03-F2", "C03-F3", "C03-F4"] and [x["id"] for x in r["unevaluable_when"]] == ["C03-U1", "C03-U2"], "C03 rule ids")
need(set(r["definitions"]) >= {"completed_run", "early_stop", "parse_clean", "release_byte_written", "child_acted", "independent_evidence"}, "C03 definitions incomplete")
need(sorted(d["n"] for d in v2["deviation_disposition"]) == [1, 2, 3, 4, 5, 6], "deviation list")
need({d["n"]: d["v1_review"] for d in v2["deviation_disposition"]} == {1: "ACCEPTABLE", 2: "ACCEPTABLE", 3: "ACCEPTABLE", 4: "ACCEPTABLE", 5: "ACCEPTABLE", 6: "REQUIRES V2"}, "deviation dispositions")
need({o["id"] for o in v2["implementation_obligations"]} == {"F-8", "F-9", "F-12", "F-13", "C03"}, "implementation obligations")

# ---- MD vs JSON
need(("SHA-256 `%s`" % sha2) in md, "MD does not quote the sha256 of g0_criteria_v2.json")
need(V1_CRIT_SHA in md and V1_MD_SHA in md, "MD does not quote the V1 hashes")
chk = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (FAIL|BLOCKED) \| (IDENTICAL|CLARIFIED|MODIFIED) \| (.*) \|$", line)
    if m:
        chk[m.group(1)] = m.groups()[1:]
need(sorted(chk) == sorted(v2["checks"]), "MD check table does not list exactly the V2 checks")
for cid, (name, on_fail, rel, text) in chk.items():
    c = v2["checks"][cid]
    need((name, on_fail, rel) == (c["name"], c["on_fail"], c["v1_relation"]), "MD check row %s: name/class/relation differ from JSON" % cid)
    need(text.replace("\\|", "|") == c["text"], "MD check row %s: text differs from JSON" % cid)
mp = {}
for line in md.splitlines():
    m = re.match(r"^\| `(G0-C\d\d)` \| (\S+) \| (\S+) \| (\w+) → (\w+) \| \*\*(\w+)\*\* \| (.*) \|$", line)
    if m:
        mp[m.group(1)] = m.groups()[1:]
need(sorted(mp) == sorted(v2["checks"]), "MD mapping table does not list exactly the V2 checks")
for cid, (a, b, f1, f2, rel, note) in mp.items():
    m = next(x for x in v2["v1_to_v2_mapping"] if x["id"] == cid)
    need((a, b, f1, f2, rel) == (m["v1_name"], m["v2_name"], m["v1_on_fail"], m["v2_on_fail"], m["relation"]), "MD mapping row %s differs from JSON" % cid)
for rid in [x["id"] for x in r["fail_when"]] + [x["id"] for x in r["unevaluable_when"]]:
    need(("| `%s` |" % rid) in md, "MD lacks rule %s" % rid)
    src = next(x for x in r["fail_when"] + r["unevaluable_when"] if x["id"] == rid)
    need(src["when"].replace("|", "\\|") in md, "MD text of rule %s differs from JSON" % rid)
for n, d in ((d["n"], d) for d in v2["deviation_disposition"]):
    need(("| %d | %s | `%s` |" % (n, d["deviation"], d["v1_review"])) in md, "MD deviation row %d" % n)
need("8 项文字逐字不变（IDENTICAL），8 项只补充定义或时点（CLARIFIED，决策语义不变），1 项语义改变（MODIFIED：C03）" in md, "MD relation-count sentence")
for o in v2["implementation_obligations"]:
    need(("**%s**：%s" % (o["id"], o["requirement"])) in md, "MD obligation %s" % o["id"])
for k, v in v2["enforcement"].items():
    need(("**%s**：%s" % (k, v)) in md, "MD enforcement %s" % k)
need(v2["checks"]["G0-C03"]["rules"]["pass_when"] in md and r["precedence"] in md and r["v1_inconsistency_resolved"] in md, "MD C03 pass/precedence/inconsistency text")
need("AUTHORIZATION_E1A_GATE_G0.json" in md and "不创建" in md, "MD authorization statement")

print("V2 criteria sha256:", sha2)
print("V1 files unchanged:", sha("g0_criteria_v1.json") == V1_CRIT_SHA and sha("E1A_GATE_G0_PREREG.md") == V1_MD_SHA)
print("relations:", rel_count, "| checks:", len(v2["checks"]), "| MD check rows:", len(chk), "| MD mapping rows:", len(mp))
print("INCONSISTENCIES: %d" % len(bad))
for b in bad:
    print("  -", b)
sys.exit(0 if not bad else 1)
