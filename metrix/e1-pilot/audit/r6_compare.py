"""R6-A/B/C FINAL COMPARISON: my results (r6_anchor.py, r6_general.py outputs) vs the Executor's round-6 outputs.
Executor files are read here only as comparison targets, after my own computation; nothing of theirs is executed.
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).
Compared: number of windows, length distribution, both general DEV hashes, anchor hash, rows by split, decoded-row
counts, and per unit (ws, w, tok) the unit totals, shared counts for n = 1..13 and the longest shared n, the L6 line,
RESULT and exit code of t2_l6_check.txt; the Executor's general_dev.json (ids and texts per window) and anchor.json.
usage: python -I r6_compare.py <my_general_summary.json> <my_anchor.json> <exec_t2_l6_check.txt>
                               <exec_general_dev.json> <exec_anchor.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, json, re
from common import sha, canon
from r6_guard import run


def main():
    mine = json.load(open(sys.argv[1], encoding="utf-8"))
    my_anchor = json.load(open(sys.argv[2], encoding="utf-8"))
    t2 = open(sys.argv[3], encoding="utf-8").read()
    ex_gen = json.load(open(sys.argv[4], encoding="utf-8"))
    ex_anc = json.load(open(sys.argv[5], encoding="utf-8"))
    res = []

    def cmp(label, a, b):
        res.append(a == b)
        print(f"{'EQUAL' if a == b else 'DIFFERENT':9s} | {label}: mine {a} | executor {b}")

    g = lambda pat: re.search(pat, t2).group(1)
    cmp("windows", len(mine["windows"]), int(g(r"general DEV windows: (\d+);")))
    cmp("length distribution", {int(k): v for k, v in mine["lengths"].items()},
        ast.literal_eval(g(r"protocol-tokenizer lengths: (\{[^}]*\})")))
    cmp("texts canonical sha256", mine["texts_sha"], g(r"list of window texts[^:]*: ([0-9a-f]{64})"))
    cmp("ids canonical sha256", mine["ids_sha"], g(r"list of token-id lists[^:]*: ([0-9a-f]{64})"))
    cmp("anchor canonical sha256", mine["anchor_sha"], g(r"anchor texts: 512; canonical sha256 ([0-9a-f]{64})"))
    cmp("rows by split", mine["rows_by_split"], ast.literal_eval(g(r"eval_sets rows by split: (\{[^}]*\})")))
    cmp("rows decoded by split", mine["decoded"], ast.literal_eval(g(r"rows decoded by split: (\{[^}]*\})")))
    cmp("test rows decoded", mine["decoded"].get("test", 0), int(g(r"test rows decoded: (\d+)")))
    for unit in ("ws", "w", "tok"):
        m = re.search(r"unit %s\s*\| units: anchor (\d+), general (\d+) \| shared n-grams n=1\.\.13: (\[[^\]]*\]) \| "
                      r"longest shared n <= 13: (\d+)" % unit, t2)
        u = mine["units"][unit]
        cmp(f"unit {unit} (anchor units, general units, shared n=1..13, longest)",
            (u["anchor_units"], u["general_units"], u["shared"], u["longest"]),
            (int(m.group(1)), int(m.group(2)), json.loads(m.group(3)), int(m.group(4))))
    cmp("judged L6 count (str.split() 13-grams)", mine["units"]["ws"]["shared"][12],
        int(g(r"L6 \(DEV part\) shared word 13-grams \(word = str\.split\(\), unit ws\): (\d+); limit 0")))
    cmp("report-only Qwen token 13-grams", mine["units"]["tok"]["shared"][12], int(g(r"Qwen token 13-grams \(unit tok\) (\d+)")))
    body = t2.split("l6_check.py --eval-sets", 1)[1]
    cmp("RESULT line and exit of the l6_check run", ("RESULT: PASS", "exit=0"),
        (re.search(r"^RESULT: \w+", body, re.M).group(0), re.search(r"^exit=\d+", body, re.M).group(0)))

    print("== Executor general_dev.json:", type(ex_gen).__name__, len(ex_gen), "entries; keys of entry 0:",
          sorted(ex_gen[0]) if isinstance(ex_gen, list) else sorted(ex_gen))
    cmp("general_dev.json (domain, doc_id) order", [(w["domain"], w["doc_id"]) for w in mine["windows"]],
        [(e["domain"], e["doc_id"]) for e in ex_gen])
    cmp("general_dev.json ids equal per window (count of equal windows)", 100,
        sum(a["ids"] == b["ids"] for a, b in zip(mine["windows"], ex_gen)))
    cmp("general_dev.json texts equal per window (count of equal windows)", 100,
        sum(a["text"] == b["text"] for a, b in zip(mine["windows"], ex_gen)))
    ex_texts = ex_anc["texts"] if isinstance(ex_anc, dict) else ex_anc
    cmp("anchor.json texts canonical sha256", sha(canon(my_anchor)), sha(canon(ex_texts)))
    print(f"compared items: {len(res)}, equal: {sum(res)}, different: {len(res) - sum(res)}")
    return all(res)


if __name__ == "__main__":
    run(main)
