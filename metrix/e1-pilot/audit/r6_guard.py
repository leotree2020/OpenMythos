"""Data Auditor helper (round 6, item 2 rule applied to the auditor's own new scripts). Independent; no Executor code.

run(main): main() returns True (checks passed) or False (a check failed).
  - True  -> prints "RESULT: PASS", exit code 0
  - False -> prints "RESULT: FAIL", exit code 1
  - any exception, including SystemExit and KeyboardInterrupt raised inside main() -> traceback on stdout,
    "RESULT: FAIL", exit code 2
  - main() returning anything other than True / False -> "RESULT: FAIL", exit code 3
Scripts using this helper never call sys.exit themselves."""
import sys
import traceback


def run(main):
    try:
        ok = main()
    except BaseException:                      # noqa: B902 - deliberate: every failure path ends in RESULT: FAIL
        sys.stdout.flush()
        traceback.print_exc(file=sys.stdout)
        print("RESULT: FAIL (exception)")
        sys.stdout.flush()
        sys.exit(2)
    if ok is True:
        print("RESULT: PASS")
        sys.stdout.flush()
        sys.exit(0)
    if ok is False:
        print("RESULT: FAIL")
        sys.stdout.flush()
        sys.exit(1)
    print("RESULT: FAIL (main returned %r, not a bool)" % (ok,))
    sys.stdout.flush()
    sys.exit(3)
