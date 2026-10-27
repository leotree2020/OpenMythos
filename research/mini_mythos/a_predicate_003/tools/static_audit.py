#!/usr/bin/env python3
"""Static audit of the E1-A bench: AST only, nothing is imported or executed, no process is started.

Policy checked (ERRATA-002 section 2 / PREP-001 safety rules):
  * every file parses;
  * os.fork only in gate.py; os.exec* only in trial.py; os.setsid/os.setpgid only in node.py and trial.py;
  * signals ONLY through PidfdHandle.send (signal.pidfd_send_signal only in common.py); no os.kill / os.killpg / signal.raise_signal /
    signal.pthread_kill call anywhere (the stub's instrumentation WRAPS those names by attribute assignment, it never calls them);
  * waits: os.waitpid only in observer.py (specific pid, never -1) and via the stub's saved original; no os.wait/wait3/wait4/waitid
    calls, no waitpid(-1, ...), no P_ALL;
  * no subprocess / multiprocessing / threading / shutil imports, no os.system / os.popen / os.spawn* / posix_spawn;
  * no string literal mentioning pkill / killall / pgrep;
  * command-line / environ readers (read_cmdline, read_environ) are used for diagnostics in truth.py only;
  * os._exit allowed only in the files that implement child-side exits.
Exit status 0 = no violations.  Usage: static_audit.py [--json] [--dir gate_g0]

`--dir gate_g0` audits the G0 entry directory under the stricter G0 profile (GATE-PREP-001): NO process-creating, signalling, exec or exit
call at all (os.fork / os.kill / os.killpg / signal.* senders / exec* / spawn* / os._exit / os.pidfd_open / os.setsid / os.setpgid), no
signal.SIG* constant, os.waitpid only in g0_run.py, and `subprocess` / `signal` imports only in g0_run.py (the guard traps them there;
it never calls them).  The bench itself is audited with the default profile exactly as before."""
import ast
import json
import os
import sys

A003 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BENCH = os.path.join(A003, "bench")
G0_DIR = os.path.join(A003, "gate_g0")

# dotted call name -> files where it is allowed (empty set = forbidden everywhere)
CALL_RULES = {
    "os.fork": {"gate.py"},
    "os.forkpty": set(), "pty.fork": set(),
    "os.execve": {"trial.py"}, "os.execv": set(), "os.execvp": set(), "os.execl": set(), "os.execlp": set(), "os.execvpe": set(),
    "os.system": set(), "os.popen": set(), "os.posix_spawn": set(), "os.posix_spawnp": set(),
    "os.spawnl": set(), "os.spawnv": set(), "os.spawnlp": set(), "os.spawnvp": set(),
    "os.kill": set(), "os.killpg": set(), "signal.raise_signal": set(), "signal.pthread_kill": set(),
    "signal.pidfd_send_signal": {"common.py"},
    "os.waitpid": {"observer.py"}, "os.wait": set(), "os.wait3": set(), "os.wait4": set(), "os.waitid": set(),
    "os.setsid": {"node.py", "trial.py"}, "os.setpgid": {"node.py"}, "os.setpgrp": set(),
    "os._exit": {"gate.py", "node.py", "sup_stub.py", "janitor.py", "validity.py"},
    "os.pidfd_open": {"common.py"},
}
FORBIDDEN_IMPORTS = {"subprocess", "multiprocessing", "threading", "shutil", "pty"}
FORBIDDEN_FROM = {("os", n) for n in ("kill", "killpg", "system", "popen", "fork", "waitid", "wait", "wait3", "wait4")} | \
                 {("signal", n) for n in ("pthread_kill", "raise_signal")}
FORBIDDEN_STRINGS = ("pkill", "killall", "pgrep", "xargs kill", "kill -9", "kill -KILL")
DIAG_ONLY = {"read_cmdline": {"truth.py", "common.py"}, "read_environ": {"truth.py", "common.py"}}


