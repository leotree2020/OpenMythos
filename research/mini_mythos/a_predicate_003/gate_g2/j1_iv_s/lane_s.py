"""Isolated Lane S *structural* validator candidate for synthetic J1.

Independent implementation: does not import any j1 modules or oracle.
A valid result proves only syntax, whitelists and declared role-shape consistency,
NOT an authenticated source, case truth, SC-08 per-case event content, or acceptance.
"""

from dataclasses import dataclass
import json
import re
import unicodedata

ASSERTIONS = frozenset(("ATTRIBUTION", "UNIQUE_REGISTRY", "ZOMBIE_AT_T", "LOG_MATCHES_SEAL", "WRITE_COMPLETE",
                        "PREVENT_PROOF", "LAWFUL_REAP", "EVIDENCE_USABLE", "DELIVERY"))
B0 = frozenset(("RUN_START", "INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD", "RUN_END"))
TIERS = {
    "B0_LEDGER": (B0, "SYNTHETIC_B0_SHAPED_TRANSCRIPT"),
    "NODE_CLAIM_SIM": (frozenset(("NODE_CLAIM",)), "UNTRUSTED_CLAIM"),
    "KERNEL_SNAPSHOT_SIM": (frozenset(("KERNEL_SNAPSHOT",)), "SYNTHETIC_ASSUMPTION"),
    "G2_WITNESS_SIM": (frozenset(("GATE_CHILD_OBSERVATION",)), "SYNTHETIC_ASSUMPTION"),
    "G2_WRAP_SIM": (frozenset(("R_WRITE_RESULT",)), "SYNTHETIC_ASSUMPTION"),
    "SEAL_MANIFEST_SIM": (frozenset(("SEAL_MANIFEST",)), "SYNTHETIC_ASSUMPTION"),
    "SUBJECT_LOG_READBACK": (frozenset(("LOG_READBACK",)), "SUBJECT_ARTIFACT"),
}
TOKEN = re.compile(r"[A-Za-z0-9_.:\-]{1,64}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
ERRNO = re.compile(r"E[A-Z0-9]{2,15}\Z")
FIXTURE_LEAK = re.compile(r"j1[-_ ]?f\d", re.IGNORECASE)
LEAK_KEYS = ("fixture", "oracle", "expected", "canonicalcard", "behaviorlabel", "behaviourlabel", "acceptance",
             "isattack", "caseid", "filename", "filepath", "inputdigest", "actualgate", "truthmodel", "grade",
             "score", "teststatus", "runstage", "ownerdecision", "groundtruth")
EVENT_REQ = frozenset(("source_handle", "event_kind", "monotonic_order", "read_status"))
EVENT_OPT = frozenset(("node_token", "identity", "gate_token", "raw_fields"))
TRUST_FIELDS = frozenset(("role", "synthetic_assumption", "allowed_event_kinds", "provenance_tier"))
IDENTITY_FIELDS = frozenset(("pid", "starttime", "ppid", "boot_id", "pidns"))
STATES = frozenset("RSDZTtXxKWPI")
READ_STATUSES = frozenset(("OK", "TORN_TAIL", "CORRUPT", "MISSING", "UNREADABLE"))
CLAIM_TYPES = frozenset(("GATE_CHILD_IDENTITY", "R_WRITTEN", "READY", "WAIT_RESULT", "OTHER"))
MAX_INPUT_BYTES = 8_000_000  # provisional parser safety budget; not a J1 scientific criterion


def _uint(v):
    return type(v) is int and v >= 0


def _pid(v):
    return type(v) is int and v >= 1


def _str(v):
    return type(v) is str and len(v) <= 256


def _token(v):
    return type(v) is str and TOKEN.fullmatch(v) is not None


def _hex(v):
    return type(v) is str and HEX.fullmatch(v) is not None


def _bool(v):
    return type(v) is bool


def _enum(choices):
    return lambda v: type(v) is str and v in choices


def _str_none(v):
    return v is None or _str(v)


def _errno(v):
    return v is None or (type(v) is str and ERRNO.fullmatch(v) is not None)


def _log(v):
    if type(v) is not str or len(v) > 1_000_000:
        return False
    try:
        v.encode("utf-8")
    except UnicodeError:
        return False
    return True


# (required, optional) raw_fields: independent rules implemented from pinned
# synthetic S contract, not imported from the system under test.
RAW = {
    "RUN_START": ({}, {"run_id": _str, "observer_pid": _uint}),
    "INTENT": ({}, {"role": _str, "label": _str, "creator": _str, "creator_pid": _uint, "mode": _str_none}),
    "FORKED": ({}, {"role": _str, "label": _str, "creator": _str, "creator_pid": _uint, "pid": _pid}),
    "REGISTERED": ({}, {"role": _str, "label": _str, "creator": _str, "creator_pid": _uint, "sid": _uint, "pgrp": _uint}),
    "RELEASED": ({}, {}),
    "ABORTED": ({}, {"reason": _str, "creation_unresolved": _bool}),
    "DEAD": ({}, {"basis": _str}),
    "RUN_END": ({}, {"run_id": _str, "cleanup_confirmed": _bool}),
    "NODE_CLAIM": ({"claim_kind": _enum(CLAIM_TYPES)}, {"pid": _uint, "starttime": _uint}),
    "KERNEL_SNAPSHOT": ({"state": _enum(STATES)}, {}),
    "GATE_CHILD_OBSERVATION": ({}, {}),
    "R_WRITE_RESULT": ({"bytes": _uint, "errno": _errno}, {"byte": lambda v: v == "R" and type(v) is str}),
    "SEAL_MANIFEST": ({"full_file_sha256": _hex, "byte_length": _uint, "final_seq": _uint,
                       "last_digest": _hex, "run_id": _str}, {}),
    "LOG_READBACK": ({"log_utf8": _log, "run_id": _str}, {}),
}
NODE_REQUIRED = frozenset(("INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD",
                           "GATE_CHILD_OBSERVATION", "R_WRITE_RESULT"))
NODE_FORBIDDEN = frozenset(("RUN_START", "RUN_END", "SEAL_MANIFEST", "LOG_READBACK"))
IDENTITY_REQUIRED = frozenset(("REGISTERED", "KERNEL_SNAPSHOT", "GATE_CHILD_OBSERVATION"))
IDENTITY_FORBIDDEN = frozenset(("RUN_START", "RUN_END", "INTENT", "RELEASED", "ABORTED", "DEAD",
                               "NODE_CLAIM", "R_WRITE_RESULT", "SEAL_MANIFEST", "LOG_READBACK"))


@dataclass(frozen=True)
class LaneSResult:
    valid: bool
    reason: str
    events: int = 0
    trust_handles: int = 0


class _Violation(ValueError):
    pass


def _require(ok, code):
    if not ok:
        raise _Violation(code)


def _scan(obj, depth=0):
    _require(depth <= 8, "NESTING_TOO_DEEP")
    if type(obj) is dict:
        for key, value in obj.items():
            _require(type(key) is str, "KEY_NOT_STRING")
            norm = "".join(c for c in key.lower() if c.isalnum())
            _require(not any(part in norm for part in LEAK_KEYS), "LANE_O_KEY")
            _scan(value, depth + 1)
    elif type(obj) in (list, tuple):
        for value in obj:
            _scan(value, depth + 1)
    elif type(obj) is str:
        _require(FIXTURE_LEAK.search(obj) is None, "LANE_O_VALUE")
        _require(unicodedata.normalize("NFC", obj) == obj, "NON_NFC_VALUE")
        obj.encode("utf-8")
    else:
        _require(obj is None or type(obj) in (bool, int), "NON_JSON_VALUE")


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise _Violation("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def _no_float(_):
    raise _Violation("FLOAT_OR_NONFINITE")


def _trust_map(trust):
    _require(type(trust) is dict and len(trust) <= 64, "TRUST_SHAPE_OR_LIMIT")
    for handle, row in trust.items():
        _require(_token(handle), "TRUST_HANDLE_INVALID")
        _require(type(row) is dict and set(row) == TRUST_FIELDS, "TRUST_FIELDS_INVALID")
        role = row["role"]
        _require(type(role) is str and role in TIERS, "TRUST_ROLE_INVALID")
        _require(row["synthetic_assumption"] is True, "TRUST_NOT_SYNTHETIC")
        _require(row["provenance_tier"] == TIERS[role][1] and type(row["provenance_tier"]) is str,
                 "TRUST_TIER_INVALID")
        kinds = row["allowed_event_kinds"]
        _require(type(kinds) in (list, tuple) and all(type(k) is str for k in kinds),
                 "TRUST_KINDS_INVALID")
        _require(set(kinds) <= TIERS[role][0], "TRUST_ROLE_CEILING")


def _identity(identity, kind):
    if identity is None:
        _require(kind not in IDENTITY_REQUIRED, "REQUIRED_IDENTITY_MISSING")
        return
    _require(kind not in IDENTITY_FORBIDDEN, "FORBIDDEN_IDENTITY")
    _require(type(identity) is dict and set(identity) <= IDENTITY_FIELDS, "IDENTITY_SHAPE_INVALID")
    _require(_pid(identity.get("pid")) and _uint(identity.get("starttime")), "IDENTITY_PID_START_INVALID")
    _require(identity.get("ppid") is None or _uint(identity.get("ppid")), "IDENTITY_PPID_INVALID")
    for field in ("boot_id", "pidns"):
        _require(identity.get(field) is None or _token(identity[field]), "IDENTITY_TOKEN_INVALID")
    if kind == "REGISTERED":
        _require(identity.get("ppid") is not None, "REGISTERED_PPID_REQUIRED")


def _event(record, trust):
    _require(type(record) is dict and EVENT_REQ <= set(record) <= EVENT_REQ | EVENT_OPT,
             "EVENT_FIELDS_INVALID")
    handle, kind = record["source_handle"], record["event_kind"]
    _require(_token(handle) and handle in trust, "EVENT_HANDLE_INVALID")
    _require(type(kind) is str and kind in RAW, "EVENT_KIND_INVALID")
    _require(kind in trust[handle]["allowed_event_kinds"], "EVENT_KIND_UNTRUSTED")
    _require(_uint(record["monotonic_order"]), "EVENT_ORDER_INVALID")
    _require(type(record["read_status"]) is str and record["read_status"] in READ_STATUSES,
             "EVENT_STATUS_INVALID")
    node = record.get("node_token")
    _require(node is None or _token(node), "EVENT_NODE_INVALID")
    _require(kind not in NODE_REQUIRED or node is not None, "EVENT_NODE_REQUIRED")
    _require(kind not in NODE_FORBIDDEN or node is None, "EVENT_NODE_FORBIDDEN")
    gate = record.get("gate_token")
    _require(gate is None or _token(gate), "EVENT_GATE_INVALID")
    _identity(record.get("identity"), kind)
    fields = record.get("raw_fields", {})
    _require(type(fields) is dict, "RAW_NOT_OBJECT")
    required, optional = RAW[kind]
    _require(set(required) <= set(fields) <= (set(required) | set(optional)), "RAW_FIELDS_INVALID")
    for key, validator in {**required, **optional}.items():
        if key in fields:
            _require(validator(fields[key]), "RAW_TYPE_INVALID")


def validate_lane_s(value) -> LaneSResult:
    """Validate a parsed S-only document. No O, provenance or test oracle access."""
    try:
        _require(type(value) is dict and set(value) == {"assertion_id", "subject_observables", "declared_trust_model"},
                 "S_TOP_LEVEL_FIELDS")
        _scan(value)
        _require(type(value["assertion_id"]) is str and value["assertion_id"] in ASSERTIONS,
                 "S_ASSERTION_INVALID")
        events = value["subject_observables"]
        _require(type(events) in (list, tuple) and len(events) <= 2000, "S_EVENTS_SHAPE_OR_LIMIT")
        trust = value["declared_trust_model"]
        _trust_map(trust)
        seen = set()
        for record in events:
            _event(record, trust)
            key = (record["source_handle"], record["monotonic_order"])
            _require(key not in seen, "DUPLICATE_SOURCE_ORDER")
            seen.add(key)
        return LaneSResult(True, "STRUCTURE_VALID", len(events), len(trust))
    except (ValueError, UnicodeError, TypeError, RecursionError) as error:
        reason = str(error) if isinstance(error, _Violation) else "UNHANDLED_INVALID_INPUT"
        return LaneSResult(False, reason)


def validate_lane_s_bytes(data) -> LaneSResult:
    """Require a single canonical UTF-8 JSON object and then validate its S shape."""
    if type(data) is not bytes:
        return LaneSResult(False, "INPUT_NOT_BYTES")
    if not data or len(data) > MAX_INPUT_BYTES:
        return LaneSResult(False, "EMPTY_OR_OVERSIZE_BYTES")
    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs,
                         parse_float=_no_float, parse_constant=_no_float)
        structure = validate_lane_s(obj)
        if not structure.valid:
            return structure
        canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")
        _require(data == canonical, "NON_CANONICAL_S_BYTES")
        return structure
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError) as error:
        reason = str(error) if isinstance(error, _Violation) else "JSON_OR_ENCODING_INVALID"
        return LaneSResult(False, reason)
