"""ic11_03 (implementation stage C, C4 code commit (staged tree 63121c79, parent 3bc761ea), round 1; my ic10_03 run again; task 4): the smoke
produced no TEST content, and the TEST generator refuses in the current state (black box).
  A. <smoke> (the smoke's work directory): no file named test_qa.jsonl or general_test.jsonl anywhere under it (names
     only, nothing is opened); the step 8 out directory the smoke used does not exist.
  B. records/step8_record.json: the command is the generator module (python -m metrix_e1.test_data) with --data the
     smoke's data directory and --out under <smoke>; non-zero return code, last stdout line RESULT: FAIL, the refusal
     line present, --out not created, no TEST file under <smoke>, refused true, SMOKE label.
  C. My own run of the generator, once, as a black-box subprocess, the way run_pilot.py runs it (cwd the repository
     root, PYTHONPATH the package's src directory, PYTHONDONTWRITEBYTECODE=1):
         <venv python> -m metrix_e1.test_data --inputs <inputs> --data <smoke>/data --out <out_dir>
     <out_dir> does not exist and lies outside the repository. Expected (written before the run): every
     interpretation is ruled and HEAD has no Gate 0 record (metrix/e1-pilot/results/gate0_record.json is neither in
     HEAD nor in the working tree), so condition 2 fails first: stdout exactly
         TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
         no TEST content was generated, read or written
         RESULT: FAIL
     exit code 1, the same three lines as the smoke's step 8 and as c4_02_checks.txt; <out_dir> not created. The
     process is killed at once if a line only a generating run prints appears.
     After: data directory, inputs, src tree and `git status --porcelain --ignored --untracked-files=all -- metrix`
     (audit/ excluded: my outputs are written there) unchanged; no results directory; no ST10 record in the working
     tree or in any commit.
Data Auditor's own script; the Executor's module is only executed as the black-box command.
usage: python -I -B ic11_03_test_refusal.py <repo_root> <venv_python> <inputs_dir> <smoke_work_dir> <out_dir (must not exist)>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import shlex
import subprocess
from ia_common import file_sha, run

GEN_MARKERS = ("byte_sha256", "TEST part value", "TEST part count", "L6 TEST count", "leakage_test_report",
               "ST10 record written", "ST10:")
EXPECTED = ["TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD",
            "no TEST content was generated, read or written", "RESULT: FAIL"]
TEST_NAMES = ("test_qa.jsonl", "general_test.jsonl")


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %r" % (args, r.stderr))
    return r


def tree_snapshot(root):
    out = {}
    for r, ds, fs in os.walk(root):
        for f in fs:
            p = os.path.join(r, f)
            st = os.stat(p)
            out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns, file_sha(p))
    return out


def main():
    repo, py, inputs, work, out = sys.argv[1:6]
    data = os.path.join(work, "data")
    ok = True
    print("== A. no TEST file under the smoke's work directory (names only)")
    hits = [os.path.join(d, f) for d, _, fs in os.walk(work) for f in fs if f in TEST_NAMES]
    nfiles = sum(len(fs) for _, _, fs in os.walk(work))
    print("files under %s: %d | named test_qa.jsonl / general_test.jsonl: %s" % (work, nfiles, hits))
    ok &= not hits
    s8out = os.path.join(work, "step8_refused_out")
    print("smoke step 8 --out %s exists: %s" % (s8out, os.path.exists(s8out)))
    ok &= not os.path.exists(s8out)

    print("\n== B. records/step8_record.json")
    s8 = json.load(open(os.path.join(work, "records", "step8_record.json"), encoding="utf-8"))
    cmd8 = s8["command"]
    lines8 = s8["stdout"].rstrip("\n").split("\n")
    print("command %s" % cmd8)
    c_ok = (cmd8[1:3] == ["-m", "metrix_e1.test_data"] and cmd8[cmd8.index("--data") + 1] == data
            and cmd8[cmd8.index("--out") + 1] == s8out)
    print("generator module, --data the smoke data dir, --out under the work dir: %s" % c_ok)
    print("returncode %r | stdout lines %s | stderr %r | out_exists %r | test_files_under_work %r | refused %r | mode %r "
          "label %r" % (s8["returncode"], lines8, s8["stderr"], s8["out_exists"], s8["test_files_under_work"], s8["refused"],
                        s8["mode"], s8["label"]))
    b_ok = (c_ok and s8["returncode"] != 0 and lines8 == EXPECTED and s8["out_exists"] is False
            and s8["test_files_under_work"] == [] and s8["refused"] is True and s8["mode"] == "smoke"
            and s8["label"] == "SMOKE — NOT A RESULT")
    print("step 8 record shows the refusal (stdout == my expected three lines): %s" % b_ok)
    ok &= b_ok

    print("\n== C. my black-box run of the TEST generator")
    print("out_dir %s exists: %s" % (out, os.path.exists(out)))
    ok &= not os.path.exists(out)
    ro, oo = os.path.realpath(repo), os.path.realpath(out)
    outside = not (oo == ro or oo.startswith(ro + os.sep))
    print("out_dir outside the repository %s: %s" % (ro, outside))
    ok &= outside
    g0 = "metrix/e1-pilot/results/gate0_record.json"
    in_head = git(repo, "cat-file", "-e", "HEAD:%s" % g0, check=False).returncode == 0
    in_idx = git(repo, "cat-file", "-e", ":%s" % g0, check=False).returncode == 0
    in_wt = os.path.exists(os.path.join(repo, g0))
    print("%s: in HEAD %s | in the index %s | in the working tree %s" % (g0, in_head, in_idx, in_wt))
    if in_head or in_wt or in_idx:
        print("precondition 2 could hold: the generator is NOT run")
        return False
    print("expected stdout (before the run): %s ; exit code 1" % EXPECTED)
    src = os.path.join(repo, "metrix/e1-pilot/src")
    data_before, inputs_before, src_before = tree_snapshot(data), tree_snapshot(inputs), tree_snapshot(src)
    gs_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix", ":(exclude)metrix/e1-pilot/audit")
    gs_before = git(repo, *gs_args).stdout.decode()
    print("data dir files: %s | files under src: %d | files under inputs: %d" % (sorted(data_before), len(src_before),
                                                                                len(inputs_before)))
    cmd = [py, "-m", "metrix_e1.test_data", "--inputs", inputs, "--data", data, "--out", out]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=src)
    print("cwd %s | PYTHONPATH %s" % (repo, src))
    print("$ " + " ".join(shlex.quote(c) for c in cmd))
    print("----- generator stdout+stderr begin -----")
    sys.stdout.flush()
    p = subprocess.Popen(cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
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
    print("exit code %d | killed by the auditor %s" % (rc, killed))
    same = not killed and rc == 1 and lines == EXPECTED
    print("output == my expected three lines and exit 1: %s | == the smoke's step 8 stdout: %s" % (same, lines == lines8))
    ok &= same and lines == lines8
    exl = [ln for ln in open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c4_02_checks.txt"), encoding="utf-8").read().split("\n")
           if ln.startswith("TEST generator refused:")]
    print("refusal line == the Executor's in c4_02_checks.txt %s: %s" % (exl, [lines[0]] == exl))
    ok &= [lines[0]] == exl

    print("\n== after")
    print("out_dir %s exists: %s" % (out, os.path.exists(out)))
    ok &= not os.path.exists(out)
    data_after, inputs_after, src_after = tree_snapshot(data), tree_snapshot(inputs), tree_snapshot(src)
    gs_after = git(repo, *gs_args).stdout.decode()
    print("data dir unchanged (names, sizes, mtimes, sha256): %s | TEST file names in it: %s" % (
        data_after == data_before, [n for n in TEST_NAMES if os.path.exists(os.path.join(data, n))]))
    ok &= data_after == data_before and not any(os.path.exists(os.path.join(data, n)) for n in TEST_NAMES)
    print("inputs unchanged: %s | src tree unchanged: %s | git status (audit/ excluded) unchanged: %s" % (
        inputs_after == inputs_before, src_after == src_before, gs_after == gs_before))
    ok &= inputs_after == inputs_before and src_after == src_before and gs_after == gs_before
    print("results directory exists: %s" % os.path.exists(os.path.join(repo, "metrix/e1-pilot/results")))
    ok &= not os.path.exists(os.path.join(repo, "metrix/e1-pilot/results"))
    st10 = "metrix/e1-pilot/results/st10_record.json"
    st10_any = os.path.exists(os.path.join(repo, st10)) or git(repo, "log", "--all", "--full-history", "--format=%H", "--", st10).stdout.strip() != b""
    print("%s in the working tree or in any commit: %s" % (st10, st10_any))
    ok &= not st10_any
    hits2 = [os.path.join(d, f) for d, _, fs in os.walk(work) for f in fs if f in TEST_NAMES]
    print("TEST file names under the smoke work dir after the run: %s" % hits2)
    ok &= not hits2
    return bool(ok)


run(main)
