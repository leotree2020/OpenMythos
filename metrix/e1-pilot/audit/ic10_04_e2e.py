"""ic10_04_e2e (implementation stage C, C2 third fix commit (staged tree c7869d35, parent 2665ab10), round 1; task 2 of
the invocation; my ic9_04_e2e.py updated for this round's code and test). Data Auditor's own script: nothing of the
Executor is imported here.

Runs the Executor's test tests/test_run_pilot.py::test_test_evaluate_end_to_end_once once as a driver subprocess (C1
ruling item 5; throw-away clone with a bare remote, synthetic TEST rows written by the test itself, random tiny models,
require_gpu and the device check replaced by the fixture; no TEST data, no weights), with my pass-through trace plugin
(ic10_04_trace_plugin.py) and pytest's --basetemp in my scratch directory. My expectations are printed BEFORE the run;
after it this script compares the trace, the bare remote's history (git only), the clone and the work directory with
them.

The test makes four run_test_evaluate calls (runs 0-3):
  run 0  base model replaced by a different tiny model (not N's weights of the step 3 record): refused before the
         marker (ProtocolStop without a stop code): no record, no commit;
  run 1  one checkpoint file changed: refused before the marker, no record;
  run 2  the evaluation (the test replaces before_run with a list append first);
  run 3  TEST already evaluated, and the test now replaces before_run with a function raising ST7: this round's
         refuse_if_test_evaluated (after the flag reset, code_commit and start_checks; before check_preconditions)
         raises TestAlreadyEvaluated because the result file is in the clone's working tree: no git command inside it,
         no check_preconditions, no device check, no checkpoint hash, no look-ahead, NO before_run (the ST7 function is
         never called), no base model, no begin, no record, no commit, no fetch; the Pilot's flags after it are
         (False, None).
In runs 0-2 refuse_if_test_evaluated returns after exactly two git commands, `cat-file blob HEAD:<result>` then
`cat-file blob HEAD:<marker>` (neither file in the working tree), and no fetch / push / pull / ls-remote happens before
begin. Order before begin in runs 0-2: TG.code_commit < start_checks('test-evaluate') < refuse_if_test_evaluated <
check_preconditions < the device check (the fixture's, traced) < the committed records < the checkpoint files <
test_evaluation_seconds < before_run(look-ahead) < base_model < state hash. Every fetch of run 2 happens inside begin,
finish or final_record (none inside an evaluation or a claim: ruling 2026-11-27 item 1).
My ST7 look-ahead for the fixture's step 2 timing (mean_step_s 0.1, a_factor 1, dev_evaluation_seconds 1, load_s 1,
hash_s 0.1, save_s 0.1, reload_s 0.1, file_hash_s 0.1), my model of this round (see ic10_04e): load_s (N) + 15 x
reload_s (the checkpoints) + 16 x DEV 1 x 3/2 (TEST / DEV questions per fact) + 17 state hashes x 0.1
= 1 + 1.5 + 24 + 1.7 = 28.2 s (no file-hash term).

Modes (faults injected by my plugin into run 2):
  normal                  the test as written; pytest exit 0.
  stop_after_marker       ProtocolStop(None, BLOCKED) at the 3rd evaluate_model(split="test"): begun_by_this_process
                          True -> experiment record (BLOCKED, test_begun True) committed and pushed; returns (False,
                          'BLOCKED'); the test fails at its own assertion (pytest exit 1).
  crash_after_marker      RuntimeError at the same point: record BLOCKED "crash after the TEST marker: RuntimeError(...)",
                          pushed, RuntimeError raised again (pytest exit 1).
  interrupt_after_marker  (supplementary) KeyboardInterrupt at the same point: record BLOCKED, pushed, raised again
                          (pytest interrupted, exit 2).
  st7_before_begin        (supplementary) stops.Stop("ST7", BLOCKED) from before_run(look-ahead) in run 2, before the
                          base model is loaded, TEST not evaluated: not begun, stop code ST7 -> experiment record
                          (BLOCKED, stop ST7, test_begun False) committed and pushed; no marker; returns (False,
                          'BLOCKED'); the test fails at looks[0] (pytest exit 1).
usage: python -I -B ic10_04_e2e.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)> <mode>
"""
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
STEP2, STEP3 = RES + "/step2_record.json", RES + "/step3_record.json"
FREEZE, GATE0 = RES + "/selection_freeze_record.json", RES + "/gate0_record.json"
TEST_ID = "metrix/e1-pilot/tests/test_run_pilot.py::test_test_evaluate_end_to_end_once"
SELECTED = {"F": "F3", "L": "L2", "A": "A5"}
FIXTURE_TIMING = {"mean_step_s": 0.1, "a_factor": 1.0, "dev_evaluation_seconds": 1.0, "load_s": 1.0, "hash_s": 0.1,
                  "save_s": 0.1, "reload_s": 0.1, "file_hash_s": 0.1}
MY_LOOKAHEAD = 1.0 + 15 * 0.1 + 16 * 1.0 * 3 / 2 + 17 * 0.1
TEXT_NEEDLES = ("Synthetic question", "not a TEST row", "synthetic window", "SYNTHETIC_T", "synthetic-")
ROW_KEYS = {"question", "ids", "generated_ids", "output", "normalized", "doc_id", "scores", "prediction", "top2_gap",
            "answer_index"}
MODES = ("normal", "stop_after_marker", "crash_after_marker", "interrupt_after_marker", "st7_before_begin")
AFTER_MARKER = ("stop_after_marker", "crash_after_marker", "interrupt_after_marker")


