"""Fail-closed janitor.  Exec'd as `python -I -S -B janitor.py REG OBSERVER_PID OBSERVER_STARTTIME LOG` by the observer, or called
as library functions from the validity checks.  It acts ONLY on nodes that have an INTENT record AND a complete REGISTERED record,
re-opens a pidfd first and compares the live starttime with the registered one, and refuses to signal when identity cannot be
confirmed.  It never matches names or command lines, never signals process groups.

Responsibility rules (STATIC-FIX-001):
  * ABORTED does not end responsibility: only a DEAD record (written after the observer CONFIRMED death) does;
  * a node that was forked but never identity-registered is reported as UNRESOLVED while its process may still exist (never signalled);
  * RUN_END carries `cleanup_confirmed`.  True is trusted only after a read-only re-verification; False / missing means the run
    ended with recovery still owed, so the janitor works until cleanup is confirmed and exits non-zero if it cannot confirm it;
  * (STATIC-FIX-002-B) the REG file's own integrity is assessed SEPARATELY from the cleanup state: a missing / unreadable file, a torn
    tail, corrupt lines, a sequence gap, orphan or malformed critical records mean the janitor cannot know that it sees every node.
    It then NEVER exits 0 (EXIT_REG_INTEGRITY / EXIT_BOTH).  It still signals only processes covered by a COMPLETE identity-verified
    record -- anything it cannot identify is never signalled.
WRITTEN, NOT RUN."""
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C            # noqa: E402
import registry as R          # noqa: E402

EXIT_CLEAN = 0
EXIT_IDENTITY = 2
EXIT_INCOMPLETE = 4           # cleanup could not be confirmed: recovery responsibility is STILL OPEN
EXIT_REG_INTEGRITY = 5        # the registration file could not be shown to be complete: recovery responsibility is STILL OPEN
EXIT_BOTH = 6                 # both of the above
CLEANUP_ATTEMPTS = 15
CLEANUP_INTERVAL = 1.0


def _default_signal(handle, sig):
    return handle.send(sig)


def run_cleanup(reg_path, signal_fn=_default_signal, log=None, skip_pids=None):
    """One pass over the REG file.  -> list of per-target result dicts (also appended to `log` if given).
    The janitor never signals itself."""
    return run_cleanup_full(reg_path, signal_fn, log, skip_pids)["targets"]


def run_cleanup_full(reg_path, signal_fn=_default_signal, log=None, skip_pids=None):
    skip = {os.getpid()} if skip_pids is None else set(skip_pids)
    records, info = R.parse_reg(reg_path)
    results = []
    for t in R.cleanup_targets(records):
        if t["pid"] in skip:
            continue
        res = {"node_id": t["node_id"], "pid": t["pid"], "starttime": t["starttime"]}
        h = None
        try:
            h = C.PidfdHandle(t["pid"], t["starttime"])
            res["result"] = signal_fn(h, signal.SIGKILL)
        except ProcessLookupError:
            res["result"] = "gone"
        except C.AlreadyExited:
            res["result"] = "gone"
        except C.IdentityError as e:
            res["result"] = "refused_identity_mismatch"
            res["detail"] = str(e)
        except C.ProcUnreadable as e:
            res["result"] = "refused_proc_unreadable"
            res["detail"] = str(e)
        except OSError as e:
            res["result"] = "refused_pidfd_unavailable"
            res["detail"] = repr(e)
        finally:
            if h is not None:
                h.close()
        results.append(res)
        if log:
            C.append_jsonl(log, dict(res, who="janitor", mono=C.mono()))
    unresolved = unresolved_report(records, skip)
    for u in unresolved:
        if log:
            C.append_jsonl(log, dict(u, who="janitor", event="UNRESOLVED_FORKED_NOT_REGISTERED", mono=C.mono()))
    if log:
        C.append_jsonl(log, {"who": "janitor", "pass_done": True, "targets": len(results), "unresolved": len(unresolved), "reg_info": info,
                             "mono": C.mono()})
    return {"targets": results, "unresolved": unresolved, "reg_info": info}


def unresolved_report(records, skip=()):
    """Forked-but-unregistered nodes whose process may still exist.  Read-only: NEVER signalled.  alive is True / False / None (unreadable)."""
    out = []
    for u in R.unresolved_forked(records):
        if u["pid"] in skip:
            continue
        try:
            st = C.read_stat(u["pid"])
            if st is None or st["state"] in ("Z", "X"):
                alive = False
            elif u.get("starttime") is not None and st["starttime"] != u["starttime"]:
                alive = False
            else:
                alive = True
        except C.ProcUnreadable:
            alive = None
        out.append(dict(u, alive=alive))
    return out


def registered_still_alive(records, skip=()):
    """Read-only: registered, not-DEAD targets whose process still exists (None entries = unreadable, counted as alive)."""
    left = []
    for t in R.cleanup_targets(records):
        if t["pid"] in skip:
            continue
        try:
            if not C.process_is_dead(t["pid"], t["starttime"]):
                left.append(t["node_id"])
        except C.ProcUnreadable:
            left.append(t["node_id"])
    return left


