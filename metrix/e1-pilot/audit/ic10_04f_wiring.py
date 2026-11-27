"""ic10_04f (implementation stage C, C2 third fix commit (staged tree c7869d35, parent 2665ab10), round 1; task 2 of the
invocation, second driver). Data Auditor's own script: nothing of the Executor is imported here.

Runs the Executor's test tests/test_run_pilot.py::test_test_evaluate_begin_wiring with its three parameters once, as a
driver subprocess (C1 ruling item 5; the eval_clone fixture: throw-away clone with a bare remote, synthetic TEST rows,
random tiny models; no TEST data, no weights), with my pass-through trace plugin ic10_04_trace_plugin.py. My
expectations are printed BEFORE the run; afterwards this script compares the trace, the bare remote's history (git only)
and the clone with them. The fixture's step 2 timing gives my look-ahead 28.2 s (see ic10_04_e2e).

My expectations (per parameter; "pre" = the pre-marker part of a run: TG.code_commit < start_checks('test-evaluate') <
refuse_if_test_evaluated returning after [cat-file blob HEAD:<result>, cat-file blob HEAD:<marker>] < check_preconditions
< the device check < the four committed records < 15 checkpoint files < test_evaluation_seconds 28.2 <
before_run(28.2) < base_model < one state hash == step 3 N; no fetch / push before begin):
  crash_after_begin   2 run_test_evaluate calls on the fixture's Pilot.
    run A: pre; begin entered once with (base == N, begin_called True, marker_before_begin False, no marker file) and
      returns; control_evaluation entered twice, the 2nd raises RuntimeError (the test's crash_second raises before
      the real evaluate_model, so my evaluate_model wrapper sees only N); 1 claim (N); begun_by_this_process -> [True];
      final_record('test-evaluate', 'BLOCKED', Actual keys ['crashed', 'test_begun'], test_begun True, stop code None,
      status BLOCKED, message "crash after the TEST marker: RuntimeError('injected crash in the second TEST
      evaluation')"); commit_paths [record json, txt]; run_test_evaluate raises RuntimeError; flags after (True, False).
    run B (same Pilot, evaluate_model restored): code_commit, start_checks, then refuse_if_test_evaluated raises
      ProtocolStop (no stop code; "already started") after exactly ONE git command, cat-file blob HEAD:<result> (the
      marker file is in the working tree, so its HEAD blob is not read); no check_preconditions, no device check, no
      record read, no checkpoint hash, no look-ahead, no before_run, no base_model, no begin; begun_by_this_process ->
      [False]; no final_record, no commit_paths, no fetch / push; returns (False, 'BLOCKED'); flags after (False, None).
    remote after the fixture: exactly 2 commits: marker (A), experiment record json + txt (A; Status BLOCKED, stop code
      None, Actual ['crashed', 'test_begun'], test_begun True); no result; the clone clean at the remote's tip.
  refused_inside_begin  1 run_test_evaluate call.
    pre; begin entered once with (True, True, False, False); begin raises ProtocolStop("... injected: a dry-run push to
      origin fails") (the test's check_commit_preconditions for "the TEST marker"); network git commands of the run:
      only fetch, at least one, all inside begin (refuse_if_marker's check_checkout before the refused precondition);
      no push; no evaluation; begun_by_this_process -> [False]; no final_record, no commit_paths; returns (False,
      'BLOCKED'); flags after (True, False). Remote: 0 commits after the fixture; no marker file in the clone.
  wrong_work  1 run_test_evaluate call, on the test's own Pilot q (--work .../another_work, no device ledger).
    TG.code_commit once, then start_checks('test-evaluate') raises ProtocolStop ("device ledger"); refuse_if_test_evaluated
    not called; no check_preconditions, no device check (Pilot.device_check class method not called), no before_run,
    no base_model, no begin; begun_by_this_process -> [False]; no final_record, no commit_paths, no git fetch / push;
    returns (False, 'BLOCKED'); flags after (False, None) on q, whose work directory ends with another_work. Remote: 0
    commits after the fixture.
  pytest: "3 passed", exit 0; this repository unchanged.
usage: python -I -B ic10_04f_wiring.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import shlex
import subprocess
import time
from ia_common import run

RES = "metrix/e1-pilot/results"
MARKER = RES + "/test_evaluation_marker.json"
RESULT = RES + "/test_evaluation_result.json"
FREEZE, GATE0 = RES + "/selection_freeze_record.json", RES + "/gate0_record.json"
STEP2, STEP3 = RES + "/step2_record.json", RES + "/step3_record.json"
NODE = "metrix/e1-pilot/tests/test_run_pilot.py::test_test_evaluate_begin_wiring"
PARAMS = ("crash_after_begin", "refused_inside_begin", "wrong_work")
LOOK = round(1.0 + 15 * 0.1 + 16 * 1.0 * 3 / 2 + 17 * 0.1, 9)
NETWORK = ("fetch", "push", "pull", "ls-remote")
RGIT2 = [["cat-file", "blob", "HEAD:" + RESULT], ["cat-file", "blob", "HEAD:" + MARKER]]


def git(d, *args):
    r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r.stdout.strip() if r.returncode == 0 else None


def calls(evs, name, phase="enter"):
    return [e for e in evs if e["call"] == name and e["phase"] == phase]


def idx(evs, pred):
    for i, e in enumerate(evs):
        if pred(e):
            return i
    return None


def runs_of(evs):
    out, cur = [], None
    for ev in evs:
        if ev["call"] == "run_test_evaluate" and ev["phase"] == "enter":
            cur = []
        elif ev["call"] == "run_test_evaluate" and ev["phase"] in ("return", "raise") and cur is not None:
            out.append((cur, ev))
            cur = None
        elif cur is not None:
            cur.append(ev)
    if cur is not None:
        out.append((cur, None))
    return out


def pre_part(evs, n3):
    ib = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "enter")
    pre = evs[:ib] if ib is not None else evs
    order = [idx(pre, lambda e, n=n: e["call"] == n and e["phase"] == "enter")
             for n in ("TG.code_commit", "Pilot.start_checks", "refuse_if_test_evaluated", "check_preconditions",
                       "p.device_check")]
    reads = [e["rel"] for e in calls(pre, "R.committed_record") + calls(pre, "R.committed_json")]
    return {"order": None not in order and order == sorted(order),
            "refuse": [(e["phase"], e.get("exc")) for e in pre if e["call"] == "refuse_if_test_evaluated"
                       and e["phase"] in ("return", "raise")],
            "refuse_git": [e["args"] for e in pre if e["call"] == "git" and "refuse_if_test_evaluated" in e["stack"]],
            "network_before_begin": [e["args"][0] for e in pre if e["call"] == "git" and e["args"] and e["args"][0] in NETWORK],
            "code_commit": len(calls(pre, "TG.code_commit")),
            "start_checks": [(e["command"]) for e in calls(pre, "Pilot.start_checks")],
            "device_check": len(calls(pre, "p.device_check")) + len(calls(pre, "Pilot.device_check")),
            "check_preconditions": len(calls(pre, "check_preconditions")),
            "four_records": all(r in reads for r in (FREEZE, GATE0, STEP2, STEP3)),
            "pt_hashes": len(calls(pre, "file_sha256")),
            "look_ahead": [round(e["seconds"], 9) for e in calls(pre, "test_evaluation_seconds", "return")],
            "before_run": [round(e["next_seconds"], 9) for e in calls(pre, "p.before_run")] + [
                "class" for _ in calls(pre, "Pilot.before_run")],
            "base_model": len(calls(pre, "p.base_model")) + len(calls(pre, "Pilot.base_model")),
            "state_hash_eq_N": [e["sha256"] == n3 for e in calls(pre, "T.state_sha256", "return")]}, ib


def tail_part(evs, end, ib):
    post = evs[ib:] if ib is not None else evs
    fr = calls(evs, "final_record")
    bg = calls(evs, "begin_test_evaluation")
    i_ret = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "return")
    return {"begin": [(e["begin_called"], e["marker_before_begin"], e["marker_in_worktree"]) for e in bg],
            "begin_end": [(e["phase"], e.get("exc")) for e in evs if e["call"] == "begin_test_evaluation"
                          and e["phase"] in ("return", "raise")],
            "control_evaluation": len(calls(post, "control_evaluation")),
            "control_evaluation_raised": [e["exc"] for e in calls(post, "control_evaluation", "raise")],
            "evaluate_model": [e["checkpoint"] for e in calls(post, "evaluate_model")],
            "claims": [e["checkpoint"] for e in calls(post, "claim_checkpoint")],
            "begun_by_this_process": [e["result"] for e in calls(evs, "begun_by_this_process", "return")],
            "final_record": [(e["command"], e["status"], e["actual_keys"], e["test_begun"], (e["stop"] or {}).get("code"),
                              (e["stop"] or {}).get("status")) for e in fr],
            "commit_paths_after_begin": len(calls(evs[i_ret + 1:], "commit_paths")) if i_ret is not None else 0,
            "network": sorted({(e["args"][0], "begin_test_evaluation" in e["stack"], "final_record" in e["stack"])
                               for e in evs if e["call"] == "git" and e["args"] and e["args"][0] in NETWORK}),
            "end": None if end is None else (end["phase"], end.get("result") if end["phase"] == "return" else end.get("exc")),
            "flags_after": None if end is None else (end.get("begin_called"), end.get("marker_before_begin"))}


def main():
    repo, py, inputs, scratch = sys.argv[1:5]
    ok = True
    if os.path.exists(scratch):
        print("scratch dir %s exists: refused" % scratch)
        return False
    os.makedirs(scratch)
    base, trace_f = os.path.join(scratch, "basetemp"), os.path.join(scratch, "trace.jsonl")
    tsrc = open(os.path.join(repo, "metrix/e1-pilot/tests/test_run_pilot.py"), encoding="utf-8").read()
    par = '@pytest.mark.parametrize("how", ["crash_after_begin", "refused_inside_begin", "wrong_work"])\ndef test_test_evaluate_begin_wiring('
    print("test file: the parametrize line of test_test_evaluate_begin_wiring present: %s" % (par in tsrc))
    ok &= par in tsrc
    print("\n== my expectations: see this script's docstring (written before the run), printed here")
    print(__doc__.split("My expectations")[1].split("usage:")[0])
    sys.stdout.flush()
    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix", ":(exclude)metrix/e1-pilot/audit")
    gs0, ix0 = git(repo, *st_args), git(repo, "ls-files", "-s")
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src") + os.pathsep
               + os.path.dirname(os.path.abspath(__file__)), METRIX_INPUTS_DIR=inputs, IC10_TRACE=trace_f,
               IC10_FAULT="", PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    nodes = ["%s[%s]" % (NODE, x) for x in PARAMS]
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic10_04_trace_plugin", "--basetemp=%s" % base,
           *nodes]
    print("== driver run (once): cwd %s\n$ %s\n----- pytest stdout+stderr begin -----" % (
        repo, " ".join(shlex.quote(c) for c in cmd)))
    sys.stdout.flush()
    t0 = time.time()
    r = subprocess.run(cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout.rstrip("\n"))
    print("----- pytest stdout+stderr end ----- exit %d, %.0f s" % (r.returncode, time.time() - t0))
    passed = r.returncode == 0 and r.stdout.strip().split("\n")[-1].startswith("3 passed")
    print("3 passed, exit 0: %s" % passed)
    ok &= passed

    trace = [json.loads(x) for x in open(trace_f, encoding="utf-8").read().split("\n") if x]
    starts = [i for i, e in enumerate(trace) if e["call"] == "test" and e["phase"] == "start"]
    print("\n== trace: %d events, %d test starts %s" % (len(trace), len(starts), [trace[i]["node"].split("[")[-1] for i in starts]))
    ok &= [trace[i]["node"] for i in starts] == nodes
    if len(starts) != 3:
        return False
    for k, i in enumerate(starts):
        j = starts[k + 1] if k + 1 < len(starts) else len(trace)
        evs, start = trace[i + 1:j], trace[i]
        how = PARAMS[k]
        print("\n== %s (%d events)" % (how, len(evs)))
        for e in evs:
            print("  " + json.dumps(e, ensure_ascii=False))
        root, remote, tip0, started = start["root"], start["remote"], start["remote_tip_after_fixture"], start["started"]
        exp = sorted([RES + "/experiment_record_test-evaluate_%s.json" % started, RES + "/experiment_record_test-evaluate_%s.txt" % started])
        n3 = (json.loads(git(remote, "show", "%s:%s" % (tip0, STEP3)) or "{}").get("N") or {}).get("state_sha256")
        print("fixture: Pilot flags at the test start (%r, %r) | step 3 N %s" % (start["begin_called"], start["marker_before_begin"], n3))
        ok &= (start["begin_called"], start["marker_before_begin"]) == (False, None) and n3 is not None
        runs = runs_of(evs)
        want_n = 2 if how == "crash_after_begin" else 1
        print("run_test_evaluate calls %d (expected %d)" % (len(runs), want_n))
        ok &= len(runs) == want_n
        if len(runs) != want_n:
            continue
        full_pre = {"order": True, "refuse": [("return", None)], "refuse_git": RGIT2, "network_before_begin": [],
                    "code_commit": 1, "start_checks": ["test-evaluate"], "device_check": 1, "check_preconditions": 1,
                    "four_records": True, "pt_hashes": 15, "look_ahead": [LOOK], "before_run": [LOOK], "base_model": 1,
                    "state_hash_eq_N": [True]}
        if how == "crash_after_begin":
            (ea, enda), (eb, endb) = runs
            pa, iba = pre_part(ea, n3)
            ta = tail_part(ea, enda, iba)
            print("run A pre-marker: observed %s\n                  expected %s\n                  equal %s" % (pa, full_pre, pa == full_pre))
            ok &= pa == full_pre
            want_ta = {"begin": [(True, False, False)], "begin_end": [("return", None)], "control_evaluation": 2,
                       "control_evaluation_raised": ["RuntimeError"], "evaluate_model": ["N"], "claims": ["N"],
                       "begun_by_this_process": [True],
                       "final_record": [("test-evaluate", "BLOCKED", ["crashed", "test_begun"], True, None, "BLOCKED")],
                       "commit_paths_after_begin": 1, "end": ("raise", "RuntimeError"), "flags_after": (True, False)}
            got_ta = {k_: ta[k_] for k_ in want_ta}
            print("run A after: observed %s\n             expected %s\n             equal %s" % (got_ta, want_ta, got_ta == want_ta))
            ok &= got_ta == want_ta
            print("run A network git (verb, inside begin, inside final_record): %s" % ta["network"])
            ok &= all(b or f for _, b, f in ta["network"]) and any(v == "fetch" and f for v, _, f in ta["network"])
            stop = calls(ea, "final_record")[0]["stop"]
            print("run A stop passed to final_record: %s" % stop)
            ok &= str(stop.get("message")).startswith("crash after the TEST marker: RuntimeError('injected crash in the second "
                                                      "TEST evaluation')")
            pb, ibb = pre_part(eb, n3)
            tb = tail_part(eb, endb, ibb)
            want_pb = {"order": False, "refuse": [("raise", "ProtocolStop")], "refuse_git": [RGIT2[0]],
                       "network_before_begin": [], "code_commit": 1, "start_checks": ["test-evaluate"], "device_check": 0,
                       "check_preconditions": 0, "four_records": False, "pt_hashes": 0, "look_ahead": [], "before_run": [],
                       "base_model": 0, "state_hash_eq_N": []}
            print("run B: observed %s\n       expected %s\n       equal %s" % (pb, want_pb, pb == want_pb))
            ok &= pb == want_pb
            want_tb = {"begin": [], "control_evaluation": 0, "begun_by_this_process": [False], "final_record": [],
                       "network": [], "end": ("return", "(False, 'BLOCKED')"), "flags_after": (False, None)}
            got_tb = {k_: tb[k_] for k_ in want_tb}
            print("run B after: observed %s\n             expected %s\n             equal %s" % (got_tb, want_tb, got_tb == want_tb))
            ok &= got_tb == want_tb and len(calls(eb, "commit_paths")) == 0
            msg = [e.get("msg") for e in calls(eb, "refuse_if_test_evaluated", "raise")]
            print("run B refuse_if_test_evaluated raised: %s" % msg)
            ok &= len(msg) == 1 and "already started" in msg[0]
            want_commits = [("A", [MARKER]), ("A", exp)]
        elif how == "refused_inside_begin":
            (ea, enda), = runs
            pa, iba = pre_part(ea, n3)
            ta = tail_part(ea, enda, iba)
            print("pre-marker: observed %s\n            expected %s\n            equal %s" % (pa, full_pre, pa == full_pre))
            ok &= pa == full_pre
            want_ta = {"begin": [(True, False, False)], "begin_end": [("raise", "ProtocolStop")], "control_evaluation": 0,
                       "evaluate_model": [], "claims": [], "begun_by_this_process": [False], "final_record": [],
                       "end": ("return", "(False, 'BLOCKED')"), "flags_after": (True, False)}
            got_ta = {k_: ta[k_] for k_ in want_ta}
            print("after: observed %s\n       expected %s\n       equal %s" % (got_ta, want_ta, got_ta == want_ta))
            ok &= got_ta == want_ta and len(calls(ea, "commit_paths")) == 0
            print("network git (verb, inside begin, inside final_record): %s" % ta["network"])
            ok &= ta["network"] == [("fetch", True, False)]
            braise = [e.get("msg") for e in calls(ea, "begin_test_evaluation", "raise")]
            print("begin raised: %s" % braise)
            ok &= len(braise) == 1 and "injected: a dry-run push to origin fails" in braise[0]
            want_commits = []
        else:
            (ea, enda), = runs
            pa, iba = pre_part(ea, n3)
            ta = tail_part(ea, enda, iba)
            want_pa = {"order": False, "refuse": [], "refuse_git": [], "network_before_begin": [], "code_commit": 1,
                       "start_checks": ["test-evaluate"], "device_check": 0, "check_preconditions": 0, "four_records": False,
                       "pt_hashes": 0, "look_ahead": [], "before_run": [], "base_model": 0, "state_hash_eq_N": []}
            print("observed %s\nexpected %s\nequal %s" % (pa, want_pa, pa == want_pa))
            ok &= pa == want_pa
            want_ta = {"begin": [], "control_evaluation": 0, "begun_by_this_process": [False], "final_record": [],
                       "network": [], "end": ("return", "(False, 'BLOCKED')"), "flags_after": (False, None)}
            got_ta = {k_: ta[k_] for k_ in want_ta}
            print("after: observed %s\n       expected %s\n       equal %s" % (got_ta, want_ta, got_ta == want_ta))
            ok &= got_ta == want_ta and len(calls(ea, "commit_paths")) == 0
            sc = [e.get("msg") for e in calls(ea, "Pilot.start_checks", "raise")]
            print("start_checks raised: %s | run on work %s (another_work: %s)" % (sc, enda.get("work"),
                                                                                  str(enda.get("work")).endswith("another_work")))
            ok &= len(sc) == 1 and "device ledger" in sc[0] and str(enda.get("work")).endswith("another_work")
            want_commits = []
        new = (git(remote, "rev-list", "--reverse", "%s..main" % tip0) or "").split()
        got = []
        for c in new:
            st = [x for x in git(remote, "diff-tree", "--no-commit-id", "-r", "--name-status", "--root", c).split("\n") if x]
            got.append(("".join(sorted(set(x.split("\t")[0] for x in st))), sorted(x.split("\t", 1)[1] for x in st)))
            print("  remote commit %s: %s | %s" % (c[:12], got[-1], git(remote, "log", "-1", "--format=%s", c)))
        print("remote commits after the fixture's tip %s: %d == expected %s: %s" % (tip0[:12], len(new), want_commits, got == want_commits))
        ok &= got == want_commits
        if how == "crash_after_begin" and len(new) == 2:
            rec = json.loads(git(remote, "show", "%s:%s" % (new[1], exp[0])) or "{}").get("template", {})
            stop = (rec.get("Stop Conditions") or {}).get("stop") or {}
            act = rec.get("Actual") or {}
            print("record: Status %r | stop code %r status %r | Actual keys %s test_begun %r | message mentions the injected "
                  "crash: %s" % (rec.get("Status"), stop.get("code"), stop.get("status"), sorted(act), act.get("test_begun"),
                                 "injected crash" in str(stop.get("message"))))
            ok &= rec.get("Status") == "BLOCKED" and stop.get("code") is None and sorted(act) == ["crashed", "test_begun"] \
                and act.get("test_begun") is True and "injected crash" in str(stop.get("message"))
        tree = (git(remote, "ls-tree", "-r", "--name-only", "main") or "").split("\n")
        clean = git(root, "status", "--porcelain", "--untracked-files=all")
        print("remote: marker %s result %s | clone: marker file %s, git status %r, HEAD == remote main %s" % (
            MARKER in tree, RESULT in tree, os.path.exists(os.path.join(root, MARKER)), clean,
            git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")))
        ok &= (MARKER in tree) == (how == "crash_after_begin") and RESULT not in tree
        ok &= os.path.exists(os.path.join(root, MARKER)) == (how == "crash_after_begin")
        if how == "crash_after_begin":
            ok &= clean == "" and git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    gs1, ix1 = git(repo, *st_args), git(repo, "ls-files", "-s")
    print("\nthis repository unchanged (git status audit/ excluded, index): %s %s" % (gs1 == gs0, ix1 == ix0))
    ok &= gs1 == gs0 and ix1 == ix0
    return bool(ok)


run(main)
