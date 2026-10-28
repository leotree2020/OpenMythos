#!/usr/bin/env python3
"""STATIC audit of the G1 implementation (F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001, step 5).

Uses ONLY source reading, ast, json, re, hashlib and the text of `git diff --name-status` (passed in with --changed-files; this tool starts no process).
It never imports or executes g1_*.py, g0_*.py, the bench, or any test; the CPU tests are NOT run by this tool.
usage: audit_g1_implementation.py [--changed-files FILE] [--review-changed-files FILE] [--out DIR]       Exit 0 = no finding, 1 = findings (all listed).
Writes (with --out): G1_STATIC_AUDIT.md, G1_TRACEABILITY.md, g1_static_audit.json."""
import ast
import builtins
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A003 = os.path.dirname(HERE)
G0 = os.path.join(A003, "gate_g0")
G1 = os.path.join(A003, "gate_g1")
TESTS = os.path.join(A003, "tests")
IMPL = ("g1_auth.py", "g1_judge.py", "g1_run.py")
TEST_FILES = ("test_g1_judge_cases.py", "test_g1_auth_preflight.py", "test_g1_run_parts.py", "test_g1_boundaries.py", "test_g1_mutations.py", "test_g1_runner_acceptance.py")
FILES = {"auth": os.path.join(G1, "g1_auth.py"), "judge": os.path.join(G1, "g1_judge.py"), "run": os.path.join(G1, "g1_run.py"),
         "t:fixtures": os.path.join(TESTS, "g1_fixtures.py"), "tool:runner": os.path.join(HERE, "run_g1_cpu_tests.py"), "tool:acceptance": os.path.join(HERE, "g1_test_acceptance.py"), "tool:audit": os.path.join(HERE, "audit_g1_implementation.py")}
for t in TEST_FILES:
    FILES["t:" + t] = os.path.join(TESTS, t)
SRC = {k: open(p, encoding="utf-8").read() for k, p in FILES.items()}
crit = json.load(open(os.path.join(G1, "g1_criteria_v1.json"), encoding="utf-8"))
findings = []
notes = []


def need(cond, msg):
    if not cond:
        findings.append(msg)


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def blob(p):
    with open(p, "rb") as f:
        d = f.read()
    return hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()


# ------------------------------------------------------------------ 1. syntax, names, imports
def name_audit(label, src):
    tree = ast.parse(src)
    compile(src, label, "exec")                       # syntax and symbol-table check only; nothing is executed
    defined = set(dir(builtins)) | {"__file__"}
    imported = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            defined.add(n.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                defined.add((a.asname or a.name).split(".")[0])
                imported[(a.asname or a.name).split(".")[0]] = n.lineno
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                defined.add(a.asname or a.name)
                imported[a.asname or a.name] = n.lineno
        elif isinstance(n, ast.arg):
            defined.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            defined.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            defined.add(n.name)
    undefined = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in defined})
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return undefined, sorted(k for k in imported if k not in used and k != "hashlib")


name_rows = []
for key, src in SRC.items():
    und, unused = name_audit(key, src)
    name_rows.append((key, und, unused))
    need(not und, "%s: undefined names %s" % (key, und))
    need(not unused, "%s: unused imports %s" % (key, unused))

# ------------------------------------------------------------------ 2. the frozen criteria are fully present in the source
tree_judge = ast.parse(SRC["judge"])
consts = {}
for n in ast.walk(tree_judge):
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
        try:
            consts[n.targets[0].id] = ast.literal_eval(n.value)
        except (ValueError, SyntaxError):
            pass
declared_types = {f["type"] for f in crit["evidence_schema"]["fields"]}
g0_consts = {}
for n in ast.walk(ast.parse(open(os.path.join(G0, "g0_judge.py"), encoding="utf-8").read())):
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
        try:
            g0_consts[n.targets[0].id] = ast.literal_eval(n.value)
        except (ValueError, SyntaxError):
            pass
validator_keys = {v for k, v in consts.items() if k.startswith("T_") and isinstance(v, str)} | {v for k, v in g0_consts.items() if k.startswith("T_") and isinstance(v, str)}
validator_keys |= {"string", "bool", "number", "list[int]", "int", "object", "list", "list[string]"}
need(declared_types <= validator_keys, "schema types without a validator constant: %s" % sorted(declared_types - validator_keys))
need(len(crit["evidence_schema"]["fields"]) == 88, "evidence schema field count")
need(tuple(consts.get("MARKER_KEYS", ())) == tuple(f["path"] for f in crit["closure"]["marker_schema"]["fields"]), "MARKER_KEYS differs from the criteria")
need(consts.get("MARKER_SCHEMA") == crit["closure"]["marker_schema"]["id"] and consts.get("MARKER_MAX_BYTES") == crit["closure"]["marker_schema"]["max_bytes"], "marker schema constants")
need(consts.get("EXIT_FOR") == crit["exit_codes"], "exit-code table differs from the criteria")
need(tuple(consts.get("SNAPS_TEST", ())) == tuple(crit["snapshots"]["per_test"]), "snapshot names differ from the criteria")
need(set(consts.get("DISK_DEPENDENT", ())) == set(crit["witness_dependencies"]["disk_dependent_checks"]), "disk-dependent checks differ from witness_dependencies")
need(consts.get("FAIL_SCOPE") == "G1 bench/protocol failure; not evidence about the Mythos model architecture", "FAIL_SCOPE text")
need(consts.get("NODE_ORDER") == ("INTENT", "FORKED", "REGISTERED", "ABORTED", "DEAD"), "NODE_ORDER")
need(consts.get("R_BYTE") == crit["scenarios"]["common"]["r_byte"] == 82, "the release byte value")
for cid, c in crit["checks"].items():
    need(('"%s"' % cid) in SRC["judge"], "check %s missing in g1_judge.py" % cid)
    for group in ("fail_when", "unevaluable_when"):
        for r in c.get("rules", {}).get(group, []):
            need(('"%s"' % r["id"]) in SRC["judge"], "rule %s is not implemented in g1_judge.py" % r["id"])
