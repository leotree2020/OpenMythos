"""R6b-4 (round 6, re-audit of 2620f306): the Executor's recorded harness outputs, before and after the fix.
Reads output files only (reports/round6/t2_*.txt); nothing of the Executor is executed or imported.
Data Auditor's own script. Exceptions -> RESULT: FAIL (r6_guard).

  1. the .py files the harnesses run are unchanged between the pre-fix run (work commit 481a6f0f) and 2620f306, and
     the working tree equals 2620f306 for them;
  2. for guard_ab.sh (t2_guard_normal.txt -> t2_guard_normal_rerun.txt) and guard_fail.sh (t2_guard_fail.txt ->
     t2_guard_fail_rerun.txt): the harness run block (from its `$ bash ...` line to its `exit=` line), with the OUT_DIR
     argument replaced by <OUT>, must differ only by one line `RESULT: PASS` appended at the end; exit codes equal;
     RESULT lines after = before + 1; the block's last line is the harness's own RESULT line;
  3. t2_harness_fail.txt: every recorded run, its output lines (or the RESULT / exit lines of piped runs), and the
     harness's own exit code where it is recorded (exit= of an unpiped run, harness_exit= otherwise).
PASS iff 1 and 2 hold and 3 shows RESULT: FAIL with a non-zero harness exit code for every failure run.
usage: python -I r6b_evidence.py <repo_root> <prefix_rev> <new_rev>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import difflib, re, shlex, subprocess
from r6_guard import run

R6 = "metrix/e1-pilot/reports/round6/"


def block(path, script):
    lines = open(path, encoding="utf-8").read().split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith(f"$ bash {R6}{script} ")]
    assert len(starts) == 1, (path, starts)
    s = starts[0]
    args = shlex.split(lines[s][2:])
    out_dir = args[3]                                    # bash, script, OLD, OUT, ...
    e = next(i for i in range(s + 1, len(lines)) if re.fullmatch(r"exit=\d+", lines[i]))
    body = [l.replace(out_dir, "<OUT>") for l in lines[s + 1:e]]
    return args, out_dir, body, int(lines[e][5:])


def main():
    repo, pre, new = sys.argv[1:4]
    ok = True
    os.chdir(repo)
    print("== 1. scripts run by the harnesses")
    d = subprocess.check_output(["git", "diff", "--name-status", pre, new, "--", "metrix/e1-pilot/reports/*.py",
                                 "metrix/e1-pilot/reports/**/*.py"], text=True).strip()
    w = subprocess.check_output(["git", "status", "--porcelain", "--", "metrix/e1-pilot/reports"], text=True).strip()
    wpy = [l for l in w.split("\n") if l.endswith(".py")] if w else []
    print(f"   .py under reports/ changed {pre[:8]}..{new[:8]}: {d.split(chr(10)) if d else []}")
    print(f"   working-tree status of .py under reports/ (untracked/modified): {wpy}")
    tracked_mod = [l for l in wpy if not l.startswith("??")]
    ok &= not d and not tracked_mod
    print(f"   no tracked .py changed: {not d and not tracked_mod}"
          + (" (untracked .py are not run by either harness)" if wpy else ""))
    print("== 2. pre-fix vs post-fix harness output")
    for script, before, after in (("guard_ab.sh", "t2_guard_normal.txt", "t2_guard_normal_rerun.txt"),
                                  ("guard_fail.sh", "t2_guard_fail.txt", "t2_guard_fail_rerun.txt")):
        a1, o1, b1, e1 = block(R6 + before, script)
        a2, o2, b2, e2 = block(R6 + after, script)
        same_args = [x for k, x in enumerate(a1) if k != 3] == [x for k, x in enumerate(a2) if k != 3]
        ops = [o for o in difflib.SequenceMatcher(None, b1, b2, autojunk=False).get_opcodes() if o[0] != "equal"]
        only_append = (len(ops) == 1 and ops[0][0] == "insert" and ops[0][1] == len(b1) and b2[ops[0][3]:ops[0][4]] == ["RESULT: PASS"])
        r1, r2 = sum(l.startswith("RESULT:") for l in b1), sum(l.startswith("RESULT:") for l in b2)
        summ = [l for l in b2 if re.match(r"(identical \(output and exit code\)|new scripts with non-zero exit)", l)]
        good = same_args and only_append and e1 == e2 and r2 == r1 + 1 and b2[-1] == "RESULT: PASS"
        ok &= good
        print(f"   {script}: {before} ({len(b1)} lines, exit {e1}) -> {after} ({len(b2)} lines, exit {e2})")
        print(f"      OUT_DIR {o1} -> {o2}; other arguments identical: {same_args}")
        print(f"      non-equal blocks after OUT_DIR normalisation: {[(t, i1, i2, j1, j2, b2[j1:j2]) for t, i1, i2, j1, j2 in ops]}")
        print(f"      only change = 'RESULT: PASS' appended at the end: {only_append} | RESULT lines {r1} -> {r2} | "
              f"last line {b2[-1]!r} | harness summary line {summ}")
        print(f"      -> {good}")
    print("== 3. t2_harness_fail.txt")
    lines = open(R6 + "t2_harness_fail.txt", encoding="utf-8").read().split("\n")
    runs, cur = [], None
    for l in lines:
        if l.startswith("$ "):
            cur = {"cmd": l[2:], "out": []}
            runs.append(cur)
        elif cur is not None and re.fullmatch(r"exit=\d+", l):
            cur["exit"] = int(l[5:])
            cur = None
        elif cur is not None:
            cur["out"].append(l)
    for k, r in enumerate(runs, 1):
        cmd = r["cmd"]
        inner = shlex.split(cmd)[2] if cmd.startswith("bash -c ") else cmd
        piped = "| grep" in inner
        script = re.search(r"guard_(ab|fail)\.sh", inner).group(0)
        nargs = len(shlex.split(inner.split("|")[0].split(">")[0])) - 2
        he = [int(x[13:]) for x in r["out"] if x.startswith("harness_exit=")]
        harness_exit = he[0] if he else (None if piped else r["exit"])
        res = [x for x in r["out"] if x.startswith("RESULT:")]
        last_result = [x for x in r["out"] if not x.startswith("harness_exit=")][-1]
        summ = [x for x in r["out"] if re.match(r"(identical \(output|new scripts with non-zero exit)", x)]
        print(f"   run {k}: {script} with {nargs} argument(s){' | piped into grep' if piped else ''}")
        if len(r["out"]) <= 3:
            print(f"      output: {r['out']}")
        print(f"      summary line: {summ} | RESULT lines {len(res)} | last line {last_result!r} | "
              f"recorded exit= {r['exit']} ({'grep' if piped else 'of the shell command'}) | harness exit code: {harness_exit}")
        good = last_result == "RESULT: FAIL" and (harness_exit is None or harness_exit != 0)
        if not piped and not he and nargs not in (6, 4):
            good &= harness_exit == 2 and r["out"][0].startswith(f"usage: bash {script}")
        print(f"      RESULT: FAIL last and harness exit non-zero (where recorded): {good}")
        ok &= good
    return bool(ok)


if __name__ == "__main__":
    run(main)
