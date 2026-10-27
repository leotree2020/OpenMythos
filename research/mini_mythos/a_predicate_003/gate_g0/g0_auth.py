"""G0 execution interlock (PURE: files and hashes only; no process is ever started here).  WRITTEN, NOT RUN.

Implements the FROZEN criteria g0_criteria_v5.json (E1A-GATE-G0-CRITERIA-V5, F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001).
The G0 test needs its OWN authorization file, AUTHORIZATION_E1A_GATE_G0.json (schema e1a-gate-auth-1, stage "G0").  It
  * is rejected by the E1-A runner (that one only accepts schema e1a-auth-2) and rejects that schema in turn, so a G0 authorization can
    never be inherited as a G1/G2/G3/BV/E1-A authorization (and vice versa);
  * is bound to the git head and to the hashes of the E1-A preregistration, the G0 criteria, the G0 preregistration text, the bench code
    and the G0 code, so any change after review invalidates it;
  * must name the FROZEN V5 criteria hash and the FROZEN V5 preregistration-text hash: an authorization bound to the V1, V2, V3 or V4 files is
    void for this code (version isolation, CL-08).  NOTE on the frozen text of G0-C02: it still says "bound to THIS criteria file (V2)".  That
    parenthesis is a historical wording error that V5 keeps unchanged (frozen); the binding that is actually required and checked is the V5 hash;
  * grants exactly one run, one fork, ZERO signals, no fault injection, one concurrent child, at most 20 s;
  * is single-use: the run writes a consumption marker before it forks, and refuses to start when the marker already exists.
No function of this module writes an authorization file; template() is deliberately NOT valid.  This round creates NO valid authorization file."""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A003, "bench"))
import common as C  # noqa: E402

