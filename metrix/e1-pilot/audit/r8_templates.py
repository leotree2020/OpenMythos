"""R8-5: the 32 template hashes of SPLIT_MANIFEST.json (freeze commit): normalized string, normalized_sha256 per
template, and template_set_sha256. Data Auditor's own script; no Executor code is imported, called or copied.
Standard library only. Templates are only normalized and hashed, never instantiated (no question text, no TEST data).
Exceptions -> RESULT: FAIL (r6_guard).

Rule (SPLIT_MANIFEST template_freeze.normalization / identity, protocol section 3 "模板冻结"):
  normalized = text with {E} -> <ENTITY>, {A} -> <ANSWER>; lowercase; every character outside [a-z0-9<> ] -> space;
               runs of spaces collapsed to one; (leading / trailing space removed - see ALT lines)
  normalized_sha256 = sha256(normalized.encode("utf-8"))
  template_set_sha256 = sha256("\n".join(sorted(normalized_sha256 values)).encode("utf-8"))
Also: the template texts equal the protocol 2.4 table of the same commit (cell by cell, in order), 32 templates,
per relation 1 TRAIN + 2 DEV + 3 TEST + 2 Y (1 Y_ENTITY + 1 Y_ANSWER), template_id = <relation>.<kind>.<n>.
Prints AUDIT_VALUE lines (one per template and the set hash).
PASS iff every recomputed normalized string and normalized_sha256 equal the manifest, the set hash equals
template_set_sha256, and the texts equal the protocol table.
usage: python -I r8_templates.py <repo_root> <commit>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, json, re, subprocess
from collections import Counter
from r6_guard import run

RELS = ["capital", "currency", "founder", "river"]


def git_blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], capture_output=True, check=True).stdout


def normalize(text, strip=True):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(ch if ("a" <= ch <= "z" or "0" <= ch <= "9" or ch in "<> ") else " " for ch in s)
    s = re.sub(" +", " ", s)
    return s.strip(" ") if strip else s


def h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    repo, commit = sys.argv[1:3]
    ok = True
    sm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/SPLIT_MANIFEST.json"))
    proto = git_blob(repo, commit, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md").decode("utf-8")
    tf = sm["template_freeze"]
    print("template_freeze.normalization:", tf["normalization"])
    print("template_freeze.identity     :", tf["identity"])
    T = sm["templates"]
    ids = [t["template_id"] for t in T]
    print("templates:", len(T), "| distinct ids:", len(set(ids)))
    ok &= len(T) == 32 and len(set(ids)) == 32
    cnt = Counter((t["relation"], t["kind"]) for t in T)
    shape = all(cnt[(r, k)] == n for r in RELS for k, n in
                (("TRAIN", 1), ("DEV", 2), ("TEST", 3), ("Y_ENTITY", 1), ("Y_ANSWER", 1)))
    print("per relation 1 TRAIN, 2 DEV, 3 TEST, 1 Y_ENTITY, 1 Y_ANSWER:", shape)
    ok &= shape
    idfmt = all(re.fullmatch(rf"{t['relation']}\.{t['kind']}\.\d", t["template_id"]) for t in T)
    setfield = all(t["set"] == ("Y" if t["kind"].startswith("Y_") else t["kind"]) for t in T)
    print("template_id format <relation>.<kind>.<n>:", idfmt, "| set field consistent with kind:", setfield)
    ok &= idfmt and setfield

    # protocol 2.4 table
    table = {}
    for line in proto.splitlines():
        m = re.fullmatch(r"\| (capital|currency|founder|river) \| (TRAIN|DEV|TEST|Y) \| (.+) \|", line)
        if m:
            table[(m.group(1), m.group(2))] = [x.strip() for x in m.group(3).split(" / ")]
    print("protocol 2.4 table rows parsed:", len(table))
    tab_ok = len(table) == 16
    for r in RELS:
        for st in ("TRAIN", "DEV", "TEST", "Y"):
            mine = [t["text"] for t in T if t["relation"] == r and t["set"] == st]
            eq = mine == table.get((r, st))
            tab_ok &= eq
            if not eq:
                print("  MISMATCH protocol table vs manifest:", r, st, table.get((r, st)), mine)
    print("manifest template texts == protocol 2.4 table (in order):", tab_ok)
    ok &= tab_ok

    n_ok = 0
    mine_h = []
    for t in T:
        n = normalize(t["text"])
        hh = h(n)
        mine_h.append(hh)
        eq = n == t["normalized"] and hh == t["normalized_sha256"]
        n_ok += eq
        print(f"  {t['template_id']:<20} {hh} | manifest {t['normalized_sha256']} | normalized equal {n == t['normalized']} "
              f"| MATCH {eq} | {n!r}")
        print(f"AUDIT_VALUE template_normalized_sha256:{t['template_id']} {hh}")
    print(f"templates whose normalized string and normalized_sha256 match: {n_ok}/32")
    ok &= n_ok == 32
    set_h = h("\n".join(sorted(mine_h)))
    print(f"template_set_sha256 {set_h} | manifest {tf['template_set_sha256']} | MATCH {set_h == tf['template_set_sha256']}")
    print(f"AUDIT_VALUE template_set_sha256 {set_h}")
    ok &= set_h == tf["template_set_sha256"]
    # set hash also from the manifest's own normalized_sha256 values
    set_m = h("\n".join(sorted(t["normalized_sha256"] for t in T)))
    print("template_set_sha256 from the manifest's own normalized_sha256 values:", set_m, "| MATCH", set_m == tf["template_set_sha256"])
    ok &= set_m == tf["template_set_sha256"]
    print("ALT no strip (trailing space kept):", sum(h(normalize(t["text"], strip=False)) == t["normalized_sha256"] for t in T), "/32 match")
    print("ALT set hash with a final newline:", h("\n".join(sorted(mine_h)) + "\n"), "| equals manifest:",
          h("\n".join(sorted(mine_h)) + "\n") == tf["template_set_sha256"])
    print("ALT set hash unsorted (manifest order):", h("\n".join(mine_h)), "| equals manifest:",
          h("\n".join(mine_h)) == tf["template_set_sha256"])
    # informational: L1 on the recomputed hashes (template-only; no TEST data)
    sets = {}
    for t, hh in zip(T, mine_h):
        sets.setdefault(t["set"], set()).add(hh)
    names = sorted(sets)
    dup = [(a, b, sorted(sets[a] & sets[b])) for i, a in enumerate(names) for b in names[i + 1:] if sets[a] & sets[b]]
    print("informational L1 (pairwise intersections of TRAIN/DEV/TEST/Y normalized_sha256):", dup,
          "| distinct hashes", len(set(mine_h)))
    return ok


run(main)
