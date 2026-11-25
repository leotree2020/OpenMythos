"""Implementation Task Order V1, section 6 item 7: gate.py with artificial inputs: every G0 condition both satisfied
and not satisfied; the status words come only from protocol section 9; smoke mode fixes the status to NOT_TESTED.
Thresholds are the contract's (parsed from the frozen protocol); the boundary cases use those numbers."""
import copy
import math

import pytest

from metrix_e1 import gate as G
from metrix_e1 import mode as M
from metrix_e1.errors import STATUSES

SEEDS = (101, 202, 303)


def passing(c):
    g = c.gate
    mid = lambda iv: (iv[0] + iv[1]) / 2                       # noqa: E731
    return {
        "G0.1": {"leakage_result": "PASS", "over_limit": []},
        "G0.2": {"all_finite": True, "nonfinite": []},
        "G0.3": {"acc_dev_learned": mid(g.g3_learned), "acc_dev_unread": mid(g.g3_unread), "acc_cb": mid(g.g3_cb),
                 "acc_dev_learned:natural": mid(g.g3_stratum), "acc_dev_learned:random": mid(g.g3_stratum)},
        "G0.4": {"acc_cb_by_seed": {s: g.g4_cb_min for s in SEEDS}},
        "G0.5": {"acc_avg": g.g5_acc_min, "delta_avg": {"ci_low": 0.01}, "delta_by_seed": {s: 0.3 for s in SEEDS}},
        "G0.6": {"point": g.g6_point_max, "ci_high": g.g6_upper_max},
        "G0.7": {"point": g.g7_point_max, "ci_high": g.g7_upper_max},
        "G0.8": {"checkpoints": {s: {"satisfied": True} for s in SEEDS}},
        "G0.9": {"acc_avg": g.g9_acc_max},
        "G0.10": {"estimates": {"L-F": {"finite": True}, "A-F": {"finite": True}}, "planning_n": 200},
    }


def failing_variants(c):
    g = c.gate
    eps = 1e-9
    out = {
        "G0.1": [("leakage_result", "FAIL"), ("over_limit", ["L4"])],
        "G0.2": [("all_finite", False)],
        "G0.3": [("acc_dev_learned", g.g3_learned[0] - eps), ("acc_dev_learned", g.g3_learned[1] + eps),
                 ("acc_dev_unread", g.g3_unread[1] + eps), ("acc_cb", g.g3_cb[0] - eps),
                 ("acc_dev_learned:random", g.g3_stratum[0] - eps)],
        "G0.4": [("acc_cb_by_seed", {101: 1.0, 202: g.g4_cb_min - eps, 303: 1.0})],
        "G0.5": [("acc_avg", g.g5_acc_min - eps), ("delta_avg", {"ci_low": 0.0}),
                 ("delta_by_seed", {101: 0.2, 202: 0.0, 303: 0.2})],
        "G0.6": [("point", g.g6_point_max + eps), ("ci_high", g.g6_upper_max + eps)],
        "G0.7": [("point", g.g7_point_max + eps), ("ci_high", g.g7_upper_max + eps)],
        "G0.8": [("checkpoints", {101: {"satisfied": True}, 202: {"satisfied": False}, 303: {"satisfied": True}}),
                 ("checkpoints", {}),
                 ("checkpoints", {101: {"satisfied": True}, 202: {"satisfied": True}}),      # only 2 of the 3
                 ("checkpoints", {101: {"satisfied": True}, 202: {"satisfied": True}, 404: {"satisfied": True}})],
        "G0.9": [("acc_avg", g.g9_acc_max + eps)],
        "G0.10": [("estimates", {"L-F": {"finite": True}, "A-F": {"finite": False}})],
    }
    return out


def _words(res):
    words = [res["gate0_status"]] + list(res["reasons"]) + [x["reason"] for x in res["conditions"].values()]
    return [w for w in words if w is not None]


def test_all_satisfied_at_the_boundaries_is_pass(contract):
    res = G.judge(passing(contract), contract, M.FORMAL_MODE)
    assert all(x["satisfied"] for x in res["conditions"].values())
    assert res["gate0_status"] == "PASS" and res["reasons"] == []
    assert set(res["conditions"]) == set(G.CONDITIONS) and len(G.CONDITIONS) == 10


