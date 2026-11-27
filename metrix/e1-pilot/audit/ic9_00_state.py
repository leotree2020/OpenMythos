"""ic9_00 (implementation stage C, C2 second fix commit, round 1; my ic8_00 rewritten for this round): the state audited.
Read-only git commands only (no write-tree: the staged tree is compared entry by entry with the tree object named in
the review input).
  a. HEAD is the parent 0cbee197; the index entries (git ls-files -s) equal the entries of the review input's tree
     a6ce8a0e (git ls-tree -r); the full staged diff against HEAD is the diff part of review_c2c/input.diff;
     review_c2c/input_code.diff is byte-identical to `git diff --cached HEAD` of src/, tests/,
     reports/impl_c/c2_mutate_fix2.py, c2_mutate_fix2b.py and c2c_checks.sh.
  b. src/, tests/ and run_pilot.py: working tree == index (the code I run as a driver is the staged code); the sha256 of
     `git diff --cached HEAD -- src tests run_pilot.py` equals the one recorded at the start and end of
     c2c_03_checks.txt and c2c_04_mutate_fix2b.txt; the `git ls-files -s` code lines recorded there (first and last)
     equal the staged tree's code entries.
  c. The smoke (c2c_02_smoke.txt) ran on the c2c_01 tree: its recorded write-tree, code diff sha256 and ls-files lines
     (first and last) equal c2c_01's; of those code entries only tests/test_run_pilot.py differs from the staged tree
     (src/ and run_pilot.py identical blob ids); the tree object e5abf74b (if present) has the same code entries.
  d. The staged copies reports/impl_c/c2c_smoke_records/* are byte-identical to the smoke's records under
     c2c_smoke/records (index blob vs file); not copied: the per-question details only.
  e. RUNBOOK_A100.md and reports/impl_c/c3_hf_tree_70d244cc.txt are untracked and not staged (C3 drafts).
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic9_00_state.py <repo_root> <review_dir> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
import subprocess
from ia_common import sha, run

PARENT = "0cbee1978a76c82691e48516ddf97549e361fc2c"
TREE = "a6ce8a0ea0aeff1e86443a2a22a2a4eb349bcc50"
SMOKE_TREE = "e5abf74b6bf79b83a5b415bd841a25842dc6d919"
CODE = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/run_pilot.py"]
CODE_INPUT = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/reports/impl_c/c2_mutate_fix2.py",
              "metrix/e1-pilot/reports/impl_c/c2_mutate_fix2b.py", "metrix/e1-pilot/reports/impl_c/c2c_checks.sh"]
COPY = "metrix/e1-pilot/reports/impl_c/c2c_smoke_records/"
DRAFTS = ["metrix/e1-pilot/RUNBOOK_A100.md", "metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt"]
IMPL_C = "metrix/e1-pilot/reports/impl_c/"
LS_RE = re.compile(r"^(100644|100755) ([0-9a-f]{40}) 0\t(metrix/e1-pilot/(?:src/|tests/|run_pilot\.py)\S*)$", re.M)


def g(repo, *a, text=True):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=text, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))


def ls_blocks(text):
    """The `git ls-files -s` code lines of a recording, grouped in runs of consecutive lines (one block per STATE)."""
    blocks, cur, last = [], [], None
    for m in LS_RE.finditer(text):
        line_no = text.count("\n", 0, m.start())
        if cur and line_no != last + 1:
            blocks.append(cur)
            cur = []
        cur.append((m.group(1), m.group(2), m.group(3)))
        last = line_no
    if cur:
        blocks.append(cur)
    return blocks


def main():
    repo, rdir, work = sys.argv[1:4]
    ok = True
    head = g(repo, "rev-parse", "HEAD").stdout.strip()
    print("a. HEAD %s == parent %s: %s" % (head, PARENT, head == PARENT))
    ok &= head == PARENT
    idx = sorted(tuple(x.split("\t")[0].split()[:2] + [x.split("\t")[1]]) for x in g(repo, "ls-files", "-s").stdout.split("\n") if x)
    tre = sorted((x.split("\t")[0].split()[0], x.split("\t")[0].split()[2], x.split("\t")[1])
                 for x in g(repo, "ls-tree", "-r", TREE).stdout.split("\n") if x)
    print("   index entries %d | tree %s entries %d | identical (mode, blob, path): %s" % (len(idx), TREE[:8], len(tre), idx == tre))
    ok &= idx == tre
    tree_file = open(os.path.join(rdir, "tree.txt"), encoding="utf-8").read().strip()
    print("   review_c2c/tree.txt names %s: %s" % (tree_file, tree_file == TREE))
    ok &= tree_file == TREE
    diff = g(repo, "diff", "--cached", "HEAD", text=False).stdout
    inp = open(os.path.join(rdir, "input.diff"), "rb").read()
    tail = inp.endswith(diff) or inp.endswith(diff + b"\n")
    print("   staged diff vs HEAD: %d bytes, sha256 %s | contained in input.diff (%d bytes) as its tail: %s" % (
        len(diff), sha(diff), len(inp), tail))
    ok &= tail
    cdiff = g(repo, "diff", "--cached", "HEAD", "--", *CODE_INPUT, text=False).stdout
    cin = open(os.path.join(rdir, "input_code.diff"), "rb").read()
    print("   input_code.diff sha256 %s == git diff --cached HEAD -- %s (sha256 %s): %s" % (
        sha(cin), CODE_INPUT, sha(cdiff), cin == cdiff))
    ok &= cin == cdiff
    ns = [x for x in g(repo, "diff", "--cached", "--name-status", "HEAD").stdout.split("\n") if x]
    print("   staged paths %d: %s" % (len(ns), sorted(set(x.split("\t")[0] for x in ns))))
    for x in ns:
        if not x.split("\t")[1].startswith(COPY + "training_runs/"):
            print("     " + x)
    print("     (+ %d files under %straining_runs/)" % (sum(1 for x in ns if x.split("\t")[1].startswith(COPY + "training_runs/")), COPY))
    outside = [x for x in ns if not x.split("\t")[1].startswith("metrix/e1-pilot/")]
    print("   staged paths outside metrix/e1-pilot/: %s" % outside)
    ok &= not outside
    code_changed = sorted(x.split("\t")[1] for x in ns if any(x.split("\t")[1].startswith(c) for c in CODE))
    print("   staged code paths (src/, tests/, run_pilot.py): %s" % code_changed)

    q = g(repo, "diff", "--quiet", "--", *CODE).returncode
    print("\nb. working tree == index for %s: %s (git diff --quiet exit %d)" % (CODE, q == 0, q))
    ok &= q == 0
    cd = g(repo, "diff", "--cached", "HEAD", "--", *CODE, text=False).stdout
    code_sha = sha(cd)
    staged_code = sorted((x.split("\t")[0].split()[0], x.split("\t")[0].split()[2], x.split("\t")[1])
                         for x in g(repo, "ls-tree", "-r", TREE, "--", *CODE).stdout.split("\n") if x)
    print("   sha256 of git diff --cached HEAD -- %s: %s | staged tree code entries: %d" % (CODE, code_sha, len(staged_code)))
    for f in ("c2c_03_checks.txt", "c2c_04_mutate_fix2b.txt"):
        t = open(os.path.join(repo, IMPL_C, f), encoding="utf-8").read()
        shas = re.findall(r"^([0-9a-f]{64})  -$", t, re.M)
        trees = re.findall(r"^([0-9a-f]{40})$", t, re.M)
        blocks = ls_blocks(t)
        print("   %s: code diff sha256 lines %s (== mine: %s) | 40-hex lines %s | ls-files code blocks %d, each == the staged "
              "tree's code entries: %s" % (f, [s[:8] for s in shas], [s == code_sha for s in shas], [x[:8] for x in trees],
                                            len(blocks), [sorted(b) == staged_code for b in blocks]))
        ok &= shas == [code_sha, code_sha] and len(blocks) == 2 and all(sorted(b) == staged_code for b in blocks)

    print("\nc. the smoke's code state (c2c_02_smoke.txt) and the c2c_01 recording it followed")
    t2 = open(os.path.join(repo, IMPL_C, "c2c_02_smoke.txt"), encoding="utf-8").read()
    t1 = open(os.path.join(repo, IMPL_C, "c2c_01_checks_superseded.txt"), encoding="utf-8").read()
    b2, b1 = ls_blocks(t2), ls_blocks(t1)
    s2, s1 = re.findall(r"^([0-9a-f]{64})  -$", t2, re.M), re.findall(r"^([0-9a-f]{64})  -$", t1, re.M)
    w2 = [x for x in re.findall(r"^([0-9a-f]{40})$", t2, re.M) if x != PARENT]
    w1 = re.findall(r"^([0-9a-f]{40})$", t1, re.M)
    print("   c2c_02: ls-files blocks %d (first == last: %s) | code diff sha256 %s | write-tree lines %s" % (
        len(b2), len(b2) == 2 and b2[0] == b2[1], [s[:8] for s in s2], [x[:8] for x in w2]))
    print("   c2c_01: ls-files blocks %d (first == last: %s) | code diff sha256 %s | 40-hex lines %s" % (
        len(b1), len(b1) == 2 and b1[0] == b1[1], [s[:8] for s in s1], [x[:8] for x in w1]))
    same_01 = b2 and b1 and b2[0] == b1[0] and set(s2) == set(s1) and set(w2) == {SMOKE_TREE} and SMOKE_TREE in w1
    print("   c2c_02's code state == c2c_01's (ls-files lines, code diff sha256, write-tree %s): %s" % (SMOKE_TREE[:8], bool(same_01)))
    ok &= len(b2) == 2 and b2[0] == b2[1] and bool(same_01)
    smoke_code = {p: (m, b) for m, b, p in b2[0]}
    staged_map = {p: (m, b) for m, b, p in staged_code}
    differ = sorted(p for p in set(smoke_code) | set(staged_map) if smoke_code.get(p) != staged_map.get(p))
    print("   code entries differing between the smoke's state and the staged tree: %s" % differ)
    for p in differ:
        print("     %s: smoke %s | staged %s" % (p, smoke_code.get(p), staged_map.get(p)))
    ok &= differ == ["metrix/e1-pilot/tests/test_run_pilot.py"]
    if g(repo, "cat-file", "-t", SMOKE_TREE).stdout.strip() == "tree":
        st = sorted((x.split("\t")[0].split()[0], x.split("\t")[0].split()[2], x.split("\t")[1])
                    for x in g(repo, "ls-tree", "-r", SMOKE_TREE, "--", *CODE).stdout.split("\n") if x)
        print("   tree object %s present: its code entries == the smoke's recorded ls-files lines: %s" % (
            SMOKE_TREE[:8], st == sorted(b2[0])))
        ok &= st == sorted(b2[0])
    else:
        print("   tree object %s not in this object database (only the recorded lines compared)" % SMOKE_TREE[:8])

    copies = [x.split("\t")[1] for x in ns if x.split("\t")[1].startswith(COPY)]
    same, diffr, missing = 0, [], []
    for rel in copies:
        sub = rel[len(COPY):]
        src = os.path.join(work, "records", sub)
        staged = g(repo, "cat-file", "blob", ":" + rel, text=False).stdout
        if not os.path.exists(src):
            missing.append(sub)
            continue
        if open(src, "rb").read() == staged:
            same += 1
        else:
            diffr.append(sub)
    print("\nd. staged copies under %s: %d | byte-identical to %s/records: %d | different %s | not in the smoke's records %s" % (
        COPY, len(copies), work, same, diffr, missing))
    lab = os.path.join(repo, COPY + "LABEL.txt")
    print("   LABEL.txt of the copy directory: %r" % open(lab, encoding="utf-8").read())
    ok &= not diffr and missing == ["LABEL.txt"] and same == len(copies) - 1
    smoke_recs = sorted(os.path.relpath(os.path.join(d, f), os.path.join(work, "records"))
                        for d, _, fs in os.walk(os.path.join(work, "records")) for f in fs)
    not_copied = sorted(set(smoke_recs) - {c[len(COPY):] for c in copies})
    print("   smoke records not copied (expected: the per-question details only): %d, all under details/: %s" % (
        len(not_copied), all(x.startswith("details/") for x in not_copied)))
    ok &= all(x.startswith("details/") for x in not_copied)

    for d in DRAFTS:
        st = [x for x in g(repo, "status", "--porcelain", "--", d).stdout.split("\n") if x]
        in_idx = g(repo, "cat-file", "-e", ":" + d).returncode == 0
        print("\ne. %s status %s | in the index %s (expected untracked '??', not staged)" % (d, st, in_idx))
        ok &= st == ["?? " + d] and not in_idx
    return bool(ok)


run(main)
