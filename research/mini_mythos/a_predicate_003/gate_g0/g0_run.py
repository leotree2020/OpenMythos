"""G0 entry: the first minimal controlled process-gate test.  WRITTEN, NOT RUN.  `--execute` is refused without a valid single-use
AUTHORIZATION_E1A_GATE_G0.json (see g0_auth.py); `--check` starts no process and reads no /proc entry of any other process.

Fixed procedure (E1A_GATE_G0_PREREG.md section 3): one observer, ONE sacrificial gated child, no descendants, ZERO signals.
Python-level guards trap kill/killpg/pidfd_send_signal/exec*/spawn*/system/popen/subprocess and allow exactly one os.fork and
waitpid on the one specific child pid.  A Python-level trap is NOT proof that no kernel path exists (stated in the safety review).
There is no code path from here to G1/G2/G3, BV, E1-A cells, the janitor, or any signal.  On any anomaly the run stops, sends no
signal, keeps the evidence and writes MANUAL_DISPOSITION_REQUIRED.json."""
import argparse
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(A003, "bench"))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402

TOKEN = "g0_run.py"                                                 # diagnostic scan marker (command line); never authorizes a signal
HOLD_S = 0.3
SPEC = {"label": "g0", "role": "sleeper", "mode": "none", "children": []}


# ------------------------------------------------------------------ pure helpers (no process is started by any of them)
def bench_code_hash():
    h = []
    for f in sorted(os.listdir(C.BENCH_DIR)):
        if f.endswith(".py"):
            h.append("%s:%s" % (f, C.sha256_file(os.path.join(C.BENCH_DIR, f))))
    return C.sha256_bytes("\n".join(h).encode())


def git_head():
    try:
        gd = os.path.join(C.REPO_ROOT, ".git")
        head = open(os.path.join(gd, "HEAD")).read().strip()
        if not head.startswith("ref: "):
            return head
        ref = head[5:]
        p = os.path.join(gd, ref)
        if os.path.exists(p):
            return open(p).read().strip()
        for line in open(os.path.join(gd, "packed-refs")):
            if line.strip().endswith(" " + ref):
                return line.split()[0]
    except OSError:
        pass
    return "UNKNOWN"


def prereg_sha():
    return C.sha256_file(C.PREREG_PATH)


def current():
    return GA.current_bindings(git_head(), prereg_sha(), bench_code_hash())


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------ Python-level guard
class GuardViolation(Exception):
    pass


class Guard:
    def __init__(self):
        self.violations, self.fork_pids, self.waitpid_calls, self.release_pre = [], [], [], []
        self.fork_calls = 0
        self.watch_fd = None
        self.allowed_pid = None
        self.real = {}
        self.installed = False

    def _trap(self, name):
        def trap(*a, **k):
            self.violations.append({"call": name, "mono": C.mono(), "args": repr(a)[:120]})
            raise GuardViolation("G0 guard refused %s" % name)
        return trap

    def install(self):
        import signal
        import subprocess
        r = self.real
        for modname, mod, names in (("os", os, ("kill", "killpg", "system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp",
                                                "execlpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
                                                "posix_spawn", "posix_spawnp", "forkpty", "wait", "wait3", "wait4", "waitid")),
                                    ("signal", signal, ("pidfd_send_signal", "raise_signal", "pthread_kill")),
                                    ("subprocess", subprocess, ("Popen", "run", "call", "check_call", "check_output"))):
            for n in names:
                if hasattr(mod, n):
                    r[modname + "." + n] = getattr(mod, n)
                    setattr(mod, n, self._trap(modname + "." + n))
        r["os.fork"], r["os.waitpid"], r["os.write"] = os.fork, os.waitpid, os.write

        def g_fork():
            if self.fork_calls >= 1:
                self.violations.append({"call": "os.fork (second)", "mono": C.mono()})
                raise GuardViolation("G0 allows exactly one fork")
            self.fork_calls += 1
            pid = r["os.fork"]()
            if pid != 0:                                     # parent only
                self.fork_pids.append(pid)
                self.allowed_pid = pid
            return pid

        def g_waitpid(pid, options=0):
            t = C.mono()
            if not isinstance(pid, int) or pid <= 0 or pid != self.allowed_pid:
                self.violations.append({"call": "os.waitpid", "mono": t, "args": repr((pid, options))})
                raise GuardViolation("G0 allows waitpid only on the one specific child pid")
            got = r["os.waitpid"](pid, options)
            self.waitpid_calls.append({"pid": pid, "options": options, "returned": got[0], "status": got[1], "mono": t})
            return got

        def g_write(fd, data):
            if self.watch_fd is not None and fd == self.watch_fd and bytes(data) == b"R":
                self.release_pre.append(C.mono())
            return r["os.write"](fd, data)

        os.fork, os.waitpid, os.write = g_fork, g_waitpid, g_write
        self.installed = True

    def uninstall(self):
        import signal
        import subprocess
        for key, fn in self.real.items():
            modname, n = key.split(".", 1)
            setattr({"os": os, "signal": signal, "subprocess": subprocess}[modname], n, fn)
        self.installed = False

    def summary(self):
        return {"violations": self.violations, "fork_calls": self.fork_calls, "fork_pids": self.fork_pids, "waitpid_calls": self.waitpid_calls,
                "release_byte_pre_write_monos": self.release_pre}


