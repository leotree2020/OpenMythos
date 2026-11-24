"""Stage C item 7 (testonce.py): the two hard preconditions of TEST evaluation.
- ST10 PASS as a committed record (positive and negative cases; committed bytes against the working tree);
- TEST evaluated once: a committed or uncommitted reservation refuses any further reservation; evaluate_model's TEST
  path needs the committed reservation and refuses after the evaluated marker is committed.
Throw-away git repositories under tmp_path; no TEST content is generated or read (the authorization is hand-built and
its checks stop before any row is read, or the synthetic leakage report is used).
"""
import json
import subprocess

import pytest

from metrix_e1 import leakage as LK
from metrix_e1 import stops as STP
from metrix_e1 import testonce as TO
from metrix_e1.errors import ImplementationFail


def _auth(fz, g="a" * 64, s="b" * 64):
    return LK.TestAuthorization(fz.record.commit, g, s)


def _report(within=True):
    return {"part": "test", "result": "PASS" if within else "FAIL",
            "checks": {c: {"value": 0, "limit": 0, "within_limit": within, "detail": {}} for c in LK.TEST_CHECKS}}


def _commit_repo(tmp_path, files):
    """A repository whose HEAD holds `files` (rel path -> text); returns the root."""
    root = tmp_path / "repo"
    root.mkdir()
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "t"], check=True)
    return root


def _record_text(rec):
    return json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


# ----------------------------------------------------------------------------------------------- ST10 record

def test_st10_record_pass_is_accepted(fz):
    auth = _auth(fz)
    rec = TO.make_st10_record(fz, auth, _report(), 7, 7)
    assert rec["result"] == "PASS" and TO.st10_problem(rec, fz, auth) is None


def test_st10_record_is_not_written_when_st10_stops(fz):
    auth = _auth(fz)
    with pytest.raises(STP.Stop) as e:
        TO.make_st10_record(fz, auth, _report(), 7, 8)          # the two L6 counts differ
    assert e.value.stop == "ST10"
    with pytest.raises(STP.Stop):
        TO.make_st10_record(fz, auth, _report(within=False), 7, 7)   # a TEST part over its limit
    with pytest.raises(STP.Stop):
        TO.make_st10_record(fz, auth, _report(), 7, None)       # no data-auditor count


@pytest.mark.parametrize("case", ["result", "frozen_commit", "bound", "checks", "over", "l6", "label"])
def test_st10_problem_branches(fz, case):
    auth = _auth(fz)
    rec = TO.make_st10_record(fz, auth, _report(), 7, 7)
    if case == "result":
        rec["result"] = "FAIL"
    elif case == "frozen_commit":
        rec["frozen_commit"] = "1" * 40
    elif case == "bound":
        rec["authorization"]["gate0_record_sha256"] = "c" * 64
    elif case == "checks":
        del rec["leakage_test_checks"]["L6"]
    elif case == "over":
        rec["leakage_test_checks"]["L4"]["within_limit"] = False
    elif case == "l6":
        rec["l6_auditor"] = 8
    elif case == "label":
        rec["label"] = "smoke"
    assert TO.st10_problem(rec, fz, auth) is not None


def test_st10_committed_bytes_must_match_the_working_tree(fz, tmp_path):
    auth = _auth(fz)
    rec = TO.make_st10_record(fz, auth, _report(), 7, 7)
    root = _commit_repo(tmp_path, {TO.ST10_REL: _record_text(rec)})
    TO.require_st10(fz, auth, root)                                  # committed and equal: accepted
    (root / TO.ST10_REL).write_text(_record_text(dict(rec, l6_auditor=6)), encoding="utf-8")   # edited, not committed
    with pytest.raises(ImplementationFail, match="no committed ST10 record|differs"):
        TO.require_st10(fz, auth, root)


def test_st10_not_committed_refuses(fz, tmp_path):
    auth = _auth(fz)
    root = _commit_repo(tmp_path, {"README.md": "x\n"})
    (root / TO.ST10_REL).parent.mkdir(parents=True)
    (root / TO.ST10_REL).write_text(_record_text(TO.make_st10_record(fz, auth, _report(), 7, 7)), encoding="utf-8")
    with pytest.raises(ImplementationFail, match="no committed ST10 record"):
        TO.require_st10(fz, auth, root)


# ----------------------------------------------------------------------------------- one reservation, evaluated once

@pytest.fixture
def no_leakage_recheck(monkeypatch):
    """verify_authorization re-checks the committed Gate 0 and freeze records (tested in test_test_data.py); here the
    reservation rules are the subject, so that re-check is replaced by a no-op."""
    monkeypatch.setattr(LK, "verify_authorization", lambda *a, **k: None)