AUTH_SCHEMA = "e1a-gate-auth-1"
STAGE = "G0"
AUTH_DEFAULT = os.path.join(A003, "AUTHORIZATION_E1A_GATE_G0.json")
EVIDENCE_ROOT = os.path.join(A003, "evidence")
CONSUMED_DIR = os.path.join(EVIDENCE_ROOT, "_g0_consumed")
CRITERIA_FILE = "g0_criteria_v5.json"
PREREG_MD_FILE = "E1A_GATE_G0_PREREG_V5.md"
CRITERIA_PATH = os.path.join(HERE, CRITERIA_FILE)
PREREG_MD_PATH = os.path.join(HERE, PREREG_MD_FILE)
CRITERIA_ID = "E1A-GATE-G0-CRITERIA-V5"
G0_CODE_FILES = ("g0_auth.py", "g0_judge.py", "g0_run.py", CRITERIA_FILE)
# The frozen bytes (SHA-256).  V5 is the only criteria version this code implements; V1..V4 are listed so that they can be verified unchanged
# and so that an authorization bound to any of them is recognisably void.
FROZEN_CRITERIA_SHA256 = "d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821"
FROZEN_PREREG_SHA256 = "8338f4a0e20e37ad791d35eb876aca23f3e86e6f16fa9e2d84fd4ac82ef6e25c"
FROZEN_FILES = {
    "g0_criteria_v1.json": "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2",
    "E1A_GATE_G0_PREREG.md": "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb",
    "g0_criteria_v2.json": "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438",
    "E1A_GATE_G0_PREREG_V2.md": "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2",
    "g0_criteria_v3.json": "653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a",
    "E1A_GATE_G0_PREREG_V3.md": "0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88",
    "g0_criteria_v4.json": "6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414",
    "E1A_GATE_G0_PREREG_V4.md": "05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42",
    CRITERIA_FILE: FROZEN_CRITERIA_SHA256,
    PREREG_MD_FILE: FROZEN_PREREG_SHA256,
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")
BINDING_KEYS = ("git_head", "prereg_sha256", "g0_criteria_sha256", "g0_prereg_sha256", "bench_code_sha256", "g0_code_sha256")
REQUIRED_GRANTS = {"runs": 1, "forks": 1, "signals": 0, "fault_injection": False, "max_concurrent_children": 1, "max_seconds": 20}
ALLOWED_KEYS = {"schema", "stage", "authorized_by", "authorization_id", "date", "expires_utc", "bindings", "grants", "not_granted"}
MUST_NOT_GRANT = ("G1", "G2", "G3", "BV", "E1A-CELLS", "E1-B", "E1-C", "E1-D", "E2", "E3")


class G0AuthorizationError(Exception):
    pass


def g0_code_hash():
    parts = []
    for f in G0_CODE_FILES:
        parts.append("%s:%s" % (f, C.sha256_file(os.path.join(HERE, f))))
    return C.sha256_bytes("\n".join(parts).encode())


def frozen_problems(base_dir=None):
    """-> list of problems (empty = every frozen V1..V5 file in gate_g0 has exactly its frozen bytes).  Reads files only."""
    base = base_dir or HERE
    bad = []
    for name, want in sorted(FROZEN_FILES.items()):
        try:
            got = C.sha256_file(os.path.join(base, name))
        except OSError as e:
            bad.append("%s: unreadable (%r)" % (name, e))
            continue
        if got != want:
            bad.append("%s: sha256 %s != frozen %s" % (name, got, want))
    return bad


def current_bindings(git_head, prereg_sha256, bench_code_sha256):
    """The values an authorization must name.  git_head / prereg / bench hash are passed in (computed by the caller) so that this module
    stays free of the heavier runner imports."""
    return {"git_head": git_head, "prereg_sha256": prereg_sha256, "g0_criteria_sha256": C.sha256_file(CRITERIA_PATH),
            "g0_prereg_sha256": C.sha256_file(PREREG_MD_PATH), "bench_code_sha256": bench_code_sha256, "g0_code_sha256": g0_code_hash()}


def validate(auth, current, now_utc_iso):
    """-> list of problems (empty = valid).  PURE."""
    if not isinstance(auth, dict):
        return ["authorization is not a JSON object"]
    bad = []
    extra = sorted(set(auth) - ALLOWED_KEYS)
    if extra:
        bad.append("unknown keys %s (a G0 authorization is a closed schema)" % extra)
    if auth.get("schema") != AUTH_SCHEMA:
        bad.append("schema must be %s (an e1a-auth-2 authorization is NOT a G0 authorization)" % AUTH_SCHEMA)
    if auth.get("stage") != STAGE:
        bad.append("stage must be exactly %r (G1/G2/G3/BV/E1-A are not granted by this file)" % STAGE)
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
        # version isolation (CL-08): only the frozen V5 files can be authorized; V1..V4 bindings are void for this code
        if b.get("g0_criteria_sha256") != FROZEN_CRITERIA_SHA256:
            bad.append("binding g0_criteria_sha256 is not the frozen V5 criteria hash (an authorization bound to V1..V4 is void)")
        if b.get("g0_prereg_sha256") != FROZEN_PREREG_SHA256:
            bad.append("binding g0_prereg_sha256 is not the frozen V5 preregistration-text hash (an authorization bound to V1..V4 is void)")
        if set(b) - set(BINDING_KEYS):
            bad.append("unknown binding keys %s" % sorted(set(b) - set(BINDING_KEYS)))
    g = auth.get("grants")
    if g != REQUIRED_GRANTS:
        bad.append("grants must be exactly %s (got %r)" % (REQUIRED_GRANTS, g))
    ng = auth.get("not_granted")
    if not isinstance(ng, list) or not set(MUST_NOT_GRANT) <= set(ng):
        bad.append("not_granted must list %s" % (MUST_NOT_GRANT,))
    exp = auth.get("expires_utc")
    if exp is not None and (not isinstance(exp, str) or exp <= now_utc_iso):
        bad.append("authorization expired or expires_utc malformed")
    return bad


def consumed_marker(authorization_id, consumed_dir=None):
    return os.path.join(consumed_dir or CONSUMED_DIR, "%s.json" % authorization_id)


def load(path, current, now_utc_iso, consumed_dir=None):
    """-> (auth dict, raw bytes).  Raises G0AuthorizationError.  Refuses an already consumed authorization."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        auth = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as e:
        raise G0AuthorizationError("no valid G0 authorization file at %s (%r)" % (path, e))
    bad = validate(auth, current, now_utc_iso)
    if bad:
        raise G0AuthorizationError("; ".join(bad))
    if os.path.exists(consumed_marker(auth["authorization_id"], consumed_dir)):
        raise G0AuthorizationError("authorization %s was already consumed (single use)" % auth["authorization_id"])
    return auth, raw


def template():
    """Text of a NON-VALID template (schema deliberately wrong) for the owner to adapt; the real file is created only by the owner."""
    return json.dumps({"schema": "TEMPLATE-NOT-VALID-" + AUTH_SCHEMA, "stage": STAGE, "authorized_by": "owner", "authorization_id": "OWNER-CHOOSES-ID",
                       "date": "YYYY-MM-DD", "expires_utc": "YYYY-MM-DDTHH:MM:SSZ", "bindings": {k: "FILL-FROM `g0_run.py --check`" for k in BINDING_KEYS},
                       "grants": REQUIRED_GRANTS, "not_granted": list(MUST_NOT_GRANT)}, indent=1)
