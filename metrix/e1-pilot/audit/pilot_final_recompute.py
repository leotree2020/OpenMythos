"""PILOT_REPORT_ORDER item 3: independent recomputation of the Gate 0 and T1-T3 point estimates and 95% CIs,
and of Delta(L-F), Delta(A-F), from the committed per-fact scores only; comparison with
results/step7_record.json and results/test_evaluation_result.json.

Data Auditor's own script, written new for this task. It does not import, call or copy any Executor code
(metrix/e1-pilot/src/, run_pilot.py, tests/). Standard library + numpy (numpy only for a secondary percentile
self-check). CPU only; no model, no tokenizer, no network. It does not read, generate or look for any TEST data
file (test_qa.jsonl, general_test.jsonl, leakage_test_report.json, <work>/test_details/ ...): the only TEST input
is the committed per-fact score table results/test_evaluation_result.json summaries.<model>.scores_test /
scores_cb, as the order requires.

Definitions used (read from the protocol text and from the interpretations recorded in
results/experiment_record_formal_20261128T045921Z.json environment.interpretations; printed verbatim below):
  protocol 5   Score_split(f) = mean over the questions of f of correct(f, q); Acc = mean of Score over a fact group;
               Acc_CB = mean of CB(f) over the 120 learned facts.
  protocol 6   paired d_f = Score_X(f) - Score_Y(f) on the learned facts; 10,000 replicates; within natural and
               random separately resampled with replacement (60 each); Delta* = mean of the drawn d_f; 95% CI =
               2.5th / 97.5th percentiles; rng_rule(BOOTSTRAP_SEED, '<cmp>:<split>:<seed or avg>'); seed-average
               = per fact the mean of the 3 seeds' Scores, then bootstrap.
  protocol 0   rng_rule = random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8],
               "big")), BOOTSTRAP_SEED = 20261112, TRAIN_SEEDS = [101, 202, 303].
  B10          one generator per comparison; per replicate, natural then random: r.choices(d_stratum,
               k=len(d_stratum)) with the facts of the stratum in facts.jsonl order; Delta* = mean of 120 values.
  B11          percentile = linear interpolation at position (B - 1) * p / 100 of the sorted replicates.
  B12          purpose '<X>-<Y>:<DEV|TEST>:<seed|avg>'.
  B13          G0.10 sigma_d (ddof 1), its bootstrap with purpose 'sigma:<X>-<Y>:DEV:avg', n = ceil(((1.96 +
               0.84) * sigma / delta)^2), planning n = max, half-width check with purpose
               'halfwidth:<X>-<Y>:DEV:avg:<n>' resampling ceil(n/2) facts per stratum.
  B22          G0.3 'each stratum' = learned accuracy of each stratum; unread checked overall.
  B24          T3 = all four G0.3 ranges (Acc_CB(N) included); TEST purposes use split 'TEST'.
All arithmetic on Scores is exact (fractions.Fraction / integers); square roots for G0.10 use decimal with
60 significant digits. Each recomputed value is compared with the recorded value.
Consistency criterion (fixed before the run): float fields |recorded - mine| <= 1e-12 (difference computed
exactly from the recorded binary float); point_exact fields exact Fraction equality; integers, strings,
booleans and dicts exact equality.
usage: python3 -I pilot_final_recompute.py <repo_root> <fact_order_json> <out_json>"""
import hashlib
import json
import math
import os
import platform
import random
import socket
import sys
from decimal import Decimal, getcontext, ROUND_CEILING
from fractions import Fraction

getcontext().prec = 60
BOOTSTRAP_SEED = 20261112
TRAIN_SEEDS = [101, 202, 303]
B = 10000
TOL = 1e-12
DEN = 18            # every d_f of this pilot (halves, sixths, thirds, ninths) is an integer multiple of 1/18
P_LO, P_HI = Fraction(5, 2), Fraction(195, 2)
DELTAS = [("0.05", Fraction(5, 100)), ("0.1", Fraction(10, 100)), ("0.15", Fraction(15, 100))]
Z = Fraction(196, 100) + Fraction(84, 100)
ITEMS = []          # main comparison items
SUPP = []           # supplementary cross-checks


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()[:8], "big"))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def get(obj, path):
    for k in path:
        obj = obj[k]
    return obj


def to_dec(x):
    if isinstance(x, Fraction):
        return Decimal(x.numerator) / Decimal(x.denominator)
    return x


def fmt(x):
    if isinstance(x, Fraction):
        return f"{float(x)!r} (={x})"
    if isinstance(x, Decimal):
        return f"{float(x)!r}"
    return json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list, str, bool)) or x is None else repr(x)