@pytest.mark.parametrize("cond", G.CONDITIONS)
def test_each_condition_not_satisfied(contract, cond):
    for key, val in failing_variants(contract)[cond]:
        v = passing(contract)
        v[cond] = dict(v[cond], **{key: val})
        res = G.judge(v, contract, M.FORMAL_MODE)
        assert [c for c, x in res["conditions"].items() if not x["satisfied"]] == [cond], (cond, key, val)
        assert res["gate0_status"] == "PIPELINE_NOT_QUALIFIED"
        assert res["conditions"][cond]["reason"] == G.REASON[cond]
        assert all(w in STATUSES for w in _words(res))


def test_g03_endpoints_are_inside(contract):
    g = contract.gate
    for side in (0, 1):
        v = passing(contract)
        v["G0.3"] = {"acc_dev_learned": g.g3_learned[side], "acc_dev_unread": g.g3_unread[side], "acc_cb": g.g3_cb[side],
                     "acc_dev_learned:natural": g.g3_stratum[side], "acc_dev_learned:random": g.g3_stratum[side]}
        assert G.judge(v, contract, M.FORMAL_MODE)["conditions"]["G0.3"]["satisfied"]


def test_preflight_mode_is_not_judged(contract):
    with pytest.raises(ValueError):
        G.judge(passing(contract), contract, M.preflight_mode(contract))
    with pytest.raises(ValueError):
        G.judge_test(passing_test(contract), "PASS", contract, M.preflight_mode(contract))


def test_reasons_follow_section_9(contract):
    assert {c for c, r in G.REASON.items() if r == "IMPLEMENTATION_FAIL"} == {"G0.1", "G0.2", "G0.6", "G0.7", "G0.8"}
    assert G.REASON["G0.4"] == "OPTIMIZATION_FAIL"
    assert G.REASON["G0.5"] == "OPTIMIZATION_OR_CAPACITY_UNRESOLVED"
    v = passing(contract)
    v["G0.4"]["acc_cb_by_seed"][202] = 0.5
    v["G0.5"]["acc_avg"] = 0.3
    res = G.judge(v, contract, M.FORMAL_MODE)
    assert res["conditions"]["G0.5"]["reason"] == "OPTIMIZATION_FAIL"         # G0.4 not satisfied
    assert res["conditions"]["G0.5"]["note"] == G.TOO_HARD_NOTE               # seed-average < 0.40
    v = passing(contract)
    v["G0.3"]["acc_cb"] = 0.9
    v["G0.9"]["acc_avg"] = 0.99
    res = G.judge(v, contract, M.FORMAL_MODE)
    for c in ("G0.3", "G0.9"):          # B14 as ruled by Review Gate 2026-11-24: reason null, note '需重新校准'
        assert res["conditions"][c] == {"satisfied": False, "reason": None, "note": "需重新校准"}
    assert G.RECALIBRATION_NOTE == "需重新校准"


def test_smoke_mode_status_is_not_tested(contract):
    for v in (passing(contract), dict(passing(contract), **{"G0.2": {"all_finite": False}})):
        res = G.judge(v, contract, M.smoke_mode(3))
        assert res["gate0_status"] == "NOT_TESTED"
        assert res["note"] == M.SMOKE_GATE_NOTE and res["label"] == M.SMOKE_LABEL
        assert res["reasons"] == [] and all(x["reason"] is None for x in res["conditions"].values())
        assert "PASS" not in _words(res)


def test_unknown_status_word_is_refused():
    with pytest.raises(ValueError):
        G._word("QUALIFIED")


# --------------------------------------------------------------------------------------------------- G0.8 (B15)

def _ev(scores_qa, nll):
    rows = [{"fact_id": "f%d" % i, "template_id": "t", "scores": s, "prediction": None, "top2_gap": None}
            for i, s in enumerate(scores_qa)]
    for r in rows:
        srt = sorted(r["scores"], reverse=True)
        r["top2_gap"] = srt[0] - srt[1]
        top = [i for i, x in enumerate(r["scores"]) if x == srt[0]]
        r["prediction"] = top[0] if len(top) == 1 else "tie"
    return {"dev_qa": rows, "train_cb": copy.deepcopy(rows),
            "general_dev": [{"domain": "d", "doc_id": i, "nll": x} for i, x in enumerate(nll)]}


