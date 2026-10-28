"""J1 acceptance oracle (Lane O).  NOT TESTED / NEVER EXECUTED.  Pure functions.

ISOLATION CONTRACT
    * This module holds the PRIVATE expectations (fixture ids, canonical cards, expected subject verdicts, behaviour labels).  It is never imported by
      schema.py, judge.py or codec.py, and the judge never receives anything from it.  It does not import them either: its verdict vocabulary and
      scope labels are re-declared here so that a drift between judge and oracle is detectable instead of shared.
    * It grades a J1 OUTPUT dict against a PRIVATE expectation.  It never recomputes the subject verdict from the judge's logic.
    * Subject verdict (what J1 said about the synthetic evidence) and test acceptance (did J1 say what was predeclared) are different things.
      A test acceptance PASS means "the detector behaved as predeclared on synthetic input"; it says NOTHING about native B0 safety, kernel
      authenticity of any record, lawful reaping, or delivery.  A known B0 defect that J1 identifies correctly is not a B0 safety PASS.
    * SPEC_V0_1_INVENTORY is the V0.1 DOCUMENT inventory (6 arms, 18 proposed ids; 5 PASS / 5 FAIL / 8 BLOCKED expected).  It is a DRAFT, not frozen,
      and is not fixture data: no S/O bytes, hashes or run results exist.  The four SMOKE_ONLY assertions may never expect PASS.
"""
import re

SCOPE = "SYNTHETIC_CPU_ONLY"
MEASUREMENT_TARGET = "J1_SYNTHETIC_DETECTOR"
NATIVE_B0_SAFETY_STATUS = "NOT_EVALUATED_BY_J1"
GROK_REVIEW_STATE = "DEFERRED_NOT_PERFORMED"

VERDICTS = ("PASS", "FAIL", "BLOCKED")
ACCEPTANCE = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
EVIDENCE_SENSITIVE = ("ATTRIBUTION", "UNIQUE_REGISTRY", "ZOMBIE_AT_T", "LOG_MATCHES_SEAL", "WRITE_COMPLETE")
SMOKE_ONLY = ("PREVENT_PROOF", "LAWFUL_REAP", "EVIDENCE_USABLE", "DELIVERY")

_FIXTURE_ID_RE = re.compile(r"^J1-F0[1-6]-[A-D]$")
_REQUIRED_OUTPUT_KEYS = ("assertion_id", "subject_verdict", "evidence_basis_codes", "supporting_observable_refs", "coverage",
                         "measurement_target", "native_B0_safety_status", "scope")

# fixture id -> (canonical card, assertion, expected subject verdict).  V0.1 document inventory; NOT frozen; NOT fixture data.
SPEC_V0_1_INVENTORY = {
    "J1-F01-A": ("D03c", "ATTRIBUTION", "FAIL"),
    "J1-F01-B": ("D03c", "ATTRIBUTION", "BLOCKED"),
    "J1-F01-C": ("D03c", "ATTRIBUTION", "PASS"),
    "J1-F01-D": ("D03c", "ATTRIBUTION", "BLOCKED"),
    "J1-F02-A": ("D03d", "UNIQUE_REGISTRY", "FAIL"),
    "J1-F02-B": ("D03d", "UNIQUE_REGISTRY", "PASS"),
    "J1-F03-A": ("D01-B0", "PREVENT_PROOF", "BLOCKED"),
    "J1-F03-B": ("D01-B0", "PREVENT_PROOF", "BLOCKED"),
    "J1-F04-A": ("D07", "LAWFUL_REAP", "BLOCKED"),
    "J1-F04-B": ("D07", "ZOMBIE_AT_T", "PASS"),
    "J1-F04-C": ("D07", "ZOMBIE_AT_T", "FAIL"),
    "J1-F05-A": ("D05", "LOG_MATCHES_SEAL", "FAIL"),
    "J1-F05-B": ("D05", "LOG_MATCHES_SEAL", "PASS"),
    "J1-F05-C": ("D05", "EVIDENCE_USABLE", "BLOCKED"),
    "J1-F06-A": ("D09", "DELIVERY", "BLOCKED"),
    "J1-F06-B": ("D09", "WRITE_COMPLETE", "PASS"),
    "J1-F06-C": ("D09", "WRITE_COMPLETE", "FAIL"),
    "J1-F06-D": ("D09", "WRITE_COMPLETE", "BLOCKED"),
}
SPEC_V0_1_EXPECTED_COUNTS = {"PASS": 5, "FAIL": 5, "BLOCKED": 8}


