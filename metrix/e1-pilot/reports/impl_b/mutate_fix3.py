import subprocess, sys
from pathlib import Path
SP, PY = sys.argv[1], sys.argv[2]
E = Path("metrix/e1-pilot/src/metrix_e1")
muts = [
 ("loop NaN check removed", E / "evaluate.py", "                past, nxt = o.past_key_values, _finite_argmax(o.logits[:, -1].float())",
  "                past, nxt = o.past_key_values, o.logits[:, -1].float().argmax(-1)", "tests/test_evaluate.py"),
 ("pending check removed", E / "leakage.py", "    open_ids = INT.pending()\n    if open_ids:", "    open_ids = []\n    if open_ids:", "tests/test_test_data.py"),
 ("freeze content check removed", E / "leakage.py", "                         (R.SELECTION_FREEZE_REL, R.freeze_record_problem(", "                         (R.SELECTION_FREEZE_REL, None and R.freeze_record_problem(", "tests/test_test_data.py"),
 ("fz commit check removed", E / "leakage.py", "    if not authorization.frozen_commit == current == fz.record.commit:", "    if not authorization.frozen_commit == current:", "tests/test_test_data.py"),
 ("checkpoint check removed", E / "record.py", "    if missing:\n        return \"no checkpoint", "    if False:\n        return \"no checkpoint", "tests/test_test_data.py"),
 ("data hash check removed", E / "record.py", "    if rec.get(\"data_content_hashes\") != content_hashes:", "    if False:", "tests/test_test_data.py"),
]
for name, path, old, new, tests in muts:
    orig = path.read_bytes()
    s = orig.decode()
    assert s.count(old) == 1, name
    path.write_text(s.replace(old, new), encoding="utf-8")
    try:
        r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "metrix/e1-pilot/" + tests], capture_output=True, text=True)
        last = r.stdout.strip().split("\n")[-1]
        print("%-30s -> exit %d | %s" % (name, r.returncode, last))
        for l in r.stdout.split("\n"):
            if l.startswith("FAILED"):
                print("    ", l[:150])
    finally:
        path.write_bytes(orig)
