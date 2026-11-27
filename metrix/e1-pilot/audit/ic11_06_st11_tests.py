"""ic11_06 (implementation stage C, C4 code commit, round 1; task 3 of the invocation): the Executor's test
tests/test_run_pilot.py::test_formal_st11_reads_b17_plus_the_checkpoint_overhead[<param>] run once as a driver (C1 ruling
item 5; one parameter per invocation of this script), with my pass-through plugin ic11_06_plugin.py, pytest's
--basetemp under my scratch directory (so that the test's clone and bare remote stay for my inspection). My own
reading afterwards uses git commands only (nothing of the Executor imported).

The test (as staged): formal on a clone with a bare remote, the real preflight with train_run at 1 smoke step,
CP.estimate_total_hours replaced to give 3.0 h (its parts real), P.checkpoint_overhead_seconds replaced to give 1801 s
(sum_over_bound) or 1800 s (sum_at_bound) with the real counts, P.step3 replaced by a RuntimeError("injected after
step 2"); the real st11_estimate_hours and stops.st11.

My expectations (printed before the run; derived from my reading of the protocol (ST11: stop above 3.5 h, BLOCKED per
B16 / ST11 row "停止;报告 Owner") and of the code paths: stop_in_step commits the step record with "stopped" then
re-raises; run_gate turns a stop into (False, status) and an exception into the experiment record and re-raises):
  sum_over_bound: estimate 3.0 + 1801/3600 = 3.50027... > 3.5 -> ST11 raised (Stop ST11 BLOCKED, message
    "preflight estimate 3.500 h > 3.5 h"); run_gate returns (False, "BLOCKED"); remote: step 2 record with
    stopped {code ST11, status BLOCKED}, no step 3 record, experiment record Status BLOCKED with stop code ST11.
  sum_at_bound: estimate 3.0 + 1800/3600 = 3.5 exactly (0.5 is exact in binary) -> not above the bound, no stop;
    run_gate raises RuntimeError("injected after step 2"); remote: step 2 record without "stopped", st11 "within bound",
    no step 3 record, experiment record Status NOT_TESTED with the injected message.
  both: st11_estimate_hours called once with (3.0, overhead); stops.st11 called once with that value and bound 3.5;
    the clone clean and at the remote's main; pytest "1 passed", exit 0; this repository unchanged.
usage: python -I -B ic11_06_st11_tests.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)>
       <sum_over_bound|sum_at_bound>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob
import json
import shlex
import subprocess
from ia_common import run

NODE = "metrix/e1-pilot/tests/test_run_pilot.py::test_formal_st11_reads_b17_plus_the_checkpoint_overhead[%s]"
RES = "metrix/e1-pilot/results"


def git(d, *args):
    r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r.stdout, r.returncode


def main():
    repo, py, inputs, scratch, param = sys.argv[1:6]
    if param not in ("sum_over_bound", "sum_at_bound") or os.path.exists(scratch):
        print("bad parameter or scratch dir %s exists: refused" % scratch)
        return False
    os.makedirs(scratch)
    over = param == "sum_over_bound"
    overhead = 1801.0 if over else 1800.0
    est = 3.0 + overhead / 3600.0
    exp = {"estimate": est, "st11_triggers": est > 3.5, "run_gate": ("returns [False, 'BLOCKED']" if over else
                                                                  "raises RuntimeError('injected after step 2')"),
           "step2_stopped": {"code": "ST11", "status": "BLOCKED"} if over else None,
           "step2_st11_field": None if over else "within bound",
           "stop_message_contains": "preflight estimate %.3f h > 3.5 h" % est if over else None,
           "experiment_status": "BLOCKED" if over else "NOT_TESTED", "experiment_stop_code": "ST11" if over else None,
           "step3_record": False}
    print("== my expectation for [%s] (before the run)" % param)
    print(json.dumps(exp, indent=1, sort_keys=True))
    print("   estimate repr %r; > 3.5: %s" % (est, est > 3.5))
    sys.stdout.flush()

    trace = os.path.join(scratch, "trace.jsonl")
    open(trace, "w").close()
    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix", ":(exclude)metrix/e1-pilot/audit")
    gs0, ix0 = git(repo, *st_args)[0], git(repo, "ls-files", "-s")[0]
    head0 = git(repo, "rev-parse", "HEAD")[0]
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src") + os.pathsep + os.path.dirname(os.path.abspath(__file__)),
               METRIX_INPUTS_DIR=inputs, IC11_TRACE=trace, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    base = os.path.join(scratch, "basetemp")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic11_06_plugin", "-rA", "--basetemp=%s" % base,
           NODE % param]
    print("\n$ (cwd %s) PYTHONPATH=%s %s" % (repo, env["PYTHONPATH"], " ".join(shlex.quote(c) for c in cmd)))
    print("----- pytest stdout+stderr begin -----")
    sys.stdout.flush()
    r = subprocess.run(cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout.rstrip("\n"))
    print("----- pytest stdout+stderr end ----- exit %d" % r.returncode)
    ok = r.returncode == 0 and r.stdout.strip().split("\n")[-1].startswith("1 passed")

    print("\n== trace (my plugin)")
    ev = [json.loads(x) for x in open(trace, encoding="utf-8").read().split("\n") if x]
    for e in ev:
        print("  %s" % json.dumps(e, sort_keys=True))
    sums = [e for e in ev if e.get("call") == "st11_estimate_hours"]
    st11 = [e for e in ev if e.get("call") == "stops.st11"]
    gate = [e for e in ev if e.get("call") == "run_gate" and ("returned" in e or "raised" in e)]
    root = [e["root"] for e in ev if e.get("call") == "run_gate" and "root" in e]
    print("  st11_estimate_hours calls %d, args/result %s | expected one call (3.0, %r) -> %r" % (
        len(sums), [(e["b17_hours"], e["overhead_seconds"], e["result_repr"]) for e in sums], overhead, est))
    ok &= len(sums) == 1 and sums[0]["b17_hours"] == 3.0 and sums[0]["overhead_seconds"] == overhead and sums[0]["result"] == est
    print("  stops.st11 calls %d: %s" % (len(st11), [(e["estimate_repr"], e["bound"], e.get("raised"), e.get("stop"),
                                                     e.get("status"), e.get("message")) for e in st11]))
    ok &= len(st11) == 1 and st11[0]["estimate_hours"] == est and st11[0]["bound"] == 3.5
    if over:
        ok &= st11[0].get("raised") == "Stop" and st11[0].get("stop") == "ST11" and st11[0].get("status") == "BLOCKED" \
            and exp["stop_message_contains"] in st11[0].get("message", "")
    else:
        ok &= "raised" not in st11[0]
    print("  run_gate outcome %s" % gate)
    if over:
        ok &= len(gate) == 1 and gate[0].get("returned") == [False, "BLOCKED"]
    else:
        ok &= len(gate) == 1 and gate[0].get("raised") == "RuntimeError" and gate[0].get("message") == "injected after step 2"

    print("\n== the test's bare remote and clone (my git reading)")
    remotes = sorted(set(os.path.realpath(x) for x in glob.glob(os.path.join(base, "*", "remote.git"))))   # pytest adds a "<name>current" symlink
    print("  bare remotes under basetemp: %s" % remotes)
    if len(remotes) != 1 or len(root) != 1:
        print("  cannot locate exactly one remote and one clone")
        return False
    remote, clone = remotes[0], root[0]
    log = git(remote, "log", "--format=%h %s", "--name-status", "%s..main" % head0.strip())[0]
    print("  git log --name-status <this repository's HEAD>..main (remote; the commits made in the test):\n" + "\n".join("    " + x for x in log.rstrip("\n").split("\n")))
    tree = git(remote, "ls-tree", "-r", "--name-only", "main")[0].split("\n")
    res = sorted(x for x in tree if x.startswith(RES + "/"))
    print("  files under %s at the remote's main: %s" % (RES, res))
    has3 = RES + "/step3_record.json" in tree
    s2 = json.loads(git(remote, "show", "main:%s/step2_record.json" % RES)[0])
    pre = s2["preflight"]
    mine = pre["b17_estimate_hours"] + pre["checkpoint_overhead"]["seconds"] / 3600.0
    print("  step2 record: b17_estimate_hours %r | checkpoint_overhead.seconds %r | st11_estimate_hours %r (my sum %r, equal "
          "%s) | st11_bound_hours %r | st11 %r | st11_reads %r | stopped %s" % (
              pre["b17_estimate_hours"], pre["checkpoint_overhead"]["seconds"], pre["st11_estimate_hours"], mine,
              mine == pre["st11_estimate_hours"], pre["st11_bound_hours"], pre.get("st11"), pre.get("st11_reads"),
              s2.get("stopped")))
    ok &= pre["b17_estimate_hours"] == 3.0 and pre["checkpoint_overhead"]["seconds"] == overhead
    ok &= mine == pre["st11_estimate_hours"] == est and pre["st11_bound_hours"] == 3.5
    print("  checkpoint_overhead.counts %s" % json.dumps(pre["checkpoint_overhead"]["counts"], sort_keys=True))
    ok &= pre["checkpoint_overhead"]["counts"] == {"base_loads": 32, "checkpoints": 30, "checkpoint_reloads": 18,
                                                   "test_state_hashes": 17, "test_file_hashes": 15, "test_models": 16}
    if over:
        st = s2.get("stopped") or {}
        ok &= st.get("code") == "ST11" and st.get("status") == "BLOCKED" and exp["stop_message_contains"] in st.get("message", "")
    else:
        ok &= "stopped" not in s2 and pre.get("st11") == "within bound"
    exps = [x for x in tree if x.startswith(RES + "/experiment_record_formal_") and x.endswith(".json")]
    print("  experiment records (json) %s | step3 record present %s" % (exps, has3))
    ok &= len(exps) == 1 and not has3
    if len(exps) == 1:
        rec = json.loads(git(remote, "show", "main:%s" % exps[0])[0])
        tpl = rec["template"]
        sc = tpl["Stop Conditions"]
        print("  experiment record Status %r | Stop Conditions stop %s" % (tpl["Status"], json.dumps(sc.get("stop"), ensure_ascii=False)))
        ok &= tpl["Status"] == exp["experiment_status"]
        if over:
            ok &= (sc.get("stop") or {}).get("code") == "ST11"
        else:
            ok &= "injected after step 2" in json.dumps(sc.get("stop"))
    porc = git(clone, "status", "--porcelain")[0]
    ch, rh = git(clone, "rev-parse", "HEAD")[0].strip(), git(remote, "rev-parse", "main")[0].strip()
    print("  clone %s: status --porcelain %r | HEAD %s == remote main %s: %s" % (clone, porc, ch[:12], rh[:12], ch == rh))
    ok &= porc == "" and ch == rh

    gs1, ix1 = git(repo, *st_args)[0], git(repo, "ls-files", "-s")[0]
    print("\nthis repository unchanged (git status audit/ excluded, index, HEAD): %s %s %s" % (
        gs1 == gs0, ix1 == ix0, git(repo, "rev-parse", "HEAD")[0] == head0))
    ok &= gs1 == gs0 and ix1 == ix0 and git(repo, "rev-parse", "HEAD")[0] == head0
    return bool(ok)


run(main)
