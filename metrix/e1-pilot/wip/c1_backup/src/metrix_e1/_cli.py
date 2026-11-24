"""Exit convention of every judging command of the package (Implementation Task Order V1, section 5 "检查脚本"):
a check that does not pass prints "RESULT: FAIL" and exits non-zero; an exception does the same. The same guard
as the round 6 check scripts (metrix/e1-pilot/reports/round5/l6_check.py, run_guarded).
"""
import sys
import traceback


def run_guarded(main):
    """Run main(). Exit codes 0 and 1 raised by main() pass through (main() prints its own RESULT line before them);
    any other SystemExit (sys.exit("message"), an argparse error) and any exception print RESULT: FAIL and exit
    non-zero."""
    try:
        main()
    except SystemExit as e:
        if e.code is None or (type(e.code) is int and e.code in (0, 1)):
            raise
        sys.stdout.flush()
        if type(e.code) is not int:
            print(e.code, file=sys.stderr)
            sys.stderr.flush()
        print("RESULT: FAIL")
        sys.exit(e.code if type(e.code) is int else 1)
    except BaseException:
        sys.stdout.flush()
        traceback.print_exc()
        sys.stderr.flush()
        print("RESULT: FAIL")
        sys.exit(1)
