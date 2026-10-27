"""G0 execution interlock (PURE: files and hashes only; no process is ever started here).  WRITTEN, NOT RUN.

The G0 test needs its OWN authorization file, AUTHORIZATION_E1A_GATE_G0.json (schema e1a-gate-auth-1, stage "G0").  It
  * is rejected by the E1-A runner (that one only accepts schema e1a-auth-2) and rejects that schema in turn, so a G0 authorization can
    never be inherited as a G1/G2/G3/BV/E1-A authorization (and vice versa);
  * is bound to the git head and to the hashes of the E1-A preregistration, the G0 criteria, the G0 preregistration text, the bench code
    and the G0 code, so any change after review invalidates it;
  * grants exactly one run, one fork, ZERO signals, no fault injection, one concurrent child, at most 20 s;
  * is single-use: the run writes a consumption marker before it forks, and refuses to start when the marker already exists.
This round creates NO valid authorization file."""
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
CRITERIA_PATH = os.path.join(HERE, "g0_criteria_v1.json")
PREREG_MD_PATH = os.path.join(HERE, "E1A_GATE_G0_PREREG.md")
G0_CODE_FILES = ("g0_auth.py", "g0_judge.py", "g0_run.py", "g0_criteria_v1.json")
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
