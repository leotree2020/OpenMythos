#!/usr/bin/env python3
"""
Stage 2 of E2-c (E2C_PREREG_DRAFT 7.4 steps 1-6, 6 V2, 8.4, 9 F11, 13), as two
separately authorized commands and one read-only check:

    verify   1. E1's set files: every file against sets/manifest.json, the
                manifest against E1's freeze records, nothing changed since
                E1's archive commit (7.4 step 1; before and after the run)
             2. F11: the Appendix A script, rebuilt byte for byte from the
                preregistration, re-run with verbatim output, and the stage-4
                keyspace job (R* / M1* hashes in its own format, B2) with the
                counts H, U, R_star, M1_star of Appendix A (7.4 steps 2-5)
             3. the key rules of e2c_test2 against E1's body_key / is_heldout
             4. V2: the training streams of the 33 seeds 1-5, 91-93, 99,
                201-224, 12000 x 64 accepted samples each, drawn with E1's
                generator and hashed with train_e2c's batch chain: no held-out
                key, chains equal to the 60 committed stage-1 run records, and
                no held-out key in E1's non-U K=2 sets
             -> stage2/v2_streams.json, stage2/stage2_verify.json (written once)
    freeze   after the review approved that record (its commit and sha256 on
             the command line): the salt commitment (sha256 only, B3; a salt
             is never accepted) and e2c_workload_freeze.json (written once)
    check    read-only: an existing record / freeze against the inputs

Authorization: a real run needs E2C_STAGE2_AUTHORIZED=verify (or =freeze) and
--authorization TEXT, so each command is authorized on its own. Only the
stage-4 keyspace job and the Appendix A script enumerate R* / M1*; verify
starts them with E2C_KEYSPACE_STAGE=2 in their own environment only. Nothing
writes a key list; every output is scanned for key-like text; no checkpoint
is ever opened (audit hook).

Budget (8.4, F9): one ledger for verify and freeze, 3600 s over all launches,
never reset. Each launch is counted from the start of its process (kernel
start time), interpreter start-up and imports included, and the ledger is
opened, and the cap checked, before the heavy imports. A watchdog thread
interrupts the running step at the cap (SIGUSR1 -> BudgetExceeded, a
BaseException); every wait for a job (the Appendix A script, the keyspace job,
the V2 workers) also checks the cap every 0.1-0.2 s. At the cap, on an
interruption or an error the job's whole process group is terminated, and
after a job ends its group is ended too. Every child starts through an exec
wrapper (no preexec_fn in this threaded driver) that sets PR_SET_PDEATHSIG,
so a direct child dies if the driver is killed; its own descendants are not
covered by that (the real jobs start none). Outputs that cannot be undone
(v2_streams.json / stage2_verify.json, the freeze and its receipt) are
written and fsynced under temporary names first; the last check is then
followed only by link() calls, which no signal can split (the publish
window). The final status is decided when the ledger interval is closed: if
the launch ended at or past the cap (inside the publish window, or after the
publication), it is BUDGET_CAP_REVIEW_REQUIRED (exit 7), not PASS; the
published files stay as written and a review record bound to their sha256
(budget_review_required[_freeze].json) blocks verify --resume and freeze,
also once deleted (the history is checked). An interval left open by a
process that is gone is kept as it was and reported; the next launch
refuses until --accept-stale-supplement books a conservative supplement of
two heartbeat periods for it (or the review decides otherwise).

Exit codes: 0 pass; 3 F11 (counts differ from Appendix A), V2 integrity
failure (recorded as such, not as F11) or another integrity failure: nothing
is frozen and stage2/verify_stop.json makes later verify launches refuse
until the review decides; 4 other error; 5 refused; 6 an expected output
missing; 7 the stage-2 cap (1 h over all launches, never reset; F9);
130 interrupted (resume with --resume).

Test mode (e2c_stage2_tests.py only): E2C_S2_TEST_DIR names a synthetic
setup (config.json) with stub jobs and a synthetic stream; the functions that
could reach the real key space or the real training streams raise there.
"""

import argparse
import contextlib
import fcntl
import fnmatch
import glob
import gzip
import hashlib
import itertools
import json
import os
import random
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(GE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

TEST_DIR = os.environ.get("E2C_S2_TEST_DIR")


def process_start():
    """Wall-clock time at which this process started (kernel start time in /proc against CLOCK_BOOTTIME, 10 ms
    resolution): every launch is ledgered from it, interpreter start-up and imports included (8.4)."""
    try:
        ticks = int(open("/proc/self/stat").read().rsplit(")", 1)[1].split()[19])
        return time.time() - (time.clock_gettime(time.CLOCK_BOOTTIME) - ticks / os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


T_PROCESS = min(t for t in (process_start(), time.time()) if t is not None)

PREREG_SHA256 = "434f586996e49b5a493b5a346839756da7c653fc451bcba2b14438bfb00d6681"
DESIGN_REVIEW_SHA256 = "96f0df4883276b105a3026ed06f7ee09e1e9d3348895faf659fc689e4ed8d7d4"
LAMBDA_SELECTED_SHA256 = "6c23606ebec922dcfe9a577260b9830ffac002da778e27ea39865cce30fff43f"
CALIBRATION_SHA256 = "a2301dc764393872ac82f4a083456a54fa0c4a826ebf92c08483e7f70dee87c2"
APPENDIX_A_SCRIPT_SHA256 = "dfa649e37b21f81cb7ff740dd4bbf2206c4efbbc434d9a1a63e1500c48876390"
APPENDIX_A_STDOUT_SHA256 = "3b58fb663310509e52daf99f0ee0b016734e345cf8cdc335101bb1f89edb267b"
E1_SETS_MANIFEST_SHA256 = "d22fcdab84c0ae85b49f0c7fd8c578a3f753b9b824a50654e8427f88ca4c259e"
E1_ARCHIVE_COMMIT = "4b33c861a749f53f3445119dd09ef92a9b60ea8e"
STAGE1_ACCEPTED_COMMIT = "f7a0ffe867b55a0087731a2b29fe5fbd8487b3fa"
# the only code changes since the stage-1 acceptance (I2); any other one is refused
ALLOWED_CODE_CHANGES = {"experiments/gate_e/e2c/e2c_launcher_tests.py": "M", "experiments/gate_e/e2c/e2c_stage2.py": "A",
                        "experiments/gate_e/e2c/e2c_stage2_tests.py": "A", "experiments/gate_e/e2c/run_e2c.py": "M"}
E1_ANCHORS = (("experiments/gate_e/workload_freeze.json", ("basis", "sets_manifest_sha256")),
              ("experiments/gate_e/workload_freeze_v2.json", ("basis", "sets_manifest_sha256")),
              ("experiments/gate_e/run_freeze.json", ("sets_manifest_sha256",)),
              ("experiments/gate_e/run_freeze.json", ("workload", "basis", "sets_manifest_sha256")))
E1_GIT_PATHS = ("experiments/gate_e/sets", "experiments/gate_e/workload_freeze.json", "experiments/gate_e/workload_freeze_v2.json",
                "experiments/gate_e/run_freeze.json")
# committed stage-1 run records with batch chains (train_e2c.py, seeds 1-5, 91-93, 99): 60 files, digest of "path:sha256\n"
REFERENCE_GLOBS = ("stage1/gate1/*.json", "stage1/gate2/r2/*.json", "stage1/gate3/run_*.json", "stage1/gate4/run_archive/*.json.gz",
                   "stage1/v3/*.json")
REFERENCE_COUNT, REFERENCE_DIGEST = 60, "22017d1b160e3a455a2fcbee6a019d417818fced7511f02da422dcd385a0de83"
SEEDS_33 = list(range(1, 6)) + [91, 92, 93, 99] + list(range(201, 225))
U_SETS = ("dev_heldout", "test_heldout", "diag_fit", "diag_eval", "minpair")
NON_U_K2_SETS = ("dev_seen", "pool_b_k2", "pool_c_k2")
V2_UPDATES, V2_BATCH, V2_WORKERS = 12000, 64, 4
CAP_SECONDS, HEARTBEAT_SECONDS, JOB_TIMEOUT_SECONDS = 3600.0, 10.0, 1800.0
DIG = "0123456789"
KEY_LIKE = re.compile(r"[A-Za-z]=[0-9];[A-Za-z]=[0-9]")
FORBIDDEN_REAL_ENV = ("E2C_TEST_DIR", "E2C_TEST_CMDS", "E2C_TEST_PLAN", "E2C_TEST_CAP_SECONDS", "E2C_KEYSPACE_STAGE", "E2C_S2_WORKER")
STATUS = {0: "PASS", 3: "INTEGRITY_FAILURE", 4: "ERROR", 5: "REFUSED", 6: "MISSING_OUTPUT", 7: "BUDGET_CAP", 130: "INTERRUPTED"}
# I2-R2: outputs published, but the launch ended past the cap (inside the publish window, or after the publication and
# before the ledger closed): exit 7, the outputs stay as written, a review record bound to their sha256 blocks freeze
REVIEW_STATUS = "BUDGET_CAP_REVIEW_REQUIRED"
REVIEW_RECORDS = {"verify": "budget_review_required.json", "freeze": "budget_review_required_freeze.json"}


class S2Stop(Exception):
    def __init__(self, code, msg, status=None):
        super().__init__(msg)
        self.code, self.status = code, status or STATUS[code]


class Interrupted(Exception):
    pass


class BudgetExceeded(BaseException):
    """F9 (exit 7). A BaseException, so that no `except Exception` on the way can swallow it."""
    code, status = 7, "BUDGET_CAP"


# Signal state. CPython runs every Python-level handler in the main thread, whichever thread the kernel delivered the
# signal to, so a signal mask alone does not protect a section: the handlers consult these flags. "shielded": the
# process is cleaning up and stops nothing more; "window": the publish window, where a signal is deferred;
# "published": the outputs are visible; "stopping": a budget stop is already under way.
_SIG = {"shielded": False, "window": False, "published": False, "stopping": False, "deferred": None, "note": None,
        "message": "BUDGET EXCEEDED (F9)"}


def _on_term(signum, frame):
    if _SIG["shielded"]:
        return
    if _SIG["window"]:
        _SIG["deferred"] = _SIG["deferred"] or Interrupted(signum)
        return
    raise Interrupted(signum)


def _on_budget_signal(signum, frame):
    if _SIG["shielded"] or _SIG["published"] or _SIG["stopping"]:
        return
    if _SIG["window"]:
        _SIG["deferred"] = _SIG["deferred"] or BudgetExceeded(_SIG["message"])
        return
    _SIG["stopping"] = True
    raise BudgetExceeded(_SIG["message"])


class CheckpointAccess(RuntimeError):
    pass


def _audit(event, args):
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        p = os.fsdecode(args[0])
        if p.endswith((".pt", ".pth", ".ckpt")) or "openmythos-artifacts" in p:
            raise CheckpointAccess(f"stage 2 never opens a checkpoint: {p}")


def _tripwire(*a, **k):
    raise RuntimeError("TRIPWIRE: a function of the real key space or training streams was called in test mode")


def shield():
    """The process is shutting down: a further SIGTERM / SIGINT / budget signal must not interrupt the cleanup."""
    _SIG["shielded"] = True
    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT, signal.SIGUSR1})


