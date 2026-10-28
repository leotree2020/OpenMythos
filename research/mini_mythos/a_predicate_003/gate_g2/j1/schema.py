"""J1 input schema: closed whitelist, strict types, harness-bound trust map, answer-firewall (Lane S only).  NOT TESTED / NEVER EXECUTED.

Lane S (what J1 may see)   : assertion_id, a list of synthetic B0-shaped observation records, a harness-validated trust map.
Lane O (what J1 must never see): fixture id, canonical card, expected verdicts, behaviour labels, oracle truth, paths, grades.  Any field name or
string value that looks like Lane O material is rejected here, BEFORE any judging, and the rejection is a BLOCKED input, never a verdict about
the subject.  Diagnostics never echo input values (only field positions and rule codes).

Strictness: `bool` is never an `int`; floats and non-JSON types are rejected; unknown keys are rejected; a record is never silently dropped.
Pure module: stdlib only (re, dataclasses); no I/O, no clock, no /proc, no Bench import.
"""
import re
from dataclasses import dataclass

# ---------------------------------------------------------------- scope labels (mandatory in every report)
MEASUREMENT_TARGET = "J1_SYNTHETIC_DETECTOR"
# Correction 001 (J1-IMPL-F05 / F06): J1 accepts HAND-AUTHORED SYNTHETIC B0-SHAPED input only.  The trust map is a hypothetical contract declared by an
# EXTERNAL harness; J1 cannot authenticate it, and nothing here is kernel identity or an authenticated sender.  A native-to-J1 adapter (original bytes,
# digests, sequence, missing / torn status, float timestamps, independent custody) is an OPEN question and is NOT IMPLEMENTED; direct compatibility with
# native bench/registry.py records is NOT SUPPORTED (they carry float mono / wall and extra keys that the closed schema rejects).
INPUT_DOMAIN = "HAND_AUTHORED_SYNTHETIC_B0_SHAPED_ONLY"
NATIVE_B0_ADAPTER_STATUS = "NOT_IMPLEMENTED_OPEN_QUESTION"
TRUST_BASIS = "HYPOTHETICAL_HARNESS_DECLARED_UNAUTHENTICATED"
NATIVE_B0_SAFETY_STATUS = "NOT_EVALUATED_BY_J1"
SCOPE = "SYNTHETIC_CPU_ONLY"

PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"
VERDICTS = (PASS, FAIL, BLOCKED)

# ---------------------------------------------------------------- assertions (V0.1: 5 discriminative + 4 SMOKE_ONLY)
EVIDENCE_SENSITIVE = ("ATTRIBUTION", "UNIQUE_REGISTRY", "ZOMBIE_AT_T", "LOG_MATCHES_SEAL", "WRITE_COMPLETE")
SMOKE_ONLY = ("PREVENT_PROOF", "LAWFUL_REAP", "EVIDENCE_USABLE", "DELIVERY")
ASSERTION_IDS = EVIDENCE_SENSITIVE + SMOKE_ONLY

# ---------------------------------------------------------------- event kinds
# Native registry kinds, copied by value from the frozen bench/registry.py::KINDS (J1 never imports the Bench).  CREATED / EXIT / REAPED are NOT
# native registry kinds and are deliberately absent.
B0_KINDS = ("RUN_START", "INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD", "RUN_END")
SIM_KINDS = ("NODE_CLAIM", "KERNEL_SNAPSHOT", "GATE_CHILD_OBSERVATION", "R_WRITE_RESULT", "SEAL_MANIFEST", "LOG_READBACK")
EVENT_KINDS = B0_KINDS + SIM_KINDS

# ---------------------------------------------------------------- source roles (harness-assigned; never self-declared by a record)
ROLE_B0_LEDGER = "B0_LEDGER"
ROLE_NODE_CLAIM = "NODE_CLAIM_SIM"
ROLE_KERNEL_SNAPSHOT = "KERNEL_SNAPSHOT_SIM"
ROLE_G2_WITNESS = "G2_WITNESS_SIM"
ROLE_G2_WRAP = "G2_WRAP_SIM"
ROLE_SEAL_MANIFEST = "SEAL_MANIFEST_SIM"
ROLE_SUBJECT_LOG = "SUBJECT_LOG_READBACK"        # implementer addition (open question OQ-3): the artefact under judgement, never an authority

