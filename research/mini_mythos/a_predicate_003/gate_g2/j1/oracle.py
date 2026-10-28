"""J1 acceptance oracle (Lane O).  NOT TESTED / NEVER EXECUTED.  Pure functions.  (Correction 001: J1-IMPL-F01, J1-IMPL-F02.)

ISOLATION CONTRACT
    * This module holds the PRIVATE expectations (fixture ids, canonical cards, expected subject verdicts, behaviour labels).  It is never imported by
      schema.py, judge.py or codec.py, and the judge never receives anything from it.  It does not import them either: its verdict vocabulary and
      scope labels are re-declared here so that a drift between judge and oracle is detectable instead of shared.
    * It checks a J1 OUTPUT dict against a PRIVATE expectation.  It never recomputes the subject verdict from the judge's logic.

TWO KINDS OF RESULT -- NEVER MIXED
    * inline_check_verdict  : a NON-FORMAL demonstration check ("did the detector answer as predeclared on THIS in-memory input?").  It exists so that
                              small illustrative unit tests can be written.  It is not an acceptance result and may never be summed into one.
    * test_acceptance_verdict (formal): UNCONDITIONALLY BLOCKED / NOT_READY in this stage.  A formal acceptance PASS needs (a) materialised, independently
                              sealed Lane S / Lane O fixture bytes, (b) an independently implemented attestation verifier, (c) a reviewed CPU guard and
                              runner, (d) a frozen criteria set, (e) an authenticated origin of the trust map.  None of these exists; no Python
                              object, dataclass, private attribute or caller-supplied dictionary can stand in for them (that would be a fiction, not
                              a seal).  FORMAL_ACCEPTANCE_READY is therefore a constant False; flipping it is a reviewed, owner-authorised change.

INPUT VALIDITY IS NOT A SUBJECT VERDICT
    * A J1 output with input_valid != True, result_kind != "SUBJECT_VERDICT", any input diagnostic, or an INPUT_INVALID basis code is a BROKEN TEST
      INSTRUMENT, never a "matching BLOCKED".  inline_check_verdict is BLOCKED for it and no expected verdict can turn that into PASS.

EXPECTATIONS ARE PINNED
    * A private expectation must equal the versioned V0.1 inventory tuple (fixture_id, canonical_card, assertion_id, expected_subject_verdict).  The
      inventory is a DRAFT, not frozen, and is not fixture data: no S/O bytes, hashes or run results exist.  The 18 expected verdicts are the V0.1
      document values and are NOT changed by this correction.  There is no parameter that can shrink or replace the 18-id set.
"""
import re

SCOPE = "SYNTHETIC_CPU_ONLY"
MEASUREMENT_TARGET = "J1_SYNTHETIC_DETECTOR"
NATIVE_B0_SAFETY_STATUS = "NOT_EVALUATED_BY_J1"
GROK_REVIEW_STATE = "DEFERRED_NOT_PERFORMED"
INVENTORY_VERSION = "J1-SPEC-V0.1-DRAFT-18-NOT-FROZEN"
FORMAL_ACCEPTANCE_READY = False
NOT_READY_REASONS = (
    "NO_MATERIALIZED_SEALED_FIXTURE_S_O_BYTES",
    "NO_INDEPENDENT_ATTESTATION_VERIFIER_IMPLEMENTED",
    "NO_REVIEWED_CPU_GUARD_OR_RUNNER",
    "G2_CRITERIA_NOT_FROZEN",
    "TRUST_MAP_ORIGIN_NOT_AUTHENTICATED",
)

VERDICTS = ("PASS", "FAIL", "BLOCKED")
EVIDENCE_SENSITIVE = ("ATTRIBUTION", "UNIQUE_REGISTRY", "ZOMBIE_AT_T", "LOG_MATCHES_SEAL", "WRITE_COMPLETE")
SMOKE_ONLY = ("PREVENT_PROOF", "LAWFUL_REAP", "EVIDENCE_USABLE", "DELIVERY")

_FIXTURE_ID_RE = re.compile(r"^J1-F0[1-6]-[A-D]$")
_REQUIRED_OUTPUT_KEYS = ("assertion_id", "subject_verdict", "input_valid", "result_kind", "input_diagnostics", "evidence_basis_codes",
                         "supporting_observable_refs", "coverage", "measurement_target", "native_B0_safety_status", "scope")

