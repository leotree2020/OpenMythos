"""The single entry point of METRIX E1-PILOT (Implementation Task Order V1, sections 4, 5 and 7; protocol v1.1
section 8, steps 1-8). The steps are in metrix_e1.pilot; RUNBOOK_A100.md gives the command sequence on the A100.

  python run_pilot.py smoke --steps STEPS --inputs DIR --work DIR
        CPU smoke test: steps 1-7 with a random small model of the protocol's class, STEPS optimizer steps per
        training run (fewer than the contract's), step 8 only as the refusal of the TEST generator. Every output is
        labelled SMOKE — NOT A RESULT; nothing is committed; Gate 0 is NOT_TESTED.
  python run_pilot.py formal --inputs DIR --work DIR
        On the A100: steps 1-7 and, when Gate 0 is PASS, the freeze record of step 8; every step's record is
        committed and pushed. There is no step option: the contract's step count is the only one (RunMode refuses a
        shortened count in formal mode).
  python run_pilot.py test-generate --inputs DIR --work DIR
        Step 8, on the Owner's decision: the TEST generator (python -m metrix_e1.test_data) with --out <work>/test.
  python run_pilot.py test-evaluate --inputs DIR --work DIR
        Step 8, after the data-auditor's L6 count is committed: TEST evaluated once.
  python run_pilot.py fetch-model --inputs DIR
        On the A100 host only: the pinned model revision's files into <inputs>/qwen_model.

--inputs is the directory written by `python -m metrix_e1.data fetch` and `python -m metrix_e1.train fetch-config`;
--work is a directory outside the repository. Each command prints RESULT: PASS or RESULT: FAIL; exit 0 only on PASS
(an exception or a stop prints RESULT: FAIL and exits non-zero).
"""
import argparse
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parent
SRC = PILOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metrix_e1 import mode as M          # noqa: E402
from metrix_e1 import pilot as P         # noqa: E402
from metrix_e1._cli import run_guarded   # noqa: E402


def parser():
    ap = argparse.ArgumentParser(prog="run_pilot.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("smoke")
    a.add_argument("--steps", type=int, required=True, help="optimizer steps per training run (smoke only)")
    for name in ("smoke", "formal", "test-generate", "test-evaluate"):
        x = a if name == "smoke" else sub.add_parser(name)
        x.add_argument("--inputs", required=True)
        x.add_argument("--work", required=True)
    sub.add_parser("fetch-model").add_argument("--inputs", required=True)
    return ap


def build_mode(args):
    """smoke: RunMode(smoke, --steps); every other command: the formal mode (no shortened step count exists for it)."""
    return M.smoke_mode(args.steps) if args.cmd == "smoke" else M.FORMAL_MODE


def main(argv=None):
    a = parser().parse_args(argv)
    if a.cmd == "fetch-model":
        from metrix_e1 import frozen as FZ
        for name, sha in P.fetch_model(FZ.load(), a.inputs).items():
            print("%-40s sha256 %s (downloaded from the frozen revision)" % (name, sha))
        print("RESULT: PASS")
        sys.exit(0)
    mode = build_mode(a)
    p = P.Pilot(mode, a.inputs, a.work, "cpu" if mode.smoke else "cuda")
    if a.cmd in ("smoke", "formal"):
        ok, status = P.run_gate(p, a.cmd)
        passed = ok and (status == "PASS" or (mode.smoke and status == "NOT_TESTED"))
        print("%s %s: %s" % (a.cmd, "completed" if ok else "stopped", status))
    elif a.cmd == "test-generate":
        passed = P.run_test_generate(p) == 0
    else:
        ok, status = P.run_test_evaluate(p)
        passed = ok and status == "PASS"
        print("test-evaluate %s: %s" % ("completed" if ok else "stopped or refused", status))
    print("RESULT: %s" % ("PASS" if passed else "FAIL"))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    run_guarded(main)
