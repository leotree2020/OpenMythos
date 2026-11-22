#!/usr/bin/env python3
"""Round 9: checks of the protocol v1.1 errata (items 1a-1e) against the v1 freeze commit.

  python3 -I v11_checks.py REPO_ROOT V1_COMMIT [NEW_REV]

NEW_REV omitted: the new files are read from the working tree; otherwise from git objects at NEW_REV.
Prints, for the three JSONs: version / status / frozen, whether a re-dump with indent=2 equals the file, and the
paths of every value that differs from the v1 freeze commit (required: only "version", v1 -> v1.1). Prints whether
the SEARCH_SPACE.json inline copy in the protocol equals the file. Prints the full text of the protocol lines
changed by items 1a-1e (title, status line, section 1 margin line, section 2.2 fact-hash line, G0.8, ST12) and
the v1.1 rows of section 14, and the list of protocol lines that differ from V1_COMMIT outside section 14.
Last line: RESULT: PASS / FAIL (FAIL if a JSON differs in anything but "version", a JSON is not v1.1, a re-dump
differs, the inline copy differs, or an expected changed line is missing). Writes nothing.
"""
import difflib
import json
import subprocess
import sys

ROOT, V1 = sys.argv[1], sys.argv[2]
NEW = sys.argv[3] if len(sys.argv) > 3 else None
D = "metrix/e1-pilot/"
JSONS = ("DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "SEARCH_SPACE.json")
PROTO = D + "METRIX_E1_PROTOCOL.md"


def at(rev, path):
    return subprocess.run(["git", "-C", ROOT, "cat-file", "blob", "%s:%s" % (rev, path)],
                          check=True, capture_output=True).stdout.decode("utf-8")


def new(path):
    if NEW:
        return at(NEW, path)
    with open(ROOT + "/" + path, encoding="utf-8") as fh:
        return fh.read()


def diff_paths(a, b, p=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(p + "/" + k + (" (added)" if k not in a else " (removed)"))
            else:
                out += diff_paths(a[k], b[k], p + "/" + k)
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_paths(x, y, "%s[%d]" % (p, i))
        return out
    return [] if a == b else [p + ": %r -> %r" % (a, b)]


ok = True
print("new files read from:", NEW or "working tree", "| v1 freeze commit:", V1)
for f in JSONS:
    txt_new, txt_old = new(D + f), at(V1, D + f)
    j_new, j_old = json.loads(txt_new), json.loads(txt_old)
    redump = json.dumps(j_new, indent=2, ensure_ascii=False) + "\n" == txt_new
    paths = diff_paths(j_old, j_new)
    print(f, "| version", j_new["version"], "| status", j_new["status"], "| frozen", j_new.get("frozen"),
          "| re-dump identical:", redump)
    print("  differences from v1 freeze commit:", paths)
    ok &= redump and j_new["version"] == "v1.1" and paths == ["/version: 'v1' -> 'v1.1'"]

doc = new(PROTO)
B, E = "<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->", "<!-- END INLINE COPY: SEARCH_SPACE.json -->"
inner = doc[doc.index(B) + len(B):doc.index(E)]
block = inner[len("\n```json\n"):-len("```\n")]
inline_ok = doc.count(B) == 1 and doc.count(E) == 1 and block == new(D + "SEARCH_SPACE.json")
print("inline copy identical (marked block):", inline_ok)
ok &= inline_ok

lines = doc.split("\n")
want = {
    "title": lambda s: s == "# METRIX · E1-PILOT · PROTOCOL v1.1",
    "status line": lambda s: s.startswith("| 状态 | **PROTOCOL_FROZEN（v1.1）**"),
    "section 1 margin": lambda s: s.startswith("- 不对 general damage 下 non-inferiority 结论"),
    "section 2.2 fact hash": lambda s: s.startswith("- **fact 哈希的比对方法**"),
    "G0.8": lambda s: s.startswith("| G0.8 |"),
    "ST12": lambda s: s.startswith("| ST12 |"),
}
for name, pred in want.items():
    hits = [(i + 1, s) for i, s in enumerate(lines) if pred(s)]
    print("== %s: %d line(s)" % (name, len(hits)))
    for n, s in hits:
        print("%d: %s" % (n, s))
    ok &= len(hits) == 1
rows = [(i + 1, s) for i, s in enumerate(lines) if s.startswith("| v1.1(冻结勘误) |")]
print("== section 14 v1.1 rows: %d" % len(rows))
for n, s in rows:
    print("%d: %s" % (n, s))
reason = "冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验"
print("v1.1 rows whose last cell starts with the required reason:",
      sum(1 for _, s in rows if s.rstrip(" |").split(" | ")[-1].startswith(reason)), "of", len(rows))
ok &= len(rows) == 5 and all(s.rstrip(" |").split(" | ")[-1].startswith(reason) for _, s in rows)

old = at(V1, PROTO).split("\n")
s14_new = next(i for i, s in enumerate(lines) if s.startswith("## 14."))
s14_old = next(i for i, s in enumerate(old) if s.startswith("## 14."))
print("== unified diff vs v1 freeze commit, lines before section 14 (n=0 context)")
for d in difflib.unified_diff(old[:s14_old], lines[:s14_new], "v1", "v1.1", n=0, lineterm=""):
    print(d)
print("== section 14: lines added vs v1 (removed lines must be 0)")
sd = list(difflib.ndiff(old[s14_old:], lines[s14_new:]))
print("added", sum(1 for d in sd if d.startswith("+ ")), "| removed", sum(1 for d in sd if d.startswith("- ")))
ok &= not any(d.startswith("- ") for d in sd)
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
