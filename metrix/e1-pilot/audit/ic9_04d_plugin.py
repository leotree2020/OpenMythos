"""ic9_04d plugin (implementation stage C, C2 second fix commit, round 1). Data Auditor's own code; my ic8_04d_plugin.py
extended. Loaded with `-p ic9_04d_plugin` while some of the Executor's tests run as drivers (C1 ruling item 5). It checks
nothing:
  - it wraps subprocess.run with a pass-through that appends to the JSONL file named by IC9D_TRACE one line per call
    whose command names the TEST generator module (metrix_e1.test_data), with the pytest node id of the test running;
    every call is passed through unchanged (git calls included);
  - after collection it wraps metrix_e1.pilot.st10_over_limit with a pass-through that logs each call's result (the
    test test_test_generate_records_an_st10_stop_of_its_own_run replaces pilot's own `subprocess` reference and
    final_record, not st10_over_limit), so that my script sees whether run_test_generate read the committed ST10
    record on each call."""
import json
import os
import subprocess

TRACE = os.environ.get("IC9D_TRACE")
_CUR = {"node": None, "installed": False}
_orig = subprocess.run


def _log(ev):
    with open(TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, default=str) + "\n")


def _run(*a, **k):
    cmd = a[0] if a else k.get("args")
    text = " ".join(str(x) for x in cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    if "metrix_e1.test_data" in text:
        _log({"node": _CUR["node"], "generator_command": text})
    return _orig(*a, **k)


subprocess.run = _run


def pytest_collection_finish(session):
    if _CUR["installed"]:
        return
    import metrix_e1.pilot as P
    orig = P.st10_over_limit

    def st10_over_limit(p):
        r = orig(p)
        _log({"node": _CUR["node"], "call": "st10_over_limit", "result": r})
        return r
    P.st10_over_limit = st10_over_limit
    _CUR["installed"] = True


def pytest_runtest_setup(item):
    _CUR["node"] = item.nodeid
    _log({"node": item.nodeid, "event": "setup"})
