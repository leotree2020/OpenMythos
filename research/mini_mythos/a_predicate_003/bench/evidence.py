"""Provenance of the run-level bench-validity (BV) evidence.  PURE FILE LOGIC: no process is started here.  WRITTEN, NOT RUN.

Problem (STATIC-FIX-002-C): a JSON that says `ok: true` proves nothing.  Cell results may count only if an AUTHORIZED BV run is shown
to have happened, with the same preregistration and the same bench code, and its raw records still match what the owner approved.

Chain of trust:
  1. The runner (not the user) writes, inside the run directory of a BV run: environment.json (taken at start), a verbatim copy of
     the authorization that was in force (authorization_used.json), plan.json, validity.json, registry.jsonl (the observer's append-only
     REG file, including RUN_START / RUN_END), summary.json and finally bv_attestation.json.
  2. bv_attestation.json is computed FROM THOSE FILES (build_attestation): it holds their SHA-256 values plus run id, authorization id,
     prereg hash, bench-code hash and a digest of the results; its own digest is `attestation_sha256`.
  3. The OWNER binds a later cells authorization to that run: phases["E1A-CELLS"]["bv_binding"] = {run_id, bv_authorization_id,
     attestation_sha256}.  The runner then re-derives everything from the raw files (verify_bv_provenance) and counts the cells only if
     every check holds.  A path, a self-reported field or a hand-written JSON never counts: any edit of any raw file changes the
     digest the owner approved.
Residual limit (stated, not hidden): a person with write access to the evidence directory who fabricates a complete, mutually
consistent run BEFORE the owner reviews it is not detected by file logic alone; the owner's review of the committed BV evidence is
the anchor, so the BV run directory should be committed before the binding is issued.
"""
import json
import os
import re

import common as C
import registry as R

EVIDENCE_ROOT = os.path.join(C.A003_DIR, "evidence")
BV_RUN_LEVEL_IDS = ("BV-1", "BV-2", "BV-3", "BV-6", "BV-7")
PHASE_BV = "BV-SELFTEST"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
REQUIRED_FILES = ("environment.json", "authorization_used.json", "plan.json", "validity.json", "registry.jsonl", "summary.json", "bv_attestation.json")

# what the observer's registry must show for each check that starts processes: label -> (kinds required, kinds forbidden)
REG_EXPECT = {
    "BV-1": ("BV1", {"INTENT", "FORKED", "REGISTERED", "ABORTED", "DEAD"}, {"RELEASED"}),
    "BV-2": ("BV2-helper", {"INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD"}, {"ABORTED"}),
    "BV-3": ("BV3", {"INTENT", "FORKED", "REGISTERED", "DEAD"}, {"RELEASED", "ABORTED"}),
    "BV-6": ("BV6", {"INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD"}, {"ABORTED"}),
}
BV7_FILE = os.path.join("validity_work", "bv7_torn.jsonl")


def canonical_sha256(obj):
    return C.sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _file_sha(run_dir, name):
    return C.sha256_file(os.path.join(run_dir, name))


def attestation_digest(att):
    """Digest of the attestation without its own digest field."""
    return canonical_sha256({k: v for k, v in att.items() if k != "attestation_sha256"})


def build_attestation(run_dir, write=True):
    """Compute the attestation FROM THE FILES currently in `run_dir` (never from memory).  -> dict (also written unless write=False)."""
    env, used, val = (_read_json(os.path.join(run_dir, n)) for n in ("environment.json", "authorization_used.json", "validity.json"))
    summ = _read_json(os.path.join(run_dir, "summary.json"))
    att = {"schema": "e1a-bv-attestation-1", "run_id": os.path.basename(os.path.normpath(run_dir)), "phase": env.get("phase"),
           "authorization_id": used.get("authorization_id"), "prereg_sha256": env.get("prereg_sha256"),
           "bench_code_sha256": env.get("bench_code_sha256"), "checks_run": sorted((val.get("meta") or {}).get("checks_run") or []),
           "results_sha256": canonical_sha256(val.get("results")), "files": {n: _file_sha(run_dir, n) for n in REQUIRED_FILES if n not in ("bv_attestation.json",)},
           "summary_digest": {k: summ.get(k) for k in ("phase", "aborted", "cleanup_confirmed", "recovery_open", "janitor_exit", "planned_trials")}}
    att["attestation_sha256"] = attestation_digest(att)
    if write:
        with open(os.path.join(run_dir, "bv_attestation.json"), "w", encoding="utf-8") as f:
            json.dump(att, f, indent=1, sort_keys=True)
    return att