# ------------------------------------------------------------------ read-only /proc observation
def ancestors(pid):
    out, seen = set(), set()
    while pid and pid not in seen:
        seen.add(pid)
        st = C.read_stat(pid)
        if st is None:
            break
        out.add(pid)
        pid = st["ppid"]
    return out


def token_scan(exclude):
    """Diagnostic only: live processes (not zombies, not the excluded ancestors/self) whose command line carries the G0 marker."""
    table, problems = C.scan_proc()
    found = []
    for pid, st in sorted(table.items()):
        if pid in exclude or st["state"] in ("Z", "X"):
            continue
        cmd = " ".join(C.read_cmdline(pid) or [])
        if TOKEN in cmd:
            found.append({"pid": pid, "starttime": st["starttime"], "ppid": st["ppid"], "state": st["state"], "cmdline": cmd[:160]})
    return found, problems


def fd_report(pid):
    links = C.fd_links(pid)
    if links is None:
        return None
    out = {}
    for fd, target in links.items():
        access = None
        try:
            with open("/proc/%d/fdinfo/%d" % (pid, fd)) as f:
                for line in f:
                    if line.startswith("flags:"):
                        access = {0: "r", 1: "w", 2: "rw"}.get(int(line.split()[1], 8) & 3)
        except (OSError, ValueError):
            pass
        out[str(fd)] = {"target": target, "access": access}
    return out


def snapshot(name, obs_pid, child_pid=None, with_fds=False, tokens=False, exclude=()):
    table, problems = C.scan_proc()
    kids = C.children_of(table, obs_pid)
    desc = C.descendants_of(table, obs_pid)
    child = None
    if child_pid is not None and child_pid in table:
        st = table[child_pid]
        child = {"pid": child_pid, "starttime": st["starttime"], "ppid": st["ppid"], "state": st["state"], "sid": st["sid"], "pgrp": st["pgrp"]}
    s = {"name": name, "children": kids, "grandchildren": [d for d in desc if d not in kids], "total_procs": len(table),
         "enum_problems": {str(k): v for k, v in problems.items()}, "fd_count": len(os.listdir("/proc/self/fd")), "child": child}
    if with_fds and child_pid is not None:
        s["fds"] = fd_report(child_pid)
    if tokens:
        s["token_residue"], tp = token_scan(set(exclude))
        if tp:
            s["enum_problems"].update({"token_" + str(k): v for k, v in tp.items()})
    s["mono"] = C.mono()                                    # taken AFTER every observation of this snapshot
    return s


