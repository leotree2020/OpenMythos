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
    # evaluate_model
    etree = T("evaluate.py")
    sf = next(n for n in etree.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "SPLIT_FILES" for x in n.targets))
    sfv = ast.literal_eval(sf.value)
    print(f"  {ast.unparse(sf)} | keys exactly dev, test: {sorted(sfv) == ['dev', 'test']}")
    ok &= sorted(sfv) == ["dev", "test"]
    em = func(etree, "evaluate_model")
    print(f"  evaluate_model signature: ({ast.unparse(em.args)})")
    emb = body_wo_doc(em)
    for i, s in enumerate(emb):
        print(f"    evaluate_model statement {i}: {first1(s)}")
    i_split = next((i for i, s in enumerate(emb) if isinstance(s, ast.If) and ast.unparse(s.test) == "split not in SPLIT_FILES"
                    and isinstance(s.body[0], ast.Raise)), None)
    i_guard = next((i for i, s in enumerate(emb) if isinstance(s, ast.If) and ast.unparse(s.test) in ("split == 'test'", "'test' == split")), None)
    guard_calls = [ast.unparse(c) for c in calls_in(emb[i_guard])] if i_guard is not None else []
    guard_else = bool(emb[i_guard].orelse) if i_guard is not None else None
    touch = {"data", "qa_file", "gen_file", "qs", "facts", "cands"}
    i_data = next((i for i, s in enumerate(emb) if names_in(s) & touch), None)
    print(f"  split check at statement {i_split} | guard `if split == 'test'` at statement {i_guard}, calls {guard_calls}, else branch {guard_else} | "
          f"first statement touching data / qa_file / gen_file at {i_data}: {first1(emb[i_data]) if i_data is not None else None!r}")
    e_ok = (i_split is not None and i_guard is not None and i_data is not None and i_split < i_guard < i_data
            and guard_calls == ["verify_authorization(test_authorization, repo_root)"] and not guard_else)
    print(f"  evaluate_model: verify_authorization(test_authorization, repo_root) runs for split 'test' before anything touches the data: {e_ok}")
    ok &= e_ok
    defaults = dict(zip([a.arg for a in em.args.args][-len(em.args.defaults):], [ast.unparse(d) for d in em.args.defaults]))
    print(f"  defaults: test_authorization={defaults.get('test_authorization')} repo_root={defaults.get('repo_root')} "
          f"(split 'test' with the defaults -> verify_authorization(None, None) -> the isinstance guard raises)")
    # verify_authorization
    va = func(ltree, "verify_authorization")
    vab = body_wo_doc(va)
    for i, s in enumerate(vab):
        print(f"    verify_authorization statement {i}: {first1(s)}")
    v0 = vab[0]
    v0_ok = isinstance(v0, ast.If) and ast.unparse(v0.test) == "not isinstance(authorization, TestAuthorization)" and isinstance(v0.body[0], ast.Raise)
    loop_v = next((s for s in vab if isinstance(s, ast.For)), None)
    it = ast.unparse(loop_v.iter) if loop_v is not None else ""
    recs = ("R.GATE0_RECORD_REL, 'gate0', authorization.gate0_record_sha256" in it and
            "R.SELECTION_FREEZE_REL, 'selection_freeze', authorization.selection_record_sha256" in it)
    lsrc = ast.unparse(loop_v) if loop_v is not None else ""
    cr = "R.committed_record(repo_root, rel, kind, authorization.frozen_commit)" in lsrc
    raises = [ast.unparse(r)[:100] for r in ast.walk(loop_v) if isinstance(r, ast.Raise)] if loop_v is not None else []
    cmp_ = any(isinstance(s, ast.If) and ast.unparse(s.test) == "got != want" and isinstance(s.body[0], ast.Raise) for s in ast.walk(loop_v)) if loop_v is not None else False
    vcalls = sorted({callee(c) for c in calls_in(va)} - {None})
    print(f"  verify_authorization: statement 0 isinstance guard raising {v0_ok} | loop over both records (gate0, selection_freeze) {recs} | "
          f"committed_record(repo_root, rel, kind, authorization.frozen_commit) {cr} | NotCommitted -> raise, got != want -> raise "
          f"{len(raises) == 2 and cmp_} | all calls {vcalls}")
    ok &= v0_ok and recs and cr and len(raises) == 2 and cmp_ and set(vcalls) <= {"isinstance", "ImplementationFail", "committed_record"}
    # record.committed_record / committed_json
    rtree = T("record.py")
    crf = func(rtree, "committed_record")
    crc = sorted({callee(c) for c in calls_in(crf)} - {None})
    crb = [ast.unparse(s).replace("\n", " / ")[:150] for s in body_wo_doc(crf)]
    print(f"  record.committed_record: {crb} | calls {crc}")
    ok &= set(crc) <= {"committed_json", "get", "NotCommitted"} and "committed_json" in crc
    cj = func(rtree, "committed_json")
    cj_calls = [ast.unparse(n)[:100] for n in ast.walk(cj) if isinstance(n, ast.Call)]
    print(f"  record.committed_json calls: {cj_calls}")
    ok &= any("cat-file" in c and "HEAD:%s" in c for c in cj_calls) and not any("open(" in c for c in cj_calls)
    # stops.st13_scan
    stree = T("stops.py")
    sc = func(stree, "st13_scan")
    scc = [ast.unparse(c)[:110] for c in calls_in(sc)]
    sc_reads = [c for c in calls_in(sc) if callee(c) in READERS + ("read",)]
    print(f"  stops.st13_scan calls: {scc} | readers {[ast.unparse(c) for c in sc_reads]}")
    ok &= not sc_reads and any(callee(c) == "exists" for c in calls_in(sc))
    print(f"  TestAuthorization(...) constructed in the package at: {sites['TestAuthorization']}")

    # ---------------------------------------------------------------------------------------------- e
    print("\n== e. leakage.py")
    ld = func(ltree, "load_data")
    stems = [ast.literal_eval(e) for n in ast.walk(ld) if isinstance(n, ast.Tuple) for e in n.elts if isinstance(e, ast.Constant)]
    print(f"  load_data file stems: {stems}")
    ok &= stems and not any("test" in x for x in stems)
    subst = [n.lineno for n in ast.walk(ltree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ("{E}", "{A}")]
    print(f"  '{{E}}' / '{{A}}' constants in leakage.py: {subst}")
    ok &= not subst
    lm = next(n for n in ltree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    lmc = [callee(n) for n in ast.walk(lm) if isinstance(n, ast.Call)]
    print(f"  leakage.main calls run_test_part: {'run_test_part' in lmc} | verify_authorization: {'verify_authorization' in lmc} | run_gate0: {'run_gate0' in lmc}")
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
    tt = func(etree, "train_templates")
    print(f"  evaluate.train_templates selects: {ast.unparse(next(n for n in ast.walk(tt) if isinstance(n, ast.If)).test)}")

    # ---------------------------------------------------------------------------------------------- g
    print("\n== g. evaluate.evaluate_model callers")
    print(f"  callers in src/ and reports/impl_b/dump_for_audit.py: {sites['evaluate_model']}")
    ok &= not sites["evaluate_model"]

    # ---------------------------------------------------------------------------------------------- h
    print("\n== h. tests/ and every eval_sets.jsonl reader under metrix/")
    g0rel = "metrix/e1-pilot/results/gate0_record.json"
    selrel = "metrix/e1-pilot/results/selection_freeze_record.json"
    in_head = {r: git(repo, "cat-file", "-e", f"HEAD:{r}", check=False).returncode == 0 for r in (g0rel, selrel)}
    print(f"  records committed at HEAD of the real repository: {in_head} (verify_authorization with repo_root = the real repository "
          f"(fz.repo_root) refuses at the first record while both are False)")
    ok &= not any(in_head.values())
    tdir = os.path.join(repo, TESTS)
    tcalls = []
    for fn_ in sorted(os.listdir(tdir)):
        if not fn_.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read())
        enc_of = enclosing(tree)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and callee(n) in ("generate_test", "build_test_qa", "run_test_part", "TestAuthorization", "evaluate_model",
                                                         "params_for_test", "check_preconditions", "verify_authorization"):
                tcalls.append((fn_, n, enc_of[id(n)]))
    for fn_, n, encf in tcalls:
        c = callee(n)
        s = ast.unparse(n)
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
            if not sp:
                good = len(n.args) <= 7
                verdict = f"split default 'dev': {good}"
            else:
                good = sp == ["'test'"] and rr == ["fz.repo_root"] and ast.unparse(n.args[2]) == "data_rows"
                verdict = (f"split 'test' with repo_root fz.repo_root (records not committed -> refused) and data_rows (generated "
                           f"non-TEST files only): {good}")
            ok &= good
        elif c == "check_preconditions":
            fdef = func(ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read()), encf)
            other_calls = sorted({callee(x) for x in calls_in(fdef)} & {"generate_test", "run_test_part", "evaluate_model", "build_test_qa", "build_general_dev"})
            mp = [ast.unparse(x)[:80] for x in calls_in(fdef) if callee(x) == "setattr"]
            verdict = f"the test function calls no TEST path after it: {not other_calls} {other_calls} | monkeypatches {mp}"
            ok &= not other_calls
        elif c == "verify_authorization":
            fdef = func(ast.parse(open(os.path.join(tdir, fn_), encoding="utf-8").read()), encf)
            other_calls = sorted({callee(x) for x in calls_in(fdef)} & {"generate_test", "run_test_part", "evaluate_model", "build_test_qa", "build_general_dev"})
            verdict = f"verification only; the test function calls no TEST path: {not other_calls} {other_calls}"
            ok &= not other_calls
        print(f"  {fn_}:{n.lineno} in {encf}: {s[:150]}")
        print(f"      -> {verdict}")
    conf = ast.parse(open(os.path.join(tdir, "conftest.py"), encoding="utf-8").read())
    dr = func(conf, "data_rows")
    gfx = func(conf, "generated")
    print(f"  conftest.data_rows: {[ast.unparse(s)[:140] for s in body_wo_doc(dr)]}")
    print(f"  conftest.generated: {[ast.unparse(s)[:140] for s in body_wo_doc(gfx)]}")
    ok &= any("D.generate(fz, inputs_dir)" in ast.unparse(s) for s in body_wo_doc(gfx))
    gfn = func(dtree, "generate")
    asrt = [ast.unparse(s) for s in ast.walk(gfn) if isinstance(s, ast.Assert)]
    print(f"  data.generate asserts: {asrt} (its files are exactly DATA_FILES, which holds no TEST file)")
    ok &= "assert tuple(files) == DATA_FILES" in asrt
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
    print(f"  executable files under metrix/ (audit/ excluded below) that mention eval_sets: {[x for x in readers if not x.startswith('metrix/e1-pilot/audit/')]}")
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
    ic = next(i for i, s in enumerate(lp.body) if isinstance(s, ast.If) and any(isinstance(x, ast.Continue) for x in s.body))
    ij = next(i for i, s in enumerate(lp.body) if "json.loads" in ast.unparse(s))
    l6_open = [ast.unparse(n) for n in ast.walk(l6t) if isinstance(n, ast.Call) and callee(n) == "open" and "eval_sets" in ast.unparse(n)]
    l6_blob_head = git(repo, "cat-file", "blob", f"HEAD:{l6}").stdout
    l6_blob_r2 = git(repo, "cat-file", "blob", f"0bc0eecf1f684773248c198afb94e7026dcfb16d:{l6}").stdout
    l6_wt = open(os.path.join(repo, l6), "rb").read()
    print(f"  l6_check.py working tree == HEAD blob == blob at 0bc0eecf (round-2 HEAD): {l6_wt == l6_blob_head == l6_blob_r2}")
    print(f"  l6_check.py: open {l6_open} (text mode: every line, test rows included, is UTF-8-decoded into "
          f"str by Python) | non-dev continue at {ic}, json.loads at {ij}: continue first {ic < ij}")
    ok &= ic < ij
    th = open(os.path.join(repo, TESTS, "test_data_hashes.py"), encoding="utf-8").read()
    runs = re.findall(r'_run\(\[rep / "round5/l6_check\.py", "--eval-sets", ([^,]+),', th)
    print(f"  tests/test_data_hashes.py still runs round5/l6_check.py with --eval-sets {runs} (round-2 observation 1, pending Review Gate)")
    return bool(ok)


run(main)
