"""GATED-SPAWN child side: the ONLY place in the bench that calls os.fork().

Invariants (ERRATA-002 section 2):
  I1  a freshly forked process performs no experiment action before it reads b"R" from its gate pipe;
  I2  anything other than b"R" (abort byte, EOF because the creator/observer died, or silence for T_GATE_MAX) ends the process;
  I3  the gate WRITE end is never present in the child (it stays with the observer), so a node cannot release itself or a sibling;
  I4  the child first closes every inherited descriptor except {0,1,2,gate_r,control socket}.
WRITTEN, NOT RUN."""
import os
import resource
import signal
import sys

import common as C


def _max_fd():
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    lim = soft if soft != resource.RLIM_INFINITY else 1 << 20
    return min(max(lim, 1024), 1 << 20)


def close_fds_except(keep):
    keep = sorted({k for k in keep if k >= 0})
    lo = 0
    for k in keep:
        if k > lo:
            os.closerange(lo, k)
        lo = k + 1
    os.closerange(lo, _max_fd())


def child_hygiene(keep):
    """Executed first in every gated child: reset inherited signal state, then close inherited descriptors."""
    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGCHLD, signal.SIGUSR1, signal.SIGUSR2, signal.SIGALRM):
        signal.signal(s, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_SETMASK, [])
    signal.set_wakeup_fd(-1)
    close_fds_except(keep)


def gate_wait(gate_r, t_max):
    """Block until exactly b"R" arrives; every other outcome terminates the process (never returns in that case)."""
    deadline = C.mono() + t_max
    while True:
        left = deadline - C.mono()
        if left <= 0:
            os._exit(C.EXIT_GATE_TIMEOUT)
        try:
            ready = C.poll_ready([gate_r], left)
        except OSError:
            os._exit(C.EXIT_GATE_ABORT)
        if not ready:
            os._exit(C.EXIT_GATE_TIMEOUT)
        try:
            b = os.read(gate_r, 1)
        except OSError:
            os._exit(C.EXIT_GATE_ABORT)
        if b == b"R":
            return
        os._exit(C.EXIT_GATE_ABORT)             # b"A", b"" (EOF: write end closed) or anything unexpected


def fork_gated(gate_r, ctrl_fd, entry, t_gate_max=C.T_GATE_MAX, extra_keep=()):
    """Fork a gated child.  Parent: returns the child pid.  Child: hygiene -> gate -> entry(ctrl_fd); never returns.
    `entry` must end in os.execve or os._exit.  Any exception in the child ends it with EXIT_CHILD_EXC."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except (OSError, ValueError):
        pass
    pid = os.fork()
    if pid == 0:
        try:
            child_hygiene({0, 1, 2, gate_r, ctrl_fd} | set(extra_keep))
            gate_wait(gate_r, t_gate_max)
            os.close(gate_r)
            entry(ctrl_fd)
        except BaseException:
            os._exit(C.EXIT_CHILD_EXC)
        os._exit(0)
    return pid
