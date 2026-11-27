"""Stage C, C2 second fix commit: the one mutation of c2_mutate_fix2.py that c2c_03 reported NOT CAUGHT because its
test list also named test_test_evaluate_end_to_end_once, which does not reach the case (the records test did fail:
c2c_03_checks.txt); here it names the records test only. c2_mutate_fix2.py is kept as it ran. Same runner. Each
mutation removes or weakens one check in the working tree (exact replacements), runs the tests named for it (no -x:
every named test runs) and restores the file (byte-for-byte, checked). A mutation is "caught" when every named test
fails; the outcome of each named test is printed.
Run from the repository root:
    METRIX_INPUTS_DIR=DIR python metrix/e1-pilot/reports/impl_c/c2_mutate_fix2b.py PYTHON
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
    ("TEST: begun read from the marker file alone", PI,
     "    return p.begin_called and not p.marker_before_begin and (p.root / TG.MARKER_REL).exists()",
     "    return (p.root / TG.MARKER_REL).exists()", RECORDS),
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
