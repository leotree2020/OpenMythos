"""Read-only checks after the single freeze launch (revision r1; prepared before the GO, run only after the freeze has
ended). Compares the working tree with the accepted verify commit e79acc6 and with the reviewer's approved commitment.
Writes nothing in the repository.

Exit status: 0 = every check passed; 1 = at least one check failed; 2 = ABORTED (a git command failed, a file was
missing or unreadable, or any other error): an aborted run is never reported as a pass."""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = "/home/user/OpenMythos"
E = REPO + "/experiments/gate_e/e2c"
RUN = os.path.dirname(os.path.abspath(__file__))
C = "e79acc6e7a39e1ec4e720d9a66ec05bc8848f150"
VSHA = "6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a"
SSHA = "a8bdcd34199441038442111ef28dac221ec37c7eb063b772fbbbb6750c6055fc"
APPROVED_SC = "52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc"
CAP = 3600.0


class Aborted(Exception):
    pass


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if r.returncode != 0:
        raise Aborted(f"git {' '.join(args)} failed (exit {r.returncode}): {r.stderr.strip()[:300]}")
    return r.stdout


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


res = {}


def check(name, cond, detail=""):
    res[name] = bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f": {detail}" if detail != "" else ""))


def union_seconds(intervals, supplements):
    spans = sorted((x["start"], x["end"] if x["end"] is not None else x["heartbeat"]) for x in intervals)
    total, cur = 0.0, None
    for a, b in spans:
        if cur is None or a > cur[1]:
            total += (cur[1] - cur[0]) if cur else 0.0
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    total += (cur[1] - cur[0]) if cur else 0.0
    return total + sum(x["seconds"] for x in supplements)


def scan_processes(proc_root="/proc", opener=open, self_pid=None):
    """Processes whose command line names an E2-c driver, worker or job. Only a process that disappeared while it was
    being read (FileNotFoundError, ProcessLookupError) is skipped; any other read error (PermissionError included)
    raises Aborted, so an unreadable process table never yields "no process left"."""
    me = os.getpid() if self_pid is None else self_pid
    try:
        entries = os.listdir(proc_root)
    except OSError as e:
        raise Aborted(f"cannot list {proc_root}: {type(e).__name__}: {e}")
    left = []
    for x in entries:
        if not x.isdigit() or int(x) == me:
            continue
        path = os.path.join(proc_root, x, "cmdline")
        try:
            with opener(path, "rb") as fh:
                cl = fh.read()
        except (FileNotFoundError, ProcessLookupError):
            continue  # the process is gone
        except OSError as e:
            raise Aborted(f"cannot read {path}: {type(e).__name__}: {e}")
        if re.search(rb"e2c_stage2\.py|_v2-worker|e2c_stage4", cl):
            left.append((int(x), cl.replace(b"\0", b" ")[:100].decode(errors="replace")))
    return left


