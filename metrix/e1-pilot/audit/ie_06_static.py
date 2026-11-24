"""IE-6 (implementation stage B, second fix commit, task 2, static).  Questions:
  (1) after the change, does any path in src/ or tests/ (including the reference scripts under reports/ that the tests
      run) open eval_sets.jsonl in text mode, or decode / parse a row whose split is not dev?
  (2) do the new re-checks of leakage.verify_authorization (Gate 0 status PASS, freeze record bound to the Gate 0
      record, the authorization's frozen commit == the one PROTOCOL_FROZEN names) and the new formal-mode-only
      restriction of evaluate.evaluate_model(split="test") run before any TEST content is read?
  (3) (carried over from my round 3) do evaluate_model(split="test"), generate_test and run_test_part call
      verify_authorization first; can anything before the preconditions instantiate a TEST question?
Every source file is read as text and parsed with the standard `ast` module (never imported or run).  Interpretation
ENTRIES are read with ast.literal_eval (literals only).
  a. call sites in src/metrix_e1/*.py and reports/impl_b/dump_for_audit.py (as in id_06);
  b. data.build_general_dev (unchanged file; as in id_06);
  c. test_data.main / check_preconditions / interpretation check / record checks (as in id_06);
  d. the guards: generate_test and run_test_part statement 0; evaluate_model: split check, then
     `if split == 'test':` whose body is [formal-mode check raising, import, verify_authorization(...)], all before
     require_gpu and before anything touches data / qa_file / gen_file; mode.RunMode.formal is `name == FORMAL`;
     verify_authorization: isinstance guard; loop over the two committed records (committed_record, hash compare);
     then the three new checks (status from the committed Gate 0 record, binding from the committed freeze record,
     PROTOCOL_FROZEN commit), each raising ImplementationFail; its only reads are committed_record (git cat-file of the
     two records + their working-tree bytes) and read_bytes of Path(repo_root) / FZ.PROTOCOL_FROZEN_REL
     (== "metrix/e1-pilot/PROTOCOL_FROZEN"); frozen.parse_protocol_frozen reads no file; no TEST name appears in it;
  e./f./g. leakage.py, template instantiation, evaluate_model callers (as in id_06);
  h. tests/: every call of a TEST path with its arguments (as in id_06, plus the new tests);
  i. eval_sets.jsonl readers: every open / read_text / read_bytes / json.load / copy call in src/ and tests/ whose
     argument refers to eval_sets (by name or through general_source / the variable bound to it); every script run
     by tests as a subprocess and whether it mentions eval_sets; tests/test_data_hashes.py::_dev_rows_only (binary
     open, bytes pattern anchored at the row start, inside the row loop only _ROW_SPLIT.match(line) and, under
     `if m.group(1) == b'dev'`, fo.write(line); no decode / loads of a row; counts asserted 400 / 800; the manifest
     copy changes only general_text.source_file_sha256) and that l6_check.py receives that file and that manifest
     and nothing else from eval_sets; the other eval_sets users in tests (test_st12: shutil.copyfile, flip =
     read_bytes / write_bytes, check_inputs = whole-file hash).
Data Auditor's own script (adapted from my id_06_static.py); no Executor code imported, called or copied.
usage: python -I ie_06_static.py <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, re
from ia_common import frozen_json, git, run

PKG = "metrix/e1-pilot/src/metrix_e1"
EXTRA = ["metrix/e1-pilot/reports/impl_b/dump_for_audit.py"]
TESTS = "metrix/e1-pilot/tests"
WATCH = ["generate_test", "build_test_qa", "params_for_test", "run_test_part", "TestAuthorization", "verify_authorization",
         "committed_record", "committed_json", "build_general_dev", "check_preconditions", "check_interpretations_ruled",
         "evaluate_model"]
READERS = ("open", "read_text", "read_bytes", "read_jsonl", "parse_jsonl", "load", "loads")
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
    return ast.unparse(s).split("\n")[0][:120]


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
    for w in WATCH:
        print(f"  {w}: {sites[w]}")
    expect = {"generate_test": [("test_data.py", "main")], "build_test_qa": [("test_data.py", "generate_test")],
              "params_for_test": [("test_data.py", "generate_test")], "run_test_part": [("test_data.py", "main")],
              "TestAuthorization": [("test_data.py", "check_preconditions")],
              "verify_authorization": [("evaluate.py", "evaluate_model"), ("leakage.py", "run_test_part"), ("test_data.py", "generate_test")],
              "committed_record": [("leakage.py", "verify_authorization"), ("stops.py", "st13_scan"), ("test_data.py", "_committed")],
              "committed_json": [("record.py", "committed_record")],
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
    print(f"  read calls whose argument names a TEST file (test_qa / general_test / TEST_FILES / SPLIT_FILES / qa_file / gen_file): {test_readers}")
    ok &= not test_readers
    print(f"  uses of TEST_FILES / SPLIT_FILES (file, line, function): {tf_uses}")
    tf_ok = True
    for b, ln, fn in tf_uses:
        if fn == "<module>":
            continue
        ftree = trees[f"{PKG}/{b}"][1] if f"{PKG}/{b}" in trees else None
        f_ = func(ftree, fn)
        stmts = [s for s in ast.walk(f_) if isinstance(s, (ast.Assign, ast.If, ast.Raise, ast.Expr, ast.Return)) and
                 any((isinstance(x, ast.Name) and x.id in ("TEST_FILES", "SPLIT_FILES")) or (isinstance(x, ast.Attribute) and x.attr in ("TEST_FILES", "SPLIT_FILES"))
                     for x in ast.walk(s)) and getattr(s, "lineno", -1) <= ln <= getattr(s, "end_lineno", -1)]
        st = min(stmts, key=lambda s: s.end_lineno - s.lineno) if stmts else None
        txt = ast.unparse(st) if st is not None else "?"
        cs = sorted({callee(c) for c in calls_in(st)} - {None}) if st is not None else []
        good = (fn, b) == ("evaluate_model", "evaluate.py") or not (set(cs) & set(READERS))
        tf_ok &= good
        print(f"    {b}:{ln} in {fn}: {txt.split(chr(10))[0][:120]} | calls {cs} | no reader {good}")
    ok &= tf_ok
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
        print(f"  capture groups {groups} | anchored at the domain field, group 1 = the split value up to the next quote: {split_grp}")
        ok &= groups == 1 and split_grp
    bg = func(dtree, "build_general_dev")
    opens = [n for n in ast.walk(bg) if isinstance(n, ast.Call) and callee(n) == "open"]
    binary = len(opens) == 1 and len(opens[0].args) == 2 and isinstance(opens[0].args[1], ast.Constant) and opens[0].args[1].value == "rb" \
        and not opens[0].keywords
    print(f"  open calls: {[ast.unparse(o) for o in opens]} | exactly one open, mode 'rb', no encoding argument: {binary}")
    ok &= binary
    want = [ast.unparse(s) for s in body_wo_doc(bg) if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "want" for t in s.targets)]
    print(f"  want: {want}")
    ok &= want == ["want = p.general_dev_split.encode('ascii')"]
    loop = next(n for n in ast.walk(bg) if isinstance(n, ast.For) and "enumerate(fh" in ast.unparse(n.iter))
    for i, s in enumerate(loop.body):
        print(f"    loop statement {i}: {first1(s)}")
    i_cont = next(i for i, s in enumerate(loop.body) if isinstance(s, ast.If) and any(isinstance(x, ast.Continue) for x in s.body))
    cont_test = ast.unparse(loop.body[i_cont].test)
    print(f"  non-dev continue: statement {i_cont}, test {cont_test!r}")
    ok &= cont_test == "m.group(1) != want"
    before = loop.body[:i_cont]
    line_uses = [ast.unparse(n) for s in before for n in ast.walk(s) if isinstance(n, ast.Call) and "line" in names_in(n)
                 and not any(isinstance(a, ast.Call) for a in n.args)]
    decodes_before = [ast.unparse(n) for s in before for n in ast.walk(s) if isinstance(n, ast.Call) and callee(n) in ("decode", "loads", "load")]
    b_ok = line_uses == ["_ROW_HEAD.match(line)"] and decodes_before == ["m.group(1).decode('ascii', 'replace')"]
    print(f"  calls before the continue that take the row bytes: {line_uses}")
    print(f"  decode / json calls before the continue: {decodes_before} | only the prefix match and the split-field decode: {b_ok}")
    ok &= b_ok
    after_dec = [(i, ast.unparse(n)) for i, s in enumerate(loop.body) for n in ast.walk(s)
                 if isinstance(n, ast.Call) and callee(n) in ("decode", "loads") and "line" in names_in(n)]
    print(f"  calls that decode or parse the row, with their statement index: {after_dec}")
    ok &= bool(after_dec) and all(i > i_cont for i, _ in after_dec)
    inc = [(i, ast.unparse(s)) for i, s in enumerate(loop.body) if isinstance(s, ast.AugAssign) and ast.unparse(s.target) == "parsed"]
    i_loads = min(i for i, _ in after_dec)
    print(f"  'parsed' increments in the loop: {inc} | after the continue and after the parse (statement {i_loads}): "
          f"{bool(inc) and all(i > i_cont and i > i_loads for i, _ in inc)}")
    ok &= len(inc) == 1 and inc[0][0] > i_loads > i_cont
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

    # ---------------------------------------------------------------------------------------------- c
    print("\n== c. test_data.main, check_preconditions, interpretation check, record checks")
    ttree = T("test_data.py")
    fns = {n.name: n for n in ttree.body if isinstance(n, ast.FunctionDef)}
    mf = fns["main"]
    try_i = next(i for i, s in enumerate(mf.body) if isinstance(s, ast.Try))
    t = mf.body[try_i]
    try_calls = [callee(n) for s in t.body for n in ast.walk(s) if isinstance(n, ast.Call)]
    print(f"  try body calls: {try_calls} | handlers: {[(ast.unparse(h.type), [ast.unparse(s) for s in h.body]) for h in t.handlers]}")
    exits = len(t.handlers) == 1 and ast.unparse(t.handlers[0].body[-1]) == "sys.exit(1)"
    after = [callee(n) for s in mf.body[try_i + 1:] for n in ast.walk(s) if isinstance(n, ast.Call)]
    print(f"  handler ends with sys.exit(1): {exits} | finally / else: {bool(t.finalbody)} / {bool(t.orelse)} | calls after the try: {after}")
    ok &= try_calls == ["check_preconditions"] and exits and not t.finalbody and not t.orelse and "generate_test" in after
    tsrc = trees[f"{PKG}/test_data.py"][0]
    guarded = re.search(r'if __name__ == "__main__":\n    run_guarded\(main\)\s*$', tsrc) is not None
    print(f"  module entry point is run_guarded(main): {guarded}")
    ok &= guarded
    cp = body_wo_doc(fns["check_preconditions"])
    want_order = ["st12", "load", "check_data_dir", "check_gate0_record", "check_selection_record", "check_interpretations_ruled", "TestAuthorization"]
    got_order = [callee(next(n for n in ast.walk(s) if isinstance(n, ast.Call))) if not isinstance(s, ast.Return)
                 else [callee(n) for n in ast.walk(s) if isinstance(n, ast.Call)][0] for s in cp]
    print(f"  check_preconditions, first call of each statement: {got_order} | == {want_order}: {got_order == want_order}")
    ok &= got_order == want_order and isinstance(cp[-1], ast.Return)
    cir = body_wo_doc(fns["check_interpretations_ruled"])
    ok &= len(cir) == 2 and ast.unparse(cir[0]) == "open_ids = INT.pending()" and isinstance(cir[1], ast.If) \
        and isinstance(cir[1].body[0], ast.Raise) and "PreconditionFailed" in ast.unparse(cir[1].body[0])
    itree = T("interpretations.py")
    ent = next(n for n in itree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "ENTRIES" for x in n.targets))
    entries = ast.literal_eval(ent.value)
    pc = next(n for n in itree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "PENDING" for x in n.targets))
    PENDING = ast.literal_eval(pc.value)
    pend_ids = [e["id"] for e in entries if e.get("status", PENDING) == PENDING]
    print(f"  check_interpretations_ruled: {[ast.unparse(s)[:80] for s in cir]} | ENTRIES {len(entries)} | pending now {len(pend_ids)}")
    ok &= len(pend_ids) == len(entries) > 0
    for name in ("_committed", "check_gate0_record", "check_selection_record"):
        calls = sorted({callee(n) for n in ast.walk(fns[name]) if isinstance(n, ast.Call)} - {None})
        print(f"  {name} calls: {calls}")
        ok &= not ({"generate_test", "build_test_qa", "build_general_dev", "fill", "read_jsonl", "open", "verify_authorization"} & set(calls))

    # ---------------------------------------------------------------------------------------------- d
    print("\n== d. the guards of the three TEST paths and what they check (new: formal-mode check, three re-checks)")
    gt_fn = func(ttree, "generate_test")
    gtb = body_wo_doc(gt_fn)
    g0 = ast.unparse(gtb[0])
    g_ok = g0 == "LK.verify_authorization(authorization, fz.repo_root)"
    i_rep = next(i for i, s in enumerate(gtb) if "dataclasses.replace" in ast.unparse(s))
    reads_gt = [(i, callee(c)) for i, s in enumerate(gtb) for c in calls_in(s)
                if callee(c) in ("params", "check_inputs", "load_qwen_tokenizer", "params_for_test", "read_jsonl", "build_test_qa", "build_general_dev")]
    print(f"  generate_test statement 0 is LK.verify_authorization(authorization, fz.repo_root): {g_ok} | readers / builders after it: "
          f"{reads_gt} (all at statement > 0: {all(i > 0 for i, _ in reads_gt)}) | TEST split set at statement {i_rep}")
    ok &= g_ok and bool(reads_gt) and all(i > 0 for i, _ in reads_gt) and i_rep > 0
    ltree = T("leakage.py")
    rtp = body_wo_doc(func(ltree, "run_test_part"))
    r0 = ast.unparse(rtp[0])
    first_use = next(i for i, s in enumerate(rtp) if names_in(s) & {"test_qa", "general_test"})
    r_ok = r0 == "verify_authorization(authorization, repo_root)"
    print(f"  run_test_part statement 0: {r0!r} -> verify first {r_ok} | first statement using test_qa / general_test: {first_use} | after the verify {first_use > 0}")
    ok &= r_ok and first_use > 0
    # evaluate_model
    etree = T("evaluate.py")
    sf = next(n for n in etree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "SPLIT_FILES" for x in n.targets))
    sfv = ast.literal_eval(sf.value)
    print(f"  {ast.unparse(sf)} | keys exactly dev, test: {sorted(sfv) == ['dev', 'test']}")
    ok &= sorted(sfv) == ["dev", "test"]
    em = func(etree, "evaluate_model")
    emb = body_wo_doc(em)
    for i, s in enumerate(emb):
        print(f"    evaluate_model statement {i}: {first1(s)}")
    i_split = next((i for i, s in enumerate(emb) if isinstance(s, ast.If) and ast.unparse(s.test) == "split not in SPLIT_FILES"
                    and isinstance(s.body[0], ast.Raise)), None)
    i_guard = next((i for i, s in enumerate(emb) if isinstance(s, ast.If) and ast.unparse(s.test) in ("split == 'test'", "'test' == split")), None)
    i_gpu = next((i for i, s in enumerate(emb) if any(callee(c) == "require_gpu" for c in calls_in(s))), None)
    touch = {"data", "qa_file", "gen_file", "qs", "facts", "cands"}
    i_data = next((i for i, s in enumerate(emb) if {n.id for n in ast.walk(s) if isinstance(n, ast.Name)} & touch), None)
    e_ok = False
    if i_guard is not None:
        gb = emb[i_guard].body
        for j, s in enumerate(gb):
            print(f"      guard statement {j}: {first1(s)}")
        j_mode = next((j for j, s in enumerate(gb) if isinstance(s, ast.If) and ast.unparse(s.test) == "not mode.formal"
                       and len(s.body) == 1 and isinstance(s.body[0], ast.Raise) and callee(s.body[0].exc) == "ImplementationFail"
                       and not s.orelse), None)
        j_ver = next((j for j, s in enumerate(gb) if isinstance(s, ast.Expr) and ast.unparse(s) == "verify_authorization(test_authorization, repo_root)"), None)
        mode_names = sorted({n.id for n in ast.walk(gb[j_mode]) if isinstance(n, ast.Name)}) if j_mode is not None else None
        g_calls = sorted({callee(c) for c in calls_in(emb[i_guard])} - {None})
        print(f"  guard `if split == 'test'` at statement {i_guard}: formal-mode check (`if not mode.formal: raise ImplementationFail`) at guard "
              f"statement {j_mode}, names it uses {mode_names}; verify_authorization at guard statement {j_ver}; all calls in the guard {g_calls}; "
              f"else branch {bool(emb[i_guard].orelse)}")
        print(f"  split check {i_split} < guard {i_guard} < require_gpu {i_gpu} < first statement touching data / qa_file / gen_file {i_data} "
              f"({first1(emb[i_data]) if i_data is not None else None!r})")
        e_ok = (i_split is not None and i_gpu is not None and i_data is not None and i_split < i_guard < i_gpu < i_data
                and j_mode is not None and j_ver is not None and j_mode < j_ver and mode_names == ["ImplementationFail", "mode"]
                and set(g_calls) <= {"ImplementationFail", "verify_authorization"} and not emb[i_guard].orelse)
    print(f"  evaluate_model: for split 'test' the formal-mode check and then verify_authorization run before anything touches the data: {e_ok}")
    ok &= e_ok
    mtree = ast.parse(open(os.path.join(repo, "metrix/e1-pilot/src/metrix_e1/mode.py"), encoding="utf-8").read())
    fprop = next((n for n in ast.walk(mtree) if isinstance(n, ast.FunctionDef) and n.name == "formal"), None)
    fdec = [ast.unparse(d) for d in fprop.decorator_list] if fprop else None
    fbody = [ast.unparse(s) for s in body_wo_doc(fprop)] if fprop else None
    fconst = [ast.unparse(n) for n in mtree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "FORMAL"]
    print(f"  mode.RunMode.formal: decorators {fdec} body {fbody} | {fconst}")
    ok &= fdec == ["property"] and fbody == ["return self.name == FORMAL"] and fconst == ["FORMAL = 'formal'"]
    defaults = dict(zip([a.arg for a in em.args.args][-len(em.args.defaults):], [ast.unparse(d) for d in em.args.defaults]))
    print(f"  defaults: split={defaults.get('split')} test_authorization={defaults.get('test_authorization')} repo_root={defaults.get('repo_root')}")
    # verify_authorization
    va = func(ltree, "verify_authorization")
    vab = body_wo_doc(va)
    for i, s in enumerate(vab):
        print(f"    verify_authorization statement {i}: {first1(s)}")
    v0 = vab[0]
    v0_ok = isinstance(v0, ast.If) and ast.unparse(v0.test) == "not isinstance(authorization, TestAuthorization)" and isinstance(v0.body[0], ast.Raise)
    i_loop = next((i for i, s in enumerate(vab) if isinstance(s, ast.For)), None)
    loop_v = vab[i_loop] if i_loop is not None else None
    it = ast.unparse(loop_v.iter) if loop_v is not None else ""
    recs = ("R.GATE0_RECORD_REL, 'gate0', authorization.gate0_record_sha256" in it and
            "R.SELECTION_FREEZE_REL, 'selection_freeze', authorization.selection_record_sha256" in it)
    lsrc = ast.unparse(loop_v) if loop_v is not None else ""
    cr = "recs[kind], got = R.committed_record(repo_root, rel, kind, authorization.frozen_commit)" in lsrc
    lraises = [r for r in ast.walk(loop_v) if isinstance(r, ast.Raise)] if loop_v is not None else []
    cmp_ = any(isinstance(s, ast.If) and ast.unparse(s.test) == "got != want" and isinstance(s.body[0], ast.Raise) for s in ast.walk(loop_v)) if loop_v is not None else False
    print(f"  statement 0 isinstance guard raising {v0_ok} | loop (statement {i_loop}) over both records (gate0, selection_freeze) {recs} | "
          f"recs[kind], got = committed_record(repo_root, rel, kind, authorization.frozen_commit) {cr} | NotCommitted -> raise, got != want -> raise "
          f"{len(lraises) == 2 and cmp_}")
    ok &= v0_ok and recs and cr and len(lraises) == 2 and cmp_
    rest = vab[i_loop + 1:] if i_loop is not None else []
    txt = [ast.unparse(s) for s in rest]
    i_status = next((i for i, s in enumerate(txt) if s == "status = (recs['gate0'].get('gate0') or {}).get('gate0_status')"), None)
    i_status_chk = next((i for i, s in enumerate(rest) if isinstance(s, ast.If) and ast.unparse(s.test) == "status != 'PASS'"
                         and isinstance(s.body[0], ast.Raise)), None)
    i_bind = next((i for i, s in enumerate(rest) if isinstance(s, ast.If) and ast.unparse(s.test) ==
                   "recs['selection_freeze'].get('gate0_record_sha256') != authorization.gate0_record_sha256" and isinstance(s.body[0], ast.Raise)), None)
    i_pf = next((i for i, s in enumerate(rest) if isinstance(s, ast.Try) and
                 ast.unparse(s.body[0]) == "current = FZ.parse_protocol_frozen((Path(repo_root) / FZ.PROTOCOL_FROZEN_REL).read_bytes()).commit"
                 and len(s.handlers) == 1 and ast.unparse(s.handlers[0].type) == "(OSError, ST12Error)"
                 and isinstance(s.handlers[0].body[0], ast.Raise)), None)
    i_cur = next((i for i, s in enumerate(rest) if isinstance(s, ast.If) and ast.unparse(s.test) == "current != authorization.frozen_commit"
                  and isinstance(s.body[0], ast.Raise)), None)
    new_ok = None not in (i_status, i_status_chk, i_bind, i_pf, i_cur) and i_status < i_status_chk and i_pf < i_cur
    print(f"  after the loop: status from the committed Gate 0 record at {i_status}, `status != 'PASS'` -> raise at {i_status_chk}; "
          f"binding (committed freeze record's gate0_record_sha256 == authorization's) -> raise at {i_bind}; PROTOCOL_FROZEN parsed "
          f"(OSError / ST12Error -> raise) at {i_pf}; `current != authorization.frozen_commit` -> raise at {i_cur} | all three present: {new_ok}")
    ok &= new_ok
    all_raises = [r for r in ast.walk(va) if isinstance(r, ast.Raise)]
    raise_kinds = sorted({callee(r.exc) for r in all_raises})
    vcalls = sorted({callee(c) for c in calls_in(va)} - {None})
    reads_va = [ast.unparse(c) for c in calls_in(va) if callee(c) in READERS + ("read", "committed_record", "committed_json", "run")]
    vnames = names_in(va) & TEST_NAMES
    va_ok = raise_kinds == ["ImplementationFail"] and len(all_raises) == 7 and not vnames and \
        set(vcalls) <= {"isinstance", "ImplementationFail", "committed_record", "get", "parse_protocol_frozen", "read_bytes", "Path"} and \
        sorted(reads_va) == sorted(["R.committed_record(repo_root, rel, kind, authorization.frozen_commit)",
                                    "(Path(repo_root) / FZ.PROTOCOL_FROZEN_REL).read_bytes()"])
    print(f"  raises {len(all_raises)} (all ImplementationFail: {raise_kinds == ['ImplementationFail']}) | all calls {vcalls} | reads {reads_va} | "
          f"TEST names used {sorted(vnames)} | 7 raises, reads = the two committed records + PROTOCOL_FROZEN only: {va_ok}")
    ok &= va_ok
    ftree = T("frozen.py")
    pfr = [ast.unparse(n) for n in ftree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) in ("PILOT_REL", "PROTOCOL_FROZEN_REL")]
    ppf = func(ftree, "parse_protocol_frozen")
    ppf_calls = sorted({callee(c) for c in calls_in(ppf)} - {None})
    ppf_reads = sorted(set(ppf_calls) & {"open", "read_text", "read_bytes", "read_jsonl", "run", "blob_at", "check_output", "cat_file"})
    print(f"  frozen: {pfr} | parse_protocol_frozen(data) calls {ppf_calls} | file / git reads in it: {ppf_reads}")
    ok &= pfr == ["PILOT_REL = 'metrix/e1-pilot'", "PROTOCOL_FROZEN_REL = PILOT_REL + '/PROTOCOL_FROZEN'"] and not ppf_reads
    # the guards run before the TEST paths read anything: statement 0 of generate_test / run_test_part (above); in
    # evaluate_model inside the guard before data access (above).  The new checks are statements of verify_authorization.
    print(f"  -> the three new re-checks are statements of verify_authorization, which is statement 0 of generate_test and run_test_part "
          f"and runs inside the evaluate_model guard before the data: {g_ok and r_ok and e_ok and new_ok}")
    # record.committed_record / committed_json
    rtree = T("record.py")
    crf = func(rtree, "committed_record")
    crc = sorted({callee(c) for c in calls_in(crf)} - {None})
    print(f"  record.committed_record calls {crc}")
    ok &= set(crc) <= {"committed_json", "get", "NotCommitted"} and "committed_json" in crc
    cj = func(rtree, "committed_json")
    cj_calls = [ast.unparse(n)[:100] for n in ast.walk(cj) if isinstance(n, ast.Call)]
    print(f"  record.committed_json calls: {cj_calls}")
    ok &= any("cat-file" in c and "HEAD:%s" in c for c in cj_calls) and not any("open(" in c for c in cj_calls)
    stree = T("stops.py")
    sc = func(stree, "st13_scan")
    sc_reads = [c for c in calls_in(sc) if callee(c) in READERS + ("read",)]
    print(f"  stops.st13_scan readers {[ast.unparse(c) for c in sc_reads]} (only .exists() on TEST names)")
    ok &= not sc_reads and any(callee(c) == "exists" for c in calls_in(sc))

    # ---------------------------------------------------------------------------------------------- e
    print("\n== e. leakage.py")
    ld = func(ltree, "load_data")
    stems = [ast.literal_eval(e) for n in ast.walk(ld) if isinstance(n, ast.Tuple) for e in n.elts if isinstance(e, ast.Constant)]
    print(f"  load_data file stems: {stems}")
    ok &= stems and not any("test" in x for x in stems)
    subst = [n.lineno for n in ast.walk(ltree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("{E}", "{A}")]
    lm = next(n for n in ltree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    lmc = [callee(n) for n in ast.walk(lm) if isinstance(n, ast.Call)]
    print(f"  '{{E}}' / '{{A}}' constants: {subst} | leakage.main calls run_test_part: {'run_test_part' in lmc} | run_gate0: {'run_gate0' in lmc}")
    ok &= not subst and "run_test_part" not in lmc and "run_gate0" in lmc

    # ---------------------------------------------------------------------------------------------- f
    print("\n== f. template instantiation ({E} substitution)")
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
    print(f"  in test_data.py: {test_inst} | elsewhere: {other} | elsewhere == DEV / TRAIN / Y builders, fill, prefix(f): {other == expected_other}")
    ok &= test_inst == ["build_test_qa"] and other == expected_other

    # ---------------------------------------------------------------------------------------------- g
    print("\n== g. evaluate.evaluate_model callers")
    print(f"  callers in src/ and reports/impl_b/dump_for_audit.py: {sites['evaluate_model']}")
    ok &= not sites["evaluate_model"]

    # ---------------------------------------------------------------------------------------------- h
    print("\n== h. tests/: every call of a TEST path")
    g0rel = "metrix/e1-pilot/results/gate0_record.json"
    selrel = "metrix/e1-pilot/results/selection_freeze_record.json"
    in_head = {r: git(repo, "cat-file", "-e", f"HEAD:{r}", check=False).returncode == 0 for r in (g0rel, selrel)}
    print(f"  records committed at HEAD of the real repository: {in_head} (verify_authorization with repo_root = the real repository refuses)")
    ok &= not any(in_head.values())
    tdir = os.path.join(repo, TESTS)
    ttrees = {fn_: ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read()) for fn_ in sorted(os.listdir(tdir)) if fn_.endswith(".py")}
    for fn_, tree in ttrees.items():
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call) and callee(n) in ("generate_test", "build_test_qa", "run_test_part", "TestAuthorization", "evaluate_model",
                                                              "params_for_test", "check_preconditions", "verify_authorization")):
                continue
            c, s, encf = callee(n), ast.unparse(n), enc_of[id(n)]
            verdict = "listed"
            if c == "generate_test":
                a1 = ast.unparse(n.args[1])
                good = ast.unparse(n.args[0]) == "fz" and (a1 == "None" or a1 == "LK.TestAuthorization(None, None, None)")
                verdict = f"fz + None / TestAuthorization(None, None, None) -> refused by verify_authorization against the real repository: {good}"
                ok &= good
            elif c == "run_test_part":
                good = ast.unparse(n.args[2]) == "[]" and ast.unparse(n.args[3]) == "[]"
                verdict = f"test_qa and general_test are [] (no TEST content): {good}"
                ok &= good
            elif c in ("build_test_qa", "params_for_test"):
                verdict = "TEST builder called from a test: False"
                ok = False
            elif c == "evaluate_model":
                sp = [ast.unparse(k.value) for k in n.keywords if k.arg == "split"]
                rr = [ast.unparse(k.value) for k in n.keywords if k.arg == "repo_root"]
                mode_arg = ast.unparse(n.args[5]) if len(n.args) > 5 else None
                if not sp:
                    good = len(n.args) <= 7
                    verdict = f"split default 'dev': {good}"
                else:
                    good = sp == ["'test'"] and rr == ["fz.repo_root"] and ast.unparse(n.args[2]) == "data_rows"
                    verdict = (f"split 'test', mode {mode_arg}, repo_root fz.repo_root (records not committed -> refused; a non-formal mode is "
                               f"refused before that) and data_rows (generated non-TEST files only): {good}")
                ok &= good
            elif c in ("check_preconditions", "verify_authorization"):
                fdef = func(tree, encf)
                other_calls = sorted({callee(x) for x in calls_in(fdef)} & {"generate_test", "run_test_part", "evaluate_model", "build_test_qa", "build_general_dev"})
                verdict = f"the test function calls no TEST path: {not other_calls} {other_calls}"
                ok &= not other_calls
            print(f"  {fn_}:{n.lineno} in {encf}: {s[:150]}")
            print(f"      -> {verdict}")
    conf = ttrees["conftest.py"]
    gfx = func(conf, "generated")
    ok &= any("D.generate(fz, inputs_dir)" in ast.unparse(s) for s in body_wo_doc(gfx))
    asrt = [ast.unparse(s) for s in ast.walk(func(dtree, "generate")) if isinstance(s, ast.Assert)]
    print(f"  conftest.generated calls D.generate(fz, inputs_dir); data.generate asserts {asrt}")
    ok &= "assert tuple(files) == DATA_FILES" in asrt

    # ---------------------------------------------------------------------------------------------- i
    print("\n== i. eval_sets.jsonl readers in src/, tests/ and the scripts the tests run")
    # i1: every file under metrix/ (audit/ excluded) that mentions eval_sets
    mention = []
    for r, ds, fs in os.walk(os.path.join(repo, "metrix")):
        if "/." in r or "__pycache__" in r or "/metrix/e1-pilot/audit" in r:
            continue
        for f in fs:
            if f.endswith((".py", ".sh")):
                p = os.path.join(r, f)
                if re.search(r"eval_sets|eval-sets", open(p, encoding="utf-8", errors="replace").read()):
                    mention.append(os.path.relpath(p, repo))
    print(f"  executable files under metrix/ (audit/ excluded) that mention eval_sets: {sorted(mention)}")
    # i2: src/ and tests/: every reader / copier call whose argument refers to eval_sets, directly or through a variable
    RD = ("open", "read_text", "read_bytes", "load", "loads", "read_jsonl", "parse_jsonl", "copyfile", "copy", "copy2", "copytree",
          "flip", "check_file", "file_sha256", "check_inputs", "build_general_dev", "Popen", "run", "_run", "_cli", "read")
    roots = [os.path.join(repo, "metrix/e1-pilot/src"), tdir]
    found = []
    for root in roots:
        for r, ds, fs in os.walk(root):
            if "__pycache__" in r:
                continue
            for f in sorted(fs):
                if not f.endswith(".py"):
                    continue
                p = os.path.join(r, f)
                tree = ast.parse(open(p, encoding="utf-8").read())
                enc_of = enclosing(tree)
                # names bound (in the same function) to an expression that mentions eval_sets / general_source
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
    # classify every hit
    expected_hits = {
        ("metrix/e1-pilot/src/metrix_e1/data.py", "build_general_dev", "open(eval_sets_path, 'rb')"),
        ("metrix/e1-pilot/src/metrix_e1/data.py", "generate", "build_general_dev(p, tok, paths['eval_sets'], paths['parcae_tokenizer'])"),
        ("metrix/e1-pilot/src/metrix_e1/test_data.py", "generate_test", "D.build_general_dev(pt, tok, paths['eval_sets'], paths['parcae_tokenizer'])"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "open(src, 'rb')"),
        # the DEV-rows copy (its file name, eval_sets_dev_rows.jsonl, contains "eval_sets"): written, hashed, given to l6_check.py
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "open(out, 'wb')"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "_dev_rows_only", "FZ.file_sha256(out)"),
        ("metrix/e1-pilot/tests/test_data_hashes.py", "test_byte_identical_to_reference_scripts",
         "_run([rep / 'round5/l6_check.py', '--eval-sets', dev_rows, '--parcae-tokenizer', inputs_dir / 'parcae_tokenizer/tokenizer.json', '--manifest', manifest, '--toke"),
        ("metrix/e1-pilot/tests/test_st12.py", "mini_repo", "shutil.copyfile(fz.repo_root / ev, root / ev)"),
        ("metrix/e1-pilot/tests/test_st12.py", "test_eval_sets_one_byte", "flip(root / p.general_source)"),
    }
    got_hits = {(a, c, d) for a, _, c, d in found}
    extra = sorted(got_hits - expected_hits)
    print(f"  hits outside the expected set (binary open in build_general_dev and its two callers; binary open of eval_sets.jsonl, write, "
          f"hash and l6_check.py run of the DEV-rows copy in the test helper; shutil.copyfile and flip in test_st12): {extra} | "
          f"expected hits all present: {expected_hits <= got_hits}")
    ok &= not extra and expected_hits <= got_hits
    # data.check_inputs / frozen.check_file hash the file in binary (file_sha256)
    fs_ = func(ftree, "file_sha256")
    fs_open = [ast.unparse(c) for c in calls_in(fs_) if callee(c) == "open"]
    cf = func(ftree, "check_file")
    cf_calls = sorted({callee(c) for c in calls_in(cf)} - {None})
    fs_ok = fs_open == ["open(path, 'rb')"] and not ({"open", "read_text", "loads", "read_jsonl"} & set(cf_calls))
    print(f"  frozen.file_sha256 opens {fs_open} | frozen.check_file calls {cf_calls} | binary whole-file hash only: {fs_ok}")
    ok &= fs_ok
    st12 = ttrees["test_st12.py"]
    fl = func(st12, "flip")
    fl_calls = sorted({callee(c) for c in calls_in(fl)} - {None})
    fl_ok = set(fl_calls) <= {"bytearray", "read_bytes", "len", "write_bytes", "bytes"}
    print(f"  tests/test_st12.py flip calls {fl_calls} (raw bytes in, one byte changed, raw bytes out; no decode): {fl_ok}")
    ok &= fl_ok
    tev = func(st12, "test_eval_sets_one_byte")
    tev_calls = sorted({callee(c) for c in calls_in(tev)} - {None})
    tev_ok = tev_calls == sorted({"load", "params", "check_inputs", "flip", "raises"})
    print(f"  tests/test_st12.py test_eval_sets_one_byte: {[ast.unparse(s)[:100] for s in body_wo_doc(tev)]} | calls {tev_calls} "
          f"(load, params, check_inputs = whole-file hash, flip, raises only): {tev_ok}")
    ok &= tev_ok
    # i3: test_data_hashes._dev_rows_only and its use
    th = ttrees["test_data_hashes.py"]
    rs = next(n for n in th.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "_ROW_SPLIT")
    rs_arg = rs.value.args[0] if isinstance(rs.value, ast.Call) and rs.value.args else None
    rs_ok = (callee(rs.value) == "compile" and isinstance(rs_arg, ast.Constant) and isinstance(rs_arg.value, bytes)
             and rs_arg.value == rb'\{"domain": "[^"\\]*", "split": "([^"\\]*)", ')
    print(f"  _ROW_SPLIT = {ast.unparse(rs.value)} | bytes pattern anchored at the domain field, one group = the split value: {rs_ok}")
    ok &= rs_ok
    dr = func(th, "_dev_rows_only")
    drb = body_wo_doc(dr)
    for i, s in enumerate(drb):
        print(f"    _dev_rows_only statement {i}: {first1(s)}")
    gt = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]
    src_assign = [ast.unparse(s) for s in drb if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "src"]
    src_ok = src_assign == [f"src = PILOT.parents[1] / '{gt['source_file']}'"]
    opens = [n for n in ast.walk(dr) if isinstance(n, ast.Call) and callee(n) == "open"]
    open_txt = [ast.unparse(o) for o in opens]
    print(f"  src = the frozen general_text.source_file under the repository root: {src_ok} | open calls {open_txt}")
    ok &= src_ok and open_txt == ["open(src, 'rb')", "open(out, 'wb')"]
    loop = next(n for n in ast.walk(dr) if isinstance(n, ast.For))
    print(f"  row loop: `for {ast.unparse(loop.target)} in {ast.unparse(loop.iter)}`")
    lb = loop.body
    line_calls = [(i, ast.unparse(c)) for i, s in enumerate(lb) for c in calls_in(s) if "line" in {x.id for x in ast.walk(c) if isinstance(x, ast.Name)}
                  and not any(isinstance(a, ast.Call) for a in c.args)]
    dec = [ast.unparse(c) for c in calls_in(dr) if callee(c) in ("decode", "loads", "load", "read_text") and
           "line" in {x.id for x in ast.walk(c) if isinstance(x, ast.Name)}]
    i_if = next((i for i, s in enumerate(lb) if isinstance(s, ast.If) and ast.unparse(s.test) == "m.group(1) == b'dev'"), None)
    write_in_dev = i_if is not None and [ast.unparse(s) for s in lb[i_if].body][:1] == ["fo.write(line)"] and \
        not any(callee(c) == "write" for s in lb[i_if].orelse for c in calls_in(s))
    writes = [ast.unparse(c) for c in calls_in(dr) if callee(c) in ("write", "write_text", "write_bytes", "writelines")]
    print(f"  calls in the loop that take the row: {line_calls} | decode / json of a row anywhere in the helper: {dec}")
    loop_ok = [c for _, c in line_calls] == ["_ROW_SPLIT.match(line)", "fo.write(line)"] and line_calls[0][0] == 0 and not dec
    w_ok = sorted(writes) == sorted(["fo.write(line)", "mpath.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')"])
    print(f"  `if m.group(1) == b'dev'` at loop statement {i_if}; fo.write(line) only in its body, nothing written in the else branch: {write_in_dev} | "
          f"write calls in the helper {writes} (the DEV rows, the manifest copy): {w_ok} | the row is only matched, then written if dev: {loop_ok}")
    ok &= loop_ok and write_in_dev and w_ok
    asserts = [ast.unparse(s) for s in ast.walk(dr) if isinstance(s, ast.Assert)]
    as_ok = "assert n == {'dev': 400, 'other': 800}" in asserts and "assert m is not None" in asserts
    print(f"  asserts: {asserts} | every row must match the prefix; 400 dev / 800 other: {as_ok}")
    ok &= as_ok
    msub = [ast.unparse(s) for s in ast.walk(dr) if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Subscript)]
    mload = [ast.unparse(s) for s in drb if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "manifest"]
    m_ok = msub == ["manifest['general_text']['source_file_sha256'] = FZ.file_sha256(out)"] and \
        mload == ["manifest = json.loads((PILOT / 'DATA_MANIFEST.json').read_text(encoding='utf-8'))"]
    print(f"  manifest copy: {mload} | subscript assignments {msub} | only general_text.source_file_sha256 replaced: {m_ok}")
    ok &= m_ok
    tb = func(th, "test_byte_identical_to_reference_scripts")
    tbb = body_wo_doc(tb)
    runs = [(i, n) for i, s in enumerate(tbb) for n in calls_in(s) if callee(n) == "_run"]
    i_dr = next((i for i, s in enumerate(tbb) if ast.unparse(s) == "dev_rows, manifest = _dev_rows_only(tmp_path)"), None)
    scripts = []
    for i, n in runs:
        lst = n.args[0]
        script = ast.unparse(lst.elts[0]) if isinstance(lst, ast.List) else ast.unparse(lst)
        elts = [ast.unparse(e) for e in lst.elts] if isinstance(lst, ast.List) else []
        ev_arg = elts[elts.index("'--eval-sets'") + 1] if "'--eval-sets'" in elts else None
        man_arg = elts[elts.index("'--manifest'") + 1] if "'--manifest'" in elts else None
        scripts.append((i, script, ev_arg, man_arg))
        print(f"  _run at statement {i}: {script} | --eval-sets {ev_arg} | --manifest {man_arg}")
    l6runs = [x for x in scripts if "l6_check" in x[1]]
    l6_ok = (i_dr is not None and len(l6runs) == 1 and l6runs[0][2] == "dev_rows" and l6runs[0][3] == "manifest" and i_dr < l6runs[0][0]
             and all(x[2] is None for x in scripts if "l6_check" not in x[1]))
    print(f"  `dev_rows, manifest = _dev_rows_only(tmp_path)` at statement {i_dr}; l6_check.py gets --eval-sets dev_rows and --manifest manifest, "
          f"no other script gets --eval-sets: {l6_ok}")
    ok &= l6_ok
    # i4: every script / module the tests run as a subprocess, and whether it mentions eval_sets
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
        if kind == "script":
            p = os.path.join(repo, x)
        else:
            p = os.path.join(repo, "metrix/e1-pilot/src", *x.split(".")) + ".py"
        s = open(p, encoding="utf-8").read()
        print(f"  run by tests ({kind}): {x} -> {os.path.relpath(p, repo)} mentions eval_sets: {bool(re.search(r'eval_sets|eval-sets', s))}")
    script_mentions = sorted(x for k, x in sub if k == "script" and re.search(r"eval_sets|eval-sets", open(os.path.join(repo, x), encoding="utf-8").read()))
    print(f"  reports/ scripts run by tests that mention eval_sets: {script_mentions} (l6_check.py receives only the DEV-rows copy, above)")
    ok &= script_mentions == ["metrix/e1-pilot/reports/round5/l6_check.py"]
    l6 = "metrix/e1-pilot/reports/round5/l6_check.py"
    l6t = ast.parse(open(os.path.join(repo, l6), encoding="utf-8").read())
    l6_open = [ast.unparse(n) for n in ast.walk(l6t) if isinstance(n, ast.Call) and callee(n) == "open" and "eval_sets" in ast.unparse(n)]
    print(f"  l6_check.py (unchanged since round 2): opens {l6_open} -- in the test that is the DEV-rows copy, so the text-mode decode sees DEV rows only")
    return bool(ok)


run(main)
