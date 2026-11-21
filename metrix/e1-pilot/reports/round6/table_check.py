#!/usr/bin/env python3
"""Round 6, item 1i: every row of every Markdown table in the protocol has as many cells as its header row.

A table is a run of consecutive lines that start with "|"; its first line is the header. Cells are split at "|"
not preceded by a backslash (GitHub Markdown splits a table row at an unescaped "|", also inside a code span).
Also counts, in table rows, "<|endoftext|>" and "<|im_end|>" written with unescaped bars (required: 0).

  python table_check.py PROTOCOL.md
"""
import re
import sys

BAR = re.compile(r"(?<!\\)\|")
UNESCAPED = re.compile(r"<\|(?:endoftext|im_end|im_start)\|>")


def main():
    lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
    header = None
    rows = bad = special = 0
    for i, line in enumerate(lines, 1):
        if not line.startswith("|"):
            header = None
            continue
        cells = len(BAR.split(line)) - 2
        if header is None:
            header = (i, cells)
            continue
        rows += 1
        if cells != header[1]:
            bad += 1
            print("line %d: %d cells, header (line %d) %d: %s" % (i, cells, header[0], header[1], line[:80]))
        n = len(UNESCAPED.findall(line))
        if n:
            special += n
            print("line %d: %d special token(s) with unescaped bars" % (i, n))
    print("table rows checked: %d; rows whose cell count differs from the header: %d; unescaped special tokens: %d"
          % (rows, bad, special))
    ok = bad == 0 and special == 0
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def run_guarded(main):
    """Round 6, task 2: on an exception, or on an exit that comes before the RESULT line (sys.exit("message"),
    an argparse error), print RESULT: FAIL and exit non-zero. Exit codes 0 and 1 raised by main() pass through."""
    import sys
    import traceback
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


if __name__ == "__main__":
    run_guarded(main)
