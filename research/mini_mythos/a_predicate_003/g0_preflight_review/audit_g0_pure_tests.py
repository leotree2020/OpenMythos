#!/usr/bin/env python3
"""PREFLIGHT-001 static audit of tests/test_g0_interlock_and_judge.py.  AST ONLY: nothing is imported from the audited code and
nothing is executed; no process is started by the analysis itself.

Answers: can any test execution path reach a real fork / signal / wait / exec / spawn / pidfd / setsid / fault injection?
  A. every Call in the test file whose dotted name or attribute is process-capable;
  B. which g0_run functions the tests call, and the syntactic call-closure of that set with and without the edge main -> run
     (run() is the only function that forks);
  C. process-capable calls inside the closure functions;
  D. module-level (import-time) calls of every module the tests import;
  E. the expected number of tests.
Usage: audit_g0_pure_tests.py [--json]   Exit 0 = no process-capable path in the test code and in the closure that excludes run()."""
import ast
import json
import os
import sys

A003 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TEST = os.path.join(A003, "tests", "test_g0_interlock_and_judge.py")
MODS = {"g0_run": "gate_g0/g0_run.py", "g0_auth": "gate_g0/g0_auth.py", "g0_judge": "gate_g0/g0_judge.py", "common": "bench/common.py",
        "registry": "bench/registry.py"}
PROC_ATTRS = {"fork", "forkpty", "kill", "killpg", "waitpid", "wait", "wait3", "wait4", "waitid", "system", "popen", "Popen", "call", "check_call",
              "check_output", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe", "spawnl", "spawnle", "spawnlp",
              "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp", "pidfd_open", "pidfd_send_signal",
              "raise_signal", "pthread_kill", "setsid", "setpgid", "setpgrp", "_exit", "alarm", "setitimer"}
# bench / g0 functions that create or signal processes (reaching one of these = reaching a process)
PROC_FUNCS = {"run", "spawn_direct", "fork_gated", "release", "final_cleanup", "finish_cleanup", "kill_registered", "kill_unregistered_direct",
              "reap_direct", "install", "node_main", "request_spawn", "PidfdHandle", "Observer"}


def dotted(n):
    parts = []
    while isinstance(n, ast.Attribute):
        parts.append(n.attr)
        n = n.value
    if isinstance(n, ast.Name):
        parts.append(n.id)
        return ".".join(reversed(parts))
    return None


def parse(rel):
    p = os.path.join(A003, rel)
    return ast.parse(open(p).read(), p)