@contextlib.contextmanager
def publish_window():
    """The only section that neither the budget watchdog nor SIGTERM / SIGINT can split: the last budget check and the
    link() calls that make staged outputs visible. A signal arriving here is deferred: raised when the window closes
    if the outputs were not published, recorded (and not raised) if they were."""
    _SIG["window"] = True
    try:
        yield
    finally:
        _SIG["window"] = False
    deferred, _SIG["deferred"] = _SIG["deferred"], None  # reached only when the block ended without an exception
    if deferred is not None:
        if not _SIG["published"]:
            _SIG["stopping"] = True
            raise deferred
        _SIG["note"] = f"{type(deferred).__name__} arrived inside the publish window after the outputs were decided; deferred"


def _alive(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return False


# Every child (the two jobs, the V2 workers) starts through this wrapper instead of a preexec_fn: no Python code runs
# between fork and exec in the driver (which has threads), so subprocess can use vfork / posix_spawn. The wrapper, a
# fresh single-threaded interpreter, asks the kernel for SIGKILL when its parent dies (PR_SET_PDEATHSIG, kept across
# execve for ordinary binaries), exits at once if the driver is already gone, then executes the real command with
# its arguments and environment unchanged. This covers the direct child only: a descendant of a job is not covered
# (on a normal stop the job's whole process group is terminated; the real jobs start no processes of their own).
EXEC_WRAPPER = ("import ctypes, os, signal, sys\n"
                "if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL) != 0: os._exit(71)\n"
                "if os.getppid() != int(sys.argv[1]): os._exit(70)\n"
                "os.execv(sys.argv[2], sys.argv[2:])\n")


def child_argv(argv):
    """argv of a child that dies with the driver; argv[0] must be an absolute path (sys.executable)."""
    return [sys.executable, "-I", "-c", EXEC_WRAPPER, str(os.getpid()), *argv]


def end_group(p):
    """After a job's leader has exited (normally or not): no member of its process group may run on."""
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def kill_group(p, grace=5.0):
    """Terminate the whole process group of a job started with start_new_session=True: SIGTERM, then SIGKILL."""
    shield()
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            break
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
    try:
        os.killpg(p.pid, signal.SIGKILL)  # members that outlived the leader
    except ProcessLookupError:
        pass
    p.wait()


def run_bounded(argv, ledger, label, att, cwd, env):
    """A job in its own process group, waited for in steps of 0.1 s with the stage-2 cap checked at each step; at the
    cap (F9, exit 7), on an interruption, a timeout or any error the whole group is terminated. Output goes to files
    of the attempt. Returns (exit code, stdout, stderr)."""
    paths = [os.path.join(att, f"job_{label}.{x}.txt") for x in ("stdout", "stderr")]
    with open(paths[0], "wb") as fo, open(paths[1], "wb") as fe:
        p = subprocess.Popen(child_argv(argv), cwd=cwd, env=env, stdout=fo, stderr=fe, start_new_session=True)
        try:
            t0 = time.time()
            while p.poll() is None:
                ledger.check(f"while the {label} job runs")
                if time.time() - t0 > JOB_TIMEOUT_SECONDS:
                    raise S2Stop(4, f"RUN ERROR: the {label} job did not finish within {JOB_TIMEOUT_SECONDS:.0f} s")
                time.sleep(0.1)
        finally:
            if p.poll() is None:
                kill_group(p)
            else:
                end_group(p)  # a descendant the job left behind does not run on
    if p.returncode in (70, 71):
        raise S2Stop(4, f"RUN ERROR: the {label} job could not be tied to the driver (wrapper exit {p.returncode})")
    return p.returncode, open(paths[0], encoding="utf-8", errors="replace").read(), open(paths[1], errors="replace").read()


def test_delay(ctx, where):
    """Tests only: a slow step just before the last budget check ("verify", "freeze"), or inside the publish window
    ("verify_inside_window"), to reach the boundaries of the budget rule."""
    if ctx["test"] and ctx["cfg"].get("stub_delay_before_final_write", {}).get(where):
        time.sleep(ctx["cfg"]["stub_delay_before_final_write"][where])


def install_guards(test):
    sys.addaudithook(_audit)
    if test:
        import e2c_test2 as T
        T.keyspace = T.training_stream_keys = T.generate = _tripwire


# ------------------------------------------------------------ small helpers


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def canon(obj):
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stage_file(path, data):
    """First half of a write-once: the content in a temporary file of the same directory, written and fsynced."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=f".{os.path.basename(path)}.tmp.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        os.unlink(tmp)
        raise
    return tmp


def publish(tmp, path):
    """Second half: link (atomic; fails if the name exists, never replaces it), drop the temporary name, fsync the
    directory. Only the link() call decides whether the file exists."""
    try:
        os.link(tmp, path)
    finally:
        os.unlink(tmp)
    dfd = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY)
    os.fsync(dfd)
    os.close(dfd)


def discard(*tmps):
    for t in tmps:
        if t and os.path.exists(t):
            os.unlink(t)


def write_once(path, data):
    """Write bytes to path only if it does not exist."""
    publish(stage_file(path, data), path)


def write_once_or_same(path, data):
    try:
        write_once(path, data)
    except FileExistsError:
        if open(path, "rb").read() != data:
            raise S2Stop(3, f"INTEGRITY FAILURE: {os.path.basename(path)} exists with other content (written once)")


def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise S2Stop(4, f"RUN ERROR: git {' '.join(args[:3])}: {r.stderr.strip()[:200]}")
    return r.stdout


def leak_scan(paths=(), texts=()):
    """Key-like text ("a=3;b=7") anywhere in the outputs: must be none (no key list is ever written)."""
    hits, n = 0, 0
    for p in paths:
        with open(p, "rb") as f:
            hits += len(KEY_LIKE.findall(f.read().decode("utf-8", "replace")))
        n += 1
    for t in texts:
        hits += len(KEY_LIKE.findall(t.decode("utf-8", "replace") if isinstance(t, bytes) else t))
        n += 1
    return {"files": n, "key_like_hits": hits}


def files_under(d):
    return sorted(os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs)


# ------------------------------------------------------------ context


PATH_KEYS = ("code_root", "prereg", "design_review", "sets_manifest", "git_root", "sets_dir", "code_git_root", "lambda_file",
             "calibration_file", "environment_file", "reference_root", "stub_appendix_stdout", "stub_appendix_script",
             "stub_keyspace_job")


def ledger_location():
    """Where the stage-2 ledger is, its cap and heartbeat, without the heavy imports of context() (they are ledgered
    too). Tests may switch the watchdog off to reach the last explicit check; a real run always has it."""
    cfg = json.load(open(os.path.join(TEST_DIR, "config.json"))) if TEST_DIR else {}
    return (os.path.join(TEST_DIR or HERE, "stage2", "budget_ledger_s2.json"), float(cfg.get("cap_seconds", CAP_SECONDS)),
            float(cfg.get("heartbeat_seconds", HEARTBEAT_SECONDS)), not (TEST_DIR and cfg.get("stub_no_watchdog")))


def context():
    cfg = json.load(open(os.path.join(TEST_DIR, "config.json"))) if TEST_DIR else {}
    for k in PATH_KEYS:
        if cfg.get(k) and not os.path.isabs(cfg[k]):
            cfg[k] = os.path.join(TEST_DIR, cfg[k])
    import run_e2c as R
    p = R.paths()  # the freeze path: e2c/ (real) or E2C_TEST_DIR (tests set it to the test directory)
    if TEST_DIR and os.path.realpath(p["base"]) != os.path.realpath(TEST_DIR):
        raise S2Stop(5, "REFUSED: test mode needs E2C_TEST_DIR equal to E2C_S2_TEST_DIR")
    for k in ("code_root", "prereg", "design_review", "sets_manifest"):
        if cfg.get(k):
            p[k] = cfg[k]
    s1 = os.path.join(HERE, "stage1")
    return {
        "test": bool(TEST_DIR), "cfg": cfg, "p": p, "R": R,
        "git_root": cfg.get("git_root", ROOT), "out": os.path.join(TEST_DIR or HERE, "stage2"),
        "sets_dir": cfg.get("sets_dir", os.path.join(GE, "sets")),
        "e1_anchors": [tuple(x) for x in cfg.get("e1_anchors", E1_ANCHORS)], "e1_git_paths": cfg.get("e1_git_paths", E1_GIT_PATHS),
        "e1_manifest_sha256": cfg.get("e1_manifest_sha256", E1_SETS_MANIFEST_SHA256),
        "e1_archive_commit": cfg.get("e1_archive_commit", E1_ARCHIVE_COMMIT),
        "code_git_root": cfg.get("code_git_root", ROOT), "code_base_commit": cfg.get("code_base_commit", STAGE1_ACCEPTED_COMMIT),
        "allowed_changes": cfg.get("allowed_changes", ALLOWED_CODE_CHANGES),
        "lambda_file": cfg.get("lambda_file", os.path.join(s1, "gate4", "lambda_selected.json")),
        "calibration_file": cfg.get("calibration_file", os.path.join(s1, "gate4", "calibration.json")),
        "environment_file": cfg.get("environment_file", os.path.join(s1, "environment.json")),
        "reference_root": cfg.get("reference_root", HERE), "reference_globs": cfg.get("reference_globs", REFERENCE_GLOBS),
        "reference_count": cfg.get("reference_count", REFERENCE_COUNT), "reference_digest": cfg.get("reference_digest", REFERENCE_DIGEST),
        "cap": float(cfg.get("cap_seconds", CAP_SECONDS)), "heartbeat": float(cfg.get("heartbeat_seconds", HEARTBEAT_SECONDS)),
        "updates": int(cfg.get("updates", V2_UPDATES)), "batch": int(cfg.get("batch", V2_BATCH)),
        "workers": int(cfg.get("workers", V2_WORKERS)),
    }


def env_checks(command, authorization):
    """First of all, before any file is read or written: who may run what."""
    if TEST_DIR:
        bad = [k for k in ("E2C_KEYSPACE_STAGE", "E2C_STAGE2_AUTHORIZED") if k in os.environ]
        if bad:
            raise S2Stop(5, f"REFUSED: test mode with {bad} set")
        return
    bad = sorted(k for k in os.environ if k in FORBIDDEN_REAL_ENV or k.startswith("STUB_"))
    if command == "_v2-worker":
        bad = [k for k in bad if k != "E2C_S2_WORKER"]
        if os.environ.get("E2C_S2_WORKER") != "1":
            bad.append("E2C_S2_WORKER")
    if bad:
        raise S2Stop(5, f"REFUSED: a real stage-2 run with test or stage variables set: {bad}")
    want = "verify" if command == "_v2-worker" else command
    if command in ("verify", "freeze", "_v2-worker"):
        if os.environ.get("E2C_STAGE2_AUTHORIZED") != want or (command != "_v2-worker" and not (authorization or "").strip()):
            raise S2Stop(5, f"REFUSED: stage-2 {want} needs its own authorization: E2C_STAGE2_AUTHORIZED={want} and --authorization")


# ------------------------------------------------------------ budget ledger (8.4: stage 2, 1 h, all launches)


def _proc_start(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def _union(intervals):
    spans = sorted((iv["start"], iv["end"] if iv["end"] is not None else iv["heartbeat"]) for iv in intervals)
    total, cur = 0.0, None
    for a, b in spans:
        if cur is None or a > cur[1]:
            if cur:
                total += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    return total + (cur[1] - cur[0] if cur else 0.0)


class Ledger:
    """Union of launch intervals plus supplements (fcntl lock, interval ids, alive check by pid and process start
    time, heartbeat). An interval left open by a process that is gone keeps its original fields; it is counted up
    to its last heartbeat, and the next launch refuses until the stale interval is accepted with a conservative
    supplement of two heartbeat periods (recorded with the authorization), or the review decides."""

    def __init__(self, path, cap, heartbeat, label, watchdog=True):
        self.path, self.cap, self.hb, self.label, self.watchdog = path, cap, heartbeat, label, watchdog
        self.iv_id, self.base, self.t0, self._stop, self.published = None, 0.0, None, threading.Event(), {}

    @contextlib.contextmanager
    def _locked(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd = os.open(self.path + ".lock", os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            d = json.load(open(self.path)) if os.path.exists(self.path) else {"stage": 2, "cap_seconds": self.cap, "intervals": [],
                                                                              "supplements": []}
            yield d
            tmp = f"{self.path}.tmp.{os.getpid()}"
            with open(tmp, "w") as f:
                json.dump(d, f, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @staticmethod
    def total(d):
        return _union(d["intervals"]) + sum(x["seconds"] for x in d.get("supplements", []))

    def open(self, accept_stale=False, authorization=""):
        now, refused = time.time(), None
        with self._locked() as d:
            iv = {"id": len(d["intervals"]) + 1, "label": self.label, "pid": os.getpid(), "pid_start": _proc_start(os.getpid()),
                  "start": T_PROCESS, "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(T_PROCESS)), "heartbeat": now,
                  "heartbeat_seconds": self.hb, "cap_seconds": self.cap, "end": None, "status": None}
            stale = []
            for old in d["intervals"]:
                if old["end"] is None and "stale" not in old:
                    if old.get("pid_start") and _proc_start(old["pid"]) == old["pid_start"]:
                        refused = S2Stop(5, f"REFUSED: another stage-2 process is running (pid {old['pid']}, interval {old['id']})")
                    else:
                        stale.append(old)
            if refused is None and stale and not accept_stale:
                for x in stale:
                    d.setdefault("stale_reports", []).append({
                        "interval": x["id"], "reported_by_interval": iv["id"], "reported_utc": utc(), "last_heartbeat": x["heartbeat"],
                        "counted_until": x["heartbeat"], "proposed_supplement_seconds": 2 * float(x.get("heartbeat_seconds", self.hb)),
                        "seconds_since_last_heartbeat": round(now - x["heartbeat"], 3),
                        "note": "not ledgered after the last heartbeat; booked only when accepted (--accept-stale-supplement) "
                                "or as the review decides"})
                refused = S2Stop(5, "REFUSED: interval(s) " + ", ".join(
                    f"{x['id']} ({x['label']}, last heartbeat {time.strftime('%H:%M:%SZ', time.gmtime(x['heartbeat']))})" for x in stale)
                    + " were left open by a process that is gone; the time after the last heartbeat is not ledgered. Relaunch with "
                    "--accept-stale-supplement to book a conservative supplement of two heartbeat periods each, or submit it to the review")
            elif refused is None:
                for x in stale:
                    sup = 2 * float(x.get("heartbeat_seconds", self.hb))
                    x["stale"] = {"detected_utc": utc(), "accepted_by_interval": iv["id"], "counted_until": x["heartbeat"],
                                  "supplement_seconds": sup}
                    d.setdefault("supplements", []).append({"interval": x["id"], "seconds": sup, "accepted_utc": utc(),
                                                            "authorization": authorization or "-",
                                                            "reason": "process gone: conservative supplement for the time after "
                                                                      "its last heartbeat (two heartbeat periods)"})
            self.base = self.total(d)
            d["intervals"].append(iv)
            if refused is None and self.base + (now - T_PROCESS) >= self.cap:
                refused = BudgetExceeded(f"BUDGET EXCEEDED (F9): stage 2 used {self.base + now - T_PROCESS:.1f} s of {self.cap:.0f} s "
                                         "(refused at the start of the launch)")
            if refused:  # the launch is recorded, then refused
                iv.update(end=now, status=refused.status)
            else:
                self.iv_id, self.t0 = iv["id"], T_PROCESS
            d["used_seconds"] = round(self.total(d), 3)
        if refused:  # raised after the ledger was saved
            raise refused
        threading.Thread(target=self._beat, daemon=True).start()
        if self.watchdog:
            threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        """At the cap, interrupt the main thread whatever it is doing (an import, hashing, a loop, a wait)."""
        while not self._stop.wait(0.05):
            if self.used() >= self.cap:
                _SIG["message"] = (f"BUDGET EXCEEDED (F9): stage 2 reached its cap of {self.cap:.0f} s "
                                   "(watchdog: the running step was interrupted)")
                signal.pthread_kill(threading.main_thread().ident, signal.SIGUSR1)
                return

    def _beat(self):
        while not self._stop.wait(self.hb):
            with self._locked() as d:
                d["intervals"][self.iv_id - 1]["heartbeat"] = time.time()

    def used(self):
        return self.base + (time.time() - self.t0)

    def check(self, where=""):
        if self.used() >= self.cap:
            _SIG["stopping"] = True
            raise BudgetExceeded(f"BUDGET EXCEEDED (F9): stage 2 used {self.used():.1f} s of {self.cap:.0f} s"
                                 + (f" ({where})" if where else ""))

    def close(self, status):
        """End the interval and decide the final status: a PASS whose launch ends at or past the cap becomes
        BUDGET_CAP_REVIEW_REQUIRED (whatever it published stays as written). Returns (final status, cumulative use)."""
        if self.iv_id is None:
            return status, None
        self._stop.set()
        with self._locked() as d:
            t = time.time()
            iv = d["intervals"][self.iv_id - 1]
            iv.update(end=t, heartbeat=t, end_utc=utc())
            used = self.total(d)
            if status == "PASS" and used >= self.cap:
                iv["status_before_close"], status = "PASS", REVIEW_STATUS
            iv.update(status=status, used_seconds_at_end=round(used, 6))
            if self.published:
                iv["published"] = dict(self.published)
            d["used_seconds"] = round(used, 3)
        return status, used


# ------------------------------------------------------------ inputs


def code_match(path, globs):
    return any(os.path.dirname(path) == os.path.dirname(g) and fnmatch.fnmatch(os.path.basename(path), os.path.basename(g)) for g in globs)


def code_changes(ctx):
    """Files of the frozen code tree (run_e2c.CODE_GLOBS, same non-recursive matching) changed since the
    stage-1 acceptance: {path: A / M / D}."""
    def tree(rev):
        out = {}
        for line in git(ctx["code_git_root"], "ls-tree", "-r", rev).splitlines():
            meta, path = line.split("\t", 1)
            if code_match(path, ctx["R"].CODE_GLOBS):
                out[path] = meta.split()[2]
        return out
    a, b = tree(ctx["code_base_commit"]), tree("HEAD")
    return {f: ("A" if f not in a else "D" if f not in b else "M") for f in sorted(set(a) | set(b)) if a.get(f) != b.get(f)}


def reference_records(ctx):
    refs = []
    for g in ctx["reference_globs"]:
        for f in sorted(glob.glob(os.path.join(ctx["reference_root"], g))):
            raw = open(f, "rb").read()
            d = json.loads(gzip.decompress(raw) if f.endswith(".gz") else raw)
            if isinstance(d, dict) and d.get("batch_chain"):
                refs.append({"path": os.path.relpath(f, ctx["reference_root"]), "sha256": sha256_bytes(raw), "seed": d["seed"],
                             "batch_chain": d["batch_chain"], "first_batch_sha256": d.get("first_batch_sha256")})
    refs.sort(key=lambda r: r["path"])
    digest = sha256_bytes("".join(f"{r['path']}:{r['sha256']}\n" for r in refs).encode())
    return refs, digest


def prestart(ctx, expected_commit):
    """Refused (5) unless the reviewed commit is checked out unchanged and every frozen input is the approved one."""
    R, bad = ctx["R"], []
    head = git(ctx["git_root"], "rev-parse", "HEAD").strip()
    if not (expected_commit and R.HEX40.match(expected_commit)):
        bad.append("--expected-commit must be the 40-hex reviewed commit")
    elif head != expected_commit:
        bad.append(f"HEAD {head[:12]} is not the reviewed commit {expected_commit[:12]}")
    out_rel = os.path.relpath(os.path.realpath(ctx["out"]), os.path.realpath(ctx["git_root"])) + "/"
    dirty = [ln for ln in git(ctx["git_root"], "status", "--porcelain", "--untracked-files=all").splitlines()
             if not ln[3:].strip('"').startswith(out_rel)]
    if dirty:
        bad.append(f"uncommitted changes outside {out_rel}: {dirty[:4]}")
    ch = code_changes(ctx)
    if ch != ctx["allowed_changes"]:
        bad.append(f"code changes since the stage-1 acceptance {ch} differ from the allowed {ctx['allowed_changes']}")
    b = R.basis(ctx["p"])
    if b["preregistration_sha256"] != PREREG_SHA256:
        bad.append(f"preregistration {b['preregistration_sha256'][:12]} is not the approved {PREREG_SHA256[:12]}")
    if b["design_review_sha256"] != DESIGN_REVIEW_SHA256:
        bad.append(f"design review record {b['design_review_sha256'][:12]} is not the approved {DESIGN_REVIEW_SHA256[:12]}")
    lam = lam2 = None
    if sha256_file(ctx["lambda_file"]) != LAMBDA_SELECTED_SHA256:
        bad.append("lambda_selected.json is not the approved 6c23606e")
    elif sha256_file(ctx["calibration_file"]) != CALIBRATION_SHA256:
        bad.append("calibration.json is not the approved a2301dc7")
    else:
        sel, cal = json.load(open(ctx["lambda_file"])), json.load(open(ctx["calibration_file"]))["selection_summary"]
        lam, lam2 = sel["lambda"], sel["lambda2"]
        if (lam, lam2) != (cal["selected_lambda"], cal["lambda2"]):
            bad.append("lambda / lambda2 differ between lambda_selected.json and calibration.json")
    import numpy
    import torch
    env = {"python": sys.version, "torch": torch.__version__, "numpy": numpy.__version__}
    rec = json.load(open(ctx["environment_file"]))
    if {k: rec.get(k) for k in env} != env:
        bad.append(f"environment {env} differs from the stage-1 record {({k: rec.get(k) for k in env})}")
    refs, digest = reference_records(ctx)
    if len(refs) != ctx["reference_count"] or digest != ctx["reference_digest"]:
        bad.append(f"stage-1 reference chains: {len(refs)} files, digest {digest[:12]}; approved {ctx['reference_count']}, "
                   f"{ctx['reference_digest'][:12]}")
    if bad:
        raise S2Stop(5, "REFUSED: " + "; ".join(bad))
    return {"head": head, "basis": b, "code_changes": ch, "environment": env, "lambda": lam, "lambda2": lam2, "references": refs,
            "references_digest": digest}


def e1_sets(ctx):
    """7.4 step 1. Returns (record, problems)."""
    bad, root = [], ctx["git_root"]
    for rel, keys in ctx["e1_anchors"]:
        v = json.load(open(os.path.join(root, rel)))
        for k in keys:
            v = (v or {}).get(k)
        if v != ctx["e1_manifest_sha256"]:
            bad.append(f"{rel} {'/'.join(keys)} is not the E1 manifest {ctx['e1_manifest_sha256'][:12]}")
    if subprocess.run(["git", "diff", "--quiet", ctx["e1_archive_commit"], "HEAD", "--", *ctx["e1_git_paths"]], cwd=root).returncode:
        bad.append("E1's sets or freeze records changed since E1's archive commit")
    if git(root, "status", "--porcelain", "--untracked-files=all", "--", *ctx["e1_git_paths"]).strip():
        bad.append("E1's sets or freeze records have uncommitted changes")
    sd = ctx["sets_dir"]
    mpath = os.path.join(sd, "manifest.json")
    msha = sha256_file(mpath)
    if msha != ctx["e1_manifest_sha256"]:
        bad.append(f"sets/manifest.json {msha[:12]} is not {ctx['e1_manifest_sha256'][:12]}")
    man = json.load(open(mpath))
    if sorted(os.listdir(sd)) != sorted([n + ".jsonl" for n in man] + ["manifest.json"]):
        bad.append("the set directory holds other files than the manifest lists")
    if sorted(n for n in man if "k4" not in n) != sorted(U_SETS + NON_U_K2_SETS):
        bad.append("the K=2 sets are not the eight of E1")
    files = {}
    for n in sorted(man):
        p = os.path.join(sd, n + ".jsonl")
        if not os.path.exists(p):
            bad.append(f"{n} missing")
            continue
        raw = open(p, "rb").read()
        files[n] = {"sha256": sha256_bytes(raw), "rows": len(raw.splitlines())}
        if files[n]["sha256"] != man[n]["sha256"] or files[n]["rows"] != man[n]["rows"]:
            bad.append(f"{n} differs from the manifest")
    return {"manifest_sha256": msha, "files": files}, bad


def appendix_a(prereg_path):
    """The Appendix A script (code block + final newline, as run in the design stage) and its verbatim output."""
    t = open(prereg_path, encoding="utf-8").read()
    i = t.index("## 附录 A")
    j = t.index("```python\n", i) + len("```python\n")
    k = t.index("\n```", j)
    script = t[j:k] + "\n"
    o = t.index("输出（逐字）", k)
    a = t.index("```\n", o) + 4
    b = t.index("\n```", a)
    stdout = t[a:b] + "\n"
    letters = re.search(r'^LETTERS = "([A-Za-z]+)"$', script, re.M).group(1)
    if sha256_bytes(script.encode()) != APPENDIX_A_SCRIPT_SHA256 or sha256_bytes(stdout.encode()) != APPENDIX_A_STDOUT_SHA256:
        raise S2Stop(5, "REFUSED: the Appendix A script or its output differ from the approved text")
    return script, stdout, letters


# ------------------------------------------------------------ the enumerating jobs (real) and their stubs (tests)


def run_appendix_a(ctx, script, att, ledger):
    d = os.path.join(att, "appendix_a_run")
    os.mkdir(d)
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}
    if ctx["test"]:
        argv = [sys.executable, "-I", ctx["cfg"]["stub_appendix_script"], ctx["cfg"]["stub_appendix_stdout"], TEST_DIR]
    else:
        path = os.path.join(d, "keyspace.py")  # the design-stage name; sha256 checked above
        open(path, "w").write(script)
        argv = [sys.executable, "-I", path, ctx["sets_dir"]]
    rc, out, err = run_bounded(argv, ledger, "appendix_a", att, d, env)
    if rc:
        raise S2Stop(4, f"RUN ERROR: Appendix A script exited {rc}: {err.strip()[-300:]}")
    return out


def run_keyspace_job(ctx, att, ledger):
    out = os.path.join(att, "keyspace_stage2.json")
    if ctx["test"]:
        argv = [sys.executable, ctx["cfg"]["stub_keyspace_job"], out]
        env = dict(os.environ, E2C_S2_STUB_KEYSPACE_STAGE="2")
    else:
        argv = [sys.executable, os.path.join(HERE, "e2c_stage4.py"), "keyspace", "--out", out]
        env = dict(os.environ, E2C_KEYSPACE_STAGE="2")  # only in the job's own environment
    rc, _, err = run_bounded(argv, ledger, "keyspace", att, ROOT, env)
    if rc:
        raise S2Stop(4, f"RUN ERROR: keyspace job exited {rc}: {err.strip()[-300:]}")
    if not os.path.exists(out):
        raise S2Stop(6, "RESULT CHECK FAILED: the keyspace job wrote no record")
    return json.load(open(out))


def key_rules(letters, tick=lambda: None):
    """e2c_test2.key / held against E1's body_key / is_heldout on both statement orders of every key."""
    import e2c_test2 as T
    from e_common import body_key, is_heldout
    total = held = mism = 0
    for l1, l2 in itertools.combinations(letters, 2):
        for d1 in DIG:
            for d2 in DIG:
                if d1 == d2:
                    continue
                total += 1
                if total % 2000 == 0:
                    tick()
                k = T.key([(l1, d1), (l2, d2)])
                h = T.held(k)
                held += h
                for b in (f"{l1}={d1};{l2}={d2};", f"{l2}={d2};{l1}={d1};"):
                    mism += body_key(b) != k or is_heldout(b) != h
    return {"letters": len(letters), "keys": total, "heldout": held, "mismatches": mism}


def non_u_heldout(sets_dir):
    import e2c_test2 as T
    out = {}
    for n in NON_U_K2_SETS:
        c = 0
        for line in open(os.path.join(sets_dir, n + ".jsonl")):
            r = json.loads(line)
            for b in [r["body"]] + [x["body"] for x in r.get("root_swap", [])]:
                c += T.held(T.key(T.stmts(b)))
        out[n] = c
    return out


def stub_stream(cfg, seed):
    """Synthetic stream (tests): bodies over symbols that are no letters, so no real key occurs."""
    import torch
    import e2c_test2 as T
    letters = cfg["key_rule_letters"]
    rng = random.Random(1_000_000 + seed + (7 if seed in cfg.get("stub_nondet_seeds", []) else 0))

    def draw():
        while True:
            (l1, l2), (d1, d2) = rng.sample(letters, 2), rng.sample(DIG, 2)
            body = f"{l1}={d1};{l2}={d2};"
            if not T.held(T.key(T.stmts(body))):
                return body + f"|{l1}?", d1

    def encode(rows):
        x = torch.tensor([list((p + a).encode()) for p, a in rows], dtype=torch.long)
        return x, x[:, -1].clone()
    return draw, encode


def stream_check(ctx, seed, extra_points):
    """One training stream as train_e2c.py draws and hashes it: per update `batch` accepted samples of
    train_sample_k2(train_rng_k2(seed)), x = encode_rows(rows), HashChain over x, chain logged when
    step1 % 100 == 0 or step1 == steps (and at the reference points); every sample checked with e2c_test2.held."""
    import e2c_common as C
    import e2c_test2 as T
    cfg, updates, batch = ctx["cfg"], ctx["updates"], ctx["batch"]
    if ctx["test"]:
        draw, encode = stub_stream(cfg, seed)
        generator = "synthetic stub (tests)"
    else:
        __import__("e_common")  # puts gen_gate_a on sys.path, as train_e2c.py's own import of e_common does
        from data import encode_rows
        from e_task import train_rng_k2, train_sample_k2
        rng = train_rng_k2(seed)
        draw, encode = (lambda: train_sample_k2(rng)), encode_rows
        generator = "e_task.train_rng_k2 / train_sample_k2, gen_gate_a/data.encode_rows, e2c_common.HashChain"
    chain, log, hits, n, first, extra = C.HashChain(), {}, 0, 0, None, set(extra_points)
    for step in range(updates):
        rows = [draw() for _ in range(batch)]
        step1 = step + 1
        if ctx["test"]:
            rows = test_hooks(cfg, seed, step1, rows)
        x, _ = encode(rows)
        if step == 0:
            first = hashlib.sha256(x.numpy().tobytes()).hexdigest()
        cv = chain.update(x)
        if step1 % 100 == 0 or step1 == updates or step1 in extra:
            log[str(step1)] = cv
        n += len(rows)
        hits += sum(T.held(T.key(T.stmts(p.split("|")[0]))) for p, _ in rows)
    return {"seed": seed, "updates": updates, "batch": batch, "accepted_samples": n, "heldout_hits": hits,
            "first_batch_sha256": first, "batch_chain": log, "generator": generator}


def test_hooks(cfg, seed, step1, rows):
    if cfg.get("stub_sleep_per_update"):
        time.sleep(cfg["stub_sleep_per_update"])
    inj = cfg.get("stub_inject_heldout")
    if inj and inj["seed"] == seed and inj["update"] == step1:
        rows = [(inj["body"] + "|" + inj["body"][0] + "?", inj["body"][2])] + rows[1:]
    mut = cfg.get("stub_mutate_file")
    if mut and mut["seed"] == seed and mut["update"] == step1:
        with open(mut["path"], "a") as f:
            f.write(mut.get("text", " "))
    if cfg.get("stub_open_checkpoint") == seed and step1 == 1:
        open(os.path.join(cfg["stub_scratch"], "x.pt"), "w").close()
    return rows


def v2_worker(a):
    ctx = context()
    att = a.attempt
    points = json.load(open(os.path.join(att, "v2_points.json")))
    for s in [int(x) for x in a.seeds.split(",")]:
        if ctx["test"] and ctx["cfg"].get("stub_skip_seed") == s:
            continue
        res = stream_check(ctx, s, points.get(str(s), []))
        write_once(os.path.join(att, "v2", f"seed_{s:03d}.json"), canon(res))
        print(f"V2 seed {s}: {res['accepted_samples']} accepted samples, {res['heldout_hits']} held-out", flush=True)


def run_v2(ctx, att, ledger, log):
    """The 33 streams in `workers` processes; returns the per-seed results."""
    refs = ctx["refs"]
    points = {}
    for r in refs:
        for u in r["batch_chain"]:
            u = int(u)
            if not (u % 100 == 0 or u == ctx["updates"]):
                points.setdefault(str(r["seed"]), set()).add(u)
    write_once(os.path.join(att, "v2_points.json"), canon({k: sorted(v) for k, v in points.items()}))
    os.makedirs(os.path.join(att, "v2"), exist_ok=True)
    chunks = [SEEDS_33[i::ctx["workers"]] for i in range(ctx["workers"])]
    procs = []
    env = dict(os.environ, E2C_S2_WORKER="1")
    try:
        for i, ch in enumerate(chunks):
            f = open(os.path.join(att, f"v2_worker_{i}.txt"), "w")
            argv = [sys.executable, os.path.abspath(__file__), "_v2-worker", "--attempt", att, "--seeds", ",".join(map(str, ch))]
            assert os.path.isabs(argv[0])
            procs.append((subprocess.Popen(child_argv(argv), cwd=ROOT, env=env, stdout=f, stderr=f, start_new_session=True), f))
        log(f"V2: {len(SEEDS_33)} seeds in {len(procs)} worker processes, {ctx['updates']} x {ctx['batch']} samples each")
        while any(p.poll() is None for p, _ in procs):
            ledger.check("while the V2 workers run")
            for p, _ in procs:
                if p.poll() not in (None, 0):
                    raise S2Stop(3 if p.returncode == 3 else 4, f"V2 worker exited {p.returncode} (see v2_worker_*.txt)")
            time.sleep(0.2)
        for p, _ in procs:
            if p.returncode:
                raise S2Stop(3 if p.returncode == 3 else 4, f"V2 worker exited {p.returncode} (see v2_worker_*.txt)")
    finally:
        for p, f in procs:
            if p.poll() is None:
                kill_group(p)
            else:
                end_group(p)
            f.close()
    res = {}
    for s in SEEDS_33:
        path = os.path.join(att, "v2", f"seed_{s:03d}.json")
        if not os.path.exists(path):
            raise S2Stop(6, f"RESULT CHECK FAILED: V2 wrote no result for seed {s}")
        res[s] = json.load(open(path))
    return res


def v2_check(ctx, res, nonu):
    """V2 integrity: every seed complete and free of held-out keys, chains equal to the stage-1 records."""
    bad, compared = [], 0
    U, B = ctx["updates"], ctx["batch"]
    if sorted(res) != SEEDS_33 or len(set(SEEDS_33)) != 33 or ctx["R"].training_stream_seeds() != SEEDS_33:
        bad.append("the seeds are not the 33 of the preregistration and of run_e2c.training_stream_seeds()")
    for s, r in sorted(res.items()):
        if (r["seed"], r["updates"], r["batch"], r["accepted_samples"]) != (s, U, B, U * B):
            bad.append(f"seed {s}: {r['accepted_samples']} accepted samples, not {U} x {B}")
        if r["heldout_hits"]:
            bad.append(f"seed {s}: {r['heldout_hits']} held-out samples in the training stream")
    for ref in ctx["refs"]:
        mine = res.get(ref["seed"], {})
        for u, cv in ref["batch_chain"].items():
            compared += 1
            if mine.get("batch_chain", {}).get(u) != cv:
                bad.append(f"{ref['path']}: batch chain at update {u} differs")
        if ref.get("first_batch_sha256") and mine.get("first_batch_sha256") != ref["first_batch_sha256"]:
            bad.append(f"{ref['path']}: first batch differs")
    for n, c in nonu.items():
        if c:
            bad.append(f"E1's non-U set {n} holds {c} held-out keys")
    return bad, compared


# ------------------------------------------------------------ verify


def attempts_of(out):
    d = os.path.join(out, "attempts")
    return sorted(x for x in os.listdir(d) if x.isdigit()) if os.path.isdir(d) else []


def new_attempt(out):
    n = int(attempts_of(out)[-1]) + 1 if attempts_of(out) else 1
    while True:
        d = os.path.join(out, "attempts", f"{n:02d}")
        try:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            os.mkdir(d)
            return d
        except FileExistsError:
            n += 1


def compare_attempts(out, att):
    """Every output of an earlier attempt equals this attempt's (the computation is deterministic)."""
    names = ["e1_sets.json", "appendix_a_stdout.txt", "keyspace_stage2.json", "key_rules.json", "non_u_sets.json"]
    for prev in attempts_of(out):
        pd = os.path.join(out, "attempts", prev)
        if os.path.realpath(pd) == os.path.realpath(att):
            continue
        rel = names + [os.path.join("v2", f) for f in sorted(os.listdir(os.path.join(pd, "v2")))] if os.path.isdir(os.path.join(pd, "v2")) else names
        for n in rel:
            a, b = os.path.join(pd, n), os.path.join(att, n)
            if os.path.exists(a) and os.path.exists(b) and open(a, "rb").read() != open(b, "rb").read():
                raise S2Stop(3, f"INTEGRITY FAILURE: {n} of this attempt differs from attempt {prev}")


def sweep_temporaries(dirs, dest, log):
    """Temporary names of a write-once that a crash interrupted (never published): kept, moved out of the way."""
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, ".*.tmp.*"))):
            os.makedirs(dest, exist_ok=True)
            os.replace(f, os.path.join(dest, os.path.basename(f)))
            log(f"moved {os.path.basename(f)} (a temporary file of an interrupted write) to {os.path.relpath(dest, d)}")


