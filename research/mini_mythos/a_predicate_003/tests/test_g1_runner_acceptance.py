"""G1 CPU runner acceptance (CPU; WRITTEN, NOT RUN -- NOT TESTED).  Negative controls for the review finding that the runner could report PASS for a run with
SKIPs, unselected tests or too few executed tests: a PASS needs a FULL selection, every expected test id executed exactly once and PASS, 0 SKIP / FAIL / ERROR /
load error / sentinel hit.  Pure: tools/g1_test_acceptance.py has no side effects (the runner itself is never imported here -- importing it would install the
process sentinels); the runner is checked by reading its source with ast.  No process is started."""
import ast
import os
import re
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
TOOLS = os.path.join(A003, "tools")
sys.path.insert(0, TOOLS)
import g1_test_acceptance as ACC  # noqa: E402


def make_ids(n):
    return ["test_g1_demo.TestDemo.test_%03d" % i for i in range(n)]


def make_rows(ids, status="PASS"):
    return [{"id": i, "status": status} for i in ids]


def assess(rows, expected=None, total=10, full=True, load_errors=(), violations=()):
    expected = make_ids(total) if expected is None else expected
    return ACC.assess(full, rows, expected, total, list(load_errors), list(violations))


def load_mutant(repl):
    path = os.path.join(TOOLS, "g1_test_acceptance.py")
    src = open(path, encoding="utf-8").read()
    for old, new in repl:
        assert src.count(old) == 1, "anchor not unique: %r" % old
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_acceptance")
    mod.__file__ = path
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


class TestAcceptancePass(unittest.TestCase):
    def test_a_full_clean_complete_run_is_the_only_pass(self):
        a = assess(make_rows(make_ids(10)))
        self.assertEqual((a["verdict"], a["exit_code"], a["acceptance_scope"], a["reasons"]), ("PASS", 0, "FULL", []))
        self.assertEqual((a["expected_total"], a["expected_unique"], a["executed_unique"], a["pass_unique"]), (10, 10, 10, 10))
        self.assertEqual((a["missing_ids"], a["unexpected_ids"], a["duplicate_ids"], a["counts"]["SKIP"]), ([], [], [], 0))

    def test_exit_codes(self):
        self.assertEqual(ACC.EXIT_FOR, {"PASS": 0, "FAIL": 1, "INCOMPLETE": 3})


class TestIncompleteIsNeverPass(unittest.TestCase):
    def test_a_skip_is_not_a_pass(self):
        ids = make_ids(10)
        rows = make_rows(ids[:9]) + [{"id": ids[9], "status": "SKIP"}]
        a = assess(rows)
        self.assertEqual((a["verdict"], a["exit_code"]), ("INCOMPLETE", 3))
        self.assertEqual((a["counts"]["SKIP"], a["pass_unique"], a["missing_ids"]), (1, 9, []))
        self.assertEqual(a["expected_not_pass"], [ids[9]])

    def test_a_skip_next_to_an_otherwise_complete_run_is_not_a_pass(self):
        rows = make_rows(make_ids(10)) + [{"id": "test_g1_demo.TestDemo.test_skipped", "status": "SKIP"}]
        a = assess(rows)
        self.assertEqual(a["verdict"], "INCOMPLETE")
        self.assertEqual(a["unexpected_ids"], ["test_g1_demo.TestDemo.test_skipped"])

    def test_an_unselected_group_is_not_a_pass_and_a_diagnostic_run_never_is(self):
        ids = make_ids(10)
        a = assess(make_rows(ids[:6]))
        self.assertEqual((a["verdict"], len(a["missing_ids"]), a["pass_unique"]), ("INCOMPLETE", 4, 6))
        full_pass_rows_but_partial_selection = assess(make_rows(ids), full=False)
        self.assertEqual((full_pass_rows_but_partial_selection["verdict"], full_pass_rows_but_partial_selection["acceptance_scope"]), ("INCOMPLETE", "PARTIAL"))
        self.assertTrue(any("partial selection" in r for r in full_pass_rows_but_partial_selection["reasons"]))

    def test_fewer_executed_tests_than_expected_is_not_a_pass(self):
        for n in (0, 1, 9):
            a = assess(make_rows(make_ids(n)))
            self.assertEqual((a["verdict"], a["exit_code"]), ("INCOMPLETE", 3), n)
        self.assertTrue(any("no test was executed" in r for r in assess([])["reasons"]))

    def test_a_run_with_the_right_number_of_rows_but_other_ids_is_not_a_pass(self):
        a = assess(make_rows(make_ids(9) + ["test_g1_demo.TestDemo.test_other"]))
        self.assertEqual((a["verdict"], len(a["missing_ids"]), len(a["unexpected_ids"])), ("INCOMPLETE", 1, 1))

    def test_a_duplicated_id_cannot_make_up_for_a_missing_one(self):
        ids = make_ids(10)
        a = assess(make_rows(ids[:9] + [ids[0]]))
        self.assertEqual(a["verdict"], "INCOMPLETE")
        self.assertEqual((a["duplicate_ids"], a["missing_ids"], a["executed_rows"], a["executed_unique"]), ([ids[0]], [ids[9]], 10, 9))
        b = assess(make_rows(ids + [ids[3]]))
        self.assertEqual((b["verdict"], b["duplicate_ids"]), ("INCOMPLETE", [ids[3]]))

    def test_the_expected_total_must_match_the_frozen_expectation(self):
        a = ACC.assess(True, make_rows(make_ids(9)), make_ids(9), 10, [], [])
        self.assertEqual(a["verdict"], "INCOMPLETE")
        self.assertTrue(any("frozen expectation" in r for r in a["reasons"]))
        dup_expected = make_ids(9) + [make_ids(9)[0]]
        b = ACC.assess(True, make_rows(make_ids(9)), dup_expected, 10, [], [])
        self.assertEqual(b["verdict"], "INCOMPLETE")

    def test_expected_failures_and_unexpected_successes_and_unknown_statuses_are_not_pass(self):
        ids = make_ids(10)
        for status in ("XFAIL", "XPASS", "WEIRD", None):
            rows = make_rows(ids[:9]) + [{"id": ids[9], "status": status}]
            a = assess(rows)
            self.assertEqual(a["verdict"], "INCOMPLETE", status)

    def test_a_missing_status_key_is_not_a_pass(self):
        ids = make_ids(10)
        a = assess(make_rows(ids[:9]) + [{"id": ids[9]}])
        self.assertNotEqual(a["verdict"], "PASS")