# Ceiling of event kinds per role: a harness trust map can only NARROW this, never widen it (a claim cannot self-upgrade authority).
ROLE_CEILING = {
    ROLE_B0_LEDGER: frozenset(B0_KINDS),
    ROLE_NODE_CLAIM: frozenset({"NODE_CLAIM"}),
    ROLE_KERNEL_SNAPSHOT: frozenset({"KERNEL_SNAPSHOT"}),
    ROLE_G2_WITNESS: frozenset({"GATE_CHILD_OBSERVATION"}),
    ROLE_G2_WRAP: frozenset({"R_WRITE_RESULT"}),
    ROLE_SEAL_MANIFEST: frozenset({"SEAL_MANIFEST"}),
    ROLE_SUBJECT_LOG: frozenset({"LOG_READBACK"}),
}
# Roles that can ever carry authority.  NODE_CLAIM_SIM and SUBJECT_LOG_READBACK never do.
AUTHORITY_ROLES = frozenset({ROLE_B0_LEDGER, ROLE_KERNEL_SNAPSHOT, ROLE_G2_WITNESS, ROLE_G2_WRAP, ROLE_SEAL_MANIFEST})
# Every source in this stage is synthetic: the four hypothetical sensors, the untrusted claim source, the hand-authored B0-SHAPED ledger and the subject
# log.  None is real B0 evidence and none is authenticated by J1; the harness declares them (J1-IMPL-F05).
SYNTHETIC_ONLY_ROLES = frozenset({ROLE_B0_LEDGER, ROLE_NODE_CLAIM, ROLE_KERNEL_SNAPSHOT, ROLE_G2_WITNESS, ROLE_G2_WRAP, ROLE_SEAL_MANIFEST,
                                  ROLE_SUBJECT_LOG})          # every source is synthetic in this stage, the B0-shaped ledger and the subject log included
ROLE_TIER = {
    ROLE_B0_LEDGER: "SYNTHETIC_B0_SHAPED_TRANSCRIPT",
    ROLE_NODE_CLAIM: "UNTRUSTED_CLAIM",
    ROLE_KERNEL_SNAPSHOT: "SYNTHETIC_ASSUMPTION",
    ROLE_G2_WITNESS: "SYNTHETIC_ASSUMPTION",
    ROLE_G2_WRAP: "SYNTHETIC_ASSUMPTION",
    ROLE_SEAL_MANIFEST: "SYNTHETIC_ASSUMPTION",
    ROLE_SUBJECT_LOG: "SUBJECT_ARTIFACT",
}

READ_STATUSES = ("OK", "TORN_TAIL", "CORRUPT", "MISSING", "UNREADABLE")
CLAIM_KINDS = ("GATE_CHILD_IDENTITY", "R_WRITTEN", "READY", "WAIT_RESULT", "OTHER")
PROC_STATES = frozenset("RSDZTtXxKWPI")

MAX_EVENTS = 2000
MAX_LOG_CHARS = 1000000
MAX_TRUST_ENTRIES = 64
MAX_DEPTH = 8

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ERRNO_RE = re.compile(r"^E[A-Z0-9]{2,15}$")
# Lane O leak guard.  Matches the SHAPE of fixture identifiers only; it holds no answer, no mapping and no expected verdict.
_LEAK_VALUE_RE = re.compile(r"j1[-_ ]?f\d", re.IGNORECASE)
# Normalised (lower-case alphanumerics only) substrings that mark a field NAME as Lane O material.
_FORBIDDEN_NAME_PARTS = ("fixture", "oracle", "expected", "canonicalcard", "behaviorlabel", "behaviourlabel", "acceptance", "isattack", "caseid",
                         "filename", "filepath", "inputdigest", "actualgate", "truthmodel", "grade", "score", "teststatus", "runstage",
                         "ownerdecision", "groundtruth")


