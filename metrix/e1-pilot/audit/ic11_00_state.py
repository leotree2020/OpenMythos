"""ic11_00 (implementation stage C, C4 code commit (Review Gate ruling of 2026-11-27, tasks/IMPL_C4_RULING.md), round 1;
my ic10_00 rewritten for this round): the state audited. Read-only git commands only (no write-tree in this script).
  a. HEAD is the parent 3bc761ea; review_c4/tree.txt names the staged tree 63121c79; the index entries (git ls-files -s)
     equal the entries of that tree; the full staged diff against HEAD is the diff part (tail) of review_c4/input.diff;
     review_c4/input_code.diff is byte-identical to `git diff --cached HEAD` of src/, tests/ and
     reports/impl_c/c4_mutate.py, c4_checks.sh, c4_smoke.sh; staged paths all under metrix/e1-pilot/.
  b. src/, tests/ and run_pilot.py: working tree == index (the code I run as a driver is the staged code); the sha256 of
     `git diff --cached HEAD -- src tests run_pilot.py` equals the one recorded at the start and end of c4_02_checks.txt
     and c4_03_smoke.txt (e8df1988...); the `git ls-files -s` code blocks recorded there equal the staged tree's code
     entries; the sha256 lines of c4_mutate.py, c4_checks.sh, IMPL_C4_RULING.md (c4_02) and c4_smoke.sh (c4_03) equal
     the sha256 of their staged blobs.
  c. The recorded write-tree 178c9a2f (c4_02 and c4_03, first and last): the tree object exists; its difference to the
     staged tree 63121c79 is only added files: c4_02_checks.txt, c4_03_smoke.txt and reports/impl_c/c4_smoke_records/*
     (its code entries identical to the staged tree's).
  d. The staged copies reports/impl_c/c4_smoke_records/* are byte-identical to the smoke's records under
     c4_smoke/records (index blob vs file); not copied: the per-question details only.
  e. tasks/IMPL_C4_RULING.md (staged blob) == the ruling text quoted in my invocation (embedded below, as quoted by the
     Executor from the Owner's relay) and == review_c4/ruling_c4.txt.
  f. Files the Executor says are not part of this commit (RUNBOOK_A100.md, reports/IMPL_C_REPORT.md,
     reports/DEFERRED_MINORS.md): working tree == index == HEAD; nothing in metrix/ is modified-unstaged or untracked
     outside audit/.
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic11_00_state.py <repo_root> <review_dir> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
import subprocess
from ia_common import sha, run

PARENT = "3bc761ea1d1cb7a1bf5a7a89d4084055e4ca83d1"
TREE = "63121c792654e53fce2bb1418b6413b3a275c126"
REC_TREE = "178c9a2f42a0598b1baa27bfbc4c5084ba2bdbac"
CODE_SHA = "e8df198872e911601f0d71aa009b2f649965e4898fd3bd236bb659a43f50d44a"
CODE = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/run_pilot.py"]
IMPL_C = "metrix/e1-pilot/reports/impl_c/"
CODE_INPUT = ["metrix/e1-pilot/src", "metrix/e1-pilot/tests", IMPL_C + "c4_mutate.py", IMPL_C + "c4_checks.sh",
              IMPL_C + "c4_smoke.sh"]
COPY = IMPL_C + "c4_smoke_records/"
RULING = "metrix/e1-pilot/tasks/IMPL_C4_RULING.md"
NOT_IN_COMMIT = ["metrix/e1-pilot/RUNBOOK_A100.md", "metrix/e1-pilot/reports/IMPL_C_REPORT.md",
                 "metrix/e1-pilot/reports/DEFERRED_MINORS.md"]
LS_RE = re.compile(r"^(100644|100755) ([0-9a-f]{40}) 0\t(metrix/e1-pilot/(?:src/|tests/|run_pilot\.py)\S*)$", re.M)
SUM_RE = re.compile(r"^([0-9a-f]{64})  (metrix/e1-pilot/(?:reports/impl_c/(?:c4_mutate\.py|c4_checks\.sh|c4_smoke\.sh)"
                    r"|tasks/IMPL_C4_RULING\.md))$", re.M)
# The ruling as quoted in my invocation (Owner's relay of Review Gate's ruling of 2026-11-27).
RULING_TEXT = """读 metrix/CLAUDE.md、tasks/IMPL_C1_RULING.md、reports/IMPL_C_REPORT.md、RUNBOOK_A100.md。直接在 metrix-e1-pilot-protocol-v1 上工作，只做快进推送，不推送标签，不经 PR。本段原文入库为 tasks/IMPL_C4_RULING.md。

