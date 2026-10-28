"""J1 test SOURCE (static skeleton).  NOT RUN, NOT IMPORTED, NOT COMPILED (implementation stage F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-PREP-001 and correction
stage F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-001: no Python of any kind was executed while writing it).

These tests are NOT the 18 V0.1 fixtures: no fixture S/O JSON, fixture hash or fixture-id-to-verdict table for the judge is materialised here (that is a
separately authorised later stage).  The inputs below are small inline illustrations (fictional pids) of the intended behaviour of each handler and of the
minimal counterexamples of the independent static review (J1-IMPL-F01 ... F06).  Their expected values are INTENTIONS, not results: every test in this
file is NOT TESTED.  Oracle `inline_check_verdict` values used below are NON-FORMAL demonstration checks; the formal acceptance verdict is
unconditionally BLOCKED / NOT_READY in this stage.

A later runner must keep a process-safety sentinel (no fork / exec / subprocess / signal / wait); nothing here needs any.
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
    def entry(role, kinds):
        return {"role": role, "synthetic_assumption": True, "allowed_event_kinds": list(kinds), "provenance_tier": schema.ROLE_TIER[role]}
    return {
        "L": entry("B0_LEDGER", schema.B0_KINDS),
        "N": entry("NODE_CLAIM_SIM", ["NODE_CLAIM"]),
        "K": entry("KERNEL_SNAPSHOT_SIM", ["KERNEL_SNAPSHOT"]),
        "W": entry("G2_WITNESS_SIM", ["GATE_CHILD_OBSERVATION"]),
        "R": entry("G2_WRAP_SIM", ["R_WRITE_RESULT"]),
        "M": entry("SEAL_MANIFEST_SIM", ["SEAL_MANIFEST"]),
        "G": entry("SUBJECT_LOG_READBACK", ["LOG_READBACK"]),
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


def _ledger(nodes, release=(), gates=None, start_raw="default"):
    """Valid illustrative synthetic B0-shaped ledger: RUN_START (run_id + observer_pid), INTENT + REGISTERED per node (contiguous order from 1), then
    RELEASED for the nodes in `release`.  `gates` maps node -> explicit gate/ticket token carried by that node's REGISTERED record (synthetic field)."""
    gates = gates or {}
    start = {"run_id": "run-1", "observer_pid": 300} if start_raw == "default" else start_raw
    out = [_ev("L", "RUN_START", 1, raw=start)]
    n = 1
    for (tok, pid, st) in nodes:
        n += 1
        out.append(_ev("L", "INTENT", n, node=tok, raw={"creator": "O"}))
        n += 1
        out.append(_ev("L", "REGISTERED", n, node=tok, ident=_idn(pid, st, ppid=4100), gate=gates.get(tok)))
    for tok in release:
        n += 1
        out.append(_ev("L", "RELEASED", n, node=tok))
    return out


def _out(assertion, events, trust=None):
    return judge.evaluate(assertion, events, _trust() if trust is None else trust)


def _verdict(assertion, events, trust=None):
    return _out(assertion, events, trust)["subject_verdict"]


def _exp(fid):
    card, assertion, expected = oracle.SPEC_V0_1_INVENTORY[fid]
    return {"fixture_id": fid, "canonical_card": card, "assertion_id": assertion, "expected_subject_verdict": expected}


