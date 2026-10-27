#!/usr/bin/env python3
"""G0-V5-IMPLEMENTATION-001 static audit and requirement traceability.  READS SOURCE TEXT, JSON AND FILE HASHES ONLY: it parses the G0 modules with
`ast` and `re`, never imports or executes them, never runs a test and starts no process.
usage: audit_g0_v5_implementation.py [--markdown OUT.md] [--json OUT.json]       Exit 0 = no finding.
It (1) checks syntax / undefined names / unused imports of the implementation and test files, (2) checks that the schema types, rule ids, marker
fields and stderr markers of the FROZEN criteria are all present in the source, (3) audits forbidden calls, (4) verifies the frozen files V1..V5, and
(5) builds the requirement -> implementation -> test traceability table (every locator must be found, otherwise the row is NOT FOUND and the exit
code is 1).  This audit never runs a test; the results of the CPU tests are recorded by tools/run_g0_v5_cpu_tests.py."""
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
TESTS = os.path.join(A003, "tests")
IMPL = ("g0_auth.py", "g0_judge.py", "g0_run.py")
NEW_TESTS = ("test_g0_interlock_and_judge.py", "test_g0_v5_cases.py", "test_g0_v5_closure_cases.py", "test_g0_v5_pipeline.py", "test_g0_v5_run_parts.py", "test_g0_v5_supplement.py")
FILES = {"auth": os.path.join(G0, "g0_auth.py"), "judge": os.path.join(G0, "g0_judge.py"), "run": os.path.join(G0, "g0_run.py")}
for t in NEW_TESTS:
    FILES["t:" + t] = os.path.join(TESTS, t)
FILES["t:fixtures"] = os.path.join(TESTS, "g0_v5_fixtures.py")
SRC = {k: open(p, encoding="utf-8").read() for k, p in FILES.items()}
crit = json.load(open(os.path.join(G0, "g0_criteria_v5.json"), encoding="utf-8"))
findings = []


def need(cond, msg):
    if not cond:
        findings.append(msg)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


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


audit_rows = []
for key, src in SRC.items():
    und, unused = name_audit(key, src)
    audit_rows.append((key, und, unused))
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
validator_keys = {v for k, v in consts.items() if k.startswith("T_") and isinstance(v, str)} | {"string", "bool", "number", "list[int]", "int", "object", "list", "list[string]"}
need(declared_types <= validator_keys, "schema types without a validator constant: %s" % sorted(declared_types - validator_keys))
need(len(crit["evidence_schema"]["fields"]) == 91, "evidence schema field count")
need(tuple(consts.get("MARKER_KEYS", ())) == tuple(f["path"] for f in crit["closure"]["marker_schema"]["fields"]), "MARKER_KEYS differs from the criteria")
need(consts.get("MARKER_SCHEMA") == crit["closure"]["marker_schema"]["id"] and consts.get("MARKER_MAX_BYTES") == crit["closure"]["marker_schema"]["max_bytes"], "marker schema constants")
need(consts.get("EXIT_FOR") == crit["exit_codes"], "exit-code table differs from the criteria")
need(tuple(consts.get("SNAPS", ())) == tuple(crit["snapshots"]), "snapshot names differ from the criteria")
need(tuple(consts.get("DISK_DEPENDENT", ())) == tuple(sorted(crit["witness_dependencies"]["disk_dependent_checks"])) or set(consts.get("DISK_DEPENDENT", ())) == set(crit["witness_dependencies"]["disk_dependent_checks"]),
     "disk-dependent checks differ from witness_dependencies")
need(consts.get("FAIL_SCOPE") == "G0 bench/protocol failure; not evidence about the Mythos model architecture", "FAIL_SCOPE text")
c3, c7 = crit["checks"]["G0-C03"]["rules"], crit["checks"]["G0-C07"]["rules"]
for r in [x["id"] for x in c3["fail_when"] + c3["unevaluable_when"] + c7["fail_when"] + c7["unevaluable_when"]]:
    need(('"%s"' % r) in SRC["judge"], "rule %s is not implemented in g0_judge.py" % r)
