"""Metrics and statistics of METRIX E1-PILOT.

Protocol v1.1 section 5 (Score_split(f) = mean over the fact's questions; Acc = mean over facts; AllCorrect, FPR,
ImmediateGain, dNLL, PPL degradation; Spill = Delta(arm - N) on unread facts, gate.report_comparisons) and section 6 (the unit is the fact: question scores are aggregated to
one score per fact before anything is resampled; paired, stratified bootstrap; 10,000 replicates; 95% CI = 2.5th and
97.5th percentiles; seed-average = per-fact mean over the 3 seeds, then bootstrap; rng_rule(BOOTSTRAP_SEED, purpose));
section 8 G0.10 (size estimate). Choices left open by the protocol: interpretations B10-B13.

Accuracies are exact fractions (fractions.Fraction) so that ties in the selection of section 7 are exact; the
bootstrap works on floats.
"""
import math
from fractions import Fraction

from . import frozen as FZ


# ------------------------------------------------------------------------------------------ fact level (5)

def fact_scores(rows, key="correct"):
    """Score_split(f) = (1/|Q_split(f)|) * sum_q 1[...]: one exact fraction per fact (aggregation = mean). `rows`: one
    row per (fact, question) with a boolean `key`."""
    num, den = {}, {}
    for r in rows:
        f = r["fact_id"]
        num[f] = num.get(f, 0) + (1 if r[key] else 0)
        den[f] = den.get(f, 0) + 1
    return {f: Fraction(num[f], den[f]) for f in num}


def all_correct(rows, key="correct"):
    """AllCorrect(f) = product over the fact's questions of correct(f, q)."""
    out = {}
    for r in rows:
        out[r["fact_id"]] = out.get(r["fact_id"], True) and bool(r[key])
    return {f: Fraction(int(v)) for f, v in out.items()}


def groups(facts, strata):
    """Fact ids in facts.jsonl order: learned, unread, and learned / unread per stratum."""
    g = {"learned": [f["fact_id"] for f in facts if f["exposure"] == "learned"],
         "unread": [f["fact_id"] for f in facts if f["exposure"] == "unread"]}
    for st in strata:
        for e in ("learned", "unread"):
            g["%s:%s" % (e, st)] = [f["fact_id"] for f in facts if f["exposure"] == e and f["stratum"] == st]
    return g


def acc(scores, fact_ids):
    """Acc(arm, split, G) = (1/|G|) sum_{f in G} Score_split(f)."""
    missing = [f for f in fact_ids if f not in scores]
    if missing or not fact_ids:
        raise ValueError("Acc over %d facts: %d have no score" % (len(fact_ids), len(missing)))
    return sum((scores[f] for f in fact_ids), Fraction(0)) / len(fact_ids)


def seed_average(per_seed):
    """Per-fact mean of the scores of several seeds (section 6 'seed-average')."""
    keys = set(per_seed[0])
    if any(set(s) != keys for s in per_seed):
        raise ValueError("seeds score different facts")
    return {f: sum((s[f] for s in per_seed), Fraction(0)) / len(per_seed) for f in keys}


def immediate_gain(summary_arm, summary_n, split="dev"):
    """ImmediateGain(arm, split) = Acc(arm, split, learned) - Acc(N, split, learned) (protocol section 5)."""
    key = "acc_%s_learned" % split
    return summary_arm[key] - summary_n[key]


def dnll(rows_arm, rows_n):
    """dNLL(arm) = mean over domains of mean over the domain's windows of NLL_arm(w) - NLL_N(w); domains in the order
    of the rows. Returns (dNLL, PPL_degradation% = 100 (exp(dNLL) - 1))."""
    base = {(r["domain"], r["doc_id"]): r["nll"] for r in rows_n}
    if len(base) != len(rows_n) or len(rows_arm) != len(rows_n):
        raise ValueError("NLL rows of the arm and of N do not match")
    by_dom = {}
    for r in rows_arm:
        by_dom.setdefault(r["domain"], []).append(r["nll"] - base[(r["domain"], r["doc_id"])])
    d = sum(sum(v) / len(v) for v in by_dom.values()) / len(by_dom)
    return d, 100.0 * (math.exp(d) - 1.0)


# --------------------------------------------------------------------------------------------- bootstrap (6)

def purpose(comparison, split, seed):
    """B12: '<X>-<Y>:<split>:<seed or avg>'."""
    return "%s:%s:%s" % (comparison, split, seed)


def percentile(sorted_values, p):
    """B11: linear interpolation at position (B - 1) * p / 100 of the sorted values."""
    pos = (len(sorted_values) - 1) * p / 100.0
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def stratified_draws(d_by_stratum, n_boot, rng):
    """B10: n_boot replicates; per replicate, per stratum in the given order, rng.choices(values, k=len(values))."""
    out = []
    strata = list(d_by_stratum.values())
    for _ in range(n_boot):
        drawn = []
        for vals in strata:
            drawn += rng.choices(vals, k=len(vals))
        out.append(drawn)
    return out


def _by_stratum(d, fact_ids, stratum_of, strata):
    return {st: [float(d[f]) for f in fact_ids if stratum_of[f] == st] for st in strata}


