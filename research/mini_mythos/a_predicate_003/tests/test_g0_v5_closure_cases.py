"""Pure-logic tests for the closure marker g0_closed.json and the historical-run closure rules CL-01..CL-23: the 38 static closure cases of
g0_preflight_review/g0_v5_cases.json.  WRITTEN, NOT RUN (F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001); running them needs its own authorization.
The cases are design-review records; here each one is (a) evaluated as facts against the rules and (b) MATERIALISED as a run directory in a
temporary directory and read back with the real read-only fact collector of g0_run (no process is started, the repository is not touched)."""
import copy
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g0_v5_fixtures as F  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402
import g0_run as GR  # noqa: E402

CRIT = F.criteria()
V5 = F.load_v5_cases()
CASES = V5["cases"]
BY_ID = {c["id"]: c for c in CASES}
TOOL_SHA = GA.FROZEN_CRITERIA_SHA256
TOOL_ID = GA.CRITERIA_ID
GLOBAL_REASONS = {"ROOT_MANUAL_DISPOSITION", "LIVE_RESIDUE", "ROOT_LISTING_INCOMPLETE"}


# ------------------------------------------------------------------ materialising a run directory
def make_files(run_id, verdict="PASS", code=0, marker_sha=None, summary_sha=None, evidence_obj=None, evidence_bytes=None, summary_bytes=None,
               marker_verdict=None, marker_code=None, marker_run_id=None):
    ev = evidence_obj if evidence_obj is not None else {"run_id": run_id, "note": "evidence stand-in"}
    eb = evidence_bytes if evidence_bytes is not None else GJ.strict_bytes(ev)
    sm = {"run_id": run_id, "criteria_id": TOOL_ID, "criteria_sha256": summary_sha or TOOL_SHA, "evidence_sha256": GJ.sha256_hex(eb), "verdict": verdict, "exit_code": code}
    sb = summary_bytes if summary_bytes is not None else GJ.strict_bytes(sm)
    _, cb = GJ.build_marker(marker_run_id or run_id, marker_sha or TOOL_SHA, eb, sb, marker_verdict or verdict, code if marker_code is None else marker_code)
    return {"registry.jsonl": b"", "g0_evidence.json": eb, "g0_summary.json": sb, "g0_closed.json": cb, "g0_closed.json.tmp": cb}


def write_run(root, name, files):
    d = os.path.join(root, name)
    os.mkdir(d)
    for fname, content in files.items():
        p = os.path.join(d, fname)
        if content is None:
            continue
        if isinstance(content, tuple) and content[0] == "dir":
            os.mkdir(p)
        elif isinstance(content, tuple) and content[0] == "symlink":
            os.symlink(content[1], p)
        else:
            with open(p, "wb") as f:
                f.write(content)
    return d


def flip(b):
    """same length, different bytes"""
    return b[:-2] + (b"xy" if b[-2:] != b"xy" else b"yx")


