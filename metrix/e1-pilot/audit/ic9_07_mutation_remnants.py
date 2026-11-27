"""ic9_07 (implementation stage C, C2 second fix commit (staged tree a6ce8a0e, parent 0cbee197), round 1; supplementary;
my ic8_07 for this round's mutation scripts): the mutation runs (c2c_01, c2c_03, c2c_04) rewrite the working tree of
this repository (CG19). Here: no mutation is left in the code under review. The mutation lists of
reports/impl_c/c2_mutate_fix2.py (35) and c2_mutate_fix2b.py (1) are READ as data with ast (never imported or executed):
for each mutation the original text ("old") occurs exactly once in the STAGED blob of its file (a mutation left applied
would have removed it), the replacement text ("new") does not occur where it is not part of the original, and the staged
blob and the working-tree file are byte-identical. Data Auditor's own script.
usage: python -I -B ic9_07_mutation_remnants.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import subprocess
from ia_common import run

MUTS_FILES = {"metrix/e1-pilot/reports/impl_c/c2_mutate_fix2.py": 35, "metrix/e1-pilot/reports/impl_c/c2_mutate_fix2b.py": 1}
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
            c_new = blobs[path].count(new.value)
            c_new_in_old = old.value.count(new.value)
            n += 1
            new_ok = c_new == c_new_in_old * c or new.value in old.value or c_new == 0
            print("  %-66s %s: original occurs %d time(s) | replacement occurs %d (inside the original %d)%s" % (
                name, FILES[path].split("/")[-1], c, c_new, c_new_in_old * c,
                "" if new_ok else " -- replacement %r also occurs outside the original (informational)" % new.value))
            ok &= c == 1
        print("mutations read: %d (expected %d)" % (n, want_n))
        ok &= n == want_n
    return bool(ok)


run(main)
