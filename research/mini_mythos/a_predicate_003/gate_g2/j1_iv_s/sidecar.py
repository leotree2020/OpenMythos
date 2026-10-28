"""Independent J1 IV-S *candidate* sidecar checker (stdlib, CPU only).

Does not import j1.codec, j1.schema, j1.judge or j1.oracle. Verifies
internal bytes/chain and a caller-supplied F05 reference relation. It NEVER
attests that the reference came from an independent custodian, and NEVER
returns formal case/run acceptance.
"""

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_KEYS = frozenset(("seq", "prev_digest", "kind", "body", "event_digest"))
_MANIFEST = frozenset(("full_file_sha256", "byte_length", "final_seq", "last_digest", "run_id"))
_GENESIS = "0" * 64
_MAX_BYTES = 4_000_001  # defensive cap; policy is not a J1 schema equivalence claim
_MAX_DEPTH = 8


@dataclass(frozen=True)
class ChainResult:
    valid: bool
    reason: str
    count: int = 0
    last_digest: str | None = None


@dataclass(frozen=True)
class ReferenceResult:
    status: str  # INVALID_INSTRUMENT, VALID_SEAL_MATCH, VALID_SEAL_MISMATCH
    reason: str


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("DUPLICATE_KEY")
        obj[key] = value
    return obj


def _invalid_constant(_):
    raise ValueError("NONFINITE_NUMBER")


def _invalid_float(_):
    raise ValueError("FLOAT_VALUE")


def _validate_tree(value, depth=0):
    if depth > _MAX_DEPTH:
        raise ValueError("NESTING_TOO_DEEP")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("NON_NFC_STRING")
        value.encode("utf-8")
        return
    if type(value) is list:
        for item in value:
            _validate_tree(item, depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("NONSTRING_KEY")
            _validate_tree(key, depth + 1)
            _validate_tree(item, depth + 1)
        return
    raise ValueError("UNSUPPORTED_TYPE")


def _canon(value):
    _validate_tree(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hex64(s):
    return type(s) is str and _HEX64.fullmatch(s) is not None


def verify_chain(data: bytes) -> ChainResult:
    """Full strict parse; independent from J1 codec; no silent line repairs."""
    if type(data) is not bytes:
        return ChainResult(False, "INPUT_NOT_BYTES")
    if not data:
        return ChainResult(False, "EMPTY_LOG")
    if len(data) > _MAX_BYTES:
        return ChainResult(False, "LOG_TOO_LARGE")
    if not data.endswith(b"\n"):
        return ChainResult(False, "TORN_TAIL")
    lines = data[:-1].split(b"\n")
    if not lines or any(not line for line in lines):
        return ChainResult(False, "EMPTY_LINE")
    previous = _GENESIS
    for seq, line in enumerate(lines, 1):
        try:
            obj = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=_invalid_constant, parse_float=_invalid_float)
            if type(obj) is not dict or frozenset(obj) != _KEYS:
                return ChainResult(False, "RECORD_SHAPE")
            if _canon(obj) != line:
                return ChainResult(False, "NON_CANONICAL")
            if type(obj["seq"]) is not int or obj["seq"] != seq:
                return ChainResult(False, "SEQ_INVALID")
            if type(obj["kind"]) is not str or not obj["kind"] or type(obj["body"]) is not dict:
                return ChainResult(False, "KIND_OR_BODY_INVALID")
            if not _hex64(obj["prev_digest"]) or not _hex64(obj["event_digest"]):
                return ChainResult(False, "DIGEST_FORMAT")
            if obj["prev_digest"] != previous:
                return ChainResult(False, "CHAIN_BROKEN")
            digest = hashlib.sha256(_canon({k: obj[k] for k in obj if k != "event_digest"})).hexdigest()
            if obj["event_digest"] != digest:
                return ChainResult(False, "DIGEST_MISMATCH")
            previous = digest
        except (UnicodeError, ValueError, TypeError, OverflowError, RecursionError):
            return ChainResult(False, "RECORD_INVALID")
    return ChainResult(True, "CHAIN_VALID", len(lines), previous)


def verify_f05_reference(readback: bytes, reference: bytes, manifest: dict, run_id: str) -> ReferenceResult:
    """F05 2/3 complete-record prefix contract; byte integrity only.

    No trusted origin for reference, manifest or run_id is established.
    This function cannot supply IV-O, IV-C, IV-G or case acceptance.
    """
    got, ref = verify_chain(readback), verify_chain(reference)
    if not got.valid:
        return ReferenceResult("INVALID_INSTRUMENT", "READBACK_" + got.reason)
    if not ref.valid:
        return ReferenceResult("INVALID_INSTRUMENT", "REFERENCE_" + ref.reason)
    if ref.count != 3 or got.count not in (2, 3):
        return ReferenceResult("INVALID_INSTRUMENT", "F05_RECORD_COUNT")
    if type(run_id) is not str or not run_id:
        return ReferenceResult("INVALID_INSTRUMENT", "RUN_ID_INVALID")
    if type(manifest) is not dict or frozenset(manifest) != _MANIFEST:
        return ReferenceResult("INVALID_INSTRUMENT", "MANIFEST_SHAPE")
    if not (_hex64(manifest["full_file_sha256"]) and _hex64(manifest["last_digest"])):
        return ReferenceResult("INVALID_INSTRUMENT", "MANIFEST_DIGEST_FORMAT")
    if (type(manifest["byte_length"]) is not int or type(manifest["final_seq"]) is not int
            or type(manifest["run_id"]) is not str):
        return ReferenceResult("INVALID_INSTRUMENT", "MANIFEST_TYPE")
    if (manifest["byte_length"] != len(reference)
            or manifest["full_file_sha256"] != hashlib.sha256(reference).hexdigest()
            or manifest["final_seq"] != ref.count
            or manifest["last_digest"] != ref.last_digest
            or manifest["run_id"] != run_id):
        return ReferenceResult("INVALID_INSTRUMENT", "MANIFEST_REFERENCE_MISMATCH")
    if not reference.startswith(readback):
        return ReferenceResult("INVALID_INSTRUMENT", "NOT_REFERENCE_PREFIX")
    if readback == reference:
        return ReferenceResult("VALID_SEAL_MATCH", "INTERNAL_VALID_AND_SEAL_EQUAL")
    return ReferenceResult("VALID_SEAL_MISMATCH", "INTERNAL_VALID_BUT_SEAL_DIFFERS")
