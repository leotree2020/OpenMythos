"""ic7_06 (implementation stage C, C2 work commit (staged tree b80c9062, parent f8139f9), round 1; supplementary to tasks
1-5): the smoke outputs are labelled and carry no Gate 0 conclusion (Implementation Task Order V1 section 7).
  - every JSON file under <smoke>/records (step, run, details, Gate 0, smoke report, experiment record) has
    label "SMOKE — NOT A RESULT" and mode "smoke"; every .txt record starts with the label line; data/, checkpoints/,
    preflight/ each hold LABEL.txt with the label;
  - gate0_record: gate0_status NOT_TESTED with the note 冒烟测试，不构成结论, all ten conditions G0.1-G0.10 computed;
    experiment record Status NOT_TESTED; "smoke: device check skipped" recorded (step 1 record, smoke report);
  - the smoke's recorded "would stop" entries are exactly the value stops whose condition holds by the recorded values:
    ST3 (positive control: Acc_CB below the ST3 bound or Acc(F, DEV-QA, learned) below it; bounds read from the frozen
    protocol's ST3 / G0.4 / G0.5 text), ST11 (preflight estimate above the ST11 hours of the frozen protocol), and not
    ST2 / ST4 / ST5 (G0.3, G0.7, G0.6 satisfied in the smoke Gate 0 record).
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic7_06_smoke_labels.py <repo_root> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import re
from ia_common import frozen_protocol, run

LABEL = "SMOKE — NOT A RESULT"


def main():
    repo, work = sys.argv[1:3]
    rec = os.path.join(work, "records")
    ok = True
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
    g0 = json.load(open(os.path.join(rec, "gate0_record.json"), encoding="utf-8"))["gate0"]
    conds = sorted(g0["conditions"], key=lambda c: int(c.split(".")[1]))
    print("gate0_status %r note %r | conditions %s" % (g0["gate0_status"], g0.get("note"), conds))
    ok &= g0["gate0_status"] == "NOT_TESTED" and g0.get("note") == "冒烟测试，不构成结论" and conds == ["G0.%d" % i for i in range(1, 11)]
    ex = json.load(open(os.path.join(rec, "experiment_record_smoke.json"), encoding="utf-8"))["template"]
    print("experiment record Status %r Interpretation %r | template fields %d" % (ex["Status"], ex["Interpretation"], len(ex)))
    ok &= ex["Status"] == "NOT_TESTED" and len(ex) == 20
    s1 = json.load(open(os.path.join(rec, "step1_record.json"), encoding="utf-8"))
    sr = json.load(open(os.path.join(rec, "smoke_report.json"), encoding="utf-8"))
    print("device note: step1_record %r | smoke_report %r" % (s1["device"], sr["device_note"]))
    ok &= s1["device"] == "smoke: device check skipped" == sr["device_note"]

    prot = frozen_protocol(repo)
    st3 = [ln for ln in prot.split("\n") if ln.startswith("| ST3 |")][0]
    st11 = [ln for ln in prot.split("\n") if ln.startswith("| ST11 |")][0]
    cb_min, acc_min = [float(x) for x in re.findall(r"< (0\.\d+)", st3)]
    hours = float(re.search(r"超过 ([\d.]+) 小时", st11).group(1))
    print("frozen protocol: %s\n                 %s\n  -> ST3 bounds Acc_CB %s, Acc %s | ST11 hours %s" % (st3, st11, cb_min, acc_min, hours))
    s4 = json.load(open(os.path.join(rec, "step4_record.json"), encoding="utf-8"))["positive_control"]
    pre = json.load(open(os.path.join(rec, "step2_record.json"), encoding="utf-8"))["preflight"]
    sat = {c: x["satisfied"] for c, x in g0["conditions"].items()}
    want = sorted((["ST3"] if s4["acc_cb"] < cb_min or s4["acc_dev_learned"] < acc_min else [])
                  + (["ST11"] if pre["estimate_total_hours"] > hours else [])
                  + (["ST2"] if not sat["G0.3"] else []) + (["ST4"] if not sat["G0.7"] else [])
                  + (["ST5"] if not sat["G0.6"] else []))
    got = sorted(x["stop"] for x in sr["smoke_recorded_stops"])
    print("positive control acc_cb %s acc_dev_learned %s (step4 st3 %r) | preflight estimate %.3f h (step2 st11 %r) | G0.3 %s "
          "G0.6 %s G0.7 %s" % (s4["acc_cb"], s4["acc_dev_learned"], s4["st3"], pre["estimate_total_hours"], pre["st11"],
                               sat["G0.3"], sat["G0.6"], sat["G0.7"]))
    print("recorded 'would stop' %s == expected from the recorded values %s: %s | every entry labelled: %s" % (
        got, want, got == want, all(x["label"] == LABEL for x in sr["smoke_recorded_stops"])))
    ok &= got == want and all(x["label"] == LABEL for x in sr["smoke_recorded_stops"])
    return bool(ok)


run(main)
