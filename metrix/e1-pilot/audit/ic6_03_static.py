"""ic6_03 (implementation stage C, C1 second submission, fix commit (staged tree ae5fcb2f, parent ae60e0f), round 1,
task 2, static). Every file is read as text (working tree, which equals the index: checked) and parsed with the
standard `ast` module; nothing of the package or the probe is imported or run. Sections a-h are those of my ic5_03
(re-run on the fix commit; section c now expects the isinstance guards of the fix); section i is new: the fix
commit against the Executor's description.
  a. test_data.main: the order of its top-level statements; check_commit_preconditions and refuse_if_st10_record come
     before generate_test, as unconditional top-level statements of main; generate_test is called nowhere else in the
     package;
  b. what the ST10 record, the marker and the result hold: their dict literals, the value expressions, the names each
     reads; the TEST rows reach them only as sha256 (rows_hashes_of -> rows_sha256; FZ.sha256_hex of the file bytes);
     the counts are report["checks"][c]["value"]; the result is the caller's `result` plus two fields;
  c. every TEST path reaches check_checkout (with its fetch) or the local marker-commit check before it writes or
     evaluates anything: call graph of testgate.py (transitive), test_data.main, evaluate.evaluate_model(split="test");
     the bodies of check_checkout, _check_session_checkout, check_commit_preconditions, _where, commit_paths, _push
     (every git argument list), against ruling items 1 and 2;
  d. the probe reports/impl_c/c1b_gate_probe.py against the interfaces: every call of a function of testgate,
     evaluate, leakage, frozen (positional count and keywords vs the parameters), every module attribute it reads or
     assigns exists, the TestSession attributes it reads; the probe's guard comes before its override of
     CANONICAL_REPO / PILOT_BRANCH and before the first operation;
  e. the searches the ruling removed (remote_heads, --all, --reflog, --full-history, rev-list, ls-remote --heads,
     _ever_committed, tags) have no remaining use in src/ or in the probe; the only ls-remote left is the pushed-ref
     check of _push;
  f. B25 (ruling item 3): interpretations.ENTRIES read as a literal; the status and ruling of B25; the entries a
     reading of pending() returns; pending_problem's callers;
  g. the refusal kinds per function (ruling item 4: environment -> BLOCKED, records -> ImplementationFail);
  h. the threat-model paragraph of tasks/IMPL_C1_RULING.md equals the text of the caller's instruction;
  i. the fix: (1) begin_test_evaluation: the two checks of the pushed commit (its marker blob == the bytes this begin
     wrote; its first parent holds no marker) come after commit_paths and before the session is built, registered and
     returned, and raise BLOCKED; `blob` and `head` are assigned once; _blob reads bytes (no text decoding) and
     returns None on any failure; the commit checked is the one _push pushed and verified with ls-remote;
     (2) claim_checkpoint and finish_test_evaluation (and require_test_session) start their session use with the
     guard `not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session` -> _refuse;
     (3) evaluate_model refuses with_s_mapping on a split other than dev before the TEST branch (before
     verify_authorization, require_test_session, require_gpu, claim_checkpoint), and only there; (4) sleep defaults
     None in commit_paths, begin, finish; _push binds time.sleep when called; (5) the BLOCKED text of check_checkout;
     (6) generate_test's docstring and its only caller; (7) the new and renamed tests exist in tests/test_testgate.py;
     (8) the Executor's records c1b_03 / c1b_04 (mutation counts, the one mutation not caught in c1b_03, pytest).
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ic6_03_static.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import glob
import re
import subprocess
from ia_common import run

PKG = "metrix/e1-pilot/src/metrix_e1"
PROBE = "metrix/e1-pilot/reports/impl_c/c1b_gate_probe.py"
RULING = "metrix/e1-pilot/tasks/IMPL_C1_RULING.md"
THREAT = ("防范对象：TEST 闸门要防的是「按规则办事的 Executor 在按 RUNBOOK 操作时，意外评测 TEST 两次，或在 ST10 不成立时评测 "
          "TEST」；不防有仓库写权限者的故意篡改（改写历史、伪造记录），这类风险由 GitHub 分支保护和审查记录承担。审查按此范围判定："
          "范围外的边缘情况记为 MINOR 并登记，不作为 BLOCKER。调用两份审查时，把本段防范对象原文写进调用文字。")
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, env=ENV)


def callee(n):
    f = n.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def funcs(tree):
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def body_of(fn):
    b = fn.body
    return b[1:] if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) else b


def calls_in(node):
    return [c for c in ast.walk(node) if isinstance(c, ast.Call)]


def first_call_line(fn, name, contains=None):
    ls = [c.lineno for c in calls_in(fn) if callee(c) == name and (contains is None or contains in ast.unparse(c))]
    return min(ls) if ls else None


def git_args(fn):
    """The argument lists of every _git(...) / subprocess git call in fn."""
    out = []
    for c in calls_in(fn):
        if callee(c) == "_git":
            out.append("%d: _git(%s)" % (c.lineno, ", ".join(ast.unparse(a) for a in c.args)))
    return out


def main():
    repo = sys.argv[1]
    ok = True
    src = {}
    for p in sorted(glob.glob(os.path.join(repo, PKG, "*.py"))):
        rel = os.path.relpath(p, repo)
        t = open(p, encoding="utf-8").read()
        idx = git(repo, "cat-file", "blob", ":" + rel).stdout.decode("utf-8")
        if t != idx:
            print("working tree != index for %s" % rel)
            ok = False
        src[os.path.basename(p)[:-3]] = t
    probe_src = open(os.path.join(repo, PROBE), encoding="utf-8").read()
    ok &= probe_src == git(repo, "cat-file", "blob", ":" + PROBE).stdout.decode("utf-8")
    print("package modules read (working tree == index for every one and for the probe: %s): %s" % (ok, sorted(src)))
    trees = {m: ast.parse(t) for m, t in src.items()}
    F = {m: funcs(t) for m, t in trees.items()}
    tg, td, ev = F["testgate"], F["test_data"], F["evaluate"]

    print("\n== a. test_data.main: top-level statements in order (line: statement)")
    mainf = td["main"]
    top = body_of(mainf)
    order = {}
    for st in top:
        txt = ast.unparse(st).split("\n")[0][:130]
        print("  %4d: %s" % (st.lineno, txt))
        for c in calls_in(st):
            name = callee(c)
            if name in ("check_preconditions", "code_commit", "check_commit_preconditions", "refuse_if_st10_record",
                        "generate_test", "write_st10_record", "commit_paths", "run_test_part"):
                nested = not isinstance(st, (ast.Expr, ast.Assign, ast.Try))
                order.setdefault(name, []).append((c.lineno, nested))
    print("  calls: %s" % order)
    g = order.get("generate_test", [(None, None)])[0][0]
    a_ok = (g is not None and len(order["generate_test"]) == 1
            and order.get("check_commit_preconditions", [(10 ** 9,)])[0][0] < g
            and order.get("refuse_if_st10_record", [(10 ** 9,)])[0][0] < g
            and order.get("code_commit", [(10 ** 9,)])[0][0] < g
            and order.get("check_preconditions", [(10 ** 9,)])[0][0] < g
            and not any(n for k in ("check_commit_preconditions", "refuse_if_st10_record", "generate_test")
                        for _, n in order.get(k, [])))
    cpre = [ast.unparse(c) for c in calls_in(mainf) if callee(c) == "check_commit_preconditions"]
    print("  check_commit_preconditions call: %s" % cpre)
    others = [(m, f) for m, fs in F.items() for f, fn in fs.items() if f != "main" and
              any(callee(c) == "generate_test" for c in calls_in(fn))]
    print("  generate_test called by other package functions: %s" % others)
    print("  a: check_preconditions, code_commit, check_commit_preconditions and refuse_if_st10_record come before "
          "generate_test, as unconditional top-level statements of main; generate_test called once: %s" % a_ok)
    ok &= a_ok and others == []

    print("\n== b. what the ST10 record, the marker and the result hold")

    def dict_literal(fn, first_key):
        for n in ast.walk(fn):
            if isinstance(n, ast.Dict) and n.keys and isinstance(n.keys[0], ast.Constant) and n.keys[0].value == first_key:
                return n
        return None

    b_ok = True
    rec = dict_literal(tg["st10_record"], "kind")
    print("  testgate.st10_record returns:")
    for k, v in zip(rec.keys, rec.values):
        print("    %-20s <- %s" % (k.value, ast.unparse(v)))
    st10_body = "\n".join(ast.unparse(s) for s in body_of(tg["st10_record"]))
    counts_ok = "counts = {c: report['checks'][c]['value'] for c in LK.TEST_CHECKS}" in st10_body
    files_ok = any(ast.unparse(v) == "{n: FZ.sha256_hex(test_files[n]) for n in D.TEST_FILES}" for v in rec.values)
    inner = {id(n.value) for n in ast.walk(tg["st10_record"]) if isinstance(n, ast.Subscript)}
    uses = sorted({ast.unparse(n) for n in ast.walk(tg["st10_record"]) if isinstance(n, ast.Subscript)
                   and ast.unparse(n).startswith("report[") and id(n) not in inner})
    bare = [n.lineno for n in ast.walk(tg["st10_record"]) if isinstance(n, ast.Name) and n.id == "report"]
    print("  reads of `report` in st10_record (outermost subscript chains): %s (%d occurrences of the name)" % (uses, len(bare)))
    print("  counts are report['checks'][c]['value'] and nothing else of the report is read (report['checks'] only for "
          "its keys): %s; test_files_sha256 is FZ.sha256_hex of the file bytes: %s" % (
              counts_ok and uses == ["report['checks']", "report['checks'][c]['value']"], files_ok))
    b_ok &= counts_ok and files_ok and uses == ["report['checks']", "report['checks'][c]['value']"]
    mk = dict_literal(tg["begin_test_evaluation"], "kind")
    print("  testgate.begin_test_evaluation marker:")
    for k, v in zip(mk.keys, mk.values):
        print("    %-22s <- %s" % (k.value, ast.unparse(v)))
    beg = tg["begin_test_evaluation"]
    rows_src = [ast.unparse(s) for s in body_of(beg) if "data" in {n.id for n in ast.walk(s) if isinstance(n, ast.Name)}]
    print("  statements of begin_test_evaluation that read `data`: %s" % rows_src)
    b_ok &= rows_src == ["rows_hashes = rows_hashes_of(data)"]
    print("  rows_hashes_of: %s" % " | ".join(ast.unparse(s) for s in body_of(tg["rows_hashes_of"])))
    print("  rows_sha256: %s" % " | ".join(ast.unparse(s) for s in body_of(tg["rows_sha256"])))
    b_ok &= ast.unparse(body_of(tg["rows_sha256"])[-1]) == "return FZ.sha256_hex(FZ.jsonl_bytes(rows))"
    fin = tg["finish_test_evaluation"]
    wr = [ast.unparse(c) for c in calls_in(fin) if callee(c) in ("write_text", "write_bytes")]
    print("  finish_test_evaluation writes: %s" % wr)
    print("  -> the result file is the caller's `result` with session_id and marker_commit; its content is the caller's "
          "(run_pilot.py, C2): no TEST row is added by testgate; whether the caller's result holds TEST text is for C2")
    b_ok &= len(wr) == 1 and "dict(result, session_id=session.session_id, marker_commit=session.marker_commit)" in wr[0]
    tg_data_readers = sorted(f for f, fn in tg.items() if "data" in [a.arg for a in fn.args.args])
    print("  testgate functions with a parameter `data`: %s; each passes it only to rows_hashes_of: %s" % (
        tg_data_readers, all(all(ast.unparse(p) == "rows_hashes_of(data)" for p in calls_in(tg[f])
                                 if any(isinstance(a, ast.Name) and a.id == "data" for a in p.args))
                             for f in tg_data_readers)))
    b_ok &= all(all(ast.unparse(p) == "rows_hashes_of(data)" for p in calls_in(tg[f])
                    if any(isinstance(a, ast.Name) and a.id == "data" for a in p.args)) for f in tg_data_readers)
    print("  b: %s" % b_ok)
    ok &= b_ok

    print("\n== c. TEST paths and the checkout")
    graph = {f: sorted({callee(c) for c in calls_in(fn) if callee(c) in tg}) for f, fn in tg.items()}

    def closure(f):
        seen, todo = set(), [f]
        while todo:
            x = todo.pop()
            for y in graph.get(x, []):
                if y not in seen:
                    seen.add(y)
                    todo.append(y)
        return seen

    for f in ("check_checkout", "_where", "check_commit_preconditions", "_check_session_checkout", "commit_paths", "_push"):
        fn = tg[f]
        print("  %s (lines %d-%d):" % (f, fn.lineno, fn.end_lineno))
        for s in body_of(fn):
            print("     | " + ast.unparse(s).replace("\n", "\n     | ")[:400])
    cc = "\n".join(ast.unparse(s) for s in body_of(tg["check_checkout"]))
    need = ["got = repo_id(remote_url(root, PILOT_REMOTE))", "if got != CANONICAL_REPO:",
            "local = _git(root, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()", "if local != PILOT_BRANCH:",
            "if _git(root, 'rev-parse', '--is-shallow-repository').stdout.strip() == 'true':",
            "f = _git(root, 'fetch', '-q', '--no-tags', PILOT_REMOTE, 'refs/heads/%s' % PILOT_BRANCH)",
            "if f.returncode != 0:", "tip = _git(root, 'rev-parse', '--verify', '-q', 'FETCH_HEAD^{commit}').stdout.strip()",
            "head = _git(root, 'rev-parse', '--verify', '-q', 'HEAD^{commit}').stdout.strip()",
            "if not HEX40.fullmatch(tip) or head != tip:", "return tip"]
    miss = [x for x in need if x not in cc]
    raises = [ast.unparse(n.exc)[:12] for n in ast.walk(tg["check_checkout"]) if isinstance(n, ast.Raise)]
    print("  check_checkout: origin's repository == CANONICAL_REPO, branch == PILOT_BRANCH, not shallow, fetch "
          "refs/heads/PILOT_BRANCH (no tags) works, HEAD == FETCH_HEAD; every failure _blocked: missing pieces %s; "
          "raises %s" % (miss, raises))
    c_ok = not miss and len(raises) == 5 and all(r.startswith("_blocked") for r in raises)
    wh = "\n".join(ast.unparse(s) for s in body_of(tg["_where"]))
    print("  _where looks at: the working tree (Path(root) / rel).exists() and `git cat-file -e <tip>:<rel>` only: %s" % (
        wh.count("_git(") == 1 and "'cat-file', '-e', '%s:%s' % (tip, rel)" in wh and ".exists()" in wh))
    c_ok &= wh.count("_git(") == 1 and "'cat-file', '-e', '%s:%s' % (tip, rel)" in wh
    sc = "\n".join(ast.unparse(s) for s in body_of(tg["_check_session_checkout"]))
    print("  _check_session_checkout: branch == PILOT_BRANCH and HEAD == session.marker_commit, else _blocked; no fetch: %s"
          % ("if local != PILOT_BRANCH or head != session.marker_commit:" in sc and "fetch" not in sc))
    c_ok &= "if local != PILOT_BRANCH or head != session.marker_commit:" in sc and "fetch" not in sc
    ccp = body_of(tg["check_commit_preconditions"])
    ccp_txt = [ast.unparse(s) for s in ccp]
    print("  check_commit_preconditions: first statement after root is check_checkout(root): %s; then staged, identity "
          "(git var GIT_COMMITTER_IDENT), dry run (push --dry-run --no-follow-tags origin HEAD:refs/heads/<branch>): %s" % (
              ccp_txt[1] == "check_checkout(root)",
              ["diff', '--cached', '--quiet'" in "\n".join(ccp_txt), "'var', 'GIT_COMMITTER_IDENT'" in "\n".join(ccp_txt),
               "'push', '--dry-run', '--no-follow-tags', PILOT_REMOTE, 'HEAD:refs/heads/%s' % PILOT_BRANCH" in "\n".join(ccp_txt)]))
    c_ok &= ccp_txt[1] == "check_checkout(root)" and "'push', '--dry-run', '--no-follow-tags', PILOT_REMOTE" in "\n".join(ccp_txt)
    cpt = "\n".join(ast.unparse(s) for s in body_of(tg["commit_paths"]))
    print("  commit_paths: no remote / branch check of its own (no check_checkout, remote_url, rev-parse --abbrev-ref): %s" % (
        "check_checkout" not in cpt and "remote_url" not in cpt and "abbrev-ref" not in cpt))
    pu = "\n".join(ast.unparse(s) for s in body_of(tg["_push"]))
    print("  _push: plain push --no-follow-tags (no --force, no +refspec) and ls-remote of the one ref: %s" % (
        "'push', '--no-follow-tags', PILOT_REMOTE, 'HEAD:refs/heads/%s' % PILOT_BRANCH" in pu and "force" not in pu
        and "'+" not in pu and "'ls-remote', PILOT_REMOTE, 'refs/heads/%s' % PILOT_BRANCH" in pu))
    c_ok &= "force" not in pu and "'+" not in pu
    print("  call graph (testgate functions reached, transitively):")
    want = {"refuse_if_marker": "check_checkout", "refuse_if_st10_record": "check_checkout",
            "check_commit_preconditions": "check_checkout", "begin_test_evaluation": "check_checkout",
            "require_test_session": "_check_session_checkout", "finish_test_evaluation": "_check_session_checkout"}
    for f in ("refuse_if_marker", "refuse_if_st10_record", "check_commit_preconditions", "begin_test_evaluation",
              "require_test_session", "claim_checkpoint", "finish_test_evaluation", "st10_check", "commit_paths"):
        cl = closure(f)
        print("    %-28s -> %s" % (f, sorted(cl)))
        if f in want:
            c_ok &= want[f] in cl
    print("  require_test_session reaches check_checkout / fetch: %s (Executor's reading: the calls do not fetch)" % (
        "check_checkout" in closure("require_test_session")))
    print("  finish_test_evaluation reaches check_checkout (through check_commit_preconditions): %s" % (
        "check_checkout" in closure("finish_test_evaluation")))
    c_ok &= "check_checkout" in closure("finish_test_evaluation")
    # order inside the functions that write
    b = tg["begin_test_evaluation"]
    lines_b = {n: first_call_line(b, n) for n in ("refuse_if_marker", "verify_authorization", "st10_check",
                                                  "check_commit_preconditions", "write_bytes", "commit_paths", "_blob",
                                                  "TestSession")}
    print("  begin_test_evaluation call lines: %s" % lines_b)
    c_ok &= lines_b["refuse_if_marker"] < lines_b["verify_authorization"] < lines_b["st10_check"] < \
        lines_b["check_commit_preconditions"] < lines_b["write_bytes"] < lines_b["commit_paths"] < lines_b["_blob"] < \
        lines_b["TestSession"]
    f = tg["finish_test_evaluation"]
    lines_f = {n: first_call_line(f, n) for n in ("_check_session_checkout", "_committed", "check_commit_preconditions",
                                                  "write_text", "commit_paths")}
    print("  finish_test_evaluation call lines: %s" % lines_f)
    c_ok &= lines_f["_check_session_checkout"] < lines_f["check_commit_preconditions"] < lines_f["write_text"] < \
        lines_f["commit_paths"]
    r = tg["require_test_session"]
    lines_r = {n: first_call_line(r, n) for n in ("_check_session_checkout", "_committed", "st10_check", "state_sha256")}
    print("  require_test_session call lines: %s" % lines_r)
    c_ok &= lines_r["_check_session_checkout"] < lines_r["_committed"] < lines_r["st10_check"] < lines_r["state_sha256"]
    em = ev["evaluate_model"]
    lines_e = {n: first_call_line(em, n) for n in ("verify_authorization", "require_test_session", "require_gpu",
                                                   "claim_checkpoint", "score_qa")}
    print("  evaluate.evaluate_model call lines (TEST branch, then the scoring): %s" % lines_e)
    c_ok &= lines_e["verify_authorization"] < lines_e["require_test_session"] < lines_e["require_gpu"] < \
        lines_e["claim_checkpoint"] < lines_e["score_qa"]
    other_callers = sorted((m, fn_name) for m, fs in F.items() for fn_name, fn in fs.items()
                           if any(callee(c) in ("begin_test_evaluation", "require_test_session", "finish_test_evaluation",
                                                "claim_checkpoint") for c in calls_in(fn)))
    print("  package functions calling begin / require_test_session / claim_checkpoint / finish: %s" % other_callers)
    gen_callers = sorted((m, fn_name, callee(c)) for m, fs in F.items() for fn_name, fn in fs.items() for c in calls_in(fn)
                         if callee(c) in ("run_test_part", "write_st10_record", "build_test_qa", "generate_test"))
    print("  package callers of the TEST generation steps (generate_test, build_test_qa, run_test_part, "
          "write_st10_record): %s" % gen_callers)
    c_ok &= {(m, f) for m, f, _ in gen_callers} <= {("test_data", "main"), ("test_data", "generate_test"),
                                                     ("testgate", "write_st10_record")}
    fin_guard = ast.unparse(body_of(tg["finish_test_evaluation"])[1].test)
    clm_guard = ast.unparse(body_of(tg["claim_checkpoint"])[0].test)
    req_guard = ast.unparse(body_of(tg["require_test_session"])[2].test)
    print("  session guards: require_test_session `%s` | claim_checkpoint `%s` | finish_test_evaluation `%s`" % (
        req_guard, clm_guard, fin_guard))
    want_guard = "not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session"
    print("  all three guards are `%s` (round-1 MINOR-1 fixed: None and objects of another type are refused before "
          "session.session_id is read): %s" % (want_guard, req_guard == clm_guard == fin_guard == want_guard))
    c_ok &= req_guard == clm_guard == fin_guard == want_guard
    print("  c: %s" % c_ok)
    ok &= c_ok

    print("\n== d. the probe against the interfaces")
    pt = ast.parse(probe_src)
    mods = {"TG": "testgate", "E": "evaluate", "LK": "leakage", "FZ": "frozen", "R": "record", "M": "mode"}
    top_names = {m: {n.id for st in trees[m].body for n in ast.walk(st) if isinstance(n, ast.Name)
                     and isinstance(n.ctx, ast.Store)} | {n.name for n in trees[m].body
                                                          if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
                 for m in set(mods.values())}
    d_ok = True
    for c in calls_in(pt):
        if isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) and c.func.value.id in mods:
            m = mods[c.func.value.id]
            fn = F[m].get(c.func.attr)
            if fn is None:
                cls = next((n for n in trees[m].body if isinstance(n, ast.ClassDef) and n.name == c.func.attr), None)
                if cls is None:
                    print("    %d %s: no function %s.%s" % (c.lineno, ast.unparse(c)[:80], m, c.func.attr))
                    d_ok = False
                    continue
                fn = next((x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == "__init__"), None)
                params = [a.arg for a in fn.args.args][1:]
            else:
                params = [a.arg for a in fn.args.args]
            npos, kws = len(c.args), [k.arg for k in c.keywords]
            required = params[:len(params) - len(fn.args.defaults)]
            good = (npos <= len(params) and all(k in params[npos:] for k in kws)
                    and all(p in params[:npos] or p in kws for p in required))
            print("    line %3d %-60s params %s: %s" % (c.lineno, ast.unparse(c)[:60], params, "ok" if good else "MISMATCH"))
            d_ok &= bool(good)
    attrs = sorted({(n.value.id, n.attr) for n in ast.walk(pt) if isinstance(n, ast.Attribute)
                    and isinstance(n.value, ast.Name) and n.value.id in mods})
    missing = [(a, b) for a, b in attrs if b not in top_names[mods[a]] and b not in F[mods[a]]]
    print("  module attributes the probe reads or assigns: %s | missing in the package: %s" % (
        ["%s.%s" % x for x in attrs], missing))
    d_ok &= not missing
    ts = next(n for n in trees["testgate"].body if isinstance(n, ast.ClassDef) and n.name == "TestSession")
    fields = [s.target.id for s in ts.body if isinstance(s, ast.AnnAssign)]
    sess_reads = sorted({n.attr for n in ast.walk(pt) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                         and n.value.id == "session"})
    print("  TestSession fields %s | the probe reads session.%s" % (fields, sess_reads))
    d_ok &= set(sess_reads) <= set(fields)
    pmain = next(n for n in pt.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    guard = next(s.lineno for s in ast.walk(pmain) if isinstance(s, ast.If) and "CANONICAL_REPO" in ast.unparse(s.test))
    override = next(s.lineno for s in ast.walk(pmain) if isinstance(s, ast.Assign) and "TG.CANONICAL_REPO" in ast.unparse(s))
    loop = next(s.lineno for s in ast.walk(pmain) if isinstance(s, ast.For))
    print("  probe guard line %d < override of CANONICAL_REPO / PILOT_BRANCH line %d < first operation (loop) line %d: %s" % (
        guard, override, loop, guard < override < loop))
    d_ok &= guard < override < loop
    kinds = sorted({ast.unparse(c.comparators[0]).strip("'") for c in ast.walk(pmain) if isinstance(c, ast.Compare)
                    and ast.unparse(c.left) == "kind"})
    print("  operations the probe implements: %s" % kinds)
    d_ok &= kinds == sorted(["begin", "eval", "finish", "gate", "marker", "pre", "st10", "st10rec", "tinysha"])
    print("  d: %s" % d_ok)
    ok &= d_ok

    print("\n== e. the searches the ruling removed: occurrences in src/metrix_e1/*.py and in the probe")
    pats = [r"remote_heads", r"--all\b", r"--reflog", r"--full-history", r"rev-list", r"--heads", r"_ever_committed",
            r"[\"']log[\"']", r"refs/tags", r"for-each-ref", r"show-ref", r"ls-remote"]
    e_hits = {}
    for name, text in list(src.items()) + [("c1b_gate_probe", probe_src)]:
        for i, ln in enumerate(text.split("\n"), 1):
            for p in pats:
                if re.search(p, ln):
                    e_hits.setdefault(p, []).append("%s:%d: %s" % (name, i, ln.strip()[:110]))
    for p in pats:
        print("  %-16s %s" % (p, e_hits.get(p, [])))
    lsr = e_hits.get(r"ls-remote", [])
    e_ok = all(p == r"ls-remote" for p in e_hits) and len(lsr) == 1 and lsr[0].startswith("testgate:") and \
        "refs/heads/%s" in lsr[0] and "_git(root" in lsr[0]
    print("  e: no removed search left; the one ls-remote is _push's pushed-ref check: %s" % e_ok)
    ok &= e_ok

    print("\n== f. B25 and pending()")
    it = trees["interpretations"]
    consts = {s.targets[0].id: ast.literal_eval(s.value) for s in it.body
              if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)
              and isinstance(s.value, ast.Constant)}
    ent = next(s.value for s in it.body if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "ENTRIES")
    entries = []
    for d in ent.elts:
        e = {}
        for k, v in zip(d.keys, d.values):
            e[k.value] = consts[v.id] if isinstance(v, ast.Name) else ast.literal_eval(v)
        entries.append(e)
    statuses = {e["id"]: e.get("status", consts["PENDING"]) for e in entries}
    my_pending = [i for i, s in statuses.items() if s == consts["PENDING"]]
    b25 = next(e for e in entries if e["id"] == "B25")
    print("  entries %d (%s..%s); statuses: %s" % (len(entries), entries[0]["id"], entries[-1]["id"],
                                                   sorted(set(statuses.values()))))
    print("  B25 status %r ruling %r" % (b25.get("status"), b25.get("ruling")))
    print("  B25 text: %s" % b25["text"])
    pend = funcs(it)["pending"]
    print("  pending(): %s -> my reading of its result: %s" % (ast.unparse(body_of(pend)[-1]), my_pending))
    pp_callers = sorted((m, f) for m, fs in F.items() for f, fn in fs.items()
                        if any(callee(c) == "pending_problem" for c in calls_in(fn)))
    print("  pending_problem callers: %s" % pp_callers)
    f_ok = (b25.get("status") == "ACCEPTED（Review Gate 2026-11-25）" and my_pending == []
            and "IMPL_C1_RULING.md" in str(b25.get("ruling")) and ("leakage", "verify_authorization") in pp_callers
            and ("test_data", "check_interpretations_ruled") in pp_callers
            and all(s in ("ACCEPTED（Review Gate 2026-11-24）", "ACCEPTED（Review Gate 2026-11-25）") for s in statuses.values()))
    print("  f: %s" % f_ok)
    ok &= f_ok

    print("\n== g. refusal kinds per testgate function (raise sites)")
    for fname in ("check_checkout", "check_commit_preconditions", "_push", "commit_paths", "refuse_if_st10_record",
                  "refuse_if_marker", "st10_check", "_committed", "begin_test_evaluation", "_check_session_checkout",
                  "require_test_session", "claim_checkpoint", "finish_test_evaluation", "code_commit"):
        rs = ["%s" % ast.unparse(n.exc).split("(")[0] for n in ast.walk(tg[fname]) if isinstance(n, ast.Raise) and n.exc]
        print("  %-28s %s" % (fname, rs))

    print("\n== h. the threat-model paragraph")
    rt = open(os.path.join(repo, RULING), encoding="utf-8").read()
    print("  %s holds the paragraph of the instruction verbatim: %s" % (RULING, THREAT in rt))
    ok &= THREAT in rt

    print("\n== i. the fix commit against the Executor's description")
    i_ok = True

    def idx(stmts, pred):
        return next((k for k, s in enumerate(stmts) if pred(s)), None)

    def assigned(fn, name):
        return [n.lineno for n in ast.walk(fn) if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign))
                and any(isinstance(t, ast.Name) and t.id == name
                        for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]

    print(" (1) begin_test_evaluation, from the marker write to the end:")
    bb = body_of(tg["begin_test_evaluation"])
    k_write = idx(bb, lambda s: "path.write_bytes(blob)" == ast.unparse(s))
    k_commit = idx(bb, lambda s: isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "head"
                   and isinstance(s.value, ast.Call) and callee(s.value) == "commit_paths")
    k_check = idx(bb, lambda s: isinstance(s, ast.If) and "_blob(" in ast.unparse(s.test))
    k_sess = idx(bb, lambda s: isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "session")
    k_live = idx(bb, lambda s: isinstance(s, ast.Assign) and ast.unparse(s.targets[0]).startswith("_LIVE["))
    k_ret = idx(bb, lambda s: isinstance(s, ast.Return))
    for s in bb[k_write:]:
        print("     %4d | %s" % (s.lineno, ast.unparse(s).replace("\n", "\n          | ")[:420]))
    order = None not in (k_write, k_commit, k_check, k_sess, k_live, k_ret) and \
        k_write < k_commit < k_check < k_sess < k_live < k_ret == len(bb) - 1
    print("   order write_bytes < head = commit_paths(...) < the _blob check < session = TestSession(...) < "
          "_LIVE[...] = session < return session (the last statement): %s (statement indices %s)" % (
              order, [k_write, k_commit, k_check, k_sess, k_live, k_ret]))
    i_ok &= order
    chk = bb[k_check]
    want_test = ("_blob(root, '%s:%s' % (head, MARKER_REL)) != blob or "
                 "_blob(root, '%s^:%s' % (head, MARKER_REL)) is not None")
    test_ok = ast.unparse(chk.test) == want_test
    raise_ok = (len(chk.body) == 1 and isinstance(chk.body[0], ast.Raise) and not chk.orelse
                and ast.unparse(chk.body[0].exc).startswith("_blocked(")
                and "another TEST evaluation began at the same time" in ast.unparse(chk.body[0].exc)
                and "counts as evaluated" in ast.unparse(chk.body[0].exc))
    print("   the check is exactly `if %s:` -> %s; its only statement raises _blocked(... another TEST evaluation began "
          "at the same time ... counts as evaluated ...): %s" % (want_test, test_ok, raise_ok))
    i_ok &= test_ok and raise_ok
    ret_n = [n.lineno for n in ast.walk(tg["begin_test_evaluation"]) if isinstance(n, ast.Return)]
    blob_asg, head_asg = assigned(tg["begin_test_evaluation"], "blob"), assigned(tg["begin_test_evaluation"], "head")
    blob_src = [ast.unparse(s) for s in bb if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "blob"]
    print("   begin has one return (%s); `blob` assigned at %s: %s; `head` assigned at %s" % (
        ret_n, blob_asg, blob_src, head_asg))
    i_ok &= len(ret_n) == 1 and len(blob_asg) == 1 and blob_asg[0] < bb[k_write].lineno and len(head_asg) == 1 \
        and blob_src == ["blob = (json.dumps(marker, ensure_ascii=False, indent=1, sort_keys=True) + '\\n').encode('utf-8')"]
    bl = tg["_blob"]
    bl_txt = [ast.unparse(s) for s in body_of(bl)]
    run_calls = [c for c in calls_in(bl) if ast.unparse(c.func) == "subprocess.run"]
    kws = {k.arg: ast.unparse(k.value) for k in run_calls[0].keywords} if run_calls else {}
    blob_fn_ok = (bl_txt == ["r = subprocess.run(['git', '-C', str(root), 'cat-file', 'blob', spec], capture_output=True, "
                             "check=False)", "return r.stdout if r.returncode == 0 else None"]
                  and "text" not in kws and "encoding" not in kws and "universal_newlines" not in kws)
    print("   _blob: %s | bytes (no text / encoding / universal_newlines keyword), None on a non-zero exit: %s" % (
        bl_txt, blob_fn_ok))
    i_ok &= blob_fn_ok
    pu = [ast.unparse(s) for s in body_of(tg["_push"])]
    cp_ret = [ast.unparse(s) for s in body_of(tg["commit_paths"]) if isinstance(s, ast.Return)]
    push_ok = ("head = _git(root, 'rev-parse', 'HEAD').stdout.strip()" in pu and pu.index(
        "head = _git(root, 'rev-parse', 'HEAD').stdout.strip()") == 1
               and any("ls.stdout.split()[:1] == [head]" in x and "return head" in x for x in pu)
               and cp_ret == ["return _push(root, retries, sleep, what)"])
    print("   commit_paths returns _push(...); _push reads head = HEAD before its first push, pushes HEAD and returns "
          "head only when ls-remote shows it: %s -> the commit checked is the one pushed and verified" % push_ok)
    i_ok &= push_ok

    print(" (2) session guards")
    want_guard = "not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session"
    for fname, msg in (("claim_checkpoint", "no TEST session of this process (begin_test_evaluation)"),
                       ("finish_test_evaluation", "no TEST session of this process"),
                       ("require_test_session", "no TEST session of this process (begin_test_evaluation)")):
        fb = body_of(tg[fname])
        kg = idx(fb, lambda s: isinstance(s, ast.If) and "_LIVE" in ast.unparse(s.test))
        before = [ast.unparse(s) for s in fb[:kg]]
        uses_before = [x for x in before if re.search(r"\bsession\b", x)]
        g = fb[kg]
        ok_g = (ast.unparse(g.test) == want_guard and len(g.body) == 1 and isinstance(g.body[0], ast.Raise)
                and ast.unparse(g.body[0].exc) == "_refuse(%r)" % msg and not uses_before)
        print("   %-24s statements before the guard %s | guard `%s` -> %s: %s" % (
            fname, before, ast.unparse(g.test), ast.unparse(g.body[0].exc), ok_g))
        i_ok &= ok_g
    print("   for session None or another type, isinstance is False and `not ...` short-circuits: refused before "
          "session.session_id is read; a copy of a session fails the identity test against _LIVE")

    print(" (3) evaluate_model: with_s_mapping")
    em = ev["evaluate_model"]
    eb = body_of(em)
    k_sm = idx(eb, lambda s: isinstance(s, ast.If) and ast.unparse(s.test) == "with_s_mapping and split != 'dev'")
    k_tb = idx(eb, lambda s: isinstance(s, ast.If) and ast.unparse(s.test) == "split == 'test'")
    print("   statements before the s_mapping check: %s" % [ast.unparse(s)[:120] for s in eb[:k_sm]] if k_sm is not None
          else "   no s_mapping check found")
    sm_ok = k_sm is not None and k_tb is not None and k_sm < k_tb
    if sm_ok:
        sm = eb[k_sm]
        sm_ok &= (len(sm.body) == 1 and isinstance(sm.body[0], ast.Raise)
                  and ast.unparse(sm.body[0].exc) == "ValueError(\"S's own-mapping accuracy is reported on DEV only "
                                                     "(protocol section 8)\")")
        firsts = {n: first_call_line(em, n) for n in ("verify_authorization", "require_test_session", "require_gpu",
                                                      "claim_checkpoint", "score_s_mapping")}
        print("   check at line %d: `if %s: raise %s` | TEST branch `if split == 'test':` at line %d | first calls %s" % (
            sm.lineno, ast.unparse(sm.test), ast.unparse(sm.body[0].exc), eb[k_tb].lineno, firsts))
        sm_ok &= all(v is not None and v > sm.lineno for v in firsts.values())
        before_ok = [ast.unparse(s).split("\n")[0] for s in eb[:k_sm]] == ["if split not in SPLIT_FILES:"]
        sm_ok &= before_ok
    own = [n.lineno for n in ast.walk(em) if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and "own-mapping accuracy" in n.value]
    s_use = [ast.unparse(s).split("\n")[0] for s in ast.walk(em) if isinstance(s, ast.If) and "with_s_mapping" in ast.unparse(s.test)]
    print("   the refusal text occurs %d time(s) in evaluate_model (lines %s); ifs on with_s_mapping: %s" % (
        len(own), own, s_use))
    sm_ok &= len(own) == 1
    print("   (3): %s" % sm_ok)
    i_ok &= sm_ok

    print(" (4) sleep")
    sl_ok = True
    for fname in ("commit_paths", "begin_test_evaluation", "finish_test_evaluation", "_push"):
        a = tg[fname].args
        names = [x.arg for x in a.args]
        defaults = dict(zip(names[len(names) - len(a.defaults):], [ast.unparse(d) for d in a.defaults]))
        print("   %-24s sleep default %r" % (fname, defaults.get("sleep", "(no default)")))
        if fname != "_push":
            sl_ok &= defaults.get("sleep") == "None"
    first_push = ast.unparse(body_of(tg["_push"])[0])
    ts = [(f, c.lineno) for f, fn in tg.items() for c in ast.walk(fn) if isinstance(c, ast.Attribute)
          and ast.unparse(c) == "time.sleep"]
    print("   _push first statement `%s` | functions reading time.sleep: %s" % (first_push, ts))
    sl_ok &= first_push == "sleep = time.sleep if sleep is None else sleep" and [f for f, _ in ts] == ["_push"]
    print("   (4): %s" % sl_ok)
    i_ok &= sl_ok

    print(" (5) the BLOCKED text of check_checkout (HEAD is not the latest commit)")
    msg = [ast.unparse(n.exc) for n in ast.walk(tg["check_checkout"]) if isinstance(n, ast.Raise)
           and "is not the latest commit" in ast.unparse(n.exc)]
    t5 = len(msg) == 1 and "fast-forward" in msg[0] and "pull" in msg[0] and "push the local commits" not in msg[0] \
        and "only on the Owner" in msg[0]
    print("   %s\n   names a fast-forward pull, local TEST-path commits pushed only on the Owner's decision, no 'push the "
          "local commits': %s" % (msg, t5))
    i_ok &= t5

    print(" (6) generate_test")
    gdoc = ast.get_docstring(td["generate_test"]) or ""
    callers = sorted((m, f) for m, fs in F.items() for f, fn in fs.items() if any(callee(c) == "generate_test"
                                                                                  for c in calls_in(fn)))
    rp = os.path.exists(os.path.join(repo, "metrix/e1-pilot/run_pilot.py"))
    print("   docstring: %r\n   package callers %s | run_pilot.py exists: %s (C2; the caller to check then)" % (
        gdoc, callers, rp))
    i_ok &= "main() is the only caller" in gdoc and callers == [("test_data", "main")]

    print(" (7) tests/test_testgate.py")
    tt = open(os.path.join(repo, "metrix/e1-pilot/tests/test_testgate.py"), encoding="utf-8").read()
    ok_idx = tt.encode("utf-8") == git(repo, "cat-file", "blob", ":metrix/e1-pilot/tests/test_testgate.py").stdout
    tfn = {n.name for n in ast.parse(tt).body if isinstance(n, ast.FunctionDef)}
    want_t = ["test_a_second_begin_in_the_same_clone_is_blocked",
              "test_a_commit_of_another_begin_between_commit_and_push_is_blocked",
              "test_a_marker_file_overwritten_before_the_commit_is_blocked",
              "test_evaluation_calls_do_not_fetch_finish_does", "test_s_mapping_on_test_is_refused_before_the_gate",
              "test_a_marker_deleted_in_a_later_commit_is_not_searched"]
    print("   working tree == index: %s | present: %s | old name test_history_other_refs_and_the_reflog_are_not_searched "
          "present: %s" % (ok_idx, {t: t in tfn for t in want_t},
                           "test_history_other_refs_and_the_reflog_are_not_searched" in tfn))
    i_ok &= ok_idx and all(t in tfn for t in want_t) and "test_history_other_refs_and_the_reflog_are_not_searched" not in tfn
    none_lines = [ln.strip() for ln in tt.split("\n") if "no TEST session of this process" in ln
                  and ("None" in ln or "copy.copy" in ln)]
    print("   refusal asserts with None or copy.copy: %s" % none_lines)
    i_ok &= any("claim_checkpoint, None" in x for x in none_lines) and \
        any("finish_test_evaluation, env.fz, None" in x for x in none_lines) and \
        any("finish_test_evaluation, env.fz, copy.copy(s)" in x for x in none_lines)

    print(" (8) the Executor's records of this round")
    c3 = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1b_03_checks_fix.txt"), encoding="utf-8").read()
    c4 = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1b_04_checks_fix.txt"), encoding="utf-8").read()
    m3, m4 = re.findall(r"^mutations \d+, caught \d+$", c3, re.M), re.findall(r"^mutations \d+, caught \d+$", c4, re.M)
    nc3 = re.findall(r"^(.*?)\s+-> NOT CAUGHT.*$", c3, re.M)
    nc4 = re.findall(r"^(.*?)\s+-> NOT CAUGHT.*$", c4, re.M)
    py4 = re.findall(r"^\d+ passed.*$", c4, re.M)
    fail4 = re.findall(r"^.*\b\d+ failed\b.*$", c4.split("c1b_mutate_fix1.py")[0], re.M)
    eq4 = re.findall(r"src\+tests sha256 before (\w+) after (\w+) (\w+)", c4)
    print("   c1b_03: %s, not caught %s | c1b_04: %s, not caught %s | pytest %s (failed lines before the mutation run: "
          "%s) | src+tests before/after the mutations %s" % (m3, nc3, m4, nc4, py4, fail4, eq4))
    i_ok &= m4 == ["mutations 78, caught 78"] and nc4 == [] and nc3 == ["begin: pushed marker bytes not checked"] \
        and m3 == ["mutations 78, caught 77"] and len(py4) == 1 and not fail4 and eq4 and eq4[0][0] == eq4[0][1]
    print("  i: %s" % i_ok)
    ok &= i_ok
    return bool(ok)


run(main)
