#!/usr/bin/env python3
"""
Strict check of the training outputs before any evaluation (run_budget.sh).

For every expected (arm, seed) the run directory must hold exactly
    A_<arm>_s<seed>.json, A_<arm>_s<seed>.pt, A_<arm>_s<seed>_step<N>.pt
and nothing else (no *_ABORTED.json, no other files). Every file must be
newer than the launch marker written by run_budget.sh, so results left
over from an earlier launch cannot be mistaken for this one. Each result
JSON must name the right level, arm, seed, step count and schedule, log the
last probe at the final step, and carry a passed step-3000 comparability
record against the expected reference checkpoint; each checkpoint must name
the right arm, seed (and step). With --gate-a-sha the first training batch
must match the Gate A level-A record. Exits 1 listing every problem.
"""

import argparse
import json
import os
import sys

import torch

ARMS = ("openmythos", "transformer")
# first-batch hashes of the Gate A level-A runs (LEVEL_A_REPORT.md)
GATE_A_SHA = {1: "2024179ed9a9", 2: "24a856fcfa6a", 3: "7b6ee871415d"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--marker", required=True)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--steps", type=int, default=12000)
    ap.add_argument("--save-at", default="3000,6000,9000")
    ap.add_argument("--compare-at", type=int, default=3000)
    ap.add_argument("--ref-dir", required=True)
    ap.add_argument("--gate-a-sha", action="store_true")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    save_at = [int(s) for s in args.save_at.split(",")]
    t_launch = os.path.getmtime(args.marker)
    marker_name = os.path.basename(args.marker)
    bad = []

    expected = set()
    for a in ARMS:
        for s in seeds:
            stem = f"A_{a}_s{s}"
            expected |= {f"{stem}.json", f"{stem}.pt"}
            expected |= {f"{stem}_step{n}.pt" for n in save_at}
    present = {f for f in os.listdir(args.dir) if f != marker_name}
    for f in sorted(present - expected):
        bad.append(f"unexpected file in run directory: {f}")
    for f in sorted(expected - present):
        bad.append(f"missing: {f}")
    for f in sorted(present & expected):
        if os.path.getmtime(os.path.join(args.dir, f)) < t_launch:
            bad.append(f"older than this launch (stale): {f}")

    for a in ARMS:
        for s in seeds:
            stem = os.path.join(args.dir, f"A_{a}_s{s}")
            tag = f"A_{a}_s{s}"
            if os.path.exists(stem + ".json"):
                r = json.load(open(stem + ".json"))
                want = {
                    "level": "A",
                    "arm": a,
                    "seed": s,
                    "steps": args.steps,
                    "schedule": "extended",
                }
                for k, v in want.items():
                    if r.get(k) != v:
                        bad.append(f"{tag}.json: {k}={r.get(k)!r}, expected {v!r}")
                last = r.get("log", [{}])[-1].get("step") if r.get("log") else None
                if last != args.steps:
                    bad.append(f"{tag}.json: last logged step {last}, expected {args.steps}")
                c = r.get("comparability") or {}
                ref = os.path.join(args.ref_dir, f"A_{a}_s{s}.pt")
                if c.get("passed") is not True:
                    bad.append(f"{tag}.json: comparability not passed: {c}")
                if os.path.normpath(c.get("reference", "")) != os.path.normpath(ref):
                    bad.append(f"{tag}.json: comparability reference {c.get('reference')!r}, expected {ref!r}")
                if args.gate_a_sha and not str(r.get("first_batch_sha256", "")).startswith(GATE_A_SHA[s]):
                    bad.append(f"{tag}.json: first batch {r.get('first_batch_sha256')!r} != Gate A {GATE_A_SHA[s]}")
            ckpts = [(stem + ".pt", None)] + [(f"{stem}_step{n}.pt", n) for n in save_at]
            for path, n in ckpts:
                if not os.path.exists(path):
                    continue
                ck = torch.load(path, map_location="cpu", weights_only=False)
                name = os.path.basename(path)
                if (ck.get("level"), ck.get("arm"), ck.get("seed")) != ("A", a, s):
                    bad.append(f"{name}: names {ck.get('level')}/{ck.get('arm')}/s{ck.get('seed')}")
                if n is not None and ck.get("step") != n:
                    bad.append(f"{name}: step {ck.get('step')}, expected {n}")

    for b in bad:
        print("FAIL", b)
    print(f"verify_runs: {len(bad)} problem(s), {len(expected)} expected files")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
