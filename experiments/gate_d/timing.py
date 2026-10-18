#!/usr/bin/env python3
"""
Performance test and frozen workload (PREREGISTRATION 8.10).

Non-formal models only (seed 99: random initialization and the 60-step
budget_a smoke checkpoint, both arms); non-diagnostic data drawn from
Random(50000) with the formal shapes (500 + 500 bodies, pool_b-like batches,
1000 pool_c bodies). Each D1-D5 component is timed single-threaded at full
scale; the four timing jobs run in parallel, as the formal run does, so CPU
contention is included. The slower of the two timing models per arm is used.
The OpenMythos D5 time is scaled by (2 + 4) / (2 + L), L = mean number of
loops the timing model's original forward executes (formal models may run
all 4). Estimate: simulated makespan of the launcher's queue on 4 workers,
x 1.2 margin. Peak memory of the timing jobs is taken from timing_rss.log.
Ladder (applied in this order until the estimate is <= 4 h):
    1 D5(a) bodies 500 -> 250     2 D5(b) R 200 -> 100
    3 D5 only at steps 0, 3000, 12000     4 D3 permutations 1000 -> 500
Writes timing.json with the measurements and the frozen workload, before any
formal diagnostic is run. Exits 4 if level 4 still exceeds 4 h.
"""

import json
import os
import random
import sys
import time

import torch

from common import EXP, HERE, STEPS, family_tensors, load_state
from d1 import run_d1
from d2 import run_d2
from d3 import run_d3
from d4 import run_d4
from d5 import run_d5
from runner import Runner

sys.path.insert(0, os.path.join(EXP, "gen_gate_a"))
from levels import make_sample  # noqa: E402

LIMIT_H = 4.0


def fam(body):
    return {"body": body, "queries": [body[4 * k] for k in range(4)],
            "answers": [body[4 * k + 2] for k in range(4)]}


def timing_data():
    rng = random.Random(50_000)
    draw = lambda: fam(make_sample("A", rng, "test")[0].split("|")[0])  # noqa: E731
    fit = [dict(draw(), id=i) for i in range(500)]
    ev = [dict(draw(), id=i) for i in range(500)]
    pb = []
    for scheme, nb, nq in (("O", 64, 1), ("P", 32, 2), ("F", 16, 4)):
        for b in range(200):
            for _ in range(nb):
                f = draw()
                slots = [rng.randrange(4)] if nq == 1 else sorted(rng.sample(range(4), nq))
                pb.append(dict(f, scheme=scheme, batch=b, slots=slots))
    pc = [dict(draw(), id=i) for i in range(1000)]
    return fit, ev, pb, pc


def loops_executed(model, x):
    rec = Runner(model).run(x, record=True)[1]
    return float(sum(rec[f"valid{t}"].float().mean() for t in range(4)))


def time_model(model, fit, ev, pb, pc):
    runner = Runner(model)
    fitT, evT = family_tensors(fit), family_tensors(ev)
    t = {}
    s = time.time(); run_d1(runner, evT, fitT); t["D1"] = time.time() - s
    s = time.time(); run_d2(runner, fitT, fit, evT, ev); t["D2"] = time.time() - s
    s = time.time(); run_d3(runner, evT, n_perm=1000); t["D3_1000"] = time.time() - s
    s = time.time(); run_d3(runner, evT, n_perm=500); t["D3_500"] = time.time() - s
    s = time.time(); run_d4(runner, evT); t["D4"] = time.time() - s
    # D5 at full size once; its parts (c, a, b) are timed inside run_d5 and the
    # reduced levels are derived linearly (a with 250 bodies = a / 2, b with R 100 = b / 2)
    s = time.time()
    p = run_d5(model, ev, fit, pb, pc, n_bodies_a=500, R=200, n_boot=2000)["seconds"]
    t["D5_full"] = time.time() - s
    t["D5_parts"] = p
    t["D5_a250"] = t["D5_full"] - p["a"] / 2
    t["D5_a250_R100"] = t["D5_full"] - p["a"] / 2 - p["b"] / 2
    return t


