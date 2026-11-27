"""ic8_04_static (implementation stage C, C2 fix commit (staged tree b40224e6, parent 1900b1fe), round 1; task 4): static
reading, with Python's ast, of the STAGED blobs (git cat-file :path), never imported. My ic7_04_static rewritten for the
changed code.
  a. pilot.test_evaluate: every check before the marker sits before TG.begin_test_evaluation, in source order:
     formal-mode check -> TD.check_preconditions -> TG.code_commit -> p.start_checks('test-evaluate') -> p.device_check
     -> p.load_data -> TEST files read -> committed freeze / Gate 0 / step 2 / step 3 records -> checkpoint files over
     models[1:] (FZ.file_sha256 vs the committed run record and the freeze record; raise ProtocolStop BLOCKED) ->
     test_evaluation_seconds(p.contract, step2['preflight']['timing']) -> p.before_run(look_ahead) (ST7) ->
     p.base_model -> T.state_sha256 -> N's hash vs the committed step 3 record (raise ProtocolStop BLOCKED) -> begin
     (with that hash) -> ONE evaluation call (control_evaluation(..., split='test', test_session=session,
     checkpoint_name=name)) inside the single loop over `models` -> compute_test_values -> judge_test ->
     report_comparisons(..., 'test') -> finish. None of the pre-marker calls is inside a loop that also holds begin;
     the pre-marker record reads are wrapped so that NotCommitted / KeyError / OSError / TypeError become ProtocolStop
     BLOCKED; the GPU-clock part is one try / finally p.close_clock(). control_evaluation holds exactly one p.evaluate
     call (split and **kw passed through), no loop: one evaluation per call.
  b. pilot.run_test_evaluate: two handlers: (ProtocolStop, TD.PreconditionFailed) returns without final_record when
     the marker file does not exist and the stop code is not ST10; Exception re-raises (bare raise) when the marker
     does not exist, otherwise records crash, status BLOCKED; final_record after the try; then `raise crash`.
     Consequence I check dynamically (ic8_04a run 3): TestAlreadyEvaluated (base Exception) on a checkout whose working
     tree holds the marker is handled as a crash after the marker: a BLOCKED experiment record is written and pushed.
  c. CD13: result = plain({kind, frozen_commit, values, final, comparisons, summaries}); summaries via _summary_record
     (drops keys starting with general_); details under p.work / TEST_DETAILS_DIR; Pilot.__init__ refuses a work
     directory inside the repository.
  d. CD5 / CE5 and MAJOR 2: run_test_generate runs subprocess.run(test_generate_command(...)) once and calls nothing of
     test_data; after it, st10_over_limit(p); final_record is called only inside `if over:` with status 'BLOCKED' and
     a stop of code 'ST10'; st10_over_limit reads the COMMITTED ST10 record (R.committed_json) and TG.over_limit and
     returns [] on R.NotCommitted. Package-wide, generate_test and run_test_part are called only in test_data.main;
     pilot.py uses only TD.check_preconditions and TD.PreconditionFailed.
  e. MAJOR 9: step8_smoke_refusal raises ImplementationFail before subprocess.run when HEAD (TG._blob 'HEAD:...') or
     the working tree holds the Gate 0, freeze or ST10 record; the subprocess is the same generator command.
  f. CA20: begin / finish called package-wide only by pilot.test_evaluate.
  g. ruling 2026-11-27 item 1: begin and finish reach check_checkout (git fetch); require_test_session,
     _check_session_checkout, claim_checkpoint do not.
  h. run_pilot.py: --steps only on the smoke sub-parser; test-generate / test-evaluate call P.run_test_generate /
     P.run_test_evaluate.
Data Auditor's own script; the Executor's code is parsed, not imported or executed.
usage: python -I -B ic8_04_static.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import subprocess
from ia_common import run

PKG = "metrix/e1-pilot/src/metrix_e1/"
EVAL_NAMES = ("p.evaluate", "E.evaluate_model", "evaluate_model", "self.evaluate", "control_evaluation")


def staged(repo, rel):
    r = subprocess.run(["git", "-C", repo, "cat-file", "blob", ":" + rel], capture_output=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    assert r.returncode == 0, rel
    return r.stdout.decode("utf-8")


def func(tree, name):
    hits = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(hits) == 1, (name, len(hits))
    return hits[0]


def calls(node):
    return sorted((c for c in ast.walk(node) if isinstance(c, ast.Call)), key=lambda c: (c.lineno, c.col_offset))


def cname(c):
    return ast.unparse(c.func)


def first(node, pred):
    xs = [c for c in calls(node) if pred(c)]
    return xs[0] if xs else None


def line(c):
    return c.lineno if c is not None else None


def kw(c, name):
    for k in c.keywords:
        if k.arg == name:
            return ast.unparse(k.value)
    return None


def enclosing_functions(tree):
    out = {}

    def visit(n, fn):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = n.name
        if isinstance(n, ast.Call):
            out[id(n)] = fn
        for ch in ast.iter_child_nodes(n):
            visit(ch, fn)
    visit(tree, None)
    return out


def main():
    repo = sys.argv[1]
    ok = True
    pilot = ast.parse(staged(repo, PKG + "pilot.py"))
    te = func(pilot, "test_evaluate")

    print("== a. pilot.test_evaluate (staged blob, source lines)")
    begin = first(te, lambda c: cname(c) == "TG.begin_test_evaluation")
    cr = [c for c in calls(te) if cname(c) in ("R.committed_record", "R.committed_json")]
    rec_line = {ast.unparse(c.args[1]): c.lineno for c in cr if len(c.args) > 1}
    print("committed record reads: %s" % rec_line)
    st3_cmp = [n for n in ast.walk(te) if isinstance(n, ast.If) and ast.unparse(n.test) == "base_sha != n_sha"
               and any(isinstance(b, ast.Raise) and "ProtocolStop" in ast.unparse(b) and "'BLOCKED'" in ast.unparse(b)
                       for b in n.body)]
    seq = [
        ("formal-mode check (raise when not p.mode.formal)", next(
            (n.lineno for n in ast.walk(te) if isinstance(n, ast.If) and "p.mode.formal" in ast.unparse(n.test)
             and any(isinstance(b, ast.Raise) for b in n.body)), None)),
        ("TD.check_preconditions", line(first(te, lambda c: cname(c) == "TD.check_preconditions"))),
        ("TG.code_commit", line(first(te, lambda c: cname(c) == "TG.code_commit"))),
        ("p.start_checks('test-evaluate')", line(first(te, lambda c: cname(c) == "p.start_checks"
                                                       and ast.unparse(c.args[0]) == "'test-evaluate'"))),
        ("p.device_check", line(first(te, lambda c: cname(c) == "p.device_check"))),
        ("p.load_data", line(first(te, lambda c: cname(c) == "p.load_data"))),
        ("TEST files read (FZ.read_jsonl)", line(first(te, lambda c: cname(c) == "FZ.read_jsonl"))),
        ("committed freeze record", rec_line.get("R.SELECTION_FREEZE_REL")),
        ("committed Gate 0 record", rec_line.get("R.GATE0_RECORD_REL")),
        ("committed step 2 record", rec_line.get("'%s/step2_record.json' % R.FORMAL_RESULTS_REL")),
        ("committed step 3 record", rec_line.get("'%s/step3_record.json' % R.FORMAL_RESULTS_REL")),
        ("checkpoint file sha256 (FZ.file_sha256)", line(first(te, lambda c: cname(c) == "FZ.file_sha256"))),
        ("test_evaluation_seconds(p.contract, step2['preflight']['timing'])", line(first(
            te, lambda c: cname(c) == "test_evaluation_seconds"
            and [ast.unparse(a) for a in c.args] == ["p.contract", "step2['preflight']['timing']"]))),
        ("p.before_run(look_ahead) (ST7)", line(first(te, lambda c: cname(c) == "p.before_run"
                                                       and [ast.unparse(a) for a in c.args] == ["look_ahead"]))),
        ("p.base_model", line(first(te, lambda c: cname(c) == "p.base_model"))),
        ("T.state_sha256(base)", line(first(te, lambda c: cname(c) == "T.state_sha256"))),
        ("if base_sha != n_sha: raise ProtocolStop BLOCKED", st3_cmp[0].lineno if len(st3_cmp) == 1 else None),
        ("TG.begin_test_evaluation(fz, auth, data, base_sha)", line(begin) if begin is not None and
         [ast.unparse(a) for a in begin.args] == ["fz", "auth", "data", "base_sha"] else None),
        ("the evaluation call", line(first(te, lambda c: cname(c) in EVAL_NAMES))),
        ("G.compute_test_values", line(first(te, lambda c: cname(c) == "G.compute_test_values"))),
        ("G.judge_test", line(first(te, lambda c: cname(c) == "G.judge_test"))),
        ("G.report_comparisons", line(first(te, lambda c: cname(c) == "G.report_comparisons"))),
        ("TG.finish_test_evaluation", line(first(te, lambda c: cname(c) == "TG.finish_test_evaluation"))),
    ]
    for k, v in seq:
        print("  line %-5s %s" % (v, k))
    lines = [v for _, v in seq]
    ordered = None not in lines and lines == sorted(lines)
    print("all present and in this order (every pre-marker check before begin): %s" % ordered)
    ok &= ordered
    n_assign = [ast.unparse(n.value) for n in ast.walk(te) if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == ["n_sha"]]
    la_assign = [ast.unparse(n.value) for n in ast.walk(te) if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == ["look_ahead"]]
    print("n_sha = %s | look_ahead = %s" % (n_assign, la_assign))
    ok &= n_assign == ["step3['N']['state_sha256']"] and la_assign == ["test_evaluation_seconds(p.contract, step2['preflight']['timing'])"]
    fors = [n for n in ast.walk(te) if isinstance(n, ast.For)]
    ck_loop = [f for f in fors if ast.unparse(f.iter) == "models[1:]"]
    ev_loop = [f for f in fors if ast.unparse(f.iter) == "models"]
    ck_ok = (len(ck_loop) == 1 and any(cname(c) == "FZ.file_sha256" for c in calls(ck_loop[0]))
             and any(isinstance(n, ast.Raise) and "ProtocolStop" in ast.unparse(n) and "'BLOCKED'" in ast.unparse(n)
                     for n in ast.walk(ck_loop[0]))
             and "freeze['checkpoints'][name]" in ast.unparse(ck_loop[0]) and "run_rec['checkpoint']['file_sha256']" in ast.unparse(ck_loop[0]))
    print("checkpoint check: one loop over models[1:] with FZ.file_sha256 vs run_rec['checkpoint']['file_sha256'] and "
          "freeze['checkpoints'][name], raise ProtocolStop(..., 'BLOCKED', ...): %s" % ck_ok)
    ok &= ck_ok
    tries = [n for n in te.body if isinstance(n, ast.Try)]
    pre_try = [t for t in tries if t.handlers and any(cname(c) == "FZ.file_sha256" for c in calls(ast.Module(body=t.body, type_ignores=[])))]
    conv = (len(pre_try) == 1 and len(pre_try[0].handlers) == 1
            and ast.unparse(pre_try[0].handlers[0].type) == "(R.NotCommitted, KeyError, OSError, TypeError)"
            and any(isinstance(n, ast.Raise) and "ProtocolStop" in ast.unparse(n) and "'BLOCKED'" in ast.unparse(n)
                    for n in ast.walk(pre_try[0].handlers[0])))
    print("pre-marker reads inside a try whose single handler (R.NotCommitted, KeyError, OSError, TypeError) raises "
          "ProtocolStop BLOCKED: %s" % conv)
    ok &= conv
    gpu_try = [t for t in tries if t.finalbody and not t.handlers]
    gt = gpu_try[0] if len(gpu_try) == 1 else None
    gt_calls = [cname(c) for c in calls(ast.Module(body=gt.body, type_ignores=[]))] if gt else []
    gt_ok = (gt is not None and [ast.unparse(x) for x in gt.finalbody] == ["p.close_clock()"]
             and "p.before_run" in gt_calls and "TG.begin_test_evaluation" in gt_calls and "TG.finish_test_evaluation" in gt_calls
             and "p.base_model" in gt_calls)
    print("one try / finally p.close_clock() holding before_run(look_ahead), base_model, begin, the evaluations and "
          "finish: %s" % gt_ok)
    ok &= gt_ok
    evs_all = [c for c in calls(te) if cname(c) in EVAL_NAMES]
    evs_loop = [c for c in calls(ev_loop[0]) if c in evs_all] if len(ev_loop) == 1 else []
    ev_ok = (len(ev_loop) == 1 and len(evs_all) == 1 and len(evs_loop) == 1
             and kw(evs_loop[0], "split") == "'test'" and kw(evs_loop[0], "test_session") == "session"
             and kw(evs_loop[0], "checkpoint_name") == "name" and line(begin) < ev_loop[0].lineno)
    print("evaluation calls in test_evaluate %d %s, inside the single loop over `models` (after begin) %d | split=%s "
          "test_session=%s checkpoint_name=%s | ok %s" % (
              len(evs_all), [cname(c) for c in evs_all], len(evs_loop),
              kw(evs_all[0], "split") if evs_all else None, kw(evs_all[0], "test_session") if evs_all else None,
              kw(evs_all[0], "checkpoint_name") if evs_all else None, ev_ok))
    ok &= ev_ok
    ce = func(pilot, "control_evaluation")
    ce_ev = [c for c in calls(ce) if cname(c) in EVAL_NAMES]
    ce_loops = [n for n in ast.walk(ce) if isinstance(n, (ast.For, ast.While))]
    ce_ok = (len(ce_ev) == 1 and cname(ce_ev[0]) == "p.evaluate" and kw(ce_ev[0], "split") == "split"
             and any(k.arg is None and ast.unparse(k.value) == "kw" for k in ce_ev[0].keywords) and not ce_loops
             and any(isinstance(h.type, ast.Attribute) and ast.unparse(h.type) == "T.NonFinite"
                     for t in ast.walk(ce) if isinstance(t, ast.Try) for h in t.handlers))
    print("control_evaluation: evaluation calls %s, split and **kw passed through, loops %d, NonFinite -> st6 handler: %s" % (
        [ast.unparse(c) for c in ce_ev], len(ce_loops), ce_ok))
    ok &= ce_ok
    rc = [c for c in calls(te) if cname(c) == "G.report_comparisons"]
    ok &= [ast.unparse(c.args[2]) for c in rc if len(c.args) > 2] == ["'test'"]
    fins = [c for c in calls(te) if cname(c) == "TG.finish_test_evaluation"]
    begins = [c for c in calls(te) if cname(c) == "TG.begin_test_evaluation"]
    print("begin calls %d, finish calls %d, begin inside a loop: %s | report_comparisons split %s" % (
        len(begins), len(fins), any(b in calls(f) for f in fors for b in begins), [ast.unparse(c.args[2]) for c in rc]))
    ok &= len(begins) == 1 and len(fins) == 1 and not any(b in calls(f) for f in fors for b in begins)
    tes = ast.parse(staged(repo, PKG + "pilot.py"))
    tev = func(tes, "test_evaluation_seconds")
    print("test_evaluation_seconds: %s" % " | ".join(ast.unparse(x) for x in tev.body[1:]))

    print("\n== b. pilot.run_test_evaluate")
    rte = func(pilot, "run_test_evaluate")
    t = [n for n in rte.body if isinstance(n, ast.Try)]
    t = t[0] if len(t) == 1 else None
    types = [ast.unparse(h.type) for h in t.handlers] if t else []
    print("handlers %s" % types)
    ok &= types == ["(ProtocolStop, TD.PreconditionFailed)", "Exception"]
    h1, h2 = t.handlers
    if1 = [n for n in h1.body if isinstance(n, ast.If)]
    if1_ok = (len(if1) == 1 and ast.unparse(if1[0].test) == "not (p.root / TG.MARKER_REL).exists() and code != 'ST10'"
              and isinstance(if1[0].body[-1], ast.Return) and not any(cname(c) == "final_record" for c in calls(if1[0])))
    print("handler 1: %r -> return without final_record: %s" % (ast.unparse(if1[0].test) if if1 else None, if1_ok))
    ok &= if1_ok
    if2 = [n for n in h2.body if isinstance(n, ast.If)]
    if2_ok = (len(if2) == 1 and ast.unparse(if2[0].test) == "not (p.root / TG.MARKER_REL).exists()"
              and [ast.unparse(x) for x in if2[0].body] == ["raise"])
    crash_ok = any(ast.unparse(x) == "crash = e" for x in h2.body) and any(
        "'BLOCKED'" in ast.unparse(x) and ast.unparse(x).startswith("status, actual, nxt =") for x in h2.body)
    print("handler 2: %r -> bare raise: %s | else crash = e, status 'BLOCKED': %s" % (
        ast.unparse(if2[0].test) if if2 else None, if2_ok, crash_ok))
    ok &= if2_ok and crash_ok
    after = rte.body[rte.body.index(t) + 1:]
    after_s = [ast.unparse(x) for x in after]
    print("after the try: %s" % after_s)
    ok &= after_s[0].startswith("final_record(p, 'test-evaluate', status") and after_s[1] == "if crash is not None:\n    raise crash"
    tg = ast.parse(staged(repo, PKG + "testgate.py"))
    td = ast.parse(staged(repo, PKG + "test_data.py"))

    def bases(tree, name):
        return [ast.unparse(b) for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name for b in n.bases]
    print("class bases: TestAlreadyEvaluated %s | PreconditionFailed %s" % (bases(tg, "TestAlreadyEvaluated"),
                                                                           bases(td, "PreconditionFailed")))
    ok &= bases(tg, "TestAlreadyEvaluated") == ["Exception"] and bases(td, "PreconditionFailed") == ["Exception"]
    tae_doc = ast.get_docstring([n for n in ast.walk(tg) if isinstance(n, ast.ClassDef) and n.name == "TestAlreadyEvaluated"][0])
    print("TestAlreadyEvaluated docstring: %r" % tae_doc)
    print("=> before the marker exists: ProtocolStop / PreconditionFailed -> no record, except code ST10 -> record; any "
          "other exception propagates without a record. Once the marker file exists in the working tree: every "
          "ProtocolStop / PreconditionFailed -> record (status of the stop or BLOCKED); any other exception, "
          "TestAlreadyEvaluated included, -> record with status BLOCKED, message 'crash after the TEST marker', then "
          "re-raised")

    print("\n== c. CD13: what finish_test_evaluation commits")
    res_assign = [n for n in ast.walk(te) if isinstance(n, ast.Assign) and [ast.unparse(x) for x in n.targets] == ["result"]]
    keys, summ = None, []
    if len(res_assign) == 1 and isinstance(res_assign[0].value, ast.Call) and cname(res_assign[0].value) == "plain":
        d = res_assign[0].value.args[0]
        keys = [ast.unparse(k) for k in d.keys] if isinstance(d, ast.Dict) else None
        summ = [ast.unparse(v) for k, v in zip(d.keys, d.values) if ast.unparse(k) == "'summaries'"]
    fin_arg = [ast.unparse(c.args[2]) for c in fins]
    print("result = plain({...}) keys %s | summaries value %s | finish called with %s" % (keys, summ, fin_arg))
    ok &= keys == ["'kind'", "'frozen_commit'", "'values'", "'final'", "'comparisons'", "'summaries'"] and fin_arg == ["result"]
    ok &= summ == ["{m: _summary_record(s) for m, s in summaries.items()}"]
    sr = func(pilot, "_summary_record")
    print("_summary_record body: %s" % ast.unparse(sr.body[-1]))
    ok &= "not k.startswith('general_')" in ast.unparse(sr.body[-1])
    det_assign = [ast.unparse(n) for n in ast.walk(te) if isinstance(n, ast.Assign) and "TEST_DETAILS_DIR" in ast.unparse(n)]
    print("details directory: %s" % det_assign)
    ok &= any("p.work / TEST_DETAILS_DIR" in x for x in det_assign)
    init = [n for n in ast.walk(pilot) if isinstance(n, ast.ClassDef) and n.name == "Pilot"][0]
    init_f = [n for n in init.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"][0]
    refuse = any(isinstance(n, ast.If) and "outside(self.work, self.root)" in ast.unparse(n.test)
                 and any(isinstance(b, ast.Raise) for b in n.body) for n in ast.walk(init_f))
    print("Pilot.__init__ raises when the work directory is not outside the repository: %s" % refuse)
    ok &= refuse
    acts = [ast.unparse(n) for n in ast.walk(te) if isinstance(n, ast.Assign) and [ast.unparse(x) for x in n.targets] == ["actual"]]
    print("experiment record's Actual of test_evaluate: %s" % acts)

    print("\n== d. CD5 / CE5 / MAJOR 2: TEST generation")
    rtg = func(pilot, "run_test_generate")
    rtg_calls = [cname(c) for c in calls(rtg)]
    print("run_test_generate calls (source order): %s" % rtg_calls)
    sp = [c for c in calls(rtg) if cname(c) == "subprocess.run"]
    ok &= len(sp) == 1 and "test_generate_command" in rtg_calls and not any(x.startswith("TD.") for x in rtg_calls)
    over_ifs = [n for n in ast.walk(rtg) if isinstance(n, ast.If) and ast.unparse(n.test) == "over"]
    fr = [c for c in calls(rtg) if cname(c) == "final_record"]
    fr_in_if = len(over_ifs) == 1 and len(fr) == 1 and fr[0] in calls(over_ifs[0])
    stop_assign = [ast.unparse(n.value) for n in ast.walk(over_ifs[0]) if isinstance(n, ast.Assign)
                   and [ast.unparse(x) for x in n.targets] == ["stop"]] if over_ifs else []
    over_assign = [ast.unparse(n.value) for n in ast.walk(rtg) if isinstance(n, ast.Assign) and [ast.unparse(x) for x in n.targets] == ["over"]]
    print("over = %s (after subprocess.run: %s) | final_record calls %d, all inside `if over:` %s | its status %s | stop %s" % (
        over_assign, bool(over_assign) and line(first(rtg, lambda c: cname(c) == "st10_over_limit")) > sp[0].lineno, len(fr),
        fr_in_if, [ast.unparse(c.args[2]) for c in fr], stop_assign))
    ok &= over_assign == ["st10_over_limit(p)"] and fr_in_if and [ast.unparse(c.args[2]) for c in fr] == ["'BLOCKED'"]
    ok &= len(stop_assign) == 1 and "'code': 'ST10'" in stop_assign[0] and "'status': 'BLOCKED'" in stop_assign[0]
    sol = func(pilot, "st10_over_limit")
    sol_s = ast.unparse(sol)
    sol_ok = ("R.committed_json(p.root, TG.ST10_RECORD_REL)" in sol_s and "except R.NotCommitted:\n        return []" in sol_s
              and "TG.over_limit(p.fz, rec.get('counts') or {})" in sol_s)
    print("st10_over_limit: committed record (R.committed_json), [] when not committed, TG.over_limit on its counts: %s" % sol_ok)
    ok &= sol_ok
    tgc = func(pilot, "test_generate_command")
    ret = [n for n in ast.walk(tgc) if isinstance(n, ast.Return)][0]
    print("test_generate_command returns %s" % ast.unparse(ret.value))
    ok &= ast.unparse(ret.value).startswith("[sys.executable, '-m', 'metrix_e1.test_data', '--inputs'")
    files = sorted(f for f in os.listdir(os.path.join(repo, PKG)) if f.endswith(".py"))
    srcs = {PKG + f: staged(repo, PKG + f) for f in files}
    srcs["metrix/e1-pilot/run_pilot.py"] = staged(repo, "metrix/e1-pilot/run_pilot.py")
    sites = {"generate_test": [], "run_test_part": [], "begin_test_evaluation": [], "finish_test_evaluation": []}
    td_attrs = set()
    for rel, text in srcs.items():
        tree = ast.parse(text)
        enc = enclosing_functions(tree)
        for c in ast.walk(tree):
            if isinstance(c, ast.Call):
                last = cname(c).split(".")[-1]
                if last in sites:
                    sites[last].append("%s:%d in %s" % (rel.split("/")[-1], c.lineno, enc.get(id(c))))
        if rel.endswith("/pilot.py"):
            td_attrs = {ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                        and isinstance(n.value, ast.Name) and n.value.id == "TD"}
        imp = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and "test_data" in n.module
               and any(a.name in ("generate_test", "main") for a in n.names)]
        if imp:
            print("  %s imports generate_test / main of test_data by name: %s" % (rel, imp))
            ok = False
    for k, v in sites.items():
        print("call sites of %s: %s" % (k, v))
    ok &= [x.split(" in ")[1] for x in sites["generate_test"]] == ["main"] and sites["generate_test"][0].startswith("test_data.py")
    ok &= [x.split(" in ")[1] for x in sites["run_test_part"]] == ["main"] and sites["run_test_part"][0].startswith("test_data.py")
    print("attributes of test_data (TD.*) used in pilot.py: %s" % sorted(td_attrs))
    ok &= td_attrs == {"TD.check_preconditions", "TD.PreconditionFailed"}

    print("\n== e. MAJOR 9: smoke step 8")
    s8 = func(pilot, "step8_smoke_refusal")
    sp8 = [c for c in calls(s8) if cname(c) == "subprocess.run"]
    fifs = [n for n in ast.walk(s8) if isinstance(n, ast.If) and ast.unparse(n.test) == "formal"
            and any(isinstance(b, ast.Raise) and "ImplementationFail" in ast.unparse(b) for b in n.body)]
    fl = [ast.unparse(n.value) for n in ast.walk(s8) if isinstance(n, ast.Assign) and [ast.unparse(x) for x in n.targets] == ["formal"]]
    print("formal = %s" % fl)
    e_ok = (len(sp8) == 1 and "test_generate_command" in ast.unparse(sp8[0]) and len(fifs) == 1 and fifs[0].lineno < sp8[0].lineno
            and len(fl) == 1 and all(x in fl[0] for x in ("R.GATE0_RECORD_REL", "R.SELECTION_FREEZE_REL", "TG.ST10_RECORD_REL",
                                                          "TG._blob(p.root, 'HEAD:%s' % rel) is not None", "(p.root / rel).exists()")))
    print("`if formal: raise ImplementationFail` at line %s before subprocess.run(test_generate_command(...)) at line %s; formal "
          "names the Gate 0, freeze and ST10 records in HEAD or the working tree: %s" % (
              fifs[0].lineno if fifs else None, sp8[0].lineno if sp8 else None, e_ok))
    ok &= e_ok

    print("\n== f. CA20: production callers of begin / finish")
    b_ok = sites["begin_test_evaluation"] == ["pilot.py:%d in test_evaluate" % begins[0].lineno]
    f_ok = sites["finish_test_evaluation"] == ["pilot.py:%d in test_evaluate" % fins[0].lineno]
    print("begin only in pilot.test_evaluate: %s | finish only in pilot.test_evaluate: %s" % (b_ok, f_ok))
    ok &= b_ok and f_ok

    print("\n== g. fetch: begin / finish yes, the per-call checks no (ruling 2026-11-27 item 1)")

    def fcalls(name):
        return [cname(c) for c in calls(func(tg, name))]
    cc_fetch = any(isinstance(n, ast.Constant) and n.value == "fetch" for n in ast.walk(func(tg, "check_checkout")))
    g_ok = (cc_fetch and "refuse_if_marker" in fcalls("begin_test_evaluation") and "check_checkout" in fcalls("refuse_if_marker")
            and "check_commit_preconditions" in fcalls("finish_test_evaluation") and "check_checkout" in fcalls("check_commit_preconditions"))
    print("check_checkout runs git fetch %s; begin -> refuse_if_marker -> check_checkout, finish -> check_commit_preconditions "
          "-> check_checkout: %s" % (cc_fetch, g_ok))
    ok &= g_ok
    for name in ("require_test_session", "_check_session_checkout", "claim_checkpoint"):
        fc = fcalls(name)
        bad = [x for x in fc if x in ("check_checkout", "check_commit_preconditions", "refuse_if_marker")]
        lit = any(isinstance(n, ast.Constant) and n.value == "fetch" for n in ast.walk(func(tg, name)))
        print("  %-24s calls check_checkout / check_commit_preconditions / refuse_if_marker: %s | 'fetch' literal: %s" % (name, bad, lit))
        ok &= not bad and not lit

    print("\n== h. run_pilot.py")
    rp = ast.parse(srcs["metrix/e1-pilot/run_pilot.py"])
    steps = [c for c in calls(rp) if cname(c).endswith(".add_argument") and c.args and ast.unparse(c.args[0]) == "'--steps'"]
    smoke_parser = [ast.unparse(n.targets[0]) for n in ast.walk(rp) if isinstance(n, ast.Assign)
                    and isinstance(n.value, ast.Call) and "add_parser('smoke')" in ast.unparse(n.value)]
    print("--steps added %d time(s), on %s | smoke sub-parser %s" % (len(steps), [ast.unparse(c.func.value) for c in steps], smoke_parser))
    ok &= len(steps) == 1 and [ast.unparse(c.func.value) for c in steps] == smoke_parser
    bm = func(rp, "build_mode")
    print("build_mode: %s" % ast.unparse(bm.body[-1]))
    ok &= ast.unparse(bm.body[-1]) == "return M.smoke_mode(args.steps) if args.cmd == 'smoke' else M.FORMAL_MODE"
    mc = [cname(c) for c in calls(func(rp, "main"))]
    print("main calls P.run_test_generate %s, P.run_test_evaluate %s" % ("P.run_test_generate" in mc, "P.run_test_evaluate" in mc))
    ok &= "P.run_test_generate" in mc and "P.run_test_evaluate" in mc
    return bool(ok)


run(main)
