"""ic10_04d (implementation stage C, C2 third fix commit (staged tree c7869d35, parent 2665ab10), round 1; task 3,
supplementary dynamic evidence; my ic9_04d with this round's changed tests). Data Auditor's own script; nothing of the
Executor is imported. Runs the Executor's tests changed in this round (and the records test) once as drivers (C1 ruling
item 5) with my pass-through plugin ic10_04d_plugin.py (generator subprocess calls; st10_over_limit results).
My expectations (written before the run):
  - every named test passes: pytest "6 passed", exit 0;
  - no generator subprocess is started during any of them;
  - test_test_generate_records_an_st10_stop_of_its_own_run now calls run_test_generate four times (no ST10 record /
    an over-limit record committed by this run / that record already at HEAD / a committed step 1 record and no device
    ledger in this --work): st10_over_limit is called on the first two calls only (the third has `before` not None;
    the fourth is refused by start_checks before the generator), returning first [] and then a list naming L4;
  - st10_over_limit is not called by any other named test.
These are the Executor's own assertions; my independent evidence for the same branches is ic10_04_static, ic10_04e and
the e2e / wiring drivers ic10_04a-f.
usage: python -I -B ic10_04d_branch_tests.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import shlex
import subprocess
from ia_common import run

T = "metrix/e1-pilot/tests/test_run_pilot.py::"
TESTS = [T + "test_test_evaluate_records_after_the_marker_and_for_st10",
         T + "test_test_generate_records_an_st10_stop_of_its_own_run",
         T + "test_st7_look_ahead_of_a_run",
         T + "test_preflight_overhead_counts",
         T + "test_test_evaluate_refuses_outside_formal_mode",
         T + "test_formal_commit_chain_through_the_freeze_record"]
GEN = T + "test_test_generate_records_an_st10_stop_of_its_own_run"


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
    print("expected (before the run): pytest '%d passed', exit 0; generator subprocess calls: none; st10_over_limit "
          "results in %s: [[], ['L4']] (2 calls); in the other tests: none" % (len(TESTS), GEN.split("::")[1]))
    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix", ":(exclude)metrix/e1-pilot/audit")
    gs0, ix0 = git(repo, *st_args), git(repo, "ls-files", "-s")
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src") + os.pathsep + os.path.dirname(os.path.abspath(__file__)),
               METRIX_INPUTS_DIR=inputs, IC10D_TRACE=trace, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic10_04d_plugin",
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
    s10 = {}
    for e in ev:
        if e.get("call") == "st10_over_limit":
            s10.setdefault(e["node"], []).append(e["result"])
    print("tests set up %d %s | generator subprocess calls %s | st10_over_limit results per test %s" % (
        len(setups), setups, gen, s10))
    passed = r.returncode == 0 and r.stdout.strip().split("\n")[-1].startswith("%d passed" % len(TESTS))
    ran = sorted(setups) == sorted(TESTS)
    s10_ok = s10 == {GEN: [[], ["L4"]]}
    print("%d passed, exit 0: %s | the named tests ran: %s | no generator subprocess: %s | st10_over_limit as expected: %s" % (
        len(TESTS), passed, ran, not gen, s10_ok))
    gs1, ix1 = git(repo, *st_args), git(repo, "ls-files", "-s")
    print("this repository unchanged (git status audit/ excluded, index): %s %s" % (gs1 == gs0, ix1 == ix0))
    return bool(passed and ran and not gen and s10_ok and gs1 == gs0 and ix1 == ix0)


run(main)
