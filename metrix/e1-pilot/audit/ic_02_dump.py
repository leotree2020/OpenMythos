"""IC-2 (implementation stage B, round 2, task 2, first part): the Executor's dump after the fixes (audit_dump_c.json).
  - sha256 of audit_dump_c.json == the value written in reports/impl_b/t6_fix_round.txt ("written <SCRATCH>/
    audit_dump_c.json sha256 ...") == the value of round 1 in reports/impl_b/t5_dump_for_audit.txt;
  - audit_dump_c.json == audit_dump_b.json byte for byte (my own comparison; t6 records `cmp` exit 0);
  - the sha256 of audit_dump_b.json still equals the round-1 value (the file ib_03 / ib_04 compared in round 1);
  - the keys and sizes of the dump.
The content comparisons themselves are re-run by ic_03_scoring.py and ib_04_training.py on audit_dump_c.json.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ic_02_dump.py <repo_root> <audit_dump_b.json> <audit_dump_c.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from ia_common import file_sha, run

T5 = "metrix/e1-pilot/reports/impl_b/t5_dump_for_audit.txt"
T6 = "metrix/e1-pilot/reports/impl_b/t6_fix_round.txt"


def main():
    repo, pb, pc = sys.argv[1:4]
    ok = True
    t5 = open(os.path.join(repo, T5), encoding="utf-8").read()
    t6 = open(os.path.join(repo, T6), encoding="utf-8").read()
    r5 = re.findall(r"^written <SCRATCH>/audit_dump_b\.json sha256 ([0-9a-f]{64})$", t5, re.M)
    r6 = re.findall(r"^written <SCRATCH>/audit_dump_c\.json sha256 ([0-9a-f]{64})$", t6, re.M)
    cmp_line = re.search(r"^\$ cmp <SCRATCH>/audit_dump_b\.json <SCRATCH>/audit_dump_c\.json\nexit=(\d+)$", t6, re.M)
    print(f"t5 recorded (audit_dump_b.json): {r5} | t6 recorded (audit_dump_c.json): {r6} | t6 cmp exit {cmp_line.group(1) if cmp_line else None}")
    ok &= len(r5) == 1 and len(r6) == 1 and cmp_line is not None and cmp_line.group(1) == "0"
    hb, hc = file_sha(pb), file_sha(pc)
    print(f"audit_dump_b.json sha256 {hb} | == t5 {hb == r5[0]}")
    print(f"audit_dump_c.json sha256 {hc} | == t6 {hc == r6[0]} | == t5 {hc == r5[0]}")
    ok &= hb == r5[0] and hc == r6[0] == r5[0]
    bb, bc = open(pb, "rb").read(), open(pc, "rb").read()
    print(f"bytes: b {len(bb)} | c {len(bc)} | identical {bb == bc}")
    ok &= bb == bc
    d = json.loads(bc)
    print(f"keys {sorted(d)} | qa_inputs {len(d['qa_inputs'])} | cb_inputs {len(d['cb_inputs'])} | training_sequences "
          f"{ {k: len(v) for k, v in sorted(d['training_sequences'].items())} } | batch_schedule {sorted(d['batch_schedule'])} "
          f"| anchor_docs {len(d['anchor_docs'])} | lr_factor {len(d['lr_factor'])}")
    ok &= len(d["qa_inputs"]) == 1280 and len(d["cb_inputs"]) == 480 and len(d["anchor_docs"]) == len(d["lr_factor"]) == 300
    return bool(ok)


run(main)
