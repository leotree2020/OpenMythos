"""Executor's tables for reports/PILOT_FINAL_REPORT.md (E1-PILOT final report round, tasks/PILOT_REPORT_ORDER.md item 2).

Reads only committed records under metrix/e1-pilot/results/ (via `git show <rev>:<path>`, so working-tree edits cannot
change the input) and prints the values the report quotes, each with its file and JSON field. Derived numbers (sums,
the cost arithmetic) are printed with the formula. It recomputes no statistic of protocol section 6: the independent
recomputation of the point estimates and CIs is the data-auditor's (audit/pilot_final_recompute.py).

Usage (repository root): python3 -I metrix/e1-pilot/reports/pilot_final/report_tables.py [rev]   (rev default 53800ef7)
"""
import hashlib
import json
import subprocess
import sys

REV = sys.argv[1] if len(sys.argv) > 1 else "53800ef7ba5070fb1bb571c4a96a1130acebdf04"
R = "metrix/e1-pilot/results"
RUNS = ["F-F1-seed101", "F-F2-seed101", "F-F3-seed101", "F-F4-seed101", "F-F5-seed101", "F-F6-seed101",
        "L-L1-seed101", "L-L2-seed101", "L-L3-seed101", "L-L4-seed101", "L-L5-seed101", "L-L6-seed101",
        "A-A1-seed101", "A-A2-seed101", "A-A3-seed101", "A-A4-seed101", "A-A5-seed101", "A-A6-seed101",
        "F-F3-seed202", "F-F3-seed303", "L-L6-seed202", "L-L6-seed303", "A-A5-seed202", "A-A5-seed303",
        "S-F3-seed101", "S-F3-seed202", "S-F3-seed303", "Y-F3-seed101", "Y-F3-seed202", "Y-F3-seed303"]
SEEDS = ("101", "202", "303")
UNIT_PRICE = 2.14          # USD per hour, Owner-reported (tasks/PILOT_REPORT_ORDER.md item 2)
OWNER_COST = 6.72          # USD, Owner-reported actual spend (same source)


def blob(path):
    return subprocess.run(["git", "show", "%s:%s" % (REV, path)], check=True, capture_output=True).stdout


def load(path):
    return json.loads(blob(path).decode("utf-8"))


def section(title):
    print("\n== %s" % title)


