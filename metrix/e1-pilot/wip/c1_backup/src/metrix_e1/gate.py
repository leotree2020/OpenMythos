"""Gate 0 (G0.1-G0.10), the TEST confirmation (T1-T3) and the status words of METRIX E1-PILOT.

Protocol v1.1 section 8 (Gate 0 table; "seed-average"; the notes under the table; T1-T3 and the final status) and
section 9 (the fixed status vocabulary and which reason belongs to which condition). Thresholds come from
metrix_e1.contract (parsed from the frozen protocol text). Status words are only those of section 9
(errors.STATUSES, checked against the frozen protocol by contract.load); interpretation B14 covers what section 9
leaves open for Gate 0, B24 for T1-T3, B15 the meaning of G0.8's terms.

compute_values() / compute_test_values() turn evaluation summaries into the numbers each condition reads; judge() /
judge_test() apply the thresholds. In smoke mode the conditions are computed but the status is fixed to NOT_TESTED
with the note "冒烟测试，不构成结论" (Implementation Task Order V1, section 7); preflight mode is refused.
"""
import math

from . import stats as S
from .errors import STATUSES
from .mode import SMOKE_GATE_NOTE, SMOKE_LABEL

CONDITIONS = ("G0.1", "G0.2", "G0.3", "G0.4", "G0.5", "G0.6", "G0.7", "G0.8", "G0.9", "G0.10")
REASON = {"G0.1": "IMPLEMENTATION_FAIL", "G0.2": "IMPLEMENTATION_FAIL", "G0.6": "IMPLEMENTATION_FAIL",
          "G0.7": "IMPLEMENTATION_FAIL", "G0.8": "IMPLEMENTATION_FAIL", "G0.4": "OPTIMIZATION_FAIL",
          "G0.5": "OPTIMIZATION_OR_CAPACITY_UNRESOLVED", "G0.3": None, "G0.9": None, "G0.10": None}
TEST_CONDITIONS = ("T1", "T2", "T3")
TEST_REASON = {"T1": "OPTIMIZATION_OR_CAPACITY_UNRESOLVED", "T2": "IMPLEMENTATION_FAIL", "T3": None}
RECALIBRATION_NOTE = "越过 G0.3 或 G0.9 的界限不代表机制失败:它触发 benchmark 重新校准(新协议版本)"
TOO_HARD_NOTE = "对该模型与该训练量过难"


def _word(w):
    if w is not None and w not in STATUSES:
        raise ValueError("%r is not a protocol section 9 status" % (w,))
    return w


def _in(x, iv):
    return iv[0] <= x <= iv[1]


def _judged_mode(mode):
    if mode.preflight:
        raise ValueError("preflight mode is timing only; Gate 0 and T1-T3 are not judged in it")


# ----------------------------------------------------------------------------------------- G0.8 (B15)

def repro_compare(ev1, ev2, g):
    """Two evaluations of one checkpoint. Candidate scores of DEV-QA and the TRAIN closed book may differ by at most
    g8_score_tol; predictions must be identical except for items whose top two candidates are within g8_top2_tol in
    either evaluation; general-window NLL may differ by at most g8_nll_tol."""
    max_score, bad_pred, allowed, n_items = 0.0, [], 0, 0
    for part in ("dev_qa", "train_cb"):
        a, b = ev1[part], ev2[part]
        if [(r["fact_id"], r["template_id"]) for r in a] != [(r["fact_id"], r["template_id"]) for r in b]:
            raise ValueError("the two evaluations do not cover the same items in the same order (%s)" % part)
        for x, y in zip(a, b):
            n_items += 1
            max_score = max(max_score, max(abs(p - q) for p, q in zip(x["scores"], y["scores"])))
            if x["prediction"] != y["prediction"]:
                if x["top2_gap"] <= g.g8_top2_tol or y["top2_gap"] <= g.g8_top2_tol:
                    allowed += 1
                else:
                    bad_pred.append((part, x["fact_id"], x["template_id"]))
    na, nb = ev1["general_dev"], ev2["general_dev"]
    if [(r["domain"], r["doc_id"]) for r in na] != [(r["domain"], r["doc_id"]) for r in nb]:
        raise ValueError("the two evaluations do not cover the same windows")
    max_nll = max(abs(x["nll"] - y["nll"]) for x, y in zip(na, nb))
    ok = max_score <= g.g8_score_tol and not bad_pred and max_nll <= g.g8_nll_tol
    return {"satisfied": ok, "items": n_items, "max_score_diff": max_score, "prediction_differences_allowed": allowed,
            "prediction_differences_not_allowed": bad_pred, "max_nll_diff": max_nll}


