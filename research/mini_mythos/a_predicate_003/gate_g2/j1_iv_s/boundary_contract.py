"""Non-authoritative input-domain delta probe for independent J1 IV-S research.

Compares *transcribed* J1 schema regex/str rules with the isolated IV-S
stricter policies. Does NOT import J1, authenticate a source, or decide
formal S/O, case/run acceptance. Source and IV-S versions must be pinned by
an external reviewer before a verdict based on this table can be trusted.
"""
from dataclasses import dataclass
import re
import unicodedata

_J1_PATTERNS = {
    "token": re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$"),
    "hex64": re.compile(r"^[0-9a-f]{64}$"),
    "errno": re.compile(r"^E[A-Z0-9]{2,15}$"),
}
_IVS_PATTERNS = {
    "token": re.compile(r"[A-Za-z0-9_.:\-]{1,64}\Z"),
    "hex64": re.compile(r"[0-9a-f]{64}\Z"),
    "errno": re.compile(r"E[A-Z0-9]{2,15}\Z"),
}
MAX_S_DOC_BYTES_PROVISIONAL = 8_000_000
J1_LOG_FIELD_MAX_CHARACTERS = 1_000_000


@dataclass(frozen=True)
class BoundaryObservation:
    field: str
    j1_schema_accepts: bool
    independent_ivs_accepts: bool
    result: str
    # This is an observed difference between transcribed predicates, not a
    # judgment about the correct scientific acceptance contract.


@dataclass(frozen=True)
class BudgetObservation:
    result: str
    measured_bytes: int | None
    policy_limit: int
    formal_input_validity: str = "NOT_DETERMINED"


def _compare(kind: str, j1: bool, ivs: bool) -> BoundaryObservation:
    if j1 and ivs:
        status = "AGREE_ACCEPT"
    elif not j1 and not ivs:
        status = "AGREE_REJECT"
    elif j1:
        status = "J1_ACCEPTS_IVS_REJECTS_UNRESOLVED"
    else:
        status = "J1_REJECTS_IVS_ACCEPTS_UNRESOLVED"
    return BoundaryObservation(kind, j1, ivs, status)


def compare_field(kind: str, value: object) -> BoundaryObservation:
    """Compare known edge predicates, never infer a complete J1 verdict.

    kind: token, hex64, errno, string_nfc, or log_utf8_nfc.
    The last two demonstrate that J1 _v_str/_v_log and J1 codec's NFC
    precondition need separate contracts; they do not mimic whole _scan.
    """
    if kind in _J1_PATTERNS:
        if kind == "errno" and value is None:
            return _compare(kind, True, True)
        if type(value) is not str:
            return _compare(kind, False, False)
        return _compare(kind,
                        _J1_PATTERNS[kind].match(value) is not None,
                        _IVS_PATTERNS[kind].fullmatch(value) is not None)
    if kind == "string_nfc":
        if type(value) is not str:
            return _compare(kind, False, False)
        # This mirrors _v_str and the extra recursive IV-S NFC check.
        j1 = len(value) <= 256
        ivs = j1 and unicodedata.is_normalized("NFC", value)
        return _compare(kind, j1, ivs)
    if kind == "log_utf8_nfc":
        if type(value) is not str or len(value) > J1_LOG_FIELD_MAX_CHARACTERS:
            return _compare(kind, False, False)
        try:
            value.encode("utf-8")
        except UnicodeError:
            return _compare(kind, False, False)
        return _compare(kind, True, unicodedata.is_normalized("NFC", value))
    raise ValueError("UNKNOWN_FIELD_KIND")


def review_provisional_size(byte_count: object) -> BudgetObservation:
    """Resource budget preflight; never labels oversized S as schema-invalid.

    Caller supplies a measured byte count to avoid allocating huge input;
    no measurement trust or byte integrity follows from this function.
    """
    if type(byte_count) is not int or byte_count < 0:
        return BudgetObservation("MEASUREMENT_UNVERIFIABLE", None,
                                 MAX_S_DOC_BYTES_PROVISIONAL)
    if byte_count > MAX_S_DOC_BYTES_PROVISIONAL:
        return BudgetObservation("BLOCKED_RESOURCE_POLICY_UNFROZEN", byte_count,
                                 MAX_S_DOC_BYTES_PROVISIONAL)
    return BudgetObservation("WITHIN_PROVISIONAL_RESOURCE_BUDGET", byte_count,
                             MAX_S_DOC_BYTES_PROVISIONAL)
