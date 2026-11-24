"""ID-6 (implementation stage B, fix commit, task 3, static part).  Questions:
  (1) do evaluate.evaluate_model(split="test"), test_data.generate_test and leakage.run_test_part each call
      leakage.verify_authorization before reading or using any TEST content?
  (2) before the TEST generator's three preconditions (and the interpretation check) hold, can any path decode or
      parse an eval_sets.jsonl row whose split is not dev, or instantiate a TEST question?
Every source file is read as text and parsed with the standard `ast` module (never imported or run).  Interpretation
ENTRIES are read with ast.literal_eval (literals only).
  a. call sites (src/metrix_e1/*.py and reports/impl_b/dump_for_audit.py) of the TEST entry points, of
     verify_authorization, committed_record, committed_json, build_general_dev, check_preconditions,
     check_interpretations_ruled and evaluate_model; every constant naming TEST material; every file read in the
     package; every use of data.TEST_FILES and evaluate.SPLIT_FILES;
  b. data.build_general_dev: binary open; bytes pattern; inside the row loop only _ROW_HEAD.match(line) and the
     decode of the matched split field come before the non-dev `continue`; line.decode / json.loads after it; the
     new `parsed` counter is incremented only after the continue; `want` from p.general_dev_split; in data.generate
     p = params(fz) whose split is the frozen 'dev'; in generate_test the TEST split is set only after the guard;
  c. test_data.main / check_preconditions / check_interpretations_ruled / interpretations pending / _committed and
     the two record checks (no generator or reader called);
  d. the guards: generate_test statement 0 is LK.verify_authorization(authorization, fz.repo_root); run_test_part
     statement 0 is verify_authorization(authorization, repo_root) and test_qa / general_test are used only after it;
     evaluate_model: the split check, then `if split == 'test': verify_authorization(test_authorization, repo_root)`,
     both before any statement that touches `data`, qa_file or gen_file; SPLIT_FILES has exactly the keys dev and
     test; verify_authorization: isinstance guard first, then for both committed records (gate0 / selection_freeze)
     committed_record + hash comparison, raising on every failure, no other call; record.committed_record /
     committed_json read only the named record; stops.st13_scan touches TEST files only with .exists();
  e. leakage.py: load_data stems; main does not call run_test_part; no {E}/{A} substitution;
  f. every template instantiation ({E} substitution) in the package, and the template kinds the builders select;
  g. evaluate_model callers in the package and the reports script;
  h. tests/: every call of generate_test, build_test_qa, params_for_test, run_test_part, TestAuthorization,
     verify_authorization, evaluate_model, check_preconditions (arguments printed) with the conditions under which
     none of them can reach TEST content; conftest data_rows holds only the generated non-TEST files; every reader of
     eval_sets.jsonl under metrix/ and how it opens the file (reports/round5/l6_check.py, run by
     tests/test_data_hashes.py, round-2 observation 1).
Data Auditor's own script (adapted from my ic_06_static.py); no Executor code imported, called or copied.
usage: python -I id_06_static.py <repo_root>"""
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
          f"labels, the generator and run_test_part: {stray}")
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
    print(f"  calls before the continue that take the row bytes: {line_uses}")
    print(f"  decode / json calls before the continue: {decodes_before}")
    ok &= line_uses == ["_ROW_HEAD.match(line)"] and decodes_before == ["m.group(1).decode('ascii', 'replace')"]
    after_dec = [(i, ast.unparse(n)) for i, s in enumerate(loop.body) for n in ast.walk(s)
                 if isinstance(n, ast.Call) and callee(n) in ("decode", "loads") and "line" in names_in(n)]
    print(f"  calls that decode or parse the row, with their statement index: {after_dec}")
    ok &= bool(after_dec) and all(i > i_cont for i, _ in after_dec)
    inc = [(i, ast.unparse(s)) for i, s in enumerate(loop.body) if isinstance(s, ast.AugAssign) and ast.unparse(s.target) == "parsed"]
    i_loads = min(i for i, _ in after_dec)
    print(f"  'parsed' increments in the loop: {inc} | after the continue and after the parse (statement {i_loads}): "
          f"{bool(inc) and all(i > i_cont and i > i_loads for i, _ in inc)}")
    ok &= len(inc) == 1 and inc[0][0] > i_loads > i_cont
    ret = [ast.unparse(s) for s in ast.walk(bg) if isinstance(s, ast.Return)]
    print(f"  return: {ret}")
    ok &= len(ret) == 1 and "'parsed_rows': parsed" in ret[0] and "'windows': len(out)" in ret[0]
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
    dmain = func(dtree, "main")
    lbl = [ast.unparse(n)[:220] for n in ast.walk(dmain) if isinstance(n, ast.Call) and callee(n) == "print" and "rows by split" in ast.unparse(n)]
    print(f"  data.main count line: {lbl}")

    # ---------------------------------------------------------------------------------------------- c
    print("\n== c. test_data.main, check_preconditions, interpretation check, record checks")
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
    print(f"  module entry point is run_guarded(main): {guarded}")
    ok &= guarded
    cp = body_wo_doc(fns["check_preconditions"])
    for i, s in enumerate(cp):
        print(f"    check_preconditions statement {i}: {ast.unparse(s)}")
    want_order = ["st12", "load", "check_data_dir", "check_gate0_record", "check_selection_record", "check_interpretations_ruled", "TestAuthorization"]
    got_order = [callee(next(n for n in ast.walk(s) if isinstance(n, ast.Call))) if not isinstance(s, ast.Return)
                 else [callee(n) for n in ast.walk(s) if isinstance(n, ast.Call)][0] for s in cp]
    print(f"  first call of each statement: {got_order} | == {want_order}: {got_order == want_order}")
    ok &= got_order == want_order and isinstance(cp[-1], ast.Return)
    repo_args = [ast.unparse(s) for s in cp if "repo_root" in ast.unparse(s)]
    print(f"  repo_root used by conditions 2 and 3: {repo_args}")
    ok &= all("fz.repo_root" in s for s in repo_args if "check_gate0_record" in s or "check_selection_record" in s)
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
    cmt = body_wo_doc(fns["_committed"])
    print(f"  test_data._committed: {[ast.unparse(s).replace(chr(10), ' / ')[:160] for s in cmt]}")
    for name in ("_committed", "check_gate0_record", "check_selection_record"):
        calls = sorted({callee(n) for n in ast.walk(fns[name]) if isinstance(n, ast.Call)} - {None})
        print(f"  {name} calls: {calls}")
        ok &= not ({"generate_test", "build_test_qa", "build_general_dev", "fill", "read_jsonl", "open", "verify_authorization"} & set(calls))

    # ---------------------------------------------------------------------------------------------- d
    print("\n== d. the guards of the three TEST paths and what they check")
    # generate_test
    gt_fn = func(ttree, "generate_test")
    gtb = body_wo_doc(gt_fn)
    for i, s in enumerate(gtb):
        print(f"    generate_test statement {i}: {first1(s)}")
    g0 = ast.unparse(gtb[0])
    g_ok = g0 == "LK.verify_authorization(authorization, fz.repo_root)"
    i_rep = next(i for i, s in enumerate(gtb) if "dataclasses.replace" in ast.unparse(s))
    reads_gt = [(i, callee(c)) for i, s in enumerate(gtb) for c in calls_in(s)
                if callee(c) in ("params", "check_inputs", "load_qwen_tokenizer", "params_for_test", "read_jsonl", "build_test_qa", "build_general_dev")]
    print(f"  generate_test statement 0 is LK.verify_authorization(authorization, fz.repo_root): {g_ok} | readers / builders after it: "
          f"{reads_gt} (all at statement > 0: {all(i > 0 for i, _ in reads_gt)}) | TEST split set at statement {i_rep}")
    ok &= g_ok and bool(reads_gt) and all(i > 0 for i, _ in reads_gt) and i_rep > 0
    # run_test_part
    ltree = T("leakage.py")
    rtp = body_wo_doc(func(ltree, "run_test_part"))
    r0 = ast.unparse(rtp[0])
    first_use = next(i for i, s in enumerate(rtp) if names_in(s) & {"test_qa", "general_test"})
    r_ok = r0 == "verify_authorization(authorization, repo_root)"
    print(f"  run_test_part statement 0: {r0!r} -> verify first {r_ok} | first statement using test_qa / general_test: {first_use} "
          f"({first1(rtp[first_use])!r}) | after the verify {first_use > 0}")
    ok &= r_ok and first_use > 0
