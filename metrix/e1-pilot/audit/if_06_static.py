"""IF-6 (implementation stage B, report commit, task 1, static).  Questions:
  (1) after the change, does any path in src/ or tests/ (including the reference scripts under reports/ that the tests
      run) open eval_sets.jsonl in text mode, or decode / parse a row whose split is not dev?
  (2) does every TEST path (test_data.generate_test, leakage.run_test_part, evaluate.evaluate_model(split="test"))
      call verify_authorization before it reads any TEST content?
  (3) which re-checks does verify_authorization hold, and under which conditions does it refuse; does it, or anything
      it calls (transitively, inside the package), read any file other than PROTOCOL_FROZEN and the two committed
      records?
  (4) after the move of the content checks into record.gate0_record_problem / record.freeze_record_problem, do the
      TEST generator's conditions 2 and 3 still check the same things as before (HEAD version of test_data.py)?
Every source file is read as text and parsed with the standard `ast` module (never imported or run).  Interpretation
ENTRIES and module constants are read with ast.literal_eval (literals only).  The HEAD versions are read with
`git cat-file blob HEAD:<path>`.
  a. call sites in src/ (and reports/impl_b/dump_for_audit.py), TEST constants, file reads (as in ie_06), plus the
     callers of the new shared checks;
  b. data.build_general_dev (unchanged file; as in ie_06);
  c. test_data.main / check_preconditions / interpretation check (as in ie_06; updated for the shared checks);
  d. the guards of the three TEST paths with the new signatures; verify_authorization statement by statement: each
     refusal and its condition, in order; the four content-hash keys and their PROTOCOL_FROZEN table labels;
  e. transitive call closure of verify_authorization inside the package (module aliases resolved; fz./self. methods
     resolved to frozen.Frozen): every I/O-like leaf call, which must be exactly the read of PROTOCOL_FROZEN and the
     committed-record reads of record.committed_json; no TEST name anywhere in the closure;
  f. conditions 2 and 3 before (HEAD test_data.py) and after (record.py shared functions; test_data.py callers;
     leakage.verify_authorization caller): normalized sequence of checks compared;
  g. leakage.py load_data / {E} constants / main; template instantiation; evaluate_model callers (as in ie_06);
  h. tests/: every call of a TEST path with its arguments (new signatures);
  i. eval_sets.jsonl readers in src/, tests/ and the scripts the tests run; tests/test_data_hashes.py::_dev_rows_only
     (new: whole-file sha256 against the frozen value before the copy; counts against data.py's prefix count; the
     manifest copy from the frozen-commit DATA_MANIFEST);
  j. the Executor's listing (reports/impl_b/t12_fix3.txt lines 19-58, grep of open( / read_text( / read_bytes( in
     src/ and tests/) against my AST enumeration of those calls.
Data Auditor's own script (adapted from my ie_06_static.py); no Executor code imported, called or copied.
usage: python -I if_06_static.py <repo_root> [<repository whose eval_sets.jsonl is hashed in i; default repo_root>]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, re
from ia_common import frozen_json, git, file_sha, run

PKG = "metrix/e1-pilot/src/metrix_e1"
EXTRA = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py"]
TESTS = "metrix/e1-pilot/tests"
WATCH = ["generate_test", "build_test_qa", "params_for_test", "run_test_part", "TestAuthorization", "verify_authorization",
         "committed_record", "committed_json", "build_general_dev", "check_preconditions", "check_interpretations_ruled",
         "evaluate_model", "gate0_record_problem", "freeze_record_problem", "check_gate0_record", "check_selection_record",
         "pending"]
READERS = ("open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl", "load", "loads")
IO_LEAVES = {"open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl", "loads", "run", "Popen", "check_output",
             "call", "iterdir", "glob", "rglob", "listdir", "walk", "exists", "is_file", "is_dir", "stat", "scandir",
             "write_text", "write_bytes", "mkdir", "unlink", "from_file", "from_pretrained", "read_parquet", "read_table",
             "git_blob", "file_sha256"}
TEST_NAMES = {"test_qa", "general_test", "TEST_FILES", "SPLIT_FILES", "qa_file", "gen_file", "eval_sets", "eval_sets_path"}


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
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


def calls_in(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def first1(s):
    return ast.unparse(s).split("\n")[0][:130]


def raises_only(stmts, kind):
    return len(stmts) == 1 and isinstance(stmts[0], ast.Raise) and callee(stmts[0].exc) == kind


def main():
    repo = sys.argv[1]
    ev_root = sys.argv[2] if len(sys.argv) > 2 else repo     # where eval_sets.jsonl is hashed (the real repository; see if_07)
    ok = True
    files = sorted(os.path.join(PKG, x) for x in os.listdir(os.path.join(repo, PKG)) if x.endswith(".py")) + EXTRA
    trees = {}
    for rel in files:
        src = open(os.path.join(repo, rel), encoding="utf-8").read()
        trees[rel] = (src, ast.parse(src, rel))
    print("files parsed:", [os.path.basename(f) for f in files])
    T = lambda name: trees[f"{PKG}/{name}"][1]

    # ---------------------------------------------------------------------------------------------- a
    print("\n== a. call sites, TEST constants, file reads, TEST_FILES / SPLIT_FILES uses")
    sites = {w: [] for w in WATCH}
    consts, reads, tf_uses = [], [], []
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        b = os.path.basename(rel)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and callee(n) in sites:
                sites[callee(n)].append((b, n.lineno, enc_of[id(n)]))
            if isinstance(n, ast.Call) and callee(n) in READERS:
                reads.append((b, n.lineno, enc_of[id(n)], ast.unparse(n)[:90]))
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("TEST", "test", "test_qa.jsonl", "general_test.jsonl"):
                consts.append((b, n.lineno, enc_of[id(n)], n.value))
            if (isinstance(n, ast.Name) and n.id in ("TEST_FILES", "SPLIT_FILES")) or (isinstance(n, ast.Attribute) and n.attr in ("TEST_FILES", "SPLIT_FILES")):
                tf_uses.append((b, n.lineno, enc_of[id(n)]))
    expect = {"generate_test": [("test_data.py", "main")], "build_test_qa": [("test_data.py", "generate_test")],
              "params_for_test": [("test_data.py", "generate_test")], "run_test_part": [("test_data.py", "main")],
              "TestAuthorization": [("test_data.py", "check_preconditions")],
              "verify_authorization": [("evaluate.py", "evaluate_model"), ("leakage.py", "run_test_part"), ("test_data.py", "generate_test")],
              "committed_record": [("leakage.py", "verify_authorization"), ("stops.py", "st13_scan"), ("test_data.py", "_committed")],
              "committed_json": [("record.py", "committed_record")],
              "build_general_dev": [("data.py", "generate"), ("test_data.py", "generate_test")],
              "check_preconditions": [("test_data.py", "main")],
              "check_interpretations_ruled": [("test_data.py", "check_preconditions")],
              "evaluate_model": [],
              "gate0_record_problem": [("leakage.py", "verify_authorization"), ("test_data.py", "check_gate0_record")],
              "freeze_record_problem": [("leakage.py", "verify_authorization"), ("test_data.py", "check_selection_record")],
              "check_gate0_record": [("test_data.py", "check_preconditions")],
              "check_selection_record": [("test_data.py", "check_preconditions")],
              "pending": [("leakage.py", "verify_authorization"), ("test_data.py", "check_interpretations_ruled")]}
    for w in WATCH:
        got = sorted({(f, fn) for f, _, fn in sites[w]})
        same = got == sorted(expect[w])
        ok &= same
        print(f"  {w}: called from {got} | expected {sorted(expect[w])} | {same}")
    print("  constants naming TEST material (file, line, function, value):")
    for c in consts:
        print("   ", c)
    allowed = {("data.py", "<module>"), ("evaluate.py", "<module>"), ("evaluate.py", "evaluate_model"), ("contract.py", "_accounting"),
               ("gate.py", "compute_test_values"), ("gate.py", "judge_test"), ("test_data.py", "params_for_test"),
               ("test_data.py", "build_test_qa"), ("test_data.py", "generate_test"), ("leakage.py", "run_test_part")}
    stray = [c for c in consts if (c[0], c[2]) not in allowed]
    em_consts = [c for c in consts if (c[0], c[2]) == ("evaluate.py", "evaluate_model")]
    print(f"  in evaluate_model: {em_consts} (expected: the one comparison split == 'test' of the guard, checked in d)")
    print(f"  constants outside module-level name tuples, the evaluate_model guard, contract accounting (a count), gate T1-T3 "
          f"labels, the generator and run_test_part: {stray} | none: {not stray}")
    ok &= not stray and [c[3] for c in em_consts] == ["test"]
    print("  file reads in the package (file, line, function, call):")
    for r in reads:
        print("   ", r)
    ev_readers = [r for r in reads if "eval_sets" in r[3]]
    print(f"  calls that open eval_sets.jsonl: {ev_readers}")
    ok &= [(r[0], r[2]) for r in ev_readers] == [("data.py", "build_general_dev")]
    test_readers = [r for r in reads if any(x in r[3] for x in ("test_qa", "general_test", "TEST_FILES", "SPLIT_FILES", "qa_file", "gen_file"))]
    print(f"  read calls whose argument names a TEST file: {test_readers}")
    ok &= not test_readers
    print(f"  uses of TEST_FILES / SPLIT_FILES (file, line, function): {tf_uses}")
    tf_ok = True
    for b, ln, fn in tf_uses:
        if fn == "<module>":
            continue
        f_ = func(trees[f"{PKG}/{b}"][1], fn)
        stmts = [s for s in ast.walk(f_) if isinstance(s, (ast.Assign, ast.If, ast.Raise, ast.Expr, ast.Return)) and
                 any((isinstance(x, ast.Name) and x.id in ("TEST_FILES", "SPLIT_FILES")) or (isinstance(x, ast.Attribute) and x.attr in ("TEST_FILES", "SPLIT_FILES"))
                     for x in ast.walk(s)) and getattr(s, "lineno", -1) <= ln <= getattr(s, "end_lineno", -1)]
        st = min(stmts, key=lambda s: s.end_lineno - s.lineno) if stmts else None
        cs = sorted({callee(c) for c in calls_in(st)} - {None}) if st is not None else []
        good = (fn, b) == ("evaluate_model", "evaluate.py") or not (set(cs) & set(READERS))
        tf_ok &= good
        print(f"    {b}:{ln} in {fn}: {first1(st) if st is not None else '?'} | calls {cs} | no reader {good}")
    ok &= tf_ok

    # ---------------------------------------------------------------------------------------------- b
    print("\n== b. data.build_general_dev (data.py is not in the change)")
    dtree = T("data.py")
    rh = next(n for n in dtree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_ROW_HEAD" for t in n.targets))
    rh_arg = rh.value.args[0] if isinstance(rh.value, ast.Call) and rh.value.args else None
    is_bytes = isinstance(rh_arg, ast.Constant) and isinstance(rh_arg.value, bytes)
    pat_ok = is_bytes and len(re.findall(rb"\((?!\?)", rh_arg.value)) == 1 and rh_arg.value == rb'\{"domain": "[^"\\]*", "split": "([^"\\]*)", '
    print(f"  _ROW_HEAD = {ast.unparse(rh.value)} | bytes pattern anchored at the domain field, one group = the split value: {pat_ok}")
    ok &= pat_ok
    bg = func(dtree, "build_general_dev")
    opens = [n for n in ast.walk(bg) if isinstance(n, ast.Call) and callee(n) == "open"]
    binary = len(opens) == 1 and len(opens[0].args) == 2 and isinstance(opens[0].args[1], ast.Constant) and opens[0].args[1].value == "rb" and not opens[0].keywords
    print(f"  open calls: {[ast.unparse(o) for o in opens]} | exactly one open, mode 'rb', no encoding argument: {binary}")
    ok &= binary
    loop = next(n for n in ast.walk(bg) if isinstance(n, ast.For) and "enumerate(fh" in ast.unparse(n.iter))
    i_cont = next(i for i, s in enumerate(loop.body) if isinstance(s, ast.If) and any(isinstance(x, ast.Continue) for x in s.body))
    cont_test = ast.unparse(loop.body[i_cont].test)
    before = loop.body[:i_cont]
    line_uses = [ast.unparse(n) for s in before for n in ast.walk(s) if isinstance(n, ast.Call) and "line" in names_in(n)
                 and not any(isinstance(a, ast.Call) for a in n.args)]
    decodes_before = [ast.unparse(n) for s in before for n in ast.walk(s) if isinstance(n, ast.Call) and callee(n) in ("decode", "loads", "load")]
    after_dec = [(i, ast.unparse(n)) for i, s in enumerate(loop.body) for n in ast.walk(s)
                 if isinstance(n, ast.Call) and callee(n) in ("decode", "loads") and "line" in names_in(n)]
    want = [ast.unparse(s) for s in body_wo_doc(bg) if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "want" for t in s.targets)]
    b_ok = (cont_test == "m.group(1) != want" and line_uses == ["_ROW_HEAD.match(line)"] and
            decodes_before == ["m.group(1).decode('ascii', 'replace')"] and bool(after_dec) and all(i > i_cont for i, _ in after_dec)
            and want == ["want = p.general_dev_split.encode('ascii')"])
    print(f"  {want} | non-dev continue at loop statement {i_cont} ({cont_test!r}) | before it, calls taking the row {line_uses}, "
          f"decodes {decodes_before} | row decode / parse after it {after_dec} | only prefix match + split-field decode before the skip: {b_ok}")
    ok &= b_ok
    dev = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]["dev"]
    print(f"  frozen general_text.dev: {dev!r}")

    # ---------------------------------------------------------------------------------------------- c
    print("\n== c. test_data.main, check_preconditions, interpretation check")
    ttree = T("test_data.py")
    fns = {n.name: n for n in ttree.body if isinstance(n, ast.FunctionDef)}
    mf = fns["main"]
    try_i = next(i for i, s in enumerate(mf.body) if isinstance(s, ast.Try))
    t = mf.body[try_i]
    try_calls = [callee(n) for s in t.body for n in ast.walk(s) if isinstance(n, ast.Call)]
    exits = len(t.handlers) == 1 and ast.unparse(t.handlers[0].body[-1]) == "sys.exit(1)"
    after = [callee(n) for s in mf.body[try_i + 1:] for n in ast.walk(s) if isinstance(n, ast.Call)]
    print(f"  main: try body calls {try_calls} | handler ends with sys.exit(1): {exits} | calls after the try: {after}")
    ok &= try_calls == ["check_preconditions"] and exits and not t.finalbody and not t.orelse and after.index("generate_test") < after.index("run_test_part")
    rtp_call = [ast.unparse(n) for s in mf.body[try_i + 1:] for n in ast.walk(s) if isinstance(n, ast.Call) and callee(n) == "run_test_part"]
    print(f"  main calls {rtp_call} (the fz of check_preconditions)")
    ok &= rtp_call == ["LK.run_test_part(fz, LK.load_data(a.data), info['test_qa'], info['general_test'], auth)"]
    cp = body_wo_doc(fns["check_preconditions"])
    want_order = ["st12", "load", "check_data_dir", "check_gate0_record", "check_selection_record", "check_interpretations_ruled", "TestAuthorization"]
    got_order = [[callee(n) for n in ast.walk(s) if isinstance(n, ast.Call)][0] for s in cp]
    print(f"  check_preconditions, first call of each statement: {got_order} | == {want_order}: {got_order == want_order}")
    ok &= got_order == want_order and isinstance(cp[-1], ast.Return)
    cir = body_wo_doc(fns["check_interpretations_ruled"])
    ok &= len(cir) == 2 and ast.unparse(cir[0]) == "open_ids = INT.pending()" and isinstance(cir[1], ast.If) \
        and raises_only(cir[1].body, "PreconditionFailed")
    itree = T("interpretations.py")
    ent = next(n for n in itree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "ENTRIES" for x in n.targets))
    entries = ast.literal_eval(ent.value)
    PENDING = ast.literal_eval(next(n for n in itree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "PENDING" for x in n.targets)).value)
    pend_ids = [e["id"] for e in entries if e.get("status", PENDING) == PENDING]
    pdef = [ast.unparse(s) for s in body_wo_doc(func(itree, "pending"))]
    print(f"  check_interpretations_ruled: {[ast.unparse(s)[:80] for s in cir]} | interpretations.pending: {pdef} | ENTRIES {len(entries)} | pending now {len(pend_ids)}")
    ok &= pdef == ["return [e['id'] for e in ENTRIES if e.get('status', PENDING) == PENDING]"] and len(pend_ids) == len(entries) > 0
    for name in ("_committed", "check_gate0_record", "check_selection_record"):
        calls = sorted({callee(n) for n in ast.walk(fns[name]) if isinstance(n, ast.Call)} - {None})
        print(f"  {name} calls: {calls}")
        ok &= not ({"generate_test", "build_test_qa", "build_general_dev", "fill", "read_jsonl", "open", "verify_authorization"} & set(calls))

    # ---------------------------------------------------------------------------------------------- d
    print("\n== d. the guards of the three TEST paths; verify_authorization statement by statement")
    gtb = body_wo_doc(func(ttree, "generate_test"))
    g0 = ast.unparse(gtb[0])
    g_ok = g0 == "LK.verify_authorization(authorization, fz)"
    reads_gt = [(i, callee(c)) for i, s in enumerate(gtb) for c in calls_in(s)
                if callee(c) in ("params", "check_inputs", "load_qwen_tokenizer", "params_for_test", "read_jsonl", "build_test_qa", "build_general_dev")]
    print(f"  generate_test statement 0: {g0!r} -> verify first {g_ok} | readers / builders after it: {reads_gt} (all at statement > 0: "
          f"{all(i > 0 for i, _ in reads_gt)}) | the `fz` it verifies with is its own parameter, the one it then reads with")
    ok &= g_ok and bool(reads_gt) and all(i > 0 for i, _ in reads_gt)
    ltree = T("leakage.py")
    rtp_f = func(ltree, "run_test_part")
    rtp = body_wo_doc(rtp_f)
    r0 = ast.unparse(rtp[0])
    first_use = next(i for i, s in enumerate(rtp) if names_in(s) & {"test_qa", "general_test"})
    r_ok = r0 == "verify_authorization(authorization, fz, repo_root)"
    rargs = [a.arg for a in rtp_f.args.args]
    rdef = dict(zip(rargs[-len(rtp_f.args.defaults):], [ast.unparse(d) for d in rtp_f.args.defaults]))
    print(f"  run_test_part{tuple(rargs)} defaults {rdef} | statement 0: {r0!r} -> verify first {r_ok} | statement 1: {first1(rtp[1])!r} | "
          f"first statement using test_qa / general_test: {first_use} (after the verify: {first_use > 0})")
    ok &= r_ok and first_use > 0 and rdef == {"repo_root": "None"}
    etree = T("evaluate.py")
    sf = next(n for n in etree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "SPLIT_FILES" for x in n.targets))
    sfv = ast.literal_eval(sf.value)
    ok &= sorted(sfv) == ["dev", "test"]
    em = func(etree, "evaluate_model")
    emb = body_wo_doc(em)
    for i, s in enumerate(emb[:6]):
        print(f"    evaluate_model statement {i}: {first1(s)}")
    i_split = next((i for i, s in enumerate(emb) if isinstance(s, ast.If) and ast.unparse(s.test) == "split not in SPLIT_FILES" and isinstance(s.body[0], ast.Raise)), None)
    i_guard = next((i for i, s in enumerate(emb) if isinstance(s, ast.If) and ast.unparse(s.test) in ("split == 'test'", "'test' == split")), None)
    i_gpu = next((i for i, s in enumerate(emb) if any(callee(c) == "require_gpu" for c in calls_in(s))), None)
    touch = {"data", "qa_file", "gen_file", "qs", "facts", "cands"}
    i_data = next((i for i, s in enumerate(emb) if {n.id for n in ast.walk(s) if isinstance(n, ast.Name)} & touch), None)
    e_ok = False
    if i_guard is not None:
        gb = emb[i_guard].body
        for j, s in enumerate(gb):
            print(f"      guard statement {j}: {first1(s)}")
        j_mode = next((j for j, s in enumerate(gb) if isinstance(s, ast.If) and ast.unparse(s.test) == "not mode.formal" and raises_only(s.body, "ImplementationFail") and not s.orelse), None)
        j_none = next((j for j, s in enumerate(gb) if isinstance(s, ast.If) and ast.unparse(s.test) == "fz is None" and raises_only(s.body, "ImplementationFail") and not s.orelse), None)
        j_ver = next((j for j, s in enumerate(gb) if isinstance(s, ast.Expr) and ast.unparse(s) == "verify_authorization(test_authorization, fz)"), None)
        g_calls = sorted({callee(c) for c in calls_in(emb[i_guard])} - {None})
        print(f"  guard `if split == 'test'` at statement {i_guard}: formal-mode check at {j_mode}; `if fz is None: raise` at {j_none}; "
              f"verify_authorization(test_authorization, fz) at {j_ver}; calls in the guard {g_calls}; else branch {bool(emb[i_guard].orelse)}")
        print(f"  split check {i_split} < guard {i_guard} < require_gpu {i_gpu} < first statement touching data / qa_file / gen_file {i_data} "
              f"({first1(emb[i_data]) if i_data is not None else None!r})")
        e_ok = (None not in (i_split, i_gpu, i_data, j_mode, j_none, j_ver) and i_split < i_guard < i_gpu < i_data and j_mode < j_none < j_ver
                and set(g_calls) <= {"ImplementationFail", "verify_authorization"} and not emb[i_guard].orelse)
    eargs = [a.arg for a in em.args.args]
    edef = dict(zip(eargs[-len(em.args.defaults):], [ast.unparse(d) for d in em.args.defaults]))
    print(f"  evaluate_model parameters {eargs} | defaults split={edef.get('split')} test_authorization={edef.get('test_authorization')} "
          f"fz={edef.get('fz')} | repo_root no longer a parameter: {'repo_root' not in eargs}")
    print(f"  evaluate_model: for split 'test' the formal-mode check, the fz check and verify_authorization run before anything touches the data: {e_ok}")
    ok &= e_ok and edef.get("fz") == "None" and "repo_root" not in eargs
    # verify_authorization
    va = func(ltree, "verify_authorization")
    vargs = [a.arg for a in va.args.args]
    vdef = dict(zip(vargs[-len(va.args.defaults):], [ast.unparse(d) for d in va.args.defaults]))
    vab = body_wo_doc(va)
    print(f"  verify_authorization{tuple(vargs)} defaults {vdef}")
    for i, s in enumerate(vab):
        print(f"    statement {i}: {first1(s)}")
    txt = [ast.unparse(s) for s in vab]
    idx = lambda pred: next((i for i, s in enumerate(vab) if pred(s)), None)
    s_inst = idx(lambda s: isinstance(s, ast.If) and ast.unparse(s.test) == "not isinstance(authorization, TestAuthorization)" and raises_only(s.body, "ImplementationFail"))
    imports = sorted(ast.unparse(s) for s in vab if isinstance(s, ast.ImportFrom))
    s_root = idx(lambda s: ast.unparse(s) == "root = Path(repo_root) if repo_root is not None else fz.repo_root")
    s_pf = idx(lambda s: isinstance(s, ast.Try) and [ast.unparse(x) for x in s.body] == ["current = FZ.parse_protocol_frozen((root / FZ.PROTOCOL_FROZEN_REL).read_bytes()).commit"]
               and len(s.handlers) == 1 and ast.unparse(s.handlers[0].type) == "(OSError, ST12Error)" and raises_only(s.handlers[0].body, "ImplementationFail"))
    s_commit = idx(lambda s: isinstance(s, ast.If) and ast.unparse(s.test) == "not authorization.frozen_commit == current == fz.record.commit" and raises_only(s.body, "ImplementationFail"))
    s_recs = idx(lambda s: ast.unparse(s) == "recs = {}")
    s_loop = idx(lambda s: isinstance(s, ast.For))
    loop_v = vab[s_loop] if s_loop is not None else None
    it = ast.unparse(loop_v.iter) if loop_v is not None else ""
    two = ("R.GATE0_RECORD_REL, 'gate0', authorization.gate0_record_sha256" in it and "R.SELECTION_FREEZE_REL, 'selection_freeze', authorization.selection_record_sha256" in it)
    lsrc = ast.unparse(loop_v) if loop_v is not None else ""
    cr = "recs[kind], got = R.committed_record(root, rel, kind, authorization.frozen_commit)" in lsrc
    nc = any(isinstance(h, ast.ExceptHandler) and ast.unparse(h.type) == "R.NotCommitted" and raises_only(h.body, "ImplementationFail") for h in ast.walk(loop_v)) if loop_v else False
    gw = any(isinstance(s, ast.If) and ast.unparse(s.test) == "got != want" and raises_only(s.body, "ImplementationFail") for s in ast.walk(loop_v)) if loop_v else False
    s_content = idx(lambda s: ast.unparse(s) == "content = {k: fz.data_hash(k) for k in FZ.CONTENT_HASH_KEYS}")
    s_prob = idx(lambda s: isinstance(s, ast.For) and "R.gate0_record_problem(recs['gate0'])" in ast.unparse(s.iter)
                 and "R.freeze_record_problem(recs['selection_freeze'], C.load(fz), content, authorization.gate0_record_sha256)" in ast.unparse(s.iter)
                 and len(s.body) == 1 and isinstance(s.body[0], ast.If) and ast.unparse(s.body[0].test) == "problem" and raises_only(s.body[0].body, "ImplementationFail"))
    prob_iter = ast.unparse(vab[s_prob].iter) if s_prob is not None else ""
    prob_pairs = ("(R.GATE0_RECORD_REL, R.gate0_record_problem(recs['gate0']))" in prob_iter and
                  "(R.SELECTION_FREEZE_REL, R.freeze_record_problem(" in prob_iter)
    s_pend = idx(lambda s: ast.unparse(s) == "open_ids = INT.pending()")
    s_pend_chk = idx(lambda s: isinstance(s, ast.If) and ast.unparse(s.test) == "open_ids" and raises_only(s.body, "ImplementationFail"))
    order = [s_inst, s_root, s_pf, s_commit, s_recs, s_loop, s_content, s_prob, s_pend, s_pend_chk]
    v_ok = (None not in order and order == sorted(order) and order[0] == 0 and two and cr and nc and gw and prob_pairs and vdef == {"repo_root": "None"}
            and imports == ["from . import contract as C", "from . import interpretations as INT", "from . import record as R"]
            and len(vab) == len(order) + len(imports))
    print(f"  refusals of verify_authorization, in order (statement index):")
    print(f"    {s_inst}: authorization is not a TestAuthorization")
    print(f"    {s_pf}: PROTOCOL_FROZEN at <root>/metrix/e1-pilot/PROTOCOL_FROZEN cannot be read or parsed (OSError / ST12Error); root = repo_root or fz.repo_root ({s_root})")
    print(f"    {s_commit}: NOT (authorization.frozen_commit == the commit PROTOCOL_FROZEN names now == fz.record.commit)")
    print(f"    {s_loop}: for the Gate 0 record and the freeze record (both: {two}): committed_record(root, rel, kind, authorization.frozen_commit) raises "
          f"NotCommitted -> refuse ({cr and nc}); committed sha256 != the authorization's -> refuse ({gw})")
    print(f"    {s_prob}: record.gate0_record_problem(committed Gate 0 record) or record.freeze_record_problem(committed freeze record, C.load(fz), "
          f"content = frozen data_hash of {s_content}, authorization.gate0_record_sha256) not None -> refuse ({prob_pairs})")
    print(f"    {s_pend_chk}: interpretations.pending() ({s_pend}) not empty -> refuse")
    print(f"    imports {imports} | statements accounted for {len(order) + len(imports)} of {len(vab)} | order as listed: {v_ok}")
    ok &= v_ok
    all_raises = [r for r in ast.walk(va) if isinstance(r, ast.Raise)]
    raise_kinds = sorted({callee(r.exc) for r in all_raises})
    vnames = names_in(va) & TEST_NAMES
    print(f"  raises {len(all_raises)} (kinds {raise_kinds}) | TEST names used {sorted(vnames)}")
    ok &= raise_kinds == ["ImplementationFail"] and len(all_raises) == 7 and not vnames
    ftree = T("frozen.py")
    fassign = {ast.unparse(n.targets[0]): n.value for n in ftree.body if isinstance(n, ast.Assign) and len(n.targets) == 1}
    chk = ast.literal_eval(fassign["CONTENT_HASH_KEYS"])
    dtr = ast.literal_eval(fassign["DATA_TABLE_ROWS"])
    labels = {k: [lab for lab, (key, _) in dtr.items() if key == k] for k in chk}
    want_labels = {"facts": ["fact(160 条)"], "train_S": ["`train_S.jsonl`"], "candidates": ["`candidates.json`"], "anchor_texts": ["锚文本(512 篇解码文本)"]}
    print(f"  frozen.CONTENT_HASH_KEYS {chk} | their PROTOCOL_FROZEN table labels (DATA_TABLE_ROWS) {labels} | == the protocol's rows for fact (2.2), "
          f"train_S (2.6), candidates (2.5), anchor texts: {labels == want_labels} (values checked by if_01_content_hashes.py)")
    ok &= labels == want_labels
    pfr = [ast.unparse(n) for n in ftree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) in ("PILOT_REL", "PROTOCOL_FROZEN_REL")]
    print(f"  frozen: {pfr}")
    ok &= pfr == ["PILOT_REL = 'metrix/e1-pilot'", "PROTOCOL_FROZEN_REL = PILOT_REL + '/PROTOCOL_FROZEN'"]
    rtree = T("record.py")
    crf = func(rtree, "committed_record")
    crb = [ast.unparse(s).split("\n")[0] for s in body_wo_doc(crf)]
    print(f"  record.committed_record: {crb}")
    ok &= any("rec.get('kind') != kind or rec.get('mode') != 'formal' or rec.get('label') is not None" in s for s in crb) and \
        any("rec.get('frozen_commit') != frozen_commit" in s for s in crb)
    cj_calls = [ast.unparse(n)[:110] for n in ast.walk(func(rtree, "committed_json")) if isinstance(n, ast.Call)]
    print(f"  record.committed_json calls: {cj_calls}")
    ok &= any("cat-file" in c and "HEAD:%s" in c for c in cj_calls) and not any("open(" in c for c in cj_calls)
    sc = func(T("stops.py"), "st13_scan")
    sc_reads = [c for c in calls_in(sc) if callee(c) in READERS + ("read",)]
    print(f"  stops.st13_scan readers {[ast.unparse(c) for c in sc_reads]} (only .exists() on TEST names)")
    ok &= not sc_reads and any(callee(c) == "exists" for c in calls_in(sc))

    # ---------------------------------------------------------------------------------------------- e
    print("\n== e. transitive call closure of verify_authorization inside the package (I/O-like leaf calls)")
    mods = {os.path.basename(r)[:-3]: tr for r, (_, tr) in trees.items() if r.startswith(PKG)}
    defs = {}
    for m, tr in mods.items():
        for n in tr.body:
            if isinstance(n, ast.FunctionDef):
                defs[(m, n.name)] = n
            if isinstance(n, ast.ClassDef):
                for x in n.body:
                    if isinstance(x, ast.FunctionDef):
                        defs[(m, f"{n.name}.{x.name}")] = x

    def aliases(m, f):
        al, names = {}, {}
        for n in list(mods[m].body) + list(ast.walk(f)):
            if isinstance(n, ast.ImportFrom) and n.level == 1:
                for a in n.names:
                    if n.module is None:
                        al[a.asname or a.name] = a.name
                    else:
                        names[a.asname or a.name] = (n.module, a.name)
        return al, names

    seen, todo, leaves, unresolved = set(), [("leakage", "verify_authorization")], [], set()
    while todo:
        key = todo.pop()
        if key in seen or key not in defs:
            if key not in defs:
                unresolved.add(key)
            continue
        seen.add(key)
        m, fname = key
        f = defs[key]
        al, names = aliases(m, f)
        cls = fname.split(".")[0] if "." in fname else None
        for c in calls_in(f):
            fn_ = c.func
            tgt = None
            if isinstance(fn_, ast.Name):
                if fn_.id in names:
                    tgt = names[fn_.id]
                elif (m, fn_.id) in defs:
                    tgt = (m, fn_.id)
                elif any(k == (m, f"{fn_.id}.__init__") for k in defs):
                    tgt = (m, f"{fn_.id}.__init__")
            elif isinstance(fn_, ast.Attribute) and isinstance(fn_.value, ast.Name):
                base = fn_.value.id
                if base in al:
                    tgt = (al[base], fn_.attr)
                elif base == "fz" and ("frozen", f"Frozen.{fn_.attr}") in defs:
                    tgt = ("frozen", f"Frozen.{fn_.attr}")
                elif base == "self" and cls and (m, f"{cls}.{fn_.attr}") in defs:
                    tgt = (m, f"{cls}.{fn_.attr}")
            if tgt is not None and tgt in defs:
                todo.append(tgt)
            elif tgt is not None:
                unresolved.add(tgt)
            else:
                if callee(c) in IO_LEAVES or (callee(c) == "load" and ast.unparse(fn_).startswith("json")):
                    leaves.append((m, fname, ast.unparse(c)[:150]))
    print(f"  functions in the closure ({len(seen)}): {sorted(f'{m}.{n}' for m, n in seen)}")
    print(f"  resolved names without a definition (constructors / classes): {sorted(unresolved)}")
    for x in leaves:
        print(f"  I/O-like leaf: {x[0]}.{x[1]}: {x[2]}")
    exp_leaves = {("leakage", "verify_authorization", "(root / FZ.PROTOCOL_FROZEN_REL).read_bytes()"),
                  ("record", "committed_json", "wt.is_file()"), ("record", "committed_json", "wt.read_bytes()"),
                  ("record", "committed_json", "json.loads(r.stdout)")}
    got_leaves = {x for x in leaves if not x[2].startswith("subprocess.run(")}
    git_runs = [x for x in leaves if x[2].startswith("subprocess.run(")]
    git_ok = [x[:2] for x in git_runs] == [("record", "committed_json")] and "'cat-file', 'blob', 'HEAD:%s' % rel" in git_runs[0][2]
    print(f"  leaves == PROTOCOL_FROZEN read + committed_json reads: {got_leaves == exp_leaves} | the only subprocess is committed_json's "
          f"git cat-file blob HEAD:<rel>: {git_ok}")
    ok &= got_leaves == exp_leaves and git_ok
    closure_test = sorted({(m, n) for m, n in seen if names_in(defs[(m, n)]) & TEST_NAMES})
    print(f"  functions in the closure that use a TEST name {sorted(TEST_NAMES)}: {closure_test}")
    ok &= not closure_test
    need = {("record", "gate0_record_problem"), ("record", "freeze_record_problem"), ("train", "training_plan"), ("contract", "load"),
            ("interpretations", "pending"), ("frozen", "parse_protocol_frozen"), ("frozen", "Frozen.data_hash"), ("record", "committed_record")}
    print(f"  the closure contains the shared checks, training_plan, contract.load, pending, parse_protocol_frozen, Frozen.data_hash, committed_record: {need <= seen}")
    ok &= need <= seen

    # ---------------------------------------------------------------------------------------------- f
    print("\n== f. conditions 2 and 3 before (HEAD test_data.py) and after (record.py shared functions)")
    old_src = git(repo, "cat-file", "blob", f"HEAD:{PKG}/test_data.py").stdout.decode("utf-8")
    old = ast.parse(old_src)
    old_g, old_s = func(old, "check_gate0_record"), func(old, "check_selection_record")
    new_g, new_s = func(rtree, "gate0_record_problem"), func(rtree, "freeze_record_problem")
    old_imports = [ast.unparse(n) for n in old.body if isinstance(n, ast.ImportFrom) and any(a.name == "train" for a in n.names)]

    def norm(fn, old_style):
        out = []
        for s in body_wo_doc(fn):
            u = ast.unparse(s)
            if isinstance(s, ast.ImportFrom):
                out.append(("import", u))
            elif isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) in ("rel", "(rec, sha)", "hexes"):
                out.append(("setup", u))
            elif isinstance(s, ast.Assign):
                u = u.replace("T.training_plan(", "training_plan(").replace("hexes.fullmatch(", "FZ.HEX64.fullmatch(")
                out.append(("assign", u))
            elif isinstance(s, ast.Try):
                b = [ast.unparse(x).replace("T.training_plan(", "training_plan(") for x in s.body]
                h = [(ast.unparse(x.type), "FAIL" if raises_only(x.body, "PreconditionFailed") or (len(x.body) == 1 and isinstance(x.body[0], ast.Return)) else "?")
                     for x in s.handlers]
                out.append(("try", tuple(b), tuple(h)))
            elif isinstance(s, ast.If):
                fail = raises_only(s.body, "PreconditionFailed") if old_style else (len(s.body) == 1 and isinstance(s.body[0], ast.Return)
                                                                                     and not (isinstance(s.body[0].value, ast.Constant) and s.body[0].value.value is None))
                out.append(("if", ast.unparse(s.test), "FAIL" if fail else "?", bool(s.orelse)))
            elif isinstance(s, ast.Return):
                v = s.value
                if isinstance(v, ast.IfExp) and isinstance(v.body, ast.Constant) and v.body.value is None:
                    out.append(("if", f"not ({ast.unparse(v.test)})", "FAIL", False))
                elif isinstance(v, ast.Constant) and v.value is None:
                    out.append(("end", "ok"))
                elif ast.unparse(v) == "sha":
                    out.append(("end", "ok"))
                else:
                    out.append(("return?", ast.unparse(v)))
            else:
                out.append(("other", u))
        return out
    og, ng = norm(old_g, True), norm(new_g, False)
    os_, ns = norm(old_s, True), norm(new_s, False)
    for label, a, b in (("condition 2: HEAD check_gate0_record", og, None), ("            record.gate0_record_problem", ng, None),
                        ("condition 3: HEAD check_selection_record", os_, None), ("            record.freeze_record_problem", ns, None)):
        print(f"  {label}:")
        for x in a:
            print(f"      {x}")
    strip = lambda L: [x for x in L if x[0] not in ("setup", "import", "end")]
    g_same = [("if", "status != 'PASS'", "FAIL", False)] == [x for x in strip(og) if x[0] == "if"] and \
        [("if", "not (status == 'PASS')", "FAIL", False)] == [x for x in strip(ng) if x[0] == "if"] and \
        [x for x in strip(og) if x[0] == "assign"] == [x for x in strip(ng) if x[0] == "assign"]
    s_same = strip(os_) == strip(ns)
    hexes_old = [ast.unparse(s.value) for s in ast.walk(old_s) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "hexes"]
    hex_new = ast.unparse(fassign["HEX64"])
    tp_new = [ast.unparse(s) for s in body_wo_doc(new_s) if isinstance(s, ast.ImportFrom)]
    print(f"  condition 2: same assignment, and the failing condition `status != 'PASS'` == `not (status == 'PASS')`: {g_same}")
    print(f"  condition 3: same sequence of assignments and checks after renaming T.training_plan -> training_plan, hexes -> FZ.HEX64: {s_same}")
    print(f"    old hexes = {hexes_old} | frozen.HEX64 = {hex_new} | same pattern: {hexes_old == [hex_new]} | old training_plan from {old_imports} "
          f"(T = train) | new from {tp_new}")
    ok &= g_same and s_same and hexes_old == [hex_new] and old_imports == ["from . import train as T"] and tp_new == ["from .train import training_plan"]
    ng_c = body_wo_doc(fns["check_gate0_record"])
    ns_c = body_wo_doc(fns["check_selection_record"])
    og_head = [ast.unparse(s) for s in body_wo_doc(old_g)][0]
    os_head = [ast.unparse(s) for s in body_wo_doc(old_s)][:2]
    wire = ([ast.unparse(s) for s in ng_c][:2] == [og_head, "problem = R.gate0_record_problem(rec)"]
            and isinstance(ng_c[2], ast.If) and raises_only(ng_c[2].body, "PreconditionFailed") and ast.unparse(ng_c[3]) == "return sha"
            and os_head == ["rel = R.SELECTION_FREEZE_REL", "rec, sha = _committed(repo_root, rel, 'selection_freeze', fz)"]
            and [ast.unparse(s) for s in ns_c][:2] == ["rec, sha = _committed(repo_root, R.SELECTION_FREEZE_REL, 'selection_freeze', fz)",
                                                       "problem = R.freeze_record_problem(rec, contract, content_hashes, gate0_sha)"]
            and isinstance(ns_c[2], ast.If) and raises_only(ns_c[2].body, "PreconditionFailed") and ast.unparse(ns_c[3]) == "return sha")
    sig_same = [a.arg for a in fns["check_selection_record"].args.args] == [a.arg for a in old_s.args.args] and \
        [a.arg for a in fns["check_gate0_record"].args.args] == [a.arg for a in old_g.args.args]
    old_cp = [ast.unparse(s) for s in body_wo_doc(func(old, "check_preconditions"))]
    new_cp = [ast.unparse(s) for s in body_wo_doc(fns["check_preconditions"])]
    print(f"  test_data callers: same committed record read (_committed), shared function called with the same arguments, any problem -> "
          f"PreconditionFailed, return sha: {wire} | signatures unchanged: {sig_same} | check_preconditions unchanged: {old_cp == new_cp}")
    ok &= wire and sig_same and old_cp == new_cp
    print("  verify_authorization calls the same two functions with: the record from committed_record(root, rel, kind, authorization.frozen_commit) "
          "(== fz.record.commit, statement checked above), contract C.load(fz) (the generator: C.load(fz)), content = frozen data_hash of the four "
          "keys (the generator: check_data_dir, which returns those keys only when each equals data_hash), gate0 sha = the authorization's (checked "
          f"== the committed Gate 0 record's sha256 in the loop): {prob_pairs and s_content is not None}")

    # ---------------------------------------------------------------------------------------------- g
    print("\n== g. leakage.py load_data / main, template instantiation, evaluate_model callers")
    ld = func(ltree, "load_data")
    stems = [ast.literal_eval(e) for n in ast.walk(ld) if isinstance(n, ast.Tuple) for e in n.elts if isinstance(e, ast.Constant)]
    subst = [n.lineno for n in ast.walk(ltree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("{E}", "{A}")]
    lmc = [callee(n) for n in ast.walk(func(ltree, "main")) if isinstance(n, ast.Call)]
    print(f"  load_data file stems: {stems} | '{{E}}' / '{{A}}' constants: {subst} | leakage.main calls run_test_part: {'run_test_part' in lmc} | run_gate0: {'run_gate0' in lmc}")
    ok &= bool(stems) and not any("test" in x for x in stems) and not subst and "run_test_part" not in lmc and "run_gate0" in lmc
    inst = set()
    for rel, (src, tree) in trees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and (callee(n) == "fill" or (callee(n) == "replace" and n.args and isinstance(n.args[0], ast.Constant)
                                                                    and n.args[0].value == "{E}" and ast.unparse(n.args[1]) != "'<ENTITY>'")):
                inst.add((os.path.basename(rel), enc_of[id(n)]))
    test_inst = sorted(fn for f, fn in inst if f == "test_data.py")
    other = sorted((f, fn) for f, fn in inst if f != "test_data.py")
    expected_other = [("data.py", "build_dev_qa"), ("data.py", "build_train_F"), ("data.py", "build_train_S"), ("data.py", "build_train_Y"),
                      ("data.py", "fill"), ("evaluate.py", "statement_prefix")]
    print(f"  template instantiation in test_data.py: {test_inst} | elsewhere: {other} | elsewhere == DEV / TRAIN / Y builders, fill, prefix(f): {other == expected_other}")
    ok &= test_inst == ["build_test_qa"] and other == expected_other
    print(f"  evaluate_model callers in src/ and reports/impl_b/dump_for_audit.py: {sites['evaluate_model']}")

    # ---------------------------------------------------------------------------------------------- h
    print("\n== h. tests/: every call of a TEST path")
    g0rel, selrel = "metrix/e1-pilot/results/gate0_record.json", "metrix/e1-pilot/results/selection_freeze_record.json"
    in_head = {r: git(repo, "cat-file", "-e", f"HEAD:{r}", check=False).returncode == 0 for r in (g0rel, selrel)}
    print(f"  records committed at HEAD of the real repository: {in_head} (verify_authorization against the real repository refuses)")
    ok &= not any(in_head.values())
    tdir = os.path.join(repo, TESTS)
    ttrees = {fn_: ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read()) for fn_ in sorted(os.listdir(tdir)) if fn_.endswith(".py")}
    gen_auth_ok = {"None", "LK.TestAuthorization(None, None, None)", "LK.TestAuthorization(fz.record.commit, 'a' * 64, 'b' * 64)"}
    for fn_, tree in ttrees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call) and callee(n) in ("generate_test", "build_test_qa", "run_test_part", "TestAuthorization", "evaluate_model",
                                                              "params_for_test", "check_preconditions", "verify_authorization")):
                continue
            c, s, encf = callee(n), ast.unparse(n), enc_of[id(n)]
            verdict = "listed"
            if c == "generate_test":
                good = ast.unparse(n.args[0]) == "fz" and ast.unparse(n.args[1]) in gen_auth_ok
                verdict = (f"fz + None / TestAuthorization(None, None, None) (frozen-commit refusal) / TestAuthorization(fz.record.commit, 'a'*64, "
                           f"'b'*64) (records not committed in the real repository -> refusal): {good}")
                ok &= good
            elif c == "run_test_part":
                good = ast.unparse(n.args[0]) == "fz" and ast.unparse(n.args[2]) == "[]" and ast.unparse(n.args[3]) == "[]"
                verdict = f"fz first; test_qa and general_test are [] (no TEST content): {good}"
                ok &= good
            elif c in ("build_test_qa", "params_for_test"):
                verdict = "TEST builder called from a test: False"
                ok = False
            elif c == "evaluate_model":
                sp = [ast.unparse(k.value) for k in n.keywords if k.arg == "split"]
                fzk = [ast.unparse(k.value) for k in n.keywords if k.arg == "fz"]
                rr = [k.arg for k in n.keywords if k.arg == "repo_root"]
                mode_arg = ast.unparse(n.args[5]) if len(n.args) > 5 else None
                if not sp:
                    good = len(n.args) <= 7
                    verdict = f"split default 'dev': {good}"
                else:
                    good = sp == ["'test'"] and fzk == ["fz"] and not rr and ast.unparse(n.args[2]) == "data_rows"
                    verdict = (f"split 'test', mode {mode_arg}, fz=fz (records not committed -> refused; a non-formal mode is refused before that) "
                               f"and data_rows (generated non-TEST files only): {good}")
                ok &= good
            elif c in ("check_preconditions", "verify_authorization"):
                fdef = func(tree, encf)
                other_calls = sorted({callee(x) for x in calls_in(fdef)} & {"generate_test", "run_test_part", "evaluate_model", "build_test_qa", "build_general_dev", "params_for_test"})
                verdict = f"the test function calls no TEST path: {not other_calls} {other_calls}"
                ok &= not other_calls
            print(f"  {fn_}:{n.lineno} in {encf}: {s[:150]}")
            print(f"      -> {verdict}")
    gfx = func(ttrees["conftest.py"], "generated")
    ok &= any("D.generate(fz, inputs_dir)" in ast.unparse(s) for s in body_wo_doc(gfx))
    fzfx = [ast.unparse(s) for s in body_wo_doc(func(ttrees["conftest.py"], "fz"))]
    print(f"  conftest.fz: {fzfx} | conftest.generated calls D.generate(fz, inputs_dir)")
    ok &= fzfx == ["return FZ.load()"]

    # ---------------------------------------------------------------------------------------------- i
    print("\n== i. eval_sets.jsonl readers in src/, tests/ and the scripts the tests run")
    RD = ("open", "read_text", "read_bytes", "load", "loads", "read_jsonl", "parse_jsonl", "copyfile", "copy", "copy2", "copytree",
          "flip", "check_file", "file_sha256", "check_inputs", "build_general_dev", "Popen", "run", "_run", "_cli", "read")
    found = []
    for root in (os.path.join(repo, "metrix/e1-pilot/src"), tdir):
        for r, ds, fs in os.walk(root):
            if "__pycache__" in r:
                continue
            for f in sorted(fs):
                if not f.endswith(".py"):
                    continue
                p = os.path.join(r, f)
                tree = ast.parse(open(p, encoding="utf-8").read())
                enc_of = enclosing(tree)
                tainted = {}
                for n in ast.walk(tree):
                    if isinstance(n, ast.Assign) and re.search(r"eval_sets|general_source|eval-sets", ast.unparse(n.value)):
                        for tg in n.targets:
                            for x in ast.walk(tg):
                                if isinstance(x, ast.Name):
                                    tainted.setdefault(enc_of[id(n)], set()).add(x.id)
                for n in ast.walk(tree):
                    if isinstance(n, ast.Call) and callee(n) in RD:
                        argtxt = " ".join(ast.unparse(a) for a in n.args) + " " + " ".join(ast.unparse(k.value) for k in n.keywords)
                        fn_ = enc_of[id(n)]
                        hit = re.search(r"eval_sets|general_source|eval-sets", argtxt) or \
                            any(isinstance(x, ast.Name) and x.id in tainted.get(fn_, set()) for a in list(n.args) + [k.value for k in n.keywords] for x in ast.walk(a))
                        if hit:
                            found.append((os.path.relpath(p, repo), n.lineno, fn_, ast.unparse(n)[:160]))
    for x in found:
        print(f"   {x[0]}:{x[1]} in {x[2]}: {x[3]}")
    expected_hits = {
        ("metrix/e1-pilot/src/metrix_e1/data.py", "build_general_dev", "open(eval_sets_path, 'rb')"),
        ("metrix/e1-pilot/src/metrix_e1/data.py", "generate", "build_general_dev(p, tok, paths['eval_sets'], paths['parcae_tokenizer'])"),
        ("metrix/e1-pilot/src/metrix_e1/test_data.py", "generate_test", "D.build_general_dev(pt, tok, paths['eval_sets'], paths['parcae_tokenizer'])"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "FZ.file_sha256(src)"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "open(src, 'rb')"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "open(out, 'wb')"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "FZ.file_sha256(out)"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "test_byte_identical_to_reference_scripts",
         "_run([rep / 'round5/l6_check.py', '--eval-sets', dev_rows, '--parcae-tokenizer', inputs_dir / 'parcae_tokenizer/tokenizer.json', '--manifest', manifest, '--toke"),
        ("metrix/e1-pilot/tests/test_st12.py", "mini_repo", "shutil.copyfile(fz.repo_root / ev, root / ev)"),
        ("metrix/e1-pilot/tests/test_st12.py", "test_eval_sets_one_byte", "flip(root / p.general_source)"),
    }
    got_hits = {(a, c, d) for a, _, c, d in found}
    extra = sorted(got_hits - expected_hits)
    print(f"  hits outside the expected set: {extra} | expected hits all present: {expected_hits <= got_hits}")
    ok &= not extra and expected_hits <= got_hits
    fs_open = [ast.unparse(c) for c in calls_in(func(ftree, "file_sha256")) if callee(c) == "open"]
    print(f"  frozen.file_sha256 opens {fs_open} (binary whole-file hash)")
    ok &= fs_open == ["open(path, 'rb')"]
    st12 = ttrees["test_st12.py"]
    fl_calls = sorted({callee(c) for c in calls_in(func(st12, "flip"))} - {None})
    tev_calls = sorted({callee(c) for c in calls_in(func(st12, "test_eval_sets_one_byte"))} - {None})
    print(f"  tests/test_st12.py flip calls {fl_calls} | test_eval_sets_one_byte calls {tev_calls} (unchanged file; raw bytes only, whole-file hash)")
    ok &= set(fl_calls) <= {"bytearray", "read_bytes", "len", "write_bytes", "bytes"} and tev_calls == sorted({"load", "params", "check_inputs", "flip", "raises"})
    th = ttrees["test_data_hashes.py"]
    rs = next(n for n in th.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "_ROW_SPLIT")
    rs_arg = rs.value.args[0] if isinstance(rs.value, ast.Call) and rs.value.args else None
    rs_ok = callee(rs.value) == "compile" and isinstance(rs_arg, ast.Constant) and rs_arg.value == rb'\{"domain": "[^"\\]*", "split": "([^"\\]*)", '
    print(f"  _ROW_SPLIT = {ast.unparse(rs.value)} | bytes pattern anchored at the domain field, one group = the split value: {rs_ok}")
    ok &= rs_ok
    dr = func(th, "_dev_rows_only")
    print(f"  _dev_rows_only parameters {[a.arg for a in dr.args.args]}")
    drb = body_wo_doc(dr)
    for i, s in enumerate(drb):
        print(f"    statement {i}: {first1(s)}")
    gt = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]
    i_src = next((i for i, s in enumerate(drb) if ast.unparse(s) == "src = fz.repo_root / D.params(fz).general_source"), None)
    i_sha = next((i for i, s in enumerate(drb) if isinstance(s, ast.Assert) and ast.unparse(s.test) == "FZ.file_sha256(src) == fz.data_hash('eval_sets')"), None)
    i_with = next((i for i, s in enumerate(drb) if isinstance(s, ast.With)), None)
    par = func(dtree, "params")
    gs = [ast.unparse(k) for c in calls_in(par) for k in c.keywords if k.arg == "general_source"]
    gt_assign = [ast.unparse(s) for s in ast.walk(par) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "gt"]
    par_reads = sorted({callee(c) for c in calls_in(par)} & (set(READERS) | IO_LEAVES))
    ev_label = [lab for lab, (key, _) in dtr.items() if key == "eval_sets"]
    pf_text = open(os.path.join(repo, "metrix/e1-pilot/PROTOCOL_FROZEN"), encoding="utf-8").read()
    pf_row = [c.split("|")[2].strip().strip("`") for c in pf_text.split("\n") if c.startswith("| `eval_sets.jsonl` |")]
    real_sha = file_sha(os.path.join(ev_root, gt["source_file"]))
    src_ok = (i_src is not None and i_sha is not None and i_with is not None and i_src < i_sha < i_with and gs == ["general_source=gt['source_file']"]
              and gt_assign == ["gt = dm['general_text']"] and not par_reads and ev_label == ["`eval_sets.jsonl`"] and pf_row == [real_sha])
    print(f"  src at statement {i_src} (data.params: {gs}, {gt_assign}, I/O calls in params {par_reads}; frozen source_file {gt['source_file']!r}) | "
          f"whole-file sha256 assert at {i_sha}, before the open (with) at {i_with} | data_hash('eval_sets') = table row {ev_label} = {pf_row} | "
          f"whole-file sha256 of the real file (computed here) {real_sha} | all as required: {src_ok}")
    ok &= src_ok
    with_s = drb[i_with] if i_with is not None else None
    open_txt = [ast.unparse(o) for o in ast.walk(dr) if isinstance(o, ast.Call) and callee(o) == "open"]
    ok &= open_txt == ["open(src, 'rb')", "open(out, 'wb')"]
    loop = next(n for n in ast.walk(dr) if isinstance(n, ast.For))
    lb = loop.body
    line_calls = [(i, ast.unparse(c)) for i, s in enumerate(lb) for c in calls_in(s) if "line" in {x.id for x in ast.walk(c) if isinstance(x, ast.Name)}
                  and not any(isinstance(a, ast.Call) for a in c.args)]
    dec = [ast.unparse(c) for c in calls_in(dr) if callee(c) in ("decode", "loads", "load", "read_text") and "line" in {x.id for x in ast.walk(c) if isinstance(x, ast.Name)}]
    i_if = next((i for i, s in enumerate(lb) if isinstance(s, ast.If) and ast.unparse(s.test) == "m.group(1) == b'dev'"), None)
    write_in_dev = i_if is not None and [ast.unparse(s) for s in lb[i_if].body][:1] == ["fo.write(line)"] and \
        not any(callee(c) == "write" for s in lb[i_if].orelse for c in calls_in(s))
    writes = [ast.unparse(c) for c in calls_in(dr) if callee(c) in ("write", "write_text", "write_bytes", "writelines")]
    loop_ok = [c for _, c in line_calls] == ["_ROW_SPLIT.match(line)", "fo.write(line)"] and line_calls[0][0] == 0 and not dec
    w_ok = sorted(writes) == sorted(["fo.write(line)", "mpath.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')"])
    print(f"  open calls {open_txt} | in the row loop: {line_calls} | decode / json of a row: {dec} | fo.write(line) only under "
          f"`if m.group(1) == b'dev'`: {write_in_dev} | writes {writes} | only matched, then written if dev: {loop_ok and write_in_dev and w_ok}")
    ok &= loop_ok and write_in_dev and w_ok and with_s is not None
    asserts = [ast.unparse(s) for s in ast.walk(dr) if isinstance(s, ast.Assert)]
    bys = [ast.unparse(s) for s in drb if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "by_split"]
    i_cnt = next((i for i, s in enumerate(drb) if isinstance(s, ast.Assert) and ast.unparse(s.test).startswith("n == ")), None)
    gen_info = [ast.unparse(k) + ": " + ast.unparse(v) for s in ast.walk(func(dtree, "generate")) if isinstance(s, ast.Dict)
                for k, v in zip(s.keys, s.values) if isinstance(k, ast.Constant) and k.value == "general_dev"]
    gen_stats = [ast.unparse(s) for s in ast.walk(func(dtree, "generate")) if isinstance(s, ast.Assign) and "general_stats" in ast.unparse(s.targets[0])]
    rbs = [ast.unparse(r.value)[:120] for r in ast.walk(bg) if isinstance(r, ast.Return)]
    cnt_ok = ("assert n == {'dev': by_split['dev'], 'other': sum((v for k, v in by_split.items() if k != 'dev'))}" in asserts
              and "assert m is not None" in asserts and bys == ["by_split = generated['info']['general_dev']['rows_by_split']"]
              and gen_info == ["'general_dev': general_stats"] and len(gen_stats) == 1 and "build_general_dev(" in gen_stats[0]
              and any("'rows_by_split': dict(sorted(rows_by_split.items()))" in r for r in rbs) and i_cnt is not None and i_cnt > i_with)
    print(f"  asserts {asserts}")
    print(f"  {bys} | data.generate info {gen_info} from {gen_stats} | build_general_dev returns {rbs} (rows_by_split counted from the "
          f"row prefix, section b) | count assert at statement {i_cnt} (after the copy): {cnt_ok}")
    ok &= cnt_ok
    msub = [ast.unparse(s) for s in ast.walk(dr) if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Subscript)]
    mload = [ast.unparse(s) for s in drb if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "manifest"]
    lf = func(ftree, "load")
    dm_assign = [ast.unparse(s) for s in ast.walk(lf) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "dm"]
    ret_dm = [ast.unparse(r.value) for r in ast.walk(lf) if isinstance(r, ast.Return)]
    m_ok = (msub == ["manifest['general_text']['source_file_sha256'] = FZ.file_sha256(out)"] and mload == ["manifest = copy.deepcopy(fz.data_manifest)"]
            and dm_assign == ["dm = json.loads(blobs[DATA_MANIFEST_REL])"] and any("data_manifest=dm" in r for r in ret_dm))
    wt_dm = open(os.path.join(repo, "metrix/e1-pilot/DATA_MANIFEST.json"), "rb").read()
    print(f"  manifest copy: {mload} (fz.data_manifest: load() {dm_assign}, the frozen-commit blob) | subscript assignments {msub} | "
          f"only general_text.source_file_sha256 replaced: {m_ok} | working-tree DATA_MANIFEST.json == freeze-commit blob (what the old code read): "
          f"{wt_dm == git(repo, 'cat-file', 'blob', '87a244db28a901f9e89282b50df76778ab5c2887:metrix/e1-pilot/DATA_MANIFEST.json').stdout}")
    ok &= m_ok
    tb = func(th, "test_byte_identical_to_reference_scripts")
    tbb = body_wo_doc(tb)
    runs = [(i, n) for i, s in enumerate(tbb) for n in calls_in(s) if callee(n) == "_run"]
    i_dr = next((i for i, s in enumerate(tbb) if ast.unparse(s) == "dev_rows, manifest = _dev_rows_only(fz, generated, tmp_path)"), None)
    scripts = []
    for i, n in runs:
        lst = n.args[0]
        elts = [ast.unparse(e) for e in lst.elts] if isinstance(lst, ast.List) else []
        ev_arg = elts[elts.index("'--eval-sets'") + 1] if "'--eval-sets'" in elts else None
        man_arg = elts[elts.index("'--manifest'") + 1] if "'--manifest'" in elts else None
        scripts.append((i, elts[0] if elts else ast.unparse(lst), ev_arg, man_arg))
        print(f"  _run at statement {i}: {elts[0] if elts else '?'} | --eval-sets {ev_arg} | --manifest {man_arg}")
    l6runs = [x for x in scripts if "l6_check" in x[1]]
    l6_ok = (i_dr is not None and len(l6runs) == 1 and l6runs[0][2] == "dev_rows" and l6runs[0][3] == "manifest" and i_dr < l6runs[0][0]
             and all(x[2] is None for x in scripts if "l6_check" not in x[1]))
    print(f"  `dev_rows, manifest = _dev_rows_only(fz, generated, tmp_path)` at statement {i_dr}; l6_check.py gets --eval-sets dev_rows and --manifest "
          f"manifest, no other script gets --eval-sets: {l6_ok}")
    ok &= l6_ok
    sub = set()
    for fn_, tree in ttrees.items():
        for n in ast.walk(tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) and ast.unparse(n.left) == "rep" and isinstance(n.right, ast.Constant):
                sub.add(("script", "metrix/e1-pilot/reports/" + n.right.value))
            if isinstance(n, ast.List) and len(n.elts) >= 3 and ast.unparse(n.elts[0]) == "sys.executable" and \
                    any(isinstance(e, ast.Constant) and e.value == "-m" for e in n.elts):
                k = [i for i, e in enumerate(n.elts) if isinstance(e, ast.Constant) and e.value == "-m"][0]
                if k + 1 < len(n.elts) and isinstance(n.elts[k + 1], ast.Constant):
                    sub.add(("module", n.elts[k + 1].value))
    for kind, x in sorted(sub):
        p = os.path.join(repo, x) if kind == "script" else os.path.join(repo, "metrix/e1-pilot/src", *x.split(".")) + ".py"
        print(f"  run by tests ({kind}): {x} mentions eval_sets: {bool(re.search(r'eval_sets|eval-sets', open(p, encoding='utf-8').read()))}")
    script_mentions = sorted(x for k, x in sub if k == "script" and re.search(r"eval_sets|eval-sets", open(os.path.join(repo, x), encoding="utf-8").read()))
    print(f"  reports/ scripts run by tests that mention eval_sets: {script_mentions} (l6_check.py receives only the DEV-rows copy, above)")
    ok &= script_mentions == ["metrix/e1-pilot/reports/round5/l6_check.py"]

    # ---------------------------------------------------------------------------------------------- j
    print("\n== j. the Executor's listing (t12_fix3.txt lines 19-58) vs my AST enumeration of open / read_text / read_bytes calls")
    t12 = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_b/t12_fix3.txt"), encoding="utf-8").read().split("\n")
    ex = [m.groups() for ln in t12[18:58] for m in [re.match(r"^(metrix/e1-pilot/(?:src|tests)/\S+\.py):(\d+):(.*)$", ln)] if m]
    print(f"  Executor lines parsed: {len(ex)} (t12 line 18 is the grep command, line 59 its exit=0: {t12[58] == 'exit=0'})")
    ok &= len(ex) == 40 and t12[58] == "exit=0"
    mine, strings = set(), {}
    for root in (os.path.join(repo, "metrix/e1-pilot/src"), tdir):
        for r, ds, fs in os.walk(root):
            if "__pycache__" in r:
                continue
            for f in fs:
                if f.endswith(".py"):
                    p = os.path.join(r, f)
                    rel = os.path.relpath(p, repo)
                    tree = ast.parse(open(p, encoding="utf-8").read())
                    for n in ast.walk(tree):
                        if isinstance(n, ast.Call) and callee(n) in ("open", "read_text", "read_bytes"):
                            mine.add((rel, n.func.end_lineno if isinstance(n.func, ast.Attribute) else n.lineno))
                        if isinstance(n, ast.Constant) and isinstance(n.value, str):
                            for k in range(n.lineno, n.end_lineno + 1):
                                strings.setdefault(rel, set()).add(k)
                        if isinstance(n, ast.FunctionDef):
                            strings.setdefault(rel + "#def", set()).add(n.lineno)
    exs = {(a, int(b)) for a, b, _ in ex}
    only_ex = sorted(exs - mine)
    only_mine = sorted(mine - exs)
    explained = [(a, b) for a, b in only_ex if b in strings.get(a, set()) or b in strings.get(a + "#def", set())]
    print(f"  my calls {len(mine)} | Executor lines {len(exs)} | lines only in the Executor's grep {only_ex} | calls only in mine {only_mine}")
    for a, b in only_ex:
        why = "inside a string constant (docstring)" if b in strings.get(a, set()) else ("a def line" if b in strings.get(a + "#def", set()) else "?")
        print(f"    {a}:{b}: {why}: {open(os.path.join(repo, a), encoding='utf-8').read().split(chr(10))[b - 1].strip()[:100]!r}")
    print(f"  every call I enumerate is in the Executor's listing, and every extra grep line is a docstring or a def: {not only_mine and explained == only_ex}")
    ok &= not only_mine and explained == only_ex
    ev_lines = [(a, b, c.strip()) for a, b, c in ex if "eval_sets" in c or "(src" in c or "eval_sets_path" in c]
    print(f"  of them, opens of eval_sets.jsonl (Executor's note, line 17): {ev_lines}")
    return bool(ok)


run(main)
