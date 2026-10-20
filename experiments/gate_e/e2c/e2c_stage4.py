#!/usr/bin/env python3
"""
Stage-4 jobs of the E2-c launcher (E2C_PREREG_DRAFT 7.4 steps 7-10, 5.1).
Implemented in stage 1, never run there on real data (V4 uses stubs); they
run only under the stage-4 authorization, started by run_e2c.py after the
salt check passed.

    keyspace  R*, M1* recomputed with E1's sets; counts and hashes -> JSON
    test2     generate test2 from the salt (7.4 step 8), serialize it, run
              the isolation checks (step 9) -> test2_heldout.jsonl + JSON
    judge     one run at step 12000 on test2, written once (5.1)
"""

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_test2 as T  # noqa: E402
from e_common import atomic_write_json, jsonable, load_state  # noqa: E402

SETS = os.path.join(GE, "sets")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job", choices=["keyspace", "test2", "judge"])
    ap.add_argument("--salt-file")
    ap.add_argument("--seeds", help="training-stream seeds for the isolation check (comma-separated)")
    ap.add_argument("--arm")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--cond")
    ap.add_argument("--ckpt")
    ap.add_argument("--test2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.job == "keyspace":
        ks = T.keyspace(SETS)
        out = dict(T.pool_hashes(ks["R"], ks["M1"]))
        out["counts"].update({"H": len(ks["H"]), "U": len(ks["U"])})
        atomic_write_json(a.out, out, indent=1)
    elif a.job == "test2":
        salt = open(a.salt_file).read().strip()
        ks = T.keyspace(SETS)
        rows, stats = T.generate(salt, ks["R"], ks["M1"])
        text = T.serialize_test2(rows)
        path = os.path.join(os.path.dirname(a.out), "test2_heldout.jsonl")
        if os.path.exists(path):
            print("REFUSED: test2_heldout.jsonl exists; it is written once", file=sys.stderr)
            sys.exit(3)
        with open(path, "w") as f:
            f.write(text)
        seeds = [int(s) for s in a.seeds.split(",")]
        iso = T.isolation(rows, ks["R"], T.e1_set_keys(SETS), T.training_stream_keys(seeds))
        atomic_write_json(a.out, {"sha256": hashlib.sha256(text.encode()).hexdigest(), "stats": stats,
                                  "isolation": iso, "training_stream_seeds": seeds,
                                  "pools": T.pool_hashes(ks["R"], ks["M1"])}, indent=1)
    else:
        if os.path.exists(a.out):
            print(f"REFUSED: {a.out} exists; a judgment is written once, never redone", file=sys.stderr)
            sys.exit(3)
        import torch
        torch.set_num_threads(1)
        model = load_state(a.arm, 2, a.seed, 12000, path=a.ckpt)
        rows = [json.loads(line) for line in open(a.test2)]
        res = {"cond": a.cond, "arm": a.arm, "seed": a.seed, "step": 12000, "set": "test2_heldout",
               "test2_sha256": hashlib.sha256(open(a.test2, "rb").read()).hexdigest(), "main": T.evaluate(model, rows)}
        if a.arm == "openmythos":
            res["reference_loops"] = {str(t): T.evaluate(model, rows, n_loops=t)["accuracy"] for t in (1, 2, 8)}
        atomic_write_json(a.out, jsonable(res), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