def verify_state_problem(out, a, record_path, stop_path):
    for name in REVIEW_RECORDS.values():
        if os.path.exists(os.path.join(out, name)):
            return f"REFUSED: {name} exists: a budget review is pending; only the review resolves it (no resume)"
    if os.path.exists(record_path):
        return "REFUSED: verify is complete; stage2_verify.json is written once"
    if os.path.exists(stop_path):
        return f"REFUSED: a verify attempt stopped ({json.load(open(stop_path)).get('status')}); the review decides"
    if attempts_of(out) and not a.resume:
        return "REFUSED: verify was launched before; continue with --resume"
    if a.resume and not attempts_of(out):
        return "REFUSED: --resume without an earlier attempt"
    return None


def cmd_verify(a, ctx, ledger):
    out, R = ctx["out"], ctx["R"]
    record_path, stop_path = os.path.join(out, "stage2_verify.json"), os.path.join(out, "verify_stop.json")
    att, status, code, summary, review = None, "ERROR", 4, {}, None

    def log(msg):
        if att:
            with open(os.path.join(att, "driver_log.txt"), "a") as f:
                f.write(f"{utc()} {msg}\n")
        print(msg, file=sys.stderr, flush=True)

    def save(name, obj):
        data = obj if isinstance(obj, bytes) else (obj.encode() if isinstance(obj, str) else canon(obj))
        write_once(os.path.join(att, name), data)

    try:
        bad = verify_state_problem(out, a, record_path, stop_path)
        if bad:
            raise S2Stop(5, bad)
        inp = prestart(ctx, a.expected_commit)
        ctx["refs"] = inp["references"]
        e1, bad = e1_sets(ctx)
        if bad:
            raise S2Stop(5, "REFUSED: " + "; ".join(bad))
        ledger.check("after the start checks")
        att = new_attempt(out)
        sweep_temporaries([out], os.path.join(att, "temporaries_of_an_interrupted_write"), log)
        log(f"verify ({'test' if ctx['test'] else 'real'}) attempt {os.path.basename(att)} at {inp['head'][:12]}; "
            f"authorization: {a.authorization or '-'}; budget used {ledger.used():.1f} s of {ledger.cap:.0f} s")
        save("e1_sets.json", e1)
        log(f"E1 sets: {len(e1['files'])} files equal to the manifest {e1['manifest_sha256'][:12]}")
        script, expected, letters = appendix_a(ctx["p"]["prereg"])
        stdout = run_appendix_a(ctx, script, att, ledger)
        save("appendix_a_stdout.txt", stdout)
        if stdout != expected:
            raise S2Stop(3, "F11: the Appendix A script's output differs from Appendix A", "F11")
        log("F11: Appendix A output verbatim")
        ks = run_keyspace_job(ctx, att, ledger)
        fmt = R.keyspace_format_problem(ks)
        if fmt:
            raise S2Stop(3, f"INTEGRITY FAILURE: keyspace job output: {fmt}")
        if ks["counts"] != R.KEYSPACE_COUNTS:
            raise S2Stop(3, f"F11: counts {ks['counts']} differ from Appendix A {R.KEYSPACE_COUNTS}", "F11")
        log(f"F11: counts equal to Appendix A {ks['counts']}")
        kl = ctx["cfg"].get("key_rule_letters") if ctx["test"] else letters
        kr = key_rules(kl, tick=lambda: ledger.check("during the key-rule check"))
        import e2c_test2 as T
        from e_common import LETTERS
        want_keys = len(kl) * (len(kl) - 1) // 2 * 90
        want_h = ctx["cfg"]["key_rule_expected_heldout"] if ctx["test"] else ks["counts"]["H"]
        kr["pass"] = (kr["mismatches"] == 0 and kr["keys"] == want_keys and kr["heldout"] == want_h
                      and (ctx["test"] or letters == LETTERS == T.LETTERS))
        save("key_rules.json", kr)
        if not kr["pass"]:
            raise S2Stop(3, f"INTEGRITY FAILURE: key rules {kr}, expected {want_keys} keys, {want_h} held-out, letters as Appendix A")
        log(f"key rules: {kr['keys']} keys, {kr['heldout']} held-out, no mismatch")
        nonu = non_u_heldout(ctx["sets_dir"])
        save("non_u_sets.json", nonu)
        ledger.check("before V2")
        res = run_v2(ctx, att, ledger, log)
        bad, compared = v2_check(ctx, res, nonu)
        if bad:
            raise S2Stop(3, "INTEGRITY FAILURE (V2): " + "; ".join(bad[:8]), "INTEGRITY_FAILURE_V2")
        log(f"V2: 33 seeds, {compared} stage-1 chain points equal, no held-out key")
        e1b, bad = e1_sets(ctx)
        if bad or e1b != e1:
            raise S2Stop(3, "INTEGRITY FAILURE: E1's set files changed during the run")
        if R.basis(ctx["p"]) != inp["basis"]:
            raise S2Stop(3, "INTEGRITY FAILURE: the code tree or a frozen document changed during the run")
        compare_attempts(out, att)
        streams = canon({str(s): r for s, r in sorted(res.items())})
        record = {
            "stage": 2, "command": "verify", "mode": "test" if ctx["test"] else "real", "status": "PASS",
            "reviewed_commit": inp["head"], "basis": inp["basis"], "code_changes_since_stage1": inp["code_changes"],
            "environment": inp["environment"],
            "inputs": {"lambda_selected_sha256": LAMBDA_SELECTED_SHA256, "calibration_sha256": CALIBRATION_SHA256,
                       "stage1_reference_chains": {"files": len(ctx["refs"]), "digest_sha256": inp["references_digest"]}},
            "e1_sets": e1,
            "appendix_a": {"script_sha256": APPENDIX_A_SCRIPT_SHA256, "expected_stdout_sha256": APPENDIX_A_STDOUT_SHA256,
                           "stdout_sha256": sha256_bytes(stdout.encode()), "verbatim_equal": True},
            "keyspace": ks, "f11": {"counts": ks["counts"], "appendix_a": R.KEYSPACE_COUNTS, "pass": True},
            "key_rules": kr,
            "v2": {"seeds": SEEDS_33, "unique_seeds": len(set(SEEDS_33)), "updates": ctx["updates"], "batch": ctx["batch"],
                   "accepted_samples_per_seed": ctx["updates"] * ctx["batch"], "heldout_hits_total": 0,
                   "streams_sha256": sha256_bytes(streams), "generator": res[SEEDS_33[0]]["generator"],
                   "stage1_chain_points_compared": compared, "non_u_sets_heldout_keys": nonu, "pass": True},
        }
        scan = leak_scan(files_under(att), [streams, canon(record)])
        if scan["key_like_hits"]:
            raise S2Stop(3, f"INTEGRITY FAILURE: {scan['key_like_hits']} key-like strings in the outputs (no key list is written)")
        record["leak_scan"] = scan
        data = canon(record)
        sp = os.path.join(out, "v2_streams.json")
        if os.path.exists(sp) and open(sp, "rb").read() != streams:
            raise S2Stop(3, "INTEGRITY FAILURE: v2_streams.json exists with other content (written once)")
        # both files are written and fsynced under temporary names first; after the last budget check only link()
        staged = [None, None]
        try:
            staged[0] = None if os.path.exists(sp) else stage_file(sp, streams)
            staged[1] = stage_file(record_path, data)
            test_delay(ctx, "verify")
            with publish_window():
                ledger.check("before writing v2_streams.json and stage2_verify.json")
                t_check = time.time()
                test_delay(ctx, "verify_inside_window")
                if staged[0]:
                    publish(staged[0], sp)
                    staged[0] = None
                if ctx["test"] and ctx["cfg"].get("stub_crash_after") == "v2_streams":
                    os._exit(9)
                publish(staged[1], record_path)
                staged[1] = None
                _SIG["published"] = True
                ledger.published = {"stage2_verify.json": sha256_bytes(data), "v2_streams.json": sha256_bytes(streams)}
                window, over = time.time() - t_check, ledger.used() - ledger.cap
        finally:
            discard(*staged)
        summary = {"record_sha256": sha256_bytes(data), "v2_streams_sha256": sha256_bytes(streams),
                   "publish_window_seconds": round(window, 6)}
        if _SIG["note"]:
            summary["signal_inside_publish_window"] = _SIG["note"]
            log(_SIG["note"])
        log(f"published stage2_verify.json {sha256_bytes(data)} and v2_streams.json; last budget check to both published: "
            f"{window * 1000:.2f} ms; budget used {ledger.used():.3f} s of {ledger.cap:.0f} s")
        if over >= 0:  # the cap passed inside the publish window: published as decided at the last check, but not a PASS
            status, code = REVIEW_STATUS, 7
            review = {"where": "inside the publish window, after the last budget check", "crossed_by_seconds": round(over, 6)}
        else:
            status, code = "PASS", 0
        print(json.dumps({"stage2_verify_sha256": sha256_bytes(data), "v2_streams_sha256": sha256_bytes(streams)}))
    except (S2Stop, BudgetExceeded) as s:
        status, code = s.status, s.code
        log(str(s))
    except Interrupted:
        status, code = "INTERRUPTED", 130
        log("interrupted")
    except CheckpointAccess as e:
        status, code = "INTEGRITY_FAILURE", 3
        log(f"INTEGRITY FAILURE: {e}")
    except Exception as e:  # noqa: BLE001
        status, code = "ERROR", 4
        log(f"RUN ERROR: {e!r}")
    finally:
        shield()
        try:
            if att and code == 3:
                write_once_or_same(stop_path, canon({"status": status, "attempt": os.path.basename(att)}))
            test_delay(ctx, "verify_before_close")
        finally:
            final, used = ledger.close(status)  # the final decision: a PASS that ends past the cap is not a PASS
        if final != status:
            status, code = final, 7
            review = {"where": "after the publication, before the ledger closed", "crossed_by_seconds": round(used - ledger.cap, 6)}
        # bookkeeping of the decision (milliseconds, after the interval): it cannot turn a status into PASS
        if review:
            write_review_record(out, "verify", dict(review, verify_record_sha256=summary["record_sha256"],
                                                    v2_streams_sha256=summary["v2_streams_sha256"],
                                                    attempt=os.path.basename(att), interval=ledger.iv_id, cap_seconds=ledger.cap,
                                                    used_seconds_at_end=round(used, 6)))
            log(f"{REVIEW_STATUS}: the cap was crossed {review['where']} by {review['crossed_by_seconds']:.6f} s; the published "
                f"files stay as written; freeze refuses until the review resolves {REVIEW_RECORDS['verify']}")
        if att:
            write_once(os.path.join(att, "summary.json"), canon(dict(summary, status=status, exit=code, end_utc=utc())))
            log(f"final status {status} (exit {code})")
    return code


