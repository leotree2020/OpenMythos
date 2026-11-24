#!/usr/bin/env python3
"""ic1: data-auditor's independent reproduction of the TEST-path gate scenarios (Implementation Task Order V1 stage C
item 7). Written from the protocol/task-order wording, NOT from the Executor's code: no import of metrix_e1, no
copy of its checks. It reads no eval_sets.jsonl, no TEST rows, loads no model, uses no GPU. Every scenario runs in a
fresh temporary git repository created under the directory given as argv[1].

Usage: python3 -I ic1_test_gate_scenarios.py <base_dir_outside_repo>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FROZEN = "f" * 40
LIMITS = {"L3a": 2, "L3b": 2, "L4": 2, "L5": 2, "L6": 2}
ST10 = "results/st10_record.json"
RESERVED = "results/test_evaluation_reserved.json"
EVALUATED = "results/test_evaluated.json"
AUTH = {"frozen_commit": FROZEN, "gate0_record_sha256": "a" * 64, "selection_record_sha256": "b" * 64}
AUTH_OTHER = dict(AUTH, gate0_record_sha256="c" * 64)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)


def committed(repo, rel):
    r = git(repo, "cat-file", "blob", "HEAD:" + rel)
    return r.stdout if r.returncode == 0 else None


def working(repo, rel):
    p = Path(repo) / rel
    return p.read_bytes() if p.is_file() else None


def write(repo, rel, obj_or_bytes):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    data = obj_or_bytes if isinstance(obj_or_bytes, bytes) else (
        json.dumps(obj_or_bytes, sort_keys=True, indent=1) + "\n").encode()
    p.write_bytes(data)


def commit(repo, msg="c"):
    git(repo, "add", "-A")
    r = git(repo, "commit", "-q", "-m", msg)
    assert r.returncode == 0, r.stderr


def new_repo(base, name):
    repo = Path(base) / name
    repo.mkdir(parents=True, exist_ok=False)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "audit@example.invalid")
    git(repo, "config", "user.name", "audit")
    write(repo, "README.txt", b"base\n")
    commit(repo, "base")
    return repo


def st10_record(auth=AUTH, value=1, flag=True, result="PASS", exe_l6=5, aud_l6=5, frozen=FROZEN):
    checks = {}
    for c in ("L3a", "L3b", "L4", "L5", "L6"):
        checks[c] = {"value": value if c == "L4" else 0, "limit": LIMITS[c],
                     "within_limit": flag if c == "L4" else True}
    return {"kind": "st10", "mode": "formal", "label": None, "frozen_commit": frozen,
            "authorization": dict(auth), "leakage_test_checks": checks,
            "l6_executor": exe_l6, "l6_auditor": aud_l6, "result": result}


# ---------------------------------------------------------------- independent gate model (spec, not Executor code)

def st10_refusal(repo, auth):
    """None when ST10 passed and is committed exactly as in the working tree; else the reason."""
    raw = committed(repo, ST10)
    if raw is None:
        return "ST10 record not committed"
    if working(repo, ST10) != raw:
        return "ST10 record in working tree differs from committed"
    try:
        rec = json.loads(raw)
    except ValueError:
        return "ST10 record does not parse"
    if rec.get("kind") != "st10" or rec.get("result") != "PASS":
        return "ST10 record is not a PASS"
    if rec.get("frozen_commit") != FROZEN or auth.get("frozen_commit") != FROZEN:
        return "frozen commit mismatch"
    if rec.get("authorization") != {k: auth[k] for k in ("frozen_commit", "gate0_record_sha256", "selection_record_sha256")}:
        return "ST10 record not bound to this authorization"
    checks = rec.get("leakage_test_checks") or {}
    if set(checks) != {"L3a", "L3b", "L4", "L5", "L6"}:
        return "ST10 TEST checks incomplete"
    for c, v in checks.items():
        if not (v.get("value") is not None and v["value"] <= LIMITS[c]):
            return "TEST check %s over limit (value %r, limit %r)" % (c, v.get("value"), LIMITS[c])
    if rec.get("l6_auditor") is None or rec.get("l6_executor") != rec.get("l6_auditor"):
        return "L6 TEST counts differ (Executor %r, data-auditor %r)" % (rec.get("l6_executor"), rec.get("l6_auditor"))
    return None


def evaluated_committed(repo):
    return committed(repo, EVALUATED) is not None


def reservation_for_evaluation(repo, auth):
    """None when the reservation is committed exactly as in the working tree and is for this authorization."""
    if evaluated_committed(repo):
        return "TEST already evaluated (evaluated marker committed)"
    raw = committed(repo, RESERVED)
    if raw is None:
        return "reservation not committed"
    if working(repo, RESERVED) != raw:
        return "reservation in working tree differs from committed"
    rec = json.loads(raw)
    want = {k: auth[k] for k in ("frozen_commit", "gate0_record_sha256", "selection_record_sha256")}
    if rec.get("kind") != "test_reservation" or rec.get("result") != "RESERVED" or rec.get("authorization") != want:
        return "reservation is not for this authorization"
    return None


def reserve(repo, auth):
    """Writes the reservation file (not committed here). Returns (accepted, reason)."""
    if evaluated_committed(repo):
        return False, "evaluated marker committed"
    reason = st10_refusal(repo, auth)
    if reason:
        return False, reason
    if committed(repo, RESERVED) is not None or working(repo, RESERVED) is not None:
        return False, "reservation already committed or present in working tree"
    write(repo, RESERVED, {"kind": "test_reservation", "result": "RESERVED", "frozen_commit": FROZEN,
                           "authorization": {k: auth[k] for k in ("frozen_commit", "gate0_record_sha256",
                                                                  "selection_record_sha256")}})
    return True, "reservation written"


def evaluate(repo, auth):
    """Entry point before any TEST evaluation. Returns (accepted, reason)."""
    reason = st10_refusal(repo, auth)
    if reason:
        return False, reason
    reason = reservation_for_evaluation(repo, auth)
    if reason:
        return False, reason
    return True, "TEST evaluation allowed"


# ---------------------------------------------------------------- scenarios

RESULTS = []


def scenario(code, title, expect_accept, run):
    base = sys.argv[1]
    repo = new_repo(base, code)
    cmd_desc, got = run(repo)
    ok = got[0] == expect_accept
    RESULTS.append(ok)
    print("[%s] %s" % (code, title))
    print("    action   : %s" % cmd_desc)
    print("    expected : %s" % ("ACCEPT" if expect_accept else "REFUSE"))
    print("    observed : %s (%s)" % ("ACCEPT" if got[0] else "REFUSE", got[1]))
    print("    result   : %s" % ("PASS" if ok else "FAIL"))


def s_st10_missing(repo):
    write(repo, "results/README.txt", b"no record\n")
    commit(repo)
    return "evaluate with no ST10 record", evaluate(repo, AUTH)


def s_st10_uncommitted(repo):
    write(repo, ST10, st10_record())
    return "evaluate with ST10 record written, not committed", evaluate(repo, AUTH)


def s_st10_wt_differs(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    write(repo, ST10, st10_record(value=0))
    return "ST10 committed, then working tree edited", evaluate(repo, AUTH)


def s_st10_l6_differ(repo):
    write(repo, ST10, st10_record(exe_l6=3, aud_l6=4))
    commit(repo)
    return "ST10 committed with L6 counts 3 vs 4", evaluate(repo, AUTH)


def s_st10_over_honest(repo):
    write(repo, ST10, st10_record(value=3, flag=False))
    commit(repo)
    return "ST10 committed with L4 value 3 > limit 2, within_limit false", evaluate(repo, AUTH)


def s_st10_over_forged_flag(repo):
    write(repo, ST10, st10_record(value=3, flag=True))
    commit(repo)
    return "ST10 committed with L4 value 3 > limit 2, within_limit forged true", evaluate(repo, AUTH)


def s_st10_auth_other(repo):
    write(repo, ST10, st10_record(auth=AUTH_OTHER))
    commit(repo)
    return "ST10 committed for another gate0 hash, evaluate with AUTH", evaluate(repo, AUTH)


def s_st10_result_fail(repo):
    write(repo, ST10, st10_record(result="FAIL"))
    commit(repo)
    return "ST10 committed with result FAIL", evaluate(repo, AUTH)


def s_st10_valid_control(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    reason = st10_refusal(repo, AUTH)
    return "control: ST10 PASS committed (ST10 check alone, before reservation)", (reason is None, reason or "ST10 passes")


def s_reserve_residual(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    write(repo, RESERVED, {"kind": "test_reservation", "result": "RESERVED"})
    acc, why = reserve(repo, AUTH)
    return "reserve with a reservation file left uncommitted in working tree", (acc, why)


def s_reserve_again_committed(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    acc, why = reserve(repo, AUTH)
    assert acc, why
    commit(repo, "reservation")
    acc, why = reserve(repo, AUTH)
    return "reserve again after reservation committed", (acc, why)


def s_reserve_after_evaluated(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    acc, why = reserve(repo, AUTH)
    assert acc, why
    commit(repo, "reservation")
    write(repo, EVALUATED, {"kind": "test_evaluated"})
    commit(repo, "evaluated")
    acc, why = reserve(repo, AUTH)
    return "reserve after evaluated marker committed", (acc, why)


def s_reserve_st10_missing(repo):
    write(repo, "README2.txt", b"x\n")
    commit(repo)
    return "reserve with no ST10 record", reserve(repo, AUTH)


def s_reserve_auth_mismatch(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    return "reserve with authorization whose gate0 hash differs from ST10 record", reserve(repo, AUTH_OTHER)


def s_eval_reservation_uncommitted(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    acc, why = reserve(repo, AUTH)
    assert acc, why
    return "evaluate with reservation written, not committed", evaluate(repo, AUTH)


def s_eval_reservation_other_auth(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    write(repo, RESERVED, {"kind": "test_reservation", "result": "RESERVED", "frozen_commit": FROZEN,
                           "authorization": {k: AUTH_OTHER[k] for k in ("frozen_commit", "gate0_record_sha256",
                                                                        "selection_record_sha256")}})
    commit(repo, "reservation for other authorization")
    return "evaluate with AUTH; ST10 is for AUTH, committed reservation is for AUTH_OTHER", evaluate(repo, AUTH)


def s_eval_marker_committed(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    acc, why = reserve(repo, AUTH)
    assert acc, why
    commit(repo, "reservation")
    write(repo, EVALUATED, {"kind": "test_evaluated"})
    commit(repo, "evaluated")
    return "evaluate with reservation and evaluated marker committed", evaluate(repo, AUTH)


def s_full_valid_path(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    acc, why = reserve(repo, AUTH)
    assert acc, why
    commit(repo, "reservation")
    return "control: ST10 PASS + reservation committed, no marker", evaluate(repo, AUTH)


def s_no_marker_second_eval(repo):
    write(repo, ST10, st10_record())
    commit(repo)
    acc, why = reserve(repo, AUTH)
    assert acc, why
    commit(repo, "reservation")
    first = evaluate(repo, AUTH)
    assert first[0], first
    return "second evaluate when the first run committed NO evaluated marker (window)", evaluate(repo, AUTH)


CASES = [
    ("A1", "ST10 missing", False, s_st10_missing),
    ("A2", "ST10 written but not committed", False, s_st10_uncommitted),
    ("A3", "ST10 committed, working tree differs", False, s_st10_wt_differs),
    ("A4", "ST10 two L6 counts differ", False, s_st10_l6_differ),
    ("A5", "ST10 one check over limit (honest flag)", False, s_st10_over_honest),
    ("A6", "ST10 one check over limit (flag forged true)", False, s_st10_over_forged_flag),
    ("A7", "ST10 bound to another authorization", False, s_st10_auth_other),
    ("A8", "ST10 result FAIL", False, s_st10_result_fail),
    ("A9", "control: valid ST10", True, s_st10_valid_control),
    ("B1", "reservation residual in working tree refuses reserve", False, s_reserve_residual),
    ("B2", "reserve again after reservation committed", False, s_reserve_again_committed),
    ("B3", "reserve after evaluated marker committed", False, s_reserve_after_evaluated),
    ("B4", "reserve without ST10", False, s_reserve_st10_missing),
    ("B5", "reserve with authorization hash mismatch", False, s_reserve_auth_mismatch),
    ("B6", "evaluate with reservation uncommitted", False, s_eval_reservation_uncommitted),
    ("B7", "evaluate with reservation for other authorization", False, s_eval_reservation_other_auth),
    ("B8", "evaluate after evaluated marker committed", False, s_eval_marker_committed),
    ("B9", "control: full valid path reaches evaluation", True, s_full_valid_path),
    ("B10", "observation: second evaluate without marker", True, s_no_marker_second_eval),
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    print("ic1 gate scenarios, independent model; temp repos under %s" % sys.argv[1])
    for code, title, expect, fn in CASES:
        scenario(code, title, expect, fn)
    print("SUMMARY: %d/%d scenarios as expected" % (sum(RESULTS), len(RESULTS)))
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