def _codes(assertion, events, trust=None):
    return _out(assertion, events, trust)["evidence_basis_codes"]


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

    def _function_args(self, name, func):
        for n in self._tree(name).body:
            if isinstance(n, ast.FunctionDef) and n.name == func:
                return [a.arg for a in n.args.args]
        self.fail("%s not found in %s" % (func, name))

    def test_pure_modules_import_only_pure_stdlib(self):
        for name in self.PURE:
            mods = self._imports(self._tree(name))
            self.assertFalse(mods & self.FORBIDDEN, name)
            self.assertTrue(mods <= self.ALLOWED_IMPORTS | {"codec", "schema"}, (name, mods))

    def test_oracle_is_isolated_from_judge_side_modules(self):
        mods = self._imports(self._tree("oracle.py"))
        self.assertFalse(mods & {"judge", "schema", "codec", "j1"})

    def test_evaluate_signature_is_exactly_the_lane_s_triple(self):
        self.assertEqual(self._function_args("judge.py", "evaluate"), ["assertion_id", "subject_observables", "declared_trust_model"])

    def test_aggregate_has_no_expected_ids_parameter(self):                       # F02: the 18-id formal scope cannot be shrunk by an argument
        self.assertEqual(self._function_args("oracle.py", "aggregate"), ["case_results"])

    def test_no_fixture_identifier_literals_on_the_judge_side(self):
        pat = re.compile(r"J1-F0[1-6]-[A-D]")
        for name in self.PURE:
            for n in ast.walk(self._tree(name)):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    self.assertIsNone(pat.search(n.value), name)

    def test_inventory_self_check_and_unchanged_expected_counts(self):
        self.assertEqual(oracle.inventory_self_check(), [])
        counts = {PASS: 0, FAIL: 0, BLOCKED: 0}
        for (_c, _a, e) in oracle.SPEC_V0_1_INVENTORY.values():
            counts[e] += 1
        self.assertEqual(counts, {PASS: 5, FAIL: 5, BLOCKED: 8})
        self.assertEqual(oracle.SPEC_V0_1_INVENTORY["J1-F01-A"], ("D03c", "ATTRIBUTION", "FAIL"))

    def test_scope_constants_agree_between_judge_side_and_oracle(self):
        self.assertEqual(schema.SCOPE, oracle.SCOPE)
        self.assertEqual(schema.MEASUREMENT_TARGET, oracle.MEASUREMENT_TARGET)
        self.assertEqual(schema.NATIVE_B0_SAFETY_STATUS, oracle.NATIVE_B0_SAFETY_STATUS)
        self.assertEqual(schema.EVIDENCE_SENSITIVE, oracle.EVIDENCE_SENSITIVE)
        self.assertEqual(schema.SMOKE_ONLY, oracle.SMOKE_ONLY)


# ---------------------------------------------------------------- J1-IMPL-F01: invalid input is never a test acceptance
class TestF01InvalidInputIsNeverAcceptance(unittest.TestCase):
    def _valid_missing_witness(self):
        return _out("PREVENT_PROOF", _ledger([("nA", 4101, 101)], release=("nA",)))

    def test_forbidden_lane_o_key_gives_input_invalid_and_no_subject_verdict(self):
        events = _ledger([("nA", 4101, 101)])
        events[0]["raw_fields"]["expected_subject_verdict"] = "BLOCKED"
        out = _out("PREVENT_PROOF", events)
        self.assertFalse(out["input_valid"])
        self.assertEqual(out["result_kind"], "INPUT_INVALID")
        self.assertIsNone(out["subject_verdict"])
        self.assertIn("INPUT_INVALID", out["evidence_basis_codes"])
        self.assertTrue(out["input_diagnostics"])

    def test_oracle_does_not_accept_the_invalid_input_even_though_blocked_was_expected(self):    # minimal counterexample of F01 (J1-F03-A expects BLOCKED)
        events = _ledger([("nA", 4101, 101)])
        events[0]["raw_fields"]["expected_subject_verdict"] = "BLOCKED"
        graded = oracle.grade_case(_exp("J1-F03-A"), _out("PREVENT_PROOF", events))
        self.assertEqual(graded["inline_check_verdict"], BLOCKED)
        self.assertEqual(graded["test_acceptance_verdict"], BLOCKED)

    def test_contrast_valid_missing_witness_is_a_subject_blocked_and_only_an_inline_pass(self):
        out = self._valid_missing_witness()
        self.assertTrue(out["input_valid"])
        self.assertEqual(out["result_kind"], "SUBJECT_VERDICT")
        self.assertEqual(out["subject_verdict"], BLOCKED)
        graded = oracle.grade_case(_exp("J1-F03-A"), out)
        self.assertEqual(graded["inline_check_verdict"], PASS)                    # non-formal demonstration only
        self.assertEqual(graded["inline_check_scope"], "NON_FORMAL_DEMONSTRATION")
        self.assertEqual(graded["test_acceptance_verdict"], BLOCKED)              # formal acceptance NOT_READY, whatever the inline check says
        self.assertEqual(graded["acceptance_state"], "NOT_READY")

    def test_tampered_outputs_cannot_be_an_inline_pass(self):
        valid = self._valid_missing_witness()
        for tampered in (dict(valid, input_diagnostics=["x"]), dict(valid, input_valid=False),
                         dict(valid, result_kind="INPUT_INVALID"),
                         dict(valid, evidence_basis_codes=valid["evidence_basis_codes"] + ["INPUT_INVALID"]),
                         dict(valid, evidence_basis_codes=[])):
            self.assertEqual(oracle.grade_case(_exp("J1-F03-A"), tampered)["inline_check_verdict"], BLOCKED)

    def test_smoke_only_inline_pass_verdict_is_a_failure_of_the_instrument(self):
        forged = dict(self._valid_missing_witness(), subject_verdict=PASS)
        self.assertEqual(oracle.grade_case(_exp("J1-F03-A"), forged)["inline_check_verdict"], FAIL)