def paired_bootstrap(score_x, score_y, fact_ids, stratum_of, st, purpose_text):
    """Section 6: d_f = Score_X(f) - Score_Y(f) over `fact_ids` (both arms on the same resampled facts); stratified
    resampling within each stratum; Delta* = mean(d_f); 95% CI from the percentiles. Returns a dict."""
    d = {f: score_x[f] - score_y[f] for f in fact_ids}
    by = _by_stratum(d, fact_ids, stratum_of, st.strata)
    if sum(len(v) for v in by.values()) != len(fact_ids):
        raise ValueError("facts outside the strata %s" % (st.strata,))
    rng = FZ.rng_rule(st.bootstrap_seed, purpose_text)
    reps = sorted(sum(x) / len(x) for x in stratified_draws(by, st.n_boot, rng))
    point = sum((d[f] for f in fact_ids), Fraction(0)) / len(fact_ids)
    return {"purpose": purpose_text, "point": float(point), "point_exact": str(point), "n_facts": len(fact_ids),
            "n_per_stratum": {k: len(v) for k, v in by.items()}, "replicates": st.n_boot,
            "ci_low": percentile(reps, st.ci_low_pct), "ci_high": percentile(reps, st.ci_high_pct)}


# ------------------------------------------------------------------------------------------- G0.10 (8; B13)

def sample_sd(values):
    n = len(values)
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def required_n(sigma, delta, z_sum):
    return math.ceil((z_sum * sigma / delta) ** 2) if math.isfinite(sigma) else math.inf


def size_estimate(d_avg, fact_ids, stratum_of, st, comparison, split="DEV"):
    """G0.10 for one comparison: sigma_d of the seed-average paired differences, its bootstrap percentiles, the
    required n for each delta and each sigma value, and the CI half-width obtained when n facts are resampled."""
    by = _by_stratum(d_avg, fact_ids, stratum_of, st.strata)
    vals = [v for vs in by.values() for v in vs]
    sigma = sample_sd(vals)
    rng = FZ.rng_rule(st.bootstrap_seed, purpose("sigma:" + comparison, split, "avg"))
    sig_reps = sorted(sample_sd(x) for x in stratified_draws(by, st.n_boot, rng))
    sigmas = {"p%g" % st.ci_low_pct: percentile(sig_reps, st.ci_low_pct), "point": sigma,
              "p%g" % st.ci_high_pct: percentile(sig_reps, st.ci_high_pct)}
    n_table = {"%s|delta=%g" % (k, dl): required_n(s, dl, st.z_sum) for k, s in sigmas.items() for dl in st.deltas}
    return {"comparison": comparison, "sigma": sigmas, "n": n_table, "n_max": max(n_table.values()),
            "finite": all(math.isfinite(v) for v in list(sigmas.values()) + list(n_table.values()))}


def halfwidth_check(d_avg, fact_ids, stratum_of, st, comparison, n, split="DEV"):
    """B13 (report only): resample n facts (ceil(n / number of strata) per stratum) n_boot times and report the
    half-width of the 95% CI of the mean. n = 0 (sigma_d = 0: every d_f equal) has nothing to resample: reported as
    skipped."""
    if n == 0:
        return {"n": 0, "per_stratum": 0, "halfwidth": None, "skipped": "n = 0 (sigma_d = 0)"}
    by = _by_stratum(d_avg, fact_ids, stratum_of, st.strata)
    per = math.ceil(n / len(by))
    rng = FZ.rng_rule(st.bootstrap_seed, purpose("halfwidth:" + comparison, split, "avg:%d" % n))
    reps = []
    for _ in range(st.n_boot):
        drawn = []
        for vals in by.values():
            drawn += rng.choices(vals, k=per)
        reps.append(sum(drawn) / len(drawn))
    reps.sort()
    return {"n": n, "per_stratum": per, "halfwidth": (percentile(reps, st.ci_high_pct) - percentile(reps, st.ci_low_pct)) / 2}


# ------------------------------------------------------------------------------------- per-evaluation summary

def evaluation_summary(ev_out, facts, strata, split="dev"):
    """Section 5 summary of one evaluation (evaluate.evaluate_model output for `split`): exact fact scores and
    accuracies. Keys (shown for split "dev"): scores_dev (Score(f) for all 160 facts), scores_cb (CB(f) for the 120
    learned facts), acc_dev_learned, acc_dev_unread, acc_dev_<exposure>:<stratum>, acc_cb, all_correct_dev, fpr_dev,
    em_dev_learned / em_dev_unread (if EM was run), general_dev (the NLL rows)."""
    g = groups(facts, strata)
    sd = fact_scores(ev_out["%s_qa" % split])
    scb = fact_scores(ev_out["train_cb"])
    allc = all_correct(ev_out["%s_qa" % split])
    out = {"scores_%s" % split: sd, "scores_cb": scb, "acc_%s_learned" % split: acc(sd, g["learned"]),
           "acc_%s_unread" % split: acc(sd, g["unread"]), "acc_cb": acc(scb, g["learned"]),
           "all_correct_%s" % split: allc, "fpr_%s" % split: acc(allc, g["unread"]),
           "general_%s" % split: ev_out["general_%s" % split]}
    for st in strata:
        for e in ("learned", "unread"):
            out["acc_%s_%s:%s" % (split, e, st)] = acc(sd, g["%s:%s" % (e, st)])
    if "em_%s" % split in ev_out:
        se = fact_scores(ev_out["em_%s" % split], key="em")
        out["em_%s_learned" % split], out["em_%s_unread" % split] = acc(se, g["learned"]), acc(se, g["unread"])
    if "s_mapping_dev_qa" in ev_out:
        out["s_mapping_dev_learned"] = acc(fact_scores(ev_out["s_mapping_dev_qa"]), g["learned"])
        out["s_mapping_cb"] = acc(fact_scores(ev_out["s_mapping_cb"]), g["learned"])
    return out
