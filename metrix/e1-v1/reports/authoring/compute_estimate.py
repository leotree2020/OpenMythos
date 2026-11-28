#!/usr/bin/env python3
"""E1-V1 protocol section 10: compute, disk and cost estimate for the Owner's decision (pending field 1 and 3 of
Task Order section 14). Every measured input is read from the committed E1-PILOT records (file and field printed);
every V1 workload number comes from reports/authoring/v1_data_check.txt (token sums printed by v1_data_check.py,
passed here as constants and printed). No GPU, no model. Run from the repository root:

  python3 metrix/e1-v1/reports/authoring/compute_estimate.py
"""
import json
import statistics
from pathlib import Path

R = Path("metrix/e1-pilot/results")


def load(p):
    return json.loads((R / p).read_text(encoding="utf-8"))


def mean(xs):
    return statistics.fmean(xs)


# ------------------------------------------------------------------ measured inputs (E1-PILOT, A100 80GB PCIe)
runs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((R / "training_runs").glob("*.json"))}


def step_s(prefix):
    xs = [r["accounting"]["wall_seconds"] / r["steps_run"] for n, r in runs.items() if n.startswith(prefix)]
    return mean(xs), len(xs)


st_F, nF = step_s("F-F3-")
st_L, nL = step_s("L-L6-")
st_A, nA = step_s("A-A5-")
ck = [runs[n]["checkpoint"]["seconds"] for n in runs if n.startswith("F-F3-")]
save_hash = mean([c["save"] + c["hash"] for c in ck])
reload_s = mean([c["reload"] for c in ck])
hash_s = mean([c["hash"] for c in ck])
step2 = load("step2_record.json")
dev_eval_em = step2["preflight"]["dev_evaluation_seconds"]
step7 = load("step7_record.json")
g08_eval = step7["step_info"]["seconds"] / 3 - reload_s          # 3 reloads + 3 DEV evaluations without EM
step3 = load("step3_record.json")
base_load = step3["step_info"]["seconds"] - dev_eval_em           # base load + N DEV evaluation (with EM)
print("MEASURED (E1-PILOT records)")
print("  step seconds F3 %.4f (training_runs/F-F3-*.json accounting.wall_seconds / steps_run, %d runs)" % (st_F, nF))
print("  step seconds L6 %.4f (training_runs/L-L6-*.json, %d runs)" % (st_L, nL))
print("  step seconds A5 %.4f (training_runs/A-A5-*.json, %d runs; includes the anchor KL forward/backward)" % (st_A, nA))
print("  checkpoint save + hash %.2f s, reload %.2f s, state hash %.2f s (training_runs/F-F3-*.json checkpoint.seconds)" % (save_hash, reload_s, hash_s))
print("  DEV evaluation with EM %.2f s (step2_record.json preflight.dev_evaluation_seconds)" % dev_eval_em)
print("  DEV evaluation without EM %.2f s (step7_record.json step_info.seconds / 3 - reload; G0.8 re-evaluations)" % g08_eval)
print("  base model load %.2f s (step3_record.json step_info.seconds - DEV evaluation with EM)" % base_load)

# Pilot DEV scoring workload, approximated with the V1 per-sequence means (same templates and name rules)
QA_MEAN, CB_MEAN, D1_MEAN = 30.481, 13.842, 248.893          # v1_data_check.txt: DEV-QA, closed-book, D1 DEV ids
pilot_tokens = 1280 * QA_MEAN + 480 * CB_MEAN + 100 * D1_MEAN
tps = pilot_tokens / g08_eval
em_per_gen = (dev_eval_em - g08_eval) / 320
print("DERIVED")
print("  Pilot DEV scoring tokens ~ %.0f (1280 QA x %.3f + 480 CB x %.3f + 100 windows x %.3f)" % (pilot_tokens, QA_MEAN, CB_MEAN, D1_MEAN))
print("  float32 scoring throughput ~ %.0f tokens/s; greedy EM ~ %.4f s per question" % (tps, em_per_gen))

# ------------------------------------------------------------------ V1 workloads (v1_data_check.txt)
V1 = {"qa_dev": 78032, "cb": 13288, "d1_dev": 99557, "d2_dev": 107377}
QA_TEST = 3840 * QA_MEAN * 1.05            # 3 TEST questions per fact; TEST templates ~5% longer (assumption)
D2_PAD = 1.3                               # padding factor for the variable-length D2 prompts (assumption)
SAFETY = 1.2
print("  V1 DEV workload tokens: QA %d, closed-book %d, D1 %d, D2 %d (x %.1f padding)" % (V1["qa_dev"], V1["cb"], V1["d1_dev"], V1["d2_dev"], D2_PAD))