class InputInvalid(Exception):
    """The Lane S input is malformed or contains Lane O material.  `problems` holds rule codes and positions, never input values."""

    def __init__(self, problems):
        Exception.__init__(self, "; ".join(problems[:10]))
        self.problems = list(problems)


# ---------------------------------------------------------------- normalised, immutable views
@dataclass(frozen=True)
class Identity:
    pid: int
    starttime: int
    ppid: object        # int or None
    boot_id: object     # str or None
    pidns: object       # str or None

    def same_instance(self, other):
        """Same process instance: pid and starttime equal; boot_id / pidns are compared only when BOTH sides carry them."""
        if self.pid != other.pid or self.starttime != other.starttime:
            return False
        if self.boot_id is not None and other.boot_id is not None and self.boot_id != other.boot_id:
            return False
        if self.pidns is not None and other.pidns is not None and self.pidns != other.pidns:
            return False
        return True


@dataclass(frozen=True)
class Event:
    source_handle: str
    event_kind: str
    order: int
    node_token: object      # str or None
    identity: object        # Identity or None
    gate_token: object      # str or None
    raw: dict
    read_status: str

    @property
    def ref(self):
        return "%s#%d" % (self.source_handle, self.order)


@dataclass(frozen=True)
class TrustEntry:
    role: str
    synthetic_assumption: bool
    allowed_event_kinds: frozenset
    provenance_tier: str

    @property
    def authority(self):
        return self.role in AUTHORITY_ROLES


# ---------------------------------------------------------------- primitive checks (bool is never an int)
def _is_int(v):
    return type(v) is int


def _is_str(v):
    return type(v) is str


def _token_ok(v):
    return type(v) is str and _TOKEN_RE.match(v) is not None


def _v_nonneg_int(v):
    return _is_int(v) and v >= 0


def _v_pid(v):
    """A source-reported process id: a non-bool integer >= 1 (None, 0, negatives, bools and strings are all invalid when the key is present)."""
    return _is_int(v) and v >= 1


def _v_bool(v):
    return type(v) is bool


def _v_str(v):
    return type(v) is str and len(v) <= 256


def _v_str_or_none(v):
    return v is None or _v_str(v)


def _v_hex64(v):
    return type(v) is str and _HEX64_RE.match(v) is not None


def _v_state(v):
    return type(v) is str and len(v) == 1 and v in PROC_STATES


def _v_claim_kind(v):
    return type(v) is str and v in CLAIM_KINDS


def _v_byte_r(v):
    return type(v) is str and v == "R"


def _v_errno(v):
    return v is None or (type(v) is str and _ERRNO_RE.match(v) is not None)


def _v_log(v):
    if type(v) is not str or len(v) > MAX_LOG_CHARS:
        return False
    try:
        v.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


# kind -> (required raw fields, optional raw fields); value = validator.  Unknown raw keys are rejected (closed schema).
_RAW_SCHEMA = {
    "RUN_START": ({}, {"run_id": _v_str, "observer_pid": _v_nonneg_int}),
    "INTENT": ({}, {"role": _v_str, "label": _v_str, "creator": _v_str, "creator_pid": _v_nonneg_int, "mode": _v_str_or_none}),
    # J1-FIX2-REVIEW-F05: `pid` is the normalised synthetic projection of the native FORKED record's source-reported pid (bench/observer.py::_note_forked
    # writes pid=<fork pid>; bench/registry.py::integrity_issues rejects a non-integer one as MALFORMED_FORKED).  It is OPTIONAL in the schema on purpose:
    # an ABSENT pid is a well-formed input with missing evidence (judge: subject BLOCKED), whereas a PRESENT but invalid pid is a malformed input
    # (INPUT_INVALID).  The native FORKED starttime may legitimately be None (unreadable /proc), so no FORKED starttime is required here.
    "FORKED": ({}, {"role": _v_str, "label": _v_str, "creator": _v_str, "creator_pid": _v_nonneg_int, "pid": _v_pid}),
    "REGISTERED": ({}, {"role": _v_str, "label": _v_str, "creator": _v_str, "creator_pid": _v_nonneg_int, "sid": _v_nonneg_int,
                        "pgrp": _v_nonneg_int}),
    "RELEASED": ({}, {}),
    "ABORTED": ({}, {"reason": _v_str, "creation_unresolved": _v_bool}),
    "DEAD": ({}, {"basis": _v_str}),
    "RUN_END": ({}, {"run_id": _v_str, "cleanup_confirmed": _v_bool}),
    "NODE_CLAIM": ({"claim_kind": _v_claim_kind}, {"pid": _v_nonneg_int, "starttime": _v_nonneg_int}),
    "KERNEL_SNAPSHOT": ({"state": _v_state}, {}),
    "GATE_CHILD_OBSERVATION": ({}, {}),
    "R_WRITE_RESULT": ({"bytes": _v_nonneg_int, "errno": _v_errno}, {"byte": _v_byte_r}),
    "SEAL_MANIFEST": ({"full_file_sha256": _v_hex64, "byte_length": _v_nonneg_int, "final_seq": _v_nonneg_int, "last_digest": _v_hex64,
                       "run_id": _v_str}, {}),
    "LOG_READBACK": ({"log_utf8": _v_log, "run_id": _v_str}, {}),
}

