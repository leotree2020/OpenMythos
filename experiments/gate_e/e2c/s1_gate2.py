#!/usr/bin/env python3
"""
Stage 1, gate 2: R2 and R3 (E2C_PREREG_DRAFT 6). Run only after gate 1 passed.

    R2  E1 seeds 1-5, both arms: train_e2c.py C0 (records on, the stage-3
        configuration) for 3000 updates with checkpoints at E1's grid
        25, 50, ..., 3000 (14 steps). Every checkpoint, and step 0, must be
        bitwise equal to E1's archived checkpoint of the same state as
        retrieved from LFS by s1_precheck.py (file sha256 and parameter hash
        checked there against checkpoints_manifest.json): state-dict tensors
        equal and parameter hash equal to the manifest's. The task loss of
        every update, the light log, the dev log and the first-batch hash are
        compared with E1's run record (runs/K2_<arm>_s<seed>.json, first 3000
        updates) as further evidence.
    R3  D2c (d2c.py) on the same LFS-retrieved E1 checkpoints of seeds 1-5,
        both arms, at the 14 D2c checkpoints, with E1's measurement sets;
        every value equal to E1's archived result of that state within 1e-6
        (s1_compare.py).
The first failure stops the pool (nothing new starts, running jobs are
killed): F2, the intervention gates are not entered. Exit 0 if both pass;
3 on a failure; 7 when the stage-1 cap is reached.
Resumption (added after the first launch was killed by the session's
background time limit at 10:53 UTC): a job whose final output exists is not
re-run, but its comparison is recomputed from the files; files of a training
run without its final record, and temporary files, are moved to
gate2/quarantine/<time>/ first, and a re-trained run must equal the kept
files on the overlap (checkpoints bitwise).
"""

import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402
from e_common import K2_SEEDS, param_hash  # noqa: E402
from models import build  # noqa: E402
from s1_budget import STAGE1, Ledger, run_pool  # noqa: E402
from s1_compare import compare_state  # noqa: E402

OUT = os.path.join(STAGE1, "gate2")
LFS = os.path.join(STAGE1, "lfs_e1", "gate_e", "formal")
R2_SAVE = (25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000)
ARMS = ("openmythos", "transformer")
PY = sys.executable
MAN = json.load(open(os.path.join(GE, "checkpoints_manifest.json")))["states"]


def e1_ckpt(arm, seed, step):
    return os.path.join(LFS, f"K2_{arm}_s{seed}_step{step}.pt")


def jobs():
    r2 = [(f"r2_{arm}_s{s}", [PY, os.path.join(HERE, "train_e2c.py"), "--cond", "C0", "--arm", arm, "--seed", str(s),
                              "--steps", "3000", "--save-at", ",".join(map(str, R2_SAVE)),
                              "--ckpt-dir", f"{OUT}/r2ckpt", "--out", f"{OUT}/r2/C0_{arm}_s{s}.json"])
          for arm in ARMS for s in K2_SEEDS]

    def r3(arm, s, t):
        return (f"r3_{arm}_s{s}_step{t}", [PY, os.path.join(HERE, "d2c.py"), "--arm", arm, "--seed", str(s), "--step", str(t),
                                           "--ckpt", e1_ckpt(arm, s, t), "--out", f"{OUT}/r3/K2_{arm}_s{s}_step{t}.json"])
    heavy_om = [r3("openmythos", s, t) for s in K2_SEEDS for t in C.D2C_STEPS if t in C.D2C_HEAVY]
    light_om = [r3("openmythos", s, t) for s in K2_SEEDS for t in C.D2C_STEPS if t not in C.D2C_HEAVY]
    tf = [r3("transformer", s, t) for s in K2_SEEDS for t in C.D2C_STEPS]
    # longest first: OpenMythos trainings, heavy OpenMythos states, then the rest
    return r2[:5] + heavy_om + r2[5:] + light_om + tf


def check_r2(arm, seed):
    rec = json.load(open(f"{OUT}/r2/C0_{arm}_s{seed}.json"))
    e1 = json.load(open(os.path.join(GE, "runs", f"K2_{arm}_s{seed}.json")))
    per = {}
    for t in (0,) + R2_SAVE:
        a = torch.load(f"{OUT}/r2ckpt/C0_{arm}_s{seed}_step{t}.pt", map_location="cpu", weights_only=False)["model"]
        b = torch.load(e1_ckpt(arm, seed, t), map_location="cpu", weights_only=False)["model"]
        m = build(arm, 2)
        m.load_state_dict(a)
        per[str(t)] = {"state_dict_bitwise_equal": C.state_dict_equal(a, b),
                       "param_sha256_equals_manifest": param_hash(m) == MAN[f"K2_{arm}_s{seed}_step{t}"]["param_sha256"]}
    logs = {"loss_every_step": rec["loss_every_step"] == e1["loss_every_step"][:3000],
            "light_log": rec["light_log"] == [x for x in e1["light_log"] if x["step"] <= 3000],
            "dev_log": rec["dev_log"] == [x for x in e1["dev_log"] if x["step"] <= 3000],
            "first_batch_sha256": rec["first_batch_sha256"] == e1["first_batch_sha256"]}
    ok = all(v["state_dict_bitwise_equal"] and v["param_sha256_equals_manifest"] for v in per.values()) and all(logs.values())
    return {"checkpoints": per, "logs_equal_first_3000": logs, "wall_seconds": rec["wall_seconds"], "pass": ok}


