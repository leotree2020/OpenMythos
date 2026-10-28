"""J1 test SOURCE (static skeleton).  NOT RUN, NOT IMPORTED, NOT COMPILED in the implementation stage (F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-PREP-001).

These tests are NOT the 18 V0.1 fixtures: no fixture S/O JSON, fixture hash or fixture-id-to-verdict table is materialised here (that is a separately
authorised later stage).  The inputs below are small inline illustrations of the intended behaviour of each handler, so that a later, separately
authorised CPU stage has something to run.  Their expected values are INTENTIONS, not results: every test in this file is NOT TESTED.

A later runner must keep the process-safety sentinel of the G1 CPU runner idea (no fork / exec / subprocess / signal / wait); nothing here needs any.
"""
import ast
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
J1_DIR = os.path.dirname(HERE)
G2_DIR = os.path.dirname(J1_DIR)
if G2_DIR not in sys.path:
    sys.path.insert(0, G2_DIR)

from j1 import codec, judge, oracle, schema  # noqa: E402

PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"


# ---------------------------------------------------------------- inline builders (illustrative, fictional pids)
def _trust():
    def entry(role, syn, kinds):
        return {"role": role, "synthetic_assumption": syn, "allowed_event_kinds": list(kinds), "provenance_tier": schema.ROLE_TIER[role]}
    return {
        "L": entry("B0_LEDGER", False, schema.B0_KINDS),
        "N": entry("NODE_CLAIM_SIM", True, ["NODE_CLAIM"]),
        "K": entry("KERNEL_SNAPSHOT_SIM", True, ["KERNEL_SNAPSHOT"]),
        "W": entry("G2_WITNESS_SIM", True, ["GATE_CHILD_OBSERVATION"]),
        "R": entry("G2_WRAP_SIM", True, ["R_WRITE_RESULT"]),
        "M": entry("SEAL_MANIFEST_SIM", True, ["SEAL_MANIFEST"]),
        "G": entry("SUBJECT_LOG_READBACK", False, ["LOG_READBACK"]),
    }


def _idn(pid, st, ppid=None):
    d = {"pid": pid, "starttime": st}
    if ppid is not None:
        d["ppid"] = ppid
    return d


def _ev(handle, kind, order, node=None, ident=None, raw=None, status="OK", gate=None):
    e = {"source_handle": handle, "event_kind": kind, "monotonic_order": order, "read_status": status}
    if node is not None:
        e["node_token"] = node
    if ident is not None:
        e["identity"] = ident
    if gate is not None:
        e["gate_token"] = gate
    if raw is not None:
        e["raw_fields"] = raw
    return e


def _ledger(nodes, release=()):
    """RUN_START, then INTENT + REGISTERED per node (contiguous order from 1), then RELEASED for nodes in `release`."""
    out = [_ev("L", "RUN_START", 1)]
    n = 1
    for (tok, pid, st) in nodes:
        n += 1
        out.append(_ev("L", "INTENT", n, node=tok))
        n += 1
        out.append(_ev("L", "REGISTERED", n, node=tok, ident=_idn(pid, st, ppid=4100)))
    for tok in release:
        n += 1
        out.append(_ev("L", "RELEASED", n, node=tok))
    return out


def _verdict(assertion, events, trust=None):
    return judge.evaluate(assertion, events, _trust() if trust is None else trust)["subject_verdict"]


