#!/usr/bin/env python3
"""
Stage-1 summary: collects the gate records into stage1/summary.json and writes
stage1/file_hashes.json, the sha256 of every E2-c code file and every stage-1
record committed to the research branch (no checkpoint, no LFS retrieval
directory, no temporary file). Reads only; runs no job.
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE1 = os.path.join(HERE, "stage1")


def load(rel):
    p = os.path.join(STAGE1, rel)
    return json.load(open(p)) if os.path.exists(p) else None


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    s = {}
    pc = load("precheck.json")
    s["precheck"] = {"pass": pc and pc["pass"], "lfs_verified": pc and pc["lfs"]["verified"]}
    g1 = load("gate1/gate1.json")
    s["gate1"] = g1 and {a: {"R1": g1[a]["R1"]["pass"], "R1'": g1[a]["R1_prime"]["pass"],
                             "R1''": {k: v["pass"] for k, v in g1[a]["R1_double_prime"].items()}} for a in ("openmythos", "transformer")}
    g2 = load("gate2/gate2.json")
    s["gate2"] = g2 and {k: g2.get(k) for k in ("R2_pass", "R3_pass", "R3_values_compared", "R3_max_abs_diff", "pass", "pool",
                                                 "skipped_complete_jobs")}
    if g2:
        s["gate2"]["R2_checkpoints_compared"] = sum(len(v["checkpoints"]) for v in g2["R2"].values())
        s["gate2"]["R3_states"] = len(g2["R3"])
        s["gate2"]["skipped_complete_jobs"] = len(g2.get("skipped_complete_jobs") or [])
    g3 = load("gate3/gate3.json")
    s["gate3"] = g3 and {"pass": g3["pass"], **{a: g3[a]["pass"] for a in ("openmythos", "transformer") if a in g3}}
    g4 = load("gate4/calibration.json")
    s["gate4"] = g4 and {"selection": g4.get("selection_summary"), "stopped": g4.get("stopped"), "pass": g4.get("pass")}
    g5 = load("gate5.json")
    s["gate5"] = g5
    led = json.load(open(os.path.join(STAGE1, "budget_ledger_s1.json")))
    s["budget"] = {"total_hours": led["total_seconds"] / 3600, "cap_hours": led["cap_seconds"] / 3600,
                   "intervals": len(led["intervals"]), "closed_after_interruption": led["closed_after_interruption"],
                   "corrections": led.get("corrections")}
    json.dump(s, open(os.path.join(STAGE1, "summary.json"), "w"), indent=1, ensure_ascii=False)
    files = {}
    for f in sorted(os.listdir(HERE)):
        if f.endswith((".py", ".md")):
            files[f] = sha(os.path.join(HERE, f))
    for root, dirs, fs in os.walk(STAGE1):
        dirs[:] = [d for d in dirs if d not in ("lfs_e1", "fresh", "ckpt", "r2ckpt") and not d.startswith(".")]
        for f in fs:
            if f.endswith(".pt") or ".tmp." in f or f.endswith(".lock") or f == "file_hashes.json":
                continue
            p = os.path.join(root, f)
            files[os.path.relpath(p, HERE)] = sha(p)
    json.dump(files, open(os.path.join(STAGE1, "file_hashes.json"), "w"), indent=1)
    print(json.dumps(s, indent=1, ensure_ascii=False)[:4000])
    print(f"{len(files)} files hashed")
    sys.exit(0)


if __name__ == "__main__":
    main()
