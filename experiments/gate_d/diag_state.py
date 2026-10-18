#!/usr/bin/env python3
"""
Run D1-D5 on one model state with the frozen workload (timing.json) and write
results/<state>.json. Single-threaded. Exits 3 on any hard integrity failure
(D4 identity / full-state controls, D5 tied-weight split, parameter hash
differing from the D0 rev3 validation); nothing is written for that state.

    python experiments/gate_d/diag_state.py --arm openmythos --seed 1 --step 12000
"""

import argparse
import json
import os
import sys
import time

import torch

from common import HERE, family_tensors, load_diag, load_state, param_hash, state_name
from d1 import run_d1
from d2 import run_d2
from d3 import run_d3
from d4 import IntegrityError, run_d4
from d5 import run_d5
from runner import Runner


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, torch.Tensor):
        return o.tolist()
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, float) and o != o:
        return None
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "results"))
    ap.add_argument("--workload", default=os.path.join(HERE, "timing.json"))
    args = ap.parse_args()
    torch.set_num_threads(1)
    wl = json.load(open(args.workload))["frozen_workload"]
    name = state_name(args.arm, args.seed, args.step)
    model = load_state(args.arm, args.seed, args.step)
    h = param_hash(model)
    ref = json.load(open(os.path.join(HERE, "validation", "d0_rev3.json")))["states"][name]["param_sha256"]
    if h != ref:
        print(f"parameter hash of {name} differs from the D0 rev3 validation", file=sys.stderr)
        sys.exit(3)
    ev_rows, fit_rows = load_diag("diag_eval"), load_diag("diag_fit")
    ev, fit = family_tensors(ev_rows), family_tensors(fit_rows)
    runner = Runner(model)
    out = {"state": name, "param_sha256": h, "workload": wl, "seconds": {}}
    try:
        t = time.time()
        out["D1"], _ = run_d1(runner, ev, fit)
        out["seconds"]["D1"] = time.time() - t
        t = time.time()
        out["D2"] = run_d2(runner, fit, fit_rows, ev, ev_rows)
        out["seconds"]["D2"] = time.time() - t
        t = time.time()
        out["D3"] = run_d3(runner, ev, n_perm=wl["d3_permutations"])
        out["seconds"]["D3"] = time.time() - t
        t = time.time()
        out["D4"] = run_d4(runner, ev)
        out["seconds"]["D4"] = time.time() - t
        if args.step in wl["d5_steps"]:
            t = time.time()
            out["D5"] = run_d5(model, ev_rows, fit_rows, load_diag("pool_b"), load_diag("pool_c"),
                               n_bodies_a=wl["d5a_bodies"], R=wl["d5b_batches"])
            out["seconds"]["D5"] = time.time() - t
        else:
            out["D5"] = {"skipped": "workload level excludes this checkpoint from D5"}
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
