"""ID-2 (implementation stage B, fix commit, task 2): the Executor's dump after the fixes (audit_dump_d.json).
  - sha256 of audit_dump_d.json == the value written in reports/impl_b/t8_fix_commit.txt ("written <SCRATCH>/
    audit_dump_d.json sha256 ...") == the round-1 value in reports/impl_b/t5_dump_for_audit.txt (audit_dump_b.json)
    == the round-2 value in reports/impl_b/t6_fix_round.txt (audit_dump_c.json);
  - audit_dump_d.json == audit_dump_b.json byte for byte (my own comparison; t8 records `cmp` exit 0), and == the
    round-2 audit_dump_c.json;
  - the sha256 of audit_dump_b.json still equals the round-1 value (the file ib_03 / ib_04 compared in round 1,
    re-compared as audit_dump_c.json by ic_03 / ib_04 in round 2);
  - the t8 dump line (counts printed by the Executor) and the keys / sizes of the dump.
Data Auditor's own script (adapted from my ic_02_dump.py); no Executor code imported, called or copied.
usage: python -I id_02_dump.py <repo_root> <audit_dump_b.json> <audit_dump_c.json> <audit_dump_d.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from ia_common import file_sha, run

T5 = "metrix/e1-pilot/reports/impl_b/t5_dump_for_audit.txt"
T6 = "metrix/e1-pilot/reports/impl_b/t6_fix_round.txt"
T8 = "metrix/e1-pilot/reports/impl_b/t8_fix_commit.txt"


def main():
    repo, pb, pc, pd = sys.argv[1:5]
    ok = True
    t5 = open(os.path.join(repo, T5), encoding="utf-8").read()
    t6 = open(os.path.join(repo, T6), encoding="utf-8").read()
    t8 = open(os.path.join(repo, T8), encoding="utf-8").read()
    r5 = re.findall(r"^written <SCRATCH>/audit_dump_b\.json sha256 ([0-9a-f]{64})$", t5, re.M)
    r6 = re.findall(r"^written <SCRATCH>/audit_dump_c\.json sha256 ([0-9a-f]{64})$", t6, re.M)
    r8 = re.findall(r"^written <SCRATCH>/audit_dump_d\.json sha256 ([0-9a-f]{64})$", t8, re.M)
    cmd8 = re.findall(r"^\$ <SCRATCH>/venv/bin/python metrix/e1-pilot/reports/impl_b/dump_for_audit\.py .*$", t8, re.M)
    cnt8 = re.findall(r"^qa_inputs \d+, cb_inputs \d+, .*$", t8, re.M)
    cmp8 = re.search(r"^\$ cmp <SCRATCH>/audit_dump_b\.json <SCRATCH>/audit_dump_d\.json\nexit=(\d+)$", t8, re.M)
    print(f"t8 dump command: {cmd8}")
    print(f"t8 dump counts line: {cnt8}")
    print(f"t5 recorded (audit_dump_b.json): {r5} | t6 recorded (audit_dump_c.json): {r6} | t8 recorded (audit_dump_d.json): {r8} | "
          f"t8 cmp b/d exit {cmp8.group(1) if cmp8 else None}")
    ok &= len(r5) == len(r6) == len(r8) == 1 and len(cmd8) == 1 and "--data <SCRATCH>/data_d" in cmd8[0]
    ok &= cmp8 is not None and cmp8.group(1) == "0"
    hb, hc, hd = file_sha(pb), file_sha(pc), file_sha(pd)
    print(f"audit_dump_b.json sha256 {hb} | == t5 {hb == r5[0]}")
    print(f"audit_dump_c.json sha256 {hc} | == t6 {hc == r6[0]}")
    print(f"audit_dump_d.json sha256 {hd} | == t8 {hd == r8[0]} | == t5 {hd == r5[0]} | == t6 {hd == r6[0]}")
    ok &= hb == r5[0] and hc == r6[0] and hd == r8[0] == r5[0] == r6[0]
    bb, bc, bd = open(pb, "rb").read(), open(pc, "rb").read(), open(pd, "rb").read()
    print(f"bytes: b {len(bb)} | c {len(bc)} | d {len(bd)} | d == b byte for byte {bd == bb} | d == c byte for byte {bd == bc}")
    ok &= bd == bb and bd == bc
    d = json.loads(bd)
    sizes = (len(d["qa_inputs"]), len(d["cb_inputs"]), {k: len(v) for k, v in sorted(d["training_sequences"].items())},
             len(d["batch_schedule"]), len(d["anchor_docs"]))
    print(f"keys {sorted(d)} | qa_inputs {sizes[0]} | cb_inputs {sizes[1]} | training_sequences {sizes[2]} | batch_schedule "
          f"{sorted(d['batch_schedule'])} ({sizes[3]}) | anchor_docs {sizes[4]} | lr_factor {len(d['lr_factor'])}")
    want = f"qa_inputs {sizes[0]}, cb_inputs {sizes[1]}, training sequences {sizes[2]}, schedules {sizes[3]}, anchor steps {sizes[4]}"
    print(f"t8 counts line == the dump's sizes ({want!r}): {cnt8 == [want]}")
    ok &= cnt8 == [want] and sizes[0] == 1280 and sizes[1] == 480 and sizes[4] == len(d["lr_factor"]) == 300
    return bool(ok)


run(main)
