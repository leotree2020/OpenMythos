"""ic7_04_e2e (implementation stage C, C2 work commit (staged tree b80c9062, parent f8139f9), round 1; task 4, dynamic
part). Data Auditor's own script: nothing of the Executor is imported here.

Runs the Executor's test tests/test_run_pilot.py::test_test_evaluate_end_to_end_once once as a driver subprocess (C1
ruling item 5; the test builds a throw-away clone with a bare remote, synthetic TEST rows written by the test itself,
random tiny models, require_gpu replaced; no TEST data, no weights), with my pass-through trace plugin
(ic7_04_trace_plugin.py) recording the calls on the TEST path, and pytest's --basetemp in my scratch directory so that
the clone, the bare remote and the work directory stay for my analysis. My expectations are printed BEFORE the run;
after it, this script compares the trace, the bare remote's history (git only) and the work directory with them.

Modes:
  normal              the test as written: refusal before the marker (changed checkpoint file), one evaluation
                      (marker -> 16 x evaluate_model(split="test") -> T1-T3 -> result -> experiment record), then
                      TestAlreadyEvaluated.
  stop_after_marker   the plugin raises a ProtocolStop(BLOCKED) at the 3rd evaluate_model(split="test"): expected
                      that the experiment record IS written, committed and pushed after the marker (the test then
                      fails at its own assertion; only the state is analysed).
  crash_after_marker  the plugin raises a RuntimeError at the 3rd evaluate_model(split="test"): my reading of
                      pilot.run_test_evaluate (only ProtocolStop / PreconditionFailed are caught) predicts that NO
                      experiment record is written for this run, although the marker exists (registered as MINOR,
                      outside the guarded object: the marker still refuses a second evaluation). The script checks
                      that the observation equals this prediction.
usage: python -I -B ic7_04_e2e.py <repo_root> <venv_python> <inputs_dir> <scratch_dir (created, must not exist)> <mode>
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
EXP = [RES + "/experiment_record_test-evaluate.json", RES + "/experiment_record_test-evaluate.txt"]
TEST_ID = "metrix/e1-pilot/tests/test_run_pilot.py::test_test_evaluate_end_to_end_once"
SELECTED = {"F": "F3", "L": "L2", "A": "A5"}          # the test's SELECTED (read from the test file below, compared)
TEXT_NEEDLES = ("Synthetic question", "not a TEST row", "synthetic window", "SYNTHETIC_T", "synthetic-")
# the synthetic TEST rows of the test: question text, window text, the TEST template id and the window doc ids
ROW_KEYS = {"question", "ids", "generated_ids", "output", "normalized", "doc_id", "scores", "prediction", "top2_gap",
            "answer_index"}                    # fields of a per-question or per-window row (evaluate's details)


def git(d, *args):
    r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r.stdout.strip() if r.returncode == 0 else None


def my_models():
    """The 16 models TEST evaluates, from my reading of the protocol (section 8 step 8: N and the final checkpoints of
    F, L, A (selected configuration) and S, Y (F's configuration), seeds 101, 202, 303) and the test's SELECTED."""
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
    p = ["models TEST evaluates (my list, set): %s" % sorted(models),
         "run 1 (checkpoint file of the fixture's models[1] changed by the test): check_preconditions once; exactly 1 "
         "checkpoint file hashed (that one); no begin, no evaluate_model(split=test), no commit_paths, no final_record; returns "
         "(False, 'BLOCKED'); no marker"]
    if mode == "normal":
        p += ["run 2: check_preconditions once, then the 15 checkpoint files hashed (set = models[1:]), all before "
              "begin; begin once (commit_paths [marker] inside); 16 evaluate_model(split=test) in the marker's model "
              "order (marker models == the fixture's list), each followed by claim_checkpoint, no DEV evaluation; then compute_test_values, judge_test, "
              "report_comparisons(split test) once each; then finish (commit_paths [result] inside); then final_record "
              "('test-evaluate'), commit_paths [experiment record json, txt]; returns (True, 'PIPELINE_NOT_QUALIFIED') "
              "(random tiny models: T1 cannot hold)",
              "run 3: check_preconditions once, 15 checkpoint files hashed, begin raises TestAlreadyEvaluated; no "
              "evaluation, no commit, no final_record",
              "remote after the fixture: exactly 3 commits, oldest first: marker only, result only, experiment record "
              "(json + txt) only; result.marker_commit = the marker commit; no added blob contains the synthetic "
              "TEST text %s; result and experiment record have no key starting with 'general_test' and no "
              "per-question / per-window row key %s" % (list(TEXT_NEEDLES), sorted(ROW_KEYS)),
              "work: test_details/ holds 16 files <model>_test.json (the per-question details: rows with the "
              "synthetic template id; outside the clone); the clone and the remote hold no test_qa.jsonl, "
              "general_test.jsonl, and no *_test.json under metrix/e1-pilot/"]
    elif mode == "stop_after_marker":
        p += ["run 2: begin once; evaluate_model(split=test) entered 3 times, the 3rd raises the injected ProtocolStop; "
              "2 claims; no finish; final_record('test-evaluate', 'BLOCKED'); commit_paths [experiment record json, "
              "txt]; returns (False, 'BLOCKED'); the test fails at its own assertion (pytest exit 1)",
              "remote after the fixture: exactly 2 commits: marker only, then experiment record (json + txt) only; no "
              "result file; the experiment record's Status BLOCKED and its stop message names the injected stop"]
    else:
        p += ["run 2: begin once; evaluate_model(split=test) entered 3 times, the 3rd raises the injected RuntimeError; "
              "no finish; NO final_record; run_test_evaluate raises RuntimeError (pytest exit 1)",
              "remote after the fixture: exactly 1 commit (the marker); no result, no experiment record on the remote "
              "or in the clone's working tree (a crash after the marker leaves no section 10 record: MINOR finding)"]
    return p


def runs_of(trace):
    """Split the trace into the run_test_evaluate calls: list of (events between enter and its return / raise, end)."""
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
    print("test file: SELECTED line %r present: %s" % (sel_line, sel_line in tsrc))
    ok &= sel_line in tsrc
    models = my_models()
    print("\n== my expectations (written before the run; mode %s)" % mode)
    for x in predictions(mode, models):
        print("  - " + x)

    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix",
               ":(exclude)metrix/e1-pilot/audit")         # audit/ is where my own outputs are being written
    gs_before = git(repo, *st_args)
    idx_before = git(repo, "ls-files", "-s")
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src") + os.pathsep
               + os.path.dirname(os.path.abspath(__file__)), METRIX_INPUTS_DIR=inputs, IC7_TRACE=trace_f,
               IC7_FAULT="" if mode == "normal" else mode, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    cmd = [py, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "ic7_04_trace_plugin",
           "--basetemp=%s" % base, TEST_ID]
    print("\n== driver run (once): cwd %s" % repo)
    print("$ IC7_FAULT=%s " % env["IC7_FAULT"] + " ".join(shlex.quote(c) for c in cmd))
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
    print("\n== trace (%d events, complete)" % len(trace))
    for e in trace:
        print("  " + json.dumps(e, ensure_ascii=False))
    start = [e for e in trace if e["call"] == "test" and e["phase"] == "start"][0]
    root, remote, work, tip0 = start["root"], start["remote"], start["work"], start["remote_tip_after_fixture"]
    print("\nfixture models as a set == my list: %s | fixture order (the order compared below): %s" % (
        sorted(start["models"]) == sorted(models), start["models"]))
    ok &= sorted(start["models"]) == sorted(models) and start["models"][0] == "N"
    models = start["models"]          # my set, in the fixture's (= the marker's, checked below) order
    runs = runs_of(trace)
    want_runs = 3 if mode == "normal" else 2
    print("run_test_evaluate calls: %d (expected %d)" % (len(runs), want_runs))
    ok &= len(runs) == want_runs

    print("\n== run 1 (refusal before the marker)")
    evs, end = runs[0]
    pt = calls(evs, "file_sha256")
    c1 = {"check_preconditions": len(calls(evs, "check_preconditions")), "pt_hashes": [e["file"] for e in pt],
          "begin": len(calls(evs, "begin_test_evaluation")),
          "evaluate_test": len([e for e in calls(evs, "evaluate_model") if e["split"] == "test"]),
          "commit_paths": len(calls(evs, "commit_paths")), "final_record": len(calls(evs, "final_record")),
          "end": (end["phase"], end.get("result"))}
    print("observed %s" % c1)
    e1 = {"check_preconditions": 1, "pt_hashes": [models[1] + ".pt"], "begin": 0, "evaluate_test": 0,
          "commit_paths": 0, "final_record": 0, "end": ("return", "(False, 'BLOCKED')")}
    print("expected %s | equal %s" % (e1, c1 == e1))
    ok &= c1 == e1

    print("\n== run 2 (the evaluation)")
    evs, end = runs[1]
    i_pre = idx(evs, lambda e: e["call"] == "check_preconditions" and e["phase"] == "enter")
    pt_i = [i for i, e in enumerate(evs) if e["call"] == "file_sha256" and e["phase"] == "enter"]
    i_begin = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "enter")
    i_begin_ret = idx(evs, lambda e: e["call"] == "begin_test_evaluation" and e["phase"] == "return")
    pts = sorted(evs[i]["file"] for i in pt_i)
    pre_ok = (len(calls(evs, "check_preconditions")) == 1 and i_pre is not None and i_begin is not None
              and all(i_pre < i < i_begin for i in pt_i) and pts == sorted(m + ".pt" for m in models[1:]))
    print("check_preconditions once, then 15 checkpoint files hashed (set = models[1:]), all before begin: %s "
          "(hashed %d: %s)" % (pre_ok, len(pt_i), pts))
    ok &= pre_ok
    inner = evs[i_begin:i_begin_ret] if i_begin_ret is not None else []
    marker_commit = evs[i_begin_ret].get("marker_commit") if i_begin_ret is not None else None
    mc = [e["rels"] for e in calls(inner, "commit_paths")]
    print("begin entered %d time(s); returned marker commit %s; commit_paths inside begin %s" % (
        len(calls(evs, "begin_test_evaluation")), marker_commit, mc))
    ok &= len(calls(evs, "begin_test_evaluation")) == 1 and mc == [[MARKER]] and marker_commit is not None
    ev_enter = [(i, e) for i, e in enumerate(evs) if e["call"] == "evaluate_model" and e["phase"] == "enter"]
    ev_test = [e["checkpoint"] for _, e in ev_enter if e["split"] == "test"]
    ev_dev = [e for _, e in ev_enter if e["split"] != "test"]
    claims = [e["checkpoint"] for e in calls(evs, "claim_checkpoint", "enter")]
    after_begin = all(i > i_begin_ret for i, _ in ev_enter) if i_begin_ret is not None else False
    marker_blob = git(remote, "show", "%s:%s" % (marker_commit, MARKER)) if marker_commit else None
    marker = json.loads(marker_blob) if marker_blob else {}
    print("marker models (remote blob) == the fixture's list, same order: %s" % (marker.get("models") == models))
    ok &= marker.get("models") == models
    if mode == "normal":
        i_last_ev = max(i for i, e in enumerate(evs) if e["call"] == "evaluate_model" and e["phase"] == "return")
        seq = [(n, idx(evs, lambda e, n=n: e["call"] == n and e["phase"] == "enter")) for n in
               ("compute_test_values", "judge_test", "report_comparisons", "finish_test_evaluation", "final_record")]
        i_fin = dict(seq)["finish_test_evaluation"]
        i_fin_ret = idx(evs, lambda e: e["call"] == "finish_test_evaluation" and e["phase"] == "return")
        once = {n: len(calls(evs, n)) for n, _ in seq}
        pos = [i for _, i in seq]
        ordered = None not in pos and pos == sorted(pos) and pos[0] > i_last_ev
        fin_commits = [e["rels"] for e in calls(evs[i_fin:i_fin_ret], "commit_paths")] if None not in (i_fin, i_fin_ret) else None
        fr = calls(evs, "final_record")
        after = [e["rels"] for e in calls(evs[i_fin_ret:], "commit_paths")] if i_fin_ret is not None else None
        rc = [e for e in calls(evs, "report_comparisons")]
        print("evaluate_model(split=test) calls %d in order %s | == marker models in order: %s | DEV evaluations %d | "
              "claims %d == marker models: %s | all evaluations after begin returned: %s" % (
                  len(ev_test), ev_test, ev_test == marker.get("models"), len(ev_dev), len(claims),
                  claims == marker.get("models"), after_begin))
        ok &= ev_test == marker.get("models") == models and not ev_dev and claims == models and after_begin
        print("once each %s | order compute_test_values < judge_test < report_comparisons < finish < final_record, "
              "all after the last evaluation: %s | report_comparisons split %s" % (once, ordered, [e["split"] for e in rc]))
        ok &= set(once.values()) == {1} and ordered and [e["split"] for e in rc] == ["test"]
        print("commit_paths inside finish %s | final_record %s | commit_paths after finish %s" % (
            fin_commits, [(e["command"], e["status"]) for e in fr], after))
        ok &= fin_commits == [[RESULT]] and [e["command"] for e in fr] == ["test-evaluate"] and after == [EXP]
        print("run 2 ends %s %s (expected return (True, 'PIPELINE_NOT_QUALIFIED'))" % (end["phase"], end.get("result")))
        ok &= end["phase"] == "return" and end.get("result") == "(True, 'PIPELINE_NOT_QUALIFIED')"

        print("\n== run 3 (second evaluation attempt)")
        evs3, end3 = runs[2]
        c3 = {"check_preconditions": len(calls(evs3, "check_preconditions")),
              "pt_hashes": len(calls(evs3, "file_sha256")), "begin": len(calls(evs3, "begin_test_evaluation")),
              "begin_raised": [e["exc"] for e in calls(evs3, "begin_test_evaluation", "raise")],
              "evaluate": len(calls(evs3, "evaluate_model")), "commit_paths": len(calls(evs3, "commit_paths")),
              "final_record": len(calls(evs3, "final_record")), "end": (end3["phase"], end3.get("exc"))}
        e3 = {"check_preconditions": 1, "pt_hashes": 15, "begin": 1, "begin_raised": ["TestAlreadyEvaluated"],
              "evaluate": 0, "commit_paths": 0, "final_record": 0, "end": ("raise", "TestAlreadyEvaluated")}
        print("observed %s\nexpected %s | equal %s" % (c3, e3, c3 == e3))
        ok &= c3 == e3
    else:
        inj = [e for e in evs if e["phase"] == "injected"]
        fr = calls(evs, "final_record")
        print("evaluate_model(split=test) entered %d (%s) | injected %s | claims %s | finish %d | final_record %s" % (
            len(ev_test), ev_test, [(e["fault"], e["exc"]) for e in inj], claims,
            len(calls(evs, "finish_test_evaluation")), [(e["command"], e["status"]) for e in fr]))
        ok &= len(ev_test) == 3 and ev_test == models[:3] and len(inj) == 1 and claims == models[:2] \
            and not calls(evs, "finish_test_evaluation") and after_begin
        if mode == "stop_after_marker":
            after = [e["rels"] for e in calls(evs[i_begin_ret:], "commit_paths")]
            print("final_record expected [('test-evaluate', 'BLOCKED')]; commit_paths after begin %s (expected [%s]); "
                  "run 2 ends %s %s (expected return (False, 'BLOCKED'))" % (after, EXP, end["phase"], end.get("result")))
            ok &= [(e["command"], e["status"]) for e in fr] == [("test-evaluate", "BLOCKED")] and after == [EXP] \
                and end["phase"] == "return" and end.get("result") == "(False, 'BLOCKED')"
        else:
            after = [e["rels"] for e in calls(evs[i_begin_ret:], "commit_paths")]
            print("final_record expected none; commit_paths after begin %s (expected []); run 2 ends %s %s (expected "
                  "raise RuntimeError)" % (after, end["phase"] if end else None, end.get("exc") if end else None))
            ok &= fr == [] and after == [] and end is not None and end["phase"] == "raise" and end.get("exc") == "RuntimeError"

    print("\n== the bare remote (git only)")
    new = (git(remote, "rev-list", "--reverse", "%s..main" % tip0) or "").split()
    want_files = {"normal": [[MARKER], [RESULT], sorted(EXP)], "stop_after_marker": [[MARKER], sorted(EXP)],
                  "crash_after_marker": [[MARKER]]}[mode]
    got_files, blobs = [], {}
    for c in new:
        st = git(remote, "diff-tree", "--no-commit-id", "-r", "--name-status", "--root", c).split("\n")
        files = sorted(x.split("\t", 1)[1] for x in st if x)
        kinds = sorted(set(x.split("\t", 1)[0] for x in st if x))
        got_files.append(files)
        print("  commit %s parent %s: %s %s | %s" % (c[:12], (git(remote, "rev-parse", c + "^") or "")[:12], kinds, files,
                                                     git(remote, "log", "-1", "--format=%s", c)))
        for f in files:
            blobs[(c, f)] = git(remote, "show", "%s:%s" % (c, f)) or ""
    print("commits after the fixture's tip %s: %d; files per commit == expected %s: %s" % (
        tip0[:12], len(new), want_files, got_files == want_files))
    ok &= got_files == want_files
    if new:
        print("first commit after the fixture == the marker commit begin returned: %s" % (new[0] == marker_commit))
        ok &= new[0] == marker_commit
    hits = {k[1]: [n for n in TEXT_NEEDLES if n in v] for k, v in blobs.items()}
    print("synthetic TEST text %s in the blobs added after the fixture: %s" % (list(TEXT_NEEDLES), hits))
    ok &= not any(hits.values())
    tree = (git(remote, "ls-tree", "-r", "--name-only", "main") or "").split("\n")
    bad_paths = [x for x in tree if x.endswith(("test_qa.jsonl", "general_test.jsonl"))
                 or (x.startswith("metrix/e1-pilot/") and x.endswith("_test.json"))]
    print("remote tree: TEST data file names, or *_test.json under metrix/e1-pilot/: %s" % bad_paths)
    ok &= not bad_paths
    for (c, f), v in blobs.items():
        if f.endswith(".json") and f != MARKER:
            obj = json.loads(v)
            keys = walk_keys(obj, set())
            gen = sorted(k for k in keys if str(k).startswith("general_test"))
            rowk = sorted(ROW_KEYS & keys)
            print("  %s: keys starting with 'general_test' %s | per-question / per-window row keys %s" % (f, gen, rowk))
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
                print("  experiment record: Status %r | stop %s" % (t.get("Status"), stop))
                if mode == "stop_after_marker":
                    ok &= t.get("Status") == "BLOCKED" and "auditor-injected stop" in json.dumps(stop, ensure_ascii=False)
                else:
                    ok &= t.get("Status") == "PIPELINE_NOT_QUALIFIED" and stop is None
    clone_files = [os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) if "/.git" not in d + "/"
                   for f in fs]
    clone_bad = [x for x in clone_files if x.endswith(("test_qa.jsonl", "general_test.jsonl"))
                 or (x.startswith("metrix/e1-pilot/") and x.endswith("_test.json"))]
    clone_exp = [x for x in EXP if os.path.exists(os.path.join(root, x))]
    print("clone working tree: TEST data file names, or *_test.json under metrix/e1-pilot/: %s | experiment record files "
          "%s" % (clone_bad, clone_exp))
    ok &= not clone_bad
    if mode == "crash_after_marker":
        ok &= clone_exp == []
    wd = os.path.join(work, "test_details")
    det = sorted(os.listdir(wd)) if os.path.isdir(wd) else []
    want_det = sorted("%s_test.json" % m for m in (models if mode == "normal" else models[:2]))
    inside = os.path.realpath(work).startswith(os.path.realpath(root) + os.sep)
    with_text = sum(1 for n in det if '"SYNTHETIC_T"' in open(os.path.join(wd, n), encoding="utf-8").read())
    print("work %s (inside the clone: %s): test_details %s == expected %s: %s | files holding per-question rows of the "
          "synthetic TEST template (the per-question details) %d" % (work, inside, det, want_det, det == want_det, with_text))
    ok &= not inside and det == want_det and with_text == len(want_det)

    gs_after = git(repo, *st_args)
    idx_after = git(repo, "ls-files", "-s")
    print("\nthis repository: git status --porcelain --ignored --untracked-files=all -- metrix (audit/ excluded) unchanged by "
          "the run: %s | "
          "index entries unchanged: %s" % (gs_after == gs_before, idx_after == idx_before))
    if gs_after != gs_before:
        print("  before:\n%s\n  after:\n%s" % (gs_before, gs_after))
    ok &= gs_after == gs_before and idx_after == idx_before
    return bool(ok)


run(main)
