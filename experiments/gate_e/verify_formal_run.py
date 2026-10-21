#!/usr/bin/env python3
"""
Integrity verification of the finished formal E1 run (PREREGISTRATION 8,
12.4, 12.8). Written after the launcher reported DONE; not part of the
frozen code tree, and it checks that none of the frozen files changed.
Reads only the run records, the result and judgment JSON files, the local
checkpoints and a fresh LFS retrieval; never the test_heldout set itself.

    1  run freeze = approved baseline v2; the frozen code files unchanged
    2  checkpoints: 16 archived runs, 280 states; every local file matches
       its file sha256 and parameter hash; the 6 rebuilt initializations
       match their parameter hash; budget_a step-3000 references match
    3  LFS: all published checkpoints retrieved into a fresh directory, both
       hashes verified (--skip-lfs leaves this out)
    4  results: 280 files, each equal to its ledger entry and valid under the
       launcher's own validate_result (M0, M3 controls, M5 split check,
       parameter hash, frozen workload); the quarantined result equals the
       re-diagnosed one without timing fields
    5  judgments: 10, each equal to its ledger entry, one attempt, test_heldout
       at step 12000, valid under validate_judgment
    6  events.json is reproduced exactly by a fresh e_events.py run
    7  budget: cumulative diagnostic time under the cap, never reset
    8  research branch: no checkpoint tracked or committed; code files that
       name test_heldout
Writes validation/formal_integrity.json; exits non-zero if any check fails.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import rebuild_init, param_hash  # noqa: E402
from e_storage import ARTIFACTS_URL, ckpt_param_hash, research_branch_has_no_checkpoints, retrieve_and_verify  # noqa: E402
from run_gate_e import (APPROVED, ROOT, WORKLOAD_FILE, code_tree, result_digest, sha256_file, state_list,  # noqa: E402
                        validate_judgment, validate_result)

def load(name):
    return json.load(open(os.path.join(HERE, name)))


def check_freeze():
    freeze, wl = load("run_freeze.json"), load(WORKLOAD_FILE)
    keys = ("code_tree_sha256", "preregistration_sha256", "sets_manifest_sha256", "timing_json_sha256")
    _, now = code_tree()
    frozen = freeze["code_files"]
    changed = sorted(f for f in frozen if frozen[f] != now.get(f))  # modified or deleted; additions listed apart
    prereg_now = sha256_file(os.path.join(HERE, "PREREGISTRATION.md"))
    return {"run_freeze_equals_baseline": {k: freeze[k] == wl["basis"][k] for k in keys},
            "workload_as_approved": wl["frozen_workload"] == APPROVED["frozen_workload"],
            "frozen_code_files": len(frozen), "frozen_code_files_changed": changed,
            "files_added_after_the_run": sorted(set(now) - set(frozen)),
            "preregistration_unchanged": prereg_now == freeze["preregistration_sha256"],
            "pass": all(freeze[k] == wl["basis"][k] for k in keys) and not changed
            and prereg_now == freeze["preregistration_sha256"]}


def check_checkpoints(m):
    bad, n_file, n_init, n_ref = [], 0, 0, 0
    for st in state_list():
        e = m["states"].get(st)
        if e is None:
            bad.append(f"{st}: no manifest entry")
            continue
        arm, K = st.split("_")[1], int(st[1])
        if e.get("source") == "rebuilt initialization":
            seed = int(st.split("_s")[1].split("_")[0])
            if param_hash(rebuild_init(arm, K, seed)) != e["param_sha256"]:
                bad.append(f"{st}: rebuilt initialization parameter hash")
            n_init += 1
            continue
        local = e.get("local")
        if not (local and os.path.exists(local)):
            bad.append(f"{st}: local file missing")
            continue
        if sha256_file(local) != e["sha256"]:
            bad.append(f"{st}: file sha256")
        elif ckpt_param_hash(local, arm, K) != e["param_sha256"]:
            bad.append(f"{st}: parameter hash")
        n_file += 1
        n_ref += str(e.get("source", "")).startswith("archived budget_a")
    return {"archived_runs": len(m["archived_runs"]), "states": len(m["states"]), "local_files_checked": n_file,
            "budget_a_references": n_ref, "rebuilt_initializations": n_init, "failures": bad,
            "pass": not bad and len(m["archived_runs"]) == 16 and len(m["states"]) == 280}


def check_lfs(m, scratch):
    ents = [e for e in m["states"].values() if e.get("published")]
    fresh = os.path.join(scratch, "lfs_verify")
    ver = retrieve_and_verify(ents, ARTIFACTS_URL, fresh)
    bad = [k for k, v in ver.items() if not (v["file_sha256"] and v["param_sha256"])]
    shutil.rmtree(fresh, ignore_errors=True)
    return {"published": len(ents), "verified": len(ver) - len(bad), "failures": bad,
            "pass": not bad and len(ver) == len(ents) == 268}


def check_results(m):
    led, wl = load("results_ledger.json"), load(WORKLOAD_FILE)["frozen_workload"]
    bad = []
    for st in state_list():
        path = os.path.join(HERE, "results", f"{st}.json")
        if st not in led or not os.path.exists(path):
            bad.append(f"{st}: missing")
            continue
        if sha256_file(path) != led[st]["sha256"]:
            bad.append(f"{st}: differs from its ledger entry")
        why = validate_result(path, st, m, wl)
        if why:
            bad.append(f"{st}: {why}")
    quarantined = []
    for q in sorted(glob.glob(os.path.join(HERE, "quarantine", "*", "*.json"))):
        st = os.path.basename(q)[:-5]
        kept = os.path.join(HERE, "results", os.path.basename(q))
        quarantined.append({"file": os.path.relpath(q, HERE),
                            "equals_rediagnosed_without_timing": result_digest(q) == result_digest(kept),
                            "ledger_digest_equal": led.get(st, {}).get("digest") == result_digest(q)})
    ok = not bad and len(led) == 280 and all(x["equals_rediagnosed_without_timing"] for x in quarantined)
    return {"ledger_entries": len(led), "failures": bad, "quarantined": quarantined, "pass": ok}


def check_judgments():
    led = load("judgments_ledger.json")
    rows, bad = {}, []
    for name, v in sorted(led.items()):
        _, arm, s = name.split("_")
        path = os.path.join(HERE, "judgments", f"K2_{arm}_{s}.json")
        j = json.load(open(path))
        why = validate_judgment(path, name)
        ok = (sha256_file(path) == v.get("sha256") and v.get("attempts") == 1 and not why
              and j.get("set") == "test_heldout" and j.get("step") == 12000)
        rows[name] = {"sha256_equals_ledger": sha256_file(path) == v.get("sha256"), "attempts": v.get("attempts"),
                      "set": j.get("set"), "step": j.get("step"), "valid": why is None}
        if not ok:
            bad.append(name)
    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(HERE, "judgments", "*")))
    return {"judgments": rows, "files": files, "failures": bad,
            "pass": not bad and len(led) == 10 and len(files) == 10}


def check_events(scratch):
    out = os.path.join(scratch, "events_again.json")
    rc = subprocess.run(["python", os.path.join(HERE, "e_events.py"), "--results", os.path.join(HERE, "results"),
                         "--runs", os.path.join(HERE, "runs"), "--out", out],
                        cwd=os.path.abspath(ROOT), capture_output=True, text=True).returncode
    same = rc == 0 and json.load(open(out)) == load("events.json")
    return {"exit": rc, "reproduced_exactly": same, "pass": same}


def check_budget():
    b = load("budget_ledger.json")
    per = [x["diag_seconds"] for x in b["launches"]]
    return {"diag_seconds": b["diag_seconds"], "diag_hours": b["diag_seconds"] / 3600, "cap_hours": b["cap_seconds"] / 3600,
            "launches": [{"started_utc": x["started_utc"], "resume": x["resume"], "diag_seconds": x["diag_seconds"]}
                         for x in b["launches"]],
            "cumulative_equals_sum_of_launches": abs(sum(per) - b["diag_seconds"]) < 1e-6,
            "pass": b["diag_seconds"] < b["cap_seconds"] and abs(sum(per) - b["diag_seconds"]) < 1e-6}


def check_branch():
    r = research_branch_has_no_checkpoints(os.path.abspath(ROOT))
    names = subprocess.run(["git", "grep", "-l", "test_heldout", "--", "experiments/gate_e/*.py"],
                           cwd=os.path.abspath(ROOT), capture_output=True, text=True).stdout.split()
    return {**r, "code_files_naming_test_heldout": names}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-lfs", action="store_true")
    args = ap.parse_args()
    scratch = tempfile.mkdtemp(prefix="gate_e_verify_")
    m = load("checkpoints_manifest.json")
    out = {"freeze": check_freeze(), "checkpoints": check_checkpoints(m)}
    out["lfs"] = {"skipped": True, "pass": True} if args.skip_lfs else check_lfs(m, scratch)
    out.update(results=check_results(m), judgments=check_judgments(), events=check_events(scratch),
               budget=check_budget(), research_branch=check_branch())
    shutil.rmtree(scratch, ignore_errors=True)
    out["pass"] = all(v.get("pass") for v in out.values() if isinstance(v, dict))
    with open(os.path.join(HERE, "validation", "formal_integrity.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: (v.get("pass") if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