def write_review_record(out, command, fields):
    write_once_or_same(os.path.join(out, REVIEW_RECORDS[command]), canon(dict(
        fields, status=REVIEW_STATUS, command=command, written_utc=utc(),
        resolution="only by the review: verify (also with --resume) and freeze refuse while this record exists or "
                   "existed in the history; the published files are never rewritten")))


# ------------------------------------------------------------ freeze


def budget_admission(ctx, record_sha, commit):
    """I2-R2: a freeze needs the stage-2 budget to stand behind the approved verify record. Checked against the
    ledger as committed in the approved commit (not only the working-tree copy, which the launch itself extends):
    the launch that published this record ended as PASS below its cap; no launch is waiting for a budget review;
    the working-tree ledger continues the committed one unchanged; no review or stop record exists, or ever
    existed in the history (deleting one does not resolve it). Returns problems."""
    out, bad = ctx["out"], []
    top = git(out, "rev-parse", "--show-toplevel").strip()
    rel = lambda p: os.path.relpath(os.path.realpath(p), os.path.realpath(top))  # noqa: E731
    for name in list(REVIEW_RECORDS.values()) + ["verify_stop.json"]:
        path = os.path.join(out, name)
        if os.path.exists(path):
            bad.append(f"{name} exists (unresolved)")
        if git(top, "log", "--format=%H", "HEAD", "--", rel(path)).strip():
            bad.append(f"{name} is in the history (only the review resolves it)")
    lpath = os.path.join(out, "budget_ledger_s2.json")
    r = subprocess.run(["git", "show", f"{commit}:{rel(lpath)}"], cwd=top, capture_output=True)
    if r.returncode:
        return bad + ["the budget ledger is not committed with the approved verify record"]
    approved = json.loads(r.stdout)
    pub = [iv for iv in approved["intervals"] if (iv.get("published") or {}).get("stage2_verify.json") == record_sha]
    if len(pub) != 1:
        bad.append("the committed ledger does not name exactly one launch that published the approved record")
    elif not (pub[0].get("status") == "PASS" and pub[0].get("used_seconds_at_end", float("inf")) < pub[0].get("cap_seconds", 0)):
        bad.append(f"the launch that published the record ended as {pub[0].get('status')} at {pub[0].get('used_seconds_at_end')} s "
                   f"of {pub[0].get('cap_seconds')} s")
    if any(iv.get("status") == REVIEW_STATUS for iv in approved["intervals"]):
        bad.append(f"a launch in the committed ledger is {REVIEW_STATUS}")
    now = json.load(open(lpath))["intervals"]
    for i, iv in enumerate(approved["intervals"]):
        cur = now[i] if i < len(now) else None
        if cur != iv and not (cur and iv["end"] is None and "stale" in cur and {k: v for k, v in cur.items() if k != "stale"} == iv):
            bad.append(f"interval {iv['id']} of the working-tree ledger differs from the committed one")
            break
    return bad


