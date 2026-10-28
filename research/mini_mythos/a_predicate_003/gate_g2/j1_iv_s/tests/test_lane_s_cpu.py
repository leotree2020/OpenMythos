"""Nonofficial, isolated synthetic Lane S structural validation CPU unit tests."""
import copy
import json
import unittest

from j1_iv_s.lane_s import validate_lane_s, validate_lane_s_bytes


TIERS = {
    "hL": ("B0_LEDGER", "SYNTHETIC_B0_SHAPED_TRANSCRIPT", ["RUN_START", "INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD", "RUN_END"]),
    "hN": ("NODE_CLAIM_SIM", "UNTRUSTED_CLAIM", ["NODE_CLAIM"]),
    "hK": ("KERNEL_SNAPSHOT_SIM", "SYNTHETIC_ASSUMPTION", ["KERNEL_SNAPSHOT"]),
    "hW": ("G2_WITNESS_SIM", "SYNTHETIC_ASSUMPTION", ["GATE_CHILD_OBSERVATION"]),
    "hR": ("G2_WRAP_SIM", "SYNTHETIC_ASSUMPTION", ["R_WRITE_RESULT"]),
    "hM": ("SEAL_MANIFEST_SIM", "SYNTHETIC_ASSUMPTION", ["SEAL_MANIFEST"]),
    "hG": ("SUBJECT_LOG_READBACK", "SUBJECT_ARTIFACT", ["LOG_READBACK"]),
}


def baseline():
    trust = {handle: {"role": role, "synthetic_assumption": True,
                      "allowed_event_kinds": kinds, "provenance_tier": tier}
             for handle, (role, tier, kinds) in TIERS.items()}
    return {"assertion_id": "ATTRIBUTION", "declared_trust_model": trust,
            "subject_observables": [{"source_handle": "hL", "event_kind": "RUN_START",
                                     "monotonic_order": 1, "read_status": "OK",
                                     "raw_fields": {"run_id": "run-synth-01", "observer_pid": 300}}]}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def obs(handle, kind, order, node=None, ident=None, raw=None, gate=None):
    event = {"source_handle": handle, "event_kind": kind, "monotonic_order": order,
             "read_status": "OK", "raw_fields": raw or {}}
    if node is not None:
        event["node_token"] = node
    if ident is not None:
        event["identity"] = ident
    if gate is not None:
        event["gate_token"] = gate
    return event


ID = {"pid": 4101, "starttime": 101, "ppid": 4100}