for cid in ("C04-F1", "C04-U1", "C04-U2", "C05-F1", "C05-U1", "C06-F1", "C06-U1", "C07-F1", "C07-F2", "C07-F3", "C07-U1", "C07-U2", "C07-U3", "C10-F1", "C10-F2",
            "C10-F3", "C10-U1", "C10-U2", "C03-F1", "C03-F2", "C03-F3", "C03-U0", "C03-U1", "C03-U2", "C03-U3", "C03-U4"):
    need(('"%s"' % cid) in SRC["judge"], "rule id %s not present in g1_judge.py" % cid)
need(crit["scenarios"]["order"] == ["T1_ABORT", "T2_EOF", "T3_INVALID_BYTE", "T4_TIMEOUT"], "scenario order")
need([crit["scenarios"]["tests"][t]["expected_exit"] for t in crit["scenarios"]["order"]] == [111, 111, 111, 112], "expected exit codes")
need([crit["scenarios"]["tests"][t]["stimulus"]["planned_gate_bytes"] for t in crit["scenarios"]["order"]] == [[65], [], [114], []], "planned gate bytes")
need([crit["scenarios"]["tests"][t]["t_gate_max_s"] for t in crit["scenarios"]["order"]] == [5.0, 5.0, 5.0, 2.0], "t_gate_max per scenario")
need(crit["limits"]["max_forks"] == 4 and crit["limits"]["max_forks_per_test"] == 1 and crit["limits"]["max_signals"] == 0 and crit["limits"]["max_seconds"] == 30.0, "limits")
for kind in ("abort_held", "close_only", "write_byte"):
    need(('kind == "%s"' % kind) in SRC["run"], "stimulus kind %s not executed by g1_run.py" % kind)
need('kind == "none"' in SRC["run"], "the silent-gate (none) kind is not handled in g1_run.py")
for k in ("limits", "scenarios", "identity_margin_s", "t4_exit_margin_s", "exit_deadline_s", "per_test_seconds", "max_seconds", "hold_before_stimulus_s", "reap_deadline_s"):
    need(k in SRC["judge"] or k in SRC["run"], "criteria item %s is never used" % k)
need("closure_reasons" in SRC["judge"] and 'crit["closure"]["preflight"]["rules"]' in open(os.path.join(G0, "g0_judge.py"), encoding="utf-8").read() and "GJ.closure_reasons" in SRC["run"],
     "CL1 rules must be read from the frozen criteria through the G0 engine")
facts = crit["closure"]["preflight"]["facts"]
G0J = open(os.path.join(G0, "g0_judge.py"), encoding="utf-8").read()
for fname in facts:      # the binding facts are produced by the reused G0 engine function closure_bindings(); the others by collect_run_facts() in g1_run.py
    need(('"%s"' % fname) in SRC["run"] or ('"%s"' % fname) in SRC["judge"] or ('"%s"' % fname) in G0J, "closure fact %s is never produced" % fname)
for m in ("G1-EVIDENCE-UNSAVED", "G1-EVIDENCE-UNVERIFIED", "G1-JUDGE-ERROR", "G1-SUMMARY-UNSAVED", "G1-CLOSE-UNPUBLISHED", "G1-CLOSE-UNCONFIRMED", "G1-STARTUP-ERROR",
          "G1-RUN-ERROR", "G1-PIPELINE-ERROR", "G1-DIR-ERROR", "G1-TEST-STOP"):
    need(m in SRC["run"], "stderr marker %s" % m)
need("e1a-gate-g1-evidence-1" in SRC["run"] and crit["evidence_schema"]["id"] == "e1a-gate-g1-evidence-1", "evidence schema id in g1_run")
need(crit["closure"]["publication"]["steps"][4]["id"] == "K4" and "os.link(tmp, final, follow_symlinks=False)" in SRC["run"], "K4 uses os.link")
need(re.search(r"os\.(rename|replace)\(", SRC["run"]) is None, "g1_run must not call os.rename / os.replace")
need(crit["authorization"]["schema"] == "e1a-gate-auth-g1-1" and 'AUTH_SCHEMA = "e1a-gate-auth-g1-1"' in SRC["auth"], "authorization schema")
need(tuple(crit["authorization"]["bindings"]) == tuple(re.findall(r'"(\w+)"', re.search(r"BINDING_KEYS = \((.*?)\)\n", SRC["auth"], re.S).group(1))), "binding keys differ from the criteria")
need(crit["authorization"]["g0_reference"]["closed_sha256"] in SRC["auth"] and "FROZEN_G1_CRITERIA_SHA256" in SRC["auth"], "authorization constants")
need("_g1_consumed" in SRC["auth"] and 'with open(G1A.consumed_marker(auth["authorization_id"]), "x")' in SRC["run"], "single-use consumption marker (exclusive create) before the first fork")
need(SRC["run"].index('with open(G1A.consumed_marker(auth["authorization_id"]), "x")') < SRC["run"].index("guard.install()"), "the consumption marker must be written before the guard / the first fork")
need(SRC["run"].index("guard.install()") < SRC["run"].index("for tid in order:"), "the guard must be installed before any test")
need("hold_release=True" in SRC["run"], "the gate must be created held (hold_release=True)")

# ------------------------------------------------------------------ 3. forbidden calls / unprotected process operations
FORBIDDEN_ATTR = {"kill", "killpg", "pidfd_send_signal", "raise_signal", "pthread_kill", "fork", "forkpty", "system", "popen", "Popen", "run", "call", "check_call", "check_output",
                  "execv", "execve", "execvp", "execl", "execlp", "execvpe", "execle", "execlpe", "spawnl", "spawnv", "spawnle", "spawnlp", "spawnlpe", "spawnve", "spawnvp",
                  "spawnvpe", "posix_spawn", "posix_spawnp", "_exit", "pidfd_open", "setsid", "setpgid", "wait", "wait3", "wait4", "waitid", "rename", "replace", "unlink",
                  "remove", "truncate", "ftruncate", "renames"}
