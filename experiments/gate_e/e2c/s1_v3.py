#!/usr/bin/env python3
"""
V3: timing and the stage-3 forecast (E2C_PREREG_DRAFT 6, 8.2, 8.4). Run after
gate 4 (it uses the calibrated lambda and lambda2). A forecast only: it does
not start, authorize or plan stage 3.

    measured here   C0, C1 (lambda), C2 (lambda2) on the non-formal seed 99,
                    both arms, 1000 updates each, four at a time (the stage-3
                    parallelism): seconds per update and the ratios C1 / C0,
                    C2 / C0
    measured before R2 (C0, 3000 updates, seeds 1-5), the C1 calibration runs
                    (3000 updates), R3 (D2c on 14 checkpoints per run, from the
                    seconds every D2c result records), V5 (transfer rates)
    forecast        training per 12000-update run = max(4 x the 3000-update time,
                    E1's measured 12000-update time) for C0, times the measured
                    ratio for C1 / C2; D2c per run = the R3 sum per run; process
                    time / 4 workers; archive from the V5 rates. Compared with the
                    42 h cap; the fixed trimming order of 8.4 is listed, not applied.
"""

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import e2c_common as C  # noqa: E402
from s1_budget import STAGE1, Ledger, run_pool  # noqa: E402

OUT = os.path.join(STAGE1, "v3")
PY = sys.executable
ARMS = ("openmythos", "transformer")
N_UPD = 1000


def main():
    os.makedirs(OUT, exist_ok=True)
    sel = json.load(open(os.path.join(STAGE1, "gate4", "lambda_selected.json")))
    jobs = []
    for arm in ARMS:
        for cond in C.CONDS:
            argv = [PY, os.path.join(HERE, "train_e2c.py"), "--cond", cond, "--arm", arm, "--seed", str(C.IMPL_SEED),
                    "--steps", str(N_UPD), "--save-at", str(N_UPD), "--ckpt-dir", f"{OUT}/ckpt", "--out", f"{OUT}/{cond}_{arm}.json"]
            if cond != "C0":
                argv += ["--lam", str(sel["lambda"][arm] if cond == "C1" else sel["lambda2"][arm])]
            jobs.append((f"v3_{cond}_{arm}", argv))
    led = Ledger()
    with led.job("v3") as job:
        st, info = run_pool(jobs, job, width=4, log_dir=os.path.join(OUT, "logs"))
    if st != "ok":
        json.dump({"pool": [st, info], "pass": False}, open(os.path.join(OUT, "v3.json"), "w"), indent=1)
        sys.exit(7 if st == "cap" else 3)
    meas = {arm: {c: json.load(open(f"{OUT}/{c}_{arm}.json"))["wall_seconds"] / N_UPD for c in C.CONDS} for arm in ARMS}
    g2 = json.load(open(os.path.join(STAGE1, "gate2", "gate2.json")))
    r2 = {arm: statistics.mean(v["wall_seconds"] for k, v in g2["R2"].items() if k.startswith(arm)) for arm in ARMS}
    e1 = {arm: statistics.mean(json.load(open(os.path.join(GE, "runs", f"K2_{arm}_s{s}.json")))["wall_seconds"] for s in range(1, 6))
          for arm in ARMS}
    cal = {arm: statistics.mean(json.load(open(os.path.join(STAGE1, "gate4", "runs", f)))["wall_seconds"]
                                for f in os.listdir(os.path.join(STAGE1, "gate4", "runs")) if f.startswith(f"C1_{arm}_"))
           for arm in ARMS}
    d2c = {}
    for arm in ARMS:
        per_run = []
        for s in range(1, 6):
            per_run.append(sum(sum(v["seconds"].values()) for k, v in g2["R3"].items() if k.startswith(f"{arm}_s{s}_")))
        d2c[arm] = statistics.mean(per_run)
    v5 = json.load(open(os.path.join(STAGE1, "v5", "v5.json"))) if os.path.exists(os.path.join(STAGE1, "v5", "v5.json")) else {}
    t12 = {}
    for arm in ARMS:
        c0 = max(4 * r2[arm], e1[arm])
        t12[arm] = {"C0": c0, "C1": max(c0 * meas[arm]["C1"] / meas[arm]["C0"], 4 * cal[arm]),
                    "C2": c0 * meas[arm]["C2"] / meas[arm]["C0"]}
    plan = {"openmythos": {"C0": 24, "C1": 24 + 5, "C2": 24 + 5}, "transformer": {"C0": 10, "C1": 10 + 5, "C2": 10 + 5}}
    train_proc = sum(plan[a][c] * t12[a][c] for a in ARMS for c in C.CONDS)
    diag_runs = {"openmythos": 24 * 3 + 10, "transformer": 10 * 3 + 10}
    diag_proc = sum(diag_runs[a] * d2c[a] for a in ARMS)
    size = (v5.get("projection") or {}).get("stage3_bytes", 2.45e6 * 13 * 122)
    rate = min((v5.get("measured_MB_per_s") or {"push": 5.0, "retrieve": 5.0}).values()) * 1e6
    archive_wall = 2 * size / rate  # push and fresh retrieval of every archived file
    wall = (train_proc + diag_proc) / 4 + archive_wall
    res = {"measured_seconds_per_update_seed99": meas, "R2_C0_3000_updates_seconds": r2, "E1_12000_updates_seconds": e1,
           "calibration_C1_3000_updates_seconds": cal, "D2c_seconds_per_run_R3": d2c,
           "forecast_seconds_per_12000_update_run": t12, "planned_trainings": plan, "planned_D2c_runs": diag_runs,
           "forecast": {"training_process_hours": train_proc / 3600, "D2c_process_hours": diag_proc / 3600,
                        "archive_wall_hours": archive_wall / 3600, "stage3_wall_hours_4_workers": wall / 3600, "cap_hours": 42,
                        "within_cap": wall / 3600 <= 42},
           "trimming_order_if_over_cap (8.4, not applied)": ["drop the historical cohort's C2",
                                                              "MLP and M3 only at 0, 150, 12000", "Transformer confirmatory 8 seeds"],
           "note": "forecast only; stage 3 is not authorized"}
    res["pass"] = True
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "v3.json"), "w"), indent=1)
    print(json.dumps(res["forecast"], indent=1))
    sys.exit(0)


if __name__ == "__main__":
    main()
