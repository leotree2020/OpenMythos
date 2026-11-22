"""R8-U: UTF-8 validity of the Executor's round-8 raw outputs (freeze-commit blobs of reports/round8/*.txt and, if
present, the untracked working-tree reports/round8/t5_frozen_hashes.txt). Informational (cosmetic finding of
r8_compare.py's first run). Data Auditor's own script; the files are read as bytes only.
Exceptions -> RESULT: FAIL (r6_guard). PASS means the check ran; invalid positions are reported, not judged.
usage: python -I r8_utf8_check.py <repo_root> <commit>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess
from r6_guard import run


def bad_positions(b):
    out, i = [], 0
    while i < len(b):
        try:
            b[i:].decode("utf-8")
            break
        except UnicodeDecodeError as e:
            out.append(i + e.start)
            i = i + e.start + 1
    return out


def main():
    repo, commit = sys.argv[1:3]
    d = "metrix/e1-pilot/reports/round8/"
    names = subprocess.run(["git", "-C", repo, "ls-tree", "--name-only", f"{commit}:{d}"], capture_output=True,
                           check=True, text=True).stdout.split()
    items = [(f"{commit[:8]}:{d}{n}", subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{d}{n}"],
                                                     capture_output=True, check=True).stdout) for n in names]
    t5 = os.path.join(repo, d, "t5_frozen_hashes.txt")
    if os.path.exists(t5):
        items.append(("working tree " + d + "t5_frozen_hashes.txt", open(t5, "rb").read()))
    for label, b in items:
        bad = bad_positions(b)
        print(f"{label}: bytes {len(b)} | valid UTF-8 {not bad} | invalid byte positions {bad}")
        for p in bad:
            ln = b.count(b"\n", 0, p) + 1
            start = b.rfind(b"\n", 0, p) + 1
            end = b.find(b"\n", p)
            line = b[start:end if end >= 0 else len(b)]
            print(f"    line {ln}: {len(line)} bytes, ends with {line[-6:]!r}; starts {line[:60].decode('utf-8', 'replace')!r}")
    return True


run(main)