# kind -> (node_token requirement, identity requirement): "req" required, "opt" optional, "none" must be absent.
_SEMANTICS = {
    "RUN_START": ("none", "none"),
    "RUN_END": ("none", "none"),
    "INTENT": ("req", "none"),
    "FORKED": ("req", "opt"),
    "REGISTERED": ("req", "req"),
    "RELEASED": ("req", "none"),
    "ABORTED": ("req", "none"),
    "DEAD": ("req", "none"),
    "NODE_CLAIM": ("opt", "none"),
    "KERNEL_SNAPSHOT": ("opt", "req"),
    "GATE_CHILD_OBSERVATION": ("req", "req"),
    "R_WRITE_RESULT": ("req", "none"),
    "SEAL_MANIFEST": ("none", "none"),
    "LOG_READBACK": ("none", "none"),
}

_EVENT_REQUIRED_KEYS = frozenset({"source_handle", "event_kind", "monotonic_order", "read_status"})
_EVENT_ALLOWED_KEYS = _EVENT_REQUIRED_KEYS | frozenset({"node_token", "identity", "gate_token", "raw_fields"})
_IDENTITY_ALLOWED_KEYS = frozenset({"pid", "starttime", "ppid", "boot_id", "pidns"})
_TRUST_KEYS = frozenset({"role", "synthetic_assumption", "allowed_event_kinds", "provenance_tier"})


# ---------------------------------------------------------------- answer firewall
def _norm_key(k):
    return "".join(ch for ch in k.lower() if ch.isalnum())


