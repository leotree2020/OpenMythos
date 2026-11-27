"""ic7_00 (implementation stage C, C2 work commit, round 1): the state audited. Read-only git commands only (no
write-tree: the staged tree is compared entry by entry with the tree object named in the review input).
  a. HEAD is the parent f8139f9; the index entries (git ls-files -s) equal the entries of the review input's tree
     b80c9062 (git ls-tree -r); the full staged diff against HEAD is the diff part of review_c2/input.diff.
  b. src/, tests/ and run_pilot.py: working tree == index (the code I run as a driver is the staged code).
  c. The smoke ran on the staged tree 05a76f57 recorded at the start and end of c2_06_smoke.txt: src/, tests/ and
     run_pilot.py of 05a76f57 equal those of b80c9062 (blob ids).
  d. The staged copies reports/impl_c/c2_smoke_records/* are byte-identical to the smoke's records under
     c2_smoke_final/records (index blob vs file).
  e. RUNBOOK_A100.md is untracked and not staged (not part of this review).
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic7_00_state.py <repo_root> <review_dir> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess
from ia_common import sha, run

PARENT = "f8139f9fd59bb8ec5c661379a549db7bba3d179a"
TREE = "b80c9062134db0d950cd9786209862f69ffda06c"
SMOKE_TREE = "05a76f57fc9962d3dc0b42a0e98186f9a6738106"
CODE = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/run_pilot.py"]
COPY = "metrix/e1-pilot/reports/impl_c/c2_smoke_records/"


def g(repo, *a, text=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=text, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r


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
    print("   review_c2/tree.txt names %s: %s" % (tree_file, tree_file == TREE))
    ok &= tree_file == TREE
    diff = g(repo, "diff", "--cached", "HEAD", text=False).stdout
    inp = open(os.path.join(rdir, "input.diff"), "rb").read()
    print("   staged diff vs HEAD: %d bytes, sha256 %s | contained in input.diff (%d bytes) as its tail: %s" % (
        len(diff), sha(diff), len(inp), inp.endswith(diff) or inp.endswith(diff + b"\n")))
    ok &= inp.endswith(diff) or inp.endswith(diff + b"\n")
    ns = [x for x in g(repo, "diff", "--cached", "--name-status", "HEAD").stdout.split("\n") if x]
    print("   staged paths %d: %s" % (len(ns), sorted(set(x.split("\t")[0] for x in ns))))
    for x in ns:
        if not x.split("\t")[1].startswith(COPY + "training_runs/"):
            print("     " + x)
    print("     (+ %d files under %straining_runs/)" % (sum(1 for x in ns if x.split("\t")[1].startswith(COPY + "training_runs/")), COPY))
    outside = [x for x in ns if not x.split("\t")[1].startswith("metrix/e1-pilot/")]
    print("   staged paths outside metrix/e1-pilot/: %s" % outside)
    ok &= not outside

    q = g(repo, "diff", "--quiet", "--", *CODE).returncode
    print("\nb. working tree == index for %s: %s (git diff --quiet exit %d)" % (CODE, q == 0, q))
    ok &= q == 0

    def code_entries(t):
        return sorted(x for x in g(repo, "ls-tree", "-r", t, "--", *CODE).stdout.split("\n") if x)
    a, b = code_entries(SMOKE_TREE), code_entries(TREE)
    print("\nc. smoke tree %s: %d code entries | staged tree: %d | identical: %s" % (SMOKE_TREE[:8], len(a), len(b), a == b))
    ok &= a == b and len(a) > 0

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
    ok &= not diffr and missing in ([], ["LABEL.txt"]) and same == len(copies) - len(missing)
    smoke_recs = sorted(os.path.relpath(os.path.join(d, f), os.path.join(work, "records"))
                        for d, _, fs in os.walk(os.path.join(work, "records")) for f in fs)
    not_copied = sorted(set(smoke_recs) - {c[len(COPY):] for c in copies})
    print("   smoke records not copied (expected: the per-question details only): %d, all under details/: %s" % (
        len(not_copied), all(x.startswith("details/") for x in not_copied)))
    ok &= all(x.startswith("details/") for x in not_copied)

    st = [x for x in g(repo, "status", "--porcelain", "--", "metrix/e1-pilot/RUNBOOK_A100.md").stdout.split("\n") if x]
    print("\ne. RUNBOOK_A100.md status %s (expected untracked '??', not staged)" % st)
    ok &= st == ["?? metrix/e1-pilot/RUNBOOK_A100.md"]
    return bool(ok)


run(main)
