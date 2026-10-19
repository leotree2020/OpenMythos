#!/usr/bin/env python3
"""
Gate E performance test and budget freeze (PREREGISTRATION 6.7, 9.9, 11.3).
Non-formal seed 99 only; the formal held-out test set is not touched (the
formal-judgment script is timed on dev_heldout and scaled by the set size).

    python e_timing.py run --scratch S     everything below, then summarize
    python e_timing.py summarize           timing.json from timing_parts/

1. training: 4 parallel jobs (K=2 train_k.py and K=4 train_level.py with the
   bridge arguments, both arms), 600 steps each with the formal checkpoint /
   probe density of the first 600 steps; seconds per step
2. storage: LFS push of the K=2 OpenMythos timing checkpoints (10 files) to
   leotree2020/openmythos-artifacts (gate_e/timing_test/), retrieval into a
   fresh directory, both hashes checked; throughput
3. diagnostics: e_diag_state.py at level 0 on 8 timing states (K = 2, 4 x both
   arms x {initialization, 500 steps}), 4 in parallel; per component times;
   MLP and linear probe fit times by number of classes (wrapped, the
   diagnostic code is unchanged); OpenMythos forward-dependent times scaled
   by (2 + 4) / (2 + L) with L the mean number of loops executed
4. formal-judgment script on dev_heldout (500 bodies), scaled x 2
5. memory: resident set of the parallel jobs, sampled every 5 s

Estimate: simulated makespan of the launcher queue on 4 workers, x 1.2.
Workload levels (PREREGISTRATION 6.7 / 9.9: only these may be reduced):
    0  full: M5(b) R = 200, MLP everywhere
    1  M5(b) R = 100
    2  level 1 + no MLP on P1 / P3 where the linear probe detects (its saving
       depends on the formal results, so the budget uses the level-1 time
       for it; the best-case saving is reported)
Never reduced: checkpoints, sets, P2 probes, M3 pairs and controls, M5(a)
fixed at 500 bodies (11.3). Diagnostics must fit in 6 h; if level 2 does
not, no workload is frozen and the run stops for review (exit 4).
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import ARMS, BRIDGE_SEEDS, BRIDGE_STEPS, K2_SEEDS, K2_STEPS, ROOT  # noqa: E402

PARTS = os.path.join(HERE, "timing_parts")
LOGS = os.path.join(HERE, "timing_logs")
DIAG_LIMIT_H = 6.0
TRAIN_STEPS = 600
SAVE_600 = "25,50,75,100,150,200,300,400,500"
MARGIN = 1.2
ENV = dict(os.environ, PYTHONPATH=os.path.abspath(ROOT))


def rss_mb(pid):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except OSError:
        return 0.0
    return 0.0


def run_parallel(jobs, log_name, width=4):
    """jobs: list of (name, argv). At most `width` at once; samples the summed
    resident set of the live jobs every 5 s. Returns {name: (rc, seconds)}."""
    os.makedirs(LOGS, exist_ok=True)
    rss_log = open(os.path.join(LOGS, f"{log_name}_rss.log"), "w")
    pending, live, out, peak, peak1 = list(jobs), {}, {}, 0.0, 0.0
    while pending or live:
        while pending and len(live) < width:
            name, argv = pending.pop(0)
            f = open(os.path.join(LOGS, f"{log_name}_{name}.log"), "w")
            live[name] = (subprocess.Popen(argv, cwd=os.path.abspath(ROOT), env=ENV, stdout=f, stderr=f), time.time(), f)
        time.sleep(5)
        sizes = {n: rss_mb(p.pid) for n, (p, _, _) in live.items()}
        tot = sum(sizes.values())
        peak, peak1 = max(peak, tot), max(peak1, max(sizes.values(), default=0.0))
        rss_log.write(f"{time.strftime('%H:%M:%S')} {tot:.0f} {max(sizes.values(), default=0):.0f} {len(live)}\n")
        rss_log.flush()
        for n in list(live):
            p, t0, f = live[n]
            if p.poll() is not None:
                out[n] = (p.returncode, time.time() - t0)
                f.close()
                del live[n]
    rss_log.close()
    return out, {"peak_total_mb": peak, "peak_single_mb": peak1}


def stage_train(S):
    d = os.path.join(S, "timing_train")
    jobs = []
    for arm in ARMS:
        jobs.append((f"K2_{arm}", ["python", "experiments/gate_e/train_k.py", "--task", "k2", "--arm", arm,
                                   "--seed", "99", "--steps", str(TRAIN_STEPS), "--save-at", SAVE_600,
                                   "--ckpt-dir", f"{d}/K2_{arm}", "--out", f"{d}/K2_{arm}.json"]))
        jobs.append((f"K4_{arm}", ["python", "experiments/gen_gate_a/train_level.py", "--level", "A", "--arm", arm,
                                   "--seed", "99", "--steps", str(TRAIN_STEPS), "--schedule", "extended",
                                   "--save-at", SAVE_600, "--probe-every", "25", "--out", f"{d}/A_{arm}.json"]))
    res, mem = run_parallel(jobs, "train")
    out = {"memory": mem, "jobs": {}}
    for name, (rc, sec) in res.items():
        K, arm = name.split("_", 1)
        js = json.load(open(f"{d}/{'K2' if K == 'K2' else 'A'}_{arm}.json")) if rc == 0 else {}
        out["jobs"][name] = {"exit": rc, "process_seconds": sec, "loop_seconds": js.get("wall_seconds"),
                             "seconds_per_step": (js.get("wall_seconds") or sec) / TRAIN_STEPS}
    return out


def stage_storage(S):
    from e_storage import ARTIFACTS_URL, entry, push_files, retrieve_and_verify

    d = os.path.join(S, "timing_train", "K2_openmythos")
    files = [(os.path.join(d, f"K2_openmythos_s99_step{t}.pt"), f"gate_e/timing_test/K2_openmythos_s99_step{t}.pt", t)
             for t in [0] + [int(x) for x in SAVE_600.split(",")]]
    ents = [entry(p, pub, "openmythos", 2, 99, t, "timing", "e_timing.py stage 1") for p, pub, t in files]
    total = sum(e["bytes"] for e in ents)
    t0 = time.time()
    commit = push_files([(p, pub) for p, pub, _ in files], "/home/user/openmythos-artifacts", ARTIFACTS_URL,
                        "gate_e: timing - storage throughput with 10 non-formal checkpoints (seed 99)")
    t_push = time.time() - t0
    t0 = time.time()
    ver = retrieve_and_verify(ents, ARTIFACTS_URL, os.path.join(S, "artifacts_fresh_timing"))
    t_pull = time.time() - t0
    ok = all(v["file_sha256"] and v["param_sha256"] for v in ver.values())
    return {"files": len(ents), "bytes": total, "push_seconds": t_push, "pull_and_verify_seconds": t_pull,
            "push_mb_per_s": total / 1e6 / t_push, "pull_mb_per_s": total / 1e6 / t_pull,
            "pushed_commit": commit, "verified": ok}


def diag_job(arm, K, label, ckpt, outdir):
    """One timing state; the fit functions of e_m2 are wrapped to time them by
    number of classes (P1: K, P3: 10, P2 / P0: 52)."""
    import e_m2
    import e_diag_state

    times = {}

    def wrap(name):
        f = getattr(e_m2, name)

        def g(X, y, C, *a, **k):
            t = time.time()
            r = f(X, y, C, *a, **k)
            key = f"{name}_C{C}"
            times[key] = times.get(key, 0.0) + time.time() - t
            return r
        setattr(e_m2, name, g)

    for n in ("fit_mlp", "fit_linear", "fit_linear_raw"):
        wrap(n)
    wl = os.path.join(outdir, "workload_level0.json")
    step = 0 if label == "init" else TRAIN_STEPS - 100
    argv = ["e_diag_state.py", "--arm", arm, "--K", str(K), "--seed", "99", "--step", str(step),
            "--no-manifest", "--workload", wl, "--out-dir", outdir]
    if ckpt:
        argv += ["--ckpt", ckpt]
    sys.argv = argv
    e_diag_state.main()
    name = f"K{K}_{arm}_s99_step{step}"
    res = json.load(open(os.path.join(outdir, f"{name}.json")))
    loops = None
    if arm == "openmythos":
        loops = float(sum(res["M6"]["valid_by_loop"]))
    part = {"seconds": res["seconds"], "m5_parts": res["M5"]["seconds"], "fit_seconds_by_classes": times,
            "loops_executed": loops}
    os.makedirs(PARTS, exist_ok=True)
    with open(os.path.join(PARTS, f"diag_K{K}_{arm}_{label}.json"), "w") as f:
        json.dump(part, f, indent=1)


def stage_diag(S):
    outdir = os.path.join(S, "timing_diag")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "workload_level0.json"), "w") as f:
        json.dump({"frozen_workload": {"level": 0, "m5b_batches": 200, "mlp_p13_when_linear_detected": True,
                                       "m5a_bodies": 500}}, f)
    d = os.path.join(S, "timing_train")
    step = TRAIN_STEPS - 100
    jobs = []
    for K in (2, 4):
        for arm in ARMS:
            for label in ("init", "trained"):
                if K == 2:
                    ck = f"{d}/K2_{arm}/K2_{arm}_s99_step{0 if label == 'init' else step}.pt"
                else:
                    ck = "" if label == "init" else f"{d}/A_{arm}_step{step}.pt"
                jobs.append((f"K{K}_{arm}_{label}", ["python", "experiments/gate_e/e_timing.py", "--diag-job",
                                                    arm, str(K), label, ck, outdir]))
    jobs.sort(key=lambda j: (0 if "openmythos" in j[0] else 1))  # long jobs first
    res, mem = run_parallel(jobs, "diag")
    return {"memory": mem, "jobs": {n: {"exit": rc, "process_seconds": s} for n, (rc, s) in res.items()}}


def stage_eval(S):
    d = os.path.join(S, "timing_train")
    out = {}
    for arm in ARMS:
        t = time.time()
        rc = subprocess.run(["python", "experiments/gate_e/e_eval_test.py", "--arm", arm, "--seed", "99",
                             "--step", str(TRAIN_STEPS - 100), "--ckpt",
                             f"{d}/K2_{arm}/K2_{arm}_s99_step{TRAIN_STEPS - 100}.pt", "--set", "dev_heldout",
                             "--out", os.path.join(S, "timing_eval", f"{arm}.json")],
                            cwd=os.path.abspath(ROOT), env=ENV, capture_output=True).returncode
        out[arm] = {"exit": rc, "seconds_dev_500_bodies": time.time() - t,
                    "estimated_seconds_test_1000_bodies": 2 * (time.time() - t)}
    return out


# ---------------------------------------------------------------- summarize


def makespan(durations, width=4):
    free = [0.0] * width
    for d in durations:
        i = free.index(min(free))
        free[i] += d
    return max(free)


def per_state_seconds(part, level, arm):
    s = dict(part["seconds"])
    f = 6.0 / (2.0 + part["loops_executed"]) if arm == "openmythos" else 1.0
    fits = sum(part["fit_seconds_by_classes"].values())
    s["M2+M6"] = (s["M2+M6"] - fits) * f + fits  # probe fits do not depend on the loop count
    for k in ("M0", "M1", "M3", "M4"):
        s[k] *= f
    m5 = s["M5"]
    if level >= 1:
        m5 -= part["m5_parts"]["b"] / 2
    s["M5"] = m5 * f
    return sum(s.values())


def summarize():
    T = json.load(open(os.path.join(PARTS, "train.json")))
    st = json.load(open(os.path.join(PARTS, "storage.json")))
    dg = json.load(open(os.path.join(PARTS, "diag_jobs.json")))
    ev = json.load(open(os.path.join(PARTS, "eval.json")))
    parts = {}
    for K in (2, 4):
        for arm in ARMS:
            parts[(K, arm)] = {lb: json.load(open(os.path.join(PARTS, f"diag_K{K}_{arm}_{lb}.json")))
                               for lb in ("init", "trained")}
    rep = {"note": "non-formal seed 99 only; formal test set not used", "training": T, "storage": st,
           "diag_jobs": dg, "eval": ev}
    # training: 10 K=2 runs x 12,000 steps, 6 bridge runs x 3,000 steps, 4 workers, longest first
    sps = {k: v["seconds_per_step"] for k, v in T["jobs"].items()}
    train_jobs = sorted([sps[f"K2_{a}"] * 12000 for a in ARMS for _ in K2_SEEDS]
                        + [sps[f"K4_{a}"] * 3000 for a in ARMS for _ in BRIDGE_SEEDS], reverse=True)
    train_h = makespan(train_jobs) * MARGIN / 3600
    n_files = len(K2_SEEDS) * len(ARMS) * len(K2_STEPS) + len(BRIDGE_SEEDS) * len(ARMS) * (len(BRIDGE_STEPS) - 2)
    om_bytes = st["bytes"] / st["files"]
    total_bytes = n_files * om_bytes  # OpenMythos file size for every file (upper bound: transformer is smaller)
    storage_h = (total_bytes / 1e6 / st["push_mb_per_s"] + total_bytes / 1e6 / st["pull_mb_per_s"]) * MARGIN / 3600
    rep["per_state_seconds"], rep["diag_hours_by_level"] = {}, {}
    for level in (0, 1, 2):
        durs = []
        for (K, arm), pp in parts.items():
            sec = max(per_state_seconds(p, level, arm) for p in pp.values())
            rep["per_state_seconds"][f"level{level}_K{K}_{arm}"] = sec
            n = len(K2_SEEDS) * len(K2_STEPS) if K == 2 else len(BRIDGE_SEEDS) * len(BRIDGE_STEPS)
            durs += [sec] * n
        rep["diag_hours_by_level"][str(level)] = makespan(sorted(durs, reverse=True)) * MARGIN / 3600
    # level 2 best case: no MLP at all on P1 / P3 (classes K and 10)
    best = []
    for (K, arm), pp in parts.items():
        p = max(pp.values(), key=lambda q: per_state_seconds(q, 1, arm))
        p13 = sum(v for k, v in p["fit_seconds_by_classes"].items() if k.startswith("fit_mlp") and k[9:] in (str(K), "10"))
        n = len(K2_SEEDS) * len(K2_STEPS) if K == 2 else len(BRIDGE_SEEDS) * len(BRIDGE_STEPS)
        best += [per_state_seconds(p, 1, arm) - p13] * n
    rep["diag_hours_level2_best_case"] = makespan(sorted(best, reverse=True)) * MARGIN / 3600
    rep["diag_hours_by_level"]["2"] = rep["diag_hours_by_level"]["1"]  # budget: saving not guaranteed
    eval_h = sum(v["estimated_seconds_test_1000_bodies"] for v in ev.values()) * len(K2_SEEDS) * MARGIN / 3600
    rep["storage_budget"] = {"files": n_files, "bytes_upper_bound": total_bytes,
                             "gib_upper_bound": total_bytes / 2**30,
                             "lfs_storage_gib": total_bytes / 2**30 + st["bytes"] / 2**30,
                             "lfs_download_gib_verification": total_bytes / 2**30,
                             "hours_push_and_verify": storage_h,
                             "quota": "pending: the owner confirms the Git LFS storage / bandwidth quota (GitHub Billing & Licensing, Usage)"}
    rep["hours"] = {"training": train_h, "storage": storage_h, "formal_judgment": eval_h,
                    "diagnostics_by_level": rep["diag_hours_by_level"]}
    level = next((lv for lv in (0, 1, 2) if rep["diag_hours_by_level"][str(lv)] <= DIAG_LIMIT_H), None)
    rep["diag_limit_hours"] = DIAG_LIMIT_H
    rep["chosen_level"] = level
    rep["memory_mb"] = {"training_4_jobs": T["memory"], "diagnostics_4_jobs": dg["memory"], "machine_total": 15 * 1024}
    if level is not None:
        rep["frozen_workload"] = {
            "level": level, "m5a_bodies": 500, "m5b_batches": 200 if level == 0 else 100,
            "mlp_p13_when_linear_detected": level < 2, "parallel_workers": 4,
            "k2_seeds": list(K2_SEEDS), "k2_steps": list(K2_STEPS), "k2_train_steps": 12000,
            "bridge_seeds": list(BRIDGE_SEEDS), "bridge_steps": list(BRIDGE_STEPS), "bridge_train_steps": 3000,
        }
        rep["hours"]["total_estimate"] = (train_h + storage_h + eval_h + rep["diag_hours_by_level"][str(level)])
    with open(os.path.join(HERE, "timing.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps({"hours": rep["hours"], "level2_best_case": rep["diag_hours_level2_best_case"],
                      "chosen_level": level, "storage": rep["storage_budget"]}, indent=1, ensure_ascii=False))
    return 0 if level is not None else 4


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--diag-job":
        arm, K, label, ck, outdir = sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5] or None, sys.argv[6]
        return diag_job(arm, K, label, ck, outdir)
    if len(sys.argv) >= 2 and sys.argv[1] == "summarize":
        sys.exit(summarize())
    assert sys.argv[1] == "run" and sys.argv[2] == "--scratch", "usage: e_timing.py run --scratch S"
    S = sys.argv[3]
    os.makedirs(PARTS, exist_ok=True)

    def dump(name, obj):
        with open(os.path.join(PARTS, f"{name}.json"), "w") as f:
            json.dump(obj, f, indent=1)

    dump("train", stage_train(S))
    dump("storage", stage_storage(S))
    dump("diag_jobs", stage_diag(S))
    dump("eval", stage_eval(S))
    sys.exit(summarize())


if __name__ == "__main__":
    main()