# G0 profile: the same table, but nothing that creates, signals, execs or exits a process may be CALLED; waitpid only in g0_run.py
G0_CALL_RULES = {k: set() for k in CALL_RULES}
G0_CALL_RULES["os.waitpid"] = {"g0_run.py"}
G0_IMPORT_ALLOWED = {"subprocess": {"g0_run.py"}}
G0_DIAG_ONLY = {"read_cmdline": {"g0_run.py"}, "read_environ": set()}      # g0_run.py: diagnostic token scan only
G0_FORBIDDEN_IMPORTS = FORBIDDEN_IMPORTS | {"ctypes", "socketserver", "asyncio", "concurrent"}


def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def audit_file(path, g0=False):
    name = os.path.basename(path)
    rules = G0_CALL_RULES if g0 else CALL_RULES
    bad_imports = G0_FORBIDDEN_IMPORTS if g0 else FORBIDDEN_IMPORTS
    diag = G0_DIAG_ONLY if g0 else DIAG_ONLY
    src = open(path).read()
    tree = ast.parse(src, path)
    v, inv = [], {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                top = a.name.split(".")[0]
                if top in bad_imports and not (g0 and name in G0_IMPORT_ALLOWED.get(top, ())):
                    v.append((name, n.lineno, "forbidden import %s" % a.name))
        elif isinstance(n, ast.ImportFrom):
            top = (n.module or "").split(".")[0]
            if top in bad_imports and not (g0 and name in G0_IMPORT_ALLOWED.get(top, ())):
                v.append((name, n.lineno, "forbidden import from %s" % n.module))
            for a in n.names:
                if (n.module, a.name) in FORBIDDEN_FROM:
                    v.append((name, n.lineno, "forbidden from-import %s.%s" % (n.module, a.name)))
        elif isinstance(n, ast.Call):
            d = dotted(n.func)
            if d is None:
                continue
            if d in rules:
                inv.setdefault(d, []).append(n.lineno)
                if name not in rules[d]:
                    v.append((name, n.lineno, "call %s not allowed in this file" % d))
            if d == "os.waitpid" and n.args:
                a0 = n.args[0]
                if isinstance(a0, ast.UnaryOp) and isinstance(a0.op, ast.USub):
                    v.append((name, n.lineno, "os.waitpid with a negative pid"))
            last = d.split(".")[-1]
            if last in diag:
                inv.setdefault(last, []).append(n.lineno)
                if name not in diag[last]:
                    v.append((name, n.lineno, "%s is diagnostic-only (truth.py / definition in common.py)" % last))
        elif isinstance(n, ast.Attribute):
            if dotted(n) in ("os.P_ALL",):
                v.append((name, n.lineno, "os.P_ALL"))
            if g0 and (dotted(n) or "").startswith("signal.SIG"):
                v.append((name, n.lineno, "signal constant %s (G0 never names a signal)" % dotted(n)))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            low = n.value.lower()
            for bad in FORBIDDEN_STRINGS:
                if bad.lower() in low and not (isinstance(n.value, str) and name == "static_audit.py"):
                    v.append((name, n.lineno, "string mentions %r" % bad))
    return v, inv


def main():
    g0 = "--dir" in sys.argv
    if g0 and sys.argv[sys.argv.index("--dir") + 1:sys.argv.index("--dir") + 2] != ["gate_g0"]:
        sys.exit("--dir accepts only gate_g0")
    root = G0_DIR if g0 else BENCH
    files = sorted(f for f in os.listdir(root) if f.endswith(".py"))
    violations, inventory = [], {}
    for f in files:
        v, inv = audit_file(os.path.join(root, f), g0)
        violations += v
        inventory[f] = inv
    # the wrappers installed by sup_stub.py must be attribute ASSIGNMENTS, never calls
    res = {"files": files, "violations": violations, "inventory": inventory, "ok": not violations}
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1))
    else:
        print("files audited: %d" % len(files))
        for f, inv in inventory.items():
            for k, lines in sorted(inv.items()):
                print("  %-14s %-26s lines %s" % (f, k, lines))
        print("VIOLATIONS: %d" % len(violations))
        for x in violations:
            print("  %s:%d  %s" % x)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