def compare(bucket, file, path, mine, kind, rec_root):
    """kind: 'float' (tolerance), 'exact' (point_exact string vs Fraction), 'eq' (exact equality).
    float items: diff = |recorded - float(mine)| (0 means bit-identical binary64); diff_exact = |recorded - mine|
    with the recorded binary64 value taken exactly and mine exact (Fraction) or 60-digit Decimal; both must be <= TOL."""
    try:
        rec = get(rec_root, path)
        present = True
    except (KeyError, TypeError, IndexError):
        rec, present = None, False
    diff = diff_exact = None
    if not present:
        ok = False
    elif kind == "float":
        if isinstance(rec, bool) or not isinstance(rec, (int, float)) or not math.isfinite(rec):
            ok = False
        else:
            diff = abs(float(rec) - float(mine))
            fr = Fraction(rec)
            if isinstance(mine, Decimal):
                diff_exact = abs(Decimal(fr.numerator) / Decimal(fr.denominator) - mine)
            else:
                diff_exact = abs(fr - Fraction(mine))
            ok = diff <= TOL and float(diff_exact) <= TOL
    elif kind == "exact":
        try:
            fr = Fraction(rec)
            diff = abs(fr - mine)
            ok = fr == mine
        except (TypeError, ValueError):
            ok = False
    else:
        ok = rec == mine and type(rec) is type(mine)
    bucket.append({"file": file, "path": "/".join(str(p) for p in path), "kind": kind,
                   "recorded": rec, "mine": (str(mine) if isinstance(mine, (Fraction, Decimal)) else mine),
                   "mine_float": (float(mine) if isinstance(mine, (Fraction, Decimal)) else None),
                   "abs_diff": (float(diff) if diff is not None else None),
                   "abs_diff_exact": (float(diff_exact) if diff_exact is not None else None),
                   "bit_identical": (diff == 0.0 if kind == "float" and diff is not None else None),
                   "consistent": bool(ok)})
    tag = "OK      " if ok else "MISMATCH"
    d = "" if diff is None else f" | diff {float(diff):.3e}"
    if diff_exact is not None:
        d += f" (exact-value diff {float(diff_exact):.1e})"
    print(f"  [{tag}] {file} :: {'/'.join(str(p) for p in path)} | recorded {fmt(rec)} | mine {fmt(mine)}{d}")
    return ok


def score_fraction(x, q, where):
    k = round(x * q)
    f = Fraction(k, q)
    if not (0 <= k <= q) or float(f) != x:
        raise ValueError(f"{where}: score {x!r} is not k/{q}")
    return f


def mean(xs):
    xs = list(xs)
    return sum(xs, Fraction(0)) / len(xs)


def pct_exact(sorted_vals, p):
    pos = Fraction(len(sorted_vals) - 1) * p / 100
    lo = math.floor(pos)
    t = pos - lo
    if lo + 1 >= len(sorted_vals):
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[lo + 1] - sorted_vals[lo]) * (t if isinstance(sorted_vals[lo], Fraction) else to_dec(t))


NP_DIFFS = []


def boot_mean(d_nat, d_rnd, purpose, k_nat=None, k_rnd=None):
    """d_nat, d_rnd: integer numerators (d_f * DEN) in facts.jsonl order. Returns exact CI (Fraction)."""
    kn = len(d_nat) if k_nat is None else k_nat
    kr = len(d_rnd) if k_rnd is None else k_rnd
    r = rng_rule(BOOTSTRAP_SEED, purpose)
    sums = []
    for _ in range(B):
        sums.append(sum(r.choices(d_nat, k=kn)) + sum(r.choices(d_rnd, k=kr)))
    sums.sort()
    den = (kn + kr) * DEN
    vals = [Fraction(s, den) for s in sums]
    lo, hi = pct_exact(vals, P_LO), pct_exact(vals, P_HI)
    try:
        import numpy as np
        a = np.array(sums, dtype=np.float64) / den
        q = np.percentile(a, [2.5, 97.5])
        NP_DIFFS.append(max(abs(float(q[0]) - float(lo)), abs(float(q[1]) - float(hi))))
    except ImportError:
        pass
    return lo, hi


def sample_var(nums):
    """exact sample variance (ddof 1) of values nums / DEN."""
    n = len(nums)
    s1, s2 = sum(nums), sum(x * x for x in nums)
    return Fraction(n * s2 - s1 * s1, n * (n - 1) * DEN * DEN)


def dsqrt(fr):
    return (Decimal(fr.numerator) / Decimal(fr.denominator)).sqrt()


def boot_sigma(d_nat, d_rnd, purpose):
    r = rng_rule(BOOTSTRAP_SEED, purpose)
    vs = []
    for _ in range(B):
        xs = r.choices(d_nat, k=len(d_nat)) + r.choices(d_rnd, k=len(d_rnd))
        vs.append(sample_var(xs))
    vs.sort()
    sig = [dsqrt(v) for v in vs]
    return pct_exact(sig, P_LO), pct_exact(sig, P_HI)


def n_required(sigma, delta):
    """exact (sigma Fraction-variance or Decimal) ceil(((1.96+0.84) * sigma / delta)^2); returns (n, value, n_float)."""
    if isinstance(sigma, tuple):           # ('var', Fraction variance): exact rational
        val = Z * Z * sigma[1] / (delta * delta)
        n = math.ceil(val)
        s_float = math.sqrt(float(sigma[1]))
        vdec = to_dec(val)
    else:
        vdec = (to_dec(Z) * sigma / to_dec(delta)) ** 2
        n = int(vdec.to_integral_value(rounding=ROUND_CEILING))
        s_float = float(sigma)
    n_float = math.ceil(((1.96 + 0.84) * s_float / float(delta)) ** 2)
    near = abs(vdec - vdec.to_integral_value()) < Decimal("1e-9")
    return n, vdec, n_float, near