def reg_integrity(reg_path, retries=3, delay=0.2):
    """-> (report, records).  The integrity of the registration FILE, independent of any cleanup state.
    A torn tail is re-read a few times first (the observer may be mid-append); persistent torn tails, corrupt lines, a missing /
    unreadable file or record-level issues all make the report not ok.  status is one of OK, MISSING, CORRUPT, TORN_TAIL."""
    for attempt in range(retries + 1):
        records, info = R.parse_reg(reg_path)
        if not info["torn_tail"] or attempt == retries:
            break
        time.sleep(delay)
    issues = R.integrity_issues(records) if not info["missing"] else []
    if info["missing"]:
        status = "MISSING"
    elif info["corrupt_lines"] or issues:
        status = "CORRUPT"
    elif info["torn_tail"]:
        status = "TORN_TAIL"
    else:
        status = "OK"
    return {"status": status, "ok": status == "OK", "info": info, "issues": issues}, records


def decide_with_integrity(records, observer_exited, integrity_ok, skip=()):
    """decide(), but a file whose integrity is not established can never lead to EXIT_CONFIRMED, and while the observer is still
    running it must not trigger a cleanup of live nodes (the observer's own run-set check reports the damage)."""
    action = decide(records, observer_exited, skip)
    if integrity_ok:
        return action
    return "CLEANUP" if action == "EXIT_CONFIRMED" else action


def final_exit_code(cleanup_clear, integrity_ok):
    """Cleanup state and registration-file integrity are separate facts; 0 requires both."""
    if cleanup_clear and integrity_ok:
        return EXIT_CLEAN
    if cleanup_clear:
        return EXIT_REG_INTEGRITY
    return EXIT_INCOMPLETE if integrity_ok else EXIT_BOTH


def decide(records, observer_exited, skip=()):
    """Pure decision (no I/O except the read-only liveness checks inside `registered_still_alive` when RUN_END claims success).
    -> 'WAIT' | 'EXIT_CONFIRMED' | 'CLEANUP'.
      * no RUN_END and observer alive            -> WAIT
      * no RUN_END and observer dead             -> CLEANUP   (abnormal exit never lifts responsibility)
      * RUN_END with cleanup_confirmed != True   -> CLEANUP   (recovery still owed; also when the field is missing)
      * RUN_END with cleanup_confirmed == True   -> EXIT_CONFIRMED only if nothing registered is still alive, else CLEANUP"""
    end = R.last_run_end(records)
    if end is None:
        return "CLEANUP" if observer_exited else "WAIT"
    if end.get("cleanup_confirmed") is not True:
        return "CLEANUP"
    if registered_still_alive(records, skip) or any(u["alive"] is not False for u in unresolved_report(records, skip)):
        return "CLEANUP"
    return "EXIT_CONFIRMED"


def cleanup_until_clear(reg_path, log, attempts=CLEANUP_ATTEMPTS, interval=CLEANUP_INTERVAL):
    """Repeat passes until every registered target is gone and no forked-unregistered process is alive/unreadable.
    -> (clear: bool, last_result)."""
    last = None
    for _ in range(attempts):
        last = run_cleanup_full(reg_path, log=log)
        records, _ = R.parse_reg(reg_path)
        skip = {os.getpid()}
        if not registered_still_alive(records, skip) and all(u["alive"] is False for u in unresolved_report(records, skip)):
            return True, last
        time.sleep(interval)
    return False, last


def main(argv):
    reg_path, obs_pid, obs_start, log = argv[1], int(argv[2]), int(argv[3]), argv[4]
    C.append_jsonl(log, {"who": "janitor", "event": "START", "pid": os.getpid(), "mono": C.mono()})
    try:
        obs = C.PidfdHandle(obs_pid, obs_start)
    except (C.IdentityError, ProcessLookupError, OSError, C.ProcUnreadable) as e:
        C.append_jsonl(log, {"who": "janitor", "event": "OBSERVER_IDENTITY_UNCONFIRMED_NO_ACTION", "detail": repr(e)})
        return EXIT_IDENTITY
    alerted = None
    while True:                                   # no lifetime cap while the observer is alive: a silent exit would drop the responsibility
        integ, records = reg_integrity(reg_path)
        if not integ["ok"] and alerted != integ["status"]:
            alerted = integ["status"]             # logged as its own event, never mixed into the cleanup events
            C.append_jsonl(log, {"who": "janitor", "event": "REG_INTEGRITY_ALERT", "reg_integrity": integ["status"], "info": integ["info"],
                                 "issues": integ["issues"][:20], "mono": C.mono()})
        action = decide_with_integrity(records, obs.exited(), integ["ok"], {os.getpid()})
        if action == "EXIT_CONFIRMED":
            C.append_jsonl(log, {"who": "janitor", "event": "JANITOR_EXIT", "cleanup_state": "CONFIRMED_AND_VERIFIED", "reg_integrity": "OK",
                                 "code": EXIT_CLEAN})
            return EXIT_CLEAN
        if action == "CLEANUP":
            C.append_jsonl(log, {"who": "janitor", "event": "CLEANUP_REQUIRED", "observer_exited": obs.exited(),
                                 "run_end": R.last_run_end(records)})
            clear, last = cleanup_until_clear(reg_path, log)
            integ_after, _ = reg_integrity(reg_path)                      # judged again AFTER the cleanup passes
            code = final_exit_code(clear, integ_after["ok"])
            C.append_jsonl(log, {"who": "janitor", "event": "JANITOR_EXIT",
                                 "cleanup_state": "CONFIRMED" if clear else "INCOMPLETE_RESPONSIBILITY_OPEN",
                                 "reg_integrity": integ_after["status"], "reg_issues": integ_after["issues"][:20], "code": code, "last": last})
            return code
        C.poll_ready([obs.fd], 0.5)


if __name__ == "__main__":
    os._exit(main(sys.argv))