def cmd_freeze(a, ctx, ledger):
    out, R, p = ctx["out"], ctx["R"], ctx["p"]
    record_path, receipt_path = os.path.join(out, "stage2_verify.json"), os.path.join(out, "stage2_freeze_receipt.json")
    status, code, review = "ERROR", 4, None
    try:
        if os.path.exists(p["freeze"]) or os.path.exists(receipt_path):
            raise S2Stop(5, f"REFUSED: {os.path.basename(p['freeze'])} exists; the freeze is written once")
        bad = R.git_anchor(record_path, a.approved_verify_commit, a.approved_verify_sha256)
        if bad:
            raise S2Stop(5, "REFUSED: stage2_verify.json is not the approved record: " + "; ".join(bad))
        bad = budget_admission(ctx, a.approved_verify_sha256, a.approved_verify_commit)
        if bad:
            raise S2Stop(5, "REFUSED: the stage-2 budget does not admit a freeze: " + "; ".join(bad))
        rec = json.load(open(record_path))
        if rec.get("status") != "PASS" or rec.get("mode") != ("test" if ctx["test"] else "real"):
            raise S2Stop(5, "REFUSED: the approved record is not a passed verify of this mode")
        sp = os.path.join(out, "v2_streams.json")
        if not os.path.exists(sp) or sha256_file(sp) != rec["v2"]["streams_sha256"]:
            raise S2Stop(5, "REFUSED: v2_streams.json differs from the approved record")
        cp = R.commitment_problem(a.salt_commitment_sha256)
        if cp:
            raise S2Stop(5, f"REFUSED: salt commitment {cp} (only sha256(salt) is accepted, never a salt)")
        ledger.check("after the record checks")
        inp = prestart(ctx, a.expected_commit)
        if inp["basis"] != rec["basis"]:
            raise S2Stop(5, "REFUSED: the code tree or a frozen document changed since the approved verify")
        e1, bad = e1_sets(ctx)
        if bad or e1 != rec["e1_sets"]:
            raise S2Stop(5, "REFUSED: E1's set files differ from the approved verify")
        ledger.check("after the start checks")
        fz = R.make_baseline(p, inp["lambda"], inp["lambda2"], a.salt_commitment_sha256, rec["keyspace"])
        fz["stage2"] = {"verify_record_sha256": a.approved_verify_sha256, "verify_commit": a.approved_verify_commit,
                        "v2_streams_sha256": rec["v2"]["streams_sha256"], "training_stream_seeds": SEEDS_33,
                        "e1_sets_sha256": {n: v["sha256"] for n, v in rec["e1_sets"]["files"].items()},
                        "e1_sets_manifest_sha256": rec["e1_sets"]["manifest_sha256"], "environment": rec["environment"],
                        "mode": rec["mode"]}
        diffs = R.check_baseline(fz, fz["basis"])
        if diffs or fz["basis"] != rec["basis"] or fz["keyspace"] != rec["keyspace"]:
            raise S2Stop(3, f"INTEGRITY FAILURE: the freeze built from the approved record does not pass the launcher's check: {diffs}")
        text = canon(fz)
        if leak_scan(texts=[text])["key_like_hits"]:
            raise S2Stop(3, "INTEGRITY FAILURE: key-like text in the freeze")
        receipt = {"freeze_sha256": sha256_bytes(text), "verify_record_sha256": a.approved_verify_sha256,
                   "verify_commit": a.approved_verify_commit, "salt_commitment_sha256": a.salt_commitment_sha256,
                   "authorization": a.authorization or "-", "staged_utc": utc(), "budget_used_seconds_at_staging": round(ledger.used(), 1),
                   "note": "not trusted by the launcher: stage 3 takes the commit and sha256 from the review"}
        sweep_temporaries([out, os.path.dirname(os.path.abspath(p["freeze"]))],
                          os.path.join(out, f"temporaries_of_an_interrupted_write_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"),
                          lambda m: print(m, file=sys.stderr))
        # freeze and receipt are written and fsynced under temporary names first; after the last budget check only link()
        staged = [None, None]
        try:
            staged[0] = stage_file(p["freeze"], text)
            staged[1] = stage_file(receipt_path, canon(receipt))
            test_delay(ctx, "freeze")
            with publish_window():
                ledger.check("before writing the freeze")
                t_check = time.time()
                try:
                    publish(staged[0], p["freeze"])
                except FileExistsError:
                    raise S2Stop(5, "REFUSED: the freeze file appeared meanwhile; it is written once")
                finally:
                    staged[0] = None
                publish(staged[1], receipt_path)
                staged[1] = None
                _SIG["published"] = True
                ledger.published = {"e2c_workload_freeze.json": sha256_bytes(text),
                                    "stage2_freeze_receipt.json": sha256_file(receipt_path)}
                window, over = time.time() - t_check, ledger.used() - ledger.cap
        finally:
            discard(*staged)
        fsha = sha256_file(p["freeze"])
        if fsha != sha256_bytes(text):
            raise S2Stop(3, "INTEGRITY FAILURE: the written freeze differs from the built one")
        print(f"last budget check to freeze and receipt published: {window * 1000:.2f} ms", file=sys.stderr)
        if over >= 0:  # the cap passed inside the publish window: written as decided at the last check, but not a PASS
            status, code = REVIEW_STATUS, 7
            review = {"where": "inside the publish window, after the last budget check", "crossed_by_seconds": round(over, 6)}
        else:
            status, code = "PASS", 0
    except (S2Stop, BudgetExceeded) as s:
        status, code = s.status, s.code
        print(s, file=sys.stderr)
    except Interrupted:
        status, code = "INTERRUPTED", 130
    except Exception as e:  # noqa: BLE001
        status, code = "ERROR", 4
        print(f"RUN ERROR: {e!r}", file=sys.stderr)
    finally:
        shield()
        try:
            test_delay(ctx, "freeze_before_close")
        finally:
            final, used = ledger.close(status)  # the final decision: a PASS that ends past the cap is not a PASS
    if final != status:
        status, code = final, 7
        review = {"where": "after the publication, before the ledger closed", "crossed_by_seconds": round(used - ledger.cap, 6)}
    if review:
        write_review_record(out, "freeze", dict(review, freeze_sha256=ledger.published.get("e2c_workload_freeze.json"),
                                                receipt_sha256=ledger.published.get("stage2_freeze_receipt.json"),
                                                verify_record_sha256=a.approved_verify_sha256, interval=ledger.iv_id,
                                                cap_seconds=ledger.cap, used_seconds_at_end=round(used, 6)))
        print(f"{REVIEW_STATUS}: the cap was crossed {review['where']} by {review['crossed_by_seconds']:.6f} s; the freeze and its "
              f"receipt stay as written; {REVIEW_RECORDS['freeze']} is for the review (exit 7)", file=sys.stderr)
    if code == 0:
        print(json.dumps({"freeze_sha256": ledger.published["e2c_workload_freeze.json"]}))
        print("freeze written once; commit it on its own, push, and pass that commit and its sha256 from the review "
              "to run_e2c.py (--approved-stage2-commit / --approved-freeze-sha256)", file=sys.stderr)
    return code