def preflight(run_dir, exclude):
    problems = []
    if sys.version_info[:3] != (3, 13, 16):
        problems.append("python %s != 3.13.16" % (sys.version.split()[0],))
    if not sys.flags.dont_write_bytecode:
        problems.append("run with python -B (bytecode writing would modify the code directory)")
    if not hasattr(os, "pidfd_open") or not hasattr(__import__("socket"), "send_fds"):
        problems.append("pidfd_open / send_fds missing")
    sig = C.read_sigign(os.getpid())
    if sig is None or sig & C.SIGIGN_SIGCHLD_BIT:
        problems.append("SIGCHLD ignored or unreadable (a child would be auto-reaped)")
    unresolved = []
    ev_root = GA.EVIDENCE_ROOT
    if os.path.isdir(ev_root):
        for d in sorted(os.listdir(ev_root)):
            p = os.path.join(ev_root, d)
            if d.startswith("g0_") and os.path.isdir(p):
                if os.path.exists(os.path.join(p, "MANUAL_DISPOSITION_REQUIRED.json")) or not os.path.exists(os.path.join(p, "g0_summary.json")):
                    unresolved.append(d)
    if os.path.exists(os.path.join(ev_root, "MANUAL_DISPOSITION_REQUIRED.json")):
        unresolved.append("MANUAL_DISPOSITION_REQUIRED.json")
    table, enum_problems = C.scan_proc()
    kids = C.children_of(table, os.getpid())
    residue, tp = token_scan(exclude)
    enum_problems = dict(enum_problems)
    enum_problems.update({"token_" + str(k): v for k, v in tp.items()})
    unique = not os.path.exists(run_dir)
    if kids:
        problems.append("observer already has children %r" % kids)
    return {"ok": not (problems or unresolved or residue or enum_problems or kids) and unique, "problems": problems, "children": len(kids), "token_residue": residue,
            "unresolved_prior": unresolved, "enumeration_problems": {str(k): v for k, v in enum_problems.items()}, "run_id_unique": unique,
            "fd_count": len(os.listdir("/proc/self/fd")), "total_procs": len(table)}


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True, default=str)
        f.write("\n")


