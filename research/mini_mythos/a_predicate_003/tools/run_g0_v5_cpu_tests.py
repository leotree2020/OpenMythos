#!/usr/bin/env python3
"""Runner for the G0 V5 CPU pure-logic tests (F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001).

Safety: before any test module is imported it replaces EVERY process-creating / signalling / waiting function (os.fork*, os.kill*, os.exec*, os.spawn*,
os.system/popen, os.wait*, signal senders, subprocess) by a sentinel that raises ProcessSafetyViolation and is counted; a run is only PASS when the
count is zero.  Tests run in an isolated temporary directory (TMPDIR), with bytecode writing off, in the fixed group order of the task.  Results are
recorded per test (status, time, traceback) together with the environment and the Git SHA given in G0_TEST_GIT_SHA.
usage: run_g0_v5_cpu_tests.py [--groups g1,g2,...] [--json OUT.json] [--txt OUT.txt]       Exit 0 = every selected test passed and no sentinel fired."""
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A003, "tests"))
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, os.path.join(A003, "gate_g0"))

# environment facts are collected BEFORE the sentinels exist (platform.platform() runs `uname -p` through subprocess on some systems)
ENV0 = {"python": sys.version.split()[0], "platform": platform.platform(), "kernel": platform.release(), "cpu_count": os.cpu_count(), "uid": os.getuid()}
VIOLATIONS = []


class ProcessSafetyViolation(AssertionError):
    pass


def _sentinel(name):
    def f(*a, **k):
        VIOLATIONS.append(name)
        raise ProcessSafetyViolation("the CPU tests must not start, signal or wait for a process: %s" % name)
    f.__name__ = "sentinel_" + name.replace(".", "_")
    return f


for _n in ("fork", "forkpty", "kill", "killpg", "system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe", "spawnl",
           "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp", "wait", "wait3", "wait4", "waitid",
           "waitpid", "pidfd_open", "setsid", "setpgid"):
    if hasattr(os, _n):
        setattr(os, _n, _sentinel("os." + _n))
for _n in ("pidfd_send_signal", "raise_signal", "pthread_kill"):
    if hasattr(signal, _n):
        setattr(signal, _n, _sentinel("signal." + _n))
for _n in ("Popen", "run", "call", "check_call", "check_output"):
    setattr(subprocess, _n, _sentinel("subprocess." + _n))

GROUPS = [
    ("g1_judge_fidelity_closure", ["test_g0_v5_cases", "test_g0_v5_closure_cases.TestMarkerSchema", "test_g0_v5_closure_cases.TestClosureRulesAsFacts",
                                   "test_g0_interlock_and_judge.TestJudge"]),
    ("g2_directory_pipeline_fault_injection", ["test_g0_v5_closure_cases.TestClosureCasesMaterialised", "test_g0_v5_pipeline", "test_g0_v5_run_parts"]),
    ("g3_interlock_and_source_constraints", ["test_g0_interlock_and_judge.TestInterlock", "test_g0_interlock_and_judge.TestSourceConstraints"]),
    ("g4_supplementary", ["test_g0_v5_supplement"]),
]


class Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        unittest.TextTestResult.__init__(self, *a, **k)
        self.rows, self._t = [], {}

    def startTest(self, test):
        self._t[test.id()] = time.monotonic()
        unittest.TextTestResult.startTest(self, test)

    def _row(self, test, status, detail=""):
        self.rows.append({"id": test.id(), "status": status, "seconds": round(time.monotonic() - self._t.get(test.id(), time.monotonic()), 4), "detail": detail})

    def addSuccess(self, test):
        unittest.TextTestResult.addSuccess(self, test)
        self._row(test, "PASS")

    def addFailure(self, test, err):
        unittest.TextTestResult.addFailure(self, test, err)
        self._row(test, "FAIL", "".join(traceback.format_exception(*err)))

    def addError(self, test, err):
        unittest.TextTestResult.addError(self, test, err)
        self._row(test, "ERROR", "".join(traceback.format_exception(*err)))

    def addSkip(self, test, reason):
        unittest.TextTestResult.addSkip(self, test, reason)
        self._row(test, "SKIP", reason)

    def addSubTest(self, test, subtest, err):
        unittest.TextTestResult.addSubTest(self, test, subtest, err)
        if err is not None:
            self._row(subtest, "FAIL", "".join(traceback.format_exception(*err)))


def main(argv):
    sel = None
    if "--groups" in argv:
        sel = set(argv[argv.index("--groups") + 1].split(","))
    tmp = tempfile.mkdtemp(prefix="g0v5_cpu_tests_")
    os.environ["TMPDIR"] = tmp
    tempfile.tempdir = tmp
    env = {**ENV0, "tmpdir": tmp, "cwd": os.getcwd(), "git_sha": os.environ.get("G0_TEST_GIT_SHA", "UNKNOWN"), "dont_write_bytecode": sys.dont_write_bytecode,
           "gpu_used": False}
    report = {"environment": env, "groups": [], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    all_ok = True
    for gname, mods in GROUPS:
        if sel is not None and gname not in sel:
            continue
        stream = open(os.path.join(tmp, gname + ".log"), "w")
        runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result)
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        load_errors = []
        for m in mods:
            try:
                suite.addTests(loader.loadTestsFromName(m))
            except BaseException:
                load_errors.append({"module": m, "error": traceback.format_exc()})
        res = runner.run(suite)
        rows = res.rows
        counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("PASS", "FAIL", "ERROR", "SKIP")}
        report["groups"].append({"group": gname, "modules": mods, "tests_run": res.testsRun, "counts": counts, "load_errors": load_errors, "rows": rows})
        all_ok = all_ok and not load_errors and counts["FAIL"] == 0 and counts["ERROR"] == 0
        print("%-42s run=%3d PASS=%3d FAIL=%3d ERROR=%3d SKIP=%3d load_errors=%d" % (gname, res.testsRun, counts["PASS"], counts["FAIL"], counts["ERROR"], counts["SKIP"], len(load_errors)))
    report["sentinel_violations"] = list(VIOLATIONS)
    report["verdict"] = "PASS" if (all_ok and not VIOLATIONS) else "FAIL"
    print("process-safety sentinel violations:", len(VIOLATIONS), "| verdict:", report["verdict"])
    for g in report["groups"]:
        for r in g["rows"]:
            if r["status"] in ("FAIL", "ERROR"):
                print("  %s %s" % (r["status"], r["id"]))
        for e in g["load_errors"]:
            print("  LOAD-ERROR", e["module"])
    if "--json" in argv:
        with open(argv[argv.index("--json") + 1], "w") as f:
            json.dump(report, f, indent=1)
    if "--txt" in argv:
        with open(argv[argv.index("--txt") + 1], "w") as f:
            for g in report["groups"]:
                f.write("== %s %s\n" % (g["group"], g["counts"]))
                for r in g["rows"]:
                    f.write("%-5s %s (%.3fs)\n" % (r["status"], r["id"], r["seconds"]))
                    if r["status"] in ("FAIL", "ERROR"):
                        f.write(r["detail"] + "\n")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
