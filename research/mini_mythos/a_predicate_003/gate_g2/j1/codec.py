"""J1 deterministic serialisation and sidecar chain / seal checks.  Pure functions on bytes and plain data.  NOT TESTED / NEVER EXECUTED.

Proposed byte contract (DRAFT, not frozen; open question OQ-3 / OQ-7): UTF-8, strings already in Unicode NFC (a non-NFC string is REJECTED, never
silently normalised), object keys sorted, compact separators, no floats / NaN / Infinity, booleans never accepted where an integer is required,
every line newline-terminated.

Evidence boundary: a matching hash chain or a matching seal proves that THESE BYTES are the sealed bytes.  It does not prove that any kernel event
happened, who wrote the log, or that a seal custodian exists.  No signature, key custody or filesystem durability is modelled here.
"""
import hashlib
import json
import unicodedata

GENESIS_DIGEST = "0" * 64
MAX_DEPTH = 8

MATCH = "MATCH"
MISMATCH = "MISMATCH"
UNDECIDABLE = "UNDECIDABLE"


class CodecError(ValueError):
    """Raised for input that cannot be canonically serialised (never for a mere mismatch)."""


def _check_value(v, depth):
    if depth > MAX_DEPTH:
        raise CodecError("nesting too deep")
    if v is None or type(v) is bool or type(v) is int:
        return
    if type(v) is str:
        if unicodedata.normalize("NFC", v) != v:
            raise CodecError("string is not NFC")
        try:
            v.encode("utf-8")
        except UnicodeEncodeError:
            raise CodecError("string is not encodable as UTF-8")
        return
    if isinstance(v, (list, tuple)):
        for x in v:
            _check_value(x, depth + 1)
        return
    if type(v) is dict:
        for k, x in v.items():
            if type(k) is not str:
                raise CodecError("non-string key")
            _check_value(k, depth + 1)
            _check_value(x, depth + 1)
        return
    raise CodecError("type %s is not serialisable (no floats, no non-JSON types)" % type(v).__name__)


def canonical_json(obj):
    """-> bytes.  Deterministic: sorted keys, compact separators, UTF-8, ensure_ascii=False."""
    _check_value(obj, 0)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data):
    if type(data) is not bytes:
        raise CodecError("sha256_hex needs bytes")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- sidecar records (proposed shape; DRAFT)
# record = {"seq": int >= 1, "prev_digest": hex64, "kind": str, "body": dict, "event_digest": hex64}
# event_digest = sha256(canonical_json(record without "event_digest")); genesis prev_digest = "0" * 64; one canonical record per line.
def record_digest(record_without_digest):
    return sha256_hex(canonical_json(record_without_digest))


def build_record(seq, prev_digest, kind, body):
    """Builder for a LATER, separately authorised fixture-materialisation stage.  Not used to create any fixture in this stage."""
    if type(seq) is not int or seq < 1:
        raise CodecError("seq must be an integer >= 1")
    base = {"seq": seq, "prev_digest": prev_digest, "kind": kind, "body": body}
    rec = dict(base)
    rec["event_digest"] = record_digest(base)
    return rec


def serialize_log(records):
    """-> bytes: canonical record lines, each terminated by a newline."""
    return b"".join(canonical_json(r) + b"\n" for r in records)


class SidecarParse:
    """Result of parse_sidecar.  ok is True only if EVERY line is a canonical, correctly chained record and the file ends with a newline."""

    def __init__(self, ok, records, final_seq, last_digest, problems):
        self.ok = ok
        self.records = records
        self.final_seq = final_seq
        self.last_digest = last_digest
        self.problems = problems