def main():
    print("rev %s" % REV)
    section("1. record hashes cited by later records (sha256 of the committed file bytes at rev)")
    gate0_sha = hashlib.sha256(blob("%s/gate0_record.json" % R)).hexdigest()
    sel_sha = hashlib.sha256(blob("%s/selection_freeze_record.json" % R)).hexdigest()
    st10_sha = hashlib.sha256(blob("%s/st10_record.json" % R)).hexdigest()
    aud_sha = hashlib.sha256(blob("metrix/e1-pilot/audit/st10_l6_test_count.json")).hexdigest()
    marker = load("%s/test_evaluation_marker.json" % R)
    st10 = load("%s/st10_record.json" % R)
    step8 = load("%s/step8_record.json" % R)
    sel = load("%s/selection_freeze_record.json" % R)
    checks = [
        ("gate0_record.json", gate0_sha, "step8_record.json gate0_record_sha256", step8["gate0_record_sha256"]),
        ("gate0_record.json", gate0_sha, "selection_freeze_record.json gate0_record_sha256",
         sel["gate0_record_sha256"]),
        ("gate0_record.json", gate0_sha, "st10_record.json authorization.gate0_record_sha256",
         st10["authorization"]["gate0_record_sha256"]),
        ("selection_freeze_record.json", sel_sha, "st10_record.json authorization.selection_record_sha256",
         st10["authorization"]["selection_record_sha256"]),
        ("st10_record.json", st10_sha, "test_evaluation_marker.json st10_record_sha256", marker["st10_record_sha256"]),
        ("audit/st10_l6_test_count.json", aud_sha, "test_evaluation_marker.json auditor_count_sha256",
         marker["auditor_count_sha256"]),
    ]
    for name, got, where, cited in checks:
        print("%-30s %s | cited in %s %s | %s" % (name, got, where, cited, "equal" if got == cited else "DIFFERENT"))

    section("2. checkpoint state_sha256: training_runs/<run>.json checkpoint vs selection_freeze_record.json and "
            "test_evaluation_marker.json checkpoints")
    n_ok = 0
    for run in RUNS:
        rec = load("%s/training_runs/%s.json" % (R, run))
        ck = rec["checkpoint"]
        same = (ck["state_sha256"] == ck["reloaded_state_sha256"] == sel["checkpoints"][run]
                == marker["checkpoints"][run])
        n_ok += same
        if not same:
            print("DIFFERENT: %s" % run)
    print("30 runs: %d equal in all four places (state_sha256, reloaded_state_sha256, freeze record, marker)" % n_ok)
    step3 = load("%s/step3_record.json" % R)
    print("N: step3_record.json N.state_sha256 %s | marker checkpoints.N %s | %s" % (
        step3["N"]["state_sha256"], marker["checkpoints"]["N"],
        "equal" if step3["N"]["state_sha256"] == marker["checkpoints"]["N"] else "DIFFERENT"))

    section("3. training runs (training_runs/<run>.json): config, accounting, dev summary, dnll")
    hdr = ("run", "config", "steps_run", "fact_tok", "anchor_tok", "train_flops", "anchor_flops", "wall_s",
           "acc_dev_learned", "acc_cb", "em_dev_learned", "dnll", "ppl_deg_%", "device_name", "finite")
    print(" | ".join(hdr))
    tot = {"fact_tokens": 0, "anchor_tokens": 0, "train_flops": 0, "anchor_flops": 0, "wall_seconds": 0.0,
           "steps": 0, "ckpt_seconds": 0.0}
    devices = set()
    for run in RUNS:
        rec = load("%s/training_runs/%s.json" % (R, run))
        a, d = rec["accounting"], rec["dev"]
        cfg = {k: v for k, v in rec["config"].items() if k != "id"}
        devices.add(rec["device_name"])
        for k in ("fact_tokens", "train_flops", "wall_seconds", "steps"):
            tot[k] += a[k]
        tot["anchor_tokens"] += a.get("anchor_tokens", 0)
        tot["anchor_flops"] += a.get("anchor_flops", 0)
        tot["ckpt_seconds"] += sum(rec["checkpoint"]["seconds"].values())
        print(" | ".join(str(x) for x in (
            run, json.dumps(cfg, sort_keys=True), rec["steps_run"], a["fact_tokens"], a.get("anchor_tokens", "-"),
            "%.6e" % a["train_flops"], ("%.6e" % a["anchor_flops"]) if "anchor_flops" in a else "-",
            "%.2f" % a["wall_seconds"], "%.4f" % d["acc_dev_learned"], "%.4f" % d["acc_cb"],
            "%.4f" % d["em_dev_learned"], "%.5f" % rec["dnll"], "%.2f" % rec["ppl_degradation_pct"],
            rec["device_name"], rec["finite"])))
    print("totals over 30 runs: steps %d, fact_tokens %d, anchor_tokens %d, train_flops %.6e, anchor_flops %.6e, "
          "train+anchor flops %.6e, training wall_seconds %.2f, checkpoint save/hash/reload seconds %.2f" % (
              tot["steps"], tot["fact_tokens"], tot["anchor_tokens"], tot["train_flops"], tot["anchor_flops"],
              tot["train_flops"] + tot["anchor_flops"], tot["wall_seconds"], tot["ckpt_seconds"]))
    print("device_name values over the 30 runs: %s" % sorted(devices))

    section("4. GPU wall-clock and step times")
    exf = load("%s/experiment_record_formal_20261128T045921Z.json" % R)["template"]
    ext = load("%s/experiment_record_test-evaluate_20261128T072505Z.json" % R)["template"]
    ca_f = exf["Compute accounting (tokens / steps / FLOPs / wall-clock)"]
    ca_t = ext["Compute accounting (tokens / steps / FLOPs / wall-clock)"]
    print("experiment_record_formal ... gpu_wall_clock_seconds %.6f" % ca_f["gpu_wall_clock_seconds"])
    print("experiment_record_test-evaluate ... gpu_wall_clock_seconds %.6f" % ca_t["gpu_wall_clock_seconds"])
    print("formal steps seconds: %s ; sum %.6f" % (json.dumps(ca_f["steps"]), sum(ca_f["steps"].values())))
    man = blob("%s/command_output/final_work_manifest.txt" % R).decode("utf-8")
    clock = json.loads(man.split("contents of gpu_clock.json =====\n", 1)[1].split("\n", 1)[0])
    segs = [b - a for a, b in clock["segments"]]
    print("final_work_manifest.txt gpu_clock.json segments: %s s each; sum %.6f s = %.6f h; open %s" % (
        ["%.6f" % s for s in segs], sum(segs), sum(segs) / 3600, clock["open"]))
    gpu_h = ca_t["gpu_wall_clock_seconds"] / 3600
    print("ST7 bound 4 h: cumulative %.6f h" % gpu_h)
    s2 = load("%s/step2_record.json" % R)["preflight"]
    print("step2 preflight: st11_estimate_hours %.6f (b17 %.6f + checkpoint_overhead %.3f s / 3600), bound %s, %s" % (
        s2["st11_estimate_hours"], s2["b17_estimate_hours"], s2["checkpoint_overhead"]["seconds"],
        s2["st11_bound_hours"], s2["st11"]))

    section("5. cost (Owner-reported: USD %.2f actual, unit price USD %.2f / h)" % (OWNER_COST, UNIT_PRICE))
    print("implied rental hours = %.2f / %.2f = %.4f h" % (OWNER_COST, UNIT_PRICE, OWNER_COST / UNIT_PRICE))
    print("GPU wall-clock part = %.6f h x %.2f = USD %.4f" % (gpu_h, UNIT_PRICE, gpu_h * UNIT_PRICE))
    print("RUNBOOK_A100.md section 6 planning: unit price 1.8 USD/h; rental 3.6-9.0 USD; GPU part 2.2-5.6 USD")

    section("6. peak memory (stepN_record.json step_info.peak_memory_bytes; CUDA max_memory_allocated)")
    for n in range(2, 9):
        si = load("%s/step%d_record.json" % (R, n))["step_info"]
        print("step %d: %d bytes = %.3f GiB, seconds %.3f, started %s" % (
            n, si["peak_memory_bytes"], si["peak_memory_bytes"] / 2 ** 30, si["seconds"], si["started_utc"]))

    section("7. report-only values: Spill (comparisons.Spill-<arm>:<split>:<seed>), from step7 / TEST result")
    s7 = load("%s/step7_record.json" % R)
    ter = load("%s/test_evaluation_result.json" % R)
    for split, rec in (("DEV", s7), ("TEST", ter)):
        for arm in ("F", "L", "A", "S", "Y"):
            row = []
            for sd in SEEDS + ("avg",):
                c = rec["comparisons"]["Spill-%s:%s" % (arm, sd)]
                assert c["purpose"] == "Spill-%s:%s:%s" % (arm, split, sd)
                row.append("%s %s [%s, %s]" % (sd, c["point_exact"], "%.4f" % c["ci_low"], "%.4f" % c["ci_high"]))
            print("%s Spill-%s: %s" % (split, arm, " ; ".join(row)))

    section("8. report-only values: EM and FPR per model")
    names = ["F-F3", "L-L6", "A-A5", "S-F3", "Y-F3"]
    print("DEV N (step3_record.json N.summary): em_dev_learned %s em_dev_unread %s fpr_dev %s" % (
        step3["N"]["summary"]["em_dev_learned"], step3["N"]["summary"]["em_dev_unread"],
        step3["N"]["summary"]["fpr_dev"]))
    for nm in names:
        for sd in SEEDS:
            d = load("%s/training_runs/%s-seed%s.json" % (R, nm, sd))["dev"]
            t = ter["summaries"]["%s-seed%s" % (nm, sd)]
            print("%s-seed%s DEV em_learned %.4f em_unread %.4f fpr %.4f | TEST em_learned %.4f em_unread %.4f "
                  "fpr %.4f" % (nm, sd, d["em_dev_learned"], d["em_dev_unread"], d["fpr_dev"], t["em_test_learned"],
                                t["em_test_unread"], t["fpr_test"]))
    t = ter["summaries"]["N"]
    print("TEST N: em_learned %.4f em_unread %.4f fpr %.4f" % (t["em_test_learned"], t["em_test_unread"],
                                                                t["fpr_test"]))

    section("9. report-only: S on its own mapping (step7_record.json s_own_mapping)")
    print(json.dumps(s7["s_own_mapping"], sort_keys=True))

    section("10. selection (step4_record.json, step5_record.json)")
    s4 = load("%s/step4_record.json" % R)["selection"]
    s5 = load("%s/step5_record.json" % R)["selection"]
    for arm, s in (("F", s4), ("L", s5["L"]), ("A", s5["A"])):
        print("%s selected %s ranking %s" % (arm, s["selected"], s["ranking"]))
        for row in s["rows"]:
            print("   %s" % json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
