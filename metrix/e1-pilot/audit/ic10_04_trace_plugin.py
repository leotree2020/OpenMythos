"""ic10_04 trace plugin (implementation stage C, C2 third fix commit, round 1; task 2 of the invocation). Data Auditor's
own code; my ic9_04_trace_plugin.py extended for this round's code.

A pytest plugin loaded with `-p ic10_04_trace_plugin` while the Executor's tests
tests/test_run_pilot.py::test_test_evaluate_end_to_end_once (ic10_04_e2e.py) or
tests/test_run_pilot.py::test_test_evaluate_begin_wiring[...] (ic10_04f_wiring.py) run as driver subprocesses (C1
ruling item 5). It does not check anything: it only records, in the JSONL file named by the environment variable
IC10_TRACE, every call (enter / return / raise) of the functions on the TEST evaluation path, so that my own analysis
scripts (which import nothing of the Executor) can compare the observed order with the order I expected before the run.
The wrappers pass arguments and results through unchanged.

Observed (module or class attribute replaced by a pass-through wrapper after collection, before the fixture runs):
  metrix_e1.pilot: run_test_evaluate (and, at its exit, the Pilot's begin_called / marker_before_begin and its work
    directory), test_evaluate, refuse_if_test_evaluated, final_record, write_experiment_record (the paths it returns),
    control_evaluation, test_evaluation_seconds (its timing argument and result), begun_by_this_process (its result),
    Pilot.start_checks (the command), and the class methods Pilot.device_check, Pilot.before_run and
    Pilot.base_model (called only by a Pilot whose instance does not replace them);
  metrix_e1.record: committed_json, committed_record (the path read);
  metrix_e1.train.state_sha256 (the hash returned);
  metrix_e1.test_data.check_preconditions; metrix_e1.frozen.file_sha256 (only paths ending in .pt are logged);
  metrix_e1.testgate: code_commit, begin_test_evaluation (its base-model hash argument; at its entry also the Pilot's
    begin_called and marker_before_begin and whether the marker file exists in the clone's working tree),
    claim_checkpoint, commit_paths, finish_test_evaluation; metrix_e1.evaluate.evaluate_model; metrix_e1.gate:
    compute_test_values, judge_test, report_comparisons.
  subprocess.run (global, pass-through): every git command run while refuse_if_test_evaluated is active, and every
    git fetch / push / pull / ls-remote run while run_test_evaluate is active, with the stack of the wrapped calls
    active at that moment (so that the script sees which call fetched).
At the start of each test call (after the fixture; tryfirst) the plugin logs the test's node id, the clone, the bare
remote, the work directory, the models of the fixture, the remote's tip and the Pilot's start time and flags, and makes
every callable later assigned to the Pilot's `before_run`, `base_model` or `device_check` a pass-through that logs the
call (before_run: its next_seconds argument): it gives the Pilot instance a subclass of its own class whose __setattr__
wraps those attributes; the values assigned, the calls and their results are unchanged.

Fault injection (IC10_FAULT, empty by default; only used with the end-to-end test):
  "stop_after_marker"       ProtocolStop(None, "BLOCKED", ...) when evaluate_model(split="test") is entered for the
                            3rd time (after the marker was pushed and two models were evaluated);
  "crash_after_marker"      RuntimeError at the same point;
  "interrupt_after_marker"  KeyboardInterrupt at the same point (supplementary);
  "st7_before_begin"        stops.Stop("ST7", "BLOCKED", ...) raised by the before_run wrapper, instead of calling the
                            test's before_run, at the first before_run call with next_seconds > 0 in the 3rd call of
                            run_test_evaluate (the test's evaluation run; the ST7 look-ahead before the begin).
"""
import json
import os
import subprocess

import pytest

TRACE = os.environ.get("IC10_TRACE")
FAULT = os.environ.get("IC10_FAULT", "")
_STATE = {"installed": False, "test_evals": 0, "seq": 0, "rte_calls": 0, "st7_done": False, "p": None, "root": None,
          "stack": []}
NETWORK = ("fetch", "push", "pull", "ls-remote")
_orig_run = subprocess.run


def _run(*a, **k):
    cmd = a[0] if a else k.get("args")
    if isinstance(cmd, (list, tuple)) and cmd and os.path.basename(str(cmd[0])) == "git":
        args = [str(x) for x in cmd[1:]]
        if len(args) >= 2 and args[0] == "-C":
            args = args[2:]
        stack = list(_STATE["stack"])
        if "refuse_if_test_evaluated" in stack or ("run_test_evaluate" in stack and args and args[0] in NETWORK):
            _log({"call": "git", "phase": "run", "args": args, "stack": stack})
    return _orig_run(*a, **k)