# ---------------------------------------------------------------- J1-IMPL-F02: expectations pinned, no forged aggregate, formal gate NOT_READY
class TestF02PinnedExpectationsAndNoForgedAggregate(unittest.TestCase):
    def test_altered_expectation_is_rejected_not_graded(self):                   # F01-A is FAIL in V0.1; a caller-supplied PASS must not be graded
        altered = dict(_exp("J1-F01-A"), expected_subject_verdict="PASS")
        self.assertTrue(oracle.validate_private_expectation(altered))
        out = _out("ATTRIBUTION", _ledger([("nA", 4101, 101)]))
        self.assertEqual(oracle.grade_case(altered, out)["inline_check_verdict"], BLOCKED)

    def test_altered_card_assertion_and_unknown_id_are_rejected(self):
        self.assertTrue(oracle.validate_private_expectation(dict(_exp("J1-F01-A"), canonical_card="D03d")))
        self.assertTrue(oracle.validate_private_expectation(dict(_exp("J1-F01-A"), assertion_id="UNIQUE_REGISTRY")))
        self.assertTrue(oracle.validate_private_expectation(dict(_exp("J1-F01-A"), fixture_id="J1-F06-E")))
        self.assertEqual(oracle.validate_private_expectation(_exp("J1-F01-A")), [])

    def test_fabricated_eighteen_pass_rows_never_give_a_formal_pass(self):
        rows = []
        for fid, (_card, assertion, _expected) in oracle.SPEC_V0_1_INVENTORY.items():
            rows.append({"fixture_id": fid, "assertion_id": assertion, "inline_check_verdict": PASS, "test_acceptance_verdict": PASS})
        agg = oracle.aggregate(rows)
        self.assertEqual(agg["run_acceptance_verdict"], BLOCKED)
        self.assertEqual(agg["acceptance_state"], "NOT_READY")
        self.assertFalse(agg["formal_acceptance_ready"])
        self.assertIn("a row claims a formal acceptance verdict that this stage cannot grant", agg["reasons"])

    def test_even_honestly_graded_rows_do_not_lift_the_formal_gate(self):
        rows = [oracle.grade_case(_exp(fid), _out("PREVENT_PROOF", [])) for fid in oracle.SPEC_V0_1_INVENTORY]
        self.assertEqual(oracle.aggregate(rows)["run_acceptance_verdict"], BLOCKED)

    def test_scope_cannot_be_shrunk_by_an_argument(self):
        with self.assertRaises(TypeError):
            oracle.aggregate([], expected_ids=["J1-F01-A"])
        self.assertEqual(oracle.aggregate([{"fixture_id": "J1-F01-A"}])["run_acceptance_verdict"], BLOCKED)

    def test_duplicate_unknown_and_missing_ids_add_reasons(self):
        agg = oracle.aggregate([{"fixture_id": "J1-F01-A"}, {"fixture_id": "J1-F01-A"}, {"fixture_id": "J1-F09-Z"}, {}])
        for needle in ("duplicate fixture ids", "unknown fixture ids", "a row has no fixture_id"):
            self.assertIn(needle, agg["reasons"])
        self.assertTrue(any("missing" in r for r in agg["reasons"]))

    def test_attestation_verifier_is_a_stub_that_accepts_nothing(self):
        ok, reasons = oracle.verify_fixture_attestation({"sealed": True, "sha256": "0" * 64})
        self.assertFalse(ok)
        self.assertIn("ATTESTATION_VERIFIER_NOT_IMPLEMENTED", reasons)
        self.assertFalse(oracle.FORMAL_ACCEPTANCE_READY)