def plan(name, doses, max_passes, d_scale=1.0, test_brackets_per_run=5, test_points=3):
    steps_pass = 30
    ev_dev = (V1["qa_dev"] + V1["cb"] + d_scale * (V1["d1_dev"] + D2_PAD * V1["d2_dev"])) / tps
    ev_test_full = (QA_TEST + V1["cb"] + d_scale * (V1["d1_dev"] + D2_PAD * V1["d2_dev"])) / tps + 960 * em_per_gen
    ev_test_fact = (QA_TEST + V1["cb"]) / tps + 960 * em_per_gen
    saves_per_run = min(doses, 5)
    # Gate D: N DEV; Z0 x3 (2 passes, save + reload + 2 hashes); P+ x3 (11 passes, save); reproducibility re-eval
    gate_d = (base_load + ev_dev) + 3 * (base_load + 2 * steps_pass * st_F + save_hash + reload_s + hash_s + ev_dev) \
        + 3 * (base_load + 11 * steps_pass * st_F + save_hash + ev_dev) + (reload_s + ev_dev)
    curves = 0.0
    for st, extra_load, sv in ((st_F, 0, save_hash), (st_L, 0, 2.0), (st_A, base_load, save_hash)):
        curves += 3 * (base_load + extra_load + max_passes * steps_pass * st + doses * ev_dev + saves_per_run * sv)
    sy = 6 * (base_load + 11 * steps_pass * st_F + save_hash + ev_dev + 10.0)     # +10 s S own-mapping scoring
    g08 = 3 * (reload_s + ev_dev)
    brackets = 9 * test_brackets_per_run
    test = (base_load + ev_test_full) + 9 * (reload_s + hash_s + ev_test_fact) + brackets * (reload_s + hash_s + ev_test_full)
    preflight = 3 * (base_load + 20 * 1.0) + ev_dev
    total = gate_d + curves + sy + g08 + test + preflight
    disk_ckpt = 6.88 * (6 * saves_per_run + 3 + 6 + 3 + 3)     # F/A curve saves + F d0 + S/Y + P+ + Z0 (GB)
    disk_worst = 6.88 * (6 * doses + 3 + 6 + 3 + 3)
    print("PLAN %s: %d dose points up to %d passes, damage sets x %.2f, TEST brackets/run %d (points %d)" % (
        name, doses, max_passes, d_scale, test_brackets_per_run, test_points))
    print("  one DEV evaluation %.1f s; one full TEST evaluation %.1f s" % (ev_dev, ev_test_full))
    print("  runs: curves 9 (F, L, A x 3 seeds), S 3, Y 3, Z0 3, P+ 3 = 21 training runs; DEV evaluations %d" % (9 * doses + 1 + 3 + 3 + 1 + 6 + 3))
    print("  hours: Gate D %.2f, curves %.2f, S/Y %.2f, G0.8 %.2f, TEST %.2f, preflight %.2f -> GPU %.2f; x %.1f = %.2f" % (
        gate_d / 3600, curves / 3600, sy / 3600, g08 / 3600, test / 3600, preflight / 3600, total / 3600, SAFETY, SAFETY * total / 3600))
    rental = SAFETY * total / 3600 + 2.0
    print("  rental hours ~ GPU x %.1f + 2.0 (setup, CPU data steps, approval waits) = %.2f; cost at 2.14 USD/h: GPU part %.2f USD, rental %.2f USD" % (
        SAFETY, rental, 2.14 * SAFETY * total / 3600, 2.14 * rental))
    print("  checkpoints on disk ~%.0f GB expected, %.0f GB worst case (all dose points of F and A saved)" % (disk_ckpt, disk_worst))
    return SAFETY * total / 3600


main = plan("MAIN", 10, 32)
r1 = plan("R1 (7 dose points)", 7, 32)
r2 = plan("R2 (D1 200 + D2 400 per split)", 10, 32, d_scale=0.5)
r3 = plan("R3 (TEST only at Acq 0.80)", 10, 32, test_brackets_per_run=2, test_points=1)
r4 = plan("R4 (R1 + R2 + R3)", 7, 32, d_scale=0.5, test_brackets_per_run=2, test_points=1)
print("SAVINGS vs MAIN (hours, with safety factor): R1 %.2f, R2 %.2f, R3 %.2f, R4 %.2f" % (main - r1, main - r2, main - r3, main - r4))