def inventory_self_check():
    """-> list of problems in the document inventory itself (empty = consistent).  Detects a mistyped inventory, not a wrong judge."""
    problems = []
    if len(SPEC_V0_1_INVENTORY) != 18:
        problems.append("inventory does not have 18 ids")
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
    for fid, (card, assertion, expected) in SPEC_V0_1_INVENTORY.items():
        if _FIXTURE_ID_RE.match(fid) is None:
            problems.append("bad id shape")
        if assertion not in EVIDENCE_SENSITIVE + SMOKE_ONLY:
            problems.append("unknown assertion")
        if expected not in VERDICTS:
            problems.append("unknown expected verdict")
            continue
        counts[expected] += 1
        if assertion in SMOKE_ONLY and expected == "PASS":
            problems.append("a SMOKE_ONLY assertion may not expect PASS")
    if counts != SPEC_V0_1_EXPECTED_COUNTS:
        problems.append("expected verdict distribution differs from 5/5/8")
    for assertion in ("ATTRIBUTION", "UNIQUE_REGISTRY", "ZOMBIE_AT_T", "LOG_MATCHES_SEAL", "WRITE_COMPLETE"):
        seen = {e for (_c, a, e) in SPEC_V0_1_INVENTORY.values() if a == assertion}
        if len(seen) < 2:
            problems.append("discriminative assertion has no contrasting expected outcome")
    return problems


def validate_private_expectation(exp):
    """Strict check of one PRIVATE expectation record.  -> list of problems (empty = usable).  An unusable expectation makes the case BLOCKED
    (spec / instrument not ready), never a subject FAIL."""
    problems = []
    if type(exp) is not dict:
        return ["expectation: not a dict"]
    required = {"fixture_id", "canonical_card", "assertion_id", "expected_subject_verdict"}
    allowed = required | {"expected_behavior_label", "truth_model"}
    if required - set(exp):
        problems.append("expectation: missing required fields")
    if set(exp) - allowed:
        problems.append("expectation: unknown fields")
    if problems:
        return problems
    if type(exp["fixture_id"]) is not str or _FIXTURE_ID_RE.match(exp["fixture_id"]) is None:
        problems.append("expectation: bad fixture_id shape")
    if type(exp["canonical_card"]) is not str or not exp["canonical_card"]:
        problems.append("expectation: bad canonical_card")
    if exp["assertion_id"] not in EVIDENCE_SENSITIVE + SMOKE_ONLY:
        problems.append("expectation: unknown assertion_id")
    if exp["expected_subject_verdict"] not in VERDICTS:
        problems.append("expectation: unknown expected_subject_verdict")
    elif exp["assertion_id"] in SMOKE_ONLY and exp["expected_subject_verdict"] == "PASS":
        problems.append("expectation: a SMOKE_ONLY assertion may not expect PASS in V0.1")
    return problems


def _output_problems(out):
    if type(out) is not dict:
        return ["J1 output is not a dict"]
    p = []
    for k in _REQUIRED_OUTPUT_KEYS:
        if k not in out:
            p.append("J1 output lacks a required key")
            break
    if p:
        return p
    if out["subject_verdict"] not in VERDICTS:
        p.append("J1 output has an unknown subject_verdict")
    if not isinstance(out["evidence_basis_codes"], list) or not all(type(c) is str for c in out["evidence_basis_codes"]):
        p.append("J1 output evidence_basis_codes is not a list of strings")
    if out["measurement_target"] != MEASUREMENT_TARGET or out["native_B0_safety_status"] != NATIVE_B0_SAFETY_STATUS or out["scope"] != SCOPE:
        p.append("J1 output scope labels are missing or wrong")
    return p


