"""R5-C: the round-4 blind-test records committed in round 5 (reports/round4/blind/) vs the sha256 / byte-size record
committed in round 4 (reports/round4/t6_blind_timeline.txt). Data Auditor's own script; Executor code is not used.
- t6 is read from the git object of <t6_commit> (the round-4 commit that added it) and compared with HEAD and the working tree
- per file: sha256 and byte count of the working-tree file and of the HEAD git object, vs the t6 sha256sum / ls -l lines
- commit hash named in each prompt file vs t6's wip-a..wip-e records (for-each-ref and git log lines); base hash vs t6 parent
- extra: each file's bytes vs the matching tool-call input in source_events.jsonl; Write/Agent event times vs t6 mtimes
- git: the commit(s) that added the blind/ files; whether the wip commits exist in this clone
usage: python -I r5_blind.py <repo_root> <t6_commit> <head>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess
from common import sha

repo, t6c, head = sys.argv[1:4]
B = "metrix/e1-pilot/reports/round4/blind/"
T6 = "metrix/e1-pilot/reports/round4/t6_blind_timeline.txt"


def git(*a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True)
    if check and r.returncode:
        raise SystemExit(r.stderr.decode())
    return r


t6 = git("show", f"{t6c}:{T6}").stdout
print("t6 first added in:", git("log", "--diff-filter=A", "--format=%H %cI %s", "--", T6).stdout.decode().strip())
print("t6 at", t6c[:8], "sha256", sha(t6), "| == HEAD object:", t6 == git("show", f"{head}:{T6}").stdout,
      "| == working tree:", t6 == open(os.path.join(repo, T6), "rb").read())
t6 = t6.decode("utf-8")
rec_sha = dict((n, h) for h, n in re.findall(r"^([0-9a-f]{64})  /root/\.blind_r4/(\S+)$", t6, re.M))
rec_size = dict((n, int(s)) for s, n in re.findall(r"^-rw-r--r-- 1 root root\s+(\d+) \S+ (\S+)$", t6, re.M))
rec_mtime = dict((n, t) for t, n in re.findall(r"^-rw-r--r-- 1 root root\s+\d+ (\S+) (\S+)$", t6, re.M))
ref = dict(re.findall(r"^(wip-[a-e]) ([0-9a-f]{40})$", t6, re.M))
logl = {m[0]: (m[1], m[2]) for m in re.findall(r"^(wip-[a-e]) ([0-9a-f]{40}) parent=([0-9a-f]{40}) ", t6, re.M)}
print("t6 records: sha256 lines", len(rec_sha), "| ls -l lines", len(rec_size), "| for-each-ref lines", len(ref), "| git log lines", len(logl))
print("t6 for-each-ref == git log hashes:", all(ref[k] == logl[k][0] for k in ref), "| parents:", sorted({p for _, p in logl.values()}))

files = sorted(os.listdir(os.path.join(repo, B)))
print("files in", B, ":", files)
print("files not covered by the t6 record:", [f for f in files if f not in rec_sha])
print("t6 records without a file:", [f for f in rec_sha if f not in files])
added = git("log", "--diff-filter=A", "--format=%H %cI", f"{t6c}..{head}", "--", B).stdout.decode().split("\n")
print("commits in", f"{t6c[:8]}..{head[:8]}", "that added files under blind/:", [l for l in added if l])
ok = 0
for f in sorted(rec_sha):
    b = open(os.path.join(repo, B, f), "rb").read()
    g = git("show", f"{head}:{B}{f}").stdout
    line = (f"{f:17s} sha256 {sha(b)} recorded {rec_sha[f]} match {sha(b) == rec_sha[f]} | bytes {len(b)} recorded {rec_size.get(f)} "
            f"match {len(b) == rec_size.get(f)} | HEAD object == working tree {g == b}")
    good = sha(b) == rec_sha[f] and len(b) == rec_size.get(f) and g == b
    if f.startswith("prompt_"):
        w = f[len("prompt_"):-len(".txt")]
        first = b.decode("utf-8").split("\n", 1)[0]
        m = re.search(r"\b" + re.escape(w) + r"\(提交 ([0-9a-f]{40})\)相对 ([0-9a-f]{40}) ", first)
        c, base = (m.group(1), m.group(2)) if m else (None, None)
        good = good and c == ref.get(w) and base == logl[w][1]
        line += f" | prompt names {w} commit {c} t6 {ref.get(w)} match {c == ref.get(w)} | base {base} == t6 parent {base == logl[w][1]}"
    ok += good
    print(line)
print("files with every check matching:", ok, "of", len(rec_sha))

print("== extra: files vs source_events.jsonl tool-call inputs, and event times vs t6 mtimes")
ev = [json.loads(l) for l in open(os.path.join(repo, B, "source_events.jsonl"), encoding="utf-8")]
for e in ev:
    f = e["file"]
    b = open(os.path.join(repo, B, f), "rb").read()
    src = e["input"]["prompt"] if e["tool"] == "Agent" else e["input"]["content"]
    sb = src.encode("utf-8")
    rel = "equal" if sb == b else ("file = input + '\\n'" if sb + b"\n" == b else ("input = file + '\\n'" if b + b"\n" == sb else "DIFFERENT"))
    print(f"  {e['created_at']} {e['tool']:5s} {f:17s} input vs file: {rel} | t6 mtime {rec_mtime.get(f)}"
          + (f" | Write path {e['input']['file_path']}" if e["tool"] == "Write" else f" | subagent_type {e['input'].get('subagent_type')}"))
print("== wip commits in this clone")
for w, h in sorted(ref.items()):
    r = git("cat-file", "-t", h, check=False)
    print(f"  {w} {h}: {(r.stdout or r.stderr).decode().strip()}")
