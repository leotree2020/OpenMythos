"""IB-6 (implementation stage B, task 5, static part): can anything in the Executor's package parse or decode an
eval_sets.jsonl row whose split is not dev, or instantiate a TEST question, before the three preconditions of the TEST
generator hold?  The source files are read as text and parsed with the standard `ast` module (never imported or run).
Checked:
  a. every call site, in every module of src/metrix_e1 and in reports/impl_b/dump_for_audit.py, of the TEST entry
     points generate_test, build_test_qa, params_for_test, run_test_part, TestAuthorization, and of build_general_dev
     (the only reader of eval_sets.jsonl rows); every read of the "TEST" template key, splits["TEST"],
     general_text["test"]; every open() / read of a TEST file name;
  b. test_data.main: the try block holds only check_preconditions; its handler prints, then sys.exit(1); everything that
     generates comes after the try statement; other exceptions are not caught in main (they leave main);
  c. test_data.check_preconditions: what it calls (no generator, no TEST reader) and that TestAuthorization is built
     last; generate_test and leakage.run_test_part start with an isinstance(authorization, TestAuthorization) guard that
     raises;
  d. data.build_general_dev: inside the row loop, the non-dev `continue` precedes json.loads and every other use of the
     row; how the file is opened; the split value it compares with comes from the frozen DATA_MANIFEST general_text.dev;
  e. leakage.py: files it opens; L1 / L2 use template texts only (no {E} / {A} substitution in the module).
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ib_06_static.py <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, re
from ia_common import frozen_json, run

PKG = "metrix/e1-pilot/src/metrix_e1"
EXTRA = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py"]
WATCH = ["generate_test", "build_test_qa", "params_for_test", "run_test_part", "TestAuthorization", "build_general_dev"]


def callee(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def enclosing(tree):
    """{id(node): name of the innermost enclosing function (or '<module>')}"""
    out = {}

    def walk(n, fn):
        for c in ast.iter_child_nodes(n):
            name = c.name if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            out[id(c)] = name
            walk(c, name)
    walk(tree, "<module>")
    return out


def main():
    repo = sys.argv[1]
    ok = True
    files = sorted(os.path.join(PKG, x) for x in os.listdir(os.path.join(repo, PKG)) if x.endswith(".py")) + EXTRA
    trees = {}
    for rel in files:
        src = open(os.path.join(repo, rel), encoding="utf-8").read()
        trees[rel] = (src, ast.parse(src, rel))
    print("files parsed:", [os.path.basename(f) for f in files])

    print("\n== a. call sites of the TEST entry points and of build_general_dev")
    sites = {w: [] for w in WATCH}
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and callee(n) in sites:
                sites[callee(n)].append((os.path.basename(rel), n.lineno, enc_of[id(n)]))
    for w in WATCH:
        print(f"  {w}: {sites[w]}")
    expect = {"generate_test": [("test_data.py", "main")], "build_test_qa": [("test_data.py", "generate_test")],
              "params_for_test": [("test_data.py", "generate_test")], "run_test_part": [("test_data.py", "main")],
              "TestAuthorization": [("test_data.py", "check_preconditions")],
              "build_general_dev": [("data.py", "generate"), ("test_data.py", "generate_test")]}
    for w, e in expect.items():
        got = sorted({(f, fn) for f, _, fn in sites[w]})
        same = got == sorted(e)
        ok &= same
        print(f"  {w}: called only from {got} | expected {sorted(e)} | {same}")
    print("  string keys that select TEST material:")
    hits = []
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("TEST", "test", "test_qa.jsonl", "general_test.jsonl"):
                hits.append((os.path.basename(rel), n.lineno, enc_of[id(n)], n.value))
    for h in hits:
        print("   ", h)
    allowed_fn = {"generate_test", "build_test_qa", "params_for_test", "main", "<module>", "run_test_part"}
    stray = [h for h in hits if not (h[0] in ("test_data.py", "data.py", "leakage.py") and h[2] in allowed_fn)]
    print(f"  constants outside test_data.py generation / module-level constants / leakage.run_test_part: {stray}")
    ok &= not stray

    print("\n== b. test_data.main")
    src, tree = trees[f"{PKG}/test_data.py"]
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    main_fn = fns["main"]
    try_i = next(i for i, s in enumerate(main_fn.body) if isinstance(s, ast.Try))
    t = main_fn.body[try_i]
    try_calls = [callee(n) for s in t.body for n in ast.walk(s) if isinstance(n, ast.Call)]
    handlers = [(ast.unparse(h.type), [ast.unparse(s) for s in h.body]) for h in t.handlers]
    print(f"  statements before the try: {[ast.unparse(s)[:60] for s in main_fn.body[:try_i]]}")
    print(f"  try body calls: {try_calls}")
    print(f"  handlers: {handlers}")
    last = t.handlers[0].body[-1] if t.handlers else None
    exits = last is not None and isinstance(last, ast.Expr) and ast.unparse(last) == "sys.exit(1)"
    after = [callee(n) for s in main_fn.body[try_i + 1:] for n in ast.walk(s) if isinstance(n, ast.Call)]
    before = [callee(n) for s in main_fn.body[:try_i] for n in ast.walk(s) if isinstance(n, ast.Call)]
    print(f"  handler ends with sys.exit(1): {exits} | finally / else clauses: {bool(t.finalbody)} / {bool(t.orelse)} | calls after the try: {after}")
    ok &= try_calls == ["check_preconditions"] and exits and len(t.handlers) == 1 and not t.finalbody and not t.orelse
    ok &= not (set(before) & set(WATCH)) and "generate_test" in after
    print(f"  handled exception types: {ast.unparse(t.handlers[0].type)} (any other exception leaves main before generation)")
    guarded = re.search(r'if __name__ == "__main__":\n    run_guarded\(main\)', src) is not None
    print(f"  module entry point is run_guarded(main): {guarded}")
    ok &= guarded

    print("\n== c. check_preconditions, guards")
    cp = fns["check_preconditions"]
    cp_calls = [callee(n) for n in ast.walk(cp) if isinstance(n, ast.Call)]
    print(f"  check_preconditions calls: {cp_calls}")
    ok &= not ({"generate_test", "build_test_qa", "params_for_test", "build_general_dev", "run_test_part"} & set(cp_calls))
    ret = cp.body[-1]
    print(f"  last statement: {ast.unparse(ret)}")
    ok &= isinstance(ret, ast.Return) and "TestAuthorization" in ast.unparse(ret)
    for rel, fname in ((f"{PKG}/test_data.py", "generate_test"), (f"{PKG}/leakage.py", "run_test_part")):
        fn = next(n for n in ast.walk(trees[rel][1]) if isinstance(n, ast.FunctionDef) and n.name == fname)
        body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        g = ast.unparse(body[0])
        good = g.startswith("if not isinstance(authorization,") and "TestAuthorization" in g and "raise" in g
        print(f"  {fname} first statement: {g!r} -> guard {good}")
        ok &= good
    cls_sites = sites["TestAuthorization"]
    print(f"  TestAuthorization(...) constructed at: {cls_sites}")

    print("\n== d. data.build_general_dev")
    dsrc, dtree = trees[f"{PKG}/data.py"]
    bg = next(n for n in ast.walk(dtree) if isinstance(n, ast.FunctionDef) and n.name == "build_general_dev")
    opens = [ast.unparse(n) for n in ast.walk(bg) if isinstance(n, ast.Call) and callee(n) == "open"]
    print(f"  open calls: {opens}")
    loop = next(n for n in ast.walk(bg) if isinstance(n, ast.For) and "enumerate(fh" in ast.unparse(n.iter))
    order = [ast.unparse(s).split("\n")[0][:90] for s in loop.body]
    for i, s in enumerate(order):
        print(f"    loop statement {i}: {s}")
    i_cont = next(i for i, s in enumerate(loop.body) if isinstance(s, ast.If) and any(isinstance(x, ast.Continue) for x in s.body)
                  and "general_dev_split" in ast.unparse(s.test))
    i_json = next(i for i, s in enumerate(loop.body) if "json.loads" in ast.unparse(s))
    uses_line_before = [ast.unparse(s)[:80] for s in loop.body[:i_cont] if "line" in ast.unparse(s)]
    print(f"  non-dev continue at statement {i_cont}, json.loads at statement {i_json}: continue first {i_cont < i_json}")
    print(f"  statements before the continue that use the line: {uses_line_before}")
    rh = re.search(r"_ROW_HEAD = re\.compile\((r'.*?')\)", dsrc)
    print(f"  _ROW_HEAD pattern: {rh.group(1) if rh else None} (used with .match, i.e. anchored at the line start)")
    ok &= i_cont < i_json and rh is not None
    dev = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]["dev"]
    m = re.fullmatch(r"first (\d+) windows per domain \(([a-z0-9, ]+)\) with split == '(\w+)', file order", dev)
    print(f"  frozen general_text.dev: {dev!r} -> split value the dev generation compares with: {m.group(3) if m else None}")
    ok &= m is not None and m.group(3) == "dev"
    text_mode = any("encoding=" in o and "'rb'" not in o and '"rb"' not in o for o in opens)
    print(f"  file opened in text mode (Python decodes every line, test rows included, from UTF-8 into str before the "
          f"prefix match; no JSON parse and no token decode of a non-dev row): {text_mode}")

    print("\n== e. leakage.py")
    lsrc, ltree = trees[f"{PKG}/leakage.py"]
    lopens = [(n.lineno, ast.unparse(n)) for n in ast.walk(ltree) if isinstance(n, ast.Call) and callee(n) in ("open", "read_jsonl", "read_text", "read_bytes")]
    print(f"  file reads: {lopens}")
    ld = next(n for n in ast.walk(ltree) if isinstance(n, ast.FunctionDef) and n.name == "load_data")
    names = [ast.unparse(e) for n in ast.walk(ld) if isinstance(n, ast.Tuple) for e in n.elts]
    print(f"  load_data file stems: {names}")
    ok &= not any("test" in x for x in names)
    subst = [n.lineno for n in ast.walk(ltree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("{E}", "{A}")]
    print(f"  '{{E}}' / '{{A}}' constants in leakage.py (template instantiation): {subst}")
    ok &= not subst
    lmain = next(n for n in ltree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    lm_calls = [callee(n) for n in ast.walk(lmain) if isinstance(n, ast.Call)]
    print(f"  leakage.main calls run_test_part: {'run_test_part' in lm_calls} | run_gate0: {'run_gate0' in lm_calls}")
    ok &= "run_test_part" not in lm_calls and "run_gate0" in lm_calls

    print("\n== f. every template instantiation in the package ({E} substitution: data.fill or .replace('{E}', ...))")
    inst = []
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and (callee(n) == "fill" or (callee(n) == "replace" and n.args and isinstance(n.args[0], ast.Constant)
                                                                    and n.args[0].value == "{E}" and isinstance(n.args[1], ast.Attribute) is False
                                                                    and ast.unparse(n.args[1]) != "'<ENTITY>'")):
                inst.append((os.path.basename(rel), n.lineno, enc_of[id(n)]))
    for x in sorted(set(inst)):
        print("   ", x)
    test_inst = sorted({x[2] for x in inst if x[0] == "test_data.py"})
    other = sorted({(x[0], x[2]) for x in inst if x[0] != "test_data.py"})
    print(f"  instantiation sites in test_data.py: {test_inst} | elsewhere: {other}")
    expected_other = [("data.py", "build_dev_qa"), ("data.py", "build_train_F"), ("data.py", "build_train_S"), ("data.py", "build_train_Y"),
                      ("data.py", "fill"), ("evaluate.py", "statement_prefix")]
    print(f"  elsewhere == the DEV / TRAIN / Y builders and prefix(f) (+ the definition of fill): {other == expected_other}")
    ok &= test_inst == ["build_test_qa"] and other == expected_other
    for fname, kind in (("build_train_F", "TRAIN"), ("build_train_S", "TRAIN"), ("build_train_Y", "Y_"), ("build_dev_qa", "DEV")):
        fn = next(n for n in ast.walk(trees[f"{PKG}/data.py"][1]) if isinstance(n, ast.FunctionDef) and n.name == fname)
        kinds = sorted({c.value for c in ast.walk(fn) if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value in ("TRAIN", "DEV", "TEST", "Y_ENTITY", "Y_ANSWER")})
        print(f"  data.{fname} template kinds selected: {kinds}")
        ok &= "TEST" not in kinds and any(k.startswith(kind) for k in kinds)
    tt = next(n for n in ast.walk(trees[f"{PKG}/evaluate.py"][1]) if isinstance(n, ast.FunctionDef) and n.name == "train_templates")
    print(f"  evaluate.train_templates selects: {ast.unparse(next(n for n in ast.walk(tt) if isinstance(n, ast.If)).test)}")
    return bool(ok)


run(main)