# -------------------------------------------------------------------------------------- values from evaluations

class _Ctx:
    """Fact groups, strata and seed-averages shared by the computations of one split."""

    def __init__(self, inp, contract, split):
        self.st = contract.statistics
        self.seeds = contract.training.training_seeds
        self.inp, self.split, self.label = inp, split, split.upper()
        self.grp = S.groups(inp["facts"], self.st.strata)
        self.stratum_of = {f["fact_id"]: f["stratum"] for f in inp["facts"]}
        self._avg = {}

    def scores(self, arm, seed):
        key = "scores_%s" % self.split
        if arm == "N":
            return self.inp["N"][key]
        if seed == "avg":
            if arm not in self._avg:
                self._avg[arm] = S.seed_average([self.inp[arm][s][key] for s in self.seeds])
            return self._avg[arm]
        return self.inp[arm][seed][key]

    def cmp(self, x, y, seed, group="learned", label=None):
        label = label or "%s-%s" % (x, y)
        return S.paired_bootstrap(self.scores(x, seed), self.scores(y, seed), self.grp[group], self.stratum_of, self.st,
                                  S.purpose(label, self.label, seed))


def compute_values(inp, contract):
    """Numbers read by G0.1-G0.10. `inp`:
      leakage      the Gate 0 leakage report (leakage.run_gate0)
      all_finite   True iff every loss, score and NLL used was finite; nonfinite: list of descriptions
      facts        facts.jsonl rows
      N            stats.evaluation_summary of arm N (split "dev")
      F, S, Y, L, A  {seed: stats.evaluation_summary} of the selected configuration (F, L, A) / F's configuration (S, Y)
      repro        {seed: (evaluation 1, evaluation 2)} of F's selected configuration (raw evaluate_model outputs)
    """
    c = _Ctx(inp, contract, "dev")
    st, g, learned, N = c.st, contract.gate, c.grp["learned"], inp["N"]
    v = {}
    v["G0.1"] = {"leakage_result": inp["leakage"]["result"],
                 "over_limit": sorted(k for k, x in inp["leakage"]["checks"].items() if not x["within_limit"])}
    v["G0.2"] = {"all_finite": bool(inp["all_finite"]), "nonfinite": list(inp.get("nonfinite", []))}
    v["G0.3"] = {"acc_dev_learned": float(N["acc_dev_learned"]), "acc_dev_unread": float(N["acc_dev_unread"]),
                 "acc_cb": float(N["acc_cb"])}
    for s_ in st.strata:
        v["G0.3"]["acc_dev_learned:%s" % s_] = float(N["acc_dev_learned:%s" % s_])
    v["G0.4"] = {"acc_cb_by_seed": {s: float(inp["F"][s]["acc_cb"]) for s in c.seeds}}
    v["G0.5"] = {"acc_avg": float(S.acc(c.scores("F", "avg"), learned)), "delta_avg": c.cmp("F", "N", "avg"),
                 "delta_by_seed": {s: c.cmp("F", "N", s)["point"] for s in c.seeds}}
    for cond, arm in (("G0.6", "S"), ("G0.7", "Y")):
        d = c.cmp(arm, "N", "avg")
        v[cond] = {"point": d["point"], "ci_high": d["ci_high"], "delta_avg": d}
    v["G0.8"] = {"checkpoints": {s: repro_compare(a, b, g) for s, (a, b) in inp["repro"].items()}}
    v["G0.9"] = {"acc_avg": v["G0.5"]["acc_avg"]}
    f_avg, d_avg, est = c.scores("F", "avg"), {}, {}
    for arm in ("L", "A"):
        x_avg = c.scores(arm, "avg")
        d_avg[arm] = {f: x_avg[f] - f_avg[f] for f in learned}
        est["%s-F" % arm] = S.size_estimate(d_avg[arm], learned, c.stratum_of, st, "%s-F" % arm)
    planning = max(e["n_max"] for e in est.values())
    v["G0.10"] = {"estimates": est, "planning_n": planning}
    if math.isfinite(planning):
        for arm in ("L", "A"):
            est["%s-F" % arm]["halfwidth_at_planning_n"] = S.halfwidth_check(d_avg[arm], learned, c.stratum_of, st,
                                                                              "%s-F" % arm, planning)
    return v