def build(case_id, name):
    """-> (files dict for the run directory | None, extra) for one closure case.  Mirrors the narrative of the case record."""
    f = make_files(name)
    cb = f["g0_closed.json"]
    if case_id in ("A",):
        for k in ("g0_closed.json", "g0_closed.json.tmp"):
            f[k] = None
    elif case_id == "A2":
        f["g0_closed.json"] = f["g0_closed.json.tmp"] = None
        f["g0_summary.json"] = f["g0_summary.json"][: len(f["g0_summary.json"]) // 2]
    elif case_id in ("A3", "E", "F2"):
        f["g0_closed.json"] = None
        f["g0_closed.json.tmp"] = cb if case_id != "E" else cb[:30]
        if case_id == "E":
            f["g0_summary.json"] = f["g0_summary.json"]
    elif case_id == "B":
        f["g0_closed.json"], f["g0_closed.json.tmp"] = cb[:60], None
    elif case_id == "B2":
        f["g0_closed.json"], f["g0_closed.json.tmp"] = b"", None
    elif case_id == "B3":
        f["g0_closed.json"] = cb + b"\n"                    # the temporary file keeps the original bytes: fact tmp == 'other'
    elif case_id == "B4":
        f["g0_closed.json"], f["g0_closed.json.tmp"] = b'{"run_id":"g0_a","run_id":"g0_b"}', None
    elif case_id == "B5":
        f["g0_closed.json"], f["g0_closed.json.tmp"] = ("symlink", "/etc/hostname"), None
    elif case_id == "B6":
        f = make_files(name, verdict="FAIL", code=1)
        o = json.loads(f["g0_closed.json"].decode())
        o["recorded_exit_code"] = True
        f["g0_closed.json"], f["g0_closed.json.tmp"] = GJ.strict_bytes(o), None
    elif case_id == "C":
        f["g0_summary.json"] = flip(f["g0_summary.json"])
    elif case_id == "C2":
        f["g0_summary.json"] = f["g0_summary.json"][:-5]
    elif case_id == "C3":
        f["g0_summary.json"] = None
    elif case_id == "C4":
        f["g0_evidence.json"] = flip(f["g0_evidence.json"])
    elif case_id == "C5":
        f["g0_evidence.json"] = None
    elif case_id == "C6":
        f = make_files(name, marker_verdict="FAIL", marker_code=1)
    elif case_id == "C7":
        f = make_files(name, evidence_obj={"run_id": "g0_other"})
    elif case_id == "C8":
        other = make_files("g0_other", evidence_obj={"run_id": "g0_other", "different": True})
        f = {k: (v if k in ("registry.jsonl",) else None) for k, v in f.items()}
        # same lengths as the files the copied marker binds, different bytes: the fact is hash_mismatch (not size_mismatch)
        f["g0_evidence.json"] = flip(other["g0_evidence.json"])
        f["g0_summary.json"] = flip(other["g0_summary.json"])
        f["g0_closed.json"] = f["g0_closed.json.tmp"] = other["g0_closed.json"]
    elif case_id == "C9":
        f = make_files(name, summary_bytes=b"this is not json")
    elif case_id == "C10":
        f = make_files(name, evidence_bytes=b"this is not json either")
    elif case_id == "C11":
        f["g0_summary.json"] = ("dir",)
        f["g0_evidence.json"] = ("dir",)
    elif case_id == "D":
        f = make_files(name, marker_sha="f" * 64)
    elif case_id == "D2":
        f = make_files(name, marker_sha="f" * 64, summary_sha="f" * 64)
    elif case_id in ("F", "F3", "H"):
        pass
    elif case_id == "G":
        f["MANUAL_DISPOSITION_REQUIRED.json"] = b"{}"
    elif case_id == "G3":
        f["MANUAL_DISPOSITION_REQUIRED.json"] = b"{}"
    elif case_id in ("G2", "G4"):
        pass
    elif case_id == "H2":
        f = make_files(name, verdict="FAIL", code=1)
    elif case_id == "H3":
        f = make_files(name, verdict="BLOCKED", code=3)
    elif case_id == "H4":
        f["g0_closed.json.tmp"] = None
    elif case_id == "I":
        f["g0_closed.json.tmp"] = b"something else entirely"
    elif case_id == "I2":
        f["g0_closed.json.bak"] = cb
    elif case_id in ("J", "K"):
        return None
    else:
        raise AssertionError("no builder for case %s" % case_id)
    return f


def expected_unresolved(name, reasons):
    return [("%s:%s" % (name, r)) if r not in GLOBAL_REASONS else (":%s" % r) for r in reasons if r not in GLOBAL_REASONS] + \
           [(":%s" % r) for r in reasons if r in GLOBAL_REASONS]


class TestMarkerSchema(unittest.TestCase):
    def test_marker_fields_and_consts_are_the_frozen_ones(self):
        ms = CRIT["closure"]["marker_schema"]
        self.assertEqual(tuple(f["path"] for f in ms["fields"]), GJ.MARKER_KEYS)
        self.assertEqual(ms["id"], GJ.MARKER_SCHEMA)
        self.assertEqual(ms["max_bytes"], GJ.MARKER_MAX_BYTES)

    def test_a_built_marker_is_valid_canonical_and_binds_the_bytes(self):
        f = make_files("g0_run_1")
        state, obj = GJ.classify_marker(f["g0_closed.json"])
        self.assertEqual(state, "ok")
        self.assertEqual(obj["run_id"], "g0_run_1")
        self.assertEqual(obj["criteria_id"], "E1A-GATE-G0-CRITERIA-V5")
        self.assertEqual(obj["criteria_sha256"], TOOL_SHA)
        self.assertEqual(obj["evidence_sha256"], GJ.sha256_hex(f["g0_evidence.json"]))
        self.assertEqual(obj["summary_sha256"], GJ.sha256_hex(f["g0_summary.json"]))
        self.assertEqual(obj["evidence_bytes"], len(f["g0_evidence.json"]))
        self.assertEqual((obj["recorded_verdict"], obj["recorded_exit_code"], obj["process_exit_proof"]), ("PASS", 0, False))
        self.assertEqual(f["g0_closed.json"], GJ.strict_bytes(obj))
        self.assertNotIn(b"\n", f["g0_closed.json"])

    def test_the_marker_never_claims_process_exit_proof(self):
        f = make_files("g0_run_1")
        o = json.loads(f["g0_closed.json"].decode())
        o["process_exit_proof"] = True
        self.assertEqual(GJ.classify_marker(GJ.strict_bytes(o))[0], "schema_invalid")

    def test_each_marker_defect_is_classified(self):
        good = make_files("g0_run_1")["g0_closed.json"]
        o = json.loads(good.decode())
        tests = {
            "oversize_or_empty": [b"", b"x" * (GJ.MARKER_MAX_BYTES + 1)],
            "unparsable": [good[:40], b"\xff\xfe", b"[1,2", b'{"a":NaN}', b'{"run_id":"a","run_id":"b"}'],
            "noncanonical": [good + b"\n", b" " + good, json.dumps(o, indent=1).encode()],
            "schema_invalid": [b"[]", b"3", json.dumps({k: v for k, v in o.items() if k != "run_id"}, sort_keys=True, separators=(",", ":")).encode(),
                               json.dumps(dict(o, extra=1), sort_keys=True, separators=(",", ":")).encode(),
                               GJ.strict_bytes(dict(o, evidence_bytes=True)), GJ.strict_bytes(dict(o, evidence_sha256="ABC")),
                               GJ.strict_bytes(dict(o, recorded_verdict="PASS", recorded_exit_code=1)), GJ.strict_bytes(dict(o, run_id="not_g0")),
                               GJ.strict_bytes(dict(o, closed_schema="e1a-gate-g0-closed-2")), GJ.strict_bytes(dict(o, criteria_id="E1A-GATE-G0-CRITERIA-V4"))],
        }
        for want, raws in tests.items():
            for raw in raws:
                self.assertEqual(GJ.classify_marker(raw)[0], want, raw[:50])

    def test_build_marker_refuses_an_impossible_pair(self):
        with self.assertRaises(ValueError):
            GJ.build_marker("g0_x", TOOL_SHA, b"e", b"s", "PASS", 1)
        with self.assertRaises(ValueError):
            GJ.build_marker("g0_x", "nothex", b"e", b"s", "PASS", 0)
        with self.assertRaises(ValueError):
            GJ.build_marker("x", TOOL_SHA, b"e", b"s", "PASS", 0)

    def test_every_recorded_verdict_pair_is_allowed(self):
        for verdict, code in (("PASS", 0), ("FAIL", 1), ("BLOCKED", 3)):
            self.assertEqual(GJ.classify_marker(GJ.build_marker("g0_x", TOOL_SHA, b"e", b"s", verdict, code)[1])[0], "ok")

    def test_strict_bytes_refuses_non_json_values_and_nan(self):
        for bad in ({"a": {1, 2}}, {"a": float("nan")}, {"a": float("inf")}, {"a": object()}):
            with self.assertRaises((TypeError, ValueError)):
                GJ.strict_bytes(bad)

    def test_parse_strict_refuses_duplicates_and_non_finite_constants(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b"\xff"):
            with self.assertRaises(ValueError):
                GJ.parse_strict(raw)


class TestClosureRulesAsFacts(unittest.TestCase):
    def test_the_case_file_has_38_closure_cases_and_19_pipeline_cases(self):
        self.assertEqual(len(CASES), 38)
        self.assertEqual(len(V5["pipeline_cases"]), 19)
        self.assertTrue({"A", "B", "C", "D", "E", "F", "G", "H"} <= set(BY_ID))

    def test_every_case_gets_its_recorded_reasons_from_the_frozen_rules(self):
        bad = []
        for c in CASES:
            hits = GJ.closure_reasons(c["run_dir"], c["global"], CRIT)
            reasons = [h["reason"] for h in hits]
            if reasons != c["expected"]["reasons"]:
                bad.append((c["id"], reasons, c["expected"]["reasons"]))
            acts = sorted({h["human_action"] for h in hits})
            if acts != sorted(c["expected"]["human_actions"]):
                bad.append((c["id"], "actions", acts))
        self.assertEqual(bad, [])

    def test_only_a_valid_bound_marker_without_residue_is_closed(self):
        ok = [c["id"] for c in CASES if not GJ.closure_reasons(c["run_dir"], c["global"], CRIT)]
        self.assertEqual(sorted(ok), sorted(["F", "F3", "H", "H2", "H3", "H4"]))

    def test_the_existence_of_the_summary_never_closes_a_run(self):
        for cid in ("A", "A2", "A3"):
            c = BY_ID[cid]
            self.assertIn("g0_summary.json", c["files_present"])
            self.assertEqual([h["reason"] for h in GJ.closure_reasons(c["run_dir"], c["global"], CRIT)], ["NO_CLOSED"], cid)

    def test_every_rule_is_exercised_by_a_case(self):
        seen = set()
        for c in CASES:
            seen |= {h["id"] for h in GJ.closure_reasons(c["run_dir"], c["global"], CRIT)}
        self.assertEqual(seen, {r["id"] for r in CRIT["closure"]["preflight"]["rules"]})

    def test_the_closure_marker_is_not_proof_of_process_exit(self):
        c = copy.deepcopy(BY_ID["H"])
        c["global"]["live_marker_process"] = True
        self.assertEqual([h["reason"] for h in GJ.closure_reasons(c["run_dir"], c["global"], CRIT)], ["LIVE_RESIDUE"])
        c = copy.deepcopy(BY_ID["H"])
        c["run_dir"]["manual_disposition"] = True
        self.assertEqual([h["reason"] for h in GJ.closure_reasons(c["run_dir"], c["global"], CRIT)], ["MANUAL_DISPOSITION"])

    def test_any_recorded_verdict_closes_a_run_but_not_a_manual_disposition(self):
        for cid in ("H", "H2", "H3"):
            self.assertEqual(GJ.closure_reasons(BY_ID[cid]["run_dir"], BY_ID[cid]["global"], CRIT), [])
        self.assertTrue(GJ.closure_reasons(BY_ID["G"]["run_dir"], BY_ID["G"]["global"], CRIT))


class TestClosureCasesMaterialised(unittest.TestCase):
    """Each case as real files in a temporary evidence root, read with g0_run.collect_run_facts / closure_preflight (read-only)."""

    def run_case(self, cid):
        c = BY_ID[cid]
        name = "g0_case_%s" % cid.lower()
        with tempfile.TemporaryDirectory() as root:
            files = build(cid, name)
            live = []
            if cid in ("G2", "G3"):
                live = [{"pid": 4242, "cmdline": "python3 g0_run.py"}]
            if cid == "G4" or cid == "K":
                pass
            if cid == "J":
                os.mkdir(os.path.join(root, "elsewhere"))
                os.symlink(os.path.join(root, "elsewhere"), os.path.join(root, name))
            elif files is not None:
                write_run(root, name, files)
            if cid == "G4":
                open(os.path.join(root, "MANUAL_DISPOSITION_REQUIRED.json"), "w").write("{}")
            if cid == "K":
                real = os.listdir

                def broken(p="."):
                    if os.fspath(p) == root:
                        raise PermissionError(13, "denied")
                    return real(p)
                with mock.patch.object(GR.os, "listdir", side_effect=broken):
                    unresolved, details = GR.closure_preflight(root, CRIT, live)
            else:
                unresolved, details = GR.closure_preflight(root, CRIT, live)
            return c, name, unresolved, details

    def test_every_closure_case_gives_the_recorded_preflight_result(self):
        bad = []
        for cid in BY_ID:
            c, name, unresolved, details = self.run_case(cid)
            want = expected_unresolved(name, c["expected"]["reasons"])
            if cid == "K":
                want = [":ROOT_LISTING_INCOMPLETE"]
            if unresolved != want:
                bad.append((cid, unresolved, want))
        self.assertEqual(bad, [])

    def test_the_collected_facts_equal_the_facts_of_the_case_record(self):
        bad = []
        for cid, c in BY_ID.items():
            if c["run_dir"] is None:
                continue
            _, name, unresolved, details = self.run_case(cid)
            got = details["entries"][name]["facts"]
            if got != c["run_dir"]:
                bad.append((cid, {k: (got.get(k), c["run_dir"].get(k)) for k in set(got) | set(c["run_dir"]) if got.get(k) != c["run_dir"].get(k)}))
        self.assertEqual(bad, [])

    def test_preflight_reads_only_it_creates_repairs_and_deletes_nothing(self):
        for cid in ("A2", "B", "G", "I"):
            name = "g0_ro_%s" % cid.lower()
            with tempfile.TemporaryDirectory() as root:
                write_run(root, name, build(cid, name))
                before = {fn: open(os.path.join(root, name, fn), "rb").read() for fn in os.listdir(os.path.join(root, name)) if os.path.isfile(os.path.join(root, name, fn))}
                GR.closure_preflight(root, CRIT, [])
                after = {fn: open(os.path.join(root, name, fn), "rb").read() for fn in os.listdir(os.path.join(root, name)) if os.path.isfile(os.path.join(root, name, fn))}
                self.assertEqual(before, after, cid)

    def test_a_missing_evidence_root_means_there_is_no_earlier_run(self):
        with tempfile.TemporaryDirectory() as d:
            unresolved, details = GR.closure_preflight(os.path.join(d, "no_such_root"), CRIT, [])
        self.assertEqual(unresolved, [])
        self.assertEqual(details["global_facts"]["root_listing"], "complete")

    def test_the_consumption_directory_is_not_a_run_directory(self):
        with tempfile.TemporaryDirectory() as root:
            os.mkdir(os.path.join(root, "_g0_consumed"))
            open(os.path.join(root, "notes.txt"), "w").write("x")
            unresolved, details = GR.closure_preflight(root, CRIT, [])
        self.assertEqual((unresolved, list(details["entries"])), ([], []))

    def test_several_earlier_runs_are_all_judged_and_listed(self):
        with tempfile.TemporaryDirectory() as root:
            write_run(root, "g0_a_closed", make_files("g0_a_closed"))
            write_run(root, "g0_b_open", build("A", "g0_b_open"))
            write_run(root, "g0_c_manual", dict(make_files("g0_c_manual"), **{"MANUAL_DISPOSITION_REQUIRED.json": b"{}"}))
            unresolved, _ = GR.closure_preflight(root, CRIT, [])
        self.assertEqual(unresolved, ["g0_b_open:NO_CLOSED", "g0_c_manual:MANUAL_DISPOSITION"])

    def test_a_foreign_owned_or_non_directory_entry_is_not_a_real_run_directory(self):
        with tempfile.TemporaryDirectory() as root:
            open(os.path.join(root, "g0_file"), "w").write("x")
            unresolved, _ = GR.closure_preflight(root, CRIT, [])
        self.assertEqual(unresolved, ["g0_file:NOT_A_DIRECTORY"])

    def test_c01_text_and_the_unresolved_format(self):
        c01 = CRIT["checks"]["G0-C01"]["text"]
        self.assertIn("never makes a run closed", c01)
        with tempfile.TemporaryDirectory() as root:
            write_run(root, "g0_x_open", build("A", "g0_x_open"))
            unresolved, _ = GR.closure_preflight(root, CRIT, [{"pid": 1}])
        self.assertEqual(unresolved, ["g0_x_open:NO_CLOSED", ":LIVE_RESIDUE"])

    def test_read_bound_classifies_the_bound_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.json")
            data = GJ.strict_bytes({"a": 1})
            open(p, "wb").write(data)
            self.assertEqual(GR.read_bound(p, GJ.sha256_hex(data), len(data))[0], "ok")
            self.assertEqual(GR.read_bound(p, GJ.sha256_hex(data), len(data) + 1)[0], "size_mismatch")
            self.assertEqual(GR.read_bound(p, "0" * 64, len(data))[0], "hash_mismatch")
            self.assertEqual(GR.read_bound(os.path.join(d, "none"), "0" * 64, 1)[0], "absent")
            junk = b"not json!"
            open(p, "wb").write(junk)
            self.assertEqual(GR.read_bound(p, GJ.sha256_hex(junk), len(junk))[0], "unparsable")
            self.assertEqual(GR.read_bound(p, "0" * 64, GR.MAX_BOUND_BYTES + 1)[0], "size_mismatch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