# ------------------------------------------------------------ check (read-only)


def cmd_check(a, ctx):
    R, p, out = ctx["R"], ctx["p"], ctx["out"]
    rep, ok = {}, True
    pending = [n for n in list(REVIEW_RECORDS.values()) + ["verify_stop.json"] if os.path.exists(os.path.join(out, n))]
    lp = os.path.join(out, "budget_ledger_s2.json")
    if os.path.exists(lp):
        led = json.load(open(lp))
        rep["budget"] = {"used_seconds": led.get("used_seconds"), "intervals": [(iv["id"], iv["label"], iv["status"]) for iv in led["intervals"]]}
        if any(iv["status"] == REVIEW_STATUS for iv in led["intervals"]):
            pending.append(f"a ledger interval is {REVIEW_STATUS}")
    if pending:
        rep["review_pending"], ok = pending, False
    rp = os.path.join(out, "stage2_verify.json")
    if os.path.exists(rp):
        rec = json.load(open(rp))
        sp = os.path.join(out, "v2_streams.json")
        rep["verify_record"] = {"sha256": sha256_file(rp), "status": rec.get("status"),
                                "v2_streams_equal": os.path.exists(sp) and sha256_file(sp) == rec["v2"]["streams_sha256"]}
        ok &= rec.get("status") == "PASS" and rep["verify_record"]["v2_streams_equal"]
        if a.approved_verify_commit:
            rep["verify_record"]["anchor"] = R.git_anchor(rp, a.approved_verify_commit, a.approved_verify_sha256)
            ok &= not rep["verify_record"]["anchor"]
    else:
        rec, ok = None, False
    if os.path.exists(p["freeze"]):
        fz = json.load(open(p["freeze"]))
        now = R.basis(p)
        rep["freeze"] = {"sha256": sha256_file(p["freeze"]), "check_baseline": R.check_baseline(fz, now),
                         "keyspace_equals_record": bool(rec) and fz.get("keyspace") == rec.get("keyspace"),
                         "record_sha256_equals": bool(rec) and fz.get("stage2", {}).get("verify_record_sha256") == sha256_file(rp)}
        ok &= not rep["freeze"]["check_baseline"] and rep["freeze"]["keyspace_equals_record"] and rep["freeze"]["record_sha256_equals"]
        if a.approved_freeze_commit:
            rep["freeze"]["anchor"] = R.git_anchor(p["freeze"], a.approved_freeze_commit, a.approved_freeze_sha256)
            ok &= not rep["freeze"]["anchor"]
    rep["pass"] = bool(ok)
    print(json.dumps(rep, indent=1))
    return 0 if ok else 3