def compute_test_values(inp, contract):
    """Numbers read by T1-T3 (`inp` as compute_values, with summaries of split "test")."""
    c = _Ctx(inp, contract, "test")
    N = inp["N"]
    d_f = c.cmp("F", "N", "avg")
    v = {"T1": {"acc_avg": float(S.acc(c.scores("F", "avg"), c.grp["learned"])), "delta_avg": d_f}}
    v["T2"] = {}
    for arm in ("S", "Y"):
        d = c.cmp(arm, "N", "avg")
        v["T2"][arm] = {"point": d["point"], "ci_high": d["ci_high"], "delta_avg": d}
    v["T3"] = {"acc_test_learned": float(N["acc_test_learned"]), "acc_test_unread": float(N["acc_test_unread"]),
               "acc_cb": float(N["acc_cb"])}
    for s_ in c.st.strata:
        v["T3"]["acc_test_learned:%s" % s_] = float(N["acc_test_learned:%s" % s_])
    return v


# ------------------------------------------------------------------------------------------------- judge

def _g3_ranges(x, g, split):
    return (_in(x["acc_%s_learned" % split], g.g3_learned) and _in(x["acc_%s_unread" % split], g.g3_unread)
            and _in(x["acc_cb"], g.g3_cb)
            and all(_in(x[k], g.g3_stratum) for k in x if k.startswith("acc_%s_learned:" % split)))


def judge(values, contract, mode):
    """Apply G0.1-G0.10 to `values`. Returns {conditions: {G0.k: {satisfied, reason, note}}, gate0_status, reasons,
    note}. Every status word is from section 9. G0.8 needs the re-evaluation of exactly the training seeds' three
    checkpoints."""
    _judged_mode(mode)
    g = contract.gate
    v = values
    sat = {}
    sat["G0.1"] = v["G0.1"]["leakage_result"] == "PASS" and not v["G0.1"]["over_limit"]
    sat["G0.2"] = v["G0.2"]["all_finite"]
    sat["G0.3"] = _g3_ranges(v["G0.3"], g, "dev")
    sat["G0.4"] = all(a >= g.g4_cb_min for a in v["G0.4"]["acc_cb_by_seed"].values())
    x = v["G0.5"]
    sat["G0.5"] = (x["acc_avg"] >= g.g5_acc_min and x["delta_avg"]["ci_low"] > 0
                   and all(d > 0 for d in x["delta_by_seed"].values()))
    sat["G0.6"] = v["G0.6"]["point"] <= g.g6_point_max and v["G0.6"]["ci_high"] <= g.g6_upper_max
    sat["G0.7"] = v["G0.7"]["point"] <= g.g7_point_max and v["G0.7"]["ci_high"] <= g.g7_upper_max
    ck = v["G0.8"]["checkpoints"]
    sat["G0.8"] = set(ck) == set(contract.training.training_seeds) and all(c["satisfied"] for c in ck.values())
    sat["G0.9"] = v["G0.9"]["acc_avg"] <= g.g9_acc_max
    sat["G0.10"] = all(e["finite"] for e in v["G0.10"]["estimates"].values())
    conds = {}
    for c in CONDITIONS:
        reason, note = None, None
        if not sat[c]:
            reason = REASON[c]
            if c == "G0.5" and not sat["G0.4"]:
                reason = REASON["G0.4"]          # section 9: OPTIMIZATION_OR_CAPACITY_UNRESOLVED needs G0.4 satisfied
            if c == "G0.5" and v["G0.5"]["acc_avg"] < g.too_hard_below:
                note = TOO_HARD_NOTE
            if c in ("G0.3", "G0.9"):
                note = RECALIBRATION_NOTE
        conds[c] = {"satisfied": sat[c], "reason": _word(reason), "note": note}
    return _status(conds, sat, mode, "gate0_status")


