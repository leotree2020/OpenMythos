"""ic10_07 (implementation stage C, C2 third fix commit (staged tree c7869d35, parent 2665ab10), round 1; supplementary;
my ic9_07 for this round's mutation script): the mutation run (c2d_01) rewrites the working tree of this repository.
Here: no mutation is left in the code under review. The mutation list of reports/impl_c/c2_mutate_fix3.py (43) is READ
as data with ast (never imported or executed): for each mutation the original text ("old") occurs exactly once in the
STAGED blob of its file (a mutation left applied would have removed it, and the runner refuses a mutation whose
original does not occur exactly once), and the staged blob and the working-tree file are byte-identical. Also printed:
the test nodes each mutation names (as written in the list). Data Auditor's own script.
usage: python -I -B ic10_07_mutation_remnants.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import subprocess
from ia_common import run

MUTS_FILES = {"metrix/e1-pilot/reports/impl_c/c2_mutate_fix3.py": 43}
FILES = {"PI": "metrix/e1-pilot/src/metrix_e1/pilot.py", "RP": "metrix/e1-pilot/run_pilot.py"}


def staged(repo, rel):
    r = subprocess.run(["git", "-C", repo, "cat-file", "blob", ":" + rel], capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    assert r.returncode == 0, rel
    return r.stdout.decode("utf-8")


def main():
    repo = sys.argv[1]
    ok = True
    blobs = {k: staged(repo, v) for k, v in FILES.items()}
    wt = {k: open(os.path.join(repo, v), encoding="utf-8").read() for k, v in FILES.items()}
    for k in FILES:
        print("%s: staged blob == working tree file: %s" % (FILES[k], blobs[k] == wt[k]))
        ok &= blobs[k] == wt[k]
    for mut, want_n in MUTS_FILES.items():
        tree = ast.parse(staged(repo, mut))
        muts = [n.value for n in tree.body if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == ["MUTS"]][0]
        print("\n%s" % mut)
        n = 0
        for t in muts.elts:
            name = t.elts[0].value
            path = ast.unparse(t.elts[1])
            old, new = t.elts[2], t.elts[3]
            assert isinstance(old, ast.Constant) and isinstance(old.value, str), name
            assert isinstance(new, ast.Constant) and isinstance(new.value, str), name
            c = blobs[path].count(old.value)
            n += 1
            if new.value == "":
                rinfo = "replacement: deletion"
            else:
                c_new = blobs[path].count(new.value)
                c_new_in_old = old.value.count(new.value) * c
                rinfo = "replacement occurs %d (inside the original %d)%s" % (
                    c_new, c_new_in_old, "" if c_new == c_new_in_old or c_new == 0 else " -- also outside the original "
                    "(informational: the runner replaces the original only)")
            tests_src = ast.unparse(t.elts[4])
            print("  %-62s %s: original occurs %d time(s) | %s | tests %s" % (name, FILES[path].split("/")[-1], c, rinfo, tests_src))
            ok &= c == 1
        print("mutations read: %d (expected %d)" % (n, want_n))
        ok &= n == want_n
    return bool(ok)


run(main)