class LaneSValidCpu(unittest.TestCase):
    def test_baseline_struct_valid(self):
        result = validate_lane_s(baseline())
        self.assertTrue(result.valid, result.reason)
        self.assertEqual(result.events, 1)
        self.assertEqual(result.trust_handles, 7)

    def test_baseline_canonical_bytes_valid(self):
        self.assertTrue(validate_lane_s_bytes(canonical(baseline())).valid)

    def test_nine_assertions_allowed(self):
        for assertion in ("ATTRIBUTION", "UNIQUE_REGISTRY", "ZOMBIE_AT_T", "LOG_MATCHES_SEAL", "WRITE_COMPLETE",
                          "PREVENT_PROOF", "LAWFUL_REAP", "EVIDENCE_USABLE", "DELIVERY"):
            with self.subTest(assertion=assertion):
                item = baseline()
                item["assertion_id"] = assertion
                self.assertTrue(validate_lane_s(item).valid)

    def test_all_fourteen_kinds_have_schema_valid_examples(self):
        examples = [
            obs("hL", "RUN_START", 1, raw={"run_id": "id", "observer_pid": 300}),
            obs("hL", "INTENT", 2, node="nA", raw={"creator": "O"}),
            obs("hL", "FORKED", 3, node="nA", raw={"pid": 4101}),
            obs("hL", "REGISTERED", 4, node="nA", ident=ID, gate="gate-A"),
            obs("hL", "RELEASED", 5, node="nA"),
            obs("hL", "ABORTED", 6, node="nA"),
            obs("hL", "DEAD", 7, node="nA"),
            obs("hL", "RUN_END", 8, raw={"cleanup_confirmed": True}),
            obs("hN", "NODE_CLAIM", 9, node="nA", gate="gate-A", raw={"claim_kind": "WAIT_RESULT"}),
            obs("hK", "KERNEL_SNAPSHOT", 10, ident=ID, raw={"state": "Z"}),
            obs("hW", "GATE_CHILD_OBSERVATION", 11, node="nA", ident=ID, gate="gate-A"),
            obs("hR", "R_WRITE_RESULT", 12, node="nA", raw={"bytes": 1, "errno": None, "byte": "R"}),
            obs("hM", "SEAL_MANIFEST", 13, raw={"full_file_sha256": "a" * 64, "byte_length": 5,
                                                     "final_seq": 3, "last_digest": "b" * 64, "run_id": "abc"}),
            obs("hG", "LOG_READBACK", 14, raw={"log_utf8": "sample\n", "run_id": "abc"}),
        ]
        item = baseline()
        item["subject_observables"] = examples
        self.assertTrue(validate_lane_s(item).valid)
        self.assertTrue(validate_lane_s_bytes(canonical(item)).valid)

    def test_schema_allows_non_ok_read_status(self):
        item = baseline()
        item["subject_observables"][0]["read_status"] = "TORN_TAIL"
        # J1's structural schema allows this; later evidence quality/claim semantics do NOT.
        self.assertTrue(validate_lane_s(item).valid)

    def test_schema_allows_optional_forked_identity(self):
        item = baseline()
        item["subject_observables"].append(obs("hL", "FORKED", 2, node="nA", ident=ID))
        self.assertTrue(validate_lane_s(item).valid)


class LaneSInvalidCpu(unittest.TestCase):
    def setUp(self):
        self.item = baseline()

    def reject(self, code=None):
        result = validate_lane_s(self.item)
        self.assertFalse(result.valid)
        if code:
            self.assertEqual(result.reason, code)

    def test_missing_top_level_field(self):
        del self.item["assertion_id"]
        self.reject("S_TOP_LEVEL_FIELDS")

    def test_lane_o_expected_key_rejected(self):
        self.item["subject_observables"][0]["raw_fields"]["expected_verdict"] = "PASS"
        self.reject("LANE_O_KEY")

    def test_lane_o_case_identifier_rejected(self):
        self.item["subject_observables"][0]["raw_fields"]["run_id"] = "J1-F01-A"
        self.reject("LANE_O_VALUE")

    def test_float_tainted_input(self):
        self.item["subject_observables"][0]["raw_fields"]["observer_pid"] = 300.0
        self.reject("NON_JSON_VALUE")

    def test_invalid_assertion(self):
        self.item["assertion_id"] = "UNRECOGNIZED"
        self.reject("S_ASSERTION_INVALID")

    def test_trust_role_can_not_self_upgrade(self):
        self.item["declared_trust_model"]["hN"]["allowed_event_kinds"] = ["NODE_CLAIM", "R_WRITE_RESULT"]
        self.reject("TRUST_ROLE_CEILING")

    def test_trust_non_synthetic_rejected(self):
        self.item["declared_trust_model"]["hW"]["synthetic_assumption"] = False
        self.reject("TRUST_NOT_SYNTHETIC")

    def test_trust_invalid_tier(self):
        self.item["declared_trust_model"]["hN"]["provenance_tier"] = "SYNTHETIC_ASSUMPTION"
        self.reject("TRUST_TIER_INVALID")

    def test_event_handle_not_in_trust(self):
        self.item["subject_observables"][0]["source_handle"] = "self_said_trusted"
        self.reject("EVENT_HANDLE_INVALID")

    def test_event_kind_not_in_handle_role(self):
        self.item["subject_observables"][0]["event_kind"] = "NODE_CLAIM"
        self.reject("EVENT_KIND_UNTRUSTED")

    def test_bool_monotonic_order_rejected(self):
        self.item["subject_observables"][0]["monotonic_order"] = True
        self.reject("EVENT_ORDER_INVALID")

    def test_missing_node(self):
        self.item["subject_observables"].append(obs("hR", "R_WRITE_RESULT", 2,
                                                   raw={"bytes": 1, "errno": None}))
        self.reject("EVENT_NODE_REQUIRED")

    def test_forbidden_node(self):
        self.item["subject_observables"][0]["node_token"] = "nA"
        self.reject("EVENT_NODE_FORBIDDEN")

    def test_invalid_register_identity(self):
        self.item["subject_observables"].append(obs("hL", "REGISTERED", 2, node="nA",
                                                   ident={"pid": 1, "starttime": 1}))
        self.reject("REGISTERED_PPID_REQUIRED")

    def test_bool_in_identity_pid(self):
        self.item["subject_observables"].append(obs("hK", "KERNEL_SNAPSHOT", 2,
                                                   ident={"pid": True, "starttime": 1}, raw={"state": "Z"}))
        self.reject("IDENTITY_PID_START_INVALID")

    def test_wrong_wait_claim_field_errno(self):
        self.item["subject_observables"].append(obs("hN", "NODE_CLAIM", 2, node="nA",
                                                   raw={"claim_kind": "WAIT_RESULT", "errno": "ECHILD"}))
        self.reject("RAW_FIELDS_INVALID")

    def test_invalid_write_errno_type(self):
        self.item["subject_observables"].append(obs("hR", "R_WRITE_RESULT", 2, node="nA",
                                                   raw={"bytes": 0, "errno": "BAD"}))
        self.reject("RAW_TYPE_INVALID")

    def test_bool_write_bytes(self):
        self.item["subject_observables"].append(obs("hR", "R_WRITE_RESULT", 2, node="nA",
                                                   raw={"bytes": True, "errno": None}))
        self.reject("RAW_TYPE_INVALID")

    def test_duplicate_handle_and_order(self):
        self.item["subject_observables"].append(copy.deepcopy(self.item["subject_observables"][0]))
        self.reject("DUPLICATE_SOURCE_ORDER")

    def test_non_nfc_string(self):
        self.item["subject_observables"][0]["raw_fields"]["run_id"] = "e\u0301"
        self.reject("NON_NFC_VALUE")

    def test_unknown_event_field(self):
        self.item["subject_observables"][0]["verdict"] = "PASS"
        self.reject("EVENT_FIELDS_INVALID")