def _authorization_covers_bv(used, prereg_sha, code_hash, auth_id):
    errs = []
    if used.get("schema") != "e1a-auth-2" or used.get("authorized_by") != "owner":
        errs.append("authorization copy: wrong schema or not owner-issued")
    if used.get("authorization_id") != auth_id:
        errs.append("authorization copy: id %r != bound bv_authorization_id %r" % (used.get("authorization_id"), auth_id))
    if used.get("prereg_sha256") != prereg_sha or used.get("bench_code_sha256") != code_hash:
        errs.append("authorization copy: bound to a different preregistration or bench code")
    granted = ((used.get("phases") or {}).get(PHASE_BV) or {}).get("checks") or []
    if not set(BV_RUN_LEVEL_IDS) <= set(granted):
        errs.append("authorization copy: does not grant all run-level checks")
    return errs


def verify_bv_provenance(binding, prereg_sha, code_hash, evidence_root=None):
    """-> (ok: bool, reasons: [str]).  Counts nothing as proven unless EVERY check holds.  `binding` comes from the owner-issued cells
    authorization; nothing here trusts a user-supplied path or a self-reported field."""
    root = evidence_root or EVIDENCE_ROOT
    why = []
    if not isinstance(binding, dict) or not all(isinstance(binding.get(k), str) and binding.get(k) for k in ("run_id", "bv_authorization_id", "attestation_sha256")):
        return False, ["no complete owner-issued bv_binding in the cells authorization"]
    rid = binding["run_id"]
    if not RUN_ID_RE.match(rid) or rid in (".", ".."):
        return False, ["bv_binding.run_id is not a plain run directory name"]
    run_dir = os.path.join(root, rid)
    if not os.path.isdir(run_dir) or os.path.islink(run_dir) or os.path.dirname(os.path.realpath(run_dir)) != os.path.realpath(root):
        return False, ["run directory %r is missing, a link, or outside the evidence root" % rid]
    missing = [n for n in REQUIRED_FILES if not os.path.isfile(os.path.join(run_dir, n))]
    if missing:
        return False, ["run directory lacks %s" % missing]
    try:
        att = _read_json(os.path.join(run_dir, "bv_attestation.json"))
        env, used, val, summ = (_read_json(os.path.join(run_dir, n)) for n in ("environment.json", "authorization_used.json", "validity.json", "summary.json"))
        fresh = build_attestation(run_dir, write=False)                       # recomputed from the raw files, not from the stored copy
    except (OSError, ValueError, KeyError, TypeError) as e:
        return False, ["evidence files unreadable or malformed: %r" % (e,)]
    if att.get("attestation_sha256") != attestation_digest(att):
        why.append("stored attestation does not match its own digest (edited)")
    if fresh != att:
        why.append("attestation differs from a recomputation over the raw files (a raw file changed after attestation)")
    if att.get("attestation_sha256") != binding["attestation_sha256"] or fresh["attestation_sha256"] != binding["attestation_sha256"]:
        why.append("attestation digest differs from the one the owner bound")
    if att.get("run_id") != rid:
        why.append("attestation run_id %r != bound %r" % (att.get("run_id"), rid))
    if att.get("authorization_id") != binding["bv_authorization_id"]:
        why.append("attestation authorization_id differs from the bound bv_authorization_id")
    if att.get("prereg_sha256") != prereg_sha or env.get("prereg_sha256") != prereg_sha:
        why.append("BV run used a different preregistration")
    if att.get("bench_code_sha256") != code_hash or env.get("bench_code_sha256") != code_hash:
        why.append("BV run used different bench code")
    if env.get("phase") != "bv" or att.get("phase") != "bv":
        why.append("run is not a BV-phase run")
    if sorted(att.get("checks_run") or []) != sorted(BV_RUN_LEVEL_IDS):
        why.append("not all run-level checks were run: %s" % att.get("checks_run"))
    meta = val.get("meta") or {}
    res = val.get("results") or {}
    if meta.get("run_id") != rid or meta.get("authorization_id") != binding["bv_authorization_id"]:
        why.append("validity.json meta does not name the bound run / authorization")
    bad = [k for k in BV_RUN_LEVEL_IDS if not (isinstance(res.get(k), dict) and res[k].get("ok") is True and (res[k].get("cleanup") or {"cleanup_ok": True}).get("cleanup_ok") is True)]
    if bad:
        why.append("checks not passed or without confirmed cleanup: %s" % bad)
    why += _authorization_covers_bv(used, prereg_sha, code_hash, binding["bv_authorization_id"])
    if env.get("authorization_sha256") != att["files"].get("authorization_used.json"):
        why.append("the authorization copy is not the file recorded at the start of the run")
    for k, expect in (("phase", "bv"), ("aborted", None), ("cleanup_confirmed", True), ("recovery_open", False), ("janitor_exit", 0), ("planned_trials", 0)):
        if summ.get(k) != expect:
            why.append("summary %s = %r (expected %r)" % (k, summ.get(k), expect))
    why += _verify_registry(run_dir, rid, prereg_sha)
    if not os.path.isfile(os.path.join(run_dir, BV7_FILE)):
        why.append("BV-7 work file missing")
    return (not why), why