# ------------------------------------------------------------ main


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    sub = ap.add_subparsers(dest="command", required=True)
    v = sub.add_parser("verify", allow_abbrev=False)
    v.add_argument("--expected-commit", required=True, help="the reviewed implementation commit (40 hex)")
    v.add_argument("--authorization", default="")
    v.add_argument("--resume", action="store_true")
    v.add_argument("--accept-stale-supplement", action="store_true",
                   help="book a conservative supplement for intervals left open by a process that is gone")
    f = sub.add_parser("freeze", allow_abbrev=False)
    f.add_argument("--expected-commit", required=True)
    f.add_argument("--approved-verify-commit", required=True)
    f.add_argument("--approved-verify-sha256", required=True)
    f.add_argument("--salt-commitment-sha256", required=True, help="sha256(salt), 64 lowercase hex; never the salt")
    f.add_argument("--authorization", default="")
    f.add_argument("--accept-stale-supplement", action="store_true")
    c = sub.add_parser("check", allow_abbrev=False)
    for k in ("--approved-verify-commit", "--approved-verify-sha256", "--approved-freeze-commit", "--approved-freeze-sha256"):
        c.add_argument(k)
    w = sub.add_parser("_v2-worker", allow_abbrev=False)
    w.add_argument("--attempt", required=True)
    w.add_argument("--seeds", required=True)
    a = ap.parse_args(argv)
    try:
        env_checks(a.command, getattr(a, "authorization", ""))
        if a.command == "_v2-worker":
            install_guards(bool(TEST_DIR))
            try:
                v2_worker(a)
            except CheckpointAccess as e:
                print(f"INTEGRITY FAILURE: {e}", file=sys.stderr)
                return 3
            return 0
        signal.signal(signal.SIGTERM, _on_term)
        signal.signal(signal.SIGINT, _on_term)
        signal.signal(signal.SIGUSR1, _on_budget_signal)
        if a.command == "check":  # read-only: not a stage-2 run, not ledgered
            install_guards(bool(TEST_DIR))
            return cmd_check(a, context())
        # verify / freeze: the launch is ledgered from the start of its process; the ledger (with its watchdog) is
        # opened before anything heavy is imported, and a refused launch is ledgered too
        path, cap, hb, watchdog = ledger_location()
        ledger = Ledger(path, cap, hb, a.command, watchdog)
        ledger.open(a.accept_stale_supplement, a.authorization)
        try:
            install_guards(bool(TEST_DIR))
            ctx = context()
            ledger.check("after loading the code")
        except BaseException as e:
            shield()
            ledger.close(e.status if isinstance(e, (S2Stop, BudgetExceeded)) else "INTERRUPTED" if isinstance(e, Interrupted)
                         else "ERROR")
            raise
        return {"verify": cmd_verify, "freeze": cmd_freeze}[a.command](a, ctx, ledger)
    except (S2Stop, BudgetExceeded) as s:
        print(s, file=sys.stderr)
        return s.code
    except Interrupted:
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"RUN ERROR: {e!r}", file=sys.stderr)
        return 4

if __name__ == "__main__":
    sys.exit(main())