# fixture id -> (canonical card, assertion, expected subject verdict).  V0.1 document inventory; NOT frozen; NOT fixture data.  UNCHANGED by the
# correction: the 18 predeclared expected verdicts are the historical V0.1 values.
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
    for assertion in EVIDENCE_SENSITIVE:
        seen = {e for (_c, a, e) in SPEC_V0_1_INVENTORY.values() if a == assertion}
        if len(seen) < 2:
            problems.append("discriminative assertion has no contrasting expected outcome")
    return problems


def validate_private_expectation(exp):
    """Strict check of one PRIVATE expectation record, PINNED to the versioned inventory.  -> list of problems (empty = usable).
    An unusable or altered expectation makes the case BLOCKED (spec / instrument not ready), never a subject FAIL and never a PASS."""
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
    if type(exp["assertion_id"]) is not str or exp["assertion_id"] not in EVIDENCE_SENSITIVE + SMOKE_ONLY:
        problems.append("expectation: unknown assertion_id")
    if type(exp["expected_subject_verdict"]) is not str or exp["expected_subject_verdict"] not in VERDICTS:
        problems.append("expectation: unknown expected_subject_verdict")
    elif exp["assertion_id"] in SMOKE_ONLY and exp["expected_subject_verdict"] == "PASS":
        problems.append("expectation: a SMOKE_ONLY assertion may not expect PASS in V0.1")
    if problems:
        return problems
    pinned = SPEC_V0_1_INVENTORY.get(exp["fixture_id"])
    if pinned is None:
        problems.append("expectation: fixture_id is not in the versioned V0.1 inventory")
    elif pinned != (exp["canonical_card"], exp["assertion_id"], exp["expected_subject_verdict"]):
        problems.append("expectation: tuple differs from the versioned V0.1 inventory (altered expectation)")
    return problems


def _output_problems(out):
    """Shape and validity of a J1 output.  Any problem here is an INSTRUMENT problem: the case cannot be accepted, whatever the verdict says."""
    if type(out) is not dict:
        return ["J1 output is not a dict"]
    for k in _REQUIRED_OUTPUT_KEYS:
        if k not in out:
            return ["J1 output lacks a required key"]
    p = []
    if out["input_valid"] is not True or out["result_kind"] != "SUBJECT_VERDICT":
        p.append("J1 reported an invalid input (INPUT_INVALID): the fixture is broken, a matching BLOCKED is not an acceptance")
    if not isinstance(out["input_diagnostics"], list) or out["input_diagnostics"]:
        p.append("J1 output carries input diagnostics")
    if out["subject_verdict"] not in VERDICTS:
        p.append("J1 output has no usable subject_verdict")
    codes = out["evidence_basis_codes"]
    if not isinstance(codes, list) or not codes or not all(type(c) is str and c for c in codes):
        p.append("J1 output evidence_basis_codes is not a non-empty list of non-empty strings")
    elif "INPUT_INVALID" in codes:
        p.append("J1 output evidence_basis_codes contains INPUT_INVALID")
    refs = out["supporting_observable_refs"]
    if not isinstance(refs, list) or not all(type(r) is str for r in refs):
        p.append("J1 output supporting_observable_refs is not a list of strings")
    if out["measurement_target"] != MEASUREMENT_TARGET or out["native_B0_safety_status"] != NATIVE_B0_SAFETY_STATUS or out["scope"] != SCOPE:
        p.append("J1 output scope labels are missing or wrong")
    return p


def verify_fixture_attestation(attestation):
    """Placeholder for the INDEPENDENT verifier of sealed Lane S / Lane O fixture bytes and run evidence.  NOT IMPLEMENTED.
    It always returns (False, reasons): there is no authenticated custody, signature or sealed fixture in this stage, and nothing a caller can pass
    in is accepted as one.  Any future implementation is a separately reviewed, owner-authorised change."""
    return False, ["ATTESTATION_VERIFIER_NOT_IMPLEMENTED"] + list(NOT_READY_REASONS)


