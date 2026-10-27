#!/usr/bin/env python3
"""E1-A runner (F3B-D1-A-CPU-003).  STATUS: WRITTEN, NOT RUN.

  --check    static consistency checks (hashes, pins, recipe/prereg agreement, plan size).  Starts no process.
  --plan     print the frozen trial plan summary.  Starts no process.
  --execute  run the experiment.  REFUSED unless an owner authorization file referencing the SHA-256 of the frozen preregistration
             exists (default: AUTHORIZATION_E1A_RUN.json next to this bench).  No such file exists at the time of writing.
"""
import argparse
import json
import os
import platform
import signal
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import candidates as K     # noqa: E402
import common as C         # noqa: E402
import scenarios as S      # noqa: E402
import truth as T          # noqa: E402

AUTH_DEFAULT = os.path.join(C.A003_DIR, "AUTHORIZATION_E1A_RUN.json")
FROZEN_REFS = {
    "R3 approved candidate": "research/mini_mythos/docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md",
    "R3 owner decision": "research/mini_mythos/docs/F3B_D1_R3_OWNER_DECISION_20261026.md",
    "R3 spec freeze record": "research/mini_mythos/docs/F3B_D1_R3_SPEC_FREEZE_RECORD_20261026.md",
    "design errata 001": "research/mini_mythos/docs/F3B_D1_A_CPU_003_DESIGN_ERRATA_001_20261027.md",
    "design errata 002": "research/mini_mythos/docs/F3B_D1_A_CPU_003_DESIGN_ERRATA_002_20261027.md",
    "design plan": "research/mini_mythos/docs/F3B_D1_A_CPU_003_DESIGN_PLAN_20261027.md",
}


def pins_from_prereg(prereg):
    out = {}
    for name, p in prereg["candidate_code_pins"].items():
        if isinstance(p, dict) and "path" in p:
            out[name.split(" ")[0]] = {"path": os.path.join(C.REPO_ROOT, p["path"]), "sha256": p["sha256"]}
    return out


def static_checks(prereg, sha):
    """-> list of problems (empty = consistent).  Reads files only."""
    bad = []
    for name, rel in FROZEN_REFS.items():
        if C.sha256_file(os.path.join(C.REPO_ROOT, rel)) != prereg["frozen_reference_hashes"][name]:
            bad.append("frozen reference changed: %s" % name)
    for name, p in pins_from_prereg(prereg).items():
        if C.sha256_file(p["path"]) != p["sha256"]:
            bad.append("candidate code pin mismatch: %s" % name)
    if sorted(S.RECIPES) != sorted(prereg["scenarios"]) or sorted(S.SCENARIO_ORDER) != sorted(prereg["scenarios"]):
        bad.append("recipes/scenario order do not match the preregistration")
    for scn, recipe in S.RECIPES.items():
        if "root" not in S.all_labels(recipe):
            bad.append("%s has no node labelled root" % scn)
        kind = prereg["scenarios"][scn]["evidence_kind"]
        if (kind == "SIMULATED") != bool(recipe.get("injection")):
            bad.append("%s: evidence_kind %s vs injection %r" % (scn, kind, recipe.get("injection")))
    if K.load_checks() != prereg["s0_checks"]:
        bad.append("candidates.load_checks() differs from the preregistration")
    trials = S.plan_trials(prereg)
    if len(trials) != prereg["repetitions"]["planned_trials"]["total"]:
        bad.append("plan size %d != frozen %d" % (len(trials), prereg["repetitions"]["planned_trials"]["total"]))
    if prereg["global_parameters"]["primary_python"] != "%d.%d.%d" % sys.version_info[:3]:
        bad.append("python %s != frozen primary %s" % (platform.python_version(), prereg["global_parameters"]["primary_python"]))
    return bad


def check_authorization(path, prereg_sha):
    try:
        with open(path) as f:
            a = json.load(f)
    except (OSError, ValueError) as e:
        return "no valid authorization file at %s (%r)" % (path, e)
    if a.get("prereg_sha256") != prereg_sha:
        return "authorization references prereg %s, frozen file is %s" % (a.get("prereg_sha256"), prereg_sha)
    if a.get("authorized_by") != "owner" or "E1-A" not in str(a.get("scope", "")) or not a.get("authorization_id"):
        return "authorization file incomplete (need authorized_by=owner, scope containing E1-A, authorization_id)"
    return None


