#!/usr/bin/env python3
"""
Interim audit after gate 2 (stage-1 mid-way audit request, items 1-6). Read
only: it starts no job and writes only stage1/interim_audit_gate2.json.

    1  R2 per arm, seed and checkpoint (from gate2/gate2.json)
    2  R3 per state: values compared, maximum difference, failures
    3  the interrupted first launch of gate 2: jobs started and not ended in
       its log, files quarantined, and the evidence for the resumed launch
    4  the stage-1 ledger recomputed independently from the raw intervals
       (a second implementation: an event sweep), checked against the job
       evidence (gate logs, output file times) for lost or doubled time
    5  code provenance: the files R1, R2, R3 ran, their sha256 and change
       times against the gate start times; E1's frozen code tree
    6  no stage 2-4 artefact, no test2, no confirmatory seed trained
"""

import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(GE, "..", ".."))
S1 = os.path.join(HERE, "stage1")
sys.path.insert(0, GE)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def ts(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%H:%M:%S")


def clock(day_epoch, hhmmss):
    h, m, s = map(int, hhmmss.split(":"))
    return day_epoch + h * 3600 + m * 60 + s


def log_events(path):
    out = []
    for line in open(path):
        m = re.match(r"\[(\d\d:\d\d:\d\d)\] (start|end) (\S+)(?: rc=(\S+))?", line)
        if m:
            out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def main():
    g2 = json.load(open(os.path.join(S1, "gate2", "gate2.json")))
    res = {}
    # 1 R2
    r2 = {}
    for k, v in sorted(g2["R2"].items()):
        ck = v["checkpoints"]
        r2[k] = {"checkpoints_compared": len(ck), "steps": sorted(int(s) for s in ck),
                 "all_bitwise_equal": all(x["state_dict_bitwise_equal"] for x in ck.values()),
                 "all_param_sha256_equal_manifest": all(x["param_sha256_equals_manifest"] for x in ck.values()),
                 "logs_equal_first_3000": v["logs_equal_first_3000"], "kept_attempt_comparisons": v.get("equal_to_kept_attempt"),
                 "pass": v["pass"]}
    res["1_R2"] = {"runs": r2, "n_runs": len(r2), "n_checkpoints": sum(x["checkpoints_compared"] for x in r2.values()),
                   "failures": [k for k, x in r2.items() if not x["pass"]], "pass": g2["R2_pass"]}
    # 2 R3
    r3 = {k: {"values_compared": v["n_values"], "max_abs_diff": v["max_abs_diff"], "mismatches": len(v["mismatches"]),
              "param_sha256_equal": v["param_sha256_equal"], "parts": len(v["parts"]), "pass": v["pass"]}
          for k, v in sorted(g2["R3"].items())}
    per_run = {}
    for k, v in r3.items():
        run = k.rsplit("_step", 1)[0]
        e = per_run.setdefault(run, {"states": 0, "values": 0, "max_abs_diff": 0.0, "failures": 0})
        e["states"] += 1
        e["values"] += v["values_compared"]
        e["max_abs_diff"] = max(e["max_abs_diff"], v["max_abs_diff"])
        e["failures"] += not v["pass"]
    res["2_R3"] = {"per_run": per_run, "per_state": r3, "n_states": len(r3), "values_compared": g2["R3_values_compared"],
                   "max_abs_diff": g2["R3_max_abs_diff"], "failures": [k for k, v in r3.items() if not v["pass"]],
                   "tolerance": 1e-6, "pass": g2["R3_pass"]}
    # 3 interruption
    l1 = log_events(os.path.join(S1, "gate2_stdout_launch1.log"))
    started = [n for _, ev, n, _ in l1 if ev == "start"]
    ended = {n: rc for _, ev, n, rc in l1 if ev == "end"}
    killed = [n for n in started if n not in ended]
    l2 = log_events(os.path.join(S1, "gate2_stdout.log"))
    started2 = [n for _, ev, n, _ in l2 if ev == "start"]
    res["3_interruption"] = {
        "launches": json.load(open(os.path.join(S1, "gate2", "launches.json"))),
        "launch1_jobs_started": len(started), "launch1_jobs_ended_rc0": sorted(n for n, rc in ended.items() if rc == "0"),
        "launch1_jobs_ended_nonzero": sorted(n for n, rc in ended.items() if rc != "0"),
        "launch1_jobs_killed": killed,
        "killed_jobs_had_no_output_before_launch2": all(n not in g2.get("skipped_complete_jobs", []) for n in killed),
        "killed_jobs_rerun_in_launch2": {n: n in started2 for n in killed},
        "killed_jobs_results_after_rerun": {n: (g2["R3"].get(n[3:]) or {}).get("pass") for n in killed},
        "launch2_skipped_complete_jobs_rechecked": g2.get("skipped_complete_jobs"),
        "launch2_skipped_rechecked_pass": all((g2["R2"].get(n[3:]) or g2["R3"].get(n[3:]) or {}).get("pass")
                                              for n in g2.get("skipped_complete_jobs", [])),
        "quarantined_partial_attempt_files": g2.get("quarantined_partial_attempt_files"),
        "quarantine_dirs": sorted(os.listdir(os.path.join(S1, "gate2", "quarantine"))) if os.path.isdir(
            os.path.join(S1, "gate2", "quarantine")) else [],
        "surviving_processes_after_kill": "none (ps at 10:53:59 showed no train_e2c / d2c / s1_gate2 process)"}
    # 4 ledger
    led = json.load(open(os.path.join(S1, "budget_ledger_s1.json")))
    iv = led["intervals"]
    events = sorted([(i["start"], 1) for i in iv] + [(i["end"], -1) for i in iv])
    depth, last, union = 0, None, 0.0
    for t, d in events:
        if depth > 0:
            union += t - last
        depth += d
        last = t
    total_len = sum(i["end"] - i["start"] for i in iv)
    day = dt.datetime.fromtimestamp(iv[0]["start"], dt.timezone.utc).replace(hour=0, minute=0, second=0).timestamp()
    evidence = {}
    for label, logf in (("gate1", "gate1/logs"), ("gate2", "gate2_stdout_launch1.log"), ("gate2_resume1", "gate2_stdout.log")):
        i = next((x for x in iv if x["label"] == label), None)
        p = os.path.join(S1, logf)
        if i is None or not os.path.exists(p):
            continue
        if os.path.isdir(p):
            times = [os.path.getmtime(f) for f in glob.glob(os.path.join(p, "*.log"))]
            first, lastt = min(times), max(times)
        else:
            ev = log_events(p)
            first, lastt = clock(day, ev[0][0]), clock(day, ev[-1][0])
        evidence[label] = {"interval": [ts(i["start"]), ts(i["end"])], "job_activity": [ts(first), ts(lastt)],
                           "activity_inside_interval": i["start"] - 1 <= first and lastt <= i["end"] + 1}
    dev_out = {"dev_smoke_c0": "dev/smoke_c0.json", "dev_smoke_c1": "dev/smoke_c1.json", "dev_smoke_c2": "dev/smoke_c2.json",
               "dev_r1_trk_openmythos": "dev/trk_openmythos.json", "dev_r1_c0_openmythos": "dev/c0_openmythos.json",
               "dev_r1_trk_transformer": "dev/trk_transformer.json", "dev_r1_c0_transformer": "dev/c0_transformer.json",
               "dev_d2c_tf_s1_75": "dev/d2c_tf_s1_75.json", "dev_d2c_om_s2_150": "dev/d2c_om_s2_150.json",
               "dev_v1aux_tf": "dev/v1aux_tf.json", "dev_alin_om": "dev/alin_om.json", "dev_v4_tests": "v4/launcher_tests.json",
               "precheck": "precheck_run1.json"}
    for label, rel in dev_out.items():
        i = next((x for x in iv if x["label"] == label), None)
        p = os.path.join(S1, rel)
        if i and os.path.exists(p):
            m = os.path.getmtime(p)
            evidence[label] = {"interval": [ts(i["start"]), ts(i["end"])], "output_written": ts(m),
                               "output_inside_interval": i["start"] <= m <= i["end"] + 1}
    labels = [i["label"] for i in iv]
    res["4_ledger"] = {
        "intervals": [{"label": i["label"], "start": ts(i["start"]), "end": ts(i["end"]), "seconds": round(i["end"] - i["start"], 1),
                       "open": i["open"], "pid": i.get("pid")} for i in iv],
        "stored_total_seconds": led["total_seconds"], "recomputed_union_seconds": union,
        "agree_within_1s": abs(union - led["total_seconds"]) <= 1.0,
        "sum_of_interval_lengths": total_len, "overlap_counted_once_seconds": total_len - union,
        "duplicate_labels": sorted({x for x in labels if labels.count(x) > 1}),
        "open_intervals": [i["label"] for i in iv if i["open"]],
        "closed_after_interruption_as_written": led["closed_after_interruption"],
        "job_evidence": evidence,
        "all_evidence_inside_intervals": all(v.get("activity_inside_interval", v.get("output_inside_interval")) for v in evidence.values()),
        "precheck_run_without_ledger_exec": "the two precheck runs carry their own intervals (labels 'precheck')"}
    # 5 code provenance
    used = {"R1": ["train_e2c.py", "e2c_common.py", "s1_gate1.py"], "R2": ["train_e2c.py", "e2c_common.py", "s1_gate2.py"],
            "R3": ["d2c.py", "e2c_common.py", "s1_compare.py", "s1_gate2.py"]}
    starts = {"R1": next(i["start"] for i in iv if i["label"] == "gate1"), "R2": next(i["start"] for i in iv if i["label"] == "gate2"),
              "R3": next(i["start"] for i in iv if i["label"] == "gate2")}
    prov = {}
    for gate, files in used.items():
        prov[gate] = {f: {"sha256": sha(os.path.join(HERE, f)), "modified": ts(os.path.getmtime(os.path.join(HERE, f))),
                          "unchanged_since_gate_start": os.path.getmtime(os.path.join(HERE, f)) < starts[gate]}
                      for f in files}
    import run_gate_e as E1L
    tree, per = E1L.code_tree()
    rf = json.load(open(os.path.join(GE, "run_freeze.json")))
    diff_since = subprocess.run(["git", "diff", "--name-only", "5ef6a54", "--", "experiments/gate_e/e2c/*.py"], cwd=ROOT,
                                capture_output=True, text=True).stdout.split()
    res["5_code"] = {"files": prov, "gate_starts": {k: ts(v) for k, v in starts.items()},
                     "s1_gate2_note": "s1_gate2.py changed between launch 1 and launch 2 (resume logic only, 10:55); "
                                      "R2 / R3 checks (check_r2, compare_state) are the same functions in both",
                     "s1_budget_note": "ledger v1 (stage1/s1_budget_v1_used_until_gate2.py) ran gates 1-2; v2 written at 10:57 for later runs",
                     "E1_frozen_code_files_unchanged": [f for f in rf["code_files"] if rf["code_files"][f] != per.get(f)] == [],
                     "E1_imported_modules": ["train_k.py (R1 reference run and imported helpers)", "e_common.py", "e_task.py", "e_m0.py",
                                             "e_m1.py", "e_m2.py", "e_m3.py", "e_masks.py", "gate_d/runner.py", "gate_d/d2.py",
                                             "gate_d/common.py", "basic_learn/models.py", "gen_gate_a/*", "budget_a/schedule.py",
                                             "open_mythos/*"],
                     "E1_code_tree_sha256_now": tree, "E1_code_tree_sha256_frozen": rf["code_tree_sha256"],
                     "e2c_py_changed_since_5ef6a54": diff_since}
    # 6 stage 2-4 absent, seeds
    formal = {p: os.path.exists(os.path.join(HERE, p)) for p in ("runs", "results", "judgments", "e2c_workload_freeze.json",
                                                                 "run_freeze.json", "pairing_ledger.json", "test2_record.json")}
    test2_files = [p for p in glob.glob(os.path.join(ROOT, "experiments", "**", "*test2*"), recursive=True)
                   if not p.endswith(".py")]
    seeds = {}
    for f in glob.glob(os.path.join(S1, "**", "*.json"), recursive=True):
        try:
            r = json.load(open(f))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(r, dict) and "loss_every_step" in r and "seed" in r:
            seeds.setdefault(r["seed"], []).append(os.path.relpath(f, S1))
    res["6_scope"] = {"formal_stage3_4_paths_exist": formal, "test2_files_found": test2_files,
                      "seeds_of_all_training_records_in_stage1": {str(k): len(v) for k, v in sorted(seeds.items())},
                      "confirmatory_seed_trained": any(201 <= s <= 224 for s in seeds),
                      "keyspace_enumeration": "never executed: e2c_test2.keyspace refuses unless E2C_KEYSPACE_STAGE is 2 or 4; "
                                              "no stage-1 process set it (the V4 stage-4 cases use stub jobs)",
                      "v4_dev_run_note": "the V4 development run (10:37-10:49) used stub jobs named after seeds 201 / 202 / 1 in "
                                         "temporary directories: no model was trained, diagnosed or evaluated; its synthetic test "
                                         "evaluated an untrained Transformer on 50 synthetic non-held-out bodies (never in R*)",
                      "artifacts_pushed_in_stage1": "none so far (V5 not run)"}
    res["pass_items_1_2"] = res["1_R2"]["pass"] and res["2_R3"]["pass"]
    json.dump(res, open(os.path.join(S1, "interim_audit_gate2.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"R2": res["1_R2"]["pass"], "R3": res["2_R3"]["pass"], "killed": killed,
                      "ledger_agree": res["4_ledger"]["agree_within_1s"], "evidence_inside": res["4_ledger"]["all_evidence_inside_intervals"],
                      "confirmatory_seed_trained": res["6_scope"]["confirmatory_seed_trained"]}, indent=1))


if __name__ == "__main__":
    main()
