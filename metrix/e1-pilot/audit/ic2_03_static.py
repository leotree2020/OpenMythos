"""ic2_03 (implementation stage C, C1 work commit, task 3, static).  Every file is read as text (working tree, which
equals the index; checked) and parsed with the standard `ast` module; nothing of the package is imported or run.
  a. TEST references in src/: every function of src/metrix_e1/*.py and src/metrix/**.py that names a TEST file, the
     TEST constants, eval_sets, or calls a TEST path; the set at HEAD vs now, and for every function new to the set,
     its I/O-like calls (what it opens / reads / writes);
  b. testgate.py: every I/O-like call (with its argument text), per function; the TEST rows (`data`) are used only by
     rows_hashes_of -> rows_sha256 (canonical JSONL bytes -> sha256); no function opens a TEST file or eval_sets;
  c. test_data.main: the order of the steps (preconditions -> --out outside the repository -> --out empty ->
     refuse_if_st10_record -> generate_test -> write files to --out -> run_test_part -> report to --out ->
     write_st10_record) and the exact --out test;
  d. what the ST10 record and the marker hold: the dict literals of testgate.st10_record and begin_test_evaluation
     (keys and value expressions); st10_record reads only report["checks"][c]["value"] (never "detail", which may
     quote TEST);
  e. evaluate.evaluate_model, split "test": verify_authorization and require_test_session before require_gpu and before
     the first read of data[...] rows;
  f. tests/ and reports/impl_c/{c1_gate_probe.py, c1_mutate.py}: every call of a TEST path (test_data.main /
     generate_test, leakage.run_test_part, evaluate_model(split="test"), testgate functions) with the data it gets;
     the monkeypatches in force for each test_data.main call; every reference to eval_sets / test_qa.jsonl /
     general_test.jsonl / a real data directory in the new or changed tests;
  g. the history search used by "TEST once" and "TEST generated once" (git log arguments).
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ic2_03_static.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import glob
import re
from ia_common import git, run

PKG = "metrix/e1-pilot/src"
TESTS = "metrix/e1-pilot/tests"
TEST_NAMES = {"test_qa", "general_test", "TEST_FILES", "eval_sets", "test_qa.jsonl", "general_test.jsonl"}
TEST_PATHS = {"generate_test", "run_test_part", "build_test_qa", "begin_test_evaluation", "require_test_session",
              "st10_check", "finish_test_evaluation", "write_st10_record", "st10_record", "refuse_if_marker",
              "refuse_if_st10_record", "rows_hashes_of", "rows_sha256"}
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
        body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant)) else fn.body
        hit = set()
        for st in body:
            nm = names_in(st)
            hit |= (nm & TEST_NAMES) | (nm & TEST_PATHS)
        if hit:
            out[name] = sorted(hit)
    return out


def io_calls(fn):
    return ["%s(%s)" % (callee(c), ", ".join(ast.unparse(a) for a in c.args)[:110]) for c in ast.walk(fn)
            if isinstance(c, ast.Call) and callee(c) in IO]


def main():
    repo = sys.argv[1]
    ok = True
    st = git(repo, "status", "--porcelain", "--untracked-files=no", "--", PKG, TESTS, check=False).stdout.decode().splitlines()
    print("src/ and tests/ status (tracked): %s | working tree == index: %s" % (
        st, git(repo, "diff", "--quiet", "--", PKG, TESTS, check=False).returncode == 0))
    ok &= git(repo, "diff", "--quiet", "--", PKG, TESTS, check=False).returncode == 0

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
    for f, fn in functions(tg).items():
        calls = io_calls(fn)
        if calls:
            print("  %-24s %s" % (f, calls))
    reads = [c for fn in functions(tg).values() for c in io_calls(fn) if c.split("(")[0] in ("open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl")]
    print("file reads (open / read_*): %s" % reads)
    ok &= reads == []
    uses = []
    for f, fn in functions(tg).items():
        for n in ast.walk(fn):
            if isinstance(n, ast.Name) and n.id == "data" and isinstance(n.ctx, ast.Load):
                uses.append(f)
    print("functions that load the name `data` (the TEST rows): %s" % sorted(set(uses)))
    rh = functions(tg)["rows_hashes_of"]
    rs = functions(tg)["rows_sha256"]
    print("rows_hashes_of: %s" % [ast.unparse(s) for s in rh.body[1:]])
    print("rows_sha256   : %s" % [ast.unparse(s) for s in rs.body[1:]])
    data_uses = {}
    for f in sorted(set(uses)):
        data_uses[f] = sorted({ast.unparse(p) for p in ast.walk(functions(tg)[f]) if isinstance(p, ast.Call)
                               and any(isinstance(a, ast.Name) and a.id == "data" for a in p.args)})
    print("calls receiving `data`: %s" % data_uses)
    allowed = all(all(c.startswith("rows_hashes_of(data)") or c.startswith("rows_sha256(data[n])") for c in v) for v in data_uses.values())
    print("the TEST rows only go to rows_hashes_of / rows_sha256 (hash of the canonical JSONL bytes): %s" % allowed)
    ok &= allowed and [ast.unparse(s) for s in rs.body[1:]] == ["return FZ.sha256_hex(FZ.jsonl_bytes(rows))"]

    print("\n== c. test_data.main: order of the steps and the --out test")
    td = trees["test_data.py"]
    mn = functions(td)["main"]
    order = []
    for i, s in enumerate(mn.body):
        txt = ast.unparse(s).split("\n")[0]
        for key in ("check_preconditions", "out.resolve() == root", "present = ", "refuse_if_st10_record", "generate_test(",
                    "out.mkdir", "run_test_part", "leakage_test_report", "write_st10_record"):
            if key in ast.unparse(s) and key not in [k for k, _ in order]:
                order.append((key, i))
    print("statement index of each step: %s" % order)
    idx = [i for _, i in order]
    ok &= [k for k, _ in order] == ["check_preconditions", "out.resolve() == root", "present = ", "refuse_if_st10_record",
                                     "generate_test(", "out.mkdir", "run_test_part", "leakage_test_report", "write_st10_record"] \
        and idx == sorted(idx)
    tests = [ast.unparse(s) for s in mn.body if isinstance(s, ast.If) and "resolve" in ast.unparse(s.test)]
    roots = [ast.unparse(s) for s in mn.body if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "root"]
    print("--out test: %s | %s" % (roots, tests))
    ok &= roots == ["root = fz.repo_root.resolve()"] and len(tests) == 1 and \
        ast.unparse(mn.body[[ast.unparse(s) for s in mn.body].index(tests[0])].test) == "out.resolve() == root or root in out.resolve().parents"
    cc = functions(tg)["code_commit"]
    print("note: testgate.code_commit (uncommitted-code refusal) is reached through write_st10_record, i.e. after "
          "generate_test and run_test_part (statement order above)")

    print("\n== d. ST10 record and marker contents")
    sr = functions(tg)["st10_record"]
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
    bt = functions(tg)["begin_test_evaluation"]
    md = [s for s in ast.walk(bt) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "marker"]
    mk = {ast.literal_eval(k): ast.unparse(v) for k, v in zip(md[0].value.keys, md[0].value.values)}
    for k, v in mk.items():
        print("  marker[%r] = %s" % (k, v))
    ok &= "data" not in " ".join(mk.values()).replace("rows_hashes", "")
    fin = functions(tg)["finish_test_evaluation"]
    print("  finish_test_evaluation writes: %s  (the caller's `result`; content decided in C2)" % [
        c for c in io_calls(fin) if c.startswith("write")])

    print("\n== e. evaluate.evaluate_model, split 'test': gate order")
    ev = functions(trees["evaluate.py"])["evaluate_model"]
    seq = []
    for n in ast.walk(ev):
        if isinstance(n, ast.Call) and callee(n) in ("verify_authorization", "require_test_session", "require_gpu"):
            seq.append((n.lineno, callee(n)))
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "data":
            seq.append((n.lineno, "data[%s]" % ast.unparse(n.slice)))
    seq.sort()
    print("  %s" % seq)
    first_data = min(l for l, w in seq if w.startswith("data["))
    gates = {w: l for l, w in seq if not w.startswith("data[")}
    ok &= gates["verify_authorization"] < gates["require_test_session"] < gates["require_gpu"] < first_data

    print("\n== f. tests/ and reports/impl_c scripts: TEST-path calls and the data they get")
    tfiles = sorted(glob.glob(os.path.join(repo, TESTS, "*.py"))) + [
        os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1_gate_probe.py"),
        os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1_mutate.py")]
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
        ev_refs = [m.start() for m in re.finditer(r"eval_sets", src)]
        if rel in changed or hits:
            print("  %s (%s): %d TEST-path calls; 'eval_sets' mentioned %d times" % (rel, "changed" if rel in changed else "unchanged",
                                                                                 len(hits), len(ev_refs)))
            for h in hits:
                print("     %s:%d %s" % h)
    tt = ast.parse(open(os.path.join(repo, TESTS, "test_testgate.py"), encoding="utf-8").read())
    for fn in functions(tt).values():
        mains = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and ast.unparse(c.func) == "TD.main"]
        if mains:
            patches = [ast.unparse(c.args[0]) + "." + ast.literal_eval(c.args[1]) for c in ast.walk(fn)
                       if isinstance(c, ast.Call) and ast.unparse(c.func) == "monkeypatch.setattr" and len(c.args) >= 2
                       and isinstance(c.args[1], ast.Constant)]
            first_main = min(c.lineno for c in mains)
            before = [ast.unparse(c.args[0]) + "." + ast.literal_eval(c.args[1]) for c in ast.walk(fn)
                      if isinstance(c, ast.Call) and ast.unparse(c.func) == "monkeypatch.setattr" and len(c.args) >= 2
                      and isinstance(c.args[1], ast.Constant) and c.lineno < first_main]
            inputs = sorted({ast.unparse(c.args[0].elts[1]) for c in mains if isinstance(c.args[0], ast.List)})
            print("  test_testgate.%s: TD.main called %d times; monkeypatched before the first call: %s; --inputs %s" % (
                fn.name, len(mains), before, inputs))
            ok &= {"TD.check_preconditions", "TD.generate_test", "TD.LK.run_test_part"} <= set(before) and inputs == ["'unused'"]
    syn = [ln for ln in open(os.path.join(repo, TESTS, "test_testgate.py"), encoding="utf-8").read().split("\n")
           if re.search(r"eval_sets|inputs_dir|generated\[|c1_data|scratchpad|METRIX_INPUTS", ln)]
    print("  test_testgate.py lines naming eval_sets / inputs_dir / a generated data dir / METRIX_INPUTS: %s" % syn)
    for p in tfiles:
        rel = os.path.relpath(p, repo)
        if rel in changed:
            hb = git(repo, "cat-file", "blob", "HEAD:" + rel, check=False)
            old_l = [ln for ln in (hb.stdout.decode("utf-8").split("\n") if hb.returncode == 0 else []) if "eval_sets" in ln]
            new_l = [ln for ln in open(p, encoding="utf-8").read().split("\n") if "eval_sets" in ln]
            same = old_l == new_l
            print("  %s: lines naming eval_sets HEAD %d / now %d, identical: %s" % (rel, len(old_l), len(new_l), same))
            if not same:
                print("     now: %s" % [ln.strip()[:150] for ln in new_l if ln not in old_l])
                ok &= rel.endswith("test_testgate.py") and all(ln.strip().startswith("generated, read or counted") for ln in new_l)
    probe = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1_gate_probe.py"), encoding="utf-8").read()
    print("  c1_gate_probe.py: TEST rows read from %s" % re.findall(r"data = \{[^\n]*", probe))

    print("\n== g. history search of 'TEST once' / 'TEST generated once'")
    ec = functions(tg)["_ever_committed"]
    print("  _ever_committed: %s" % [ast.unparse(s) for s in ec.body[1:]])
    gl = [ast.unparse(c) for c in ast.walk(ec) if isinstance(c, ast.Call) and callee(c) == "_git"]
    full = any("--full-history" in g for g in gl)
    print("  git log arguments: %s | --full-history given: %s" % (gl, full))
    print("  note: without --full-history, `git log <revs> -- <path>` applies the default history simplification: a "
          "side branch whose net change to <path> is nil is pruned at a merge that is TREESAME to its first parent, so a "
          "marker (or ST10 record, or result) added and removed on such a branch is not listed (see ic2_01 B05)")
    print("  callers of _ever_committed: %s" % sorted({f for f, fn in functions(tg).items()
                                                       for c in ast.walk(fn) if isinstance(c, ast.Call) and callee(c) == "_ever_committed"}))
    return bool(ok)


run(main)