subprocess.run = _run


def _log(ev):
    _STATE["seq"] += 1
    ev = dict(ev, seq=_STATE["seq"])
    with open(TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, default=str, ensure_ascii=False) + "\n")


def _short(v):
    s = repr(v)
    return s if len(s) <= 300 else s[:300] + "..."


def _inject_after_marker():
    if FAULT == "stop_after_marker":
        from metrix_e1.errors import ProtocolStop
        return ProtocolStop(None, "BLOCKED", "auditor-injected stop after the TEST marker (ic10 fault injection, 3rd TEST "
                            "evaluation)")
    if FAULT == "crash_after_marker":
        return RuntimeError("auditor-injected crash after the TEST marker (ic10 fault injection, 3rd TEST evaluation)")
    if FAULT == "interrupt_after_marker":
        return KeyboardInterrupt("auditor-injected interrupt after the TEST marker (ic10 fault injection, 3rd TEST "
                                 "evaluation)")
    return None


def _flags(name, a):
    """At the exit of run_test_evaluate: the Pilot's two flags and its work directory."""
    if name != "run_test_evaluate" or not a:
        return {}
    return {"begin_called": getattr(a[0], "begin_called", "<absent>"),
            "marker_before_begin": getattr(a[0], "marker_before_begin", "<absent>"), "work": str(a[0].work)}


def _wrap(owner, name, describe=None, result=None, only=None, label=None):
    orig = getattr(owner, name)
    label = label or name

    def wrapper(*a, **k):
        if only is not None and not only(a, k):
            return orig(*a, **k)
        info = describe(a, k) if describe else {}
        _log(dict({"call": label, "phase": "enter"}, **info))
        if name == "run_test_evaluate":
            _STATE["rte_calls"] += 1
        if name == "evaluate_model" and k.get("split") == "test":
            _STATE["test_evals"] += 1
            if _STATE["test_evals"] == 3:
                exc = _inject_after_marker()
                if exc is not None:
                    _log({"call": label, "phase": "injected", "fault": FAULT, "exc": type(exc).__name__})
                    raise exc
        _STATE["stack"].append(label)
        try:
            r = orig(*a, **k)
        except BaseException as e:      # noqa: B902 -- logged and re-raised unchanged
            _STATE["stack"].pop()
            _log(dict({"call": label, "phase": "raise", "exc": type(e).__name__, "msg": str(e)[:400]}, **_flags(name, a)))
            raise
        _STATE["stack"].pop()
        _log(dict({"call": label, "phase": "return"}, **(result(r) if result else {}), **_flags(name, a)))
        return r
    wrapper.__wrapped_by_ic10__ = orig
    setattr(owner, name, wrapper)


def _begin_describe(a, k):
    p, root = _STATE["p"], _STATE["root"]
    out = {"base_sha256": a[3] if len(a) > 3 else k.get("base_model_sha256")}
    if p is not None:
        import metrix_e1.testgate as TG
        out.update(begin_called=getattr(p, "begin_called", "<absent>"),
                   marker_before_begin=getattr(p, "marker_before_begin", "<absent>"),
                   marker_in_worktree=os.path.exists(os.path.join(root, TG.MARKER_REL)))
    return out