class LaneSBytesCpu(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        doc = canonical(baseline())
        mutated = doc.replace(b'"assertion_id":"ATTRIBUTION",', b'"assertion_id":"ATTRIBUTION","assertion_id":"ATTRIBUTION",')
        self.assertEqual(validate_lane_s_bytes(mutated).reason, "DUPLICATE_JSON_KEY")

    def test_pretty_json_is_not_canonical(self):
        doc = json.dumps(baseline(), indent=2).encode("utf-8")
        self.assertEqual(validate_lane_s_bytes(doc).reason, "NON_CANONICAL_S_BYTES")

    def test_escaped_json_is_not_canonical(self):
        doc = canonical(baseline()).replace(b'"ATTRIBUTION"', b'"ATTRIBUTI\\u004fN"')
        self.assertEqual(validate_lane_s_bytes(doc).reason, "NON_CANONICAL_S_BYTES")

    def test_float_input_rejected_in_bytes(self):
        doc = canonical(baseline()).replace(b'"observer_pid":300', b'"observer_pid":300.0')
        self.assertEqual(validate_lane_s_bytes(doc).reason, "FLOAT_OR_NONFINITE")

    def test_bytes_only(self):
        self.assertEqual(validate_lane_s_bytes("not bytes").reason, "INPUT_NOT_BYTES")

    def test_empty_document(self):
        self.assertEqual(validate_lane_s_bytes(b"").reason, "EMPTY_OR_OVERSIZE_BYTES")

    def test_invalid_utf8(self):
        self.assertEqual(validate_lane_s_bytes(b"\xff").reason, "JSON_OR_ENCODING_INVALID")


if __name__ == "__main__":
    unittest.main()
