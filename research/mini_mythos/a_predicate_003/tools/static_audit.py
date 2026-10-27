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
Exit status 0 = no violations.  Usage: static_audit.py [--json]"""
import ast
import json
import os
import sys

BENCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench")

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


def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def audit_file(path):
    name = os.path.basename(path)
    src = open(path).read()
    tree = ast.parse(src, path)
    v, inv = [], {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    v.append((name, n.lineno, "forbidden import %s" % a.name))
        elif isinstance(n, ast.ImportFrom):
            if (n.module or "").split(".")[0] in FORBIDDEN_IMPORTS:
                v.append((name, n.lineno, "forbidden import from %s" % n.module))
            for a in n.names:
                if (n.module, a.name) in FORBIDDEN_FROM:
                    v.append((name, n.lineno, "forbidden from-import %s.%s" % (n.module, a.name)))
        elif isinstance(n, ast.Call):
            d = dotted(n.func)
            if d is None:
                continue
            if d in CALL_RULES:
                inv.setdefault(d, []).append(n.lineno)
                if name not in CALL_RULES[d]:
                    v.append((name, n.lineno, "call %s not allowed in this file" % d))
            if d == "os.waitpid" and n.args:
                a0 = n.args[0]
                if isinstance(a0, ast.UnaryOp) and isinstance(a0.op, ast.USub):
                    v.append((name, n.lineno, "os.waitpid with a negative pid"))
            last = d.split(".")[-1]
            if last in DIAG_ONLY:
                inv.setdefault(last, []).append(n.lineno)
                if name not in DIAG_ONLY[last]:
                    v.append((name, n.lineno, "%s is diagnostic-only (truth.py / definition in common.py)" % last))
        elif isinstance(n, ast.Attribute):
            if dotted(n) in ("os.P_ALL",):
                v.append((name, n.lineno, "os.P_ALL"))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            low = n.value.lower()
            for bad in FORBIDDEN_STRINGS:
                if bad.lower() in low and not (isinstance(n.value, str) and name == "static_audit.py"):
                    v.append((name, n.lineno, "string mentions %r" % bad))
    return v, inv


def main():
    files = sorted(f for f in os.listdir(BENCH) if f.endswith(".py"))
    violations, inventory = [], {}
    for f in files:
        v, inv = audit_file(os.path.join(BENCH, f))
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