# ---------------------------------------------------------------- static source contracts (SRC-02 / SRC-03 / SRC-07 intentions)
class TestStaticContracts(unittest.TestCase):
    PURE = ("schema.py", "judge.py", "codec.py")
    ALLOWED_IMPORTS = {"re", "dataclasses", "hashlib", "json", "unicodedata", "j1"}
    FORBIDDEN = {"os", "sys", "time", "datetime", "random", "socket", "signal", "subprocess", "multiprocessing", "threading", "pathlib", "shutil",
                 "ctypes", "oracle", "common", "observer", "registry", "node", "gate", "janitor", "proto"}

    def _tree(self, name):
        with open(os.path.join(J1_DIR, name), encoding="utf-8") as f:
            return ast.parse(f.read())

    def _imports(self, tree):
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                if n.level:
                    mods |= {a.name for a in n.names}           # `from . import codec` -> names codec / schema
                else:
                    mods.add((n.module or "").split(".")[0])
        return mods

    def test_pure_modules_import_only_pure_stdlib(self):
        for name in self.PURE:
            mods = self._imports(self._tree(name))
            self.assertFalse(mods & self.FORBIDDEN, name)
            self.assertTrue(mods <= self.ALLOWED_IMPORTS | {"codec", "schema"}, (name, mods))

    def test_oracle_is_isolated_from_judge_side_modules(self):
        mods = self._imports(self._tree("oracle.py"))
        self.assertFalse(mods & {"judge", "schema", "codec", "j1"})

    def test_evaluate_signature_is_exactly_the_lane_s_triple(self):
        for n in self._tree("judge.py").body:
            if isinstance(n, ast.FunctionDef) and n.name == "evaluate":
                self.assertEqual([a.arg for a in n.args.args], ["assertion_id", "subject_observables", "declared_trust_model"])
                return
        self.fail("evaluate not found")

    def test_no_fixture_identifier_literals_on_the_judge_side(self):
        pat = re.compile(r"J1-F0[1-6]-[A-D]")
        for name in self.PURE:
            for n in ast.walk(self._tree(name)):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    self.assertIsNone(pat.search(n.value), name)

    def test_inventory_self_check(self):
        self.assertEqual(oracle.inventory_self_check(), [])

    def test_scope_constants_agree_between_judge_side_and_oracle(self):
        self.assertEqual(schema.SCOPE, oracle.SCOPE)
        self.assertEqual(schema.MEASUREMENT_TARGET, oracle.MEASUREMENT_TARGET)
        self.assertEqual(schema.NATIVE_B0_SAFETY_STATUS, oracle.NATIVE_B0_SAFETY_STATUS)
        self.assertEqual(schema.EVIDENCE_SENSITIVE, oracle.EVIDENCE_SENSITIVE)
        self.assertEqual(schema.SMOKE_ONLY, oracle.SMOKE_ONLY)


# ---------------------------------------------------------------- input firewall and trust map
class TestInputFirewall(unittest.TestCase):
    def test_forbidden_field_name_is_blocked_input_invalid(self):
        events = _ledger([("nA", 4101, 101)])
        events[0]["raw_fields"] = {"expected_subject_verdict": "PASS"}
        out = judge.evaluate("UNIQUE_REGISTRY", events, _trust())
        self.assertEqual(out["subject_verdict"], BLOCKED)
        self.assertIn("INPUT_INVALID", out["evidence_basis_codes"])

    def test_fixture_shaped_string_value_is_blocked(self):
        events = _ledger([("nA", 4101, 101)])
        events[1]["node_token"] = "J1-F02-A"
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED)

    def test_bool_is_not_an_int(self):
        events = _ledger([("nA", 4101, 101)])
        events[2]["identity"]["pid"] = True
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED)

    def test_unknown_source_handle_and_unauthorised_kind_are_blocked(self):
        events = _ledger([("nA", 4101, 101)])
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events + [_ev("ZZ", "RELEASED", 99, node="nA")]), BLOCKED)
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events + [_ev("N", "RELEASED", 99, node="nA")]), BLOCKED)

    def test_simulated_source_cannot_be_declared_non_synthetic(self):
        t = _trust()
        t["W"]["synthetic_assumption"] = False
        self.assertEqual(_verdict("ATTRIBUTION", _ledger([("nA", 4101, 101)]), t), BLOCKED)

    def test_claim_source_cannot_widen_its_kind_ceiling(self):
        t = _trust()
        t["N"]["allowed_event_kinds"] = ["NODE_CLAIM", "R_WRITE_RESULT"]
        self.assertEqual(_verdict("WRITE_COMPLETE", _ledger([("nA", 4101, 101)]), t), BLOCKED)

    def test_duplicate_handle_order_is_blocked(self):
        events = _ledger([("nA", 4101, 101)])
        events.append(dict(events[0]))
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED)

    def test_output_always_carries_scope_labels(self):
        out = judge.evaluate("DELIVERY", [], _trust())
        self.assertEqual(out["measurement_target"], "J1_SYNTHETIC_DETECTOR")
        self.assertEqual(out["native_B0_safety_status"], "NOT_EVALUATED_BY_J1")
        self.assertEqual(out["scope"], "SYNTHETIC_CPU_ONLY")


