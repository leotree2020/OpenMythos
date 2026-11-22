"""R6-E (round 6, item 2): static audit of the Executor's script changes. Reads the source of both revisions with
`git show` and parses it with ast; nothing of the Executor is imported, called, executed or copied.
Data Auditor's own script. Exceptions -> RESULT: FAIL (r6_guard).

For every .py / .sh under metrix/e1-pilot/reports at <new_rev>:
  1. guarded = a module-level `def run_guarded` and a `if __name__ == "__main__":` block that is exactly run_guarded(main).
  2. for guarded files that exist at <old_rev>: the module AST without run_guarded and without the __main__ block
     (and, where the new version wraps the old __main__ body in a new `def main()`, that body moved back) must be
     identical to the old module AST without its __main__ block (ast.dump, no line numbers). Reported with and without
     docstrings. l6_check.py is expected to differ (its logic changed in round 6) and is listed node by node.
  3. run_guarded: the same AST in every guarded file; its source and its handler structure are printed.
  4. every sys.exit / SystemExit inside main code (outside run_guarded), with its argument, the enclosing function,
     and whether that function prints a "RESULT" line: exit code 1 passes through run_guarded without a RESULT line.
  5. module-level statements other than imports, defs, constant assignments and the __main__ block (they run
     outside the guard).
  6. l6_check.py at <new_rev>: JUDGED, the verdict expression, the "test rows decoded" print and its argument, the
     decode counter, the split-reading loop.
  7. scripts without the guard: first docstring / comment line, verdict markers, exit behaviour.
PASS iff 1-3 hold for all guarded files (l6_check.py excepted from 2) and 6 shows the round-6 changes.
usage: python -I r6_guard_audit.py <repo_root> <old_rev> <new_rev>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, re, subprocess
from r6_guard import run

P = "metrix/e1-pilot/reports/"


def show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def is_main_if(n):
    return (isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name)
            and n.test.left.id == "__name__" and len(n.test.comparators) == 1
            and isinstance(n.test.comparators[0], ast.Constant) and n.test.comparators[0].value == "__main__")


def strip_doc(body):
    out = []
    for n in body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            n = ast.fix_missing_locations(n)
            b = n.body[1:] if n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) \
                and isinstance(n.body[0].value.value, str) else n.body
            n = type(n)(**{**{f: getattr(n, f) for f in n._fields}, "body": strip_doc(b) or [ast.Pass()]})
        out.append(n)
    return out


def dump_body(body, nodoc):
    if nodoc:
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        body = strip_doc(body)
    return [ast.dump(n, include_attributes=False) for n in body]


def name_of(n):
    if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
        return f"def {n.name}"
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        return "import " + ", ".join(a.name for a in n.names)
    if isinstance(n, ast.Assign):
        return "assign " + ", ".join(ast.unparse(t) for t in n.targets)
    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
        return "docstring"
    return type(n).__name__ + " " + ast.unparse(n)[:60]


def exits(tree):
    """(function, line, form, argument node) for sys.exit(...), exit(...), raise SystemExit(...)."""
    found = []

    def walk(node, fn):
        for ch in ast.iter_child_nodes(node):
            f = ch.name if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            if isinstance(ch, ast.Call) and ast.unparse(ch.func) in ("sys.exit", "exit", "quit"):
                found.append((fn, ch.lineno, "sys.exit", ch.args[0] if ch.args else None))
            if isinstance(ch, ast.Raise) and isinstance(ch.exc, ast.Call) and ast.unparse(ch.exc.func) == "SystemExit":
                found.append((fn, ch.lineno, "raise SystemExit", ch.exc.args[0] if ch.exc.args else None))
            walk(ch, f)
    walk(tree, "<module>")
    return found


def exit_kind(node):
    """How run_guarded treats the exit: a str code -> RESULT: FAIL printed, exit 1; int 0/1 or None -> re-raised unchanged."""
    if node is None:
        return "no argument (code None) -> passes through the guard unchanged, exit 0"
    if isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str)) or (
            isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)):
        return "str code -> guard prints the message and RESULT: FAIL, exit 1"
    ints = [c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and type(c.value) is int]
    if isinstance(node, ast.IfExp) and isinstance(node.body, ast.Constant) and isinstance(node.orelse, ast.Constant):
        return f"int {sorted(ints)} -> passes through the guard unchanged"
    return "value of an expression/call (int 0/1 at run time) -> passes through the guard unchanged"


def prints_result(fn_node):
    return any(isinstance(c, ast.Call) and ast.unparse(c.func) == "print" and "RESULT" in ast.unparse(c)
               for c in ast.walk(fn_node))


def main():
    repo, old_rev, new_rev = sys.argv[1:4]
    ok = True
    for rev in (old_rev, new_rev):            # an unknown revision raises here (CalledProcessError -> RESULT: FAIL)
        full = subprocess.check_output(["git", "-C", repo, "rev-parse", "--verify", rev + "^{commit}"], text=True).strip()
        print(f"revision {rev} -> commit {full}")
    added = {l.split("\t", 1)[1] for l in subprocess.check_output(
        ["git", "-C", repo, "diff", "--name-status", "--no-renames", old_rev, new_rev, "--", P], text=True).splitlines()
        if l.startswith("A\t")}
    print(f"files added under {P} in {old_rev[:8]}..{new_rev[:8]}: {sorted(added)}")
    files = subprocess.check_output(["git", "-C", repo, "ls-tree", "-r", "--name-only", new_rev, "--", P], text=True).split()
    py = [f for f in files if f.endswith(".py")]
    sh = [f for f in files if f.endswith(".sh")]
    print(f"scripts under {P} at {new_rev[:8]}: {len(py)} .py, {len(sh)} .sh")
    guarded, unguarded, rg_dumps = [], [], {}
    for f in py:
        src = show(repo, new_rev, f)
        t = ast.parse(src)
        rg = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "run_guarded"]
        mains = [n for n in t.body if is_main_if(n)]
        if rg:
            guarded.append(f)
            rg_dumps[f] = ast.dump(rg[0], include_attributes=False)
            mb = [ast.unparse(s) for s in mains[0].body] if mains else None
            good = mb == ["run_guarded(main)"] and any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in t.body)
            ok &= good
            print(f"  GUARDED   {f[len(P):]:40s} __main__ block {mb} | def main present and block == run_guarded(main): {good}")
        else:
            unguarded.append(f)
    print(f"guarded: {len(guarded)} | unguarded .py: {len(unguarded)}")

    print("== 2. old vs new AST without run_guarded and the __main__ block")
    for f in guarded:
        old_src, new_src = show(repo, old_rev, f), show(repo, new_rev, f)
        if old_src is None:
            listed = f in added
            ok &= listed
            print(f"  {f[len(P):]:40s} not present at {old_rev[:8]}; listed as added (A) in git diff: {listed}; no old version to compare")
            continue
        ot, nt = ast.parse(old_src), ast.parse(new_src)
        old_main = [n for n in ot.body if is_main_if(n)]
        ob = [n for n in ot.body if not is_main_if(n)]
        nb = [n for n in nt.body if not is_main_if(n) and not (isinstance(n, ast.FunctionDef) and n.name == "run_guarded")]
        moved = ""
        old_has_main = any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in ot.body)
        if not old_has_main:          # new `def main()` wraps the old __main__ body
            nm = [n for n in nb if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
            same_body = [ast.dump(s, include_attributes=False) for s in nm.body] == \
                        [ast.dump(s, include_attributes=False) for s in old_main[0].body]
            nb = [n for n in nb if n is not nm]
            moved = f" | new def main() body == old __main__ body: {same_body}"
            ok &= same_body
        else:
            om = [ast.unparse(s) for s in old_main[0].body] if old_main else None
            moved = f" | old __main__ block {om}"
        eq_doc = dump_body(ob, False) == dump_body(nb, False)
        eq_nodoc = dump_body(ob, True) == dump_body(nb, True)
        print(f"  {f[len(P):]:40s} identical incl. docstrings: {eq_doc} | identical without docstrings: {eq_nodoc}{moved}")
        if f.endswith("round5/l6_check.py"):
            od, nd = dict(zip(map(name_of, ob), dump_body(ob, True))), dict(zip(map(name_of, nb), dump_body(nb, True)))
            for k in sorted(set(od) | set(nd)):
                st = "same" if od.get(k) == nd.get(k) else ("added" if k not in od else "removed" if k not in nd else "CHANGED")
                if st != "same":
                    print(f"      l6_check.py top-level node {k!r}: {st}")
        else:
            ok &= eq_doc

    print("== 3. run_guarded")
    variants = sorted(set(rg_dumps.values()))
    print(f"distinct run_guarded ASTs across {len(rg_dumps)} guarded files: {len(variants)}")
    ok &= len(variants) == 1
    t = ast.parse(show(repo, new_rev, guarded[0]))
    rg = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "run_guarded"][0]
    print("source (ast.unparse, from %s):" % guarded[0][len(P):])
    for line in ast.unparse(rg).split("\n"):
        print("    " + line)
    tr = [n for n in rg.body if isinstance(n, ast.Try)][0]
    print("try body:", [ast.unparse(s) for s in tr.body], "| else:", [ast.unparse(s) for s in tr.orelse],
          "| finally:", [ast.unparse(s) for s in tr.finalbody])
    for h in tr.handlers:
        print(f"  handler {ast.unparse(h.type)} as {h.name}: statements {[ast.unparse(s).split(chr(10))[0] for s in h.body]}")

    print("== 4. exits inside the guarded scripts (outside run_guarded)")
    for f in guarded:
        tt = ast.parse(show(repo, new_rev, f))
        fns = {n.name: n for n in ast.walk(tt) if isinstance(n, ast.FunctionDef)}
        for fn, line, form, node in exits(tt):
            if fn == "run_guarded":
                continue
            print(f"  {f[len(P):]:36s} line {line:4d} in {fn}: {form}({ast.unparse(node) if node is not None else ''}) "
                  f"[{exit_kind(node)}] | {fn} prints a RESULT line: {prints_result(fns[fn]) if fn in fns else 'n/a'}")
        rets = []
        for n in ast.walk(tt):
            if isinstance(n, ast.FunctionDef) and n.name not in ("run_guarded", "main"):
                rs = [ast.unparse(r.value) for r in ast.walk(n) if isinstance(r, ast.Return) and r.value is not None]
                if any(re.search(r"\b[01]\b", r) for r in rs) and any(
                        a is not None and n.name in ast.unparse(a) for _, _, _, a in exits(tt)):
                    rets.append((n.name, rs, prints_result(n)))
        for name, rs, pr in rets:
            print(f"      {f[len(P):]} function {name} (its value goes to sys.exit): returns {rs} | prints a RESULT line: {pr}")

    print("== 5. module-level statements that run outside the guard (beyond stdlib imports, defs, constants)")
    stdlib = set(sys.stdlib_module_names)
    for f in guarded:
        tt = ast.parse(show(repo, new_rev, f))
        risky = []
        for n in tt.body:
            if is_main_if(n) or isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                continue
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
                continue
            if isinstance(n, ast.Import) and all(a.name.split(".")[0] in stdlib for a in n.names):
                continue
            if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] in stdlib:
                continue
            if isinstance(n, ast.Assign) and all(isinstance(x, ast.Constant) for x in ast.walk(n.value) if isinstance(x, ast.expr)
                                                 and not isinstance(x, (ast.Tuple, ast.List, ast.Dict, ast.Set))):
                continue
            risky.append(f"line {n.lineno}: {ast.unparse(n)[:110]}")
        print(f"  {f[len(P):]:40s} {risky if risky else 'none'}")

    print("== 6. l6_check.py at", new_rev[:8])
    l6 = ast.parse(show(repo, new_rev, P + "round5/l6_check.py"))
    consts = {t.id: ast.unparse(n.value) for n in l6.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    print("  module constants:", consts)
    main_fn = [n for n in l6.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    oks = [ast.unparse(n) for n in ast.walk(main_fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ok" for t in n.targets)]
    print("  verdict assignment(s):", oks)
    trd = [ast.unparse(n) for n in ast.walk(main_fn) if isinstance(n, ast.Call) and ast.unparse(n.func) == "print"
           and "test rows decoded" in ast.unparse(n)]
    print("  print(s) containing 'test rows decoded':", trd)
    dec = [n for n in ast.walk(main_fn) if isinstance(n, ast.FunctionDef)]
    for d in dec:
        print(f"  nested def {d.name}:", " ; ".join(ast.unparse(s) for s in d.body))
    sexit = [ast.unparse(n) for n in ast.walk(main_fn) if isinstance(n, ast.If) and "decoded_by_split" in ast.unparse(n.test)]
    print("  checks on the decode counter:", sexit)
    loops = [n for n in ast.walk(main_fn) if isinstance(n, ast.For) and "enumerate(fh" in ast.unparse(n.iter)]
    print("  eval_sets loop body (statement order):")
    for s in loops[0].body:
        print("    " + ast.unparse(s).split("\n")[0])
    loads_lines = [n.lineno for n in ast.walk(loops[0]) if isinstance(n, ast.Call) and ast.unparse(n.func) == "json.loads"]
    cont_lines = [n.lineno for n in ast.walk(loops[0]) if isinstance(n, ast.If) and "split != 'dev'" in ast.unparse(n.test)]
    print(f"  json.loads at line(s) {loads_lines}; `if split != 'dev': continue` at line(s) {cont_lines}; "
          f"parse only after the dev filter: {bool(cont_lines) and all(l > max(cont_lines) for l in loads_lines)}")
    units = [ast.unparse(n) for n in ast.walk(main_fn) if isinstance(n, ast.Call) and "print" == ast.unparse(n.func)
             and ("report only" in ast.unparse(n) or "L6 (DEV part)" in ast.unparse(n))]
    print("  L6 verdict / report prints:", units)
    ok &= consts.get("JUDGED") == "'ws'" and oks == ["ok = result[JUDGED] == 0"] and \
        any("decoded_by_split['test']" in x for x in trd) and bool(sexit)

    print("== 7. scripts without the guard")
    for f in unguarded + sh:
        src = show(repo, new_rev, f)
        first = ""
        if f.endswith(".py"):
            d = ast.get_docstring(ast.parse(src))
            first = (d or "").split("\n")[0] or "(no docstring) " + src.split("\n")[0][:70]
        else:
            first = next((l for l in src.split("\n")[1:] if l.startswith("#")), "")[:110]
        marks = {k: len(re.findall(k, src)) for k in (r"RESULT", r"\bPASS\b|\bFAIL\b", r"sys\.exit|^\s*exit\b|^\[ ")}
        tail = src.rstrip().split("\n")[-1][:80]
        print(f"  {f[len(P):]:36s} | {first[:100]}")
        print(f"  {'':36s} | markers {marks} | set -e: {'set -e' in src} | last line: {tail}")
    return bool(ok)


if __name__ == "__main__":
    run(main)
