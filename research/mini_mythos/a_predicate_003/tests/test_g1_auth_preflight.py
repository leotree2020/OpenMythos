"""G1 authorization, reference run and history checks (CPU; WRITTEN, NOT RUN -- NOT TESTED).  Pure files in temporary directories; no process is started and
no authorization file is created outside a temporary directory.  Covers: schema isolation (G0 / E1-A authorizations are void), binding and grant checks,
expiry, single use (a consumed authorization is refused), the frozen-file check, the G0 REAL-001 reference run, and the closure facts / rules of earlier
'g1_' runs (an unclosed or damaged earlier run is unresolved)."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_fixtures as F  # noqa: E402
import common as C  # noqa: E402
import g0_auth as GA  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_judge as GJ  # noqa: E402
import g1_run as R  # noqa: E402

NOW = "2026-11-01T00:00:00Z"
CRIT = F.criteria()


def good_auth():
    return {"schema": G1A.AUTH_SCHEMA, "stage": "G1", "authorized_by": "owner", "authorization_id": "OWNER-G1-TEST-0001", "date": "2026-11-01",
            "expires_utc": "2099-01-01T00:00:00Z", "bindings": F.bindings(), "grants": copy.deepcopy(G1A.REQUIRED_GRANTS), "not_granted": list(G1A.MUST_NOT_GRANT)}


class TestAuthorizationValidation(unittest.TestCase):
    def problems(self, **changes):
        a = good_auth()
        for path, val in changes.items():
            cur = a
            parts = path.split(".")
            for p in parts[:-1]:
                cur = cur[p]
            if val is KeyError:
                del cur[parts[-1]]
            else:
                cur[parts[-1]] = val
        return G1A.validate(a, F.bindings(), NOW)

    def test_the_reference_authorization_is_valid(self):
        self.assertEqual(G1A.validate(good_auth(), F.bindings(), NOW), [])

    def test_g0_and_e1a_authorizations_are_void_for_g1(self):
        self.assertTrue(self.problems(schema="e1a-gate-auth-1"))
        self.assertTrue(self.problems(schema="e1a-auth-2"))
        self.assertTrue(self.problems(stage="G0"))
        self.assertTrue(self.problems(stage="G2"))
        self.assertTrue(self.problems(authorized_by="agent"))

    def test_g1_schema_is_rejected_by_the_g0_interlock(self):
        cur = GA.current_bindings("a" * 40, "b" * 64, "c" * 64)
        self.assertTrue(GA.validate(good_auth(), cur, NOW))

    def test_every_binding_must_equal_its_current_value(self):
        for k in G1A.BINDING_KEYS:
            self.assertTrue(self.problems(**{"bindings." + k: "0" * 64}), k)
            self.assertTrue(self.problems(**{"bindings." + k: KeyError}), k)
            self.assertTrue(self.problems(**{"bindings." + k: ""}), k)

    def test_the_frozen_hashes_are_the_only_acceptable_ones_even_if_current_agrees(self):
        cur = F.bindings()
        for k in ("g1_criteria_sha256", "g1_prereg_sha256", "g0_criteria_sha256", "g0_prereg_sha256", "g0_reference_sha256"):
            a = good_auth()
            a["bindings"][k] = cur[k] = "9" * 64
            self.assertTrue(G1A.validate(a, cur, NOW), k)
            cur = F.bindings()

    def test_unknown_binding_or_authorization_keys_are_refused(self):
        self.assertTrue(self.problems(**{"bindings.extra": "x"}))
        self.assertTrue(self.problems(extra_key=1))

    def test_grants_must_be_exactly_the_frozen_ones(self):
        for path, val in (("grants.runs", 2), ("grants.forks", 5), ("grants.forks", 3), ("grants.signals", 1), ("grants.fault_injection", True),
                          ("grants.max_concurrent_children", 2), ("grants.max_seconds", 31), ("grants.max_seconds", 20), ("grants.tests", ["T1_ABORT"]),
                          ("grants.tests", list(reversed(G1A.TESTS))), ("grants.extra", 1)):
            self.assertTrue(self.problems(**{path: val}), path)
        self.assertTrue(self.problems(grants=None))

    def test_not_granted_must_list_everything_else(self):
        for missing in G1A.MUST_NOT_GRANT:
            a = good_auth()
            a["not_granted"].remove(missing)
            self.assertTrue(G1A.validate(a, F.bindings(), NOW), missing)
        self.assertTrue(self.problems(not_granted="all"))

    def test_expiry_is_required_and_enforced(self):
        self.assertTrue(self.problems(expires_utc="2026-10-31T00:00:00Z"))
        self.assertTrue(self.problems(expires_utc=NOW))
        self.assertTrue(self.problems(expires_utc=None))
        self.assertTrue(self.problems(expires_utc=KeyError))
        self.assertTrue(self.problems(expires_utc=20991231))

    def test_the_authorization_id_must_be_a_plain_identifier(self):
        for bad in ("", "a", "../x", "has space", "x" * 80, None, 7, "-lead"):
            self.assertTrue(self.problems(authorization_id=bad), repr(bad))

    def test_non_object_authorizations(self):
        for bad in (None, [], "x", 3):
            self.assertEqual(G1A.validate(bad, F.bindings(), NOW), ["authorization is not a JSON object"])

    def test_template_is_not_valid(self):
        t = json.loads(G1A.template())
        self.assertTrue(t["schema"].startswith("TEMPLATE-NOT-VALID-"))
        self.assertTrue(G1A.validate(t, F.bindings(), NOW))

    def test_no_function_of_the_module_writes_an_authorization_file(self):
        import ast
        tree = ast.parse(open(os.path.join(G1A.HERE, "g1_auth.py"), encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open":
                mode = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else "r"
                self.assertFalse(any(c in str(mode) for c in "wax+"), "open() with mode %r at line %d" % (mode, n.lineno))


class TestLoadAndSingleUse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "AUTH.json")
        self.consumed = os.path.join(self.tmp.name, "consumed")
        os.mkdir(self.consumed)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, obj):
        with open(self.path, "w") as f:
            json.dump(obj, f)

    def test_a_valid_authorization_loads_and_returns_the_raw_bytes(self):
        self.write(good_auth())
        auth, raw = G1A.load(self.path, F.bindings(), NOW, self.consumed)
        self.assertEqual(auth["authorization_id"], "OWNER-G1-TEST-0001")
        self.assertEqual(raw, open(self.path, "rb").read())

    def test_a_consumed_authorization_is_refused_single_use(self):
        self.write(good_auth())
        with open(G1A.consumed_marker("OWNER-G1-TEST-0001", self.consumed), "w") as f:
            f.write("{}")
        with self.assertRaises(G1A.G1AuthorizationError) as cm:
            G1A.load(self.path, F.bindings(), NOW, self.consumed)
        self.assertIn("already consumed", str(cm.exception))

    def test_a_different_id_is_not_blocked_by_another_consumption(self):
        a = good_auth()
        a["authorization_id"] = "OWNER-G1-TEST-0002"
        self.write(a)
        with open(G1A.consumed_marker("OWNER-G1-TEST-0001", self.consumed), "w") as f:
            f.write("{}")
        self.assertEqual(G1A.load(self.path, F.bindings(), NOW, self.consumed)[0]["authorization_id"], "OWNER-G1-TEST-0002")

    def test_missing_unreadable_or_invalid_files_are_refused(self):
        with self.assertRaises(G1A.G1AuthorizationError):
            G1A.load(os.path.join(self.tmp.name, "nope.json"), F.bindings(), NOW, self.consumed)
        with open(self.path, "w") as f:
            f.write("{not json")
        with self.assertRaises(G1A.G1AuthorizationError):
            G1A.load(self.path, F.bindings(), NOW, self.consumed)
        with open(self.path, "wb") as f:
            f.write(b"\xff\xfe")
        with self.assertRaises(G1A.G1AuthorizationError):
            G1A.load(self.path, F.bindings(), NOW, self.consumed)
        self.write(dict(good_auth(), schema="e1a-gate-auth-1"))
        with self.assertRaises(G1A.G1AuthorizationError):
            G1A.load(self.path, F.bindings(), NOW, self.consumed)

    def test_the_consumed_marker_path_is_inside_the_g1_consumption_directory(self):
        self.assertTrue(G1A.consumed_marker("X-1").startswith(G1A.CONSUMED_DIR))
        self.assertTrue(G1A.CONSUMED_DIR.endswith("_g1_consumed"))
        self.assertNotEqual(G1A.CONSUMED_DIR, GA.CONSUMED_DIR)


class TestFrozenFiles(unittest.TestCase):
    def test_the_real_tree_has_no_problem(self):
        self.assertEqual(G1A.frozen_problems(), [])

    def test_a_changed_or_missing_g1_file_is_a_problem(self):
        with tempfile.TemporaryDirectory() as d:
            for name in G1A.FROZEN_G1_FILES:
                with open(os.path.join(G1A.HERE, name), "rb") as f, open(os.path.join(d, name), "wb") as g:
                    g.write(f.read())
            self.assertEqual([p for p in G1A.frozen_problems(d) if "g1_" in p or "G1_" in p], [])
            with open(os.path.join(d, G1A.CRITERIA_FILE), "ab") as g:
                g.write(b" ")
            self.assertTrue(any(G1A.CRITERIA_FILE in p for p in G1A.frozen_problems(d)))
            os.unlink(os.path.join(d, G1A.PREREG_MD_FILE))
            self.assertTrue(any("unreadable" in p for p in G1A.frozen_problems(d)))

    def test_the_g0_frozen_files_are_part_of_the_check(self):
        with tempfile.TemporaryDirectory() as d:
            problems = G1A.frozen_problems(g0_dir=d)
            self.assertTrue(any("g0_criteria_v5.json" in p for p in problems))

    def test_g1_code_hash_covers_the_four_files(self):
        self.assertEqual(G1A.G1_CODE_FILES, ("g1_auth.py", "g1_judge.py", "g1_run.py", "g1_criteria_v1.json"))
        self.assertRegex(G1A.g1_code_hash(), r"^[0-9a-f]{64}$")


class TestG0ReferenceRun(unittest.TestCase):
    def make(self, root, run_id="g0_20261101_000000_aaaaaa", verdict="PASS", code=0):
        d = os.path.join(root, run_id)
        os.makedirs(d)
        ev, sm = b'{"run_id":"%s"}' % run_id.encode(), b'{"verdict":"PASS"}'
        marker = json.dumps({"run_id": run_id, "recorded_verdict": verdict, "recorded_exit_code": code, "evidence_sha256": hashlib.sha256(ev).hexdigest(),
                             "summary_sha256": hashlib.sha256(sm).hexdigest()}).encode()
        for name, data in (("g0_evidence.json", ev), ("g0_summary.json", sm), ("g0_closed.json", marker)):
            with open(os.path.join(d, name), "wb") as f:
                f.write(data)
        return {"run_id": run_id, "closed_sha256": hashlib.sha256(marker).hexdigest(), "evidence_sha256": hashlib.sha256(ev).hexdigest(),
                "summary_sha256": hashlib.sha256(sm).hexdigest(), "verdict": "PASS"}, d

    def test_absent_reference_run_is_not_ok(self):
        with tempfile.TemporaryDirectory() as root:
            st = G1A.g0_reference_status(root)
            self.assertFalse(st["ok"])
            self.assertTrue(st["problems"])
            self.assertIsNone(st["closed_sha256"])

    def test_a_matching_closed_pass_run_is_ok(self):
        with tempfile.TemporaryDirectory() as root:
            ref, _ = self.make(root)
            with mock.patch.object(G1A, "G0_REFERENCE", ref):
                st = G1A.g0_reference_status(root)
            self.assertEqual((st["ok"], st["problems"], st["closed_sha256"]), (True, [], ref["closed_sha256"]))

    def test_a_tampered_file_or_a_non_pass_marker_is_not_ok(self):
        with tempfile.TemporaryDirectory() as root:
            ref, d = self.make(root)
            with open(os.path.join(d, "g0_summary.json"), "ab") as f:
                f.write(b" ")
            with mock.patch.object(G1A, "G0_REFERENCE", ref):
                self.assertFalse(G1A.g0_reference_status(root)["ok"])
        with tempfile.TemporaryDirectory() as root:
            ref, _ = self.make(root, verdict="FAIL", code=1)
            with mock.patch.object(G1A, "G0_REFERENCE", ref):
                st = G1A.g0_reference_status(root)
            self.assertFalse(st["ok"])
            self.assertTrue(any("verdict PASS" in p for p in st["problems"]))

    def test_a_symlink_or_unparsable_marker_is_not_ok(self):
        with tempfile.TemporaryDirectory() as root:
            ref, d = self.make(root)
            os.rename(os.path.join(d, "g0_evidence.json"), os.path.join(root, "elsewhere.json"))
            os.symlink(os.path.join(root, "elsewhere.json"), os.path.join(d, "g0_evidence.json"))
            with mock.patch.object(G1A, "G0_REFERENCE", ref):
                self.assertFalse(G1A.g0_reference_status(root)["ok"])
        with tempfile.TemporaryDirectory() as root:
            ref, d = self.make(root)
            with open(os.path.join(d, "g0_closed.json"), "wb") as f:
                f.write(b"{broken")
            ref2 = dict(ref, closed_sha256=hashlib.sha256(b"{broken").hexdigest())
            with mock.patch.object(G1A, "G0_REFERENCE", ref2):
                self.assertFalse(G1A.g0_reference_status(root)["ok"])

    def test_current_bindings_names_ten_values_and_an_unreadable_reference(self):
        with tempfile.TemporaryDirectory() as root:
            b = G1A.current_bindings("a" * 40, "b" * 64, "c" * 64, evidence_root=root)
        self.assertEqual(set(b), set(G1A.BINDING_KEYS))
        self.assertEqual(b["g0_reference_sha256"], "UNREADABLE")
        self.assertEqual(b["g1_criteria_sha256"], G1A.FROZEN_G1_CRITERIA_SHA256)
        self.assertEqual(b["g0_criteria_sha256"], GA.FROZEN_CRITERIA_SHA256)


def make_closed_run(root, name, verdict="PASS", code=0, tool_sha=None):
    """A complete closed g1 run directory (as the pipeline publishes it).  -> path."""
    d = os.path.join(root, name)
    os.makedirs(d)
    crit_sha = tool_sha or C.sha256_file(G1A.CRITERIA_PATH)
    ev = GJ.strict_bytes({"run_id": name})
    evh = hashlib.sha256(ev).hexdigest()
    sm = GJ.strict_bytes({"run_id": name, "criteria_id": G1A.CRITERIA_ID, "criteria_sha256": crit_sha, "evidence_sha256": evh, "verdict": verdict, "exit_code": code})
    obj, mk = GJ.build_marker(name, crit_sha, ev, sm, verdict, code)
    for fn, data in (("g1_evidence.json", ev), ("g1_summary.json", sm), ("g1_closed.json", mk), ("g1_closed.json.tmp", mk)):
        with open(os.path.join(d, fn), "wb") as f:
            f.write(data)
    return d


class TestClosurePreflightOfEarlierG1Runs(unittest.TestCase):
    def pre(self, root, residue=()):
        return R.closure_preflight(root, CRIT, list(residue))

    def test_no_evidence_root_or_an_empty_one_is_clean(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.pre(root)[0], [])
            self.assertEqual(self.pre(os.path.join(root, "absent"))[0], [])

    def test_a_properly_closed_run_is_resolved_whatever_its_verdict(self):
        with tempfile.TemporaryDirectory() as root:
            make_closed_run(root, "g1_20261101_000000_aaaaaa")
            make_closed_run(root, "g1_20261101_000001_bbbbbb", "FAIL", 1)
            make_closed_run(root, "g1_20261101_000002_cccccc", "BLOCKED", 3)
            self.assertEqual(self.pre(root)[0], [])

    def test_a_directory_without_a_marker_is_unresolved(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "g1_20261101_000000_aaaaaa"))
            self.assertEqual(self.pre(root)[0], ["g1_20261101_000000_aaaaaa:NO_CLOSED"])

    def test_a_summary_without_a_marker_does_not_close_the_run(self):
        with tempfile.TemporaryDirectory() as root:
            d = make_closed_run(root, "g1_20261101_000000_aaaaaa")
            os.unlink(os.path.join(d, "g1_closed.json"))
            self.assertEqual(self.pre(root)[0], ["g1_20261101_000000_aaaaaa:NO_CLOSED"])

    def test_damaged_markers_and_bound_files_are_unresolved(self):
        cases = {"CLOSED_PARSE": lambda d: open(os.path.join(d, "g1_closed.json"), "wb").write(b"{trunc"),
                 "CLOSED_NONCANONICAL": lambda d: open(os.path.join(d, "g1_closed.json"), "ab").write(b"\n"),
                 "SUMMARY_HASH": lambda d: open(os.path.join(d, "g1_summary.json"), "ab").write(b" "),
                 "EVIDENCE_HASH": lambda d: open(os.path.join(d, "g1_evidence.json"), "ab").write(b" "),
                 "SUMMARY_MISSING": lambda d: os.unlink(os.path.join(d, "g1_summary.json")),
                 "EVIDENCE_MISSING": lambda d: os.unlink(os.path.join(d, "g1_evidence.json")),
                 "STRAY_CLOSURE_FILE": lambda d: open(os.path.join(d, "g1_closed.json.tmp"), "wb").write(b"other"),
                 "MANUAL_DISPOSITION": lambda d: open(os.path.join(d, "MANUAL_DISPOSITION_REQUIRED.json"), "w").write("{}")}
        for reason, damage in cases.items():
            with tempfile.TemporaryDirectory() as root:
                name = "g1_20261101_000000_aaaaaa"
                damage(make_closed_run(root, name))
                un = self.pre(root)[0]
                self.assertIn("%s:%s" % (name, reason), un, reason)

    def test_a_marker_for_another_criteria_or_run_is_unresolved(self):
        with tempfile.TemporaryDirectory() as root:
            make_closed_run(root, "g1_20261101_000000_aaaaaa", tool_sha="e" * 64)
            self.assertIn("g1_20261101_000000_aaaaaa:CRITERIA_MISMATCH", self.pre(root)[0])
        with tempfile.TemporaryDirectory() as root:
            d = make_closed_run(root, "g1_20261101_000000_aaaaaa")
            os.rename(d, os.path.join(root, "g1_20261101_000000_dddddd"))
            self.assertIn("g1_20261101_000000_dddddd:CLOSED_RUNID", self.pre(root)[0])

    def test_a_symlink_or_a_file_instead_of_a_run_directory_is_unresolved(self):
        with tempfile.TemporaryDirectory() as root:
            make_closed_run(root, "g1_20261101_000009_target")
            os.symlink(os.path.join(root, "g1_20261101_000009_target"), os.path.join(root, "g1_20261101_000000_aaaaaa"))
            with open(os.path.join(root, "g1_20261101_000001_bbbbbb"), "w") as f:
                f.write("x")
            un = self.pre(root)[0]
            self.assertIn("g1_20261101_000000_aaaaaa:NOT_A_DIRECTORY", un)
            self.assertIn("g1_20261101_000001_bbbbbb:NOT_A_DIRECTORY", un)

    def test_global_rules(self):
        with tempfile.TemporaryDirectory() as root:
            open(os.path.join(root, "MANUAL_DISPOSITION_REQUIRED.json"), "w").write("{}")
            self.assertIn(":ROOT_MANUAL_DISPOSITION", self.pre(root)[0])
        with tempfile.TemporaryDirectory() as root:
            self.assertIn(":LIVE_RESIDUE", self.pre(root, residue=[{"pid": 1}])[0])
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(R.os, "listdir", side_effect=PermissionError(13, "denied")):
                self.assertIn(":ROOT_LISTING_INCOMPLETE", self.pre(root)[0])

    def test_only_g1_prefixed_entries_are_judged_here(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "g0_20261027_000000_aaaaaa"))
            os.makedirs(os.path.join(root, "_g1_consumed"))
            os.makedirs(os.path.join(root, "unrelated"))
            self.assertEqual(self.pre(root)[0], [])

    def test_the_g0_history_is_judged_by_the_g0_engine_and_blocks_g1(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "g0_20261027_000000_aaaaaa"))
            un, _ = R.GR.closure_preflight(root, R.GJ0.load_criteria(), [])
            self.assertEqual(un, ["g0_20261027_000000_aaaaaa:NO_CLOSED"])

    def test_the_rules_are_read_from_the_frozen_g1_criteria(self):
        ids = [r["id"] for r in CRIT["closure"]["preflight"]["rules"]]
        self.assertEqual(ids, ["CL1-%02d" % i for i in range(1, 24)])
        facts = R.collect_run_facts("x", "/nonexistent/x", G1A.CRITERIA_ID, "0" * 64)
        self.assertEqual(facts, {"entry": "unreadable"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
