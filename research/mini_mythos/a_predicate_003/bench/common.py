"""F3B-D1-A-CPU-003 E1-A bench -- shared constants, /proc helpers, pidfd identity handle.

STATUS: WRITTEN, NOT RUN (F3B-D1-A-CPU-003-E1A-PREP-001).  Standard library only, Linux only, no network, no GPU.
Signals are only ever sent through PidfdHandle.send(), which refuses when the process identity cannot be confirmed.
"""
import hashlib
import json
import os
import select
import signal
import time

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
A003_DIR = os.path.dirname(BENCH_DIR)
REPO_ROOT = os.path.abspath(os.path.join(A003_DIR, "..", "..", ".."))
PROBES_DIR = os.path.join(REPO_ROOT, "research", "mini_mythos", "r3_cpu_probes")
CPU001_DIR = os.path.join(PROBES_DIR, "a_predicate")
CPU002_DIR = os.path.join(PROBES_DIR, "a_predicate_002")
PREREG_PATH = os.path.join(A003_DIR, "prereg", "e1_provability_table_v1.json")

# GATED-SPAWN timing budget (seconds)
T_GATE_MAX = 10.0        # a gated process that is neither released nor aborted exits by itself after this long
T_REG_MAX = 5.0          # budget for the observer to verify + register one node
T_NODE_MAX = 120.0       # hard lifetime cap of every bench node (self-termination fail-safe)
T_SETUP = 30.0           # budget for a scenario SETUP phase
T_S0 = 30.0              # budget for the candidate S0 evaluation
T_JANITOR_MAX = 3600.0   # janitor lifetime cap (a full run is expected to take well under this)

EXIT_GATE_ABORT = 111    # gate said abort / gate closed (EOF)
EXIT_GATE_TIMEOUT = 112  # gate stayed silent for T_GATE_MAX
EXIT_CHILD_EXC = 113     # exception in a gated child before / outside its role

SIGIGN_SIGCHLD_BIT = 1 << (signal.SIGCHLD - 1)

# calls that a candidate must not make between the start of preflight and its S0 verdict (instrumented in the supervisor stub)
UNSAFE_CALLS = frozenset({"os.kill", "os.killpg", "signal.pidfd_send_signal", "os.waitpid", "os.waitid", "os.wait", "os.wait3", "os.wait4"})


class IdentityError(RuntimeError):
    """The process behind a pid cannot be confirmed to be the registered one."""


class AlreadyExited(IdentityError):
    """The process had already terminated (zombie or reaped) when its pidfd was opened."""


class ProcUnreadable(RuntimeError):
    pass


def mono():
    return time.monotonic()


def poll_ready(fds, timeout):
    """poll(2)-based readiness (select.select breaks for descriptors >= 1024).  -> set of fds with any event (data, EOF, error)."""
    p = select.poll()
    for fd in fds:
        p.register(fd, select.POLLIN)
    return {fd for fd, _ev in p.poll(int(max(timeout, 0) * 1000))}


