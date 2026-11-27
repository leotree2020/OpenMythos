"""ic9_04_static (implementation stage C, C2 second fix commit (staged tree a6ce8a0e, parent 0cbee197), round 1; task 3
of the invocation): static reading, with Python's ast, of the STAGED blobs (git cat-file :path), never imported. My
ic8_04_static rewritten for the changed code.
  a. pilot.test_evaluate: every check before the marker sits before TG.begin_test_evaluation, in source order:
     formal-mode check -> TD.check_preconditions -> TG.code_commit -> p.start_checks('test-evaluate') -> p.device_check
     -> p.load_data -> TEST files read -> committed freeze / Gate 0 / step 2 / step 3 records -> checkpoint files over
     models[1:] -> test_evaluation_seconds(p.contract, step2['preflight']['timing']) -> p.before_run(look_ahead) (ST7)
     -> p.base_model -> T.state_sha256 -> N's hash vs the step 3 record (raise ProtocolStop BLOCKED) ->
     p.marker_before_begin = marker exists -> p.begin_called = True -> begin (the next statement) -> ONE evaluation
     call inside the single loop over `models` -> compute_test_values -> judge_test -> report_comparisons(..., 'test')
     -> finish. load_data and the TEST file reads now sit inside the pre-marker try, whose single handler
     (R.NotCommitted, KeyError, OSError, TypeError, ValueError) raises ProtocolStop BLOCKED; the GPU-clock part is one
     try / finally p.close_clock(). begin_called / marker_before_begin are assigned only in Pilot.__init__ (False /
     None) and in test_evaluate right before begin.
  b. pilot.begun_by_this_process and run_test_evaluate: three handlers in this order: (ProtocolStop,
     TD.PreconditionFailed): begun = begun_by_this_process(p); `if not begun and code is None` -> return, no
     final_record; TG.TestAlreadyEvaluated: p.close_clock(); bare raise (no record); BaseException: bare raise when
     not begun_by_this_process(p), otherwise crash = e, status BLOCKED; final_record after the try; then `raise crash`.
     TestAlreadyEvaluated's base is Exception (not ProtocolStop / PreconditionFailed): handler 1 cannot take it; it is
     raised only in testgate.refuse_if_marker, which only begin calls, as its first statement, before the marker is
     written.
  c. CD13: as before.
  d. run_test_generate: formal check -> TG.code_commit -> p.start_checks('test-generate') -> before =
     TG._blob(p.root, 'HEAD:%s' % TG.ST10_RECORD_REL) -> the single subprocess.run(test_generate_command(...)) ->
     over = st10_over_limit(p) if before is None else [] -> final_record only inside `if over:` (BLOCKED, ST10).
     CD5: generate_test / run_test_part only in test_data.main.
  e. MAJOR 9: smoke step 8 refusal (unchanged).
  f. CA20: begin / finish called only by pilot.test_evaluate.
  g. ruling 2026-11-27 item 1: begin and finish reach check_checkout (git fetch); the per-call checks do not.
  h. run_pilot.py: --steps only on the smoke sub-parser; one Pilot per main() call.
  i. ST7 look-ahead of the runs: Pilot.run_seconds multiplies the per-step time by a_factor only when spec.arm == 'A';
     its terms; Pilot.eval_seconds by what is loaded first; every p.before_run call site with its argument and the
     load that follows it (step3 'load' -> p.base_model; train_and_evaluate run_seconds(spec) -> p.base_model,
     eval_seconds(None) -> p.evaluate(reloaded) without a load; step7 'reload' -> p.load_checkpoint).
  j. test_evaluation_seconds: its terms (load_s once, reload_s x test_file_hashes, per_eval x test_models, hash_s x
     test_state_hashes, file_hash_s x test_file_hashes; per_eval = DEV seconds x TEST / DEV questions per fact).
  k. Pilot.commit: TG.commit_paths before the paths leave p.uncommitted; start_checks: ledger, freeze, checkpoints.
Data Auditor's own script; the Executor's code is parsed, not imported or executed.
usage: python -I -B ic9_04_static.py <repo_root>"""
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


def assign_line(node, target, value):
    hits = [n.lineno for n in ast.walk(node) if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == [target]
            and ast.unparse(n.value) == value]
    return hits[0] if len(hits) == 1 else None


