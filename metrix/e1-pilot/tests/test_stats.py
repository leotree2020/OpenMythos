"""Implementation Task Order V1, section 6 item 3: a tie is wrong; aggregation is the mean; the bootstrap unit is
the fact (protocol v1.1 sections 5 and 6)."""
import math
from fractions import Fraction

import torch

from conftest import tiny_model
from metrix_e1 import evaluate as E
from metrix_e1 import frozen as FZ
from metrix_e1 import stats as S


# ------------------------------------------------------------------------------------------------------ ties

def test_tie_with_the_true_answer_is_wrong():
    assert E._judge([-1.0, -1.0, -2.0, -3.0], 0) == (False, "tie")
    assert E._judge([-1.0, -2.0, -1.0, -3.0], 0) == (False, "tie")
    assert E._judge([-3.0, -2.0, -2.0, -1.0], 3) == (True, 3)
    assert E._judge([-3.0, -2.0, -2.0, -1.0], 1) == (False, 3)


def test_all_candidates_tied_gives_accuracy_zero(tok, data_rows, fz, contract):
    """A model whose logits are all 0 gives every candidate of a fact the same score (equal K within the fact):
    every question is a tie, so every answer is wrong and Acc = 0 (not the 0.25 a random tie-break would give)."""
    m = tiny_model()
    with torch.no_grad():
        m.model.embed_tokens.weight.zero_()          # tied with lm_head: every logit is 0
    rows = E.score_qa(m, tok, data_rows["dev_qa.jsonl"][:40], data_rows["candidates.json"], data_rows["facts.jsonl"],
                      contract.evaluation, "cpu", batch_size=40)
    assert all(len(set(r["scores"])) == 1 for r in rows)
    assert all(r["correct"] is False and r["prediction"] == "tie" for r in rows)
    sc = S.fact_scores(rows)
    assert S.acc(sc, sorted(sc)) == 0


# ------------------------------------------------------------------------------------------------ aggregation

def test_fact_score_is_the_mean_over_questions_and_acc_the_mean_over_facts():
    rows = [{"fact_id": "a", "correct": True}, {"fact_id": "a", "correct": False},
            {"fact_id": "b", "correct": True}, {"fact_id": "b", "correct": True},
            {"fact_id": "c", "correct": False}, {"fact_id": "c", "correct": False}, {"fact_id": "c", "correct": True}]
    sc = S.fact_scores(rows)
    assert sc == {"a": Fraction(1, 2), "b": Fraction(1), "c": Fraction(1, 3)}
    assert S.acc(sc, ["a", "b", "c"]) == (Fraction(1, 2) + 1 + Fraction(1, 3)) / 3
    # not the pooled question-level rate (4/7)
    assert S.acc(sc, ["a", "b", "c"]) != Fraction(4, 7)
    assert S.all_correct(rows) == {"a": 0, "b": 1, "c": 0}


def test_seed_average_is_the_per_fact_mean():
    a = {"x": Fraction(1), "y": Fraction(0)}
    b = {"x": Fraction(1, 2), "y": Fraction(1)}
    c = {"x": Fraction(0), "y": Fraction(1)}
    assert S.seed_average([a, b, c]) == {"x": Fraction(1, 2), "y": Fraction(2, 3)}


# --------------------------------------------------------------------------------------------- bootstrap unit

def _facts(n_per_stratum=60):
    out = []
    for st in ("natural", "random"):
        out += [{"fact_id": "%s-%02d" % (st, i), "stratum": st, "exposure": "learned"} for i in range(n_per_stratum)]
    return out


def test_bootstrap_resamples_facts_within_strata(contract):
    st = contract.statistics
    facts = _facts()
    ids = [f["fact_id"] for f in facts]
    stratum_of = {f["fact_id"]: f["stratum"] for f in facts}
    x = {f: Fraction((i * 7) % 3, 2) for i, f in enumerate(ids)}
    y = {f: Fraction((i * 5) % 2, 2) for i, f in enumerate(ids)}
    res = S.paired_bootstrap(x, y, ids, stratum_of, st, S.purpose("F-N", "DEV", 101))
    assert res["n_facts"] == 120 and res["n_per_stratum"] == {"natural": 60, "random": 60}
    assert res["replicates"] == st.n_boot == 10000
    # independent re-implementation over the 120 fact-level differences, same generator and call order (B10, B11)
    d = {f: float(x[f] - y[f]) for f in ids}
    r = FZ.rng_rule(st.bootstrap_seed, "F-N:DEV:101")
    nat = [d[f] for f in ids if stratum_of[f] == "natural"]
    rnd = [d[f] for f in ids if stratum_of[f] == "random"]
    reps = sorted((sum(r.choices(nat, k=60)) + sum(r.choices(rnd, k=60))) / 120 for _ in range(st.n_boot))
    lo_pos, hi_pos = (st.n_boot - 1) * 0.025, (st.n_boot - 1) * 0.975
    lo = reps[int(lo_pos)] + (reps[int(lo_pos) + 1] - reps[int(lo_pos)]) * (lo_pos - int(lo_pos))
    hi = reps[int(hi_pos)] + (reps[int(hi_pos) + 1] - reps[int(hi_pos)]) * (hi_pos - int(hi_pos))
    assert math.isclose(res["ci_low"], lo, rel_tol=0, abs_tol=1e-15)
    assert math.isclose(res["ci_high"], hi, rel_tol=0, abs_tol=1e-15)
    assert res["point"] == float(sum(x[f] - y[f] for f in ids) / 120)


