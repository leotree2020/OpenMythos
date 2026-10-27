"""Side-effect-free helpers of the G0 CPU test runner (F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001, final closeout).  Nothing here starts a process, signals,
writes a file or imports platform / subprocess: environment facts come from os.uname() (a system call), the checkout HEAD from reading .git files, and
file identities from hashing.  Used by run_g0_v5_cpu_tests.py and tested by tests/test_g0_v5_boundaries.py."""
import hashlib
import os
import re
import sys

HEX40 = re.compile(r"^[0-9a-f]{40}$")
# expected aggregate hash of bench/*.py (unchanged since the E1-A bench; the same formula as g0_run.bench_code_hash)
BENCH_CODE_SHA256 = "b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0"
KEY_FILES = ("gate_g0/g0_auth.py", "gate_g0/g0_judge.py", "gate_g0/g0_run.py", "gate_g0/g0_criteria_v5.json", "gate_g0/E1A_GATE_G0_PREREG_V5.md",
             "tools/run_g0_v5_cpu_tests.py", "tools/g0_test_env.py", "tests/g0_v5_fixtures.py", "tests/test_g0_interlock_and_judge.py", "tests/test_g0_v5_cases.py",
             "tests/test_g0_v5_closure_cases.py", "tests/test_g0_v5_pipeline.py", "tests/test_g0_v5_run_parts.py", "tests/test_g0_v5_supplement.py",
             "tests/test_g0_v5_boundaries.py")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path):
    """The Git object id of a file's content (what `git hash-object` prints), computed without Git."""
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def find_git_dir(start):
    d = os.path.abspath(start)
    while True:
        g = os.path.join(d, ".git")
        if os.path.isdir(g):
            return g
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def read_git_head(start):
    """-> (head sha, ref or None, git dir).  Reads .git/HEAD, loose refs and packed-refs; raises RuntimeError when the HEAD cannot be established."""
    gd = find_git_dir(start)
    if gd is None:
        raise RuntimeError("no .git directory above %s" % start)
    head = open(os.path.join(gd, "HEAD")).read().strip()
    if HEX40.match(head):
        return head, None, gd
    if not head.startswith("ref: "):
        raise RuntimeError("unrecognised HEAD content %r" % head[:60])
    ref = head[5:]
    p = os.path.join(gd, ref)
    if os.path.isfile(p):
        sha = open(p).read().strip()
        if HEX40.match(sha):
            return sha, ref, gd
    pr = os.path.join(gd, "packed-refs")
    if os.path.isfile(pr):
        for line in open(pr):
            line = line.strip()
            if line and not line.startswith(("#", "^")) and line.endswith(" " + ref) and HEX40.match(line.split()[0]):
                return line.split()[0], ref, gd
    raise RuntimeError("cannot resolve %s" % ref)


def environment_info():
    u = os.uname()
    return {"python": sys.version.split()[0], "implementation": sys.implementation.name, "sysname": u.sysname, "kernel": u.release, "machine": u.machine,
            "cpu_count": os.cpu_count(), "uid": os.getuid(), "dont_write_bytecode": sys.dont_write_bytecode, "gpu_used": False}


def bench_code_sha256(a003):
    b = os.path.join(a003, "bench")
    parts = ["%s:%s" % (f, sha256_file(os.path.join(b, f))) for f in sorted(os.listdir(b)) if f.endswith(".py")]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def verify_checkout(a003, expected_sha, frozen_files):
    """Independent identity check; never trusts the environment variable alone.  -> dict; `ok` is True only when the checkout HEAD equals the expected
    SHA, every frozen file has its frozen bytes and the bench code is unchanged.  `frozen_files` = {name: sha256} relative to gate_g0."""
    out = {"expected_sha": expected_sha, "ok": False, "problems": []}
    if not (isinstance(expected_sha, str) and HEX40.match(expected_sha)):
        out["problems"].append("expected SHA missing or not a 40-digit hex id (set G0_TEST_GIT_SHA or pass --expect-sha)")
    try:
        head, ref, gd = read_git_head(a003)
        out.update(actual_head=head, ref=ref)
        if head != expected_sha:
            out["problems"].append("checkout HEAD %s != expected %s" % (head, expected_sha))
    except (RuntimeError, OSError) as e:
        out.update(actual_head=None, ref=None)
        out["problems"].append("cannot read the checkout HEAD: %s" % e)
    bad = []
    for name, want in sorted(frozen_files.items()):
        try:
            if sha256_file(os.path.join(a003, "gate_g0", name)) != want:
                bad.append(name)
        except OSError:
            bad.append(name + " (unreadable)")
    out["frozen_files_checked"] = len(frozen_files)
    if bad:
        out["problems"].append("frozen files changed: %s" % bad)
    b = bench_code_sha256(a003)
    out["bench_code_sha256"] = b
    if b != BENCH_CODE_SHA256:
        out["problems"].append("bench code hash %s != %s" % (b, BENCH_CODE_SHA256))
    files = {}
    for rel in KEY_FILES:
        p = os.path.join(a003, rel)
        if os.path.isfile(p):
            files[rel] = {"sha256": sha256_file(p), "git_blob_sha1": git_blob_sha1(p)}
    out["key_files"] = files
    out["ok"] = not out["problems"]
    return out
