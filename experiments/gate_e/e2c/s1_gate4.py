#!/usr/bin/env python3
"""
Stage 1, gate 4: the non-formal calibration of lambda (C1) and lambda2 (C2)
(E2C_PREREG_DRAFT 3.5, 5.2). Run only after gates 1-3 passed. Calibration seeds
91, 92, 93 only; each arm on its own.

    A  C1 for every lambda in {0.03, 0.1, 0.3, 1.0} and every calibration seed:
       3000 updates, checkpoints 0, 25, 50, 75, 100, 150, 200, 300, 500, 1000,
       2000, 3000
    B  A_lin at every checkpoint (d2c.py --alin-only: linear_std P2 on E1's
       diag_fit / diag_eval, maximum over the digit-position points except
       emb). Step 0 once per seed (the initialization is the same for every
       lambda; checked by the step-0 parameter hash of every run).
       theta_s = c0 + 0.5 (A_lin_s(0) - c0), c0 = 1/52.
       lambda = the smallest candidate with A_lin(t) > theta_s for every
       calibration seed s and every checkpoint t in 50..3000. Only readability
       is used; the learning metrics of the calibration runs are recorded and
       reported, never used. No candidate: F4, stop (the range is not widened).
    C  C2 with lambda2 = lambda for 300 updates on the same seeds: E_W^C2(lambda)
       = sum_{u=1..300} r_u^2. E_W^C1 = the same sum of the C1 calibration run
       at the selected lambda. Both averaged over the three seeds;
       lambda2 = lambda * sqrt(mean E_W^C1 / mean E_W^C2(lambda)), clipped to
       [lambda/10, 10 lambda]; reaching a bound is reported. E_W^C2 = 0 or not
       finite: F4. One shot; no iteration.
Exit 0 if both arms are calibrated; 4 for F4; 3 for any other failure; 7 at the cap.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e2c_common as C  # noqa: E402
from s1_budget import STAGE1, Ledger, run_pool  # noqa: E402

OUT = os.path.join(STAGE1, "gate4")
ARMS = ("openmythos", "transformer")
PY = sys.executable
C0_P2 = 1 / 52
RULE_STEPS = tuple(t for t in C.CAL_STEPS if 50 <= t <= 3000)


def lam_tag(lam):
    return str(lam).replace(".", "p")


def phase_a():
    j = []
    for arm in ARMS:  # OpenMythos first (longest)
        for lam in C.LAMBDA_CANDIDATES:
            for s in C.CAL_SEEDS:
                tag = f"C1_{arm}_s{s}_lam{lam_tag(lam)}"
                j.append((f"train_{tag}", [PY, os.path.join(HERE, "train_e2c.py"), "--cond", "C1", "--lam", str(lam), "--arm", arm,
                                           "--seed", str(s), "--steps", "3000",
                                           "--save-at", ",".join(str(t) for t in C.CAL_STEPS if t),
                                           "--ckpt-dir", f"{OUT}/ckpt/lam{lam_tag(lam)}", "--out", f"{OUT}/runs/{tag}.json"]))
    return j


def phase_b():
    j = []
    for arm in ARMS:
        for s in C.CAL_SEEDS:  # step 0: the common initialization (from the lambda 0.03 run)
            j.append((f"alin_{arm}_s{s}_step0", alin_cmd(arm, s, 0, C.LAMBDA_CANDIDATES[0])))
            for lam in C.LAMBDA_CANDIDATES:
                for t in C.CAL_STEPS:
                    if t:
                        j.append((f"alin_{arm}_s{s}_lam{lam_tag(lam)}_step{t}", alin_cmd(arm, s, t, lam)))
    return j


def alin_cmd(arm, s, t, lam):
    tag = f"{arm}_s{s}_step0" if t == 0 else f"{arm}_s{s}_lam{lam_tag(lam)}_step{t}"
    return [PY, os.path.join(HERE, "d2c.py"), "--alin-only", "--arm", arm, "--seed", str(s), "--step", str(t),
            "--ckpt", f"{OUT}/ckpt/lam{lam_tag(lam)}/C1_{arm}_s{s}_step{t}.pt", "--out", f"{OUT}/alin/{tag}.json"]


def phase_c(sel):
    j = []
    for arm, lam in sel.items():
        for s in C.CAL_SEEDS:
            tag = f"C2_{arm}_s{s}_lam{lam_tag(lam)}"
            j.append((f"train_{tag}", [PY, os.path.join(HERE, "train_e2c.py"), "--cond", "C2", "--lam", str(lam), "--arm", arm,
                                       "--seed", str(s), "--steps", str(C.W_UPDATES), "--save-at", str(C.W_UPDATES),
                                       "--ckpt-dir", f"{OUT}/ckpt/c2", "--out", f"{OUT}/runs/{tag}.json"]))
    return j


def run_record(cond, arm, s, lam):
    return json.load(open(f"{OUT}/runs/{cond}_{arm}_s{s}_lam{lam_tag(lam)}.json"))


def select(arm):
    alin = lambda s, t, lam: json.load(open(f"{OUT}/alin/{arm}_s{s}_step0.json" if t == 0 else  # noqa: E731
                                            f"{OUT}/alin/{arm}_s{s}_lam{lam_tag(lam)}_step{t}.json"))["A_lin"]
    a0 = {s: alin(s, 0, None) for s in C.CAL_SEEDS}
    theta = {s: C0_P2 + 0.5 * (a0[s] - C0_P2) for s in C.CAL_SEEDS}
    init = {lam: {s: run_record("C1", arm, s, lam)["init_param_sha256"] for s in C.CAL_SEEDS} for lam in C.LAMBDA_CANDIDATES}
    same_init = all(init[lam][s] == init[C.LAMBDA_CANDIDATES[0]][s] for lam in C.LAMBDA_CANDIDATES for s in C.CAL_SEEDS)
    cand = {}
    for lam in C.LAMBDA_CANDIDATES:
        tab = {s: {t: alin(s, t, lam) for t in C.CAL_STEPS if t} for s in C.CAL_SEEDS}
        fails = [{"seed": s, "step": t, "A_lin": tab[s][t], "theta": theta[s]} for s in C.CAL_SEEDS for t in RULE_STEPS
                 if not tab[s][t] > theta[s]]
        learn = {s: {"dev_last": run_record("C1", arm, s, lam)["dev_log"][-1],
                     "aux_loss_last": run_record("C1", arm, s, lam)["aux_loss_every_step"][-1]} for s in C.CAL_SEEDS}
        cand[str(lam)] = {"A_lin": tab, "min_A_lin_50_3000": {s: min(tab[s][t] for t in RULE_STEPS) for s in C.CAL_SEEDS},
                          "failures": fails, "qualifies": not fails, "learning_metrics_reported_not_used": learn}
    q = [lam for lam in C.LAMBDA_CANDIDATES if cand[str(lam)]["qualifies"]]
    return {"A_lin_step0": a0, "theta": theta, "same_initialization_across_lambda": same_init,
            "rule": "smallest lambda with A_lin(t) > theta_s for all s in 91-93 and all t in " + str(list(RULE_STEPS)),
            "candidates": cand, "selected_lambda": q[0] if q else None}


def lambda2(arm, lam):
    e1 = {s: run_record("C1", arm, s, lam)["E_W"] for s in C.CAL_SEEDS}
    e2 = {s: run_record("C2", arm, s, lam)["E_W"] for s in C.CAL_SEEDS}
    m1, m2 = sum(e1.values()) / 3, sum(e2.values()) / 3
    out = {"lambda": lam, "E_W_C1_per_seed": e1, "E_W_C2_at_lambda_per_seed": e2, "mean_E_W_C1": m1, "mean_E_W_C2": m2,
           "clip_share_W_C1": {s: run_record("C1", arm, s, lam)["clip_share_W"] for s in C.CAL_SEEDS},
           "clip_share_W_C2": {s: run_record("C2", arm, s, lam)["clip_share_W"] for s in C.CAL_SEEDS},
           "E_W_after_clip_C1": {s: run_record("C1", arm, s, lam)["E_W_after_clip"] for s in C.CAL_SEEDS},
           "E_W_after_clip_C2": {s: run_record("C2", arm, s, lam)["E_W_after_clip"] for s in C.CAL_SEEDS}}
    if not (m2 > 0 and math.isfinite(m2) and math.isfinite(m1)):
        out["F4"] = "E_W^C2(lambda) = 0 or not finite"
        return out
    raw = lam * math.sqrt(m1 / m2)
    lo, hi = lam / 10, 10 * lam
    out.update({"lambda2_unclipped": raw, "bounds": [lo, hi], "lambda2": min(max(raw, lo), hi),
                "at_bound": raw <= lo or raw >= hi})
    return out


def main():
    led = Ledger()
    for d in ("runs", "alin", "logs"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    res = {"seeds": list(C.CAL_SEEDS), "candidates": list(C.LAMBDA_CANDIDATES), "checkpoints": list(C.CAL_STEPS)}

    def stop(code, why):
        res["stopped"] = why
        res["stage1_ledger_seconds"] = led.total()
        json.dump(res, open(os.path.join(OUT, "calibration.json"), "w"), indent=1)
        print(json.dumps(res.get("selection_summary", res.get("stopped")), indent=1))
        print("GATE 4 STOP:", why)
        sys.exit(code)

    with led.job("gate4") as job:
        for phase, jobs in (("A", phase_a()), ("B", phase_b())):
            st, info = run_pool(jobs, job, width=4, log_dir=os.path.join(OUT, "logs"))
            res[f"pool_{phase}"] = [st, info]
            if st != "ok":
                stop(7 if st == "cap" else 3, f"phase {phase}: {st} {info}")
        res["lambda_calibration"] = {arm: select(arm) for arm in ARMS}
        sel = {arm: res["lambda_calibration"][arm]["selected_lambda"] for arm in ARMS}
        res["selection_summary"] = {"selected_lambda": sel}
        if not all(res["lambda_calibration"][a]["same_initialization_across_lambda"] for a in ARMS):
            stop(3, "initializations differ across lambda runs (F8)")
        if any(v is None for v in sel.values()):
            stop(4, "F4: no lambda candidate meets the rule for " + ", ".join(a for a, v in sel.items() if v is None))
        st, info = run_pool(phase_c(sel), job, width=4, log_dir=os.path.join(OUT, "logs"))
        res["pool_C"] = [st, info]
        if st != "ok":
            stop(7 if st == "cap" else 3, f"phase C: {st} {info}")
    res["lambda2_calibration"] = {arm: lambda2(arm, sel[arm]) for arm in ARMS}
    if any("F4" in v for v in res["lambda2_calibration"].values()):
        stop(4, "F4: lambda2 calibration denominator 0 or not finite")
    res["selection_summary"]["lambda2"] = {a: res["lambda2_calibration"][a]["lambda2"] for a in ARMS}
    res["selection_summary"]["lambda2_at_bound"] = {a: res["lambda2_calibration"][a]["at_bound"] for a in ARMS}
    res["pass"] = True
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "calibration.json"), "w"), indent=1)
    json.dump({"lambda": sel, "lambda2": res["selection_summary"]["lambda2"], "note":
               "stage-1 calibration result; enters the stage-2 freeze file only with the stage-2 authorization"},
              open(os.path.join(OUT, "lambda_selected.json"), "w"), indent=1)
    print(json.dumps(res["selection_summary"], indent=1))
    print("GATE 4 PASS", f"ledger {led.total():.0f} s")
    sys.exit(0)


if __name__ == "__main__":
    main()
