#!/usr/bin/env python3
"""Runner for the G1 CPU tests (F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001; WRITTEN, NOT RUN -- the CPU tests need a separate owner authorization).

Safety: before any test module is imported it replaces EVERY process-creating / signalling / waiting function (os.fork*, os.kill*, os.exec*, os.spawn*,
os.system/popen, os.wait*, signal senders, subprocess) by a sentinel that raises ProcessSafetyViolation and is counted; a run is only PASS when the
count is zero.  Tests run in an isolated temporary directory (TMPDIR), with bytecode writing off, in fixed group order.  Results are recorded per test
(status, time, traceback) together with the environment, the ACTUAL checkout HEAD (read from .git, compared with the expected SHA; a mismatch, a changed
frozen G0 / G1 file or a changed bench refuses the run) and the hashes of the key G1 implementation and test files.  The sentinels are installed before
anything else; environment facts come from os.uname() (no subprocess).  No test installs the G1 guard and none starts a process.
usage: run_g1_cpu_tests.py --expect-sha SHA | G0_TEST_GIT_SHA=SHA [--groups g1,g2,...] [--json OUT.json] [--txt OUT.txt]       Exit 0 = every selected test passed and no sentinel fired."""
import json
import os
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
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(A003, "tests"))
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, os.path.join(A003, "gate_g0"))
sys.path.insert(0, os.path.join(A003, "gate_g1"))

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
    ("g1_judge_cases", ["test_g1_judge_cases"]),
    ("g2_auth_preflight_pipeline", ["test_g1_auth_preflight", "test_g1_run_parts"]),
    ("g3_boundaries_mutations_acceptance", ["test_g1_boundaries", "test_g1_mutations", "test_g1_runner_acceptance"]),
]
G1_KEY_FILES = ("gate_g1/g1_auth.py", "gate_g1/g1_judge.py", "gate_g1/g1_run.py", "gate_g1/g1_criteria_v1.json", "gate_g1/E1A_GATE_G1_PREREG.md",
                "gate_g1/g1_criteria_v1.json.sha256", "gate_g1/E1A_GATE_G1_PREREG.md.sha256", "tests/g1_fixtures.py", "tests/test_g1_judge_cases.py",
                "tests/test_g1_auth_preflight.py", "tests/test_g1_run_parts.py", "tests/test_g1_boundaries.py", "tests/test_g1_mutations.py",
                "tools/run_g1_cpu_tests.py", "tools/g1_test_acceptance.py", "tests/test_g1_runner_acceptance.py", "tools/audit_g1_implementation.py")


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

    def addExpectedFailure(self, test, err):
        unittest.TextTestResult.addExpectedFailure(self, test, err)
        self._row(test, "XFAIL", "expected failure: the test did not pass")           # an unknown status: never part of an acceptance PASS

    def addUnexpectedSuccess(self, test):
        unittest.TextTestResult.addUnexpectedSuccess(self, test)
        self._row(test, "XPASS", "unexpected success")

    def addSubTest(self, test, subtest, err):
        unittest.TextTestResult.addSubTest(self, test, subtest, err)
        if err is not None:
            self._row(subtest, "FAIL", "".join(traceback.format_exception(*err)))


def main(argv):
    sel = None
    if "--groups" in argv:
        sel = set(argv[argv.index("--groups") + 1].split(","))
    import g0_test_env as E
    import g0_auth as GA
    expect = argv[argv.index("--expect-sha") + 1] if "--expect-sha" in argv else os.environ.get("G0_TEST_GIT_SHA")
    import g1_auth as G1A
    ident = E.verify_checkout(A003, expect, GA.FROZEN_FILES)
    g1_files = {}
    for rel in G1_KEY_FILES:
        p = os.path.join(A003, rel)
        if os.path.isfile(p):
            g1_files[rel] = {"sha256": E.sha256_file(p), "git_blob_sha1": E.git_blob_sha1(p)}
    ident["g1_key_files"] = g1_files
    g1_frozen = G1A.frozen_problems()                     # the frozen G1 criteria / preregistration text AND every frozen G0 V1..V5 file
    if g1_frozen:
        ident["problems"] = list(ident["problems"]) + ["frozen G1 / G0 files changed: %s" % "; ".join(g1_frozen)]
        ident["ok"] = False
    if os.path.exists(G1A.AUTH_DEFAULT):
        ident["problems"] = list(ident["problems"]) + ["a G1 authorization file exists at %s (the CPU tests must run without one)" % G1A.AUTH_DEFAULT]
        ident["ok"] = False
    tmp = tempfile.mkdtemp(prefix="g1_cpu_tests_")
    os.environ["TMPDIR"] = tmp
    tempfile.tempdir = tmp
    env = {**E.environment_info(), "tmpdir": tmp, "cwd": os.getcwd(), "git_sha_expected": expect, "git_head_actual": ident.get("actual_head"),
           "git_sha_match": ident.get("actual_head") == expect and expect is not None, "checkout_identity": ident}
    report = {"environment": env, "groups": [], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    import g1_test_acceptance as ACC
    full_selection = sel is None
    all_rows, all_load_errors = [], []
    if not ident["ok"]:
        report["sentinel_violations"] = list(VIOLATIONS)
        report["verdict"] = "REFUSED"
        print("REFUSED: checkout identity not verified:", "; ".join(ident["problems"]))
        if "--json" in argv:
            with open(argv[argv.index("--json") + 1], "w") as f:
                json.dump(report, f, indent=1)
        return 3
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
        all_rows.extend(rows)
        all_load_errors.extend(load_errors)
        print("%-42s run=%3d PASS=%3d FAIL=%3d ERROR=%3d SKIP=%3d load_errors=%d" % (gname, res.testsRun, counts["PASS"], counts["FAIL"], counts["ERROR"], counts["SKIP"], len(load_errors)))
    report["sentinel_violations"] = list(VIOLATIONS)
    acc = ACC.assess(full_selection, all_rows, ACC.discover_expected_ids(os.path.join(A003, "tests")), ACC.EXPECTED_TOTAL_TESTS, all_load_errors, VIOLATIONS)
    report["acceptance"] = acc
    report["verdict"] = acc["verdict"]                                  # PASS only for a FULL run in which every expected test id executed once and passed
    print("process-safety sentinel violations:", len(VIOLATIONS), "| verdict:", report["verdict"], "| scope:", acc["acceptance_scope"])
    print("acceptance: expected %d (unique %d) | executed %d (unique %d) | PASS unique %d | missing %d | unexpected %d | duplicates %d | SKIP %d | load errors %d" % (
        acc["expected_total"], acc["expected_unique"], acc["executed_rows"], acc["executed_unique"], acc["pass_unique"], len(acc["missing_ids"]), len(acc["unexpected_ids"]),
        len(acc["duplicate_ids"]), acc["counts"]["SKIP"], acc["load_errors"]))
    if not full_selection:
        print("DIAGNOSTIC ONLY: a partial (--groups) run is never an acceptance PASS")
    for reason in acc["reasons"]:
        print("  reason:", reason)
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
    return acc["exit_code"]


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except BaseException as e:                                      # never leave through Python's default exit code 1 (= a test FAIL)
        print("RUNNER-ERROR (BLOCKED): %s: %s" % (type(e).__name__, e))
        rc = 3
    sys.exit(rc)
