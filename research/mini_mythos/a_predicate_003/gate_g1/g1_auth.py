"""G1 execution interlock (PURE: files and hashes only; no process is ever started here).  WRITTEN, NOT RUN.

Implements the FROZEN criteria g1_criteria_v1.json (E1A-GATE-G1-CRITERIA-V1, F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001), section `authorization`.
The G1 test needs its OWN authorization file, AUTHORIZATION_E1A_GATE_G1.json (schema e1a-gate-auth-g1-1, stage "G1").  It
  * is rejected by the G0 interlock (schema e1a-gate-auth-1) and by the E1-A runner (schema e1a-auth-2) and rejects those schemas in turn: no G0 or
    E1-A authorization can be inherited as a G1 authorization, and vice versa;
  * is bound to the git head and to the hashes of the E1-A preregistration, the G0 V5 criteria / preregistration text / code, the bench code, the G1
    criteria / preregistration text / code, and the G0 REAL-001 closure marker (the G0 reference run must exist, be closed and have verdict PASS);
  * grants exactly one run of the four tests (T1_ABORT, T2_EOF, T3_INVALID_BYTE, T4_TIMEOUT), four forks, ZERO signals, no fault injection, one
    concurrent child, at most 30 s;
  * is single-use: the run writes a consumption marker before its first fork and refuses to start when the marker already exists.
No function of this module writes an authorization file; template() is deliberately NOT valid.  This stage creates NO authorization file."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, os.path.join(A003, "gate_g0"))
import common as C  # noqa: E402
import g0_auth as GA  # noqa: E402

AUTH_SCHEMA = "e1a-gate-auth-g1-1"
STAGE = "G1"
AUTH_DEFAULT = os.path.join(A003, "AUTHORIZATION_E1A_GATE_G1.json")
EVIDENCE_ROOT = GA.EVIDENCE_ROOT
CONSUMED_DIR = os.path.join(EVIDENCE_ROOT, "_g1_consumed")
CRITERIA_FILE = "g1_criteria_v1.json"
PREREG_MD_FILE = "E1A_GATE_G1_PREREG.md"
CRITERIA_PATH = os.path.join(HERE, CRITERIA_FILE)
PREREG_MD_PATH = os.path.join(HERE, PREREG_MD_FILE)
CRITERIA_ID = "E1A-GATE-G1-CRITERIA-V1"
G1_CODE_FILES = ("g1_auth.py", "g1_judge.py", "g1_run.py", CRITERIA_FILE)
# The frozen bytes (SHA-256) of the G1 criteria and preregistration text (frozen by their own commit, before any G1 code).
FROZEN_G1_CRITERIA_SHA256 = "1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257"
FROZEN_G1_PREREG_SHA256 = "3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69"
FROZEN_G1_FILES = {CRITERIA_FILE: FROZEN_G1_CRITERIA_SHA256, PREREG_MD_FILE: FROZEN_G1_PREREG_SHA256}
ID_RE = GA.ID_RE
BINDING_KEYS = ("git_head", "prereg_sha256", "g0_criteria_sha256", "g0_prereg_sha256", "bench_code_sha256", "g0_code_sha256", "g1_criteria_sha256",
                "g1_prereg_sha256", "g1_code_sha256", "g0_reference_sha256")
TESTS = ("T1_ABORT", "T2_EOF", "T3_INVALID_BYTE", "T4_TIMEOUT")
REQUIRED_GRANTS = {"runs": 1, "tests": list(TESTS), "forks": 4, "signals": 0, "fault_injection": False, "max_concurrent_children": 1, "max_seconds": 30}
ALLOWED_KEYS = {"schema", "stage", "authorized_by", "authorization_id", "date", "expires_utc", "bindings", "grants", "not_granted"}
MUST_NOT_GRANT = ("G0", "G2", "G3", "BV", "E1A-CELLS", "E1-B", "E1-C", "E1-D", "E2", "E3")
# The G0 REAL-001 run that must be present, closed and PASS (criteria: authorization.g0_reference).
G0_REFERENCE = {"run_id": "g0_20261027_144311_479c54", "closed_sha256": "de96e1be2faf831bbe5c9e14a09deae9efdad0bb2234350d3942bc796e309736",
                "evidence_sha256": "11a8d36dfdf60678a2b5d9a8b53be1b9f8587710d643158b86f3f58371ed33bb",
                "summary_sha256": "e54cc1225dd87a36cc951b4d2a831d3792a55ae7d96bcbeb95fad92bd3367032", "verdict": "PASS"}


class G1AuthorizationError(Exception):
    pass


def g1_code_hash():
    parts = []
    for f in G1_CODE_FILES:
        parts.append("%s:%s" % (f, C.sha256_file(os.path.join(HERE, f))))
    return C.sha256_bytes("\n".join(parts).encode())


def frozen_problems(base_dir=None, g0_dir=None):
    """-> list of problems (empty = the G1 frozen files and every frozen G0 V1..V5 file have exactly their frozen bytes).  Reads files only."""
    base = base_dir or HERE
    bad = []
    for name, want in sorted(FROZEN_G1_FILES.items()):
        try:
            got = C.sha256_file(os.path.join(base, name))
        except OSError as e:
            bad.append("%s: unreadable (%r)" % (name, e))
            continue
        if got != want:
            bad.append("%s: sha256 %s != frozen %s" % (name, got, want))
    return bad + GA.frozen_problems(g0_dir)


def g0_reference_status(evidence_root=None):
    """Read-only verification of the G0 REAL-001 reference run.  -> {ok, problems, run_id, closed_sha256}.  Never raises."""
    root = evidence_root or EVIDENCE_ROOT
    ref = G0_REFERENCE
    d = os.path.join(root, ref["run_id"])
    problems = []
    out = {"ok": False, "problems": problems, "run_id": ref["run_id"], "closed_sha256": None}
    got = {}
    for key, name in (("closed_sha256", "g0_closed.json"), ("evidence_sha256", "g0_evidence.json"), ("summary_sha256", "g0_summary.json")):
        p = os.path.join(d, name)
        try:
            if os.path.islink(p) or not os.path.isfile(p):
                problems.append("%s is not a regular file" % name)
                continue
            got[key] = C.sha256_file(p)
        except OSError as e:
            problems.append("%s unreadable: %r" % (name, e))
            continue
        if got[key] != ref[key]:
            problems.append("%s sha256 %s != reference %s" % (name, got[key], ref[key]))
    out["closed_sha256"] = got.get("closed_sha256")
    if "closed_sha256" in got and got["closed_sha256"] == ref["closed_sha256"]:
        try:
            with open(os.path.join(d, "g0_closed.json"), "rb") as f:
                marker = json.loads(f.read().decode("utf-8"))
            if not (isinstance(marker, dict) and marker.get("recorded_verdict") == ref["verdict"] and marker.get("recorded_exit_code") == 0
                    and marker.get("run_id") == ref["run_id"] and marker.get("evidence_sha256") == ref["evidence_sha256"]
                    and marker.get("summary_sha256") == ref["summary_sha256"]):
                problems.append("g0_closed.json does not record run %s with verdict PASS bound to the reference hashes" % ref["run_id"])
        except (OSError, ValueError) as e:
            problems.append("g0_closed.json unparsable: %r" % (e,))
    out["ok"] = not problems
    return out


def current_bindings(git_head, prereg_sha256, bench_code_sha256, evidence_root=None):
    """The values an authorization must name.  git_head / prereg / bench hash are passed in (computed by the caller)."""
    b = dict(GA.current_bindings(git_head, prereg_sha256, bench_code_sha256))
    b["g1_criteria_sha256"] = C.sha256_file(CRITERIA_PATH)
    b["g1_prereg_sha256"] = C.sha256_file(PREREG_MD_PATH)
    b["g1_code_sha256"] = g1_code_hash()
    ref = g0_reference_status(evidence_root)
    b["g0_reference_sha256"] = ref["closed_sha256"] or "UNREADABLE"
    return b


def validate(auth, current, now_utc_iso):
    """-> list of problems (empty = valid).  PURE."""
    if not isinstance(auth, dict):
        return ["authorization is not a JSON object"]
    bad = []
    extra = sorted(set(auth) - ALLOWED_KEYS)
    if extra:
        bad.append("unknown keys %s (a G1 authorization is a closed schema)" % extra)
    if auth.get("schema") != AUTH_SCHEMA:
        bad.append("schema must be %s (a G0 e1a-gate-auth-1 or E1-A e1a-auth-2 authorization is NOT a G1 authorization)" % AUTH_SCHEMA)
    if auth.get("stage") != STAGE:
        bad.append("stage must be exactly %r (G0/G2/G3/BV/E1-A are not granted by this file)" % STAGE)
    if auth.get("authorized_by") != "owner":
        bad.append("authorized_by must be owner")
    aid = auth.get("authorization_id")
    if not isinstance(aid, str) or not ID_RE.match(aid):
        bad.append("authorization_id missing or not a plain identifier")
    b = auth.get("bindings")
    if not isinstance(b, dict):
        bad.append("bindings missing")
    else:
        for k in BINDING_KEYS:
            if b.get(k) != current.get(k) or not isinstance(b.get(k), str) or not b.get(k):
                bad.append("binding %s differs from the current value" % k)
        if b.get("g1_criteria_sha256") != FROZEN_G1_CRITERIA_SHA256:
            bad.append("binding g1_criteria_sha256 is not the frozen G1 criteria hash")
        if b.get("g1_prereg_sha256") != FROZEN_G1_PREREG_SHA256:
            bad.append("binding g1_prereg_sha256 is not the frozen G1 preregistration-text hash")
        if b.get("g0_criteria_sha256") != GA.FROZEN_CRITERIA_SHA256:
            bad.append("binding g0_criteria_sha256 is not the frozen G0 V5 criteria hash")
        if b.get("g0_prereg_sha256") != GA.FROZEN_PREREG_SHA256:
            bad.append("binding g0_prereg_sha256 is not the frozen G0 V5 preregistration-text hash")
        if b.get("g0_reference_sha256") != G0_REFERENCE["closed_sha256"]:
            bad.append("binding g0_reference_sha256 is not the G0 REAL-001 closure marker hash")
        if set(b) - set(BINDING_KEYS):
            bad.append("unknown binding keys %s" % sorted(set(b) - set(BINDING_KEYS)))
    g = auth.get("grants")
    if g != REQUIRED_GRANTS:
        bad.append("grants must be exactly %s (got %r)" % (REQUIRED_GRANTS, g))
    ng = auth.get("not_granted")
    if not isinstance(ng, list) or not set(MUST_NOT_GRANT) <= set(ng):
        bad.append("not_granted must list %s" % (MUST_NOT_GRANT,))
    exp = auth.get("expires_utc")
    if not isinstance(exp, str) or exp <= now_utc_iso:
        bad.append("authorization expired, or expires_utc missing / malformed (it is required)")
    return bad


def consumed_marker(authorization_id, consumed_dir=None):
    return os.path.join(consumed_dir or CONSUMED_DIR, "%s.json" % authorization_id)


def load(path, current, now_utc_iso, consumed_dir=None):
    """-> (auth dict, raw bytes).  Raises G1AuthorizationError.  Refuses an already consumed authorization."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        auth = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as e:
        raise G1AuthorizationError("no valid G1 authorization file at %s (%r)" % (path, e))
    bad = validate(auth, current, now_utc_iso)
    if bad:
        raise G1AuthorizationError("; ".join(bad))
    if os.path.exists(consumed_marker(auth["authorization_id"], consumed_dir)):
        raise G1AuthorizationError("authorization %s was already consumed (single use)" % auth["authorization_id"])
    return auth, raw


def template():
    """Text of a NON-VALID template (schema deliberately wrong) for the owner to adapt; the real file is created only by the owner."""
    return json.dumps({"schema": "TEMPLATE-NOT-VALID-" + AUTH_SCHEMA, "stage": STAGE, "authorized_by": "owner", "authorization_id": "OWNER-CHOOSES-ID",
                       "date": "YYYY-MM-DD", "expires_utc": "YYYY-MM-DDTHH:MM:SSZ", "bindings": {k: "FILL-FROM `g1_run.py --check`" for k in BINDING_KEYS},
                       "grants": REQUIRED_GRANTS, "not_granted": list(MUST_NOT_GRANT)}, indent=1)


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()
