"""R6b-1 (round 6, re-audit of 2620f306): static audit of reports/round6/guard_ab.sh and guard_fail.sh.
Reads both revisions with `git show` and analyses the text line by line. Nothing of the Executor is executed,
sourced, imported or copied. Data Auditor's own script. Exceptions -> RESULT: FAIL (r6_guard).

For each harness:
  1. line diff old -> new (difflib, no autojunk); every non-equal block printed. Expected change set, nothing else:
       (a) one block inserted directly before `set -u`: comment lines plus exactly three code lines
           (flag = 0, the EXIT handler definition, `trap <handler> EXIT`);
       (b) one line inserted directly after `set -u`: `if [ $# -ne N ]; then ... exit 2; fi`, N = highest positional
           parameter the script uses;
       (c) the old last line `[ COND ]` replaced by: flag = 1, `if [ COND ]; then echo "RESULT: PASS"; exit 0; fi`,
           `echo "RESULT: FAIL"`, `exit 1`, with COND textually identical to the old one;
       and equal lines == old line count - 1 (only the old last line removed).
  2. structure of the new text (comments stripped):
       - the only code lines before `trap ... EXIT` are the flag assignment and the handler definition;
       - exactly one `trap` statement, no `set -e` / `set -o errexit` / `exec` / `source` / `.` / background `&`;
       - the handler, statement by statement: first statement captures $?; if the flag is 0 it prints RESULT: FAIL and
         turns a 0 status into 1; last statement exits with the captured status;
       - every assignment of the flag, every `exit` outside the handler, with the flag value in force at that line
         and whether a RESULT line is printed before it on the same path;
       - set -u: every variable referenced has an assignment on an earlier line (or earlier on the same line);
         positional parameters are first used after the $# check; the variables used after `flag = 1` are assigned
         at top level (loop depth 0), so `set -u` cannot stop the script between `flag = 1` and the RESULT line.
PASS iff 1 and 2 hold for both files.
usage: python -I r6b_harness_static.py <repo_root> <old_rev> <new_rev>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import difflib, hashlib, re, subprocess
from r6_guard import run

FILES = ["metrix/e1-pilot/reports/round6/guard_ab.sh", "metrix/e1-pilot/reports/round6/guard_fail.sh"]
SPECIAL = {"#", "?", "@", "*", "$", "!", "-", "0"}


def show(repo, rev, path):
    return subprocess.check_output(["git", "-C", repo, "show", f"{rev}:{path}"]).decode("utf-8")


def code_of(line):
    """Line without a trailing comment (a '#' that starts the line or follows whitespace, outside quotes)."""
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            out.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t") and not line[max(0, i - 2):i].endswith("${"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def split_top(s):
    """Split a one-line shell body at ';' outside quotes and outside [ ] / $( ) nesting."""
    parts, cur, q, depth = [], [], None, 0
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "'\"":
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == ";" and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def refs(code):
    """Variable names read in a code line: $name, ${name...}, ${#name[...]}, and bare names inside $(( ))."""
    names = []
    s = re.sub(r"'[^']*'", "''", code)          # single-quoted text is literal
    for m in re.finditer(r"\$\{#?([A-Za-z_][A-Za-z0-9_]*)|\$([A-Za-z_][A-Za-z0-9_]*)|\$\{?([0-9#?@*$!-])", s):
        names.append(m.group(1) or m.group(2) or m.group(3))
    for m in re.finditer(r"\$\(\((.*?)\)\)", s):
        for b in re.finditer(r"(?<![\$\{#\w])([A-Za-z_][A-Za-z0-9_]*)", re.sub(r"\$\{[^}]*\}", "", m.group(1))):
            names.append(b.group(1))
    return names


def assigns(code):
    """Names assigned in a code line: NAME=..., `read -r a b c`, `for x in`, also after ';' or 'then'/'else'."""
    out = []
    for part in split_top(code):
        p = re.sub(r"^(if .*?; then|then|else|do)\s+", "", part)
        for m in re.finditer(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=(?!=)", " " + p):
            out.append(m.group(1))
        # `read` may be preceded by environment assignments for that command only, e.g. IFS='|' read -r a b c
        m = re.match(r"\s*(?:[A-Za-z_]\w*=\S*\s+)*read\s+(?:-r\s+)?([A-Za-z_ ][A-Za-z0-9_ ]*?)\s*(?:<<<|<|$)", p)
        if m:
            out += m.group(1).split()
        m = re.match(r"\s*for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b", p)
        if m:
            out.append(m.group(1))
    return out


def audit(repo, old_rev, new_rev, path):
    return audit_texts(show(repo, old_rev, path), show(repo, new_rev, path), path, old_rev[:8], new_rev[:8])


def audit_texts(old, new, path, old_label, new_label):
    ol, nl = old.split("\n"), new.split("\n")
    if ol and ol[-1] == "":
        ol = ol[:-1]
    if nl and nl[-1] == "":
        nl = nl[:-1]
    print(f"## {path}")
    print(f"   old {old_label}: {len(ol)} lines, sha256 {hashlib.sha256(old.encode()).hexdigest()}")
    print(f"   new {new_label}: {len(nl)} lines, sha256 {hashlib.sha256(new.encode()).hexdigest()}")
    sm = difflib.SequenceMatcher(None, ol, nl, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
    n_equal = sum(i2 - i1 for t, i1, i2, _, _ in sm.get_opcodes() if t == "equal")
    print(f"   1. line diff: equal lines {n_equal} (old lines - 1 = {len(ol) - 1}); non-equal blocks {len(ops)}")
    for t, i1, i2, j1, j2 in ops:
        print(f"      {t} old {i1 + 1}..{i2} -> new {j1 + 1}..{j2}")
        for k in range(i1, i2):
            print(f"        - {ol[k]}")
        for k in range(j1, j2):
            print(f"        + {nl[k]}")
    ok_eq = n_equal == len(ol) - 1
    # (a) block before set -u
    su_new = [i for i, l in enumerate(nl) if code_of(l) == "set -u"]
    su_old = [i for i, l in enumerate(ol) if code_of(l) == "set -u"]
    ok_a = ok_b = ok_c = False
    cond_old = cond_new = None
    code = []
    if len(su_new) == 1 and len(su_old) == 1 and len(ops) == 3:
        t, i1, i2, j1, j2 = ops[0]
        blk = nl[j1:j2]
        code = [code_of(l) for l in blk if code_of(l)]
        ok_a = (t == "insert" and j2 == su_new[0] and i1 == su_old[0] and len(code) == 3
                and re.fullmatch(r"([A-Za-z_]\w*)=0", code[0]) is not None
                and re.match(r"([A-Za-z_]\w*)\(\)\s*\{", code[1]) is not None
                and re.fullmatch(r"trap ([A-Za-z_]\w*) EXIT", code[2]) is not None
                and all(l.startswith("#") or code_of(l) in code for l in blk))
        print(f"      (a) block inserted directly before `set -u`, comments + [flag=0, handler def, trap EXIT]: {ok_a} "
              f"| code lines {code}")
        t, i1, i2, j1, j2 = ops[1]
        pos = sorted({int(x) for l in nl for x in re.findall(r"\$\{?([1-9])\b", code_of(l))})
        nmax = max(pos) if pos else 0
        m = re.fullmatch(r"if \[ \$# -ne (\d+) \]; then echo \"usage: [^\"]*\" >&2; exit (\d+); fi", nl[j1]) if j2 - j1 == 1 else None
        ok_b = (t == "insert" and j1 == su_new[0] + 1 and m is not None and int(m.group(1)) == nmax and m.group(2) != "0")
        print(f"      (b) one line inserted directly after `set -u`: $# check against N={m.group(1) if m else None}, "
              f"exit {m.group(2) if m else None}; positional parameters used {pos} (max {nmax}): {ok_b}")
        t, i1, i2, j1, j2 = ops[2]
        mo = re.fullmatch(r"\[ (.*) \]", ol[i1]) if i2 - i1 == 1 else None
        rep = nl[j1:j2]
        mn = re.fullmatch(r"if \[ (.*) \]; then echo \"RESULT: PASS\"; exit 0; fi", rep[1]) if len(rep) == 4 else None
        cond_old, cond_new = (mo.group(1) if mo else None), (mn.group(1) if mn else None)
        fname = code[0][:-2] if ok_a else None          # code[0] is `NAME=0`
        ok_c = (t == "replace" and i2 == len(ol) and j2 == len(nl) and mo is not None and mn is not None
                and rep[0] == f"{fname}=1" and rep[2] == 'echo "RESULT: FAIL"' and rep[3] == "exit 1"
                and cond_old == cond_new)
        print(f"      (c) old last line replaced by [flag=1, if [COND] PASS exit 0, echo FAIL, exit 1]: {ok_c}")
        print(f"          old COND: {cond_old!r}")
        print(f"          new COND: {cond_new!r} | identical: {cond_old == cond_new}")
        print(f"          old: last command `[ COND ]` -> script exit status 0 if COND true, 1 if false; no output line")
        print(f"          new: COND true -> 'RESULT: PASS', exit 0; COND false -> 'RESULT: FAIL', exit 1 (same codes, one added line)")
    else:
        print(f"      unexpected shape: `set -u` lines old {su_old} new {su_new}, non-equal blocks {len(ops)}")
    ok1 = ok_eq and ok_a and ok_b and ok_c
    print(f"   1 summary: equal lines == old - 1: {ok_eq}; (a) {ok_a}; (b) {ok_b}; (c) {ok_c} -> {ok1}")

    # 2. structure of the new text
    codes = [(i + 1, code_of(l)) for i, l in enumerate(nl)]
    codes = [(n, c) for n, c in codes if c and not c.startswith("#!")]
    traps = [(n, c) for n, c in codes if re.match(r"\s*trap\b", c)]
    tm = re.fullmatch(r"trap ([A-Za-z_]\w*) EXIT", traps[0][1]) if len(traps) == 1 else None
    handler = tm.group(1) if tm else None
    before = [c for n, c in codes if n < traps[0][0]] if traps else []
    hdef = [(n, c) for n, c in codes if re.match(rf"{handler}\(\)\s*\{{", c or "")] if handler else []
    flagm = re.fullmatch(r"([A-Za-z_]\w*)=0", before[0]) if before else None
    flag = flagm.group(1) if flagm else None
    ok_order = len(before) == 2 and flag is not None and len(hdef) == 1 and before[1] == hdef[0][1]
    print(f"   2. trap statements: {traps}")
    print(f"      code lines before the trap: {before} | only flag=0 and the handler definition: {ok_order}")
    forbidden = {k: [n for n, c in codes if re.search(p, c)] for k, p in {
        "set -e / errexit": r"\bset\s+-[a-zA-Z]*e|\bset\s+-o\s+errexit", "exec": r"(^|[;&|]\s*)exec\b",
        "source / .": r"(^|[;&|]\s*)(source|\.)\s", "background &": r"[^&>]&\s*($|[^&>])", "return": r"\breturn\b",
        "kill": r"\bkill\b"}.items()}
    ok_forb = all(not v for v in forbidden.values())
    print(f"      forbidden constructs (line numbers): {forbidden} | none: {ok_forb}")
    ok_h = False
    if hdef:
        body = re.fullmatch(rf"{handler}\(\)\s*\{{\s*(.*?)\s*;?\s*\}}", hdef[0][1])
        stmts = split_top(body.group(1)) if body else []
        print(f"      handler {handler} (line {hdef[0][0]}), statements:")
        for s in stmts:
            print(f"        {s}")
        cap = re.fullmatch(r"([A-Za-z_]\w*)=\$\?", stmts[0]) if stmts else None
        st = cap.group(1) if cap else None
        mid = stmts[1:-1]
        cond = re.fullmatch(rf'if \[ "\${flag}" = 0 \]; then echo "RESULT: FAIL"; \[ "\${st}" = 0 \] && {st}=1; fi', "; ".join(mid)) if st else None
        last = stmts[-1] == f'exit "${st}"' if stmts else False
        ok_h = cap is not None and cond is not None and last
        print(f"        first statement captures $? into {st}: {cap is not None} | if flag 0: print RESULT: FAIL and status 0 -> 1: "
              f"{cond is not None} | last statement exit \"${st}\": {last} -> {ok_h}")
    fl = [(n, c) for n, c in codes if re.fullmatch(rf"{flag}=\S+", c)] if flag else []
    ok_flag = [c for _, c in fl] == [f"{flag}=0", f"{flag}=1"]
    print(f"      assignments of {flag}: {fl} | exactly [=0, =1]: {ok_flag}")
    set1 = fl[1][0] if len(fl) == 2 else None
    exits = []
    for n, c in codes:
        if hdef and n == hdef[0][0]:
            continue
        for part in split_top(c):
            for m in re.finditer(r"(?:^|then\s+|else\s+|&&\s*|\|\|\s*)exit(?:\s+(\S+))?", part):
                exits.append((n, m.group(1)))
    ok_exits = True
    for n, arg in exits:
        fv = 1 if set1 and n > set1 else 0
        printed = None
        if fv == 1:
            line = dict(codes)[n]
            printed = 'echo "RESULT: ' in line.split("exit")[0] or (n - 1 in dict(codes) and dict(codes)[n - 1].startswith('echo "RESULT: '))
            good = printed and arg is not None and ((arg == "0" and "RESULT: PASS" in (line + dict(codes).get(n - 1, ""))) or arg == "1")
        else:
            good = arg not in (None, "0")
        ok_exits &= bool(good)
        print(f"      exit at line {n} with argument {arg}: flag in force {fv} -> "
              + ("handler prints RESULT: FAIL; status kept (non-zero)" if fv == 0 else f"RESULT line printed before it: {printed}")
              + f" | ok: {bool(good)}")
    # 2c. set -u: every variable read has been assigned earlier
    defined, depth, bad, depth_of = {flag} if flag else set(), 0, [], {}
    check_line = [n for n, c in codes if re.match(r"if \[ \$# -ne", c)]
    pos_first = min([n for n, c in codes if re.search(r"\$\{?[1-9]", c)] or [0])
    for n, c in codes:
        if hdef and n == hdef[0][0]:
            continue                                    # handler: reads only the flag (assigned first) and its own status var
        for part in split_top(c):
            a_here = assigns(part)
            for r in refs(part):
                if r in SPECIAL or r.isdigit() or r in defined or r in a_here and re.search(rf"\b{r}=", part) and \
                        part.find(f"{r}=") < max(part.find("$" + r), part.find("${" + r)):
                    continue
                if r in a_here and re.match(r"\s*(for|read)\b", part):
                    continue
                bad.append((n, r))
            for a in a_here:
                defined.add(a)
                depth_of.setdefault(a, depth)
        if re.search(r"(^|;\s*)do\s*$", c):
            depth += 1
        if re.fullmatch(r"done", c):
            depth -= 1
    print(f"      set -u: variables read before any assignment: {bad} | loop depth at end {depth}")
    ok_pos = bool(check_line) and pos_first > check_line[0]
    print(f"      first use of a positional parameter at line {pos_first}; $# check at line {check_line} -> check first: {ok_pos}")
    after = sorted({r for n, c in codes if set1 and n >= set1 for r in refs(c)} - SPECIAL)
    top = {r: depth_of.get(r) for r in after}
    ok_after = all(v == 0 for v in top.values())
    print(f"      variables read after {flag}=1 (line {set1}): {after}; loop depth of first assignment {top} -> all top level: {ok_after}")
    ok2 = ok_order and ok_forb and ok_h and ok_flag and ok_exits and not bad and depth == 0 and ok_pos and ok_after and len(traps) == 1
    print(f"   2 summary -> {ok2}")
    return ok1 and ok2


def main():
    repo, old_rev, new_rev = sys.argv[1:4]
    for rev in (old_rev, new_rev):
        full = subprocess.check_output(["git", "-C", repo, "rev-parse", "--verify", rev + "^{commit}"], text=True).strip()
        print(f"revision {rev} -> commit {full}")
    ch = subprocess.check_output(["git", "-C", repo, "diff", "--name-status", "--no-renames", old_rev, new_rev], text=True)
    print("files changed old..new:")
    for l in ch.strip().split("\n"):
        print("   " + l)
    res = {f: audit(repo, old_rev, new_rev, f) for f in FILES}
    print("per file:", {os.path.basename(k): v for k, v in res.items()})
    return all(res.values())


if __name__ == "__main__":
    run(main)
