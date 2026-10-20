#!/usr/bin/env python3
"""
D2c, the reduced E2-c diagnostics of one model state (E2C_PREREG_DRAFT 5.2,
5.3), with E1's verified code and definitions on the measurement sets only
(diag_fit, diag_eval, minpair; manifest-checked by e_common.load_set):

    every checkpoint      M1 (e_m1.run_m1, unchanged)
                          M2-P2: linear_std and linear_raw at every probe point
                          (emb included: the same-subset emb control), each with
                          its shuffled-label control
    0, 75, 150, 3000, 12000  M2-P2 MLP with its own emb control; the planted-
                          signal check of P2 at the last point; M3 (e_m3.run_m3,
                          controls enforced); M6 (e_masks.m6_summary)
    0, 12000              M0 (e_m0.model_checks)
No M4, M5, P0, P1, P3 (5.3). The P2 part repeats e_m2.run_m2 line for line
for probe P2 (each fit is seeded on its own, so leaving the other probes out
does not change P2; R3 checks every value against E1). The planted check
draws P1's random directions first and discards them, so P2's directions are
the ones E1 drew.

--alin-only: only the linear_std P2 accuracy at the digit-position points
(the A_lin of the lambda calibration, 3.5); same fits, no controls.
Exit 3 on a hard check failure (M0, M3 controls; F6): nothing is written.

    python experiments/gate_e/e2c/d2c.py --arm openmythos --seed 1 --step 75 --ckpt PATH --out OUT.json
"""

import argparse
import os
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402
from e_common import LETTERS, Geom, atomic_write_json, family_tensors, jsonable, load_set, load_state, param_hash  # noqa: E402
from e_m0 import model_checks  # noqa: E402
from e_m1 import run_m1  # noqa: E402
from e_m2 import baselines, clearly_above_chance, fit_linear_raw, loop_index  # noqa: E402
from e_m3 import IntegrityError, run_m3  # noqa: E402
from e_masks import act_masks, complete, m6_summary  # noqa: E402
from d2 import ALPHAS, acc_ci, decide, fit_linear, fit_mlp, grouped_shuffle, majority_share, predict_linear  # noqa: E402
from runner import Runner, probe_points  # noqa: E402