for cid in crit["checks"]:
    need(('"%s"' % cid) in SRC["judge"], "check %s missing in g0_judge.py" % cid)
for et in ("LOST", "FOREIGN", "ALTERED", "PARSE", "COUNT"):
    need(('"%s"' % et) in SRC["judge"], "fidelity entry type %s" % et)
facts = crit["closure"]["preflight"]["facts"]
for fname in facts:
    need(('"%s"' % fname) in SRC["run"] or ('"%s"' % fname) in SRC["judge"], "closure fact %s is never produced" % fname)
need("closure_reasons" in SRC["judge"] and 'crit["closure"]["preflight"]["rules"]' in SRC["judge"], "CL rules must be read from the frozen criteria")
markers = ["G0-EVIDENCE-UNSAVED", "G0-EVIDENCE-UNVERIFIED", "G0-JUDGE-ERROR", "G0-SUMMARY-UNSAVED", "G0-CLOSE-UNPUBLISHED", "G0-CLOSE-UNCONFIRMED"]
for m in markers:
    need(m in SRC["run"], "stderr marker %s" % m)
need("e1a-gate-g0-evidence-4" in SRC["run"], "evidence schema id in g0_run")
need(crit["closure"]["publication"]["steps"][4]["id"] == "K4" and "os.link" in SRC["run"] and "follow_symlinks=False" in SRC["run"], "K4 uses os.link")
need(re.search(r"os\.(rename|replace)\(", SRC["run"]) is None, "g0_run must not call os.rename / os.replace")

# ------------------------------------------------------------------ 3. forbidden calls
FORBIDDEN_ATTR = {"kill", "killpg", "pidfd_send_signal", "raise_signal", "pthread_kill", "fork", "forkpty", "system", "popen", "Popen", "execv", "execve", "execvp",
                  "execl", "execlp", "execvpe", "spawnl", "spawnv", "posix_spawn", "_exit", "pidfd_open", "setsid", "setpgid", "wait", "wait3", "wait4", "waitid",
                  "rename", "replace", "unlink", "remove", "truncate", "ftruncate", "renames"}
for key in ("auth", "judge", "run"):
    t = ast.parse(SRC[key])
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in ("os", "signal", "subprocess", "pty"):
            need(n.func.attr not in FORBIDDEN_ATTR, "%s:%d forbidden call %s.%s" % (key, n.lineno, n.func.value.id, n.func.attr))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("dump", "dumps") and any(k.arg == "default" for k in n.keywords):
            need(False, "%s:%d json default= argument" % (key, n.lineno))
    wp = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "waitpid" and isinstance(n.func.value, ast.Name) and n.func.value.id == "os"]
    need(len(wp) == (1 if key == "run" else 0), "%s: os.waitpid call count %d" % (key, len(wp)))
need("authorization" not in "".join(re.findall(r"open\([^)]*AUTH_DEFAULT[^)]*,\s*['\"][wax]", SRC["auth"] + SRC["run"])), "an authorization file must never be written")
for bad in ("import janitor", "import trial", "import scenarios", "import validity", "import e1a_runner", "run_e1a"):
    for key in ("auth", "judge", "run"):
        need(bad not in SRC[key], "%s references %s" % (key, bad))

# ------------------------------------------------------------------ 4. frozen files
FROZEN = {"g0_criteria_v1.json": "4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2", "E1A_GATE_G0_PREREG.md": "9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb",
          "g0_criteria_v2.json": "43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438", "E1A_GATE_G0_PREREG_V2.md": "ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2",
          "g0_criteria_v3.json": "653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a", "E1A_GATE_G0_PREREG_V3.md": "0d52cf5a7a729c0364e9b9f41d3e4b1a50d27b7323f7d5ae2ba21fe2a81d1a88",
          "g0_criteria_v4.json": "6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414", "E1A_GATE_G0_PREREG_V4.md": "05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42",
          "g0_criteria_v5.json": "d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821", "E1A_GATE_G0_PREREG_V5.md": "8338f4a0e20e37ad791d35eb876aca23f3e86e6f16fa9e2d84fd4ac82ef6e25c"}
