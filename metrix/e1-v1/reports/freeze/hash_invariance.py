"""Compare every 40/64-hex string (hashes, revisions, commits) in the protocol and the four JSON files at a base commit
with those at a target tree-ish; report strings only in one side. Usage: hash_invariance.py <base> <target>"""
import re, subprocess, sys
base, target = sys.argv[1], sys.argv[2]
FILES = ["METRIX_E1V1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "DOSE_SPACE.json", "DAMAGE_MANIFEST.json"]
rx = re.compile(r"(?<![0-9a-f])(?:[0-9a-f]{64}|[0-9a-f]{40})(?![0-9a-f])")
def show(rev, f):
    return subprocess.run(["git", "show", f"{rev}:metrix/e1-v1/{f}"], capture_output=True, check=True, text=True).stdout
ok = True
for f in FILES:
    a, b = show(base, f), show(target, f)
    A, B = set(rx.findall(a)), set(rx.findall(b))
    print(f"{f}: base {len(A)} distinct hex strings, target {len(B)}; only in base: {sorted(A - B)}; only in target: {sorted(B - A)}")
    ok &= (A == B)
print("RESULT:", "SAME hex-string sets in all five files" if ok else "DIFFERENT")