# ---------------------------------------------------------------- the five discriminative assertions (illustrative inputs only)
class TestDiscriminativeHandlers(unittest.TestCase):
    def test_attribution_mismatch_agreement_and_missing_witness(self):
        base = _ledger([("nA", 4101, 101)], release=("nA",))
        wit_bad = _ev("W", "GATE_CHILD_OBSERVATION", 50, node="nA", ident=_idn(4102, 102))
        wit_ok = _ev("W", "GATE_CHILD_OBSERVATION", 50, node="nA", ident=_idn(4101, 101))
        claim = _ev("N", "NODE_CLAIM", 60, node="nA", raw={"claim_kind": "GATE_CHILD_IDENTITY", "pid": 4102, "starttime": 102})
        self.assertEqual(_verdict("ATTRIBUTION", base + [wit_bad]), FAIL)
        self.assertEqual(_verdict("ATTRIBUTION", base + [wit_ok]), PASS)
        self.assertEqual(_verdict("ATTRIBUTION", base), BLOCKED)
        self.assertEqual(_verdict("ATTRIBUTION", base + [claim]), BLOCKED)

    def test_unique_registry_duplicate_unique_and_incomplete(self):
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101), ("nB", 4101, 101)])), FAIL)
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101), ("nB", 4102, 102)])), PASS)
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101)])[1:]), BLOCKED)      # no RUN_START at order 1 -> incomplete
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101), ("nB", 4101, 102)])), PASS)   # pid reuse with other starttime

    def test_zombie_at_t_z_s_and_missing_snapshot(self):
        z = _ev("K", "KERNEL_SNAPSHOT", 70, ident=_idn(4101, 101), raw={"state": "Z"})
        s = _ev("K", "KERNEL_SNAPSHOT", 70, ident=_idn(4101, 101), raw={"state": "S"})
        self.assertEqual(_verdict("ZOMBIE_AT_T", [z]), PASS)
        self.assertEqual(_verdict("ZOMBIE_AT_T", [s]), FAIL)
        self.assertEqual(_verdict("ZOMBIE_AT_T", []), BLOCKED)
        self.assertEqual(_verdict("ZOMBIE_AT_T", [z, dict(s, monotonic_order=71)]), BLOCKED)           # T not selected (OQ-1)

    def test_write_complete_ok_error_and_untrusted_claim(self):
        base = _ledger([("nA", 4101, 101)], release=("nA",))
        ok = _ev("R", "R_WRITE_RESULT", 80, node="nA", raw={"bytes": 1, "errno": None, "byte": "R"})
        epipe = _ev("R", "R_WRITE_RESULT", 80, node="nA", raw={"bytes": 0, "errno": "EPIPE"})
        claim = _ev("N", "NODE_CLAIM", 80, node="nA", raw={"claim_kind": "R_WRITTEN"})
        self.assertEqual(_verdict("WRITE_COMPLETE", base + [ok]), PASS)
        self.assertEqual(_verdict("WRITE_COMPLETE", base + [epipe]), FAIL)
        self.assertEqual(_verdict("WRITE_COMPLETE", base + [claim]), BLOCKED)

    def test_log_matches_seal_match_mismatch_and_missing_manifest(self):
        r1 = codec.build_record(1, codec.GENESIS_DIGEST, "A", {"x": 1})
        r2 = codec.build_record(2, r1["event_digest"], "B", {"x": 2})
        r3 = codec.build_record(3, r2["event_digest"], "C", {"x": 3})

        def manifest(records, run_id="run-1"):
            data = codec.serialize_log(records)
            return {"full_file_sha256": codec.sha256_hex(data), "byte_length": len(data), "final_seq": records[-1]["seq"],
                    "last_digest": records[-1]["event_digest"], "run_id": run_id}

        def log(records):
            return _ev("G", "LOG_READBACK", 1, raw={"log_utf8": codec.serialize_log(records).decode("utf-8"), "run_id": "run-1"})

        def seal(m):
            return _ev("M", "SEAL_MANIFEST", 2, raw=m)

        self.assertEqual(_verdict("LOG_MATCHES_SEAL", [log([r1, r2, r3]), seal(manifest([r1, r2, r3]))]), PASS)
        self.assertEqual(_verdict("LOG_MATCHES_SEAL", [log([r1, r2]), seal(manifest([r1, r2, r3]))]), FAIL)
        self.assertEqual(_verdict("LOG_MATCHES_SEAL", [log([r1, r2, r3])]), BLOCKED)
        self.assertEqual(_verdict("EVIDENCE_USABLE", [log([r1, r2]), seal(manifest([r1, r2, r3]))]), BLOCKED)


