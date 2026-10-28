"""Independent-author supplemental adversarial CPU probes for the IV-S candidate.

These tests generate ephemeral nonofficial synthetic inputs and establish no
Lane O independent truth, cryptographic custody, or formal acceptance PASS.
"""

import hashlib
import json
import unittest

from j1_iv_s.sidecar import verify_chain, verify_f05_reference


def _serialize(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _records(count=3, *, marker=0):
    chunks = []
    previous_digest = "0" * 64
    for i in range(1, count + 1):
        payload = {"seq": i, "prev_digest": previous_digest,
                   "kind": "SYNTH", "body": {"marker": marker if i == 2 else i}}
        previous_digest = hashlib.sha256(_serialize(payload)).hexdigest()
        chunks.append(_serialize({**payload, "event_digest": previous_digest}) + b"\n")
    return chunks


def _reference():
    chunks = _records()
    complete = b"".join(chunks)
    manifest = {"full_file_sha256": hashlib.sha256(complete).hexdigest(),
                "byte_length": len(complete), "final_seq": 3,
                "last_digest": json.loads(chunks[-1])["event_digest"],
                "run_id": "run-synth-01"}
    return b"".join(chunks[:2]), complete, manifest


class ChainAdversarialCpu(unittest.TestCase):
    def test_valid_non_ascii_nfc_body(self):
        payload = {"seq": 1, "prev_digest": "0" * 64,
                   "kind": "CHECK", "body": {"label": "東京"}}
        rec = {**payload, "event_digest": hashlib.sha256(_serialize(payload)).hexdigest()}
        self.assertTrue(verify_chain(_serialize(rec) + b"\n").valid)

    def test_non_nfc_body_rejected_even_with_matching_digest(self):
        payload = {"seq": 1, "prev_digest": "0" * 64,
                   "kind": "CHECK", "body": {"label": "e\u0301"}}
        rec = {**payload, "event_digest": hashlib.sha256(_serialize(payload)).hexdigest()}
        self.assertFalse(verify_chain(_serialize(rec) + b"\n").valid)

    def test_equivalent_json_escape_is_not_canonical(self):
        line = _records(1)[0]
        changed = line.replace(b'"kind":"SYNTH"', b'"kind":"S\\u0059NTH"')
        self.assertNotEqual(line, changed)
        self.assertFalse(verify_chain(changed).valid)

    def test_reordered_valid_record_chunks_rejected(self):
        chunks = _records()
        self.assertFalse(verify_chain(chunks[0] + chunks[2] + chunks[1]).valid)

    def test_boolean_prev_digest_rejected(self):
        chunk = _records(1)[0]
        changed = chunk.replace(b'"prev_digest":"' + b"0" * 64 + b'"', b'"prev_digest":true')
        self.assertNotEqual(chunk, changed)
        self.assertFalse(verify_chain(changed).valid)

    def test_array_body_rejected_even_with_valid_hash(self):
        payload = {"seq": 1, "prev_digest": "0" * 64, "kind": "TEST", "body": []}
        rec = {**payload, "event_digest": hashlib.sha256(_serialize(payload)).hexdigest()}
        self.assertFalse(verify_chain(_serialize(rec) + b"\n").valid)

    def test_non_bytes_argument_rejected(self):
        self.assertEqual(verify_chain("not bytes").reason, "INPUT_NOT_BYTES")


class F05AdversarialCpu(unittest.TestCase):
    def test_manifest_last_digest_tamper_rejected(self):
        short, complete, manifest = _reference()
        manifest["last_digest"] = "0" * 64
        self.assertEqual(verify_f05_reference(short, complete, manifest, "run-synth-01").status,
                         "INVALID_INSTRUMENT")

    def test_self_signed_reference_does_not_mean_independent_custody(self):
        # A malicious caller can replace both the reference and its manifest.
        # The byte checker can detect neither authorship nor independent custody.
        fake_chunks = _records(marker=123456)
        fake = b"".join(fake_chunks)
        manifest = {"full_file_sha256": hashlib.sha256(fake).hexdigest(),
                    "byte_length": len(fake), "final_seq": 3,
                    "last_digest": json.loads(fake_chunks[-1])["event_digest"],
                    "run_id": "run-synth-01"}
        self.assertEqual(verify_f05_reference(fake, fake, manifest, "run-synth-01").status,
                         "VALID_SEAL_MATCH")
        # This assertion documents the LIMIT; it does not award IV-O/IV-C PASS.

    def test_reference_with_four_records_rejected(self):
        short, _complete, manifest = _reference()
        four = b"".join(_records(4))
        self.assertEqual(verify_f05_reference(short, four, manifest, "run-synth-01").status,
                         "INVALID_INSTRUMENT")


if __name__ == "__main__":
    unittest.main()