def git(d, *args):
    r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r.stdout.strip() if r.returncode == 0 else None


def my_models():
    seeds = (101, 202, 303)
    names = ["N"]
    for arm in ("F", "L", "A"):
        names += ["%s-%s-seed%d" % (arm, SELECTED[arm], s) for s in seeds]
    for arm in ("S", "Y"):
        names += ["%s-%s-seed%d" % (arm, SELECTED["F"], s) for s in seeds]
    return names


def walk_keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            walk_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, out)
    return out


def predictions(mode, models):
    pre = ("TG.code_commit once < start_checks('test-evaluate') once < refuse_if_test_evaluated returning after the git "
           "commands [cat-file blob HEAD:<result>, cat-file blob HEAD:<marker>] < check_preconditions once < device check "
           "once; committed reads freeze < Gate 0 < step 2 < step 3 before the checkpoint loop, the 15 checkpoint files "
           "(set = models[1:]) hashed, test_evaluation_seconds once with the fixture's timing returning %.6f s, "
           "before_run(next_seconds=%.6f) once, base_model once, T.state_sha256 once (the base model); no fetch / push "
           "-- all before begin" % (MY_LOOKAHEAD, MY_LOOKAHEAD))
    p = ["models TEST evaluates (my list, set): %s" % sorted(models),
         "run 0 (base model replaced by the test with a different tiny model): " + pre + "; that hash != N's of the "
         "committed step 3 record -> ProtocolStop without a stop code; begun_by_this_process -> False; no begin, no "
         "evaluation, no final_record, no commit_paths; returns (False, 'BLOCKED'); no marker",
         "run 1 (models[1]'s checkpoint file changed by the test): code_commit, start_checks, refuse_if_test_evaluated "
         "(the same two git commands), check_preconditions, device check once each, the committed freeze / Gate 0 / "
         "step 2 / step 3 records read, exactly 1 checkpoint file hashed (that one); no test_evaluation_seconds, no "
         "before_run, no base_model, no state hash, no begin, no evaluation, no commit_paths, no final_record; "
         "begun_by_this_process -> False; returns (False, 'BLOCKED'); no marker; flags after the run (False, None)"]
    begin_state = ("begin entered once with the base hash == step 3 N; at its entry the Pilot's begin_called True, "
                   "marker_before_begin False, no marker file in the clone's working tree")
    if mode == "normal":
        p += ["run 2: " + pre + "; that hash == step 3 N; " + begin_state + "; then 16 x (before_run(0.0), "
              "evaluate_model(split=test) with one state hash and one claim) in the marker's model order, no DEV "
              "evaluation; compute_test_values, judge_test, report_comparisons(test) once each after the last evaluation; "
              "finish (commit_paths [result] inside); begun_by_this_process not called; final_record('test-evaluate', "
              "'PIPELINE_NOT_QUALIFIED', stop None) writing experiment_record_test-evaluate_<start>.json/.txt, "
              "commit_paths [those two]; returns (True, 'PIPELINE_NOT_QUALIFIED')",
              "run 3 (before_run replaced by the test with an ST7 raiser): code_commit once, start_checks('test-evaluate') "
              "once, then refuse_if_test_evaluated raises TestAlreadyEvaluated with NO git command (the result file is in "
              "the working tree); no check_preconditions, no device check, no committed record read, no checkpoint hash, "
              "no test_evaluation_seconds, NO before_run call (the ST7 raiser is never reached), no base_model, no state "
              "hash, no begin, no evaluation, begun_by_this_process not called, NO final_record, NO "
              "write_experiment_record, NO commit_paths, no fetch / push; run_test_evaluate raises TestAlreadyEvaluated; "
              "the Pilot's flags after it (False, None) (the test passes, pytest exit 0)",
              "remote after the fixture: exactly 3 commits, oldest first: marker only (A), result only (A), experiment "
              "record json + txt (A, Status PIPELINE_NOT_QUALIFIED, stop null); result.marker_commit = the marker commit",
              "work: test_details/ holds 16 files <model>_test.json; the clone is clean and at the remote's tip"]
    elif mode in AFTER_MARKER:
        exc = {"stop_after_marker": "ProtocolStop", "crash_after_marker": "RuntimeError",
               "interrupt_after_marker": "KeyboardInterrupt"}[mode]
        how = ("returns (False, 'BLOCKED'); the test fails at its own assertion (pytest exit 1)" if mode == "stop_after_marker"
               else "run_test_evaluate raises %s again (pytest exit %d)" % (exc, 1 if mode == "crash_after_marker" else 2))
        msg = ("message naming the injected stop" if mode == "stop_after_marker"
               else "message 'crash after the TEST marker: %s(...)'" % exc)
        keys = "['stopped', 'test_begun']" if mode == "stop_after_marker" else "['crashed', 'test_begun']"
        p += ["run 2: " + pre + "; " + begin_state + "; evaluate_model(split=test) entered 3 times, the 3rd raises the "
              "injected %s; 2 claims, 2 state hashes after begin; no finish; begun_by_this_process -> True; "
              "final_record('test-evaluate', 'BLOCKED', Actual keys %s with test_begun True, stop code None / status "
              "BLOCKED / %s); commit_paths [experiment record json, txt]; %s" % (exc, keys, msg, how),
              "remote after the fixture: exactly 2 commits: marker only, then experiment record json + txt; no result; "
              "the record's Status BLOCKED; the clone is clean and at the remote's tip; test_details/ 2 files"]
    else:
        p += ["run 2: code_commit, start_checks, refuse_if_test_evaluated (returns), check_preconditions, device check, the "
              "four records, the 15 checkpoint files, test_evaluation_seconds "
              "%.6f s, then my plugin raises Stop ST7 in place of before_run(%.6f); no base_model, no state hash, no begin, "
              "no evaluation; begun_by_this_process -> False; stop code ST7 -> final_record('test-evaluate', 'BLOCKED', "
              "Actual keys ['stopped', 'test_begun'] with test_begun False, stop code ST7 / status BLOCKED); commit_paths "
              "[experiment record json, txt]; returns (False, 'BLOCKED'); the test fails at looks[0] (pytest exit 1)" % (
                  MY_LOOKAHEAD, MY_LOOKAHEAD),
              "remote after the fixture: exactly 1 commit: experiment record json + txt (Status BLOCKED, stop ST7); no "
              "marker, no result; the clone is clean and at the remote's tip; no test_details/ files"]
    p += ["no added blob holds the synthetic TEST text %s; the result and the experiment records have no key starting "
          "with 'general_test' and no per-question / per-window row key %s; no TEST data file in the clone or the "
          "remote; this repository unchanged" % (list(TEXT_NEEDLES), sorted(ROW_KEYS))]
    return p


