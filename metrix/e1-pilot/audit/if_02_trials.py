"""IF-2 (implementation stage B, report commit, task 3): the files the Executor copied into audit/stdout/impl_b/trials/
are byte-identical to the files I wrote in the session scratchpad in my rounds 3 and 4.
  a. my own list of what I wrote there that is not working data: every regular file directly in <scratch>/auditor_ib,
     auditor_ic, auditor_id, auditor_ie (my trial outputs and helper excerpts); the working-data subdirectories
     (dl/ downloads, out/ regenerations, devrows/ DEV-row file, selftest*/ copies for the positive controls) are
     listed with file counts only (they are inputs / regenerated data, not outputs to be kept);
  b. for each such original: the repository copy named by the Executor's rule (<round>_<name>, helper .py files
     <round>_helper_<name>) exists; original bytes == working-tree bytes == index (staged) blob; and, independently of
     the naming rule, the set of scratch originals whose bytes equal each repository copy;
  c. nothing else is in trials/ except this round's own trial outputs (if_trial*);
  d. the sha256 the Executor printed in reports/impl_b/t12b_review_records_copy.txt for the 9 copies == mine;
  e. what the helper .py files are: id06_base.py == my audit/id_06_static.py; part_head.py / part_mid.py are
     verbatim excerpts of it (my own code; no Executor code).
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I if_02_trials.py <repo_root> <scratch_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from ia_common import git, sha, run

TRIALS = "metrix/e1-pilot/audit/stdout/impl_b/trials"
ROUNDS = {"auditor_ib": "ib", "auditor_ic": "ic", "auditor_id": "id", "auditor_ie": "ie"}


def main():
    repo, scratch = sys.argv[1:3]
    ok = True
    print("== a. what I wrote in the scratchpad (rounds 1-4 of implementation stage B)")
    originals = []
    for d, tag in ROUNDS.items():
        base = os.path.join(scratch, d)
        top = sorted(x for x in os.listdir(base) if os.path.isfile(os.path.join(base, x)))
        subs = sorted(x for x in os.listdir(base) if os.path.isdir(os.path.join(base, x)))
        counts = {s: sum(len(fs) for _, _, fs in os.walk(os.path.join(base, s))) for s in subs}
        print(f"  {d}: files {top} | working-data subdirectories (file counts) {counts}")
        originals += [(tag, os.path.join(base, x), x) for x in top]
    print(f"  originals to be kept: {len(originals)}")

    print("\n== b. each original vs its repository copy (working tree and index)")
    copies = sorted(x for x in os.listdir(os.path.join(repo, TRIALS)))
    expected_names = set()
    content_index = {}
    for tag, path, name in originals:
        content_index.setdefault(sha(open(path, "rb").read()), []).append(path)
    for tag, path, name in originals:
        cname = f"{tag}_helper_{name}" if name.endswith(".py") else f"{tag}_{name}"
        expected_names.add(cname)
        rel = f"{TRIALS}/{cname}"
        orig = open(path, "rb").read()
        wt_path = os.path.join(repo, rel)
        wt = open(wt_path, "rb").read() if os.path.isfile(wt_path) else None
        r = git(repo, "cat-file", "blob", f":{rel}", check=False)
        idx = r.stdout if r.returncode == 0 else None
        same = wt is not None and idx is not None and orig == wt == idx
        ok &= same
        print(f"  {os.path.relpath(path, scratch)} ({len(orig)} bytes, sha256 {sha(orig)}) -> {cname}: working tree {wt is not None and orig == wt} | "
              f"index {idx is not None and orig == idx} | IDENTICAL {same}")
    print("  by content, independent of names: repository copy -> scratch originals with the same bytes")
    for c in copies:
        if c.startswith("if_"):
            continue
        h = sha(open(os.path.join(repo, TRIALS, c), "rb").read())
        m = [os.path.relpath(p, scratch) for p in content_index.get(h, [])]
        print(f"    {c} -> {m}")
        ok &= len(m) == 1

    print("\n== c. contents of trials/")
    extra = [c for c in copies if c not in expected_names and not re.fullmatch(r"if_trial\d*_[a-z0-9_]+\.txt", c)]
    missing = sorted(expected_names - set(copies))
    print(f"  files {len(copies)} | copies of my originals {len(expected_names & set(copies))} | this round's own trial outputs "
          f"{[c for c in copies if c.startswith('if_')]} | anything else {extra} | originals without a copy {missing}")
    ok &= not extra and not missing

    print("\n== d. the Executor's sha256 (reports/impl_b/t12b_review_records_copy.txt)")
    t12b = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_b/t12b_review_records_copy.txt"), encoding="utf-8").read()
    ex = dict((p.split("/")[-1], h) for h, p in re.findall(r"^([0-9a-f]{64})  (audit/stdout/impl_b/trials/\S+)$", t12b, re.M))
    cmps = re.findall(r"^\$ cmp <SCRATCH>/(\S+) metrix/e1-pilot/audit/stdout/impl_b/trials/(\S+)\nexit=(\d+)$", t12b, re.M)
    print(f"  sha256 lines for trials/: {len(ex)} | cmp lines {len(cmps)}, all exit=0: {all(e == '0' for _, _, e in cmps)}")
    ok &= len(ex) == len(expected_names) and len(cmps) == len(expected_names) and all(e == "0" for _, _, e in cmps)
    for n in sorted(expected_names):
        mine = sha(open(os.path.join(repo, TRIALS, n), "rb").read())
        print(f"  {n}: mine {mine} | Executor {ex.get(n)} | equal {mine == ex.get(n)}")
        ok &= mine == ex.get(n)
    pairs = sorted((a, b) for a, b, _ in cmps)
    mine_pairs = sorted((os.path.relpath(p, scratch), f"{t}_helper_{n}" if n.endswith(".py") else f"{t}_{n}") for t, p, n in originals)
    print(f"  the Executor's cmp pairs == my original -> copy pairs: {pairs == mine_pairs}")
    ok &= pairs == mine_pairs

    print("\n== e. the helper .py files")
    id06 = open(os.path.join(repo, "metrix/e1-pilot/audit/id_06_static.py"), encoding="utf-8").read()
    base = open(os.path.join(scratch, "auditor_ie/id06_base.py"), encoding="utf-8").read()
    head = open(os.path.join(scratch, "auditor_ie/part_head.py"), encoding="utf-8").read()
    mid = open(os.path.join(scratch, "auditor_ie/part_mid.py"), encoding="utf-8").read()
    print(f"  id06_base.py == audit/id_06_static.py: {base == id06} | part_head.py is a verbatim excerpt of it: {head in id06} "
          f"(at offset {id06.find(head)}) | part_mid.py is a verbatim excerpt of it: {mid in id06} (at offset {id06.find(mid)})")
    ok &= base == id06 and head in id06 and mid in id06
    return bool(ok)


run(main)
