"""Stage C, C2 second fix commit (after the round-1 reviews of the fix commit 49fc9a35): mutation check of run_pilot.py
and metrix_e1.pilot; c2_mutate_fix1.py is kept as it ran for c2b_03; this copy follows the changed code and adds the
mutations of the second fix (the runner is the one of c1b_mutate_fix1.py; every mutation is one replacement). Each
mutation removes or weakens one check in the working tree (exact replacements), runs the tests named for it (no -x:
every named test runs) and restores the file (byte-for-byte, checked). A mutation is "caught" when every named test
fails; the outcome of each named test is printed.
Run from the repository root:
    METRIX_INPUTS_DIR=DIR python metrix/e1-pilot/reports/impl_c/c2_mutate_fix2.py PYTHON
Prints one block per mutation and, at the end, the sha256 of src/, tests/ and run_pilot.py before and after (must be
equal).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PY = sys.argv[1]
PI = Path("metrix/e1-pilot/src/metrix_e1/pilot.py")
RP = Path("metrix/e1-pilot/run_pilot.py")
T = "tests/test_run_pilot.py::"
E2E = T + "test_test_evaluate_end_to_end_once"
CKPT = T + "test_every_checkpoint_reloads_with_the_same_state_hash"
CKPT_BAD = T + "test_a_checkpoint_that_does_not_reload_identically_is_refused"
STOPS = T + "test_smoke_records_the_value_stops_and_formal_raises_them"
CHAIN = T + "test_formal_commit_chain_through_the_freeze_record"
RECORDS = T + "test_test_evaluate_records_after_the_marker_and_for_st10"
CONT = T + "test_continuity_checks_before_anything"
STOPCRASH = T + "test_formal_stop_and_crash_commit_what_was_written[%s]"
GEN = T + "test_test_generate_records_an_st10_stop_of_its_own_run"
LOOK = T + "test_st7_look_ahead_of_a_run"
OVER = T + "test_preflight_overhead_counts"

MUTS = [
    ("checkpoint: reload hash not compared", PI, "        if again != sha:\n", "        if False:\n", CKPT_BAD),
    ("checkpoint: label not checked", PI, 'if ck.get("run") != spec.name or ck.get("label") != self.mode.label:',
     'if ck.get("run") != spec.name:', CKPT_BAD),
    ("checkpoint: an existing file overwritten", PI,
     '        if path.exists():\n            raise ImplementationFail("checkpoint %s exists', '        if False:\n'
     '            raise ImplementationFail("checkpoint %s exists', CKPT),
    ("work directory inside the repository", PI, "        if not outside(self.work, self.root):\n",
     "        if False:\n", T + "test_work_directory_inside_the_repository_is_refused"),
    ("formal records value stops as smoke", PI, "            if self.mode.smoke and e.stop in SMOKE_RECORDED_STOPS:",
     "            if e.stop in SMOKE_RECORDED_STOPS:", STOPS),
    ("smoke records ST1", PI, 'SMOKE_RECORDED_STOPS = ("ST2", "ST3", "ST4", "ST5", "ST11")',
     'SMOKE_RECORDED_STOPS = ("ST1", "ST2", "ST3", "ST4", "ST5", "ST11")', STOPS),
    ("formal: no device check before step 1", PI, "        p.device_info_record = p.device_check()\n        if p.mode.formal:",
     '        p.device_info_record = "skipped"\n        if p.mode.formal:',
     T + "test_formal_on_the_cpu_stops_with_st8_before_anything"),
    ("step 1: manifest change outside the step-1 field", PI,
     "        if FZ.strip_step1_fields(rel, json.loads(blob)) != FZ.strip_step1_fields(rel, json.loads(fz.blobs[rel])):",
     "        if False:", T + "test_step1_writes_only_the_fields_st12_leaves_out"),
    ("step 1: split_sha256 not written", PI,
     '            sm["split_sha256"][name] = file_hashes[name]["canonical_sha256"]',
     '            sm["split_sha256"][name] = sm["split_sha256"][name]',
     T + "test_step1_writes_only_the_fields_st12_leaves_out"),
    ("model directory: revision not compared", PI, "        if got != rev:\n", "        if False:\n",
     T + "test_model_directory_against_the_frozen_revision"),
    ("smoke records without their label", PI, "rec = dict(plain(obj), mode=self.mode.name, label=self.mode.label)",
     "rec = dict(plain(obj), mode=self.mode.name, label=None)",
     T + "test_smoke_outputs_are_labelled_and_stay_in_the_work_directory"),
    ("run records under 'runs' (git-ignored)", PI, 'RUNS_DIR, DETAILS_DIR = "training_runs", "details"',
     'RUNS_DIR, DETAILS_DIR = "runs", "details"', T + "test_no_formal_record_path_is_ignored_by_git " + E2E),
    ("formal takes a step count", RP,
     '        x = a if name == "smoke" else sub.add_parser(name)\n',
     '        x = a if name == "smoke" else sub.add_parser(name)\n        if name != "smoke":\n'
     '            x.add_argument("--steps", type=int)\n',
     T + "test_formal_commands_have_no_step_option"),
    ("TEST: checkpoint files not checked before the marker", PI,
     '            if (got != run_rec["checkpoint"]["file_sha256"]\n'
     '                    or run_rec["checkpoint"]["state_sha256"] != freeze["checkpoints"][name]):',
     "            if False:", E2E),
    ("TEST: general-text rows in the committed result", PI,
     '"summaries": {m: _summary_record(s) for m, s in summaries.items()}})',
     '"summaries": {m: s for m, s in summaries.items()}})', E2E),
    ("formal: a run stopped before step 1 writes into the repository", PI,
     '    if p.mode.formal and command == "formal" and not p.step1_started:', "    if False:",
     T + "test_formal_on_the_cpu_stops_with_st8_before_anything"),
    ("TEST: a refusal before the begin writes a record", PI,
     "        if not begun and code is None:\n", "        if False:\n", E2E + " " + RECORDS),
    ("TEST: a protocol stop before the begin not recorded", PI, "        if not begun and code is None:\n",
     "        if not begun:\n", RECORDS),
    ("TEST: a crash after the begin not recorded", PI,
     "        if not begun_by_this_process(p):\n            raise\n        crash = e\n", "        raise\n", RECORDS),
    ("TEST: begun read from the marker file alone", PI,
     "    return p.begin_called and not p.marker_before_begin and (p.root / TG.MARKER_REL).exists()",
     "    return (p.root / TG.MARKER_REL).exists()", RECORDS + " " + E2E),
    ("TEST: no ST7 look-ahead before the begin", PI, "        p.before_run(look_ahead)", "        p.before_run()", E2E),
    ("TEST: N's hash not compared before the begin", PI, "        if base_sha != n_sha:\n", "        if False:\n", E2E),
    ("TEST look-ahead: checkpoints counted as base loads", PI,
     'n["test_file_hashes"] * pre["reload_s"]', 'n["test_file_hashes"] * pre["load_s"]', OVER),
    ("run look-ahead: A factor for every arm", PI, 'factor = q["a_factor"] if spec.arm == "A" else 1.0',
     'factor = q["a_factor"]', LOOK),
    ("run look-ahead not passed to before_run", PI, "    p.before_run(p.run_seconds(spec))", "    p.before_run()", CHAIN),
    ("test-generate: no ST10 record", PI, "    if over:\n        stop = {", "    if False:\n        stop = {", GEN),
    ("test-generate: an earlier run's ST10 record counted", PI,
     "    over = st10_over_limit(p) if before is None else []", "    over = st10_over_limit(p)", GEN),
    ("a stop inside a step: step record not written first", PI,
     '                self.step_end(k, rec, paths, "metrix: E1-PILOT formal step %d record (stop %s)" % (k, e.stop))',
     "                pass", T + "test_a_stop_inside_a_step_writes_the_step_record_first " + STOPCRASH % "st3"),
    ("stopped run: written records not committed", PI, "        left = [x for x in p.uncommitted if x not in paths]",
     "        left = []", STOPCRASH % "crash"),
    ("continuity: a --work with checkpoints accepted", PI,
     '        if command == "formal" and self.ckpt_dir.is_dir() and any(self.ckpt_dir.glob("*.pt")):',
     "        if False:", CONT),
    ("continuity: no device ledger accepted", PI,
     'if TG._blob(self.root, "HEAD:%s" % STEP1_RECORD_REL) is not None and not self.ledger.path.exists():',
     "if False:", CONT + " " + CHAIN),
    ("continuity: formal runs again after the freeze", PI,
     'if command == "formal" and TG._blob(self.root, "HEAD:%s" % R.SELECTION_FREEZE_REL) is not None:',
     "if False:", CONT + " " + CHAIN),
    ("smoke step 8 started on a checkout with formal records", PI,
     "    if formal:                          # there the generator's", "    if False:                           # there the generator's",
     T + "test_smoke_step8_refuses_where_formal_records_exist"),
    ("excluded run without a checkpoint hash", PI,
     '            return {"spec": spec, "finite": False, "state_sha256": ck["state_sha256"],',
     '            return {"spec": spec, "finite": False,', CHAIN),
    ("unchanged paths committed", PI,
     '        changed = [r for r in rels if TG._blob(self.root, "HEAD:%s" % r) != (self.root / r).read_bytes()]',
     "        changed = rels", CHAIN),
]


def tree_sha():
    h = hashlib.sha256()
    files = (sorted(Path("metrix/e1-pilot/src").rglob("*.py")) + sorted(Path("metrix/e1-pilot/tests").rglob("*.py"))
             + [RP])
    for p in files:
        h.update(str(p).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def parse(m):
    name, path, old, new, tests = m
    return name, path, [(old, new)], ["metrix/e1-pilot/" + t for t in tests.split()]


if __name__ == "__main__":
    before = tree_sha()
    caught = 0
    for m in MUTS:
        name, path, pairs, nodes = parse(m)
        orig = path.read_bytes()
        s = orig.decode("utf-8")
        bad = [s.count(old) for old, _ in pairs if s.count(old) != 1]
        if bad:
            print("%-48s -> MUTATION NOT APPLICABLE (%s matches)" % (name, bad))
            continue
        for old, new in pairs:
            s = s.replace(old, new)
        path.write_text(s, encoding="utf-8")
        try:
            r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rf"] + nodes, capture_output=True,
                               text=True)
            last = r.stdout.strip().split("\n")[-1]
            failed = {ln.split(" ")[1] for ln in r.stdout.split("\n") if ln.startswith("FAILED ")}
            ok = r.returncode == 1 and all(n in failed for n in nodes)
            caught += ok
            print("%-48s -> %s exit %d | %s" % (name, "CAUGHT" if ok else "NOT CAUGHT", r.returncode, last))
            for n in nodes:
                print("       %s %s" % ("FAILED" if n in failed else "passed", n.split("::", 1)[1]))
        finally:
            path.write_bytes(orig)
    after = tree_sha()
    print("mutations %d, caught %d" % (len(MUTS), caught))
    print("src+tests+run_pilot sha256 before %s after %s %s" % (before, after, "EQUAL" if before == after else "DIFFERENT"))
    print("RESULT: %s" % ("PASS" if caught == len(MUTS) and before == after else "FAIL"))
