"""ic8_00 (implementation stage C, C2 fix commit, round 1): the state audited. Read-only git commands only (no
write-tree: the staged tree is compared entry by entry with the tree object named in the review input).
  a. HEAD is the parent 1900b1fe; the index entries (git ls-files -s) equal the entries of the review input's tree
     b40224e6 (git ls-tree -r); the full staged diff against HEAD is the diff part of review_c2b/input.diff;
     review_c2b/input_code.diff is byte-identical to `git diff --cached HEAD` of src/, tests/,
     reports/impl_c/c2_mutate_fix1.py and c2b_checks.sh.
  b. src/, tests/ and run_pilot.py: working tree == index (the code I run as a driver is the staged code); the sha256 of
     `git diff --cached HEAD -- src tests run_pilot.py` is the 3920af52... recorded at the start and end of
     c2b_03_checks.txt and c2b_04_smoke.txt.
  c. The smoke ran on the tree 6071ea72 (git write-tree at the start and end of c2b_04_smoke.txt): src/, tests/ and
     run_pilot.py of 6071ea72 equal those of b40224e6 (blob ids).
  d. The staged copies reports/impl_c/c2b_smoke_records/* are byte-identical to the smoke's records under
     c2b_smoke/records (index blob vs file); not copied: the per-question details only.
  e. RUNBOOK_A100.md and reports/impl_c/c3_hf_tree_70d244cc.txt are untracked and not staged (C3 drafts).
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic8_00_state.py <repo_root> <review_dir> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
import subprocess
from ia_common import sha, run

PARENT = "1900b1fe3fc1c24f0d3b6b15c3ba3cb7e5069f46"
TREE = "b40224e68d1d42f9b4dc886fe9e159f9d99162b1"
SMOKE_TREE = "6071ea727fec6bf2eedff62f184a02bfc1a4ac64"
CODE_DIFF_SHA = "3920af52f4d3bfd7269d7fa280599137ac315d74f2117e28168fe88d9cd1e33d"
CODE = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/run_pilot.py"]
CODE_INPUT = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/reports/impl_c/c2_mutate_fix1.py",
              "metrix/e1-pilot/reports/impl_c/c2b_checks.sh"]
COPY = "metrix/e1-pilot/reports/impl_c/c2b_smoke_records/"
DRAFTS = ["metrix/e1-pilot/RUNBOOK_A100.md", "metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt"]


def g(repo, *a, text=True):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=text, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))


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
    print("   review_c2b/tree.txt names %s: %s" % (tree_file, tree_file == TREE))
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
    print("   sha256 of git diff --cached HEAD -- %s: %s | == %s (c2b_03, c2b_04): %s" % (CODE, sha(cd), CODE_DIFF_SHA[:8],
                                                                                    sha(cd) == CODE_DIFF_SHA))
    ok &= sha(cd) == CODE_DIFF_SHA
    for f in ("c2b_03_checks.txt", "c2b_04_smoke.txt"):
        t = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c", f), encoding="utf-8").read()
        shas = re.findall(r"^([0-9a-f]{64})  -$", t, re.M)
        trees = re.findall(r"^([0-9a-f]{40})$", t, re.M)
        print("   %s: code diff sha256 lines %s | 40-hex lines %s" % (f, [s[:8] for s in shas], [x[:8] for x in trees]))
        ok &= shas == [CODE_DIFF_SHA, CODE_DIFF_SHA] and SMOKE_TREE in trees

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