def stmt_lists(node):
    """Every statement list (body, orelse, finalbody, handler bodies) under node."""
    for n in ast.walk(node):
        for f in ("body", "orelse", "finalbody"):
            v = getattr(n, f, None)
            if isinstance(v, list) and v and isinstance(v[0], ast.stmt):
                yield v


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
        ("p.marker_before_begin = (p.root / TG.MARKER_REL).exists()", assign_line(te, "p.marker_before_begin",
                                                                                 "(p.root / TG.MARKER_REL).exists()")),
        ("p.begin_called = True", assign_line(te, "p.begin_called", "True")),
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
    adj = None
    for body in stmt_lists(te):
        txt = [ast.unparse(x) for x in body]
        for i, x in enumerate(txt):
            if x == "p.begin_called = True":
                adj = (txt[i - 1] if i else None, txt[i + 1] if i + 1 < len(txt) else None)
    print("statement before `p.begin_called = True`: %r | statement after it: %r" % adj if adj else "p.begin_called = True not found")
    ok &= adj == ("p.marker_before_begin = (p.root / TG.MARKER_REL).exists()",
                  "session = TG.begin_test_evaluation(fz, auth, data, base_sha)")
    sets = []
    for c_ in ast.walk(pilot):
        if isinstance(c_, (ast.FunctionDef,)):
            for n in ast.walk(c_):
                if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                    tg_ = n.targets if isinstance(n, ast.Assign) else [n.target]
                    for t_ in tg_:
                        for e in ast.walk(t_):
                            if isinstance(e, ast.Attribute) and e.attr in ("begin_called", "marker_before_begin"):
                                sets.append((c_.name, ast.unparse(n)))
    sets = sorted(set(sets))
    print("assignments to .begin_called / .marker_before_begin in pilot.py (function, statement): %s" % sets)
    ok &= sets == [("__init__", "self.begin_called = False"), ("__init__", "self.marker_before_begin = None"),
                   ("test_evaluate", "p.begin_called = True"),
                   ("test_evaluate", "p.marker_before_begin = (p.root / TG.MARKER_REL).exists()")]
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
            and ast.unparse(pre_try[0].handlers[0].type) == "(R.NotCommitted, KeyError, OSError, TypeError, ValueError)"
            and any(isinstance(n, ast.Raise) and "ProtocolStop" in ast.unparse(n) and "'BLOCKED'" in ast.unparse(n)
                    for n in ast.walk(pre_try[0].handlers[0])))
    pre_calls = [cname(c) for c in calls(ast.Module(body=pre_try[0].body, type_ignores=[]))] if len(pre_try) == 1 else []
    inside = {k: k in pre_calls for k in ("p.load_data", "FZ.read_jsonl", "R.committed_record", "R.committed_json",
                                          "FZ.file_sha256", "test_evaluation_seconds")}
    print("pre-marker reads inside a try whose single handler (R.NotCommitted, KeyError, OSError, TypeError, ValueError) "
          "raises ProtocolStop BLOCKED: %s | inside that try: %s" % (conv, inside))
    ok &= conv and all(inside.values())
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

    print("\n== b. pilot.begun_by_this_process and pilot.run_test_evaluate")
    bb = func(pilot, "begun_by_this_process")
    bb_ret = [ast.unparse(x) for x in bb.body if isinstance(x, ast.Return)]
    print("begun_by_this_process returns %s" % bb_ret)
    ok &= bb_ret == ["return p.begin_called and (not p.marker_before_begin) and (p.root / TG.MARKER_REL).exists()"]
    rte = func(pilot, "run_test_evaluate")
    t = [n for n in rte.body if isinstance(n, ast.Try)]
    t = t[0] if len(t) == 1 else None
    types = [ast.unparse(h.type) for h in t.handlers] if t else []
    print("handlers (in order) %s" % types)
    ok &= types == ["(ProtocolStop, TD.PreconditionFailed)", "TG.TestAlreadyEvaluated", "BaseException"]
    h1, h2, h3 = t.handlers
    h1s = [ast.unparse(x) for x in h1.body]
    if1 = [n for n in h1.body if isinstance(n, ast.If)]
    if1_ok = ("begun = begun_by_this_process(p)" in h1s and len(if1) == 1
              and ast.unparse(if1[0].test) == "not begun and code is None"
              and isinstance(if1[0].body[-1], ast.Return) and not any(cname(c) == "final_record" for c in calls(if1[0]))
              and h1s.index("begun = begun_by_this_process(p)") < h1.body.index(if1[0])
              and "code = getattr(e, 'stop', None)" in h1s)
    print("handler 1: code = e.stop; begun = begun_by_this_process(p); if %r -> return without final_record: %s" % (
        ast.unparse(if1[0].test) if if1 else None, if1_ok))
    rest1 = [x for x in h1s if x.startswith(("status =", "actual, nxt =", "stop ="))]
    print("handler 1 otherwise: %s" % rest1)
    ok &= if1_ok and any("'test_begun': begun" in x for x in rest1)
    h2s = [ast.unparse(x) for x in h2.body]
    print("handler 2 (TG.TestAlreadyEvaluated) body: %s" % h2s)
    ok &= h2s == ["p.close_clock()", "raise"]
    h3s = [ast.unparse(x) for x in h3.body]
    if3 = [n for n in h3.body if isinstance(n, ast.If)]
    if3_ok = (len(if3) == 1 and ast.unparse(if3[0].test) == "not begun_by_this_process(p)"
              and [ast.unparse(x) for x in if3[0].body] == ["raise"] and h3.body.index(if3[0]) < h3s.index("crash = e"))
    crash_ok = "crash = e" in h3s and any("'BLOCKED'" in x and x.startswith("status, actual, nxt =") and "'test_begun': True" in x
                                          for x in h3s)
    print("handler 3 (BaseException): %r -> bare raise: %s | else crash = e, status 'BLOCKED', test_begun True: %s" % (
        ast.unparse(if3[0].test) if if3 else None, if3_ok, crash_ok))
    ok &= if3_ok and crash_ok
    after = rte.body[rte.body.index(t) + 1:]
    after_s = [ast.unparse(x) for x in after]
    print("after the try: %s" % after_s)
    ok &= after_s[0].startswith("final_record(p, 'test-evaluate', status") and after_s[1] == "if crash is not None:\n    raise crash"
    tg = ast.parse(staged(repo, PKG + "testgate.py"))
    td = ast.parse(staged(repo, PKG + "test_data.py"))
    er = ast.parse(staged(repo, PKG + "errors.py"))
    stp = ast.parse(staged(repo, PKG + "stops.py"))

    def bases(tree, name):
        return [ast.unparse(b) for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name for b in n.bases]
    print("class bases: TestAlreadyEvaluated %s | PreconditionFailed %s | ProtocolStop %s | stops.Stop %s" % (
        bases(tg, "TestAlreadyEvaluated"), bases(td, "PreconditionFailed"), bases(er, "ProtocolStop"), bases(stp, "Stop")))
    ok &= bases(tg, "TestAlreadyEvaluated") == ["Exception"] and bases(td, "PreconditionFailed") == ["Exception"]
    ok &= bases(er, "ProtocolStop") == ["Exception"] and bases(stp, "Stop") == ["ProtocolStop"]
    tae_raises = []
    for n in ast.walk(tg):
        if isinstance(n, ast.FunctionDef):
            for r in ast.walk(n):
                if isinstance(r, ast.Raise) and r.exc is not None and "TestAlreadyEvaluated" in ast.unparse(r.exc):
                    tae_raises.append(n.name)
    rim_sites = [fn.name for fn in ast.walk(tg) if isinstance(fn, ast.FunctionDef)
                 for c in calls(fn) if cname(c) == "refuse_if_marker"]
    bg = func(tg, "begin_test_evaluation")
    bg_first = [ast.unparse(x) for x in bg.body if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant))]
    write_line = line(first(bg, lambda c: cname(c) == "path.write_bytes"))
    rim_line = line(first(bg, lambda c: cname(c) == "refuse_if_marker"))
    print("TestAlreadyEvaluated raised in testgate functions %s | refuse_if_marker called by %s | begin: refuse_if_marker at "
          "line %s, the marker written (path.write_bytes) at line %s; begin's first statements %s (refuse_if_marker the first check)" % (
              tae_raises, rim_sites, rim_line, write_line, bg_first[:3]))
    ok &= tae_raises == ["refuse_if_marker"] and rim_sites == ["begin_test_evaluation"] and rim_line < write_line
    ok &= bg_first[:3] == ["from . import contract as C", "root = Path(repo_root) if repo_root is not None else fz.repo_root",
                           "refuse_if_marker(root)"]
    tae_doc = ast.get_docstring([n for n in ast.walk(tg) if isinstance(n, ast.ClassDef) and n.name == "TestAlreadyEvaluated"][0])
    print("TestAlreadyEvaluated docstring: %r" % tae_doc)
    print("=> before this process began TEST (not begun_by_this_process): a ProtocolStop / PreconditionFailed without a "
          "stop code -> no record; with a stop code (ST7, ST8, ST9, ST10, ST12) -> record; TestAlreadyEvaluated -> no "
          "record, raised; any other BaseException -> raised, no record. After this process wrote the marker: every "
          "stop -> record (BLOCKED or its status); any other BaseException (KeyboardInterrupt included) -> record "
          "BLOCKED 'crash after the TEST marker', then re-raised")

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
    ok &= over_assign == ["st10_over_limit(p) if before is None else []"] and fr_in_if and [ast.unparse(c.args[2]) for c in fr] == ["'BLOCKED'"]
    before_assign = [(n.lineno, ast.unparse(n.value)) for n in ast.walk(rtg) if isinstance(n, ast.Assign)
                     and [ast.unparse(x) for x in n.targets] == ["before"]]
    cc_line = line(first(rtg, lambda c: cname(c) == "TG.code_commit"))
    sc = first(rtg, lambda c: cname(c) == "p.start_checks")
    fm = next((n.lineno for n in ast.walk(rtg) if isinstance(n, ast.If) and "p.mode.formal" in ast.unparse(n.test)
               and any(isinstance(b, ast.Raise) for b in n.body)), None)
    print("run_test_generate: formal check line %s | TG.code_commit line %s | p.start_checks(%s) line %s | before = %s | "
          "subprocess.run line %s" % (fm, cc_line, ast.unparse(sc.args[0]) if sc else None, line(sc), before_assign, sp[0].lineno))
    ok &= (len(before_assign) == 1 and before_assign[0][1] == "TG._blob(p.root, 'HEAD:%s' % TG.ST10_RECORD_REL)"
           and None not in (fm, cc_line, line(sc)) and fm < cc_line < line(sc) < before_assign[0][0] < sp[0].lineno
           and ast.unparse(sc.args[0]) == "'test-generate'")
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
    pil = [c for c in calls(rp) if cname(c) == "P.Pilot"]
    loops = [n for n in ast.walk(func(rp, "main")) if isinstance(n, (ast.For, ast.While))]
    cmd_calls = ("P.Pilot", "P.run_gate", "P.run_test_generate", "P.run_test_evaluate")
    in_loop = sorted({cname(c) for lp in loops for c in calls(lp) if cname(c) in cmd_calls})
    print("P.Pilot(...) constructed %d time(s), in main: %s | loops in main %d (%s); Pilot / run_* calls inside a loop: %s "
          "(one Pilot, one command per process)" % (len(pil), [enclosing_functions(rp).get(id(c)) for c in pil], len(loops),
                                                    [ast.unparse(lp).split("\n")[0] for lp in loops], in_loop))
    ok &= len(pil) == 1 and enclosing_functions(rp).get(id(pil[0])) == "main" and not in_loop

    print("\n== i. ST7 look-ahead of the runs (run_seconds, eval_seconds) and every p.before_run call site")
    cls = [n for n in ast.walk(pilot) if isinstance(n, ast.ClassDef) and n.name == "Pilot"][0]
    meth = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    rs = [ast.unparse(x) for x in meth["run_seconds"].body[1:]]
    es = [ast.unparse(x) for x in meth["eval_seconds"].body[1:]]
    print("run_seconds(%s): %s" % (", ".join(a.arg for a in meth["run_seconds"].args.args), rs))
    print("eval_seconds(%s): %s" % (", ".join(a.arg for a in meth["eval_seconds"].args.args), es))
    ok &= rs == ["if self.pre is None:\n    return 0.0", "q = self.pre", "factor = q['a_factor'] if spec.arm == 'A' else 1.0",
                 "return q['load_s'] + q['mean_step_s'] * self.contract.training.total_steps * factor + 2 * q['hash_s'] + "
                 "q['save_s'] + q['file_hash_s'] + q['reload_s'] + q['dev_evaluation_seconds']"]
    ok &= es == ["if self.pre is None:\n    return 0.0",
                 "return {'load': self.pre['load_s'], 'reload': self.pre['reload_s'], None: 0.0}[load] + "
                 "self.pre['dev_evaluation_seconds']"]
    enc_p = enclosing_functions(pilot)
    sites_br = []
    for fn in ast.walk(pilot):
        if isinstance(fn, ast.FunctionDef):
            for body in stmt_lists(fn):
                for i, st in enumerate(body):
                    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and cname(st.value) == "p.before_run":
                        nxt_ = ast.unparse(body[i + 1]).split("\n")[0] if i + 1 < len(body) else None
                        sites_br.append((fn.name, st.lineno, ast.unparse(st.value), nxt_))
    for x in sorted(set(sites_br), key=lambda x: x[1]):
        print("  %-20s line %-5d %-40s next statement: %s" % x)
    want_br = {("preflight", "p.before_run()", "t0 = time.perf_counter()"),
               ("step3", "p.before_run(p.eval_seconds('load'))", "model = p.base_model()"),
               ("train_and_evaluate", "p.before_run(p.run_seconds(spec))", "model = p.base_model()"),
               ("train_and_evaluate", "p.before_run(p.eval_seconds(None))", "ev = p.evaluate(reloaded, with_em=True, with_s_mapping=spec.arm == 'S')"),
               ("step7", "p.before_run(p.eval_seconds('reload'))", "model = p.load_checkpoint(spec, p.ckpt_dir / ('%s.pt' % spec.name))"),
               ("test_evaluate", "p.before_run(look_ahead)", "base = p.base_model()"),
               ("test_evaluate", "p.before_run()", "model = base if name == TG.BASE_MODEL else p.load_checkpoint(specs[name], p.ckpt_dir / ('%s.pt' % name))")}
    got_br = {(a, c, d) for a, _, c, d in sites_br}
    print("call sites == expected (function, call, next statement): %s%s" % (
        got_br == want_br, "" if got_br == want_br else " | missing %s | extra %s" % (want_br - got_br, got_br - want_br)))
    ok &= got_br == want_br
    other = sorted({(enc_p.get(id(c)), ast.unparse(c)) for c in calls(pilot) if cname(c) in ("p.run_seconds", "p.eval_seconds",
                                                                                               "self.run_seconds", "self.eval_seconds")})
    print("all run_seconds / eval_seconds calls: %s" % other)
    ok &= other == [("step3", "p.eval_seconds('load')"), ("step7", "p.eval_seconds('reload')"),
                    ("train_and_evaluate", "p.eval_seconds(None)"), ("train_and_evaluate", "p.run_seconds(spec)")]

    print("\n== j. test_evaluation_seconds and evaluation_plan")
    tev = func(pilot, "test_evaluation_seconds")
    tev_s = [ast.unparse(x) for x in tev.body[1:]]
    print("test_evaluation_seconds: %s" % tev_s)
    ok &= tev_s == ["n = evaluation_plan(contract)", "acc = contract.accounting",
                    "per_eval = pre['dev_evaluation_seconds'] * acc.test_questions_per_fact / acc.dev_questions_per_fact",
                    "return pre['load_s'] + n['test_file_hashes'] * pre['reload_s'] + n['test_models'] * per_eval + "
                    "n['test_state_hashes'] * pre['hash_s'] + n['test_file_hashes'] * pre['file_hash_s']"]
    ep = func(pilot, "evaluation_plan")
    print("evaluation_plan: %s" % [ast.unparse(x) for x in ep.body[1:]])

    print("\n== k. Pilot.commit and Pilot.start_checks")
    cm = [ast.unparse(x) for x in meth["commit"].body]
    i_cp = next((i for i, x in enumerate(cm) if "TG.commit_paths(" in x), None)
    i_rm = next((i for i, x in enumerate(cm) if x.startswith("for x in paths:") and "self.uncommitted.remove(x)" in x), None)
    print("commit: TG.commit_paths statement #%s, removal from self.uncommitted statement #%s (removal after the commit: %s)" % (
        i_cp, i_rm, None not in (i_cp, i_rm) and i_cp < i_rm))
    ok &= None not in (i_cp, i_rm) and i_cp < i_rm
    sc_ifs = [ast.unparse(x.test) for x in meth["start_checks"].body if isinstance(x, ast.If)]
    print("start_checks conditions in order: %s" % sc_ifs)
    ok &= len(sc_ifs) == 4 and "not self.ledger.path.exists()" in sc_ifs[1] and "R.SELECTION_FREEZE_REL" in sc_ifs[2] \
        and "self.ckpt_dir.glob('*.pt')" in sc_ifs[3] and sc_ifs[3].startswith("command == 'formal'")
    return bool(ok)


run(main)