def judge_test(values, gate0_status, contract, mode):
    """Apply T1-T3 (section 8, TEST confirmation, evaluated once after Gate 0). Final pilot status: PASS iff Gate 0 is
    PASS and T1-T3 all hold; otherwise PIPELINE_NOT_QUALIFIED with the section 9 reasons (B24)."""
    _judged_mode(mode)
    if not mode.smoke and gate0_status != "PASS":
        raise ValueError("T1-T3 are judged only after Gate 0 PASS (got %r)" % (gate0_status,))
    g = contract.gate
    v = values
    sat = {"T1": v["T1"]["acc_avg"] >= g.t1_acc_min and v["T1"]["delta_avg"]["ci_low"] > 0,
           "T2": (v["T2"]["S"]["point"] <= g.g6_point_max and v["T2"]["S"]["ci_high"] <= g.g6_upper_max
                  and v["T2"]["Y"]["point"] <= g.g7_point_max and v["T2"]["Y"]["ci_high"] <= g.g7_upper_max),
           "T3": _g3_ranges(v["T3"], g, "test")}
    conds = {c: {"satisfied": sat[c], "reason": _word(None if sat[c] else TEST_REASON[c]),
                 "note": RECALIBRATION_NOTE if c == "T3" and not sat[c] else None} for c in TEST_CONDITIONS}
    return _status(conds, sat, mode, "final_status")


def _status(conds, sat, mode, key):
    if mode.smoke:
        # Implementation Task Order V1 section 7: computed as usual, status fixed to NOT_TESTED; no reason word and
        # no computed status leave smoke mode (the satisfied flags are smoke values).
        for c in conds.values():
            c["reason"] = None
        return {"conditions": conds, key: _word("NOT_TESTED"), "reasons": [], "note": SMOKE_GATE_NOTE,
                "label": SMOKE_LABEL}
    reasons = sorted({c["reason"] for c in conds.values() if c["reason"]})
    status = "PASS" if all(sat.values()) else "PIPELINE_NOT_QUALIFIED"
    return {"conditions": conds, key: _word(status), "reasons": [_word(r) for r in reasons], "note": None}


# ------------------------------------------------------------------------------- section 6 comparisons (report)

COMPARISONS = (("F", "N"), ("L", "F"), ("A", "F"), ("S", "N"), ("Y", "N"))


def report_comparisons(inp, contract, split="dev"):
    """Section 6 comparisons, reported (not judged): every training seed and the seed-average, with the paired
    stratified bootstrap. Delta(F-N), Delta(L-F), Delta(A-F), Delta(S-N), Delta(Y-N) on learned facts; Spill(arm) =
    Acc(arm, unread) - Prior on unread facts (purpose 'Spill-<arm>:<split>:<seed>', B12). `inp` as compute_values()."""
    c = _Ctx(inp, contract, split)
    out = {}
    for seed in list(c.seeds) + ["avg"]:
        for x, y in COMPARISONS:
            out["%s-%s:%s" % (x, y, seed)] = c.cmp(x, y, seed)
        for arm in ("F", "L", "A", "S", "Y"):
            out["Spill-%s:%s" % (arm, seed)] = c.cmp(arm, "N", seed, group="unread", label="Spill-%s" % arm)
    return out
