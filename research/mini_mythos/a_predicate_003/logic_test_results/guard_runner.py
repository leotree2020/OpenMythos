"""Execution guard for F3B-D1-A-CPU-003-E1A-LOGIC-TEST-001 (pure-logic tests only).

Runs ONE unmodified test file as __main__ after replacing every process-creating, signalling, waiting or exec primitive with a
recorder that raises.  Any attempt is a BOUNDARY VIOLATION: it is recorded in <guard json> and the run exits 3 (-> BLOCKED).
This is defense in depth on top of the static audit; it does not change the tests, the bench or any expectation.
usage: guard_runner.py TEST_FILE GUARD_JSON"""
import json
import os
import runpy
import signal
import subprocess
import sys

VIOL = []


def trap(name):
    def f(*a, **k):
        VIOL.append({"call": name, "args": repr(a)[:160]})
        raise RuntimeError("LOGIC-TEST-001 BOUNDARY VIOLATION: " + name)
    f.__name__ = "trapped_" + name.replace(".", "_")
    return f


TRAPS = {
    os: ["fork", "forkpty", "kill", "killpg", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe", "posix_spawn",
         "posix_spawnp", "system", "popen", "waitpid", "wait", "wait3", "wait4", "waitid", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv",
         "spawnve", "spawnvp", "spawnvpe", "pidfd_open", "setsid", "setpgid", "setpgrp"],
    signal: ["pidfd_send_signal", "raise_signal", "pthread_kill"],
    subprocess: ["Popen", "run", "call", "check_call", "check_output"],
}
for mod, names in TRAPS.items():
    for n in names:
        if hasattr(mod, n):
            setattr(mod, n, trap("%s.%s" % (mod.__name__, n)))

test_file, guard_json = sys.argv[1], sys.argv[2]
code = 0
sys.argv = [test_file]          # RERUN-001: unittest.main() must not read the guard's own arguments as test names
try:
    runpy.run_path(test_file, run_name="__main__")
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
json.dump({"test_file": test_file, "violations": VIOL, "trapped_primitives": sum(len(v) for v in TRAPS.values())}, open(guard_json, "w"), indent=1)
sys.exit(3 if VIOL else code)