# ---------------------------------------------------------------- the five discriminative assertions (illustrative inputs only)
class TestDiscriminativeHandlers(unittest.TestCase):
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


# ---------------------------------------------------------------- J1-IMPL-F03: ATTRIBUTION needs an explicit identical gate/ticket association
class TestF03AttributionNeedsExplicitGateAssociation(unittest.TestCase):
    def _case(self, reg_gate, wit_ident, wit_gate, release=True):
        base = _ledger([("nA", 4101, 101)], release=("nA",) if release else (), gates={"nA": reg_gate} if reg_gate else None)
        return base + [_ev("W", "GATE_CHILD_OBSERVATION", 50, node="nA", ident=wit_ident, gate=wit_gate)]

    def test_matching_gate_agreement_pass_and_mismatching_identity_fail(self):
        self.assertEqual(_verdict("ATTRIBUTION", self._case("gate-A", _idn(4101, 101), "gate-A")), PASS)
        self.assertEqual(_verdict("ATTRIBUTION", self._case("gate-A", _idn(4102, 102), "gate-A")), FAIL)

    def test_node_token_alone_is_not_a_same_ticket_proof(self):                  # no gate token on either side, identities agree -> BLOCKED, not PASS
        events = self._case(None, _idn(4101, 101), None)
        self.assertEqual(_verdict("ATTRIBUTION", events), BLOCKED)
        self.assertIn("GATE_ASSOCIATION_UNVERIFIED", _codes("ATTRIBUTION", events))

    def test_gate_token_missing_on_one_side_is_blocked(self):
        self.assertEqual(_verdict("ATTRIBUTION", self._case("gate-A", _idn(4101, 101), None)), BLOCKED)
        self.assertEqual(_verdict("ATTRIBUTION", self._case(None, _idn(4101, 101), "gate-A")), BLOCKED)

    def test_mismatching_gate_tokens_are_a_conflict_not_a_convenient_choice(self):   # the reviewer's counterexample: same node, gate-B witness
        events = self._case("gate-A", _idn(4101, 101), "gate-B")
        self.assertEqual(_verdict("ATTRIBUTION", events), BLOCKED)
        self.assertIn("GATE_ASSOCIATION_CONFLICT", _codes("ATTRIBUTION", events))

    def test_two_witnesses_with_different_gates_are_a_conflict(self):
        events = self._case("gate-A", _idn(4101, 101), "gate-A") + [_ev("W", "GATE_CHILD_OBSERVATION", 51, node="nA", ident=_idn(4101, 101), gate="gate-B")]
        self.assertEqual(_verdict("ATTRIBUTION", events), BLOCKED)

    def test_unreadable_witness_blocks_instead_of_being_dropped(self):
        events = self._case("gate-A", _idn(4102, 102), "gate-A")
        events[-1]["read_status"] = "CORRUPT"
        self.assertEqual(_verdict("ATTRIBUTION", events), BLOCKED)

    def test_untrusted_claim_cannot_supply_the_association(self):
        base = _ledger([("nA", 4101, 101)], gates={"nA": "gate-A"})
        claim = _ev("N", "NODE_CLAIM", 60, node="nA", raw={"claim_kind": "GATE_CHILD_IDENTITY", "pid": 4102, "starttime": 102})
        self.assertEqual(_verdict("ATTRIBUTION", base + [claim]), BLOCKED)

    def test_retrospective_witness_after_released_is_still_a_retrospective_result_not_prevention(self):
        events = self._case("gate-A", _idn(4101, 101), "gate-A", release=True)       # witness order 50 is after the RELEASED record
        codes = _codes("ATTRIBUTION", events)
        self.assertEqual(_verdict("ATTRIBUTION", events), PASS)
        self.assertIn("WITNESS_NOT_BEFORE_RELEASED_INTENT", codes)
        self.assertIn("RETROSPECTIVE_AGREEMENT_NOT_PREVENT_PROOF", codes)


