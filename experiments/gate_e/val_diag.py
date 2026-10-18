#!/usr/bin/env python3
"""
Pre-run validation (PREREGISTRATION 6.4): on non-formal K=4 models (seed 99:
the rebuilt initialization and the 200-step model of val_train.py), the Gate E
diagnostic code must reproduce the archived Gate D code on Gate D's own
diagnostic sets (read only):
    M0 vs d0.model_checks    every pass flag; numeric details equal
    M1 vs d1                 every per-question array bitwise equal
    M2 vs d2                 D2-E: linear_std = d2 "probes", mlp = d2 "mlp"
                             (where Gate D ran it); D2-F: linear_std_F = d2
                             "probes_F", mlp_F = d2 "mlp_F"; planted
    M4 vs d3 (descriptive)   statement shares of the layers Gate D uses,
                             readout -> query token, digit -> own letter
    M5 vs d5                 on reduced sizes (20 bodies, R = 8, 40 pool_c
                             bodies, 200 bootstrap draws)
Tolerance fixed before running: bitwise equal, or |a - b| <= 1e-6 * max(1, |b|).
Writes validation/diag_equivalence.json; exits non-zero on any mismatch.
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

from e_common import Geom, family_tensors, jsonable, load_state, rebuild_init  # noqa: E402
from e_m0 import model_checks  # noqa: E402
from e_m1 import per_question  # noqa: E402
from e_m2 import run_m2  # noqa: E402
from e_m4 import run_m4  # noqa: E402
from e_m5 import run_m5  # noqa: E402
import common as gd_common  # noqa: E402  gate_d
import d0 as gd0  # noqa: E402
import d1 as gd1  # noqa: E402
import d2 as gd2  # noqa: E402
import d3 as gd3  # noqa: E402
import d5 as gd5  # noqa: E402
from runner import Runner  # noqa: E402

TOL = 1e-6


class Cmp:
    def __init__(self):
        self.n, self.bad = 0, []

    def num(self, where, a, b):
        self.n += 1
        if a is None or b is None:
            if a is not b:
                self.bad.append((where, a, b))
            return
        a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
        if a.shape != b.shape or not np.all(np.abs(a - b) <= TOL * np.maximum(1, np.abs(b))):
            self.bad.append((where, a.tolist() if a.size < 20 else "array", b.tolist() if b.size < 20 else "array"))

    def eq(self, where, a, b):
        self.n += 1
        if a != b:
            self.bad.append((where, a, b))


def compare_state(model, label, c):
    g = Geom(4)
    ev_rows, fit_rows = gd_common.load_diag("diag_eval"), gd_common.load_diag("diag_fit")
    ev_d, fit_d = gd_common.family_tensors(ev_rows), gd_common.family_tensors(fit_rows)
    ev_e, fit_e = family_tensors(ev_rows, g), family_tensors(fit_rows, g)
    for a, b in zip(ev_d, ev_e):
        c.eq(f"{label}:family_tensors", bool(torch.equal(a, b)), True)
    run = Runner(model)
    # M0
    r_d = gd0.model_checks(model, ev_rows)
    r_e = model_checks(model, ev_rows, g)
    for k, v in r_d.items():
        if isinstance(v, dict) and "pass" in v:
            c.eq(f"{label}:M0:{k}:pass", v["pass"], r_e[k]["pass"])
    for k in ("attention_reconstruction", "tied_decomposition"):
        c.num(f"{label}:M0:{k}", r_d[k]["max_diff"], r_e[k]["max_diff"])
    # M1
    L = gd1.readout_logits(run, ev_d[0])
    qd, pd = gd1.per_question(L, ev_d[1], ev_d[4], ev_d[3])
    qe, pe = per_question(L, ev_e[1], ev_e[4], 4)
    c.eq(f"{label}:M1:pred", bool(torch.equal(pd, pe)), True)
    for k in qd:
        c.eq(f"{label}:M1:{k}:bitwise", bool(np.array_equal(qd[k], qe[k])), True)
    # M2
    d2r = gd2.run_d2(run, fit_d, fit_rows, ev_d, ev_rows)
    m2r, _ = run_m2(run, fit_e, fit_rows, ev_e, ev_rows, g)
    for k, v in d2r["probes"].items():
        if "acc" in v:
            c.num(f"{label}:M2:linear:{k}:acc", v["acc"], m2r["linear_std"][k]["acc"])
            c.num(f"{label}:M2:linear:{k}:ci", v["ci95"], m2r["linear_std"][k]["ci95"])
            c.num(f"{label}:M2:linear:{k}:shuffled", v["shuffled"]["acc"], m2r["linear_std"][k]["shuffled"]["acc"])
            c.eq(f"{label}:M2:linear:{k}:decision", v["decision"], m2r["linear_std"][k]["decision"])
        else:
            c.eq(f"{label}:M2:linear:{k}:skipped", "skipped" in m2r["linear_std"][k], True)
    for k, v in d2r["mlp"].items():
        c.num(f"{label}:M2:mlp:{k}:acc", v["acc"], m2r["mlp"][k]["acc"])
        c.num(f"{label}:M2:mlp:{k}:control", v["emb_control"]["acc"], m2r["mlp"][k]["emb_control"]["acc"])
        c.eq(f"{label}:M2:mlp:{k}:decision", v["decision"], m2r["mlp"][k]["decision"])
    for k, v in d2r["probes_F"].items():  # D2-F (OpenMythos loop points)
        e = m2r["linear_std_F"][k]
        if "acc" in v:
            c.num(f"{label}:M2F:linear:{k}:acc", v["acc"], e["acc"])
            c.num(f"{label}:M2F:linear:{k}:shuffled", v["shuffled"]["acc"], e["shuffled"]["acc"])
            c.eq(f"{label}:M2F:linear:{k}:decision", v["decision"], e["decision"])
        else:
            c.eq(f"{label}:M2F:linear:{k}:skipped", "skipped" in e, True)
    c.eq(f"{label}:M2F:keys", sorted(d2r["probes_F"]), sorted(m2r["linear_std_F"]))
    c.eq(f"{label}:M2F:mlp_keys", sorted(d2r["mlp_F"]), sorted(m2r["mlp_F"]))
    for k, v in d2r["mlp_F"].items():
        c.num(f"{label}:M2F:mlp:{k}:acc", v["acc"], m2r["mlp_F"][k]["acc"])
        c.eq(f"{label}:M2F:mlp:{k}:decision", v["decision"], m2r["mlp_F"][k]["decision"])
    for k, v in d2r["planted"].items():
        for a, rr in v["by_alpha"].items():
            c.num(f"{label}:M2:planted:{k}:{a}", rr["acc"], m2r["planted"][k]["by_alpha"][a]["acc"])
    # M4
    d3r = gd3.run_d3(run, ev_d, n_perm=10)
    m4r = run_m4(run, ev_e, g)
    for layer, v in d3r["descriptive"]["share_by_layer_head"].items():
        c.num(f"{label}:M4:share:{layer}", v, m4r["share_queried_by_layer_head"][layer])
    for layer, v in d3r["descriptive"]["attn_readout_to_query_token"].items():
        c.num(f"{label}:M4:readout_query:{layer}", v, m4r["readout_to_query_token"][layer])
    for layer, v in d3r["descriptive"]["attn_digit_to_own_variable"].items():
        c.num(f"{label}:M4:digit_own:{layer}", v, m4r["digit_to_own_letter"][layer])
    # M5 (reduced sizes; separate model copies so hooks never mix)
    pool_b, pool_c = gd_common.load_diag("pool_b"), gd_common.load_diag("pool_c")[:40]
    kw = dict(n_bodies_a=20, R=8, n_boot=200)
    d5r = gd5.run_d5(copy.deepcopy(model), ev_rows, fit_rows[:60], pool_b, pool_c, **kw)
    m5r = run_m5(copy.deepcopy(model), ev_rows, fit_rows[:60], pool_b, pool_c, g, **kw)
    for grp, v in d5r["a_per_question"].items():
        e = m5r["a_per_question"][grp]
        for k in ("V_b", "S", "S_share", "cos_between_queries"):
            c.num(f"{label}:M5:a:{grp}:{k}", v[k], e[k])
        for s in ("O", "P", "F"):
            c.num(f"{label}:M5:a:{grp}:pred:{s}", v["pred_trvar"][s], e["pred_trvar"][s])
    for s in ("O", "P", "F"):
        for grp, val in d5r["b_batches"][s]["trvar"].items():
            c.num(f"{label}:M5:b:{s}:{grp}", val, m5r["b_batches"][s]["trvar"][grp])
        c.num(f"{label}:M5:b:{s}:snr", d5r["b_batches"][s]["s_along_u"]["snr"], m5r["b_batches"][s]["s_along_u"]["snr"])
    for grp, v in d5r["c_local_direction"]["groups"].items():
        e = m5r["c_local_direction"]["groups"][grp]
        for k in ("d_dot_gradJ", "d_dot_gradK", "cos_d_gradJ", "norm_grad_L_roots", "norm_grad_L_within"):
            c.num(f"{label}:M5:c:{grp}:{k}", v[k], e[k])
    c.num(f"{label}:M5:J_fit", d5r["c_local_direction"]["J_fit"], m5r["c_local_direction"]["J_fit"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True, help="directory of val_train.py (200-step K=4 models)")
    args = ap.parse_args()
    torch.set_num_threads(1)
    out, ok = {"tolerance": TOL, "states": {}}, True
    for arm in ("openmythos", "transformer"):
        for label, model in ((f"{arm}_init", rebuild_init(arm, 4, 99)),
                             (f"{arm}_step200", load_state(arm, 4, 99, 200,
                              path=os.path.join(args.scratch, f"tk4_{arm}", f"K4_{arm}_s99_step200.pt")))):
            model.eval()
            c = Cmp()
            compare_state(model, label, c)
            out["states"][label] = {"comparisons": c.n, "mismatches": [str(b) for b in c.bad]}
            ok &= not c.bad
            print(label, c.n, "comparisons,", len(c.bad), "mismatches", flush=True)
    out["pass"] = ok
    with open(os.path.join(HERE, "validation", "diag_equivalence.json"), "w") as f:
        json.dump(jsonable(out), f, indent=1, ensure_ascii=False)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
