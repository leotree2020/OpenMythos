"""R6b-2 (round 6, re-audit of 2620f306): bash semantics behind the static argument of r6b_harness_static.py.
Generic probe scripts written by the Data Auditor (own text, own names: flag FIN, handler finish, status s); nothing of
the Executor is executed, sourced or copied. Each probe is written to <work_dir>, run as `bash probe.sh ARGS` with
stdout and stderr captured separately, and its stdout / stderr / exit status printed. Exceptions -> RESULT: FAIL.

Pattern under test (same mechanism as the harnesses: a flag, an EXIT trap that prints a FAIL line when the flag is
not set and turns status 0 into 1, `set -u`, an argument-count check, and a verdict that sets the flag, prints a line
and exits 0 or 1):
  A  wrong argument count -> explicit `exit 2` before the flag: one VERDICT: FAIL line, status 2
  B  unbound variable under set -u in the middle of the run: handler runs, one VERDICT: FAIL line, status != 0
  C  `exit 0` before the flag: one VERDICT: FAIL line, status 1
  D  script falls off its end without setting the flag (last status 0): one VERDICT: FAIL line, status 1
  E1 flag set, verdict true: last line VERDICT: PASS, status 0, no handler line
  E2 flag set, verdict false: last line VERDICT: FAIL (exactly one), status 1
  F  failing commands in the middle (missing program -> 127, redirect into a missing directory, cmp and grep -c on
     missing files) do not stop a script without set -e; execution reaches the verdict, which here is FAIL, status 1
  G  command substitutions $( ), $(( )) and here-strings <<< do not run the parent's EXIT trap (one line only)
  J  `exit` inside the EXIT handler does not run the handler again (one line only)
  K  with zero arguments, `$#` is defined under set -u (no unbound error); `$1` is not (old behaviour: exit 1)
Information only (not part of PASS): H a syntax error later in the file; I1 SIGTERM, I2 SIGINT sent to the script
itself; L the handler line is the last stdout line also when the script printed earlier stdout and stderr.
PASS iff A-G, J, K hold.
usage: python -I r6b_bash_probes.py <bash> <work_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess
from r6_guard import run

HEAD = """FIN=0
finish() {
  s=$?
  if [ "$FIN" != 1 ]; then
    echo "VERDICT: FAIL"
    if [ "$s" -eq 0 ]; then s=1; fi
  fi
  exit "$s"
}
trap finish EXIT
set -u
if [ "$#" != 2 ]; then echo "need 2 arguments" >&2; exit 2; fi
A1="$1"; A2="$2"
"""


def verdict(cond):
    return f"""FIN=1
if {cond}; then echo "VERDICT: PASS"; exit 0; fi
echo "VERDICT: FAIL"
exit 1
"""


PROBES = {
    "A": (HEAD + "echo body\n" + verdict("[ 1 = 1 ]"), [], dict(rc=2, fails=1, last="VERDICT: FAIL")),
    "B": (HEAD + "echo before\necho \"$NOT_SET_ANYWHERE\"\necho after\n" + verdict("[ 1 = 1 ]"), ["x", "y"],
          dict(rc_nonzero=True, fails=1, last="VERDICT: FAIL", absent="after")),
    "C": (HEAD + "echo early\nexit 0\n" + verdict("[ 1 = 1 ]"), ["x", "y"], dict(rc=1, fails=1, last="VERDICT: FAIL")),
    "D": (HEAD + "echo body\ntrue\n", ["x", "y"], dict(rc=1, fails=1, last="VERDICT: FAIL")),
    "E1": (HEAD + "n=0\nfor k in 1 2 3; do n=$((n + 1)); done\n" + verdict('[ "$n" = 3 ]'), ["x", "y"],
           dict(rc=0, fails=0, passes=1, last="VERDICT: PASS")),
    "E2": (HEAD + "n=0\nfor k in 1 2; do n=$((n + 1)); done\n" + verdict('[ "$n" = 3 ]'), ["x", "y"],
           dict(rc=1, fails=1, passes=0, last="VERDICT: FAIL")),
    "F": (HEAD + """good=0