# ---------------------------------------------------------------- J1-IMPL-F04: UNIQUE_REGISTRY restated frozen lifecycle rules, finite-set claim
class TestF04UniqueRegistryLifecycle(unittest.TestCase):
    TWO_OK = [("nA", 4101, 101), ("nB", 4102, 102)]

    def test_valid_finite_set_passes_without_claiming_original_log_completeness(self):
        out = _out("UNIQUE_REGISTRY", _ledger(self.TWO_OK))
        self.assertEqual(out["subject_verdict"], PASS)
        self.assertIn("ORIGINAL_LOG_COMPLETENESS_NOT_ASSERTED", out["evidence_basis_codes"])
        self.assertIn("FINITE", out["accepted_claim"])

    def test_duplicate_identity_across_nodes_is_fail(self):
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101), ("nB", 4101, 101)])), FAIL)

    def test_duplicate_fail_survives_other_incompleteness(self):                 # both contradictory records are well-formed and source-qualified
        events = _ledger([("nA", 4101, 101), ("nB", 4101, 101)], start_raw={})
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), FAIL)

    def test_pid_reuse_with_a_different_starttime_is_not_a_duplicate(self):
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101), ("nB", 4101, 102)])), PASS)

    def test_run_start_without_run_id_or_observer_pid_blocks(self):              # reviewer counterexample: RUN_START with empty fields
        for start in ({}, {"observer_pid": 300}, {"run_id": "run-1"}, {"run_id": "", "observer_pid": 300}):
            events = _ledger(self.TWO_OK, start_raw=start)
            self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED, start)
            self.assertIn("LEDGER_PREREQUISITE_FAILED_RUN_START_METADATA_MISSING_OR_INVALID", _codes("UNIQUE_REGISTRY", events))

    def test_observer_pid_must_be_an_integer_not_a_bool(self):
        events = _ledger(self.TWO_OK, start_raw={"run_id": "run-1", "observer_pid": True})
        self.assertIsNone(_verdict("UNIQUE_REGISTRY", events))                                      # the closed schema rejects bool-as-int outright

    def test_orphan_creator_intent_blocks(self):
        events = _ledger(self.TWO_OK)
        events.append(_ev("L", "INTENT", len(events) + 1, node="nC", raw={"creator": "nZ"}))
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED)
        self.assertIn("LEDGER_PREREQUISITE_FAILED_CREATOR_NOT_REGISTERED_BEFORE_CHILD_INTENT", _codes("UNIQUE_REGISTRY", events))

    def test_registered_creator_is_accepted(self):
        events = _ledger(self.TWO_OK)
        events.append(_ev("L", "INTENT", len(events) + 1, node="nC", raw={"creator": "nA"}))
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), PASS)

    def test_run_end_with_a_wrong_run_id_or_missing_cleanup_flag_blocks(self):
        for end in ({"run_id": "other", "cleanup_confirmed": False}, {"run_id": "run-1"}, {"cleanup_confirmed": False}):
            events = _ledger(self.TWO_OK)
            events.append(_ev("L", "RUN_END", len(events) + 1, raw=end))
            self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED, end)

    def test_confirmed_run_end_with_unfinished_nodes_blocks(self):
        events = _ledger(self.TWO_OK)
        events.append(_ev("L", "RUN_END", len(events) + 1, raw={"run_id": "run-1", "cleanup_confirmed": True}))
        self.assertEqual(_verdict("UNIQUE_REGISTRY", events), BLOCKED)
        self.assertIn("LEDGER_PREREQUISITE_FAILED_CONFIRMED_RUN_END_WITH_UNFINISHED_NODES", _codes("UNIQUE_REGISTRY", events))

    def test_torn_or_non_ok_rows_and_gaps_block(self):
        torn = _ledger(self.TWO_OK)
        torn[-1]["read_status"] = "TORN_TAIL"
        self.assertEqual(_verdict("UNIQUE_REGISTRY", torn), BLOCKED)
        gap = _ledger(self.TWO_OK)
        del gap[2]
        self.assertEqual(_verdict("UNIQUE_REGISTRY", gap), BLOCKED)
        self.assertEqual(_verdict("UNIQUE_REGISTRY", _ledger(self.TWO_OK)[1:]), BLOCKED)           # no RUN_START at order 1