def main():
    lr = dict(l.split(" ", 1) for l in open(os.path.join(RUN, "launch_record.txt")).read().splitlines() if " " in l)
    print("launch record:", {k: lr.get(k) for k in ("start_utc", "go_reference", "driver_pid", "end_utc", "exit_code")})
    m = re.search(r"--salt-commitment-sha256 (\S+)", lr.get("command", ""))
    cmd_sc = m.group(1) if m else None
    check("1 exit code 0", lr.get("exit_code") == "0", lr.get("exit_code"))
    status = sorted(git("status", "--porcelain", "--untracked-files=all").splitlines())
    want = sorted(["?? experiments/gate_e/e2c/e2c_workload_freeze.json", "?? experiments/gate_e/e2c/stage2/stage2_freeze_receipt.json",
                   " M experiments/gate_e/e2c/stage2/budget_ledger_s2.json"])
    check("2 working-tree changes are exactly: freeze (new), receipt (new), ledger (modified)", status == want, status)
    committed_rec = git("show", f"{C}:experiments/gate_e/e2c/stage2/stage2_verify.json")
    check("3 verify outputs unchanged (and stage2_verify.json byte-equal to e79acc6)",
          sha(f"{E}/stage2/stage2_verify.json") == VSHA and sha(f"{E}/stage2/v2_streams.json") == SSHA
          and open(f"{E}/stage2/stage2_verify.json").read() == committed_rec)
    led = json.load(open(f"{E}/stage2/budget_ledger_s2.json"))
    old = json.loads(git("show", f"{C}:experiments/gate_e/e2c/stage2/budget_ledger_s2.json"))
    iv = led["intervals"]
    check("4 interval 1 (verify) unchanged", len(iv) == 2 and iv[0] == old["intervals"][0])
    f = iv[1] if len(iv) > 1 else {}
    check("5 interval 2: freeze, PASS, closed, its pid = the launched driver",
          f.get("label") == "freeze" and f.get("status") == "PASS" and f.get("end") is not None and str(f.get("pid")) == lr.get("driver_pid"),
          {k: f.get(k) for k in ("label", "status", "end_utc", "pid", "used_seconds_at_end")})
    check("6a caps: top level and every interval are 3600 s", led.get("cap_seconds") == CAP and all(x.get("cap_seconds") == CAP for x in iv),
          [led.get("cap_seconds")] + [x.get("cap_seconds") for x in iv])
    tot = union_seconds(iv, led.get("supplements", []))
    check("6b cumulative use recomputed from the intervals: strictly below 3600 s; no supplement, no stale report",
          tot < CAP and led.get("supplements") == [] and "stale_reports" not in led, f"{tot:.6f} s")
    check("6c recomputed cumulative = ledger used_seconds (recorded to 0.001 s)", abs(tot - led.get("used_seconds", -1)) <= 0.0005 + 1e-9,
          f"recomputed {tot:.6f}, ledger {led.get('used_seconds')}")
    check("6d recomputed cumulative = freeze interval used_seconds_at_end (recorded to 0.000001 s)",
          abs(tot - f.get("used_seconds_at_end", -1)) <= 0.0000005 + 1e-9, f"recomputed {tot:.6f}, interval {f.get('used_seconds_at_end')}")
    names = ("stage2/verify_stop.json", "stage2/budget_review_required.json", "stage2/budget_review_required_freeze.json")
    check("7 no stop or review record; no temporaries directory", not any(os.path.exists(f"{E}/{n}") for n in names)
          and not [x for x in os.listdir(f"{E}/stage2") if x.startswith("temporaries_of_an_interrupted_write")])
    left = scan_processes()
    check("8 no E2-c process left", not left, left)
    fp, rp = f"{E}/e2c_workload_freeze.json", f"{E}/stage2/stage2_freeze_receipt.json"
    fz, rc = json.load(open(fp)), json.load(open(rp))
    out = open(os.path.join(RUN, "freeze_stdout.txt")).read()
    pub = f.get("published", {})
    check("9 freeze sha256 = ledger.published = receipt = stdout; receipt sha256 = ledger.published",
          sha(fp) == pub.get("e2c_workload_freeze.json") == rc.get("freeze_sha256") and sha(fp) in out
          and sha(rp) == pub.get("stage2_freeze_receipt.json"), f"freeze {sha(fp)}; receipt {sha(rp)}")
    check("10a command commitment = the approved commitment", cmd_sc == APPROVED_SC, cmd_sc)
    check("10b receipt commitment = the approved commitment", rc.get("salt_commitment_sha256") == APPROVED_SC, rc.get("salt_commitment_sha256"))
    check("10c freeze commitment = the approved commitment", fz.get("salt_commitment_sha256") == APPROVED_SC, fz.get("salt_commitment_sha256"))
    check("10d receipt binds the accepted verify (sha256 and commit)", rc.get("verify_record_sha256") == VSHA and rc.get("verify_commit") == C)
    rec = json.loads(committed_rec)
    lam = json.loads(git("show", f"{C}:experiments/gate_e/e2c/stage1/gate4/lambda_selected.json"))
    s2 = fz.get("stage2", {})
    check("11a freeze binds: verify sha/commit, v2 streams, 33 seeds, E1 manifest, basis, keyspace, lambda/lambda2",
          s2.get("verify_record_sha256") == VSHA and s2.get("verify_commit") == C and s2.get("v2_streams_sha256") == SSHA == rec["v2"]["streams_sha256"]
          and s2.get("training_stream_seeds") == rec["v2"]["seeds"] and len(rec["v2"]["seeds"]) == 33
          and s2.get("e1_sets_manifest_sha256") == rec["e1_sets"]["manifest_sha256"] and fz.get("basis") == rec["basis"]
          and fz.get("keyspace") == rec["keyspace"] and fz.get("lambda") == lam["lambda"] and fz.get("lambda2") == lam["lambda2"])
    want_e1 = {n: v["sha256"] for n, v in rec["e1_sets"]["files"].items()}
    check("11b freeze stage2.e1_sets_sha256 = the accepted verify's per-set sha256 map", s2.get("e1_sets_sha256") == want_e1 and len(want_e1) == 13,
          f"{len(s2.get('e1_sets_sha256') or {})} sets")
    sys.path.insert(0, E)
    sys.dont_write_bytecode = True
    import run_e2c as R  # read-only functions: paths, basis, check_baseline
    diffs = R.check_baseline(fz, R.basis(R.paths()))
    check("12 launcher baseline check of the written freeze against the tree now: no difference", diffs == [], diffs)
    kl = re.compile(r"[A-Za-z]=[0-9];[A-Za-z]=[0-9]")
    check("13 no key-like text in freeze, receipt, stdout, stderr", not any(kl.search(open(p, encoding="utf-8", errors="replace").read()) for p in
          (fp, rp, os.path.join(RUN, "freeze_stdout.txt"), os.path.join(RUN, "freeze_stderr.txt"))))
    end_ts = dt.datetime.strptime(lr["end_utc"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc).timestamp()
    print(f"closing: ledger interval 2 end {f.get('end_utc')} ({f.get('end')}); process end {lr['end_utc']}; "
          f"difference {end_ts - f['end']:.3f} s (recorded only; the cause is not asserted)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ABORTED: {type(e).__name__}: {e}")
        print("post-run freeze checks: ABORTED (not a pass)")
        sys.exit(2)
    print("post-run freeze checks:", "ALL PASS" if res and all(res.values()) else "FAILED", f"({sum(res.values())}/{len(res)})")
    sys.exit(0 if res and all(res.values()) else 1)