def git_head():
    try:
        gd = os.path.join(C.REPO_ROOT, ".git")
        head = open(os.path.join(gd, "HEAD")).read().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            p = os.path.join(gd, ref)
            if os.path.exists(p):
                return open(p).read().strip()
            for line in open(os.path.join(gd, "packed-refs")):
                if line.strip().endswith(" " + ref):
                    return line.split()[0]
            return "UNKNOWN"
        return head
    except OSError:
        return "UNKNOWN"


def environment(prereg_sha):
    u = os.uname()
    return {"python": platform.python_version(), "executable": sys.executable, "kernel": u.release, "machine": u.machine, "uid": os.getuid(),
            "cwd": os.getcwd(), "git_head": git_head(), "git_status": "recorded by the wrapper script (see git_status_*.txt in the run directory)",
            "prereg_sha256": prereg_sha, "pidfd_open": hasattr(os, "pidfd_open"), "pidfd_send_signal": hasattr(signal, "pidfd_send_signal"),
            "send_fds": hasattr(__import__("socket"), "send_fds"), "waitid": hasattr(os, "waitid"), "start_wall": C.wall()}


def summarize(prereg, plan, records, validity_ok, aborted, partial, residue=()):
    cells = {}
    for it in plan:
        key = (it["kind"], it["scenario"], it["candidate"], it["launch"] if it["kind"] == "sweep" else "L1")
        cells.setdefault(key, {"planned": 0, "verdicts": []})["planned"] += 1
    unsafe_any = False
    for r in records:
        it = r["trial"]
        key = (it["kind"], it["scenario"], it["candidate"], it["launch"] if it["kind"] == "sweep" else "L1")
        cells[key]["verdicts"].append(r["verdict"])
        if any(str(x).startswith("UNSAFE_EVENT") for x in r["judgement"]["reasons"]):
            unsafe_any = True
    out_cells, per_cand = {}, {}
    maxb = prereg["global_parameters"]["bench_blocked_fraction_max_per_cell"]
    for key, c in sorted(cells.items()):
        v, note = T.cell_verdict(c["verdicts"], c["planned"], maxb)
        out_cells["|".join(key)] = {"verdict": v, "note": note, "planned": c["planned"], "recorded": len(c["verdicts"]),
                                    "class": prereg["classification"][key[1]][key[2]]["class"]}
        per_cand.setdefault(key[2], []).append(v)
    cand_verdicts = {c: T.candidate_verdict(vs) for c, vs in per_cand.items()}
    exp = "PARTIAL RUN - no experiment verdict" if partial else T.experiment_verdict(cand_verdicts, validity_ok and not aborted and not residue, unsafe_any)
    return {"token_scan_unregistered": list(residue), "cells": out_cells, "candidate_verdicts": cand_verdicts, "experiment_verdict": exp, "unsafe_event_any_candidate": unsafe_any,
            "bench_validity_ok": validity_ok, "aborted": aborted, "partial": partial,
            "note": "Mechanism states and experiment verdicts are separate; P0/P1 FAILs on UNPROVABLE cells are capability findings, not an experiment FAIL. No candidate is selected."}


