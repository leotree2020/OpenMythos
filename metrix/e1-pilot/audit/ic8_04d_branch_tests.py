"""ic8_04d (implementation stage C, C2 fix commit (staged tree b40224e6, parent 1900b1fe), round 1; task 4,
supplementary dynamic evidence for the branches read statically in ic8_04_static b / e). Data Auditor's own script;
nothing of the Executor is imported. Runs two of the Executor's tests once as drivers (C1 ruling item 5) with my
pass-through plugin ic8_04d_plugin.py, which logs every subprocess.run whose command names metrix_e1.test_data:
  tests/test_run_pilot.py::test_smoke_step8_refuses_where_formal_records_exist
      my expectation: passes; NO generator subprocess is started during it (the checkout holds a committed Gate 0 record:
      step8_smoke_refusal raises ImplementationFail before subprocess.run).
  tests/test_run_pilot.py::test_test_evaluate_records_after_the_marker_and_for_st10
      my expectation: passes (its assertions: before the marker no record except for an ST10 stop; after it a record for
      a stop and for a crash, the crash re-raised); no generator subprocess.
These are the Executor's own assertions; my independent evidence for the same branches is ic8_04_static (b, e) and the
e2e runs ic8_04a-c. Expected pytest summary: "2 passed", exit 0; generator subprocess calls: none.
usage: python -I -B ic8_04d_branch_tests.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import shlex
import subprocess
from ia_common import run

TESTS = ["metrix/e1-pilot/tests/test_run_pilot.py::test_smoke_step8_refuses_where_formal_records_exist",
         "metrix/e1-pilot/tests/test_run_pilot.py::test_test_evaluate_records_after_the_marker_and_for_st10"]


def git(d, *args):
    r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r.stdout


def main():
    repo, py, inputs, scratch = sys.argv[1:5]
    if os.path.exists(scratch):
        print("scratch dir %s exists: refused" % scratch)
        return False
    os.makedirs(scratch)
    trace = os.path.join(scratch, "trace.jsonl")
    open(trace, "w").close()
    print("expected (before the run): pytest '2 passed', exit 0; generator subprocess calls during the two tests: none")
    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix", ":(exclude)metrix/e1-pilot/audit")
    gs0, ix0 = git(repo, *st_args), git(repo, "ls-files", "-s")
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src") + os.pathsep + os.path.dirname(os.path.abspath(__file__)),
               METRIX_INPUTS_DIR=inputs, IC8D_TRACE=trace, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic8_04d_plugin",
           "--basetemp=%s" % os.path.join(scratch, "basetemp"), *TESTS]
    print("$ " + " ".join(shlex.quote(c) for c in cmd))
    print("----- pytest stdout+stderr begin -----")
    sys.stdout.flush()
    r = subprocess.run(cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout.rstrip("\n"))
    print("----- pytest stdout+stderr end ----- exit %d" % r.returncode)
    ev = [json.loads(x) for x in open(trace, encoding="utf-8").read().split("\n") if x]
    for e in ev:
        print("  trace %s" % json.dumps(e))
    gen = [e for e in ev if "generator_command" in e]
    setups = [e["node"] for e in ev if e.get("event") == "setup"]
    print("tests set up %s | generator subprocess calls %s" % (setups, gen))
    passed = r.returncode == 0 and r.stdout.strip().split("\n")[-1].startswith("2 passed")
    print("2 passed, exit 0: %s | the two tests ran: %s | no generator subprocess: %s" % (
        passed, sorted(s.split("::")[1] for s in setups) == sorted(t.split("::")[1] for t in TESTS), not gen))
    gs1, ix1 = git(repo, *st_args), git(repo, "ls-files", "-s")
    print("this repository unchanged (git status audit/ excluded, index): %s %s" % (gs1 == gs0, ix1 == ix0))
    return bool(passed and not gen and sorted(s.split("::")[1] for s in setups) == sorted(t.split("::")[1] for t in TESTS)
                and gs1 == gs0 and ix1 == ix0)


run(main)
