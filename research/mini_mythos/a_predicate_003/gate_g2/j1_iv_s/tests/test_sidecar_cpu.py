"""Local non-formal CPU unit probes; no official S/O fixtures or custody claims."""

import hashlib
import json
import unittest

from j1_iv_s.sidecar import verify_chain, verify_f05_reference


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def make_records(n=3, *, second_item=None):
    result = []
    last = "0" * 64
    for i in range(1, n + 1):
        value = {"seq": i, "prev_digest": last, "kind": "SYNTH", "body": {"item": second_item if i == 2 and second_item is not None else i}}
        last = hashlib.sha256(canonical(value)).hexdigest()
        result.append(dict(value, event_digest=last))
    return [canonical(r) + b"\n" for r in result]


def dataset():
    records = make_records()
    ref = b"".join(records)
    short = b"".join(records[:2])
    manifest = {"full_file_sha256": hashlib.sha256(ref).hexdigest(),
                "byte_length": len(ref), "final_seq": 3,
                "last_digest": json.loads(records[-1])["event_digest"],
                "run_id": "run-synth-01"}
    return short, ref, manifest


class ChainTests(unittest.TestCase):
    def test_complete_three_records(self):
        self.assertTrue(verify_chain(dataset()[1]).valid)

    def test_complete_two_record_prefix(self):
        self.assertTrue(verify_chain(dataset()[0]).valid)

    def test_torn_tail(self):
        self.assertEqual(verify_chain(dataset()[0][:-1]).reason, "TORN_TAIL")

    def test_empty_log(self):
        self.assertEqual(verify_chain(b"").reason, "EMPTY_LOG")

    def test_duplicate_keys(self):
        log = make_records(1)[0].replace(b'"kind":"SYNTH",', b'"kind":"SYNTH","kind":"SYNTH",')
        self.assertFalse(verify_chain(log).valid)

    def test_corrupted_digest(self):
        data = make_records(1)[0].replace(b'"event_digest":"', b'"event_digest":"f')
        self.assertFalse(verify_chain(data).valid)

    def test_broken_chain(self):
        data = make_records(2)
        self.assertFalse(verify_chain(data[0] + data[1].replace(b'"prev_digest":"', b'"prev_digest":"f')).valid)

    def test_non_contiguous_sequence(self):
        data = make_records(2)
        changed = data[1].replace(b'"seq":2', b'"seq":3')
        self.assertFalse(verify_chain(data[0] + changed).valid)

    def test_noncanonical(self):
        self.assertFalse(verify_chain(make_records(1)[0].replace(b',"kind":', b', "kind":')).valid)

    def test_bool_seq(self):
        self.assertFalse(verify_chain(make_records(1)[0].replace(b'"seq":1', b'"seq":true')).valid)

    def test_float(self):
        self.assertFalse(verify_chain(make_records(1)[0].replace(b'"item":1', b'"item":1.0')).valid)

    def test_invalid_utf8(self):
        self.assertFalse(verify_chain(b"\xff\n").valid)

    def test_empty_extra_line(self):
        self.assertEqual(verify_chain(make_records(1)[0] + b"\n").reason, "EMPTY_LINE")

    def test_non_nfc_unicode(self):
        raw = make_records(1)[0].replace(b'"kind":"SYNTH"', b'"kind":"e\\u0301"')
        self.assertFalse(verify_chain(raw).valid)


class F05Tests(unittest.TestCase):
    def test_valid_shorter_log_is_valid_mismatch(self):
        s, ref, man = dataset()
        self.assertEqual(verify_f05_reference(s, ref, man, "run-synth-01").status, "VALID_SEAL_MISMATCH")

    def test_full_reference_matches(self):
        _, ref, man = dataset()
        self.assertEqual(verify_f05_reference(ref, ref, man, "run-synth-01").status, "VALID_SEAL_MATCH")

    def test_shorter_torn_tail_invalid(self):
        s, ref, man = dataset()
        self.assertEqual(verify_f05_reference(s[:-1], ref, man, "run-synth-01").status, "INVALID_INSTRUMENT")

    def test_changed_reference_manifest_invalid(self):
        s, ref, man = dataset()
        man["byte_length"] += 1
        self.assertEqual(verify_f05_reference(s, ref, man, "run-synth-01").status, "INVALID_INSTRUMENT")

    def test_wrong_run_id_invalid(self):
        s, ref, man = dataset()
        self.assertEqual(verify_f05_reference(s, ref, man, "different-run").status, "INVALID_INSTRUMENT")

    def test_malformed_manifest_invalid(self):
        s, ref, man = dataset()
        del man["final_seq"]
        self.assertEqual(verify_f05_reference(s, ref, man, "run-synth-01").status, "INVALID_INSTRUMENT")

    def test_nonprefix_two_line_log_invalid(self):
        s, ref, man = dataset()
        other = b"".join(make_records(2, second_item=99))
        self.assertTrue(verify_chain(other).valid)
        result = verify_f05_reference(other, ref, man, "run-synth-01")
        self.assertEqual(result.status, "INVALID_INSTRUMENT")
        self.assertEqual(result.reason, "NOT_REFERENCE_PREFIX")

    def test_reference_chain_corrupt_invalid(self):
        s, ref, man = dataset()
        bad = ref.replace(b'"item":3', b'"item":4')
        self.assertEqual(verify_f05_reference(s, bad, man, "run-synth-01").status, "INVALID_INSTRUMENT")

    def test_bool_in_manifest_invalid(self):
        s, ref, man = dataset()
        man["final_seq"] = True
        self.assertEqual(verify_f05_reference(s, ref, man, "run-synth-01").status, "INVALID_INSTRUMENT")


if __name__ == "__main__":
    unittest.main()
