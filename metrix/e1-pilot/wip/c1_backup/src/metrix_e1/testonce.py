"""The two hard preconditions of TEST evaluation (protocol v1.1 section 8 step 8 and section 11 ST10; Implementation
Task Order V1 stage C item 7; DEFERRED_MINORS BB1, BC2, BD8).

1. ST10 passed, as a committed record: results/st10_record.json. It is written only when stops.st10 does not stop
   (the TEST part of L3-L6 within every limit; the Executor's and the data-auditor's L6 TEST counts equal), it names the
   frozen commit and the three hashes of the TestAuthorization, and it must be committed as it is in the working tree.
   require_st10() checks the committed bytes before any TEST evaluation.
2. TEST is evaluated once: reserve_test_evaluation() writes results/test_evaluation_reserved.json, which must then be
   committed before TEST is evaluated. A reservation (committed or left uncommitted in the working tree) refuses any
   further reservation. evaluate_model(split="test") needs the reservation committed with the same authorization, and
   refuses when results/test_evaluated.json is committed (the driver commits it after the evaluation).
"""
import json
from pathlib import Path

from . import frozen as FZ
from . import leakage as LK
from . import record as R
from . import stops as STP
from .errors import ImplementationFail

ST10_REL = "results/st10_record.json"
RESERVATION_REL = "results/test_evaluation_reserved.json"
EVALUATED_REL = "results/test_evaluated.json"


def _authorization_fields(authorization):
    return {"frozen_commit": authorization.frozen_commit,
            "gate0_record_sha256": authorization.gate0_record_sha256,
            "selection_record_sha256": authorization.selection_record_sha256}


def make_st10_record(fz, authorization, report, executor_l6, auditor_l6):
    """The ST10 PASS record. Raises stops.Stop (ST10) when the TEST part of the leakage report or the two L6 counts
    do not pass; nothing is written then."""
    STP.st10(fz, report, executor_l6, auditor_l6)
    checks = {c: {"value": v["value"], "limit": v["limit"], "within_limit": v["within_limit"]}
              for c, v in report["checks"].items()}
    return {"kind": "st10", "mode": "formal", "label": None, "frozen_commit": fz.record.commit,
            "authorization": _authorization_fields(authorization), "leakage_test_checks": checks,
            "l6_executor": executor_l6, "l6_auditor": auditor_l6, "result": "PASS"}


def st10_problem(rec, fz, authorization):
    """None when the record is a formal ST10 PASS for this frozen commit and this authorization, else the reason."""
    if rec.get("kind") != "st10" or rec.get("mode") != "formal" or rec.get("label") is not None:
        return "not a formal-mode st10 record (kind %r, mode %r)" % (rec.get("kind"), rec.get("mode"))
    if rec.get("result") != "PASS":
        return "result %r, not PASS" % (rec.get("result"),)
    if rec.get("frozen_commit") != fz.record.commit or authorization.frozen_commit != fz.record.commit:
        return "names frozen commit %r, the loaded frozen files %s" % (rec.get("frozen_commit"), fz.record.commit)
    if rec.get("authorization") != _authorization_fields(authorization):
        return "not bound to this TEST authorization"
    checks = rec.get("leakage_test_checks") or {}
    if set(checks) != set(LK.TEST_CHECKS):
        return "checks %s, not %s" % (sorted(checks), list(LK.TEST_CHECKS))
    over = sorted(c for c, v in checks.items() if v.get("within_limit") is not True)
    if over:
        return "TEST part over limit: %s" % ", ".join(over)
    l6e, l6a = rec.get("l6_executor"), rec.get("l6_auditor")
    if l6a is None or l6e != l6a:
        return "L6 TEST counts differ: Executor %r, data-auditor %r" % (l6e, l6a)
    return None


def require_st10(fz, authorization, repo_root=None):
    """Condition 1 of the TEST path: the committed ST10 record passes st10_problem."""
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    try:
        rec, _sha = R.committed_json(root, ST10_REL)
    except R.NotCommitted as e:
        raise ImplementationFail("TEST path refused: no committed ST10 record: %s" % e) from e
    problem = st10_problem(rec, fz, authorization)
    if problem:
        raise ImplementationFail("TEST path refused: committed %s: %s" % (ST10_REL, problem))


def _is_committed(root, rel):
    try:
        R.committed_json(root, rel)
        return True
    except R.NotCommitted:
        return False


def reserve_test_evaluation(fz, authorization, repo_root=None):
    """Write the reservation (the caller commits it before TEST is evaluated). Refused, before anything is written,
    when ST10 has not passed, when a reservation is committed or present in the working tree, or when TEST is already
    marked evaluated. Returns the path written."""
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    LK.verify_authorization(authorization, fz, root)
    require_st10(fz, authorization, root)
    path = root / RESERVATION_REL
    if _is_committed(root, RESERVATION_REL) or path.exists():
        raise ImplementationFail("TEST only once: %s already exists (committed or in the working tree)" % RESERVATION_REL)
    if _is_committed(root, EVALUATED_REL):
        raise ImplementationFail("TEST only once: %s is committed" % EVALUATED_REL)
    rec = {"kind": "test_reservation", "mode": "formal", "label": None, "frozen_commit": fz.record.commit,
           "authorization": _authorization_fields(authorization), "result": "RESERVED"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def require_reservation(fz, authorization, repo_root=None):
    """Condition 2 of the TEST path: the reservation is committed, as it is in the working tree, for this authorization,
    and TEST is not marked evaluated (committed)."""
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    if _is_committed(root, EVALUATED_REL):
        raise ImplementationFail("TEST only once: %s is committed; TEST is not evaluated again" % EVALUATED_REL)
    try:
        rec, _sha = R.committed_json(root, RESERVATION_REL)
    except R.NotCommitted as e:
        raise ImplementationFail("TEST path refused: no committed TEST reservation: %s" % e) from e
    if (rec.get("kind") != "test_reservation" or rec.get("mode") != "formal" or rec.get("result") != "RESERVED"
            or rec.get("frozen_commit") != fz.record.commit
            or rec.get("authorization") != _authorization_fields(authorization)):
        raise ImplementationFail("TEST path refused: committed %s is not the reservation of this authorization" % RESERVATION_REL)
