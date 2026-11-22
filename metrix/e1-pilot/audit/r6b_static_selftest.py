"""R6b-3 (round 6, re-audit of 2620f306): sensitivity test of r6b_harness_static.audit_texts on synthetic fixtures.
The fixtures are the Data Auditor's own text (a toy harness with other names); they follow the same pattern
(flag, EXIT handler, set -u, $# check, final RESULT line) because that is the pattern the checker verifies. Nothing of
the Executor is read, executed or copied. Each fixture pair (old, new) is checked; the correct variant must give
True, every defective variant False. Exceptions -> RESULT: FAIL.
usage: python -I r6b_static_selftest.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r6_guard import run
import r6b_harness_static as S

OLD = """#!/usr/bin/env bash
# toy harness (auditor fixture): counts non-empty keys
set -u
SRC="$1"; DST="$2"
items=(
  "a|x"
  "b|y"
)
hits=0
for it in "${items[@]}"; do
  IFS='|' read -r key val <<< "$it"
  if [ -n "$key" ]; then hits=$((hits + 1)); fi
  echo "== $key $val $SRC $DST"
done
echo "hits $hits"
[ COND ]
"""
COND = '"$hits" = "${#items[@]}"'
PRE = """# fixture: added comment
DONE_FLAG=0
fin() { st=$?; if [ "$DONE_FLAG" = 0 ]; then echo "RESULT: FAIL"; [ "$st" = 0 ] && st=1; fi; exit "$st"; }
trap fin EXIT
"""
CHECK = 'if [ $# -ne 2 ]; then echo "usage: toy SRC DST" >&2; exit 2; fi\n'
TAIL = """DONE_FLAG=1
if [ COND ]; then echo "RESULT: PASS"; exit 0; fi
echo "RESULT: FAIL"
exit 1
"""


def make_new(old, pre=PRE, check=CHECK, tail=TAIL, cond=COND):
    head, rest = old.split("set -u\n")
    body = rest.rsplit("[ COND ]\n", 1)[0]
    return head + pre + "set -u\n" + check + body + tail.replace("COND", cond)


def main():
    old = OLD.replace("COND", COND)
    cases = {
        "correct": (old, make_new(OLD), True),
        "M1 trap installed after the $# check": (old, make_new(OLD, pre=PRE.replace("trap fin EXIT\n", ""),
                                                             check=CHECK + "trap fin EXIT\n"), False),
        "M2 verdict condition changed": (old, make_new(OLD, cond='"$hits" -ge 1'), False),
        "M3 one body line changed": (old, make_new(OLD).replace('echo "hits $hits"', 'echo "hits: $hits"'), False),
        "M4 flag set to 1 before the loop": (old, make_new(OLD).replace("hits=0\n", "hits=0\nDONE_FLAG=1\n"), False),
        "M5 set -e added": (old, make_new(OLD).replace("set -u\n", "set -u\nset -e\n"), False),
        "M6 handler does not turn status 0 into 1": (old, make_new(OLD, pre=PRE.replace(' [ "$st" = 0 ] && st=1;', "")), False),
        "M7 $# check against the wrong count": (old, make_new(OLD, check=CHECK.replace("-ne 2", "-ne 3")), False),
        "M8 verdict reads a variable first assigned inside the loop":
            (OLD.replace("COND", '"$hits$val" = "2y"'), make_new(OLD, cond='"$hits$val" = "2y"'), False),
        "M9 no RESULT line before the final exit 1": (old, make_new(OLD, tail=TAIL.replace('echo "RESULT: FAIL"\n', 'echo "done"\n')), False),
    }
    ok = True
    summary = []
    for name, (o, n, expect) in cases.items():
        print(f"######## fixture: {name} (expected {expect})")
        got = S.audit_texts(o, n, f"fixture[{name}]", "old", "new")
        good = got is expect
        ok &= good
        summary.append((name, expect, got, good))
    print("== summary (fixture, expected, checker result, as expected)")
    for s in summary:
        print("  ", s)
    return bool(ok)


if __name__ == "__main__":
    run(main)
