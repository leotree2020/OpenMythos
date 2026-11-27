"""Stage C, C4 (Review Gate ruling of 2026-11-27, tasks/IMPL_C4_RULING.md item 1: ST11 reads B17's estimate plus the
checkpoint overhead; B17 revised; the ST7 look-ahead unchanged; no margin on the TEST look-ahead): mutation check of
that change (the runner is the one of c2_mutate_fix3.py; every mutation is one exact replacement). Each mutation
removes or weakens one part of the change in the working tree, runs the tests named for it (no -x: every named test
runs) and restores the file (byte-for-byte, checked). A mutation is "caught" when every named test fails; the outcome
of each named test is printed.
Run from the repository root:
    METRIX_INPUTS_DIR=DIR python metrix/e1-pilot/reports/impl_c/c4_mutate.py PYTHON
Prints one block per mutation and, at the end, the sha256 of src/, tests/ and run_pilot.py before and after (must be
equal).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PY = sys.argv[1]
PI = Path("metrix/e1-pilot/src/metrix_e1/pilot.py")
ST = Path("metrix/e1-pilot/src/metrix_e1/stops.py")
IN = Path("metrix/e1-pilot/src/metrix_e1/interpretations.py")
RP = Path("metrix/e1-pilot/run_pilot.py")
T = "tests/test_run_pilot.py::"
FST11 = T + "test_formal_st11_reads_b17_plus_the_checkpoint_overhead[%s]"
OVER = T + "test_preflight_overhead_counts"
LOOK = T + "test_st7_look_ahead_of_a_run"
ST11 = "tests/test_stops.py::test_st11"
RULED = "tests/test_test_data.py::test_interpretations_ruled_by_review_gate"

MUTS = [
    ("step 2: ST11 reads B17's estimate only", PI,
     '[], STP.st11, p.fz, p.contract, pre["st11_estimate_hours"])',
     '[], STP.st11, p.fz, p.contract, pre["b17_estimate_hours"])', FST11 % "sum_over_bound"),
    ("ST11 estimate: overhead not added", PI, "    return b17_hours + overhead_seconds / 3600.0\n",
     "    return b17_hours\n", OVER + " " + FST11 % "sum_over_bound"),
    ("ST11 estimate: overhead seconds taken as minutes", PI,
     "    return b17_hours + overhead_seconds / 3600.0\n", "    return b17_hours + overhead_seconds / 60.0\n",
     OVER + " " + FST11 % "sum_at_bound"),
    ("preflight: ST11 estimate is B17's alone", PI, "    st11_hours = st11_estimate_hours(hours, overhead)\n",
     "    st11_hours = hours\n", FST11 % "sum_over_bound"),
    ("ST11 stops at the bound itself", ST,
     "if not math.isfinite(estimate_hours) or estimate_hours > contract.stops.st11_hours:",
     "if not math.isfinite(estimate_hours) or estimate_hours >= contract.stops.st11_hours:",
     ST11 + " " + FST11 % "sum_at_bound"),
    ("B17 status not revised", IN, '{"id": "B17", "status": ACCEPTED_C4, "ruling": RULING_REF_C4,',
     '{"id": "B17", "status": ACCEPTED,', RULED),
    ("B17 text not revised", IN,
     '"estimate + the checkpoint overhead. B17\'s estimate = (measured mean seconds per step of the first "',
     '"estimate. B17\'s estimate = (measured mean seconds per step of the first "', RULED),
    ("TEST look-ahead with a 10% margin", PI,
     '            + n["test_state_hashes"] * pre["hash_s"])\n',
     '            + n["test_state_hashes"] * pre["hash_s"]) * 1.1\n', OVER),
    ("run look-ahead (ST7) without the checkpoint save", PI,
     '+ 2 * q["hash_s"]\n                + q["save_s"] + q["file_hash_s"]', '+ 2 * q["hash_s"]\n                + q["file_hash_s"]',
     LOOK),
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
