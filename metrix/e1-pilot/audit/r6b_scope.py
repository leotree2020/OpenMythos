"""R6b-5 (round 6, re-audit of 2620f306): which scripts at <rev> are check scripts by the Executor's own standard,
and are they all guarded? Reads sources with `git show` (ast for .py, text for .sh); nothing is executed or imported.
Data Auditor's own script. Exceptions -> RESULT: FAIL (r6_guard).

Standard (ROUND6_REPORT.md, task 2, "范围"): a check script outputs a pass/fail verdict: a RESULT line, PASS/FAIL or
inside/OUTSIDE wording, or an exit code set by a verdict.
Per script (every file under metrix/ at <rev> ending in .py / .sh or starting with "#!"):
  - output strings: string constants and f-string parts outside docstrings and comments (.py), echo/printf text
    outside comments (.sh); verdict words found in them, with the strings;
  - exits: sys.exit / exit / raise SystemExit (.py) or exit / a final `[ ]` test (.sh), each classified as
    verdict exit (non-constant code, or exit 1 under a condition, or a final test), message exit (str code),
    pass-through (`exit "$rc"` of a wrapped command), or constant;
  - guard: .py `def run_guarded` + `if __name__ == "__main__": run_guarded(main)`; .sh `trap F EXIT` whose F prints
    RESULT: FAIL, plus a RESULT echo; auditor scripts: `run(main)` from r6_guard.
  - class: CHECK (verdict words in output or a verdict exit), MESSAGE-EXIT ONLY, or NO VERDICT.
The Executor's lists are parsed from the "范围" paragraph of the report draft (included / excluded file names).
PASS iff every Executor script classed CHECK is guarded, and the Executor's included list == my CHECK set.
usage: python -I r6b_scope.py <repo_root> <rev> <report_md>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, re, subprocess
from r6_guard import run

WORDS = re.compile(r"RESULT|\bPASS\b|\bFAIL\b|\binside\b|\bOUTSIDE\b")


def git(repo, *a):
    return subprocess.check_output(["git", "-C", repo] + list(a)).decode("utf-8")


def docstring_nodes(tree):
    ids = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            f = n.body[0]
            if isinstance(f, ast.Expr) and isinstance(f.value, ast.Constant) and isinstance(f.value.value, str):
                ids.add(id(f.value))
    return ids


def py_info(src):
    t = ast.parse(src)
    docs = docstring_nodes(t)
    strings = [n.value for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]
    hits = sorted({s.strip()[:90] for s in strings if WORDS.search(s)})
    parents = {}
    for p in ast.walk(t):
        for c in ast.iter_child_nodes(p):
            parents[id(c)] = p
    exits = []
    for n in ast.walk(t):
        arg, form = None, None
        if isinstance(n, ast.Call) and ast.unparse(n.func) in ("sys.exit", "exit", "quit"):
            form, arg = "sys.exit", (n.args[0] if n.args else None)
        elif isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and ast.unparse(n.exc.func) == "SystemExit":
            form, arg = "raise SystemExit", (n.exc.args[0] if n.exc.args else None)
        if not form:
            continue
        fn, p, cond = None, n, False
        while id(p) in parents:
            p = parents[id(p)]
            if isinstance(p, ast.If) and not (isinstance(p.test, ast.Compare) and ast.unparse(p.test.left) == "__name__"):
                cond = True
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn is None:
                fn = p.name
        if fn == "run_guarded":
            continue
        if arg is None:
            kind = "constant (None)"
        elif isinstance(arg, ast.Constant) and isinstance(arg.value, str) or isinstance(arg, ast.JoinedStr) or (
                isinstance(arg, ast.BinOp) and isinstance(arg.left, ast.Constant) and isinstance(arg.left.value, str)):
            kind = "message exit"
        elif isinstance(arg, ast.Constant) and type(arg.value) is int:
            kind = "verdict exit" if (cond and arg.value != 0) else f"constant ({arg.value})"
        else:
            kind = "verdict exit"
        exits.append((n.lineno, fn, form, ast.unparse(arg) if arg is not None else "", kind))
    rg = any(isinstance(n, ast.FunctionDef) and n.name == "run_guarded" for n in t.body)
    mains = [n for n in t.body if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
             and ast.unparse(n.test) in ('__name__ == "__main__"', "__name__ == '__main__'")]
    mb = [ast.unparse(s) for s in mains[0].body] if mains else None
    guard = "run_guarded(main)" if rg and mb == ["run_guarded(main)"] else ("r6_guard.run(main)" if mb == ["run(main)"] and
                                                                         "from r6_guard import run" in src else "none")
    asserts = sum(isinstance(n, ast.Assert) for n in ast.walk(t))
    return hits, exits, guard, mb, asserts


def strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t") and not line[max(0, i - 2):i].endswith("${"):
            return line[:i].rstrip()
    return line.rstrip()


def sh_info(src):
    code = [(k + 1, strip_comment(l)) for k, l in enumerate(src.split("\n"))]
    code = [(n, c) for n, c in code if c.strip() and not c.startswith("#!")]
    hits = sorted({m.group(0)[:90] for n, c in code for m in re.finditer(r"(?:echo|printf)\s+(\"[^\"]*\"|'[^']*')", c)
                   if WORDS.search(m.group(1))})
    exits = []
    traps = [c for n, c in code if re.match(r"\s*trap\s", c)]
    handler = re.match(r"\s*trap\s+(\w+)\s+EXIT", traps[0]).group(1) if traps and re.match(r"\s*trap\s+(\w+)\s+EXIT", traps[0]) else None
    for n, c in code:
        if handler and re.match(rf"\s*{handler}\(\)", c):
            continue
        for m in re.finditer(r"(?:^|;|then|else|&&|\|\|)\s*exit(?:\s+(\S+))?", c):
            a = (m.group(1) or "").rstrip(";")
            if a in ('"$rc"', "$rc", '"$?"', "$?"):
                kind = "pass-through of a wrapped command's status"
            elif a in ("0", ""):
                kind = "constant (0)"
            elif c.lstrip().startswith("if ") or n == code[-1][0] or re.search(r"then|&&|\|\|", c):
                kind = "verdict exit" if "usage" not in c else "argument-count exit"
            else:
                kind = "verdict exit"
            exits.append((n, a, kind))
    if re.fullmatch(r"\s*\[ .* \]\s*", code[-1][1]):
        exits.append((code[-1][0], code[-1][1].strip(), "verdict exit (final test sets the status)"))
    hdef = [c for n, c in code if handler and re.match(rf"\s*{handler}\(\)", c)]
    guard = "EXIT trap printing RESULT: FAIL" if hdef and 'echo "RESULT: FAIL"' in hdef[0] and any(
        'echo "RESULT: PASS"' in c for n, c in code) else "none"
    return hits, exits, guard, traps


def classify(hits, exits):
    if hits or any(k.startswith("verdict exit") for *_, k in exits):
        return "CHECK"
    if any(k == "message exit" for *_, k in exits):
        return "MESSAGE-EXIT ONLY"
    return "NO VERDICT"


def executor_lists(report):
    text = open(report, encoding="utf-8").read()
    para = text[text.index("- **范围**"):text.index("- **做法**")]
    inc, exc = set(), set()
    for line in para.split("\n"):
        names = set(re.findall(r"`(round\d/[\w.]+\.(?:py|sh))`", line))
        (exc if ("没有加的" in line or "不输出判定" in line) else inc).update(names)
    return inc, exc


def main():
    repo, rev, report = sys.argv[1:4]
    full = git(repo, "rev-parse", "--verify", rev + "^{commit}").strip()
    print(f"revision {rev} -> {full}")
    files = git(repo, "ls-tree", "-r", "--name-only", full, "--", "metrix").split("\n")
    scripts = []
    for f in files:
        if not f:
            continue
        if f.endswith((".py", ".sh")):
            scripts.append(f)
            continue
        if f.endswith((".md", ".txt", ".json", ".jsonl", ".diff")):
            continue
        head = subprocess.run(["git", "-C", repo, "show", f"{full}:{f}"], capture_output=True).stdout[:2]
        if head == b"#!":
            scripts.append(f)
    ex = [f for f in scripts if f.startswith("metrix/e1-pilot/reports/")]
    au = [f for f in scripts if f.startswith("metrix/e1-pilot/audit/")]
    other = [f for f in scripts if f not in ex and f not in au]
    print(f"scripts under metrix/ at {full[:8]}: {len(scripts)} (Executor reports/: {len(ex)}, auditor audit/: {len(au)}, other: {other})")
    outside = git(repo, "diff", "--name-status", "61d3c76705b28cc2ee334abc5bf1baaac4fc30dc", full, "--", ".", ":(exclude)metrix").strip()
    print(f"changed outside metrix/ since the baseline: {outside.split(chr(10))}")
    print("== Executor scripts (reports/)")
    mine = {}
    for f in ex:
        src = git(repo, "show", f"{full}:{f}")
        short = f[len("metrix/e1-pilot/reports/"):]
        if f.endswith(".py"):
            hits, exits, guard, mb, asserts = py_info(src)
            extra = f"__main__ block {mb} | asserts {asserts}"
        else:
            hits, exits, guard, traps = sh_info(src)
            extra = f"trap statements {traps}"
        cls = classify(hits, exits)
        mine[short] = (cls, guard)
        print(f"  {short}: class {cls} | guard {guard}")
        print(f"      verdict words in output strings: {hits[:6]}{' ...' if len(hits) > 6 else ''}")
        print(f"      exits: {exits}")
        print(f"      {extra}")
    inc, exc = executor_lists(report)
    check = {k for k, (c, g) in mine.items() if c == "CHECK"}
    unguarded_check = sorted(k for k in check if mine[k][1] == "none")
    print("== comparison with the Executor's lists (ROUND6_REPORT.md, task 2, 范围)")
    print(f"  Executor included ({len(inc)}): {sorted(inc)}")
    print(f"  Executor excluded ({len(exc)}): {sorted(exc)}")
    print(f"  my CHECK ({len(check)}): {sorted(check)}")
    print(f"  CHECK but not in the Executor's included list: {sorted(check - inc)}")
    print(f"  in the Executor's included list but not CHECK: {sorted(inc - check)}")
    print(f"  Executor scripts named in neither list: {sorted(set(mine) - inc - exc)} -> class {[mine[k] for k in sorted(set(mine) - inc - exc)]}")
    print(f"  included scripts without a guard: {sorted(k for k in inc if mine.get(k, ('', 'none'))[1] == 'none')}")
    print(f"  CHECK scripts without a guard: {unguarded_check}")
    print(f"  non-CHECK scripts by class: { {k: v[0] for k, v in mine.items() if v[0] != 'CHECK'} }")
    print("== auditor scripts (audit/; outside the Executor's standard as written, see its pending item 6)")
    for f in au:
        src = git(repo, "show", f"{full}:{f}")
        if f.endswith(".py"):
            hits, exits, guard, mb, asserts = py_info(src)
        else:
            hits, exits, guard, traps = sh_info(src)
        print(f"  {f[len('metrix/e1-pilot/audit/'):]:24s} class {classify(hits, exits):17s} guard {guard}")
    return not unguarded_check and check == inc


if __name__ == "__main__":
    run(main)
