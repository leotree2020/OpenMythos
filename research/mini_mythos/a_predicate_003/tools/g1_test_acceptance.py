"""Acceptance logic of the G1 CPU test runner (PURE: no side effects, imports no project code; WRITTEN, NOT RUN).

The sentinel runner tools/run_g1_cpu_tests.py replaces process functions at import time, so its acceptance decision lives here, where tests and the static
audit can read it without importing the runner.  A run is an ACCEPTANCE PASS only when ALL of the following hold:
  * the selection is FULL (every group; a --groups run is diagnostic only and can never be an acceptance PASS, whatever it shows);
  * the set of expected test ids -- found by reading the test files with ast, every tests/test_g1_*.py, whether or not a group names it -- has exactly
    EXPECTED_TOTAL_TESTS members;
  * every expected id was executed exactly once and ended PASS (so: no missing test, no unselected test, no duplicate, no unexpected id);
  * 0 SKIP, 0 FAIL, 0 ERROR, 0 load errors, 0 process-safety sentinel hits.
Verdicts: FAIL (any FAIL / ERROR / load error / sentinel hit) > INCOMPLETE (anything else that is not a full, clean, complete run) > PASS.
Exit codes of the runner: PASS 0, FAIL 1, INCOMPLETE or REFUSED 3."""
import ast
import glob
import os

EXPECTED_TOTAL_TESTS = 289
EXIT_FOR = {"PASS": 0, "FAIL": 1, "INCOMPLETE": 3}


def discover_expected_ids(tests_dir, pattern="test_g1_*.py"):
    """-> sorted list of '<module>.<Class>.<test method>' for every test of every matching test file (classes defined in the file; no inheritance)."""
    ids = []
    for path in sorted(glob.glob(os.path.join(tests_dir, pattern))):
        mod = os.path.basename(path)[:-3]
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for c in tree.body:
            if isinstance(c, ast.ClassDef):
                for m in c.body:
                    if isinstance(m, ast.FunctionDef) and m.name.startswith("test_"):
                        ids.append("%s.%s.%s" % (mod, c.name, m.name))
    return sorted(ids)


def assess(full_selection, rows, expected_ids, expected_total, load_errors, sentinel_violations):
    """rows: [{'id': str, 'status': 'PASS'|'FAIL'|'ERROR'|'SKIP'}] as executed.  -> dict with verdict, exit_code and every number that decided it."""
    expected = list(expected_ids)
    executed = [r.get("id") for r in rows]
    counts = {k: sum(1 for r in rows if r.get("status") == k) for k in ("PASS", "FAIL", "ERROR", "SKIP")}
    other = [r for r in rows if r.get("status") not in ("PASS", "FAIL", "ERROR", "SKIP")]
    exp_set, ran_set = set(expected), set(executed)
    duplicates = sorted({i for i in executed if executed.count(i) > 1})
    missing = sorted(exp_set - ran_set)
    unexpected = sorted(ran_set - exp_set)
    pass_ids = {r["id"] for r in rows if r.get("status") == "PASS"}
    not_pass_expected = sorted(i for i in exp_set if i in ran_set and i not in pass_ids)
    fail_reasons, incomplete_reasons = [], []
    if counts["FAIL"] or counts["ERROR"]:
        fail_reasons.append("%d FAIL / %d ERROR" % (counts["FAIL"], counts["ERROR"]))
    if load_errors:
        fail_reasons.append("%d load error(s)" % len(load_errors))
    if sentinel_violations:
        fail_reasons.append("%d process-safety sentinel hit(s)" % len(sentinel_violations))
    if not full_selection:
        incomplete_reasons.append("partial selection (--groups): a diagnostic run is never an acceptance PASS")
    if counts["SKIP"]:
        incomplete_reasons.append("%d SKIP" % counts["SKIP"])
    if other:
        incomplete_reasons.append("%d row(s) with an unknown status" % len(other))
    if missing:
        incomplete_reasons.append("%d expected test(s) not executed" % len(missing))
    if unexpected:
        incomplete_reasons.append("%d executed id(s) that are not expected tests" % len(unexpected))
    if duplicates:
        incomplete_reasons.append("%d id(s) executed more than once" % len(duplicates))
    if len(exp_set) != len(expected) or len(exp_set) != expected_total:
        incomplete_reasons.append("expected test count %d (unique %d) != the frozen expectation %d" % (len(expected), len(exp_set), expected_total))
    if not (exp_set <= pass_ids and len(pass_ids) == expected_total):
        incomplete_reasons.append("%d unique test ids PASS, %d required" % (len(pass_ids), expected_total))
    if not rows:
        incomplete_reasons.append("no test was executed")
    verdict = "FAIL" if fail_reasons else ("INCOMPLETE" if incomplete_reasons else "PASS")
    return {"verdict": verdict, "exit_code": EXIT_FOR[verdict], "acceptance_scope": "FULL" if full_selection else "PARTIAL", "expected_total": expected_total,
            "expected_unique": len(exp_set), "executed_rows": len(rows), "executed_unique": len(ran_set), "pass_unique": len(pass_ids), "counts": counts,
            "missing_ids": missing, "unexpected_ids": unexpected, "duplicate_ids": duplicates, "expected_not_pass": not_pass_expected,
            "load_errors": len(load_errors), "sentinel_violations": len(sentinel_violations), "reasons": fail_reasons + incomplete_reasons}