Review Gate 裁决（2026-11-27，作用范围：E1 Pilot 直至结束）：
1. ST11 改为读「B17 估算 + checkpoint 开销」之和，超过 3.5 小时即停。B17 的解释文字相应修订，status 记为 ACCEPTED（Review Gate 2026-11-27 修订）。ST7 的事前判断不变，TEST 的事前估计不加余量。补测试与变异。
2. C2 待决第 1、3、4、5、6、7 项：全部按现行实现接受，不改代码。
3. A100 上的依赖安装、输入与权重下载属于正式流程；metrix/CLAUDE.md 第 4 节「租卡后只跑正式流程」指不在租用机器上开发调试。
4. 正式运行期间只含输出的手工提交（results/command_output/、audit/、reviews/）按证据提交处理，不经 code-reviewer；此前各项「本阶段」裁决在 A100 运行期间继续有效。
5. 两份 L6 计数不同：ST10，不运行 test-evaluate；Executor 按协议第 10 节模板手写一份 BLOCKED 实验记录，作为证据提交。
6. 主机没有 CPython 3.13.18 时，允许用 uv 安装该精确版本；装不到即停下报告 Owner。
7. RUNBOOK 按 1、3–6 更新，删去「待 Review Gate 决定」的措辞，时长表改为 ST11 读两者之和；另写明在 A100 主机上运行 Claude Code 的前提（从仓库根目录、本分支启动，使两个 agent 定义直接加载）。