def calls_in(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            d = dotted(n.func)
            attr = n.func.attr if isinstance(n.func, ast.Attribute) else (n.func.id if isinstance(n.func, ast.Name) else None)
            yield n.lineno, d, attr


def main():
    out = {"test_file": os.path.relpath(TEST, A003), "findings": [], "ok": True}
    ttree = ast.parse(open(TEST).read(), TEST)

    # A. process-capable calls anywhere in the test file
    a = []
    for ln, d, attr in calls_in(ttree):
        if attr in PROC_ATTRS or attr in PROC_FUNCS:
            a.append({"line": ln, "call": d or attr})
    out["A_process_capable_calls_in_test_file"] = a
    # the ones that are mock.patch targets are strings, not calls; the spy replaces run() -> record the patch lines
    out["A_patched_run_spies"] = [ln for ln, d, attr in calls_in(ttree) if d == "mock.patch.object"]

    # E. tests
    tests = {}
    for c in [n for n in ttree.body if isinstance(n, ast.ClassDef)]:
        tests[c.name] = sorted(f.name for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"))
    out["E_tests"] = {k: len(v) for k, v in tests.items()}
    out["E_tests_total"] = sum(len(v) for v in tests.values())

    # per-test call inventory limited to g0/bench-module and filesystem-ish names
    per = {}
    for c in [n for n in ttree.body if isinstance(n, ast.ClassDef)]:
        for f in c.body:
            if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"):
                names = sorted({d for _, d, _ in calls_in(f) if d and d.split(".")[0] in ("g0_run", "GA", "GJ", "R", "C", "tempfile", "mock", "os")})
                per[c.name + "." + f.name] = names
    out["per_test_calls"] = per

    # B/C. g0_run closure
    rt = parse(MODS["g0_run"])
    funcs, methods = {}, {}
    for n in rt.body:
        if isinstance(n, ast.FunctionDef):
            funcs[n.name] = n
        elif isinstance(n, ast.ClassDef):
            for f in n.body:
                if isinstance(f, ast.FunctionDef):
                    methods[n.name + "." + f.name] = f
    called_by_tests = sorted({attr for ln, d, attr in calls_in(ttree) if d and d.startswith("g0_run.")})
    out["B_g0_run_functions_called_by_tests"] = called_by_tests

    def closure(start, cut=()):
        seen, todo = set(), list(start)
        while todo:
            f = todo.pop()
            if f in seen or f not in funcs:
                continue
            seen.add(f)
            for ln, d, attr in calls_in(funcs[f]):
                nm = attr if (d is None or "." not in d) else None
                if d and "." not in d and d in funcs and d not in cut:
                    todo.append(d)
        return seen
    full = closure(called_by_tests)
    cut = closure(called_by_tests, cut={"run"})
    # closure() follows only plain-name calls inside the module; cut = same without the main->run edge
    cut.discard("run")
    out["B_closure_with_run_edge"] = sorted(full)
    out["B_closure_without_run_edge"] = sorted(cut)
    out["B_run_syntactically_reachable_from_main"] = "run" in full
    bad, edge = [], []
    for f in sorted(cut):
        for ln, d, attr in calls_in(funcs[f]):
            if f == "main" and d == "run":                         # the main -> run edge is analysed on its own (guard lines below)
                edge.append(ln)
            elif attr in PROC_ATTRS or attr in PROC_FUNCS:
                bad.append({"function": f, "line": ln, "call": d or attr})
    out["B_main_to_run_edge_lines"] = edge
    out["C_process_capable_calls_in_closure_without_run"] = bad
    run_hits = [{"line": ln, "call": d or attr} for ln, d, attr in calls_in(funcs["run"]) if attr in PROC_ATTRS or attr in PROC_FUNCS]
    out["C_process_capable_calls_inside_run_only"] = run_hits

    # the guard that keeps run() unreachable from main()
    mt = funcs["main"]
    src = open(os.path.join(A003, MODS["g0_run"])).read().splitlines()
    out["B_guard_before_run_in_main"] = [(i, src[i - 1].strip()) for i in range(mt.lineno, mt.end_lineno + 1)
                                         if "GA.load" in src[i - 1] or "return 2" in src[i - 1] or "= run(" in src[i - 1]]
    gl = [i for i, t in out["B_guard_before_run_in_main"] if "auth, raw = GA.load" in t]
    ret = [i for i, t in out["B_guard_before_run_in_main"] if t == "return 2"]
    out["B_every_run_edge_is_after_an_authorization_load_and_refusal_return"] = bool(edge and gl and ret and min(edge) > max(gl) and any(gl[0] < r < min(edge) for r in ret))

    # D. import-time (module-level, outside def/class) calls of every imported module
    d_hits = {}
    for mod, rel in MODS.items():
        tree = parse(rel)
        hits = []
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                continue
            for ln, d, attr in calls_in(n):
                hits.append({"line": ln, "call": d or attr, "proc_capable": bool(attr in PROC_ATTRS or attr in PROC_FUNCS)})
        d_hits[mod] = hits
    out["D_import_time_calls"] = d_hits
    out["D_import_time_process_capable"] = [(m, h) for m, hs in d_hits.items() for h in hs if h["proc_capable"]]

    spies = out["A_patched_run_spies"]
    out["A_tests_that_call_main_and_spy_on_run"] = len(spies)
    ok = (not a and not bad and not out["D_import_time_process_capable"] and "run" in full and out["B_every_run_edge_is_after_an_authorization_load_and_refusal_return"]
          and len(spies) == 2 and called_by_tests == ["main"])
    out["ok"] = bool(ok)
    out["verdict_text"] = ("no process-capable call in the test file, none in the main()-closure that excludes run(), none at import time; run() is "
                           "syntactically reachable from main() only behind GA.load(...)/return 2 and is replaced by a failing spy in both tests that call main()")
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        print("tests: %d  %s" % (out["E_tests_total"], out["E_tests"]))
        print("A. process-capable calls in the test file: %d" % len(a), a)
        print("B. g0_run functions called by tests:", called_by_tests)
        print("   closure incl. run edge   :", out["B_closure_with_run_edge"])
        print("   closure excl. run edge   :", out["B_closure_without_run_edge"])
        print("   run() reachable from main (syntactic):", out["B_run_syntactically_reachable_from_main"])
        print("   main -> run edge line(s) :", edge, " guard lines:", out["B_guard_before_run_in_main"])
        print("   run edge only after authorization load + refusal return:", out["B_every_run_edge_is_after_an_authorization_load_and_refusal_return"])
        print("   tests that call main() and replace run() by a failing spy:", len(spies), "(lines %s)" % spies)
        print("C. process-capable calls in the closure excluding run(): %d" % len(bad), bad)
        print("   process-capable calls inside run() only (for reference):", run_hits)
        print("D. import-time process-capable calls: %d" % len(out["D_import_time_process_capable"]), out["D_import_time_process_capable"])
        print("RESULT:", "OK" if ok else "FINDINGS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