def wall():
    return time.time()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def append_jsonl(path, obj):
    """One O_APPEND write of one newline-terminated JSON line (a crash can leave at most a torn final line)."""
    data = (json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        n = os.write(fd, data)
    finally:
        os.close(fd)
    if n != len(data):
        raise OSError("short write to %s: %d of %d" % (path, n, len(data)))


# ---------------------------------------------------------------- /proc readers
def parse_stat(text):
    i = text.rindex(")")
    rest = text[i + 2:].split()
    return {"state": rest[0], "ppid": int(rest[1]), "pgrp": int(rest[2]), "sid": int(rest[3]),
            "starttime": int(rest[19]), "comm": text[text.index("(") + 1:i]}


def read_stat(pid):
    """/proc/<pid>/stat as a dict; None if the process is gone; ProcUnreadable for any other failure."""
    try:
        with open("/proc/%d/stat" % pid) as f:
            return parse_stat(f.read())
    except (FileNotFoundError, ProcessLookupError):
        return None
    except (OSError, ValueError, IndexError) as e:
        raise ProcUnreadable("stat %d: %r" % (pid, e))


def scan_proc():
    """Complete enumeration -> (table, problems).  problems is non-empty when any entry could not be read; a listdir
    failure raises ProcUnreadable (the caller must then report UNKNOWN, never an empty table)."""
    try:
        names = os.listdir("/proc")
    except OSError as e:
        raise ProcUnreadable("listdir /proc: %r" % (e,))
    table, problems = {}, {}
    for n in names:
        if not n.isdigit():
            continue
        pid = int(n)
        try:
            st = read_stat(pid)
        except ProcUnreadable as e:
            problems[pid] = str(e)
            continue
        if st is not None:
            table[pid] = st
    return table, problems


def children_of(table, pid):
    return sorted(p for p, st in table.items() if st["ppid"] == pid)


def descendants_of(table, pid):
    out, frontier = set(), {pid}
    while frontier:
        nxt = {p for p, st in table.items() if st["ppid"] in frontier and p not in out}
        out |= nxt
        frontier = nxt
    return sorted(out)


def fingerprint(pid):
    st = read_stat(pid)
    if st is None:
        return None
    return {"pid": pid, "starttime": st["starttime"], "sid": st["sid"], "pgrp": st["pgrp"], "ppid": st["ppid"], "state": st["state"]}


def read_sigign(pid):
    """SigIgn mask of a process from /proc/<pid>/status (int), None if unreadable."""
    try:
        with open("/proc/%d/status" % pid) as f:
            for line in f:
                if line.startswith("SigIgn:"):
                    return int(line.split()[1], 16)
    except (OSError, ValueError):
        return None
    return None


def fd_links(pid):
    out = {}
    try:
        names = os.listdir("/proc/%d/fd" % pid)
    except OSError:
        return None
    for n in names:
        try:
            out[int(n)] = os.readlink("/proc/%d/fd/%s" % (pid, n))
        except OSError:
            pass
    return out


def read_cmdline(pid):
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            return [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
    except OSError:
        return None


def read_environ(pid):
    try:
        with open("/proc/%d/environ" % pid, "rb") as f:
            return [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
    except OSError:
        return None


# ---------------------------------------------------------------- pidfd identity handle
class PidfdHandle:
    """A pidfd opened for a registered (pid, starttime).  Identity is confirmed at open time by comparing the live
    starttime with the registered one AFTER the pidfd exists (so pid reuse cannot go unnoticed).  Signals are sent
    only through this object.  A pidfd is used for identity/lifecycle only; it says nothing about lineage."""

    def __init__(self, pid, starttime):
        self.pid, self.starttime, self.fd = pid, starttime, None
        fd = os.pidfd_open(pid)                     # ProcessLookupError if the pid is already gone: propagated
        try:
            st = read_stat(pid)
            if st is None or st["starttime"] != starttime:
                raise IdentityError("pid %d starttime %r != registered %r" % (pid, None if st is None else st["starttime"], starttime))
            if self._readable(fd):
                raise AlreadyExited("pid %d already exited when its pidfd was opened" % pid)
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd

    @staticmethod
    def _readable(fd):
        return bool(poll_ready([fd], 0))

    def exited(self):
        """True once the process has terminated (zombie or reaped).  pidfd readability is a lifecycle fact only."""
        return self.fd is None or self._readable(self.fd)

    def send(self, sig):
        """Deliver sig to the identity-confirmed process.  Returns 'sent' | 'gone'."""
        if self.fd is None:
            raise IdentityError("pidfd closed")
        try:
            signal.pidfd_send_signal(self.fd, sig)
        except ProcessLookupError:
            return "gone"
        return "sent"

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def process_is_dead(pid, starttime):
    """Independent death check from /proc only: gone, zombie, or pid now carrying a different starttime."""
    st = read_stat(pid)
    return st is None or st["state"] in ("Z", "X") or st["starttime"] != starttime