def final_output(name, argv):
    return argv[argv.index("--out") + 1]


def main():
    import glob
    import shutil
    import time
    led = Ledger()
    for d in ("r2", "r3", "r2ckpt", "logs"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    res = {"R2": {}, "R3": {}, "launches": []}
    prev = os.path.join(OUT, "launches.json")
    launches = json.load(open(prev)) if os.path.exists(prev) else []
    launches.append({"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    json.dump(launches, open(prev, "w"), indent=1)
    res["launches"] = launches
    qdir = os.path.join(OUT, "quarantine", time.strftime("%Y%m%dT%H%M%S", time.gmtime()))
    kept = {}
    for f in glob.glob(os.path.join(OUT, "r3", ".*.tmp.*")) + glob.glob(os.path.join(OUT, "r2", ".*.tmp.*")):
        os.makedirs(qdir, exist_ok=True)
        shutil.move(f, os.path.join(qdir, os.path.basename(f)))
    for arm in ARMS:
        for s in K2_SEEDS:
            if not os.path.exists(f"{OUT}/r2/C0_{arm}_s{s}.json"):
                for f in glob.glob(f"{OUT}/r2ckpt/C0_{arm}_s{s}_step*.pt") + glob.glob(f"{OUT}/r2/C0_{arm}_s{s}.json.progress.json"):
                    os.makedirs(qdir, exist_ok=True)
                    kept[os.path.basename(f)] = shutil.move(f, os.path.join(qdir, os.path.basename(f)))
    res["quarantined_partial_attempt_files"] = sorted(kept)

    def on_done(name):
        parts = name.split("_")
        if parts[0] == "r2":
            arm, seed = parts[1], int(parts[2][1:])
            r = check_r2(arm, seed)
            r["equal_to_kept_attempt"] = {b: C.state_dict_equal(
                torch.load(p, map_location="cpu", weights_only=False)["model"],
                torch.load(f"{OUT}/r2ckpt/{b}", map_location="cpu", weights_only=False)["model"])
                for b, p in kept.items() if b.startswith(f"C0_{arm}_s{seed}_") and b.endswith(".pt")}
            r["pass"] = r["pass"] and all(r["equal_to_kept_attempt"].values())
            res["R2"][f"{arm}_s{seed}"] = r
            return None if r["pass"] else f"R2 {arm} s{seed} differs"
        arm, seed, step = parts[1], int(parts[2][1:]), int(parts[3][4:])
        d = json.load(open(f"{OUT}/r3/K2_{arm}_s{seed}_step{step}.json"))
        e1 = json.load(open(os.path.join(GE, "results", f"K2_{arm}_s{seed}_step{step}.json")))
        r = compare_state(d, e1)
        r["seconds"] = d["seconds"]
        res["R3"][f"{arm}_s{seed}_step{step}"] = r
        return None if r["pass"] else f"R3 {arm} s{seed} step{step} differs"

    all_jobs = jobs()
    todo = [j for j in all_jobs if not os.path.exists(final_output(*j))]
    res["skipped_complete_jobs"] = [j[0] for j in all_jobs if j not in todo]
    with led.job("gate2" if len(launches) == 1 else f"gate2_resume{len(launches) - 1}") as job:
        status, info = "ok", None
        for name in res["skipped_complete_jobs"]:  # outputs from an earlier launch: comparisons recomputed
            why = on_done(name)
            if why:
                status, info = "failed", (name, why)
                break
        if status == "ok":
            status, info = run_pool(todo, job, width=4, log_dir=os.path.join(OUT, "logs"), on_done=on_done)
    res["pool"] = [status, info]
    res["R2_pass"] = len(res["R2"]) == 10 and all(v["pass"] for v in res["R2"].values())
    res["R3_pass"] = len(res["R3"]) == 140 and all(v["pass"] for v in res["R3"].values())
    res["R3_values_compared"] = sum(v["n_values"] for v in res["R3"].values())
    res["R3_max_abs_diff"] = max([v["max_abs_diff"] for v in res["R3"].values()] or [None])
    res["pass"] = status == "ok" and res["R2_pass"] and res["R3_pass"]
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "gate2.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: res[k] for k in ("pool", "R2_pass", "R3_pass", "R3_values_compared", "R3_max_abs_diff", "pass")}, indent=1))
    print("GATE 2", "PASS" if res["pass"] else "FAIL (F2)", f"ledger {led.total():.0f} s")
    sys.exit(0 if res["pass"] else (7 if status == "cap" else 3))


if __name__ == "__main__":
    main()
