"""Synthetic CPU custody compression and strict decoding fixtures only."""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fixture_storage_codec", ROOT / "storage_codec.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def pin(payload):
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def crafted(raw, count=1):
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0, compresslevel=9) as compressor:
        compressor.write(raw)
    encoded = stream.getvalue()
    return encoded, {"schema": C.SCHEMA, "compression": C.COMPRESSION,
                     "record_count": count, "canonical": pin(raw), "compressed": pin(encoded)}


class StorageTests(unittest.TestCase):
    def setUp(self):
        repeated = pin(b"same bytes at separate protected paths")
        self.mapping = {"/workspaces/old tree/a.py": repeated.copy(),
                        "/workspaces/new tree/a.py": repeated.copy(),
                        "/workspaces/\u65e7\u8bb0\u5f55/empty": pin(b"")}

    def test_roundtrip_keeps_every_path_even_when_pins_are_identical(self):
        encoded, receipt = C.pack(self.mapping)
        decoded = C.unpack(encoded, receipt)
        self.assertEqual(decoded, self.mapping)
        self.assertEqual(set(decoded), set(self.mapping))
        self.assertEqual(receipt["record_count"], 3)
        self.assertEqual(receipt["canonical"], pin(C.canonical_bytes(self.mapping)))
        self.assertEqual(receipt["compressed"], pin(encoded))

    def test_deterministic_header_sorting_and_same_runtime_output(self):
        encoded, receipt = C.pack(self.mapping)
        other, other_receipt = C.pack(dict(reversed(list(self.mapping.items()))))
        self.assertEqual(encoded, other)
        self.assertEqual(receipt, other_receipt)
        self.assertEqual(encoded[:10], C.HEADER)
        self.assertEqual(gzip.decompress(encoded), C.canonical_bytes(self.mapping))
        self.assertEqual(encoded[4:8], bytes(4))
        self.assertEqual(encoded[9], 255)

    def test_storage_limit_boundaries_and_exception_class(self):
        encoded, receipt = C.pack(self.mapping)
        raw = C.canonical_bytes(self.mapping)
        with mock.patch.object(C, "COMPRESSED_LIMIT", len(encoded)), mock.patch.object(C, "CANONICAL_LIMIT", len(raw)):
            self.assertEqual(C.unpack(*C.pack(self.mapping)), self.mapping)
        with mock.patch.object(C, "COMPRESSED_LIMIT", len(encoded)-1):
            with self.assertRaises(C.StorageLimitError):
                C.pack(self.mapping)
        with mock.patch.object(C, "CANONICAL_LIMIT", len(raw)-1):
            with self.assertRaises(C.StorageLimitError):
                C.pack(self.mapping)
        bad = copy.deepcopy(receipt); bad["compressed"]["bytes"] = C.COMPRESSED_LIMIT+1
        with self.assertRaises(C.StorageLimitError):
            C.unpack(encoded, bad)
        with self.assertRaises(C.StorageLimitError):
            C.unpack(b"x"*(C.COMPRESSED_LIMIT+1), receipt)

    def test_compressed_canonical_count_and_header_tampering_rejected(self):
        encoded, receipt = C.pack(self.mapping)
        bad = copy.deepcopy(receipt); bad["compressed"]["sha256"] = "f"*64
        with self.assertRaises(C.CodecError): C.unpack(encoded, bad)
        bad = copy.deepcopy(receipt); bad["canonical"]["sha256"] = "f"*64
        with self.assertRaises(C.CodecError): C.unpack(encoded, bad)
        bad = copy.deepcopy(receipt); bad["record_count"] += 1
        with self.assertRaises(C.CodecError): C.unpack(encoded, bad)
        changed = encoded[:4] + b"\x01" + encoded[5:]
        bad = copy.deepcopy(receipt); bad["compressed"] = pin(changed)
        with self.assertRaises(C.CodecError): C.unpack(changed, bad)

    def test_crc_truncation_trailing_and_concatenated_streams_rejected(self):
        encoded, receipt = C.pack(self.mapping)
        crc_bad = encoded[:-8] + bytes([encoded[-8]^1]) + encoded[-7:]
        for changed in (crc_bad, encoded[:-1], encoded+b"extra", encoded+encoded):
            bad = copy.deepcopy(receipt); bad["compressed"] = pin(changed)
            with self.subTest(length=len(changed)):
                with self.assertRaises(C.CodecError): C.unpack(changed, bad)

    def test_bounded_decompression_rejects_high_expansion(self):
        # Deliberately compressible synthetic bytes, never real corpus/weights.
        raw = b"x" * (C.CANONICAL_LIMIT+1)
        encoded, receipt = crafted(raw)
        self.assertLess(len(encoded), C.COMPRESSED_LIMIT)
        receipt["canonical"]["bytes"] = C.CANONICAL_LIMIT
        with self.assertRaises(C.StorageLimitError): C.unpack(encoded, receipt)

    def test_duplicate_json_keys_cannot_silently_reduce_protected_scope(self):
        descriptor = json.dumps(pin(b"a"), separators=(",", ":"))
        raw = ("{\"/workspaces/a\":"+descriptor+",\"/workspaces/a\":"+descriptor+"}\n").encode()
        encoded, receipt = crafted(raw, count=2)
        with self.assertRaisesRegex(C.CodecError, "Duplicate JSON key"):
            C.unpack(encoded, receipt)
        raw = ("{\"/workspaces/a\":{\"bytes\":1,\"bytes\":2,\"sha256\":\""+"a"*64+"\"}}\n").encode()
        with self.assertRaisesRegex(C.CodecError, "Duplicate JSON key"):
            C.unpack(*crafted(raw))

    def test_strict_mapping_and_receipt_schemas(self):
        invalid = [{}, {"relative":pin(b"a")}, {"/workspaces/../a":pin(b"a")},
                   {"/workspaces/a":dict(pin(b"a"),extra=1)},
                   {"/workspaces/a":{"bytes":True,"sha256":"a"*64}},
                   {"/workspaces/a":{"bytes":1,"sha256":"A"*64}},
                   {"/workspaces/a":{"bytes":-1,"sha256":"a"*64}}]
        for mapping in invalid:
            with self.subTest(mapping=mapping):
                with self.assertRaises(C.CodecError): C.pack(mapping)
        encoded, receipt = C.pack(self.mapping)
        for changes in ({"record_count":True},{"record_count":0},{"schema":"unknown"},{"extra":1}):
            bad = dict(receipt, **changes)
            with self.subTest(changes=changes):
                with self.assertRaises(C.CodecError): C.unpack(encoded,bad)

    def test_noncanonical_or_invalid_json_is_not_accepted_with_valid_hashes(self):
        raws = [json.dumps(self.mapping, indent=2).encode(), b"not-json", b"\xff", b"{\"/workspaces/a\":NaN}\n"]
        for raw in raws:
            with self.subTest(raw=raw[:12]):
                with self.assertRaises(C.CodecError): C.unpack(*crafted(raw, count=3))

    def test_file_roundtrip_exclusive_write_and_file_size_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"protected_before.json.gz"
            receipt = C.write_manifest(path,self.mapping)
            before = path.read_bytes()
            self.assertEqual(C.read_manifest(path,receipt), self.mapping)
            with self.assertRaises(C.CodecError): C.write_manifest(path,self.mapping)
            self.assertEqual(path.read_bytes(),before)
            path.write_bytes(before+b"x")
            with self.assertRaises(C.CodecError): C.read_manifest(path,receipt)

    def test_output_and_ancestor_symlinks_refused_without_open(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);path=base/"protected_before.json.gz"
            original=Path.is_symlink
            for link in (path,base):
                with mock.patch.object(Path,"is_symlink",lambda value: value==link or original(value)):
                    with mock.patch.object(C.os,"open",side_effect=AssertionError("must reject before opening")):
                        with self.assertRaises(C.CodecError): C.write_manifest(path,self.mapping)
            self.assertFalse(path.exists())

    def test_oversized_manifest_never_leaves_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"protected_before.json.gz"
            with mock.patch.object(C,"COMPRESSED_LIMIT",18):
                with self.assertRaises(C.StorageLimitError): C.write_manifest(path,self.mapping)
            self.assertFalse(path.exists())


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path,required=True);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(StorageTests)
    test_ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    passed=result.wasSuccessful() and result.testsRun==len(test_ids) and not result.skipped
    report={"Purpose":"Lossless bounded full-scope custody compression fixtures",
            "Environment":{"python":sys.version,"runtime":"CPU standard library only"},
            "Input":"Synthetic complete path maps and gzip corruption cases; no target/model/real evidence reads",
            "Expected":"Exact full path roundtrip, deterministic within-runtime bytes, integrity/bounds/overwrite guards; no skips",
            "Actual":{"test_ids":test_ids,"planned":len(test_ids),"run":result.testsRun,
                      "failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),
                      "expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},
            "Status":"PASS" if passed else "FAIL"}
    with args.report.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write("\n")
    return 0 if passed else 2


if __name__=="__main__":raise SystemExit(main())
