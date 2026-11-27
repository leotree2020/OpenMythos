"""ic11_08 (implementation stage C, C4 code commit (staged tree 63121c79, parent 3bc761ea), round 1; supplementary to
tasks 1-5; my ic10_06 with this round's ST11 fields): the smoke outputs are labelled and carry no Gate 0 conclusion
(Implementation Task Order V1 section 7), and the stop / preflight fields this fix changed.
  A. every JSON file under <smoke>/records has label "SMOKE — NOT A RESULT" and mode "smoke"; every .txt record starts
     with the label line; data/, checkpoints/, preflight/ each hold LABEL.txt with the label; exactly one experiment
     record pair experiment_record_smoke_<start>.json / .txt (file name with the start time, MINOR fix);
  B. gate0_record: NOT_TESTED with the note 冒烟测试，不构成结论, G0.1-G0.10; experiment record Status NOT_TESTED, 20
     fields; "smoke: device check skipped" (step 1 record, smoke report);
  C. the recorded "would stop" entries are exactly the value stops whose condition holds by the recorded values: ST3
     (bounds from the frozen protocol's ST3 row), ST11 now read from st11_estimate_hours (tasks/IMPL_C4_RULING.md item 1:
     B17's estimate + the checkpoint overhead; the field st11_reads names it), ST2 / ST4 / ST5 from G0.3 / G0.7 / G0.6 of the smoke Gate 0
     record; no step record carries a "stopped" field (no stop propagated in the smoke; MAJOR 3's field appears only
     when a stop propagates);
  D. preflight, recomputed by me from the recorded timing block: my counts from the protocol (base-model loads: N at
     step 3, 30 runs, N at TEST = 32; 30 checkpoints; further checkpoint reloads: 3 G0.8 re-evaluations + 15 TEST
     checkpoints = 18; state hashes at TEST: 16 models + N once more = 17; TEST checkpoint files 15), CHECKPOINT_OVERHEAD
     = 32 x load + 30 x (2 hash + save + reload + file hash) + 18 x reload + 17 hash + 15 file hash, the ST11 estimate
     B17 + overhead (st11_estimate_hours; the record field checkpoint_overhead); B17's total from its recorded parts
     (train_seconds + eval_seconds + used_seconds) / 3600; train_seconds = mean step x total_steps x (other runs +
     a_runs x a_factor) and eval_seconds = evaluation_units x DEV evaluation seconds; the TEST look-ahead that
     test_evaluate would use with this timing (my model of the previous round, ic10_04e; unchanged by this commit, ic11_05 E): load (N) +
     15 reload (the checkpoints) + 16 x DEV evaluation x TEST/DEV questions per fact + 17 hash (no file hash), the
     questions per fact counted by me from the frozen SPLIT_MANIFEST templates (informational here).
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic11_08_smoke_labels.py <repo_root> <smoke_work_dir>"""
import glob
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import re
from collections import Counter
from ia_common import frozen_json, frozen_protocol, run

LABEL = "SMOKE — NOT A RESULT"