class TestFailureIsNeverPassOrIncomplete(unittest.TestCase):
    def test_fail_and_error_rows_fail_the_run(self):
        ids = make_ids(10)
        for bad in ("FAIL", "ERROR"):
            a = assess(make_rows(ids[:9]) + [{"id": ids[9], "status": bad}])
            self.assertEqual((a["verdict"], a["exit_code"]), ("FAIL", 1), bad)

    def test_a_failing_subtest_row_fails_the_run(self):
        ids = make_ids(10)
        rows = make_rows(ids) + [{"id": ids[0] + " (subtest name)", "status": "FAIL"}]
        self.assertEqual(assess(rows)["verdict"], "FAIL")

    def test_a_load_error_fails_the_run_even_when_every_executed_row_passed(self):
        a = assess(make_rows(make_ids(10)), load_errors=[{"module": "test_g1_demo", "error": "ImportError"}])
        self.assertEqual((a["verdict"], a["load_errors"]), ("FAIL", 1))

    def test_a_sentinel_violation_fails_the_run_even_when_every_row_passed(self):
        a = assess(make_rows(make_ids(10)), violations=["os.kill"])
        self.assertEqual((a["verdict"], a["exit_code"], a["sentinel_violations"]), ("FAIL", 1, 1))

    def test_fail_takes_precedence_over_incomplete(self):
        a = assess(make_rows(make_ids(3)), full=False, violations=["subprocess.run"])
        self.assertEqual(a["verdict"], "FAIL")
        self.assertTrue(any("sentinel" in r for r in a["reasons"]) and any("partial" in r for r in a["reasons"]))


class TestDiscoveryOfTheExpectedTests(unittest.TestCase):
    def test_every_test_of_every_test_file_is_found_with_a_unique_id(self):
        ids = ACC.discover_expected_ids(HERE)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), ACC.EXPECTED_TOTAL_TESTS)
        for i in ids:
            self.assertRegex(i, r"^test_g1_[a-z_]+\.Test[A-Za-z0-9]+\.test_[a-z0-9_]+$")
        mods = {i.split(".")[0] for i in ids}
        self.assertEqual(mods, {"test_g1_judge_cases", "test_g1_auth_preflight", "test_g1_run_parts", "test_g1_boundaries", "test_g1_mutations", "test_g1_runner_acceptance"})

    def test_a_test_file_that_no_group_names_is_still_expected(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "test_g1_extra.py"), "w") as f:
                f.write("import unittest\nclass TestX(unittest.TestCase):\n    def test_a(self):\n        pass\n    def helper(self):\n        pass\n    def test_b(self):\n        pass\n")
            with open(os.path.join(d, "test_other.py"), "w") as f:
                f.write("import unittest\nclass TestY(unittest.TestCase):\n    def test_c(self):\n        pass\n")
            self.assertEqual(ACC.discover_expected_ids(d), ["test_g1_extra.TestX.test_a", "test_g1_extra.TestX.test_b"])

    def test_the_runner_groups_name_every_test_file_and_the_acceptance_is_used(self):
        src = open(os.path.join(TOOLS, "run_g1_cpu_tests.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        groups = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GROUPS" for t in n.targets))
        named = {c.value for c in ast.walk(groups.value) if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value.startswith("test_g1_")}
        files = {f[:-3] for f in os.listdir(HERE) if re.match(r"test_g1_.*\.py$", f)}
        self.assertEqual(named, files)

    def test_the_runner_can_return_pass_only_through_the_acceptance_function(self):
        src = open(os.path.join(TOOLS, "run_g1_cpu_tests.py"), encoding="utf-8").read()
        self.assertNotIn("all_ok", src)
        self.assertNotIn('report["verdict"] = "PASS"', src)
        self.assertIn("ACC.assess(full_selection, all_rows,", src)
        self.assertIn("full_selection = sel is None", src)
        self.assertIn('report["verdict"] = acc["verdict"]', src)
        self.assertIn('return acc["exit_code"]', src)
        main = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "main")
        for n in ast.walk(main):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant):
                self.assertNotEqual(n.value.value, 0, "main() returns the PASS code at line %d" % n.lineno)

    def test_skips_and_expected_failures_are_recorded_by_the_runner(self):
        src = open(os.path.join(TOOLS, "run_g1_cpu_tests.py"), encoding="utf-8").read()
        for name in ("addSkip", "addExpectedFailure", "addUnexpectedSuccess"):
            self.assertIn("def %s(" % name, src)

    def test_the_acceptance_module_has_no_side_effects(self):
        tree = ast.parse(open(os.path.join(TOOLS, "g1_test_acceptance.py"), encoding="utf-8").read())
        imports = {a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {"ast", "glob", "os"})
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
        for n in calls:
            self.assertNotIn(n.func.attr, ("kill", "fork", "system", "popen", "remove", "unlink", "rename", "replace"))


