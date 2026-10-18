#!/usr/bin/env python3
"""
Pre-run validation of the M2 / M3 additions (PREREGISTRATION 9.10, 10.1), on
synthetic data and non-formal seed-99 models only. Writes
validation/m2m3_checks.json; exits non-zero if any check fails.

M2
  raw_vs_std     fit_linear_raw on features standardized beforehand gives
                 exactly fit_linear's weights and predictions
  xor            a linearly unreadable, non-linearly readable code: linear
                 probe "not detected", MLP "detected"
M3 (pure statistics, synthetic)
  erasure        changes at the noise level only -> "not detected", s = 0
  scaled_1e-3    changes 1e-3 x sigma -> "found"
  local_1pct     1% of the pairs change, the rest at the noise level ->
                 "found" with s = 0.01 (a mean cannot hide a local change)
  sigma_zero     sigma = 0 -> "not computable", no NaN / infinity, excluded
                 from pooling and from t_M3
M3 (non-formal models, K=2 and K=4, both arms, init and 200 steps)
  controls       negative (query swap) and positive (own letter at emb)
                 controls pass with the hard rule; the emb '=' position has
                 sigma = 0 and is reported as not computable
  erased model   all letter embeddings set to their mean: the letter positions
                 have sigma = 0, so the positive control cannot run and counts
                 as failed (run 1 expected a plain failure and found the
                 vacuous pass this check now guards against); every
                 digit-position record point "not detected", t_M3 true
  scaled model   letter embeddings shrunk to 1e-3 of their spread around the
                 mean: controls pass, digit positions after emb "found"
"""

import argparse
import copy
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)

from d2 import acc_ci, decide, fit_linear, fit_mlp, predict_linear  # noqa: E402  gate_d
from e_common import LETTERS, Geom, jsonable, load_set, load_state, rebuild_init  # noqa: E402
from e_m2 import DETECTED, NOT_DETECTED as LIN_NOT, fit_linear_raw  # noqa: E402
from e_m3 import FOUND, NOT_COMPUTABLE, NOT_DETECTED, pooled, run_m3, sensitivity_stats, t_m3_condition  # noqa: E402
from runner import Runner  # noqa: E402

NO_PAIRS = "无有效最小对"  # loop record point not executed by any pair (single-sample ACT)


def m2_checks():
    out = {}
    g = torch.Generator().manual_seed(0)
    X = torch.randn(600, 16, generator=g) * (10 ** (torch.rand(16, generator=g) * 4 - 3))
    y = torch.randint(0, 5, (600,), generator=g)
    X[:, :5] += 0.5 * torch.nn.functional.one_hot(y, 5) * X[:, :5].std(0)
    a = fit_linear(X, y, 5)
    mu, sd = X.mean(0), X.std(0).clamp_min(1e-6)
    b = fit_linear_raw((X - mu) / sd, y, 5)
    out["raw_vs_std"] = {"W_bitwise": bool(torch.equal(a["W"], b["W"])), "b_bitwise": bool(torch.equal(a["b"], b["b"])),
                         "pred_equal": bool(torch.equal(predict_linear(a, X), predict_linear(b, (X - mu) / sd)))}
    out["raw_vs_std"]["pass"] = all(out["raw_vs_std"].values())
    s = torch.randint(0, 2, (2, 2000), generator=g) * 2 - 1
    yx = (s[0] == s[1]).long()
    Xx = torch.cat([s.T.float() + 0.1 * torch.randn(2000, 2, generator=g), torch.randn(2000, 6, generator=g)], 1)
    grp = np.arange(1000)
    lin = fit_linear(Xx[:1000], yx[:1000], 2)
    r_lin = acc_ci(predict_linear(lin, Xx[1000:]) == yx[1000:], grp)
    mlp = fit_mlp(Xx[:1000], yx[:1000], 2)
    r_mlp = acc_ci(mlp(Xx[1000:]) == yx[1000:], grp)
    c_hi = max(0.5, float(torch.bincount(yx[:1000]).max()) / 1000)
    out["xor"] = {"linear_acc": r_lin["acc"], "linear_decision": decide(r_lin, None, c_hi, 0.5),
                  "mlp_acc": r_mlp["acc"], "mlp_decision": decide(r_mlp, None, c_hi, 0.5)}
    out["xor"]["pass"] = out["xor"]["linear_decision"] == LIN_NOT and out["xor"]["mlp_decision"] == DETECTED
    return out