# ---------------------------------------------------------------- J1-IMPL-F05: trust is a hypothetical, unauthenticated harness declaration
class TestF05TrustIsHypotheticalAndUnauthenticated(unittest.TestCase):
    def test_every_result_labels_the_trust_basis(self):
        out = _out("DELIVERY", [])
        self.assertEqual(out["trust_basis"], "HYPOTHETICAL_HARNESS_DECLARED_UNAUTHENTICATED")
        self.assertEqual(out["input_domain"], "HAND_AUTHORED_SYNTHETIC_B0_SHAPED_ONLY")

    def test_the_validator_documents_that_it_cannot_authenticate_the_map(self):
        self.assertIn("cannot authenticate", schema.validate_trust_model.__doc__)

    def test_no_source_can_be_declared_non_synthetic(self):
        for handle in ("L", "G", "W", "K"):
            t = _trust()
            t[handle]["synthetic_assumption"] = False
            self.assertIsNone(_verdict("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101)]), t), handle)

    def test_a_role_string_inside_raw_fields_grants_nothing(self):
        claim = _ev("N", "NODE_CLAIM", 60, node="nA", raw={"claim_kind": "GATE_CHILD_IDENTITY", "role": "G2_WITNESS_SIM"})
        self.assertIsNone(_verdict("ATTRIBUTION", _ledger([("nA", 4101, 101)]) + [claim]))

    def test_claim_source_cannot_widen_its_kind_ceiling(self):
        t = _trust()
        t["N"]["allowed_event_kinds"] = ["NODE_CLAIM", "R_WRITE_RESULT"]
        self.assertIsNone(_verdict("WRITE_COMPLETE", _ledger([("nA", 4101, 101)]), t))

    def test_unknown_handle_and_unauthorised_kind_are_invalid_not_ignored(self):
        events = _ledger([("nA", 4101, 101)])
        self.assertIsNone(_verdict("UNIQUE_REGISTRY", events + [_ev("ZZ", "RELEASED", 99, node="nA")]))
        self.assertIsNone(_verdict("UNIQUE_REGISTRY", events + [_ev("N", "RELEASED", 99, node="nA")]))


# ---------------------------------------------------------------- J1-IMPL-F06: synthetic-only; native B0 records are NOT supported
class TestF06SyntheticOnlyNoNativeAdapter(unittest.TestCase):
    def test_native_shaped_record_with_float_timestamps_is_rejected(self):
        native_like = _ev("L", "RUN_START", 1, raw={"run_id": "run-1", "observer_pid": 300, "mono": 12.5, "wall": 1793156391.5})
        out = _out("UNIQUE_REGISTRY", [native_like])
        self.assertFalse(out["input_valid"])
        self.assertEqual(out["result_kind"], "INPUT_INVALID")

    def test_output_states_that_no_native_adapter_exists(self):
        out = _out("UNIQUE_REGISTRY", _ledger([("nA", 4101, 101)]))
        self.assertEqual(out["native_b0_adapter_status"], "NOT_IMPLEMENTED_OPEN_QUESTION")
        self.assertEqual(out["native_B0_safety_status"], "NOT_EVALUATED_BY_J1")

    def test_no_adapter_function_is_exposed(self):
        for mod in (schema, judge, codec, oracle):
            for name in dir(mod):
                if "adapter" in name.lower() or "native" in name.lower():
                    self.assertFalse(callable(getattr(mod, name)), (mod.__name__, name))


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


# ---------------------------------------------------------------- remaining input-firewall behaviour
class TestInputFirewall(unittest.TestCase):
    def test_fixture_shaped_string_value_is_invalid(self):
        events = _ledger([("nA", 4101, 101)])
        events[1]["node_token"] = "J1-F02-A"
        self.assertIsNone(_verdict("UNIQUE_REGISTRY", events))

    def test_bool_is_not_an_int(self):
        events = _ledger([("nA", 4101, 101)])
        events[2]["identity"]["pid"] = True
        self.assertIsNone(_verdict("UNIQUE_REGISTRY", events))

    def test_duplicate_handle_order_is_invalid(self):
        events = _ledger([("nA", 4101, 101)])
        events.append(dict(events[0]))
        self.assertIsNone(_verdict("UNIQUE_REGISTRY", events))

    def test_output_always_carries_scope_labels(self):
        for out in (_out("DELIVERY", []), _out("DELIVERY", [{"bad": 1}])):
            self.assertEqual(out["measurement_target"], "J1_SYNTHETIC_DETECTOR")
            self.assertEqual(out["native_B0_safety_status"], "NOT_EVALUATED_BY_J1")
            self.assertEqual(out["scope"], "SYNTHETIC_CPU_ONLY")


# ---------------------------------------------------------------- metamorphic skeletons (inline base; NOT RUN)
class TestMetamorphicSkeletons(unittest.TestCase):
    def _base(self):
        return _ledger([("nA", 4101, 101)], release=("nA",), gates={"nA": "gate-A"}) + [
            _ev("W", "GATE_CHILD_OBSERVATION", 50, node="nA", ident=_idn(4102, 102), gate="gate-A")]

    def test_m1_bijective_token_rename_keeps_verdict(self):
        a = self._base()
        b = [dict(e, node_token="zz" + e["node_token"]) if "node_token" in e else dict(e) for e in a]
        self.assertEqual(_verdict("ATTRIBUTION", a), _verdict("ATTRIBUTION", b))
        self.assertEqual(_verdict("ATTRIBUTION", a), FAIL)

    def test_m2_reordering_unrelated_records_keeps_verdict(self):
        a = self._base()
        self.assertEqual(_verdict("ATTRIBUTION", a), _verdict("ATTRIBUTION", list(reversed(a))))

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


@unittest.skip("fixture S/O data, hashes and the 18-id formal acceptance run are NOT MATERIALIZED / NOT AUTHORIZED in this stage")
class TestEighteenFixturesNotMaterialized(unittest.TestCase):
    def test_placeholder(self):
        pass


if __name__ == "__main__":
    unittest.main()