def main():
    repo, work = sys.argv[1:3]
    rec = os.path.join(work, "records")
    ok = True
    print("== A. labels")
    js, txt = [], []
    for d, _, fs in os.walk(rec):
        for f in fs:
            (js if f.endswith(".json") else txt).append(os.path.join(d, f))
    bad = []
    for p in js:
        o = json.load(open(p, encoding="utf-8"))
        if o.get("label") != LABEL or o.get("mode") != "smoke":
            bad.append((os.path.relpath(p, rec), o.get("label"), o.get("mode")))
    badt = [os.path.relpath(p, rec) for p in txt if open(p, encoding="utf-8").read().split("\n")[0] != LABEL]
    print("JSON records %d, without the SMOKE label or mode smoke: %s | text records %d %s, first line not the label: %s" % (
        len(js), bad, len(txt), [os.path.relpath(p, rec) for p in txt], badt))
    ok &= not bad and not badt and len(js) > 0
    for d in ("data", "checkpoints", "preflight"):
        lab = open(os.path.join(work, d, "LABEL.txt"), encoding="utf-8").read()
        print("  %s/LABEL.txt %r" % (d, lab))
        ok &= lab == LABEL + "\n"
    exj = sorted(glob.glob(os.path.join(rec, "experiment_record_smoke_*.json")))
    ext = sorted(glob.glob(os.path.join(rec, "experiment_record_smoke_*.txt")))
    names_ok = (len(exj) == 1 and len(ext) == 1 and exj[0][:-5] == ext[0][:-4]
                and re.fullmatch(r"experiment_record_smoke_\d{8}T\d{6}Z\.json", os.path.basename(exj[0])) is not None)
    print("experiment records %s %s | one pair named with the start time: %s" % (
        [os.path.basename(x) for x in exj], [os.path.basename(x) for x in ext], names_ok))
    ok &= names_ok

    print("\n== B. no Gate 0 conclusion")
    g0 = json.load(open(os.path.join(rec, "gate0_record.json"), encoding="utf-8"))["gate0"]
    conds = sorted(g0["conditions"], key=lambda c: int(c.split(".")[1]))
    print("gate0_status %r note %r | conditions %s" % (g0["gate0_status"], g0.get("note"), conds))
    ok &= g0["gate0_status"] == "NOT_TESTED" and g0.get("note") == "冒烟测试，不构成结论" and conds == ["G0.%d" % i for i in range(1, 11)]
    exo = json.load(open(exj[0], encoding="utf-8"))
    ex = exo["template"]
    print("experiment record Status %r Interpretation %r | template fields %d | Experiment ID %r" % (
        ex["Status"], ex["Interpretation"], len(ex), ex["Experiment ID"]))
    ok &= ex["Status"] == "NOT_TESTED" and len(ex) == 20 and ex["Experiment ID"].endswith(
        os.path.basename(exj[0])[len("experiment_record_smoke_"):-5])
    s1 = json.load(open(os.path.join(rec, "step1_record.json"), encoding="utf-8"))
    sr = json.load(open(os.path.join(rec, "smoke_report.json"), encoding="utf-8"))
    print("device note: step1_record %r | smoke_report %r" % (s1["device"], sr["device_note"]))
    ok &= s1["device"] == "smoke: device check skipped" == sr["device_note"]

    print("\n== C. would-stop entries and step records")
    prot = frozen_protocol(repo)
    st3 = [ln for ln in prot.split("\n") if ln.startswith("| ST3 |")][0]
    st11 = [ln for ln in prot.split("\n") if ln.startswith("| ST11 |")][0]
    cb_min, acc_min = [float(x) for x in re.findall(r"< (0\.\d+)", st3)]
    hours = float(re.search(r"超过 ([\d.]+) 小时", st11).group(1))
    print("frozen protocol: %s\n                 %s\n  -> ST3 bounds Acc_CB %s, Acc %s | ST11 hours %s" % (st3, st11, cb_min, acc_min, hours))
    steps = {k: json.load(open(os.path.join(rec, "step%d_record.json" % k), encoding="utf-8")) for k in range(1, 9)}
    s4 = steps[4]["positive_control"]
    pre = steps[2]["preflight"]
    sat = {c: x["satisfied"] for c, x in g0["conditions"].items()}
    want = sorted((["ST3"] if s4["acc_cb"] < cb_min or s4["acc_dev_learned"] < acc_min else [])
                  + (["ST11"] if pre["st11_estimate_hours"] > hours else [])
                  + (["ST2"] if not sat["G0.3"] else []) + (["ST4"] if not sat["G0.7"] else [])
                  + (["ST5"] if not sat["G0.6"] else []))
    got = sorted(x["stop"] for x in sr["smoke_recorded_stops"])
    print("positive control acc_cb %s acc_dev_learned %s (step4 st3 %r) | preflight st11_reads %r, st11_estimate_hours %.4f h "
          "(step2 st11 %r) | G0.3 %s G0.6 %s G0.7 %s (step3 st2 %r)" % (
              s4["acc_cb"], s4["acc_dev_learned"], s4["st3"], pre.get("st11_reads"), pre["st11_estimate_hours"], pre["st11"],
              sat["G0.3"], sat["G0.6"], sat["G0.7"], steps[3]["N"].get("st2")))
    print("recorded 'would stop' %s == expected from the recorded values %s: %s | every entry labelled: %s" % (
        got, want, got == want, all(x["label"] == LABEL for x in sr["smoke_recorded_stops"])))
    ok &= got == want and all(x["label"] == LABEL for x in sr["smoke_recorded_stops"])
    ok &= pre.get("st11_reads") == "b17_estimate_hours + checkpoint_overhead.seconds / 3600"
    ok &= s4["st3"] == ("smoke: would stop" if "ST3" in want else "not triggered")
    ok &= pre["st11"] == ("smoke: would stop" if "ST11" in want else "within bound")
    ok &= steps[3]["N"].get("st2") == ("smoke: would stop" if "ST2" in want else "not triggered")
    stopped = {k: v.get("stopped") for k, v in steps.items() if "stopped" in v}
    print("step records 1-8 present; kinds %s | 'stopped' fields %s (expected none)" % (
        [steps[k].get("kind") for k in range(1, 9)], stopped))
    ok &= not stopped and [steps[k].get("kind") for k in range(1, 9)] == ["step%d" % k for k in range(1, 9)]
    st7 = steps[7]
    print("step7 smoke_stops %s | excluded %s | experiment record Stop Conditions stop %r, smoke_recorded %s" % (
        [x["stop"] for x in st7["smoke_stops"]], st7["excluded"], ex["Stop Conditions"]["stop"],
        [x["stop"] for x in ex["Stop Conditions"]["smoke_recorded"]]))
    ok &= st7["excluded"] == [] and ex["Stop Conditions"]["stop"] is None
    ok &= sorted(x["stop"] for x in ex["Stop Conditions"]["smoke_recorded"]) == want

    print("\n== D. preflight (my recomputation from the recorded timing)")
    t = pre["timing"]
    ss = frozen_json(repo, "SEARCH_SPACE.json")
    sm = frozen_json(repo, "SPLIT_MANIFEST.json")
    runs = ss["counts"]["total_training_runs"]
    seeds = len(ss["training_contract"]["training_seeds"])
    test_models = 1 + 5 * seeds                    # N + F, L, A, S, Y x 3 training seeds (protocol section 8 step 8)
    counts = {"base_loads": 1 + runs + 1, "checkpoints": runs, "checkpoint_reloads": seeds + test_models - 1,
              "test_state_hashes": test_models + 1, "test_file_hashes": test_models - 1, "test_models": test_models}
    rc = pre["checkpoint_overhead"]["counts"]
    print("my counts %s | recorded %s | equal %s" % (counts, rc, counts == rc))
    ok &= counts == rc
    ov = (counts["base_loads"] * t["load_s"] + counts["checkpoints"] * (2 * t["hash_s"] + t["save_s"] + t["reload_s"] + t["file_hash_s"])
          + counts["checkpoint_reloads"] * t["reload_s"] + counts["test_state_hashes"] * t["hash_s"]
          + counts["test_file_hashes"] * t["file_hash_s"])
    rs = pre["checkpoint_overhead"]["seconds"]
    print("overhead seconds mine %.9f | recorded %.9f | |diff| %.3g" % (ov, rs, abs(ov - rs)))
    ok &= abs(ov - rs) < 1e-9
    p = pre["b17_parts"]
    total_steps = ss["training_contract"]["total_steps"]
    train_s = pre["summary"]["mean_seconds_per_step_excluding_first"] * total_steps * (p["other_runs"] + p["a_runs"] * p["a_factor"])
    eval_s = p["evaluation_units"] * pre["dev_evaluation_seconds"]
    b17 = (p["train_seconds"] + p["eval_seconds"] + p["used_seconds"]) / 3600.0
    print("B17 parts %s | train_seconds mine %.6f (recorded %.6f) | eval_seconds mine %.6f (recorded %.6f) | total from the "
          "parts %.9f h == b17_estimate_hours %.9f h: %s" % (p, train_s, p["train_seconds"], eval_s, p["eval_seconds"], b17,
                                                            pre["b17_estimate_hours"], abs(b17 - pre["b17_estimate_hours"]) < 1e-9))
    ok &= abs(train_s - p["train_seconds"]) < 1e-6 and abs(eval_s - p["eval_seconds"]) < 1e-6 \
        and abs(b17 - pre["b17_estimate_hours"]) < 1e-9
    s = pre["st11_estimate_hours"]
    print("ST11 estimate (B17 + overhead) mine %.9f h | recorded %.9f h | equal %s" % (pre["b17_estimate_hours"] + ov / 3600.0, s,
                                                                      abs(pre["b17_estimate_hours"] + ov / 3600.0 - s) < 1e-9))
    ok &= abs(pre["b17_estimate_hours"] + ov / 3600.0 - s) < 1e-9
    per_rel = {k: Counter(x["relation"] for x in sm["templates"] if x["kind"] == k) for k in ("DEV", "TEST")}
    q_dev, q_test = set(per_rel["DEV"].values()), set(per_rel["TEST"].values())
    print("questions per fact from the frozen templates: DEV %s TEST %s" % (dict(per_rel["DEV"]), dict(per_rel["TEST"])))
    ok &= len(q_dev) == 1 and len(q_test) == 1
    la = (t["load_s"] + (counts["test_models"] - 1) * t["reload_s"]
          + counts["test_models"] * t["dev_evaluation_seconds"] * q_test.pop() / q_dev.pop()
          + counts["test_state_hashes"] * t["hash_s"])
    print("TEST look-ahead with this (smoke) timing, informational: %.3f s = %.4f h" % (la, la / 3600.0))
    print("timing block keys %s" % sorted(t))
    ok &= sorted(t) == sorted(["mean_step_s", "a_factor", "dev_evaluation_seconds", "load_s", "hash_s", "save_s",
                               "reload_s", "file_hash_s"])
    return bool(ok)


run(main)