class TestAcceptanceMutations(unittest.TestCase):
    """Each mutant removes one rule; the targeted case must then be judged differently (the rule is not vacuous)."""

    def verdicts(self, repl, **kw):
        rows = kw.pop("rows")
        args = dict(full=True, load_errors=[], violations=[], total=10, expected=None)
        args.update(kw)
        expected = make_ids(args["total"]) if args["expected"] is None else args["expected"]
        real = ACC.assess(args["full"], rows, expected, args["total"], args["load_errors"], args["violations"])["verdict"]
        mutant = load_mutant(repl).assess(args["full"], rows, expected, args["total"], args["load_errors"], args["violations"])["verdict"]
        return real, mutant

    def test_the_partial_selection_rule_matters(self):
        self.assertEqual(self.verdicts([("    if not full_selection:\n", "    if False:\n")], rows=make_rows(make_ids(10)), full=False), ("INCOMPLETE", "PASS"))

    def test_the_missing_test_rules_matter(self):
        rows = make_rows(make_ids(9))
        repl = [("    if missing:\n", "    if False:\n"), ("    if not (exp_set <= pass_ids and len(pass_ids) == expected_total):\n", "    if False:\n"),
                ("    if not rows:\n", "    if False:\n")]
        self.assertEqual(self.verdicts(repl, rows=rows), ("INCOMPLETE", "PASS"))

    def test_the_sentinel_rule_matters(self):
        self.assertEqual(self.verdicts([("    if sentinel_violations:\n", "    if False:\n")], rows=make_rows(make_ids(10)), violations=["os.kill"]), ("FAIL", "PASS"))

    def test_the_load_error_rule_matters(self):
        self.assertEqual(self.verdicts([("    if load_errors:\n", "    if False:\n")], rows=make_rows(make_ids(10)), load_errors=[{"module": "m"}]), ("FAIL", "PASS"))

    def test_the_fail_and_error_rule_matters(self):
        ids = make_ids(10)
        rows = make_rows(ids[:9]) + [{"id": ids[9], "status": "FAIL"}]
        real, mutant = self.verdicts([('    if counts["FAIL"] or counts["ERROR"]:\n', "    if False:\n")], rows=rows)
        self.assertEqual(real, "FAIL")
        self.assertNotEqual(mutant, "FAIL")

    def test_the_duplicate_rule_matters(self):
        ids = make_ids(10)
        self.assertEqual(self.verdicts([("    if duplicates:\n", "    if False:\n")], rows=make_rows(ids + [ids[0]])), ("INCOMPLETE", "PASS"))

    def test_the_frozen_expectation_rule_matters(self):
        repl = [("    if len(exp_set) != len(expected) or len(exp_set) != expected_total:\n", "    if False:\n"),
                ("    if not (exp_set <= pass_ids and len(pass_ids) == expected_total):\n", "    if False:\n")]
        rows = make_rows(make_ids(9))
        real = ACC.assess(True, rows, make_ids(9), 10, [], [])["verdict"]
        mutant = load_mutant(repl).assess(True, rows, make_ids(9), 10, [], [])["verdict"]
        self.assertEqual((real, mutant), ("INCOMPLETE", "PASS"))

    def test_the_anchors_exist_exactly_once(self):
        src = open(os.path.join(TOOLS, "g1_test_acceptance.py"), encoding="utf-8").read()
        for old in ("    if not full_selection:\n", "    if missing:\n", "    if not (exp_set <= pass_ids and len(pass_ids) == expected_total):\n", "    if not rows:\n",
                    "    if sentinel_violations:\n", "    if load_errors:\n", '    if counts["FAIL"] or counts["ERROR"]:\n', "    if duplicates:\n",
                    "    if len(exp_set) != len(expected) or len(exp_set) != expected_total:\n"):
            self.assertEqual(src.count(old), 1, old)


if __name__ == "__main__":
    unittest.main(verbosity=2)
