#!/usr/bin/env python3
"""Round 9, item 6: check metrix/e1-pilot/PROTOCOL_FROZEN (working tree) against git objects.

  python3 -I protocol_frozen_check.py REPO_ROOT V11_COMMIT V1_COMMIT OLD_REV

Checks (each printed as name: True/False with the compared values):
  - the file is valid UTF-8; its first non-empty line after the title is "当前有效版本：v1.1";
  - the v1.1 section names V11_COMMIT in full, its parent and commit time as git reports them, the tag
    metrix-e1-pilot-frozen-v1.1 "(由 Owner 推送)" and "Owner 批准，2026-11-22 09:44 UTC";
  - the four sha256 lines of the v1.1 section equal sha256(git cat-file blob V11_COMMIT:<path>), and the four
    lines of the v1 section equal those of V1_COMMIT;
  - the v1 section equals the file at OLD_REV except: the title line became the section heading, the
    "Owner 批准" line follows it, the paths sentence moved to the top, "## " headings became "### ", and the tag
    line's parenthesis "(与本文件所在提交同时推送)" became "(由 Owner 在 Codespace 推送)";
  - every 64-hex value in the file is one of: the v1 file's values, the eight sha256 values above.
Last line: RESULT: PASS / FAIL. Writes nothing.
"""
import hashlib
import re
import subprocess
import sys

ROOT, C11, C1, OLD = sys.argv[1:5]
PATH = "metrix/e1-pilot/PROTOCOL_FROZEN"
FILES = ("metrix/e1-pilot/METRIX_E1_PROTOCOL.md", "metrix/e1-pilot/DATA_MANIFEST.json",
         "metrix/e1-pilot/SPLIT_MANIFEST.json", "metrix/e1-pilot/SEARCH_SPACE.json")


def git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], check=True, capture_output=True).stdout


ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print("%s: %s%s" % (name, bool(cond), (" | " + detail) if detail else ""))


raw = open(ROOT + "/" + PATH, "rb").read()
try:
    text = raw.decode("utf-8")
    check("valid UTF-8", True, "bytes %d | sha256 %s" % (len(raw), hashlib.sha256(raw).hexdigest()))
except UnicodeDecodeError as e:
    check("valid UTF-8", False, str(e))
    print("RESULT: FAIL")
    sys.exit(1)
lines = text.split("\n")
first = next(l for l in lines[1:] if l.strip())
check("first line after title", first == "当前有效版本：v1.1", repr(first))

i11, i1 = lines.index("## v1.1(当前有效)"), next(i for i, l in enumerate(lines) if l.startswith("## v1(METRIX"))
check("section order", 0 < i11 < i1, "v1.1 at line %d, v1 at line %d" % (i11 + 1, i1 + 1))
s11, s1 = "\n".join(lines[i11:i1]), "\n".join(lines[i1:])

parent = git("log", "-1", "--format=%P", C11).decode().strip()
ctime = git("log", "-1", "--date=format-local:%Y-%m-%d %H:%M:%S", "--format=%ad|%cd", C11).decode().strip()
check("v1.1 full hash", "| v1.1 冻结提交(完整 hash) | `%s` |" % C11 in s11, C11)
check("v1.1 parent", "| 父提交 | `%s` |" % parent in s11, parent)
a, c = ctime.split("|")
check("v1.1 commit time", a == c and "| 提交时间(author / committer) | %s UTC |" % a in s11, ctime)
check("v1.1 tag", "| 标签 | `metrix-e1-pilot-frozen-v1.1`,指向 v1.1 冻结提交(由 Owner 推送) |" in s11)
check("v1.1 approval", "\nOwner 批准，2026-11-22 09:44 UTC\n" in s11)

blocks = re.findall(r"```\n(.*?)```", text, re.S)
check("two sha256 blocks", len(blocks) == 2, "found %d" % len(blocks))
known = set()
for label, commit, block in (("v1.1", C11, blocks[0]), ("v1", C1, blocks[1])):
    want = ["%s  %s" % (hashlib.sha256(git("cat-file", "blob", "%s:%s" % (commit, f))).hexdigest(), f) for f in FILES]
    got = block.rstrip("\n").split("\n")
    for w in want:
        print("  %s %s git cat-file: %s" % (label, commit[:8], w))
    check("%s sha256 lines == git cat-file %s" % (label, commit[:8]), got == want)
    known |= {w.split()[0] for w in want}

old = git("cat-file", "blob", "%s:%s" % (OLD, PATH)).decode("utf-8").split("\n")
body = [("#" + l) if l.startswith("## ") else l for l in old[5:]]
exp = ["## v1(METRIX-E1-PILOT protocol v1;保留为记录)", "", old[2]] + body
exp = [l.replace("(与本文件所在提交同时推送)", "(由 Owner 在 Codespace 推送)") if l.startswith("| 标签 |") else l for l in exp]
check("v1 section == file at %s with the stated edits only" % OLD[:8], lines[i1:] == exp,
      "old title %r | old approval %r | old paths sentence %r" % (old[0], old[2], old[4]))
check("paths sentence at top", lines[4].startswith(old[4]))
tag_lines = [l for l in lines[i1:] if l.startswith("| 标签 |")]
print("  v1 tag line:", tag_lines)

old_hex = set(re.findall(r"\b[0-9a-f]{64}\b", "\n".join(old)))
all_hex = set(re.findall(r"\b[0-9a-f]{64}\b", text))
check("every 64-hex value known", all_hex <= old_hex | known,
      "values %d | not known %s" % (len(all_hex), sorted(all_hex - old_hex - known)))
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
