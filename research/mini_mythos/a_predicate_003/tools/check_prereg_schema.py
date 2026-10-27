#!/usr/bin/env python3
"""Pure-JSON schema + consistency check of e1_provability_table_v1.json.  Reads files only; starts nothing.
It independently RE-DERIVES the classification table from scenario defects and candidate ECDs and compares it with the frozen table."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "prereg", "e1_provability_table_v1.json")
TOP = ["prereg_id", "schema_version", "experiment", "base_commit", "frozen_scope", "not_frozen", "authorization", "global_parameters",
       "environment_expectation", "candidate_code_pins", "frozen_reference_hashes", "state_vocabulary", "s0_checks", "proof_rules",
       "candidates", "plan_mapping", "scenarios", "classification", "bench_unverifiable_conditions", "independent_truth", "verdict_function",
       "repetitions", "bench_validity_checks", "pass_fail_blocked", "safety_boundaries", "cleanup_procedure", "evidence_outputs",
       "known_limitations", "amendment_policy", "execution_interlock", "setup_phase", "correction_log", "status"]


def main():
    bad = []
    raw = open(PATH, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    side = open(PATH + ".sha256").read().split()[0]
    if side != sha:
        bad.append("sidecar hash %s != file hash %s" % (side, sha))
    d = json.loads(raw)
    for k in TOP:
        if k not in d:
            bad.append("missing top-level key %s" % k)
    gp = d["global_parameters"]
    if (gp["w1_w2_nominal_unexpected_unknown_target"], gp["bench_blocked_fraction_max_per_cell"], gp["min_valid_trials_per_cell_E1D"], gp["primary_python"],
            gp["stress_5000_allowed"], gp["cpu_only"], gp["gpu_allowed"]) != (0, 0.05, 50, "3.13.16", False, True, False):
        bad.append("global parameters differ from the owner-approved preparation parameters")
    if d["authorization"]["execution_authorized"] is not False:
        bad.append("execution_authorized must be false")
    for k in ("E1-B", "E1-C", "E1-D"):
        if not str(d["not_frozen"].get(k, "")).startswith("PENDING"):
            bad.append("%s must be pending/unfrozen" % k)
    checks, rules, cands, scn, cls = d["s0_checks"], d["proof_rules"], d["candidates"], d["scenarios"], d["classification"]
    for cid, c in checks.items():
        if c["rule"] not in rules:
            bad.append("check %s cites unknown rule %s" % (cid, c["rule"]))
    for cname, c in cands.items():
        for r in c["ecd_rules"]:
            if r not in rules:
                bad.append("%s ECD cites unknown rule %s" % (cname, r))
    if sorted(cands) != ["P0", "P1", "P2", "P3", "P4"]:
        bad.append("candidate set")
    if len(scn) != 12 or sorted(cls) != sorted(scn):
        bad.append("scenario/classification coverage")
    # independent re-derivation
    for s, sc in scn.items():
        for cname in ("P0", "P1", "P2"):
            cell = cls[s][cname]
            D = set(sc["defects"])
            for x in D:
                if x not in checks:
                    bad.append("%s: unknown defect %s" % (s, x))
            prov = {x for x in D if checks[x]["rule"] in cands[cname]["ecd_rules"]}
            if not D:
                want = ("PROVABLE", "ACCEPT")
            elif not prov:
                want = ("UNPROVABLE", "REFUSE_ANY")
            else:
                want = ("PROVABLE", "BLOCKED")
            if (cell["class"], cell["expected_s0_verdict"]) != want:
                bad.append("%s/%s: class/verdict %s != re-derived %s" % (s, cname, (cell["class"], cell["expected_s0_verdict"]), want))
            if want[1] == "BLOCKED":
                if cname == "P2":
                    codes = sorted({checks[x]["code_p2"] for x in D})
                    need = sorted({checks[x]["rule"] for x in D})
                else:
                    codes, need = set(), set()
                    for x in prov:
                        if x in ("C1", "C2"):
                            codes.add("STAGE_SESSION_NOT_DEDICATED")
                            need.add(checks[x]["rule"])
                        elif x == "C6":
                            codes.add("ROOT_FINGERPRINT_MISMATCH")
                            need.add("PR-S0-6")
                        elif x == "C8":
                            codes.add("PREFLIGHT_FAILED")
                            need.add("PR-S0-8")
                    codes, need = sorted(codes), sorted(need)
                if cell["expected_codes"] != codes or cell["cited_rules_required"] != need:
                    bad.append("%s/%s: codes/rules %s %s != re-derived %s %s" % (s, cname, cell["expected_codes"], cell["cited_rules_required"], codes, need))
                if not set(codes) <= set(cands[cname]["code_vocabulary"]):
                    bad.append("%s/%s: expected code outside candidate vocabulary" % (s, cname))
                if not set(need) <= set(cands[cname]["ecd_rules"]):
                    bad.append("%s/%s: cited rule outside ECD" % (s, cname))
        for cname in ("P3", "P4"):
            if cls[s][cname]["class"] != "NOT_CLASSIFIED":
                bad.append("%s/%s must be NOT_CLASSIFIED" % (s, cname))
        if sc["evidence_kind"] not in ("REAL_KERNEL", "SIMULATED"):
            bad.append("%s evidence_kind" % s)
    rp = d["repetitions"]["planned_trials"]
    if rp["total"] != rp["deterministic"] + rp["false_reject_sweep"] or rp["deterministic"] != 36 * d["repetitions"]["deterministic_per_cell"]:
        bad.append("planned trial arithmetic")
    if set(d["bench_validity_checks"]["checks"]) != {"BV-%d" % i for i in range(1, 11)}:
        bad.append("BV-1..BV-10 incomplete")
    ids = [c["id"] for c in d["correction_log"]]
    if ids != ["PREP-CORR-1", "PREP-CORR-2"]:
        bad.append("correction log %r" % ids)
    print(json.dumps({"sha256": sha, "problems": bad, "ok": not bad}, indent=1))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
