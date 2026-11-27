"""ic11_06 plugin (implementation stage C, C4 code commit, round 1; task 3). Data Auditor's own code. Loaded with
`-p ic11_06_plugin` while tests/test_run_pilot.py::test_formal_st11_reads_b17_plus_the_checkpoint_overhead[...] runs as a
driver subprocess (C1 ruling item 5). It checks nothing; it appends to the JSONL file named by IC11_TRACE one line per
call of the observed functions, with arguments and results passed through unchanged:
  metrix_e1.pilot.run_gate (its return value, or the exception type and message; the Pilot's root and work directory),
  metrix_e1.pilot.st11_estimate_hours (arguments and result), metrix_e1.stops.st11 (its estimate argument, the bound
  of the contract it was given, and whether it raised: the stop code, status and message), metrix_e1.pilot.step3 is
  not wrapped (the test replaces it). The wrappers are installed after collection, before the test's own
  monkeypatching (which replaces CP.estimate_total_hours, P.checkpoint_overhead_seconds, P.step3 and T.train_run, none
  of which is wrapped here)."""
import json
import os

TRACE = os.environ.get("IC11_TRACE")
_S = {"installed": False, "node": None}


def _log(ev):
    with open(TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(ev, node=_S["node"]), default=repr) + "\n")


def pytest_collection_finish(session):
    if _S["installed"]:
        return
    import metrix_e1.pilot as P
    import metrix_e1.stops as STP
    orig_gate, orig_sum, orig_st11 = P.run_gate, P.st11_estimate_hours, STP.st11

    def run_gate(p, *a, **k):
        _log({"call": "run_gate", "args": [repr(x) for x in a], "root": str(getattr(p, "root", None)),
              "work": str(getattr(p, "work", None))})
        try:
            r = orig_gate(p, *a, **k)
        except BaseException as e:
            _log({"call": "run_gate", "raised": type(e).__name__, "message": str(e)})
            raise
        _log({"call": "run_gate", "returned": r})
        return r

    def st11_estimate_hours(b17_hours, overhead_seconds):
        r = orig_sum(b17_hours, overhead_seconds)
        _log({"call": "st11_estimate_hours", "b17_hours": b17_hours, "overhead_seconds": overhead_seconds, "result": r,
              "result_repr": repr(r)})
        return r

    def st11(fz, contract, estimate_hours):
        ev = {"call": "stops.st11", "estimate_hours": estimate_hours, "estimate_repr": repr(estimate_hours),
              "bound": contract.stops.st11_hours}
        try:
            r = orig_st11(fz, contract, estimate_hours)
        except BaseException as e:
            _log(dict(ev, raised=type(e).__name__, stop=getattr(e, "stop", None), status=getattr(e, "status", None),
                      message=str(e)))
            raise
        _log(dict(ev, returned=r))
        return r
    P.run_gate, P.st11_estimate_hours, STP.st11 = run_gate, st11_estimate_hours, st11
    _S["installed"] = True


def pytest_runtest_setup(item):
    _S["node"] = item.nodeid
    _log({"event": "setup"})