def m3_synthetic():
    out, rng = {}, np.random.default_rng(0)
    n = 1000
    bodies = np.arange(n) // 6
    eps = {b: 1e-7 for b in range(n // 6 + 1)}
    cases = {
        "erasure": rng.uniform(0, 1e-7, n),
        "scaled_1e-3": np.full(n, 1e-3),
        "local_1pct": np.where(np.arange(n) % 100 == 0, 1e-2, rng.uniform(0, 1e-7, n)),
    }
    for name, diff in cases.items():
        st, above = sensitivity_stats(diff, eps, bodies, 1.0)
        po = pooled({"p": (st, above)}, {"p": bodies}, {"p": np.ones(n, dtype=int)})
        out[name] = {"label": st["label"], "pooled_s": po["s"], "mean_delta": st["delta"]["mean"], "tau": st["tau"]}
    out["erasure"]["pass"] = out["erasure"]["label"] == NOT_DETECTED and out["erasure"]["pooled_s"] == 0
    out["scaled_1e-3"]["pass"] = out["scaled_1e-3"]["label"] == FOUND and out["scaled_1e-3"]["pooled_s"] == 1
    out["local_1pct"]["pass"] = out["local_1pct"]["label"] == FOUND and abs(out["local_1pct"]["pooled_s"] - 0.01) < 1e-12
    st, above = sensitivity_stats(np.zeros(n), {b: 0.0 for b in range(n // 6 + 1)}, bodies, 0.0)
    po = pooled({"p": (st, above)}, {"p": bodies}, {"p": np.ones(n, dtype=int)})
    try:
        json.dumps(jsonable(st), allow_nan=False)
        finite = True
    except ValueError:
        finite = False
    t = t_m3_condition({"emb": NOT_DETECTED, "e": NOT_COMPUTABLE, "h1": NOT_DETECTED})
    out["sigma_zero"] = {"label": st["label"], "above_is_none": above is None, "finite_json": finite,
                         "pooled_label": po["label"], "t_M3_excluded": t["excluded_not_computable"],
                         "t_M3_all_not_detected": t["all_not_detected"]}
    out["sigma_zero"]["pass"] = (st["label"] == NOT_COMPUTABLE and above is None and finite
                                 and po["label"] == NOT_COMPUTABLE and t["excluded_not_computable"] == ["e"]
                                 and t["all_not_detected"] is True)
    t2 = t_m3_condition({"emb": NOT_DETECTED, "e": NOT_COMPUTABLE})
    out["sigma_zero"]["only_not_computable_gives_false"] = t2["all_not_detected"] is False
    out["sigma_zero"]["pass"] &= out["sigma_zero"]["only_not_computable_gives_false"]
    return out


def modify_letters(model, scale):
    m = copy.deepcopy(model)
    ids = torch.tensor([ord(c) for c in LETTERS])
    with torch.no_grad():
        W = m.embed.weight
        mean = W[ids].mean(0, keepdim=True)
        W[ids] = mean + scale * (W[ids] - mean)
    m.eval()
    return m


def summarize(r):
    return {"controls": {k: v["pass"] for k, v in r["controls"].items()},
            "digit_labels": {p: v["digit"]["label"] for p, v in r["pooled"].items()},
            "digit_s": {p: v["digit"].get("s") for p, v in r["pooled"].items()},
            "eq_emb_label": r["pooled"]["emb"]["eq"]["label"],
            "t_M3": r["t_M3_condition"]}


def m3_models(scratch):
    out, ok = {}, True
    for K, mp_name, ev_name in ((2, "minpair", "diag_eval"), (4, "minpair_k4", "diag_eval_k4")):
        g = Geom(K)
        ev, mp = load_set(ev_name), load_set(mp_name)
        for arm in ("openmythos", "transformer"):
            sub = f"k2a_{arm}" if K == 2 else f"tk4_{arm}"
            for label, model in (("init", rebuild_init(arm, K, 99)),
                                 ("step200", load_state(arm, K, 99, 200,
                                  path=os.path.join(scratch, sub, f"K{K}_{arm}_s99_step200.pt")))):
                model.eval()
                key = f"K{K}_{arm}_{label}"
                r = summarize(run_m3(Runner(model), ev, mp, g))  # hard controls
                r["json_finite"] = _finite(r)
                r["pass"] = all(r["controls"].values()) and r["eq_emb_label"] == NOT_COMPUTABLE and r["json_finite"]
                out[key] = r
                ok &= r["pass"]
                if label == "step200" and K == 2:
                    r_er = run_m3(Runner(modify_letters(model, 0.0)), ev, mp, g, enforce_controls=False)
                    er = summarize(r_er)
                    dig = {p: v for p, v in er["digit_labels"].items() if p != "emb" and v != NO_PAIRS}
                    er["positive_control_detail"] = r_er["controls"]["positive_own_letter_emb"]
                    er["pass"] = (not er["controls"]["positive_own_letter_emb"]
                                  and r_er["controls"]["positive_own_letter_emb"]["n_positions_run"] == 0
                                  and all(v == NOT_DETECTED for v in dig.values())
                                  and er["t_M3"]["all_not_detected"] is True)
                    out[f"{key}_erased"] = er
                    sc = summarize(run_m3(Runner(modify_letters(model, 1e-3)), ev, mp, g))
                    dig = {p: v for p, v in sc["digit_labels"].items() if p != "emb" and v != NO_PAIRS}
                    sc["pass"] = all(sc["controls"].values()) and all(v == FOUND for v in dig.values())
                    out[f"{key}_scaled_1e-3"] = sc
                    ok &= er["pass"] and sc["pass"]
                print(key, "ok" if out[key]["pass"] else "FAIL", flush=True)
    return out, ok


def _finite(obj):
    try:
        json.dumps(jsonable(obj), allow_nan=False)
        return True
    except ValueError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    args = ap.parse_args()
    torch.set_num_threads(1)
    res = {"m2": m2_checks(), "m3_synthetic": m3_synthetic()}
    ok = all(v["pass"] for v in res["m2"].values()) and all(v["pass"] for v in res["m3_synthetic"].values())
    print("synthetic", "ok" if ok else "FAIL", flush=True)
    res["m3_models"], ok_m = m3_models(args.scratch)
    res["pass"] = ok and ok_m
    with open(os.path.join(HERE, "validation", "m2m3_checks.json"), "w") as f:
        json.dump(jsonable(res), f, indent=1, ensure_ascii=False)
    print("pass" if res["pass"] else "FAIL")
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