def test_bootstrap_does_not_depend_on_the_number_of_questions(contract):
    """The question rows are aggregated to one score per fact before resampling: four questions per fact with the
    same outcomes as two give the same fact scores and exactly the same CI (questions are not the unit)."""
    st = contract.statistics
    facts = _facts()
    ids = [f["fact_id"] for f in facts]
    stratum_of = {f["fact_id"]: f["stratum"] for f in facts}
    two = [{"fact_id": f, "correct": c} for i, f in enumerate(ids) for c in ((i % 3 == 0), (i % 2 == 0))]
    four = [{"fact_id": f, "correct": c} for i, f in enumerate(ids) for c in ((i % 3 == 0), (i % 2 == 0)) * 2]
    base = {f: Fraction(1, 4) for f in ids}
    r2 = S.paired_bootstrap(S.fact_scores(two), base, ids, stratum_of, st, "X-N:DEV:avg")
    r4 = S.paired_bootstrap(S.fact_scores(four), base, ids, stratum_of, st, "X-N:DEV:avg")
    assert r2 == r4


def test_percentile_linear_interpolation():
    v = list(range(10001))
    assert S.percentile(v, 2.5) == 250.0 and S.percentile(v, 97.5) == 9750.0
    assert S.percentile([0.0, 1.0], 50) == 0.5


def test_dnll_is_mean_over_domains_of_window_means():
    n = [{"domain": "a", "doc_id": 1, "nll": 2.0}, {"domain": "a", "doc_id": 2, "nll": 2.0},
         {"domain": "a", "doc_id": 3, "nll": 2.0}, {"domain": "b", "doc_id": 4, "nll": 3.0}]
    x = [{"domain": "a", "doc_id": 1, "nll": 2.3}, {"domain": "a", "doc_id": 2, "nll": 2.0},
         {"domain": "a", "doc_id": 3, "nll": 2.0}, {"domain": "b", "doc_id": 4, "nll": 3.5}]
    d, ppl = S.dnll(x, n)
    assert math.isclose(d, (0.1 + 0.5) / 2)
    assert math.isclose(ppl, 100 * (math.exp(d) - 1))


def test_size_estimate_formula(contract):
    st = contract.statistics
    facts = _facts()
    ids = [f["fact_id"] for f in facts]
    stratum_of = {f["fact_id"]: f["stratum"] for f in facts}
    d = {f: (1.0 if i % 2 else -1.0) * 0.5 for i, f in enumerate(ids)}
    est = S.size_estimate(d, ids, stratum_of, st, "L-F")
    sigma = S.sample_sd(list(d.values()))
    assert est["sigma"]["point"] == sigma
    assert est["n"]["point|delta=0.1"] == math.ceil(((1.96 + 0.84) * sigma / 0.1) ** 2)
    assert est["finite"] and est["n_max"] == max(est["n"].values())
    assert est["sigma"]["p2.5"] <= sigma <= est["sigma"]["p97.5"]


def test_immediate_gain_and_halfwidth_at_zero(contract):
    assert S.immediate_gain({"acc_dev_learned": Fraction(3, 4)}, {"acc_dev_learned": Fraction(1, 4)}) == Fraction(1, 2)
    facts = _facts()
    ids = [f["fact_id"] for f in facts]
    stratum_of = {f["fact_id"]: f["stratum"] for f in facts}
    d = {f: 0.0 for f in ids}                                  # every d_f equal: sigma_d = 0, planning n = 0
    est = S.size_estimate(d, ids, stratum_of, contract.statistics, "L-F")
    assert est["sigma"]["point"] == 0 and est["n_max"] == 0 and est["finite"]
    assert S.halfwidth_check(d, ids, stratum_of, contract.statistics, "L-F", 0)["skipped"]