class _FZ:
    """The frozen commit only: reserve_test_evaluation uses fz.record.commit and fz.repo_root."""
    def __init__(self, root, commit):
        self.repo_root = root
        self.record = type("R", (), {"commit": commit})()


def test_reservation_is_written_once_after_st10_and_refused_again(fz, tmp_path, no_leakage_recheck):
    auth = _auth(fz)
    st10 = TO.make_st10_record(fz, auth, _report(), 7, 7)
    root = _commit_repo(tmp_path, {TO.ST10_REL: _record_text(st10)})
    fake = _FZ(root, fz.record.commit)
    with pytest.raises(ImplementationFail, match="no committed TEST reservation"):
        TO.require_reservation(fake, auth, root)
    path = TO.reserve_test_evaluation(fake, auth, root)
    assert path.exists()
    with pytest.raises(ImplementationFail, match="TEST only once"):
        TO.reserve_test_evaluation(fake, auth, root)              # the reservation exists in the working tree
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-q", "-m", "reserve"], check=True)
    TO.require_reservation(fake, auth, root)                      # committed and matching: the evaluation may run
    with pytest.raises(ImplementationFail, match="TEST only once"):
        TO.reserve_test_evaluation(fake, auth, root)              # a committed reservation refuses again


def test_reservation_refused_without_st10_and_nothing_written(fz, tmp_path, no_leakage_recheck):
    auth = _auth(fz)
    root = _commit_repo(tmp_path, {"README.md": "x\n"})
    with pytest.raises(ImplementationFail, match="no committed ST10 record"):
        TO.reserve_test_evaluation(_FZ(root, fz.record.commit), auth, root)
    assert not (root / TO.RESERVATION_REL).exists()


def test_evaluated_marker_refuses_the_evaluation(fz, tmp_path, no_leakage_recheck):
    auth = _auth(fz)
    st10 = TO.make_st10_record(fz, auth, _report(), 7, 7)
    reservation = {"kind": "test_reservation", "mode": "formal", "label": None, "frozen_commit": fz.record.commit,
                   "authorization": TO._authorization_fields(auth), "result": "RESERVED"}
    root = _commit_repo(tmp_path, {TO.ST10_REL: _record_text(st10), TO.RESERVATION_REL: _record_text(reservation),
                                   TO.EVALUATED_REL: _record_text({"kind": "test_evaluated"})})
    with pytest.raises(ImplementationFail, match="TEST only once"):
        TO.require_reservation(_FZ(root, fz.record.commit), auth, root)
    with pytest.raises(ImplementationFail, match="TEST only once"):
        TO.reserve_test_evaluation(_FZ(root, fz.record.commit), auth, root)


def test_reservation_for_another_authorization_is_refused(fz, tmp_path, no_leakage_recheck):
    auth = _auth(fz)
    st10 = TO.make_st10_record(fz, auth, _report(), 7, 7)
    other = {"kind": "test_reservation", "mode": "formal", "label": None, "frozen_commit": fz.record.commit,
             "authorization": TO._authorization_fields(_auth(fz, g="d" * 64)), "result": "RESERVED"}
    root = _commit_repo(tmp_path, {TO.ST10_REL: _record_text(st10), TO.RESERVATION_REL: _record_text(other)})
    with pytest.raises(ImplementationFail, match="not the reservation of this authorization"):
        TO.require_reservation(_FZ(root, fz.record.commit), auth, root)


def test_evaluate_model_test_path_refuses_without_committed_st10(fz, contract, tmp_path):
    """evaluate_model(split="test") in the real repository: no ST10 record is committed there, so the TEST path refuses
    before any data is read (the synthetic authorization fails verify_authorization first; the ST10 check is the
    second precondition, reached in test_st10_not_committed_refuses)."""
    from metrix_e1 import evaluate as E
    from metrix_e1 import mode as M
    with pytest.raises(ImplementationFail, match="TEST path refused"):
        E.evaluate_model(None, None, {}, fz.templates, contract.evaluation, M.FORMAL_MODE, "cuda", split="test",
                         test_authorization=_auth(fz), fz=fz)


def test_protocol_frozen_file_names_another_commit(fz, monkeypatch):
    """BE2: the authorization equals the loaded frozen commit, but the PROTOCOL_FROZEN file of the repository names
    another commit: refused with that comparison's own message (the parser is replaced; the file is not changed)."""
    from types import SimpleNamespace
    from metrix_e1 import frozen as FZm
    monkeypatch.setattr(FZm, "parse_protocol_frozen", lambda data: SimpleNamespace(commit="3" * 40))
    with pytest.raises(ImplementationFail, match="PROTOCOL_FROZEN names 3{40}, the loaded frozen files"):
        LK.verify_authorization(_auth(fz), fz)
