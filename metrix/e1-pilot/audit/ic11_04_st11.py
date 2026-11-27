"""ic11_04 (implementation stage C, C4 code commit, round 1; task 1 of the invocation): ST11's estimate (Review Gate ruling
of 2026-11-27, tasks/IMPL_C4_RULING.md item 1: ST11 reads B17's estimate + the checkpoint overhead, stop above 3.5 h)
recomputed by me from the smoke's step 2 record (<smoke>/records/step2_record.json: the measured per-step seconds,
fact_tokens_per_step, anchor_tokens_per_step, the timing block) and counts I read from the frozen protocol text
(sections 7, 8, 10, 11; git cat-file at the frozen commit) and the frozen SPLIT_MANIFEST.json / SEARCH_SPACE.json.
Smoke values (CPU, random small model): no conclusion about the A100 run.

My model (my own formula, written from the protocol and the revised B17 text; nothing of the Executor imported):
  runs (section 7): F, L, A x 6 configs at the search seed (18) + F, L, A x the 2 other seeds (6) + S, Y x 3 seeds (6)
    = 30; arm A runs = 6 + 2 = 8, other runs 22; steps per run 300 (section 7 table "共 300 步"; Y also 300).
  mean step seconds = mean of the recorded seconds_per_step without the first (warm-up).
  A factor = 1 + (forward + train coefficient) x anchor tokens per step / (train coefficient x fact tokens per step),
    coefficients from section 10 (training 6 P T, forward 2 P T).
  evaluation units: DEV: N (step 3) + 30 runs + 3 G0.8 re-evaluations (section 8 G0.8: the 3 checkpoints of F's
    selected configuration evaluated twice); TEST: N + 15 final checkpoints (F, L, A, S, Y x 3 seeds), each x TEST/DEV
    questions per fact (frozen templates per relation).
  B17 = (mean_step x 300 x (22 + 8 x A factor) + units x dev_evaluation_seconds + GPU seconds already used) / 3600;
    GPU seconds already used = 0 in the smoke (CPU; the smoke's work directory has no device ledger).
  checkpoint overhead (revised B17 text) = 32 x load (N, the 30 runs, N at TEST) + 30 x (2 x hash + save + reload +
    file hash) + 18 x reload (3 G0.8 + 15 TEST checkpoints) + 17 x hash (16 TEST models + N once more) + 15 x file hash.
  ST11 estimate = B17 + overhead / 3600; ST11 triggers iff estimate > 3.5 (bound from the ST11 row); the smoke records
    "within bound" or "smoke: would stop".
usage: python -I -B ic11_04_st11.py <repo_root> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import re
from collections import Counter
from ia_common import frozen_json, frozen_protocol, run

TOL = 1e-9


def close(a, b):
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def one(pattern, text, what):
    m = re.findall(pattern, text)
    print("  protocol %-44s %r -> %s" % (what, pattern, m))
    if len(m) != 1:
        raise ValueError("%s: %d matches" % (what, len(m)))
    return m[0]


def main():
    repo, work = sys.argv[1:3]
    ok = True
    prot = frozen_protocol(repo)
    ss = frozen_json(repo, "SEARCH_SPACE.json")
    sm = frozen_json(repo, "SPLIT_MANIFEST.json")
    print("== counts read from the frozen protocol (commit 87a244db)")
    per_arm, search_total = [int(x) for x in one(r"F、L、A 各 \*\*(\d+)\*\* 个配置,共 \*\*(\d+)\*\* 次搜索训练", prot, "search")]
    other_seeds = one(r"F、L、A 用种子 ([\d、]+) 各再训练一次", prot, "extra seeds F, L, A").split("、")
    sy_seeds = int(one(r"S、Y 各训练 (\d+) 个种子", prot, "S, Y seeds"))
    total_runs = int(one(r"\*\*训练总次数 (\d+)。\*\*", prot, "total runs"))
    steps = int(one(r"每遍 \d+ 步;共 (\d+) 步", prot, "steps per run"))
    y_steps = int(one(r"batch 16,同为 (\d+) 步", prot, "Y steps"))
    g08 = int(one(r"\| G0\.8 \| 复现：对 F 选定配置的 (\d+) 个 checkpoint 各评测两次", prot, "G0.8 row (table)"))
    train_c, fwd_c = [int(x) for x in one(r"训练 FLOPs ≈ (\d+) · P · T,前向 FLOPs ≈ (\d+) · P · T", prot, "section 10")]
    st11_row = [ln for ln in prot.split("\n") if ln.startswith("| ST11 |")]
    bound = float(re.search(r"预估总时长超过 ([\d.]+) 小时", st11_row[0]).group(1))
    print("  protocol ST11 row %r -> bound %s h" % (st11_row[0], bound))
    test_arms = ["F", "L", "A", "S", "Y"]                  # section 8 step 8 / T1-T3: every arm's final checkpoints
    n_seeds = len(ss["training_contract"]["training_seeds"])
    runs = 3 * per_arm + 3 * len(other_seeds) + 2 * sy_seeds
    a_runs = per_arm + len(other_seeds)
    print("  my runs %d (search %d + %d + %d) == protocol total %d == SEARCH_SPACE counts %s: %s | A runs %d, other %d | steps "
          "%d (Y %d) == SEARCH_SPACE total_steps %d" % (
              runs, 3 * per_arm, 3 * len(other_seeds), 2 * sy_seeds, total_runs, ss["counts"], runs == total_runs ==
              ss["counts"]["total_training_runs"], a_runs, runs - a_runs, steps, y_steps, ss["training_contract"]["total_steps"]))
    ok &= runs == total_runs == ss["counts"]["total_training_runs"] and search_total == 3 * per_arm
    ok &= steps == y_steps == ss["training_contract"]["total_steps"]
    per_rel = {k: Counter(x["relation"] for x in sm["templates"] if x["kind"] == k) for k in ("DEV", "TEST")}
    q = {k: set(v.values()) for k, v in per_rel.items()}
    print("  questions per fact from the frozen templates: DEV %s TEST %s" % (dict(per_rel["DEV"]), dict(per_rel["TEST"])))
    ok &= len(q["DEV"]) == 1 and len(q["TEST"]) == 1
    ratio = next(iter(q["TEST"])) / next(iter(q["DEV"]))
    test_models = 1 + len(test_arms) * n_seeds
    dev_units = 1 + runs + g08
    units = dev_units + test_models * ratio
    counts = {"base_loads": 1 + runs + 1, "checkpoints": runs, "checkpoint_reloads": g08 + (test_models - 1),
              "test_state_hashes": test_models + 1, "test_file_hashes": test_models - 1, "test_models": test_models}
    print("  evaluation units: DEV %d (N + %d runs + %d G0.8) + TEST %d models x %g = %g | overhead counts %s" % (
        dev_units, runs, g08, test_models, ratio, units, json.dumps(counts, sort_keys=True)))

    s2 = json.load(open(os.path.join(work, "records", "step2_record.json"), encoding="utf-8"))
    pre = s2["preflight"]
    t = pre["timing"]
    print("\n== inputs from the smoke's step 2 record")
    sps = pre["summary"]["seconds_per_step"]
    mean_step = sum(sps[1:]) / len(sps[1:])
    print("  seconds_per_step %s -> my mean without the first %.15f | recorded summary %.15f, timing.mean_step_s %.15f" % (
        sps, mean_step, pre["summary"]["mean_seconds_per_step_excluding_first"], t["mean_step_s"]))
    ok &= close(mean_step, pre["summary"]["mean_seconds_per_step_excluding_first"]) and close(mean_step, t["mean_step_s"])
    fact, anchor, dev = pre["fact_tokens_per_step"], pre["anchor_tokens_per_step"], pre["dev_evaluation_seconds"]
    print("  fact_tokens_per_step %r anchor_tokens_per_step %r dev_evaluation_seconds %r (timing %r) | timing %s" % (
        fact, anchor, dev, t["dev_evaluation_seconds"], json.dumps({k: t[k] for k in ("load_s", "hash_s", "save_s",
                                                                                         "reload_s", "file_hash_s")})))
    ok &= dev == t["dev_evaluation_seconds"]
    ledger = [os.path.join(d, f) for d, _, fs in os.walk(work) for f in fs if "ledger" in f.lower()]
    print("  device ledger files under the smoke's work directory: %s -> GPU seconds already used = 0" % ledger)
    ok &= not ledger

    print("\n== my values")
    a_factor = 1.0 + (fwd_c + train_c) * anchor / (train_c * fact)
    train_s = mean_step * steps * ((runs - a_runs) + a_runs * a_factor)
    eval_s = units * dev
    b17 = (train_s + eval_s + 0.0) / 3600.0
    over = (counts["base_loads"] * t["load_s"]
            + counts["checkpoints"] * (2 * t["hash_s"] + t["save_s"] + t["reload_s"] + t["file_hash_s"])
            + counts["checkpoint_reloads"] * t["reload_s"] + counts["test_state_hashes"] * t["hash_s"]
            + counts["test_file_hashes"] * t["file_hash_s"])
    total = b17 + over / 3600.0
    print("  A factor 1 + (%d + %d) x %.6f / (%d x %.6f) = %.12f" % (fwd_c, train_c, anchor, train_c, fact, a_factor))
    print("  training %.6f x %d x (%d + %d x %.6f) = %.9f s | evaluation %g x %.9f = %.9f s | used 0" % (
        mean_step, steps, runs - a_runs, a_runs, a_factor, train_s, units, dev, eval_s))
    print("  B17 estimate %.12f h" % b17)
    print("  checkpoint overhead %d x %.9f + %d x (2 x %.9f + %.9f + %.9f + %.9f) + %d x %.9f + %d x %.9f + %d x %.9f = %.9f s "
          "(%.9f h)" % (counts["base_loads"], t["load_s"], counts["checkpoints"], t["hash_s"], t["save_s"], t["reload_s"],
                        t["file_hash_s"], counts["checkpoint_reloads"], t["reload_s"], counts["test_state_hashes"], t["hash_s"],
                        counts["test_file_hashes"], t["file_hash_s"], over, over / 3600.0))
    print("  ST11 estimate = B17 + overhead / 3600 = %.12f h | bound %s h | ST11 triggers (estimate > bound): %s | B17 alone "
          "> bound: %s" % (total, bound, total > bound, b17 > bound))

    print("\n== comparison with the record")
    p = pre["b17_parts"]
    rows = [("A factor (b17_parts / timing)", a_factor, p["a_factor"]), ("A factor timing", a_factor, t["a_factor"]),
            ("train_seconds", train_s, p["train_seconds"]), ("eval_seconds", eval_s, p["eval_seconds"]),
            ("evaluation_units", units, p["evaluation_units"]), ("used_seconds", 0.0, p["used_seconds"]),
            ("b17_estimate_hours", b17, pre["b17_estimate_hours"]),
            ("checkpoint_overhead.seconds", over, pre["checkpoint_overhead"]["seconds"]),
            ("st11_estimate_hours", total, pre["st11_estimate_hours"])]
    for name, mine, rec in rows:
        print("  %-30s mine %.12f | recorded %.12f | equal (rel. tol %g) %s" % (name, mine, rec, TOL, close(mine, rec)))
        ok &= close(mine, rec)
    print("  a_runs %s other_runs %s (mine %d, %d) | checkpoint_overhead.counts %s == mine: %s" % (
        p["a_runs"], p["other_runs"], a_runs, runs - a_runs, json.dumps(pre["checkpoint_overhead"]["counts"], sort_keys=True),
        pre["checkpoint_overhead"]["counts"] == counts))
    ok &= p["a_runs"] == a_runs and p["other_runs"] == runs - a_runs and pre["checkpoint_overhead"]["counts"] == counts
    exp_st11 = "smoke: would stop" if total > bound else "within bound"
    print("  st11 %r (expected from my sum: %r) | st11_bound_hours %r (== %s) | st11_reads %r" % (
        pre["st11"], exp_st11, pre["st11_bound_hours"], bound, pre["st11_reads"]))
    ok &= pre["st11"] == exp_st11 and pre["st11_bound_hours"] == bound
    ok &= pre["st11_reads"] == "b17_estimate_hours + checkpoint_overhead.seconds / 3600"
    gone = [k for k in ("checkpoint_overhead_report_only", "b17_plus_checkpoint_overhead_hours_report_only") if k in pre]
    print("  the two renamed fields still present in the record: %s | preflight keys %s" % (gone, sorted(pre)))
    ok &= not gone
    sr = json.load(open(os.path.join(work, "records", "smoke_report.json"), encoding="utf-8"))
    st11_recorded = [x for x in sr["smoke_recorded_stops"] if x["stop"] == "ST11"]
    print("  smoke_report smoke_recorded_stops ST11 entries %s (expected %s)" % (st11_recorded, "one" if total > bound else "none"))
    ok &= bool(st11_recorded) == (total > bound)

    print("\n== the smoke recording (reports/impl_c/c4_03_smoke.txt)")
    txt = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c4_03_smoke.txt"), encoding="utf-8").read()
    lines = [ln for ln in txt.split("\n") if "B17 estimate" in ln and "checkpoint overhead" in ln]
    for ln in lines:
        print("  log line: %s" % ln)
    m = re.search(r"B17 estimate ([\d.]+) h \+ checkpoint overhead ([\d.]+) h = ([\d.]+) h \(ST11, bound ([\d.]+) h\)",
                  lines[0]) if len(lines) == 1 else None
    if m:
        want = ("%.3f" % b17, "%.3f" % (over / 3600.0), "%.3f" % total, "%g" % bound)
        print("  log values %s == my values at 3 decimals %s: %s" % (m.groups(), want, m.groups() == want))
        ok &= m.groups() == want
    else:
        print("  log line not found exactly once")
        ok = False
    return bool(ok)


run(main)
