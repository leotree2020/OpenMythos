"""ic8_07 (implementation stage C, C2 fix commit (staged tree b40224e6, parent 1900b1fe), round 1; supplementary): the
Executor's c2b_01 recording was killed while a mutation of c2_mutate_fix1.py was applied to the working tree
(c2b_01b_restore_after_kill.txt). Here: no mutation is left in the code under review. The mutation list of
reports/impl_c/c2_mutate_fix1.py is READ as data with ast (never imported or executed): for each of its 25 mutations the
original text ("old") occurs exactly once in the STAGED blob of its file and in the working-tree file (a mutation left
applied would have removed it), and the two files are byte-identical. Data Auditor's own script.
usage: python -I -B ic8_07_mutation_remnants.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import subprocess
from ia_common import run

MUT = "metrix/e1-pilot/reports/impl_c/c2_mutate_fix1.py"
FILES = {"PI": "metrix/e1-pilot/src/metrix_e1/pilot.py", "RP": "metrix/e1-pilot/run_pilot.py"}


def staged(repo, rel):
    r = subprocess.run(["git", "-C", repo, "cat-file", "blob", ":" + rel], capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    assert r.returncode == 0, rel
    return r.stdout.decode("utf-8")


def main():
    repo = sys.argv[1]
    tree = ast.parse(staged(repo, MUT))
    muts = [n.value for n in tree.body if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == ["MUTS"]][0]
    ok = True
    blobs = {k: staged(repo, v) for k, v in FILES.items()}
    wt = {k: open(os.path.join(repo, v), encoding="utf-8").read() for k, v in FILES.items()}
    for k in FILES:
        print("%s: staged blob == working tree file: %s" % (FILES[k], blobs[k] == wt[k]))
        ok &= blobs[k] == wt[k]
    n = 0
    for t in muts.elts:
        name = t.elts[0].value
        path = ast.unparse(t.elts[1])
        old = t.elts[2]
        assert isinstance(old, ast.Constant) and isinstance(old.value, str), name
        c = blobs[path].count(old.value)
        n += 1
        print("  %-62s %s: original text occurs %d time(s)" % (name, FILES[path].split("/")[-1], c))
        ok &= c == 1
    print("mutations read: %d (expected 25)" % n)
    ok &= n == 25
    return bool(ok)


run(main)
