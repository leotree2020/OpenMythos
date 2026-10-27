#!/usr/bin/env python3
"""Merge the per-case parts of the formal run into one results file and derive the summary tables used by the report."""
import glob
import gzip
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a_cases as C

ARMS = C.ARM_ORDER


def main():
    parts = sorted(glob.glob(os.path.join(HERE, "results", "parts", "T-*.json")) + glob.glob(os.path.join(HERE, "results", "parts", "T-*.json.gz")))
    results, envs, errors, unclean, notok = [], [], [], [], []
    for p in parts:
        d = json.load(gzip.open(p, "rt")) if p.endswith(".gz") else json.load(open(p))
        results += d["results"]
        envs.append({"part": os.path.basename(p), "git_commit": d["environment"]["git_commit"], "git_status_short": d["environment"]["git_status_short"],
                     "kernel": d["environment"]["kernel"], "supervisor_pid": d["environment"]["supervisor_pid"], "sentinel": d["environment"].get("sentinel")})
        if d.get("run_error"):
            errors.append((os.path.basename(p), d["run_error"]))
        unclean += d["cleanup_unclean_runs"]
        notok += d["tool_not_ok_runs"]
    matrix = C.summarize(results, ARMS)
    first_env = (json.load(gzip.open(parts[0], "rt")) if parts[0].endswith(".gz") else json.load(open(parts[0])))["environment"]
    out = {"experiment": "F3B-D1-A-CPU-001", "environment_first_part": first_env, "parts": envs, "results": results, "matrix": matrix,
           "run_errors": errors, "cleanup_unclean_runs": unclean, "tool_not_ok_runs": notok}
    path = os.path.join(HERE, "results", "a_predicate_cpu_001_results.json.gz")
    text = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n"
    with gzip.GzipFile(path, "wb", mtime=0) as f:        # mtime=0: byte-reproducible archive
        f.write(text.encode("ascii"))

    # ---------- derived tables
    der = {}
    der["totals"] = {a: dict(Counter(r["status"] for r in results if r["arm"] == a)) for a in ARMS + ["BENCH"]}
    der["runs_total"] = len(results)
    der["matrix_verdicts"] = {c: {a: v["verdict"] for a, v in d.items()} for c, d in matrix.items()}
    der["matrix_counts"] = {c: {a: v["counts"] for a, v in d.items()} for c, d in matrix.items()}
    der["matrix_failed_checks"] = {c: {a: v["failed_checks"] for a, v in d.items() if v["failed_checks"]} for c, d in matrix.items()}
    der["matrix_blocked"] = {c: {a: v["blocked"] for a, v in d.items() if v["blocked"]} for c, d in matrix.items()}

    def runs(case, arm):
        return [r for r in results if r["case"] == case and r["arm"] == arm]

    # race statistics
    race = {}
    for cid in ("T-08a", "T-08b", "T-08c", "T-14a", "T-14b"):
        race[cid] = {}
        for a in ARMS:
            rs = runs(cid, a)
            dec = Counter()
            false_esc = 0
            for r in rs:
                t = r.get("trace")
                if not t:
                    dec["NO_TRACE"] += 1
                    continue
                dec[t["decision"] if t["decision"] else "NONE"] += 1
                false_esc += 1 if t.get("false_escalation") else 0
            race[cid][a] = {"n": len(rs), "decisions": dict(dec), "false_escalations": false_esc,
                            "status": dict(Counter(r["status"] for r in rs))}
    der["race"] = race
    # T-14 signal results
    sig = defaultdict(Counter)
    for cid in ("T-14a", "T-14b"):
        for a in ("CA", "CB"):
            for r in runs(cid, a):
                for s in r.get("signal_records", []):
                    sig[(cid, a)][s["result"]] += 1
    der["t14_signal_results"] = {"%s/%s" % k: dict(v) for k, v in sig.items()}
    # killpg(pgid,0) on a zombie-only group (T-03 and T-02), before any arm action
    kp = Counter()
    for r in results:
        if r["case"] in ("T-02a", "T-02b", "T-03") and "reference_killpg0_before_any_arm_action" in r:
            kp[(r["case"], r["arm"], r["reference_killpg0_before_any_arm_action"], tuple(m["state"] for m in r["group_members_before_any_arm_action"]))] += 1
    der["killpg0_zombie_only_group_before_arm_action"] = {"%s|%s|%s|members=%s" % k: v for k, v in kp.items()}
    kpa = Counter()
    for r in results:
        if r["case"] in ("T-02a", "T-02b", "T-03") and "reference_killpg0_after_run" in r:
            kpa[(r["arm"], r["reference_killpg0_after_run"], r["post_run_observation"]["kill_pid0"], r["post_run_observation"]["proc_entry_present"])] += 1
    der["after_run_killpg0_kill0_procpresent_by_arm"] = {"%s|killpg0=%s|kill0=%s|proc_present=%s" % k: v for k, v in kpa.items()}
    # orphan behaviour with the subreaper flag really off
    orph = Counter()
    for r in results:
        if r["case"].startswith("T-04b") and "part2_orphan_behaviour" in r:
            o = r["part2_orphan_behaviour"]
            orph[(r["case"], o["D_ppid"] == 1, o["adopter_comm"], o["adopted_by_supervisor"], o["waitid_by_supervisor"])] += 1
    der["orphan_behaviour_subreaper_off"] = {"%s|ppid_is_1=%s|adopter=%s|adopted_by_supervisor=%s|%s" % k: v for k, v in orph.items()}
    # T-04b part 2 tri-state by arm
    t04 = defaultdict(Counter)
    for r in results:
        if r["case"].startswith("T-04b") and "part2_poll1_D_alive" in r:
            t04[(r["case"], r["arm"])][(r["part2_poll1_D_alive"]["tri"], r["part2_poll2_all_exited"]["tri"])] += 1
    der["t04b_poll1_poll2_tri"] = {"%s/%s" % k: {"%s->%s" % kk: n for kk, n in v.items()} for k, v in t04.items()}
    # zombie dwell: polls in which the oracle saw any ZOMBIE among targets, per arm, over comparable cases
    dwell = defaultdict(list)
    for r in results:
        t = r.get("trace")
        if r["arm"] in ("CA", "CB") and t and r["case"] in ("T-02a", "T-02b", "T-04", "T-05", "T-06", "T-07a", "T-07b"):
            z = sum(1 for p in t["polls"] if any(v == "ZOMBIE" for v in (p["truth_pre"] or {}).values()))
            dwell[(r["case"], r["arm"])].append(z)
    der["zombie_visible_poll_count_mean"] = {"%s/%s" % k: round(sum(v) / len(v), 2) for k, v in sorted(dwell.items())}
    # exit-status integrity
    st_fail = Counter()
    st_tot = Counter()
    for r in results:
        for c in r.get("checks", []):
            if c["name"].startswith("exit_status"):
                st_tot[r["arm"]] += 1
                if not c["ok"]:
                    st_fail[r["arm"]] += 1
    der["exit_status_checks"] = {a: {"total": st_tot[a], "failed": st_fail[a]} for a in ARMS}
    # safety checks
    safety = defaultdict(Counter)
    for r in results:
        for c in r.get("checks", []):
            if c["name"] in ("no_signal_to_non_target", "sentinel_alive_and_untouched", "wait_calls_only_on_own_children", "bystander_still_running",
                             "decoy_still_unreaped_zombie", "no_false_escalation", "no_false_escalation (stable-exited target never escalated)"):
                safety[(r["arm"], c["name"])]["ok" if c["ok"] else "FAILED"] += 1
    der["safety_checks"] = {"%s|%s" % k: dict(v) for k, v in sorted(safety.items())}
    # CA vs CB: any case where verdicts differ
    der["ca_cb_differences"] = [c for c, d in matrix.items() if "CA" in d and "CB" in d and d["CA"]["verdict"] != d["CB"]["verdict"]]
    # T-08b distribution of outcomes vs jitter
    jb = defaultdict(list)
    for a in ARMS:
        for r in runs("T-08b", a):
            jb[a].append((r.get("jitter_s"), r.get("race_outcome")))
    der["t08b_outcomes"] = {a: dict(Counter(o for _, o in v)) for a, v in jb.items()}
    # outside view before T5: does a consumed (CA) vs unconsumed (CB) child still look alive to kill(pid,0)?
    pre5 = defaultdict(Counter)
    for r in results:
        t = r.get("trace")
        if r["arm"] in ("CA", "CB") and t and r["case"] in ("T-02a", "T-02b", "T-03", "T-06", "T-04", "T-07a"):
            for n, o in (t.get("pre_t5_observation") or {}).items():
                pre5[(r["case"], r["arm"], n)][(o["proc_state"], o["kill_pid_0"])] += 1
    der["pre_T5_outside_view"] = {"%s/%s/%s" % k: {"%s|kill0=%s" % kk: n for kk, n in v.items()} for k, v in sorted(pre5.items())}
    # SIGKILL results in the race cases
    sk = defaultdict(Counter)
    for r in results:
        t = r.get("trace")
        if t and r["case"] in ("T-08b", "T-08c") and r["arm"] in ("CA", "CB"):
            for s in t["signals"]:
                if s.get("stage") == "SIGKILL":
                    sk[(r["case"], r["arm"])][s["result"]] += 1
    der["sigkill_result_counts_race_cases"] = {"%s/%s" % k: dict(v) for k, v in sorted(sk.items())}
    esc = defaultdict(Counter)
    for r in results:
        t = r.get("trace")
        if t and r["case"] == "T-08b":
            if t["decision"] == "ESCALATED":
                esc[r["arm"]]["escalated_truth_pre_recheck_running" if any(v == "RUNNING" for v in t["escalation"]["truth_pre_recheck"].values()) else "escalated_target_already_exited_BOUNDARY_OR_FALSE"] += 1
    der["t08b_escalation_truth"] = {a: dict(v) for a, v in esc.items()}
    ad = Counter()
    for r in results:
        if r["case"] in ("T-04", "T-07a", "T-07b") and "D_ppid_after_leader_exit" in r:
            ad[(r["case"], r["D_ppid_after_leader_exit"] == r["supervisor_pid"])] += 1
    der["orphan_adopted_by_supervisor_with_subreaper_on"] = {"%s|adopted=%s" % k: v for k, v in ad.items()}
    der["cleanup_unclean_runs"] = unclean
    der["tool_not_ok_count"] = len(notok)
    der["tool_not_ok_sample"] = notok[:10]
    dp = os.path.join(HERE, "results", "a_predicate_cpu_001_derived.json")
    open(dp, "w").write(json.dumps(der, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n")
    print(json.dumps({"runs": len(results), "totals": der["totals"], "ca_cb_diff": der["ca_cb_differences"],
                      "unclean": len(unclean), "tool_not_ok": len(notok)}, indent=1))
    for c, d in der["matrix_verdicts"].items():
        print("%-9s" % c, " ".join("%s=%s" % (a[:12], d.get(a, "-")) for a in ARMS + ["BENCH"] if a in d))


if __name__ == "__main__":
    main()