def runs_of(trace):
    out, cur = [], None
    for ev in trace:
        if ev["call"] == "run_test_evaluate" and ev["phase"] == "enter":
            cur = []
        elif ev["call"] == "run_test_evaluate" and cur is not None:
            out.append((cur, ev))
            cur = None
        elif cur is not None:
            cur.append(ev)
    if cur is not None:
        out.append((cur, None))
    return out


def calls(evs, name, phase="enter"):
    return [e for e in evs if e["call"] == name and e["phase"] == phase]


def idx(evs, pred):
    for i, e in enumerate(evs):
        if pred(e):
            return i
    return None


def before_begin(evs, n3_sha):
    """The pre-marker part of a run (events before begin's enter). Returns (dict of observations, index of begin)."""
    ib = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "enter")
    ifr = idx(evs, lambda e: e["call"] == "final_record" and e["phase"] == "enter")
    pre = evs[:ib] if ib is not None else evs[:ifr] if ifr is not None else evs     # without begin: up to the record
    icp = idx(pre, lambda e: e["call"] == "check_preconditions" and e["phase"] == "return")
    own = pre[icp + 1:] if icp is not None else []      # test_evaluate's own reads: after check_preconditions returned
    reads_sorted = []
    for e in sorted(calls(own, "R.committed_record") + calls(own, "R.committed_json"), key=lambda e: e["seq"]):
        # record.committed_record calls record.committed_json: the nested read of the same path is the same read
        if not (e["call"] == "R.committed_json" and reads_sorted and reads_sorted[-1] == ("R.committed_record", e["rel"])):
            reads_sorted.append((e["call"], e["rel"]))
    reads_sorted = [rel for _, rel in reads_sorted]
    first_pt = idx(own, lambda e: e["call"] == "file_sha256" and e["phase"] == "enter")
    four = [r for r in reads_sorted if r in (FREEZE, GATE0, STEP2, STEP3)]
    i4 = [idx(own, lambda e, r=r: e["call"] in ("R.committed_record", "R.committed_json") and e["phase"] == "enter"
              and e["rel"] == r) for r in (FREEZE, GATE0, STEP2, STEP3)]
    tes = calls(pre, "test_evaluation_seconds", "return")
    tes_in = calls(pre, "test_evaluation_seconds")
    br = calls(pre, "p.before_run")
    sh = calls(pre, "T.state_sha256", "return")
    order_names = ["TG.code_commit", "Pilot.start_checks", "refuse_if_test_evaluated", "check_preconditions", "p.device_check"]
    order_idx = [idx(pre, lambda e, n=n: e["call"] == n and e["phase"] == "enter") for n in order_names]
    rit_end = [(e["phase"], e.get("exc")) for e in pre if e["call"] == "refuse_if_test_evaluated" and e["phase"] in ("return", "raise")]
    rit_git = [e["args"] for e in pre if e["call"] == "git" and "refuse_if_test_evaluated" in e["stack"]]
    net_pre = [e["args"][0] for e in pre if e["call"] == "git" and e["args"] and e["args"][0] in ("fetch", "push", "pull", "ls-remote")]
    obs = {"code_commit": len(calls(pre, "TG.code_commit")),
           "order_code_commit<start_checks<refuse<check_preconditions<device_check": None not in order_idx and order_idx == sorted(order_idx),
           "refuse_if_test_evaluated": rit_end, "refuse_git": rit_git, "network_git_before_begin": net_pre,
           "device_check": len(calls(pre, "p.device_check")),
           "check_preconditions": len(calls(pre, "check_preconditions")),
           "start_checks": [e["command"] for e in calls(pre, "Pilot.start_checks")],
           "four_records_read_in_order_before_the_checkpoint_loop": four == [FREEZE, GATE0, STEP2, STEP3]
           and None not in i4 and first_pt is not None and max(i4) < first_pt,
           "pt_hashes": sorted(e["file"] for e in calls(pre, "file_sha256")),
           "test_evaluation_seconds": [round(e["seconds"], 9) for e in tes],
           "timing_argument_is_the_fixture's": [e["timing"] == FIXTURE_TIMING for e in tes_in],
           "before_run": [round(e["next_seconds"], 9) for e in br],
           "base_model": len(calls(pre, "p.base_model")),
           "state_hashes_equal_step3_N": [e["sha256"] == n3_sha for e in sh]}
    return obs, ib


def run_end(end):
    if end is None:
        return None
    return (end["phase"], end.get("result") if end["phase"] == "return" else end.get("exc"))