def test_repro_compare(contract):
    g = contract.gate
    a = _ev([[-1.0, -2.0, -3.0, -4.0], [-1.0, -1.00005, -3.0, -4.0]], [3.0, 4.0])
    same = G.repro_compare(a, copy.deepcopy(a), g)
    assert same["satisfied"] and same["max_score_diff"] == 0 and same["max_nll_diff"] == 0
    # second item: top two within 1e-4 -> its prediction may flip
    b = _ev([[-1.0, -2.0, -3.0, -4.0], [-1.00006, -1.0, -3.0, -4.0]], [3.0, 4.0])
    r = G.repro_compare(a, b, g)
    assert r["satisfied"] and r["prediction_differences_allowed"] == 2           # dev_qa and train_cb copies
    # a score difference above the tolerance
    c = _ev([[-1.0, -2.0, -3.0, -4.0 + 2e-4], [-1.0, -1.00005, -3.0, -4.0]], [3.0, 4.0])
    assert not G.repro_compare(a, c, g)["satisfied"]
    # NLL difference above 1e-5
    d = _ev([[-1.0, -2.0, -3.0, -4.0], [-1.0, -1.00005, -3.0, -4.0]], [3.0, 4.0 + 2e-5])
    assert not G.repro_compare(a, d, g)["satisfied"]
    # a prediction flip where the top two are far apart in both runs is not allowed (scores changed by > tol anyway)
    e = _ev([[-2.0, -1.0, -3.0, -4.0], [-1.0, -1.00005, -3.0, -4.0]], [3.0, 4.0])
    r = G.repro_compare(a, e, g)
    assert not r["satisfied"] and r["prediction_differences_not_allowed"]
    assert math.isclose(g.g8_score_tol, 1e-4) and math.isclose(g.g8_nll_tol, 1e-5)


# ------------------------------------------------------------------------- compute_values end to end (synthetic)

def _summary(facts, rng, p_learned, p_unread, cb):
    from fractions import Fraction
    sd = {f["fact_id"]: Fraction(rng.choice([0, 1, 2]) if rng.random() < (p_learned if f["exposure"] == "learned"
                                                                             else p_unread) else 0, 2) for f in facts}
    return {"scores_dev": sd, "acc_cb": cb}


def test_compute_values_and_comparisons(contract, data_rows):
    import random
    from metrix_e1 import stats as S
    facts = data_rows["facts.jsonl"]
    rng = random.Random(0)
    learned = [f["fact_id"] for f in facts if f["exposure"] == "learned"]
    unread = [f["fact_id"] for f in facts if f["exposure"] == "unread"]
    N = _summary(facts, rng, 0.25, 0.25, 0.25)
    from fractions import Fraction
    N.update({"acc_dev_learned": S.acc(N["scores_dev"], learned), "acc_dev_unread": S.acc(N["scores_dev"], unread),
              "acc_dev_learned:natural": Fraction(1, 4), "acc_dev_learned:random": Fraction(1, 4)})
    inp = {"facts": facts, "N": N, "all_finite": True,
           "leakage": {"result": "PASS", "checks": {"L1": {"within_limit": True}}}}
    for arm, pl in (("F", 0.95), ("L", 0.9), ("A", 0.9), ("S", 0.25), ("Y", 0.25)):
        inp[arm] = {s: _summary(facts, rng, pl, 0.25, 0.97) for s in SEEDS}
    ev = _ev([[-1.0, -2.0, -3.0, -4.0]], [3.0])
    inp["repro"] = {s: (ev, copy.deepcopy(ev)) for s in SEEDS}
    v = G.compute_values(inp, contract)
    assert set(v) == set(G.CONDITIONS)
    f_avg = S.seed_average([inp["F"][s]["scores_dev"] for s in SEEDS])
    assert v["G0.5"]["acc_avg"] == float(S.acc(f_avg, learned))
    assert v["G0.5"]["delta_avg"]["purpose"] == "F-N:DEV:avg"
    assert set(v["G0.5"]["delta_by_seed"]) == set(SEEDS)
    assert v["G0.10"]["planning_n"] == max(e["n_max"] for e in v["G0.10"]["estimates"].values())
    assert "halfwidth_at_planning_n" in v["G0.10"]["estimates"]["L-F"]
    res = G.judge(v, contract, M.FORMAL_MODE)
    assert res["gate0_status"] in STATUSES
    rep = G.report_comparisons(inp, contract)
    assert len(rep) == 4 * (5 + 5)
    assert rep["Spill-F:101"]["n_facts"] == 40 and rep["L-F:avg"]["n_facts"] == 120
    assert rep["F-N:avg"] == v["G0.5"]["delta_avg"]


