"""Actual pinned J1 schema versus isolated IV-S Lane S CPU differential.

This *test harness* intentionally imports J1; independent validator lane_s.py
must never do so. Synthetic inputs are created only in memory. No judge,
Oracle, Bench, Parcae, native processes, model training, GPU or official S/O.
"""
import copy
import json
import unittest

from j1 import schema as j1_schema
from j1_iv_s.lane_s import validate_lane_s, validate_lane_s_bytes


def trust(handle="hL", role="B0_LEDGER", kind="RUN_START", tier="SYNTHETIC_B0_SHAPED_TRANSCRIPT"):
    return {handle: {"role": role, "synthetic_assumption": True,
                     "allowed_event_kinds": [kind], "provenance_tier": tier}}


def event(handle="hL", kind="RUN_START", order=1, raw=None, node=None, identity=None):
    result = {"source_handle": handle, "event_kind": kind,
              "monotonic_order": order, "read_status": "OK",
              "raw_fields": {} if raw is None else raw}
    if node is not None:
        result["node_token"] = node
    if identity is not None:
        result["identity"] = identity
    return result


def subject():
    return {"assertion_id": "ATTRIBUTION",
            "subject_observables": [event(raw={"run_id": "r", "observer_pid": 300})],
            "declared_trust_model": trust()}


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def direct_j1_accepts(doc):
    try:
        j1_schema.validate_input(doc["assertion_id"], doc["subject_observables"],
                                 doc["declared_trust_model"])
        return True
    except j1_schema.InputInvalid:
        return False


class J1VersusIndependentLaneSCpu(unittest.TestCase):
    def assert_domains(self, doc, j1_expected, ivs_expected):
        self.assertEqual(direct_j1_accepts(doc), j1_expected,
                         "native J1 schema unexpectedly changed acceptance domain")
        self.assertEqual(validate_lane_s(doc).valid, ivs_expected,
                         "candidate IV-S unexpectedly changed acceptance domain")

    def test_normal_case_accepted_by_both(self):
        self.assert_domains(subject(), True, True)

    def test_trailing_newline_in_source_handle(self):
        doc = subject()
        doc["declared_trust_model"] = trust(handle="hL\n")
        doc["subject_observables"][0]["source_handle"] = "hL\n"
        self.assert_domains(doc, True, False)

    def test_trailing_newline_in_hex64_manifest(self):
        doc = subject()
        doc["declared_trust_model"] = trust("hM", "SEAL_MANIFEST_SIM", "SEAL_MANIFEST", "SYNTHETIC_ASSUMPTION")
        doc["subject_observables"] = [event("hM", "SEAL_MANIFEST", raw={
            "full_file_sha256": "a" * 64 + "\n", "byte_length": 12,
            "final_seq": 1, "last_digest": "b" * 64, "run_id": "r"})]
        self.assert_domains(doc, True, False)

    def test_trailing_newline_in_errno(self):
        doc = subject()
        doc["declared_trust_model"] = trust("hR", "G2_WRAP_SIM", "R_WRITE_RESULT", "SYNTHETIC_ASSUMPTION")
        doc["subject_observables"] = [event("hR", "R_WRITE_RESULT", node="nA",
                                             raw={"bytes": 0, "errno": "EPIPE\n"})]
        self.assert_domains(doc, True, False)

    def test_decomposed_non_nfc_run_id(self):
        doc = subject()
        doc["subject_observables"][0]["raw_fields"]["run_id"] = "e\u0301"
        self.assert_domains(doc, True, False)

    def test_decomposed_non_nfc_log_readback(self):
        doc = subject()
        doc["declared_trust_model"] = trust("hG", "SUBJECT_LOG_READBACK", "LOG_READBACK", "SUBJECT_ARTIFACT")
        doc["subject_observables"] = [event("hG", "LOG_READBACK",
                                             raw={"log_utf8": "e\u0301", "run_id": "r"})]
        self.assert_domains(doc, True, False)

    def test_invalid_wrong_role_kind_rejected_by_both(self):
        doc = subject()
        doc["subject_observables"][0]["event_kind"] = "NODE_CLAIM"
        self.assert_domains(doc, False, False)

    def test_invalid_bool_order_rejected_by_both(self):
        doc = subject()
        doc["subject_observables"][0]["monotonic_order"] = True
        self.assert_domains(doc, False, False)

    def test_invalid_bool_identity_pid_rejected_by_both(self):
        doc = subject()
        doc["declared_trust_model"] = trust("hK", "KERNEL_SNAPSHOT_SIM", "KERNEL_SNAPSHOT", "SYNTHETIC_ASSUMPTION")
        doc["subject_observables"] = [event("hK", "KERNEL_SNAPSHOT",
                                             identity={"pid": True, "starttime": 1},
                                             raw={"state": "Z"})]
        self.assert_domains(doc, False, False)

    def test_lane_o_key_rejected_by_both(self):
        doc = subject()
        doc["subject_observables"][0]["raw_fields"]["expected_verdict"] = "PASS"
        self.assert_domains(doc, False, False)

    def test_whole_document_resource_cap_is_separate_from_j1_schema(self):
        doc = subject()
        doc["declared_trust_model"] = trust("hG", "SUBJECT_LOG_READBACK", "LOG_READBACK", "SUBJECT_ARTIFACT")
        body = "x" * 16000  # below J1's 1M-character *per-field* limit
        doc["subject_observables"] = [event("hG", "LOG_READBACK", order=i,
                                             raw={"log_utf8": body, "run_id": "r"})
                                      for i in range(1, 521)]
        encoded = canonical(doc)
        self.assertGreater(len(encoded), 8_000_000)
        self.assertTrue(direct_j1_accepts(doc), "original J1 has no equivalent whole-S-document byte cap")
        ivs = validate_lane_s_bytes(encoded)
        self.assertFalse(ivs.valid)
        self.assertEqual(ivs.reason, "EMPTY_OR_OVERSIZE_BYTES")
        # This is a provisional resource BLOCK, not a scientific verdict that
        # an otherwise legitimate J1 input was semantically invalid.


if __name__ == "__main__":
    unittest.main()
