"""R5-D: this round's stdout files vs my previous round's stdout files (audit/stdout/<prev>/), same scripts.
The 3 header lines (host/time, note, command line) are dropped; scratch-directory paths are replaced by <S>.
Every remaining line that differs is printed (unified diff, no context).
usage: python -I r5_compare_prev.py <prev_dir> <now_dir> <prev_file>=<now_file> [...]"""
import difflib, os, re, sys

prev_dir, now_dir, pairs = sys.argv[1], sys.argv[2], sys.argv[3:]
SP = re.compile(r"/tmp/claude-0/-home-user/[0-9a-f-]+/scratchpad")


def body(p):
    lines = open(p, encoding="utf-8").read().split("\n")
    assert lines[0].startswith("# Data Auditor run") and lines[2].startswith("$ ")
    return [SP.sub("<S>", l) for l in lines[3:]]


total = 0
for pr in pairs:
    a, b = pr.split("=")
    A, B = body(os.path.join(prev_dir, a)), body(os.path.join(now_dir, b))
    d = [l for l in difflib.unified_diff(A, B, lineterm="", n=0) if not l.startswith(("---", "+++", "@@"))]
    total += len(d)
    print(f"{a} ({len(A)} lines) vs {b} ({len(B)} lines): identical after path normalisation: {not d} | differing lines: {len(d)}")
    for l in d:
        print("   ", l[:400])
print("differing lines in total:", total)