def main():
    repo, order_json, out_json = sys.argv[1:4]
    e1 = os.path.join(repo, "metrix", "e1-pilot")
    res = os.path.join(e1, "results")
    print(f"host {socket.gethostname()} | {platform.platform()} | python {sys.version.split()[0]} | CPU only, no GPU, no model")
    try:
        import numpy
        print(f"numpy {numpy.__version__} (secondary percentile self-check only)")
    except ImportError:
        print("numpy not available")

    # ------------------------------------------------------------------ definitions printed from the records
    print("\n== A. definitions used (verbatim from the committed record / protocol)")
    proto = open(os.path.join(e1, "METRIX_E1_PROTOCOL.md"), encoding="utf-8").read().splitlines()
    for ln in proto:
        if ln.startswith("**种子**") or ln.startswith("`random.Random(int.from_bytes"):
            print("  protocol 0:", ln)
    sec6 = proto.index("## 6. Statistical Plan")
    for ln in proto[sec6 + 1:sec6 + 10]:
        if ln.strip():
            print("  protocol 6:", ln)
    exp_rec = load(os.path.join(res, "experiment_record_formal_20261128T045921Z.json"))
    interp = {x["id"]: x for x in exp_rec["environment"]["interpretations"]}
    for bid in ("B10", "B11", "B12", "B13", "B22", "B24"):
        x = interp[bid]
        print(f"  {bid} [{x['status']}] (protocol {x['protocol']}): {x['text']}")
    dm = load(os.path.join(e1, "DATA_MANIFEST.json"))
    print(f"  DATA_MANIFEST seeds: BOOTSTRAP_SEED {dm['seeds']['BOOTSTRAP_SEED']} TRAIN_SEEDS {dm['seeds']['TRAIN_SEEDS']} "
          f"rng_rule {dm['seeds']['rng_rule']}")
    ok_setup = dm["seeds"]["BOOTSTRAP_SEED"] == BOOTSTRAP_SEED and dm["seeds"]["TRAIN_SEEDS"] == TRAIN_SEEDS
    print(f"  constants used here: BOOTSTRAP_SEED {BOOTSTRAP_SEED}, TRAIN_SEEDS {TRAIN_SEEDS}, replicates {B} | == manifest {ok_setup}")
    print(f"  consistency criterion: float |recorded - mine| <= {TOL} (exact difference from the recorded float); "
          f"point_exact exact Fraction equality; int / str / bool / dict exact equality")

    # ------------------------------------------------------------------ fact order
    print("\n== B. fact order (B10: facts of a stratum in facts.jsonl order)")
    fo = load(order_json)
    print(f"  source: {order_json}, written by metrix/e1-pilot/audit/pilot_final_facts_order.py "
          f"(full stdout: metrix/e1-pilot/audit/stdout/pilot_final_facts_order.txt)")
    print(f"  how confirmed: the 160 facts were regenerated on CPU from protocol 2.2; the canonical hash of the list "
          f"is {fo['confirmation']['fact_list_canonical_sha256']} (frozen value matched: {fo['confirmation']['list_hash_match']}); "
          f"the facts.jsonl bytes rebuilt from it by the protocol 0 JSONL rule hash to "
          f"{fo['confirmation']['facts_jsonl_sha256_rebuilt']} = results/step1_record.json "
          f"environment.data_hashes['facts.jsonl'].byte_sha256 {fo['confirmation']['step1_record_facts_jsonl_byte_sha256']} "
          f"(match: {fo['confirmation']['byte_hash_match']}); a byte-identical file has the same line order.")
    step1 = load(os.path.join(res, "step1_record.json"))
    rec_b = step1["environment"]["data_hashes"]["facts.jsonl"]["byte_sha256"]
    order_ok = fo["confirmation"]["byte_hash_match"] is True and fo["confirmation"]["facts_jsonl_sha256_rebuilt"] == rec_b \
        and fo["confirmation"]["list_hash_match"] is True
    facts = fo["facts"]
    ids = [f["fact_id"] for f in facts]
    rule = []
    for rel in ("capital", "currency", "founder", "river"):
        for ab in ("nat", "rnd"):
            rule += [f"E1P-L-{rel}-{ab}-{i:02d}" for i in range(1, 16)] + [f"E1P-U-{rel}-{ab}-{i:02d}" for i in range(1, 6)]
    print(f"  re-checked here: step1 byte_sha256 {rec_b} == order file value: {fo['confirmation']['facts_jsonl_sha256_rebuilt'] == rec_b}; "
          f"order == protocol 2.2 generation-order rule: {ids == rule}; 160 distinct ids: {len(set(ids)) == 160}")
    order_ok &= ids == rule and len(set(ids)) == 160
    learned = {st: [f["fact_id"] for f in facts if f["exposure"] == "learned" and f["stratum"] == st] for st in ("natural", "random")}
    unread = [f["fact_id"] for f in facts if f["exposure"] == "unread"]
    learned_all = learned["natural"] + learned["random"]
    attr_ok = all((f["exposure"] == "learned") == f["fact_id"].startswith("E1P-L-") and
                  (f["stratum"] == "natural") == (f["fact_id"].split("-")[3] == "nat") for f in facts)
    print(f"  learned / unread and natural / random from the regenerated facts' fields; agree with the SPLIT_MANIFEST "
          f"fact_id pattern (E1P-<L|U>-<relation>-<nat|rnd>-NN): {attr_ok}")
    print(f"  learned natural {len(learned['natural'])} (first {learned['natural'][0]}, last {learned['natural'][-1]}) | "
          f"learned random {len(learned['random'])} (first {learned['random'][0]}, last {learned['random'][-1]}) | unread {len(unread)}")
    order_ok &= attr_ok and len(learned["natural"]) == 60 and len(learned["random"]) == 60 and len(unread) == 40
    if not order_ok:
        print("  FACT ORDER NOT CONFIRMED")

    # ------------------------------------------------------------------ inputs
    print("\n== C. inputs (per-fact scores)")
    sfr = load(os.path.join(res, "selection_freeze_record.json"))
    sel = sfr["selected"]
    print(f"  results/selection_freeze_record.json selected: {sel} (S and Y use F's configuration, protocol 4)")
    cfg = {"F": sel["F"], "L": sel["L"], "A": sel["A"], "S": sel["F"], "Y": sel["F"]}
    step3 = load(os.path.join(res, "step3_record.json"))
    test = load(os.path.join(res, "test_evaluation_result.json"))
    step7 = load(os.path.join(res, "step7_record.json"))
    dev, dev_cb, tst, tst_cb = {}, {}, {}, {}
    in_ok = True
    all_ids = set(ids)
    lset = set(learned_all)

    def take(scores, q, where, keyset):
        nonlocal in_ok
        if set(scores) != keyset:
            print(f"  !! {where}: fact_id set differs ({len(scores)} keys)")
            in_ok = False
        return {k: score_fraction(v, q, f"{where}[{k}]") for k, v in scores.items()}

    dev["N"] = take(step3["N"]["summary"]["scores_dev"], 2, "step3_record.json N/summary/scores_dev", all_ids)
    dev_cb["N"] = take(step3["N"]["summary"]["scores_cb"], 1, "step3_record.json N/summary/scores_cb", lset)
    print(f"  N   DEV : results/step3_record.json N/summary/scores_dev ({len(dev['N'])}) and scores_cb ({len(dev_cb['N'])})")
    f_cfg = load(os.path.join(res, "training_runs", f"F-{sel['F']}-seed101.json"))["config"]
    for arm in ("F", "L", "A", "S", "Y"):
        for s in TRAIN_SEEDS:
            run = f"{arm}-{cfg[arm]}-seed{s}"
            tr = load(os.path.join(res, "training_runs", f"{run}.json"))
            meta_ok = tr["run"] == run and tr["arm"] == arm and tr["seed"] == s and tr["config_id"] == cfg[arm] \
                and tr["steps_run"] == 300 and tr["finite"] is True
            if arm in ("S", "Y"):
                meta_ok &= tr["config"] == f_cfg
            in_ok &= meta_ok
            dev[run] = take(tr["dev"]["scores_dev"], 2, f"training_runs/{run}.json dev/scores_dev", all_ids)
            dev_cb[run] = take(tr["dev"]["scores_cb"], 1, f"training_runs/{run}.json dev/scores_cb", lset)
            print(f"  {run:<14} DEV : results/training_runs/{run}.json dev/scores_dev ({len(dev[run])}), dev/scores_cb "
                  f"({len(dev_cb[run])}) | run/arm/seed/config_id/steps/finite{'/config == F config' if arm in 'SY' else ''} as expected: {meta_ok}")
    summ = test["summaries"]
    for model in ["N"] + [f"{a}-{cfg[a]}-seed{s}" for a in ("F", "L", "A", "S", "Y") for s in TRAIN_SEEDS]:
        tst[model] = take(summ[model]["scores_test"], 3, f"test_evaluation_result.json summaries/{model}/scores_test", all_ids)
        tst_cb[model] = take(summ[model]["scores_cb"], 1, f"test_evaluation_result.json summaries/{model}/scores_cb", lset)
    print(f"  TEST: results/test_evaluation_result.json summaries/<model>/scores_test (160 each) and scores_cb (120 each) "
          f"for {len(tst)} models: {sorted(tst)}")
    extra = sorted(set(summ) - set(tst))
    print(f"  models in TEST summaries not used: {extra}")
    print(f"  all DEV Scores are k/2, all TEST Scores k/3, all CB values 0/1 (checked exactly when converting): True")
    print(f"  inputs consistent: {in_ok}")
    cb_same = sum(dev_cb[m] != tst_cb[m] for m in tst)
    print(f"  info: models whose TEST-session scores_cb differ from their DEV scores_cb: {cb_same} of {len(tst)}")

    # ------------------------------------------------------------------ helpers on Scores
    def acc(sc, group):
        return mean(sc[f] for f in group)

    def avg_scores(table, models):
        return {f: mean(table[m][f] for m in models) for f in ids}

    def cmp_values(table, xs, ys):
        """xs, ys: lists of model names (seed-average if 3); returns d (Fraction per learned fact)."""
        sx = avg_scores(table, xs) if len(xs) > 1 else table[xs[0]]
        sy = avg_scores(table, ys) if len(ys) > 1 else table[ys[0]]
        return {f: sx[f] - sy[f] for f in learned_all}

    def run_comparison(table, split, X, Y, seed):
        if seed == "avg":
            xs = [f"{X}-{cfg[X]}-seed{s}" for s in TRAIN_SEEDS]
            ys = ["N"] if Y == "N" else [f"{Y}-{cfg[Y]}-seed{s}" for s in TRAIN_SEEDS]
        else:
            xs = [f"{X}-{cfg[X]}-seed{seed}"]
            ys = ["N"] if Y == "N" else [f"{Y}-{cfg[Y]}-seed{seed}"]
        d = cmp_values(table, xs, ys)
        nums = {}
        for st in ("natural", "random"):
            nums[st] = []
            for f in learned[st]:
                v = d[f] * DEN
                assert v.denominator == 1, "d_f not a multiple of 1/18"
                nums[st].append(int(v))
        point = mean(d.values())
        purpose = f"{X}-{Y}:{split}:{seed}"
        lo, hi = boot_mean(nums["natural"], nums["random"], purpose)
        return {"point": point, "ci_low": lo, "ci_high": hi, "purpose": purpose, "nums": nums, "d": d,
                "n_facts": len(d), "n_per_stratum": {"natural": len(nums["natural"]), "random": len(nums["random"])}}

    def check_comparison(file, root, path, c, bucket=ITEMS):
        ok = True
        ok &= compare(bucket, file, path + ["point"], c["point"], "float", root)
        ok &= compare(bucket, file, path + ["point_exact"], c["point"], "exact", root)
        ok &= compare(bucket, file, path + ["ci_low"], c["ci_low"], "float", root)
        ok &= compare(bucket, file, path + ["ci_high"], c["ci_high"], "float", root)
        ok &= compare(bucket, file, path + ["purpose"], c["purpose"], "eq", root)
        ok &= compare(bucket, file, path + ["n_facts"], c["n_facts"], "eq", root)
        ok &= compare(bucket, file, path + ["n_per_stratum"], c["n_per_stratum"], "eq", root)
        ok &= compare(bucket, file, path + ["replicates"], B, "eq", root)
        return ok

    PAIRS = [("F", "N"), ("S", "N"), ("Y", "N"), ("L", "F"), ("A", "F")]
    SEEDS = TRAIN_SEEDS + ["avg"]
    F7, FT = "results/step7_record.json", "results/test_evaluation_result.json"

    # ------------------------------------------------------------------ DEV
    print("\n== D. DEV (Gate 0) - recomputation and comparison with results/step7_record.json")
    C = {}
    for X, Y in PAIRS:
        for s in SEEDS:
            C[(X, Y, s)] = run_comparison(dev, "DEV", X, Y, s)
    print(" -- comparisons (Delta(F-N), Delta(S-N), Delta(Y-N), Delta(L-F), Delta(A-F); each seed and seed-average)")
    for X, Y in PAIRS:
        for s in SEEDS:
            check_comparison(F7, step7, ["comparisons", f"{X}-{Y}:{s}"], C[(X, Y, s)])
    v7 = ["values"]
    print(" -- G0.3 (N, DEV-QA; B22)")
    nsc = dev["N"]
    g03 = {"acc_cb": mean(dev_cb["N"][f] for f in learned_all), "acc_dev_learned": acc(nsc, learned_all),
           "acc_dev_learned:natural": acc(nsc, learned["natural"]), "acc_dev_learned:random": acc(nsc, learned["random"]),
           "acc_dev_unread": acc(nsc, unread)}
    for k, v in g03.items():
        compare(ITEMS, F7, v7 + ["G0.3", k], v, "float", step7)
    print(" -- G0.4 (Acc_CB(F) per seed)")
    g04 = {}
    for s in TRAIN_SEEDS:
        g04[s] = mean(dev_cb[f"F-{cfg['F']}-seed{s}"][f] for f in learned_all)
        compare(ITEMS, F7, v7 + ["G0.4", "acc_cb_by_seed", str(s)], g04[s], "float", step7)
    print(" -- G0.5 (seed-average Acc(F, DEV-QA, learned); Delta(F-N) per seed and seed-average)")
    f_avg = avg_scores(dev, [f"F-{cfg['F']}-seed{s}" for s in TRAIN_SEEDS])
    acc_f_avg = acc(f_avg, learned_all)
    compare(ITEMS, F7, v7 + ["G0.5", "acc_avg"], acc_f_avg, "float", step7)
    check_comparison(F7, step7, v7 + ["G0.5", "delta_avg"], C[("F", "N", "avg")])
    for s in TRAIN_SEEDS:
        compare(ITEMS, F7, v7 + ["G0.5", "delta_by_seed", str(s)], C[("F", "N", s)]["point"], "float", step7)
    print(" -- G0.6 (seed-average Delta(S-N))")
    compare(ITEMS, F7, v7 + ["G0.6", "point"], C[("S", "N", "avg")]["point"], "float", step7)
    compare(ITEMS, F7, v7 + ["G0.6", "ci_high"], C[("S", "N", "avg")]["ci_high"], "float", step7)
    check_comparison(F7, step7, v7 + ["G0.6", "delta_avg"], C[("S", "N", "avg")])
    print(" -- G0.7 (seed-average Delta(Y-N))")
    compare(ITEMS, F7, v7 + ["G0.7", "point"], C[("Y", "N", "avg")]["point"], "float", step7)
    compare(ITEMS, F7, v7 + ["G0.7", "ci_high"], C[("Y", "N", "avg")]["ci_high"], "float", step7)
    check_comparison(F7, step7, v7 + ["G0.7", "delta_avg"], C[("Y", "N", "avg")])
    print(" -- G0.9 (seed-average Acc(F, DEV-QA, learned))")
    compare(ITEMS, F7, v7 + ["G0.9", "acc_avg"], acc_f_avg, "float", step7)

    print(" -- G0.10 (B13): sigma_d of the seed-average d_f of Delta(L-F), Delta(A-F); n per delta; planning n; half-width")
    est = {}
    boundary = []
    for X, Y in [("L", "F"), ("A", "F")]:
        c = C[(X, Y, "avg")]
        allnums = c["nums"]["natural"] + c["nums"]["random"]
        var = sample_var(allnums)
        sig_pt = dsqrt(var)
        p_lo, p_hi = boot_sigma(c["nums"]["natural"], c["nums"]["random"], f"sigma:{X}-{Y}:DEV:avg")
        sig = {"p2.5": p_lo, "point": sig_pt, "p97.5": p_hi}
        ns = {}
        for lab, sv in sig.items():
            for dl, dv in DELTAS:
                arg = ("var", var) if lab == "point" else sv
                n, val, n_float, near = n_required(arg, dv)
                ns[f"{lab}|delta={dl}"] = n
                if n != n_float or near:
                    boundary.append((f"{X}-{Y}", lab, dl, n, n_float, str(val)))
        finite = all(math.isfinite(float(v)) for v in sig.values()) and all(isinstance(v, int) for v in ns.values())
        est[f"{X}-{Y}"] = {"sigma": sig, "n": ns, "n_max": max(ns.values()), "finite": finite, "var": var,
                           "nums": c["nums"]}
        print(f"    {X}-{Y}: sigma variance (exact) {var} ; sigma point {float(sig_pt)!r}")
    planning_n = max(e["n_max"] for e in est.values())
    print(f"    planning n (max over both comparisons, 3 sigmas, 3 deltas) = {planning_n}; n values where exact and float "
          f"ceil differ or the argument is within 1e-9 of an integer: {boundary}")
    for key, e in est.items():
        per = -(-planning_n // 2)
        lo, hi = boot_mean(e["nums"]["natural"], e["nums"]["random"], f"halfwidth:{key}:DEV:avg:{planning_n}", per, per)
        e["halfwidth"] = {"halfwidth": (hi - lo) / 2, "n": planning_n, "per_stratum": per}
        base = v7 + ["G0.10", "estimates", key]
        compare(ITEMS, F7, base + ["comparison"], key, "eq", step7)
        for lab in ("p2.5", "point", "p97.5"):
            compare(ITEMS, F7, base + ["sigma", lab], e["sigma"][lab], "float", step7)
        for k in sorted(e["n"]):
            compare(ITEMS, F7, base + ["n", k], e["n"][k], "eq", step7)
        compare(ITEMS, F7, base + ["n_max"], e["n_max"], "eq", step7)
        compare(ITEMS, F7, base + ["finite"], e["finite"], "eq", step7)
        compare(ITEMS, F7, base + ["halfwidth_at_planning_n", "halfwidth"], e["halfwidth"]["halfwidth"], "float", step7)
        compare(ITEMS, F7, base + ["halfwidth_at_planning_n", "n"], planning_n, "eq", step7)
        compare(ITEMS, F7, base + ["halfwidth_at_planning_n", "per_stratum"], per, "eq", step7)
    compare(ITEMS, F7, v7 + ["G0.10", "planning_n"], planning_n, "eq", step7)

    # ------------------------------------------------------------------ TEST
    print("\n== E. TEST (T1-T3) - recomputation and comparison with results/test_evaluation_result.json")
    T = {}
    for X, Y in PAIRS:
        for s in SEEDS:
            T[(X, Y, s)] = run_comparison(tst, "TEST", X, Y, s)
    print(" -- comparisons (Delta(F-N), Delta(S-N), Delta(Y-N), Delta(L-F), Delta(A-F); each seed and seed-average)")
    for X, Y in PAIRS:
        for s in SEEDS:
            check_comparison(FT, test, ["comparisons", f"{X}-{Y}:{s}"], T[(X, Y, s)])
    vt = ["values"]
    print(" -- T1 (seed-average Acc(F, TEST-QA, learned); seed-average Delta(F-N))")
    ft_avg = avg_scores(tst, [f"F-{cfg['F']}-seed{s}" for s in TRAIN_SEEDS])
    acc_ft_avg = acc(ft_avg, learned_all)
    compare(ITEMS, FT, vt + ["T1", "acc_avg"], acc_ft_avg, "float", test)
    check_comparison(FT, test, vt + ["T1", "delta_avg"], T[("F", "N", "avg")])
    print(" -- T2 (seed-average Delta(S-N), Delta(Y-N) on TEST)")
    for arm in ("S", "Y"):
        compare(ITEMS, FT, vt + ["T2", arm, "point"], T[(arm, "N", "avg")]["point"], "float", test)
        compare(ITEMS, FT, vt + ["T2", arm, "ci_high"], T[(arm, "N", "avg")]["ci_high"], "float", test)
        check_comparison(FT, test, vt + ["T2", arm, "delta_avg"], T[(arm, "N", "avg")])
    print(" -- T3 (N on TEST-QA; B24: all four G0.3 ranges, Acc_CB(N) included)")
    nt = tst["N"]
    t3 = {"acc_cb": mean(tst_cb["N"][f] for f in learned_all), "acc_test_learned": acc(nt, learned_all),
          "acc_test_learned:natural": acc(nt, learned["natural"]), "acc_test_learned:random": acc(nt, learned["random"]),
          "acc_test_unread": acc(nt, unread)}
    for k, v in t3.items():
        compare(ITEMS, FT, vt + ["T3", k], v, "float", test)

    # ------------------------------------------------------------------ supplementary cross-checks
    print("\n== F. supplementary cross-checks (not in the ordered scope; counted separately)")
    print(" -- F1. gate decisions recomputed from my values and the protocol 8 thresholds vs recorded 'satisfied'")
    q = Fraction

    def inr(x, a, b):
        return q(a) <= x <= q(b)
    g = {"G0.3": inr(g03["acc_dev_learned"], "0.15", "0.35") and inr(g03["acc_dev_learned:natural"], "0.10", "0.40")
         and inr(g03["acc_dev_learned:random"], "0.10", "0.40") and inr(g03["acc_dev_unread"], "0.10", "0.40")
         and inr(g03["acc_cb"], "0.15", "0.35"),
         "G0.4": all(v >= q("0.90") for v in g04.values()),
         "G0.5": acc_f_avg >= q("0.70") and C[("F", "N", "avg")]["ci_low"] > 0 and all(C[("F", "N", s)]["point"] > 0 for s in TRAIN_SEEDS),
         "G0.6": C[("S", "N", "avg")]["point"] <= q("0.05") and C[("S", "N", "avg")]["ci_high"] <= q("0.12"),
         "G0.7": C[("Y", "N", "avg")]["point"] <= q("0.05") and C[("Y", "N", "avg")]["ci_high"] <= q("0.12"),
         "G0.9": acc_f_avg <= q("0.95"),
         "G0.10": all(e["finite"] for e in est.values())}
    gate0 = load(os.path.join(res, "gate0_record.json"))
    for k, v in g.items():
        compare(SUPP, F7, ["gate0", "conditions", k, "satisfied"], v, "eq", step7)
        compare(SUPP, "results/gate0_record.json", ["gate0", "conditions", k, "satisfied"], v, "eq", gate0)
    t = {"T1": acc_ft_avg >= q("0.70") and T[("F", "N", "avg")]["ci_low"] > 0,
         "T2": all(T[(a, "N", "avg")]["point"] <= q("0.05") and T[(a, "N", "avg")]["ci_high"] <= q("0.12") for a in ("S", "Y")),
         "T3": inr(t3["acc_test_learned"], "0.15", "0.35") and inr(t3["acc_test_learned:natural"], "0.10", "0.40")
         and inr(t3["acc_test_learned:random"], "0.10", "0.40") and inr(t3["acc_test_unread"], "0.10", "0.40")
         and inr(t3["acc_cb"], "0.15", "0.35")}
    for k, v in t.items():
        compare(SUPP, FT, ["final", "conditions", k, "satisfied"], v, "eq", test)
    print(" -- F2. per-model accuracies in the records (DEV: training_runs dev.* and step3 N.summary / g03_values; TEST: summaries.*)")
    groups = {"learned": learned_all, "learned:natural": learned["natural"], "learned:random": learned["random"],
              "unread": unread, "unread:natural": [f for f in unread if "-nat-" in f],
              "unread:random": [f for f in unread if "-rnd-" in f]}
    for model in sorted(dev):
        if model == "N":
            root, file, base = step3, "results/step3_record.json", ["N", "summary"]
        else:
            root, file, base = load(os.path.join(res, "training_runs", f"{model}.json")), f"results/training_runs/{model}.json", ["dev"]
        compare(SUPP, file, base + ["acc_cb"], mean(dev_cb[model][f] for f in learned_all), "float", root)
        for gk, gv in groups.items():
            compare(SUPP, file, base + [f"acc_dev_{gk}"], acc(dev[model], gv), "float", root)
    for k, v in g03.items():
        compare(SUPP, "results/step3_record.json", ["N", "g03_values", k], v, "float", step3)
    for model in sorted(tst):
        compare(SUPP, FT, ["summaries", model, "acc_cb"], mean(tst_cb[model][f] for f in learned_all), "float", test)
        for gk, gv in groups.items():
            compare(SUPP, FT, ["summaries", model, f"acc_test_{gk}"], acc(tst[model], gv), "float", test)
    print(" -- F3. DEV details (results/details/<run>_dev.json): correct = s(answer) > max s(other), ties wrong; Score and CB")
    det_bad = 0
    det_items = 0
    for model in sorted(dev):
        dname = "N_dev.json" if model == "N" else f"{model}_dev.json"
        det = load(os.path.join(res, "details", dname))["evaluation"]
        per = {}
        flag_bad = 0
        for row in det["dev_qa"]:
            sc = row["scores"]
            a = row["answer_index"]
            corr = all(sc[a] > sc[j] for j in range(len(sc)) if j != a)
            flag_bad += corr != row["correct"]
            per.setdefault(row["fact_id"], []).append(Fraction(int(corr)))
        cbp = {}
        for row in det["train_cb"]:
            sc = row["scores"]
            a = row["answer_index"]
            corr = all(sc[a] > sc[j] for j in range(len(sc)) if j != a)
            flag_bad += corr != row["correct"]
            cbp[row["fact_id"]] = Fraction(int(corr))
        nq_ok = all(len(v) == 2 for v in per.values()) and set(per) == all_ids and set(cbp) == lset
        s_bad = sum(mean(per[f]) != dev[model][f] for f in ids) + sum(cbp[f] != dev_cb[model][f] for f in learned_all)
        det_items += len(det["dev_qa"]) + len(det["train_cb"]) + 160 + 120
        det_bad += flag_bad + s_bad + (0 if nq_ok else 1)
        ok_ = flag_bad == 0 and s_bad == 0 and nq_ok
        print(f"  [{'OK      ' if ok_ else 'MISMATCH'}] results/details/{dname}: rows dev_qa {len(det['dev_qa'])} train_cb "
              f"{len(det['train_cb'])} | 2 DEV questions per fact, ids complete: {nq_ok} | 'correct' flags != recomputed: "
              f"{flag_bad} | Scores / CB != committed scores_dev / scores_cb: {s_bad}")
    print("  (TEST per-question details were not committed; no TEST detail cross-check is possible or attempted)")

    # ------------------------------------------------------------------ sensitivity (negative controls)
    print("\n== H. sensitivity of the CI comparison (negative controls; information only, not counted)")
    print("  Each variant changes one implementation detail and recomputes the 40 comparisons (DEV and TEST, 5 pairs x")
    print("  4 seeds); shown is how many of the 80 recorded CI endpoints it still reproduces within the tolerance.")

    def variant_ci(nums, purpose, variant):
        nat, rnd = list(nums["natural"]), list(nums["random"])
        if variant == "reversed fact order within each stratum":
            nat, rnd = nat[::-1], rnd[::-1]
        if variant == "purpose with U+2212 minus instead of ASCII '-'":
            purpose = purpose.replace("-", "\u2212", 1)
        r = rng_rule(BOOTSTRAP_SEED, purpose)
        sums = []
        for _ in range(B):
            if variant == "unstratified resampling (120 from all learned facts)":
                sums.append(sum(r.choices(nat + rnd, k=len(nat) + len(rnd))))
            elif variant == "stratum order random, then natural":
                sums.append(sum(r.choices(rnd, k=len(rnd))) + sum(r.choices(nat, k=len(nat))))
            else:
                sums.append(sum(r.choices(nat, k=len(nat))) + sum(r.choices(rnd, k=len(rnd))))
        sums.sort()
        den = (len(nat) + len(rnd)) * DEN
        vals = [Fraction(x, den) for x in sums]
        if variant == "percentile without interpolation (lower order statistic)":
            return (vals[math.floor(Fraction(B - 1) * P_LO / 100)], vals[math.floor(Fraction(B - 1) * P_HI / 100)])
        return pct_exact(vals, P_LO), pct_exact(vals, P_HI)

    variants = ["as implemented above (B10-B12)", "reversed fact order within each stratum",
                "stratum order random, then natural", "unstratified resampling (120 from all learned facts)",
                "purpose with U+2212 minus instead of ASCII '-'",
                "percentile without interpolation (lower order statistic)"]
    for variant in variants:
        hit = tot = 0
        for split, table_c, root in (("DEV", C, step7), ("TEST", T, test)):
            for (X, Y, sd), c in table_c.items():
                lo, hi = variant_ci(c["nums"], c["purpose"], variant)
                rc = root["comparisons"][f"{X}-{Y}:{sd}"]
                hit += abs(float(lo) - rc["ci_low"]) <= TOL
                hit += abs(float(hi) - rc["ci_high"]) <= TOL
                tot += 2
        print(f"  {variant:<58}: {hit:>2} of {tot} recorded CI endpoints reproduced")
    sorted_ids = sorted(learned_all)
    same_sorted = all([f for f in sorted_ids if f in set(learned[st])] == learned[st] for st in ("natural", "random"))
    print(f"  note: within each stratum the learned facts in plain fact_id sort order are in the same order as in facts.jsonl: "
          f"{same_sorted} (so a sorted-fact_id implementation would give the same draws; the order variant above is a reversal)")

    # ------------------------------------------------------------------ summary
    def summarize(items, label):
        n = len(items)
        bad = [x for x in items if not x["consistent"]]
        diffs = [x["abs_diff"] for x in items if x["abs_diff"] is not None]
        fl = [x for x in items if x["kind"] == "float"]
        exact_eq = sum(1 for x in fl if x["bit_identical"])
        dex = [x["abs_diff_exact"] for x in fl if x["abs_diff_exact"] is not None]
        print(f"{label}: items {n} | inconsistent {len(bad)} | max |diff| {max(diffs) if diffs else 0.0:.3e} | "
              f"max exact-value diff of float items {max(dex) if dex else 0.0:.3e} | "
              f"by kind {dict((k, sum(1 for x in items if x['kind'] == k)) for k in ('float', 'exact', 'eq'))} | "
              f"float items bit-identical (diff exactly 0): {exact_eq} of {len(fl)}")
        for x in bad:
            print(f"   INCONSISTENT {x['file']} :: {x['path']} | recorded {x['recorded']} | mine {x['mine']}")
        return n, len(bad), (max(diffs) if diffs else 0.0)

    print("\n== G. summary")
    print(f"numpy.percentile (default 'linear') vs my exact percentiles over all {len(NP_DIFFS)} bootstraps of means: "
          f"max |diff| {max(NP_DIFFS) if NP_DIFFS else float('nan'):.3e} (self-check of B11)")
    n_dev = sum(1 for x in ITEMS if x["file"] == F7)
    n_tst = sum(1 for x in ITEMS if x["file"] == FT)
    print(f"main items: DEV (step7_record.json) {n_dev}, TEST (test_evaluation_result.json) {n_tst}")
    m_n, m_bad, m_max = summarize(ITEMS, "MAIN (ordered scope)")
    s_n, s_bad, s_max = summarize(SUPP, "SUPPLEMENTARY F1-F2")
    print(f"SUPPLEMENTARY F3 (DEV details): checked values {det_items} | inconsistent {det_bad}")
    print(f"setup checks: fact order confirmed {order_ok} | inputs consistent {in_ok} | seeds == manifest {ok_setup}")
    out = {"what": "pilot_final_recompute.py comparison table", "tolerance_float": TOL, "replicates": B,
           "fact_order_source": order_json, "fact_order_confirmed": order_ok,
           "main": {"items": m_n, "inconsistent": m_bad, "max_abs_diff": m_max, "rows": ITEMS},
           "supplementary": {"items": s_n, "inconsistent": s_bad, "max_abs_diff": s_max, "rows": SUPP,
                             "dev_details_values": det_items, "dev_details_inconsistent": det_bad},
           "g010_boundary_cases": boundary}
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    print(f"wrote {out_json}")
    total_bad = m_bad + s_bad + det_bad
    print(f"TOTAL items {m_n + s_n} (+ {det_items} detail values) | inconsistent {total_bad} | main inconsistent {m_bad}")
    return order_ok and in_ok and ok_setup and total_bad == 0


if __name__ == "__main__":
    try:
        res_ = main()
    except BaseException:
        import traceback
        sys.stdout.flush()
        traceback.print_exc(file=sys.stdout)
        print("RESULT: FAIL (exception)")
        sys.exit(2)
    print("RESULT: PASS" if res_ else "RESULT: FAIL")
    sys.exit(0 if res_ else 1)