# --------------------------------------------------------------------------------------------- T1-T3 (B24)

def passing_test(c):
    g = c.gate
    return {"T1": {"acc_avg": g.t1_acc_min, "delta_avg": {"ci_low": 0.01}},
            "T2": {"S": {"point": g.g6_point_max, "ci_high": g.g6_upper_max},
                   "Y": {"point": g.g7_point_max, "ci_high": g.g7_upper_max}},
            "T3": {"acc_test_learned": g.g3_learned[0], "acc_test_unread": g.g3_unread[1], "acc_cb": g.g3_cb[0],
                   "acc_test_learned:natural": g.g3_stratum[0], "acc_test_learned:random": g.g3_stratum[1]}}


def test_t1_t3(contract):
    g = contract.gate
    res = G.judge_test(passing_test(contract), "PASS", contract, M.FORMAL_MODE)
    assert res["final_status"] == "PASS" and all(x["satisfied"] for x in res["conditions"].values())
    eps = 1e-9
    cases = [("T1", lambda v: v["T1"].update(acc_avg=g.t1_acc_min - eps), "OPTIMIZATION_OR_CAPACITY_UNRESOLVED"),
             ("T1", lambda v: v["T1"].update(delta_avg={"ci_low": 0.0}), "OPTIMIZATION_OR_CAPACITY_UNRESOLVED"),
             ("T2", lambda v: v["T2"]["S"].update(point=g.g6_point_max + eps), "IMPLEMENTATION_FAIL"),
             ("T2", lambda v: v["T2"]["Y"].update(ci_high=g.g7_upper_max + eps), "IMPLEMENTATION_FAIL"),
             ("T3", lambda v: v["T3"].update(acc_test_unread=g.g3_unread[1] + eps), None),
             ("T3", lambda v: v["T3"].update(**{"acc_test_learned:random": g.g3_stratum[0] - eps}), None)]
    for cond, change, reason in cases:
        v = passing_test(contract)
        change(v)
        res = G.judge_test(v, "PASS", contract, M.FORMAL_MODE)
        assert [c for c, x in res["conditions"].items() if not x["satisfied"]] == [cond]
        assert res["final_status"] == "PIPELINE_NOT_QUALIFIED" and res["conditions"][cond]["reason"] == reason
        assert all(w in STATUSES for w in _words_final(res))
    with pytest.raises(ValueError):
        G.judge_test(passing_test(contract), "PIPELINE_NOT_QUALIFIED", contract, M.FORMAL_MODE)
    smoke = G.judge_test(passing_test(contract), "NOT_TESTED", contract, M.smoke_mode(3))
    assert smoke["final_status"] == "NOT_TESTED" and smoke["reasons"] == []


def _words_final(res):
    return [w for w in [res["final_status"]] + res["reasons"] + [x["reason"] for x in res["conditions"].values()] if w]


def test_compute_test_values(contract, data_rows):
    import random
    from fractions import Fraction
    from metrix_e1 import stats as S
    facts = data_rows["facts.jsonl"]
    rng = random.Random(1)
    learned = [f["fact_id"] for f in facts if f["exposure"] == "learned"]
    unread = [f["fact_id"] for f in facts if f["exposure"] == "unread"]

    def summ(p):
        return {"scores_test": {f["fact_id"]: Fraction(int(rng.random() < p), 1) for f in facts}, "acc_cb": Fraction(1, 4)}
    N = summ(0.25)
    N.update({"acc_test_learned": S.acc(N["scores_test"], learned), "acc_test_unread": S.acc(N["scores_test"], unread),
              "acc_test_learned:natural": Fraction(1, 4), "acc_test_learned:random": Fraction(1, 4)})
    inp = {"facts": facts, "N": N}
    for arm, p in (("F", 0.9), ("S", 0.25), ("Y", 0.25)):
        inp[arm] = {s: summ(p) for s in SEEDS}
    v = G.compute_test_values(inp, contract)
    assert v["T1"]["delta_avg"]["purpose"] == "F-N:TEST:avg"
    assert v["T2"]["S"]["delta_avg"]["purpose"] == "S-N:TEST:avg"
    assert v["T3"]["acc_test_learned"] == float(N["acc_test_learned"])
    assert G.judge_test(v, "PASS", contract, M.FORMAL_MODE)["final_status"] in STATUSES