def run_flags(end):
    return None if end is None else (end.get("begin_called"), end.get("marker_before_begin"))


def main():
    repo, py, inputs, scratch, mode = sys.argv[1:6]
    assert mode in MODES, mode
    ok = True
    if os.path.exists(scratch):
        print("scratch dir %s exists: refused" % scratch)
        return False
    os.makedirs(scratch)
    base, trace_f = os.path.join(scratch, "basetemp"), os.path.join(scratch, "trace.jsonl")
    tsrc = open(os.path.join(repo, "metrix/e1-pilot/tests/test_run_pilot.py"), encoding="utf-8").read()
    sel_line = 'SELECTED = {"F": "F3", "L": "L2", "A": "A5"}'
    timing_text = ('"preflight": {"timing": {"mean_step_s": 0.1, "a_factor": 1.0, "dev_evaluation_seconds": 1.0, "load_s": 1.0,\n'
                   '                                   "hash_s": 0.1, "save_s": 0.1, "reload_s": 0.1, "file_hash_s": 0.1}}')
    print("test file: SELECTED line present: %s | the fixture's step 2 timing text present: %s" % (
        sel_line in tsrc, timing_text in tsrc))
    ok &= sel_line in tsrc and timing_text in tsrc
    models = my_models()
    print("\n== my expectations (written before the run; mode %s)" % mode)
    for x in predictions(mode, models):
        print("  - " + x)
    sys.stdout.flush()

    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix",
               ":(exclude)metrix/e1-pilot/audit")
    gs_before = git(repo, *st_args)
    idx_before = git(repo, "ls-files", "-s")
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src") + os.pathsep
               + os.path.dirname(os.path.abspath(__file__)), METRIX_INPUTS_DIR=inputs, IC10_TRACE=trace_f,
               IC10_FAULT="" if mode == "normal" else mode, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic10_04_trace_plugin",
           "--basetemp=%s" % base, TEST_ID]
    print("\n== driver run (once): cwd %s" % repo)
    print("$ IC10_FAULT=%s " % env["IC10_FAULT"] + " ".join(shlex.quote(c) for c in cmd))
    print("----- pytest stdout+stderr begin -----")
    sys.stdout.flush()
    t0 = time.time()
    r = subprocess.run(cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout.rstrip("\n"))
    print("----- pytest stdout+stderr end ----- exit %d, %.0f s" % (r.returncode, time.time() - t0))
    want_rc = {"normal": 0, "interrupt_after_marker": 2}.get(mode, 1)
    print("pytest exit code %d, expected %d: %s" % (r.returncode, want_rc, r.returncode == want_rc))
    ok &= r.returncode == want_rc

    trace = [json.loads(x) for x in open(trace_f, encoding="utf-8").read().split("\n") if x]
    start = [e for e in trace if e["call"] == "test" and e["phase"] == "start"][0]
    print("\n== trace (%d events; events of the fixture before the test start omitted: %d)" % (
        len(trace), start["seq"] - 1))
    for e in trace:
        if e["seq"] >= start["seq"]:
            print("  " + json.dumps(e, ensure_ascii=False))
    root, remote, work, tip0, started = (start["root"], start["remote"], start["work"], start["remote_tip_after_fixture"],
                                         start["started"])
    EXP = [RES + "/experiment_record_test-evaluate_%s.json" % started, RES + "/experiment_record_test-evaluate_%s.txt" % started]
    print("\nfixture models as a set == my list: %s | fixture order: %s | Pilot start time %s -> experiment record %s | "
          "Pilot at the test start: begin_called %r marker_before_begin %r" % (
              sorted(start["models"]) == sorted(models), start["models"], started, EXP, start["begin_called"],
              start["marker_before_begin"]))
    ok &= sorted(start["models"]) == sorted(models) and start["models"][0] == "N"
    ok &= start["begin_called"] is False and start["marker_before_begin"] is None
    models = start["models"]
    step2 = json.loads(git(remote, "show", "%s:%s" % (tip0, STEP2)) or "{}")
    step3 = json.loads(git(remote, "show", "%s:%s" % (tip0, STEP3)) or "{}")
    n3 = (step3.get("N") or {}).get("state_sha256")
    print("remote at the fixture's tip: step 2 timing == the fixture's %s | step 3 N.state_sha256 %s" % (
        (step2.get("preflight") or {}).get("timing") == FIXTURE_TIMING, n3))
    ok &= (step2.get("preflight") or {}).get("timing") == FIXTURE_TIMING and n3 is not None
    runs = runs_of(trace)
    want_runs = 4 if mode == "normal" else 3
    print("run_test_evaluate calls: %d (expected %d)" % (len(runs), want_runs))
    ok &= len(runs) == want_runs
    if len(runs) != want_runs:
        return False
    la = round(MY_LOOKAHEAD, 9)
    rgit = [["cat-file", "blob", "HEAD:" + RESULT], ["cat-file", "blob", "HEAD:" + MARKER]]
    want_pre = {"code_commit": 1, "order_code_commit<start_checks<refuse<check_preconditions<device_check": True,
                "refuse_if_test_evaluated": [("return", None)], "refuse_git": rgit, "network_git_before_begin": [],
                "device_check": 1, "check_preconditions": 1, "start_checks": ["test-evaluate"],
                "four_records_read_in_order_before_the_checkpoint_loop": True,
                "pt_hashes": sorted(m + ".pt" for m in models[1:]), "test_evaluation_seconds": [la],
                "timing_argument_is_the_fixture's": [True], "before_run": [la], "base_model": 1,
                "state_hashes_equal_step3_N": [True]}

    def refusal(evs, end):
        obs, ib = before_begin(evs, n3)
        return dict(obs, begin=ib is not None,
                    evaluate_test=len([e for e in calls(evs, "evaluate_model") if e["split"] == "test"]),
                    begun_by_this_process=[e["result"] for e in calls(evs, "begun_by_this_process", "return")],
                    commit_paths=len(calls(evs, "commit_paths")), final_record=len(calls(evs, "final_record")),
                    end=run_end(end), flags_after=run_flags(end))

    print("\n== run 0 (base model not N's weights: refusal before the marker)")
    c0 = refusal(*runs[0])
    e0 = dict(want_pre, state_hashes_equal_step3_N=[False], begin=False, evaluate_test=0, begun_by_this_process=[False],
              commit_paths=0, final_record=0, end=("return", "(False, 'BLOCKED')"), flags_after=(False, None))
    print("observed %s\nexpected %s\nequal %s" % (c0, e0, c0 == e0))
    ok &= c0 == e0
    msg0 = [e.get("msg") for e in calls(runs[0][0], "test_evaluate", "raise")]
    print("test_evaluate raised: %s" % msg0)
    ok &= len(msg0) == 1 and "is not N's" in msg0[0] and "TEST not started" in msg0[0]

    print("\n== run 1 (changed checkpoint file: refusal before the marker)")
    c1 = refusal(*runs[1])
    e1 = {"code_commit": 1, "order_code_commit<start_checks<refuse<check_preconditions<device_check": True,
          "refuse_if_test_evaluated": [("return", None)], "refuse_git": rgit, "network_git_before_begin": [],
          "device_check": 1, "check_preconditions": 1, "start_checks": ["test-evaluate"],
          "four_records_read_in_order_before_the_checkpoint_loop": True, "pt_hashes": [models[1] + ".pt"],
          "test_evaluation_seconds": [], "timing_argument_is_the_fixture's": [], "before_run": [], "base_model": 0,
          "state_hashes_equal_step3_N": [], "begin": False, "evaluate_test": 0, "begun_by_this_process": [False],
          "commit_paths": 0, "final_record": 0, "end": ("return", "(False, 'BLOCKED')"), "flags_after": (False, None)}
    print("observed %s\nexpected %s\nequal %s" % (c1, e1, c1 == e1))
    ok &= c1 == e1

    print("\n== run 2 (the evaluation run)")
    evs, end = runs[2]
    obs, i_begin = before_begin(evs, n3)
    fr = calls(evs, "final_record")
    wer = calls(evs, "write_experiment_record", "return")
    bbp = [e["result"] for e in calls(evs, "begun_by_this_process", "return")]
    marker_commit = None
    net2 = [(e["args"][0], e["args"][1] if len(e["args"]) > 1 else None,
             next((x for x in reversed(e["stack"]) if x in ("begin_test_evaluation", "finish_test_evaluation", "final_record",
                                                             "evaluate_model", "claim_checkpoint", "control_evaluation")), None))
            for e in evs if e["call"] == "git" and e["args"] and e["args"][0] in ("fetch", "push", "pull", "ls-remote")]
    print("run 2 network git commands (verb, first argument, innermost of begin / finish / final_record / evaluate_model / "
          "claim_checkpoint / control_evaluation on the stack): %s" % net2)
    fetch_where = sorted({w for v, _, w in net2 if v == "fetch"})
    print("run 2: fetches inside %s (expected a subset of begin_test_evaluation, finish_test_evaluation, final_record; none "
          "inside an evaluation or a claim)" % fetch_where)
    ok &= set(w for _, _, w in net2) <= {"begin_test_evaluation", "finish_test_evaluation", "final_record"} and bool(fetch_where)
    print("run 2: the Pilot's flags after the run %s" % (run_flags(end),))
    if mode == "st7_before_begin":
        inj = [e for e in evs if e["phase"] == "injected"]
        want = dict(want_pre, before_run=[], base_model=0, state_hashes_equal_step3_N=[])
        ok &= run_flags(end) == (False, None)
        print("before the (absent) begin: observed %s\n                           expected %s\n                           equal %s" % (
            obs, want, obs == want))
        ok &= obs == want
        c2 = {"injected": [(e["call"], e["exc"], round(e["next_seconds"], 9)) for e in inj], "begin": i_begin is not None,
              "evaluate": len(calls(evs, "evaluate_model")), "begun_by_this_process": bbp,
              "final_record": [(e["command"], e["status"], e["actual_keys"], e["test_begun"], (e["stop"] or {}).get("code"),
                                (e["stop"] or {}).get("status")) for e in fr],
              "write_experiment_record": [e["paths"] for e in wer],
              "commit_paths": [e["rels"] for e in calls(evs, "commit_paths")], "end": run_end(end)}
        e2 = {"injected": [("p.before_run", "Stop", la)], "begin": False, "evaluate": 0, "begun_by_this_process": [False],
              "final_record": [("test-evaluate", "BLOCKED", ["stopped", "test_begun"], False, "ST7", "BLOCKED")],
              "write_experiment_record": [[os.path.basename(x) for x in EXP]], "commit_paths": [EXP],
              "end": ("return", "(False, 'BLOCKED')")}
        print("observed %s\nexpected %s\nequal %s" % (c2, e2, c2 == e2))
        print("stop passed to final_record: %s" % (fr[0]["stop"] if fr else None))
        ok &= c2 == e2 and "auditor-injected ST7" in str((fr[0]["stop"] or {}).get("message"))
    else:
        print("before begin: observed %s\n              expected %s\n              equal %s" % (obs, want_pre, obs == want_pre))
        ok &= obs == want_pre and run_flags(end) == (True, False)
        i_begin_ret = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "return")
        bg = calls(evs, "begin_test_evaluation")
        marker_commit = evs[i_begin_ret].get("marker_commit") if i_begin_ret is not None else None
        inner = evs[i_begin:i_begin_ret] if i_begin_ret is not None else []
        mc = [e["rels"] for e in calls(inner, "commit_paths")]
        bstate = [(e["base_sha256"] == n3, e["begin_called"], e["marker_before_begin"], e["marker_in_worktree"]) for e in bg]
        print("begin entered %d time(s): (base hash == step 3 N, begin_called, marker_before_begin, marker file in the "
              "working tree) at entry %s; returned marker commit %s; commit_paths inside begin %s" % (
                  len(bg), bstate, marker_commit, mc))
        ok &= bstate == [(True, True, False, False)] and mc == [[MARKER]] and marker_commit is not None
        marker = json.loads(git(remote, "show", "%s:%s" % (marker_commit, MARKER)) or "{}") if marker_commit else {}
        print("marker models (remote blob) == the fixture's list, same order: %s | marker checkpoints['N'] == step 3 N: %s" % (
            marker.get("models") == models, (marker.get("checkpoints") or {}).get("N") == n3))
        ok &= marker.get("models") == models and (marker.get("checkpoints") or {}).get("N") == n3
        post = evs[i_begin_ret + 1:] if i_begin_ret is not None else []
        ev_enter = calls(post, "evaluate_model")
        ev_test = [e["checkpoint"] for e in ev_enter if e["split"] == "test"]
        ev_dev = [e for e in ev_enter if e["split"] != "test"]
        claims = [e["checkpoint"] for e in calls(post, "claim_checkpoint")]
        post_hashes = calls(post, "T.state_sha256", "return")
        post_br = [e["next_seconds"] for e in calls(post, "p.before_run")]
        ce = calls(post, "control_evaluation")
        if mode == "normal":
            n_eval = len(models)
            i_last_ev = max(i for i, e in enumerate(evs) if e["call"] == "evaluate_model" and e["phase"] == "return")
            seq = [(n, idx(evs, lambda e, n=n: e["call"] == n and e["phase"] == "enter")) for n in
                   ("compute_test_values", "judge_test", "report_comparisons", "finish_test_evaluation", "final_record")]
            once = {n: len(calls(evs, n)) for n, _ in seq}
            pos = [i for _, i in seq]
            ordered = None not in pos and pos == sorted(pos) and pos[0] > i_last_ev
            i_fin = dict(seq)["finish_test_evaluation"]
            i_fin_ret = idx(evs, lambda e: e["call"] == "finish_test_evaluation" and e["phase"] == "return")
            fin_commits = [e["rels"] for e in calls(evs[i_fin:i_fin_ret], "commit_paths")] if None not in (i_fin, i_fin_ret) else None
            after = [e["rels"] for e in calls(evs[i_fin_ret:], "commit_paths")] if i_fin_ret is not None else None
            print("after begin: evaluate_model(split=test) %d in order == marker models %s | DEV evaluations %d | claims == "
                  "marker models %s | state hashes after begin %d | before_run after begin %s | control_evaluation %d "
                  "(split %s)" % (len(ev_test), ev_test == models, len(ev_dev), claims == models, len(post_hashes), post_br,
                                  len(ce), sorted(set(e["split"] for e in ce))))
            ok &= ev_test == models and not ev_dev and claims == models and len(post_hashes) == n_eval \
                and post_br == [0.0] * n_eval and len(ce) == n_eval and set(e["split"] for e in ce) == {"test"}
            print("once each %s | order compute < judge < report < finish < final_record, after the last evaluation: %s | "
                  "commit_paths inside finish %s | final_record %s | write_experiment_record returned %s | commit_paths "
                  "after finish %s | begun_by_this_process calls %s" % (
                      once, ordered, fin_commits, [(e["command"], e["status"], e["stop"]) for e in fr],
                      [e["paths"] for e in wer], after, bbp))
            ok &= set(once.values()) == {1} and ordered and fin_commits == [[RESULT]] and after == [EXP] and bbp == []
            ok &= [(e["command"], e["status"], e["stop"]) for e in fr] == [("test-evaluate", "PIPELINE_NOT_QUALIFIED", None)]
            ok &= [e["paths"] for e in wer] == [[os.path.basename(x) for x in EXP]]
            print("run 2 ends %s (expected return (True, 'PIPELINE_NOT_QUALIFIED'))" % (run_end(end),))
            ok &= run_end(end) == ("return", "(True, 'PIPELINE_NOT_QUALIFIED')")

            print("\n== run 3 (second evaluation attempt; before_run replaced by the test with an ST7 raiser)")
            evs3, end3 = runs[3]
            c3 = refusal(evs3, end3)
            c3.update(order_head=[e["call"] for e in evs3 if e["phase"] == "enter"][:4],
                      write_experiment_record=len(calls(evs3, "write_experiment_record")),
                      network_git=[e["args"][0] for e in evs3 if e["call"] == "git" and e["args"]
                                   and e["args"][0] in ("fetch", "push", "pull", "ls-remote")],
                      committed_reads=len(calls(evs3, "R.committed_json")) + len(calls(evs3, "R.committed_record")))
            e3 = {"code_commit": 1, "order_code_commit<start_checks<refuse<check_preconditions<device_check": False,
                  "refuse_if_test_evaluated": [("raise", "TestAlreadyEvaluated")], "refuse_git": [],
                  "network_git_before_begin": [], "device_check": 0, "check_preconditions": 0,
                  "start_checks": ["test-evaluate"], "four_records_read_in_order_before_the_checkpoint_loop": False,
                  "pt_hashes": [], "test_evaluation_seconds": [], "timing_argument_is_the_fixture's": [], "before_run": [],
                  "base_model": 0, "state_hashes_equal_step3_N": [], "begin": False, "evaluate_test": 0,
                  "begun_by_this_process": [], "commit_paths": 0, "final_record": 0,
                  "end": ("raise", "TestAlreadyEvaluated"), "flags_after": (False, None),
                  "order_head": ["test_evaluate", "TG.code_commit", "Pilot.start_checks", "refuse_if_test_evaluated"],
                  "write_experiment_record": 0, "network_git": [], "committed_reads": 0}
            print("observed %s\nexpected %s\nequal %s" % (c3, e3, c3 == e3))
            print("(the order flag is False because check_preconditions and the device check are absent)")
            ok &= c3 == e3
            msg3 = [e.get("msg") for e in calls(evs3, "refuse_if_test_evaluated", "raise")]
            st7_calls = [e for e in evs3 if e["call"] == "p.before_run"]
            print("refuse_if_test_evaluated raised: %s | p.before_run events in run 3 (the ST7 raiser): %d" % (msg3, len(st7_calls)))
            ok &= len(msg3) == 1 and "TEST was evaluated" in msg3[0] and not st7_calls
        else:
            inj = [e for e in post if e["phase"] == "injected"]
            stop = fr[0]["stop"] if fr else None
            after = [e["rels"] for e in calls(post, "commit_paths")]
            print("after begin: evaluate_model(split=test) entered %d %s | injected %s | claims %s | state hashes after begin "
                  "%d | finish %d | begun_by_this_process %s | final_record %s | write_experiment_record returned %s | "
                  "commit_paths after begin %s" % (
                      len(ev_test), ev_test, [(e["fault"], e["exc"]) for e in inj], claims, len(post_hashes),
                      len(calls(evs, "finish_test_evaluation")), bbp,
                      [(e["command"], e["status"], e["actual_keys"], e["test_begun"]) for e in fr],
                      [e["paths"] for e in wer], after))
            print("stop passed to final_record: %s" % stop)
            exc = {"stop_after_marker": "ProtocolStop", "crash_after_marker": "RuntimeError",
                   "interrupt_after_marker": "KeyboardInterrupt"}[mode]
            akeys = ["stopped", "test_begun"] if mode == "stop_after_marker" else ["crashed", "test_begun"]
            ok &= ev_test == models[:3] and [(e["exc"]) for e in inj] == [exc] and claims == models[:2] \
                and len(post_hashes) == 2 and not calls(evs, "finish_test_evaluation") and after == [EXP] and bbp == [True]
            ok &= [(e["command"], e["status"], e["actual_keys"], e["test_begun"]) for e in fr] == [
                ("test-evaluate", "BLOCKED", akeys, True)]
            ok &= [e["paths"] for e in wer] == [[os.path.basename(x) for x in EXP]]
            ok &= stop is not None and stop.get("code") is None and stop.get("status") == "BLOCKED"
            if mode == "stop_after_marker":
                ok &= "auditor-injected stop" in str(stop.get("message"))
                want_end = ("return", "(False, 'BLOCKED')")
            else:
                ok &= str(stop.get("message")).startswith("crash after the TEST marker: %s(" % exc) \
                    and "auditor-injected" in str(stop.get("message"))
                want_end = ("raise", exc)
            print("run 2 ends %s (expected %s)" % (run_end(end), want_end))
            ok &= run_end(end) == want_end

    print("\n== the bare remote (git only)")
    new = (git(remote, "rev-list", "--reverse", "%s..main" % tip0) or "").split()
    want = {"normal": [("A", [MARKER]), ("A", [RESULT]), ("A", sorted(EXP))],
            "st7_before_begin": [("A", sorted(EXP))]}.get(mode, [("A", [MARKER]), ("A", sorted(EXP))])
    got, blobs = [], {}
    for c in new:
        st = [x for x in git(remote, "diff-tree", "--no-commit-id", "-r", "--name-status", "--root", c).split("\n") if x]
        files = sorted(x.split("\t", 1)[1] for x in st)
        kinds = sorted(set(x.split("\t", 1)[0] for x in st))
        got.append(("".join(kinds), files))
        print("  commit %s parent %s: %s %s | %s" % (c[:12], (git(remote, "rev-parse", c + "^") or "")[:12], kinds, files,
                                                     git(remote, "log", "-1", "--format=%s", c)))
        for f in files:
            blobs[(c, f)] = git(remote, "show", "%s:%s" % (c, f)) or ""
    print("commits after the fixture's tip %s: %d; (change kind, files) per commit == expected %s: %s" % (
        tip0[:12], len(new), want, got == want))
    ok &= got == want
    if new and marker_commit is not None:
        print("first commit after the fixture == the marker commit begin returned: %s" % (new[0] == marker_commit))
        ok &= new[0] == marker_commit
    tree = (git(remote, "ls-tree", "-r", "--name-only", "main") or "").split("\n")
    print("remote tree: marker present %s | result present %s" % (MARKER in tree, RESULT in tree))
    ok &= (MARKER in tree) == (mode != "st7_before_begin") and (RESULT in tree) == (mode == "normal")
    hits = {"%s %s" % (k[0][:8], k[1]): [n for n in TEXT_NEEDLES if n in v] for k, v in blobs.items()}
    print("synthetic TEST text in the blobs added after the fixture: %s" % hits)
    ok &= not any(hits.values())
    bad_paths = [x for x in tree if x.endswith(("test_qa.jsonl", "general_test.jsonl"))
                 or (x.startswith("metrix/e1-pilot/") and x.endswith("_test.json"))]
    print("remote tree: TEST data file names, or *_test.json under metrix/e1-pilot/: %s" % bad_paths)
    ok &= not bad_paths
    exp_status = []
    for (c, f), v in blobs.items():
        if f.endswith(".json") and f != MARKER:
            obj = json.loads(v)
            keys = walk_keys(obj, set())
            gen = sorted(k for k in keys if str(k).startswith("general_test"))
            rowk = sorted(ROW_KEYS & keys)
            print("  %s %s: keys starting with 'general_test' %s | per-question / per-window row keys %s" % (c[:8], f, gen, rowk))
            ok &= not gen and not rowk
            if f == RESULT:
                print("  result: marker_commit == marker commit %s | summaries == the 16 models %s | final_status %r" % (
                    obj.get("marker_commit") == marker_commit, sorted(obj.get("summaries", {})) == sorted(models),
                    (obj.get("final") or {}).get("final_status")))
                ok &= obj.get("marker_commit") == marker_commit and sorted(obj.get("summaries", {})) == sorted(models)
                ok &= (obj.get("final") or {}).get("final_status") == "PIPELINE_NOT_QUALIFIED"
            if f == EXP[0]:
                t = obj.get("template", {})
                stop = (t.get("Stop Conditions") or {}).get("stop")
                act = t.get("Actual") or {}
                exp_status.append((t.get("Status"), None if stop is None else (stop.get("code"), stop.get("status"),
                                                                                 str(stop.get("message"))),
                                   sorted(act.keys()), act.get("test_begun", "<absent>"), t.get("Experiment ID")))
                print("  experiment record in %s: Status %r | stop %s | Actual keys %s, test_begun %r | Experiment ID %r" % (
                    c[:8], t.get("Status"), stop, sorted(act.keys()), act.get("test_begun", "<absent>"), t.get("Experiment ID")))
    # (Status, stop code, stop status, stop message prefix, Actual keys, test_begun)
    e_st = {"normal": [("PIPELINE_NOT_QUALIFIED", None, None, None, ["final", "interpretation", "result_commit", "values"],
                        "<absent>")],
            "stop_after_marker": [("BLOCKED", None, "BLOCKED", "BLOCKED: auditor-injected stop after the TEST marker",
                                   ["stopped", "test_begun"], True)],
            "crash_after_marker": [("BLOCKED", None, "BLOCKED", "crash after the TEST marker: RuntimeError('auditor-injected crash",
                                    ["crashed", "test_begun"], True)],
            "interrupt_after_marker": [("BLOCKED", None, "BLOCKED",
                                        "crash after the TEST marker: KeyboardInterrupt('auditor-injected interrupt",
                                        ["crashed", "test_begun"], True)],
            "st7_before_begin": [("BLOCKED", "ST7", "BLOCKED", "ST7 -> BLOCKED: auditor-injected ST7 look-ahead",
                                  ["stopped", "test_begun"], False)]}[mode]
    got_st = []
    for (st, stop, ak, tb, _), exp_ in zip(exp_status, e_st + [(None,) * 6] * len(exp_status)):
        pref = exp_[3]
        if stop is None:
            got_st.append((st, None, None, None, ak, tb))
        else:
            got_st.append((st, stop[0], stop[1], pref if pref is not None and stop[2].startswith(pref) else stop[2], ak, tb))
    print("experiment records (Status, stop code, stop status, message prefix, Actual keys, test_begun) oldest first %s | "
          "expected %s | equal %s" % (got_st, e_st, got_st == e_st))
    ok &= got_st == e_st
    clone_files = [os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) if "/.git" not in d + "/"
                   for f in fs]
    clone_bad = [x for x in clone_files if x.endswith(("test_qa.jsonl", "general_test.jsonl"))
                 or (x.startswith("metrix/e1-pilot/") and x.endswith("_test.json"))]
    clean = git(root, "status", "--porcelain", "--untracked-files=all")
    at_tip = git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    print("clone: TEST data file names or *_test.json under metrix/e1-pilot/: %s | git status --porcelain %r | HEAD == "
          "remote main: %s" % (clone_bad, clean, at_tip))
    ok &= not clone_bad and clean == "" and at_tip
    wd = os.path.join(work, "test_details")
    det = sorted(os.listdir(wd)) if os.path.isdir(wd) else []
    n_det = {"normal": len(models), "st7_before_begin": 0}.get(mode, 2)
    want_det = sorted("%s_test.json" % m for m in models[:n_det])
    inside = os.path.realpath(work).startswith(os.path.realpath(root) + os.sep)
    print("work %s (inside the clone: %s): test_details %s == expected: %s" % (work, inside, det, det == want_det))
    ok &= not inside and det == want_det

    gs_after = git(repo, *st_args)
    idx_after = git(repo, "ls-files", "-s")
    print("\nthis repository: git status --porcelain --ignored --untracked-files=all -- metrix (audit/ excluded) unchanged by "
          "the run: %s | index entries unchanged: %s" % (gs_after == gs_before, idx_after == idx_before))
    if gs_after != gs_before:
        print("  before:\n%s\n  after:\n%s" % (gs_before, gs_after))
    ok &= gs_after == gs_before and idx_after == idx_before
    return bool(ok)


run(main)
