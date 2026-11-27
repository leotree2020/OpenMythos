"""ic8_04d plugin (implementation stage C, C2 fix commit, round 1). Data Auditor's own code. Loaded with
`-p ic8_04d_plugin` while two of the Executor's tests run as drivers (C1 ruling item 5). It checks nothing: it wraps
subprocess.run with a pass-through that appends to the JSONL file named by IC8D_TRACE one line per call whose command
names the TEST generator module (metrix_e1.test_data), with the pytest node id of the test running; every call is
passed through unchanged (git calls included)."""
import json
import os
import subprocess

TRACE = os.environ.get("IC8D_TRACE")
_CUR = {"node": None}
_orig = subprocess.run


def _run(*a, **k):
    cmd = a[0] if a else k.get("args")
    text = " ".join(str(x) for x in cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    if "metrix_e1.test_data" in text:
        with open(TRACE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"node": _CUR["node"], "generator_command": text}) + "\n")
    return _orig(*a, **k)


subprocess.run = _run


def pytest_runtest_setup(item):
    _CUR["node"] = item.nodeid
    with open(TRACE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"node": item.nodeid, "event": "setup"}) + "\n")
