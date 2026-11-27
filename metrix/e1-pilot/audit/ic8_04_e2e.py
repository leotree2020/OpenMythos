"""ic8_04_e2e (implementation stage C, C2 fix commit (staged tree b40224e6, parent 1900b1fe), round 1; task 3 of the
invocation, dynamic part; my ic7_04_e2e.py rewritten for the changed code). Data Auditor's own script: nothing of the
Executor is imported here.

Runs the Executor's test tests/test_run_pilot.py::test_test_evaluate_end_to_end_once once as a driver subprocess (C1
ruling item 5; throw-away clone with a bare remote, synthetic TEST rows written by the test itself, random tiny models,
require_gpu replaced; no TEST data, no weights), with my pass-through trace plugin (ic8_04_trace_plugin.py) and pytest's
--basetemp in my scratch directory. My expectations are printed BEFORE the run; after it this script compares the trace,
the bare remote's history (git only), the clone and the work directory with them.

New in this round (the fix): before the marker test_evaluate also reads the committed step 2 and step 3 records, runs
the continuity check, computes the ST7 look-ahead of the whole TEST evaluation from the committed step 2 timing and
passes it to before_run, and compares the base model's state hash with N's of the step 3 record; run_test_evaluate
records a crash after the marker (BLOCKED) and re-raises it; the experiment record's file name carries the Pilot's start
time. My look-ahead for the fixture's timing (mean_step_s 0.1, a_factor 1, dev_evaluation_seconds 1, load_s 1, hash_s
0.1, save_s 0.1, reload_s 0.1, file_hash_s 0.1): 16 models x (load 1 + DEV 1 x 3/2 TEST/DEV questions per fact) + 17
state hashes x 0.1 + 15 files x 0.1 = 43.2 s (counts and questions per fact: mine, see ic8_06 D).

Modes:
  normal              the test as written: run 1 refusal before the marker (changed checkpoint file), run 2 one
                      evaluation, run 3 TestAlreadyEvaluated. My reading of the fixed run_test_evaluate predicts that
                      run 3, on a clone whose working tree holds the marker (pulled), takes the `except Exception`
                      branch: a BLOCKED experiment record "crash after the TEST marker: TestAlreadyEvaluated(...)" is
                      written under the SAME file name as run 2's (the test reuses one Pilot, so one start time),
                      committed and pushed, then TestAlreadyEvaluated is re-raised (the test still passes).
  stop_after_marker   the plugin raises ProtocolStop(BLOCKED) at the 3rd evaluate_model(split="test"): the experiment
                      record is written, committed and pushed (BLOCKED); the test fails at its own assertion.
  crash_after_marker  the plugin raises RuntimeError at the 3rd evaluate_model(split="test"): NOW (MAJOR 4 / IC7-M1)
                      the experiment record is written, committed and pushed with status BLOCKED, then RuntimeError is
                      raised again (pytest exit 1).
usage: python -I -B ic8_04_e2e.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)> <mode>
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
MY_LOOKAHEAD = 16 * (1.0 + 1.0 * 3 / 2) + 17 * 0.1 + 15 * 0.1
TEXT_NEEDLES = ("Synthetic question", "not a TEST row", "synthetic window", "SYNTHETIC_T", "synthetic-")
ROW_KEYS = {"question", "ids", "generated_ids", "output", "normalized", "doc_id", "scores", "prediction", "top2_gap",
            "answer_index"}


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
    pre = ("check_preconditions once, start_checks('test-evaluate') once, committed reads freeze < Gate 0 < step 2 < "
           "step 3 before the checkpoint loop, the 15 checkpoint files (set = models[1:]) hashed, "
           "test_evaluation_seconds once with the fixture's timing returning %.6f s, before_run(next_seconds=%.6f) once, "
           "T.state_sha256 once (the base model) -- all before begin; that hash == begin's base-model argument == the "
           "marker's N hash == N.state_sha256 of the committed step 3 record" % (MY_LOOKAHEAD, MY_LOOKAHEAD))
    p = ["models TEST evaluates (my list, set): %s" % sorted(models),
         "run 1 (models[1]'s checkpoint file changed by the test): check_preconditions once, start_checks once, the "
         "committed freeze / Gate 0 / step 2 / step 3 records read, exactly 1 checkpoint file hashed (that one); no "
         "test_evaluation_seconds, no before_run, no state hash, no begin, no evaluation, no commit_paths, no "
         "final_record; returns (False, 'BLOCKED'); no marker"]
    if mode == "normal":
        p += ["run 2: " + pre + "; then 16 x (before_run(0.0), evaluate_model(split=test) with one state hash and one "
              "claim) in the marker's model order, no DEV evaluation; compute_test_values, judge_test, "
              "report_comparisons(test) once each after the last evaluation; finish (commit_paths [result] inside); "
              "final_record('test-evaluate', 'PIPELINE_NOT_QUALIFIED', stop None) writing experiment_record_test-"
              "evaluate_<start>.json/.txt, commit_paths [those two]; returns (True, 'PIPELINE_NOT_QUALIFIED')",
              "run 3: " + pre + "; begin raises TestAlreadyEvaluated; no evaluation; final_record('test-evaluate', "
              "'BLOCKED', stop code None / status BLOCKED / message 'crash after the TEST marker: "
              "TestAlreadyEvaluated(...)'), the same two file names as run 2 (same Pilot, same start time), "
              "commit_paths [those two]; run_test_evaluate raises TestAlreadyEvaluated (the test passes, pytest exit 0)",
              "remote after the fixture: exactly 4 commits, oldest first: marker only (A), result only (A), experiment "
              "record json + txt (A), experiment record json + txt (M); the third commit's record Status "
              "PIPELINE_NOT_QUALIFIED with stop null, the tip's Status BLOCKED with the crash message naming "
              "TestAlreadyEvaluated; result.marker_commit = the marker commit",
              "work: test_details/ holds 16 files <model>_test.json; the clone is clean and at the remote's tip"]
    elif mode == "stop_after_marker":
        p += ["run 2: " + pre + "; evaluate_model(split=test) entered 3 times, the 3rd raises the injected "
              "ProtocolStop; 2 claims, 2 state hashes after begin; no finish; final_record('test-evaluate', 'BLOCKED', "
              "stop code None / status BLOCKED / message naming the injected stop); commit_paths [experiment record "
              "json, txt]; returns (False, 'BLOCKED'); the test fails at its own assertion (pytest exit 1)",
              "remote after the fixture: exactly 2 commits: marker only, then experiment record json + txt; no result; "
              "the record's Status BLOCKED; the clone is clean and at the remote's tip; test_details/ 2 files"]
    else:
        p += ["run 2: " + pre + "; evaluate_model(split=test) entered 3 times, the 3rd raises the injected "
              "RuntimeError; 2 claims, 2 state hashes after begin; no finish; final_record('test-evaluate', 'BLOCKED', "
              "stop code None / status BLOCKED / message 'crash after the TEST marker: RuntimeError(...)'); "
              "commit_paths [experiment record json, txt]; run_test_evaluate raises RuntimeError (pytest exit 1)",
              "remote after the fixture: exactly 2 commits: marker only, then experiment record json + txt; no result; "
              "the record's Status BLOCKED, Actual {'crashed': ...}; the clone is clean and at the remote's tip; "
              "test_details/ 2 files"]
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
    pre = evs[:ib] if ib is not None else evs
    icp = idx(pre, lambda e: e["call"] == "check_preconditions" and e["phase"] == "return")
    own = pre[icp + 1:] if icp is not None else []      # test_evaluate's own reads: after check_preconditions returned
    reads = [e["rel"] for e in calls(own, "R.committed_record") + calls(own, "R.committed_json")]
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
    obs = {"check_preconditions": len(calls(pre, "check_preconditions")),
           "start_checks": [e["command"] for e in calls(pre, "Pilot.start_checks")],
           "four_records_read_in_order_before_the_checkpoint_loop": four == [FREEZE, GATE0, STEP2, STEP3]
           and None not in i4 and first_pt is not None and max(i4) < first_pt,
           "pt_hashes": sorted(e["file"] for e in calls(pre, "file_sha256")),
           "test_evaluation_seconds": [round(e["seconds"], 9) for e in tes],
           "timing_argument_is_the_fixture's": [e["timing"] == FIXTURE_TIMING for e in tes_in],
           "before_run": [round(e["next_seconds"], 9) for e in br],
           "state_hashes": [e["sha256"] for e in sh],
           "base_hash_equals_step3_N": [e["sha256"] == n3_sha for e in sh]}
    return obs, ib, len(reads)


def main():
    repo, py, inputs, scratch, mode = sys.argv[1:6]
    assert mode in ("normal", "stop_after_marker", "crash_after_marker"), mode
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
               + os.path.dirname(os.path.abspath(__file__)), METRIX_INPUTS_DIR=inputs, IC8_TRACE=trace_f,
               IC8_FAULT="" if mode == "normal" else mode, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic8_04_trace_plugin",
           "--basetemp=%s" % base, TEST_ID]
    print("\n== driver run (once): cwd %s" % repo)
    print("$ IC8_FAULT=%s " % env["IC8_FAULT"] + " ".join(shlex.quote(c) for c in cmd))
    print("----- pytest stdout+stderr begin -----")
    sys.stdout.flush()
    t0 = time.time()
    r = subprocess.run(cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout.rstrip("\n"))
    print("----- pytest stdout+stderr end ----- exit %d, %.0f s" % (r.returncode, time.time() - t0))
    want_rc = 0 if mode == "normal" else 1
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
    print("\nfixture models as a set == my list: %s | fixture order: %s | Pilot start time %s -> experiment record %s" % (
        sorted(start["models"]) == sorted(models), start["models"], started, EXP))
    ok &= sorted(start["models"]) == sorted(models) and start["models"][0] == "N"
    models = start["models"]
    step2 = json.loads(git(remote, "show", "%s:%s" % (tip0, STEP2)) or "{}")
    step3 = json.loads(git(remote, "show", "%s:%s" % (tip0, STEP3)) or "{}")
    n3 = (step3.get("N") or {}).get("state_sha256")
    print("remote at the fixture's tip: step 2 timing == the fixture's %s | step 3 N.state_sha256 %s" % (
        (step2.get("preflight") or {}).get("timing") == FIXTURE_TIMING, n3))
    ok &= (step2.get("preflight") or {}).get("timing") == FIXTURE_TIMING and n3 is not None
    runs = runs_of(trace)
    want_runs = 3 if mode == "normal" else 2
    print("run_test_evaluate calls: %d (expected %d)" % (len(runs), want_runs))
    ok &= len(runs) == want_runs
    want_pre = {"check_preconditions": 1, "start_checks": ["test-evaluate"],
                "four_records_read_in_order_before_the_checkpoint_loop": True,
                "pt_hashes": sorted(m + ".pt" for m in models[1:]), "test_evaluation_seconds": [round(MY_LOOKAHEAD, 9)],
                "timing_argument_is_the_fixture's": [True], "before_run": [round(MY_LOOKAHEAD, 9)],
                "state_hashes": [n3], "base_hash_equals_step3_N": [True]}

    print("\n== run 1 (refusal before the marker)")
    evs, end = runs[0]
    obs, ib, _ = before_begin(evs, n3)
    c1 = dict(obs, begin=ib is not None, evaluate_test=len([e for e in calls(evs, "evaluate_model") if e["split"] == "test"]),
              commit_paths=len(calls(evs, "commit_paths")), final_record=len(calls(evs, "final_record")),
              end=(end["phase"], end.get("result")))
    e1 = {"check_preconditions": 1, "start_checks": ["test-evaluate"],
          "four_records_read_in_order_before_the_checkpoint_loop": True, "pt_hashes": [models[1] + ".pt"],
          "test_evaluation_seconds": [], "timing_argument_is_the_fixture's": [], "before_run": [], "state_hashes": [],
          "base_hash_equals_step3_N": [], "begin": False, "evaluate_test": 0, "commit_paths": 0, "final_record": 0,
          "end": ("return", "(False, 'BLOCKED')")}
    print("observed %s\nexpected %s\nequal %s" % (c1, e1, c1 == e1))
    ok &= c1 == e1

    print("\n== run 2 (the evaluation)")
    evs, end = runs[1]
    obs, i_begin, _ = before_begin(evs, n3)
    print("before begin: observed %s\n              expected %s\n              equal %s" % (obs, want_pre, obs == want_pre))
    ok &= obs == want_pre
    i_begin_ret = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "return")
    bg = calls(evs, "begin_test_evaluation")
    marker_commit = evs[i_begin_ret].get("marker_commit") if i_begin_ret is not None else None
    inner = evs[i_begin:i_begin_ret] if i_begin_ret is not None else []
    mc = [e["rels"] for e in calls(inner, "commit_paths")]
    print("begin entered %d time(s) with base hash %s (== step 3 N: %s); returned marker commit %s; commit_paths inside "
          "begin %s" % (len(bg), [e["base_sha256"] for e in bg], [e["base_sha256"] == n3 for e in bg], marker_commit, mc))
    ok &= len(bg) == 1 and bg[0]["base_sha256"] == n3 and mc == [[MARKER]] and marker_commit is not None
    marker = json.loads(git(remote, "show", "%s:%s" % (marker_commit, MARKER)) or "{}") if marker_commit else {}
    print("marker models (remote blob) == the fixture's list, same order: %s | marker checkpoints['N'] == step 3 N: %s" % (
        marker.get("models") == models, (marker.get("checkpoints") or {}).get("N") == n3))
    ok &= marker.get("models") == models and (marker.get("checkpoints") or {}).get("N") == n3
    post = evs[i_begin_ret + 1:] if i_begin_ret is not None else []
    ev_enter = [e for e in calls(post, "evaluate_model")]
    ev_test = [e["checkpoint"] for e in ev_enter if e["split"] == "test"]
    ev_dev = [e for e in ev_enter if e["split"] != "test"]
    claims = [e["checkpoint"] for e in calls(post, "claim_checkpoint")]
    post_hashes = calls(post, "T.state_sha256", "return")
    post_br = [e["next_seconds"] for e in calls(post, "p.before_run")]
    ce = calls(post, "control_evaluation")
    fr = calls(evs, "final_record")
    wer = calls(evs, "write_experiment_record", "return")
    if mode == "normal":
        n_eval = len(models)
        i_last_ev = max(i for i, e in enumerate(evs) if e["call"] == "evaluate_model" and e["phase"] == "return")
        seq = [(n, idx(evs, lambda e, n=n: e["call"] == n and e["phase"] == "enter")) for n in
               ("compute_test_values", "judge_test", "report_comparisons", "finish_test_evaluation", "final_record")]
        once = {n: len(calls(evs, n)) for n, _ in seq}
        pos = [i for _, i in seq]
        ordered = None not in pos and pos == sorted(pos) and pos[0] > i_last_ev
        i_fin, i_fin_ret = dict(seq)["finish_test_evaluation"], idx(evs, lambda e: e["call"] == "finish_test_evaluation" and e["phase"] == "return")
        fin_commits = [e["rels"] for e in calls(evs[i_fin:i_fin_ret], "commit_paths")] if None not in (i_fin, i_fin_ret) else None
        after = [e["rels"] for e in calls(evs[i_fin_ret:], "commit_paths")] if i_fin_ret is not None else None
        print("after begin: evaluate_model(split=test) %d in order == marker models %s | DEV evaluations %d | claims == marker "
              "models %s | state hashes after begin %d | before_run after begin %s | control_evaluation %d (split %s)" % (
                  len(ev_test), ev_test == models, len(ev_dev), claims == models, len(post_hashes), post_br, len(ce),
                  sorted(set(e["split"] for e in ce))))
        ok &= ev_test == models and not ev_dev and claims == models and len(post_hashes) == n_eval \
            and post_br == [0.0] * n_eval and len(ce) == n_eval and set(e["split"] for e in ce) == {"test"}
        print("once each %s | order compute < judge < report < finish < final_record, after the last evaluation: %s | "
              "commit_paths inside finish %s | final_record %s | write_experiment_record returned %s | commit_paths "
              "after finish %s" % (once, ordered, fin_commits, [(e["command"], e["status"], e["stop"]) for e in fr],
                                   [e["paths"] for e in wer], after))
        ok &= set(once.values()) == {1} and ordered and fin_commits == [[RESULT]] and after == [EXP]
        ok &= [(e["command"], e["status"], e["stop"]) for e in fr] == [("test-evaluate", "PIPELINE_NOT_QUALIFIED", None)]
        ok &= [e["paths"] for e in wer] == [[os.path.basename(x) for x in EXP]]
        print("run 2 ends %s %s (expected return (True, 'PIPELINE_NOT_QUALIFIED'))" % (end["phase"], end.get("result")))
        ok &= end["phase"] == "return" and end.get("result") == "(True, 'PIPELINE_NOT_QUALIFIED')"

        print("\n== run 3 (second evaluation attempt)")
        evs3, end3 = runs[2]
        obs3, ib3, _ = before_begin(evs3, n3)
        print("before begin: observed %s\n              equal to the expected pre-marker part %s" % (obs3, obs3 == want_pre))
        ok &= obs3 == want_pre
        fr3 = calls(evs3, "final_record")
        stop3 = fr3[0]["stop"] if fr3 else None
        c3 = {"begin": len(calls(evs3, "begin_test_evaluation")),
              "begin_raised": [e["exc"] for e in calls(evs3, "begin_test_evaluation", "raise")],
              "evaluate": len(calls(evs3, "evaluate_model")),
              "final_record": [(e["command"], e["status"]) for e in fr3],
              "stop_code_status": (stop3 or {}).get("code"), "stop_status": (stop3 or {}).get("status"),
              "stop_message_crash_TestAlreadyEvaluated": str((stop3 or {}).get("message", "")).startswith(
                  "crash after the TEST marker: TestAlreadyEvaluated("),
              "write_experiment_record": [e["paths"] for e in calls(evs3, "write_experiment_record", "return")],
              "commit_paths": [e["rels"] for e in calls(evs3, "commit_paths")],
              "end": (end3["phase"], end3.get("exc"))}
        e3 = {"begin": 1, "begin_raised": ["TestAlreadyEvaluated"], "evaluate": 0,
              "final_record": [("test-evaluate", "BLOCKED")], "stop_code_status": None, "stop_status": "BLOCKED",
              "stop_message_crash_TestAlreadyEvaluated": True,
              "write_experiment_record": [[os.path.basename(x) for x in EXP]], "commit_paths": [EXP],
              "end": ("raise", "TestAlreadyEvaluated")}
        print("observed %s\nexpected %s\nequal %s" % (c3, e3, c3 == e3))
        print("stop of run 3's record: %s" % stop3)
        ok &= c3 == e3
    else:
        inj = [e for e in post if e["phase"] == "injected"]
        stop = fr[0]["stop"] if fr else None
        after = [e["rels"] for e in calls(post, "commit_paths")]
        print("after begin: evaluate_model(split=test) entered %d %s | injected %s | claims %s | state hashes after begin %d "
              "| finish %d | final_record %s | write_experiment_record returned %s | commit_paths after begin %s" % (
                  len(ev_test), ev_test, [(e["fault"], e["exc"]) for e in inj], claims, len(post_hashes),
                  len(calls(evs, "finish_test_evaluation")), [(e["command"], e["status"]) for e in fr],
                  [e["paths"] for e in wer], after))
        print("stop passed to final_record: %s" % stop)
        ok &= ev_test == models[:3] and len(inj) == 1 and claims == models[:2] and len(post_hashes) == 2 \
            and not calls(evs, "finish_test_evaluation") and after == [EXP]
        ok &= [(e["command"], e["status"]) for e in fr] == [("test-evaluate", "BLOCKED")] and [e["paths"] for e in wer] == [
            [os.path.basename(x) for x in EXP]]
        ok &= stop is not None and stop.get("code") is None and stop.get("status") == "BLOCKED"
        if mode == "stop_after_marker":
            ok &= "auditor-injected stop" in str(stop.get("message"))
            print("run 2 ends %s %s (expected return (False, 'BLOCKED'))" % (end["phase"], end.get("result")))
            ok &= end["phase"] == "return" and end.get("result") == "(False, 'BLOCKED')"
        else:
            ok &= str(stop.get("message")).startswith("crash after the TEST marker: RuntimeError(") \
                and "auditor-injected crash" in str(stop.get("message"))
            print("run 2 ends %s %s (expected raise RuntimeError)" % (end["phase"] if end else None, end.get("exc") if end else None))
            ok &= end is not None and end["phase"] == "raise" and end.get("exc") == "RuntimeError"

    print("\n== the bare remote (git only)")
    new = (git(remote, "rev-list", "--reverse", "%s..main" % tip0) or "").split()
    want = {"normal": [("A", [MARKER]), ("A", [RESULT]), ("A", sorted(EXP)), ("M", sorted(EXP))],
            "stop_after_marker": [("A", [MARKER]), ("A", sorted(EXP))],
            "crash_after_marker": [("A", [MARKER]), ("A", sorted(EXP))]}[mode]
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
    if new:
        print("first commit after the fixture == the marker commit begin returned: %s" % (new[0] == marker_commit))
        ok &= new[0] == marker_commit
    hits = {"%s %s" % (k[0][:8], k[1]): [n for n in TEXT_NEEDLES if n in v] for k, v in blobs.items()}
    print("synthetic TEST text in the blobs added after the fixture: %s" % hits)
    ok &= not any(hits.values())
    tree = (git(remote, "ls-tree", "-r", "--name-only", "main") or "").split("\n")
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
                exp_status.append((t.get("Status"), None if stop is None else (stop.get("code"), stop.get("status"),
                                                                                 str(stop.get("message"))),
                                   sorted((t.get("Actual") or {}).keys()), t.get("Experiment ID")))
                print("  experiment record in %s: Status %r | stop %s | Actual keys %s | Experiment ID %r" % (
                    c[:8], t.get("Status"), stop, sorted((t.get("Actual") or {}).keys()), t.get("Experiment ID")))
    if mode == "normal":        # (Status, stop code, stop status, stop message prefix, Actual keys)
        e_st = [("PIPELINE_NOT_QUALIFIED", None, None, None, ["final", "interpretation", "result_commit", "values"]),
                ("BLOCKED", None, "BLOCKED", "crash after the TEST marker: TestAlreadyEvaluated(", ["crashed"])]
    elif mode == "stop_after_marker":
        e_st = [("BLOCKED", None, "BLOCKED", "BLOCKED: auditor-injected stop after the TEST marker", ["stopped"])]
    else:
        e_st = [("BLOCKED", None, "BLOCKED", "crash after the TEST marker: RuntimeError('auditor-injected crash", ["crashed"])]
    got_st = []
    for (st, stop, ak, _), (_, _, _, pref, _) in zip(exp_status, e_st + [(None,) * 5] * len(exp_status)):
        if stop is None:
            got_st.append((st, None, None, None, ak))
        else:
            got_st.append((st, stop[0], stop[1], pref if pref is not None and stop[2].startswith(pref) else stop[2], ak))
    print("experiment records (Status, stop, Actual keys) oldest first %s | expected %s | equal %s" % (got_st, e_st, got_st == e_st))
    ok &= got_st == e_st
    print("Experiment IDs %s (one start time per Pilot)" % [x[3] for x in exp_status])
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
    want_det = sorted("%s_test.json" % m for m in (models if mode == "normal" else models[:2]))
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
