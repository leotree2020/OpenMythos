"""R8-P: does `env PYTHONHASHSEED=<n> python -I ...` fix the string-hash seed? (Executor's t1d_data_hashes.txt runs
reports/round7/gen_s_cands.py twice as `env PYTHONHASHSEED=0 python -I` and `env PYTHONHASHSEED=31337 python -I`.)
Data Auditor's own script; standard library only; runs child interpreters of the same executable.
Exceptions -> RESULT: FAIL (r6_guard). Informational: PASS means the probe ran, whatever the answer.
usage: python -I r8_hashseed_probe.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess
from r6_guard import run

CODE = ("import os, sys; print('flags.hash_randomization', sys.flags.hash_randomization, '| ignore_environment', "
        "sys.flags.ignore_environment, '| env PYTHONHASHSEED', os.environ.get('PYTHONHASHSEED'), '| hash(\"abc\")', hash('abc'))")


def child(flags, seed):
    env = dict(os.environ, PYTHONHASHSEED=seed)
    return subprocess.run([sys.executable, *flags, "-c", CODE], env=env, capture_output=True, text=True, check=True).stdout.strip()


def main():
    print("python", sys.version.split()[0], sys.executable)
    res = {}
    for flags in (["-I"], []):
        for seed in ("0", "0", "31337", "31337"):
            out = child(flags, seed)
            res.setdefault((tuple(flags), seed), []).append(out.rsplit(" ", 1)[1])
            print(f"flags {flags or '(none)'} PYTHONHASHSEED={seed}: {out}")
    for flags in (("-I",), ()):
        same0 = len(set(res[(flags, "0")])) == 1
        print(f"flags {list(flags) or '(none)'}: two runs with PYTHONHASHSEED=0 give the same hash('abc'): {same0}")
    print("conclusion: with -I the variable is", "IGNORED" if len(set(res[(("-I",), "0")])) > 1 else "honoured",
          "| without -I it is", "honoured" if len(set(res[((), "0")])) == 1 else "IGNORED")
    return True


run(main)