def grade_case(expectation, j1_output):
    """Check ONE case.  -> dict with
         inline_check_verdict      PASS | FAIL | BLOCKED   -- NON-FORMAL demonstration check only (scope NON_FORMAL_DEMONSTRATION);
         test_acceptance_verdict   BLOCKED                  -- the formal acceptance result, unconditionally NOT_READY in this stage.
      inline BLOCKED : the expectation is unusable / altered, or the J1 output reports INPUT_INVALID / diagnostics / a malformed shape (broken instrument);
      inline FAIL    : a well-formed, valid-input output whose assertion or subject verdict differs from the pinned expectation;
      inline PASS    : same assertion and subject verdict on a valid input (for a SMOKE_ONLY assertion: never a PASS verdict, and labelled SMOKE_ONLY)."""
    reasons = validate_private_expectation(expectation)
    ok_exp = type(expectation) is dict
    res = {"fixture_id": expectation.get("fixture_id") if ok_exp else None,
           "assertion_id": expectation.get("assertion_id") if ok_exp else None,
           "expected_subject_verdict": expectation.get("expected_subject_verdict") if ok_exp else None,
           "subject_verdict": None, "inline_check_verdict": "BLOCKED", "inline_check_scope": "NON_FORMAL_DEMONSTRATION",
           "test_acceptance_verdict": "BLOCKED", "acceptance_state": "NOT_READY", "acceptance_reasons": list(NOT_READY_REASONS),
           "reasons": reasons, "coverage_limit": None, "inventory_version": INVENTORY_VERSION,
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
        res["inline_check_verdict"] = "FAIL"
        res["reasons"] = ["J1 answered a different assertion than the one predeclared"]
        return res
    if smoke and j1_output["coverage"] != "SMOKE_ONLY":
        res["reasons"] = ["J1 output does not label a SMOKE_ONLY assertion as SMOKE_ONLY"]
        return res
    if smoke and j1_output["subject_verdict"] == "PASS":
        res["inline_check_verdict"] = "FAIL"
        res["reasons"] = ["a SMOKE_ONLY assertion produced PASS: an unproven PASS"]
        return res
    if j1_output["subject_verdict"] == expectation["expected_subject_verdict"]:
        res["inline_check_verdict"] = "PASS"
        res["reasons"] = ["subject verdict equals the pinned expectation (non-formal inline check only)"]
    else:
        res["inline_check_verdict"] = "FAIL"
        res["reasons"] = ["subject verdict differs from the pinned expectation"]
    return res


def aggregate(case_results):
    """Run-level FORMAL acceptance over graded cases.  UNCONDITIONALLY BLOCKED / NOT_READY in this stage.

    Caller-supplied grade dictionaries are claims, not evidence: eighteen rows saying PASS prove nothing about fixture bytes, about J1, or about who
    produced them, and no Python-level structure can be an unforgeable seal.  There is deliberately NO `expected_ids` parameter: the formal run is the
    18-id V0.1 inventory, and a different suite is a new versioned scope that needs owner review, not a keyword argument.  The diagnostics below
    (duplicate / unknown / missing ids, non-formal rows) are informational and can only ADD reasons; they can never lift the result.  No count here
    is an acceptance claim; a SMOKE_ONLY pass carries no broad accuracy claim; nothing here says anything about native B0 safety."""
    rows = list(case_results) if isinstance(case_results, (list, tuple)) else []
    ids = [r.get("fixture_id") if type(r) is dict else None for r in rows]
    expected = set(SPEC_V0_1_INVENTORY)
    reasons = list(NOT_READY_REASONS)
    if not isinstance(case_results, (list, tuple)):
        reasons.append("case_results is not a list")
    if any(i is None for i in ids):
        reasons.append("a row has no fixture_id")
    if len({i for i in ids if i is not None}) != len([i for i in ids if i is not None]):
        reasons.append("duplicate fixture ids")
    if any(i is not None and i not in expected for i in ids):
        reasons.append("unknown fixture ids")
    if expected - set(ids):
        reasons.append("%d of the 18 inventory ids are missing" % len(expected - set(ids)))
    if any(type(r) is dict and r.get("test_acceptance_verdict") not in (None, "BLOCKED") for r in rows):
        reasons.append("a row claims a formal acceptance verdict that this stage cannot grant")
    inline = [r.get("inline_check_verdict") if type(r) is dict else None for r in rows]
    return {"run_acceptance_verdict": "BLOCKED", "acceptance_state": "NOT_READY", "formal_acceptance_ready": FORMAL_ACCEPTANCE_READY,
            "reasons": reasons, "inventory_version": INVENTORY_VERSION, "rows": len(rows), "expected_cases": len(expected),
            "informational_non_formal_counts": {"PASS": inline.count("PASS"), "FAIL": inline.count("FAIL"), "BLOCKED": inline.count("BLOCKED")},
            "smoke_only_note": "SMOKE_ONLY passes carry no broad accuracy claim",
            "measurement_target": MEASUREMENT_TARGET, "native_B0_safety_status": NATIVE_B0_SAFETY_STATUS, "scope": SCOPE,
            "grok_review_state": GROK_REVIEW_STATE}
