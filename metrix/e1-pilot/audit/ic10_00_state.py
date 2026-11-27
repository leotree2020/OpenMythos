"""ic10_00 (implementation stage C, C2 third fix commit, round 1; my ic9_00 rewritten for this round): the state audited.
Read-only git commands only (no write-tree: the staged tree is compared entry by entry with the tree object named in
the review input).
  a. HEAD is the parent 2665ab10; review_c2d/tree.txt names write-tree c7869d35 and HEAD 2665ab10, and its listing
     equals `git ls-tree -r` of that tree; the index entries (git ls-files -s) equal the entries of tree c7869d35; the
     full staged diff against HEAD is the diff part of review_c2d/input.diff; review_c2d/input_code.diff is
     byte-identical to `git diff --cached HEAD` of src/, tests/, reports/impl_c/c2_mutate_fix3.py and c2d_checks.sh.
  b. src/, tests/ and run_pilot.py: working tree == index (the code I run as a driver is the staged code); the sha256 of
     `git diff --cached HEAD -- src tests run_pilot.py` equals the one recorded at the start and end of
     c2d_01_checks.txt and c2d_02_smoke.txt; the `git ls-files -s` code lines recorded in c2d_01 (first and last)
     equal the staged tree's code entries; the sha256 lines of c2_mutate_fix3.py and c2d_checks.sh recorded in c2d_01
     equal the sha256 of their staged blobs.
  c. The recorded write-tree da82a1e1 (c2d_01 and c2d_02, first and last): the tree object exists; its difference to the
     staged tree c7869d35 is only added files: c2d_01_checks.txt, c2d_02_smoke.txt and reports/impl_c/c2d_smoke_records/*
     (its code entries identical to the staged tree's).
  d. The staged copies reports/impl_c/c2d_smoke_records/* are byte-identical to the smoke's records under
     c2d_smoke/records (index blob vs file); not copied: the per-question details only.
  e. RUNBOOK_A100.md, reports/impl_c/c3_hf_tree_70d244cc.txt and reports/impl_c/c3_checks.sh are untracked and not
     staged (C3 drafts).
  f. The recordings' first line names the parent as "2665ab17" (the Executor's stated typo); the STATE lines of
     `git rev-parse HEAD` in c2d_01 / c2d_02 give the full parent.
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic10_00_state.py <repo_root> <review_dir> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
import subprocess
from ia_common import sha, run

PARENT = "2665ab1036b66180ef1dee6b869135a45efefaa5"
TREE = "c7869d358c4adf6677d0f9843937bb6f3009b67b"
REC_TREE = "da82a1e1b4de13588bd215b1bf5b5e88bd001112"
CODE = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/run_pilot.py"]
IMPL_C = "metrix/e1-pilot/reports/impl_c/"
CODE_INPUT = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", IMPL_C + "c2_mutate_fix3.py", IMPL_C + "c2d_checks.sh"]
COPY = IMPL_C + "c2d_smoke_records/"
DRAFTS = ["metrix/e1-pilot/RUNBOOK_A100.md", IMPL_C + "c3_hf_tree_70d244cc.txt", IMPL_C + "c3_checks.sh"]
LS_RE = re.compile(r"^(100644|100755) ([0-9a-f]{40}) 0\t(metrix/e1-pilot/(?:src/|tests/|run_pilot\.py)\S*)$", re.M)
SUM_RE = re.compile(r"^([0-9a-f]{64})  (metrix/e1-pilot/reports/impl_c/(?:c2_mutate_fix3\.py|c2d_checks\.sh))$", re.M)


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


def tree_entries(repo, tree, *paths):
    out = g(repo, "ls-tree", "-r", tree, *(("--",) + paths if paths else ())).stdout
    return sorted((x.split("\t")[0].split()[0], x.split("\t")[0].split()[2], x.split("\t")[1]) for x in out.split("\n") if x)


def main():
    repo, rdir, work = sys.argv[1:4]
    ok = True
    head = g(repo, "rev-parse", "HEAD").stdout.strip()
    print("a. HEAD %s == parent %s: %s" % (head, PARENT, head == PARENT))
    ok &= head == PARENT
    tt = open(os.path.join(rdir, "tree.txt"), encoding="utf-8").read().split("\n")
    print("   review_c2d/tree.txt first lines %r %r" % (tt[0], tt[1]))
    ok &= tt[0] == "git write-tree: " + TREE and tt[1] == "HEAD: " + PARENT
    listed = sorted((x.split("\t")[0].split()[0], x.split("\t")[0].split()[2], x.split("\t")[1]) for x in tt[2:] if x)
    tre = tree_entries(repo, TREE)
    sub = tree_entries(repo, TREE, "metrix/e1-pilot")
    print("   tree.txt listing %d entries == git ls-tree -r %s -- metrix/e1-pilot (%d entries; the whole tree has %d): %s" % (
        len(listed), TREE[:8], len(sub), len(tre), listed == sub))
    ok &= listed == sub
    idx = sorted(tuple(x.split("\t")[0].split()[:2] + [x.split("\t")[1]]) for x in g(repo, "ls-files", "-s").stdout.split("\n") if x)
    print("   index entries %d | tree %s entries %d | identical (mode, blob, path): %s" % (len(idx), TREE[:8], len(tre), idx == tre))
    ok &= idx == tre
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
    staged_code = tree_entries(repo, TREE, *CODE)
    print("   sha256 of git diff --cached HEAD -- %s: %s | staged tree code entries: %d" % (CODE, code_sha, len(staged_code)))
    blob_sums = {}
    for rel in (IMPL_C + "c2_mutate_fix3.py", IMPL_C + "c2d_checks.sh"):
        blob_sums[rel] = sha(g(repo, "cat-file", "blob", ":" + rel, text=False).stdout)
    print("   sha256 of the staged blobs: %s" % {k.split("/")[-1]: v[:16] for k, v in blob_sums.items()})
    texts = {}
    for f in ("c2d_01_checks.txt", "c2d_02_smoke.txt"):
        t = open(os.path.join(repo, IMPL_C, f), encoding="utf-8").read()
        texts[f] = t
        shas = re.findall(r"^([0-9a-f]{64})  -$", t, re.M)
        trees = re.findall(r"^([0-9a-f]{40})$", t, re.M)
        blocks = ls_blocks(t)
        sums = SUM_RE.findall(t)
        print("   %s: code diff sha256 lines %s (== mine: %s) | 40-hex lines %s | ls-files code blocks %d, each == the staged "
              "tree's code entries: %s | script sha256 lines %s == staged blobs: %s" % (
                  f, [s[:8] for s in shas], [s == code_sha for s in shas], [x[:8] for x in trees], len(blocks),
                  [sorted(b) == staged_code for b in blocks], [(p.split("/")[-1], s[:8]) for s, p in sums],
                  [blob_sums[p] == s for s, p in sums]))
        ok &= shas == [code_sha, code_sha] and all(blob_sums[p] == s for s, p in sums)
        if f == "c2d_01_checks.txt":
            ok &= len(blocks) == 2 and all(sorted(b) == staged_code for b in blocks) and len(sums) == 4
            ok &= [x for x in trees if x != PARENT] == [REC_TREE, REC_TREE]
        else:
            ok &= len(blocks) == 2 and all(sorted(b) == staged_code for b in blocks)
            ok &= [x for x in trees if x != PARENT] == [REC_TREE, REC_TREE]
            ok &= trees.count(PARENT) == 2

    print("\nc. the recorded write-tree %s" % REC_TREE[:8])
    if g(repo, "cat-file", "-t", REC_TREE).stdout.strip() == "tree":
        dt = [x for x in g(repo, "diff-tree", "-r", "--name-status", REC_TREE, TREE).stdout.split("\n") if x]
        kinds = sorted(set(x.split("\t")[0] for x in dt))
        paths = [x.split("\t")[1] for x in dt]
        not_evidence = [p for p in paths if p not in (IMPL_C + "c2d_01_checks.txt", IMPL_C + "c2d_02_smoke.txt")
                        and not p.startswith(COPY)]
        rc = tree_entries(repo, REC_TREE, *CODE)
        print("   tree object present; diff-tree %s..%s: %d paths, change kinds %s; paths other than c2d_01, c2d_02 and the "
              "smoke-record copies: %s | its code entries == the staged tree's: %s" % (
                  REC_TREE[:8], TREE[:8], len(dt), kinds, not_evidence, rc == staged_code))
        ok &= kinds == ["A"] and not not_evidence and rc == staged_code
    else:
        print("   tree object %s not in this object database" % REC_TREE[:8])
        ok = False

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

    print("\nf. first lines of the recordings and their HEAD lines")
    for f, t in texts.items():
        first = t.split("\n")[0]
        m = re.search(r"parent ([0-9a-f]+)", first)
        heads = [x for x in re.findall(r"^([0-9a-f]{40})$", t, re.M) if x == PARENT]
        print("   %s: first line names parent %r (prefix of the real parent: %s) | `git rev-parse HEAD` lines equal to %s: %d" % (
            f, m.group(1) if m else None, bool(m) and PARENT.startswith(m.group(1)), PARENT[:12], len(heads)))
    sh = open(os.path.join(repo, IMPL_C, "c2d_checks.sh"), encoding="utf-8").read().split("\n")
    print("   c2d_checks.sh line 9 names %r" % re.findall(r"parent [0-9a-f]+", sh[8]))
    return bool(ok)


run(main)
