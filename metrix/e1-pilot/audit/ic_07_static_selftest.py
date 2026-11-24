"""IC-7: positive controls for ic_06_static.py (does the static check notice the faults it is meant to find?).
A copy of the files ic_06 reads (metrix/e1-pilot/src/metrix_e1/*.py, reports/impl_b/dump_for_audit.py,
reports/round5/l6_check.py, tests/*.py) is placed under <work_dir>/<case>/ (a new directory); git objects are read from
the real repository through GIT_DIR (ic_06 only runs `git cat-file`, read-only).  ic_06 is run once on the unchanged copy
(must PASS) and once per seeded fault (each must FAIL):
  M1 data.build_general_dev opens eval_sets.jsonl in text mode (open(..., encoding="utf-8") instead of "rb");
  M2 data.build_general_dev JSON-parses every row before the non-dev continue;
  M3 test_data.check_preconditions no longer calls check_interpretations_ruled();
  M4 leakage.run_test_part uses test_qa before re-checking the committed records;
  M5 test_data.main calls generate_test inside the try block (before the refusal handler);
  M6 a new module function instantiates a TEST template ({E} substitution) outside test_data.build_test_qa.
The faults are text substitutions on the copies only; nothing in the repository is changed, nothing is imported or run
except ic_06_static.py itself.
Data Auditor's own script; no Executor code imported, called or copied (the copies are inputs to my static checker).
usage: python -I ic_07_static_selftest.py <repo_root> <work_dir (new)>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shutil, subprocess
from ia_common import run

FILES_DIRS = [("metrix/e1-pilot/src/metrix_e1", ".py"), ("metrix/e1-pilot/tests", ".py")]
FILES = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py", "metrix/e1-pilot/reports/round5/l6_check.py"]
D_ = "metrix/e1-pilot/src/metrix_e1/data.py"
TD = "metrix/e1-pilot/src/metrix_e1/test_data.py"
LK = "metrix/e1-pilot/src/metrix_e1/leakage.py"
CASES = {
    "control": [],
    "M1": [(D_, 'with open(eval_sets_path, "rb") as fh:', 'with open(eval_sets_path, encoding="utf-8") as fh:')],
    "M2": [(D_, "            rows_by_split[m.group(1).decode(\"ascii\", \"replace\")] += 1",
            "            r0 = json.loads(line.decode(\"utf-8\"))\n            rows_by_split[m.group(1).decode(\"ascii\", \"replace\")] += 1")],
    "M3": [(TD, "    check_interpretations_ruled()\n    return fz, LK.TestAuthorization", "    return fz, LK.TestAuthorization")],
    "M4": [(LK, "    from . import record as R\n", "    from . import record as R\n    n_q = len(test_qa)\n")],
    "M5": [(TD, "        fz, auth = check_preconditions(None, a.inputs, a.data)\n",
            "        fz, auth = check_preconditions(None, a.inputs, a.data)\n        generate_test(fz, auth, a.inputs, a.data)\n")],
    "M6": [(D_, "def build_general_dev(p, tok, eval_sets_path, parcae_path):",
            "def peek_test(fz, f):\n    return [t[\"text\"].replace(\"{E}\", f[\"entity\"]) for t in templates_by(fz).get((f[\"relation\"], \"TEST\"), [])]\n\n\n"
            "def build_general_dev(p, tok, eval_sets_path, parcae_path):")],
}


def main():
    repo, work = sys.argv[1:3]
    if os.path.exists(work):
        print("work_dir exists already; refusing to reuse:", work)
        return False
    os.makedirs(work)
    here = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ, GIT_DIR=os.path.join(repo, ".git"), PYTHONDONTWRITEBYTECODE="1")
    ok = True
    control_lines = None
    for case, subs in CASES.items():
        root = os.path.join(work, case)
        rels = list(FILES)
        for d, ext in FILES_DIRS:
            rels += [f"{d}/{x}" for x in sorted(os.listdir(os.path.join(repo, d))) if x.endswith(ext)]
        for rel in rels:
            os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
            shutil.copyfile(os.path.join(repo, rel), os.path.join(root, rel))
        applied = True
        for rel, a, b in subs:
            p = os.path.join(root, rel)
            s = open(p, encoding="utf-8").read()
            applied &= s.count(a) == 1
            open(p, "w", encoding="utf-8").write(s.replace(a, b, 1))
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(here, "ic_06_static.py"), root], capture_output=True, text=True, env=env)
        last = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
        want_pass = case == "control"
        good = applied and ((r.returncode == 0 and last == "RESULT: PASS") if want_pass else (r.returncode != 0 and last.startswith("RESULT: FAIL")))
        ok &= good
        print(f"{case}: fault applied {applied} | ic_06 exit {r.returncode} | last line {last!r} | expected {'PASS' if want_pass else 'FAIL'} -> {good}")
        lines = [ln for ln in r.stdout.split("\n") if not ln.startswith("env:")]
        if want_pass:
            control_lines = set(lines)
        else:
            changed = [ln.strip()[:200] for ln in lines if control_lines is not None and ln not in control_lines]
            changed.sort(key=lambda ln: not (ln.endswith("False") or "| False" in ln or ": False" in ln or "RESULT" in ln))
            print(f"   ic_06 output lines that differ from the control run ({len(changed)}; lines with a False check first):")
            for ln in changed[:6]:
                print(f"     {ln}")
    return bool(ok)


run(main)
