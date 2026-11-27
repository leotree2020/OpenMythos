"""ic7_04_static (implementation stage C, C2 work commit (staged tree b80c9062, parent f8139f9), round 1; task 4, static
part): the production callers of the TEST paths (DEFERRED_MINORS 1.27 CA20, 1.30 CD5 / CD13, 1.31 CE5; Review Gate
ruling of 2026-11-27 item 1), read with Python's ast from the STAGED blobs (git cat-file :path), never imported.
  a. pilot.test_evaluate, in source order: formal-mode check -> TD.check_preconditions (the authorization) -> the TEST
     files read -> checkpoint file check over models[1:] (FZ.file_sha256 against the committed run record, raise
     ProtocolStop BLOCKED) -> TG.begin_test_evaluation -> a loop over `models` with exactly one p.evaluate(...,
     split="test", test_session=session, checkpoint_name=name) -> G.compute_test_values -> G.judge_test ->
     G.report_comparisons(..., "test") -> TG.finish_test_evaluation; `models` = TG.evaluated_models(...); no other
     evaluation call in the function.
  b. pilot.run_test_evaluate: test_evaluate inside try; the handler catches exactly (ProtocolStop, TD.PreconditionFailed);
     it returns without final_record when the marker file does not exist, and final_record is called after the try
     otherwise; TestAlreadyEvaluated and PreconditionFailed are not ProtocolStop subclasses (class bases); exceptions
     of other types are not caught (no record: see ic7_04c for the dynamic observation).
  c. CD13: the result passed to finish_test_evaluation is plain({...}) with keys kind, frozen_commit, values, final,
     comparisons, summaries; summaries go through _summary_record, which drops keys starting with "general_"; the
     per-question details are written under p.work / TEST_DETAILS_DIR; Pilot.__init__ refuses a work directory inside
     the repository.
  d. CD5 / CE5: run_test_generate runs subprocess.run(test_generate_command(...)) and calls nothing of test_data;
     test_generate_command is [sys.executable, "-m", "metrix_e1.test_data", ...]; package-wide (src/metrix_e1/*.py and
     run_pilot.py), generate_test and run_test_part are called only inside test_data.main; pilot.py uses only
     TD.check_preconditions and TD.PreconditionFailed of test_data; step8_smoke_refusal runs the same command.
  e. CA20: begin_test_evaluation and finish_test_evaluation are called (package-wide) only by pilot.test_evaluate.
  f. ruling 2026-11-27 item 1: begin (refuse_if_marker, check_commit_preconditions) and finish
     (check_commit_preconditions) reach check_checkout, which runs `git fetch`; require_test_session,
     _check_session_checkout and claim_checkpoint (the per-call checks) call none of them and hold no "fetch".
  g. run_pilot.py: --steps is added once, to the smoke sub-parser; test-generate / test-evaluate call
     P.run_test_generate / P.run_test_evaluate.
Data Auditor's own script; the Executor's code is parsed, not imported or executed.
usage: python -I -B ic7_04_static.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import subprocess
from ia_common import run

PKG = "metrix/e1-pilot/src/metrix_e1/"


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


def first_line(node, pred):
    xs = [c.lineno for c in calls(node) if pred(c)]
    return min(xs) if xs else None


def kw(c, name):
    for k in c.keywords:
        if k.arg == name:
            return ast.unparse(k.value)
    return None


def enclosing_functions(tree):
    """{id(call node): name of the innermost function definition around it}."""
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

    print("== a. pilot.test_evaluate, order of the TEST path (staged blob, source lines)")
    seq = {
        "formal-mode check (raise when not p.mode.formal)": next(
            (n.lineno for n in ast.walk(te) if isinstance(n, ast.If) and "p.mode.formal" in ast.unparse(n.test)
             and any(isinstance(b, ast.Raise) for b in n.body)), None),
        "TD.check_preconditions": first_line(te, lambda c: cname(c) == "TD.check_preconditions"),
        "TEST files read (FZ.read_jsonl)": first_line(te, lambda c: cname(c) == "FZ.read_jsonl"),
        "checkpoint file sha256 (FZ.file_sha256)": first_line(te, lambda c: cname(c) == "FZ.file_sha256"),
        "TG.begin_test_evaluation": first_line(te, lambda c: cname(c) == "TG.begin_test_evaluation"),
        "p.evaluate(split='test')": first_line(te, lambda c: cname(c) == "p.evaluate"),
        "G.compute_test_values": first_line(te, lambda c: cname(c) == "G.compute_test_values"),
        "G.judge_test": first_line(te, lambda c: cname(c) == "G.judge_test"),
        "G.report_comparisons": first_line(te, lambda c: cname(c) == "G.report_comparisons"),
        "TG.finish_test_evaluation": first_line(te, lambda c: cname(c) == "TG.finish_test_evaluation"),
    }
    for k, v in seq.items():
        print("  line %-5s %s" % (v, k))
    lines = list(seq.values())
    ordered = None not in lines and lines == sorted(lines)
    print("all present and in this order: %s" % ordered)
    ok &= ordered
    fors = [n for n in ast.walk(te) if isinstance(n, ast.For)]
    ck_loop = [f for f in fors if ast.unparse(f.iter) == "models[1:]"]
    ev_loop = [f for f in fors if ast.unparse(f.iter) == "models"]
    ck_ok = (len(ck_loop) == 1 and any(cname(c) == "FZ.file_sha256" for c in calls(ck_loop[0]))
             and any(isinstance(n, ast.Raise) and "ProtocolStop" in ast.unparse(n) and "'BLOCKED'" in ast.unparse(n)
                     for n in ast.walk(ck_loop[0])))
    print("checkpoint check: one loop over models[1:] with FZ.file_sha256 and raise ProtocolStop(..., 'BLOCKED', ...): %s" % ck_ok)
    ok &= ck_ok
    models_assign = [ast.unparse(n.value) for n in ast.walk(te) if isinstance(n, ast.Assign)
                     and [ast.unparse(t) for t in n.targets] == ["models"]]
    print("models = %s" % models_assign)
    ok &= models_assign == ["TG.evaluated_models(p.contract, selected)"]
    evs_all = [c for c in calls(te) if cname(c) in ("p.evaluate", "E.evaluate_model", "evaluate_model", "self.evaluate")]
    evs_loop = [c for c in calls(ev_loop[0]) if c in evs_all] if len(ev_loop) == 1 else []
    ev_ok = (len(ev_loop) == 1 and len(evs_all) == 1 and len(evs_loop) == 1
             and kw(evs_loop[0], "split") == "'test'" and kw(evs_loop[0], "test_session") == "session"
             and kw(evs_loop[0], "checkpoint_name") == "name")
    print("evaluation calls in test_evaluate %d, inside the single loop over `models` %d: %s | split=%s test_session=%s "
          "checkpoint_name=%s | ok %s" % (len(evs_all), len(evs_loop), [cname(c) for c in evs_all],
                                          kw(evs_all[0], "split") if evs_all else None,
                                          kw(evs_all[0], "test_session") if evs_all else None,
                                          kw(evs_all[0], "checkpoint_name") if evs_all else None, ev_ok))
    ok &= ev_ok
    rc = [c for c in calls(te) if cname(c) == "G.report_comparisons"]
    print("report_comparisons split argument: %s" % [ast.unparse(c.args[2]) for c in rc if len(c.args) > 2])
    ok &= [ast.unparse(c.args[2]) for c in rc if len(c.args) > 2] == ["'test'"]
    begins = [c for c in calls(te) if cname(c) == "TG.begin_test_evaluation"]
    fins = [c for c in calls(te) if cname(c) == "TG.finish_test_evaluation"]
    print("begin calls %d, finish calls %d, begin inside a loop: %s" % (
        len(begins), len(fins), any(b in calls(f) for f in fors for b in begins)))
    ok &= len(begins) == 1 and len(fins) == 1 and not any(b in calls(f) for f in fors for b in begins)

    print("\n== b. pilot.run_test_evaluate")
    rte = func(pilot, "run_test_evaluate")
    tries = [n for n in rte.body if isinstance(n, ast.Try)]
    t = tries[0] if len(tries) == 1 else None
    caught = ast.unparse(t.handlers[0].type) if t and len(t.handlers) == 1 else None
    in_try = t is not None and any(cname(c) == "test_evaluate" for c in calls(ast.Module(body=t.body, type_ignores=[])))
    h = t.handlers[0] if t and t.handlers else None
    marker_if = [n for n in (h.body if h else []) if isinstance(n, ast.If) and "MARKER_REL" in ast.unparse(n.test)
                 and ast.unparse(n.test).startswith("not ")]
    ret_no_rec = bool(marker_if) and any(isinstance(x, ast.Return) for x in marker_if[0].body) and not any(
        cname(c) == "final_record" for c in calls(marker_if[0]))
    after = [n for n in rte.body[rte.body.index(t) + 1:]] if t else []
    fr_after = any(cname(c) == "final_record" for n in after for c in calls(n))
    fr_in_handler = any(cname(c) == "final_record" for c in calls(h)) if h else False
    print("test_evaluate inside the try: %s | handler catches %s | 'if not <marker exists>: ... return' without "
          "final_record in the handler: %s | final_record called in the handler: %s | final_record after the try: %s" % (
              in_try, caught, ret_no_rec, fr_in_handler, fr_after))
    ok &= in_try and caught == "(ProtocolStop, TD.PreconditionFailed)" and ret_no_rec and fr_after and not fr_in_handler
    tg = ast.parse(staged(repo, PKG + "testgate.py"))
    td = ast.parse(staged(repo, PKG + "test_data.py"))
    errs = ast.parse(staged(repo, PKG + "errors.py"))

    def bases(tree, name):
        return [ast.unparse(b) for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name for b in n.bases]
    print("class bases: TestAlreadyEvaluated %s | PreconditionFailed %s | ImplementationFail %s | ST12Error %s" % (
        bases(tg, "TestAlreadyEvaluated"), bases(td, "PreconditionFailed"), bases(errs, "ImplementationFail"),
        bases(errs, "ST12Error")))
    ok &= bases(tg, "TestAlreadyEvaluated") == ["Exception"] and bases(td, "PreconditionFailed") == ["Exception"]
    print("=> after the marker: a ProtocolStop (incl. ImplementationFail, ST12Error) or PreconditionFailed is recorded "
          "(final_record); TestAlreadyEvaluated and any other exception type (e.g. RuntimeError, an out-of-memory error) "
          "propagate without an experiment record")

    print("\n== c. CD13: what finish_test_evaluation commits")
    res_assign = [n for n in ast.walk(te) if isinstance(n, ast.Assign) and [ast.unparse(x) for x in n.targets] == ["result"]]
    keys = None
    if len(res_assign) == 1 and isinstance(res_assign[0].value, ast.Call) and cname(res_assign[0].value) == "plain":
        d = res_assign[0].value.args[0]
        keys = [ast.unparse(k) for k in d.keys] if isinstance(d, ast.Dict) else None
        summ = [ast.unparse(v) for k, v in zip(d.keys, d.values) if ast.unparse(k) == "'summaries'"]
    else:
        summ = []
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

    print("\n== d. CD5 / CE5: TEST generation")
    rtg = func(pilot, "run_test_generate")
    rtg_calls = [cname(c) for c in calls(rtg)]
    print("run_test_generate calls: %s" % rtg_calls)
    ok &= "subprocess.run" in rtg_calls and "test_generate_command" in rtg_calls and not any(x.startswith("TD.") for x in rtg_calls)
    tgc = func(pilot, "test_generate_command")
    ret = [n for n in ast.walk(tgc) if isinstance(n, ast.Return)][0]
    print("test_generate_command returns %s" % ast.unparse(ret.value))
    ok &= ast.unparse(ret.value).startswith("[sys.executable, '-m', 'metrix_e1.test_data', '--inputs'")
    s8 = func(pilot, "step8_smoke_refusal")
    print("step8_smoke_refusal runs subprocess.run(test_generate_command(...)): %s" % any(
        cname(c) == "subprocess.run" and "test_generate_command" in ast.unparse(c) for c in calls(s8)))
    ok &= any(cname(c) == "subprocess.run" and "test_generate_command" in ast.unparse(c) for c in calls(s8))
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
        if rel.endswith("pilot.py") and not rel.endswith("run_pilot.py"):
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

    print("\n== e. CA20: production callers of begin / finish")
    ok &= sites["begin_test_evaluation"] == ["pilot.py:%d in test_evaluate" % begins[0].lineno]
    ok &= sites["finish_test_evaluation"] == ["pilot.py:%d in test_evaluate" % fins[0].lineno]
    print("begin only in pilot.test_evaluate: %s | finish only in pilot.test_evaluate: %s" % (
        sites["begin_test_evaluation"] == ["pilot.py:%d in test_evaluate" % begins[0].lineno],
        sites["finish_test_evaluation"] == ["pilot.py:%d in test_evaluate" % fins[0].lineno]))

    print("\n== f. fetch: begin / finish yes, the per-call checks no (ruling 2026-11-27 item 1)")

    def fcalls(name):
        return [cname(c) for c in calls(func(tg, name))]
    cc_fetch = any(isinstance(n, ast.Constant) and n.value == "fetch" for n in ast.walk(func(tg, "check_checkout")))
    print("check_checkout runs git fetch: %s" % cc_fetch)
    print("begin_test_evaluation calls refuse_if_marker %s, check_commit_preconditions %s | refuse_if_marker calls "
          "check_checkout %s | check_commit_preconditions calls check_checkout %s | finish calls check_commit_preconditions %s" % (
              "refuse_if_marker" in fcalls("begin_test_evaluation"), "check_commit_preconditions" in fcalls("begin_test_evaluation"),
              "check_checkout" in fcalls("refuse_if_marker"), "check_checkout" in fcalls("check_commit_preconditions"),
              "check_commit_preconditions" in fcalls("finish_test_evaluation")))
    ok &= cc_fetch and "refuse_if_marker" in fcalls("begin_test_evaluation") and "check_checkout" in fcalls("refuse_if_marker") \
        and "check_commit_preconditions" in fcalls("finish_test_evaluation") and "check_checkout" in fcalls("check_commit_preconditions")
    for name in ("require_test_session", "_check_session_checkout", "claim_checkpoint"):
        fc = fcalls(name)
        bad = [x for x in fc if x in ("check_checkout", "check_commit_preconditions", "refuse_if_marker")]
        lit = any(isinstance(n, ast.Constant) and n.value == "fetch" for n in ast.walk(func(tg, name)))
        print("  %-24s calls check_checkout / check_commit_preconditions / refuse_if_marker: %s | 'fetch' literal: %s" % (name, bad, lit))
        ok &= not bad and not lit

    print("\n== g. run_pilot.py")
    rp = ast.parse(srcs["metrix/e1-pilot/run_pilot.py"])
    steps = [c for c in calls(rp) if cname(c).endswith(".add_argument") and c.args and ast.unparse(c.args[0]) == "'--steps'"]
    print("--steps added %d time(s), on %s" % (len(steps), [ast.unparse(c.func.value) for c in steps]))
    smoke_parser = [ast.unparse(n.targets[0]) for n in ast.walk(rp) if isinstance(n, ast.Assign)
                    and isinstance(n.value, ast.Call) and "add_parser('smoke')" in ast.unparse(n.value)]
    print("the smoke sub-parser is assigned to %s" % smoke_parser)
    ok &= len(steps) == 1 and [ast.unparse(c.func.value) for c in steps] == smoke_parser
    bm = func(rp, "build_mode")
    print("build_mode: %s" % ast.unparse(bm.body[-1]))
    ok &= ast.unparse(bm.body[-1]) == "return M.smoke_mode(args.steps) if args.cmd == 'smoke' else M.FORMAL_MODE"
    mc = [cname(c) for c in calls(func(rp, "main"))]
    print("main calls P.run_test_generate %s, P.run_test_evaluate %s" % ("P.run_test_generate" in mc, "P.run_test_evaluate" in mc))
    ok &= "P.run_test_generate" in mc and "P.run_test_evaluate" in mc
    return bool(ok)


run(main)
