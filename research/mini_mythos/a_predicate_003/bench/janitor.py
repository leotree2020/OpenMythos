"""Fail-closed janitor.  Exec'd as `python -I -S janitor.py REG OBSERVER_PID OBSERVER_STARTTIME LOG` by the observer, or called
as run_cleanup() from the validity checks.  It acts ONLY on nodes that have an INTENT record AND a complete REGISTERED record,
re-opens a pidfd first and compares the live starttime with the registered one, and refuses to signal when identity cannot be
confirmed.  It never matches names or command lines, never signals process groups.  WRITTEN, NOT RUN."""
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C            # noqa: E402
import registry as R          # noqa: E402


def _default_signal(handle, sig):
    return handle.send(sig)


def run_cleanup(reg_path, signal_fn=_default_signal, log=None, skip_pids=None):
    """One pass over the REG file.  -> list of per-target result dicts (also appended to `log` if given).
    The janitor never signals itself."""
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
    if log:
        C.append_jsonl(log, {"who": "janitor", "pass_done": True, "targets": len(results), "reg_info": info, "mono": C.mono()})
    return results


def _run_end_seen(reg_path):
    records, _ = R.parse_reg(reg_path)
    return any(r.get("kind") == "RUN_END" for r in records)


def main(argv):
    reg_path, obs_pid, obs_start, log = argv[1], int(argv[2]), int(argv[3]), argv[4]
    C.append_jsonl(log, {"who": "janitor", "event": "START", "pid": os.getpid(), "mono": C.mono()})
    try:
        obs = C.PidfdHandle(obs_pid, obs_start)
    except (C.IdentityError, ProcessLookupError, OSError, C.ProcUnreadable) as e:
        C.append_jsonl(log, {"who": "janitor", "event": "OBSERVER_IDENTITY_UNCONFIRMED_NO_ACTION", "detail": repr(e)})
        return 2
    deadline = C.mono() + C.T_JANITOR_MAX
    while C.mono() < deadline:
        if obs.exited():
            if _run_end_seen(reg_path):
                C.append_jsonl(log, {"who": "janitor", "event": "OBSERVER_EXITED_AFTER_RUN_END_NO_ACTION"})
                return 0
            C.append_jsonl(log, {"who": "janitor", "event": "OBSERVER_DIED_WITHOUT_RUN_END_CLEANUP"})
            run_cleanup(reg_path, log=log)
            time.sleep(1.0)
            run_cleanup(reg_path, log=log)
            return 0
        if _run_end_seen(reg_path):
            C.append_jsonl(log, {"who": "janitor", "event": "RUN_END_SEEN_NO_ACTION"})
            return 0
        C.poll_ready([obs.fd], 0.5)
    C.append_jsonl(log, {"who": "janitor", "event": "LIFETIME_CAP_NO_ACTION"})
    return 3


if __name__ == "__main__":
    os._exit(main(sys.argv))
