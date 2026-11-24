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