def m2_p2(runner, fit_fam, fit_rows, ev_fam, ev_rows, g, Mf, Me, heavy, alin_only=False):
    K = g.K
    C_DECISION, N_CLASSES = baselines(K)
    points = probe_points(runner.arm)
    feat = [p for p in points if not (alin_only and p == "emb")]

    def features(fam):
        rec = runner.run(fam[0], record=set(feat))[1]
        return {p: {"digits": rec[p][:, list(g.DIGIT_POS)]} for p in feat}

    Ff, Fe = features(fit_fam), features(ev_fam)

    def p2_labels(rows):
        return torch.tensor([[LETTERS.index(r["queries"][k]) for k in range(K)] for r in rows])

    Lf, Le = p2_labels(fit_rows), p2_labels(ev_rows)
    first_f, first_e = torch.arange(0, len(fit_fam[3]), K), torch.arange(0, len(ev_fam[3]), K)

    def masks_for(M, p):
        n = M["valid"].shape[0]
        t = loop_index(p)
        if t is None:
            return torch.ones(n, dtype=torch.bool), torch.ones(n // K, dtype=torch.bool)
        q = complete(M["valid"][:, t], K)
        return q, q.view(-1, K)[:, 0]

    def data(p, feat_point=None):
        fp = feat_point or p
        _, bfm = masks_for(Mf, p)
        _, bem = masks_for(Me, p)
        D = Ff[fp]["digits"].shape[-1]
        Xf = Ff[fp]["digits"][first_f][bfm].reshape(-1, D)
        Xe = Fe[fp]["digits"][first_e][bem].reshape(-1, D)
        return (Xf, Lf[bfm].reshape(-1), np.repeat(np.flatnonzero(bfm.numpy()), K),
                Xe, Le[bem].reshape(-1), np.repeat(np.flatnonzero(bem.numpy()), K))

    def linear(Xf, yf, bf, Xe, ye, be, raw):
        Cn = N_CLASSES["P2"]
        fit = fit_linear_raw if raw else fit_linear
        m = fit(Xf, yf, Cn)
        r = acc_ci(predict_linear(m, Xe) == ye, be)
        r["fit_grad_max"] = m["grad_max"]
        if alin_only:
            return r
        ms = fit(Xf, grouped_shuffle(yf, bf, "across"), Cn)
        sh = acc_ci(predict_linear(ms, Xe) == ye, be)
        r["shuffled"] = sh
        c0 = C_DECISION["P2"]
        mshare = majority_share(yf)
        c_hi = max(c0, mshare)
        r.update({"baseline_c0": c0, "baseline_c_hi": c_hi, "fit_majority_share": mshare,
                  "n_eval_bodies": int(len(np.unique(be)))})
        r["decision"] = decide(r, sh, c_hi, c0)
        r["clearly_above_chance(descriptive)"] = clearly_above_chance(r, sh, c0)
        return r

    def mlp(p):
        c0 = C_DECISION["P2"]
        Xf, yf, bf, Xe, ye, be = data(p)
        Cf, cyf, cbf, Ce, cye, cbe = data(p, feat_point="emb")
        assert torch.equal(yf, cyf) and torch.equal(ye, cye) and (bf == cbf).all() and (be == cbe).all()
        fc = fit_mlp(Cf, cyf, N_CLASSES["P2"])
        ctrl = acc_ci(fc(Ce) == cye, cbe)
        ctrl["at_baseline"] = ctrl["ci95"][1] <= c0 + 0.10
        f = fit_mlp(Xf, yf, N_CLASSES["P2"])
        r = acc_ci(f(Xe) == ye, be)
        r["emb_control"] = ctrl
        r["void"] = not ctrl["at_baseline"]
        c_hi = max(c0, majority_share(yf))
        r["decision"] = "作废（控制未通过）" if r["void"] else decide(r, None, c_hi, c0)
        r["clearly_above_chance(descriptive)"] = (not r["void"]) and clearly_above_chance(r, None, c0)
        return r

    res = {"linear_std": {}} if alin_only else {"linear_std": {}, "linear_raw": {}}
    if heavy and not alin_only:
        res.update({"mlp": {}, "planted": {}})
    for p in feat:
        key = f"P2@{p}"
        Xf, yf, bf, Xe, ye, be = data(p)
        if len(np.unique(bf)) < 0.5 * len(fit_rows) or len(np.unique(be)) < 0.5 * len(ev_rows):
            skip = {"skipped": "fewer than half of the bodies are complete for this point",
                    "n_fit_bodies": int(len(np.unique(bf))), "n_eval_bodies": int(len(np.unique(be)))}
            for k in res:
                if k != "planted":
                    res[k][key] = skip
            continue
        res["linear_std"][key] = linear(Xf, yf, bf, Xe, ye, be, raw=False)
        if alin_only:
            continue
        res["linear_raw"][key] = linear(Xf, yf, bf, Xe, ye, be, raw=True)
        if heavy:
            res["mlp"][key] = mlp(p)
    if heavy and not alin_only:
        last = points[-1]
        gen = torch.Generator().manual_seed(7)
        Xf, yf, bf, Xe, ye, be = data(last)
        torch.randn(N_CLASSES["P1"], Xf.shape[1], generator=gen)  # E1 drew P1's directions first
        Cn = N_CLASSES["P2"]
        Rp = torch.randn(Cn, Xf.shape[1], generator=gen)
        Rp = Rp / Rp.norm(dim=1, keepdim=True)
        scale = Xf.norm(dim=1).mean()
        out = {}
        for a in ALPHAS:
            m = fit_linear(Xf + a * scale * Rp[yf], yf, Cn)
            r = acc_ci(predict_linear(m, Xe + a * scale * Rp[ye]) == ye, be)
            r["decision"] = decide(r, None, C_DECISION["P2"])
            out[str(a)] = r
        det = [a for a in ALPHAS if out[str(a)]["decision"] == "检测到可线性解码的信息"]
        res["planted"][f"P2@{last}"] = {"by_alpha": out, "smallest_detected_alpha": det[0] if det else None,
                                        "mean_feature_norm": float(scale)}
    return res


def a_lin(m2):
    """A_lin: maximum linear_std P2 accuracy over the digit-position points except emb (e_events.a_max)."""
    v = [r["acc"] for k, r in m2["linear_std"].items() if k.startswith("P2@") and k != "P2@emb" and "acc" in r]
    return max(v) if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--alin-only", action="store_true")
    args = ap.parse_args()
    torch.set_num_threads(1)
    g = Geom(2)
    model = load_state(args.arm, 2, args.seed, args.step, path=args.ckpt)
    runner = Runner(model)
    fit_rows, ev_rows = load_set("diag_fit"), load_set("diag_eval")
    fit, ev = family_tensors(fit_rows, g), family_tensors(ev_rows, g)
    heavy = args.step in C.D2C_HEAVY and not args.alin_only
    out = {"arm": args.arm, "seed": args.seed, "step": args.step, "ckpt": os.path.basename(args.ckpt),
           "param_sha256": param_hash(model), "alin_only": args.alin_only, "heavy": heavy, "seconds": {}}
    try:
        if args.step in C.D2C_M0 and not args.alin_only:
            t = time.time()
            out["M0"] = model_checks(model, ev_rows, g)
            out["seconds"]["M0"] = time.time() - t
            if not out["M0"]["pass"]:
                raise IntegrityError("M0 failed")
        if not args.alin_only:
            t = time.time()
            out["M1"] = run_m1(runner, ev, fit, g)
            out["seconds"]["M1"] = time.time() - t
        t = time.time()
        Mf, Me = act_masks(runner, fit[0], g), act_masks(runner, ev[0], g)
        out["M2"] = m2_p2(runner, fit, fit_rows, ev, ev_rows, g, Mf, Me, heavy, alin_only=args.alin_only)
        out["A_lin"] = a_lin(out["M2"])
        if heavy:
            out["M6"] = m6_summary(Me, g)
        out["seconds"]["M2+M6"] = time.time() - t
        if heavy:
            t = time.time()
            out["M3"] = run_m3(runner, ev_rows, load_set("minpair"), g)
            out["seconds"]["M3"] = time.time() - t
    except IntegrityError as e:
        print(f"HARD CHECK FAILURE (F6) {args.arm} s{args.seed} step{args.step}: {e}", file=sys.stderr)
        sys.exit(3)
    atomic_write_json(args.out, jsonable(out))
    print(f"{args.out} done in {sum(out['seconds'].values()):.0f}s {out['seconds']}")


if __name__ == "__main__":
    main()