# ---------------------------------------------------------------- SMOKE_ONLY assertions never produce PASS
class TestSmokeOnlyHaveNoPassPath(unittest.TestCase):
    def test_smoke_only_assertions_are_blocked_and_labelled(self):
        events = _ledger([("nA", 4101, 101)], release=("nA",)) + [
            _ev("K", "KERNEL_SNAPSHOT", 70, ident=_idn(4101, 101), raw={"state": "Z"}),
            _ev("R", "R_WRITE_RESULT", 80, node="nA", raw={"bytes": 1, "errno": None}),
            _ev("N", "NODE_CLAIM", 90, node="nA", raw={"claim_kind": "READY"}),
        ]
        for a in schema.SMOKE_ONLY:
            out = judge.evaluate(a, events, _trust())
            self.assertEqual(out["subject_verdict"], BLOCKED, a)
            self.assertEqual(out["coverage"], "SMOKE_ONLY", a)
            self.assertIsNone(out["accepted_claim"], a)

    def test_zombie_dead_echild_are_distinguished_from_reap(self):
        events = _ledger([("nA", 4101, 101)]) + [
            _ev("L", "DEAD", 6, node="nA"),
            _ev("K", "KERNEL_SNAPSHOT", 70, ident=_idn(4101, 101), raw={"state": "Z"}),
            _ev("N", "NODE_CLAIM", 90, node="nA", raw={"claim_kind": "WAIT_RESULT"}),
        ]
        out = judge.evaluate("LAWFUL_REAP", events, _trust())
        for code in ("DEAD_RECORD_IS_NOT_REAP", "ZOMBIE_IS_NOT_REAP", "UNTRUSTED_WAIT_OR_ECHILD_CLAIM_NOT_REAP"):
            self.assertIn(code, out["evidence_basis_codes"])


# ---------------------------------------------------------------- metamorphic skeletons (inline base; NOT RUN)
class TestMetamorphicSkeletons(unittest.TestCase):
    def _base(self):
        return _ledger([("nA", 4101, 101)], release=("nA",)) + [_ev("W", "GATE_CHILD_OBSERVATION", 50, node="nA", ident=_idn(4102, 102))]

    def test_m1_bijective_token_rename_keeps_verdict(self):
        a = self._base()
        b = [dict(e, node_token="zz" + e["node_token"]) if "node_token" in e else dict(e) for e in a]
        self.assertEqual(_verdict("ATTRIBUTION", a), _verdict("ATTRIBUTION", b))

    def test_m2_reordering_unrelated_records_keeps_verdict(self):
        a = self._base()
        b = list(reversed(a))
        self.assertEqual(_verdict("ATTRIBUTION", a), _verdict("ATTRIBUTION", b))

    def test_m3_removing_the_decisive_witness_does_not_keep_fail(self):
        a = self._base()
        b = [e for e in a if e["source_handle"] != "W"]
        self.assertEqual(_verdict("ATTRIBUTION", a), FAIL)
        self.assertEqual(_verdict("ATTRIBUTION", b), BLOCKED)

    def test_m4_demoting_a_trusted_witness_to_a_claim_never_promotes(self):
        a = self._base()
        claim = [e for e in a if e["source_handle"] != "W"] + [
            _ev("N", "NODE_CLAIM", 50, node="nA", raw={"claim_kind": "GATE_CHILD_IDENTITY", "pid": 4102, "starttime": 102})]
        self.assertEqual(_verdict("ATTRIBUTION", claim), BLOCKED)


# ---------------------------------------------------------------- oracle (private lane) behaviour
class TestOracleSkeleton(unittest.TestCase):
    def test_smoke_pass_is_an_unproven_pass(self):
        exp = {"fixture_id": "J1-F03-A", "canonical_card": "D01-B0", "assertion_id": "PREVENT_PROOF", "expected_subject_verdict": "BLOCKED"}
        out = judge.evaluate("PREVENT_PROOF", [], _trust())
        self.assertEqual(oracle.grade_case(exp, out)["test_acceptance_verdict"], PASS)
        forged = dict(out, subject_verdict="PASS")
        self.assertEqual(oracle.grade_case(exp, forged)["test_acceptance_verdict"], FAIL)

    def test_missing_ids_make_the_run_blocked_not_pass(self):
        self.assertEqual(oracle.aggregate([])["run_acceptance_verdict"], BLOCKED)


@unittest.skip("fixture S/O data, hashes and the 18-id acceptance run are NOT MATERIALIZED / NOT AUTHORIZED in this stage")
class TestEighteenFixturesNotMaterialized(unittest.TestCase):
    def test_placeholder(self):
        pass


if __name__ == "__main__":
    unittest.main()