for f, h in FROZEN.items():
    need(sha(os.path.join(G0, f)) == h, "frozen file %s changed" % f)
need(sha(os.path.join(A003, "prereg", "e1_provability_table_v1.json")) == "e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39", "E1-A preregistration changed")
need("FROZEN_CRITERIA_SHA256 = \"%s\"" % FROZEN["g0_criteria_v5.json"] in SRC["auth"] and "FROZEN_PREREG_SHA256 = \"%s\"" % FROZEN["E1A_GATE_G0_PREREG_V5.md"] in SRC["auth"], "g0_auth frozen constants")
need(not os.path.exists(os.path.join(A003, "AUTHORIZATION_E1A_GATE_G0.json")), "an authorization file exists")
need(not os.path.exists(os.path.join(A003, "evidence")), "an evidence directory exists")
bench = hashlib.sha256("\n".join("%s:%s" % (f, sha(os.path.join(A003, "bench", f))) for f in sorted(os.listdir(os.path.join(A003, "bench"))) if f.endswith(".py")).encode()).hexdigest()

# ------------------------------------------------------------------ 5. test inventory (never run)
inventory = {}
for t in NEW_TESTS:
    tree = ast.parse(SRC["t:" + t])
    cls = [c for c in tree.body if isinstance(c, ast.ClassDef)]
    inventory[t] = {c.name: sum(1 for m in c.body if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")) for c in cls}
n_tests = sum(sum(v.values()) for v in inventory.values())

# ------------------------------------------------------------------ 6. traceability: requirement -> implementation -> test
def line_of(key, pattern):
    for i, line in enumerate(SRC[key].splitlines(), 1):
        if re.search(pattern, line):
            return i
    return None


def loc(key, pattern):
    n = line_of(key, pattern)
    return ("%s:%d" % ({"auth": "gate_g0/g0_auth.py", "judge": "gate_g0/g0_judge.py", "run": "gate_g0/g0_run.py"}.get(key, "tests/" + key[2:]), n)) if n else None


# (requirement id, V5 source, implementation locators [(file, regex)], test locators [(file, regex)])
T_J, T_R, T_A = "judge", "run", "auth"
TS = "t:test_g0_v5_supplement.py"
TI, TC, TL, TP, TR = "t:test_g0_interlock_and_judge.py", "t:test_g0_v5_cases.py", "t:test_g0_v5_closure_cases.py", "t:test_g0_v5_pipeline.py", "t:test_g0_v5_run_parts.py"
ROWS = [
    ("G0-C01 preflight_clean (V5: earlier runs closed by a valid marker; residue independent)", "checks.G0-C01", [(T_J, r"^def c01\("), (T_R, r"^def closure_preflight\("), (T_R, r"^def preflight\(")], [(TI, r"def test_preflight_problems_are_blocked"), (TL, r"def test_c01_text_and_the_unresolved_format")]),
    ("G0-C02 authorization_and_bindings (V5 hash; '(V2)' = historical wording error)", "checks.G0-C02", [(T_J, r"^def c02\("), (T_A, r"^FROZEN_CRITERIA_SHA256"), (T_A, r"is not the frozen V5 criteria hash")], [(TI, r"def test_authorization_bound_to_a_historical"), (TI, r"def test_authorization_bound_to_a_historical_version_is_void")]),
    ("G0-C03 registration_sequence_and_integrity", "checks.G0-C03", [(T_J, r"^def check_c03\(")], [(TC, r"def test_every_case_matches_its_recorded_states")]),
    ("G0-C04 identity_registered_before_release (M-2)", "checks.G0-C04", [(T_J, r"^def c04\(")], [(TI, r"def test_registered_identity_mismatch_is_fail")]),
    ("G0-C05 no_action_before_release (M-2)", "checks.G0-C05", [(T_J, r"^def c05\(")], [(TI, r"def test_child_action_before_release_is_fail")]),
    ("G0-C06 gate_descriptor_hygiene", "checks.G0-C06", [(T_J, r"^def c06\(")], [(TI, r"def test_gate_write_end_in_child_is_fail")]),
    ("G0-C07 release evidence", "checks.G0-C07", [(T_J, r"^def check_c07\(")], [(TC, r"class TestC07Rules")]),
    ("G0-C08 exit_observed_unreaped", "checks.G0-C08", [(T_J, r"^def c08\(")], [(TI, r"def test_wait_before_unreaped_observation_is_not_pass")]),
    ("G0-C09 reap_by_specific_pid (polls return 0)", "checks.G0-C09", [(T_J, r"^def c09\(")], [(TI, r"def test_a_poll_that_returned_neither_zero_nor_the_child_is_not_pass")]),
    ("G0-C10 exit_status_zero", "checks.G0-C10", [(T_J, r"^def c10\(")], [(TI, r"def test_nonzero_exit_status_is_fail")]),
    ("G0-C11 process_budget (M-2)", "checks.G0-C11", [(T_J, r"^def c11\(")], [(TI, r"def test_extra_child_or_descendant_is_fail")]),
    ("G0-C12 zero_signals", "checks.G0-C12", [(T_J, r"^def c12\(")], [(TI, r"def test_guard_violation_is_fail")]),
    ("G0-C13 cleanup_and_no_residue (M-2)", "checks.G0-C13", [(T_J, r"^def c13\(")], [(TI, r"def test_residue_is_blocked")]),
    ("G0-C14 observer_descriptor_baseline", "checks.G0-C14", [(T_J, r"^def c14\(")], [(TI, r"def test_fd_baseline_difference_is_blocked")]),
    ("G0-C15 time_bounds (runtime budget)", "checks.G0-C15", [(T_J, r"^def c15\("), (T_R, r"^class Budget\b")], [(TI, r"def test_deadline_hit_or_overlong_run_is_blocked"), (TR, r"class TestBudget")]),
    ("G0-C16 evidence_complete (schema e1a-gate-g0-evidence-4)", "checks.G0-C16", [(T_J, r"^def c16\("), (T_J, r"^def validate_evidence\("), (T_J, r"^TYPE_VALIDATORS")], [(TI, r"def test_each_schema_field_is_required"), (TI, r"def test_every_declared_schema_type_has_a_validator")]),
    ("G0-C17 no_unexplained_error", "checks.G0-C17", [(T_J, r"^def c17\(")], [(TI, r"def test_exception_alone_is_blocked")]),
    ("C03-F1 (a)-(f) ledger violations", "C03-F1", [(T_J, r"^def rule_f1\(")], [(TC, r"def test_f1_needs_neither")]),
    ("C03-F2 hole in the ledger (needs clean writer, no foreign lines)", "C03-F2", [(T_J, r"^def has_hole\("), (T_J, r"\"C03-F2\"")], [(TC, r"def test_f2_needs_a_clean_writer")]),
    ("C03-F3a fork proven, no valid INTENT", "C03-F3a", [(T_J, r"\"C03-F3a\"")], [(TC, r"def test_f3a_needs_a_clean_writer")]),
    ("C03-F3b release write ok, no valid REGISTERED/RELEASED", "C03-F3b", [(T_J, r"\"C03-F3b\"")], [(TC, r"def test_f3b_needs_a_clean_writer")]),
    ("C03-F3c gate pass proven despite append failure", "C03-F3c", [(T_J, r"\"C03-F3c\"")], [(TC, r"def test_f3c_does_not_need_a_clean_writer"), (TC, r"def test_f3c_needs_a_proven_gate_pass")]),
    ("C03-F4 completed run with incomplete ledger", "C03-F4", [(T_J, r"\"C03-F4\"")], [(TC, r"def test_f4_needs_a_clean_writer")]),
    ("C03-U0/U2/U3/U5/U1/U4 and their order", "C03-U*", [(T_J, r"\"C03-U0\""), (T_J, r"order = \[\"C03-U0\", \"C03-U2\"")], [(TC, r"def test_append_failure_or_seq_gap_alone_is_blocked_never_fail")]),
    ("C03 requirements table (writer_clean only where required)", "rules.requirements", [(T_J, r"no_foreign is True"), (T_J, r"^def writer_clean\(")], [(TC, r"def test_the_table_in_the_criteria_is_the_one_the_tests_assume")]),
    ("C03 definitions: release_attempt / release_write_ok / gate_passed / gate_pass_proven", "rules.definitions", [(T_J, r"^def independent\(")], [(TC, r"def test_definitions_release_attempt_write_ok_and_gate_passed_are_distinct")]),
    ("C03 disk_faithful on whole canonical records; fidelity report LOST/FOREIGN/ALTERED/PARSE/COUNT", "F-20 / M-1", [(T_J, r"^def fidelity\("), (T_J, r"^def canon\(")], [(TC, r"def test_the_report_lists_lost_foreign_altered_parse_and_count"), (TC, r"def test_fid_cases_report_the_concrete_unfaithful_evidence")]),
    ("M-2: C04/C05/C11/C13 UNEVALUABLE when the durable copy is unfaithful", "M-2", [(T_J, r"^DISK_DEPENDENT"), (T_J, r"M-2: the durable copy is not faithful")], [(TI, r"def test_m2_disk_dependent_checks_are_unevaluable"), (TC, r"def test_fid_a_to_e_are_blocked")]),
    ("FID-A..E (and FID-F) cases", "F-20", [(T_J, r"^def fidelity\(")], [(TC, r"def test_fid_a_to_e_are_blocked"), (TC, r"def test_fid_f_the_ledger_proven_violation")]),
    ("C07-F1/F2/F3 and U1..U7", "checks.G0-C07", [(T_J, r"\"C07-F1\""), (T_J, r"\"C07-U7\"")], [(TC, r"def test_u_rules"), (TC, r"def test_f3_the_child_acted_before_the_release")]),
    ("67 V4 rule cases -> V5 judge", "g0_v4_cases.json", [(T_J, r"^def judge\(")], [(TC, r"def test_every_case_matches_its_recorded_states_rules_and_verdict")]),
    ("verdict rule: FAIL > BLOCKED > PASS; exit codes 0/1/3", "verdict_rule", [(T_J, r"verdict = \"FAIL\" if fails"), (T_J, r"^EXIT_FOR")], [(TI, r"def test_verdict_and_exit_code_follow_the_criteria"), (TI, r"def test_fail_takes_precedence_over_bench_blocked")]),
    ("FAIL scope text", "verdict_policy", [(T_J, r"^FAIL_SCOPE"), (T_R, r"summary\[\"fail_scope\"\]")], [(TI, r"def test_fail_summary_scope_text_is_the_frozen_one")]),
    ("P0 construct: ledger + writer seq captured before the registry parse", "evidence_pipeline P0 / LEDGER", [(T_R, r"ev\[\"reg_memory_records\"\] = "), (T_R, r"ev\[\"reg_writer_seq\"\] = ")], [(TR, r"def test_the_ledger_is_captured_before_the_registry_file_is_parsed")]),
    ("P1 strict serialisation (no default=str)", "evidence_pipeline P1", [(T_J, r"^def strict_bytes\("), (T_R, r"b = GJ\.strict_bytes\(ev\)")], [(TP, r"def test_pipe_2_a_non_json_value_is_never_converted"), (TI, r"def test_no_default_str_and_no_overwriting_or_deleting_call")]),
    ("P2 exclusive write + fsync (+ directory fsync); never overwrite", "evidence_pipeline P2", [(T_R, r"^def write_exclusive\("), (T_R, r"^def fsync_dir\(")], [(TP, r"def test_pipe_4_an_existing_evidence_file_is_not_overwritten"), (TP, r"def test_pipe_6_an_fsync_failure")]),
    ("P3 read back, verify bytes + SHA-256, strict parse", "evidence_pipeline P3", [(T_R, r"^def read_back\("), (T_R, r"^def save_and_verify\(")], [(TP, r"def test_pipe_7_bytes_read_back_differ"), (TP, r"def test_pipe_8_not_a_regular_file_or_not_parseable")]),
    ("P4 validate types (once, on the read-back evidence)", "evidence_pipeline P4", [(T_R, r"invalid = GJ\.validate_evidence\(e2, crit\)")], [(TP, r"def test_pipe_9_a_type_error")]),
    ("P5 judge ONLY the read-back evidence", "evidence_pipeline P5", [(T_R, r"res = GJ\.judge\(e2, crit, crit_sha, validation=invalid\)")], [(TP, r"def test_the_judge_receives_only_the_read_back_evidence"), (TP, r"def test_pipe_10_the_judge_raises")]),
    ("P6 save + verify the summary", "evidence_pipeline P6", [(T_R, r"bs2, s2 = save_and_verify")], [(TP, r"def test_pipe_11_a_fail_that_cannot_be_recorded"), (TP, r"def test_pipe_12_a_pass_that_cannot_be_recorded"), (TP, r"def test_pipe_13")]),
    ("P7 publish the marker, return the recorded exit code; uncaught exceptions -> 3", "evidence_pipeline P7", [(T_R, r"^def publish_closure\("), (T_R, r"G0-PIPELINE-ERROR")], [(TP, r"def test_pipe_14_a_fail_saved_and_closed_exits_1"), (TP, r"def test_pipe_15_an_uncaught_exception")]),
    ("stderr markers of the pipeline", "evidence_pipeline", [(T_R, r"G0-EVIDENCE-UNSAVED"), (T_R, r"G0-SUMMARY-UNSAVED"), (T_R, r"G0-JUDGE-ERROR")], [(TR, r"def test_every_marker_of_the_criteria_is_emitted")]),
    ("closure marker g0_closed.json: schema, strict bytes, validation", "closure.marker_schema", [(T_J, r"^MARKER_KEYS"), (T_J, r"^def build_marker\("), (T_J, r"^def classify_marker\(")], [(TL, r"class TestMarkerSchema")]),
    ("K1 build / K2 temp file O_EXCL+fsync / K3 verify", "closure.publication K1-K3", [(T_R, r"GJ\.build_marker\(run_id"), (T_R, r"write_exclusive\(tmp, bc\)")], [(TP, r"def test_publication_is_atomic_exclusive_and_the_temporary_name_is_kept")]),
    ("K4 os.link exclusive publication (EEXIST, no fallback)", "closure.publication K4", [(T_R, r"os\.link\(tmp, final, follow_symlinks=False\)")], [(TP, r"def test_an_existing_final_marker_is_never_replaced"), (TP, r"def test_no_fallback_creates_the_final_name_when_link_is_unsupported")]),
    ("K5 directory fsync / K6 verify published name / K7 exit", "closure.publication K5-K7", [(T_R, r"fsync_dir\(run_dir\)"), (T_R, r"raw = read_back\(final\)")], [(TP, r"def test_the_order_of_the_stages_and_steps"), (TP, r"def test_k7_an_exception_after")]),
    ("G0-CLOSE-UNPUBLISHED / G0-CLOSE-UNCONFIRMED and exit 3", "closure.publication.failures", [(T_R, r"G0-CLOSE-UNCONFIRMED"), (T_R, r"G0-CLOSE-UNPUBLISHED")], [(TP, r"class TestClosurePipelineCases")]),
    ("19 closure pipeline cases", "g0_v5_cases.json pipeline_cases", [(T_R, r"^def finalize\(")], [(TP, r"def test_cases_with_an_injected_fault"), (TP, r"def test_the_cases_cover_the_expected_ids")]),
    ("reporting rule (outcome = recorded verdict only when confirmed)", "closure.publication.reporting_rule", [(T_R, r"return 3\s*$")], [(TP, r"def test_k7b_a_base_exception_right_after_the_link_returned")]),
    ("temporary name never deleted", "closure.publication.no_delete", [(T_R, r"CLOSED_TMP_NAME")], [(TI, r"def test_no_default_str_and_no_overwriting_or_deleting_call"), (TP, r"def test_publication_is_atomic_exclusive_and_the_temporary_name_is_kept")]),
    ("CL-01..CL-23 evaluated from the frozen rules (pure)", "closure.preflight.rules", [(T_J, r"^def closure_reasons\(")], [(TL, r"def test_every_case_gets_its_recorded_reasons_from_the_frozen_rules"), (TL, r"def test_every_rule_is_exercised_by_a_case")]),
    ("closure facts collected read-only from run directories", "closure.preflight.facts", [(T_R, r"^def collect_run_facts\("), (T_R, r"^def read_bound\("), (T_J, r"^def closure_bindings\(")], [(TL, r"def test_the_collected_facts_equal_the_facts_of_the_case_record"), (TL, r"def test_preflight_reads_only")]),
    ("38 closure cases A..K", "g0_v5_cases.json cases", [(T_R, r"^def closure_preflight\(")], [(TL, r"def test_every_closure_case_gives_the_recorded_preflight_result")]),
    ("summary existence never closes a run", "closure.principle", [(T_R, r"cstate, closed = GJ\.classify_marker")], [(TL, r"def test_the_existence_of_the_summary_never_closes_a_run")]),
    ("closure marker is not process-exit proof (live scan + MANUAL independent)", "CL-C / CL-20..22", [(T_R, r"live_marker_process"), (T_R, r"MANUAL = ")], [(TL, r"def test_the_closure_marker_is_not_proof_of_process_exit")]),
    ("any recorded verdict may be closed, a manual disposition still blocks (CL-D)", "CL-D", [(T_J, r"^def closure_reasons\(")], [(TL, r"def test_any_recorded_verdict_closes_a_run_but_not_a_manual_disposition")]),
    ("F-8 bounded reap (non-blocking polls)", "enforcement.reap_wait", [(T_R, r"os\.waitpid\(rec\.pid, os\.WNOHANG\)")], [(TR, r"def test_the_reap_is_a_bounded_non_blocking_poll"), (TI, r"def test_waitpid_is_called_exactly_once_in_run_with_wnohang_and_nowhere_else")]),
    ("F-9 total runtime budget", "enforcement.total_budget", [(T_R, r"^class Budget\b"), (T_R, r"budget\.check\(\"hold\"\)")], [(TR, r"def test_every_loop_and_phase_boundary_checks_the_budget"), (TR, r"def test_left_cap_and_check")]),
    ("F-12 files only into a run directory created by this process", "enforcement.summary_write", [(T_R, r"created_by_this_process"), (T_R, r"os\.mkdir\(run_dir, 0o755\)")], [(TR, r"def test_prepare_dirs_creates_the_run_directory_exclusively")]),
    ("F-13 evidence root / consumption dir created-or-validated, run dir exclusive", "enforcement.directories", [(T_R, r"^def ensure_dir\("), (T_R, r"^def prepare_dirs\(")], [(TR, r"def test_ensure_dir_refuses_a_symlink"), (TR, r"def test_the_directory_infos_validate_against_the_schema")]),
    ("F-18 release writes recorded as entries (before / after / result)", "enforcement.release_evidence", [(T_R, r"def g_write\("), (T_R, r"self\.release_writes\.append\(entry\)")], [(TR, r"class TestReleaseWriteGuard")]),
    ("single-use, V5-bound authorization; no authorization is ever written", "g0_auth", [(T_A, r"^def frozen_problems\("), (T_A, r"^def template\(")], [(TI, r"def test_no_function_of_g0_auth_writes_an_authorization_file"), (TI, r"def test_template_is_never_valid")]),
    ("version isolation (V1..V4 frozen bytes unchanged; V1..V4 bindings void)", "CL-08", [(T_A, r"^FROZEN_FILES")], [(TI, r"def test_frozen_files_V1_to_V5_have_their_frozen_bytes"), (TI, r"def test_authorization_bound_to_a_historical_version_is_void")]),
    ("preflight never raises (BLOCKED, never FAIL)", "checks.G0-C01", [(T_R, r"^def safe_preflight\(")], [(TR, r"def test_safe_preflight_never_raises")]),
    ("any start-up / run exception -> exit code 3, never Python's default 1 (PURE-TEST-001 S-1)", "evidence_pipeline P7 / exit_codes", [(T_R, r"^def main\("), (T_R, r"G0-STARTUP-ERROR")], [(TS, r"def test_every_unexpected_exception_in_the_start_up_path_gives_3_never_1"), (TS, r"def test_no_code_path_of_main_returns_1")]),
    ("format-damaged release / fork evidence is unavailable, never an evidenced FAIL (PURE-TEST-001 S-2)", "checks.G0-C07 / G0-C03 F3", [(T_J, r"^def independent\("), (T_J, r"Format-damaged guard evidence")], [(TS, r"def test_a_malformed_list_never_gives_a_c07_fail_or_a_run_fail"), (TS, r"def test_negative_controls_well_formed_violations_still_fail")]),
]
trace = []
for rid, src, impls, tests in ROWS:
    il = [loc(k, p) for k, p in impls]
    tl = [loc(k, p) for k, p in tests]
    ok = all(il) and all(tl)
    need(ok, "traceability row NOT FOUND: %s impl=%s tests=%s" % (rid, il, tl))
    trace.append({"requirement": rid, "v5_source": src, "implementation": il, "tests": tl, "status": "IMPLEMENTED; tests present (results: g0_v5_pure_test_results)" if ok else "NOT FOUND"})

# every frozen check id and rule id appears in at least one row text or in the source (completeness of the matrix)
rows_text = json.dumps(trace)
for cid in crit["checks"]:
    need(cid in rows_text, "matrix lacks %s" % cid)
for sid in ["P%d" % i for i in range(8)] + ["K%d" % i for i in range(8)]:
    need(sid in rows_text or sid in ("P0", "K0"), "matrix lacks %s" % sid)

# ------------------------------------------------------------------ report
print("files audited:", len(audit_rows), "| syntax + undefined-name + unused-import audit:", "clean" if not any(u or v for _, u, v in audit_rows) else "FINDINGS")
print("schema fields:", len(crit["evidence_schema"]["fields"]), "| schema types:", len(declared_types), "| rules checked in source:", len(c3["fail_when"]) + len(c3["unevaluable_when"]) + len(c7["fail_when"]) + len(c7["unevaluable_when"]), "| closure rules:", len(crit["closure"]["preflight"]["rules"]), "| closure facts:", len(facts))
print("frozen files verified:", len(FROZEN) + 1, "| bench_code_sha256 (unchanged check against the base is done with git):", bench)
print("tests present (executed only by tools/run_g0_v5_cpu_tests.py, never by this audit):", n_tests, {k: sum(v.values()) for k, v in inventory.items()})
print("traceability rows:", len(trace), "| NOT FOUND:", sum(1 for r in trace if r["status"] == "NOT FOUND"))
print("FINDINGS: %d" % len(findings))
for f in findings:
    print("  -", f)
args = sys.argv[1:]
if "--markdown" in args:
    out = args[args.index("--markdown") + 1]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("| V5 requirement | V5 source | implementation | tests | status |\n|---|---|---|---|---|\n")
        for r in trace:
            fh.write("| %s | `%s` | %s | %s | %s |\n" % (r["requirement"], r["v5_source"], "<br>".join("`%s`" % x for x in r["implementation"]), "<br>".join("`%s`" % x for x in r["tests"]), r["status"]))
if "--json" in args:
    out = args[args.index("--json") + 1]
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"trace": trace, "test_inventory": inventory, "bench_code_sha256": bench, "findings": findings}, fh, indent=1)
sys.exit(1 if findings else 0)