代码提交送两份审查，调用文字写入 IMPL_C1_RULING.md 的防范对象原文；只改文档的提交只送 code-reviewer。完成后状态仍为 IMPLEMENTATION_READY，停下。"""


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
    tt = open(os.path.join(rdir, "tree.txt"), encoding="utf-8").read()
    print("   review_c4/tree.txt %r == %s: %s" % (tt, TREE[:8], tt.strip() == TREE))
    ok &= tt.strip() == TREE
    tre = tree_entries(repo, TREE)
    idx = sorted(tuple(x.split("\t")[0].split()[:2] + [x.split("\t")[1]]) for x in g(repo, "ls-files", "-s").stdout.split("\n") if x)
    print("   index entries %d | tree %s entries %d | identical (mode, blob, path): %s" % (len(idx), TREE[:8], len(tre), idx == tre))
    ok &= idx == tre
    diff = g(repo, "diff", "--cached", "HEAD", text=False).stdout
    inp = open(os.path.join(rdir, "input.diff"), "rb").read()
    tail = inp.endswith(diff) or inp.endswith(diff + b"\n")
    print("   staged diff vs HEAD: %d bytes, sha256 %s | contained in input.diff (%d bytes) as its tail: %s" % (
        len(diff), sha(diff), len(inp), tail))
    ok &= tail
    stat = g(repo, "diff", "--cached", "--stat", "HEAD", text=False).stdout
    print("   input.diff starts with `git diff --cached --stat HEAD` (%d bytes): %s" % (len(stat), inp.startswith(stat)))
    ok &= inp.startswith(stat)
    cdiff = g(repo, "diff", "--cached", "HEAD", "--", *CODE_INPUT, text=False).stdout
    cin = open(os.path.join(rdir, "input_code.diff"), "rb").read()
    print("   input_code.diff sha256 %s == git diff --cached HEAD -- %s (sha256 %s): %s" % (
        sha(cin), [c.split("/")[-1] for c in CODE_INPUT], sha(cdiff), cin == cdiff))
    ok &= cin == cdiff
    ns = [x for x in g(repo, "diff", "--cached", "--name-status", "HEAD").stdout.split("\n") if x]
    print("   staged paths %d: kinds %s" % (len(ns), sorted(set(x.split("\t")[0] for x in ns))))
    for x in ns:
        if not x.split("\t")[1].startswith(COPY + "training_runs/"):
            print("     " + x)
    print("     (+ %d files under %straining_runs/)" % (sum(1 for x in ns if x.split("\t")[1].startswith(COPY + "training_runs/")), COPY))
    outside = [x for x in ns if not x.split("\t")[1].startswith("metrix/e1-pilot/")]
    print("   staged paths outside metrix/e1-pilot/: %s" % outside)
    ok &= not outside
    code_changed = sorted(x for x in ns if any(x.split("\t")[1].startswith(c) for c in CODE))
    print("   staged code paths (src/, tests/, run_pilot.py): %s" % code_changed)
    ok &= [x.split("\t")[1].split("/")[-1] for x in code_changed] == [
        "interpretations.py", "pilot.py", "test_run_pilot.py", "test_test_data.py"]

    q = g(repo, "diff", "--quiet", "--", *CODE).returncode
    print("\nb. working tree == index for %s: %s (git diff --quiet exit %d)" % (CODE, q == 0, q))
    ok &= q == 0
    cd = g(repo, "diff", "--cached", "HEAD", "--", *CODE, text=False).stdout
    code_sha = sha(cd)
    print("   sha256 of git diff --cached HEAD -- src tests run_pilot.py: %s | == %s (stated): %s" % (
        code_sha, CODE_SHA[:8], code_sha == CODE_SHA))
    ok &= code_sha == CODE_SHA
    staged_code = tree_entries(repo, TREE, *CODE)
    print("   staged tree code entries: %d" % len(staged_code))
    blob_sums = {}
    for rel in (IMPL_C + "c4_mutate.py", IMPL_C + "c4_checks.sh", IMPL_C + "c4_smoke.sh", RULING):
        blob_sums[rel] = sha(g(repo, "cat-file", "blob", ":" + rel, text=False).stdout)
    print("   sha256 of the staged blobs: %s" % {k.split("/")[-1]: v[:16] for k, v in blob_sums.items()})
    texts = {}
    for f, nsums in (("c4_02_checks.txt", 6), ("c4_03_smoke.txt", 2)):
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
        ok &= shas == [code_sha, code_sha] and all(blob_sums[p] == s for s, p in sums) and len(sums) == nsums
        ok &= len(blocks) == 2 and all(sorted(b) == staged_code for b in blocks)
        ok &= trees == [PARENT, REC_TREE, PARENT, REC_TREE]
        ok &= t.count("WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT\n") == 2

    print("\nc. the recorded write-tree %s" % REC_TREE[:8])
    if g(repo, "cat-file", "-t", REC_TREE).stdout.strip() == "tree":
        dt = [x for x in g(repo, "diff-tree", "-r", "--name-status", REC_TREE, TREE).stdout.split("\n") if x]
        kinds = sorted(set(x.split("\t")[0] for x in dt))
        paths = [x.split("\t")[1] for x in dt]
        not_evidence = [p for p in paths if p not in (IMPL_C + "c4_02_checks.txt", IMPL_C + "c4_03_smoke.txt")
                        and not p.startswith(COPY)]
        rc = tree_entries(repo, REC_TREE, *CODE)
        print("   tree object present; diff-tree %s..%s: %d paths, change kinds %s; paths other than c4_02, c4_03 and the "
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
    ok &= not diffr and not missing and same == len(copies)
    smoke_recs = sorted(os.path.relpath(os.path.join(d, f), os.path.join(work, "records"))
                        for d, _, fs in os.walk(os.path.join(work, "records")) for f in fs)
    not_copied = sorted(set(smoke_recs) - {c[len(COPY):] for c in copies})
    print("   smoke records %d, not copied %d (expected: the per-question details only), all under details/: %s" % (
        len(smoke_recs), len(not_copied), all(x.startswith("details/") for x in not_copied)))
    ok &= all(x.startswith("details/") for x in not_copied)

    print("\ne. %s" % RULING)
    rb = g(repo, "cat-file", "blob", ":" + RULING, text=False).stdout.decode("utf-8")
    rc4 = open(os.path.join(rdir, "ruling_c4.txt"), encoding="utf-8").read()
    print("   staged blob %d chars, ends with newline %s | == the text quoted in my invocation (trailing newline aside): %s | "
          "== review_c4/ruling_c4.txt: %s | working tree == index: %s" % (
              len(rb), rb.endswith("\n"), rb.rstrip("\n") == RULING_TEXT, rb == rc4,
              open(os.path.join(repo, RULING), encoding="utf-8").read() == rb))
    ok &= rb.rstrip("\n") == RULING_TEXT and rb == rc4
    if rb.rstrip("\n") != RULING_TEXT:
        a, b = rb.rstrip("\n").split("\n"), RULING_TEXT.split("\n")
        print("   differing lines: %s" % [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y][:5])

    print("\nf. files outside this commit")
    for rel in NOT_IN_COMMIT:
        wt = open(os.path.join(repo, rel), "rb").read()
        hb = g(repo, "cat-file", "blob", "HEAD:" + rel, text=False).stdout
        ib = g(repo, "cat-file", "blob", ":" + rel, text=False).stdout
        print("   %s: working tree == index == HEAD: %s" % (rel, wt == ib == hb))
        ok &= wt == ib == hb
    st = [x for x in g(repo, "status", "--porcelain", "--untracked-files=all", "--", "metrix").stdout.split("\n") if x]
    other = [x for x in st if not (x[:2] in ("A ", "M ") or x.startswith("?? metrix/e1-pilot/audit/"))]
    print("   git status entries in metrix/: %d | neither staged-only (A_/M_) nor untracked under audit/: %s" % (len(st), other))
    ok &= not other
    return bool(ok)


run(main)