# ------------------------------------------------------------------ the one controlled run
def run(auth, auth_raw, run_id, run_dir):
    import node
    import observer as O
    import proto
    import registry as R

    t0 = C.mono()
    ev = {"run_id": run_id, "auth_expected": auth["bindings"], "bindings_start": current(), "snapshots": {}, "events": {}, "reap": {}, "cleanup": {"rounds": []},
          "deadline_hits": [], "exception": None, "aborted": None, "auth_consumed": False}
    lim = GJ.load_criteria()["limits"]
    guard = Guard()
    obs_pid = os.getpid()
    exclude = ancestors(obs_pid)
    ev["observer"] = {"pid": obs_pid, "sid": C.fingerprint(obs_pid)["sid"], "pgrp": C.fingerprint(obs_pid)["pgrp"]}
    pf = preflight(run_dir, exclude)                                   # BEFORE the run directory exists (uniqueness is part of the preflight)
    ev["preflight"] = pf
    os.mkdir(run_dir)                                                  # exclusive: raises if the directory appeared meanwhile
    with open(os.path.join(run_dir, "authorization_used.json"), "wb") as f:
        f.write(auth_raw)
    rec = obs = None
    try:
        if not pf["ok"]:
            raise RuntimeError("preflight not clean: %r" % {k: pf[k] for k in ("problems", "unresolved_prior", "token_residue", "enumeration_problems", "children")})
        os.makedirs(GA.CONSUMED_DIR, exist_ok=True)
        with open(GA.consumed_marker(auth["authorization_id"]), "x") as f:      # single use: consumed BEFORE the fork, even if the run later fails
            json.dump({"authorization_id": auth["authorization_id"], "run_id": run_id, "consumed_utc": utc_now(), "bindings": ev["bindings_start"]}, f)
        ev["auth_consumed"] = True
        ev["snapshots"]["S0_before_fork"] = snapshot("S0_before_fork", obs_pid, tokens=True, exclude=exclude)
        reg_path = os.path.join(run_dir, "registry.jsonl")
        obs = O.Observer(reg_path)
        obs.trial_tag = "G0"
        obs.reg.write("RUN_START", run_id=run_id, prereg_sha256=prereg_sha(), observer_pid=obs_pid, phase="G0")
        guard.install()
        rec = obs.spawn_direct("sleeper", "g0", dict(SPEC), node.node_main, t_gate_max=lim["t_gate_max_s"], hold_release=True)
        if rec.state != "REGISTERED":
            raise RuntimeError("child not registered: state %s, problems %r" % (rec.state, obs.problems))
        ev["node"] = {"node_id": rec.node_id, "pid": rec.pid, "starttime": rec.starttime, "gate_ino": rec.gate_ino}
        hold_end = C.mono() + HOLD_S
        while C.mono() < hold_end:
            obs.serve(min(0.05, hold_end - C.mono()))
        s1 = snapshot("S1_held_registered_unreleased", obs_pid, rec.pid, with_fds=True)
        s1["messages_received"] = int(rec.ready is not None) + int(rec.first_action_mono is not None) + len(rec.messages)
        s1["first_action_mono"] = rec.first_action_mono
        ev["snapshots"]["S1_held_registered_unreleased"] = s1
        if s1["messages_received"] or rec.state != "REGISTERED":
            raise RuntimeError("child acted or changed state while held (messages %d, state %s)" % (s1["messages_received"], rec.state))
        guard.watch_fd = rec.gate_w
        obs.release(rec)
        guard.watch_fd = None
        if not obs.wait_for(lambda: rec.ready is not None, lim["ready_deadline_s"]):
            ev["deadline_hits"].append("ready")
            raise RuntimeError("READY not received within %.1f s" % lim["ready_deadline_s"])
        ev["events"]["first_action_mono"] = rec.first_action_mono
        ev["snapshots"]["S2_ready_after_release"] = snapshot("S2_ready_after_release", obs_pid, rec.pid, with_fds=True)
        ev["events"]["exit_sent_mono"] = C.mono()
        proto.send_msg(rec.sock, {"t": "EXIT"})                       # a control-channel message, never a signal
        if not obs.wait_for(lambda: rec.handle.exited(), lim["exit_deadline_s"]):
            ev["deadline_hits"].append("exit")
            raise RuntimeError("child did not exit within %.1f s after EXIT" % lim["exit_deadline_s"])
        ev["events"]["pidfd_readable_mono"] = C.mono()
        ev["snapshots"]["S3_exited_unreaped"] = snapshot("S3_exited_unreaped", obs_pid, rec.pid)
        pid, status = os.waitpid(rec.pid, 0)                            # guard: only this pid; the child is a zombie, so this returns at once
        ev["events"]["reap_mono"] = C.mono()
        rec.exit_status = os.waitstatus_to_exitcode(status)
        ev["reap"] = {"waitpid_pid": pid, "exit_status": rec.exit_status, "raw_status": status}
        gone_by = C.mono() + lim["reap_deadline_s"]
        while C.read_stat(rec.pid) is not None:
            if C.mono() > gone_by:
                ev["deadline_hits"].append("proc_gone")
                raise RuntimeError("/proc/%d still present after reap" % rec.pid)
            time.sleep(0.01)
        ev["events"]["proc_gone_mono"] = C.mono()
        ev["snapshots"]["S4_reaped"] = snapshot("S4_reaped", obs_pid, rec.pid)
        cl = obs.final_cleanup(grace=3.0)       # child is exited AND reaped: kill_registered finds the pidfd readable -> 'already_exited', no signal
        ev["cleanup"] = {"cleanup_ok": cl["cleanup_ok"], "run_set": cl["run_set"], "rounds": cl["rounds"], "residual_detail": cl["residual_detail"]}
        scan, scan_problems = token_scan(exclude)
        confirmed = bool(cl["cleanup_ok"]) and not scan and not scan_problems
        obs.reg.write("RUN_END", run_id=run_id, aborted=None, cleanup_confirmed=confirmed, residual=cl["residual_after_kill"],
                      token_residue=[x["pid"] for x in scan], token_scan_problems=sorted(scan_problems))
    except BaseException:
        ev["exception"] = traceback.format_exc()
        if rec is not None and rec.pid is not None and rec.handle is not None and not rec.handle.exited():
            ident = {"pid": rec.pid, "starttime": rec.starttime, "node_id": rec.node_id, "verified_by": "REGISTERED record + pidfd",
                     "ends_by": "EXIT message / control EOF when this observer exits / gate or node timeout; NO signal was or will be sent by G0"}
            write_json(os.path.join(run_dir, "MANUAL_DISPOSITION_REQUIRED.json"), {"run_id": run_id, "alive": ident, "decision": "a person decides"})
            ev["manual_disposition"] = ident
        elif rec is not None and rec.pid is None and rec.forked_pid is not None:
            try:
                st = C.read_stat(rec.forked_pid)
            except C.ProcUnreadable:
                st = {"state": "UNREADABLE"}
            if st is None or st["state"] in ("Z", "X"):
                pass                                                  # gone or exited-unreaped: nothing alive to dispose of
            else:
                ident = {"pid": rec.forked_pid, "starttime": rec.forked_starttime, "node_id": rec.node_id, "verified_by": "NONE (registration failed; never signalled)",
                         "ends_by": "abort byte already written / gate EOF when this observer exits / gate timeout %.1f s; NO signal was or will be sent by G0" % lim["t_gate_max_s"]}
                write_json(os.path.join(run_dir, "MANUAL_DISPOSITION_REQUIRED.json"), {"run_id": run_id, "alive": ident, "decision": "a person decides"})
                ev["manual_disposition"] = ident
        if obs is not None and not any(r["kind"] == "RUN_END" for r in obs.reg.records):
            try:                                                      # honest end marker: cleanup NOT confirmed (a person decides; no signal)
                obs.reg.write("RUN_END", run_id=run_id, aborted=ev["exception"].strip().splitlines()[-1][:200], cleanup_confirmed=False)
            except Exception:
                ev["exception"] += "\nRUN_END not written: " + traceback.format_exc()
    finally:
        guard.uninstall()
        ev["guard"] = guard.summary()
        ev["bindings_end"] = current()
        try:
            ev["snapshots"]["S5_final"] = snapshot("S5_final", obs_pid, (rec.pid if rec is not None else None), tokens=True, exclude=exclude)
        except Exception:
            ev["exception"] = (ev["exception"] or "") + "\nS5: " + traceback.format_exc()
        ev["timing"] = {"duration": C.mono() - t0}
        try:
            ev["reg"], info = R.parse_reg(os.path.join(run_dir, "registry.jsonl"))
            ev["reg_parse_info"] = info
        except Exception:
            ev["exception"] = (ev["exception"] or "") + "\nREG: " + traceback.format_exc()
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser(description="G0 minimal process-gate test.  --execute needs a valid single-use G0 authorization.")
    ap.add_argument("--check", action="store_true", help="print bindings and authorization status; starts no process")
    ap.add_argument("--template", action="store_true", help="print a NON-VALID authorization template")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--auth", default=GA.AUTH_DEFAULT)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)
    if args.template:
        print(GA.template())
        return 0
    cur = current()
    if args.check or not args.execute:
        info = {"stage": "G0", "bindings": cur, "authorization_file": args.auth, "authorization_present": os.path.exists(args.auth), "executed": False}
        if os.path.exists(args.auth):
            try:
                GA.load(args.auth, cur, utc_now())
                info["authorization_valid"] = True
            except GA.G0AuthorizationError as e:
                info["authorization_valid"] = False
                info["authorization_problem"] = str(e)
        print(json.dumps(info, indent=1))
        return 0
    try:
        auth, raw = GA.load(args.auth, cur, utc_now())
    except GA.G0AuthorizationError as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    run_id = args.run_id or ("g0_" + time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + "_" + os.urandom(3).hex())
    if not GA.ID_RE.match(run_id) or not run_id.startswith("g0_"):
        print("REFUSED: run id %r" % run_id, file=sys.stderr)
        return 2
    run_dir = os.path.join(GA.EVIDENCE_ROOT, run_id)
    if os.path.exists(run_dir):
        print("REFUSED: run directory exists", file=sys.stderr)
        return 2
    try:
        ev = run(auth, raw, run_id, run_dir)
    except BaseException:                       # before the guarded section (e.g. /proc unreadable in the preflight): BLOCKED, never FAIL
        tb = traceback.format_exc()
        print("BLOCKED: the run could not start/finish its preamble:\n" + tb, file=sys.stderr)
        if os.path.isdir(run_dir):
            write_json(os.path.join(run_dir, "g0_summary.json"), {"run_id": run_id, "verdict": "BLOCKED", "exit_code": 3, "exception": tb,
                                                                  "scope": "G0 only; nothing was forked unless the registry says so"})
        return 3
    res = GJ.judge(ev)
    write_json(os.path.join(run_dir, "g0_evidence.json"), ev)
    write_json(os.path.join(run_dir, "g0_summary.json"), {"run_id": run_id, "verdict": res["verdict"], "exit_code": res["exit_code"], "checks": res["checks"],
                                                              "fail_class": res["fail_class"], "blocked_class": res["blocked_class"],
                                                              "scope": "G0 only; not evidence for G1/G2/G3, BV or E1-A", "bindings": ev.get("bindings_start")})
    print(json.dumps({"run_id": run_id, "verdict": res["verdict"]}))
    return res["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
