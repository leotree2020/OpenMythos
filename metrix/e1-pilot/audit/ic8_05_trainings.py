"""ic8_05 (implementation stage C, C2 fix commit (staged tree b40224e6, parent 1900b1fe), round 1; my ic7_05 run again; task 5): the 30
training runs of the smoke test.
  A. The training plan derived by me from the frozen SEARCH_SPACE.json (protocol section 7): F, L, A each 6 configs
     with the search seed; the selection on DEV recomputed by me from the per-question DEV details (records/details)
     -- correct(f, q) = 1[score of the true answer > every other candidate's score] (a tie is wrong), Score(f) = mean
     over the fact's DEV questions, Acc(learned) = mean over the 120 learned facts (facts.jsonl), dNLL = mean over
     domains of the mean over windows of NLL_run(w) - NLL_N(w) (N's DEV details) -- by the frozen rule: highest Acc,
     then lower dNLL, then lower learning rate, then lower config index; then F, L, A with the selected config and the
     two other training seeds, S and Y with F's config and the three seeds. Run names "<arm>-<config>-seed<seed>".
     Compared with the smoke's step4/step5 selections and rows, the step6 training_plan / runs_completed, the 30
     records under records/training_runs and the 30 checkpoint files.
  B. Every record: kind training_run, mode smoke, label, arm / config_id / config / seed / phase consistent with the
     name and SEARCH_SPACE.json, finite, steps_run == mode_steps == 3 (smoke --steps 3), contract_steps == the frozen
     total_steps; my Acc(learned) and dNLL equal to the record's dev.acc_dev_learned and dnll.
  C. Checkpoints (file bytes only -- never loaded; torch is not imported by this script): sha256 of
     checkpoints/<run>.pt == record checkpoint.file_sha256, size == file_bytes, file == "<run>.pt";
     state_sha256 == reloaded_state_sha256 in all 30 records; the 30 state hashes distinct and different from N's;
     smoke_report.json trainings: 30 completed, steps_run 3, state_sha256 equal to the records; the checkpoint
     directory holds exactly the 30 files + LABEL.txt (SMOKE label).
  D. G0.8 (informational recomputation): the second evaluation of F's selected config (details/*_dev_g08.json) against
     the first: max |score difference| over QA and closed-book items, prediction differences, max |NLL difference|,
     compared with step7_record values G0.8.
Data Auditor's own script; nothing of the Executor is imported.
usage: python -I -B ic8_05_trainings.py <repo_root> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import defaultdict
from fractions import Fraction
from ia_common import file_sha, frozen_json, read_jsonl, run

SMOKE_LABEL = "SMOKE — NOT A RESULT"


def load(p):
    return json.load(open(p, encoding="utf-8"))


def correct(item):
    sc, a = item["scores"], item["answer_index"]
    return all(sc[a] > s for i, s in enumerate(sc) if i != a)


def acc_learned(details, learned):
    per = defaultdict(list)
    for q in details["evaluation"]["dev_qa"]:
        per[q["fact_id"]].append(1 if correct(q) else 0)
    score = {f: Fraction(sum(v), len(v)) for f, v in per.items()}
    flags_ok = all(q["correct"] == correct(q) for q in details["evaluation"]["dev_qa"])
    return sum(score[f] for f in learned) / len(learned), flags_ok, {f: len(v) for f, v in per.items()}


def dnll(details, n_rows):
    base = {r["doc_id"]: r for r in n_rows}
    by_dom = defaultdict(list)
    for r in details["evaluation"]["general_dev"]:
        b = base[r["doc_id"]]
        assert b["domain"] == r["domain"] and b["n_w"] == r["n_w"]
        by_dom[r["domain"]].append(r["nll"] - b["nll"])
    return sum(sum(v) / len(v) for v in by_dom.values()) / len(by_dom), {d: len(v) for d, v in by_dom.items()}


def main():
    repo, work = sys.argv[1:3]
    rec, ck = os.path.join(work, "records"), os.path.join(work, "checkpoints")
    ok = True
    ss = frozen_json(repo, "SEARCH_SPACE.json")
    seeds, search_seed = ss["training_contract"]["training_seeds"], ss["search_seed"]
    total = ss["training_contract"]["total_steps"]
    facts = read_jsonl(os.path.join(work, "data", "facts.jsonl"))
    learned = [f["fact_id"] for f in facts if f["exposure"] == "learned"]
    print("frozen SEARCH_SPACE: seeds %s search seed %s total_steps %s counts %s | inherits S %r Y %r" % (
        seeds, search_seed, total, ss["counts"], ss["arms"]["S"]["inherits"], ss["arms"]["Y"]["inherits"]))
    n_det = load(os.path.join(rec, "details", "N_dev.json"))
    n_rows = n_det["evaluation"]["general_dev"]

    print("\n== A. selection recomputed from the DEV details")
    mine_acc, mine_dnll, selected = {}, {}, {}
    for arm in ("F", "L", "A"):
        rows = []
        for i, c in enumerate(ss["arms"][arm]["configs"]):
            name = "%s-%s-seed%d" % (arm, c["id"], search_seed)
            det = load(os.path.join(rec, "details", "%s_dev.json" % name))
            a, flags_ok, nq = acc_learned(det, learned)
            d, nd = dnll(det, n_rows)
            mine_acc[name], mine_dnll[name] = a, d
            rows.append((c["id"], i, c["learning_rate"], a, d))
            print("  %-14s acc_dev_learned %.10f (%s) dNLL %+.6e | recorded 'correct' flags == my rule: %s | questions "
                  "per fact %s | windows per domain %s" % (name, float(a), a, d, flags_ok, sorted(set(nq.values())), nd))
            ok &= flags_ok and set(nq.values()) == {2}
        ranking = sorted(rows, key=lambda r: (-r[3], r[4], r[2], r[1]))
        selected[arm] = ranking[0][0]
        s_rec = load(os.path.join(rec, "step4_record.json" if arm == "F" else "step5_record.json"))["selection"]
        s_rec = s_rec if arm == "F" else s_rec[arm]
        same_rank = [r[0] for r in ranking] == s_rec["ranking"]
        rows_eq = all(abs(x["acc"] - float(mine_acc["%s-%s-seed%d" % (arm, x["config_id"], search_seed)])) < 1e-12 and
                      abs(x["dnll"] - mine_dnll["%s-%s-seed%d" % (arm, x["config_id"], search_seed)]) < 1e-12 for x in s_rec["rows"])
        print("  %s: my selection %s ranking %s | smoke selection %s ranking %s | equal %s | smoke rows (acc, dnll) == mine "
              "(|diff| < 1e-12): %s" % (arm, selected[arm], [r[0] for r in ranking], s_rec["selected"], s_rec["ranking"],
                                        selected[arm] == s_rec["selected"] and same_rank, rows_eq))
        ok &= selected[arm] == s_rec["selected"] and same_rank and rows_eq
    plan = ["%s-%s-seed%d" % (arm, c["id"], search_seed) for arm in ("F", "L", "A") for c in ss["arms"][arm]["configs"]]
    plan += ["%s-%s-seed%d" % (arm, selected[arm], s) for arm in ("F", "L", "A") for s in seeds if s != search_seed]
    plan += ["%s-%s-seed%d" % (arm, selected["F"], s) for arm in ("S", "Y") for s in seeds]
    print("my plan: %d runs (frozen total_training_runs %d): %s" % (len(plan), ss["counts"]["total_training_runs"], plan))
    ok &= len(plan) == len(set(plan)) == ss["counts"]["total_training_runs"] == 30
    s6 = load(os.path.join(rec, "step6_record.json"))
    recs = sorted(x[:-5] for x in os.listdir(os.path.join(rec, "training_runs")) if x.endswith(".json"))
    pts = sorted(x[:-3] for x in os.listdir(ck) if x.endswith(".pt"))
    print("step6 training_plan == my plan (same order): %s | runs_completed == my plan (set): %s | selected %s == mine %s | "
          "excluded %s" % (s6["training_plan"] == plan, sorted(s6["runs_completed"]) == sorted(plan), s6["selected"],
                           selected, s6["excluded"]))
    ok &= s6["training_plan"] == plan and sorted(s6["runs_completed"]) == sorted(plan) and s6["selected"] == selected \
        and s6["excluded"] == []
    print("training_runs records %d == my plan: %s | checkpoint files %d == my plan: %s | other files in checkpoints/ %s" % (
        len(recs), recs == sorted(plan), len(pts), pts == sorted(plan),
        sorted(x for x in os.listdir(ck) if not x.endswith(".pt"))))
    ok &= recs == sorted(plan) and pts == sorted(plan) and sorted(x for x in os.listdir(ck) if not x.endswith(".pt")) == ["LABEL.txt"]
    print("checkpoints/LABEL.txt %r" % open(os.path.join(ck, "LABEL.txt"), encoding="utf-8").read())
    ok &= open(os.path.join(ck, "LABEL.txt"), encoding="utf-8").read() == SMOKE_LABEL + "\n"

    print("\n== B. the 30 records, C. their checkpoints (file bytes only)")
    cfg_of = {(arm, c["id"]): c for arm in ("F", "L", "A") for c in ss["arms"][arm]["configs"]}
    n_sha = load(os.path.join(rec, "step3_record.json"))["N"]["state_sha256"]
    sr = load(os.path.join(rec, "smoke_report.json"))
    states = []
    for name in plan:
        r = load(os.path.join(rec, "training_runs", "%s.json" % name))
        arm, cid, seed = name.split("-")[0], name.split("-")[1], int(name.split("seed")[1])
        phase = "search" if seed == search_seed and arm in ("F", "L", "A") else "seeds"
        cfg = cfg_of[("F" if arm in ("S", "Y") else arm, cid)]
        meta = (r["kind"] == "training_run" and r["mode"] == "smoke" and r["label"] == SMOKE_LABEL and r["run"] == name
                and r["arm"] == arm and r["config_id"] == cid and r["config"] == cfg and r["seed"] == seed
                and r["phase"] == phase and r["finite"] is True and r["steps_run"] == r["mode_steps"] == 3
                and r["contract_steps"] == total)
        c = r["checkpoint"]
        p = os.path.join(ck, "%s.pt" % name)
        fsha, size = file_sha(p), os.path.getsize(p)
        ck_ok = c["file"] == "%s.pt" % name and fsha == c["file_sha256"] and size == c["file_bytes"]
        st_ok = c["state_sha256"] == c["reloaded_state_sha256"]
        det = load(os.path.join(rec, "details", "%s_dev.json" % name))
        a, flags_ok, _ = acc_learned(det, learned)
        d, _ = dnll(det, n_rows)
        val_ok = abs(float(a) - r["dev"]["acc_dev_learned"]) < 1e-12 and abs(d - r["dnll"]) < 1e-12 and flags_ok
        t = sr["trainings"].get(name, {})
        rep_ok = t.get("steps_run") == 3 and t.get("finite") is True and t.get("state_sha256") == c["state_sha256"]
        states.append(c["state_sha256"])
        print("  %-14s meta %s | file sha256 %s == record %s, bytes %d == %s | state %s == reloaded %s | acc/dNLL == mine %s "
              "| smoke_report %s" % (name, meta, fsha[:16], fsha == c["file_sha256"], size, size == c["file_bytes"],
                                    c["state_sha256"][:16], st_ok, val_ok, rep_ok))
        ok &= meta and ck_ok and st_ok and val_ok and rep_ok
    print("state_sha256 distinct: %d of %d | N's state sha256 %s among them: %s | smoke_report trainings_completed %s, "
          "names == my plan %s" % (len(set(states)), len(states), n_sha[:16], n_sha in states, sr["trainings_completed"],
                                   sorted(sr["trainings"]) == sorted(plan)))
    ok &= len(set(states)) == 30 and n_sha not in states and sr["trainings_completed"] == 30 and sorted(sr["trainings"]) == sorted(plan)

    print("\n== D. G0.8 (informational recomputation; compared with step7_record)")
    g = load(os.path.join(rec, "step7_record.json"))["values"]["G0.8"]["checkpoints"]
    for s in seeds:
        name = "F-%s-seed%d" % (selected["F"], s)
        e1 = load(os.path.join(rec, "details", "%s_dev.json" % name))["evaluation"]
        e2 = load(os.path.join(rec, "details", "%s_dev_g08.json" % name))["evaluation"]
        items1, items2 = e1["dev_qa"] + e1["train_cb"], e2["dev_qa"] + e2["train_cb"]
        keyed = all((a["fact_id"], a["template_id"]) == (b["fact_id"], b["template_id"]) for a, b in zip(items1, items2))
        msd = max(abs(x - y) for a, b in zip(items1, items2) for x, y in zip(a["scores"], b["scores"]))
        pdiff = sum(1 for a, b in zip(items1, items2) if a["prediction"] != b["prediction"])
        n1 = {r["doc_id"]: r["nll"] for r in e1["general_dev"]}
        mnd = max(abs(r["nll"] - n1[r["doc_id"]]) for r in e2["general_dev"])
        x = g[str(s)]
        same = (len(items1) == len(items2) == x["items"] and keyed and msd == x["max_score_diff"] and mnd == x["max_nll_diff"]
                and pdiff == 0 and x["prediction_differences_not_allowed"] == [] and x["satisfied"] is True)
        print("  %s: items %d (record %d), aligned %s | max score diff %g (record %g) | prediction differences %d | max NLL "
              "diff %g (record %g) | satisfied (record) %s | equal %s" % (name, len(items1), x["items"], keyed, msd,
                                                                         x["max_score_diff"], pdiff, mnd, x["max_nll_diff"],
                                                                         x["satisfied"], same))
        ok &= same
    print("torch imported by this script: %s" % ("torch" in sys.modules))
    ok &= "torch" not in sys.modules
    return bool(ok)


run(main)
