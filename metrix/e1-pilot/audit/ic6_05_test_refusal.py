"""ic6_05 (implementation stage C, C1 second submission, fix commit (staged tree ae5fcb2f), round 1, task 3, black
box): my ic5_05_test_refusal.py with the comparison file of this round (reports/impl_c/c1b_04_checks_fix.txt); the
expectation is unchanged: every interpretation is ruled (pending() is empty, ic6_03 f), so the generator must refuse
because condition 2 does not hold (the Gate 0 record is not committed). Run the Executor's TEST generator once, exactly as instructed, and record that it
refuses in the current state:
    cd metrix/e1-pilot/src && <venv python> -m metrix_e1.test_data --inputs <inputs> --data <c1_data> --out <out_dir>
The generator is run as a subprocess (black box; nothing of it is imported here), with PYTHONDONTWRITEBYTECODE=1 so
that no .pyc file is written under src/.  Its stdout and stderr are printed line by line as they arrive; if a line
that only a generating run prints appears ("byte_sha256", "TEST part count", "ST10 record written", ...), the process
is killed at once and the run is reported as NOT REFUSED.
Before: <out_dir> must not exist and must lie outside the repository; precondition 2 cannot hold
(metrix/e1-pilot/results/gate0_record.json is not in HEAD and not in the working tree), so the run cannot reach the
TEST driver's checkout, commit-precondition or ST10-record checks either; snapshots of the data directory, of the input
directory, of `git status --porcelain --ignored --untracked-files=all -- metrix` and of every file under
metrix/e1-pilot/src including __pycache__.
After: exit code non-zero, last line "RESULT: FAIL", the refusal line present and naming the Gate 0 record; <out_dir>
not created; data dir unchanged, no test_qa.jsonl / general_test.jsonl in it; inputs, git status and the src tree
unchanged; no results directory, no ST10 record.
Data Auditor's own script; the Executor's module is only executed as the instructed black-box command.
usage: python -I ic6_05_test_refusal.py <repo_root> <venv_python> <inputs_dir> <data_dir> <out_dir (must not exist)>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shlex, subprocess
from ia_common import file_sha, run


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %r" % (args, r.stderr))
    return r

GEN_MARKERS = ("byte_sha256", "TEST part value", "TEST part count", "L6 TEST count", "leakage_test_report",
               "ST10 record written", "ST10:")


def tree_snapshot(root):
    out = {}
    for r, ds, fs in os.walk(root):
        for f in fs:
            p = os.path.join(r, f)
            st = os.stat(p)
            out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns, file_sha(p))
    return out


def main():
    repo, py, inputs, data, out = sys.argv[1:6]
    ok = True
    src = os.path.join(repo, "metrix/e1-pilot/src")
    print("== before")
    print(f"out_dir {out} exists: {os.path.exists(out)}")
    ok &= not os.path.exists(out)
    ro, oo = os.path.realpath(repo), os.path.realpath(out)
    outside = not (oo == ro or oo.startswith(ro + os.sep))
    print(f"out_dir outside the repository {ro}: {outside}")
    ok &= outside
    g0 = "metrix/e1-pilot/results/gate0_record.json"
    in_head = git(repo, "cat-file", "-e", f"HEAD:{g0}", check=False).returncode == 0
    in_wt = os.path.exists(os.path.join(repo, g0))
    print(f"{g0}: in HEAD {in_head} | in working tree {in_wt} | metrix/e1-pilot/results exists {os.path.exists(os.path.join(repo, 'metrix/e1-pilot/results'))}")
    if in_head or in_wt:
        print("precondition 2 could hold: the generator is NOT run")
        return False
    data_before = tree_snapshot(data)
    inputs_before = tree_snapshot(inputs)
    src_before = tree_snapshot(src)
    gs_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix")
    gs_before = git(repo, *gs_args).stdout.decode()
    print(f"data dir {data} files: {sorted(data_before)}")
    print(f"test_qa.jsonl / general_test.jsonl in the data dir: {[n for n in ('test_qa.jsonl', 'general_test.jsonl') if n in data_before]}")
    print(f"files under src (incl. __pycache__): {len(src_before)} | files under inputs: {len(inputs_before)}")

    cmd = [py, "-m", "metrix_e1.test_data", "--inputs", inputs, "--data", data, "--out", out]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    print("\n== run (once)")
    print(f"cwd {src}")
    print("$ " + " ".join(shlex.quote(c) for c in cmd))
    print("----- generator stdout+stderr begin -----")
    sys.stdout.flush()
    p = subprocess.Popen(cmd, cwd=src, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines, killed = [], False
    for line in p.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        print(line)
        sys.stdout.flush()
        if any(m in line for m in GEN_MARKERS):
            p.kill()
            killed = True
            print("!!! generation output seen: process killed")
            break
    rc = p.wait()
    print("----- generator stdout+stderr end -----")
    print(f"exit code {rc} | killed by the auditor {killed}")
    refused = (not killed and rc != 0 and lines and lines[-1] == "RESULT: FAIL"
               and any(x.startswith("TEST generator refused:") for x in lines))
    print(f"refused (non-zero exit, last line RESULT: FAIL, refusal line present): {bool(refused)}")
    ok &= bool(refused)
    exl = [ln for ln in open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c1b_04_checks_fix.txt"), encoding="utf-8").read().split("\n")
           if ln.startswith("TEST generator refused:")]
    mine = [x for x in lines if x.startswith("TEST generator refused:")]
    print(f"refusal line == the Executor's in c1b_04_checks_fix.txt ({exl}): {mine == exl}")
    ok &= mine == exl
    names_g0 = len(mine) == 1 and "gate0_record.json" in mine[0] and "not committed" in mine[0]
    print(f"the refusal names the Gate 0 record (condition 2, not committed), as expected with pending() empty: {names_g0}")
    ok &= names_g0

    print("\n== after")
    print(f"out_dir {out} exists: {os.path.exists(out)}")
    ok &= not os.path.exists(out)
    data_after = tree_snapshot(data)
    print(f"data dir unchanged (names, sizes, mtimes, sha256): {data_after == data_before} | test_qa.jsonl / general_test.jsonl in the data dir: "
          f"{[n for n in ('test_qa.jsonl', 'general_test.jsonl') if os.path.exists(os.path.join(data, n))]}")
    ok &= data_after == data_before and not any(os.path.exists(os.path.join(data, n)) for n in ("test_qa.jsonl", "general_test.jsonl"))
    inputs_after = tree_snapshot(inputs)
    src_after = tree_snapshot(src)
    gs_after = git(repo, *gs_args).stdout.decode()
    print(f"inputs unchanged: {inputs_after == inputs_before} | src tree unchanged (incl. __pycache__): {src_after == src_before} "
          f"| git status --porcelain --ignored --untracked-files=all -- metrix unchanged: {gs_after == gs_before}")
    if src_after != src_before:
        print("  src differences:", sorted(set(src_after.items()) ^ set(src_before.items()))[:10])
    ok &= inputs_after == inputs_before and src_after == src_before and gs_after == gs_before
    print(f"results directory created: {os.path.exists(os.path.join(repo, 'metrix/e1-pilot/results'))}")
    ok &= not os.path.exists(os.path.join(repo, "metrix/e1-pilot/results"))
    st10 = "metrix/e1-pilot/results/st10_record.json"
    st10_any = os.path.exists(os.path.join(repo, st10)) or git(repo, "log", "--all", "--full-history", "--format=%H", "--", st10).stdout.strip() != b""
    print(f"{st10} in the working tree or in any commit: {st10_any}")
    ok &= not st10_any
    return bool(ok)


run(main)