def _install():
    if _STATE["installed"]:
        return
    import metrix_e1.evaluate as E
    import metrix_e1.frozen as FZ
    import metrix_e1.gate as G
    import metrix_e1.pilot as P
    import metrix_e1.record as R
    import metrix_e1.test_data as TD
    import metrix_e1.testgate as TG
    import metrix_e1.train as T
    _wrap(P, "run_test_evaluate", result=lambda r: {"result": _short(r)})
    _wrap(P, "test_evaluate", result=lambda r: {"result": _short(r[0])})
    _wrap(P, "begun_by_this_process", result=lambda r: {"result": r})
    _wrap(P, "refuse_if_test_evaluated")
    _wrap(TG, "code_commit", result=lambda r: {"head": r}, label="TG.code_commit")
    _wrap(P, "final_record", describe=lambda a, k: {"command": a[1], "status": a[2], "actual_keys": sorted(a[3]) if isinstance(a[3], dict) else None,
                                                    "test_begun": a[3].get("test_begun", "<absent>") if isinstance(a[3], dict) else None,
                                                    "stop": a[6] if len(a) > 6 else k.get("stop")})
    _wrap(P, "write_experiment_record", result=lambda r: {"paths": [os.path.basename(str(x)) for x in r]})
    _wrap(P, "control_evaluation", describe=lambda a, k: {"what": a[2], "split": k.get("split", "dev")})
    _wrap(P, "test_evaluation_seconds", describe=lambda a, k: {"timing": a[1]}, result=lambda r: {"seconds": r})
    _wrap(P.Pilot, "start_checks", describe=lambda a, k: {"command": a[1]}, label="Pilot.start_checks")
    for m in ("device_check", "before_run", "base_model"):      # the class methods (a Pilot whose instance does not
        _wrap(P.Pilot, m, label="Pilot." + m)                   # replace them, e.g. the wrong_work test's own Pilot)
    _wrap(R, "committed_json", describe=lambda a, k: {"rel": str(a[1])}, label="R.committed_json")
    _wrap(R, "committed_record", describe=lambda a, k: {"rel": str(a[1])}, label="R.committed_record")
    _wrap(T, "state_sha256", result=lambda r: {"sha256": r}, label="T.state_sha256")
    _wrap(TD, "check_preconditions")
    _wrap(FZ, "file_sha256", describe=lambda a, k: {"file": os.path.basename(str(a[0]))}, result=lambda r: {"sha256": r},
          only=lambda a, k: str(a[0]).endswith(".pt"))
    _wrap(TG, "begin_test_evaluation", describe=_begin_describe,
          result=lambda r: {"marker_commit": getattr(r, "marker_commit", None)})
    _wrap(TG, "claim_checkpoint", describe=lambda a, k: {"checkpoint": a[1]})
    _wrap(TG, "commit_paths", describe=lambda a, k: {"rels": list(a[1])}, result=lambda r: {"head": r})
    _wrap(TG, "finish_test_evaluation", result=lambda r: {"head": r})
    _wrap(E, "evaluate_model", describe=lambda a, k: {"split": k.get("split", "dev"),
                                                      "checkpoint": k.get("checkpoint_name")})
    _wrap(G, "compute_test_values")
    _wrap(G, "judge_test", result=lambda r: {"final_status": r.get("final_status")})
    _wrap(G, "report_comparisons", describe=lambda a, k: {"split": a[2] if len(a) > 2 else k.get("split")})
    _STATE["installed"] = True
    _log({"call": "plugin", "phase": "installed", "fault": FAULT})


def pytest_collection_finish(session):
    _install()


def _traced(name, fn):
    def wrapper(*a, **k):
        info = {"call": "p." + name, "phase": "enter"}
        if name == "before_run":
            info["next_seconds"] = a[0] if a else k.get("next_seconds", 0.0)
            if (FAULT == "st7_before_begin" and not _STATE["st7_done"] and _STATE["rte_calls"] == 3
                    and info["next_seconds"] > 0):
                _STATE["st7_done"] = True
                from metrix_e1 import stops as STP
                exc = STP.Stop("ST7", "BLOCKED", "stop and report", "auditor-injected ST7 look-ahead before the TEST "
                               "begin (ic10 fault injection, next_seconds %r)" % info["next_seconds"])
                _log(dict(info, phase="injected", fault=FAULT, exc=type(exc).__name__))
                raise exc
        _log(info)
        try:
            r = fn(*a, **k)
        except BaseException as e:      # noqa: B902 -- logged and re-raised unchanged
            _log({"call": "p." + name, "phase": "raise", "exc": type(e).__name__})
            raise
        _log({"call": "p." + name, "phase": "return"})
        return r
    wrapper.__ic10_traced__ = True
    return wrapper


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item):
    c = item.funcargs.get("eval_clone")
    if c is None:
        return
    p = c["p"]
    _STATE["p"], _STATE["root"] = p, str(c["root"])
    base_cls = type(p)

    class _Traced(base_cls):
        def __setattr__(self, k, v):
            if k in ("before_run", "base_model", "device_check") and callable(v) and not getattr(v, "__ic10_traced__", False):
                v = _traced(k, v)
            super().__setattr__(k, v)
    _Traced.__name__ = base_cls.__name__
    _Traced.__qualname__ = base_cls.__qualname__
    p.__class__ = _Traced
    p.before_run = p.before_run          # the fixture's callables, now wrapped (pass-through)
    p.base_model = p.base_model
    p.device_check = p.device_check
    tip = subprocess.run(["git", "-C", str(c["remote"]), "rev-parse", "main"], capture_output=True, text=True).stdout.strip()
    _log({"call": "test", "phase": "start", "node": item.nodeid, "root": str(c["root"]), "remote": str(c["remote"]),
          "work": str(p.work), "models": list(c["models"]), "remote_tip_after_fixture": tip, "started": p.started,
          "begin_called": p.begin_called, "marker_before_begin": p.marker_before_begin})
