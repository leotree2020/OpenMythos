#!/usr/bin/env python3
"""Merge CPU-002 parts into results/a_predicate_002_results.json.gz and derive the tables used by the report."""
import glob
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"


def load(p):
    return json.load(gzip.open(p, "rt")) if p.endswith(".gz") else json.load(open(p))


def main():
    parts = sorted(glob.glob(os.path.join(HERE, "results", "parts", "E*.json")) + glob.glob(os.path.join(HERE, "results", "parts", "E*.json.gz")))
    results, envs, errors, unclean, notok = [], [], [], [], []
    for p in parts:
        d = load(p)
        results += d["results"]
        e = d["environment"]
        envs.append({"part": os.path.basename(p), "git_commit": e["git_commit"], "git_status_short": e["git_status_short"], "kernel": e["kernel"]})
        if d.get("run_error"):
            errors.append((os.path.basename(p), d["run_error"]))
        unclean += d["cleanup_unclean_runs"]
        notok += d["tool_not_ok_runs"]
    cases = []
    for r in results:
        if r["case"] not in cases:
            cases.append(r["case"])
    matrix = {}
    for c in cases:
        for a in sorted({r["arm"] for r in results if r["case"] == c}):
            rs = [r for r in results if r["case"] == c and r["arm"] == a]
            n = Counter(r["status"] for r in rs)
            fails = Counter(f for r in rs for f in r.get("failed_checks", []))
            matrix.setdefault(c, {})[a] = {"counts": {s: n.get(s, 0) for s in (PASS, FAIL, BLOCKED)}, "verdict": FAIL if n.get(FAIL) else BLOCKED if n.get(BLOCKED) else PASS,
                                           "runs": len(rs), "failed_checks": dict(fails), "blocked": sorted({(r.get("blocked_reason") or "")[:140] for r in rs if r["status"] == BLOCKED})}
    out = {"experiment": "F3B-D1-A-CPU-002", "environment_first_part": load(parts[0])["environment"], "parts": envs, "results": results, "matrix": matrix,
           "run_errors": errors, "cleanup_unclean_runs": unclean, "tool_not_ok_runs": notok}
    with gzip.GzipFile(os.path.join(HERE, "results", "a_predicate_002_results.json.gz"), "wb", mtime=0) as f:
        f.write((json.dumps(out, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n").encode("ascii"))

    def runs(c, a):
        return [r for r in results if r["case"] == c and r["arm"] == a]

    der = {"runs_total": len(results), "matrix": {c: {a: {"verdict": v["verdict"], "counts": v["counts"], "failed_checks": v["failed_checks"], "blocked": v["blocked"]} for a, v in d.items()} for c, d in matrix.items()}}
    der["totals_by_arm"] = {a: dict(Counter(r["status"] for r in results if r["arm"] == a)) for a in sorted({r["arm"] for r in results})}
    # E1
    e1 = {}
    for c in ("E1-P2", "E1-A2", "E1-A3"):
        for a in ("CA", "CB", "CA-S", "CB-S"):
            e1["%s/%s outcome" % (c, a)] = dict(Counter(r.get("outcome") for r in runs(c, a)))
    for c in ("E1-X1a", "E1-X1z", "E1-X2", "E1-S2"):
        for a in ("CA", "CB", "CA-S", "CB-S"):
            rs = runs(c, a)
            e1["%s/%s non-target attributed as" % (c, a)] = dict(Counter(tuple(r.get("attributed_X") or r.get("X_attribution") or []) for r in rs))
            e1["%s/%s signals delivered to non-target (runs)" % (c, a)] = sum(1 for r in rs if any(ch["name"].startswith("K1") and not ch["ok"] for ch in r.get("checks", [])))
            e1["%s/%s non-target reaped or killed (runs)" % (c, a)] = sum(1 for r in rs if any(ch["name"].startswith(("K_non_target_final_state", "K2")) and not ch["ok"] for ch in r.get("checks", [])))
    e1["E1-S1 setpgid(unexec child -> stage group)"] = dict(Counter(r.get("setpgid_unexec_child_into_stage_group") for r in runs("E1-S1", "BENCH")))
    e1["E1-S1 setpgid(exec'd child) observation only"] = dict(Counter(r.get("v1_method_setpgid_on_exec_child_observation_only") for r in runs("E1-S1", "BENCH")))
    e1["E1-S2 preflight (strict)"] = dict(Counter((r.get("preflight") or {}).get("code") for a in ("CA-S", "CB-S") for r in runs("E1-S2", a)))
    e1["E1-P3 D attribution"] = {a: dict(Counter(tuple(r.get("D_attribution") or []) for r in runs("E1-P3", a))) for a in ("CA", "CB", "CA-S", "CB-S")}
    der["E1"] = e1
    # E2
    e2 = {}
    for c in ("E2-01", "E2-02", "E2-03"):
        for a in ("CA", "CA-P"):
            rs = runs(c, a)
            e2["%s/%s" % (c, a)] = {"ca_record": dict(Counter(json.dumps({k: v for k, v in (r.get("ca_record") or {}).items() if k != "raw"}, sort_keys=True) for r in rs)),
                                    "popen_poll": dict(Counter(r.get("popen_poll") for r in rs)), "popen_wait": dict(Counter(r.get("popen_wait") for r in rs)),
                                    "kernel_second_status_copy": dict(Counter(r.get("kernel_second_status_copy") for r in rs))}
    for a in ("CA", "CA-P"):
        rs = runs("E2-05", a)
        e2["E2-05/%s race outcomes" % a] = dict(Counter(r.get("race_outcome") for r in rs))
        e2["E2-05/%s popen rc" % a] = dict(Counter(r.get("popen_rc") for r in rs))
        e2["E2-05/%s arm tri" % a] = dict(Counter(r.get("arm_tri") for r in rs))
    for a in ("CA", "CA-P", "CB"):
        e2["E2-04/%s" % a] = {"arm_tri": dict(Counter(r.get("arm_tri") for r in runs("E2-04", a))), "popen_wait": dict(Counter(r.get("popen_wait") for r in runs("E2-04", a)))}
    e2["E2-06 os.kill calls after arm reaped"] = dict(Counter(len(r.get("os_kill_calls", [])) for r in runs("E2-06", "CA")))
    e2["E2-06 popen returncode after arm reaped"] = dict(Counter(r.get("popen_returncode") for r in runs("E2-06", "CA")))
    e2["E2-08a CB t5 then Popen.poll"] = dict(Counter(r.get("popen_poll") for r in runs("E2-08a", "CB")))
    e2["E2-08b CB after Popen consumed"] = dict(Counter(r.get("cb_tri_after") for r in runs("E2-08b", "CB")))
    e2["E2-00 control popen_wait"] = {c: dict(Counter(r.get("popen_wait") for r in runs(c, "POPEN"))) for c in ("E2-00a", "E2-00b", "E2-00c")}
    der["E2"] = e2
    # E3
    e3 = {}
    for a in ("CB", "CA"):
        rs = runs("E3-01", a)
        e3["E3-01/%s zombie samples / total" % a] = [sum(r["zombie_samples"] for r in rs), sum(r["total_samples"] for r in rs)]
        e3["E3-01/%s kill(pid,0)=success samples" % a] = sum(r["kill0_success_samples"] for r in rs)
    rs = runs("E3-01b", "BENCH")
    e3["E3-01b"] = {"zombies_counted": [r["zombies_counted"] for r in rs], "pid_max": rs[0]["pid_max"] if rs else None, "RLIMIT_NPROC": rs[0]["RLIMIT_NPROC"] if rs else None,
                    "meminfo_kB_first_run": rs[0]["meminfo_kB_before_after"] if rs else None}
    for c in ("E3-02a", "E3-02b"):
        for a in ("CB", "CA"):
            rs = runs(c, a)
            e3["%s/%s gone-after-death seconds" % (c, a)] = [r.get("seconds_after_supervisor_death_until_node_gone") for r in rs]
            e3["%s/%s adopted_by_outer (per node)" % (c, a)] = dict(Counter((n, o.get("adopted_by_outer")) for r in rs for n, o in (r.get("after_supervisor_death") or {}).items()))
            e3["%s/%s status readable by outer before reap" % (c, a)] = dict(Counter((n, json.dumps(o.get("status_readable_before_reap"), sort_keys=True)) for r in rs for n, o in (r.get("after_supervisor_death") or {}).items() if n in ("R", "E", "Y")))
            e3["%s/%s final states" % (c, a)] = dict(Counter(json.dumps(r.get("final_states"), sort_keys=True) for r in rs))
    for c, a in (("E3-03", "CB-nofinally"), ("E3-03", "CA-nofinally"), ("E3-03p", "CB-finally")):
        e3["%s/%s state after exception path" % (c, a)] = dict(Counter(r.get("state_after_exception_path") for r in runs(c, a)))
    der["E3"] = e3
    der["cleanup_unclean_runs"] = unclean
    der["tool_not_ok"] = notok[:10]
    der["tool_not_ok_count"] = len(notok)
    der["run_errors"] = errors
    def strkeys(o):
        if isinstance(o, dict):
            return {(k if isinstance(k, str) else str(k)): strkeys(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [strkeys(x) for x in o]
        return o
    der = strkeys(der)
    with open(os.path.join(HERE, "results", "a_predicate_002_derived.json"), "w") as f:
        f.write(json.dumps(der, indent=1, sort_keys=True, ensure_ascii=True, default=str) + "\n")
    print(json.dumps({"runs": len(results), "totals": der["totals_by_arm"], "unclean": len(unclean), "tool_not_ok": len(notok), "run_errors": len(errors)}, indent=1))
    for c, d in der["matrix"].items():
        print("%-8s" % c, "  ".join("%s=%s(%d/%d/%d)" % (a, v["verdict"], v["counts"]["PASS"], v["counts"]["FAIL"], v["counts"]["BLOCKED"]) for a, v in d.items()))


if __name__ == "__main__":
    main()