def estimate(per_arm, level):
    """Simulated makespan of the launcher's own queue (run_gate_d.sh order:
    arm, seed, steps 12000..0; 4 workers, each takes the next state when it
    becomes free), x 1.2 margin. Per-state times come from the four timing
    jobs, which already ran in parallel like the formal run."""
    d5_steps = STEPS if level < 3 else (0, 3000, 12000)
    queue = []
    for arm in ("openmythos", "transformer"):
        t = per_arm[arm]
        d3 = t["D3_500"] if level >= 4 else t["D3_1000"]
        d5 = t["D5_full"] if level == 0 else t["D5_a250"] if level == 1 else t["D5_a250_R100"]
        for _seed in (1, 2, 3):
            for step in (12000, 9000, 6000, 3000, 0):
                queue.append(t["D1"] + t["D2"] + d3 + t["D4"] + (d5 if step in d5_steps else 0.0))
    free = [0.0] * 4
    for job in queue:
        i = free.index(min(free))
        free[i] += job
    return max(free) * 1.2 / 3600


PARTS = os.path.join(HERE, "timing_parts")
LABELS = ("seed99_init", "seed99_smoke60")


def job(arm, label):
    """One timing model; the four jobs run in parallel (as the formal run does)."""
    torch.set_num_threads(1)
    fit, ev, pb, pc = timing_data()
    x = family_tensors(ev)[0]
    if label == "seed99_init":
        m = load_state(arm, 99, 0)
    else:
        m = load_state(arm, 99, 60, path=os.path.join(EXP, "budget_a", "smoke", f"run1_{arm}.pt"))
    L = loops_executed(m, x) if arm == "openmythos" else None
    t = time_model(m, fit, ev, pb, pc)
    if arm == "openmythos":
        f = 6.0 / (2.0 + L)
        for k in ("D5_full", "D5_a250", "D5_a250_R100"):
            t[k + "_unscaled"] = t[k]
            t[k] = t[k] * f
        t["loops_executed"] = L
        t["d5_scale_factor"] = f
    os.makedirs(PARTS, exist_ok=True)
    with open(os.path.join(PARTS, f"{arm}_{label}.json"), "w") as fh:
        json.dump(t, fh, indent=1)


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--job":
        return job(sys.argv[2], sys.argv[3])
    rep = {"models": {}, "per_arm_seconds": {}}
    for arm in ("openmythos", "transformer"):
        cand = {lb: json.load(open(os.path.join(PARTS, f"{arm}_{lb}.json"))) for lb in LABELS}
        rep["models"][arm] = cand
        keys = ("D1", "D2", "D3_1000", "D3_500", "D4", "D5_full", "D5_a250", "D5_a250_R100")
        rep["per_arm_seconds"][arm] = {k: max(c[k] for c in cand.values()) for k in keys}
    est = {lvl: estimate(rep["per_arm_seconds"], lvl) for lvl in range(5)}
    rss_path = os.path.join(HERE, "timing_rss.log")
    rss = [l.split() for l in open(rss_path)] if os.path.exists(rss_path) else []
    rep["memory_mb"] = {"peak_total_4_jobs": max((float(r[1]) for r in rss), default=None),
                        "peak_single_job": max((float(r[2]) for r in rss), default=None),
                        "machine_total": 15 * 1024}
    rep["estimated_hours_by_level"] = est
    level = next((lvl for lvl in range(5) if est[lvl] <= LIMIT_H), None)
    rep["chosen_level"] = level
    if level is not None:
        rep["frozen_workload"] = {
            "level": level,
            "d5a_bodies": 500 if level == 0 else 250,
            "d5b_batches": 200 if level <= 1 else 100,
            "d5_steps": list(STEPS) if level < 3 else [0, 3000, 12000],
            "d3_permutations": 1000 if level < 4 else 500,
        }
    with open(os.path.join(HERE, "timing.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps({k: rep[k] for k in ("estimated_hours_by_level", "chosen_level")}, indent=1))
    sys.exit(0 if level is not None else 4)


if __name__ == "__main__":
    main()
