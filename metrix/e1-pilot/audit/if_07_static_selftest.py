"""IF-7: positive controls for if_06_static.py (does the static check notice the faults it is meant to find?).
A copy of the files if_06 reads (metrix/e1-pilot/src/metrix_e1/*.py, src/metrix/e1_pilot/*.py, tests/*.py,
reports/impl_b/dump_for_audit.py, the four reference scripts the tests run, reports/impl_b/t12_fix3.txt,
PROTOCOL_FROZEN, DATA_MANIFEST.json) is placed under <work_dir>/<case>/ (a new directory); git objects are read from
the real repository through GIT_DIR (if_06 only runs `git cat-file`, read-only); eval_sets.jsonl is not copied: if_06
hashes the real repository's file (second argument), whole file only.
if_06 is run once on the unchanged copy (must PASS) and once per seeded fault (each must FAIL).
New for this round (the change under review):
  P1  verify_authorization: the frozen-commit check no longer compares fz.record.commit;
  P2  verify_authorization: the result of freeze_record_problem ignored;
  P3  verify_authorization: the pending-interpretation check removed;
  P4  verify_authorization: `content` taken from the committed record itself instead of the frozen data_hash;
  P5  frozen.CONTENT_HASH_KEYS without anchor_texts;
  P6  frozen.DATA_TABLE_ROWS: the facts and anchor_texts keys swapped;
  P7  record.freeze_record_problem: checkpoint check removed;
  P8  record.freeze_record_problem: data content hash check removed;
  P9  record.freeze_record_problem: binding check disabled;
  P10 record.gate0_record_problem accepts NOT_TESTED;
  P11 record.freeze_record_problem: plan = [] (selected configurations unchecked, checkpoint check vacuous);
  P12 test_data.check_selection_record without the shared check;
  P13 test_data.check_gate0_record without the shared check;
  P14 generate_test verifies after check_inputs;
  P15 run_test_part uses test_qa before the verify;
  P16 evaluate_model: the fz-is-None refusal replaced by skipping the verify;
  P17 evaluate_model: the verify removed from the guard;
  P18 verify_authorization reads a TEST file first;
  P19 contract.load (in the closure of verify_authorization) reads a TEST file;
  P20 _dev_rows_only: whole-file hash check removed;
  P21 _dev_rows_only: whole-file hash check moved after the copy;
  P22 _dev_rows_only opens eval_sets.jsonl in text mode;
  P23 _dev_rows_only decodes each row before matching;
  P24 _dev_rows_only also writes the non-dev rows;
  P25 _dev_rows_only's manifest copy also replaces another value;
  P26 the test hands the real eval_sets.jsonl to l6_check.py;
  P27 a test calls generate_test with an authorization that passes verify_authorization (throw-away repository);
  P28 verify_authorization: NotCommitted swallowed;
  P29 verify_authorization: an unreadable PROTOCOL_FROZEN accepted;
  P30 test_data.check_selection_record passes {} instead of the data directory's content hashes.
Carried over: M1 build_general_dev text mode; M2 json.loads before the non-dev continue; M8 hash comparison disabled;
N12 test_eval_sets_one_byte reads eval_sets.jsonl as text; N13 flip decodes the file it changes.
The faults are text substitutions on the copies only; nothing in the repository is changed, nothing is imported or run
except if_06_static.py itself.
Data Auditor's own script (adapted from my ie_07_static_selftest.py); no Executor code imported, called or copied (the
copies are inputs to my static checker).
usage: python -I if_07_static_selftest.py <repo_root> <work_dir (new)>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shutil, subprocess
from ia_common import run

FILES_DIRS = [("metrix/e1-pilot/src/metrix_e1", ".py"), ("metrix/e1-pilot/src/metrix/e1_pilot", ".py"), ("metrix/e1-pilot/tests", ".py")]
FILES = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py", "metrix/e1-pilot/reports/round5/l6_check.py",
         "metrix/e1-pilot/reports/round2/anchor_check.py", "metrix/e1-pilot/reports/round2/gen_facts.py",
         "metrix/e1-pilot/reports/round7/gen_s_cands.py", "metrix/e1-pilot/reports/impl_b/t12_fix3.txt",
         "metrix/e1-pilot/PROTOCOL_FROZEN", "metrix/e1-pilot/DATA_MANIFEST.json"]
P = "metrix/e1-pilot/src/metrix_e1/"
D_, TD, LK, EV, RC, FZ, CT = (P + x for x in ("data.py", "test_data.py", "leakage.py", "evaluate.py", "record.py", "frozen.py", "contract.py"))
TH, T12, TT = "metrix/e1-pilot/tests/test_data_hashes.py", "metrix/e1-pilot/tests/test_st12.py", "metrix/e1-pilot/tests/test_test_data.py"
SHA_ASSERT = '    assert FZ.file_sha256(src) == fz.data_hash("eval_sets")\n'
BY_SPLIT = '    by_split = generated["info"]["general_dev"]["rows_by_split"]\n'
VERIFY_EV = ('        if fz is None:\n            raise ImplementationFail("TEST path refused: the frozen files (fz) are needed to check the authorization")\n'
             '        verify_authorization(test_authorization, fz)\n')
CASES = {
    "control": [],
    "P1": [(LK, "    if not authorization.frozen_commit == current == fz.record.commit:\n", "    if not authorization.frozen_commit == current:\n")],
    "P2": [(LK, "(R.SELECTION_FREEZE_REL, R.freeze_record_problem(", "(R.SELECTION_FREEZE_REL, None and R.freeze_record_problem(")],
    "P3": [(LK, "    open_ids = INT.pending()\n    if open_ids:", "    open_ids = []\n    if open_ids:")],
    "P4": [(LK, "    content = {k: fz.data_hash(k) for k in FZ.CONTENT_HASH_KEYS}\n", '    content = recs["selection_freeze"].get("data_content_hashes")\n')],
    "P5": [(FZ, 'CONTENT_HASH_KEYS = ("facts", "train_S", "candidates", "anchor_texts")', 'CONTENT_HASH_KEYS = ("facts", "train_S", "candidates")')],
    "P6": [(FZ, '"fact(160 条)": ("facts",', '"fact(160 条)": ("anchor_texts",'), (FZ, '"锚文本(512 篇解码文本)": ("anchor_texts",', '"锚文本(512 篇解码文本)": ("facts",')],
    "P7": [(RC, '    if missing:\n        return "no checkpoint', '    if False:\n        return "no checkpoint')],
    "P8": [(RC, '    if rec.get("data_content_hashes") != content_hashes:\n', "    if False:\n")],
    "P9": [(RC, '    if rec.get("gate0_record_sha256") != gate0_sha:\n', '    if rec.get("gate0_record_sha256") != gate0_sha and False:\n')],
    "P10": [(RC, '    return None if status == "PASS" else', '    return None if status in ("PASS", "NOT_TESTED") else')],
    "P11": [(RC, "        plan = training_plan(contract, selected)\n", "        plan = []\n")],
    "P12": [(TD, "    problem = R.freeze_record_problem(rec, contract, content_hashes, gate0_sha)\n", "    problem = None\n")],
    "P13": [(TD, "    problem = R.gate0_record_problem(rec)\n", "    problem = None\n")],
    "P14": [(TD, "    LK.verify_authorization(authorization, fz)\n    p = D.params(fz)\n    paths = D.check_inputs(fz, p, inputs_dir)\n",
             "    p = D.params(fz)\n    paths = D.check_inputs(fz, p, inputs_dir)\n    LK.verify_authorization(authorization, fz)\n")],
    "P15": [(LK, "    verify_authorization(authorization, fz, repo_root)\n    split_manifest = fz.split_manifest\n",
             "    n_q = len(test_qa)\n    verify_authorization(authorization, fz, repo_root)\n    split_manifest = fz.split_manifest\n")],
    "P16": [(EV, VERIFY_EV, "        if fz is not None:\n            verify_authorization(test_authorization, fz)\n")],
    "P17": [(EV, "        verify_authorization(test_authorization, fz)\n", "        pass\n")],
    "P18": [(LK, "    root = Path(repo_root) if repo_root is not None else fz.repo_root\n",
             '    root = Path(repo_root) if repo_root is not None else fz.repo_root\n    peek = (root / "test_qa.jsonl").read_bytes()\n')],
    "P19": [(CT, "    ss, dm, text = fz.search_space, fz.data_manifest, fz.protocol_text\n",
             '    ss, dm, text = fz.search_space, fz.data_manifest, fz.protocol_text\n    extra = open(fz.repo_root / "general_test.jsonl").read()\n')],
    "P20": [(TH, SHA_ASSERT, "")],
    "P21": [(TH, SHA_ASSERT, ""), (TH, BY_SPLIT, SHA_ASSERT + BY_SPLIT)],
    "P22": [(TH, 'with open(src, "rb") as fi, open(out, "wb") as fo:', 'with open(src, encoding="utf-8") as fi, open(out, "wb") as fo:')],
    "P23": [(TH, "            m = _ROW_SPLIT.match(line)\n", "            text = line.decode(\"utf-8\")\n            m = _ROW_SPLIT.match(line)\n")],
    "P24": [(TH, '            else:\n                n["other"] += 1\n', '            else:\n                fo.write(line)\n                n["other"] += 1\n')],
    "P25": [(TH, '    manifest["general_text"]["source_file_sha256"] = FZ.file_sha256(out)\n',
             '    manifest["general_text"]["source_file_sha256"] = FZ.file_sha256(out)\n    manifest["general_text"]["decode_tokenizer_json_sha256"] = "0" * 64\n')],
    "P26": [(TH, '_run([rep / "round5/l6_check.py", "--eval-sets", dev_rows,', '_run([rep / "round5/l6_check.py", "--eval-sets", fz.repo_root / D.params(fz).general_source,')],
    "P27": [(TT, "    LK.verify_authorization(LK.TestAuthorization(fz.record.commit, _sha(g), _sha(sel)), fz, root)   # all checks hold\n",
             "    LK.verify_authorization(LK.TestAuthorization(fz.record.commit, _sha(g), _sha(sel)), fz, root)   # all checks hold\n"
             "    TD.generate_test(fz, LK.TestAuthorization(fz.record.commit, _sha(g), _sha(sel)), None, generated[\"dir\"])\n")],
    "P28": [(LK, '        except R.NotCommitted as e:\n            raise ImplementationFail("TEST path refused: %s" % e) from e\n',
             "        except R.NotCommitted as e:\n            continue\n")],
    "P29": [(LK, '    except (OSError, ST12Error) as e:\n        raise ImplementationFail("TEST path refused: cannot read PROTOCOL_FROZEN: %s" % e) from e\n',
             "    except (OSError, ST12Error) as e:\n        current = authorization.frozen_commit\n")],
    "P30": [(TD, "    problem = R.freeze_record_problem(rec, contract, content_hashes, gate0_sha)\n",
             "    problem = R.freeze_record_problem(rec, contract, {}, gate0_sha)\n")],
    "M1": [(D_, 'with open(eval_sets_path, "rb") as fh:', 'with open(eval_sets_path, encoding="utf-8") as fh:')],
    "M2": [(D_, "            rows_by_split[m.group(1).decode(\"ascii\", \"replace\")] += 1",
            "            r0 = json.loads(line.decode(\"utf-8\"))\n            rows_by_split[m.group(1).decode(\"ascii\", \"replace\")] += 1")],
    "M8": [(LK, "        if got != want:\n", "        if got != want and False:\n")],
    "N12": [(T12, "    flip(root / p.general_source)\n", "    (root / p.general_source).read_text(encoding=\"utf-8\")\n    flip(root / p.general_source)\n")],
    "N13": [(T12, "    b = bytearray(path.read_bytes())\n", "    b = bytearray(path.read_text(encoding=\"utf-8\").encode(\"utf-8\"))\n")],
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
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(here, "if_06_static.py"), root, repo], capture_output=True, text=True, env=env)
        last = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
        want_pass = case == "control"
        good = applied and ((r.returncode == 0 and last == "RESULT: PASS") if want_pass else (r.returncode != 0 and last.startswith("RESULT: FAIL")))
        ok &= good
        print(f"{case}: fault applied {applied} | if_06 exit {r.returncode} | last line {last!r} | expected {'PASS' if want_pass else 'FAIL'} -> {good}")
        lines = [ln for ln in r.stdout.split("\n") if not ln.startswith("env:")]
        if want_pass:
            control_lines = set(lines)
        else:
            changed = [ln.strip()[:220] for ln in lines if control_lines is not None and ln not in control_lines]
            changed.sort(key=lambda ln: not (ln.endswith("False") or "| False" in ln or ": False" in ln or "False |" in ln or "RESULT" in ln
                                             or "Traceback" in ln or "Error" in ln or "at None" in ln))
            print(f"   if_06 output lines that differ from the control run ({len(changed)}; lines with a False check or an error first):")
            for ln in changed[:4]:
                print(f"     {ln}")
    return bool(ok)


run(main)
