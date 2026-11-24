"""IE-7: positive controls for ie_06_static.py (does the static check notice the faults it is meant to find?).
A copy of the files ie_06 reads (metrix/e1-pilot/src/metrix_e1/*.py, src/metrix/e1_pilot/*.py,
reports/impl_b/dump_for_audit.py, the four reference scripts the tests run (reports/round2/anchor_check.py,
gen_facts.py, round5/l6_check.py, round7/gen_s_cands.py), tests/*.py) is placed under <work_dir>/<case>/ (a new
directory); git objects are read from the real repository through GIT_DIR (ie_06 only runs `git cat-file`, read-only).
ie_06 is run once on the unchanged copy (must PASS) and once per seeded fault (each must FAIL).
New for this round (the change under review):
  N1  tests/test_data_hashes.py::_dev_rows_only opens eval_sets.jsonl in text mode;
  N2  the test hands the real eval_sets.jsonl to l6_check.py again (instead of the DEV-rows copy);
  N3  _dev_rows_only UTF-8-decodes every row before matching its prefix;
  N4  _dev_rows_only also writes the non-dev rows into the copy;
  N5  _dev_rows_only's manifest copy also replaces another value (decode_tokenizer_json_sha256);
  N6  evaluate_model: the formal-mode-only check removed;
  N7  evaluate_model: the formal-mode-only check moved after the data access;
  N8  verify_authorization: the Gate 0 status re-check removed;
  N9  verify_authorization: the binding re-check removed;
  N10 verify_authorization: weakened status check (NOT_TESTED accepted);
  N11 verify_authorization reads a TEST file before its re-checks;
  N12 tests/test_st12.py::test_eval_sets_one_byte reads eval_sets.jsonl as text;
  N13 tests/test_st12.py::flip decodes the file it changes;
  N14 verify_authorization: the PROTOCOL_FROZEN re-check removed.
Carried over from my round 3 (id_07): M1 build_general_dev text mode; M2 json.loads before the non-dev continue;
M5 evaluate_model guard without verify_authorization; M6 generate_test verifies after reading facts; M7 run_test_part
uses test_qa before the verify; M8 hash comparison disabled.
The faults are text substitutions on the copies only; nothing in the repository is changed, nothing is imported or run
except ie_06_static.py itself.
Data Auditor's own script (adapted from my id_07_static_selftest.py); no Executor code imported, called or copied (the
copies are inputs to my static checker).
usage: python -I ie_07_static_selftest.py <repo_root> <work_dir (new)>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shutil, subprocess
from ia_common import run

FILES_DIRS = [("metrix/e1-pilot/src/metrix_e1", ".py"), ("metrix/e1-pilot/src/metrix/e1_pilot", ".py"), ("metrix/e1-pilot/tests", ".py")]
FILES = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py", "metrix/e1-pilot/reports/round5/l6_check.py",
         "metrix/e1-pilot/reports/round2/anchor_check.py", "metrix/e1-pilot/reports/round2/gen_facts.py",
         "metrix/e1-pilot/reports/round7/gen_s_cands.py"]
P = "metrix/e1-pilot/src/metrix_e1/"
D_, TD, LK, EV = P + "data.py", P + "test_data.py", P + "leakage.py", P + "evaluate.py"
TH, T12 = "metrix/e1-pilot/tests/test_data_hashes.py", "metrix/e1-pilot/tests/test_st12.py"
REAL_EV = 'PILOT.parents[1] / "research/mini_mythos/stage1/results/r1/eval_sets.jsonl"'
MODE_CHECK = ('        if not mode.formal:\n            raise ImplementationFail("TEST is evaluated in formal mode only (%s mode; protocol section 8 step 8: TEST "\n'
              '                                     "is evaluated once)" % mode.name)\n')
CASES = {
    "control": [],
    "N1": [(TH, 'with open(src, "rb") as fi, open(out, "wb") as fo:', 'with open(src, encoding="utf-8") as fi, open(out, "wb") as fo:')],
    "N2": [(TH, '_run([rep / "round5/l6_check.py", "--eval-sets", dev_rows,', '_run([rep / "round5/l6_check.py", "--eval-sets", ' + REAL_EV + ',')],
    "N3": [(TH, "            m = _ROW_SPLIT.match(line)\n", "            text = line.decode(\"utf-8\")\n            m = _ROW_SPLIT.match(line)\n")],
    "N4": [(TH, '            else:\n                n["other"] += 1\n', '            else:\n                fo.write(line)\n                n["other"] += 1\n')],
    "N5": [(TH, '    manifest["general_text"]["source_file_sha256"] = FZ.file_sha256(out)\n',
            '    manifest["general_text"]["source_file_sha256"] = FZ.file_sha256(out)\n'
            '    manifest["general_text"]["decode_tokenizer_json_sha256"] = "0" * 64\n')],
    "N6": [(EV, MODE_CHECK, "")],
    "N7": [(EV, MODE_CHECK, ""),
           (EV, "    facts, cands, qs = data[\"facts.jsonl\"], data[\"candidates.json\"], data[qa_file]\n",
            "    facts, cands, qs = data[\"facts.jsonl\"], data[\"candidates.json\"], data[qa_file]\n"
            "    if split == \"test\" and not mode.formal:\n        raise ImplementationFail(\"TEST is evaluated in formal mode only\")\n")],
    "N8": [(LK, '    if status != "PASS":\n        raise ImplementationFail("TEST path refused: committed Gate 0 status %r, not PASS" % (status,))\n', "")],
    "N9": [(LK, '    if recs["selection_freeze"].get("gate0_record_sha256") != authorization.gate0_record_sha256:\n'
                '        raise ImplementationFail("TEST path refused: the freeze record is not bound to the committed Gate 0 record")\n', "")],
    "N10": [(LK, '    if status != "PASS":\n', '    if status not in ("PASS", "NOT_TESTED"):\n')],
    "N11": [(LK, '    status = (recs["gate0"].get("gate0") or {}).get("gate0_status")\n',
             '    peek = (Path(repo_root) / "test_qa.jsonl").read_bytes()\n    status = (recs["gate0"].get("gate0") or {}).get("gate0_status")\n')],
    "N12": [(T12, "    flip(root / p.general_source)\n", "    (root / p.general_source).read_text(encoding=\"utf-8\")\n    flip(root / p.general_source)\n")],
    "N13": [(T12, "    b = bytearray(path.read_bytes())\n", "    b = bytearray(path.read_text(encoding=\"utf-8\").encode(\"utf-8\"))\n")],
    "N14": [(LK, '    if current != authorization.frozen_commit:\n', '    if current != authorization.frozen_commit and False:\n')],
    "M1": [(D_, 'with open(eval_sets_path, "rb") as fh:', 'with open(eval_sets_path, encoding="utf-8") as fh:')],
    "M2": [(D_, "            rows_by_split[m.group(1).decode(\"ascii\", \"replace\")] += 1",
            "            r0 = json.loads(line.decode(\"utf-8\"))\n            rows_by_split[m.group(1).decode(\"ascii\", \"replace\")] += 1")],
    "M5": [(EV, "        verify_authorization(test_authorization, repo_root)\n", "        pass\n")],
    "M6": [(TD, "    LK.verify_authorization(authorization, fz.repo_root)\n    p = D.params(fz)\n", "    p = D.params(fz)\n"),
           (TD, '    facts = FZ.read_jsonl(Path(data_dir) / "facts.jsonl")\n',
            '    facts = FZ.read_jsonl(Path(data_dir) / "facts.jsonl")\n    LK.verify_authorization(authorization, fz.repo_root)\n')],
    "M7": [(LK, "    verify_authorization(authorization, repo_root)\n    gate0 = run_gate0",
            "    n_q = len(test_qa)\n    verify_authorization(authorization, repo_root)\n    gate0 = run_gate0")],
    "M8": [(LK, "        if got != want:\n", "        if got != want and False:\n")],
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
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(here, "ie_06_static.py"), root], capture_output=True, text=True, env=env)
        last = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
        want_pass = case == "control"
        good = applied and ((r.returncode == 0 and last == "RESULT: PASS") if want_pass else (r.returncode != 0 and last.startswith("RESULT: FAIL")))
        ok &= good
        print(f"{case}: fault applied {applied} | ie_06 exit {r.returncode} | last line {last!r} | expected {'PASS' if want_pass else 'FAIL'} -> {good}")
        lines = [ln for ln in r.stdout.split("\n") if not ln.startswith("env:")]
        if want_pass:
            control_lines = set(lines)
        else:
            changed = [ln.strip()[:220] for ln in lines if control_lines is not None and ln not in control_lines]
            changed.sort(key=lambda ln: not (ln.endswith("False") or "| False" in ln or ": False" in ln or "False |" in ln or "RESULT" in ln
                                             or "Traceback" in ln or "Error" in ln or "at None" in ln))
            print(f"   ie_06 output lines that differ from the control run ({len(changed)}; lines with a False check or an error first):")
            for ln in changed[:5]:
                print(f"     {ln}")
    return bool(ok)


run(main)