for key in ("auth", "judge", "run"):
    t = ast.parse(SRC[key])
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in ("os", "signal", "subprocess", "pty"):
            need(n.func.attr not in FORBIDDEN_ATTR, "%s:%d forbidden call %s.%s" % (key, n.lineno, n.func.value.id, n.func.attr))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("dump", "dumps") and any(k.arg == "default" for k in n.keywords):
            need(False, "%s:%d json default= argument" % (key, n.lineno))
    wp = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "waitpid" and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
    need(len(wp) == (1 if key == "run" else 0), "%s: os.waitpid call count %d" % (key, len(wp)))
# the only processes created by G1 are created by gate.fork_gated through the guard; g1_run itself never forks
fork_refs = [n for n in ast.walk(ast.parse(SRC["run"])) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "os" and n.attr == "fork"]
need(len(fork_refs) == 2, "g1_run references os.fork %d times (only the guard install may: one load, one store)" % len(fork_refs))
need(not [n for n in ast.walk(ast.parse(SRC["run"])) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "fork" and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"],
     "g1_run calls os.fork directly")
for key in ("auth", "judge", "run"):
    t = ast.parse(SRC[key])
    imported = set()
    called = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            imported |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module)
        elif isinstance(n, ast.Call):
            called.add(n.func.attr if isinstance(n.func, ast.Attribute) else (n.func.id if isinstance(n.func, ast.Name) else None))
    for bad in ("janitor", "trial", "scenarios", "validity", "e1a_runner"):
        need(bad not in imported, "%s imports %s" % (key, bad))
    for bad in ("_confirmed_dead", "finish_trial_cleanup", "kill_registered", "kill_unregistered_direct", "release"):
        need(bad not in called, "%s calls %s" % (key, bad))
    need("run_e1a" not in re.sub(r'"""[\s\S]*?"""', "", SRC[key]), "%s references run_e1a" % key)
need("authorization" not in "".join(re.findall(r"open\([^)]*AUTH_DEFAULT[^)]*,\s*['\"][wax]", SRC["auth"] + SRC["run"])), "an authorization file must never be written")
need(not re.search(r"os\.kill|pidfd_send_signal\(|subprocess\.(run|Popen|call|check_)", re.sub(r'"[^"\n]*"', '""', SRC["judge"] + SRC["auth"])), "signal / subprocess use in judge or auth")
trap_names = set(re.findall(r'"(kill|killpg|forkpty|waitid|wait3|wait4|wait|system|popen|execv|execve|posix_spawn|pidfd_send_signal|raise_signal|pthread_kill|Popen)"', SRC["run"]))
need({"kill", "killpg", "forkpty", "waitid", "wait3", "wait4", "wait", "system", "popen", "execv", "execve", "posix_spawn", "pidfd_send_signal", "raise_signal", "pthread_kill", "Popen"} <= trap_names,
     "guard trap list incomplete: %s" % sorted(trap_names))
# order of operations inside run_test: stimulus < wait for exit < S3 < waitpid < proc gone < S4 < cleanup < S5
fn = next(n for n in ast.walk(ast.parse(SRC["run"])) if isinstance(n, ast.FunctionDef) and n.name == "run_test")
body_src = ast.get_source_segment(SRC["run"], fn)
order_marks = ['events["stimulus_mono"] = C.mono()', 'budget.wait(obs, exited', 'events["pidfd_readable_mono"] = C.mono()', 'snaps["S3_exited_unreaped"]', "os.waitpid(rec.pid, os.WNOHANG)",
               'events["proc_gone_mono"] = C.mono()', 'snaps["S4_reaped"]', "obs.finish_cleanup(nodes=[rec]", 'snaps["S5_after_cleanup"]']
pos = [body_src.index(m) if m in body_src else -1 for m in order_marks]
need(all(p >= 0 for p in pos) and pos == sorted(pos), "run_test order of operations: %s" % pos)
need(body_src.count("finish_cleanup(") == 1 and body_src.index("finish_cleanup(") > body_src.index("os.waitpid("), "cleanup before the reap")

# ------------------------------------------------------------------ 4. frozen files, bench, base diff
FROZEN_G0 = {"g0_criteria_v1.json": "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2", "E1A_GATE_G0_PREREG.md": "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb",
             "g0_criteria_v2.json": "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438", "E1A_GATE_G0_PREREG_V2.md": "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2",
             "g0_criteria_v3.json": "653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a", "E1A_GATE_G0_PREREG_V3.md": "0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88",
             "g0_criteria_v4.json": "6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414", "E1A_GATE_G0_PREREG_V4.md": "05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42",
             "g0_criteria_v5.json": "d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821", "E1A_GATE_G0_PREREG_V5.md": "8338f4a0e20e37ad791d35eb876aca23f3e86e6f16fa9e2d84fd4ac82ef6e25c"}
for f, h in FROZEN_G0.items():
    need(sha(os.path.join(G0, f)) == h, "frozen G0 file %s changed" % f)
FROZEN_G1 = {"g1_criteria_v1.json": "1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257", "E1A_GATE_G1_PREREG.md": "3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69"}
for f, h in FROZEN_G1.items():
    need(sha(os.path.join(G1, f)) == h, "frozen G1 file %s changed" % f)
    need(open(os.path.join(G1, f + ".sha256")).read().split()[0] == h, "%s.sha256 file differs" % f)
need("FROZEN_G1_CRITERIA_SHA256 = \"%s\"" % FROZEN_G1["g1_criteria_v1.json"] in SRC["auth"] and "FROZEN_G1_PREREG_SHA256 = \"%s\"" % FROZEN_G1["E1A_GATE_G1_PREREG.md"] in SRC["auth"],
     "g1_auth frozen constants")