def execute(args, prereg, sha):
    import observer as O
    import trial as TR
    import validity as V
    run_id = args.run_id or time.strftime("e1a_%Y%m%d_%H%M%S")
    out_dir = os.path.join(C.A003_DIR, "evidence", run_id)
    if os.path.exists(out_dir):
        sys.exit("refusing to reuse existing run directory %s" % out_dir)
    os.makedirs(out_dir)
    only = None
    if args.only:
        only = {tuple(x.split(":")) for x in args.only.split(",")}
    reps = args.reps
    frozen_reps = prereg["repetitions"]["deterministic_per_cell"]
    partial = bool(only) or (reps is not None and reps != frozen_reps) or args.no_sweep
    plan = S.plan_trials(prereg, reps=reps, only_cells=only, only_sweep=not args.no_sweep)
    env = environment(sha)
    env["partial_run"] = partial
    json.dump(env, open(os.path.join(out_dir, "environment.json"), "w"), indent=1)
    json.dump([{k: v for k, v in t.items()} for t in plan], open(os.path.join(out_dir, "plan.json"), "w"))
    reg_path = os.path.join(out_dir, "registry.jsonl")
    obs = O.Observer(reg_path)
    obs.reg.write("RUN_START", run_id=run_id, prereg_sha256=sha, observer_pid=os.getpid())
    obs.trial_tag = "RUN"
    signal.signal(signal.SIGTERM, lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    records, aborted, jrec, validity = [], None, None, {}
    pins = pins_from_prereg(prereg)
    try:
        st = C.read_stat(os.getpid())
        jrec = obs.spawn_direct("janitor", "JANITOR", {"label": "JANITOR", "mode": "none", "children": [], "exit_after_ready": False},
                                TR.make_exec_janitor(reg_path, os.getpid(), st["starttime"], os.path.join(out_dir, "janitor_actions.jsonl")))
        if jrec.state != "RELEASED":
            raise TR.RunAbort("janitor not released: %s" % jrec.state)
        validity = V.run_all(obs, os.path.join(out_dir, "validity_work"))
        json.dump(validity, open(os.path.join(out_dir, "validity.json"), "w"), indent=1, default=str)
        validity_ok = all(v["ok"] for v in validity.values())
        if not validity_ok:
            aborted = "bench validity check failed: %s" % [k for k, v in validity.items() if not v["ok"]]
        else:
            with open(os.path.join(out_dir, "trials.jsonl"), "a") as tf:
                for i, item in enumerate(plan):
                    r = TR.run_trial(obs, prereg, item, pins, {"prereg_sha": sha})
                    records.append(r)
                    tf.write(json.dumps(r, sort_keys=True, default=str) + "\n")
                    tf.flush()
                    if i % 50 == 0:
                        print("[%d/%d] %s %s %s -> %s" % (i + 1, len(plan), item["trial_id"], item["scenario"], item["candidate"], r["verdict"]), file=sys.stderr)
    except TR.RunAbort as e:
        aborted = "RunAbort: %s" % e
    except KeyboardInterrupt:
        aborted = "interrupted"
    except Exception:
        aborted = "runner exception: " + traceback.format_exc()
    finally:
        if obs.trial_tag not in (None, "RUN"):
            obs.finish_trial_cleanup()
        obs.reg.write("RUN_END", aborted=aborted)
        if jrec is not None and jrec.pid is not None:
            obs.trial_tag = "RUN"
            obs.wait_for(lambda: C.process_is_dead(jrec.pid, jrec.starttime), 5.0)
            if not C.process_is_dead(jrec.pid, jrec.starttime):
                obs.kill_registered(only={jrec.node_id})
            obs.wait_for(lambda: C.process_is_dead(jrec.pid, jrec.starttime), 3.0)
            obs.reap_direct()
    registered_pids = {r.pid for r in obs.nodes.values() if r.pid is not None}
    residue, scan_problems = T.token_scan(["--run-id " + run_id, "bench/sup_stub.py"], registered_pids, {os.getpid(), os.getppid()})
    summary = summarize(prereg, plan, records, all(v["ok"] for v in validity.values()) if validity else False, aborted, partial, residue)
    summary["token_scan_problems"] = scan_problems
    summary.update(run_id=run_id, prereg_sha256=sha, recorded_trials=len(records), planned_trials=len(plan))
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({k: summary[k] for k in ("run_id", "experiment_verdict", "candidate_verdicts", "aborted", "partial")}, indent=1))
    return 0 if not aborted else 3


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--auth", default=AUTH_DEFAULT)
    ap.add_argument("--run-id")
    ap.add_argument("--only", help="comma list SCENARIO:CANDIDATE (makes the run PARTIAL)")
    ap.add_argument("--reps", type=int, help="override deterministic repetitions (makes the run PARTIAL)")
    ap.add_argument("--no-sweep", action="store_true", help="skip the false-reject sweep (makes the run PARTIAL)")
    args = ap.parse_args(argv)
    prereg, sha = S.load_prereg()
    if args.check:
        bad = static_checks(prereg, sha)
        print(json.dumps({"prereg_sha256": sha, "problems": bad, "ok": not bad}, indent=1))
        return 0 if not bad else 1
    if args.plan:
        plan = S.plan_trials(prereg)
        print(json.dumps({"prereg_sha256": sha, "trials": len(plan), "cells": len({(t["scenario"], t["candidate"]) for t in plan}),
                          "sweep_trials": sum(1 for t in plan if t["kind"] == "sweep")}, indent=1))
        return 0
    if args.execute:
        why = check_authorization(args.auth, sha)
        if why:
            print("REFUSED: " + why, file=sys.stderr)
            return 2
        bad = static_checks(prereg, sha)
        if bad:
            print("REFUSED: static checks failed: %s" % bad, file=sys.stderr)
            return 2
        return execute(args, prereg, sha)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