def parse_sidecar(data):
    """Strict parse: nothing is skipped, repaired or guessed.  Torn tail, empty line, non-canonical line, bad digest, broken chain, seq gap,
    bool-as-int, float -> problems (ok=False).  An empty file is ok=False (no genesis evidence)."""
    problems = []
    records = []
    if type(data) is not bytes:
        return SidecarParse(False, [], None, None, ["INPUT_NOT_BYTES"])
    if not data:
        return SidecarParse(False, [], None, None, ["EMPTY_LOG"])
    if not data.endswith(b"\n"):
        problems.append("TORN_TAIL_NO_FINAL_NEWLINE")
    lines = data.split(b"\n")
    body_lines = lines[:-1]                  # the last element is b"" (clean end) or the torn tail, which is reported above and never parsed
    prev = GENESIS_DIGEST
    expect = 1
    for i, ln in enumerate(body_lines):
        if not ln:
            problems.append("EMPTY_LINE_AT_%d" % (i + 1))
            continue
        try:
            obj = json.loads(ln.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            problems.append("UNDECODABLE_LINE_AT_%d" % (i + 1))
            continue
        if type(obj) is not dict or set(obj) != {"seq", "prev_digest", "kind", "body", "event_digest"}:
            problems.append("BAD_RECORD_SHAPE_AT_%d" % (i + 1))
            continue
        try:
            canon = canonical_json(obj)
        except CodecError:
            problems.append("NOT_SERIALISABLE_AT_%d" % (i + 1))
            continue
        if canon != ln:
            problems.append("NON_CANONICAL_LINE_AT_%d" % (i + 1))
            continue
        if type(obj["seq"]) is not int or obj["seq"] != expect:
            problems.append("SEQ_GAP_OR_BOOL_AT_%d" % (i + 1))
        if obj["prev_digest"] != prev:
            problems.append("CHAIN_BROKEN_AT_%d" % (i + 1))
        base = {"seq": obj["seq"], "prev_digest": obj["prev_digest"], "kind": obj["kind"], "body": obj["body"]}
        try:
            good = record_digest(base) == obj["event_digest"]
        except CodecError:
            good = False
        if not good:
            problems.append("DIGEST_MISMATCH_AT_%d" % (i + 1))
        records.append(obj)
        prev = obj["event_digest"] if type(obj["event_digest"]) is str else prev
        expect += 1
    if not records:
        problems.append("NO_VALID_RECORD")
    ok = not problems
    final_seq = records[-1]["seq"] if records else None
    last = records[-1]["event_digest"] if records else None
    return SidecarParse(ok, records, final_seq, last, problems)


# ---------------------------------------------------------------- seal comparison
_MANIFEST_FIELDS = ("full_file_sha256", "byte_length", "final_seq", "last_digest", "run_id")


def _hex64(v):
    return type(v) is str and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def manifest_problems(manifest):
    """-> list of problem codes (empty = well-formed).  A malformed manifest can never produce MISMATCH, only UNDECIDABLE."""
    p = []
    if type(manifest) is not dict or set(manifest) != set(_MANIFEST_FIELDS):
        return ["MANIFEST_SHAPE"]
    if not _hex64(manifest["full_file_sha256"]):
        p.append("MANIFEST_SHA")
    if not _hex64(manifest["last_digest"]):
        p.append("MANIFEST_LAST_DIGEST")
    for name in ("byte_length", "final_seq"):
        if type(manifest[name]) is not int or manifest[name] < 0:
            p.append("MANIFEST_" + name.upper())
    if type(manifest["run_id"]) is not str or not manifest["run_id"]:
        p.append("MANIFEST_RUN_ID")
    return p


def compare_seal(log_text, log_run_id, manifest):
    """Compare read-back log text with an independently declared seal manifest.  -> (status, reasons) with status MATCH | MISMATCH | UNDECIDABLE.

      MISMATCH    : the bytes or (once parseable) the sequence / head / run id POSITIVELY contradict a well-formed manifest.
      UNDECIDABLE : malformed manifest, unencodable text, or bytes that match the seal but cannot be parsed to check seq / head.
      MATCH       : byte length, SHA-256, final seq, last digest and run id all agree and the whole chain verified.
    Hash agreement is integrity of bytes only, never event authenticity."""
    mp = manifest_problems(manifest)
    if mp:
        return UNDECIDABLE, mp
    try:
        data = log_text.encode("utf-8")
    except (UnicodeEncodeError, AttributeError):
        return UNDECIDABLE, ["LOG_NOT_ENCODABLE"]
    reasons = []
    if len(data) != manifest["byte_length"]:
        reasons.append("BYTE_LENGTH_DIFFERS")
    if sha256_hex(data) != manifest["full_file_sha256"]:
        reasons.append("FULL_FILE_SHA256_DIFFERS")
    if reasons:
        return MISMATCH, reasons
    parsed = parse_sidecar(data)
    if not parsed.ok:
        return UNDECIDABLE, ["SEALED_BYTES_NOT_A_VALID_CHAIN"] + parsed.problems[:5]
    if parsed.final_seq != manifest["final_seq"]:
        reasons.append("FINAL_SEQ_DIFFERS")
    if parsed.last_digest != manifest["last_digest"]:
        reasons.append("LAST_DIGEST_DIFFERS")
    if log_run_id != manifest["run_id"]:
        reasons.append("RUN_ID_DIFFERS")
    if reasons:
        return MISMATCH, reasons
    return MATCH, ["BYTES_CHAIN_AND_MANIFEST_AGREE"]