need(sha(os.path.join(A003, "prereg", "e1_provability_table_v1.json")) == "e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39", "E1-A preregistration changed")
bench = hashlib.sha256("\n".join("%s:%s" % (f, sha(os.path.join(A003, "bench", f))) for f in sorted(os.listdir(os.path.join(A003, "bench"))) if f.endswith(".py")).encode()).hexdigest()
need(bench == "b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0", "bench code hash changed: %s" % bench)
need(not os.path.exists(os.path.join(A003, "AUTHORIZATION_E1A_GATE_G1.json")), "a G1 authorization file exists")
ev_root = os.path.join(A003, "evidence")
need(not [n for n in (os.listdir(ev_root) if os.path.isdir(ev_root) else []) if n.startswith("g1_") or n == "_g1_consumed"], "a G1 evidence directory or consumption marker exists")
g0_ref = crit["authorization"]["g0_reference"]
d0 = os.path.join(ev_root, g0_ref["run_id"])
need(sha(os.path.join(d0, "g0_closed.json")) == g0_ref["closed_sha256"] and sha(os.path.join(d0, "g0_evidence.json")) == g0_ref["evidence_sha256"]
     and sha(os.path.join(d0, "g0_summary.json")) == g0_ref["summary_sha256"], "the G0 REAL-001 evidence changed")
ALLOWED_PREFIXES = ("research/mini_mythos/a_predicate_003/gate_g1/", "research/mini_mythos/a_predicate_003/tests/g1_fixtures.py", "research/mini_mythos/a_predicate_003/tests/test_g1_",
                    "research/mini_mythos/a_predicate_003/tools/run_g1_cpu_tests.py", "research/mini_mythos/a_predicate_003/tools/audit_g1_implementation.py",
                    "research/mini_mythos/a_predicate_003/tools/g1_test_acceptance.py",
                    "research/mini_mythos/a_predicate_003/g1_impl_static_audit/", "research/mini_mythos/docs/")
changed = None
if "--changed-files" in sys.argv:
    changed = [ln.split("\t") for ln in open(sys.argv[sys.argv.index("--changed-files") + 1], encoding="utf-8").read().splitlines() if ln.strip()]
    for status, *paths in changed:
        for p in paths:
            need(p.startswith(ALLOWED_PREFIXES), "changed file outside the G1 scope: %s %s" % (status, p))
        need(status.startswith(("A", "M")), "unexpected change status %s %s (deleted / renamed files)" % (status, paths))
    protected = [p for status, *paths in changed for p in paths if any(x in p for x in ("/bench/", "/gate_g0/", "/prereg/", "r3_cpu_probes", "/evidence/", "parcae", "Parcae", "/model", "open_mythos"))]
    need(not protected, "protected files changed: %s" % protected)
    for status, *paths in changed:
        for p in paths:
            if p.endswith(("g1_criteria_v1.json", "E1A_GATE_G1_PREREG.md", "g1_criteria_v1.json.sha256", "E1A_GATE_G1_PREREG.md.sha256")):
                need(status == "A", "a frozen G1 file is reported as %s (only its freezing commit may add it)" % status)

REVIEW_ALLOWED = ("research/mini_mythos/a_predicate_003/gate_g1/g1_run.py", "research/mini_mythos/a_predicate_003/gate_g1/g1_judge.py", "research/mini_mythos/a_predicate_003/tests/",
                  "research/mini_mythos/a_predicate_003/tools/", "research/mini_mythos/a_predicate_003/g1_impl_static_audit/", "research/mini_mythos/docs/")
review_changed = None
if "--review-changed-files" in sys.argv:        # git diff --name-status <reviewed commit 453fe4e> HEAD: only the two implementation files, tests, tools, audit outputs and docs may change
    review_changed = [ln.split("\t") for ln in open(sys.argv[sys.argv.index("--review-changed-files") + 1], encoding="utf-8").read().splitlines() if ln.strip()]
    for status, *paths in review_changed:
        for p in paths:
            need(p.startswith(REVIEW_ALLOWED), "review-fix change outside the allowed files: %s %s" % (status, p))
            need(not p.endswith(("g1_criteria_v1.json", "E1A_GATE_G1_PREREG.md", ".sha256", "g1_auth.py", "E1A_GATE_G1_DESIGN.md")), "a frozen / untouched G1 file changed in the review fix: %s" % p)
        need(status.startswith(("A", "M")), "unexpected review-fix status %s %s" % (status, paths))

# ------------------------------------------------------------------ 4b. review fixes: residue on the exception path, in-run judgement, runner acceptance
run_tree = ast.parse(SRC["run"])
run_fn = next(n for n in ast.walk(run_tree) if isinstance(n, ast.FunctionDef) and n.name == "run")
handlers = [h for t in ast.walk(run_fn) if isinstance(t, ast.Try) for h in t.handlers if isinstance(h.type, ast.Name) and h.type.id == "BaseException"]
need(len(handlers) == 1, "run() must have exactly one BaseException handler")
if handlers:
    hdump = ast.dump(ast.Module(body=handlers[0].body, type_ignores=[]))
    need("attr='rec'" not in hdump, "the exception path of run() must not use S.rec (stale node of an earlier test)")
    need("report_residue" in hdump and "live_pid" in hdump and "nodes" in hdump, "the exception path of run() must report every node and the guard's unreaped child")
rt_src = ast.get_source_segment(SRC["run"], next(n for n in ast.walk(run_tree) if isinstance(n, ast.FunctionDef) and n.name == "run_test"))
need(rt_src.index("S.rec = None") < rt_src.index("obs.spawn_direct("), "run_test must forget the previous node before it spawns")
need("GJ.judge_test_in_run(_in_run_view(S), S.crit, tid)" in rt_src and 'ev["deadline_hits"], judged)' in rt_src, "run_test must stop on the in-run judgement")
need('ev["stopped_after"] = tid' in rt_src, "run_test must mark the stop on an exception")
need("def judge_test_in_run(" in SRC["judge"] and "IN_RUN_CHECKS = (" in SRC["judge"], "g1_judge: in-run judgement")
acc_src = SRC["tool:acceptance"]
need(re.search(r"EXPECTED_TOTAL_TESTS = (\d+)", acc_src), "acceptance: expected total constant")
runner_src = SRC["tool:runner"]
for must in ("ACC.assess(full_selection, all_rows,", "full_selection = sel is None", 'report["verdict"] = acc["verdict"]', 'return acc["exit_code"]', "def addSkip(", "def addExpectedFailure(", "def addUnexpectedSuccess("):
    need(must in runner_src, "runner acceptance: %r missing" % must)