/no/such/program --flag > "$A1/out.txt" 2>&1; r1=$?
echo "missing program status $r1"
echo hi > /no/such/dir/file 2>/dev/null; r2=$?
echo "redirect into missing directory status $r2"
if cmp -s /no/such/a /no/such/b; then good=$((good + 1)); fi
c=$(grep -c '^X$' /no/such/file 2>/dev/null); r3=$?
echo "grep -c on a missing file: status $r3, output [$c]"
echo "reached the verdict"
""" + verdict('[ "$good" = 1 ]'), ["__WORK__", "y"], dict(rc=1, fails=1, last="VERDICT: FAIL", present="reached the verdict")),
    "G": (HEAD + """x=$(echo inner; exit 3); y=$(( 2 + 3 )); z=$(bash -c 'exit 0')
IFS='|' read -r p q <<< "a|b"
w=$(grep -c . <<< "line")
echo "x=[$x] y=[$y] p=[$p] q=[$q] w=[$w]"
""" + verdict("[ 1 = 1 ]"), ["x", "y"], dict(rc=0, fails=0, passes=1, last="VERDICT: PASS")),
    "J": (HEAD + "exit 5\n", ["x", "y"], dict(rc=5, fails=1, last="VERDICT: FAIL")),
    "K": ("set -u\necho \"count $#\"\necho \"first $1\"\necho unreachable\n", [], dict(rc_nonzero=True, absent="unreachable",
                                                                                         present="count 0")),
    "H": (HEAD + "echo before\nif [ 1 = 1 ]; then echo x\n" + "fi fi )\n" + verdict("[ 1 = 1 ]"), ["x", "y"], None),
    "I1": (HEAD + "echo before\nkill -TERM $$\necho after\n" + verdict("[ 1 = 1 ]"), ["x", "y"], None),
    "I2": (HEAD + "echo before\nkill -INT $$\necho after\n" + verdict("[ 1 = 1 ]"), ["x", "y"], None),
    "L": (HEAD + "echo out1\necho err1 >&2\necho out2\nexit 4\n", ["x", "y"], None),
}


def main():
    bash, work = sys.argv[1], sys.argv[2]
    os.makedirs(work, exist_ok=True)
    print("bash:", subprocess.check_output([bash, "--version"], text=True).split("\n")[0])
    ok = True
    for name, (text, args, exp) in PROBES.items():
        path = os.path.join(work, f"probe_{name}.sh")
        with open(path, "w") as fh:
            fh.write("#!/usr/bin/env bash\n" + text)
        args = [work if a == "__WORK__" else a for a in args]
        r = subprocess.run([bash, path] + args, capture_output=True, text=True, timeout=30, cwd=work)
        out = r.stdout.rstrip("\n").split("\n") if r.stdout else []
        fails = sum(l == "VERDICT: FAIL" for l in out)
        passes = sum(l == "VERDICT: PASS" for l in out)
        last = out[-1] if out else None
        print(f"== probe {name}: bash {os.path.basename(path)} {' '.join(args)}")
        for l in text.rstrip("\n").split("\n")[len(HEAD.rstrip(chr(10)).split(chr(10))) if text.startswith(HEAD) else 0:]:
            print(f"   | {l}")
        print(f"   status {r.returncode} | stdout {out} | stderr {r.stderr.strip().splitlines()}")
        print(f"   VERDICT: FAIL lines {fails}, VERDICT: PASS lines {passes}, last stdout line {last!r}")
        if exp is None:
            print("   (information only)")
            continue
        good = True
        if "rc" in exp:
            good &= r.returncode == exp["rc"]
        if exp.get("rc_nonzero"):
            good &= r.returncode != 0
        if "fails" in exp:
            good &= fails == exp["fails"]
        if "passes" in exp:
            good &= passes == exp["passes"]
        if "last" in exp:
            good &= last == exp["last"]
        if "absent" in exp:
            good &= exp["absent"] not in out
        if "present" in exp:
            good &= any(exp["present"] in l for l in out)
        print(f"   expected {exp} -> {good}")
        ok &= good
    return bool(ok)


if __name__ == "__main__":
    run(main)
