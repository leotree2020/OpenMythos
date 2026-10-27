#!/usr/bin/env python3
"""E1-A runner (F3B-D1-A-CPU-003).  STATUS: WRITTEN, NOT RUN.

  --check    static consistency checks (hashes, pins, recipe/prereg agreement, plan size).  Starts no process.
  --plan     print the frozen trial plan summary.  Starts no process.
  --execute  run something.  REFUSED unless an owner authorization file exists that (a) references the SHA-256 of the frozen
             preregistration AND of the bench code, and (b) explicitly authorizes the requested PHASE and its exact scope:
               --phase bv     only the listed run-level bench validity checks (--bv BV-1,BV-3 ...), each fault-injecting check
                              authorized by id; it runs NO experiment cell;
               --phase cells  only the listed E1-A cells (--only E1A-a:P2 ...), at most the authorized repetitions, the false-reject
                              sweep only if authorized; it runs NO run-level BV check.  Cell results COUNT only if the owner-issued
                              authorization carries a bv_binding (run id, BV authorization id, attestation digest) that is re-derived
                              from the raw records of that earlier BV run (evidence.py); otherwise they are SMOKE: reported, not counted.
             No such file exists at the time of writing.
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
import evidence as EV      # noqa: E402
import scenarios as S      # noqa: E402
import truth as T          # noqa: E402

AUTH_DEFAULT = os.path.join(C.A003_DIR, "AUTHORIZATION_E1A_RUN.json")
PHASE_BV, PHASE_CELLS = "BV-SELFTEST", "E1A-CELLS"
V_RUN_LEVEL_IDS = ("BV-1", "BV-2", "BV-3", "BV-6", "BV-7")   # must equal validity.RUN_LEVEL_IDS (tested)
AUTH_SCHEMA = "e1a-auth-2"


class AuthorizationError(Exception):
    pass


def bench_code_hash():
    """One hash over every bench/*.py (sorted by name): the authorization is bound to the reviewed code revision."""
    h = []
    for f in sorted(os.listdir(C.BENCH_DIR)):
        if f.endswith(".py"):
            h.append("%s:%s" % (f, C.sha256_file(os.path.join(C.BENCH_DIR, f))))
    return C.sha256_bytes("\n".join(h).encode())
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


def load_authorization(path, prereg_sha, code_hash):
    """-> authorization dict, or raises AuthorizationError.  The file is the ONLY source of authority; command-line flags can only
    narrow it."""
    try:
        with open(path) as f:
            a = json.load(f)
    except (OSError, ValueError) as e:
        raise AuthorizationError("no valid authorization file at %s (%r)" % (path, e))
    if a.get("schema") != AUTH_SCHEMA:
        raise AuthorizationError("authorization schema must be %s" % AUTH_SCHEMA)
    if a.get("authorized_by") != "owner" or not a.get("authorization_id"):
        raise AuthorizationError("authorization must have authorized_by=owner and an authorization_id")
    if a.get("prereg_sha256") != prereg_sha:
        raise AuthorizationError("authorization references prereg %s, frozen file is %s" % (a.get("prereg_sha256"), prereg_sha))
    if a.get("bench_code_sha256") != code_hash:
        raise AuthorizationError("authorization is bound to bench code %s, current code is %s" % (a.get("bench_code_sha256"), code_hash))
    if not isinstance(a.get("phases"), dict) or not a["phases"]:
        raise AuthorizationError("authorization lists no phase")
    return a


def build_execution_plan(prereg, auth, phase, bv=None, only=None, reps=None, no_sweep=True, all_cells=False):
    """PURE.  -> {'phase', 'bv_checks': [...], 'trials': [...], 'partial': bool}.  Raises AuthorizationError for anything not
    explicitly authorized.  A cells plan never contains BV checks and a BV plan never contains cells."""
    ph = auth["phases"]
    if phase == "bv":
        grant = ph.get(PHASE_BV)
        if not grant:
            raise AuthorizationError("phase %s is not authorized" % PHASE_BV)
        want = sorted(set(bv or []))
        if not want:
            raise AuthorizationError("--phase bv needs an explicit --bv list (there is no implicit 'all')")
        bad = [x for x in want if x not in V_RUN_LEVEL_IDS]
        if bad:
            raise AuthorizationError("unknown run-level check(s) %s" % bad)
        notgranted = [x for x in want if x not in (grant.get("checks") or [])]
        if notgranted:
            raise AuthorizationError("run-level check(s) %s not authorized" % notgranted)
        if only or reps is not None or all_cells or not no_sweep:
            raise AuthorizationError("--phase bv takes no cell options")
        return {"phase": "bv", "bv_checks": want, "trials": [], "partial": want != sorted(V_RUN_LEVEL_IDS)}
    if phase == "cells":
        grant = ph.get(PHASE_CELLS)
        if not grant:
            raise AuthorizationError("phase %s is not authorized" % PHASE_CELLS)
        if bv:
            raise AuthorizationError("--phase cells takes no --bv option: it never runs run-level checks")
        granted = grant.get("cells")
        max_reps = int(grant.get("max_reps", 0))
        frozen_reps = prereg["repetitions"]["deterministic_per_cell"]
        if reps is None:
            raise AuthorizationError("--phase cells needs an explicit --reps")
        if reps < 1 or reps > max_reps:
            raise AuthorizationError("--reps %d outside the authorized 1..%d" % (reps, max_reps))
        if all_cells:
            if granted != "ALL":
                raise AuthorizationError("ALL cells are not authorized")
            sel = None
        else:
            if not only:
                raise AuthorizationError("--phase cells needs --only SCENARIO:CANDIDATE[,...] (or --all-cells when authorized)")
            sel = {tuple(x.split(":")) for x in only}
            known = {(sc, c) for sc in S.SCENARIO_ORDER for c in S.CANDIDATES}
            if not sel <= known:
                raise AuthorizationError("unknown cell(s) %s" % sorted(sel - known))
            if granted != "ALL":
                not_ok = sorted(f"{a}:{b}" for a, b in sel if f"{a}:{b}" not in (granted or []))
                if not_ok:
                    raise AuthorizationError("cell(s) %s not authorized" % not_ok)
        sweep = not no_sweep
        if sweep and not grant.get("sweep"):
            raise AuthorizationError("the false-reject sweep is not authorized")
        trials = S.plan_trials(prereg, reps=reps, only_cells=sel, only_sweep=sweep)
        partial = bool(sel) or reps != frozen_reps or not sweep
        return {"phase": "cells", "bv_checks": [], "trials": trials, "partial": partial}
    raise AuthorizationError("--phase must be 'bv' or 'cells'")


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


def summarize(prereg, plan, records, validity_ok, aborted, partial, residue=(), counted=True, recovery_open=False):
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
    if recovery_open:
        exp = "BLOCKED - recovery responsibility still open (manual disposition); no cleanup PASS may be inferred"
    elif not plan:
        exp = "NO CELLS RUN (bench-validity phase only)"
    elif not counted:
        exp = "SMOKE - cell results not counted (run-level bench validity not established by an authorized BV run)"
    elif partial:
        exp = "PARTIAL RUN - no experiment verdict"
    else:
        exp = T.experiment_verdict(cand_verdicts, validity_ok and not aborted and not residue, unsafe_any)
    return {"token_scan_unregistered": list(residue), "cells": out_cells, "candidate_verdicts": cand_verdicts, "experiment_verdict": exp, "unsafe_event_any_candidate": unsafe_any,
            "bench_validity_ok": validity_ok, "aborted": aborted, "partial": partial, "cells_counted": counted, "recovery_open_blocks_verdict": bool(recovery_open),
            "note": "Mechanism states and experiment verdicts are separate; P0/P1 FAILs on UNPROVABLE cells are capability findings, not an experiment FAIL. No candidate is selected."}


def may_stop_janitor(cleanup_confirmed, final_residual, residue=(), scan_problems=()):
    """PURE.  The janitor carries the recovery responsibility.  It may be stopped by the runner ONLY when that responsibility is fully
    discharged: cleanup confirmed over the verified run set, nothing left over, the diagnostic scan clean and complete."""
    return bool(cleanup_confirmed) and not final_residual and not residue and not scan_problems


def recovery_state(cleanup_confirmed, final_residual, residue, scan_problems, janitor_started, janitor_exit, janitor_running,
                   janitor_stopped_after_discharge):
    """PURE.  recovery_open is TRUE unless EVERYTHING holds: cleanup confirmed, no residual, clean complete diagnostic scan, a janitor
    that ran, is no longer running and either exited 0 or was stopped by us after the responsibility was discharged.  An abnormal janitor
    exit, an unconfirmed cleanup or a non-empty residual can never yield a closed recovery."""
    discharged = may_stop_janitor(cleanup_confirmed, final_residual, residue, scan_problems)
    janitor_ok = bool(janitor_started) and not janitor_running and (janitor_exit == 0 or bool(janitor_stopped_after_discharge))
    open_ = not (discharged and janitor_ok)
    if not open_:
        label = "CLOSED"
    elif janitor_running:
        label = "BLOCKED: RECOVERY DELEGATED TO THE STILL-RUNNING JANITOR (check janitor_actions.jsonl; manual disposition if it fails)"
    else:
        label = "BLOCKED: MANUAL DISPOSITION REQUIRED"
    return {"recovery_open": open_, "manual_disposition_required": open_ and not janitor_running, "state": label, "discharged": discharged}


def execute(args, prereg, sha, plan, code_hash, counted, provenance, auth, auth_bytes):
    import observer as O
    import trial as TR
    import validity as V
    run_id = args.run_id or time.strftime("e1a_%Y%m%d_%H%M%S")
    if not EV.RUN_ID_RE.match(run_id):
        sys.exit("run id %r is not a plain directory name" % run_id)
    out_dir = os.path.join(C.A003_DIR, "evidence", run_id)
    if os.path.exists(out_dir):
        sys.exit("refusing to reuse existing run directory %s" % out_dir)
    os.makedirs(out_dir)
    with open(os.path.join(out_dir, "authorization_used.json"), "wb") as f:      # verbatim copy of the authorization in force
        f.write(auth_bytes)
    env = environment(sha)
    env.update(partial_run=plan["partial"], phase=plan["phase"], bench_code_sha256=code_hash, cells_counted=counted, run_id=run_id,
               authorization_id=auth["authorization_id"], authorization_sha256=C.sha256_bytes(auth_bytes), bv_provenance=provenance)
    json.dump(env, open(os.path.join(out_dir, "environment.json"), "w"), indent=1, default=str)
    json.dump({"phase": plan["phase"], "bv_checks": plan["bv_checks"], "trials": plan["trials"]}, open(os.path.join(out_dir, "plan.json"), "w"))
    reg_path = os.path.join(out_dir, "registry.jsonl")
    janitor_log = os.path.join(out_dir, "janitor_actions.jsonl")
    obs = O.Observer(reg_path)
    obs.reg.write("RUN_START", run_id=run_id, prereg_sha256=sha, observer_pid=os.getpid(), phase=plan["phase"])
    obs.trial_tag = "RUN"
    signal.signal(signal.SIGTERM, lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    records, aborted, jrec, validity = [], None, None, {}
    pins = pins_from_prereg(prereg)

    def janitor_alive():
        return jrec is not None and jrec.pid is not None and not C.process_is_dead(jrec.pid, jrec.starttime)

    try:
        st = C.read_stat(os.getpid())
        jrec = obs.spawn_direct("janitor", "JANITOR", {"label": "JANITOR", "mode": "none", "children": [], "exit_after_ready": False},
                                TR.make_exec_janitor(reg_path, os.getpid(), st["starttime"], janitor_log))
        if jrec.state != "RELEASED":
            raise TR.RunAbort("janitor not released: %s" % jrec.state)
        if plan["bv_checks"]:
            validity = V.run_all(obs, os.path.join(out_dir, "validity_work"), plan["bv_checks"])
            json.dump({"meta": {"run_id": run_id, "authorization_id": auth["authorization_id"], "prereg_sha256": sha, "bench_code_sha256": code_hash,
                                "checks_run": plan["bv_checks"]}, "results": validity},
                      open(os.path.join(out_dir, "validity.json"), "w"), indent=1, default=str)
            if not all(v["ok"] for v in validity.values()):
                aborted = "bench validity check failed: %s" % [k for k, v in validity.items() if not v["ok"]]
        if plan["trials"] and not aborted:
            with open(os.path.join(out_dir, "trials.jsonl"), "a") as tf:
                for i, item in enumerate(plan["trials"]):
                    if not janitor_alive():                    # an abnormal janitor exit mid-run means the recovery guard is gone
                        raise TR.RunAbort("janitor is no longer running: recovery protection lost before %s" % item["trial_id"])
                    r = TR.run_trial(obs, prereg, item, pins, {"prereg_sha": sha})
                    records.append(r)
                    tf.write(json.dumps(r, sort_keys=True, default=str) + "\n")
                    tf.flush()
                    if i % 50 == 0:
                        print("[%d/%d] %s %s %s -> %s" % (i + 1, len(plan["trials"]), item["trial_id"], item["scenario"], item["candidate"], r["verdict"]), file=sys.stderr)
    except TR.RunAbort as e:
        aborted = "RunAbort: %s" % e
    except KeyboardInterrupt:
        aborted = "interrupted"
    except Exception:
        aborted = "runner exception: " + traceback.format_exc()
    finally:
        # ---- final cleanup over the WHOLE run: intake closed, in-flight tickets revoked, node set re-read every round, run set verified
        jid = {jrec.node_id} if jrec is not None else set()
        cleanup = obs.final_cleanup(jid)
        registered_pids = {r.pid for r in obs.nodes.values() if r.pid is not None}
        residue, scan_problems = T.token_scan(["--run-id " + run_id, "bench/sup_stub.py"], registered_pids, {os.getpid(), os.getppid()})
        # RUN_END says whether cleanup is CONFIRMED.  An inconsistent run set, a residual node, an unregistered token-bearing process or an
        # unreadable /proc during the diagnostic scan all mean "not confirmed": the janitor then keeps working and recovery stays open.
        confirmed = bool(cleanup["cleanup_ok"]) and not residue and not scan_problems
        obs.reg.write("RUN_END", aborted=aborted, cleanup_confirmed=confirmed, residual=cleanup["residual_after_kill"],
                      run_set_consistent=cleanup["run_set"]["consistent"], run_set_problems=cleanup["run_set"]["problems"],
                      token_residue=[x["pid"] for x in residue], token_scan_problems=scan_problems)
        janitor_exit, janitor_running, stopped_after_discharge = None, False, False
        if jrec is not None and jrec.pid is not None:
            obs.trial_tag = "RUN"
            done = obs.wait_for(lambda: C.process_is_dead(jrec.pid, jrec.starttime), 15.0 if confirmed else 90.0)
            if done:
                obs.reap_direct(nodes=[jrec])
                janitor_exit = jrec.exit_status
            else:
                janitor_running = True
        final_residual = obs.residual_detail(obs.run_level_nodes(jid))
        if janitor_running and may_stop_janitor(confirmed, final_residual, residue, scan_problems):
            # only now is the responsibility fully discharged, so only now may a janitor that did not exit on its own be stopped
            obs.kill_registered(only=jid, nodes=[jrec])
            if obs.wait_for(lambda: C.process_is_dead(jrec.pid, jrec.starttime), 3.0):
                obs.reap_direct(nodes=[jrec])
                janitor_exit, janitor_running, stopped_after_discharge = jrec.exit_status, False, True
        rs = recovery_state(confirmed, final_residual, residue, scan_problems, jrec is not None and jrec.pid is not None, janitor_exit,
                            janitor_running, stopped_after_discharge)
        if rs["recovery_open"]:
            json.dump({"state": rs["state"], "run_id": run_id, "final_residual": final_residual, "token_residue": residue,
                       "token_scan_problems": scan_problems, "janitor_exit": janitor_exit, "janitor_still_running": janitor_running,
                       "janitor_log": janitor_log, "registry": reg_path,
                       "instruction": "No component signals a process whose identity is not confirmed.  A person must identify and handle the "
                                      "listed processes; the experiment verdict of this run is BLOCKED."},
                      open(os.path.join(out_dir, "MANUAL_DISPOSITION_REQUIRED.json"), "w"), indent=1, default=str)
    summary = summarize(prereg, plan["trials"], records, bool(validity) and all(v["ok"] for v in validity.values()), aborted,
                        plan["partial"], residue, counted, rs["recovery_open"])
    summary.update(run_id=run_id, phase=plan["phase"], prereg_sha256=sha, bench_code_sha256=code_hash, recorded_trials=len(records),
                   planned_trials=len(plan["trials"]), validity=validity, token_scan_problems=scan_problems, cleanup_confirmed=confirmed,
                   janitor_exit=janitor_exit, janitor_still_running=janitor_running, janitor_stopped_after_discharge=stopped_after_discharge,
                   recovery_open=rs["recovery_open"], recovery_state=rs["state"], manual_disposition_required=rs["manual_disposition_required"],
                   final_residual=final_residual, run_set=cleanup["run_set"], bv_provenance=provenance)
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=1, sort_keys=True, default=str)
    if plan["bv_checks"]:                                          # attestation is computed LAST, from the final raw files
        try:
            EV.build_attestation(out_dir)
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("could not write bv_attestation.json: %r" % (e,), file=sys.stderr)
    print(json.dumps({k: summary[k] for k in ("run_id", "phase", "experiment_verdict", "candidate_verdicts", "aborted", "partial",
                                              "cleanup_confirmed", "recovery_open", "recovery_state", "janitor_exit")}, indent=1, default=str))
    return 0 if not aborted and not rs["recovery_open"] else 3


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--phase", choices=["bv", "cells"], help="REQUIRED with --execute; each phase needs its own authorization")
    ap.add_argument("--auth", default=AUTH_DEFAULT)
    ap.add_argument("--run-id")
    ap.add_argument("--bv", help="phase bv: comma list of run-level checks, e.g. BV-1,BV-3 (no implicit 'all')")
    ap.add_argument("--only", help="phase cells: comma list SCENARIO:CANDIDATE")
    ap.add_argument("--all-cells", action="store_true", help="phase cells: every cell (only if the authorization says ALL)")
    ap.add_argument("--reps", type=int, help="phase cells: repetitions per cell (required; bounded by the authorization)")
    ap.add_argument("--with-sweep", action="store_true", help="phase cells: include the false-reject sweep (only if authorized)")
    args = ap.parse_args(argv)
    prereg, sha = S.load_prereg()
    if args.check:
        bad = static_checks(prereg, sha)
        print(json.dumps({"prereg_sha256": sha, "bench_code_sha256": bench_code_hash(), "problems": bad, "ok": not bad}, indent=1))
        return 0 if not bad else 1
    if args.plan:
        plan = S.plan_trials(prereg)
        print(json.dumps({"prereg_sha256": sha, "trials": len(plan), "cells": len({(t["scenario"], t["candidate"]) for t in plan}),
                          "sweep_trials": sum(1 for t in plan if t["kind"] == "sweep")}, indent=1))
        return 0
    if args.execute:
        code_hash = bench_code_hash()
        try:
            if not args.phase:
                raise AuthorizationError("--execute needs --phase bv|cells")
            auth = load_authorization(args.auth, sha, code_hash)
            plan = build_execution_plan(prereg, auth, args.phase, bv=args.bv.split(",") if args.bv else None,
                                        only=args.only.split(",") if args.only else None, reps=args.reps,
                                        no_sweep=not args.with_sweep, all_cells=args.all_cells)
        except AuthorizationError as e:
            print("REFUSED: %s" % e, file=sys.stderr)
            return 2
        bad = static_checks(prereg, sha)
        if bad:
            print("REFUSED: static checks failed: %s" % bad, file=sys.stderr)
            return 2
        counted, provenance = EV.evaluate_counting(auth, bool(plan["trials"]), sha, code_hash)
        with open(args.auth, "rb") as f:
            auth_bytes = f.read()
        if json.loads(auth_bytes.decode("utf-8")) != auth:
            print("REFUSED: the authorization file changed while it was being read", file=sys.stderr)
            return 2
        return execute(args, prereg, sha, plan, code_hash, counted, provenance, auth, auth_bytes)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