need("all_ok" not in runner_src and 'report["verdict"] = "PASS"' not in runner_src, "runner: a PASS must only come from the acceptance function")
ids = []
for t in TEST_FILES:
    for c in ast.parse(SRC["t:" + t]).body:
        if isinstance(c, ast.ClassDef):
            ids += ["%s.%s.%s" % (t[:-3], c.name, m.name) for m in c.body if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")]
need(len(ids) == len(set(ids)), "duplicate test ids (a later definition would silently replace an earlier test)")
total_const = int(re.search(r"EXPECTED_TOTAL_TESTS = (\d+)", acc_src).group(1))
need(total_const == len(ids), "EXPECTED_TOTAL_TESTS %d != the %d tests found by ast" % (total_const, len(ids)))
groups_node = next(n for n in ast.parse(runner_src).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GROUPS" for t in n.targets))
grouped = {c.value for c in ast.walk(groups_node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value.startswith("test_g1_")}
need(grouped == {t[:-3] for t in TEST_FILES}, "runner GROUPS differ from the test files: %s" % sorted(grouped ^ {t[:-3] for t in TEST_FILES}))
need(len([f for f in os.listdir(TESTS) if re.match(r"test_g1_.*\.py$", f)]) == len(TEST_FILES), "a test_g1_*.py file is not audited")

# ------------------------------------------------------------------ 5. test inventory (never run by this tool)
inventory = {}
for t in TEST_FILES:
    tree = ast.parse(SRC["t:" + t])
    cls = [c for c in tree.body if isinstance(c, ast.ClassDef)]
    names = [(c.name, m.name) for c in cls for m in c.body if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")]
    inventory[t] = len(names)
    need(names, "%s has no tests" % t)
    need("unittest.main" in SRC["t:" + t], "%s has no unittest main" % t)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in ("os", "signal", "subprocess"):
            need(n.func.attr not in FORBIDDEN_ATTR - {"remove", "replace", "unlink", "rename"}, "%s:%d test calls %s.%s" % (t, n.lineno, n.func.value.id, n.func.attr))
all_tests = sum(inventory.values())

# ------------------------------------------------------------------ 6. traceability: frozen criteria -> implementation -> tests
T_J, T_R, T_A = "judge", "run", "auth"
TJ, TA, TR, TB, TM = ("t:test_g1_judge_cases.py", "t:test_g1_auth_preflight.py", "t:test_g1_run_parts.py", "t:test_g1_boundaries.py", "t:test_g1_mutations.py")
FILEREL = {"auth": "gate_g1/g1_auth.py", "judge": "gate_g1/g1_judge.py", "run": "gate_g1/g1_run.py"}


def line_of(key, pattern):
    for i, line in enumerate(SRC[key].splitlines(), 1):
        if re.search(pattern, line):
            return i
    return None


def loc(key, pattern):
    n = line_of(key, pattern)
    if not n:
        return None
    rel = FILEREL.get(key) or ("tests/" + key[2:] if key.startswith("t:") else key)
    return "%s:%d" % (rel, n)


ROWS = [
    ("G1-C01 preflight_clean (incl. G0 REAL-001 reference verified)", "checks.G1-C01", [(T_J, r"^def c01\("), (T_R, r"^def preflight\("), (T_R, r"^def safe_preflight\("), (T_A, r"^def g0_reference_status\(")],
     [(TJ, r"def test_the_run_level_preflight_failure_blocks_every_test"), (TR, r"def test_every_blocking_condition_makes_the_preflight_not_ok"), (TA, r"def test_a_matching_closed_pass_run_is_ok")]),
    ("G1-C02 authorization_and_bindings (10 bindings, frozen hashes, consumed)", "checks.G1-C02", [(T_J, r"^def c02\("), (T_A, r"^def validate\("), (T_A, r"^FROZEN_G1_CRITERIA_SHA256")],
     [(TJ, r"def test_binding_differences_block_c02"), (TA, r"def test_every_binding_must_equal_its_current_value")]),
    ("G1-C03 registration sequence per scenario + disk fidelity (F1..F3, U0..U4)", "checks.G1-C03", [(T_J, r"^def check_c03\("), (T_J, r"^def rule_f1\("), (T_J, r"^def expected_kinds\(")],
     [(TJ, r"def test_wrong_kinds_with_a_clean_writer_and_faithful_disk_are_c03_f2"), (TJ, r"def test_a_seq_gap_or_append_failure_alone_is_blocked_never_fail"),
      (TJ, r"def test_an_altered_durable_copy_blocks_and_disables_the_disk_dependent_checks"), (TJ, r"def test_a_released_record_fails_c03_c05_and_c07")]),
    ("G1-C04 identity registered before the stimulus (PID/starttime in 7 places; margin before the gate timer)", "checks.G1-C04", [(T_J, r"^def c04\("), (T_R, r"snaps\[\"S1b_pre_stimulus\"\] = _held_snapshot")],
     [(TJ, r"def test_registered_pid_differs_from_the_held_child"), (TJ, r"def test_starttime_differences_are_c04_f1"), (TJ, r"def test_t4_identity_taken_too_late_for_the_gate_timer_is_unevaluable_never_pass")]),
    ("G1-C05 no action without release", "checks.G1-C05", [(T_J, r"^def c05\("), (T_R, r"^def msgs\(")],
     [(TJ, r"def test_a_message_before_release_in_a_held_snapshot_is_c05_f1"), (TJ, r"def test_first_action_ready_or_messages_at_exit_are_c05_f1"), (TJ, r"def test_a_child_in_another_state_is_unevaluable_not_fail")]),
    ("G1-C06 gate descriptor hygiene", "checks.G1-C06", [(T_J, r"^def c06\(")], [(TJ, r"def test_the_gate_write_end_in_the_child_is_c06_f1")]),
    ("G1-C07 stimulus exactness (bytes, closes, no R, no release)", "checks.G1-C07", [(T_J, r"^def c07\("), (T_R, r"^class G1Guard"), (T_R, r"    def write\(self, fd, data\)"), (T_R, r"    def close\(self, fd\)")],
     [(TJ, r"def test_an_r_write_attempt_in_the_guard_is_c07_f1_and_fails_the_run"), (TJ, r"def test_an_unplanned_extra_byte_is_c07_f2"), (TJ, r"def test_t4_gate_closed_before_the_exit_was_observed_is_c07_f3"),
      (TR, r"def test_an_r_write_is_trapped_and_never_reaches_the_pipe")]),
    ("G1-C08 exit observed unreaped (state Z, no earlier wait)", "checks.G1-C08", [(T_J, r"^def c08\("), (T_R, r"snaps\[\"S3_exited_unreaped\"\]")],
     [(TJ, r"def test_the_zombie_state_is_required_not_assumed"), (TJ, r"def test_a_wait_before_the_unreaped_observation_blocks_c08"), (TM, r"the zombie state is not required")]),
    ("G1-C09 reap by specific pid, /proc gone", "checks.G1-C09", [(T_J, r"^def c09\("), (T_R, r"os\.waitpid\(rec\.pid, os\.WNOHANG\)")],
     [(TJ, r"def test_a_wait_call_naming_another_pid_blocks_c09"), (TJ, r"def test_no_wait_call_that_returned_the_pid_blocks_c09"), (TR, r"def test_waitpid_only_on_the_current_child")]),
    ("G1-C10 gate-path exit status (111/111/111/112; 0 = FAIL; 113 / signal = unevaluable; T4 fork reference)", "checks.G1-C10", [(T_J, r"^def c10\("), (T_R, r"wait_s = max\(0\.0, fe\[\"mono_before\"\]")],
     [(TJ, r"def test_swapped_gate_codes_are_c10_f2_fail"), (TJ, r"def test_exit_status_zero_is_c10_f1_fail"), (TJ, r"def test_exit_113_or_a_signal_status_is_unevaluable_never_fail"),
      (TJ, r"def test_a_112_earlier_than_the_gate_timer_can_fire_is_c10_f3_with_the_fork_as_reference")]),
    ("G1-C11 process budget (one fork per test, 4 in total, no descendants, no tickets)", "checks.G1-C11", [(T_J, r"^def c11\("), (T_R, r"    def fork\(self\)")],
     [(TJ, r"def test_more_forks_than_executed_tests_is_c11_fail"), (TJ, r"def test_a_ticket_intent_is_c03_f3_and_c11_fail"), (TR, r"def test_at_most_four_forks_in_total"), (TR, r"def test_no_new_fork_while_the_previous_child_is_unreaped")]),
    ("G1-C12 zero signals", "checks.G1-C12", [(T_J, r"^def c12\("), (T_R, r"    def _trap\(self, name\)"), (T_R, r"O\.Observer\.release = self\._trap")],
     [(TJ, r"def test_a_guard_violation_is_c12_fail"), (TJ, r"def test_a_cleanup_kill_entry_that_is_not_already_exited_is_c12_fail"), (TR, r"def test_traps_record_and_raise")]),
    ("G1-C13 cleanup and no residue (after the reap)", "checks.G1-C13", [(T_J, r"^def c13\("), (T_R, r"obs\.finish_cleanup\(nodes=\[rec\]"), (T_R, r"obs\.final_cleanup\(")],
     [(TJ, r"def test_residue_or_unconfirmed_cleanup_blocks_c13"), (TB, r"def test_cleanup_runs_only_after_the_reap_in_run_test")]),
    ("G1-C14 observer descriptor baseline", "checks.G1-C14", [(T_J, r"^def c14\(")], [(TJ, r"def test_a_changed_descriptor_count_blocks_c14")]),
    ("G1-C15 time bounds (T4 reference = fork time)", "checks.G1-C15", [(T_J, r"^def c15\("), (T_R, r"ev\[\"deadline_hits\"\]\.append\(\"test:\" \+ tid\)")],
     [(TJ, r"def test_t4_exit_observed_later_than_5s_after_the_fork_blocks"), (TJ, r"def test_a_deadline_hit_prevents_pass")]),
    ("G1-C16 evidence complete and typed", "checks.G1-C16", [(T_J, r"^def c16\("), (T_J, r"^def validate_evidence\("), (T_J, r"^TYPE_VALIDATORS")],
     [(TJ, r"def test_wrong_typed_fields_make_c16_fail_and_the_run_blocked"), (TJ, r"def test_every_schema_type_has_a_validator"), (TJ, r"def test_the_good_evidence_is_well_typed")]),
    ("G1-C17 no unexplained error / manual disposition / prefix of the order", "checks.G1-C17", [(T_J, r"^def c17\("), (T_R, r"^def _manual\(")],
     [(TJ, r"def test_manual_disposition_blocks"), (TJ, r"def test_tests_that_ran_must_be_a_prefix_of_the_order"), (TR, r"def test_manual_disposition_is_written_exclusively_and_recorded_in_the_evidence")]),
    ("T1 ABORT scenario (SPEC probe, abort_held, byte A, exit 111)", "scenarios.T1_ABORT", [(T_R, r'kind == "abort_held"'), (T_R, r"obs\.abort_held\(rec\)")],
     [(TJ, r"def test_scenario_table_is_the_reviewed_design"), (TJ, r"def test_complete_run_passes_in_all_four_tests")]),
    ("T2 EOF scenario (close only, exit 111)", "scenarios.T2_EOF", [(T_R, r'kind == "close_only"')], [(TJ, r"def test_a_missing_planned_close_is_unevaluable_not_fail")]),
    ("T3 INVALID_BYTE scenario (one byte r, exit 111)", "scenarios.T3_INVALID_BYTE", [(T_R, r'kind == "write_byte"')], [(TJ, r"def test_the_wrong_byte_instead_of_the_planned_one_is_c07_f2")]),
    ("T4 TIMEOUT scenario (silent gate, t_gate_max 2.0 s, fork-time reference, exit 112)", "scenarios.T4_TIMEOUT", [(T_R, r'kind == "none"'), (T_J, r"earliest = fe\[\"mono_before\"\]")],
     [(TJ, r"def test_t4_exit_observed_later_than_5s_after_the_fork_blocks"), (TJ, r"def test_t4_identity_taken_too_late_for_the_gate_timer_is_unevaluable_never_pass")]),
    ("sequential execution T1 -> T4, first non-PASS stops the run (in-run safety rule = the judge's own checks on the evidence so far)", "enforcement.stop_rule",
     [(T_R, r"^def in_run_assessment\("), (T_R, r"if not run_test\(S, tid\):"), (T_R, r"^def _in_run_view\("), (T_J, r"^def judge_test_in_run\("), (T_J, r"^IN_RUN_CHECKS")],
     [(TR, r"class TestInRunAssessment"), (TR, r"def test_minimal_counterexample_a_pid_mismatch_with_the_expected_exit_code_used_to_continue_the_run"), (TJ, r"class TestInRunJudgement"),
      (TM, r"def test_an_in_run_rule_that_ignores_the_exit_status"), (TM, r"def test_a_stop_rule_without_the_identity_check_lets_a_pid_mismatch_through")]),
    ("exception path: every node of this run and the guard's unreaped child are checked; manual disposition, no signal (no stale S.rec)", "enforcement.no_signals / residue_policy",
     [(T_R, r"^def alive_nodes\("), (T_R, r"^def report_residue\("), (T_R, r"report_residue\(run_dir, run_id, ev, list\(obs\.nodes\.values\(\)\)")],
     [(TR, r"class TestAliveNodesOnTheExceptionPath"), (TR, r"def test_the_previous_dead_node_never_hides_the_current_one_the_stale_s_rec_case"), (TR, r"def test_a_node_whose_spawn_did_not_return_is_found_through_the_guards_unreaped_pid"),
      (TR, r"def test_the_exception_handler_of_run_uses_every_node_not_s_rec"), (TM, r"class TestReviewFixMutations")]),
    ("CPU runner: PASS only for a FULL run with every expected test id executed once and PASS (0 SKIP / FAIL / ERROR / load error / sentinel hit)", "(CPU test obligation)",
     [("tool:acceptance", r"^def assess\("), ("tool:acceptance", r"^def discover_expected_ids\("), ("tool:runner", r"ACC\.assess\(full_selection")],
     [("t:test_g1_runner_acceptance.py", r"class TestIncompleteIsNeverPass"), ("t:test_g1_runner_acceptance.py", r"def test_a_skip_is_not_a_pass"), ("t:test_g1_runner_acceptance.py", r"class TestAcceptanceMutations")]),
    ("PASS / FAIL / BLOCKED / NOT_RUN strictly apart; RUN-INCOMPLETE", "verdict_policy", [(T_J, r"^def judge\("), (T_J, r"incomplete = bool\(not_run\)"), (T_R, r"^def blank_test\(")],
     [(TJ, r"def test_a_run_that_stopped_early_but_passed_so_far_is_blocked_not_pass"), (TJ, r"def test_not_run_after_a_failed_test_is_legitimate_and_the_verdict_is_fail"), (TM, r"def test_a_mutant_that_calls_an_incomplete_run_pass")]),
    ("damaged evidence is UNEVALUABLE, never a wrong FAIL", "verdict_policy.4", [(T_J, r"^def _run_check\("), (T_J, r"^def _consumed_invalid\(")],
     [(TJ, r"def test_format_damaged_guard_records_are_unevaluable_never_fail"), (TJ, r"def test_times_of_the_wrong_type_are_unevaluable_not_fail"), (TJ, r"def test_an_exception_alone_never_gives_fail")]),
    ("process-safety guard (one fork per test, specific-pid waitpid, gate write/close record, R trap)", "enforcement.guard", [(T_R, r"^class G1Guard"), (T_R, r"    def install\(self\)"), (T_R, r"    def uninstall\(self\)")],
     [(TR, r"class TestGuardLogic"), (TM, r"def test_a_guard_that_allows_a_second_fork"), (TM, r"def test_a_guard_that_lets_the_release_byte_through")]),
    ("single-use authorization, closed schema, void G0 / E1-A authorizations", "authorization", [(T_A, r"^def load\("), (T_A, r"^def consumed_marker\("), (T_A, r"^REQUIRED_GRANTS")],
     [(TA, r"def test_g0_and_e1a_authorizations_are_void_for_g1"), (TA, r"def test_a_consumed_authorization_is_refused_single_use"), (TA, r"def test_grants_must_be_exactly_the_frozen_ones")]),
    ("consumption marker written exclusively before the first fork", "authorization.rules", [(T_R, r'G1A\.consumed_marker\(auth\["authorization_id"\]\)'), (T_R, r"guard\.install\(\)")],
     [(TB, r"def test_refusals_are_2"), (TA, r"def test_the_consumed_marker_path_is_inside_the_g1_consumption_directory")]),
    ("history: earlier g0_ runs judged with the G0 V5 engine, earlier g1_ runs with CL1-01..23", "closure.preflight", [(T_R, r"^def collect_run_facts\("), (T_R, r"^def closure_preflight\("), (T_R, r"GR\.closure_preflight\(G1A\.EVIDENCE_ROOT")],
     [(TA, r"def test_a_directory_without_a_marker_is_unresolved"), (TA, r"def test_damaged_markers_and_bound_files_are_unresolved"), (TA, r"def test_the_g0_history_is_judged_by_the_g0_engine_and_blocks_g1")]),
    ("evidence pipeline P0..P7", "evidence_pipeline", [(T_R, r"^def finalize\(")],
     [(TR, r"def test_a_passing_run_is_saved_judged_and_closed"), (TR, r"def test_the_verdict_is_computed_from_the_read_back_evidence"), (TR, r"def test_unserialisable_evidence_is_blocked_before_anything_is_written")]),
    ("closure publication K0..K7 (tmp + os.link, never overwritten)", "closure.publication", [(T_R, r"^def publish_closure\("), (T_J, r"^def build_marker\("), (T_J, r"^def classify_marker\(")],
     [(TR, r"def test_a_failed_link_publishes_nothing"), (TR, r"def test_an_existing_marker_is_never_replaced"), (TR, r"def test_a_published_marker_that_does_not_read_back_is_unconfirmed"), (TJ, r"def test_classification_of_damaged_markers")]),
    ("exit codes; SystemExit / exception -> 3; argparse 0 / 2 kept; refusal 2", "exit_code_policy", [(T_R, r"^def main\("), (T_R, r"^def _main\("), (T_R, r"^def _parser\(")],
     [(TB, r"def test_an_unexpected_system_exit_in_any_step_gives_3_never_1_or_0"), (TB, r"def test_system_exit_one_is_the_named_negative_control"), (TB, r"def test_argparse_usage_error_keeps_exit_code_2_and_help_keeps_0")]),
    ("manual disposition, no signal, no cleanup by name", "enforcement.no_signals", [(T_R, r"^def _manual\("), (T_R, r"MANUAL = ")], [(TR, r"def test_manual_disposition_is_written_exclusively_and_recorded_in_the_evidence"),
                                                                                                                            (TB, r"def test_no_process_signal_wait_or_overwrite_call_in_any_g1_module")]),
    ("reap evidence before cleanup; _confirmed_dead() not used", "enforcement.no_cleanup_by_zombie_state", [(T_R, r'events\["reap_mono"\] = C\.mono\(\)'), (T_R, r"obs\.finish_cleanup\(nodes=\[rec\]")],
     [(TB, r"def test_cleanup_runs_only_after_the_reap_in_run_test"), (TB, r"def test_the_zombie_as_dead_logic_and_the_sigkill_cleanup_are_not_used")]),
    ("the gate is never released; the bench abort path is used", "scenarios.common", [(T_R, r"hold_release=True"), (T_R, r"^class G1Guard")], [(TB, r"def test_the_gate_is_never_released_and_the_bench_abort_is_used")]),
    ("G0 helpers reused read-only; no g0_ file modified", "relation_to_g0", [(T_R, r"import g0_run as GR"), (T_J, r"import g0_judge as GJ"), (T_A, r"import g0_auth as GA")],
     [(TB, r"def test_the_runner_imports_g0_helpers_read_only_and_modifies_no_g0_file")]),
    ("mutation negative controls", "(CPU test obligation)", [(T_J, r"^def judge\(")], [(TM, r"class TestJudgeMutations"), (TM, r"class TestRunnerMutations")]),
]
trace = []
for text, ref, impls, tests in ROWS:
    il = [loc(k, p) for k, p in impls]
    tl = [loc(k, p) for k, p in tests]
    miss = [p for (k, p), l in zip(impls, il) if not l] + [p for (k, p), l in zip(tests, tl) if not l]
    need(not miss, "traceability row %r: NOT FOUND %s" % (text, miss))
    trace.append((text, ref, [x for x in il if x], [x for x in tl if x], miss))
for cid in crit["checks"]:
    need(any(r[1] == "checks." + cid for r in trace), "check %s has no traceability row" % cid)

# ------------------------------------------------------------------ 7. report
files_hashes = {}
for rel in ("gate_g1/g1_auth.py", "gate_g1/g1_judge.py", "gate_g1/g1_run.py", "gate_g1/g1_criteria_v1.json", "gate_g1/E1A_GATE_G1_PREREG.md", "tests/g1_fixtures.py",
            "tests/test_g1_judge_cases.py", "tests/test_g1_auth_preflight.py", "tests/test_g1_run_parts.py", "tests/test_g1_boundaries.py", "tests/test_g1_mutations.py",
            "tests/test_g1_runner_acceptance.py", "tools/run_g1_cpu_tests.py", "tools/g1_test_acceptance.py", "tools/audit_g1_implementation.py"):
    files_hashes[rel] = {"sha256": sha(os.path.join(A003, rel)), "git_blob_sha1": blob(os.path.join(A003, rel)), "lines": len(open(os.path.join(A003, rel), encoding="utf-8").read().splitlines())}

print("files audited:", len(SRC), "| syntax + undefined-name + unused-import audit:", "clean" if not any(u or v for _, u, v in name_rows) else "FINDINGS")
print("schema fields: %d | schema types: %d | checks: %d | rule ids checked in source: %d | closure rules: %d | closure facts: %d" % (
    len(crit["evidence_schema"]["fields"]), len(declared_types), len(crit["checks"]), sum(len(c.get("rules", {}).get(g, [])) for c in crit["checks"].values() for g in ("fail_when", "unevaluable_when")),
    len(crit["closure"]["preflight"]["rules"]), len(facts)))
print("frozen G0 files verified: %d | frozen G1 files verified: %d | bench_code_sha256: %s" % (len(FROZEN_G0), len(FROZEN_G1), bench))
print("changed-file scope check:", "not requested" if changed is None else "%d entries checked" % len(changed))
print("tests present (NOT executed, NOT TESTED): %d %s" % (all_tests, inventory))
print("traceability rows: %d | NOT FOUND: %d" % (len(trace), sum(1 for r in trace if r[4])))
print("FINDINGS: %d" % len(findings))
for f in findings:
    print("  -", f)

if "--out" in sys.argv:
    out = sys.argv[sys.argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "G1_TRACEABILITY.md"), "w", encoding="utf-8") as f:
        f.write("# G1 traceability: frozen criteria -> implementation -> CPU tests (tests are NOT TESTED: written, never run)\n\n| requirement | frozen source | implementation | tests (written, not run) |\n|---|---|---|---|\n")
        for text, ref, il, tl, miss in trace:
            f.write("| %s | %s | %s | %s |\n" % (text, ref, "<br>".join(il) or "-", "<br>".join(tl) or "-"))
    with open(os.path.join(out, "g1_static_audit.json"), "w", encoding="utf-8") as f:
        json.dump({"findings": findings, "files": files_hashes, "tests": inventory, "test_total": all_tests, "bench_code_sha256": bench, "frozen_g1": FROZEN_G1,
                   "traceability_rows": len(trace), "traceability_not_found": sum(1 for r in trace if r[4]), "name_audit": [{"file": k, "undefined": u, "unused_imports": v} for k, u, v in name_rows]},
                  f, indent=1, sort_keys=True)
sys.exit(0 if not findings else 1)
