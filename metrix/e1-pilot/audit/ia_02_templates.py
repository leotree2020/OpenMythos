"""IA-2 (audit item 1, templates): the 32 templates of SPLIT_MANIFEST.json at the freeze commit.
  normalized = text with {E} -> <ENTITY>, {A} -> <ANSWER>; lowercase; every character outside [a-z0-9<> ] -> space;
               runs of spaces collapsed to one (and the ends trimmed - see the "no trim" line)
  normalized_sha256 = sha256(normalized UTF-8);  template_set_sha256 = sha256("\n".join(sorted(normalized_sha256)))
Also: manifest template texts == protocol 2.4 table (same commit, in order); per relation 1 TRAIN, 2 DEV, 3 TEST,
1 Y_ENTITY, 1 Y_ANSWER.  Templates are only normalized and hashed here, never instantiated.
Data Auditor's own script (standard library); no Executor code imported, called or copied.
usage: python -I ia_02_templates.py <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from collections import Counter
from ia_common import RELS, sha, frozen_json, frozen_protocol, run


def normalize(text, trim=True):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(c if (c in "abcdefghijklmnopqrstuvwxyz0123456789<> ") else " " for c in s)
    s = re.sub(r" {2,}", " ", s)
    return s.strip(" ") if trim else s


def main():
    repo = sys.argv[1]
    ok = True
    sm = frozen_json(repo, "SPLIT_MANIFEST.json")
    proto = frozen_protocol(repo)
    T = sm["templates"]
    print("templates:", len(T), "| distinct template_id:", len({t["template_id"] for t in T}))
    ok &= len(T) == 32 and len({t["template_id"] for t in T}) == 32
    cnt = Counter((t["relation"], t["kind"]) for t in T)
    shape = all(cnt[(r, k)] == n for r in RELS for k, n in (("TRAIN", 1), ("DEV", 2), ("TEST", 3), ("Y_ENTITY", 1), ("Y_ANSWER", 1)))
    print("per relation 1 TRAIN / 2 DEV / 3 TEST / 1 Y_ENTITY / 1 Y_ANSWER:", shape)
    ok &= shape
    table = {}
    for line in proto.splitlines():
        m = re.fullmatch(r"\| (capital|currency|founder|river) \| (TRAIN|DEV|TEST|Y) \| (.+) \|", line)
        if m:
            table[(m.group(1), m.group(2))] = [x.strip() for x in m.group(3).split(" / ")]
    tab_ok = len(table) == 16 and all(
        [t["text"] for t in T if t["relation"] == r and t["set"] == s] == table.get((r, s))
        for r in RELS for s in ("TRAIN", "DEV", "TEST", "Y"))
    print("protocol 2.4 table rows:", len(table), "| manifest texts == table (in order):", tab_ok)
    ok &= tab_ok
    mine = []
    for t in T:
        n = normalize(t["text"])
        h = sha(n.encode("utf-8"))
        mine.append(h)
        eq = n == t["normalized"] and h == t["normalized_sha256"]
        ok &= eq
        print(f"  {t['template_id']:<20} {h} | manifest {t['normalized_sha256']} | MATCH {eq} | {n!r}")
        print(f"AUDIT_VALUE template:{t['template_id']} {h}")
    print("templates matching:", sum(h == t["normalized_sha256"] for h, t in zip(mine, T)), "/ 32")
    s = sha("\n".join(sorted(mine)).encode("utf-8"))
    exp = sm["template_freeze"]["template_set_sha256"]
    print(f"template_set_sha256 recomputed {s} | manifest {exp} | MATCH {s == exp}")
    print(f"AUDIT_VALUE template_set_sha256 {s}")
    ok &= s == exp
    print("normalization text of the manifest:", sm["template_freeze"]["normalization"])
    print("no trim: templates matching", sum(sha(normalize(t["text"], False).encode()) == t["normalized_sha256"] for t in T), "/ 32",
          "| set hash with a final newline equals manifest:", sha(("\n".join(sorted(mine)) + "\n").encode()) == exp)
    return bool(ok)


run(main)
