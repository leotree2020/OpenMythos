"""IA-12 (implementation stage A, audit round 2): byte identity.
  A. the 8 data files of gen4 vs gen1: size, sha256 and full byte comparison per file; both directories contain exactly
     these 8 files + leakage_report.json; the gen1 sha256 values are also compared with the byte_sha256 values that the
     round-1 run of ia_10_compare.py recorded for gen1 (stdout/impl_a/10_ia_compare.txt), i.e. gen1 is unchanged since
     round 1.
  B. leakage_report.json gen4 vs gen1 (bytes), and coverage: every leaf of the gen4 report is listed; the leaves that
     ia_07_leakage.py does not compare one by one are named and checked here (L6.detail.part must name the anchor text
     vs general DEV comparison, i.e. the Gate 0 part).
  C. the auditor's own regeneration of round 2 (<my_out_r2>) vs round 1 (<my_out_r1>): byte identity per file.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_12_r2_bytes.py <audit_dir> <gen1> <gen4> <my_out_r1> <my_out_r2>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from ia_common import sha, run

DATA = ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
        "general_dev.jsonl", "anchor_text.jsonl"]
COMPARED_BY_IA07 = {"part", "result", "frozen_commit", "checks.L1.detail.shared_hashes", "checks.L2.detail.pair",
                    "checks.L2.detail.n", "checks.L3a.detail.strings", "checks.L3a.detail.corpora", "checks.L3a.detail.found",
                    "checks.L3b.detail.strings", "checks.L3b.detail.found", "checks.L4.detail.questions",
                    "checks.L4.detail.corpora", "checks.L4.detail.found", "checks.L4.detail.part",
                    "checks.L5.detail.fact_id_overlap", "checks.L5.detail.duplicate_strings", "checks.L5.detail.learned",
                    "checks.L5.detail.unread", "checks.L5.detail.strings", "checks.L6.detail.anchor_documents",
                    "checks.L6.detail.windows", "checks.L6.detail.n", "checks.L6.detail.examples",
                    "checks.L6.detail.report_only_token_id_ngrams"} | {
    f"checks.{k}.{f}" for k in ("L1", "L2", "L3a", "L3b", "L4", "L5", "L6") for f in ("value", "limit", "within_limit")}


def leaves(obj, pre=""):
    if isinstance(obj, dict) and obj:
        for k, v in obj.items():
            yield from leaves(v, f"{pre}.{k}" if pre else k)
    else:
        yield pre, obj


def main():
    audit, gen1, gen4, r1, r2 = sys.argv[1:6]
    ok = True
    print("== A. gen4 vs gen1, the 8 data files")
    l1, l4 = sorted(os.listdir(gen1)), sorted(os.listdir(gen4))
    exp = sorted(DATA + ["leakage_report.json"])
    print(f"gen1 listing {l1} == expected {l1 == exp} | gen4 listing {l4} == expected {l4 == exp}")
    ok &= l1 == exp and l4 == exp
    r1_out = open(os.path.join(audit, "stdout/impl_a/10_ia_compare.txt"), encoding="utf-8").read()
    rec = dict(re.findall(r"^  (\S+): byte_sha256 ([0-9a-f]{64}) \|", r1_out, re.M))
    for n in DATA:
        b1, b4 = open(os.path.join(gen1, n), "rb").read(), open(os.path.join(gen4, n), "rb").read()
        same = b1 == b4
        r1_same = rec.get(n) == sha(b1)
        ok &= same and r1_same
        print(f"  {n}: gen1 {len(b1)} bytes sha256 {sha(b1)} | gen4 {len(b4)} bytes sha256 {sha(b4)} | byte-identical {same} "
              f"| gen1 == round-1 record {rec.get(n)} {r1_same}")
    print(f"8 data files gen4 byte-identical to gen1: {all(open(os.path.join(gen1, n), 'rb').read() == open(os.path.join(gen4, n), 'rb').read() for n in DATA)}")

    print("\n== B. leakage_report.json")
    b1, b4 = open(os.path.join(gen1, "leakage_report.json"), "rb").read(), open(os.path.join(gen4, "leakage_report.json"), "rb").read()
    print(f"gen1 sha256 {sha(b1)} | gen4 sha256 {sha(b4)} | byte-identical {b1 == b4} | gen1 == round-1 record "
          f"{rec.get('leakage_report.json')} {rec.get('leakage_report.json') == sha(b1)}")
    rep = json.loads(b4)
    lv = list(leaves(rep))
    for p, v in lv:
        print(f"  leaf {p} = {json.dumps(v, ensure_ascii=False)} | compared one by one in ia_07 {p in COMPARED_BY_IA07}")
    rest = [(p, v) for p, v in lv if p not in COMPARED_BY_IA07]
    missing = sorted(COMPARED_BY_IA07 - {p for p, _ in lv})
    print(f"leaves {len(lv)} | not compared in ia_07: {rest} | ia_07 comparisons without a leaf: {missing}")
    ok &= missing == [] and rest == [("checks.L6.detail.part", "DEV (anchor_text vs general_dev)")]
    print("checks.L6.detail.part names the Gate 0 part (anchor text vs general DEV windows, no TEST):",
          dict(rest).get("checks.L6.detail.part") == "DEV (anchor_text vs general_dev)")

    print("\n== C. auditor regeneration round 2 vs round 1")
    f1, f2 = sorted(os.listdir(r1)), sorted(os.listdir(r2))
    print(f"round 1 files {f1} | round 2 files {f2} | same names {f1 == f2}")
    ok &= f1 == f2
    for n in f2:
        a, b = open(os.path.join(r1, n), "rb").read(), open(os.path.join(r2, n), "rb").read()
        ok &= a == b
        print(f"  {n}: round 1 sha256 {sha(a)} | round 2 sha256 {sha(b)} | byte-identical {a == b}")
    return bool(ok)


run(main)
