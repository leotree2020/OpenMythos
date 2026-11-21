"""R4-D: compare with the previous round.
(1) every line inside the fenced code blocks of my round-3 report (reviews/596fcfad.../data-auditor.md) is looked up
    verbatim (after stripping) in this round's stdout files; unmatched lines are printed for manual reading
    (round-3 report lines that were abbreviated with '...' or rewritten cannot match verbatim).
(2) Executor round-3 t8 candidate-feasibility pools vs the pools in this round's a4 output.
(3) the SPLIT_MANIFEST authoring results for L1 / L2 vs this round's a4 output.
usage: python -I r4_compare_prev.py <prev_report_md> <executor_t8_txt> <split_manifest> <stdout_file> [<stdout_file> ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re

prev_md, t8, smp, outs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
now = []
for p in outs:
    now += [l.strip() for l in open(p, encoding="utf-8").read().split("\n")]
nowset = set(now)
blocks = re.findall(r"```\n(.*?)```", open(prev_md, encoding="utf-8").read(), re.S)
prev = [l.strip() for b in blocks for l in b.split("\n") if l.strip()]
prev = [l for l in prev if not l.startswith("$")]  # command lines differ only by paths
match = [l for l in prev if l in nowset]
miss = [l for l in prev if l not in nowset]
print("round-3 report: output lines in code blocks:", len(prev), "| found verbatim this round:", len(match), "| not found:", len(miss))
for l in miss:
    print("  NOT VERBATIM:", l)

# (2) Executor round-3 t8 pools vs this round's a4 pools
t8p = {}
for l in open(t8, encoding="utf-8"):
    m = re.match(r"\s+(\w+)\s+(natural|random)\s+(learned|unread)\s+K=(\d+):\s+(\d+) answers", l)
    if m:
        t8p[(m.group(1), m.group(2), m.group(3), int(m.group(4)))] = int(m.group(5))
a4p = {}
for l in now:
    m = re.match(r"\('(\w+)', '(\w+)', '(\w+)', (\d+)\) size (\d+)", l)
    if m:
        a4p[(m.group(1), m.group(2), m.group(3), int(m.group(4)))] = int(m.group(5))
print("Executor round-3 t8 pools:", len(t8p), "| this round a4 pools:", len(a4p), "| identical (keys incl. K, and sizes):", t8p == a4p)
print("  min pool size this round:", min(a4p.values()) if a4p else None, "| pools < 4:", [k for k, v in a4p.items() if v < 4])

# (3) manifest authoring results for L1 / L2
sm = json.load(open(smp, encoding="utf-8"))
lc = sm["leakage_checks"]
print("SPLIT_MANIFEST L1 authoring_result:", lc["L1_template_hash"]["authoring_result"], "| L2 authoring_result:", lc["L2_template_ngram"]["authoring_result"])
l1 = [l for l in now if l.startswith("L1 cross-set duplicate normalized hashes:")]
l2 = [l for l in now if l.startswith("L2 max Jaccard")]
print("this round:", l1, l2)
print("L1 consistent:", l1 == ["L1 cross-set duplicate normalized hashes: []"] and lc["L1_template_hash"]["authoring_result"]["duplicate_normalized_hashes"] == [])
r = lc["L2_template_ngram"]["authoring_result"]
print("L2 consistent:", l2 == [f"L2 max Jaccard word-4gram across sets: ({r['max']}, ('{r['pair'][0]}', '{r['pair'][1]}')) limit 0.25, within: True"])