def grade_case(expectation, j1_output):
    """Grade ONE case.  -> dict with test_acceptance_verdict PASS | FAIL | BLOCKED.
      BLOCKED : the expectation or the J1 output is unusable / mislabelled (instrument or spec not ready).
      FAIL    : well-formed output whose assertion or subject verdict differs from the predeclared expectation.
      PASS    : same assertion, same subject verdict (and for a SMOKE_ONLY assertion: not a PASS, and the coverage label says SMOKE_ONLY)."""
    reasons = validate_private_expectation(expectation)
    res = {"fixture_id": expectation.get("fixture_id") if type(expectation) is dict else None,
           "assertion_id": expectation.get("assertion_id") if type(expectation) is dict else None,
           "expected_subject_verdict": expectation.get("expected_subject_verdict") if type(expectation) is dict else None,
           "subject_verdict": None, "test_acceptance_verdict": "BLOCKED", "reasons": reasons, "coverage_limit": None,
           "measurement_target": MEASUREMENT_TARGET, "native_B0_safety_status": NATIVE_B0_SAFETY_STATUS, "scope": SCOPE,
           "grok_review_state": GROK_REVIEW_STATE}
    if reasons:
        return res
    oprob = _output_problems(j1_output)
    if oprob:
        res["reasons"] = oprob
        return res
    res["subject_verdict"] = j1_output["subject_verdict"]
    smoke = expectation["assertion_id"] in SMOKE_ONLY
    res["coverage_limit"] = "SMOKE_ONLY" if smoke else None
    if j1_output["assertion_id"] != expectation["assertion_id"]:
        res["test_acceptance_verdict"] = "FAIL"
        res["reasons"] = ["J1 answered a different assertion than the one predeclared"]
        return res
    if smoke and j1_output["coverage"] != "SMOKE_ONLY":
        res["reasons"] = ["J1 output does not label a SMOKE_ONLY assertion as SMOKE_ONLY"]
        return res
    if smoke and j1_output["subject_verdict"] == "PASS":
        res["test_acceptance_verdict"] = "FAIL"
        res["reasons"] = ["a SMOKE_ONLY assertion produced PASS: an unproven PASS"]
        return res
    if j1_output["subject_verdict"] == expectation["expected_subject_verdict"]:
        res["test_acceptance_verdict"] = "PASS"
        res["reasons"] = ["subject verdict equals the predeclared expectation"]
    else:
        res["test_acceptance_verdict"] = "FAIL"
        res["reasons"] = ["subject verdict differs from the predeclared expectation"]
    return res


def aggregate(case_results, expected_ids=None):
    """Run-level acceptance over graded cases.  FAIL > BLOCKED > PASS.  The id set must equal `expected_ids` exactly (default: the V0.1 inventory):
    a missing id is a NOT_RUN -> BLOCKED; an unknown or duplicate id -> BLOCKED (spec not ready).  A run PASS is a statement about the DETECTOR on
    synthetic input only; it carries the mandatory scope labels and never a native B0 safety claim."""
    expected = set(SPEC_V0_1_INVENTORY) if expected_ids is None else set(expected_ids)
    reasons = []
    ids = [r.get("fixture_id") for r in case_results]
    dup = sorted({i for i in ids if ids.count(i) > 1 and i is not None})
    unknown = sorted((i for i in set(ids) if i not in expected), key=str)
    missing = sorted(expected - set(ids))
    if dup:
        reasons.append("duplicate ids")
    if unknown:
        reasons.append("unknown ids")
    if missing:
        reasons.append("%d expected ids not run" % len(missing))
    statuses = [r.get("test_acceptance_verdict") for r in case_results]
    if any(s not in ACCEPTANCE for s in statuses):
        reasons.append("unknown acceptance status")
    if "FAIL" in statuses:
        verdict = "FAIL"
    elif reasons or "BLOCKED" in statuses or "NOT_RUN" in statuses or not statuses:
        verdict = "BLOCKED"
    else:
        verdict = "PASS"
    discriminative = sum(1 for r in case_results if r.get("assertion_id") in EVIDENCE_SENSITIVE and r.get("test_acceptance_verdict") == "PASS")
    smoke = sum(1 for r in case_results if r.get("assertion_id") in SMOKE_ONLY and r.get("test_acceptance_verdict") == "PASS")
    return {"run_acceptance_verdict": verdict, "reasons": reasons, "cases": len(case_results), "expected_cases": len(expected),
            "discriminative_cases_passed": discriminative, "smoke_only_cases_passed": smoke,
            "smoke_only_note": "SMOKE_ONLY passes carry no broad accuracy claim",
            "measurement_target": MEASUREMENT_TARGET, "native_B0_safety_status": NATIVE_B0_SAFETY_STATUS, "scope": SCOPE,
            "grok_review_state": GROK_REVIEW_STATE}
