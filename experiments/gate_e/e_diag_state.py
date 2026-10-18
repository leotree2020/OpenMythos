#!/usr/bin/env python3
"""
Run M0-M6 on one model state with the frozen workload and write
results/<state>.json (PREREGISTRATION 4, 9, 10). Single-threaded. Exit 3 on a
hard integrity failure (an M0 check, an M3 control, the M5 tied-weight split,
or a parameter hash differing from the checkpoint manifest); nothing is
written for that state.

    python experiments/gate_e/e_diag_state.py --arm openmythos --K 2 --seed 1 --step 300
Non-formal states (validation, timing) pass --ckpt explicitly and
--no-manifest.
"""

import argparse
import json
import os
import sys
import time

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from e_common import Geom, family_tensors, jsonable, load_set, load_state, param_hash, state_name  # noqa: E402
from e_m0 import model_checks  # noqa: E402
from e_m1 import run_m1  # noqa: E402
from e_m2 import run_m2  # noqa: E402
from e_m3 import IntegrityError, run_m3  # noqa: E402
from e_m4 import run_m4  # noqa: E402
from e_m5 import run_m5  # noqa: E402
from e_masks import m6_summary  # noqa: E402
from runner import Runner  # noqa: E402  gate_d

# PREREGISTRATION 11.3, option A (approved): the first 500 bodies of diag_eval in
# file order (K=4: all 500 of diag_eval_k4), all K queries each; fixed here,
# never taken from the workload file
M5A_BODIES = 500

SETS_BY_K = {2: ("diag_fit", "diag_eval", "minpair", "pool_b_k2", "pool_c_k2"),
             4: ("diag_fit_k4", "diag_eval_k4", "minpair_k4", "pool_b_k4", "pool_c_k4")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--K", type=int, required=True, choices=[2, 4])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--ckpt", default=None, help="explicit checkpoint (non-formal states)")
    ap.add_argument("--out-dir", default=os.path.join(HERE, "results"))
    ap.add_argument("--workload", default=os.path.join(HERE, "timing.json"))
    ap.add_argument("--manifest", default=os.path.join(HERE, "checkpoints_manifest.json"))
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("--only", default="M0,M1,M2,M3,M4,M5", help="validation / timing only")
    args = ap.parse_args()
    torch.set_num_threads(1)
    wl = json.load(open(args.workload))["frozen_workload"]
    g = Geom(args.K)
    name = state_name(args.arm, args.K, args.seed, args.step)
    model = load_state(args.arm, args.K, args.seed, args.step, path=args.ckpt)
    h = param_hash(model)
    if not args.no_manifest:
        ref = json.load(open(args.manifest))["states"][name]["param_sha256"]
        if h != ref:
            print(f"INTEGRITY FAILURE {name}: parameter hash differs from the checkpoint manifest", file=sys.stderr)
            sys.exit(3)
    fit_n, ev_n, mp_n, pb_n, pc_n = SETS_BY_K[args.K]
    fit_rows, ev_rows = load_set(fit_n), load_set(ev_n)
    fit, ev = family_tensors(fit_rows, g), family_tensors(ev_rows, g)
    runner = Runner(model)
    only = set(args.only.split(","))
    out = {"state": name, "param_sha256": h, "workload": wl, "seconds": {}}
    try:
        if "M0" in only:
            t = time.time()
            out["M0"] = model_checks(model, ev_rows, g)
            out["seconds"]["M0"] = time.time() - t
            if not out["M0"]["pass"]:
                failed = [k for k, v in out["M0"].items() if isinstance(v, dict) and not v.get("pass", True)]
                raise IntegrityError(f"M0 failed: {failed}")
        if "M1" in only:
            t = time.time()
            out["M1"] = run_m1(runner, ev, fit, g)
            out["seconds"]["M1"] = time.time() - t
        masks = None
        if "M2" in only:
            t = time.time()
            out["M2"], masks = run_m2(runner, fit, fit_rows, ev, ev_rows, g,
                                      mlp_p13_when_detected=wl["mlp_p13_when_linear_detected"])
            out["M6"] = m6_summary(masks[1], g)
            out["seconds"]["M2+M6"] = time.time() - t
        if "M3" in only:
            t = time.time()
            out["M3"] = run_m3(runner, ev_rows, load_set(mp_n), g)
            out["seconds"]["M3"] = time.time() - t
        if "M4" in only:
            t = time.time()
            out["M4"] = run_m4(runner, ev, g)
            out["seconds"]["M4"] = time.time() - t
        if "M5" in only:
            t = time.time()
            if wl.get("m5a_bodies", M5A_BODIES) != M5A_BODIES:
                raise SystemExit(f"workload asks for m5a_bodies={wl['m5a_bodies']}; frozen at {M5A_BODIES} (11.3)")
            out["M5"] = run_m5(model, ev_rows, fit_rows, load_set(pb_n), load_set(pc_n), g,
                               n_bodies_a=M5A_BODIES, R=wl["m5b_batches"])
            out["seconds"]["M5"] = time.time() - t
    except IntegrityError as e:
        print(f"INTEGRITY FAILURE {name}: {e}", file=sys.stderr)
        sys.exit(3)
    except RuntimeError as e:
        if "tied-weight split check failed" in str(e):
            print(f"INTEGRITY FAILURE {name}: {e}", file=sys.stderr)
            sys.exit(3)
        raise
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, f"{name}.json"), "w") as f:
        json.dump(jsonable(out), f)
    print(f"{name} done in {sum(out['seconds'].values()):.0f}s {out['seconds']}")


if __name__ == "__main__":
    main()
