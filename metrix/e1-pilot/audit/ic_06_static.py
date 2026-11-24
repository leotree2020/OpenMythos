"""IC-6 (implementation stage B, round 2, task 3, static part): after the round-1 fixes, can anything parse or decode an
eval_sets.jsonl row whose split is not dev, or instantiate a TEST question, before the TEST generator's three
preconditions (and the new interpretation check) hold?  Every source file is read as text and parsed with the standard
`ast` module (never imported or run).  Interpretations ENTRIES are read with ast.literal_eval (literals only).
  a. call sites (src/metrix_e1/*.py and reports/impl_b/dump_for_audit.py) of the TEST entry points, of
     build_general_dev, check_preconditions, check_interpretations_ruled, committed_json and evaluate_model; every
     constant that names TEST material; every file read in the package;
  b. data.build_general_dev: the file is opened in binary mode; _ROW_HEAD is a bytes pattern used with .match;
     inside the row loop, before the non-dev `continue`, the row bytes are used only by _ROW_HEAD.match(line) and
     the only decode is of the matched split field m.group(1); line.decode / json.loads come after the continue;
     `want` = p.general_dev_split.encode("ascii"); in data.generate p = params(fz), whose general_dev_split comes
     from the frozen DATA_MANIFEST general_text.dev (== 'dev'); in test_data.generate_test the TEST split is set
     only after the authorization guard;
  c. test_data.main (try body, handler, what follows) and check_preconditions (statement order: condition 1, 2, 3,
     the interpretation check, then TestAuthorization); check_interpretations_ruled raises when INT.pending() is not
     empty; interpretations.pending / ENTRIES (how many entries are pending now); record.committed_json reads only
     the named record (git cat-file blob HEAD:<rel> and the working-tree file);
  d. generate_test / run_test_part start with the isinstance guard; run_test_part re-checks the committed records
     before any statement that uses test_qa / general_test;
  e. leakage.py: files read; load_data stems; main does not call run_test_part; no {E}/{A} substitution;
  f. every template instantiation ({E} substitution) in the package, and the template kinds the builders select;
  g. evaluate.evaluate_model split "test": callers in the package, the reports script and the tests;
  h. tests/: every call of generate_test, build_test_qa, run_test_part, TestAuthorization (arguments printed);
     every reader of eval_sets.jsonl anywhere under metrix/ (*.py, *.sh) and how it opens the file, in particular
     reports/round5/l6_check.py, which tests/test_data_hashes.py runs on the real eval_sets.jsonl.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ic_06_static.py <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, re
from ia_common import frozen_json, run

PKG = "metrix/e1-pilot/src/metrix_e1"
EXTRA = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py"]
TESTS = "metrix/e1-pilot/tests"
WATCH = ["generate_test", "build_test_qa", "params_for_test", "run_test_part", "TestAuthorization", "build_general_dev",
         "check_preconditions", "check_interpretations_ruled", "committed_json", "evaluate_model"]


def callee(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def enclosing(tree):
    out = {}

    def walk(n, fn):
        for c in ast.iter_child_nodes(n):
            name = c.name if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            out[id(c)] = name
            walk(c, name)
    walk(tree, "<module>")
    return out


def func(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def body_wo_doc(fn):
    return [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]


def names_in(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def main():
    repo = sys.argv[1]
    ok = True
    files = sorted(os.path.join(PKG, x) for x in os.listdir(os.path.join(repo, PKG)) if x.endswith(".py")) + EXTRA
    trees = {}
    for rel in files:
        src = open(os.path.join(repo, rel), encoding="utf-8").read()
        trees[rel] = (src, ast.parse(src, rel))
    print("files parsed:", [os.path.basename(f) for f in files])
    T = lambda name: trees[f"{PKG}/{name}"][1]

    # ---------------------------------------------------------------------------------------------- a
    print("\n== a. call sites, TEST constants, file reads")
    sites = {w: [] for w in WATCH}
    consts, reads = [], []
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        b = os.path.basename(rel)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and callee(n) in sites:
                sites[callee(n)].append((b, n.lineno, enc_of[id(n)]))
            if isinstance(n, ast.Call) and callee(n) in ("open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl", "load", "loads"):
                reads.append((b, n.lineno, enc_of[id(n)], ast.unparse(n)[:90]))
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("TEST", "test", "test_qa.jsonl", "general_test.jsonl"):
                consts.append((b, n.lineno, enc_of[id(n)], n.value))
    for w in WATCH:
        print(f"  {w}: {sites[w]}")
    expect = {"generate_test": [("test_data.py", "main")], "build_test_qa": [("test_data.py", "generate_test")],
              "params_for_test": [("test_data.py", "generate_test")], "run_test_part": [("test_data.py", "main")],
              "TestAuthorization": [("test_data.py", "check_preconditions")],
              "build_general_dev": [("data.py", "generate"), ("test_data.py", "generate_test")],
              "check_preconditions": [("test_data.py", "main")],
              "check_interpretations_ruled": [("test_data.py", "check_preconditions")],
              "evaluate_model": []}
    for w, e in expect.items():
        got = sorted({(f, fn) for f, _, fn in sites[w]})
        same = got == sorted(e)
        ok &= same
        print(f"  {w}: called only from {got} | expected {sorted(e)} | {same}")
    print("  constants naming TEST material (file, line, function, value):")
    for c in consts:
        print("   ", c)
    allowed = {("data.py", "<module>"), ("evaluate.py", "<module>"), ("contract.py", "_accounting"), ("gate.py", "compute_test_values"),
               ("gate.py", "judge_test"), ("test_data.py", "params_for_test"), ("test_data.py", "build_test_qa"),
               ("test_data.py", "generate_test"), ("leakage.py", "run_test_part")}
    stray = [c for c in consts if (c[0], c[2]) not in allowed]
    print(f"  constants outside module-level name tuples, contract accounting (a count), gate T1-T3 labels, the generator and "
          f"run_test_part: {stray}")
    ok &= not stray
    print("  file reads in the package (file, line, function, call):")
    for r in reads:
        print("   ", r)
    ev_readers = [r for r in reads if "eval_sets" in r[3]]
    print(f"  calls that open eval_sets.jsonl: {ev_readers}")
    ok &= [(r[0], r[2]) for r in ev_readers] == [("data.py", "build_general_dev")]
    dsrc = trees[f"{PKG}/data.py"][0]
    df = re.search(r"^DATA_FILES = \((.*?)\)\n", dsrc, re.M | re.S)
    print(f"  data.DATA_FILES (read by data.file_hashes / verify): {df.group(1).split() if df else None}")
    ok &= df is not None and "test" not in df.group(1)

    # ---------------------------------------------------------------------------------------------- b
    print("\n== b. data.build_general_dev")
    dtree = T("data.py")
    rh = next(n for n in dtree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_ROW_HEAD" for t in n.targets))
    rh_arg = rh.value.args[0] if isinstance(rh.value, ast.Call) and rh.value.args else None
    is_bytes = isinstance(rh_arg, ast.Constant) and isinstance(rh_arg.value, bytes)
    print(f"  _ROW_HEAD = {ast.unparse(rh.value)} | pattern is bytes: {is_bytes}")
    ok &= is_bytes and callee(rh.value) == "compile"
    if is_bytes:
        pat = rh_arg.value
        groups = len(re.findall(rb"\((?!\?)", pat))
        split_grp = rb'"split": "([^"\\]*)", ' in pat and pat.startswith(rb'\{"domain": "[^"\\]*", "split": ')
        print(f"  pattern bytes {pat!r} | capture groups {groups} | anchored at the domain field, group 1 = the split value up to the "
              f"next quote: {split_grp}")
        ok &= groups == 1 and split_grp
    bg = func(dtree, "build_general_dev")
    opens = [n for n in ast.walk(bg) if isinstance(n, ast.Call) and callee(n) == "open"]
    print(f"  open calls: {[ast.unparse(o) for o in opens]}")
    binary = len(opens) == 1 and len(opens[0].args) == 2 and isinstance(opens[0].args[1], ast.Constant) and opens[0].args[1].value == "rb" \
        and not opens[0].keywords
    print(f"  exactly one open, mode 'rb', no encoding argument: {binary}")
    ok &= binary
    want = [ast.unparse(s) for s in body_wo_doc(bg) if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "want" for t in s.targets)]
    print(f"  want: {want}")
    ok &= want == ["want = p.general_dev_split.encode('ascii')"]
    loop = next(n for n in ast.walk(bg) if isinstance(n, ast.For) and "enumerate(fh" in ast.unparse(n.iter))
    for i, s in enumerate(loop.body):
        print(f"    loop statement {i}: {ast.unparse(s).split(chr(10))[0][:110]}")
    i_cont = next(i for i, s in enumerate(loop.body) if isinstance(s, ast.If) and any(isinstance(x, ast.Continue) for x in s.body))
    cont_test = ast.unparse(loop.body[i_cont].test)
    print(f"  non-dev continue: statement {i_cont}, test {cont_test!r}")
    ok &= cont_test == "m.group(1) != want"
    before = loop.body[:i_cont]
    line_uses = [ast.unparse(n) for s in before for n in ast.walk(s) if isinstance(n, ast.Call) and "line" in names_in(n)
                 and not any(isinstance(a, ast.Call) for a in n.args)]
    decodes_before = [ast.unparse(n) for s in before for n in ast.walk(s) if isinstance(n, ast.Call) and callee(n) in ("decode", "loads", "load")]
    print(f"  calls before the continue that take the row bytes: {line_uses}")
    print(f"  decode / json calls before the continue: {decodes_before}")
    ok &= line_uses == ["_ROW_HEAD.match(line)"] and decodes_before == ["m.group(1).decode('ascii', 'replace')"]
    after_dec = [(i, ast.unparse(n)) for i, s in enumerate(loop.body) for n in ast.walk(s)
                 if isinstance(n, ast.Call) and callee(n) in ("decode", "loads") and "line" in names_in(n)]
    print(f"  calls that decode or parse the row, with their statement index: {after_dec}")
    ok &= bool(after_dec) and all(i > i_cont for i, _ in after_dec)
    gen = func(dtree, "generate")
    p_assign = [ast.unparse(s) for s in body_wo_doc(gen) if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "p" for t in s.targets)]
    print(f"  data.generate: {p_assign} (the only p passed to build_general_dev there)")
    ok &= p_assign == ["p = params(fz)"]
    par = func(dtree, "params")
    gsplit = [ast.unparse(s)[:200] for s in ast.walk(par) if isinstance(s, ast.Assign) and "g_split" in ast.unparse(s.targets[0])]
    print(f"  data.params assignment of g_split: {gsplit}")
    ok &= len(gsplit) == 1 and "gt['dev']" in gsplit[0]
    dev = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]["dev"]
    m = re.fullmatch(r"first (\d+) windows per domain \(([a-z0-9, ]+)\) with split == '(\w+)', file order", dev)
    print(f"  frozen general_text.dev: {dev!r} -> split value: {m.group(3) if m else None}")
    ok &= m is not None and m.group(3) == "dev"
    gt_fn = func(T("test_data.py"), "generate_test")
    gtb = body_wo_doc(gt_fn)
    i_rep = next(i for i, s in enumerate(gtb) if "dataclasses.replace" in ast.unparse(s))
    print(f"  test_data.generate_test: statement 0 {ast.unparse(gtb[0]).split(chr(10))[0]!r}; the TEST split is set at statement {i_rep}: {ast.unparse(gtb[i_rep])!r}")
    ok &= i_rep > 0

    # ---------------------------------------------------------------------------------------------- c
    print("\n== c. test_data.main, check_preconditions, interpretation check, committed_json")
    ttree = T("test_data.py")
    fns = {n.name: n for n in ttree.body if isinstance(n, ast.FunctionDef)}
    mf = fns["main"]
    try_i = next(i for i, s in enumerate(mf.body) if isinstance(s, ast.Try))
    t = mf.body[try_i]
    try_calls = [callee(n) for s in t.body for n in ast.walk(s) if isinstance(n, ast.Call)]
    print(f"  statements before the try: {[ast.unparse(s)[:60] for s in mf.body[:try_i]]}")
    print(f"  try body calls: {try_calls} | handlers: {[(ast.unparse(h.type), [ast.unparse(s) for s in h.body]) for h in t.handlers]}")
    exits = len(t.handlers) == 1 and ast.unparse(t.handlers[0].body[-1]) == "sys.exit(1)"
    after = [callee(n) for s in mf.body[try_i + 1:] for n in ast.walk(s) if isinstance(n, ast.Call)]
    print(f"  handler ends with sys.exit(1): {exits} | finally / else: {bool(t.finalbody)} / {bool(t.orelse)} | calls after the try: {after}")
    ok &= try_calls == ["check_preconditions"] and exits and not t.finalbody and not t.orelse and "generate_test" in after
    tsrc = trees[f"{PKG}/test_data.py"][0]
    guarded = re.search(r'if __name__ == "__main__":\n    run_guarded\(main\)\s*$', tsrc) is not None
    print(f"  module entry point is run_guarded(main) (any other exception leaves main before generation): {guarded}")
    ok &= guarded
    cp = body_wo_doc(fns["check_preconditions"])
    order = [ast.unparse(s) for s in cp]
    for i, s in enumerate(order):
        print(f"    check_preconditions statement {i}: {s}")
    want_order = ["st12", "load", "check_data_dir", "check_gate0_record", "check_selection_record", "check_interpretations_ruled", "TestAuthorization"]
    got_order = [callee(next(n for n in ast.walk(s) if isinstance(n, ast.Call))) if not isinstance(s, ast.Return)
                 else [callee(n) for n in ast.walk(s) if isinstance(n, ast.Call)][0] for s in cp]
    print(f"  first call of each statement: {got_order} | == {want_order}: {got_order == want_order}")
    ok &= got_order == want_order and isinstance(cp[-1], ast.Return)
    cir = body_wo_doc(fns["check_interpretations_ruled"])
    print(f"  check_interpretations_ruled: {[ast.unparse(s) for s in cir]}")
    ok &= len(cir) == 2 and ast.unparse(cir[0]) == "open_ids = INT.pending()" and isinstance(cir[1], ast.If) \
        and isinstance(cir[1].body[0], ast.Raise) and "PreconditionFailed" in ast.unparse(cir[1].body[0])
    itree = T("interpretations.py")
    pend = func(itree, "pending")
    print(f"  interpretations.pending: {ast.unparse(body_wo_doc(pend)[0])}")
    ent = next(n for n in itree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "ENTRIES" for x in n.targets))
    entries = ast.literal_eval(ent.value)
    pc = next(n for n in itree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "PENDING" for x in n.targets))
    PENDING = ast.literal_eval(pc.value)
    pend_ids = [e["id"] for e in entries if e.get("status", PENDING) == PENDING]
    print(f"  ENTRIES {len(entries)} ids {[e['id'] for e in entries]} | with a status key {sum('status' in e for e in entries)} | pending now {len(pend_ids)}")
    print("  -> in the current state check_interpretations_ruled would also refuse (it runs after conditions 2 and 3)")
    ok &= len(pend_ids) == len(entries) > 0
    for name in ("_committed", "check_gate0_record", "check_selection_record"):
        calls = sorted({callee(n) for n in ast.walk(fns[name]) if isinstance(n, ast.Call)} - {None})
        print(f"  {name} calls: {calls}")
        ok &= not ({"generate_test", "build_test_qa", "build_general_dev", "fill", "read_jsonl", "open"} & set(calls))
    rtree = T("record.py")
    cj = func(rtree, "committed_json")
    cj_calls = [ast.unparse(n)[:100] for n in ast.walk(cj) if isinstance(n, ast.Call)]
    print(f"  record.committed_json calls: {cj_calls}")
    ok &= any("cat-file" in c and "HEAD:%s" in c for c in cj_calls) and not any("open(" in c for c in cj_calls)
    fzt = trees[f"{PKG}/frozen.py"][1]
    chd = func(fzt, "content_hashes")
    print(f"  frozen.content_hashes (check_data_dir) reads: {sorted({ast.unparse(n.args[0]) for n in ast.walk(chd) if isinstance(n, ast.Call) and callee(n) in ('read_jsonl', 'open')})}")

    # ---------------------------------------------------------------------------------------------- d
    print("\n== d. guards")
    for rel, fname in ((f"{PKG}/test_data.py", "generate_test"), (f"{PKG}/leakage.py", "run_test_part")):
        fn = func(trees[rel][1], fname)
        body = body_wo_doc(fn)
        g = ast.unparse(body[0])
        good = g.startswith("if not isinstance(authorization,") and "TestAuthorization" in g and "raise" in g
        print(f"  {fname} statement 0: {g!r} -> guard {good}")
        ok &= good
        if fname == "run_test_part":
            first_use = next(i for i, s in enumerate(body) if names_in(s) & {"test_qa", "general_test"})
            i_loop = next(i for i, s in enumerate(body) if isinstance(s, ast.For) and "committed_json" in ast.unparse(s))
            print(f"  run_test_part: record re-check loop at statement {i_loop} ({ast.unparse(body[i_loop].iter)[:90]}); first statement using "
                  f"test_qa / general_test: {first_use} ({ast.unparse(body[first_use])[:60]!r}) | re-check first {i_loop < first_use}")
            ok &= 0 < i_loop < first_use
    print(f"  TestAuthorization(...) constructed in the package at: {sites['TestAuthorization']}")

    # ---------------------------------------------------------------------------------------------- e
    print("\n== e. leakage.py")
    ltree = T("leakage.py")
    ld = func(ltree, "load_data")
    stems = [ast.literal_eval(e) for n in ast.walk(ld) if isinstance(n, ast.Tuple) for e in n.elts if isinstance(e, ast.Constant)]
    print(f"  load_data file stems: {stems}")
    ok &= stems and not any("test" in x for x in stems)
    subst = [n.lineno for n in ast.walk(ltree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("{E}", "{A}")]
    print(f"  '{{E}}' / '{{A}}' constants in leakage.py: {subst}")
    ok &= not subst
    lm = next(n for n in ltree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    lmc = [callee(n) for n in ast.walk(lm) if isinstance(n, ast.Call)]
    print(f"  leakage.main calls run_test_part: {'run_test_part' in lmc} | run_gate0: {'run_gate0' in lmc}")
    ok &= "run_test_part" not in lmc and "run_gate0" in lmc

    # ---------------------------------------------------------------------------------------------- f
    print("\n== f. template instantiation ({E} substitution)")
    inst = set()
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and (callee(n) == "fill" or (callee(n) == "replace" and n.args and isinstance(n.args[0], ast.Constant)
                                                                    and n.args[0].value == "{E}" and ast.unparse(n.args[1]) != "'<ENTITY>'")):
                inst.add((os.path.basename(rel), enc_of[id(n)]))
    for x in sorted(inst):
        print("   ", x)
    test_inst = sorted(fn for f, fn in inst if f == "test_data.py")
    other = sorted((f, fn) for f, fn in inst if f != "test_data.py")
    expected_other = [("data.py", "build_dev_qa"), ("data.py", "build_train_F"), ("data.py", "build_train_S"), ("data.py", "build_train_Y"),
                      ("data.py", "fill"), ("evaluate.py", "statement_prefix")]
    print(f"  in test_data.py: {test_inst} | elsewhere: {other} | elsewhere == DEV / TRAIN / Y builders, fill, prefix(f): {other == expected_other}")
    ok &= test_inst == ["build_test_qa"] and other == expected_other
    for fname, kind in (("build_train_F", "TRAIN"), ("build_train_S", "TRAIN"), ("build_train_Y", "Y_"), ("build_dev_qa", "DEV")):
        fn = func(dtree, fname)
        kinds = sorted({c.value for c in ast.walk(fn) if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value in ("TRAIN", "DEV", "TEST", "Y_ENTITY", "Y_ANSWER")})
        print(f"  data.{fname} template kinds selected: {kinds}")
        ok &= "TEST" not in kinds and any(k.startswith(kind) for k in kinds)
    etree = T("evaluate.py")
    tt = func(etree, "train_templates")
    print(f"  evaluate.train_templates selects: {ast.unparse(next(n for n in ast.walk(tt) if isinstance(n, ast.If)).test)}")
    sp_callers = sorted({fn for f, _, fn in [(os.path.basename(r), 0, enclosing(tr)[id(n)]) for r, (s, tr) in trees.items()
                                            for n in ast.walk(tr) if isinstance(n, ast.Call) and callee(n) == "statement_prefix"]})
    print(f"  statement_prefix (TRAIN template only) called from: {sp_callers}")

    # ---------------------------------------------------------------------------------------------- g
    print("\n== g. evaluate.evaluate_model with split 'test'")
    em = func(etree, "evaluate_model")
    sf = next(n for n in etree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "SPLIT_FILES" for x in n.targets))
    print(f"  {ast.unparse(sf)}")
    print(f"  evaluate_model signature: ({ast.unparse(em.args)})")
    print(f"  callers in src/ and reports/impl_b/dump_for_audit.py: {sites['evaluate_model']}")
    ok &= not sites["evaluate_model"]

    # ---------------------------------------------------------------------------------------------- h
    print("\n== h. tests/ and every eval_sets.jsonl reader under metrix/")
    tdir = os.path.join(repo, TESTS)
    for fn_ in sorted(os.listdir(tdir)):
        if not fn_.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read())
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and callee(n) in ("generate_test", "build_test_qa", "run_test_part", "TestAuthorization", "evaluate_model",
                                                         "params_for_test", "check_preconditions"):
                print(f"  {fn_}:{n.lineno} in {enc_of[id(n)]}: {ast.unparse(n)[:150]}")
                if callee(n) == "generate_test":
                    ok &= ast.unparse(n.args[1]) == "None"
                if callee(n) == "run_test_part":
                    ok &= ast.unparse(n.args[2]) == "[]" and ast.unparse(n.args[3]) == "[]"
                if callee(n) in ("build_test_qa", "params_for_test"):
                    ok = False
                if callee(n) == "evaluate_model":
                    ok &= not any(k.arg == "split" for k in n.keywords) and len(n.args) <= 7
    for fn_ in sorted(os.listdir(tdir)):
        if not fn_.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read())
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == "flip":
                print(f"  {fn_}:{n.lineno} flip() calls: {[ast.unparse(c) for c in ast.walk(n) if isinstance(c, ast.Call)]}")
            if isinstance(n, ast.Call) and callee(n) == "copyfile":
                print(f"  {fn_}:{n.lineno} in {enc_of[id(n)]}: byte copy: {ast.unparse(n)[:150]}")
            if isinstance(n, ast.Call) and ("general_source" in ast.unparse(n) or "eval_sets" in ast.unparse(n)) \
                    and not any(isinstance(a, ast.Call) and ("general_source" in ast.unparse(a) or "eval_sets" in ast.unparse(a)) for a in n.args):
                print(f"  {fn_}:{n.lineno} in {enc_of[id(n)]}: call on the eval_sets path: {ast.unparse(n)[:150]}")
    readers = []
    for r, ds, fs in os.walk(os.path.join(repo, "metrix")):
        if "/." in r or "__pycache__" in r:
            continue
        for f in fs:
            if f.endswith((".py", ".sh")):
                p = os.path.join(r, f)
                s = open(p, encoding="utf-8", errors="replace").read()
                if "eval_sets" in s or "eval-sets" in s:
                    readers.append(os.path.relpath(p, repo))
    print(f"  executable files under metrix/ that mention eval_sets: {readers}")
    for rel in readers:
        if rel.startswith("metrix/e1-pilot/audit/"):
            continue
        s = open(os.path.join(repo, rel), encoding="utf-8").read()
        try:
            tree = ast.parse(s)
        except SyntaxError:
            print(f"   {rel}: not Python")
            continue
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and callee(n) == "open" and n.args and ("eval" in ast.unparse(n.args[0])):
                print(f"   {rel}:{n.lineno} in {enc_of[id(n)]}: {ast.unparse(n)}")
    l6 = "metrix/e1-pilot/reports/round5/l6_check.py"
    l6t = ast.parse(open(os.path.join(repo, l6), encoding="utf-8").read())
    lp = next(n for n in ast.walk(l6t) if isinstance(n, ast.For) and "enumerate(fh" in ast.unparse(n.iter))
    for i, s in enumerate(lp.body):
        print(f"    l6_check.py loop statement {i}: {ast.unparse(s).split(chr(10))[0][:100]}")
    ic = next(i for i, s in enumerate(lp.body) if isinstance(s, ast.If) and any(isinstance(x, ast.Continue) for x in s.body))
    ij = next(i for i, s in enumerate(lp.body) if "json.loads" in ast.unparse(s))
    l6_open = [ast.unparse(n) for n in ast.walk(l6t) if isinstance(n, ast.Call) and callee(n) == "open" and "eval_sets" in ast.unparse(n)]
    print(f"  l6_check.py: open {l6_open} (text mode: every line, test rows included, is UTF-8-decoded into str by Python) | non-dev "
          f"continue at {ic}, json.loads at {ij}: continue first {ic < ij}")
    ok &= ic < ij
    th = open(os.path.join(repo, TESTS, "test_data_hashes.py"), encoding="utf-8").read()
    runs = re.findall(r'_run\(\[rep / "round5/l6_check\.py", "--eval-sets", ([^,]+),', th)
    print(f"  tests/test_data_hashes.py runs round5/l6_check.py with --eval-sets {runs} (the real file; pytest of t6 ran it: "
          f"test_byte_identical_to_reference_scripts)")
    return bool(ok)


run(main)
