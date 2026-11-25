"""ic4_03 (implementation stage C, C1 work commit, round 3, task 3, static).  Successor of my ic3_03_static.py.  Every
file is read as text (working tree, which equals the index; checked) and parsed with the standard `ast` module;
nothing of the package is imported or run.
  a. TEST references in src/: every function of src/metrix_e1/*.py and src/metrix/**.py that names a TEST file, the
     TEST constants, eval_sets, or calls a TEST path; the set at HEAD vs now, and for every function new to the set,
     its I/O-like calls;
  b. testgate.py: every I/O-like call per function; the TEST rows (`data`) go only to rows_hashes_of -> rows_sha256
     (canonical JSONL bytes -> sha256); no function opens a file; a committed JSON that is not an object is refused
     (record.committed_json raises NotCommitted; testgate._committed turns it into a refusal; leakage.
     verify_authorization and test_data._committed catch NotCommitted from record.committed_record);
  c. test_data.main: order of the steps (preconditions -> --out outside the repository -> --out empty -> code_commit
     -> check_remote(origin, pilot branch) -> refuse_if_st10_record(root, PILOT_REMOTE) -> generate_test -> write --out
     -> run_test_part -> report to --out -> write_st10_record -> commit_paths of the ST10 record only); every check
     comes before generate_test; the exact --out test; the --remote option is gone; the module docstring;
  d. what the ST10 record and the marker hold (dict literals; st10_record reads only report["checks"][c]["value"]);
     the marker's remote field goes through remote_url (scrubbed);
  e. evaluate.evaluate_model, split "test": verify_authorization < require_test_session < require_gpu <
     claim_checkpoint < the first read of data[...] rows; claim only in the TEST branch;
  f. tests/ and reports/impl_c/*.py: every call of a TEST path with the data it gets; the stubs in force for each
     test_data.main call of test_testgate.py; tests that build an authorization call no TEST path; references to
     eval_sets in the changed tests; the rows of c1_probe_run.py are literal synthetic rows in a temporary directory;
  g. the history search of "TEST once" and "TEST generated once": _ever_committed (git log arguments), _where,
     remote_heads (check_remote first, ls-remote --heads, fetch --no-tags by name), the revs both refusals pass
     (--all and --reflog);
  h. begin_test_evaluation: order of its checks and writes; _commit_preconditions (check_remote with the branch,
     identity, fast-forward, dry run); _push (--no-follow-tags, remote-ref check); which refusals are BLOCKED
     (ProtocolStop) and which are ImplementationFail; refuse_if_marker raises TestAlreadyEvaluated when a result
     exists; finish_test_evaluation checks the committed marker's bytes against the session;
  i. B25: interpretations.ENTRIES (B25 without status -> pending), pending_problem used by verify_authorization and
     the TEST generator; every TEST path of the package calls verify_authorization;
  j. the staged probe reports/impl_c/c1_gate_probe.py against the round-3 interfaces: every call of a function of
     testgate, evaluate, leakage, frozen, record (positional count and keywords vs the parameters), every module
     attribute it reads exists, the TestSession attributes it reads; module attributes it assigns;
  k. remote, branch, shallow clone, credentials: check_remote's body; every caller and whether it passes a branch
     (hence whether the checked-out branch is checked); scrub's pattern and every place it is applied; raise sites
     whose message carries git output or a URL without scrub;
  l. the probe's guard: the refusal (this repository, or origin == CANONICAL_REPO) comes before the override of
     CANONICAL_REPO / PILOT_BRANCH and before the first operation.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ic4_03_static.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import glob
import re
from ia_common import git, run

PKG = "metrix/e1-pilot/src"
TESTS = "metrix/e1-pilot/tests"
PROBE = "metrix/e1-pilot/reports/impl_c/c1_gate_probe.py"
TEST_NAMES = {"test_qa", "general_test", "TEST_FILES", "eval_sets", "test_qa.jsonl", "general_test.jsonl"}
TEST_PATHS = {"generate_test", "run_test_part", "build_test_qa", "begin_test_evaluation", "require_test_session",
              "st10_check", "finish_test_evaluation", "write_st10_record", "st10_record", "refuse_if_marker",
              "refuse_if_st10_record", "rows_hashes_of", "rows_sha256", "claim_checkpoint"}
IO = {"open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl", "load", "loads", "write_text", "write_bytes",
      "run", "_git", "committed_json", "committed_record", "_committed", "mkdir", "exists", "is_file", "unlink",
      "from_pretrained", "build_general_dev", "file_sha256", "git_blob"}


def callee(n):
    f = n.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def functions(tree):
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(n.name, n)
    return out


def body_of(fn):
    return fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant)) else fn.body


def names_in(node):
    s = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            s.add(n.id)
        elif isinstance(n, ast.Attribute):
            s.add(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            for t in TEST_NAMES:
                if t in n.value and len(n.value) < 60:
                    s.add(t)
    return s


def test_refs(src):
    tree = ast.parse(src)
    out = {}
    for name, fn in functions(tree).items():
        hit = set()
        for st in body_of(fn):
            nm = names_in(st)
            hit |= (nm & TEST_NAMES) | (nm & TEST_PATHS)
        if hit:
            out[name] = sorted(hit)
    return out


def io_calls(fn):
    return ["%s(%s)" % (callee(c), ", ".join(ast.unparse(a) for a in c.args)[:110]) for c in ast.walk(fn)
            if isinstance(c, ast.Call) and callee(c) in IO]


def first_line(fn, pred):
    ls = [n.lineno for n in ast.walk(fn) if pred(n)]
    return min(ls) if ls else None


def call_line(fn, name, contains=None):
    return first_line(fn, lambda n: isinstance(n, ast.Call) and callee(n) == name and
                      (contains is None or contains in ast.unparse(n)))


def raises_in(fn):
    """(line, exception constructor text) of every raise in fn."""
    return [(n.lineno, ast.unparse(n.exc)[:90]) for n in ast.walk(fn) if isinstance(n, ast.Raise) and n.exc is not None]


def probe_interface(src, tg_funcs, session_fields, label):
    """Calls TG.<f>(...) in the probe vs the parameters of testgate.<f>; session.<attr> reads vs TestSession fields."""
    t = ast.parse(src)
    bad = []
    for c in ast.walk(t):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) \
                and c.func.value.id == "TG" and c.func.attr in tg_funcs:
            fd = tg_funcs[c.func.attr]
            params = [a.arg for a in fd.args.args]
            npos, kws = len(c.args), [k.arg for k in c.keywords]
            ok = npos <= len(params) and all(k in params[npos:] for k in kws)
            print("  %s: line %d %s -> parameters %s: %s" % (label, c.lineno, ast.unparse(c)[:110], params,
                                                             "ok" if ok else "MISMATCH (%d positional for %d parameters)" % (npos, len(params))))
            if not ok:
                bad.append("line %d: %s" % (c.lineno, ast.unparse(c)[:80]))
    reads = sorted({(n.lineno, n.attr) for n in ast.walk(t) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == "session" and isinstance(n.ctx, ast.Load)})
    for ln, a in reads:
        ok = a in session_fields
        print("  %s: line %d session.%s -> TestSession field: %s" % (label, ln, a, "ok" if ok else "MISSING"))
        if not ok:
            bad.append("line %d: session.%s" % (ln, a))
    return bad


def main():
    repo = sys.argv[1]
    ok = True
    st = git(repo, "status", "--porcelain", "--untracked-files=no", "--", PKG, TESTS, PROBE, check=False).stdout.decode().splitlines()
    wt_eq = git(repo, "diff", "--quiet", "--", PKG, TESTS, "metrix/e1-pilot/reports", check=False).returncode == 0
    print("src/, tests/ and the probe status (tracked): %d entries | working tree == index: %s" % (len(st), wt_eq))
    ok &= wt_eq

    print("\n== a. functions of src/ naming TEST files / constants / eval_sets / TEST paths: HEAD vs now")
    files = sorted(glob.glob(os.path.join(repo, PKG, "**", "*.py"), recursive=True))
    new_funcs = []
    for p in files:
        rel = os.path.relpath(p, repo)
        now = test_refs(open(p, encoding="utf-8").read())
        hb = git(repo, "cat-file", "blob", "HEAD:" + rel, check=False)
        old = test_refs(hb.stdout.decode("utf-8")) if hb.returncode == 0 else {}
        for f in sorted(set(now) | set(old)):
            tag = "same" if now.get(f) == old.get(f) else ("NEW" if f not in old else ("GONE" if f not in now else "CHANGED"))
            if tag != "same":
                new_funcs.append((rel, f))
            print("  %-28s %-26s %-7s %s" % (os.path.basename(rel), f, tag, now.get(f, old.get(f))))
    print("functions new or changed in this set: %s" % new_funcs)
    trees = {os.path.basename(p): ast.parse(open(p, encoding="utf-8").read()) for p in files if "/metrix_e1/" in p}
    for rel, f in new_funcs:
        t = trees.get(os.path.basename(rel))
        if t and f in functions(t):
            print("  I/O-like calls of %s.%s: %s" % (os.path.basename(rel), f, io_calls(functions(t)[f])))

    print("\n== b. testgate.py: I/O-like calls per function; use of the TEST rows")
    tg = trees["testgate.py"]
    TGF = functions(tg)
    for f, fn in TGF.items():
        calls = io_calls(fn)
        if calls:
            print("  %-24s %s" % (f, calls))
    reads = [c for fn in TGF.values() for c in io_calls(fn) if c.split("(")[0] in ("open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl")]
    print("file reads (open / read_*): %s" % reads)
    ok &= reads == []
    uses = sorted({f for f, fn in TGF.items() for n in ast.walk(fn)
                   if isinstance(n, ast.Name) and n.id == "data" and isinstance(n.ctx, ast.Load)})
    print("functions that load the name `data` (the TEST rows): %s" % uses)
    print("rows_hashes_of: %s" % [ast.unparse(s) for s in body_of(TGF["rows_hashes_of"])])
    print("rows_sha256   : %s" % [ast.unparse(s) for s in body_of(TGF["rows_sha256"])])
    data_uses = {f: sorted({ast.unparse(p) for p in ast.walk(TGF[f]) if isinstance(p, ast.Call)
                            and any(isinstance(a, ast.Name) and a.id == "data" for a in p.args)}) for f in uses}
    print("calls receiving `data`: %s" % data_uses)
    allowed = all(all(c.startswith("rows_hashes_of(data)") or c.startswith("rows_sha256(data[n])") for c in v) for v in data_uses.values())
    print("the TEST rows only go to rows_hashes_of / rows_sha256 (hash of the canonical JSONL bytes): %s" % allowed)
    ok &= allowed and [ast.unparse(s) for s in body_of(TGF["rows_sha256"])] == ["return FZ.sha256_hex(FZ.jsonl_bytes(rows))"]
    cm = TGF["_committed"]
    print("testgate._committed: %s" % [ast.unparse(s) for s in body_of(cm)])
    rec_src = open(os.path.join(repo, PKG, "metrix_e1", "record.py"), encoding="utf-8").read()
    RF = functions(ast.parse(rec_src))
    cj = RF["committed_json"]
    cj_if = [ast.unparse(n) for n in ast.walk(cj) if isinstance(n, ast.If) and "isinstance(obj, dict)" in ast.unparse(n.test)]
    print("record.committed_json non-object check: %s" % cj_if)
    cr = [ast.unparse(c) for c in ast.walk(RF["committed_record"]) if isinstance(c, ast.Call) and callee(c) == "committed_json"]
    print("record.committed_record reads through committed_json: %s" % cr)
    obj_check = (cj_if == ["if not isinstance(obj, dict):\n    raise NotCommitted('%s is a JSON %s, not an object' % (rel, type(obj).__name__))"]
                 and any("R.committed_json(root, rel)" in ast.unparse(s) for s in body_of(cm)) and cr != [])
    users = sorted({f for f, fn in TGF.items() for c in ast.walk(fn) if isinstance(c, ast.Call) and callee(c) == "_committed"})
    print("a committed JSON that is not an object is refused (committed_json -> NotCommitted -> _committed refusal): %s"
          " | _committed used by %s" % (obj_check, users))
    ok &= obj_check and {"st10_check", "require_test_session", "finish_test_evaluation"} <= set(users)
    va_src = functions(trees["leakage.py"])["verify_authorization"]
    catches = [ast.unparse(h.type) for h in ast.walk(va_src) if isinstance(h, ast.ExceptHandler)]
    td_c = functions(trees["test_data.py"])["_committed"]
    print("leakage.verify_authorization except handlers: %s | test_data._committed: %s" % (
        catches, [ast.unparse(s)[:120] for s in body_of(td_c)]))
    ok &= "R.NotCommitted" in catches

    print("\n== c. test_data.main: order of the steps and the --out test")
    td = trees["test_data.py"]
    mn = functions(td)["main"]
    order = []
    keys = ("check_preconditions", "out.resolve() == root", "present = ", "TG.code_commit(root)", "TG.check_remote(",
            "refuse_if_st10_record", "generate_test(", "out.mkdir", "run_test_part", "leakage_test_report",
            "write_st10_record", "TG.commit_paths(")
    for i, s in enumerate(mn.body):
        for key in keys:
            if key in ast.unparse(s) and key not in [k for k, _ in order]:
                order.append((key, i))
    print("statement index of each step: %s" % order)
    idx = [i for _, i in order]
    ok &= [k for k, _ in order] == list(keys) and idx == sorted(idx) and len(set(idx)) == len(idx)
    rs = [ast.unparse(s) for s in mn.body if "refuse_if_st10_record" in ast.unparse(s)]
    print("ST10-record search call: %s | code check: %s" % (rs, [ast.unparse(s) for s in mn.body if "code_commit" in ast.unparse(s)]))
    crs = [ast.unparse(s) for s in mn.body if "TG.check_remote(" in ast.unparse(s)]
    cps = [ast.unparse(c) for c in ast.walk(mn) if isinstance(c, ast.Call) and ast.unparse(c.func) == "TG.commit_paths"]
    print("check_remote call: %s | commit_paths call: %s" % (crs, cps))
    ok &= rs == ["TG.refuse_if_st10_record(root, TG.PILOT_REMOTE)"] and crs == ["TG.check_remote(root, TG.PILOT_REMOTE, TG.PILOT_BRANCH)"] \
        and len(cps) == 1 and ast.unparse(cps and ast.parse(cps[0]).body[0].value.args[1]) == "[TG.ST10_RECORD_REL]"
    tdoc = ast.get_docstring(td)
    stale = [ln.strip() for ln in tdoc.split("\n") if "follow outside this command" in ln or "Committing and pushing the record" in ln]
    print("INFO test_data module docstring lines that still say the record is committed outside this command: %s" % stale)
    tests = [ast.unparse(s) for s in mn.body if isinstance(s, ast.If) and "resolve" in ast.unparse(s.test)]
    roots = [ast.unparse(s) for s in mn.body if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "root"]
    print("--out test: %s | %s" % (roots, tests))
    ok &= roots == ["root = fz.repo_root.resolve()"] and len(tests) == 1 and \
        ast.unparse(mn.body[[ast.unparse(s) for s in mn.body].index(tests[0])].test) == "out.resolve() == root or root in out.resolve().parents"
    remote_arg = [ast.unparse(c) for c in ast.walk(mn) if isinstance(c, ast.Call) and callee(c) == "add_argument" and "--remote" in ast.unparse(c)]
    print("--remote argument: %s" % remote_arg)
    ok &= remote_arg == []
    cc = TGF["code_commit"]
    print("testgate.code_commit: %s" % [ast.unparse(c)[:120] for c in ast.walk(cc) if isinstance(c, ast.Call) and callee(c) == "_git"])

    print("\n== d. ST10 record and marker contents")
    sr = TGF["st10_record"]
    rets = [s for s in ast.walk(sr) if isinstance(s, ast.Return) and isinstance(s.value, ast.Dict)]
    rec = {ast.literal_eval(k): ast.unparse(v) for k, v in zip(rets[0].value.keys, rets[0].value.values)}
    for k, v in rec.items():
        print("  st10_record[%r] = %s" % (k, v))
    counts_src = [ast.unparse(s) for s in sr.body if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "counts"]
    print("  counts = %s" % counts_src)
    subs = sorted({ast.unparse(n.slice) for n in ast.walk(sr) if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)})
    print("  constant subscripts used in st10_record: %s ('detail' used: %s)" % (subs, "'detail'" in subs))
    ok &= sorted(rec) == ["authorization", "code_commit", "counts", "frozen_commit", "kind", "label", "mode", "test_files_sha256"] \
        and counts_src == ["counts = {c: report['checks'][c]['value'] for c in LK.TEST_CHECKS}"] and "'detail'" not in subs \
        and rec["test_files_sha256"] == "{n: FZ.sha256_hex(test_files[n]) for n in D.TEST_FILES}"
    bt = TGF["begin_test_evaluation"]
    md = [s for s in ast.walk(bt) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "marker"]
    mk = {ast.literal_eval(k): ast.unparse(v) for k, v in zip(md[0].value.keys, md[0].value.values)}
    for k, v in mk.items():
        print("  marker[%r] = %s" % (k, v))
    want = ["auditor_count_sha256", "authorization", "branch", "checkpoints", "code_commit", "frozen_commit", "kind",
            "mode", "models", "remote", "session_id", "st10_record_sha256", "started_utc", "test_files_sha256"]
    ok &= sorted(mk) == want and "data" not in " ".join(mk.values()).replace("rows_hashes", "")
    ru = [ast.unparse(s) for s in body_of(TGF["remote_url"])]
    print("  marker['remote'] = %s | remote_url body: %s" % (mk.get("remote"), ru))
    ok &= mk.get("remote") == "remote_url(root, remote)" and any(s.startswith("return scrub(") for s in ru)
    fin = TGF["finish_test_evaluation"]
    print("  finish_test_evaluation writes: %s  (the caller's `result`; content decided in C2)" % [
        c for c in io_calls(fin) if c.startswith("write")])

    print("\n== e. evaluate.evaluate_model, split 'test': gate order")
    ev = functions(trees["evaluate.py"])["evaluate_model"]
    seq = []
    for n in ast.walk(ev):
        if isinstance(n, ast.Call) and callee(n) in ("verify_authorization", "require_test_session", "require_gpu", "claim_checkpoint"):
            seq.append((n.lineno, callee(n)))
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "data":
            seq.append((n.lineno, "data[%s]" % ast.unparse(n.slice)))
    seq.sort()
    print("  %s" % seq)
    first_data = min(l for l, w in seq if w.startswith("data["))
    gates = {}
    for l, w in seq:                                    # first occurrence (require_gpu appears in both branches now)
        if not w.startswith("data["):
            gates.setdefault(w, l)
    ok &= gates["verify_authorization"] < gates["require_test_session"] < gates["require_gpu"] < gates["claim_checkpoint"] < first_data
    claim_if = [s for s in ev.body if isinstance(s, ast.If) and "claim_checkpoint" in ast.unparse(s)]
    print("  claim_checkpoint guarded by: %s | else branch: %s" % ([ast.unparse(s.test) for s in claim_if],
                                                                   [ast.unparse(x) for s in claim_if for x in s.orelse]))
    ok &= [ast.unparse(s.test) for s in claim_if] == ["split == 'test'"] and \
        [ast.unparse(x) for s in claim_if for x in s.orelse] == ["require_gpu(mode, device)"] and \
        "claim_checkpoint" in ast.unparse(claim_if[0].body[-1]) and "require_gpu" in ast.unparse(claim_if[0].body[-2])

    print("\n== f. tests/ and reports/impl_c scripts: TEST-path calls and the data they get")
    tfiles = sorted(glob.glob(os.path.join(repo, TESTS, "*.py"))) + sorted(glob.glob(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/*.py")))
    changed = set(git(repo, "diff", "--cached", "--name-only", "HEAD", check=False).stdout.decode().split())
    for p in tfiles:
        rel = os.path.relpath(p, repo)
        src = open(p, encoding="utf-8").read()
        t = ast.parse(src)
        hits = []
        for fn in functions(t).values():
            for c in ast.walk(fn):
                if isinstance(c, ast.Call) and (callee(c) in ("generate_test", "run_test_part", "main", "begin_test_evaluation",
                                                              "finish_test_evaluation", "write_st10_record")
                                                or (callee(c) == "evaluate_model" and "test" in ast.unparse(c))):
                    if callee(c) == "main" and not ast.unparse(c.func).startswith("TD."):
                        continue
                    hits.append((fn.name, c.lineno, ast.unparse(c)[:150]))
        ev_refs = len(re.findall(r"eval_sets", src))
        if rel in changed or hits:
            print("  %s (%s): %d TEST-path calls; 'eval_sets' mentioned %d times" % (rel, "changed" if rel in changed else "unchanged",
                                                                                 len(hits), ev_refs))
            for h in hits:
                print("     %s:%d %s" % h)
    tt = ast.parse(open(os.path.join(repo, TESTS, "test_testgate.py"), encoding="utf-8").read())
    for fn in functions(tt).values():
        mains = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and ast.unparse(c.func) == "TD.main"]
        if mains:
            first_main = min(c.lineno for c in mains)
            before = [ast.unparse(c.args[0]) + "." + ast.literal_eval(c.args[1]) for c in ast.walk(fn)
                      if isinstance(c, ast.Call) and ast.unparse(c.func) == "monkeypatch.setattr" and len(c.args) >= 2
                      and isinstance(c.args[1], ast.Constant) and c.lineno < first_main]
            inputs = sorted({ast.unparse(c.args[0].elts[1]) for c in mains if isinstance(c.args[0], ast.List)})
            print("  test_testgate.%s: TD.main called %d times; stubbed before the first call: %s; --inputs %s" % (
                fn.name, len(mains), before, inputs))
            ok &= {"TD.check_preconditions", "TD.generate_test", "TD.LK.run_test_part"} <= set(before) and inputs == ["'unused'"]
    for tf in ("test_test_data.py", "test_testgate.py"):
        t = ast.parse(open(os.path.join(repo, TESTS, tf), encoding="utf-8").read())
        for fn in functions(t).values():
            builds = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and ast.unparse(c.func) == "TD.check_preconditions"]
            if builds:
                paths = sorted({callee(c) for c in ast.walk(fn) if isinstance(c, ast.Call) and callee(c) in
                                ("generate_test", "run_test_part", "begin_test_evaluation", "evaluate_model", "main")
                                and not (callee(c) == "main" and not ast.unparse(c.func).startswith("TD."))})
                patched = sorted({ast.unparse(c.args[0]) + "." + ast.literal_eval(c.args[1]) for c in ast.walk(fn)
                                  if isinstance(c, ast.Call) and ast.unparse(c.func) == "monkeypatch.setattr" and len(c.args) >= 2
                                  and isinstance(c.args[1], ast.Constant)})
                print("  %s.%s calls TD.check_preconditions; stubs %s; TEST paths called in the same test: %s" % (
                    tf, fn.name, patched, paths))
                ok &= paths == [] or "TD.generate_test" in patched
    for p in tfiles:
        rel = os.path.relpath(p, repo)
        if rel in changed:
            hb = git(repo, "cat-file", "blob", "HEAD:" + rel, check=False)
            old_l = [ln for ln in (hb.stdout.decode("utf-8").split("\n") if hb.returncode == 0 else []) if "eval_sets" in ln]
            new_l = [ln for ln in open(p, encoding="utf-8").read().split("\n") if "eval_sets" in ln]
            print("  %s: lines naming eval_sets HEAD %d / now %d, identical: %s%s" % (
                rel, len(old_l), len(new_l), old_l == new_l, "" if old_l == new_l else
                " | new: %s" % [ln.strip()[:150] for ln in new_l if ln not in old_l]))
            ok &= old_l == new_l or (rel.endswith("test_testgate.py") and all(
                ln.strip().startswith("generated, read or counted") for ln in new_l if ln not in old_l))
    probe = open(os.path.join(repo, PROBE), encoding="utf-8").read()
    print("  c1_gate_probe.py: TEST rows read from %s" % re.findall(r"data = \{[^\n]*", probe))
    pr = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1_probe_run.py"), encoding="utf-8").read()
    prt = ast.parse(pr)
    rows_assign = [n for n in ast.walk(prt) if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "rows"]
    lit = rows_assign and all(isinstance(v, ast.List) and all(isinstance(e, ast.Dict) for e in v.elts)
                              for v in rows_assign[0].value.values)
    vals = sorted({ast.literal_eval(x) for v in (rows_assign[0].value.values if rows_assign else []) for e in v.elts
                   for x in e.values if isinstance(x, ast.Constant) and isinstance(x.value, str)})
    tmp = "tempfile.TemporaryDirectory()" in pr
    print("  c1_probe_run.py: rows are literal dicts: %s; their string values %s; built under tempfile.TemporaryDirectory(): %s"
          % (bool(lit), vals, tmp))
    ok &= bool(lit) and tmp and all("synthetic" in v.lower() or v in ("s-0",) for v in vals)
    real_fixtures = sorted({(fn.name, a.arg) for fn in functions(tt).values() for a in fn.args.args
                            if a.arg in ("inputs_dir", "generated")})
    autouse = [fn.name for fn in functions(tt).values() if any("autouse=True" in ast.unparse(d) for d in fn.decorator_list)]
    print("  test_testgate.py: autouse fixtures %s (interpretations.pending -> [] for every test of the file); test "
          "functions taking the real inputs / generated data fixtures: %s" % (autouse, real_fixtures))
    ok &= real_fixtures == []

    print("\n== g. history search of 'TEST once' / 'TEST generated once'")
    ec = TGF["_ever_committed"]
    gl = [ast.unparse(c) for c in ast.walk(ec) if isinstance(c, ast.Call) and callee(c) == "_git"]
    full = any("'--full-history'" in g for g in gl)
    print("  _ever_committed git call: %s | --full-history given: %s" % (gl, full))
    ok &= full and gl == ["_git(root, 'log', '--full-history', *revs, '--format=%H', '--', rel)"]
    wh = TGF["_where"]
    print("  _where: %s" % [ast.unparse(s) for s in body_of(wh)])
    rh = TGF["remote_heads"]
    rgit = [ast.unparse(c) for c in ast.walk(rh) if isinstance(c, ast.Call) and callee(c) == "_git"]
    print("  remote_heads git calls: %s" % rgit)
    ok &= rgit == ["_git(root, 'ls-remote', '--heads', remote)", "_git(root, 'fetch', '-q', '--no-tags', remote, *[ref for _, ref in heads])"]
    print("  remote_heads raises: %s" % raises_in(rh))
    first = [ast.unparse(s) for s in body_of(rh)][:2]
    print("  remote_heads first statements: %s" % first)
    ok &= first == ["if remote is None:\n    return []", "check_remote(root, remote)"]
    for f in ("refuse_if_marker", "refuse_if_st10_record"):
        calls = [ast.unparse(c) for c in ast.walk(TGF[f]) if isinstance(c, ast.Call) and callee(c) in ("_where", "remote_heads")]
        revs = [ast.unparse(s) for s in ast.walk(TGF[f]) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) in ("revs", "where")]
        print("  %s: %s | %s" % (f, calls, revs))
        ok &= any("['--all', '--reflog'] + remote_heads(root, remote)" in r for r in revs)
    callers = sorted({f for f, fn in TGF.items() for c in ast.walk(fn) if isinstance(c, ast.Call) and callee(c) == "_ever_committed"})
    print("  callers of _ever_committed: %s" % callers)

    print("\n== h. begin_test_evaluation: order; preconditions; BLOCKED vs refused")
    steps = [("refuse_if_marker", call_line(bt, "refuse_if_marker")), ("verify_authorization", call_line(bt, "verify_authorization")),
             ("st10_check", call_line(bt, "st10_check")), ("base hash check", first_line(bt, lambda n: isinstance(n, ast.If) and "HEX64" in ast.unparse(n.test))),
             ("staged check", first_line(bt, lambda n: isinstance(n, ast.If) and "--cached" in ast.unparse(n.test))),
             ("_commit_preconditions", call_line(bt, "_commit_preconditions")), ("code_commit", call_line(bt, "code_commit")),
             ("marker write_bytes", call_line(bt, "write_bytes")), ("commit_paths", call_line(bt, "commit_paths")),
             ("_LIVE registration", first_line(bt, lambda n: isinstance(n, ast.Subscript) and ast.unparse(n.value) == "_LIVE" and isinstance(n.ctx, ast.Store)))]
    print("  line of each step: %s" % steps)
    ok &= all(l is not None for _, l in steps) and [l for _, l in steps] == sorted(l for _, l in steps)
    cp = TGF["_commit_preconditions"]
    cpg = [ast.unparse(c) for c in ast.walk(cp) if isinstance(c, ast.Call) and callee(c) == "_git"]
    print("  _commit_preconditions git calls: %s" % cpg)
    print("  _commit_preconditions raises: %s" % raises_in(cp))
    ok &= any("'var', 'GIT_COMMITTER_IDENT'" in g for g in cpg) and any("'push', '--dry-run', '--no-follow-tags'" in g for g in cpg) \
        and all(e.startswith("_blocked(") for _, e in raises_in(cp))
    print("  _commit_preconditions first statement: %s | commit_paths first statements: %s" % (
        ast.unparse(body_of(cp)[0]), [ast.unparse(s) for s in body_of(TGF["commit_paths"])][:2]))
    ok &= ast.unparse(body_of(cp)[0]) == "check_remote(root, remote, branch)" and \
        [ast.unparse(s) for s in body_of(TGF["commit_paths"])][1] == "check_remote(root, remote, branch)"
    fin_ifs = [ast.unparse(n.test) for n in ast.walk(TGF["finish_test_evaluation"]) if isinstance(n, ast.If)]
    print("  finish_test_evaluation tests: %s" % fin_ifs)
    ok &= any("sha != session.marker_sha256" in t for t in fin_ifs)
    rts = [ast.unparse(s) for s in ast.walk(TGF["require_test_session"]) if isinstance(s, ast.Return)]
    print("  require_test_session return statements: %s" % rts)
    pg = [ast.unparse(c) for c in ast.walk(TGF["_push"]) if isinstance(c, ast.Call) and callee(c) == "_git"]
    print("  _push git calls: %s" % pg)
    ok &= any("'push', '--no-follow-tags', remote" in g for g in pg) and not any("--force" in g or "'-f'" in g for g in pg)
    print("  commit_paths raises: %s" % raises_in(TGF["commit_paths"]))
    print("  begin_test_evaluation raises: %s" % raises_in(bt))
    rim = raises_in(TGF["refuse_if_marker"])
    print("  refuse_if_marker raises: %s" % rim)
    ok &= any(e.startswith("TestAlreadyEvaluated(") for _, e in rim) and any(e.startswith("ProtocolStop(None, 'BLOCKED'") for _, e in rim)
    res_first = [ast.unparse(s.test) for s in TGF["refuse_if_marker"].body if isinstance(s, ast.If)]
    print("  refuse_if_marker tests in order: %s (a result anywhere is tested before the marker)" % res_first)
    ok &= res_first[:2] == ["result", "not where"]

    print("\n== i. B25 and the interpretation gate")
    it = trees["interpretations.py"]
    ents = [n for n in ast.walk(it) if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "ENTRIES"][0].value
    st_of = {}
    for e in ents.elts:
        d = {ast.literal_eval(k): v for k, v in zip(e.keys, e.values)}
        st_of[ast.literal_eval(d["id"])] = ast.unparse(d["status"]) if "status" in d else "(absent -> PENDING)"
    print("  ids %s..%s (%d) | status of B25: %s | entries without status: %s" % (
        list(st_of)[0], list(st_of)[-1], len(st_of), st_of.get("B25"), [i for i, s in st_of.items() if s.startswith("(absent")]))
    ok &= st_of.get("B25", "").startswith("(absent") and [i for i, s in st_of.items() if s.startswith("(absent")] == ["B25"]
    va = functions(trees["leakage.py"])["verify_authorization"]
    print("  verify_authorization calls pending_problem: %s" % (call_line(va, "pending_problem") is not None))
    ok &= call_line(va, "pending_problem") is not None
    for mod, f in (("test_data.py", "generate_test"), ("leakage.py", "run_test_part"), ("evaluate.py", "evaluate_model"),
                   ("testgate.py", "begin_test_evaluation")):
        ln = call_line(functions(trees[mod])[f], "verify_authorization")
        print("  %s.%s calls verify_authorization: %s" % (mod, f, ln is not None))
        ok &= ln is not None
    print("  test_data.check_interpretations_ruled calls pending_problem: %s" % (
        call_line(functions(td)["check_interpretations_ruled"], "pending_problem") is not None))

    print("\nstatic checks a-i: %s" % ("PASS" if ok else "FAIL"))
    print("\n== j. the staged probe against the round-3 interfaces")
    sess = [n for n in tg.body if isinstance(n, ast.ClassDef) and n.name == "TestSession"][0]
    fields = [s.target.id for s in sess.body if isinstance(s, ast.AnnAssign)]
    print("  TestSession fields: %s" % fields)
    pt = ast.parse(probe)
    mods = {"TG": "testgate.py", "E": "evaluate.py", "LK": "leakage.py", "FZ": "frozen.py", "R": "record.py", "M": "mode.py"}
    imports = {a.asname: a.name for n in ast.walk(pt) if isinstance(n, ast.ImportFrom) and n.module
               and n.module.startswith("metrix_e1") for a in n.names if a.asname}
    print("  probe imports (alias -> module of metrix_e1): %s" % imports)
    ok &= all(imports.get(k) + ".py" == v for k, v in mods.items())
    for f in ("mode.py", "record.py", "frozen.py"):
        if f not in trees:
            trees[f] = ast.parse(open(os.path.join(repo, PKG, "metrix_e1", f), encoding="utf-8").read())
    bad = []

    def top_names(t):
        s = set()
        for n in t.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                s.add(n.name)
            elif isinstance(n, ast.Assign):
                for tg_ in n.targets:
                    s |= {x.id for x in ast.walk(tg_) if isinstance(x, ast.Name)}
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                s.add(n.target.id)
        return s

    def params_of(t, name):
        for n in t.body:
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return [a.arg for a in n.args.args], [a.arg for a in n.args.kwonlyargs], n.args.vararg is not None
            if isinstance(n, ast.ClassDef) and n.name == name:
                init = [m for m in n.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"]
                if init:
                    return [a.arg for a in init[0].args.args][1:], [a.arg for a in init[0].args.kwonlyargs], False
                return [s.target.id for s in n.body if isinstance(s, ast.AnnAssign)], [], False
        return None

    for n in ast.walk(pt):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in mods and n.value.id in imports:
            t = trees[mods[n.value.id]]
            exists = n.attr in top_names(t)
            if not exists:
                bad.append("line %d: %s.%s does not exist" % (n.lineno, n.value.id, n.attr))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                and n.func.value.id in mods and n.func.value.id in imports:
            t = trees[mods[n.func.value.id]]
            p = params_of(t, n.func.attr)
            if p is None:
                print("  line %d %s: not a function or class of %s" % (n.lineno, ast.unparse(n.func), mods[n.func.value.id]))
                continue
            pos, kwo, var = p
            npos, kws = len(n.args), [k.arg for k in n.keywords]
            good = (npos <= len(pos) or var) and all(k in pos[npos:] or k in kwo for k in kws)
            print("  line %3d %-70s -> %s: %s" % (n.lineno, ast.unparse(n)[:70], pos + (["*"] if kwo else []) + kwo,
                                                 "ok" if good else "MISMATCH"))
            if not good:
                bad.append("line %d: %s" % (n.lineno, ast.unparse(n)[:80]))
    reads = sorted({(n.lineno, n.attr) for n in ast.walk(pt) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == "session" and isinstance(n.ctx, ast.Load)})
    for ln, a in reads:
        print("  line %d session.%s -> TestSession field: %s" % (ln, a, "ok" if a in fields else "MISSING"))
        if a not in fields:
            bad.append("line %d: session.%s" % (ln, a))
    assigns = [(n.lineno, ast.unparse(n)[:110]) for n in ast.walk(pt) if isinstance(n, ast.Assign)
               and any(isinstance(x, ast.Attribute) for t_ in n.targets for x in ast.walk(t_))]
    print("  module attributes the probe assigns: %s" % assigns)
    print("  probe interface mismatches: %s" % bad)
    ok &= bad == []

    print("\n== k. remote, branch, shallow clone, credentials")
    cr = TGF["check_remote"]
    for s in body_of(cr):
        print("   | " + ast.unparse(s).replace("\n", "\n   | "))
    branch_if = [s for s in body_of(cr) if isinstance(s, ast.If) and ast.unparse(s.test) == "branch is not None"]
    checked_out_inside = bool(branch_if) and "--abbrev-ref" in ast.unparse(branch_if[0])
    checked_out_outside = any("--abbrev-ref" in ast.unparse(s) for s in body_of(cr) if s not in branch_if)
    print("  the checked-out branch is tested only when a branch argument is given: %s (also outside that test: %s)" % (
        checked_out_inside and not checked_out_outside, checked_out_outside))
    callers = []
    for mod in ("testgate.py", "test_data.py"):
        for f, fn in functions(trees[mod]).items():
            for c in ast.walk(fn):
                if isinstance(c, ast.Call) and callee(c) == "check_remote":
                    callers.append((mod, f, ast.unparse(c), len(c.args) + len(c.keywords) >= 3))
    for mod, f, call, has_branch in callers:
        print("  %-12s %-24s %-60s branch given (checked-out branch tested): %s" % (mod, f, call, has_branch))
    print("  callers of remote_heads: %s" % sorted({f for f, fn in TGF.items() for c in ast.walk(fn)
                                                   if isinstance(c, ast.Call) and callee(c) == "remote_heads"}))
    ok &= {(m, f) for m, f, _, b in callers if b} == {("testgate.py", "commit_paths"), ("testgate.py", "_commit_preconditions"),
                                                      ("test_data.py", "main")} \
        and {(m, f) for m, f, _, b in callers if not b} == {("testgate.py", "remote_heads")}
    consts = {ast.unparse(n.targets[0]): ast.unparse(n.value) for n in tg.body if isinstance(n, ast.Assign)
              and ast.unparse(n.targets[0]) in ("CANONICAL_REPO", "PILOT_REMOTE", "PILOT_BRANCH", "_USERINFO")}
    print("  constants: %s" % consts)
    ok &= consts.get("CANONICAL_REPO") == "'leotree2020/OpenMythos'" and consts.get("PILOT_BRANCH") == "'metrix-e1-pilot-protocol-v1'"
    claude = open(os.path.join(repo, "metrix/CLAUDE.md"), encoding="utf-8").read()
    print("  metrix/CLAUDE.md section 2 names branch metrix-e1-pilot-protocol-v1: %s | base repository leotree2020/OpenMythos: %s"
          % ("分支:metrix-e1-pilot-protocol-v1" in claude, "leotree2020/OpenMythos" in claude))
    scrub_uses = sorted({f for f, fn in TGF.items() for c in ast.walk(fn) if isinstance(c, ast.Call) and callee(c) == "scrub"})
    print("  scrub applied in: %s" % scrub_uses)
    ok &= {"_blocked", "_push", "commit_paths", "remote_url", "repo_id"} <= set(scrub_uses)
    unscrubbed = []
    for f, fn in TGF.items():
        for ln, e in raises_in(fn):
            if ("stderr" in e or "stdout" in e or "url" in e.lower()) and "scrub(" not in e and not e.startswith("_blocked("):
                unscrubbed.append((f, ln, e))
    print("  raise sites carrying git output or a URL without scrub (INFO; git log / status of the local repository): %s" % unscrubbed)
    sh_line = [ast.unparse(s) for s in body_of(cr) if "is-shallow-repository" in ast.unparse(s)]
    print("  shallow test: %s" % sh_line)
    ok &= len(sh_line) == 1 and "_blocked(" in sh_line[0]

    print("\n== l. the probe's guard")
    pm = [n for n in pt.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    stm = [ast.unparse(s) for s in pm.body]
    i_ref = next((i for i, s in enumerate(stm) if s.startswith("if repo == PILOT.parents[1] or origin == TG.CANONICAL_REPO")), None)
    i_ovr = next((i for i, s in enumerate(stm) if s.startswith("TG.CANONICAL_REPO, TG.PILOT_BRANCH = (origin, 'main')")), None)
    i_loop = next((i for i, s in enumerate(stm) if s.startswith("for op in ops")), None)
    i_fz = next((i for i, s in enumerate(stm) if s.startswith("fz = ")), None)
    print("  statement index: refusal %s | override %s | fz load %s | operations loop %s" % (i_ref, i_ovr, i_fz, i_loop))
    print("  refusal: %s" % (stm[i_ref].replace("\n", " ") if i_ref is not None else None))
    print("  PILOT = %s" % [ast.unparse(n.value) for n in pt.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "PILOT"])
    ok &= None not in (i_ref, i_ovr, i_loop, i_fz) and i_ref < i_ovr < i_fz < i_loop and "sys.exit(" in stm[i_ref]
    return bool(ok)


run(main)