def _verify_registry(run_dir, rid, prereg_sha):
    """The observer's own append-only REG file must show the run and the sacrificial nodes of every process-starting check."""
    why = []
    recs, info = R.parse_reg(os.path.join(run_dir, "registry.jsonl"))
    if info["missing"] or info["torn_tail"] or info["corrupt_lines"]:
        return ["registry.jsonl irregular: %s" % info]
    issues = R.integrity_issues(recs)
    if issues:
        why.append("registry.jsonl integrity issues: %s" % issues[:3])
    starts = [r for r in recs if r["kind"] == "RUN_START"]
    ends = [r for r in recs if r["kind"] == "RUN_END"]
    if len(starts) != 1 or starts[0].get("run_id") != rid or starts[0].get("prereg_sha256") != prereg_sha or starts[0].get("phase") != "bv":
        why.append("registry RUN_START does not match the bound run")
    if len(ends) != 1 or ends[0].get("cleanup_confirmed") is not True or ends[0].get("aborted") is not None or recs[-1] is not ends[0]:
        why.append("registry RUN_END missing, not last, aborted or without confirmed cleanup")
    nodes = R.fold(recs)
    by_label = {}
    for r in recs:
        if r["kind"] == "INTENT":
            by_label.setdefault(r.get("label"), []).append(r["node_id"])
    for chk, (label, need, forbid) in REG_EXPECT.items():
        ids = by_label.get(label) or []
        if len(ids) != 1:
            why.append("%s: expected exactly one registry node labelled %s, found %d" % (chk, label, len(ids)))
            continue
        n = nodes[ids[0]]
        kinds = {k.upper() for k, v in n.items() if v is not None}
        if not need <= kinds or kinds & forbid:
            why.append("%s: registry node %s shows %s (need %s, forbid %s)" % (chk, label, sorted(kinds), sorted(need), sorted(forbid)))
    if by_label.get("SUP"):
        why.append("a BV-phase run must not contain experiment (SUP) nodes")
    return why


def evaluate_counting(auth, plan_has_trials, prereg_sha, code_hash, evidence_root=None):
    """-> (counted, detail).  Cell results count only with a verified binding; anything else is SMOKE / NOT COUNTED."""
    if not plan_has_trials:
        return False, {"verified": False, "reasons": ["no cells in this plan"]}
    binding = (((auth.get("phases") or {}).get("E1A-CELLS")) or {}).get("bv_binding")
    ok, reasons = verify_bv_provenance(binding, prereg_sha, code_hash, evidence_root)
    return ok, {"verified": ok, "reasons": reasons, "binding": binding}