def _scan(obj, where, problems, depth):
    """Recursive scan for Lane O material and non-JSON types.  Field NAMES are never echoed; positions are."""
    if depth > MAX_DEPTH:
        problems.append("%s: nesting too deep" % where)
        return
    if isinstance(obj, dict):
        for i, (k, v) in enumerate(obj.items()):
            if type(k) is not str:
                problems.append("%s: non-string key" % where)
                continue
            nk = _norm_key(k)
            for part in _FORBIDDEN_NAME_PARTS:
                if part in nk:
                    problems.append("%s.<key %d>: forbidden Lane O field name" % (where, i))
                    break
            _scan(v, "%s.<%d>" % (where, i), problems, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _scan(v, "%s[%d]" % (where, i), problems, depth + 1)
    elif type(obj) is str:
        if _LEAK_VALUE_RE.search(obj) is not None:
            problems.append("%s: string value resembles a Lane O fixture identifier" % where)
    elif obj is None or type(obj) is bool or type(obj) is int:
        return
    else:
        problems.append("%s: type %s is not allowed (JSON-like int/str/bool/None/list/dict only)" % (where, type(obj).__name__))


# ---------------------------------------------------------------- trust map
def validate_trust_model(trust_model):
    """-> (dict handle -> TrustEntry, problems).  The harness MUST call this (or judge.evaluate does) BEFORE any judging.
    The map is the only place where authority is granted; a record cannot grant itself authority.
    LIMIT (J1-IMPL-F05): this function checks the SHAPE of a caller-supplied map; it cannot authenticate who supplied it.  A caller that controls both
    the map and the records can label its own record with any role.  The map is therefore an explicitly hypothetical contract declared by an EXTERNAL
    harness (TRUST_BASIS); a role string or synthetic_assumption=True is never kernel identity or an authenticated sender, and any PASS built on it is
    limited to that declared assumption.  The harness's origin and seal rules are an unresolved prerequisite of any formal acceptance."""
    problems = []
    out = {}
    if type(trust_model) is not dict:
        return out, ["trust_model: must be a dict"]
    if len(trust_model) > MAX_TRUST_ENTRIES:
        return out, ["trust_model: too many entries"]
    for hi, (handle, entry) in enumerate(trust_model.items()):
        where = "trust_model.<%d>" % hi
        if not _token_ok(handle):
            problems.append("%s: source handle is not a plain token" % where)
            continue
        if type(entry) is not dict:
            problems.append("%s: entry must be a dict" % where)
            continue
        extra = set(entry) - _TRUST_KEYS
        missing = _TRUST_KEYS - set(entry)
        if extra:
            problems.append("%s: unknown trust fields" % where)
        if missing:
            problems.append("%s: missing trust fields" % where)
        if extra or missing:
            continue
        role, syn, kinds, tier = entry["role"], entry["synthetic_assumption"], entry["allowed_event_kinds"], entry["provenance_tier"]
        if type(role) is not str or role not in ROLE_CEILING:
            problems.append("%s: unknown role" % where)
            continue
        if type(syn) is not bool:
            problems.append("%s: synthetic_assumption must be a bool" % where)
            continue
        if role in SYNTHETIC_ONLY_ROLES and syn is not True:
            problems.append("%s: every source must be declared synthetic_assumption=True (synthetic-only stage)" % where)
            continue
        if type(tier) is not str or tier != ROLE_TIER[role]:
            problems.append("%s: provenance_tier does not match the role" % where)
            continue
        if not isinstance(kinds, (list, tuple)) or not all(type(k) is str for k in kinds):
            problems.append("%s: allowed_event_kinds must be a list of strings" % where)
            continue
        kset = frozenset(kinds)
        if not kset <= ROLE_CEILING[role]:
            problems.append("%s: allowed_event_kinds exceed the role ceiling" % where)
            continue
        out[handle] = TrustEntry(role, syn, kset, tier)
    return out, problems


# ---------------------------------------------------------------- one observation record
def _parse_identity(raw, where, problems):
    if raw is None:
        return None
    if type(raw) is not dict:
        problems.append("%s: identity must be a dict or absent" % where)
        return None
    if set(raw) - _IDENTITY_ALLOWED_KEYS:
        problems.append("%s: unknown identity fields" % where)
        return None
    pid, st = raw.get("pid"), raw.get("starttime")
    if not (_is_int(pid) and pid >= 1) or not (_is_int(st) and st >= 0):
        problems.append("%s: pid / starttime must be non-bool integers (pid >= 1, starttime >= 0)" % where)
        return None
    ppid = raw.get("ppid")
    if ppid is not None and not (_is_int(ppid) and ppid >= 0):
        problems.append("%s: ppid must be a non-bool integer or None" % where)
        return None
    for name in ("boot_id", "pidns"):
        v = raw.get(name)
        if v is not None and not _token_ok(v):
            problems.append("%s: %s must be a plain token or None" % (where, name))
            return None
    return Identity(pid, st, ppid, raw.get("boot_id"), raw.get("pidns"))


def _parse_event(raw, where, trust, problems):
    if type(raw) is not dict:
        problems.append("%s: record must be a dict" % where)
        return None
    if _EVENT_REQUIRED_KEYS - set(raw):
        problems.append("%s: missing required record fields" % where)
        return None
    if set(raw) - _EVENT_ALLOWED_KEYS:
        problems.append("%s: unknown record fields" % where)
        return None
    n0 = len(problems)
    handle, kind, order, status = raw["source_handle"], raw["event_kind"], raw["monotonic_order"], raw["read_status"]
    if not _token_ok(handle):
        problems.append("%s: source_handle is not a plain token" % where)
    elif handle not in trust:
        problems.append("%s: source_handle is not in the harness trust map" % where)
    if type(kind) is not str or kind not in EVENT_KINDS:
        problems.append("%s: unknown event_kind" % where)
    elif handle in trust and kind not in trust[handle].allowed_event_kinds:
        problems.append("%s: event_kind not allowed for this source" % where)
    if not (_is_int(order) and order >= 0):
        problems.append("%s: monotonic_order must be a non-bool integer >= 0" % where)
    if type(status) is not str or status not in READ_STATUSES:
        problems.append("%s: unknown read_status" % where)
    node = raw.get("node_token")
    gate = raw.get("gate_token")
    if node is not None and not _token_ok(node):
        problems.append("%s: node_token must be a plain token or absent" % where)
    if gate is not None and not _token_ok(gate):
        problems.append("%s: gate_token must be a plain token or absent" % where)
    ident = _parse_identity(raw.get("identity"), where + ".identity", problems)
    fields = raw.get("raw_fields", {})
    if type(fields) is not dict:
        problems.append("%s: raw_fields must be a dict" % where)
        fields = {}
    if len(problems) > n0:
        return None
    required, optional = _RAW_SCHEMA[kind]
    for name, check in required.items():
        if name not in fields:
            problems.append("%s: raw_fields missing a required field for this event_kind" % where)
        elif not check(fields[name]):
            problems.append("%s: raw_fields has an invalid value for a required field" % where)
    for name, value in fields.items():
        if name in required:
            continue
        if name not in optional:
            problems.append("%s: raw_fields has an unknown field for this event_kind" % where)
        elif not optional[name](value):
            problems.append("%s: raw_fields has an invalid value for an optional field" % where)
    node_req, ident_req = _SEMANTICS[kind]
    if node_req == "req" and node is None:
        problems.append("%s: node_token is required for this event_kind" % where)
    if node_req == "none" and node is not None:
        problems.append("%s: node_token must be absent for this event_kind" % where)
    if ident_req == "req" and ident is None:
        problems.append("%s: identity is required for this event_kind" % where)
    if ident_req == "none" and ident is not None:
        problems.append("%s: identity must be absent for this event_kind" % where)
    if kind == "REGISTERED" and ident is not None and ident.ppid is None:
        problems.append("%s: REGISTERED requires identity.ppid" % where)
    if len(problems) > n0:
        return None
    return Event(handle, kind, order, node, ident, gate, dict(fields), status)


# ---------------------------------------------------------------- entry point used by judge.evaluate (and available to the harness)
def validate_input(assertion_id, subject_observables, declared_trust_model):
    """-> (events: list[Event] in input order, trust: dict[str, TrustEntry]).  Raises InputInvalid with ALL problems found.
    Nothing is dropped silently: any malformed record makes the whole input invalid (judge: BLOCKED)."""
    problems = []
    if type(assertion_id) is not str or assertion_id not in ASSERTION_IDS:
        problems.append("assertion_id: not one of the nine assertion identifiers")
    if not isinstance(subject_observables, (list, tuple)):
        problems.append("subject_observables: must be a list")
        raise InputInvalid(problems)
    if len(subject_observables) > MAX_EVENTS:
        problems.append("subject_observables: too many records")
        raise InputInvalid(problems)
    _scan(subject_observables, "subject_observables", problems, 0)
    _scan(declared_trust_model, "declared_trust_model", problems, 0)
    trust, tproblems = validate_trust_model(declared_trust_model)
    problems.extend(tproblems)
    events = []
    seen = set()
    for i, raw in enumerate(subject_observables):
        ev = _parse_event(raw, "subject_observables[%d]" % i, trust, problems)
        if ev is None:
            continue
        key = (ev.source_handle, ev.order)
        if key in seen:
            problems.append("subject_observables[%d]: duplicate (source_handle, monotonic_order)" % i)
            continue
        seen.add(key)
        events.append(ev)
    if problems:
        raise InputInvalid(problems)
    return events, trust
