"""ic7_04 trace plugin (implementation stage C, C2 work commit, round 1; task 4, dynamic part). Data Auditor's own code.

A pytest plugin loaded with `-p ic7_04_trace_plugin` while the Executor's test
tests/test_run_pilot.py::test_test_evaluate_end_to_end_once runs as a driver subprocess (C1 ruling item 5). It does not
check anything: it only records, in the JSONL file named by the environment variable IC7_TRACE, every call (enter /
return / raise) of the functions on the TEST evaluation path, so that my own analysis script (ic7_04_e2e.py, which
imports nothing of the Executor) can compare the observed order with the order I expected before the run. The wrappers
pass arguments and results through unchanged.

Observed (module attribute replaced by a pass-through wrapper after collection, before the fixture runs):
  metrix_e1.pilot.run_test_evaluate, metrix_e1.pilot.test_evaluate, metrix_e1.pilot.final_record,
  metrix_e1.test_data.check_preconditions, metrix_e1.frozen.file_sha256 (only paths ending in .pt are logged),
  metrix_e1.testgate.begin_test_evaluation, metrix_e1.testgate.claim_checkpoint, metrix_e1.testgate.commit_paths,
  metrix_e1.testgate.finish_test_evaluation, metrix_e1.evaluate.evaluate_model, metrix_e1.gate.compute_test_values,
  metrix_e1.gate.judge_test, metrix_e1.gate.report_comparisons.
At the start of the test call (after the fixture) the plugin logs the clone, the bare remote, the work directory, the
models of the fixture and the remote's tip; nothing of the test's objects is changed.

Fault injection (IC7_FAULT, empty by default): "stop_after_marker" raises a ProtocolStop(None, "BLOCKED", ...) and
"crash_after_marker" a RuntimeError when evaluate_model(split="test") is entered for the 3rd time (after the marker was
pushed and two models were evaluated). Used only for the two extra runs that observe the record written (or not) after
the marker; the test is then expected to fail, and only the repository state it leaves is analysed.
"""
import json
import os
import subprocess

TRACE = os.environ.get("IC7_TRACE")
FAULT = os.environ.get("IC7_FAULT", "")
_STATE = {"installed": False, "test_evals": 0, "seq": 0}


def _log(ev):
    _STATE["seq"] += 1
    ev = dict(ev, seq=_STATE["seq"])
    with open(TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, default=str, ensure_ascii=False) + "\n")


def _short(v):
    s = repr(v)
    return s if len(s) <= 300 else s[:300] + "..."


def _wrap(mod, name, describe=None, result=None, only=None):
    orig = getattr(mod, name)

    def wrapper(*a, **k):
        if only is not None and not only(a, k):
            return orig(*a, **k)
        info = describe(a, k) if describe else {}
        _log(dict({"call": name, "phase": "enter"}, **info))
        if name == "evaluate_model" and k.get("split") == "test":
            _STATE["test_evals"] += 1
            if FAULT and _STATE["test_evals"] == 3:
                if FAULT == "stop_after_marker":
                    from metrix_e1.errors import ProtocolStop
                    exc = ProtocolStop(None, "BLOCKED", "auditor-injected stop after the TEST marker (ic7 fault "
                                       "injection, 3rd TEST evaluation)")
                else:
                    exc = RuntimeError("auditor-injected crash after the TEST marker (ic7 fault injection, 3rd TEST "
                                       "evaluation)")
                _log({"call": name, "phase": "injected", "fault": FAULT, "exc": type(exc).__name__})
                raise exc
        try:
            r = orig(*a, **k)
        except BaseException as e:      # noqa: B902 -- logged and re-raised unchanged
            _log({"call": name, "phase": "raise", "exc": type(e).__name__, "msg": str(e)[:400]})
            raise
        _log(dict({"call": name, "phase": "return"}, **(result(r) if result else {})))
        return r
    wrapper.__wrapped_by_ic7__ = orig
    setattr(mod, name, wrapper)


def _install():
    if _STATE["installed"]:
        return
    import metrix_e1.evaluate as E
    import metrix_e1.frozen as FZ
    import metrix_e1.gate as G
    import metrix_e1.pilot as P
    import metrix_e1.test_data as TD
    import metrix_e1.testgate as TG
    _wrap(P, "run_test_evaluate", result=lambda r: {"result": _short(r)})
    _wrap(P, "test_evaluate", result=lambda r: {"result": _short(r[0])})
    _wrap(P, "final_record", describe=lambda a, k: {"command": a[1], "status": a[2]})
    _wrap(TD, "check_preconditions")
    _wrap(FZ, "file_sha256", describe=lambda a, k: {"file": os.path.basename(str(a[0]))}, result=lambda r: {"sha256": r},
          only=lambda a, k: str(a[0]).endswith(".pt"))
    _wrap(TG, "begin_test_evaluation", result=lambda r: {"marker_commit": getattr(r, "marker_commit", None)})
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


def pytest_runtest_call(item):
    c = item.funcargs.get("eval_clone")
    if c is None:
        return
    tip = subprocess.run(["git", "-C", str(c["remote"]), "rev-parse", "main"], capture_output=True, text=True).stdout.strip()
    _log({"call": "test", "phase": "start", "root": str(c["root"]), "remote": str(c["remote"]),
          "work": str(c["p"].work), "models": list(c["models"]), "remote_tip_after_fixture": tip,
          "synthetic_question_example": "Synthetic question 0 (not a TEST row)?"})
